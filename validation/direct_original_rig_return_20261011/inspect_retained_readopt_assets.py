"""Root-launched cheap native asset transition diagnosis; no bake or save.

Records every exact fingerprint source field and named JSON Pointer differences.
Use only the task's disposable restored_isolated.blend and frozen projection.
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
from validation_preservation import (asset_payload, digest, evaluate_forearm_runtime,
                                     identity, mesh_content)


def differences(before, after, path=''):
    if isinstance(before, dict) and isinstance(after, dict):
        rows = []
        for key in sorted(before.keys() | after.keys()):
            child = path + '/' + str(key).replace('~', '~0').replace('/', '~1')
            if key not in before or key not in after:
                rows.append({'path': child, 'before': before.get(key), 'after': after.get(key),
                             'before_present': key in before, 'after_present': key in after})
            else:
                rows.extend(differences(before[key], after[key], child))
        return rows
    if isinstance(before, list) and isinstance(after, list):
        rows = []
        for index in range(max(len(before), len(after))):
            child = path + '/' + str(index)
            if index >= len(before) or index >= len(after):
                rows.append({'path': child,
                             'before': before[index] if index < len(before) else None,
                             'after': after[index] if index < len(after) else None,
                             'before_present': index < len(before), 'after_present': index < len(after)})
            else:
                rows.extend(differences(before[index], after[index], child))
        return rows
    return [] if before == after else [{'path': path, 'before': before, 'after': after}]


def widget_content(names):
    result = {}
    for name in sorted(names):
        obj = bpy.data.objects.get(name)
        if obj is None:
            result[name] = {'missing': True}
        else:
            result[name] = {'object_id': identity(obj),
                            'mesh': mesh_content(obj) if obj.type == 'MESH' else None,
                            'matrix_basis': [list(row) for row in obj.matrix_basis]}
    return result


def capture(scene, rig, ua, original, widget_names, original_data):
    bpy.context.view_layer.update()
    runtime = evaluate_forearm_runtime(scene, rig)
    bpy.context.view_layer.update()
    payload = asset_payload(scene, rig, ua)
    return {'frame': scene.frame_current + scene.frame_subframe,
            'original_mode_active': original.active(rig),
            'rig_data_id': identity(rig.data), 'rig_data_pointer': rig.data.as_pointer(),
            'original_data_id': identity(original_data),
            'original_data_rest': ua._rest_state(original_data),
            'payload': payload, 'payload_sha256': digest(payload),
            'component_sha256': {key: digest(value) for key, value in payload.items()},
            'all_initial_widget_assets': widget_content(widget_names),
            'forearm_runtime': runtime}


def compare(before, after):
    a, b = before['payload'], after['payload']
    return {'changed_components': sorted(key for key in a.keys() | b.keys() if a.get(key) != b.get(key)),
            'field_differences': differences(a, b, '/payload'),
            'initial_widget_asset_differences': differences(before['all_initial_widget_assets'],
                after['all_initial_widget_assets'], '/all_initial_widget_assets'),
            'protected_original_rest_differences': differences(before['original_data_rest'],
                after['original_data_rest'], '/original_data_rest')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--addon-root', required=True)
    parser.add_argument('--packet', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, output = full.safe_path(args.input), full.safe_path(args.report)
    if source == output:
        raise ValueError('Input and report must differ.')
    input_hash, packet_hash = full.file_hash(source), full.file_hash(args.packet)
    report = {'schema': 'x.validation.retained-readopt-asset-transition/1', 'completed': False,
              'input': str(source), 'input_sha256': input_hash,
              'packet': args.packet, 'packet_sha256': packet_hash,
              'scope': 'Disposable restored file, no bake, no save, no artist or Unity mutation.',
              'phases': {}, 'transitions': {}}
    started = time.perf_counter()
    try:
        addon_root = Path(args.addon_root).resolve()
        sys.path.insert(0, str(addon_root))
        cd = importlib.import_module('character_designer')
        if not Path(cd.__file__).resolve().is_relative_to(addon_root):
            raise AssertionError('Unexpected runtime root.')
        report['runtime_projection'] = full.verify_runtime_projection(cd)
        cd.register()
        ua = importlib.import_module('character_designer.unity_animation')
        target = importlib.import_module('character_designer.animation_worklist_target')
        worklist = importlib.import_module('character_designer.animation_worklist')
        original = importlib.import_module('character_designer.body_original_mode')
        fk_visuals = importlib.import_module('character_designer.limb_fk_visuals')
        report['runtime'] = {'blender': bpy.app.version_string, 'addon': list(cd.bl_info['version']),
                             'modules': {m.__name__: full.file_hash(m.__file__)
                                         for m in (ua, target, worklist, original, fk_visuals)}}

        def reopen():
            bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False, load_ui=False)
            scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
            full.select_rig(scene, rig)
            if target.is_adopted(rig) or not original.active(rig):
                raise AssertionError('Input must be restored to artist Original mode.')
            return scene, rig

        scene, rig = full.phase(report, 'leave_branch_reopen', reopen)
        widget_names = {pb.custom_shape.name for pb in rig.pose.bones if pb.custom_shape}
        record = fk_visuals.get_record(rig)
        if record:
            widget_names.update(row['object'] for row in record['bindings'].values())
        original_data = rig.data
        report['initial_widget_names'] = sorted(widget_names)
        report['native_fk_record'] = record
        report['phases']['before_leave'] = capture(scene, rig, ua, original, widget_names, original_data)
        full.phase(report, 'official_leave_only', lambda: original.leave(bpy.context, rig))
        report['phases']['after_leave'] = capture(scene, rig, ua, original, widget_names, original_data)
        report['transitions']['official_leave_only'] = compare(report['phases']['before_leave'],
                                                                report['phases']['after_leave'])

        scene, rig = full.phase(report, 'readopt_branch_reopen', reopen)
        original_data = rig.data
        report['phases']['before_readopt'] = capture(scene, rig, ua, original, widget_names, original_data)
        saved = scene.character_designer_animation_worklist
        retained = [item for item in saved.items if item.rig is rig and item.custom_action]
        if len(retained) != 1:
            raise AssertionError('Expected exactly one retained Custom row.')
        item_id = retained[0].item_id
        full.phase(report, 'readopt', lambda: target.adopt_main_rig(bpy.context))
        report['phases']['after_readopt'] = capture(scene, rig, ua, original, widget_names, original_data)
        report['transitions']['readopt'] = compare(report['phases']['before_readopt'],
                                                   report['phases']['after_readopt'])
        full.phase(report, 'activate_custom', lambda: worklist.activate(bpy.context, item_id, 'CUSTOM'))
        report['phases']['after_activate'] = capture(scene, rig, ua, original, widget_names, original_data)
        report['transitions']['activate_custom'] = compare(report['phases']['after_readopt'],
                                                           report['phases']['after_activate'])
        packet = ua.load_package(args.packet)
        frame = 1.0 + float(packet['frames'][-1]['time']) * (scene.render.fps / scene.render.fps_base)
        full.phase(report, 'last_sample_frame', lambda: ua._set_frame(scene, frame))
        report['phases']['last_sample_frame'] = capture(scene, rig, ua, original, widget_names, original_data)
        report['transitions']['last_sample_frame'] = compare(report['phases']['after_activate'],
                                                             report['phases']['last_sample_frame'])
        report['transitions']['whole_readopt_preview'] = compare(report['phases']['before_readopt'],
                                                                 report['phases']['last_sample_frame'])
        full.phase(report, 'restore', lambda: target.restore_main_rig(bpy.context))
        report['phases']['after_restore'] = capture(scene, rig, ua, original, widget_names, original_data)
        report['transitions']['whole_readopt_restore'] = compare(report['phases']['before_readopt'],
                                                                 report['phases']['after_restore'])
        report['completed'] = True
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    finally:
        report['input_unchanged'] = full.file_hash(source) == input_hash
        report['packet_unchanged'] = full.file_hash(args.packet) == packet_hash
        report['elapsed_wall_seconds'] = time.perf_counter() - started
        report['completed'] = bool(report['completed'] and report['input_unchanged'] and report['packet_unchanged'])
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        print('READOPT_ASSET_TRANSITION ' + json.dumps({'completed': report['completed'],
            'error': report.get('error'), 'elapsed_wall_seconds': report['elapsed_wall_seconds'],
            'transitions': {name: {'changed_components': row['changed_components'],
                                  'changed_field_count': len(row['field_differences']),
                                  'initial_widget_asset_changes': len(row['initial_widget_asset_differences']),
                                  'protected_original_rest_changes': len(row['protected_original_rest_differences'])}
                            for name, row in report['transitions'].items()}}, ensure_ascii=False), flush=True)
    if not report['completed']:
        raise RuntimeError(report.get('error', 'Transition diagnosis failed.'))


if __name__ == '__main__':
    main()
