"""Blender 5.2 regressions for aligned Hand/Foot IK Target rotation.

The suite creates disposable factory-startup armatures only.  It never opens,
edits, or saves the production ``X.blend`` file.

Run from the repository root with Blender 5.2::

    blender --background --factory-startup --python-exit-code 1 \
        --python tests/test_limb_ik_target_rotation_blender.py
"""

from __future__ import annotations

import math
import os
import sys
import traceback

import bpy
from mathutils import Euler, Vector


TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import test_limb_ik_blender as base


limb_ik = base.limb_ik

BUILD_METHODS = ("DIRECT_PREROLL", "ROLL_DECOUPLED")
LIMB_KEYS = (
    ("ARM", "L"),
    ("ARM", "R"),
    ("LEG", "L"),
    ("LEG", "R"),
)
ANGLE = math.radians(17.0)
POSITION_TOLERANCE = 2.5e-4
ROTATION_TOLERANCE = 3.0e-3
CHANNEL_TOLERANCE = 2.0e-6


def _rotation_error(actual, expected):
    """Return the shortest angular difference for Matrix or Quaternion input."""

    actual_quaternion = (
        actual.to_quaternion() if hasattr(actual, "to_quaternion") else actual
    )
    expected_quaternion = (
        expected.to_quaternion() if hasattr(expected, "to_quaternion") else expected
    )
    angle = actual_quaternion.rotation_difference(expected_quaternion).angle
    return abs(math.remainder(angle, math.tau))


def _assert_vector_close(actual, expected, label, tolerance=CHANNEL_TOLERANCE):
    error = (Vector(actual) - Vector(expected)).length
    if error > tolerance:
        raise AssertionError(
            f"{label}: error={error:.7g}, actual={tuple(actual)}, "
            f"expected={tuple(expected)}"
        )


def _build_all(build_method, name):
    base.reset_scene()
    armature = base.make_humanoid(
        name=name,
        include_right=True,
        # An arbitrary non-zero source roll catches tests that accidentally
        # work only for globally aligned bones.
        roll_offset=0.73,
    )
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {settings.last_message}")
    settings.build_method = build_method
    if bpy.ops.character_designer.limb_ik_build_all() != {"FINISHED"}:
        raise AssertionError(
            f"Build All {build_method} failed: {settings.last_message}"
        )
    bpy.context.view_layer.update()
    inventory = limb_ik._validate_inventory(armature)
    if set(inventory["rigs"]) != set(LIMB_KEYS):
        raise AssertionError(
            f"{build_method}: built {sorted(inventory['rigs'])}, "
            f"expected {sorted(LIMB_KEYS)}"
        )
    return armature, settings, inventory


def _role_entry(rig, role):
    matches = [
        (owner, constraint, record)
        for owner, constraint, record in rig["entries"]
        if record["role"] == role
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"{rig['rig_id']}: expected one {role}, found {len(matches)}"
        )
    return matches[0]


def _rotation_parts(armature, rig):
    target = armature.pose.bones[rig["target"].name]
    solver = armature.pose.bones[rig["solver_target"].name]
    end = armature.pose.bones[rig["chain"][2]]
    end_owner, end_rotation, _end_record = _role_entry(rig, "END_ROTATION")
    offset_owner, offset_rotation, _offset_record = _role_entry(
        rig,
        "AUTO_OFFSET_ROTATION",
    )
    if end_owner.name != end.name or offset_owner.name != end.name:
        raise AssertionError(
            f"{rig['rig_id']}: Target rotation constraints are not on the end bone"
        )
    return target, solver, end, end_rotation, offset_rotation


def _rig_signature(armature):
    """Capture resources whose count must not change during rotation controls."""

    inventory = limb_ik._validate_inventory(armature)
    bones = tuple(
        sorted(
            (
                bone.name,
                bone.get(limb_ik.ROLE_KEY, ""),
                bone.get(limb_ik.RIG_ID_KEY, ""),
            )
            for bone in armature.data.bones
            if bone.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        )
    )
    constraints = tuple(
        sorted(
            (
                owner.name,
                constraint.name,
                record["role"],
                record.get("rig_id", ""),
            )
            for owner, constraint, record in inventory["records"]
        )
    )
    return bones, constraints


def _assert_signature(armature, expected, label):
    actual = _rig_signature(armature)
    if actual != expected:
        raise AssertionError(f"{label}: a rotation operation added or removed rig data")


def _activate_target(armature, target):
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    if armature.mode != "POSE":
        bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in armature.pose.bones:
        pose_bone.select = False
    target.bone.hide = False
    target.select = True
    armature.data.bones.active = target.bone
    bpy.context.view_layer.update()
    active = bpy.context.active_pose_bone
    if active is None or active.name != target.name:
        raise AssertionError(f"Could not make {target.name} the active Pose bone")


def _assert_manual_contract(armature, inventory, label):
    if inventory["target_rotation_version"] != limb_ik.TARGET_ROTATION_VERSION:
        raise AssertionError(
            f"{label}: Target rotation version={inventory['target_rotation_version']}, "
            f"expected {limb_ik.TARGET_ROTATION_VERSION}"
        )
    for key in LIMB_KEYS:
        rig = inventory["rigs"][key]
        target, _solver, end, end_rotation, offset = _rotation_parts(
            armature,
            rig,
        )
        limb_label = f"{label} {key[1]} {key[0].title()}"
        if target.rotation_mode != "XYZ":
            raise AssertionError(
                f"{limb_label}: Target rotation mode is {target.rotation_mode}, expected XYZ"
            )
        if rig["auto_align"] or end_rotation.mute or not offset.mute:
            raise AssertionError(
                f"{limb_label}: Manual must use END_ROTATION only "
                f"(auto={rig['auto_align']}, end_mute={end_rotation.mute}, "
                f"offset_mute={offset.mute})"
            )
        if (
            offset.type != "COPY_ROTATION"
            or offset.target is not armature
            or offset.subtarget != target.name
            or offset.target_space != "LOCAL"
            or offset.owner_space != "LOCAL"
            or getattr(offset, "mix_mode", "") != "AFTER"
            or abs(float(offset.influence) - 1.0) > CHANNEL_TOLERANCE
            or not all(getattr(offset, field) for field in ("use_x", "use_y", "use_z"))
            or any(
                getattr(offset, field)
                for field in ("invert_x", "invert_y", "invert_z")
            )
        ):
            raise AssertionError(
                f"{limb_label}: AUTO_OFFSET_ROTATION is not exact LOCAL/LOCAL AFTER XYZ"
            )
        offset_owner, _constraint, _record = _role_entry(
            rig,
            "AUTO_OFFSET_ROTATION",
        )
        if offset_owner.name != end.name:
            raise AssertionError(
                f"{limb_label}: AUTO_OFFSET_ROTATION owner is {offset_owner.name}"
            )


def _assert_auto_contract(armature, label):
    inventory = limb_ik._validate_inventory(armature)
    for key in LIMB_KEYS:
        rig = inventory["rigs"][key]
        _target, _solver, _end, end_rotation, offset = _rotation_parts(
            armature,
            rig,
        )
        if not rig["auto_align"] or not end_rotation.mute or offset.mute:
            raise AssertionError(
                f"{label} {key}: Auto must mute END_ROTATION and enable "
                f"AUTO_OFFSET_ROTATION"
            )
    return inventory


def test_generated_rotation_contract_and_global_auto_swap():
    for build_method in BUILD_METHODS:
        armature, settings, inventory = _build_all(
            build_method,
            f"TargetRotationContract{build_method}",
        )
        signature = _rig_signature(armature)
        _assert_manual_contract(armature, inventory, build_method)

        settings.selected_limb = "RIGHT_LEG"
        result = bpy.ops.character_designer.limb_ik_auto_align_target(
            action="ENABLE"
        )
        if result != {"FINISHED"}:
            raise AssertionError(
                f"{build_method}: global Auto enable failed: {settings.last_message}"
            )
        _assert_auto_contract(armature, f"{build_method} global enable")
        _assert_signature(armature, signature, f"{build_method} global enable")

        result = bpy.ops.character_designer.limb_ik_auto_align_target(
            action="DISABLE"
        )
        if result != {"FINISHED"}:
            raise AssertionError(
                f"{build_method}: global Manual restore failed: {settings.last_message}"
            )
        inventory = limb_ik._validate_inventory(armature)
        _assert_manual_contract(armature, inventory, f"{build_method} restored")
        _assert_signature(armature, signature, f"{build_method} global disable")


def test_auto_local_xyz_offsets_and_reset_rotation():
    for build_method in BUILD_METHODS:
        armature, settings, _inventory = _build_all(
            build_method,
            f"TargetRotationAxes{build_method}",
        )
        signature = _rig_signature(armature)
        if bpy.ops.character_designer.limb_ik_auto_align_target(
            action="ENABLE"
        ) != {"FINISHED"}:
            raise AssertionError(
                f"{build_method}: global Auto enable failed: {settings.last_message}"
            )
        inventory = _assert_auto_contract(armature, f"{build_method} axes")

        # Establish one clean natural-pose baseline for every limb before
        # applying one local Euler channel at a time.
        for rig in inventory["rigs"].values():
            target = armature.pose.bones[rig["target"].name]
            target.rotation_mode = "XYZ"
            target.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()

        for key in LIMB_KEYS:
            rig = limb_ik._validate_inventory(armature)["rigs"][key]
            target, _solver, end, _end_rotation, _offset = _rotation_parts(
                armature,
                rig,
            )
            natural = end.matrix.copy()
            for axis in range(3):
                values = [0.0, 0.0, 0.0]
                values[axis] = ANGLE
                target.rotation_euler = values
                armature.update_tag(refresh={"OBJECT"})
                bpy.context.view_layer.update()

                expected_rotation = (
                    natural.to_quaternion()
                    @ Euler(values, "XYZ").to_quaternion()
                )
                position_error = (
                    end.matrix.translation - natural.translation
                ).length
                rotation_error = _rotation_error(
                    end.matrix.to_quaternion(),
                    expected_rotation,
                )
                if position_error > POSITION_TOLERANCE:
                    raise AssertionError(
                        f"{build_method} {key} local {'XYZ'[axis]} moved the end "
                        f"by {position_error:.7g}"
                    )
                if rotation_error > ROTATION_TOLERANCE:
                    raise AssertionError(
                        f"{build_method} {key} local {'XYZ'[axis]} did not apply "
                        f"after the natural end frame; rotation error={rotation_error:.7g}"
                    )

                target.rotation_euler = (0.0, 0.0, 0.0)
                armature.update_tag(refresh={"OBJECT"})
                bpy.context.view_layer.update()
                if (
                    end.matrix.translation - natural.translation
                ).length > POSITION_TOLERANCE or _rotation_error(
                    end.matrix,
                    natural,
                ) > ROTATION_TOLERANCE:
                    raise AssertionError(
                        f"{build_method} {key}: clearing local {'XYZ'[axis]} "
                        "did not restore the natural end pose"
                    )

            # Reset is deliberately tested with non-default location and scale
            # so the operator cannot pass by replacing the whole matrix basis.
            original_location = target.location.copy()
            original_scale = target.scale.copy()
            target.location += Vector((0.011, -0.007, 0.005))
            target.scale = (
                original_scale.x * 1.03,
                original_scale.y * 0.98,
                original_scale.z * 1.02,
            )
            target.rotation_euler = (0.0, 0.0, 0.0)
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
            reset_natural = end.matrix.copy()
            kept_location = target.location.copy()
            kept_scale = target.scale.copy()

            target.rotation_euler = (
                math.radians(13.0),
                math.radians(-9.0),
                math.radians(7.0),
            )
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
            if _rotation_error(end.matrix, reset_natural) < math.radians(3.0):
                raise AssertionError(
                    f"{build_method} {key}: combined Target rotation had no effect"
                )

            _activate_target(armature, target)
            result = bpy.ops.character_designer.limb_ik_reset_target_rotation()
            if result != {"FINISHED"}:
                raise AssertionError(
                    f"{build_method} {key}: Reset Rotation failed: "
                    f"{settings.last_message}"
                )
            bpy.context.view_layer.update()
            if target.rotation_mode != "XYZ":
                raise AssertionError(
                    f"{build_method} {key}: Reset changed rotation mode to "
                    f"{target.rotation_mode}"
                )
            _assert_vector_close(
                target.rotation_euler,
                (0.0, 0.0, 0.0),
                f"{build_method} {key} reset rotation",
            )
            _assert_vector_close(
                target.location,
                kept_location,
                f"{build_method} {key} reset location preservation",
            )
            _assert_vector_close(
                target.scale,
                kept_scale,
                f"{build_method} {key} reset scale preservation",
            )
            if (
                end.matrix.translation - reset_natural.translation
            ).length > POSITION_TOLERANCE or _rotation_error(
                end.matrix,
                reset_natural,
            ) > ROTATION_TOLERANCE:
                raise AssertionError(
                    f"{build_method} {key}: Reset did not restore the natural end pose"
                )

            # Restore location/scale before testing the next independent limb.
            target.location = original_location
            target.scale = original_scale
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()

        _assert_signature(armature, signature, f"{build_method} XYZ/Reset")


def test_auto_to_manual_nonzero_rotation_is_no_pop():
    for build_method in BUILD_METHODS:
        armature, settings, _inventory = _build_all(
            build_method,
            f"TargetRotationHandoff{build_method}",
        )
        signature = _rig_signature(armature)
        if bpy.ops.character_designer.limb_ik_auto_align_target(
            action="ENABLE"
        ) != {"FINISHED"}:
            raise AssertionError(
                f"{build_method}: global Auto enable failed: {settings.last_message}"
            )
        inventory = _assert_auto_contract(
            armature,
            f"{build_method} handoff before",
        )

        for index, key in enumerate(LIMB_KEYS):
            rig = inventory["rigs"][key]
            target = armature.pose.bones[rig["target"].name]
            sign = -1.0 if key[1] == "R" else 1.0
            target.rotation_mode = "XYZ"
            target.rotation_euler = (
                sign * math.radians(8.0 + index),
                math.radians(-6.0 + index),
                sign * math.radians(11.0 - index),
            )
        armature.update_tag(refresh={"OBJECT"})
        bpy.context.view_layer.update()

        before = {}
        for key in LIMB_KEYS:
            rig = inventory["rigs"][key]
            _target, solver, end, _end_rotation, _offset = _rotation_parts(
                armature,
                rig,
            )
            before[key] = (
                (armature.matrix_world @ solver.matrix).translation.copy(),
                (armature.matrix_world @ end.matrix).copy(),
            )

        result = bpy.ops.character_designer.limb_ik_auto_align_target(
            action="DISABLE"
        )
        if result != {"FINISHED"}:
            raise AssertionError(
                f"{build_method}: Auto-to-Manual failed: {settings.last_message}"
            )
        inventory = limb_ik._validate_inventory(armature)
        _assert_manual_contract(
            armature,
            inventory,
            f"{build_method} handoff after",
        )

        for key in LIMB_KEYS:
            rig = inventory["rigs"][key]
            _target, solver, end, _end_rotation, _offset = _rotation_parts(
                armature,
                rig,
            )
            solver_before, end_before = before[key]
            solver_error = (
                (armature.matrix_world @ solver.matrix).translation - solver_before
            ).length
            end_after = armature.matrix_world @ end.matrix
            end_position_error = (
                end_after.translation - end_before.translation
            ).length
            end_rotation_error = _rotation_error(end_after, end_before)
            if solver_error > POSITION_TOLERANCE:
                raise AssertionError(
                    f"{build_method} {key}: Auto-to-Manual moved the solver "
                    f"by {solver_error:.7g}"
                )
            if (
                end_position_error > POSITION_TOLERANCE
                or end_rotation_error > ROTATION_TOLERANCE
            ):
                raise AssertionError(
                    f"{build_method} {key}: Auto-to-Manual popped the end pose "
                    f"(position={end_position_error:.7g}, "
                    f"rotation={end_rotation_error:.7g})"
                )
        _assert_signature(armature, signature, f"{build_method} Auto-to-Manual")


def test_target_rotation_rebuild_remove_and_failure_rollback():
    for build_method in BUILD_METHODS:
        armature, settings, _inventory = _build_all(
            build_method,
            f"TargetRotationLifecycle{build_method}",
        )
        if bpy.ops.character_designer.limb_ik_auto_align_target(
            action="ENABLE"
        ) != {"FINISHED"}:
            raise AssertionError(
                f"{build_method}: lifecycle Auto enable failed: {settings.last_message}"
            )
        inventory = _assert_auto_contract(
            armature,
            f"{build_method} lifecycle initial",
        )
        for index, key in enumerate(LIMB_KEYS):
            target = armature.pose.bones[inventory["rigs"][key]["target"].name]
            target.rotation_mode = "XYZ"
            target.rotation_euler = (
                math.radians(4.0 + index),
                math.radians(-3.0 - index),
                math.radians(6.0 + index),
            )
        armature.update_tag(refresh={"OBJECT"})
        bpy.context.view_layer.update()

        first_ids = {
            key: rig["rig_id"] for key, rig in inventory["rigs"].items()
        }
        target_basis_before = {
            key: armature.pose.bones[rig["target"].name].matrix_basis.copy()
            for key, rig in inventory["rigs"].items()
        }
        if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
            raise AssertionError(
                f"{build_method}: Target-rotation Rebuild failed: "
                f"{settings.last_message}"
            )
        rebuilt = _assert_auto_contract(
            armature,
            f"{build_method} lifecycle rebuilt",
        )
        _assert_manual_or_auto_xyz_targets(
            armature,
            rebuilt,
            f"{build_method} lifecycle rebuilt",
        )
        rebuilt_ids = {
            key: rig["rig_id"] for key, rig in rebuilt["rigs"].items()
        }
        if any(rebuilt_ids[key] == first_ids[key] for key in LIMB_KEYS):
            raise AssertionError(
                f"{build_method}: Rebuild did not replace every limb rig ID"
            )
        for key, rig in rebuilt["rigs"].items():
            base.assert_matrix_close(
                armature.pose.bones[rig["target"].name].matrix_basis,
                target_basis_before[key],
                f"{build_method} {key} Rebuild Target basis",
                location=4.0e-4,
                rotation=3.0e-3,
                scale=4.0e-4,
            )

        # Fail after the old rig has been snapshotted and removed.  Recovery
        # must restore the exact v1 marker, rig IDs, offset constraints, mute
        # state, and posed Target matrices.
        rollback_signature = _rig_signature(armature)
        rollback_ids = rebuilt_ids.copy()
        rollback_target_basis = {
            key: armature.pose.bones[rig["target"].name].matrix_basis.copy()
            for key, rig in rebuilt["rigs"].items()
        }
        rollback_end_pose = {
            key: armature.pose.bones[rig["chain"][2]].matrix.copy()
            for key, rig in rebuilt["rigs"].items()
        }
        original_create = limb_ik._create_constraints_and_shapes
        calls = {"count": 0}

        def fail_new_build_once(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("injected Target rotation Rebuild failure")
            return original_create(*args, **kwargs)

        limb_ik._create_constraints_and_shapes = fail_new_build_once
        try:
            result = base.cancelled_result(
                bpy.ops.character_designer.limb_ik_rebuild
            )
            if result != {"CANCELLED"}:
                raise AssertionError(
                    f"{build_method}: injected Rebuild failure did not cancel"
                )
        finally:
            limb_ik._create_constraints_and_shapes = original_create

        restored = _assert_auto_contract(
            armature,
            f"{build_method} lifecycle rollback",
        )
        _assert_manual_or_auto_xyz_targets(
            armature,
            restored,
            f"{build_method} lifecycle rollback",
        )
        restored_ids = {
            key: rig["rig_id"] for key, rig in restored["rigs"].items()
        }
        if restored_ids != rollback_ids:
            raise AssertionError(
                f"{build_method}: failed Rebuild changed exact rig IDs"
            )
        _assert_signature(
            armature,
            rollback_signature,
            f"{build_method} failed Rebuild rollback",
        )
        for key, rig in restored["rigs"].items():
            base.assert_matrix_close(
                armature.pose.bones[rig["target"].name].matrix_basis,
                rollback_target_basis[key],
                f"{build_method} {key} rollback Target basis",
                location=4.0e-4,
                rotation=3.0e-3,
                scale=4.0e-4,
            )
            base.assert_matrix_close(
                armature.pose.bones[rig["chain"][2]].matrix,
                rollback_end_pose[key],
                f"{build_method} {key} rollback end pose",
                location=4.0e-4,
                rotation=3.0e-3,
                scale=4.0e-4,
            )

        if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {
            "FINISHED"
        }:
            raise AssertionError(
                f"{build_method}: Remove failed: {settings.last_message}"
            )
        removed = limb_ik._validate_inventory(armature)
        if (
            removed["rigs"]
            or removed["records"]
            or removed["bones"]
            or removed["target_rotation_version"] != 0
            or limb_ik.TARGET_ROTATION_VERSION_KEY in armature.data
        ):
            raise AssertionError(
                f"{build_method}: Remove left Target rotation ownership or metadata"
            )


def _assert_manual_or_auto_xyz_targets(armature, inventory, label):
    if inventory["target_rotation_version"] != limb_ik.TARGET_ROTATION_VERSION:
        raise AssertionError(f"{label}: Target rotation feature marker was lost")
    for key in LIMB_KEYS:
        rig = inventory["rigs"][key]
        target, _solver, _end, end_rotation, offset = _rotation_parts(
            armature,
            rig,
        )
        if target.rotation_mode != "XYZ":
            raise AssertionError(f"{label} {key}: Target is not Local XYZ")
        if bool(end_rotation.mute) is not bool(rig["auto_align"]):
            raise AssertionError(f"{label} {key}: END_ROTATION mute mismatch")
        if bool(offset.mute) is bool(rig["auto_align"]):
            raise AssertionError(
                f"{label} {key}: AUTO_OFFSET_ROTATION mute mismatch"
            )


def main():
    tests = (
        test_generated_rotation_contract_and_global_auto_swap,
        test_auto_local_xyz_offsets_and_reset_rotation,
        test_auto_to_manual_nonzero_rotation_is_no_pop,
        test_target_rotation_rebuild_remove_and_failure_rollback,
    )
    exit_code = 0
    base.ensure_registered()
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
        print(f"PASS Limb IK Target Rotation {len(tests)} tests")
    except Exception:
        traceback.print_exc()
        exit_code = 1
    finally:
        try:
            base.reset_scene()
        finally:
            base.ensure_unregistered()
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
