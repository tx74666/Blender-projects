"""Prepared Source: one owned background read of the actually saved Original20 artist.

No automatic entry. run() reads only; no save, SDK, editing, activation, frame
seek, model import, worker, publication or original-window access. A completed
actual integration report, savedX SHA and its approved .36 manifest are required.
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
INTEGRATION_SHA = 'e8bbdfbb08f7503c43bca971d1e51ca2617d3b8c198ed78ab023747e630c7dc3'


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
    integrate = load(ROUND / 'integrate_original20_saved_artist_07736.py', INTEGRATION_SHA, 'saved_original28_integrate_readonly')
    refresh = load(ROUND / 'refresh_original_artist_runtime_07736.py', integrate.REFRESH_SHA, 'saved_original28_refresh_readonly')
    inputs = {'source': refresh.pin(__file__, script_sha256),
        'integration_source': refresh.pin(ROUND / 'integrate_original20_saved_artist_07736.py', INTEGRATION_SHA),
        'integration_report': refresh.pin(integration_report, integration_report_sha256),
        'saved_artist': refresh.pin(integrate.ARTIST, saved_artist_sha256),
        'package_manifest': refresh.pin(package_manifest, package_manifest_sha256)}
    completed = refresh.document(inputs['integration_report'])
    require(completed['schema'] == 'x.validation.original20-artist-integration/1'
        and completed['completed'] is True and completed['native_execution_performed'] is True
        and completed['phase'] == 'completed_original_integration_saved'
        and completed['original_artist_save_attempted'] is True and completed['original_artist_saved'] is True
        and completed['save_operator_result'] == ['FINISHED'] and completed['dirty_after'] is False
        and completed['Pose_use_fake_user_after'] is True
        and completed['Pose_content_sha256'] == integrate.POSE_CONTENT_SHA
        and completed['closed_persistent_PAIR_for_public_Resume'] is True
        and completed['exact_prepared_Input20_and_Return14_verified'] is True
        and completed['original_Body_Source_Custom_not_edited'] is True
        and completed['source_inputs']['source'] == inputs['integration_source']
        and completed['source_inputs']['package_manifest'] == inputs['package_manifest']
        and completed['saved_original'] == completed['original_artist_disk_after'] == inputs['saved_artist']
        and completed['pid'] != expected_pid,
        'The same actual successfully saved original integration and .36 package must certify this reader.')
    proof = completed['post_save_guard']
    require(proof['all_original_Action_count'] == completed['original_Action_count'] and proof['new_Control_Action_count'] == 2
        and proof['full_motion_proof_provider'] == 'same_boundary_action_contents'
        and all(proof[k] is True for k in ('full_original_Action_contents_known',
            'native_ID_inventory_exact_except_two_Control_Actions',
            'old_rows_header_status_Source_Custom_slots_full_contents_preserved',
            'original_live_pose_context_NLA_clock_restored',
            'observed_original_assets_Rest_colors_groups_widgets_modifiers_preserved')),
        'The actual original pre/post-save protection must be complete, including any explicitly authenticated Pose recovery.')
    manifest, root = refresh.projection(inputs['package_manifest'], '0.77.36', 190)
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
        'validation_provenance': completed['validation_provenance']}
    refresh.write(report_path, report, first=True)
    try:
        package = verifier.mount(root.parent)
        require(tuple(package.bl_info['version']) == (0, 77, 36), 'Only the approved frozen .36 package may read this file.')
        package._validate_registration_integrity()
        refresh.loaded_sources(package, root, manifest)
        opened = bpy.ops.wm.open_mainfile(filepath=inputs['saved_artist']['path'], use_scripts=False, load_ui=False)
        require(opened == {'FINISHED'} and Path(bpy.data.filepath).resolve() == integrate.ARTIST.resolve(),
            'The actual saved original file did not reopen in the owned background reader.')
        report.update(phase='saved_original_reopened_readonly', open_operator_result=sorted(opened))
        refresh.write(report_path, report)
        backend = __import__('character_designer.unity_animation_original_inputs', fromlist=['unity_animation_original_inputs'])
        require(refresh.pin(backend.__file__, integrate.BACKEND_SHA)['path'] == str(root / 'unity_animation_original_inputs.py'),
            'The Original20 reader backend belongs to another candidate.')
        scene, rig = bpy.data.scenes.get('Scene'), bpy.data.objects.get('CoshaRig')
        layer = scene.view_layers.get('ViewLayer') if scene else None
        require(scene is not None and rig is not None and layer is not None and rig.type == 'ARMATURE'
            and not rig.library and not rig.data.library and scene.objects.get(rig.name) == rig
            and scene.character_designer_setup.rig == rig and layer.objects.get(rig.name) == rig
            and backend.current(rig) is None, 'The saved original Scene/MainRig or closed owner state changed.')
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
