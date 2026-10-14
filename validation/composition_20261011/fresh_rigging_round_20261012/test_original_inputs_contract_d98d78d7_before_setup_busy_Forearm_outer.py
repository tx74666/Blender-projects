"""Portable Original20 boundaries; no solver or full native proof is simulated.

These tests execute selected actual product functions, plus the real pure
wire validator. Native admission is separately required in isolated Blender.
"""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / 'addons' / 'character_designer' / 'unity_animation_original_inputs.py'


def functions(*names, **extra):
    tree = ast.parse(PRODUCT.read_text(encoding='utf-8-sig'))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(selected) != len(names): raise AssertionError('A tested production entry is missing.')
    space = dict(math=math, struct=struct, json=json, hashlib=hashlib, Path=Path,
        PUBLICATION_SCHEMA='cdesigner.controls-only-publication/1', **extra)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(PRODUCT), 'exec'), space)
    return space


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def wire():
    path = ROOT / 'addons' / 'character_designer' / 'animation_rigging_contract.py'
    spec = importlib.util.spec_from_file_location('original20_pure_wire', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class NativeId:
    def __init__(self, name, pointer): self.name, self.pointer = name, pointer
    def as_pointer(self): return self.pointer


def packets():
    identity = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]
    old = dict(schema='packet', units='meters', coordinate='unity-left-handed', matrixLayout='row-major',
        targetGuid='12' * 16, targetAssetPath='Assets/Cosha.prefab', projectId='34' * 16, duration=0.9666666984558105,
        bones=[dict(name='root', path='root', parent=-1, humanRole='', weighted=False, restSource='hierarchy', rest=identity),
               dict(name='tip', path='root/tip', parent=0, humanRole='RightHand', weighted=True, restSource='bindpose', rest=list(identity))])
    new = deepcopy(old); new['duration'] = 0.9666667
    old['bones'][1]['rest'][0] = 0.7823156714439392
    new['bones'][1]['rest'][0] = 0.7823157
    return old, new


def capture_fixture(contract):
    capture = dict(schema=contract.SCHEMA, targetGuid='12' * 16, targetDependencyHash='23' * 16,
        newActionId='db32bc9214884033a9185a8706ec01bc', sourceMode='prefab-default', bindingsSha256='',
        duration=0.9666667, sampleRate=60, loopTime=True, previewEnabled=True, sourceTimeMode='normalized-base-phase',
        targetLayoutSha256='ab' * 32, baseControllerGuid='34' * 16, baseControllerDependencyHash='45' * 16,
        avatarDependencyHash='56' * 16)
    capture['bindings'] = []
    for side in ('Right', 'Left'):
        capture['bindings'].append(dict(rigPath='CoshaRig/Rig1', rigWeight=0., constraintPath='CoshaRig/Rig1/' + side + 'Arm',
            rootPath='CoshaRig/' + side + 'Upper',
            midPath='CoshaRig/' + side + 'Upper/' + side + 'Mid',
            tipPath='CoshaRig/' + side + 'Upper/' + side + 'Mid/' + side + 'Hand',
            targetPath='CoshaRig/Rig1/' + side + 'Target', targetParentPath='CoshaRig/Rig1',
            hintPath='CoshaRig/Rig1/' + side + 'Hint', hintParentPath='CoshaRig/Rig1', constraintWeight=1.,
            targetPositionWeight=1., targetRotationWeight=1., hintWeight=1.,
            maintainTargetPositionOffset=False, maintainTargetRotationOffset=False))
    capture['bindings'][1]['targetParentPath'] = capture['bindings'][0]['tipPath']
    capture['bindings'][1]['targetPath'] = capture['bindings'][1]['targetParentPath'] + '/LeftTarget'
    capture['bindingsSha256'] = contract.bindings_digest(capture['bindings'])
    times = contract._clock(capture)[3]
    matrix = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]
    capture['frames'] = [dict(time=time, controls=[dict(targetPosition=[0., 0., 0.], targetRotation=[0., 0., 0., 1.],
        hintPosition=[0., 1., 0.], targetParentRoot=matrix, hintParentRoot=matrix) for _side in range(2)]) for time in times]
    return contract.validate_capture(capture)


class OriginalInputsContractTests(unittest.TestCase):
    def test_float32_lineage_accepts_serialization_rounding_and_rejects_other_ancestry(self):
        code = functions('_require', '_f32', '_lineage', native=SimpleNamespace(_digest=digest))
        old, new = packets()
        self.assertEqual(len(code['_lineage'](old, new)), 64)
        for mutation in ('parent', 'rest', 'targetGuid'):
            altered = deepcopy(new)
            if mutation == 'parent': altered['bones'][1]['parent'] = -1
            elif mutation == 'rest': altered['bones'][1]['rest'][0] += 0.001
            else: altered['targetGuid'] = 'fe' * 16
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): code['_lineage'](old, altered)

    def test_body30_and_inputs60_are_independent_normalized_clocks(self):
        code = functions('_require', '_f32', 'preview_base_timing', validate_reference=lambda session: None)
        body_duration, input_duration = packets()[0]['duration'], packets()[1]['duration']
        self.assertNotEqual(body_duration, input_duration)
        session = dict(capture={'duration': input_duration, 'sampleRate': 60}, scene_clock=[24, 1.], scene_start=10)
        reference = dict(action=NativeId('old Body', 1), slot=7, duration=body_duration, sample_rate=30., start=1.)
        action, slot, timing = code['preview_base_timing'](session, reference)
        self.assertIs(action, reference['action']); self.assertEqual(slot, 7)
        self.assertEqual(timing['end'], 1. + body_duration * 30.)
        middle = 1. + 0.5 * body_duration * 30.
        self.assertAlmostEqual(10. + (middle - timing['begin']) * timing['scale'], 10. + 0.5 * input_duration * 24., places=12)

    def test_role_boundary_refuses_body_as_input_and_base_tweak(self):
        # The native pair proof is not faked as a pass: only this subsequent
        # Action/slot/role boundary is isolated; native pair validation is external.
        pair = dict(rig=NativeId('Rig', 1), scene=NativeId('Scene', 2), source_action=NativeId('Source20', 3), source_slot=7,
            custom_action=NativeId('Custom20', 4), custom_slot=8, capture={}, work_item_id='31' * 16, packet={'sha256': 'ab' * 32})
        session = dict(original_inputs=pair, rig=pair['rig'], scene=pair['scene'], base_action=pair['source_action'], base_slot=7,
            input_action=pair['custom_action'], input_slot=8, capture={}, work_item_id=pair['work_item_id'],
            source_packet_sha256=pair['packet']['sha256'], source_read_only=False, edit_role='RIGGING', tweak_enabled=True)
        code = functions('_require', '_same', 'validate_session', _pair_validate=lambda value, files=False: value)
        self.assertIs(code['validate_session'](session), pair)
        for replacement in ({'base_action': NativeId('old Body', 9)}, {'input_slot': 9}, {'edit_role': 'BASE'}, {'source_read_only': True}):
            wrong = dict(session, **replacement)
            with self.subTest(replacement=replacement), self.assertRaises(ValueError): code['validate_session'](wrong)

    def publication_environment(self):
        contract = wire(); capture = capture_fixture(contract)
        samples = [dict(time=f['time'], controls=[{k: c[k] for k in contract.LOCAL_FIELDS} for c in f['controls']]) for f in capture['frames']]
        dto = contract.build_export(capture, samples, source_packet_sha256='ab' * 32, work_item_id='31' * 16,
            new_action_id=capture['newActionId'], source_action='Source20', source_action_slot=7, target_input_action='Custom20', target_input_action_slot=8)
        pair = dict(capture=capture, source_uuid='9f' * 16, prepared_report={'path': 'prepare.json', 'sha256': 'cd' * 32},
            body_action=NativeId('old Body', 9), body_slot=11, body_source=NativeId('old Source', 10), body_source_slot=12,
            body_clock=30., body_start=1., body_duration=packets()[0]['duration'], clock_certificate={'path': 'clock.json', 'sha256': 'ef' * 32})
        code = functions('_require', '_sha', '_pin', 'publish_inputs', _active=lambda context, rig: {},
            validate_session=lambda session, files=False: pair, capture_inputs=lambda context, session: dto)
        return code, contract, capture, dto, pair

    def test_publication_uses_real_wire14_full_grid_and_distinct_source_target_roles(self):
        code, contract, capture, expected, pair = self.publication_environment()
        with tempfile.TemporaryDirectory() as folder:
            pins = code['publish_inputs'](None, None, Path(folder) / 'controls.json')
            dto = json.loads(Path(pins['return']['path']).read_text(encoding='utf-8'))
            publication = json.loads(Path(pins['publication']['path']).read_text(encoding='utf-8'))
            self.assertEqual(set(dto), set(contract.EXPORT_FIELDS)); self.assertEqual(len(dto), 14)
            self.assertEqual(dto, expected); self.assertEqual([f['time'] for f in dto['frames']], [f['time'] for f in capture['frames']])
            self.assertEqual(dto['frames'][-1]['time'], 0.9666667); self.assertEqual(len(dto['frames']), 59)
            self.assertTrue(all(set(c) == set(contract.LOCAL_FIELDS) for f in dto['frames'] for c in f['controls']))
            self.assertEqual(publication['controlChannelCount'], 20); self.assertTrue(publication['completed'])
            self.assertEqual(publication['sourceActionId'], pair['source_uuid'])
            self.assertEqual(publication['targetInputActionId'], capture['newActionId'])
            self.assertNotEqual(publication['sourceActionId'], publication['targetInputActionId'])
            self.assertTrue(all(publication[k] is True for k in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly')))
            self.assertEqual(publication['returnSha256'], pins['return']['sha256'])

    def test_publication_never_overwrites_and_failed_readback_never_returns_success(self):
        code, _contract, _capture, _dto, _pair = self.publication_environment()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'controls.json'; path.write_bytes(b'protected existing content')
            with self.assertRaises(ValueError): code['publish_inputs'](None, None, path)
            self.assertEqual(path.read_bytes(), b'protected existing content')
            path.unlink(); real_pin = code['_pin']
            def fail_publication_pin(name, digest):
                if Path(name).stem.endswith('.publication'): raise RuntimeError('Injected publication readback failure')
                return real_pin(name, digest)
            with mock.patch.dict(code, _pin=fail_publication_pin), self.assertRaises(RuntimeError): code['publish_inputs'](None, None, path)
            self.assertFalse(path.exists()); self.assertFalse(path.with_name('controls.publication.json').exists())


    def metadata_environment(self):
        class Id:
            def __init__(self, name, library=None):
                object.__setattr__(self, 'name', name)
                object.__setattr__(self, 'library', library)
            def __setattr__(self, name, value):
                raise AssertionError('A referenced native ID must remain read-only.')
            def items(self):
                raise AssertionError('Native ID contents must not be traversed or rewritten.')
        class Armature(Id):
            pass
        class Group:
            def __init__(self, values): self.values = values
            def items(self): return self.values.items()
        class Array:
            def __init__(self, values): self.values = values
            def to_list(self): return list(self.values)
        bpy = SimpleNamespace(types=SimpleNamespace(ID=Id, Armature=Armature))
        forbidden = mock.Mock(side_effect=AssertionError('Digest must not use the recovery encoder.'))
        code = functions('_require', '_reference_headers', '_properties_digest', bpy=bpy,
            native=SimpleNamespace(_digest=digest), composition=SimpleNamespace(_encode=forbidden))
        return code, bpy, Armature, Group, Array, forbidden

    def test_body_digest_reads_existing_armature_reference_without_ownership_or_ID_writes(self):
        code, bpy, Armature, Group, Array, forbidden = self.metadata_environment()
        original = Armature('Original Main data')
        metadata = {'old_motion_refs': Group({'data': original, 'values': Array([1., 2., 3.])}),
            'flags': [True, None, 'unchanged']}
        before = (original.name, original.library, list(metadata), metadata['old_motion_refs'].values['data'])
        actual = code['_properties_digest'](metadata)
        self.assertEqual(len(actual), 64)
        self.assertEqual(code['_properties_digest'](metadata), actual)
        self.assertEqual(before, (original.name, original.library, list(metadata), metadata['old_motion_refs'].values['data']))
        forbidden.assert_not_called()
        # Execute the actual unchanged transaction encoder separately: read-only
        # digest acceptance must never promote Armature ownership into recovery.
        recovery = ROOT / 'addons' / 'character_designer' / 'animation_composition.py'
        tree = ast.parse(recovery.read_text(encoding='utf-8-sig'))
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_encode']
        self.assertEqual(len(selected), 1)
        namespace = {'bpy': bpy}
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(recovery), 'exec'), namespace)
        refs = {}
        with self.assertRaisesRegex(ValueError, 'Armature ownership'):
            namespace['_encode']({'original': original}, refs)
        self.assertEqual(refs, {})

    def test_body_digest_changes_for_values_and_ID_headers_and_rejects_unknown_values(self):
        code, _bpy, Armature, Group, Array, forbidden = self.metadata_environment()
        original = Armature('Original Main data')
        baseline = code['_properties_digest']({'data': original, 'value': [1., 2.]})
        for altered in ({'data': original, 'value': [1., 3.]},
                {'data': Armature('Different data'), 'value': [1., 2.]},
                {'data': Armature('Original Main data', SimpleNamespace(filepath='other.blend')), 'value': [1., 2.]},
                {'data': {'id_header': {'type': 'Armature', 'name': original.name, 'library': None}}, 'value': [1., 2.]}):
            with self.subTest(altered=altered):
                self.assertNotEqual(code['_properties_digest'](altered), baseline)
        for invalid in (float('nan'), object()):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                code['_properties_digest']({'invalid': invalid})
        forbidden.assert_not_called()



if __name__ == '__main__': unittest.main()
