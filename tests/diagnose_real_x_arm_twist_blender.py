"""Read-only real-X ARM Default(+Y) Rebuild twist diagnostic.

Run in a disposable Blender background process.  The script opens the supplied
Blend file, never saves it, applies Analyze -> Default Direction for both arms
-> Rebuild in memory, and emits one JSON payload with evaluated pose-frame and
deformation-frame measurements for upper_arm/forearm on L and R.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
TESTS_ROOT = PROJECT_ROOT / "tests"
for path in (ADDONS_ROOT, TESTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import character_designer
from character_designer import limb_ik
import probe_limb_ik_real_x_blender as probe
import probe_real_x_0292_rebuild_blender as repeat_probe
import test_real_x_pole_direction_migration_blender as migration


ARM_KEYS = (("ARM", "L"), ("ARM", "R"))
BONE_NAMES = ("upper_arm.L", "forearm.L", "upper_arm.R", "forearm.R")
AXIAL_180_TOLERANCE_DEGREES = 10.0


def _fingerprint(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "sha256": digest.hexdigest().upper(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _f(value):
    value = float(value)
    return 0.0 if abs(value) < 5.0e-14 else value


def _vector(value):
    return [_f(component) for component in value]


def _matrix(value):
    return [[_f(component) for component in row] for row in value]


def _canonical_quaternion(value):
    quat = Quaternion(value).normalized()
    parts = [quat.w, quat.x, quat.y, quat.z]
    for component in parts:
        if abs(component) <= 1.0e-14:
            continue
        if component < 0.0:
            parts = [-item for item in parts]
        break
    return Quaternion(parts)


def _quaternion(value):
    quat = _canonical_quaternion(value)
    return [_f(quat.w), _f(quat.x), _f(quat.y), _f(quat.z)]


def _rotation_quaternion(matrix):
    return _canonical_quaternion(matrix.to_3x3().normalized().to_quaternion())


def _axes(quat):
    return {
        "x": Vector(quat @ Vector((1.0, 0.0, 0.0))),
        "y": Vector(quat @ Vector((0.0, 1.0, 0.0))),
        "z": Vector(quat @ Vector((0.0, 0.0, 1.0))),
    }


def _wrap_degrees(value):
    wrapped = (float(value) + 180.0) % 360.0 - 180.0
    if wrapped <= -180.0 + 1.0e-10:
        return 180.0
    return wrapped


def _parallel_transport_roll_degrees(q_before, q_after):
    """Signed roll after removing the shortest swing from before-Y to after-Y.

    Bone-local +Y is Blender's longitudinal axis.  This frame method remains
    valid when Rebuild also changes the bend direction, unlike Euler channels
    or a bare quaternion angle.
    """
    before_axes = _axes(q_before)
    after_axes = _axes(q_after)
    before_y = before_axes["y"].normalized()
    after_y = after_axes["y"].normalized()
    axis_dot = max(-1.0, min(1.0, before_y.dot(after_y)))
    if axis_dot <= -1.0 + 1.0e-8:
        return {
            "defined": False,
            "reason": "longitudinal axes are antiparallel, so shortest-swing transport is ambiguous",
            "longitudinal_axis_dot": axis_dot,
        }
    swing = before_y.rotation_difference(after_y)
    transported_x = Vector(swing @ before_axes["x"])
    transported_z = Vector(swing @ before_axes["z"])
    transported_x -= after_y * transported_x.dot(after_y)
    transported_z -= after_y * transported_z.dot(after_y)
    after_x = Vector(after_axes["x"])
    after_z = Vector(after_axes["z"])
    after_x -= after_y * after_x.dot(after_y)
    after_z -= after_y * after_z.dot(after_y)
    for value in (transported_x, transported_z, after_x, after_z):
        value.normalize()
    radians = math.atan2(
        after_y.dot(transported_x.cross(after_x)),
        max(-1.0, min(1.0, transported_x.dot(after_x))),
    )
    degrees = _wrap_degrees(math.degrees(radians))
    return {
        "defined": True,
        "degrees": _f(degrees),
        "absolute_distance_from_180_degrees": _f(abs(abs(degrees) - 180.0)),
        "near_180": abs(abs(degrees) - 180.0) <= AXIAL_180_TOLERANCE_DEGREES,
        "longitudinal_axis_dot": _f(axis_dot),
        "longitudinal_axis_swing_degrees": _f(math.degrees(math.acos(axis_dot))),
        "transported_x_to_after_x_dot": _f(transported_x.dot(after_x)),
        "transported_z_to_after_z_dot": _f(transported_z.dot(after_z)),
    }


def _swing_twist_degrees(q_before, q_after):
    """Quaternion swing/twist decomposition about before-frame local +Y."""
    relative = _canonical_quaternion(q_before.conjugated() @ q_after)
    projected = Quaternion((relative.w, 0.0, relative.y, 0.0))
    if projected.magnitude <= 1.0e-12:
        return {
            "defined": False,
            "reason": "twist projection is singular",
            "relative_quaternion_wxyz": _quaternion(relative),
        }
    twist = projected.normalized()
    degrees = _wrap_degrees(math.degrees(2.0 * math.atan2(twist.y, twist.w)))
    return {
        "defined": True,
        "degrees": _f(degrees),
        "absolute_distance_from_180_degrees": _f(abs(abs(degrees) - 180.0)),
        "near_180": abs(abs(degrees) - 180.0) <= AXIAL_180_TOLERANCE_DEGREES,
        "relative_quaternion_wxyz": _quaternion(relative),
        "twist_quaternion_wxyz": _quaternion(twist),
    }


def _evaluated_armature(armature):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    return armature.evaluated_get(depsgraph)


def _bone_state(armature, evaluated, name):
    pose_bone = evaluated.pose.bones[name]
    rest_bone = armature.data.bones[name]
    pose_matrix = pose_bone.matrix.copy()
    rest_matrix = rest_bone.matrix_local.copy()
    deform_matrix = pose_matrix @ rest_matrix.inverted()
    pose_q = _rotation_quaternion(pose_matrix)
    rest_q = _rotation_quaternion(rest_matrix)
    deform_q = _rotation_quaternion(deform_matrix)
    pose_axes = _axes(pose_q)
    rest_relative_transport = _parallel_transport_roll_degrees(rest_q, pose_q)
    rest_relative_swing_twist = _swing_twist_degrees(rest_q, pose_q)
    return {
        "pose_matrix_armature": _matrix(pose_matrix),
        "pose_quaternion_wxyz": _quaternion(pose_q),
        "deform_matrix_pose_times_rest_inverse": _matrix(deform_matrix),
        "deform_quaternion_wxyz": _quaternion(deform_q),
        "rest_matrix_armature": _matrix(rest_matrix),
        "rest_quaternion_wxyz": _quaternion(rest_q),
        "pose_head_armature": _vector(pose_bone.head),
        "pose_tail_armature": _vector(pose_bone.tail),
        "pose_axes_armature": {key: _vector(value) for key, value in pose_axes.items()},
        "rest_to_pose_axial_roll_parallel_transport": rest_relative_transport,
        "rest_to_pose_twist_swing_decomposition": rest_relative_swing_twist,
    }


def _ik_state(armature, evaluated, inventory, side):
    key = ("ARM", side)
    rig = inventory["rigs"][key]
    upper_name, lower_name, _end_name = rig["chain"]
    upper = evaluated.pose.bones[upper_name]
    lower = evaluated.pose.bones[lower_name]
    pole = evaluated.pose.bones[rig["pole"].name]
    start = Vector(upper.head)
    joint = Vector(lower.head)
    end = Vector(lower.tail)
    chain_axis = end - start
    projection = start + chain_axis * (joint - start).dot(chain_axis) / chain_axis.length_squared
    bend = joint - projection
    pole_projection = Vector(pole.head) - projection
    pole_projection -= chain_axis * pole_projection.dot(chain_axis) / chain_axis.length_squared
    plus_y_projection = Vector((0.0, 1.0, 0.0))
    plus_y_projection -= chain_axis * plus_y_projection.dot(chain_axis) / chain_axis.length_squared
    bend_direction = bend.normalized() if bend.length > 1.0e-12 else Vector((0.0, 0.0, 0.0))
    pole_direction = pole_projection.normalized() if pole_projection.length > 1.0e-12 else Vector((0.0, 0.0, 0.0))
    expected_direction = plus_y_projection.normalized() if plus_y_projection.length > 1.0e-12 else Vector((0.0, 0.0, 0.0))
    constraints = []
    for constraint in armature.pose.bones[lower_name].constraints:
        if constraint.type == "IK":
            constraints.append({
                "name": constraint.name,
                "pole_angle_degrees": _f(math.degrees(float(constraint.pole_angle))),
                "target": constraint.target.name if constraint.target else "",
                "subtarget": constraint.subtarget,
                "pole_target": constraint.pole_target.name if constraint.pole_target else "",
                "pole_subtarget": constraint.pole_subtarget,
                "chain_count": int(constraint.chain_count),
                "influence": _f(constraint.influence),
                "mute": bool(constraint.mute),
            })
    saved = rig["pole"].get(limb_ik.POLE_DIRECTION_KEY)
    return {
        "chain": list(rig["chain"]),
        "saved_pole_direction": _vector(saved) if saved is not None else None,
        "pole_head_armature": _vector(pole.head),
        "start_armature": _vector(start),
        "joint_armature": _vector(joint),
        "end_armature": _vector(end),
        "chain_axis": _vector(chain_axis.normalized()),
        "bend_residual_length": _f(bend.length),
        "bend_direction": _vector(bend_direction),
        "bend_direction_y": _f(bend_direction.y),
        "bend_to_projected_plus_y_dot": _f(bend_direction.dot(expected_direction)),
        "pole_to_bend_dot": _f(pole_direction.dot(bend_direction)),
        "ik_constraints": constraints,
    }


def _snapshot(armature):
    evaluated = _evaluated_armature(armature)
    inventory = limb_ik._validate_inventory(armature)
    return {
        "bones": {name: _bone_state(armature, evaluated, name) for name in BONE_NAMES},
        "arms": {side: _ik_state(armature, evaluated, inventory, side) for side in ("L", "R")},
        "armature_matrix_world": _matrix(armature.matrix_world),
    }


def _bone_only_snapshot(armature):
    evaluated = _evaluated_armature(armature)
    return {
        "bones": {name: _bone_state(armature, evaluated, name) for name in BONE_NAMES},
        "armature_matrix_world": _matrix(armature.matrix_world),
    }


def _bone_comparison(before, after, name):
    before_state = before["bones"][name]
    after_state = after["bones"][name]
    q_before = Quaternion(before_state["pose_quaternion_wxyz"])
    q_after = Quaternion(after_state["pose_quaternion_wxyz"])
    q_deform_before = Quaternion(before_state["deform_quaternion_wxyz"])
    q_deform_after = Quaternion(after_state["deform_quaternion_wxyz"])
    pose_before = Matrix(before_state["pose_matrix_armature"])
    pose_after = Matrix(after_state["pose_matrix_armature"])
    deform_before = Matrix(before_state["deform_matrix_pose_times_rest_inverse"])
    deform_after = Matrix(after_state["deform_matrix_pose_times_rest_inverse"])
    relative_frame_q = _canonical_quaternion(q_before.conjugated() @ q_after)
    relative_deform_q = _canonical_quaternion(q_deform_after @ q_deform_before.conjugated())
    frame_rotation = q_before.rotation_difference(q_after)
    deformation_rotation = q_deform_before.rotation_difference(q_deform_after)
    head_before = Vector(before_state["pose_head_armature"])
    head_after = Vector(after_state["pose_head_armature"])
    tail_before = Vector(before_state["pose_tail_armature"])
    tail_after = Vector(after_state["pose_tail_armature"])
    return {
        "parallel_transport_axial_roll": _parallel_transport_roll_degrees(q_before, q_after),
        "swing_twist_about_before_local_y": _swing_twist_degrees(q_before, q_after),
        "shortest_pose_frame_rotation_degrees": _f(math.degrees(frame_rotation.angle)),
        "relative_pose_frame_quaternion_before_inverse_times_after_wxyz": _quaternion(relative_frame_q),
        "relative_pose_frame_rotation_matrix": _matrix(relative_frame_q.to_matrix()),
        "shortest_deformation_rotation_degrees": _f(math.degrees(deformation_rotation.angle)),
        "relative_deformation_quaternion_after_times_before_inverse_wxyz": _quaternion(relative_deform_q),
        "relative_deformation_matrix_after_times_before_inverse": _matrix(deform_after @ deform_before.inverted()),
        "relative_pose_matrix_before_inverse_times_after": _matrix(pose_before.inverted() @ pose_after),
        "head_shift": _vector(head_after - head_before),
        "head_shift_length": _f((head_after - head_before).length),
        "tail_shift": _vector(tail_after - tail_before),
        "tail_shift_length": _f((tail_after - tail_before).length),
        "absolute_rest_roll_before_parallel_transport_degrees": before_state[
            "rest_to_pose_axial_roll_parallel_transport"
        ].get("degrees"),
        "absolute_rest_roll_after_parallel_transport_degrees": after_state[
            "rest_to_pose_axial_roll_parallel_transport"
        ].get("degrees"),
    }


def _pole_angle_delta(before, after, side):
    before_constraints = before["arms"][side]["ik_constraints"]
    after_constraints = after["arms"][side]["ik_constraints"]
    before_angle = before_constraints[0]["pole_angle_degrees"] if len(before_constraints) == 1 else None
    after_angle = after_constraints[0]["pole_angle_degrees"] if len(after_constraints) == 1 else None
    return {
        "before_degrees": before_angle,
        "after_degrees": after_angle,
        "wrapped_delta_degrees": (
            _f(_wrap_degrees(after_angle - before_angle))
            if before_angle is not None and after_angle is not None
            else None
        ),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("Expected exactly one X.blend path after --")
    input_path = Path(args[0]).resolve()
    disk_before = _fingerprint(input_path)
    bpy.ops.wm.open_mainfile(filepath=str(input_path), load_ui=False)
    character_designer.register()
    armature = migration._find_real_armature()
    migration._mode_set(bpy.context, armature, "POSE")
    initial_inventory = limb_ik._validate_inventory(armature)
    if not set(ARM_KEYS).issubset(initial_inventory["rigs"]):
        raise AssertionError(f"Saved X does not contain both generated arm rigs: {sorted(initial_inventory['rigs'])}")

    source_rest_before = {
        name: _matrix(armature.data.bones[name].matrix_local)
        for name in BONE_NAMES
    }
    initial_saved_directions = {
        f"{kind}.{side}": (
            _vector(rig["pole_direction"])
            if rig["pole_direction"] is not None
            else None
        )
        for (kind, side), rig in sorted(initial_inventory["rigs"].items())
    }
    before = _snapshot(armature)

    # X currently has one known BoneCollection membership drift.  Repair only
    # that exact ownership fact in memory so the normal transactional Rebuild
    # preflight can run; this does not touch source rest/pose transforms.
    repair = repeat_probe._repair_known_collection_drift(armature, initial_inventory)

    analyze_result = bpy.ops.character_designer.limb_ik_analyze()
    settings = bpy.context.window_manager.character_designer_limb_ik
    if analyze_result != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {analyze_result}; {settings.last_message}")
    hydrated_directions = {
        f"{kind}.{side}": _vector(getattr(settings, probe.POLE_DIRECTION_PROPERTIES[(kind, side)]))
        for kind, side in sorted(initial_inventory["rigs"])
    }
    default_results = {}
    for key in ARM_KEYS:
        settings.selected_limb = probe.SELECTED_LIMBS[key]
        result = bpy.ops.character_designer.limb_ik_default_pole_direction()
        value = Vector(getattr(settings, probe.POLE_DIRECTION_PROPERTIES[key]))
        if result != {"FINISHED"} or (value - Vector((0.0, 1.0, 0.0))).length > 1.0e-9:
            raise AssertionError(f"ARM Default(+Y) failed for {key}: {result}, {tuple(value)}; {settings.last_message}")
        default_results[f"{key[0]}.{key[1]}"] = {
            "operator_result": sorted(result),
            "direction": _vector(value),
        }

    rebuild_result = bpy.ops.character_designer.limb_ik_rebuild()
    if rebuild_result != {"FINISHED"}:
        raise AssertionError(f"Rebuild failed: {rebuild_result}; {settings.last_message}")
    after = _snapshot(armature)
    source_rest_after = {
        name: _matrix(armature.data.bones[name].matrix_local)
        for name in BONE_NAMES
    }

    # Remove only after capturing the requested Rebuild result.  This gives a
    # clean source/FK baseline in the same disposable process and lets us tell
    # "Rebuild introduced a flip" apart from "the loaded saved rig was already
    # in that rolled state".  Nothing is written back to disk.
    remove_result = bpy.ops.character_designer.limb_ik_remove()
    if remove_result != {"FINISHED"}:
        raise AssertionError(f"Post-measurement Remove failed: {remove_result}; {settings.last_message}")
    unrigged = _bone_only_snapshot(armature)
    source_rest_unrigged = {
        name: _matrix(armature.data.bones[name].matrix_local)
        for name in BONE_NAMES
    }

    clean_analyze_result = bpy.ops.character_designer.limb_ik_analyze()
    if clean_analyze_result != {"FINISHED"}:
        raise AssertionError(f"Clean-source Analyze failed: {clean_analyze_result}; {settings.last_message}")
    for key in ARM_KEYS:
        settings.selected_limb = probe.SELECTED_LIMBS[key]
        clean_default_result = bpy.ops.character_designer.limb_ik_default_pole_direction()
        if clean_default_result != {"FINISHED"}:
            raise AssertionError(f"Clean-source ARM Default failed for {key}: {clean_default_result}; {settings.last_message}")
    clean_build_result = bpy.ops.character_designer.limb_ik_build_arm()
    if clean_build_result != {"FINISHED"}:
        raise AssertionError(f"Clean-source Build Arm failed: {clean_build_result}; {settings.last_message}")
    clean_build = _snapshot(armature)
    disk_after = _fingerprint(input_path)
    if disk_after != disk_before:
        raise AssertionError(f"Input X.blend changed on disk: {disk_before} -> {disk_after}")

    comparisons = {name: _bone_comparison(before, after, name) for name in BONE_NAMES}
    unrigged_to_before = {name: _bone_comparison(unrigged, before, name) for name in BONE_NAMES}
    unrigged_to_after = {name: _bone_comparison(unrigged, after, name) for name in BONE_NAMES}
    unrigged_to_clean_build = {name: _bone_comparison(unrigged, clean_build, name) for name in BONE_NAMES}
    pole_angles = {side: _pole_angle_delta(before, after, side) for side in ("L", "R")}
    near_180_bones = [
        name
        for name, comparison in comparisons.items()
        if comparison["parallel_transport_axial_roll"].get("near_180")
    ]
    payload = {
        "input": str(input_path),
        "blender_version": bpy.app.version_string,
        "addon_version": list(character_designer.bl_info["version"]),
        "disk_fingerprint_before": disk_before,
        "disk_fingerprint_after": disk_after,
        "disk_input_unchanged": disk_after == disk_before,
        "operation": {
            "analyze": sorted(analyze_result),
            "arm_defaults": default_results,
            "rebuild": sorted(rebuild_result),
            "last_message": settings.last_message,
            "repair_before_rebuild": repair,
            "initial_saved_directions": initial_saved_directions,
            "analyze_hydrated_directions": hydrated_directions,
        },
        "source_rest_matrices_unchanged": (
            source_rest_before == source_rest_after == source_rest_unrigged
        ),
        "measurement_definition": {
            "longitudinal_axis": "bone-local +Y (Blender head-to-tail axis)",
            "primary": "shortest-swing parallel transport of before local X to after local-Y plane, then signed angle to after local X around after local +Y",
            "cross_check": "quaternion swing/twist projection of inverse(before pose orientation) * after pose orientation onto before local +Y",
            "mesh_deformation": "pose_matrix * inverse(rest_matrix); relative deformation is after * inverse(before)",
            "near_180_threshold_degrees": AXIAL_180_TOLERANCE_DEGREES,
            "why_not_euler": "Euler channels and raw quaternion angle mix bend swing with axial roll and depend on rotation order",
        },
        "before": before,
        "after": after,
        "unrigged_source_baseline_after_in_memory_remove": unrigged,
        "clean_source_build_arm": clean_build,
        "comparison": comparisons,
        "comparison_unrigged_source_to_loaded_saved_rig": unrigged_to_before,
        "comparison_unrigged_source_to_after_rebuild": unrigged_to_after,
        "comparison_unrigged_source_to_clean_build_arm": unrigged_to_clean_build,
        "pole_angle_comparison": pole_angles,
        "near_180_bones_primary_measure": near_180_bones,
        "post_measurement_remove": sorted(remove_result),
        "clean_source_analyze": sorted(clean_analyze_result),
        "clean_source_build_arm_result": sorted(clean_build_result),
    }
    def compact_comparison(items):
        return {
            name: {
                "axial_roll_parallel_transport_degrees": value["parallel_transport_axial_roll"].get("degrees"),
                "axial_twist_quaternion_decomposition_degrees": value["swing_twist_about_before_local_y"].get("degrees"),
                "longitudinal_swing_degrees": value["parallel_transport_axial_roll"].get("longitudinal_axis_swing_degrees"),
                "shortest_pose_frame_rotation_degrees": value["shortest_pose_frame_rotation_degrees"],
                "relative_pose_quaternion_wxyz": value[
                    "relative_pose_frame_quaternion_before_inverse_times_after_wxyz"
                ],
                "relative_pose_rotation_matrix": value["relative_pose_frame_rotation_matrix"],
                "transported_x_dot": value["parallel_transport_axial_roll"].get("transported_x_to_after_x_dot"),
                "transported_z_dot": value["parallel_transport_axial_roll"].get("transported_z_to_after_z_dot"),
            }
            for name, value in items.items()
        }

    summary = {
        "disk_input_unchanged": disk_after == disk_before,
        "sha256": disk_after["sha256"],
        "source_rest_matrices_unchanged": payload["source_rest_matrices_unchanged"],
        "loaded_saved_to_after_rebuild": compact_comparison(comparisons),
        "unrigged_source_to_loaded_saved": compact_comparison(unrigged_to_before),
        "unrigged_source_to_after_rebuild": compact_comparison(unrigged_to_after),
        "unrigged_source_to_clean_build_arm": compact_comparison(unrigged_to_clean_build),
        "pose_quaternion_wxyz": {
            state_name: {
                name: state["bones"][name]["pose_quaternion_wxyz"]
                for name in BONE_NAMES
            }
            for state_name, state in (
                ("loaded_saved", before),
                ("after_rebuild", after),
                ("unrigged_source", unrigged),
                ("clean_build_arm", clean_build),
            )
        },
        "bend": {
            state_name: {
                side: {
                    "direction": state["arms"][side]["bend_direction"],
                    "y": state["arms"][side]["bend_direction_y"],
                    "to_projected_plus_y_dot": state["arms"][side]["bend_to_projected_plus_y_dot"],
                }
                for side in ("L", "R")
            }
            for state_name, state in (
                ("loaded_saved", before),
                ("after_rebuild", after),
                ("clean_build_arm", clean_build),
            )
        },
        "pole_angle_rebuild": pole_angles,
        "clean_build_pole_angles_degrees": {
            side: clean_build["arms"][side]["ik_constraints"][0]["pole_angle_degrees"]
            for side in ("L", "R")
        },
    }
    print("REAL_X_ARM_TWIST_SUMMARY_JSON=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print("REAL_X_ARM_TWIST_DIAGNOSTIC_JSON=" + json.dumps(payload, ensure_ascii=False, sort_keys=True))
    print("PASS read-only real-X ARM Default(+Y) Rebuild twist diagnostic")


if __name__ == "__main__":
    main()
