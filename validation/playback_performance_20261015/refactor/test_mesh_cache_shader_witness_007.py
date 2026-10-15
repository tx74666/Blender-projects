"""Pure fake-native tests only; no bpy/native/artist or PASS receipt emitted."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import mesh_cache_shader_witness_007 as shader


class Props(list):
    def __getitem__(self, key):
        return next(item for item in self if item.identifier == key) if isinstance(key, str) else super().__getitem__(key)


def prop(name, kind='FLOAT', **kw):
    return types.SimpleNamespace(identifier=name, type=kind, is_runtime=False, **kw)


class Struct:
    def __init__(self, kind, fields=None, props=()):
        self.bl_rna = types.SimpleNamespace(identifier=kind, is_runtime=False, properties=Props(props))
        self.raw = {}
        self.set_bits = {}
        self.__dict__.update(fields or {})

    @staticmethod
    def items(owner):
        return tuple(owner.raw.items())

    def is_property_set(self, name):
        return self.set_bits.get(name, True)

    def as_pointer(self):
        return id(self)


class ID(Struct):
    def __init__(self, kind, name, fields=None, props=()):
        super().__init__(kind, fields, props)
        self.name_full = name
        self.library = None
        self.is_evaluated = False
        self.is_embedded_data = False
        self.animation_data = None

    def evaluated_get(self, depsgraph):
        return getattr(self, 'evaluated', self)


class Material(ID):
    pass


class World(ID):
    pass


class Image(ID):
    pass


class ShaderNodeTree(ID):
    pass


class ShaderNodeValue(Struct):
    pass


class Object(ID):
    pass


class Action(ID):
    pass


def scene_fixture():
    output = Struct('NodeSocketFloat', {'identifier': 'Value', 'default_value': 0.25},
        (prop('identifier', 'STRING'), prop('default_value')))
    node = ShaderNodeValue('ShaderNodeValue', {'name': 'Value', 'outputs': [output], 'inputs': []},
        (prop('outputs', 'COLLECTION'), prop('inputs', 'COLLECTION')))
    tree = ShaderNodeTree('ShaderNodeTree', 'Shader', {'nodes': [node], 'links': []},
        (prop('nodes', 'COLLECTION'), prop('links', 'COLLECTION')))
    material = Material('Material', 'M', {'node_tree': tree, 'is_grease_pencil': False, 'roughness': 0.5},
        (prop('node_tree', 'POINTER'), prop('roughness')))
    obj = Object('Object', 'Body', {'type': 'MESH', 'data': types.SimpleNamespace(materials=[material]),
        'material_slots': [types.SimpleNamespace(link='DATA', material=material)]})
    return types.SimpleNamespace(objects=[obj], world=None), obj, material, node, output


class ShaderTests(unittest.TestCase):
    def setUp(self):
        self.bpy = types.SimpleNamespace(types=types.SimpleNamespace(bpy_struct=Struct, ID=ID,
            Material=Material, World=World, Image=Image, ShaderNodeTree=ShaderNodeTree,
            ShaderNodeValue=ShaderNodeValue), app=types.SimpleNamespace(version=(5, 2, 0)),
            path=types.SimpleNamespace(abspath=lambda value, library=None: value))
        self.patcher = patch.dict(sys.modules, bpy=self.bpy)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_parameter_numeric_and_link_binding_changes_are_detected(self):
        scene, obj, material, node, output = scene_fixture()
        witness = shader.ShaderWitness()
        before = witness.capture(scene)
        output.default_value = 0.5
        self.assertNotEqual(before['sha256'], witness.capture(scene)['sha256'])
        output.default_value = 0.25
        self.assertEqual(before['sha256'], witness.capture(scene)['sha256'])
        obj.material_slots[0].link = 'OBJECT'
        self.assertNotEqual(before['sha256'], witness.capture(scene)['sha256'])
        self.assertNotEqual(shader._plain(-0.0, lambda value: value), shader._plain(0.0, lambda value: value))

    def test_explicit_native_and_serialized_ID_routes_preserve_values(self):
        source, source_obj, source_mat, source_node, source_output = scene_fixture()
        clone, obj, mat, node, output = scene_fixture()
        obj.name_full, mat.name_full, mat.node_tree.name_full = 'Body copy', 'M copy', 'Shader copy'
        mapping = {source_obj: obj, source_mat: mat, source_mat.node_tree: mat.node_tree}
        witness = shader.ShaderWitness()
        golden = witness.capture(source)['sha256']
        self.assertNotEqual(golden, witness.capture(clone)['sha256'])
        self.assertEqual(golden, witness.capture(clone, {target: source for source, target in mapping.items()})['sha256'])
        routes = json.loads(json.dumps(shader.serialize_id_mapping(mapping)))
        self.assertEqual(golden, witness.capture(clone, routes)['sha256'])
        output.default_value = 0.25001
        self.assertNotEqual(golden, witness.capture(clone, routes)['sha256'])

    def test_unknown_pointer_and_runtime_callback_rejected_before_get(self):
        class Trap(Struct):
            @property
            def unknown(self):
                raise AssertionError('must not invoke source getter')
        witness = shader.ShaderWitness()
        target = Trap('Known', props=[prop('unknown', 'POINTER')])
        with self.assertRaisesRegex(RuntimeError, 'Unsupported shader content'):
            witness._state(target, lambda value: value, 'path')
        target.bl_rna.properties[0].is_runtime = True
        with self.assertRaisesRegex(RuntimeError, 'registered shader field'):
            witness._state(target, lambda value: value, 'path')

    def test_unset_registered_pointer_metadata_only_and_stored_extension_rejected(self):
        class Trap(Struct):
            @property
            def cycles(self):
                raise AssertionError('unset extension getter must never run')
        field = prop('cycles', 'POINTER', fixed_type=types.SimpleNamespace(identifier='CyclesMaterialSettings'))
        field.is_runtime = True
        target = Trap('Material', props=[field])
        target.set_bits['cycles'] = False
        witness = shader.ShaderWitness()
        state = witness._state(target, lambda value: value, 'Material')
        self.assertEqual(state['fields']['cycles']['scope'], 'unset-registered-pointer-no-getter')
        self.assertFalse(target.set_bits['cycles'])
        self.assertEqual(target.raw, {})
        target.set_bits['cycles'] = True
        with self.assertRaisesRegex(RuntimeError, 'Unsupported stored/registered'):
            witness._state(target, lambda value: value, 'Material')

    def test_raw_and_setbit_mutation_fail_closed(self):
        class Trap(Struct):
            @property
            def reading(self):
                if self.change_raw:
                    self.raw['new'] = 2
                else:
                    self.set_bits['reading'] = False
                return 1.
        witness = shader.ShaderWitness()
        for raw in (True, False):
            target = Trap('Known', {'change_raw': raw}, [prop('reading')])
            with self.assertRaisesRegex(RuntimeError, 'getter changed'):
                witness._state(target, lambda value: value, 'path')

    def test_enum_without_array_flag_and_nested_ramp_mutation(self):
        enum = prop('interpolation', 'ENUM', enum_items=[types.SimpleNamespace(identifier='LINEAR', value=0)])
        point = Struct('ColorRampElement', {'position': 0.2}, [prop('position')])
        ramp = Struct('ColorRamp', {'interpolation': 'LINEAR', 'elements': [point]},
            [enum, prop('elements', 'COLLECTION')])
        witness = shader.ShaderWitness()
        before = shader.digest(witness._nested(ramp, lambda value: value, 'ramp'))
        point.position = 0.3
        self.assertNotEqual(before, shader.digest(witness._nested(ramp, lambda value: value, 'ramp')))

    def test_evaluated_parameter_read_only_and_no_pointer_alias(self):
        source, obj, material, node, output = scene_fixture()
        other, _, eval_mat, _, eval_output = scene_fixture()
        material.evaluated = eval_mat
        eval_mat.is_evaluated, eval_mat.original = True, material
        eval_mat.node_tree.is_evaluated, eval_mat.node_tree.original = True, material.node_tree
        eval_output.default_value = 0.75
        witness = shader.ShaderWitness()
        stored = witness.capture(source)
        evaluated = witness.capture(source, depsgraph=object())
        self.assertNotEqual(stored['sha256'], evaluated['sha256'])
        self.assertEqual(output.default_value, 0.25)
        self.assertTrue(evaluated['scope']['evaluated_parameters'])

    def test_external_and_packed_resource_mutations_and_no_rehash_on_capture(self):
        witness = shader.ShaderWitness()
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'texture.bin'
            file.write_bytes(b'old')
            image = Image('Image', 'Texture', {'source': 'FILE', 'is_dirty': False, 'is_multiview': False,
                'filepath': str(file), 'packed_files': [],
                'colorspace_settings': Struct('ColorManagedInputColorspaceSettings', {'name': 'sRGB'}, [prop('name', 'STRING')])})
            identity = witness._routes(None)
            first = witness._image(image, identity)
            with patch.object(witness, '_file', side_effect=AssertionError('hot disk hash')):
                self.assertEqual(first, witness._image(image, identity))
            image.colorspace_settings.name = 'Non-Color'
            self.assertNotEqual(shader.digest(first), shader.digest(witness._image(image, identity)))
            image.colorspace_settings.name = 'sRGB'
            self.assertTrue(witness.verify_resources())
            file.write_bytes(b'new')
            with self.assertRaisesRegex(RuntimeError, 'resource bytes/path changed'):
                witness.verify_resources()
            packed = types.SimpleNamespace(filepath=str(file), packed_file=types.SimpleNamespace(data=b'pixels'))
            image.packed_files = [packed]
            witness = shader.ShaderWitness()
            witness._image(image, witness._routes(None))
            packed.packed_file.data = b'other'
            with self.assertRaisesRegex(RuntimeError, 'resource bytes/path changed'):
                witness.verify_resources()

    def test_unknown_custom_node_and_resource_mode_fail_closed(self):
        scene, _, _, node, _ = scene_fixture()
        node.bl_rna.identifier = 'UserNode'
        with self.assertRaisesRegex(RuntimeError, 'Unsupported/custom shader node'):
            shader.ShaderWitness().capture(scene)
        image = Image('Image', 'Movie', {'source': 'MOVIE'})
        with self.assertRaisesRegex(RuntimeError, 'single-file'):
            shader.ShaderWitness()._image(image, lambda value: value)

    def test_duplicate_routes_and_nonfinite_parameters_fail_closed(self):
        scene, obj, material, node, output = scene_fixture()
        witness = shader.ShaderWitness()
        with self.assertRaisesRegex(RuntimeError, 'Duplicate serialized'):
            witness.capture(scene, [{'target': ['same'], 'source': ['A']}, {'target': ['same'], 'source': ['B']}])
        with self.assertRaisesRegex(RuntimeError, 'Non-injective'):
            witness.capture(scene, [{'target': ['A'], 'source': ['same']}, {'target': ['B'], 'source': ['same']}])
        output.default_value = float('nan')
        with self.assertRaisesRegex(RuntimeError, 'Nonfinite'):
            witness.capture(scene)

    def test_animation_function_globals_and_original_portable_module_unchanged(self):
        scene, _, material, _, _ = scene_fixture()
        witness = shader.ShaderWitness()
        identity = witness._routes(None)
        functions = {name: value for name, value in vars(witness.portable).items() if isinstance(value, types.FunctionType)}
        before = {name: value.__globals__ for name, value in functions.items()}
        self.assertEqual(witness._animation(material, identity), (None, ()))
        self.assertEqual(functions, {name: getattr(witness.portable, name) for name in functions})
        self.assertTrue(all(getattr(witness.portable, name).__globals__ is env for name, env in before.items()))

    def test_copied_action_ID_name_routes_but_curve_values_and_layer_names_do_not(self):
        def fixture(name):
            point = Struct('Keyframe', {'co': (1., 0.25)}, [prop('co')])
            curve = Struct('FCurve', {'driver': None, 'group': None, 'keyframe_points': [point],
                'sampled_points': [], 'modifiers': []})
            bag = Struct('ActionChannelbag', {'slot_handle': 1, 'groups': [], 'fcurves': [curve]})
            strip = Struct('ActionKeyframeStrip', {'channelbags': [bag]})
            layer = Struct('ActionLayer', {'name': 'Layer', 'strips': [strip]}, [prop('name', 'STRING')])
            action = Action('Action', name, {'name': name, 'is_action_legacy': False, 'slots': [], 'layers': [layer], 'pose_markers': []},
                [prop('name', 'STRING'), prop('name_full', 'STRING')])
            ad = Struct('AnimData', {'use_tweak_mode': False, 'action_tweak_storage': None, 'action': action,
                'action_slot': None, 'drivers': [], 'nla_tracks': []})
            owner = Material('Material', 'M')
            owner.animation_data = ad
            return owner, action, point, layer
        source, source_action, _, _ = fixture('Shader Action')
        target, target_action, point, layer = fixture('Shader Action copy')
        witness = shader.ShaderWitness()
        golden = shader.digest(witness._animation(source, witness._routes(None)))
        routes = witness._routes({target_action: source_action})
        self.assertEqual(golden, shader.digest(witness._animation(target, routes)))
        point.co = (1., 0.5)
        self.assertNotEqual(golden, shader.digest(witness._animation(target, routes)))
        point.co = (1., 0.25)
        layer.name = 'Different Layer'
        self.assertNotEqual(golden, shader.digest(witness._animation(target, routes)))


if __name__ == '__main__':
    unittest.main()
