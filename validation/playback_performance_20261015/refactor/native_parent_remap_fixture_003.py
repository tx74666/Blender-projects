"""Tiny native parent-inverse regression; Root alone runs the private worker.

No addon registration, artist open, clip, save or GUI. Compare the actual old
Stage06 remap with the sealed Stage08 replacement using only our new native IDs.
"""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
HELPER = HERE/'mesh_cache_actor_parent_diagnostic_003.py'
if hashlib.sha256(HELPER.read_bytes()).hexdigest() != 'e2015c64d1e83e2ac4dba1339dd488cce8f36d09f4adc9f900144bc661b5e73b':
    raise RuntimeError('Parent diagnostic helper changed')
import mesh_cache_actor_parent_diagnostic_003 as helper

base, require = helper.base, helper.require
OLD = HERE/'staged_20261015_06/addons/character_designer/forearm_twist_playback_scene.py'
OLD_SHA = 'e4f4f58378540d23ea8c3acf6f4bbc7a3b056494b7af480e2f3b9aa092ecef3d'


def source_transform(state):
    # COW pointer addresses may change when adding fixture IDs/rebuilding graph;
    # protect the Main identity and all transform payload, not ephemeral IDs.
    ignored = {'pointer', 'session_uid', 'parent_pointer', 'parent_session_uid'}
    return {**state, 'evaluated': {key: value for key, value in state['evaluated'].items() if key not in ignored}}


def old_scope(bpy):
    require(base.pin(OLD)['sha256'] == OLD_SHA, 'Historical Stage06 scene source changed')
    tree = ast.parse(OLD.read_text(encoding='utf-8'))
    names = {'PlaybackSceneError', '_require', '_pointer', '_copy_id_properties', '_remap_rna'}
    constants = {'_GEOMETRY_COLLECTIONS', '_READONLY_OBJECT_POINTERS'}
    nodes = [node for node in tree.body if
             isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names
             or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in constants for target in node.targets)]
    scope = {'bpy': bpy}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(OLD), 'exec'), scope)
    return scope


def main(args, report):
    import bpy
    from mathutils import Matrix
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath,
            'Fresh private factory background worker required')
    require(any(value in ('-t', '--threads') and native[i+1] == '1' for i, value in enumerate(native[:-1])), '-t 1 required')
    require(bpy.app.version[:2] == (5, 2), 'Blender 5.2 required')
    original_scene = bpy.context.scene
    ids, handlers, artist = base.native_id_pointers(), base.handler_snapshot(), base.pin(args.artist)
    old = old_scope(bpy)
    fixed, fixed_scope, seal = helper.sealed_remap(old)
    created, errors = [], []
    report.update(scripts={path.name: base.pin(path) for path in (Path(__file__), HELPER, OLD, helper.ACTOR, helper.actor.BASE, helper.actor.FACTORY)},
                  parent_patch=seal, artist_before=artist, blender=bpy.app.version_string)
    def own(collection, item):
        require(item.library is None and item.session_uid > 0 and item.as_pointer() not in ids, 'Fixture ID is not owned')
        created.append((collection, int(item.as_pointer()), item.session_uid))
        return item
    try:
        scene = own('scenes', bpy.data.scenes.new('Parent Copy Fixture'))
        bpy.context.window.scene = scene
        parent = own('objects', bpy.data.objects.new('Parent Source', None))
        scene.collection.objects.link(parent)
        parent.location, parent.rotation_euler, parent.scale = (2., -3., 1.), (.125, -.25, .375), (1.25, .75, 1.5)
        mesh = own('meshes', bpy.data.meshes.new('Child Source Mesh'))
        mesh.from_pydata(((0., 0., 0.), (1., 0., 0.), (0., 1., 0.)), (), ((0, 1, 2),))
        source = own('objects', bpy.data.objects.new('Child Source', mesh))
        scene.collection.objects.link(source)
        source.parent = parent
        source.location, source.rotation_euler, source.scale = (.5, -.25, 1.), (.25, .125, -.125), (.75, 1.25, 1.)
        source.matrix_parent_inverse = Matrix(((1.5, -0., 0., .25), (0., .75, .125, -.5),
                                                (0., 0., 1.25, .75), (0., 0., 0., 1.)))
        scene.frame_set(1)
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        protected = helper.object_state(source, {}, graph)
        parent_copy = own('objects', parent.copy())
        parent_copy.name = 'Parent Copy'
        scene.collection.objects.link(parent_copy)
        children = {}
        for label, remap in (('old', old['_remap_rna']), ('fixed', fixed)):
            child = own('objects', source.copy())
            child.name = 'Child '+label.title()
            child.data = own('meshes', mesh.copy())
            scene.collection.objects.link(child)
            before = helper.object_state(child, {})
            require(before['raw']['inverse'] == protected['raw']['inverse'], 'ID.copy already changed inverse')
            mapping = {parent: parent_copy, source: child, mesh: child.data}
            remap(child, mapping, set(), [])
            after = helper.object_state(child, {})
            report[label] = {'before_remap_raw': before, 'after_remap_raw': after}
            children[label] = child
        require(report['old']['after_remap_raw']['raw']['inverse'] == helper.matrix_hex(Matrix.Identity(4)),
                'Old native parent setter did not demonstrate inverse reset')
        require(report['fixed']['after_remap_raw']['raw']['inverse'] == protected['raw']['inverse'],
                'Fixed native parent remap did not restore the exact inverse')
        report['visits'] = []
        for frame in (1, 2, 1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            current_source = helper.object_state(source, {}, graph)
            require(source_transform(protected) == source_transform(current_source), 'Fixture source transform changed')
            rows = {}
            for label, child in children.items():
                state = helper.object_state(child, {}, graph)
                delta = helper.matrix_delta(protected['evaluated']['world'], state['evaluated']['world'])
                rows[label] = {'state': state, 'world_delta': delta}
            require(not rows['old']['world_delta']['hex_exact'] and rows['old']['world_delta']['max_abs_delta'] > 0.,
                    'Old remap did not demonstrate a numeric world-matrix error')
            require(rows['fixed']['world_delta']['hex_exact'], 'Fixed remap evaluated world differs')
            report['visits'].append({'frame': frame, 'results': rows})
        report['native_old_reset_and_fixed_exact'] = True
        print('PARENT_REMAP_FIXTURE_PASS', flush=True)
    finally:
        bpy.context.window.scene = original_scene
        for collection in ('objects', 'meshes', 'scenes'):
            for kind, pointer, uid in reversed(created):
                if kind != collection:
                    continue
                try:
                    item = next((item for item in getattr(bpy.data, collection) if int(item.as_pointer()) == pointer), None)
                    require(item is not None and item.session_uid == uid, 'Owned fixture ID changed')
                    getattr(bpy.data, collection).remove(item, do_unlink=True)
                except BaseException:
                    errors.append(traceback.format_exc())
        report['cleanup'] = {'errors': errors, 'owned_ids_removed': ids == base.native_id_pointers(),
            'context_restored': bpy.context.scene is original_scene, 'handlers_unchanged': handlers == base.handler_snapshot(),
            'artist_disk_unchanged': artist == base.pin(args.artist),
            'scripts_unchanged': all(item == base.pin(item['path']) for item in report['scripts'].values()),
            'stage08_unchanged': seal['manifest'] == base.pin(helper.STAGE/'source_manifest.json')
                and seal['package'] == base.verify_package_manifest(helper.STAGE/'addons/character_designer',
                    json.loads((helper.STAGE/'source_manifest.json').read_text(encoding='utf-8-sig')))}
        require(not errors and all(value for key, value in report['cleanup'].items() if key != 'errors'), 'Parent fixture cleanup/protection failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artist', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.native-parent-remap-fixture/1', 'completed': False, 'diagnostic_only': True,
        'pid': os.getpid(), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'no_addon_register_or_blend_open_save': True, 'no_gui_or_actor_acceptance': True}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
