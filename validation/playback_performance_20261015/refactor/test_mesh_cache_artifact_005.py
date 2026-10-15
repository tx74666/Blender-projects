"""Pure contract/publication regression tests; no Blender or real .blend files."""
import importlib
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_cache_artifact_contract_005 as contract
import mesh_cache_artifact_assembler_005 as assembler


class ContractTests(unittest.TestCase):
    def geometry_fixture(self):
        material = type('Material', (), {'name_full': 'Copied Material', 'library': None})()
        obj = SimpleNamespace(evaluated_get=lambda graph: SimpleNamespace(data=SimpleNamespace(materials=[material])))
        scene = SimpleNamespace(frame_current=1, frame_subframe=0., objects={'Copy': obj})
        payload = {'components': {'vertex_coordinates': 'coordinates', 'corner_normals': 'normals',
                                  'object_matrix_world': 'matrix', 'materials': 'un-normalized'}, 'scope': {}}
        normalized = {**payload['components'], 'materials': contract.base.object_hash([['Material', 'Source Material', None]])}
        golden = {'sha256': contract.base.object_hash(normalized), 'components': normalized}
        binding = {'objects': [{'source_name': 'Source', 'target_name': 'Copy'}],
                   'material_id_map': [{'target': ['Material', 'Copied Material', None], 'source': ['Material', 'Source Material', None]}]}
        native = SimpleNamespace(context=SimpleNamespace(scene=scene, evaluated_depsgraph_get=lambda: object()))
        return scene, binding, payload, golden, native

    def test_material_identity_normalization_preserves_every_numeric_component(self):
        scene, binding, payload, golden, native = self.geometry_fixture()
        def run():
            return contract.check_frame(scene, binding, 1)
        with patch.dict(sys.modules, {'bpy': native}), patch.object(contract, 'check_binding'), \
             patch.object(contract, 'accepted', return_value={'golden': [{'meshes': {'Source': golden}}]}), \
             patch.object(contract.base, 'oracle', return_value=SimpleNamespace(evaluated_shoes=lambda obj: copy.deepcopy(payload))):
            self.assertTrue(run()['exact'])
            self.assertEqual(payload['components']['materials'], 'un-normalized')
            payload['components']['vertex_coordinates'] = 'changed coordinates'
            result = run()
            self.assertFalse(result['exact'])
            self.assertEqual(result['meshes'][0]['changed_components'], ['vertex_coordinates'])
            binding['material_id_map'] = []
            with self.assertRaisesRegex(RuntimeError, 'Unmapped'):
                run()

    def test_readonly_frame_probe_refuses_stale_frame(self):
        scene, binding, payload, golden, native = self.geometry_fixture()
        scene.frame_current = 2
        with patch.dict(sys.modules, {'bpy': native}), patch.object(contract.base, 'oracle') as oracle:
            with self.assertRaisesRegex(RuntimeError, 'Current evaluated'):
                contract.check_frame(scene, binding, 1)
            oracle.assert_not_called()

    def test_missing_actual_receipt_refuses_before_native_import(self):
        with tempfile.TemporaryDirectory() as directory:
            args = type('Args', (), {'full30_report': str(Path(directory)/'missing.json'), 'full30_sha256': '0'*64})()
            with self.assertRaises(FileNotFoundError):
                assembler.main(args, {})
            self.assertNotIn('bpy', sys.modules)

    def test_incomplete_receipt_is_not_an_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'failure_fixture.json'
            path.write_text(json.dumps({'schema': 'x.pc2-fixed-actor-full30/1', 'completed': False}), encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'Completed real'):
                contract.load_full30(path, contract.base.pin(path)['sha256'])

    def test_contract_json_roundtrip_is_stable(self):
        original = {'ids': [('embedded', (('Material', 'M', None), 'node_tree'), ('ShaderNodeTree', 'N', None))],
                    'animation': {'clip': {'units': ((('scale_length', ('float', '0x1.0p+0')),), ())}}}
        encoded = contract.json_value(original)
        self.assertEqual(encoded, json.loads(json.dumps(encoded)))
        self.assertEqual(encoded, contract.json_value(original))

    def test_content_pin_checks_length_path_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'payload.bin'
            path.write_bytes(b'pure payload')
            pin = contract.base.pin(path)
            self.assertEqual(contract.verify_pin({**pin, 'source': 'fixture'}), pin)
            for field, value in [('sha256', '0'*64), ('bytes', 0)]:
                with self.assertRaisesRegex(RuntimeError, 'Content changed'):
                    contract.verify_pin({**pin, field: value})

    def test_publication_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            staged, output = Path(directory)/'stage.bin', Path(directory)/'out.bin'
            staged.write_bytes(b'new')
            output.write_bytes(b'old')
            report = {'artifact_published': False}
            with self.assertRaises(FileExistsError):
                assembler.publish(staged, output, report)
            self.assertEqual(output.read_bytes(), b'old')
            self.assertEqual(staged.read_bytes(), b'new')
            self.assertIs(report['artifact_published'], False)

    def test_linked_output_is_honest_when_verification_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            staged, output = Path(directory)/'stage.bin', Path(directory)/'out.bin'
            staged.write_bytes(b'pure text payload, not a blend')
            original_pin = contract.base.pin
            def fail_after_link(path):
                if Path(path) == output:
                    raise OSError('injected verification failure')
                return original_pin(path)
            report = {}
            with patch.object(assembler.base, 'pin', fail_after_link):
                with self.assertRaisesRegex(OSError, 'injected'):
                    assembler.publish(staged, output, report)
            self.assertTrue(report['artifact_published'])
            self.assertFalse(report['artifact_publication_complete'])
            self.assertEqual(report['artifact']['path'], str(output))
            self.assertTrue(staged.exists() and output.exists())

    def test_publication_cleanup_failure_keeps_link_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            staged, output = Path(directory)/'stage.bin', Path(directory)/'out.bin'
            staged.write_bytes(b'pure text payload')
            original_unlink = Path.unlink
            def fail_stage_unlink(path, *args, **kwargs):
                if path == staged:
                    raise OSError('injected cleanup failure')
                return original_unlink(path, *args, **kwargs)
            report = {}
            with patch.object(Path, 'unlink', fail_stage_unlink):
                with self.assertRaisesRegex(OSError, 'cleanup'):
                    assembler.publish(staged, output, report)
            self.assertTrue(report['artifact_published'] and report['artifact_output_verified'])
            self.assertFalse(report['artifact_publication_complete'])
            self.assertTrue(output.exists())


if __name__ == '__main__':
    unittest.main()
