"""Pure ownership/visit/Base-read regressions; not native or receipt acceptance."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_cache_view_layer_adapter_006 as adapter
import mesh_cache_actor_full30_006 as full
import mesh_cache_artifact_contract_006 as contract
import mesh_cache_artifact_assembler_006 as writer


class Obj:
    type = 'MESH'
    def __init__(self, name, pointer):
        self.name = self.name_full = name
        self.pointer, self.hidden, self.selected = pointer, {}, {}
    def as_pointer(self):
        return self.pointer
    def hide_get(self, *, view_layer):
        return self.hidden[view_layer]
    def select_get(self, *, view_layer):
        return self.selected[view_layer]


class Members(dict):
    active = None
    def __iter__(self):
        return iter(self.values())


class Layers(list):
    def __getitem__(self, key):
        return next(item for item in self if item.name == key) if isinstance(key, str) else super().__getitem__(key)


class Layer:
    def __init__(self, name, objects, active):
        self.name = name
        self.objects = Members((obj.name_full, obj) for obj in objects)
        self.objects.active = active
        for obj in objects:
            obj.hidden[self] = obj.selected[self] = False


class Collection:
    def __init__(self, name, pointer, children=()):
        self.name_full, self.pointer, self.children, self.hide_select = name, pointer, list(children), False
    def as_pointer(self):
        return self.pointer


class VisibilityTests(unittest.TestCase):
    def fixture(self):
        obj = Obj('Rig', 1)
        layers = Layers([Layer('Main', [obj], obj), Layer('Other', [obj], None)])
        root = Collection('Scene Collection', 2, [Collection('Child', 3)])
        scene = SimpleNamespace(view_layers=layers, collection=root)
        state = {'schema': 'character-designer.private-view-layer-state/1', 'context_view_layer': 'Main',
            'layers': [{'name': layer.name, 'active': 'Rig' if layer.name == 'Main' else None,
                        'objects': [{'name': 'Rig', 'hidden': False, 'selected': False}]} for layer in layers],
            'collection_hide_select': [{'name': 'Child', 'hide_select': False}, {'name': 'Scene Collection', 'hide_select': False}]}
        native = SimpleNamespace(context=SimpleNamespace(scene=scene, view_layer=layers[0]))
        return scene, state, native, obj

    def test_embedded_master_and_all_layer_guards(self):
        scene, state, native, obj = self.fixture()
        with patch.dict(sys.modules, {'bpy': native}):
            self.assertTrue(adapter.check_visibility(scene, state)['exact'])
            obj.hidden[scene.view_layers['Other']] = True
            self.assertEqual(adapter.check_visibility(scene, state, False)['layers_checked'], 1)
            with self.assertRaisesRegex(RuntimeError, 'Other'):
                adapter.check_visibility(scene, state, True)
            obj.hidden[scene.view_layers['Other']] = False
            scene.collection.hide_select = True
            with self.assertRaisesRegex(RuntimeError, 'selectability'):
                adapter.check_visibility(scene, state)

    def test_context_and_ambiguous_collection_names_fail_without_healing(self):
        scene, state, native, obj = self.fixture()
        with patch.dict(sys.modules, {'bpy': native}):
            native.context.view_layer = scene.view_layers['Other']
            with self.assertRaisesRegex(RuntimeError, 'context View Layer'):
                adapter.check_visibility(scene, state)
            self.assertEqual(native.context.view_layer.name, 'Other')
            native.context.view_layer = scene.view_layers['Main']
            scene.collection.children.append(Collection('Child', 4))
            with self.assertRaisesRegex(RuntimeError, 'Ambiguous'):
                adapter.check_visibility(scene, state)

    def test_geometry_observer_counts_consecutive_same_frame_visits(self):
        tree = ast.parse((HERE/'mesh_cache_actor_full30_006.py').read_text())
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        node = next(node for node in main.body if isinstance(node, ast.FunctionDef) and node.name == 'geometry')
        outer = ast.parse('def factory(adapter, report, bpy, original_geometry, visibility, first_pointer=None):\n pass').body[0]
        outer.body = [node, ast.Return(ast.Name(id='geometry', ctx=ast.Load()))]
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[outer], type_ignores=[])), '<observer-regression>', 'exec'), namespace)
        a, b, clone_a, clone_b = Obj('A', 1), Obj('B', 2), Obj('A Copy', 3), Obj('B Copy', 4)
        scene = SimpleNamespace(frame_current=1, frame_subframe=0.)
        session = SimpleNamespace(closed=False, scene=scene, object_map={a: clone_a, b: clone_b})
        report, outputs = {'visibility_contract': {}, 'visibility_replay': []}, []
        observer = namespace['factory'](SimpleNamespace(session=session), report,
            SimpleNamespace(context=SimpleNamespace(scene=scene)), lambda obj, reverse: outputs.append(obj.name),
            SimpleNamespace(check_visibility=lambda *args, **kwargs: {'exact': True}))
        visits = [frame for block, frames in full.previous.runner.replay_visits() for frame in frames]
        for frame in visits:
            scene.frame_current = frame
            observer(clone_a, {})
            observer(clone_b, {})
        self.assertEqual([row['frame'] for row in report['visibility_replay']], visits)
        self.assertEqual(len(outputs), 300)

    def test_post_build_copy_failure_closes_session_before_return(self):
        calls, report = [], {}
        session = SimpleNamespace(close=lambda: calls.append('close'))
        module = SimpleNamespace(build_isolated_scene=lambda source: session)
        seal = adapter.sealed_copy({})[1]
        def fail(session):
            raise ValueError('copy readback fails')
        with patch.object(adapter, 'sealed_copy', return_value=(fail, seal)):
            controller = adapter.VisibilityAdapter(module, report).install()
            with self.assertRaisesRegex(ValueError, 'copy readback'):
                module.build_isolated_scene(object())
            self.assertEqual(calls, ['close'])
            self.assertIsNone(controller.session)
            controller.close()
            self.assertTrue(report['visibility_hook_restored'])

    def test_missing_actual006_receipt_refuses_before_native(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(full30_report=str(Path(directory)/'missing.json'), full30_sha256='0'*64)
            with self.assertRaises(FileNotFoundError):
                writer.main(args, {})
            self.assertNotIn('bpy', sys.modules)


if __name__ == '__main__':
    unittest.main()
