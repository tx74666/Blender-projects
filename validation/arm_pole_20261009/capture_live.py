import bpy
import hashlib
import json
import sys
from pathlib import Path

OUT = Path(r'D:\Blender\Projects\Character\X\validation\arm_pole_20261009')
OUT.mkdir(parents=True, exist_ok=True)

def plain(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bpy.types.ID):
        return {'id_type': type(value).__name__, 'name': value.name}
    if hasattr(value, 'keys'):
        return {str(k): plain(value[k]) for k in value.keys()}
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)

def props(owner):
    return {k: plain(owner[k]) for k in owner.keys()}

def constraints(pb):
    result = []
    for con in pb.constraints:
        item = {'name': con.name, 'type': con.type}
        for prop in con.bl_rna.properties:
            if prop.identifier in {'rna_type', 'name', 'type'} or prop.type == 'COLLECTION':
                continue
            try:
                item[prop.identifier] = plain(getattr(con, prop.identifier))
            except Exception as exc:
                item[prop.identifier] = {'error': str(exc)}
        result.append(item)
    return result

def bone(pb):
    db = pb.bone
    return {
        'name': pb.name, 'parent': pb.parent.name if pb.parent else None,
        'location': plain(pb.location), 'rotation_mode': pb.rotation_mode,
        'rotation_euler': plain(pb.rotation_euler),
        'rotation_quaternion': plain(pb.rotation_quaternion),
        'rotation_axis_angle': plain(pb.rotation_axis_angle), 'scale': plain(pb.scale),
        'matrix_basis': plain(pb.matrix_basis), 'matrix': plain(pb.matrix),
        'head': plain(pb.head), 'tail': plain(pb.tail),
        'rest_matrix': plain(db.matrix_local), 'rest_head': plain(db.head_local),
        'rest_tail': plain(db.tail_local), 'use_connect': db.use_connect,
        'inherit_scale': db.inherit_scale, 'use_inherit_rotation': db.use_inherit_rotation,
        'use_local_location': db.use_local_location,
        'properties': props(pb), 'bone_properties': props(db),
        'constraints': constraints(pb),
    }

rig = bpy.data.objects.get('CoshaRig')
assert rig is not None and rig.type == 'ARMATURE'
data = {
    'artist': bpy.data.filepath, 'is_dirty': bpy.data.is_dirty,
    'blender': bpy.app.version_string, 'frame': bpy.context.scene.frame_current,
    'mode': bpy.context.mode, 'active_object': bpy.context.object.name if bpy.context.object else None,
    'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
    'selected': [pb.name for pb in rig.pose.bones if getattr(pb, 'select', getattr(pb.bone, 'select', False))],
    'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto,
    'rig_properties': props(rig), 'data_properties': props(rig.data),
    'scene_properties': props(bpy.context.scene),
    'rig_matrix_world': plain(rig.matrix_world),
    'bones': {pb.name: bone(pb) for pb in rig.pose.bones},
    'settings': {}, 'runtime': {}, 'actions': [],
}
for name in dir(bpy.context.scene):
    if name.startswith('character_designer'):
        setting = getattr(bpy.context.scene, name)
        if hasattr(setting, 'bl_rna'):
            data['settings'][name] = {}
            for p in setting.bl_rna.properties:
                if p.identifier != 'rna_type' and p.type not in {'COLLECTION', 'POINTER'}:
                    try:
                        data['settings'][name][p.identifier] = plain(getattr(setting, p.identifier))
                    except Exception:
                        pass
for name, mod in tuple(sys.modules.items()):
    if name == 'character_designer' or name.startswith('character_designer.limb_') or name in {
        'character_designer.body_original_mode', 'character_designer.control_pose_mirror',
        'character_designer.control_pose_assets', 'character_designer.skirt_wiggle_ui',
    }:
        path = getattr(mod, '__file__', None)
        data['runtime'][name] = {
            'path': path,
            'disk_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest() if path and Path(path).is_file() else None,
            'bl_info': plain(getattr(mod, 'bl_info', None)),
        }
for action in bpy.data.actions:
    data['actions'].append({'name': action.name, 'users': action.users, 'asset': action.asset_data is not None})
ad = rig.animation_data
data['animation'] = None if ad is None else {
    'action': ad.action.name if ad.action else None,
    'slot': getattr(getattr(ad, 'action_slot', None), 'identifier', None),
    'nla_tracks': [{'name': t.name, 'mute': t.mute, 'strips': [
        {'name': s.name, 'action': s.action.name if s.action else None, 'mute': s.mute,
         'frame_start': s.frame_start, 'frame_end': s.frame_end, 'influence': s.influence}
        for s in t.strips]} for t in ad.nla_tracks],
}
Path(globals().get('CAPTURE_OUTPUT_PATH', OUT / 'live_before.json')).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('ARM_POLE_READ_ONLY_CAPTURE_OK', data['active_bone'], data['frame'], data['animation'])
