"""Blender 5.2 regression tests for Limb IK bend/roll decoupling.

These tests deliberately model the failure seen on X: the source elbow or
knee has a measurable bend on one side of the limb chord, while the requested
Pole direction is on the opposite side.  A correct rig must satisfy both
requirements independently:

* the evaluated joint follows the requested Pole plane; and
* each deform segment keeps its modeled cross-section through the shortest
  swing that aims local Y along the new segment (no hidden 180-degree roll).

The transported local X/Z axes are the rig-level proxy for the asymmetric
elbow topology: the inset elbow pit must remain on the compression side while
the rounded elbow tip remains on the stretch side when the arm bends back.

Run with Blender 5.2::

    blender --background --factory-startup --python tests/test_limb_ik_roll_decoupling_blender.py

The script creates only factory-startup, in-memory data.  It never opens or
saves the production ``X.blend`` file.
"""

from __future__ import annotations

import math
import os
import sys
import json

import bpy
from mathutils import Matrix, Vector


TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import test_limb_ik_blender as base


limb_ik = base.limb_ik
EPSILON = 1.0e-9
TWIST_LIMIT = math.radians(0.2)
AXIS_DOT_LIMIT = 0.99999
BEND_DOT_LIMIT = 0.999


def _normalized_axis(matrix, index):
    axis = Vector(matrix.to_3x3().col[index])
    if axis.length <= EPSILON:
        raise AssertionError(f"Matrix axis {index} is degenerate")
    return axis.normalized()


def _project_perpendicular(vector, axis):
    vector = Vector(vector)
    axis = Vector(axis)
    if axis.length <= EPSILON:
        raise AssertionError("Cannot project against a degenerate axis")
    axis.normalize()
    return vector - axis * vector.dot(axis)


def _signed_angle(reference, target, axis):
    axis = Vector(axis).normalized()
    reference = _project_perpendicular(reference, axis)
    target = _project_perpendicular(target, axis)
    if min(reference.length, target.length) <= EPSILON:
        raise AssertionError("Cannot measure twist from a degenerate cross-section")
    reference.normalize()
    target.normalize()
    return math.atan2(
        axis.dot(reference.cross(target)),
        max(-1.0, min(1.0, reference.dot(target))),
    )


def _minimum_swing_metrics(reference_matrix, evaluated_matrix):
    """Compare evaluated roll with shortest-arc transport of reference local Y."""
    reference_x = _normalized_axis(reference_matrix, 0)
    reference_y = _normalized_axis(reference_matrix, 1)
    reference_z = _normalized_axis(reference_matrix, 2)
    evaluated_x = _normalized_axis(evaluated_matrix, 0)
    evaluated_y = _normalized_axis(evaluated_matrix, 1)
    evaluated_z = _normalized_axis(evaluated_matrix, 2)

    swing = reference_y.rotation_difference(evaluated_y)
    expected_x = (swing @ reference_x).normalized()
    expected_z = (swing @ reference_z).normalized()
    return {
        "twist": _signed_angle(expected_x, evaluated_x, evaluated_y),
        "x_dot": evaluated_x.dot(expected_x),
        "z_dot": evaluated_z.dot(expected_z),
    }


def _assert_minimum_swing(reference_matrix, pose_bone, label):
    metrics = _minimum_swing_metrics(reference_matrix, pose_bone.matrix)
    if abs(metrics["twist"]) >= TWIST_LIMIT:
        raise AssertionError(
            f"{label} retained {math.degrees(metrics['twist']):.6f} degrees axial twist "
            f"after minimum-swing transport"
        )
    if metrics["x_dot"] <= AXIS_DOT_LIMIT or metrics["z_dot"] <= AXIS_DOT_LIMIT:
        raise AssertionError(
            f"{label} cross-section flipped or drifted: "
            f"X dot={metrics['x_dot']:.9f}, Z dot={metrics['z_dot']:.9f}"
        )


def _assert_solution(armature, key, reference_matrices, label):
    rig = limb_ik._validate_inventory(armature)["rigs"][key]
    upper = armature.pose.bones[rig["chain"][0]]
    lower = armature.pose.bones[rig["chain"][1]]
    end = armature.pose.bones[rig["chain"][2]]
    pole = armature.pose.bones[rig["pole"].name]
    solver_target = armature.pose.bones[rig["solver_target"].name]

    chord = Vector(lower.tail) - Vector(upper.head)
    bend = _project_perpendicular(Vector(lower.head) - Vector(upper.head), chord)
    pole_projection = _project_perpendicular(Vector(pole.head) - Vector(upper.head), chord)
    if min(bend.length, pole_projection.length) <= 1.0e-7:
        raise AssertionError(f"{label} has no measurable evaluated bend/Pole plane")
    bend_dot = bend.normalized().dot(pole_projection.normalized())
    if bend_dot < BEND_DOT_LIMIT:
        raise AssertionError(f"{label} joint bends away from its Pole: dot={bend_dot:.9f}")

    _assert_minimum_swing(reference_matrices[upper.name], upper, f"{label} {upper.name}")
    _assert_minimum_swing(reference_matrices[lower.name], lower, f"{label} {lower.name}")

    endpoint_error = (Vector(lower.tail) - Vector(solver_target.head)).length
    connected_error = (Vector(end.head) - Vector(lower.tail)).length
    end_rotation_error = end.matrix.to_quaternion().rotation_difference(
        solver_target.matrix.to_quaternion()
    ).angle
    if endpoint_error > 2.0e-5:
        raise AssertionError(f"{label} IK endpoint missed its solver target by {endpoint_error}")
    if connected_error > 2.0e-5:
        raise AssertionError(f"{label} Hand/Foot detached from the lower segment by {connected_error}")
    if end_rotation_error > 3.0e-3:
        raise AssertionError(f"{label} Hand/Foot rotation missed its target by {end_rotation_error}")


def _assert_requested_build_direction(armature, key, requested_direction, label):
    """Ensure Build did not make both the Pole and bend agree on the wrong side."""
    rig = limb_ik._validate_inventory(armature)["rigs"][key]
    upper = armature.pose.bones[rig["chain"][0]]
    lower = armature.pose.bones[rig["chain"][1]]
    pole = armature.pose.bones[rig["pole"].name]
    chord = Vector(lower.tail) - Vector(upper.head)
    expected = _project_perpendicular(requested_direction, chord)
    bend = _project_perpendicular(Vector(lower.head) - Vector(upper.head), chord)
    pole_projection = _project_perpendicular(Vector(pole.head) - Vector(upper.head), chord)
    if min(expected.length, bend.length, pole_projection.length) <= 1.0e-7:
        raise AssertionError(f"{label} has a degenerate requested/build direction")
    bend_dot = bend.normalized().dot(expected.normalized())
    pole_dot = pole_projection.normalized().dot(expected.normalized())
    if bend_dot < BEND_DOT_LIMIT or pole_dot < BEND_DOT_LIMIT:
        raise AssertionError(
            f"{label} did not honor the requested anatomical side: "
            f"bend dot={bend_dot:.9f}, Pole dot={pole_dot:.9f}"
        )


def _force_opposite_rest_bend(armature, kind, *, upper_roll, lower_roll, end_roll):
    bpy.ops.object.mode_set(mode="EDIT")
    if kind == "ARM":
        upper = armature.data.edit_bones["upper_arm.L"]
        lower = armature.data.edit_bones["forearm.L"]
        end = armature.data.edit_bones["hand.L"]
        joint = Vector((0.6, -0.12, 1.46))
    else:
        upper = armature.data.edit_bones["thigh.L"]
        lower = armature.data.edit_bones["shin.L"]
        end = armature.data.edit_bones["foot.L"]
        joint = Vector((0.15, 0.10, 0.58))
    upper.tail = joint
    lower.head = joint
    upper.roll = upper_roll
    lower.roll = lower_roll
    end.roll = end_roll
    bpy.ops.object.mode_set(mode="POSE")
    bpy.context.view_layer.update()


def _make_opposite_bend_fixture(kind):
    armature = base.make_humanoid(include_right=False)
    if kind == "ARM":
        _force_opposite_rest_bend(
            armature,
            kind,
            upper_roll=0.73,
            lower_roll=-1.17,
            end_roll=0.41,
        )
    else:
        _force_opposite_rest_bend(
            armature,
            kind,
            upper_roll=-0.61,
            lower_roll=1.03,
            end_roll=-0.37,
        )
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    side = "L"
    key = (kind, side)
    direction = Vector(base.DEFAULT_POLE_DIRECTIONS[kind])
    base.set_pole_direction(settings, kind, side, direction)
    settings.selected_limb = "LEFT_ARM" if kind == "ARM" else "LEFT_LEG"
    names = tuple(
        getattr(settings, limb_ik._field_name(kind, side, role))
        for role in limb_ik.ROLES
    )
    source_bend = base._axis_residual(
        armature.data.bones[names[0]].head_local,
        armature.data.bones[names[1]].head_local,
        armature.data.bones[names[1]].tail_local,
    )
    requested = _project_perpendicular(
        direction,
        Vector(armature.data.bones[names[1]].tail_local)
        - Vector(armature.data.bones[names[0]].head_local),
    )
    if source_bend.normalized().dot(requested.normalized()) > -0.95:
        raise AssertionError(
            f"{key} fixture no longer exercises an opposite bend: "
            f"source={tuple(source_bend)}, requested={tuple(requested)}"
        )
    reference = {
        name: armature.pose.bones[name].matrix.copy()
        for name in names[:2]
    }
    end_before = armature.pose.bones[names[2]].matrix.copy()
    return armature, settings, key, names, reference, end_before


def _translate_control(pose_bone, delta):
    matrix = pose_bone.matrix.copy()
    matrix.translation += Vector(delta)
    pose_bone.matrix = matrix
    bpy.context.view_layer.update()


def _pose_state(pose_bone):
    return {
        "head": [float(value) for value in pose_bone.head],
        "tail": [float(value) for value in pose_bone.tail],
        "matrix": [
            [float(value) for value in row]
            for row in pose_bone.matrix
        ],
    }


def _rebuild_debug_names(armature, rig, source_names):
    names = list(source_names)
    for key in (
        "mch_upper",
        "mch_lower",
        "ori_upper",
        "ori_lower",
        "target",
        "pole",
        "solver_target",
    ):
        bone = rig.get(key)
        if bone is not None and bone.name not in names:
            names.append(bone.name)
    return [name for name in names if armature.pose.bones.get(name) is not None]


def _print_rebuild_diagnostics(armature, source_names, before_states, after_rig):
    names = sorted(set(before_states) | set(_rebuild_debug_names(armature, after_rig, source_names)))
    payload = {"bones": {}}
    for name in names:
        before = before_states.get(name)
        pose_bone = armature.pose.bones.get(name)
        after = _pose_state(pose_bone) if pose_bone is not None else None
        payload["bones"][name] = {"before": before, "after": after}
    payload["source_frame_delta"] = {}
    for name in source_names[:2]:
        before_matrix = before_states[name]["matrix"]
        # Convert the serialized rows back only for diagnostic calculations.
        before_matrix = Matrix(before_matrix)
        after_matrix = armature.pose.bones[name].matrix
        metrics = _minimum_swing_metrics(before_matrix, after_matrix)
        before_y = _normalized_axis(before_matrix, 1)
        after_y = _normalized_axis(after_matrix, 1)
        payload["source_frame_delta"][name] = {
            "rotation_deg": math.degrees(
                before_matrix.to_quaternion().rotation_difference(after_matrix.to_quaternion()).angle
            ),
            "y_axis_deg": math.degrees(before_y.angle(after_y)),
            "minimum_swing_twist_deg": math.degrees(metrics["twist"]),
            "x_dot": metrics["x_dot"],
            "z_dot": metrics["z_dot"],
        }
    print("ROLL_DECOUPLING_REBUILD_DIAGNOSTIC=" + json.dumps(payload, sort_keys=True))


def test_arm_opposite_bend_preserves_roll_dynamically_and_rebuilds_cleanly():
    base.reset_scene()
    armature, settings, key, names, reference, hand_before = _make_opposite_bend_fixture("ARM")

    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()
    _assert_solution(armature, key, reference, "Arm opposite-bend Build")
    _assert_requested_build_direction(
        armature,
        key,
        base.DEFAULT_POLE_DIRECTIONS["ARM"],
        "Arm opposite-bend Build",
    )
    base.assert_matrix_close(
        armature.pose.bones[names[2]].matrix,
        hand_before,
        "Arm opposite-bend Hand no-pop",
    )

    inventory = limb_ik._validate_inventory(armature)
    rig = inventory["rigs"][key]
    target = armature.pose.bones[rig["target"].name]
    pole = armature.pose.bones[rig["pole"].name]
    _translate_control(target, (-0.08, 0.03, 0.05))
    _translate_control(pole, (0.02, 0.11, -0.03))
    _assert_solution(armature, key, reference, "Arm dynamic target/Pole")

    before_rebuild = {
        name: armature.pose.bones[name].matrix.copy()
        for name in names
    }
    before_rig = limb_ik._validate_inventory(armature)["rigs"][key]
    before_debug_states = {
        name: _pose_state(armature.pose.bones[name])
        for name in _rebuild_debug_names(armature, before_rig, names)
    }
    if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()
    after_rig = limb_ik._validate_inventory(armature)["rigs"][key]
    try:
        for name, matrix in before_rebuild.items():
            base.assert_matrix_close(
                armature.pose.bones[name].matrix,
                matrix,
                f"Arm Rebuild no-pop {name}",
            )
    except AssertionError:
        _print_rebuild_diagnostics(armature, names, before_debug_states, after_rig)
        raise

    # A rebuilt schema-3 rig establishes its new orientation helpers from the
    # preserved current pose.  Exercise another live control move against that
    # reference so Rebuild cannot merely bake one correct-looking frame.
    reference_after_rebuild = {
        name: armature.pose.bones[name].matrix.copy()
        for name in names[:2]
    }
    rig = limb_ik._validate_inventory(armature)["rigs"][key]
    _translate_control(armature.pose.bones[rig["target"].name], (-0.035, -0.02, 0.025))
    _translate_control(armature.pose.bones[rig["pole"].name], (-0.01, 0.06, 0.02))
    _assert_solution(armature, key, reference_after_rebuild, "Arm after Rebuild dynamic move")

    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if (
        base.owned_bones(armature)
        or limb_ik._owned_constraint_records(armature)
        or limb_ik.ARMATURE_ID_KEY in armature.data
        or limb_ik.SCHEMA_KEY in armature.data
    ):
        raise AssertionError("Remove left schema-3 roll-decoupling ownership residue")
    remaining_owned_ids = [
        datablock.name
        for datablocks in (
            bpy.data.objects,
            bpy.data.meshes,
            bpy.data.collections,
            armature.data.collections,
        )
        for datablock in datablocks
        if datablock.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
    ]
    if remaining_owned_ids:
        raise AssertionError(f"Remove left owned widgets/collections: {remaining_owned_ids}")
    constrained_sources = {
        pose_bone.name: tuple(constraint.name for constraint in pose_bone.constraints)
        for pose_bone in armature.pose.bones
        if pose_bone.bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE and pose_bone.constraints
    }
    if constrained_sources:
        raise AssertionError(f"Remove left source constraints: {constrained_sources}")


def test_leg_opposite_bend_with_arbitrary_roll_preserves_foot():
    base.reset_scene()
    armature, settings, key, names, reference, foot_before = _make_opposite_bend_fixture("LEG")
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()
    _assert_solution(armature, key, reference, "Leg opposite-bend Build")
    _assert_requested_build_direction(
        armature,
        key,
        base.DEFAULT_POLE_DIRECTIONS["LEG"],
        "Leg opposite-bend Build",
    )
    base.assert_matrix_close(
        armature.pose.bones[names[2]].matrix,
        foot_before,
        "Leg opposite-bend Foot no-pop",
    )

    rig = limb_ik._validate_inventory(armature)["rigs"][key]
    _translate_control(armature.pose.bones[rig["target"].name], (0.03, 0.04, 0.07))
    _translate_control(armature.pose.bones[rig["pole"].name], (-0.025, -0.10, 0.015))
    _assert_solution(armature, key, reference, "Leg dynamic target/Pole")


def main():
    base.ensure_registered()
    tests = (
        test_arm_opposite_bend_preserves_roll_dynamically_and_rebuilds_cleanly,
        test_leg_opposite_bend_with_arbitrary_roll_preserves_foot,
    )
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        base.reset_scene()
        base.ensure_unregistered()
    print(f"PASS Limb IK roll decoupling {len(tests)} tests")


if __name__ == "__main__":
    main()
