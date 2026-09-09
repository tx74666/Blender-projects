"""Read-only comparison of X arm Pose roll between two saved .blend files."""

import json
import math
import os
import sys

import bpy
from mathutils import Vector


def _snapshot(path, experiment="baseline"):
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    armature = bpy.data.objects.get("CoshaRig")
    if armature is None or armature.type != "ARMATURE":
        raise AssertionError(f"CoshaRig is missing from {path}")
    bpy.context.view_layer.update()
    if experiment == "use_rotation":
        for side in ("L", "R"):
            lower = armature.pose.bones[f"forearm.{side}"]
            ik = next(constraint for constraint in lower.constraints if constraint.type == "IK" and constraint.chain_count == 2)
            ik.use_rotation = True
            if hasattr(ik, "orient_weight"):
                ik.orient_weight = 1.0
        bpy.context.view_layer.update()
    elif experiment != "baseline":
        raise AssertionError(f"Unknown experiment: {experiment}")
    result = {}
    for side in ("L", "R"):
        names = (f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
        bones = {}
        for name in names:
            pose_bone = armature.pose.bones[name]
            rotation = pose_bone.matrix.to_3x3().normalized()
            bones[name] = {
                "head": tuple(float(value) for value in pose_bone.head),
                "tail": tuple(float(value) for value in pose_bone.tail),
                "x": tuple(float(value) for value in rotation.col[0]),
                "y": tuple(float(value) for value in rotation.col[1]),
                "z": tuple(float(value) for value in rotation.col[2]),
                "quaternion": tuple(float(value) for value in rotation.to_quaternion()),
            }
        lower = armature.pose.bones[names[1]]
        ik = next((constraint for constraint in lower.constraints if constraint.type == "IK" and constraint.chain_count == 2), None)
        bones["ik"] = {
            "pole_angle": None if ik is None else float(ik.pole_angle),
            "pole_subtarget": "" if ik is None else ik.pole_subtarget,
        }
        result[side] = bones
    return result


def _signed_twist(reference, current):
    old_y = Vector(reference["y"]).normalized()
    new_y = Vector(current["y"]).normalized()
    swing = old_y.rotation_difference(new_y)
    expected_x = swing @ Vector(reference["x"])
    actual_x = Vector(current["x"])
    expected_x -= new_y * expected_x.dot(new_y)
    actual_x -= new_y * actual_x.dot(new_y)
    if min(expected_x.length, actual_x.length) <= 1.0e-9:
        raise AssertionError("Cannot measure arm axial twist")
    expected_x.normalize()
    actual_x.normalize()
    return math.atan2(new_y.dot(expected_x.cross(actual_x)), expected_x.dot(actual_x))


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) not in {2, 3}:
        raise SystemExit("Expected: reference.blend current.blend [baseline|use_rotation]")
    reference_path, current_path = map(os.path.abspath, args[:2])
    experiment = args[2] if len(args) == 3 else "baseline"
    reference = _snapshot(reference_path)
    current = _snapshot(current_path, experiment)
    comparison = {}
    for side in ("L", "R"):
        comparison[side] = {
            "ik_reference": reference[side]["ik"],
            "ik_current": current[side]["ik"],
            "bones": {},
        }
        for name in (f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}"):
            angle = _signed_twist(reference[side][name], current[side][name])
            comparison[side]["bones"][name] = {
                "axial_twist_degrees": math.degrees(angle),
                "reference": reference[side][name],
                "current": current[side][name],
            }
    print("REAL_X_ARM_TWIST_JSON=" + json.dumps({"experiment": experiment, "comparison": comparison}, sort_keys=True))


if __name__ == "__main__":
    main()
