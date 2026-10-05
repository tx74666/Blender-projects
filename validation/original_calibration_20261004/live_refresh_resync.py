"""Guarded native X console integration, after isolated validation has passed.

Invoke only in the paused artist's Python Console:
    exec(compile(Path(...).read_text(encoding='utf-8'), ..., 'exec'),
         {'__file__': ...})

This script never opens a blend file or starts a calibration preview. It saves
an independent checkpoint, refreshes the installed add-on, accepts only the
authorized two upper-arm Rest edits, and saves X only after protection checks.
An error leaves the checkpoint and diagnostics; it does not rewrite artist data
to imitate recovery or replace the live scene with a background test result.
"""
import ast
import datetime
import hashlib
import importlib
import json
import math
import sys
import time
import traceback
from array import array
from pathlib import Path
from types import SimpleNamespace

import bpy

FOLDER = Path(__file__).resolve().parent
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
VALIDATION = FOLDER / 'validate_current_resync.json'
REPORT = FOLDER / 'live_refresh_resync.json'
VERSION = (0, 74, 0)
EXPECTED_CHANGED = {'upper_arm.L', 'upper_arm.R'}
POSE_LIMIT = 4e-4


def snapshot_helpers():
    """Reuse reviewed readers without importing its background entry point.

    probe_current imports canonical sources at module scope; live integration
    must instead retain Blender's installed package and sys.path unchanged.
    Extract only these read-only function definitions from the local helper.
    """
    helper_path = FOLDER / 'probe_current.py'
    names = {'sha_file', 'fingerprint', 'plain', 'custom', 'matrix', 'rna_fields',
             'data_hash', 'bulk', 'mesh_snapshot', 'bone_rest', 'differences'}
    parsed = ast.parse(helper_path.read_text(encoding='utf-8'), str(helper_path))
    nodes = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in nodes} != names:
        raise RuntimeError('The reviewed snapshot helper definitions changed.')
    namespace = {'bpy': bpy, 'hashlib': hashlib, 'json': json, 'math': math,
                 'array': array, 'Path': Path}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(helper_path), 'exec'), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in names})


def modules():
    addon = sys.modules.get('character_designer')
    if addon is None:
        raise RuntimeError('The installed Character Designer runtime is not loaded.')
    result = {'addon': addon}
    for name in ('body_original_mode', 'control_pose_assets', 'forearm_twist', 'limb_ik'):
        result[name] = importlib.import_module('character_designer.' + name)
    return SimpleNamespace(**result)


def no_preview(forearm):
    if forearm._SESSION is not None:
        raise RuntimeError('An active Forearm preview must be finished by the artist first.')
    marked = [obj.name for obj in bpy.data.objects if forearm.PREVIEW_KEY in obj]
    if marked:
        raise RuntimeError('A persisted Forearm preview exists; do not refresh or save: ' + ', '.join(marked))


def raw_meshes(probe):
    return {obj.name: probe.mesh_snapshot(obj) for obj in bpy.data.objects if obj.type == 'MESH'}


def native_rest(poses):
    return {obj.name: poses.native_rest(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def native_pose(poses):
    return {obj.name: {name: obj.pose.bones[name].matrix.copy() for name in poses.native_rest(obj)}
            for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def mesh_check(probe, expected, facts, label):
    current = raw_meshes(probe)
    differences = []
    for name in sorted(set(expected) | set(current)):
        before, after = expected.get(name), current.get(name)
        if before != after:
            differences.append({'object': name, 'inventory_changed': before is None or after is None,
                                'changed_fields': [key for key in before if before[key] != after.get(key)]
                                                  if before and after else [],
                                'old_sha256': before.get('content_sha256') if before else None,
                                'new_sha256': after.get('content_sha256') if after else None})
    facts[label] = {'exact': not differences, 'mesh_objects': len(expected), 'differences': differences}
    if differences:
        raise AssertionError('Raw mesh, Shape Keys, weights or relationships changed: ' + label)


def rest_check(poses, expected, facts, label):
    current = native_rest(poses)
    facts[label] = {'exact': current == expected, 'armatures': len(expected),
                    'native_bones': sum(map(len, expected.values()))}
    if current != expected:
        raise AssertionError('The current author Rest must remain exactly unchanged: ' + label)


def pose_check(poses, expected, facts, label):
    current = native_pose(poses)
    if set(current) != set(expected) or any(set(current[name]) != set(before) for name, before in expected.items()):
        raise AssertionError('The native pose inventory changed: ' + label)
    maximum, worst = 0., None
    for object_name, before in expected.items():
        for name, old in before.items():
            now = current[object_name][name]
            if any(not math.isfinite(float(value)) for row in now for value in row):
                raise AssertionError('Non-finite native pose: ' + object_name + ':' + name)
            error = poses._difference(old, now)
            if not math.isfinite(error):
                raise AssertionError('Non-finite native pose error: ' + object_name + ':' + name)
            if error > maximum:
                maximum, worst = error, object_name + ':' + name
    facts[label] = {'maximum_matrix_error': maximum, 'worst': worst, 'tolerance': POSE_LIMIT,
                    'native_bones': sum(map(len, expected.values()))}
    if maximum > POSE_LIMIT:
        raise AssertionError('Native pose preservation failed: ' + label)


def surfaces_check(removal, rig, expected, facts, label):
    maximum, worst, vertices = 0., None, 0
    per_object = []
    for obj, points in expected:
        now = removal._surface(bpy.context, rig, obj)
        if len(now) != len(points):
            raise AssertionError('Evaluated surface topology changed: ' + obj.name)
        errors = [(old - new).length for old, new in zip(points, now)]
        if any(not math.isfinite(error) for error in errors):
            raise AssertionError('A bound surface has non-finite coordinates: ' + obj.name)
        error = max(errors, default=0.)
        vertices += len(points)
        per_object.append({'object': obj.name, 'vertices': len(points), 'maximum_position_error': error})
        if error > maximum:
            maximum, worst = error, obj.name
    facts[label] = {'maximum_position_error': maximum, 'worst': worst, 'vertices': vertices,
                    'tolerance': removal.SURFACE_TOLERANCE, 'objects': per_object}
    if maximum > removal.SURFACE_TOLERANCE:
        raise AssertionError('Bound surface preservation failed: ' + label)


def provenance(rig, key):
    raw = rig.get(key)
    return json.loads(raw) if raw else {'version': 1, 'events': []}


def installed_source(addon):
    expected = (Path(bpy.utils.user_resource('SCRIPTS')) / 'addons' / 'character_designer' / '__init__.py').resolve()
    actual = Path(addon.__file__).resolve()
    if actual != expected:
        raise RuntimeError('Unexpected loaded Character Designer source: ' + str(actual))
    return actual


def main(facts):
    if bpy.app.background or bpy.context.window is None or bpy.context.area is None:
        raise RuntimeError('This integration is only for the paused native artist window.')
    if bpy.context.area.type != 'CONSOLE':
        raise RuntimeError('Run this script from X\'s native Python Console only.')
    if Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('The current artist filepath must be exactly X.blend; no file was opened.')
    if bpy.context.mode not in {'OBJECT', 'POSE'}:
        raise RuntimeError('Finish the current Edit/Weight session before integration.')
    probe = snapshot_helpers()
    validation = json.loads(VALIDATION.read_text(encoding='utf-8'))
    if (validation.get('status') != 'passed' or validation.get('addon') != list(VERSION)
            or not validation.get('input_unchanged') or not validation.get('blend_saved')):
        raise RuntimeError('The isolated current-X validation has not passed; do not integrate.')
    if validation.get('input_after') != probe.fingerprint(FOLDER / 'X_live_input.blend'):
        raise RuntimeError('The validated input fingerprint no longer matches its saved file.')
    facts['isolated_validation'] = {'path': str(VALIDATION), 'sha256': probe.sha_file(VALIDATION),
                                    'source_schema': validation.get('source_schema'),
                                    'status': validation['status']}
    runtime = modules()
    source = installed_source(runtime.addon)
    no_preview(runtime.forearm_twist)
    if runtime.addon.ADDON_REFRESH_PENDING or bpy.app.timers.is_registered(runtime.addon._reload_addon_deferred):
        raise RuntimeError('A Refresh is already pending; wait for it to finish before integration.')
    rig = bpy.data.objects.get('CoshaRig')
    if rig is None or bpy.context.view_layer.objects.active != rig:
        raise RuntimeError('CoshaRig must remain the active object in this artist view layer.')
    original = runtime.body_original_mode
    if not original.active(rig):
        raise RuntimeError('The authorized current Original session is not active; no repair was applied.')
    raw_session = rig[original.SESSION]
    saved = json.loads(raw_session)
    changed = {row['bone'] for row in probe.differences(runtime.control_pose_assets.native_rest(rig), saved['rest'])
               if row.get('substantial', True)}
    if changed != EXPECTED_CHANGED:
        raise RuntimeError('The current intentional Rest edit scope changed; inspect before integration: ' + str(changed))
    if rig.data.get(runtime.limb_ik.SCHEMA_KEY) != validation.get('source_schema'):
        raise RuntimeError('The current rig schema differs from the validated Cosha input.')
    area = bpy.context.area
    facts.update({'runtime': bpy.app.version_string, 'addon_before': list(runtime.addon.bl_info['version']),
                  'addon_source': str(source), 'artist': str(ARTIST), 'artist_before': probe.fingerprint(ARTIST),
                  'scene': bpy.context.scene.name, 'view_layer': bpy.context.view_layer.name,
                  'original_session_raw_before': raw_session, 'changed_native_rest': sorted(changed),
                  'test_preview_started': False, 'artist_file_opened': False, 'artist_saved': False})
    bpy.context.view_layer.update()
    before_meshes = raw_meshes(probe)
    before_rest = native_rest(runtime.control_pose_assets)
    before_pose = native_pose(runtime.control_pose_assets)
    before_channels = original._channels(rig)
    facts['protected_input'] = {'raw_meshes': before_meshes, 'native_rest': before_rest,
                               'native_pose': {obj: {name: probe.matrix(matrix) for name, matrix in state.items()}
                                               for obj, state in before_pose.items()},
                               'channels': before_channels}
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    checkpoint = FOLDER / ('X_before_live_resync_' + stamp + '.blend')
    if checkpoint.exists() or checkpoint.resolve() == ARTIST:
        raise RuntimeError('Checkpoint must be a new independent file in the evidence folder.')
    facts['phase'] = 'save_independent_checkpoint'
    result = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True, check_existing=False))
    facts['checkpoint_save'] = result
    if result != ['FINISHED'] or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('The native independent checkpoint was not saved without changing artist filepath.')
    facts['checkpoint'] = probe.fingerprint(checkpoint)
    facts['artist_unchanged_after_checkpoint'] = probe.fingerprint(ARTIST) == facts['artist_before']
    if not facts['artist_unchanged_after_checkpoint']:
        raise RuntimeError('Artist disk file changed during checkpoint save; inspect before continuing.')
    mesh_check(probe, before_meshes, facts, 'raw_meshes_after_checkpoint')
    rest_check(runtime.control_pose_assets, before_rest, facts, 'native_rest_after_checkpoint')
    pose_check(runtime.control_pose_assets, before_pose, facts, 'native_pose_after_checkpoint')
    if rig.get(original.SESSION) != raw_session or original._channels(rig) != before_channels:
        raise AssertionError('Checkpoint save changed the Original session or channels.')
    facts['phase'] = 'refresh_installed_addon'
    old_reload = runtime.addon._reload_addon_deferred
    old_reload()
    runtime = modules()
    if installed_source(runtime.addon) != source or tuple(runtime.addon.bl_info['version']) != VERSION:
        raise RuntimeError('Refresh did not load the deployed 0.74.0 installed package.')
    if runtime.addon.ADDON_REFRESH_LAST_ERROR:
        raise RuntimeError('Refresh failed: ' + runtime.addon.ADDON_REFRESH_LAST_ERROR)
    runtime.addon._validate_registration_integrity()
    no_preview(runtime.forearm_twist)
    original, poses = runtime.body_original_mode, runtime.control_pose_assets
    if rig.get(original.SESSION) != raw_session or original._channels(rig) != before_channels:
        raise AssertionError('Refresh changed the exact Original session or channels.')
    bpy.context.view_layer.update()
    mesh_check(probe, before_meshes, facts, 'raw_meshes_after_refresh')
    rest_check(poses, before_rest, facts, 'native_rest_after_refresh')
    pose_check(poses, before_pose, facts, 'native_pose_after_refresh')
    facts['refresh'] = {'status': 'passed', 'addon': list(runtime.addon.bl_info['version']),
                        'source': runtime.addon.__file__, 'integrity': 'passed',
                        'session_exact': True, 'channels_exact': True}
    resync = importlib.import_module('character_designer.body_rest_resync')
    removal = importlib.import_module('character_designer.body_setup_removal')
    before_surfaces = removal._bound_surfaces(bpy.context, rig)
    before_history = provenance(rig, resync.PROVENANCE_KEY)
    facts['phase'] = 'authorized_original_to_controls_resync'
    started = time.perf_counter()
    left = original.leave(bpy.context, rig)
    facts['resync_seconds'] = time.perf_counter() - started
    if not left or original.active(rig):
        raise AssertionError('The authorized Original session did not return to Controls.')
    inventory = runtime.limb_ik._validate_inventory(rig)
    facts['strict_inventory'] = {'status': 'passed', 'schema': inventory['schema'],
                                 'rigs': [list(key) for key in sorted(inventory['rigs'])]}
    rest_check(poses, before_rest, facts, 'native_rest_after_resync')
    pose_check(poses, before_pose, facts, 'native_pose_after_resync')
    mesh_check(probe, before_meshes, facts, 'raw_meshes_after_resync')
    surfaces_check(removal, rig, before_surfaces, facts, 'bound_surfaces_after_resync')
    after_history = provenance(rig, resync.PROVENANCE_KEY)
    previous_events = before_history['events']
    if after_history['events'][:len(previous_events)] != previous_events:
        raise AssertionError('Existing Rest adaptation provenance was changed.')
    events = after_history['events'][len(previous_events):]
    if len(events) != 1 or set(events[0]['changed']) != EXPECTED_CHANGED:
        raise AssertionError('The adaptation did not record exactly one authorized upper-arm event.')
    facts['provenance'] = {'before_events': len(previous_events), 'after_events': len(after_history['events']),
                           'new_events': events}
    no_preview(runtime.forearm_twist)
    if Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Artist filepath changed before saving; no artist save was requested.')
    # Save the familiar Geometry Nodes editor, rather than the temporary console.
    facts['phase'] = 'restore_editor_before_artist_save'
    area.type = 'NODE_EDITOR'
    area.ui_type = 'GeometryNodeTree'
    if area.type != 'NODE_EDITOR' or area.ui_type != 'GeometryNodeTree':
        raise RuntimeError('The temporary console could not restore Geometry Nodes; inspect before saving.')
    facts['editor_restored'] = {'type': area.type, 'ui_type': area.ui_type}
    facts['phase'] = 'save_current_artist'
    facts['artist_save_requested'] = True
    facts['artist_save_result'] = sorted(bpy.ops.wm.save_mainfile())
    if facts['artist_save_result'] != ['FINISHED'] or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Blender did not confirm saving the current artist X.blend.')
    facts['artist_saved'] = True
    facts['artist_after'] = probe.fingerprint(ARTIST)
    if facts['artist_after'] == facts['artist_before']:
        raise RuntimeError('Artist disk evidence did not change after the completed adaptation.')
    facts['phase'] = 'verify_after_native_save'
    no_preview(runtime.forearm_twist)
    rest_check(poses, before_rest, facts, 'native_rest_after_save')
    pose_check(poses, before_pose, facts, 'native_pose_after_save')
    mesh_check(probe, before_meshes, facts, 'raw_meshes_after_save')
    surfaces_check(removal, rig, before_surfaces, facts, 'bound_surfaces_after_save')
    runtime.limb_ik._validate_inventory(rig)
    if original.active(rig) or provenance(rig, resync.PROVENANCE_KEY) != after_history:
        raise AssertionError('Saving changed the completed Controls state or provenance.')
    facts.update({'status': 'passed', 'phase': 'complete'})


def run():
    facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'status': 'starting', 'phase': 'preflight', 'artist_saved': False,
             'artist_save_requested': False, 'blind_recovery_performed': False}
    try:
        main(facts)
    except Exception as exc:
        facts.update({'status': 'failed', 'error': str(exc), 'traceback': traceback.format_exc()})
        if facts.get('checkpoint'):
            facts['recovery_checkpoint'] = facts['checkpoint']['path']
        # The add-on owns transactional rollback. Do not independently rewrite
        # channels/Shape Keys or replace live data if an integration check fails.
    finally:
        facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        REPORT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
        print('LIVE_X_REFRESH_RESYNC', facts['status'], facts.get('phase'), str(REPORT), flush=True)
        if facts.get('error'):
            print('LIVE_X_REFRESH_RESYNC_ERROR', facts['error'], flush=True)
    return facts


# Console exec callers deliberately need only __file__, not a special __name__.
LIVE_X_REFRESH_RESYNC_RESULT = run()
