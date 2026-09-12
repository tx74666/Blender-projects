"""Migrate breast curvature only in memory; save a disposable preview copy."""
import bpy
import copy
import importlib
import importlib.util
import json
import traceback
from pathlib import Path
from mathutils import Matrix

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
SOURCE = ROOT / 'X.blend'
PREVIEW = OUT / 'X_body_wrap_0531_preview.blend'
REPORT = OUT / 'body_wrap_0531_validation.json'
spec = importlib.util.spec_from_file_location('body_integration_helpers', OUT / 'validate_body_detail_0530.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
helpers, service = checks.helpers, checks.detail


def widget_state(record):
    result = {entry['role']: {
        'name': name, 'object': entry['object'], 'mesh': entry['mesh'],
        'vertices': [list(v.co) for v in bpy.data.meshes[entry['mesh']].vertices],
        'edges': [list(e.vertices) for e in bpy.data.meshes[entry['mesh']].edges],
        'faces': [list(p.vertices) for p in bpy.data.meshes[entry['mesh']].polygons],
        'weights': [[(g.group, g.weight) for g in v.groups] for v in bpy.data.meshes[entry['mesh']].vertices],
        'object_settings': helpers.rna_values(bpy.data.objects[entry['object']]),
        'object_properties': helpers.properties(bpy.data.objects[entry['object']]),
        'mesh_properties': helpers.properties(bpy.data.meshes[entry['mesh']]),
    } for name, entry in record['bindings'].items()}
    for role, state in result.items():
        if role.startswith('BREAST_'):
            state['object_settings'].pop('dimensions', None)
    return result


def compare_record(old, new):
    old, new = copy.deepcopy(old), copy.deepcopy(new)
    old_profile = {role: old['fit']['roles'][role].pop('profile', None) for role in ('BREAST_L', 'BREAST_R')}
    new_profile = {role: new['fit']['roles'][role].pop('profile', None) for role in ('BREAST_L', 'BREAST_R')}
    assert old == new, 'Migration changed recovery or fitting data beyond breast profile fields.'
    assert old_profile != new_profile and set(new_profile.values()) == {'WRAP'}, 'Curvature profile did not change.'
    return {'before': old_profile, 'after': new_profile}


def capture_current():
    """Capture the open CoshaRig, allowing only breast vertices/profile to differ.

    Safe to import and call around a live add-on reload: no build, save, mode,
    display or pose operation occurs here. Evaluates the depsgraph for matrices.
    """
    global service
    for name in ('limb_ik', 'limb_ik_fk', 'root_control', 'head_neck_visuals', 'eye_controls', 'control_colors'):
        setattr(checks, name, importlib.import_module('character_designer.' + name))
    service = checks.detail = importlib.import_module('character_designer.body_detail_visuals')
    checks.rig = bpy.data.objects['CoshaRig']
    record = service.validate(checks.rig)
    assert record and set(record['bindings']) == {'Hips', 'breast.L', 'breast.R'}
    breast = [entry for entry in record['bindings'].values() if entry['role'].startswith('BREAST_')]
    breast_objects, breast_meshes = {entry['object'] for entry in breast}, {entry['mesh'] for entry in breast}
    objects = set(bpy.data.objects.keys())
    normalized = copy.deepcopy(record)
    for role in ('BREAST_L', 'BREAST_R'):
        normalized['fit']['roles'][role].pop('profile', None)
    widgets = widget_state(record)
    for role in ('BREAST_L', 'BREAST_R'):
        widgets[role].pop('vertices')
    custom = []
    for obj in sorted(bpy.data.objects, key=lambda obj: obj.name):
        custom.append(['object', obj.name, helpers.properties(obj)])
        if obj.type == 'ARMATURE':
            data = helpers.properties(obj.data)
            if obj == checks.rig:
                data.pop(service.RECORD_KEY, None)
            custom.append(['armature', obj.name, data])
            for pb in sorted(obj.pose.bones, key=lambda pb: pb.name):
                custom.append(['bone', obj.name, pb.name, helpers.properties(pb.bone), helpers.properties(pb)])
    all_meshes = []
    for mesh in sorted(bpy.data.meshes, key=lambda mesh: mesh.name):
        custom.append(['mesh', mesh.name, helpers.properties(mesh)])
        if mesh.name not in breast_meshes:
            all_meshes.append([mesh.name, [list(v.co) for v in mesh.vertices],
                [list(e.vertices) for e in mesh.edges], [list(p.vertices) for p in mesh.polygons],
                [[(g.group, g.weight) for g in v.groups] for v in mesh.vertices]])
    return {'state': checks.state_snapshot(objects - breast_objects),
            'objects': sorted(objects), 'meshes': sorted(bpy.data.meshes.keys()),
            'normalized_record': normalized, 'widget_settings': widgets,
            'all_other_meshes': helpers.digest(all_meshes), 'custom_properties': helpers.digest(custom)}


def assert_unchanged(before, after):
    """Assert capture_current() snapshots differ only in permitted visual data."""
    pose_error = checks.compare(before['state'], after['state'])
    for key in before.keys() - {'state'}:
        assert before[key] == after[key], 'Unexpected change in ' + key
    return pose_error


def anatomical_points(record, role):
    name = record['names'][role]
    transform = Matrix(record['fit']['frame']).inverted() @ checks.rig.data.bones[name].matrix_local
    return [transform @ v.co for v in checks.rig.pose.bones[name].custom_shape.data.vertices]


def main():
    assert bpy.app.background
    source_hash = helpers.sha_file(SOURCE)
    report = {'ok': False, 'source': str(SOURCE), 'preview': str(PREVIEW), 'source_sha_before': source_hash}
    try:
        assert hasattr(service, 'update_breast_curvature'), 'Service is not ready.'
        checks.cd.register()
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False)
        checks.rig = bpy.data.objects['CoshaRig']
        bpy.context.view_layer.objects.active = checks.rig
        checks.rig.select_set(True)
        checks.limb_ik._mode_set(bpy.context, checks.rig, 'POSE')
        record = service.validate(checks.rig)
        assert record and set(record['bindings']) == {'Hips', 'breast.L', 'breast.R'}
        old_record = copy.deepcopy(record)
        preserved_before = capture_current()
        widgets_before = widget_state(record)
        breast_objects = {entry['object'] for entry in record['bindings'].values() if entry['role'].startswith('BREAST_')}
        original_objects = set(bpy.data.objects.keys())
        objects_to_compare = original_objects - breast_objects
        before = checks.state_snapshot(objects_to_compare)
        body_before = checks.evaluated_meshes()
        points_before = {role: anatomical_points(record, role) for role in ('BREAST_L', 'BREAST_R')}
        result = service.update_breast_curvature(bpy.context, checks.rig)
        record = service.validate(checks.rig)
        report['full_state_pose_error'] = assert_unchanged(preserved_before, capture_current())
        report['profile'] = compare_record(old_record, record)
        report['updated_roles'] = [role for role in ('BREAST_L', 'BREAST_R')
                                   if result['fit']['roles'][role].get('profile') == 'WRAP']
        assert set(bpy.data.objects.keys()) == original_objects
        widgets_after = widget_state(record)
        report['shape'] = {}
        for role in widgets_before:
            old, new = copy.deepcopy(widgets_before[role]), copy.deepcopy(widgets_after[role])
            old_vertices, new_vertices = old.pop('vertices'), new.pop('vertices')
            assert old == new, role + ' changed topology, weights, ownership or object settings.'
            if role == 'HIPS':
                assert old_vertices == new_vertices, 'Hips geometry changed.'
                continue
            assert old_vertices != new_vertices, role + ' curvature was not updated.'
            old_points, new_points = points_before[role], anatomical_points(record, role)
            assert len(new_points) == 64
            xz_error = max(abs(a[i]-b[i]) for a,b in zip(old_points, new_points) for i in (0, 2))
            assert xz_error < 1e-6, role + ' silhouette changed.'
            old_range = [min(p.y for p in old_points), max(p.y for p in old_points)]
            new_range = [min(p.y for p in new_points), max(p.y for p in new_points)]
            assert max(abs(a-b) for a,b in zip(old_range, new_range)) < 1e-6, 'Depth envelope changed.'
            middle_y = (new_points[0].y + new_points[32].y) * .5
            ends_y = (new_points[16].y + new_points[48].y) * .5
            assert middle_y < ends_y - 1e-5, 'Middle must sit anterior to upper and lower endpoints.'
            report['shape'][role] = {'middle_y': middle_y, 'upper_lower_y': ends_y,
                'anterior_bulge': ends_y-middle_y, 'depth_envelope_before': old_range,
                'depth_envelope_after': new_range, 'silhouette_xz_error': xz_error}
        report['pose_error'] = checks.compare(before, checks.state_snapshot(objects_to_compare))
        report['evaluated_mesh_errors'] = checks.mesh_errors(body_before)
        assert max(report['evaluated_mesh_errors'].values(), default=0.) < 3e-6
        checks.validate_existing()
        after = checks.state_snapshot(objects_to_compare)
        assert bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW), copy=True) == {'FINISHED'}
        bpy.ops.wm.open_mainfile(filepath=str(PREVIEW), use_scripts=False)
        checks.rig = bpy.data.objects['CoshaRig']
        bpy.context.view_layer.objects.active = checks.rig
        checks.rig.select_set(True)
        checks.limb_ik._mode_set(bpy.context, checks.rig, 'POSE')
        assert service.validate(checks.rig) == record
        assert widget_state(record) == widgets_after
        report['reopen_pose_error'] = checks.compare(after, checks.state_snapshot(objects_to_compare))
        checks.validate_existing()
        all_widget_objects = {entry['object'] for entry in record['bindings'].values()}
        removal_objects = original_objects - all_widget_objects
        removal_before = checks.state_snapshot(removal_objects)
        assert service.remove(bpy.context, checks.rig) == {'removed': 3}
        assert service.validate(checks.rig) is None
        assert set(bpy.data.objects.keys()) == removal_objects
        report['removal_pose_error'] = checks.compare(removal_before, checks.state_snapshot(removal_objects), allow_details=True)
        for name, entry in old_record['bindings'].items():
            assert checks.limb_ik._pose_shape_json_state(checks.rig.pose.bones[name]) == entry['original']
            assert checks.control_colors.capture_bone(checks.rig.pose.bones[name]) == entry['original_color']
        assert max(checks.mesh_errors(body_before).values(), default=0.) < 3e-6
        checks.validate_existing()
        report.update(ok=True, version=list(checks.cd.bl_info['version']), only_breast_vertices_and_profile_changed=True,
                      hips_root_display_native_pivots_poses_weights_animation_preserved=True,
                      reopened_verified=True, original_display_color_restoration_verified=True)
    except Exception as exc:
        report.update(ok=False, error=str(exc), traceback=traceback.format_exc())
    finally:
        report['source_sha_after'] = helpers.sha_file(SOURCE)
        report['source_file_unchanged'] = source_hash == report['source_sha_after']
        if not report['source_file_unchanged']:
            report.update(ok=False, error='Production source changed while validation ran.')
        REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('BODY_WRAP_0531_VALIDATION', json.dumps(report), flush=True)
    assert report['ok'], report.get('error', 'Validation failed.')


if __name__ == '__main__':
    main()
