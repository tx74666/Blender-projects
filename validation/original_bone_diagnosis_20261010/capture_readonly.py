"""Read current Cosha armatures without changing scene, pose, or model data."""
import bpy
import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone

OUT = Path(r'D:\Blender\Projects\Character\X\validation\original_bone_diagnosis_20261010\live_readonly.json')
def vec(v):
    return [float(x) for x in v]
def mat(m):
    return [[float(x) for x in row] for row in m]
def scalar_props(obj):
    result = {}
    for key in obj.keys():
        value = obj[key]
        if isinstance(value, (str, int, float, bool)):
            result[key] = value if not isinstance(value, str) or len(value) <= 500 else '<long saved record>'
    return result
def bone_record(rig, bone):
    pb = rig.pose.bones.get(bone.name)
    return {'parent': bone.parent.name if bone.parent else None,
            'head': vec(bone.head_local), 'tail': vec(bone.tail_local), 'length': float(bone.length),
            'rest': mat(bone.matrix_local), 'world_rest': mat(rig.matrix_world @ bone.matrix_local),
            'use_connect': bool(bone.use_connect), 'use_deform': bool(bone.use_deform),
            'inherit_scale': bone.inherit_scale, 'props': scalar_props(bone),
            'basis': mat(pb.matrix_basis), 'pose': mat(pb.matrix),
            'location': vec(pb.location), 'scale': vec(pb.scale),
            'rotation_mode': pb.rotation_mode, 'rotation_quaternion': vec(pb.rotation_quaternion),
            'rotation_euler': vec(pb.rotation_euler),
            'shape': pb.custom_shape.name if pb.custom_shape else None,
            'constraints': [{'name': c.name, 'type': c.type, 'mute': bool(c.mute),
                             'influence': float(c.influence),
                             'target': getattr(c, 'target', None).name if getattr(c, 'target', None) else None,
                             'subtarget': getattr(c, 'subtarget', None)} for c in pb.constraints]}

data = {'captured_utc': datetime.now(timezone.utc).isoformat(), 'blender': bpy.app.version_string,
        'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
        'current_scene': bpy.context.scene.name, 'mode': bpy.context.mode,
        'active': bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
        'selected': [o.name for o in bpy.context.selected_objects],
        'scenes': [{'name': s.name, 'frame': s.frame_current,
                    'armatures': [o.name for o in s.objects if o.type == 'ARMATURE'],
                    'meshes': [o.name for o in s.objects if o.type == 'MESH']} for s in bpy.data.scenes],
        'armatures': {}, 'meshes': {}}
rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE' and 'cosha' in o.name.lower()]
for rig in rigs:
    names = [b.name for b in rig.data.bones if any(term in b.name.lower() for term in ('thumb', 'eye')) or b.name in {'Head', 'Hips', 'Root', 'hand.L', 'hand.R', 'forearm.L', 'forearm.R'}]
    action = rig.animation_data.action if rig.animation_data else None
    data['armatures'][rig.name] = {
        'data': rig.data.name, 'data_users': rig.data.users, 'matrix_world': mat(rig.matrix_world),
        'object_scale': vec(rig.scale), 'object_rotation': vec(rig.rotation_euler),
        'pose_position': rig.data.pose_position, 'bone_count': len(rig.data.bones),
        'action': action.name if action else None, 'props': scalar_props(rig),
        'animation_drivers': [{'path': d.data_path, 'mute': d.mute} for d in rig.animation_data.drivers] if rig.animation_data else [],
        'bones': {n: bone_record(rig, rig.data.bones[n]) for n in names}}
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    armatures = [m.object for m in obj.modifiers if m.type == 'ARMATURE' and m.object in rigs]
    if not armatures or not obj.name.lower().startswith('cosha'):
        continue
    rig = armatures[0]
    group_names = {g.index: g.name for g in obj.vertex_groups}
    thumb_ids = {i for i, n in group_names.items() if 'thumb' in n.lower()}
    vertices = []
    for v in obj.data.vertices:
        if any(g.group in thumb_ids and g.weight > 0.00001 for g in v.groups):
            vertices.append({'index': v.index, 'co': vec(v.co),
                             'weights': {group_names[g.group]: float(g.weight) for g in v.groups if g.weight > 0.00001}})
    data['meshes'][obj.name] = {
        'data': obj.data.name, 'data_users': obj.data.users, 'vertices': len(obj.data.vertices),
        'matrix_world': mat(obj.matrix_world), 'rig': rig.name,
        'rig_relative': mat(rig.matrix_world.inverted() @ obj.matrix_world),
        'props': scalar_props(obj),
        'modifiers': [{'name': m.name, 'type': m.type, 'visible': m.show_viewport,
                       'object': m.object.name if m.type == 'ARMATURE' and m.object else None,
                       'vertex_groups': m.use_vertex_groups if m.type == 'ARMATURE' else None,
                       'envelopes': m.use_bone_envelopes if m.type == 'ARMATURE' else None} for m in obj.modifiers],
        'shape_keys': [{'name': k.name, 'value': float(k.value)} for k in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else [],
        'thumb_vertices': vertices}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'path': str(OUT), 'scene': data['current_scene'],
                  'scenes': [s['name'] for s in data['scenes']],
                  'rigs': list(data['armatures']),
                  'meshes': {n: {'vertices': d['vertices'], 'thumb_vertices': len(d['thumb_vertices'])} for n, d in data['meshes'].items()}}, ensure_ascii=False))
