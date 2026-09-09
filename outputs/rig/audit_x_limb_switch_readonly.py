import hashlib, json, sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import limb_ik, limb_ik_fk, foot_controls, torso_controls, eye_controls
SOURCE=Path(r'D:\Blender\Projects\Character\X\X.blend')
REPORT=Path(r'D:\Blender\Projects\Character\X\outputs\rig\audit_x_limb_switch_readonly.json')
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['CoshaRig']
limb_ik._mode_set(bpy.context, rig, 'POSE')
def update(): limb_ik_fk._update(bpy.context,rig)
inv=limb_ik._validate_inventory(rig)
torso=torso_controls.get_record(rig)
feet=foot_controls.records(rig)
eyes=eye_controls.get_record(rig)
if not eyes: eyes=eye_controls.build(bpy.context,rig)
rest={b.name:torso_controls._state(b) for b in rig.data.bones}
records={key:rig.data[key] for key in (foot_controls.RECORD_KEY,torso_controls.RECORD_KEY,eye_controls.RECORD_KEY)}
rig.pose.bones[torso['bend']].rotation_euler.x += 0.08
rig.pose.bones[torso['controls'][torso['sources'][1]]].rotation_euler.z += 0.025
rig.pose.bones[feet['L']['roll']].rotation_euler.x += 0.2
rig.pose.bones[feet['R']['roll']].rotation_euler.y += 0.06
rig.pose.bones[feet['R']['toe_control']].rotation_euler.x += 0.1
rig.pose.bones[eyes['master']].location += Vector((0.01,0,0.005))
update()
report={'schema':inv['schema'],'version':character_designer.bl_info['version'],'feet':list(feet),'torso':True,'eyes':True,'switches':[]}
for key in inv['rigs']:
    for mode in ('FK','IK'):
        update()
        before={pb.name:pb.matrix.copy() for pb in rig.pose.bones if not pb.bone.get(limb_ik.OWNER_KEY)}
        result=limb_ik_fk.switch_limb(bpy.context,rig,key,mode,keyframe=False)
        update()
        errors={name:max(abs(rig.pose.bones[name].matrix[i][j]-m[i][j]) for i in range(4) for j in range(4)) for name,m in before.items()}
        worst=max(errors,key=errors.get)
        report['switches'].append({'key':key,'mode':mode,'match_result':result,'native_pose_max_error':errors[worst],'worst_bone':worst})
        assert errors[worst]<0.003, (key,mode,worst,errors[worst])
        assert {b.name:torso_controls._state(b) for b in rig.data.bones}==rest
        assert records=={k:rig.data[k] for k in records}
        limb_ik._validate_inventory(rig)
report['source_file_unchanged']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
report['saved']=False
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('X_LIMB_SWITCH_AUDIT',json.dumps(report),flush=True)
