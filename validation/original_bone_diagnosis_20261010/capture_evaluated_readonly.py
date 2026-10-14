import bpy
import json
from pathlib import Path

folder = Path(r'D:\Blender\Projects\Character\X\validation\original_bone_diagnosis_20261010')
initial = json.loads((folder / 'live_readonly.json').read_text(encoding='utf-8'))
rig = bpy.data.objects['CoshaRig.001']
obj = bpy.data.objects['Cosha.001']
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated_rig = rig.evaluated_get(depsgraph)
evaluated_obj = obj.evaluated_get(depsgraph)
def mat(m):
    return [[float(v) for v in row] for row in m]
result = {'current_scene': bpy.context.scene.name, 'frame': bpy.context.scene.frame_current,
          'active': bpy.context.view_layer.objects.active.name,
          'selected': [o.name for o in bpy.context.selected_objects], 'dirty': bpy.data.is_dirty,
          'base_vertices': len(obj.data.vertices), 'evaluated_vertices': len(evaluated_obj.data.vertices),
          'mesh_matrix_world': mat(evaluated_obj.matrix_world),
          'rig_matrix_world': mat(evaluated_rig.matrix_world), 'bones': {}, 'thumb_vertices': [],
          'armature_modifiers': [], 'source_forearm_key_deltas': {}, 'action_curves': [], 'nla': []}
for b in rig.data.bones:
    pb = evaluated_rig.pose.bones[b.name]
    result['bones'][b.name] = {'rest': mat(b.matrix_local), 'pose': mat(pb.matrix),
                              'deform': b.use_deform, 'parent': b.parent.name if b.parent else None}
if result['base_vertices'] == result['evaluated_vertices']:
    for v in initial['meshes']['Cosha.001']['thumb_vertices']:
        result['thumb_vertices'].append({'index': v['index'],
                                         'co': list(evaluated_obj.data.vertices[v['index']].co)})
for m in obj.modifiers:
    if m.type == 'ARMATURE':
        result['armature_modifiers'].append({'name': m.name, 'object': m.object.name if m.object else None,
                                             'preserve_volume': m.use_deform_preserve_volume,
                                             'vertex_groups': m.use_vertex_groups, 'envelopes': m.use_bone_envelopes})
source = bpy.data.objects['Cosha']
if source.data.shape_keys:
    basis = source.data.shape_keys.key_blocks['Basis']
    ids = [v['index'] for v in initial['meshes']['Cosha']['thumb_vertices']]
    for key in source.data.shape_keys.key_blocks:
        if 'Forearm' in key.name:
            result['source_forearm_key_deltas'][key.name] = {'value': key.value,
                 'max_thumb_delta': max(((key.data[i].co - basis.data[i].co).length for i in ids), default=0.0)}
animation = rig.animation_data
if animation and animation.action:
    action = animation.action
    curves = []
    legacy = getattr(action, 'fcurves', None)
    if legacy is not None:
        curves.extend(legacy)
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', []):
                curves.extend(bag.fcurves)
    for curve in curves:
        if 'thumb' in curve.data_path.lower() and curve.data_path.endswith(('.scale', '.location')):
            values = [float(k.co[1]) for k in curve.keyframe_points]
            result['action_curves'].append({'path': curve.data_path, 'index': curve.array_index,
               'current': curve.evaluate(bpy.context.scene.frame_current), 'keys': len(values),
               'min': min(values) if values else None, 'max': max(values) if values else None})
    result['nla'] = [{'name': t.name, 'mute': t.mute,
                     'strips': [{'name': s.name, 'influence': s.influence,
                                 'action': s.action.name if s.action else None} for s in t.strips]} for t in animation.nla_tracks]
path = folder / 'evaluated_readonly.json'
path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'path': str(path), 'evaluated_vertices': result['evaluated_vertices'],
                  'thumb_vertices': len(result['thumb_vertices']),
                  'forearm_thumb_deltas': result['source_forearm_key_deltas'],
                  'thumb_scale_location_curves': len(result['action_curves']), 'nla_tracks': len(result['nla'])}, ensure_ascii=False))
