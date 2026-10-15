"""Experimental paired-bone backend for an explicitly disposable preview.

This module has no registration, handlers, operators, export, or save entry point.
The pure plan expresses the existing post-skin target, not its float32 inverse
Shape Key implementation. Native construction is restricted to background
Blender and independent mesh/rig copies. Native geometry equivalence and timing
remain mandatory before this experiment can become an artist playback backend.

For a sample with ratio r and influence a, the additional deform bones implement
L @ R(r*theta) and H @ R((r-1)*theta). Their weights are a*wL and a*wH; the
original terms keep (1-a)*wL and (1-a)*wH. All unrelated contributions remain.
This preserves wrist swing and translation, unlike a single lower-follow bone.
"""

import json
import math
import uuid
from dataclasses import dataclass, replace
from weakref import WeakValueDictionary


RECORD_KEY = "character_designer_forearm_twist_v1"
OWNER_KEY = "character_designer_forearm_bone_preview_owner"
MAX_ANGLE = math.radians(120.0)
_ISSUED_PLANS = WeakValueDictionary()


class BonePreviewError(ValueError):
    """The isolated input cannot safely use this experimental backend."""


def _require(condition, message):
    if not condition:
        raise BonePreviewError(message)


def _number(value, label):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool),
             label + " must be a finite number")
    value = float(value)
    _require(math.isfinite(value), label + " must be finite")
    return value


def _name(value, label):
    _require(isinstance(value, str) and bool(value), label + " must be nonempty")
    return value


def _vector(value, label):
    _require(isinstance(value, (tuple, list)) and len(value) == 3,
             label + " must have three components")
    return tuple(_number(item, label) for item in value)


@dataclass(frozen=True)
class Side:
    name: str
    lower: str
    hand: str
    axis: tuple
    pivot: tuple
    enabled: bool
    samples: tuple  # (vertex index, ratio, influence)


@dataclass(frozen=True)
class Helper:
    key: tuple  # (side name, lower/hand role, exact sampled ratio)
    source_bone: str
    fraction: float
    axis: tuple
    pivot: tuple


@dataclass(frozen=True)
class Rewrite:
    index: int
    source_weights: tuple  # exact source normalized deform weights, native order
    target_weights: tuple  # original name or Helper.key, normalized amount
    transfers: tuple  # original name, Helper.key, influence


@dataclass(frozen=True)
class Plan:
    vertex_count: int
    sides: tuple
    helpers: tuple
    rewrites: tuple
    managed_key_names: tuple
    record_text: str
    source_ids: tuple = ()


def build_plan(sides, weights, *, vertex_count, managed_key_names=(), record_text=""):
    """Compile immutable validated source samples without reading Blender.

    Callers supply normalized *all-deform* weights from the authoring preflight.
    The native builder independently checks them against its source and clone.
    Ratios are never quantized, and two close ratios never share a helper.
    """
    _require(isinstance(vertex_count, int) and not isinstance(vertex_count, bool)
             and vertex_count > 0, "Vertex count must be a positive integer")
    weight_rows = tuple(weights.items()) if isinstance(weights, dict) else tuple(weights)
    by_index = {}
    for index, row in weight_rows:
        _require(isinstance(index, int) and not isinstance(index, bool)
                 and 0 <= index < vertex_count and index not in by_index,
                 "Weights need unique in-range vertex indices")
        row = tuple(row.items()) if isinstance(row, dict) else tuple(row)
        clean, names = [], set()
        for name, amount in row:
            name = _name(name, "Deform bone")
            amount = _number(amount, "Deform weight")
            _require(amount > 0.0 and name not in names,
                     "Weights must be positive and have unique bone names")
            names.add(name)
            clean.append((name, amount))
        _require(clean and abs(sum(amount for _name_, amount in clean) - 1.0) <= 1e-4,
                 "Weights must be normalized across every deform influence")
        by_index[index] = tuple(clean)

    frozen_sides, helpers, rewrites = [], {}, []
    claimed, side_names = set(), set()
    for source in tuple(sides):
        name = _name(source.name, "Side")
        lower, hand = _name(source.lower, "Lower bone"), _name(source.hand, "Hand bone")
        _require(name not in side_names and lower != hand, "Sides and chain roles must be unique")
        side_names.add(name)
        axis, pivot = _vector(source.axis, "Axis"), _vector(source.pivot, "Pivot")
        axis_length = math.hypot(*axis)
        _require(math.isfinite(axis_length) and axis_length >= 1e-6, "Axis has invalid length")
        _require(isinstance(source.enabled, bool), "Side enabled must be a boolean")
        samples = []
        for index, ratio, influence in tuple(source.samples):
            _require(isinstance(index, int) and not isinstance(index, bool)
                     and 0 <= index < vertex_count and index not in claimed,
                     "Samples must be disjoint and have in-range indices")
            _require(index in by_index, "A sample is missing its source deform weights")
            claimed.add(index)
            ratio, influence = _number(ratio, "Ratio"), _number(influence, "Influence")
            _require(0.0 <= ratio <= 1.0 and 0.0 <= influence <= 1.0,
                     "Ratio and influence must be in [0, 1]")
            samples.append((index, ratio, influence))
            if not source.enabled or influence == 0.0:
                continue
            targets, transfers = [], []
            for bone_name, amount in by_index[index]:
                role = "lower" if bone_name == lower else "hand" if bone_name == hand else None
                fraction = ratio if role == "lower" else ratio - 1.0 if role == "hand" else 0.0
                if role is None or fraction == 0.0:
                    targets.append((bone_name, amount))
                    continue
                key = (name, role, ratio)
                helpers.setdefault(key, Helper(key, bone_name, fraction, axis, pivot))
                if influence < 1.0:
                    targets.append((bone_name, amount * (1.0 - influence)))
                targets.append((key, amount * influence))
                transfers.append((bone_name, key, influence))
            if transfers:
                rewrites.append(Rewrite(index, by_index[index], tuple(targets), tuple(transfers)))
        _require(bool(samples), "Each side needs at least one captured sample")
        frozen_sides.append(Side(name, lower, hand, axis, pivot, source.enabled, tuple(samples)))
    _require(bool(frozen_sides), "At least one captured side is required")
    names = tuple(_name(name, "Managed key") for name in managed_key_names)
    _require(len(set(names)) == len(names), "Managed key names must be unique")
    _require(isinstance(record_text, str), "Record text must be a string")
    return Plan(vertex_count, tuple(frozen_sides), tuple(helpers.values()), tuple(rewrites), names, record_text)


def plan_from_template(template, *, vertex_count=None):
    """Read the playback core's frozen validated template without consuming it."""
    from . import forearm_twist_playback_core as core
    core.check_template(template)
    if vertex_count is None:
        vertex_count = template.vertex_count
    _require(vertex_count == template.vertex_count, "Template vertex count differs")
    record_text = template.record_text
    _require(isinstance(record_text, str) and bool(record_text), "A captured calibration is required")
    try:
        records = json.loads(record_text)
        names = tuple(record["key"] for record in records.values())
    except (TypeError, ValueError, KeyError, AttributeError) as error:
        raise BonePreviewError("Captured calibration is malformed") from error
    plan = replace(build_plan(template.sides, template.weights, vertex_count=vertex_count,
                              managed_key_names=names, record_text=record_text),
                   source_ids=template.source_ids)
    _ISSUED_PLANS[id(plan)] = plan
    return plan


def _native_weights(mesh, rig, index):
    names = {group.index: group.name for group in mesh.vertex_groups
             if group.name in rig.data.bones and rig.data.bones[group.name].use_deform}
    raw = tuple((names[group.group], float(group.weight))
                for group in mesh.data.vertices[index].groups
                if group.group in names and group.weight > 0.0)
    total = sum(amount for _name_, amount in raw)
    _require(raw and total > 0.0, "A captured vertex has no current deform weights")
    return raw, tuple((name, amount / total) for name, amount in raw)


def _clone_guard(mesh, rig, source_mesh, source_rig, plan, disposable):
    import bpy
    _require(disposable is True and bpy.app.background,
             "Bone preview construction is restricted to explicitly disposable background scenes")
    _require(_ISSUED_PLANS.get(id(plan)) is plan,
             "Use an unused plan_from_template result for native construction")
    _require(mesh.type == source_mesh.type == "MESH" and rig.type == source_rig.type == "ARMATURE",
             "Expected mesh and armature source/clone pairs")
    _require(mesh != source_mesh and rig != source_rig and mesh.data != source_mesh.data
             and rig.data != source_rig.data, "Source and preview must own independent datablocks")
    current_source_ids = tuple((getattr(item, "session_uid", None), int(item.as_pointer()))
                               for item in (source_mesh, source_mesh.data, source_rig,
                                            source_rig.data, source_mesh.data.shape_keys))
    _require(current_source_ids == plan.source_ids, "Source identities differ from captured template")
    _require(mesh.matrix_world == source_mesh.matrix_world and rig.matrix_world == source_rig.matrix_world,
             "Clone/source object transforms differ")
    _require(mesh.library is None and rig.library is None and mesh.data.library is None
             and rig.data.library is None, "Linked preview data is unsupported")
    _require(all(obj == mesh for obj in bpy.data.objects if obj.type == "MESH" and obj.data == mesh.data)
             and all(obj == rig for obj in bpy.data.objects if obj.type == "ARMATURE" and obj.data == rig.data),
             "Preview mesh/rig data has another object owner")
    _require(len(mesh.data.vertices) == len(source_mesh.data.vertices) == plan.vertex_count,
             "Preview/source vertex counts changed")
    keys, source_keys = mesh.data.shape_keys, source_mesh.data.shape_keys
    _require(keys is not None and source_keys is not None and keys != source_keys and keys.use_relative,
             "Preview requires an independent relative Shape Key datablock")
    _require(keys.library is None, "Linked preview Shape Keys are unsupported")
    _require(OWNER_KEY not in mesh and OWNER_KEY not in rig, "Preview has already been built")
    _require(plan.record_text and source_mesh.get(RECORD_KEY) == plan.record_text,
             "Authoritative source calibration changed after capture")
    _require(bool(plan.managed_key_names) and all(name in keys.key_blocks for name in plan.managed_key_names),
             "Managed keys are missing on the clone")
    _require(all(key.relative_key.name not in plan.managed_key_names for key in keys.key_blocks
                 if key.name not in plan.managed_key_names),
             "Foreign Shape Keys relative to a managed corrective need a separate dependency backend")
    _require(bool(mesh.modifiers) and mesh.modifiers[0].type == "ARMATURE",
             "This experiment needs Armature first")
    mod = mesh.modifiers[0]
    _require(sum(item.type == "ARMATURE" for item in mesh.modifiers) == 1
             and mod.object in (source_rig, rig) and mod.use_vertex_groups
             and not (mod.use_bone_envelopes or mod.use_deform_preserve_volume
                      or mod.use_multi_modifier or mod.vertex_group)
             and mod.show_viewport and mod.show_render,
             "Only ordinary unmasked LBS is supported")
    _require(mesh.mode == rig.mode == "OBJECT" and bpy.context.mode == "OBJECT",
             "Construct the disposable preview in Object Mode")
    _require(mesh.name in bpy.context.view_layer.objects and rig.name in bpy.context.view_layer.objects,
             "Preview objects must be in the active disposable view layer")
    for side in plan.sides:
        _require(side.lower in rig.data.bones and side.hand in rig.data.bones,
                 "A captured chain bone is missing")
        for index, _ratio, _influence in side.samples:
            expected = next((row.source_weights for row in plan.rewrites if row.index == index), None)
            if expected is None:
                continue
            _require(_native_weights(source_mesh, source_rig, index)[1] == expected
                     and _native_weights(mesh, rig, index)[1] == expected,
                     "Source or clone weights changed after capture")
            _require(all(rig.data.bones[name].bbone_segments == 1 for name, _weight in expected),
                     "Segmented B-Bone influences are unsupported")


def _preserve_shape_masks(mesh, rig, rewrites, managed_names):
    """Copy affected foreign masks before transferring clone deform weights."""
    affected = {name for rewrite in rewrites for name, _key, _a in rewrite.transfers}
    keys = mesh.data.shape_keys.key_blocks
    mask_names = {key.vertex_group for key in keys
                  if key.name not in managed_names and key.vertex_group in affected}
    remapping = {}
    for number, name in enumerate(sorted(mask_names), 1):
        source = mesh.vertex_groups.get(name)
        _require(source is not None, "A foreign Shape Key mask is missing")
        candidate = "Forearm Preview Mask %02d" % number
        while candidate in mesh.vertex_groups or candidate in rig.data.bones:
            number += 1
            candidate = "Forearm Preview Mask %02d" % number
        target = mesh.vertex_groups.new(name=candidate)
        _require(target.name not in rig.data.bones,
                 "A copied foreign mask must remain a non-deform group")
        for vertex in mesh.data.vertices:
            amount = next((float(item.weight) for item in vertex.groups if item.group == source.index), 0.0)
            if amount > 0.0:
                target.add([vertex.index], amount, "REPLACE")
        remapping[name] = target.name
    for key in keys:
        if key.name not in managed_names and key.vertex_group in remapping:
            key.vertex_group = remapping[key.vertex_group]
    return remapping


class IsolatedBonePreview:
    """Owned helper matrices in a fixed disposable clone; no implicit updates."""

    def __init__(self, mesh, rig, plan, token, helpers, mask_copies):
        self.mesh, self.rig, self.plan, self.token = mesh, rig, plan, token
        self.helper_names = dict(helpers)
        self.mask_copies = dict(mask_copies)
        self._rest = {key: rig.data.bones[name].matrix_local.copy() for key, name in helpers.items()}
        self._pointers = {key: rig.data.bones[name].as_pointer() for key, name in helpers.items()}

    def update_from_deformations(self, transforms):
        """Set helper basis from evaluated armature-space source deformations.

        Read/evaluate original lower and hand first, call this method, then let
        Blender evaluate the clone. This method never seeks, updates a depsgraph,
        reads vertices, writes keys/groups, or installs a callback.
        """
        from mathutils import Matrix, Quaternion, Vector
        from .forearm_twist_math import TwistMathError, twist_angle
        _require(self.mesh.get(OWNER_KEY) == self.token and self.rig.get(OWNER_KEY) == self.token,
                 "Preview ownership changed")
        angles = {}
        for side in self.plan.sides:
            if not side.enabled:
                angles[side.name] = 0.0
                continue
            _require(side.lower in transforms and side.hand in transforms,
                     "A current deformation matrix is missing")
            try:
                angle = twist_angle(transforms[side.lower], transforms[side.hand], side.axis)
            except (TwistMathError, ValueError, TypeError) as error:
                raise BonePreviewError("Current deformation is unsupported: " + str(error)) from error
            _require(abs(angle) <= MAX_ANGLE + 1e-5, "Twist exceeds the calibrated +/-120 degree range")
            angles[side.name] = angle
        pending = []
        for helper in self.plan.helpers:
            name = self.helper_names[helper.key]
            bone, pose = self.rig.data.bones.get(name), self.rig.pose.bones.get(name)
            _require(bone is not None and pose is not None and bone.as_pointer() == self._pointers[helper.key]
                     and bone.parent is None and bone.get(OWNER_KEY) == self.token,
                     "Owned helper identity or parent changed")
            rest = self._rest[helper.key]
            _require(bone.matrix_local == rest and not pose.constraints,
                     "Owned helper rest or constraints changed")
            axis, pivot = Vector(helper.axis).normalized(), Vector(helper.pivot)
            rotation = (Matrix.Translation(pivot)
                        @ Quaternion(axis, helper.fraction * angles[helper.key[0]]).to_matrix().to_4x4()
                        @ Matrix.Translation(-pivot))
            # Unparented bone pose = Rest @ basis. Thus pose @ Rest^-1 = T @ R.
            basis = rest.inverted() @ (transforms[helper.source_bone] @ rotation @ rest)
            _require(all(math.isfinite(value) for row in basis for value in row),
                     "A helper basis became non-finite")
            pending.append((pose, basis, pose.matrix_basis.copy()))
        written = []
        try:
            for pose, basis, previous in pending:
                written.append((pose, previous))
                pose.matrix_basis = basis
        except Exception:
            for pose, previous in reversed(written):
                pose.matrix_basis = previous
            raise
        return tuple((side.name, angles[side.name]) for side in self.plan.sides)


def build_isolated_preview(mesh, rig, plan, *, source_mesh, source_rig, disposable=False):
    """Modify only verified disposable copies; construction failures discard them.

    Caller owns destruction of a failed clone and source graph proof. No authored
    object, original group, key, rig, action or file is changed. Helper groups
    receive native raw weights, preserving all unrelated native group weights.
    """
    import bpy
    from mathutils import Vector
    _require(isinstance(plan, Plan), "A compiled immutable Plan is required")
    _clone_guard(mesh, rig, source_mesh, source_rig, plan, disposable)
    _ISSUED_PLANS.pop(id(plan), None)
    token = uuid.uuid4().hex
    mesh[OWNER_KEY] = rig[OWNER_KEY] = token
    mesh.modifiers[0].object = rig
    # A copied authoring record must never enroll this clone in the existing
    # authoring handler or apply the inverse Shape Key on top of helper skinning.
    if RECORD_KEY in mesh:
        del mesh[RECORD_KEY]
    for name in plan.managed_key_names:
        key = mesh.data.shape_keys.key_blocks[name]
        key.value, key.mute = 0.0, True
    masks = _preserve_shape_masks(mesh, rig, plan.rewrites, set(plan.managed_key_names))
    selected, active = tuple(bpy.context.selected_objects), bpy.context.view_layer.objects.active
    names = {}
    try:
        for obj in selected:
            obj.select_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        result = bpy.ops.object.mode_set(mode="EDIT")
        _require("FINISHED" in result and rig.mode == "EDIT", "Could not edit the disposable rig")
        for number, helper in enumerate(plan.helpers, 1):
            candidate = "Forearm Preview %s %s %02d" % (helper.key[0], helper.key[1].title(), number)
            while candidate in rig.data.edit_bones or candidate in mesh.vertex_groups:
                number += 1
                candidate = "Forearm Preview %s %s %02d" % (helper.key[0], helper.key[1].title(), number)
            bone = rig.data.edit_bones.new(candidate)
            bone.head = Vector(helper.pivot)
            bone.tail = bone.head + Vector(helper.axis).normalized() * 0.05
            bone.parent, bone.use_connect, bone.use_deform = None, False, True
            names[helper.key] = bone.name
        result = bpy.ops.object.mode_set(mode="OBJECT")
        _require("FINISHED" in result and rig.mode == "OBJECT", "Could not finish the disposable rig")
    finally:
        if rig.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        rig.select_set(False)
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
    for name in names.values():
        rig.data.bones[name][OWNER_KEY] = token
        _require(mesh.vertex_groups.new(name=name).name == name,
                 "A helper group name could not match its owned bone")
    for rewrite in plan.rewrites:
        raw = dict(_native_weights(mesh, rig, rewrite.index)[0])
        for original, helper_key, influence in rewrite.transfers:
            amount = raw[original]
            group = mesh.vertex_groups[original]
            if influence == 1.0:
                group.remove([rewrite.index])
            else:
                group.add([rewrite.index], amount * (1.0 - influence), "REPLACE")
            mesh.vertex_groups[names[helper_key]].add([rewrite.index], amount * influence, "REPLACE")
    return IsolatedBonePreview(mesh, rig, plan, token, names, masks)
