"""Correct two existing breast display curves in the live X scene, with backup."""
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

backup = OUT / 'backups' / ('X_before_body_wrap_0531_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
backup.parent.mkdir(parents=True, exist_ok=True)
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}

spec = importlib.util.spec_from_file_location('body_wrap_live_checks', OUT / 'validate_body_wrap_0531.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
before = checks.capture_current()

import character_designer as cd
if tuple(cd.bl_info['version']) != (0, 53, 1):
    cd._reload_addon_deferred()
    cd = importlib.import_module('character_designer')
assert tuple(cd.bl_info['version']) == (0, 53, 1)
from character_designer import body_detail_visuals as service
old_record = service.validate(rig)
old_coordinates = {role: [v.co.copy() for v in rig.pose.bones[old_record['names'][role]].custom_shape.data.vertices]
                   for role in ('BREAST_L', 'BREAST_R')}
try:
    result = service.update_breast_curvature(bpy.context, rig)
    after = checks.capture_current()
    checks.assert_unchanged(before, after)
    record = service.validate(rig)
    assert all(record['fit']['roles'][role].get('profile') == 'WRAP' for role in old_coordinates)
except Exception:
    for role, coordinates in old_coordinates.items():
        mesh = rig.pose.bones[old_record['names'][role]].custom_shape.data
        for vertex, coordinate in zip(mesh.vertices, coordinates):
            vertex.co = coordinate
        mesh.update()
    rig.data[service.RECORD_KEY] = json.dumps(old_record)
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
          'profiles': {role: record['fit']['roles'][role]['profile'] for role in old_coordinates}}
(OUT / 'body_wrap_0531_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BODY_WRAP_0531_LIVE', json.dumps(report), flush=True)
