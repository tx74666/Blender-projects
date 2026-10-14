"""Quantify native tail-edit rounding on an existing disposable Cosha FBX."""
import bpy
import importlib.util
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cosha_probe_utils', folder / 'probe_cosha_roundtrip.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
model = folder / 'real_model_probe_complete' / 'CoshaProbe.fbx'
payload = json.loads(model.with_suffix('.cdesigner.json').read_text(encoding='utf-8'))['bone_rest_lengths']
bpy.ops.preferences.addon_enable(module='io_scene_fbx')
bpy.ops.import_scene.fbx(filepath=str(model), use_anim=False, automatic_bone_orientation=False,
                         use_image_search=False, use_custom_props=False)
rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
probe.install_owned_pose_animation(rig)
before = probe.native_rest(rig)
samples_before = probe.samples(rig, meshes)
scale = rig.matrix_world.to_3x3().col[0].length
records = {row['name']: row for row in payload['bones']}
plan = {name: row['length'] / scale for name, row in records.items()
        if row['restore'] and abs(row['length'] / scale - rig.data.bones[name].length) > 1e-7}
for obj in bpy.context.selected_objects:
    obj.select_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for name, length in plan.items():
    rig.data.edit_bones[name].length = length
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
after = probe.native_rest(rig)
samples_after = probe.samples(rig, meshes)
errors = []
for name in before:
    error = probe.maximum_error(before[name]['matrix'], after[name]['matrix'])
    if error > 1e-7:
        errors.append({'name': name, 'rest_matrix_error': error,
                       'old_length': before[name]['length'], 'new_length': after[name]['length'],
                       'head_error': probe.maximum_error(before[name]['head'], after[name]['head']),
                       'changed': name in plan})
errors.sort(key=lambda row: row['rest_matrix_error'], reverse=True)
sample_error = {}
for frame, first in samples_before.items():
    second = samples_after[frame]
    pose_errors = sorted(({'name': name, 'error': probe.maximum_error(values, second['pose'][name])}
                          for name, values in first['pose'].items()), key=lambda row: row['error'], reverse=True)
    sample_error[frame] = {'pose_errors': pose_errors[:10],
        'max_basis_error': max(probe.maximum_error(values, second['basis'][name])
                               for name, values in first['basis'].items()),
        'mesh_errors': {name: probe.maximum_error(values, second['surfaces'][name])
                        for name, values in first['surfaces'].items()}}
result = {'changed': len(plan), 'matrix_errors': errors,
          'samples': sample_error, 'max_rest_matrix_error': max((row['rest_matrix_error'] for row in errors), default=0)}
(folder / 'tail_precision_debug.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
