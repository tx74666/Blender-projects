"""Update both existing Foot Roll directions, preserving current artist data."""
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

backup = OUT / 'backups' / ('X_before_foot_direction_0532_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
backup.parent.mkdir(parents=True, exist_ok=True)
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}
spec = importlib.util.spec_from_file_location('foot_direction_live_checks', OUT / 'validate_foot_direction_0532.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
before = checks.capture_current()

import character_designer as cd
if tuple(cd.bl_info['version']) != (0, 53, 2):
    cd._reload_addon_deferred()
    cd = importlib.import_module('character_designer')
assert tuple(cd.bl_info['version']) == (0, 53, 2)
from character_designer import foot_controls as service
old_raw = rig.data[service.RECORD_KEY]
old_records = service.validate(rig)
assert set(old_records) == {'L', 'R'}
old_rotations = {record['roll']: rig.pose.bones[record['roll']].rotation_euler.copy()
                 for record in old_records.values()}
old_expressions = [(curve, curve.driver.expression) for curve in rig.animation_data.drivers]
try:
    for side in ('L', 'R'):
        service.update_rotation_direction(bpy.context, rig, side)
    after = checks.capture_current()
    errors = checks.assert_unchanged(before, after)
    records = service.validate(rig)
    assert all(record['rotation_direction'] == 'NATURAL' for record in records.values())
except Exception:
    for name, rotation in old_rotations.items():
        rig.pose.bones[name].rotation_euler = rotation
    for curve, expression in old_expressions:
        curve.driver.expression = expression
    rig.data[service.RECORD_KEY] = old_raw
    service._update(bpy.context, rig)
    raise

area = bpy.context.area
if area and area.type == 'CONSOLE':
    area.type = 'VIEW_3D'
for window in bpy.context.window_manager.windows:
    for item in window.screen.areas:
        item.tag_redraw()
assert bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'X.blend')) == {'FINISHED'}
report = {'ok': True, 'version': list(cd.bl_info['version']), 'backup': str(backup),
          'saved': str(ROOT / 'X.blend'), 'preservation_verified': True,
          'errors': errors, 'directions': {side: record['rotation_direction'] for side, record in records.items()},
          'previous_rotations': {name: list(value) for name, value in old_rotations.items()},
          'current_rotations': {name: list(rig.pose.bones[name].rotation_euler) for name in old_rotations}}
(OUT / 'foot_direction_0532_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('FOOT_DIRECTION_0532_LIVE', json.dumps(report), flush=True)
