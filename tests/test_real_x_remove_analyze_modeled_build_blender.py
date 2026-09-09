"""Read-only real-X migration rehearsal: Remove -> Analyze -> Build All.

The input Blend is opened into a disposable Blender background process.  The
    script never saves.  It rebuilds all four limbs from X's fixed anatomical
    Pole axes, verifies pose/target and protected-asset invariants, and requires
the input file's SHA-256, mtime, and size to remain exact.
"""

from __future__ import annotations

import hashlib
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
import test_real_x_pole_direction_migration_blender as migration


EXPECTED_KEYS = migration.EXPECTED_KEYS
CHAIN_NAMES = probe.EXPECTED_CHAINS
POLE_FIELDS = probe.POLE_DIRECTION_PROPERTIES
POSITION_TOLERANCE = 5.0e-5
ROTATION_TOLERANCE = math.radians(0.05)
SCALE_TOLERANCE = 5.0e-5
ALIGNMENT_MIN = 0.999


def _digest(value):
    return hashlib.sha256(repr(value).encode("utf-8", "surrogatepass")).hexdigest().upper()


def _aggregate_digest(items):
    ordered = tuple(sorted(items.items()))
    return {"count": len(ordered), "sha256": _digest(ordered)}


def _shape_key_signature(mesh):
    keys = mesh.shape_keys
    if keys is None:
        return None
    animation = None
    if keys.animation_data is not None:
        action = keys.animation_data.action
        drivers = tuple(
            (
                curve.data_path,
                int(curve.array_index),
                curve.driver.type,
                curve.driver.expression,
                tuple(
                    (
                        variable.name,
                        variable.type,
                        tuple(
                            (
                                target.id.name_full if target.id else "",
                                target.data_path,
                                target.bone_target,
                                target.transform_type,
                                target.transform_space,
                            )
                            for target in variable.targets
                        ),
                    )
                    for variable in curve.driver.variables
                ),
            )
            for curve in keys.animation_data.drivers
        )
        action_signature = None
        if action is not None:
            action_signature = (
                action.name_full,
                tuple(
                    (
                        curve.data_path,
                        int(curve.array_index),
                        tuple(
                            (
                                tuple(float(value) for value in point.co),
                                tuple(float(value) for value in point.handle_left),
                                tuple(float(value) for value in point.handle_right),
                                point.interpolation,
                            )
                            for point in curve.keyframe_points
                        ),
                    )
                    for curve in action.fcurves
                ),
            )
        animation = (action_signature, drivers)
    return (
        keys.name_full,
        bool(keys.use_relative),
        float(keys.eval_time),
        keys.reference_key.name if keys.reference_key else "",
        probe._id_properties(keys),
        tuple(
            (
                block.name,
                block.relative_key.name if block.relative_key else "",
                float(block.value),
                float(block.slider_min),
                float(block.slider_max),
                bool(block.mute),
                block.interpolation,
                tuple(tuple(float(value) for value in point.co) for point in block.data),
            )
            for block in keys.key_blocks
        ),
        animation,
    )


def _protected_asset_fingerprints():
    """Fingerprint every non-Limb-IK object/mesh and all mesh deformation data."""
    protected_objects = [
        obj for obj in bpy.data.objects
        if obj.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    ]
    protected_meshes = [
        mesh for mesh in bpy.data.meshes
        if mesh.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    ]
    objects = {}
    for obj in protected_objects:
        parent = obj.parent
        objects[obj.name_full] = _digest(
            (
                obj.name_full,
                obj.type,
                obj.data.name_full if obj.data else "",
                parent.name_full if parent else "",
                obj.parent_type,
                obj.parent_bone,
                tuple(tuple(float(value) for value in row) for row in obj.matrix_world),
                tuple(tuple(float(value) for value in row) for row in obj.matrix_parent_inverse),
                probe._id_properties(obj),
                tuple(sorted(collection.name_full for collection in obj.users_collection)),
                tuple(
                    (
                        constraint.name,
                        constraint.type,
                        probe._writable_rna_signature(constraint),
                    )
                    for constraint in obj.constraints
                ),
                tuple(
                    (
                        modifier.name,
                        modifier.type,
                        probe._id_properties(modifier),
                        probe._writable_rna_signature(modifier),
                    )
                    for modifier in obj.modifiers
                ),
            )
        )

    meshes = {}
    shape_keys = {}
    for mesh in protected_meshes:
        signature = probe._mesh_data_signature(mesh)
        meshes[mesh.name_full] = _digest(signature)
        shape_keys[mesh.name_full] = _digest(_shape_key_signature(mesh))

    vertex_groups = {}
    for obj in protected_objects:
        if obj.type == "MESH":
            vertex_groups[obj.name_full] = _digest(probe._vertex_group_signature(obj))

    return {
        "objects": _aggregate_digest(objects),
        "meshes": _aggregate_digest(meshes),
        "shape_keys": {
            **_aggregate_digest(shape_keys),
            "datablocks": sum(bpy.data.meshes[name].shape_keys is not None for name in shape_keys),
        },
        "vertex_groups": {
            **_aggregate_digest(vertex_groups),
            "groups": sum(len(bpy.data.objects[name].vertex_groups) for name in vertex_groups),
        },
    }


def _pose_matrix(armature, name):
    return armature.pose.bones[name].matrix.copy()


def _rest_error(armature, name):
    pose = _pose_matrix(armature, name)
    rest = armature.data.bones[name].matrix_local
    return migration._matrix_errors(pose, rest)


def _all_source_rest_summary(armature, source_names):
    errors = {name: _rest_error(armature, name) for name in source_names}
    return {
        "max_position": max(value["position"] for value in errors.values()),
        "max_rotation_degrees": math.degrees(max(value["rotation"] for value in errors.values())),
        "max_scale": max(value["scale"] for value in errors.values()),
        "worst_position_bone": max(errors, key=lambda name: errors[name]["position"]),
        "worst_rotation_bone": max(errors, key=lambda name: errors[name]["rotation"]),
    }


def _limb_rest_summary(armature):
    result = {}
    for key, names in sorted(CHAIN_NAMES.items()):
        result[f"{key[0]}.{key[1]}"] = {
            name: {
                "position": _rest_error(armature, name)["position"],
                "rotation_degrees": math.degrees(_rest_error(armature, name)["rotation"]),
                "scale": _rest_error(armature, name)["scale"],
            }
            for name in names
        }
    return result


def _capture_matrices(armature, inventory):
    source_ends = {
        key: _pose_matrix(armature, rig["chain"][2])
        for key, rig in inventory["rigs"].items()
    }
    controls = {}
    for key, rig in inventory["rigs"].items():
        names = {rig["target"].name, rig["solver_target"].name}
        if rig["heel"] is not None:
            names.add(rig["heel"].name)
        controls[key] = {
            name: {
                "pose": _pose_matrix(armature, name),
                "world": armature.matrix_world @ _pose_matrix(armature, name),
                "rest": armature.data.bones[name].matrix_local.copy(),
                "basis": armature.pose.bones[name].matrix_basis.copy(),
            }
            for name in sorted(names)
        }
    return {"source_ends": source_ends, "controls": controls}


def _matrix_comparison(after, before):
    errors = migration._matrix_errors(after, before)
    return {
        "position": errors["position"],
        "rotation_degrees": math.degrees(errors["rotation"]),
        "scale": errors["scale"],
    }


def _compare_captured_matrices(before, after):
    result = {"source_ends": {}, "controls": {}}
    for key, old in before["source_ends"].items():
        result["source_ends"][f"{key[0]}.{key[1]}"] = _matrix_comparison(
            after["source_ends"][key], old
        )
    for key, old_controls in before["controls"].items():
        label = f"{key[0]}.{key[1]}"
        result["controls"][label] = {}
        if set(after["controls"][key]) != set(old_controls):
            raise AssertionError(f"Rebuild changed target/heel name inventory for {label}")
        for name, old in old_controls.items():
            new = after["controls"][key][name]
            result["controls"][label][name] = {
                field: _matrix_comparison(new[field], old[field])
                for field in ("pose", "world", "rest", "basis")
            }
    return result


def _assert_matrix_comparison(label, comparison):
    if (
        comparison["position"] > POSITION_TOLERANCE
        or math.radians(comparison["rotation_degrees"]) > ROTATION_TOLERANCE
        or comparison["scale"] > SCALE_TOLERANCE
    ):
        raise AssertionError(f"{label} changed: {comparison}")


def _assert_matrix_invariants(comparison):
    for key, errors in comparison["source_ends"].items():
        _assert_matrix_comparison(f"source Hand/Foot {key}", errors)
    for key, controls in comparison["controls"].items():
        for name, fields in controls.items():
            for field, errors in fields.items():
                _assert_matrix_comparison(f"{key} control {name} {field}", errors)


def _source_pose_snapshot(armature, source_names):
    return {name: _pose_matrix(armature, name) for name in source_names}


def _compare_source_pose(before, after, excluded):
    result = {}
    for name, old in before.items():
        if name not in excluded:
            result[name] = _matrix_comparison(after[name], old)
    return {
        "max_position": max(value["position"] for value in result.values()),
        "max_rotation_degrees": max(value["rotation_degrees"] for value in result.values()),
        "max_scale": max(value["scale"] for value in result.values()),
        "worst_position_bone": max(result, key=lambda name: result[name]["position"]),
        "worst_rotation_bone": max(result, key=lambda name: result[name]["rotation_degrees"]),
    }


def _anatomical_directions_from_defaults(armature, settings):
    result = {}
    for key in sorted(EXPECTED_KEYS):
        kind, side = key
        prefix = f"{'left' if side == 'L' else 'right'}_{kind.lower()}"
        names = tuple(getattr(settings, f"{prefix}_{role}") for role in ("upper", "lower", "end"))
        if names != CHAIN_NAMES[key]:
            raise AssertionError(f"Analyze chose {names} for {kind}.{side}, expected {CHAIN_NAMES[key]}")
        settings.selected_limb = probe.SELECTED_LIMBS[key]
        reset = bpy.ops.character_designer.limb_ik_default_pole_direction()
        if reset != {"FINISHED"}:
            raise AssertionError(f"Default Direction failed for {kind}.{side}: {reset}; {settings.last_message}")
        raw = Vector(getattr(settings, POLE_FIELDS[key]))
        expected_raw = probe.DEFAULT_POLE_DIRECTIONS[key]
        if (raw - expected_raw).length > 1.0e-9:
            raise AssertionError(
                f"{kind}.{side} Default Direction was not the fixed anatomical axis: "
                f"{tuple(raw)} != {tuple(expected_raw)}"
            )
        upper = armature.data.bones[names[0]]
        lower = armature.data.bones[names[1]]
        direction = limb_ik._project_perpendicular(raw, Vector(lower.tail_local) - Vector(upper.head_local))
        if direction.length <= limb_ik.EPSILON:
            raise AssertionError(f"{kind}.{side} anatomical direction is chain-parallel")
        direction.normalize()
        if kind == "ARM" and direction.y <= 0.95:
            raise AssertionError(f"{kind}.{side} elbow default is not behind at +Y: {tuple(direction)}")
        if kind == "LEG" and (direction.y >= -0.99 or abs(direction.x) > 0.01):
            raise AssertionError(f"{kind}.{side} knee default is not straight forward at -Y: {tuple(direction)}")
        result[key] = direction
    return result


def _json_pose_metrics(metrics):
    return dict(sorted(metrics.items()))


def _parse_input_path():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 1:
        raise AssertionError("Expected exactly one argument after --: the backup Blend path")
    path = Path(args[0]).resolve()
    if not path.is_file():
        raise AssertionError(f"Input Blend does not exist: {path}")
    return path


def main():
    path = _parse_input_path()
    disk_before = migration._file_fingerprint(path)
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    character_designer.register()

    armature = migration._find_real_armature()
    initial_inventory = limb_ik._validate_inventory(armature)
    old_semantics = migration._verify_saved_preconditions(armature, initial_inventory)
    source_names = tuple(
        bone.name for bone in armature.data.bones
        if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    )
    source_upper_lower = {
        name for names in CHAIN_NAMES.values() for name in names[:2]
    }
    source_before = _source_pose_snapshot(armature, source_names)
    before_pose_metrics = migration._limb_pose_metrics(armature, initial_inventory)
    before_limb_rest = _limb_rest_summary(armature)
    before_all_rest = _all_source_rest_summary(armature, source_names)
    matrices_before = _capture_matrices(armature, initial_inventory)
    assets_before = _protected_asset_fingerprints()

    migration._mode_set(bpy.context, armature, "POSE")
    remove_result = bpy.ops.character_designer.limb_ik_remove()
    settings = bpy.context.window_manager.character_designer_limb_ik
    if remove_result != {"FINISHED"}:
        raise AssertionError(f"Remove Generated Rig failed: {remove_result}; {settings.last_message}")
    if limb_ik._validate_inventory(armature)["rigs"]:
        raise AssertionError("Remove Generated Rig left an owned limb rig")

    analyze_result = bpy.ops.character_designer.limb_ik_analyze()
    if analyze_result != {"FINISHED"}:
        raise AssertionError(f"Analyze Rig failed: {analyze_result}; {settings.last_message}")
    anatomical_directions = _anatomical_directions_from_defaults(armature, settings)
    source_after_remove = _source_pose_snapshot(armature, source_names)
    after_remove_all_rest = _all_source_rest_summary(armature, source_names)
    after_remove_limb_rest = _limb_rest_summary(armature)

    build_result = bpy.ops.character_designer.limb_ik_build_all()
    if build_result != {"FINISHED"}:
        raise AssertionError(f"Build All failed: {build_result}; {settings.last_message}")
    final_inventory = limb_ik._validate_inventory(armature)
    if (
        final_inventory["schema"] != limb_ik.CURRENT_SCHEMA
        or set(final_inventory["rigs"]) != EXPECTED_KEYS
        or len(final_inventory["bones"]) != 37
        or len(final_inventory["records"]) != 47
    ):
        raise AssertionError(
            "Build All did not produce exact current-schema inventory "
            f"(schema={final_inventory['schema']}, rigs={tuple(sorted(final_inventory['rigs']))}, "
            f"bones={len(final_inventory['bones'])}, records={len(final_inventory['records'])})"
        )

    final_pose_metrics = migration._limb_pose_metrics(armature, final_inventory)
    final_limb_rest = _limb_rest_summary(armature)
    final_all_rest = _all_source_rest_summary(armature, source_names)
    source_final = _source_pose_snapshot(armature, source_names)
    matrices_final = _capture_matrices(armature, final_inventory)
    matrix_comparison = _compare_captured_matrices(matrices_before, matrices_final)
    _assert_matrix_invariants(matrix_comparison)

    unrelated_change = _compare_source_pose(source_before, source_final, source_upper_lower)
    if (
        unrelated_change["max_position"] > POSITION_TOLERANCE
        or math.radians(unrelated_change["max_rotation_degrees"]) > ROTATION_TOLERANCE
        or unrelated_change["max_scale"] > SCALE_TOLERANCE
    ):
        raise AssertionError(f"Remove/Analyze/Build changed an unrelated source bone: {unrelated_change}")

    for label, metric in final_pose_metrics.items():
        kind, side = label.split(".")
        key = (kind, side)
        if metric["alignment_dot"] <= ALIGNMENT_MIN:
            raise AssertionError(f"{label} bend/Pole alignment is low: {metric['alignment_dot']}")
        saved = Vector(final_inventory["rigs"][key]["pole"][limb_ik.POLE_DIRECTION_KEY]).normalized()
        if saved.dot(anatomical_directions[key]) <= 0.999999:
            raise AssertionError(f"{label} did not persist its fixed anatomical direction")
        if kind == "ARM" and saved.y <= 0.95:
            raise AssertionError(f"{label} elbow Pole is not behind at +Y: {tuple(saved)}")
        if kind == "LEG" and (saved.y >= -0.99 or abs(saved.x) > 0.01):
            raise AssertionError(f"{label} knee Pole is not straight forward at -Y: {tuple(saved)}")

    assets_final = _protected_asset_fingerprints()
    if assets_final != assets_before:
        raise AssertionError("Remove/Analyze/Build changed protected object/mesh/shape-key/vertex-group data")

    disk_after = migration._file_fingerprint(path)
    if disk_after != disk_before:
        raise AssertionError(f"Input Blend changed on disk: before={disk_before}, after={disk_after}")

    payload = {
        "input": str(path),
        "fingerprint_before": disk_before,
        "fingerprint_after": disk_after,
        "operators": {
            "remove": sorted(remove_result),
            "analyze": sorted(analyze_result),
            "build_all": sorted(build_result),
        },
        "saved_old_semantics": old_semantics,
        "anatomical_directions": {
            f"{key[0]}.{key[1]}": tuple(direction)
            for key, direction in sorted(anatomical_directions.items())
        },
        "pose_metrics_before": _json_pose_metrics(before_pose_metrics),
        "pose_metrics_after": _json_pose_metrics(final_pose_metrics),
        "source_pose_vs_rest": {
            "before_all_source": before_all_rest,
            "after_remove_analyze_all_source": after_remove_all_rest,
            "after_build_all_source": final_all_rest,
            "before_limbs": before_limb_rest,
            "after_remove_analyze_limbs": after_remove_limb_rest,
            "after_build_all_limbs": final_limb_rest,
        },
        "unrelated_source_pose_change": unrelated_change,
        "end_and_foot_matrix_change": matrix_comparison,
        "protected_asset_fingerprints_before": assets_before,
        "protected_asset_fingerprints_after": assets_final,
        "inventory_after": {
            "schema": final_inventory["schema"],
            "rigs": tuple(f"{key[0]}.{key[1]}" for key in sorted(final_inventory["rigs"])),
            "bones": len(final_inventory["bones"]),
            "constraints": len(final_inventory["records"]),
        },
    }
    print("REAL_X_REMOVE_ANALYZE_ANATOMICAL_BUILD_JSON=" + json.dumps(payload, sort_keys=True))
    print("PASS real-X Remove -> Analyze -> fixed anatomical directions -> Build All (read-only input)")


if __name__ == "__main__":
    main()
