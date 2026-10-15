"""Pure GUI007 AST/current-count/material gates; never launch or open Blender."""
import ast
import dis
import hashlib
import io
import sys
import types
import unittest
from unittest.mock import patch

import mesh_cache_current_reopen_gui_007 as gui


class Mesh(dict):
    type = 'MESH'


class GuiCurrentTests(unittest.TestCase):
    def test_only_disclosed_base_proofs_change_and_original_globals_stay_untouched(self):
        changed = {'assert_cache_health', 'verify_frame'}
        for name, value in vars(gui.original.ReopenSession).items():
            before = value.__func__ if isinstance(value, staticmethod) else value
            if isinstance(before, types.FunctionType) and name not in changed:
                after = getattr(gui._BaseSession, name)
                self.assertEqual([(row.opname, row.argval) for row in dis.get_instructions(before)],
                    [(row.opname, row.argval) for row in dis.get_instructions(after)], name)
                self.assertIsNot(before.__globals__, after.__globals__)
        self.assertEqual(gui.EXTRACTION['changes'], {'mesh_count_constants': 3,
            'geometry_field_rename': 1, 'shader_guard': 1, 'result_fields': 3})
        scope = gui._BaseSession.start.__globals__
        self.assertEqual(scope['CONTRACT_PATH'], gui.CONTRACT_PATH)
        self.assertEqual(scope['__file__'], str(gui.Path(gui.__file__).resolve()))
        self.assertEqual(gui.original.CONTRACT_PATH.name, 'mesh_cache_artifact_contract_005.py')
        self.assertIsNot(scope['importlib'], gui.original.importlib)

    def test_visibility_class_AST_is_exact006_and_import_router_is_local(self):
        source = ast.parse(gui.VISIBILITY_PATH.read_text(encoding='utf-8'))
        cls = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'ReopenSession')
        self.assertEqual(hashlib.sha256(ast.dump(cls, include_attributes=False).encode()).hexdigest(),
            gui.EXTRACTION['visibility_class_ast_sha256'])
        marker = object()
        with patch.object(gui.importlib, 'import_module', return_value=marker) as importer:
            self.assertIs(gui.routed_import('mesh_cache_artifact_contract_005'), marker)
            importer.assert_called_with('mesh_cache_current_contract_007', None)
            gui.routed_import('json')
            importer.assert_called_with('json', None)

    def test_real_contract_count_replaces69_and_separate_shader_false_cannot_pass(self):
        meshes = [Mesh(), Mesh()]
        result = {'exact': True, 'frame': 1, 'meshes': [{'exact': True, 'changed_components': []} for _ in meshes],
            'shader_exact': True, 'shader_sha256': 'a'*64, 'visibility_exact': True}
        state = types.SimpleNamespace(scene=types.SimpleNamespace(objects=meshes, frame_current=1, frame_subframe=0.),
            frame=1, expected_mesh_count=2, contract={'objects': [1, 2]}, report={},
            runtime=types.SimpleNamespace(RECORD_KEY='record'), standard_handlers={'x': []},
            helper=types.SimpleNamespace(check_frame=lambda *args: result))
        state.assert_cache_health = lambda: gui._BaseSession.assert_cache_health(state)
        scope = gui._BaseSession.verify_frame.__globals__
        with patch.dict(scope, handlers=lambda bpy: {'x': []}):
            row = gui._BaseSession.verify_frame(state, object())
            self.assertEqual(row['mesh_count'], 2)
            self.assertTrue(row['full_current_geometry_exact'])
            self.assertNotIn('full69_geometry_exact', row)
            result['shader_exact'] = False
            with self.assertRaisesRegex(RuntimeError, 'shader or Base'):
                gui._BaseSession.verify_frame(state, object())
            result['shader_exact'] = True
            result['visibility_exact'] = False
            with self.assertRaisesRegex(RuntimeError, 'shader or Base'):
                gui._BaseSession.verify_frame(state, object())

    def test_constructor_current_provenance_and_positive_dynamic_count(self):
        def fake_base(self, args, stream, report):
            self.contract = {'schema': 'x.current-pc2-artifact-contract/1', 'objects': [1, 2, 3]}
            self.receipt = {'schema': 'x.current-pc2-artifact/1', 'current_snapshot_receipt': {'sha256': 'b'*64},
                'input_before': {'sha256': 'c'*64}}
            self.report = report
        with patch.object(gui._BaseSession, '__init__', fake_base):
            item = gui.ReopenSession(None, io.StringIO(), {})
        self.assertEqual(item.expected_mesh_count, 3)
        self.assertEqual(item.report['schema'], gui.SCHEMA)
        self.assertTrue(item.report['current_snapshot_provenance_verified'])
        self.assertEqual(item.report['current_input']['sha256'], 'c'*64)

    def test_per_frame_and_saved1_material_receipts_require_initial_resource_check(self):
        item = object.__new__(gui.ReopenSession)
        item.report = {'shader_frames': [], 'portable_animation_initial_exact': False}
        item.expected_mesh_count, item.frame, item.phase = 2, 1, 'VERIFY'
        row = {'mesh_count': 2, 'shader_exact': True, 'visibility_exact': True,
            'shader_sha256': 'd'*64, 'check_sha256': 'e'*64}
        with patch.object(gui._VisibilitySession, 'verify_frame', return_value=row):
            with self.assertRaisesRegex(RuntimeError, 'Initial current animation/resource'):
                item.verify_frame(None)
            item.report['portable_animation_initial_exact'] = True
            item.verify_frame(None)
            self.assertEqual(item.report['shader_frames'], [{'frame': 1, 'exact': True, 'sha256': 'd'*64, 'check_sha256': 'e'*64}])
            self.assertTrue(item.report['current_material_resources_initial_exact'])
            item.phase = 'RESTORE_VERIFY'
            item.verify_frame(None)
            self.assertTrue(item.report['current_material_saved_frame_exact'])
            self.assertEqual(len(item.report['shader_frames']), 1)

    def test_material_failure_retains_original_error_and_runs_inherited_cleanup(self):
        item = object.__new__(gui.ReopenSession)
        item.finished = False
        item.report = {'shader_frames': [], 'adapter_visibility_gui': gui.pin(gui.VISIBILITY_PATH)}
        observed = []
        with patch.object(gui._VisibilitySession, 'finish', lambda self, error: observed.append(error)):
            item.finish('original native error')
        self.assertEqual(len(observed), 1)
        self.assertIn('original native error', observed[0])
        self.assertIn('Current GUI proof', observed[0])
        self.assertFalse(item.report['current_materials_all_frames_exact'])

    def test_complete_material_flags_pass_without_manual_extra_evaluation(self):
        item = object.__new__(gui.ReopenSession)
        item.finished = False
        item.report = {'shader_frames': [{'frame': frame, 'exact': True} for frame in range(1, 31)],
            'adapter_visibility_gui': gui.pin(gui.VISIBILITY_PATH), 'current_snapshot_provenance_verified': True,
            'current_material_resources_initial_exact': True, 'current_material_saved_frame_exact': True,
            'portable_animation_after_restore_exact': True}
        observed = []
        with patch.object(gui._VisibilitySession, 'finish', lambda self, error: observed.append(error)):
            item.finish()
        self.assertEqual(observed, [None])
        self.assertTrue(item.report['current_materials_all_frames_exact'])
        self.assertTrue(item.report['current_material_resources_after_exact'])


if __name__ == '__main__':
    unittest.main()
