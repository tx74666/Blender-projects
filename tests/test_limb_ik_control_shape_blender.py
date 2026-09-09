"""Blender 5.2 regressions for Limb IK control shapes and Pole colors.

The fixture is created from ``--factory-startup`` data.  This test never opens
or saves the production ``X.blend`` file.

Run from the repository root with Blender 5.2::

    blender --background --factory-startup --python-exit-code 1 \
        --python tests/test_limb_ik_control_shape_blender.py
"""

from __future__ import annotations

import os
import sys

import bpy
from mathutils import Vector


TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import test_limb_ik_auto_visual_blender as visual
import test_limb_ik_blender as base


limb_ik = base.limb_ik
STYLE_KEY = "character_designer_limb_ik_control_shape_style"
MATRIX_TOLERANCE = 1.0e-7
VECTOR_TOLERANCE = 1.0e-7
COLOR_TOLERANCE = 2.0e-6


def _assert_matrix_elements_close(actual, expected, label, tolerance=MATRIX_TOLERANCE):
    residual = max(
        abs(float(actual[row][column] - expected[row][column]))
        for row in range(4)
        for column in range(4)
    )
    if residual > tolerance:
        raise AssertionError(f"{label}: matrix residual={residual:.9g}")


def _assert_vector_close(actual, expected, label, tolerance=VECTOR_TOLERANCE):
    residual = (Vector(actual) - Vector(expected)).length
    if residual > tolerance:
        raise AssertionError(f"{label}: vector residual={residual:.9g}")


def _source_rest_signature(armature):
    return {
        bone.name: bone.matrix_local.copy()
        for bone in armature.data.bones
        if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    }


def _assert_rest_signature(actual, expected, label):
    if set(actual) != set(expected):
        raise AssertionError(
            f"{label}: source bone names changed: {sorted(actual)} != {sorted(expected)}"
        )
    for name, matrix in expected.items():
        _assert_matrix_elements_close(actual[name], matrix, f"{label} source Rest '{name}'")


def _make_source_mesh():
    mesh = bpy.data.meshes.new("ControlShapeSourceMeshData")
    mesh.from_pydata(
        (
            (-0.4, -0.2, 0.0),
            (0.4, -0.2, 0.0),
            (0.4, 0.2, 0.0),
            (-0.4, 0.2, 0.0),
            (0.0, 0.0, 0.7),
        ),
        (),
        ((0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)),
    )
    mesh.update()
    obj = bpy.data.objects.new("ControlShapeSourceMesh", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _mesh_signature(obj):
    return (
        tuple(tuple(float(value) for value in vertex.co) for vertex in obj.data.vertices),
        tuple(tuple(int(index) for index in polygon.vertices) for polygon in obj.data.polygons),
        tuple(float(value) for row in obj.matrix_world for value in row),
    )


def _constraint_signature(armature):
    def value(constraint, name, default=None):
        return getattr(constraint, name, default)

    return tuple(
        sorted(
            (
                owner.name,
                constraint.name,
                constraint.type,
                bool(constraint.mute),
                float(constraint.influence),
                getattr(value(constraint, "target"), "name", ""),
                str(value(constraint, "subtarget", "")),
                getattr(value(constraint, "pole_target"), "name", ""),
                str(value(constraint, "pole_subtarget", "")),
                int(value(constraint, "chain_count", 0)),
                float(value(constraint, "pole_angle", 0.0)),
                float(value(constraint, "head_tail", 0.0)),
                str(value(constraint, "track_axis", "")),
                str(value(constraint, "owner_space", "")),
                str(value(constraint, "target_space", "")),
            )
            for owner in armature.pose.bones
            for constraint in owner.constraints
        )
    )


def _pose_basis_signature(armature):
    return {pose_bone.name: pose_bone.matrix_basis.copy() for pose_bone in armature.pose.bones}


def _assert_pose_basis_signature(armature, expected, label):
    if set(expected) != {pose_bone.name for pose_bone in armature.pose.bones}:
        raise AssertionError(f"{label}: PoseBone inventory changed")
    for name, matrix in expected.items():
        _assert_matrix_elements_close(
            armature.pose.bones[name].matrix_basis,
            matrix,
            f"{label} matrix_basis '{name}'",
        )


def _shape_assignments(armature):
    return {
        pose_bone.name: pose_bone.custom_shape
        for pose_bone in armature.pose.bones
    }


def _control_nonshape_signature(pose_bone):
    return (
        bool(pose_bone.use_custom_shape_bone_size),
        float(getattr(pose_bone, "custom_shape_wire_width", 1.0)),
        tuple(bool(value) for value in pose_bone.lock_location),
        tuple(bool(value) for value in pose_bone.lock_rotation),
        tuple(bool(value) for value in pose_bone.lock_scale),
        str(pose_bone.rotation_mode),
        tuple(
            sorted(
                (str(key), repr(value))
                for key, value in pose_bone.bone.items()
                if key != STYLE_KEY
            )
        ),
    )


def _assert_shape_assignments_except(armature, expected, allowed_name, label):
    if set(expected) != {pose_bone.name for pose_bone in armature.pose.bones}:
        raise AssertionError(f"{label}: PoseBone inventory changed")
    for name, shape in expected.items():
        if name != allowed_name and armature.pose.bones[name].custom_shape is not shape:
            raise AssertionError(f"{label}: changed non-active control shape on '{name}'")


def _assert_style(target, style, expected_kind, default_shape, label):
    shape = target.custom_shape
    if shape is None or shape.get(limb_ik.KIND_KEY) != expected_kind:
        raise AssertionError(
            f"{label}: widget kind={getattr(shape, 'get', lambda *_: None)(limb_ik.KIND_KEY)}, "
            f"expected {expected_kind!r}"
        )
    raw = target.bone.get(STYLE_KEY, None)
    if style == "DEFAULT":
        if STYLE_KEY in target.bone or raw is not None:
            raise AssertionError(f"{label}: DEFAULT left the style ID property: {raw!r}")
        if target.custom_shape is not default_shape:
            raise AssertionError(f"{label}: DEFAULT did not restore the canonical widget object")
    elif raw != style:
        raise AssertionError(f"{label}: stored style={raw!r}, expected {style!r}")


def _set_shape(style, settings, label):
    if not bpy.ops.character_designer.limb_ik_set_control_shape.poll():
        raise AssertionError(f"{label}: Set Control Shape did not poll")
    result = bpy.ops.character_designer.limb_ik_set_control_shape(style=style)
    if result != {"FINISHED"}:
        raise AssertionError(f"{label}: operator returned {result}: {settings.last_message}")


def _assert_shape_only_change(
    armature,
    target,
    *,
    pose_basis,
    transform,
    visual_state,
    nonshape_state,
    constraints,
    source_rest,
    source_mesh,
    mesh_signature,
    shapes,
    label,
):
    _assert_pose_basis_signature(armature, pose_basis, label)
    if target.custom_shape_transform is not transform:
        raise AssertionError(f"{label}: changed custom_shape_transform")
    visual._assert_visual_state(visual._visual_state(target), visual_state, label)
    if _control_nonshape_signature(target) != nonshape_state:
        raise AssertionError(f"{label}: changed non-shape control state")
    if _constraint_signature(armature) != constraints:
        raise AssertionError(f"{label}: changed a constraint")
    _assert_rest_signature(_source_rest_signature(armature), source_rest, label)
    if _mesh_signature(source_mesh) != mesh_signature:
        raise AssertionError(f"{label}: changed source mesh data")
    _assert_shape_assignments_except(armature, shapes, target.name, label)


def test_selected_control_shape_sequence_is_display_only_and_active_only():
    base.reset_scene()
    source_mesh = _make_source_mesh()
    armature = base.make_humanoid(
        name="ControlShapeSequenceRig",
        include_right=False,
        roll_offset=0.31,
    )
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {settings.last_message}")
    settings.build_method = "DIRECT_PREROLL"
    settings.selected_limb = "LEFT_ARM"
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(f"Build failed: {settings.last_message}")
    bpy.context.view_layer.update()

    inventory = limb_ik._validate_inventory(armature)
    rig = inventory["rigs"][("ARM", "L")]
    target = visual._activate_pose_bone(armature, rig["target"].name)
    pole = armature.pose.bones[rig["pole"].name]
    default_shape = target.custom_shape
    pole_shape = pole.custom_shape
    if default_shape is None or default_shape.get(limb_ik.KIND_KEY) != "HAND":
        raise AssertionError("Fixture Hand Target has no canonical HAND widget")
    if STYLE_KEY in target.bone or STYLE_KEY in pole.bone:
        raise AssertionError("A freshly built control unexpectedly stored a non-default style")

    pose_basis = _pose_basis_signature(armature)
    transform = target.custom_shape_transform
    visual_state = visual._visual_state(target)
    nonshape_state = _control_nonshape_signature(target)
    constraints = _constraint_signature(armature)
    source_rest = _source_rest_signature(armature)
    mesh_signature = _mesh_signature(source_mesh)

    for style, kind in (
        ("ARROW", "CONTROL_ARROW"),
        ("SPHERE", "CONTROL_SPHERE"),
        ("DEFAULT", "HAND"),
    ):
        shapes = _shape_assignments(armature)
        _set_shape(style, settings, f"Set {style}")
        target = armature.pose.bones[rig["target"].name]
        _assert_style(target, style, kind, default_shape, f"Set {style}")
        _assert_shape_only_change(
            armature,
            target,
            pose_basis=pose_basis,
            transform=transform,
            visual_state=visual_state,
            nonshape_state=nonshape_state,
            constraints=constraints,
            source_rest=source_rest,
            source_mesh=source_mesh,
            mesh_signature=mesh_signature,
            shapes=shapes,
            label=f"Set {style}",
        )

    # Multiple selected controls are allowed, but the operator is deliberately
    # an active-control edit.  The non-active Pole must remain untouched.
    target.select = True
    pole.select = True
    armature.data.bones.active = target.bone
    shapes = _shape_assignments(armature)
    _set_shape("ARROW", settings, "Multi-select Set Arrow")
    _assert_style(target, "ARROW", "CONTROL_ARROW", default_shape, "Multi-select Set Arrow")
    if pole.custom_shape is not pole_shape or STYLE_KEY in pole.bone:
        raise AssertionError("Multi-select shape edit changed the non-active Pole")
    _assert_shape_only_change(
        armature,
        target,
        pose_basis=pose_basis,
        transform=transform,
        visual_state=visual_state,
        nonshape_state=nonshape_state,
        constraints=constraints,
        source_rest=source_rest,
        source_mesh=source_mesh,
        mesh_signature=mesh_signature,
        shapes=shapes,
        label="Multi-select Set Arrow",
    )

    # Keep a non-default choice through the destructive internal Rebuild.  The
    # style declaration, not an object-name accident, is the persistence source.
    _set_shape("SPHERE", settings, "Pre-Rebuild Set Sphere")
    before_rebuild_visual = visual._visual_state(target)
    before_rebuild_mesh = _mesh_signature(source_mesh)
    if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
        raise AssertionError(f"Rebuild failed: {settings.last_message}")
    bpy.context.view_layer.update()
    inventory = limb_ik._validate_inventory(armature)
    rebuilt_rig = inventory["rigs"][("ARM", "L")]
    rebuilt_target = armature.pose.bones[rebuilt_rig["target"].name]
    rebuilt_shape = rebuilt_target.custom_shape
    if (
        rebuilt_target.bone.get(STYLE_KEY, None) != "SPHERE"
        or rebuilt_shape is None
        or rebuilt_shape.get(limb_ik.KIND_KEY) != "CONTROL_SPHERE"
    ):
        raise AssertionError("Rebuild did not retain the selected SPHERE control style")
    visual._assert_visual_state(
        visual._visual_state(rebuilt_target),
        before_rebuild_visual,
        "Rebuild retained visual vectors",
    )
    if _mesh_signature(source_mesh) != before_rebuild_mesh:
        raise AssertionError("Rebuild with a custom control style changed source mesh data")

    armature_id = inventory["armature_id"]
    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(f"Remove failed: {settings.last_message}")
    if base.owned_bones(armature) or limb_ik._owned_constraint_records(armature):
        raise AssertionError("Remove left generated bones or constraints")
    if any(
        obj.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        and obj.get(limb_ik.ARMATURE_ID_KEY) == armature_id
        for obj in bpy.data.objects
    ):
        raise AssertionError("Remove left an owned widget object, including custom styles")
    if any(
        mesh.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        and mesh.get(limb_ik.ARMATURE_ID_KEY) == armature_id
        for mesh in bpy.data.meshes
    ):
        raise AssertionError("Remove left an owned widget mesh, including custom styles")
    if bpy.data.collections.get(limb_ik.WIDGET_COLLECTION_NAME) is not None:
        raise AssertionError("Remove left the Limb IK widget collection")
    if any(STYLE_KEY in bone for bone in armature.data.bones):
        raise AssertionError("Remove left a control-shape style property on a source bone")
    if _mesh_signature(source_mesh) != before_rebuild_mesh:
        raise AssertionError("Remove changed source mesh data")


def _stable_role_controls(armature, inventory):
    arm = inventory["rigs"][("ARM", "L")]
    leg = inventory["rigs"][("LEG", "L")]
    controls = {
        "MASTER": armature.pose.bones[inventory["master"].name],
        "HAND_IK": armature.pose.bones[arm["target"].name],
        "FOOT_IK": armature.pose.bones[leg["target"].name],
        "POLE": armature.pose.bones[arm["pole"].name],
        "HEEL_ROLL": armature.pose.bones[leg["heel"].name],
    }
    for role, pose_bone in controls.items():
        if pose_bone.bone.get(limb_ik.ROLE_KEY) != role:
            raise AssertionError(
                f"Stable fixture role {role} resolved '{pose_bone.name}' with "
                f"role={pose_bone.bone.get(limb_ik.ROLE_KEY)!r}"
            )
    return controls


def _widget_signature(obj):
    if obj is None or obj.type != "MESH":
        return None
    return (
        obj.name,
        obj.get(limb_ik.KIND_KEY, None),
        obj.data.name,
        tuple(tuple(float(value) for value in vertex.co) for vertex in obj.data.vertices),
        tuple(tuple(int(index) for index in edge.vertices) for edge in obj.data.edges),
    )


def _optional_widget_signature(armature_id):
    return tuple(
        sorted(
            _widget_signature(obj)
            for obj in bpy.data.objects
            if obj.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
            and obj.get(limb_ik.ARMATURE_ID_KEY) == armature_id
            and obj.get(limb_ik.ROLE_KEY) == "WIDGET"
            and obj.get(limb_ik.KIND_KEY) in {"CONTROL_ARROW", "CONTROL_SPHERE"}
        )
    )


def _control_shape_snapshot(controls):
    return {
        pose_bone.name: {
            "style_present": STYLE_KEY in pose_bone.bone,
            "style": pose_bone.bone.get(STYLE_KEY, None),
            "shape": _widget_signature(pose_bone.custom_shape),
            "transform": (
                pose_bone.custom_shape_transform.name
                if pose_bone.custom_shape_transform is not None
                else ""
            ),
            "visual": visual._visual_state(pose_bone),
            "basis": pose_bone.matrix_basis.copy(),
        }
        for pose_bone in controls.values()
    }


def _assert_control_shape_snapshot(controls, expected, label):
    if set(expected) != {pose_bone.name for pose_bone in controls.values()}:
        raise AssertionError(f"{label}: control-name set changed")
    for pose_bone in controls.values():
        saved = expected[pose_bone.name]
        if (
            (STYLE_KEY in pose_bone.bone) is not saved["style_present"]
            or pose_bone.bone.get(STYLE_KEY, None) != saved["style"]
        ):
            raise AssertionError(f"{label}: style changed on '{pose_bone.name}'")
        if _widget_signature(pose_bone.custom_shape) != saved["shape"]:
            raise AssertionError(f"{label}: Custom Shape changed on '{pose_bone.name}'")
        transform_name = (
            pose_bone.custom_shape_transform.name
            if pose_bone.custom_shape_transform is not None
            else ""
        )
        if transform_name != saved["transform"]:
            raise AssertionError(
                f"{label}: Custom Shape Transform changed on '{pose_bone.name}'"
            )
        visual._assert_visual_state(
            visual._visual_state(pose_bone),
            saved["visual"],
            f"{label} visual '{pose_bone.name}'",
        )
        _assert_matrix_elements_close(
            pose_bone.matrix_basis,
            saved["basis"],
            f"{label} matrix_basis '{pose_bone.name}'",
        )


def _build_stable_role_fixture(name):
    base.reset_scene()
    armature = base.make_humanoid(
        name=name,
        include_right=False,
        roll_offset=0.29,
    )
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {settings.last_message}")
    settings.build_method = "ROLL_DECOUPLED"
    if bpy.ops.character_designer.limb_ik_build_all() != {"FINISHED"}:
        raise AssertionError(f"Stable Build All failed: {settings.last_message}")
    bpy.context.view_layer.update()
    inventory = limb_ik._validate_inventory(armature)
    return armature, settings, inventory, _stable_role_controls(armature, inventory)


def test_stable_all_control_roles_support_shapes_defaults_and_visual_reset():
    armature, settings, inventory, controls = _build_stable_role_fixture(
        "StableControlShapeRolesRig"
    )
    expected_defaults = {
        "MASTER": "MASTER",
        "HAND_IK": "HAND",
        "FOOT_IK": "FOOT",
        "POLE": "POLE_ARROW",
        "HEEL_ROLL": "HEEL",
    }
    default_shapes = {role: pose_bone.custom_shape for role, pose_bone in controls.items()}
    for role, expected_kind in expected_defaults.items():
        shape = default_shapes[role]
        if shape is None or shape.get(limb_ik.KIND_KEY) != expected_kind:
            raise AssertionError(
                f"Stable {role} default kind={getattr(shape, 'get', lambda *_: None)(limb_ik.KIND_KEY)}, "
                f"expected {expected_kind!r}"
            )

    for role, pose_bone in controls.items():
        visual._activate_pose_bone(armature, pose_bone.name)
        _set_shape("SPHERE", settings, f"Stable {role} Set Sphere")
        sphere = armature.pose.bones[pose_bone.name].custom_shape
        _assert_style(
            armature.pose.bones[pose_bone.name],
            "SPHERE",
            "CONTROL_SPHERE",
            default_shapes[role],
            f"Stable {role} Set Sphere",
        )
        if not bpy.ops.character_designer.limb_ik_reset_control_visual.poll():
            raise AssertionError(f"Stable {role}: Reset Visual did not poll for Sphere")
        if bpy.ops.character_designer.limb_ik_reset_control_visual() != {"FINISHED"}:
            raise AssertionError(
                f"Stable {role}: Reset Visual failed: {settings.last_message}"
            )
        current = armature.pose.bones[pose_bone.name]
        if (
            current.custom_shape is not sphere
            or current.bone.get(STYLE_KEY, None) != "SPHERE"
        ):
            raise AssertionError(
                f"Stable {role}: Reset Visual changed the SPHERE shape/style"
            )
        _set_shape("DEFAULT", settings, f"Stable {role} Restore Default")
        _assert_style(
            current,
            "DEFAULT",
            expected_defaults[role],
            default_shapes[role],
            f"Stable {role} Restore Default",
        )

    # Explicitly cover the shared non-Pole Arrow widget rather than relying on
    # the Direct Hand test alone.
    hand = controls["HAND_IK"]
    visual._activate_pose_bone(armature, hand.name)
    _set_shape("ARROW", settings, "Stable Hand Set Arrow")
    _assert_style(
        hand,
        "ARROW",
        "CONTROL_ARROW",
        default_shapes["HAND_IK"],
        "Stable Hand Set Arrow",
    )
    _set_shape("DEFAULT", settings, "Stable Hand Restore Default")
    _assert_style(
        hand,
        "DEFAULT",
        expected_defaults["HAND_IK"],
        default_shapes["HAND_IK"],
        "Stable Hand Restore Default",
    )

    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(f"Stable role Remove failed: {settings.last_message}")


def test_control_shape_rebuild_failure_restores_styles_shapes_and_optional_widgets():
    armature, settings, inventory, controls = _build_stable_role_fixture(
        "ControlShapeRollbackRig"
    )
    requested = {
        "MASTER": "SPHERE",
        "HAND_IK": "ARROW",
        "FOOT_IK": "SPHERE",
        # A Stable Pole Arrow reuses its canonical Pole arrowhead but must still
        # preserve the explicit ARROW style declaration through rollback.
        "POLE": "ARROW",
        "HEEL_ROLL": "SPHERE",
    }
    for role, style in requested.items():
        pose_bone = controls[role]
        visual._activate_pose_bone(armature, pose_bone.name)
        _set_shape(style, settings, f"Rollback fixture {role} {style}")

    inventory = limb_ik._validate_inventory(armature)
    controls = _stable_role_controls(armature, inventory)
    old_ids = {key: rig["rig_id"] for key, rig in inventory["rigs"].items()}
    old_shapes = _control_shape_snapshot(controls)
    old_optional_widgets = _optional_widget_signature(inventory["armature_id"])
    optional_kinds = {signature[1] for signature in old_optional_widgets}
    if optional_kinds != {"CONTROL_ARROW", "CONTROL_SPHERE"}:
        raise AssertionError(
            f"Rollback fixture did not own both optional widget kinds: {optional_kinds}"
        )

    original_create = limb_ik._create_constraints_and_shapes
    calls = {"count": 0}

    def fail_new_build_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("injected control-shape Rebuild failure")
        return original_create(*args, **kwargs)

    limb_ik._create_constraints_and_shapes = fail_new_build_once
    try:
        result = base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild)
    finally:
        limb_ik._create_constraints_and_shapes = original_create
    if result != {"CANCELLED"}:
        raise AssertionError("Injected control-shape Rebuild failure did not cancel")
    if calls["count"] < 2:
        raise AssertionError("Injected Rebuild did not exercise snapshot recovery")

    restored = limb_ik._validate_inventory(armature)
    restored_ids = {key: rig["rig_id"] for key, rig in restored["rigs"].items()}
    if restored_ids != old_ids:
        raise AssertionError("Failed Rebuild did not restore the exact prior rig IDs")
    restored_controls = _stable_role_controls(armature, restored)
    _assert_control_shape_snapshot(
        restored_controls,
        old_shapes,
        "Failed Rebuild control-shape recovery",
    )
    restored_optional_widgets = _optional_widget_signature(restored["armature_id"])
    if restored_optional_widgets != old_optional_widgets:
        raise AssertionError(
            "Failed Rebuild did not restore the exact optional Arrow/Sphere widget set"
        )


def _opaque_theme_color(value):
    components = tuple(float(component) for component in value)
    return (*components[:3], 1.0)


def _color_close(actual, expected):
    return max(abs(float(a) - float(b)) for a, b in zip(actual, expected)) <= COLOR_TOLERANCE


def _count_color(values, expected):
    return sum(1 for value in values if _color_close(value, expected))


def test_direct_pole_guide_colors_follow_pose_selection_and_batch_together():
    base.reset_scene()
    armature = base.make_humanoid(
        name="PoleGuideColorRig",
        include_right=True,
        roll_offset=0.23,
    )
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {settings.last_message}")
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_all() != {"FINISHED"}:
        raise AssertionError(f"Build All failed: {settings.last_message}")
    bpy.context.view_layer.update()

    inventory = limb_ik._validate_inventory(armature)
    poles = tuple(
        armature.pose.bones[rig["pole"].name]
        for _key, rig in sorted(inventory["rigs"].items())
    )
    if len(poles) != 4:
        raise AssertionError(f"Fixture expected four Direct Poles, found {len(poles)}")
    armature.data.show_bone_colors = True
    for pole in poles:
        pole.bone.color.palette = "DEFAULT"
        pole.select = False
    armature.data.bones.active = None

    theme = bpy.context.preferences.themes[0].view_3d
    wire = _opaque_theme_color(theme.wire)
    selected = _opaque_theme_color(theme.bone_pose)
    active = _opaque_theme_color(theme.bone_pose_active)

    normal_segments = limb_ik._direct_pole_guide_segments(bpy.context)
    if len(normal_segments) != 4 or any(len(segment) != 3 for segment in normal_segments):
        raise AssertionError(
            "Direct Pole guide helper did not return four (joint, pole, color) segments: "
            f"count={len(normal_segments)}, lengths={[len(segment) for segment in normal_segments]}, "
            f"context_mode={bpy.context.mode!r}, object_mode={armature.mode!r}, "
            f"schema={armature.data.get(limb_ik.SCHEMA_KEY, None)!r}, "
            f"active={getattr(bpy.context.object, 'name', None)!r}, "
            f"visible={armature.visible_get(view_layer=bpy.context.view_layer)!r}"
        )
    if _count_color((segment[2] for segment in normal_segments), wire) != 4:
        raise AssertionError("Unselected Pole shafts did not use the theme wire color")

    poles[0].select = True
    poles[1].select = True
    armature.data.bones.active = poles[1].bone
    bpy.context.view_layer.update()
    segments = limb_ik._direct_pole_guide_segments(bpy.context)
    colors = tuple(segment[2] for segment in segments)
    expected_counts = (
        (wire, 2, "wire"),
        (selected, 1, "bone_pose"),
        (active, 1, "bone_pose_active"),
    )
    for color, count, label in expected_counts:
        actual = _count_color(colors, color)
        if actual != count:
            raise AssertionError(
                f"Pole selection colors contain {actual} {label} segment(s), expected {count}"
            )

    batches = limb_ik._pole_guide_line_batches(segments)
    if not isinstance(batches, (tuple, list)):
        raise AssertionError("Pole guide color batches are not an ordered sequence")
    batch_colors = []
    total_vertices = 0
    for batch in batches:
        if not isinstance(batch, (tuple, list)) or len(batch) != 2:
            raise AssertionError("A Pole guide color batch is not (color, vertices)")
        color, vertices = batch
        if len(color) != 4 or len(vertices) % 2:
            raise AssertionError("A Pole guide batch has malformed color or line vertices")
        batch_colors.append(tuple(color))
        total_vertices += len(vertices)
        matching_segments = [segment for segment in segments if _color_close(segment[2], color)]
        if len(vertices) != 2 * len(matching_segments):
            raise AssertionError("Pole guide batching split or duplicated a same-color shaft")
        expected_points = [Vector(point) for segment in matching_segments for point in segment[:2]]
        actual_points = [Vector(point) for point in vertices]
        while expected_points:
            point = expected_points.pop()
            match_index = next(
                (
                    index
                    for index, candidate in enumerate(actual_points)
                    if (candidate - point).length <= VECTOR_TOLERANCE
                ),
                None,
            )
            if match_index is None:
                raise AssertionError("Pole guide color batch lost or changed a shaft endpoint")
            actual_points.pop(match_index)
        if actual_points:
            raise AssertionError("Pole guide color batch emitted an unexpected endpoint")
    if total_vertices != 2 * len(segments):
        raise AssertionError("Pole guide color batching lost or duplicated a complete shaft")
    for color, _count, label in expected_counts:
        if _count_color(batch_colors, color) != 1:
            raise AssertionError(f"Pole guide batches did not group {label} into one draw call")

    # Match Blender's effective bone-color inheritance.  A PoseBone DEFAULT
    # palette inherits its Armature Bone color; a non-default Pose palette
    # overrides it; disabling bone colors returns to the ordinary pose theme.
    probe = poles[0]
    for pole in poles:
        pole.select = False
    armature.data.bones.active = None
    probe.bone.color.palette = "THEME01"
    probe.color.palette = "DEFAULT"
    bpy.context.view_layer.update()
    bone_theme = _opaque_theme_color(
        bpy.context.preferences.themes[0].bone_color_sets[0].normal
    )
    inherited = limb_ik._direct_pole_guide_segments(bpy.context)
    inherited_color = next(
        segment[2]
        for segment in inherited
        if (Vector(segment[1]) - limb_ik._custom_shape_anchor_world(armature, probe)).length
        <= VECTOR_TOLERANCE
    )
    if not _color_close(inherited_color, bone_theme):
        raise AssertionError("Pole shaft did not inherit its Armature Bone theme color")

    probe.color.palette = "THEME02"
    bpy.context.view_layer.update()
    pose_theme = _opaque_theme_color(
        bpy.context.preferences.themes[0].bone_color_sets[1].normal
    )
    overridden = limb_ik._direct_pole_guide_segments(bpy.context)
    overridden_color = next(
        segment[2]
        for segment in overridden
        if (Vector(segment[1]) - limb_ik._custom_shape_anchor_world(armature, probe)).length
        <= VECTOR_TOLERANCE
    )
    if not _color_close(overridden_color, pose_theme):
        raise AssertionError("Pole shaft did not use its PoseBone theme override")

    armature.data.show_bone_colors = False
    bpy.context.view_layer.update()
    disabled = limb_ik._direct_pole_guide_segments(bpy.context)
    disabled_color = next(
        segment[2]
        for segment in disabled
        if (Vector(segment[1]) - limb_ik._custom_shape_anchor_world(armature, probe)).length
        <= VECTOR_TOLERANCE
    )
    if not _color_close(disabled_color, wire):
        raise AssertionError("Disabled bone colors did not restore the theme wire color")
    armature.data.show_bone_colors = True
    probe.color.palette = "DEFAULT"
    probe.bone.color.palette = "DEFAULT"

    # The helper is read-only: selection-color evaluation must not create any
    # bones, constraints, objects, meshes, or persistent armature metadata.
    bone_count = len(armature.data.bones)
    constraint_count = sum(len(pose_bone.constraints) for pose_bone in armature.pose.bones)
    object_count = len(bpy.data.objects)
    mesh_count = len(bpy.data.meshes)
    metadata = {
        key: armature.data.get(key, None)
        for key in (
            limb_ik.ARMATURE_ID_KEY,
            limb_ik.SCHEMA_KEY,
            limb_ik.DIRECT_REST_KEY,
        )
    }
    limb_ik._pole_guide_line_batches(limb_ik._direct_pole_guide_segments(bpy.context))
    if (
        len(armature.data.bones) != bone_count
        or sum(len(pose_bone.constraints) for pose_bone in armature.pose.bones)
        != constraint_count
        or len(bpy.data.objects) != object_count
        or len(bpy.data.meshes) != mesh_count
        or {
            key: armature.data.get(key, None)
            for key in metadata
        }
        != metadata
    ):
        raise AssertionError("Read-only Pole color batching changed Blender data")


def test_pole_sphere_hides_connector_and_arrow_default_restore():
    for method, label in (
        ("DIRECT_PREROLL", "Direct"),
        ("ROLL_DECOUPLED", "Stable"),
    ):
        base.reset_scene()
        armature = base.make_humanoid(
            name=f"{label}PoleSphereConnectorRig",
            include_right=False,
            roll_offset=0.27,
        )
        result, settings = base.analyze(armature)
        if result != {"FINISHED"}:
            raise AssertionError(f"{label} Analyze failed: {settings.last_message}")
        settings.build_method = method
        settings.selected_limb = "LEFT_ARM"
        if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
            raise AssertionError(f"{label} Build failed: {settings.last_message}")
        bpy.context.view_layer.update()

        inventory = limb_ik._validate_inventory(armature)
        rig = inventory["rigs"][("ARM", "L")]
        pole = visual._activate_pose_bone(armature, rig["pole"].name)
        default_shape = pole.custom_shape
        line = rig["line"]
        line_shape = (
            armature.pose.bones[line.name].custom_shape
            if line is not None
            else None
        )

        def assert_connector(visible, step):
            current_inventory = limb_ik._validate_inventory(armature)
            current_rig = current_inventory["rigs"][("ARM", "L")]
            if method == "DIRECT_PREROLL":
                count = len(limb_ik._direct_pole_guide_segments(bpy.context))
                if count != int(visible):
                    raise AssertionError(
                        f"{label} {step}: GPU connector count={count}, "
                        f"expected {int(visible)}"
                    )
                return
            current_line = current_rig["line"]
            current_line_pose = armature.pose.bones[current_line.name]
            if bool(current_line.hide) == bool(visible):
                raise AssertionError(
                    f"{label} {step}: VIS connector hidden={current_line.hide}, "
                    f"expected {not visible}"
                )
            if current_line_pose.custom_shape is not line_shape:
                raise AssertionError(
                    f"{label} {step}: hiding the connector changed its POLE_LINE widget"
                )
            if not current_line.hide_select:
                raise AssertionError(
                    f"{label} {step}: hiding the connector made its helper selectable"
                )

        assert_connector(True, "Default")
        _set_shape("SPHERE", settings, f"{label} Set SPHERE before Rebuild")
        _assert_style(
            pole,
            "SPHERE",
            "CONTROL_SPHERE",
            default_shape,
            f"{label} Set SPHERE before Rebuild",
        )
        assert_connector(False, "Set SPHERE before Rebuild")
        if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
            raise AssertionError(
                f"{label} Rebuild with Sphere failed: {settings.last_message}"
            )
        bpy.context.view_layer.update()
        inventory = limb_ik._validate_inventory(armature)
        rig = inventory["rigs"][("ARM", "L")]
        pole = visual._activate_pose_bone(armature, rig["pole"].name)
        default_shape = next(
            obj
            for obj in bpy.data.objects
            if limb_ik._owned(obj, inventory["armature_id"], role="WIDGET")
            and obj.get(limb_ik.KIND_KEY) == "POLE_ARROW"
        )
        line = rig["line"]
        line_shape = (
            armature.pose.bones[line.name].custom_shape
            if line is not None
            else None
        )
        _assert_style(
            pole,
            "SPHERE",
            "CONTROL_SPHERE",
            default_shape,
            f"{label} Rebuild retained SPHERE",
        )
        assert_connector(False, "Rebuild retained SPHERE")

        for style, kind, visible in (
            ("ARROW", "POLE_ARROW", True),
            ("SPHERE", "CONTROL_SPHERE", False),
            ("DEFAULT", "POLE_ARROW", True),
        ):
            _set_shape(style, settings, f"{label} Set {style}")
            pole = armature.pose.bones[rig["pole"].name]
            _assert_style(
                pole,
                style,
                kind,
                default_shape,
                f"{label} Set {style}",
            )
            assert_connector(visible, f"Set {style}")


def main():
    base.ensure_registered()
    tests = (
        test_selected_control_shape_sequence_is_display_only_and_active_only,
        test_stable_all_control_roles_support_shapes_defaults_and_visual_reset,
        test_control_shape_rebuild_failure_restores_styles_shapes_and_optional_widgets,
        test_direct_pole_guide_colors_follow_pose_selection_and_batch_together,
        test_pole_sphere_hides_connector_and_arrow_default_restore,
    )
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        base.reset_scene()


if __name__ == "__main__":
    main()
