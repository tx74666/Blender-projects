"""Diagnostic only: record exact frozen/current cache metadata before rejection.

The immutable DirectMain recipe and original cache guard remain unchanged.
Observations copy the SAME cache_state return values used by that recipe; no
extra frame, graph update, mesh/cache read, reset, free, bake or flags setter is
introduced. Memory position/velocity cache contents are not measured here.
"""
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CANDIDATE = HERE / "verify_direct_main_manual_input52_node_ui.py"
CANDIDATE_SHA = "fe61357686cdb6ab43fd801c722e6b5eb60967cad23b22fd4e72d45579b681af"
FAILED = HERE / "actual_direct_main_ui6_52_20261006_203002_652/result/input800_reproduction.json"
FAILED_SHA = "e258f1e9d35b9a057216761c09116e6acd0106061f7a65a557d27f7d49adeac6"
FIELD_TYPES = {"pointer": int, "start": int, "end": int, "step": int,
               "is_baked": bool, "disk": bool, "external": bool, "name": str,
               "is_baking": bool, "is_outdated": bool, "info": str,
               "filepath": str, "library_path": bool, "index": int}
OFFICIAL = {
    "readonly_cache_status_and_info": "https://raw.githubusercontent.com/blender/blender/v5.2.0/source/blender/makesrna/intern/rna_object_force.cc",
    "info_recalculation_and_depsgraph_reset": "https://raw.githubusercontent.com/blender/blender/v5.2.0/source/blender/blenkernel/intern/pointcache.cc"}


def need(condition, message):
    if not condition:
        raise RuntimeError("Cache diagnostic: " + message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def load_candidate():
    need(sha(CANDIDATE) == CANDIDATE_SHA and sha(FAILED) == FAILED_SHA,
         "Immutable Direct/failure evidence changed")
    spec = importlib.util.spec_from_file_location("cache_diagnostic_frozen_direct52", CANDIDATE)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def cache_receipt(value):
    complete = type(value) is dict and set(value) == set(FIELD_TYPES)
    complete = complete and all(type(value[name]) is kind for name, kind in FIELD_TYPES.items())
    return {"status": "Measured" if complete else "Unknown", "typed_14_fields_complete": bool(complete),
            "value": copy.deepcopy(value) if complete else None,
            "reason": None if complete else "Native cache metadata fieldset/types unresolved"}


def differences(left, right):
    a, b = cache_receipt(left), cache_receipt(right)
    if a["status"] != "Measured" or b["status"] != "Measured":
        return {"status": "Unknown", "differences": None}
    return {"status": "Measured", "differences": [{"field": name, "frozen": left[name], "current": right[name]}
            for name in FIELD_TYPES if left[name] != right[name]]}


def make_observer(original_cache, exercise_code, callback):
    """Return native cache values unmodified; all observation errors are contained."""
    def observed_cache(cloth, qa):
        result = original_cache(cloth, qa)
        frame = inspect.currentframe().f_back
        try:
            if frame.f_code is exercise_code and "frozen_cache" not in frame.f_locals:
                callback("frozen_before_first_seek", result, dict(frame.f_locals))
            elif frame.f_code.co_name == "sample" and frame.f_back is not None and frame.f_back.f_code is exercise_code:
                callback("sample", result, dict(frame.f_locals))
        except Exception:
            # Diagnostic collection cannot replace/swallow the original return or guard.
            pass
        finally:
            del frame
        return result
    return observed_cache


def observation(phase, result, local):
    home, cloth = local["home"], local["cloth"]
    row = {"phase": phase, "frame": [int(home.frame_current), float(home.frame_subframe)],
           "cloth_flags": {"show_viewport": bool(cloth.show_viewport), "show_render": bool(cloth.show_render)},
           "current": cache_receipt(result), "metadata_only": True, "cache_content_measured": False,
           "accepted": False}
    if phase == "sample":
        row.update(label=str(local["label"]), frozen=cache_receipt(local["frozen_cache"]),
                   comparison=differences(local["frozen_cache"], result),
                   exact_boolean_used_by_original_guard=(result == local["frozen_cache"]))
    return row


def prepared_namespace(candidate, adapter, direct, core, base, protection_path, protection_sha, original_prepare):
    namespace = original_prepare(adapter, direct, core, base, protection_path, protection_sha)
    wrapper_sha = sha(Path(__file__))
    namespace["PINS"].update({CANDIDATE: CANDIDATE_SHA, FAILED: FAILED_SHA, Path(__file__): wrapper_sha})
    original_exercise = namespace["exercise_direct"]
    def exercise(values, frozen):
        same, report = values["same"], values["report"]
        original_cache = same.cache_state; captured = []; sidecar = values["write"]
        path = values["endpoint_path"].parent / "first_direct_cache_transition.json"
        need(not path.exists(), "Refusing to overwrite a cache diagnostic")
        diagnostic = {"diagnostics_only": True, "candidate": {"path": str(CANDIDATE), "sha256": CANDIDATE_SHA},
                      "prior_failure": {"path": str(FAILED), "sha256": FAILED_SHA},
                      "wrapper": {"path": str(Path(__file__)), "sha256": wrapper_sha},
                      "same_native_read_results_observed": True, "original_guard_modified": False,
                      "accepted": False, "cache_content_measured": False, "official": OFFICIAL, "observations": captured}
        report["cache_transition_diagnostic"] = diagnostic
        def collect(phase, result, local):
            if phase == "sample" and any(row.get("phase") == "sample" for row in captured):
                return
            try:
                captured.append(observation(phase, result, local))
            except Exception as error:
                captured.append({"phase": phase, "status": "Unknown", "error": type(error).__name__ + ": " + str(error)})
            path.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
            report["cache_transition_diagnostic_file"] = {"path": str(path), "sha256": sha(path)}
            sidecar()
        same.cache_state = make_observer(original_cache, direct.exercise_direct.__code__, collect)
        try:
            return original_exercise(values, frozen)
        finally:
            same.cache_state = original_cache
    namespace["exercise_direct"] = exercise
    need(namespace["restore_program"] is core.restore_program and namespace["main"].__globals__ is namespace,
         "Compiled Main/restoration identity differs")
    return namespace


def pure_checks(candidate):
    adapter = candidate.load_current(); direct = adapter.load_direct(); core = direct.load_core(); base = core.load_base()
    text = inspect.getsource(direct.exercise_direct); tree = ast.parse(text)
    function = tree.body[0]
    frozen = next(node for node in function.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "frozen_cache" for target in node.targets))
    sample = next(node for node in function.body if isinstance(node, ast.FunctionDef) and node.name == "sample")
    row = next(node for node in sample.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "row" for target in node.targets))
    exact = next(value for key, value in zip(row.value.keys, row.value.values) if isinstance(key, ast.Constant) and key.value == "cache_exact")
    guard = next(node for node in sample.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                 and len(node.value.args) > 1 and isinstance(node.value.args[1], ast.Constant)
                 and node.value.args[1].value == "raw80 outside720/originalcache guard failed")
    # Real frozen assignment, comparison and unchanged guard execute with only
    # cache/geometry transport stubs. This is not native cache preservation proof.
    small = ast.parse('''def exercise_direct(same, cloth, qa):
    frozen_cache = None
    def sample(label):
        row = {}
        effect = {"outside720": {"maximum_m": 0.}}
        guard = 5.e-5
        need(False, "placeholder")
        return row
    return sample("action_1_sequential")
''')
    small.body[0].body[0] = copy.deepcopy(frozen)
    mini_sample = small.body[0].body[1]
    mini_sample.body[0].value = ast.Dict(keys=[ast.Constant(value="cache_exact")], values=[copy.deepcopy(exact)])
    mini_sample.body[3] = copy.deepcopy(guard)
    ast.fix_missing_locations(small)
    namespace = {"need": direct.need}; exec(compile(small, "<actual frozen cache guard transport>", "exec"), namespace)
    mini = namespace["exercise_direct"]
    baseline = {name: (False if kind is bool else "" if kind is str else 1) for name, kind in FIELD_TYPES.items()}
    changed = dict(baseline); changed["info"] = "readonly status changed"
    calls = []; receipts = []
    def native_transport(*unused):
        calls.append(1); return baseline if len(calls) == 1 else changed
    same = SimpleNamespace(cache_state=None); same.cache_state = make_observer(native_transport, mini.__code__,
        lambda phase, value, local: receipts.append((phase, copy.deepcopy(value), dict(local))))
    try: mini(same, object(), None)
    except RuntimeError as error:
        need(str(error) == "DirectMain52: raw80 outside720/originalcache guard failed", "Original guard message/throw differs")
    else: raise RuntimeError("Diagnostic manufactured guard success")
    need(len(calls) == 2 and [row[0] for row in receipts] == ["frozen_before_first_seek", "sample"]
         and receipts[1][2]["frozen_cache"] is baseline and receipts[1][1] == changed,
         "Actual guard comparison values/caller not observed or extra native reads introduced")
    need(differences(baseline, changed)["differences"] == [{"field": "info", "frozen": "", "current": changed["info"]}],
         "Exact field difference lost")
    need(differences(baseline, baseline)["differences"] == [], "Equal metadata manufactures change")
    missing = dict(baseline); missing.pop("pointer")
    wrong = dict(baseline); wrong["pointer"] = True
    need(differences(missing, changed)["status"] == differences(wrong, changed)["status"] == "Unknown",
         "Missing or untyped ABI manufactured proof")
    calls.clear(); same.cache_state = make_observer(native_transport, mini.__code__,
        lambda *unused: (_ for _ in ()).throw(RuntimeError("observer failure")))
    try: mini(same, object(), None)
    except RuntimeError as error: need(str(error) == "DirectMain52: raw80 outside720/originalcache guard failed", "Observer swallowed original guard")
    else: raise RuntimeError("Observer exception manufactured success")
    need(sha(CANDIDATE) == CANDIDATE_SHA and sha(FAILED) == FAILED_SHA, "Immutable files changed during pure controls")
    return {"passed": True, "focused_controls": 6, "actual_frozen_cache_assignment_comparison_guard_used": True,
            "extra_native_cache_reads": 0, "native_run": False, "guard_changed": False, "accepted": False}


def main(args, candidate):
    if args.pure_checks:
        print(json.dumps(pure_checks(candidate))); return 0
    original_prepare = candidate.prepared_namespace
    candidate.prepared_namespace = lambda *values: prepared_namespace(candidate, *values, original_prepare)
    try:
        return candidate.main(args)
    finally:
        candidate.prepared_namespace = original_prepare


if __name__ == "__main__":
    frozen = load_candidate()
    raise SystemExit(main(frozen.arguments(), frozen))
