"""Isolate saved Rest constants in a disposable same-process ABBA comparison.

Only the two Rest selectors change. Current runtime/math/UA and the current
record compiler remain identical. Never save or refresh the artist.
"""
import argparse
from collections import Counter
import datetime
import json
import os
from pathlib import Path
import statistics
import sys
import time
import traceback
import bpy

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER.parent))
from profile_saved_forearm_display import functions, pin, witness


def main(args, report):
    addons = Path(args.addons).resolve()
    sys.path.insert(0, str(addons))
    import character_designer as addon
    from character_designer import forearm_twist as runtime, forearm_twist_math as geometry
    from character_designer import animation_worklist_target as target, unity_animation as ua
    modules = (runtime, geometry, target, ua)
    assert all(Path(module.__file__).resolve().is_relative_to(addons) for module in modules)
    report['blender'], report['metadata_version'] = bpy.app.version_string, list(addon.bl_info['version'])
    report['input'], report['artist_before'] = pin(args.input), pin(args.artist)
    assert Path(args.input).resolve() != Path(args.artist).resolve(), 'Use a disposable saved copy'
    assert report['input']['sha256'] == report['artist_before']['sha256']
    report['sources'] = [pin(module.__file__) for module in modules]
    report['metadata_source'], report['script'] = pin(addon.__file__), pin(__file__)
    report['witness_helper'] = pin(FOLDER.parent / 'profile_saved_forearm_display.py')
    baseline = Path(args.baseline).resolve()
    report['materialized_selector_source'] = pin(baseline)
    names = {'control_rest_view', 'validation_rest_view'}
    selected_constants = {name: getattr(target, name) for name in names}
    selected_materialized = functions(baseline, target.__dict__, names)
    fixed = [(module, name, value) for module in modules for name, value in vars(module).items()
             if callable(value) and getattr(value, '__module__', None) == module.__name__
             and not (module is target and name in names)]
    report['fixed_callable_names'] = {
        module.__name__: sorted(name for owner, name, _value in fixed if owner is module)
        for module in modules}
    addon.register()
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.input).resolve()))
    scene = bpy.context.scene
    report['scene'] = scene.name
    report['actions'] = {obj.name: obj.animation_data.action.name for obj in scene.objects
                         if obj.animation_data and obj.animation_data.action}
    report['calibrated_meshes'] = calibrated = {obj.name: {
        side: {'enabled': value.get('enabled', True), 'support_vertices': len(value['vertices'])}
        for side, value in runtime._records(obj).items()}
        for obj in scene.objects if obj.type == 'MESH' and runtime.RECORD_KEY in obj}
    assert any(value['enabled'] and value['support_vertices'] for records in calibrated.values()
               for value in records.values()), 'No enabled Forearm support exercises the Rest path'
    report['warmup_frames'], report['frames'] = [1, 3], [2, 6, 10, 14, 18, 22, 26, 30] * 2
    report['cases'] = cases = []
    reference = None
    loader, proof = target._load_rest_record, target._prove_motion_data
    try:
        for block, label in enumerate(('materialized', 'saved_constants', 'saved_constants', 'materialized'), 1):
            chosen = selected_materialized if label == 'materialized' else selected_constants
            for name, function in chosen.items():
                setattr(target, name, function)
            assert all(getattr(module, name) is value for module, name, value in fixed)
            runtime._CACHE.clear()
            runtime._OUTPUT_CACHE.clear()
            runtime.validation_cache.clear()
            target._compile_rest_record.cache_clear()
            counts = Counter()

            def observed_loader(*values, **kwargs):
                result = loader(*values, **kwargs)
                flagged = bool(kwargs.get('_for_rest_proof', False))
                counts['proof_flag_true' if flagged else 'proof_flag_false'] += 1
                original = result['capture']['targets'][0]['rest']
                motion = result['motion_rest']
                compiled = isinstance(original, ua._SavedRestState) and isinstance(motion, ua._SavedRestState)
                materialized = type(original) is dict and type(motion) is dict
                counts['compiled_pair' if compiled else 'materialized_pair' if materialized else 'other_pair'] += 1
                return result

            def observed_proof(*values, **kwargs):
                counts['native_proof_calls'] += 1
                return proof(*values, **kwargs)

            target._load_rest_record, target._prove_motion_data = observed_loader, observed_proof
            try:
                for frame in report['warmup_frames']:
                    scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    assert not runtime._ERRORS, dict(runtime._ERRORS)
            finally:
                target._load_rest_record, target._prove_motion_data = loader, proof
            constants = label == 'saved_constants'
            expected_flag = 'proof_flag_true' if constants else 'proof_flag_false'
            expected_pair = 'compiled_pair' if constants else 'materialized_pair'
            assert counts[expected_flag] > 0 and counts[expected_pair] == counts[expected_flag], dict(counts)
            assert counts['proof_flag_false' if constants else 'proof_flag_true'] == 0, dict(counts)
            assert counts['native_proof_calls'] > 0, 'Fresh native Rest proof did not run'
            warm_cache = target._compile_rest_record.cache_info()._asdict()
            assert warm_cache['hits'] > 0 and warm_cache['misses'] > 0, 'Compiled record was not warmed'
            assert all(getattr(module, name) is value for module, name, value in fixed)
            elapsed, outputs = [], []
            for frame in report['frames']:
                start = time.perf_counter()
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                elapsed.append((time.perf_counter() - start) * 1000)
                assert not runtime._ERRORS, dict(runtime._ERRORS)
                outputs.append(witness(runtime, scene))
            if reference is None:
                reference = outputs
            assert outputs == reference, 'Pose/managed output/records/collection/display changed'
            assert all(getattr(module, name) is value for module, name, value in fixed)
            hot_cache = target._compile_rest_record.cache_info()._asdict()
            assert hot_cache['hits'] > warm_cache['hits'], 'Hot frames did not read the compiled Rest plan'
            row = {'block': block, 'label': label, 'milliseconds': elapsed,
                   'median_ms': statistics.median(elapsed), 'warm_rest_path_counts': dict(counts),
                   'warm_compile_cache': warm_cache,
                   'hot_compile_cache': hot_cache,
                   'outputs_equal_to_baseline': True, 'errors': dict(runtime._ERRORS)}
            cases.append(row)
            print('SAVED_CONSTANTS_CASE', block, label, round(row['median_ms'], 3), flush=True)
    finally:
        target._load_rest_record, target._prove_motion_data = loader, proof
        for name, function in selected_constants.items():
            setattr(target, name, function)
    report['sources_after'] = [pin(module.__file__) for module in modules]
    assert report['sources_after'] == report['sources'], 'Source files changed during evaluation'
    report['input_after'], report['artist_after'] = pin(args.input), pin(args.artist)
    assert report['input_after'] == report['input'] and report['artist_after'] == report['artist_before']
    report['artist_disk_unchanged'] = report['all_frame_witnesses_equal'] = report['no_scene_save'] = True
    report['paired_delta_ms'] = [[left - right for left, right in zip(cases[a]['milliseconds'], cases[b]['milliseconds'])]
                                 for a, b in ((0, 1), (3, 2))]
    report['limits'] = ['One disposable saved snapshot, one thread, shared load; background time is not GUI FPS.',
        'Only two Rest selectors switch; current runtime/math/UA/compiler and native proof are held identical.',
        'Two warmup and sixteen hot frames per ABBA block; compilation and path counters are outside hot timings.',
        'Saved constants are immutable saved inputs, not cached native validation results.',
        'Exact observed witnesses, not all-world equality; unsaved live changes and external GUI callbacks excluded.',
        'No artist refresh or scene save; output witnesses contain hashes, not full vertex arrays.']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'artist', 'addons', 'report'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--baseline', default=str(FOLDER / 'accepted_r2_sources/animation_worklist_target.py'))
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    destination = Path(args.report).resolve()
    if destination.exists():
        raise SystemExit('Use a new report path; prior evidence must remain intact')
    report = {'schema': 'x.saved-rest-constants-focus/1', 'completed': False, 'pid': os.getpid(),
              'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'model_and_reasoning_effort': 'unrecorded'}
    try:
        main(args, report)
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        with destination.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
