"""Prepared Source: gated in-process Original20 import/close and original artist save.

run() is the only entry. No automatic execution, process/SDK call, reload,
registration, model import, ordinary Attach, QA edit, worker or publication.
Actual clone/retained-END/refresh receipts are mandatory future parameters.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
from types import MethodType, SimpleNamespace

ROUND = Path(r'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012')
HISTORY = Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011')
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
REFRESH_SHA = 'b16d5f0e9b01cf3f356982d98baf99680391a3e4f2e2f650869696ffa3d1ae17'
CLONE_SHA = '2cce4620c90d21b10c71c569449069b3cecddd5bcc9b46c7ed042f7e6a7a389b'
BACKEND_SHA = 'a7fc96e0ad2e12ee8ddf425198fa3edd89006facd3abc906905b50223d7e5adf'
PROTECTION_SHA = '7098c3b20a5a115423913ce91268cc4fd9a57adab9973c9c6c2000e2afd2d468'
CFAA_SHA = 'cfaa6dc580d69dbdc7c752078752f2a3cbe89f33ec02a60c5186a196fba4cdcb'
LIGHT_SHA = '6df88f6e605a2a4e96eb1d3f261ed456dbe150c3e54a0d1e68f0f5aa962ff971'
ORACLE_SHA = '260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d'
VERIFIER_SHA = 'f220d2f398e16a190715fd28a9c161207bcbeaf05946ff9d516038408ba2bf32'
POSE_WRITE_SHA = '6ac66dc320e88238075a243586cdb92b535da14cc4decf912886dedb912296d4'
POSE_READ_SHA = '26123aaff8dd5a83e00611ae52ca1aa1e4bb30db69294b99dfb1f5a9d6391aa2'
POSE_BACKUP_SHA = 'c956d715940c7a92ea19a85e26997498a7bda0b0d86a300a443ba507e0055dc6'
POSE_WRITER_SHA = '702aa1b69291cba7e8bc722d3324507f8d412043a6b15503d97a4b9fb9cc5458'
POSE_CONTENT_SHA = 'acdd30eda498c058f9fea9a7a019ec11ffd355e7409b666e26cb98e69d225d3f'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pose_digest(value):
    # Exact existing Pose writer serialization; never import its executing module.
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()

def curves(action):
    if action.is_action_layered:
        return [curve for layer in action.layers for strip in layer.strips
                for bag in strip.channelbags for curve in bag.fcurves]
    return list(action.fcurves)


def pose_content(action):
    result = {'name': action.name, 'custom_properties': {key: action[key] for key in action.keys()},
        'slots': [{'handle': slot.handle, 'identifier': slot.identifier, 'name_display': slot.name_display,
                   'target_id_type': slot.target_id_type} for slot in action.slots],
        'layer_names': [layer.name for layer in action.layers],
        'layout': [{'name': layer.name, 'strips': [{'type': strip.type,
            'channelbags': [{'slot_handle': bag.slot_handle,
                'curves': [[curve.data_path, curve.array_index] for curve in bag.fcurves]}
                for bag in strip.channelbags]} for strip in layer.strips]} for layer in action.layers],
        'curves': []}
    for curve in curves(action):
        result['curves'].append({'data_path': curve.data_path, 'array_index': curve.array_index,
            'mute': curve.mute, 'lock': curve.lock, 'extrapolation': curve.extrapolation,
            'group': curve.group.name if curve.group else None,
            'modifiers': [(modifier.type, modifier.name, modifier.mute) for modifier in curve.modifiers],
            'sampled': [list(point.co) for point in curve.sampled_points],
            'keys': [{'co': list(key.co), 'left': list(key.handle_left), 'right': list(key.handle_right),
                'interpolation': key.interpolation, 'easing': key.easing, 'type': key.type,
                'left_type': key.handle_left_type, 'right_type': key.handle_right_type,
                'back': key.back, 'amplitude': key.amplitude, 'period': key.period,
                'selected': [key.select_control_point, key.select_left_handle, key.select_right_handle]}
                for key in curve.keyframe_points]})
    return result


def exact(row, refresh):
    require(set(row) == {'path', 'sha256', 'bytes'} and refresh.pin(row['path'], row['sha256']) == row,
            'A required exact three-field input pin changed.')
    return row


def admitted_clone(inputs, refresh):
    control = refresh.document(inputs['clone_report'])
    exited = refresh.document(inputs['clone_exit'])
    updated = refresh.document(inputs['refresh_receipt'])
    require(control['schema'] == 'x.validation.original20-controls-clone/1'
            and control['completed'] is True and control['native_execution_performed'] is True
            and control['package_manifest_version'] == '0.77.27' and control['package_file_count'] == 190
            and control['artist_opened'] is False and control['artist_written'] is False
            and all(control[k] is True for k in ('original_clone_only', 'save_reopen_verified',
                'original_rows_header_Body_keys_and_observed_assets_preserved',
                'strict14_Return_and_twenty_scalar_publication_verified', 'input_files_unchanged',
                'no_QA_offset_remaining', 'public_Custom20_edit_Save_restore_verified',
                'initial_Input20_exact_prepared_capture_verified')),
            'Actual completed .27 original-clone Input20/edit/restore/save-reopen/publication is required.')
    require(control['source_inputs']['source'] == inputs['clone_source'], 'Clone source/report pin mismatch.')
    witness = control['live_Target_edit_and_Save_restore']
    require(witness['restored_exact_BF59'] is True and type(witness['public_save_count']) is int
            and witness['public_save_count'] == 2 and witness['edited_Return_readback_verified'] is True,
            'The clone must have restored exact BF59 after its real public Target edit/Save.')
    require(exited['schema'] == 'x.validation.resource-release/1' and exited['status'] == 'ACTUAL_RELEASE'
            and exited['passed'] is True and exited['retained_handle_natural_exit'] is True
            and type(exited['native_exit_code']) is int and exited['native_exit_code'] == 0
            and type(exited['owned_pid']) is int and exited['owned_pid'] > 0
            and isinstance(exited['owned_process_filetime'], str) and exited['owned_process_filetime'].isdigit()
            and 0 < int(exited['owned_process_filetime']) < 2 ** 64
            and isinstance(exited['native_exited_utc'], str) and exited['native_exited_utc'].endswith(('Z', '+00:00'))
            and exited['owned_native_gone'] is True and exited['all_owned_activity_closed'] is True
            and exited['process_termination_performed'] is False
            and exited['source'] == inputs['clone_source'] and exited['report'] == inputs['clone_report'],
            'The matching retained-handle natural0/closed END proof is required.')
    require(updated['schema'] == 'x.validation.original-artist-runtime-refresh/1'
            and updated['completed'] is True and updated['native_execution_performed'] is True
            and updated['new_version'] == [0, 77, 27]
            and updated['phase'] == 'completed_refresh_only_no_Attach_or_save'
            and updated['original_Scene_rows_header_catalog_Actions_slots_assets_pose_context_preserved'] is True
            and updated['original_artist_disk_unchanged'] is True and updated['original_artist_saved'] is False
            and updated['Pose_fake_user_final_save_step_performed'] is False
            and updated['pid'] == inputs['expected_pid']
            and updated['external_process_filetime'] == inputs['external_process_filetime'],
            'The actual completed original-process refresh must preserve the same original and process identity.')
    for key, label in (('original20_report', 'clone_report'), ('original20_source', 'clone_source'),
                       ('original20_exit_receipt', 'clone_exit'), ('package_manifest', 'package_manifest'),
                       ('protected_artist', 'protected_artist'), ('source', 'refresh_source')):
        require(updated['source_inputs'][key] == inputs[label], 'Refresh chain differs: ' + key)
    for key in ('prepared_report', 'clock_report'):
        inputs[key] = exact(control['source_inputs'][key], refresh)
    for key in ('snapshot_receipt', 'seed', 'protected_artist', 'package_manifest'):
        refresh_key = {'snapshot_receipt': 'latest_snapshot_receipt', 'seed': 'latest_seed'}.get(key, key)
        require(control['source_inputs'][key] == updated['source_inputs'][refresh_key], 'Clone/refresh ancestry differs: ' + key)
        inputs[key] = exact(control['source_inputs'][key], refresh)
    saved = exact(control['saved_clone'], refresh)
    require(Path(saved['path']).resolve().is_relative_to(ROUND) and Path(saved['path']).resolve() != ARTIST.resolve(),
            'Only the actual completed saved clone may certify save/reopen.')
    inputs['saved_clone'] = saved
    published = control['actual_controls_only_publication']
    require(set(published) == {'return', 'publication'}, 'Require the actual final two-file controls-only publication.')
    for key, row in published.items():
        inputs['clone_' + key] = exact(row, refresh)
        require(updated['source_inputs']['original20_' + key] == row, 'Refresh did not admit this exact final publication.')
    dto, pub = (refresh.document(published[key]) for key in ('return', 'publication'))
    require(set(dto) == refresh.RETURN_FIELDS and pub['schema'] == 'cdesigner.controls-only-publication/1'
            and pub['completed'] is True and pub['controlChannelCount'] == 20
            and pub['returnSha256'] == published['return']['sha256'] and pub['targetInputActionId'] == dto['newActionId']
            and all(pub[k] == dto[k] for k in refresh.RETURN_FIELDS - {'schema', 'frames'})
            and all(pub[k] is True for k in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly'))
            and len(dto['frames']) == 59 and dto['sampleRate'] == 60,
            'Final clone Return14/Input20 publication is incomplete or inconsistent.')
    return updated, dto


def protect(helper, package, bpy, ctx, rig, oracle, report):
    # No old Round constructor or saved10 qualification is called.
    probe = SimpleNamespace(bpy=bpy, worklist=package.animation_worklist,
        target=package.animation_worklist_target, ua=package.unity_animation,
        native=package.unity_animation_rigging, weapon=package.animation_composition_weapon,
        fingerprints=package.animation_worklist_fingerprint, oracle=oracle, report=report, old=None)
    for name in ('id', 'plain', 'rna', 'old_state', 'actions', 'original_data', 'asset_snapshot', 'guard_old', 'guard_assets'):
        setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))
    record = probe.target._load(rig)
    probe.original_capture = probe.plain(record['capture'])
    probe.original_mapped_names = record['mapped_names']
    probe.original_objects = {helper.digest(probe.id(o)) for o in ctx.scene.objects}
    old_actions = probe.actions(full_motions=True)
    probe.old = probe.old_state(ctx)
    probe.old['actions'] = old_actions
    probe.assets_before = probe.asset_snapshot(ctx, rig)
    return probe


def id_inventory(bpy, light):
    blocks = {int(block.as_pointer()): block for block in bpy.data.user_map()}
    blocks.update((int(a.as_pointer()), a) for a in bpy.data.actions)
    return {str(key): light.reference(block) for key, block in blocks.items()}


def guard(ctx, rig, package, bpy, refresh, light, verifier, probe, before, pair, *, pose_fake_user):
    probe.guard_old(ctx, 'original_closed_pre_save', attach_boundary=True, full_motions=True)
    require(probe.old_state(ctx)['derived_feedback'] == probe.old['derived_feedback'], 'Original row/status/selection feedback changed.')
    probe.guard_assets(ctx, 'original_closed_pre_save')
    require(package.unity_animation_original_inputs.current(rig) is None, 'Close the exact owned input session before protecting/saving.')
    source, custom = pair['source_action'], pair['custom_action']
    additions = {str(int(a.as_pointer())): light.reference(a) for a in (source, custom)}
    require(len(additions) == 2 and not set(additions) & set(before['IDs']), 'Only two genuinely new Controls Actions are admitted.')
    require(id_inventory(bpy, light) == {**before['IDs'], **additions}, 'Unexpected native ID addition, removal or replacement.')
    rows = refresh.action_contents(bpy, light, package.animation_worklist_fingerprint)
    originals = [row for row in rows if str(row['identity']['native_pointer']) in before['IDs']]
    require(originals == before['actions'] and len(bpy.data.actions) == 13, 'An original Action/slot/full content/property changed.')
    current_light = light.snapshot(ctx, rig, bpy, package.unity_animation)
    raw = current_light['original_MainRig_session_and_rawRest']
    require(raw['known'] is True and raw['value']['rig_properties'].pop(package.unity_animation_original_inputs.PAIR_KEY, None)
            == light.reference(source), 'The sole new Rig property must identify the exact readonly Controls Source.')
    current_light['actions'] = [row for row in current_light['actions']
        if str(row['identity']['native_pointer']) in before['IDs']]
    require(current_light == before['light'], 'Original Rig/Rest/NLA/pose/clock/rows/skin/context light data changed.')
    require(verifier.scene_capture() == before['scenes'] and verifier.wm_capture(package) == before['wm']
            and verifier.native_context() == before['context'] and verifier.native_pose_channels() == before['pose'],
            'Original Scene/WM/context/live pose was not exactly restored.')
    fake_flags = {str(int(a.as_pointer())): bool(a.use_fake_user) for a in bpy.data.actions
        if str(int(a.as_pointer())) in before['fake_flags']}
    expected = dict(before['fake_flags']); expected[before['Pose_pointer']] = pose_fake_user
    require(fake_flags == expected and pose_digest(pose_content(before['Pose'])) == POSE_CONTENT_SHA,
            'Only the authenticated existing Pose fake-user flag may change; its complete content must remain exact.')
    return {'all_original_Action_count': 11, 'new_Control_Action_count': 2,
        'full_original_Action_contents_known': True, 'native_ID_inventory_exact_except_two_Control_Actions': True,
        'old_rows_header_status_Source_Custom_slots_full_contents_preserved': True,
        'original_live_pose_context_NLA_clock_restored': True,
        'observed_original_assets_Rest_colors_groups_widgets_modifiers_preserved': True,
        'derived_geometry_or_world_equivalence_claimed': False}


def run(*, expected_pid, external_process_filetime, authorization_token, external_authorization_confirmed,
        script_sha256, output_root, protected_artist_sha256,
        clone_report, clone_report_sha256, clone_exit_receipt, clone_exit_receipt_sha256,
        refresh_receipt, refresh_receipt_sha256, package_manifest, package_manifest_sha256):
    """Call only after Root's fresh authorization in the existing original process."""
    require(type(expected_pid) is int and os.getpid() == expected_pid
            and type(external_process_filetime) is int and 0 < external_process_filetime < 2 ** 64
            and external_authorization_confirmed is True and isinstance(authorization_token, str) and authorization_token,
            'Root must freshly bind the actual original PID/FILETIME and authorization before run().')
    import importlib.util
    refresh_path = ROUND / 'refresh_original_artist_runtime_07727.py'
    require(hashlib.sha256(refresh_path.read_bytes()).hexdigest() == REFRESH_SHA, 'Refresh Source changed.')
    spec = importlib.util.spec_from_file_location('original20_integration_refresh_readonly', refresh_path)
    refresh = importlib.util.module_from_spec(spec); spec.loader.exec_module(refresh)
    inputs = {'source': refresh.pin(__file__, script_sha256), 'protected_artist': refresh.pin(ARTIST, protected_artist_sha256),
        'clone_source': refresh.pin(ROUND / 'validate_original20_controls.py', CLONE_SHA),
        'clone_report': refresh.pin(clone_report, clone_report_sha256),
        'clone_exit': refresh.pin(clone_exit_receipt, clone_exit_receipt_sha256),
        'refresh_source': refresh.pin(refresh_path, REFRESH_SHA),
        'refresh_receipt': refresh.pin(refresh_receipt, refresh_receipt_sha256),
        'package_manifest': refresh.pin(package_manifest, package_manifest_sha256),
        'expected_pid': expected_pid, 'external_process_filetime': external_process_filetime}
    updated, clone_dto = admitted_clone(inputs, refresh)
    manifest, _frozen = refresh.projection(inputs['package_manifest'], '0.77.27', 190)
    bpy, package = sys.modules.get('bpy'), sys.modules.get('character_designer')
    require(bpy is not None and package is not None and not bpy.app.background
            and tuple(package.bl_info['version']) == (0, 77, 27) and getattr(package, '__addon_enabled__', False)
            and Path(bpy.data.filepath).resolve() == ARTIST.resolve(), 'Use only the already-refreshed original headful X runtime.')
    installed = Path(package.__file__).resolve().parent
    leaves = {p.relative_to(installed).as_posix() for p in installed.rglob('*') if p.is_file()
        and '__pycache__' not in p.relative_to(installed).parts and p.suffix not in {'.pyc', '.pyo'}}
    require(leaves == set(manifest['files']), 'Actual deployed .27 source file set differs from the approved190 leaves.')
    for relative, expected in manifest['files'].items(): refresh.pin(installed / relative, expected)
    refresh.loaded_sources(package, installed, manifest)
    # UI intentionally lazy-loads this backend. Load only the admitted deployed
    # package module during the explicitly authorized run, without registration.
    refresh.pin(installed / 'unity_animation_original_inputs.py', BACKEND_SHA)
    backend = importlib.import_module('character_designer.unity_animation_original_inputs')
    require(refresh.pin(backend.__file__, BACKEND_SHA)['path'] == str(installed / 'unity_animation_original_inputs.py'),
            'Use the exact A7FC backend from the already-registered approved package.')
    refresh.loaded_sources(package, installed, manifest)
    light = refresh.load_source(ROUND / 'snapshot_latest_original_artist.py', LIGHT_SHA, 'artist_refresh_snapshot803')
    verifier = refresh.load_source(HISTORY / 'verify_addon_refresh_isolated.py', VERIFIER_SHA, 'artist_refresh_verifier_f220')
    oracle = refresh.load_source(HISTORY / 'validation_preservation.py', ORACLE_SHA, 'validation_preservation')
    inputs['protection_helper'] = refresh.pin(ROUND / 'original_cosha_control_round.py', PROTECTION_SHA)
    inputs['protection_inherited_helper'] = refresh.pin(ROUND / 'new_official_cosha_round.py', CFAA_SHA)
    helper = refresh.load_source(inputs['protection_helper']['path'], PROTECTION_SHA, 'original20_artist_readonly_protection7098')
    clone_helper = refresh.load_source(inputs['clone_source']['path'], CLONE_SHA, 'original20_artist_exact_input3931')
    for key, path, expected in (('light_source', ROUND / 'snapshot_latest_original_artist.py', LIGHT_SHA),
        ('preservation_oracle', HISTORY / 'validation_preservation.py', ORACLE_SHA),
        ('verifier_source', HISTORY / 'verify_addon_refresh_isolated.py', VERIFIER_SHA),
        ('Pose_writer_source', ROUND / 'preserve_original_pose_action.py', POSE_WRITER_SHA),
        ('Pose_write', ROUND / 'Pose-preservation_01/Pose_library_write_report.json', POSE_WRITE_SHA),
        ('Pose_readback', ROUND / 'Pose-preservation_02_readback/Pose_library_readback_report.json', POSE_READ_SHA)):
        inputs[key] = refresh.pin(path, expected)
    written, readback = refresh.document(inputs['Pose_write']), refresh.document(inputs['Pose_readback'])
    inputs['Pose_backup'] = exact(written['backup'], refresh)
    require(inputs['Pose_backup']['sha256'] == POSE_BACKUP_SHA and written['write_completed'] is True
            and written['original_state_unchanged'] is True and written['artist_saved'] is False
            and written['before']['pose_content_sha256'] == POSE_CONTENT_SHA
            and readback['schema'] == 'x.validation.original-Pose-library-readback/1' and readback['completed'] is True
            and readback['artist_opened_or_saved'] is False and readback['write_report'] == inputs['Pose_write']
            and readback['backup'] == inputs['Pose_backup'] and readback['content_equal'] is True
            and readback['actual_content_sha256'] == readback['expected_content_sha256'] == POSE_CONTENT_SHA,
            'The existing Pose C956/ACDD backup and independent26123 readback must remain exact.')
    destination = Path(output_root).resolve()
    require(destination != ROUND and destination.is_relative_to(ROUND) and destination.is_dir()
            and not any(destination.iterdir()), 'Use a new empty persistent ROUND integration report directory.')
    report_path = destination / 'original20_artist_integration_report.json'
    report = {'schema': 'x.validation.original20-artist-integration/1', 'completed': False,
        'native_execution_performed': True, 'source_inputs': inputs, 'pid': expected_pid,
        'external_process_filetime': external_process_filetime, 'FILETIME_verified_by_script': False,
        'authorization_token': authorization_token, 'authorization_verified_externally': True,
        'original_artist_save_attempted': False, 'original_artist_saved': False,
        'ordinary_Attach_FBX_Body_reimport_repair_or_QA_edit_performed': False,
        'new_control_publication_performed': False, 'Unity_Collect_or_Apply_verified_by_this_script': False,
        'natural_exit_inferred': False, 'phase': 'admitted_before_original_mutation'}
    refresh.write(report_path, report, first=True)
    rig = pose = probe = pair = before = None
    try:
        with light.original_context(bpy, 'Scene', 'CoshaRig') as (ctx, rig):
            refresh.idle(package, ctx, bpy)
            require(backend.PAIR_KEY not in rig, 'This is a one-time Original20 integration; do not blindly repeat an existing pair.')
            require(light.digest(light.snapshot(ctx, rig, bpy, package.unity_animation)) == updated['after_light_signature']
                    and bool(bpy.data.is_dirty) == updated['dirty_after'], 'Original state changed since the actual successful refresh.')
            actions = refresh.action_contents(bpy, light, package.animation_worklist_fingerprint)
            pose = bpy.data.actions.get('Pose')
            require(len(actions) == 11 and pose is not None and pose.library is None
                    and pose.use_fake_user is False and pose.asset_data is None
                    and pose_digest(pose_content(pose)) == POSE_CONTENT_SHA,
                    'Protect the actual current full11 including authenticated unsaved Pose; never apply saved10 qualification.')
            probe = protect(helper, package, bpy, ctx, rig, oracle, report)
            before = {'light': light.snapshot(ctx, rig, bpy, package.unity_animation), 'actions': actions,
                'IDs': id_inventory(bpy, light), 'scenes': verifier.scene_capture(), 'wm': verifier.wm_capture(package),
                'context': verifier.native_context(), 'pose': verifier.native_pose_channels(),
                'fake_flags': {str(int(a.as_pointer())): bool(a.use_fake_user) for a in bpy.data.actions},
                'Pose_pointer': str(int(pose.as_pointer())), 'Pose': pose}
            require(before['light']['original_MainRig_session_and_rawRest']['known'] is True
                    and before['light']['full_worklist']['known'] is True, 'Current original owner/Rest/rows cannot be Unknown.')
            report.update(phase='public_original_Input20_import', before_light_signature=light.digest(before['light']),
                original_Action_inventory=actions, original_Action_count=11, original_asset_baseline=probe.assets_before)
            refresh.write(report_path, report)
            session = backend.import_inputs(ctx, rig, inputs['prepared_report']['path'], inputs['prepared_report']['sha256'],
                inputs['clock_report']['path'], inputs['clock_report']['sha256'])
            pair = session['original_inputs']; clone_helper.exact_initial_twenty(package, pair)
            dto = backend.capture_inputs(ctx, session)
            require(set(dto) == refresh.RETURN_FIELDS and all(dto[k] == clone_dto[k] for k in refresh.RETURN_FIELDS
                    - {'sourceAction', 'sourceActionSlot', 'targetInputAction', 'targetInputActionSlot'}),
                    'Actual original Input20 values/clock/WorkID/packet/bindings must equal the restored clone certificate.')
            require(pair['source_uuid'] != pair['capture']['newActionId']
                    and pair['custom_action'] != pair['source_action'], 'Readonly Source20 and editable DB32 must have distinct native identity.')
            backend.close_owned(ctx, rig)
            report['pre_fake_user_guard'] = guard(ctx, rig, package, bpy, refresh, light, verifier, probe, before, pair, pose_fake_user=False)
            pose.use_fake_user = True
            report['pre_save_guard'] = guard(ctx, rig, package, bpy, refresh, light, verifier, probe, before, pair, pose_fake_user=True)
            report.update(phase='verified_before_original_save', exact_prepared_Input20_and_Return14_verified=True,
                original_Body_Source_Custom_not_edited=True, closed_persistent_PAIR_for_public_Resume=True,
                Pose_content_sha256=POSE_CONTENT_SHA, Pose_fake_user_only_expected_flag_change=True,
                controls_pair={'source': light.reference(pair['source_action']), 'source_slot': pair['source_slot'],
                    'custom': light.reference(pair['custom_action']), 'custom_slot': pair['custom_slot'],
                    'work_item_id': pair['work_item_id'], 'source_uuid': pair['source_uuid'], 'new_action_id': pair['capture']['newActionId']})
            for row in inputs.values():
                if isinstance(row, dict) and set(row) == {'path', 'sha256', 'bytes'}: exact(row, refresh)
            for relative, expected in manifest['files'].items(): refresh.pin(installed / relative, expected)
            refresh.write(report_path, report)
            report['original_artist_save_attempted'] = True
            report['phase'] = 'saving_verified_original_X'
            refresh.write(report_path, report)
            result = bpy.ops.wm.save_mainfile('EXEC_DEFAULT', filepath=str(ARTIST))
            report['save_operator_result'] = sorted(result)
            require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == ARTIST.resolve()
                    and bpy.data.is_dirty is False, 'The verified original artist save did not finish cleanly.')
            report['original_artist_saved'] = True
            report['post_save_guard'] = guard(ctx, rig, package, bpy, refresh, light, verifier, probe, before, pair, pose_fake_user=True)
            report['saved_original'] = refresh.pin(ARTIST, refresh.sha(ARTIST))
            report.update(original_artist_saved=True, completed=True, phase='completed_original_integration_saved',
                dirty_after=bool(bpy.data.is_dirty), Pose_use_fake_user_after=bool(pose.use_fake_user),
                saved_file_readonly_reopen_verification_pending=True)
    except Exception as error:
        report.update(completed=False, error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        # Restore only the just-owned active preview through its public close.
        # Never save an unverified failure or attempt another integration.
        try:
            if rig is not None:
                with light.original_context(bpy, 'Scene', 'CoshaRig') as (ctx, actual_rig):
                    require(actual_rig.as_pointer() == rig.as_pointer(), 'Failure cleanup Rig changed.')
                    backend.close_owned(ctx, rig)
                    if pose is not None and not report['original_artist_save_attempted']:
                        pose.use_fake_user = False
                    report['public_failure_close_completed'] = backend.current(rig) is None
        except Exception as cleanup_error:
            report['public_failure_cleanup_error'] = str(cleanup_error)
    finally:
        try:
            report['original_artist_disk_after'] = refresh.pin(ARTIST, refresh.sha(ARTIST))
            report['original_artist_disk_unchanged_if_no_save'] = (report['original_artist_save_attempted']
                or report['original_artist_disk_after'] == inputs['protected_artist'])
        except Exception as disk_error:
            report.update(completed=False, original_artist_disk_readback_error=str(disk_error))
        report['completed'] = bool(report['completed'] and report['original_artist_saved'])
        refresh.write(report_path, report)
    return {'completed': report['completed'], 'error': report.get('error'),
        'report': refresh.pin(report_path, refresh.sha(report_path)), 'saved_original': report.get('saved_original')}
