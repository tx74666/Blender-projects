"""Back up X, organize bone displays and retain every binding and pose."""
import bpy
import importlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
assert not bpy.app.background
assert Path(bpy.data.filepath).resolve() == (ROOT / 'X.blend').resolve()
assert bpy.context.mode in {'OBJECT', 'POSE'}, 'Finish the current modeling operation first.'
rig = bpy.data.objects['CoshaRig']
assert bpy.context.object == rig, 'Select the character rig first.'
backup = OUT / 'backups' / ('X_before_bone_display_0540_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
backup.parent.mkdir(parents=True, exist_ok=True)
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}

spec = importlib.util.spec_from_file_location('bone_display_live_checks', OUT / 'validate_bone_display_0540.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
before = checks.capture_current()
import character_designer as cd
if tuple(cd.bl_info['version']) != (0, 54, 0):
    cd._reload_addon_deferred()
    cd = importlib.import_module('character_designer')
assert tuple(cd.bl_info['version']) == (0, 54, 0)
from character_designer import bone_collections as groups, bone_display as display, skirt_rig
assert display.view_mode(rig) is None, 'Restore the current temporary bone view first.'
dresses = display.dress_rigs(bpy.context, rig)
affected = [rig] + [item for item, _record in dresses]
layouts = [(item, groups.snapshot_layout(item), display._snapshot(item)) for item in affected]
try:
    groups.simplify_body_collections(rig)
    for item, _record in dresses:
        skirt_rig.migrate_skirt_bone_collections(item)
    display.show_controls(bpy.context, rig, 'ALL')
    pose_error = checks.assert_unchanged(before, checks.capture_current())
    checks.validate_existing(rig)
except Exception:
    for item, saved, visible in layouts:
        groups.restore_layout(item, saved)
        display._restore(item, visible)
    raise

bpy.context.window_manager.character_designer.ui_page = 'RIG'
bpy.context.window_manager.character_designer.rig_section = 'BODY'
area = bpy.context.area
if area and area.type == 'CONSOLE':
    area.type = 'VIEW_3D'
for window in bpy.context.window_manager.windows:
    for item in window.screen.areas:
        item.tag_redraw()
assert bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'X.blend')) == {'FINISHED'}
report = {'ok': True, 'version': list(cd.bl_info['version']), 'backup': str(backup),
          'saved': str(ROOT / 'X.blend'), 'counts': before['counts'], 'pose_error': pose_error,
          'preservation_verified': True, 'roots': list(rig.data.collections.keys()),
          'groups': {c.name: len(c.bones) for c in rig.data.collections_all},
          'dress_rigs': [item.name for item, _record in dresses]}
(OUT / 'bone_display_0540_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BONE_DISPLAY_0540_LIVE', json.dumps(report), flush=True)
