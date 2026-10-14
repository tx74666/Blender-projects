"""Owned Action diagnostic: Scene marker, then bounded native curve Key if stable.

No Character Designer registration, Body fingerprint, public Gun claim or SaveCopy.
Completion is diagnostic completion, never Original20 semantic acceptance.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
from contextlib import contextmanager

ROUND = Path(__file__).resolve().parent
REPORT_SHA = '64faf182b88775599a6cfa0848301b7b41a3b6434d301f833d68a7c30b7dfa88'
FAILURE_SHA = '7cac37ab17ac30ab1c6a36d9c0ce1ddd1094f8af1cfe5ceba17e048a45acde72'
MANIFEST_SHA = 'bb08d3abb146836db522dcbf322ad32bff52a66dbe967f5dd62457f81b234358'


def require(value, message):
    if not value: raise RuntimeError(message)


def document(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def pin(path, expected=None):
    path = Path(path).resolve(); data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(expected is None or digest == expected.lower(), 'Changed input: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': len(data)}


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def differences(before, after, path='$'):
    if type(before) is not type(after): return [{'path': path, 'before': before, 'after': after}]
    if isinstance(before, dict):
        rows = []
        for key in sorted(before.keys() | after.keys()):
            if key not in before or key not in after:
                rows.append({'path': path + '.' + key, 'before_present': key in before,
                    'after_present': key in after, 'before': before.get(key), 'after': after.get(key)})
            else: rows.extend(differences(before[key], after[key], path + '.' + key))
        return rows
    if isinstance(before, list):
        if len(before) != len(after): return [{'path': path, 'before': before, 'after': after}]
        return [row for index, (a, b) in enumerate(zip(before, after))
            for row in differences(a, b, path + '[' + str(index) + ']')]
    return [] if before == after else [{'path': path, 'before': before, 'after': after}]


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--confirm-isolated-headful', action='store_true', required=True)
    parser.add_argument('--quit-on-completion', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir()
        and not any(output.iterdir()), 'Use a new empty owned output directory.')
    inputs = {'source': pin(__file__, args.source_sha256),
        'native03_report': pin(ROUND / 'recovery_gun_undo_07734_03/original20_recovery_gun_undo_report.json', REPORT_SHA),
        'failure_scene': pin(ROUND / 'recovery_gun_undo_07734_03/failed_original20_recovery_gun_undo.blend', FAILURE_SHA),
        'package_manifest': pin(ROUND / 'package_3fd79576/python_projection.json', MANIFEST_SHA)}
    prior, manifest = document(inputs['native03_report']['path']), document(inputs['package_manifest']['path'])
    require(prior['completed'] is False and prior['stage'] == 'gun_redo_readback'
        and prior['error'] == 'RuntimeError: Redo changed the exact edited Custom20 motion.'
        and prior['failure_scene'] == inputs['failure_scene'], 'Require the actual failed Redo evidence.')
    identity = prior['motion_boundaries'][-1]['pair_identity']
    require(prior['motion_boundaries'][-1]['boundary'] == 'Gun_Redo', 'Require the actual Redo boundary.')
    inputs['fingerprint_source'] = pin(Path(manifest['source_root']) / 'animation_worklist_fingerprint.py',
        manifest['files']['animation_worklist_fingerprint.py'])
    spec = importlib.util.spec_from_file_location('original20_fingerprint_diagnostic', inputs['fingerprint_source']['path'])
    fingerprint = importlib.util.module_from_spec(spec); spec.loader.exec_module(fingerprint)
    import bpy
    require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
        and len(bpy.context.window_manager.windows) == 1 and bpy.context.preferences.edit.use_global_undo
        and not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Use fresh isolated headful 5.2 with existing Undo and scripts disabled.')
    require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules),
        'Do not load Character Designer runtime or its handlers in this diagnostic.')
    report = {'schema': 'x.diagnostic.original20-action-undo/1', 'completed': False,
        'semantic_validation_pass': False, 'original_artist_opened_or_written': False,
        'Character_Designer_registered': False, 'Body_fingerprint_performed': False,
        'Action_edit_performed': False, 'SaveCopy_performed': False, 'source_inputs': inputs,
        'pid': os.getpid(), 'historical_edited_payload_available': False, 'snapshots': {}, 'comparisons': {}}
    report_path = output / 'action_undo_diagnostic_report.json'
    state = {'phase': 'open', 'payloads': {}, 'marker': 'codex_action_undo_probe_' + str(os.getpid())}

    @contextmanager
    def view():
        windows = list(bpy.context.window_manager.windows)
        require(len(windows) == 1, 'Require one owned window.')
        areas = [area for area in windows[0].screen.areas if area.type == 'VIEW_3D']
        require(len(areas) == 1, 'Require one factory View3D.')
        regions = [region for region in areas[0].regions if region.type == 'WINDOW']
        require(len(regions) == 1, 'Require its WINDOW region.')
        with bpy.context.temp_override(window=windows[0], area=areas[0], region=regions[0]): yield

    def operation(name, **kwargs):
        with view():
            operator = getattr(bpy.ops.ed, name)
            require(operator.poll(), 'Native operator unavailable: ' + name)
            result = operator('EXEC_DEFAULT', False, **kwargs)
            require(result == {'FINISHED'}, 'Native operator did not finish: ' + name)
        report.setdefault('operators', []).append({'id': 'ed.' + name, 'result': sorted(result)})

    def snapshot(label):
        action = bpy.data.actions.get(identity['actions']['custom']['name'])
        require(action is not None and action.library is None, 'Fresh owned Custom20 Action missing.')
        owner = json.loads(action['character_designer_rigging_input_owner_v1'])
        require(owner['new_action_id'] == identity['custom_uuid']
            and owner['input_slot'] == identity['slots']['custom'], 'Fresh Action/slot owner changed.')
        curves = fingerprint._selected_curves(action, identity['slots']['custom'])
        expected = {('[' + json.dumps('cd_rigging_' + side + '_' + field) + ']', index)
            for side in ('right', 'left') for field, size in (('targetPosition', 3), ('targetRotation', 4), ('hintPosition', 3))
            for index in range(size)}
        require(len(curves) == 20 and {(curve.data_path, curve.array_index) for curve in curves} == expected
            and all(len(curve.keyframe_points) == 59 for curve in curves), 'Inspect only exact20 curves and their59 keys.')
        payload = fingerprint.collect_action_payload(action, identity['slots']['custom'])
        proof = fingerprint.fingerprint_action(action, identity['slots']['custom'])
        require(proof['fingerprint_known'] and proof['action_fingerprint'] == fingerprint._stream_digest(
            {'schema': fingerprint.SCHEMA, 'action': payload}), 'Collected payload differs from the actual native fingerprint.')
        destination = output / (label + '_full20_payload.json'); write(destination, payload)
        state['payloads'][label] = payload
        report['snapshots'][label] = {'file': pin(destination), 'action_fingerprint': proof['action_fingerprint'],
            'action': action.name, 'slot': identity['slots']['custom'], 'curve_count': len(curves),
            'key_count': sum(len(curve.keyframe_points) for curve in curves),
            'curve_order': [[curve.data_path, curve.array_index] for curve in curves],
            'Scene_marker_present': state['marker'] in bpy.context.scene}
        write(report_path, report)

    def prepare():
        snapshot('before_checkpoints')
        operation('undo_push', message='Before owned Scene diagnostic marker')
        require(state['marker'] not in bpy.context.scene, 'Owned marker already exists.')
        bpy.context.scene[state['marker']] = 1
        operation('undo_push', message='After owned Scene diagnostic marker')
        snapshot('before_undo')

    def prepare_curve_key():
        snapshot('before_curve_key')
        operation('undo_push', message='Before owned twenty-curve Key diagnostic')
        action = bpy.data.actions.get(identity['actions']['custom']['name'])
        curves = fingerprint._selected_curves(action, identity['slots']['custom'])
        changed = []
        for curve in curves:
            matches = [point for point in curve.keyframe_points if float(point.co.x) == 1.]
            require(len(matches) == 1, 'Require the one existing frame1 key per scalar curve.')
            value = float(matches[0].co.y)
            if curve.data_path == '["cd_rigging_right_targetPosition"]' and curve.array_index == 0:
                value += .001
                changed.append([curve.data_path, curve.array_index])
            # The same three native RNA operations as key_current:1479-1482.
            point = curve.keyframe_points.insert(1., value)
            require(point is not None, 'The diagnostic scalar key insert failed.')
            point.interpolation = 'LINEAR'
            curve.update()
        require(len(changed) == 1, 'Exactly one scalar value must receive the diagnostic delta.')
        report.update(Action_edit_performed=True, curve_Key_diagnostic={
            'public_Gun_operator_claimed': False, 'edited_scalar': changed[0], 'delta': .001,
            'frame': 1., 'curves_inserted_LINEAR_updated': 20, 'production_backend_called': False})
        snapshot('after_curve_key')
        operation('undo_push', message='After owned twenty-curve Key diagnostic')
        snapshot('before_curve_undo')

    def finish(error=None):
        if error is not None:
            report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        for label, before, after in (('checkpoint_effect', 'before_checkpoints', 'before_undo'),
                ('Undo_effect', 'before_checkpoints', 'after_undo'), ('Redo_effect', 'before_undo', 'after_redo'),
                ('curve_Key_change', 'before_curve_key', 'after_curve_key'),
                ('curve_PostCheckpoint_effect', 'after_curve_key', 'before_curve_undo'),
                ('curve_Undo_effect', 'before_curve_key', 'after_curve_undo'),
                ('curve_Redo_effect', 'before_curve_undo', 'after_curve_redo')):
            if before in state['payloads'] and after in state['payloads']:
                changes = differences(state['payloads'][before], state['payloads'][after])
                destination = output / (label + '_structural_diff.json'); write(destination, changes)
                report['comparisons'][label] = {'exact_payload_equal': not changes, 'difference_count': len(changes), 'file': pin(destination)}
        try:
            for row in inputs.values(): pin(row['path'], row['sha256'])
            report['inputs_unchanged'] = True
        except Exception as pin_error:
            report['input_error'] = str(pin_error); error = pin_error
        report['completed'] = error is None
        write(report_path, report)
        print('ACTION_UNDO_DIAGNOSTIC ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)
        if args.quit_on_completion:
            def quit_owned():
                bpy.ops.wm.quit_blender('EXEC_DEFAULT', False)
                return None
            bpy.app.timers.register(quit_owned, first_interval=3., persistent=False)

    def tick():
        report['stage'] = state['phase']; write(report_path, report)
        print('ACTION_UNDO_STAGE ' + state['phase'], flush=True)
        try:
            if state['phase'] == 'open':
                require(bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=inputs['failure_scene']['path'],
                    use_scripts=False, load_ui=False) == {'FINISHED'}, 'Owned failure copy did not open.')
                require(Path(bpy.data.filepath).resolve() == Path(inputs['failure_scene']['path']), 'Unexpected opened file.')
                state['phase'] = 'prepare'
            elif state['phase'] == 'prepare':
                prepare()  # All Action RNA leaves its stack before native Undo.
                operation('undo'); state['phase'] = 'undo_readback'
            elif state['phase'] == 'undo_readback':
                require(state['marker'] not in bpy.context.scene, 'Marker Undo failed.')
                snapshot('after_undo')
                operation('redo'); state['phase'] = 'redo_readback'
            elif state['phase'] == 'redo_readback':
                require(bpy.context.scene.get(state['marker']) == 1, 'Marker Redo failed.')
                snapshot('after_redo')
                baseline = state['payloads']['before_checkpoints']
                stable = all(state['payloads'][label] == baseline for label in ('before_undo', 'after_undo', 'after_redo'))
                report['marker_cycle_full_payload_stable'] = stable
                if not stable:
                    finish(); return None
                state['phase'] = 'curve_prepare'
            elif state['phase'] == 'curve_prepare':
                prepare_curve_key()  # Discard all current Action RNA before Undo.
                operation('undo'); state['phase'] = 'curve_undo_readback'
            elif state['phase'] == 'curve_undo_readback':
                snapshot('after_curve_undo')
                operation('redo'); state['phase'] = 'curve_redo_readback'
            elif state['phase'] == 'curve_redo_readback':
                snapshot('after_curve_redo'); finish(); return None
            return .1
        except Exception as error:
            finish(error); return None
    bpy.app.timers.register(tick, first_interval=.1, persistent=True)


if __name__ == '__main__': main()
