"""Pure008 delta plus all007 gates; no Blender or evidence receipt creation."""
import types
import unittest
from unittest.mock import patch

import mesh_cache_shader_witness_008 as shader
import test_mesh_cache_shader_witness_007 as old


class RetainedTests(old.ShaderTests):
    def setUp(self):
        super().setUp()
        self.route = patch.object(old, 'shader', shader)
        self.route.start()
        self.addCleanup(self.route.stop)


class NodePanelState(old.Struct):
    def __getattribute__(self, name):
        if name == 'unknown_pointer':
            raise AssertionError('unsupported pointer getter ran')
        return super().__getattribute__(name)


class PanelTests(old.ShaderTests):
    # Only the delta tests are inherited here; the twelve old cases run once
    # through RetainedTests above.
    def setUp(self):
        super().setUp()
        self.bpy.types.Node = old.ShaderNodeValue
        self.bpy.types.NodePanelState = NodePanelState

    def panel_node(self):
        scene, _, _, node, _ = old.scene_fixture()
        field = old.prop('panel_states', 'COLLECTION', fixed_type=types.SimpleNamespace(identifier='NodePanelState', is_runtime=False))
        node.bl_rna.properties.append(field)
        node.panel_states = [NodePanelState('NodePanelState', {'identifier': 7, 'is_collapsed': value},
            [old.prop('identifier', 'INT'), old.prop('is_collapsed', 'BOOLEAN')]) for value in (False, True)]
        return scene, node, field

    def test_native_panel_collection_ordinal_empty_and_all_scalar_changes(self):
        scene, node, field = self.panel_node()
        witness = shader.ShaderWitness()
        golden = witness.capture(scene)['sha256']
        node.panel_states.reverse()
        self.assertNotEqual(golden, witness.capture(scene)['sha256'])
        node.panel_states.reverse()
        node.panel_states[0].identifier = 8
        self.assertNotEqual(golden, witness.capture(scene)['sha256'])
        node.panel_states[0].identifier = 7
        self.assertEqual(golden, witness.capture(scene)['sha256'])
        node.panel_states = []
        self.assertNotEqual(golden, witness.capture(scene)['sha256'])

    def test_unknown_panel_declaration_and_non_native_row_fail_closed(self):
        scene, node, field = self.panel_node()
        field.fixed_type.identifier = 'UserPanel'
        with self.assertRaisesRegex(RuntimeError, 'Unknown node panel collection declaration'):
            shader.ShaderWitness().capture(scene)
        field.fixed_type.identifier = 'NodePanelState'
        node.panel_states[0] = old.Struct('NodePanelState')
        with self.assertRaisesRegex(RuntimeError, 'Unknown native node panel row'):
            shader.ShaderWitness().capture(scene)

    def test_panel_unknown_pointer_is_not_read_and_old_source_stays_unchanged(self):
        scene, node, _ = self.panel_node()
        node.panel_states[0].bl_rna.properties.append(old.prop('unknown_pointer', 'POINTER'))
        with self.assertRaisesRegex(RuntimeError, 'Unsupported shader content'):
            shader.ShaderWitness().capture(scene)
        self.assertEqual(shader.base.__file__, str(shader.BASE_PATH))
        self.assertEqual(shader.hashlib.sha256(shader.BASE_PATH.read_bytes()).hexdigest(), shader.BASE_SHA)
        self.assertIsNot(shader.ShaderWitness, shader.base.ShaderWitness)


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(RetainedTests)
    delta = unittest.TestSuite(PanelTests(name) for name in PanelTests.__dict__ if name.startswith('test_'))
    suite.addTests(delta)
    return suite


if __name__ == '__main__':
    unittest.main()
