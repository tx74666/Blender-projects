"""Current009 thin namespace/source/error checks; no Blender is loaded."""
import ast
import dis
import hashlib
import io
import types
import unittest
from unittest.mock import patch

import mesh_cache_current_reopen_gui_009 as gui


class Tests(unittest.TestCase):
    def test_complete_previous_binding_class_is_unchanged_and_private(self):
        for name, before in vars(gui.previous.ReopenSession).items():
            if isinstance(before, types.FunctionType):
                after = getattr(gui._PreviousSession, name)
                self.assertEqual([(i.opname, i.argval) for i in dis.get_instructions(before)],
                    [(i.opname, i.argval) for i in dis.get_instructions(after)], name)
                self.assertIsNot(before.__globals__, after.__globals__)
        cls = next(n for n in ast.parse(gui.PREVIOUS_PATH.read_bytes()).body
            if isinstance(n, ast.ClassDef) and n.name == 'ReopenSession')
        self.assertEqual(gui.EXTRACTION['previous_binding_class_ast_sha256'],
            hashlib.sha256(ast.dump(cls, include_attributes=False).encode()).hexdigest())
        for name in ('start', 'tick', 'ready', 'lifecycle', 'flush'):
            before, after = getattr(gui.previous.ReopenSession, name), getattr(gui._PreviousSession, name)
            self.assertEqual([(i.opname, i.argval) for i in dis.get_instructions(before)],
                [(i.opname, i.argval) for i in dis.get_instructions(after)], name)

    def test_all_contract_source_and_file_routes_are_owned_and_originals_unmodified(self):
        for function in (gui._PreviousSession.__init__, gui._PreviousSession.finish,
                         gui._PreviousSession.start):
            scope = function.__globals__
            self.assertEqual(scope['CONTRACT_PATH'], gui.CONTRACT_PATH)
            self.assertEqual(scope['CONTRACT_SHA'], gui.CONTRACT_SHA)
            self.assertEqual(scope['__file__'], str(gui.Path(gui.__file__).resolve()))
        self.assertEqual(gui._PreviousSession.__init__.__globals__['SOURCE_SEAL_PATH'], gui.SOURCE_SEAL_PATH)
        self.assertEqual(gui.previous.CONTRACT_PATH.name, 'mesh_cache_current_contract_008.py')
        self.assertEqual(gui.previous.original.CONTRACT_PATH.name, 'mesh_cache_current_contract_007.py')
        with patch.object(gui.importlib, 'import_module', return_value=object()) as importer:
            gui.routed_import('mesh_cache_artifact_contract_005')
            importer.assert_called_with('mesh_cache_current_contract_009', None)
            gui.routed_import('json')
            importer.assert_called_with('json', None)

    def test_adds_previous_source_receipt_without_changing_current_schema(self):
        def init(self, args, stream, report):
            self.report = report
        with patch.object(gui._PreviousSession, '__init__', init):
            item = gui.ReopenSession(None, io.StringIO(), {})
        self.assertEqual(gui.SCHEMA, 'x.current-pc2-artifact-gui-reopen/1')
        self.assertEqual(item.report['adapter_previous_gui']['sha256'], gui.PREVIOUS_SHA)
        self.assertFalse(item.report['adapter_previous_gui_unchanged'])

    def item(self):
        item = object.__new__(gui.ReopenSession)
        item.finished = False
        item.report = {'adapter_previous_gui': gui.pin(gui.PREVIOUS_PATH)}
        return item

    def test_finish_success_runs_inherited_cleanup_once(self):
        item, errors = self.item(), []
        with patch.object(gui._PreviousSession, 'finish', lambda self, error: errors.append(error)):
            item.finish()
        self.assertEqual(errors, [None])
        self.assertTrue(item.report['adapter_previous_gui_unchanged'])

    def test_changed_source_retains_primary_error_and_still_runs_cleanup(self):
        item, errors = self.item(), []
        item.report['adapter_previous_gui']['bytes'] += 1
        with patch.object(gui._PreviousSession, 'finish', lambda self, error: errors.append(error)):
            item.finish('primary native failure')
        self.assertEqual(len(errors), 1)
        self.assertIn('primary native failure', errors[0])
        self.assertIn('Current009 binding', errors[0])
        self.assertFalse(item.report['adapter_previous_gui_unchanged'])

    def test_finished_guard_does_not_reenter_cleanup_or_read_sources(self):
        item = self.item()
        item.finished = True
        with patch.object(gui, 'pin', side_effect=AssertionError('late pin')):
            with patch.object(gui._PreviousSession, 'finish', side_effect=AssertionError('duplicate cleanup')):
                item.finish()

    def test_entry_keeps_session_and_original_exception(self):
        original = gui.SESSION
        old_tree = gui._OWNED_SCOPE['sealed_tree']
        try:
            gui._OWNED_SCOPE['sealed_tree'] = lambda: ast.parse(
                "if __name__ == '__main__':\n    SESSION = CONTRACT_PATH\n    raise ValueError('native failure')\n")
            with self.assertRaisesRegex(ValueError, 'native failure'):
                gui.main()
            self.assertEqual(gui.SESSION, gui.CONTRACT_PATH)
        finally:
            gui._OWNED_SCOPE['sealed_tree'] = old_tree
            gui.SESSION = gui._OWNED_SCOPE['SESSION'] = original


if __name__ == '__main__':
    unittest.main()
