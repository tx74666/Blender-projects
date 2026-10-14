"""SOURCE ONLY: one future in-process original-artist CD .24 -> .26 refresh.

No automatic entry point, SDK call, file open/save, Attach, frame evaluation,
Undo, repair or process launch. Root must grant this exact future original
process call after the latest SaveCopy, actual Original20 clone validation and retained-handle END.
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
    """Compare every old field; allow only actual empty root schema defaults and two empty row workspace fields."""
    if isinstance(old, dict):
        require(isinstance(current, dict) and set(old) <= set(current), 'Removed protected field at ' + path)
        for key in set(current) - set(old):
            value = current[key]
            if scene:
                row_default = (key in {'workspace_path', 'workspace_identity'}
                    and re.search(r'\.worklist\.items\.items\[\d+\]$', path) is not None and value == '')
                root_default = (re.fullmatch(r'Scenes\..+\.worklist', path) is not None and (
                    key in {'composition_workspace_path', 'composition_workspace_identity', 'composition_base_item_id'}
                    and value == '' or key == 'composition_catalog' and value == {'kind': 'COLLECTION', 'items': []}
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
            'An actual cached job/scan is active; defer refresh without importing disk .26.')
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
    require(latest['schema'] == 'x.validation.latest-original-artist-snapshot/1'
            and latest['completed'] is True and latest['backup_verified'] is True
            and latest['original_artist_saved'] is False and latest['original_artist_disk_unchanged'] is True
            and latest['runtime_version'] == [0, 77, 24] and latest['source']['sha256'] == SNAPSHOT_SHA
            and latest['pid'] == expected_pid and latest['external_process_filetime'] == external_process_filetime
            and latest['protected_artist'] == protected, 'Require the actual latest803 completed SaveCopy of this original process.')
    backup = pin(latest['backup']['path'], latest['backup']['sha256'])
    require(backup == latest['backup'] and Path(backup['path']).is_relative_to(ROUND)
            and Path(backup['path']) != ARTIST.resolve(), 'The latest recovery backup pin is invalid.')
    manifest_pin = pin(package_manifest, package_manifest_sha256)
    candidate, frozen_root = projection(manifest_pin, '0.77.26', 190)
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
              'latest_seed': backup, 'package_manifest': manifest_pin, 'rollback_projection': old_pin,
              'original20_report': pin(original20_report, original20_report_sha256),
              'original20_source': pin(original20_source, original20_source_sha256),
              'original20_exit_receipt': pin(original20_exit_receipt, original20_exit_receipt_sha256)}
    control, exited = document(inputs['original20_report']), document(inputs['original20_exit_receipt'])
    require(Path(inputs['original20_source']['path']).is_relative_to(ROUND)
            and control['source_inputs']['source'] == inputs['original20_source'],
            'Use the reviewed actual Original20 source/report pair, never an ordinary Attach/FBX harness.')
    require(control['schema'] == 'x.validation.original20-controls-clone/1'
            and control['completed'] is True and control['native_execution_performed'] is True
            and control['package_manifest_version'] == '0.77.26' and control['package_file_count'] == 190
            and all(control[field] is True for field in ('original_clone_only', 'save_reopen_verified',
                'original_rows_header_Body_keys_and_observed_assets_preserved',
                'strict14_Return_and_twenty_scalar_publication_verified', 'input_files_unchanged',
                'no_QA_offset_remaining', 'public_Custom20_edit_Save_restore_verified'))
            and control['artist_opened'] is False and control['artist_written'] is False,
            'Require actual completed original-clone Input20 capture/edit/restore/save-reopen/publication evidence.')
    for label, expected in (('protected_artist', protected), ('snapshot_receipt', latest_pin),
                            ('seed', backup), ('package_manifest', manifest_pin)):
        require(control['source_inputs'][label] == expected, 'Clone proof uses a different refresh input: ' + label)
    witness = control['live_Target_edit_and_Save_restore']
    require(control['initial_Input20_exact_prepared_capture_verified'] is True
            and witness['restored_exact_BF59'] is True and witness['public_save_count'] == 2
            and witness['edited_Return_readback_verified'] is True,
            'The actual Target edit and public Save must have restored exact BF59 before clone save/reopen.')
    require(exited['schema'] == 'x.validation.resource-release/1' and exited['status'] == 'ACTUAL_RELEASE'
            and exited['passed'] is True and exited['retained_handle_natural_exit'] is True
            and type(exited['native_exit_code']) is int and exited['native_exit_code'] == 0
            and type(exited['owned_pid']) is int and exited['owned_pid'] > 0
            and isinstance(exited['owned_process_filetime'], str) and exited['owned_process_filetime'].isdigit()
            and 0 < int(exited['owned_process_filetime']) < 2 ** 64
            and isinstance(exited['native_exited_utc'], str) and exited['native_exited_utc'].endswith(('Z', '+00:00'))
            and exited['owned_native_gone'] is True and exited['all_owned_activity_closed'] is True
            and exited['process_termination_performed'] is False
            and exited['source'] == inputs['original20_source'] and exited['report'] == inputs['original20_report'],
            'Require the genuine matching Original20 retained-handle exit0/FILETIME/closed END receipt.')
    saved = control['saved_clone']
    require(pin(saved['path'], saved['sha256']) == saved and Path(saved['path']).is_relative_to(ROUND)
            and Path(saved['path']) != ARTIST.resolve(), 'The actual saved/reopened clone pin is invalid.')
    published = control['actual_controls_only_publication']
    require(set(published) == {'return', 'publication'}, 'Use the actual two-file controls-only publication.')
    for name, row in published.items():
        require(pin(row['path'], row['sha256']) == row and Path(row['path']).is_relative_to(ROUND),
                'Actual controls-only publication pin changed: ' + name)
        inputs['original20_' + name] = row
    dto, pub = document(published['return']), document(published['publication'])
    require(set(dto) == RETURN_FIELDS and pub['schema'] == 'cdesigner.controls-only-publication/1'
            and pub['completed'] is True and pub['controlChannelCount'] == 20
            and pub['returnSha256'] == published['return']['sha256']
            and pub['targetInputActionId'] == dto['newActionId']
            and all(pub[field] == dto[field] for field in RETURN_FIELDS - {'schema', 'frames'})
            and all(pub[field] is True for field in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly')),
            'The actual twenty-scalar/strict14 Return publication does not match its final restored carrier.')
    require(len(dto['frames']) == 59 and dto['sampleRate'] == 60
            and all(len(frame['controls']) == 2 and all(
                set(control_row) == {'targetPosition', 'targetRotation', 'hintPosition'}
                and len(control_row['targetPosition']) == len(control_row['hintPosition']) == 3
                and len(control_row['targetRotation']) == 4 for control_row in frame['controls'])
                for frame in dto['frames']), 'The actual published Input20 domain is not the fixed BF59 two-arm schedule.')
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
               'Original20_acceptance': 'Actual isolated clone only; artist Input20 setup is not performed by refresh.',
               'public_UI_or_Undo_acceptance_inferred': False, 'world_model_equivalence': 'Unknown',
               'Pose_fake_user_final_save_step_performed': False}
    write(receipt, report, first=True)
    scene_name, rig_name = latest['after']['context']['scene']['name'], latest['after']['original_MainRig_session_and_rawRest']['value']['rig']['name']
    old_sys_path = list(sys.path)
    try:
        with light.original_context(bpy, scene_name, rig_name) as (ctx, rig):
            idle(old, ctx, bpy)
            # The unchanged260b oracle uses these exact lazy imports. Require
            # cached .24 dependencies, not newly deployed disk .26 code, before
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
                    and bool(bpy.data.is_dirty) == latest['dirty_after'], 'Original state changed since latest803 SaveCopy; take a new backup first.')
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
                require(tuple(new.bl_info['version']) == (0, 77, 26), 'Registered candidate is not .26.')
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
            report.update(completed=True, phase='completed_refresh_only_no_Attach_or_save', new_version=[0, 77, 26],
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
