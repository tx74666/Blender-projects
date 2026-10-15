"""Read-only metadata and wrapper ownership checks; no bpy or native."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

import native_unset_cycles_copy_fixture_010 as fixture


class NativeOwner:
    def __init__(self, is_set=False, raw=None):
        self.is_set, self.raw, self.getter_calls = is_set, raw or {}, 0

    def is_property_set(self, name):
        assert name == 'cycles'
        return self.is_set

    @property
    def cycles(self):
        self.getter_calls += 1
        raise AssertionError('Unset Cycles getter must not run')

    @property
    def items(self):
        raise AssertionError('Instance items may be shadowed')


class FakeStruct:
    @staticmethod
    def items(owner):
        return owner.raw.items()


class Tests(unittest.TestCase):
    def bpy(self):
        return SimpleNamespace(types=SimpleNamespace(bpy_struct=FakeStruct, ID=type('ID', (), {})))

    def test_snapshot_never_gets_unset_cycles_or_instance_items(self):
        owner = NativeOwner(False, {'raw': [1, -0.0, {'x': True}]})
        result = fixture.snapshot(owner, self.bpy())
        self.assertEqual(result, {'cycles_set': False,
            'raw': {'raw': [1, {'float_hex': '-0x0.0p+0'}, {'x': True}]}})
        self.assertEqual(owner.getter_calls, 0)
        self.assertFalse(owner.is_set)

    def test_snapshot_reports_real_materialization_or_raw_changes(self):
        owner = NativeOwner()
        before = fixture.snapshot(owner, self.bpy())
        owner.is_set = True
        self.assertNotEqual(before, fixture.snapshot(owner, self.bpy()))
        owner.is_set, owner.raw = False, {'new_backing': {}}
        self.assertNotEqual(before, fixture.snapshot(owner, self.bpy()))

    def test_hook_restore_only_owned_and_does_not_overwrite_foreign(self):
        original, installed, foreign = object(), object(), object()
        module = SimpleNamespace(_remap_rna=installed)
        self.assertTrue(fixture.restore_hook(module, installed, original))
        self.assertIs(module._remap_rna, original)
        module._remap_rna = foreign
        self.assertFalse(fixture.restore_hook(module, installed, original))
        self.assertIs(module._remap_rna, foreign)

    def test_fixture_has_no_artist_input_open_save_register_or_solver(self):
        source = Path(fixture.__file__).read_text(encoding='utf-8')
        tree = ast.parse(source)
        calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse(calls & {'open_mainfile', 'save_as_mainfile', 'save_mainfile', 'register',
            'frame_set', 'defer_runtime', '_calculate_object', 'animation_play'})
        self.assertNotIn('getattr(owner', source)
        self.assertIn('sys.exc_info()[0] is None', source)


if __name__ == '__main__':
    unittest.main()
