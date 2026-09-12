"""Keep necessary foot mechanisms invisible without modifying any binding."""
import bpy, importlib, importlib.util, json
from pathlib import Path
from datetime import datetime
ROOT=Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve()==(ROOT/'X.blend').resolve()
assert bpy.context.mode in {'OBJECT','POSE'}
rig=bpy.data.objects['CoshaRig']
assert bpy.context.object==rig
backup=ROOT/'outputs/rig/backups'/('X_before_foot_hidden_0541_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)=={'FINISHED'}
spec=importlib.util.spec_from_file_location('foot_visibility_checks',ROOT/'outputs/rig/validate_bone_display_0540.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
before=checks.capture_current()
import character_designer as cd
if tuple(cd.bl_info['version'])!=(0,54,1):
    cd._reload_addon_deferred()
    cd=importlib.import_module('character_designer')
assert tuple(cd.bl_info['version'])==(0,54,1)
from character_designer import bone_display, foot_controls
bone_display.show_controls(bpy.context,rig,'ALL')
mechanisms=[]
for record in foot_controls.records(rig).values():
    for role,name in record['bones'].items():
        if role not in {'FOOT_ROLL','TOE_BEND'}:
            bone=rig.data.bones[name]
            assert bone.hide, name
            mechanisms.append(name)
pose_error=checks.assert_unchanged(before,checks.capture_current())
checks.validate_existing(rig)
area=bpy.context.area
if area and area.type=='CONSOLE': area.type='VIEW_3D'
for win in bpy.context.window_manager.windows:
    for area in win.screen.areas: area.tag_redraw()
assert bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'X.blend'))=={'FINISHED'}
report={'ok':True,'version':list(cd.bl_info['version']),'backup':str(backup),'hidden_mechanisms':mechanisms,'pose_error':pose_error,'preservation_verified':True,'saved':bpy.data.filepath}
(ROOT/'outputs/rig/foot_hidden_0541_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FOOT_HIDDEN_0541_LIVE',json.dumps(report))
