"""Disposable Blender 5.2 probe for two-bone IK Pole/twist behavior.

This creates only synthetic in-memory armatures.  It never opens or saves X.blend.
Run with::

    blender --background --factory-startup --python tests/probe_two_bone_ik_twist_blender.py
"""

from __future__ import annotations

import json
import math

import bpy
from mathutils import Matrix, Vector


EPS = 1.0e-9


def clamp(value, lower=-1.0, upper=1.0):
    return max(lower, min(upper, value))


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def shortest_rotation_error(actual, expected):
    angle = actual.to_quaternion().rotation_difference(expected.to_quaternion()).angle
    angle = abs(float(angle)) % math.tau
    return min(angle, math.tau - angle)


def project(vector, axis):
    axis = Vector(axis).normalized()
    vector = Vector(vector)
    return vector - axis * vector.dot(axis)


def signed_angle(reference, target, axis):
    axis = Vector(axis).normalized()
    reference = project(reference, axis)
    target = project(target, axis)
    if min(reference.length, target.length) <= EPS:
        return float("nan")
    reference.normalize()
    target.normalize()
    return math.atan2(axis.dot(reference.cross(target)), clamp(reference.dot(target)))


def swing_twist_about_y(rest_matrix, pose_matrix):
    """Twist of pose X vs the minimum-swing transported rest X."""
    rest = rest_matrix.to_3x3()
    pose = pose_matrix.to_3x3()
    rest_x = Vector(rest.col[0]).normalized()
    rest_y = Vector(rest.col[1]).normalized()
    pose_x = Vector(pose.col[0]).normalized()
    pose_y = Vector(pose.col[1]).normalized()
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


def create_fixture(
    upper_roll,
    lower_roll,
    target_position,
    pole_position,
    *,
    use_rotation=False,
    target_twist=0.0,
):
    reset_scene()
    data = bpy.data.armatures.new("SyntheticTwoBoneData")
    rig = bpy.data.objects.new("SyntheticTwoBone", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    upper = data.edit_bones.new("upper")
    upper.head = (0.0, 0.0, 0.0)
    upper.tail = (1.15, 0.42, 0.23)
    upper.roll = upper_roll

    lower = data.edit_bones.new("lower")
    lower.head = upper.tail
    lower.tail = (2.03, 0.08, 0.51)
    lower.parent = upper
    lower.use_connect = True
    lower.roll = lower_roll
    bpy.ops.object.mode_set(mode="POSE")

    rest = {
        "upper": data.bones["upper"].matrix_local.copy(),
        "lower": data.bones["lower"].matrix_local.copy(),
    }
    lengths = (data.bones["upper"].length, data.bones["lower"].length)

    target = bpy.data.objects.new("target", None)
    pole = bpy.data.objects.new("pole", None)
    bpy.context.scene.collection.objects.link(target)
    bpy.context.scene.collection.objects.link(pole)
    target.matrix_world = (
        Matrix.Translation(target_position)
        @ rest["lower"].to_quaternion().to_matrix().to_4x4()
        @ Matrix.Rotation(target_twist, 4, "Y")
    )
    pole.location = pole_position

    constraint = rig.pose.bones["lower"].constraints.new("IK")
    constraint.target = target
    constraint.pole_target = pole
    constraint.chain_count = 2
    constraint.use_stretch = False
    constraint.use_tail = True
    constraint.use_rotation = use_rotation
    bpy.context.view_layer.update()
    return rig, constraint, target, pole, rest, lengths


def desired_joint(start, target, pole, lengths):
    start = Vector(start)
    target = Vector(target)
    pole = Vector(pole)
    chord = target - start
    distance = chord.length
    axis = chord.normalized()
    direction = project(pole - start, axis)
    direction.normalize()
    upper_length, lower_length = lengths
    along = (
        upper_length * upper_length
        - lower_length * lower_length
        + distance * distance
    ) / (2.0 * distance)
    height = math.sqrt(max(0.0, upper_length * upper_length - along * along))
    return start + axis * along + direction * height


def analytic_pole_angle(rest_upper_matrix, start, target, pole, lengths):
    start = Vector(start)
    target = Vector(target)
    pole = Vector(pole)
    joint = desired_joint(start, target, pole, lengths)
    chord = target - start
    normal = chord.cross(pole - start)
    in_plane_cross_section = normal.cross(joint - start)
    upper_x = Vector(rest_upper_matrix.to_3x3().col[0])
    return wrap(-signed_angle(upper_x, in_plane_cross_section, joint - start))


def rest_plane_pole_angle(rest, lengths):
    """The runtime-Pole-independent offset that makes its plane exact."""
    start = Vector(rest["upper"].translation)
    joint = Vector(rest["lower"].translation)
    lower_y = Vector(rest["lower"].to_3x3().col[1]).normalized()
    end = joint + lower_y * lengths[1]
    chord = end - start
    rest_bend = project(joint - start, chord)
    normal = chord.cross(rest_bend)
    in_plane_cross_section = normal.cross(joint - start)
    upper_x = Vector(rest["upper"].to_3x3().col[0])
    return wrap(-signed_angle(upper_x, in_plane_cross_section, joint - start))


def measure(rig, pole, desired, rest):
    upper = rig.pose.bones["upper"]
    lower = rig.pose.bones["lower"]
    start = Vector(upper.head)
    joint = Vector(lower.head)
    end = Vector(lower.tail)
    chord = end - start
    desired_bend = project(Vector(pole.location) - start, chord)
    actual_bend = project(joint - start, chord)
    plane_error = signed_angle(desired_bend, actual_bend, chord)
    return {
        "joint_error": (joint - desired).length,
        "plane_error": plane_error,
        "upper_twist": swing_twist_about_y(rest["upper"], upper.matrix),
        "lower_twist": swing_twist_about_y(rest["lower"], lower.matrix),
        "upper_matrix_error": shortest_rotation_error(upper.matrix, rest["upper"]),
        "lower_matrix_error": shortest_rotation_error(lower.matrix, rest["lower"]),
    }


def optimize_angle(constraint, measure_angle, score):
    """Global grid followed by bounded golden-section refinement."""
    lower = float(constraint.bl_rna.properties["pole_angle"].hard_min)
    upper = float(constraint.bl_rna.properties["pole_angle"].hard_max)
    count = 720
    step = (upper - lower) / count
    cache = {}

    def evaluate(angle):
        angle = max(lower, min(upper, float(angle)))
        key = round(angle, 14)
        if key not in cache:
            constraint.pole_angle = angle
            bpy.context.view_layer.update()
            values = measure_angle()
            cache[key] = (float(constraint.pole_angle), score(values), values)
        return cache[key]

    coarse = [evaluate(lower + index * step) for index in range(count + 1)]
    best_index = min(range(len(coarse)), key=lambda index: coarse[index][1])
    left = lower + max(0, best_index - 1) * step
    right = lower + min(count, best_index + 1) * step
    golden = (math.sqrt(5.0) - 1.0) * 0.5
    x1 = right - golden * (right - left)
    x2 = left + golden * (right - left)
    e1 = evaluate(x1)
    e2 = evaluate(x2)
    for _ in range(48):
        if e1[1] <= e2[1]:
            right, x2, e2 = x2, x1, e1
            x1 = right - golden * (right - left)
            e1 = evaluate(x1)
        else:
            left, x1, e1 = x1, x2, e2
            x2 = left + golden * (right - left)
            e2 = evaluate(x2)
    return min(cache.values(), key=lambda item: item[1])


def run_case(
    label,
    upper_roll,
    lower_roll,
    target_position,
    pole_position,
    *,
    use_rotation=False,
    target_twist=0.0,
):
    rig, constraint, _target, pole, rest, lengths = create_fixture(
        upper_roll,
        lower_roll,
        target_position,
        pole_position,
        use_rotation=use_rotation,
        target_twist=target_twist,
    )
    start = Vector(rest["upper"].translation)
    desired = desired_joint(start, target_position, pole_position, lengths)
    analytic = analytic_pole_angle(rest["upper"], start, target_position, pole_position, lengths)
    exact_plane_formula = rest_plane_pole_angle(rest, lengths)

    measure_angle = lambda: measure(rig, pole, desired, rest)
    plane_angle, _plane_score, at_plane = optimize_angle(
        constraint,
        measure_angle,
        lambda values: values["joint_error"] ** 2,
    )
    upper_angle, _upper_score, at_upper = optimize_angle(
        constraint,
        measure_angle,
        lambda values: 1.0 - math.cos(values["upper_twist"]),
    )
    lower_angle, _lower_score, at_lower = optimize_angle(
        constraint,
        measure_angle,
        lambda values: 1.0 - math.cos(values["lower_twist"]),
    )
    compromise_angle, _compromise_score, at_compromise = optimize_angle(
        constraint,
        measure_angle,
        lambda values: values["upper_twist"] ** 2 + values["lower_twist"] ** 2,
    )

    constraint.pole_angle = analytic
    bpy.context.view_layer.update()
    at_analytic = measure(rig, pole, desired, rest)
    if not use_rotation and abs(wrap(plane_angle - exact_plane_formula)) > 2.0e-5:
        raise AssertionError(
            f"{label}: rest-plane formula {exact_plane_formula} != evaluated optimum {plane_angle}"
        )
    return {
        "label": label,
        "upper_roll": upper_roll,
        "lower_roll": lower_roll,
        "use_rotation": use_rotation,
        "target_twist": target_twist,
        "analytic_angle": analytic,
        "exact_plane_formula": exact_plane_formula,
        "at_analytic": at_analytic,
        "plane_angle": plane_angle,
        "at_plane": at_plane,
        "upper_twist_zero_angle": upper_angle,
        "at_upper_twist_zero": at_upper,
        "lower_twist_zero_angle": lower_angle,
        "at_lower_twist_zero": at_lower,
        "twist_compromise_angle": compromise_angle,
        "at_twist_compromise": at_compromise,
    }


def main():
    source_start = Vector((0.0, 0.0, 0.0))
    source_joint = Vector((1.15, 0.42, 0.23))
    rest_end = Vector((2.03, 0.08, 0.51))
    moved_end = Vector((1.78, -0.31, 0.76))
    source_pole = Vector((0.95, 2.0, 0.35))
    moved_pole = Vector((0.45, 1.63, -0.37))
    source_chord = rest_end - source_start
    source_direction = project(source_joint - source_start, source_chord).normalized()
    aligned_pole = source_joint + source_direction * 1.3
    cases = []
    for upper_roll, lower_roll in (
        (0.0, 0.0),
        (0.7, 0.0),
        (0.0, -1.1),
        (0.7, -1.1),
        (math.pi - 0.03, 1.2),
    ):
        tag = f"u{upper_roll:+.3f}_l{lower_roll:+.3f}"
        cases.append(
            run_case(
                "aligned_rest_target_" + tag,
                upper_roll,
                lower_roll,
                rest_end,
                aligned_pole,
            )
        )
        cases.append(
            run_case(
                "rest_target_" + tag,
                upper_roll,
                lower_roll,
                rest_end,
                source_pole,
            )
        )
        cases.append(
            run_case(
                "moved_target_" + tag,
                upper_roll,
                lower_roll,
                moved_end,
                moved_pole,
            )
        )
    for target_twist in (0.0, math.pi):
        cases.append(
            run_case(
                f"rotation_target_twist_{target_twist:+.3f}",
                0.0,
                0.0,
                rest_end,
                aligned_pole,
                use_rotation=True,
                target_twist=target_twist,
            )
        )
    print("TWO_BONE_IK_TWIST_JSON=" + json.dumps(cases, sort_keys=True))


if __name__ == "__main__":
    main()
