import bpy,json,os
from pathlib import Path
assert os.getpid()==27676
assert Path(bpy.data.filepath).resolve()==Path('D:/Blender/Projects/Character/X/X.blend').resolve()
a=bpy.data.actions.get('Pose')
assert a is not None and a.library is None
curves=[]
if a.is_action_layered:
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    curves.append({'data_path':curve.data_path,'array_index':curve.array_index,'keys':len(curve.keyframe_points),'sampled_points':len(curve.sampled_points)})
else:
    curves=[{'data_path:c.data_path,'array_index':c.array_index,'keys':len(c.keyframe_points),'sampled_points':len(c.sampled_points)} for c in a.fcurves]
refs=[]
for ob in bpy.data.objects:
    ad=ob.animation_data
    if not ad: continue
    if ad.action==a: refs.append({'object':ob.name,'active_action':True})
    for track in ad.nla_tracks:
        for strip in track.strips:
            if strip.action==a: refs.append({'object':ob.name,'track':track.name,'strip':strip.name})
report={'schema':'x.validation.original-Pose-readonly/1','completed':True,'pid':os.getpid(),'filepath':bpy.data.filepath,
    'Pose':{'name':a.name,'users':a.users,'fake_user':a.use_fake_user,'is_asset':a.asset_data is not None,
        'is_action_layered':a.is_action_layered,'layers':len(a.layers),'custom_property_keys':list(a.keys()),
        'slots':[{'handle':s.handle,'identifier':s.identifier,'name_display':s.name_display} for s in a.slots],
        'curves':curves,'object_Action_NLA_references':refs},'dirty':bpy.data.is_dirty,'frame':bpy.context.scene.frame_current,
    'mutations':0,'artist_saved':False}
out=Path("D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_pose_metadata_01/original_pose_metadata.json")
with out.open('x',encoding='utf-8') as stream: stream.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'completed':True,'Pose_users':a.users,'fake_user':a.use_fake_user,'curves':len(curves)},ensure_ascii=True))
