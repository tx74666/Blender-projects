"""Refresh and upgrade current X feet; retain a complete pre-upgrade copy."""
import bpy, importlib, json, runpy, traceback
from datetime import datetime
from pathlib import Path

OUT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
MAIN=OUT.parents[1]/'X.blend'
assert Path(bpy.data.filepath).resolve()==MAIN.resolve()
assert not bpy.app.background and bpy.context.mode in {'OBJECT','POSE'}
assert bpy.context.object and bpy.context.object.name=='CoshaRig'
assert json.loads((OUT/'foot_auto_align_0552_validation.json').read_text())['ok']
assert json.loads((OUT/'foot_auto_remove_0552_validation.json').read_text())['ok']
assert not any('TRANSFORM_OT' in getattr(op,'bl_idname','') for op in getattr(bpy.context.window,'modal_operators',()))
report={'ok':False,'saved':False}
backup=OUT/'backups'/('X_before_foot_auto_align_0552_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
try:
    bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)
    report['backup']=str(backup)
    digest=runpy.run_path(str(OUT/'repair_reversal_20260912.py'))['digest_meshes']
    meshes=digest()
    rig=bpy.data.objects['CoshaRig']
    rests={b.name:b.matrix_local.copy() for b in rig.data.bones}
    poses={p.name:p.matrix.copy() for p in rig.pose.bones}
    bases={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
    import character_designer as cd
    if tuple(cd.bl_info['version']) != (0,55,2):
        cd._reload_addon_deferred()
        cd=importlib.import_module('character_designer')
    assert tuple(cd.bl_info['version'])==(0,55,2), cd.bl_info['version']
    assert digest()==meshes,'Add-on refresh changed mesh data'
    assert bpy.ops.character_designer.upgrade_foot_auto_align('EXEC_DEFAULT')=={'FINISHED'}
    from character_designer import foot_controls,limb_ik
    limb_ik._validate_inventory(rig)
    foot_controls.validate(rig)
    assert all(foot_controls.get_record(rig,('LEG',s))['auto_follow']==1 for s in 'LR')
    assert digest()==meshes,'Mesh/weights/keys changed'
    def error(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
    report['rest_error']=max(error(rig.data.bones[n].matrix_local,m) for n,m in rests.items())
    report['basis_error']=max(error(rig.pose.bones[n].matrix_basis,m) for n,m in bases.items())
    report['pose_error']=max(error(rig.pose.bones[n].matrix,m) for n,m in poses.items())
    assert report['rest_error']<2e-6 and report['basis_error']<2e-6 and report['pose_error']<4e-4,report
    report['new_helpers']=sorted(set(rig.data.bones.keys())-set(rests))
    if bpy.context.area.type=='CONSOLE':bpy.context.area.type='VIEW_3D'
    for screen in bpy.data.screens:
        for area in screen.areas:area.tag_redraw()
    assert bpy.ops.wm.save_as_mainfile(filepath=str(MAIN))=={'FINISHED'}
    report.update(ok=True,saved=True,version=list(cd.bl_info['version']))
except Exception as exc:
    report.update(error=str(exc),traceback=traceback.format_exc())
    raise
finally:
    (OUT/'foot_auto_align_0552_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('FOOT_AUTO_ALIGN_LIVE',json.dumps(report),flush=True)
