"""Two read-only initial-source witness passes; no clone/seek/manual solver."""
import argparse
import ctypes
from ctypes import wintypes
import datetime
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support_v8 as witness
from private_playback_native_runner_v8 import assert_fixed_source_reference_coverage

STAGE_SHA = "5c7965ef74e99ed8036bc57ad639cb4db37e6501bb580483a676d4b2fd6cc3c0"
INPUT_SHA = "40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def process_memory():
    """Current/peak lifetime RSS for this worker, not a sampled scan-only peak."""
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
            "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    current = ctypes.WinDLL("kernel32", use_last_error=True).GetCurrentProcess
    current.argtypes, current.restype = [], wintypes.HANDLE
    get_info = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    get_info.argtypes, get_info.restype = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD], wintypes.BOOL
    info = Counters()
    info.cb = ctypes.sizeof(info)
    if not get_info(current(), ctypes.byref(info), info.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"rss_bytes": info.WorkingSetSize, "peak_process_lifetime_rss_bytes": info.PeakWorkingSetSize}


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index("--")]
    require(bpy.app.background and "--factory-startup" in native and not bpy.data.filepath, "Fresh private factory background worker required")
    require(any(value in ("-t", "--threads") and native[index + 1] == "1" for index, value in enumerate(native[:-1])), "Native -t1 required")
    input_file, artist = Path(args.input).resolve(), Path(args.artist).resolve()
    require(input_file != artist and not os.path.samefile(input_file, artist), "Never open artist or its hard link")
    input_before, artist_before = witness.pin(input_file), witness.pin(artist)
    require(input_before["sha256"] == INPUT_SHA and input_before["bytes"] == 34691613, "Fixed40644 input required")
    manifest_path = Path(args.source_manifest).resolve()
    manifest_pin = witness.pin(manifest_path)
    require(manifest_pin["sha256"] == STAGE_SHA and Path(args.addons).resolve() == manifest_path.parent / "addons", "Protected Stage06 required")
    require(witness.pin(HERE / "private_playback_native_runner_v8.py")["sha256"] == "c67af8e103c7a6ad93dce723e5bfda3edcc70efde4e96c49cb49a35be6593f55", "Loaded coverage gate source changed")
    package = Path(args.addons).resolve() / "character_designer"
    manifest = json.loads(manifest_path.read_text())
    sources = witness.verify_package_manifest(package, manifest)
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module("character_designer")
    runtime = importlib.import_module("character_designer.forearm_twist")
    require(Path(addon.__file__).resolve().parent == package, "Different addon imported")
    scripts = {path.name: witness.pin(path) for path in (Path(__file__), Path(witness.__file__),
        Path(witness._extension.__file__), HERE / "private_playback_native_runner_v8.py")}
    report.update(input_before=input_before, artist_before=artist_before, source_manifest=manifest_pin,
                  scripts=scripts, witness_sources=witness.witness_dependency_pins(),
                  blender=bpy.app.version_string, passes=[], version=list(addon.bl_info["version"]))
    handlers_before = witness.handler_snapshot()
    registered = False
    try:
        addon.register()
        registered = True
        opened = bpy.ops.wm.open_mainfile(filepath=str(input_file))
        require("FINISHED" in opened and Path(bpy.data.filepath).resolve() == input_file, "Private fixed input open failed")
        source = bpy.context.scene
        bpy.context.view_layer.update()
        require(not runtime._ERRORS, "Source Forearm errors: " + repr(runtime._ERRORS))
        context_before = (source.name_full, source.frame_current, source.frame_subframe, bpy.context.view_layer.name)
        report["loaded_context"] = list(context_before)
        first = None
        for index in range(2):
            print("SOURCE_BULK_SCAN_BEGIN", index + 1, flush=True)
            memory_before = process_memory()
            began = time.perf_counter_ns()
            props = witness.source_property_witness(source)
            elapsed_ms = (time.perf_counter_ns() - began) / 1e6
            memory_after = process_memory()
            coverage = assert_fixed_source_reference_coverage(source, props, input_before)
            extension = props["registered_source_and_external_objects"]
            scope = extension["scope"]
            report["passes"].append({"pass": index + 1, "elapsed_ms": elapsed_ms, "sha256": props["sha256"],
                "component_count": len(props["components"]), "native_RNA_fields_read": scope["native_RNA_fields_read"],
                "native_ID_reference_rows": scope["native_ID_reference_rows"], "keyframe_bulk": scope["keyframe_bulk"],
                "coverage": coverage, "memory_before": memory_before, "memory_after": memory_after})
            if first is None:
                first = props
            else:
                report["two_readonly_source_witnesses_exact"] = first == props
                require(first == props, "Initial source witness changed across two read-only scans")
            print("SOURCE_BULK_SCAN_END", index + 1, round(elapsed_ms, 3), scope["keyframe_bulk"]["points"], flush=True)
        report["source_context_exact"] = context_before == (source.name_full, source.frame_current, source.frame_subframe, bpy.context.view_layer.name)
        require(report["source_context_exact"], "Read-only scan changed saved frame/context")
    finally:
        errors = []
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        checks = {"normal_handlers_restored": handlers_before == witness.handler_snapshot(),
                  "runtime_guard_released": not runtime._BUSY,
                  "owned_forearm_lifecycle_timer_gone": not bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle),
                  "input_disk_unchanged": input_before == witness.pin(input_file),
                  "artist_disk_unchanged": artist_before == witness.pin(artist),
                  "stage_sources_unchanged": sources == witness.verify_package_manifest(package, manifest) and manifest_pin == witness.pin(manifest_path),
                  "witness_sources_unchanged": report["witness_sources"] == witness.witness_dependency_pins(),
                  "scripts_unchanged": scripts == {name: witness.pin(value["path"]) for name, value in scripts.items()}}
        report["cleanup"] = {"errors": errors, **checks}
        require(not errors and all(checks.values()), "Source-scan cleanup/protected boundary failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    require(not path.exists(), "Never overwrite evidence")
    report = {"schema": "x.initial-source-bulk-scan/1", "completed": False, "pid": os.getpid(),
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "no_artist_open_or_save": True, "no_scene_save": True, "no_clone": True,
        "no_frame_seek_or_manual_solver": True, "performance_acceptance": False,
        "limits": ["Two initial raw/source-reference witness scans only; no 30-frame, evaluated-scene equivalence or GUI FPS proof.",
                   "Process peak RSS is lifetime high-water memory including load, not an isolated scan peak.",
                   "Normal addon register/load/unregister lifecycle retained; no handler deferral."]}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
