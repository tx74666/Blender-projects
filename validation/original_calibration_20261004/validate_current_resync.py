"""Isolated actual-X validation of intentional Rest adaptation and forearm UI.

Runs only in a factory background Blender. Opens the saved validation input,
never the artist X.blend; saves an isolated result only when every check passes.
The baseline timing module is imported without registering its classes.
"""
import datetime
import importlib.util
import json
import math
import statistics
import sys
import time
import traceback
from pathlib import Path

import bpy

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER))
import probe_current as probe
from character_designer import (body_original_mode as original, body_rest_resync as resync,
    body_setup_removal as removal, control_pose_assets as poses, forearm_twist as forearm,
    limb_ik)
import character_designer

SOURCE = FOLDER / 'X_live_input.blend'
REPORT = FOLDER / 'validate_current_resync.json'
RESULT = FOLDER / 'X_resynced_test.blend'
BASELINE = FOLDER / 'baseline_body_original_mode_0734.py'
REST_LIMIT = 2e-6
POSE_LIMIT = 4e-4
SURFACE_LIMIT = removal.SURFACE_TOLERANCE


def activate(obj, mode='OBJECT'):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for item in bpy.context.selected_objects:
        item.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if mode != 'OBJECT':
        bpy.ops.object.mode_set(mode=mode)
    bpy.context.view_layer.update()


def all_raw_meshes():
    return {obj.name: probe.mesh_snapshot(obj) for obj in bpy.data.objects if obj.type == 'MESH'}


def all_native_rest():
    return {obj.name: poses.native_rest(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def all_native_pose():
    return {obj.name: {name: obj.pose.bones[name].matrix.copy() for name in poses.native_rest(obj)}
            for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def pose_errors(before):
    maximum, worst = 0., None
    for object_name, state in before.items():
        obj = bpy.data.objects.get(object_name)
        if obj is None or set(state) != set(poses.native_rest(obj)):
            raise AssertionError('Native pose inventory changed: ' + object_name)
        for name, matrix in state.items():
            error = poses._difference(matrix, obj.pose.bones[name].matrix)
            if not math.isfinite(error):
                raise AssertionError('Non-finite native pose: ' + object_name + ':' + name)
            if error > maximum:
                maximum, worst = error, object_name + ':' + name
    return {'maximum_matrix_error': maximum, 'worst': worst,
            'native_bones': sum(map(len, before.values())), 'tolerance': POSE_LIMIT}


def check_pose(before):
    result = pose_errors(before)
    if result['maximum_matrix_error'] > POSE_LIMIT:
        raise AssertionError('Native pose changed: ' + str(result))
    return result


def check_rest(before):
    after = all_native_rest()
    if set(before) != set(after):
        raise AssertionError('Native armature inventory changed.')
    differences = []
    for name, state in before.items():
        if set(state) != set(after[name]):
            raise AssertionError('Native Rest bone inventory changed in ' + name)
        differences.extend({'rig': name, **entry} for entry in probe.differences(after[name], state))
    significant = [entry for entry in differences if entry.get('substantial', True)]
    if significant:
        raise AssertionError('Native author Rest changed: ' + str(significant[:8]))
    return {'exact': before == after, 'within_tolerance': True,
            'max_matrix_error': max((entry.get('matrix_max_error', 0.) for entry in differences), default=0.),
            'max_length_error': max((abs(entry.get('length_delta', 0.)) for entry in differences), default=0.),
            'matrix_tolerance': REST_LIMIT, 'length_tolerance': 1e-6}


def mesh_differences(before, after):
    differences = []
    for name in sorted(set(before) | set(after)):
        old, now = before.get(name), after.get(name)
        if old is None or now is None:
            differences.append({'object': name, 'inventory_changed': True})
            continue
        if old != now:
            differences.append({'object': name, 'fields': [key for key in old if old[key] != now.get(key)],
                                'before_sha256': old['content_sha256'], 'after_sha256': now['content_sha256'],
                                'before_shape_keys': old['shape_keys'], 'after_shape_keys': now['shape_keys'],
                                'relationship_changed': old['relationship'] != now['relationship']})
    return differences


def check_meshes(before, facts, label):
    after = all_raw_meshes()
    differences = mesh_differences(before, after)
    facts[label] = {'exact': not differences, 'mesh_objects': len(before), 'differences': differences}
    if differences:
        raise AssertionError('Raw mesh / all Shape Key / relationship protection failed: ' + label)
    return after


def bound_surfaces(rig):
    return removal._bound_surfaces(bpy.context, rig)


def surface_errors(rig, before):
    maximum, worst, vertices = 0., None, 0
    per_object = []
    for obj, points in before:
        now = removal._surface(bpy.context, rig, obj)
        if len(now) != len(points):
            raise AssertionError('Evaluated surface topology changed: ' + obj.name)
        error = max(((first - second).length for first, second in zip(points, now)), default=0.)
        vertices += len(points)
        if error > maximum:
            maximum, worst = error, obj.name
        per_object.append({'object': obj.name, 'vertices': len(points), 'maximum_position_error': error})
    return {'maximum_position_error': maximum, 'worst': worst, 'vertices': vertices,
            'meshes': len(before), 'tolerance': SURFACE_LIMIT, 'objects': per_object}


def check_surfaces(rig, before):
    result = surface_errors(rig, before)
    if not math.isfinite(result['maximum_position_error']) or result['maximum_position_error'] > SURFACE_LIMIT:
        raise AssertionError('Bound surfaces changed: ' + str(result))
    return result


def provenance(rig):
    raw = rig.get(resync.PROVENANCE_KEY)
    return json.loads(raw) if raw else {'version': 1, 'events': []}


class JsonReads:
    """Count only a module's own Original JSON reads, not unrelated record IO."""
    def __init__(self, wrapped):
        self.wrapped, self.reads = wrapped, 0

    def loads(self, *args, **kwargs):
        self.reads += 1
        return self.wrapped.loads(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.wrapped, name)


def timed(module, action, rig):
    previous = module.json
    counter = JsonReads(previous)
    module.json = counter
    try:
        started = time.perf_counter()
        getattr(module, action)(bpy.context, rig)
        elapsed = time.perf_counter() - started
    finally:
        module.json = previous
    return {'seconds': elapsed, 'module_local_original_json_reads': counter.reads}


def timing_probe(rig, facts):
    spec = importlib.util.spec_from_file_location('character_designer._baseline_original', BASELINE)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    expected_rest, expected_pose = all_native_rest(), all_native_pose()
    expected_meshes = all_raw_meshes()
    samples = {'baseline_0.73.4': {'enter': [], 'leave': []},
               'current': {'enter': [], 'leave': []}}
    facts['timing'] = {'scope': 'Background isolated native operations; no GUI latency or FPS claim.',
                       'baseline_file': str(BASELINE), 'baseline_sha256': probe.sha_file(BASELINE),
                       'round_pairs': 6, 'samples': samples, 'warmup_rounds_per_variant': 1,
                       'read_counter_scope': 'Only json.loads called through the tested Original module; other modules are excluded.'}
    # One full untimed pair establishes the same warm state for both variants.
    for label, module in (('baseline_0.73.4', baseline), ('current', original)):
        activate(rig)
        module.enter(bpy.context, rig)
        check_pose(expected_pose)
        module.leave(bpy.context, rig)
        check_pose(expected_pose)
        check_rest(expected_rest)
    for round_index in range(6):
        # Alternate the order to reduce systematic warm-cache/order effects.
        variants = [('baseline_0.73.4', baseline), ('current', original)]
        if round_index % 2:
            variants.reverse()
        for label, module in variants:
            activate(rig)
            for action in ('enter', 'leave'):
                sample = timed(module, action, rig)
                sample['round'] = round_index + 1
                sample['native_pose'] = check_pose(expected_pose)
                samples[label][action].append(sample)
            check_rest(expected_rest)
    check_meshes(expected_meshes, facts['timing'], 'raw_meshes_after_all_pairs')
    facts['timing']['native_pose_after_all_pairs'] = check_pose(expected_pose)
    summary = {}
    for label, directions in samples.items():
        summary[label] = {action: {'median_seconds': statistics.median(row['seconds'] for row in rows),
                                  'minimum_seconds': min(row['seconds'] for row in rows),
                                  'maximum_seconds': max(row['seconds'] for row in rows),
                                  'original_json_reads': [row['module_local_original_json_reads'] for row in rows]}
                          for action, rows in directions.items()}
    facts['timing']['summary'] = summary
    facts['timing']['comparison'] = {action: {'baseline_median_seconds': summary['baseline_0.73.4'][action]['median_seconds'],
        'current_median_seconds': summary['current'][action]['median_seconds'],
        'fractional_change': summary['current'][action]['median_seconds'] / summary['baseline_0.73.4'][action]['median_seconds'] - 1}
        for action in ('enter', 'leave')}
    facts['timing']['status'] = 'passed'


def preview_probe(rig, body, facts):
    preview = facts['forearm_preview'] = {'status': 'starting'}
    activate(rig)
    original.enter(bpy.context, rig)
    activate(body)
    raw_before = all_raw_meshes()
    pose_before, rest_before = all_native_pose(), all_native_rest()
    records_before = body.get(forearm.RECORD_KEY)
    session_before = rig[original.SESSION]
    control_channels_before = {pb.name: {'mode': pb.rotation_mode,
                               'channels': {field: list(getattr(pb, field)) for field in probe.CHANNELS}}
                               for pb in rig.pose.bones if pb.bone.get(limb_ik.OWNER_KEY) in limb_ik.GENERATED_CONTROL_OWNERS}
    side = 'L'
    try:
        arm, route = forearm._resolve_rig(body, side)
        rings = forearm.detect_rings(body, arm, route['chain'][1], route['chain'][2])
        preview['detected_loops'] = len(rings)
        preview['native_hand'] = route['target'].name
        preview['existing_profile'] = forearm._records(body)
        if len(rings) < 3:
            raise ValueError('Current Cosha automatic capture found fewer than three closed forearm loops.')
    except Exception as exc:
        preview.update({'status': 'failed_detection', 'error': str(exc), 'preview_started': False})
        original.leave(bpy.context, rig)
        return False
    started = False
    try:
        # This is the same current-mesh recapture route as Capture & Preview.
        # No old ring override is used to hide a detection failure.
        bpy.context.window_manager.character_designer_forearm_twist.side = side
        forearm.start_paired_test(bpy.context, recapture=True)
        started = True
        preview['target'] = forearm._SESSION['target']
        if preview['target'] != route['chain'][2]:
            raise AssertionError('Original preview selected a generated target instead of the native hand.')
        bpy.context.window_manager.character_designer_forearm_twist.test_angle = math.pi / 2
        actual = forearm.current_twist_angle(bpy.context)
        preview['requested_angle_radians'] = math.pi / 2
        preview['actual_angle_radians'] = actual
        if abs(actual - math.pi / 2) > 5e-4:
            raise AssertionError('The native hand did not reach the 90 degree preview angle.')
        controls = {pb.name: {'mode': pb.rotation_mode,
                    'channels': {field: list(getattr(pb, field)) for field in probe.CHANNELS}}
                    for pb in rig.pose.bones if pb.bone.get(limb_ik.OWNER_KEY) in limb_ik.GENERATED_CONTROL_OWNERS}
        if controls != control_channels_before:
            raise AssertionError('Original forearm preview changed generated control input channels.')
        forearm.finish_test(bpy.context, confirm=False)
        started = False
        preview['cancel_native_pose'] = check_pose(pose_before)
        preview['cancel_native_rest'] = check_rest(rest_before)
        check_meshes(raw_before, preview, 'cancel_raw_meshes')
        preview['cancel_calibration_json_exact'] = body.get(forearm.RECORD_KEY) == records_before
        preview['cancel_original_session_exact'] = rig.get(original.SESSION) == session_before
        preview['preview_marker_removed'] = forearm.PREVIEW_KEY not in body and forearm._SESSION is None
        if not (preview['cancel_calibration_json_exact'] and preview['cancel_original_session_exact']
                and preview['preview_marker_removed']):
            raise AssertionError('Cancel did not restore the exact Original/calibration records.')
        activate(rig)
        original.leave(bpy.context, rig)
        limb_ik._validate_inventory(rig)
        preview['controls_resumed'] = not original.active(rig)
        preview['controls_native_pose'] = check_pose(pose_before)
        preview['status'] = 'passed'
        return True
    except Exception as exc:
        preview.update({'status': 'failed', 'error': str(exc), 'traceback': traceback.format_exc()})
        raise
    finally:
        if started and forearm._SESSION is not None:
            forearm.finish_test(bpy.context, confirm=False)


def main(facts):
    if not bpy.app.background:
        raise RuntimeError('This validation is background-only; never run it in the artist window.')
    if Path(character_designer.__file__).resolve().parent != probe.CANONICAL / 'character_designer':
        raise RuntimeError('Canonical sources were not loaded.')
    if RESULT.resolve() == SOURCE.resolve() or RESULT.parent.resolve() != FOLDER.resolve():
        raise RuntimeError('The result must be a separate isolated file under this evidence folder.')
    facts['input_before'] = probe.fingerprint(SOURCE)
    facts['phase'] = 'load'
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    rig, body = bpy.data.objects['CoshaRig'], bpy.data.objects['Cosha']
    if any(forearm.PREVIEW_KEY in obj for obj in bpy.data.objects if obj.type == 'MESH') or forearm._SESSION is not None:
        raise RuntimeError('A saved or active preview must be resolved before actual-X validation.')
    facts.update({'runtime': bpy.app.version_string, 'addon': list(character_designer.bl_info['version']),
                  'addon_source': character_designer.__file__, 'source_schema': rig.data.get(limb_ik.SCHEMA_KEY),
                  'artist_file_opened': False, 'artist_file_saved': False, 'blend_saved': False})
    # Preserve the initially saved managed-output state through registration
    # and initial observations; the actual leave transaction performs its own
    # deferred final runtime refresh and is tested with runtime enabled.
    forearm._BUSY = True
    try:
        character_designer.register()
        activate(rig)
        raw_before = all_raw_meshes()
        rest_before, pose_before = all_native_rest(), all_native_pose()
        surfaces_before = bound_surfaces(rig)
        original_raw = rig.get(original.SESSION)
        if original_raw is None:
            raise RuntimeError('The validation input must retain its actual Original session.')
        saved = json.loads(original_raw)
        before_provenance = provenance(rig)
        expected_changes = {entry['bone'] for entry in probe.differences(poses.native_rest(rig), saved['rest'])
                            if entry.get('substantial', True)}
        facts['native_rest_original_differences'] = sorted(expected_changes)
        if expected_changes != {'upper_arm.L', 'upper_arm.R'}:
            raise RuntimeError('Unexpected intentional Rest edit scope; do not silently expand resync: ' + str(expected_changes))
        facts['protected_input'] = {'mesh_objects': len(raw_before), 'raw_meshes': raw_before,
                                    'native_rest': rest_before,
                                    'native_pose': {obj: {name: probe.matrix(value) for name, value in state.items()}
                                                    for obj, state in pose_before.items()}}
    finally:
        forearm._BUSY = False
    facts['phase'] = 'actual_rest_resync'
    started = time.perf_counter()
    original.leave(bpy.context, rig)
    facts['actual_resync_seconds'] = time.perf_counter() - started
    if original.active(rig):
        raise AssertionError('Actual Original session did not return to Controls.')
    inventory = limb_ik._validate_inventory(rig)
    facts['strict_inventory_after_resync'] = {'status': 'passed', 'schema': inventory['schema'],
                                            'rigs': [list(key) for key in sorted(inventory['rigs'])]}
    facts['native_rest_after_resync'] = check_rest(rest_before)
    facts['native_pose_after_resync'] = check_pose(pose_before)
    facts['bound_surfaces_after_resync'] = check_surfaces(rig, surfaces_before)
    check_meshes(raw_before, facts, 'raw_meshes_after_resync')
    after_provenance = provenance(rig)
    facts['resync_provenance'] = {'before_events': len(before_provenance['events']),
                                 'after_events': len(after_provenance['events']),
                                 'new_events': after_provenance['events'][len(before_provenance['events']):]}
    events = facts['resync_provenance']['new_events']
    if len(events) != 1 or set(events[0]['changed']) != expected_changes:
        raise AssertionError('Resync did not record exactly one event for the intended upper-arm edits.')
    facts['phase'] = 'actual_cosha_forearm_capture_preview'
    preview_ok = preview_probe(rig, body, facts)
    facts['phase'] = 'paired_background_switch_timing'
    timing_probe(rig, facts)
    facts['final_native_rest'] = check_rest(rest_before)
    facts['final_native_pose'] = check_pose(pose_before)
    facts['final_bound_surfaces'] = check_surfaces(rig, surfaces_before)
    check_meshes(raw_before, facts, 'final_raw_meshes')
    if not preview_ok:
        facts['status'] = 'completed_with_preview_failure'
        facts['save_skipped'] = 'Actual Cosha loop detection failed; full validation did not pass.'
        return
    facts['phase'] = 'save_isolated_result'
    facts['isolated_save'] = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(RESULT), copy=True, check_existing=False))
    if facts['isolated_save'] != ['FINISHED']:
        raise RuntimeError('The isolated validation copy was not saved.')
    facts['blend_saved'] = True
    facts['isolated_result'] = probe.fingerprint(RESULT)
    facts['status'] = 'passed'
    facts['phase'] = 'complete'


if __name__ == '__main__':
    facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'starting'}
    try:
        main(facts)
    except Exception as exc:
        facts.update({'status': 'failed', 'error': str(exc), 'traceback': traceback.format_exc()})
    finally:
        if SOURCE.exists():
            facts['input_after'] = probe.fingerprint(SOURCE)
            facts['input_unchanged'] = facts.get('input_before') == facts['input_after']
            if not facts['input_unchanged']:
                facts['status'] = 'failed'
                facts['input_protection_error'] = 'The saved isolated input changed.'
        facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        REPORT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
        print('CURRENT_X_RESYNC_VALIDATION', facts['status'], facts.get('phase'), str(REPORT), flush=True)
    if facts['status'] != 'passed':
        raise SystemExit(1)
