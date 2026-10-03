"""Read back the saved artist file against the pre-migration backup.

This verifier never registers runtime handlers, switches display/pose modes,
changes coordinates, or saves a Blender scene. Only its JSON report is written.
Schedule its Blender process serially with other Blender/Unity work.
"""
import json
from pathlib import Path
import sys

import bpy

ROOT = Path('D:/MyRepository/Blender-addons-by-Randy')
sys.path[:0] = [str(ROOT / 'addons'), str(ROOT / 'tests')]
import character_designer
from character_designer import skirt_rig as skirt, body_original_mode as original
from character_designer import bone_display as display
from test_skirt_shared_rig_blender import (
    meshes_content, content_digest, rest_state, pose_channels,
)

PROJECT = Path('D:/Blender/Projects/Character/X')
BEFORE = PROJECT / 'Backups/DressSharedRig_20261003/X_before_dress_shared_rig.blend'
ARTIST = PROJECT / 'X.blend'
REPORT = PROJECT / 'validation/shared_dress_saved_readback_20261003.json'


def file_stamp(path):
    stat = path.stat()
    return (stat.st_size, stat.st_mtime_ns)


def channels_report(before, after, classes):
    """Stored channels are evidence; Original display changes are reported."""
    fields = ('rotation_mode', 'location', 'rotation_euler', 'rotation_quaternion',
              'rotation_axis_angle', 'scale')
    details = {}
    for name, previous in before.items():
        current = after[name]
        changes = {}
        for field, old, new in zip(fields, previous, current):
            if old == new:
                continue
            if field == 'rotation_mode':
                changes[field] = {'before': old, 'after': new}
            else:
                changes[field] = {'before': old, 'after': new,
                                  'max_component_difference': max(abs(a - b) for a, b in zip(old, new))}
        if changes:
            details[name] = changes
    summaries = {}
    for role, names in classes.items():
        changed = {name: details[name] for name in names if name in details}
        maxima = {field: max((item.get('max_component_difference', 0.0)
                              for changes in changed.values() for key, item in changes.items()
                              if key == field), default=0.0)
                  for field in fields if field != 'rotation_mode'}
        summaries[role] = {'bones': len(names), 'changed_bones': len(changed),
                           'changed_names': sorted(changed), 'component_maxima': maxima}
    return {'all_existing_channels_equal': not details, 'classes': summaries, 'differences': details,
            'policy': 'Report stored channel differences; do not require bitwise pose matrices across display sessions.'}


result = {'success': False, 'backup': str(BEFORE), 'artist': str(ARTIST),
          'version': list(character_designer.bl_info['version']),
          'scene_saved_by_verifier': False, 'runtime_handlers_registered': False}
try:
    stamps = {str(path): file_stamp(path) for path in (BEFORE, ARTIST)}
    bpy.ops.wm.open_mainfile(filepath=str(BEFORE), load_ui=False, use_scripts=False)
    before_main = bpy.data.objects['CoshaRig']
    before_source = bpy.data.objects['Dress']
    before_legacy = before_source[skirt.RIG_KEY]
    assert before_legacy != before_main, 'Backup must contain the independent Dress rig'
    original_names = tuple(before_main.data.bones.keys())
    assert len(original_names) == 236
    before_content = meshes_content(bpy.data)
    before_rest = rest_state(before_main)
    before_channels = pose_channels(before_main)
    before_native = original._native_groups(bpy.context, before_main)
    classes = {'BODY_NATIVE': set(before_native['BODY'].get(before_main, ())),
               'HAIR_NATIVE': set(before_native['HAIR'].get(before_main, ()))}
    classes['OTHER_EXISTING'] = set(original_names) - set.union(*classes.values())
    before_dress_names = tuple(before_legacy.data.bones.keys())
    before_dress_native = set(display._native_targets(bpy.context, before_main, 'DRESS')[before_legacy])
    result.update(before_main_bones=len(original_names), before_dress_bones=len(before_dress_names),
                  before_meshes=len(before_content), old_rig=before_legacy.name,
                  before_original_active=original.active(before_main),
                  protected_content_hash=content_digest(before_content))

    bpy.ops.wm.open_mainfile(filepath=str(ARTIST), load_ui=False, use_scripts=False)
    main = bpy.data.objects['CoshaRig']
    source = bpy.data.objects['Dress']
    after_content = meshes_content(bpy.data)
    result['mesh_content_differences'] = sorted(
        name for name in set(before_content) | set(after_content)
        if before_content.get(name) != after_content.get(name))
    result['after_protected_content_hash'] = content_digest(after_content)
    assert not result['mesh_content_differences'], result['mesh_content_differences']
    # This includes original vertex coordinates/index order, all Shape Keys,
    # edges/faces/loops, UV, material assignments, group order/index and exact
    # per-vertex group-index-to-weight mappings, normalized only for entry order.
    result['all_mesh_raw_data_equal'] = True
    assert all(name in main.data.bones for name in original_names)
    actual_rest = rest_state(main, original_names)
    result['existing_rest_differences'] = sorted(name for name in original_names
                                                if actual_rest[name] != before_rest[name])
    assert not result['existing_rest_differences'], result['existing_rest_differences']
    result['all_existing_236_rest_equal'] = True
    result['existing_pose_channels'] = channels_report(
        before_channels, pose_channels(main, original_names), classes)

    record = skirt.read_record(source)
    assert skirt.is_shared(record)
    assert source[skirt.RIG_KEY] == main
    assert tuple(skirt.shared_sources(main)) == (source,)
    assert len(main.data.bones) == 351
    assert result['old_rig'] not in bpy.data.objects
    owned = set(record['shared']['names'])
    assert len(owned) == 115 and owned == set(before_dress_names)
    assert set(main.data.bones.keys()) == set(original_names) | owned
    assert main.get(skirt.OWNER_KEY) is None and main.data.get(skirt.OWNER_KEY) is None
    collection = main.data.collections_all[record['shared']['collection']]
    assert collection.get(skirt.OWNER_KEY) == record['owner']
    assert set(collection.bones.keys()) == owned
    for name in owned:
        bone = main.data.bones[name]
        assert bone.get(skirt.OWNER_KEY) == record['owner']
        assert bone.get(skirt.SOURCE_KEY) == source
        assert set(bone.collections) == {collection}
    native = display._native_targets(bpy.context, main, 'DRESS')
    assert native == {main: before_dress_native} and len(native[main]) == 33
    assert source.modifiers[record['modifier']].object == main
    saved_groups = original._native_groups(bpy.context, main)
    assert saved_groups['BODY'][main] == classes['BODY_NATIVE']
    assert saved_groups['HAIR'][main] == classes['HAIR_NATIVE']
    assert saved_groups['DRESS'] == native
    assert original.active(main), 'Artist file should retain the final Original view'
    assert {str(path): file_stamp(path) for path in (BEFORE, ARTIST)} == stamps
    result.update(after_main_bones=len(main.data.bones), owned_dress_bones=len(owned),
                  native_dress_bones=len(native[main]), dress_collection=collection.name,
                  shared_idrefs_valid=True, dress_collection_ownership_valid=True,
                  existing_body_hair_native_inventory_equal=True, original_active=True,
                  backup_and_artist_files_unchanged=True, success=True)
except Exception as error:
    result['error'] = f'{type(error).__name__}: {error}'
    raise
finally:
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    keys = ('success', 'error', 'version', 'before_main_bones', 'after_main_bones',
            'owned_dress_bones', 'native_dress_bones', 'all_mesh_raw_data_equal',
            'all_existing_236_rest_equal', 'original_active', 'backup_and_artist_files_unchanged')
    summary = {key: result[key] for key in keys if key in result}
    if 'existing_pose_channels' in result:
        summary['pose_channel_changed_counts'] = {
            role: item['changed_bones'] for role, item in result['existing_pose_channels']['classes'].items()}
    print('SHARED_DRESS_SAVED_READBACK', json.dumps(summary, ensure_ascii=False), flush=True)
