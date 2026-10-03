"""Native Dress pose repair on an isolated saved-X copy only.

Run serially with other Blender/Unity jobs. Never saves X.blend: all mutation,
one deliberate test rotation, and save/reopen stay in a disposable candidate.
The output is evidence for this task, not a central optimisation record.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Quaternion, Vector

REPOSITORY = Path('D:/MyRepository/Blender-addons-by-Randy')
PROJECT = Path('D:/Blender/Projects/Character/X')
ARTIST = PROJECT / 'X.blend'
OUTPUT = PROJECT / 'Validation/dress_original_20261003'
REPORT = OUTPUT / 'real_x_dress_original.json'
CANDIDATE = OUTPUT / 'X_dress_original_candidate.blend'
BASELINE_ONLY = '--baseline-only' in sys.argv
SETTLE_ORIGINAL = '--settle-original' in sys.argv
if BASELINE_ONLY:
    REPORT = OUTPUT / 'real_x_dress_original_baseline.json'
    CANDIDATE = OUTPUT / 'X_dress_original_baseline_candidate.blend'
elif SETTLE_ORIGINAL:
    REPORT = OUTPUT / 'real_x_dress_original_settled.json'
    CANDIDATE = OUTPUT / 'X_dress_original_settled_candidate.blend'
assert CANDIDATE.resolve() != ARTIST.resolve()
sys.path[:0] = [str(REPOSITORY / 'addons'), str(REPOSITORY / 'tests')]

import character_designer
from character_designer import body_original_mode as original, skirt_rig as skirt
from character_designer import skirt_original_mode as dress_original
from test_skirt_shared_rig_blender import (
    content_digest, meshes_content, rest_state, pose_channels, world_pose,
    world_vertices, geometry_error, matrix_error, matrix_values,
)
from test_skirt_original_mode_blender import colors_state

POSE_LIMIT = 5e-5
GEOMETRY_LIMIT = 5e-5


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


def graph_state():
    """Permanent relationships; switchable display/mix/basis are separate."""
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


def pose_error(rig, expected):
    actual = world_pose(rig, expected)
    return max((matrix_error(matrix, actual[name]) for name, matrix in expected.items()), default=0.0)


def detailed_pose_errors(rig, expected):
    actual = world_pose(rig, expected)
    values = {name: matrix_error(matrix, actual[name]) for name, matrix in expected.items()}
    ranked = sorted(values, key=values.get, reverse=True)
    frames = {}
    for name in ranked:
        before, after = expected[name], actual[name]
        angles = []
        for axis in range(3):
            left, right = before.to_3x3().col[axis].normalized(), after.to_3x3().col[axis].normalized()
            angles.append(math.atan2(left.cross(right).length, left.dot(right)))
        frames[name] = {'matrix_max': values[name],
                        'head_displacement_m': (before.translation - after.translation).length,
                        'tail_displacement_m': (
                            before @ Vector((0, rig.data.bones[name].length, 0))
                            - after @ Vector((0, rig.data.bones[name].length, 0))).length,
                        'normalised_axis_angle_radians': max(angles),
                        'desired_world_matrix': matrix_values(before),
                        'actual_world_matrix': matrix_values(after)}
    return {'ranked_names': ranked, 'bones': frames}


def native_colour_details(rig, names):
    details = {}
    for name in names:
        pose = rig.pose.bones[name]
        effective = pose.color if pose.color.palette != 'DEFAULT' else pose.bone.color
        details[name] = {'bone_palette': pose.bone.color.palette,
                         'pose_palette': pose.color.palette,
                         'effective_palette': effective.palette,
                         'normal': tuple(effective.custom.normal),
                         'select': tuple(effective.custom.select),
                         'active': tuple(effective.custom.active)}
    return details


def run_switch(action):
    result = bpy.ops.character_designer.body_original_mode(action=action)
    assert result == {'FINISHED'}, (action, result)


def assert_protected(meshes, rests, graph, colors):
    assert meshes_content(bpy.data) == meshes, 'Raw vertex/Shape Key/UV/weights data changed'
    assert {obj.name: rest_state(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'} == rests, 'Rest bones changed'
    assert graph_state() == graph, 'Armature, mesh, parent or constraint relationships changed'
    assert {obj.name: colors_state(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'} == colors, 'Artist colours changed'


result = {'success': False, 'artist_path': str(ARTIST), 'candidate_path': str(CANDIDATE),
          'artist_saved_by_verifier': False, 'version': list(character_designer.bl_info['version']),
          'blender_version': list(bpy.app.version), 'pose_limit': POSE_LIMIT,
          'geometry_limit_m': GEOMETRY_LIMIT,
          'diagnostic_baseline_only': BASELINE_ONLY, 'settle_old_original_first': SETTLE_ORIGINAL}
artist_before = file_state(ARTIST)
result['artist_before'] = artist_before
try:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(ARTIST), load_ui=False, use_scripts=False)
    main, source = bpy.data.objects['CoshaRig'], bpy.data.objects['Dress']
    assert source[skirt.RIG_KEY] == main
    record = skirt.read_record(source)
    assert skirt.is_shared(record)
    names = tuple(name for chain in record['chains'] for name in chain['def']) + (
        record['controls']['waist'],)
    assert len(names) == 33, ('Unexpected current Cosha Dress domain', len(names))
    native_name = record['chains'][0]['def'][1]
    owned = set(record['shared']['names'])
    meshes = meshes_content(bpy.data)
    rests = {obj.name: rest_state(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'}
    colors = {obj.name: colors_state(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'}
    graph = graph_state()
    other_channels = {obj.name: pose_channels(obj) for obj in bpy.data.objects
                      if obj.type == 'ARMATURE' and obj != main}
    initial_active = original.active(main)
    if initial_active:
        saved = json.loads(main[original.SESSION])
        expected_non_dress = saved['channels']
    else:
        expected_non_dress = original._channels(main)
    native_colours = native_colour_details(main, names)
    pink = sum(1 for state in native_colours.values()
               if state['effective_palette'] == 'THEME05'
               or (state['effective_palette'] == 'CUSTOM'
                   and state['normal'][0] > state['normal'][1]
                   and state['normal'][0] > state['normal'][2]))
    result.update(initial_original_active=initial_active,
                  initial_legacy_display_session=initial_active and 'dress_edit' not in saved,
                  main_bones=len(main.data.bones), native_dress_bones=len(names),
                  pink_native_count=pink, native_colour_details=native_colours,
                  protected_content_hash=content_digest(meshes))
    skirt._activate(bpy.context, main, 'POSE')
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    before_pose, before_vertices = world_pose(main, names), world_vertices(source)
    start = time.perf_counter()
    run_switch('ORIGINAL')
    result['original_upgrade_seconds'] = time.perf_counter() - start
    assert original.active(main)
    assert json.loads(main[original.SESSION])['dress_edit']
    result['original_upgrade_pose_error'] = pose_error(main, before_pose)
    result['original_upgrade_mesh_error_m'] = geometry_error(before_vertices, world_vertices(source))
    assert result['original_upgrade_pose_error'] <= POSE_LIMIT
    assert result['original_upgrade_mesh_error_m'] <= GEOMETRY_LIMIT
    assert_protected(meshes, rests, graph, colors)
    upgraded = main[original.SESSION]
    run_switch('ORIGINAL')
    assert main[original.SESSION] == upgraded, 'Clicking blue Original replaced the saved session'
    if SETTLE_ORIGINAL:
        legacy_pose, legacy_vertices = world_pose(main, names), world_vertices(source)
        run_switch('CONTROLS')
        result['old_original_no_edit_baseline_pose_error'] = pose_error(main, legacy_pose)
        result['old_original_no_edit_baseline_mesh_error_m'] = geometry_error(legacy_vertices, world_vertices(source))
        result['old_original_return_within_feature_tolerance'] = (
            result['old_original_no_edit_baseline_pose_error'] <= POSE_LIMIT
            and result['old_original_no_edit_baseline_mesh_error_m'] <= GEOMETRY_LIMIT)
        result['old_original_no_edit_baseline_errors'] = detailed_pose_errors(main, legacy_pose)
        assert_protected(meshes, rests, graph, colors)
        run_switch('ORIGINAL')
        before_pose, before_vertices = world_pose(main, names), world_vertices(source)
    untouched_pose = world_pose(main, [name for name in main.pose.bones.keys() if name not in owned])
    mechanisms = tuple(name for chain in record['chains'] for kind in ('manual', 'phys') for name in chain[kind])
    mechanism_before = world_pose(main, mechanisms)
    if not BASELINE_ONLY:
        native = main.pose.bones[native_name]
        native.rotation_mode = 'QUATERNION'
        native.rotation_quaternion = native.matrix_basis.to_quaternion() @ Quaternion((1, 0, 0), .08)
        main.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
    edited_pose, edited_vertices = world_pose(main, names), world_vertices(source)
    result['test_rotated_bone'] = native_name
    result['direct_rotation_mesh_displacement_m'] = geometry_error(before_vertices, edited_vertices)
    if not BASELINE_ONLY:
        assert result['direct_rotation_mesh_displacement_m'] > 1e-5, 'Original Dress rotation did not affect its skin'
    result['unowned_pose_edit_error'] = pose_error(main, untouched_pose)
    assert result['unowned_pose_edit_error'] <= POSE_LIMIT, 'Dress edit changed an unrelated pose'
    assert_protected(meshes, rests, graph, colors)
    run_switch('CONTROLS')
    assert not original.active(main)
    if not BASELINE_ONLY:
        assert source.get(dress_original.CORRECTIONS)
    correction = source.get(dress_original.CORRECTIONS)
    result['return_pose_error'] = pose_error(main, edited_pose)
    result['return_mesh_error_m'] = geometry_error(edited_vertices, world_vertices(source))
    result['return_native_pose_errors'] = detailed_pose_errors(main, edited_pose)
    result['return_manual_physics_pose_errors'] = detailed_pose_errors(main, mechanism_before)
    assert result['return_pose_error'] <= POSE_LIMIT
    assert result['return_mesh_error_m'] <= GEOMETRY_LIMIT
    assert original._channels(main) == expected_non_dress, 'Body/Hair/control channels were not precisely restored'
    assert other_channels == {obj.name: pose_channels(obj) for obj in bpy.data.objects
                              if obj.type == 'ARMATURE' and obj != main}
    assert_protected(meshes, rests, graph, colors)
    repeat_channels = pose_channels(main)
    repeat_pose, repeat_vertices = world_pose(main, names), world_vertices(source)
    repeat_errors = []
    for _repeat in range(2):
        run_switch('ORIGINAL')
        run_switch('CONTROLS')
        repeat_errors.append({'pose': pose_error(main, repeat_pose),
                              'mesh_m': geometry_error(repeat_vertices, world_vertices(source))})
        assert repeat_errors[-1]['pose'] <= POSE_LIMIT
        assert repeat_errors[-1]['mesh_m'] <= GEOMETRY_LIMIT
        assert source.get(dress_original.CORRECTIONS) == correction
        assert pose_channels(main) == repeat_channels
    result['repeat_no_edit_errors'] = repeat_errors
    assert_protected(meshes, rests, graph, colors)
    candidate_pose, candidate_vertices = world_pose(main, names), world_vertices(source)
    main_name, source_name = main.name, source.name
    bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE), copy=True)
    assert CANDIDATE.exists()
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE), load_ui=False, use_scripts=False)
    main, source = bpy.data.objects[main_name], bpy.data.objects[source_name]
    assert not original.active(main)
    assert source.get(dress_original.CORRECTIONS) == correction
    assert source[skirt.RIG_KEY] == main
    result['saved_reopen_pose_error'] = pose_error(main, candidate_pose)
    result['saved_reopen_mesh_error_m'] = geometry_error(candidate_vertices, world_vertices(source))
    assert result['saved_reopen_pose_error'] <= POSE_LIMIT
    assert result['saved_reopen_mesh_error_m'] <= GEOMETRY_LIMIT
    assert pose_channels(main) == repeat_channels
    assert_protected(meshes, rests, graph, colors)
    result.update(all_raw_mesh_keys_uv_weights_equal=True, all_rest_equal=True,
                  all_permanent_relationships_equal=True, all_character_colours_equal=True,
                  saved_candidate_reopened=True, candidate_sha256=file_state(CANDIDATE)['sha256'])
    result['success'] = True
except Exception as error:
    result['error'] = repr(error)
    raise
finally:
    result['artist_after'] = file_state(ARTIST)
    result['artist_unchanged'] = result['artist_after'] == artist_before
    if not result['artist_unchanged']:
        result['success'] = False
    OUTPUT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('REAL_X_DRESS_ORIGINAL', json.dumps(result, ensure_ascii=False), flush=True)
    assert result['artist_unchanged'], 'Artist file changed during isolated verification'
