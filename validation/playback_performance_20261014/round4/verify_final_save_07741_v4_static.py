"""Pure Python checks; no bpy import, Blender process, UI or scene access."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import py_compile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "final_save_07741_v4.py"
INSTALLER = ROOT / "install_final_save_07741_v4.py"
OLD = ROOT / "final_save_07741_v3.py"
OLD_INSTALLER = ROOT / "install_final_save_07741_v3.py"
CAPTURE = ROOT / "protected_refresh_07741_v3.py"
FAILED = ROOT / "final_save_07741_20261014T192834Z_15c1805b8f8c" / "final_save_receipt.json"


def pin(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


class Line:
    def __init__(self, body, kind="OUTPUT", pointer=11):
        self.body, self.type, self.pointer = body, kind, pointer
        self.current_character = len(body)
        self.bl_rna = SimpleNamespace(identifier="ConsoleLine", properties={"body": object(), "current_character": object(), "type": object()})

    def as_pointer(self):
        return self.pointer


class Space:
    def __init__(self, line):
        self.history, self.scrollback = [line], []
        self.bl_rna = SimpleNamespace(identifier="SpaceConsole", properties={"history": object(), "scrollback": object()})

    def as_pointer(self):
        return 101


def main():
    before = {str(path): pin(path) for path in (OLD, OLD_INSTALLER, CAPTURE, FAILED)}
    assert before[str(OLD)]["sha256"] == "dbb73ca8ce7254230d7cbbfd6648b69d1b113ab9884318565d368ff9e4a05f74"
    assert before[str(OLD_INSTALLER)]["sha256"] == "148aed631c5b8d40e32b2f5deaabd72f8d7ee7b40087748b4f27b83d356d7617"
    assert before[str(CAPTURE)]["sha256"] == "069fe18afcb46a11b6faf63dac3846281dde3c4c0fbc9da90d3c50f105a71eef"
    for path in (SOURCE, INSTALLER):
        py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("final_save_v4_pure_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = module.PENDING_HAIR_TEXT

    def worker(line=None):
        line = line or Line(text)
        space = Space(line)
        value = object.__new__(module.FinalSave)
        value.area = SimpleNamespace(spaces=SimpleNamespace(active=space))
        value.pending_console_text, value.report = text, {}
        value.console_space = None
        value.console_line_pointer = value.console_history_count = value.console_cursor = None
        return value, space, line

    def rejected(callback):
        try:
            callback()
        except RuntimeError:
            return
        raise AssertionError("Malformed native-buffer witness was accepted")

    # A blank or partially typed tail is still waiting, regardless its style.
    for body in ("", text[:40], "# " + text):
        value, _, _ = worker(Line(body, "OUTPUT"))
        assert value.pending_input() is False and not value.report
    for kind in ("OUTPUT", "INPUT", "INFO", "ERROR"):
        value, _, _ = worker(Line(text, kind))
        assert value.pending_input() and value.retained_input()
        row = value.report["pending_console_input"]
        assert row["line_type"] == kind and row["command_execution_called"] is False
        assert row["history_tail_not_in_scrollback"] and len(row["schema_sources"]) == 4

    for field in ("history", "scrollback"):
        value, space, _ = worker()
        del space.bl_rna.properties[field]
        rejected(value.pending_input)
    for field in ("body", "current_character"):
        value, _, line = worker()
        del line.bl_rna.properties[field]
        rejected(value.pending_input)
    value, _, line = worker()
    line.bl_rna.identifier = "OtherRNA"
    rejected(value.pending_input)
    value, space, line = worker()
    space.scrollback.append(line)
    rejected(value.pending_input)
    for cursor in (-1, len(text) + 1, 1.5):
        value, _, line = worker()
        line.current_character = cursor
        rejected(value.pending_input)
    value, _, line = worker()
    line.pointer = 0
    rejected(value.pending_input)

    for alteration in ("body", "cursor", "pointer", "history_count", "scrollback_alias"):
        value, space, line = worker()
        assert value.pending_input()
        if alteration == "body": line.body += " "
        if alteration == "cursor": line.current_character -= 1
        if alteration == "pointer": space.history[-1] = Line(text, pointer=12)
        if alteration == "history_count": space.history.insert(0, Line("earlier", pointer=13))
        if alteration == "scrollback_alias": space.scrollback.append(line)
        rejected(value.retained_input)

    source_tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    installer_tree = ast.parse(INSTALLER.read_text(encoding="utf-8"))
    assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in installer_tree.body
                   if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                   and isinstance(node.value, ast.Constant)}
    assert assignments["expected_sha256"] == pin(SOURCE)["sha256"]
    assert module.CAPTURE_SOURCE_SHA256 == pin(CAPTURE)["sha256"]
    capture_tree = ast.parse(CAPTURE.read_text(encoding="utf-8"))
    definitions = [node for node in capture_tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign))
                   or isinstance(node, ast.FunctionDef) and node.name in module.CAPTURE_FUNCTIONS]
    assert {node.name for node in definitions if isinstance(node, ast.FunctionDef)} == module.CAPTURE_FUNCTIONS
    assert {"exact", "id_properties"} <= module.CAPTURE_FUNCTIONS
    compile(ast.Module(body=definitions, type_ignores=[]), "pinned_capture_definitions", "exec")
    native_calls = [ast.unparse(node.func) for node in ast.walk(source_tree) if isinstance(node, ast.Call)]
    assert native_calls.count("bpy.ops.wm.save_mainfile") == 1
    assert not any(name.startswith("bpy.ops.console.") or name.endswith(".frame_set")
                   or name.endswith(".update_runtime") or name.endswith(".save_as_mainfile") for name in native_calls)
    assert not any(isinstance(node, (ast.Expr, ast.If)) and any(isinstance(call, ast.Call) and ast.unparse(call.func).endswith("begin")
                                                             for call in ast.walk(node)) for node in source_tree.body)
    assert {str(path): pin(path) for path in (OLD, OLD_INSTALLER, CAPTURE, FAILED)} == before
    receipt = {"schema": "x.final-save-v4-pure-source-checks/1", "completed": True,
               "native_or_UI_executed": False, "source": pin(SOURCE), "installer": pin(INSTALLER),
               "preserved_inputs": before, "official_console_schema_sources": list(module.CONSOLE_SCHEMA_SOURCES),
               "checks": ["py_compile", "blank_partial_commented_body_wait", "history_style_not_scrollbacks_semantics",
                          "native_schema_and_cursor_fail_closed", "tail_identity_and_scrollback_disjoint",
                          "pending_buffer_retained_across_transition", "source_installer_capture_pins",
                          "whitelisted_exact_capture_dependencies", "single_native_save_no_console_execution",
                          "no_top_level_worker_run", "failed_v3_sources_receipt_preserved"]}
    (ROOT / "final_save_07741_v4_source_checks.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"completed": True, "checks": len(receipt["checks"]), "source": receipt["source"], "installer": receipt["installer"]}))


if __name__ == "__main__":
    main()
