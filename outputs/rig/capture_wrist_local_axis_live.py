"""Capture current wrist axes and a test copy without changing the main file."""
import bpy, json, math
from pathlib import Path
from datetime import datetime
from character_designer import limb_ik, forearm_twist

out=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
assert Path(bpy.data.filepath).resolve()==(out.parents[1]/'X.blend').resolve()
assert bpy.context.mode in {'POSE','OBJECT'}
assert not any('TRANSFORM_OT' in getattr(op,'bl_idname','') for op in getattr(bpy.context.window,'modal_operators',()))
rig=bpy.data.objects['CoshaRig']
data={'selected':bpy.context.active_pose_bone.name if bpy.context.active_pose_bone else None,
      'orientation':bpy.context.scene.transform_orientation_slots[0].type,
      'sides':{},'calibrations':{}}
for side in 'LR':
    names=['CTRL_hand_IK.'+side,'forearm.'+side,'hand.'+side]
    bones={n:rig.pose.bones[n] for n in names}
    data['sides'][side]={n:{'matrix':[list(row) for row in p.matrix],
        'rest':[list(row) for row in p.bone.matrix_local],
        'shape_transform':p.custom_shape_transform.name if p.custom_shape_transform else None,
        'at_shape':p.use_transform_at_custom_shape,'around_shape':p.use_transform_around_custom_shape,
        'rotation':list(p.rotation_euler),'properties':{k:v for k,v in p.items() if isinstance(v,(int,float,str,bool))}}
        for n,p in bones.items()}
    target,lower,end=[bones[n] for n in names]
    data['sides'][side]['angles']={
        'target_Y_vs_forearm':math.degrees(target.matrix.col[1].xyz.angle(lower.matrix.col[1].xyz)),
        'hand_Y_vs_forearm':math.degrees(end.matrix.col[1].xyz.angle(lower.matrix.col[1].xyz))}
for obj in bpy.data.objects:
    if obj.type=='MESH' and forearm_twist.RECORD_KEY in obj:
        records=forearm_twist._records(obj)
        data['calibrations'][obj.name]={'error':forearm_twist._ERRORS.get(obj.name),
            'records':{side:{'enabled':r['enabled'],'topology_matches':r['topology']==forearm_twist._topology(obj.data),
                'chain':r['chain'],'key':r['key']} for side,r in records.items()}}
snapshot=out/'fixtures'/('X_wrist_local_axis_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
assert bpy.ops.wm.save_as_mainfile(filepath=str(snapshot),copy=True)=={'FINISHED'}
data['snapshot']=str(snapshot)
(out/'wrist_local_axis_live_audit.json').write_text(json.dumps(data,indent=2),encoding='utf8')
if bpy.context.area.type=='CONSOLE':bpy.context.area.type='VIEW_3D'
print('WRIST_LOCAL_AXIS_CAPTURED',str(snapshot))
