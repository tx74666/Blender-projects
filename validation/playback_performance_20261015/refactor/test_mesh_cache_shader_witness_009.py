"""Pure009 scalar/provenance/annotation traps plus retained007/008 guards."""
import ast
import sys
import types
import unittest
from unittest.mock import patch

import mesh_cache_shader_witness_009 as shader
import test_mesh_cache_shader_witness_007 as old
import test_mesh_cache_shader_witness_008 as panel


class RetainedTests(old.ShaderTests):
    def setUp(self):
        super().setUp()
        route = patch.object(old, 'shader', shader)
        route.start()
        self.addCleanup(route.stop)


class RetainedPanelTests(panel.PanelTests):
    def setUp(self):
        super().setUp()
        route = patch.object(panel, 'shader', shader)
        route.start()
        self.addCleanup(route.stop)


class CyclesTests(old.ShaderTests):
    def setUp(self):
        super().setUp()
        self.bpy.types.NodeTree = old.ShaderNodeTree
        class PropertyGroup(old.Struct):
            pass
        self.bpy.types.PropertyGroup = PropertyGroup
        class CyclesMaterialSettings(PropertyGroup):
            def __getattribute__(self, name):
                if name == 'unknown_pointer':
                    raise AssertionError('unsupported registered getter invoked')
                return super().__getattribute__(name)
        CyclesMaterialSettings.__module__ = 'cycles.properties'
        source = ast.parse(shader.CYCLES_PATH.read_text(encoding='utf-8'))
        cls_ast = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'CyclesMaterialSettings')
        CyclesMaterialSettings.__annotations__ = {node.target.id: ast.unparse(node.annotation)
            for node in cls_ast.body if isinstance(node, ast.AnnAssign)}
        fields = [old.prop('name', 'STRING')]
        for name, (kind, _) in shader.FIELDS.items():
            field = old.prop(name, kind)
            field.is_runtime = True
            if kind == 'ENUM':
                field.enum_items = [types.SimpleNamespace(identifier='AUTO', value=0), types.SimpleNamespace(identifier='LINEAR', value=1)]
            fields.append(field)
        rna = types.SimpleNamespace(identifier='CyclesMaterialSettings', is_runtime=True, properties=old.Props(fields))
        rna.as_pointer = lambda: id(rna)
        CyclesMaterialSettings.bl_rna = rna
        module = types.ModuleType('cycles.properties')
        module.__file__ = str(shader.CYCLES_PATH)
        module.CyclesMaterialSettings = CyclesMaterialSettings
        self.cls, self.module = CyclesMaterialSettings, module
        module_patch = patch.dict(sys.modules, {'cycles.properties': module})
        module_patch.start()
        self.addCleanup(module_patch.stop)

    def fixture(self):
        scene, _, material, _, _ = old.scene_fixture()
        group = self.cls('CyclesMaterialSettings', {'name': '', 'emission_sampling': 'AUTO',
            'use_bump_map_correction': True, 'volume_sampling': 'AUTO', 'volume_interpolation': 'LINEAR', 'volume_step_rate': 1.0})
        group.bl_rna = self.cls.bl_rna
        group.set_bits['name'] = False
        material.cycles = group
        field = old.prop('cycles', 'POINTER', fixed_type=self.cls.bl_rna)
        field.is_runtime = True
        material.bl_rna.properties.append(field)
        return scene, material, group, field

    def test_official_str_annotation_and_all_scalar_data_preserved(self):
        scene, material, group, _ = self.fixture()
        witness = shader.ShaderWitness()
        golden = witness.capture(scene)
        self.assertTrue(any(row['identity'][0] == 'code-provenance' for row in golden['resources']))
        group.volume_step_rate = 0.75
        self.assertNotEqual(golden['sha256'], witness.capture(scene)['sha256'])
        group.volume_step_rate = 1.0
        group.name = 'named'
        self.assertNotEqual(golden['sha256'], witness.capture(scene)['sha256'])
        group.name = ''
        self.assertEqual(golden, witness.capture(scene))

    def test_class_or_live_annotation_change_rejected_before_pointer_getter(self):
        scene, material, _, _ = self.fixture()
        self.cls.__annotations__['emission_sampling'] = "EnumProperty(get=unsafe_getter)"
        with patch.object(old.Material, 'cycles', property(lambda self: (_ for _ in ()).throw(AssertionError('Source pointer getter ran'))), create=True):
            with self.assertRaisesRegex(RuntimeError, 'Live Cycles annotations'):
                shader.ShaderWitness().capture(scene)

    def test_unknown_runtime_RNA_name_override_and_complex_field_rejected(self):
        scene, _, group, _ = self.fixture()
        group.bl_rna.properties[0].is_runtime = True
        with self.assertRaisesRegex(RuntimeError, 'runtime override'):
            shader.ShaderWitness().capture(scene)
        group.bl_rna.properties[0].is_runtime = False
        group.bl_rna.properties.append(old.prop('unknown_pointer', 'POINTER'))
        with self.assertRaisesRegex(RuntimeError, 'Unexpected Cycles RNA fields'):
            shader.ShaderWitness().capture(scene)

    def test_collective_outer_set_bit_guard_covers_late_cycles_pointer_getter(self):
        scene, material, group, _ = self.fixture()
        def getter(owner):
            owner.set_bits['roughness'] = False
            return group
        with patch.object(old.Material, 'cycles', property(getter), create=True):
            with self.assertRaisesRegex(RuntimeError, 'pointer getter changed'):
                shader.ShaderWitness().capture(scene)

    def test_source_file_is_read_initially_and_rechecked_only_on_verify(self):
        scene, _, _, _ = self.fixture()
        witness = shader.ShaderWitness()
        witness.capture(scene)
        with patch.object(witness, '_file', side_effect=AssertionError('per-frame code hash')):
            witness.capture(scene)
        with patch.object(witness, '_file', wraps=witness._file) as reader:
            self.assertTrue(witness.verify_resources())
            self.assertEqual(reader.call_count, 1)

    def test_unset_cycles_never_reads_pointer_or_requires_loaded_class(self):
        scene, material, _, _ = self.fixture()
        material.set_bits['cycles'] = False
        with patch.dict(sys.modules, {'cycles.properties': None}):
            with patch.object(old.Material, 'cycles', property(lambda self: (_ for _ in ()).throw(AssertionError('unset getter ran'))), create=True):
                value = shader.ShaderWitness().capture(scene)
        self.assertFalse(any(row['identity'][0] == 'code-provenance' for row in value['resources']))

    def test_annotation_only_native_null_is_supported(self):
        scene, _, _, _, _ = old.scene_fixture()
        tree = scene.objects[0].data.materials[0].node_tree
        tree.bl_rna.properties.append(old.prop('annotation', 'POINTER', fixed_type=types.SimpleNamespace(identifier='Annotation', is_runtime=False)))
        tree.annotation = None
        witness = shader.ShaderWitness()
        witness.capture(scene)
        tree.annotation = old.ID('Annotation', 'Notes')
        with self.assertRaisesRegex(RuntimeError, 'Non-null annotation'):
            witness.capture(scene)


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(RetainedTests)
    suite.addTests(RetainedPanelTests(name) for name in panel.PanelTests.__dict__ if name.startswith('test_'))
    suite.addTests(CyclesTests(name) for name in CyclesTests.__dict__ if name.startswith('test_'))
    return suite


if __name__ == '__main__':
    unittest.main()
