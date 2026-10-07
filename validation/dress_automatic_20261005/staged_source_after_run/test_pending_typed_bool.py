"""Staged-only two controls; compile the narrow candidate guard in memory.
Canonical/runtime files remain unchanged. Installed native graph proof is the
existing real-hook fixture's explicit dependency spy, not Blender evidence.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(r"D:\MyRepository\Blender-addons-by-Randy")
SOURCE=ROOT/"addons/character_designer/dress_plain_native_skin.py"
TESTS=ROOT/"tests/test_dress_plain_native_skin.py"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=="2508f3b94a1322f786297feec9517a3627837a1b4f770b45380a4e4c11dce3eb"
assert hashlib.sha256(TESTS.read_bytes()).hexdigest()=="15deb95edaec52d7339152033e1fd228dbd3acfc17ba3ce300ea696231d79c4e"
spec=importlib.util.spec_from_file_location("frozen_plain_tests",TESTS)
original=importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
text=SOURCE.read_text(encoding="utf-8").replace('and state.get("editing") is False and state.get("pending") is False','and state.get("editing") is False and type(state.get("pending")) is bool').replace('only complete Manual input state is supported; finish Original and pending/Automatic previews.','only Manual input with finished Original editing and paused Cloth is supported.')
assert hashlib.sha256(text.encode()).hexdigest()=="8e2477f7cb5756ee0b479d7749344cbaa41b6a838d85f3f20792240cd54e6980"
node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=="_direct_guard")
def fixture():
    f=original.fixture()
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),"exec"),vars(f.module))
    return f
class PendingFocusedTests(unittest.TestCase):
    def test_pending_true_complete_manual_capture_and_strip_preserves_state(self):
        f = fixture()
        raw = json.loads(f.source["direct-state"])
        raw["pending"] = True
        f.source["direct-state"] = json.dumps(raw)
        state_before = f.source["direct-state"]
        receipt = json.loads(json.dumps(f.module.capture(f.source), allow_nan=False))
        self.assertIs(receipt["direct_proof"]["state"]["pending"], True)
        f.module.validate(f.source, receipt)
        with patch.dict(sys.modules, {"bpy": f.bpy}):
            f.module.prepare(f.source, receipt)
            self.assertEqual(f.events, [])
            result = f.module.strip(f.source, receipt)
        self.assertEqual(f.source["direct-state"], state_before)
        self.assertEqual(list(f.source.modifiers), [f.arm, f.sub])
        self.assertTrue(result["manual_original_preserved"])
        self.assertFalse(result["simulation_baked"] or result["animation_supported"] or result["export_authorized"])

    def test_pending_transition_or_unknown_typed_value_rejects_before_strip(self):
        for start in (False, True):
            f = fixture()
            raw = json.loads(f.source["direct-state"])
            raw["pending"] = start
            f.source["direct-state"] = json.dumps(raw)
            receipt = f.module.capture(f.source)
            raw["pending"] = not start
            f.source["direct-state"] = json.dumps(raw)
            with patch.dict(sys.modules, {"bpy": f.bpy}), self.assertRaises(ValueError):
                f.module.strip(f.source, receipt)
            self.assertEqual(f.events, [])
        for value in (0, 1, None, "false", [], {}):
            f = fixture()
            receipt = f.module.capture(f.source)
            receipt["direct_proof"]["state"]["pending"] = value
            with patch.dict(sys.modules, {"bpy": f.bpy}), self.assertRaises(ValueError):
                f.module.strip(f.source, receipt)
            self.assertEqual(f.events, [])
            raw = json.loads(f.source["direct-state"])
            raw["pending"] = value
            f.source["direct-state"] = json.dumps(raw)
            with self.assertRaises(ValueError):
                f.module.capture(f.source)
            self.assertEqual(f.events, [])


if __name__=="__main__":
    unittest.main(verbosity=2)
