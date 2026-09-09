"""Blender 5.2 regressions for the Direct Pre-Roll hand-control frame.

The production failure covered here had two independent symptoms: the hand
Target was authored from the Hand Rest axes instead of the final Forearm axes,
and a world-space end-rotation constraint made the wrist start crooked or
require manual correction.  These tests keep Direct deliberately minimal: each
arm has only Target + Pole as visible controls, plus one hidden, non-deforming
Pole-display helper and its tracking constraint.  They exercise both mirrored
arms and cover the safe upgrade path for legacy WORLD/WORLD wrist-frame rigs.

Run with Blender 5.2::

    blender --background --factory-startup --python tests/test_limb_ik_hand_frame_blender.py

The script creates factory-startup, in-memory data only.  It never opens or
saves the production ``X.blend`` file.
"""

from __future__ import annotations

import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector


TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import test_limb_ik_blender as base


limb_ik = base.limb_ik
FRAME_TOLERANCE = 2.0e-5
ROTATION_TOLERANCE = 4.0e-4


def _matrix_tuple(matrix):
    return tuple(float(value) for row in matrix for value in row)


def _rotation_error(actual, expected):
    return actual.to_quaternion().rotation_difference(expected.to_quaternion()).angle


def _end_rotation_constraint(rig):
    matches = [
        constraint
        for _pose_bone, constraint, record in rig["entries"]
        if record["role"] == "END_ROTATION"
    ]
    if len(matches) != 1:
        raise AssertionError(f"Expected one END_ROTATION constraint, found {len(matches)}")
    return matches[0]


def _assert_pole_display_contract(armature, rig, label):
    display_bone = rig["display"]
    pole_bone = rig["pole"]
    if display_bone is None:
        raise AssertionError(f"{label} has no schema-5 Pole display helper")
    display = armature.pose.bones[display_bone.name]
    pole = armature.pose.bones[pole_bone.name]
    tracks = [
        (owner, constraint)
        for owner, constraint, record in rig["entries"]
        if record["role"] == "POLE_DISPLAY_TRACK"
    ]
    if len(tracks) != 1:
        raise AssertionError(
            f"{label} expected one POLE_DISPLAY_TRACK constraint, found {len(tracks)}"
        )
    owner, track = tracks[0]
    if (
        display_bone.parent is None
        or display_bone.parent.name != pole_bone.name
        or display_bone.use_connect
        or display_bone.use_deform
        or not display_bone.hide
        or not display_bone.hide_select
        or not all(display.lock_location)
        or not all(display.lock_rotation)
        or not all(display.lock_scale)
        or pole.custom_shape_transform is None
        or pole.custom_shape_transform.name != display.name
        or owner.name != display.name
        or track.type != "DAMPED_TRACK"
        or track.target is not armature
        or track.subtarget != rig["chain"][1]
        or track.track_axis != "TRACK_NEGATIVE_Y"
        or track.target_space != "WORLD"
        or track.owner_space != "WORLD"
    ):
        raise AssertionError(f"{label} Pole display helper/track contract is wrong")


def _assert_new_wrist_contract(armature, key, label, *, expect_identity_basis=True):
    rig = limb_ik._validate_inventory(armature)["rigs"][key]
    _assert_pole_display_contract(armature, rig, label)
    lower = armature.data.bones[rig["chain"][1]]
    target_bone = rig["target"]
    target = armature.pose.bones[target_bone.name]

    head_error = (Vector(target_bone.head_local) - Vector(lower.tail_local)).length
    frame_error = _rotation_error(target_bone.matrix_local, lower.matrix_local)
    target_y = Vector(target_bone.matrix_local.to_3x3().col[1]).normalized()
    lower_y = Vector(lower.matrix_local.to_3x3().col[1]).normalized()
    target_z = Vector(target_bone.matrix_local.to_3x3().col[2]).normalized()
    lower_z = Vector(lower.matrix_local.to_3x3().col[2]).normalized()
    if (
        head_error > FRAME_TOLERANCE
        or frame_error > FRAME_TOLERANCE
        or target_y.dot(lower_y) < 1.0 - FRAME_TOLERANCE
        or target_z.dot(lower_z) < 1.0 - FRAME_TOLERANCE
    ):
        raise AssertionError(
            f"{label} Target is not in the final Forearm frame: "
            f"head={head_error}, rotation={frame_error}, "
            f"Y dot={target_y.dot(lower_y)}, Z dot={target_z.dot(lower_z)}"
        )

    if expect_identity_basis:
        base.assert_matrix_close(
            target.matrix_basis,
            Matrix.Identity(4),
            f"{label} Target basis identity",
            location=1.0e-7,
            rotation=1.0e-7,
            scale=1.0e-7,
        )
    end_rotation = _end_rotation_constraint(rig)
    if (
        end_rotation.type != "COPY_ROTATION"
        or end_rotation.target is not armature
        or end_rotation.subtarget != rig["solver_target"].name
        or end_rotation.target_space != "LOCAL_OWNER_ORIENT"
        or end_rotation.owner_space != "LOCAL_WITH_PARENT"
        or getattr(end_rotation, "mix_mode", "") != "REPLACE"
    ):
        raise AssertionError(
            f"{label} END_ROTATION contract is wrong: "
            f"{end_rotation.target_space}->{end_rotation.owner_space}, "
            f"mix={getattr(end_rotation, 'mix_mode', '')}"
        )
    return rig


def _assert_hand_follows_target_basis(armature, key, expected_basis, label):
    rig = limb_ik._validate_inventory(armature)["rigs"][key]
    target = armature.pose.bones[rig["target"].name]
    hand = armature.pose.bones[rig["chain"][2]]
    target_rest = armature.data.bones[target.name].matrix_local
    hand_rest = armature.data.bones[hand.name].matrix_local
    base.assert_matrix_close(
        target.matrix_basis,
        expected_basis,
        f"{label} Target authored XYZ basis",
        location=2.0e-6,
        rotation=2.0e-6,
        scale=2.0e-6,
    )
    target_world_delta = target.matrix.to_quaternion() @ target_rest.to_quaternion().inverted()
    hand_world_delta = hand.matrix.to_quaternion() @ hand_rest.to_quaternion().inverted()
    error = hand_world_delta.rotation_difference(target_world_delta).angle
    if error > ROTATION_TOLERANCE:
        raise AssertionError(
            f"{label} Hand did not inherit the Target's local multi-axis rotation: {error} radians"
        )


def _assert_zero_deformation(armature, names, label):
    """Rest-axis edits must keep the skinned source output at identity."""
    for name in names:
        deform = armature.pose.bones[name].matrix @ armature.data.bones[name].matrix_local.inverted()
        base.assert_matrix_close(
            deform,
            Matrix.Identity(4),
            f"{label} {name} deformation no-pop",
            location=2.0e-5,
            rotation=3.0e-4,
            scale=2.0e-5,
        )


def _build_direct_arms(*, include_right):
    armature = base.make_humanoid(include_right=include_right, roll_offset=0.83)
    hand_names = ("hand.L", "hand.R") if include_right else ("hand.L",)
    hands_before = {
        name: armature.pose.bones[name].matrix.copy()
        for name in hand_names
    }
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_arm() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()
    return armature, settings, hands_before


def _make_legacy_world_wrist(armature, key):
    """Recreate the old wrist frame while retaining schema-5 display plumbing."""
    rig = limb_ik._validate_inventory(armature)["rigs"][key]
    target_name = rig["target"].name
    target_bone = armature.data.bones[target_name]
    target_length = max(float(target_bone.length), 1.0e-4)
    hand_name = rig["chain"][2]

    bpy.ops.object.mode_set(mode="EDIT")
    target_edit = armature.data.edit_bones[target_name]
    hand_edit = armature.data.edit_bones[hand_name]
    hand_axis = Vector(hand_edit.tail) - Vector(hand_edit.head)
    target_edit.head = Vector(hand_edit.head)
    target_edit.tail = Vector(hand_edit.head) + hand_axis.normalized() * target_length
    target_edit.align_roll(Vector(hand_edit.matrix.to_3x3().col[2]))
    bpy.ops.object.mode_set(mode="POSE")
    target_pose = armature.pose.bones[target_name]
    target_pose.matrix_basis = Matrix.Identity(4)
    target_pose.custom_shape_rotation_euler = (0.0, 0.0, 0.0)

    legacy_rig = limb_ik._validate_inventory(armature)["rigs"][key]
    end_rotation = _end_rotation_constraint(legacy_rig)
    end_rotation.target_space = "WORLD"
    end_rotation.owner_space = "WORLD"
    end_rotation.mix_mode = "REPLACE"
    bpy.context.view_layer.update()

    legacy_rig = limb_ik._validate_inventory(armature)["rigs"][key]
    legacy_target = legacy_rig["target"]
    hand_bone = armature.data.bones[hand_name]
    legacy_constraint = _end_rotation_constraint(legacy_rig)
    frame_error = _rotation_error(legacy_target.matrix_local, hand_bone.matrix_local)
    if (
        frame_error > FRAME_TOLERANCE
        or legacy_constraint.target_space != "WORLD"
        or legacy_constraint.owner_space != "WORLD"
    ):
        raise AssertionError(
            "Legacy fixture did not reproduce the old WORLD/WORLD Hand frame: "
            f"rotation={frame_error}, "
            f"spaces={legacy_constraint.target_space}/{legacy_constraint.owner_space}"
        )
    return legacy_rig


def _primary_rig_signature(armature):
    inventory = limb_ik._validate_inventory(armature)
    owned_names = {bone.name for bone in inventory["bones"]}
    source_names = {
        name
        for rig in inventory["rigs"].values()
        for name in rig["chain"]
    }
    watched_names = sorted(owned_names | source_names)
    bones = tuple(
        (
            name,
            _matrix_tuple(armature.data.bones[name].matrix_local),
            armature.data.bones[name].parent.name if armature.data.bones[name].parent else "",
            bool(armature.data.bones[name].use_connect),
            _matrix_tuple(armature.pose.bones[name].matrix_basis),
        )
        for name in watched_names
    )
    constraints = tuple(
        sorted(
            (
                pose_bone.name,
                constraint.name,
                constraint.type,
                constraint.target_space,
                constraint.owner_space,
                getattr(constraint, "mix_mode", ""),
                constraint.subtarget,
                record["rig_id"],
                record["role"],
            )
            for pose_bone, constraint, record in inventory["records"]
        )
    )
    rig_ids = tuple(sorted(rig["rig_id"] for rig in inventory["rigs"].values()))
    metadata = tuple(
        (key, armature.data.get(key, None))
        for key in (limb_ik.ARMATURE_ID_KEY, limb_ik.SCHEMA_KEY, limb_ik.DIRECT_REST_KEY)
    )
    return bones, constraints, rig_ids, metadata


def test_direct_hand_frame_rotation_and_rebuild_are_stable():
    base.reset_scene()
    armature, settings, hands_before = _build_direct_arms(include_right=True)
    inventory = limb_ik._validate_inventory(armature)
    if set(inventory["rigs"]) != {("ARM", "L"), ("ARM", "R")}:
        raise AssertionError(f"Direct Arm build produced the wrong limbs: {set(inventory['rigs'])}")
    if (
        inventory["schema"] != limb_ik.DIRECT_PREROLL_SCHEMA
        or len(inventory["bones"]) != 6
        or len(inventory["records"]) != 8
    ):
        raise AssertionError(
            "Direct Arm build was not Target + Pole + hidden Pole display per side"
        )
    expected_roles = {
        "IK",
        "END_ROTATION",
        "AUTO_OFFSET_ROTATION",
        "POLE_DISPLAY_TRACK",
    }
    for key, rig in inventory["rigs"].items():
        roles = {record["role"] for _owner, _constraint, record in rig["entries"]}
        if roles != expected_roles:
            raise AssertionError(f"{key} Direct constraint roles are wrong: {roles}")

    for side in limb_ik.SIDES:
        key = ("ARM", side)
        rig = _assert_new_wrist_contract(armature, key, f"{side} Build")
        _assert_zero_deformation(armature, rig["chain"], f"{side} Direct Build")
        base.assert_matrix_close(
            armature.pose.bones[rig["chain"][2]].matrix,
            hands_before[rig["chain"][2]],
            f"{side} Direct Hand Build no-pop",
            location=2.0e-5,
            rotation=3.0e-4,
            scale=2.0e-5,
        )

    requested_basis = Euler((0.37, -0.29, 0.46), "XYZ").to_matrix().to_4x4()
    for side in limb_ik.SIDES:
        rig = limb_ik._validate_inventory(armature)["rigs"][("ARM", side)]
        armature.pose.bones[rig["target"].name].matrix_basis = requested_basis.copy()
    bpy.context.view_layer.update()
    for side in limb_ik.SIDES:
        _assert_hand_follows_target_basis(
            armature,
            ("ARM", side),
            requested_basis,
            f"{side} dynamic XYZ",
        )

    baseline = {}
    for side in limb_ik.SIDES:
        key = ("ARM", side)
        rig = limb_ik._validate_inventory(armature)["rigs"][key]
        baseline[key] = {
            "target": armature.pose.bones[rig["target"].name].matrix.copy(),
            "target_basis": armature.pose.bones[rig["target"].name].matrix_basis.copy(),
            "source_pose": {
                name: armature.pose.bones[name].matrix.copy()
                for name in rig["chain"]
            },
            "lower_rest": armature.data.bones[rig["chain"][1]].matrix_local.copy(),
        }

    for rebuild_index in (1, 2):
        if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
            raise AssertionError(settings.last_message)
        bpy.context.view_layer.update()
        for side in limb_ik.SIDES:
            key = ("ARM", side)
            rig = _assert_new_wrist_contract(
                armature,
                key,
                f"{side} Rebuild {rebuild_index}",
                expect_identity_basis=False,
            )
            target = armature.pose.bones[rig["target"].name]
            base.assert_matrix_close(
                target.matrix,
                baseline[key]["target"],
                f"{side} Rebuild {rebuild_index} Target no-drift",
                location=3.0e-5,
                rotation=4.0e-4,
                scale=3.0e-5,
            )
            base.assert_matrix_close(
                target.matrix_basis,
                baseline[key]["target_basis"],
                f"{side} Rebuild {rebuild_index} Target basis no-drift",
                location=2.0e-6,
                rotation=2.0e-6,
                scale=2.0e-6,
            )
            for name, expected in baseline[key]["source_pose"].items():
                base.assert_matrix_close(
                    armature.pose.bones[name].matrix,
                    expected,
                    f"{side} Rebuild {rebuild_index} {name} no-drift",
                    location=3.0e-5,
                    rotation=4.0e-4,
                    scale=3.0e-5,
                )
            base.assert_matrix_close(
                armature.data.bones[rig["chain"][1]].matrix_local,
                baseline[key]["lower_rest"],
                f"{side} Rebuild {rebuild_index} Forearm Rest no-drift",
                location=2.0e-6,
                rotation=2.0e-6,
                scale=2.0e-6,
            )
            _assert_hand_follows_target_basis(
                armature,
                key,
                requested_basis,
                f"{side} Rebuild {rebuild_index} dynamic XYZ",
            )


def test_untouched_legacy_world_wrist_migrates_without_pop():
    base.reset_scene()
    armature, settings, _hands_before = _build_direct_arms(include_right=False)
    key = ("ARM", "L")
    legacy_rig = _make_legacy_world_wrist(armature, key)
    legacy_target_rest = legacy_rig["target"].matrix_local.copy()
    lower_rest = armature.data.bones[legacy_rig["chain"][1]].matrix_local
    if _rotation_error(legacy_target_rest, lower_rest) < 0.02:
        raise AssertionError("Legacy fixture is not materially different from the final Forearm frame")
    source_before = {
        name: armature.pose.bones[name].matrix.copy()
        for name in legacy_rig["chain"]
    }

    if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()
    rebuilt = _assert_new_wrist_contract(armature, key, "Legacy migration")
    for name, expected in source_before.items():
        base.assert_matrix_close(
            armature.pose.bones[name].matrix,
            expected,
            f"Legacy migration {name} no-pop",
            location=3.0e-5,
            rotation=4.0e-4,
            scale=3.0e-5,
        )
    if _rotation_error(rebuilt["target"].matrix_local, legacy_target_rest) < 0.02:
        raise AssertionError("Legacy Rebuild did not replace the old Hand-frame Target Rest axes")


def test_posed_legacy_world_wrist_is_rejected_without_mutation():
    base.reset_scene()
    armature, settings, _hands_before = _build_direct_arms(include_right=False)
    key = ("ARM", "L")
    legacy_rig = _make_legacy_world_wrist(armature, key)
    target = armature.pose.bones[legacy_rig["target"].name]
    target.matrix_basis = Euler((0.24, -0.31, 0.19), "XYZ").to_matrix().to_4x4()
    bpy.context.view_layer.update()

    end_rotation = _end_rotation_constraint(legacy_rig)
    constraint_pointer = end_rotation.as_pointer()
    target_before = target.matrix.copy()
    source_before = {
        name: armature.pose.bones[name].matrix.copy()
        for name in legacy_rig["chain"]
    }
    before = _primary_rig_signature(armature)

    if base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild) != {"CANCELLED"}:
        raise AssertionError("Rebuild accepted a posed legacy WORLD/WORLD hand Target")
    bpy.context.view_layer.update()
    after = _primary_rig_signature(armature)
    if after != before:
        raise AssertionError("Rejected legacy wrist migration changed primary rig state")

    preserved_rig = limb_ik._validate_inventory(armature)["rigs"][key]
    preserved_constraint = _end_rotation_constraint(preserved_rig)
    if (
        preserved_constraint.as_pointer() != constraint_pointer
        or preserved_constraint.target_space != "WORLD"
        or preserved_constraint.owner_space != "WORLD"
    ):
        raise AssertionError("Rejected migration replaced or rewrote the legacy END_ROTATION constraint")
    base.assert_matrix_close(
        armature.pose.bones[preserved_rig["target"].name].matrix,
        target_before,
        "Rejected migration Target pose",
        location=2.0e-6,
        rotation=2.0e-6,
        scale=2.0e-6,
    )
    for name, expected in source_before.items():
        base.assert_matrix_close(
            armature.pose.bones[name].matrix,
            expected,
            f"Rejected migration {name} pose",
            location=2.0e-6,
            rotation=2.0e-6,
            scale=2.0e-6,
        )
    if "Rest transform" not in settings.last_message:
        raise AssertionError(f"Legacy refusal was not actionable: {settings.last_message}")


def main():
    base.ensure_registered()
    tests = (
        test_direct_hand_frame_rotation_and_rebuild_are_stable,
        test_untouched_legacy_world_wrist_migrates_without_pop,
        test_posed_legacy_world_wrist_is_rejected_without_mutation,
    )
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        base.reset_scene()
        base.ensure_unregistered()
    print(f"PASS Limb IK Direct hand frame {len(tests)} tests")


if __name__ == "__main__":
    main()
