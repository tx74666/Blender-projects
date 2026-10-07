import bpy
import hashlib
import json
import os
from pathlib import Path

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
assert os.getpid() == 12696 and Path(bpy.data.filepath).resolve() == artist
assert bpy.context.mode == 'POSE'
assert not (folder / 'cleanup_result.json').exists(), 'Cleanup already completed.'
baseline = json.loads((folder / 'preflight.json').read_text(encoding='utf-8'))
inventory = json.loads((folder / 'live_inventory.json').read_text(encoding='utf-8'))
move = json.loads((folder / 'pose_move.json').read_text(encoding='utf-8-sig'))
pose_file = Path(move['Destination'])
assert pose_file.is_file()
with pose_file.open('rb') as handle:
    assert hashlib.file_digest(handle, 'sha256').hexdigest().upper() == move['SHA256']

def scene_state():
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

assert scene_state() == baseline['state'], 'Scene changed since checkpoint; recapture before cleanup.'
targets = []
for group in ('materials', 'objects'):
    expected = {x['name']: x for x in inventory['assets'][group]}
    actual = {x.name for x in getattr(bpy.data, group) if x.asset_data and x.library is None}
    assert actual == set(expected), (group, 'Asset inventory changed.')
    for name, saved in expected.items():
        block = getattr(bpy.data, group)[name]
        assert block.library is None and block.asset_data
        assert block.use_fake_user == saved['fake_user']
        targets.append((group, block, block.use_fake_user))

libraries = bpy.context.preferences.filepaths.asset_libraries
protected = {x['name']: str(Path(x['path']).resolve()) for x in inventory['libraries'] if x['name'] != 'BlenderKit'}
cache = Path(r'C:\Users\Randy\blenderkit_data').resolve()
remove = [lib for lib in libraries if Path(lib.path).resolve() == cache]
assert len(remove) == 1 and remove[0].name == 'BlenderKit'
kit = bpy.context.preferences.addons['blenderkit'].preferences
kit.create_asset_library = False

cleared = []
for group, block, fake_user in targets:
    block.asset_clear()
    block.use_fake_user = fake_user
    cleared.append({'type': group, 'name': block.name})
remove_indexes = [i for i, lib in enumerate(libraries) if Path(lib.path).resolve() == cache]
for index in reversed(remove_indexes):
    assert bpy.ops.preferences.asset_library_remove(index=index) == {'FINISHED'}
assert not any(Path(lib.path).resolve() == cache for lib in libraries)
assert {lib.name: str(Path(lib.path).resolve()) for lib in libraries} == protected
assert scene_state() == baseline['state'], 'Cleanup must not alter artist scene data.'

updated_browsers = []
browser_errors = []
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type != 'FILE_BROWSER' or area.spaces.active.browse_mode != 'ASSETS':
            continue
        params = area.spaces.active.params
        try:
            if screen.name in {'Default.001', 'Geometry Nodes.001', 'Modeling.001'}:
                params.asset_library_reference = 'Pose Library'
                params.catalog_id = '00000000-0000-0000-0000-000000000000'
                params.asset_catalog_visibility = 'ALL'
                params.filter_search = ''
                updated_browsers.append(screen.name)
            if screen == bpy.context.window.screen:
                with bpy.context.temp_override(area=area, region=next(r for r in area.regions if r.type == 'WINDOW')):
                    bpy.ops.asset.library_refresh()
        except Exception as exc:
            browser_errors.append({'screen': screen.name, 'error': str(exc)})
        area.tag_redraw()

preferences_save = bpy.ops.wm.save_userpref()
assert preferences_save == {'FINISHED'}
console_area = bpy.context.area
assert console_area.type == 'CONSOLE'
console_area.type = 'NODE_EDITOR'
console_area.ui_type = 'ShaderNodeTree'
scene_save = bpy.ops.wm.save_as_mainfile(filepath=str(artist), check_existing=False)
assert scene_save == {'FINISHED'} and Path(bpy.data.filepath).resolve() == artist
assert scene_state() == baseline['state']
report = {'runtime': bpy.app.version_string, 'pid': os.getpid(), 'artist': str(artist),
          'removed_library': str(cache), 'automatic_registration': bool(kit.create_asset_library),
          'remaining_libraries': [{'name': lib.name, 'path': lib.path} for lib in libraries],
          'cleared_asset_marks': cleared, 'scene_data_preserved': True,
          'pose_file': str(pose_file), 'updated_browsers': updated_browsers, 'browser_errors': browser_errors,
          'preferences_save': sorted(preferences_save), 'scene_save': sorted(scene_save),
          'asset_counts_after': {group: sum(bool(x.asset_data) for x in getattr(bpy.data, group))
             for group in ('actions', 'materials', 'objects', 'collections', 'node_groups')},
          'cache_files_preserved': True, 'scene_file_bytes': artist.stat().st_size}
(folder / 'cleanup_result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ASSET_LIBRARY_CLEANUP_VERIFIED_AND_SAVED', len(cleared))
