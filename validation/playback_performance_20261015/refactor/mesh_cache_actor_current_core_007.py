"""Current SaveCopy kernels extracted from sealed002/005; explicit policy only.

The extraction audit records every changed block. Solver/evaluation ordering,
PC2 static gate, complete mesh oracle,150 visits, cleanup and serialization/
publication order retain the original source. No global monkeypatch is used.
"""
from array import array
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
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import mesh_cache_actor_admission_001 as admission
import mesh_cache_actor_full30_002 as helper
from mesh_cache_actor_full30_002 import static_components,changed_components,check_points,inspect_stream,replay_visits,shader_diagnostics
from mesh_cache_pc2_factory_001 import HEADER,bulk
from mesh_cache_artifact_assembler_005 import dependency_closure,asset_paths,external_assets,publish

base,require=admission.witness,admission.require
ADMISSION=Path(admission.__file__)
FRAMES=tuple(range(1,31))

def run_clip(args, report, policy):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath,
            'Fresh private factory-startup background worker required')
    require(any(value in ('-t', '--threads') and native[index+1] == '1'
                for index, value in enumerate(native[:-1])), 'Native -t 1 required')
    require(bpy.app.version[:2] == (5, 2), 'Blender 5.2 required')
    witness, witness_deps = policy.choose_witness(args, report)
    source_file, artist_file = Path(args.input).resolve(), Path(args.artist).resolve()
    require(source_file != artist_file and not os.path.samefile(source_file, artist_file), 'Never open artist')
    input_pin, artist_pin = base.pin(source_file), base.pin(artist_file)
    require(input_pin == policy.snapshot_pin, 'Guarded current SaveCopy pin differs')
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
    scene_module = policy.scene_module(package, report)
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
        row['material_source_exact'] = policy.protect_source(source_scene)
        report[label] = row
        require(row['material_source_exact'], 'Current Source material/resource state changed: '+label)
        require(row['output']['exact'] and row['source_properties_exact'], 'Source protection failed: '+label)

    try:
        addon.register()
        registered = True
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(source_file)), 'Fixed input open failed')
        require(Path(bpy.data.filepath).resolve() == source_file, 'Another file opened')
        source_scene = policy.loaded_source(bpy)
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
            policy.begin_source(source_scene, report)
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
                report['golden'].append({'frame': frame, 'authoring_update_ms': elapsed, 'meshes': rows,
                                        'shader': policy.source_frame(source_scene, frame)})
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
            policy.bind_target(session, report)
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
                    policy.target_frame(session.scene, frame, reverse, report)
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
        policy.finalize_clip(report)


def assemble_clip(args, report, policy):
    contract = policy.contract
    # Receipt, source, cache and policy admission precedes input open or writes.
    passed, passed_pin = contract.load_full30(args.full30_report, args.full30_sha256)
    report['accepted_full30_report'] = passed_pin
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath
        and bpy.app.version[:2] == (5, 2), 'Fresh private factory-startup Blender5.2 background required')
    require(any(value in ('-t', '--threads') and native[index+1] == '1'
        for index, value in enumerate(native[:-1])), '-t 1 required')
    output, artist = Path(args.output).resolve(), Path(args.artist).resolve()
    source_file = Path(passed['input_before']['path']).resolve()
    require(output.suffix.lower() == '.blend' and output.parent.is_dir() and not output.exists()
        and output != source_file and output != artist, 'Unused new .blend output in existing directory required')
    require(artist.is_file() and source_file != artist and not os.path.samefile(source_file, artist), 'Never open artist')
    package = Path(passed['source_manifest']['path']).parent/'addons/character_designer'
    report.update(blender=bpy.app.version_string, input_before=base.pin(source_file), artist_before=base.pin(artist))
    require(report['input_before'] == passed['input_before'], 'Fixed input changed')
    dependencies = {}
    for group in ('scripts', 'adapter_sources', 'v8_factory_sources', 'source_witness_dependencies'):
        dependencies.update(passed[group])
    for name in (Path(__file__).name, 'mesh_cache_artifact_contract_005.py', 'native_artifact_action_witness_008.py'):
        dependencies[name] = base.pin(HERE/name)
    report['dependency_pins'] = dependencies
    require(dependencies['native_artifact_action_witness_008.py']['sha256'] == contract.PORTABLE_SHA, 'Portable Action source differs')
    helper = importlib.import_module('mesh_cache_actor_full30_002')
    witness = importlib.import_module('native_validation_support_v9')
    portable = importlib.import_module('native_artifact_action_witness_008')
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module('character_designer')
    runtime = importlib.import_module('character_designer.forearm_twist')
    scene_module = policy.scene_module(package, report)
    require(Path(addon.__file__).resolve().parent == package, 'Another addon package imported')
    policy.bind_stage_proof(passed, report)
    handlers = base.handler_snapshot()
    session = source_scene = protected = props = staged = None
    registered, private_ids, errors = False, set(), []

    def protect(label):
        helper.admission.select_scene(bpy, source_scene)
        bpy.context.view_layer.update()
        require(not runtime._ERRORS, 'Source authoring runtime reported errors: '+label)
        observed = witness.source_property_witness(source_scene)
        row = {'output': base.compare_witness(protected, base.frame_witness(source_scene, source_pairs, runtime, {})),
               'source_properties_exact': props == observed}
        row['material_source_exact'] = policy.protect_source(source_scene)
        report[label] = row
        require(row['material_source_exact'], 'Current Source material/resource state changed: '+label)
        require(row['output']['exact'] and row['source_properties_exact'], 'Source changed: '+label)

    try:
        addon.register()
        registered = True
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(source_file)), 'Fixed input open failed')
        require(Path(bpy.data.filepath).resolve() == source_file, 'Another file opened')
        source_scene = policy.loaded_source(bpy)
        require(source_scene.frame_current == passed['saved_frame'] and float(source_scene.frame_subframe) == 0., 'Saved input frame differs')
        source_pairs = [(obj.name, obj) for obj in source_scene.objects]
        meshes = sorted((obj for obj in source_scene.objects if obj.type == 'MESH'), key=lambda obj: obj.name)
        caches = {row['source']: row for row in passed['cache_files']}
        require({obj.name for obj in meshes} == set(caches), 'Actor mapping changed')
        with runtime.defer_runtime(bpy.context, flush_on_exit=False):
            bpy.context.view_layer.update()
            for obj in meshes:
                if runtime.RECORD_KEY in obj:
                    runtime._calculate_object(obj, bpy.context.evaluated_depsgraph_get())
            bpy.context.view_layer.update()
            require(not runtime._ERRORS, 'Authoring correction failed')
            protected = base.frame_witness(source_scene, source_pairs, runtime, {})
            props = witness.source_property_witness(source_scene)
            policy.begin_source(source_scene, report)
            before_ids = base.native_id_pointers()
            try:
                print('PC2 artifact: clone begin', flush=True)
                session = scene_module.build_isolated_scene(source_scene)
                print('PC2 artifact: clone complete', flush=True)
            finally:
                private_ids = base.native_id_pointers() - before_ids
            require(session.source_scene is source_scene and set(session.object_map) == set(source_scene.objects), 'Full isolated Scene mapping required')
            helper.admission.select_scene(bpy, source_scene)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            objects = []
            for source in meshes:
                target = session.object_map[source]
                before = {int(item.as_pointer()) for item in bpy.data.meshes}
                mesh = bpy.data.meshes.new_from_object(source.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
                require(int(mesh.as_pointer()) not in before and mesh.library is None, 'New final Mesh ownership failed')
                session.created.append(('meshes', int(mesh.as_pointer()), mesh.session_uid))
                private_ids.add(int(mesh.as_pointer()))
                helper.inspect_stream(caches[source.name]['path'], len(mesh.vertices))
                require(mesh.shape_keys is None, 'Final Mesh has Shape Keys')
                for index, material in enumerate(tuple(mesh.materials)):
                    if material is not None:
                        material = getattr(material, 'original', material)
                        require(material in session.id_map, 'Material lacks isolated mapping')
                        mesh.materials[index] = session.id_map[material]
                target.data = mesh
                target.modifiers.clear()
                if runtime.RECORD_KEY in target:
                    del target[runtime.RECORD_KEY]
                modifier = target.modifiers.new('Cached Playback', 'MESH_CACHE')
                modifier.filepath = caches[source.name]['path']
                for key, value in contract.CACHE_SETTINGS.items():
                    setattr(modifier, key, value)
                objects.append({'source_name': source.name, 'target_name': target.name_full,
                    'target_data_name': mesh.name_full, 'cache': caches[source.name],
                    'modifier': {'name': modifier.name, 'settings': contract.modifier_state(modifier)}})
            scene = session.scene
            policy.bind_target(session, report)
            helper.admission.select_scene(bpy, scene)
            scene.frame_set(1, subframe=0.)
            bpy.context.view_layer.update()
            materials = [{'target': contract.logical(target), 'source': contract.logical(source)}
                for source, target in session.id_map.items() if isinstance(target, bpy.types.Material)]
            closure = dependency_closure(scene)
            require(not (closure & set(session.id_map)), 'Serialization reaches an original authoring ID')
            require(not any(isinstance(item, bpy.types.Scene) and item is not scene for item in closure), 'Serialization reaches another Scene')
            actions = sorted((item for item in closure if isinstance(item, bpy.types.Action)), key=lambda item: item.name_full)
            closure_ids = contract.json_value(sorted((portable.identity(item) for item in closure), key=repr))
            reopen = {'schema': contract.SCHEMA, 'accepted_full30_report': passed_pin,
                'source_snapshot_scope': 'Guarded current SaveCopy at its receipt timestamp; later artist edits require a new capture.',
                'current_snapshot_receipt': policy.snapshot_receipt_pin,
                'visibility': session.view_layer_state,
                'shader_id_mapping': policy.shader_id_mapping,
                'scene': {**contract.scene_state(scene), 'saved_frame': 1, 'frames': list(contract.FRAMES)},
                'objects': objects, 'material_id_map': materials, 'actions': [contract.logical(item) for item in actions],
                'portable_animation': contract.json_value(portable.capture(scene, actions)), 'serialized_dependency_ids': closure_ids,
                'expected_scene_names': [scene.name_full],
                'package': {'path': str(package), 'addons': str(package.parent), 'manifest': passed['source_manifest'], 'files': passed['source_package']}}
            report['reopen_contract'] = reopen
            report['external_assets'], report['external_concrete_files'] = external_assets(closure)
            report['replay'] = []
            for frame in contract.FRAMES:
                scene.frame_set(frame, subframe=0.)
                bpy.context.view_layer.update()
                row = contract.check_frame(scene, reopen, frame)
                report['replay'].append(row)
                require(row['exact'], 'Assembler geometry differs at frame '+str(frame))
            report['all_30_geometry_exact'] = True
            scene.frame_set(1, subframe=0.)
            bpy.context.view_layer.update()
            require(contract.animation_state(scene, reopen) == reopen['portable_animation'], 'Animation changed during replay')
            before_geometry = contract.check_frame(scene, reopen, 1)
            protect('source_before_write')
            helper.admission.select_scene(bpy, scene)
            bpy.context.view_layer.update()
            paths_before = asset_paths()
            staged = output.with_name('.'+output.stem+'.'+uuid.uuid4().hex+'.staged.blend')
            require(not staged.exists(), 'Staging path collision')
            report['artifact_staging_path'] = str(staged)
            bpy.data.libraries.write(str(staged), {scene}, path_remap='ABSOLUTE', compress=True)
            report['artifact_staged'] = base.pin(staged)
            require(report['artifact_staged']['bytes'] > 0, 'Empty serialized artifact')
            report['write_preserved_candidate_exact'] = (before_geometry == contract.check_frame(scene, reopen, 1)
                and reopen['portable_animation'] == contract.animation_state(scene, reopen)
                and closure_ids == contract.json_value(sorted((portable.identity(item) for item in dependency_closure(scene)), key=repr))
                and paths_before == asset_paths())
            require(report['write_preserved_candidate_exact'], 'Serialization changed candidate/source asset paths or Action/geometry content')
            protect('source_after_write')
    finally:
        if source_scene is not None:
            with runtime.defer_runtime(bpy.context, flush_on_exit=False):
                helper.admission.select_scene(bpy, source_scene)
                if session is not None:
                    try:
                        session.close()
                    except BaseException:
                        errors.append(traceback.format_exc())
                if protected is not None:
                    try:
                        protect('source_after_cleanup')
                    except BaseException:
                        errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        report['scene_module_proof_unchanged'] = policy.scene_sources_unchanged()
        report['cleanup'] = {'errors': errors,
            'owned_ids_removed': not bool(private_ids & base.native_id_pointers()),
            'handlers_restored_exact': handlers == base.handler_snapshot(),
            'scene_module_proof_unchanged': report['scene_module_proof_unchanged']}
        try:
            contract.verify_external_pins(report)
            report['cleanup']['all_external_source_artist_cache_pins_unchanged'] = True
        except BaseException:
            report['cleanup']['all_external_source_artist_cache_pins_unchanged'] = False
            errors.append(traceback.format_exc())
        require(not errors and all(value is True for key, value in report['cleanup'].items() if key != 'errors'), 'Assembler cleanup/protected pins failed')
        require(report.get('source_after_cleanup', {}).get('output', {}).get('exact') is True
            and report['source_after_cleanup']['source_properties_exact'], 'Final source proof failed')
    require(staged is not None and report.get('write_preserved_candidate_exact') is True
        and report.get('all_30_geometry_exact') is True, 'No verified staging candidate')
    require(base.pin(staged) == report['artifact_staged'], 'Staged file changed before publication')
    policy.finalize_assembly(report)
    publish(staged, output, report)
