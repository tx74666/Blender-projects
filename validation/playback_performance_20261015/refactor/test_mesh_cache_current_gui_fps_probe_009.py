"""Only009 binding deltas; frozen008 retains timing/health proof tests."""
import ast
import io
import sys
import unittest
from unittest.mock import patch
import mesh_cache_current_gui_fps_probe_009 as probe
import test_mesh_cache_current_gui_fps_probe_008 as prior_tests


class Tests(unittest.TestCase):
    def test_gui9_extra_previous_binding_gate_keeps_existing_current_proof(self):
        receipt = prior_tests.gui()
        with self.assertRaises(RuntimeError):
            probe.validate_gui(receipt, 777, receipt['artifact'])
        receipt['adapter_previous_gui_unchanged'] = True
        self.assertEqual(probe.validate_gui(receipt, 777, receipt['artifact']), {})
        for key in probe.GUI_FLAGS:
            with self.subTest(flag=key), self.assertRaises(RuntimeError):
                probe.validate_gui({**receipt, key: False}, 777, receipt['artifact'])

    def test_entire008_class_ast_retained_in_private009_binding(self):
        before = dict(vars(probe.previous))
        cls, extraction = probe.private_binding()
        source = ast.parse(probe.PREVIOUS_PATH.read_bytes())
        node = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'CacheProbe')
        self.assertEqual(extraction['previous_binding_class_ast_sha256'],
            probe.hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest())
        self.assertEqual(extraction['inherited_extraction'], probe.previous.EXTRACTION)
        scope = cls.__init__.__globals__
        for name in ('CONTRACT_PATH', 'CONTRACT_SHA', 'GUI_PATH', 'GUI_SHA', 'SOURCE_SEAL_PATH', 'SOURCE_SEAL_SHA'):
            self.assertEqual(scope[name], getattr(probe, name))
        self.assertEqual(scope['__file__'], str(probe.Path(probe.__file__).resolve()))
        self.assertIs(scope['_VisibilityProbe'].__init__.__globals__['_sealed_init'].__globals__['validate_gui'], probe.validate_gui)
        self.assertEqual(before, dict(vars(probe.previous)))
        self.assertEqual(probe.previous.CONTRACT_PATH.name, 'mesh_cache_current_contract_008.py')
        self.assertEqual(probe.previous.GUI_PATH.name, 'mesh_cache_current_reopen_gui_008.py')
        self.assertEqual(cls.full_state.__globals__['baseline'].comparison_view,
            probe.previous.baseline.comparison_view)

    def test_import_router_only_changes_literal_contract_in_own_namespace(self):
        with patch.object(probe.importlib, 'import_module', side_effect=lambda name, package: (name, package)):
            self.assertEqual(probe.routed_import('mesh_cache_artifact_contract_005'),
                ('mesh_cache_current_contract_009', None))
            self.assertEqual(probe.routed_import('gpu'), ('gpu', None))

    def test_timing_callbacks_fixed_window_are_actual_original_functions(self):
        for name in ('tick', 'on_pre', 'on_post', 'on_draw', 'context_state', 'visibility_state', 'in_hot'):
            self.assertIs(getattr(probe.CacheProbe, name), getattr(probe.core.Probe, name))
        self.assertEqual((probe.core.WARM_SECONDS, probe.core.MEASURE_SECONDS), (2., 16.))
        self.assertEqual(probe.CacheProbe.assert_hot_bindings.__code__, probe.previous.CacheProbe.assert_hot_bindings.__code__)
        self.assertEqual(probe.CacheProbe.capture_hot_bindings.__code__, probe.previous.CacheProbe.capture_hot_bindings.__code__)

    def test_previous008_source_is_in_existing_final_dependency_gate(self):
        stream = io.StringIO()
        def initialized(controller, config):
            controller.dependencies, controller.report = {}, {}
            controller.stream, controller.flush = stream, lambda: None
        with patch.object(probe._PreviousProbe, '__init__', side_effect=initialized, autospec=True):
            controller = probe.CacheProbe({})
            self.assertEqual(controller.dependencies['previous_current_fps008']['sha256'], probe.PREVIOUS_SHA)
            self.assertEqual(controller.report['adapter_previous_fps'], controller.dependencies['previous_current_fps008'])
        stream.close()
        failed = io.StringIO()
        def initialize_failure(controller, config):
            initialized(controller, config)
            controller.stream = failed
        with patch.object(probe._PreviousProbe, '__init__', side_effect=initialize_failure, autospec=True), \
             patch.object(probe, 'pin', side_effect=ValueError('pin failed')):
            with self.assertRaisesRegex(ValueError, 'pin failed'):
                probe.CacheProbe({})
        self.assertTrue(failed.closed)

    def test_own_session_cleanup_retains_primary_error_and_foreign_owner(self):
        controller = object.__new__(probe.CacheProbe)
        controller.closed = False
        probe.SESSION = controller
        try:
            with patch.object(probe._PreviousProbe, 'finish', side_effect=ValueError('original cleanup')):
                with self.assertRaisesRegex(ValueError, 'original cleanup'):
                    controller.finish()
            self.assertIsNone(probe.SESSION)
            foreign = object()
            probe.SESSION = foreign
            with patch.object(probe._PreviousProbe, 'finish'):
                controller.finish()
            self.assertIs(probe.SESSION, foreign)
        finally:
            probe.SESSION = None

    def test_final_dependency_pins_and_no_new_native_work(self):
        self.assertNotIn('bpy', sys.modules)
        for path, sha in ((probe.PREVIOUS_PATH, probe.PREVIOUS_SHA), (probe.CONTRACT_PATH, probe.CONTRACT_SHA),
            (probe.GUI_PATH, probe.GUI_SHA), (probe.SOURCE_SEAL_PATH, probe.SOURCE_SEAL_SHA)):
            self.assertEqual(probe.pin(path)['sha256'], sha)
        tree = ast.parse(probe.Path(probe.__file__).read_bytes())
        forbidden = {'open_mainfile', 'save_mainfile', 'save_as_mainfile', 'frame_set', 'animation_play',
            'defer_runtime', '_calculate_object', 'register_class'}
        self.assertFalse({n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)} & forbidden)


if __name__ == '__main__':
    unittest.main()
