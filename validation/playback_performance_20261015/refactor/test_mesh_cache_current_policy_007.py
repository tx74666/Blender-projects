"""Pure admission/protection regressions; no native PASS receipts or bpy calls."""
import ast
import importlib
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import mesh_cache_current_policy_007 as policy


class FakeNamed(dict):
    pass


class PolicyTests(unittest.TestCase):
    def make(self):
        obj = policy.CurrentPolicy.__new__(policy.CurrentPolicy)
        obj.report = {'visibility_replay': [], 'shader_replay': []}
        obj.session = NS(scene=object(), view_layer_state={}, closed=False)
        obj.native_reverse = {}
        obj.source_shader = NS(verify_resources=lambda: True)
        obj.target_shader = NS(verify_resources=lambda: True)
        obj.source_before = {'sha256': 'before', 'resources': []}
        obj.golden_shader = {1: {'sha256': 'same', 'resources': []}}
        obj.capture = lambda *args: {'sha256': 'same', 'resources': []}
        return obj

    def test_exact_source_scene_layer_and_clip_selection(self):
        obj = self.make()
        obj.snapshot = {'source_identity': {'scene': 'Actual', 'view_layer': 'Artist', 'frame': [7, 0.]}}
        layer = object()
        scene = NS(view_layers=FakeNamed(Artist=layer), frame_current=7, frame_subframe=0.,
            frame_start=1, frame_end=30, render=NS(fps=30, fps_base=1.))
        bpy = NS(data=NS(scenes=FakeNamed(Actual=scene)), context=NS(window=NS(scene=None, view_layer=None)))
        self.assertIs(obj.loaded_source(bpy), scene)
        self.assertIs(bpy.context.window.view_layer, layer)
        scene.render.fps = 24
        with self.assertRaisesRegex(RuntimeError, '30FPS'):
            obj.loaded_source(bpy)

    def test_same_material_name_different_content_is_rejected(self):
        obj = self.make()
        scene = NS(frame_subframe=0.)
        obj.session.scene = scene
        obj.capture = lambda *args: {'sha256': 'changed-content', 'resources': []}
        with patch.object(policy.contract.visibility, 'check_visibility', return_value={'exact': True}):
            with self.assertRaisesRegex(RuntimeError, 'material graph'):
                obj.target_frame(scene, 1, {}, obj.report)
        self.assertFalse(obj.report['shader_replay'][0]['exact'])

    def test_every_visit_checks_and_only_endpoints_check_full_base_table(self):
        obj = self.make()
        scene = NS(frame_subframe=0.)
        obj.session.scene = scene
        calls = []
        def check(scene, state, all_layers):
            calls.append(all_layers)
            return {'exact': True}
        with patch.object(policy.contract.visibility, 'check_visibility', side_effect=check):
            for _ in range(150):
                obj.target_frame(scene, 1, {}, obj.report)
        self.assertEqual(len(obj.report['shader_replay']), 150)
        self.assertEqual(calls, [True]+[False]*148+[True])

    def test_resource_checks_do_not_touch_closed_target_rna(self):
        obj = self.make()
        obj.capture = lambda *args: obj.source_before
        calls = []
        obj.source_shader = NS(verify_resources=lambda: calls.append('source'))
        obj.target_shader = NS(verify_resources=lambda: calls.append('target'))
        obj.report['shader_replay'] = [{}]
        self.assertTrue(obj.protect_source(object()))
        obj.session.closed = True
        self.assertTrue(obj.protect_source(object()))
        self.assertEqual(calls, ['source', 'target', 'source'])

    def test_source_material_change_is_not_hidden_by_geometry(self):
        obj = self.make()
        obj.session = None
        self.assertFalse(obj.protect_source(object()))

    def test_no_legacy_input_gate_or_shared_global_mutation(self):
        here = Path(__file__).resolve().parent
        files = ('mesh_cache_actor_current_core_007.py', 'mesh_cache_current_policy_007.py',
            'mesh_cache_current_contract_007.py', 'mesh_cache_current_runner_007.py')
        for name in files:
            text = (here/name).read_text(encoding='utf-8')
            self.assertNotIn('40644b848dd2cb2c', text)
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        self.assertFalse(isinstance(target, ast.Attribute) and target.attr in ('pin', '_remap_rna', 'build_isolated_scene'))

    def test_missing_real_receipt_refuses_without_importing_bpy(self):
        import mesh_cache_current_runner_007 as entry
        args = entry.parser().parse_args(['capture', '--input', 'missing.blend', '--artist', 'X.blend',
            '--snapshot-report', '__missing_actual_capture__.json', '--snapshot-sha256', '0'*64,
            '--input-sha256', '0'*64, '--input-bytes', '1', '--tiny-report', 'missing.json',
            '--tiny-sha256', '0'*64, '--cache-dir', 'unused', '--v9-factory-report', 'missing.json',
            '--v9-factory-sha256', '0'*64, '--source-seal-sha256', '0'*64, '--report', 'unused.json'])
        original = importlib.import_module
        def guarded(name, *args, **kwargs):
            if name == 'bpy':
                raise AssertionError('Native imported before actual receipt')
            return original(name, *args, **kwargs)
        with patch.object(importlib, 'import_module', side_effect=guarded), patch.object(entry, 'preflight_sources'):
            with self.assertRaises(FileNotFoundError):
                entry.run(args, {})

    def test_captured_target_resources_can_be_checked_under_source_context(self):
        obj = NS(as_pointer=lambda: 123, session_uid=45)
        token = (123, 45)
        calls = []
        witness = NS(verify_resources=lambda: calls.append('resource-only') or True)
        with patch.dict(policy.contract._SHADERS, {token: witness}, clear=True), patch.object(policy.contract, '_shader', side_effect=AssertionError('wrong graph')):
            self.assertTrue(policy.contract.verify_shader_resources(obj, {}))
        self.assertEqual(calls, ['resource-only'])


if __name__ == '__main__':
    unittest.main()
