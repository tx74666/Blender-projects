"""Pure inventory getter traps only; no native input/report or bpy execution."""
import ast
import types
import unittest

import native_current_shader_inventory_008 as inventory
import test_mesh_cache_shader_witness_007 as fake


class InventoryTests(fake.ShaderTests):
    def test_unknown_native_pointer_and_stored_registered_getters_are_not_invoked(self):
        class Trap(fake.Struct):
            @property
            def unknown(self):
                raise AssertionError('unknown getter invoked')
        for runtime in (False, True):
            field = fake.prop('unknown', 'POINTER', fixed_type=types.SimpleNamespace(identifier='Unknown'))
            field.is_runtime = runtime
            owner = Trap('Known', props=[field])
            reader = inventory.Inventory()
            reader._state(owner, lambda value: value, 'Source')
            self.assertEqual(reader.unsupported['Source.unknown']['getter_invoked'], False)
            self.assertEqual(owner.raw, {})

    def test_supported_getter_mutation_still_rejected_and_unknown_collections_ordinal_not_read(self):
        class Trap(fake.Struct):
            @property
            def unknown(self):
                raise AssertionError('unknown collection getter invoked')
            @property
            def reading(self):
                self.raw['changed'] = 1
                return 2.
        owner = Trap('Known', props=[fake.prop('unknown', 'COLLECTION')])
        reader = inventory.Inventory()
        reader._state(owner, lambda value: value, 'Source')
        self.assertIn('Source.unknown', reader.unsupported)
        owner.bl_rna.properties.append(fake.prop('reading'))
        with self.assertRaisesRegex(RuntimeError, 'getter changed'):
            reader._state(owner, lambda value: value, 'Source')

    def test_entry_has_no_seek_update_manual_solver_save_or_defer_and_not_admission(self):
        source = inventory.Path(inventory.__file__).read_text(encoding='utf-8')
        tree = ast.parse(source)
        calls = [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
        for forbidden in ('frame_set', 'view_layer.update', '_calculate_object', 'defer_runtime', 'save_as_mainfile', 'save_mainfile'):
            self.assertFalse(any(forbidden in name for name in calls), forbidden)
        self.assertIn("'acceptance': False", source)
        self.assertIn('load_ui=False', source)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(InventoryTests(name) for name in InventoryTests.__dict__ if name.startswith('test_'))


if __name__ == '__main__':
    unittest.main()
