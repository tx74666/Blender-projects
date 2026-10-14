"""Source draft: one owned headful original clone, exact Input20 and controls-only publication.

Requires actual successful clock plus retained-handle release and a future pinned R8
projection. The first scope uses public backend creation, one live Target edit with
public Save, exact same-frame restore/Save, references, owned save/reopen and publication.
Gun Motion/Edit and Key UI run in this clone; other public UI and Undo/Redo remain deferred.
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
import time
from types import MethodType, SimpleNamespace

ROUND = Path(__file__).resolve().parent
CLOCK_SHA = '9f3647bc0e7d177e1e2dbecd0db7a49ffbf6a52b4f61c28d8b024c7c45a08155'
PROTECTION_SHA = '7098c3b20a5a115423913ce91268cc4fd9a57adab9973c9c6c2000e2afd2d468'
ORACLE_SHA = '260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d'
SNAPSHOT_SHA = '5387b972a123b81ab3b77df398fd1cfd3e33165a8934095bf3ff1953663c81ef'
SEED_SHA = 'cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'
ARTIST_SHA = 'cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'
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
    require(receipt.get('scope') == 'Read-only reopened byte-copy of latest user-saved disk file; no live-memory claim.'
            and receipt.get('artist_opened_or_written') is False
            and receipt.get('backup_disk_unchanged') is True,
            'Require the actual current saved-artist readback; all saved Actions remain protected.')
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
    seed_receipt = {**receipt, 'before': {**receipt['before'], 'full_worklist': qualified_worklist}}
    report['candidate_new_empty_RNA_defaults'] = {
        'candidate_version': '.'.join(map(str, package.bl_info['version'])),
        'composition_catalog': [], 'composition_catalog_index': -1,
        'original_snapshot_immutable': True,
        'qualification': 'Only new empty RNA defaults; all current saved Actions are included unchanged.'}
    probe.snapshot_receipt = seed_receipt
    expected_actions = [probe.snapshot_identity(row['identity']) for row in seed_receipt['before']['actions']]
    loaded_actions = [{'identity': probe.id(action), 'users': action.users,
        'use_fake_user': action.use_fake_user, 'is_asset': action.asset_data is not None}
        for action in bpy.data.actions]
    expected_keys = {helper.digest(row) for row in expected_actions}
    loaded_keys = {helper.digest(row['identity']) for row in loaded_actions}
    report['loaded_snapshot_Action_inventory'] = {
        'expected_source': 'Actual reopened byte-copy of current user-saved X; every saved Action is protected.',
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


@contextmanager
def temporary_body_display(bpy, ctx, rig, package, session, report, label):
    """Reveal through the existing BODY button; restore every affected display."""
    def check(value, message):
        if not value:
            raise RuntimeError(message)

    display, native = package.bone_display, package.unity_animation_rigging
    original = __import__(package.__name__ + '.body_original_mode', fromlist=['body_original_mode'])
    pair = session['original_inputs']

    def input_motions():
        # Reuse the existing bounded Input20 fingerprint. No Body scan,
        # backend validation, capture sampling, file read or frame seek.
        return tuple((int(pair[side + '_action'].as_pointer()), pair[side + '_slot'],
                      native._motion(pair[side + '_action'], pair[side + '_slot']))
                     for side in ('source', 'custom'))

    check(ctx.active_object == rig and rig.mode == 'POSE'
          and not original.active(rig),
          'Use the existing Main Rig in Pose/Controls mode for temporary Body display.')
    collections = display._control_collections(ctx, rig, 'BODY')
    check(len(collections) == 1 and collections[0][0] == rig,
          'Temporary Body display needs the one existing owned Body collection.')
    affected = display._affected(ctx, rig)
    checkpoint = display._checkpoint(affected)
    entry_frame = (ctx.scene.frame_current, ctx.scene.frame_subframe)
    observation = {'label': label, 'completed': False,
        'affected_rigs': [target.name for target in affected],
        'public_operator': 'character_designer.bone_display', 'action': 'BODY',
        'public_operator_executed': False, 'display_restored_exactly': False,
        'Source20_Custom20_unchanged_by_show': False,
        'Source20_Custom20_unchanged_by_restore': False}
    report.setdefault('temporary_Body_display_scopes', []).append(observation)
    primary = None
    try:
        before_show = input_motions()
        if not display._controls_visible(collections):
            # BODY is a toggle. Call it only when its current group is hidden,
            # so this is the artist's normal Show Body gesture, never Hide Body.
            observation['public_operator_executed'] = True
            result = bpy.ops.character_designer.bone_display('EXEC_DEFAULT', action='BODY')
            observation['operator_result'] = sorted(result)
            check(result == {'FINISHED'}, 'The public Body display operator did not finish.')
        check(display._controls_visible(collections), 'The existing Body controls are still not visible.')
        check(input_motions() == before_show, 'Showing Body changed a Source20 or Custom20 Action/slot/input.')
        check((ctx.scene.frame_current, ctx.scene.frame_subframe) == entry_frame,
              'Showing Body changed the current native key frame.')
        observation['Source20_Custom20_unchanged_by_show'] = True
        yield
        observation['completed'] = True
    except Exception as error:
        primary = error
        observation['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if observation.get('operator_result') == ['FINISHED']:
            report['public_UI_operators_executed'] = True
            called = report.setdefault('actual_public_UI_operator_ids', [])
            if observation['public_operator'] not in called:
                called.append(observation['public_operator'])
        try:
            before_restore, input_error = None, None
            try:
                before_restore = input_motions()
            except Exception as error:
                # A broken input proof must not prevent restoring the display.
                input_error = error
            # BODY can clear solo flags on Main and Dress rigs. The official
            # complete checkpoint also retains temporary VIEW/REFS ownership.
            display._rollback(checkpoint)
            check(display._checkpoint(affected) == checkpoint,
                  'Temporary Body display did not restore the exact Main/Dress snapshots and VIEW/REFS.')
            observation['display_restored_exactly'] = True
            if input_error is not None:
                raise RuntimeError('Input20 proof was unavailable before display restore.') from input_error
            check(input_motions() == before_restore,
                  'Restoring Body display changed a Source20 or Custom20 Action/slot/input.')
            check((ctx.scene.frame_current, ctx.scene.frame_subframe) == entry_frame,
                  'Temporary Body display changed the same-frame edit/restore scope.')
            observation['Source20_Custom20_unchanged_by_restore'] = True
        except Exception as error:
            observation['completed'] = False
            observation['restore_error'] = type(error).__name__ + ': ' + str(error)
            if primary is None:
                raise
            primary.add_note('Temporary Body display restore failed: ' + str(error))


def exercise_gun_ui(bpy, ctx, rig, package, helper, baseline_dto, report, *, edited_publication_destination=None):
    """Exercise the actual Gun buttons in this clone; restore only live controls."""
    backend, native = package.unity_animation_original_inputs, package.unity_animation_rigging
    operator_ids = ('character_designer.original_inputs_edit', 'character_designer.original_inputs_save')
    witness = {'completed': False, 'public_save_count': 0, 'restored_exact_BF59': False,
        'operator_ids': list(operator_ids), 'private_curve_writes': False, 'frame_seek_during_restore': False,
        'Unity_world_equivalence_claimed': False, 'extra_publications': 0}
    report['Gun_Motion_UI_edit_Key_restore'] = witness
    require(bpy.ops.character_designer.original_inputs_edit.poll(), 'The actual Gun Motion operator is unavailable in this owning context.')
    print('ORIGINAL20_STAGE Gun_Motion_UI_select', flush=True)
    result = bpy.ops.character_designer.original_inputs_edit('EXEC_DEFAULT', focus_gun_motion=True)
    witness['edit_operator_result'] = sorted(result)
    require(result == {'FINISHED'}, 'The actual Gun Motion operator did not finish.')
    session = backend.current(rig)
    require(session is not None and session['enabled'] and session['tweak_enabled']
        and session['edit_role'] == 'RIGGING' and ctx.active_object == rig and rig.mode == 'POSE'
        and native._time(ctx, session) == 0., 'Gun Motion must edit the exact first Custom20 key in its owning Pose context.')
    sides = {row['native_side']: (index, row) for index, row in enumerate(session['native_bindings'])}
    require(set(sides) == {'L', 'R'} and len(session['native_bindings']) == 2, 'Gun Motion needs exactly the captured two-arm inputs.')
    right_index, right = sides['R']; left_index, left = sides['L']
    target = rig.pose.bones[right['target']]
    require(rig.data.bones.active == target.bone
        and [pb.name for pb in rig.pose.bones if package.animation_composition._pose_selection_owner(pb).select] == [target.name],
        'The actual Gun Motion operator did not uniquely select its existing Right Target.')
    visible = [collection.is_visible_effectively for collection in target.bone.collections]
    require(not getattr(target, 'hide', target.bone.hide) and not target.bone.hide
        and ((not visible and not rig.data.collections.is_solo_active) or any(visible))
        and not target.bone.hide_select and not target.lock_location[0],
        'The selected Gun Motion Target must be visible, selectable and position-unlocked.')
    record, gun_objects = package.animation_composition_weapon.validate_owned(rig)
    require(record['rigging_session_owner'] == session['owner']
        and json.loads(record['proof_json'])['native_mount'] == right['chain'][2]
        and session['capture']['bindings'][left_index]['targetParentPath'] == session['capture']['bindings'][right_index]['tipPath'],
        'Gun Motion must use the authenticated gun mount and current Right-hand parent for Left Target.')
    exact_initial_twenty(package, session['original_inputs'])
    require(backend.capture_inputs(ctx, session) == baseline_dto, 'Gun Motion selection changed a saved input.')
    source_before = native._motion(session['base_action'], session['base_slot'])
    custom_before = native._motion(session['input_action'], session['input_slot'])
    channel_keys = set(native._curves(session['input_action'], session['input_slot']))
    require(len(channel_keys) == 20, 'Gun Motion must retain the existing twenty scalar channels.')
    # Save all four live input transforms because the Left Target follows the
    # moving Right-hand parent. These are pose channels, never Action curves.
    ctx.view_layer.update()
    controls = [rig.pose.bones[row[key]] for row in session['native_bindings'] for key in ('target', 'pole')]
    fields = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')
    prior = {pb.name: {field: list(getattr(pb, field)) for field in fields} for pb in controls}
    pose_bones = {'right_target': target, 'right_hand': rig.pose.bones[right['chain'][2]],
        'left_target': rig.pose.bones[left['target']], 'left_hand': rig.pose.bones[left['chain'][2]]}
    def observed():
        return {**{name: helper.base.matrix(rig.matrix_world @ pb.matrix) for name, pb in pose_bones.items()},
            **{'gun:' + obj.name: helper.base.matrix(obj.matrix_world) for obj in gun_objects}}
    before = observed()
    witness.update(target=target.name, time=0., native_key_frame=1.,
        source_motion_before=source_before, custom_motion_before=custom_before,
        captured_rig_weights=[binding['rigWeight'] for binding in session['capture']['bindings']],
        captured_weights_modified=False, owned_gun_objects=[obj.name for obj in gun_objects])
    target.location[0] = prior[target.name]['location'][0] + .001
    report['Target_Hint_edit_or_Key_or_Undo_Redo_performed'] = True
    rig.update_tag(refresh={'OBJECT'}); ctx.view_layer.update()
    changed = observed()
    deltas = {name: helper.base.delta(before[name], changed[name]) for name in before}
    witness['native_follow_matrix_deltas'] = deltas
    require(all(delta > 1e-7 for delta in deltas.values()),
        'Moving Gun Motion must visibly move its Right Target, Right hand, owned gun, Left Target and Left hand in this Blender preview.')
    require(bpy.ops.character_designer.original_inputs_save.poll(), 'Key Gun Motion is unavailable after its actual edit.')
    print('ORIGINAL20_STAGE Key_Gun_Motion_UI_edited', flush=True)
    result = bpy.ops.character_designer.original_inputs_save('EXEC_DEFAULT')
    witness['edited_save_operator_result'] = sorted(result)
    require(result == {'FINISHED'}, 'The actual Key Gun Motion operator did not save the edit.')
    witness['public_save_count'] = 1
    session = backend.current(rig)
    edited = backend.capture_inputs(ctx, session)
    require(set(edited) == RETURN_FIELDS and len(edited['frames']) == 59
        and set(native._curves(session['input_action'], session['input_slot'])) == channel_keys
        and native._motion(session['input_action'], session['input_slot']) != custom_before
        and edited['frames'][0]['controls'][right_index]['targetPosition'] != baseline_dto['frames'][0]['controls'][right_index]['targetPosition']
        and native._motion(session['base_action'], session['base_slot']) == source_before,
        'Key Gun Motion must save the changed Right Target in Custom20 while retaining Source20 and strict Return14.')
    witness.update(edited_twenty_scalar_Return_verified=True, Source20_unchanged_after_edit=True)
    if edited_publication_destination is not None:
        print('ORIGINAL20_STAGE publish_actual_edited_Gun_Return', flush=True)
        edited_publication = backend.publish_inputs(ctx, rig, str(edited_publication_destination))
        witness.update(edited_publication=edited_publication, extra_publications=1,
            edited_publication_is_test_evidence_only=True)
        require(set(edited_publication) == {'return', 'publication'},
            'The edited Gun publisher returned no two-file ownership pins.')
        for row in edited_publication.values(): helper.pin(row['path'], row['sha256'])
        publication = helper.document(edited_publication['publication']['path'])
        pair = session['original_inputs']
        require(helper.document(edited_publication['return']['path']) == edited
            and set(edited) == RETURN_FIELDS and len(edited) == 14
            and publication['schema'] == backend.PUBLICATION_SCHEMA and publication['completed'] is True
            and publication['controlChannelCount'] == 20
            and publication['returnSha256'] == edited_publication['return']['sha256']
            and publication['sourceActionId'] == pair['source_uuid']
            and publication['targetInputActionId'] == pair['capture']['newActionId']
            and all(publication[field] == edited[field] for field in RETURN_FIELDS - {'schema', 'frames'})
            and all(publication[field] is True for field in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly'))
            and native._motion(session['base_action'], session['base_slot']) == source_before,
            'The retained edited Gun Return/publication changed strict14 inputs, Source20 or controls-only identities.')
        witness['edited_Return_readback_verified'] = True
    # Restore Right first so its parent-follow callback settles, then put the
    # original input channel values back without seeking or rewriting keys.
    for row in (right, left):
        for key in ('target', 'pole'):
            pb = rig.pose.bones[row[key]]
            for field in fields:
                setattr(pb, field, prior[pb.name][field])
        rig.update_tag(refresh={'OBJECT'}); ctx.view_layer.update()
    require(native._time(ctx, backend.current(rig)) == 0., 'Restore Gun Motion at the same existing native key, with no seek.')
    require(bpy.ops.character_designer.original_inputs_save.poll(), 'Key Gun Motion is unavailable for the exact restore.')
    print('ORIGINAL20_STAGE Key_Gun_Motion_UI_restore', flush=True)
    result = bpy.ops.character_designer.original_inputs_save('EXEC_DEFAULT')
    witness['restore_save_operator_result'] = sorted(result)
    require(result == {'FINISHED'}, 'The actual Key Gun Motion operator did not save the restore.')
    witness['public_save_count'] = 2
    session = backend.current(rig)
    exact_initial_twenty(package, session['original_inputs'])
    require(backend.capture_inputs(ctx, session) == baseline_dto
        and native._motion(session['base_action'], session['base_slot']) == source_before,
        'Gun Motion restore left a BF59 residual; preserve the failure without private curve repair or tolerance relaxation.')
    witness.update(completed=True, restored_exact_BF59=True, Source20_unchanged_after_restore=True,
        custom_motion_after_restore=native._motion(session['input_action'], session['input_slot']))
    report['public_UI_operators_executed'] = True
    report['actual_public_UI_operator_ids'] = list(operator_ids)
    report['deferred_public_UI'] = [name for name in report['deferred_public_UI'] if name not in operator_ids]
    return session


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
            'Use actual current5387/CC9A saved artist and unchanged260B oracle.')
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
        'world_model_equivalence': 'Unknown', 'natural_exit_verified': False, 'scope': 'Exact captured Input20, actual Gun Motion/Key UI follow and restore, one live Left Target edit/public Save and exact restore, read-only Body references, owned clone save/reopen then actual controls-only publication.'}
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
                reference_started = time.perf_counter()
                backend.view_body(ctx, rig, side)
                elapsed = time.perf_counter() - reference_started
                report.setdefault("body_reference_seconds", {})[side] = elapsed
                print("ORIGINAL20_TIMING " + json.dumps({"view_body": side, "seconds": elapsed}), flush=True)
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
            with temporary_body_display(bpy, ctx, rig, package, session, report, 'Gun Motion edit and restore'):
                session = exercise_gun_ui(bpy, ctx, rig, package, helper, baseline_dto, report)
            guard(ctx, probe, 'Gun_Motion_UI_restored_saved')
            with temporary_body_display(bpy, ctx, rig, package, session, report, 'Left Target edit and Save'):
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
            with temporary_body_display(bpy, ctx, rig, package, session, report, 'Left Target restore and Save'):
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
        report.update(completed=False, error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc(),
            failure_scene_saved=False)
        # Persist the primary failure before any save handler can run. This
        # artifact is a recovery aid, never a successful integration checkpoint.
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        try:
            active_file = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
            owned_files = {Path(inputs['seed']['path']).resolve(), (output / 'original20_controls_owned.blend').resolve()}
            if active_file is not None and active_file in owned_files:
                failure_file = (output / 'failed_original20_scene.blend').resolve()
                require(failure_file.parent == output.resolve() and not failure_file.exists()
                        and active_file != Path(inputs['protected_artist']['path']).resolve(),
                        'Failure SaveCopy must use a new owned output file, never the artist.')
                saved = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=str(failure_file),
                    copy=True, check_existing=False)
                report['failure_scene_save_result'] = sorted(saved)
                require(saved == {'FINISHED'} and failure_file.is_file(), 'Failure-scene SaveCopy did not finish.')
                report['failure_scene'] = pin(failure_file, helper.sha(failure_file))
                require(Path(bpy.data.filepath).resolve() == active_file, 'Failure SaveCopy changed the active file path.')
                for name in ('seed', 'protected_artist'):
                    pin(inputs[name]['path'], inputs[name]['sha256'])
                report['failure_scene_saved'] = True
            else:
                report['failure_scene_save_skipped'] = 'No authenticated owned seed/clone is currently open.'
        except Exception as checkpoint_error:
            report['failure_scene_error'] = type(checkpoint_error).__name__ + ': ' + str(checkpoint_error)
    finally:
        report['natural_exit_external_retained_handle_readback_required'] = True
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        print('ORIGINAL20_CONTROLS_CLONE ' + json.dumps({'completed': report['completed'], 'report': pin(report_path, helper.sha(report_path))}))
    if args.quit_on_completion:
        # Leave startup execution before asking the owned GUI event loop to quit.
        # Success or failure is already durable; external process evidence decides exit.
        quit_path = output / "owned_quit_observation.json"
        def quit_owned_after_startup():
            observation = {"completed_report": bool(report["completed"]), "pid": os.getpid(),
                           "requested_from_timer": True, "natural_exit_still_external": True}
            try:
                with owning_context(bpy):
                    observation["operator_result"] = sorted(bpy.ops.wm.quit_blender("EXEC_DEFAULT"))
            except Exception as error:
                observation["error"] = type(error).__name__ + ": " + str(error)
            quit_path.write_text(json.dumps(observation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return None
        bpy.app.timers.register(quit_owned_after_startup, first_interval=3., persistent=False)
    elif not report['completed']:
        raise RuntimeError(report['error'])


if __name__ == '__main__': main()
