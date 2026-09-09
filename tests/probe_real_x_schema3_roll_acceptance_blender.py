"""Read-only real-X schema-2 -> schema-3 roll-decoupling acceptance probe.

Run this only in two disposable Blender background processes.  Baseline mode
prints ``REAL_X_SCHEMA3_BASELINE_BASE64``; pass that exact token to migrate
mode in the second process.  Each process opens the source Blend once and never
saves it:

1. remove the saved schema-2 rig in memory to expose the underlying artist
   pose used as the independent orientation baseline;
2. reopen the untouched schema-2 input, Rebuild directly to schema 3, repeat
   Rebuild twice, then Remove and audit the complete cleanup.

The first branch is important.  Schema 2 evaluates IK directly on the deform
bones, so its evaluated upper/lower matrices can contain roughly 164/180
degrees of Pole-induced axial roll.  Those evaluated matrices are deliberately
not accepted as the artist-frame baseline.
"""

from __future__ import annotations

import hashlib
import base64
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
TESTS_ROOT = PROJECT_ROOT / "tests"
for root in (ADDONS_ROOT, TESTS_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

import character_designer
from character_designer import limb_ik
import probe_limb_ik_real_x_blender as probe
import probe_real_x_0292_rebuild_blender as rebuild_probe
import test_real_x_pole_direction_migration_blender as migration
import test_real_x_remove_analyze_modeled_build_blender as real_x


EXPECTED_KEYS = set(probe.EXPECTED_CHAINS)
ROLL_LIMIT_DEGREES = 0.2
TRANSPORT_DOT_MIN = 0.99999
ALIGNMENT_MIN = 0.999
POSITION_TOLERANCE = 5.0e-5
ROTATION_TOLERANCE_DEGREES = 0.05
SCALE_TOLERANCE = 5.0e-5
OLD_ARM_TWIST_MIN_DEGREES = 150.0


def _fingerprint(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "sha256": digest.hexdigest().upper(),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _arguments():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) not in {2, 3} or args[0] not in {"baseline", "migrate"}:
        raise SystemExit(
            "Expected: -- baseline <schema2.blend> OR -- migrate <schema2.blend> <baseline-base64>"
        )
    mode = args[0]
    if mode == "baseline" and len(args) != 2:
        raise SystemExit("Baseline mode takes exactly one Blend path")
    if mode == "migrate" and len(args) != 3:
        raise SystemExit("Migrate mode also requires the BASELINE_PAYLOAD_BASE64 value")
    path = Path(args[1]).resolve()
    if not path.is_file() or path.suffix.lower() != ".blend":
        raise SystemExit(f"Input is not a Blend file: {path}")
    return mode, path, (args[2] if len(args) == 3 else "")


def _open_input(path: Path):
    result = bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    if result != {"FINISHED"}:
        raise AssertionError(f"Could not open input Blend: {result}")


def _settle(armature, mode="POSE"):
    migration._mode_set(bpy.context, armature, mode)
    armature.data.update_tag()
    armature.update_tag(refresh={"OBJECT"})
    bpy.context.scene.update_tag()
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def _prepare_saved_schema2(path: Path):
    _open_input(path)
    armature = migration._find_real_armature()
    _settle(armature)
    inventory = limb_ik._validate_inventory(armature)
    if inventory["schema"] != limb_ik.ENHANCED_SCHEMA:
        raise AssertionError(
            f"Acceptance input must be schema 2, got schema {inventory['schema']}"
        )
    if set(inventory["rigs"]) != EXPECTED_KEYS:
        raise AssertionError(
            f"Acceptance input must contain all four limbs, got {sorted(inventory['rigs'])}"
        )
    repair = rebuild_probe._repair_known_collection_drift(armature, inventory)
    inventory = limb_ik._validate_inventory(armature)
    limb_ik._removal_resources(bpy.context, armature, inventory)
    return armature, inventory, repair


def _source_names(armature):
    return tuple(
        bone.name
        for bone in armature.data.bones
        if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    )


def _matrix_map(armature, names):
    _settle(armature)
    return {name: armature.pose.bones[name].matrix.copy() for name in names}


def _matrix_result(actual: Matrix, expected: Matrix):
    errors = migration._matrix_errors(actual, expected)
    return {
        "position": float(errors["position"]),
        "rotation_degrees": math.degrees(float(errors["rotation"])),
        "scale": float(errors["scale"]),
    }


def _assert_matrix(label, actual: Matrix, expected: Matrix):
    result = _matrix_result(actual, expected)
    if (
        result["position"] > POSITION_TOLERANCE
        or result["rotation_degrees"] > ROTATION_TOLERANCE_DEGREES
        or result["scale"] > SCALE_TOLERANCE
    ):
        raise AssertionError(f"{label} changed: {result}")
    return result


def _unit_axis(matrix: Matrix, index: int):
    axis = Vector(matrix.to_3x3().col[index])
    if axis.length <= limb_ik.EPSILON:
        raise AssertionError("Pose matrix has a zero local axis")
    return axis.normalized()


def _minimum_swing_metrics(artist_matrix: Matrix, evaluated_matrix: Matrix):
    """Residual local-Y roll after shortest-swing transporting artist X/Z."""
    artist_x = _unit_axis(artist_matrix, 0)
    artist_y = _unit_axis(artist_matrix, 1)
    artist_z = _unit_axis(artist_matrix, 2)
    actual_x = _unit_axis(evaluated_matrix, 0)
    actual_y = _unit_axis(evaluated_matrix, 1)
    actual_z = _unit_axis(evaluated_matrix, 2)
    swing = artist_y.rotation_difference(actual_y)
    expected_x = (swing @ artist_x).normalized()
    expected_z = (swing @ artist_z).normalized()
    x_dot = max(-1.0, min(1.0, expected_x.dot(actual_x)))
    z_dot = max(-1.0, min(1.0, expected_z.dot(actual_z)))
    twist_x = math.atan2(
        actual_y.dot(expected_x.cross(actual_x)),
        x_dot,
    )
    twist_z = math.atan2(
        actual_y.dot(expected_z.cross(actual_z)),
        z_dot,
    )
    return {
        "axial_twist_degrees": math.degrees(twist_x),
        "z_axial_twist_degrees": math.degrees(twist_z),
        "transported_x_dot": x_dot,
        "transported_z_dot": z_dot,
        "swing_degrees": math.degrees(float(swing.angle)),
    }


def _roll_metrics(artist_pose, actual_pose):
    result = {}
    for key, chain in sorted(probe.EXPECTED_CHAINS.items()):
        label = f"{key[0]}.{key[1]}"
        result[label] = {
            name: _minimum_swing_metrics(artist_pose[name], actual_pose[name])
            for name in chain[:2]
        }
    return result


def _assert_schema2_twist(metrics):
    for side in ("L", "R"):
        label = f"ARM.{side}"
        for name, item in metrics[label].items():
            if abs(item["axial_twist_degrees"]) < OLD_ARM_TWIST_MIN_DEGREES:
                raise AssertionError(
                    f"Saved schema-2 {label} {name} did not expose the expected old "
                    f"direct-IK twist: {item}"
                )


def _assert_roll_clean(stage, metrics):
    for label, bones in metrics.items():
        for name, item in bones.items():
            if max(
                abs(item["axial_twist_degrees"]),
                abs(item["z_axial_twist_degrees"]),
            ) >= ROLL_LIMIT_DEGREES:
                raise AssertionError(f"{stage} {label} {name} retained axial roll: {item}")
            if min(item["transported_x_dot"], item["transported_z_dot"]) <= TRANSPORT_DOT_MIN:
                raise AssertionError(
                    f"{stage} {label} {name} did not preserve transported artist X/Z: {item}"
                )


def _bend_alignment(start, joint, end, desired):
    axis = Vector(end) - Vector(start)
    if axis.length <= limb_ik.EPSILON:
        raise AssertionError("Two-bone chain has a zero root-to-end axis")
    projection = Vector(start) + axis * (
        (Vector(joint) - Vector(start)).dot(axis) / axis.length_squared
    )
    bend = Vector(joint) - projection
    wanted = limb_ik._project_perpendicular(Vector(desired), axis)
    if min(bend.length, wanted.length) <= limb_ik.EPSILON:
        raise AssertionError("Two-bone bend/alignment residual is undefined")
    return float(bend.normalized().dot(wanted.normalized())), bend, wanted


def _alignment_metrics(armature, inventory):
    result = {}
    _settle(armature)
    for key, rig in sorted(inventory["rigs"].items()):
        label = f"{key[0]}.{key[1]}"
        desired = probe.DEFAULT_POLE_DIRECTIONS[key]
        configured = Vector(rig["configured_pole_direction"]).normalized()
        configured_dot = configured.dot(desired.normalized())
        if configured_dot <= 0.999999:
            raise AssertionError(
                f"{label} did not persist its raw fixed direction: "
                f"configured={tuple(configured)}, expected={tuple(desired)}, dot={configured_dot}"
            )
        item = {}
        for graph, upper_name, lower_name in (
            ("source", rig["chain"][0], rig["chain"][1]),
            ("mch", rig["mch_upper"].name, rig["mch_lower"].name),
        ):
            upper = armature.pose.bones[upper_name]
            lower = armature.pose.bones[lower_name]
            dot, bend, wanted = _bend_alignment(
                upper.head,
                lower.head,
                lower.tail,
                desired,
            )
            item[graph] = {
                "upper": upper_name,
                "lower": lower_name,
                "dot": dot,
                "bend_y": float(bend.y),
                "desired_projected_y": float(wanted.normalized().y),
                "bend_length": float(bend.length),
                "start": tuple(float(value) for value in upper.head),
                "joint": tuple(float(value) for value in lower.head),
                "end": tuple(float(value) for value in lower.tail),
            }
            if dot < ALIGNMENT_MIN:
                raise AssertionError(
                    f"{label} {graph} bend alignment is only {dot}: {item[graph]}"
                )
            if key[0] == "ARM" and bend.y <= 0.0:
                raise AssertionError(f"{label} {graph} elbow did not bend toward +Y")
            if key[0] == "LEG" and bend.y >= 0.0:
                raise AssertionError(f"{label} {graph} knee did not bend toward -Y")
        result[label] = item
    return result


def _ori_rest_metrics(armature, inventory):
    result = {}
    for key, rig in sorted(inventory["rigs"].items()):
        label = f"{key[0]}.{key[1]}"
        result[label] = {}
        for segment, source_name, ori in (
            ("upper", rig["chain"][0], rig["ori_upper"]),
            ("lower", rig["chain"][1], rig["ori_lower"]),
        ):
            source = armature.data.bones[source_name]
            errors = _matrix_result(ori.matrix_local, source.matrix_local)
            x_dot = _unit_axis(ori.matrix_local, 0).dot(_unit_axis(source.matrix_local, 0))
            z_dot = _unit_axis(ori.matrix_local, 2).dot(_unit_axis(source.matrix_local, 2))
            if (
                errors["position"] > 2.0e-6
                or errors["rotation_degrees"] > 1.0e-3
                or errors["scale"] > SCALE_TOLERANCE
                or min(x_dot, z_dot) <= TRANSPORT_DOT_MIN
            ):
                raise AssertionError(
                    f"{label} ORI {segment} rest frame differs from source: "
                    f"errors={errors}, x_dot={x_dot}, z_dot={z_dot}"
                )
            result[label][segment] = {
                "source": source_name,
                "ori": ori.name,
                "position_error": errors["position"],
                "rotation_error_degrees": errors["rotation_degrees"],
                "x_dot": float(x_dot),
                "z_dot": float(z_dot),
            }
    return result


def _capture_unconstrained_ori(armature, inventory):
    """Temporarily mute only ORI location/track constraints, then restore."""
    source_before = {
        name: armature.pose.bones[name].matrix.copy()
        for chain in probe.EXPECTED_CHAINS.values()
        for name in chain
    }
    constraints = []
    for rig in inventory["rigs"].values():
        for bone in (rig["ori_upper"], rig["ori_lower"]):
            pose_bone = armature.pose.bones[bone.name]
            for constraint in pose_bone.constraints:
                constraints.append((constraint, bool(constraint.mute)))
                constraint.mute = True
    try:
        _settle(armature)
        result = {}
        for key, rig in sorted(inventory["rigs"].items()):
            result[key] = {
                rig["chain"][0]: armature.pose.bones[rig["ori_upper"].name].matrix.copy(),
                rig["chain"][1]: armature.pose.bones[rig["ori_lower"].name].matrix.copy(),
            }
    finally:
        for constraint, mute in constraints:
            constraint.mute = mute
        _settle(armature)
    for name, before in source_before.items():
        _assert_matrix(f"ORI mute/restore source {name}", armature.pose.bones[name].matrix, before)
    return result


def _ori_baseline_metrics(artist_pose, ori_pose):
    result = {}
    for key, matrices in sorted(ori_pose.items()):
        label = f"{key[0]}.{key[1]}"
        result[label] = {
            name: _minimum_swing_metrics(artist_pose[name], matrix)
            for name, matrix in matrices.items()
        }
    return result


def _capture_endpoint_state(armature, inventory):
    _settle(armature)
    result = {}
    for key, rig in sorted(inventory["rigs"].items()):
        upper_name, lower_name, end_name = rig["chain"]
        result[key] = {
            "end_matrix": armature.pose.bones[end_name].matrix.copy(),
            "root_head": Vector(armature.pose.bones[upper_name].head),
            "lower_tail": Vector(armature.pose.bones[lower_name].tail),
            "end_head": Vector(armature.pose.bones[end_name].head),
        }
    return result


def _endpoint_comparison(before, after, stage):
    result = {}
    for key, old in sorted(before.items()):
        label = f"{key[0]}.{key[1]}"
        new = after[key]
        matrix = _assert_matrix(
            f"{stage} {label} Hand/Foot matrix",
            new["end_matrix"],
            old["end_matrix"],
        )
        vectors = {
            name: float((new[name] - old[name]).length)
            for name in ("root_head", "lower_tail", "end_head")
        }
        if max(vectors.values()) > POSITION_TOLERANCE:
            raise AssertionError(f"{stage} {label} endpoint changed: {vectors}")
        result[label] = {"matrix": matrix, **vectors}
    return result


def _capture_stable_state(armature, inventory):
    _settle(armature)
    source = {}
    for chain in probe.EXPECTED_CHAINS.values():
        for name in chain:
            pose_bone = armature.pose.bones[name]
            source[name] = {
                "matrix": pose_bone.matrix.copy(),
                "head": Vector(pose_bone.head),
                "tail": Vector(pose_bone.tail),
            }
    controls = {}
    mechanisms = {}
    for key, rig in sorted(inventory["rigs"].items()):
        for role in ("target", "pole", "heel", "solver_target"):
            bone = rig.get(role)
            if bone is None:
                continue
            pose_bone = armature.pose.bones[bone.name]
            controls[bone.name] = {
                "pose": pose_bone.matrix.copy(),
                "rest": bone.matrix_local.copy(),
                "basis": pose_bone.matrix_basis.copy(),
            }
        for role in ("mch_upper", "mch_lower", "ori_upper", "ori_lower"):
            bone = rig[role]
            mechanisms[bone.name] = armature.pose.bones[bone.name].matrix.copy()
    return {"source": source, "controls": controls, "mechanisms": mechanisms}


def _stable_comparison(before, after, stage):
    if {field: set(before[field]) for field in before} != {
        field: set(after[field]) for field in after
    }:
        raise AssertionError(f"{stage} changed stable bone-name inventory")
    maxima = {
        "position": 0.0,
        "rotation_degrees": 0.0,
        "scale": 0.0,
        "head": 0.0,
        "tail": 0.0,
    }
    for name, old in before["source"].items():
        comparison = _assert_matrix(
            f"{stage} source {name}", after["source"][name]["matrix"], old["matrix"]
        )
        for field in ("position", "rotation_degrees", "scale"):
            maxima[field] = max(maxima[field], comparison[field])
        for field in ("head", "tail"):
            error = (after["source"][name][field] - old[field]).length
            maxima[field] = max(maxima[field], float(error))
            if error > POSITION_TOLERANCE:
                raise AssertionError(f"{stage} source {name} {field} drifted by {error}")
    for group in ("controls",):
        for name, old in before[group].items():
            for field, old_matrix in old.items():
                comparison = _assert_matrix(
                    f"{stage} {group} {name} {field}",
                    after[group][name][field],
                    old_matrix,
                )
                for metric in ("position", "rotation_degrees", "scale"):
                    maxima[metric] = max(maxima[metric], comparison[metric])
    for name, old in before["mechanisms"].items():
        comparison = _assert_matrix(
            f"{stage} mechanism {name}", after["mechanisms"][name], old
        )
        for field in ("position", "rotation_degrees", "scale"):
            maxima[field] = max(maxima[field], comparison[field])
    return maxima


def _assert_source_static(stage, armature, source_names, signatures):
    if tuple(bone.name for bone in armature.data.bones if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE) != source_names:
        raise AssertionError(f"{stage}: source bone inventory/order changed")
    if probe._edit_bone_signature(armature, source_names) != signatures["edit"]:
        raise AssertionError(f"{stage}: source edit/rest signature changed")
    if probe._source_basis_signature(armature, source_names) != signatures["basis"]:
        raise AssertionError(f"{stage}: source matrix_basis changed (pose was baked)")
    if probe._source_pose_signature(armature, source_names) != signatures["pose"]:
        raise AssertionError(f"{stage}: source properties or non-owned constraints changed")


def _assert_schema3_inventory(inventory):
    if inventory["schema"] != limb_ik.ROLL_DECOUPLED_SCHEMA:
        raise AssertionError(f"Rebuild produced schema {inventory['schema']}, not schema 3")
    if set(inventory["rigs"]) != EXPECTED_KEYS:
        raise AssertionError(f"Schema 3 limb set is incomplete: {sorted(inventory['rigs'])}")
    for key, rig in inventory["rigs"].items():
        for role in ("mch_upper", "mch_lower", "ori_upper", "ori_lower"):
            if rig.get(role) is None:
                raise AssertionError(f"Schema 3 {key} is missing {role}")


def _owned_residue(armature):
    registry_records = []
    named_constraints = []
    for pose_bone in armature.pose.bones:
        registry = limb_ik._constraint_registry(pose_bone, strict=False)
        for name, record in registry.items():
            if isinstance(record, dict) and record.get("owner") == limb_ik.OWNER_VALUE:
                registry_records.append((pose_bone.name, name))
        for constraint in pose_bone.constraints:
            if constraint.name.startswith("CDLimbIK_"):
                named_constraints.append((pose_bone.name, constraint.name))
    expected_helper_names = {
        limb_ik.LIMB_SPEC[kind][role].format(side=side)
        for kind, side in EXPECTED_KEYS
        for role in ("mch_upper", "mch_lower", "ori_upper", "ori_lower")
    }
    return {
        "bones": tuple(
            bone.name
            for bone in armature.data.bones
            if bone.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        ),
        "named_mch_ori": tuple(sorted(expected_helper_names & set(armature.data.bones))),
        "registry_records": tuple(registry_records),
        "named_constraints": tuple(named_constraints),
        "objects": tuple(
            obj.name
            for obj in bpy.data.objects
            if obj.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        ),
        "meshes": tuple(
            mesh.name
            for mesh in bpy.data.meshes
            if mesh.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        ),
        "collections": tuple(
            collection.name
            for collection in bpy.data.collections
            if collection.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        ),
        "bone_collections": tuple(
            collection.name
            for collection in armature.data.collections
            if collection.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        ),
        "armature_id": armature.data.get(limb_ik.ARMATURE_ID_KEY, ""),
        "schema": armature.data.get(limb_ik.SCHEMA_KEY, 0),
    }


def _pack_matrix(matrix):
    return [float(value) for row in matrix for value in row]


def _unpack_matrix(values):
    if len(values) != 16:
        raise AssertionError("Portable baseline contains a malformed 4x4 matrix")
    return Matrix(tuple(tuple(values[row * 4 + column] for column in range(4)) for row in range(4)))


def _pack_endpoint_state(state):
    return {
        f"{key[0]}.{key[1]}": {
            "end_matrix": _pack_matrix(item["end_matrix"]),
            "root_head": tuple(float(value) for value in item["root_head"]),
            "lower_tail": tuple(float(value) for value in item["lower_tail"]),
            "end_head": tuple(float(value) for value in item["end_head"]),
        }
        for key, item in state.items()
    }


def _unpack_endpoint_state(state):
    result = {}
    for label, item in state.items():
        kind, side = label.split(".")
        result[(kind, side)] = {
            "end_matrix": _unpack_matrix(item["end_matrix"]),
            "root_head": Vector(item["root_head"]),
            "lower_tail": Vector(item["lower_tail"]),
            "end_head": Vector(item["end_head"]),
        }
    return result


def _portable_baseline(baseline, fingerprint):
    chain_names = {
        name for chain in probe.EXPECTED_CHAINS.values() for name in chain
    }
    return {
        "fingerprint": fingerprint,
        "artist_pose": {
            name: _pack_matrix(baseline["artist_pose"][name])
            for name in sorted(chain_names)
        },
        "schema2_pose": {
            name: _pack_matrix(baseline["schema2_pose"][name])
            for name in sorted(chain_names)
        },
        "schema2_endpoints": _pack_endpoint_state(baseline["schema2_endpoints"]),
        "old_twist": baseline["old_twist"],
        "repair": baseline["repair"],
    }


def _decode_portable_baseline(encoded, fingerprint):
    try:
        raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssertionError("Could not decode the portable artist baseline") from exc
    if payload.get("fingerprint") != fingerprint:
        raise AssertionError("Portable baseline was derived from a different input fingerprint")
    return {
        "artist_pose": {
            name: _unpack_matrix(matrix)
            for name, matrix in payload["artist_pose"].items()
        },
        "schema2_pose": {
            name: _unpack_matrix(matrix)
            for name, matrix in payload["schema2_pose"].items()
        },
        "schema2_endpoints": _unpack_endpoint_state(payload["schema2_endpoints"]),
        "old_twist": payload["old_twist"],
        "repair": payload["repair"],
    }


def _build_artist_baseline(path, fingerprint):
    armature, inventory, repair = _prepare_saved_schema2(path)
    source_names = _source_names(armature)
    signatures = {
        "edit": probe._edit_bone_signature(armature, source_names),
        "basis": probe._source_basis_signature(armature, source_names),
        "pose": probe._source_pose_signature(armature, source_names),
    }
    # Entering Armature Edit mode recreates Bone RNA wrappers.  Never retain
    # inventory Bone references across the strict edit/rest snapshot.
    inventory = limb_ik._validate_inventory(armature)
    schema2_pose = _matrix_map(armature, source_names)
    schema2_endpoints = _capture_endpoint_state(armature, inventory)
    result = bpy.ops.character_designer.limb_ik_remove()
    settings = bpy.context.window_manager.character_designer_limb_ik
    if result != {"FINISHED"}:
        raise AssertionError(f"Baseline in-memory Remove failed: {result}; {settings.last_message}")
    _settle(armature)
    artist_pose = _matrix_map(armature, source_names)
    artist_endpoints = {
        key: {
            "end_matrix": artist_pose[chain[2]],
            "root_head": Vector(armature.pose.bones[chain[0]].head),
            "lower_tail": Vector(armature.pose.bones[chain[1]].tail),
            "end_head": Vector(armature.pose.bones[chain[2]].head),
        }
        for key, chain in probe.EXPECTED_CHAINS.items()
    }
    _assert_source_static("baseline Remove", armature, source_names, signatures)
    old_twist = _roll_metrics(artist_pose, schema2_pose)
    _assert_schema2_twist(old_twist)
    if _fingerprint(path) != fingerprint:
        raise AssertionError("Input Blend changed while deriving the artist baseline")
    return {
        "source_names": source_names,
        "signatures": signatures,
        "artist_pose": artist_pose,
        "schema2_pose": schema2_pose,
        "schema2_endpoints": schema2_endpoints,
        "artist_endpoints": artist_endpoints,
        "old_twist": old_twist,
        "repair": repair,
    }


def _run_migration(path, fingerprint, baseline):
    armature, inventory, repair = _prepare_saved_schema2(path)
    source_names = _source_names(armature)
    signatures = {
        "edit": probe._edit_bone_signature(armature, source_names),
        "basis": probe._source_basis_signature(armature, source_names),
        "pose": probe._source_pose_signature(armature, source_names),
    }
    protected_before = real_x._protected_asset_fingerprints()
    schema2_pose = _matrix_map(armature, source_names)
    for name in baseline["schema2_pose"]:
        _assert_matrix(
            f"reopened schema-2 evaluated pose {name}",
            schema2_pose[name],
            baseline["schema2_pose"][name],
        )
    schema2_endpoints = _capture_endpoint_state(armature, inventory)

    analyze = bpy.ops.character_designer.limb_ik_analyze()
    settings = bpy.context.window_manager.character_designer_limb_ik
    if analyze != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {analyze}; {settings.last_message}")
    rebuild_probe._set_fixed_defaults(settings)
    rebuilt = bpy.ops.character_designer.limb_ik_rebuild()
    if rebuilt != {"FINISHED"}:
        raise AssertionError(f"Schema-2 -> schema-3 Rebuild failed: {rebuilt}; {settings.last_message}")
    _settle(armature)
    first_inventory = limb_ik._validate_inventory(armature)
    _assert_schema3_inventory(first_inventory)
    limb_ik._removal_resources(bpy.context, armature, first_inventory)
    _assert_source_static("schema-3 migration", armature, source_names, signatures)
    first_inventory = limb_ik._validate_inventory(armature)

    first_pose = _matrix_map(armature, source_names)
    first_roll = _roll_metrics(baseline["artist_pose"], first_pose)
    _assert_roll_clean("schema-3 source", first_roll)
    first_alignment = _alignment_metrics(armature, first_inventory)
    ori_rest = _ori_rest_metrics(armature, first_inventory)
    first_ori_pose = _capture_unconstrained_ori(armature, first_inventory)
    first_ori_roll = _ori_baseline_metrics(baseline["artist_pose"], first_ori_pose)
    _assert_roll_clean("schema-3 ORI baseline", first_ori_roll)
    first_endpoints = _capture_endpoint_state(armature, first_inventory)
    endpoint_preservation = _endpoint_comparison(
        schema2_endpoints,
        first_endpoints,
        "schema-2 -> schema-3",
    )
    first_stable = _capture_stable_state(armature, first_inventory)

    repeat_results = []
    previous_state = first_stable
    for index in (1, 2):
        result = bpy.ops.character_designer.limb_ik_rebuild()
        if result != {"FINISHED"}:
            raise AssertionError(
                f"Same-schema Rebuild {index} failed: {result}; {settings.last_message}"
            )
        _settle(armature)
        repeat_inventory = limb_ik._validate_inventory(armature)
        _assert_schema3_inventory(repeat_inventory)
        limb_ik._removal_resources(bpy.context, armature, repeat_inventory)
        _assert_source_static(f"same-schema Rebuild {index}", armature, source_names, signatures)
        repeat_inventory = limb_ik._validate_inventory(armature)
        current_state = _capture_stable_state(armature, repeat_inventory)
        drift = _stable_comparison(
            previous_state,
            current_state,
            f"same-schema Rebuild {index}",
        )
        current_pose = _matrix_map(armature, source_names)
        roll = _roll_metrics(baseline["artist_pose"], current_pose)
        _assert_roll_clean(f"same-schema Rebuild {index} source", roll)
        alignment = _alignment_metrics(armature, repeat_inventory)
        ori_pose = _capture_unconstrained_ori(armature, repeat_inventory)
        ori_roll = _ori_baseline_metrics(baseline["artist_pose"], ori_pose)
        _assert_roll_clean(f"same-schema Rebuild {index} ORI baseline", ori_roll)
        repeat_results.append(
            {
                "index": index,
                "drift": drift,
                "roll": roll,
                "ori_roll": ori_roll,
                "alignment": alignment,
            }
        )
        previous_state = current_state

    final_inventory = limb_ik._validate_inventory(armature)
    final_endpoints = _capture_endpoint_state(armature, final_inventory)
    repeat_endpoint_preservation = _endpoint_comparison(
        first_endpoints,
        final_endpoints,
        "two repeated Rebuilds",
    )
    removed = bpy.ops.character_designer.limb_ik_remove()
    if removed != {"FINISHED"}:
        raise AssertionError(f"Final Remove failed: {removed}; {settings.last_message}")
    _settle(armature)
    _assert_source_static("final Remove", armature, source_names, signatures)
    removed_pose = _matrix_map(armature, source_names)
    remove_return = {}
    for name in baseline["artist_pose"]:
        remove_return[name] = _assert_matrix(
            f"final Remove artist pose {name}",
            removed_pose[name],
            baseline["artist_pose"][name],
        )
    residue = _owned_residue(armature)
    if any(
        value
        for key, value in residue.items()
        if key not in {"schema"}
    ) or residue["schema"]:
        raise AssertionError(f"Final Remove left owned MCH/ORI/constraint residue: {residue}")
    protected_after = real_x._protected_asset_fingerprints()
    if protected_after != protected_before:
        raise AssertionError("Migration/Rebuild/Remove changed a protected asset")
    if _fingerprint(path) != fingerprint:
        raise AssertionError("Input Blend changed during migration acceptance")
    return {
        "repair": repair,
        "schema": first_inventory["schema"],
        "source_roll": first_roll,
        "ori_baseline_roll": first_ori_roll,
        "ori_rest": ori_rest,
        "alignment": first_alignment,
        "endpoint_preservation": endpoint_preservation,
        "repeat_rebuilds": repeat_results,
        "repeat_endpoint_preservation": repeat_endpoint_preservation,
        "remove_return_max": {
            field: max(item[field] for item in remove_return.values())
            for field in ("position", "rotation_degrees", "scale")
        },
        "residue": residue,
        "protected_assets": protected_after,
    }


def main():
    mode, path, encoded_baseline = _arguments()
    fingerprint_before = _fingerprint(path)
    character_designer.register()
    if mode == "baseline":
        baseline = _build_artist_baseline(path, fingerprint_before)
        portable = _portable_baseline(baseline, fingerprint_before)
        encoded = base64.urlsafe_b64encode(
            json.dumps(portable, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).decode("ascii")
        if _fingerprint(path) != fingerprint_before:
            raise AssertionError("Input Blend changed during baseline process")
        print("REAL_X_SCHEMA3_BASELINE_BASE64=" + encoded)
        print("REAL_X_SCHEMA3_BASELINE_JSON=" + json.dumps({
            "input": str(path),
            "fingerprint": fingerprint_before,
            "schema2_direct_ik_twist": baseline["old_twist"],
            "collection_repair": baseline["repair"],
        }, sort_keys=True))
        print("PASS real-X schema2 clean-artist baseline (input Blend unchanged)")
        return

    baseline = _decode_portable_baseline(encoded_baseline, fingerprint_before)
    _assert_schema2_twist(baseline["old_twist"])
    migration_result = _run_migration(path, fingerprint_before, baseline)
    fingerprint_after = _fingerprint(path)
    if fingerprint_after != fingerprint_before:
        raise AssertionError(
            f"Input Blend fingerprint changed: {fingerprint_before} -> {fingerprint_after}"
        )
    payload = {
        "input": str(path),
        "fingerprint_before": fingerprint_before,
        "fingerprint_after": fingerprint_after,
        "baseline_collection_repair": baseline["repair"],
        "schema2_direct_ik_twist": baseline["old_twist"],
        "migration": migration_result,
        "thresholds": {
            "alignment_min": ALIGNMENT_MIN,
            "axial_roll_degrees_max": ROLL_LIMIT_DEGREES,
            "transported_xz_dot_min": TRANSPORT_DOT_MIN,
            "old_arm_direct_ik_twist_degrees_min": OLD_ARM_TWIST_MIN_DEGREES,
        },
    }
    print("REAL_X_SCHEMA3_ROLL_ACCEPTANCE_JSON=" + json.dumps(payload, sort_keys=True))
    print(
        "PASS real-X schema2->schema3 roll-decoupling + repeat-Rebuild + Remove "
        "(input Blend unchanged)"
    )


if __name__ == "__main__":
    main()
