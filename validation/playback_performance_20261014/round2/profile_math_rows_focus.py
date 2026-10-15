"""Focused same-process ABBA comparison of direct matrix access and row snapshots.

Use a disposable saved-file copy in isolated Blender --background. Both paths
keep the same current Worklist/Unity Rest code. Never save or refresh the artist.
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import statistics
import sys
import time
import traceback

import bpy


FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER.parent))
from profile_saved_forearm_display import functions, pin, witness


def cache_info(module):
    result = {}
    for name, function in vars(module).items():
        info = getattr(function, "cache_info", None)
        if callable(info):
            result[name] = info()._asdict()
    return result


def own_callables(module):
    return {name: function for name, function in vars(module).items()
            if callable(function) and getattr(function, "__module__", None) == module.__name__}


def main(args, report):
    assert bpy.app.background, 'Use a disposable background Blender process'
    addons_path = Path(args.addons).resolve()
    sys.path.insert(0, str(addons_path))
    import character_designer as addon
    from character_designer import forearm_twist as runtime
    from character_designer import forearm_twist_math as geometry
    from character_designer import animation_worklist_target as target
    from character_designer import unity_animation as ua

    modules = (runtime, geometry, target, ua)
    assert all(Path(module.__file__).resolve().is_relative_to(addons_path) for module in modules), \
        "A compared module was imported from a different add-on tree"
    report["blender"] = bpy.app.version_string
    report["metadata_version"] = list(addon.bl_info["version"])
    report["input"] = input_before = pin(args.input)
    report["artist_before"] = artist_before = pin(args.artist)
    assert Path(args.input).resolve() != Path(args.artist).resolve(), "Input must be a disposable copy"
    assert input_before["sha256"] == artist_before["sha256"], "Saved copy differs from artist disk"
    report["sources"] = source_before = [pin(module.__file__) for module in modules]
    report["metadata_source"] = pin(addon.__file__)
    baseline_folder = Path(args.baseline).resolve()
    report["baseline_sources"] = [pin(baseline_folder / name) for name in
                                  ("forearm_twist.py", "forearm_twist_math.py")]
    report["script"] = pin(__file__)
    report["witness_helper"] = pin(FOLDER.parent / "profile_saved_forearm_display.py")

    addon.register()
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.input).resolve()))
    scene = bpy.context.scene
    report["scene"] = scene.name
    report["actions"] = {obj.name: obj.animation_data.action.name for obj in scene.objects
                         if obj.animation_data and obj.animation_data.action}
    report["calibrated_meshes"] = calibrated = {obj.name: {
        side: {"enabled": record.get("enabled", True), "support_vertices": len(record["vertices"])}
        for side, record in runtime._records(obj).items()}
        for obj in scene.objects if obj.type == "MESH" and runtime.RECORD_KEY in obj}
    assert any(record["enabled"] and record["support_vertices"]
               for records in calibrated.values() for record in records.values()), \
        "No enabled calibrated support; this would not exercise the row snapshot"
    report["warmup_frames"] = [1, 3]
    report["frames"] = frames = [2, 6, 10, 14, 18, 22, 26, 30] * 2
    current_math = {name: getattr(geometry, name) for name in
                    ("blended_matrix", "desired_vertex", "corrected_vertex")}
    baseline_math = functions(baseline_folder / "forearm_twist_math.py", geometry.__dict__,
                              set(current_math))
    current_calculate = runtime._calculate_records
    current_corrected_alias = runtime.corrected_vertex
    baseline_calculate = functions(baseline_folder / "forearm_twist.py", runtime.__dict__,
                                   {"_calculate_records"})["_calculate_records"]
    shared_rest = {module: own_callables(module) for module in (target, ua)}
    report["unchanged_rest_callable_names"] = {
        module.__name__: sorted(values) for module, values in shared_rest.items()}
    report["cases"] = cases = []
    expected = None
    try:
        for block, label in enumerate(("old_rows", "rows", "rows", "old_rows"), 1):
            for module, values in shared_rest.items():
                assert all(getattr(module, name) is function for name, function in values.items()), \
                    "Shared Rest code changed during the comparison"
            selected_math = baseline_math if label == "old_rows" else current_math
            for name, function in selected_math.items():
                setattr(geometry, name, function)
            selected_corrected = geometry.corrected_vertex
            runtime.corrected_vertex = selected_corrected
            selected_calculate = baseline_calculate if label == "old_rows" else current_calculate
            runtime._CACHE.clear()
            runtime._OUTPUT_CACHE.clear()
            runtime.validation_cache.clear()
            target._compile_rest_record.cache_clear()
            totals = {"calls": 0, "seconds": 0.0}

            def measured_calculate(*values, **kwargs):
                start = time.perf_counter()
                try:
                    return selected_calculate(*values, **kwargs)
                finally:
                    totals["calls"] += 1
                    totals["seconds"] += time.perf_counter() - start

            runtime._calculate_records = measured_calculate
            try:
                warm_calls = [0]

                def counted_corrected(*values, **kwargs):
                    warm_calls[0] += 1
                    return selected_corrected(*values, **kwargs)

                runtime.corrected_vertex = counted_corrected
                try:
                    for frame in report["warmup_frames"]:
                        scene.frame_set(frame)
                        bpy.context.view_layer.update()
                        assert not runtime._ERRORS, dict(runtime._ERRORS)
                finally:
                    runtime.corrected_vertex = selected_corrected
                assert warm_calls[0] > 0, "No Forearm correction ran during warmup"
                elapsed, calculation_ms, calculation_calls, outputs = [], [], [], []
                for frame in frames:
                    totals["calls"], totals["seconds"] = 0, 0.0
                    start = time.perf_counter()
                    scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    elapsed.append((time.perf_counter() - start) * 1000)
                    calculation_ms.append(totals["seconds"] * 1000)
                    calculation_calls.append(totals["calls"])
                    assert not runtime._ERRORS, dict(runtime._ERRORS)
                    assert totals["calls"] > 0, "Hot frame did not execute _calculate_records"
                    outputs.append(witness(runtime, scene))
                if expected is None:
                    expected = outputs
                same = outputs == expected
                assert same, "Pose/managed output/records/collection/display changed"
                row = {"block": block, "label": label, "milliseconds": elapsed,
                       "median_ms": statistics.median(elapsed),
                       "calculate_milliseconds": calculation_ms,
                       "calculate_median_ms": statistics.median(calculation_ms),
                       "calculate_calls": calculation_calls,
                       "warm_corrected_calls": warm_calls[0],
                       "outputs_equal_to_baseline": same,
                       "shared_rest_cache_info": {module.__name__: cache_info(module)
                                                  for module in (target, ua)},
                       "errors": dict(runtime._ERRORS)}
                cases.append(row)
                print("MATH_ROWS_CASE", block, label, round(row["median_ms"], 3),
                      "CALCULATE", round(row["calculate_median_ms"], 3), flush=True)
            finally:
                runtime._calculate_records = selected_calculate
                runtime.corrected_vertex = selected_corrected
    finally:
        for name, function in current_math.items():
            setattr(geometry, name, function)
        runtime._calculate_records = current_calculate
        runtime.corrected_vertex = current_corrected_alias

    for module, values in shared_rest.items():
        assert all(getattr(module, name) is function for name, function in values.items())
    report["sources_after"] = [pin(module.__file__) for module in modules]
    assert report["sources_after"] == source_before, "Compared source files changed during evaluation"
    report["input_after"] = pin(args.input)
    report["artist_after"] = pin(args.artist)
    assert report["input_after"] == input_before
    assert report["artist_after"] == artist_before
    report["artist_disk_unchanged"] = True
    report["all_frame_witnesses_equal"] = True
    report["no_scene_save"] = True
    report["paired_calculate_delta_ms"] = [
        [left - right for left, right in zip(cases[a]["calculate_milliseconds"],
                                             cases[b]["calculate_milliseconds"])]
        for a, b in ((0, 1), (3, 2))]
    report["limits"] = [
        "One disposable saved snapshot, one thread, shared system load; not viewport FPS.",
        "Only three geometry functions and _calculate_records are switched; current target/UA Rest code is identical.",
        "Two warmup plus sixteen hot samples per ABBA block, repeating the same eight frames twice.",
        "_calculate_records times overlap whole-frame times; do not add their durations.",
        "Per-vertex correction is counted only during warmup, outside all hot measurements.",
        "Exact observed pose/managed coordinates/state/records/display witnesses, not all-world equality.",
        "Unsaved artist edits and external GUI callbacks are excluded; no live artist refresh or scene save."]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "report"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--baseline", default=str(FOLDER / "baseline_07739"))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    destination = Path(args.report).resolve()
    if destination.exists():
        raise SystemExit("Use a new report path; prior evidence must remain intact")
    report = {"schema": "x.forearm-matrix-rows-focus/1", "completed": False,
              "pid": os.getpid(), "model_and_reasoning_effort": "unrecorded",
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        main(args, report)
        report["completed"] = True
    except Exception:
        report["error"] = traceback.format_exc()
        raise
    finally:
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
