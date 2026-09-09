"""Disposable real-X integration probe for Character Designer Limb IK.

The caller must open ``X.blend`` in a separate Blender background process.
This probe loads the current source add-on, analyzes ``metarig``, builds both
arm and leg rigs in memory, audits the generated ownership and IK wiring, then
removes the generated rig.  It intentionally never saves the Blend file.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
BLEND_PATH = PROJECT_ROOT / "X.blend"
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

import character_designer
from character_designer import limb_ik


ARMATURE_NAME = "metarig"
MESH_NAME = "Cosha"
EXPECTED_CHAINS = {
    ("ARM", "L"): ("upper_arm.L", "forearm.L", "hand.L"),
    ("ARM", "R"): ("upper_arm.R", "forearm.R", "hand.R"),
    ("LEG", "L"): ("thigh.L", "shin.L", "foot.L"),
    ("LEG", "R"): ("thigh.R", "shin.R", "foot.R"),
}
EXPECTED_CONTROLS = {
    ("ARM", "L"): ("CTRL_hand_IK.L", "CTRL_elbow_pole.L"),
    ("ARM", "R"): ("CTRL_hand_IK.R", "CTRL_elbow_pole.R"),
    ("LEG", "L"): ("CTRL_foot_IK.L", "CTRL_knee_pole.L"),
    ("LEG", "R"): ("CTRL_foot_IK.R", "CTRL_knee_pole.R"),
}
POLE_DIRECTION_PROPERTIES = {
    ("ARM", "L"): "left_arm_pole_direction",
    ("ARM", "R"): "right_arm_pole_direction",
    ("LEG", "L"): "left_leg_pole_direction",
    ("LEG", "R"): "right_leg_pole_direction",
}
DEFAULT_POLE_DIRECTIONS = {
    ("ARM", "L"): Vector((0.0, 1.0, 0.0)),
    ("ARM", "R"): Vector((0.0, 1.0, 0.0)),
    ("LEG", "L"): Vector((0.0, -1.0, 0.0)),
    ("LEG", "R"): Vector((0.0, -1.0, 0.0)),
}
SELECTED_LIMBS = {
    ("ARM", "L"): "LEFT_ARM",
    ("ARM", "R"): "RIGHT_ARM",
    ("LEG", "L"): "LEFT_LEG",
    ("LEG", "R"): "RIGHT_LEG",
}
CUSTOM_REBUILD_DIRECTIONS = {
    ("ARM", "L"): Vector((0.18, 1.0, 0.14)).normalized(),
    ("ARM", "R"): Vector((-0.16, 1.0, -0.12)).normalized(),
    ("LEG", "L"): Vector((0.13, -1.0, 0.1)).normalized(),
    ("LEG", "R"): Vector((-0.11, -1.0, -0.09)).normalized(),
}
EXPECTED_CURRENT_BONES = {
    limb_ik.MASTER_NAME,
    *(name for pair in EXPECTED_CONTROLS.values() for name in pair),
    *(limb_ik.LIMB_SPEC[kind][role].format(side=side) for kind, side in EXPECTED_CHAINS for role in ("line", "display")),
    *(limb_ik.LIMB_SPEC[kind][role].format(side=side) for kind, side in EXPECTED_CHAINS for role in ("mch_upper", "mch_lower", "ori_upper", "ori_lower")),
    *(limb_ik.LIMB_SPEC["LEG"][role].format(side=side) for side in ("L", "R") for role in ("heel", "solver_target")),
}
NO_POP_POSITION_TOLERANCE = 2.0e-5
NO_POP_ROTATION_TOLERANCE_DEGREES = 0.05
SAVED_REBUILD_POSITION_TOLERANCE = 5.0e-5
FUNCTION_POSITION_TOLERANCE = 2.0e-4
FUNCTION_ROTATION_TOLERANCE_DEGREES = 0.5
POLE_ALIGNMENT_DOT_MIN = 0.999
EXPECTED_ARM_RESIDUAL_RATIO = 0.009185
ARM_RESIDUAL_RATIO_TOLERANCE = 5.0e-6


def _set_pole_directions(settings, directions):
    for key, direction in directions.items():
        setattr(settings, POLE_DIRECTION_PROPERTIES[key], direction)


def _settings_pole_direction(settings, key):
    return Vector(getattr(settings, POLE_DIRECTION_PROPERTIES[key]))


def _reset_all_pole_directions_with_operator(settings):
    for key, selection in SELECTED_LIMBS.items():
        settings.selected_limb = selection
        result = bpy.ops.character_designer.limb_ik_default_pole_direction()
        if result != {"FINISHED"}:
            raise AssertionError(f"Default Direction failed for {key}: {result}; {settings.last_message}")
        actual = _settings_pole_direction(settings, key)
        expected = DEFAULT_POLE_DIRECTIONS[key]
        if (actual - expected).length > 1.0e-9:
            raise AssertionError(
                f"Default Direction did not restore the fixed {key} axis: "
                f"{tuple(actual)} != {tuple(expected)}"
            )


def _assert_x_anatomical_pole_directions(armature):
    inventory = limb_ik._validate_inventory(armature)
    diagnostics = {}
    for key, rig in sorted(inventory["rigs"].items()):
        kind, side = key
        upper = armature.data.bones[rig["chain"][0]]
        lower = armature.data.bones[rig["chain"][1]]
        axis = Vector(lower.tail_local) - Vector(upper.head_local)
        direction = limb_ik._project_perpendicular(
            DEFAULT_POLE_DIRECTIONS[key],
            axis,
        )
        if direction.length <= limb_ik.EPSILON:
            raise AssertionError(f"Real X {key} anatomical axis is chain-parallel")
        direction.normalize()
        saved = Vector(rig["pole"][limb_ik.POLE_DIRECTION_KEY]).normalized()
        pole_projection = limb_ik._project_perpendicular(
            Vector(rig["pole"].head_local) - Vector(upper.head_local),
            axis,
        )
        if pole_projection.length <= limb_ik.EPSILON:
            raise AssertionError(f"Real X {key} Pole has no perpendicular projection")
        pole_projection.normalize()
        if saved.dot(direction) <= 0.999999 or pole_projection.dot(direction) <= 0.999999:
            raise AssertionError(
                f"Real X {key} Pole does not follow its anatomical axis: "
                f"saved={tuple(saved)}, projected={tuple(pole_projection)}, expected={tuple(direction)}"
            )
        if kind == "ARM" and saved.y <= 0.95:
            raise AssertionError(f"Real X {key} elbow Pole is not behind the character at +Y: {tuple(saved)}")
        if kind == "LEG":
            if saved.y >= -0.99:
                raise AssertionError(f"Real X {key} knee Pole is not forward at -Y: {tuple(saved)}")
            if abs(saved.x) > 0.01:
                raise AssertionError(f"Real X {key} knee Pole retained a lateral component: {tuple(saved)}")
        diagnostics[f"{kind}.{side}"] = {
            "saved": tuple(saved),
            "pole_projection": tuple(pole_projection),
        }
    return diagnostics


def _file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _freeze(value):
    """Return a deterministic, process-local snapshot of common Blender values."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return ("BYTES", value.hex())
    if isinstance(value, bpy.types.ID):
        return (
            "ID",
            value.bl_rna.identifier,
            value.name_full,
            value.library.filepath if value.library else "",
            value.as_pointer(),
        )
    if isinstance(value, dict) or hasattr(value, "keys"):
        try:
            return tuple(sorted((str(key), _freeze(value[key])) for key in value.keys()))
        except (AttributeError, KeyError, ReferenceError, TypeError):
            pass
    try:
        return tuple(_freeze(item) for item in value)
    except (ReferenceError, TypeError):
        pass
    if hasattr(value, "as_pointer"):
        try:
            return (
                "RNA",
                getattr(getattr(value, "bl_rna", None), "identifier", type(value).__name__),
                getattr(value, "name", ""),
                value.as_pointer(),
            )
        except (ReferenceError, TypeError):
            pass
    return repr(value)


def _id_properties(owner):
    try:
        keys = tuple(owner.keys())
    except (AttributeError, ReferenceError, TypeError):
        return ()
    return tuple(sorted((str(key), _freeze(owner[key])) for key in keys))


def _writable_rna_signature(owner):
    values = []
    for prop in owner.bl_rna.properties:
        name = prop.identifier
        if name == "rna_type" or prop.is_readonly:
            continue
        try:
            value = getattr(owner, name)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            continue
        values.append((name, _freeze(value)))
    return tuple(values)


def _attribute_element_signature(element):
    values = []
    for prop in element.bl_rna.properties:
        if prop.identifier == "rna_type":
            continue
        try:
            values.append((prop.identifier, _freeze(getattr(element, prop.identifier))))
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            continue
    return tuple(values)


def _mesh_data_signature(mesh):
    attributes = []
    for attribute in mesh.attributes:
        attributes.append(
            (
                attribute.name,
                attribute.data_type,
                attribute.domain,
                tuple(_attribute_element_signature(item) for item in attribute.data),
            )
        )
    uv_layers = []
    for layer in mesh.uv_layers:
        uv_layers.append(
            (
                layer.name,
                bool(layer.active),
                bool(layer.active_clone),
                bool(layer.active_render),
                tuple(_attribute_element_signature(item) for item in layer.data),
            )
        )
    shape_keys = None
    if mesh.shape_keys is not None:
        keys = mesh.shape_keys
        shape_keys = (
            keys.as_pointer(),
            keys.name,
            bool(keys.use_relative),
            float(keys.eval_time),
            keys.reference_key.name if keys.reference_key else "",
            _id_properties(keys),
            tuple(
                (
                    block.name,
                    block.relative_key.name if block.relative_key else "",
                    float(block.value),
                    float(block.slider_min),
                    float(block.slider_max),
                    bool(block.mute),
                    block.interpolation,
                    tuple(tuple(float(value) for value in point.co) for point in block.data),
                )
                for block in keys.key_blocks
            ),
        )
    return (
        mesh.as_pointer(),
        mesh.name,
        _id_properties(mesh),
        tuple(tuple(float(value) for value in vertex.co) for vertex in mesh.vertices),
        tuple(
            (
                tuple(int(value) for value in edge.vertices),
                bool(edge.use_seam),
                bool(edge.use_edge_sharp),
            )
            for edge in mesh.edges
        ),
        tuple((int(loop.vertex_index), int(loop.edge_index)) for loop in mesh.loops),
        tuple(
            (
                int(polygon.loop_start),
                int(polygon.loop_total),
                tuple(int(value) for value in polygon.vertices),
                int(polygon.material_index),
                bool(polygon.use_smooth),
            )
            for polygon in mesh.polygons
        ),
        tuple(attributes),
        tuple(uv_layers),
        tuple(material.as_pointer() if material else 0 for material in mesh.materials),
        shape_keys,
    )


def _vertex_group_signature(mesh_obj):
    groups = tuple(
        (
            group.index,
            group.name,
            bool(group.lock_weight),
            _id_properties(group),
        )
        for group in mesh_obj.vertex_groups
    )
    memberships = tuple(
        tuple((item.group, float(item.weight)) for item in vertex.groups)
        for vertex in mesh_obj.data.vertices
    )
    return groups, memberships, int(mesh_obj.vertex_groups.active_index)


def _modifier_signature(mesh_obj):
    return tuple(
        (
            modifier.as_pointer(),
            modifier.name,
            modifier.type,
            _id_properties(modifier),
            _writable_rna_signature(modifier),
        )
        for modifier in mesh_obj.modifiers
    )


def _mesh_object_signature(mesh_obj):
    parent = mesh_obj.parent
    return (
        mesh_obj.as_pointer(),
        mesh_obj.name,
        mesh_obj.data.as_pointer(),
        parent.as_pointer() if parent else 0,
        mesh_obj.parent_type,
        mesh_obj.parent_bone,
        tuple(tuple(float(value) for value in row) for row in mesh_obj.matrix_world),
        tuple(tuple(float(value) for value in row) for row in mesh_obj.matrix_parent_inverse),
        _id_properties(mesh_obj),
    )


def _cosha_signature(mesh_obj):
    return (
        _mesh_object_signature(mesh_obj),
        _mesh_data_signature(mesh_obj.data),
        _vertex_group_signature(mesh_obj),
        _modifier_signature(mesh_obj),
    )


def _enter_armature_mode(armature, mode):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        if bpy.ops.object.mode_set(mode="OBJECT") != {"FINISHED"}:
            raise AssertionError("Could not leave the current mode")
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    if mode != "OBJECT" and bpy.ops.object.mode_set(mode=mode) != {"FINISHED"}:
        raise AssertionError(f"Could not enter {mode} mode")


def _edit_bone_signature(armature, source_names):
    _enter_armature_mode(armature, "EDIT")
    try:
        result = []
        for name in source_names:
            bone = armature.data.edit_bones.get(name)
            if bone is None:
                raise AssertionError(f"Source bone disappeared: {name}")
            result.append(
                (
                    bone.name,
                    bone.parent.name if bone.parent else "",
                    tuple(float(value) for value in bone.head),
                    tuple(float(value) for value in bone.tail),
                    float(bone.roll),
                    bool(bone.use_deform),
                    bool(bone.use_connect),
                )
            )
        return tuple(result)
    finally:
        _enter_armature_mode(armature, "POSE")


def _constraint_signature(constraint):
    return (
        constraint.as_pointer(),
        constraint.name,
        constraint.type,
        _writable_rna_signature(constraint),
    )


def _source_pose_signature(armature, source_names):
    result = []
    for name in source_names:
        pose_bone = armature.pose.bones[name]
        registry = limb_ik._constraint_registry(pose_bone, strict=False)
        owned_names = {
            constraint_name
            for constraint_name, record in registry.items()
            if isinstance(record, dict) and record.get("owner") == limb_ik.OWNER_VALUE
        }
        properties = tuple(
            item for item in _id_properties(pose_bone)
            if item[0] != limb_ik.CONSTRAINT_REGISTRY_KEY
        )
        constraints = tuple(
            _constraint_signature(item)
            for item in pose_bone.constraints
            if item.name not in owned_names
        )
        result.append((name, properties, constraints))
    return tuple(result)


def _source_basis_signature(armature, source_names):
    return tuple(
        (
            name,
            armature.pose.bones[name].rotation_mode,
            tuple(tuple(float(value) for value in row) for row in armature.pose.bones[name].matrix_basis),
        )
        for name in source_names
    )


def _source_armature_data_properties(armature):
    ignored = {limb_ik.ARMATURE_ID_KEY, limb_ik.SCHEMA_KEY}
    return tuple(item for item in _id_properties(armature.data) if item[0] not in ignored)


def _evaluated_limb_pose_snapshot(armature):
    bpy.context.view_layer.update()
    snapshot = {}
    for key, names in EXPECTED_CHAINS.items():
        snapshot[key] = {
            name: {
                "matrix": armature.pose.bones[name].matrix.copy(),
                "head": Vector(armature.pose.bones[name].head),
                "tail": Vector(armature.pose.bones[name].tail),
            }
            for name in names
        }
    return snapshot


def _rotation_difference_degrees(before_matrix, after_matrix):
    before = before_matrix.to_quaternion()
    after = after_matrix.to_quaternion()
    return math.degrees(before.rotation_difference(after).angle)


def _chain_residual_ratio(start, joint, end):
    start = Vector(start)
    joint = Vector(joint)
    end = Vector(end)
    axis = end - start
    if axis.length <= 1.0e-10:
        raise AssertionError("Cannot measure a zero-length IK chain axis")
    projection = start + axis * (joint - start).dot(axis) / axis.length_squared
    total = (joint - start).length + (end - joint).length
    if total <= 1.0e-10:
        raise AssertionError("Cannot measure a zero-length IK chain")
    return (joint - projection).length / total


def _current_residual_ratios(armature):
    bpy.context.view_layer.update()
    result = {}
    for key, names in EXPECTED_CHAINS.items():
        upper, lower, _end = (armature.pose.bones[name] for name in names)
        result[f"{key[0]}.{key[1]}"] = _chain_residual_ratio(
            upper.head,
            lower.head,
            lower.tail,
        )
    return result


def _pole_alignment(armature, key, configured_direction):
    inventory = limb_ik._validate_inventory(armature)
    rig = inventory["rigs"][key]
    upper_name, lower_name, _end_name = EXPECTED_CHAINS[key]
    upper = armature.pose.bones[upper_name]
    lower = armature.pose.bones[lower_name]
    pole = armature.pose.bones[rig["pole"].name]
    display = armature.pose.bones[rig["display"].name]
    start = Vector(upper.head)
    joint = Vector(lower.head)
    end = Vector(lower.tail)
    axis = end - start
    if axis.length <= 1.0e-10:
        raise AssertionError(f"{key} has no usable chain axis")
    axis.normalize()
    bend = (joint - start) - axis * (joint - start).dot(axis)
    pole_projection = (Vector(pole.head) - start) - axis * (Vector(pole.head) - start).dot(axis)
    rest_start = Vector(armature.data.bones[upper_name].head_local)
    rest_end = Vector(armature.data.bones[lower_name].tail_local)
    rest_axis = rest_end - rest_start
    configured_direction = limb_ik._project_perpendicular(Vector(configured_direction), rest_axis)
    saved_direction = Vector(rig["pole"].get(limb_ik.POLE_DIRECTION_KEY, ()))
    visible_from_joint = Vector(pole.head) - joint
    display_to_joint = joint - Vector(display.head)
    display_negative_y = -Vector(display.matrix.to_3x3().col[1])
    if min(bend.length, pole_projection.length, configured_direction.length, saved_direction.length, visible_from_joint.length, display_to_joint.length, display_negative_y.length) <= 1.0e-10:
        raise AssertionError(f"{key} has a degenerate bend/Pole/display direction")
    return {
        "residual_ratio": _chain_residual_ratio(start, joint, end),
        "configured_direction_to_saved_dot": configured_direction.normalized().dot(saved_direction.normalized()),
        "saved_direction_to_visible_pole_dot": saved_direction.normalized().dot(visible_from_joint.normalized()),
        "bend_pole_projection_dot": bend.normalized().dot(pole_projection.normalized()),
        "display_negative_y_to_joint_dot": display_negative_y.normalized().dot(display_to_joint.normalized()),
    }


def _assert_pole_alignment_after_build_and_target_move(armature, configured_directions):
    diagnostics = {"built": {}, "moved_target": {}}
    failures = []
    bpy.context.view_layer.update()
    for key, names in EXPECTED_CHAINS.items():
        label = f"{key[0]}.{key[1]}"
        built = _pole_alignment(armature, key, configured_directions[key])
        diagnostics["built"][label] = built
        for metric in ("configured_direction_to_saved_dot", "saved_direction_to_visible_pole_dot", "bend_pole_projection_dot", "display_negative_y_to_joint_dot"):
            if built[metric] <= POLE_ALIGNMENT_DOT_MIN:
                failures.append(f"{label} built {metric}={built[metric]:.9g}")

        upper = armature.pose.bones[names[0]]
        target = armature.pose.bones[EXPECTED_CONTROLS[key][0]]
        original_basis = target.matrix_basis.copy()
        initial_target_matrix = target.matrix.copy()
        total = max(float(upper.length + armature.pose.bones[names[1]].length), 1.0e-4)
        translation = Vector(upper.head) - Vector(target.head)
        if translation.length <= 1.0e-10:
            raise AssertionError(f"{label} target has no usable inward test direction")
        translation.normalize()
        translation *= total * 0.025
        try:
            moved = initial_target_matrix.copy()
            moved.translation += translation
            target.matrix = moved
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
            moved_diag = _pole_alignment(armature, key, configured_directions[key])
            diagnostics["moved_target"][label] = moved_diag
            for metric in ("bend_pole_projection_dot", "display_negative_y_to_joint_dot"):
                if moved_diag[metric] <= POLE_ALIGNMENT_DOT_MIN:
                    failures.append(f"{label} moved {metric}={moved_diag[metric]:.9g}")
        finally:
            target.matrix_basis = original_basis
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
    print("REAL_X_LIMB_IK_POLE_ALIGNMENT_JSON=" + json.dumps(diagnostics, sort_keys=True))
    if failures:
        raise AssertionError("Pole direction/alignment regression: " + "; ".join(failures))
    return diagnostics


def _no_pop_diagnostics(armature, before):
    bpy.context.view_layer.update()
    diagnostics = {}
    for key, names in EXPECTED_CHAINS.items():
        kind, side = key
        upper_name, lower_name, end_name = names
        current = {name: armature.pose.bones[name] for name in names}
        bone_errors = {}
        for name in names:
            initial = before[key][name]
            pose_bone = current[name]
            bone_errors[name] = {
                "head_offset": (Vector(pose_bone.head) - initial["head"]).length,
                "tail_offset": (Vector(pose_bone.tail) - initial["tail"]).length,
                "rotation_error_deg": _rotation_difference_degrees(
                    initial["matrix"],
                    pose_bone.matrix,
                ),
            }
        diagnostics[f"{kind}.{side}"] = {
            "root_offset": (
                Vector(current[upper_name].head) - before[key][upper_name]["head"]
            ).length,
            "joint_offset": (
                Vector(current[lower_name].head) - before[key][lower_name]["head"]
            ).length,
            "ik_end_offset": (
                Vector(current[end_name].head) - before[key][end_name]["head"]
            ).length,
            "terminal_tail_offset": (
                Vector(current[end_name].tail) - before[key][end_name]["tail"]
            ).length,
            "bones": bone_errors,
        }
    return diagnostics


def _assert_no_pop(
    armature,
    before,
    *,
    position_tolerance=NO_POP_POSITION_TOLERANCE,
    rotation_tolerance_degrees=NO_POP_ROTATION_TOLERANCE_DEGREES,
):
    """Protect the chain root/end while allowing the requested joint re-plane.

    Version 0.27 deliberately rotates and relocates each upper/lower joint so
    the real IK bend follows the configured Pole direction.  The Hand/Foot and
    both chain endpoints remain the no-pop contract.
    """
    diagnostics = _no_pop_diagnostics(armature, before)
    print("REAL_X_LIMB_IK_REPLAN_CONTRACT_JSON=" + json.dumps(diagnostics, sort_keys=True))
    failures = []
    for limb, values in diagnostics.items():
        for point in ("root_offset", "ik_end_offset", "terminal_tail_offset"):
            if values[point] > position_tolerance:
                failures.append(f"{limb} {point}={values[point]:.9g}")
        end_name = EXPECTED_CHAINS[tuple(limb.split("."))][2]
        for bone_name in (end_name,):
            errors = values["bones"][bone_name]
            if errors["head_offset"] > position_tolerance:
                failures.append(f"{limb} {bone_name} head={errors['head_offset']:.9g}")
            if errors["tail_offset"] > position_tolerance:
                failures.append(f"{limb} {bone_name} tail={errors['tail_offset']:.9g}")
            if errors["rotation_error_deg"] > rotation_tolerance_degrees:
                failures.append(
                    f"{limb} {bone_name} rotation={errors['rotation_error_deg']:.9g}deg"
                )
    if failures:
        raise AssertionError("Limb IK changed a protected chain endpoint or Hand/Foot pose: " + "; ".join(failures))
    return diagnostics


def _exercise_generated_controls(armature, before):
    """Move and rotate every generated target, then restore its exact basis."""
    diagnostics = {}
    failures = []
    for key, names in EXPECTED_CHAINS.items():
        kind, side = key
        upper_name, lower_name, end_name = names
        target_name, _pole_name = EXPECTED_CONTROLS[key]
        upper = armature.pose.bones[upper_name]
        lower = armature.pose.bones[lower_name]
        end = armature.pose.bones[end_name]
        target = armature.pose.bones[target_name]
        original_basis = target.matrix_basis.copy()
        original_rotation_mode = target.rotation_mode
        initial_target_matrix = target.matrix.copy()
        initial_lower_tail = Vector(lower.tail)
        initial_end_matrix = end.matrix.copy()
        total = max(float(upper.length + lower.length), 1.0e-4)
        # X's limbs are almost fully extended, so an arbitrary outward move can
        # be physically unreachable with stretching disabled.  Move the target
        # a short distance toward the chain root to test IK following without
        # asking the solver to exceed the source segment lengths.
        translation = Vector(upper.head) - Vector(target.head)
        if translation.length <= 1.0e-8:
            raise AssertionError(f"{kind}.{side} has no usable root-to-target direction")
        translation.normalize()
        translation *= total * 0.025
        limb_diag = {}
        try:
            moved_matrix = initial_target_matrix.copy()
            moved_matrix.translation = moved_matrix.translation + translation
            target.matrix = moved_matrix
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
            target_motion = (Vector(target.head) - initial_target_matrix.translation).length
            lower_motion = (Vector(lower.tail) - initial_lower_tail).length
            follow_error = (Vector(lower.tail) - Vector(target.head)).length
            limb_diag.update(
                {
                    "translation_requested": translation.length,
                    "target_motion": target_motion,
                    "lower_tail_motion": lower_motion,
                    "lower_tail_to_target_error": follow_error,
                }
            )
            if target_motion < translation.length * 0.9:
                failures.append(f"{kind}.{side} target did not accept translation")
            if lower_motion < translation.length * 0.5:
                failures.append(f"{kind}.{side} lower.tail did not follow the IK target")
            if follow_error > FUNCTION_POSITION_TOLERANCE:
                failures.append(
                    f"{kind}.{side} lower.tail target error={follow_error:.9g}"
                )

            target.matrix_basis = original_basis.copy()
            target.rotation_mode = original_rotation_mode
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
            translation_restore_error = (
                Vector(lower.tail) - before[key][lower_name]["tail"]
            ).length
            limb_diag["translation_restore_error"] = translation_restore_error
            if translation_restore_error > NO_POP_POSITION_TOLERANCE:
                failures.append(
                    f"{kind}.{side} translation restore error={translation_restore_error:.9g}"
                )

            restored_target_matrix = target.matrix.copy()
            restored_end_matrix = end.matrix.copy()
            twist_axis = Vector(restored_target_matrix.to_3x3().col[1])
            if twist_axis.length <= 1.0e-8:
                raise AssertionError(f"{kind}.{side} target has no usable twist axis")
            twist_axis.normalize()
            twist_radians = math.radians(10.0)
            pivot = restored_target_matrix.translation.copy()
            twist = Quaternion(twist_axis, twist_radians).to_matrix().to_4x4()
            twisted_matrix = (
                Matrix.Translation(pivot)
                @ twist
                @ Matrix.Translation(-pivot)
                @ restored_target_matrix
            )
            target.matrix = twisted_matrix
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
            target_rotation = _rotation_difference_degrees(
                restored_target_matrix,
                target.matrix,
            )
            end_rotation = _rotation_difference_degrees(
                restored_end_matrix,
                end.matrix,
            )
            end_to_target_error = _rotation_difference_degrees(end.matrix, target.matrix)
            limb_diag.update(
                {
                    "rotation_requested_deg": 10.0,
                    "target_rotation_deg": target_rotation,
                    "end_rotation_deg": end_rotation,
                    "end_to_target_rotation_error_deg": end_to_target_error,
                }
            )
            if target_rotation < 9.0:
                failures.append(f"{kind}.{side} target did not accept rotation")
            if end_rotation < 8.0:
                failures.append(f"{kind}.{side} hand/foot did not follow target rotation")
            if end_to_target_error > FUNCTION_ROTATION_TOLERANCE_DEGREES:
                failures.append(
                    f"{kind}.{side} end-target rotation error={end_to_target_error:.9g}deg"
                )
        finally:
            target.matrix_basis = original_basis.copy()
            target.rotation_mode = original_rotation_mode
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
        limb_diag["rotation_restore_error_deg"] = _rotation_difference_degrees(
            initial_end_matrix,
            end.matrix,
        )
        diagnostics[f"{kind}.{side}"] = limb_diag
        if limb_diag["rotation_restore_error_deg"] > NO_POP_ROTATION_TOLERANCE_DEGREES:
            failures.append(
                f"{kind}.{side} rotation restore={limb_diag['rotation_restore_error_deg']:.9g}deg"
            )
    print("REAL_X_LIMB_IK_FUNCTION_JSON=" + json.dumps(diagnostics, sort_keys=True))
    if failures:
        raise AssertionError("Generated Limb IK controls are not functional: " + "; ".join(failures))
    return diagnostics


def _exercise_master_poles_and_heels(armature):
    inventory = limb_ik._validate_inventory(armature)
    diagnostics = {}
    failures = []

    master = armature.pose.bones[limb_ik.MASTER_NAME]
    master_basis = master.matrix_basis.copy()
    tracked_names = ("Hips", "CTRL_hand_IK.L", "CTRL_foot_IK.L", "CTRL_elbow_pole.L", "CTRL_knee_pole.L")
    tracked_before = {name: armature.pose.bones[name].matrix.copy() for name in tracked_names}
    try:
        master.location += Vector((0.035, -0.02, 0.015))
        bpy.context.view_layer.update()
        motions = {
            name: (armature.pose.bones[name].matrix.translation - matrix.translation).length
            for name, matrix in tracked_before.items()
        }
        diagnostics["master_motion"] = motions
        if any(value < 0.025 for value in motions.values()):
            failures.append(f"Master did not transport all tracked controls/source roots: {motions}")
    finally:
        master.matrix_basis = master_basis
        bpy.context.view_layer.update()

    pole_diagnostics = {}
    for key, rig in inventory["rigs"].items():
        pole = armature.pose.bones[rig["pole"].name]
        line = armature.pose.bones[rig["line"].name]
        display = armature.pose.bones[rig["display"].name]
        basis = pole.matrix_basis.copy()
        try:
            pole.location += Vector((0.0, 0.025, 0.018))
            bpy.context.view_layer.update()
            line_error = (Vector(line.tail) - Vector(pole.head)).length
            aim = Vector(armature.pose.bones[rig["chain"][1]].head) - Vector(display.head)
            aim_axis = -Vector(display.matrix.to_3x3().col[1])
            aim_error = 1.0 - aim_axis.normalized().dot(aim.normalized())
            pole_diagnostics[f"{key[0]}.{key[1]}"] = {"line_error": line_error, "aim_error": aim_error}
            if line_error > 3.0e-4 or aim_error > 3.0e-4:
                failures.append(f"Dynamic Pole display failed for {key}: line={line_error}, aim={aim_error}")
        finally:
            pole.matrix_basis = basis
            bpy.context.view_layer.update()
    diagnostics["poles"] = pole_diagnostics

    heel_diagnostics = {}
    for key in (("LEG", "L"), ("LEG", "R")):
        rig = inventory["rigs"][key]
        heel = armature.pose.bones[rig["heel"].name]
        solver = armature.pose.bones[rig["solver_target"].name]
        foot = armature.pose.bones[rig["chain"][2]]
        basis = heel.matrix_basis.copy()
        solver_before = Vector(solver.head)
        foot_before = Vector(foot.head)
        try:
            heel.rotation_mode = "XYZ"
            heel.rotation_euler.x = math.radians(12.0)
            bpy.context.view_layer.update()
            solver_motion = (Vector(solver.head) - solver_before).length
            foot_motion = (Vector(foot.head) - foot_before).length
            heel_diagnostics[key[1]] = {"solver_motion": solver_motion, "foot_motion": foot_motion}
            if solver_motion < 1.0e-4 or foot_motion < 1.0e-5:
                failures.append(f"Heel Roll did not drive the internal target/Foot for {key[1]}")
        finally:
            heel.matrix_basis = basis
            bpy.context.view_layer.update()
    diagnostics["heels"] = heel_diagnostics
    print("REAL_X_LIMB_IK_ENHANCED_FUNCTION_JSON=" + json.dumps(diagnostics, sort_keys=True))
    if failures:
        raise AssertionError("Enhanced controls are not functional: " + "; ".join(failures))
    return diagnostics


def _assert_vector_close(actual, expected, label, tolerance=2.0e-6):
    distance = (Vector(actual) - Vector(expected)).length
    if distance > tolerance:
        raise AssertionError(f"{label} differs by {distance:.9g}: {tuple(actual)} != {tuple(expected)}")


def _analysis_payload(settings):
    try:
        payload = json.loads(settings.analysis_json)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AssertionError("Analyze Rig did not store valid JSON") from exc
    for key, expected_chain in EXPECTED_CHAINS.items():
        kind, side = key
        result = payload["limbs"][kind][side]
        actual_chain = (result.get("upper"), result.get("lower"), result.get("end"))
        if actual_chain != expected_chain:
            raise AssertionError(f"Analyze misidentified {side} {kind}: {actual_chain}")
        if result.get("status") != "READY":
            raise AssertionError(f"{side} {kind} was not ready with an explicit Pole direction: {result}")
    obsolete = ("modeled bend", "roll fallback", "projected -local Z")
    combined = settings.last_message + " " + " ".join(payload.get("warnings", ()))
    if any(token in combined for token in obsolete):
        raise AssertionError(f"Analyze still advertised obsolete automatic Pole inference: {combined}")
    return payload


def _capture_expected_plans(armature, settings):
    plans = {}
    _enter_armature_mode(armature, "POSE")
    for (kind, side), names in EXPECTED_CHAINS.items():
        chain = limb_ik.LimbChain(kind, side, *names)
        plan = limb_ik._build_plan(
            armature,
            chain,
            settings.pole_distance_ratio,
            _settings_pole_direction(settings, (kind, side)),
        )
        pole_axis = plan.pole_tail - plan.pole_head
        if pole_axis.length <= limb_ik.EPSILON:
            raise AssertionError(f"Planned {kind}.{side} Pole tail has no usable length")
        if pole_axis.normalized().dot(plan.pole_direction.normalized()) <= 0.999999:
            raise AssertionError(
                f"Planned {kind}.{side} Pole tail does not point along its effective direction: "
                f"{tuple(pole_axis)}"
            )
        plans[(kind, side)] = plan
    return plans


def _owned_controls(armature):
    return tuple(
        bone.name
        for bone in armature.data.bones
        if bone.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
    )


def _validate_built_limb(armature, key, expected_plan):
    kind, side = key
    chain = EXPECTED_CHAINS[key]
    target_name, pole_name = EXPECTED_CONTROLS[key]
    target = armature.data.bones.get(target_name)
    pole = armature.data.bones.get(pole_name)
    if target is None or pole is None:
        raise AssertionError(f"Missing generated controls for {side} {kind}")
    for bone, role in (
        (target, limb_ik.LIMB_SPEC[kind]["target_role"]),
        (pole, "POLE"),
    ):
        if bone.use_deform:
            raise AssertionError(f"Generated control unexpectedly deforms: {bone.name}")
        if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE:
            raise AssertionError(f"Generated control lacks owner marker: {bone.name}")
        if bone.get(limb_ik.VERSION_KEY) != limb_ik.RIG_VERSION:
            raise AssertionError(f"Generated control has the wrong version: {bone.name}")
        if bone.get(limb_ik.ROLE_KEY) != role:
            raise AssertionError(f"Generated control has the wrong role: {bone.name}")
        if bone.get(limb_ik.KIND_KEY) != kind or bone.get(limb_ik.SIDE_KEY) != side:
            raise AssertionError(f"Generated control has the wrong limb identity: {bone.name}")
    _assert_vector_close(target.head_local, expected_plan.end, f"{target_name} head")
    _assert_vector_close(target.tail_local, expected_plan.target_tail, f"{target_name} tail")
    _assert_vector_close(pole.head_local, expected_plan.pole_head, f"{pole_name} head")
    _assert_vector_close(pole.tail_local, expected_plan.pole_tail, f"{pole_name} tail")
    pole_axis = Vector(pole.tail_local) - Vector(pole.head_local)
    if pole_axis.length <= limb_ik.EPSILON or pole_axis.normalized().dot(expected_plan.pole_direction.normalized()) <= 0.999999:
        raise AssertionError(f"{pole_name} tail does not point along the effective bend direction")
    actual_direction = Vector(pole.head_local) - expected_plan.pole_joint
    configured_direction = Vector(expected_plan.pole_direction)
    if min(actual_direction.length, configured_direction.length) <= 1.0e-10:
        raise AssertionError(f"Degenerate configured Pole direction for {side} {kind}")
    configured_alignment = actual_direction.normalized().dot(configured_direction.normalized())
    if configured_alignment <= 0.999999:
        raise AssertionError(
            f"{pole_name} did not use its configured Armature-local XYZ direction: {configured_alignment}"
        )

    inventory = limb_ik._validate_inventory(armature)
    rig = inventory["rigs"][key]
    if inventory["schema"] != limb_ik.CURRENT_SCHEMA:
        raise AssertionError("Rebuild did not upgrade X to the current Limb IK schema")
    line = rig["line"]
    display = rig["display"]
    if line is None or display is None or line.parent is None or line.parent.name != chain[0] or display.parent is None or display.parent.name != pole_name:
        raise AssertionError(f"Incorrect dynamic Pole helper hierarchy for {side} {kind}")
    if line.use_connect or pole.use_connect:
        raise AssertionError(f"Pole/helper hierarchy is not Keep Offset for {side} {kind}")
    line_axis = Vector(line.tail_local) - Vector(line.head_local)
    joint_to_pole = Vector(pole.head_local) - Vector(line.head_local)
    if (Vector(line.head_local) - expected_plan.pole_joint).length > 2.0e-6:
        raise AssertionError(f"{line.name} does not start at the planned joint")
    if line_axis.length <= limb_ik.EPSILON or line_axis.length >= joint_to_pole.length:
        raise AssertionError(
            f"{line.name} Rest length is not shorter than joint-to-Pole: "
            f"helper={line_axis.length}, full={joint_to_pole.length}"
        )
    if line_axis.normalized().dot(joint_to_pole.normalized()) <= 0.999999:
        raise AssertionError(f"{line.name} short Rest axis does not aim toward the Pole")
    bpy.context.view_layer.update()
    if (Vector(armature.pose.bones[line.name].tail) - Vector(armature.pose.bones[pole_name].head)).length > 2.0e-4:
        raise AssertionError(f"{line.name} STRETCH_TO does not reach the Pole in Pose Mode")
    if not line.hide_select or not display.hide:
        raise AssertionError(f"Pole helpers are not cleanly display-only for {side} {kind}")
    solver_name = rig["solver_target"].name
    if kind == "LEG":
        if rig["heel"] is None or rig["heel"].parent is None or rig["heel"].parent.name != target_name:
            raise AssertionError(f"Missing Foot -> Heel hierarchy for {side} Leg")
        if rig["solver_target"].parent is None or rig["solver_target"].parent.name != rig["heel"].name:
            raise AssertionError(f"Missing Heel -> internal target hierarchy for {side} Leg")

    end = armature.pose.bones[chain[2]]
    ik_owner, ik, _ik_record = next(
        entry for entry in rig["entries"] if entry[2]["role"] == "IK"
    )
    copy_constraints = tuple(item for item in end.constraints if item.type == "COPY_ROTATION")
    if ik_owner.name != rig["mch_lower"].name or len(copy_constraints) != 2:
        raise AssertionError(f"Unexpected constraint inventory for {side} {kind}")
    copy_rotation = next(
        constraint
        for _owner, constraint, record in rig["entries"]
        if record["role"] == "END_ROTATION"
    )
    if (
        ik.chain_count != 2
        or ik.target is not armature
        or ik.subtarget != solver_name
        or ik.pole_target is not armature
        or ik.pole_subtarget != pole_name
    ):
        raise AssertionError(f"Incorrect IK target/Pole/chain settings for {side} {kind}")
    # Build may refine the analytic seed with Blender's evaluated IK solver to
    # preserve arbitrary-roll source poses.  The no-pop audit below is the
    # authoritative result check; here only require a finite calibrated angle.
    if not math.isfinite(float(ik.pole_angle)):
        raise AssertionError(f"Non-finite Pole Angle for {side} {kind}: {ik.pole_angle}")
    if copy_rotation.target is not armature or copy_rotation.subtarget != solver_name:
        raise AssertionError(f"Incorrect end rotation target for {side} {kind}")
    if copy_rotation.target_space != "WORLD" or copy_rotation.owner_space != "WORLD":
        raise AssertionError(f"End rotation does not use the verified World-space mapping for {side} {kind}")
    if expected_plan.pole_warning:
        raise AssertionError(f"Explicit valid direction produced an obsolete Pole warning: {expected_plan.pole_warning}")


def _assert_protected_unchanged(
    stage,
    armature,
    mesh_obj,
    source_names,
    source_bones_before,
    cosha_before,
):
    source_after = _edit_bone_signature(armature, source_names)
    if source_after != source_bones_before:
        raise AssertionError(f"{stage}: a source bone name/parent/head/tail/roll/deform/connect value changed")
    cosha_after = _cosha_signature(mesh_obj)
    if cosha_after != cosha_before:
        raise AssertionError(f"{stage}: Cosha mesh, weights, object state, or Modifier stack changed")


def _assert_only_expected_constraints(armature, built_keys, source_names):
    expected = {}
    for key in built_keys:
        chain = EXPECTED_CHAINS[key]
        expected.setdefault(chain[0], []).append("COPY_ROTATION")
        expected.setdefault(chain[1], []).append("COPY_ROTATION")
        expected.setdefault(chain[2], []).extend(("COPY_ROTATION", "COPY_ROTATION"))
    for name in source_names:
        bone = armature.data.bones[name]
        if bone.parent is None:
            expected.setdefault(name, []).append("COPY_TRANSFORMS")
    for name in source_names:
        actual = sorted(constraint.type for constraint in armature.pose.bones[name].constraints)
        wanted = sorted(expected.get(name, ()))
        if actual != wanted:
            raise AssertionError(f"Unexpected constraints on {name}: {actual}, expected {wanted}")


def main():
    loaded_path = Path(bpy.data.filepath).resolve()
    if loaded_path != BLEND_PATH.resolve():
        raise AssertionError(f"Probe must be run with X.blend loaded, got: {loaded_path}")
    disk_hash_before = _file_sha256(BLEND_PATH)
    character_designer.register()
    armature = bpy.data.objects.get(ARMATURE_NAME)
    if armature is None or armature.type != "ARMATURE":
        required_names = {name for chain in EXPECTED_CHAINS.values() for name in chain}
        candidates = [
            obj
            for obj in bpy.data.objects
            if obj.type == "ARMATURE"
            and required_names.issubset({bone.name for bone in obj.data.bones})
            and (obj.data.name == ARMATURE_NAME or obj.data.get(limb_ik.ARMATURE_ID_KEY, ""))
        ]
        if len(candidates) == 1:
            armature = candidates[0]
    mesh_obj = bpy.data.objects.get(MESH_NAME)
    if armature is None or armature.type != "ARMATURE":
        raise AssertionError("The real metarig Armature is unavailable")
    if mesh_obj is None or mesh_obj.type != "MESH":
        raise AssertionError("The real Cosha Mesh is unavailable")

    initial_inventory = limb_ik._validate_inventory(armature)
    if initial_inventory["schema"] not in {
        0,
        limb_ik.LEGACY_SCHEMA,
        limb_ik.ENHANCED_SCHEMA,
        limb_ik.CURRENT_SCHEMA,
    }:
        raise AssertionError(f"Saved X has an unsupported Limb IK schema: {initial_inventory['schema']}")
    initial_schema = initial_inventory["schema"]
    initial_rig_keys = tuple(sorted(initial_inventory["rigs"]))
    initial_owned_bones = len(initial_inventory["bones"])
    initial_owned_records = len(initial_inventory["records"])
    initial_saved_directions = {
        key: rig["pole_direction"].copy()
        for key, rig in initial_inventory["rigs"].items()
        if rig["pole_direction"] is not None
    }
    source_names = tuple(
        bone.name
        for bone in armature.data.bones
        if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    )
    missing_chain_bones = sorted({name for names in EXPECTED_CHAINS.values() for name in names} - set(source_names))
    if missing_chain_bones:
        raise AssertionError(f"Real X is missing required source limb bones: {missing_chain_bones}")
    face_related_source_bones = tuple(
        name for name in source_names
        if any(token in name.lower() for token in ("eye", "jaw", "mouth", "lip"))
    )
    source_bones_before = _edit_bone_signature(armature, source_names)
    source_pose_before = _source_pose_signature(armature, source_names)
    source_basis_before = _source_basis_signature(armature, source_names)
    cosha_before = _cosha_signature(mesh_obj)
    armature_data_custom_before = _source_armature_data_properties(armature)
    armature_object_custom_before = _id_properties(armature)

    _enter_armature_mode(armature, "POSE")
    for pose_bone in armature.pose.bones:
        pose_bone.select = pose_bone.name == "upper_arm.L"
    armature.data.bones.active = armature.data.bones["upper_arm.L"]

    analyze_result = bpy.ops.character_designer.limb_ik_analyze()
    if analyze_result != {"FINISHED"}:
        raise AssertionError(f"Analyze Rig failed: {analyze_result}")
    settings = bpy.context.window_manager.character_designer_limb_ik
    _analysis_payload(settings)
    for key, default in DEFAULT_POLE_DIRECTIONS.items():
        expected = initial_saved_directions.get(key, default)
        actual = _settings_pole_direction(settings, key)
        if (actual - expected).length > 1.0e-6:
            source = "saved generated direction" if key in initial_saved_directions else "fixed anatomical default"
            raise AssertionError(
                f"Real X did not hydrate the {key} {source}: {tuple(actual)} != {tuple(expected)}"
            )
    _assert_protected_unchanged(
        "Analyze",
        armature,
        mesh_obj,
        source_names,
        source_bones_before,
        cosha_before,
    )
    if _source_pose_signature(armature, source_names) != source_pose_before:
        raise AssertionError("Analyze changed source PoseBone properties or constraints")
    rebuild_no_pop = {}
    rebuild_result = {"SKIPPED"}
    first_remove_result = {"SKIPPED"}
    if initial_rig_keys:
        # The user's disk may contain controls generated by an earlier build.
        # Remove them only in this disposable process, then validate 0.27 from
        # the exact source skeleton.  The dedicated custom phase below covers
        # current-schema Rebuild without depending on historical Pole angles.
        first_remove_result = bpy.ops.character_designer.limb_ik_remove()
        if first_remove_result != {"FINISHED"}:
            raise AssertionError(f"Remove of the saved generated rig failed: {first_remove_result}; {settings.last_message}")
        if tuple(bone.name for bone in armature.data.bones) != source_names:
            raise AssertionError("First Remove did not restore the exact source-bone inventory/order")
    source_residual_ratios = _current_residual_ratios(armature)
    for side in ("L", "R"):
        actual = source_residual_ratios[f"ARM.{side}"]
        if abs(actual - EXPECTED_ARM_RESIDUAL_RATIO) > ARM_RESIDUAL_RATIO_TOLERANCE:
            raise AssertionError(
                f"Real X ARM.{side} residual is {actual:.9%}, expected approximately "
                f"{EXPECTED_ARM_RESIDUAL_RATIO:.9%}"
            )

    # Build one selected side, customize its XYZ direction, then Rebuild while
    # another dropdown side is selected.  Rebuild must replace only the side
    # that actually exists and must drive the real joint toward its visible Pole.
    selected_analyze_result = bpy.ops.character_designer.limb_ik_analyze()
    if selected_analyze_result != {"FINISHED"}:
        raise AssertionError(f"Analyze before selected Build failed: {selected_analyze_result}; {settings.last_message}")
    _reset_all_pole_directions_with_operator(settings)
    settings.selected_limb = "LEFT_ARM"
    selected_build_result = bpy.ops.character_designer.limb_ik_build_selected()
    if selected_build_result != {"FINISHED"}:
        raise AssertionError(f"Selected Left Arm Build failed: {selected_build_result}; {settings.last_message}")
    selected_inventory = limb_ik._validate_inventory(armature)
    if set(selected_inventory["rigs"]) != {("ARM", "L")}:
        raise AssertionError(f"Selected Build generated unrequested sides: {tuple(sorted(selected_inventory['rigs']))}")
    selected_old_id = selected_inventory["rigs"][("ARM", "L")]["rig_id"]

    settings.left_arm_pole_direction = CUSTOM_REBUILD_DIRECTIONS[("ARM", "L")]
    settings.selected_limb = "RIGHT_LEG"
    custom_expected = _capture_expected_plans(armature, settings)[("ARM", "L")]
    custom_rebuild_result = bpy.ops.character_designer.limb_ik_rebuild()
    if custom_rebuild_result != {"FINISHED"}:
        raise AssertionError(f"Custom Left Arm Rebuild failed: {custom_rebuild_result}; {settings.last_message}")
    custom_inventory = limb_ik._validate_inventory(armature)
    if set(custom_inventory["rigs"]) != {("ARM", "L")}:
        raise AssertionError(f"Rebuild generated unselected sibling sides: {tuple(sorted(custom_inventory['rigs']))}")
    if custom_inventory["rigs"][("ARM", "L")]["rig_id"] == selected_old_id:
        raise AssertionError("Custom Rebuild did not replace the selected-side rig ID")
    _validate_built_limb(armature, ("ARM", "L"), custom_expected)
    custom_alignment = _pole_alignment(armature, ("ARM", "L"), CUSTOM_REBUILD_DIRECTIONS[("ARM", "L")])
    for metric in ("configured_direction_to_saved_dot", "saved_direction_to_visible_pole_dot", "bend_pole_projection_dot", "display_negative_y_to_joint_dot"):
        if custom_alignment[metric] <= POLE_ALIGNMENT_DOT_MIN:
            raise AssertionError(f"Custom Rebuild {metric}={custom_alignment[metric]:.9g}")
    custom_remove_result = bpy.ops.character_designer.limb_ik_remove()
    if custom_remove_result != {"FINISHED"}:
        raise AssertionError(f"Remove after custom Rebuild failed: {custom_remove_result}; {settings.last_message}")
    if tuple(bone.name for bone in armature.data.bones) != source_names:
        raise AssertionError("Custom Rebuild/Remove did not restore the exact source-bone inventory/order")

    analyze_all_result = bpy.ops.character_designer.limb_ik_analyze()
    if analyze_all_result != {"FINISHED"}:
        raise AssertionError(f"Analyze before Build All failed: {analyze_all_result}")
    _reset_all_pole_directions_with_operator(settings)
    _analysis_payload(settings)
    expected_plans = _capture_expected_plans(armature, settings)
    evaluated_pose_before = _evaluated_limb_pose_snapshot(armature)
    build_all_result = bpy.ops.character_designer.limb_ik_build_all()
    if build_all_result != {"FINISHED"}:
        raise AssertionError(f"Build All failed: {build_all_result}; {settings.last_message}")
    all_keys = tuple(EXPECTED_CHAINS)
    for key in all_keys:
        _validate_built_limb(armature, key, expected_plans[key])
    _assert_only_expected_constraints(armature, all_keys, source_names)
    if set(_owned_controls(armature)) != EXPECTED_CURRENT_BONES:
        raise AssertionError(f"Unexpected generated control inventory: {_owned_controls(armature)}")
    current_inventory = limb_ik._validate_inventory(armature)
    if current_inventory["schema"] != limb_ik.CURRENT_SCHEMA or len(current_inventory["records"]) != 47:
        raise AssertionError("Current ownership inventory is incomplete after Build All")
    if len(current_inventory["bones"]) != 37 or len(armature.data.bones) != len(source_names) + 37:
        raise AssertionError(f"Expected 37 current-schema bones, found {len(current_inventory['bones'])}")
    master = armature.data.bones.get(limb_ik.MASTER_NAME)
    if master is None or Vector(master.head_local).length > 1.0e-8:
        raise AssertionError(f"CTRL_master is not at armature-local origin: {tuple(master.head_local) if master else None}")
    no_pop = _assert_no_pop(armature, evaluated_pose_before)
    pole_alignment = _assert_pole_alignment_after_build_and_target_move(armature, DEFAULT_POLE_DIRECTIONS)
    anatomical_poles = _assert_x_anatomical_pole_directions(armature)
    functional = _exercise_generated_controls(armature, evaluated_pose_before)
    enhanced_functional = _exercise_master_poles_and_heels(armature)
    _assert_no_pop(armature, evaluated_pose_before)
    _assert_protected_unchanged(
        "Build All",
        armature,
        mesh_obj,
        source_names,
        source_bones_before,
        cosha_before,
    )

    remove_result = bpy.ops.character_designer.limb_ik_remove()
    if remove_result != {"FINISHED"}:
        raise AssertionError(f"Remove Generated Rig failed: {remove_result}; {settings.last_message}")
    if tuple(bone.name for bone in armature.data.bones) != source_names:
        raise AssertionError("Remove did not restore the exact original source-bone inventory/order")
    if _owned_controls(armature):
        raise AssertionError("Remove left owned control bones behind")
    if _source_pose_signature(armature, source_names) != source_pose_before:
        raise AssertionError("Remove changed non-owned source PoseBone properties/constraints")
    if _source_basis_signature(armature, source_names) != source_basis_before:
        raise AssertionError("Remove changed source PoseBone matrix_basis values")
    if _source_armature_data_properties(armature) != armature_data_custom_before:
        raise AssertionError("Remove left Armature Data ownership properties behind")
    if _id_properties(armature) != armature_object_custom_before:
        raise AssertionError("Remove changed Armature Object custom properties")
    _assert_protected_unchanged(
        "Remove",
        armature,
        mesh_obj,
        source_names,
        source_bones_before,
        cosha_before,
    )
    owned_residue = {
        "objects": tuple(obj.name for obj in bpy.data.objects if obj.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE),
        "meshes": tuple(mesh.name for mesh in bpy.data.meshes if mesh.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE),
        "collections": tuple(collection.name for collection in bpy.data.collections if collection.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE),
        "bone_collections": tuple(collection.name for collection in armature.data.collections if collection.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE),
    }
    if any(owned_residue.values()):
        raise AssertionError(f"Remove left owned generated data behind: {owned_residue}")

    disk_hash_after = _file_sha256(BLEND_PATH)
    if disk_hash_after != disk_hash_before:
        raise AssertionError("X.blend changed on disk; this disposable probe must never save")
    payload = {
        "analyze": sorted(analyze_result),
        "analyze_before_build_all": sorted(analyze_all_result),
        "saved_schema_before": initial_schema,
        "saved_rig_sides_before": tuple(f"{kind}.{side}" for kind, side in initial_rig_keys),
        "saved_owned_bones_before": initial_owned_bones,
        "saved_owned_constraints_before": initial_owned_records,
        "saved_rig_rebuild": sorted(rebuild_result),
        "first_remove": sorted(first_remove_result),
        "build_all": sorted(build_all_result),
        "remove": sorted(remove_result),
        "source_bones": len(source_names),
        "face_related_source_bones": face_related_source_bones,
        "source_residual_ratios": source_residual_ratios,
        "generated_controls_checked": 21,
        "ik_constraints_checked": 4,
        "copy_rotation_constraints_checked": 4,
        "owned_constraints_checked": 19,
        "explicit_pole_directions_checked": 4,
        "pole_alignment_dot_minimum": POLE_ALIGNMENT_DOT_MIN,
        "anatomical_poles": anatomical_poles,
        "pole_built_min_dot": min(
            min(item["configured_direction_to_saved_dot"], item["saved_direction_to_visible_pole_dot"], item["bend_pole_projection_dot"], item["display_negative_y_to_joint_dot"])
            for item in pole_alignment["built"].values()
        ),
        "pole_moved_target_min_dot": min(
            min(item["bend_pole_projection_dot"], item["display_negative_y_to_joint_dot"])
            for item in pole_alignment["moved_target"].values()
        ),
        "saved_rebuild_no_pop_max_joint_offset": max(
            (item["joint_offset"] for item in rebuild_no_pop.values()),
            default=0.0,
        ),
        "saved_rebuild_position_tolerance": SAVED_REBUILD_POSITION_TOLERANCE,
        "no_pop_position_tolerance": NO_POP_POSITION_TOLERANCE,
        "no_pop_rotation_tolerance_degrees": NO_POP_ROTATION_TOLERANCE_DEGREES,
        "no_pop_max_joint_offset": max(item["joint_offset"] for item in no_pop.values()),
        "no_pop_max_ik_end_offset": max(item["ik_end_offset"] for item in no_pop.values()),
        "no_pop_max_rotation_error_degrees": max(
            error["rotation_error_deg"]
            for item in no_pop.values()
            for error in item["bones"].values()
        ),
        "functional_controls_checked": len(functional),
        "enhanced_function_groups_checked": len(enhanced_functional),
        "functional_max_follow_error": max(
            item["lower_tail_to_target_error"] for item in functional.values()
        ),
        "functional_max_end_target_rotation_error_degrees": max(
            item["end_to_target_rotation_error_deg"] for item in functional.values()
        ),
        "cosha_vertices": len(mesh_obj.data.vertices),
        "cosha_vertex_groups": len(mesh_obj.vertex_groups),
        "cosha_modifiers": len(mesh_obj.modifiers),
        "disk_sha256_unchanged": disk_hash_after,
    }
    print("REAL_X_LIMB_IK_JSON=" + json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
