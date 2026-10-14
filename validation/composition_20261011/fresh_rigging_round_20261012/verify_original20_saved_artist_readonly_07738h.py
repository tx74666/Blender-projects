"""Prepared Source: one owned background read of the actually saved Original20 artist.

No automatic entry. run() reads only; no save, SDK, editing, activation, frame
seek, model import, worker, publication or original-window access. A completed
actual integration report, savedX SHA and its approved .38 manifest are required.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
from types import MethodType

ROUND = Path(__file__).resolve().parent
INTEGRATION_SHA = '1065ec1118ded2ad43a9c2e10f508b3bdc69f32c6f79b6db2a7d2f45f8f7fefa'
WRITER_REPORT_SHA = '49f92b51c3460aa1b53778a3c61702ae79523c7e450c0a6e7c62cbd7cfc0655b'
CURRENT_ARTIST_SHA = 'aea53ab4f324c7d99fdfe0ce40fc3d220b01d77b6c15671a5744e2bea86008f6'
SAVE_STATUS_SHA = 'b7289824cf27cc7c5507454627e7831e6a7f1638310bf36ce19955c92681f99d'
RESUME_RECEIPT_SHA = '09d73856ec3f2199a0fea1ef0608da9ac12669481cb47581483d1f7d52eed79a'


def load(path, expected, name):
    path = Path(path).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Read-only helper changed: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def detached_ids(value):
    """Only process-specific native pointers change on a genuine file reload."""
    if isinstance(value, dict):
        if set(value) == {'type', 'name', 'library', 'native_pointer'}:
            return {k: value[k] for k in ('type', 'name', 'library')}
        return {k: detached_ids(v) for k, v in value.items()}
    if isinstance(value, list):
        return [detached_ids(v) for v in value]
    return value


def run(*, expected_pid, external_process_filetime, external_authorization_confirmed,
        authorization_token, script_sha256, output_root, integration_report,
        integration_report_sha256, saved_artist_sha256, package_manifest, package_manifest_sha256):
    require = lambda ok, message: None if ok else (_ for _ in ()).throw(RuntimeError(message))
    require(type(expected_pid) is int and expected_pid == os.getpid()
        and type(external_process_filetime) is int and 0 < external_process_filetime < 2 ** 64
        and external_authorization_confirmed is True and isinstance(authorization_token, str) and authorization_token,
        'Root must freshly bind this one owned background reader PID/FILETIME and authorization.')
    bpy = sys.modules.get('bpy')
    require(bpy is not None and bpy.app.background and not bpy.data.filepath
        and 'character_designer' not in sys.modules, 'Use a fresh owned background process, never the original window.')
    integrate = load(ROUND / 'integrate_original20_saved_artist_07738f.py', INTEGRATION_SHA, 'saved_original28_integrate_readonly')
    refresh = load(ROUND / 'refresh_original_artist_runtime_07736.py', integrate.REFRESH_SHA, 'saved_original28_refresh_readonly')
    inputs = {'source': refresh.pin(__file__, script_sha256),
        'integration_source': refresh.pin(ROUND / 'integrate_original20_saved_artist_07738f.py', INTEGRATION_SHA),
        'integration_report': refresh.pin(integration_report, integration_report_sha256),
        'saved_artist': refresh.pin(integrate.ARTIST, saved_artist_sha256),
        'package_manifest': refresh.pin(package_manifest, package_manifest_sha256)}
    # The writer's failed synchronous dirty check is historical and immutable.
    # Its actual FINISHED save was separately observed clean after the event loop.
    # The artist was later reopened and saved again; validate that new file fully.
    completed = refresh.document(inputs['integration_report'])
    require(inputs['integration_report']['sha256'] == WRITER_REPORT_SHA
        and completed['schema'] == 'x.validation.original20-artist-integration/1'
        and completed['completed'] is False and completed['native_execution_performed'] is True
        and completed['phase'] == 'saving_verified_original_X'
        and completed['error'] == 'RuntimeError: The verified original artist save did not finish cleanly.'
        and completed['original_artist_save_attempted'] is True and completed['original_artist_saved'] is False
        and completed['save_operator_result'] == ['FINISHED']
        and completed['public_failure_close_completed'] is True
        and completed['Pose_content_sha256'] == integrate.POSE_CONTENT_SHA
        and completed['closed_persistent_PAIR_for_public_Resume'] is True
        and completed['exact_prepared_Input20_and_Return14_verified'] is True
        and completed['original_Body_Source_Custom_not_edited'] is True
        and completed['actual_registration_recovery_verified'] is True
        and completed['qualified_registration_recovery_verified'] is True
        and completed['strict_recovery_remains_failed'] is True
        and completed['recovery_strict_full_capture_exact'] is False
        and completed['recovery_strict_raw_capture_exact'] is False
        and completed['fresh_qualified_full_before_mutation_verified'] is True
        and completed['current_qualified_light_raw_Scene_WM_context_pose_ID_users_and_flags_exact'] is True
        and completed['unknown_pre_failure_WM_or_Undo_preservation_claimed'] is False
        and completed['source_inputs']['source'] == inputs['integration_source']
        and completed['source_inputs']['package_manifest'] == inputs['package_manifest']
        and completed['pid'] != expected_pid
        and completed['original_artist_disk_after']['sha256'] == 'e4188e7dcbf04b3d1390040144158dccf54b65db5747006c6bead0d954bda97c'
        and Path(completed['original_artist_disk_after']['path']).resolve() == integrate.ARTIST.resolve(),
        'Only this exact FINISHED writer history may authenticate the original intended integration.')
    inputs['save_status'] = refresh.pin(ROUND / 'original_saved_status_07738_01/report.json', SAVE_STATUS_SHA)
    status = refresh.document(inputs['save_status'])
    require(status['schema'] == 'x.validation.original-saved-eventloop-status/1'
        and status['writer_report'] == inputs['integration_report']
        and status['dirty_after_event_loop'] is False and status['read_only'] is True
        and status['saved_or_closed'] is False and status['pid'] == completed['pid']
        and status['actual_saved_file'] == completed['original_artist_disk_after'],
        'Retain the actual clean post-event-loop observation without inventing a live post-save full guard.')
    inputs['latest_saved_backup_receipt'] = refresh.pin(ROUND / 'artist_current_saved_resume_20261013_01/backup_receipt.json', RESUME_RECEIPT_SHA)
    resumed = refresh.document(inputs['latest_saved_backup_receipt'])
    require(resumed['schema'] == 'x.artist.saved-resume-backup/1'
        and resumed['original_mutated'] is False
        and inputs['saved_artist']['sha256'] == CURRENT_ARTIST_SHA
        and integrate.exact(resumed['artist'], refresh) == inputs['saved_artist']
        and resumed['prior_saved_writer_sha256'] == completed['original_artist_disk_after']['sha256']
        and resumed['current_original_pid'] == 36396
        and resumed['current_original_filetime'] == '134363465953148764',
        'Use only the exact current saved artist revision observed at this resume.')
    inputs['latest_saved_backup'] = integrate.exact(resumed['backup'], refresh)
    require(inputs['latest_saved_backup']['sha256'] == inputs['saved_artist']['sha256']
        and inputs['latest_saved_backup']['bytes'] == inputs['saved_artist']['bytes'],
        'The latest artist revision must have its separately verified persistent backup.')
    proof = completed['pre_save_guard']
    require(proof['all_original_Action_count'] == completed['original_Action_count'] and proof['new_Control_Action_count'] == 2
        and proof['full_motion_proof_provider'] == 'same_boundary_action_contents'
        and all(proof[k] is True for k in ('full_original_Action_contents_known',
            'native_ID_inventory_exact_except_two_Control_Actions',
            'old_rows_header_status_Source_Custom_slots_full_contents_preserved',
            'original_live_pose_context_NLA_clock_restored',
            'observed_original_assets_Rest_colors_groups_widgets_modifiers_preserved')),
        'The exact original writer must have passed all original preservation checks before its actual save.')
    require(inputs['package_manifest']['sha256'] == integrate.CANDIDATE_MANIFEST_SHA,
            'The reader must use the exact final reviewed candidate.')
    manifest, root = refresh.projection(inputs['package_manifest'], '0.77.38', 190)
    inputs['snapshot_receipt'] = integrate.exact(completed['source_inputs']['snapshot_receipt'], refresh)
    inputs['clone_return'] = integrate.exact(completed['source_inputs']['clone_return'], refresh)
    snapshot, clone_dto = refresh.document(inputs['snapshot_receipt']), refresh.document(inputs['clone_return'])
    require(snapshot['completed'] is True and snapshot['backup_verified'] is True
        and snapshot['metadata_preservation_verified'] is True, 'The sealed original metadata ancestry is incomplete.')
    helper = refresh.load_source(ROUND / 'original_cosha_control_round.py', integrate.PROTECTION_SHA, 'saved_original28_protection7098')
    inputs['protection_source'] = refresh.pin(ROUND / 'original_cosha_control_round.py', integrate.PROTECTION_SHA)
    inputs['protection_inherited_source'] = refresh.pin(ROUND / 'new_official_cosha_round.py', integrate.CFAA_SHA)
    oracle = refresh.load_source(integrate.HISTORY / 'validation_preservation.py', integrate.ORACLE_SHA, 'validation_preservation')
    verifier = refresh.load_source(integrate.HISTORY / 'verify_addon_refresh_isolated.py', integrate.VERIFIER_SHA, 'saved_original28_verifier_f220')
    light = refresh.load_source(ROUND / 'snapshot_latest_original_artist.py', integrate.LIGHT_SHA, 'saved_original28_light6df')
    inputs['validation_harness'] = integrate.exact(completed['source_inputs']['validation_harness'], refresh)
    exact20 = refresh.load_source(inputs['validation_harness']['path'], inputs['validation_harness']['sha256'], 'saved_original33_exact20')
    destination = Path(output_root).resolve()
    require(destination != ROUND and destination.is_relative_to(ROUND) and destination.is_dir()
        and not any(destination.iterdir()), 'Use one new empty persistent ROUND reader report directory.')
    report_path = destination / 'original20_artist_saved_readback_report.json'
    report = {'schema': 'x.validation.original20-artist-saved-readback/1', 'completed': False,
        'native_execution_performed': True, 'source_inputs': inputs, 'pid': expected_pid,
        'external_process_filetime': external_process_filetime, 'FILETIME_verified_by_script': False,
        'authorization_token': authorization_token, 'authorization_verified_externally': True,
        'original_window_accessed': False, 'original_file_saved_or_written': False,
        'edit_activation_frame_seek_worker_or_publication_performed': False,
        'natural_exit_inferred': False, 'phase': 'admitted_before_readonly_open',
        'validation_provenance': completed['validation_provenance'],
        'writer_completed_remains_false': True, 'same_process_live_post_save_full_guard_claimed': False,
        'current_saved_file_changed_after_writer': True,
        'comparison_scope': 'Full independent saved-file preservation against the original writer pre-save certificate; later artist file is kept and tested.'}
    refresh.write(report_path, report, first=True)
    try:
        package = verifier.mount(root.parent)
        require(tuple(package.bl_info['version']) == (0, 77, 38), 'Only the approved frozen .38 package may read this file.')
        package._validate_registration_integrity()
        refresh.loaded_sources(package, root, manifest)
        dependencies = integrate.load_runtime_dependencies(package, root, manifest, refresh)
        opened = bpy.ops.wm.open_mainfile(filepath=inputs['saved_artist']['path'], use_scripts=False, load_ui=False)
        require(opened == {'FINISHED'} and Path(bpy.data.filepath).resolve() == integrate.ARTIST.resolve(),
            'The actual saved original file did not reopen in the owned background reader.')
        report.update(phase='saved_original_reopened_readonly', open_operator_result=sorted(opened))
        refresh.write(report_path, report)
        backend = dependencies['unity_animation_original_inputs']
        require(manifest['files']['unity_animation_original_inputs.py'] == integrate.BACKEND_SHA,
            'The shared readonly closure must retain the approved Original20 backend.')
        scene, rig = bpy.data.scenes.get('Scene'), bpy.data.objects.get('CoshaRig')
        layer = scene.view_layers.get('ViewLayer') if scene else None
        require(scene is not None and rig is not None and layer is not None and rig.type == 'ARMATURE'
            and not rig.library and not rig.data.library and scene.objects.get(rig.name) == rig
            and scene.character_designer_setup.rig == rig and layer.objects.get(rig.name) == rig
            and backend.current(rig) is None, 'The saved original Scene/MainRig or closed owner state changed.')
        # Cheap global ownership readback also covers unlinked Objects/Collections.
        # The integration request refuses a pre-existing tagged display before run().
        weapon = dependencies['animation_composition_weapon']
        native = package.unity_animation_rigging
        remaining_owned_display = {
            'objects': [obj.name for obj in bpy.data.objects if weapon.OWNER in obj],
            'collections': [collection.name for collection in bpy.data.collections if weapon.OWNER in collection]}
        require(not remaining_owned_display['objects'] and not remaining_owned_display['collections']
            and weapon.RECORD not in rig and native.SESSION_KEY not in rig and native._REFS_KEY not in rig,
            'Owned weapon Object/Collection or active session references remain in the saved closed original; preserve for inspection.')
        report['owned_weapon_display_absence'] = {
            'scope': 'All saved bpy.data.objects and bpy.data.collections; includes unlinked IDs.',
            'owner_property': weapon.OWNER, 'remaining': remaining_owned_display,
            'Object_and_Collection_owner_tags_absent': True, 'rig_weapon_and_native_session_refs_absent': True,
            'observed_only_no_deletion_or_cleanup': True}
        with bpy.context.temp_override(scene=scene, view_layer=layer):
            ctx = bpy.context
            pair = backend._pair_validate(backend._pair(rig), files=True)
            require(pair['scene'] == scene, 'The saved pair belongs to another original Scene.')
            exact20.exact_initial_twenty(package, pair)
            recorded = completed['controls_pair']
            for key, action, slot in (('source', pair['source_action'], pair['source_slot']),
                                     ('custom', pair['custom_action'], pair['custom_slot'])):
                require(detached_ids(light.reference(action)) == detached_ids(recorded[key])
                    and slot == recorded[key + '_slot'], 'A saved Controls Action/slot identity changed: ' + key)
            require(pair['work_item_id'] == recorded['work_item_id'] and pair['source_uuid'] == recorded['source_uuid']
                and pair['capture']['newActionId'] == recorded['new_action_id'], 'Saved WorkID/Source20/DB32 identities changed.')
            actual = refresh.action_contents(bpy, light, package.animation_worklist_fingerprint)
            old = {json.dumps(detached_ids(r['identity']), sort_keys=True): detached_ids(r) for r in completed['original_Action_inventory']}
            expected_new = {json.dumps(detached_ids(light.reference(a)), sort_keys=True) for a in (pair['source_action'], pair['custom_action'])}
            observed = {json.dumps(detached_ids(r['identity']), sort_keys=True): detached_ids(r) for r in actual}
            require(len(old) == completed['original_Action_count'] and len(actual) == len(old) + 2 and set(observed) == set(old) | expected_new
                and all(observed[key] == value for key, value in old.items()), 'The saved original Action/slot/content/property inventory changed.')
            pose = bpy.data.actions.get('Pose')
            require(pose is not None and not pose.library and pose.use_fake_user is True and pose.asset_data is None
                and integrate.pose_digest(integrate.pose_content(pose)) == integrate.POSE_CONTENT_SHA,
                'The saved Pose ACDD content or required fake-user persistence changed.')
            source_record = completed['Pose_recovery_source_library']
            if completed['Pose_restored_from_exact_backup']:
                require(source_record is not None and completed['expected_recovered_ID_count'] == 2
                    and source_record['backup']['sha256'] == integrate.POSE_BACKUP_SHA,
                    'The actual Pose restore must identify its exact owned source Library.')
                inputs['Pose_source_backup'] = integrate.exact(source_record['backup'], refresh)
                source_path = Path(inputs['Pose_source_backup']['path']).resolve()
                saved_sources = [row for row in bpy.data.libraries
                    if Path(bpy.path.abspath(row.filepath)).resolve() == source_path]
                require(len(saved_sources) <= 1 and pose.library_weak_reference is None,
                    'The saved Pose source record is duplicated or its local Action acquired a weak reference.')
                observed_source = (integrate.pose_source_library_record(bpy, saved_sources[0],
                    inputs['Pose_source_backup'], light) if saved_sources else None)
                if observed_source is not None:
                    require(detached_ids(observed_source) == detached_ids(source_record),
                        'The persisted Pose source Library differs from its authenticated append record.')
                report['Pose_source_library_readback'] = {'persisted': observed_source is not None,
                    'observed': observed_source, 'scope': 'Only the exact unused Pose backup source Library may be absent after reload; all original and Action protections remain unchanged.'}
            else:
                require(source_record is None and completed['expected_recovered_ID_count'] == 0,
                    'An existing Pose must not admit a newly added source Library.')
            probe = integrate.protect(helper, package, bpy, ctx, rig, oracle, report)
            for name in ('snapshot_identity', 'snapshot_value'):
                setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))
            original_worklist = completed['original_worklist_baseline']
            require(original_worklist['known'] is True, 'Original old rows/header snapshot is Unknown.')
            expected = probe.snapshot_value(original_worklist['value']); saved = package.animation_worklist.state(ctx)
            for key in helper.HEADER_FIELDS:
                left, right = getattr(saved, key), expected[key]
                if key.endswith('_path') or key == 'model_file':
                    left = str(Path(left).resolve()) if left else left
                    right = str(Path(right).resolve()) if right else right
                require(left == right, 'A saved original Worklist header changed: ' + key)
            rows = {row['item_id']: row for row in expected['items']}
            require(set(rows) == {item.item_id for item in saved.items}, 'The saved old row identities changed.')
            for item in saved.items:
                row = probe.rna(item, exclude=helper.DERIVED_ROW)
                require(all(key in row and row[key] == value for key, value in rows[item.item_id].items()
                    if key not in helper.DERIVED_ROW), 'A saved original row/native ref/tag changed: ' + item.item_id)
            require([probe.rna(row) for row in saved.catalog] == expected['catalog'], 'The original catalog changed: catalog')
            if 'composition_catalog' in expected:
                require([probe.rna(row) for row in saved.composition_catalog] == expected['composition_catalog'],
                    'The original catalog changed: composition_catalog')
            else:
                require(snapshot['runtime_version'] == [0, 77, 24]
                    and len(saved.composition_catalog) == 0 and saved.composition_catalog_index == -1,
                    'Only the authenticated .24 missing composition catalog may use the empty/-1 candidate default.')
            if 'composition_catalog_index' in expected:
                require(saved.composition_catalog_index == expected['composition_catalog_index'], 'The original composition catalog index changed.')
            # protect() just captured this same scene; the intervening checks
            # only read metadata, so reuse that complete asset snapshot.
            assets = probe.assets_before
            prior = completed['original_asset_baseline']
            for key in ('qualified_original_component_sha256', 'raw_current_rest_sha256',
                        'original_modifiers', 'original_object_ids', 'original_object_structure'):
                require(assets[key] == prior[key], 'Saved original asset/design/native ownership changed: ' + key)
            # Closed-pair sampling only: no active SESSION is created or claimed.
            native, contract = package.unity_animation_rigging, backend.contract
            sampling_view = {'input_action': pair['custom_action'], 'input_slot': pair['custom_slot']}
            samples = [{'time': frame['time'], 'controls': native._sample(sampling_view, frame['time'])}
                for frame in pair['capture']['frames']]
            dto = contract.build_export(pair['capture'], samples, source_packet_sha256=pair['packet']['sha256'],
                work_item_id=pair['work_item_id'], new_action_id=pair['capture']['newActionId'],
                source_action=pair['source_action'].name, source_action_slot=pair['source_slot'],
                target_input_action=pair['custom_action'].name, target_input_action_slot=pair['custom_slot'])
            require(set(dto) == refresh.RETURN_FIELDS and all(dto[key] == clone_dto[key] for key in refresh.RETURN_FIELDS
                - {'sourceAction', 'sourceActionSlot', 'targetInputAction', 'targetInputActionSlot'}),
                'The saved exact20 carrier does not reproduce the genuinely restored BF59 Return values/clock/identity.')
            require(backend.current(rig) is None, 'A read-only sample unexpectedly activated the saved pair.')
            report.update(actual_saved_Action_inventory=actual, saved_Action_count=len(actual),
                original_Action_count_preserved=len(old),
                original_Actions_slots_properties_contents_preserved=True,
                Pose_content_sha256=integrate.POSE_CONTENT_SHA, Pose_fake_user_persisted=True,
                saved_PAIR_and_two_Input20_Actions_verified=True, old_Body_rows_header_catalog_preserved=True,
                observed_assets_Rest_colors_groups_widgets_modifiers_preserved=True,
                asset_readback=assets, closed_pair_actual_BF59_Return=dto,
                exact_prepared_twenty_channels_and_BF59_values_verified=True,
                derived_world_or_model_equivalence_claimed=False, transient_SKIP_SAVE_feedback_claimed_equal=False)
        for row in inputs.values(): integrate.exact(row, refresh)
        refresh.loaded_sources(package, root, manifest)
        report.update(completed=True, phase='completed_saved_original_readonly_reopen', original_disk_unchanged=True)
    except Exception as error:
        report.update(completed=False, error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
    finally:
        try:
            report['saved_original_after'] = refresh.pin(integrate.ARTIST, saved_artist_sha256)
            report['original_disk_unchanged'] = report['saved_original_after'] == inputs['saved_artist']
        except Exception as disk_error:
            report.update(completed=False, original_disk_unchanged=False, disk_error=str(disk_error))
        report['completed'] = bool(report['completed'] and report['original_disk_unchanged'])
        report['retained_handle_natural_exit_receipt_required_externally'] = True
        refresh.write(report_path, report)
    return {'completed': report['completed'], 'error': report.get('error'),
        'report': refresh.pin(report_path, refresh.sha(report_path))}
