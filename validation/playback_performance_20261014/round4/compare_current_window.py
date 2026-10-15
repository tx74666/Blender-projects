"""Explicit eight-report GUI comparison; no native execution or ledger writes.

Supply the final two .40 and .41 Material/Solid case reports explicitly. Older
reports are never globbed or auto-selected. Failed, partial, diagnostic-mesh,
wrong-window/version, incomplete 1..30 coverage or restoration failures abort.
The GUI measurements remain sequential observational samples, not ABBA.
"""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return json.loads(raw), {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def all_true(value):
    return bool(value) and all(all_true(item) if isinstance(item, dict) else item is True for item in value.values())


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def sample(path, version, shading, pid, min_run_id):
    report, identity = read(path)
    prefix = identity["path"] + ": "
    require(report.get("operation") == "sample" and report.get("completed") is True, prefix + "not a completed sample")
    match = re.search(r"_(\d+)$", report.get("id", ""))
    require(match and int(match.group(1)) >= min_run_id, prefix + "outside the explicit current measurement epoch")
    require(report.get("pid") == pid, prefix + "wrong process")
    addon = report.get("addons", {}).get("character_designer", {})
    require(addon.get("version") == [0, 77, version], prefix + "wrong loaded live version")
    require(not addon.get("forearm_errors") and addon.get("forearm_busy") is False, prefix + "unhealthy live runtime")
    require(not report.get("errors") and report.get("callback_exceptions") == {}
            and all(component.get("exception_count") == 0 for component in report.get("components", {}).values()),
            prefix + "callback or sample exception")
    require(report.get("measurement_started") is True and report.get("event_limit_reached") is False
            and report.get("stop_reason") == "elapsed", prefix + "partial/truncated measurement")
    require(report.get("disk_unchanged") is True and report.get("disk_before") == report.get("disk_after")
            and report.get("dirty_before") == report.get("dirty_after"), prefix + "disk/dirty restoration differs")
    require(all_true(report.get("restored", {})), prefix + "restoration guard failed or missing")
    channel = report.get("artist_channel_check", {})
    require(channel.get("raw_channels_equal") is True and channel.get("managed_coordinates_equal") is True,
            prefix + "raw/managed output restoration failed")
    mesh = report.get("mesh_diagnostic", {})
    require(mesh.get("controls_equal_after_frame_and_channel_restore") is True
            and mesh.get("runtime_errors_restored_equal") is True
            and mesh.get("before_controls") == mesh.get("after_controls"), prefix + "mesh/runtime restoration differs")
    for phase in ("runtime_errors_before", "runtime_errors_at_measurement_end", "runtime_errors_after_restoration"):
        require(mesh.get(phase) and all(not value["errors"] and value["busy"] is False for value in mesh[phase].values()),
                prefix + "runtime error/busy state or absent witness in " + phase)
    request = report.get("request", {})
    require(request.get("shading") == shading and request.get("warmup_seconds") == 2
            and request.get("seconds") == 16, prefix + "wrong case/warmup/duration")
    require(request.get("hide_objects") == [] and request.get("disable_modifiers") == {}
            and request.get("disable_viewport_objects") == [], prefix + "mesh diagnostic is not a complete-model comparison")
    before = report.get("before", {})
    require(before.get("mode") == "OBJECT" and before.get("active_object") == "Cosha"
            and before.get("selected_objects") == [] and before.get("frame") == 21
            and before.get("subframe") == 0.0 and before.get("sync_mode") == "NONE"
            and before.get("playing") is False, prefix + "changed starting context")
    evaluated = sorted({event["frame"] for event in report.get("frame_boundaries", [])})
    displayed = sorted({event["frame"] for event in report.get("display_boundaries", [])})
    require(evaluated == list(range(1, 31)) and displayed == list(range(1, 31)), prefix + "does not cover all 30 evaluated/displayed frames")
    hz = report.get("observed_displayed_frame_change_hz")
    require(positive(hz), prefix + "invalid displayed-change rate")
    components = report.get("components", {})
    row = {"evidence": identity, "id": report["id"], "created_utc": report["created_utc"],
           "live_version": addon["version"], "pid": pid, "request": request,
           "restore_all_passed": True, "callback_exception_count": 0,
           "all_30_evaluated_frames": True, "all_30_displayed_frames": True,
           "evaluated_frame_count": report["evaluated_frame_count"],
           "displayed_frame_change_count": report["displayed_frame_change_count"],
           "displayed_frame_change_hz": hz, "frame_evaluation_median_ms": report["frame_evaluation_ms"]["median"]}
    for short, function in (("forearm_update", "update_runtime"), ("forearm_prepare", "_prepare_runtime_records"),
                            ("forearm_calculate", "_calculate_records")):
        component = components.get("function:character_designer.forearm_twist." + function, {})
        require(positive(component.get("mean_ms")) and component.get("count", 0) > 0,
                prefix + "missing active Forearm route witness")
        row[short + "_mean_ms"] = component["mean_ms"]
        row[short + "_calls"] = component["count"]
    comparable = {"pid": pid, "blender": report["blender"], "disk": report["disk_before"],
                  "before": before, "geometry": mesh["before_geometry"], "controls": mesh["before_controls"]}
    return row, comparable


def aggregate(rows, key):
    values = [row[key] for row in rows]
    return {"n_samples": 2, "two_sample_midpoint": statistics.fmean(values), "sample_min": min(values), "sample_max": max(values)}


def main(args):
    groups, witnesses, paths = {}, [], []
    for name, version, shading in (("material40", 40, "MATERIAL"), ("solid40", 40, "SOLID"),
                                  ("material41", 41, "MATERIAL"), ("solid41", 41, "SOLID")):
        rows = []
        for path in getattr(args, name):
            row, witness = sample(path, version, shading, args.expected_pid, args.min_run_id)
            rows.append(row); witnesses.append(witness); paths.append(row["evidence"]["path"])
        rows.sort(key=lambda row: row["created_utc"])
        groups[name] = rows
    require(len(set(paths)) == 8, "Supply eight distinct final report paths")
    require(all(witness == witnesses[0] for witness in witnesses), "Current window/file/model/starting context differs across samples")
    comparisons = {}
    for case in ("material", "solid"):
        old, new = groups[case + "40"], groups[case + "41"]
        require(old[0]["request"] == old[1]["request"] == new[0]["request"] == new[1]["request"], "Case requests differ: " + case)
        values = {}
        for key in ("displayed_frame_change_hz", "frame_evaluation_median_ms", "forearm_update_mean_ms",
                    "forearm_prepare_mean_ms", "forearm_calculate_mean_ms"):
            baseline, candidate = aggregate(old, key), aggregate(new, key)
            values[key] = {"live_07740": baseline, "live_07741": candidate,
                           "observed_midpoint_percent_change": 100 * (candidate["two_sample_midpoint"] / baseline["two_sample_midpoint"] - 1)}
        comparisons[case] = values
    summary = {"schema": "x.current-window-playback-comparison/1", "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "accepted": True, "artist_pid": args.expected_pid, "epoch_min_run_id": args.min_run_id,
               "selection": "Only the eight explicitly supplied final reports; historical/failed reports are not scanned",
               "method": "Two sequential observational GUI samples per live version and case; no controlled GUI ABBA or significance claim",
               "current_window_file": witnesses[0]["disk"], "samples": groups, "observed_comparisons": comparisons,
               "limits": ["POST_PIXEL changed-frame events are viewport draw callbacks, not physical monitor presentation.",
                          "Equal window/context/request and full frame coverage do not control shared CPU/GPU/memory load or draw warm-state drift.",
                          "Two GUI samples per cell do not establish a causal marginal gain or statistical significance.",
                          "Nested inclusive Forearm timings overlap and must not be added.",
                          "Background frame evaluation is separate evidence; no reciprocal timing-to-GUI-FPS conversion or additive benefit claim."],
               "artist_save_deploy_refresh_or_goal_status": "Not determined by this analysis; main closeout receipts own those states"}
    if args.background_reference:
        background, evidence = read(args.background_reference)
        require(background.get("candidate_version") == "0.77.41" and background.get("observed_background_results", {}).get("all_observed_outputs_equal") is True,
                "Background reference is not the accepted .41 preparation evidence")
        summary["separate_background_reference"] = {"evidence": evidence, "saved_input": background["artist"],
                                                   "results": background["observed_background_results"],
                                                   "scope": "Existing private single-thread same-process ABBA; approximately 5.3% background time improvement, not viewport FPS"}
    output = Path(args.output).resolve()
    require(str(output) not in paths, "Output may not overwrite an input report")
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"accepted": True, "output": str(output), "cases": comparisons}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for group in ("material40", "solid40", "material41", "solid41"):
        parser.add_argument("--" + group, nargs=2, required=True)
    parser.add_argument("--expected-pid", type=int, default=24416)
    parser.add_argument("--min-run-id", type=int, default=1792002610000000000)
    parser.add_argument("--background-reference")
    parser.add_argument("--output", required=True)
    main(parser.parse_args())
