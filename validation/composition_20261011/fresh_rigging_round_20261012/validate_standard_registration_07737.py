"""Owned blank headful standard-enable lifecycle probe; never opens an artist file."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROUND = Path(__file__).resolve().parent
EXPECTED = {'__init__.py': '12c4aee9037741b649d0de258e0ed4a3c77d27fd77448e82438bcb5f910dcd7c',
    'unity_animation_rigging.py': '0ca35e2e44bea9ed1007bf9024cfadb50b0e6a8ada2a702a84de43f30c484cd9',
    'skirt_wiggle.py': '81b0f0c42cfb8c4d3854c81e7da4a351d47e42b18929467d3e4864982bb13c25'}
INJECTED = 'Owned .37 probe: fail after restricted Rigging timer registration.'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path, expected=None):
    path = Path(path).resolve()
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(expected is None or digest == expected.lower(), 'File pin changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': len(data)}


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--package-manifest', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir()),
        'Use a new empty owned output directory.')
    import bpy
    import addon_utils
    report = {'schema': 'x.validation.standard-registration-lifecycle/1', 'completed': False, 'passed': False,
        'pid': os.getpid(), 'native_execution_performed': True, 'scene_opened_or_saved': False,
        'artist_opened': False, 'Body_Gun_or_animation_protocol_retested': False,
        'runtime_source_mutated': False, 'in_memory_failure_injection_performed': False,
        'scope': 'Factory blank standard addon_utils.enable: deferred admission, ordinary disable, immediate cancellation and controlled initialization cleanup only.',
        'natural_exit_verified': False, 'natural_exit_external_retained_handle_required': True}
    report_path = output / 'report.json'
    state = {'phase': 'enable', 'timers': [], 'modules': {}}

    def write():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    def handle_error(error):
        report.setdefault('handled_errors', []).append({'phase': state['phase'], 'type': type(error).__name__,
            'message': str(error), 'traceback': ''.join(traceback.format_exception(error))})
        write()

    @contextmanager
    def timed(name):
        row = {'operation': name, 'started_utc': datetime.now(timezone.utc).isoformat(), 'completed': False}
        report.setdefault('operations', []).append(row)
        write()
        start = time.perf_counter()
        try:
            yield
            row['completed'] = True
        finally:
            row.update(ended_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter() - start)
            write()

    def keep_modules():
        for name, module in tuple(sys.modules.items()):
            if name == 'character_designer' or name.startswith('character_designer.'):
                path = Path(module.__file__).resolve()
                require(path.is_relative_to(state['root']), 'Mixed source module: ' + name)
                state['modules'][name] = module

    def blank_state():
        return {'filepath': bpy.data.filepath, 'scene': bpy.context.scene.name,
            'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
            'objects': {obj.name: {'pointer': obj.as_pointer(), 'type': obj.type,
                'matrix': [list(row) for row in obj.matrix_world]} for obj in bpy.data.objects}}

    def properties():
        return {cls.__name__: sorted(prop.identifier for prop in cls.bl_rna.properties
            if prop.identifier.startswith('character_designer')) for cls in
            (bpy.types.Scene, bpy.types.Object, bpy.types.WindowManager)}

    def cleanup_witness(label):
        keep_modules()
        module = state['module']
        classes = tuple(module.CLASSES) + tuple(module.skirt_wiggle_ui.SKIRT_WIGGLE_UI_CLASSES)
        residual_classes = sorted({cls.__name__ for cls in classes if bool(cls.is_registered)})
        callbacks = []
        for name in dir(bpy.app.handlers):
            values = getattr(bpy.app.handlers, name)
            if isinstance(values, list):
                callbacks.extend(name + ':' + callback.__name__ for callback in values
                    if getattr(callback, '__module__', '').startswith('character_designer'))
        candidates = list(state['timers'])
        for module in state['modules'].values():
            candidates.extend(value for value in vars(module).values() if inspect.isfunction(value)
                and getattr(value, '__module__', '').startswith('character_designer'))
        residual_timers = sorted({callback.__module__ + ':' + callback.__name__ for callback in candidates
            if bpy.app.timers.is_registered(callback)})
        row = {'boundary': label, 'registered_owned_classes': residual_classes, 'owned_handlers': callbacks,
            'owned_timers': residual_timers, 'properties': properties(),
            'pending_registration_timer': state['native']._REACQUIRE_TIMER is not None,
            'pending_reacquisition': bool(state['native']._REACQUIRE_PENDING)}
        report.setdefault('cleanup_witnesses', []).append(row)
        write()
        require(not residual_classes and not callbacks and not residual_timers
            and row['properties'] == state['initial_properties']
            and not row['pending_registration_timer'] and not row['pending_reacquisition'],
            'Owned standard-disable/failed-initialization state did not fully clean up.')
        require(blank_state() == state['blank'], 'Registration changed the blank scene or its existing object transforms.')

    def enable():
        with timed('standard restricted addon_utils.enable'):
            module = addon_utils.enable('character_designer', default_set=False, persistent=False, handle_error=handle_error)
        require(module is not None and module.__addon_enabled__ and not report.get('handled_errors'), 'Standard enable failed.')
        state['module'] = module
        keep_modules()
        native = sys.modules['character_designer.unity_animation_rigging']
        state['native'] = native
        require(tuple(module.bl_info['version']) == (0, 77, 37), 'Wrong runtime version.')
        module._validate_registration_integrity()
        timer = native._REACQUIRE_TIMER
        require(timer is not None and bpy.app.timers.is_registered(timer) and not native._CACHE
            and not native._HANDLER_ERRORS and not native._REACQUIRE_PENDING,
            'Restricted enable did not return with exactly its fresh pending admission.')
        state.update(first_timer=timer, first_generation=native._REACQUIRE_GENERATION)
        state['timers'].append(timer)
        report['standard_enable_returned_module_before_deferred_admission'] = True
        return 'observe_admission'

    def observe_admission():
        native = state['native']
        require(native._REACQUIRE_TIMER is None and not bpy.app.timers.is_registered(state['first_timer'])
            and native._REACQUIRE_GENERATION == state['first_generation'] + 1
            and not native._REACQUIRE_PENDING and not native._HANDLER_ERRORS and not native._CACHE,
            'The actual one-shot registration admission did not settle exactly once.')
        for name in ('load_post', 'undo_post', 'redo_post'):
            require(sum(callback is native._reacquire for callback in getattr(bpy.app.handlers, name)) == 1,
                'Lifecycle callback missing or duplicated.')
        report['actual_deferred_registration_admission_once'] = True
        report['deferred_admission_witness'] = {'generation_at_enable': state['first_generation'],
            'generation_after_timer': native._REACQUIRE_GENERATION, 'manual_callback_or_current_invoked': False}
        with timed('standard disable after deferred registration'):
            addon_utils.disable('character_designer', default_set=False, handle_error=handle_error)
        require(not state['module'].__addon_enabled__ and not report.get('handled_errors'), 'Standard disable failed.')
        cleanup_witness('normal_disable')
        report['standard_disable_cleanup_verified'] = True
        return 'enable_cancel'

    def enable_cancel():
        with timed('standard enable then immediate disable before next tick'):
            module = addon_utils.enable('character_designer', default_set=False, persistent=False, handle_error=handle_error)
            require(module is state['module'] and module.__addon_enabled__ and not report.get('handled_errors'), 'Second enable failed.')
            native = state['native']
            timer = native._REACQUIRE_TIMER
            require(timer is not None and bpy.app.timers.is_registered(timer), 'Second enable lost its pending registration timer.')
            state['timers'].append(timer)
            generation = native._REACQUIRE_GENERATION
            addon_utils.disable('character_designer', default_set=False, handle_error=handle_error)
            require(not module.__addon_enabled__ and not report.get('handled_errors')
                and native._REACQUIRE_GENERATION == generation + 1, 'Immediate disable did not invalidate the pending generation.')
            state['cancel_generation'] = native._REACQUIRE_GENERATION
        cleanup_witness('immediate_disable')
        return 'observe_cancel'

    def observe_cancel():
        require(state['native']._REACQUIRE_GENERATION == state['cancel_generation'], 'Canceled registration callback ran later.')
        cleanup_witness('next_tick_after_immediate_disable')
        report['immediate_disable_cancels_without_late_admission'] = True
        return 'failure_cleanup'

    def failure_cleanup():
        module, native = state['module'], state['native']
        require(sys.modules.get('character_designer') is module and module.__time__ == os.path.getmtime(module.__file__),
            'Controlled injection requires the same standard-loaded module without an impending reload.')
        original = module.register_rigging_runtime
        def injected_registration():
            require(not hasattr(bpy.data, 'objects'), 'Failure injection did not run under RestrictBlend.')
            original()
            require(native._REACQUIRE_TIMER is not None and bpy.app.timers.is_registered(native._REACQUIRE_TIMER),
                'Controlled failure did not follow actual deferred registration.')
            state['timers'].append(native._REACQUIRE_TIMER)
            raise RuntimeError(INJECTED)
        module.register_rigging_runtime = injected_registration
        report['in_memory_failure_injection_performed'] = True
        try:
            with timed('standard enable controlled failure after native registration'):
                enabled = addon_utils.enable('character_designer', default_set=False, persistent=False, handle_error=handle_error)
        finally:
            module.register_rigging_runtime = original
        require(enabled is None and 'character_designer' not in sys.modules,
            'Standard failed enable did not return None and remove its failed root module.')
        errors = report.get('handled_errors', [])
        require(len(errors) == 1 and errors[0]['type'] == 'RuntimeError' and errors[0]['message'] == INJECTED
            and '_RestrictContext' not in errors[0]['traceback'], 'Failure cleanup masked the exact original injected error.')
        cleanup_witness('controlled_failure_cleanup')
        state['failed_generation'] = native._REACQUIRE_GENERATION
        report['controlled_failure_preserves_original_error_and_cleans_RNA'] = True
        return 'observe_failure'

    def observe_failure():
        require(state['native']._REACQUIRE_GENERATION == state['failed_generation'], 'Failed initialization left a late admission callback.')
        cleanup_witness('next_tick_after_controlled_failure')
        report['controlled_failure_leaves_no_late_callback'] = True
        return 'finish'

    def finish(error=None):
        if error is not None:
            report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        try:
            for row in report.get('source_inputs', {}).values():
                pin(row['path'], row['sha256'])
            for row in state.get('file_pins', {}).values():
                pin(row['path'], row['sha256'])
            report['input_files_unchanged'] = True
        except Exception as exc:
            report['input_pin_error'] = str(exc)
            error = exc
        required = ('standard_enable_returned_module_before_deferred_admission', 'actual_deferred_registration_admission_once',
            'standard_disable_cleanup_verified', 'immediate_disable_cancels_without_late_admission',
            'controlled_failure_preserves_original_error_and_cleans_RNA', 'controlled_failure_leaves_no_late_callback', 'input_files_unchanged')
        report['completed'] = report['passed'] = error is None and all(report.get(key) is True for key in required)
        write()
        print('STANDARD_REGISTRATION_07737 ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)
        def quit_owned():
            bpy.ops.wm.quit_blender('EXEC_DEFAULT', False)
            return None
        bpy.app.timers.register(quit_owned, first_interval=1., persistent=False)
        return None

    def tick():
        report['stage'] = state['phase']
        write()
        try:
            if state['phase'] == 'finish':
                return finish()
            phases = {'enable': enable, 'observe_admission': observe_admission, 'enable_cancel': enable_cancel,
                'observe_cancel': observe_cancel, 'failure_cleanup': failure_cleanup, 'observe_failure': observe_failure}
            state['phase'] = phases[state['phase']]()
            return .2
        except Exception as exc:
            return finish(exc)

    try:
        require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
            and len(bpy.context.window_manager.windows) == 1 and not bpy.context.preferences.filepaths.use_scripts_auto_execute,
            'Use one isolated factory blank headful Blender 5.2 with autoexecute disabled.')
        require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules),
            'Character Designer was already loaded.')
        report['source_inputs'] = {'source': pin(__file__, args.source_sha256), 'package_manifest': pin(args.package_manifest, args.manifest_sha256)}
        manifest = json.loads(Path(args.package_manifest).read_text(encoding='utf-8'))
        root = Path(manifest['source_root']).resolve()
        require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
            and manifest['version'] == '0.77.37' and len(manifest['files']) == 190
            and all(manifest['files'].get(name) == digest for name, digest in EXPECTED.items()), 'Wrong frozen .37 package.')
        state['root'] = root
        state['file_pins'] = {}
        for leaf, digest in manifest['files'].items():
            path = (root / leaf).resolve()
            require(path.is_relative_to(root), 'Invalid package path.')
            state['file_pins'][leaf] = pin(path, digest)
        require({path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()} == set(manifest['files']),
            'Frozen package has extra/missing files.')
        report['package_manifest_version'] = manifest['version']
        report['package_manifest_file_count'] = len(manifest['files'])
        state.update(blank=blank_state(), initial_properties=properties())
        require(not any(state['initial_properties'].values()), 'Factory blank has prior Character Designer properties.')
        sys.path.insert(0, str(root.parent))
        importlib.invalidate_caches()
        write()
        bpy.app.timers.register(tick, first_interval=.1, persistent=False)
    except Exception as exc:
        finish(exc)


if __name__ == '__main__':
    main()
