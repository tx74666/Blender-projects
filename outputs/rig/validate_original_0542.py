"""Check the real live-input copy without writing the production blend."""
import bpy, importlib.util, json
from pathlib import Path
OUT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
spec=importlib.util.spec_from_file_location('original_checks',OUT/'validate_bone_display_0540.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
import character_designer as cd
cd.register()
from character_designer import bone_display as display, bone_display_sync as sync
rig=bpy.data.objects['CoshaRig']
before=checks.capture_current()
checks.validate_existing(rig)
report={'input':bpy.data.filepath,'initial_left_pose_hidden':getattr(rig.pose.bones['shin.L'],'hide',None),'errors':{}}
display.show_controls(bpy.context,rig,'ALL')
report['errors']['controls']=checks.assert_unchanged(before,checks.capture_current())
daily=display._snapshot(rig)
rig.data.collections_all['Original'].is_visible=True
sync.sync_pending()
assert display.view_mode(rig)=='ORIGINAL'
for side in 'LR':
    pb=rig.pose.bones['shin.'+side]
    assert not pb.bone.hide and not getattr(pb,'hide',False),pb.name
assert not rig.data.collections_all['Body'].is_visible
assert not rig.data.collections_all['_Internal'].is_visible
report['errors']['native']=checks.assert_unchanged(before,checks.capture_current())
native=display._snapshot(rig)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'X_original_0542_validated.blend'),copy=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'X_original_0542_validated.blend'),use_scripts=False)
rig=bpy.data.objects['CoshaRig']
assert display._snapshot(rig)==native
rig.data.collections_all['Original'].is_visible=False
sync.sync_pending()
assert display.view_mode(rig) is None
assert display._snapshot(rig)==daily
report['errors']['restore_reopen']=checks.assert_unchanged(before,checks.capture_current())
checks.validate_existing(rig)
report.update(ok=True,counts=before['counts'],production_file_written=False)
(OUT/'original_0542_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ORIGINAL_0542_VALIDATED',json.dumps(report))
