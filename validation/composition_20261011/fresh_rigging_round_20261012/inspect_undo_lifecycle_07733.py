"""Observe load/Undo cache identity in one owned .33 failure copy; no semantic PASS."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

ROUND = Path(__file__).resolve().parent
RUNNER = ROUND / 'validate_original20_recovery_gun_undo_07733.py'
RUNNER_SHA = '6d89a1cb652a6aa564a66ab25c73312439dc887f25f44c0326a050305be50d1a'
FAILURE = ROUND / 'recovery_gun_undo_07733_01/failed_original20_recovery_gun_undo.blend'
FAILURE_SHA = '557d3180d5c7b2989a9f3ab7379aca85a49c6efd8a1f10a0ed51748320ebe4dc'
MANIFEST = ROUND / 'package_0fa9adfa/python_projection.json'
MANIFEST_SHA = '5b195a86a5b6d3834c7c76f02c0f83e42835e0cf7ca268556ec1e4ebf36f6640'


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--profile-root', required=True)
    parser.add_argument('--confirm-isolated-headful', action='store_true', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    assert hashlib.sha256(RUNNER.read_bytes()).hexdigest() == RUNNER_SHA, 'Frozen runner changed.'
    spec = importlib.util.spec_from_file_location('undo_diagnostic_runner_6d89', RUNNER)
    runner = importlib.util.module_from_spec(spec); sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)  # __name__ is not __main__; never execute its workflow.
    require, pin, write = runner.require, runner.pin, runner.write
    output, profile = Path(args.output_root).resolve(), Path(args.profile_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir()), 'Use a new empty output child.')
    require(profile.is_relative_to(Path(r'D:\Codex\XV').resolve()) and profile.is_dir(), 'Use an owned short profile.')
    for name in ('CONFIG', 'DATAFILES'):
        require((profile / name).is_dir() and Path(os.environ['BLENDER_USER_' + name]).resolve() == profile / name,
                'Use the owning profile ' + name)
    inputs = {'source': pin(__file__, args.source_sha256), 'runner': pin(RUNNER, RUNNER_SHA),
              'failure': pin(FAILURE, FAILURE_SHA), 'package_manifest': pin(MANIFEST, MANIFEST_SHA),
              'harness': pin(ROUND / 'validate_original20_latest_saved_controls_r14.py', runner.R14_SHA)}
    manifest = runner.document(MANIFEST); root = Path(manifest['source_root']).resolve()
    require(manifest['version'] == '0.77.33' and len(manifest['files']) == 190
            and root == ROUND / 'package_0fa9adfa/source/character_designer'
            and all(manifest['files'][name] == sha for name, sha in runner.RUNTIME_PINS.items()), 'Frozen .33 projection changed.')
    files = {name: pin(root / name, sha) for name, sha in manifest['files'].items()}
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(files), 'Projection leaves changed.')
    import bpy
    require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
            and len(bpy.context.window_manager.windows) == 1 and bpy.context.preferences.edit.use_global_undo
            and not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Use fresh isolated factory headful Blender with existing Undo and disabled autoexec.')
    require(not any(n == 'character_designer' or n.startswith('character_designer.') for n in sys.modules), 'Another runtime is loaded.')
    harness = runner.load(inputs['harness']['path'], runner.R14_SHA, 'undo_diagnostic_R14')
    package = runner.load(root / '__init__.py', files['__init__.py']['sha256'], 'character_designer', package=True)
    package.register()
    native = __import__('character_designer.unity_animation_rigging', fromlist=['unity_animation_rigging'])
    backend = __import__('character_designer.unity_animation_original_inputs', fromlist=['unity_animation_original_inputs'])
    report = {'schema': 'x.diagnostic.original20-undo-lifecycle/1', 'completed': False, 'diagnostic_only': True,
        'semantic_validation_pass': False, 'artist_opened_or_written': False, 'SaveCopy_performed': False,
        'no_op_Gun_Body_or_import_performed': False, 'pid': os.getpid(), 'source_inputs': inputs,
        'completed_means': 'Requested observations collected; not semantic, preservation or integration PASS.',
        'natural_exit_requires_external_retained_handle': True, 'observations': [], 'manual_current_calls': []}
    state = {'phase': 'open', 'marker': 'codex_undo_lifecycle_07733_' + str(os.getpid())}
    report_path = output / 'undo_lifecycle_report.json'

    def attempt(operation):
        try: return operation()
        except Exception as error: return {'error': type(error).__name__ + ': ' + str(error)}

    def identity(value):
        if value is None: return None
        return {'python_id': id(value), 'type': type(value).__name__,
            'pointer': attempt(lambda: int(value.as_pointer())), 'name': attempt(lambda: value.name)}

    def plain(value):
        if value is None or type(value) in (str, int, float, bool): return value
        if isinstance(value, dict): return {str(k): plain(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)): return [plain(v) for v in value]
        if hasattr(value, 'as_pointer'): return identity(value)
        return {'python_type': type(value).__name__, 'repr': attempt(lambda: repr(value))}

    def snapshot(label):
        # No current/activate/seek, no manual _reacquire. Read raw cache first.
        rig, scene = bpy.data.objects.get('CoshaRig'), bpy.data.scenes.get('Scene')
        cache = list(native._CACHE.items())
        row = {'label': label, 'rig': identity(rig), 'scene': identity(scene), 'context_scene': identity(bpy.context.scene),
            'raw_CACHE': plain(dict(cache)), 'raw_HANDLER_ERRORS': plain(dict(native._HANDLER_ERRORS)),
            'cache_identity_comparisons': [], 'raw_BUSY': plain(native._BUSY), 'raw_SUSPENDED': plain(native._SUSPENDED)}
        for key, session in cache:
            other, other_scene = session.get('rig'), session.get('scene')
            row['cache_identity_comparisons'].append({'cache_key': key, 'cached_rig': identity(other), 'cached_scene': identity(other_scene),
                'rig_is': other is rig, 'rig_equal': attempt(lambda: other == rig),
                'rig_pointer_equal': attempt(lambda: other.as_pointer() == rig.as_pointer()),
                'scene_is': other_scene is scene, 'scene_equal': attempt(lambda: other_scene == scene)})
        row['display_state'] = attempt(lambda: plain(native.display_state(rig)))
        row['SESSION_KEY_present'] = bool(rig is not None and native.SESSION_KEY in rig)
        row['persistent_SESSION'] = attempt(lambda: json.loads(rig[native.SESSION_KEY])) if row['SESSION_KEY_present'] else None
        payload = row['persistent_SESSION'].get('payload', {}) if isinstance(row['persistent_SESSION'], dict) else {}
        row['persistent_flags'] = {key: payload.get(key) for key in ('enabled', 'edit_role', 'tweak_enabled', 'source_read_only', 'preview_error')}
        if row['SESSION_KEY_present']:
            refs = rig.get(native._REFS_KEY, {})
            row['persistent_REFS'] = plain(dict(refs))
            def decoded_identity():
                used = set()
                decoded = native.composition._decode(payload, refs, used)
                other, other_scene = decoded.get('rig'), decoded.get('scene')
                return {'rig': identity(other), 'scene': identity(other_scene), 'used_refs_exact': used == set(refs),
                    'rig_is_live': other is rig, 'rig_equal_live': attempt(lambda: other == rig),
                    'rig_pointer_equal_live': attempt(lambda: other.as_pointer() == rig.as_pointer()),
                    'scene_is_live': other_scene is scene, 'scene_equal_live': attempt(lambda: other_scene == scene),
                    'scene_pointer_equal_live': attempt(lambda: other_scene.as_pointer() == scene.as_pointer()),
                    'scene_is_context': other_scene is bpy.context.scene,
                    'scene_equal_context': attempt(lambda: other_scene == bpy.context.scene),
                    'scene_pointer_equal_context': attempt(lambda: other_scene.as_pointer() == bpy.context.scene.as_pointer())}
            row['decoded_SESSION_identity_without_current'] = attempt(decoded_identity)
        ad = rig.animation_data if rig is not None else None
        row['NLA'] = {'tweak': ad.use_tweak_mode, 'use_nla': ad.use_nla, 'action': identity(ad.action),
            'slot': ad.action_slot_handle, 'rig_mode': rig.mode} if ad else None
        row['marker_present'] = bool(scene is not None and state['marker'] in scene)
        row['persistent_handlers'] = {name: [{'name': getattr(h, '__name__', None), 'module': getattr(h, '__module__', None),
            'python_id': id(h), 'persistent': bool(getattr(h, '_bpy_persistent', False)), 'is_native_reacquire': h is native._reacquire}
            for h in getattr(bpy.app.handlers, name)] for name in ('load_post', 'undo_pre', 'undo_post', 'redo_post')}
        row['native_handler_counts'] = {name: sum(h is callback for h in getattr(bpy.app.handlers, name)) for name, callback in
            (('load_post', native._reacquire), ('undo_post', native._reacquire), ('redo_post', native._reacquire),
             ('frame_change_post', native._frame), ('depsgraph_update_post', native._depsgraph))}
        report['observations'].append(row); write(report_path, report)

    def manual_current(label):
        def read():
            with harness.owning_context(bpy) as (ctx, rig):
                session = backend.current(rig)
                return {'present': session is not None, 'rig': identity(rig), 'session_rig': identity(session.get('rig')) if session else None,
                        'owner': session.get('owner') if session else None}
        report['manual_current_calls'].append({'label': label, 'result': attempt(read)})

    def finish(error=None):
        report['completed'] = error is None
        if error: report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        try:
            for row in list(inputs.values()) + list(files.values()): pin(row['path'], row['sha256'])
            report['input_files_unchanged'] = True
        except Exception as pin_error:
            report.update(completed=False, input_pin_error=str(pin_error))
        write(report_path, report)
        print('UNDO_LIFECYCLE_DIAGNOSIS ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)
        def quit_owned():
            result = attempt(lambda: sorted(bpy.ops.wm.quit_blender('EXEC_DEFAULT', False)))
            write(output / 'owned_quit_observation.json', {'pid': os.getpid(), 'operator_result': result, 'natural_exit_requires_external_evidence': True})
            return None
        bpy.app.timers.register(quit_owned, first_interval=3., persistent=False)
        return None

    def tick():
        try:
            if state['phase'] == 'open':
                require(bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=str(FAILURE), use_scripts=False, load_ui=False) == {'FINISHED'}
                        and Path(bpy.data.filepath).resolve() == FAILURE.resolve(), 'Owned failure copy did not open.')
                snapshot('opened_before_any_manual_current'); manual_current('after_load'); snapshot('opened_after_manual_current')
                require(state['marker'] not in bpy.data.scenes['Scene'], 'Owned marker already exists.')
                runner.push_checkpoint(bpy, report, 'Undo lifecycle before owned Scene marker')
                state['phase'] = 'marker'
            elif state['phase'] == 'marker':
                with harness.owning_context(bpy) as (ctx, rig): ctx.scene[state['marker']] = 1
                runner.push_checkpoint(bpy, report, 'Undo lifecycle after owned Scene marker')
                snapshot('marker_checkpoint_before_undo'); state['phase'] = 'undo'
            elif state['phase'] == 'undo':
                runner.native_undo_redo(bpy, report); state['phase'] = 'readback'
            elif state['phase'] == 'readback':
                snapshot('undo_next_tick_before_any_manual_current')
                report['marker_disappeared_after_actual_Undo'] = state['marker'] not in bpy.data.scenes['Scene']
                manual_current('after_Undo'); snapshot('undo_next_tick_after_manual_current')
                return finish()
            write(report_path, report)
            return .1
        except Exception as error: return finish(error)
    write(report_path, report)
    bpy.app.timers.register(tick, first_interval=.1, persistent=True)


if __name__ == '__main__':
    main()
