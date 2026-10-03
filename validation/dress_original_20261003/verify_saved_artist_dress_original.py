"""Read saved artist data against the persistent pre-change backup only.

No registration, scene operation, posing, runtime upgrade or .blend save occurs.
Only this task's JSON evidence is written. Start after the artist SAVE succeeds.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy

REPOSITORY = Path('D:/MyRepository/Blender-addons-by-Randy')
PROJECT = Path('D:/Blender/Projects/Character/X')
OUTPUT = PROJECT / 'Validation/dress_original_20261003'
BEFORE = OUTPUT / 'before_live_change/X_before_dress_original.blend'
ARTIST = PROJECT / 'X.blend'
REPORT = OUTPUT / 'saved_artist_readback.json'
sys.path[:0] = [str(REPOSITORY / 'addons'), str(REPOSITORY / 'tests')]

import character_designer
from character_designer import body_original_mode as original, skirt_rig as skirt
from test_skirt_shared_rig_blender import meshes_content, rest_state, content_digest, matrix_values
from test_skirt_original_mode_blender import colors_state


def file_state(path):
    stat = path.stat()
    return {'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def constraints_state(owner):
    return tuple((constraint.name, constraint.type,
                  tuple((key, getattr(getattr(constraint, key, None), 'name', None))
                        for key in ('target', 'pole_target', 'space_object')),
                  tuple((key, getattr(constraint, key, None))
                        for key in ('subtarget', 'pole_subtarget', 'owner_space', 'target_space')),
                  tuple((entry.target.name if entry.target else None, entry.subtarget, entry.weight)
                        for entry in getattr(constraint, 'targets', ())))
                 for constraint in owner.constraints)


def relationships():
    result = {}
    for obj in bpy.data.objects:
        result[obj.name] = {
            'type': obj.type,
            'parent': (obj.parent.name if obj.parent else None, obj.parent_type, obj.parent_bone,
                       matrix_values(obj.matrix_parent_inverse)),
            'modifiers': tuple((modifier.name, modifier.type,
                                getattr(getattr(modifier, 'object', None), 'name', None),
                                getattr(modifier, 'subtarget', None),
                                getattr(modifier, 'vertex_group', None),
                                matrix_values(modifier.matrix_inverse)
                                if hasattr(modifier, 'matrix_inverse') else None)
                               for modifier in obj.modifiers),
            'constraints': constraints_state(obj),
        }
        if obj.type == 'ARMATURE':
            result[obj.name]['pose_constraints'] = {pb.name: constraints_state(pb) for pb in obj.pose.bones}
            result[obj.name]['collections'] = {
                collection.name: (collection.parent.name if collection.parent else None,
                                  tuple(sorted(collection.bones.keys())))
                for collection in obj.data.collections_all}
    return result


def snapshot():
    return {'meshes': meshes_content(bpy.data),
            'rest': {obj.name: rest_state(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'},
            'relationships': relationships(),
            'colours': {obj.name: colors_state(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'}}


result = {'success': False, 'artist': str(ARTIST), 'before_backup': str(BEFORE),
          'version': list(character_designer.bl_info['version']),
          'blender_version': list(bpy.app.version), 'runtime_registered': False,
          'scene_operations_or_pose_edits': False, 'blend_saved_by_verifier': False}
stamps = {str(path): file_state(path) for path in (BEFORE, ARTIST)}
try:
    bpy.ops.wm.open_mainfile(filepath=str(BEFORE), load_ui=False, use_scripts=False)
    before = snapshot()
    result['protected_mesh_hash_before'] = content_digest(before['meshes'])
    bpy.ops.wm.open_mainfile(filepath=str(ARTIST), load_ui=False, use_scripts=False)
    after = snapshot()
    result['protected_mesh_hash_after'] = content_digest(after['meshes'])
    for name in ('meshes', 'rest', 'relationships', 'colours'):
        result[name + '_differences'] = sorted(
            key for key in set(before[name]) | set(after[name])
            if before[name].get(key) != after[name].get(key))
        assert not result[name + '_differences'], (name, result[name + '_differences'])
    main, source = bpy.data.objects['CoshaRig'], bpy.data.objects['Dress']
    record = skirt.read_record(source)
    assert source[skirt.RIG_KEY] == main and skirt.is_shared(record)
    native = tuple(name for chain in record['chains'] for name in chain['def']) + (
        record['controls']['waist'],)
    deform = tuple(name for chain in record['chains'] for name in chain['def'])
    assert bpy.context.scene.frame_current == 39
    assert len(main.data.bones) == 351
    assert len(native) == 33 and len(deform) == 32
    assert original.active(main)
    session = json.loads(main[original.SESSION])
    assert session.get('dress_edit')
    assert any(entry['owner'] == record['owner'] for entry in session['dress_edit'])
    palettes = {}
    for name in native:
        pose = main.pose.bones[name]
        effective = pose.color if pose.color.palette != 'DEFAULT' else pose.bone.color
        palettes[name] = {'pose_palette': pose.color.palette, 'bone_palette': pose.bone.color.palette,
                          'effective_palette': effective.palette}
        assert effective.palette == 'THEME05', (name, palettes[name])
        assert not any(pose.lock_rotation), (name, 'rotation locks')
        assert not pose.lock_rotation_w and not pose.lock_rotations_4d, (name, 'quaternion locks')
    for name in deform:
        pose = main.pose.bones[name]
        manual, physics = pose.constraints['Skirt manual pose'], pose.constraints['Skirt physics delta']
        assert manual.mix_mode == 'BEFORE_FULL', (name, manual.mix_mode)
        assert not manual.mute and not physics.mute, (name, 'unexpected muted drive')
        assert physics.mix_mode == 'BEFORE'
    result.update(frame=bpy.context.scene.frame_current, main_bones=len(main.data.bones),
                  native_dress_bones=len(native), pink_native_count=len(palettes),
                  native_colour_palettes=palettes, original_active=True,
                  persistent_dress_session=True, before_full_deform_bones=len(deform),
                  native_rotation_locks_unlocked=True, generated_drives_remain_active=True,
                  all_raw_mesh_keys_uv_weights_equal=True, all_rest_equal=True,
                  all_permanent_relationships_equal=True, all_artist_colours_equal=True)
    result['success'] = True
except Exception as error:
    result['error'] = repr(error)
    raise
finally:
    result['file_stamps_before'] = stamps
    result['file_stamps_after'] = {str(path): file_state(path) for path in (BEFORE, ARTIST)}
    result['artist_and_backup_unchanged_by_verifier'] = stamps == result['file_stamps_after']
    if not result['artist_and_backup_unchanged_by_verifier']:
        result['success'] = False
    OUTPUT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('SAVED_ARTIST_DRESS_ORIGINAL', json.dumps(result, ensure_ascii=False), flush=True)
    assert result['artist_and_backup_unchanged_by_verifier'], 'A source file changed during readback'
