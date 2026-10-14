"""Source draft: one owned headful original clone, exact Input20 and controls-only publication.

Requires actual successful clock plus retained-handle release and a future pinned R8
projection. The first scope uses public backend creation/reference/publish/close APIs;
Target/Hint edits, Key, public UI and Undo/Redo remain separate unexecuted scopes.
The artist is hashed only. No ordinary Attach, model import or fresh Rig setup occurs.
"""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import traceback
from types import MethodType, SimpleNamespace

ROUND = Path(__file__).resolve().parent
CLOCK_SHA = '8df8ac78580623c83befbc35d193747934bdb17c8666a25b604ad299c4a059bf'
PROTECTION_SHA = '7098c3b20a5a115423913ce91268cc4fd9a57adab9973c9c6c2000e2afd2d468'
ORACLE_SHA = '260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d'
SNAPSHOT_SHA = '99b08426346d77908dbed93e518bc0e2370701a0e8ee906df7d36cb072bb2949'
SEED_SHA = '1c1984156b3d7637596382ff12359f3460f51b4b6216cd088f9dd97c1cd4bf41'
ARTIST_SHA = '3cd5619d70e8b4e21c2483884a04d352a2405f0eab02f00d34d306c81c5aa4b0'
RETURN_FIELDS = {'schema', 'sourcePacketSha256', 'bindingsSha256', 'targetGuid', 'workItemId',
    'newActionId', 'sourceAction', 'sourceActionSlot', 'targetInputAction', 'targetInputActionSlot',
    'duration', 'sampleRate', 'loopTime', 'frames'}
DEFERRED_PUBLIC_UI = ('character_designer.original_inputs_attach', 'character_designer.original_inputs_edit',
    'character_designer.original_inputs_save', 'character_designer.original_inputs_body_view',
    'character_designer.original_inputs_publish', 'character_designer.original_inputs_close')


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-sha256', required=True)
    for name in ('snapshot-receipt', 'seed', 'prepared-report', 'clock-report', 'clock-exit-receipt',
                 'package-manifest', 'protected-artist', 'preservation-oracle'):
        p.add_argument('--' + name, required=True); p.add_argument('--' + name + '-sha256', required=True)
    p.add_argument('--output-root', required=True); p.add_argument('--profile-root', required=True)
    p.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    p.add_argument('--quit-on-completion', action='store_true')
    return p.parse_args(sys.argv[sys.argv.index('--') + 1:])


def require(value, message):
    if not value: raise RuntimeError(message)


def load(path, expected, name, *, package=False):
    import hashlib
    path = Path(path).resolve()
    require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Helper/runtime pin changed: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path, submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def same_pin(left, right):
    return (Path(left['path']).resolve() == Path(right['path']).resolve()
            and left['sha256'] == right['sha256'] and left['bytes'] == right['bytes'])


def f32(value):
    return struct.unpack('<f', struct.pack('<f', float(value)))[0]


@contextmanager
def owning_context(bpy):
    scene, rig = bpy.data.scenes.get('Scene'), bpy.data.objects.get('CoshaRig')
    require(scene is not None and rig is not None and rig.type == 'ARMATURE' and not rig.library
            and not rig.data.library and scene.objects.get(rig.name) == rig, 'Use the actual original Scene/CoshaRig.')
    windows = list(bpy.context.window_manager.windows)
    require(len(windows) == 1, 'Use one owned headful window.')
    windows[0].scene = scene
    layer = scene.view_layers.get('ViewLayer')
    require(layer is not None and layer.objects.get(rig.name) == rig, 'The original ViewLayer/Rig is missing.')
    with bpy.context.temp_override(window=windows[0], scene=scene, view_layer=layer):
        require(bpy.context.active_object == rig, 'The saved original active object must remain CoshaRig.')
        yield bpy.context, rig


def protection(helper, package, bpy, ctx, rig, receipt, oracle, report):
    # Bind only unchanged read-only7098 protection methods; no old Round instance,
    # constructor, ordinary Attach/model gate or old native control flow is used.
    names = ('id', 'plain', 'rna', 'old_state', 'snapshot_identity', 'snapshot_value', 'check_loaded_snapshot',
             'actions', 'original_data', 'asset_snapshot', 'guard_old', 'guard_assets')
    probe = SimpleNamespace(bpy=bpy, worklist=package.animation_worklist,
        target=package.animation_worklist_target, ua=package.unity_animation, native=package.unity_animation_rigging,
        weapon=package.animation_composition_weapon, fingerprints=package.animation_worklist_fingerprint,
        oracle=oracle, report=report, old=None, snapshot_receipt=receipt)
    for name in names: setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))
    probe.check_loaded_snapshot(ctx, rig)
    record = probe.target._load(rig)
    probe.original_capture = probe.plain(record['capture'])
    probe.original_mapped_names = record['mapped_names']
    probe.original_objects = {helper.digest(probe.id(o)) for o in ctx.scene.objects}
    return probe


def exact_initial_twenty(package, pair):
    native = package.unity_animation_rigging
    capture = pair['capture']; expected = {}
    for index, side in enumerate(('Right', 'Left')):
        rotations, previous = [], None
        for frame in capture['frames']:
            values = list(frame['controls'][index]['targetRotation'])
            if previous is not None and sum(a * b for a, b in zip(previous, values)) < 0: values = [-v for v in values]
            rotations.append(values); previous = values
        for field, count in (('targetPosition', 3), ('targetRotation', 4), ('hintPosition', 3)):
            path = '[' + json.dumps(native._property(side, field)) + ']'
            for component in range(count):
                values = ([row[component] for row in rotations] if field == 'targetRotation'
                    else [frame['controls'][index][field][component] for frame in capture['frames']])
                expected[path, component] = [(f32(1. + frame['time'] * capture['sampleRate']), f32(value))
                    for frame, value in zip(capture['frames'], values)]
    require(len(expected) == 20, 'The capture is not the fixed two-arm twenty-scalar input domain.')
    for action, slot in ((pair['source_action'], pair['source_slot']), (pair['custom_action'], pair['custom_slot'])):
        curves = native._curves(action, slot)
        require(set(curves) == set(expected), 'A new input carrier has missing or extra channels.')
        for key, curve in curves.items():
            require([(float(p.co.x), float(p.co.y)) for p in curve.keyframe_points] == expected[key],
                    'The initial captured Input20 was offset or otherwise changed: ' + str(key))


def main():
    sys.dont_write_bytecode = True
    args = arguments()
    helper = load(ROUND / 'original_cosha_control_round.py', PROTECTION_SHA, 'original20_readonly_protection7098')
    pin, document, digest = helper.pin, helper.document, helper.digest
    inputs = {'source': pin(__file__, args.source_sha256), 'protection_helper': pin(ROUND / 'original_cosha_control_round.py', PROTECTION_SHA)}
    for name in ('snapshot_receipt', 'seed', 'prepared_report', 'clock_report', 'clock_exit_receipt', 'package_manifest', 'protected_artist', 'preservation_oracle'):
        inputs[name] = pin(getattr(args, name), getattr(args, name + '_sha256'))
    require(inputs['snapshot_receipt']['sha256'] == SNAPSHOT_SHA and inputs['seed']['sha256'] == SEED_SHA
            and inputs['protected_artist']['sha256'] == ARTIST_SHA and inputs['preservation_oracle']['sha256'] == ORACLE_SHA,
            'Use actual latest99B/1C, protected3CD artist and unchanged260B oracle.')
    require(Path(inputs['protected_artist']['path']) == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve(), 'Only hash the actual artist path.')
    receipt, clock, exited = (document(inputs[name]['path']) for name in ('snapshot_receipt', 'clock_report', 'clock_exit_receipt'))
    require(receipt['completed'] is True and receipt['backup_verified'] is True and receipt['metadata_preservation_verified'] is True
            and same_pin(receipt['backup'], inputs['seed']) and same_pin(receipt['protected_artist'], inputs['protected_artist']), 'The actual latest clone receipt is incomplete.')
    require(clock['schema'] == 'x.validation.original-legacy-base-clock/1' and clock['completed'] is True
            and clock['native_execution_performed'] is True and clock['legacy_clock_known'] is True
            and all(clock[k] is True for k in ('context_and_pose_restored', 'raw_asset_data_unchanged', 'input_files_unchanged'))
            and clock['source_inputs']['source']['sha256'] == CLOCK_SHA
            and same_pin(clock['source_inputs']['snapshot_receipt'], inputs['snapshot_receipt'])
            and same_pin(clock['source_inputs']['seed'], inputs['seed']), 'The actual completed clock certificate is absent or Unknown.')
    require(exited['schema'] == 'x.validation.resource-release/1' and exited['retained_handle_natural_exit'] is True
            and type(exited['native_exit_code']) is int and exited['native_exit_code'] == 0
            and exited['owned_native_gone'] is True and exited['process_termination_performed'] is False
            and type(exited['owned_pid']) is int and exited['owned_pid'] == clock['pid']
            and isinstance(exited['owned_process_filetime'], str) and exited['owned_process_filetime'].isdigit()
            and 0 < int(exited['owned_process_filetime']) < 2 ** 64
            and isinstance(exited['native_exited_utc'], str) and exited['native_exited_utc'].endswith(('Z', '+00:00'))
            and same_pin(exited['clock_source'], clock['source_inputs']['source'])
            and same_pin(exited['clock_report'], inputs['clock_report']), 'Require the actual retained-handle clock release, exact FILETIME and report binding.')
    output, profile = Path(args.output_root).resolve(), Path(args.profile_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir()), 'Use a new empty owned output child.')
    require(profile.is_relative_to(Path(r'D:\Codex\XV').resolve()) and profile.is_dir() and {p.name for p in profile.iterdir()} == {'CONFIG', 'DATAFILES'}, 'Use a fresh short owned profile.')
    for name in ('CONFIG', 'DATAFILES'):
        path = profile / name
        require(path.is_dir() and not any(path.iterdir()) and Path(os.environ['BLENDER_USER_' + name]).resolve() == path, 'Bind the fresh profile ' + name)
    require(Path(inputs['seed']['path']).is_relative_to(ROUND) and Path(inputs['seed']['path']) != Path(inputs['protected_artist']['path']), 'Never open or save the artist.')
    manifest = document(inputs['package_manifest']['path']); root = Path(manifest['source_root']).resolve()
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer' and root.name == 'character_designer'
            and isinstance(manifest['source_provenance'], dict) and manifest['source_provenance'], 'Use a real future complete projection.')
    required = {'__init__.py', 'unity_animation_original_inputs.py', 'animation_original_inputs_ui.py', 'unity_animation_rigging.py'}
    require(required <= set(manifest['files']), 'The future R8 Original20 payload is incomplete.')
    files = {}
    for relative, expected in manifest['files'].items():
        path = (root / relative).resolve()
        require(not Path(relative).is_absolute() and path.is_relative_to(root) and '__pycache__' not in Path(relative).parts, 'A projected leaf escaped the package.')
        files[relative] = pin(path, expected)
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(files), 'The future package has extra or missing leaves.')
    import bpy
    require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2), 'Use one fresh owned headful5.2 factory child.')
    require(not any(n == 'character_designer' or n.startswith('character_designer.') for n in sys.modules), 'Another Character Designer runtime is already loaded.')
    report = {'schema': 'x.validation.original20-controls-clone/1', 'completed': False, 'source_inputs': inputs,
        'native_execution_performed': True, 'package_manifest_version': manifest['version'], 'package_file_count': len(files),
        'artist_opened': False, 'artist_written': False, 'original_artist_integration_verified': False,
        'ordinary_Attach_or_FBX_or_fresh_Rig_setup_performed': False, 'Target_Hint_edit_or_Key_or_Undo_Redo_performed': False,
        'public_UI_operators_executed': False, 'deferred_public_UI': list(DEFERRED_PUBLIC_UI), 'Unity_Apply_verified': False,
        'world_model_equivalence': 'Unknown', 'natural_exit_verified': False, 'scope': 'Exact captured Input20, read-only Body references, actual controls-only publication and owned clone save/reopen.'}
    report_path = output / 'original20_controls_report.json'
    with report_path.open('x', encoding='utf-8') as stream: json.dump(report, stream, indent=2)
    def guard(ctx, probe, boundary):
        saved = probe.worklist.state(ctx)
        require({i.item_id for i in saved.items} == set(probe.old['rows']), 'An original row was added or removed.')
        probe.guard_old(ctx, boundary, full_motions=True)
        probe.guard_assets(ctx, boundary)
    try:
        package = load(root / '__init__.py', files['__init__.py']['sha256'], 'character_designer', package=True)
        require('.'.join(map(str, package.bl_info['version'])) == manifest['version'], 'The loaded runtime version differs from the hashed projection.')
        package.register()
        for name in ('animation_worklist', 'animation_worklist_target', 'animation_worklist_fingerprint', 'animation_composition_weapon',
                     'unity_animation', 'unity_animation_rigging', 'unity_animation_original_inputs'):
            module = __import__('character_designer.' + name, fromlist=[name])
            require(Path(module.__file__).resolve() == root / (name + '.py'), 'A runtime module came from another package.')
            setattr(package, name, module)
        backend = package.unity_animation_original_inputs
        oracle = load(inputs['preservation_oracle']['path'], ORACLE_SHA, 'original20_raw_oracle260b')
        require(bpy.ops.wm.open_mainfile(filepath=inputs['seed']['path'], use_scripts=False, load_ui=False) == {'FINISHED'}, 'The owned original snapshot did not open.')
        require(Path(bpy.data.filepath).resolve() == Path(inputs['seed']['path']), 'Another scene was loaded.')
        with owning_context(bpy) as (ctx, rig):
            probe = protection(helper, package, bpy, ctx, rig, receipt, oracle, report)
            probe.old = probe.old_state(ctx); probe.old['actions'] = probe.actions(full_motions=True)
            probe.assets_before = probe.asset_snapshot(ctx, rig)
            require(backend.PAIR_KEY not in rig, 'Keep an existing input pair; this scope needs the untouched1C seed.')
            session = backend.import_inputs(ctx, rig, inputs['prepared_report']['path'], inputs['prepared_report']['sha256'], inputs['clock_report']['path'], inputs['clock_report']['sha256'])
            pair = session['original_inputs']; packet = package.unity_animation.load_package(pair['packet']['path'])
            require(pair['capture'] == package.animation_rigging_contract.validate_capture(packet['rigging'], packet=packet), 'The actual prepared capture was changed.')
            exact_initial_twenty(package, pair)
            baseline_dto = backend.capture_inputs(ctx, session)
            require(set(baseline_dto) == RETURN_FIELDS and len(baseline_dto) == 14, 'The Return is not the strict fourteen-field DTO.')
            report['initial_Input20_exact_prepared_capture_verified'] = True
            for side in ('SOURCE', 'CUSTOM'):
                backend.view_body(ctx, rig, side)
                session = backend.current(rig)
                require(session['preview_reference']['legacy_side'] == side and backend.capture_inputs(ctx, session) == baseline_dto, 'A read-only Body reference changed the input Return.')
                exact_initial_twenty(package, session['original_inputs']); guard(ctx, probe, 'reference_' + side)
            published = backend.publish_inputs(ctx, rig, str(output / 'captured_controls_Return.json'))
            require(set(published) == {'return', 'publication'}, 'The publisher returned no actual two-file ownership pins.')
            for row in published.values(): pin(row['path'], row['sha256'])
            pub = document(published['publication']['path'])
            require(document(published['return']['path']) == baseline_dto and pub['completed'] is True and pub['schema'] == backend.PUBLICATION_SCHEMA
                    and pub['controlChannelCount'] == 20 and pub['returnSha256'] == published['return']['sha256']
                    and pub['sourceActionId'] == pair['source_uuid'] and pub['targetInputActionId'] == pair['capture']['newActionId'], 'The actual publication disagrees with the captured20/strict14 identities.')
            require(all(pub[field] == baseline_dto[field] for field in RETURN_FIELDS - {'schema', 'frames'})
                    and all(pub[field] is True for field in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly')), 'The published controls-only identity headers changed.')
            report['actual_controls_only_publication'] = published
            backend.close_owned(ctx, rig); guard(ctx, probe, 'closed_before_save')
            saved_pair_motions = {key: package.unity_animation_rigging._motion(pair[key + '_action'], pair[key + '_slot']) for key in ('source', 'custom')}
        clone = output / 'original20_controls_owned.blend'
        require(not clone.exists() and bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=str(clone), check_existing=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == clone, 'The owned clone was not saved successfully.')
        report['saved_clone'] = pin(clone, helper.sha(clone))
        require(bpy.ops.wm.open_mainfile(filepath=str(clone), use_scripts=False, load_ui=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == clone, 'The saved owned clone did not reopen.')
        with owning_context(bpy) as (ctx, rig):
            guard(ctx, probe, 'reopened_closed_clone')
            require(backend.current(rig) is None and backend.PAIR_KEY in rig, 'The saved closed owner state did not reopen.')
            session = backend.import_inputs(ctx, rig, inputs['prepared_report']['path'], inputs['prepared_report']['sha256'], inputs['clock_report']['path'], inputs['clock_report']['sha256'])
            pair = session['original_inputs']; exact_initial_twenty(package, pair)
            require(backend.capture_inputs(ctx, session) == baseline_dto
                    and all(package.unity_animation_rigging._motion(pair[key + '_action'], pair[key + '_slot']) == value for key, value in saved_pair_motions.items()), 'Save/reopen changed an input carrier or Return.')
            backend.close_owned(ctx, rig); guard(ctx, probe, 'reopened_final_closed')
        for row in inputs.values(): pin(row['path'], row['sha256'])
        for row in files.values(): pin(row['path'], row['sha256'])
        for row in published.values(): pin(row['path'], row['sha256'])
        report.update(completed=True, original_clone_only=True, save_reopen_verified=True,
            original_rows_header_Body_keys_and_observed_assets_preserved=True, strict14_Return_and_twenty_scalar_publication_verified=True,
            input_files_unchanged=True, no_QA_offset_or_authored_key_performed=True)
    except Exception as error:
        report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
    finally:
        report['natural_exit_external_retained_handle_readback_required'] = True
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        print('ORIGINAL20_CONTROLS_CLONE ' + json.dumps({'completed': report['completed'], 'report': pin(report_path, helper.sha(report_path))}))
    if args.quit_on_completion:
        bpy.ops.wm.quit_blender()
    elif not report['completed']:
        raise RuntimeError(report['error'])


if __name__ == '__main__': main()
