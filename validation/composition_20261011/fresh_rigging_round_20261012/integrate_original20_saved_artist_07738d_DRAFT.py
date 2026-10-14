"""Prepared Source: gated in-process Original20 import/close and original artist save.

run() is the only entry. No automatic execution, process/SDK call, reload,
registration, model import, ordinary Attach, QA edit, worker or publication.
Actual saved-file inspection, historical asset guards and focused .36 recovery/END plus current registration-recovery receipts are mandatory.
The existing original remains open; only an actual successful postfailure registration recovery admits this operation.
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
REFRESH_SHA = 'f9c28504ce0453bfe4232dc0231fc484f18db8793dfd34302f5ec3a6edf38cc7'
BACKEND_SHA = 'f2f6e1693c7fab0cb8ffaa479a3af19f5c4392f66119844183c32a61f91b1473'
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

# Exact frozen .38 candidate and reviewed registration-recovery source.
CANDIDATE_VERSION = (0, 77, 38)
CANDIDATE_MANIFEST_SHA = '0d0678388250fca04ce53164628c9460d6d237a5664d6e14c5f79ea8b337e209'
REGISTRATION_RECOVERY_SOURCE_SHA = 'PENDING_FINAL_QUALIFIER_SOURCE_SHA256'
CLONE_MANIFEST_SHA = 'e413d8e6d66bb5a0dd676fc24b0152d1599436464981979fd12d38085daca7e4'
EXPECTED_REGISTRATION_LEAVES = {'__init__.py', 'unity_animation_rigging.py', 'skirt_wiggle.py', 'control_weight_paint.py'}
EXPECTED_RUNTIME = {
    '__init__.py': '0132dca91c92b16763c678ec326afef8c453b1e159f1e3edcdf0ad0a9de79a52',
    'unity_animation_rigging.py': '0ca35e2e44bea9ed1007bf9024cfadb50b0e6a8ada2a702a84de43f30c484cd9',
    'skirt_wiggle.py': '81b0f0c42cfb8c4d3854c81e7da4a351d47e42b18929467d3e4864982bb13c25',
    'control_weight_paint.py': 'efbaf8227830b48c5744f1c024d0240c147cdc612612a72810eb60b2c01748bc'}


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
    # The immutable .36 admission keeps its exact E413 lineage. Candidate .38
    # registration cleanup is admitted separately; no old result is relabelled.
    inputs['clone_package_manifest'] = refresh.pin(ROUND / 'package_c1e59f7f/python_projection.json', CLONE_MANIFEST_SHA)
    require(inputs['package_manifest']['sha256'] == CANDIDATE_MANIFEST_SHA,
            'Bind the actual reviewed frozen candidate; prepared manifests cannot pass.')
    candidate, prior = refresh.document(inputs['package_manifest']), refresh.document(inputs['clone_package_manifest'])
    require(candidate['version'] == '.'.join(map(str, CANDIDATE_VERSION)) and len(candidate['files']) == 190
            and set(candidate['files']) == set(prior['files'])
            and {name for name in prior['files'] if candidate['files'][name] != prior['files'][name]}
                == EXPECTED_REGISTRATION_LEAVES
            and all(candidate['files'][name] == digest for name, digest in EXPECTED_RUNTIME.items()),
            'Candidate differs from the exact reviewed registration and failed-initialization cleanup scope.')
    admitted = refresh.admit_recovery_validation(source=inputs['clone_source'],
        report=inputs['clone_report'], exit_receipt=inputs['clone_exit'],
        package_manifest=inputs['clone_package_manifest'], snapshot_receipt=inputs['snapshot_receipt'],
        protected_artist=inputs['protected_artist'])
    inputs.update(admitted['pins'])
    admitted['evidence']['candidate_registration_scope'] = {
        'candidate_runtime': '.'.join(map(str, CANDIDATE_VERSION)),
        'candidate_manifest': inputs['package_manifest'],
        'inherited_actual_runtime': '0.77.36',
        'changed_manifest_leaves': sorted(EXPECTED_REGISTRATION_LEAVES),
        'other_186_manifest_leaves_exact': True,
        'unchanged_Gun_Body_numeric_and_Close_proof_reused': True,
        'current_candidate_Gun_Body_rerun_claimed': False,
        'current_registration_recovery_must_be_admitted_separately': True}
    return admitted['snapshot'], admitted['dto'], admitted['evidence']


def admit_registration_recovery(inputs, refresh, receipt_path, receipt_sha256):
    # Replay the frozen four-path qualification; the strict receipt stays failed.
    inputs['actual_registration_recovery'] = refresh.pin(receipt_path, receipt_sha256)
    recovered = refresh.document(inputs['actual_registration_recovery'])
    require(recovered['schema'] == 'x.recovery.original-registration-qualified/1'
            and recovered['completed'] is True
            and recovered['phase'] == 'completed_qualified_recovery_readonly'
            and recovered['registered_candidate_version'] == list(CANDIDATE_VERSION)
            and recovered['pid'] == inputs['expected_pid']
            and recovered['external_process_filetime'] == inputs['external_process_filetime']
            and all(recovered[key] is True for key in ('qualified_preservation_verified',
                'fresh_live_read_scope_exact', 'natural_registration_timer_completed_once',
                'Forearm_lifecycle_settled', 'input_files_unchanged', 'native_identities_exact',
                'original_disk_unchanged', 'strict_recovery_remains_failed'))
            and all(recovered[key] is False for key in ('fresh_full_postfailure_preservation_verified',
                'fresh_raw_values_exact', 'unknown_pre_failure_WM_or_Undo_preservation_claimed',
                'file_reload_or_save_performed', 'runtime_registration_or_scene_mutation_performed',
                'live_full_asset_or_Action_content_recapture_performed')),
            'Require actual same-process qualified recovery; no strict failure may be promoted to exact preservation.')
    recovered_inputs = {key: exact(row, refresh) for key, row in recovered['inputs'].items()}
    require(recovered_inputs['source']['sha256'] == REGISTRATION_RECOVERY_SOURCE_SHA
            and recovered_inputs['recovery_package_manifest'] == inputs['package_manifest']
            and recovered_inputs['recovery_old_manifest'] == inputs['clone_package_manifest']
            and recovered_inputs['recovery_protected_artist'] == inputs['protected_artist'],
            'Qualified recovery source, old/current package or original disk differs.')
    for key, row in recovered_inputs.items():
        inputs['registration_recovery_' + key] = row
    inputs['actual_registration_recovery_source'] = recovered_inputs['source']
    qualifier = refresh.load_source(recovered_inputs['source']['path'], REGISTRATION_RECOVERY_SOURCE_SHA,
                                    'original38_qualified_recovery_admission')
    require(recovered_inputs['strict_recovery_report']['sha256'] == qualifier.STRICT_SHA
            and recovered_inputs['strict_recovery_source']['sha256'] == qualifier.CONTINUATION_SHA
            and recovered_inputs['strict_verifier_source']['sha256'] == qualifier.VERIFIER_SHA
            and recovered_inputs['recovery_failed_refresh_receipt']['sha256'] == qualifier.F9_SHA,
            'The qualified recovery must replay the fixed actual strict failure and its exact predecessor sources.')
    strict = refresh.document(recovered_inputs['strict_recovery_report'])
    require(strict['schema'] == 'x.recovery.original-registration/1' and strict['completed'] is False
            and strict['phase'] == 'candidate_verification_failed'
            and strict['error'] == 'RuntimeError: Original protected assets changed during refresh.'
            and strict['pid'] == inputs['expected_pid']
            and strict['external_process_filetime'] == inputs['external_process_filetime']
            and strict['registered_candidate_version'] == list(CANDIDATE_VERSION)
            and all(strict[key] is True for key in ('exact_original36_cleanup_completed',
                'temporary_root_removed', 'standard_enable_returned', 'continuation_of_actual_partial_cleanup',
                'current_precleanup_baseline_exact_before_continuation', 'known_owned_timers_idle_before_cleanup',
                'weight_paint_inactive_before_cleanup'))
            and strict['before_baseline_replaced'] is False
            and strict['file_reload_or_save_performed'] is False
            and strict['unknown_pre_failure_WM_or_Undo_preservation_claimed'] is False
            and strict['old_registered_pointer_types_exact_count'] == 14
            and strict['standard_enable_errors'] == []
            and strict['owned_RNA_classes_remaining_after_cleanup'] == [],
            'Only the actual completed cleanup/enable subproofs may be inherited from the unchanged failed strict receipt.')
    for key, row in strict['inputs'].items():
        require(exact(row, refresh) == recovered_inputs['recovery_' + key],
                'The qualified report changed strict predecessor input: ' + key)
    checkpoints = {}
    for key, expected in qualifier.SNAPSHOT_SHAS.items():
        require(recovered_inputs[key] == exact(strict[key], refresh)
                and recovered_inputs[key]['sha256'] == expected, 'The actual four preservation checkpoints changed.')
        checkpoints[key] = refresh.document(recovered_inputs[key])
    f9 = refresh.document(recovered_inputs['recovery_failed_refresh_receipt'])
    require(f9['completed'] is False and f9['phase'] == 'before_disable_07724'
            and f9['old_version'] == [0, 77, 24], 'Use the actual failed pre-F9 asset witness without relabeling it.')
    qualification = qualifier.qualify_evidence(checkpoints['fresh_full_before'], checkpoints['fresh_full_after'],
        checkpoints['fresh_raw_Scene_WM_Object_Action_before'],
        checkpoints['fresh_raw_Scene_WM_Object_Action_after'], f9['before_assets'])
    require(qualifier.encoded(qualification) == qualifier.encoded(recovered['qualification']),
            'The reported typed four-path qualification differs from the complete pure replay.')
    inputs['registration_recovery_fresh_live_readonly'] = exact(recovered['fresh_live_readonly'], refresh)
    live = refresh.document(inputs['registration_recovery_fresh_live_readonly'])
    after = checkpoints['fresh_full_after']
    for key in ('light', 'scenes', 'wm', 'context', 'pose', 'all_IDs'):
        require(qualifier.encoded(live[key]) == qualifier.encoded(after[key]),
                'Qualified fresh read differs from the actual full after checkpoint: ' + key)
    require(qualifier.encoded(live['raw']) == qualifier.encoded(checkpoints['fresh_raw_Scene_WM_Object_Action_after']),
            'Qualified fresh raw read differs from the actual raw after checkpoint.')
    require(type(recovered['dirty_before']) is bool and type(recovered['dirty_after']) is bool
            and recovered['dirty_before'] == recovered['dirty_after'] == strict['dirty_before']
            and qualifier.encoded(recovered['identities_before']) == qualifier.encoded(recovered['identities_after'])
            == qualifier.encoded(strict['identities_before']),
            'Qualified preservation must keep the original dirty state and exact live native identities.')
    require(set(after['assets']) == set(f9['before_assets']) == {'CoshaRig'},
            'The authenticated whole asset domain must remain exactly the original CoshaRig.')
    return recovered, qualifier, after, f9['before_assets'], live


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
    # Keep all identity/slot RNA/properties/recovery refs. The same-boundary
    # action_contents result independently supplies the complete slot fingerprints.
    old_actions = probe.actions(full_motions=False)
    probe.old = probe.old_state(ctx)
    probe.old['actions'] = old_actions
    probe.assets_before = probe.asset_snapshot(ctx, rig)
    return probe


def id_inventory(bpy, light):
    blocks = {int(block.as_pointer()): block for block in bpy.data.user_map()}
    blocks.update((int(a.as_pointer()), a) for a in bpy.data.actions)
    return {str(key): light.reference(block) for key, block in blocks.items()}


def guard(ctx, rig, package, bpy, refresh, light, verifier, probe, before, pair, *, pose_fake_user):
    probe.guard_old(ctx, 'original_closed_pre_save', attach_boundary=True, full_motions=False)
    require(probe.old_state(ctx)['derived_feedback'] == probe.old['derived_feedback'], 'Original row/status/selection feedback changed.')
    probe.guard_assets(ctx, 'original_closed_pre_save')
    require(package.unity_animation_original_inputs.current(rig) is None, 'Close the exact owned input session before protecting/saving.')
    source, custom = pair['source_action'], pair['custom_action']
    additions = {str(int(a.as_pointer())): light.reference(a) for a in (source, custom)}
    require(len(additions) == 2 and not set(additions) & set(before['IDs']), 'Only two genuinely new Controls Actions are admitted.')
    require(id_inventory(bpy, light) == {**before['IDs'], **additions}, 'Unexpected native ID addition, removal or replacement.')
    # Exactly one actual full Action/slot fingerprint pass at this boundary.
    # guard_old above retains all of its non-motion fields and reports full_motions=False.
    rows = refresh.action_contents(bpy, light, package.animation_worklist_fingerprint)
    originals = [row for row in rows if str(row['identity']['native_pointer']) in before['IDs']]
    require(originals == before['actions'] and len(bpy.data.actions) == len(before['actions']) + 2, 'An original Action/slot/full content/property changed.')
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
            'Only the authenticated existing/recovered Pose fake-user flag may change; its complete content must remain exact.')
    return {'all_original_Action_count': len(before['actions']), 'new_Control_Action_count': 2,
        'full_original_Action_contents_known': True, 'full_motion_proof_provider': 'same_boundary_action_contents',
        'native_ID_inventory_exact_except_two_Control_Actions': True,
        'old_rows_header_status_Source_Custom_slots_full_contents_preserved': True,
        'original_live_pose_context_NLA_clock_restored': True,
        'observed_original_assets_Rest_colors_groups_widgets_modifiers_preserved': True,
        'derived_geometry_or_world_equivalence_claimed': False}


def run(*, expected_pid, external_process_filetime, authorization_token, external_authorization_confirmed,
        script_sha256, output_root, protected_artist_sha256,
        clone_report, clone_report_sha256, clone_exit_receipt, clone_exit_receipt_sha256,
        current_inspection, current_inspection_sha256, clone_source, clone_source_sha256,
        package_manifest, package_manifest_sha256,
        actual_registration_recovery_receipt, actual_registration_recovery_receipt_sha256):
    """Call only in the freshly opened, deployed original after admitted historical guards and focused .36 validation PASS."""
    require(type(expected_pid) is int and os.getpid() == expected_pid
            and type(external_process_filetime) is int and 0 < external_process_filetime < 2 ** 64
            and external_authorization_confirmed is True and isinstance(authorization_token, str) and authorization_token,
            'Root must freshly bind the actual original PID/FILETIME and authorization before run().')
    import importlib.util
    refresh_path = ROUND / 'refresh_original_artist_runtime_07736.py'
    require(hashlib.sha256(refresh_path.read_bytes()).hexdigest() == REFRESH_SHA, 'Refresh Source changed.')
    spec = importlib.util.spec_from_file_location('original20_integration_refresh_readonly', refresh_path)
    refresh = importlib.util.module_from_spec(spec); spec.loader.exec_module(refresh)
    inputs = {'source': refresh.pin(__file__, script_sha256), 'protected_artist': refresh.pin(ARTIST, protected_artist_sha256),
        'clone_source': refresh.pin(clone_source, clone_source_sha256),
        'clone_report': refresh.pin(clone_report, clone_report_sha256),
        'clone_exit': refresh.pin(clone_exit_receipt, clone_exit_receipt_sha256),
        'refresh_source': refresh.pin(refresh_path, REFRESH_SHA),
        'snapshot_receipt': refresh.pin(current_inspection, current_inspection_sha256),
        'package_manifest': refresh.pin(package_manifest, package_manifest_sha256),
        'expected_pid': expected_pid, 'external_process_filetime': external_process_filetime}
    snapshot, clone_dto, validation_provenance = admitted_clone(inputs, refresh)
    updated, qualifier, qualified_after, pre_failure_assets, qualified_live = admit_registration_recovery(inputs, refresh,
        actual_registration_recovery_receipt, actual_registration_recovery_receipt_sha256)
    manifest, _frozen = refresh.projection(inputs['package_manifest'], '0.77.38', 190)
    bpy, package = sys.modules.get('bpy'), sys.modules.get('character_designer')
    require(bpy is not None and package is not None and not bpy.app.background
            and tuple(package.bl_info['version']) == (0, 77, 38) and getattr(package, '__addon_enabled__', False)
            and Path(bpy.data.filepath).resolve() == ARTIST.resolve(), 'Use only the freshly opened original headful X with deployed .38 runtime.')
    installed = Path(package.__file__).resolve().parent
    leaves = {p.relative_to(installed).as_posix() for p in installed.rglob('*') if p.is_file()
        and '__pycache__' not in p.relative_to(installed).parts and p.suffix not in {'.pyc', '.pyo'}}
    require(leaves == set(manifest['files']), 'Actual deployed .38 source file set differs from the approved190 leaves.')
    for relative, expected in manifest['files'].items(): refresh.pin(installed / relative, expected)
    refresh.loaded_sources(package, installed, manifest)
    # UI intentionally lazy-loads this backend. Load only the admitted deployed
    # package module during the explicitly authorized run, without registration.
    refresh.pin(installed / 'unity_animation_original_inputs.py', BACKEND_SHA)
    backend = importlib.import_module('character_designer.unity_animation_original_inputs')
    require(refresh.pin(backend.__file__, BACKEND_SHA)['path'] == str(installed / 'unity_animation_original_inputs.py'),
            'Use the exact approved backend from the already-registered approved package.')
    # This module is lazy in a clean standard registration. The protection
    # helpers use its read-only ownership API before the first Input20 import.
    weapon = importlib.import_module('character_designer.animation_composition_weapon')
    require(refresh.pin(weapon.__file__, manifest['files']['animation_composition_weapon.py'])['path']
            == str((installed / 'animation_composition_weapon.py').resolve()),
            'The protection weapon module must come from the exact deployed candidate.')
    refresh.loaded_sources(package, installed, manifest)
    light = refresh.load_source(ROUND / 'snapshot_latest_original_artist.py', LIGHT_SHA, 'artist_refresh_snapshot803')
    verifier = refresh.load_source(HISTORY / 'verify_addon_refresh_isolated.py', VERIFIER_SHA, 'artist_refresh_verifier_f220')
    oracle = refresh.load_source(HISTORY / 'validation_preservation.py', ORACLE_SHA, 'validation_preservation')
    inputs['protection_helper'] = refresh.pin(ROUND / 'original_cosha_control_round.py', PROTECTION_SHA)
    inputs['protection_inherited_helper'] = refresh.pin(ROUND / 'new_official_cosha_round.py', CFAA_SHA)
    helper = refresh.load_source(inputs['protection_helper']['path'], PROTECTION_SHA, 'original20_artist_readonly_protection7098')
    clone_helper = refresh.load_source(inputs['validation_harness']['path'], inputs['validation_harness']['sha256'], 'original20_artist_exact_input_r14')
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
        'natural_exit_inferred': False, 'phase': 'admitted_before_original_mutation',
        'validation_provenance': validation_provenance,
        'preservation_baseline_scope': 'The fixed four lifecycle differences are qualified from immutable before/after evidence; current full assets and Actions are freshly compared before mutation. Pre-failure WM and Undo are not claimed exact.',
        'qualified_registration_recovery_verified': True, 'strict_recovery_remains_failed': True,
        'recovery_strict_full_capture_exact': False, 'recovery_strict_raw_capture_exact': False,
        'registration_recovery_qualification': updated['qualification'],
        'fresh_qualified_full_before_mutation_verified': False,
        'unknown_pre_failure_WM_or_Undo_preservation_claimed': False,
        'actual_registration_recovery_verified': True}
    refresh.write(report_path, report, first=True)
    rig = pose = probe = pair = before = None
    initial_pose_fake = None
    try:
        with light.original_context(bpy, 'Scene', 'CoshaRig') as (ctx, rig):
            refresh.idle(package, ctx, bpy)
            require(backend.PAIR_KEY not in rig, 'This is a one-time Original20 integration; do not blindly repeat an existing pair.')
            # Retain the original current-file protection helper independently. Its
            # .24 default adaptation preserves every actual saved Action.
            identity = {'scene': light.reference(ctx.scene), 'rig': light.reference(rig),
                'rig_data': light.reference(rig.data), 'window_manager': light.reference(ctx.window_manager),
                'window': {'native_pointer': int(ctx.window.as_pointer())},
                'view_layer': {'name': ctx.view_layer.name, 'native_pointer': int(ctx.view_layer.as_pointer())}}
            require(identity == updated['identities_after'], 'The postfailure recovered original identity changed.')
            require(light.digest(light.snapshot(ctx, rig, bpy, package.unity_animation))
                    == updated['after_light_signature']
                    and bool(bpy.data.is_dirty) == updated['dirty_after'],
                    'User/live state changed after actual postfailure recovery; preserve it and re-admit before import.')
            disk_probe = clone_helper.protection(helper, package, bpy, ctx, rig, snapshot, oracle, report)
            disk_probe.assets_before = disk_probe.asset_snapshot(ctx, rig)
            actions_disk = refresh.action_contents(bpy, light, package.animation_worklist_fingerprint)
            disk_ids = id_inventory(bpy, light)
            disk_light = light.snapshot(ctx, rig, bpy, package.unity_animation)
            disk_scene, disk_wm = verifier.scene_capture(), verifier.wm_capture(package)
            disk_context, disk_pose = verifier.native_context(), verifier.native_pose_channels()
            disk_fake = {str(int(a.as_pointer())): bool(a.use_fake_user) for a in bpy.data.actions}
            # Reuse this existing full capture: no second geometry or Action scan.
            # The original protection adds six fields to the unchanged oracle's
            # complete nine-field asset snapshot; all extra fields remain guarded.
            base_asset_fields = {'sha256', 'component_sha256', 'raw_additional_component_sha256',
                'protected_preview_sha256', 'protected_preview_component_sha256',
                'runtime_derived_display', 'runtime_generated_outputs', 'counts', 'skin_mesh_summary'}
            require(set(qualified_after['assets']['CoshaRig']) == base_asset_fields
                    and set(pre_failure_assets['CoshaRig']) == base_asset_fields
                    and base_asset_fields <= set(disk_probe.assets_before),
                    'The complete authenticated asset schema changed; do not ignore unknown or missing fields.')
            fresh_base_assets = verifier.public({key: disk_probe.assets_before[key] for key in base_asset_fields})
            require(qualifier.encoded(fresh_base_assets) == qualifier.encoded(qualified_after['assets']['CoshaRig'])
                    == qualifier.encoded(pre_failure_assets['CoshaRig']),
                    'Current full geometry/assets differ from the qualified after checkpoint or entire pre-F9 asset tree.')
            require(qualifier.encoded(verifier.public(actions_disk)) == qualifier.encoded(qualified_after['actions']),
                    'Current complete Action/slot content differs from the actual qualified after checkpoint.')
            fresh_domains = {'light': disk_light, 'scenes': disk_scene, 'wm': disk_wm,
                'context': disk_context, 'pose': disk_pose,
                'all_IDs': sorted((dict(light.reference(block), users=block.users, use_fake_user=block.use_fake_user)
                    for block in bpy.data.user_map()), key=lambda row: row['native_pointer'])}
            for key, value in fresh_domains.items():
                require(qualifier.encoded(verifier.public(value)) == qualifier.encoded(qualified_live[key]),
                        'Original live ' + key + ' changed after qualified recovery; stop before any mutation.')
            continuation = sys.modules.get('x_original_runtime_recovery_07738_03')
            require(continuation is not None and continuation.ACTIVE is not None,
                    'The authenticated original recovery context is no longer retained.')
            prior = continuation.ACTIVE
            require(refresh.pin(continuation.__file__, qualifier.CONTINUATION_SHA)
                    == inputs['registration_recovery_strict_recovery_source']
                    and refresh.pin(prior.__file__, qualifier.VERIFIER_SHA)
                    == inputs['registration_recovery_strict_verifier_source'],
                    'The retained read-only raw snapshot source or native history changed.')
            fresh_raw = prior.corrected_raw_snapshot(bpy, prior.STATE['observed'])
            require(qualifier.encoded(verifier.public(fresh_raw)) == qualifier.encoded(qualified_live['raw']),
                    'Current original raw properties differ from the qualified after checkpoint.')
            report.update(fresh_qualified_full_before_mutation_verified=True,
                current_full_asset_comparison='Existing disk_probe.asset_snapshot complete base nine fields; six additional protection fields retained.',
                current_full_Action_comparison='Existing actions_disk complete result, reused without another scan.',
                current_qualified_light_raw_Scene_WM_context_pose_ID_users_and_flags_exact=True)
            pose = bpy.data.actions.get('Pose')
            pose_restored = False
            if pose is None:
                # The historical zero-user action had a verified single-Action
                # library backup. Restore only that authenticated missing work.
                with bpy.data.libraries.load(inputs['Pose_backup']['path'], link=False) as (available, requested):
                    require(available.actions == ['Pose'], 'Pose backup must contain exactly its authenticated Action.')
                    requested.actions = ['Pose']
                pose = requested.actions[0]
                pose_restored = True
            require(pose is not None and pose.name == 'Pose' and pose.library is None and pose.asset_data is None
                    and pose_digest(pose_content(pose)) == POSE_CONTENT_SHA,
                    'Existing/restored Pose differs from the authenticated backup; preserve current work and stop before save.')
            initial_pose_fake = bool(pose.use_fake_user)
            pose_addition = {str(int(pose.as_pointer())): light.reference(pose)} if pose_restored else {}
            require(id_inventory(bpy, light) == {**disk_ids, **pose_addition}, 'Pose restoration added unexpected native data.')
            # Only library loading mutates this interval. With the existing Pose,
            # all intervening reads are synchronous and the full baseline is reusable.
            restored_actions = (refresh.action_contents(bpy, light, package.animation_worklist_fingerprint)
                                if pose_restored else actions_disk)
            require([row for row in restored_actions if str(row['identity']['native_pointer']) in disk_ids] == actions_disk,
                    'Pose recovery changed a current saved Action/slot/full content/property.')
            after_recovery = light.snapshot(ctx, rig, bpy, package.unity_animation)
            after_recovery['actions'] = [row for row in after_recovery['actions']
                if str(row['identity']['native_pointer']) in disk_ids]
            require(after_recovery == disk_light and verifier.scene_capture() == disk_scene
                    and verifier.wm_capture(package) == disk_wm and verifier.native_context() == disk_context
                    and verifier.native_pose_channels() == disk_pose
                    and {str(int(a.as_pointer())): bool(a.use_fake_user) for a in bpy.data.actions
                         if str(int(a.as_pointer())) in disk_fake} == disk_fake,
                    'Pose recovery changed current saved scene/context/pose/flags.')
            disk_probe.guard_assets(ctx, 'after_authenticated_Pose_recovery')
            report.update(Pose_restored_from_exact_backup=pose_restored,
                disk_original_Action_count=len(actions_disk), disk_original_Action_inventory=actions_disk,
                expected_recovered_Action_count=int(pose_restored))
            actions = restored_actions
            probe = protect(helper, package, bpy, ctx, rig, oracle, report)
            before = {'light': light.snapshot(ctx, rig, bpy, package.unity_animation), 'actions': actions,
                'IDs': id_inventory(bpy, light), 'scenes': verifier.scene_capture(), 'wm': verifier.wm_capture(package),
                'context': verifier.native_context(), 'pose': verifier.native_pose_channels(),
                'fake_flags': {str(int(a.as_pointer())): bool(a.use_fake_user) for a in bpy.data.actions},
                'Pose_pointer': str(int(pose.as_pointer())), 'Pose': pose}
            require(before['light']['original_MainRig_session_and_rawRest']['known'] is True
                    and before['light']['full_worklist']['known'] is True, 'Current original owner/Rest/rows cannot be Unknown.')
            report.update(phase='public_original_Input20_import', before_light_signature=light.digest(before['light']),
                original_Action_inventory=actions, original_Action_count=len(actions),
                original_worklist_baseline=before['light']['full_worklist'], original_asset_baseline=probe.assets_before)
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
            report['pre_fake_user_guard'] = guard(ctx, rig, package, bpy, refresh, light, verifier, probe, before, pair, pose_fake_user=initial_pose_fake)
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
                    if pose is not None and initial_pose_fake is not None and not report['original_artist_save_attempted']:
                        pose.use_fake_user = initial_pose_fake
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
