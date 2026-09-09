"""Read-only in-memory probe for additive Target rotation in Auto Align mode."""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Euler


TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import test_limb_ik_blender as base


limb_ik = base.limb_ik


def rotation_error(actual, expected):
    angle = actual.rotation_difference(expected).angle
    return abs(math.remainder(angle, math.tau))


def probe(build_method, selected_limb, key):
    base.reset_scene()
    armature = base.make_humanoid(
        name=f"AutoOffset{build_method}{selected_limb}",
        include_right=False,
        roll_offset=0.73,
    )
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = build_method
    settings.selected_limb = selected_limb
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if bpy.ops.character_designer.limb_ik_auto_align_target() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()

    rig = limb_ik._validate_inventory(armature)["rigs"][key]
    target = armature.pose.bones[rig["target"].name]
    end = armature.pose.bones[rig["chain"][2]]
    natural = end.matrix.copy()
    offset = end.constraints.new("COPY_ROTATION")
    offset.name = "AUTO_OFFSET_PROBE"
    offset.target = armature
    offset.subtarget = target.name
    offset.target_space = "LOCAL"
    offset.owner_space = "LOCAL"
    offset.mix_mode = "AFTER"
    target.rotation_mode = "XYZ"

    for axis in range(3):
        target.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        baseline = end.matrix.copy()
        values = [0.0, 0.0, 0.0]
        values[axis] = math.radians(17.0)
        target.rotation_euler = values
        bpy.context.view_layer.update()
        expected = baseline.to_quaternion() @ Euler(values, "XYZ").to_quaternion()
        print(
            "AUTO_OFFSET_PROBE",
            build_method,
            selected_limb,
            "XYZ"[axis],
            "position",
            (end.matrix.translation - baseline.translation).length,
            "rotation",
            rotation_error(end.matrix.to_quaternion(), expected),
            "magnitude",
            rotation_error(end.matrix.to_quaternion(), baseline.to_quaternion()),
        )
    end.constraints.remove(offset)
    target.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    print(
        "AUTO_OFFSET_RESTORE",
        build_method,
        selected_limb,
        (end.matrix.translation - natural.translation).length,
        rotation_error(end.matrix.to_quaternion(), natural.to_quaternion()),
    )


def main():
    base.ensure_registered()
    try:
        for case in (
            ("DIRECT_PREROLL", "LEFT_ARM", ("ARM", "L")),
            ("DIRECT_PREROLL", "LEFT_LEG", ("LEG", "L")),
            ("ROLL_DECOUPLED", "LEFT_ARM", ("ARM", "L")),
            ("ROLL_DECOUPLED", "LEFT_LEG", ("LEG", "L")),
        ):
            probe(*case)
    finally:
        base.reset_scene()


if __name__ == "__main__":
    main()
