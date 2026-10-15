"""Root-only disposable factory diagnosis: ID.copy versus Stage09 remapping.

Never reads an unset Cycles getter, opens an input, registers CD or launches
Blender. A reproduced clone difference is diagnostic evidence, not acceptance.
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
STAGE = HERE/'staged_20261015_09'
MANIFEST_SHA = 'b8faecfb0ce428bbdc3d845494fae7cb2aa5db4b4c9ad875e399194f98529ee6'
SCENE_SHA = '3d06f61b85758723150f518524ea63aee066e545cb4b6ad2a7499ebfb877b4ac'
sys.path.insert(0, str(HERE))
import native_validation_support as base


def require(value, message):
    if not value:
        raise RuntimeError(message)


def raw_value(value, bpy):
    if value is None or type(value) in (bool, int, str):
        return value
    if isinstance(value, float):
        return {'float_hex': value.hex()}
    if isinstance(value, bpy.types.ID):
        return {'id': value.bl_rna.identifier, 'name': value.name_full,
            'pointer': int(value.as_pointer()), 'uid': value.session_uid}
    if hasattr(value, 'items'):
        return {key: raw_value(item, bpy) for key, item in value.items()}
    return [raw_value(item, bpy) for item in value]


def snapshot(owner, bpy):
    # Explicit base descriptor bypasses any registered "items" shadow.
    raw = {key: raw_value(value, bpy) for key, value in bpy.types.bpy_struct.items(owner)}
    return {'cycles_set': bool(owner.is_property_set('cycles')), 'raw': raw}


def restore_hook(owner, installed, original):
    owned = owner._remap_rna is installed
    if owned:
        owner._remap_rna = original
    return owned and owner._remap_rna is original


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath
        and bpy.app.version[:2] == (5, 2), 'New private blank factory Blender5.2 required')
    require(any(value in ('-t', '--threads') and native[i+1] == '1'
        for i, value in enumerate(native[:-1])), 'Explicit native -t 1 required')
    artist = base.pin(args.artist)
    require(artist['sha256'] == args.artist_sha256, 'Root artist disk pin differs')
    manifest = base.pin(STAGE/'source_manifest.json')
    require(manifest['sha256'] == MANIFEST_SHA, 'Stage09 manifest changed')
    package = STAGE/'addons/character_designer'
    sources = base.verify_package_manifest(package,
        json.loads(Path(manifest['path']).read_text(encoding='utf-8-sig')))
    require(base.pin(package/'forearm_twist_playback_scene.py')['sha256'] == SCENE_SHA, 'Stage09 scene changed')
    require('character_designer' not in sys.modules, 'Foreign Character Designer already imported')
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module('character_designer')
    scene_module = importlib.import_module('character_designer.forearm_twist_playback_scene')
    require(Path(addon.__file__).resolve().parent == package and Path(scene_module.__file__).resolve().parent == package,
        'Foreign Stage09 module loaded')
    original_scene, original_layer = bpy.context.scene, bpy.context.view_layer
    ids_before, handlers = scene_module._inventory(), base.handler_snapshot()
    created, session, errors, hook = [], None, [], None
    report.update(blender=bpy.app.version_string, artist_before=artist, manifest=manifest,
        scene_source=base.pin(scene_module.__file__), script=base.pin(__file__), support=base.pin(base.__file__),
        source_package=sources, imported_addon_version=list(addon.bl_info['version']), remap_events=[])
    def own(collection, value):
        created.append((collection, int(value.as_pointer()), value.session_uid))
        return value
    try:
        source = own('scenes', bpy.data.scenes.new('Unset Cycles Source'))
        world = own('worlds', bpy.data.worlds.new('Unset Cycles World'))
        unset = own('materials', bpy.data.materials.new('Unset Cycles Material'))
        stored = own('materials', bpy.data.materials.new('Stored Cycles Material'))
        world.use_nodes = unset.use_nodes = stored.use_nodes = True
        # Intentionally set one known scalar on this newly owned fixture only.
        stored.cycles.volume_step_rate = 1.25
        source.world = world
        mesh = own('meshes', bpy.data.meshes.new('Unset Cycles Mesh'))
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        mesh.materials.append(unset)
        mesh.materials.append(stored)
        obj = own('objects', bpy.data.objects.new('Unset Cycles Object', mesh))
        source.collection.objects.link(obj)
        bpy.context.window.scene = source
        owners = {'world': world, 'unset_material': unset, 'stored_material': stored}
        before = {key: snapshot(value, bpy) for key, value in owners.items()}
        require(not before['world']['cycles_set'] and not before['unset_material']['cycles_set']
            and before['stored_material']['cycles_set'], 'Fixture did not establish unset/stored Cycles states')
        report['source_initial'] = before
        direct = {key: own('worlds' if key == 'world' else 'materials', value.copy())
            for key, value in owners.items()}
        report['direct_id_copy'] = {key: snapshot(value, bpy) for key, value in direct.items()}
        report['direct_copy_preserves_state'] = report['direct_id_copy'] == before
        report['source_after_direct_copy_exact'] = before == {key: snapshot(value, bpy) for key, value in owners.items()}
        require(report['source_after_direct_copy_exact'], 'ID.copy changed fixture Source')
        original_remap = scene_module._remap_rna
        def observed_remap(struct, id_map, visited, external):
            owner = struct.id_data
            watched = isinstance(owner, (bpy.types.World, bpy.types.Material))
            state = snapshot(owner, bpy) if watched else None
            if watched and len(report['remap_events']) < 48:
                report['remap_events'].append({'phase': 'enter', 'struct': struct.bl_rna.identifier,
                    'owner': owner.name_full, 'state': state})
            try:
                return original_remap(struct, id_map, visited, external)
            finally:
                if watched:
                    after = snapshot(owner, bpy)
                    if state != after:
                        report['remap_events'].append({'phase': 'changed', 'struct': struct.bl_rna.identifier,
                            'owner': owner.name_full, 'before': state, 'after': after})
        hook = observed_remap
        scene_module._remap_rna = hook
        session = scene_module.build_isolated_scene(source)
        report['builder_copy'] = {key: snapshot(session.id_map[value], bpy) for key, value in owners.items()}
        report['builder_preserves_state'] = report['builder_copy'] == before
        report['source_after_build_exact'] = before == {key: snapshot(value, bpy) for key, value in owners.items()}
        report['reproduced_remapper_materialization'] = (report['direct_copy_preserves_state']
            and not report['builder_preserves_state'] and any(row['phase'] == 'changed' for row in report['remap_events']))
        require(report['source_after_build_exact'], 'Builder changed fixture Source')
        # Own stored scalar is read only after proving this pointer was stored.
        report['stored_value_preserved'] = (stored.cycles.volume_step_rate.hex()
            == session.id_map[stored].cycles.volume_step_rate.hex())
        require(report['stored_value_preserved'], 'Stored Cycles scalar changed')
    finally:
        if hook is not None:
            report['remap_hook_restored'] = restore_hook(scene_module, hook, original_remap)
        else:
            report['remap_hook_restored'] = True
        try:
            bpy.context.window.scene = original_scene
            bpy.context.window.view_layer = original_layer
        except BaseException:
            errors.append(traceback.format_exc())
        if session is not None:
            try:
                session.close()
            except BaseException:
                errors.append(traceback.format_exc())
        if 'owners' in locals() and 'before' in locals():
            try:
                report['source_after_close_exact'] = before == {key: snapshot(value, bpy) for key, value in owners.items()}
            except BaseException:
                errors.append(traceback.format_exc())
        for collection_name, pointer, uid in reversed(created):
            collection = getattr(bpy.data, collection_name)
            matches = [item for item in collection if int(item.as_pointer()) == pointer]
            if not matches:
                continue
            if len(matches) != 1 or matches[0].session_uid != uid:
                errors.append('Owned UID changed: '+collection_name)
                continue
            try:
                collection.remove(matches[0], do_unlink=True)
            except BaseException:
                errors.append(traceback.format_exc())
        report['cleanup'] = {'errors': errors, 'owned_ids_removed': scene_module._inventory() == ids_before,
            'handlers_unchanged': base.handler_snapshot() == handlers, 'artist_disk_unchanged': base.pin(args.artist) == artist,
            'context_restored': bpy.context.scene is original_scene
                and int(bpy.context.view_layer.as_pointer()) == int(original_layer.as_pointer()),
            'scripts_unchanged': base.pin(__file__) == report['script'] and base.pin(base.__file__) == report['support'],
            'stage09_unchanged': base.pin(STAGE/'source_manifest.json') == manifest
                and base.verify_package_manifest(package, json.loads(Path(manifest['path']).read_text(encoding='utf-8-sig'))) == sources,
            'remap_hook_restored': report['remap_hook_restored'],
            'fixture_source_after_close_exact': report.get('source_after_close_exact') is True}
        if sys.exc_info()[0] is None:
            require(not errors and all(value is True for key, value in report['cleanup'].items() if key != 'errors'),
                'Disposable fixture cleanup failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('report', 'artist', 'artist-sha256'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output = Path(args.report).resolve()
    require(output.parent == HERE and output.suffix == '.json' and not output.exists(), 'Unused direct project JSON required')
    report = {'schema': 'x.native-unset-cycles-copy-fixture/1', 'completed': False, 'pid': os.getpid(),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'diagnostic_only': True,
        'no_artist_or_input_open_save': True, 'no_cd_registration_or_solver': True,
        'scope': 'Own factory World/Material ID.copy and Stage09 builder storage flags/raw; no shader/domain acceptance.'}
    with output.open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
