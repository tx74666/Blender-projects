"""Pure cache FPS admission/cadence checks; no bpy, native process or receipt."""
import ast
import copy
import sys
import types
import unittest
from unittest.mock import patch

import mesh_cache_private_gui_fps_probe_005 as probe


def config():
    return {'expected_pid': 777, 'private_blend': 'private.blend', 'private_sha256': 'a'*64,
            'artist': 'artist.blend', 'gui_report': 'gui.json', 'gui_report_sha256': 'b'*64,
            'mode': 'SOLID', 'report': 'unused.json'}


def gui():
    receipt = {'schema': 'x.pc2-actor-artifact-gui-reopen/1', 'completed': True, 'pid': 777,
        'cleanup_errors': [], 'artifact': {'path': 'private.blend', 'sha256': 'a'*64, 'bytes': 1},
        'frames': [{'frame': frame, 'full69_geometry_exact': True, 'mesh_count': 69,
                    'check_sha256': 'c'*64} for frame in range(1, 31)],
        'callbacks_after_natural_settle': {}}
    receipt.update(dict.fromkeys(probe.GUI_FLAGS, True))
    return receipt


class ProbeTests(unittest.TestCase):
    def test_exact_cache_only_config(self):
        self.assertEqual(probe.validate_config(config(), 777), config())
        changes = ({'expected_pid': 778}, {'expected_pid': True}, {'private_sha256': 'x'*64},
                   {'mode': 'WIREFRAME'}, {'gui_report': ''}, {'gui_report_sha256': 'B'*64},
                   {'kind': 'baseline'}, {'allow_fixed_baseline': True})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                probe.validate_config({**config(), **change}, 777)

    def test_real_cache_gui_scope_and_each_gate(self):
        valid = gui()
        self.assertEqual(probe.validate_gui(valid, 777, valid['artifact']), {})
        for key in probe.GUI_FLAGS:
            bad = copy.deepcopy(valid)
            bad[key] = False
            with self.subTest(gate=key), self.assertRaises(RuntimeError):
                probe.validate_gui(bad, 777, valid['artifact'])
        for change in ({'pid': 778}, {'completed': False}, {'error': 'failed'},
                       {'schema': 'x.independent-artifact-gui-reopen/1'}, {'cleanup_errors': ['failed']}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                probe.validate_gui({**valid, **change}, 777, valid['artifact'])
        for mutate in (lambda value: value['frames'].pop(),
                       lambda value: value['frames'][0].update(mesh_count=68),
                       lambda value: value['frames'][1].update(frame=1),
                       lambda value: value['frames'][0].update(check_sha256='x'*64),
                       lambda value: value['frames'][0].update(full69_geometry_exact=False)):
            bad = copy.deepcopy(valid)
            mutate(bad)
            with self.assertRaises(RuntimeError):
                probe.validate_gui(bad, 777, valid['artifact'])

    def test_exact_fixed_window_event_math_and_no_draw_double_count(self):
        events = [(round(index*1e9/30), index % 30+1, 0.) for index in range(480)]
        self.assertEqual(probe.core.cadence(events)['count_per_fixed_window_hz'], 30.)
        self.assertEqual(probe.core.changed_draw_events([row for row in events for _ in (0, 1)]), events)
        advances = probe.observed_advances(events)
        self.assertEqual(advances['minimum_unobserved_integer_frames'], 0)
        self.assertEqual(advances['observed_wraps'], 15)
        self.assertEqual(advances['forward_modulo30_step_histogram'], {1: 479})
        controller = object.__new__(probe.CacheProbe)
        controller.collecting, controller.start_ns, controller.end_ns = True, 2_000_000_000, 18_000_000_000
        self.assertFalse(controller.in_hot(1_999_999_999))
        self.assertTrue(controller.in_hot(2_000_000_000))
        self.assertTrue(controller.in_hot(17_999_999_999))
        self.assertFalse(controller.in_hot(18_000_000_000))

    def test_observed_gaps_repeat_wrap_and_ambiguous_full_loop(self):
        rows = [(0, 29, 0.), (1, 30, 0.), (2, 2, 0.), (3, 2, 0.), (4, 5, 0.)]
        result = probe.observed_advances(rows)
        self.assertEqual(result['observed_wraps'], 1)
        self.assertEqual(result['repeated_integer_tokens'], 1)
        self.assertEqual(result['minimum_unobserved_integer_frames'], 3)
        self.assertEqual(result['forward_modulo30_step_histogram'], {0: 1, 1: 1, 2: 1, 3: 1})
        self.assertEqual(probe.observed_advances([])['transitions'], 0)
        self.assertEqual(probe.observed_advances([(0, 1, 0.), (1, 1, 0.)])['minimum_unobserved_integer_frames'], 0)
        self.assertTrue(probe.observed_advances([(0, 1, 0.), (1, 31, 0.)])['outside_clip_transitions'])

    def test_only_sealed_timing_callbacks_are_inherited(self):
        for name in ('tick', 'on_pre', 'on_post', 'on_draw', 'context_state', 'visibility_state'):
            self.assertIs(getattr(probe.CacheProbe, name), getattr(probe.core.Probe, name))
        self.assertEqual(probe.core.WARM_SECONDS, 2.)
        self.assertEqual(probe.core.MEASURE_SECONDS, 16.)
        self.assertNotEqual(probe.CacheProbe.__init__, probe.core.Probe.__init__)
        self.assertNotEqual(probe.CacheProbe.full_state, probe.core.Probe.full_state)
        tree = ast.parse(probe.Path(probe.__file__).read_text(encoding='utf8'))
        forbidden = {'open_mainfile', 'save_mainfile', 'save_as_mainfile', '_calculate_object',
                     'defer_runtime', 'update_from_deformation', 'animation_play', 'frame_set'}
        self.assertFalse({node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)} & forbidden)
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                             and node.func.attr == '__init__' for node in ast.walk(tree)))

    def test_cache_health_has_no_owner_fallback_and_no_hot_file_work(self):
        controller = object.__new__(probe.CacheProbe)
        controller.collecting = False
        controller.runtime = types.SimpleNamespace(RECORD_KEY='record')
        controller.scene = types.SimpleNamespace(objects=[types.SimpleNamespace(type='MESH', __contains__=lambda _: False)])
        class Mesh(dict):
            type = 'MESH'
        controller.scene.objects = [Mesh()]
        calls = []
        controller.contract, controller.receipt = {}, {}
        controller.shared = types.SimpleNamespace(check_binding=lambda *_: {'healthy': True, 'meshes': 69},
            verify_external_pins=lambda *_: calls.append('disk'))
        with patch.object(probe.core.Probe, 'assert_runtime'):
            controller.assert_runtime()
            self.assertEqual(calls, ['disk'])
            controller.collecting = True
            with self.assertRaises(RuntimeError):
                controller.assert_runtime()
            controller.collecting = False
            controller.scene.objects[0]['record'] = 1
            with self.assertRaises(RuntimeError):
                controller.assert_runtime()
        self.assertEqual(calls, ['disk'])

    def test_hot_health_only_reads_binding_record_and_errors(self):
        class Mesh(dict):
            type = 'MESH'
        class Objects(list):
            def __getitem__(self, key):
                return next(obj for obj in self if obj.name == key) if isinstance(key, str) else super().__getitem__(key)
        controller = object.__new__(probe.CacheProbe)
        controller.collecting = False
        controller.contract = {'objects': [{'target_name': str(i)} for i in range(69)]}
        controller.runtime = types.SimpleNamespace(RECORD_KEY='record', _ERRORS={})
        objects = Objects()
        for index in range(69):
            obj = Mesh()
            obj.name, obj.session_uid = str(index), index+1
            obj.as_pointer = lambda value=index: value+100
            obj.data = types.SimpleNamespace(as_pointer=lambda value=index: value+200, session_uid=index+300)
            obj.modifiers = [types.SimpleNamespace(as_pointer=lambda value=index: value+400,
                name='Cache', type='MESH_CACHE', filepath='//literal.pc2', factor=1., flip_axis=[False]*3)]
            objects.append(obj)
        controller.scene = types.SimpleNamespace(objects=objects)
        controller.shared = types.SimpleNamespace(CACHE_SETTINGS={'factor': 1., 'flip_axis': [False]*3},
            scene_state=lambda *_: {'clip': [1, 30], 'sync': 'NONE'},
            check_binding=lambda *_: self.fail('hot filesystem resolving binding helper'),
            verify_external_pins=lambda *_: self.fail('hot disk work'))
        controller.capture_hot_bindings()
        controller.collecting = True
        controller.config = {'expected_pid': probe.os.getpid()}
        controller.loaded_filepath_literal = '/already-verified-private.blend'
        controller.area = types.SimpleNamespace(type='VIEW_3D')
        controller.screen = types.SimpleNamespace(areas=[controller.area])
        controller.window = types.SimpleNamespace(screen=controller.screen, scene=controller.scene)
        bpy = types.SimpleNamespace(data=types.SimpleNamespace(filepath=controller.loaded_filepath_literal))
        with patch.dict(sys.modules, bpy=bpy), patch.object(probe.Path, 'resolve', side_effect=AssertionError('hot Path.resolve')):
            controller.assert_owned()
            objects[-1].modifiers[0].filepath = '//changed.pc2'
            with self.assertRaises(RuntimeError):
                controller.assert_owned()
            objects[-1].modifiers[0].filepath = '//literal.pc2'
            controller.runtime._ERRORS['failure'] = 'standard error'
            with self.assertRaises(RuntimeError):
                controller.assert_owned()

    def test_gpu_context_is_optional_and_captured_as_reported(self):
        platform = types.SimpleNamespace(renderer_get=lambda: 'Actual renderer', vendor_get=lambda: 'Actual vendor',
                                         version_get=lambda: 'Actual driver')
        with patch.object(probe.importlib, 'import_module', return_value=types.SimpleNamespace(platform=platform)):
            self.assertEqual(probe.gpu_context_info()['renderer'], 'Actual renderer')
            del platform.vendor_get
            self.assertEqual(probe.gpu_context_info()['vendor'], 'unknown')
        with patch.object(probe.importlib, 'import_module', side_effect=ImportError('unavailable')):
            result = probe.gpu_context_info()
            self.assertEqual(result['renderer'], 'unknown')
            self.assertEqual(result['unavailable']['platform'], 'ImportError')

    def test_finish_unwinds_own_session_after_inherited_failure(self):
        controller = object.__new__(probe.CacheProbe)
        controller.closed, controller.collecting, controller.report = False, True, {}
        controller.post_events, controller.draw_events = [], []
        probe.SESSION = controller
        with patch.object(probe.core.Probe, 'finish', side_effect=ValueError('original')):
            with self.assertRaises(ValueError):
                controller.finish()
        self.assertIsNone(probe.SESSION)
        self.assertFalse(controller.collecting)
        self.assertIn('observed_frame_advances', controller.report)

    def test_pure_import(self):
        self.assertNotIn('bpy', sys.modules)


if __name__ == '__main__':
    unittest.main()
