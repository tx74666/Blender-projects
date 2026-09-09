"""Blender 5.2 regressions for Limb IK Auto Align and Control Visual.

These tests use only the shared factory-startup humanoid fixture.  They do not
open or save the production ``X.blend`` file.

Run from the repository root with Blender 5.2::

    blender --background --factory-startup --python-exit-code 1 \
        --python tests/test_limb_ik_auto_visual_blender.py
"""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector


TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import test_limb_ik_blender as base
import test_limb_ik_widget_fit_blender as widget_fit


limb_ik = base.limb_ik

POSITION_TOLERANCE = 2.5e-4
ROTATION_TOLERANCE = 3.0e-3
VISUAL_TOLERANCE = 1.0e-6
DISPLAY_MATRIX_TOLERANCE = 3.0e-5


def _rotation_error(actual, expected):
    return actual.to_quaternion().rotation_difference(expected.to_quaternion()).angle


def _assert_vector_close(actual, expected, label, tolerance=VISUAL_TOLERANCE):
    error = (Vector(actual) - Vector(expected)).length
    if error > tolerance:
        raise AssertionError(f"{label}: error={error}, actual={tuple(actual)}, expected={tuple(expected)}")


def _assert_world_pose_close(actual, expected, label):
    position_error = (actual.translation - expected.translation).length
    rotation_error = _rotation_error(actual, expected)
    if position_error > POSITION_TOLERANCE or rotation_error > ROTATION_TOLERANCE:
        raise AssertionError(
            f"{label}: position={position_error:.6g}, rotation={rotation_error:.6g}"
        )


def _assert_matrix_elements_close(
    actual,
    expected,
    label,
    tolerance=DISPLAY_MATRIX_TOLERANCE,
):
    magnitude = max(
        1.0,
        *(abs(float(expected[row][column])) for row in range(4) for column in range(4)),
    )
    residual = max(
        abs(float(actual[row][column] - expected[row][column]))
        for row in range(4)
        for column in range(4)
    )
    if residual > tolerance * magnitude:
        raise AssertionError(
            f"{label}: matrix residual={residual:.6g}, magnitude={magnitude:.6g}"
        )


def _custom_shape_world_matrix(armature, pose_bone):
    """Return the effective world matrix Blender uses for a control widget."""
    transform = pose_bone.custom_shape_transform or pose_bone
    return (
        armature.matrix_world
        @ transform.matrix
        @ Matrix.Translation(pose_bone.custom_shape_translation)
        @ pose_bone.custom_shape_rotation_euler.to_matrix().to_4x4()
        @ Matrix.Diagonal((*tuple(pose_bone.custom_shape_scale_xyz), 1.0))
    )


def _visual_state_world_matrix(armature, transform, state):
    return (
        armature.matrix_world
        @ transform.matrix
        @ Matrix.Translation(state["translation"])
        @ Euler(tuple(state["rotation"]), "XYZ").to_matrix().to_4x4()
        @ Matrix.Diagonal((*tuple(state["scale"]), 1.0))
    )


def _world_rotation_delta_error(actual_before, actual_after, expected_before, expected_after):
    actual_delta = actual_after.to_quaternion() @ actual_before.to_quaternion().inverted()
    expected_delta = expected_after.to_quaternion() @ expected_before.to_quaternion().inverted()
    # Blender may return the equivalent negative quaternion and report the
    # identity difference as 2*pi.  Compare the shortest wrapped angle.
    angle = actual_delta.rotation_difference(expected_delta).angle
    return abs(math.remainder(angle, math.tau))


def _assert_auto_visual_reference(rig, target, expected, label):
    transform = target.custom_shape_transform
    wanted = target.id_data.pose.bones[rig["chain"][2]] if expected else None
    actual_name = transform.name if transform is not None else "None"
    wanted_name = wanted.name if wanted is not None else "None"
    if actual_name != wanted_name:
        raise AssertionError(
            f"{label}: custom_shape_transform={actual_name!r}, expected {wanted_name!r}"
        )


def _end_rotation_entry(rig):
    matches = [
        (owner, constraint, record)
        for owner, constraint, record in rig["entries"]
        if record["role"] == "END_ROTATION"
    ]
    if len(matches) != 1:
        raise AssertionError(f"Expected one END_ROTATION entry, found {len(matches)}")
    return matches[0]


def _auto_offset_entry(rig):
    matches = [
        (owner, constraint, record)
        for owner, constraint, record in rig["entries"]
        if record["role"] == "AUTO_OFFSET_ROTATION"
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected one AUTO_OFFSET_ROTATION entry, found {len(matches)}"
        )
    return matches[0]


def _rig_parts(armature, key):
    inventory = limb_ik._validate_inventory(armature)
    rig = inventory["rigs"].get(key)
    if rig is None:
        raise AssertionError(f"Missing generated rig {key}")
    target = armature.pose.bones[rig["target"].name]
    solver = armature.pose.bones[rig["solver_target"].name]
    end = armature.pose.bones[rig["chain"][2]]
    _owner, end_rotation, _record = _end_rotation_entry(rig)
    return inventory, rig, target, solver, end, end_rotation


def _constraint_mutes(inventory):
    return {
        (owner.name, constraint.name): bool(constraint.mute)
        for owner, constraint, _record in inventory["records"]
    }


def _assert_only_mutes_changed(before, after, changed, label):
    if set(before) != set(after):
        raise AssertionError(f"{label}: constraint inventory changed during a mode toggle")
    for entry, old_value in before.items():
        wanted = bool(changed[entry]) if entry in changed else old_value
        if after[entry] != wanted:
            raise AssertionError(
                f"{label}: mute state for {entry} is {after[entry]}, expected {wanted}"
            )


def _assert_auto_state(armature, expected, label):
    inventory = limb_ik._validate_inventory(armature)
    if set(inventory["rigs"]) != set(expected):
        raise AssertionError(
            f"{label}: rig keys {sorted(inventory['rigs'])}, expected {sorted(expected)}"
        )
    for key, wanted in expected.items():
        rig = inventory["rigs"][key]
        target_bone = rig["target"]
        raw = target_bone.get(limb_ik.AUTO_ALIGN_KEY, None)
        _owner, end_rotation, _record = _end_rotation_entry(rig)
        _owner, auto_offset, _record = _auto_offset_entry(rig)
        if type(raw) is not bool:
            raise AssertionError(f"{label} {key}: Auto Align metadata is not a bool: {raw!r}")
        if (
            raw is not bool(wanted)
            or bool(end_rotation.mute) is not bool(wanted)
            or bool(auto_offset.mute) is bool(wanted)
        ):
            raise AssertionError(
                f"{label} {key}: metadata={raw!r}, END_ROTATION mute={end_rotation.mute!r}, "
                f"AUTO_OFFSET_ROTATION mute={auto_offset.mute!r}, expected Auto={bool(wanted)!r}"
            )
        target = armature.pose.bones[target_bone.name]
        _assert_auto_visual_reference(
            rig,
            target,
            bool(wanted),
            f"{label} {key} visible Target frame",
        )


def _build_selected(build_method, selected_limb, *, include_right=False, name="AutoVisualRig"):
    base.reset_scene()
    armature = base.make_humanoid(name=name, include_right=include_right)
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {settings.last_message}")
    settings.build_method = build_method
    settings.selected_limb = selected_limb
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(f"Build {build_method} {selected_limb} failed: {settings.last_message}")
    bpy.context.view_layer.update()
    return armature, settings


def _build_all(build_method, *, include_right=False, name="AutoVisualRig"):
    base.reset_scene()
    armature = base.make_humanoid(name=name, include_right=include_right)
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {settings.last_message}")
    settings.build_method = build_method
    if bpy.ops.character_designer.limb_ik_build_all() != {"FINISHED"}:
        raise AssertionError(f"Build All {build_method} failed: {settings.last_message}")
    bpy.context.view_layer.update()
    return armature, settings


def _move_target(target, delta):
    matrix = target.matrix.copy()
    matrix.translation += Vector(delta)
    target.matrix = matrix
    target.id_data.update_tag(refresh={"OBJECT"})
    bpy.context.view_layer.update()


def _visual_state(pose_bone):
    return {
        "scale": tuple(float(value) for value in pose_bone.custom_shape_scale_xyz),
        "translation": tuple(float(value) for value in pose_bone.custom_shape_translation),
        "rotation": tuple(float(value) for value in pose_bone.custom_shape_rotation_euler),
    }


def _set_visual_state(pose_bone, state):
    pose_bone.custom_shape_scale_xyz = state["scale"]
    pose_bone.custom_shape_translation = state["translation"]
    pose_bone.custom_shape_rotation_euler = state["rotation"]


def _assert_visual_state(actual, expected, label):
    for field in ("scale", "translation", "rotation"):
        _assert_vector_close(actual[field], expected[field], f"{label} {field}")


def _edited_visual_state(state, seed=1.0):
    factors = (1.13 + seed * 0.01, 0.89 + seed * 0.01, 1.07 + seed * 0.01)
    offsets = (0.013 * seed, -0.021 * seed, 0.034 * seed)
    angles = (0.07 * seed, -0.11 * seed, 0.19 * seed)
    return {
        "scale": tuple(value * factor for value, factor in zip(state["scale"], factors)),
        "translation": tuple(value + offset for value, offset in zip(state["translation"], offsets)),
        "rotation": tuple(value + angle for value, angle in zip(state["rotation"], angles)),
    }


def _activate_pose_bone(armature, name):
    if bpy.context.mode != "POSE" or bpy.context.object is not armature:
        bpy.context.view_layer.objects.active = armature
        armature.select_set(True)
        if armature.mode != "POSE":
            bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in armature.pose.bones:
        pose_bone.select = False
    bone = armature.data.bones[name]
    armature.data.bones.active = bone
    armature.pose.bones[name].select = True
    bpy.context.view_layer.update()
    active = bpy.context.active_pose_bone
    if active is None or active.name != name:
        raise AssertionError(f"Could not activate PoseBone '{name}'")
    return active


def _assert_visual_eligible(armature, name, label):
    pose_bone = _activate_pose_bone(armature, name)
    resolved = limb_ik._active_control_visual(bpy.context)
    if resolved is None or resolved[0] is not armature or resolved[1].name != name:
        raise AssertionError(f"{label}: generated control was not resolved")
    strict = limb_ik._active_control_visual(bpy.context, strict=True)
    if strict[0] is not armature or strict[1].name != name:
        raise AssertionError(f"{label}: strict visual-control resolution disagreed")
    if not bpy.ops.character_designer.limb_ik_reset_control_visual.poll():
        raise AssertionError(f"{label}: Reset Control Visual did not poll")
    if limb_ik.CONTROL_VISUAL_DEFAULT_KEY not in pose_bone.bone:
        raise AssertionError(f"{label}: generated control has no stored visual default")


def _assert_visual_excluded(armature, name, label):
    _activate_pose_bone(armature, name)
    if limb_ik._active_control_visual(bpy.context) is not None:
        raise AssertionError(f"{label}: excluded bone was accepted as a visual control")
    try:
        limb_ik._active_control_visual(bpy.context, strict=True)
    except limb_ik.LimbIKError:
        pass
    else:
        raise AssertionError(f"{label}: strict visual-control resolution did not fail closed")
    if bpy.ops.character_designer.limb_ik_reset_control_visual.poll():
        raise AssertionError(f"{label}: Reset Control Visual polled for an excluded bone")


def _expected_rebuilt_override(old_state, old_default, new_default):
    scale = []
    for current, old_base, new_base in zip(
        old_state["scale"], old_default["scale"], new_default["scale"]
    ):
        if abs(old_base) <= limb_ik.EPSILON:
            scale.append(new_base + (current - old_base))
        else:
            scale.append(new_base * (current / old_base))
    return {
        "scale": tuple(scale),
        "translation": tuple(
            new_base + (current - old_base)
            for current, old_base, new_base in zip(
                old_state["translation"],
                old_default["translation"],
                new_default["translation"],
            )
        ),
        "rotation": tuple(
            (
                Euler(tuple(new_default["rotation"]), "XYZ").to_quaternion()
                @ (
                    Euler(tuple(old_default["rotation"]), "XYZ").to_quaternion().inverted()
                    @ Euler(tuple(old_state["rotation"]), "XYZ").to_quaternion()
                )
            ).to_euler(
                "XYZ",
                Euler(
                    tuple(
                        new_base + math.remainder(current - old_base, math.tau)
                        for current, old_base, new_base in zip(
                            old_state["rotation"],
                            old_default["rotation"],
                            new_default["rotation"],
                        )
                    ),
                    "XYZ",
                ),
            )
        ),
    }


def test_auto_align_persistent_direct_and_stable_arm_leg():
    cases = (
        ("DIRECT_PREROLL", "LEFT_ARM", ("ARM", "L"), (-0.08, -0.16, 0.12)),
        ("DIRECT_PREROLL", "LEFT_LEG", ("LEG", "L"), (0.12, -0.08, 0.10)),
        ("ROLL_DECOUPLED", "LEFT_ARM", ("ARM", "L"), (-0.08, -0.16, 0.12)),
        ("ROLL_DECOUPLED", "LEFT_LEG", ("LEG", "L"), (0.12, -0.08, 0.10)),
    )
    for build_method, selected_limb, key, translation in cases:
        label = f"{build_method} {selected_limb}"
        armature, settings = _build_selected(
            build_method,
            selected_limb,
            name=f"Persistent{build_method}{selected_limb}",
        )
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        if target.bone.get(limb_ik.AUTO_ALIGN_KEY, None) is not False or end_rotation.mute:
            raise AssertionError(f"{label}: a new Target did not start in Manual mode")
        _assert_auto_visual_reference(rig, target, False, f"{label} initial visual frame")

        before_mutes = _constraint_mutes(inventory)
        bases_before_enable = {
            pose_bone.name: pose_bone.matrix_basis.copy()
            for pose_bone in armature.pose.bones
        }
        solver_before_enable = armature.matrix_world @ solver.matrix.copy()
        end_before_enable = armature.matrix_world @ end.matrix.copy()
        visual_before_enable = _custom_shape_world_matrix(armature, target)
        relative_visual_before_enable = (
            end_before_enable.inverted_safe() @ visual_before_enable
        )
        changed_entry = (_end_rotation_entry(rig)[0].name, end_rotation.name)
        offset_entry = (
            _auto_offset_entry(rig)[0].name,
            _auto_offset_entry(rig)[1].name,
        )
        if bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE") != {"FINISHED"}:
            raise AssertionError(f"{label}: ENABLE failed: {settings.last_message}")
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        _assert_auto_state(armature, {key: True}, f"{label} ENABLE")
        _assert_only_mutes_changed(
            before_mutes,
            _constraint_mutes(inventory),
            {changed_entry: True, offset_entry: False},
            f"{label} ENABLE",
        )
        solver_after_enable = armature.matrix_world @ solver.matrix.copy()
        if (
            solver_after_enable.translation - solver_before_enable.translation
        ).length > POSITION_TOLERANCE:
            raise AssertionError(f"{label}: ENABLE moved the IK solver point")
        end_after_enable = armature.matrix_world @ end.matrix.copy()
        visual_after_enable = _custom_shape_world_matrix(armature, target)
        _assert_matrix_elements_close(
            end_after_enable.inverted_safe() @ visual_after_enable,
            relative_visual_before_enable,
            f"{label} ENABLE end-relative visible Target",
        )
        _assert_matrix_elements_close(
            visual_after_enable,
            end_after_enable @ end_before_enable.inverted_safe() @ visual_before_enable,
            f"{label} ENABLE visible Target followed end",
        )
        for name, before in bases_before_enable.items():
            base.assert_matrix_close(
                armature.pose.bones[name].matrix_basis,
                before,
                f"{label} ENABLE authored '{name}'",
                location=1.0e-7,
                rotation=1.0e-7,
                scale=1.0e-7,
            )

        natural_end_before = armature.matrix_world @ end.matrix.copy()
        target_before_move = armature.matrix_world @ target.matrix.copy()
        target_basis_before_move = target.matrix_basis.copy()
        solver_before_move = armature.matrix_world @ solver.matrix.copy()
        visual_before_move = _custom_shape_world_matrix(armature, target)
        _move_target(target, translation)
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        natural_end_after = armature.matrix_world @ end.matrix.copy()
        visual_after_move = _custom_shape_world_matrix(armature, target)
        natural_follow = _rotation_error(natural_end_after, natural_end_before)
        if natural_follow < 8.0e-3:
            raise AssertionError(
                f"{label}: muted natural end did not follow the translated Target "
                f"(rotation change {natural_follow:.6g})"
            )
        if (
            (armature.matrix_world @ solver.matrix).translation - solver_before_move.translation
        ).length < 1.0e-3:
            raise AssertionError(f"{label}: translated Target did not move the IK solver")
        if _rotation_error(armature.matrix_world @ target.matrix, target_before_move) > 1.0e-5:
            raise AssertionError(f"{label}: translation unexpectedly rotated the Target")
        if _rotation_error(target.matrix_basis, target_basis_before_move) > 1.0e-5:
            raise AssertionError(f"{label}: translation changed the Target rotation channel")
        visible_follow = _rotation_error(visual_after_move, visual_before_move)
        if visible_follow < 8.0e-3:
            raise AssertionError(
                f"{label}: Auto Target widget stayed fixed after its end bone tilted "
                f"(rotation change {visible_follow:.6g})"
            )
        delta_error = _world_rotation_delta_error(
            visual_before_move,
            visual_after_move,
            natural_end_before,
            natural_end_after,
        )
        if delta_error > ROTATION_TOLERANCE:
            raise AssertionError(
                f"{label}: visible Target did not inherit its end-bone rotation "
                f"(delta error {delta_error:.6g})"
            )
        lower = armature.pose.bones[rig["chain"][1]]
        inherited_end = (
            lower.matrix
            @ lower.bone.matrix_local.inverted_safe()
            @ end.bone.matrix_local
            @ end.matrix_basis
        )
        base.assert_matrix_close(
            end.matrix,
            inherited_end,
            f"{label} natural inherited end",
            location=POSITION_TOLERANCE,
            rotation=3.0e-4,
            scale=POSITION_TOLERANCE,
        )
        if not end_rotation.mute or target.bone.get(limb_ik.AUTO_ALIGN_KEY, None) is not True:
            raise AssertionError(f"{label}: Auto mode was not persistent after Target translation")

        before_disable_mutes = _constraint_mutes(inventory)
        solver_before_disable = armature.matrix_world @ solver.matrix.copy()
        end_before_disable = armature.matrix_world @ end.matrix.copy()
        target_before_disable = armature.matrix_world @ target.matrix.copy()
        visual_before_disable = _custom_shape_world_matrix(armature, target)
        if bpy.ops.character_designer.limb_ik_auto_align_target(action="DISABLE") != {"FINISHED"}:
            raise AssertionError(f"{label}: DISABLE failed: {settings.last_message}")
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        _assert_auto_state(armature, {key: False}, f"{label} DISABLE")
        _assert_only_mutes_changed(
            before_disable_mutes,
            _constraint_mutes(inventory),
            {changed_entry: False, offset_entry: True},
            f"{label} DISABLE",
        )
        solver_after_disable = armature.matrix_world @ solver.matrix.copy()
        end_after_disable = armature.matrix_world @ end.matrix.copy()
        if (
            solver_after_disable.translation - solver_before_disable.translation
        ).length > POSITION_TOLERANCE:
            raise AssertionError(f"{label}: DISABLE popped the IK solver point")
        _assert_world_pose_close(end_after_disable, end_before_disable, f"{label} DISABLE end")
        _assert_world_pose_close(
            _custom_shape_world_matrix(armature, target),
            visual_before_disable,
            f"{label} DISABLE visible Target",
        )
        if _rotation_error(armature.matrix_world @ target.matrix, target_before_disable) < 2.0e-3:
            raise AssertionError(f"{label}: fixture did not require DISABLE to sync Target rotation")


def test_auto_align_fitted_right_foot_visual_follows_ankle():
    """A fitted sole outline must receive the same mode-switch delta as Foot."""

    base.reset_scene()
    armature = base.make_humanoid(
        name="AutoFittedRightFootRig",
        include_right=True,
    )
    widget_fit._make_anatomical_seed(armature)
    widget_fit._make_anatomical_feet(
        "AutoFittedRightFootShoes",
        scale=1.0,
        z_min=-0.035,
        z_max=0.075,
    )
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_leg() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()

    key = ("LEG", "R")
    _inventory, rig, target, solver, end, _end_rotation = _rig_parts(armature, key)
    _move_target(target, (-0.10, -0.16, 0.16))
    _assert_vector_close(
        target.rotation_euler,
        (0.0, 0.0, 0.0),
        "fitted right Foot fixture Target Rotation",
        tolerance=1.0e-7,
    )
    if Vector(target.custom_shape_translation).length < 0.05:
        raise AssertionError("fitted right Foot fixture has no meaningful visual offset")
    if max(abs(float(value)) for value in target.custom_shape_rotation_euler) < 0.05:
        raise AssertionError("fitted right Foot fixture has no meaningful visual rotation")

    end_before = armature.matrix_world @ end.matrix.copy()
    display_before = _custom_shape_world_matrix(armature, target)
    relative_before = end_before.inverted_safe() @ display_before
    solver_before = armature.matrix_world @ solver.matrix.copy()
    if bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE") != {"FINISHED"}:
        raise AssertionError(f"fitted right Foot ENABLE failed: {settings.last_message}")
    bpy.context.view_layer.update()

    _inventory, rig, target, solver, end, _end_rotation = _rig_parts(armature, key)
    _assert_auto_state(
        armature,
        {("LEG", "L"): True, ("LEG", "R"): True},
        "fitted right Foot ENABLE",
    )
    end_after = armature.matrix_world @ end.matrix.copy()
    display_after = _custom_shape_world_matrix(armature, target)
    if _rotation_error(end_after, end_before) < 0.05:
        raise AssertionError("fixture did not rotate the natural right Foot")
    _assert_matrix_elements_close(
        end_after.inverted_safe() @ display_after,
        relative_before,
        "fitted right Foot end-relative visual",
        tolerance=5.0e-5,
    )
    _assert_matrix_elements_close(
        display_after,
        end_after @ end_before.inverted_safe() @ display_before,
        "fitted right Foot visual followed ankle",
        tolerance=5.0e-5,
    )
    if _rotation_error(display_after, display_before) < 0.05:
        raise AssertionError("fitted right Foot widget stayed fixed in world space")
    _assert_vector_close(
        target.rotation_euler,
        (0.0, 0.0, 0.0),
        "fitted right Foot Auto Target Rotation",
        tolerance=1.0e-7,
    )
    if (
        (armature.matrix_world @ solver.matrix).translation - solver_before.translation
    ).length > POSITION_TOLERANCE:
        raise AssertionError("fitted right Foot ENABLE moved the IK solver")


def test_auto_align_nonuniform_target_scale_preserves_or_fails_closed():
    cases = (
        ("DIRECT_PREROLL", "LEFT_ARM", ("ARM", "L")),
        ("DIRECT_PREROLL", "LEFT_LEG", ("LEG", "L")),
        ("ROLL_DECOUPLED", "LEFT_ARM", ("ARM", "L")),
        ("ROLL_DECOUPLED", "LEFT_LEG", ("LEG", "L")),
    )
    for build_method, selected_limb, key in cases:
        label = f"{build_method} {selected_limb} nonuniform scale"
        armature, settings = _build_selected(
            build_method,
            selected_limb,
            name=f"Scaled{build_method}{selected_limb}",
        )
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        target.scale = (1.4, 0.8, 1.2)
        bpy.context.view_layer.update()
        basis_before = target.matrix_basis.copy()
        visual_before = _visual_state(target)
        display_before = _custom_shape_world_matrix(armature, target)
        solver_before = armature.matrix_world @ solver.matrix.copy()
        end_before = armature.matrix_world @ end.matrix.copy()
        relative_before = end_before.inverted_safe() @ display_before

        result = base.cancelled_result(
            lambda: bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE")
        )
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        if result == {"CANCELLED"}:
            if "display shear" not in settings.last_message:
                raise AssertionError(
                    f"{label}: non-representable frame failed for the wrong reason: "
                    f"{settings.last_message}"
                )
            _assert_auto_state(armature, {key: False}, f"{label} ENABLE fail-closed")
            base.assert_matrix_close(
                target.matrix_basis,
                basis_before,
                f"{label} failed ENABLE Target basis",
            )
            _assert_visual_state(
                _visual_state(target),
                visual_before,
                f"{label} failed ENABLE visual vectors",
            )
            _assert_matrix_elements_close(
                _custom_shape_world_matrix(armature, target),
                display_before,
                f"{label} failed ENABLE visible Target",
            )
            _assert_world_pose_close(
                armature.matrix_world @ solver.matrix,
                solver_before,
                f"{label} failed ENABLE solver",
            )
            _assert_world_pose_close(
                armature.matrix_world @ end.matrix,
                end_before,
                f"{label} failed ENABLE end",
            )
            continue
        if result != {"FINISHED"}:
            raise AssertionError(f"{label}: unexpected ENABLE result {result}")

        _assert_auto_state(armature, {key: True}, f"{label} ENABLE")
        base.assert_matrix_close(
            target.matrix_basis,
            basis_before,
            f"{label} ENABLE Target basis",
        )
        end_after = armature.matrix_world @ end.matrix.copy()
        _assert_matrix_elements_close(
            end_after.inverted_safe() @ _custom_shape_world_matrix(armature, target),
            relative_before,
            f"{label} ENABLE end-relative visible Target",
        )
        if (
            (armature.matrix_world @ solver.matrix).translation
            - solver_before.translation
        ).length > POSITION_TOLERANCE:
            raise AssertionError(f"{label}: ENABLE moved the IK solver")

        basis_before_disable = target.matrix_basis.copy()
        visual_before_disable = _visual_state(target)
        display_before_disable = _custom_shape_world_matrix(armature, target)
        solver_before_disable = armature.matrix_world @ solver.matrix.copy()
        end_before_disable = armature.matrix_world @ end.matrix.copy()
        result = base.cancelled_result(
            lambda: bpy.ops.character_designer.limb_ik_auto_align_target(action="DISABLE")
        )
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        if result == {"CANCELLED"}:
            if "display shear" not in settings.last_message:
                raise AssertionError(
                    f"{label}: DISABLE failed for the wrong reason: {settings.last_message}"
                )
            _assert_auto_state(armature, {key: True}, f"{label} DISABLE fail-closed")
            base.assert_matrix_close(
                target.matrix_basis,
                basis_before_disable,
                f"{label} failed DISABLE Target basis",
            )
            _assert_visual_state(
                _visual_state(target),
                visual_before_disable,
                f"{label} failed DISABLE visual vectors",
            )
        elif result == {"FINISHED"}:
            _assert_auto_state(armature, {key: False}, f"{label} DISABLE")
        else:
            raise AssertionError(f"{label}: unexpected DISABLE result {result}")
        _assert_matrix_elements_close(
            _custom_shape_world_matrix(armature, target),
            display_before_disable,
            f"{label} DISABLE visible Target",
        )
        if (
            (armature.matrix_world @ solver.matrix).translation
            - solver_before_disable.translation
        ).length > POSITION_TOLERANCE:
            raise AssertionError(f"{label}: DISABLE moved the IK solver point")
        _assert_world_pose_close(
            armature.matrix_world @ end.matrix,
            end_before_disable,
            f"{label} DISABLE end",
        )


def test_auto_reset_visual_uses_manual_default_in_live_end_frame():
    cases = (
        ("DIRECT_PREROLL", "LEFT_ARM", ("ARM", "L"), (-0.08, -0.16, 0.12)),
        ("DIRECT_PREROLL", "LEFT_LEG", ("LEG", "L"), (0.12, -0.08, 0.10)),
        ("ROLL_DECOUPLED", "LEFT_ARM", ("ARM", "L"), (-0.08, -0.16, 0.12)),
        ("ROLL_DECOUPLED", "LEFT_LEG", ("LEG", "L"), (0.12, -0.08, 0.10)),
    )
    for build_method, selected_limb, key, translation in cases:
        label = f"{build_method} {selected_limb} Auto Reset"
        armature, settings = _build_selected(
            build_method,
            selected_limb,
            name=f"AutoReset{build_method}{selected_limb}",
        )
        if bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE") != {"FINISHED"}:
            raise AssertionError(f"{label}: ENABLE failed: {settings.last_message}")
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        _activate_pose_bone(armature, target.name)

        # Resetting an untouched Auto control is visually a no-op.  This is the
        # Direct-Hand regression: applying its Manual-local default directly in
        # the end frame previously flipped the widget by almost 180 degrees.
        display_before_reset = _custom_shape_world_matrix(armature, target)
        target_before_reset = armature.matrix_world @ target.matrix.copy()
        solver_before_reset = armature.matrix_world @ solver.matrix.copy()
        end_before_reset = armature.matrix_world @ end.matrix.copy()
        if bpy.ops.character_designer.limb_ik_reset_control_visual() != {"FINISHED"}:
            raise AssertionError(f"{label}: untouched Reset failed: {settings.last_message}")
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        _assert_auto_state(armature, {key: True}, f"{label} untouched Reset")
        _assert_matrix_elements_close(
            _custom_shape_world_matrix(armature, target),
            display_before_reset,
            f"{label} untouched Reset visible Target",
        )
        _assert_world_pose_close(
            armature.matrix_world @ target.matrix,
            target_before_reset,
            f"{label} untouched Reset Target",
        )
        _assert_world_pose_close(
            armature.matrix_world @ solver.matrix,
            solver_before_reset,
            f"{label} untouched Reset solver",
        )
        _assert_world_pose_close(
            armature.matrix_world @ end.matrix,
            end_before_reset,
            f"{label} untouched Reset end",
        )

        # After an actual display edit, Reset must reproduce the canonical
        # Manual/Target-frame default, converted into the live end frame.
        default = limb_ik._parse_control_visual_state(
            target.bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None),
            f"{label} stored default",
        )
        expected_default_world = _visual_state_world_matrix(
            armature,
            target.custom_shape_transform or target,
            default,
        )
        _set_visual_state(target, _edited_visual_state(_visual_state(target), seed=1.7))
        bpy.context.view_layer.update()
        target_before_edited_reset = armature.matrix_world @ target.matrix.copy()
        end_before_edited_reset = armature.matrix_world @ end.matrix.copy()
        if bpy.ops.character_designer.limb_ik_reset_control_visual() != {"FINISHED"}:
            raise AssertionError(f"{label}: edited Reset failed: {settings.last_message}")
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        _assert_auto_state(armature, {key: True}, f"{label} edited Reset")
        _assert_matrix_elements_close(
            _custom_shape_world_matrix(armature, target),
            expected_default_world,
            f"{label} canonical default in live end frame",
        )
        _assert_world_pose_close(
            armature.matrix_world @ target.matrix,
            target_before_edited_reset,
            f"{label} edited Reset Target",
        )
        _assert_world_pose_close(
            armature.matrix_world @ end.matrix,
            end_before_edited_reset,
            f"{label} edited Reset end",
        )

        # The Reset conversion must retain the dynamic end reference: moving a
        # translation-only Target still rotates only its visible Hand/Foot.
        natural_end_before = armature.matrix_world @ end.matrix.copy()
        target_before_move = armature.matrix_world @ target.matrix.copy()
        target_basis_before_move = target.matrix_basis.copy()
        visual_before_move = _custom_shape_world_matrix(armature, target)
        _move_target(target, translation)
        inventory, rig, target, solver, end, end_rotation = _rig_parts(armature, key)
        natural_end_after = armature.matrix_world @ end.matrix.copy()
        visual_after_move = _custom_shape_world_matrix(armature, target)
        if _rotation_error(armature.matrix_world @ target.matrix, target_before_move) > 1.0e-5:
            raise AssertionError(f"{label}: translation rotated the real Target after Reset")
        if _rotation_error(target.matrix_basis, target_basis_before_move) > 1.0e-5:
            raise AssertionError(f"{label}: translation changed a Target rotation channel after Reset")
        if _rotation_error(natural_end_after, natural_end_before) < 8.0e-3:
            raise AssertionError(f"{label}: fixture end did not tilt after Reset")
        if _rotation_error(visual_after_move, visual_before_move) < 8.0e-3:
            raise AssertionError(f"{label}: Reset left the Auto widget fixed")
        delta_error = _world_rotation_delta_error(
            visual_before_move,
            visual_after_move,
            natural_end_before,
            natural_end_after,
        )
        if delta_error > ROTATION_TOLERANCE:
            raise AssertionError(
                f"{label}: reset visible Target stopped following its end "
                f"(delta error {delta_error:.6g})"
            )


def test_auto_align_is_global_and_mismatch_fails_closed():
    armature, settings = _build_all(
        "ROLL_DECOUPLED",
        include_right=True,
        name="GlobalAutoAlignRig",
    )
    all_keys = {(kind, side) for kind in limb_ik.KINDS for side in limb_ik.SIDES}
    all_manual = {key: False for key in all_keys}
    all_auto = {key: True for key in all_keys}
    _assert_auto_state(armature, all_manual, "initial global Manual mode")

    target_bases = {
        key: armature.pose.bones[rig["target"].name].matrix_basis.copy()
        for key, rig in limb_ik._validate_inventory(armature)["rigs"].items()
    }
    # The limb dropdown only edits/analyzes one limb.  Auto Align is a global
    # animator mode and must update every already-generated limb at once.
    settings.selected_limb = "LEFT_ARM"
    if bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_auto_state(armature, all_auto, "global ENABLE from Left Arm selection")
    current_inventory = limb_ik._validate_inventory(armature)
    for key, before in target_bases.items():
        base.assert_matrix_close(
            armature.pose.bones[current_inventory["rigs"][key]["target"].name].matrix_basis,
            before,
            f"global ENABLE authored {key} Target",
            location=1.0e-7,
            rotation=1.0e-7,
            scale=1.0e-7,
        )

    # Explicit actions are idempotent and selection-independent.
    settings.selected_limb = "RIGHT_LEG"
    if bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_auto_state(armature, all_auto, "idempotent global ENABLE from Right Leg selection")

    # The public default action is one real global toggle.
    if bpy.ops.character_designer.limb_ik_auto_align_target() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_auto_state(armature, all_manual, "global TOGGLE off from Right Leg selection")

    settings.selected_limb = "LEFT_ARM"
    if bpy.ops.character_designer.limb_ik_auto_align_target() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_auto_state(armature, all_auto, "global TOGGLE on from Left Arm selection")

    settings.selected_limb = "LEFT_LEG"
    if bpy.ops.character_designer.limb_ik_auto_align_target(action="DISABLE") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_auto_state(armature, all_manual, "global DISABLE from Left Leg selection")

    if bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_auto_state(armature, all_auto, "global ENABLE before mismatch fixture")

    # Inventory validation is authoritative.  A mixed legacy/corrupt state
    # must fail closed rather than partially toggling the generated limbs.
    key = ("LEG", "L")
    _inventory, rig, target, _solver, _end, end_rotation = _rig_parts(armature, key)
    targets = {
        rig_key: armature.pose.bones[saved_rig["target"].name]
        for rig_key, saved_rig in _inventory["rigs"].items()
    }
    target_bases = {rig_key: bone.matrix_basis.copy() for rig_key, bone in targets.items()}
    target_transforms = {
        rig_key: bone.custom_shape_transform for rig_key, bone in targets.items()
    }
    mute_states = {
        (owner.name, constraint.name): bool(constraint.mute)
        for owner, constraint, _record in _inventory["records"]
    }

    target.bone[limb_ik.AUTO_ALIGN_KEY] = False
    settings.selected_limb = "RIGHT_ARM"
    if base.cancelled_result(
        lambda: bpy.ops.character_designer.limb_ik_auto_align_target(action="DISABLE")
    ) != {"CANCELLED"}:
        raise AssertionError("Global Auto Align accepted mixed metadata/mute state")
    if target.bone.get(limb_ik.AUTO_ALIGN_KEY) is not False or not end_rotation.mute:
        raise AssertionError("Mismatch refusal repaired or changed the corrupt limb")
    for rig_key, bone in targets.items():
        base.assert_matrix_close(
            bone.matrix_basis,
            target_bases[rig_key],
            f"global mismatch refusal changed {rig_key} Target",
        )
        before_transform = target_transforms[rig_key]
        if (
            bone.custom_shape_transform.name if bone.custom_shape_transform else ""
        ) != (before_transform.name if before_transform else ""):
            raise AssertionError(
                f"Global mismatch refusal changed {rig_key} visible Target frame"
            )
    for owner, constraint, _record in _inventory["records"]:
        if bool(constraint.mute) is not mute_states[(owner.name, constraint.name)]:
            raise AssertionError(
                f"Global mismatch refusal changed mute state on '{owner.name}:{constraint.name}'"
            )

    target.bone[limb_ik.AUTO_ALIGN_KEY] = True
    if bpy.ops.character_designer.limb_ik_auto_align_target(action="DISABLE") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_auto_state(armature, all_manual, "restored global Manual mode")

    _inventory, rig, target, _solver, _end, end_rotation = _rig_parts(armature, key)
    targets = {
        rig_key: armature.pose.bones[saved_rig["target"].name]
        for rig_key, saved_rig in _inventory["rigs"].items()
    }
    target_bases = {rig_key: bone.matrix_basis.copy() for rig_key, bone in targets.items()}
    target_transforms = {
        rig_key: bone.custom_shape_transform for rig_key, bone in targets.items()
    }
    end_rotation.mute = True
    if base.cancelled_result(
        lambda: bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE")
    ) != {"CANCELLED"}:
        raise AssertionError("Global Auto Align accepted reverse mixed metadata/mute state")
    if target.bone.get(limb_ik.AUTO_ALIGN_KEY) is not False or not end_rotation.mute:
        raise AssertionError("Reverse mismatch refusal repaired or changed the corrupt limb")
    for rig_key, bone in targets.items():
        base.assert_matrix_close(
            bone.matrix_basis,
            target_bases[rig_key],
            f"reverse global mismatch refusal changed {rig_key} Target",
        )
        before_transform = target_transforms[rig_key]
        if (
            bone.custom_shape_transform.name if bone.custom_shape_transform else ""
        ) != (before_transform.name if before_transform else ""):
            raise AssertionError(
                f"Reverse global mismatch refusal changed {rig_key} visible Target frame"
            )

    end_rotation.mute = False
    _assert_auto_state(armature, all_manual, "restored reverse mismatch fixture")


def test_auto_align_state_survives_rebuild_and_rollback():
    for build_method in ("DIRECT_PREROLL", "ROLL_DECOUPLED"):
        label = f"{build_method} Rebuild"
        armature, settings = _build_all(
            build_method,
            include_right=False,
            name=f"{build_method}RebuildAutoRig",
        )
        settings.selected_limb = "LEFT_ARM"
        if bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE") != {"FINISHED"}:
            raise AssertionError(f"{label}: ENABLE failed: {settings.last_message}")
        expected = {("ARM", "L"): True, ("LEG", "L"): True}
        _assert_auto_state(armature, expected, f"{label} before")
        before_inventory = limb_ik._validate_inventory(armature)
        target_visuals_before_rebuild = {
            key: _custom_shape_world_matrix(
                armature,
                armature.pose.bones[rig["target"].name],
            )
            for key, rig in before_inventory["rigs"].items()
        }
        # The panel must read the persisted Target state from the active rig,
        # not from transient Analyze state that disappears after reopening.  It
        # reports the one global mode even though a limb remains selected.
        analyzed_armature = settings.armature
        settings.armature = None
        try:
            if limb_ik._selected_auto_align_ui_state(bpy.context, settings) != (True, True):
                raise AssertionError(f"{label}: saved Auto state disappeared without Analyze state")
        finally:
            settings.armature = analyzed_armature
        old_ids = {
            key: rig["rig_id"]
            for key, rig in limb_ik._validate_inventory(armature)["rigs"].items()
        }
        if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
            raise AssertionError(f"{label} failed: {settings.last_message}")
        inventory = limb_ik._validate_inventory(armature)
        new_ids = {key: rig["rig_id"] for key, rig in inventory["rigs"].items()}
        if any(new_ids[key] == old_ids[key] for key in expected):
            raise AssertionError(f"{label}: successful Rebuild did not replace each rig ID")
        _assert_auto_state(armature, expected, f"{label} after")
        for key, rig in inventory["rigs"].items():
            _assert_world_pose_close(
                _custom_shape_world_matrix(
                    armature,
                    armature.pose.bones[rig["target"].name],
                ),
                target_visuals_before_rebuild[key],
                f"{label} {key} visible Target after Rebuild",
            )
        rebuilt_leg_target = armature.pose.bones[
            inventory["rigs"][("LEG", "L")]["target"].name
        ]

        # Auto is one animator-facing global mode.  An intentional planning
        # edit must not silently switch it off during Rebuild.
        foot_visual_before_direction_rebuild = _custom_shape_world_matrix(
            armature,
            rebuilt_leg_target,
        )
        settings.left_arm_pole_direction = (0.2, 0.97, 0.1)
        if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
            raise AssertionError(f"{label} direction-change Rebuild failed: {settings.last_message}")
        inventory = limb_ik._validate_inventory(armature)
        direction_ids = {key: rig["rig_id"] for key, rig in inventory["rigs"].items()}
        if any(direction_ids[key] == new_ids[key] for key in expected):
            raise AssertionError(f"{label}: direction-change Rebuild did not replace each rig ID")
        _assert_auto_state(armature, expected, f"{label} after direction change")
        direction_leg_target = armature.pose.bones[
            inventory["rigs"][("LEG", "L")]["target"].name
        ]
        _assert_world_pose_close(
            _custom_shape_world_matrix(armature, direction_leg_target),
            foot_visual_before_direction_rebuild,
            f"{label} visible Foot after Arm direction Rebuild",
        )
        new_ids = direction_ids

        if build_method != "ROLL_DECOUPLED":
            continue

        rollback_ids = new_ids.copy()
        rollback_target_bases = {
            key: armature.pose.bones[rig["target"].name].matrix_basis.copy()
            for key, rig in inventory["rigs"].items()
        }
        rollback_end_world = {
            key: armature.matrix_world @ armature.pose.bones[rig["chain"][2]].matrix.copy()
            for key, rig in inventory["rigs"].items()
        }
        rollback_visuals = {
            rig["target"].name: _visual_state(armature.pose.bones[rig["target"].name])
            for rig in inventory["rigs"].values()
        }
        rollback_visible_world = {
            key: _custom_shape_world_matrix(
                armature,
                armature.pose.bones[rig["target"].name],
            )
            for key, rig in inventory["rigs"].items()
        }
        rollback_visual_defaults = {
            bone.name: bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None)
            for bone in inventory["bones"]
        }

        original_create = limb_ik._create_constraints_and_shapes
        calls = {"count": 0}

        def fail_new_build_once(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("injected Auto Align Rebuild failure")
            return original_create(*args, **kwargs)

        limb_ik._create_constraints_and_shapes = fail_new_build_once
        try:
            result = base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild)
        finally:
            limb_ik._create_constraints_and_shapes = original_create
        if result != {"CANCELLED"}:
            raise AssertionError("Injected Auto Align Rebuild failure did not cancel")
        if calls["count"] < 2:
            raise AssertionError("Injected Rebuild did not exercise old-rig snapshot recovery")

        restored = limb_ik._validate_inventory(armature)
        restored_ids = {key: rig["rig_id"] for key, rig in restored["rigs"].items()}
        if restored_ids != rollback_ids:
            raise AssertionError("Failed Rebuild did not restore the exact prior rig IDs")
        _assert_auto_state(armature, expected, "failed Rebuild Auto Align recovery")
        for key, rig in restored["rigs"].items():
            target = armature.pose.bones[rig["target"].name]
            base.assert_matrix_close(
                target.matrix_basis,
                rollback_target_bases[key],
                f"failed Rebuild {key} Target basis",
            )
            _assert_world_pose_close(
                armature.matrix_world @ armature.pose.bones[rig["chain"][2]].matrix,
                rollback_end_world[key],
                f"failed Rebuild {key} end",
            )
            _assert_visual_state(
                _visual_state(target),
                rollback_visuals[target.name],
                f"failed Rebuild {key} visual",
            )
            _assert_world_pose_close(
                _custom_shape_world_matrix(armature, target),
                rollback_visible_world[key],
                f"failed Rebuild {key} visible Target",
            )
        for bone in restored["bones"]:
            if bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None) != rollback_visual_defaults[bone.name]:
                raise AssertionError(
                    f"Failed Rebuild changed stored visual default on '{bone.name}'"
                )


def test_control_visual_eligibility_direct_edits_and_reset():
    armature, settings = _build_all(
        "ROLL_DECOUPLED",
        include_right=False,
        name="ControlVisualEligibilityRig",
    )
    inventory = limb_ik._validate_inventory(armature)
    arm_rig = inventory["rigs"][("ARM", "L")]
    leg_rig = inventory["rigs"][("LEG", "L")]
    eligible = (
        (arm_rig["target"].name, "Arm Target"),
        (arm_rig["pole"].name, "Arm Pole"),
        (inventory["master"].name, "Master"),
        (leg_rig["heel"].name, "Heel"),
    )
    for name, label in eligible:
        _assert_visual_eligible(armature, name, label)

    target = armature.pose.bones[leg_rig["target"].name]
    _activate_pose_bone(armature, target.name)
    default_raw = target.bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None)
    default = limb_ik._parse_control_visual_state(default_raw, f"Control '{target.name}'")
    if (
        (Vector(default["scale"]) - Vector((1.0, 1.0, 1.0))).length <= 1.0e-5
        and Vector(default["translation"]).length <= 1.0e-5
        and Vector(default["rotation"]).length <= 1.0e-5
    ):
        raise AssertionError(
            f"Foot Target fixture did not store a nontrivial fitted default: {default!r}"
        )

    pose_before = target.matrix.copy()
    basis_before = target.matrix_basis.copy()
    all_pose_before = {
        pose_bone.name: pose_bone.matrix.copy()
        for pose_bone in armature.pose.bones
    }
    shape_before = target.custom_shape
    transform_before = target.custom_shape_transform
    use_size_before = target.use_custom_shape_bone_size
    lock_signature = (
        tuple(target.lock_location),
        tuple(target.lock_rotation),
        tuple(target.lock_scale),
    )
    inventory_signature = (
        tuple(sorted(bone.name for bone in inventory["bones"])),
        tuple(sorted(constraint.name for _owner, constraint, _record in inventory["records"])),
    )
    edited = _edited_visual_state(_visual_state(target), seed=1.0)
    _set_visual_state(target, edited)
    bpy.context.view_layer.update()
    _assert_visual_state(_visual_state(target), edited, "direct visual edit")
    base.assert_matrix_close(target.matrix, pose_before, "direct visual edit pose")
    base.assert_matrix_close(target.matrix_basis, basis_before, "direct visual edit basis")
    for name, before in all_pose_before.items():
        base.assert_matrix_close(
            armature.pose.bones[name].matrix,
            before,
            f"direct visual edit changed '{name}' pose",
        )
    if (
        target.custom_shape is not shape_before
        or target.custom_shape_transform is not transform_before
        or target.use_custom_shape_bone_size != use_size_before
        or target.bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None) != default_raw
        or (
            tuple(target.lock_location),
            tuple(target.lock_rotation),
            tuple(target.lock_scale),
        )
        != lock_signature
    ):
        raise AssertionError("Direct visual-vector edits changed non-visual control state")
    checked = limb_ik._validate_inventory(armature)
    checked_signature = (
        tuple(sorted(bone.name for bone in checked["bones"])),
        tuple(sorted(constraint.name for _owner, constraint, _record in checked["records"])),
    )
    if checked_signature != inventory_signature:
        raise AssertionError("Direct visual-vector edits changed generated rig data")

    if bpy.ops.character_designer.limb_ik_reset_control_visual() != {"FINISHED"}:
        raise AssertionError(f"Reset Control Visual failed: {settings.last_message}")
    _assert_visual_state(_visual_state(target), default, "Reset stored fitted default")
    base.assert_matrix_close(target.matrix, pose_before, "Reset Control Visual pose")
    base.assert_matrix_close(target.matrix_basis, basis_before, "Reset Control Visual basis")
    for name, before in all_pose_before.items():
        base.assert_matrix_close(
            armature.pose.bones[name].matrix,
            before,
            f"Reset Control Visual changed '{name}' pose",
        )
    if target.custom_shape is not shape_before or target.custom_shape_transform is not transform_before:
        raise AssertionError("Reset Control Visual changed the widget or transform reference")

    # POLE_LINE is a generated display helper with an owned widget, making it
    # a stronger exclusion check than a helper that simply lacks a shape.
    helper_bone = arm_rig["line"]
    helper_hidden = (helper_bone.hide, helper_bone.hide_select)
    helper_bone.hide = False
    helper_bone.hide_select = False
    try:
        _assert_visual_excluded(armature, helper_bone.name, "generated Pole Line helper")
    finally:
        helper_bone.hide, helper_bone.hide_select = helper_hidden

    source = armature.pose.bones["shoulder.L"]
    if source.custom_shape is None or not limb_ik._owned(
        source.custom_shape,
        inventory["armature_id"],
        role="WIDGET",
    ):
        raise AssertionError("Source Shoulder fixture did not receive its owned display widget")
    _assert_visual_excluded(armature, source.name, "decorated source Shoulder bone")

    foreign_mesh = bpy.data.meshes.new("ForeignControlVisualMesh")
    foreign_shape = bpy.data.objects.new("ForeignControlVisualShape", foreign_mesh)
    bpy.context.scene.collection.objects.link(foreign_shape)
    generated = armature.pose.bones[arm_rig["target"].name]
    owned_shape = generated.custom_shape
    generated.custom_shape = foreign_shape
    try:
        _assert_visual_excluded(armature, generated.name, "foreign widget on generated Target")
    finally:
        generated.custom_shape = owned_shape
    _assert_visual_eligible(armature, generated.name, "restored generated Target")
    limb_ik._validate_inventory(armature)


def test_control_visual_override_rebuild_and_incremental_master():
    armature, settings = _build_selected(
        "ROLL_DECOUPLED",
        "LEFT_ARM",
        include_right=False,
        name="ControlVisualPersistenceRig",
    )
    inventory = limb_ik._validate_inventory(armature)
    master_bone = inventory["master"]
    master = armature.pose.bones[master_bone.name]
    master_rest = master_bone.matrix_local.copy()
    master_tags = {
        key: master_bone.get(key, None)
        for key in (limb_ik.OWNER_KEY, limb_ik.ARMATURE_ID_KEY, limb_ik.ROLE_KEY)
    }
    master_shape = master.custom_shape
    master_default_raw = master_bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None)
    master_edited = _edited_visual_state(_visual_state(master), seed=0.7)
    _set_visual_state(master, master_edited)

    settings.selected_limb = "LEFT_LEG"
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(f"Incremental Leg Build failed: {settings.last_message}")
    inventory = limb_ik._validate_inventory(armature)
    rebuilt_master_bone = inventory["master"]
    rebuilt_master = armature.pose.bones[rebuilt_master_bone.name]
    base.assert_matrix_close(
        rebuilt_master_bone.matrix_local,
        master_rest,
        "Incremental Build Master Rest",
        location=1.0e-7,
        rotation=1.0e-7,
        scale=1.0e-7,
    )
    if {
        key: rebuilt_master_bone.get(key, None)
        for key in (limb_ik.OWNER_KEY, limb_ik.ARMATURE_ID_KEY, limb_ik.ROLE_KEY)
    } != master_tags:
        raise AssertionError("Incremental Build changed the existing Master's ownership")
    if rebuilt_master.custom_shape is not master_shape:
        raise AssertionError("Incremental Build replaced the existing Master widget")
    if rebuilt_master_bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None) != master_default_raw:
        raise AssertionError("Incremental Build overwrote the Master's stored visual default")
    _assert_visual_state(
        _visual_state(rebuilt_master),
        master_edited,
        "Incremental Build Master override",
    )

    leg_rig = inventory["rigs"][("LEG", "L")]
    target_name = leg_rig["target"].name
    target = armature.pose.bones[target_name]
    old_default = limb_ik._parse_control_visual_state(
        target.bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None),
        f"Control '{target_name}'",
    )
    target_override = _edited_visual_state(_visual_state(target), seed=1.4)
    _set_visual_state(target, target_override)
    old_master_default = limb_ik._parse_control_visual_state(
        rebuilt_master.bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None),
        "Master",
    )

    if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
        raise AssertionError(f"same-schema Rebuild failed: {settings.last_message}")
    inventory = limb_ik._validate_inventory(armature)
    rebuilt_target = armature.pose.bones[inventory["rigs"][("LEG", "L")]["target"].name]
    new_default = limb_ik._parse_control_visual_state(
        rebuilt_target.bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None),
        f"Rebuilt control '{target_name}'",
    )
    expected_target = _expected_rebuilt_override(target_override, old_default, new_default)
    _assert_visual_state(
        _visual_state(rebuilt_target),
        expected_target,
        "same-schema Rebuild Target override",
    )

    final_master = armature.pose.bones[limb_ik.MASTER_NAME]
    new_master_default = limb_ik._parse_control_visual_state(
        final_master.bone.get(limb_ik.CONTROL_VISUAL_DEFAULT_KEY, None),
        "Rebuilt Master",
    )
    expected_master = _expected_rebuilt_override(
        master_edited,
        old_master_default,
        new_master_default,
    )
    _assert_visual_state(
        _visual_state(final_master),
        expected_master,
        "same-schema Rebuild Master override",
    )


def main():
    base.ensure_registered()
    tests = (
        test_auto_align_persistent_direct_and_stable_arm_leg,
        test_auto_align_fitted_right_foot_visual_follows_ankle,
        test_auto_align_nonuniform_target_scale_preserves_or_fails_closed,
        test_auto_reset_visual_uses_manual_default_in_live_end_frame,
        test_auto_align_is_global_and_mismatch_fails_closed,
        test_auto_align_state_survives_rebuild_and_rollback,
        test_control_visual_eligibility_direct_edits_and_reset,
        test_control_visual_override_rebuild_and_incremental_master,
    )
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        base.reset_scene()
        base.ensure_unregistered()
    print(f"PASS Limb IK Auto Align / Control Visual {len(tests)} tests")


if __name__ == "__main__":
    main()
