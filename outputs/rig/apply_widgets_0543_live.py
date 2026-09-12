"""Apply the validated organizer to the live scene, retaining a before-file."""
import bpy,importlib,importlib.util,json
from pathlib import Path
OUT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
input_info=json.loads((OUT/'widgets_0543_live_input.json').read_text(encoding='utf-8'))
verified=json.loads((OUT/'widgets_0543_validation.json').read_text(encoding='utf-8'))
assert verified['ok'] and verified['fixture']==input_info['backup']
assert Path(bpy.data.filepath).resolve()==Path(input_info['filepath']).resolve()
assert bpy.context.mode in {'OBJECT','POSE'} and bpy.context.object.name=='CoshaRig'
spec=importlib.util.spec_from_file_location('live_widget_checks',OUT/'validate_widgets_0543.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
rig=bpy.data.objects['CoshaRig']
before=checks.snapshot(rig)
import character_designer as cd
if tuple(cd.bl_info['version'])!=(0,54,3):
    cd._reload_addon_deferred()
    cd=importlib.import_module('character_designer')
assert tuple(cd.bl_info['version'])==(0,54,3)
assert bpy.ops.character_designer.organize_widgets()=={'FINISHED'}
error=checks.unchanged(before,rig)
from character_designer import widget_collections as widgets
report={'ok':True,'backup':input_info['backup'],'version':list(cd.bl_info['version']),
        'pose_error':error,'preservation_verified':True,'main_saved':False,
        'collections':[x['collection'].name for x in widgets._resources(rig)]}
(OUT/'widgets_0543_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if bpy.context.area.type=='CONSOLE':bpy.context.area.type='VIEW_3D'
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:area.tag_redraw()
print('WIDGETS_0543_LIVE',json.dumps(report))
