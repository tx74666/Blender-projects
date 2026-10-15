"""Pure regression for actual007 failure; no fake PASS receipt or Native calls."""
import ast
import builtins
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import symtable
import unittest

import mesh_cache_actor_current_core_008 as core

HERE = Path(__file__).resolve().parent


def functions(name):
    return {item.name: item for item in ast.parse((HERE/name).read_text()).body if isinstance(item, ast.FunctionDef)}


def main_try(function):
    return next(item for item in function.body if isinstance(item, ast.Try)
        and item.body and isinstance(item.body[0], ast.Expr)
        and isinstance(item.body[0].value, ast.Call) and ast.unparse(item.body[0].value.func) == 'addon.register')


class FailureTests(unittest.TestCase):
    def test_success_native_main_bodies_remain_complete_identical_ast(self):
        old, new = functions('mesh_cache_actor_current_core_007.py'), functions('mesh_cache_actor_current_core_008.py')
        for name in ('run_clip', 'assemble_clip'):
            self.assertEqual(ast.dump(ast.Module(body=main_try(old[name]).body, type_ignores=[])),
                ast.dump(ast.Module(body=main_try(new[name]).body, type_ignores=[])))

    def test_cleanup_native_operations_and_raw_flags_keep_order(self):
        old, new = functions('mesh_cache_actor_current_core_007.py'), functions('mesh_cache_actor_current_core_008.py')
        selected = {'update_source', 'session.close', 'addon.unregister', 'base.native_id_pointers',
            'base.handler_snapshot', 'base.pin', 'base.verify_package_manifest', 'witness.witness_dependency_pins',
            'protect_source', 'protect', 'runtime.defer_runtime', 'admission.select_scene', 'helper.admission.select_scene'}
        def calls(nodes):
            result = []
            class Visitor(ast.NodeVisitor):
                def visit_Call(self, item):
                    if ast.unparse(item.func) in selected:
                        result.append((ast.unparse(item.func), [ast.dump(arg) for arg in item.args]))
                    self.generic_visit(item)
            for node in nodes:
                Visitor().visit(node)
            return result
        for name in ('run_clip', 'assemble_clip'):
            a, b = main_try(old[name]).finalbody, main_try(new[name]).finalbody
            self.assertEqual(calls(a), calls(b))
            def flags(nodes):
                return next(item.value for node in nodes for item in ast.walk(node) if isinstance(item, ast.Assign)
                    and any(ast.unparse(target) == "report['cleanup']" for target in item.targets))
            self.assertEqual(ast.dump(flags(a)), ast.dump(flags(b)))

    def test_primary_exception_identity_survives_secondary_cleanup_fault(self):
        original, cleanup = ValueError('original shader failure'), RuntimeError('cleanup failure')
        report = {}
        def fail():
            primary_failed = False
            try:
                raise original
            except BaseException:
                primary_failed = True
                report['primary_error'] = core.traceback.format_exc()
                raise
            finally:
                with core._cleanup_diagnostics(report, primary_failed):
                    raise cleanup
        with self.assertRaises(ValueError) as observed:
            fail()
        self.assertIs(observed.exception, original)
        self.assertIn('original shader failure', report['primary_error'])
        self.assertIn('cleanup failure', report['secondary_cleanup_error'])

    def test_cleanup_failure_without_primary_still_fails(self):
        report = {}
        with self.assertRaisesRegex(RuntimeError, 'standalone cleanup'):
            with core._cleanup_diagnostics(report, False):
                raise RuntimeError('standalone cleanup')
        self.assertIn('standalone cleanup', report['cleanup_error'])

    def test_clean_cleanup_does_not_replace_primary(self):
        marker = RuntimeError('actual shader primary')
        report = {}
        with self.assertRaises(RuntimeError) as observed:
            try:
                raise marker
            finally:
                with core._cleanup_diagnostics(report, True):
                    report['cleanup_ran'] = True
        self.assertIs(observed.exception, marker)
        self.assertTrue(report['cleanup_ran'])
        self.assertNotIn('secondary_cleanup_error', report)

    def _protection(self, ready):
        run = functions('mesh_cache_actor_current_core_008.py')['run_clip']
        func = deepcopy(next(item for item in run.body if isinstance(item, ast.FunctionDef) and item.name == 'protect_source'))
        func.body = [ast.Global(names=item.names) if isinstance(item, ast.Nonlocal) else item for item in func.body]
        calls, report = [], {}
        def forbidden(*args):
            raise AssertionError('missing shader baseline must not be read')
        policy = NS(source_baseline_ready=lambda: ready, protect_source=forbidden)
        env = {'needs_restore': False, 'admission': NS(select_scene=lambda *args: calls.append('select')),
            'bpy': NS(context=NS(view_layer=NS(update=lambda: calls.append('update')))),
            'source_scene': object(), 'source_pairs': [], 'runtime': object(),
            'base': NS(frame_witness=lambda *args: 'output', compare_witness=lambda *args: {'exact': True}),
            'witness': NS(source_property_witness=lambda *args: {'components': {'actual': 'same'}}),
            'protected_output': 'output', 'protected_props': {'components': {'actual': 'same'}},
            'changed_components': lambda *args: [], 'policy': policy, 'report': report, 'require': core.require}
        module = ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[]))
        exec(compile(module, '<isolated actual protection helper>', 'exec'), env)
        return env['protect_source'], report, calls

    def test_unfinished_baseline_cleanup_records_actual_raw_and_unproven_shader(self):
        protect, report, calls = self._protection(False)
        protect('source_after_cleanup', allow_unproven=True)
        row = report['source_after_cleanup']
        self.assertTrue(row['output']['exact'])
        self.assertTrue(row['source_properties_exact'])
        self.assertIsNone(row['material_source_exact'])
        self.assertEqual(row['material_protection_state'], 'not_proven')
        self.assertEqual(calls, ['select', 'update'])
        core._source_protection_status(report)
        self.assertIs(report['source_protection_complete'], False)
        self.assertEqual(report['source_shader_protection_state'], 'not_proven')

    def test_unfinished_baseline_cannot_pass_ordinary_protection(self):
        protect, report, _ = self._protection(False)
        with self.assertRaisesRegex(RuntimeError, 'unproved'):
            protect('source_after_candidate')
        self.assertIsNone(report['source_after_candidate']['material_source_exact'])

    def test_source_exact_requires_boolean_true_not_truthy_or_missing(self):
        for value in (None, False, 0, 1, 'true'):
            report = {'source_after_cleanup': {'output': {'exact': True}, 'source_properties_exact': True,
                'material_source_exact': value}}
            core._source_protection_status(report)
            self.assertIs(report['source_protection_complete'], False)
        report['source_after_cleanup']['material_source_exact'] = True
        core._source_protection_status(report)
        self.assertIs(report['source_protection_complete'], True)

    def test_extracted_globals_are_declared(self):
        table = symtable.symtable((HERE/'mesh_cache_actor_current_core_008.py').read_text(), 'core008', 'exec')
        provided = set(table.get_identifiers()) | set(dir(builtins))
        for child in table.get_children():
            self.assertEqual([item.get_name() for item in child.get_symbols()
                if item.is_global() and item.is_referenced() and item.get_name() not in provided], [])


if __name__ == '__main__':
    unittest.main()
