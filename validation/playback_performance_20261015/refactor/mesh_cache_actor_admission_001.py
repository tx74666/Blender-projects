"""One saved-frame PC2 admission on fixed input and an owned Stage06 Scene copy.

Diagnostic only: original base/raw source protection plus initial/final complete
mesh/Shape Key/rig output; registered RNA/foreign payload coverage is unclaimed.
No artifact, adoption, shader appearance, clip-wide staticness or FPS proof.
"""
import argparse
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
BASE = HERE/'native_validation_support.py'
FACTORY = HERE/'mesh_cache_pc2_factory_001.py'
for path, expected in ((BASE, '3994f58288244684679ffd48d0837ac88bcfd9768f0a3a12c3e1d7d5b6265c0a'),
                       (FACTORY, '71ad83108122388a536a44a36007840068ba15fcb03aaaecafe148ca12e39440')):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Protected small helper changed: '+path.name)
import native_validation_support as witness
from mesh_cache_pc2_factory_001 import HEADER, bulk, inspect_pc2, vector_diff


def require(value, message):
    if not value:
        raise RuntimeError(message)


def select_scene(bpy, scene):
    require(bpy.context.window is not None, 'Background window context is required')
    bpy.context.window.scene = scene


def vectors(obj, graph):
    mesh = obj.evaluated_get(graph).data
    return {'vertex_coordinates': bulk(mesh.vertices, 'co'), 'vertex_normals': bulk(mesh.vertices, 'normal'),
            'polygon_normals': bulk(mesh.polygons, 'normal'), 'corner_normals': bulk(mesh.corner_normals, 'vector')}


def shader_usage(materials):
    result, visited = [], set()
    def walk(material, tree):
        if tree is None or int(tree.as_pointer()) in visited:
            return
        visited.add(int(tree.as_pointer()))
        for node in tree.nodes:
            if node.bl_idname == 'ShaderNodeTexCoord':
                result.append({'material': material.name_full, 'tree': tree.name_full, 'node': node.name,
                    'linked_coordinates': [socket.name for socket in node.outputs if socket.is_linked]})
            if node.bl_idname == 'ShaderNodeGroup':
                walk(material, node.node_tree)
    for material in materials:
        walk(material, material.node_tree)
    return result


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath,
            'A new private factory-startup background worker is required')
    require(any(v in ('-t', '--threads') and native[i+1] == '1' for i, v in enumerate(native[:-1])), '-t 1 required')
    require(bpy.app.version[:2] == (5, 2), 'This admission targets Blender 5.2')
    source_file, artist_file = Path(args.input).resolve(), Path(args.artist).resolve()
    require(source_file != artist_file and not os.path.samefile(source_file, artist_file), 'Never open artist')
    input_pin, artist_pin = witness.pin(source_file), witness.pin(artist_file)
    require(input_pin['sha256'] == '40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721'
            and input_pin['bytes'] == 34691613, 'Use the fixed 40644 saved input')
    manifest_path = Path(args.source_manifest).resolve()
    require(witness.pin(manifest_path)['sha256'] == '5c7965ef74e99ed8036bc57ad639cb4db37e6501bb580483a676d4b2fd6cc3c0',
            'Use the reviewed Stage06 source manifest')
    package = Path(args.addons).resolve()/'character_designer'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    source_seal = witness.verify_package_manifest(package, manifest)
    directory = Path(args.cache_dir).resolve()
    require(directory.parent == HERE and not directory.exists(), 'Name a new direct child cache directory')
    directory.mkdir()
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module('character_designer')
    runtime = importlib.import_module('character_designer.forearm_twist')
    scene_module = importlib.import_module('character_designer.forearm_twist_playback_scene')
    require(Path(addon.__file__).resolve().parent == package, 'Imported another addon package')
    handlers_before = witness.handler_snapshot()
    session, source_scene, protected_output, protected_props = None, None, None, None
    registered, private_ids, errors = False, set(), []
    report.update(input_before=input_pin, artist_before=artist_pin, source_manifest=witness.pin(manifest_path),
        scripts={p.name: witness.pin(p) for p in (Path(__file__), BASE, FACTORY)}, sources=source_seal,
        geometry_oracle=witness.pin(witness.ORACLE_PATH), blender=bpy.app.version_string,
        version=list(addon.bl_info['version']), meshes=[], cache_files=[])
    try:
        addon.register()
        registered = True
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(source_file)), 'Fixed input open failed')
        require(Path(bpy.data.filepath).resolve() == source_file, 'Opened another file')
        source_scene = bpy.context.scene
        frame, subframe = source_scene.frame_current, float(source_scene.frame_subframe)
        require(1 <= frame <= 30 and subframe == 0., 'Saved frame must be an integer in 1-30')
        report['saved_frame'] = frame
        source_pairs = [(obj.name, obj) for obj in source_scene.objects]
        meshes = [obj for obj in source_scene.objects if obj.type == 'MESH']
        require(meshes and any(runtime.RECORD_KEY in obj for obj in meshes), 'Expected complete calibrated actor')
        with runtime.defer_runtime(bpy.context, flush_on_exit=False):
            bpy.context.view_layer.update()
            for obj in meshes:
                if runtime.RECORD_KEY in obj:
                    runtime._calculate_object(obj, bpy.context.evaluated_depsgraph_get())
            bpy.context.view_layer.update()
            require(not runtime._ERRORS, 'Source authoring runtime has errors')
            graph = bpy.context.evaluated_depsgraph_get()
            protected_output = witness.frame_witness(source_scene, source_pairs, runtime, {})
            protected_props = witness.source_property_witness(source_scene)
            golden = {obj.name: witness.geometry_witness(obj, {}) for obj in meshes}
            golden_vectors = {obj.name: vectors(obj, graph) for obj in meshes}
            report['source_geometry_scope'] = {name: item['scope'] for name, item in golden.items()}
            materials = {mat for obj in meshes for mat in obj.data.materials if mat is not None}
            materials.update(slot.material for obj in meshes for slot in obj.material_slots if slot.material is not None)
            report['explicit_texture_coordinates'] = shader_usage(materials)
            before_ids = witness.native_id_pointers()
            try:
                session = scene_module.build_isolated_scene(source_scene)
            finally:
                private_ids = witness.native_id_pointers() - before_ids
            require(session.source_scene is source_scene and session.scene is not source_scene
                    and set(session.object_map) == set(source_scene.objects), 'Full Scene copy admission failed')
            reverse = {int(target.as_pointer()): source for source, target in session.id_map.items()}
            select_scene(bpy, source_scene)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            for index, source in enumerate(meshes):
                target = session.object_map[source]
                require(target is not source and target.data is not source.data, 'Mesh source/copy not independent')
                evaluated = source.evaluated_get(graph)
                before_meshes = {int(item.as_pointer()) for item in bpy.data.meshes}
                mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=graph)
                require(int(mesh.as_pointer()) not in before_meshes and mesh.library is None,
                        'Final Mesh primitive did not return a new owned local ID')
                session.created.append(('meshes', int(mesh.as_pointer()), mesh.session_uid))
                private_ids.add(int(mesh.as_pointer()))
                require(mesh.shape_keys is None and len(mesh.vertices) > 0, 'Expected a nonempty final Mesh without Shape Keys')
                for slot, material in enumerate(tuple(mesh.materials)):
                    if material is None:
                        continue
                    material = getattr(material, 'original', material)
                    require(material in session.id_map, 'Final evaluated material lacks an owned copy')
                    mesh.materials[slot] = session.id_map[material]
                target.data = mesh
                target.modifiers.clear()
                if runtime.RECORD_KEY in target:
                    del target[runtime.RECORD_KEY]
                require(len(target.vertex_groups) == len(source.vertex_groups), 'Final mesh group mapping changed')
                points = golden_vectors[source.name]['vertex_coordinates']
                path = directory/('mesh_'+str(index).zfill(3)+'.pc2')
                raw = HEADER.pack(b'POINTCACHE2\0', 1, len(mesh.vertices), 0., 1., 1) + points
                inspect_pc2(raw)
                with path.open('xb') as stream:
                    stream.write(raw)
                report['cache_files'].append({'source': source.name, **witness.pin(path)})
                modifier = target.modifiers.new('Cached Playback', 'MESH_CACHE')
                modifier.filepath, modifier.cache_format, modifier.deform_mode = str(path), 'PC2', 'OVERWRITE'
                modifier.factor, modifier.vertex_group, modifier.interpolation = 1., '', 'NONE'
                modifier.play_mode, modifier.time_mode = 'SCENE', 'FRAME'
                modifier.frame_start, modifier.frame_scale = float(frame), 1.
                modifier.forward_axis, modifier.up_axis, modifier.flip_axis = 'POS_Y', 'POS_Z', (False, False, False)
            select_scene(bpy, session.scene)
            session.scene.frame_set(frame)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            require(not any(obj.type == 'MESH' and runtime.RECORD_KEY in obj for obj in session.scene.objects),
                    'A candidate mesh remains enrolled in the authoring solver')
            for source in meshes:
                target = session.object_map[source]
                current = witness.geometry_witness(target, reverse)
                changed = sorted(key for key in set(golden[source.name]['components']) | set(current['components'])
                    if golden[source.name]['components'].get(key) != current['components'].get(key))
                actual = vectors(target, graph)
                report['meshes'].append({'source': source.name, 'exact': not changed, 'changed_components': changed,
                    'source_sha256': golden[source.name]['sha256'], 'cache_sha256': current['sha256'],
                    'vector_metrics': {field: vector_diff(golden_vectors[source.name][field], actual[field]) for field in actual}})
            select_scene(bpy, source_scene)
            bpy.context.view_layer.update()
            output_after = witness.frame_witness(source_scene, source_pairs, runtime, {})
            props_after = witness.source_property_witness(source_scene)
            report['source_after_playback'] = {'output': witness.compare_witness(protected_output, output_after),
                'base_raw_properties_exact': protected_props == props_after}
            report['all_mesh_geometry_exact'] = all(row['exact'] for row in report['meshes'])
            require(report['source_after_playback']['output']['exact'] and protected_props == props_after,
                    'Candidate playback changed source output or base/raw source properties')
            require(report['all_mesh_geometry_exact'], 'Saved-frame final Mesh/PC2 exact admission failed')
    finally:
        if source_scene is not None:
            with runtime.defer_runtime(bpy.context, flush_on_exit=False):
                select_scene(bpy, source_scene)
                if session is not None:
                    try:
                        session.close()
                    except BaseException:
                        errors.append(traceback.format_exc())
                if protected_output is not None:
                    try:
                        bpy.context.view_layer.update()
                        report['source_after_cleanup'] = {
                            'output': witness.compare_witness(protected_output, witness.frame_witness(source_scene, source_pairs, runtime, {})),
                            'base_raw_properties_exact': protected_props == witness.source_property_witness(source_scene)}
                    except BaseException:
                        errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        report['cleanup'] = {'errors': errors, 'owned_ids_removed': not bool(private_ids & witness.native_id_pointers()),
            'handlers_restored_exact': handlers_before == witness.handler_snapshot(),
            'input_disk_unchanged': input_pin == witness.pin(source_file),
            'artist_disk_unchanged': artist_pin == witness.pin(artist_file),
            'source_package_unchanged': source_seal == witness.verify_package_manifest(package, manifest),
            'scripts_unchanged': all(pin == witness.pin(pin['path']) for pin in report['scripts'].values()),
            'cache_files_unchanged': all(pin['sha256'] == witness.pin(pin['path'])['sha256'] for pin in report['cache_files'])}
        require(not errors and all(value for key, value in report['cleanup'].items() if key != 'errors'),
                'Admission cleanup/disk/source protection failed')
        require(report.get('source_after_cleanup', {}).get('output', {}).get('exact') is True
                and report['source_after_cleanup']['base_raw_properties_exact'], 'Source final output/raw properties changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'artist', 'addons', 'source-manifest', 'cache-dir', 'report'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.pc2-fixed-actor-saved-frame-admission/1', 'completed': False, 'diagnostic_only': True,
        'pid': os.getpid(), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'no_artifact_save': True, 'no_adoption_or_deploy': True, 'gui_fps_verified': False,
        'limits': ['One saved integer frame only; no complete clip/static-attribute/FPS proof.',
                   'Old base/raw source property and full initial/final geometry/ShapeKey/rig coverage only; registered RNA/foreign payload proof pending bulk witness.',
                   'Original copied object parents/constraints/actions/transforms remain; only final mesh data/modifiers/keys/Forearm enrollment replaced.',
                   'Full evaluated mesh oracle includes all normals/attributes; shader appearance/Generated/Reflection/implicit coordinates remain unproven.',
                   'Owned PC2 caches and report only; artist/input blend disks are never written.']}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
