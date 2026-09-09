import bpy, json, hashlib
from pathlib import Path
SOURCE=Path(r'D:\Blender Samples\Characters\Rain v3.3\rain_v3.2.blend')
REPORT=Path(r'D:\Blender\Projects\Character\X\outputs\rig\audit_rain_spine_readonly.json')
before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
report={'armatures':[]}
for obj in bpy.data.objects:
    if obj.type!='ARMATURE': continue
    picked=set(pb.name for pb in obj.pose.bones if any(word in pb.name.lower() for word in ('spine','torso','chest','hip','pelvis','rib')))
    # Include direct constraint relations, then their ancestors, for this bounded inventory.
    for pb in list(obj.pose.bones):
        if pb.name in picked:
            for c in pb.constraints:
                if getattr(c,'target',None)==obj and getattr(c,'subtarget',''): picked.add(c.subtarget)
    for name in list(picked):
        picked.update(pb.name for pb in obj.pose.bones[name].parent_recursive)
    bones=[]
    for pb in obj.pose.bones:
        if pb.name not in picked: continue
        cons=[]
        for c in pb.constraints:
            fields={}
            for prop in ('target','subtarget','pole_target','pole_subtarget','pole_angle','chain_count','influence','mute','mix_mode','target_space','owner_space','use_tail','use_stretch','use_rotation','use_location','track_axis','y_scale_mode','xz_scale_mode','use_original_scale'):
                if hasattr(c,prop):
                    v=getattr(c,prop)
                    fields[prop]=getattr(v,'name',v)
            cons.append({'name':c.name,'type':c.type,**fields})
        bones.append({'name':pb.name,'parent':pb.parent.name if pb.parent else None,'deform':pb.bone.use_deform,'hide':pb.bone.hide,'collections':[c.name for c in pb.bone.collections], 'location':list(pb.location),'rotation_mode':pb.rotation_mode,'rotation_euler':list(pb.rotation_euler),'scale':list(pb.scale),'locks':{'location':list(pb.lock_location),'rotation':list(pb.lock_rotation),'scale':list(pb.lock_scale)},'props':{k:str(pb[k]) for k in pb.keys()},'custom_shape':pb.custom_shape.name if pb.custom_shape else None,'constraints':cons})
    drivers=[]
    if obj.animation_data:
        for f in obj.animation_data.drivers:
            if any('pose.bones["'+name+'"]' in f.data_path for name in picked):
                drivers.append({'path':f.data_path,'index':f.array_index,'expression':f.driver.expression,'variables':[{'name':v.name,'type':v.type,'targets':[{'id':t.id.name if t.id else None,'bone_target':t.bone_target,'data_path':t.data_path,'transform_type':t.transform_type,'transform_space':t.transform_space} for t in v.targets]} for v in f.driver.variables]})
    report['armatures'].append({'name':obj.name,'total_bones':len(obj.data.bones),'picked_bones':bones,'drivers':drivers})
report['curve_objects']=[{'name':o.name,'type':o.type,'modifiers':[m.type for m in o.modifiers],'parent':o.parent.name if o.parent else None} for o in bpy.data.objects if o.type=='CURVE']
report['texts']=[{'name':t.name,'spine_mentions':[l.body for l in t.lines if any(w in l.body.lower() for w in ('spine','torso','ik/fk','ik_fk'))][:80]} for t in bpy.data.texts]
report['saved']=False
report['source_unchanged']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RAIN_SPINE_AUDIT',json.dumps({'armatures':[(a['name'],a['total_bones'],len(a['picked_bones'])) for a in report['armatures']],'curves':report['curve_objects'],'source_unchanged':report['source_unchanged']}),flush=True)
