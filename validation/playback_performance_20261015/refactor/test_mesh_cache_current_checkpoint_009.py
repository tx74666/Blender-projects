"""Targeted pure009 checkpoint proof; no bpy/Blender or fake acceptance files."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import mesh_cache_current_input_009 as current
import mesh_cache_current_policy_009 as policy
import mesh_cache_current_contract_009 as contract
import mesh_cache_actor_current_core_009 as core

HERE = Path(__file__).resolve().parent


def functions(name):
    return {node.name: node for node in ast.parse((HERE/name).read_text()).body
        if isinstance(node, ast.FunctionDef)}


def native_try(function):
    return next(node for node in function.body if isinstance(node, ast.Try)
        and node.body and isinstance(node.body[0], ast.Expr)
        and ast.unparse(node.body[0].value.func) == 'addon.register')


class CheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual = json.loads(current.CHECKPOINT.read_text())

    def test_actual_failed_payload_is_only_capture_eligible(self):
        self.assertEqual(len(current.validate_checkpoint_payload(self.actual)), 69)
        self.assertIs(self.actual['completed'], False)
        self.assertEqual(self.actual['replay'], [])
        self.assertNotIn('all_replay_geometry_exact', self.actual)

    def test_incomplete_failed_or_changed_capture_is_rejected(self):
        changes = [lambda r: r.update(completed=True),
            lambda r: r['golden'].pop(),
            lambda r: r['golden'][2]['meshes'].pop(next(iter(r['golden'][2]['meshes']))),
            lambda r: r['cache_files'].pop(),
            lambda r: r.update(static_deltas=[{'changed': 'custom_normal'}]),
            lambda r: r['source_after_cleanup'].update(material_source_exact=None),
            lambda r: r['source_after_golden']['output'].update(exact=False),
            lambda r: r['cleanup'].update(owned_ids_removed=False),
            lambda r: r.update(primary_error='another failure'),
            lambda r: r['golden'][0]['meshes']['Cosha'].update(sha256='0'*64)]
        for change in changes:
            with self.subTest(change=change):
                row = deepcopy(self.actual)
                change(row)
                with self.assertRaises(RuntimeError):
                    current.validate_checkpoint_payload(row)

    def test_checkpoint_loader_refuses_other_path_or_sha_before_payload(self):
        with patch.object(current.base, 'pin', return_value={'path': str(current.CHECKPOINT),
            'sha256': '0'*64, 'bytes': current.CHECKPOINT_BYTES}):
            with self.assertRaisesRegex(RuntimeError, 'fixed actual008|Fixed actual008'):
                current.load_capture_checkpoint(current.CHECKPOINT, '0'*64)

    def test_pc2_header_length_count_and_payload_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root/'blendcache_current_008'
            directory.mkdir()
            path = directory/'mesh_000.pc2'
            def write(samples=30, vertices=2, extra=b''):
                path.write_bytes(current.HEADER.pack(b'POINTCACHE2\0', 1, vertices, 0., 1., samples)
                    + b'\0'*(2*30*12) + extra)
                return {'cache_files': [{'source': 'Fixture', **current.base.pin(path)}]}
            with patch.object(current, 'HERE', root):
                row = write()
                self.assertEqual(current.checkpoint_cache_domains(row), {'Fixture': 2})
                with self.assertRaises(RuntimeError):
                    current.checkpoint_cache_domains(write(samples=29))
                with self.assertRaises(RuntimeError):
                    current.checkpoint_cache_domains(write(vertices=3))
                with self.assertRaises(RuntimeError):
                    current.checkpoint_cache_domains(write(extra=b'bad'))
                row = write()
                path.write_bytes(path.read_bytes()[:-1]+b'1')
                with self.assertRaises(RuntimeError):
                    current.checkpoint_cache_domains(row)

    def test_full_readonly_gate_passes_actual_producer_interpreter(self):
        # Historical AST serialization is interpreter-specific; production uses
        # this same bundled3.13 as actual008.312 still runs every other pure test.
        import sys
        if sys.version_info[:2] != (3, 13):
            self.skipTest('Actual008 ast.dump receipt was produced by bundled3.13')
        row, pin = current.load_capture_checkpoint(current.CHECKPOINT, current.CHECKPOINT_SHA)
        self.assertEqual(pin['sha256'], current.CHECKPOINT_SHA)
        self.assertEqual(len(row['_checkpoint_vertex_counts']), 69)
        self.assertIs(row['completed'], False)
        self.assertEqual(current.scene_source_proof()['stage10_manifest']['sha256'], current.STAGE10_SHA)
        actual_pg = contract.validate_pg_fixture(HERE/'native_unset_cycles_copy_fixture_report_011.json',
            '3cecca5c644582286a44f545b2aa3a94beb8b54c5547cce02ded165c011c5f93')
        self.assertEqual(actual_pg['bytes'], 57729)

    def test_fresh_saved13_geometry_and_shader_are_mandatory(self):
        value = object.__new__(policy.CurrentPolicy)
        value.checkpoint = self.actual
        witness = {'sha256': current.SOURCE_SHA, 'frame': 13, 'subframe': 0.0.hex(),
            'components': {'mesh:'+name: row['sha256'] for name, row in self.actual['golden'][12]['meshes'].items()}}
        report = {}
        value.validate_fresh_output(witness, report)
        self.assertIs(report['checkpoint_source_frame_exact'], True)
        for bad in ({**witness, 'sha256': '0'*64}, {**witness, 'frame': 12},
                    {**witness, 'components': {}}, {**witness, 'subframe': 0.5.hex()}):
            with self.assertRaises(RuntimeError):
                value.validate_fresh_output(bad, {})
        value.source_before = None
        value.source_shader = object()
        value.capture = lambda *args: deepcopy(self.actual['protected_shader_before'])
        report = {}
        value.begin_source(object(), report)
        self.assertIs(report['checkpoint_source_shader_exact'], True)
        value.source_before = None
        value.capture = lambda *args: {'changed': 'World.cycles'}
        with self.assertRaises(RuntimeError):
            value.begin_source(object(), {})

    def test_build_replay_timing_and_cleanup_stay_identical_to008(self):
        old = functions('mesh_cache_actor_current_core_008.py')
        new = functions('mesh_cache_actor_current_core_009.py')
        a, b = native_try(old['run_clip']), native_try(new['run_clip'])
        def after_build_marker(body):
            nodes = body[-1].body
            start = next(i for i, node in enumerate(nodes) if isinstance(node, ast.Assign)
                and ast.unparse(node.targets[0]) == 'before_ids')
            return ast.dump(ast.Module(body=nodes[start:], type_ignores=[]))
        self.assertEqual(after_build_marker(a.body), after_build_marker(b.body))
        self.assertEqual(ast.dump(ast.Module(body=a.finalbody, type_ignores=[])),
            ast.dump(ast.Module(body=b.finalbody, type_ignores=[])))
        self.assertEqual(ast.dump(ast.Module(body=a.handlers, type_ignores=[])),
            ast.dump(ast.Module(body=b.handlers, type_ignores=[])))

    def test_assembly_only_adds_fresh_source_gate(self):
        old = native_try(functions('mesh_cache_actor_current_core_008.py')['assemble_clip'])
        new = deepcopy(native_try(functions('mesh_cache_actor_current_core_009.py')['assemble_clip']))
        calls = [node for node in ast.walk(new) if isinstance(node, ast.With)]
        outer = calls[0]
        expected = ast.dump(ast.parse('policy.validate_fresh_output(protected, report)').body[0])
        matches = [node for node in outer.body if ast.dump(node) == expected]
        self.assertEqual(len(matches), 1)
        outer.body.remove(matches[0])
        self.assertEqual(ast.dump(old), ast.dump(new))

    def test_run_clip_never_writes_or_creates_cache_and_reuses_complete_golden(self):
        func = functions('mesh_cache_actor_current_core_009.py')['run_clip']
        calls = [node for node in ast.walk(func) if isinstance(node, ast.Call)]
        self.assertFalse(any(isinstance(node.func, ast.Attribute) and node.func.attr in {'write', 'mkdir'} for node in calls))
        modes = [node.args[0].value for node in calls if isinstance(node.func, ast.Attribute)
            and node.func.attr == 'open' and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertEqual(modes, ['rb'])
        self.assertNotIn('policy.source_frame', [ast.unparse(node.func) for node in calls])
        self.assertEqual(ast.dump(functions('mesh_cache_actor_current_core_008.py')['_cleanup_diagnostics']),
            ast.dump(functions('mesh_cache_actor_current_core_009.py')['_cleanup_diagnostics']))


if __name__ == '__main__':
    unittest.main()
