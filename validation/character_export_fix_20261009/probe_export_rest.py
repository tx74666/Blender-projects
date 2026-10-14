"""Isolated Blender reproduction for frozen/patched export skeleton cleanup.

Run only in background Blender. This script writes JSON/optional FBX evidence,
never saves any .blend, and never starts Blender or Unity itself.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback

import bpy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_rest(rig):
    result = {}
    for bone in rig.data.bones:
        axis = (bone.tail_local - bone.head_local).normalized()
        _axis, roll = bpy.types.Bone.AxisRollFromMatrix(bone.matrix_local.to_3x3(), axis=axis)
        result[bone.name] = {
            'matrix': [list(row) for row in bone.matrix_local],
            'head': list(bone.head_local), 'tail': list(bone.tail_local),
            'roll': float(roll), 'parent': bone.parent.name if bone.parent else None,
            'use_deform': bool(bone.use_deform),
        }
    return result


def rest_comparison(before, after, retained):
    rows = {}
    missing = sorted(set(retained) - set(before) | set(retained) - set(after))
    for name in sorted(set(retained) & set(before) & set(after)):
        first, second = before[name], after[name]
        rows[name] = {
            'matrix_error': max(abs(a - b) for row_a, row_b in zip(first['matrix'], second['matrix'])
                                for a, b in zip(row_a, row_b)),
            'head_error': max(abs(a - b) for a, b in zip(first['head'], second['head'])),
            'tail_error': max(abs(a - b) for a, b in zip(first['tail'], second['tail'])),
            'roll_error_rad': abs((second['roll'] - first['roll'] + math.pi) % math.tau - math.pi),
            'deform_preserved': first['use_deform'] == second['use_deform'],
            'prior_parent': first['parent'], 'clean_parent': second['parent'],
        }
    bad = {name: row for name, row in rows.items()
           if max(row['matrix_error'], row['head_error'], row['tail_error'], row['roll_error_rad']) > 3e-6
           or not row['deform_preserved']}
    return {'passed': not missing and not bad and len(rows) == len(retained),
            'retained_count': len(retained), 'missing': missing, 'mismatches': bad, 'per_bone': rows}


def cosha_fixture():
    # The same independently captured Cosha geometry as the persistent canonical
    # test_clean_skeleton_preserves_native_cosha_roll regression.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm = bpy.data.armatures.new('Cosha Rest Regression Data')
    rig = bpy.data.objects.new('Cosha Rest Regression', arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    root = arm.edit_bones.new('CTRL_master')
    root.head, root.tail, root.use_deform = (0, 0, 0), (0, 0, .2), False
    hips = arm.edit_bones.new('Hips')
    hips.head, hips.tail, hips.parent = (0, 0, .2), (0, 0, .4), root
    bridge = arm.edit_bones.new('CTRL_bridge')
    bridge.head, bridge.tail, bridge.parent = (0, 0, .4), (0, .1, .4), hips
    bridge.use_deform = False
    geometries = {
        'shin.R': ((-.09694115072488785, .06386806070804596, .6524592041969299),
                   (-.09949608147144318, .060485754162073135, -.021930769085884094), 1.574584722518921),
        'thigh.L': ((.09480436891317368, .09454359859228134, 1.2164766788482666),
                    (.09694115072488785, .06386806070804596, .6524592041969299), 1.5670078992843628),
        'hand.R': ((-.5040974020957947, .06748819351196289, 1.2489454746246338),
                   (-.5401939749717712, .06766103953123093, 1.2075296640396118), -.940944492816925),
    }
    for name, (head, tail, roll) in geometries.items():
        bone = arm.edit_bones.new(name)
        bone.head, bone.tail, bone.roll, bone.parent = head, tail, roll, bridge
        bone.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')
    for name in ('CTRL_master', 'CTRL_bridge'):
        arm.bones[name]['character_designer_owner'] = 'limb_ik'
    return rig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--scope', choices=('cosha', 'real-clean', 'real-export'), default='cosha')
    parser.add_argument('--blend', type=Path)
    parser.add_argument('--job', type=Path)
    parser.add_argument('--rig', default='CoshaRig')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not bpy.app.background:
        raise RuntimeError('This verification is allowed only in isolated background Blender.')
    if args.scope != 'cosha' and args.blend is None:
        raise ValueError('Real verification needs an explicitly supplied read-only .blend input.')
    if args.scope == 'real-export' and args.job is None:
        raise ValueError('Real export needs the exact captured Export job JSON; do not guess its scope.')
    source_sha = sha(args.blend) if args.blend else None
    worker_sha = sha(args.worker)
    report = {'scope': args.scope, 'worker': str(args.worker), 'worker_sha256': worker_sha,
              'input_blend': str(args.blend) if args.blend else None, 'input_sha256': source_sha,
              'Blender_version': bpy.app.version_string, 'checks': [], 'saved_blend': False}
    try:
        spec = importlib.util.spec_from_file_location('isolated_export_rest_worker', args.worker)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        real_clean = worker._clean_skeleton

        def traced_clean(context, rig, objects):
            before = native_rest(rig)
            mirror_before = bool(rig.data.use_mirror_x)
            retained = real_clean(context, rig, objects)
            after = native_rest(rig)
            comparison = rest_comparison(before, after, retained)
            comparison.update(rig=rig.name, before=before, after=after, retained=retained,
                              mirror_x_before=mirror_before, mirror_x_after=bool(rig.data.use_mirror_x))
            report['checks'].append(comparison)
            return retained

        worker._clean_skeleton = traced_clean
        if args.scope == 'cosha':
            rig = cosha_fixture()
            retained = worker._clean_skeleton(bpy.context, rig, [rig])
            report['expected_retained_names'] = ['Hips', 'hand.R', 'shin.R', 'thigh.L']
            if retained != report['expected_retained_names']:
                raise AssertionError('The Cosha fixture did not actually remove both generated bridges.')
        else:
            bpy.ops.wm.open_mainfile(filepath=str(args.blend), load_ui=False, use_scripts=False)
            job = json.loads(args.job.read_text(encoding='utf-8')) if args.job else None
            if args.scope == 'real-export':
                stage = args.report.parent / ('export_' + worker_sha[:12])
                if stage.exists():
                    raise ValueError('Export evidence directory already exists; choose a new report directory.')
                job['stage'] = str(stage)
                report['input_job_sha256'] = sha(args.job)
                report['captured_objects'] = job['objects']
                report['export_result'] = worker.export_job(job)
                report['fbx_path'] = str(stage / job['filename'])
                report['fbx_sha256'] = sha(stage / job['filename'])
            else:
                rig = bpy.data.objects.get(job['rig'] if job else args.rig)
                if rig is None or rig.type != 'ARMATURE':
                    raise ValueError('The explicitly selected Main Rig is missing from the input.')
                objects = [bpy.data.objects[name] for name in job['objects']] if job else list(bpy.context.scene.objects)
                if rig.name not in bpy.context.view_layer.objects:
                    bpy.context.scene.collection.objects.link(rig)
                worker._clean_skeleton(bpy.context, rig, objects)
        report['passed'] = bool(report['checks']) and all(check['passed'] for check in report['checks'])
    except Exception:
        report['passed'] = False
        report['error'] = traceback.format_exc()
    finally:
        report['source_file_unchanged'] = args.blend is None or sha(args.blend) == source_sha
        report['passed'] = report.get('passed', False) and report['source_file_unchanged']
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        print('EXPORT_REST_PROBE_REPORT', str(args.report), flush=True)
        for check in report['checks']:
            print('REST_RESULT', check['rig'], check['passed'],
                  json.dumps(check['mismatches'], sort_keys=True), flush=True)
    if not report['passed']:
        raise AssertionError('Export changed retained native Rest or verification failed; inspect JSON evidence.')


if __name__ == '__main__':
    main()
