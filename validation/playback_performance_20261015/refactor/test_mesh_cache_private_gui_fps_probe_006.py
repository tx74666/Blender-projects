"""Pure006 adapter checks; no bpy import, native process or receipt creation."""
import ast
import copy
import io
import sys
import types
import unittest
from unittest.mock import patch

import mesh_cache_private_gui_fps_probe_006 as probe
import test_mesh_cache_private_gui_fps_probe_005 as old_tests


def gui():
    value = old_tests.gui()
    value.update(schema='x.pc2-actor-artifact-gui-reopen/2', **dict.fromkeys(probe.VISIBILITY_FLAGS, True))
    for row in value['frames']:
        row['current_layer_visibility_exact'] = True
    value['visibility_frames'] = [{'frame': row['frame'], 'exact': True,
        'check_sha256': row['check_sha256']} for row in value['frames']]
    return value


class Native:
    def __init__(self, name, pointer):
        self.name = self.name_full = name
        self.pointer, self.session_uid = pointer, pointer+100
    def as_pointer(self):
        return self.pointer


class Object(Native):
    def __init__(self, name, pointer):
        super().__init__(name, pointer)
        self.hidden, self.selected = False, False
    def hide_get(self, *, view_layer):
        return self.hidden
    def select_get(self, *, view_layer):
        return self.selected


class Named(list):
    active = None
    def __getitem__(self, key):
        return next(row for row in self if row.name == key) if isinstance(key, str) else super().__getitem__(key)
    def get(self, key):
        return next((row for row in self if row.name == key), None)


def visibility_controller():
    controller = object.__new__(probe.CacheProbe)
    obj, backup = Object('Rig', 1), Object('Backup', 2)
    obj.selected, backup.hidden = True, True
    objects = Named([obj, backup])
    objects.active = obj
    layer = Native('Main', 3)
    layer.objects = objects
    master, child = Native('Master', 4), Native('Child', 5)
    master.children, child.children = [child], []
    master.hide_select, child.hide_select = False, True
    controller.scene = types.SimpleNamespace(view_layers=Named([layer]), collection=master)
    controller.window = types.SimpleNamespace(view_layer=layer)
    controller.collecting = False
    controller.contract = {'visibility': {'schema': 'character-designer.private-view-layer-state/1',
        'context_view_layer': 'Main', 'layers': [{'name': 'Main', 'active': 'Rig', 'objects': [
            {'name': 'Rig', 'hidden': False, 'selected': True},
            {'name': 'Backup', 'hidden': True, 'selected': False}]}],
        'collection_hide_select': [{'name': 'Master', 'hide_select': False}, {'name': 'Child', 'hide_select': True}]}}
    bpy = types.SimpleNamespace(context=types.SimpleNamespace(view_layer=layer))
    return controller, bpy, obj, backup, master, child


class ProbeTests(unittest.TestCase):
    def test_gui006_requires_real_schema_and_every_gate(self):
        valid = gui()
        self.assertEqual(probe.validate_gui(valid, 777, valid['artifact']), {})
        for key in probe.original.GUI_FLAGS+probe.VISIBILITY_FLAGS:
            with self.subTest(gate=key), self.assertRaises(RuntimeError):
                probe.validate_gui({**valid, key: False}, 777, valid['artifact'])
        for change in ({'schema': 'x.pc2-actor-artifact-gui-reopen/1'}, {'completed': False},
                       {'pid': 778}, {'cleanup_errors': ['error']}, {'error': 'failed'}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                probe.validate_gui({**valid, **change}, 777, valid['artifact'])
        for mutate in (lambda value: value['visibility_frames'].pop(),
            lambda value: value['visibility_frames'][1].update(frame=1),
            lambda value: value['visibility_frames'][0].update(exact=False),
            lambda value: value['visibility_frames'][0].update(check_sha256='e'*64),
            lambda value: value['frames'][0].update(current_layer_visibility_exact=False),
            lambda value: value['frames'][0].update(mesh_count=68),
            lambda value: value['frames'][0].update(check_sha256='x'*64)):
            bad = copy.deepcopy(valid)
            mutate(bad)
            with self.assertRaises(RuntimeError):
                probe.validate_gui(bad, 777, valid['artifact'])

    def test_constructor_is_sealed_private_and_router_is_local(self):
        original_globals = dict(vars(probe.original))
        constructor, digest = probe.sealed_constructor()
        self.assertEqual(digest, probe.BASE_CONSTRUCTOR_AST_SHA)
        scope = constructor.__globals__
        self.assertEqual(scope['__file__'], probe.__file__)
        self.assertIs(scope['validate_gui'], probe.validate_gui)
        self.assertEqual(scope['CONTRACT_PATH'], probe.CONTRACT_PATH)
        self.assertEqual(scope['GUI_PATH'], probe.GUI_PATH)
        self.assertIsNot(scope['importlib'], probe.original.importlib)
        with patch.object(probe.importlib, 'import_module', side_effect=lambda name, package: (name, package)):
            self.assertEqual(scope['importlib'].import_module('mesh_cache_artifact_contract_005'),
                             ('mesh_cache_artifact_contract_006', None))
            self.assertEqual(scope['importlib'].import_module('gpu'), ('gpu', None))
        self.assertEqual(dict(vars(probe.original)), original_globals)

    def test_clock_callbacks_are_exact_inherited_methods(self):
        for name in ('tick', 'on_pre', 'on_post', 'on_draw', 'context_state', 'visibility_state', 'in_hot'):
            self.assertIs(getattr(probe.CacheProbe, name), getattr(probe.core.Probe, name))
        self.assertEqual((probe.core.WARM_SECONDS, probe.core.MEASURE_SECONDS), (2., 16.))
        tree = ast.parse(probe.Path(probe.__file__).read_text(encoding='utf8'))
        forbidden = {'open_mainfile', 'save_mainfile', 'save_as_mainfile', '_calculate_object',
                     'defer_runtime', 'frame_set', 'animation_play', 'register_class'}
        self.assertFalse({node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)} & forbidden)

    def test_literal_hot_flags_and_topology_have_no_disk_or_shared_checker(self):
        controller, bpy, obj, backup, master, child = visibility_controller()
        controller.shared = types.SimpleNamespace(check_visibility=lambda *_a, **_k: self.fail('hot checker'))
        with patch.dict(sys.modules, bpy=bpy), \
             patch.object(probe.original.CacheProbe, 'capture_hot_bindings'), \
             patch.object(probe.original.CacheProbe, 'assert_hot_bindings'), \
             patch.object(probe.Path, 'resolve', side_effect=AssertionError('hot path IO')), \
             patch.object(probe, 'pin', side_effect=AssertionError('hot file proof')):
            controller.capture_hot_bindings()
            controller.collecting = True
            controller.assert_hot_bindings()
            mutations = (
                (backup, 'hidden', False), (obj, 'selected', False),
                (child, 'hide_select', False), (master, 'hide_select', True),
                (master, 'children', []), (controller.hot_layer.objects, 'active', backup),
                (obj, 'name_full', 'Renamed'), (controller.hot_layer, 'name', 'Changed'))
            for owner, name, value in mutations:
                before = getattr(owner, name)
                setattr(owner, name, value)
                with self.subTest(field=name), self.assertRaises(RuntimeError):
                    controller.assert_hot_bindings()
                setattr(owner, name, before)
            controller.hot_layer.objects.append(Object('New', 30))
            with self.assertRaises(RuntimeError):
                controller.assert_hot_bindings()
            controller.hot_layer.objects.pop()
            other = Native('Other', 31)
            controller.window.view_layer = other
            with self.assertRaises(RuntimeError):
                controller.assert_hot_bindings()

    def test_hot_handles_native_wrapper_alias_by_pointer(self):
        controller, bpy, *_ = visibility_controller()
        with patch.dict(sys.modules, bpy=bpy), \
             patch.object(probe.original.CacheProbe, 'capture_hot_bindings'), \
             patch.object(probe.original.CacheProbe, 'assert_hot_bindings'):
            controller.capture_hot_bindings()
            alias = Native('Main', controller.hot_layer_pointer)
            alias.objects = controller.hot_layer.objects
            bpy.context.view_layer = alias
            controller.assert_hot_bindings()

    def test_endpoints_check_all_layers_and_include_full_table(self):
        controller, *_ = visibility_controller()
        controller.closed, controller.report = True, {}
        calls = []
        controller.shared = types.SimpleNamespace(check_visibility=lambda *args, **kwargs:
            calls.append(kwargs) or {'exact': True, 'layers_checked': 2, 'context_view_layer': 'Main'})
        controller.witness = types.SimpleNamespace(object_hash=lambda value: repr(value))
        state = {'sha256': 'old', 'components': {}, 'context': {}}
        with patch.object(probe.original.CacheProbe, 'full_state', return_value=state):
            current = controller.full_state()
            self.assertEqual(calls, [{'all_layers': True}])
            self.assertTrue(controller.report['visibility_after_exact'])
            self.assertIn('source_view_layer_state', current['components'])
            self.assertIn('collection_hide_select', current['sha256'])
            controller.shared.check_visibility = lambda *_a, **_k: {'exact': False}
            with self.assertRaises(RuntimeError):
                controller.full_state()

    def test_post_constructor_failure_closes_exclusive_stream(self):
        stream = io.StringIO()
        def initialize(controller, config):
            controller.stream, controller.dependencies = stream, {}
        with patch.object(probe, '_sealed_init', side_effect=initialize), \
             patch.object(probe, 'pin', side_effect=ValueError('pin failed')):
            with self.assertRaises(ValueError):
                probe.CacheProbe({})
        self.assertTrue(stream.closed)

    def test_own_session_unwinds_even_when_inherited_finish_raises(self):
        controller = object.__new__(probe.CacheProbe)
        controller.closed = False
        probe.SESSION = controller
        try:
            with patch.object(probe.original.CacheProbe, 'finish', side_effect=ValueError('inherited')):
                with self.assertRaises(ValueError):
                    controller.finish()
            self.assertIsNone(probe.SESSION)
        finally:
            probe.SESSION = None

    def test_pure_import(self):
        self.assertNotIn('bpy', sys.modules)


if __name__ == '__main__':
    unittest.main()
