"""Real Cosha terminal-length probe for a disposable background Blender process.

The caller starts Blender --background --factory-startup and sets
CD_BONE_LENGTH_ADDON_DIR to a frozen candidate package. This script never starts
another process, registers the add-on, saves a .blend, or writes Unity assets.
Only the explicit saved X source and Unity manifest are read. All new artifacts
are confined to this validation directory.
"""

import argparse
from array import array
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import traceback

import bpy
from mathutils import Matrix


HERE = Path(__file__).resolve().parent
ARTIST = HERE.parents[1] / 'X.blend'
UNITY_MANIFEST = Path(r'D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha\Cosha.cdesigner.json')
STAGE = HERE / 'real_model_probe_verified'
MODEL_NAME = 'CoshaProbe.fbx'
LEAVES = ('eye.L', 'eye.R', 'thumb.03.L', 'thumb.03.R')
FRAMES = (1, 7, 15)
TOLERANCE = 2e-5
EXPECTED_BONES = 217


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                     allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, 'Cannot load frozen module: ' + str(path))
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def flat(matrix):
    return tuple(float(value) for row in matrix for value in row)


def maximum_error(first, second):
    require(len(first) == len(second), 'Numeric comparison changed array size.')
    return max((abs(a - b) for a, b in zip(first, second)), default=0.0)


def coordinates(data):
    values = array('f', [0.0]) * (len(data) * 3)
    data.foreach_get('co', values)
    require(all(math.isfinite(value) for value in values), 'A coordinate array is non-finite.')
    return values


def coordinate_sha(data):
    return hashlib.sha256(coordinates(data).tobytes()).hexdigest()


def native_rest(rig):
    return {
        bone.name: {
            'matrix': flat(bone.matrix_local), 'head': tuple(bone.head_local),
            'tail': tuple(bone.tail_local), 'length': float(bone.length),
            'parent': bone.parent.name if bone.parent else None,
            'connected': bool(bone.use_connect), 'deform': bool(bone.use_deform),
            'inherit_scale': bone.inherit_scale, 'bbone_segments': bone.bbone_segments,
        }
        for bone in rig.data.bones
    }


def world_length_meters(rig, bone, unit_scale):
    return float(((rig.matrix_world @ bone.tail_local) -
                  (rig.matrix_world @ bone.head_local)).length * unit_scale)


def mesh_inventory(mesh):
    names = {group.index: group.name for group in mesh.vertex_groups}
    weights = [sorted((names[item.group], float(item.weight)) for item in vertex.groups)
               for vertex in mesh.data.vertices]
    keys = mesh.data.shape_keys
    shapes = []
    for key in keys.key_blocks if keys else ():
        shapes.append({'name': key.name, 'value': float(key.value), 'mute': bool(key.mute),
                       'relative_key': key.relative_key.name, 'vertex_group': key.vertex_group,
                       'coordinates_sha256': coordinate_sha(key.data)})
    return {
        'data_name': mesh.data.name, 'vertices': len(mesh.data.vertices),
        'raw_coordinates_sha256': coordinate_sha(mesh.data.vertices),
        'topology_sha256': canonical_sha([tuple(face.vertices) for face in mesh.data.polygons]),
        'vertex_groups': sorted(names.values()), 'weights_sha256': canonical_sha(weights),
        'shape_keys': shapes, 'matrix_world': flat(mesh.matrix_world),
        'modifiers': [
            {'name': mod.name, 'type': mod.type,
             'rig': mod.object.name if mod.type == 'ARMATURE' and mod.object else None,
             'vertex_groups': bool(mod.use_vertex_groups) if mod.type == 'ARMATURE' else None,
             'envelopes': bool(mod.use_bone_envelopes) if mod.type == 'ARMATURE' else None,
             'preserve_volume': bool(mod.use_deform_preserve_volume) if mod.type == 'ARMATURE' else None}
            for mod in mesh.modifiers
        ],
    }


def action_curves(action):
    if action is None:
        return []
    result = list(getattr(action, 'fcurves', ()))
    for layer in getattr(action, 'layers', ()):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', ()):
                result.extend(bag.fcurves)
    return list({curve.as_pointer(): curve for curve in result}.values())


def action_inventory(rig):
    animation = rig.animation_data
    action = animation.action if animation else None
    return {
        'name': action.name if action else None,
        'slot': animation.action_slot.handle if animation and animation.action_slot else None,
        'curves': sorted(
            (curve.data_path, curve.array_index, bool(curve.mute),
             [(tuple(key.co), key.interpolation, tuple(key.handle_left), tuple(key.handle_right))
              for key in curve.keyframe_points])
            for curve in action_curves(action)
        ),
    }


def install_owned_pose_animation(rig):
    require(rig.animation_data is None or rig.animation_data.action is None,
            'An unexpected imported Action is attached; do not replace it.')
    rig.data.pose_position = 'POSE'
    rotations = {
        'eye.L': (.20, -.10, .06), 'eye.R': (-.16, .08, -.05),
        'thumb.01.L': (.22, -.14, .10), 'thumb.02.L': (.08, .17, -.09),
        'thumb.03.L': (.05, .16, .21),
        'thumb.01.R': (.22, .14, -.10), 'thumb.02.R': (.08, -.17, .09),
        'thumb.03.R': (.05, -.16, -.21),
    }
    missing = sorted(set(rotations) - set(rig.pose.bones.keys()))
    require(not missing, 'Native pose probe bones are missing: ' + repr(missing))
    for name, rotation in rotations.items():
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'XYZ'
        for frame, factor in ((1, 0.0), (7, 1.0), (15, -.65)):
            bone.rotation_euler = tuple(factor * value for value in rotation)
            result = bone.keyframe_insert(data_path='rotation_euler', frame=frame)
            require(result, 'Cannot key native test pose: ' + name)
    require(rig.animation_data is not None and rig.animation_data.action is not None,
            'Native test Action was not created.')
    rig.animation_data.action.name = 'Cosha terminal-length isolated rotation probe'
    bpy.context.scene.frame_set(7)
    bpy.context.view_layer.update()


def samples(rig, meshes):
    scene = bpy.context.scene
    current = scene.frame_current
    result = {}
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = rig.evaluated_get(depsgraph)
        row = {'pose': {bone.name: flat(bone.matrix) for bone in evaluated.pose.bones},
               'basis': {bone.name: flat(bone.matrix_basis) for bone in rig.pose.bones},
               'surfaces': {}}
        for mesh in meshes:
            obj = mesh.evaluated_get(depsgraph)
            data = obj.to_mesh()
            try:
                require(data is not None, 'Evaluated mesh is missing: ' + mesh.name)
                row['surfaces'][mesh.name] = coordinates(data.vertices)
            finally:
                obj.to_mesh_clear()
        result[frame] = row
    scene.frame_set(current)
    bpy.context.view_layer.update()
    return result


def compare_samples(before, after):
    require(set(before) == set(after) == set(FRAMES), 'Sample frames changed.')
    result = {}
    for frame in FRAMES:
        first, second = before[frame], after[frame]
        require(set(first['pose']) == set(second['pose']), 'Pose bone inventory changed.')
        require(len(first['pose']) == EXPECTED_BONES, 'Pose sample did not contain 217 bones.')
        pose = {name: maximum_error(values, second['pose'][name])
                for name, values in first['pose'].items()}
        basis = {name: maximum_error(values, second['basis'][name])
                 for name, values in first['basis'].items()}
        require(set(first['surfaces']) == set(second['surfaces']), 'Sample mesh inventory changed.')
        surfaces = {}
        for name, expected in first['surfaces'].items():
            actual = second['surfaces'][name]
            error = maximum_error(expected, actual)
            # Compare deformation in physical world meters, since this export
            # preserves different local coordinate scales for its five meshes.
            basis_world = bpy.data.objects[name].matrix_world.to_3x3()
            max_world = 0.0
            for index in range(0, len(expected), 3):
                delta = tuple(actual[index + axis] - expected[index + axis] for axis in range(3))
                for row in basis_world:
                    max_world = max(max_world, abs(sum(row[axis] * delta[axis] for axis in range(3))))
            surfaces[name] = {'vertices': len(expected) // 3, 'max_local_coordinate_error': error,
                              'max_world_coordinate_error_meters': max_world}
        result[frame] = {'bone_count': len(pose), 'max_pose_matrix_error': max(pose.values()),
                         'max_basis_matrix_error': max(basis.values()), 'meshes': surfaces}
        require(max(pose.values()) <= TOLERANCE and max(basis.values()) <= TOLERANCE
                and all(row['max_world_coordinate_error_meters'] <= TOLERANCE for row in surfaces.values()),
                'Restoring terminal lengths changed evaluated pose or mesh at frame ' + str(frame))
    return result


def compare_rest(before, after, records):
    require(set(before) == set(after) == set(records), 'Complete imported bone inventory changed.')
    require(len(before) == EXPECTED_BONES, 'Imported skeleton does not contain exactly 217 bones.')
    rows = {}
    changed_tails = []
    for name, first in before.items():
        second = after[name]
        matrix_error = maximum_error(first['matrix'], second['matrix'])
        head_error = maximum_error(first['head'], second['head'])
        parent_equal = first['parent'] == second['parent']
        flags_equal = all(first[field] == second[field] for field in
                          ('connected', 'deform', 'inherit_scale', 'bbone_segments'))
        tail_error = maximum_error(first['tail'], second['tail'])
        if tail_error > 1e-7:
            changed_tails.append(name)
            require(records[name]['terminal'] and records[name]['restore'],
                    'A non-restorable bone tail changed: ' + name)
        require(matrix_error <= TOLERANCE and head_error <= TOLERANCE and parent_equal and flags_equal,
                'Restoring length changed the native bind/head/parent/flags: ' + name)
        rows[name] = {'matrix_error': matrix_error, 'head_error': head_error,
                      'parent_equal': parent_equal, 'flags_equal': flags_equal,
                      'tail_error': tail_error, 'length_before': first['length'],
                      'length_after': second['length']}
    return {'bone_count': len(rows), 'max_rest_matrix_error': max(row['matrix_error'] for row in rows.values()),
            'max_head_error': max(row['head_error'] for row in rows.values()),
            'changed_tails': sorted(changed_tails), 'per_bone': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=HERE / 'probe_cosha_roundtrip_report.json')
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    args = parser.parse_args(arguments)
    report_path = args.report.resolve()
    require(report_path.is_relative_to(HERE), 'Evidence report must stay in this validation directory.')
    require(not report_path.exists(), 'Evidence report already exists; choose a fresh --report path.')
    require(bpy.app.background, 'Run only in an isolated background Blender process.')
    require(not bpy.data.filepath, 'Start with --factory-startup; do not run inside an opened artist session.')
    report = {'passed': False, 'scope': 'ISOLATED_REAL_MODEL_TERMINAL_LENGTH_ROUNDTRIP',
              'Blender_version': bpy.app.version_string, 'saved_blend': False,
              'Unity_written': False, 'tolerance_local': TOLERANCE, 'samples': {}}
    source_sha = manifest_sha = None
    try:
        addon_setting = os.environ.get('CD_BONE_LENGTH_ADDON_DIR')
        require(bool(addon_setting), 'CD_BONE_LENGTH_ADDON_DIR must identify the frozen candidate package.')
        addon_dir = Path(addon_setting).resolve()
        worker_path, helper_path = addon_dir / 'unity_export_worker.py', addon_dir / 'bone_rest_lengths.py'
        require(worker_path.is_file() and helper_path.is_file(), 'Frozen worker/helper files are missing.')
        require(ARTIST.is_file() and UNITY_MANIFEST.is_file(), 'Saved X or authoritative Unity manifest is missing.')
        require(not STAGE.exists(), 'real_model_probe already exists; do not overwrite prior evidence.')
        source_sha, manifest_sha = sha(ARTIST), sha(UNITY_MANIFEST)
        report.update(source_blend=str(ARTIST), source_sha256=source_sha,
                      manifest=str(UNITY_MANIFEST), manifest_sha256=manifest_sha,
                      frozen_addon_dir=str(addon_dir), worker_sha256=sha(worker_path),
                      helper_sha256=sha(helper_path))
        manifest = json.loads(UNITY_MANIFEST.read_text(encoding='utf-8'))
        require(type(manifest) is dict and manifest.get('schema') == 'cdesigner.unity-character.v1',
                'Unity manifest has no recognized model schema.')
        names, rig_name = manifest.get('objects'), manifest.get('source_rig')
        require(type(names) is list and len(names) == 6 and len(set(names)) == 6
                and all(type(name) is str and name for name in names),
                'Unity manifest must supply six unique explicit object names.')
        require(type(rig_name) is str and rig_name in names, 'Unity manifest source_rig is missing from its objects.')
        worker = module('cosha_length_probe_worker', worker_path)
        lengths = module('cosha_length_probe_helper', helper_path)
        # Textures are outside this bone/skin probe. Keep the frozen geometry
        # exporter intact while avoiding image-pixel extraction/conversion.
        def omit_texture_publication(objects, stage, warnings):
            materials = {material.name for obj in objects if obj.type == 'MESH'
                         for material in obj.data.materials if material is not None}
            return sorted(materials), []
        worker._export_textures = omit_texture_publication
        report['texture_publication_omitted_for_bone_skin_scope'] = True
        opened = bpy.ops.wm.open_mainfile(filepath=str(ARTIST), load_ui=False, use_scripts=False)
        require('FINISHED' in opened and Path(bpy.data.filepath).resolve() == ARTIST.resolve(),
                'Saved artist input did not open in this background process.')
        missing = [name for name in names if bpy.data.objects.get(name) is None]
        require(not missing, 'Explicit source objects are missing: ' + repr(missing))
        objects = [bpy.data.objects[name] for name in names]
        rig = bpy.data.objects[rig_name]
        require(rig.type == 'ARMATURE' and sum(obj.type == 'ARMATURE' for obj in objects) == 1
                and sum(obj.type == 'MESH' for obj in objects) == 5,
                'Explicit source inventory must contain one rig and five meshes.')
        missing = [name for name in LEAVES if name not in rig.data.bones]
        require(not missing, 'Expected source terminal bones are missing: ' + repr(missing))
        require(all(not rig.data.bones[name].children for name in LEAVES),
                'An expected source leaf now has children; do not infer terminal recovery.')
        scenes = [scene for scene in bpy.data.scenes if all(name in scene.objects for name in names)]
        require(len(scenes) == 1, 'The six source objects do not identify one unambiguous saved Scene.')
        bpy.context.window.scene = scenes[0]
        unit_scale = float(scenes[0].unit_settings.scale_length)
        require(math.isfinite(unit_scale) and unit_scale > 0, 'Source Scene has invalid unit scale.')
        owned_keys = {}
        for obj in objects:
            if obj.type != 'MESH':
                continue
            keys = obj.data.shape_keys
            owned_keys[obj.name] = [key.name for key in keys.key_blocks
                                    if key.name.startswith('CD Forearm Twist')] if keys else []
        require(any(owned_keys.values()), 'Expected Forearm Twist Shape Keys are missing; do not silently change probe scope.')
        report.update(source_scene=scenes[0].name, source_frame=scenes[0].frame_current,
                      source_rig=rig_name, source_objects=names, owned_keys_stripped=owned_keys,
                      forearm_companion_tested=False, source_unit_scale=unit_scale)
        # The real character has configured Hair motion. Supply the same
        # validated native proof the normal host captures; never bypass the
        # worker's single-source inventory gate for this integration fixture.
        registry_service, profile_service, _hair_export = worker._hair_services()
        hair_sources = [obj for obj in objects if obj.type == 'MESH' and profile_service.PROFILE_KEY in obj]
        require(len(hair_sources) == 1, 'Expected exactly one configured native Hair source.')
        hair_source = hair_sources[0]
        hair_rig = hair_source.get(registry_service.hair.RIG_KEY)
        require(hair_rig == rig, 'The configured Hair source uses another armature.')
        hair_registry = registry_service.read(hair_source, validate=True)
        hair_profiles = profile_service.effective_all(hair_source, registry=hair_registry)
        hair_capture = {'source': hair_source.name, 'rig': hair_rig.name,
                        'registry': hair_registry, 'profiles': hair_profiles, 'tool_version': '0.77.17'}
        report['hair_capture_included'] = True
        job = {'objects': names, 'rig': rig_name, 'rigs': [rig_name],
               'asset_id': manifest['asset_id'],
               'stage': str(STAGE), 'filename': MODEL_NAME, 'unit_scale': unit_scale,
               'owned_keys': owned_keys, 'forearm': {}, 'had_forearm': False,
               'hair_motion': hair_capture, 'warnings': []}
        result = worker.export_job(job)
        require(result.get('ok') is True, 'Frozen worker did not complete export.')
        payload = result.get('bone_rest_lengths')
        require(payload is not None, 'Frozen worker omitted bone_rest_lengths; this probe must not fall back to legacy import.')
        model = STAGE / MODEL_NAME
        require(model.is_file(), 'The isolated model FBX is missing.')
        digest = sha(model)
        records = lengths._validate(payload, digest, rig_name)
        require(len(records) == EXPECTED_BONES and set(records) == set(rig.data.bones.keys()),
                'Worker metadata does not cover the complete 217-bone source rig.')
        expected_names = manifest.get('rigs', {}).get(rig_name)
        require(type(expected_names) is list and len(expected_names) == EXPECTED_BONES
                and set(expected_names) == set(records),
                'Current source skeleton differs from the authoritative 217-bone model inventory.')
        source_lengths = {name: world_length_meters(rig, rig.data.bones[name], unit_scale) for name in LEAVES}
        for name in LEAVES:
            require(records[name]['terminal'] and records[name]['restore'],
                    'Expected leaf is not safely restorable: ' + name)
            require(abs(source_lengths[name] - records[name]['length']) <= TOLERANCE,
                    'Export metadata length differs from native source measurement: ' + name)
        file_hashes = {}
        for relative in result['files']:
            path = (STAGE / relative).resolve()
            require(path.is_relative_to(STAGE.resolve()) and path.is_file(),
                    'Worker reported an absent or external publication file: ' + str(relative))
            file_hashes[relative] = sha(path)
        fixture_manifest = dict(result)
        fixture_manifest.update(schema='cdesigner.unity-character.v1', filename=MODEL_NAME,
                                source_rig=rig_name, files=file_hashes)
        fixture_path = model.with_suffix('.cdesigner.json')
        fixture_path.write_text(json.dumps(fixture_manifest, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        report.update(export_result=result, fbx=str(model), fbx_sha256=digest,
                      fixture_manifest=str(fixture_path), fixture_manifest_sha256=sha(fixture_path),
                      source_leaf_lengths_meters=source_lengths)
        require(lengths.load(model, digest, rig_name) == payload, 'Hash-bound fixture manifest did not reload exactly.')

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = unit_scale
        bpy.ops.preferences.addon_enable(module='io_scene_fbx')
        imported = bpy.ops.import_scene.fbx(
            filepath=str(model), use_anim=False, automatic_bone_orientation=False,
            force_connect_children=False, primary_bone_axis='Y', secondary_bone_axis='X',
            use_custom_props=False, use_image_search=False)
        require('FINISHED' in imported, 'The isolated FBX import failed.')
        imported_rigs = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
        require(len(imported_rigs) == 1, 'Reimport did not produce exactly one independent rig.')
        rig = imported_rigs[0]
        require(rig.name == rig_name and set(rig.data.bones.keys()) == set(records),
                'Reimport changed source rig identity or retained bone inventory.')
        # Source Object RNA references were invalidated by factory reset. Use
        # the names from the authoritative, explicit manifest instead.
        mesh_names = set(names) - {rig_name}
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        require(len(meshes) == 5 and {obj.name for obj in meshes} == mesh_names,
                'Reimport changed the explicit five-mesh inventory.')
        for mesh in meshes:
            skins = [mod for mod in mesh.modifiers if mod.type == 'ARMATURE']
            require(len(skins) == 1 and skins[0].object == rig and skins[0].use_vertex_groups
                    and not skins[0].use_bone_envelopes and not skins[0].use_deform_preserve_volume,
                    'Reimport is not ordinary vertex-group linear skinning: ' + mesh.name)
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        install_owned_pose_animation(rig)
        before_rest = native_rest(rig)
        before_meshes = {mesh.name: mesh_inventory(mesh) for mesh in meshes}
        before_action = action_inventory(rig)
        before_world = flat(rig.matrix_world)
        before_samples = samples(rig, meshes)
        before_lengths = {name: world_length_meters(rig, rig.data.bones[name], unit_scale) for name in LEAVES}
        changed = lengths.restore(bpy.context, rig, lengths.load(model, digest, rig_name),
                                  digest, rig_name, meters_per_unit=unit_scale)
        require(changed > 0, 'The real reimport did not exercise any terminal-length restoration.')
        after_rest = native_rest(rig)
        after_lengths = {name: world_length_meters(rig, rig.data.bones[name], unit_scale) for name in LEAVES}
        report['rest_comparison'] = compare_rest(before_rest, after_rest, records)
        report['leaf_lengths'] = {}
        for name in LEAVES:
            row = {'source_meters': source_lengths[name], 'imported_before_meters': before_lengths[name],
                   'restored_after_meters': after_lengths[name],
                   'error_meters': abs(after_lengths[name] - source_lengths[name])}
            report['leaf_lengths'][name] = row
            print('COSHA_LEAF_LENGTH', name, json.dumps(row, sort_keys=True), flush=True)
            require(row['error_meters'] <= TOLERANCE, 'A real leaf length was not recovered: ' + name)
            require(abs(before_lengths[name] - after_lengths[name]) > 1e-6,
                    'A required real leaf did not exercise a changed import length: ' + name)
        after_meshes = {mesh.name: mesh_inventory(mesh) for mesh in meshes}
        require(before_meshes == after_meshes, 'Weights, Shape Keys, geometry, modifier or Object inventory changed.')
        require(before_action == action_inventory(rig), 'The owned native test Action changed during recovery.')
        require(maximum_error(before_world, flat(rig.matrix_world)) <= TOLERANCE,
                'Length recovery changed the rig Object matrix.')
        after_samples = samples(rig, meshes)
        report['samples'] = compare_samples(before_samples, after_samples)
        report.update(restored_bones=changed, weights_and_shape_keys_inventory_unchanged=True,
                      native_action_unchanged=True, meshes_inventory=after_meshes,
                      imported_rest_before=before_rest, imported_rest_after=after_rest,
                      passed=True)
    except Exception:
        report['error'] = traceback.format_exc()
        report['passed'] = False
    finally:
        report['source_file_unchanged'] = source_sha is not None and ARTIST.is_file() and sha(ARTIST) == source_sha
        report['Unity_manifest_unchanged'] = manifest_sha is not None and UNITY_MANIFEST.is_file() and sha(UNITY_MANIFEST) == manifest_sha
        report['passed'] = bool(report.get('passed') and report['source_file_unchanged'] and report['Unity_manifest_unchanged'])
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        print('COSHA_LENGTH_ROUNDTRIP_REPORT', str(report_path), 'PASS' if report['passed'] else 'FAIL', flush=True)
    if not report['passed']:
        raise RuntimeError('Real Cosha terminal-length verification failed; inspect the JSON report.')


if __name__ == '__main__':
    main()
