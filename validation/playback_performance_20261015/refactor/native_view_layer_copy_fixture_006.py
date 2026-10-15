"""Root-only tiny native Base-state proof; no artist/input open or addon register.

Optional new fixture .blend plus expected state supports a separate reopen run.
No Native is launched by preparing/importing this script outside its entry.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_cache_view_layer_adapter_006 as adapter

base, require = adapter.base, adapter.require


def snapshot(scene):
    return [{'name': layer.name, 'active': layer.objects.active.name_full if layer.objects.active else None,
        'objects': [{'name': obj.name_full, 'hidden': bool(obj.hide_get(view_layer=layer)),
                     'selected': bool(obj.select_get(view_layer=layer))}
                    for obj in sorted(layer.objects, key=lambda item: item.name_full)]}
            for layer in scene.view_layers]


def layer_map(layer):
    result = {}
    def visit(item):
        result[item.collection] = item
        for child in item.children:
            visit(child)
    visit(layer.layer_collection)
    return result


def reopen(args, report):
    import bpy
    pin = base.pin(args.reopen_report)
    require(pin['sha256'] == args.reopen_report_sha256, 'Explicit tiny receipt SHA differs')
    receipt = json.loads(Path(pin['path']).read_text(encoding='utf-8-sig'))
    require(receipt.get('completed') is True and 'error' not in receipt and receipt.get('source_exact') is True
        and receipt.get('all_visits_exact') is True and receipt.get('cleanup', {}).get('owned_ids_removed') is True,
        'Actually passed tiny receipt required')
    for item in receipt['scripts'].values():
        require(base.pin(item['path']) == item, 'Tiny source changed')
    fixture = receipt['fixture']
    require(base.pin(fixture['path']) == fixture, 'Owned tiny fixture changed')
    require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=fixture['path'], load_ui=False), 'Fixture open failed')
    state = receipt['visibility_contract']
    scene = bpy.context.scene
    bpy.context.window.view_layer = scene.view_layers[state['context_view_layer']]
    require(adapter.check_visibility(scene, state, all_layers=True)['exact'], 'Saved Base state did not survive native reopen')
    require(base.pin(fixture['path']) == fixture, 'Opening modified fixture disk')
    report.update(reopen_receipt=pin, fixture=fixture, reopened_base_state_exact=True,
                  loaded_private_ids_cleanup='Owned background process exits after this script; factory Main was replaced by its own tiny fixture.')


def main(args, report):
    import bpy
    require(bpy.app.background and '--factory-startup' in sys.argv and not bpy.data.filepath
        and bpy.app.version[:2] == (5, 2), 'New private factory background Blender5.2 required')
    report['blender'] = bpy.app.version_string
    if args.reopen_report:
        require(args.reopen_report_sha256 and not args.fixture_output, 'Reopen requires explicit receipt SHA only')
        reopen(args, report)
        return
    require(not args.reopen_report_sha256, 'Receipt SHA without reopen path')
    original = bpy.context.scene
    handlers, before = base.handler_snapshot(), base.native_id_pointers()
    created, errors, seal = [], [], None
    def own(collection, item):
        created.append((collection, int(item.as_pointer()), item.session_uid))
        return item
    scripts = {Path(__file__).name: base.pin(__file__), Path(adapter.__file__).name: base.pin(adapter.__file__)}
    report['scripts'] = scripts
    try:
        source = own('scenes', bpy.data.scenes.new('Base State Source'))
        bpy.context.window.scene = source
        source.view_layers[0].name = 'Main'
        source.view_layers.new('Other')
        collections = {}
        for name in ('Visible', 'Excluded', 'Locked'):
            collection = own('collections', bpy.data.collections.new(name))
            source.collection.children.link(collection)
            collections[name] = collection
        rig_data = own('armatures', bpy.data.armatures.new('Fixture Rig Data'))
        rig = own('objects', bpy.data.objects.new('Fixture Rig', rig_data))
        backup = own('objects', bpy.data.objects.new('Fixture Backup', None))
        excluded = own('objects', bpy.data.objects.new('Fixture Excluded', None))
        locked = own('objects', bpy.data.objects.new('Fixture Locked', None))
        for obj in (rig, backup):
            collections['Visible'].objects.link(obj)
        collections['Excluded'].objects.link(excluded)
        collections['Locked'].objects.link(locked)
        collections['Locked'].hide_select = True
        for layer in source.view_layers:
            layer_map(layer)[collections['Excluded']].exclude = True
            layer.update()
        main_layer, other = source.view_layers['Main'], source.view_layers['Other']
        backup.hide_set(True, view_layer=main_layer)
        rig.select_set(True, view_layer=main_layer)
        main_layer.objects.active = rig
        rig.hide_set(True, view_layer=other)
        backup.select_set(True, view_layer=other)
        other.objects.active = backup
        for layer in source.view_layers:
            layer.update()
        bpy.context.window.view_layer = main_layer
        protected = snapshot(source)
        target = own('scenes', source.copy())
        target.name = 'Base State Target'
        for child in tuple(target.collection.children):
            target.collection.children.unlink(child)
        mapping = {source: target, source.collection: target.collection}
        object_map = {}
        for old in collections.values():
            new = own('collections', bpy.data.collections.new(old.name+' Playback'))
            new.hide_viewport, new.hide_render = old.hide_viewport, old.hide_render
            target.collection.children.link(new)
            mapping[old] = new
            for obj in old.objects:
                clone = own('objects', obj.copy())
                clone.name = obj.name+' Playback'
                if obj.data is not None:
                    clone.data = own('armatures', obj.data.copy())
                new.objects.link(clone)
                mapping[obj], object_map[obj] = clone, clone
        for old_layer, new_layer in zip(source.view_layers, target.view_layers):
            old_tree, new_tree = layer_map(old_layer), layer_map(new_layer)
            for collection, item in old_tree.items():
                copied = new_tree[mapping[collection]]
                for field in ('exclude', 'hide_viewport', 'holdout', 'indirect_only'):
                    setattr(copied, field, getattr(item, field))
            new_layer.update()
        report['old_relink_state'] = snapshot(target)
        report['old_hidden_state_lost'] = not object_map[backup].hide_get(view_layer=target.view_layers['Main'])
        require(report['old_hidden_state_lost'], 'Tiny did not reproduce old Base hiding loss')
        copy, seal = adapter.sealed_copy({'bpy': bpy, '_require': require})
        session = SimpleNamespace(source_scene=source, scene=target, id_map=mapping, object_map=object_map, closed=False)
        state = copy(session)
        report.update(visibility_override=seal, visibility_contract=state, visits=[])
        bpy.context.window.scene = target
        bpy.context.window.view_layer = target.view_layers[state['context_view_layer']]
        for frame in (1, 2, 1):
            target.frame_set(frame)
            bpy.context.view_layer.update()
            exact = snapshot(target) == state['layers']
            report['visits'].append({'frame': frame, 'exact': exact})
            require(exact, 'Native seek changed copied Base state')
        bpy.context.window.scene = source
        bpy.context.window.view_layer = main_layer
        report['source_exact'] = snapshot(source) == protected
        report['all_visits_exact'] = all(row['exact'] for row in report['visits'])
        require(report['source_exact'], 'Copy/seek changed Source Base state')
        if args.fixture_output:
            output = Path(args.fixture_output).resolve()
            require(output.suffix.lower() == '.blend' and output.parent.is_dir() and not output.exists(), 'Unused tiny fixture output required')
            bpy.data.libraries.write(str(output), {target}, path_remap='ABSOLUTE', compress=True)
            report['fixture'] = base.pin(output)
            require(snapshot(source) == protected and snapshot(target) == state['layers'], 'Tiny write changed native Base state')
    finally:
        bpy.context.window.scene = original
        for collection_name, pointer, uid in reversed(created):
            collection = getattr(bpy.data, collection_name)
            matches = [item for item in collection if int(item.as_pointer()) == pointer]
            if not matches:
                continue
            if len(matches) != 1 or matches[0].session_uid != uid:
                errors.append('Native ownership reused: '+collection_name)
                continue
            try:
                collection.remove(matches[0], do_unlink=True)
            except BaseException:
                errors.append(traceback.format_exc())
        report['cleanup'] = {'errors': errors, 'owned_ids_removed': base.native_id_pointers() == before,
            'handlers_unchanged': handlers == base.handler_snapshot(),
            'scripts_unchanged': all(item == base.pin(item['path']) for item in scripts.values()),
            'stage09_unchanged': seal is not None and seal['manifest'] == base.pin(seal['manifest']['path'])
                and seal['scene_source'] == base.pin(seal['scene_source']['path']) and seal['package'] == base.verify_package_manifest(
                adapter.STAGE/'addons/character_designer', json.loads(Path(seal['manifest']['path']).read_text(encoding='utf-8-sig')))}
        require(not errors and all(value is True for key, value in report['cleanup'].items() if key != 'errors'), 'Tiny cleanup failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    parser.add_argument('--fixture-output')
    parser.add_argument('--reopen-report')
    parser.add_argument('--reopen-report-sha256')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.native-view-layer-copy-fixture/1', 'completed': False, 'pid': os.getpid(),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'diagnostic_only': True,
        'no_artist_or_fixed_input_open': True, 'no_addon_registration': True}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
