"""Diagnose no-edit Save on an authenticated owned recovery using frozen .32.

Execution completion does not mean semantic roundtrip or integration PASS.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
from types import MethodType, SimpleNamespace

ROUND = Path(__file__).resolve().parent
RECOVERY = ROUND / 'native_original20_r13_12/unverified_native12_quit_recovery.blend'
RECOVERY_SHA = 'd4cb2b7c8fb4667baa11e9f6cd7956076ef010f511069ea9c912a01e3d2dc5a6'
MANIFEST_SHA = '772fb8908edeabe886ab52f833063353cc24f1c597613c95fa3589986c52f205'
REPORT_SHA = '01b1d9fa2e428e03710a304bac7c8e7174c727edf650d3228b2c08fd09c7ea5b'
RELEASE_SHA = '239d846cade89959e0ecd73979c39e968d62acb86161cc4b990d9f4a10a7e6e2'
OLD_SOURCE_SHA = '82522f42851abbb1e3434cbaf4a9a26fd07aaaf327b1bee58400355c5fca7172'
HELPER_SHA = '7098c3b20a5a115423913ce91268cc4fd9a57adab9973c9c6c2000e2afd2d468'
PACKET_SHA = 'bffbbf00c3bcdfccc1a8bc1995aadeb188afb9f1d643bc78f1a34c8bb5cf7c4f'
PREPARED_SHA = '401b00d209b7806fa3c44c06fdf7e643256c64009d2abda45495a8b1cc0d4ac6'
CLOCK_SHA = 'cc0c749f29419747ec54195c63bd5d35249e97c2da0e62f5657880db77fc4e1d'
SNAPSHOT_SHA = '5387b972a123b81ab3b77df398fd1cfd3e33165a8934095bf3ff1953663c81ef'
ARTIST_SHA = 'cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path, expected):
    path = Path(path).resolve()
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(digest == expected.lower(), 'File pin changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': len(data)}


def document(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def load(path, expected, name, package=False):
    path = Path(pin(path, expected)['path'])
    spec = importlib.util.spec_from_file_location(name, path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def inventory(bpy, helper, pair, snapshot):
    probe = SimpleNamespace(bpy=bpy)
    for name in ('id', 'snapshot_identity'):
        setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))
    old = {helper.digest(probe.snapshot_identity(row['identity'])): row
           for row in snapshot['before']['actions']}
    owned = [probe.id(pair[key + '_action']) for key in ('source', 'custom')]
    owned_keys = {helper.digest(row) for row in owned}
    actual = {helper.digest(probe.id(action)): action for action in bpy.data.actions}
    require(len(old) == 10 and len(owned_keys) == 2 and not set(old) & owned_keys
            and len(actual) == 12 and set(actual) == set(old) | owned_keys,
            'Recovery must retain the original ten Actions and exactly the two authenticated input carriers.')
    for key, row in old.items():
        action = actual[key]
        slots = [{'handle': s.handle, 'target_id_type': s.target_id_type,
                  'identifier': s.identifier, 'name_display': s.name_display}
                 for s in action.slots] if action.is_action_layered else []
        require(slots == row['slots'], 'An original Action slot identity changed: ' + action.name)
    return {'original_count': len(old), 'original_identities_and_slots_exact': True,
            'original_actions': [probe.snapshot_identity(row['identity']) for row in old.values()],
            'owned_actions': owned, 'owned_slots': [pair['source_slot'], pair['custom_slot']],
            'source_uuid': pair['source_uuid'], 'custom_uuid': pair['capture']['newActionId'],
            'all_original_action_motion_or_geometry_preservation_claimed': False}


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    for name in ('package-manifest', 'harness', 'recovery'):
        parser.add_argument('--' + name, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    parser.add_argument('--quit-on-completion', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir()
            and not any(output.iterdir()), 'Use a new empty owned output directory.')
    inputs = {'source': pin(__file__, args.source_sha256),
              'harness': pin(args.harness, args.harness_sha256),
              'package_manifest': pin(args.package_manifest, args.package_manifest_sha256),
              'recovery': pin(args.recovery, args.recovery_sha256),
              'native12_report': pin(ROUND / 'native_original20_r13_12/original20_controls_report.json', REPORT_SHA),
              'native12_source': pin(ROUND / 'validate_original20_latest_saved_controls_r13.py', OLD_SOURCE_SHA),
              'native12_release': pin(ROUND / 'resource_release_X_NATIVE12_FAILED_GUN_VISIBILITY.json', RELEASE_SHA),
              'helper': pin(ROUND / 'original_cosha_control_round.py', HELPER_SHA)}
    require(Path(inputs['recovery']['path']) == RECOVERY.resolve()
            and inputs['recovery']['sha256'] == RECOVERY_SHA
            and inputs['package_manifest']['sha256'] == MANIFEST_SHA
            and Path(inputs['harness']['path']) == ROUND / 'validate_original20_latest_saved_controls_r14.py',
            'Use the exact owned Native12 recovery, frozen .32 package and explicitly pinned R14 helper.')
    old_report, release = (document(inputs[key]['path']) for key in ('native12_report', 'native12_release'))
    require(old_report['completed'] is False and old_report['source_inputs']['source'] == inputs['native12_source']
            and old_report['Gun_Motion_UI_edit_Key_restore']['public_save_count'] == 0
            and 'Show the Right Target collection' in old_report['error']
            and release['report'] == inputs['native12_report'] and release['completed'] is False
            and release['retained_handle_natural_exit'] is True and release['native_exit_code'] == 0
            and release['owned_native_gone'] is True and release['process_termination_performed'] is False,
            'The recovery provenance must remain the failed Native12 pre-Save run with actual release.')
    for key, expected in (('prepared_report', PREPARED_SHA), ('clock_report', CLOCK_SHA),
                          ('snapshot_receipt', SNAPSHOT_SHA), ('protected_artist', ARTIST_SHA)):
        row = old_report['source_inputs'][key]
        require(row['sha256'] == expected, 'Native12 input binding changed: ' + key)
        inputs[key] = pin(row['path'], expected)
    require(Path(inputs['protected_artist']['path']) == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve(),
            'Hash only the actual protected artist.')
    manifest = document(inputs['package_manifest']['path'])
    root = Path(manifest['source_root']).resolve()
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
            and manifest['version'] == '0.77.32' and len(manifest['files']) == 190
            and root == ROUND / 'package_05989efd/source/character_designer', 'Require the exact complete frozen .32 runtime.')
    files = {}
    for relative, expected in manifest['files'].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and '__pycache__' not in path.parts, 'Invalid package leaf.')
        files[relative] = pin(path, expected)
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(files),
            'The frozen runtime has extra or missing files.')
    import bpy
    require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
            and len(bpy.context.window_manager.windows) == 1, 'Require one fresh isolated headful Blender 5.2 factory child.')
    require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules),
            'Another Character Designer runtime is loaded.')
    report = {'schema': 'x.validation.native12-recovery-gun-smoke/1', 'completed': False,
              'scope': 'No-edit public Save after fresh public Edit; report exact DTO and semantic deltas, no artist mutation or integration claim.',
              'source_inputs': inputs, 'pid': os.getpid(), 'native_execution_performed': True,
              'artist_opened': False, 'artist_written': False, 'original_artist_integration_verified': False,
              'full_original_preservation_oracle_run': False, 'reference_phases_run': False,
              'private_curve_writes': False, 'Undo_Redo_performed': False, 'Unity_Apply_verified': False,
              'natural_exit_verified': False, 'natural_exit_external_retained_handle_readback_required': True}
    report_path = output / 'noop_save_diagnosis_report.json'
    write(report_path, report)
    baseline = backend = harness = None
    try:
        harness = load(inputs['harness']['path'], inputs['harness']['sha256'], 'native12_recovery_r14')
        helper = load(inputs['helper']['path'], HELPER_SHA, 'native12_recovery_protection7098')
        report['deferred_public_UI'] = list(harness.DEFERRED_PUBLIC_UI)
        package = load(root / '__init__.py', files['__init__.py']['sha256'], 'character_designer', package=True)
        require(tuple(package.bl_info['version']) == (0, 77, 32), 'Loaded runtime version mismatch.')
        package.register()
        for name in ('animation_worklist', 'animation_worklist_target', 'animation_worklist_fingerprint',
                     'animation_composition_weapon', 'unity_animation', 'unity_animation_rigging', 'unity_animation_original_inputs'):
            module = __import__('character_designer.' + name, fromlist=[name])
            require(Path(module.__file__).resolve() == root / (name + '.py'), 'Mixed runtime module: ' + name)
            setattr(package, name, module)
        backend = package.unity_animation_original_inputs
        require(bpy.ops.wm.open_mainfile(filepath=inputs['recovery']['path'], use_scripts=False, load_ui=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(), 'The owned recovery did not open.')
        with harness.owning_context(bpy) as (ctx, rig):
            print('RECOVERY_GUN_STAGE authenticate_persisted_session', flush=True)
            session = backend.current(rig)
            require(session is not None and 'original_inputs' in session,
                    'No authenticated persistent Original20 session; do not reconstruct or reimport it in this smoke.')
            pair = session['original_inputs']
            for pair_key, input_key in (('prepared_report', 'prepared_report'), ('clock_certificate', 'clock_report'),
                                        ('snapshot_receipt', 'snapshot_receipt')):
                require(harness.same_pin(pair[pair_key], inputs[input_key]), 'Persistent pair binding changed: ' + pair_key)
            require(pair['packet']['sha256'] == PACKET_SHA, 'The recovery is not the actual BF packet.')
            inputs['packet'] = pin(pair['packet']['path'], PACKET_SHA)
            packet = package.unity_animation.load_package(pair['packet']['path'])
            require(pair['capture'] == package.animation_rigging_contract.validate_capture(packet['rigging'], packet=packet)
                    and len(pair['capture']['frames']) == 59, 'The recovered capture changed from the actual BF59 packet.')
            harness.exact_initial_twenty(package, pair)
            report['Action_inventory'] = inventory(bpy, helper, pair, document(inputs['snapshot_receipt']['path']))
            require(session['enabled'] and session['tweak_enabled'] and session['edit_role'] == 'RIGGING'
                    and rig.mode == 'POSE' and rig.animation_data.use_tweak_mode
                    and package.unity_animation_rigging._time(ctx, session) == 0.,
                    'The recovery lost the active first-key editing context; no implicit repair is allowed.')
            baseline = backend.capture_inputs(ctx, session)
            require(set(baseline) == harness.RETURN_FIELDS and len(baseline['frames']) == 59,
                    'The recovered Return is not strict14/BF59.')
            write(output / 'baseline_Return.json', baseline)
            report['persistent_pair_and_exact_BF20_authenticated'] = True
            report['diagnostic_only'] = True
            report['no_edit_or_restore_performed'] = True
            with harness.temporary_body_display(bpy, ctx, rig, package, session, report, 'No-edit Save diagnosis'):
                print('NOOP_SAVE_STAGE fresh_public_edit', flush=True)
                result = bpy.ops.character_designer.original_inputs_edit('EXEC_DEFAULT', focus_gun_motion=True)
                require(result == {'FINISHED'}, 'Public Edit did not finish.')
                session = backend.current(rig)
                require(backend.capture_inputs(ctx, session) == baseline, 'Edit changed saved Input20 before Save.')
                print('NOOP_SAVE_STAGE actual_public_save_without_edit', flush=True)
                result = bpy.ops.character_designer.original_inputs_save('EXEC_DEFAULT')
                require(result == {'FINISHED'}, 'Public Save did not finish.')
                current = backend.capture_inputs(ctx, backend.current(rig))
                write(output / 'noop_saved_Return.json', current)
                from math import acos, degrees, sqrt
                deltas = []
                for index, (a, b) in enumerate(zip(baseline['frames'][0]['controls'], current['frames'][0]['controls'])):
                    qa, qb = a['targetRotation'], b['targetRotation']
                    dot = abs(sum(x*y for x,y in zip(qa,qb))) / sqrt(sum(x*x for x in qa)*sum(x*x for x in qb))
                    deltas.append({'control':index,
                        'position_max_component':max(abs(x-y) for x,y in zip(a['targetPosition'], b['targetPosition'])),
                        'rotation_degrees':degrees(2*acos(min(1., max(0., dot)))),
                        'hint_max_component':max(abs(x-y) for x,y in zip(a['hintPosition'], b['hintPosition'])),
                        'before':a, 'after':b})
                report['noop_save'] = {'public_edit_result':['FINISHED'], 'public_save_result':sorted(result),
                    'baseline_exact':current == baseline, 'differing_frames':[i for i,(a,b) in enumerate(zip(baseline['frames'],current['frames'])) if a != b],
                    'control_deltas':deltas, 'public_operator_ids':['character_designer.original_inputs_edit','character_designer.original_inputs_save']}
            result_path = output / 'noop_saved_scene.blend'
            result = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT',filepath=str(result_path),copy=True,check_existing=False)
            require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(), 'Diagnostic SaveCopy failed.')
            report['diagnostic_scene'] = pin(result_path,hashlib.sha256(result_path.read_bytes()).hexdigest())
            report['completed'] = True
            report['completed_means'] = 'Diagnosis executed and evidence saved; no semantic PASS or original integration claim.'
    except Exception as error:
        report.update(completed=False, error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        write(report_path, report)
        if baseline is not None and backend is not None and harness is not None:
            try:
                with harness.owning_context(bpy) as (ctx, rig):
                    current = backend.capture_inputs(ctx, backend.current(rig))
                    write(output / 'Return_after_failure.json', current)
                    report['failure_Return_equals_baseline'] = current == baseline
                    report['failure_Return_differing_frame_indices'] = [i for i, (a, b) in enumerate(zip(baseline['frames'], current['frames'])) if a != b]
            except Exception as residual_error:
                report['residual_readback_error'] = type(residual_error).__name__ + ': ' + str(residual_error)
        try:
            if bpy.data.filepath and Path(bpy.data.filepath).resolve() == RECOVERY.resolve():
                failure = output / 'failed_recovery_gun_smoke.blend'
                require(not failure.exists(), 'Do not overwrite an existing diagnostic scene.')
                result = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=str(failure), copy=True, check_existing=False)
                report['failure_scene_save_result'] = sorted(result)
                require(result == {'FINISHED'} and failure.is_file() and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(),
                        'Diagnostic SaveCopy did not finish or changed the active path.')
                report['failure_scene'] = pin(failure, hashlib.sha256(failure.read_bytes()).hexdigest())
            else:
                report['failure_scene_save_skipped'] = 'The authenticated owned recovery path is not currently open.'
        except Exception as save_error:
            report['failure_scene_error'] = type(save_error).__name__ + ': ' + str(save_error)
    finally:
        try:
            for row in list(inputs.values()) + list(files.values()):
                pin(row['path'], row['sha256'])
            report['input_files_unchanged'] = True
        except Exception as immutable_error:
            report['completed'] = False
            report['immutable_input_error'] = type(immutable_error).__name__ + ': ' + str(immutable_error)
        write(report_path, report)
        print('RECOVERY_GUN_SMOKE ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)
    if args.quit_on_completion:
        def quit_owned():
            observation = {'pid': os.getpid(), 'requested_from_timer': True,
                           'completed_report': report['completed'], 'natural_exit_still_external': True}
            try:
                observation['operator_result'] = sorted(bpy.ops.wm.quit_blender('EXEC_DEFAULT'))
            except Exception as error:
                observation['error'] = type(error).__name__ + ': ' + str(error)
            write(output / 'owned_quit_observation.json', observation)
            return None
        bpy.app.timers.register(quit_owned, first_interval=3., persistent=False)
    elif not report['completed']:
        raise RuntimeError(report.get('error', report.get('immutable_input_error')))


if __name__ == '__main__':
    main()
