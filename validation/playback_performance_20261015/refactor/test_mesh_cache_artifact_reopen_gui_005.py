"""Pure event-loop/ownership tests; no Blender import, launch or report emitted."""
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import mesh_cache_artifact_reopen_gui_005 as gui


def settled():
    return {'_RUNTIME_REGISTERED': True, '_SCENE_STATE_ACTIVE': True, '_INITIALIZE_PENDING': False,
            '_SCENE_CLEANUP_PENDING': False, '_BUSY': False, 'natural_lifecycle_timer_registered': False,
            'errors': {}}


def state_session():
    session = gui.ReopenSession.__new__(gui.ReopenSession)
    advances, reads, finishes = [], [], []
    scene = types.SimpleNamespace(frame_current=1, frame_subframe=0.)
    def frame_set(frame, subframe):
        advances.append(frame)
        scene.frame_current, scene.frame_subframe = frame, subframe
    scene.frame_set = frame_set
    session.scene, session.artifact = scene, Path(__file__).resolve().with_name('synthetic-private.blend')
    session.args, session.started = types.SimpleNamespace(timeout=180.), gui.time.monotonic()
    session.phase, session.frame, session.stable_ticks = 'WAIT_STANDARD_LOAD', 1, 0
    session.last_lifecycle, session.tee = None, types.SimpleNamespace(detected=False)
    session.contract = {'scene': {'saved_frame': 1}, 'portable_animation': {'test': 'fixed'}}
    session.helper = types.SimpleNamespace(animation_state=lambda *args: {'test': 'fixed'},
                                          check_serialized_dependencies=lambda *args: {'exact': True})
    session.report = {'frames': [], 'lifecycle_observations': []}
    session.lifecycle = lambda bpy: settled()
    session.flush = lambda: None
    session.finish = lambda error=None: finishes.append(error)
    def verify(bpy):
        reads.append((session.frame, len(advances)))
        return {'frame': session.frame, 'full69_geometry_exact': True, 'mesh_count': 69}
    session.verify_frame = verify
    bpy = types.SimpleNamespace(data=types.SimpleNamespace(filepath=str(session.artifact)),
        context=types.SimpleNamespace(scene=scene), app=types.SimpleNamespace(handlers=types.SimpleNamespace()))
    return session, bpy, advances, reads, finishes


class GuiTests(unittest.TestCase):
    def test_natural_settle_then_separate_advance_and_read(self):
        session, bpy, advances, reads, finishes = state_session()
        with patch.dict(sys.modules, bpy=bpy):
            self.assertEqual(session.tick(), .1)
            self.assertEqual(advances, [])
            self.assertEqual(session.tick(), .05)
            self.assertEqual(advances, [1])
            self.assertEqual(reads, [])
            for _ in range(100):
                if session.tick() is None:
                    break
        self.assertEqual(advances, list(range(1, 31))+[1])
        self.assertEqual([row[0] for row in reads], advances)
        self.assertEqual([row[1] for row in reads], list(range(1, 32)))
        self.assertEqual([row['frame'] for row in session.report['frames']], list(range(1, 31)))
        self.assertTrue(session.report['saved_frame_restored_verified'])
        self.assertTrue(session.report['portable_animation_start_end_exact'])
        self.assertEqual(finishes, [None])

    def test_lifecycle_error_and_timeout_stop_before_seek(self):
        for mode in ('error', 'timeout'):
            session, bpy, advances, reads, finishes = state_session()
            if mode == 'error':
                state = settled()
                state['errors'] = {'problem': 'standard callback failed'}
                session.lifecycle = lambda bpy: state
            else:
                session.started -= 181
            with self.subTest(mode=mode), patch.dict(sys.modules, bpy=bpy):
                self.assertIsNone(session.tick())
            self.assertFalse(advances or reads)
            self.assertEqual(len(finishes), 1)
            self.assertIsInstance(finishes[0], str)

    def test_false_or_incomplete_geometry_receipt_rejected(self):
        session, bpy, advances, reads, finishes = state_session()
        session.assert_cache_health = lambda: None
        session.standard_handlers = {}
        result = {'frame': 1, 'exact': True,
                  'meshes': [{'exact': True, 'changed_components': []} for _ in range(69)]}
        session.helper.check_frame = lambda *args: result
        self.assertTrue(gui.ReopenSession.verify_frame(session, bpy)['full69_geometry_exact'])
        for mutate in (lambda: result.update(exact=False), lambda: result['meshes'].pop(),
                       lambda: result['meshes'][0].update(changed_components=['world'])):
            mutate()
            with self.assertRaises(RuntimeError):
                gui.ReopenSession.verify_frame(session, bpy)
            result['exact'] = True
            while len(result['meshes']) < 69:
                result['meshes'].append({'exact': True, 'changed_components': []})

    def test_cache_health_rejects_authoring_enrollment(self):
        class Mesh(dict):
            type = 'MESH'
        session, bpy, *_ = state_session()
        session.scene.objects = [Mesh() for _ in range(69)]
        session.contract['objects'] = [None]*69
        session.runtime = types.SimpleNamespace(RECORD_KEY='authoring')
        session.assert_cache_health()
        session.scene.objects[50]['authoring'] = '{}'
        with self.assertRaises(RuntimeError):
            session.assert_cache_health()

    def test_stderr_observer_detects_after_truncation_and_split_tokens(self):
        observer = gui.PythonErrorTee(io.StringIO())
        observer.write('x'*40000)
        observer.write('Traceback (most recent ')
        observer.write('call last)')
        self.assertTrue(observer.detected and observer.truncated)
        self.assertEqual(len(observer.text), 32768)

    def test_finish_restores_only_owned_stderr_and_timer(self):
        for foreign in (False, True):
            session, bpy, *_ = state_session()
            del session.finish
            session.finished, session.timer = False, object()
            timers = {session.timer}
            bpy.app.timers = types.SimpleNamespace(is_registered=lambda timer: timer in timers,
                unregister=lambda timer: timers.remove(timer))
            bpy.context.window_manager = types.SimpleNamespace(windows=[])
            session.factory_ui = []
            session.standard_handlers = {}
            session.runtime = types.SimpleNamespace(_RUNTIME_REGISTERED=True)
            session.contract['objects'] = [None]*69
            session.helper = types.SimpleNamespace(verify_external_pins=lambda receipt: None,
                check_binding=lambda *args: None, check_serialized_dependencies=lambda *args: {'exact': True})
            session.receipt_pin = {'path': 'receipt'}
            session.artist_pin = {'path': 'artist'}
            session.receipt = {'artifact': {'path': 'artifact'}}
            session.report.update(script={'path': 'entry'}, shared_contract_helper={'path': 'helper'},
                frames=[{'frame': n} for n in range(1, 31)], saved_frame_restored_verified=True,
                portable_animation_start_end_exact=True, cached_meshes_not_authoring_enrolled=True)
            session.stream = io.StringIO()
            original, replacement = io.StringIO(), io.StringIO()
            session.tee = gui.PythonErrorTee(original)
            def fake_pin(path):
                if path == gui.ARTIST:
                    return session.artist_pin
                if path == session.artifact:
                    return session.receipt['artifact']
                if path == gui.__file__:
                    return session.report['script']
                if path == gui.CONTRACT_PATH:
                    return session.report['shared_contract_helper']
                return session.receipt_pin
            with self.subTest(foreign=foreign), patch.dict(sys.modules, bpy=bpy), \
                 patch.object(gui, 'pin', side_effect=fake_pin), \
                 patch.object(sys, 'stderr', replacement if foreign else session.tee):
                session.finish()
                self.assertFalse(timers)
                self.assertIs(sys.stderr, replacement if foreign else original)
                self.assertEqual(session.report['completed'], not foreign)
                self.assertEqual(session.report['own_stderr_restored'], not foreign)
                self.assertTrue(session.stream.closed)

    def test_no_forbidden_lifecycle_or_save_calls(self):
        import ast
        tree = ast.parse(Path(gui.__file__).read_text(encoding='utf-8'))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        names = {node.func.attr for node in calls if isinstance(node.func, ast.Attribute)}
        self.assertFalse(names & {'defer_runtime', '_calculate_object', 'prepare', 'capture',
                                  'save_as_mainfile', 'quit_blender', 'animation_play'})
        for node in calls:
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'update':
                self.assertIn(ast.unparse(node.func.value), ('self.report', 'report', 'digest'))
        opens = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == 'open_mainfile']
        self.assertEqual(len(opens), 1)
        self.assertTrue(any(key.arg == 'load_ui' and isinstance(key.value, ast.Constant) and key.value.value is False
                            for key in opens[0].keywords))


if __name__ == '__main__':
    unittest.main()
