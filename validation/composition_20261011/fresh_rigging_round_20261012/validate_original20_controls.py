"""Source draft: one owned headful original clone, exact Input20 and controls-only publication.

Requires actual successful clock plus retained-handle release and a future pinned R8
projection. The first scope uses public backend creation, one live Target edit with
public Save, exact same-frame restore/Save, references, owned save/reopen and publication.
Public UI and Undo/Redo remain separate unexecuted scopes.
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
CLOCK_SHA = '36b03fa10bbaf21531d04a4a843e3487cf86c4dabcb284b45c06b237963c4ba8'
PROTECTION_SHA = '7098c3b20a5a115423913ce91268cc4fd9a57adab9973c9c6c2000e2afd2d468'
ORACLE_SHA = '260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d'
SNAPSHOT_SHA = 'e6815b94a910d7ec82f33c094ea9dfbd93e811c9f1f6e46e3efb9df284bebcbd'
SEED_SHA = 'd353805da6b37407c435b26853fdbdad3e9c9f5f79be9432959b4fd9c3044395'
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
    inventory_path = ROUND / 'saved_action_inventory_02/saved_action_inventory.json'
    pose_path = ROUND / 'original_pose_metadata_02/original_pose_metadata.json'
    inventory = helper.document(helper.pin(inventory_path, '01aea77acf5349084a254a081feacbf18017aa6370415eabc73bb033c161e325')['path'])
    live_pose = helper.document(helper.pin(pose_path, 'e655f9f28de84210dd0f34898db79f0dad4f8b8b9f7867bfe2f7cc293c5a4f4a')['path'])
    require(inventory['completed'] is True and inventory['addon_registered'] is False
            and inventory['missing_original_local_names'] == ['Pose'] and not inventory['unexpected_loaded_local_names']
            and same_pin(inventory['input_pins']['seed'], receipt['backup'])
            and live_pose['completed'] is True and live_pose['pid'] == 27676
            and live_pose['Pose']['name'] == 'Pose' and live_pose['mutations'] == 0,
            'Require actual no-addon saved inventory and original unsaved Pose preservation evidence.')
    original_actions = receipt['before']['actions']
    omitted = [row for row in original_actions if row['identity']['name'] == 'Pose' and row['identity']['library'] is None]
    require(len(omitted) == 1, 'Only the actual unsaved Pose may be outside this old seed.')
    original_worklist = receipt['before']['full_worklist']
    recorded = original_worklist['value']
    custom_properties = recorded['$custom_properties']
    require(original_worklist['known'] is True and isinstance(custom_properties, dict)
            and all(key not in recorded and key not in custom_properties
                for key in ('composition_catalog', 'composition_catalog_index')),
            'Only absent .24 RNA/custom-property fields may receive new empty candidate defaults.')
    candidate_worklist = package.animation_worklist.state(ctx)
    require(len(candidate_worklist.composition_catalog) == 0 and candidate_worklist.composition_catalog_index == -1,
            'The actual candidate composition catalog/default index must be empty/-1.')
    qualified_worklist = {**original_worklist, 'value': {**recorded,
        'composition_catalog': [], 'composition_catalog_index': -1}}
    seed_receipt = {**receipt, 'before': {**receipt['before'],
        'actions': [row for row in original_actions if row not in omitted], 'full_worklist': qualified_worklist}}
    report['candidate_new_empty_RNA_defaults'] = {
        'candidate_version': '.'.join(map(str, package.bl_info['version'])),
        'composition_catalog': [], 'composition_catalog_index': -1,
        'original_record_and_custom_properties_lacked_both_fields': True,
        'original_snapshot_immutable': True,
        'qualification': 'New empty candidate RNA defaults only; these were not saved values in original99B.'}
    probe.snapshot_receipt = seed_receipt
    report['original_unsaved_Pose_outside_old_seed'] = {'original_memory_receipt_unchanged': True,
        'saved_inventory': str(inventory_path), 'original_live_pose_readonly': str(pose_path),
        'omitted_identity': omitted[0]['identity'], 'saved_baseline_action_count': 10,
        'critical_Body_Source_Custom_reference_NLA_slots_guards_unchanged': True,
        'qualification': 'Old seed never saved user Pose; native20 protects actual saved10 only. Original360-curve Pose must be preserved separately and in final artist save; no full11 preservation claim.'}
    expected_actions = [probe.snapshot_identity(row['identity']) for row in seed_receipt['before']['actions']]
    loaded_actions = [{'identity': probe.id(action), 'users': action.users,
        'use_fake_user': action.use_fake_user, 'is_asset': action.asset_data is not None}
        for action in bpy.data.actions]
    expected_keys = {helper.digest(row) for row in expected_actions}
    loaded_keys = {helper.digest(row['identity']) for row in loaded_actions}
    report['loaded_snapshot_Action_inventory'] = {
        'expected_source': 'Original live-memory before/after SaveCopy in actual6DF/99B; seed was not reopened by snapshot.',
        'expected': expected_actions, 'loaded': loaded_actions,
        'missing': [row for row in expected_actions if helper.digest(row) not in loaded_keys],
        'unexpected': [row['identity'] for row in loaded_actions if helper.digest(row['identity']) not in expected_keys],
        'expected_count': len(expected_actions), 'loaded_count': len(loaded_actions)}
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
    inputs['protection_inherited_helper'] = pin(ROUND / 'new_official_cosha_round.py', helper.CFAA_SHA)
    for name in ('snapshot_receipt', 'seed', 'prepared_report', 'clock_report', 'clock_exit_receipt', 'package_manifest', 'protected_artist', 'preservation_oracle'):
        inputs[name] = pin(getattr(args, name), getattr(args, name + '_sha256'))
    require(inputs['snapshot_receipt']['sha256'] == SNAPSHOT_SHA and inputs['seed']['sha256'] == SEED_SHA
            and inputs['protected_artist']['sha256'] == ARTIST_SHA and inputs['preservation_oracle']['sha256'] == ORACLE_SHA,
            'Use actual current E681/D353, protected3CD artist and unchanged260B oracle.')
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
        'ordinary_Attach_or_FBX_or_fresh_Rig_setup_performed': False, 'Target_Hint_edit_or_Key_or_Undo_Redo_performed': False, 'Undo_Redo_performed': False,
        'public_UI_operators_executed': False, 'deferred_public_UI': list(DEFERRED_PUBLIC_UI), 'Unity_Apply_verified': False,
        'world_model_equivalence': 'Unknown', 'natural_exit_verified': False, 'scope': 'Exact captured Input20, one live Target edit/public Save and exact restore, read-only Body references, owned clone save/reopen then actual controls-only publication.'}
    report_path = output / 'original20_controls_report.json'
    with report_path.open('x', encoding='utf-8') as stream: json.dump(report, stream, indent=2)
    def guard(ctx, probe, boundary):
        saved = probe.worklist.state(ctx)
        require(saved.composition_catalog_index == -1, 'The new empty composition catalog index changed from its authenticated default.')
        require({i.item_id for i in saved.items} == set(probe.old['rows']), 'An original row was added or removed.')
        ft = sys.modules.get('character_designer.forearm_twist')
        if ft is not None:
            report.setdefault('forearm_runtime_boundaries', []).append({'boundary': boundary, 'when': 'before_old_guard',
                'busy': bool(ft._BUSY), 'errors': dict(ft._ERRORS),
                'preview_meshes': [obj.name for obj in ctx.scene.objects if obj.type == 'MESH' and ft.PREVIEW_KEY in obj],
                'active_calibration_preview': bool(ft._SESSION)})
        probe.guard_old(ctx, boundary, full_motions=True)
        if ft is not None:
            report['forearm_runtime_boundaries'].append({'boundary': boundary, 'when': 'before_asset_guard',
                'busy': bool(ft._BUSY), 'errors': dict(ft._ERRORS)})
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
            print('ORIGINAL20_STAGE protection_and_asset_baseline', flush=True)
            probe = protection(helper, package, bpy, ctx, rig, receipt, oracle, report)
            old_actions = probe.actions(full_motions=True)
            probe.old = probe.old_state(ctx); probe.old['actions'] = old_actions
            probe.assets_before = probe.asset_snapshot(ctx, rig)
            require(backend.PAIR_KEY not in rig, 'Keep an existing input pair; this scope needs the untouched1C seed.')
            print('ORIGINAL20_STAGE public_import_inputs', flush=True)
            session = backend.import_inputs(ctx, rig, inputs['prepared_report']['path'], inputs['prepared_report']['sha256'], inputs['clock_report']['path'], inputs['clock_report']['sha256'])
            pair = session['original_inputs']; packet = package.unity_animation.load_package(pair['packet']['path'])
            require(pair['capture'] == package.animation_rigging_contract.validate_capture(packet['rigging'], packet=packet), 'The actual prepared capture was changed.')
            exact_initial_twenty(package, pair)
            print('ORIGINAL20_STAGE capture_initial_exact20', flush=True)
            baseline_dto = backend.capture_inputs(ctx, session)
            require(set(baseline_dto) == RETURN_FIELDS and len(baseline_dto) == 14, 'The Return is not the strict fourteen-field DTO.')
            report['initial_Input20_exact_prepared_capture_verified'] = True
            for side in ('SOURCE', 'CUSTOM'):
                print('ORIGINAL20_STAGE reference_' + side, flush=True)
                backend.view_body(ctx, rig, side)
                session = backend.current(rig)
                require(session['preview_reference']['legacy_side'] == side and backend.capture_inputs(ctx, session) == baseline_dto, 'A read-only Body reference changed the input Return.')
                exact_initial_twenty(package, session['original_inputs']); guard(ctx, probe, 'reference_' + side)
            # One actual Target drag and two public Save calls; never rewrite curves privately.
            native = package.unity_animation_rigging
            session = backend.current(rig)
            require(len(session['capture']['frames']) == 59 and session['capture']['frames'][0]['time'] == 0., 'Use the actual BF59 input schedule.')
            package.unity_animation._set_frame(ctx.scene, session['scene_start'])
            session = backend.edit_controls(ctx, rig)
            require(session['enabled'] and session['edit_role'] == 'RIGGING' and session['tweak_enabled']
                    and rig.mode == 'POSE' and rig.animation_data.use_tweak_mode
                    and rig.animation_data.action == session['input_action']
                    and rig.animation_data.action_slot_handle == session['input_slot']
                    and native._time(ctx, session) == 0., 'Edit the exact Custom20 at its existing first native key.')
            target = rig.pose.bones[session['native_bindings'][1]['target']]
            binding = session['capture']['bindings'][1]
            hidden = getattr(target, 'hide', target.bone.hide)
            solo = rig.data.collections.is_solo_active
            visible = [collection.is_visible_effectively for collection in target.bone.collections]
            require(type(hidden) is bool and type(solo) is bool and all(type(v) is bool for v in visible)
                    and not hidden and not target.bone.hide and ((not visible and not solo) or any(visible))
                    and not target.bone.hide_select and not target.lock_location[0]
                    and binding['targetPositionWeight'] > 0 and binding['constraintWeight'] > 0,
                    'The declared Left Target must be truly visible, selectable and position-unlocked.')
            for bone in rig.pose.bones: package.animation_composition._pose_selection_owner(bone).select = False
            package.animation_composition._pose_selection_owner(target).select = True
            rig.data.bones.active = target.bone
            require(rig.data.bones.active == target.bone
                    and [bone.name for bone in rig.pose.bones if package.animation_composition._pose_selection_owner(bone).select] == [target.name],
                    'Select only the authenticated Left Target.')
            location_before = [float(target.location[i]) for i in range(3)]
            matrix_before = helper.base.matrix(target.matrix)
            source_before = native._motion(session['base_action'], session['base_slot'])
            custom_before = native._motion(session['input_action'], session['input_slot'])
            witness = {'target': target.name, 'side': 'Left', 'time': 0., 'native_key_frame': 1.,
                'location_before': location_before, 'matrix_before': matrix_before,
                'source_motion_before': source_before, 'custom_motion_before': custom_before,
                'public_save_count': 0, 'restored_exact_BF59': False}
            report['live_Target_edit_and_Save_restore'] = witness
            target.location[0] = location_before[0] + .001
            report['Target_Hint_edit_or_Key_or_Undo_Redo_performed'] = True
            rig.update_tag(refresh={'OBJECT'}); ctx.view_layer.update()
            witness['changed_matrix'] = helper.base.matrix(target.matrix)
            witness['actual_native_Target_delta'] = helper.base.delta(matrix_before, witness['changed_matrix'])
            require(witness['actual_native_Target_delta'] > 0., 'The single live Target position did not move.')
            print('ORIGINAL20_STAGE public_Save_edited', flush=True)
            backend.key_current(ctx, rig); witness['public_save_count'] = 1
            session = backend.current(rig)
            witness['custom_motion_after_edit'] = native._motion(session['input_action'], session['input_slot'])
            edited_dto = backend.capture_inputs(ctx, session)
            left_before = baseline_dto['frames'][0]['controls'][1]['targetPosition']
            left_after = edited_dto['frames'][0]['controls'][1]['targetPosition']
            require(witness['custom_motion_after_edit'] != custom_before and edited_dto != baseline_dto
                    and len(left_before) == len(left_after) == 3 and left_after != left_before
                    and native._motion(session['base_action'], session['base_slot']) == source_before,
                    'Public Save must export the edited Left Target position while preserving Source20 and old Body proofs.')
            print('ORIGINAL20_STAGE publish_actual_edited_Return', flush=True)
            edited_publication = backend.publish_inputs(ctx, rig, str(output / 'edited_controls_Return.json'))
            require(set(edited_publication) == {'return', 'publication'}, 'The edited-state publisher returned no two-file ownership pins.')
            for row in edited_publication.values(): pin(row['path'], row['sha256'])
            edited_pub = document(edited_publication['publication']['path'])
            require(document(edited_publication['return']['path']) == edited_dto and set(edited_dto) == RETURN_FIELDS
                    and edited_pub['completed'] is True and edited_pub['controlChannelCount'] == 20
                    and edited_pub['returnSha256'] == edited_publication['return']['sha256'],
                    'The actual edited-state Return/publication readback lost the saved Target change.')
            witness.update(left_target_position_before=left_before, left_target_position_after_save=left_after,
                edited_actual_controls_only_publication=edited_publication, edited_Return_readback_verified=True,
                edited_publication_is_test_evidence_only=True)
            guard(ctx, probe, 'actual_Target_edit_saved')
            # No seek here: it would replay the changed key instead of restoring the live transform.
            target.location = location_before
            rig.update_tag(refresh={'OBJECT'}); ctx.view_layer.update()
            require(native._time(ctx, backend.current(rig)) == 0., 'Restore at exactly the same existing native key.')
            print('ORIGINAL20_STAGE public_Save_restore_exact_BF', flush=True)
            backend.key_current(ctx, rig); witness['public_save_count'] = 2
            session = backend.current(rig); pair = session['original_inputs']
            exact_initial_twenty(package, pair)
            require(backend.capture_inputs(ctx, session) == baseline_dto
                    and native._motion(session['base_action'], session['base_slot']) == source_before,
                    'Public restore/Save left an actual BF59 value residual; retain failure, never patch curves or relax the gate.')
            witness.update(restored_exact_BF59=True, custom_motion_after_restore=native._motion(session['input_action'], session['input_slot']))
            guard(ctx, probe, 'actual_Target_restored_saved')
            target = None
            backend.close_owned(ctx, rig); guard(ctx, probe, 'closed_before_save')
            saved_pair_motions = {key: package.unity_animation_rigging._motion(pair[key + '_action'], pair[key + '_slot']) for key in ('source', 'custom')}
        print('ORIGINAL20_STAGE save_owned_clone', flush=True)
        clone = output / 'original20_controls_owned.blend'
        require(not clone.exists() and bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=str(clone), check_existing=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == clone, 'The owned clone was not saved successfully.')
        report['saved_clone'] = pin(clone, helper.sha(clone))
        print('ORIGINAL20_STAGE reopen_owned_clone', flush=True)
        require(bpy.ops.wm.open_mainfile(filepath=str(clone), use_scripts=False, load_ui=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == clone, 'The saved owned clone did not reopen.')
        with owning_context(bpy) as (ctx, rig):
            guard(ctx, probe, 'reopened_closed_clone')
            require(backend.current(rig) is None and backend.PAIR_KEY in rig, 'The saved closed owner state did not reopen.')
            session = backend.import_inputs(ctx, rig, inputs['prepared_report']['path'], inputs['prepared_report']['sha256'], inputs['clock_report']['path'], inputs['clock_report']['sha256'])
            pair = session['original_inputs']; exact_initial_twenty(package, pair)
            require(backend.capture_inputs(ctx, session) == baseline_dto
                    and all(package.unity_animation_rigging._motion(pair[key + '_action'], pair[key + '_slot']) == value for key, value in saved_pair_motions.items()), 'Save/reopen changed an input carrier or Return.')
            print('ORIGINAL20_STAGE publish_final_restored_Return', flush=True)
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
            backend.close_owned(ctx, rig); guard(ctx, probe, 'reopened_final_closed')
        for row in inputs.values(): pin(row['path'], row['sha256'])
        for row in files.values(): pin(row['path'], row['sha256'])
        for row in published.values(): pin(row['path'], row['sha256'])
        report.update(completed=True, original_clone_only=True, save_reopen_verified=True,
            original_rows_header_Body_keys_and_observed_assets_preserved=True, strict14_Return_and_twenty_scalar_publication_verified=True,
            input_files_unchanged=True, no_QA_offset_remaining=True, public_Custom20_edit_Save_restore_verified=True)
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
