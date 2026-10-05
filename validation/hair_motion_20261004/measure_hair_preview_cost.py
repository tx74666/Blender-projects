"""Serial saved-X cost decomposition; never execute in the artist GUI.

Run with the same saved X and official CD_WIGGLE_TEST_ROOT as the real Hair
validator. CD_HAIR_COST_OUTPUT may choose a NEW JSON in this evidence folder.
Only adapter._changed is temporarily timed. Official handlers/solver code and
their callback identities remain unchanged; no scene or animation is saved.
"""
import collections
import ctypes
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

import bpy

DIRECTORY = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'cd_hair_cost_validation_helpers', DIRECTORY / 'validate_real_hair_preview.py')
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)  # The validator's guarded main is not called.

adapter, registry, profiles, hair = helpers.adapter, helpers.registry, helpers.profiles, helpers.hair
FRAMES = 60


def memory_status():
    """Stage-boundary observations, not peak-memory measurements."""
    if os.name != 'nt':
        return {'available': False, 'reason': 'Windows GlobalMemoryStatusEx unavailable.'}
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load_percent', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ('total_bytes', 'available_bytes',
                'total_pagefile_bytes', 'available_pagefile_bytes', 'total_virtual_bytes',
                'available_virtual_bytes', 'available_extended_virtual_bytes')]
    state = Memory()
    state.length = ctypes.sizeof(state)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
        return {'available': False, 'reason': 'GlobalMemoryStatusEx failed.'}
    return {'available': True, 'total_bytes': state.total_bytes,
            'available_bytes': state.available_bytes, 'load_percent': state.load_percent}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def timing(values):
    return {'samples': len(values), 'seconds_median': statistics.median(values),
            'seconds_mean': statistics.mean(values), 'seconds_max': max(values),
            'seconds_total': sum(values)}


def restore_author(saved):
    """Restore a baseline stage with the same rollback primitives as preview."""
    scene = bpy.context.scene
    # Freeze solver callbacks before resetting the author frame. Raw backing
    # restoration below also restores whether each native PG originally existed.
    scene.wiggle['enable'] = False
    scene.frame_set(saved['frame'], subframe=saved['subframe'])
    for snapshot in saved['custom']:
        adapter._restore_pose_custom(snapshot)
    for keys, evaluation, values in saved['shapes']:
        keys.eval_time = evaluation
        for block, value in values:
            block.value = value
    for snapshot in saved['channels']:
        adapter._restore_channels(snapshot)
    scene.tool_settings.use_keyframe_insert_auto = saved['autokey']
    for snapshot in reversed(saved['raw']):
        adapter._restore_raw(snapshot)
    bpy.context.view_layer.update()


def measure_stage(label, source, armature, data, effective, ids, strategy, guard_bucket):
    helpers.require(not adapter.status()['active'], 'A preceding preview was not stopped.')
    memory_before = memory_status()
    helpers.require(not memory_before['available'] or memory_before['available_bytes'] >= 200 * 1024 * 1024,
                    'Less than 200 MiB available; no new measurement stage was started.')
    raw_before = helpers.asset_fingerprint(source)
    saved = helpers.pose_snapshot()
    initial_anchor = (armature.matrix_world @ strategy['anchor'].matrix).to_quaternion()
    observed_ids = ids or [item['strand_id'] for item in data['strands']]
    by_id = {item['strand_id']: item for item in data['strands']}
    observed = [by_id[strand_id] for strand_id in observed_ids]
    input_times, native_times, observation_times, guard_times, guard_counts = [], [], [], [], []
    anchor_rotation = 0.0
    start_seconds = 0.0
    stop_seconds = 0.0
    began = time.perf_counter()
    try:
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        if ids:
            start = time.perf_counter()
            adapter.start_preview(bpy.context, source, data, effective, ids)
            start_seconds = time.perf_counter() - start
        else:
            bpy.context.scene.wiggle['enable'] = False
        for index in range(1, FRAMES + 1):
            # Both input and endpoint observation are outside native frame_set.
            # The guard is a subset of frame_set, not an additive extra cost.
            guard_bucket['current'] = None
            start = time.perf_counter()
            helpers.apply_input(strategy, helpers.pulse(index))
            input_times.append(time.perf_counter() - start)
            guard_bucket['current'] = []
            start = time.perf_counter()
            bpy.context.scene.frame_set(saved['frame'] + index)
            native_times.append(time.perf_counter() - start)
            guard_times.append(sum(guard_bucket['current']))
            guard_counts.append(len(guard_bucket['current']))
            guard_bucket['current'] = None
            helpers.require(not ids or adapter.status()['active'],
                            'Preview stopped during measurement: ' + adapter.status()['reason'])
            start = time.perf_counter()
            world = armature.matrix_world
            anchor = (world @ strategy['anchor'].matrix).to_quaternion()
            anchor_rotation = max(anchor_rotation, initial_anchor.rotation_difference(anchor).angle)
            for item in observed:
                tip = world @ armature.pose.bones[item['bones'][-1]].tail
                root = world @ armature.pose.bones[item['bones'][0]].head
                helpers.require(all(math.isfinite(value) for value in (*tip, *root)),
                                'An observed Hair endpoint is nonfinite.')
            observation_times.append(time.perf_counter() - start)
    finally:
        guard_bucket['current'] = None
        if adapter.status()['active']:
            start = time.perf_counter()
            adapter.stop_preview(reason='Isolated cost stage ended.')
            stop_seconds = time.perf_counter() - start
        # Baseline has no adapter session. The explicit restore also proves
        # all stages begin from identical author input channels and frame.
        restore_author(saved)
    strict_pose = helpers.check_pose(saved)
    raw_after = helpers.asset_fingerprint(source)
    helpers.require(raw_after['sha256'] == raw_before['sha256'], 'Stage changed the strict raw asset baseline.')
    helpers.require(anchor_rotation > 1e-4, 'The proven Head-local input did not move its actual anchor.')
    return {'name': label, 'frames': FRAMES, 'simulated_strands': len(ids),
        'simulated_bones': sum(len(by_id[strand_id]['bones']) for strand_id in ids),
        'observed_strands': len(observed), 'strand_ids': list(ids),
        'input': timing(input_times), 'native_frame_set': timing(native_times),
        'endpoint_observation': timing(observation_times), 'adapter_changed_guard': timing(guard_times),
        'guard_calls_total': sum(guard_counts), 'guard_calls_per_frame': guard_counts,
        'native_minus_changed_guard': timing([native - guard for native, guard in zip(native_times, guard_times)]),
        'start_preview_seconds': start_seconds, 'stop_preview_seconds': stop_seconds,
        'stage_seconds_including_protection': time.perf_counter() - began,
        'maximum_observed_anchor_rotation_degrees': math.degrees(anchor_rotation),
        'strict_pose_restored': strict_pose, 'strict_raw_baseline': True,
        'raw_before': raw_before, 'raw_after': raw_after,
        'memory_before': memory_before, 'memory_after': memory_status()}


def main():
    helpers.require(bpy.app.background, 'Run only in an isolated background Blender, never the artist GUI.')
    helpers.require(bpy.data.filepath, 'Open the explicit saved X input first.')
    output = Path(os.environ.get('CD_HAIR_COST_OUTPUT', str(DIRECTORY / (
        'hair_preview_cost_' + bpy.app.version_string.replace('.', '_').replace(' ', '_')
        + '_' + str(time.time_ns()) + '.json')))).resolve()
    helpers.require(output.parent == DIRECTORY.resolve() and output.suffix.lower() == '.json',
                    'Cost evidence must be a JSON in this validation directory.')
    helpers.require(not output.exists(), 'Refusing to overwrite previous cost evidence.')
    artist = Path(bpy.data.filepath).resolve()
    disk_before = file_hash(artist)
    module = None
    original_changed = adapter._changed
    bucket = {'current': None, 'outside_calls': 0, 'outside_seconds': 0.0}
    result = {'ok': False, 'blender': bpy.app.version_string, 'artist_path': str(artist),
        'artist_saved': False, 'simulation_baked': False, 'stages': [],
        'adapter_source': str(Path(adapter.__file__).resolve()),
        'adapter_source_sha256': file_hash(Path(adapter.__file__)),
        'input_helper_sha256': file_hash(DIRECTORY / 'validate_real_hair_preview.py'),
        'limitations': ['Serial fixed order: baseline, four strands, all 32; no paired or reversed-order comparison.',
            'Background frame_set includes native depsgraph and unmodified upstream callbacks; no GUI or FPS claim.',
            'Guard timing is inside frame_set; subtracting it does not isolate the official solver from depsgraph.',
            'Windows available-memory observations are stage boundaries, not peak RAM or process private bytes.',
            'No timer event-loop performance measurement; background manual frame stepping differs from GUI playback.',
            'One saved input, 60 samples per stage; variable system load can affect these descriptive medians.']}
    def timed_changed(session):
        started = time.perf_counter()
        try:
            return original_changed(session)
        finally:
            duration = time.perf_counter() - started
            if bucket['current'] is None:
                bucket['outside_calls'] += 1
                bucket['outside_seconds'] += duration
            else:
                bucket['current'].append(duration)
    try:
        source = bpy.data.objects['Hair']
        helpers.require(hair._read_records(source)['source_id'].replace('-', '').lower() == helpers.EXPECTED_UID,
                        'Unexpected Hair source UUID; no metadata was initialized.')
        initial = helpers.asset_fingerprint(source)
        data = registry.initialize(source)
        helpers.require(len(data['strands']) == 32 and sum(len(item['bones']) for item in data['strands']) == 128,
                        'Expected existing 32 strands / 128 segments; no rebind is authorized.')
        profiles.initialize(source, registry=data)
        record = profiles.assign_suggested_groups(source, registry=data)
        effective = profiles.effective_all(source, registry=data)
        first, long = helpers.pair(data, 14, 16), helpers.pair(data, 2, 5)
        for pair in (first, long):
            helpers.require(effective[pair[0]['strand_id']] == effective[pair[1]['strand_id']]
                            and effective[pair[0]['strand_id']]['sync_mirror'], 'Expected synchronized pair settings.')
        armature = source.get(hair.RIG_KEY)
        strategy = helpers.input_strategy(armature, data)
        helpers.require(strategy['kind'] != 'root_armature_world_rotation'
                        and isinstance(strategy['owner'], bpy.types.PoseBone)
                        and strategy['proof_diagnostics']['dependency_closure']['proved'],
                        'Head-local dependency input is unproven; no Object fallback is measured.')
        result.update(source=source.name, source_uid=data['source_uid'], topology=data['topology'],
            groups=dict(collections.Counter(item['group'] for item in effective.values())),
            input_proof={'kind': strategy['kind'], 'anchor': strategy['anchor'].name,
                'owner': strategy['owner'].name, 'axis': strategy['axis'], 'constraint_trace': strategy['trace'],
                'proof_diagnostics': strategy['proof_diagnostics']},
            registry_counts=dict(collections.Counter(item['side'] for item in data['strands'])))
        module = helpers.load_backend()
        ids = [item['strand_id'] for item in (*first, *long)]
        # Run the same strict preview gate before baseline without starting any
        # simulation, so a pre-existing author's Wiggle session is never stepped.
        adapter._preflight(bpy.context, source, data, effective, ids, adapter._backend())
        adapter._changed = timed_changed
        stages = [('baseline_no_simulation', []), ('preview_four_strands', ids),
                  ('preview_all_32', [item['strand_id'] for item in data['strands']])]
        for label, chosen in stages:
            result['stages'].append(measure_stage(label, source, armature, data, effective, chosen, strategy, bucket))
        helpers.require(profiles.read(source, registry=data) == record, 'Measurement changed saved motion profiles.')
        helpers.require(registry.read(source, validate=True) == data, 'Measurement changed the strict strand registry.')
        final = helpers.asset_fingerprint(source)
        helpers.require(final['sha256'] == initial['sha256'], 'Final raw model baseline differs.')
        helpers.require(Path(bpy.data.filepath).resolve() == artist and file_hash(artist) == disk_before,
                        'Saved input changed while measuring; preserve this report as a failed comparison.')
        result.update(ok=True, strict_baseline=True, initial_fingerprint=initial, final_fingerprint=final,
                      artist_disk_sha256_unchanged=disk_before, guard_outside_frame_calls=bucket['outside_calls'],
                      guard_outside_frame_seconds=bucket['outside_seconds'])
    except Exception as exc:
        result['error'] = str(exc)
        raise
    finally:
        adapter._changed = original_changed
        try:
            adapter.stop_preview(reason='Isolated preview cost teardown.')
            adapter.unregister_guards()
            if module is not None:
                module.unregister()
        except Exception as exc:
            result['ok'] = False
            result['teardown_error'] = str(exc)
            raise
        finally:
            output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf8')
            print('HAIR_PREVIEW_COST', json.dumps({'ok': result['ok'], 'output': str(output), 'artist_saved': False}))


if __name__ == '__main__':
    main()
