"""Assemble a local Scene-only candidate from an actual passed Full30_004 clip.

Root alone launches this fresh background worker. Existing PC2 files are read
and pinned, never regenerated. A new .blend is published only after all thirty
strict geometry visits, source restoration, serialization and cleanup gates.
Normal GUI reopen, shader appearance and GUI FPS remain separate acceptance.
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
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hashlib.sha256((HERE/'mesh_cache_artifact_contract_005.py').read_bytes()).hexdigest() != 'a4e68220734435de8f8ac52bbbca73c2b7259253626c1bc301dfcfc9b55efad6':
    raise RuntimeError('Reviewed artifact contract source changed')
import mesh_cache_artifact_contract_005 as contract

base, require = contract.base, contract.require


def dependency_closure(scene):
    return contract.dependency_closure(scene)


def asset_paths():
    """Snapshot only file path fields; no texspace or registered PG getters."""
    import bpy
    result = {}
    for name in ('images', 'libraries', 'movieclips', 'sounds', 'fonts', 'volumes', 'cache_files'):
        for item in getattr(bpy.data, name):
            result[name+':'+item.name_full] = {field: getattr(item, field)
                for field in ('filepath', 'filepath_raw') if hasattr(item, field)}
    return result


def external_assets(closure):
    """List concrete paths honestly; packed/token/sequence pixels are not proved."""
    import bpy
    records, pins = [], {}
    for item, paths in bpy.data.file_path_map(subset=closure, include_libraries=True).items():
        for raw in sorted(paths):
            resolved = str(Path(bpy.path.abspath(raw, library=item.library)).resolve())
            path = Path(resolved)
            concrete = path.is_file()
            records.append({'owner': contract.logical(item), 'raw_path': raw,
                'absolute_path': resolved, 'concrete_file': concrete,
                'scope': 'External local dependency; packed pixels, UDIM/sequence expansion and render reachability are unproved.'})
            if concrete:
                pins[resolved] = base.pin(path)
    return records, list(pins.values())


def publish(staged, output, report):
    """No overwrite. Successful link is recorded before fallible verification."""
    expected = base.pin(staged)
    os.link(staged, output)
    report.update(artifact_published=True, artifact={'path': str(output), 'sha256': expected['sha256'], 'bytes': expected['bytes']},
                  artifact_link_created=True, artifact_publication_complete=False)
    require(base.pin(output) == report['artifact'], 'Published file content differs from owned staging')
    report['artifact_output_verified'] = True
    staged.unlink()
    report['artifact_staging_removed'] = True
    require(base.pin(output) == report['artifact'], 'Published file changed during finalization')
    report['artifact_publication_complete'] = True


def main(args, report):
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
    adapter = importlib.import_module('mesh_cache_actor_full30_004')
    parent = importlib.import_module('mesh_cache_actor_parent_diagnostic_003')
    helper = importlib.import_module('mesh_cache_actor_full30_002')
    witness = importlib.import_module('native_validation_support_v9')
    portable = importlib.import_module('native_artifact_action_witness_008')
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module('character_designer')
    runtime = importlib.import_module('character_designer.forearm_twist')
    scene_module = importlib.import_module('character_designer.forearm_twist_playback_scene')
    require(Path(addon.__file__).resolve().parent == package, 'Another addon package imported')
    old_remap = scene_module._remap_rna
    patched, owned_globals, seal = parent.sealed_remap(scene_module.__dict__)
    require(seal == passed['parent_override'], 'Parent runtime seal differs from accepted run')
    owned_globals['_remap_rna'] = patched
    scene_module._remap_rna = patched
    report['parent_override'] = seal
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
        report[label] = row
        require(row['output']['exact'] and row['source_properties_exact'], 'Source changed: '+label)

    try:
        addon.register()
        registered = True
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(source_file)), 'Fixed input open failed')
        require(Path(bpy.data.filepath).resolve() == source_file, 'Another file opened')
        source_scene = bpy.context.scene
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
                'source_snapshot_scope': 'Earlier fixed40644 private input, not a current live-artist snapshot; artist disk pin is protection only, not current-model equivalence.',
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
        report['parent_hook_still_owned'] = scene_module._remap_rna is patched
        report['parent_hook_restored'] = parent.restore_owned_hooks((('parent', scene_module, '_remap_rna', patched, old_remap),))['parent']
        report['cleanup'] = {'errors': errors,
            'owned_ids_removed': not bool(private_ids & base.native_id_pointers()),
            'handlers_restored_exact': handlers == base.handler_snapshot(),
            'parent_hook_still_owned': report['parent_hook_still_owned'], 'parent_hook_restored': report['parent_hook_restored']}
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
    publish(staged, output, report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('full30-report', 'full30-sha256', 'artist', 'output', 'report'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': contract.RECEIPT_SCHEMA, 'completed': False, 'artifact_published': False,
        'artifact_publication_complete': False, 'gui_fps_verified': False, 'normal_reopen_verified': False,
        'pid': os.getpid(), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'limits': ['Local durable dependency bundle: PC2 and external images are not embedded/portable.',
            'Earlier fixed40644 private snapshot only; artist disk pin is protection, not proof of equivalence to the current live artist/model.',
            'Integer frames1-30 full native geometry/world/three-normal oracle only; shader appearance, subframes and motion blur unproved.',
            'Candidate pending separate normal-addon GUI reopen and measured GUI FPS; no artist adoption/deploy or artist save.']}
    # Reserve receipt before anything that could publish an artifact.
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
