"""Pure one-shot tests; all SaveCopy/state/file operations are fakes."""
import ast
import io
import json
import sys
import types
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import current_model_save_copy_010 as probe


class Receipt(io.StringIO):
    saved = None
    def close(self):
        self.saved = self.getvalue()
        super().close()


class SaveTests(unittest.TestCase):
    def invoke(self, *, operation_error=False, changed=False, result=None, pre_read_mutation=False):
        receipt, calls = Receipt(), []
        saved = False
        before = {'dirty': True, 'filepath': str(probe.HERE.parents[2]/'X.blend'), 'handlers': {}}
        runtime = types.SimpleNamespace(__file__=str(probe.HERE/'fake_package/forearm_twist.py'))
        def save(**kwargs):
            nonlocal saved
            calls.append(kwargs)
            saved = True
            if operation_error:
                raise ValueError('original SaveCopy error')
            return {'FINISHED'} if result is None else result
        def props(scene):
            calls.append('witness')
            return {'sha256': 'changed' if changed and saved else 'before'}
        def pin(path):
            return {'path': str(path), 'sha256': 'a'*64, 'bytes': 42}
        bpy = types.SimpleNamespace(app=types.SimpleNamespace(background=False, version=(5, 2, 0), version_string='5.2.0-fake'),
            context=types.SimpleNamespace(window=object(), screen=object(), area=object(),
                scene=types.SimpleNamespace(name_full='Current', frame_current=21, frame_subframe=0.),
                view_layer=types.SimpleNamespace(name='Main')),
            data=types.SimpleNamespace(filepath=before['filepath']),
            ops=types.SimpleNamespace(wm=types.SimpleNamespace(save_as_mainfile=save)))
        config = {'expected_pid': probe.os.getpid(), 'artist': before['filepath'], 'artist_sha256': 'a'*64,
            'copy': str(probe.HERE/'unique_fake_copy_dir/current.blend'), 'report': str(probe.HERE/'unique_fake_copy.json')}
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, bpy=bpy,
                character_designer=types.SimpleNamespace(bl_info={'version': (0, 77, 42)})))
            stack.enter_context(patch.object(probe, 'idle', return_value=runtime))
            stack.enter_context(patch.object(probe, 'state', side_effect=lambda _bpy:
                {**before, **({'unexpected_read_change': True} if pre_read_mutation and 'witness' in calls else {})}))
            stack.enter_context(patch.object(probe.witness, 'source_property_witness', side_effect=props))
            stack.enter_context(patch.object(probe.witness, 'pin', side_effect=pin))
            stack.enter_context(patch.object(probe.witness, 'package_pins', return_value={}))
            stack.enter_context(patch.object(probe.witness, 'witness_dependency_pins', return_value={}))
            stack.enter_context(patch.object(probe.witness, 'handler_snapshot', return_value={}))
            stack.enter_context(patch.object(probe.Path, 'exists', return_value=False))
            stack.enter_context(patch.object(probe.Path, 'is_file', return_value=True))
            stack.enter_context(patch.object(probe.Path, 'open', return_value=receipt))
            mkdir = stack.enter_context(patch.object(probe.Path, 'mkdir'))
            try:
                value = probe.run(config)
                error = None
            except BaseException as caught:
                value, error = None, caught
            if pre_read_mutation:
                mkdir.assert_not_called()
            else:
                mkdir.assert_called_once_with()
        return value, error, json.loads(receipt.saved), calls

    def test_success_uses_copy_and_preserves_dirty_context(self):
        value, error, report, calls = self.invoke()
        self.assertIsNone(error)
        self.assertTrue(value['completed'])
        self.assertTrue(report['source_identity']['dirty'])
        self.assertTrue(report['normal_save_handlers_preserved'])
        self.assertEqual(report['loaded_metadata']['blender'], '5.2.0-fake')
        self.assertEqual(report['loaded_metadata']['character_designer_version'], [0, 77, 42])
        arguments = next(row for row in calls if isinstance(row, dict))
        self.assertEqual(arguments['copy'], True)
        self.assertEqual(arguments['relative_remap'], True)
        self.assertEqual(arguments['show_save_modified_images_dialog'], False)
        self.assertEqual(calls.count('witness'), 2)

    def test_operator_exception_retains_error_and_still_runs_after_proof(self):
        value, error, report, calls = self.invoke(operation_error=True)
        self.assertIsInstance(error, ValueError)
        self.assertEqual(str(error), 'original SaveCopy error')
        self.assertFalse(report['completed'])
        self.assertTrue(report['source_properties_exact'])
        self.assertTrue(report['artist_disk_exact'])
        self.assertEqual(calls.count('witness'), 2)

    def test_changed_source_or_cancel_never_claims_success(self):
        for kwargs in ({'changed': True}, {'result': {'CANCELLED'}}):
            value, error, report, calls = self.invoke(**kwargs)
            self.assertIsInstance(error, RuntimeError)
            self.assertFalse(report['completed'])
            self.assertEqual(calls.count('witness'), 2)

    def test_pre_read_mutation_blocks_directory_and_save(self):
        value, error, report, calls = self.invoke(pre_read_mutation=True)
        self.assertIsInstance(error, RuntimeError)
        self.assertFalse(report['completed'])
        self.assertNotIn('copy_attempted', report)
        self.assertFalse(any(isinstance(row, dict) for row in calls))

    def test_idle_accepts_normal_forearm_runtime_and_rejects_active_work(self):
        runtime = types.SimpleNamespace(_RUNTIME_REGISTERED=True, _SCENE_STATE_ACTIVE=True, _ERRORS={},
            _BUSY=False, _INITIALIZE_PENDING=False, _SCENE_CLEANUP_PENDING=False,
            _complete_runtime_lifecycle=lambda: None, _SESSION=None, PREVIEW_KEY='preview')
        bpy = types.SimpleNamespace(app=types.SimpleNamespace(timers=types.SimpleNamespace(is_registered=lambda _: False),
            is_job_running=lambda _: False), context=types.SimpleNamespace(mode='OBJECT',
                window_manager=types.SimpleNamespace(windows=[])), data=types.SimpleNamespace(objects=[], images=[]))
        with patch.dict(sys.modules, {'character_designer.forearm_twist': runtime}):
            self.assertIs(probe.idle(bpy), runtime)
            runtime._SESSION = {'calibration': True}
            with self.assertRaises(RuntimeError):
                probe.idle(bpy)
            runtime._SESSION = {}
            with self.assertRaises(RuntimeError):
                probe.idle(bpy)
            runtime._SESSION = None
            bpy.data.images = [types.SimpleNamespace(is_dirty=True)]
            with self.assertRaises(RuntimeError):
                probe.idle(bpy)
            bpy.data.images = []
            delta = types.SimpleNamespace(_RUNTIME={'live': True})
            with patch.dict(sys.modules, {'character_designer.delta_symmetry': delta}), self.assertRaises(RuntimeError):
                probe.idle(bpy)

    def test_no_prepare_seek_refresh_handler_mutation_or_import_time_bpy(self):
        tree = ast.parse(probe.Path(probe.__file__).read_text(encoding='utf8'))
        forbidden = {'frame_set', '_calculate_object', 'prepare', 'register', 'unregister',
                     'open_mainfile', 'defer_runtime', 'load_post', 'save_mainfile'}
        self.assertFalse({node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)} & forbidden)
        self.assertTrue(all(isinstance(node.func.value, ast.Name) and node.func.value.id == 'collections'
            for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'update'))
        self.assertNotIn('bpy', sys.modules)


if __name__ == '__main__':
    unittest.main()
