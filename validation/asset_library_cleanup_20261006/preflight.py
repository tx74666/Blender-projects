import bpy
import hashlib
import json
import os
import shutil
from pathlib import Path

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
assert Path(bpy.data.filepath).resolve() == artist
assert os.getpid() == 12696
assert bpy.context.mode == 'POSE'
checkpoint = folder / 'X_before_asset_cleanup.blend'
assert not checkpoint.exists(), 'Do not overwrite the cleanup checkpoint.'

def state():
    return {'objects': {o.name: {'data': o.data.name if o.data else None,
        'matrix': [list(row) for row in o.matrix_world],
        'materials': [s.material.name if s.material else None for s in o.material_slots]}
        for o in bpy.data.objects},
        'bones': {o.name: {p.name: [list(row) for row in p.matrix_basis] for p in o.pose.bones}
                  for o in bpy.data.objects if o.type == 'ARMATURE'},
        'actions': sorted(a.name for a in bpy.data.actions),
        'materials': sorted(m.name for m in bpy.data.materials),
        'frame': bpy.context.scene.frame_current,
        'active': bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
        'selected_bones': sorted(p.name for p in bpy.context.selected_pose_bones or []),
        'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto}

before = state()
result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True, check_existing=False)
assert result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == artist
assert state() == before, 'Checkpoint must preserve artist scene state.'
report = {'checkpoint': str(checkpoint), 'checkpoint_bytes': checkpoint.stat().st_size,
          'checkpoint_sha256': hashlib.file_digest(checkpoint.open('rb'), 'sha256').hexdigest(),
          'state': before, 'preferences_backups': [], 'workspaces': [], 'browser_rna': {}}
pref_file = Path(bpy.utils.user_resource('CONFIG')) / 'userpref.blend'
if pref_file.is_file():
    target = folder / 'userpref_before_cleanup.blend'
    assert not target.exists()
    shutil.copy2(pref_file, target)
    report['preferences_backups'].append(str(target))
import blenderkit.persistent_preferences as persistent
json_prefs = Path(persistent.get_preferences_path())
if json_prefs.is_file():
    target = folder / 'blenderkit_preferences_before_cleanup.json'
    assert not target.exists()
    shutil.copy2(json_prefs, target)
    report['preferences_backups'].append(str(target))
kit_prefs = bpy.context.preferences.addons['blenderkit'].preferences
report['blenderkit_setting_before'] = bool(kit_prefs.create_asset_library)
report['blenderkit_preferences_path'] = str(json_prefs)
for ws in bpy.data.workspaces:
    report['workspaces'].append({'name': ws.name, 'screens': [s.name for s in ws.screens]})
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'FILE_BROWSER' and area.spaces.active.browse_mode == 'ASSETS':
            params = area.spaces.active.params
            report['browser_rna'] = {p.identifier: {'type': p.type,
                'items': [i.identifier for i in p.enum_items] if p.type == 'ENUM' else None}
                for p in params.bl_rna.properties if any(k in p.identifier for k in ('asset', 'catalog', 'filter'))}
            break
(folder / 'preflight.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ASSET_CLEANUP_CHECKPOINT_VERIFIED', checkpoint.stat().st_size)
