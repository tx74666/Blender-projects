"""Randomized synthetic verification of Blender two-bone IK Pole Angle math.

No production file/add-on module is imported or modified.
"""

from __future__ import annotations

import json
import math
import random

import bpy
from mathutils import Matrix, Vector


EPS = 1.0e-9
RNG = random.Random(0xC0DE52)
GEOMETRY_TOLERANCE = 3.0e-4
ANGLE_TOLERANCE = 1.0e-5


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def random_unit():
    while True:
        vector = Vector((RNG.uniform(-1.0, 1.0), RNG.uniform(-1.0, 1.0), RNG.uniform(-1.0, 1.0)))
        if vector.length > 0.2:
            return vector.normalized()


def project(vector, axis):
    axis = Vector(axis).normalized()
    vector = Vector(vector)
    return vector - axis * vector.dot(axis)


def signed_angle(reference, target, axis):
    axis = Vector(axis).normalized()
    reference = project(reference, axis).normalized()
    target = project(target, axis).normalized()
    return math.atan2(
        axis.dot(reference.cross(target)),
        max(-1.0, min(1.0, reference.dot(target))),
    )


def exact_plane_angle(rest_upper_matrix, start, joint, end):
    chord = Vector(end) - Vector(start)
    bend = project(Vector(joint) - Vector(start), chord)
    if bend.length <= EPS:
        raise AssertionError("Random fixture unexpectedly straight")
    upper_y = (Vector(joint) - Vector(start)).normalized()
    normal = chord.cross(bend)
    cross_section = normal.cross(upper_y)
    upper_x = Vector(rest_upper_matrix.to_3x3().col[0])
    return wrap(-signed_angle(upper_x, cross_section, upper_y))


def desired_joint(start, target, pole, upper_length, lower_length):
    start = Vector(start)
    chord = Vector(target) - start
    distance = chord.length
    axis = chord.normalized()
    bend = project(Vector(pole) - start, axis).normalized()
    along = (
        upper_length * upper_length
        - lower_length * lower_length
        + distance * distance
    ) / (2.0 * distance)
    height = math.sqrt(max(0.0, upper_length * upper_length - along * along))
    return start + axis * along + bend * height


def reset_scene():
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for data in tuple(bpy.data.armatures):
        if data.users == 0:
            bpy.data.armatures.remove(data)


def solve(geometry, upper_roll, lower_roll):
    start, joint, end, target_position, pole_position = geometry
    upper_length = (joint - start).length
    lower_length = (end - joint).length
    reset_scene()
    data = bpy.data.armatures.new("RandomTwoBoneData")
    rig = bpy.data.objects.new("RandomTwoBone", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    upper = data.edit_bones.new("upper")
    upper.head, upper.tail, upper.roll = start, joint, upper_roll
    lower = data.edit_bones.new("lower")
    lower.head, lower.tail, lower.roll = joint, end, lower_roll
    lower.parent, lower.use_connect = upper, True
    bpy.ops.object.mode_set(mode="POSE")

    target = bpy.data.objects.new("target", None)
    pole = bpy.data.objects.new("pole", None)
    bpy.context.scene.collection.objects.link(target)
    bpy.context.scene.collection.objects.link(pole)
    target.location, pole.location = target_position, pole_position
    ik = rig.pose.bones["lower"].constraints.new("IK")
    ik.target, ik.pole_target = target, pole
    ik.chain_count, ik.use_stretch, ik.use_tail, ik.use_rotation = 2, False, True, False
    ik.iterations = 500
    angle = exact_plane_angle(data.bones["upper"].matrix_local, start, joint, end)
    ik.pole_angle = angle
    rig.data.update_tag()
    rig.update_tag(refresh={"OBJECT"})
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()

    expected = desired_joint(start, target_position, pole_position, upper_length, lower_length)
    actual = Vector(rig.pose.bones["lower"].head)
    endpoint = Vector(rig.pose.bones["lower"].tail)
    return angle, (actual - expected).length, (endpoint - target_position).length


def random_geometry():
    start = random_unit() * RNG.uniform(0.0, 0.8)
    upper_direction = random_unit()
    hinge_axis = upper_direction.cross(random_unit())
    while hinge_axis.length < 0.1:
        hinge_axis = upper_direction.cross(random_unit())
    hinge_axis.normalize()
    lower_direction = Matrix.Rotation(
        RNG.uniform(math.radians(15.0), math.radians(125.0)),
        3,
        hinge_axis,
    ) @ upper_direction
    upper_length = RNG.uniform(0.55, 1.45)
    lower_length = RNG.uniform(0.55, 1.45)
    joint = start + upper_direction * upper_length
    end = joint + lower_direction * lower_length

    target_direction = random_unit()
    minimum = abs(upper_length - lower_length) + min(upper_length, lower_length) * 0.18
    maximum = upper_length + lower_length - min(upper_length, lower_length) * 0.18
    target = start + target_direction * RNG.uniform(minimum, maximum)
    bend = project(random_unit(), target_direction)
    while bend.length < 0.1:
        bend = project(random_unit(), target_direction)
    pole = start + (target - start) * RNG.uniform(0.2, 0.8) + bend.normalized() * RNG.uniform(0.8, 2.0)
    return start, joint, end, target, pole


def main():
    maximum_joint_error = 0.0
    maximum_endpoint_error = 0.0
    maximum_lower_roll_angle_change = 0.0
    maximum_upper_roll_law_error = 0.0
    fixtures = 16
    solves = 0
    failures = []
    for fixture_index in range(fixtures):
        geometry = random_geometry()
        upper_roll = RNG.uniform(-math.pi, math.pi)
        lower_roll = RNG.uniform(-math.pi, math.pi)
        base, joint_error, endpoint_error = solve(geometry, upper_roll, lower_roll)
        lower_changed, joint_error_2, endpoint_error_2 = solve(
            geometry,
            upper_roll,
            wrap(lower_roll + 1.173),
        )
        upper_changed, joint_error_3, endpoint_error_3 = solve(
            geometry,
            wrap(upper_roll + 0.619),
            lower_roll,
        )
        for variant, angle, j_error, e_error in (
            ("base", base, joint_error, endpoint_error),
            ("lower", lower_changed, joint_error_2, endpoint_error_2),
            ("upper", upper_changed, joint_error_3, endpoint_error_3),
        ):
            if not all(math.isfinite(value) for value in (angle, j_error, e_error)) or max(j_error, e_error) > GEOMETRY_TOLERANCE:
                failures.append(
                    {
                        "fixture": fixture_index,
                        "variant": variant,
                        "angle": angle,
                        "joint_error": j_error,
                        "endpoint_error": e_error,
                        "geometry": [list(vector) for vector in geometry],
                        "upper_roll": upper_roll,
                        "lower_roll": lower_roll,
                    }
                )
        maximum_joint_error = max(maximum_joint_error, joint_error, joint_error_2, joint_error_3)
        maximum_endpoint_error = max(maximum_endpoint_error, endpoint_error, endpoint_error_2, endpoint_error_3)
        maximum_lower_roll_angle_change = max(
            maximum_lower_roll_angle_change,
            abs(wrap(lower_changed - base)),
        )
        maximum_upper_roll_law_error = max(
            maximum_upper_roll_law_error,
            abs(wrap((upper_changed - base) - 0.619)),
        )
        solves += 3

    result = {
        "fixtures": fixtures,
        "solves": solves,
        "maximum_joint_error": maximum_joint_error,
        "maximum_endpoint_error": maximum_endpoint_error,
        "maximum_lower_roll_angle_change": maximum_lower_roll_angle_change,
        "maximum_upper_roll_law_error": maximum_upper_roll_law_error,
        "failures": failures,
    }
    if failures:
        print("RANDOM_POLE_FORMULA_FAILURES_JSON=" + json.dumps(failures, sort_keys=True))
    if maximum_joint_error > GEOMETRY_TOLERANCE or maximum_endpoint_error > GEOMETRY_TOLERANCE:
        raise AssertionError(f"rest-plane formula missed random IK geometry: {result}")
    if maximum_lower_roll_angle_change > ANGLE_TOLERANCE:
        raise AssertionError(f"lower roll changed Pole Angle: {result}")
    if maximum_upper_roll_law_error > ANGLE_TOLERANCE:
        raise AssertionError(f"Pole Angle did not track upper roll 1:1: {result}")
    print("RANDOM_POLE_FORMULA_JSON=" + json.dumps(result, sort_keys=True))
    print(f"PASS randomized Pole Angle formula {solves} solves")


if __name__ == "__main__":
    main()
