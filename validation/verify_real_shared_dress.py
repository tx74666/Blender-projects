"""Migrate the saved Cosha in isolation and save only a separate candidate.

This script must be scheduled serially with other Blender/Unity jobs.  It never
overwrites X.blend and records geometry, Shape Key, weights and pose evidence.
"""
import json
from pathlib import Path
import sys
import time

import bpy

ROOT = Path('D:/MyRepository/Blender-addons-by-Randy')
sys.path[:0] = [str(ROOT / 'addons'), str(ROOT / 'tests')]
import character_designer
from character_designer import skirt_rig as skirt
from character_designer import body_original_mode as original, bone_display as display
from character_designer import body_calibration as calibration
from test_skirt_shared_rig_blender import (
    meshes_content, content_digest, rest_state, pose_channels, world_pose,
    world_vertices, world_cage, geometry_error, matrix_error, export_skeleton_state,
    world_frames, world_rest_frames, frame_errors, geometry_extent,
    CONTROL_POSITION_RELATIVE, CAGE_POSITION_RELATIVE, SOLVER_POSITION_RELATIVE,
    CONTROL_AXIS_LIMIT, SOLVER_AXIS_LIMIT,
)

ARTIST = Path('D:/Blender/Projects/Character/X/X.blend')
OUT = ARTIST.parent / 'validation/shared_dress_real_verification_20261003.json'
CANDIDATE = ARTIST.parent / 'validation/shared_dress_candidate_20261003.blend'
assert CANDIDATE.resolve() != ARTIST.resolve()


def pose_error(actual, before):
    return max((matrix_error(actual[name], before[name]) for name in before), default=0.0)


def check_frames(errors, controls, extent):
    for name, error in errors.items():
        position_limit = extent * (CONTROL_POSITION_RELATIVE if name in controls else SOLVER_POSITION_RELATIVE)
        axis_limit = CONTROL_AXIS_LIMIT if name in controls else SOLVER_AXIS_LIMIT
        assert max(error['head'], error['tail']) <= position_limit, (name, error, position_limit)
        assert error['axis'] <= axis_limit, (name, error, axis_limit)


def frame_summary(errors, names):
    selected = [errors[name] for name in names]
    return {'head_tail_m': max((max(error['head'], error['tail']) for error in selected), default=0),
            'axis_radians': max((error['axis'] for error in selected), default=0)}


result = {'success': False, 'artist_path': str(ARTIST), 'saved_artist_scene': False,
          'candidate': str(CANDIDATE), 'version': list(character_designer.bl_info['version'])}
try:
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(ARTIST))
    artist_stat = (ARTIST.stat().st_size, ARTIST.stat().st_mtime_ns)
    main = bpy.data.objects['CoshaRig']
    source = bpy.data.objects['Dress']
    legacy = source[skirt.RIG_KEY]
    assert legacy is not main
    assert original.active(main), 'Current saved Cosha should retain its authored Original session'
    before_exit_meshes = {obj.name: world_vertices(obj) for obj in bpy.context.scene.objects
                         if obj.type == 'MESH' and obj.visible_get()}
    exit_body_names = original._native_groups(bpy.context, main)['BODY'][main]
    before_exit_body = world_pose(main, exit_body_names)
    before_exit_dress = world_pose(legacy)
    original.leave(bpy.context, main)
    result['original_exit_mesh_errors'] = {
        name: geometry_error(before, world_vertices(bpy.data.objects[name]))
        for name, before in before_exit_meshes.items()}
    after_exit_body = world_pose(main, exit_body_names)
    result['original_exit_body_pose_errors'] = {
        name: matrix_error(before, after_exit_body[name]) for name, before in before_exit_body.items()}
    after_exit_dress = world_pose(legacy)
    result['original_exit_dress_pose_errors'] = {
        name: matrix_error(before, after_exit_dress[name]) for name, before in before_exit_dress.items()}
    result['original_exit_mesh_max_error'] = max(result['original_exit_mesh_errors'].values(), default=0.0)
    result['original_exit_body_pose_max_error'] = max(result['original_exit_body_pose_errors'].values(), default=0.0)
    result['original_exit_dress_pose_max_error'] = max(result['original_exit_dress_pose_errors'].values(), default=0.0)
    # The existing Original -> Controls transaction, before any migration,
    # produced 0.084127 mm of Dress Spline IK evaluation drift in attempt 2.
    # Bound and report that baseline separately from the measured native solver
    # bounds below and the exact protected-data comparisons.
    result['original_exit_mesh_error_limit'] = 1e-4
    for name, error in result['original_exit_mesh_errors'].items():
        assert error < result['original_exit_mesh_error_limit'], (
            f'Original -> Controls changed {name} world geometry: {error:.9g}')
    record = skirt.read_record(source)
    names = tuple(legacy.data.bones.keys())
    main_names = tuple(main.data.bones.keys())
    before_mesh_data = meshes_content()
    before_rest = rest_state(main)
    before_channels = pose_channels(main)
    before_main_pose = world_pose(main)
    before_native = original._native_groups(bpy.context, main)
    body = set(before_native['BODY'][main])
    hair = set(before_native['HAIR'][main])
    native_dress = set(before_native['DRESS'][legacy])
    before_dress_rest = world_rest_frames(main, legacy, names)
    calibration_before = calibration.native_rest(main)
    legacy_export = export_skeleton_state(main, legacy)
    # Disposable export/rest checks may re-evaluate native Spline IK. Capture
    # current physical frames again after those read-only evaluation steps.
    before_dress_pose = world_frames(legacy)
    before_world = {obj.name: world_vertices(obj) for obj in bpy.context.scene.objects
                    if obj.type == 'MESH' and obj.visible_get()}
    before_cage = world_cage(source, record)
    extent = geometry_extent(world_vertices(source))
    controls, deform, mechanism = skirt._bone_collection_layout(record)
    result['physical_frame_limits'] = {
        'source_extent_m': extent, 'control_position_m': extent * CONTROL_POSITION_RELATIVE,
        'cage_position_m': extent * CAGE_POSITION_RELATIVE,
        'solver_position_m': extent * SOLVER_POSITION_RELATIVE,
        'control_axis_radians': CONTROL_AXIS_LIMIT, 'solver_axis_radians': SOLVER_AXIS_LIMIT}
    result.update(before_main_bones=len(main_names), before_skirt_bones=len(names),
                  body_native=len(body), hair_native=len(hair), dress_native=len(native_dress),
                  old_rig=legacy.name, protected_content_hash=content_digest(before_mesh_data))
    start = time.perf_counter()
    migrated = skirt.unify_skirt(bpy.context, source, main)
    result['migration_seconds'] = time.perf_counter() - start
    assert skirt.is_shared(migrated)
    assert source[skirt.RIG_KEY] is main
    assert len(main.data.bones) == len(main_names) + len(names)
    assert result['old_rig'] not in bpy.data.objects
    assert meshes_content() == before_mesh_data, 'Mesh, Shape Keys, UV or vertex weights changed'
    assert rest_state(main, main_names) == before_rest, 'Existing Body/Hair rest bones changed'
    assert pose_channels(main, main_names) == before_channels, 'Existing Body/Hair pose channels changed'
    assert calibration.native_rest(main) == calibration_before, 'Body calibration rest inventory changed'
    result['main_pose_error'] = pose_error(world_pose(main, main_names), before_main_pose)
    result['skirt_pose_frame_errors'] = frame_errors(world_frames(main, names), before_dress_pose)
    result['skirt_rest_frame_errors'] = frame_errors(world_rest_frames(main, main, names), before_dress_rest)
    result['skirt_control_frames'] = frame_summary(result['skirt_pose_frame_errors'], controls)
    result['skirt_solver_frames'] = frame_summary(result['skirt_pose_frame_errors'], set(names) - controls)
    result['skirt_rest_frames'] = frame_summary(result['skirt_rest_frame_errors'], names)
    assert result['main_pose_error'] < 8e-5
    check_frames(result['skirt_pose_frame_errors'], controls, extent)
    # Rest has no Spline IK solver drift and therefore uses the control bounds.
    check_frames(result['skirt_rest_frame_errors'], set(names), extent)
    result['mesh_errors'] = {name: geometry_error(before, world_vertices(bpy.data.objects[name]))
                             for name, before in before_world.items()}
    result['cage_errors'] = {name: geometry_error(before, world_vertices(bpy.data.objects[name]))
                             for name, before in before_cage.items()}
    for name, error in result['mesh_errors'].items():
        limit = extent * SOLVER_POSITION_RELATIVE if name == source.name else 8e-5
        assert error <= limit, (name, error, limit)
    assert max(result['cage_errors'].values(), default=0) <= extent * CAGE_POSITION_RELATIVE
    controls, deform, mechanism = skirt._bone_collection_layout(migrated)
    collection = main.data.collections_all[migrated['shared']['collection']]
    assert set(collection.bones.keys()) == set(names)
    assert all(set(main.data.bones[name].collections) == {collection} for name in names)
    after_native = original._native_groups(bpy.context, main)
    assert after_native['BODY'][main] == body and after_native['HAIR'][main] == hair
    assert after_native['DRESS'] == {main: native_dress}
    assert source.modifiers[migrated['modifier']].object is main
    for name in migrated['cage']:
        for modifier in bpy.data.objects[name].modifiers:
            if modifier.type == 'HOOK':
                assert modifier.object is main and modifier.subtarget in names
    result['hook_count'] = sum(modifier.type == 'HOOK' for name in migrated['cage']
                               for modifier in bpy.data.objects[name].modifiers)
    physics_path = main.pose.bones[migrated['controls']['waist']].path_from_id() + '["physics_influence"]'
    skirt_drivers = [curve for curve in main.animation_data.drivers
                    if any(name in curve.data_path for name in names)]
    assert len(skirt_drivers) == len(deform)
    result['dress_driver_count'] = len(skirt_drivers)
    for curve in skirt_drivers:
        for variable in curve.driver.variables:
            for target in variable.targets:
                assert target.id is main and target.data_path == physics_path
    original.enter(bpy.context, main)
    assert original._native_groups(bpy.context, main)['DRESS'] == {main: native_dress}
    assert all(not main.data.bones[name].hide for name in native_dress)
    assert original.group_visible(bpy.context, main, 'DRESS')
    original.show_group(bpy.context, main, 'DRESS')
    assert not original.group_visible(bpy.context, main, 'DRESS')
    assert original.group_visible(bpy.context, main, 'BODY')
    assert original.group_visible(bpy.context, main, 'HAIR')
    original.show_group(bpy.context, main, 'DRESS')
    waist = main.pose.bones[migrated['controls']['waist']]
    waist_location = waist.location.copy()
    waist.location.x += 0.0002
    edited_location = waist.location.copy()
    bpy.context.view_layer.update()
    original.leave(bpy.context, main)
    assert (waist.location - edited_location).length < 1e-8, 'Original return erased authored Dress pose'
    waist.location = waist_location
    bpy.context.view_layer.update()
    result['original_dress_pose_edit_retained'] = True
    display.show_controls(bpy.context, main, 'DRESS', toggle=False)
    assert all(not main.data.bones[name].hide for name in controls)
    assert all(main.data.bones[name].hide for name in deform | mechanism)
    assert meshes_content() == before_mesh_data
    from character_designer import unity_export_worker as worker
    clone = main.copy()
    clone.data = main.data.copy()
    clone.name = '__SharedDressExportValidation'
    bpy.context.collection.objects.link(clone)
    clone_data = clone.data
    expected_character = {name for name in main_names if not worker._is_control(main.data.bones[name])}
    expected_dress = deform | {migrated['controls']['waist']}
    try:
        skirt._activate(bpy.context, clone, 'OBJECT')
        worker._clean_skeleton(bpy.context, clone, [clone])
        assert set(clone.data.bones.keys()) == expected_character | expected_dress
        assert not set(clone.data.bones.keys()) & mechanism
        result.update(export_character_bones=len(expected_character),
                      export_dress_bones=len(expected_dress),
                      export_dress_names=sorted(expected_dress),
                      export_control_mechanism_filter_valid=True)
    finally:
        if clone.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.data.objects.remove(clone, do_unlink=True)
        if clone_data.users == 0:
            bpy.data.armatures.remove(clone_data)
    skirt._activate(bpy.context, main, 'POSE')
    shared_export = export_skeleton_state(main)
    assert set(shared_export) == set(legacy_export), 'Export bone names changed'
    export_errors = {}
    for name, previous in legacy_export.items():
        actual = shared_export[name]
        assert actual[:3] == previous[:3], name
        export_errors[name] = matrix_error(actual[3], previous[3])
        assert export_errors[name] < 8e-5 and abs(actual[4] - previous[4]) < 8e-5, name
    result.update(legacy_shared_export_names_parents_equal=True,
                  export_rest_max_error=max(export_errors.values(), default=0.0))
    result.update(after_main_bones=len(main.data.bones), single_character_rig=True,
                  native_collections=list(main.data.collections_all.keys()),
                  body_hair_rest_and_channels_unchanged=True, all_mesh_data_unchanged=True,
                  dress_hooks_drivers_rewired=True, original_controls_validated=True)
    # Retain the artist's preferred Original + Dress view in the candidate.
    original.enter(bpy.context, main)
    assert original.group_visible(bpy.context, main, 'DRESS')
    bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE))
    assert CANDIDATE.exists()
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE))
    main, source = bpy.data.objects['CoshaRig'], bpy.data.objects['Dress']
    assert source[skirt.RIG_KEY] is main
    assert source in skirt.shared_sources(main)
    assert skirt.is_shared(skirt.read_record(source))
    assert original.active(main)
    assert original.group_visible(bpy.context, main, 'DRESS')
    assert meshes_content() == before_mesh_data
    assert len(main.data.bones) == len(main_names) + len(names)
    assert (ARTIST.stat().st_size, ARTIST.stat().st_mtime_ns) == artist_stat
    result.update(saved_candidate=True, save_reopen_idrefs_valid=True,
                  artist_file_untouched=True, success=True)
except Exception as error:
    result['error'] = f'{type(error).__name__}: {error}'
    raise
finally:
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    summary_keys = ('success', 'version', 'error', 'candidate', 'saved_artist_scene',
                    'before_main_bones', 'before_skirt_bones', 'after_main_bones',
                    'original_exit_mesh_max_error', 'original_exit_body_pose_max_error',
                    'main_pose_error', 'skirt_control_frames', 'skirt_solver_frames',
                    'skirt_rest_frames', 'physical_frame_limits',
                    'export_rest_max_error', 'saved_candidate', 'save_reopen_idrefs_valid')
    summary = {key: result[key] for key in summary_keys if key in result}
    print('SHARED_DRESS_REAL_VERIFICATION', json.dumps(summary, ensure_ascii=False), flush=True)
