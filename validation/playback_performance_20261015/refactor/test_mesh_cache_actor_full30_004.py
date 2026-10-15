"""Pure adapter tests; no bpy, scene, Native process or accepted receipt emitted."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import mesh_cache_actor_full30_004 as adapter


def receipt():
    fields = adapter.witness._extension.KEYFRAME_FIELDS
    result = {'schema': 'x.native-keyframe-bulk-factory/1', 'completed': True, 'blender': '5.2.0',
        'cleanup_errors': [], 'field_checks': dict.fromkeys(fields, True),
        'enum_api_checks': {name: True for name, (kind, width) in fields.items() if kind == 'ENUM'},
        'mutation_traps': dict.fromkeys(('co_and_handle', 'enum', 'add_key', 'remove_key',
                                       'native_custom_storage_unsupported'), True),
        'old_point_state_sha256_before_after': ['a'*64, 'a'*64],
        'witness_sources': adapter.witness.witness_dependency_pins(),
        'scripts': {name: adapter.base.pin(adapter.HERE/name) for name in (
            'native_keyframe_bulk_factory_008.py', 'native_validation_support_v9.py',
            'native_source_reference_witness_v9.py', 'native_source_reference_witness_v7.py')},
        'factory_override': {key: adapter.base.pin(adapter.HERE/name) for key, name in (
            ('wrapper', 'native_keyframe_bulk_factory_009.py'), ('unchanged_factory', 'native_keyframe_bulk_factory_008.py'),
            ('bulk', 'native_source_reference_witness_v9.py'), ('support', 'native_validation_support_v9.py'))}}
    result.update(dict.fromkeys(adapter.FLAGS, True))
    return result


class AdapterTests(unittest.TestCase):
    def test_valid_receipt_and_explicit_legacy_alias(self):
        # Synthetic fixture remains only in a temporary test directory.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'synthetic.json'
            path.write_text(json.dumps(receipt()), encoding='utf-8')
            args = types.SimpleNamespace(witness='v9', v9_factory_report=str(path),
                                         v9_factory_sha256=adapter.base.pin(path)['sha256'])
            report = {}
            selected, deps = adapter.choose_v9(args, report)
            self.assertIs(selected, adapter.witness)
            self.assertEqual(deps, selected.witness_dependency_pins())
            self.assertEqual(args.v8_factory_report, str(path))
            self.assertEqual(report['v8_factory_receipt'], report['v9_factory_receipt'])
            self.assertIn('native_keyframe_bulk_factory_009.py', report['v8_factory_sources'])
            self.assertEqual(report['witness_adapter']['actual_witness'], 'v9')

    def test_failed_and_legacy_factory_rejected(self):
        for key in adapter.FLAGS:
            bad = receipt()
            bad[key] = False
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                adapter.validate_factory(bad)
        for name, value in (('completed', False), ('error', 'native failed'), ('blender', '5.1')):
            bad = receipt()
            bad[name] = value
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                adapter.validate_factory(bad)
        bad = receipt()
        del bad['factory_override']
        with self.assertRaises(RuntimeError):
            adapter.validate_factory(bad)

    def test_coverage_and_source_mutations_rejected(self):
        cases = []
        for key in ('field_checks', 'enum_api_checks', 'mutation_traps'):
            bad = receipt()
            member = next(iter(bad[key]))
            bad[key]['invented'] = bad[key].pop(member)
            cases.append(bad)
        bad = receipt()
        bad['old_point_state_sha256_before_after'][1] = 'b'*64
        cases.append(bad)
        for key in ('witness_sources', 'scripts', 'factory_override'):
            bad = receipt()
            next(iter(bad[key].values()))['sha256'] = '0'*64
            cases.append(bad)
        for index, bad in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                adapter.validate_factory(bad)

    def run_hooks(self, action):
        original = lambda: None
        scene = types.SimpleNamespace(_remap_rna=original)
        scope = {}
        exec('def _remap_rna():\n    return _remap_rna\n', scope)
        installed = scope['_remap_rna']
        report = {}
        original_choose = adapter.runner.choose_witness
        def body(args, target_report):
            self.assertIs(scene._remap_rna, installed)
            self.assertIs(installed(), installed)
            self.assertIs(adapter.runner.choose_witness, adapter.choose_v9)
            action(scene, target_report)
        with patch.object(adapter.parent, 'sealed_remap', return_value=(installed, scope, {'scope': 'pure'})), \
             patch.object(adapter.runner, 'main', side_effect=body):
            try:
                adapter.run_owned(None, report, scene)
            finally:
                self.assertEqual(scope['_remap_rna'], installed)
        return report, scene, original, original_choose

    def test_normal_recursive_binding_and_restoration(self):
        report, scene, original, original_choose = self.run_hooks(lambda *_: None)
        self.assertIs(scene._remap_rna, original)
        self.assertIs(adapter.runner.choose_witness, original_choose)
        self.assertTrue(all(report['adapter_hooks_still_owned'].values()))
        self.assertTrue(all(report['adapter_hooks_restored'].values()))

    def test_original_exception_and_restoration(self):
        before = adapter.runner.choose_witness
        marker = ValueError('original main error')
        def fail(scene, report):
            self.failed_scene = scene
            self.failed_report = report
            raise marker
        with self.assertRaises(ValueError) as caught:
            self.run_hooks(fail)
        self.assertIs(caught.exception, marker)
        self.assertIs(adapter.runner.choose_witness, before)
        self.assertTrue(all(self.failed_report['adapter_hooks_restored'].values()))

    def test_foreign_hooks_never_overwritten(self):
        before = adapter.runner.choose_witness
        foreign = lambda: None
        for field in ('parent', 'chooser'):
            def replace(scene, report):
                if field == 'parent':
                    scene._remap_rna = foreign
                else:
                    adapter.runner.choose_witness = foreign
            try:
                report, scene, original, original_choose = self.run_hooks(replace)
                key = 'parent_remap' if field == 'parent' else 'witness_chooser'
                self.assertFalse(report['adapter_hooks_restored'][key])
                self.assertFalse(report['adapter_hooks_still_owned'][key])
                self.assertIs(scene._remap_rna if field == 'parent' else adapter.runner.choose_witness, foreign)
            finally:
                adapter.runner.choose_witness = before

    def test_protected_source_and_no_new_native_operations(self):
        import ast
        tree = ast.parse(Path(adapter.__file__).read_text(encoding='utf-8'))
        forbidden = {'frame_set', 'save_as_mainfile', 'open_mainfile', 'register', 'defer_runtime'}
        self.assertFalse({node.func.attr for node in ast.walk(tree)
                          if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)} & forbidden)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'update':
                self.assertIsInstance(node.func.value, ast.Name)
                self.assertEqual(node.func.value.id, 'report')
        self.assertEqual(adapter.base.pin(adapter.HERE/'mesh_cache_actor_full30_002.py')['sha256'],
                         adapter.PINS['mesh_cache_actor_full30_002.py'])


if __name__ == '__main__':
    unittest.main()
