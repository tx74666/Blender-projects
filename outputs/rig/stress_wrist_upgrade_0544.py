"""Actual wrist upgrade API stress test, entirely in a disposable file copy."""
import bpy
import hashlib
import importlib.util
import json
import math
import sys
import traceback
from pathlib import Path
from mathutils import Matrix, Vector, Euler

OUT = Path(__file__).parent
TRANSLATIONS_ONLY = False
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik
spec = importlib.util.spec_from_file_location('wrist_diagnostics', OUT / 'diagnose_wrist_rotation_0544.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def rotation_vector(m):
    q = m.to_quaternion().normalized()
    if q.w < 0:
        q.negate()
    axis, angle = q.to_axis_angle()
    return axis * math.degrees(angle)


def trs(location, angles, scale):
    return Matrix.Translation(location) @ Euler(angles).to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1))


def main():
    path = Path(bpy.data.filepath)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rig = bpy.data.objects['CoshaRig']
    report = {'source': str(path), 'sha256': digest, 'ok': False, 'cases': []}
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        for group in rig.data.collections_all:
            group.is_visible, group.is_solo = True, False
        for pb in rig.pose.bones:
            if pb.name.startswith('CTRL_hand_IK.'):
                pb.hide = pb.bone.hide = pb.bone.hide_select = False
        w, a, region = next((w, a, re) for w in bpy.context.window_manager.windows
            for a in w.screen.areas if a.type == 'VIEW_3D' for re in a.regions if re.type == 'WINDOW')
        d.update(rig)
        old_pose = {p.name: p.matrix.copy() for p in rig.pose.bones}
        old_rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        report['dry_run'] = limb_ik.upgrade_wrist_rotation(bpy.context, rig, dry_run=True)
        report['upgrade'] = limb_ik.upgrade_wrist_rotation(bpy.context, rig)
        d.update(rig)
        report['migration_pose_error'] = max(abs(rig.pose.bones[n].matrix[i][j] - m[i][j])
            for n, m in old_pose.items() for i in range(4) for j in range(4))
        report['migration_rest_error'] = max(abs(rig.data.bones[n].matrix_local[i][j] - m[i][j])
            for n, m in old_rest.items() for i in range(4) for j in range(4))
        report['new_bones'] = sorted(set(rig.data.bones.keys()) - set(old_rest))
        report['idempotent'] = not limb_ik.upgrade_wrist_rotation(bpy.context, rig)['changed']
        assert report['migration_pose_error'] < 2e-5 and report['migration_rest_error'] == 0
        assert report['new_bones'] == ['MCH_hand_rotation.L', 'MCH_hand_rotation.R']
        assert report['idempotent']
        root = rig.pose.bones['CTRL_master']
        root.rotation_mode = 'XYZ'
        for curve in rig.animation_data.drivers:
            if curve.data_path == root.path_from_id('scale'):
                curve.mute = True
        original_world = rig.matrix_world.copy()
        original_root = root.matrix_basis.copy()
        native_basis = {p.name: p.matrix_basis.copy() for p in rig.pose.bones}
        identity = ((0, 0, 0), (0, 0, 0), (1, 1, 1))
        moved = ((.13, -.09, .16), (.31, -.23, .42), (1, 1, 1))
        cases = [('baseline', identity, identity),
                 ('parent_translated_rotated', moved, identity),
                 ('parent_uniform_scale', (*moved[:2], (1.4, 1.4, 1.4)), identity),
                 ('parent_negative_scale', (*moved[:2], (-1, 1, 1)), identity),
                 ('parent_nonuniform_scale', (*moved[:2], (1.4, .7, 1.15)), identity),
                 ('armature_translated_rotated', identity, moved),
                 ('armature_uniform_scale', identity, (*moved[:2], (1.4, 1.4, 1.4))),
                 ('armature_negative_scale', identity, (*moved[:2], (-1, 1, 1))),
                 ('armature_nonuniform_scale', identity, (*moved[:2], (1.4, .7, 1.15))),
                 ('both_nonuniform_scale', (*moved[:2], (1.4, .7, 1.15)), (*moved[:2], (.8, 1.5, 1.1)))]
        for label, parent_trs, rig_trs in cases:
            for name, matrix in native_basis.items():
                rig.pose.bones[name].matrix_basis = matrix
            root.matrix_basis = trs(*parent_trs) @ original_root
            rig.matrix_world = trs(*rig_trs) @ original_world
            d.update(rig)
            case = {'name': label, 'parent_scale': parent_trs[2], 'armature_scale': rig_trs[2], 'tests': []}
            for side in ('L', 'R'):
                target, hand = rig.pose.bones['CTRL_hand_IK.' + side], rig.pose.bones['hand.' + side]
                for p in rig.pose.bones:
                    p.select = p == target
                rig.data.bones.active = target.bone
                for offset in ((0, 0, 0), (.31, -.27, .42)):
                    target.rotation_euler = offset
                    d.update(rig)
                    base = target.matrix_basis.copy()
                    before = {key: Matrix(data['matrix']) for key, data in d.state(rig, side).items()}
                    entry = {'side': side, 'nonzero_offset': any(offset),
                             'control_det': before['control'].to_3x3().determinant(),
                             'hand_det': before['hand'].to_3x3().determinant(),
                             'rotations': [], 'translations': []}
                    for axis in range(3):
                        direction = Vector(tuple(1 if j == axis else 0 for j in range(3)))
                        for degrees in (() if TRANSLATIONS_ONLY else (-5, 5)):
                            with bpy.context.temp_override(window=w, area=a, region=region):
                                status = bpy.ops.transform.rotate(value=math.radians(degrees), orient_type='GLOBAL',
                                    orient_axis='XYZ'[axis], constraint_axis=tuple(j == axis for j in range(3)),
                                    use_proportional_edit=False)
                            d.update(rig)
                            after = {key: Matrix(data['matrix']) for key, data in d.state(rig, side).items()}
                            deltas = {key: rotation_vector(after[key] @ before[key].inverted()) for key in before}
                            expected = direction * degrees
                            entry['rotations'].append({'axis': 'XYZ'[axis], 'degrees': degrees, 'status': list(status),
                                'input_error_degrees': (deltas['control'] - expected).length,
                                'hand_error_degrees': (deltas['hand'] - expected).length,
                                'widget_error_degrees': (deltas['widget'] - expected).length,
                                'hand_vs_input_error_degrees': (deltas['hand'] - deltas['control']).length,
                                'hand_alignment': deltas['hand'].normalized().dot(expected.normalized()),
                                'wrist_translation_error': (after['hand'].translation - before['hand'].translation).length})
                            target.matrix_basis = base
                            d.update(rig)
                        with bpy.context.temp_override(window=w, area=a, region=region):
                            status = bpy.ops.transform.translate(value=direction * .003, orient_type='GLOBAL',
                                constraint_axis=tuple(j == axis for j in range(3)), use_proportional_edit=False)
                        d.update(rig)
                        after = {key: Matrix(data['matrix']) for key, data in d.state(rig, side).items()}
                        shift = {key: after[key].translation - before[key].translation for key in before}
                        entry['translations'].append({'axis': 'XYZ'[axis], 'status': list(status),
                            'input_error': (shift['control'] - direction * .003).length,
                            'hand_error': (shift['hand'] - direction * .003).length,
                            'hand_vs_input_error': (shift['hand'] - shift['control']).length,
                            'hand_alignment': shift['hand'].normalized().dot(direction)})
                        target.matrix_basis = base
                        d.update(rig)
                        if TRANSLATIONS_ONLY:
                            prototype = hand.constraints['Independent Parent Delta Prototype']
                            legacy = next(c for c in hand.constraints if 'AUTO_OFFSET_ROTATION' in c.name)
                            prototype.mute, legacy.mute = True, False
                            d.update(rig)
                            old_start = rig.matrix_world @ hand.head
                            with bpy.context.temp_override(window=w, area=a, region=region):
                                bpy.ops.transform.translate(value=direction * .003, orient_type='GLOBAL',
                                    constraint_axis=tuple(j == axis for j in range(3)), use_proportional_edit=False)
                            d.update(rig)
                            old_shift = rig.matrix_world @ hand.head - old_start
                            entry['translations'][-1]['prototype_vs_legacy_hand_delta_error'] = (shift['hand'] - old_shift).length
                            target.matrix_basis = base
                            prototype.mute, legacy.mute = False, True
                            d.update(rig)
                    case['tests'].append(entry)
                target.matrix_basis = native_basis[target.name]
                d.update(rig)
            report['cases'].append(case)
            rotations = [r for t in case['tests'] for r in t['rotations']]
            translations = [r for t in case['tests'] for r in t['translations']]
            case['summary'] = {'max_hand_R_error_degrees': max((r['hand_error_degrees'] for r in rotations), default=0),
                'max_input_R_error_degrees': max((r['input_error_degrees'] for r in rotations), default=0),
                'max_hand_vs_input_R_error_degrees': max((r['hand_vs_input_error_degrees'] for r in rotations), default=0),
                'min_hand_R_alignment': min((r['hand_alignment'] for r in rotations), default=0),
                'max_R_wrist_shift': max((r['wrist_translation_error'] for r in rotations), default=0),
                'max_G_hand_error': max(r['hand_error'] for r in translations),
                'min_G_hand_alignment': min(r['hand_alignment'] for r in translations)}
            if TRANSLATIONS_ONLY:
                case['summary']['max_G_prototype_vs_legacy_delta_error'] = max(r['prototype_vs_legacy_hand_delta_error'] for r in translations)
            print('PARENT_DELTA_CASE', label, json.dumps(case['summary']), flush=True)
        report['ok'] = True
        supported = [c for c in report['cases'] if 'negative' not in c['name'] and 'nonuniform' not in c['name']]
        report['supported_rotation_pass'] = all(c['summary']['max_hand_R_error_degrees'] < .005 and c['summary']['max_R_wrist_shift'] < 2e-5 for c in supported)
        assert report['supported_rotation_pass'], 'Positive uniform rotation contract failed'
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    report['source_unchanged'] = hashlib.sha256(path.read_bytes()).hexdigest() == digest
    name = 'wrist_upgrade_0544_stress.json'
    (OUT / name).write_text(json.dumps(report, indent=2), encoding='utf8')
    print('PARENT_DELTA_STRESS_COMPLETE', report['ok'], report.get('error'), flush=True)
    assert report['ok'] and report['source_unchanged'], report.get('error')


if __name__ == '__main__':
    main()
