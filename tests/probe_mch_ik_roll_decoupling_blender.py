"""Synthetic proof that IK bend-plane control and deform-bone roll can be decoupled.

The file under test is never opened or saved.  Three in-memory rigs are compared:

* ``DIRECT``: IK is placed on the deform/source chain.
* ``MCH_COPY``: an IK MCH chain is copied wholesale to the source chain.
* ``MCH_DIRECT_TRACK``: connected source bones directly Damped-Track the MCH
  endpoints, exposing the inherited-parent roll left on the lower segment.
* ``MCH_MIN_SWING``: IK supplies only MCH head/tail positions; independent
  orientation helpers Damped-Track their matching MCH tails and the source
  chain copies those minimum-swing frames.
* ``MCH_MIN_SWING_ROT``: the same helpers drive only source world rotation,
  leaving source location and scale completely untouched.

Run with Blender 5.2::

    blender --background --factory-startup --python tests/probe_mch_ik_roll_decoupling_blender.py
"""

from __future__ import annotations

import json
import math

import bpy
from mathutils import Matrix, Quaternion, Vector


EPS = 1.0e-9
S = Vector((0.0, 0.0, 0.0))
J = Vector((1.15, 0.42, 0.23))
E = Vector((2.03, 0.08, 0.51))


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def project(vector, axis):
    vector = Vector(vector)
    axis = Vector(axis).normalized()
    return vector - axis * vector.dot(axis)


def signed_angle(reference, target, axis):
    axis = Vector(axis).normalized()
    reference = project(reference, axis)
    target = project(target, axis)
    if min(reference.length, target.length) <= EPS:
        raise AssertionError("Degenerate signed-angle input")
    reference.normalize()
    target.normalize()
    return math.atan2(
        axis.dot(reference.cross(target)),
        max(-1.0, min(1.0, reference.dot(target))),
    )


def minimum_swing_twist(rest_matrix, pose_matrix):
    """Residual axial twist after shortest-arc transport of rest local Y."""
    rest_rotation = rest_matrix.to_3x3()
    pose_rotation = pose_matrix.to_3x3()
    rest_x = Vector(rest_rotation.col[0]).normalized()
    rest_y = Vector(rest_rotation.col[1]).normalized()
    pose_x = Vector(pose_rotation.col[0]).normalized()
    pose_y = Vector(pose_rotation.col[1]).normalized()
    transported_x = rest_y.rotation_difference(pose_y) @ rest_x
    return signed_angle(transported_x, pose_x, pose_y)


def reset_scene():
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for data in tuple(bpy.data.armatures):
        if data.users == 0:
            bpy.data.armatures.remove(data)


def add_bone(
    edit_bones,
    name,
    head,
    tail,
    roll,
    parent=None,
    *,
    connect=None,
    deform=False,
):
    bone = edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    bone.roll = roll
    bone.parent = parent
    if connect is None:
        connect = parent is not None and (Vector(parent.tail) - Vector(head)).length <= EPS
    bone.use_connect = bool(connect)
    bone.use_deform = deform
    return bone


def rest_plane_pole_angle(rest_upper_matrix):
    """Pole angle making Blender's joint follow its Pole plane for this chain.

    The reference is the chain's own non-degenerate rest bend, not the requested
    runtime Pole direction.  Runtime target/Pole positions do not enter the
    result; upper-bone rest roll does.
    """
    chord = E - S
    bend = project(J - S, chord).normalized()
    normal = chord.cross(bend)
    in_plane_cross_section = normal.cross(J - S)
    upper_x = Vector(rest_upper_matrix.to_3x3().col[0])
    return wrap(-signed_angle(upper_x, in_plane_cross_section, J - S))


def desired_joint(start, target_position, pole_position, lengths):
    start = Vector(start)
    chord = Vector(target_position) - start
    distance = chord.length
    axis = chord.normalized()
    bend = project(Vector(pole_position) - start, axis).normalized()
    upper_length, lower_length = lengths
    along = (
        upper_length * upper_length
        - lower_length * lower_length
        + distance * distance
    ) / (2.0 * distance)
    height = math.sqrt(max(0.0, upper_length * upper_length - along * along))
    return start + axis * along + bend * height


def create_rig(
    mode,
    upper_roll,
    lower_roll,
    target_position,
    pole_position,
    *,
    parent_rotation=0.0,
):
    reset_scene()
    data = bpy.data.armatures.new("SyntheticRollDecouplingData")
    rig = bpy.data.objects.new("SyntheticRollDecoupling", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    root = add_bone(
        data.edit_bones,
        "ROOT",
        (-0.37, -0.29, -0.41),
        S,
        0.31,
    )
    src_upper = add_bone(data.edit_bones, "SRC_upper", S, J, upper_roll, root, deform=True)
    add_bone(data.edit_bones, "SRC_lower", J, E, lower_roll, src_upper, deform=True)

    if mode != "DIRECT":
        mch_upper = add_bone(data.edit_bones, "MCH_upper", S, J, upper_roll, root)
        add_bone(data.edit_bones, "MCH_lower", J, E, lower_roll, mch_upper)
    if mode in {"MCH_MIN_SWING", "MCH_MIN_SWING_ROT"}:
        # These are deliberately unparented.  Each retains its source bone's
        # own rest cross-section before independently taking MCH head/tail data.
        add_bone(data.edit_bones, "ORI_upper", S, J, upper_roll, root)
        add_bone(data.edit_bones, "ORI_lower", J, E, lower_roll, root, connect=False)
    bpy.ops.object.mode_set(mode="POSE")

    root_pose = rig.pose.bones["ROOT"]
    root_pose.rotation_mode = "QUATERNION"
    root_pose.rotation_quaternion = Quaternion((0.31, -0.52, 0.79), parent_rotation)
    root_pose.location = Vector((0.17, -0.09, 0.13)) * abs(parent_rotation)
    bpy.context.view_layer.update()
    parent_delta = root_pose.matrix @ data.bones["ROOT"].matrix_local.inverted()
    evaluated_start = parent_delta @ S
    evaluated_target = parent_delta @ Vector(target_position)
    evaluated_pole = parent_delta @ Vector(pole_position)
    rest = {
        name: rig.pose.bones[name].matrix.copy()
        for name in ("SRC_upper", "SRC_lower")
    }
    lengths = (data.bones["SRC_upper"].length, data.bones["SRC_lower"].length)

    target = bpy.data.objects.new("IK_target", None)
    pole = bpy.data.objects.new("IK_pole", None)
    bpy.context.scene.collection.objects.link(target)
    bpy.context.scene.collection.objects.link(pole)
    target.location = evaluated_target
    pole.location = evaluated_pole

    ik_tip_name = "SRC_lower" if mode == "DIRECT" else "MCH_lower"
    ik_upper_name = "SRC_upper" if mode == "DIRECT" else "MCH_upper"
    ik = rig.pose.bones[ik_tip_name].constraints.new("IK")
    ik.target = target
    ik.pole_target = pole
    ik.chain_count = 2
    ik.use_stretch = False
    ik.use_tail = True
    ik.use_rotation = False
    ik.pole_angle = rest_plane_pole_angle(data.bones[ik_upper_name].matrix_local)

    if mode == "MCH_COPY":
        for segment in ("upper", "lower"):
            copy = rig.pose.bones[f"SRC_{segment}"].constraints.new("COPY_TRANSFORMS")
            copy.target = rig
            copy.subtarget = f"MCH_{segment}"
            copy.target_space = "WORLD"
            copy.owner_space = "WORLD"
            copy.mix_mode = "REPLACE"
    elif mode == "MCH_DIRECT_TRACK":
        for segment in ("upper", "lower"):
            track = rig.pose.bones[f"SRC_{segment}"].constraints.new("DAMPED_TRACK")
            track.target = rig
            track.subtarget = f"MCH_{segment}"
            track.head_tail = 1.0
            track.track_axis = "TRACK_Y"
    elif mode in {"MCH_MIN_SWING", "MCH_MIN_SWING_ROT"}:
        for segment in ("upper", "lower"):
            helper = rig.pose.bones[f"ORI_{segment}"]
            location = helper.constraints.new("COPY_LOCATION")
            location.target = rig
            location.subtarget = f"MCH_{segment}"
            location.head_tail = 0.0
            location.target_space = "WORLD"
            location.owner_space = "WORLD"

            track = helper.constraints.new("DAMPED_TRACK")
            track.target = rig
            track.subtarget = f"MCH_{segment}"
            track.head_tail = 1.0
            track.track_axis = "TRACK_Y"

            copy = rig.pose.bones[f"SRC_{segment}"].constraints.new(
                "COPY_ROTATION" if mode == "MCH_MIN_SWING_ROT" else "COPY_TRANSFORMS"
            )
            copy.target = rig
            copy.subtarget = f"ORI_{segment}"
            copy.target_space = "WORLD"
            copy.owner_space = "WORLD"
            copy.mix_mode = "REPLACE"

    # Force a fresh dependency graph after adding same-armature dependencies.
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.context.view_layer.update()
    return rig, rest, lengths, ik, evaluated_start, evaluated_target, evaluated_pole


def measure(rig, rest, start, target_position, pole_position, lengths):
    upper = rig.pose.bones["SRC_upper"]
    lower = rig.pose.bones["SRC_lower"]
    expected_joint = desired_joint(start, target_position, pole_position, lengths)
    actual_joint = Vector(lower.head)
    actual_end = Vector(lower.tail)
    result = {
        "joint_error": (actual_joint - expected_joint).length,
        "end_error": (actual_end - Vector(target_position)).length,
        "upper_twist_deg": math.degrees(minimum_swing_twist(rest["SRC_upper"], upper.matrix)),
        "lower_twist_deg": math.degrees(minimum_swing_twist(rest["SRC_lower"], lower.matrix)),
    }
    if "MCH_lower" in rig.pose.bones:
        mch_upper = rig.pose.bones["MCH_upper"]
        mch_lower = rig.pose.bones["MCH_lower"]
        result.update(
            mch_joint_error=(Vector(mch_lower.head) - expected_joint).length,
            mch_end_error=(Vector(mch_lower.tail) - Vector(target_position)).length,
            source_mch_joint_error=(actual_joint - Vector(mch_lower.head)).length,
            source_mch_end_error=(actual_end - Vector(mch_lower.tail)).length,
        )
    if "ORI_lower" in rig.pose.bones:
        result.update(
            upper_helper_matrix_error=max(
                abs(value)
                for row in (upper.matrix - rig.pose.bones["ORI_upper"].matrix)
                for value in row
            ),
            lower_helper_matrix_error=max(
                abs(value)
                for row in (lower.matrix - rig.pose.bones["ORI_lower"].matrix)
                for value in row
            ),
        )
    return result


def rotated_rest_pole(degrees):
    chord = E - S
    source_bend = project(J - S, chord).normalized()
    bend = Matrix.Rotation(math.radians(degrees), 3, chord.normalized()) @ source_bend
    chord_midpoint = S + chord * 0.5
    return chord_midpoint + bend * 1.8


def run_case(
    label,
    target_position,
    pole_position,
    upper_roll,
    lower_roll,
    *,
    parent_rotation=0.0,
):
    modes = {}
    angles = {}
    for mode in (
        "DIRECT",
        "MCH_COPY",
        "MCH_DIRECT_TRACK",
        "MCH_MIN_SWING",
        "MCH_MIN_SWING_ROT",
    ):
        rig, rest, lengths, ik, start, evaluated_target, evaluated_pole = create_rig(
            mode,
            upper_roll,
            lower_roll,
            target_position,
            pole_position,
            parent_rotation=parent_rotation,
        )
        angles[mode] = float(ik.pole_angle)
        modes[mode] = measure(
            rig,
            rest,
            start,
            evaluated_target,
            evaluated_pole,
            lengths,
        )

    for mode, values in modes.items():
        if values["joint_error"] > 2.0e-5 or values["end_error"] > 2.0e-5:
            raise AssertionError(f"{label} {mode} missed IK geometry: {values}")
    decoupled = modes["MCH_MIN_SWING"]
    if max(abs(decoupled["upper_twist_deg"]), abs(decoupled["lower_twist_deg"])) > 2.0e-3:
        raise AssertionError(f"{label} minimum-swing output retained axial twist: {decoupled}")
    if max(decoupled["upper_helper_matrix_error"], decoupled["lower_helper_matrix_error"]) > 2.0e-5:
        raise AssertionError(f"{label} source chain did not copy helper frames exactly: {decoupled}")
    return {
        "label": label,
        "upper_roll": upper_roll,
        "lower_roll": lower_roll,
        "parent_rotation": parent_rotation,
        "pole_angles": angles,
        "modes": modes,
    }


def run_pole_sweep():
    """Exercise one live rig across many Pole planes (not fresh rigs per sample)."""
    rig, rest, lengths, _ik, start, evaluated_target, _evaluated_pole = create_rig(
        "MCH_MIN_SWING",
        0.73,
        -1.17,
        E,
        rotated_rest_pole(-175.0),
        parent_rotation=0.91,
    )
    root_pose = rig.pose.bones["ROOT"]
    parent_delta = root_pose.matrix @ rig.data.bones["ROOT"].matrix_local.inverted()
    target = bpy.data.objects["IK_target"]
    pole = bpy.data.objects["IK_pole"]
    maxima = {
        "joint_error": 0.0,
        "end_error": 0.0,
        "upper_twist_deg": 0.0,
        "lower_twist_deg": 0.0,
    }
    count = 0
    for degrees in range(-175, 176, 5):
        target.location = evaluated_target
        evaluated_pole = parent_delta @ rotated_rest_pole(float(degrees))
        pole.location = evaluated_pole
        bpy.context.view_layer.update()
        values = measure(rig, rest, start, evaluated_target, evaluated_pole, lengths)
        for key in maxima:
            maxima[key] = max(maxima[key], abs(values[key]))
        count += 1
    if maxima["joint_error"] > 2.0e-5 or maxima["end_error"] > 2.0e-5:
        raise AssertionError(f"live Pole sweep missed IK geometry: {maxima}")
    if max(maxima["upper_twist_deg"], maxima["lower_twist_deg"]) > 2.0e-3:
        raise AssertionError(f"live Pole sweep introduced axial twist: {maxima}")
    return {"samples": count, "maxima": maxima}


def main():
    cases = []
    for upper_roll, lower_roll in ((0.0, 0.0), (0.73, -1.17), (math.pi - 0.03, 1.2)):
        tag = f"u{upper_roll:+.3f}_l{lower_roll:+.3f}"
        cases.append(run_case("rest_flip_164_" + tag, E, rotated_rest_pole(164.0), upper_roll, lower_roll))
        cases.append(
            run_case(
                "moved_target_" + tag,
                Vector((1.78, -0.31, 0.76)),
                Vector((0.45, 1.63, -0.37)),
                upper_roll,
                lower_roll,
            )
        )
    cases.append(
        run_case(
            "moved_target_rotated_parent",
            Vector((1.78, -0.31, 0.76)),
            Vector((0.45, 1.63, -0.37)),
            0.73,
            -1.17,
            parent_rotation=0.91,
        )
    )
    sweep = run_pole_sweep()
    print("MCH_IK_ROLL_DECOUPLING_JSON=" + json.dumps(cases, sort_keys=True))
    print("MCH_IK_ROLL_SWEEP_JSON=" + json.dumps(sweep, sort_keys=True))
    print(f"PASS MCH IK roll decoupling {len(cases)} cases")


if __name__ == "__main__":
    main()
