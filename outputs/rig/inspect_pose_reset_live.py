import bpy, json
from pathlib import Path
from datetime import datetime
ROOT = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
assert bpy.app.background or Path(bpy.data.filepath).resolve() == (ROOT.parent.parent / 'X.blend').resolve()
rig = bpy.data.objects['CoshaRig']
backup = ROOT / 'backups' / ('X_before_pose_reset_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
if bpy.app.background:
    backup = Path(bpy.data.filepath)
else:
    bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
def mat(m): return [list(row) for row in m]
def props(item):
    return {k: str(v) for k,v in item.items()}
rows=[]
for pb in rig.pose.bones:
    rows.append(dict(name=pb.name, parent=pb.parent.name if pb.parent else None,
        rest=mat(pb.bone.matrix_local), basis=mat(pb.matrix_basis), pose=mat(pb.matrix),
        loc=list(pb.location), rot=list(pb.rotation_euler), quat=list(pb.rotation_quaternion), scale=list(pb.scale),
        locks=[list(pb.lock_location),list(pb.lock_rotation),list(pb.lock_scale)],
        mode=pb.rotation_mode, hide=pb.bone.hide, selected=getattr(pb, 'select', getattr(pb.bone, 'select', None)),
        props=props(pb), bone_props=props(pb.bone),
        constraints=[dict(name=c.name,type=c.type,influence=c.influence,mute=c.mute,
            target=getattr(c,'target',None).name if getattr(c,'target',None) else None,
            subtarget=getattr(c,'subtarget',None)) for c in pb.constraints]))
report=dict(backup=str(backup),frame=bpy.context.scene.frame_current,rig=rig.name,
    rig_props=props(rig), bones=rows, auto_key=bpy.context.scene.tool_settings.use_keyframe_insert_auto,
    action=rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None,
    nla=[t.name for t in rig.animation_data.nla_tracks] if rig.animation_data else [],
    drivers=[dict(path=f.data_path,index=f.array_index,expression=f.driver.expression) for f in rig.animation_data.drivers] if rig.animation_data else [])
(ROOT / 'pose_reset_diagnostic.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('POSE_RESET_DIAGNOSTIC', str(backup), 'bones',len(rows), 'action',report['action'])
