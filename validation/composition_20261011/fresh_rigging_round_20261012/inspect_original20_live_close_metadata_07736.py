"""Live .36 metadata diagnostic; two owned files, no Close/Save/Gun repetition.

Reproduce the failed runner's public current/capture immediately before its
metadata baseline, then read the already closed saved clone. This is diagnostic
evidence only, not successful artist integration or a repaired preservation gate.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROUND = Path(__file__).resolve().parent
READER = ROUND / 'inspect_original20_close_metadata_07736.py'
READER_SHA = '6bb95122b2105bd329d4b3cc36d699817df2298923f9a522f090b8df53a7f929'
MANIFEST = ROUND / 'package_c1e59f7f/python_projection.json'
MANIFEST_SHA = 'e413d8e6d66bb5a0dd676fc24b0152d1599436464981979fd12d38085daca7e4'
PACKAGE_ROOT = ROUND / 'package_c1e59f7f/source/character_designer'
HARNESS = ROUND / 'validate_original20_latest_saved_controls_r14.py'
HARNESS_SHA = '621f4872cd1a4ee29a1c8182a802e6beec5f7065afaaa21cfe0be624a0da258c'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path, expected):
    path = Path(path).resolve()
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    require(actual == expected.lower(), 'Immutable source changed: ' + str(path))
    return {'path': str(path), 'sha256': actual, 'bytes': len(data)}


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def document(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load(path, expected, name, package=False):
    path = Path(pin(path, expected)['path'])
    spec = importlib.util.spec_from_file_location(name, path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir()),
        'Use a new empty owned diagnostic output directory.')
    inputs = {'source': pin(__file__, args.source_sha256), 'reader': pin(READER, READER_SHA),
        'package_manifest': pin(MANIFEST, MANIFEST_SHA), 'harness': pin(HARNESS, HARNESS_SHA)}
    reader = load(READER, READER_SHA, 'original20_closed_file_metadata_reader')
    for key, path, expected in (
            ('recovery', reader.RECOVERY, reader.RECOVERY_SHA), ('closed_clone', reader.CLOSED, reader.CLOSED_SHA),
            ('runner', reader.RUNNER, reader.RUNNER_SHA), ('helper', reader.HELPER, reader.HELPER_SHA),
            ('failed_report', reader.FAILED_REPORT, reader.FAILED_REPORT_SHA),
            ('failed_release', reader.FAILED_RELEASE, reader.FAILED_RELEASE_SHA)):
        inputs[key] = pin(path, expected)
    failed = document(inputs['failed_report']['path'])
    require(failed['completed'] is False and failed['stage'] == 'reopened_readback'
        and failed['error'] == 'RuntimeError: Close/reopen changed existing IDs/colors/modifiers.'
        and failed['saved_clone']['sha256'] == inputs['closed_clone']['sha256']
        and failed['public_Close_success'] is True, 'Keep the real failed reopen evidence failed.')
    manifest = document(MANIFEST)
    root = Path(manifest['source_root']).resolve()
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
        and manifest['version'] == '0.77.36' and len(manifest['files']) == 190 and root == PACKAGE_ROOT,
        'Use the exact frozen .36 projection.')
    files = {}
    for relative, expected in manifest['files'].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and '__pycache__' not in path.parts, 'Invalid runtime leaf.')
        files[relative] = pin(path, expected)
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(files),
        'The frozen runtime has extra/missing files.')
    import bpy
    require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
        and len(bpy.context.window_manager.windows) == 1 and not bpy.context.preferences.filepaths.use_scripts_auto_execute,
        'Use one isolated factory-startup headful Blender 5.2 with autoexecution disabled.')
    require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules),
        'Another Character Designer runtime is loaded.')
    report = {'schema': 'x.validation.original20-live-close-metadata-diagnostic/1', 'completed': False,
        'pid': os.getpid(), 'source_inputs': inputs, 'native_execution_performed': True, 'diagnostic_only': True,
        'candidate_registered': False, 'scene_saved': False, 'scene_edit_operators_performed': False,
        'frame_seek_operators_performed': False, 'original_X_opened': False,
        'Close_Save_Gun_Undo_operators_performed': False, 'public_current_calls': 0, 'public_capture_calls': 0,
        'second_file_pair_validation_performed': False, 'live_baseline_retained': False,
        'reopen_failure_resolved': False, 'natural_exit_verified': False,
        'scope': 'Exact frozen .36 load lifecycle, then one public current/capture and full live metadata; reopen existing closed clone for metadata only.',
        'limitation': 'A new observed baseline is retained. An empty diff still does not explain the original unretained live mismatch.'}
    report_path = output / 'live_close_metadata_diagnostic_report.json'
    state = {'phase': 'register', 'metadata': {}}
    write(report_path, report)

    @contextmanager
    def timed(label):
        row = {'operation': label, 'started_utc': datetime.now(timezone.utc).isoformat(), 'completed': False}
        report.setdefault('operations', []).append(row)
        write(report_path, report)
        print('LIVE_CLOSE_METADATA_BEGIN ' + label, flush=True)
        started = time.perf_counter()
        try:
            yield
            row['completed'] = True
        finally:
            row.update(ended_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter() - started)
            write(report_path, report)
            print('LIVE_CLOSE_METADATA_END ' + json.dumps(row), flush=True)

    package = load(root / '__init__.py', files['__init__.py']['sha256'], 'character_designer', package=True)
    harness = load(HARNESS, HARNESS_SHA, 'original20_live_metadata_context')
    metadata, probe = reader.exact_metadata_reader(bpy)

    def register_runtime():
        with timed('register exact frozen .36 runtime'):
            require(tuple(package.bl_info['version']) == (0, 77, 36), 'Runtime version changed.')
            package.register()
            for name in ('unity_animation_rigging', 'unity_animation_original_inputs'):
                module = __import__('character_designer.' + name, fromlist=[name])
                require(Path(module.__file__).resolve() == root / (name + '.py'), 'Mixed runtime: ' + name)
                state[name] = module
        report['candidate_registered'] = True
        return 'open_recovery'

    def open_owned(key, next_phase):
        row = inputs[key]
        with timed('open ' + key):
            result = bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=row['path'], use_scripts=False, load_ui=False)
        require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == Path(row['path']), 'Owned file did not open.')
        return next_phase

    def settled_lifecycle():
        native = state['unity_animation_rigging']
        rig = bpy.data.objects.get('CoshaRig')
        require(rig is not None, 'Recovery lost CoshaRig.')
        pending = rig.as_pointer() in native._REACQUIRE_PENDING
        timer = native._REACQUIRE_TIMER
        if pending and timer is not None and bpy.app.timers.is_registered(timer):
            first = state.setdefault('pending_started', time.monotonic())
            require(time.monotonic() - first <= 120., 'The original one-shot lifecycle admission remained pending over 120 seconds.')
            return False
        with harness.owning_context(bpy) as (ctx, fresh):
            require(native._REACQUIRE_TIMER is None and not native._REACQUIRE_PENDING, 'Lifecycle did not settle.')
            cached = native.display_state(fresh)
            require(cached is not None and cached['rig'] == fresh and cached['scene'] == ctx.scene
                and cached['enabled'] and cached['original_controls_only'] and not native._HANDLER_ERRORS,
                'The real load handler did not reacquire before public current.')
            callbacks = {name: sum(value is callback for value in getattr(bpy.app.handlers, name)) for name, callback in (
                ('load_post', native._reacquire), ('undo_post', native._reacquire), ('redo_post', native._reacquire),
                ('frame_change_post', native._frame), ('depsgraph_update_post', native._depsgraph))}
            require(all(value == 1 for value in callbacks.values()), 'Lifecycle handlers are missing or duplicated.')
            report['load_lifecycle_before_current'] = {'callbacks': callbacks, 'pending_empty': True, 'handler_errors_empty': True}
        return True

    def live_baseline():
        backend = state['unity_animation_original_inputs']
        with harness.owning_context(bpy) as (ctx, rig):
            with timed('same-runner public current and complete capture'):
                report['public_current_calls'] += 1
                session = backend.current(rig)
                require(session is not None and 'original_inputs' in session, 'No authenticated Original20 session.')
                report['public_capture_calls'] += 1
                dto = backend.capture_inputs(ctx, session)
            report['baseline_Return'] = reader.saved(output / 'live_baseline_Return.json', dto)
            record = rig.get(reader.RECORD)
            require(record is not None and record.get('scene') == ctx.scene, 'Recovery lacks its owning weapon record.')
            owned = tuple(record['objects'].values())
            require(owned and all(isinstance(obj, bpy.types.Object) and obj.get(reader.OWNER) == record['owner'] for obj in owned)
                and set(record['collection'].objects) == set(owned), 'Weapon exclusion must follow its exact record-owned Objects.')
            state['names'] = sorted(obj.name for obj in bpy.data.objects if obj not in set(owned))
            report['excluded_record_owned_weapon_objects'] = [probe.id(obj) for obj in owned]
            report['protected_object_names'] = state['names']
            with timed('full live metadata immediately after current/capture'):
                state['metadata']['live_D4CB_after_capture'] = metadata(rig, state['names'])
            report['live_D4CB_after_capture_metadata'] = reader.saved(output / 'live_D4CB_after_capture_metadata.json',
                state['metadata']['live_D4CB_after_capture'])
            report['live_baseline_retained'] = True
            report['baseline_context'] = {'frame': [ctx.scene.frame_current, ctx.scene.frame_subframe],
                'rig_mode': rig.mode, 'tweak': rig.animation_data.use_tweak_mode, 'session_owner': session['owner']}
        return 'open_closed'

    def closed_readback():
        native = state['unity_animation_rigging']
        with harness.owning_context(bpy) as (ctx, rig):
            require(reader.RECORD not in rig and native.SESSION_KEY not in rig, 'The saved closed clone is not closed.')
            report['reopened_lifecycle_raw'] = {'handler_errors': dict(native._HANDLER_ERRORS),
                'pending': sorted(native._REACQUIRE_PENDING), 'cache_count': len(native._CACHE)}
            # No backend.current, pair validation or capture is performed on this file.
            with timed('full already-closed reopened metadata'):
                state['metadata']['closed_saved_clone'] = metadata(rig, state['names'])
            report['closed_saved_clone_metadata'] = reader.saved(output / 'closed_saved_clone_metadata.json',
                state['metadata']['closed_saved_clone'])
            with timed('complete live-baseline versus reopen leaf diff'):
                diff = reader.differences(state['metadata']['live_D4CB_after_capture'], state['metadata']['closed_saved_clone'])
                for row in diff:
                    row['rna_property'] = reader.locate_rna_property(bpy, rig, row['path'])
                report['differences'] = reader.saved(output / 'live_metadata_diff.json', diff)
                report['difference_count'] = len(diff)
                report['metadata_exact'] = not diff
                report['observation'] = ('New live baseline and reopened metadata match; the original unretained mismatch was not reproduced.'
                    if not diff else 'Actual live-baseline/reopened differences are retained without field exclusions or qualification.')
        return 'finish'

    def finish(error=None):
        if error is not None:
            report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        try:
            with timed('immutable input and runtime pins after read'):
                for row in list(inputs.values()) + list(files.values()): pin(row['path'], row['sha256'])
            report['input_files_unchanged'] = True
        except Exception as exc:
            report['input_integrity_error'] = type(exc).__name__ + ': ' + str(exc)
            error = exc
        report['completed'] = error is None and report['live_baseline_retained'] and 'differences' in report
        write(report_path, report)
        print('LIVE_CLOSE_METADATA_DIAGNOSTIC ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)
        def quit_owned():
            observation = {'pid': os.getpid(), 'requested_from_timer': True, 'completed_report': report['completed'],
                'natural_exit_still_external': True}
            try:
                observation['operator_result'] = sorted(bpy.ops.wm.quit_blender('EXEC_DEFAULT', False))
            except Exception as exc:
                observation['error'] = type(exc).__name__ + ': ' + str(exc)
            write(output / 'owned_quit_observation.json', observation)
            return None
        bpy.app.timers.register(quit_owned, first_interval=3., persistent=False)
        return None

    def tick():
        phase = state['phase']
        report['stage'] = phase
        write(report_path, report)
        print('LIVE_CLOSE_METADATA_STAGE ' + phase, flush=True)
        try:
            if phase == 'register': next_phase = register_runtime()
            elif phase == 'open_recovery': next_phase = open_owned('recovery', 'live_baseline')
            elif phase == 'live_baseline':
                if not settled_lifecycle(): return .1
                next_phase = live_baseline()
            elif phase == 'open_closed': next_phase = open_owned('closed_clone', 'closed_readback')
            elif phase == 'closed_readback': next_phase = closed_readback()
            elif phase == 'finish': return finish()
            else: raise RuntimeError('Unknown owned diagnostic phase.')
            state['phase'] = next_phase
            write(report_path, report)
            return .1
        except Exception as exc:
            return finish(exc)

    bpy.app.timers.register(tick, first_interval=.1, persistent=True)


if __name__ == '__main__':
    main()
