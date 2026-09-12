"""Install display behavior on the current scene after an exact local backup."""
import bpy, importlib, importlib.util, json
from pathlib import Path
from datetime import datetime
ROOT=Path(r'D:\Blender\Projects\Character\X')
OUT=ROOT/'outputs/rig'
assert Path(bpy.data.filepath).resolve()==(ROOT/'X.blend').resolve()
assert bpy.context.mode in {'OBJECT','POSE'}
rig=bpy.data.objects['CoshaRig']
assert bpy.context.object==rig
backup=OUT/'backups'/('X_before_original_0542_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)=={'FINISHED'}
spec=importlib.util.spec_from_file_location('live_original_checks',OUT/'validate_bone_display_0540.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
before=checks.capture_current()
import character_designer as cd
if tuple(cd.bl_info['version'])!=(0,54,2):
    cd._reload_addon_deferred()
    cd=importlib.import_module('character_designer')
assert tuple(cd.bl_info['version'])==(0,54,2)
from character_designer import bone_display as display, foot_controls
display.show_controls(bpy.context,rig,'ALL')
display.show_native(bpy.context,rig,'ORIGINAL')
assert not rig.data.collections_all['Body'].is_visible
assert not rig.data.collections_all['_Internal'].is_visible
assert rig.data.collections_all['Original'].is_visible
for side in 'LR':
    pb=rig.pose.bones['shin.'+side]
    assert not pb.bone.hide and not getattr(pb,'hide',False)
for record in foot_controls.records(rig).values():
    for role,name in record['bones'].items():
        if role not in {'FOOT_ROLL','TOE_BEND'}:
            pb=rig.pose.bones[name]
            assert pb.bone.hide and getattr(pb,'hide',True),name
error=checks.assert_unchanged(before,checks.capture_current())
checks.validate_existing(rig)
report={'ok':True,'version':list(cd.bl_info['version']),'backup':str(backup),'pose_error':error,
        'both_shins_visible':True,'preservation_verified':True,'main_saved':False}
(OUT/'original_0542_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if bpy.context.area and bpy.context.area.type=='CONSOLE':bpy.context.area.type='VIEW_3D'
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:area.tag_redraw()
print('ORIGINAL_0542_LIVE',json.dumps(report))
