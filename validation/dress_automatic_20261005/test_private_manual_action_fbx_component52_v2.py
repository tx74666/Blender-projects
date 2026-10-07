"""Pure source controls only: no bpy, Native process, or output directory."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

sys.dont_write_bytecode = True
RUNNER = Path(__file__).with_name('verify_private_manual_action_fbx_component52_v2.py')
spec = importlib.util.spec_from_file_location('private_manual_v2_pure', RUNNER)
component = importlib.util.module_from_spec(spec)
spec.loader.exec_module(component)


class ClosureControls(unittest.TestCase):
    def test_dependency_direction_cycle_and_unused_orphan(self):
        users = {'Scene': set(), 'Rig': {'Scene', 'wire'}, 'Dress': {'Scene'},
                 'Body': {'Scene'}, 'wire': {'Rig'}, 'used_WGT': {'Rig'},
                 'orphan_WGT': set(), 'unreferenced_user': set()}
        reached = component.id_reference_closure({'Scene'}, users, {'Body', 'Dress', 'Rig', 'wire', 'used_WGT'})
        self.assertEqual(reached, {'Scene', 'Rig', 'Dress', 'Body', 'wire', 'used_WGT'})
        # Starting at a dependency cannot travel backwards to its users.
        self.assertEqual(component.id_reference_closure({'Dress'}, users), {'Dress'})
        self.assertEqual(component.id_reference_closure({'isolated_root'}, {}), {'isolated_root'})

    def test_required_missing_and_removed_reference_fail(self):
        for users in ({'Body': {'OtherScene'}}, {'used_WGT': set()}):
            with self.assertRaises(RuntimeError):
                component.id_reference_closure({'Scene', 'Rig'}, users, {'Body', 'used_WGT'})

    def test_projection_preserves_whole_Rest_Body_and_original(self):
        original = {'raw_named_weights_UV_Keys': {'Body': 'b', 'Dress': 'd', 'orphan_WGT': 'o'},
                    'named_Rest': 'all346', 'Body12': {'count': 12, 'eval_time': 0., 'channels': [('A', .25)]}}
        before = copy.deepcopy(original)
        result = component.snapshot_immutable_projection(original, ['Body', 'Dress'])
        self.assertEqual(result['raw_named_weights_UV_Keys'], {'Body': 'b', 'Dress': 'd'})
        self.assertEqual(result['named_Rest'], original['named_Rest'])
        self.assertEqual(result['Body12'], original['Body12'])
        result['Body12']['channels'].append(('Changed', 1.))
        self.assertEqual(original, before)
        for altered in (['Body', 'Ghost'], ['Body', 'Body'], ['Dress', 'Body']):
            with self.assertRaises(RuntimeError):
                component.snapshot_immutable_projection(original, altered)

    def test_precomputed_identity_scope_mutations_fail(self):
        expected = [('Object', 'Body', None), ('Object', 'Dress', None)]
        self.assertTrue(component.snapshot_mesh_scope(expected, list(reversed(expected))))
        for actual in (expected[:1], expected + [('Object', 'orphan_WGT', None)],
                       [('Object', 'Body', None), ('Object', 'Other', None)],
                       [('Object', 'Body', None), ('Object', 'Dress', 'other.blend')],
                       [('Object', 'Body', None), ('Mesh', 'Dress', None)],
                       [expected[0], expected[0], expected[1]]):
            with self.assertRaises(RuntimeError):
                component.snapshot_mesh_scope(expected, actual)


class OriginalProtectionControls(unittest.TestCase):
    def setUp(self):
        self.worker = NS(_curves=lambda action: [])
        self.slot = NS(handle=1, identifier='OBCoshaRig', target_id_type='OBJECT')
        self.action = NS(name='Original', use_fake_user=False, is_action_layered=True, slots=[self.slot])
        self.keys = NS(eval_time=0., key_blocks=[NS(name='Basis', value=0.), NS(name='Detail', value=.25)])
        self.bpy = NS(data=NS(actions={'Original': self.action}, materials={}, images={},
                             objects={'Cosha': NS(data=NS(shape_keys=self.keys))}))
        self.names = {'actions': ['Original'], 'materials': [], 'images': [], 'meshes': []}
        self.q = NS(digest=lambda value: repr(value), rest_content=lambda rig: {'unchanged': True})

    def test_original_six_Action_identity_flags(self):
        baseline = component.asset_state(self.bpy, self.worker, self.names)
        for obj, field, value in ((self.action, 'name', 'Renamed'), (self.action, 'use_fake_user', True),
                (self.action, 'is_action_layered', False), (self.slot, 'handle', 2),
                (self.slot, 'identifier', 'OBOther'), (self.slot, 'target_id_type', 'KEY')):
            with self.subTest(field=field):
                old = getattr(obj, field)
                setattr(obj, field, value)
                self.assertNotEqual(component.asset_state(self.bpy, self.worker, self.names), baseline)
                setattr(obj, field, old)
                self.assertEqual(component.asset_state(self.bpy, self.worker, self.names), baseline)

    def test_original_four_Body12_channels(self):
        baseline = component.immutable_state(self.bpy, self.q, None, self.names)
        for obj, field, value in ((self.keys, 'eval_time', 1.), (self.keys.key_blocks[1], 'name', 'Changed'),
                                  (self.keys.key_blocks[1], 'value', .5)):
            with self.subTest(field=field):
                old = getattr(obj, field)
                setattr(obj, field, value)
                self.assertNotEqual(component.immutable_state(self.bpy, self.q, None, self.names), baseline)
                setattr(obj, field, old)
                self.assertEqual(component.immutable_state(self.bpy, self.q, None, self.names), baseline)
        self.keys.key_blocks.append(NS(name='Extra', value=0.))
        self.assertNotEqual(component.immutable_state(self.bpy, self.q, None, self.names), baseline)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(json.dumps({'source_only': True, 'tests': result.testsRun, 'passed': result.wasSuccessful(),
                      'original_Action_Body_mutation_controls': 10, 'Native_started': False}), flush=True)
    raise SystemExit(0 if result.wasSuccessful() else 1)
