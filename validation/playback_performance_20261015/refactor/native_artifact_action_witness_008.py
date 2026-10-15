"""Portable stored Action/animation content; no native writes or evaluation.

Only ID bookkeeping and native pointer addresses are excluded. ID references
use serialized type/name/absolute-library identity. Large curve payloads stay
in memory; the returned receipt contains content hashes and explicit scope.
"""
import hashlib
import json
import math

SCHEMA = 'x.artifact-portable-animation/1'
BOOKKEEPING = frozenset(('rna_type', 'id_data', 'original', 'is_evaluated', 'users', 'tag',
                        'is_updated', 'is_updated_data', 'is_updated_transform', 'session_uid'))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def identity(value):
    import bpy
    if value is None:
        return None
    require(isinstance(value, bpy.types.ID), 'Portable animation reference must be a native ID')
    library = value.library
    result = (type(value).__name__, value.name_full,
              bpy.path.abspath(library.filepath) if library is not None else None)
    if getattr(value, 'is_embedded_data', False):
        owners = []
        for collection in (bpy.data.scenes, bpy.data.materials, bpy.data.worlds):
            for owner in collection:
                for attribute in ('collection', 'node_tree'):
                    candidate = getattr(owner, attribute, None)
                    if candidate is not None and candidate.as_pointer() == value.as_pointer():
                        owners.append((identity(owner), attribute))
        require(len(owners) == 1, 'Embedded animation ID reference needs one known owner/attribute')
        return ('embedded', owners[0], result)
    return result


def plain(value):
    import bpy
    if value is None or type(value) in (bool, int, str):
        return value
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite portable animation content')
        return ('float', value.hex())
    if isinstance(value, bpy.types.ID):
        return ('native_ID', identity(value))
    if hasattr(value, 'items'):
        return tuple((str(key), plain(item)) for key, item in value.items())
    if isinstance(value, (set, frozenset)):
        return ('set', tuple(sorted(plain(item) for item in value)))
    try:
        return tuple(plain(item) for item in value)
    except TypeError as error:
        raise RuntimeError('Unsupported portable animation value: ' + type(value).__name__) from error


def props(value):
    try:
        keys = tuple(value.keys())
    except AttributeError:
        return ('no-ID-properties-api',)
    except TypeError as error:
        require(str(error) == "bpy_struct.keys(): this type doesn't support IDProperties",
                'Unexpected native ID-properties failure')
        return ('native-no-ID-properties',)
    return tuple((str(key), plain(value[key])) for key in keys)


def state(value):
    return (tuple((prop.identifier, plain(getattr(value, prop.identifier)))
                  for prop in value.bl_rna.properties if prop.identifier not in BOOKKEEPING
                  and prop.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}), props(value))


def curve(value):
    driver = value.driver
    driver_state = None if driver is None else (state(driver), tuple(
        (state(variable), tuple((state(target), identity(target.id)) for target in variable.targets))
        for variable in driver.variables))
    group = value.group
    group_state = None if group is None else (state(group), state(group.colors))
    return (state(value), group_state,
            tuple(state(point) for point in value.keyframe_points),
            tuple(state(point) for point in value.sampled_points),
            tuple((state(modifier), tuple(state(point) for point in getattr(modifier, 'control_points', ())))
                  for modifier in value.modifiers), driver_state)


def action(value):
    if value.is_action_legacy:
        require(getattr(value, 'is_empty', False) is True, 'Only explicitly empty legacy Actions are supported')
    return (identity(value), state(value), tuple(state(slot) for slot in value.slots),
            tuple((state(layer), tuple((state(strip), tuple(
                (state(bag), bag.slot_handle,
                 tuple((state(group), state(group.colors)) for group in bag.groups),
                 tuple(curve(item) for item in bag.fcurves)) for bag in strip.channelbags))
                for strip in layer.strips)) for layer in value.layers),
            tuple((state(marker), identity(getattr(marker, 'camera', None)))
                  for marker in getattr(value, 'pose_markers', ())))


def nla_strip(strip):
    slot = strip.action_slot
    return (state(strip), identity(strip.action), state(slot) if slot is not None else None,
            tuple(curve(item) for item in strip.fcurves),
            tuple((state(modifier), tuple(state(point) for point in getattr(modifier, 'control_points', ())))
                  for modifier in strip.modifiers),
            tuple(nla_strip(child) for child in getattr(strip, 'strips', ())))


def animation(value):
    ad = value.animation_data
    if ad is None:
        return None
    require(not ad.use_tweak_mode and getattr(ad, 'action_tweak_storage', None) is None,
            'Portable preview proof does not support active or stored NLA tweak sessions')
    slot = ad.action_slot
    return (state(ad), identity(ad.action), state(slot) if slot is not None else None,
            tuple(curve(item) for item in ad.drivers),
            tuple((state(track), tuple(nla_strip(strip) for strip in track.strips))
                  for track in ad.nla_tracks))


def referenced_actions(owner):
    ad = owner.animation_data
    if ad is None:
        return ()
    result = [ad.action] if ad.action is not None else []
    def visit(strip):
        if strip.action is not None:
            result.append(strip.action)
        for child in getattr(strip, 'strips', ()):
            visit(child)
    for track in ad.nla_tracks:
        for strip in track.strips:
            visit(strip)
    return tuple(result)


def capture(scene, actions):
    """Hash exact Actions plus stored Scene/Rig animation and clip settings."""
    actions = tuple(sorted(actions, key=lambda item: item.name_full))
    require(len({identity(item) for item in actions}) == len(actions), 'Duplicate Action identity')
    require(len({item.name_full for item in actions}) == len(actions), 'Ambiguous same-name Actions are unsupported')
    owners = (scene,) + tuple(item for item in scene.objects if item.type == 'ARMATURE')
    declared = {identity(item) for item in actions}
    require(all(identity(action_id) in declared for owner in owners for action_id in referenced_actions(owner)),
            'Scene/Rig active or nested NLA Action is outside the explicitly witnessed Action set')
    action_hashes = {item.name_full: digest(action(item)) for item in actions}
    controls = {type(scene).__name__ + ':' + scene.name_full: digest(animation(scene))}
    for rig in sorted((item for item in scene.objects if item.type == 'ARMATURE'), key=lambda item: item.name_full):
        controls[type(rig).__name__ + ':' + rig.name_full] = digest(animation(rig))
    clip = {'frame_start': scene.frame_start, 'frame_end': scene.frame_end,
            'frame_preview_start': scene.frame_preview_start, 'frame_preview_end': scene.frame_preview_end,
            'use_preview_range': scene.use_preview_range, 'fps': scene.render.fps,
            'fps_base': float(scene.render.fps_base).hex(), 'units': state(scene.unit_settings)}
    content = {'actions': action_hashes, 'controls': controls, 'clip': clip}
    return {'schema': SCHEMA, 'sha256': digest(content), **content,
            'scope': {'native_pointer_addresses': False, 'native_ID_identity': 'serialized type/name/absolute library path',
                      'excluded_bookkeeping': sorted(BOOKKEEPING),
                      'stored_curve_group_points_handles_modifiers_drivers_layers_slots_custom_properties': True,
                      'scene_and_rig_active_action_slot_animation_and_clip_settings': True}}
