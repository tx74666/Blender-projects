"""Real-X migration preservation checks. Never overwrite the production file."""
import bpy
import copy
import importlib.util
import json
import math
import sys
import traceback
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).parent
FIXTURE = OUT / 'fixtures/X_wrist_rotation_20260910_151851_639.blend'
PREVIEW = OUT / 'X_wrist_rotation_0545_preview.blend'
REPORT = OUT / 'wrist_rotation_0545_validation.json'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, OUT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checks = load('wrist_scene_checks', 'validate_bone_display_0540.py')
diagnostic = load('wrist_operator_checks', 'diagnose_wrist_rotation_0544.py')


def snapshot(rig):
    result = checks.capture_current(details=True)
    result['collections'] = [[c.name, c.parent.name if c.parent else None,
        c.is_visible, c.is_solo, c.is_expanded, sorted(c.bones.keys())] for c in rig.data.collections_all]
    result['visible'] = {b.name: [b.hide, b.hide_select, getattr(rig.pose.bones[b.name], 'hide', None)]
                         for b in rig.data.bones}
    return result


def unchanged(before, after, rig):
    from character_designer import limb_ik
    targets = {rig.name + '/CTRL_hand_IK.' + side for side in 'LR'}
    hands = {rig.name + '/hand.' + side for side in 'LR'}
    helpers = {rig.name + '/MCH_hand_rotation.' + side for side in 'LR'}
    a, b = before['details'], after['details']
    for original, changed in zip(a['objects'], b['objects']):
        if 'dimensions' in original[3]:
            assert max(abs(x-y) for x,y in zip(original[3]['dimensions'], changed[3]['dimensions'])) < 2e-5
            changed[3]['dimensions'] = original[3]['dimensions']
    for section in ('objects', 'meshes', 'armature_settings', 'actions'):
        if checks.digest(a[section]) != checks.digest(b[section]):
            differences = []
            def compare(x, y, path):
                if len(differences) >= 12 or x == y:
                    return
                if isinstance(x, dict) and isinstance(y, dict) and x.keys() == y.keys():
                    for key in x:
                        compare(x[key], y[key], path + '/' + str(key))
                elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
                    for index, (v,w) in enumerate(zip(x,y)):
                        compare(v,w,path+'/'+str(index))
                else:
                    differences.append([path,str(x)[:200],str(y)[:200]])
            compare(a[section], b[section], section)
            raise AssertionError('Changed ' + json.dumps(differences))
    old = {row[0]: copy.deepcopy(row) for row in a['bones']}
    new = {row[0]: copy.deepcopy(row) for row in b['bones']}
    assert set(new) - set(old) == helpers and not set(old) - set(new), 'Unexpected added/removed bones'
    for name, row in old.items():
        other = new[name]
        # Custom shapes, all native Rest data and channel locks remain exact.
        if name in hands:
            for item in (row, other):
                item[5] = dict(item[5])
                registry = json.loads(item[5][limb_ik.CONSTRAINT_REGISTRY_KEY])
                for record in registry.values():
                    record.pop('rotation_space', None)
                item[5][limb_ik.CONSTRAINT_REGISTRY_KEY] = json.dumps(registry, sort_keys=True)
                item[9] = [dict(c) for c in item[9]]
                offset_names = {key for key, record in registry.items() if record['role'] == 'AUTO_OFFSET_ROTATION'}
                end_names = {key for key, record in registry.items() if record['role'] == 'END_ROTATION'}
                for constraint in item[9]:
                    if constraint['name'] in offset_names:
                        for field in ('subtarget', 'target_space', 'owner_space', 'space_object',
                                      'space_subtarget', 'mix_mode', 'use_offset'):
                            constraint.pop(field, None)
                    elif constraint['name'] in end_names:
                        constraint.pop('target_space', None)
                        constraint.pop('owner_space', None)
        if name in targets:
            for channel in ('location', 'scale'):
                assert max(abs(x-y) for x,y in zip(row[3][channel], other[3][channel])) < 2e-6
            for item in (row, other):
                item[3] = dict(item[3])
                for field in ('rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'location', 'scale'):
                    item[3].pop(field, None)
                item[6] = None
        assert checks.digest(row) == checks.digest(other), 'Protected bone changed: ' + name
    expected_counts = dict(before['counts'], bones=before['counts']['bones'] + 2)
    assert after['counts'] == expected_counts
    helper_names = {name.split('/', 1)[1] for name in helpers}
    new_collections = [row[:5] + [[name for name in row[5] if name not in helper_names]] for row in after['collections']]
    assert before['collections'] == new_collections, 'Existing collections changed'
    assert before['visible'] == {name: value for name,value in after['visible'].items() if name not in helper_names}
    for name in helper_names:
        bone = rig.data.bones[name]
        assert not bone.use_deform and bone.hide and bone.hide_select
        assert {c.name for c in bone.collections} == {'_Internal'}
    errors = {name: max(abs(matrix[i][j]-after['poses'][name][i][j]) for i in range(4) for j in range(4))
              for name,matrix in before['poses'].items() if name not in targets}
    maximum = max(errors.values())
    assert maximum < 2e-5, str(sorted(errors.items(), key=lambda x:x[1], reverse=True)[:4])
    return maximum


def rotations(rig):
    """Use actual Blender R transforms, including View Z from the saved viewport."""
    assert bpy.app.background
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    checks.activate(rig)
    from character_designer import bone_display
    bone_display.show_controls(bpy.context, rig)
    window, area, region = next((w,a,r) for w in bpy.context.window_manager.windows
        for a in w.screen.areas if a.type == 'VIEW_3D' for r in a.regions if r.type == 'WINDOW')
    basis = {pb.name: pb.matrix_basis.copy() for pb in rig.pose.bones}
    result = []
    for side in 'LR':
        target = rig.pose.bones['CTRL_hand_IK.' + side]
        for other in rig.pose.bones:
            if hasattr(other, 'select'):
                other.select = other == target
            else:
                other.bone.select = other == target
        target.bone.hide = target.bone.hide_select = False
        if hasattr(target, 'hide'):
            target.hide = False
        rig.data.bones.active = target.bone
        baseline = diagnostic.state(rig, side)
        for orientation, axis, angle in [('VIEW','Z',x) for x in (-17,-5,5,17)] + [('GLOBAL',a,x) for a in 'XYZ' for x in (-5,5)]:
            try:
                with bpy.context.temp_override(window=window, area=area, region=region):
                    status = bpy.ops.transform.rotate(value=math.radians(angle), orient_axis=axis,
                        orient_type=orientation, constraint_axis=tuple(a == axis for a in 'XYZ'), use_proportional_edit=False)
                diagnostic.update(rig)
                change = diagnostic.delta(baseline, diagnostic.state(rig, side))
                error = (Vector(change['control']['rotation_vector_degrees']) - Vector(change['hand']['rotation_vector_degrees'])).length
                assert status == {'FINISHED'} and error < .003, (side,orientation,axis,error,change)
                result.append(dict(side=side, orientation=orientation, axis=axis, angle=angle, error_degrees=error))
            finally:
                for name,matrix in basis.items():
                    rig.pose.bones[name].matrix_basis = matrix
                diagnostic.update(rig)
    return result


def main():
    assert bpy.app.background
    import character_designer as cd
    from character_designer import limb_ik
    report = dict(ok=False, fixture=str(FIXTURE), preview=str(PREVIEW), production_file_written=False)
    protected = checks.helpers.sha_file(FIXTURE)
    try:
        cd.register()
        bpy.ops.wm.open_mainfile(filepath=str(FIXTURE), use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        checks.activate(rig)
        before = snapshot(rig)
        report['upgrade'] = limb_ik.upgrade_wrist_rotation(bpy.context, rig)
        report['pose_error'] = unchanged(before, snapshot(rig), rig)
        checks.validate_existing(rig)
        assert not limb_ik.upgrade_wrist_rotation(bpy.context, rig)['changed']
        assert bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW), copy=True) == {'FINISHED'}
        bpy.ops.wm.open_mainfile(filepath=str(PREVIEW), use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        checks.activate(rig)
        report['reopen_pose_error'] = unchanged(before, snapshot(rig), rig)
        checks.validate_existing(rig)
        report['operations'] = rotations(rig)
        report['helper_count'] = 2
        report['ok'] = True
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        report['fixture_unchanged'] = checks.helpers.sha_file(FIXTURE) == protected
        REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('WRIST_0545', json.dumps(report), flush=True)
    assert report['ok'] and report['fixture_unchanged'], report.get('error')


if __name__ == '__main__':
    main()
