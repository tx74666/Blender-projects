import bpy,json
from pathlib import Path
C=bpy.context
C.view_layer.update()
obj=bpy.data.objects['Cosha']
obj.update_from_editmode()
rig=bpy.data.objects['CoshaRig']
report={'bones':[],'modifiers':[],'fingers':{},'creases':{}}
for bone in rig.pose.bones:
    difference=max(abs(a-b) for aa,bb in zip(bone.matrix,bone.bone.matrix_local) for a,b in zip(aa,bb))
    if difference>1e-6:
        report['bones'].append(dict(name=bone.name,difference=difference,deform=bone.bone.use_deform,
            basis=[list(row) for row in bone.matrix_basis]))
for m in obj.modifiers:
    if m.type=='ARMATURE': report['modifiers'].append({name:getattr(m,name,None) for name in ('name','use_vertex_groups','use_bone_envelopes','use_deform_preserve_volume','use_multi_modifier','vertex_group','invert_vertex_group')})
for key,candidate in json.loads(obj.character_designer_finger_bank.survey)['candidates'].items():
    indices=set(candidate['vertices'])
    groups={obj.vertex_groups[g.group].name for i in indices for g in obj.data.vertices[i].groups if g.weight>1e-7}
    report['fingers'][key]={'groups':sorted(groups),'nonneutral':[b for b in report['bones'] if b['name'] in groups]}
for name in ('crease_edge','crease_vert'):
    attr=obj.data.attributes.get(name)
    report['creases'][name]=max((v.value for v in attr.data),default=0) if attr else 0
Path(r'D:\Blender\Projects\Character\X\outputs\topology_subdivision_20260921\live_pose.json').write_text(json.dumps(report,indent=2),encoding='utf8')
