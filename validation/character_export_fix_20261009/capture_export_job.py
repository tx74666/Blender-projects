"""Capture the official model Export inputs from a protected backup only.

Run in isolated background Blender. This calls shipped collection/capture APIs,
never begin_export (which launches a process), publishes nothing to Unity, and
never saves the input .blend. Snapshot/job evidence remains in --output.
"""
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import sys
import traceback
import uuid

import bpy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def float_hash(items):
    values = array('f', [0.0]) * (3 * len(items))
    items.foreach_get('co', values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def protected_fingerprint(objects):
    """Read raw bind, artist keys, weights and channels without evaluated meshes."""
    result = {}
    for obj in objects:
        row = {'matrix_world': [list(part) for part in obj.matrix_world]}
        if obj.type == 'ARMATURE':
            row.update(
                mirror_x=bool(obj.data.use_mirror_x),
                rest={bone.name: [list(part) for part in bone.matrix_local]
                      for bone in obj.data.bones},
                pose={bone.name: {'basis': [list(part) for part in bone.matrix_basis],
                                  'mode': bone.rotation_mode, 'location': list(bone.location),
                                  'euler': list(bone.rotation_euler), 'quaternion': list(bone.rotation_quaternion),
                                  'axis_angle': list(bone.rotation_axis_angle), 'scale': list(bone.scale)}
                      for bone in obj.pose.bones})
        elif obj.type == 'MESH':
            groups = [group.name for group in obj.vertex_groups]
            row.update(vertices=float_hash(obj.data.vertices),
                       weights=hashlib.sha256(repr((groups, [tuple((entry.group, entry.weight)
                                                               for entry in vertex.groups)
                                                              for vertex in obj.data.vertices])).encode()).hexdigest())
            keys = obj.data.shape_keys
            row['keys'] = {} if keys is None else {
                key.name: {'coordinates': float_hash(key.data), 'value': key.value,
                           'mute': bool(key.mute), 'relative': key.relative_key.name,
                           'mask': key.vertex_group} for key in keys.key_blocks}
        result[obj.name] = row
    serialized = json.dumps(result, sort_keys=True, allow_nan=False).encode('utf-8')
    return hashlib.sha256(serialized).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blend', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True, help='Frozen character_designer package directory')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rig', default='CoshaRig')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not bpy.app.background:
        raise RuntimeError('Capture requires isolated background Blender.')
    if args.output.exists():
        raise ValueError('Preserve existing evidence; choose a new output directory.')
    args.output.mkdir(parents=True)
    source_sha = sha(args.blend)
    report = {'passed': False, 'input_blend': str(args.blend), 'input_sha256': source_sha,
              'runtime': str(args.runtime), 'Blender_version': bpy.app.version_string,
              'saved_input_blend': False, 'worker_started': False, 'Unity_started': False}
    try:
        expected = json.loads(args.manifest.read_text(encoding='utf-8'))['files']
        for relative, expected_sha in expected.items():
            if sha(args.runtime / relative) != expected_sha:
                raise ValueError('Frozen runtime SHA mismatch: ' + relative)
        if 'character_designer' in sys.modules:
            raise ValueError('Use factory startup without a preloaded Character Designer.')
        sys.path.insert(0, str(args.runtime.parent))
        import character_designer
        if Path(character_designer.__file__).resolve() != (args.runtime / '__init__.py').resolve():
            raise ValueError('The imported runtime is not the requested frozen package.')
        character_designer.register()
        from character_designer import forearm_twist, hair_wiggle_adapter, unity_export, unity_forearm
        from character_designer import unity_export_worker
        # Keep background handlers from rewriting correction buffers while reading.
        forearm_twist._BUSY = True
        bpy.ops.wm.open_mainfile(filepath=str(args.blend), load_ui=False, use_scripts=False)
        forearm_twist._BUSY = True
        if bpy.context.mode not in {'OBJECT', 'POSE'}:
            raise ValueError('Official Export refuses this saved Edit Mode state.')
        rig = bpy.data.objects.get(args.rig)
        if rig is None or rig.type != 'ARMATURE' or rig.name not in bpy.context.scene.objects:
            raise ValueError('The explicitly requested Main Rig is missing from this scene.')
        if hair_wiggle_adapter.status(bpy.context)['active']:
            raise ValueError('The backup contains active Hair preview; capture the author state first.')
        config = rig.character_designer_unity_export
        collected = unity_export.collect_character(bpy.context, rig, config)
        objects = collected['objects']
        before = protected_fingerprint(objects)
        report['source_rest'] = {
            obj.name: {'object_world': [list(part) for part in obj.matrix_world],
                       'bones': {bone.name: {'matrix': [list(part) for part in bone.matrix_local],
                                             'head': list(bone.head_local), 'tail': list(bone.tail_local),
                                             'parent': bone.parent.name if bone.parent else None,
                                             'use_deform': bool(bone.use_deform)}
                                 for bone in obj.data.bones}}
            for obj in objects if obj.type == 'ARMATURE'}
        directory, filename = unity_export._target(config, rig)
        asset_id = config.asset_id or uuid.uuid4().hex
        prior = unity_export._previous(directory, filename, asset_id)
        hair_motion = unity_export._capture_hair_motion(objects)
        owned_keys = unity_export._owned_keys(objects)
        forearm = {obj.name: unity_forearm.capture(obj) for obj in objects
                   if obj.type == 'MESH' and obj.name in owned_keys}
        report['unregistered_prefixed_keys'] = []
        report['shape_inputs'] = {}
        for obj in objects:
            if obj.type != 'MESH':
                continue
            managed = set(owned_keys.get(obj.name, ()))
            keys = obj.data.shape_keys
            if keys is not None:
                for key in keys.key_blocks:
                    if key.name.startswith(forearm_twist.KEY_PREFIX) and key.name not in managed:
                        report['unregistered_prefixed_keys'].append({
                            'object': obj.name, 'key': key.name, 'value': key.value, 'mute': bool(key.mute),
                            'treated_as_artist_shape_by_official_export': True})
            basis, artists = unity_export_worker._shape_inputs(obj, list(managed))
            report['shape_inputs'][obj.name] = {
                'basis_sha256': hashlib.sha256(basis.tobytes()).hexdigest(),
                'artists': [{'name': item['name'], 'value': item['value'],
                             'coordinates_sha256': hashlib.sha256(item['coordinates'].tobytes()).hexdigest()}
                            for item in artists]}
        specification = {
            'objects': [obj.name for obj in objects], 'rig': rig.name,
            'rigs': [obj.name for obj in objects if obj.type == 'ARMATURE'],
            'filename': filename, 'stage': str(args.output / 'out'), 'asset_id': asset_id,
            'unit_scale': bpy.context.scene.unit_settings.scale_length,
            'owned_keys': owned_keys, 'warnings': collected['warnings'],
            'forearm': forearm, 'hair_motion': hair_motion,
            'had_forearm': bool(prior and prior.get('forearm_correction')),
            'simple_materials': sorted({entry.material.name for entry in config.simple_materials
                                       if entry.material is not None and any(
                                           slot.material == entry.material for obj in objects if obj.type == 'MESH'
                                           for slot in obj.material_slots)}),
            'image_buffers': unity_export._image_buffers(objects, args.output),
        }
        snapshot = args.output / 'character.blend'
        bpy.data.libraries.write(str(snapshot), set(objects), path_remap='ABSOLUTE',
                                 fake_user=False, compress=True)
        job_path = args.output / 'job.json'
        job_path.write_text(json.dumps(specification, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        after = protected_fingerprint(objects)
        report.update(objects=specification['objects'], owned_keys=owned_keys,
                      forearm_meshes=list(forearm), warnings=collected['warnings'],
                      armature_mirror_x={obj.name: bool(obj.data.use_mirror_x)
                                        for obj in objects if obj.type == 'ARMATURE'},
                      original_export_directory=str(directory), original_export_filename=filename,
                      snapshot=str(snapshot), snapshot_sha256=sha(snapshot),
                      job=str(job_path), job_sha256=sha(job_path),
                      protected_before=before, protected_after=after,
                      captured_data_unchanged=before == after, passed=before == after)
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        report['source_file_unchanged'] = sha(args.blend) == source_sha
        report['passed'] = report['passed'] and report['source_file_unchanged']
        report_path = args.output / 'capture_report.json'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        print('EXPORT_JOB_CAPTURE_REPORT', str(report_path), report['passed'], flush=True)
    if not report['passed']:
        raise AssertionError('Official input capture failed or changed protected data; inspect its report.')


if __name__ == '__main__':
    main()
