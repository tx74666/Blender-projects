"""Read-only Rotation Tilt upgrade verifier for the real c24d Strap rig.

Run with Blender 5.2, factory startup, disabled autoexec, and ``X.blend``
before ``--python``.  The script mutates only Blender's in-memory copy and
never invokes a save operator.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

import character_designer
from character_designer import spline_ik_setup


RIG_ID = "c24dabe44ebc4de29cb0d4998541815d"
CHAIN = (
    "DEF_Strap_01.L",
    "DEF_Strap_02.L",
    "DEF_Strap_03.L",
    "DEF_Strap_04.L",
    "DEF_Strap_05.L",
    "DEF_Strap_06.L",
    "DEF_Strap_C",
    "DEF_Strap_06.R",
    "DEF_Strap_05.R",
    "DEF_Strap_04.R",
    "DEF_Strap_03.R",
    "DEF_Strap_02.R",
    "DEF_Strap_01.R",
)
TOLERANCE = 1.0e-5


def file_signature(path):
    stat = path.stat()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return digest, stat.st_size, stat.st_mtime_ns


def assert_matrix_close(actual, expected, tolerance=TOLERANCE):
    error = max(
        abs(left - right)
        for actual_row, expected_row in zip(actual, expected)
        for left, right in zip(actual_row, expected_row)
    )
    if error > tolerance:
        raise AssertionError(f"Matrix changed by {error}; tolerance is {tolerance}")


def assert_vector_close(actual, expected, tolerance=TOLERANCE):
    error = (Vector(actual) - Vector(expected)).length
    if error > tolerance:
        raise AssertionError(f"Vector changed by {error}; tolerance is {tolerance}")


def evaluated_curve_state(curve):
    evaluated = curve.evaluated_get(bpy.context.evaluated_depsgraph_get())
    spline = evaluated.data.splines[0]
    return tuple(
        (
            point.co.copy(),
            point.handle_left.copy(),
            point.handle_right.copy(),
            float(point.tilt),
        )
        for point in spline.bezier_points
    )


def evaluated_curve_vertices(curve):
    evaluated = curve.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return tuple(vertex.co.copy() for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def evaluated_pose_matrices(armature):
    evaluated = armature.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return tuple(evaluated.pose.bones[name].matrix.copy() for name in CHAIN)


def signed_pose_roll_delta(before, after):
    before = before.to_3x3()
    after = after.to_3x3()
    old_x = Vector(before.col[0]).normalized()
    new_x = Vector(after.col[0]).normalized()
    roll_axis = Vector(before.col[1]).normalized() + Vector(after.col[1]).normalized()
    if roll_axis.length <= 1.0e-8:
        roll_axis = Vector(before.col[1]).normalized()
    else:
        roll_axis.normalize()
    return math.atan2(roll_axis.dot(old_x.cross(new_x)), old_x.dot(new_x))


def constraint_value(value):
    if isinstance(value, bpy.types.ID):
        return value.name, value.as_pointer()
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        try:
            return tuple(value)
        except TypeError:
            pass
    if isinstance(value, float):
        return round(value, 9)
    return value


def user_constraint_signature(owner, constraint):
    properties = {}
    for name in spline_ik_setup._SPLINE_IK_SNAPSHOT_PROPERTIES:
        if hasattr(constraint, name):
            properties[name] = constraint_value(getattr(constraint, name))
    return (
        owner.as_pointer(),
        constraint.as_pointer(),
        constraint.name,
        constraint.type,
        tuple(owner.constraints).index(constraint),
        tuple(sorted(properties.items())),
    )


def main():
    source_path = Path(bpy.data.filepath).resolve()
    expected_path = (PROJECT_ROOT / "X.blend").resolve()
    if source_path != expected_path:
        raise AssertionError(f"Expected {expected_path}, opened {source_path}")
    disk_before = file_signature(source_path)

    armature = bpy.data.objects.get("Strap.001")
    if armature is None or armature.type != "ARMATURE":
        raise AssertionError("Strap.001 Armature was not found")
    if tuple(name for name in CHAIN if armature.data.bones.get(name) is None):
        raise AssertionError("The audited 13-bone Strap chain changed")

    owned_objects = [
        obj
        for obj in bpy.data.objects
        if obj.get(spline_ik_setup.RIG_ID_KEY) == RIG_ID
        and obj.get(spline_ik_setup.OWNER_KEY) == spline_ik_setup.OWNER_VALUE
    ]
    curves = [
        obj
        for obj in owned_objects
        if obj.get(spline_ik_setup.ROLE_KEY) == "CURVE"
    ]
    controls = sorted(
        (
            obj
            for obj in owned_objects
            if obj.get(spline_ik_setup.ROLE_KEY) == "CONTROL"
        ),
        key=lambda obj: obj[spline_ik_setup.CONTROL_INDEX_KEY],
    )
    if len(curves) != 1 or len(controls) != 3:
        raise AssertionError("Expected one c24d Curve and three c24d controls")
    curve = curves[0]
    if [control.empty_display_type for control in controls] != ["CUBE", "SPHERE", "CUBE"]:
        raise AssertionError("The real endpoint/interior control shapes changed")

    user_owner = armature.pose.bones["DEF_Strap_02.R"]
    user_constraint = user_owner.constraints.get("Spline IK")
    old_line = bpy.data.objects.get("Line")
    if (
        user_constraint is None
        or user_constraint.type != "SPLINE_IK"
        or old_line is None
        or user_constraint.target is not old_line
    ):
        raise AssertionError("The audited user Spline IK -> Line constraint changed")

    character_designer.register()
    try:
        settings = bpy.context.window_manager.character_designer_spline_ik
        settings.armature = armature
        settings.chain_names_json = json.dumps(list(CHAIN), separators=(",", ":"))
        settings.chain_count = len(CHAIN)
        settings.active_rig_id = RIG_ID

        inventory = spline_ik_setup._rig_inventory(
            bpy.context,
            armature,
            CHAIN,
            RIG_ID,
        )
        if inventory["rotation_tilt_state"] != "MISSING":
            raise AssertionError(
                f"Expected legacy c24d rig, got {inventory['rotation_tilt_state']}: "
                f"{inventory['rotation_tilt_detail']}"
            )
        if inventory["hook_name_state"] != spline_ik_setup.HOOK_NAME_LEGACY:
            raise AssertionError("The real c24d Hook names are no longer the legacy UUID form")
        legacy_hook_names = tuple(
            f"CDSplineIK_Hook_{RIG_ID}_{index + 1:02d}" for index in range(3)
        )
        hook_modifiers = tuple(curve.modifiers)
        if tuple(modifier.name for modifier in hook_modifiers) != legacy_hook_names:
            raise AssertionError("The real c24d legacy Hook names changed unexpectedly")
        hook_pointers = tuple(modifier.as_pointer() for modifier in hook_modifiers)
        hook_targets = tuple(modifier.object.as_pointer() for modifier in hook_modifiers)
        hook_indices = tuple(tuple(modifier.vertex_indices) for modifier in hook_modifiers)
        hook_strengths = tuple(float(modifier.strength) for modifier in hook_modifiers)
        hook_registry_before = json.loads(curve[spline_ik_setup.HOOK_REGISTRY_KEY])

        object_count = len(bpy.data.objects)
        curve_count = len(bpy.data.curves)
        identities = (curve.as_pointer(), *(control.as_pointer() for control in controls))
        control_world = tuple(control.matrix_world.copy() for control in controls)
        frame_plan = spline_ik_setup._evaluated_control_frame_plan(
            bpy.context,
            curve,
            controls,
        )
        curve_state = evaluated_curve_state(curve)
        curve_vertices = evaluated_curve_vertices(curve)
        bone_pose = evaluated_pose_matrices(armature)
        user_state = user_constraint_signature(user_owner, user_constraint)

        if bpy.ops.character_designer.spline_ik_enable_rotation_tilt() != {"FINISHED"}:
            raise AssertionError(settings.last_message)
        inventory = spline_ik_setup._rig_inventory(
            bpy.context,
            armature,
            CHAIN,
            RIG_ID,
        )
        if inventory["rotation_tilt_state"] != "ENABLED":
            raise AssertionError(inventory["rotation_tilt_detail"])
        if inventory["control_frame_state"] != "ENABLED":
            raise AssertionError(inventory["control_frame_detail"])
        if inventory["hook_name_state"] != spline_ik_setup.HOOK_NAME_CURRENT:
            raise AssertionError("The real c24d Hook names were not cleaned in place")
        readable_hook_names = tuple(
            f"CD Spline IK Hook {index + 1:02d}" for index in range(3)
        )
        if tuple(modifier.name for modifier in curve.modifiers) != readable_hook_names:
            raise AssertionError("The real c24d Hook names are not the exact readable form")
        if tuple(modifier.as_pointer() for modifier in curve.modifiers) != hook_pointers:
            raise AssertionError("Hook-name cleanup replaced a real modifier")
        if tuple(modifier.object.as_pointer() for modifier in curve.modifiers) != hook_targets:
            raise AssertionError("Hook-name cleanup retargeted a real modifier")
        if tuple(tuple(modifier.vertex_indices) for modifier in curve.modifiers) != hook_indices:
            raise AssertionError("Hook-name cleanup changed real Hook indices")
        # Enabling the new control axes deliberately compensates each Hook
        # inverse so the Curve does not move; name cleanup itself keeps the
        # same Modifier pointer, target, indices, and strength.
        if tuple(float(modifier.strength) for modifier in curve.modifiers) != hook_strengths:
            raise AssertionError("Hook-name cleanup changed real Hook strength")
        hook_registry_after = json.loads(curve[spline_ik_setup.HOOK_REGISTRY_KEY])
        for index, (before_record, after_record) in enumerate(
            zip(hook_registry_before, hook_registry_after)
        ):
            if after_record.get("name") != readable_hook_names[index]:
                raise AssertionError("The real Hook registry did not receive the readable name")
            if after_record.get("rig_id") != RIG_ID:
                raise AssertionError("Hook-name cleanup changed the internal real rig UUID")
            if {
                key: value for key, value in before_record.items() if key != "name"
            } != {
                key: value for key, value in after_record.items() if key != "name"
            }:
                raise AssertionError("Hook-name cleanup changed real ownership metadata")
        if len(bpy.data.objects) != object_count or len(bpy.data.curves) != curve_count:
            raise AssertionError("The in-place upgrade created or deleted objects/Curves")
        if identities != (
            inventory["curve_object"].as_pointer(),
            *(control.as_pointer() for control in inventory["controls"]),
        ):
            raise AssertionError("The in-place upgrade replaced real rig objects")
        for actual, old_world, expected_frame in zip(
            inventory["controls"],
            control_world,
            frame_plan["frames"],
        ):
            assert_vector_close(
                actual.matrix_world.translation,
                old_world.translation,
                tolerance=2.0e-5,
            )
            for axis_index in range(3):
                actual_axis = Vector(actual.matrix_world.col[axis_index].xyz).normalized()
                expected_axis = Vector(expected_frame.col[axis_index].xyz).normalized()
                if actual_axis.dot(expected_axis) < 1.0 - 1.0e-5:
                    raise AssertionError(
                        f"Real control axis {axis_index} did not align to the strap frame"
                    )
            if actual.rotation_mode != "YXZ" or not actual.show_axis:
                raise AssertionError("Real controls do not expose the Y-first local-axis contract")

        upgraded_curve_state = evaluated_curve_state(curve)
        final_frame_plan = spline_ik_setup._evaluated_control_frame_plan(
            bpy.context,
            curve,
            controls,
        )
        if len(upgraded_curve_state) != len(curve_state):
            raise AssertionError("Upgrade changed the real Bezier point count")
        for point_index, (actual, expected) in enumerate(
            zip(upgraded_curve_state, curve_state)
        ):
            for actual_vector, expected_vector in zip(actual[:3], expected[:3]):
                assert_vector_close(actual_vector, expected_vector, tolerance=2.0e-5)
            if abs(actual[3] - final_frame_plan["tilts"][point_index]) > 1.0e-5:
                raise AssertionError(
                    "Upgrade did not align Curve Tilt to the strap-front frame: "
                    f"point {point_index}, actual={actual[3]}, "
                    f"planned={final_frame_plan['tilts'][point_index]}"
                )
            if (
                final_frame_plan["curve_normals"][point_index].dot(
                    final_frame_plan["front_normals"][point_index]
                )
                < 1.0 - 1.0e-5
            ):
                raise AssertionError(
                    "The real evaluated Curve profile normal does not face the strap front"
                )
        upgraded_vertices = evaluated_curve_vertices(curve)
        if len(upgraded_vertices) != len(curve_vertices):
            raise AssertionError("Upgrade changed real Curve evaluation topology")
        for actual, expected in zip(upgraded_vertices, curve_vertices):
            assert_vector_close(actual, expected, tolerance=2.0e-5)
        for actual, expected in zip(evaluated_pose_matrices(armature), bone_pose):
            assert_matrix_close(actual, expected, tolerance=1.0e-4)
        if user_constraint_signature(user_owner, user_constraint) != user_state:
            raise AssertionError("Upgrade edited or replaced the user's Spline IK constraint")

        # X/Z steer the Curve but are completely isolated from Tilt.
        middle = controls[1]
        tilt_before_swing = evaluated_curve_state(curve)
        vertices_before_swing = evaluated_curve_vertices(curve)
        middle.rotation_euler.x = math.radians(24.0)
        middle.rotation_euler.z = math.radians(-29.0)
        bpy.context.view_layer.update()
        tilt_after_swing = evaluated_curve_state(curve)
        for before, after in zip(tilt_before_swing, tilt_after_swing):
            if abs(after[3] - before[3]) > 1.0e-5:
                raise AssertionError("Real local X/Z steering leaked into Curve Tilt")
        vertices_after_swing = evaluated_curve_vertices(curve)
        if max(
            (after - before).length
            for before, after in zip(vertices_before_swing, vertices_after_swing)
        ) < 1.0e-5:
            raise AssertionError("Real local X/Z steering did not bend the Curve")
        middle.rotation_euler.x = 0.0
        middle.rotation_euler.z = 0.0
        bpy.context.view_layer.update()

        # The middle Sphere is the most direct real-world acceptance gesture.
        tilt_before = evaluated_curve_state(curve)
        pose_before = evaluated_pose_matrices(armature)
        curve_before_twist = evaluated_curve_vertices(curve)
        angle = math.radians(20.0)
        middle.rotation_euler.y += angle
        bpy.context.view_layer.update()
        tilt_after = evaluated_curve_state(curve)
        for index, (before, after) in enumerate(zip(tilt_before, tilt_after)):
            expected = before[3] + (angle if index == 1 else 0.0)
            if abs(after[3] - expected) > 1.0e-5:
                raise AssertionError(
                    f"Real point {index} Tilt is {after[3]}, expected {expected}"
                )
        pose_after = evaluated_pose_matrices(armature)
        rolls = tuple(
            signed_pose_roll_delta(before, after)
            for before, after in zip(pose_before, pose_after)
        )
        if max(abs(value) for value in rolls) < math.radians(8.0):
            raise AssertionError("The real 13-bone chain did not visibly Roll")
        if max(
            (before.translation - after.translation).length
            for before, after in zip(pose_before, pose_after)
        ) > 1.0e-4:
            raise AssertionError("Real Rotation Tilt moved bone positions")
        for actual, expected in zip(evaluated_curve_vertices(curve), curve_before_twist):
            assert_vector_close(actual, expected, tolerance=2.0e-5)
        if user_constraint_signature(user_owner, user_constraint) != user_state:
            raise AssertionError("Posing the Sphere edited the user's Spline IK constraint")

        if file_signature(source_path) != disk_before:
            raise AssertionError("The verifier changed X.blend on disk")
        print(
            "PASS real c24d Rotation Tilt:",
            "13 bones, 3 strap frames, X/Z isolated, Y twist 1:1, no save",
        )
    finally:
        if hasattr(bpy.types.WindowManager, "character_designer"):
            character_designer.unregister()


if __name__ == "__main__":
    main()
