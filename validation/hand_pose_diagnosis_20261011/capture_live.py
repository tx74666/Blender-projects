"""Read the current artist pose; never assign channels, frames or scene data."""
import bpy
import json
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\validation\hand_pose_diagnosis_20261011\current_full.json')
def mat(value):
    return [[float(v) for v in row] for row in value]
scene = bpy.context.scene
rig = bpy.context.object
assert rig and rig.type == 'ARMATURE', 'The current object must be the artist-selected rig.'
ad = rig.animation_data
action = ad.action if ad else None
deps = bpy.context.evaluated_depsgraph_get()
er = rig.evaluated_get(deps)
result = {'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
          'scene': scene.name, 'frame': scene.frame_current, 'subframe': scene.frame_subframe,
          'rig': rig.name, 'mode': rig.mode, 'data': rig.data.name,
          'selected': [o.name for o in bpy.context.selected_objects],
          'selected_bones': [p.name for p in (bpy.context.selected_pose_bones or [])],
          'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
          'action': action.name if action else None, 'bone_count': len(rig.data.bones),
          'rig_world': mat(rig.matrix_world), 'bone_rows': {}, 'meshes': {}, 'action_curves': [],
          'nla': [], 'server_port': getattr(getattr(bpy.types,'blendermcp_server',None),'port',None),
          'all_bones': {b.name:{'rest':mat(b.matrix_local),'pose':mat(er.pose.bones[b.name].matrix),
                       'parent':b.parent.name if b.parent else None,'deform':b.use_deform} for b in rig.data.bones}}
for p in rig.pose.bones:
    if any(s in p.name.lower() for s in ('thumb','f_index','f_middle','f_ring','f_pinky','hand.','eye.')):
        e = er.pose.bones[p.name]
        b = p.bone
        result['bone_rows'][p.name] = {'parent': b.parent.name if b.parent else None,
            'length': b.length, 'head': list(b.head_local), 'tail': list(b.tail_local),
            'rest': mat(b.matrix_local), 'pose': mat(e.matrix), 'basis': mat(p.matrix_basis),
            'location': list(p.location), 'scale': list(p.scale), 'rotation_mode': p.rotation_mode,
            'quaternion': list(p.rotation_quaternion), 'euler': list(p.rotation_euler),
            'constraints': [{'name': c.name, 'type': c.type, 'influence': c.influence, 'mute': c.mute} for c in p.constraints]}
for o in scene.objects:
    mods = [m for m in o.modifiers if m.type == 'ARMATURE' and m.object == rig]
    if o.type != 'MESH' or not mods:
        continue
    groups = {g.index:g.name for g in o.vertex_groups}
    eo = o.evaluated_get(deps)
    row = {'world':mat(o.matrix_world), 'evaluated_world':mat(eo.matrix_world),
           'vertices':len(o.data.vertices),'evaluated_vertices':len(eo.data.vertices),
           'modifiers':[{'name':m.name,'type':m.type,'visible':m.show_viewport,
                         'preserve_volume':getattr(m,'use_deform_preserve_volume',None),
                         'object':getattr(getattr(m,'object',None),'name',None)} for m in o.modifiers],
           'hand_vertices':[], 'shape_keys':[]}
    for v in o.data.vertices:
        weights = {groups[g.group]:float(g.weight) for g in v.groups if g.weight>1e-8 and g.group in groups}
        if not any(('thumb' in n.lower() or 'f_' in n.lower() or 'hand.' in n.lower()) for n in weights):
            continue
        row['hand_vertices'].append({'index':v.index,'base':list(v.co),'weights':weights,
            'evaluated':list(eo.data.vertices[v.index].co) if len(o.data.vertices)==len(eo.data.vertices) else None})
    if o.data.shape_keys:
        row['shape_keys']=[{'name':k.name,'value':k.value,'mute':k.mute} for k in o.data.shape_keys.key_blocks]
    result['meshes'][o.name]=row
if ad:
    result['nla']=[{'name':t.name,'mute':t.mute,'strips':len(t.strips)} for t in ad.nla_tracks]
    result['action_blend']={'use_nla':ad.use_nla,'blend':ad.action_blend_type,'influence':ad.action_influence}
def read_curves(a):
    curves=[]
    legacy=getattr(a,'fcurves',None)
    if legacy is not None: curves.extend(legacy)
    for layer in getattr(a,'layers',[]):
        for strip in layer.strips:
            for bag in getattr(strip,'channelbags',[]): curves.extend(bag.fcurves)
    rows=[]
    for c in curves:
        if any(s in c.data_path.lower() for s in ('thumb','f_index','f_middle','f_ring','f_pinky')):
            rows.append({'path':c.data_path,'index':c.array_index,'mute':c.mute,
                'value':c.evaluate(scene.frame_current+scene.frame_subframe),'keys':len(c.keyframe_points)})
    return rows
if action:
    result['action_curves']=read_curves(action)
    result['action_metadata']={k:str(action[k]) for k in action.keys() if any(s in k.lower() for s in ('package','link','source','unity','slot'))}
worklist=getattr(scene,'character_designer_animation_worklist',None)
if worklist:
    result['worklist']={'active_index':worklist.active_index,'items':[]}
    for item in worklist.items:
        result['worklist']['items'].append({'name':item.name,'rig':item.rig.name if item.rig else None,
            'source':item.source_action.name if item.source_action else None,
            'custom':item.custom_action.name if item.custom_action else None,'side':item.side,
            'source_curves':read_curves(item.source_action) if item.source_action else []})
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'scene':result['scene'],'frame':result['frame'],'action':result['action'],
                  'bones':len(result['bone_rows']),'meshes':{n:len(v['hand_vertices']) for n,v in result['meshes'].items()}},ensure_ascii=False))
