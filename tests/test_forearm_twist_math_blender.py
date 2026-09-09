"""Disposable geometry and actual Armature evaluation checks for twist math.

Run: blender --background --factory-startup --python-exit-code 1
             --python tests/test_forearm_twist_math_blender.py
Never opens or saves the production X.blend.
"""

import importlib.util
import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "forearm_twist_math", os.path.join(ROOT, "addons", "character_designer", "forearm_twist_math.py"))
twist = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(twist)


def close(actual, expected, label, tolerance=4.0e-5):
    error = (Vector(actual) - Vector(expected)).length
    assert error < tolerance, f"{label}: {error}, actual={tuple(actual)}, expected={tuple(expected)}"


def rotation(axis, angle, pivot=(0, 0, 0)):
    pivot = Vector(pivot)
    return Matrix.Translation(pivot) @ Quaternion(axis, angle).to_matrix().to_4x4() @ Matrix.Translation(-pivot)


def expect_error(function, label):
    try:
        function()
    except twist.TwistMathError:
        return
    raise AssertionError(f"Expected explicit rejection: {label}")


def test_circular_arc_and_inverse():
    axis = Vector((0.3, 0.7, -0.2)).normalized()
    pivot = Vector((0.8, 1.9, -0.3))
    lower = Matrix.Translation((0.6, -0.2, 1.1)) @ rotation((0.8, -0.1, 0.2), 0.73)
    for degrees in (-120, -90, -30, 0, 30, 90, 120):
        angle = math.radians(degrees)
        transforms = {"lower": lower, "hand": lower @ rotation(axis, angle, pivot)}
        assert abs(twist.twist_angle(lower, transforms["hand"], axis) - angle) < 2.0e-6
        for hand_weight in (0.0, 0.1, 0.5, 0.8, 1.0):
            weights = {"lower": 1.0 - hand_weight, "hand": hand_weight}
            for ratio in (0.0, 0.25, 0.6, 1.0):
                for point in ((0.4, 1.1, 0.7), (-0.2, 1.7, 0.1)):
                    point = Vector(point)
                    corrected = twist.corrected_vertex(point, transforms, weights, "lower", "hand", axis, pivot, ratio)
                    evaluated = twist.blended_matrix(transforms, weights) @ corrected
                    expected = lower @ twist.rotate_about_axis(point, axis, pivot, ratio * angle)
                    close(evaluated, expected, f"arc {degrees}/{hand_weight}/{ratio}")
                    radial_before = point - pivot - axis * (point - pivot).dot(axis)
                    local_after = lower.inverted() @ evaluated - pivot
                    radial_after = local_after - axis * local_after.dot(axis)
                    assert abs(radial_before.length - radial_after.length) < 4.0e-5


def test_swing_rest_frames_and_other_weights():
    rest_lower = Matrix.Translation((0.3, -0.1, 0.7)) @ rotation((1, 0, 0), 0.4)
    rest_hand = Matrix.Translation((0.1, 2.2, 0.5)) @ rotation((0, 0, 1), -0.63) @ rotation((0, 1, 0), 0.32)
    axis = (rest_lower.to_3x3() @ Vector((0, 1, 0))).normalized()
    pivot = rest_hand.translation.copy()
    bend_axis = axis.cross(Vector((0, 0, 1))).normalized()
    lower_deform = Matrix.Translation((0.2, 0.6, -0.4)) @ rotation((0.7, 0.2, 0.1), 0.83)
    point = Vector((0.2, 1.7, 0.9))
    for degrees in (-100, 0, 100):
        angle = math.radians(degrees)
        relative = rotation(bend_axis, 0.55, pivot) @ rotation(axis, angle, pivot)
        pose_lower = lower_deform @ rest_lower
        pose_hand = lower_deform @ relative @ rest_hand
        transforms = {"lower": pose_lower @ rest_lower.inverted(),
                      "hand": pose_hand @ rest_hand.inverted(),
                      "upper": rotation((0, 0, 1), 0.24)}
        extracted = twist.twist_angle(transforms["lower"], transforms["hand"], axis)
        assert abs(extracted - angle) < 2.0e-6, "Rest orientation leaked into twist"
        hand_only = {"hand": 1.0}
        close(twist.corrected_vertex(point, transforms, hand_only, "lower", "hand", axis, pivot, 1.0), point,
              "Full hand endpoint must retain swing and original rotation")
        outside = {"upper": 1.0}
        close(twist.corrected_vertex(point, transforms, outside, "lower", "hand", axis, pivot, 0.5), point,
              "Other influences unchanged")
        weights = {"lower": 0.35, "hand": 0.45, "upper": 0.2}
        corrected = twist.corrected_vertex(point, transforms, weights, "lower", "hand", axis, pivot, 0.4)
        expected = (0.35 * (transforms["lower"] @ twist.rotate_about_axis(point, axis, pivot, 0.4 * angle))
                    + 0.45 * (transforms["hand"] @ twist.rotate_about_axis(point, axis, pivot, -0.6 * angle))
                    + 0.2 * (transforms["upper"] @ point))
        close(twist.blended_matrix(transforms, weights) @ corrected, expected, "Swing plus unrelated influence")
        if degrees == 0:
            close(corrected, point, "Bend alone must receive no corrective delta")


def test_guards_and_profile():
    transforms = {"lower": Matrix.Identity(4), "hand": rotation((0, 1, 0), math.pi)}
    expect_error(lambda: twist.corrected_vertex((1, 0, 0), transforms, {"lower": 0.5, "hand": 0.5},
                                               "lower", "hand", (0, 1, 0), (0, 0, 0), 0.5), "180-degree singular LBS")
    expect_error(lambda: twist.twist_angle(Matrix.Identity(4), Matrix.Diagonal((1, 2, 1, 1)), (0, 1, 0)), "Nonuniform scale")
    expect_error(lambda: twist.twist_angle(Matrix.Identity(4), rotation((1, 0, 0), math.pi), (0, 1, 0)), "Ambiguous swing")
    expect_error(lambda: twist.blended_matrix(transforms, {"lower": -0.2, "hand": 1.2}), "Negative weights")
    expect_error(lambda: twist.blended_matrix(transforms, {"lower": 0.4}), "Unnormalized weights")
    expect_error(lambda: twist.profile_ratio(0.5, [(0, 0), (0, 1)]), "Duplicate knot positions")
    knots = [(0.0, 0.0), (0.4, 0.2), (1.0, 1.0)]
    assert twist.profile_ratio(-1, knots) == 0
    assert twist.profile_ratio(2, knots) == 1
    assert abs(twist.profile_ratio(0.4, knots) - 0.2) < 1.0e-8
    assert abs(twist.profile_ratio(0.7, knots) - 0.6) < 1.0e-8


def test_actual_blender_armature():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig_data = bpy.data.armatures.new("TwistMathTestRig")
    rig = bpy.data.objects.new("TwistMathTestRig", rig_data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    lower = rig_data.edit_bones.new("lower")
    lower.head, lower.tail = (0, 0, 0), (0, 2, 0)
    hand = rig_data.edit_bones.new("hand")
    hand.head, hand.tail, hand.parent = (0, 2, 0), (0, 3, 0), lower
    hand.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    points = [(0.25 * math.cos(index * math.tau / 8), 1.6,
               0.25 * math.sin(index * math.tau / 8)) for index in range(8)]
    mesh_data = bpy.data.meshes.new("TwistMathTestMesh")
    mesh_data.from_pydata(points, [], [])
    mesh = bpy.data.objects.new("TwistMathTestMesh", mesh_data)
    bpy.context.collection.objects.link(mesh)
    for name in ("lower", "hand"):
        mesh.vertex_groups.new(name=name).add(list(range(8)), 0.5, "REPLACE")
    mesh.shape_key_add(name="Basis")
    correction = mesh.shape_key_add(name="TwistTestCorrection")
    correction.value = 1.0
    modifier = mesh.modifiers.new("Existing Armature", "ARMATURE")
    modifier.object = rig
    modifier.use_deform_preserve_volume = False
    counts = (len(rig_data.bones), len(mesh.modifiers))
    for degrees in (-120, -90, 0, 90, 120):
        for bend in (0.0, 0.47):
            rig.pose.bones["lower"].rotation_mode = "XYZ"
            rig.pose.bones["lower"].rotation_euler = (0.6, 0, 0.1)
            rig.pose.bones["hand"].rotation_mode = "QUATERNION"
            rig.pose.bones["hand"].rotation_quaternion = Quaternion((1, 0, 0), bend) @ Quaternion((0, 1, 0), math.radians(degrees))
            bpy.context.view_layer.update()
            transforms = {name: rig.pose.bones[name].matrix @ rig_data.bones[name].matrix_local.inverted()
                          for name in ("lower", "hand")}
            expected = []
            for index, point in enumerate(points):
                arguments = (point, transforms, {"lower": 0.5, "hand": 0.5}, "lower", "hand", (0, 1, 0), (0, 2, 0), 0.65)
                correction.data[index].co = twist.corrected_vertex(*arguments)
                expected.append(twist.desired_vertex(*arguments))
            mesh.data.update()
            bpy.context.view_layer.update()
            evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
            result = evaluated.to_mesh()
            try:
                for index, vertex in enumerate(result.vertices):
                    close(vertex.co, expected[index], f"Actual Armature {degrees}/{bend}/{index}", tolerance=7.0e-5)
            finally:
                evaluated.to_mesh_clear()
    assert (len(rig_data.bones), len(mesh.modifiers)) == counts


if __name__ == "__main__":
    for test in (test_circular_arc_and_inverse, test_swing_rest_frames_and_other_weights,
                 test_guards_and_profile, test_actual_blender_armature):
        test()
        print(f"PASS {test.__name__}")
    print("Forearm twist math: all checks passed")
