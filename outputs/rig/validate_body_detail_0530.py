"""Real-X integration check; read X and save only a disposable preview copy."""
import bpy
import hashlib
import importlib.util
import json
import sys
import traceback
from array import array
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
SOURCE = ROOT / 'X.blend'
PREVIEW = OUT / 'X_body_detail_0530_preview.blend'
REPORT = OUT / 'body_detail_0530_validation.json'
GEOMETRY = OUT / 'body_detail_0530_geometry.json'
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import (
    body_detail_visuals as detail, control_colors, root_control,
    head_neck_visuals, eye_controls, limb_ik, limb_ik_fk,
)

# Reuse the read-only serializers; its guarded main is not executed.
spec = importlib.util.spec_from_file_location('root_verification_helpers', OUT / 'verify_root_height_0523_saved.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
digest, plain, rna_values = helpers.digest, helpers.plain, helpers.rna_values


def update():
    limb_ik_fk._update(bpy.context, rig)


def validate_existing():
    limb_ik._validate_inventory(rig)
    root_control.validate(rig)
    head_neck_visuals.validate(rig)
    eye_controls.validate(rig)


def state_snapshot(original_names):
    update()
    result = {'objects': [], 'meshes': [], 'rest': [], 'basis': [], 'constraints': [],
              'actions': helpers.animation_state(), 'displays': {}, 'colors': {},
              'poses': {}, 'records': {key: plain(rig.data[key]) for key in rig.data.keys()
                         if key not in (detail.RECORD_KEY, detail.ID_KEY, detail.REFERENCE_KEY)}}
    for name in sorted(original_names):
        obj = bpy.data.objects[name]
        result['objects'].append([name, obj.type, plain(obj.matrix_world), plain(obj.matrix_basis),
                                  plain(obj.data), [rna_values(mod) for mod in obj.modifiers]])
        if obj.type == 'MESH':
            mesh = obj.data
            result['meshes'].append([name, mesh.name, [list(v.co) for v in mesh.vertices],
                                    [list(e.vertices) for e in mesh.edges],
                                    [list(p.vertices) for p in mesh.polygons],
                                    [g.name for g in obj.vertex_groups],
                                    [[(g.group, g.weight) for g in v.groups] for v in mesh.vertices],
                                    None if mesh.shape_keys is None else [
                                        [k.name, k.value, [list(p.co) for p in k.data]]
                                        for k in mesh.shape_keys.key_blocks]])
        result['constraints'].append([name, [rna_values(con) for con in obj.constraints]])
        if obj.type != 'ARMATURE':
            continue
        for pb in sorted(obj.pose.bones, key=lambda item: item.name):
            key = name + '/' + pb.name
            result['rest'].append([key, root_control._state(pb.bone)])
            result['basis'].append([key, plain(pb.matrix_basis), pb.rotation_mode,
                                    list(pb.location), list(pb.rotation_euler),
                                    list(pb.rotation_quaternion), list(pb.rotation_axis_angle), list(pb.scale)])
            result['constraints'].append([key, [rna_values(con) for con in pb.constraints]])
            result['displays'][key] = limb_ik._pose_shape_json_state(pb)
            result['colors'][key] = control_colors.capture_bone(pb)
            result['poses'][key] = plain(pb.matrix)
    for key in ('objects', 'meshes', 'rest', 'basis', 'constraints', 'actions', 'records'):
        result[key] = digest(result[key])
    return result


def compare(before, after, allow_details=False):
    for key in ('objects', 'meshes', 'rest', 'basis', 'constraints', 'actions', 'records'):
        assert before[key] == after[key], 'Unexpected change in ' + key
    allow = {rig.name + '/' + name for name in ('Hips', 'breast.L', 'breast.R')} if allow_details else set()
    for key in ('displays', 'colors'):
        assert before[key].keys() == after[key].keys(), key + ' bone set changed.'
        changed = {name for name in before[key] if before[key][name] != after[key][name]}
        assert changed <= allow, 'Unexpected ' + key + ' changes: ' + ', '.join(changed - allow)
    assert before['poses'].keys() == after['poses'].keys()
    error = max(abs(after['poses'][name][i][j] - matrix[i][j])
                for name, matrix in before['poses'].items() for i in range(4) for j in range(4))
    assert error < 3e-6, ('Evaluated pose changed', error)
    return error


def evaluated_meshes():
    update()
    result = {}
    dg = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
            continue
        evaluated = obj.evaluated_get(dg)
        mesh = evaluated.to_mesh()
        try:
            coords = array('f', [0.]) * (len(mesh.vertices) * 3)
            mesh.vertices.foreach_get('co', coords)
            result[obj.name] = coords
        finally:
            evaluated.to_mesh_clear()
    return result


def mesh_errors(before):
    after = evaluated_meshes()
    assert before.keys() == after.keys()
    return {name: max((abs(a - b) for a, b in zip(coords, after[name])), default=0.)
            for name, coords in before.items()}


def ring_geometry(record):
    result = {'coordinate_space': 'armature', 'fit': record['fit'], 'rings': {}, 'meshes': {}}
    rest_points, pose_points = [], []
    for name, entry in record['bindings'].items():
        pb = rig.pose.bones[name]
        anchor = pb.custom_shape_transform or pb
        scale = pb.custom_shape_scale_xyz * (pb.bone.length if pb.use_custom_shape_bone_size else 1.)
        local = Matrix.LocRotScale(pb.custom_shape_translation, pb.custom_shape_rotation_euler.to_quaternion(), scale)
        rest = [anchor.bone.matrix_local @ local @ v.co for v in pb.custom_shape.data.vertices]
        pose = [anchor.matrix @ local @ v.co for v in pb.custom_shape.data.vertices]
        result['rings'][entry['role']] = {'bone': name, 'rest': plain(rest), 'pose': plain(pose),
            'edges': [list(e.vertices) for e in pb.custom_shape.data.edges],
            'head_rest': list(pb.bone.head_local), 'tail_rest': list(pb.bone.tail_local),
            'head_pose': list(pb.head), 'tail_pose': list(pb.tail)}
        rest_points.extend(rest)
        pose_points.extend(pose)
    dg = bpy.context.evaluated_depsgraph_get()
    source_names = {record['fit'].get('body'), *record['fit'].get('clothing', []),
                    *record['fit'].get('skirts', []), 'Cosha', 'Clothes'}
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.name not in source_names:
            continue
        entry = {}
        evaluated = obj.evaluated_get(dg)
        evaluated_mesh = evaluated.to_mesh()
        try:
            for mode, mesh, transform, points in (
                ('rest', obj.data, rig.matrix_world.inverted_safe() @ obj.matrix_world, rest_points),
                ('pose', evaluated_mesh, rig.matrix_world.inverted_safe() @ evaluated.matrix_world, pose_points),
            ):
                minimum = Vector(tuple(min(p[i] for p in points) for i in range(3)))
                maximum = Vector(tuple(max(p[i] for p in points) for i in range(3)))
                margin = max(rig.data.bones['Hips'].length * 1.5, .08)
                vertices = [transform @ vertex.co for vertex in mesh.vertices]
                nearby = {i for i, vertex in enumerate(vertices)
                          if all(minimum[axis] - margin <= vertex[axis] <= maximum[axis] + margin for axis in range(3))}
                faces = [list(poly.vertices) for poly in mesh.polygons if set(poly.vertices) & nearby]
                indices = sorted({index for face in faces for index in face})
                mapping = {old: new for new, old in enumerate(indices)}
                entry[mode] = {'vertices': [list(vertices[index]) for index in indices],
                               'faces': [[mapping[index] for index in face] for face in faces]}
            result['meshes'][obj.name] = entry
        finally:
            evaluated.to_mesh_clear()
    GEOMETRY.write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
    return {name: {mode: len(data['vertices']) for mode, data in entry.items()}
            for name, entry in result['meshes'].items()}


def main():
    global rig
    assert bpy.app.background, 'Run headlessly.'
    protected = helpers.sha_file(SOURCE)
    report = {'ok': False, 'source': str(SOURCE), 'preview': str(PREVIEW),
              'version': list(cd.bl_info['version']), 'source_sha_before': protected}
    try:
        cd.register()
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        limb_ik._mode_set(bpy.context, rig, 'POSE')
        assert detail.get_record(rig) is None, 'Saved X already has body detail controls.'
        original_names = set(bpy.data.objects.keys())
        master = rig.pose.bones['CTRL_master']
        previous_translation = list(master.custom_shape_translation)
        desired_translation = list(limb_ik._master_widget_translation(rig))
        assert previous_translation == [0., 0., 0.] or max(abs(a-b) for a,b in zip(previous_translation, desired_translation)) < 1e-6
        master.custom_shape_translation = desired_translation
        report['root_translation'] = {'before': previous_translation, 'after': list(master.custom_shape_translation)}
        validate_existing()
        before = state_snapshot(original_names)
        mesh_before = evaluated_meshes()
        assert bpy.ops.character_designer.body_detail_visuals(action='BUILD') == {'FINISHED'}
        record = detail.validate(rig)
        assert set(record['bindings']) == {'Hips', 'breast.L', 'breast.R'}
        assert set(bpy.data.objects.keys()) - original_names == {entry['object'] for entry in record['bindings'].values()}
        assert len(record['bindings']) == 3
        for name in record['bindings']:
            control_colors.style(rig.pose.bones[name])
        for role in ('BREAST_L', 'BREAST_R', 'HIPS'):
            assert bpy.ops.character_designer.body_detail_visuals(action='SELECT_' + role) == {'FINISHED'}
            name = record['names'][role]
            assert rig.data.bones.active.name == name and rig.pose.bones[name].select
            assert not rig.data.bones[name].hide
            assert any(c.is_visible_effectively for c in rig.data.bones[name].collections)
            assert rig.pose.bones[name].custom_shape is not None
        after = state_snapshot(original_names)
        report['build_pose_error'] = compare(before, after, allow_details=True)
        report['build_mesh_errors'] = mesh_errors(mesh_before)
        assert max(report['build_mesh_errors'].values(), default=0.) < 3e-6
        validate_existing()
        report['geometry_mesh_counts'] = ring_geometry(record)
        report['fit'] = record['fit']
        assert bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW), copy=True) == {'FINISHED'}
        assert helpers.sha_file(SOURCE) == protected
        bpy.ops.wm.open_mainfile(filepath=str(PREVIEW), use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        limb_ik._mode_set(bpy.context, rig, 'POSE')
        record = detail.validate(rig)
        validate_existing()
        report['reopen_pose_error'] = compare(after, state_snapshot(original_names))
        report['motion'] = {}
        for name in ('Hips', 'breast.L', 'breast.R'):
            pb = rig.pose.bones[name]
            location = pb.location.copy()
            old_matrix = pb.matrix.copy()
            pb.location.x += max(pb.bone.length * .12, .005)
            update()
            bone_error = max(abs(pb.matrix[i][j] - old_matrix[i][j]) for i in range(4) for j in range(4))
            errors = mesh_errors(mesh_before)
            assert bone_error > 1e-4, (name, 'did not move')
            assert max(errors.values(), default=0.) > 1e-5, (name, 'did not deform a mesh')
            report['motion'][name] = {'bone_delta': bone_error, 'mesh_deltas': errors}
            pb.location = location
            update()
            assert max(mesh_errors(mesh_before).values(), default=0.) < 3e-6
        compare(after, state_snapshot(original_names))
        assert bpy.ops.character_designer.body_detail_visuals(action='REMOVE') == {'FINISHED'}
        assert detail.validate(rig) is None
        assert set(bpy.data.objects.keys()) == original_names
        report['remove_pose_error'] = compare(before, state_snapshot(original_names))
        assert list(rig.pose.bones['CTRL_master'].custom_shape_translation) == desired_translation
        assert max(mesh_errors(mesh_before).values(), default=0.) < 3e-6
        validate_existing()
        report.update(ok=True, reopened_verified=True, original_displays_colors_restored=True,
                      no_new_bones=True, only_three_native_shapes=True,
                      existing_geometry_weights_constraints_animation_preserved=True,
                      operators=['BUILD', 'SELECT_BREAST_L', 'SELECT_BREAST_R', 'SELECT_HIPS', 'REMOVE'])
    except Exception as exc:
        report.update(ok=False, error=str(exc), traceback=traceback.format_exc())
    finally:
        report['source_sha_after'] = helpers.sha_file(SOURCE)
        report['source_file_unchanged'] = report['source_sha_after'] == protected
        if not report['source_file_unchanged']:
            report.update(ok=False, error='Production X.blend changed during validation.')
        REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('BODY_DETAIL_0530_VALIDATION', json.dumps(report), flush=True)
    assert report['ok'], report.get('error', 'Validation failed.')


if __name__ == '__main__':
    main()
