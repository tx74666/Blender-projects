"""Pure adapter admission, proof boundaries and unchanged timing; no bpy."""
import ast
import copy
import io
import sys
import types
import unittest
from unittest.mock import patch

import mesh_cache_current_gui_fps_probe_008 as probe
import test_mesh_cache_private_gui_fps_probe_005 as old_tests


def gui(count=2):
    value = old_tests.gui()
    value.update(schema=probe.GUI_SCHEMA, expected_mesh_count=count, **dict.fromkeys(probe.GUI_FLAGS, True))
    for row in value['frames']:
        row.pop('full69_geometry_exact')
        row.update(full_current_geometry_exact=True, mesh_count=count, current_layer_visibility_exact=True,
            visibility_exact=True, shader_exact=True, shader_sha256='d'*64)
    value['visibility_frames'] = [{'frame': row['frame'], 'exact': True, 'check_sha256': row['check_sha256']}
        for row in value['frames']]
    value['shader_frames'] = [{'frame': row['frame'], 'exact': True, 'sha256': row['shader_sha256'],
        'check_sha256': row['check_sha256']} for row in value['frames']]
    return value


class Tests(unittest.TestCase):
    def test_current_receipt_each_gate_and_dynamic_count(self):
        valid = gui()
        self.assertEqual(probe.validate_gui(valid, 777, valid['artifact']), {})
        for key in probe.GUI_FLAGS:
            with self.subTest(gate=key), self.assertRaises(RuntimeError):
                probe.validate_gui({**valid, key: False}, 777, valid['artifact'])
        for change in ({'schema': 'x.pc2-actor-artifact-gui-reopen/2'}, {'pid': 1}, {'completed': False},
            {'error': 'failure'}, {'cleanup_errors': ['failure']}, {'expected_mesh_count': True},
            {'expected_mesh_count': 0}, {'expected_mesh_count': 69}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                probe.validate_gui({**valid, **change}, 777, valid['artifact'])
        for mutate in (lambda x: x['frames'][0].update(mesh_count=69),
            lambda x: x['frames'][0].update(shader_exact=False),
            lambda x: x['frames'][0].update(visibility_exact=False),
            lambda x: x['frames'][0].update(current_layer_visibility_exact=False),
            lambda x: x['shader_frames'][0].update(sha256='e'*64),
            lambda x: x['visibility_frames'][0].update(check_sha256='e'*64),
            lambda x: x['shader_frames'][0].update(exact=False),
            lambda x: x['frames'][1].update(frame=1), lambda x: x['shader_frames'].pop(),
            lambda x: x['frames'][0].update(shader_sha256='x'*64)):
            bad = copy.deepcopy(valid)
            mutate(bad)
            with self.assertRaises(RuntimeError):
                probe.validate_gui(bad, 777, valid['artifact'])

    def test_private_classes_do_not_patch_frozen_namespaces(self):
        before = [dict(vars(module)) for module in (probe.original, probe.visibility, probe.core)]
        base, layer, extraction = probe.private_classes()
        self.assertEqual(extraction, probe.EXTRACTION)
        self.assertEqual(extraction['mesh_count_literal_changes'], 3)
        self.assertEqual(extraction['base_constructor_ast_sha256'], probe.visibility.BASE_CONSTRUCTOR_AST_SHA)
        self.assertIs(layer.__mro__[1], base)
        self.assertIs(layer.__init__.__globals__['_sealed_init'], base.__init__)
        self.assertEqual(base.__init__.__globals__['GUI_PATH'], probe.GUI_PATH)
        self.assertEqual(base.__init__.__globals__['CONTRACT_PATH'], probe.CONTRACT_PATH)
        self.assertIs(base.__init__.__globals__['validate_gui'], probe.validate_gui)
        self.assertIsNot(base.__init__.__globals__['importlib'], probe.original.importlib)
        with patch.object(probe.importlib, 'import_module', side_effect=lambda name, package: (name, package)):
            self.assertEqual(base.__init__.__globals__['importlib'].import_module('mesh_cache_artifact_contract_005'),
                ('mesh_cache_current_contract_008', None))
            self.assertEqual(base.__init__.__globals__['importlib'].import_module('gpu'), ('gpu', None))
        self.assertEqual(before, [dict(vars(module)) for module in (probe.original, probe.visibility, probe.core)])

    def test_exact_fixed_window_and_inherited_callbacks(self):
        self.assertEqual((probe.core.WARM_SECONDS, probe.core.MEASURE_SECONDS), (2., 16.))
        for name in ('tick', 'on_pre', 'on_post', 'on_draw', 'context_state', 'visibility_state', 'in_hot'):
            self.assertIs(getattr(probe.CacheProbe, name), getattr(probe.core.Probe, name))
        events = [(round(index*1e9/30), index % 30+1, 0.) for index in range(480)]
        self.assertEqual(probe.core.cadence(events)['count_per_fixed_window_hz'], 30.)
        self.assertEqual(probe.core.changed_draw_events([row for row in events for _ in (0, 1)]), events)
        self.assertEqual(probe.original.observed_advances(events)['minimum_unobserved_integer_frames'], 0)
        controller = object.__new__(probe.CacheProbe)
        controller.collecting, controller.start_ns, controller.end_ns = True, 2_000_000_000, 18_000_000_000
        self.assertFalse(controller.in_hot(1_999_999_999))
        self.assertTrue(controller.in_hot(2_000_000_000))
        self.assertTrue(controller.in_hot(17_999_999_999))
        self.assertFalse(controller.in_hot(18_000_000_000))

    def test_dynamic_hot_mesh_binding_has_no_io_or_shared_proofs(self):
        class Mesh(dict):
            type = 'MESH'
        class Objects(list):
            def __getitem__(self, key):
                return next(obj for obj in self if obj.name == key) if isinstance(key, str) else super().__getitem__(key)
        controller = object.__new__(probe.CacheProbe)
        controller.contract = {'objects': [{'target_name': str(i)} for i in range(2)]}
        controller.collecting = False
        controller.runtime = types.SimpleNamespace(RECORD_KEY='record', _ERRORS={})
        objects = Objects()
        for i in range(2):
            obj = Mesh()
            obj.name, obj.session_uid = str(i), i+1
            obj.as_pointer = lambda value=i: value+100
            obj.data = types.SimpleNamespace(as_pointer=lambda value=i: value+200, session_uid=i+300)
            obj.modifiers = [types.SimpleNamespace(as_pointer=lambda value=i: value+400,
                name='Cache', type='MESH_CACHE', filepath='//literal.pc2', factor=1., flip_axis=[False]*3)]
            objects.append(obj)
        controller.scene = types.SimpleNamespace(objects=objects)
        def forbidden(*_a, **_k):
            self.fail('hot proof or IO')
        controller.shared = types.SimpleNamespace(CACHE_SETTINGS={'factor': 1., 'flip_axis': [False]*3},
            scene_state=lambda *_: {'clip': [1, 30], 'sync': 'NONE'}, check_binding=forbidden,
            verify_external_pins=forbidden, verify_shader_resources=forbidden)
        # Test the composed005 binding implementation itself;006's unchanged
        # all-Base/topology guard already has targeted retained tests.
        probe._BaseProbe.capture_hot_bindings(controller)
        controller.collecting = True
        with patch.object(probe.Path, 'resolve', side_effect=AssertionError('hot resolve')), \
             patch.object(probe, 'pin', side_effect=AssertionError('hot hash')):
            probe._BaseProbe.assert_hot_bindings(controller)
            objects[0].modifiers[0].filepath = '//changed.pc2'
            with self.assertRaises(RuntimeError):
                probe._BaseProbe.assert_hot_bindings(controller)
            objects[0].modifiers[0].filepath = '//literal.pc2'
            objects.pop()
            with self.assertRaises(RuntimeError):
                probe._BaseProbe.assert_hot_bindings(controller)

    def test_endpoint_shader_resources_and_shared_baseline_view(self):
        controller = object.__new__(probe.CacheProbe)
        controller.scene, controller.contract = object(), {'objects': [{}, {}]}
        controller.config = {'mode': 'MATERIAL'}
        controller.area = types.SimpleNamespace(spaces=types.SimpleNamespace(active=
            types.SimpleNamespace(shading=types.SimpleNamespace(type='MATERIAL'))))
        controller.report, controller.closed = {}, False
        calls = []
        controller.shared = types.SimpleNamespace(verify_shader_resources=lambda *args: calls.append(args) or True)
        context = dict.fromkeys(probe.baseline.VIEW_FIELDS, 'same')
        context.update(perspective='PERSP', local_view=False)
        state = {'sha256': 'proof', 'components': {}, 'context': context}
        with patch.object(probe._VisibilityProbe, 'full_state', return_value=state):
            self.assertIs(controller.full_state(), state)
            self.assertEqual(controller.report['comparison_view'], probe.baseline.comparison_view(context))
            self.assertTrue(controller.report['current_material_resources_initial_exact'])
            self.assertNotIn('current_material_resources_after_exact', controller.report)
            controller.closed = True
            controller.full_state()
            self.assertTrue(controller.report['comparison_view_after_exact'])
            self.assertTrue(controller.report['current_material_saved_frame_after_exact'])
            self.assertEqual(len(calls), 2)
            for change in ({'perspective': 'CAMERA'}, {'lens_hex': 'changed'}):
                state['context'] = {**context, **change}
                with self.assertRaises(RuntimeError):
                    controller.full_state()
            state['context'] = context
            controller.shared.verify_shader_resources = lambda *_: False
            with self.assertRaises(RuntimeError):
                controller.full_state()
            controller.shared.verify_shader_resources = lambda *_: True
            controller.area.spaces.active.shading.type = 'SOLID'
            with self.assertRaises(RuntimeError):
                controller.full_state()

    def test_constructor_failure_closes_stream_and_does_not_take_sessions(self):
        stream = io.StringIO()
        def initialized(controller, config):
            controller.stream, controller.contract, controller.receipt = stream, {'objects': []}, {}
        with patch.object(probe._VisibilityProbe, '__init__', side_effect=initialized, autospec=True):
            with self.assertRaises(RuntimeError):
                probe.CacheProbe({})
        self.assertTrue(stream.closed)
        self.assertIsNone(probe.SESSION)
        self.assertIsNone(probe.core.SESSION)

    def test_post_constructor_exact_snapshot_sources_and_gui_provenance(self):
        seal = {'path': str(probe.SOURCE_SEAL_PATH), 'sha256': probe.SOURCE_SEAL_SHA, 'bytes': 1}
        snapshot = {'path': 'actual-snapshot.json', 'sha256': 'a'*64, 'bytes': 20}
        input_pin = {'path': 'actual-current.blend', 'sha256': 'b'*64, 'bytes': 200}
        gui_pin = {'path': 'actual-gui.json', 'sha256': 'c'*64, 'bytes': 30}
        source = {'path': 'current.py', 'sha256': 'd'*64, 'bytes': 10}
        data = {'expected_mesh_count': 2, 'current_snapshot_receipt': snapshot, 'current_input': input_pin}
        mutations = [lambda _: None,
            lambda c: c.receipt.update(current_source_seal={**seal, 'sha256': 'e'*64}),
            lambda c: c.receipt.update(current_sources={}),
            lambda c: c.contract.update(current_snapshot_receipt={**snapshot, 'bytes': 21})]
        for index, mutate in enumerate(mutations):
            stream = io.StringIO()
            def initialized(controller, config):
                controller.stream, controller.dependencies = stream, {}
                controller.contract = {'objects': [{}, {}], 'schema': 'x.current-pc2-artifact-contract/1',
                    'current_snapshot_receipt': snapshot}
                controller.receipt = {'schema': 'x.current-pc2-artifact/1', 'current_source_seal': seal,
                    'current_sources': {'current.py': source}, 'current_snapshot_receipt': snapshot,
                    'input_before': input_pin}
                controller.gui_pin = gui_pin
                controller.shared = types.SimpleNamespace(verify_sources=lambda _: {'current.py': source})
                controller.report = {'gui006': gui_pin, 'limits': []}
                controller.flush = lambda: None
                mutate(controller)
            with patch.object(probe._VisibilityProbe, '__init__', side_effect=initialized, autospec=True), \
                 patch.object(probe, 'pin', side_effect=lambda path: seal if path == probe.SOURCE_SEAL_PATH else source), \
                 patch.object(probe.core, 'load_pinned_json', return_value=(data, gui_pin)):
                if index:
                    with self.subTest(case=index), self.assertRaises(RuntimeError):
                        probe.CacheProbe({})
                    self.assertTrue(stream.closed)
                else:
                    controller = probe.CacheProbe({})
                    self.assertEqual(controller.report['current_input'], input_pin)
                    self.assertEqual(controller.report['current_gui'], gui_pin)
                    self.assertEqual(controller.dependencies['current_input_copy'], input_pin)
                    self.assertNotIn('gui006', controller.report)
                    stream.close()

    def test_finish_unwinds_only_own_session_on_original_failure(self):
        controller = object.__new__(probe.CacheProbe)
        controller.closed = False
        probe.SESSION = controller
        try:
            with patch.object(probe._VisibilityProbe, 'finish', side_effect=ValueError('original cleanup error')):
                with self.assertRaisesRegex(ValueError, 'original cleanup error'):
                    controller.finish()
            self.assertIsNone(probe.SESSION)
            foreign = object()
            probe.SESSION = foreign
            with patch.object(probe._VisibilityProbe, 'finish'):
                controller.finish()
            self.assertIs(probe.SESSION, foreign)
        finally:
            probe.SESSION = None

    def test_no_native_mutations_or_bpy_import_at_module_load(self):
        self.assertNotIn('bpy', sys.modules)
        tree = ast.parse(probe.Path(probe.__file__).read_text(encoding='utf8'))
        forbidden = {'open_mainfile', 'save_mainfile', 'save_as_mainfile', '_calculate_object', 'defer_runtime',
            'update_from_deformation', 'frame_set', 'animation_play', 'register_class'}
        self.assertFalse({node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)} & forbidden)


if __name__ == '__main__':
    unittest.main()
