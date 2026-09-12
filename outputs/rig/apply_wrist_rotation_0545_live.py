"""Back up and explicitly apply the tested wrist update to the open X scene."""
import bpy
import importlib
import importlib.util
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

OUT = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
PRODUCTION = Path(r'D:\Blender\Projects\Character\X\X.blend')
report = {'ok': False, 'main_saved': False}
assert not bpy.app.background
assert Path(bpy.data.filepath).resolve() == PRODUCTION.resolve()
assert bpy.context.mode in {'OBJECT','POSE'}
assert bpy.context.object is not None and bpy.context.object.name == 'CoshaRig'
assert json.loads((OUT / 'wrist_rotation_0545_validation.json').read_text(encoding='utf-8'))['ok']
rig = bpy.data.objects['CoshaRig']
backup = OUT / 'backups' / ('X_before_wrist_rotation_0545_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
backup.parent.mkdir(parents=True, exist_ok=True)
assert not backup.exists()
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}
report['backup'] = str(backup)
(OUT / 'wrist_rotation_0545_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
paths = list(sys.path)
spec = importlib.util.spec_from_file_location('live_wrist_checks', OUT / 'validate_wrist_rotation_0545.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
sys.path[:] = paths
before = checks.snapshot(rig)
try:
    import character_designer as cd
    if tuple(cd.bl_info['version']) != (0,54,5):
        cd._reload_addon_deferred()
        cd = importlib.import_module('character_designer')
    assert tuple(cd.bl_info['version']) == (0,54,5)
    from character_designer import limb_ik
    report['preflight'] = limb_ik.upgrade_wrist_rotation(bpy.context, rig, dry_run=True)
    assert not report['preflight']['blockers'], str(report['preflight']['blockers'])
    assert bpy.ops.character_designer.upgrade_wrist_rotation() == {'FINISHED'}
    report['pose_error'] = checks.unchanged(before, checks.snapshot(rig), rig)
    checks.checks.validate_existing(rig)
    report.update(ok=True, version=list(cd.bl_info['version']), module=cd.__file__,
                  rest_weights_shapes_actions_preserved=True, helpers_hidden=True)
    # Return to the same viewport before saving the updated project layout.
    if bpy.context.area.type == 'CONSOLE':
        bpy.context.area.type = 'VIEW_3D'
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    assert bpy.ops.wm.save_as_mainfile(filepath=str(PRODUCTION)) == {'FINISHED'}
    report['main_saved'] = True
except Exception as exc:
    report.update(error=str(exc), traceback=traceback.format_exc())
    raise
finally:
    (OUT / 'wrist_rotation_0545_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('WRIST_0545_LIVE', json.dumps(report), flush=True)
