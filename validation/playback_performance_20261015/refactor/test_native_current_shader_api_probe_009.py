"""Small diagnostic helpers only; never import native bpy or create evidence."""
import ast
import sys
import types
import unittest
from unittest.mock import patch
import native_current_shader_api_probe_009 as probe


class Tests(unittest.TestCase):
    def test_scalar_descriptor_handles_enum_without_array_attributes(self):
        owner = types.SimpleNamespace(is_property_set=lambda name: name == 'sampling')
        prop = types.SimpleNamespace(identifier='sampling', type='ENUM', is_runtime=True,
            enum_items=[types.SimpleNamespace(identifier='AUTO', value=1)])
        value = probe.descriptor(owner, prop)
        self.assertEqual(value['enum'], [['AUTO', 1]])
        self.assertTrue(value['is_property_set'])
        self.assertFalse(value['is_array'])
        self.assertEqual(value['array_length'], 0)

    def test_plain_and_raw_uses_native_descriptor_and_float_hex(self):
        class Struct:
            def items(self):
                return [('float', -0.), ('flag', True)]
        class ID(Struct):
            pass
        bpy = types.SimpleNamespace(types=types.SimpleNamespace(ID=ID, bpy_struct=Struct))
        with patch.dict(sys.modules, bpy=bpy):
            self.assertEqual(probe.raw(Struct()), {'float': {'float_hex': '-0x0.0p+0'}, 'flag': True})
            self.assertNotEqual(probe.digest(probe.plain(-0.)), probe.digest(probe.plain(0.)))

    def test_actual_frozen_input_and_official_source_pins(self):
        self.assertEqual(probe.pin(probe.CYCLES_PATH)['sha256'], probe.CYCLES_SHA)
        self.assertEqual(probe.pin(probe.HERE/'mesh_cache_current_input_007.py')['sha256'], probe.HELPER_SHA)
        self.assertEqual(probe.pin(probe.HERE/'current_model_save_copy_report_010.json')['sha256'], probe.RECEIPT_SHA)
        source = ast.parse(probe.CYCLES_PATH.read_text(encoding='utf8'))
        cls = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'CyclesMaterialSettings')
        fields = [node for node in cls.body if isinstance(node, ast.AnnAssign)]
        self.assertEqual(tuple(node.target.id for node in fields), probe.FIELDS)
        self.assertFalse({kw.arg for node in fields for kw in node.annotation.keywords}
            & {'get', 'set', 'get_transform', 'set_transform', 'update'})

    def test_no_registration_solver_seek_update_save_or_bpy_import_on_load(self):
        self.assertNotIn('bpy', sys.modules)
        tree = ast.parse(probe.Path(probe.__file__).read_text(encoding='utf8'))
        calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse(calls & {'register', 'register_class', 'frame_set', '_calculate_object',
            'defer_runtime', 'save_as_mainfile', 'save_mainfile'})
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'update' and ast.unparse(node.func.value) not in {'report', 'digest'} for node in ast.walk(tree)))
        self.assertEqual(sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == 'open_mainfile'), 1)
        self.assertIn('load_ui=False', ast.unparse(tree))


if __name__ == '__main__':
    unittest.main()
