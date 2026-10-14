"""Serial, disposable full-artist regression for direct original-Rig Worklists.

Root launches this against a copy-only backup after checking memory. This script
never opens or saves artist X.blend and never changes Unity files/manifests.
"""
import argparse
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validation_preservation import (asset_snapshot, changes, digest,
                                     evaluate_forearm_runtime, forearm_runtime_output_snapshot,
                                     protected_preview_changes)
from validation_armature_users import legitimate_guards, native_guard_fixtures

EVIDENCE = Path(__file__).resolve().parent


def phase(report, name, operation):
    """Coarse flushed progress and wall/CPU timing; no per-frame logging."""
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    row = {'completed': False}
    report.setdefault('phase_timings', {})[name] = row
    print('DIRECT_RETURN_PHASE_START ' + name, flush=True)
    try:
        result = operation()
        row['completed'] = True
        return result
    except Exception as exc:
        row.update(error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        row.update(wall_seconds=time.perf_counter() - wall_start,
                   cpu_seconds=time.process_time() - cpu_start)
        print('DIRECT_RETURN_PHASE_END ' + json.dumps({'phase': name, **row}, ensure_ascii=False), flush=True)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(EVIDENCE):
        raise ValueError('All isolated inputs/results must remain within ' + str(EVIDENCE))
    if path.name.lower() == 'x.blend':
        raise ValueError('This harness must never open or save artist X.blend.')
    return path


def verify_runtime_projection(cd):
    manifest_path = EVIDENCE / 'release_projection_07724.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    expected = Path(manifest['source_root']).resolve()
    actual = Path(cd.__file__).resolve().parent
    owned = {'unity_animation.py', 'unity_animation_controls.py', 'unity_animation_dress.py',
             'animation_worklist.py', 'animation_worklist_ui.py', 'animation_worklist_target.py',
             'limb_ik.py', 'root_control.py', 'torso_controls.py', 'spine_ik_fk.py',
             'eye_controls.py', 'foot_controls.py', 'bone_display.py', 'bone_collections.py'}
    provenance = manifest['source_provenance']
    if (actual != expected or tuple(cd.bl_info['version']) != (0, 77, 24)
            or manifest['version'] != '0.77.24'
            or set(provenance['canonical_overlays']) != owned
            or provenance['init_version_only'] is not True
            or provenance['baseline_sha256'] !=
            'dd2d4903a7c45b5ed7a3b442e132dd04d13e34fbca099864eaaada08e0165f1e'):
        raise AssertionError('Runtime does not use the expected narrow 0.77.24 release projection.')
    mismatches = [name for name, expected_hash in manifest['files'].items()
                  if not (actual / name).is_file() or file_hash(actual / name) != expected_hash]
    if mismatches:
        raise AssertionError('Frozen runtime projection hash mismatch: ' + ', '.join(mismatches))
    return {'manifest': str(manifest_path), 'manifest_sha256': file_hash(manifest_path),
            'file_count': len(manifest['files']), 'all_file_hashes_match': True,
            'owned_overlays': sorted(owned)}


def select_rig(scene, rig):
    bpy.context.window.scene = scene
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.context.view_layer.update()


def old_worklist_proofs(fp):
    result = []
    for scene in bpy.data.scenes:
        saved = scene.character_designer_animation_worklist
        for item in saved.items:
            source = fp.fingerprint_action(item.source_action, item.source_slot) if item.source_action else None
            custom = fp.fingerprint_action(item.custom_action, item.custom_slot) if item.custom_action else None
            equal = bool(source and custom and source['fingerprint_known'] and custom['fingerprint_known']
                         and source['action_fingerprint'] == custom['action_fingerprint'])
            result.append({'scene': scene.name, 'item': item.name, 'item_id': item.item_id,
                'source': item.source_action, 'source_slot': item.source_slot, 'source_proof': source,
                'custom': item.custom_action, 'custom_slot': item.custom_slot, 'custom_proof': custom,
                'entire_action_equal': equal, 'source_file': item.source_file,
                'source_file_hash': file_hash(item.source_file) if Path(item.source_file).is_file() else None})
    return result


def public_proofs(rows):
    return [{**{key: value for key, value in row.items() if key not in {'source', 'custom'}},
             'source': row['source'].name if row['source'] else None,
             'custom': row['custom'].name if row['custom'] else None} for row in rows]


def verify_old_actions(rows, fp):
    for row in rows:
        for side in ('source', 'custom'):
            action = row[side]
            if action:
                if fp.fingerprint_action(action, row[side + '_slot']) != row[side + '_proof']:
                    raise AssertionError('Existing ' + side + ' Action content changed: ' + action.name)
        if row['source_file_hash'] is not None and file_hash(row['source_file']) != row['source_file_hash']:
            raise AssertionError('Existing read-only Source library file changed.')


def nla_content(rig):
    ad = rig.animation_data
    if not ad:
        return []
    return [{'name': track.name, 'mute': track.mute, 'is_solo': track.is_solo,
             'strips': [{'name': strip.name, 'action': getattr(strip.action, 'name', None),
                         **{field: getattr(strip, field) for field in
                            ('frame_start', 'frame_end', 'action_frame_start', 'action_frame_end',
                             'blend_type', 'extrapolation', 'influence', 'scale', 'repeat', 'mute')}}
                        for strip in track.strips]} for track in ad.nla_tracks]


def verify_recovery_snapshot(previous, current):
    fields = [key for key in previous if key != 'pose']
    if any(previous[key] != current.get(key) for key in fields):
        raise AssertionError('Recovery changed Scene timing, prior Action/NLA settings or auto-key.')
    if previous['pose'].keys() != current['pose'].keys():
        raise AssertionError('Recovery changed pose bone names.')
    maximum = 0.0
    for name, expected in previous['pose'].items():
        actual = current['pose'][name]
        if expected['rotation_mode'] != actual['rotation_mode']:
            raise AssertionError('Recovery changed rotation mode: ' + name)
        for field, values in expected.items():
            if field != 'rotation_mode':
                maximum = max(maximum, *(abs(a - b) for a, b in zip(values, actual[field])))
    if maximum > 4.0e-4:
        raise AssertionError('Recovery changed previous artist pose channels beyond official return tolerance.')
    return {'previous_scene_animation_settings_restored': True,
            'maximum_previous_pose_channel_difference': maximum, 'channel_tolerance': 4.0e-4}


def require_assets(scene, rig, ua, before, original_data, original_rest, authored):
    after = asset_snapshot(scene, rig, ua)
    raw_changed = changes(before, after)
    changed = protected_preview_changes(before, after)
    if digest(ua._rest_state(original_data)) != original_rest:
        raise AssertionError('Protected original Armature data changed.')
    if changed == ['rest'] and rig.data is not original_data:
        if set(rig.data.bones.keys()) != set(original_data.bones.keys()):
            raise AssertionError('Motion editing data changed bone names.')
        if not all(ua._same_rest_bone(original_data.bones[b.name], b) for b in rig.data.bones):
            raise AssertionError('Motion data changed Rest positions, axes, parent graph or other inheritance.')
        connect_changes = [b.name for b in rig.data.bones
                           if b.use_connect != original_data.bones[b.name].use_connect]
        if any(name not in authored or rig.data.bones[name].use_connect for name in connect_changes):
            raise AssertionError('Unexpected connected-bone editing flag change.')
        return {'preserved': True, 'temporary_data_copy': True,
                'only_motion_connected_flags_relaxed': connect_changes,
                'raw_component_changes': raw_changed,
                'display_comparison': 'Exact official Body mode membership and native owned FK binding proof; '
                                      'all widget assets, colors and other collection/binding fields remain exact.',
                'assets': after}
    if changed:
        raise AssertionError('Original character assets changed: ' + ', '.join(changed))
    return {'preserved': True, 'temporary_data_copy': False, 'raw_component_changes': raw_changed,
            'display_comparison': 'Only authenticated mode-derived Body membership and owned FK binding output '
                                  'are classified; Restore still requires every raw component to match.',
            'assets': after}


def samples(scene, rig, packet, mapping, ua, tolerance):
    delegated = set(getattr(mapping.controls, 'delegated_names', ())) if mapping.controls else set()
    authored = set(mapping.indices) - delegated
    if len(authored) != 184 or len(delegated) != 33 or len(packet['frames']) != 59:
        raise AssertionError('Expected this model packet: 184 authored + 33 delegated Dress bones, 59 frames.')
    fps = scene.render.fps / scene.render.fps_base
    rows = []
    worst = {'matrix_error': 0.0}
    worst_head = {'max_head_error_mm': 0.0}
    for index, frame in enumerate(packet['frames']):
        frame_value = 1.0 + float(frame['time']) * fps
        ua._set_frame(scene, frame_value)
        bpy.context.view_layer.update()
        runtime = evaluate_forearm_runtime(scene, rig)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = rig.evaluated_get(depsgraph)
        expected = ua.expected_world_matrices(rig, packet, index,
                    unit_scale=scene.unit_settings.scale_length, mapping=mapping)
        frame_worst = 0.0
        frame_head_mm = 0.0
        worst_bone = None
        worst_head_bone = None
        for name in authored:
            actual = evaluated.matrix_world @ evaluated.pose.bones[name].matrix
            desired = expected[name]
            if not all(math.isfinite(value) for matrix in (actual, desired) for row in matrix for value in row):
                raise AssertionError(f'{name} has a non-finite evaluated matrix at sample {index}.')
            error = max(abs(actual[r][c] - desired[r][c]) for r in range(4) for c in range(4))
            head_mm = (actual.translation - desired.translation).length * scene.unit_settings.scale_length * 1000.0
            if not math.isfinite(head_mm):
                raise AssertionError(f'{name} has a non-finite head error at sample {index}.')
            if head_mm > frame_head_mm:
                frame_head_mm, worst_head_bone = head_mm, name
            if error > frame_worst:
                frame_worst, worst_bone = error, name
            if error > tolerance:
                raise AssertionError(f'{name} does not match authored sample {index}: {error:.8g}.')
        row = {'index': index, 'packet_time': frame['time'], 'blender_frame': frame_value,
               'matrix_error': frame_worst, 'max_head_error_mm': frame_head_mm,
               'worst_bone': worst_bone, 'worst_head_bone': worst_head_bone,
               'forearm_runtime': runtime}
        rows.append(row)
        if frame_worst > worst['matrix_error']:
            worst = row
        if frame_head_mm > worst_head['max_head_error_mm']:
            worst_head = {'index': index, 'packet_time': frame['time'], 'blender_frame': frame_value,
                          'max_head_error_mm': frame_head_mm, 'bone': worst_head_bone}
    return {'scope': 'Every packet sample; exact comparison only for authored Body/Hair/eye/finger bones. '
                     'Validated static-package Dress remains on original manual solves.',
            'authored_count': len(authored), 'delegated_count': len(delegated),
            'sample_count': len(rows), 'matrix_tolerance': tolerance, 'worst': worst,
            'maximum_head_error': worst_head,
            'forearm_runtime_checked_all_samples': True, 'frames': rows}, authored


def save_copy(path):
    result = bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False, copy=True)
    if 'FINISHED' not in result or not path.is_file():
        raise RuntimeError('Blender did not confirm isolated result save.')
    return {'path': str(path), 'result': sorted(result), 'sha256': file_hash(path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--addon-root', required=True)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--packet', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--active-output', required=True)
    parser.add_argument('--restored-output', required=True)
    parser.add_argument('--readopted-output')
    parser.add_argument('--matrix-tolerance', type=float, default=2.0e-4)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    input_path, report_path = safe_path(args.input), safe_path(args.report)
    active_output, restored_output = safe_path(args.active_output), safe_path(args.restored_output)
    readopted_output = safe_path(args.readopted_output or str(active_output.with_name('readopted_isolated.blend')))
    if len({input_path, active_output, restored_output, readopted_output, report_path}) != 5:
        raise ValueError('Input, report, active, restored and re-adopted output paths must differ.')
    input_hash, packet_hash = file_hash(input_path), file_hash(args.packet)
    report = {'schema': 'x.validation.direct-original-rig-return/1', 'completed': False,
              'input': str(input_path), 'input_sha256': input_hash,
              'packet': args.packet, 'packet_sha256': packet_hash,
              'operation': 'Disposable backup only; no artist or Unity mutations.'}
    wall_started, cpu_started = time.perf_counter(), time.process_time()
    try:
        addon_root = Path(args.addon_root).resolve()
        sys.path.insert(0, str(addon_root))
        cd = importlib.import_module('character_designer')
        if not Path(cd.__file__).resolve().is_relative_to(addon_root):
            raise RuntimeError('Unexpected Character Designer runtime root.')
        report['runtime_projection'] = verify_runtime_projection(cd)
        cd.register()
        ua = importlib.import_module('character_designer.unity_animation')
        worklist = importlib.import_module('character_designer.animation_worklist')
        target = importlib.import_module('character_designer.animation_worklist_target')
        original = importlib.import_module('character_designer.body_original_mode')
        fp = importlib.import_module('character_designer.animation_worklist_fingerprint')
        report['runtime'] = {'blender': bpy.app.version_string, 'addon': list(cd.bl_info['version']),
                             'addon_path': cd.__file__, 'module_sha256':
                             {m.__name__: file_hash(m.__file__) for m in (ua, worklist, target, fp)}}
        datafiles = Path(bpy.utils.user_resource('DATAFILES', create=True)).resolve()
        short_cache = EVIDENCE.parent / 'dr24cache'
        if not datafiles.is_relative_to(EVIDENCE) and datafiles != short_cache:
            raise RuntimeError('Set BLENDER_USER_DATAFILES to this task validation cache before launch.')
        report['isolated_source_cache_root'] = str(datafiles)
        pre_deferral = safe_path(str(EVIDENCE / 'active_before_bake_deferral.blend'))
        if not pre_deferral.is_file():
            raise AssertionError('Preserved pre-deferral active save is required for baked-channel equality proof.')
        pre_deferral_hash = file_hash(pre_deferral)
        phase(report, 'pre_deferral_reference_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(pre_deferral), use_scripts=False, load_ui=False))
        previous_items = bpy.data.scenes['Scene'].character_designer_animation_worklist.items
        previous_custom = [entry for entry in previous_items
                           if entry.rig and entry.rig.name == 'CoshaRig' and entry.custom_action]
        if len(previous_custom) != 1:
            raise AssertionError('Preserved pre-deferral save needs exactly one original-Rig Custom Action.')
        prior_item = previous_custom[0]
        pre_deferral_proof = fp.fingerprint_action(prior_item.custom_action, prior_item.custom_slot)
        if not pre_deferral_proof['fingerprint_known']:
            raise AssertionError('Pre-deferral selected-slot Action content proof is unknown.')
        report['pre_deferral_baked_channels'] = {
            'file': str(pre_deferral), 'file_sha256': pre_deferral_hash,
            'custom_display_name': prior_item.custom_action.name,
            'custom_slot': prior_item.custom_slot, 'proof': pre_deferral_proof,
            'policy': 'Complete selected-slot motion hash excludes Action display name, library identity '
                      'and native slot handle; same packet/baking controls must retain exact channel content.'}
        phase(report, 'baseline_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(input_path), use_scripts=False, load_ui=False))
        scene, rig = bpy.data.scenes.get('Scene'), bpy.data.objects.get('CoshaRig')
        if scene is None or rig is None or rig.name not in scene.objects:
            raise RuntimeError('Full backup must contain original Scene and CoshaRig.')
        select_rig(scene, rig)
        old_rows = old_worklist_proofs(fp)
        report['existing_worklists'] = public_proofs(old_rows)
        if any(not row['entire_action_equal'] for row in old_rows):
            raise RuntimeError('Existing Custom edits require a world-motion transfer before replacement; this baseline harness refuses raw curve copying.')
        report['original_forearm_runtime_before'] = evaluate_forearm_runtime(scene, rig)
        before = asset_snapshot(scene, rig, ua)
        original_data, original_data_name = rig.data, rig.data.name
        original_rest = digest(ua._rest_state(original_data))
        previous_action = rig.animation_data.action if rig.animation_data else None
        previous_action_name = previous_action.name if previous_action else None
        previous_slot = rig.animation_data.action_slot.handle if rig.animation_data and rig.animation_data.action_slot else None
        previous_original_active = original.active(rig)
        previous_original_session = rig.get(original.SESSION)
        previous_snapshot, previous_nla = ua._snapshot(bpy.context, rig), nla_content(rig)
        report['original_assets_before'] = before
        saved = worklist.connect(bpy.context, args.workspace)
        if scene.character_designer_setup.rig is not rig:
            raise AssertionError('Existing Main Rig is not the original target.')
        result = phase(report, 'first_adopt', lambda: target.adopt_main_rig(bpy.context))
        report['adoption_result_type'] = type(result).__name__
        report['adopted'] = bool(target.is_adopted(rig))
        if saved.rig is not rig or not report['adopted'] or original.active(rig):
            raise AssertionError('Adoption did not use Main Rig or safely leave Original mode.')
        report['official_leave_forearm_runtime'] = evaluate_forearm_runtime(scene, rig)
        report['forearm_target_transition'] = {
            'before': report['original_forearm_runtime_before'],
            'after_official_leave': report['official_leave_forearm_runtime'],
            'rule': 'Only target follows the official current-mode resolver. Every other calibration '
                    'and ownership field remains protected exactly; raw Rest signatures have no tolerance exception.'}
        packet = ua.load_package(args.packet)
        mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
        report['strict_mapping'] = {'mapped': len(mapping.indices), 'error_metres': mapping.error_metres}
        ready = [row for row in saved.catalog if row.ready]
        if len(ready) != 1:
            raise AssertionError('This isolated artist packet expects exactly one prepared Walk_N catalog row.')
        item = phase(report, 'worklist_add', lambda: worklist.add(bpy.context, ready[0].clip_key))
        if bpy.context.scene is not scene or item.rig is not rig or saved.rig is not rig:
            raise AssertionError('Direct add created or chose another Scene/Rig.')
        if item.source_action.library is None or item.custom_action.library is not None:
            raise AssertionError('Read-only Source / editable Custom lifecycle was lost.')
        phase(report, 'first_custom_activate', lambda: worklist.activate(bpy.context, item.item_id, 'CUSTOM'))
        report['custom_samples'], authored = phase(report, 'custom_samples_59',
            lambda: samples(scene, rig, packet, mapping, ua, args.matrix_tolerance))
        report['original_assets_while_active'] = require_assets(scene, rig, ua, before, original_data, original_rest, authored)
        verify_old_actions(old_rows, fp)
        report['old_source_custom_preserved'] = True
        phase(report, 'first_source_activate', lambda: worklist.activate(bpy.context, item.item_id, 'SOURCE'))
        report['source_samples'], _ = phase(report, 'source_samples_59',
            lambda: samples(scene, rig, packet, mapping, ua, args.matrix_tolerance))
        worklist.activate(bpy.context, item.item_id, 'CUSTOM')
        item_id = item.item_id
        report['first_active_native_control_guards'] = legitimate_guards(bpy.context, rig)
        custom_proof = fp.fingerprint_action(item.custom_action, item.custom_slot)
        source_proof = fp.fingerprint_action(item.source_action, item.source_slot)
        if not custom_proof['fingerprint_known'] or not source_proof['fingerprint_known']:
            raise AssertionError('The new full selected-slot Action content could not be proven complete.')
        if custom_proof['action_fingerprint'] != source_proof['action_fingerprint']:
            raise AssertionError('Fresh Source/Custom Actions have different complete motion content.')
        if custom_proof['action_fingerprint'] != pre_deferral_proof['action_fingerprint']:
            raise AssertionError('Clone-only corrective deferral changed complete baked selected-slot motion content.')
        report['clone_bake_deferral_motion_unchanged'] = True
        report['new_custom_complete_motion_proof'] = custom_proof
        report['active_save'] = phase(report, 'active_save', lambda: save_copy(active_output))
        phase(report, 'active_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(active_output), use_scripts=False, load_ui=False))
        scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
        select_rig(scene, rig)
        saved = scene.character_designer_animation_worklist
        item = worklist._item(saved, item_id)
        if not target.is_adopted(rig) or item.rig is not rig:
            raise AssertionError('Persisted Main Rig adoption did not survive reopening.')
        if fp.fingerprint_action(item.custom_action, item.custom_slot) != custom_proof:
            raise AssertionError('Custom content changed after saving/reopening.')
        report['persistent_adoption_reopened'] = True
        mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
        worklist.activate(bpy.context, item_id, 'CUSTOM')
        report['reopened_samples'], _ = phase(report, 'reopened_samples_59',
            lambda: samples(scene, rig, packet, mapping, ua, args.matrix_tolerance))
        phase(report, 'first_restore', lambda: target.restore_main_rig(bpy.context))
        if target.is_adopted(rig) or original.active(rig) != previous_original_active:
            raise AssertionError('Persistent recovery did not restore previous artist mode.')
        restored_action = rig.animation_data.action if rig.animation_data else None
        restored_name = restored_action.name if restored_action else None
        restored_slot = rig.animation_data.action_slot.handle if rig.animation_data and rig.animation_data.action_slot else None
        if (restored_name, restored_slot) != (previous_action_name, previous_slot):
            raise AssertionError('Recovery failed to restore previous Action/slot.')
        if rig.get(original.SESSION) != previous_original_session:
            raise AssertionError('Recovery failed to restore the exact prior Original transaction record.')
        if nla_content(rig) != previous_nla:
            raise AssertionError('Recovery modified prior NLA tracks/strips.')
        report['recovery_snapshot'] = verify_recovery_snapshot(previous_snapshot, ua._snapshot(bpy.context, rig))
        if rig.data.name != original_data_name:
            raise AssertionError('Recovery failed to restore original Armature data.')
        after_restore = asset_snapshot(scene, rig, ua)
        if changes(before, after_restore):
            raise AssertionError('Original assets differ after persistent recovery: ' + ', '.join(changes(before, after_restore)))
        report['recovery_assets'] = after_restore
        report['recovery_forearm_runtime'] = evaluate_forearm_runtime(scene, rig)
        if (scene.frame_current + scene.frame_subframe != before['runtime_generated_outputs']['frame']):
            raise AssertionError('Recovered generated outputs were compared at a different pose frame.')
        report['recovery_generated_output_comparison'] = {
            'same_restored_frame': True,
            'before': before['runtime_generated_outputs'],
            'after': forearm_runtime_output_snapshot(scene, rig),
            'note': 'Derived output geometry is recorded at the recovered pose; protected authored geometry '
                    'and exact calibration/ownership records are compared independently.'}
        report['previous_action_slot_restored'] = True
        report['persistent_original_mode_restored'] = previous_original_active
        try:
            worklist.activate(bpy.context, item_id, 'CUSTOM')
        except ValueError as exc:
            report['activation_after_restore_blocked'] = str(exc)
        else:
            raise AssertionError('Activation after recovery must require Main Rig re-adoption.')
        report['restored_save'] = phase(report, 'restored_save', lambda: save_copy(restored_output))
        phase(report, 'restored_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(restored_output), use_scripts=False, load_ui=False))
        scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
        select_rig(scene, rig)
        if target.is_adopted(rig) or original.active(rig) != previous_original_active:
            raise AssertionError('Restored state changed after another reopening.')
        if changes(before, asset_snapshot(scene, rig, ua)):
            raise AssertionError('Recovered original assets changed after another reopening.')
        report['persistent_recovery_reopened'] = True
        report['restored_native_ownership_guard_fixtures'] = phase(report, 'restored_native_ownership_guards',
            lambda: native_guard_fixtures(bpy.context, scene, rig))
        if changes(before, asset_snapshot(scene, rig, ua)):
            raise AssertionError('Restored native guard fixtures changed protected original assets.')
        saved = scene.character_designer_animation_worklist
        item = worklist._item(saved, item_id)
        if fp.fingerprint_action(item.custom_action, item.custom_slot) != custom_proof:
            raise AssertionError('Retained Custom content changed after recovery and reopening.')
        try:
            worklist.activate(bpy.context, item_id, 'CUSTOM')
        except ValueError as exc:
            report['activation_after_reopened_restore_blocked'] = str(exc)
        else:
            raise AssertionError('Reopened restored worklist activated without Main Rig re-adoption.')
        readopt_original_data = rig.data
        readopt_original_rest = digest(ua._rest_state(readopt_original_data))
        if readopt_original_rest != original_rest:
            raise AssertionError('Original Rest changed before Main Rig re-adoption.')
        phase(report, 'retained_custom_readopt', lambda: target.adopt_main_rig(bpy.context))
        if not target.is_adopted(rig) or original.active(rig) or saved.rig is not rig:
            raise AssertionError('Re-adoption failed to restore Main Rig ownership.')
        worklist.activate(bpy.context, item_id, 'CUSTOM')
        item = worklist._item(saved, item_id)
        if item.rig is not rig or fp.fingerprint_action(item.custom_action, item.custom_slot) != custom_proof:
            raise AssertionError('Re-adoption replaced or changed retained Custom motion.')
        report['readopted_native_control_guards'] = legitimate_guards(bpy.context, rig)
        mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
        report['readopted_samples'], authored = phase(report, 'readopted_samples_59',
            lambda: samples(scene, rig, packet, mapping, ua, args.matrix_tolerance))
        report['readopted_assets'] = require_assets(scene, rig, ua, before, readopt_original_data,
                                                   readopt_original_rest, authored)
        report['readopted_save'] = phase(report, 'readopted_save', lambda: save_copy(readopted_output))
        phase(report, 'readopted_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(readopted_output), use_scripts=False, load_ui=False))
        scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
        select_rig(scene, rig)
        saved = scene.character_designer_animation_worklist
        item = worklist._item(saved, item_id)
        if not target.is_adopted(rig) or item.rig is not rig:
            raise AssertionError('Re-adopted Main Rig state did not survive another reopening.')
        report['readopted_reopened_native_control_guards'] = legitimate_guards(bpy.context, rig)
        if fp.fingerprint_action(item.custom_action, item.custom_slot) != custom_proof:
            raise AssertionError('Retained Custom changed after re-adopted save/reopen.')
        worklist.activate(bpy.context, item_id, 'CUSTOM')
        mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
        report['readopted_reopened_samples'], _ = phase(report, 'readopted_reopened_samples_59',
            lambda: samples(scene, rig, packet, mapping, ua, args.matrix_tolerance))
        report['persistent_readoption_reopened'] = True
        phase(report, 'second_restore', lambda: target.restore_main_rig(bpy.context))
        if target.is_adopted(rig) or original.active(rig) != previous_original_active:
            raise AssertionError('Second recovery did not restore prior artist mode.')
        action = rig.animation_data.action if rig.animation_data else None
        slot = rig.animation_data.action_slot.handle if rig.animation_data and rig.animation_data.action_slot else None
        if (action.name if action else None, slot) != (previous_action_name, previous_slot):
            raise AssertionError('Second recovery changed the prior Action/slot.')
        if rig.get(original.SESSION) != previous_original_session or nla_content(rig) != previous_nla:
            raise AssertionError('Second recovery changed Original transaction or NLA records.')
        if rig.data.name != original_data_name or digest(ua._rest_state(rig.data)) != original_rest:
            raise AssertionError('Second recovery failed to return the protected original Armature data.')
        report['second_recovery_snapshot'] = verify_recovery_snapshot(previous_snapshot, ua._snapshot(bpy.context, rig))
        if changes(before, asset_snapshot(scene, rig, ua)):
            raise AssertionError('Original protected assets changed after second persistent recovery.')
        report['second_recovery_forearm_runtime'] = evaluate_forearm_runtime(scene, rig)
        report['second_restored_native_control_guards'] = legitimate_guards(bpy.context, rig)
        if scene.frame_current + scene.frame_subframe != before['runtime_generated_outputs']['frame']:
            raise AssertionError('Second recovery generated-output comparison uses a different pose frame.')
        report['second_recovery_completed'] = True
        report['completed'] = True
    except Exception as exc:
        report['error_type'], report['error'], report['traceback'] = type(exc).__name__, str(exc), traceback.format_exc()
    finally:
        report['total_elapsed_wall_seconds'] = time.perf_counter() - wall_started
        report['total_elapsed_cpu_seconds'] = time.process_time() - cpu_started
        report['input_file_unchanged'] = file_hash(input_path) == input_hash
        report['packet_file_unchanged'] = file_hash(args.packet) == packet_hash
        if 'pre_deferral_baked_channels' in report:
            reference = report['pre_deferral_baked_channels']
            report['pre_deferral_reference_file_unchanged'] = file_hash(reference['file']) == reference['file_sha256']
            if not report['pre_deferral_reference_file_unchanged']:
                report['completed'] = False
        report['completed'] = bool(report['completed'] and report['input_file_unchanged'] and report['packet_file_unchanged'])
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        print('DIRECT_RETURN_ISOLATED ' + json.dumps({key: report.get(key) for key in
            ('completed', 'error_type', 'error', 'input_file_unchanged', 'packet_file_unchanged',
             'persistent_adoption_reopened', 'persistent_recovery_reopened',
             'persistent_readoption_reopened', 'second_recovery_completed',
             'total_elapsed_wall_seconds', 'total_elapsed_cpu_seconds')}, ensure_ascii=False), flush=True)
    if not report['completed']:
        raise RuntimeError(report.get('error', 'Isolated regression did not complete.'))


if __name__ == '__main__':
    main()
