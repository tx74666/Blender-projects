"""Pure extraction/admission proofs; no Blender, accepted receipts or artifacts."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import symtable
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_cache_current_input_007 as inputs


class CurrentCoreTests(unittest.TestCase):
    def test_extracted_kernels_have_explicit_module_globals(self):
        import builtins
        tree = symtable.symtable((HERE/'mesh_cache_actor_current_core_007.py').read_text(), 'current_core', 'exec')
        provided = set(tree.get_identifiers()) | set(dir(builtins))
        for function in tree.get_children():
            self.assertEqual([item.get_name() for item in function.get_symbols()
                if item.is_global() and item.is_referenced() and item.get_name() not in provided], [])

    def test_complete_function_ast_is_original_plus_only_declared_substitutions(self):
        audit = json.loads((HERE/'mesh_cache_current_core_extraction_007.json').read_text())
        current = ast.parse((HERE/'mesh_cache_actor_current_core_007.py').read_text())
        for name, old in [('run_clip', 'mesh_cache_actor_full30_002.py'), ('assemble_clip', 'mesh_cache_artifact_assembler_005.py')]:
            raw = (HERE/old).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), audit['frozen_sources'][old]['sha256'])
            original = raw.decode('utf-8')
            function = next(node for node in ast.parse(original).body if isinstance(node, ast.FunctionDef) and node.name == 'main')
            text = ast.get_source_segment(original, function)
            for change in audit['changes']:
                if change['kernel'] == name:
                    self.assertEqual(text.count(change['old']), 1, change['label'])
                    text = text.replace(change['old'], change['new'], 1)
            expected = ast.parse(text).body[0]
            actual = next(node for node in current.body if isinstance(node, ast.FunctionDef) and node.name == name)
            self.assertEqual(ast.dump(actual, include_attributes=False), ast.dump(expected, include_attributes=False))

    def test_no_native_seek_update_or_save_was_added_by_core_hooks(self):
        audit = json.loads((HERE/'mesh_cache_current_core_extraction_007.json').read_text())
        for change in audit['changes']:
            if 'policy.' in change['new']:
                for token in ('frame_set(', '.update()', 'bpy.ops.', 'libraries.write'):
                    self.assertEqual(change['new'].count(token), change['old'].count(token), change['label'])

    def test_actual_source_function_seals_and_stage_boundary_are_readonly(self):
        proof = inputs.scene_source_proof()
        self.assertEqual(len(proof['manifests']), 3)
        self.assertEqual(len(proof['parent_ast_sha256']), 64)
        self.assertEqual(len(proof['base_ast_sha256']), 64)
        self.assertNotIn('bpy', sys.modules)

    def test_absent_current_receipt_refuses_without_native(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                inputs.load_snapshot(Path(directory)/'missing.json', '0'*64, '1'*64, 1)
        self.assertNotIn('bpy', sys.modules)

    def test_failed_savecopy_is_never_current_input_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'failed-copy-fixture.json'
            path.write_text(json.dumps({'schema': 'x.current-model-save-copy/1', 'completed': False}))
            with self.assertRaisesRegex(RuntimeError, 'Actual guarded'):
                inputs.load_snapshot(path, inputs.base.pin(path)['sha256'], '1'*64, 1)


if __name__ == '__main__':
    unittest.main()
