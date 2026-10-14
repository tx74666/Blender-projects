"""SOURCE ONLY: one future in-process original-artist CD .24 -> .34 refresh.

No automatic entry point, SDK call, file open/save, Attach, frame evaluation,
Undo, repair or process launch. Root must grant this exact future original
process call after the latest SaveCopy, historical asset guards plus focused .34
Original20 validation and retained-handle END. Historical guards are not rerun claims.
"""

import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import traceback


ROUND = Path(r'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012')
HISTORY = Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011')
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
SNAPSHOT_SHA = '6df88f6e605a2a4e96eb1d3f261ed456dbe150c3e54a0d1e68f0f5aa962ff971'
VERIFIER_SHA = 'f220d2f398e16a190715fd28a9c161207bcbeaf05946ff9d516038408ba2bf32'
ORACLE_SHA = '260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d'
OLD_MANIFEST_SHA = 'c72a4b8a8b0988138f40542b1a3bb0b8313e9aaac7e4ab4bd3baa1f21c05c92b'
RETURN_FIELDS = {'schema', 'sourcePacketSha256', 'bindingsSha256', 'targetGuid', 'workItemId',
    'newActionId', 'sourceAction', 'sourceActionSlot', 'targetInputAction', 'targetInputActionSlot',
    'duration', 'sampleRate', 'loopTime', 'frames'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pin(path, expected):
    path = Path(path).resolve()
    require(re.fullmatch(r'[0-9a-f]{64}', expected or '') and path.is_file()
            and sha(path) == expected, 'Pinned input changed: ' + str(path))
    return {'path': str(path), 'sha256': expected, 'bytes': path.stat().st_size}


def document(row):
    return json.loads(Path(row['path']).read_text(encoding='utf-8-sig'))


def load_source(path, expected, name):
    row = pin(path, expected)
    existing = sys.modules.get(name)
    if existing is not None:
        require(Path(existing.__file__).resolve() == Path(row['path']), 'A helper name is already owned by another file: ' + name)
        return existing
    spec = importlib.util.spec_from_file_location(name, row['path'])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def write(path, report, *, first=False):
    with path.open('x' if first else 'w', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def projection(row, version, count):
    value = document(row)
    require(value['schema_version'] == 1 and value['module'] == 'character_designer'
            and value['version'] == version and len(value['files']) == count,
            'Use the complete approved ' + version + ' projection.')
    root = Path(value['source_root']).resolve()
    for relative, expected in value['files'].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and relative == path.relative_to(root).as_posix()
                and '__pycache__' not in path.parts and path.suffix not in {'.pyc', '.pyo'},
                'Projection contains a non-source or escaping path: ' + relative)
        pin(path, expected)
    return value, root


def admit_recovery_validation(*, source, report, exit_receipt, package_manifest,
                              snapshot_receipt, protected_artist):
    """Join actual historical asset guards with a distinct focused native run."""
    def exact(row):
        require(set(row) == {'path', 'sha256', 'bytes'} and pin(row['path'], row['sha256']) == row,
                'Required validation input pin changed.')
        return row

    for row in (source, report, exit_receipt, package_manifest, snapshot_receipt, protected_artist):
        exact(row)
    control, exited = document(report), document(exit_receipt)
    require(control['schema'] == 'x.validation.original20-recovery-gun-undo/2'
        and control['completed'] is True and control['native_execution_performed'] is True
        and control['package_manifest_version'] == '0.77.34' and control['package_manifest_file_count'] == 190
        and control['source_inputs']['source'] == source
        and all(control[k] is False for k in ('artist_opened', 'artist_written',
            'original_artist_integration_verified', 'full_original_preservation_oracle_run', 'reference_phases_run',
            'noop_Save_performed_this_run', 'noop_Undo_performed_this_run'))
        and all(control[k] is True for k in ('noop_numeric_roundtrip_reference_verified', 'load_cache_reacquired_before_current',
            'marker_Undo_cache_reacquired', 'marker_Undo_exact_BF59',
            'Gun_Undo_exact_BF59', 'Gun_Redo_exact_edited_Return', 'final_Undo_exact_BF59',
            'save_reopen_verified', 'strict14_Return_and_twenty_scalar_publication_verified',
            'no_QA_offset_remaining', 'input_files_unchanged', 'final_closed_Source_Body_motions_exact')),
        'Require the completed .34 load/marker Undo/Gun/Undo/Redo/final BF59 save-reopen run with referenced .33 numeric no-op evidence.')
    boundaries = control['motion_boundaries']
    require(isinstance(boundaries, list) and boundaries
        and set(boundaries[0]['source_body_motions']) == {'Source20', 'original_Custom_Body', 'original_Source_Body'}
        and all(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)
            for value in boundaries[0]['source_body_motions'].values())
        and all(row['Source_Body_motions_exact'] is True and row['pair_and_weights_exact'] is True
            and row['display_and_VIEW_REFS_exact'] is True and row['native_time'] == 0.
            and row['source_body_motions'] == boundaries[0]['source_body_motions']
            and row['pair_identity'] == boundaries[0]['pair_identity'] for row in boundaries)
        and any(row['boundary'] == 'reopened_BF59' and row['exact_initial_twenty_and_BF59'] is True for row in boundaries),
        'Require actual Source20/old Body motions, pair/weights and display proofs through reopened exact BF59.')
    require(Path(source['path']).is_relative_to(ROUND), 'The reviewed focused source must be in ROUND.')
    native_inputs = {key: exact(row) for key, row in control['source_inputs'].items()}
    for key, expected in (('package_manifest', package_manifest), ('snapshot_receipt', snapshot_receipt),
                          ('protected_artist', protected_artist)):
        require(native_inputs[key] == expected, 'Focused run ancestry changed: ' + key)
    historical_specs = {
        'native12_report': ('native_original20_r13_12/original20_controls_report.json', '01b1d9fa2e428e03710a304bac7c8e7174c727edf650d3228b2c08fd09c7ea5b'),
        'native12_source': ('validate_original20_latest_saved_controls_r13.py', '82522f42851abbb1e3434cbaf4a9a26fd07aaaf327b1bee58400355c5fca7172'),
        'native12_release': ('resource_release_X_NATIVE12_FAILED_GUN_VISIBILITY.json', '239d846cade89959e0ecd73979c39e968d62acb86161cc4b990d9f4a10a7e6e2'),
        'recovery': ('native_original20_r13_12/unverified_native12_quit_recovery.blend', 'd4cb2b7c8fb4667baa11e9f6cd7956076ef010f511069ea9c912a01e3d2dc5a6')}
    for key, (relative, expected) in historical_specs.items():
        require(native_inputs[key] == pin(ROUND / relative, expected), 'Historical evidence changed: ' + key)
    historical, released = document(native_inputs['native12_report']), document(native_inputs['native12_release'])
    require(historical['schema'] == 'x.validation.original20-controls-clone/1'
        and historical['completed'] is False and historical['native_execution_performed'] is True
        and historical['package_manifest_version'] == '0.77.31' and historical['package_file_count'] == 190
        and historical['source_inputs']['source'] == native_inputs['native12_source']
        and historical['Gun_Motion_UI_edit_Key_restore']['public_save_count'] == 0
        and 'Show the Right Target collection' in historical['error']
        and historical['artist_opened'] is False and historical['artist_written'] is False
        and released['report'] == native_inputs['native12_report'] and released['completed'] is False
        and released['retained_handle_natural_exit'] is True and released['native_exit_code'] == 0
        and released['owned_native_gone'] is True and released['process_termination_performed'] is False,
        'Historical Native12 remains a failed run; only its recorded earlier guards are admissible.')
    for key in ('seed', 'snapshot_receipt', 'protected_artist', 'prepared_report', 'clock_report'):
        require(historical['source_inputs'][key] == native_inputs[key], 'Recovery ancestry differs from Native12: ' + key)
    historical_guards = []
    for label in ('reference_SOURCE', 'reference_CUSTOM'):
        assets = [row for row in historical['original_asset_snapshots'] if row['boundary'] == label]
        actions = [row for row in historical['old_scanner_feedback'] if row['boundary'] == label]
        require(len(assets) == len(actions) == 1
            and assets[0]['qualified_original_changes'] == [] and assets[0]['oracle_protected_changes'] == []
            and assets[0]['original_rest_exact'] is True and assets[0]['motion_copy_proved'] is True
            and actions[0]['full_old_Action_motion_measured_this_boundary'] is True
            and actions[0]['old_row_Sync_or_batch_launch_performed'] is False,
            'Historical original asset/Rest/full old Action motion guard is incomplete: ' + label)
        historical_guards.append({'boundary': label, 'runtime': '0.77.31',
            'qualified_asset_and_Rest_guard_passed': True, 'full_old_Action_motion_measured': True,
            'raw_changes': assets[0]['raw_changes'], 'derived_geometry_not_claimed_equal': True})
    old_manifest_pin = exact(historical['source_inputs']['package_manifest'])
    require(old_manifest_pin['sha256'] == '7eec129891ef106428435b6496594e54a3d4f497c5e9fbf78349caeec2691986',
            'Use the actual Native12 .31 projection.')
    old_manifest, _ = projection(old_manifest_pin, '0.77.31', 190)
    candidate, _ = projection(package_manifest, '0.77.34', 190)
    require(set(old_manifest['files']) == set(candidate['files']), 'Historical/candidate runtime leaf domains differ.')
    changed = sorted(key for key in candidate['files'] if candidate['files'][key] != old_manifest['files'][key])
    require(set(changed) == {'__init__.py', 'unity_animation_original_inputs.py', 'unity_animation_rigging.py'},
            'Historical guard reuse requires exactly the reviewed backend dedup, Hint-order/lifecycle and version changes.')
    runtime_pins = {
        '__init__.py': '2fe699508d27317e9070e34fa489b29e5f7eedb1468d5fb5b8358b19d7683df4',
        'unity_animation_rigging.py': '77397546086392365428bcb3d87a48139aa2f36fb540e4479ec21d86109d4faf',
        'unity_animation_original_inputs.py': 'f45309023033f762ab10735ac958e14391b2807510acd92410413577aac901d9',
        'animation_original_inputs_ui.py': '38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426',
        'animation_worklist_ui.py': '24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067',
        'forearm_twist.py': '54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408'}
    require(all(candidate['files'][key] == expected for key, expected in runtime_pins.items()),
            'The candidate runtime differs from the reviewed six source pins.')
    noop_specs = {
        'noop_reference_report': ('recovery_gun_undo_07733_01/original20_recovery_gun_undo_report.json', '27a97f201811d3742e3677444a4d68b664294bc71506555b03da94e7138c49cf'),
        'noop_reference_source': ('validate_original20_recovery_gun_undo_07733.py', '6d89a1cb652a6aa564a66ab25c73312439dc887f25f44c0326a050305be50d1a'),
        'noop_reference_release': ('resource_release_X_RECOVERY_GUN_UNDO_07733_01.json', '5418b13506dc506f98ebe633a129350820538f686d2e5cfa4447ff2808ac3d9a'),
        'noop_reference_package_manifest': ('package_0fa9adfa/python_projection.json', '5b195a86a5b6d3834c7c76f02c0f83e42835e0cf7ca268556ec1e4ebf36f6640')}
    for key, (relative, expected) in noop_specs.items():
        require(native_inputs[key] == pin(ROUND / relative, expected), 'Numeric no-op evidence changed: ' + key)
    prior, prior_release = document(native_inputs['noop_reference_report']), document(native_inputs['noop_reference_release'])
    require(prior['schema'] == 'x.validation.original20-recovery-gun-undo/1'
        and prior['completed'] is False and prior['noop_numeric_roundtrip_verified'] is False
        and prior['noop_Undo_restored_exact_BF59'] is False and prior['native_execution_performed'] is True
        and prior['input_files_unchanged'] is True and prior['package_manifest_version'] == '0.77.33'
        and prior['package_manifest_file_count'] == 190 and prior['stage'] == 'noop_readback'
        and 'Undo/Redo did not reacquire' in prior['error']
        and prior['source_inputs']['source'] == native_inputs['noop_reference_source']
        and prior['source_inputs']['package_manifest'] == native_inputs['noop_reference_package_manifest']
        and prior_release['schema'] == 'x.validation.resource-release/1' and prior_release['passed'] is False
        and prior_release['report'] == native_inputs['noop_reference_report']
        and prior_release['source'] == native_inputs['noop_reference_source'] and prior_release['owned_pid'] == prior['pid']
        and prior_release['retained_handle_natural_exit'] is True and type(prior_release['native_exit_code']) is int
        and prior_release['native_exit_code'] == 0 and prior_release['owned_native_gone'] is True
        and prior_release['process_termination_performed'] is False,
        'The historical .33 overall run and Undo remain failed; its natural exit does not imply success.')
    require(all(prior['source_inputs'][key] == native_inputs[key] for key in ('harness', 'recovery', 'seed',
        'protected_artist', 'snapshot_receipt', 'prepared_report', 'clock_report', 'native12_report',
        'native12_source', 'native12_release')), 'The numeric reference belongs to a different recovery context.')
    numeric = prior['noop_save']
    require(numeric['numeric_roundtrip_gate'] is True and numeric['no_Target_or_Hint_edit_performed'] is True
        and numeric['native_time'] == 0. and numeric['frames_1_through_58_exact'] is True
        and numeric['restored_BF59_gate_remains_exact'] is True
        and numeric['gate_limits'] == {'position_max_component': 1e-5, 'hint_max_component': 1e-5, 'rotation_degrees': .001}
        and len(numeric['control_deltas']) == 2 and all(0 <= row['position_max_component'] <= 1e-5
            and 0 <= row['hint_max_component'] <= 1e-5 and 0 <= row['rotation_degrees'] <= .001
            for row in numeric['control_deltas']), 'Historical numeric evidence is absent or exceeds its original limits.')
    prior_boundaries = {row['boundary']: row for row in prior['motion_boundaries']}
    before_noop, after_noop = prior_boundaries['fixed_33_prebaseline'], prior_boundaries['no_op_saved']
    require(before_noop['exact_initial_twenty_and_BF59'] is True
        and all(row['Source_Body_motions_exact'] is True and row['pair_and_weights_exact'] is True
            and row['display_and_VIEW_REFS_exact'] is True and row['native_time'] == 0.
            for row in (before_noop, after_noop))
        and before_noop['source_body_motions'] == after_noop['source_body_motions'] == boundaries[0]['source_body_motions']
        and before_noop['pair_identity'] == after_noop['pair_identity'] == boundaries[0]['pair_identity'],
        'The referenced numeric Save must retain the same Source/Body motions and pair as this run.')
    noop_reference = {'source_version': '0.77.33', 'historical_report_completed': False,
        'historical_top_level_noop_numeric_verified': False, 'historical_noop_Undo_restored_exact_BF59': False,
        'numeric_gate_measured_true': True, 'measured_this_run': False, 'numeric_observation': numeric,
        'source_body_motions': after_noop['source_body_motions'], 'pair_identity': after_noop['pair_identity'],
        'report': native_inputs['noop_reference_report'], 'source': native_inputs['noop_reference_source'],
        'release': native_inputs['noop_reference_release']}
    require(control['noop_numeric_reference'] == noop_reference,
        'Referenced numeric evidence must preserve the actual historical failure and execution scope.')
    noop_manifest, noop_root = projection(native_inputs['noop_reference_package_manifest'], '0.77.33', 190)
    require(set(noop_manifest['files']) == set(candidate['files'])
        and {key for key in candidate['files'] if candidate['files'][key] != noop_manifest['files'][key]}
            == {'__init__.py', 'unity_animation_rigging.py'},
        'Numeric evidence reuse requires exactly version/native changes; the other 188 leaves remain exact.')
    require(native_inputs['noop_reference_native'] == pin(noop_root / 'unity_animation_rigging.py',
        noop_manifest['files']['unity_animation_rigging.py']), 'Historical numeric native source changed.')
    require(control['noop_reference_code_scope'] == {
        'other_188_manifest_leaves_exact': True, 'changed_manifest_leaves': ['__init__.py', 'unity_animation_rigging.py'],
        'changed_existing_native_functions': ['_reacquire', 'display_state', 'register', 'unregister'],
        'added_native_functions': ['_cancel_reacquire', '_deferred_reacquire'], 'removed_native_functions': [],
        'added_module_state': ['_REACQUIRE_GENERATION', '_REACQUIRE_PENDING', '_REACQUIRE_TIMER'],
        'all_other_existing_function_ASTs_exact': True,
        'numeric_functions_AST_exact': ['_apply', '_write_target', '_read_target', 'key_current', 'capture_inputs'],
        'reference_native': native_inputs['noop_reference_native'],
        'candidate_native_sha256': candidate['files']['unity_animation_rigging.py']},
        'The focused source must certify the reviewed lifecycle-only AST delta and unchanged numeric functions.')
    require(exited['schema'] in {'x.resource-release/1', 'x.validation.resource-release/1'}
        and exited['status'] == 'ACTUAL_RELEASE' and exited['passed'] is True
        and exited['retained_handle_natural_exit'] is True and type(exited['native_exit_code']) is int
        and exited['native_exit_code'] == 0 and type(exited['owned_pid']) is int
        and exited['owned_pid'] == control['pid'] and exited['owned_pid'] > 0
        and isinstance(exited['owned_process_filetime'], str) and exited['owned_process_filetime'].isdigit()
        and 0 < int(exited['owned_process_filetime']) < 2 ** 64
        and isinstance(exited['native_exited_utc'], str) and exited['native_exited_utc'].endswith(('Z', '+00:00'))
        and exited['owned_native_gone'] is True and exited['all_owned_activity_closed'] is True
        and exited['process_termination_performed'] is False and exited['source'] == source and exited['report'] == report,
        'Require the matching successful focused run retained-handle natural0/FILETIME/closed END.')
    snapshot = document(snapshot_receipt)
    seed, recovery = native_inputs['seed'], native_inputs['recovery']
    require(snapshot['schema'] == 'x.validation.latest-original-artist-snapshot/1'
        and snapshot['completed'] is True and snapshot['backup_verified'] is True
        and snapshot['metadata_preservation_verified'] is True and snapshot['runtime_version'] == [0, 77, 24]
        and snapshot['original_artist_disk_unchanged'] is True and snapshot['backup_disk_unchanged'] is True
        and snapshot['artist_opened_or_written'] is False
        and snapshot['scope'] == 'Read-only reopened byte-copy of latest user-saved disk file; no live-memory claim.'
        and snapshot['protected_artist'] == protected_artist and snapshot['backup'] == seed
        and seed['sha256'] == protected_artist['sha256'] and seed['bytes'] == protected_artist['bytes']
        and snapshot['before'] == snapshot['after'] and Path(seed['path']).is_relative_to(ROUND)
        and Path(seed['path']) != ARTIST.resolve() and seed != recovery,
        'Retain the original disk seed and distinct opened recovery; neither represents unsaved live values.')
    saved = exact(control['saved_clone'])
    require(Path(saved['path']).is_relative_to(Path(report['path']).parent)
        and saved not in (seed, recovery) and Path(saved['path']) != ARTIST.resolve(), 'Invalid final saved/reopened owned clone.')
    published = control['actual_controls_only_publication']
    require(set(published) == {'return', 'publication'}, 'Require the actual final two-file publication.')
    for row in published.values():
        exact(row)
        require(Path(row['path']).is_relative_to(Path(report['path']).parent), 'Publication escaped the focused run output.')
    dto, pub = (document(published[key]) for key in ('return', 'publication'))
    require(set(dto) == RETURN_FIELDS and pub['schema'] == 'cdesigner.controls-only-publication/1'
        and pub['completed'] is True and pub['controlChannelCount'] == 20
        and pub['returnSha256'] == published['return']['sha256'] and pub['targetInputActionId'] == dto['newActionId']
        and all(pub[k] == dto[k] for k in RETURN_FIELDS - {'schema', 'frames'})
        and all(pub[k] is True for k in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly'))
        and len(dto['frames']) == 59 and dto['sampleRate'] == 60
        and all(len(frame['controls']) == 2 and all(set(row) == {'targetPosition', 'targetRotation', 'hintPosition'}
            and len(row['targetPosition']) == len(row['hintPosition']) == 3 and len(row['targetRotation']) == 4
            for row in frame['controls']) for frame in dto['frames']), 'Final restored Input20/Return14 publication changed.')
    pins = {key: native_inputs[key] for key in ('prepared_report', 'clock_report', 'seed', 'recovery',
        'native12_report', 'native12_source', 'native12_release', 'noop_reference_report', 'noop_reference_source',
        'noop_reference_release', 'noop_reference_package_manifest', 'noop_reference_native')}
    pins.update(saved_clone=saved, clone_return=published['return'], clone_publication=published['publication'],
        validation_harness=native_inputs['harness'], inspection_collector_source=exact(snapshot['collector_source']),
        historical_package_manifest=old_manifest_pin)
    return {'snapshot': snapshot, 'dto': dto, 'pins': pins, 'evidence': {
        'historical_guards': historical_guards, 'historical_run_completed': False,
        'historical_manifest_to_candidate_changed_files': changed,
        'focused_runtime': '0.77.34', 'focused_report': report,
        'numeric_noop_reference': noop_reference, 'noop_Save_performed_this_run': False, 'noop_Undo_performed_this_run': False,
        'lifecycle_load_and_marker_Undo_measured_this_run': True,
        'focused_Source20_and_original_Body_motions_checked': True,
        'full_preservation_or_reference_rerun_claimed': False, 'unsaved_live_values_tested': False,
        'scope': 'Historical .31 SOURCE/CUSTOM asset/full old Action guards and referenced .33 numeric no-op Save (overall run and Undo remain failed), plus actual .34 load/marker Undo/Gun/Undo/Redo/final BF59 save/reopen/publication; current artist preservation is checked independently.'}}


def rollback_copy(manifest, source_root, destination):
    """Copy only the approved159 leaves; never touch113 historical cache extras."""
    require(not destination.exists() and destination.is_relative_to(ROUND), 'Rollback copy must be a new owned ROUND directory.')
    root = destination / 'character_designer'
    root.mkdir(parents=True, exist_ok=False)
    copied = {}
    for relative, expected in manifest['files'].items():
        source, target = (source_root / relative).resolve(), (root / relative).resolve()
        require(source.is_relative_to(source_root) and target.is_relative_to(root), 'Rollback copy escaped its owned roots.')
        body = source.read_bytes()
        require(hashlib.sha256(body).hexdigest() == expected, 'Rollback source changed before copy: ' + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(body)
        copied[relative] = pin(target, expected)
    for relative, expected in manifest['files'].items():
        pin(source_root / relative, expected)
        pin(root / relative, expected)
    require(len(copied) == 159 and not any(root.rglob('*.pyc')), 'Rollback copy is not the declared source-only tree.')
    return root, copied


def project_old(old, current, path, additions, *, scene=False):
    """Compare every old field; allow only exact source-proven root/row schema defaults."""
    if isinstance(old, dict):
        require(isinstance(current, dict) and set(old) <= set(current), 'Removed protected field at ' + path)
        for key in set(current) - set(old):
            value = current[key]
            if scene:
                row_path = re.search(r'\.worklist\.items\.items\[\d+\]$', path) is not None
                row_default = (row_path and (
                    key in {'workspace_path', 'workspace_identity', 'composition_json', 'composition_sha256',
                            'application_role', 'edit_scope'} and type(value) is str and value == ''
                    or key in {'b_edited', 'composition_changed', 'effective_inputs_changed', 'export_needed'}
                    and type(value) is bool and value is False))
                root_default = (re.fullmatch(r'Scenes\..+\.worklist', path) is not None and (
                    key in {'composition_workspace_path', 'composition_workspace_identity', 'composition_base_item_id'}
                    and type(value) is str and value == ''
                    or key == 'composition_catalog' and type(value) is dict and value == {'kind': 'COLLECTION', 'items': []}
                    or key == 'composition_catalog_index' and type(value) is int and value == -1))
                require(row_default or root_default,
                        'Unexpected new persistent Scene field/value: ' + path + '.' + key)
            additions.append({'path': path + '.' + key, 'value': value if type(value) in (str, bool, int, float) else '<new RNA schema>'})
        return {key: project_old(value, current[key], path + '.' + key, additions, scene=scene)
                for key, value in old.items()}
    if isinstance(old, (list, tuple)):
        require(isinstance(current, (list, tuple)) and len(old) == len(current), 'Protected collection length changed at ' + path)
        return [project_old(value, current[index], path + '[' + str(index) + ']', additions, scene=scene)
                for index, value in enumerate(old)]
    if hasattr(old, 'as_pointer'):
        require(current is not None and hasattr(current, 'as_pointer')
                and int(old.as_pointer()) == int(current.as_pointer()), 'Protected native ID pointer changed at ' + path)
    else:
        require(old == current, 'Protected value changed at ' + path)
    return old


def idle(cd, ctx, bpy):
    """Only real unregister-destructive captures block otherwise idle controls."""
    require(not bpy.app.background and ctx.window is not None
            and not ctx.screen.is_animation_playing and ctx.mode in {'OBJECT', 'POSE'}, 'Use the idle owning original headful context.')
    for obj in bpy.data.objects:
        ad = obj.animation_data
        require(not (ad and ad.use_tweak_mode) and not obj.get('character_designer_unity_animation_active')
                and not obj.get('character_designer_rigging_session_v1')
                and not obj.get('character_designer_composition_session_v1'), 'Close actual animation/Tweak/owned editing sessions before refresh: ' + obj.name)
    names = ('animation', 'animation_export', 'unity_export', 'animation_worklist_collection', 'animation_worklist_ui')
    modules = {name: sys.modules.get('character_designer.' + name) for name in names}
    require((modules['animation'] is None or modules['animation']._job is None)
            and (modules['animation_export'] is None or modules['animation_export'].active_job() is None)
            and (modules['unity_export'] is None or not modules['unity_export'].export_running())
            and (modules['animation_worklist_collection'] is None or not modules['animation_worklist_collection'].running())
            and (modules['animation_worklist_ui'] is None or modules['animation_worklist_ui']._SCAN_PENDING is None),
            'An actual cached job/scan is active; defer refresh without importing disk .27.')
    settings = cd._settings(ctx)
    require(settings is not None, 'Actual Centreline settings are unavailable.')
    require(not bpy.app.timers.is_registered(cd._live_preview_tick), 'The actual Centreline live timer is active; defer refresh.')
    for name in ('root_indices_json', 'root_edges_json', 'root_ignored_indices_json'):
        value = getattr(settings, name)
        if value:
            require(not json.loads(value), 'An actual Centreline capture would be cleared: ' + name)
    require(not settings.root_object and not settings.root_mesh and not settings.root_vertex_count
            and not settings.root_ignored_count and not settings.root_kind and not settings.root_capture_mode
            and not settings.topology_signature, 'An actual Centreline root capture would be destroyed.')
    for name in ('_LIVE_PREVIEW_INPUT_SIGNATURE', '_LIVE_PREVIEW_WORLD_POINTS', '_LIVE_PREVIEW_PATHS',
                 '_LIVE_PREVIEW_HANDLE_POINTS', '_LIVE_PREVIEW_LAYERS', '_LIVE_PREVIEW_METADATA_JSON',
                 '_LIVE_PREVIEW_SOURCE_KEY', '_LIVE_PREVIEW_TRACKED_SOURCE_KEY', '_LIVE_PREVIEW_DRAW_HANDLE'):
        require(not getattr(cd, name, None), 'An actual Centreline runtime cache would be destroyed: ' + name)
    delta = sys.modules.get('character_designer.delta_symmetry')
    require(delta is None or (not delta._CAPTURE and not delta._RUNTIME),
            'An actual Delta capture/runtime would be destroyed; defer refresh.')


def action_contents(bpy, light, fingerprint):
    rows = []
    for action in bpy.data.actions:
        slots = [{'handle': slot.handle, 'identifier': slot.identifier,
                  'target_id_type': slot.target_id_type, 'name_display': slot.name_display}
                 for slot in action.slots] if action.is_action_layered else []
        motions = {str(handle): fingerprint.fingerprint_action(action, handle)
                   for handle in ([row['handle'] for row in slots] if slots else [0])}
        require(motions and all(value['fingerprint_known'] is True for value in motions.values()),
                'An original selected-slot Action content is Unknown; stop before disable: ' + action.name)
        rows.append({'identity': light.reference(action), 'slots': slots, 'motions': motions,
                     'custom_properties': light.plain(dict(action.items()))})
    return sorted(rows, key=lambda row: row['identity']['native_pointer'])


def capture(ctx, rig, bpy, ua, cd, light, verifier, fingerprint):
    return {'light': light.snapshot(ctx, rig, bpy, ua), 'scenes': verifier.scene_capture(),
            'wm': verifier.wm_capture(cd), 'context': verifier.native_context(),
            'pose': verifier.native_pose_channels(), 'assets': verifier.assets(ua),
            'actions': action_contents(bpy, light, fingerprint),
            'all_IDs': sorted((dict(light.reference(block), users=block.users,
                                   use_fake_user=block.use_fake_user) for block in bpy.data.user_map()),
                              key=lambda row: row['native_pointer'])}


def check_capture(before, after):
    additions = []
    project_old(before['scenes'], after['scenes'], 'Scenes', additions, scene=True)
    project_old(before['wm'], after['wm'], 'WM', additions)
    # Light RNA independently includes the same new per-item fields; use the
    # strict Scene PropertyGroup comparison above, and compare every old field.
    projected_light = project_old(before['light'], after['light'], 'Light', [], scene=False)
    require(projected_light == before['light'], 'Original light inventory changed.')
    for name in ('context', 'pose', 'assets', 'actions', 'all_IDs'):
        require(before[name] == after[name], 'Original protected ' + name + ' changed during refresh.')
    return additions


def clear_cd():
    removed = sorted(name for name in tuple(sys.modules)
                     if name == 'character_designer' or name.startswith('character_designer.'))
    for name in removed:
        del sys.modules[name]
    importlib.invalidate_caches()
    return removed


def loaded_sources(cd, root, manifest):
    require(Path(cd.__file__).resolve() == root / '__init__.py', 'Runtime mounted from a different package.')
    checked = {}
    for name, module in tuple(sys.modules.items()):
        if name == 'character_designer' or name.startswith('character_designer.'):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(root), 'Loaded Character Designer module has a foreign root: ' + name)
            relative = path.relative_to(root).as_posix()
            require(relative in manifest['files'], 'Loaded module is outside the approved projection: ' + name)
            checked[name] = pin(path, manifest['files'][relative])
    return checked


def run(*, expected_pid, external_process_filetime, authorization_token,
        external_authorization_confirmed, script_sha256, output_root,
        protected_artist_sha256, latest_snapshot_receipt, latest_snapshot_receipt_sha256,
        latest_snapshot_source, latest_snapshot_source_sha256,
        clone_snapshot_receipt, clone_snapshot_receipt_sha256,
        package_manifest, package_manifest_sha256, deployed_addon_root,
        original20_report, original20_report_sha256, original20_source, original20_source_sha256,
        original20_exit_receipt, original20_exit_receipt_sha256):
    """Future one SDK caller operation; external Root PID/FILETIME/START is required."""
    require(external_authorization_confirmed is True and isinstance(authorization_token, str)
            and authorization_token.strip() and type(expected_pid) is int and expected_pid == os.getpid()
            and type(external_process_filetime) is int and external_process_filetime > 0,
            'Root must freshly verify this original PID/FILETIME and authorize this exact refresh call.')
    bpy, old = sys.modules.get('bpy'), sys.modules.get('character_designer')
    require(bpy is not None and old is not None and tuple(old.bl_info['version']) == (0, 77, 24)
            and getattr(old, '__addon_enabled__', False), 'The actual resident enabled runtime must still be .24.')
    require(Path(bpy.data.filepath).resolve() == ARTIST.resolve(), 'Use the real original X.blend; never open a clone here.')
    protected = pin(ARTIST, protected_artist_sha256)
    source = pin(__file__, script_sha256)
    latest_pin = pin(latest_snapshot_receipt, latest_snapshot_receipt_sha256)
    latest = document(latest_pin)
    live_source = pin(latest_snapshot_source, latest_snapshot_source_sha256)
    require(Path(live_source['path']).is_relative_to(ROUND), 'Use the reviewed current live SaveCopy Source in ROUND.')
    require(latest['schema'] == 'x.validation.latest-original-artist-snapshot/1'
            and latest['completed'] is True and latest['backup_verified'] is True
            and latest['original_artist_saved'] is False and latest['original_artist_disk_unchanged'] is True
            and latest['runtime_version'] == [0, 77, 24] and latest['source'] == live_source
            and latest['metadata_preservation_verified'] is True
            and latest['save_result'] == ['FINISHED']
            and latest['scope'] == 'Latest recoverable SaveCopy plus light original context/identity metadata only; full content inspection remains isolated-clone pending.'
            and latest['pid'] == expected_pid and latest['external_process_filetime'] == external_process_filetime
            and latest['protected_artist'] == protected, 'Require the actual fresh completed SaveCopy of this exact current original process.')
    backup = pin(latest['backup']['path'], latest['backup']['sha256'])
    require(backup == latest['backup'] and Path(backup['path']).is_relative_to(ROUND)
            and Path(backup['path']) != ARTIST.resolve(), 'The latest recovery backup pin is invalid.')
    # The clone tests the current saved disk byte-copy. The live SaveCopy is a
    # distinct recovery point for this process and may contain unsaved work.
    # Neither receipt is relabelled as evidence for the other's values.
    clone_snapshot_pin = pin(clone_snapshot_receipt, clone_snapshot_receipt_sha256)
    disk_snapshot = document(clone_snapshot_pin)
    require(disk_snapshot['schema'] == 'x.validation.latest-original-artist-snapshot/1'
        and disk_snapshot['completed'] is True and disk_snapshot['backup_verified'] is True
        and disk_snapshot['metadata_preservation_verified'] is True
        and disk_snapshot['runtime_version'] == [0, 77, 24]
        and disk_snapshot['source']['sha256'] == SNAPSHOT_SHA
        and disk_snapshot['scope'] == 'Read-only reopened byte-copy of latest user-saved disk file; no live-memory claim.'
        and disk_snapshot['artist_opened_or_written'] is False
        and disk_snapshot['original_artist_saved'] is False
        and disk_snapshot['original_artist_disk_unchanged'] is True
        and disk_snapshot['backup_disk_unchanged'] is True
        and disk_snapshot['protected_artist'] == protected
        and disk_snapshot['before'] == disk_snapshot['after'],
        'Require the actual unchanged current saved-disk inspection separately from the live SaveCopy.')
    clone_seed = pin(disk_snapshot['backup']['path'], disk_snapshot['backup']['sha256'])
    require(clone_seed == disk_snapshot['backup']
        and clone_seed['sha256'] == protected['sha256'] and clone_seed['bytes'] == protected['bytes']
        and Path(clone_seed['path']).is_relative_to(ROUND) and Path(clone_seed['path']) != ARTIST.resolve(),
        'The clone seed must be the actual byte-identical current saved X backup.')
    collector_source = pin(disk_snapshot['collector_source']['path'], disk_snapshot['collector_source']['sha256'])
    require(collector_source == disk_snapshot['collector_source'], 'Current saved-disk collector Source changed.')
    manifest_pin = pin(package_manifest, package_manifest_sha256)
    candidate, frozen_root = projection(manifest_pin, '0.77.34', 190)
    installed = Path(deployed_addon_root).resolve()
    require(installed == Path(old.__file__).resolve().parent and installed != frozen_root,
            'Refresh only the actual already-mounted install root after approved deployment.')
    installed_leaves = {path.relative_to(installed).as_posix() for path in installed.rglob('*')
                        if path.is_file() and '__pycache__' not in path.relative_to(installed).parts
                        and path.suffix not in {'.pyc', '.pyo'}}
    require(installed_leaves == set(candidate['files']), 'The deployed source file set is not the complete approved package; preserve and resolve extras before refresh.')
    for relative, expected in candidate['files'].items():
        pin(installed / relative, expected)
    old_pin = pin(HISTORY / 'release_projection_07724.json', OLD_MANIFEST_SHA)
    old_manifest, old_root = projection(old_pin, '0.77.24', 159)
    inputs = {'source': source, 'protected_artist': protected, 'latest_snapshot_receipt': latest_pin,
              'latest_seed': backup, 'latest_snapshot_source': live_source,
              'clone_snapshot_receipt': clone_snapshot_pin, 'clone_seed': clone_seed,
              'clone_inspection_collector_source': collector_source,
              'package_manifest': manifest_pin, 'rollback_projection': old_pin,
              'original20_report': pin(original20_report, original20_report_sha256),
              'original20_source': pin(original20_source, original20_source_sha256),
              'original20_exit_receipt': pin(original20_exit_receipt, original20_exit_receipt_sha256)}
    admission = admit_recovery_validation(source=inputs['original20_source'],
        report=inputs['original20_report'], exit_receipt=inputs['original20_exit_receipt'],
        package_manifest=manifest_pin, snapshot_receipt=clone_snapshot_pin, protected_artist=protected)
    require(admission['pins']['seed'] == clone_seed, 'The admitted historical seed differs from the saved-disk inspection.')
    inputs.update(admission['pins'])
    inputs['original20_return'] = inputs['clone_return']
    inputs['original20_publication'] = inputs['clone_publication']
    ua = sys.modules.get('character_designer.unity_animation')
    require(ua is not None and Path(ua.__file__).resolve().is_relative_to(installed), 'Use the actual already-cached artist UA module.')
    light = load_source(ROUND / 'snapshot_latest_original_artist.py', SNAPSHOT_SHA, 'artist_refresh_snapshot803')
    oracle = load_source(HISTORY / 'validation_preservation.py', ORACLE_SHA, 'validation_preservation')
    verifier = load_source(HISTORY / 'verify_addon_refresh_isolated.py', VERIFIER_SHA, 'artist_refresh_verifier_f220')
    fingerprint = load_source(old_root / 'animation_worklist_fingerprint.py', old_manifest['files']['animation_worklist_fingerprint.py'], 'artist_refresh_content_07724')
    destination = Path(output_root).resolve()
    require(destination != ROUND and destination.is_relative_to(ROUND) and destination.is_dir()
            and not any(destination.iterdir()), 'Use a fresh empty persistent ROUND refresh child.')
    receipt = destination / 'original_artist_runtime_refresh_receipt.json'
    report = {'schema': 'x.validation.original-artist-runtime-refresh/1', 'completed': False,
              'native_execution_performed': True, 'source_inputs': inputs, 'pid': expected_pid,
              'external_process_filetime': external_process_filetime, 'FILETIME_verified_by_script': False,
              'authorization_token': authorization_token, 'authorization_verified_externally': True,
              'old_version': [0, 77, 24], 'Undo_history': 'Unknown; no Undo operation or reset performed.',
              'original_artist_saved': False, 'file_opened_or_reloaded': False, 'Attach_or_readopt_performed': False,
              'Scene_or_asset_repair_performed': False, 'module_only_rollback_attempted': False,
               'Original20_acceptance': admission['evidence']['scope'],
               'validation_provenance': admission['evidence'],
               'live_preservation_scope': 'Actual full before/after Action, Scene, WM, context, pose, ID and observed asset preservation in the current process.',
               'clone_tested_unsaved_live_values': False,
               'public_UI_or_Undo_acceptance_inferred': False, 'world_model_equivalence': 'Unknown',
               'Pose_fake_user_final_save_step_performed': False}
    write(receipt, report, first=True)
    scene_name, rig_name = latest['after']['context']['scene']['name'], latest['after']['original_MainRig_session_and_rawRest']['value']['rig']['name']
    old_sys_path = list(sys.path)
    try:
        with light.original_context(bpy, scene_name, rig_name) as (ctx, rig):
            idle(old, ctx, bpy)
            # The unchanged260b oracle uses these exact lazy imports. Require
            # cached .24 dependencies, not newly deployed disk .34 code, before
            # its first original-process read. Missing modules stop pre-disable.
            oracle_dependencies = ('forearm_twist', 'bone_collections', 'limb_fk_visuals',
                                   'limb_ik', 'limb_ik_fk', 'body_original_mode')
            for name in oracle_dependencies:
                module = sys.modules.get('character_designer.' + name)
                require(module is not None and Path(module.__file__).resolve().is_relative_to(installed),
                        'Preservation requires an actual already-cached .24 dependency: ' + name)
            original_mode = sys.modules['character_designer.body_original_mode']
            if any(original_mode.active(obj) for obj in bpy.data.objects
                   if obj.type == 'ARMATURE' and obj.name in {'CoshaRig', 'CoshaRig.001'}):
                module = sys.modules.get('character_designer.forearm_original_inventory')
                require(module is not None and Path(module.__file__).resolve().is_relative_to(installed),
                        'Original-mode preservation dependency is not already cached; stop before disable.')
            require(light.digest(light.snapshot(ctx, rig, bpy, ua)) == latest['after_signature']
                    and bool(bpy.data.is_dirty) == latest['dirty_after'], 'Original state changed since its actual fresh live SaveCopy; take a new backup first.')
            before = capture(ctx, rig, bpy, ua, old, light, verifier, fingerprint)
            report['before_light_signature'] = light.digest(before['light'])
            report['before_assets'] = before['assets']
            report['Action_content_scope'] = 'Complete selected-slot content; dependency/graph Known is not inferred.'
            rollback_root, copied = rollback_copy(old_manifest, old_root, destination / 'rollback07724_source')
            report['rollback_source_leaves'] = copied
            report['phase'] = 'before_disable_07724'
            write(receipt, report)
            import addon_utils  # Blender's existing standard registration API; no candidate imported before this point.
            addon_utils.disable('character_designer', default_set=False)
            require(not getattr(old, '__addon_enabled__', False), 'The resident .24 runtime did not disable.')
            report['removed_old_module_names'] = clear_cd()
            try:
                new = verifier.mount(installed.parent)
                require(tuple(new.bl_info['version']) == (0, 77, 34), 'Registered candidate is not .34.')
                new._validate_registration_integrity()
                report['loaded_candidate_sources'] = loaded_sources(new, installed, candidate)
            except Exception as registration_error:
                report['registration_error'] = type(registration_error).__name__ + ': ' + str(registration_error)
                report['module_only_rollback_attempted'] = True
                failed = sys.modules.get('character_designer')
                if failed is not None:
                    addon_utils.disable('character_designer', default_set=False)
                    require(not getattr(failed, '__addon_enabled__', False), 'Failed candidate could not disable safely.')
                clear_cd()
                restored_runtime = verifier.mount(rollback_root.parent)
                require(tuple(restored_runtime.bl_info['version']) == (0, 77, 24), 'Rollback did not register the verified .24 copy.')
                restored = []
                for group, fields in before['wm'].items():
                    verifier.restore_only_changed_wm(getattr(ctx.window_manager, group), fields, group, restored)
                restored_ua = sys.modules['character_designer.unity_animation']
                after = capture(ctx, rig, bpy, restored_ua, restored_runtime, light, verifier, fingerprint)
                check_capture(before, after)
                report.update(module_only_rollback_verified=True, rollback_loaded_sources=loaded_sources(restored_runtime, rollback_root, old_manifest),
                              rollback_wm_fields_restored=restored, phase='registration_failed_original_state_verified')
                raise RuntimeError('Candidate registration failed; verified .24 module-only rollback completed.') from registration_error
            report['phase'] = 'candidate_registered_check_retained_scene'
            write(receipt, report)
            additions = []
            project_old(before['scenes'], verifier.scene_capture(), 'Scenes', additions, scene=True)
            restored = []
            for group, fields in before['wm'].items():
                verifier.restore_only_changed_wm(getattr(ctx.window_manager, group), fields, group, restored)
            new_ua = sys.modules['character_designer.unity_animation']
            after = capture(ctx, rig, bpy, new_ua, new, light, verifier, fingerprint)
            additions = check_capture(before, after)
            for relative, expected in candidate['files'].items():
                pin(installed / relative, expected)
            for row in inputs.values():
                pin(row['path'], row['sha256'])
            report.update(completed=True, phase='completed_refresh_only_no_Attach_or_save', new_version=[0, 77, 34],
                          wm_fields_restored=restored, new_schema_defaults=additions, after_assets=after['assets'],
                          original_Scene_rows_header_catalog_Actions_slots_assets_pose_context_preserved=True,
                          after_light_signature=light.digest(after['light']), dirty_after=bool(bpy.data.is_dirty))
    except Exception as error:
        report.update(completed=False, error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
    finally:
        # Keep the selected candidate/rollback add-on parent first; preserve all
        # prior other search entries. No external module namespace is removed.
        runtime = sys.modules.get('character_designer')
        if runtime is not None:
            parent = str(Path(runtime.__file__).resolve().parent.parent)
            sys.path[:] = [parent] + [value for value in old_sys_path if value != parent]
        try:
            report['original_artist_disk_unchanged'] = pin(ARTIST, protected_artist_sha256) == protected
        except Exception as error:
            report['original_artist_disk_unchanged'] = False
            report['final_protected_disk_error'] = str(error)
        report['completed'] = bool(report['completed'] and report['original_artist_disk_unchanged'])
        report['module_only_rollback_cannot_restore_Undo_or_unknown_transient_state'] = True
        write(receipt, report)
    result = {'completed': report['completed'], 'error': report.get('error'), 'receipt': pin(receipt, sha(receipt)),
              'new_version': report.get('new_version'), 'module_only_rollback_verified': report.get('module_only_rollback_verified', False)}
    print('ORIGINAL_ARTIST_RUNTIME_REFRESH ' + json.dumps(result, ensure_ascii=False))
    return result
