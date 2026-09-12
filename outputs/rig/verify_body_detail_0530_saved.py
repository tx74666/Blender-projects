"""Read-only comparison of saved X against the live backup before add-on reload."""
import bpy
import importlib.util
import json
import traceback
from pathlib import Path

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
spec = importlib.util.spec_from_file_location('body_integration_helpers', OUT / 'validate_body_detail_0530.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
helpers = checks.helpers
TARGETS = {'Hips', 'breast.L', 'breast.R'}
REPORT = OUT / 'body_detail_0530_saved_verification.json'


def extra_snapshot(object_names, mesh_names):
    meshes = []
    properties = []
    for name in sorted(mesh_names):
        mesh = bpy.data.meshes[name]
        meshes.append([name, [list(v.co) for v in mesh.vertices],
                       [list(e.vertices) for e in mesh.edges],
                       [list(p.vertices) for p in mesh.polygons],
                       [[(g.group, g.weight) for g in v.groups] for v in mesh.vertices]])
        properties.append(['mesh', name, helpers.properties(mesh)])
    for name in sorted(object_names):
        obj = bpy.data.objects[name]
        properties.append(['object', name, helpers.properties(obj)])
        if obj.type == 'ARMATURE':
            for pb in sorted(obj.pose.bones, key=lambda item: item.name):
                pose = helpers.properties(pb)
                if obj.name == 'CoshaRig' and pb.name in TARGETS:
                    pose.pop(checks.control_colors.BACKUP_KEY, None)
                properties.append(['bone', name, pb.name, helpers.properties(pb.bone), pose])
    return {'all_original_meshes': helpers.digest(meshes), 'custom_properties': helpers.digest(properties)}


def main():
    assert bpy.app.background
    report = {'ok': False, 'read_only': True, 'comparison_includes_pre_reload_backup': True}
    protected = {}
    try:
        live = json.loads((OUT / 'body_detail_0530_live_result.json').read_text(encoding='utf-8'))
        assert live['ok'] and live['main_file_saved']
        backup, source = Path(live['backup']), ROOT / 'X.blend'
        protected = {path: helpers.sha_file(path) for path in (backup, source)}
        report.update(backup=str(backup), source=str(source), version=list(checks.cd.bl_info['version']))
        # Importing the service supplies validators without registering add-on
        # callbacks which might normalize data in the pre-reload backup.
        bpy.ops.wm.open_mainfile(filepath=str(backup), use_scripts=False)
        checks.rig = bpy.data.objects['CoshaRig']
        assert checks.detail.get_record(checks.rig) is None
        object_names, mesh_names = set(bpy.data.objects.keys()), set(bpy.data.meshes.keys())
        assert object_names == set(live['original_objects'])
        assert mesh_names == set(live['original_meshes'])
        before = checks.state_snapshot(object_names)
        before.update(extra_snapshot(object_names, mesh_names))
        checks.validate_existing()
        mesh_before = checks.evaluated_meshes()
        bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
        checks.rig = bpy.data.objects['CoshaRig']
        record = checks.detail.validate(checks.rig)
        assert record['id'] == live['record_id'] and set(record['bindings']) == TARGETS
        assert set(bpy.data.objects.keys()) - object_names == {entry['object'] for entry in record['bindings'].values()}
        assert set(bpy.data.meshes.keys()) - mesh_names == {entry['mesh'] for entry in record['bindings'].values()}
        after = checks.state_snapshot(object_names)
        after.update(extra_snapshot(object_names, mesh_names))
        root_key = 'CoshaRig/CTRL_master'
        old_root, new_root = dict(before['displays'][root_key]), dict(after['displays'][root_key])
        old_translation, new_translation = old_root.pop('translation'), new_root.pop('translation')
        assert old_root == new_root
        assert old_translation == live['root_before']
        assert new_translation == live['root_after']
        assert max(abs(a-b) for a,b in zip(new_translation, checks.limb_ik._master_widget_translation(checks.rig))) < 1e-6
        before['displays'][root_key]['translation'] = list(new_translation)
        error = checks.compare(before, after, allow_details=True)
        assert before['all_original_meshes'] == after['all_original_meshes']
        assert before['custom_properties'] == after['custom_properties']
        mesh_errors = checks.mesh_errors(mesh_before)
        assert max(mesh_errors.values(), default=0.) < 3e-6
        checks.validate_existing()
        for name in TARGETS:
            key = 'CoshaRig/' + name
            entry = record['bindings'][name]
            assert entry['original'] == before['displays'][key]
            assert entry['original_color'] == before['colors'][key]
            assert checks.rig.pose.bones[name].custom_shape.name == live['controls'][name]
        report.update(ok=True, reopened_verified=True, pose_error=error, evaluated_mesh_errors=mesh_errors,
                      original_object_count=len(object_names), original_mesh_count=len(mesh_names),
                      native_rest_basis_actions_constraints_unchanged=True,
                      original_geometry_weights_custom_properties_unchanged=True,
                      unrelated_displays_colors_unchanged=True,
                      recovery_states_match_live_backup=True,
                      only_allowed_changes=['3 native display shapes/colors and their recovery records', 'CTRL_master display translation'],
                      root_translation_before=old_translation, root_translation_after=new_translation,
                      validation=['body_detail', 'limb_inventory', 'root', 'head', 'eye'])
    except Exception as exc:
        report.update(ok=False, error=str(exc), traceback=traceback.format_exc())
    finally:
        hashes = {str(path): {'before': sha, 'after': helpers.sha_file(path)} for path, sha in protected.items()}
        report['file_hashes'] = hashes
        report['input_files_unchanged'] = all(entry['before'] == entry['after'] for entry in hashes.values())
        if not report['input_files_unchanged']:
            report.update(ok=False, error='An input .blend changed while verification was running.')
        REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('BODY_DETAIL_0530_SAVED_VERIFICATION', json.dumps(report), flush=True)
    assert report['ok'], report.get('error', 'Saved-file verification failed.')


if __name__ == '__main__':
    main()
