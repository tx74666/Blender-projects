"""Cross-compiler semantic comparison; preserve the sealed312 test bytewise."""
import ast
import dis
import hashlib
from pathlib import Path
import types
import unittest

HERE = Path(__file__).resolve().parent
OLD_TEST = HERE/'test_mesh_cache_current_reopen_gui_009.py'
if hashlib.sha256(OLD_TEST.read_bytes()).hexdigest() != '7440672b44bae5abdd3ab309f2a232c18df708b75bd74754ba1bc9962e14b682':
    raise RuntimeError('Original GUI009 pure test changed')
import test_mesh_cache_current_reopen_gui_009 as previous

gui = previous.gui


def semantic_instructions(function):
    # Identical AST can receive source-position NOPs in3.13. Retain every real
    # operation/argument and compare branch targets by semantic operation index.
    rows = [row for row in dis.get_instructions(function) if row.opname != 'NOP']
    jumps = set(dis.hasjabs) | set(dis.hasjrel)
    return [(row.opname, ('target', next((index for index, target in enumerate(rows)
        if target.offset >= row.argval), len(rows))) if row.opcode in jumps else row.argval)
        for row in rows]


class Tests(previous.Tests):
    def test_complete_previous_binding_class_is_unchanged_and_private(self):
        for name, before in vars(gui.previous.ReopenSession).items():
            if isinstance(before, types.FunctionType):
                after = getattr(gui._PreviousSession, name)
                self.assertEqual(semantic_instructions(before), semantic_instructions(after), name)
                self.assertIsNot(before.__globals__, after.__globals__)
        cls = next(n for n in ast.parse(gui.PREVIOUS_PATH.read_bytes()).body
            if isinstance(n, ast.ClassDef) and n.name == 'ReopenSession')
        self.assertEqual(gui.EXTRACTION['previous_binding_class_ast_sha256'],
            hashlib.sha256(ast.dump(cls, include_attributes=False).encode()).hexdigest())
        for name in ('start', 'tick', 'ready', 'lifecycle', 'flush'):
            self.assertEqual(semantic_instructions(getattr(gui.previous.ReopenSession, name)),
                semantic_instructions(getattr(gui._PreviousSession, name)), name)


if __name__ == '__main__':
    unittest.main()
