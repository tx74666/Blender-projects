"""Read-only real-X direct-IK frame/root-cause probe.

The probe starts from the source skeleton in memory, builds both arms with the
fixed +Y Pole default, inspects the exact Blender IK settings, and sweeps Pole
Angle with use_rotation off/on.  It demonstrates whether one direct deform-chain
IK constraint can simultaneously keep the elbow behind and avoid axial frame
roll.  The input Blend is never saved.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT / "addons", PROJECT_ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import character_designer
from character_designer import limb_ik
import diagnose_real_x_arm_twist_blender as twist
import probe_limb_ik_real_x_blender as probe
import probe_real_x_0292_rebuild_blender as repeat_probe
import test_real_x_pole_direction_migration_blender as migration


ARM_KEYS = (("ARM", "L"), ("ARM", "R"))


def _f(value):
    value = float(value)
    return 0.0 if abs(value) < 5.0e-12 else value


def _vector(value):
    return [_f(component) for component in value]


def _signed_angle_degrees(reference, target, axis):
    reference = Vector(reference).normalized()
    target = Vector(target).normalized()
    axis = Vector(axis).normalized()
    return _f(math.degrees(math.atan2(axis.dot(reference.cross(target)), reference.dot(target))))


def _arm_metrics(armature, baseline, side):
    evaluated = twist._evaluated_armature(armature)
    upper_name = f"upper_arm.{side}"
    lower_name = f"forearm.{side}"
    upper = evaluated.pose.bones[upper_name]
    lower = evaluated.pose.bones[lower_name]
    start = Vector(upper.head)
    joint = Vector(lower.head)
    end = Vector(lower.tail)
    chain = end - start
    projection = start + chain * (joint - start).dot(chain) / chain.length_squared
    bend = joint - projection
    expected = Vector((0.0, 1.0, 0.0))
    expected -= chain * expected.dot(chain) / chain.length_squared
    bend.normalize()
    expected.normalize()
    bones = {}
    for name in (upper_name, lower_name):
        before_q = Quaternion(baseline["bones"][name]["pose_quaternion_wxyz"])
        after_q = twist._rotation_quaternion(evaluated.pose.bones[name].matrix)
        roll = twist._parallel_transport_roll_degrees(before_q, after_q)
        cross = twist._swing_twist_degrees(before_q, after_q)
        bones[name] = {
            "roll_degrees": _f(roll["degrees"]),
            "twist_crosscheck_degrees": _f(cross["degrees"]),
            "longitudinal_swing_degrees": _f(roll["longitudinal_axis_swing_degrees"]),
            "transported_x_dot": _f(roll["transported_x_to_after_x_dot"]),
            "quaternion_wxyz": twist._quaternion(after_q),
        }
    return {
        "bend_to_projected_plus_y_dot": _f(bend.dot(expected)),
        "bend_direction": _vector(bend),
        "bend_signed_angle_from_projected_plus_y_degrees": _signed_angle_degrees(expected, bend, chain),
        "max_abs_roll_degrees": max(abs(value["roll_degrees"]) for value in bones.values()),
        "bones": bones,
    }


def _constraint_settings(constraint):
    names = (
        "chain_count",
        "pole_angle",
        "use_location",
        "use_rotation",
        "use_tail",
        "use_stretch",
        "weight",
        "orient_weight",
        "iterations",
        "ik_type",
        "reference_axis",
        "target_space",
        "owner_space",
        "influence",
        "mute",
    )
    result = {}
    for name in names:
        if not hasattr(constraint, name):
            continue
        value = getattr(constraint, name)
        if name == "pole_angle":
            result["pole_angle_degrees"] = _f(math.degrees(float(value)))
        elif isinstance(value, float):
            result[name] = _f(value)
        else:
            result[name] = value
    result.update({
        "target": constraint.target.name if constraint.target else "",
        "subtarget": constraint.subtarget,
        "pole_target": constraint.pole_target.name if constraint.pole_target else "",
        "pole_subtarget": constraint.pole_subtarget,
    })
    return result


def _pose_ik_settings(pose_bone):
    names = (
        "rotation_mode",
        "lock_ik_x",
        "lock_ik_y",
        "lock_ik_z",
        "use_ik_limit_x",
        "use_ik_limit_y",
        "use_ik_limit_z",
        "ik_stiffness_x",
        "ik_stiffness_y",
        "ik_stiffness_z",
        "ik_rotation_weight",
        "ik_linear_weight",
    )
    result = {}
    for name in names:
        if hasattr(pose_bone, name):
            value = getattr(pose_bone, name)
            result[name] = _f(value) if isinstance(value, float) else value
    return result


def _roll_free_candidate_frame(armature, baseline, name):
    """Keep the solved head-tail/Y axis but parallel-transport the source frame."""
    evaluated = twist._evaluated_armature(armature)
    pose_bone = evaluated.pose.bones[name]
    source_q = Quaternion(baseline["bones"][name]["pose_quaternion_wxyz"]).normalized()
    solved_q = twist._rotation_quaternion(pose_bone.matrix)
    source_y = source_q @ Vector((0.0, 1.0, 0.0))
    solved_y = solved_q @ Vector((0.0, 1.0, 0.0))
    swing = source_y.rotation_difference(solved_y)
    candidate_q = twist._canonical_quaternion(swing @ source_q)
    candidate_matrix = candidate_q.to_matrix().to_4x4()
    candidate_matrix.translation = Vector(pose_bone.head)
    candidate_roll = twist._parallel_transport_roll_degrees(source_q, candidate_q)
    solved_to_candidate = twist._swing_twist_degrees(solved_q, candidate_q)
    candidate_y = candidate_q @ Vector((0.0, 1.0, 0.0))
    return {
        "pose_matrix_armature": twist._matrix(candidate_matrix),
        "pose_quaternion_wxyz": twist._quaternion(candidate_q),
        "source_to_candidate_axial_roll_degrees": _f(candidate_roll["degrees"]),
        "source_to_candidate_longitudinal_swing_degrees": _f(
            candidate_roll["longitudinal_axis_swing_degrees"]
        ),
        "solved_to_candidate_local_y_correction_degrees": _f(
            solved_to_candidate["degrees"]
        ),
        "candidate_y_to_solved_y_dot": _f(candidate_y.normalized().dot(solved_y.normalized())),
        "head": _vector(pose_bone.head),
        "tail": _vector(pose_bone.tail),
    }


def _summarize_candidate(angle_degrees, metrics):
    return {
        "pole_angle_degrees": _f(angle_degrees),
        "bend_dot": metrics["bend_to_projected_plus_y_dot"],
        "bend_angle_degrees": metrics["bend_signed_angle_from_projected_plus_y_degrees"],
        "max_abs_roll_degrees": metrics["max_abs_roll_degrees"],
        "upper_roll_degrees": next(value["roll_degrees"] for name, value in metrics["bones"].items() if "upper_arm" in name),
        "forearm_roll_degrees": next(value["roll_degrees"] for name, value in metrics["bones"].items() if "forearm" in name),
    }


def _sweep(armature, baseline, side, constraint, use_rotation):
    constraint.use_rotation = bool(use_rotation)
    bpy.context.view_layer.update()
    records = []
    for angle in range(-180, 181, 2):
        constraint.pole_angle = math.radians(angle)
        bpy.context.view_layer.update()
        metrics = _arm_metrics(armature, baseline, side)
        records.append((float(angle), metrics))
    coarse_best = max(records, key=lambda item: item[1]["bend_to_projected_plus_y_dot"])[0]
    for index in range(-40, 41):
        angle = coarse_best + index * 0.05
        if angle < -180.0 or angle > 180.0:
            continue
        constraint.pole_angle = math.radians(angle)
        bpy.context.view_layer.update()
        records.append((angle, _arm_metrics(armature, baseline, side)))

    best_bend = max(records, key=lambda item: item[1]["bend_to_projected_plus_y_dot"])
    best_roll = min(records, key=lambda item: item[1]["max_abs_roll_degrees"])
    bend_feasible = [item for item in records if item[1]["bend_to_projected_plus_y_dot"] >= 0.999]
    roll_feasible = [item for item in records if item[1]["max_abs_roll_degrees"] <= 5.0]
    best_roll_with_bend = min(bend_feasible, key=lambda item: item[1]["max_abs_roll_degrees"]) if bend_feasible else None
    best_bend_with_roll = max(roll_feasible, key=lambda item: item[1]["bend_to_projected_plus_y_dot"]) if roll_feasible else None
    return {
        "use_rotation": bool(use_rotation),
        "samples": len(records),
        "best_bend": _summarize_candidate(*best_bend),
        "best_no_roll": _summarize_candidate(*best_roll),
        "best_no_roll_among_bend_dot_ge_0_999": (
            _summarize_candidate(*best_roll_with_bend) if best_roll_with_bend else None
        ),
        "best_bend_among_max_abs_roll_le_5deg": (
            _summarize_candidate(*best_bend_with_roll) if best_bend_with_roll else None
        ),
        "simultaneous_bend_dot_ge_0_999_and_roll_le_5deg_exists": bool(
            bend_feasible and any(item[1]["max_abs_roll_degrees"] <= 5.0 for item in bend_feasible)
        ),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("Expected exactly one X.blend path after --")
    path = Path(args[0]).resolve()
    disk_before = twist._fingerprint(path)
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    character_designer.register()
    armature = migration._find_real_armature()
    migration._mode_set(bpy.context, armature, "POSE")
    initial_inventory = limb_ik._validate_inventory(armature)
    repair = repeat_probe._repair_known_collection_drift(armature, initial_inventory)
    remove = bpy.ops.character_designer.limb_ik_remove()
    if remove != {"FINISHED"}:
        settings = bpy.context.window_manager.character_designer_limb_ik
        raise AssertionError(f"Remove failed: {remove}; {settings.last_message}")
    baseline = twist._bone_only_snapshot(armature)

    rest_geometry = {}
    for _kind, side in ARM_KEYS:
        upper = armature.data.bones[f"upper_arm.{side}"]
        lower = armature.data.bones[f"forearm.{side}"]
        start = Vector(upper.head_local)
        joint = Vector(lower.head_local)
        end = Vector(lower.tail_local)
        chain = end - start
        projection = start + chain * (joint - start).dot(chain) / chain.length_squared
        rest_bend = joint - projection
        plus_y = Vector((0.0, 1.0, 0.0))
        plus_y -= chain * plus_y.dot(chain) / chain.length_squared
        rest_geometry[side] = {
            "start": _vector(start),
            "joint": _vector(joint),
            "end": _vector(end),
            "rest_bend_direction": _vector(rest_bend.normalized()),
            "projected_plus_y_direction": _vector(plus_y.normalized()),
            "rest_bend_to_projected_plus_y_dot": _f(rest_bend.normalized().dot(plus_y.normalized())),
            "signed_plane_rotation_rest_bend_to_plus_y_degrees": _signed_angle_degrees(rest_bend, plus_y, chain),
            "upper_rest_x_axis": _vector(upper.matrix_local.to_quaternion() @ Vector((1.0, 0.0, 0.0))),
            "forearm_rest_x_axis": _vector(lower.matrix_local.to_quaternion() @ Vector((1.0, 0.0, 0.0))),
        }

    analyze = bpy.ops.character_designer.limb_ik_analyze()
    settings = bpy.context.window_manager.character_designer_limb_ik
    if analyze != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {analyze}; {settings.last_message}")
    for key in ARM_KEYS:
        settings.selected_limb = probe.SELECTED_LIMBS[key]
        default = bpy.ops.character_designer.limb_ik_default_pole_direction()
        if default != {"FINISHED"}:
            raise AssertionError(f"Default failed for {key}: {default}; {settings.last_message}")
    build = bpy.ops.character_designer.limb_ik_build_arm()
    if build != {"FINISHED"}:
        raise AssertionError(f"Build Arm failed: {build}; {settings.last_message}")

    inventory = limb_ik._validate_inventory(armature)
    result = {
        "disk_before": disk_before,
        "blender_version": bpy.app.version_string,
        "addon_version": list(character_designer.bl_info["version"]),
        "repair": repair,
        "rest_geometry": rest_geometry,
        "sides": {},
        "acceptance": {
            "elbow_behind": "bend dot projected Armature-local +Y >= 0.999",
            "no_axial_flip": "for both upper_arm and forearm, abs shortest-swing parallel-transport roll from unrigged source <= 5 degrees",
            "transverse_frame": "transported local X/Z dot >= cos(5 degrees) = 0.9961947",
        },
    }
    for _kind, side in ARM_KEYS:
        rig = inventory["rigs"][("ARM", side)]
        lower = armature.pose.bones[f"forearm.{side}"]
        constraint = next(
            constraint
            for _pose_bone, constraint, record in rig["entries"]
            if record["role"] == "IK"
        )
        original_angle = float(constraint.pole_angle)
        original_use_rotation = bool(constraint.use_rotation)
        original_metrics = _arm_metrics(armature, baseline, side)
        sweeps = {}
        for use_rotation in (False, True):
            sweeps[str(use_rotation).lower()] = _sweep(
                armature, baseline, side, constraint, use_rotation
            )
        constraint.use_rotation = original_use_rotation
        constraint.pole_angle = original_angle
        bpy.context.view_layer.update()
        result["sides"][side] = {
            "constraint": _constraint_settings(constraint),
            "upper_pose_ik_settings": _pose_ik_settings(armature.pose.bones[f"upper_arm.{side}"]),
            "forearm_pose_ik_settings": _pose_ik_settings(lower),
            "original_built_metrics": original_metrics,
            "roll_free_candidate_frames_same_solved_y_axis": {
                name: _roll_free_candidate_frame(armature, baseline, name)
                for name in (f"upper_arm.{side}", f"forearm.{side}")
            },
            "sweeps": sweeps,
        }
    disk_after = twist._fingerprint(path)
    result["disk_after"] = disk_after
    result["disk_input_unchanged"] = disk_after == disk_before
    if disk_after != disk_before:
        raise AssertionError(f"Input changed: {disk_before} -> {disk_after}")
    print("REAL_X_ARM_IK_FRAME_TRADEOFF_JSON=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("PASS read-only real-X direct-IK frame tradeoff probe")


if __name__ == "__main__":
    main()
