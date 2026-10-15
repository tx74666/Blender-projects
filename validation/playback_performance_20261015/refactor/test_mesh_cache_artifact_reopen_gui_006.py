"""Pure thin-GUI routing/layer/visibility tests; no Blender or receipt emitted."""
import sys
import dis
import types
import unittest
from unittest.mock import patch

import mesh_cache_artifact_reopen_gui_006 as gui


class Gui006Tests(unittest.TestCase):
    def test_original_class_code_and_globals_stay_separate(self):
        for name, value in vars(gui.original.ReopenSession).items():
            original = value.__func__ if isinstance(value, staticmethod) else value
            if isinstance(original, types.FunctionType):
                copied = getattr(gui._BaseSession, name)
                # Whole-module and isolated-class compilation may encode
                # different LOAD_ATTR/LOAD_GLOBAL call flags. Compare resolved
                # instructions rather than their private operand indexes.
                self.assertEqual([(item.opname, item.argval) for item in dis.get_instructions(original)],
                                 [(item.opname, item.argval) for item in dis.get_instructions(copied)], name)
                self.assertIsNot(original.__globals__, copied.__globals__)
        scope = gui._BaseSession.start.__globals__
        self.assertEqual(scope['CONTRACT_PATH'], gui.CONTRACT_PATH)
        self.assertEqual(scope['__file__'], str(gui.Path(gui.__file__).resolve()))
        self.assertEqual(gui.original.CONTRACT_PATH.name, 'mesh_cache_artifact_contract_005.py')
        self.assertEqual(gui.original.CONTRACT_SHA, 'a4e68220734435de8f8ac52bbbca73c2b7259253626c1bc301dfcfc9b55efad6')
        self.assertIsNot(scope['importlib'], gui.original.importlib)

    def test_local_import_route_only_redirects_contract005(self):
        marker = object()
        with patch.object(gui.importlib, 'import_module', return_value=marker) as imported:
            self.assertIs(gui.routed_import('mesh_cache_artifact_contract_005'), marker)
            imported.assert_called_with('mesh_cache_artifact_contract_006', None)
            gui.routed_import('json')
            imported.assert_called_with('json', None)

    def test_select_source_layer_once_then_fail_without_autoheal(self):
        class Mesh(dict):
            type = 'MESH'
        layer_a, layer_b = types.SimpleNamespace(name='A'), types.SimpleNamespace(name='B')
        scene = types.SimpleNamespace(view_layers={'A': layer_a, 'B': layer_b}, objects=[Mesh() for _ in range(69)])
        context = types.SimpleNamespace(view_layer=layer_a)
        assignments = []
        class Window:
            @property
            def view_layer(self):
                return context.view_layer
            @view_layer.setter
            def view_layer(self, value):
                assignments.append(value.name)
                context.view_layer = value
        window = Window()
        window.scene = scene
        context.window = window
        session = gui.ReopenSession.__new__(gui.ReopenSession)
        session.scene, session.layer_selected, session.report = scene, False, {}
        session.contract = {'visibility': {'context_view_layer': 'B'}, 'objects': [None]*69}
        session.runtime = types.SimpleNamespace(RECORD_KEY='owned-authoring')
        with patch.dict(sys.modules, bpy=types.SimpleNamespace(context=context)):
            session.assert_cache_health()
            session.assert_cache_health()
            self.assertEqual(assignments, ['B'])
            context.view_layer = layer_a
            with self.assertRaises(RuntimeError):
                session.assert_cache_health()
            self.assertIs(context.view_layer, layer_a)
            self.assertEqual(assignments, ['B'])
        self.assertTrue(session.report['source_active_view_layer_restored'])

    def frame_session(self):
        session = gui.ReopenSession.__new__(gui.ReopenSession)
        session.frame, session.phase = 1, 'VERIFY'
        session.scene = types.SimpleNamespace(frame_current=1, frame_subframe=0.)
        session.contract = {}
        session.report = {'visibility_initial_exact': False, 'visibility_frames': []}
        session.assert_cache_health = lambda: None
        session.standard_handlers = {}
        all_layer_reads, frames = [], []
        def visibility(scene, contract, all_layers):
            all_layer_reads.append(all_layers)
            return {'exact': True, 'context_view_layer': 'B', 'layers_checked': 2}
        def frame(scene, contract, number):
            frames.append(number)
            if getattr(session, 'bad_visibility', False):
                raise RuntimeError('current-layer Base flags changed')
            return {'exact': True, 'frame': number, 'visibility_exact': True,
                'meshes': [{'exact': True, 'changed_components': []} for _ in range(69)]}
        session.helper = types.SimpleNamespace(check_visibility=visibility, check_frame=frame)
        bpy = types.SimpleNamespace(app=types.SimpleNamespace(handlers=types.SimpleNamespace()))
        return session, bpy, all_layer_reads, frames

    def test_full_table_once_and_current_layer_guard_each_frame(self):
        session, bpy, all_reads, frames = self.frame_session()
        for frame in (1, 2):
            session.frame = session.scene.frame_current = frame
            row = session.verify_frame(bpy)
            self.assertTrue(row['full69_geometry_exact'] and row['current_layer_visibility_exact'])
        self.assertEqual(all_reads, [True])
        self.assertEqual(frames, [1, 2])
        self.assertEqual([row['frame'] for row in session.report['visibility_frames']], [1, 2])
        session.phase = 'RESTORE_VERIFY'
        session.frame = session.scene.frame_current = 1
        session.verify_frame(bpy)
        self.assertEqual(len(session.report['visibility_frames']), 2)
        session.bad_visibility = True
        with self.assertRaisesRegex(RuntimeError, 'Base flags changed'):
            session.verify_frame(bpy)

    def test_finish_requires_complete_visibility_and_preserves_original_error(self):
        session, bpy, all_reads, frames = self.frame_session()
        session.finished, session.layer_selected = False, True
        session.report.update(visibility_initial_exact=True, source_active_view_layer_restored=True,
            adapter_base_gui=gui.pin(gui.BASE_PATH), visibility_frames=[{'frame': n, 'exact': True} for n in range(1, 31)])
        with patch.object(gui._BaseSession, 'finish') as finish:
            session.finish()
            finish.assert_called_once_with(None)
        self.assertTrue(session.report['visibility_after_exact'])
        self.assertTrue(session.report['visibility_current_layer_all_frames_exact'])
        session.report['visibility_frames'].pop()
        with patch.object(gui._BaseSession, 'finish') as finish:
            session.finish('original failure')
            self.assertIn('original failure', finish.call_args.args[0])
            self.assertIn('GUI006 visibility/source cleanup', finish.call_args.args[0])

    def test_cleanup_never_selects_uninitialized_layer(self):
        session, bpy, all_reads, frames = self.frame_session()
        session.finished, session.layer_selected = False, False
        session.assert_cache_health = lambda: self.fail('cleanup must not auto-select a layer')
        with patch.object(gui._BaseSession, 'finish') as finish:
            session.finish('original failure')
            self.assertIn('never selected', finish.call_args.args[0])
        self.assertEqual(all_reads, [])


if __name__ == '__main__':
    unittest.main()
