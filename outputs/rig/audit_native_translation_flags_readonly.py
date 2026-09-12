import sys,json
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import bpy
import character_designer
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend')
rig=bpy.data.objects['CoshaRig']
roles=[]
for pb in rig.pose.bones:
    b=pb.bone
    collections=[c.name for c in b.collections]
    if pb.name not in ('Hips','UpperChest','breast.L','breast.R') and 'Animation' not in collections:
        continue
    roles.append({'name':pb.name,'parent':pb.parent.name if pb.parent else None,'local_location':b.use_local_location,'inherit_rotation':b.use_inherit_rotation,'inherit_scale':b.inherit_scale,'connect':b.use_connect,'shape':pb.custom_shape.name if pb.custom_shape else None,'anchor':pb.custom_shape_transform.name if pb.custom_shape_transform else None,'rest_det':b.matrix_local.to_3x3().determinant(),'pose_det':pb.matrix.to_3x3().determinant(),'pose_scale':list(pb.matrix.to_scale()),'basis_scale':list(pb.scale),'parent_pose_det':pb.parent.matrix.to_3x3().determinant() if pb.parent else None,'location':list(pb.location),'lock_location':list(pb.lock_location),'constraints':[{'name':c.name,'type':c.type,'influence':c.influence,'mute':c.mute,'owner_space':c.owner_space,'target_space':c.target_space,'mix_mode':getattr(c,'mix_mode',None),'subtarget':getattr(c,'subtarget',None)} for c in pb.constraints],'rest_axes':[list(v) for v in b.matrix_local.to_3x3().col],'pose_axes':[list(v) for v in pb.matrix.to_3x3().col]})
report={'world_det':rig.matrix_world.to_3x3().determinant(),'world_scale':list(rig.matrix_world.to_scale()),'world_axes':[list(v) for v in rig.matrix_world.to_3x3().col],'controls':roles}
out=Path(r'D:\Blender\Projects\Character\X\outputs\rig\native_translation_flags_readonly.json')
out.write_text(json.dumps(report,indent=2))
print('NATIVE_TRANSLATION_FLAGS',json.dumps({'world_det':report['world_det'],'controls':[{k:v for k,v in b.items() if k not in ('rest_axes','pose_axes','constraints')} for b in roles]},separators=(',',':')),flush=True)
