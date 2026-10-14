"""One read-only post-event-loop verification of the already-finished original save.

No save, import, registration, reload, close, frame seek or scene mutation.
The failed writer report stays immutable; this separate receipt records fresh proof.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

ROUND = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012')
ARTIST = Path(r'D:/Blender/Projects/Character/X/X.blend')
WRITER_REPORT = ROUND / 'original20_artist_integration_07738_04/original20_artist_integration_report.json'
WRITER_SHA = '49f92b51c3460aa1b53778a3c61702ae79523c7e450c0a6e7c62cbd7cfc0655b'
WRITER_SOURCE = ROUND / 'integrate_original20_saved_artist_07738f.py'
WRITER_SOURCE_SHA = '1065ec1118ded2ad43a9c2e10f508b3bdc69f32c6f79b6db2a7d2f45f8f7fefa'
STATUS = ROUND / 'original_saved_status_07738_01/report.json'
STATUS_SHA = 'b7289824cf27cc7c5507454627e7831e6a7f1638310bf36ce19955c92681f99d'
QUALIFIED = ROUND / 'original_artist_recovery_07738_qualified_01/qualified_recovery_report.json'
QUALIFIED_SHA = 'be4c6a331a02fdaa88c7584732e2416e34a8b52779beeece75fae9210af8ecc6'
SAVED_SHA = 'e4188e7dcbf04b3d1390040144158dccf54b65db5747006c6bead0d954bda97c'
SAVED_BYTES = 34691479
OLD_ARTIST_SHA = 'cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def load(path, expected, name):
    path = Path(path).resolve()
    require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Immutable source changed: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*, expected_pid, external_process_filetime, authorization_token,
        external_authorization_confirmed, script_sha256, output_root):
    require(external_authorization_confirmed is True and type(authorization_token) is str and authorization_token
            and type(expected_pid) is int and expected_pid == os.getpid() == 14500
            and type(external_process_filetime) is int and external_process_filetime == 134362924923204924,
            'Fresh external admission must identify the one original artist process.')
    integrate = load(WRITER_SOURCE, WRITER_SOURCE_SHA, 'original38_saved_finalizer_writer')
    refresh = load(ROUND / 'refresh_original_artist_runtime_07736.py', integrate.REFRESH_SHA, 'original38_saved_finalizer_refresh')
    inputs = {'source': refresh.pin(__file__, script_sha256),
        'writer_report': refresh.pin(WRITER_REPORT, WRITER_SHA),
        'writer_source': refresh.pin(WRITER_SOURCE, WRITER_SOURCE_SHA),
        'post_eventloop_status': refresh.pin(STATUS, STATUS_SHA),
        'qualified_recovery': refresh.pin(QUALIFIED, QUALIFIED_SHA),
        'saved_artist': refresh.pin(ARTIST, SAVED_SHA)}
    require(inputs['saved_artist']['bytes'] == SAVED_BYTES, 'The actual saved artist size changed.')
    writer, status, qualified = (refresh.document(inputs[key])
        for key in ('writer_report', 'post_eventloop_status', 'qualified_recovery'))
    require(writer['schema'] == 'x.validation.original20-artist-integration/1'
            and writer['completed'] is False and writer['phase'] == 'saving_verified_original_X'
            and writer['error'] == 'RuntimeError: The verified original artist save did not finish cleanly.'
            and writer['original_artist_save_attempted'] is True and writer['original_artist_saved'] is False
            and writer['save_operator_result'] == ['FINISHED']
            and writer['public_failure_close_completed'] is True
            and writer['source_inputs']['source'] == inputs['writer_source']
            and writer['pid'] == expected_pid and writer['external_process_filetime'] == external_process_filetime
            and writer['original_artist_disk_after'] == inputs['saved_artist'],
            'Only the exact already-finished save with its unchanged synchronous dirty-check failure may be finalized.')
    require(status['schema'] == 'x.validation.original-saved-eventloop-status/1'
            and status['writer_report']['sha256'] == WRITER_SHA
            and status['dirty_after_event_loop'] is False and status['read_only'] is True
            and status['saved_or_closed'] is False and status['actual_saved_file'] == inputs['saved_artist']
            and Path(status['filepath']).resolve() == ARTIST.resolve()
            and status['pid'] == expected_pid and status['runtime_version'] == [0, 77, 38],
            'Require the actual later clean saved-file observation, not another save attempt.')
    require(qualified['schema'] == 'x.recovery.original-registration-qualified/1'
            and qualified['completed'] is True and qualified['qualified_preservation_verified'] is True
            and qualified['strict_recovery_remains_failed'] is True
            and qualified['fresh_raw_values_exact'] is False
            and qualified['pid'] == expected_pid and qualified['external_process_filetime'] == external_process_filetime
            and writer['source_inputs']['actual_registration_recovery'] == inputs['qualified_recovery'],
            'The qualified pre-operation baseline differs.')
    immutable = {}
    historical_artist_keys = {'protected_artist', 'registration_recovery_recovery_protected_artist'}
    historical_artist_rows = {}
    for key, row in writer['source_inputs'].items():
        if isinstance(row, dict) and set(row) == {'path', 'sha256', 'bytes'}:
            if key in historical_artist_keys:
                require(Path(row['path']).resolve() == ARTIST.resolve() and row['sha256'] == OLD_ARTIST_SHA,
                        'The historical original-file identity changed.')
                historical_artist_rows[key] = row
            else:
                immutable[key] = integrate.exact(row, refresh)
    require(set(historical_artist_rows) == historical_artist_keys,
            'Both exact historical artist references must be accounted for by the sealed writer.')
    # The one artist path legitimately advanced to E418; every other input remains immutable.
    inputs['package_manifest'] = immutable['package_manifest']
    inputs['qualified_live'] = integrate.exact(qualified['fresh_live_readonly'], refresh)
    inputs['qualifier_source'] = integrate.exact(qualified['inputs']['source'], refresh)
    inputs['clone_return'] = immutable['clone_return']
    baseline = refresh.document(inputs['qualified_live'])
    qualifier = load(inputs['qualifier_source']['path'], integrate.REGISTRATION_RECOVERY_SOURCE_SHA,
                     'original38_saved_finalizer_typed')
    same = lambda a, b: qualifier.encoded(a) == qualifier.encoded(b)
    require(writer['fresh_qualified_full_before_mutation_verified'] is True
            and writer['current_qualified_light_raw_Scene_WM_context_pose_ID_users_and_flags_exact'] is True
            and writer['qualified_registration_recovery_verified'] is True
            and writer['strict_recovery_remains_failed'] is True
            and writer['recovery_strict_full_capture_exact'] is False and writer['recovery_strict_raw_capture_exact'] is False
            and writer['unknown_pre_failure_WM_or_Undo_preservation_claimed'] is False
            and writer['exact_prepared_Input20_and_Return14_verified'] is True
            and writer['original_Body_Source_Custom_not_edited'] is True
            and writer['closed_persistent_PAIR_for_public_Resume'] is True,
            'The actual integration pre-save admission must remain complete.')
    pre = writer['pre_save_guard']
    proof_keys = ('full_original_Action_contents_known', 'native_ID_inventory_exact_except_two_Control_Actions',
        'old_rows_header_status_Source_Custom_slots_full_contents_preserved',
        'original_live_pose_context_NLA_clock_restored', 'observed_original_assets_Rest_colors_groups_widgets_modifiers_preserved')
    require(pre['all_original_Action_count'] == writer['original_Action_count'] == 11
            and pre['new_Control_Action_count'] == 2 and pre['full_motion_proof_provider'] == 'same_boundary_action_contents'
            and all(pre[key] is True for key in proof_keys), 'The writer never reached complete pre-save protection.')
    bpy, package = sys.modules.get('bpy'), sys.modules.get('character_designer')
    require(bpy is not None and package is not None and not bpy.app.background
            and tuple(package.bl_info['version']) == (0, 77, 38) and package.__addon_enabled__
            and Path(bpy.data.filepath).resolve() == ARTIST.resolve() and bpy.data.is_dirty is False,
            'Observe the same clean original file after its real save event loop; do not save or reopen it.')
    manifest, _frozen = refresh.projection(inputs['package_manifest'], '0.77.38', 190)
    installed = Path(package.__file__).resolve().parent
    for relative, expected in manifest['files'].items():
        refresh.pin(installed / relative, expected)
    refresh.loaded_sources(package, installed, manifest)
    names = ('animation_worklist', 'animation_worklist_target', 'animation_worklist_fingerprint',
        'animation_composition_weapon', 'unity_animation', 'unity_animation_rigging', 'unity_animation_original_inputs')
    for name in names:
        module = vars(package).get(name)
        require(module is not None and sys.modules.get('character_designer.' + name) is module
                and refresh.pin(module.__file__, manifest['files'][name + '.py'])['path']
                    == str((installed / (name + '.py')).resolve()),
                'Finalization only observes already-admitted helper modules; it does not load or bind a runtime module.')
    backend, native, weapon = (vars(package)[name] for name in
        ('unity_animation_original_inputs', 'unity_animation_rigging', 'animation_composition_weapon'))
    light = load(immutable['light_source']['path'], integrate.LIGHT_SHA, 'original38_saved_finalizer_light')
    verifier = load(immutable['verifier_source']['path'], integrate.VERIFIER_SHA, 'original38_saved_finalizer_verifier')
    oracle = load(immutable['preservation_oracle']['path'], integrate.ORACLE_SHA, 'validation_preservation')
    helper = load(immutable['protection_helper']['path'], integrate.PROTECTION_SHA, 'original38_saved_finalizer_protection')
    exact20 = load(immutable['validation_harness']['path'], immutable['validation_harness']['sha256'], 'original38_saved_finalizer_twenty')
    destination = Path(output_root).resolve()
    require(destination != ROUND and destination.is_relative_to(ROUND) and not destination.exists(),
            'Use one new finalization-only output directory; never overwrite writer evidence.')
    destination.mkdir()
    report_path = destination / 'original20_artist_save_finalization_report.json'
    report = {'schema': 'x.validation.original20-artist-save-finalization/1', 'completed': False,
        'phase': 'admitted_clean_saved_artist_before_full_read', 'source_inputs': inputs,
        'writer_report': inputs['writer_report'], 'writer_completed_remains_false': True,
        'historical_artist_file_references': historical_artist_rows,
        'immutable_writer_inputs': immutable, 'pid': expected_pid, 'external_process_filetime': external_process_filetime,
        'authorization_token': authorization_token, 'authorization_verified_externally': True,
        'native_execution_performed': True, 'save_or_import_or_close_or_register_performed': False,
        'frame_seek_or_scene_mutation_performed': False, 'full_geometry_and_Action_recapture_performed': True,
        'post_eventloop_clean_saved_file_verified': True,
        'original_save_verified_after_eventloop': False, 'fresh_post_save_full_guards_verified': False,
        'validation_provenance': writer['validation_provenance']}
    refresh.write(report_path, report, first=True)
    try:
        with light.original_context(bpy, 'Scene', 'CoshaRig') as (ctx, rig):
            refresh.idle(package, ctx, bpy)
            require(same(light.reference(rig), qualified['identities_after']['rig'])
                    and native.SESSION_KEY not in rig and native._REFS_KEY not in rig and weapon.RECORD not in rig
                    and backend.current(rig) is None, 'The saved original has an unexpected active native/weapon session.')
            require(not any(weapon.OWNER in row for row in bpy.data.objects)
                    and not any(weapon.OWNER in row for row in bpy.data.collections),
                    'An owned weapon display remains in the saved closed original.')
            pair = backend._pair_validate(backend._pair(rig), files=True)
            require(pair['scene'] == ctx.scene, 'The persistent closed pair belongs to another Scene.')
            exact20.exact_initial_twenty(package, pair)
            recorded = writer['controls_pair']
            for key, action, slot in (('source', pair['source_action'], pair['source_slot']),
                                      ('custom', pair['custom_action'], pair['custom_slot'])):
                require(same(light.reference(action), recorded[key]) and slot == recorded[key + '_slot'],
                        'The actual saved Controls Action/slot identity changed: ' + key)
            require(pair['work_item_id'] == recorded['work_item_id'] and pair['source_uuid'] == recorded['source_uuid']
                    and pair['capture']['newActionId'] == recorded['new_action_id'], 'Saved WorkID/Source20/DB32 identity changed.')
            pose = bpy.data.actions.get('Pose')
            pose_rows = [row for row in writer['original_Action_inventory'] if row['identity']['name'] == 'Pose'
                         and row['identity']['library'] is None]
            require(len(pose_rows) == 1 and pose is not None and pose.library is None and pose.use_fake_user is True
                    and pose.asset_data is None and same(light.reference(pose), pose_rows[0]['identity'])
                    and integrate.pose_digest(integrate.pose_content(pose)) == integrate.POSE_CONTENT_SHA,
                    'The actually restored Pose identity/content/fake user changed after save.')
            source_record = writer['Pose_recovery_source_library']
            require(writer['Pose_restored_from_exact_backup'] is True and writer['expected_recovered_ID_count'] == 2
                    and source_record['backup']['sha256'] == integrate.POSE_BACKUP_SHA,
                    'Only this actual Pose append and its source Library are admitted.')
            libraries = [row for row in bpy.data.libraries
                if int(row.as_pointer()) == source_record['identity']['native_pointer']]
            require(len(libraries) == 1 and same(integrate.pose_source_library_record(bpy, libraries[0],
                immutable['Pose_backup'], light), source_record), 'The exact approved Pose source Library changed.')
            additions = {str(int(row.as_pointer())): light.reference(row)
                         for row in (pose, libraries[0], pair['source_action'], pair['custom_action'])}
            reference_fields = ('type', 'name', 'library', 'native_pointer')
            original_ids = {str(row['native_pointer']): {key: row[key] for key in reference_fields}
                            for row in baseline['all_IDs']}
            require(len(additions) == 4 and not set(additions) & set(original_ids)
                    and same(integrate.id_inventory(bpy, light), {**original_ids, **additions}),
                    'Only the four actually authorized native IDs may differ from the qualified baseline.')
            old_fake = {str(row['native_pointer']): row['use_fake_user'] for row in baseline['all_IDs'] if row['type'] == 'Action'}
            actual_fake = {str(int(row.as_pointer())): bool(row.use_fake_user) for row in bpy.data.actions
                           if str(int(row.as_pointer())) in old_fake}
            require(same(actual_fake, old_fake), 'An original Action fake-user flag changed.')
            # Exactly one fresh complete Action/slot scan for this full post-save proof.
            actions = refresh.action_contents(bpy, light, package.animation_worklist_fingerprint)
            new_action_ptrs = {int(pair['source_action'].as_pointer()), int(pair['custom_action'].as_pointer())}
            originals = [row for row in actions if row['identity']['native_pointer'] not in new_action_ptrs]
            require(len(actions) == 13 and len(originals) == 11
                    and same(verifier.public(originals), writer['original_Action_inventory']),
                    'An original or restored Action/slot/full content/property changed after save.')
            probe = integrate.protect(helper, package, bpy, ctx, rig, oracle, report)
            require(same(verifier.public(probe.assets_before), writer['original_asset_baseline']),
                    'Current complete assets/modifiers/colors/groups/widgets/geometry differ from the actual pre-save baseline.')
            fresh_light = light.snapshot(ctx, rig, bpy, package.unity_animation)
            require(fresh_light['original_MainRig_session_and_rawRest']['known'] is True,
                    'Current original Rig state is Unknown.')
            projected_light = copy.deepcopy(fresh_light)
            actual_pair_ref = projected_light['original_MainRig_session_and_rawRest']['value']['rig_properties'].pop(backend.PAIR_KEY, None)
            require(same(actual_pair_ref, light.reference(pair['source_action'])), 'The sole added Rig property must be its exact Source20 reference.')
            authorized_actions = {int(pose.as_pointer()), *new_action_ptrs}
            require(len(authorized_actions) == 3
                    and {row['identity']['native_pointer'] for row in projected_light['actions']
                         if row['identity']['native_pointer'] in authorized_actions} == authorized_actions,
                    'The exact three authorized Actions are not the observed added action set.')
            projected_light['actions'] = [row for row in projected_light['actions']
                if row['identity']['native_pointer'] not in authorized_actions]
            require(same(verifier.public(projected_light), baseline['light']),
                    'Current light state differs beyond exactly Pose, the two Controls Actions and the owned PAIR property.')
            domains = {'scenes': verifier.scene_capture(), 'wm': verifier.wm_capture(package),
                       'context': verifier.native_context(), 'pose': verifier.native_pose_channels()}
            for key, value in domains.items():
                require(same(verifier.public(value), baseline[key]), 'Current ' + key + ' changed after the verified save.')
            continuation = sys.modules.get('x_original_runtime_recovery_07738_03')
            require(continuation is not None and continuation.ACTIVE is not None,
                    'The original readonly raw observer is no longer retained.')
            prior = continuation.ACTIVE
            require(refresh.pin(continuation.__file__, qualifier.CONTINUATION_SHA)
                    == immutable['registration_recovery_strict_recovery_source']
                    and refresh.pin(prior.__file__, qualifier.VERIFIER_SHA)
                    == immutable['registration_recovery_strict_verifier_source'], 'The original raw observer source changed.')
            raw = prior.corrected_raw_snapshot(bpy, prior.STATE['observed'])
            projected_raw = copy.deepcopy(raw)
            rig_raw = projected_raw['object_custom_properties'][str(int(rig.as_pointer()))]
            expected_raw_ref = prior.STATE['observed']['plain'](pair['source_action'])
            require(same(rig_raw.pop(backend.PAIR_KEY, None), expected_raw_ref), 'Raw Rig PAIR is not the exact admitted Source20 reference.')
            for pointer in authorized_actions:
                require(str(pointer) in projected_raw['Action_custom_properties'], 'An authorized Action is missing its raw property witness.')
                del projected_raw['Action_custom_properties'][str(pointer)]
            require(same(verifier.public(projected_raw), baseline['raw']),
                    'Current raw Scene/WM/Object/Action properties changed beyond the exact admitted additions.')
            samples = [{'time': frame['time'], 'controls': native._sample(
                {'input_action': pair['custom_action'], 'input_slot': pair['custom_slot'], 'capture': pair['capture']}, frame['time'])}
                for frame in pair['capture']['frames']]
            dto = backend.contract.build_export(pair['capture'], samples, source_packet_sha256=pair['packet']['sha256'],
                work_item_id=pair['work_item_id'], new_action_id=pair['capture']['newActionId'],
                source_action=pair['source_action'].name, source_action_slot=pair['source_slot'],
                target_input_action=pair['custom_action'].name, target_input_action_slot=pair['custom_slot'])
            clone_dto = refresh.document(inputs['clone_return'])
            require(set(dto) == refresh.RETURN_FIELDS and all(same(dto[key], clone_dto[key]) for key in refresh.RETURN_FIELDS
                - {'sourceAction', 'sourceActionSlot', 'targetInputAction', 'targetInputActionSlot'}),
                'The actual closed saved pair does not reproduce the exact BF59 Return14 contract.')
            require(backend.current(rig) is None and bpy.data.is_dirty is False
                    and Path(bpy.data.filepath).resolve() == ARTIST.resolve(),
                    'Readonly post-save validation must finish on the same clean original with no active session.')
            fresh = {'assets': verifier.public(probe.assets_before), 'actions': verifier.public(actions),
                'light': verifier.public(fresh_light), 'projected_light': verifier.public(projected_light),
                'domains': verifier.public(domains), 'raw': verifier.public(raw),
                'projected_raw': verifier.public(projected_raw), 'native_IDs': integrate.id_inventory(bpy, light),
                'old_Action_fake_user': actual_fake, 'Pose_fake_user': bool(pose.use_fake_user), 'Return14': dto}
            fresh_path = destination / 'fresh_post_save_protection.json'
            refresh.write(fresh_path, fresh, first=True)
            report['fresh_post_save_capture'] = refresh.pin(fresh_path, refresh.sha(fresh_path))
            report['post_save_guard'] = {'all_original_Action_count': 11, 'new_Control_Action_count': 2,
                'full_motion_proof_provider': 'same_boundary_action_contents',
                **{key: True for key in proof_keys}, 'derived_geometry_or_world_equivalence_claimed': False}
            for row in immutable.values():
                integrate.exact(row, refresh)
            for row in inputs.values():
                integrate.exact(row, refresh)
            report.update(completed=True, phase='completed_original_save_finalized_readonly',
                original_save_verified_after_eventloop=True, fresh_post_save_full_guards_verified=True,
                full_original_11_Actions_and_assets_exact=True,
                closed_pair_twenty_channels_and_BF59_Return14_exact=True,
                projected_light_raw_Scene_WM_context_pose_exact=True,
                native_IDs_exact_except_authorized_three_Actions_and_source_Library=True,
                old_Action_fake_users_preserved=True, owned_weapon_display_absence_verified=True,
                saved_original=refresh.pin(ARTIST, SAVED_SHA), original_artist_disk_after=refresh.pin(ARTIST, SAVED_SHA),
                dirty_after=False, Pose_use_fake_user_after=True,
                saved_file_readonly_reopen_verification_pending=True)
    except Exception as error:
        report.update(completed=False, phase='readonly_save_finalization_failed',
                      error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
    finally:
        report['dirty_after_readonly_check'] = bool(bpy.data.is_dirty)
        try:
            report['original_artist_disk_after'] = refresh.pin(ARTIST, SAVED_SHA)
            report['writer_report_after'] = refresh.pin(WRITER_REPORT, WRITER_SHA)
        except Exception as error:
            report.update(completed=False, final_pin_error=str(error))
        report['completed'] = bool(report['completed'] and not report['dirty_after_readonly_check'])
        refresh.write(report_path, report)
    return {'completed': report['completed'], 'error': report.get('error'),
            'report': refresh.pin(report_path, refresh.sha(report_path))}
