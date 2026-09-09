"""Blender 5.2 regressions for Limb IK Pole calibration and solver response."""

from __future__ import annotations

import math
import os
import sys
from types import SimpleNamespace

from mathutils import Matrix, Vector

import bpy


TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import test_limb_ik_blender as base


ROLL_CASES = (
    ("roll_zero", 0.0, False),
    ("roll_positive", 0.4, False),
    ("roll_quarter_turn", 1.57, False),
    ("roll_negative", -1.1, False),
    ("near_straight", 0.4, True),
)

POSITION_TOLERANCE = 2.0e-4
ROTATION_TOLERANCE = 2.0e-3
TARGET_TOLERANCE = 5.0e-4


def matrix_rotation_error(actual, expected):
    return actual.to_quaternion().rotation_difference(expected.to_quaternion()).angle


def assert_no_pop(armature, before, label):
    for name in ("upper_arm.L", "forearm.L"):
        pose_bone = armature.pose.bones[name]
        expected_matrix = before[name]
        position_error = (pose_bone.matrix.translation - expected_matrix.translation).length
        rotation_error = matrix_rotation_error(pose_bone.matrix, expected_matrix)
        if position_error > POSITION_TOLERANCE or rotation_error > ROTATION_TOLERANCE:
            raise AssertionError(
                f"{label} {name} popped after Build: "
                f"position={position_error:.6g}, rotation={rotation_error:.6g}"
            )


def run_case(label, roll, near_straight):
    base.reset_scene()
    armature = base.make_humanoid(
        near_straight=near_straight,
        include_right=False,
        roll_offset=roll,
    )
    before = {
        name: armature.pose.bones[name].matrix.copy()
        for name in ("upper_arm.L", "forearm.L")
    }
    expected_target_position = armature.pose.bones["hand.L"].head.copy()

    analyze_result, settings = base.analyze(armature)
    if analyze_result != {"FINISHED"}:
        raise AssertionError(f"{label}: Analyze failed: {settings.last_message}")
    settings.selected_limb = "LEFT_ARM"
    settings.left_arm_pole_direction = base.DEFAULT_POLE_DIRECTIONS["ARM"]
    if near_straight:
        obsolete = ("modeled bend", "roll fallback", "projected -local Z")
        if any(token in settings.last_message for token in obsolete):
            raise AssertionError(f"{label}: Analyze advertised obsolete Pole inference: {settings.last_message}")

    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(f"{label}: Build failed: {settings.last_message}")
    bpy.context.view_layer.update()

    target = armature.pose.bones["CTRL_hand_IK.L"]
    target_position_error = (target.head - expected_target_position).length
    if target_position_error > POSITION_TOLERANCE:
        raise AssertionError(
            f"{label}: target was not built at the wrist: {target_position_error:.6g}"
        )
    assert_no_pop(armature, before, label)
    base.assert_rest_pole_direction(
        armature,
        ("ARM", "L"),
        base.DEFAULT_POLE_DIRECTIONS["ARM"],
        f"{label} rest",
    )
    base.assert_pole_plane_alignment(armature, ("ARM", "L"), f"{label} after Build")

    endpoint_before = armature.pose.bones["forearm.L"].tail.copy()
    target_matrix = target.matrix.copy()
    target_matrix.translation += Vector((-0.08, 0.08, 0.04))
    target.matrix = target_matrix
    bpy.context.view_layer.update()

    moved_target = target.head.copy()
    moved_endpoint = armature.pose.bones["forearm.L"].tail.copy()
    if (moved_target - expected_target_position).length < 0.05:
        raise AssertionError(f"{label}: target manipulation did not take effect")
    if (moved_endpoint - endpoint_before).length < 0.02:
        raise AssertionError(f"{label}: IK chain did not respond to target manipulation")
    endpoint_error = (moved_endpoint - moved_target).length
    if endpoint_error > TARGET_TOLERANCE:
        raise AssertionError(
            f"{label}: IK endpoint did not follow target: {endpoint_error:.6g}"
        )
    base.assert_pole_plane_alignment(armature, ("ARM", "L"), f"{label} after target move")


def run_clamped_domain_regression():
    """The real-X failure: analytic-centered samples all miss +2.933 rad."""
    lower = -math.pi
    upper = math.pi
    analytic = -1.5863842657753
    optimum = 2.932971239089966

    class ClampedConstraint:
        def __init__(self):
            self._pole_angle = 0.0
            self.requested = []
            self.actual = []
            self.bl_rna = SimpleNamespace(
                properties={
                    "pole_angle": SimpleNamespace(hard_min=lower, hard_max=upper),
                }
            )

        @property
        def pole_angle(self):
            return self._pole_angle

        @pole_angle.setter
        def pole_angle(self, value):
            requested = float(value)
            actual = max(lower, min(upper, requested))
            self.requested.append(requested)
            self.actual.append(actual)
            self._pole_angle = actual

    def alignment(angle):
        return math.cos(float(angle) - optimum)

    legacy_actual = [
        max(lower, min(upper, analytic - math.pi + index * math.tau / 32))
        for index in range(32)
    ]
    legacy_best = max(alignment(angle) for angle in legacy_actual)
    if legacy_best >= 0.999:
        raise AssertionError(f"clamp-boundary fixture no longer exposes the legacy miss: {legacy_best}")
    if sum(abs(angle - lower) <= 1.0e-12 for angle in legacy_actual) < 2:
        raise AssertionError("legacy analytic-centered sweep did not collapse at the RNA hard minimum")

    constraint = ClampedConstraint()
    target = SimpleNamespace(matrix_basis=Matrix.Identity(4), head=Vector((1.0, 0.0, 0.0)))
    armature = SimpleNamespace(pose=SimpleNamespace(bones={"target": target}))
    plan = SimpleNamespace(
        pole_angle=analytic,
        target_name="target",
        start=Vector((0.0, 0.0, 0.0)),
        joint=Vector((1.0, 0.0, 0.0)),
        end=Vector((2.0, 0.0, 0.0)),
        chain=SimpleNamespace(side="L", kind="ARM"),
    )
    context = SimpleNamespace(view_layer=SimpleNamespace(update=lambda: None))
    original_measure = base.limb_ik._pole_alignment_measure
    base.limb_ik._pole_alignment_measure = lambda _armature, _plan: alignment(constraint.pole_angle)
    try:
        calibrated = base.limb_ik._calibrate_pole_angle(context, armature, plan, constraint)
    finally:
        base.limb_ik._pole_alignment_measure = original_measure

    calibrated_alignment = alignment(calibrated)
    if calibrated_alignment < 0.999999:
        raise AssertionError(
            f"fixed-domain calibration missed the legal optimum: angle={calibrated}, "
            f"alignment={calibrated_alignment}"
        )
    if abs(calibrated - optimum) > 1.0e-3:
        raise AssertionError(f"fixed-domain calibration chose {calibrated}, expected about {optimum}")
    if any(requested < lower - 1.0e-12 or requested > upper + 1.0e-12 for requested in constraint.requested):
        raise AssertionError("fixed-domain calibration submitted an angle outside the RNA hard range")
    if not any(abs(actual - upper) <= 1.0e-12 for actual in constraint.actual):
        raise AssertionError("fixed-domain calibration omitted the upper RNA boundary")


def run_exact_straight_refusal_case():
    base.reset_scene()
    armature = base.make_humanoid(near_straight=True, include_right=False)
    bpy.ops.object.mode_set(mode="EDIT")
    armature.data.edit_bones["upper_arm.L"].tail = (0.6, 0.0, 1.46)
    armature.data.edit_bones["forearm.L"].head = (0.6, 0.0, 1.46)
    bpy.ops.object.mode_set(mode="POSE")

    analyze_result, settings = base.analyze(armature)
    if analyze_result != {"FINISHED"}:
        raise AssertionError(f"exact_straight: Analyze failed: {settings.last_message}")
    settings.selected_limb = "LEFT_ARM"
    settings.left_arm_pole_direction = base.DEFAULT_POLE_DIRECTIONS["ARM"]
    if bpy.ops.character_designer.limb_ik_build_selected() != {"CANCELLED"}:
        raise AssertionError("exact_straight: Build must fail closed before creating an unstable Pole rig")
    if "effectively straight" not in settings.last_message or "small bend" not in settings.last_message:
        raise AssertionError(f"exact_straight: refusal is not actionable: {settings.last_message}")
    inventory = base.limb_ik._validate_inventory(armature)
    if inventory["rigs"] or inventory["bones"] or inventory["records"]:
        raise AssertionError("exact_straight: refused Build left generated data behind")


def main():
    base.ensure_registered()
    try:
        run_clamped_domain_regression()
        print("PASS clamped_domain_regression")
        for label, roll, near_straight in ROLL_CASES:
            run_case(label, roll, near_straight)
            print(f"PASS {label}")
        run_exact_straight_refusal_case()
        print("PASS exact_straight_refusal")
    finally:
        base.reset_scene()
        base.ensure_unregistered()
    print(f"PASS Limb IK Pole calibration {len(ROLL_CASES) + 2} cases")


if __name__ == "__main__":
    main()
