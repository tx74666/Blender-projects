"""Independent bind, shape, weight and skin oracle for the real model FBX.

Background Blender only. Inputs are read-only; the script never exports/saves a
.blend or FBX, starts another process, or writes to the artist/Unity project.
"""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).parent))
from fbx_raw_oracle import audit_raw_fbx


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coordinates(items):
    values = array('f', [0.0]) * (len(items) * 3)
    items.foreach_get('co', values)
    return np.asarray(values, dtype=np.float64).reshape((-1, 3)).copy()


def transform(points, matrix):
    mat = np.asarray([list(row) for row in matrix], dtype=np.float64)
    return points @ mat[:3, :3].T + mat[:3, 3]


def matrix_error(first, second):
    return max(abs(first[r][c] - second[r][c]) for r in range(4) for c in range(4))


def stats(values, scale=1.0):
    values = np.asarray(values, dtype=np.float64) * scale
    return {'count': int(len(values)), 'maximum_m': float(values.max(initial=0.0)),
            'rms_m': float(np.sqrt(np.mean(values * values))) if len(values) else 0.0,
            'p99_m': float(np.quantile(values, .99)) if len(values) else 0.0}


def evaluated(obj, bones):
    graph = bpy.context.evaluated_depsgraph_get()
    graph.update()
    native = obj.evaluated_get(graph)
    mesh = native.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    try:
        names = {group.index: group.name for group in obj.vertex_groups}
        weights = [{names[item.group]: float(item.weight) for item in vertex.groups
                    if item.group in names and names[item.group] in bones and item.weight > 0.0}
                   for vertex in mesh.vertices]
        return coordinates(mesh.vertices), weights
    finally:
        native.to_mesh_clear()


def zero_shapes(obj):
    keys = obj.data.shape_keys
    if keys is not None:
        for key in keys.key_blocks:
            if key != keys.reference_key:
                key.value = 0.0


def make_reference(objects, retained, shift, owned_keys):
    """Blender's native key/modifier evaluator independently supplies baked input.

    It never calls exporter _shape_inputs/_bake_mesh/_clean_skeleton or the
    forearm correction math. Masked/chained key deltas are evaluated natively.
    """
    result = {}
    for obj in objects:
        if obj.type != 'MESH':
            continue
        zero_shapes(obj)
        points, weights = evaluated(obj, retained)
        basis = points.copy()
        row = {'world': shift @ obj.matrix_world, 'vertices': basis,
               'weights': weights, 'shapes': {}, 'shape_values': {}}
        keys = obj.data.shape_keys
        omitted = set(owned_keys.get(obj.name, ()))
        if omitted and (keys is None or not omitted <= set(keys.key_blocks.keys())):
            raise ValueError(obj.name + ': a captured correction-owned ShapeKey is missing.')
        if keys is not None:
            for key in keys.key_blocks:
                if key == keys.reference_key or key.name in omitted:
                    continue
                # Captured current values are provided separately. The full
                # FBX delta is the native relative key response at weight 1.
                key.mute = False
                key.slider_max = max(1.0, key.slider_max)
                key.value = 1.0
                bpy.context.view_layer.update()
                shaped, _weights = evaluated(obj, retained)
                if shaped.shape != basis.shape:
                    raise ValueError(obj.name + ': a shape changes modifier topology.')
                row['shapes'][key.name] = shaped - basis
                key.value = 0.0
        result[obj.name] = row
    bpy.context.view_layer.update()
    return result


def descendant_names(parents, target):
    result = {target}
    while True:
        added = {name for name, parent in parents.items() if parent in result} - result
        if not added:
            return result
        result.update(added)


def rotated_frames(base, parents, operations):
    frames = {name: matrix.copy() for name, matrix in base.items()}
    for target, axis_index, degrees in operations:
        current = frames[target]
        pivot = current.translation.copy()
        axis = current.to_3x3().col[axis_index].normalized()
        rotation = (Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(degrees), 4, axis)
                    @ Matrix.Translation(-pivot))
        for name in descendant_names(parents, target) & frames.keys():
            frames[name] = rotation @ frames[name]
    return frames


def samples(base, parents):
    result = [('author_neutral', {n: m.copy() for n, m in base.items()})]
    common = Matrix.Translation((.05, -.03, .02)) @ Matrix.Rotation(.37, 4, 'Z')
    result.append(('common_rigid', {n: common @ m for n, m in base.items()}))
    combined = []
    for stem, axis, angle in (('forearm', 1, 45.), ('hand', 1, 45.), ('shin', 0, 30.), ('foot', 0, 20.)):
        for side in ('L', 'R'):
            name = stem + '.' + side
            if name not in base:
                raise ValueError('Required real joint is missing: ' + name)
            result.append((name + '_plus', rotated_frames(base, parents, [(name, axis, angle)])))
            result.append((name + '_minus', rotated_frames(base, parents, [(name, axis, -angle)])))
            combined.append((name, axis, angle))
    result.append(('combined_joints', rotated_frames(base, parents, combined)))
    return result


def set_world_pose(rig, frames):
    def depth(bone):
        count = 0
        while bone.parent is not None:
            count += 1
            bone = bone.parent
        return count
    order = sorted(rig.pose.bones, key=depth)
    rig.data.pose_position = 'POSE'
    inverse = rig.matrix_world.inverted()
    local_frames = {name: inverse @ frame for name, frame in frames.items()}
    for bone in order:
        if bone.name not in local_frames:
            continue
        parent = {}
        if bone.parent is not None:
            if bone.parent.name not in local_frames:
                raise ValueError('Requested world pose lacks parent ' + bone.parent.name)
            parent = {'parent_matrix': local_frames[bone.parent.name],
                      'parent_matrix_local': bone.parent.bone.matrix_local}
        # PoseBone.matrix setters invert the currently evaluated parent. A whole
        # hierarchy written before a graph update therefore lags by its depth.
        # Native Bone conversion accepts the requested parent explicitly and
        # respects inherit_scale/local_location/connect settings in one pass.
        basis = bone.bone.convert_local_to_pose(local_frames[bone.name], bone.bone.matrix_local,
                                                invert=True, **parent)
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = basis
    bpy.context.view_layer.update()
    actual = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    actual_frames = {name: rig.matrix_world @ actual.pose.bones[name].matrix for name in frames}
    errors = {name: matrix_error(actual_frames[name], frame) for name, frame in frames.items()}
    worst = sorted(errors, key=errors.get, reverse=True)[:5]
    return {'maximum_error': max(errors.values(), default=0.0), 'per_bone_errors': errors,
            'worst_bones': {name: {'error': errors[name],
                                   'parent': rig.data.bones[name].parent.name if rig.data.bones[name].parent else None,
                                   'inherit_scale': rig.data.bones[name].inherit_scale,
                                   'use_connect': bool(rig.data.bones[name].use_connect),
                                   'target_world': [list(row) for row in frames[name]],
                                   'actual_world': [list(row) for row in actual_frames[name]],
                                   'matrix_difference': [list(actual_frames[name][r][c] - frames[name][r][c]
                                                              for c in range(4)) for r in range(4)]}
                            for name in worst}}


def linear_skin(reference, rest, posed):
    """Independent normalized forward LBS in world space, using captured bind."""
    world = transform(reference['vertices'], reference['world'])
    total = np.zeros(len(world), dtype=np.float64)
    output = np.zeros_like(world)
    by_bone = {}
    for index, weights in enumerate(reference['weights']):
        for name, weight in weights.items():
            by_bone.setdefault(name, []).append((index, weight))
    for name, entries in by_bone.items():
        if name not in rest or name not in posed:
            raise ValueError('Actual skin references an omitted bone: ' + name)
        indices = np.asarray([item[0] for item in entries], dtype=np.int64)
        weights = np.asarray([item[1] for item in entries], dtype=np.float64)
        output[indices] += weights[:, None] * transform(world[indices], posed[name] @ rest[name].inverted())
        total[indices] += weights
    supported = total > 1e-12
    output[supported] /= total[supported, None]
    output[~supported] = world[~supported]
    return output


def import_correspondence(actual, expected, tolerance):
    direct = np.linalg.norm(actual - expected, axis=1) if actual.shape == expected.shape else None
    if direct is not None and direct.max(initial=0.0) <= tolerance:
        return np.arange(len(expected), dtype=np.int64), {'method': 'exact_vertex_order', **stats(direct)}
    tree = KDTree(len(actual))
    for index, point in enumerate(actual):
        tree.insert(Vector(point), index)
    tree.balance()
    hits = [tree.find(Vector(point)) for point in expected]
    mapping = np.asarray([hit[1] for hit in hits], dtype=np.int64)
    distances = np.asarray([hit[2] for hit in hits])
    # A nearest match alone can hide lost/split vertices. Require a bijection.
    if len(actual) != len(expected) or len(set(map(int, mapping))) != len(expected):
        raise ValueError('FBX reimport changed vertex identity; no exact skin comparison is possible.')
    if distances.max(initial=0.0) > tolerance:
        raise ValueError('FBX reimport neutral geometry differs beyond the bind tolerance.')
    return mapping, {'method': 'bijective_neutral_match', **stats(distances)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--export-proof', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--disable-forearm-correction', action='store_true',
                        help='Test ordinary FBX LBS only; omit explicitly owned keys and do not run the Unity correction sidecar.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not bpy.app.background:
        raise RuntimeError('This oracle requires isolated background Blender.')
    job = json.loads(args.job.read_text(encoding='utf-8'))
    capture = json.loads(args.capture.read_text(encoding='utf-8'))
    proof = json.loads(args.export_proof.read_text(encoding='utf-8'))
    fbx_path = Path(proof['fbx_path'])
    inputs = {str(path): sha(path) for path in (args.snapshot, args.job, args.capture, args.export_proof, fbx_path)}
    report = {'passed': False, 'inputs': inputs, 'Blender_version': bpy.app.version_string,
              'saved_blend': False, 'exported_fbx': False,
              'scope': 'NATIVE_BINARY_BIND_AND_FBX_REIMPORT_LINEAR_SKIN', 'samples': {},
              'forearm_correction': {'export_has_active_metadata': bool(job.get('forearm')),
                                     'runtime_mode': 'DISABLED', 'Unity_runtime_verified': False,
                                     'excluded_owned_shape_keys': job.get('owned_keys', {})}}
    try:
        if (not capture['passed'] or not proof['passed']
                or capture['snapshot_sha256'] != sha(args.snapshot)
                or proof['input_sha256'] != sha(args.snapshot)):
            raise ValueError('A required capture/export receipt is incomplete or has another snapshot.')
        if capture['job_sha256'] != sha(args.job) or proof['fbx_sha256'] != sha(fbx_path):
            raise ValueError('The job or real FBX no longer matches its authoritative receipt.')
        if len(job['rigs']) != 1:
            raise ValueError('This focused current-character oracle expects one rig.')
        if job.get('forearm') and not args.disable_forearm_correction:
            raise ValueError('Active forearm metadata requires explicit --disable-forearm-correction for the ordinary FBX LBS oracle.')
        scale = float(job['unit_scale'])
        tolerance = 3e-5 / scale
        bpy.ops.wm.open_mainfile(filepath=str(args.snapshot), load_ui=False, use_scripts=False)
        # Official capture writes an ID library, not an artist Scene. Loading
        # that snapshot can create an empty scene while its verified Objects
        # remain in bpy.data. Explicit inventory is checked below; also link the
        # snapshot's loaded dependencies, as the worker does for evaluation.
        if len(set(job['objects'])) != len(job['objects']):
            raise ValueError('The captured Export inventory contains duplicate names.')
        missing = [name for name in job['objects'] if bpy.data.objects.get(name) is None]
        if missing:
            raise ValueError('The captured Export inventory is absent from snapshot IDs: ' + repr(missing))
        objects = [bpy.data.objects[name] for name in job['objects']]
        rig = bpy.data.objects.get(job['rig'])
        if rig not in objects or rig.type != 'ARMATURE':
            raise ValueError('The captured Main Rig is not an Armature in the explicit inventory.')
        scene = bpy.data.scenes.new('Independent FBX Source Reference')
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = scale
        bpy.context.window.scene = scene
        cold_root_world = rig.matrix_world.copy()
        for obj in tuple(bpy.data.objects):
            scene.collection.objects.link(obj)
            if obj.animation_data:
                obj.animation_data_clear()
            if obj.data and obj.data.animation_data:
                obj.data.animation_data_clear()
            if obj.type == 'ARMATURE':
                obj.data.pose_position = 'REST'
                for bone in obj.pose.bones:
                    bone.matrix_basis = Matrix.Identity(4)
                    for constraint in tuple(bone.constraints):
                        bone.constraints.remove(constraint)
        # A newly opened library has cold matrix_world values until its parent
        # and transform dependencies have entered and updated the graph.
        bpy.context.view_layer.update()
        report['source_loaded_inventory'] = {obj.name: obj.type for obj in objects}
        report['source_loaded_dependency_count'] = len(bpy.data.objects)
        retained = set(proof['export_result']['source_rigs'][rig.name])
        source_rows = capture['source_rest'][rig.name]
        native_deform = {name for name, row in source_rows['bones'].items() if row['use_deform']}
        if not native_deform <= retained:
            raise ValueError('Export lost a captured native deform bone: ' + repr(sorted(native_deform - retained)))
        origin = Vector(proof['export_result']['origin'])
        shift = Matrix.Translation(-origin)
        source_root_world = Matrix(source_rows['object_world'])
        report['source_world_initialization'] = {
            'cold_root_world': [list(row) for row in cold_root_world],
            'initialized_root_world': [list(row) for row in rig.matrix_world],
            'captured_root_world': [list(row) for row in source_root_world],
            'cold_root_error': matrix_error(cold_root_world, source_root_world),
            'initialized_root_error': matrix_error(rig.matrix_world, source_root_world),
            'native_local_rest_error': max(matrix_error(rig.data.bones[name].matrix_local,
                                                      Matrix(source_rows['bones'][name]['matrix']))
                                           for name in retained)}
        root_world = shift @ source_root_world
        rest = {name: shift @ source_root_world @ Matrix(source_rows['bones'][name]['matrix'])
                for name in retained}
        parents = {name: row['parent'] for name, row in source_rows['bones'].items()}
        report['source_snapshot_rest_error'] = max(
            matrix_error(rig.matrix_world @ rig.data.bones[name].matrix_local,
                         source_root_world @ Matrix(source_rows['bones'][name]['matrix']))
            for name in retained)
        if report['source_snapshot_rest_error'] > 2e-5:
            raise ValueError('Snapshot native Rest differs from the captured author frame.')
        source_all_rest = {name: source_root_world @ Matrix(row['matrix'])
                           for name, row in source_rows['bones'].items()}
        original_skin_flags = {}
        # Evaluate dependencies in Rest as well (Mirror reference objects and
        # attachment rigs), without invoking the exporter's preparation code.
        for obj in tuple(bpy.data.objects):
            if obj.animation_data:
                obj.animation_data_clear()
            if obj.data and obj.data.animation_data:
                obj.data.animation_data_clear()
            if obj.type == 'ARMATURE':
                obj.data.pose_position = 'REST'
                for bone in obj.pose.bones:
                    bone.matrix_basis = Matrix.Identity(4)
                    for constraint in tuple(bone.constraints):
                        bone.constraints.remove(constraint)
        bpy.context.view_layer.update()
        worlds = {obj: obj.matrix_world.copy() for obj in objects}
        for obj in objects:
            for constraint in tuple(obj.constraints):
                obj.constraints.remove(constraint)
            if obj.parent is not None and obj.parent not in objects:
                obj.parent = None
            obj.matrix_world = worlds[obj]
            obj.hide_set(False)
            obj.hide_viewport = False
            obj.hide_render = False
            if obj.type == 'MESH':
                if obj.data.shape_keys and obj.data.shape_keys.animation_data:
                    obj.data.shape_keys.animation_data_clear()
                for modifier in obj.modifiers:
                    if modifier.type == 'ARMATURE':
                        original_skin_flags[(obj.name, modifier.name)] = modifier.show_viewport
                        modifier.show_viewport = False
        bpy.context.view_layer.update()
        # Blender skin ignores groups named for non-deforming ancestors; those
        # groups must never become active FBX skin influences.
        references = make_reference(objects, native_deform, shift, job['owned_keys'])
        for name, ref in references.items():
            ref['shape_values'] = {item['name']: item['value'] for item in capture['shape_inputs'][name]['artists']}
            if any(abs(value) > 1e-12 for value in ref['shape_values'].values()):
                raise ValueError('Focused neutral oracle requires the captured current artist defaults to be zero.')
        report['reference_meshes'] = {name: {'vertices': len(ref['vertices']), 'shape_keys': list(ref['shapes']),
                                            'weight_sum_min': min((sum(w.values()) for w in ref['weights']), default=0.0),
                                            'weight_sum_max': max((sum(w.values()) for w in ref['weights']), default=0.0)}
                                      for name, ref in references.items()}
        report['raw_fbx'] = audit_raw_fbx(fbx_path, rest, references, scale, rig.name, root_world)
        if not report['raw_fbx']['passed']:
            raise AssertionError('Serialized FBX bind, Basis, weights or shapes differ from captured source.')
        pose_samples = samples(rest, parents)
        # One separate diagnostic measures original linear skin BEFORE modifiers.
        # It is not an exported-pipeline acceptance gate.
        diagnostic_frames = dict(source_all_rest)
        diagnostic_frames.update({name: shift.inverted() @ frame
                                  for name, frame in pose_samples[-1][1].items()})
        for obj in objects:
            if obj.type == 'MESH':
                for modifier in obj.modifiers:
                    if modifier.type == 'ARMATURE':
                        modifier.use_deform_preserve_volume = False
                        modifier.show_viewport = original_skin_flags[(obj.name, modifier.name)]
        diagnostic_pose = set_world_pose(rig, diagnostic_frames)
        source_diagnostic = {}
        for obj in objects:
            if obj.type == 'MESH':
                coords, _weights = evaluated(obj, retained)
                source_diagnostic[obj.name] = transform(coords, shift @ obj.matrix_world)
        report['source_linear_before_subdivision_pose_error'] = diagnostic_pose['maximum_error']
        report['source_linear_before_subdivision_pose_diagnostic'] = diagnostic_pose
        # The rest/skin reference now lives in detached Python arrays. Import the
        # actual FBX into a new empty scene, with all automatic bone reorientation off.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = scale
        bpy.ops.preferences.addon_enable(module='io_scene_fbx')
        result = bpy.ops.import_scene.fbx(filepath=str(fbx_path), use_anim=False,
                                         automatic_bone_orientation=False, force_connect_children=False,
                                         primary_bone_axis='Y', secondary_bone_axis='X')
        if 'FINISHED' not in result:
            raise ValueError('Actual FBX import failed.')
        imported_rigs = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
        if len(imported_rigs) != 1:
            raise ValueError('Reimport produced another skeleton inventory.')
        imported_rig = imported_rigs[0]
        if set(imported_rig.data.bones.keys()) != retained:
            raise ValueError('FBX reimport changed the retained bone-name inventory.')
        imported_rest = {bone.name: imported_rig.matrix_world @ bone.matrix_local
                         for bone in imported_rig.data.bones}
        report['imported_world_rest_errors'] = {name: matrix_error(imported_rest[name], rest[name]) for name in retained}
        if max(report['imported_world_rest_errors'].values()) > 1e-4:
            raise ValueError('Reimported world bone axes/bind frames differ from the author Rest oracle.')
        imported_meshes = {name: bpy.data.objects.get(name) for name in references}
        report['imported_meshes'] = {}
        mappings = {}
        for name, obj in imported_meshes.items():
            if obj is None or obj.type != 'MESH':
                raise ValueError('A real exported mesh disappeared: ' + name)
            ref = references[name]
            zero_shapes(obj)
            points = transform(coordinates(obj.data.vertices), obj.matrix_world)
            expected = transform(ref['vertices'], ref['world'])
            mapping, details = import_correspondence(points, expected, tolerance)
            mappings[name] = mapping
            group_names = {group.index: group.name for group in obj.vertex_groups}
            actual_weights = [{group_names[item.group]: float(item.weight)
                               for item in vertex.groups if item.group in group_names and item.weight > 0}
                              for vertex in obj.data.vertices]
            weight_error = max((abs(actual_weights[int(mapping[index])].get(bone, 0.0)
                                    - wanted.get(bone, 0.0))
                                for index, wanted in enumerate(ref['weights'])
                                for bone in set(actual_weights[int(mapping[index])]) | set(wanted)), default=0.0)
            details['weight_max_abs_error'] = weight_error
            if weight_error > 1e-6:
                raise ValueError(name + ': reimport changed the source skin weights.')
            key_names = set(obj.data.shape_keys.key_blocks.keys()) - {obj.data.shape_keys.reference_key.name} if obj.data.shape_keys else set()
            if key_names != set(ref['shapes']):
                raise ValueError(name + ': reimport changed artist ShapeKey names.')
            details['shape_errors'] = {}
            if obj.data.shape_keys:
                basis = coordinates(obj.data.shape_keys.reference_key.data)
                for key_name, delta in ref['shapes'].items():
                    actual = coordinates(obj.data.shape_keys.key_blocks[key_name].data) - basis
                    # Deltas are vectors, so world translation cancels.
                    actual_world = transform(actual[mapping], obj.matrix_world) - np.asarray(obj.matrix_world.translation)
                    expected_world = transform(delta, ref['world']) - np.asarray(ref['world'].translation)
                    error = stats(np.linalg.norm(actual_world - expected_world, axis=1), scale)
                    details['shape_errors'][key_name] = error
                    if error['maximum_m'] > 3e-5:
                        raise ValueError(name + ': reimport changed the artist delta ' + key_name)
            report['imported_meshes'][name] = details
        for label, wanted in pose_samples:
            pose_diagnostic = set_world_pose(imported_rig, wanted)
            pose_error = pose_diagnostic['maximum_error']
            sample = {'bone_matrix_error': pose_error, 'bone_pose_diagnostic': pose_diagnostic, 'meshes': {}}
            report['samples'][label] = sample
            if pose_error > 2e-4:
                raise ValueError(label + ': imported bone pose does not reach independent requested world frames.')
            for name, obj in imported_meshes.items():
                actual, _weights = evaluated(obj, retained)
                actual = transform(actual, obj.matrix_world)[mappings[name]]
                expected = linear_skin(references[name], rest, wanted)
                errors = stats(np.linalg.norm(actual - expected, axis=1), scale)
                sample['meshes'][name] = errors
                if errors['maximum_m'] > 1e-4:
                    raise ValueError(label + ': actual imported skin differs from independent LBS on ' + name)
        combined_frames = pose_samples[-1][1]
        report['pipeline_diagnostic'] = {}
        for name, points in source_diagnostic.items():
            exported = linear_skin(references[name], rest, combined_frames)
            if points.shape == exported.shape:
                report['pipeline_diagnostic'][name] = {
                    'label': 'source_linear_armature_then_modifiers_vs_baked_modifiers_then_linear_skin',
                    'diagnostic_only': True, **stats(np.linalg.norm(points - exported, axis=1), scale)}
            else:
                report['pipeline_diagnostic'][name] = {'diagnostic_only': True,
                                                       'source_count': len(points), 'baked_count': len(exported)}
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        report['input_files_unchanged'] = all(sha(Path(path)) == expected for path, expected in inputs.items())
        report['passed'] = report['passed'] and report['input_files_unchanged']
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        print('REAL_FBX_ROUNDTRIP_REPORT', str(args.report), report['passed'], flush=True)
    if not report['passed']:
        raise AssertionError('Real FBX bind/skin verification failed; inspect the persisted report.')


if __name__ == '__main__':
    main()
