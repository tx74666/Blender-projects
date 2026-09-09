import bpy,hashlib,json,sys
from pathlib import Path
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons']
import character_designer
from character_designer import limb_fk_visuals as visuals,limb_ik,torso_controls
SOURCE=Path(r'D:\Blender\Projects\Character\X\X.blend')
REPORT=Path(r'D:\Blender\Projects\Character\X\outputs\rig\latest_x_limb_fk_visuals_051_validation.json')
digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['CoshaRig']
limb_ik._mode_set(bpy.context,rig,'POSE')
visuals._update(bpy.context,rig)
before={pb.name:pb.matrix.copy() for pb in rig.pose.bones}
display={pb.name:limb_ik._pose_shape_json_state(pb) for pb in rig.pose.bones}
rest={bone.name:torso_controls._state(bone) for bone in rig.data.bones}
report={'source':str(SOURCE),'source_sha256_before':digest,'status':'running'}
try:
    record=visuals.build(bpy.context,rig)
    report['rings']={'count':len(record['bindings']),'sources':list(record['bindings']),'skipped':record.get('skipped',{})}
    visuals._verify_pose(rig,before)
    result=visuals.fit_ik_sizes(bpy.context,rig)
    report['size_fit']=result
    report['fitted_scales']=visuals._size_record(rig)
    visuals._verify_pose(rig,before)
    limb_ik._validate_inventory(rig)
    visuals.restore_ik_sizes(bpy.context,rig)
    visuals.remove(bpy.context,rig)
    visuals._verify_pose(rig,before)
    report['display_states_restored']=display=={pb.name:limb_ik._pose_shape_json_state(pb) for pb in rig.pose.bones}
    report['rest_unchanged']=len(rig.data.bones)==len(rest) and all(torso_controls._same_rest(rig.data.bones[name],state) for name,state in rest.items())
    report['pose_error']=max(abs(rig.pose.bones[name].matrix[i][j]-matrix[i][j]) for name,matrix in before.items() for i in range(4) for j in range(4))
    assert report['display_states_restored'] and report['rest_unchanged']
    limb_ik._validate_inventory(rig)
    report['status']='passed'
except Exception as exc:
    report['status']='failed';report['error']=repr(exc)
    raise
finally:
    report['source_sha256_after']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    report['source_unchanged']=report['source_sha256_after']==digest
    REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('X_FK_VISUALS_RESULT',json.dumps(report),flush=True)
