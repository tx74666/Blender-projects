"""Standard-library source compatibility only; no native or effect acceptance.

Actual new-run manifests must remain full, unmodified before/after evidence.
The historical view is an explicitly labelled bytes/SHA identity comparison,
not proof that old reports tested current code, and not a new-run final guard.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPOSITORY = Path("D:/MyRepository/Blender-addons-by-Randy")
WORKFLOW = HERE / "verify_actual_surface_workflow.py"
WORKFLOW_SHA = "2e8d82bbbde00604bf3f62bc17cbcb31244ed87290e083ebb17b25f4b9216140"
DIAGNOSTIC = HERE / "diagnose_skin_transfer.py"
DIAGNOSTIC_SHA = "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28"
QA = HERE / "validate_real_dress.py"
QA_SHA = "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046"
INSTALL = HERE / "actual_install_51_20261006_031045_111/result/workflow_install.json"
INSTALL_SHA = "a2157ba399bfe32cc28401847c2556f776761fd607eaa3ba7ea23b61aaec6a32"
INPUT = HERE / "actual_install_51_20261006_031045_111/scenes/Cosha_Dress_QA_surface_install.blend"
CURRENT = {
    "forearm_twist.py": "4f159b83a2bac2aebbc9e23f03ce958da75a10728d0f21010f1178b476d66bf3",
    "__init__.py": "e8ed33bb6515cc665e2feaab4ec8bd3b55d1a32f119d50131829a166a5840aed",
}
HISTORICAL = {
    "forearm_twist.py": "fc2fbf6ff1b1bfa23b4dba5bd8e16e09e73ca33ab545735cddc929c11ebf85c6",
    "__init__.py": "f67a2febe180e03bc77e402ce44968540ac523983cde5546eff6c6b60b66d0ce",
}
SURFACE_SHA = "9d7a928e27464e772330304d03e9ca81462f800951b3172921c87429cf78891c"
WORKER_SHA = "069fb0f21b02e36a23dd02b1978d2a917c2873f290fc3331cdf0d55e877ce5bc"


def need(condition, message):
    if not condition:
        raise RuntimeError("SourceCompatibility52: " + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def explicit_modules(repository):
    need(set(CURRENT) == set(HISTORICAL) == {"forearm_twist.py", "__init__.py"}, "explicit module set changed")
    return {str((repository / "addons/character_designer" / name).resolve()).casefold(): value
            for name, value in CURRENT.items()}


def init_version_only(repository):
    path = repository / "addons/character_designer/__init__.py"
    raw = path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == CURRENT["__init__.py"], "current Init bytes differ")
    text = raw.decode("utf-8")
    tree = ast.parse(text)
    assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "bl_info" for t in n.targets)]
    need(len(assignments) == 1 and isinstance(assignments[0].value, ast.Dict), "Init bl_info AST differs")
    values = [v for k, v in zip(assignments[0].value.keys, assignments[0].value.values)
              if isinstance(k, ast.Constant) and k.value == "version"]
    need(len(values) == 1 and isinstance(values[0], ast.Tuple) and ast.literal_eval(values[0]) == (0, 76, 4),
         "Init version is not exact 0.76.4")
    segment = ast.get_source_segment(text, values[0])
    need(segment is not None and raw.count(segment.encode()) == 1 and segment.rstrip().endswith("4)"),
         "Init version byte span is not unique")
    restored_segment = segment[:segment.rfind("4")] + "3" + segment[segment.rfind("4") + 1:]
    restored = raw.replace(segment.encode(), restored_segment.encode(), 1)
    need(hashlib.sha256(restored).hexdigest() == HISTORICAL["__init__.py"], "Init changed beyond version metadata")
    return {"path": str(path), "old_sha256": HISTORICAL["__init__.py"], "new_sha256": CURRENT["__init__.py"],
            "old_version": [0, 76, 3], "new_version": [0, 76, 4], "only_version_byte_span_changed": True,
            "all_other_AST_and_bytes_exact": True}


def _manifest(manifest):
    need(type(manifest) is dict and bool(manifest), "missing/empty manifest")
    result = {}
    for path, state in manifest.items():
        need(type(path) is str and type(state) is dict and set(state) == {"bytes", "mtime_ns", "sha256"},
             "manifest file state ABI differs")
        need(type(state["bytes"]) is int and state["bytes"] >= 0 and type(state["mtime_ns"]) is int
             and state["mtime_ns"] >= 0 and type(state["sha256"]) is str and len(state["sha256"]) == 64
             and all(c in "0123456789abcdef" for c in state["sha256"]), "manifest file state is untyped")
        normalized = str(Path(path).resolve()).casefold()
        need(normalized not in result, "duplicate normalized manifest path")
        result[normalized] = (path, state)
    return result


def history_view(historical_manifest, current_manifest, repository):
    """Return (labelled historical comparison view, proof); never alter input.

    Caller must hash-pin the report supplying historical_manifest. Every file's
    bytes/SHA and inventory are checked. Only the exact two reviewed canonical
    transitions are allowed. Timestamp differences are observational evidence;
    the complete actual current manifest remains the new-run protection input.
    """
    old, current = _manifest(historical_manifest), _manifest(current_manifest)
    need(set(old) == set(current), "historical/current inventory differs")
    extras = explicit_modules(repository)
    need(set(extras) <= set(current), "reviewed source module missing")
    transitions, times = [], []
    for path, (original_path, before) in old.items():
        after = current[path][1]
        if before["mtime_ns"] != after["mtime_ns"]:
            times.append({"path": original_path, "historical": before["mtime_ns"], "current": after["mtime_ns"]})
        if path in extras:
            name = Path(original_path).name
            need(after["sha256"] == extras[path], "current reviewed module SHA differs")
            need(before["sha256"] in {HISTORICAL[name], extras[path]}, "unknown historical reviewed module SHA")
            if before["sha256"] == after["sha256"]:
                need(before["bytes"] == after["bytes"], "same SHA has mismatched byte count")
            else:
                transitions.append({"path": original_path, "historical_sha256": before["sha256"], "current_sha256": after["sha256"]})
        else:
            need((before["bytes"], before["sha256"]) == (after["bytes"], after["sha256"]),
                 "unknown historical source bytes differ: " + original_path)
    proof = {"scope": "Historical bytes/SHA comparison only; not a new-run source guard",
             "reviewed_transitions": transitions, "timestamp_differences": times,
             "version_only_Init": init_version_only(repository), "all_other_raw_bytes_and_inventory_exact": True,
             "old_reports_validated_changed_code": False, "current_source_manifest_must_remain_unmodified": True,
             "native_compatibility_proved": False, "accepted": False}
    return copy.deepcopy(historical_manifest), proof


def gate_namespace(namespace, repository):
    """Return the real frozen motion_input_gate with one explicit source guard adapter."""
    need(sha(WORKFLOW) == WORKFLOW_SHA, "immutable workflow changed")
    text = WORKFLOW.read_text(encoding="utf-8")
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "motion_input_gate")
    source = ast.get_source_segment(text, node)
    old = '    require(set(changed) <= {surface_path, worker_path}, "A canonical module other than the explicit surface/worker changed since install")'
    new = '''    extra = EXPLICIT_COMPATIBILITY_MODULES
    require(set(extra) <= set(after), "A reviewed compatibility module is missing")
    for path, expected in extra.items():
        require(after[path] == expected, "Current compatibility module differs from reviewed final SHA: " + path)
    require(set(changed) <= {surface_path, worker_path} | set(extra), "Unknown canonical module changed since install")
    report["explicit_source_compatibility"] = {"reviewed_extra_modules": dict(extra), "version_only_Init": INIT_VERSION_ONLY_PROOF(REPOSITORY),
        "canonical_inventory_exact": True, "all_other_canonical_modules_exact": True, "old_install_validated_changed_code": False,
        "full_current_manifest_sha256": qa.digest(diag.source_manifest()), "native_current_compatibility_proved": False,
        "scope": "Source preflight only; old install did not validate changed code"}'''
    need(source.count(old) == 1, "frozen compatibility guard ABI differs")
    current = dict(namespace)
    current.update(EXPLICIT_COMPATIBILITY_MODULES=explicit_modules(repository), INIT_VERSION_ONLY_PROOF=init_version_only)
    exec(compile(source.replace(old, new, 1), str(Path(__file__)), "exec"), current)
    return current["motion_input_gate"]


def current_manifest():
    need(sha(DIAGNOSTIC) == DIAGNOSTIC_SHA and sha(QA) == QA_SHA, "frozen manifest/QA source differs")
    text = DIAGNOSTIC.read_text(encoding="utf-8")
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "source_manifest")
    def file_state(path):
        stat = path.stat()
        return {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha(path)}
    namespace = {"Path": Path, "REPOSITORY": REPOSITORY, "__file__": str(DIAGNOSTIC),
                 "qa": SimpleNamespace(__file__=str(QA), file_state=file_state)}
    exec(compile(ast.get_source_segment(text, node), str(Path(__file__)), "exec"), namespace)
    return namespace["source_manifest"]()


def pure_checks():
    need(sha(INSTALL) == INSTALL_SHA, "old install report differs")
    actual = current_manifest()
    qa = SimpleNamespace(digest=lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest())
    gate = gate_namespace({"Path": Path, "HERE": HERE, "REPOSITORY": REPOSITORY, "json": json, "sha": sha,
                           "require": need, "motion_check": lambda report, qa, name, passed, **facts: need(passed, name)}, REPOSITORY)
    args = SimpleNamespace(input=INPUT.resolve(), install_report=INSTALL.resolve(), expected_surface_sha=SURFACE_SHA,
                           expected_worker_sha=WORKER_SHA)
    report = {}
    gate(args, report, qa, SimpleNamespace(source_manifest=lambda: actual))
    bad = []
    for name in ("skirt.py", "forearm_twist.py", "__init__.py", "skirt_surface.py", "unity_export_worker.py"):
        row = copy.deepcopy(actual); path = next(p for p in row if Path(p).name == name)
        row[path]["sha256"] = "0" * 64; bad.append(row)
    row = copy.deepcopy(actual); del row[next(p for p in row if Path(p).name == "unity_forearm.py")]; bad.append(row)
    row = copy.deepcopy(actual); row[str(REPOSITORY / "addons/character_designer/UNKNOWN.py")] = {"bytes": 1, "mtime_ns": 1, "sha256": "a" * 64}; bad.append(row)
    for row in bad:
        try: gate(args, {}, qa, SimpleNamespace(source_manifest=lambda: row))
        except RuntimeError: pass
        else: raise RuntimeError("source negative accepted")
    historical = copy.deepcopy(actual)
    installed = json.loads(INSTALL.read_text(encoding="utf-8"))["source_manifest_after"]
    for path in historical:
        if Path(path).name in CURRENT: historical[path] = copy.deepcopy(installed[path])
    view, proof = history_view(historical, actual, REPOSITORY)
    need(view == historical and len(proof["reviewed_transitions"]) == 2, "historical explicit two transitions differ")
    need(actual == current_manifest(), "actual source changed during pure checks")
    rejected = 0
    for name in ("skirt.py", "forearm_twist.py", "__init__.py"):
        row = copy.deepcopy(historical); path = next(p for p in row if Path(p).name == name); row[path]["sha256"] = "1" * 64
        try: history_view(row, actual, REPOSITORY)
        except RuntimeError: rejected += 1
        else: raise RuntimeError("historical unknown accepted")
    return {"passed": True, "real_frozen_gate_actual_manifest_positive": 1, "source_negatives_rejected": len(bad),
            "historical_positive": 1, "historical_negatives_rejected": rejected,
            "changed_modules": report["install_input"]["runtime_differences"], "init_version_only": proof["version_only_Init"],
            "native_run": False, "accepted": False}


if __name__ == "__main__":
    print(json.dumps(pure_checks(), ensure_ascii=False))
