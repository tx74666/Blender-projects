"""Root-launched disposable resume: authenticated retained Custom re-adoption.

No fresh bake, artist save/reload, Unity action or external manifest mutation.
Uses the same motion, asset, finite-value and Forearm checks as the full test.
"""
import argparse
import importlib
import json
from pathlib import Path
import sys
import time
import traceback

import bpy

EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(EVIDENCE))
import verify_direct_return_isolated as full
from validation_preservation import asset_snapshot, changes, digest, evaluate_forearm_runtime
from validation_armature_users import legitimate_guards, native_guard_fixtures


def require_original_state(context, scene, rig, expected, ua, original):
    if original.active(rig) != expected['original_active'] or rig.get(original.SESSION) != expected['original_session']:
        raise AssertionError('Recovery changed the retained artist Original transaction.')
    action = rig.animation_data.action if rig.animation_data else None
    slot = rig.animation_data.action_slot.handle if rig.animation_data and rig.animation_data.action_slot else None
    if (action.name if action else None, slot) != (expected['action'], expected['slot']):
        raise AssertionError('Recovery changed the artist Action/slot.')
    if rig.data.name != expected['data_name'] or digest(ua._rest_state(rig.data)) != expected['rest_sha256']:
        raise AssertionError('Recovery changed the exact protected original Armature Rest/reference.')
    if full.nla_content(rig) != expected['nla']:
        raise AssertionError('Recovery changed artist NLA tracks/strips.')
    snapshot = full.verify_recovery_snapshot(expected['snapshot'], ua._snapshot(context, rig))
    runtime = evaluate_forearm_runtime(scene, rig)
    assets = asset_snapshot(scene, rig, ua)
    changed = changes(expected['assets'], assets)
    if changed:
        raise AssertionError('Recovered protected assets differ: ' + ', '.join(changed))
    if scene.frame_current + scene.frame_subframe != expected['assets']['runtime_generated_outputs']['frame']:
        raise AssertionError('Recovered generated outputs are recorded at a different pose frame.')
    return {'protected_assets': assets, 'pose_snapshot': snapshot, 'forearm_runtime': runtime}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--baseline', default=str(EVIDENCE / 'artist_before_direct_return.blend'))
    parser.add_argument('--addon-root', required=True)
    parser.add_argument('--packet', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--active-output', default=str(EVIDENCE / 'readopted_resume_isolated.blend'))
    parser.add_argument('--restored-output', default=str(EVIDENCE / 'readopt_restored_resume_isolated.blend'))
    parser.add_argument('--matrix-tolerance', type=float, default=2e-4)
    parser.add_argument('--skip-native-guard-fixtures', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, baseline, report_path, active_output, restored_output = (
        full.safe_path(value) for value in (args.input, args.baseline, args.report,
                                            args.active_output, args.restored_output))
    if len({source, baseline, report_path, active_output, restored_output}) != 5:
        raise ValueError('Inputs, report and isolated outputs must all differ.')
    source_hash, baseline_hash, packet_hash = (full.file_hash(path) for path in (source, baseline, args.packet))
    report = {'schema': 'x.validation.retained-original-rig-readopt-resume/1', 'completed': False,
              'input': str(source), 'input_sha256': source_hash,
              'baseline': str(baseline), 'baseline_sha256': baseline_hash,
              'packet': str(args.packet), 'packet_sha256': packet_hash,
              'scope': 'Disposable saved restored scene only; retained Action, no fresh baking or artist/Unity mutation.'}
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    try:
        addon_root = Path(args.addon_root).resolve()
        sys.path.insert(0, str(addon_root))
        cd = importlib.import_module('character_designer')
        if not Path(cd.__file__).resolve().is_relative_to(addon_root):
            raise AssertionError('Unexpected projected runtime root.')
        report['runtime_projection'] = full.verify_runtime_projection(cd)
        cd.register()
        ua = importlib.import_module('character_designer.unity_animation')
        target = importlib.import_module('character_designer.animation_worklist_target')
        worklist = importlib.import_module('character_designer.animation_worklist')
        original = importlib.import_module('character_designer.body_original_mode')
        fp = importlib.import_module('character_designer.animation_worklist_fingerprint')
        display = importlib.import_module('character_designer.bone_display')
        report['runtime'] = {'blender': bpy.app.version_string, 'addon': list(cd.bl_info['version']),
                             'module_sha256': {m.__name__: full.file_hash(m.__file__)
                                               for m in (ua, target, worklist, original, fp, display)}}
        datafiles = Path(bpy.utils.user_resource('DATAFILES', create=True)).resolve()
        if not datafiles.is_relative_to(EVIDENCE) and datafiles != EVIDENCE.parent / 'dr24cache':
            raise AssertionError('Resume requires the task-owned isolated Source cache.')
        full.phase(report, 'artist_baseline_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(baseline), use_scripts=False, load_ui=False))
        scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
        full.select_rig(scene, rig)
        evaluate_forearm_runtime(scene, rig)
        baseline_assets = asset_snapshot(scene, rig, ua)
        report['baseline_assets'] = baseline_assets
        full.phase(report, 'restored_resume_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(source), use_scripts=False, load_ui=False))
        scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
        full.select_rig(scene, rig)
        if target.is_adopted(rig):
            raise AssertionError('Resume input must already be restored.')
        evaluate_forearm_runtime(scene, rig)
        before = asset_snapshot(scene, rig, ua)
        if changes(baseline_assets, before):
            raise AssertionError('Resumed artist assets differ from full backup: ' + ', '.join(changes(baseline_assets, before)))
        saved = scene.character_designer_animation_worklist
        retained = [item for item in saved.items if item.rig is rig and item.custom_action]
        if len(retained) != 1:
            raise AssertionError('Expected exactly one retained original-Rig Custom row.')
        item, item_id = retained[0], retained[0].item_id
        custom_proof = fp.fingerprint_action(item.custom_action, item.custom_slot)
        source_proof = fp.fingerprint_action(item.source_action, item.source_slot)
        if not custom_proof['fingerprint_known'] or not source_proof['fingerprint_known']:
            raise AssertionError('Retained selected-slot proof is unknown.')
        report['retained_custom_proof'] = custom_proof
        report['retained_source_proof'] = source_proof
        report['original_assets_before'] = before
        original_data = rig.data
        expected = {'data_name': rig.data.name, 'rest_sha256': digest(ua._rest_state(rig.data)),
                    'original_active': original.active(rig), 'original_session': rig.get(original.SESSION),
                    'action': rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None,
                    'slot': rig.animation_data.action_slot.handle if rig.animation_data and rig.animation_data.action_slot else None,
                    'nla': full.nla_content(rig), 'snapshot': ua._snapshot(bpy.context, rig), 'assets': before}
        try:
            worklist.activate(bpy.context, item_id, 'CUSTOM')
        except ValueError as exc:
            report['activation_before_readopt_blocked'] = str(exc)
        else:
            raise AssertionError('Retained Custom activated before explicit Main Rig re-adoption.')
        if not args.skip_native_guard_fixtures:
            report['native_ownership_guard_fixtures'] = full.phase(report, 'native_ownership_guards',
                lambda: native_guard_fixtures(bpy.context, scene, rig))
            if changes(before, asset_snapshot(scene, rig, ua)):
                raise AssertionError('Native guard fixtures changed protected artist assets.')
        packet = ua.load_package(args.packet)
        full.phase(report, 'retained_custom_readopt', lambda: target.adopt_main_rig(bpy.context))
        full.phase(report, 'retained_custom_activate', lambda: worklist.activate(bpy.context, item_id, 'CUSTOM'))
        item = worklist._item(saved, item_id)
        if not target.is_adopted(rig) or item.rig is not rig or saved.rig is not rig:
            raise AssertionError('Retained re-adoption used another rig or lost ownership.')
        report['active_native_control_guards'] = legitimate_guards(bpy.context, rig)
        if fp.fingerprint_action(item.custom_action, item.custom_slot) != custom_proof:
            raise AssertionError('Re-adoption replaced/changed retained Custom selected-slot content.')
        if fp.fingerprint_action(item.source_action, item.source_slot) != source_proof:
            raise AssertionError('Re-adoption changed retained linked Source content.')
        mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
        report['readopted_samples'], authored = full.phase(report, 'retained_custom_samples_59',
            lambda: full.samples(scene, rig, packet, mapping, ua, args.matrix_tolerance))
        report['readopted_assets'] = full.require_assets(scene, rig, ua, before, original_data,
                                                       expected['rest_sha256'], authored)
        report['active_save'] = full.phase(report, 'readopted_save', lambda: full.save_copy(active_output))
        full.phase(report, 'readopted_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(active_output), use_scripts=False, load_ui=False))
        scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
        full.select_rig(scene, rig)
        saved = scene.character_designer_animation_worklist
        item = worklist._item(saved, item_id)
        if not target.is_adopted(rig) or item.rig is not rig:
            raise AssertionError('Re-adopted Main Rig ownership did not persist after reopening.')
        report['reopened_native_control_guards'] = legitimate_guards(bpy.context, rig)
        if fp.fingerprint_action(item.custom_action, item.custom_slot) != custom_proof:
            raise AssertionError('Retained Custom content changed after active save/reopen.')
        worklist.activate(bpy.context, item_id, 'CUSTOM')
        mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
        report['reopened_samples'], _ = full.phase(report, 'readopted_reopened_samples_59',
            lambda: full.samples(scene, rig, packet, mapping, ua, args.matrix_tolerance))
        report['persistent_readoption_reopened'] = True
        full.phase(report, 'second_restore', lambda: target.restore_main_rig(bpy.context))
        if target.is_adopted(rig):
            raise AssertionError('Second Restore left adoption active.')
        report['second_recovery'] = require_original_state(bpy.context, scene, rig, expected, ua, original)
        report['second_restored_native_guards'] = legitimate_guards(bpy.context, rig)
        report['restored_save'] = full.phase(report, 'second_restored_save', lambda: full.save_copy(restored_output))
        full.phase(report, 'second_restored_reopen', lambda: bpy.ops.wm.open_mainfile(
            filepath=str(restored_output), use_scripts=False, load_ui=False))
        scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
        full.select_rig(scene, rig)
        if target.is_adopted(rig):
            raise AssertionError('Second restored saved scene reopened with adoption active.')
        report['second_recovery_reopened'] = require_original_state(bpy.context, scene, rig, expected, ua, original)
        report['completed'] = True
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    finally:
        report['total_elapsed_wall_seconds'] = time.perf_counter() - wall_start
        report['total_elapsed_cpu_seconds'] = time.process_time() - cpu_start
        report['input_file_unchanged'] = full.file_hash(source) == source_hash
        report['baseline_file_unchanged'] = full.file_hash(baseline) == baseline_hash
        report['packet_file_unchanged'] = full.file_hash(args.packet) == packet_hash
        report['completed'] = bool(report['completed'] and all(report[key] for key in
            ('input_file_unchanged', 'baseline_file_unchanged', 'packet_file_unchanged')))
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        print('READOPT_RESUME ' + json.dumps({key: report.get(key) for key in
            ('completed', 'error', 'persistent_readoption_reopened', 'total_elapsed_wall_seconds',
             'total_elapsed_cpu_seconds')}, ensure_ascii=False), flush=True)
    if not report['completed']:
        raise RuntimeError(report.get('error', 'Retained-Custom resume failed.'))


if __name__ == '__main__':
    main()
