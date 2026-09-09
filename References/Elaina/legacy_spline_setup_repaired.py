"""Recovered three-control FK / Spline IK setup, independent of any add-on.

Select one straight, connected chain of at least two bones in Pose or Edit
Mode, then run this file. The original FK bones, weights and other rig data
are retained. Select that chain or its new controls and call remove_selected()
to remove only this setup. Repeating build_selected() selects existing controls.

This recovery intentionally accepts neutral, unanimated FK source bones only.
Animation on their parent or elsewhere on the armature is supported. A curved
rest chain or a pose containing inherited shear/reflection cannot be reproduced
exactly by the old three-point design and is refused before mutation. The local control bones are translation controls;
this script supplies neither a twist system nor a physics/cache baker.
"""

import json
import math
import uuid

import bpy
from mathutils import Matrix, Vector


REGISTRY = "elaina_recovered_spline_v1"
OWNER = "elaina_recovered_spline_owner"
RIG_REF = "elaina_recovered_spline_armature"
ROLE = "elaina_recovered_spline_role"


class RecoveryError(ValueError):
    """An actionable validation error; existing artist data is not discarded."""


def _checkpoint(_stage):
    """An intentionally empty integration-test failure injection point."""


def _records(rig):
    try:
        records = json.loads(rig.get(REGISTRY, "{}"))
        if not isinstance(records, dict):
            raise ValueError()
        for owner, record in records.items():
            if (not isinstance(owner, str) or not isinstance(record, dict)
                    or record.get("owner") != owner
                    or any(not isinstance(record.get(key), list)
                           for key in ("source", "mechanism", "controls", "constraints", "collections"))):
                raise ValueError()
        return records
    except (TypeError, ValueError) as error:
        raise RecoveryError("The recovered spline ownership record is invalid; restore it before continuing.") from error


def _write_records(rig, records):
    if records:
        rig[REGISTRY] = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    elif REGISTRY in rig:
        del rig[REGISTRY]


def _selection(context):
    rig = context.object
    if rig is None or rig.type != "ARMATURE" or context.mode not in {"POSE", "EDIT_ARMATURE"}:
        raise RecoveryError("Select a bone chain on one armature in Pose or Edit Mode.")
    bones = rig.data.edit_bones if rig.mode == "EDIT" else rig.pose.bones
    names = {bone.name for bone in bones if bone.select}
    if not names:
        raise RecoveryError("Select a source chain or its recovered controls.")
    if rig.library or rig.override_library or rig.data.library or rig.data.users != 1:
        raise RecoveryError("The armature must be local with single-user armature data.")
    memberships = [scene for scene in bpy.data.scenes if scene.objects.get(rig.name) is rig]
    if memberships != [context.scene]:
        raise RecoveryError("The armature must belong only to the current scene.")
    if context.view_layer.objects.get(rig.name) is not rig:
        raise RecoveryError("The armature is excluded from the current view layer.")
    if not all(math.isfinite(x) for row in rig.matrix_world for x in row) or abs(rig.matrix_world.determinant()) < 1e-12:
        raise RecoveryError("The armature needs a finite, nonzero object scale.")
    return rig, names


def _ordered_chain(rig, names):
    bones = rig.data.edit_bones if rig.mode == "EDIT" else rig.data.bones
    roots = [bones[name] for name in names if not bones[name].parent or bones[name].parent.name not in names]
    if len(names) < 2 or len(roots) != 1:
        raise RecoveryError("Select at least two bones in one continuous parent-child chain.")
    ordered, current = [], roots[0]
    while current is not None:
        ordered.append(current.name)
        children = [child for child in current.children if child.name in names]
        if len(children) > 1:
            raise RecoveryError("The selected chain branches; select one path.")
        current = children[0] if children else None
    if len(ordered) != len(names):
        raise RecoveryError("The selected bones contain a gap or disconnected branch.")
    return ordered


def _action_curves(action):
    if action is None:
        return
    # Blender 4.4+ layered actions and pre-layered actions are both accepted.
    for curve in getattr(action, "fcurves", ()):
        yield curve
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                yield from bag.fcurves


def _animation_paths(rig):
    animation = rig.animation_data
    if animation is None:
        return set()
    paths = {curve.data_path for curve in animation.drivers}
    actions = [animation.action]

    def visit(strips):
        for strip in strips:
            actions.append(getattr(strip, "action", None))
            visit(getattr(strip, "strips", ()))

    for track in animation.nla_tracks:
        visit(track.strips)
    for action in actions:
        paths.update(curve.data_path for curve in _action_curves(action))
    return paths


def _animated_bones(rig, names):
    prefixes = tuple(rig.pose.bones[name].path_from_id() + suffix for name in names for suffix in (".", "["))
    return any(path.startswith(prefixes) for path in _animation_paths(rig))


def _driver_dependency(rig, curve, names):
    pose_prefixes = tuple(rig.pose.bones[name].path_from_id() + suffix for name in names for suffix in (".", "["))
    rest_prefixes = tuple(rig.data.bones[name].path_from_id() + suffix for name in names for suffix in (".", "["))
    seen = set()
    for domain in (bpy.data.objects, bpy.data.scenes, bpy.data.armatures, bpy.data.curves,
                   bpy.data.meshes, bpy.data.shape_keys, bpy.data.materials, bpy.data.node_groups,
                   bpy.data.worlds, bpy.data.lights, bpy.data.cameras):
        for owner in domain:
            # Embedded material/world/light/compositor trees are not members
            # of bpy.data.node_groups, but their sockets may have rig drivers.
            for container in (owner, getattr(owner, "node_tree", None)):
                if container is None or container.as_pointer() in seen:
                    continue
                seen.add(container.as_pointer())
                animation = getattr(container, "animation_data", None)
                if animation is None:
                    continue
                for fcurve in animation.drivers:
                    for variable in fcurve.driver.variables:
                        for target in variable.targets:
                            if target.id is curve or target.id is curve.data:
                                return True
                            if target.id is rig and (target.bone_target in names or target.data_path.startswith(pose_prefixes)):
                                return True
                            if target.id is rig.data and target.data_path.startswith(rest_prefixes):
                                return True
    return False


def _snapshot(context, rig):
    return {
        "mode": rig.mode,
        "objects": [obj for obj in context.view_layer.objects if obj.select_get()],
        "active": context.view_layer.objects.active,
        "bones": [(bone.name, bone.select, getattr(bone, "select_head", False), getattr(bone, "select_tail", False))
                  for bone in (rig.data.edit_bones if rig.mode == "EDIT" else rig.pose.bones)],
        "active_bone": (rig.data.edit_bones.active if rig.mode == "EDIT" else rig.data.bones.active).name
                       if (rig.data.edit_bones.active if rig.mode == "EDIT" else rig.data.bones.active) else None,
    }


def _mode(context, rig, mode):
    current = context.view_layer.objects.active
    if current is not rig and current and current.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    context.view_layer.objects.active = rig
    rig.select_set(True)
    if rig.mode != mode:
        bpy.ops.object.mode_set(mode=mode)


def _restore(context, rig, snapshot):
    _mode(context, rig, snapshot["mode"])
    bones = rig.data.edit_bones if rig.mode == "EDIT" else rig.pose.bones
    for name, selected, head, tail in snapshot["bones"]:
        bone = bones.get(name)
        if bone:
            bone.select = selected
            if rig.mode == "EDIT":
                bone.select_head, bone.select_tail = head, tail
    active_bones = rig.data.edit_bones if rig.mode == "EDIT" else rig.data.bones
    active_bones.active = active_bones.get(snapshot["active_bone"]) if snapshot["active_bone"] else None
    for obj in context.view_layer.objects:
        obj.select_set(obj in snapshot["objects"])
    context.view_layer.objects.active = snapshot["active"]
    context.view_layer.update()


def _select_controls(context, rig, record, mode):
    _mode(context, rig, mode)
    bones = rig.data.edit_bones if rig.mode == "EDIT" else rig.pose.bones
    for bone in bones:
        selected = bone.name in record["controls"]
        bone.select = selected
        if rig.mode == "EDIT":
            bone.select_head = bone.select_tail = selected
    active_bones = rig.data.edit_bones if rig.mode == "EDIT" else rig.data.bones
    active_bones.active = active_bones[record["controls"][1]]
    for collection in rig.data.collections:
        if collection.get(OWNER) == record["owner"] and collection.get(ROLE) == "CONTROLS":
            collection.is_visible = True
    context.view_layer.update()


def _curve_for(rig, owner):
    objects = [obj for obj in bpy.data.objects if obj.get(OWNER) == owner and obj.get(RIG_REF) is rig]
    if len(objects) != 1 or objects[0].type != "CURVE":
        raise RecoveryError("The recovered curve is missing or ambiguous; restore it before continuing.")
    return objects[0]


def _inventory(rig, record, for_removal=False):
    owner = record["owner"]
    generated = record["mechanism"] + record["controls"]
    for name in generated:
        bone = rig.data.bones.get(name)
        if bone is None or bone.get(OWNER) != owner:
            raise RecoveryError("A generated bone was renamed or removed; restore it before continuing.")
    curve = _curve_for(rig, owner)
    if curve.data.get(OWNER) != owner or curve.parent is not rig or curve.data.users != 1:
        raise RecoveryError("The recovered curve ownership or parent changed.")
    if len(curve.modifiers) != 3:
        raise RecoveryError("The recovered curve's Hook stack changed.")
    for index, modifier in enumerate(curve.modifiers):
        if (modifier.type != "HOOK" or modifier.object is not rig
                or modifier.subtarget != record["controls"][index]
                or tuple(modifier.vertex_indices) != (index,)):
            raise RecoveryError("The recovered curve's Hook binding changed.")
    owned_constraints = []
    for source, mechanism, name in zip(record["source"], record["mechanism"], record["constraints"]):
        pose = rig.pose.bones.get(source)
        constraint = pose.constraints.get(name) if pose else None
        if (constraint is None or constraint.type != "COPY_TRANSFORMS" or constraint.target is not rig
                or constraint.subtarget != mechanism or constraint.owner_space != "LOCAL"
                or constraint.target_space != "LOCAL" or constraint.mix_mode != "BEFORE"):
            raise RecoveryError("The recovered FK link changed; restore it before removal.")
        owned_constraints.append(constraint)
    tip = rig.pose.bones[record["mechanism"][-1]]
    spline = tip.constraints.get(record["spline_constraint"])
    if spline is None or spline.type != "SPLINE_IK" or spline.target is not curve:
        raise RecoveryError("The recovered Spline IK target changed.")
    owned_constraints.append(spline)
    if for_removal:
        if _animated_bones(rig, generated) or curve.animation_data or curve.data.animation_data:
            raise RecoveryError("Generated controls or curve are animated; keep or export that animation before removal.")
        if _driver_dependency(rig, curve, generated):
            raise RecoveryError("An artist driver depends on generated bones or curve data.")
        if any(bone.parent and bone.parent.name in generated and bone.name not in generated for bone in rig.data.bones):
            raise RecoveryError("Artist bones are parented to generated controls; reparent them before removal.")
        for obj in bpy.data.objects:
            if obj.parent is curve:
                raise RecoveryError("An artist object is parented to the generated curve.")
            if obj.parent is rig and obj.parent_type == "BONE" and obj.parent_bone in generated:
                raise RecoveryError("An artist object is parented to a generated bone.")
            for pose in obj.pose.bones if obj.type == "ARMATURE" else ():
                for constraint in pose.constraints:
                    if constraint in owned_constraints:
                        continue
                    if (obj is rig and pose.name in generated) or (getattr(constraint, "target", None) is rig
                            and getattr(constraint, "subtarget", "") in generated) or getattr(constraint, "target", None) is curve:
                        raise RecoveryError("An artist constraint depends on generated data.")
            for constraint in obj.constraints:
                if ((getattr(constraint, "target", None) is rig and getattr(constraint, "subtarget", "") in generated)
                        or getattr(constraint, "target", None) is curve):
                    raise RecoveryError("An artist object constraint depends on generated data.")
            for modifier in obj.modifiers:
                if obj is curve:
                    continue
                if getattr(modifier, "object", None) is curve:
                    raise RecoveryError("An artist modifier depends on the generated curve.")
                if getattr(modifier, "object", None) is rig and (
                        getattr(modifier, "subtarget", "") in generated
                        or (modifier.type == "ARMATURE" and any(name in obj.vertex_groups for name in generated))):
                    raise RecoveryError("Artist modifiers or weights depend on generated bones.")
        for bone in rig.data.bones:
            if bone.get(OWNER) == owner and bone.name not in generated:
                raise RecoveryError("Unexpected owned bone; removal was refused.")
        for collection in rig.data.collections:
            if collection.get(OWNER) == owner and any(bone.name not in generated for bone in collection.bones):
                raise RecoveryError("An artist bone was added to a generated collection.")
    return curve


def _matching(rig, names, records):
    matches = []
    for record in records.values():
        own = set(record["mechanism"] + record["controls"])
        source = set(record["source"])
        if names == source or names <= own:
            matches.append(record)
        elif names & (source | own):
            raise RecoveryError("The selection overlaps an existing recovered chain; select that whole chain or its controls.")
    if len(matches) > 1:
        raise RecoveryError("The selection refers to more than one recovered setup.")
    return matches[0] if matches else None


def _delete_generated(context, rig, record, curve=None):
    _mode(context, rig, "POSE")
    for source, name in zip(record["source"], record["constraints"]):
        pose = rig.pose.bones.get(source)
        if pose and (constraint := pose.constraints.get(name)):
            pose.constraints.remove(constraint)
    if curve is not None and bpy.data.objects.get(curve.name) is curve:
        data = curve.data
        bpy.data.objects.remove(curve, do_unlink=True)
        if data.users == 0:
            bpy.data.curves.remove(data)
    _mode(context, rig, "EDIT")
    for name in reversed(record["mechanism"] + record["controls"]):
        bone = rig.data.edit_bones.get(name)
        if bone is not None and bone.get(OWNER) == record["owner"]:
            rig.data.edit_bones.remove(bone)
    _mode(context, rig, "POSE")
    for collection in list(rig.data.collections):
        if collection.get(OWNER) == record["owner"] and not collection.bones and not collection.children:
            rig.data.collections.remove(collection)


def build_selected(context=bpy.context):
    """Build one recovered straight chain, or reveal its previously built controls."""
    rig, names = _selection(context)
    records = _records(rig)
    snapshot = _snapshot(context, rig)
    existing = _matching(rig, names, records)
    if existing:
        _mode(context, rig, "POSE")
        try:
            _inventory(rig, existing)
            _select_controls(context, rig, existing, snapshot["mode"])
            return existing
        except Exception:
            _restore(context, rig, snapshot)
            raise
    ordered = _ordered_chain(rig, names)
    # Commit Edit Mode changes before reading explicit rest matrices.
    _mode(context, rig, "POSE")
    record = {"owner": uuid.uuid4().hex, "source": ordered, "mechanism": [],
              "controls": [], "constraints": [], "collections": [], "spline_constraint": ""}
    curve = curve_data = None
    try:
        bones = [rig.data.bones[name] for name in ordered]
        head, tail = bones[0].head_local.copy(), bones[-1].tail_local.copy()
        line = tail - head
        length = sum(bone.length for bone in bones)
        tolerance = max(length * 1e-6, 1e-7)
        if length < 1e-6 or line.length < 1e-6:
            raise RecoveryError("The selected chain has no usable length.")
        direction = line.normalized()
        if any((a.tail_local - b.head_local).length > tolerance for a, b in zip(bones, bones[1:])):
            raise RecoveryError("The source chain has separated joints; select a connected chain.")
        if abs(line.length - length) > tolerance or any(
                (point - head - direction * (point - head).dot(direction)).length > tolerance
                for bone in bones for point in (bone.head_local, bone.tail_local)):
            raise RecoveryError("The old three-point setup cannot reproduce this curved rest chain exactly; use a straight chain.")
        if _animated_bones(rig, ordered):
            raise RecoveryError("A selected FK bone is animated or driven; use an unanimated copy for this recovery.")
        for name in ordered:
            pose = rig.pose.bones[name]
            if (pose.constraints or max(abs(value) for value in pose.location) > 1e-7
                    or max(abs(pose.matrix_basis[i][j] - float(i == j)) for i in range(4) for j in range(4)) > 1e-7):
                raise RecoveryError("Selected FK bones must have neutral local poses and no existing constraints; parent animation is supported.")
        rest = [{"name": bone.name, "matrix": bone.matrix_local.copy(), "length": bone.length,
                 "parent": bone.parent.name if bone.parent else None, "connected": bone.use_connect,
                 "inherit_scale": bone.inherit_scale, "inherit_rotation": bone.use_inherit_rotation,
                 "local_location": bone.use_local_location} for bone in bones]
        context.view_layer.update()
        evaluated = rig.evaluated_get(context.evaluated_depsgraph_get())
        baseline = {name: evaluated.pose.bones[name].matrix.copy() for name in ordered}
        for matrix in baseline.values():
            axes = [matrix.col[index].xyz for index in range(3)]
            if (matrix.determinant() <= 1e-12 or any(axis.length < 1e-8 for axis in axes)
                    or any(abs(axes[a].normalized().dot(axes[b].normalized())) > 1e-5
                           for a, b in ((0, 1), (0, 2), (1, 2)))):
                raise RecoveryError("The source pose is sheared or reflected by its parents; use a copy without inherited shear for this recovery.")
        prefix = "Recovered_" + record["owner"][:8]
        _mode(context, rig, "EDIT")
        mapping = {}
        for source in rest:
            bone = rig.data.edit_bones.new(prefix + "_SPIK_" + source["name"])
            record["mechanism"].append(bone.name)
            bone[OWNER], bone[ROLE] = record["owner"], "MECHANISM"
            # A brand-new EditBone has zero length; setting its matrix first
            # loses the intended axis when Blender later assigns its length.
            bone.head = source["matrix"].translation
            bone.tail = source["matrix"] @ Vector((0.0, source["length"], 0.0))
            bone.align_roll(source["matrix"].col[2].xyz)
            bone.use_deform = False
            bone.inherit_scale, bone.use_inherit_rotation = source["inherit_scale"], source["inherit_rotation"]
            bone.use_local_location = source["local_location"]
            if source["parent"]:
                bone.parent = rig.data.edit_bones[mapping.get(source["parent"], source["parent"])]
                bone.use_connect = source["connected"]
            mapping[source["name"]] = bone.name
        for index, t in enumerate((0.0, 0.5, 1.0)):
            bone = rig.data.edit_bones.new(f"{prefix}_CTRL_{index + 1:02d}")
            record["controls"].append(bone.name)
            bone[OWNER], bone[ROLE] = record["owner"], "CONTROL"
            bone.head = head.lerp(tail, t)
            bone.tail = bone.head + direction * (length * 0.08)
            bone.use_deform = False
            if rest[0]["parent"]:
                bone.parent = rig.data.edit_bones[rest[0]["parent"]]
        _mode(context, rig, "POSE")
        for role, generated in (("CONTROLS", record["controls"]), ("MECHANISM", record["mechanism"])):
            collection = rig.data.collections.new(prefix + "_" + role.title())
            record["collections"].append(collection.name)
            collection[OWNER], collection[ROLE] = record["owner"], role
            for name in generated:
                collection.assign(rig.data.bones[name])
                rig.data.bones[name].color.palette = "THEME09" if role == "CONTROLS" else "THEME03"
            collection.is_visible = role == "CONTROLS"
        for name in record["controls"]:
            pose = rig.pose.bones[name]
            pose.lock_rotation = (True, True, True)
            pose.lock_rotation_w = True
            pose.lock_scale = (True, True, True)
        _checkpoint("bones")
        curve_data = bpy.data.curves.new(prefix + "_Spline", "CURVE")
        curve_data[OWNER] = record["owner"]
        curve_data.dimensions, curve_data.twist_mode = "3D", "MINIMUM"
        curve_data.resolution_u = 12
        spline = curve_data.splines.new("NURBS")
        spline.points.add(2)
        spline.order_u, spline.use_endpoint_u = 3, True
        for point, t in zip(spline.points, (0.0, 0.5, 1.0)):
            point.co = (*head.lerp(tail, t), 1.0)
        curve = bpy.data.objects.new(prefix + "_Spline", curve_data)
        curve[OWNER], curve[RIG_REF] = record["owner"], rig
        context.scene.collection.objects.link(curve)
        curve.parent = rig
        curve.matrix_parent_inverse = curve.matrix_basis = Matrix.Identity(4)
        curve.hide_render, curve.show_in_front, curve.display_type = True, True, "WIRE"
        context.view_layer.update()
        for index, name in enumerate(record["controls"]):
            modifier = curve.modifiers.new(f"Recovered Hook {index + 1:02d}", "HOOK")
            modifier.object, modifier.subtarget = rig, name
            modifier.vertex_indices_set([index])
            modifier.strength, modifier.falloff_type = 1.0, "NONE"
            # Bind in REST space, so a currently posed/animated parent moves
            # the wire and copied source chain together without double motion.
            modifier.matrix_inverse = (rig.matrix_world @ rig.data.bones[name].matrix_local).inverted() @ curve.matrix_world
        _checkpoint("curve")
        constraint = rig.pose.bones[record["mechanism"][-1]].constraints.new("SPLINE_IK")
        constraint.name = prefix + "_SplineIK"
        record["spline_constraint"] = constraint.name
        constraint.target, constraint.chain_count = curve, len(ordered)
        constraint.use_even_divisions, constraint.use_curve_radius = False, False
        constraint.y_scale_mode, constraint.xz_scale_mode = "FIT_CURVE", "NONE"
        constraint.use_chain_offset = False
        for source, mechanism in zip(ordered, record["mechanism"]):
            constraint = rig.pose.bones[source].constraints.new("COPY_TRANSFORMS")
            constraint.name = prefix + "_FK_From_SPIK"
            record["constraints"].append(constraint.name)
            constraint.target, constraint.subtarget = rig, mechanism
            constraint.owner_space = constraint.target_space = "LOCAL"
            constraint.mix_mode = "BEFORE"
        _checkpoint("constraints")
        context.view_layer.update()
        _inventory(rig, record)
        evaluated = rig.evaluated_get(context.evaluated_depsgraph_get())
        for name, original in baseline.items():
            matrix = evaluated.pose.bones[name].matrix
            position_error = (matrix.translation - original.translation).length
            axis_error = max(abs(matrix[i][j] - original[i][j]) for i in range(3) for j in range(3))
            if position_error > max(length * 2e-4, 1e-6) or axis_error > 2e-3:
                raise RecoveryError("The three-point solver could not preserve this chain's initial pose; construction was rolled back. "
                                    f"Bone {name}: position error {position_error:.6g}, axis error {axis_error:.6g}.")
        records[record["owner"]] = record
        _write_records(rig, records)
        _select_controls(context, rig, record, snapshot["mode"])
        return record
    except Exception:
        _delete_generated(context, rig, record, curve)
        if curve_data is not None and any(data is curve_data for data in bpy.data.curves) and curve_data.users == 0:
            bpy.data.curves.remove(curve_data)
        records.pop(record["owner"], None)
        _write_records(rig, records)
        _restore(context, rig, snapshot)
        raise


def remove_selected(context=bpy.context):
    """Remove one verified owned setup, retaining the original bones and rig data."""
    rig, names = _selection(context)
    records = _records(rig)
    record = _matching(rig, names, records)
    if record is None:
        raise RecoveryError("Select a whole recovered source chain or one of its controls.")
    snapshot = _snapshot(context, rig)
    try:
        _mode(context, rig, "POSE")
        curve = _inventory(rig, record, for_removal=True)
    except Exception:
        _restore(context, rig, snapshot)
        raise
    _delete_generated(context, rig, record, curve)
    records.pop(record["owner"])
    _write_records(rig, records)
    _mode(context, rig, snapshot["mode"])
    bones = rig.data.edit_bones if rig.mode == "EDIT" else rig.pose.bones
    for bone in bones:
        bone.select = bone.name in record["source"]
        if rig.mode == "EDIT":
            bone.select_head = bone.select_tail = bone.select
    active_bones = rig.data.edit_bones if rig.mode == "EDIT" else rig.data.bones
    active_bones.active = active_bones[record["source"][0]]
    context.view_layer.update()
    return record


if __name__ == "__main__":
    result = build_selected()
    print(f"Recovered {len(result['source'])} FK bones with three Spline IK controls.")
