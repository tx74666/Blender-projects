"""Actual generated Hand Target routing and independence from old twist weights.

Uses disposable rigs only. Run with Blender --background --factory-startup
--python-exit-code 1 --python tests/test_forearm_twist_controller_blender.py.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)
import test_forearm_twist_blender as fixture_api

runtime = fixture_api.runtime
geometry = fixture_api.geometry
ANGLES = (-90, -45, 45, 90)
SHARES = (0.0, 0.06, 0.21, 0.75, 0.59, 0.84, 0.96, 1.0)


def rotate(point, pivot, axis, angle):
    return pivot + Quaternion(axis, angle) @ (point - pivot)


def transform_about(pivot, axis, angle):
    return Matrix.Translation(pivot) @ Quaternion(axis, angle).to_matrix().to_4x4() @ Matrix.Translation(-pivot)


def set_weight_layout(fixture, reversed_weights):
    mesh = fixture["mesh"]
    for ring_index, indices in enumerate(fixture["rings"]):
        position = fixture["positions"][ring_index]
        weight = position ** 3
        if reversed_weights and 0 < ring_index < len(fixture["rings"]) - 1:
            weight = 1.0 - position
        mesh.vertex_groups[fixture["lower_name"]].add(indices, 1.0 - weight, "REPLACE")
        mesh.vertex_groups[fixture["hand_name"]].add(indices, weight, "REPLACE")
    mesh.data.update()
    bpy.context.view_layer.update()


def apply_controller(fixture, euler):
    # The same public animator channels the artist manipulates. No calibration
    # or update_runtime calls are made; the registered depsgraph handler owns
    # the deformation update after this controller edit.
    fixture["target"].rotation_euler = euler
    fixture["armature"].update_tag(refresh={"OBJECT"})
    bpy.context.view_layer.update()
    return fixture_api.evaluated_points(fixture["mesh"])


def assert_no_runtime_error(fixture):
    assert fixture["mesh"].name not in runtime._ERRORS, runtime._ERRORS
    key = fixture["mesh"].data.shape_keys.key_blocks[fixture_api.record_for(fixture["mesh"])["key"]]
    assert not key.mute and key.value == 1.0


def test_controller_replaces_old_twist_weights():
    for method in fixture_api.BUILD_METHODS:
        fixture = fixture_api.make_fixture(method)
        mesh, armature, target = fixture["mesh"], fixture["armature"], fixture["target"]
        assert target.name == "CTRL_hand_IK.L", target.name
        before_bones = len(armature.data.bones)
        before_modifiers = tuple((modifier.name, modifier.type) for modifier in mesh.modifiers)
        saved_channels = {}
        runtime.start_test(bpy.context, mesh)
        for ring_index in range(1, len(SHARES) - 1):
            runtime.set_ratio(bpy.context, ring_index, SHARES[ring_index])
        # Fit pure-axis poses once through the real Target, then replay only
        # its channels after Confirm. A noncollinear hand rest frame can require
        # X/Z compensation for a mathematically pure forearm-axis twist.
        for degrees in ANGLES:
            target.rotation_euler = runtime._SESSION["rotation"]
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
            runtime._test_pose(bpy.context, math.radians(degrees))
            saved_channels[degrees] = target.rotation_euler.copy()
        runtime.finish_test(bpy.context, True)
        source = fixture_api.uncorrected_points(mesh)
        axis, pivot = fixture["axis"], fixture["pivot"]
        surfaces = {}
        maximum_radial_error = 0.0
        maximum_angle_error = 0.0
        for reverse in (False, True):
            set_weight_layout(fixture, reverse)
            for degrees in ANGLES:
                actual = apply_controller(fixture, saved_channels[degrees])
                assert_no_runtime_error(fixture)
                matrices = fixture_api.deformation_matrices(armature)
                lower, hand = matrices[fixture["lower_name"]], matrices[fixture["hand_name"]]
                twist = geometry.twist_angle(lower, hand, axis)
                assert abs(twist - math.radians(degrees)) < 5.0e-5
                for ring_index, indices in enumerate(fixture["rings"]):
                    for index in indices:
                        expected = lower @ rotate(source[index], pivot, axis, SHARES[ring_index] * twist)
                        fixture_api.assert_points_close([actual[index]], [expected],
                            f"{method} controller {degrees}, reversed weights={reverse}, loop={ring_index}")
                        before = source[index] - pivot
                        before -= axis * before.dot(axis)
                        after = lower.inverted() @ actual[index] - pivot
                        after -= axis * after.dot(axis)
                        radial_error = abs(before.length - after.length)
                        angle = math.atan2(axis.dot(before.cross(after)), before.dot(after))
                        angle_error = abs(math.remainder(angle - SHARES[ring_index] * twist, math.tau))
                        maximum_radial_error = max(maximum_radial_error, radial_error)
                        maximum_angle_error = max(maximum_angle_error, angle_error)
                        assert radial_error < 3.0e-5
                        assert angle_error < 8.0e-4
                # Wrist and palm hand-only vertices keep exactly the hand's
                # complete deformation, irrespective of the forearm profile.
                for index in fixture["rings"][-1] + fixture["guard_rings"][-1]:
                    fixture_api.assert_points_close([actual[index]], [hand @ source[index]], "Palm fully follows actual Hand")
                if reverse:
                    fixture_api.assert_points_close(actual, surfaces[degrees], f"{method} pure twist ignores old weights {degrees}")
                else:
                    surfaces[degrees] = actual
        # At loop 3 the hand used to have only ~7.9% weight. The calibrated
        # result at +90 degrees is 67.5 degrees (75%), not the old LBS angle.
        default_weight = fixture["positions"][3] ** 3
        old_angle = math.degrees(math.atan2(default_weight, 1.0 - default_weight))
        assert abs(old_angle - 67.5) > 50.0
        assert len(armature.data.bones) == before_bones
        assert tuple((modifier.name, modifier.type) for modifier in mesh.modifiers) == before_modifiers
        runtime.remove_calibration(bpy.context, mesh, "L")
        print(f"PASS {method} CTRL_hand_IK.L +/-45/90 old-weight replacement; "
              f"radial error={maximum_radial_error:.3g}, angle error={math.degrees(maximum_angle_error):.5g}deg; "
              f"loop3 old={old_angle:.3f}deg, calibrated=67.5deg")


def test_target_y_with_wrist_bend_preserves_swing_and_palm():
    for method in fixture_api.BUILD_METHODS:
        fixture = fixture_api.make_fixture(method)
        mesh, armature = fixture["mesh"], fixture["armature"]
        axis, pivot = fixture["axis"], fixture["pivot"]
        runtime.start_test(bpy.context, mesh)
        for ring_index in range(1, len(SHARES) - 1):
            runtime.set_ratio(bpy.context, ring_index, SHARES[ring_index])
        runtime.finish_test(bpy.context, True)
        source = fixture_api.uncorrected_points(mesh)
        for reverse in (False, True):
            set_weight_layout(fixture, reverse)
            for bend in (0.0, math.radians(25.0)):
                for degrees in ANGLES:
                    # Exercise exactly the visible Twist(Y) channel, including
                    # the small swing implied by noncollinear hand rest frames.
                    actual = apply_controller(fixture, (bend, math.radians(degrees), -0.12 if bend else 0.0))
                    assert_no_runtime_error(fixture)
                    matrices = fixture_api.deformation_matrices(armature)
                    lower, hand = matrices[fixture["lower_name"]], matrices[fixture["hand_name"]]
                    angle = geometry.twist_angle(lower, hand, axis)
                    countertwist = transform_about(pivot, axis, -angle)
                    for ring_index, indices in enumerate(fixture["rings"]):
                        for index in indices:
                            weights = fixture_api.normalized_weights(mesh, armature, index)
                            lower_weight = weights.get(fixture["lower_name"], 0.0)
                            hand_weight = weights.get(fixture["hand_name"], 0.0)
                            # Factor out the original swing-only skinning. The
                            # remaining point must follow exactly the saved arc.
                            swing_blend = lower * lower_weight + (hand @ countertwist) * hand_weight
                            recovered = swing_blend.inverted() @ actual[index]
                            expected = rotate(source[index], pivot, axis, SHARES[ring_index] * angle)
                            fixture_api.assert_points_close([recovered], [expected],
                                f"{method} literal Y {degrees}, bend={bend}, reverse={reverse}")
                    for index in fixture["rings"][-1] + fixture["guard_rings"][-1]:
                        fixture_api.assert_points_close([actual[index]], [hand @ source[index]], "Bent palm keeps complete hand deformation")
        runtime.remove_calibration(bpy.context, mesh, "L")
        print(f"PASS {method} literal Twist(Y) +/-45/90 with 25deg wrist bend: saved twist replaces old weights, swing preserved")


def test_preview_large_jumps_preserve_original_swing():
    cases = (("DIRECT_PREROLL", False, "XYZ", False),
             ("DIRECT_PREROLL", False, "XYZ", True),
             ("ROLL_DECOUPLED", False, "XYZ", False),
             ("DIRECT_PREROLL", True, "XYZ", False),
             ("ROLL_DECOUPLED", True, "XYZ", False),
             (None, False, "QUATERNION", False),
             (None, False, "AXIS_ANGLE", False),
             (None, False, "ZYX", False))
    for method, auto_align, rotation_mode, initial_gimbal in cases:
        fixture = fixture_api.make_fixture(method or "DIRECT_PREROLL", build_ik=method is not None)
        mesh, armature, target = fixture["mesh"], fixture["armature"], fixture["target"]
        if auto_align:
            bpy.context.view_layer.objects.active = armature
            armature.select_set(True)
            bpy.ops.object.mode_set(mode="POSE")
            assert bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE") == {"FINISHED"}
            fixture_api.activate_mesh(mesh)
        target.rotation_euler = (0.0, math.pi / 2, 0.0) if initial_gimbal else (0.32, 0.21, -0.16)
        target.rotation_quaternion = Quaternion(Vector((0.6, 0.7, -0.2)).normalized(), 0.43)
        target.rotation_axis_angle = (0.31, 1.0, 0.0, 0.0)
        target.rotation_mode = rotation_mode
        armature.update_tag(refresh={"OBJECT"})
        bpy.context.view_layer.update()
        before_pose = fixture_api.pose_snapshot(armature)
        before_structure = fixture_api.structure_snapshot(armature, mesh)
        matrices = fixture_api.deformation_matrices(armature)
        lower = matrices[fixture["lower_name"]]
        hand = matrices[fixture["hand_name"]]
        original_twist = geometry.twist_angle(lower, hand, fixture["axis"])
        original_swing = (lower.to_quaternion().conjugated() @ hand.to_quaternion()
                          @ Quaternion(fixture["axis"], -original_twist)).normalized()
        label = f"{method or 'FK'}/{rotation_mode}/auto={auto_align}/gimbal={initial_gimbal}"
        runtime.start_test(bpy.context, mesh)
        for degrees in (90, -90, 90, -120, 120, -90, 0, 90):
            # This is deliberately a direct large jump from the current preview,
            # without resetting channels or creating another test session.
            bpy.context.window_manager.character_designer_forearm_twist.test_angle = math.radians(degrees)
            assert runtime._SESSION is not None, f"{label}: preview cancelled at {degrees}"
            assert_no_runtime_error(fixture)
            current = fixture_api.deformation_matrices(armature)
            current_lower = current[fixture["lower_name"]]
            current_hand = current[fixture["hand_name"]]
            twist = geometry.twist_angle(current_lower, current_hand, fixture["axis"])
            assert abs(twist - math.radians(degrees)) < 8.0e-5, f"{label}: wrong twist at {degrees}"
            swing = (current_lower.to_quaternion().conjugated() @ current_hand.to_quaternion()
                     @ Quaternion(fixture["axis"], -twist)).normalized()
            difference = swing.rotation_difference(original_swing)
            error = 2.0 * math.atan2(Vector((difference.x, difference.y, difference.z)).length, abs(difference.w))
            assert error < 8.0e-5, f"{label}: original wrist swing changed {error} at {degrees}"
            assert max(abs(current_lower[row][column] - lower[row][column])
                       for row in range(4) for column in range(4)) < 5.0e-6, f"{label}: lower/IK pose changed"
            fixture_api.assert_runtime_geometry(fixture, f"{label} large jump {degrees}")
        runtime.finish_test(bpy.context, True)
        fixture_api.assert_pose_snapshot(armature, before_pose, f"{label} final pose")
        assert fixture_api.structure_snapshot(armature, mesh) == before_structure
        runtime.remove_calibration(bpy.context, mesh, "L")
        print(f"PASS preview +/-90 and +/-120 jumps preserve original swing and restore pose: {label}")


if __name__ == "__main__":
    test_controller_replaces_old_twist_weights()
    test_target_y_with_wrist_bend_preserves_swing_and_palm()
    test_preview_large_jumps_preserve_original_swing()
    print("Forearm twist generated-controller routing: all checks passed")
