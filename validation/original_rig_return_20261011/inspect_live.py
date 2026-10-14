"""Read-only artist-state and original control graph inspection."""
import bpy
import hashlib
import json
import sys
from pathlib import Path
from character_designer import limb_ik, limb_ik_fk, unity_animation, body_original_mode, forearm_original_inventory

OUT = Path(r'D:\Blender\Projects\Character\X\validation\original_rig_return_20261011')
OUT.mkdir(parents=True, exist_ok=True)
PACKET = Path(r'D:\Blender\Projects\Character\Animation\UnityExports\CharacterTuning\20261009-233830-d8fa2427ba96\Cosha_Walk_N.cdanim.json')

def signature():
    rigs = []
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            rigs.append((obj.name, obj.data.name,
                         [list(v for row in b.matrix_local for v in row) for b in obj.data.bones],
                         [list(v for row in p.matrix_basis for v in row) for p in obj.pose.bones],
                         obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None))
    state = [bpy.data.filepath, bpy.data.is_dirty, bpy.context.scene.name,
             bpy.context.scene.frame_current, bpy.context.scene.frame_subframe,
             bpy.context.object.name if bpy.context.object else None,
             bpy.context.object.mode if bpy.context.object else None,
             sorted(o.name for o in bpy.context.selected_objects), rigs,
             sorted(o.name for o in bpy.data.objects), sorted(a.name for a in bpy.data.actions)]
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()

before = signature()
rig = bpy.data.objects['CoshaRig']
result = {'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
          'scene': bpy.context.scene.name, 'frame': bpy.context.scene.frame_current,
          'object': bpy.context.object.name if bpy.context.object else None,
          'mode': bpy.context.object.mode if bpy.context.object else None,
          'blender_version': bpy.app.version_string,
          'addon_version': sys.modules['character_designer'].bl_info['version'],
          'addon_path': sys.modules['character_designer'].__file__,
          'module_sha256': {m.__name__: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
                            for m in (limb_ik, limb_ik_fk, unity_animation)},
          'scenes': [], 'switches': [], 'constraints': [], 'drivers': []}
for scene in bpy.data.scenes:
    settings = {}
    for prop in scene.bl_rna.properties:
        if 'character' not in prop.identifier.lower() and not prop.identifier.startswith('cd_'):
            continue
        value = getattr(scene, prop.identifier, None)
        if hasattr(value, 'bl_rna') and not isinstance(value, bpy.types.ID):
            settings[prop.identifier] = {p.identifier: (v.name if isinstance(v, bpy.types.ID) else str(v))
                for p in value.bl_rna.properties if 'rig' in p.identifier
                for v in [getattr(value, p.identifier, None)]}
    result['scenes'].append({'name': scene.name, 'unit_scale': scene.unit_settings.scale_length,
                            'rigs': [o.name for o in scene.objects if o.type == 'ARMATURE'], 'settings': settings})
for pb in rig.pose.bones:
    if limb_ik_fk.PROPERTY in pb or limb_ik_fk.VERSION_KEY in pb.bone:
        result['switches'].append({'bone': pb.name, 'ik_fk': pb.get(limb_ik_fk.PROPERTY),
                                  'version': pb.bone.get(limb_ik_fk.VERSION_KEY)})
    raw = pb.get(limb_ik.CONSTRAINT_REGISTRY_KEY)
    try:
        registry = json.loads(raw) if raw else None
    except Exception:
        registry = raw
    for c in pb.constraints:
        result['constraints'].append({'bone': pb.name, 'name': c.name, 'type': c.type,
                                      'mute': c.mute, 'influence': c.influence,
                                      'target': c.target.name if getattr(c, 'target', None) else None,
                                      'subtarget': getattr(c, 'subtarget', None),
                                      'registry': registry})
if rig.animation_data:
    for f in rig.animation_data.drivers:
        result['drivers'].append({'path': f.data_path, 'index': f.array_index, 'mute': f.mute,
            'valid': f.is_valid, 'expression': f.driver.expression,
            'variables': [{'name': v.name, 'type': v.type, 'targets': [
                {'id': t.id.name if t.id else None, 'path': t.data_path, 'bone': t.bone_target}
                for t in v.targets]} for v in f.driver.variables]})
data = unity_animation.load_package(PACKET)
result['original_mode'] = {'active': body_original_mode.active(rig)}
if body_original_mode.active(rig):
    saved_original = json.loads(rig[body_original_mode.SESSION])
    result['original_mode']['saved_muted_constraint_count'] = len(saved_original['constraints'])
    try:
        rest = body_original_mode._validate_session_rest(rig, saved_original)
        inventory = forearm_original_inventory.validate(rig)
        result['original_mode'].update({'rest_unchanged': True, 'native_rest_bones': len(rest),
            'complete_owned_inventory_valid': True, 'limbs': len(inventory['rigs'])})
    except Exception as exc:
        result['original_mode'].update({'validated': False, 'error_type': type(exc).__name__, 'error': str(exc)})
try:
    mapping = unity_animation._mapping(rig, data, bpy.data.scenes['Scene'].unit_settings.scale_length)
    result['mapping'] = {'compatible': True, 'bones': len(mapping.indices), 'error_mm': mapping.error_metres * 1000}
except Exception as exc:
    result['mapping'] = {'compatible': False, 'error_type': type(exc).__name__, 'error': str(exc)}
result['state_unchanged'] = signature() == before
result['state_signature'] = before
(OUT / 'live_control_graph.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: result[k] for k in ('filepath', 'dirty', 'scene', 'frame', 'object', 'mode',
    'blender_version', 'addon_version', 'addon_path', 'scenes', 'switches', 'original_mode', 'mapping', 'state_unchanged')} |
    {'constraint_count': len(result['constraints']), 'driver_count': len(result['drivers']),
     'muted_constraints': [{'bone': c['bone'], 'name': c['name'], 'influence': c['influence']} for c in result['constraints'] if c['mute']]}, ensure_ascii=False))
