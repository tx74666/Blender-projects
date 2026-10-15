"""Bounded diagnostic of the initial protected FrozenV8 source witness.

This is expected to FAIL. Existing native source/cleanup guards remain active;
neither a diagnostic abort nor cleanup attempted after it certifies restoration.
No candidate is permitted after a successful initial source witness, either.
"""
import argparse
from collections import Counter, deque
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
PINS = {
    "private_playback_native_runner_v8.py": "c67af8e103c7a6ad93dce723e5bfda3edcc70efde4e96c49cb49a35be6593f55",
    "native_source_reference_witness_v7.py": "1e0d888f6a1db20d8261cb1f56fdcb065af59a0c70a8264a0d3dff67d70de542",
    "native_validation_support_v7.py": "6d3a1b69f41b1605af77f1f987af1f89ca5b60ea1c73f4da988427322a504dc5",
    "native_validation_support.py": "3994f58288244684679ffd48d0837ac88bcfd9768f0a3a12c3e1d7d5b6265c0a",
}
STAGE_SHA = "d62c3178ca6f0615fa4517440c157bba0ab2ced87cb64aa560ac1830197bac34"
MAX_SECONDS, MAX_CALLS = 15.0, 10000


class DiagnosticBudget(RuntimeError):
    pass


def compact_path(path):
    path = str(path)
    return {"path": path if len(path) <= 2048 else path[:384] + "..." + path[-1536:],
            "path_characters": len(path), "path_truncated": len(path) > 2048}


def main(args, report):
    if not args.admission_only or args.builder_module != "character_designer.forearm_twist_playback_scene" or args.builder_function != "build_isolated_scene":
        raise RuntimeError("Protected admission builder arguments required")
    for name, expected in PINS.items():
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Protected diagnostic dependency changed: " + name)
    manifest = Path(args.source_manifest).resolve()
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != STAGE_SHA or Path(args.addons).resolve() != manifest.parent / "addons":
        raise RuntimeError("Expected unchanged Stage05 package and manifest")
    sys.path.insert(0, str(HERE))
    import bpy
    import native_source_reference_witness_v7 as extension
    import native_validation_support_v7 as witness
    import private_playback_native_runner_v8 as frozen
    for module in (extension, witness, frozen):
        if Path(module.__file__).resolve().parent != HERE:
            raise RuntimeError("Different protected module imported")
    originals = {name: getattr(extension.Reader, name) for name in ("rna", "value", "raw")}
    original_source = witness.source_property_witness
    state = {"started": None, "attempted": 0, "executed": 0, "max_depth": 0, "abort": None}
    counts, owner_counts, type_counts, pointers = Counter(), Counter(), Counter(), Counter()
    recent, stack, slow = deque(maxlen=128), [], []
    observer_errors = []
    report.update(diagnostic_dependency_pins=PINS,
                  diagnostic_script={"path": str(Path(__file__).resolve()), "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                  diagnostic_budget={"max_seconds": MAX_SECONDS, "max_calls": MAX_CALLS,
                                     "clock_start": "Initial source_property_witness entry; earlier load/evaluation is excluded.",
                                     "cooperative_limit": "Checks at call entry/exit; one blocking native operation cannot be interrupted by this Python wrapper."},
                  diagnostic_observer_errors=observer_errors)

    def abort(reason):
        if state["abort"] is None:
            state["abort"] = {"reason": reason, "elapsed_seconds": time.perf_counter() - state["started"] if state["started"] is not None else 0.0,
                              "attempted_calls": state["attempted"], "executed_calls": state["executed"],
                              "stack": list(stack), "recent": list(recent)}
            print("WITNESS_DIAGNOSTIC_ABORT", reason, state["attempted"], flush=True)
        raise DiagnosticBudget("Expected source-witness diagnostic stop: " + state["abort"]["reason"])

    def check_budget():
        if state["abort"] is not None:
            abort(state["abort"]["reason"])
        if state["attempted"] >= MAX_CALLS:
            abort("call_budget")
        if time.perf_counter() - state["started"] >= MAX_SECONDS:
            abort("time_budget")

    wrappers = {}
    for name, original in originals.items():
        def wrapped(self, value, path, *rest, _name=name, _original=original, **kwargs):
            now = time.perf_counter()
            if state["started"] is None:
                state["started"] = now
            state["attempted"] += 1
            counts[_name] += 1
            path_text = str(path)
            owner = path_text.split(".", 1)[0]
            type_name = type(value).__module__ + "." + type(value).__name__
            owner_counts[owner] += 1
            type_counts[type_name] += 1
            event = {"call": state["attempted"], "method": _name, "top_owner": owner,
                     "value_type": type_name, **compact_path(path_text)}
            try:
                if isinstance(value, bpy.types.bpy_struct):
                    pointer = int(bpy.types.bpy_struct.as_pointer(value))
                    event["RNA_pointer"] = pointer
                    pointers[(type_name, pointer)] += 1
            except BaseException:
                observer_errors.append(traceback.format_exc())
            recent.append(event)
            stack.append(event)
            state["max_depth"] = max(state["max_depth"], len(stack))
            if state["attempted"] == 1 or state["attempted"] % 1000 == 0:
                print("WITNESS_TRACE", state["attempted"], round(now - state["started"], 3), _name, event["path"][-320:], flush=True)
            try:
                check_budget()
                state["executed"] += 1
                result = _original(self, value, path, *rest, **kwargs)
                elapsed = time.perf_counter() - now
                if elapsed >= 0.01:
                    slow.append({"elapsed_seconds_inclusive": elapsed, **event})
                    slow.sort(key=lambda item: item["elapsed_seconds_inclusive"], reverse=True)
                    del slow[24:]
                check_budget()
                return result
            finally:
                stack.pop()
        wrappers[name] = wrapped
        setattr(extension.Reader, name, wrapped)

    def source_once(*source_args, **source_kwargs):
        if state["abort"] is not None:
            abort(state["abort"]["reason"])
        if state["started"] is None:
            state["started"] = time.perf_counter()
            print("WITNESS_SOURCE_BEGIN", flush=True)
        result = original_source(*source_args, **source_kwargs)
        # This read-only diagnostic never progresses into source golden/clone
        # work even if the complete initial witness happens to fit the budget.
        report["initial_source_witness_finished_before_budget"] = True
        report["initial_source_witness_component_count"] = len(result["components"])
        abort("initial_source_witness_completed")

    witness.source_property_witness = source_once
    try:
        frozen.main(args, report)
    finally:
        report["diagnostic_wrappers_still_owned"] = all(getattr(extension.Reader, name) is wrapper for name, wrapper in wrappers.items()) and witness.source_property_witness is source_once
        for name, original in originals.items():
            if getattr(extension.Reader, name) is wrappers[name]:
                setattr(extension.Reader, name, original)
        if witness.source_property_witness is source_once:
            witness.source_property_witness = original_source
        report["diagnostic_methods_restored"] = all(getattr(extension.Reader, name) is original for name, original in originals.items()) and witness.source_property_witness is original_source
        report["diagnostic_summary"] = {"abort": state["abort"], "attempted_calls": state["attempted"],
            "executed_calls": state["executed"], "method_counts": dict(counts), "max_wrapper_depth": state["max_depth"],
            "top_owners": owner_counts.most_common(24), "top_value_types": type_counts.most_common(24),
            "unique_RNA_pointer_count": len(pointers), "total_RNA_pointer_reads": sum(pointers.values()),
            "repeated_RNA_pointers": [{"type": key[0], "pointer": key[1], "reads": count} for key, count in pointers.most_common(24)],
            "recent": list(recent), "slow_completed_calls_inclusive": slow}
        if "sources" in report:
            sources = report.pop("sources")
            report["source_pin_summary"] = {"count": len(sources), "sha256": extension.object_hash(sources)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "source-manifest", "builder-module", "report"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--builder-function", default="build_isolated_scene")
    parser.add_argument("--admission-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite diagnostic evidence")
    report = {"schema": "x.initial-source-witness-budget-diagnostic/1", "completed": False,
              "pid": os.getpid(), "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "diagnostic_only": True, "expected_failure": True, "performance_acceptance": False,
              "no_artist_open_or_save": True, "no_scene_save": True, "no_deploy": True,
              "limits": ["Expected diagnostic FAIL; no playback cost, geometry acceptance or source-restoration claim is inferred.",
                         "Original FrozenV8 guards/cleanup run; diagnostic abort may also block source restoration proof.",
                         "Only metadata paths/types/counts/pointers are recorded; no source RNA getter is added for observation."]}
    try:
        main(args, report)
        raise RuntimeError("Diagnostic unexpectedly returned without a stop")
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        with path.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2, ensure_ascii=False, allow_nan=False)
            output.write("\n")
