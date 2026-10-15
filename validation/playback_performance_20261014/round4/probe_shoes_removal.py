"""One-shot private background diagnosis; no artist access or scene save.

Reopen the pinned saved copy for each case: complete, delete Shoes, disable
Cosha visibility and delete Shoes. This diagnoses failed validation separately
from native geometry cost. A failed/paused corrective route is not a fix.
Only runtime functions are timed; native handler signatures are untouched.
"""

import argparse
from array import array
from collections import Counter
import datetime
import functools
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time
import traceback

import bpy


EXPECTED_INPUT_SHA256 = "40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721"
EXPECTED_INPUT_BYTES = 34691613
FRAMES = (2, 6, 10, 14, 18, 22, 26, 30)


def pin(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def managed_summary(runtime, scene, coordinates=False):
    result = {}
    for obj in scene.objects:
        if obj.type != "MESH" or runtime.RECORD_KEY not in obj:
            continue
        keys = []
        for side, record in runtime._records(obj).items():
            key = runtime._managed_key(obj, side, record, required=False, repair_name=False)
            row = {"side": side, "enabled": record.get("enabled", True),
                   "support_vertices": len(record["vertices"]),
                   "key": key.name if key else None,
                   "mute": bool(key.mute) if key else None,
                   "value": float(key.value) if key else None}
            if coordinates and key is not None:
                values = array("f", [0.0]) * (len(key.data) * 3)
                key.data.foreach_get("co", values)
                row["coordinate_sha256"] = hashlib.sha256(values.tobytes()).hexdigest()
            keys.append(row)
        result[obj.name] = keys
    return result


def reference_summary(target, rig, shoe_identity=None):
    raw = rig.get(target.SESSION)
    if not isinstance(raw, str):
        return {"adopted_record_present": False}
    encoded = json.loads(raw)
    references = rig.get(target.REFS, {})
    paths = {}

    def walk(value, path):
        if isinstance(value, dict):
            if set(value) == {"$id"}:
                paths.setdefault(value["$id"], []).append(path)
            else:
                for key, entry in value.items():
                    walk(entry, path + "." + str(key))
        elif isinstance(value, list):
            for index, entry in enumerate(value):
                walk(entry, path + "[" + str(index) + "]")

    walk(encoded, "$")
    missing, related = [], []
    related_names = set(shoe_identity or ())
    for key, field_paths in paths.items():
        value = references.get(key)
        if value is None:
            missing.append({"key": key, "paths": field_paths})
        elif getattr(value, "name", None) in related_names:
            related.append({"key": key, "name": value.name, "id_type": type(value).__name__,
                            "paths": field_paths})
    return {"adopted_record_present": True, "encoded_reference_count": len(paths),
            "native_reference_count": len(references), "missing": missing,
            "shoe_related_references": related}


def proof_result(callback):
    started = time.perf_counter_ns()
    try:
        value = callback()
        return {"passed": True, "result_type": type(value).__name__,
                "elapsed_ms": (time.perf_counter_ns() - started) / 1_000_000}
    except Exception as exc:
        return {"passed": False, "error_type": type(exc).__name__, "error": str(exc),
                "elapsed_ms": (time.perf_counter_ns() - started) / 1_000_000}


class RuntimeTiming:
    def __init__(self, runtime):
        self.runtime = runtime
        self.original = runtime.update_runtime
        self.reset()

        @functools.wraps(self.original)
        def measured(*args, **kwargs):
            began = time.perf_counter_ns()
            try:
                return self.original(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter_ns() - began) / 1_000_000
                self.calls += 1
                self.milliseconds.append(elapsed)

        self.wrapped = measured
        runtime.update_runtime = measured

    def reset(self):
        self.calls = 0
        self.milliseconds = []

    def restore(self):
        if self.runtime.update_runtime is not self.wrapped:
            raise RuntimeError("Private runtime timing wrapper ownership changed")
        self.runtime.update_runtime = self.original


def delete_shoe(scene, shoe, method):
    name = shoe.name
    if method == "datablock":
        bpy.data.objects.remove(shoe, do_unlink=True)
        result = ["DIRECT_DATABLOCK_REMOVE"]
    else:
        active = bpy.context.view_layer.objects.active
        if active and active.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        shoe.select_set(True)
        bpy.context.view_layer.objects.active = shoe
        native = bpy.ops.object.delete(use_global=False)
        if "FINISHED" not in native:
            raise RuntimeError("Private native object.delete failed: " + repr(native))
        result = sorted(native)
    return {"method": method, "native_result": result,
            "shoe_still_in_scene": scene.objects.get(name) is not None,
            "shoe_still_in_bpy_data": bpy.data.objects.get(name) is not None,
            "scope": "Private in-memory scene only; native default delete and forced datablock delete may retain different references"}


def main(args, report):
    assert bpy.app.background, "Only a private background process is permitted"
    input_path, artist_path = Path(args.input).resolve(), Path(args.artist).resolve()
    assert input_path != artist_path, "Never open the artist file for this probe"
    input_before, artist_before = pin(input_path), pin(artist_path)
    assert input_before["sha256"] == EXPECTED_INPUT_SHA256 and input_before["bytes"] == EXPECTED_INPUT_BYTES
    report.update(input_before=input_before, artist_before=artist_before,
                  input_matches_artist_at_start=input_before["sha256"] == artist_before["sha256"],
                  script=pin(__file__), blender=bpy.app.version_string,
                  frame_sequence=list(FRAMES), deletion_method=args.delete_method,
                  cosha_hide_method=args.hide_method)
    sys.path.insert(0, str(Path(args.addons).resolve()))
    import character_designer as addon
    from character_designer import forearm_twist as runtime, animation_worklist_target as target
    from character_designer import forearm_original_inventory as inventory, limb_ik
    expected_package = Path(args.addons).resolve() / "character_designer"
    assert Path(addon.__file__).resolve().parent == expected_package
    assert tuple(addon.bl_info["version"]) == (0, 77, 40), "Use the verified installed .40, not canonical .41"
    report.update(source_version=list(addon.bl_info["version"]),
                  sources=[pin(module.__file__) for module in (addon, runtime, target, inventory, limb_ik)],
                  source_metadata_changed=False)
    addon.register()
    report["cases"] = []
    for label in ("complete", "delete_shoes", "hide_cosha_and_delete_shoes"):
        opened = bpy.ops.wm.open_mainfile(filepath=str(input_path))
        assert "FINISHED" in opened and Path(bpy.data.filepath).resolve() == input_path
        scene = bpy.context.scene
        rig, cosha, shoe = (scene.objects.get(name) for name in ("CoshaRig", "Cosha", "Shoes"))
        assert rig and cosha and shoe and cosha.type == shoe.type == "MESH"
        shoe_names = {shoe.name, shoe.data.name}
        if shoe.animation_data and shoe.animation_data.action:
            shoe_names.add(shoe.animation_data.action.name)
        row = {"label": label, "scene": scene.name,
               "references_before": reference_summary(target, rig, shoe_names),
               "control_rest_before": proof_result(lambda: target.control_rest_view(rig)),
               "inventory_before": proof_result(lambda: inventory.validate(rig)),
               "errors_before": dict(runtime._ERRORS),
               "managed_before": managed_summary(runtime, scene, coordinates=True)}
        assert not row["errors_before"] and row["inventory_before"]["passed"], "Complete input must begin valid"
        if label == "hide_cosha_and_delete_shoes":
            if args.hide_method == "hide_set":
                cosha.hide_set(True, view_layer=bpy.context.view_layer)
            else:
                cosha.hide_viewport = True
        if label != "complete":
            row["deletion"] = delete_shoe(scene, shoe, args.delete_method)
        row["references_after_mutation"] = reference_summary(target, rig, shoe_names)
        row["control_rest_after_mutation"] = proof_result(lambda: target.control_rest_view(rig))
        row["inventory_after_mutation"] = proof_result(lambda: inventory.validate(rig))
        timing = RuntimeTiming(runtime)
        try:
            for frame in (1, 3):
                scene.frame_set(frame)
                bpy.context.view_layer.update()
            rows = []
            for frame in FRAMES:
                timing.reset()
                began = time.perf_counter_ns()
                scene.frame_set(frame)
                frame_set_done = time.perf_counter_ns()
                bpy.context.view_layer.update()
                done = time.perf_counter_ns()
                rows.append({"frame": frame, "frame_set_ms": (frame_set_done - began) / 1_000_000,
                             "view_layer_update_ms": (done - frame_set_done) / 1_000_000,
                             "total_evaluation_ms": (done - began) / 1_000_000,
                             "runtime_calls": timing.calls, "runtime_inclusive_ms": sum(timing.milliseconds),
                             "runtime_mean_call_ms": statistics.fmean(timing.milliseconds) if timing.milliseconds else None,
                             "errors": dict(runtime._ERRORS), "managed": managed_summary(runtime, scene)})
            row.update(frames=rows, median_total_evaluation_ms=statistics.median(value["total_evaluation_ms"] for value in rows),
                       median_runtime_inclusive_ms=statistics.median(value["runtime_inclusive_ms"] for value in rows),
                       errors_after=dict(runtime._ERRORS), managed_after=managed_summary(runtime, scene, coordinates=True),
                       performance_acceptance=False, no_scene_save=True)
            report["cases"].append(row)
            print("CASE", label, round(row["median_total_evaluation_ms"], 3), row["errors_after"], flush=True)
        finally:
            timing.restore()
    report["input_after"], report["artist_after"] = pin(input_path), pin(artist_path)
    assert report["input_after"] == input_before and report["artist_after"] == artist_before
    report.update(input_disk_unchanged=True, artist_disk_unchanged=True,
                  no_save_operation=True, no_live_artist_access=True, no_deploy=True,
                  limits=["Private saved-copy background frame evaluation only; not GUI FPS or current unsaved artist state.",
                          "Only Character Designer registration; current GUI external handlers/drawing/shaders are absent.",
                          "A failed/muted correction is diagnostic and cannot be accepted as optimization or model equivalence.",
                          "Nested runtime time is inside total evaluation and cannot be added to it.",
                          "Eight warm hot frames per case under shared load; not a final paired performance acceptance.",
                          "Deleting native Object datablocks and default object.delete may differ in surviving ID references."])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "report"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--hide-method", choices=("hide_set", "hide_viewport"), default="hide_viewport")
    parser.add_argument("--delete-method", choices=("operator", "datablock"), default="operator")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    report = {"schema": "x.shoes-removal-private-probe/1", "completed": False,
              "pid": os.getpid(), "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "model_and_reasoning_effort": "unrecorded"}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
