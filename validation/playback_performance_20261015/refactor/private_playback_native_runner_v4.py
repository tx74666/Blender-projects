"""Private frozen differential v4. Original v2/v3 failed evidence is preserved.

Golden outputs and each .41 authoring block run without cloned IDs present.
Each candidate block owns a fresh complete cloned scene and single-use validated
source templates. Preparation, hash work and scene switching are not hot timing.
"""
import argparse
import datetime
import importlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support as witness

ALL_FRAMES = tuple(range(1, 31))
HOT_FRAMES = (2, 6, 10, 14, 18, 22, 26, 30)
WARM_FRAMES = (1, 3)
BLOCK_ORDER = ("authoring", "frozen", "frozen", "authoring") * 2
EXPECTED_INPUTS = {
    "40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721": 34691613,
    "ad5bf8ecbfe45d1ca9041c2d3608f0defe68c605e8ad10cd87a95bc946d5ae92": 34845822,
}


def source_animation_layout(scene):
    """Read-only compact native bindings for future explicit helper bake design.

    This is metadata only, not an animation content/provenance validation or
    permission to bake. No FCurves, channels or keys are copied or rewritten.
    """
    def identity(item):
        if item is None:
            return None
        return {"type": type(item).__name__, "name": item.name_full,
                "pointer": int(item.as_pointer()), "session_uid": getattr(item, "session_uid", None)}
    def slot(item):
        if item is None:
            return None
        return {name: getattr(item, name) for name in
                ("handle", "identifier", "target_id_type", "name_display") if hasattr(item, name)}
    def action(item):
        if item is None:
            return None
        return {"id": identity(item), "slots": [slot(value) for value in getattr(item, "slots", ())],
                "frame_range": [float(value).hex() for value in item.frame_range],
                "use_fake_user": bool(item.use_fake_user)}
    ids = {scene.as_pointer(): scene}
    for obj in scene.objects:
        ids[obj.as_pointer()] = obj
        data = getattr(obj, "data", None)
        if data is not None:
            ids[data.as_pointer()] = data
            keys = getattr(data, "shape_keys", None)
            if keys is not None:
                ids[keys.as_pointer()] = keys
    result = []
    strip_fields = ("type", "mute", "frame_start", "frame_end", "action_frame_start", "action_frame_end",
                    "blend_type", "extrapolation", "influence", "blend_in", "blend_out", "use_auto_blend",
                    "repeat", "scale", "strip_time", "use_animated_time", "use_animated_time_cyclic",
                    "use_animated_influence", "use_reverse", "action_slot_handle")
    for item in sorted(ids.values(), key=lambda value: (type(value).__name__, value.name_full)):
        animation = getattr(item, "animation_data", None)
        if animation is None:
            continue
        row = {"id": identity(item), "action": action(animation.action),
               "action_slot": slot(getattr(animation, "action_slot", None)),
               "drivers_count": len(animation.drivers),
               "use_nla": bool(animation.use_nla), "tracks": []}
        for name in ("action_blend_type", "action_extrapolation", "action_influence", "use_tweak_mode"):
            if hasattr(animation, name):
                value = getattr(animation, name)
                row[name] = float(value).hex() if isinstance(value, float) else value
        for track in animation.nla_tracks:
            track_row = {"name": track.name, "mute": bool(track.mute), "is_solo": bool(track.is_solo),
                         "pointer": int(track.as_pointer()), "strips": []}
            for strip in track.strips:
                strip_row = {"name": strip.name, "pointer": int(strip.as_pointer()),
                             "action": action(strip.action), "action_slot": slot(getattr(strip, "action_slot", None))}
                for name in strip_fields:
                    if hasattr(strip, name):
                        value = getattr(strip, name)
                        strip_row[name] = float(value).hex() if isinstance(value, float) else value
                track_row["strips"].append(strip_row)
            row["tracks"].append(track_row)
        result.append(row)
    return {"schema": "x.source-animation-layout-observation/1", "source_scene": scene.name,
            "bindings": result, "scene_frame": scene.frame_current,
            "scene_frame_start": scene.frame_start, "scene_frame_end": scene.frame_end,
            "scene_fps": scene.render.fps, "scene_fps_base": float(scene.render.fps_base).hex(),
            "read_only": True, "full_curves_included": False,
            "limits": "Initial native bindings/slots/NLA layout only; not bake readiness, content equality or adoption."}


def field(session, name):
    return session[name] if isinstance(session, dict) else getattr(session, name)


def select_scene(scene):
    import bpy
    if bpy.context.window is None:
        raise RuntimeError("A private Window is required for explicit graph identity")
    bpy.context.window.scene = scene
    layer = scene.view_layers[0]
    bpy.context.window.view_layer = layer
    if bpy.context.scene.as_pointer() != scene.as_pointer() or bpy.context.view_layer.as_pointer() != layer.as_pointer():
        raise RuntimeError("Native Scene/ViewLayer differs from requested branch")


def stage_evidence(values):
    expected = {"read_ms", "solve_ms", "publish_ms", "total_ms", "published", "key_count", "corrected_vertex_count"}
    if not isinstance(values, dict) or set(values) != expected or values["published"] is not True:
        raise RuntimeError("Unexpected/unpublished binding evaluation telemetry")
    for key in expected - {"published"}:
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
            raise RuntimeError("Invalid stage/count evidence")
    return values


def isolation(session, source_scene, runtime):
    import bpy
    scene, objects, ids = field(session, "scene"), field(session, "object_map"), field(session, "id_map")
    if field(session, "source_scene") is not source_scene or scene is source_scene:
        raise RuntimeError("Builder did not isolate the requested source Scene")
    if set(objects) != set(source_scene.objects) or set(objects.values()) != set(scene.objects):
        raise RuntimeError("Every full-model Scene object must map exactly once")
    if len({obj.as_pointer() for obj in objects.values()}) != len(objects):
        raise RuntimeError("Object map is not one to one")
    for source, clone in objects.items():
        if source is clone or source.type != clone.type or source.name in scene.objects or clone.name in source_scene.objects:
            raise RuntimeError("Source/clone object identity, type or Scene membership changed")
        shared_image = source.type == "EMPTY" and isinstance(source.data, bpy.types.Image)
        if shared_image:
            if clone.data != source.data or source.data in ids:
                raise RuntimeError("Readonly Image Empty must share only its original Image, outside private ID map")
        elif source.data is not None and source.data == clone.data:
            raise RuntimeError("Writable object data is shared")
        pairs = [(source, clone)]
        if source.data is not None and not shared_image:
            pairs.append((source.data, clone.data))
        if source.type == "MESH" and source.data.shape_keys:
            if clone.data.shape_keys is None or clone.data.shape_keys is source.data.shape_keys:
                raise RuntimeError("Shape Keys were not isolated")
            pairs.append((source.data.shape_keys, clone.data.shape_keys))
        for original_id, copied_id in pairs:
            old_ad, new_ad = getattr(original_id, "animation_data", None), getattr(copied_id, "animation_data", None)
            if old_ad and old_ad.action and (new_ad is None or new_ad.action is old_ad.action):
                raise RuntimeError("Active Action is shared or missing")
    eligible = {source: target for source, target in objects.items() if source.type == "MESH" and runtime.RECORD_KEY in source}
    if not eligible or dict(field(session, "objects")) != eligible:
        raise RuntimeError("Builder must cover all and only calibrated meshes")
    for source, target in eligible.items():
        if objects.get(runtime._check_mesh(source)) is not runtime._check_mesh(target):
            raise RuntimeError("Calibrated native Armature dependency is not remapped")
    reverse = {}
    for source, target in ids.items():
        if source is target or target.as_pointer() in reverse:
            raise RuntimeError("Explicit cloned ID map is not private/one to one")
        reverse[target.as_pointer()] = source
    return scene, objects, eligible, reverse


def main(args, report):
    import bpy
    if not bpy.app.background:
        raise RuntimeError("Private background process required")
    native = sys.argv[:sys.argv.index("--")]
    if "--factory-startup" not in native:
        raise RuntimeError("Factory startup required for owned registration/foreign handler protection")
    if not any(value in ("-t", "--threads") and native[i + 1] == "1" for i, value in enumerate(native[:-1])):
        raise RuntimeError("Explicit native -t 1 required")
    input_path, artist_path = Path(args.input).resolve(), Path(args.artist).resolve()
    if input_path == artist_path or os.path.samefile(input_path, artist_path):
        raise RuntimeError("Never open artist or a hard link to it")
    before_input, before_artist = witness.pin(input_path), witness.pin(artist_path)
    if EXPECTED_INPUTS.get(before_input["sha256"]) != before_input["bytes"]:
        raise RuntimeError("Input is not an accepted saved-copy pin")
    package, manifest_path = Path(args.addons).resolve() / "character_designer", Path(args.source_manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema") != "x.frozen-playback-source-seal/1":
        raise RuntimeError("Unexpected source seal")
    sources_before = witness.verify_package_manifest(package, manifest)
    report.update(input_before=before_input, artist_before=before_artist, source_manifest=witness.pin(manifest_path),
                  sources=sources_before, script=witness.pin(__file__), witness_script=witness.pin(witness.__file__),
                  oracle={"path": str(witness.ORACLE_PATH), "sha256": witness.ORACLE_SHA256},
                  blender=bpy.app.version_string, thread_request=1, frames=list(ALL_FRAMES), hot_frames=list(HOT_FRAMES),
                  model="gpt-6.1-sol", reasoning_effort="ultra",
                  model_and_reasoning_effort="gpt-6.1-sol / ultra",
                  model_source="Current root task local index verified by root; inherited task settings.",
                  preparations=[], frame_checks=[], blocks=[], disposable_cleanups=[])
    report["admission_only"] = bool(args.admission_only)
    report["all_30_complete_outputs_exact"] = False
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module("character_designer")
    runtime = importlib.import_module("character_designer.forearm_twist")
    core = importlib.import_module("character_designer.forearm_twist_playback_core")
    if not args.builder_module.startswith("character_designer."):
        raise RuntimeError("Builder must be in pinned package")
    builder = getattr(importlib.import_module(args.builder_module), args.builder_function)
    if Path(addon.__file__).resolve().parent != package:
        raise RuntimeError("Native imported a different package")
    report["version"] = list(addon.bl_info["version"])
    registered, source_scene, initial_context, initial_output, initial_props = False, None, None, None, None
    session, bindings, templates, private_ids = None, [], [], set()
    handlers_before = witness.handler_snapshot()

    def close_disposable():
        nonlocal session, bindings, templates, private_ids
        if session is None and not bindings and not templates:
            return
        errors = []
        for item in reversed(bindings):
            try:
                item.close()
            except BaseException:
                errors.append(traceback.format_exc())
        for template in templates:
            try:
                core.discard_template(template)
            except BaseException:
                errors.append(traceback.format_exc())
        if source_scene is not None:
            try:
                select_scene(source_scene)
            except BaseException:
                errors.append(traceback.format_exc())
        if session is not None:
            try:
                field(session, "close")()
            except BaseException:
                errors.append(traceback.format_exc())
        remaining = sorted(private_ids & witness.native_id_pointers())
        report["disposable_cleanups"].append({"errors": errors, "remaining_owned_id_pointers": remaining,
                                             "all_owned_ids_removed": not remaining})
        session, bindings, templates, private_ids = None, [], [], set()
        if errors or remaining:
            raise RuntimeError("Disposable cleanup failed")

    try:
        addon.register()
        registered = True
        opened = bpy.ops.wm.open_mainfile(filepath=str(input_path))
        if "FINISHED" not in opened or Path(bpy.data.filepath).resolve() != input_path:
            raise RuntimeError("Private input open failed")
        source_scene = bpy.context.scene
        source_pairs = [(obj.name, obj) for obj in source_scene.objects]
        initial_context = (source_scene.frame_current, source_scene.frame_subframe)
        report["initial_source_animation_layout"] = source_animation_layout(source_scene)
        bpy.context.view_layer.update()
        if runtime._ERRORS:
            raise RuntimeError("Input Forearm errors: " + repr(runtime._ERRORS))

        def evaluate(scene, frame, current_bindings=None):
            select_scene(scene)
            began = time.perf_counter_ns()
            scene.frame_set(frame)
            a = time.perf_counter_ns()
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            b = time.perf_counter_ns()
            if current_bindings is None:
                for obj in scene.objects:
                    if obj.type == "MESH" and runtime.RECORD_KEY in obj:
                        runtime._calculate_object(obj, graph)
                stages = []
            else:
                stages = [stage_evidence(binding.evaluate(graph)) for binding in current_bindings]
            c = time.perf_counter_ns()
            bpy.context.view_layer.update()
            d = time.perf_counter_ns()
            if runtime._ERRORS:
                raise RuntimeError("Runtime errors during pipeline: " + repr(runtime._ERRORS))
            return {"frame": frame, "frame_advance_ms": (a - began) / 1e6, "first_native_update_ms": (b - a) / 1e6,
                    "corrective_inclusive_ms": (c - b) / 1e6, "final_native_update_ms": (d - c) / 1e6,
                    "total_pipeline_ms": (d - began) / 1e6, "binding_stage_ms": stages}

        def create_disposable(phase):
            nonlocal session, bindings, templates, private_ids
            if session is not None:
                raise RuntimeError("Previous disposable not closed")
            select_scene(source_scene)
            bpy.context.view_layer.update()
            protected_output = witness.frame_witness(source_scene, source_pairs, runtime, {})
            protected_props = witness.source_property_witness(source_scene)
            existing_ids = witness.native_id_pointers()
            began = time.perf_counter_ns()
            source_templates = {}
            for obj in source_scene.objects:
                if obj.type == "MESH" and runtime.RECORD_KEY in obj:
                    template = core.capture(obj, bpy.context.evaluated_depsgraph_get())
                    templates.append(template)
                    source_templates[obj] = template
            a = time.perf_counter_ns()
            try:
                session = builder(source_scene)
            finally:
                private_ids = witness.native_id_pointers() - existing_ids
            b = time.perf_counter_ns()
            scene, objects, eligible, reverse = isolation(session, source_scene, runtime)
            select_scene(scene)
            bpy.context.view_layer.update()
            for source, target in eligible.items():
                bindings.append(core.prepare(target, bpy.context.evaluated_depsgraph_get(), isolated_scene=scene,
                    source_mesh=source, source_rig=runtime._check_mesh(source), template=source_templates[source]))
            c = time.perf_counter_ns()
            report["preparations"].append({"phase": phase, "source_canonical_capture_ms": (a - began) / 1e6,
                "actor_clone_ms": (b - a) / 1e6, "target_compile_ms": (c - b) / 1e6, "total_ms": (c - began) / 1e6,
                "binding_metadata": [binding.inspect() for binding in bindings]})
            select_scene(source_scene)
            bpy.context.view_layer.update()
            same = witness.compare_witness(protected_output, witness.frame_witness(source_scene, source_pairs, runtime, {}))
            if not same["exact"] or protected_props != witness.source_property_witness(source_scene):
                raise RuntimeError("Capture/clone/prepare changed source")
            expected = {name: scope["forearm_health"] for name, scope in protected_output["scope"].items() if "forearm_health" in scope}
            return scene, [(source.name, target) for source, target in objects.items()], reverse, expected, protected_output, protected_props

        def assert_source_unchanged(output, props):
            select_scene(source_scene)
            bpy.context.view_layer.update()
            same = witness.compare_witness(output, witness.frame_witness(source_scene, source_pairs, runtime, {}))
            raw_same = props == witness.source_property_witness(source_scene)
            if not same["exact"] or not raw_same:
                raise RuntimeError("Candidate evaluation changed source")
            return {**same, "raw_source_properties_exact": raw_same}

        with runtime.defer_runtime(bpy.context, flush_on_exit=False):
            evaluate(source_scene, initial_context[0])
            initial_output = witness.frame_witness(source_scene, source_pairs, runtime, {})
            initial_props = witness.source_property_witness(source_scene)
            golden = {}
            proof_frames = (initial_context[0],) if args.admission_only else ALL_FRAMES
            report["frames"] = list(proof_frames)
            for frame in proof_frames:
                evaluate(source_scene, frame)
                golden[frame] = witness.frame_witness(source_scene, source_pairs, runtime, {})
                if not args.admission_only and frame in (10, 20, 30):
                    print("GOLDEN", frame, "30", flush=True)
                if args.admission_only:
                    print("ADMISSION_SOURCE", frame, flush=True)
            report["golden_source_frames_before_any_clone"] = list(golden)
            scene, pairs, reverse, expected, protected_output, protected_props = create_disposable("differential")
            for frame in proof_frames:
                evaluate(scene, frame, bindings)
                current = witness.frame_witness(scene, pairs, runtime, reverse, expected_forearm=expected)
                same = witness.compare_witness(golden[frame], current)
                report["frame_checks"].append({"frame": frame, **same})
                if not args.admission_only and frame in (10, 20, 30):
                    print("CANDIDATE", frame, "30", flush=True)
                if args.admission_only:
                    print("ADMISSION_CANDIDATE", frame, flush=True)
                if frame == proof_frames[0]:
                    report["native_output_scope"] = current["scope"]
                    report["source_output_scope"] = golden[frame]["scope"]
                if not same["exact"]:
                    report["first_failed_frame_components"] = {"authoring": golden[frame]["components"], "frozen": current["components"]}
                    raise RuntimeError("Complete exact differential failed on frame " + str(frame))
            report["source_unchanged_by_candidate_frames"] = assert_source_unchanged(protected_output, protected_props)
            close_disposable()
            if args.admission_only:
                report["admission_current_frame_exact"] = len(report["frame_checks"]) == 1 and report["frame_checks"][0]["exact"]
                report["all_30_complete_outputs_exact"] = False
                report["timing_skipped"] = "Current saved-frame structural admission only; no 30-frame or ABBA performance proof"
                return
            report["all_30_complete_outputs_exact"] = True
            for index, route in enumerate(BLOCK_ORDER):
                if route == "frozen":
                    scene, pairs, reverse, expected, protected_output, protected_props = create_disposable("ABBA block " + str(index))
                    current_bindings = bindings
                else:
                    if session is not None:
                        raise RuntimeError("Authoring authority must not observe clone IDs")
                    scene, pairs, reverse, expected, current_bindings = source_scene, source_pairs, {}, None, None
                for frame in WARM_FRAMES:
                    evaluate(scene, frame, current_bindings)
                rows = []
                for frame in HOT_FRAMES:
                    timing = evaluate(scene, frame, current_bindings)
                    actual = witness.frame_witness(scene, pairs, runtime, reverse, expected_forearm=expected)
                    if not witness.compare_witness(golden[frame], actual)["exact"]:
                        raise RuntimeError("Measured block changed expected output")
                    rows.append({**timing, "complete_output_exact": True})
                block = {"block": index, "route": route, "warm_frames": list(WARM_FRAMES), "frames": rows,
                         "median_total_pipeline_ms": statistics.median(row["total_pipeline_ms"] for row in rows),
                         "median_corrective_ms": statistics.median(row["corrective_inclusive_ms"] for row in rows)}
                report["blocks"].append(block)
                if route == "frozen":
                    assert_source_unchanged(protected_output, protected_props)
                    close_disposable()
                print("BLOCK", index, route, round(block["median_total_pipeline_ms"], 3), flush=True)
            summary = {}
            for name in ("median_total_pipeline_ms", "median_corrective_ms"):
                a_rows = [block[name] for block in report["blocks"] if block["route"] == "authoring"]
                b_rows = [block[name] for block in report["blocks"] if block["route"] == "frozen"]
                a, b = statistics.median(a_rows), statistics.median(b_rows)
                summary[name] = {"authoring_blocks": a_rows, "frozen_blocks": b_rows, "authoring_median_ms": a,
                                 "frozen_median_ms": b, "observed_reduction_percent": (a - b) / a * 100 if a else None}
            report["timing_summary"] = summary
            report["background_direction_lower"] = summary["median_total_pipeline_ms"]["frozen_median_ms"] < summary["median_total_pipeline_ms"]["authoring_median_ms"]
    finally:
        errors = []
        try:
            close_disposable()
        except BaseException:
            errors.append(traceback.format_exc())
        if source_scene is not None and initial_context is not None:
            try:
                with runtime.defer_runtime(bpy.context, flush_on_exit=False):
                    select_scene(source_scene)
                    source_scene.frame_set(initial_context[0], subframe=initial_context[1])
                    bpy.context.view_layer.update()
                    for obj in source_scene.objects:
                        if obj.type == "MESH" and runtime.RECORD_KEY in obj:
                            runtime._calculate_object(obj, bpy.context.evaluated_depsgraph_get())
                    bpy.context.view_layer.update()
                    if initial_output is not None:
                        actual = witness.frame_witness(source_scene, source_pairs, runtime, {})
                        report["source_restored_exact"] = witness.compare_witness(initial_output, actual)["exact"] and initial_props == witness.source_property_witness(source_scene)
            except BaseException:
                errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        handlers_exact = handlers_before == witness.handler_snapshot()
        runtime_timer_gone = not bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle)
        issuance_empty = not len(core._ISSUED_TEMPLATES)
        report["cleanup"] = {"errors": errors, "runtime_guard_released": not runtime._BUSY,
                             "handlers_restored_exact": handlers_exact,
                             "known_forearm_lifecycle_timer_gone": runtime_timer_gone,
                             "issued_templates_empty": issuance_empty,
                             "all_disposable_ids_removed": all(row["all_owned_ids_removed"] and not row["errors"] for row in report["disposable_cleanups"])}
        report["input_after"], report["artist_after"] = witness.pin(input_path), witness.pin(artist_path)
        report["input_disk_unchanged"] = before_input == report["input_after"]
        report["artist_disk_unchanged"] = before_artist == report["artist_after"]
        report["staged_sources_unchanged"] = sources_before == witness.verify_package_manifest(package, manifest)
        if errors or not report["cleanup"]["runtime_guard_released"] or not report["cleanup"]["all_disposable_ids_removed"] or not handlers_exact or not runtime_timer_gone or not issuance_empty:
            raise RuntimeError("Owned cleanup did not complete")
        if initial_output is not None and report.get("source_restored_exact") is not True:
            raise RuntimeError("Private source did not restore exactly")
        if not report["input_disk_unchanged"] or not report["artist_disk_unchanged"]:
            raise RuntimeError("Protected input or artist disk changed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "source-manifest", "builder-module", "report"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--builder-function", default="build_isolated_scene")
    parser.add_argument("--admission-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite native evidence")
    report = {"schema": "x.private-frozen-playback-differential/4", "completed": False, "pid": os.getpid(),
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "model_and_reasoning_effort": "unrecorded",
              "no_artist_open_or_save": True, "no_scene_save": True, "no_deploy": True, "performance_acceptance": False,
              "limits": ["Background only; no viewport/GUI FPS conclusion.",
                         "Golden outputs and all A blocks run without cloned IDs; B blocks rebuild and warm private Scenes.",
                         "Prepare/hash/context switching excluded from hot timing; inclusive stages must not be added.",
                         "Thirty integer frames of one saved animation; editing/subframes/physics/all animations unverified.",
                         "Native equivalence/lower timing prerequisite to GUI acceptance, not artist adoption."]}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
