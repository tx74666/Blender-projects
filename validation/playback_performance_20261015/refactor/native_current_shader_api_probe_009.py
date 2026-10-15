"""Private native shape diagnostic only; no registration, solver or acceptance."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
INPUT_SHA = '6fd14673d8acf03fd96b9856b1db09dd39a5492ae91ef3b68b49be80cd83a848'
INPUT_BYTES = 34843358
RECEIPT_SHA = '0e630be1a411994dabb689a80ad8c94fb3663d9924cc6c74693d3d71483dd6cc'
HELPER_SHA = '24468bd93de3ed4b63f2a6e2ab6354f299bfe191d714cde3ff39e55a5b415a90'
CYCLES_PATH = Path('D:/Blender5.2/5.2/scripts/addons_core/cycles/properties.py')
CYCLES_SHA = '77f24ef03164684c5cc866fa748445043b32023cbbd121b5e6523bd6433abd9d'
FIELDS = ('emission_sampling', 'use_bump_map_correction', 'volume_sampling', 'volume_interpolation', 'volume_step_rate')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path):
    path = Path(path).resolve()
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
            size += len(block)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': size}


def plain(value):
    import bpy
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, float):
        return {'float_hex': value.hex()}
    if isinstance(value, bpy.types.ID):
        return {'ID': value.bl_rna.identifier, 'name': value.name_full, 'uid': value.session_uid}
    if isinstance(value, bpy.types.bpy_struct):
        return raw(value)
    if hasattr(value, 'items'):
        return {str(key): plain(item) for key, item in value.items()}
    return [plain(item) for item in value]


def raw(value):
    import bpy
    try:
        return {str(key): plain(item) for key, item in bpy.types.bpy_struct.items(value)}
    except TypeError as error:
        require(str(error) == "bpy_struct.items(): this type doesn't support IDProperties", 'Unexpected raw storage error')
        return {'native_ID_properties': 'unsupported'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def descriptor(owner, prop):
    fixed = getattr(prop, 'fixed_type', None)
    return {'identifier': prop.identifier, 'type': prop.type, 'runtime': bool(getattr(prop, 'is_runtime', False)),
        'is_array': bool(getattr(prop, 'is_array', False)), 'array_length': int(getattr(prop, 'array_length', 0)),
        'fixed_type': fixed.identifier if fixed is not None else None,
        'is_property_set': bool(owner.is_property_set(prop.identifier)),
        'enum': [[item.identifier, item.value] for item in prop.enum_items] if prop.type == 'ENUM' else []}


def storage(owner):
    return {'raw_sha256': digest(raw(owner)), 'set_bits': [[prop.identifier, bool(owner.is_property_set(prop.identifier))]
        for prop in owner.bl_rna.properties if prop.identifier != 'rna_type']}


def context(bpy):
    scene, layer = bpy.context.scene, bpy.context.view_layer
    return {'filepath': bpy.data.filepath, 'dirty': bool(bpy.data.is_dirty), 'scene': int(scene.as_pointer()),
        'frame': [scene.frame_current, float(scene.frame_subframe)], 'view_layer': int(layer.as_pointer()),
        'active': int(layer.objects.active.as_pointer()) if layer.objects.active else None,
        'objects': sorted((int(obj.as_pointer()), obj.session_uid, bool(obj.hide_get(view_layer=layer)),
            bool(obj.select_get(view_layer=layer))) for obj in layer.objects)}


def handlers(bpy):
    return {name: [id(item) for item in value] for name, value in vars(bpy.app.handlers).items() if isinstance(value, list)}


def run(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath
        and bpy.app.version[:2] == (5, 2), 'Fresh private factory Blender5.2 background required')
    require(any(item in ('-t', '--threads') and native[index+1] == '1' for index, item in enumerate(native[:-1])), '-t1 required')
    require(args.snapshot_sha256 == RECEIPT_SHA, 'Actual Root SaveCopy010 receipt required')
    helper_path = HERE/'mesh_cache_current_input_007.py'
    require(pin(helper_path)['sha256'] == HELPER_SHA and pin(CYCLES_PATH)['sha256'] == CYCLES_SHA, 'Reviewed source changed')
    sys.path.insert(0, str(HERE))
    helper = importlib.import_module('mesh_cache_current_input_007')
    require(Path(helper.__file__).resolve() == helper_path, 'Foreign input helper')
    snapshot, receipt_pin = helper.load_snapshot(args.snapshot_report, RECEIPT_SHA, INPUT_SHA, INPUT_BYTES)
    source, artist = Path(snapshot['copy']['path']).resolve(), Path(snapshot['artist_before']['path']).resolve()
    require(source != artist and not os.path.samefile(source, artist), 'Never open artist/hardlink')
    files = {name: pin(path) for name, path in (('input', source), ('artist', artist), ('receipt', args.snapshot_report),
        ('script', Path(__file__)), ('input_helper', helper_path), ('cycles_source', CYCLES_PATH))}
    report.update(pid=os.getpid(), blender=bpy.app.version_string, files_before=files,
        current_snapshot_receipt=receipt_pin, input_before=files['input'])
    require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False), 'Private input open failed')
    before, callbacks = context(bpy), handlers(bpy)
    cycles = importlib.import_module('cycles.properties')
    require(Path(cycles.__file__).resolve() == CYCLES_PATH, 'Foreign Cycles properties module')
    cls, rows, trees = cycles.CyclesMaterialSettings, [], {}
    try:
        annotations = []
        for name, deferred in cls.__dict__.get('__annotations__', {}).items():
            keywords = getattr(deferred, 'keywords', {})
            function = getattr(deferred, 'function', None)
            annotations.append({'name': name, 'deferred_type': type(deferred).__name__,
                'factory': getattr(function, '__name__', None), 'keyword_names': sorted(keywords),
                'callbacks': {key: {'module': getattr(value, '__module__', None), 'qualname': getattr(value, '__qualname__', None)}
                    for key, value in keywords.items() if key in {'get', 'set', 'get_transform', 'set_transform', 'update'}}})
        report['cycles_class'] = {'module': cls.__module__, 'qualname': cls.__qualname__, 'module_file': cycles.__file__,
            'rna_identifier': cls.bl_rna.identifier, 'annotations': annotations}
        for material in bpy.data.materials:
            if material.node_tree is not None:
                trees[int(material.node_tree.as_pointer())] = material.node_tree
            prop = material.bl_rna.properties.get('cycles')
            if prop is None or not material.is_property_set('cycles'):
                rows.append({'material': material.name_full, 'stored': False, 'declared': prop is not None})
                continue
            owner_before = storage(material)
            group = material.cycles
            require(type(group) is cls, 'Stored Material.cycles has unexpected exact Python class')
            group_before = storage(group)
            values = {name: plain(getattr(group, name)) for name in FIELDS}
            if group.bl_rna.properties.get('name') is not None:
                values['name'] = plain(group.name)
            row = {'material': material.name_full, 'stored': True, 'exact_class': type(group) is cls,
                'class_module': type(group).__module__, 'rna_identifier': group.bl_rna.identifier,
                'pointer': descriptor(material, prop), 'fixed_type_equals_class_rna': prop.fixed_type == cls.bl_rna,
                'fixed_type_pointer_equals_class_rna': int(prop.fixed_type.as_pointer()) == int(cls.bl_rna.as_pointer()),
                'descriptors': [descriptor(group, field) for field in group.bl_rna.properties], 'values': values,
                'owner_before': owner_before, 'group_before': group_before,
                'group_after': storage(group), 'owner_after': storage(material)}
            require(row['owner_before'] == row['owner_after'] and row['group_before'] == row['group_after'],
                'Cycles diagnostic getter changed storage/set status')
            rows.append(row)
        for world in bpy.data.worlds:
            if world.node_tree is not None:
                trees[int(world.node_tree.as_pointer())] = world.node_tree
        for tree in bpy.data.node_groups:
            if isinstance(tree, bpy.types.ShaderNodeTree):
                trees[int(tree.as_pointer())] = tree
        report['cycles_materials'], report['annotations'] = rows, []
        for tree in trees.values():
            prop, initial = tree.bl_rna.properties.get('annotation'), storage(tree)
            require(prop is not None, 'ShaderNodeTree annotation descriptor missing')
            value = tree.annotation
            metadata = None if value is None else {'python_module': type(value).__module__, 'python_type': type(value).__name__,
                'native_ID': isinstance(value, bpy.types.ID), 'rna_identifier': value.bl_rna.identifier,
                'name': value.name_full if isinstance(value, bpy.types.ID) else None}
            final = storage(tree)
            report['annotations'].append({'tree': tree.name_full, 'descriptor': descriptor(tree, prop),
                'actual': metadata, 'before': initial, 'after': final})
            require(initial == final, 'Annotation getter changed storage/set status')
        report['api_diagnostic_completed'] = True
    finally:
        report['source_context_exact'] = before == context(bpy)
        report['normal_handlers_preserved'] = callbacks == handlers(bpy)
        report['files_after_exact'] = all(value == pin(value['path']) for value in files.values())
        require(report['source_context_exact'] and report['normal_handlers_preserved'] and report['files_after_exact'],
            'Read-only diagnostic cleanup guard failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('snapshot-report', 'snapshot-sha256', 'report'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output = Path(args.report).resolve()
    require(output.parent == HERE and output.suffix == '.json' and not output.exists(), 'Unused direct project JSON required')
    report = {'schema': 'x.current-shader-native-api-diagnostic/1', 'completed': False, 'acceptance': False,
        'no_addon_registration_solver_seek_update_or_save': True,
        'scope': 'Stored Cycles scalar shape and annotation pointer metadata only; not geometry/resource/evaluated shader or full RAM acceptance.'}
    with output.open('x', encoding='utf8') as stream:
        try:
            run(args, report)
            report['completed'] = report.get('api_diagnostic_completed') is True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
