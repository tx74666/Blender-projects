"""Focused .33 recovery: no-op Save, actual Gun edit, public Undo/Redo and saved BF59.

No reimport, Body reference phases, full asset oracle or original-artist integration.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
from types import MethodType, SimpleNamespace
from contextlib import contextmanager
from math import acos, degrees, sqrt

ROUND = Path(__file__).resolve().parent
RECOVERY = ROUND / 'native_original20_r13_12/unverified_native12_quit_recovery.blend'
RECOVERY_SHA = 'd4cb2b7c8fb4667baa11e9f6cd7956076ef010f511069ea9c912a01e3d2dc5a6'
REPORT_SHA = '01b1d9fa2e428e03710a304bac7c8e7174c727edf650d3228b2c08fd09c7ea5b'
RELEASE_SHA = '239d846cade89959e0ecd73979c39e968d62acb86161cc4b990d9f4a10a7e6e2'
OLD_SOURCE_SHA = '82522f42851abbb1e3434cbaf4a9a26fd07aaaf327b1bee58400355c5fca7172'
HELPER_SHA = '7098c3b20a5a115423913ce91268cc4fd9a57adab9973c9c6c2000e2afd2d468'
PACKET_SHA = 'bffbbf00c3bcdfccc1a8bc1995aadeb188afb9f1d643bc78f1a34c8bb5cf7c4f'
PREPARED_SHA = '401b00d209b7806fa3c44c06fdf7e643256c64009d2abda45495a8b1cc0d4ac6'
CLOCK_SHA = 'cc0c749f29419747ec54195c63bd5d35249e97c2da0e62f5657880db77fc4e1d'
SNAPSHOT_SHA = '5387b972a123b81ab3b77df398fd1cfd3e33165a8934095bf3ff1953663c81ef'
ARTIST_SHA = 'cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path, expected):
    path = Path(path).resolve()
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(digest == expected.lower(), 'File pin changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': len(data)}


def document(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def load(path, expected, name, package=False):
    path = Path(pin(path, expected)['path'])
    spec = importlib.util.spec_from_file_location(name, path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def inventory(bpy, helper, pair, snapshot):
    probe = SimpleNamespace(bpy=bpy)
    for name in ('id', 'snapshot_identity'):
        setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))
    old = {helper.digest(probe.snapshot_identity(row['identity'])): row
           for row in snapshot['before']['actions']}
    owned = [probe.id(pair[key + '_action']) for key in ('source', 'custom')]
    owned_keys = {helper.digest(row) for row in owned}
    actual = {helper.digest(probe.id(action)): action for action in bpy.data.actions}
    require(len(old) == 10 and len(owned_keys) == 2 and not set(old) & owned_keys
            and len(actual) == 12 and set(actual) == set(old) | owned_keys,
            'Recovery must retain the original ten Actions and exactly the two authenticated input carriers.')
    for key, row in old.items():
        action = actual[key]
        slots = [{'handle': s.handle, 'target_id_type': s.target_id_type,
                  'identifier': s.identifier, 'name_display': s.name_display}
                 for s in action.slots] if action.is_action_layered else []
        require(slots == row['slots'], 'An original Action slot identity changed: ' + action.name)
    return {'original_count': len(old), 'original_identities_and_slots_exact': True,
            'original_actions': [probe.snapshot_identity(row['identity']) for row in old.values()],
            'owned_actions': owned, 'owned_slots': [pair['source_slot'], pair['custom_slot']],
            'source_uuid': pair['source_uuid'], 'custom_uuid': pair['capture']['newActionId'],
            'all_original_action_motion_or_geometry_preservation_claimed': False}


R14_SHA = '621f4872cd1a4ee29a1c8182a802e6beec5f7065afaaa21cfe0be624a0da258c'
MANIFEST_SHA = '5b195a86a5b6d3834c7c76f02c0f83e42835e0cf7ca268556ec1e4ebf36f6640'
RUNTIME_PINS = {
    '__init__.py': '8063a519b1afa37c3cb6d719d554eb2eb310e446078722ad999c7841e5253e62',
    'unity_animation_original_inputs.py': 'f45309023033f762ab10735ac958e14391b2807510acd92410413577aac901d9',
    'unity_animation_rigging.py': '6a0b2f1a8b8f227983595409645831d7db3c5d619aaab73aed9b46b21d01a83d',
    'animation_original_inputs_ui.py': '38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426',
    'animation_worklist_ui.py': '24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067',
    'forearm_twist.py': '54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408',
}
RETURN_FIELDS = {'schema', 'sourcePacketSha256', 'bindingsSha256', 'targetGuid', 'workItemId',
    'newActionId', 'sourceAction', 'sourceActionSlot', 'targetInputAction', 'targetInputActionSlot',
    'duration', 'sampleRate', 'loopTime', 'frames'}


def record_public(report, name):
    report['public_UI_operators_executed'] = True
    called = report.setdefault('actual_public_UI_operator_ids', [])
    if name not in called: called.append(name)
    report['deferred_public_UI'] = [value for value in report['deferred_public_UI'] if value != name]


@contextmanager
def undo_view(bpy):
    # No Scene/ViewLayer/Rig/active-object override survives the operation.
    windows = list(bpy.context.window_manager.windows)
    require(len(windows) == 1, 'Use the one isolated headful Window.')
    areas = [a for a in windows[0].screen.areas if a.type == 'VIEW_3D']
    require(len(areas) == 1, 'Use the unique existing factory View3D.')
    regions = [r for r in areas[0].regions if r.type == 'WINDOW']
    require(len(regions) == 1, 'Use the existing View3D WINDOW region.')
    with bpy.context.temp_override(window=windows[0], area=areas[0], region=regions[0]):
        yield


def push_checkpoint(bpy, report, label):
    # Caller has exited all owning_context/temporary_body_display scopes.
    with undo_view(bpy):
        require(bpy.context.preferences.edit.use_global_undo and bpy.ops.ed.undo_push.poll(), 'Global Undo/checkpoint unavailable.')
        result = bpy.ops.ed.undo_push('EXEC_DEFAULT', False, message=label)
        require(result == {'FINISHED'}, 'Explicit Undo checkpoint failed.')
    report.setdefault('undo_checkpoints', []).append({'label': label, 'result': sorted(result)})


def native_undo_redo(bpy, report, redo=False):
    # No old RNA passed in or inspected afterwards; fresh readback is next tick.
    with undo_view(bpy):
        operator = bpy.ops.ed.redo if redo else bpy.ops.ed.undo
        require(operator.poll(), 'Native Undo/Redo poll failed.')
        result = operator('EXEC_DEFAULT', False)
        require(result == {'FINISHED'}, 'Native Undo/Redo failed.')
        del operator
    report['Undo_Redo_performed'] = True
    report.setdefault('undo_redo_operators', []).append({'operator': 'ed.redo' if redo else 'ed.undo',
        'result': sorted(result), 'fresh_readback_deferred_to_next_timer_tick': True})


def numeric_delta(a, b):
    qa, qb = a['targetRotation'], b['targetRotation']
    dot = abs(sum(x*y for x,y in zip(qa,qb))) / sqrt(sum(x*x for x in qa)*sum(x*x for x in qb))
    return {'position_max_component': max(abs(x-y) for x,y in zip(a['targetPosition'], b['targetPosition'])),
        'rotation_degrees': degrees(2*acos(min(1., max(0., dot)))),
        'hint_max_component': max(abs(x-y) for x,y in zip(a['hintPosition'], b['hintPosition'])), 'before': a, 'after': b}


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
            result = bpy.ops.character_designer.bone_display('EXEC_DEFAULT', False, action='BODY')
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


def exercise_gun_edit(bpy, ctx, rig, package, helper, baseline_dto, report, *, edited_publication_destination):
    """Actual Gun edit/Save/publication only; subsequent public Undo owns restoration."""
    backend, native = package.unity_animation_original_inputs, package.unity_animation_rigging
    operator_ids = ('character_designer.original_inputs_edit', 'character_designer.original_inputs_save')
    witness = {'completed': False, 'public_save_count': 0, 'restored_exact_BF59': False,
        'operator_ids': list(operator_ids), 'private_curve_writes': False, 'frame_seek_during_restore': False,
        'Unity_world_equivalence_claimed': False, 'extra_publications': 0}
    report['Gun_Motion_UI_edit_Key'] = witness
    require(bpy.ops.character_designer.original_inputs_edit.poll(), 'The actual Gun Motion operator is unavailable in this owning context.')
    print('ORIGINAL20_STAGE Gun_Motion_UI_select', flush=True)
    result = bpy.ops.character_designer.original_inputs_edit('EXEC_DEFAULT', False, focus_gun_motion=True)
    witness['edit_operator_result'] = sorted(result)
    require(result == {'FINISHED'}, 'The actual Gun Motion operator did not finish.')
    record_public(report, operator_ids[0])
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
    sys.modules['native12_recovery_r14'].exact_initial_twenty(package, session['original_inputs'])
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
    result = bpy.ops.character_designer.original_inputs_save('EXEC_DEFAULT', False)
    witness['edited_save_operator_result'] = sorted(result)
    require(result == {'FINISHED'}, 'The actual Key Gun Motion operator did not save the edit.')
    record_public(report, operator_ids[1])
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
    witness.update(completed=True, restoration_method='subsequent public Undo', transform_restore_or_second_Save_performed=False)
    return {'dto': edited, 'motion': native._motion(session['input_action'], session['input_slot'])}


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    for name in ('package-manifest', 'harness', 'recovery'):
        parser.add_argument('--' + name, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    parser.add_argument('--quit-on-completion', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir()
            and not any(output.iterdir()), 'Use a new empty owned output directory.')
    inputs = {'source': pin(__file__, args.source_sha256),
              'harness': pin(args.harness, args.harness_sha256),
              'package_manifest': pin(args.package_manifest, args.package_manifest_sha256),
              'recovery': pin(args.recovery, args.recovery_sha256),
              'native12_report': pin(ROUND / 'native_original20_r13_12/original20_controls_report.json', REPORT_SHA),
              'native12_source': pin(ROUND / 'validate_original20_latest_saved_controls_r13.py', OLD_SOURCE_SHA),
              'native12_release': pin(ROUND / 'resource_release_X_NATIVE12_FAILED_GUN_VISIBILITY.json', RELEASE_SHA),
              'helper': pin(ROUND / 'original_cosha_control_round.py', HELPER_SHA)}
    require(Path(inputs['recovery']['path']) == RECOVERY.resolve()
            and inputs['recovery']['sha256'] == RECOVERY_SHA
            and inputs['harness']['sha256'] == R14_SHA
            and inputs['package_manifest']['sha256'] == MANIFEST_SHA
            and Path(inputs['harness']['path']) == ROUND / 'validate_original20_latest_saved_controls_r14.py',
            'Use the exact owned Native12 recovery, pinned .33 package and explicitly pinned R14 helper.')
    old_report, release = (document(inputs[key]['path']) for key in ('native12_report', 'native12_release'))
    require(old_report['completed'] is False and old_report['source_inputs']['source'] == inputs['native12_source']
            and old_report['Gun_Motion_UI_edit_Key_restore']['public_save_count'] == 0
            and 'Show the Right Target collection' in old_report['error']
            and release['report'] == inputs['native12_report'] and release['completed'] is False
            and release['retained_handle_natural_exit'] is True and release['native_exit_code'] == 0
            and release['owned_native_gone'] is True and release['process_termination_performed'] is False,
            'The recovery provenance must remain the failed Native12 pre-Save run with actual release.')
    for key, expected in (('prepared_report', PREPARED_SHA), ('clock_report', CLOCK_SHA),
                          ('snapshot_receipt', SNAPSHOT_SHA), ('protected_artist', ARTIST_SHA), ('seed', ARTIST_SHA)):
        row = old_report['source_inputs'][key]
        require(row['sha256'] == expected, 'Native12 input binding changed: ' + key)
        inputs[key] = pin(row['path'], expected)
    require(Path(inputs['protected_artist']['path']) == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve(),
            'Hash only the actual protected artist.')
    manifest = document(inputs['package_manifest']['path'])
    root = Path(manifest['source_root']).resolve()
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
            and manifest['version'] == '0.77.33' and len(manifest['files']) == 190
            and root == ROUND / 'package_0fa9adfa/source/character_designer'
            and all(manifest['files'].get(name) == value for name, value in RUNTIME_PINS.items()),
            'Require the exact six reviewed .33 runtime leaves in the complete pinned projection.')
    files = {}
    for relative, expected in manifest['files'].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and '__pycache__' not in path.parts, 'Invalid package leaf.')
        files[relative] = pin(path, expected)
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(files),
            'The frozen runtime has extra or missing files.')
    import bpy
    require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
            and len(bpy.context.window_manager.windows) == 1, 'Require one fresh isolated headful Blender 5.2 factory child.')
    require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules),
            'Another Character Designer runtime is loaded.')
    require(bpy.context.preferences.edit.use_global_undo
            and not bpy.context.preferences.filepaths.use_scripts_auto_execute,
            'Keep existing global Undo enabled and script autoexecution disabled; do not change preferences.')
    report = {'schema': 'x.validation.original20-recovery-gun-undo/1', 'completed': False,
        'scope': 'Authenticated D4CB recovery; .33 no-op numeric roundtrip, actual Gun edit/Save/publication, native Undo/Redo, exact final BF59 save/reopen/publication.',
        'source_inputs': inputs, 'pid': os.getpid(), 'native_execution_performed': True,
        'package_manifest_version': manifest['version'], 'package_manifest_file_count': len(files),
        'recovery_opened': False, 'seed_opened': False, 'artist_opened': False, 'artist_written': False,
        'original_artist_integration_verified': False, 'full_original_preservation_oracle_run': False,
        'reference_phases_run': False, 'reimport_performed': False, 'private_curve_writes': False,
        'transform_restore_or_second_Save_performed': False, 'Undo_Redo_performed': False,
        'Unity_Apply_verified': False, 'natural_exit_verified': False,
        'natural_exit_external_retained_handle_readback_required': True,
        'noop_numeric_roundtrip_verified': False, 'noop_Undo_restored_exact_BF59': False,
        'Gun_Undo_exact_BF59': False, 'Gun_Redo_exact_edited_Return': False,
        'final_Undo_exact_BF59': False, 'save_reopen_verified': False,
        'strict14_Return_and_twenty_scalar_publication_verified': False, 'no_QA_offset_remaining': False,
        'final_closed_Source_Body_motions_exact': False}
    report_path = output / 'original20_recovery_gun_undo_report.json'
    write(report_path, report)
    state = {'phase': 'admit', 'baseline': None}
    harness = load(inputs['harness']['path'], R14_SHA, 'native12_recovery_r14')
    helper = load(inputs['helper']['path'], HELPER_SHA, 'native12_recovery_protection7098')
    report['deferred_public_UI'] = list(harness.DEFERRED_PUBLIC_UI)
    package = load(root / '__init__.py', files['__init__.py']['sha256'], 'character_designer', package=True)
    require(tuple(package.bl_info['version']) == (0, 77, 33), 'Loaded runtime version mismatch.')
    package.register()
    for name in ('animation_worklist', 'animation_worklist_target', 'animation_worklist_fingerprint',
                 'animation_composition_weapon', 'unity_animation', 'unity_animation_rigging', 'unity_animation_original_inputs'):
        module = __import__('character_designer.' + name, fromlist=[name])
        require(Path(module.__file__).resolve() == root / (name + '.py'), 'Mixed runtime module: ' + name)
        setattr(package, name, module)
    backend, native = package.unity_animation_original_inputs, package.unity_animation_rigging
    probe = SimpleNamespace(bpy=bpy)
    for name in ('id', 'plain'):
        setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))

    def pair_identity(pair):
        return {'rig': probe.id(pair['rig']), 'scene': probe.id(pair['scene']),
            'actions': {side: probe.id(pair[side + '_action']) for side in ('source', 'custom')},
            'slots': {side: pair[side + '_slot'] for side in ('source', 'custom')},
            'source_uuid': pair['source_uuid'], 'custom_uuid': pair['capture']['newActionId'],
            'bindings': probe.plain(pair['capture']['bindings'])}

    def source_body_motions(pair):
        return {name: native._motion(pair[action], pair[slot]) for name, action, slot in (
            ('Source20', 'source_action', 'source_slot'), ('original_Custom_Body', 'body_action', 'body_slot'),
            ('original_Source_Body', 'body_source', 'body_source_slot'))}

    def display_identity(ctx, rig):
        display = package.bone_display
        return probe.plain(display._checkpoint(display._affected(ctx, rig)))

    def lifecycle(ctx, rig, label):
        # Cache first: current/seek/activate must not conceal a missing callback.
        cached = native.display_state(rig)
        require(cached is not None and cached['rig'] == rig and cached['scene'] == ctx.scene
                and cached['enabled'] and cached['original_controls_only'], 'Undo/Redo did not reacquire the Original20 cache.')
        callbacks = {name: sum(value is callback for value in getattr(bpy.app.handlers, name)) for name, callback in (
            ('load_post', native._reacquire), ('undo_post', native._reacquire), ('redo_post', native._reacquire),
            ('frame_change_post', native._frame), ('depsgraph_update_post', native._depsgraph))}
        require(all(count == 1 for count in callbacks.values()) and not native._HANDLER_ERRORS,
                'Owned lifecycle callbacks are missing, duplicate or failed.')
        report.setdefault('lifecycle_witnesses', []).append({'boundary': label, 'callbacks': callbacks,
            'cache_checked_before_current_or_manual_activate': True, 'fresh_timer_tick': True})

    def boundary(ctx, rig, session, label, *, exact=False, expected_dto=None, new_session=False):
        pair = session['original_inputs']
        identity, motions = pair_identity(pair), source_body_motions(pair)
        require(identity == state['pair_identity'] and motions == state['immutable_motions'],
                'An input identity/binding/weight or protected Source/Body motion changed.')
        require(new_session or session['owner'] == state['owner'], 'Undo/Redo changed the persistent session owner.')
        require(native._time(ctx, session) == 0. and ctx.scene.frame_current == state['frame'][0]
                and ctx.scene.frame_subframe == state['frame'][1], 'The exact frame-zero input phase changed.')
        dto = backend.capture_inputs(ctx, session)
        require(set(dto) == RETURN_FIELDS and len(dto['frames']) == 59, 'The strict14/BF59 Return changed shape.')
        if exact:
            harness.exact_initial_twenty(package, pair)
            require(dto == state['baseline'] and native._motion(pair['custom_action'], pair['custom_slot']) == state['baseline_motion'],
                    'Restored Input20/BF59 is not bit-exact; no tolerance applies to this gate.')
        if expected_dto is not None:
            require(dto == expected_dto, 'Native Redo did not restore the exact edited Return.')
        require(display_identity(ctx, rig) == state['display_identity'], 'Pre-test display and VIEW/REFS identity changed.')
        report.setdefault('motion_boundaries', []).append({'boundary': label, 'source_body_motions': motions,
            'pair_identity': identity, 'Source_Body_motions_exact': True, 'pair_and_weights_exact': True,
            'frame': list(state['frame']), 'native_time': 0., 'exact_initial_twenty_and_BF59': exact,
            'display_and_VIEW_REFS_exact': True})
        return dto

    def authenticate():
        require(bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=inputs['recovery']['path'], use_scripts=False, load_ui=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(), 'Authenticated recovery did not open.')
        report['recovery_opened'] = True
        # No saved RNA is retained in state; subsequent phases reacquire actual data.
        with harness.owning_context(bpy) as (ctx, rig):
            session = backend.current(rig)
            require(session is not None and 'original_inputs' in session, 'Persistent Original20 session is absent.')
            pair = session['original_inputs']
            for pair_key, input_key in (('prepared_report', 'prepared_report'), ('clock_certificate', 'clock_report'), ('snapshot_receipt', 'snapshot_receipt')):
                require(harness.same_pin(pair[pair_key], inputs[input_key]), 'Persistent evidence changed: ' + pair_key)
            require(pair['packet']['sha256'] == PACKET_SHA, 'The captured BF packet changed.')
            inputs['packet'] = pin(pair['packet']['path'], PACKET_SHA)
            packet = package.unity_animation.load_package(pair['packet']['path'])
            require(pair['capture'] == package.animation_rigging_contract.validate_capture(packet['rigging'], packet=packet)
                    and len(pair['capture']['frames']) == 59, 'Persisted BF59 capture changed.')
            harness.exact_initial_twenty(package, pair)
            report['Action_inventory'] = inventory(bpy, helper, pair, document(inputs['snapshot_receipt']['path']))
            require(session['enabled'] and session['tweak_enabled'] and session['edit_role'] == 'RIGGING'
                    and rig.mode == 'POSE' and rig.animation_data.use_tweak_mode and native._time(ctx, session) == 0.,
                    'Recovery lost its first-key Pose/Tweak context.')
            state['baseline'] = backend.capture_inputs(ctx, session)
            state['pair_identity'], state['immutable_motions'] = pair_identity(pair), source_body_motions(pair)
            state['baseline_motion'] = native._motion(pair['custom_action'], pair['custom_slot'])
            # Reapply fixed .33 before the Undo baseline; Body can stay hidden.
            session = backend.edit_controls(ctx, rig)
            state['owner'] = session['owner']
            state['frame'] = (ctx.scene.frame_current, ctx.scene.frame_subframe)
            state['display_identity'] = display_identity(ctx, rig)
            boundary(ctx, rig, session, 'fixed_33_prebaseline', exact=True)
            write(output / 'baseline_Return.json', state['baseline'])
            report['persistent_pair_and_exact_BF20_authenticated'] = True
        push_checkpoint(bpy, report, 'Original20 .33 before no-op Save')
        return 'noop_save'

    def noop_save():
        with harness.owning_context(bpy) as (ctx, rig):
            session = backend.current(rig)
            with temporary_body_display(bpy, ctx, rig, package, session, report, 'No-op public Save numeric roundtrip'):
                result = bpy.ops.character_designer.original_inputs_edit('EXEC_DEFAULT', False, focus_gun_motion=True)
                require(result == {'FINISHED'}, 'No-op public Edit failed.')
                record_public(report, 'character_designer.original_inputs_edit')
                require(backend.capture_inputs(ctx, backend.current(rig)) == state['baseline'], 'Edit changed stored baseline keys.')
                result = bpy.ops.character_designer.original_inputs_save('EXEC_DEFAULT', False)
                require(result == {'FINISHED'}, 'No-op public Save failed.')
                record_public(report, 'character_designer.original_inputs_save')
                current = backend.capture_inputs(ctx, backend.current(rig))
                write(output / 'noop_saved_Return.json', current)
                deltas = [numeric_delta(a, b) for a, b in zip(state['baseline']['frames'][0]['controls'], current['frames'][0]['controls'])]
                gate = (set(current) == RETURN_FIELDS and len(current['frames']) == 59
                    and {k:v for k,v in current.items() if k != 'frames'} == {k:v for k,v in state['baseline'].items() if k != 'frames'}
                    and current['frames'][1:] == state['baseline']['frames'][1:]
                    and all(d['position_max_component'] <= 1e-5 and d['hint_max_component'] <= 1e-5
                            and d['rotation_degrees'] <= .001 for d in deltas))
                report['noop_save'] = {'no_Target_or_Hint_edit_performed': True, 'baseline_exact': current == state['baseline'],
                    'differing_frames': [i for i,(a,b) in enumerate(zip(state['baseline']['frames'], current['frames'])) if a != b],
                    'native_time': 0., 'control_deltas': deltas, 'numeric_roundtrip_gate': gate,
                    'gate_limits': {'position_max_component': 1e-5, 'hint_max_component': 1e-5, 'rotation_degrees': .001},
                    'frames_1_through_58_exact': current['frames'][1:] == state['baseline']['frames'][1:],
                    'restored_BF59_gate_remains_exact': True}
            boundary(ctx, rig, backend.current(rig), 'no_op_saved')
        push_checkpoint(bpy, report, 'Original20 .33 after no-op Save')
        return 'noop_undo'

    def read_undo(label, flag, next_phase, *, redo=False):
        with harness.owning_context(bpy) as (ctx, rig):
            lifecycle(ctx, rig, label)
            session = backend.current(rig)
            boundary(ctx, rig, session, label, exact=not redo,
                expected_dto=state['gun_edited']['dto'] if redo else None)
            if redo:
                require(native._motion(session['input_action'], session['input_slot']) == state['gun_edited']['motion'],
                        'Redo changed the exact edited Custom20 motion.')
            report[flag] = True
        if label == 'noop_Undo':
            require(report['noop_save']['numeric_roundtrip_gate'], 'No-op Save failed the separate numeric decoder roundtrip gate.')
            report['noop_numeric_roundtrip_verified'] = True
            # Clear the no-op redo branch only after exact baseline readback.
            push_checkpoint(bpy, report, 'Original20 .33 before Gun edit')
        return next_phase

    def gun_edit():
        with harness.owning_context(bpy) as (ctx, rig):
            session = backend.current(rig)
            with temporary_body_display(bpy, ctx, rig, package, session, report, 'Gun public edit and edited Return'):
                state['gun_edited'] = exercise_gun_edit(bpy, ctx, rig, package, helper, state['baseline'], report,
                    edited_publication_destination=output / 'edited_gun_controls_Return.json')
            boundary(ctx, rig, backend.current(rig), 'Gun_edited_saved')
        push_checkpoint(bpy, report, 'Original20 .33 after Gun edit Save')
        return 'gun_undo'

    def close_save():
        with harness.owning_context(bpy) as (ctx, rig):
            boundary(ctx, rig, backend.current(rig), 'final_BF_before_Close', exact=True)
            result = bpy.ops.character_designer.original_inputs_close('EXEC_DEFAULT', False)
            require(result == {'FINISHED'} and backend.current(rig) is None and backend.PAIR_KEY in rig,
                    'Owned preview did not close with its pair retained.')
            record_public(report, 'character_designer.original_inputs_close')
            pair = backend._pair_validate(backend._pair(rig), files=True)
            harness.exact_initial_twenty(package, pair)
            require(pair_identity(pair) == state['pair_identity'] and source_body_motions(pair) == state['immutable_motions'],
                    'Close changed the persistent pair or protected motions.')
        clone = output / 'original20_controls_owned.blend'
        require(not clone.exists(), 'Do not overwrite a prior clone.')
        result = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', False, filepath=str(clone), copy=True, check_existing=False)
        require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(), 'Closed BF59 SaveCopy failed.')
        report['saved_clone'] = pin(clone, hashlib.sha256(clone.read_bytes()).hexdigest())
        return 'reopen'

    def reopen():
        clone = report['saved_clone']
        pin(clone['path'], clone['sha256'])
        require(bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=clone['path'], use_scripts=False, load_ui=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == Path(clone['path']), 'Actual saved clone did not reopen.')
        return 'reopened_readback'

    def reopened_readback():
        with harness.owning_context(bpy) as (ctx, rig):
            require(native.display_state(rig) is None and backend.current(rig) is None and backend.PAIR_KEY in rig,
                    'Saved closed pair did not reopen in its closed state.')
            pair = backend._pair_validate(backend._pair(rig), files=True)
            harness.exact_initial_twenty(package, pair)
            require(pair_identity(pair) == state['pair_identity'] and source_body_motions(pair) == state['immutable_motions'],
                    'Reopening changed input identities or Source/Body motions.')
            report['reopened_Action_inventory'] = inventory(bpy, helper, pair, document(inputs['snapshot_receipt']['path']))
            # Reactivate existing authenticated pair; never reimport any carrier.
            session = backend.edit_controls(ctx, rig)
            boundary(ctx, rig, session, 'reopened_BF59', exact=True, new_session=True)
            report['save_reopen_verified'] = True
            published = backend.publish_inputs(ctx, rig, str(output / 'captured_controls_Return.json'))
            require(set(published) == {'return', 'publication'}, 'Final publication did not return two pins.')
            for row in published.values(): pin(row['path'], row['sha256'])
            dto, publication = document(published['return']['path']), document(published['publication']['path'])
            require(dto == state['baseline'] and set(dto) == RETURN_FIELDS and publication['completed'] is True
                and publication['schema'] == backend.PUBLICATION_SCHEMA and publication['controlChannelCount'] == 20
                and publication['returnSha256'] == published['return']['sha256']
                and publication['sourceActionId'] == pair['source_uuid']
                and publication['targetInputActionId'] == pair['capture']['newActionId']
                and all(publication[field] == dto[field] for field in RETURN_FIELDS - {'schema', 'frames'})
                and all(publication[field] is True for field in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly')),
                'Final publication changed exact BF59/strict14/controls-only identities.')
            report['actual_controls_only_publication'] = published
            report['strict14_Return_and_twenty_scalar_publication_verified'] = True
            backend.close_owned(ctx, rig)
            pair = backend._pair_validate(backend._pair(rig), files=True)
            harness.exact_initial_twenty(package, pair)
            require(source_body_motions(pair) == state['immutable_motions'], 'Final Close changed Source/Body motions.')
            report['final_closed_Source_Body_motions_exact'] = True
            report['no_QA_offset_remaining'] = True
        return 'finish'

    def finish(error=None):
        if error is not None:
            report.update(completed=False, error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
            write(report_path, report)
            try:
                with harness.owning_context(bpy) as (ctx, rig):
                    session = backend.current(rig)
                    if session is not None:
                        current = backend.capture_inputs(ctx, session)
                        write(output / 'Return_after_failure.json', current)
                        report['failure_Return_equals_baseline'] = current == state['baseline']
            except Exception as read_error:
                report['failure_readback_error'] = type(read_error).__name__ + ': ' + str(read_error)
            try:
                allowed = {RECOVERY.resolve()}
                if 'saved_clone' in report: allowed.add(Path(report['saved_clone']['path']).resolve())
                require(bpy.data.filepath and Path(bpy.data.filepath).resolve() in allowed, 'Retain only an authenticated owned scene.')
                failure = output / 'failed_original20_recovery_gun_undo.blend'
                require(not failure.exists(), 'Never overwrite retained failure evidence.')
                active_path = Path(bpy.data.filepath).resolve()
                result = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', False, filepath=str(failure), copy=True, check_existing=False)
                require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == active_path, 'Failure SaveCopy failed.')
                report['failure_scene'] = pin(failure, hashlib.sha256(failure.read_bytes()).hexdigest())
            except Exception as save_error:
                report['failure_scene_error'] = type(save_error).__name__ + ': ' + str(save_error)
        try:
            for row in list(inputs.values()) + list(files.values()): pin(row['path'], row['sha256'])
            if 'saved_clone' in report: pin(report['saved_clone']['path'], report['saved_clone']['sha256'])
            report['input_files_unchanged'] = True
        except Exception as immutable_error:
            report['immutable_input_error'] = type(immutable_error).__name__ + ': ' + str(immutable_error)
            error = immutable_error
        required = ('noop_numeric_roundtrip_verified', 'noop_Undo_restored_exact_BF59', 'Gun_Undo_exact_BF59',
            'Gun_Redo_exact_edited_Return', 'final_Undo_exact_BF59', 'save_reopen_verified',
            'strict14_Return_and_twenty_scalar_publication_verified', 'no_QA_offset_remaining',
            'final_closed_Source_Body_motions_exact', 'input_files_unchanged')
        report['completed'] = error is None and all(report[field] is True for field in required)
        write(report_path, report)
        print('ORIGINAL20_RECOVERY_GUN_UNDO ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)
        if args.quit_on_completion:
            def quit_owned():
                observation = {'pid': os.getpid(), 'requested_from_timer': True,
                    'completed_report': report['completed'], 'natural_exit_still_external': True}
                try:
                    observation['operator_result'] = sorted(bpy.ops.wm.quit_blender('EXEC_DEFAULT', False))
                except Exception as quit_error:
                    observation['error'] = type(quit_error).__name__ + ': ' + str(quit_error)
                write(output / 'owned_quit_observation.json', observation)
                return None
            bpy.app.timers.register(quit_owned, first_interval=3., persistent=False)
        return None

    def tick():
        phase = state['phase']
        report['stage'] = phase
        write(report_path, report)
        print('ORIGINAL20_RECOVERY_STAGE ' + phase, flush=True)
        try:
            if phase == 'admit': next_phase = authenticate()
            elif phase == 'noop_save': next_phase = noop_save()
            elif phase in ('noop_undo', 'gun_undo', 'gun_final_undo'):
                native_undo_redo(bpy, report)
                next_phase = {'noop_undo': 'noop_readback', 'gun_undo': 'gun_undo_readback', 'gun_final_undo': 'gun_final_readback'}[phase]
            elif phase == 'noop_readback': next_phase = read_undo('noop_Undo', 'noop_Undo_restored_exact_BF59', 'gun_edit')
            elif phase == 'gun_edit': next_phase = gun_edit()
            elif phase == 'gun_undo_readback': next_phase = read_undo('Gun_Undo', 'Gun_Undo_exact_BF59', 'gun_redo')
            elif phase == 'gun_redo':
                native_undo_redo(bpy, report, redo=True)
                next_phase = 'gun_redo_readback'
            elif phase == 'gun_redo_readback': next_phase = read_undo('Gun_Redo', 'Gun_Redo_exact_edited_Return', 'gun_final_undo', redo=True)
            elif phase == 'gun_final_readback': next_phase = read_undo('final_Undo', 'final_Undo_exact_BF59', 'close_save')
            elif phase == 'close_save': next_phase = close_save()
            elif phase == 'reopen': next_phase = reopen()
            elif phase == 'reopened_readback': next_phase = reopened_readback()
            elif phase == 'finish': return finish()
            else: raise RuntimeError('Unknown owned phase: ' + phase)
            state['phase'] = next_phase
            write(report_path, report)
            return .1
        except Exception as error:
            return finish(error)

    # This one owned timer opens two authenticated files. Returning None ends it.
    bpy.app.timers.register(tick, first_interval=.1, persistent=True)


if __name__ == '__main__':
    main()
