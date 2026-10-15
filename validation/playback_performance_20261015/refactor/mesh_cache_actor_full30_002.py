"""Diagnostic whole-actor PC2 clip, using the sealed saved-frame admission helpers.

Root alone launches this fresh background worker. No blend save, artifact, GUI,
adoption or threshold relaxation. Source arrays live for one mesh/frame only;
the report keeps exact per-frame oracle hashes. Source texspace getters are not
read. The optional V8 scope requires a real passed native factory receipt.
"""
from array import array
import argparse
import datetime
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ADMISSION = HERE/'mesh_cache_actor_admission_001.py'
if hashlib.sha256(ADMISSION.read_bytes()).hexdigest() != '2322463cb2e98a37d854ad199ffed1fc14b6fd68844d3af7a77769ca7f13e02b':
    raise RuntimeError('Sealed saved-frame admission changed')
import mesh_cache_actor_admission_001 as admission
from mesh_cache_pc2_factory_001 import HEADER, bulk

require = admission.require
base = admission.witness
FRAMES = tuple(range(1, 31))
DYNAMIC_OUTPUTS = frozenset(('vertex_coordinates', 'vertex_normals', 'polygon_normals',
                             'corner_normals', 'object_matrix_world'))
V8_PINS = {
    'native_validation_support_v8.py': 'dce66a2b5739d7c54e359e7c1d542004ecedf350682dccb2537e0adabe3dcaf6',
    'native_source_reference_witness_v8.py': '5a6a12a723c3c4ce4198cc04a4d641d0a95ff4bc092b1cc2ac36c122b6d3bcf5',
    'native_keyframe_bulk_factory_008.py': '986b1ad696222cf4fb7d1ff1381dcc149691f56af543a786a68c8d706a69a606',
}


def static_components(components):
    """Normals are checked per frame; stored custom_normal remains protected."""
    return {key: value for key, value in components.items()
            if key not in DYNAMIC_OUTPUTS
            and not (key.startswith('attribute:') and key.split(':', 2)[2] == 'position')}


def changed_components(left, right):
    return sorted(key for key in set(left) | set(right)
                  if key not in left or key not in right or left[key] != right[key])


def check_points(raw, vertices):
    require(len(raw) == vertices*12 and vertices > 0, 'PC2 per-frame vertex domain changed')
    values = array('f')
    values.frombytes(raw)
    require(sys.byteorder == 'little' and all(math.isfinite(value) for value in values),
            'PC2 requires finite little-endian float32 positions')


def inspect_stream(path, vertices, samples=30):
    """Never read/unpack the whole clip; positions were checked while writing."""
    path = Path(path)
    with path.open('rb') as stream:
        raw = stream.read(HEADER.size)
        require(len(raw) == HEADER.size, 'PC2 header missing')
        require(HEADER.unpack(raw) == (b'POINTCACHE2\0', 1, vertices, 0., 1., samples),
                'PC2 stream header differs')
    require(path.stat().st_size == HEADER.size + vertices*samples*12, 'PC2 stream length differs')
    return base.pin(path)


def replay_visits():
    jump = tuple(FRAMES[index] for index in ((index*7) % 30 for index in range(30)))
    return [('forward', FRAMES), ('reverse', tuple(reversed(FRAMES))),
            ('jump', jump), ('loop', FRAMES+FRAMES)]


def choose_witness(args, report):
    if args.witness == 'base-diagnostic':
        require(args.v8_factory_report is None and args.v8_factory_sha256 is None,
                'V8 receipt does not apply to explicit base-diagnostic scope')
        report['source_property_scope'] = 'Original base/raw only; registered RNA and foreign payload unclaimed.'
        return base, {}
    require(args.v8_factory_report and args.v8_factory_sha256, 'V8 requires a passed native factory path and SHA')
    for name, expected in V8_PINS.items():
        require(base.pin(HERE/name)['sha256'] == expected, 'V8 source pin differs: '+name)
    witness = importlib.import_module('native_validation_support_v8')
    require(Path(witness.__file__).resolve() == HERE/'native_validation_support_v8.py', 'Wrong V8 module')
    receipt_pin = base.pin(args.v8_factory_report)
    require(receipt_pin['sha256'] == args.v8_factory_sha256, 'V8 factory receipt SHA differs')
    receipt = json.loads(Path(args.v8_factory_report).read_text(encoding='utf-8-sig'))
    require(receipt.get('schema') == 'x.native-keyframe-bulk-factory/1' and receipt.get('completed') is True
            and 'error' not in receipt and str(receipt.get('blender', '')).startswith('5.2'),
            'V8 factory receipt is not an actual successful 5.2 factory result')
    flags = ('bulk_read_did_not_write_old_point_state', 'all15_field_coverage_exact', 'reader_dispatch_bulk',
             'all_fixture_ids_removed', 'handlers_unchanged', 'artist_disk_unchanged', 'stage_unchanged',
             'witness_sources_unchanged', 'scripts_unchanged')
    for key, count in (('field_checks', 15), ('enum_api_checks', 5), ('mutation_traps', 5)):
        values = receipt.get(key)
        require(isinstance(values, dict) and len(values) == count and all(value is True for value in values.values()),
                'V8 factory field/enum/mutation gates failed: '+key)
    old_states = receipt.get('old_point_state_sha256_before_after')
    require(isinstance(old_states, list) and len(old_states) == 2 and old_states[0] == old_states[1]
            and isinstance(old_states[0], str) and len(old_states[0]) == 64,
            'V8 factory old point state changed')
    require(not receipt.get('cleanup_errors') and all(receipt.get(key) is True for key in flags), 'V8 factory gates failed')
    deps = witness.witness_dependency_pins()
    require(receipt.get('witness_sources') == deps, 'V8 factory used another witness payload')
    require(all(item == base.pin(item['path']) for item in receipt.get('scripts', {}).values()),
            'A V8 factory source dependency changed')
    require(receipt.get('scripts', {}).get('native_keyframe_bulk_factory_008.py', {}).get('sha256')
            == V8_PINS['native_keyframe_bulk_factory_008.py'], 'V8 receipt used another factory script')
    report.update(v8_factory_receipt=receipt_pin, v8_factory_sources=receipt['scripts'], source_witness_dependencies=deps,
        source_property_scope='V8 exact declared stored/raw/registered fields and foreign Object/data/Key/Action payload; see witness limits. Unset/computed getters and other ID content unclaimed.')
    return witness, deps


def shader_diagnostics(materials, meshes):
    """Conservative potential consumers, not a render reachability proof."""
    records, seen = [], set()
    def walk(material, tree):
        if tree is None or int(tree.as_pointer()) in seen:
            return
        seen.add(int(tree.as_pointer()))
        for node in tree.nodes:
            kind = node.bl_idname
            row = {'material': material.name_full, 'tree': tree.name_full, 'node': node.name, 'type': kind}
            vector = node.inputs.get('Vector')
            if kind.startswith('ShaderNodeTex') and kind not in ('ShaderNodeTexCoord', 'ShaderNodeTexImage', 'ShaderNodeTexEnvironment') and vector is not None and not vector.is_linked:
                records.append({**row, 'potential_implicit_generated': True, 'unconnected_input': vector.name})
            if kind == 'ShaderNodeAttribute':
                records.append({**row, 'attribute_name': node.attribute_name, 'attribute_type': node.attribute_type})
            if kind in ('ShaderNodeObjectInfo', 'ShaderNodeParticleInfo'):
                records.append({**row, 'linked_outputs': [socket.name for socket in node.outputs if socket.is_linked]})
            if kind == 'ShaderNodeTexCoord':
                records.append({**row, 'object': base.logical_id(node.object, {}),
                                'from_instancer': bool(node.from_instancer)})
            if kind == 'ShaderNodeGroup':
                walk(material, node.node_tree)
    for material in materials:
        walk(material, material.node_tree)
    return {'explicit_texture_coordinates': admission.shader_usage(materials), 'potential_consumers': records,
        'instances': [{'object': obj.name, 'instance_type': obj.instance_type,
                       'particle_system_count': len(obj.particle_systems)} for obj in meshes],
        'limits': 'Conservative node inventory only; implicit/group/muted/render paths, ObjectInfo.Random, particles/instancing, Generated/ORCO, texspace and visual appearance are not proven. No Source texspace getters are read.'}


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath,
            'Fresh private factory-startup background worker required')
    require(any(value in ('-t', '--threads') and native[index+1] == '1'
                for index, value in enumerate(native[:-1])), 'Native -t 1 required')
    require(bpy.app.version[:2] == (5, 2), 'Blender 5.2 required')
    witness, witness_deps = choose_witness(args, report)
    source_file, artist_file = Path(args.input).resolve(), Path(args.artist).resolve()
    require(source_file != artist_file and not os.path.samefile(source_file, artist_file), 'Never open artist')
    input_pin, artist_pin = base.pin(source_file), base.pin(artist_file)
    require(input_pin['sha256'] == '40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721'
            and input_pin['bytes'] == 34691613, 'Use fixed 40644 input')
    manifest_path = Path(args.source_manifest).resolve()
    manifest_pin = base.pin(manifest_path)
    require(manifest_pin['sha256'] == '5c7965ef74e99ed8036bc57ad639cb4db37e6501bb580483a676d4b2fd6cc3c0', 'Reviewed Stage06 required')
    package = Path(args.addons).resolve()/'character_designer'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    source_seal = base.verify_package_manifest(package, manifest)
    directory = Path(args.cache_dir).resolve()
    require(directory.parent == HERE and not directory.exists(), 'New direct-child cache directory required')
    directory.mkdir()
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module('character_designer')
    runtime = importlib.import_module('character_designer.forearm_twist')
    scene_module = importlib.import_module('character_designer.forearm_twist_playback_scene')
    require(Path(addon.__file__).resolve().parent == package, 'Another addon package imported')
    handlers_before = base.handler_snapshot()
    session = source_scene = protected_output = protected_props = None
    registered, needs_restore, private_ids, errors, streams = False, False, set(), [], {}
    scripts = {path.name: base.pin(path) for path in (Path(__file__), ADMISSION, admission.BASE, admission.FACTORY)}
    report.update(input_before=input_pin, artist_before=artist_pin, source_manifest=manifest_pin, scripts=scripts,
        source_package=source_seal, geometry_oracle=base.pin(base.ORACLE_PATH), blender=bpy.app.version_string,
        version=list(addon.bl_info['version']), witness_mode=args.witness, golden=[], static_deltas=[],
        replay=[], cache_files=[], timing={'measured': False})

    def update_source(frame):
        admission.select_scene(bpy, source_scene)
        source_scene.frame_set(frame, subframe=0.)
        bpy.context.view_layer.update()
        for obj in meshes:
            if runtime.RECORD_KEY in obj:
                runtime._calculate_object(obj, bpy.context.evaluated_depsgraph_get())
        bpy.context.view_layer.update()
        require(not runtime._ERRORS, 'Source authoring runtime has errors')

    def protect_source(label, restore=False):
        nonlocal needs_restore
        if restore:
            update_source(saved_frame)
            needs_restore = False
        else:
            admission.select_scene(bpy, source_scene)
            bpy.context.view_layer.update()
        output = base.frame_witness(source_scene, source_pairs, runtime, {})
        observed = witness.source_property_witness(source_scene)
        row = {'output': base.compare_witness(protected_output, output),
               'source_properties_exact': protected_props == observed,
               'changed_property_components': changed_components(protected_props['components'], observed['components'])}
        report[label] = row
        require(row['output']['exact'] and row['source_properties_exact'], 'Source protection failed: '+label)

    try:
        addon.register()
        registered = True
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(source_file)), 'Fixed input open failed')
        require(Path(bpy.data.filepath).resolve() == source_file, 'Another file opened')
        source_scene = bpy.context.scene
        saved_frame = source_scene.frame_current
        require(saved_frame in FRAMES and float(source_scene.frame_subframe) == 0., 'Integer saved frame 1-30 required')
        source_pairs = [(obj.name, obj) for obj in source_scene.objects]
        meshes = sorted((obj for obj in source_scene.objects if obj.type == 'MESH'), key=lambda obj: obj.name)
        require(meshes and any(runtime.RECORD_KEY in obj for obj in meshes), 'Complete calibrated actor required')
        report['saved_frame'] = saved_frame
        with runtime.defer_runtime(bpy.context, flush_on_exit=False):
            update_source(saved_frame)
            protected_output = base.frame_witness(source_scene, source_pairs, runtime, {})
            protected_props = witness.source_property_witness(source_scene)
            report['source_property_witness_scope'] = protected_props.get('registered_source_and_external_objects', {}).get('scope')
            materials = {slot.material for obj in meshes for slot in obj.material_slots if slot.material is not None}
            materials.update(mat for obj in meshes for mat in obj.data.materials if mat is not None)
            report['shader_diagnostics'] = shader_diagnostics(materials, meshes)
            vertex_counts, static_first, golden = {}, {}, {}
            graph = bpy.context.evaluated_depsgraph_get()
            for index, obj in enumerate(meshes):
                count = len(obj.evaluated_get(graph).data.vertices)
                require(count > 0, 'Empty Mesh unsupported: '+obj.name)
                vertex_counts[obj.name] = count
                path = directory/('mesh_'+str(index).zfill(3)+'.pc2')
                stream = path.open('xb')
                streams[obj.name] = (stream, path)
                stream.write(HEADER.pack(b'POINTCACHE2\0', 1, count, 0., 1., 30))
            needs_restore = True
            for frame in FRAMES:
                started = time.perf_counter()
                update_source(frame)
                elapsed = (time.perf_counter()-started)*1000.
                graph = bpy.context.evaluated_depsgraph_get()
                rows = {}
                for obj in meshes:
                    row = base.geometry_witness(obj, {})
                    static = static_components(row['components'])
                    if obj.name in static_first:
                        changed = changed_components(static_first[obj.name], static)
                        if changed:
                            report['static_deltas'].append({'frame': frame, 'mesh': obj.name, 'changed_components': changed})
                    else:
                        static_first[obj.name] = static
                    points = bulk(obj.evaluated_get(graph).data.vertices, 'co')
                    check_points(points, vertex_counts[obj.name])
                    require(hashlib.sha256(points).hexdigest() == row['components']['vertex_coordinates'], 'Position witness/write mismatch')
                    streams[obj.name][0].write(points)
                    rows[obj.name] = row
                    del points
                golden[frame] = rows
                report['golden'].append({'frame': frame, 'authoring_update_ms': elapsed, 'meshes': rows})
            for stream, path in streams.values():
                stream.close()
            report['cache_files'] = [{'source': name, **inspect_stream(path, vertex_counts[name])}
                                     for name, (stream, path) in streams.items()]
            protect_source('source_after_golden', restore=True)
            report['clip_static_exact'] = not report['static_deltas']
            require(report['clip_static_exact'], 'PC2 cannot preserve varying static topology/attributes/weights/materials')
            before_ids = base.native_id_pointers()
            try:
                session = scene_module.build_isolated_scene(source_scene)
            finally:
                private_ids = base.native_id_pointers() - before_ids
            require(session.source_scene is source_scene and session.scene is not source_scene
                    and set(session.object_map) == set(source_scene.objects), 'Full Scene copy admission failed')
            reverse = {int(target.as_pointer()): source for source, target in session.id_map.items()}
            # Native graph structure changed. Never reuse the earlier depsgraph handle.
            admission.select_scene(bpy, source_scene)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            for source in meshes:
                target = session.object_map[source]
                require(target is not source and target.data is not source.data, 'Source/copy not independent')
                before_meshes = {int(item.as_pointer()) for item in bpy.data.meshes}
                mesh = bpy.data.meshes.new_from_object(source.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
                require(int(mesh.as_pointer()) not in before_meshes and mesh.library is None, 'Final mesh is not a new owned local ID')
                session.created.append(('meshes', int(mesh.as_pointer()), mesh.session_uid))
                private_ids.add(int(mesh.as_pointer()))
                require(mesh.shape_keys is None and len(mesh.vertices) == vertex_counts[source.name], 'Final mesh domain/Shape Keys differ')
                for index, material in enumerate(tuple(mesh.materials)):
                    if material is not None:
                        material = getattr(material, 'original', material)
                        require(material in session.id_map, 'Final evaluated material lacks owned clone')
                        mesh.materials[index] = session.id_map[material]
                target.data = mesh
                target.modifiers.clear()
                if runtime.RECORD_KEY in target:
                    del target[runtime.RECORD_KEY]
                require(len(target.vertex_groups) == len(source.vertex_groups), 'Final group mapping changed')
                modifier = target.modifiers.new('Cached Playback', 'MESH_CACHE')
                modifier.filepath, modifier.cache_format, modifier.deform_mode = str(streams[source.name][1]), 'PC2', 'OVERWRITE'
                modifier.factor, modifier.vertex_group, modifier.interpolation = 1., '', 'NONE'
                modifier.play_mode, modifier.time_mode, modifier.frame_start, modifier.frame_scale = 'SCENE', 'FRAME', 1., 1.
                modifier.forward_axis, modifier.up_axis, modifier.flip_axis = 'POS_Y', 'POS_Z', (False, False, False)
            require(not any(obj.type == 'MESH' and runtime.RECORD_KEY in obj for obj in session.scene.objects),
                    'Candidate mesh remains enrolled in authoring solver')
            admission.select_scene(bpy, session.scene)
            all_exact = True
            for block, visits in replay_visits():
                for frame in visits:
                    session.scene.frame_set(frame, subframe=0.)
                    bpy.context.view_layer.update()
                    rows = []
                    for source in meshes:
                        actual = base.geometry_witness(session.object_map[source], reverse)
                        expected = golden[frame][source.name]
                        changed = changed_components(expected['components'], actual['components'])
                        rows.append({'mesh': source.name, 'exact': not changed, 'changed_components': changed,
                                     'source_sha256': expected['sha256'], 'cache_sha256': actual['sha256']})
                        all_exact = all_exact and not changed
                    report['replay'].append({'block': block, 'frame': frame, 'meshes': rows})
            report['all_replay_geometry_exact'] = bool(all_exact)
            protect_source('source_after_candidate')
            require(all_exact, 'Full30 PC2 geometry/world/normal replay differs')
            # Small native pipeline measurement only, after all exact gates. No hash,
            # corrective solver, mesh export or timing-dependent acceptance here.
            admission.select_scene(bpy, session.scene)
            for frame in (30, 1):
                session.scene.frame_set(frame, subframe=0.)
                bpy.context.view_layer.update()
            measurements = []
            for frame in (6, 12, 18, 24, 30, 1, 6, 12, 18, 24, 30, 1):
                started = time.perf_counter()
                session.scene.frame_set(frame, subframe=0.)
                bpy.context.view_layer.update()
                measurements.append({'frame': frame, 'milliseconds': (time.perf_counter()-started)*1000.})
            report['timing'] = {'measured': True, 'scope': 'Background frame_set+view_layer.update; no oracle/hash/solver/draw/GUI, not user playback FPS.',
                'samples': measurements, 'median_ms': statistics.median(row['milliseconds'] for row in measurements),
                'max_ms': max(row['milliseconds'] for row in measurements)}
            protect_source('source_after_timing')
    finally:
        for stream, path in streams.values():
            try:
                stream.close()
            except BaseException:
                errors.append(traceback.format_exc())
        if source_scene is not None:
            with runtime.defer_runtime(bpy.context, flush_on_exit=False):
                admission.select_scene(bpy, source_scene)
                if needs_restore:
                    try:
                        update_source(saved_frame)
                        needs_restore = False
                    except BaseException:
                        errors.append(traceback.format_exc())
                if session is not None:
                    try:
                        session.close()
                    except BaseException:
                        errors.append(traceback.format_exc())
                if protected_output is not None:
                    try:
                        protect_source('source_after_cleanup')
                    except BaseException:
                        errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        report['cleanup'] = {'errors': errors, 'owned_ids_removed': not bool(private_ids & base.native_id_pointers()),
            'handlers_restored_exact': handlers_before == base.handler_snapshot(),
            'input_disk_unchanged': input_pin == base.pin(source_file), 'artist_disk_unchanged': artist_pin == base.pin(artist_file),
            'source_manifest_unchanged': manifest_pin == base.pin(manifest_path),
            'source_package_unchanged': source_seal == base.verify_package_manifest(package, manifest),
            'scripts_unchanged': all(item == base.pin(item['path']) for item in scripts.values()),
            'cache_files_unchanged': all(item['sha256'] == base.pin(item['path'])['sha256'] for item in report['cache_files']),
            'source_witness_dependencies_unchanged': not witness_deps or witness_deps == witness.witness_dependency_pins(),
            'v8_factory_receipt_unchanged': 'v8_factory_receipt' not in report or report['v8_factory_receipt'] == base.pin(args.v8_factory_report),
            'v8_factory_sources_unchanged': all(item == base.pin(item['path']) for item in report.get('v8_factory_sources', {}).values())}
        require(not errors and all(value for key, value in report['cleanup'].items() if key != 'errors'), 'Full30 cleanup/protection failed')
        require(report.get('source_after_cleanup', {}).get('output', {}).get('exact') is True
                and report['source_after_cleanup']['source_properties_exact'], 'Final source output/properties differ')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'artist', 'addons', 'source-manifest', 'cache-dir', 'report'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--witness', choices=('base-diagnostic', 'v8'), required=True)
    parser.add_argument('--v8-factory-report')
    parser.add_argument('--v8-factory-sha256')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.pc2-fixed-actor-full30/1', 'completed': False, 'diagnostic_only': True,
        'pid': os.getpid(), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'no_artifact_save': True, 'no_adoption_or_deploy': True, 'gui_fps_verified': False,
        'limits': ['Integer frames 1-30 only; no subframe interpolation/motion blur proof.',
                   'All evaluated actor Mesh geometry/three normal domains/static data/world are compared at each visit; no shader visual proof.',
                   'Candidate retains cloned parents/constraints/Actions/control/material graph; final Mesh data and modifier stacks replace authoring geometry.',
                   'Static custom_normal/UV/weights/attributes must remain clip-constant; PC2 stores only float32 local coordinates.',
                   'No Source raw texspace getter, blend save, GUI, artifact, production integration or performance acceptance.']}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
