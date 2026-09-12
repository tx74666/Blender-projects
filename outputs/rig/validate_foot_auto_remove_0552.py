import bpy, json, runpy, sys, traceback
from pathlib import Path
OUT=Path(__file__).parent
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import body_setup, body_setup_transaction as tx, limb_ik, foot_controls
report={'ok':False}
try:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'fixtures/X_foot_auto_align_0552_preview.blend'))
    cd.register()
    rig=bpy.data.objects['CoshaRig']
    bpy.context.view_layer.objects.active=rig
    rig.hide_set(False)
    rig.select_set(True)
    if rig.mode!='POSE': bpy.ops.object.mode_set(mode='POSE')
    digest=runpy.run_path(str(OUT/'repair_reversal_20260912.py'))['digest_meshes']
    before=digest()
    bones=set(rig.data.bones.keys())
    raw=rig.data[foot_controls.RECORD_KEY]
    native_rest={b.name:b.matrix_local.copy() for b in rig.data.bones if not b.get(limb_ik.OWNER_KEY)}
    snapshot=tx.capture(bpy.context,rig)
    try:
        body_setup.remove(bpy.context,rig)
        assert not body_setup.has_generated(rig)
        assert not foot_controls.records(rig)
        assert digest()==before
        report['native_rest_error']=max(abs(rig.data.bones[n].matrix_local[i][j]-m[i][j])
            for n,m in native_rest.items() for i in range(4) for j in range(4))
        assert report['native_rest_error']<2e-6
        report['full_remove']=True
        tx.restore(bpy.context,rig,snapshot)
        assert set(rig.data.bones.keys())==bones
        assert rig.data[foot_controls.RECORD_KEY]==raw
        limb_ik._validate_inventory(rig)
        foot_controls.validate(rig)
        assert digest()==before
        report['rollback']=True
    finally:
        tx.discard(snapshot)
    report['ok']=True
except Exception as exc:
    report.update(error=str(exc),traceback=traceback.format_exc())
    raise
finally:
    (OUT/'foot_auto_remove_0552_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('X_FOOT_REMOVE_RESULT',json.dumps(report),flush=True)
