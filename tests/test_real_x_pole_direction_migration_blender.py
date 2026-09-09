"""Read-only, in-memory migration experiment for the saved real-X Limb IK rig.

Run with Blender 5.2, for example::

    blender --background --factory-startup --disable-autoexec \
      --python tests/test_real_x_pole_direction_migration_blender.py -- \
      D:\\path\\to\\X-before-pole-fix.blend

The script deliberately contains no save call.  It opens the same input afresh
for two disposable strategies, verifies exact ownership/resource invariants,
and finally requires SHA-256, mtime, and size to match their initial values.
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
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

from character_designer import limb_ik


EXPECTED_KEYS = {("ARM", "L"), ("ARM", "R"), ("LEG", "L"), ("LEG", "R")}
OLD_SEMANTIC_DIRECTIONS = {
    ("ARM", "L"): Vector((0.0, 1.0, 0.0)),
    ("ARM", "R"): Vector((0.0, 1.0, 0.0)),
    ("LEG", "L"): Vector((0.0, -1.0, 0.0)),
    ("LEG", "R"): Vector((0.0, -1.0, 0.0)),
}
ALIGNMENT_MIN = 0.999
FLOAT_TOLERANCE = 5.0e-7
END_POSITION_TOLERANCE = 2.0e-5
END_ROTATION_TOLERANCE = math.radians(0.05)


def _file_fingerprint(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "sha256": digest.hexdigest().upper(),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _vector_tuple(value):
    return tuple(float(component) for component in value)


def _matrix_tuple(value):
    return tuple(float(component) for row in value for component in row)


def _max_float_error(actual, expected):
    return max((abs(a - b) for a, b in zip(actual, expected)), default=0.0)


def _rotation_error(actual, expected):
    angle = float(actual.to_quaternion().rotation_difference(expected.to_quaternion()).angle)
    angle = abs(angle) % math.tau
    return min(angle, math.tau - angle)


def _matrix_errors(actual, expected):
    return {
        "position": (actual.translation - expected.translation).length,
        "rotation": _rotation_error(actual, expected),
        "scale": (actual.to_scale() - expected.to_scale()).length,
    }


def _freeze(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (Vector, Quaternion)):
        return tuple(float(component) for component in value)
    if isinstance(value, Matrix):
        return _matrix_tuple(value)
    if isinstance(value, dict) or hasattr(value, "keys"):
        try:
            return tuple(sorted((str(key), _freeze(value[key])) for key in value.keys()))
        except (AttributeError, KeyError, ReferenceError, TypeError):
            pass
    if hasattr(value, "bl_rna") and hasattr(value, "name"):
        return (
            getattr(value.bl_rna, "identifier", type(value).__name__),
            getattr(value, "name_full", value.name),
            value.library.filepath if getattr(value, "library", None) else "",
        )
    try:
        return tuple(_freeze(item) for item in value)
    except (ReferenceError, TypeError):
        return repr(value)


def _id_properties(owner):
    return tuple(sorted((str(key), _freeze(owner[key])) for key in owner.keys()))


def _mode_set(context, armature, mode):
    if context.object is not armature or context.view_layer.objects.active is not armature:
        if context.mode != "OBJECT" and context.object is not None:
            bpy.ops.object.mode_set(mode="OBJECT")
        for obj in tuple(context.selected_objects):
            obj.select_set(False)
        armature.select_set(True)
        context.view_layer.objects.active = armature
    if armature.mode != mode:
        bpy.ops.object.mode_set(mode=mode)


def _find_real_armature():
    exact = bpy.data.objects.get("metarig")
    if exact is not None and exact.type == "ARMATURE":
        return exact
    candidates = [
        obj
        for obj in bpy.data.objects
        if obj.type == "ARMATURE"
        and (
            obj.data.name == "metarig"
            or bool(obj.data.get(limb_ik.ARMATURE_ID_KEY, ""))
        )
    ]
    if len(candidates) != 1:
        raise AssertionError(
            f"Expected one saved real-X Armature, found {[obj.name for obj in candidates]}"
        )
    return candidates[0]


def _line_projection(point, start, end):
    axis = Vector(end) - Vector(start)
    if axis.length <= limb_ik.EPSILON:
        raise AssertionError("Cannot project onto a zero-length limb axis")
    return Vector(start) + axis * (Vector(point) - Vector(start)).dot(axis) / axis.length_squared


def _reflect_about_axis(point, start, end):
    projection = _line_projection(point, start, end)
    return projection * 2.0 - Vector(point)


def _rest_residual_direction(armature, rig):
    upper = armature.data.bones[rig["chain"][0]]
    lower = armature.data.bones[rig["chain"][1]]
    start = Vector(upper.head_local)
    joint = Vector(lower.head_local)
    end = Vector(lower.tail_local)
    residual = joint - _line_projection(joint, start, end)
    if residual.length <= limb_ik.EPSILON:
        raise AssertionError(f"{rig['chain']} has no modeled Rest bend residual")
    return residual.normalized()


def _owned_ik_constraint(rig):
    return next(
        constraint
        for _pose_bone, constraint, record in rig["entries"]
        if record["role"] == "IK"
    )


def _identity_basis(pose_bone, label):
    error = _max_float_error(
        _matrix_tuple(pose_bone.matrix_basis),
        _matrix_tuple(Matrix.Identity(4)),
    )
    if error > FLOAT_TOLERANCE:
        raise AssertionError(f"{label} matrix_basis is not identity: {error}")


def _verify_saved_preconditions(armature, inventory):
    if inventory["schema"] != limb_ik.ENHANCED_SCHEMA or set(inventory["rigs"]) != EXPECTED_KEYS:
        raise AssertionError(
            f"Expected one complete enhanced four-limb rig, got schema={inventory['schema']} "
            f"keys={tuple(sorted(inventory['rigs']))}"
        )
    problems = limb_ik._foreign_dependency_problems(armature, inventory)
    if problems:
        raise AssertionError(f"Saved generated controls have relevant action/driver/dependency data: {problems[0]}")

    semantic = {}
    for key, rig in sorted(inventory["rigs"].items()):
        upper = armature.data.bones[rig["chain"][0]]
        lower = armature.data.bones[rig["chain"][1]]
        axis = Vector(lower.tail_local) - Vector(upper.head_local)
        pole = rig["pole"]
        if limb_ik.POLE_DIRECTION_KEY not in pole:
            raise AssertionError(f"Saved {key} Pole has no Pole Direction tag")
        saved = Vector(pole[limb_ik.POLE_DIRECTION_KEY])
        if abs(saved.length - 1.0) > 1.0e-5:
            raise AssertionError(f"Saved {key} Pole Direction is not normalized: {saved.length}")
        saved.normalize()
        expected = limb_ik._project_perpendicular(OLD_SEMANTIC_DIRECTIONS[key], axis)
        if expected.length <= limb_ik.EPSILON:
            raise AssertionError(f"Saved {key} old semantic direction is chain-parallel")
        expected.normalize()
        dot = saved.dot(expected)
        if dot <= 0.999999:
            raise AssertionError(f"Saved {key} Pole Direction is not the old semantic direction: {dot}")
        _identity_basis(armature.pose.bones[pole.name], f"{key} Pole")
        _identity_basis(armature.pose.bones[rig["target"].name], f"{key} Hand/Foot target")
        semantic[f"{key[0]}.{key[1]}"] = {
            "saved": _vector_tuple(saved),
            "expected": _vector_tuple(expected),
            "dot": dot,
        }
    return semantic


def _constraint_signature(armature):
    attributes = (
        "type",
        "name",
        "mute",
        "influence",
        "target",
        "subtarget",
        "pole_target",
        "pole_subtarget",
        "chain_count",
        "target_space",
        "owner_space",
        "mix_mode",
        "track_axis",
        "use_tail",
        "use_stretch",
        "use_limit_x",
        "min_x",
        "max_x",
    )
    result = {}
    for pose_bone in armature.pose.bones:
        for constraint in pose_bone.constraints:
            result[(pose_bone.name, constraint.name)] = tuple(
                (attribute, _freeze(getattr(constraint, attribute)))
                for attribute in attributes
                if hasattr(constraint, attribute) and attribute != "pole_angle"
            )
        result[(pose_bone.name, "__registry__")] = _freeze(
            pose_bone.get(limb_ik.CONSTRAINT_REGISTRY_KEY, None)
        )
    return result


def _widget_signature(armature_id):
    result = {}
    for obj in bpy.data.objects:
        if not limb_ik._owned(obj, armature_id, role="WIDGET"):
            continue
        result[obj.name] = {
            "data": obj.data.name,
            "matrix": _matrix_tuple(obj.matrix_world),
            "properties": _id_properties(obj),
            "data_properties": _id_properties(obj.data),
            "vertices": tuple(_vector_tuple(vertex.co) for vertex in obj.data.vertices),
            "edges": tuple(tuple(int(index) for index in edge.vertices) for edge in obj.data.edges),
            "collections": tuple(sorted(collection.name for collection in obj.users_collection)),
        }
    return result


def _bone_rest_signature(bone):
    return {
        "parent": bone.parent.name if bone.parent else "",
        "head": _vector_tuple(bone.head_local),
        "tail": _vector_tuple(bone.tail_local),
        "matrix": _matrix_tuple(bone.matrix_local),
        "use_deform": bool(bone.use_deform),
        "properties": _id_properties(bone),
    }


def _capture_state(armature, inventory):
    related = {
        name
        for rig in inventory["rigs"].values()
        for name in rig["chain"][:2]
    }
    source_names = [
        bone.name for bone in armature.data.bones if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    ]
    target_names = {
        rig["target"].name for rig in inventory["rigs"].values()
    } | {
        rig["solver_target"].name for rig in inventory["rigs"].values()
    }
    result = {
        "names": {
            "objects": tuple(sorted((obj.name, obj.type, getattr(obj.data, "name", "")) for obj in bpy.data.objects)),
            "meshes": tuple(sorted(mesh.name for mesh in bpy.data.meshes)),
            "collections": tuple(sorted(collection.name for collection in bpy.data.collections)),
            "bones": tuple(bone.name for bone in armature.data.bones),
        },
        "rig_ids": {key: rig["rig_id"] for key, rig in inventory["rigs"].items()},
        "constraints": _constraint_signature(armature),
        "pole_angles": {key: float(_owned_ik_constraint(rig).pole_angle) for key, rig in inventory["rigs"].items()},
        "widgets": _widget_signature(inventory["armature_id"]),
        "control_basis": {
            bone.name: (
                armature.pose.bones[bone.name].rotation_mode,
                _matrix_tuple(armature.pose.bones[bone.name].matrix_basis),
            )
            for bone in inventory["bones"]
        },
        "source_rest": {
            name: _bone_rest_signature(armature.data.bones[name]) for name in source_names
        },
        "nonrelated_pose": {
            name: armature.pose.bones[name].matrix.copy()
            for name in source_names
            if name not in related
        },
        "targets": {
            name: {
                "rest": _bone_rest_signature(armature.data.bones[name]),
                "pose": armature.pose.bones[name].matrix.copy(),
            }
            for name in sorted(target_names)
        },
        "ends": {
            key: armature.pose.bones[rig["chain"][2]].matrix.copy()
            for key, rig in inventory["rigs"].items()
        },
    }
    return result


def _assert_rest_signatures_equal(actual, expected, label):
    if set(actual) != set(expected):
        raise AssertionError(f"{label} changed bone names")
    for name, old in expected.items():
        new = actual[name]
        for field in ("parent", "use_deform", "properties"):
            if new[field] != old[field]:
                raise AssertionError(f"{label} changed '{name}' {field}")
        for field in ("head", "tail", "matrix"):
            error = _max_float_error(new[field], old[field])
            if error > FLOAT_TOLERANCE:
                raise AssertionError(f"{label} changed '{name}' {field}: {error}")


def _assert_common_invariants(before, after):
    for field in ("names", "rig_ids", "constraints", "widgets"):
        if after[field] != before[field]:
            raise AssertionError(f"Migration changed protected {field}")
    if set(after["control_basis"]) != set(before["control_basis"]):
        raise AssertionError("Migration changed the generated control inventory")
    for name, (old_mode, old_basis) in before["control_basis"].items():
        new_mode, new_basis = after["control_basis"][name]
        if new_mode != old_mode or _max_float_error(new_basis, old_basis) > FLOAT_TOLERANCE:
            raise AssertionError(f"Migration changed control matrix_basis on '{name}'")
    _assert_rest_signatures_equal(after["source_rest"], before["source_rest"], "Migration")
    _assert_rest_signatures_equal(
        {name: value["rest"] for name, value in after["targets"].items()},
        {name: value["rest"] for name, value in before["targets"].items()},
        "Migration target",
    )
    for name, old in before["targets"].items():
        errors = _matrix_errors(after["targets"][name]["pose"], old["pose"])
        if errors["position"] > END_POSITION_TOLERANCE or errors["rotation"] > END_ROTATION_TOLERANCE:
            raise AssertionError(f"Migration changed target '{name}' pose: {errors}")
    for name, old_matrix in before["nonrelated_pose"].items():
        errors = _matrix_errors(after["nonrelated_pose"][name], old_matrix)
        if errors["position"] > END_POSITION_TOLERANCE or errors["rotation"] > END_ROTATION_TOLERANCE:
            raise AssertionError(f"Migration changed unrelated source bone '{name}': {errors}")
    for key, old_matrix in before["ends"].items():
        errors = _matrix_errors(after["ends"][key], old_matrix)
        if errors["position"] > END_POSITION_TOLERANCE or errors["rotation"] > END_ROTATION_TOLERANCE:
            raise AssertionError(f"Migration changed Hand/Foot end {key}: {errors}")


def _plain_edit_plan(armature, key, rig, new_head, new_tail, new_direction):
    pole = rig["pole"]
    display = rig["display"]
    old_head = Vector(pole.head_local)
    delta = Vector(new_head) - old_head
    return {
        "key": key,
        "pole_name": pole.name,
        "display_name": display.name,
        "old_head": old_head,
        "old_tail": Vector(pole.tail_local),
        "new_head": Vector(new_head),
        "new_tail": Vector(new_tail),
        "old_display_head": Vector(display.head_local),
        "old_display_tail": Vector(display.tail_local),
        "new_display_head": Vector(display.head_local) + delta,
        "new_display_tail": Vector(display.tail_local) + delta,
        "old_direction": Vector(pole[limb_ik.POLE_DIRECTION_KEY]).normalized(),
        "new_direction": Vector(new_direction).normalized(),
        "axis_start": Vector(armature.data.bones[rig["chain"][0]].head_local),
        "axis_end": Vector(armature.data.bones[rig["chain"][1]].tail_local),
    }


def _reflection_edit_plans(armature, inventory):
    plans = []
    for key, rig in sorted(inventory["rigs"].items()):
        start = Vector(armature.data.bones[rig["chain"][0]].head_local)
        end = Vector(armature.data.bones[rig["chain"][1]].tail_local)
        pole = rig["pole"]
        plans.append(
            _plain_edit_plan(
                armature,
                key,
                rig,
                _reflect_about_axis(pole.head_local, start, end),
                _reflect_about_axis(pole.tail_local, start, end),
                -Vector(pole[limb_ik.POLE_DIRECTION_KEY]),
            )
        )
    return plans


def _modeled_rest_edit_plans(armature, inventory):
    plans = []
    for key, rig in sorted(inventory["rigs"].items()):
        upper = armature.data.bones[rig["chain"][0]]
        lower = armature.data.bones[rig["chain"][1]]
        start = Vector(upper.head_local)
        joint = Vector(lower.head_local)
        end = Vector(lower.tail_local)
        old_direction = Vector(rig["pole"][limb_ik.POLE_DIRECTION_KEY]).normalized()
        old_joint = limb_ik._joint_on_direction_plane(start, joint, end, old_direction)
        pole_distance = (Vector(rig["pole"].head_local) - old_joint).length
        modeled = _rest_residual_direction(armature, rig)
        new_head = joint + modeled * pole_distance
        delta = new_head - Vector(rig["pole"].head_local)
        plans.append(
            _plain_edit_plan(
                armature,
                key,
                rig,
                new_head,
                Vector(rig["pole"].tail_local) + delta,
                modeled,
            )
        )
    return plans


def _apply_rest_level_pole_edits(context, armature, plans):
    """Apply preflighted Pole/Aim rest edits atomically in the current process.

    This is the reusable migration primitive: callers provide all four plans;
    each plan has old/new Pole coordinates, an Aim-child translation, and the
    normalized replacement direction tag.  No constraints, widgets, IDs, or
    pose bases are recreated.
    """
    if {plan["key"] for plan in plans} != EXPECTED_KEYS:
        raise AssertionError("Pole migration requires all four owned limb plans")
    original_mode = armature.mode
    mirror_x = bool(armature.data.use_mirror_x)
    committed = False
    try:
        _mode_set(context, armature, "OBJECT")
        armature.data.use_mirror_x = False
        _mode_set(context, armature, "EDIT")
        for plan in plans:
            pole = armature.data.edit_bones.get(plan["pole_name"])
            display = armature.data.edit_bones.get(plan["display_name"])
            if (
                pole is None
                or display is None
                or display.parent is None
                or display.parent.name != pole.name
            ):
                raise AssertionError(f"Owned Pole/Aim hierarchy is invalid for {plan['key']}")
            pole.head = plan["new_head"]
            pole.tail = plan["new_tail"]
            display.head = plan["new_display_head"]
            display.tail = plan["new_display_tail"]
        _mode_set(context, armature, "OBJECT")
        for plan in plans:
            armature.data.bones[plan["pole_name"]][limb_ik.POLE_DIRECTION_KEY] = [
                float(component) for component in plan["new_direction"]
            ]
        committed = True
    except Exception:
        try:
            _mode_set(context, armature, "EDIT")
            for plan in plans:
                pole = armature.data.edit_bones.get(plan["pole_name"])
                display = armature.data.edit_bones.get(plan["display_name"])
                if pole is not None:
                    pole.head = plan["old_head"]
                    pole.tail = plan["old_tail"]
                if display is not None:
                    display.head = plan["old_display_head"]
                    display.tail = plan["old_display_tail"]
            _mode_set(context, armature, "OBJECT")
            for plan in plans:
                armature.data.bones[plan["pole_name"]][limb_ik.POLE_DIRECTION_KEY] = [
                    float(component) for component in plan["old_direction"]
                ]
        finally:
            armature.data.use_mirror_x = mirror_x
        raise
    finally:
        if armature.mode == "EDIT":
            _mode_set(context, armature, "OBJECT")
        armature.data.use_mirror_x = mirror_x
        if committed:
            armature.data.update_tag()
            armature.update_tag(refresh={"OBJECT"})
            context.scene.update_tag()
            context.view_layer.update()
            context.evaluated_depsgraph_get().update()
        if original_mode == "POSE":
            _mode_set(context, armature, "POSE")
        elif original_mode == "EDIT":
            _mode_set(context, armature, "EDIT")
        else:
            _mode_set(context, armature, "OBJECT")
        context.view_layer.update()


def reflect_owned_poles_rest_level(context, armature, inventory=None):
    """Reusable Strategy A: reflect Pole head/tail about each source chain axis."""
    inventory = inventory or limb_ik._validate_inventory(armature)
    plans = _reflection_edit_plans(armature, inventory)
    _apply_rest_level_pole_edits(context, armature, plans)
    return plans


def place_owned_poles_on_modeled_rest_bend(context, armature, inventory=None):
    """Reusable Strategy B: place each Pole on its modeled Rest bend residual."""
    inventory = inventory or limb_ik._validate_inventory(armature)
    plans = _modeled_rest_edit_plans(armature, inventory)
    _apply_rest_level_pole_edits(context, armature, plans)
    return plans


def _bend_alignment(armature, rig):
    upper = armature.pose.bones[rig["chain"][0]]
    lower = armature.pose.bones[rig["chain"][1]]
    pole = armature.pose.bones[rig["pole"].name]
    start = Vector(upper.head)
    joint = Vector(lower.head)
    end = Vector(lower.tail)
    projection = _line_projection(joint, start, end)
    bend = joint - projection
    pole_projection = limb_ik._project_perpendicular(Vector(pole.head) - projection, end - start)
    if min(bend.length, pole_projection.length) <= limb_ik.EPSILON:
        return None, bend, pole_projection
    return bend.normalized().dot(pole_projection.normalized()), bend, pole_projection


def _local_y_twist_degrees(pose_matrix, rest_matrix):
    relative = rest_matrix.to_quaternion().inverted() @ pose_matrix.to_quaternion()
    twist = Quaternion((relative.w, 0.0, relative.y, 0.0))
    if twist.magnitude <= limb_ik.EPSILON:
        return 0.0
    twist.normalize()
    angle = math.remainder(2.0 * math.atan2(twist.y, twist.w), math.tau)
    return math.degrees(angle)


def _limb_pose_metrics(armature, inventory):
    result = {}
    for key, rig in sorted(inventory["rigs"].items()):
        upper_name, lower_name, _end_name = rig["chain"]
        upper = armature.pose.bones[upper_name]
        lower = armature.pose.bones[lower_name]
        upper_rest = armature.data.bones[upper_name].matrix_local
        lower_rest = armature.data.bones[lower_name].matrix_local
        alignment, bend, pole_projection = _bend_alignment(armature, rig)
        result[f"{key[0]}.{key[1]}"] = {
            "alignment_dot": alignment,
            "bend": _vector_tuple(bend),
            "bend_y": float(bend.y),
            "pole_projection": _vector_tuple(pole_projection),
            "joint_rest_error": (Vector(lower.head) - Vector(armature.data.bones[lower_name].head_local)).length,
            "upper_rotation_error_degrees": math.degrees(_rotation_error(upper.matrix, upper_rest)),
            "lower_rotation_error_degrees": math.degrees(_rotation_error(lower.matrix, lower_rest)),
            "upper_local_y_twist_degrees": _local_y_twist_degrees(upper.matrix, upper_rest),
            "lower_local_y_twist_degrees": _local_y_twist_degrees(lower.matrix, lower_rest),
            "pole_angle": float(_owned_ik_constraint(rig).pole_angle),
        }
    return result


def _rest_objective(armature, rig):
    upper_name, lower_name, _end_name = rig["chain"]
    upper = armature.pose.bones[upper_name]
    lower = armature.pose.bones[lower_name]
    upper_rest = armature.data.bones[upper_name].matrix_local
    lower_rest = armature.data.bones[lower_name].matrix_local
    total = upper.length + lower.length
    alignment, _bend, _pole_projection = _bend_alignment(armature, rig)
    if total <= limb_ik.EPSILON or alignment is None:
        return float("inf")
    joint_error = (Vector(lower.head) - Vector(armature.data.bones[lower_name].head_local)).length / total
    upper_error = _rotation_error(upper.matrix, upper_rest)
    lower_error = _rotation_error(lower.matrix, lower_rest)
    alignment_error = max(0.0, 1.0 - alignment)
    return upper_error * upper_error + lower_error * lower_error + 100.0 * joint_error * joint_error + 10.0 * alignment_error * alignment_error


def choose_rest_preserving_pole_angles(context, armature, inventory=None):
    """Reusable bounded search for Pole Angles that recover modeled Rest pose."""
    inventory = inventory or limb_ik._validate_inventory(armature)
    _mode_set(context, armature, "POSE")
    chosen = {}
    for key, rig in sorted(inventory["rigs"].items()):
        constraint = _owned_ik_constraint(rig)
        old_angle = float(constraint.pole_angle)
        lower, upper = limb_ik._pole_angle_domain(constraint)
        samples = 128
        step = (upper - lower) / samples

        def evaluate(angle):
            requested = max(lower, min(upper, float(angle)))
            constraint.pole_angle = requested
            context.view_layer.update()
            return float(constraint.pole_angle), _rest_objective(armature, rig)

        best_angle = old_angle
        best_score = float("inf")
        for index in range(samples + 1):
            actual, score = evaluate(lower + index * step)
            if score < best_score:
                best_angle, best_score = actual, score
        if not math.isfinite(best_score):
            raise AssertionError(f"No finite Rest-preserving Pole Angle exists for {key}")

        left = max(lower, best_angle - step)
        right = min(upper, best_angle + step)
        golden = (math.sqrt(5.0) - 1.0) * 0.5
        x1 = right - golden * (right - left)
        x2 = left + golden * (right - left)
        a1, f1 = evaluate(x1)
        a2, f2 = evaluate(x2)
        for _index in range(30):
            if f1 <= f2:
                right, x2, a2, f2 = x2, x1, a1, f1
                x1 = right - golden * (right - left)
                a1, f1 = evaluate(x1)
            else:
                left, x1, a1, f1 = x1, x2, a2, f2
                x2 = left + golden * (right - left)
                a2, f2 = evaluate(x2)
        for actual, score in ((a1, f1), (a2, f2)):
            if score < best_score:
                best_angle, best_score = actual, score
        constraint.pole_angle = best_angle
        context.view_layer.update()
        chosen[f"{key[0]}.{key[1]}"] = {
            "old": old_angle,
            "new": float(constraint.pole_angle),
            "objective": best_score,
        }
    return chosen


def _verify_plan_geometry(armature, plans, strategy):
    result = {}
    for plan in plans:
        pole = armature.data.bones[plan["pole_name"]]
        display = armature.data.bones[plan["display_name"]]
        actual_head = Vector(pole.head_local)
        actual_tail = Vector(pole.tail_local)
        actual_direction = Vector(pole[limb_ik.POLE_DIRECTION_KEY]).normalized()
        if (actual_head - plan["new_head"]).length > FLOAT_TOLERANCE or (actual_tail - plan["new_tail"]).length > FLOAT_TOLERANCE:
            raise AssertionError(f"{strategy} did not write exact Pole rest coordinates for {plan['key']}")
        if (
            (Vector(display.head_local) - plan["new_display_head"]).length > FLOAT_TOLERANCE
            or (Vector(display.tail_local) - plan["new_display_tail"]).length > FLOAT_TOLERANCE
        ):
            raise AssertionError(f"{strategy} did not translate the Aim child with its Pole for {plan['key']}")
        if actual_direction.dot(plan["new_direction"]) <= 0.999999:
            raise AssertionError(f"{strategy} wrote the wrong direction tag for {plan['key']}")

        old_side = Vector(plan["old_head"]) - _line_projection(
            plan["old_head"], plan["axis_start"], plan["axis_end"]
        )
        new_side = actual_head - _line_projection(actual_head, plan["axis_start"], plan["axis_end"])
        result[f"{plan['key'][0]}.{plan['key'][1]}"] = {
            "old_head_y": float(plan["old_head"].y),
            "new_head_y": float(actual_head.y),
            "old_axis_side": _vector_tuple(old_side),
            "new_axis_side": _vector_tuple(new_side),
            "old_to_new_direction_dot": plan["old_direction"].dot(actual_direction),
        }
        if strategy == "reflection":
            if (new_side + old_side).length > 2.0e-6 or old_side.y * new_side.y >= 0.0:
                raise AssertionError(f"Reflected {plan['key']} Pole did not move to the opposite axis-Y side")
            if actual_direction.dot(-plan["old_direction"]) <= 0.999999:
                raise AssertionError(f"Reflected {plan['key']} direction tag was not negated")
    return result


def _verify_reflection_result(metrics):
    for label, item in metrics.items():
        if item["alignment_dot"] is None or item["alignment_dot"] <= ALIGNMENT_MIN:
            raise AssertionError(f"Reflection {label} bend/Pole alignment is {item['alignment_dot']}")
        kind = label.split(".")[0]
        if kind == "ARM" and item["bend_y"] >= 0.0:
            raise AssertionError(f"Reflection {label} Arm bend did not move to -Y")
        if kind == "LEG" and item["bend_y"] <= 0.0:
            raise AssertionError(f"Reflection {label} Leg bend did not move to +Y")


def _verify_modeled_result(armature, inventory, metrics):
    for key, rig in sorted(inventory["rigs"].items()):
        label = f"{key[0]}.{key[1]}"
        item = metrics[label]
        modeled = _rest_residual_direction(armature, rig)
        saved = Vector(rig["pole"][limb_ik.POLE_DIRECTION_KEY]).normalized()
        if saved.dot(modeled) <= 0.999999:
            raise AssertionError(f"Modeled strategy {label} tag does not match Rest residual")
        if item["alignment_dot"] is None or item["alignment_dot"] <= ALIGNMENT_MIN:
            raise AssertionError(f"Modeled strategy {label} bend/Pole alignment is {item['alignment_dot']}")
        if item["joint_rest_error"] > 5.0e-5:
            raise AssertionError(f"Modeled strategy {label} joint did not return to Rest: {item['joint_rest_error']}")
        if max(item["upper_rotation_error_degrees"], item["lower_rotation_error_degrees"]) > 0.05:
            raise AssertionError(f"Modeled strategy {label} source rotations did not return to Rest: {item}")
        if key[0] == "LEG" and max(
            abs(item["upper_local_y_twist_degrees"]),
            abs(item["lower_local_y_twist_degrees"]),
        ) > 0.05:
            raise AssertionError(f"Modeled strategy {label} local-Y twist did not return near zero: {item}")


def _open_input(path):
    result = bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    if result != {"FINISHED"}:
        raise AssertionError(f"Could not open migration input: {result}")


def _run_strategy(path, strategy):
    _open_input(path)
    armature = _find_real_armature()
    _mode_set(bpy.context, armature, "POSE")
    inventory = limb_ik._validate_inventory(armature)
    old_semantic = _verify_saved_preconditions(armature, inventory)
    before = _capture_state(armature, inventory)
    baseline_metrics = _limb_pose_metrics(armature, inventory)

    if strategy == "reflection":
        plans = reflect_owned_poles_rest_level(bpy.context, armature, inventory)
        angle_changes = {
            f"{key[0]}.{key[1]}": {"old": angle, "new": angle}
            for key, angle in before["pole_angles"].items()
        }
    elif strategy == "modeled_rest":
        plans = place_owned_poles_on_modeled_rest_bend(bpy.context, armature, inventory)
        inventory = limb_ik._validate_inventory(armature)
        angle_changes = choose_rest_preserving_pole_angles(bpy.context, armature, inventory)
    else:
        raise AssertionError(f"Unknown migration strategy: {strategy}")

    _mode_set(bpy.context, armature, "POSE")
    bpy.context.view_layer.update()
    migrated = limb_ik._validate_inventory(armature)
    after = _capture_state(armature, migrated)
    _assert_common_invariants(before, after)
    if strategy == "reflection":
        for key, old_angle in before["pole_angles"].items():
            if abs(after["pole_angles"][key] - old_angle) > 1.0e-9:
                raise AssertionError(f"Reflection changed the saved IK Pole Angle for {key}")
    geometry = _verify_plan_geometry(armature, plans, strategy)
    metrics = _limb_pose_metrics(armature, migrated)
    if strategy == "reflection":
        _verify_reflection_result(metrics)
    else:
        _verify_modeled_result(armature, migrated, metrics)
    return {
        "old_semantic_directions": old_semantic,
        "baseline_pose": baseline_metrics,
        "geometry": geometry,
        "pole_angles": angle_changes,
        "final_pose": metrics,
        "armature": armature.name,
        "armature_data": armature.data.name,
        "rig_ids": {f"{key[0]}.{key[1]}": value for key, value in before["rig_ids"].items()},
    }


def _arguments():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("Expected exactly one argument after --: the source .blend path")
    path = Path(args[0]).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".blend":
        raise SystemExit(f"Migration input is not a .blend file: {path}")
    return path


def main():
    path = _arguments()
    fingerprint_before = _file_fingerprint(path)
    reflection = _run_strategy(path, "reflection")
    if _file_fingerprint(path) != fingerprint_before:
        raise AssertionError("Input .blend changed during the reflection experiment")
    modeled = _run_strategy(path, "modeled_rest")
    fingerprint_after = _file_fingerprint(path)
    if fingerprint_after != fingerprint_before:
        raise AssertionError("Input .blend hash/mtime/size changed; migration experiment must never save")

    reflection_leg_twist = max(
        abs(value[field])
        for label, value in reflection["final_pose"].items()
        if label.startswith("LEG.")
        for field in ("upper_local_y_twist_degrees", "lower_local_y_twist_degrees")
    )
    modeled_leg_twist = max(
        abs(value[field])
        for label, value in modeled["final_pose"].items()
        if label.startswith("LEG.")
        for field in ("upper_local_y_twist_degrees", "lower_local_y_twist_degrees")
    )
    if modeled_leg_twist >= reflection_leg_twist:
        raise AssertionError(
            f"Modeled-Rest strategy did not improve Leg twist: reflection={reflection_leg_twist}, "
            f"modeled={modeled_leg_twist}"
        )
    payload = {
        "input": str(path),
        "fingerprint_before": fingerprint_before,
        "fingerprint_after": fingerprint_after,
        "reflection": reflection,
        "modeled_rest": modeled,
        "comparison": {
            "reflection_max_leg_local_y_twist_degrees": reflection_leg_twist,
            "modeled_rest_max_leg_local_y_twist_degrees": modeled_leg_twist,
            "recommended": "modeled_rest_direction_plus_bounded_pole_angle_search",
        },
    }
    print("REAL_X_POLE_DIRECTION_MIGRATION_JSON=" + json.dumps(payload, sort_keys=True))
    print("PASS real-X Pole Direction migration strategies (read-only input)")


if __name__ == "__main__":
    main()
