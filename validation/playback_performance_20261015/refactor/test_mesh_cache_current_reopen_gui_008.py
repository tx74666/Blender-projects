"""Thin008 namespace/pin/error proofs only; no bpy/native process."""
import ast
import dis
import hashlib
import io
import types
import unittest
from unittest.mock import patch

import mesh_cache_current_reopen_gui_008 as gui


class Gui008Tests(unittest.TestCase):
    def test_current_class_and_lifecycle_code_unchanged_in_private_namespaces(self):
        for name, before in vars(gui.original.ReopenSession).items():
            if isinstance(before, types.FunctionType):
                after = getattr(gui._CurrentSession, name)
                self.assertEqual([(r.opname, r.argval) for r in dis.get_instructions(before)],
                    [(r.opname, r.argval) for r in dis.get_instructions(after)], name)
                self.assertIsNot(before.__globals__, after.__globals__)
        for name in ('start', 'tick', 'ready', 'lifecycle', 'flush'):
            before, after = getattr(gui.original.ReopenSession, name), getattr(gui._CurrentSession, name)
            self.assertEqual([(r.opname, r.argval) for r in dis.get_instructions(before)],
                [(r.opname, r.argval) for r in dis.get_instructions(after)], name)
        cls = next(n for n in gui.sealed_tree().body if isinstance(n, ast.ClassDef) and n.name == 'ReopenSession')
        self.assertEqual(gui.EXTRACTION['current_class_ast_sha256'],
            hashlib.sha256(ast.dump(cls, include_attributes=False).encode()).hexdigest())
        self.assertEqual(gui.EXTRACTION['inherited_extraction'], gui.original.EXTRACTION)

    def test_contract8_routing_is_local_and_start_finish_pin_new_entry(self):
        scope = gui._CurrentSession.start.__globals__
        self.assertEqual(scope['CONTRACT_PATH'], gui.CONTRACT_PATH)
        self.assertEqual(scope['CONTRACT_SHA'], gui.CONTRACT_SHA)
        self.assertEqual(scope['__file__'], str(gui.Path(gui.__file__).resolve()))
        self.assertEqual(gui._CurrentSession.__init__.__globals__['CONTRACT_PATH'], gui.CONTRACT_PATH)
        self.assertEqual(gui.original.CONTRACT_PATH.name, 'mesh_cache_current_contract_007.py')
        self.assertEqual(gui.original.original.CONTRACT_PATH.name, 'mesh_cache_artifact_contract_005.py')
        self.assertIsNot(scope['importlib'], gui.original.original.importlib)
        sentinel = object()
        with patch.object(gui.importlib, 'import_module', return_value=sentinel) as importer:
            self.assertIs(gui.routed_import('mesh_cache_artifact_contract_005'), sentinel)
            importer.assert_called_with('mesh_cache_current_contract_008', None)
            gui.routed_import('json')
            importer.assert_called_with('json', None)

    def test_constructor_requires_exact_real_source_seal_and_inventory(self):
        seal = gui.pin(gui.SOURCE_SEAL_PATH)
        def base(self, args, stream, report):
            self.report = report
            self.receipt = {'current_source_seal': seal, 'current_sources': {'example': 'pin'}}
            self.helper = types.SimpleNamespace(verify_sources=lambda s: {'example': 'pin'})
        with patch.object(gui._CurrentSession, '__init__', base):
            item = gui.ReopenSession(None, io.StringIO(), {})
            self.assertTrue(item.report['current_binding_verified'])
            self.assertEqual(item.report['adapter_current_gui']['sha256'], gui.CURRENT_SHA)
            with patch.object(gui, 'SOURCE_SEAL_SHA', 'bad'):
                with self.assertRaisesRegex(RuntimeError, 'source seal'):
                    gui.ReopenSession(None, io.StringIO(), {})
        def wrong(self, args, stream, report):
            base(self, args, stream, report)
            self.helper.verify_sources = lambda s: {'different': 'pin'}
        with patch.object(gui._CurrentSession, '__init__', wrong):
            with self.assertRaisesRegex(RuntimeError, 'inventory'):
                gui.ReopenSession(None, io.StringIO(), {})

    def item(self):
        item = object.__new__(gui.ReopenSession)
        item.finished = False
        item.report = {'adapter_current_gui': gui.pin(gui.CURRENT_PATH),
            'current_source_seal': gui.pin(gui.SOURCE_SEAL_PATH), 'current_binding_verified': True}
        return item

    def test_finish_success_keeps_inherited_cleanup_and_requires_final_pins(self):
        item, errors = self.item(), []
        with patch.object(gui._CurrentSession, 'finish', lambda self, error: errors.append(error)):
            item.finish()
        self.assertEqual(errors, [None])
        self.assertTrue(item.report['adapter_current_gui_unchanged'])
        self.assertTrue(item.report['current_binding_unchanged'])

    def test_changed_source_retains_original_failure_and_runs_cleanup(self):
        for field in ('adapter_current_gui', 'current_source_seal'):
            item, errors = self.item(), []
            item.report[field] = {'sha256': 'changed'}
            with patch.object(gui._CurrentSession, 'finish', lambda self, error: errors.append(error)):
                item.finish('primary native failure')
            self.assertEqual(len(errors), 1)
            self.assertIn('primary native failure', errors[0])
            self.assertIn('Current008 binding', errors[0])

    def test_finished_guard_has_no_further_pin_or_cleanup_effect(self):
        item = self.item()
        item.finished = True
        with patch.object(gui, 'pin', side_effect=AssertionError('late pin')):
            with patch.object(gui._CurrentSession, 'finish', side_effect=AssertionError('duplicate finish')):
                item.finish()

    def test_entry_executes_sealed_block_and_preserves_session_on_original_exception(self):
        marker = object()
        original_session = gui.SESSION
        try:
            for fail in (False, True):
                source = "if __name__ == '__main__':\n    SESSION = CURRENT_PATH\n"
                if fail:
                    source += "    raise ValueError('original entry failure')\n"
                with patch.object(gui, 'sealed_tree', return_value=ast.parse(source)):
                    with patch.object(gui, 'CURRENT_PATH', marker):
                        if fail:
                            with self.assertRaisesRegex(ValueError, 'original entry failure'):
                                gui.main()
                        else:
                            gui.main()
                self.assertIs(gui.SESSION, marker)
        finally:
            gui.SESSION = original_session


if __name__ == '__main__':
    unittest.main()
