"""Read-only, fail-closed content proofs for explicit animation worklist scans.

Importing this module needs no Blender. ``fingerprint_serialized`` hashes a
JSON-compatible payload; ``fingerprint_native`` collects one from native RNA.
Neither collector activates an Action, evaluates a frame, nor writes an ID.
Unknown dependencies return an empty full fingerprint, never an unchanged
claim. The first native policy intentionally supports plain FK rigs only.
"""

import hashlib
import json
import math


SCHEMA = 'character-designer.animation-worklist-fingerprint/1'
PROOF_POLICY = 'plain-fk-slot-v1'
MAX_ITEMS = 1_000_000
MAX_DEPTH = 32


class FingerprintUnknown(ValueError):
    """The current input cannot be proven complete without changing it."""


# RNA identity, editor state and evaluated/diagnostic fields have no role in
# Action evaluation. Everything else is serialized or explicitly refused.
_ID_METADATA = frozenset({
    'rna_type', 'name', 'name_full', 'id_type', 'users', 'use_fake_user',
    'use_extra_user', 'is_embedded_data', 'is_missing', 'is_runtime_data',
    'is_editable', 'is_evaluated', 'original', 'session_uid', 'tag', 'library',
    'library_weak_reference', 'asset_data', 'override_library', 'preview',
    'is_updated', 'is_updated_data', 'is_updated_transform',
    'is_library_indirect', 'is_linked_packed',
})
_CURVE_UI = frozenset({'select', 'hide', 'lock', 'color', 'color_mode',
                       'is_valid', 'is_empty'})
_KEY_UI = frozenset({'select_control_point', 'select_left_handle',
                    'select_right_handle'})
_MODIFIER_UI = frozenset({'name', 'show_expanded', 'active', 'is_valid'})
_TRANSFORM_SIZES = {
    'location': 3, 'rotation_euler': 3, 'rotation_quaternion': 4,
    'rotation_axis_angle': 4, 'scale': 3, 'delta_location': 3,
    'delta_rotation_euler': 3, 'delta_rotation_quaternion': 4, 'delta_scale': 3,
}
_POSE_EVALUATED = frozenset({'matrix', 'matrix_basis', 'matrix_channel', 'head',
                            'tail', 'length', 'center'})


def _plain(value, *, depth=0, budget=None):
    """Copy JSON values without coercing objects, non-finite numbers or keys."""
    if budget is None:
        budget = [MAX_ITEMS]
    budget[0] -= 1
    if budget[0] < 0 or depth > MAX_DEPTH:
        raise FingerprintUnknown('Fingerprint payload exceeds its bounded size/depth.')
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise FingerprintUnknown('Fingerprint payload contains a non-finite number.')
        # -0.0 and 0.0 represent the same motion.
        return 0.0 if value == 0.0 else value
    if type(value) in (list, tuple):
        return [_plain(item, depth=depth + 1, budget=budget) for item in value]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise FingerprintUnknown('Fingerprint dictionary keys must be strings.')
        return {key: _plain(item, depth=depth + 1, budget=budget)
                for key, item in value.items()}
    raise FingerprintUnknown('Unsupported fingerprint value: ' + type(value).__name__)


def canonical_bytes(value):
    """Stable pure serialization; no filesystem, Blender or implicit repr()."""
    return json.dumps(_plain(value), ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(',', ':')).encode('utf-8')


def _digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _result(known, reason, *, fingerprint='', action_fingerprint=''):
    return {'schema': SCHEMA, 'fingerprint_known': bool(known),
            'fingerprint': fingerprint, 'action_fingerprint': action_fingerprint,
            'proof_reason': reason}


def fingerprint_serialized(payload):
    """Hash a collected payload only when its explicit dependency proof is complete.

    A supplied pure payload is a caller attestation, not native validation.
    ``action_fingerprint`` is motion-only: no Action name or native slot handle.
    ``fingerprint`` additionally includes export timing and FK dependencies.
    """
    action_hash = ''
    try:
        value = _plain(payload)
        if not isinstance(value, dict) or value.get('schema') != SCHEMA:
            raise FingerprintUnknown('Unknown fingerprint schema.')
        if not isinstance(value.get('action'), dict):
            raise FingerprintUnknown('Fingerprint needs a complete selected-slot Action payload.')
        action_hash = _digest({'schema': SCHEMA, 'action': value['action']})
        proof = value.get('proof')
        if (not isinstance(proof, dict) or proof.get('complete') is not True
                or proof.get('policy') != PROOF_POLICY):
            raise FingerprintUnknown('Rig dependency proof is incomplete or unsupported.')
        if not isinstance(value.get('rig'), dict) or not isinstance(value.get('export'), dict):
            raise FingerprintUnknown('Fingerprint needs rig dependencies and export timing.')
        timing = value['export']
        for field in ('frame_start', 'frame_end', 'fps', 'fps_base', 'sample_rate', 'unit_scale'):
            number = timing.get(field)
            if type(number) not in (int, float) or not math.isfinite(number):
                raise FingerprintUnknown('Export timing is missing/invalid: ' + field)
        if (timing['frame_end'] <= timing['frame_start'] or timing['fps'] <= 0
                or timing['fps_base'] <= 0 or not 1 <= timing['sample_rate'] <= 240
                or timing['unit_scale'] <= 0 or type(timing.get('loop')) is not bool):
            raise FingerprintUnknown('Export timing or loop policy is outside the supported range.')
        return _result(True, 'Complete selected-slot motion and plain FK dependencies.',
                       fingerprint=_digest(value), action_fingerprint=action_hash)
    except (FingerprintUnknown, AttributeError, TypeError, ValueError) as exc:
        return _result(False, str(exc), action_fingerprint=action_hash)


def _rna_settings(block, *, exclude=(), depth=0):
    """Record all non-excluded RNA properties, including modifier collections.

    Read-only is not used as a blanket exclusion: key coordinates, envelope
    control-point collections and several meaningful Action fields are read-only
    containers. A non-null pointer, unsupported property type or read failure
    is Unknown rather than being silently omitted.
    """
    if depth > MAX_DEPTH:
        raise FingerprintUnknown('RNA settings exceed the supported depth.')
    properties = getattr(getattr(block, 'bl_rna', None), 'properties', None)
    if properties is None:
        raise FingerprintUnknown('Native block has no inspectable RNA settings.')
    excluded = set(exclude) | {'rna_type'}
    result = {}
    for prop in properties:
        name = prop.identifier
        if name in excluded:
            continue
        try:
            value = getattr(block, name)
        except (AttributeError, ReferenceError, RuntimeError, TypeError) as exc:
            raise FingerprintUnknown('Cannot read RNA property ' + name) from exc
        kind = prop.type
        if kind in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}:
            if getattr(prop, 'is_array', False):
                if getattr(prop, 'array_dimensions', ()) and len([x for x in prop.array_dimensions if x]) > 1:
                    result[name] = [_plain(tuple(row)) for row in value]
                else:
                    result[name] = _plain(tuple(value))
            elif kind == 'ENUM' and isinstance(value, set):
                result[name] = sorted(value)
            else:
                result[name] = _plain(value)
        elif kind == 'POINTER':
            if value is not None:
                raise FingerprintUnknown('Unproven RNA pointer dependency: ' + name)
            result[name] = None
        elif kind == 'COLLECTION':
            values = list(value)
            if len(values) > MAX_ITEMS:
                raise FingerprintUnknown('RNA collection exceeds its bounded size: ' + name)
            result[name] = [_rna_settings(item, depth=depth + 1) for item in values]
        else:
            raise FingerprintUnknown('Unsupported RNA property type: ' + name + ' (' + str(kind) + ')')
    return result


def _slot(action, slot_handle):
    if type(slot_handle) is not int:
        raise FingerprintUnknown('Selected Action slot handle must be an integer.')
    if not action.is_action_layered:
        if slot_handle != 0:
            raise FingerprintUnknown('Legacy Actions require slot handle zero.')
        return None
    matches = [slot for slot in action.slots if slot.handle == slot_handle
               and slot.target_id_type == 'OBJECT']
    if len(matches) != 1:
        raise FingerprintUnknown('The exact selected Object slot is missing or ambiguous.')
    return matches[0]


def _selected_curves(action, slot_handle):
    _slot(action, slot_handle)
    if not action.is_action_layered:
        return list(action.fcurves)
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags if bag.slot_handle == slot_handle
            for curve in bag.fcurves]


def _curve_payload(curve):
    if getattr(curve, 'driver', None) is not None or getattr(curve, 'is_driver', False):
        raise FingerprintUnknown('FCurve drivers are outside the plain FK content proof.')
    result = _rna_settings(curve, exclude=_CURVE_UI | {'group', 'driver', 'is_driver',
            'keyframe_points', 'sampled_points', 'modifiers'})
    result['keyframe_points'] = [_rna_settings(point, exclude=_KEY_UI)
                                 for point in curve.keyframe_points]
    result['sampled_points'] = [_rna_settings(point, exclude={'select'})
                                for point in curve.sampled_points]
    result['modifiers'] = [_rna_settings(modifier, exclude=_MODIFIER_UI)
                           for modifier in curve.modifiers]
    group = getattr(curve, 'group', None)
    if group is not None:
        result['group'] = _rna_settings(group, exclude={'name', 'channels', 'select',
                'lock', 'show_expanded', 'show_expanded_graph', 'use_pin', 'color_set',
                'colors', 'is_custom_color_set'})
    return result


def collect_action_payload(action, slot_handle):
    """Complete selected-slot RNA content, independent of display names/handles."""
    _slot(action, slot_handle)
    settings = _rna_settings(action, exclude=_ID_METADATA | {'slots', 'layers',
            'fcurves', 'groups', 'pose_markers', 'is_action_layered', 'is_action_legacy',
            'is_empty', 'curve_frame_range'})
    layers = []
    if action.is_action_layered:
        for layer in action.layers:
            strips = []
            for strip in layer.strips:
                if strip.type != 'KEYFRAME':
                    raise FingerprintUnknown('Unsupported Action strip type: ' + str(strip.type))
                bags = [bag for bag in strip.channelbags if bag.slot_handle == slot_handle]
                if len(bags) > 1:
                    raise FingerprintUnknown('Several channelbags use the same selected slot in one strip.')
                if bags:
                    strips.append({'settings': _rna_settings(strip, exclude={'channelbags'}),
                                   'curves': [_curve_payload(curve) for curve in bags[0].fcurves]})
            if strips:
                layers.append({'settings': _rna_settings(layer, exclude={'name', 'strips'}),
                               'strips': strips})
    else:
        layers = [{'settings': {}, 'strips': [{'settings': {'type': 'LEGACY'},
                   'curves': [_curve_payload(curve) for curve in action.fcurves]}]}]
    if not layers:
        raise FingerprintUnknown('The selected slot has no supported curve content.')
    return {'settings': settings, 'slot_type': 'OBJECT', 'layers': layers}


def fingerprint_action(action, slot_handle):
    """Motion-only comparison, also usable for a linked read-only Source Action."""
    try:
        payload = collect_action_payload(action, slot_handle)
        return _result(True, 'Complete selected-slot Action content.',
                       action_fingerprint=_digest({'schema': SCHEMA, 'action': payload}))
    except (FingerprintUnknown, AttributeError, ReferenceError, RuntimeError,
            TypeError, ValueError) as exc:
        return _result(False, str(exc))


def _rotation_property(mode):
    if mode == 'QUATERNION':
        return 'rotation_quaternion'
    if mode == 'AXIS_ANGLE':
        return 'rotation_axis_angle'
    if mode in {'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX'}:
        return 'rotation_euler'
    raise FingerprintUnknown('Unsupported rotation mode: ' + str(mode))


def _enabled_channels(action, slot_handle):
    result = set()
    for curve in _selected_curves(action, slot_handle):
        if not getattr(curve, 'is_valid', True):
            raise FingerprintUnknown('A disabled/invalid FCurve cannot prove keyed coverage: '
                                     + curve.data_path)
        group = getattr(curve, 'group', None)
        if curve.mute or (group is not None and getattr(group, 'mute', False)):
            continue
        if not curve.keyframe_points and not curve.sampled_points:
            raise FingerprintUnknown('An enabled curve without points cannot prove full keyed coverage.')
        result.add((curve.data_path, curve.array_index))
    return result


def _plain_replace(action, export_range):
    if action.is_action_layered:
        if len(action.layers) != 1 or len(action.layers[0].strips) != 1:
            raise FingerprintUnknown('Multiple layers/strips cannot prove full replacement of snapshot values.')
        layer = action.layers[0]
        if getattr(layer, 'mute', False):
            raise FingerprintUnknown('A muted layer cannot prove keyed replacement.')
        for field in ('mix_mode', 'blend_type'):
            if hasattr(layer, field) and getattr(layer, field) != 'REPLACE':
                raise FingerprintUnknown('Layer blending cannot prove full keyed replacement.')
        if hasattr(layer, 'influence') and layer.influence != 1.0:
            raise FingerprintUnknown('Partial layer influence needs unproven snapshot values.')
        strip = layer.strips[0]
        if (getattr(strip, 'mute', False) or strip.type != 'KEYFRAME'
                or getattr(strip, 'frame_start', export_range[0]) > export_range[0]
                or getattr(strip, 'frame_end', export_range[1]) < export_range[1]):
            raise FingerprintUnknown('The selected strip cannot prove keyed coverage of the export range.')


def _validate_transform_channels(action, rig, slot_handle):
    supported = {field: _TRANSFORM_SIZES[field] for field in _TRANSFORM_SIZES
                 if hasattr(rig, field)}
    for bone in rig.pose.bones:
        prefix = bone.path_from_id() + '.'
        supported.update({prefix + field: _TRANSFORM_SIZES[field] for field in _TRANSFORM_SIZES
                          if hasattr(bone, field)})
    for curve in _selected_curves(action, slot_handle):
        size = supported.get(curve.data_path)
        if (size is None or type(curve.array_index) is not int
                or not 0 <= curve.array_index < size):
            raise FingerprintUnknown('Selected-slot channel is outside the plain FK transform proof: '
                                     + str(curve.data_path))


def _unkeyed_transform(block, prefix, keyed, foreign, *, object_block=False):
    mode = block.rotation_mode
    fields = ['location', _rotation_property(mode), 'scale']
    if object_block:
        fields += ['delta_location', 'delta_scale',
                   'delta_rotation_quaternion' if mode == 'QUATERNION' else 'delta_rotation_euler']
    values = {'rotation_mode': mode}
    for field in fields:
        source = tuple(getattr(block, field))
        if len(source) != _TRANSFORM_SIZES[field]:
            raise FingerprintUnknown('Unexpected transform dimensions: ' + prefix + field)
        remaining = {}
        for index, value in enumerate(source):
            channel = (prefix + field, index)
            if channel in keyed:
                continue
            if channel in foreign:
                raise FingerprintUnknown('Unkeyed input is driven by the currently active foreign Action: '
                                         + prefix + field)
            remaining[str(index)] = _plain(value)
        if remaining:
            values[field] = remaining
    return values


def _rig_payload(action, rig, slot_handle, export_range):
    if (rig.type != 'ARMATURE' or rig.library or rig.data.library or rig.parent is not None
            or rig.data.pose_position != 'POSE' or rig.mode == 'EDIT'):
        raise FingerprintUnknown('The dependency proof requires a local, unparented Pose Position FK rig.')
    if rig.constraints or getattr(rig, 'modifiers', ()):
        raise FingerprintUnknown('Object constraints/modifiers are outside the plain FK proof.')
    if rig.data.animation_data is not None:
        raise FingerprintUnknown('Armature-data animation/drivers are outside the plain FK proof.')
    ad = rig.animation_data
    if ad is not None and (ad.drivers or getattr(ad, 'use_tweak_mode', False)):
        raise FingerprintUnknown('Rig drivers/NLA Tweak Mode are outside the plain FK proof.')
    if any(bone.constraints for bone in rig.pose.bones):
        raise FingerprintUnknown('Pose constraints are outside the plain FK proof.')
    _plain_replace(action, export_range)
    _validate_transform_channels(action, rig, slot_handle)
    keyed = _enabled_channels(action, slot_handle)
    foreign = set()
    if ad is not None and ad.action is not None:
        other_handle = ad.action_slot.handle if ad.action.is_action_layered and ad.action_slot else 0
        if ad.action is not action or other_handle != slot_handle:
            _plain_replace(ad.action, ad.action.frame_range)
            _validate_transform_channels(ad.action, rig, other_handle)
            foreign = _enabled_channels(ad.action, other_handle)
    if ad is not None and ad.use_nla and any(not track.mute and any(not strip.mute for strip in track.strips)
                                            for track in ad.nla_tracks):
        raise FingerprintUnknown('Live NLA can drive unkeyed snapshot inputs; its dependencies are unproven.')
    # The worker derives its reference transform/origin from the snapshot object
    # matrix before sampling. Animated object transforms therefore need a fixed
    # snapshot policy; hashing their current evaluated values would vary per frame.
    if any(path in _TRANSFORM_SIZES for path, _index in keyed | foreign):
        raise FingerprintUnknown('Animated rig-object transforms need an explicit stable export reference policy.')
    poses = []
    for bone in rig.pose.bones:
        prefix = bone.path_from_id() + '.'
        poses.append({'name': bone.name,
                      'unkeyed': _unkeyed_transform(bone, prefix, keyed, foreign),
                      'settings': _rna_settings(bone, exclude=_POSE_EVALUATED | set(_TRANSFORM_SIZES) | {
                          'name', 'bone', 'parent', 'child', 'children', 'constraints', 'color', 'custom_shape',
                          'select', 'hide',
                          'custom_shape_transform', 'custom_shape_translation', 'custom_shape_rotation_euler',
                          'custom_shape_scale_xyz', 'custom_shape_wire_width', 'use_custom_shape_bone_size',
                          'motion_path', 'rigify_type', 'rigify_parameters'})})
    bones = []
    for bone in rig.data.bones:
        bones.append({'name': bone.name, 'parent': bone.parent.name if bone.parent else None,
                      'settings': _rna_settings(bone, exclude={'name', 'parent', 'children',
                          'collections', 'color', 'select', 'select_head', 'select_tail', 'hide', 'hide_select'}),
                      'export_ownership': {field: _plain(bone.get(field)) for field in (
                          'character_designer_owner', 'character_designer_skirt_owner')}})
    return {'object_transform': _unkeyed_transform(rig, '', set(), foreign, object_block=True),
            'export_ownership': {field: _plain(rig.get(field)) for field in (
                'character_designer_skirt_owner', 'character_designer_hair_bones_owner',
                'character_designer_hair_variant_version')},
            'rest_bones': sorted(bones, key=lambda item: item['name']),
            'pose_inputs': sorted(poses, key=lambda item: item['name']),
            'armature_settings': _rna_settings(rig.data, exclude=_ID_METADATA | {
                'bones', 'edit_bones', 'collections', 'collections_all', 'animation_data',
                'active', 'show_names', 'show_axes', 'axes_position', 'display_type',
                'show_bone_custom_shapes', 'show_group_colors', 'show_bone_colors',
                'relation_line_position', 'use_mirror_x', 'is_editmode'})}


def collect_native_payload(action, rig, scene, slot_handle, *, timing=None):
    """Collect without switching Actions; incomplete dependencies raise Unknown.

    ``timing`` may explicitly supply frame_start/end, fps/base, sample_rate,
    unit_scale and loop from the verified Link policy. It must contain exactly
    those fields. Omitting it uses the same Action/scene defaults as Link Sync.
    Callers must keep their Link/model provenance in the surrounding receipt.
    """
    action_payload = collect_action_payload(action, slot_handle)
    if timing is None:
        start, end = action.frame_range
        timing = {'frame_start': float(start), 'frame_end': float(end),
                  'fps': scene.render.fps, 'fps_base': scene.render.fps_base,
                  'sample_rate': action.get('unity_sample_rate', scene.render.fps / scene.render.fps_base),
                  'unit_scale': scene.unit_settings.scale_length,
                  'loop': action.get('unity_loop_time', False)}
    required = {'frame_start', 'frame_end', 'fps', 'fps_base', 'sample_rate', 'unit_scale', 'loop'}
    if type(timing) is not dict or set(timing) != required:
        raise FingerprintUnknown('Explicit export timing must contain exactly the supported fields.')
    rig_payload = _rig_payload(action, rig, slot_handle,
                               (timing['frame_start'], timing['frame_end']))
    return {'schema': SCHEMA, 'action': action_payload, 'rig': rig_payload,
            'export': _plain(timing), 'proof': {'policy': PROOF_POLICY, 'complete': True}}


def fingerprint_native(action, rig, scene, slot_handle, *, timing=None):
    """Return known/full hash or conservative Unknown; never mutate native data."""
    motion = fingerprint_action(action, slot_handle)
    if not motion['fingerprint_known']:
        return motion
    try:
        result = fingerprint_serialized(collect_native_payload(action, rig, scene, slot_handle, timing=timing))
        return result
    except (FingerprintUnknown, AttributeError, ReferenceError, RuntimeError,
            TypeError, ValueError, ZeroDivisionError) as exc:
        return _result(False, str(exc), action_fingerprint=motion['action_fingerprint'])
