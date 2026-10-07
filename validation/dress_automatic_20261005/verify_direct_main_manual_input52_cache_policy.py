"""Bounded DirectMain continuation for one proved invalid memory-cache transition.

The original 14-field exact Boolean is retained as measured evidence. Only an
already-outdated, unbaked, non-storage memory cache may lose its known one-frame
summary during paused QA Action seeks. This does not preserve cache contents.
Active author-frame samples, the restored C geometry and final 14-field exact
protection remain the original strict gates. Not a deployed runtime policy.
"""
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CANDIDATE = HERE / "verify_direct_main_manual_input52_node_ui.py"
CANDIDATE_SHA = "fe61357686cdb6ab43fd801c722e6b5eb60967cad23b22fd4e72d45579b681af"
DIAGNOSTIC = HERE / "diagnose_direct_main_cache_transition52.py"
DIAGNOSTIC_SHA = "bf567fc87f6249ffbc2f99a23fd393b1119d5689a44bf3ac4e91cdd968028e84"
EVIDENCE = HERE / "actual_direct_cache_transition_52_20261006_210955_511/result/first_direct_cache_transition.json"
EVIDENCE_SHA = "0649e04101c3b86b731c3fcfdb0364d00d32d971c14fb2a583d335b4b880d846"
POLICY_ID = "KNOWN_INVALID_UNBAKED_MEMORY_52_V1"
STAGE = "DIRECT_MAIN_MANUAL_INPUT_52_CACHE_POLICY"
BASE_INFO = "1 frames in memory (28 KiB), cache is outdated!"
EMPTY_INFO = "0 frames in memory (0 B), cache is outdated!"
FIELD_TYPES = {"pointer": int, "start": int, "end": int, "step": int,
               "is_baked": bool, "disk": bool, "external": bool, "name": str,
               "is_baking": bool, "is_outdated": bool, "info": str,
               "filepath": str, "library_path": bool, "index": int}


def need(condition, message):
    if not condition:
        raise RuntimeError("Cache policy: " + message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def load_candidate():
    need(sha(CANDIDATE) == CANDIDATE_SHA and sha(DIAGNOSTIC) == DIAGNOSTIC_SHA
         and sha(EVIDENCE) == EVIDENCE_SHA, "Immutable candidate/diagnostic/evidence changed")
    spec = importlib.util.spec_from_file_location("cache_policy_frozen_direct52", CANDIDATE)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def classify_cache_transition(frozen, current, phase):
    """Pure, fixture-bounded metadata classification, never a memory-data proof.

    phase = {name: PAUSED_ACTION_SEEK or RESTORED_AUTHOR_FRAME_SAMPLE,
             old_cloth_flags: [viewportBool, renderBool],
             frozen_frame: [intFrame, floatSubframe], frame: [intFrame, floatSubframe]}.
    Missing, sealed/storage, unknown text and every pointer/config change reject.
    """
    result = {"policy": POLICY_ID, "allowed": False, "classification": "REJECTED_OR_UNPROVEN",
              "public_metadata_exact": None, "configuration_pointer_storage_exact": None,
              "changed_fields": None, "cache_content_preserved": "Unknown",
              "memory_position_velocity_payload_read": False, "accepted": False}
    def reject(reason):
        result["reason"] = reason; return result
    for value in (frozen, current):
        if type(value) is not dict or set(value) != set(FIELD_TYPES) or any(type(value[name]) is not kind for name, kind in FIELD_TYPES.items()):
            return reject("Missing/unknown/untyped 14-field native metadata")
    result["public_metadata_exact"] = frozen == current
    result["changed_fields"] = [{"field": name, "frozen": frozen[name], "current": current[name]}
                                for name in FIELD_TYPES if frozen[name] != current[name]]
    result["configuration_pointer_storage_exact"] = all(frozen[name] == current[name] for name in FIELD_TYPES if name != "info")
    for value in (frozen, current):
        if value["pointer"] <= 0 or value["step"] < 1 or value["start"] > value["end"] or value["index"] < 0:
            return reject("Invalid pointer/cache configuration")
        if value["is_baked"] or value["is_baking"] or value["disk"] or value["external"] or value["filepath"] != "" or value["is_outdated"] is not True:
            return reject("Sealed/baking/storage/not-already-outdated cache is outside this policy")
    if not result["configuration_pointer_storage_exact"]:
        return reject("A pointer/configuration/bake/storage/status field changed")
    if frozen["info"] != BASE_INFO or current["info"] not in {BASE_INFO, EMPTY_INFO}:
        return reject("Unknown memory summary or baseline; no post-seek rebaselining")
    if type(phase) is not dict or set(phase) != {"name", "old_cloth_flags", "frozen_frame", "frame"}:
        return reject("Unknown phase evidence")
    flags = phase["old_cloth_flags"]
    if type(flags) is not list or len(flags) != 2 or any(type(value) is not bool for value in flags):
        return reject("Unknown old Cloth enabled-state evidence")
    for key in ("frozen_frame", "frame"):
        frame = phase[key]
        if type(frame) is not list or len(frame) != 2 or type(frame[0]) is not int or type(frame[1]) is not float or not math.isfinite(frame[1]) or frame[1] != 0.0:
            return reject("Unknown/subframe phase evidence")
        if not frozen["start"] <= frame[0] <= frozen["end"]:
            return reject("Frame outside the proved cache range")
    if phase["name"] == "PAUSED_ACTION_SEEK":
        if flags != [False, False]:
            return reject("Invalidation exception requires both original Cloth evaluation flags disabled")
    elif phase["name"] == "RESTORED_AUTHOR_FRAME_SAMPLE":
        if flags != [True, True] or phase["frame"] != phase["frozen_frame"] or not result["public_metadata_exact"]:
            return reject("Active restored author-frame samples require all14 metadata exact")
    else:
        return reject("Unknown phase name")
    result["allowed"] = True
    if current["info"] == EMPTY_INFO:
        result.update(classification="KNOWN_INVALID_MEMORY_SUMMARY_DISCARDED", cache_content_preserved=False,
                      reason="Known one-frame already-invalid unbaked memory summary became empty during paused seeks")
    else:
        result.update(classification="EXACT_PUBLIC_METADATA", reason="Public metadata exact only; memory payload not measured")
    return result


def compiled_exercise_source(direct):
    """Change only the sample cache read receipt and its explicit admissibility gate."""
    source = inspect.getsource(direct.exercise_direct)
    replacements = (
        ('    frozen_cache = same.cache_state(cloth, qa); identities = None; samples = []; sequential = {}; bodies = {}\n',
         '    frozen_cache = same.cache_state(cloth, qa); identities = None; samples = []; sequential = {}; bodies = {}\n'
         '    frozen_cache_frame = [home.frame_current, home.frame_subframe]\n'),
        ('"cache_exact": same.cache_state(cloth, qa) == frozen_cache,',
         '"cache_exact": (sample_cache := same.cache_state(cloth, qa)) == frozen_cache,'),
        ('        if label in {"action_1_sequential", "action_3_sequential"}:\n',
         '''        row["cache_frozen_metadata"] = dict(frozen_cache)
        row["cache_current_metadata"] = dict(sample_cache)
        row["cache_transition"] = classify_cache_transition(frozen_cache, sample_cache, {
            "name": "PAUSED_ACTION_SEEK" if label.startswith("action_") else "RESTORED_AUTHOR_FRAME_SAMPLE",
            "old_cloth_flags": [bool(cloth.show_viewport), bool(cloth.show_render)],
            "frozen_frame": frozen_cache_frame, "frame": row["frame"]})
        report.setdefault("cache_policy_observations", []).append({"label": label, "frame": row["frame"], "classification": row["cache_transition"]})
        report["cache_content_preserved"] = False if any(item["classification"]["cache_content_preserved"] is False for item in report["cache_policy_observations"]) else "Unknown"
        if label in {"action_1_sequential", "action_3_sequential"}:
'''),
        ('need(effect["outside720"]["maximum_m"] <= guard and row["cache_exact"], "raw80 outside720/originalcache guard failed")',
         'need(effect["outside720"]["maximum_m"] <= guard and row["cache_transition"]["allowed"], "raw80 outside720/originalcache guard failed")'),
    )
    for old, new in replacements:
        need(source.count(old) == 1, "Unique frozen sample adaptation ABI differs")
        source = source.replace(old, new, 1)
    restored = source
    for old, new in reversed(replacements):
        need(restored.count(new) == 1, "Reversible sample adaptation differs")
        restored = restored.replace(new, old, 1)
    need(ast.dump(ast.parse(restored)) == ast.dump(ast.parse(inspect.getsource(direct.exercise_direct))),
         "Recipe/publicOriginal/restored C/final metadata gates changed outside the explicit sample policy")
    return source


def prepared_namespace(adapter, direct, core, base, protection_path, protection_sha):
    candidate = load_candidate()
    namespace = candidate.prepared_namespace(adapter, direct, core, base, protection_path, protection_sha)
    namespace["__file__"] = str(Path(__file__))
    namespace["PINS"].update({CANDIDATE: CANDIDATE_SHA, DIAGNOSTIC: DIAGNOSTIC_SHA,
                             EVIDENCE: EVIDENCE_SHA, Path(__file__): sha(Path(__file__))})
    # A separate private function avoids changing the immutable Direct module or
    # its historical pure-check inspect ABI. The real native core/state is shared.
    function_globals = dict(vars(direct))
    function_globals.update(_CORE=core, STAGE=STAGE, classify_cache_transition=classify_cache_transition)
    exec(compile(compiled_exercise_source(direct), str(Path(__file__)), "exec"), function_globals)
    namespace["exercise_direct"] = function_globals["exercise_direct"]
    original_capture = namespace["capture_program"]
    def capture(*values):
        receipt = original_capture(*values)
        report = values[-1]
        report["stage"] = STAGE
        report["cache_policy"] = {"id": POLICY_ID, "scope": "Only known already-invalid unbaked memory loss during paused private QA seeks",
            "evidence": {"path": str(EVIDENCE), "sha256": EVIDENCE_SHA}, "baseline_not_rebased": True,
            "original_cache_exact_boolean_retained": True, "final_metadata_exact_and_restored_C_guards_unchanged": True,
            "cache_content_preserved": "Unknown", "deployed_runtime_policy": False, "accepted": False}
        return receipt
    namespace["capture_program"] = capture
    need(namespace["main"].__globals__ is namespace and namespace["restore_program"] is core.restore_program,
         "Compiled Main/restoration identity changed")
    return namespace


def pure_checks(args):
    candidate = load_candidate(); adapter = candidate.load_current(); direct = adapter.load_direct(); core = direct.load_core(); base = core.load_base()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8")); rows = evidence["observations"]
    need(len(rows) == 2 and rows[0]["phase"] == "frozen_before_first_seek" and rows[1]["phase"] == "sample"
         and rows[1]["exact_boolean_used_by_original_guard"] is False, "Actual diagnostic does not show the exact failed transition")
    frozen, current = rows[0]["current"]["value"], rows[1]["current"]["value"]
    phase = {"name": "PAUSED_ACTION_SEEK", "old_cloth_flags": [False, False], "frozen_frame": rows[0]["frame"], "frame": rows[1]["frame"]}
    positive = classify_cache_transition(frozen, current, phase)
    need(positive["allowed"] and positive["classification"] == "KNOWN_INVALID_MEMORY_SUMMARY_DISCARDED"
         and positive["public_metadata_exact"] is False and positive["cache_content_preserved"] is False, "Actual invalidation classification differs")
    restored = {"name": "RESTORED_AUTHOR_FRAME_SAMPLE", "old_cloth_flags": [True, True], "frozen_frame": rows[0]["frame"], "frame": rows[0]["frame"]}
    need(classify_cache_transition(frozen, frozen, restored)["allowed"]
         and classify_cache_transition(frozen, frozen, restored)["cache_content_preserved"] == "Unknown", "Restored exact metadata is not content proof")
    negatives = []
    for name, value in (("pointer", frozen["pointer"] + 1), ("is_baked", True), ("is_baking", True),
                        ("disk", True), ("external", True), ("is_outdated", False), ("filepath", "other"),
                        ("end", frozen["end"] + 1), ("info", "unknown native summary"), ("pointer", True)):
        altered = dict(current); altered[name] = value; negatives.append((frozen, altered, phase))
    altered = dict(current); altered.pop("index"); negatives.append((frozen, altered, phase))
    sealed = dict(frozen); sealed["is_baked"] = True; negatives.append((sealed, sealed, restored))
    for flags in ([True, False], [False, True], [True, True]):
        altered_phase = copy.deepcopy(phase); altered_phase["old_cloth_flags"] = flags; negatives.append((frozen, current, altered_phase))
    negatives.append((frozen, current, restored))
    changed_phase = copy.deepcopy(restored); changed_phase["frame"] = rows[1]["frame"]; negatives.append((frozen, frozen, changed_phase))
    changed_phase = copy.deepcopy(phase); changed_phase["name"] = "unknown"; negatives.append((frozen, current, changed_phase))
    for a, b, c in negatives:
        need(classify_cache_transition(a, b, c)["allowed"] is False, "Conservative cache negative accepted")
    source = compiled_exercise_source(direct)
    # Execute the actual changed geometry/cache Boolean, not a mirrored helper.
    node = next(node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "need" and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "raw80 outside720/originalcache guard failed")
    for outside, admissible, should_pass in ((0., True, True), (1., True, False), (0., False, False)):
        scope = {"need": direct.need, "effect": {"outside720": {"maximum_m": outside}}, "guard": 5.e-5,
                 "row": {"cache_transition": {"allowed": admissible}, "cache_exact": False}}
        try: exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.Expr(value=copy.deepcopy(node))], type_ignores=[])), "<actual cache and geometry gate>", "exec"), scope)
        except RuntimeError: need(not should_pass, "Allowed actual gate rejected")
        else: need(should_pass, "Actual geometry or cache rejection swallowed")
    namespace = prepared_namespace(adapter, direct, core, base, args.artist_protection, args.artist_protection_sha)
    need(namespace["exercise_direct"].__globals__["_CORE"] is core
         and namespace["exercise_direct"].__globals__["classify_cache_transition"] is classify_cache_transition
         and namespace["exercise_direct"] is not direct.exercise_direct
         and namespace["main"].__globals__["exercise_direct"] is namespace["exercise_direct"], "Real compiled exercise/core/global transport differs")
    return {"passed": True, "actual_evidence_classification_positive": 1, "restored_exact_metadata_positive": 1,
            "conservative_negatives_rejected": len(negatives), "actual_geometry_cache_Boolean_controls": 3,
            "sample_cache_native_read_count_unchanged": True, "original_direct_function_unchanged": True,
            "publicOriginal_restored_C_and_final14_guards_unchanged": True, "native_run": False, "accepted": False}


def main(args):
    if args.pure_checks:
        print(json.dumps(pure_checks(args))); return 0
    candidate = load_candidate(); adapter = candidate.load_current(); direct = adapter.load_direct(); core = direct.load_core(); base = core.load_base()
    candidate.current_artist_proof(base, direct, adapter, args.artist_protection, args.artist_protection_sha)
    return prepared_namespace(adapter, direct, core, base, args.artist_protection, args.artist_protection_sha)["main"](args)


if __name__ == "__main__":
    frozen_candidate = load_candidate()
    raise SystemExit(main(frozen_candidate.arguments()))
