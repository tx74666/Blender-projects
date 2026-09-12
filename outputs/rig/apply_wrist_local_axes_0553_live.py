"""Apply validated display-frame input, keeping all existing bone transforms."""
import bpy, json, importlib, runpy, traceback
from pathlib import Path
from datetime import datetime
out=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
main=out.parents[1]/'X.blend'
assert Path(bpy.data.filepath).resolve()==main.resolve()
assert bpy.context.mode in {'OBJECT','POSE'}
assert not any('TRANSFORM_OT' in getattr(op,'bl_idname','') for op in getattr(bpy.context.window,'modal_operators',()))
assert json.loads((out/'wrist_local_axis_0553_validation.json').read_text())['ok']
rig=bpy.data.objects['CoshaRig']
assert bpy.context.object==rig
report={'ok':False,'saved':False}
try:
    backup=out/'backups'/('X_before_wrist_local_axes_0553_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
    assert bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)=={'FINISHED'}
    report['backup']=str(backup)
    digest=runpy.run_path(str(out/'repair_reversal_20260912.py'))['digest_meshes']
    meshes=digest()
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    pose={p.name:p.matrix.copy() for p in rig.pose.bones}
    basis={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
    import character_designer as cd
    if tuple(cd.bl_info['version'])!=(0,55,3):
        cd._reload_addon_deferred()
        cd=importlib.import_module('character_designer')
    assert tuple(cd.bl_info['version'])==(0,55,3)
    from character_designer import limb_ik,forearm_twist
    report['changed']=limb_ik.sync_wrist_local_axes(rig)
    assert all(rig.pose.bones['CTRL_hand_IK.'+s].use_transform_at_custom_shape for s in 'LR')
    assert not limb_ik.sync_wrist_local_axes(rig)
    assert digest()==meshes,'Mesh/weights/shape data changed'
    assert set(rest)==set(rig.data.bones.keys())
    def err(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
    report['rest_error']=max(err(m,rig.data.bones[n].matrix_local) for n,m in rest.items())
    report['pose_error']=max(err(m,rig.pose.bones[n].matrix) for n,m in pose.items())
    report['basis_error']=max(err(m,rig.pose.bones[n].matrix_basis) for n,m in basis.items())
    assert max(report[k] for k in ('rest_error','pose_error','basis_error'))<2e-5,report
    report['calibration_errors']=dict(forearm_twist._ERRORS)
    if bpy.context.area.type=='CONSOLE':bpy.context.area.type='VIEW_3D'
    for screen in bpy.data.screens:
        for area in screen.areas:area.tag_redraw()
    assert bpy.ops.wm.save_as_mainfile(filepath=str(main))=={'FINISHED'}
    report.update(ok=True,saved=True,version=list(cd.bl_info['version']))
except Exception as exc:
    report.update(error=str(exc),traceback=traceback.format_exc())
    raise
finally:
    (out/'wrist_local_axes_0553_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('WRIST_LOCAL_AXES_LIVE',json.dumps(report),flush=True)
