"""Paired 0.76.1/current Unity Export recording-layout benchmark.

Run only in a disposable Blender --background --factory-startup process:
  --python-exit-code 1 --python THIS_FILE -- --report ABSOLUTE_NEW_JSON

Creates synthetic data, never opens/saves an artist blend, never exports FBX,
and never starts a Hair simulation. Timings are Python panel work, not actual
mouse-to-screen latency or viewport FPS. Root owns scheduling native execution.
"""

import argparse
import ast
from contextlib import ExitStack, contextmanager
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import traceback
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import zipfile

import bpy

CANONICAL = Path('D:/MyRepository/Blender-addons-by-Randy')
BASELINE = CANONICAL / 'dist/character_designer-0.76.1.zip'
BASELINE_SHA256 = '52fed6e515892bbe84a2d0a1702719b9750d11d0848cfd3bf9c95a640983ca2e'
MODES = ((False, False), (True, False), (False, True), (True, True))
MODE_NAMES = ('collapsed', 'objects', 'materials', 'both')


def require(value, message):
    if not value:
        raise AssertionError(message)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RecordingLayout:
    def __init__(self, records=None):
        self.records = [] if records is None else records

    def row(self, **_kwargs):
        return RecordingLayout(self.records)

    box = column = row

    def separator(self, **_kwargs):
        pass

    def label(self, **kwargs):
        self.records.append(('label', kwargs))

    def prop(self, owner, name, **kwargs):
        require(name in owner.bl_rna.properties, 'Unknown layout RNA property: ' + name)
        self.records.append(('prop', name, kwargs))

    def operator(self, identifier, **kwargs):
        properties = SimpleNamespace()
        self.records.append(('operator', identifier, kwargs, properties))
        return properties


def draw(module):
    layout = RecordingLayout()
    module.CHARACTERDESIGNER_PT_unity_export.draw(SimpleNamespace(layout=layout), bpy.context)
    return layout


@contextmanager
def private_baseline(path):
    """Compile two unregistered modules in memory; share current dependencies."""
    names, modules = [], []
    try:
        with zipfile.ZipFile(path) as archive:
            for leaf in ('unity_export', 'unity_export_ui'):
                name = 'character_designer._foldouts_0761_' + leaf
                require(name not in sys.modules, 'Private baseline namespace is occupied.')
                module = ModuleType(name)
                module.__package__ = 'character_designer'
                member = 'character_designer/' + leaf + '.py'
                module.__file__ = str(path) + '::' + member
                sys.modules[name] = module
                names.append(name)
                modules.append(module)
                exec(compile(archive.read(member), module.__file__, 'exec'), module.__dict__)
        old_export, old_ui = modules
        old_ui._exporter = lambda: old_export
        yield old_export, old_ui
    finally:
        for name in names:
            sys.modules.pop(name, None)


def archive_metadata(path):
    with zipfile.ZipFile(path) as archive:
        source = archive.read('character_designer/__init__.py').decode('utf8')
        tree = ast.parse(source)
        version = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'bl_info'
                                                   for target in node.targets):
                version = list(ast.literal_eval(node.value)['version'])
        require(version == [0, 76, 1], 'The immutable baseline is not Character Designer 0.76.1.')
        leaves = ('unity_export.py', 'unity_export_ui.py', 'character_setup.py', 'ui_constants.py')
        hashes = {leaf: hashlib.sha256(archive.read('character_designer/' + leaf)).hexdigest()
                  for leaf in leaves}
    return {'version': version, 'module_and_shared_dependency_sha256': hashes}


@contextmanager
def synthetic_fixture(character_setup):
    require(bpy.context.window is not None, 'Factory fixture requires the native background Window context.')
    original_scene = bpy.context.window.scene
    kinds = ('objects', 'meshes', 'armatures', 'materials', 'collections', 'scenes')
    original = {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in kinds}
    scene = bpy.data.scenes.new('Unity Export Foldout Fixture')
    bpy.context.window.scene = scene

    def armature(name, count):
        data = bpy.data.armatures.new(name + ' Data')
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        for selected in tuple(bpy.context.selected_objects):
            selected.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        for index in range(count):
            bone = data.edit_bones.new('Bone%04d' % index)
            bone.head, bone.tail = (0, 0, index * .02), (0, 0, index * .02 + .01)
        bpy.ops.object.mode_set(mode='OBJECT')
        return obj

    def mesh(name, rig=None):
        data = bpy.data.meshes.new(name + ' Data')
        data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        data.update()
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        if rig is not None:
            obj.modifiers.new('Character Binding', 'ARMATURE').object = rig
            obj.vertex_groups.new(name='Bone0000').add([0, 1, 2], 1.0, 'REPLACE')
        return obj

    try:
        main, foreign = armature('Foldout Main Rig', 351), armature('Foldout Foreign Rig', 2064)
        bound = [mesh('Bound Mesh %02d' % index, main) for index in range(5)]
        widgets = [mesh('Unrelated Widget %03d' % index) for index in range(64)]
        for index, obj in enumerate(widgets):
            obj['character_designer_fixture_role'] = 'WIDGET'
            obj['fixture_unrelated_metadata'] = index
        for rig in (main, foreign):
            for index, bone in enumerate(rig.pose.bones):
                if index < 240:
                    bone.custom_shape = widgets[index % len(widgets)]
        for index in range(377 - len(bound) - len(widgets)):
            obj = mesh('Unrelated Mesh %03d' % index)
            obj['fixture_unrelated_metadata'] = index
        for index in range(128):
            obj = bpy.data.objects.new('Unrelated Empty %03d' % index, None)
            scene.collection.objects.link(obj)
            obj['fixture_unrelated_metadata'] = index
        materials = [bpy.data.materials.new('Fixture Material %02d' % index) for index in range(64)]
        for obj in bound:
            for material in materials:
                obj.data.materials.append(material)
        setup = character_setup.settings(bpy.context)
        setup.rig, setup.body = main, bound[0]
        config = main.character_designer_unity_export
        config.filename = 'Foldout Fixture'
        config.simple_materials.add().material = materials[0]
        for selected in tuple(bpy.context.selected_objects):
            selected.select_set(False)
        main.select_set(True)
        bpy.context.view_layer.objects.active = main
        bpy.context.view_layer.update()
        yield SimpleNamespace(scene=scene, main=main, foreign=foreign, bound=bound,
                              setup=setup, config=config, materials=materials)
    finally:
        if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.window.scene = original_scene
        for kind in kinds:
            bank = getattr(bpy.data, kind)
            for item in tuple(bank):
                if item.as_pointer() not in original[kind]:
                    bank.remove(item, do_unlink=True)


def pointer(value):
    return None if value is None else (value.bl_rna.identifier, value.as_pointer(), value.name)


def custom(value):
    return [(str(key), repr(value[key])) for key in sorted(value.keys())]


def matrices(value):
    return tuple(tuple(row) for row in value)


def fingerprint(f):
    """Untimed exact native data/pointer/config purity; synthetic inventory only."""
    objects = []
    for obj in sorted(f.scene.objects, key=lambda item: item.name):
        row = [pointer(obj), pointer(obj.data), pointer(obj.parent), matrices(obj.matrix_world),
               obj.rotation_mode, tuple(obj.location), tuple(obj.rotation_euler),
               tuple(obj.rotation_quaternion), tuple(obj.rotation_axis_angle), tuple(obj.scale),
               obj.select_get(), obj.hide_viewport, obj.hide_render, custom(obj),
               [pointer(collection) for collection in obj.users_collection],
               [(modifier.name, modifier.type, modifier.show_viewport, modifier.show_render,
                 pointer(getattr(modifier, 'object', None)), getattr(modifier, 'use_vertex_groups', None),
                 getattr(modifier, 'use_bone_envelopes', None)) for modifier in obj.modifiers]]
        if obj.type == 'MESH':
            row.extend(([(tuple(vertex.co), [(entry.group, entry.weight) for entry in vertex.groups])
                         for vertex in obj.data.vertices],
                        [tuple(edge.vertices) for edge in obj.data.edges],
                        [tuple(face.vertices) for face in obj.data.polygons],
                        [pointer(slot.material) for slot in obj.material_slots], custom(obj.data)))
        elif obj.type == 'ARMATURE':
            row.append([(bone.name, matrices(bone.matrix_local), bone.parent.name if bone.parent else None,
                         bone.use_connect, bone.use_deform, bone.inherit_scale, custom(bone),
                         matrices(obj.pose.bones[bone.name].matrix_basis),
                         pointer(obj.pose.bones[bone.name].custom_shape), custom(obj.pose.bones[bone.name]))
                        for bone in obj.data.bones])
        objects.append(row)
    config = {prop.identifier: (getattr(f.config, prop.identifier), f.config.is_property_set(prop.identifier))
              for prop in f.config.bl_rna.properties
              if prop.type in {'STRING', 'BOOLEAN', 'INT', 'FLOAT', 'ENUM'} and prop.identifier != 'rna_type'}
    config['raw'] = custom(f.config)
    config['extras'] = [(pointer(entry.object), entry.enabled, custom(entry)) for entry in f.config.extras]
    config['simple_materials'] = [(pointer(entry.material), custom(entry)) for entry in f.config.simple_materials]
    setup = {prop.identifier: (getattr(f.setup, prop.identifier), f.setup.is_property_set(prop.identifier))
             for prop in f.setup.bl_rna.properties
             if prop.type in {'STRING', 'BOOLEAN', 'INT', 'FLOAT', 'ENUM'} and prop.identifier != 'rna_type'}
    proof = (objects, config, setup, custom(f.setup), pointer(f.setup.rig), pointer(f.setup.body),
             [(pointer(item.object), item.role, custom(item)) for item in f.setup.assets],
             f.scene.frame_current, f.scene.frame_subframe, bpy.context.mode,
             pointer(bpy.context.view_layer.objects.active), bpy.data.filepath,
             [(pointer(item), tuple(item.diffuse_color), item.use_nodes, custom(item)) for item in f.materials],
             {kind: sorted((item.as_pointer(), item.name) for item in getattr(bpy.data, kind))
              for kind in ('objects', 'meshes', 'armatures', 'materials', 'collections', 'scenes', 'actions', 'texts')})
    return hashlib.sha256(repr(proof).encode('utf8')).hexdigest()


def layout_proof(layout, current, f, mode):
    expected_objects = sorted([obj.name for obj in f.bound] + [f.main.name])
    text = [record[2].get('text', '') for record in layout.records if record[0] in {'prop', 'operator'}]
    require('Objects · 5 Meshes · 1 Armatures' in text, 'Incorrect fresh object summary: ' + repr(text))
    require('Use Simplified Materials · 1' in text, 'Incorrect selected-material summary.')
    labels = [record[1] for record in layout.records if record[0] == 'label']
    shown_objects = sorted(item.get('text', '') for item in labels if item.get('icon') in {'MESH_DATA', 'ARMATURE_DATA'})
    require(shown_objects == (expected_objects if mode[0] else []), 'Incorrect expanded object inventory.')
    material_buttons = [record for record in layout.records if record[0] == 'operator'
                        and record[1] == 'character_designer.unity_simple_material']
    if current:
        selected = [item['text'] for item in labels if item.get('icon') == 'MATERIAL']
        require(selected == ([f.materials[0].name] if mode[1] else []), 'Current body must show only selected materials.')
        require(len(material_buttons) == (1 if mode[1] else 0), 'Unexpected current material body buttons.')
        require(all(button[3].enabled is False for button in material_buttons), 'Use Original must remove only this saved choice.')
    else:
        toggles = [button for button in material_buttons if button[2].get('icon', '').startswith('CHECKBOX_')]
        selected = [button[3].material_name for button in toggles if button[2].get('icon') == 'CHECKBOX_HLT']
        require(selected == ([f.materials[0].name] if mode[1] else []), 'Baseline selected choice differs.')
        require(len(toggles) == (len(f.materials) if mode[1] else 0), 'Baseline used-material inventory differs.')
    return {'object_header': 'Objects · 5 Meshes · 1 Armatures', 'expanded_objects': shown_objects,
            'selected_material_labels': selected, 'material_body_buttons': len(material_buttons)}


def measure(backend, panel, f, mode, current, guards):
    f.config.show_objects, f.config.show_materials, f.config.show_warnings = mode[0], mode[1], False
    before = fingerprint(f)
    calls, captured = {}, []
    with ExitStack() as stack:
        def instrument(owner, name):
            original = getattr(owner, name)
            calls[name] = []
            def wrapper(*args, **kwargs):
                began = time.perf_counter()
                try:
                    result = original(*args, **kwargs)
                    if name == 'collect_character':
                        captured.append({'objects': [obj.name for obj in result['objects']], 'warnings': result['warnings']})
                    return result
                finally:
                    calls[name].append((time.perf_counter() - began) * 1000)
            stack.enter_context(patch.object(owner, name, wrapper))
        for name in ('_helpers', '_character_armatures', '_collection_scope', 'collect_character'):
            instrument(backend, name)
        instrument(panel, '_material_choices')
        stack.enter_context(patch.object(backend, '_capture_hair_motion', side_effect=AssertionError('Panel captured strict Hair proof')))
        for owner, name in guards:
            stack.enter_context(patch.object(owner, name, side_effect=AssertionError('Panel entered Hair native/backend validation: ' + name)))
        started = time.perf_counter()
        layout = draw(panel)
        elapsed = (time.perf_counter() - started) * 1000
    require(fingerprint(f) == before, 'Draw changed native data, pointer, configuration, context or inventory.')
    expected = sorted([obj.name for obj in f.bound] + [f.main.name])
    require(len(captured) == 1 and sorted(captured[0]['objects']) == expected and captured[0]['warnings'] == [],
            'Collection result differs from the explicit fixture bindings.')
    for name in ('_helpers', '_character_armatures', '_collection_scope', 'collect_character'):
        require(len(calls[name]) == 1, 'Expected one fresh inspection per draw: ' + name)
    require(len(calls['_material_choices']) == (0 if current else int(mode[1])), 'Unexpected material-slot traversal.')
    return {'elapsed_ms': elapsed, 'inclusive_functions': {name: {'calls': len(values), 'milliseconds': sum(values)}
                                                           for name, values in calls.items()},
            'raw_pointer_config_purity': True, 'fingerprint_sha256': before,
            'collection': captured[0], 'layout': layout_proof(layout, current, f, mode),
            'strict_hair_or_backend_calls': 0}


def run(args):
    require(bpy.app.background and not bpy.data.filepath, 'Only --background --factory-startup without a blend input is allowed.')
    require(args.report.is_absolute() and not args.report.exists(), 'Supply a new absolute report path; reports are never overwritten.')
    require(file_hash(BASELINE) == BASELINE_SHA256, 'The frozen 0.76.1 release archive changed.')
    require('character_designer' not in sys.modules, 'A preloaded add-on would invalidate the canonical source comparison.')
    sys.path.insert(0, str(CANONICAL / 'addons'))
    import character_designer
    from character_designer import character_setup, unity_export, unity_export_ui
    from character_designer import hair_strand_registry, hair_motion_profiles, hair_wiggle_adapter
    require(Path(character_designer.__file__).resolve() == (CANONICAL / 'addons/character_designer/__init__.py').resolve(),
            'Character Designer did not load from canonical source.')
    leaves = ('unity_export.py', 'unity_export_ui.py', 'character_setup.py', 'ui_constants.py')
    report = {'ok': False, 'runtime': bpy.app.version_string, 'baseline_zip': str(BASELINE),
              'baseline_sha256': BASELINE_SHA256, 'baseline': archive_metadata(BASELINE),
              'current_version': list(character_designer.bl_info['version']),
              'current_sha256': {leaf: file_hash(CANONICAL / 'addons/character_designer' / leaf) for leaf in leaves},
              'shared_dependencies': 'Both unregistered baseline modules reuse the same registered canonical character_setup/ui_constants.',
              'fixture': {'total_bones': 2415, 'main_bones': 351, 'foreign_bones': 2064, 'meshes': 377,
                          'bound_meshes': 5, 'widget_meshes_in_total': 64, 'unrelated_empty_objects': 128,
                          'scene_objects': 507, 'custom_shapes_per_rig': 240, 'distinct_materials': 64,
                          'bound_material_slots': 320, 'chosen_materials': 1},
              'samples_per_condition': 5, 'warmups_per_condition': 1, 'conditions': {},
              'timing_scope': 'Real bpy synthetic scene and RecordingLayout; wrapper-inclusive Python draw time only.',
              'limitations': ['Not rendered UI latency, mouse response, viewport FPS, memory or whole FBX timing.',
                              'Synthetic triangles/material slot density and foreign rig are explicit scaling conditions, not the artist model.',
                              'Inclusive profiler function times overlap and must not be added.',
                              'Registration, data generation, purity fingerprints and validation are outside the timed region.',
                              'No artist input, .blend save, preview, worker, renderer or Unity operation. Old 0.69.0 benchmarks are not combined.']}
    registered = False
    try:
        character_designer.register()
        registered = True
        guards = ((hair_strand_registry, 'read'), (hair_motion_profiles, 'effective_all'), (hair_wiggle_adapter, '_backend'))
        with synthetic_fixture(character_setup) as f, private_baseline(BASELINE) as (old_backend, old_ui):
            for name, mode in zip(MODE_NAMES, MODES):
                entry = {'warmups': {}, 'pairs': [], 'baseline_samples_ms': [], 'current_samples_ms': []}
                entry['warmups']['baseline'] = measure(old_backend, old_ui, f, mode, False, guards)
                entry['warmups']['current'] = measure(unity_export, unity_export_ui, f, mode, True, guards)
                for index in range(5):
                    order = ('baseline', 'current') if index % 2 == 0 else ('current', 'baseline')
                    pair = {'order': list(order)}
                    for which in order:
                        pair[which] = measure(unity_export if which == 'current' else old_backend,
                                              unity_export_ui if which == 'current' else old_ui,
                                              f, mode, which == 'current', guards)
                        entry[which + '_samples_ms'].append(pair[which]['elapsed_ms'])
                    entry['pairs'].append(pair)
                entry['baseline_median_ms'] = statistics.median(entry['baseline_samples_ms'])
                entry['current_median_ms'] = statistics.median(entry['current_samples_ms'])
                entry['paired_differences_current_minus_baseline_ms'] = [pair['current']['elapsed_ms'] - pair['baseline']['elapsed_ms']
                                                                        for pair in entry['pairs']]
                report['conditions'][name] = entry
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        try:
            if registered:
                character_designer.unregister()
        except Exception:
            report['ok'] = False
            report['cleanup_error'] = traceback.format_exc()
            raise
        finally:
            report['baseline_archive_unchanged'] = file_hash(BASELINE) == BASELINE_SHA256
            report['current_sources_unchanged'] = all(file_hash(CANONICAL / 'addons/character_designer' / leaf) == expected
                                                     for leaf, expected in report['current_sha256'].items())
            report['ok'] = report['ok'] and report['baseline_archive_unchanged'] and report['current_sources_unchanged']
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open('x', encoding='utf8') as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
            print('UNITY_EXPORT_FOLDOUT_BENCHMARK', json.dumps({'ok': report['ok'], 'report': str(args.report)}), flush=True)
    require(report['ok'], 'Benchmark final cleanup/source preservation failed; inspect the owned report.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    arguments = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    run(arguments)
