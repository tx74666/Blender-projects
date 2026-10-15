"""Private complete actor experiment for paired helper bones; not adoption.

Source .41 golden frames precede all clone IDs. Bone conversion deliberately
changes owned key mute/value, selected raw weights/groups and helper counts.
Numeric geometry/normal differences are measured, never rounded into PASS.
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
import native_bone_support as geometry
from private_playback_native_runner_v2 import field, select_scene, isolation, EXPECTED_INPUTS, ALL_FRAMES, HOT_FRAMES, WARM_FRAMES, BLOCK_ORDER


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index("--")]
    if not bpy.app.background or "--factory-startup" not in native:
        raise RuntimeError("Private factory-startup background process required")
    if not any(value in ("-t", "--threads") and native[i + 1] == "1" for i, value in enumerate(native[:-1])):
        raise RuntimeError("Explicit native -t 1 required")
    source_file, artist_file = Path(args.input).resolve(), Path(args.artist).resolve()
    if source_file == artist_file or os.path.samefile(source_file, artist_file):
        raise RuntimeError("Never open artist or a hard link to it")
    input_before, artist_before = witness.pin(source_file), witness.pin(artist_file)
    if EXPECTED_INPUTS.get(input_before["sha256"]) != input_before["bytes"]:
        raise RuntimeError("Unaccepted saved-copy input")
    package = Path(args.addons).resolve() / "character_designer"
    manifest_path = Path(args.source_manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema") != "x.frozen-playback-source-seal/1":
        raise RuntimeError("Unexpected source seal")
    sources_before = witness.verify_package_manifest(package, manifest)
    report.update(input_before=input_before, artist_before=artist_before, sources=sources_before,
                  source_manifest=witness.pin(manifest_path), script=witness.pin(__file__),
                  bone_witness_script=witness.pin(geometry.__file__), witness_script=witness.pin(witness.__file__),
                  frozen_runner_dependency=witness.pin(HERE / "private_playback_native_runner_v2.py"),
                  blender=bpy.app.version_string, thread_request=1, frames=list(ALL_FRAMES), hot_frames=list(HOT_FRAMES),
                  model="gpt-6.1-sol", reasoning_effort="ultra",
                  model_and_reasoning_effort="gpt-6.1-sol / ultra",
                  model_source="Current root task local index verified by root; inherited task settings.",
                  preparations=[], frame_checks=[], blocks=[], disposable_cleanups=[])
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module("character_designer")
    runtime = importlib.import_module("character_designer.forearm_twist")
    core = importlib.import_module("character_designer.forearm_twist_playback_core")
    bone = importlib.import_module("character_designer.forearm_twist_bone_preview")
    builder = importlib.import_module("character_designer.forearm_twist_playback_scene").build_isolated_scene
    if Path(addon.__file__).resolve().parent != package:
        raise RuntimeError("Native process imported a different package")
    report["version"] = list(addon.bl_info["version"])
    registered, source_scene, initial_context, initial_output, initial_props = False, None, None, None, None
    session, templates, plans, previews, private_ids = None, [], [], {}, set()
    handlers_before = witness.handler_snapshot()

    def close_disposable():
        nonlocal session, templates, plans, previews, private_ids
        if session is None and not templates and not plans:
            return
        errors = []
        for info in previews.values():
            try:
                info["preview"].close()
            except BaseException:
                errors.append(traceback.format_exc())
        for template in templates:
            try:
                core.discard_template(template)
            except BaseException:
                errors.append(traceback.format_exc())
        for plan in plans:
            try:
                bone.discard_plan(plan)
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
        session, templates, plans, previews, private_ids = None, [], [], {}, set()
        if errors or remaining:
            raise RuntimeError("Bone disposable cleanup failed")

    try:
        addon.register()
        registered = True
        opened = bpy.ops.wm.open_mainfile(filepath=str(source_file))
        if "FINISHED" not in opened or Path(bpy.data.filepath).resolve() != source_file:
            raise RuntimeError("Private saved-copy open failed")
        source_scene = bpy.context.scene
        report["observed_scene_units"] = {"system": source_scene.unit_settings.system,
            "scale_length": float(source_scene.unit_settings.scale_length), "length_unit": source_scene.unit_settings.length_unit,
            "coordinate_error_units": "object-local native model units; not automatically millimeters"}
        source_pairs = [(obj.name, obj) for obj in source_scene.objects]
        initial_context = (source_scene.frame_current, source_scene.frame_subframe)
        bpy.context.view_layer.update()
        if runtime._ERRORS:
            raise RuntimeError("Input Forearm errors: " + repr(runtime._ERRORS))
        converted_source = {obj.name: {"managed_names": tuple(record["key"] for record in runtime._records(obj).values())}
                            for obj in source_scene.objects if obj.type == "MESH" and runtime.RECORD_KEY in obj}
        rig_names = {obj.name: tuple(bone.name for bone in obj.data.bones) for obj in source_scene.objects if obj.type == "ARMATURE"}
        if not converted_source:
            raise RuntimeError("No authoritative calibrated source owner")

        def evaluate(scene, frame, current_previews=None):
            select_scene(scene)
            began = time.perf_counter_ns()
            scene.frame_set(frame)
            a = time.perf_counter_ns()
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            b = time.perf_counter_ns()
            angles = {}
            if current_previews is None:
                for obj in scene.objects:
                    if obj.type == "MESH" and runtime.RECORD_KEY in obj:
                        runtime._calculate_object(obj, graph)
            else:
                for name, info in current_previews.items():
                    preview, inverses = info["preview"], info["rest_inverses"]
                    evaluated_rig = preview.rig.evaluated_get(graph)
                    transforms = {name: evaluated_rig.pose.bones[name].matrix @ inverse for name, inverse in inverses.items()}
                    try:
                        angles[name] = preview.update_from_deformations(transforms)
                    except BaseException:
                        report["helper_update_failure"] = {"frame": frame, "owner": name,
                            "last_basis_report": preview.last_basis_report,
                            "last_verification": preview.last_verification, "last_error": preview.last_error}
                        raise
            c = time.perf_counter_ns()
            bpy.context.view_layer.update()
            d = time.perf_counter_ns()
            matrix_verification = {}
            if current_previews is not None:
                for name, info in current_previews.items():
                    preview = info["preview"]
                    try:
                        result = preview.verify_evaluated(bpy.context.evaluated_depsgraph_get())
                        if result.get("completed") is not True or result.get("within_tolerance") is not True:
                            raise RuntimeError("Helper deformation matrix oracle did not pass")
                        matrix_verification[name] = result
                        matrix_verification[name]["basis_readback"] = preview.last_basis_report
                    except BaseException:
                        report["matrix_verification_failure"] = {
                            "frame": frame, "owner": name,
                            "last_verification": preview.last_verification,
                        }
                        raise
            if runtime._ERRORS:
                raise RuntimeError("Authoring errors during pipeline: " + repr(runtime._ERRORS))
            return {"frame": frame, "frame_advance_ms": (a - began) / 1e6, "first_native_update_ms": (b - a) / 1e6,
                    "corrective_or_helper_update_ms": (c - b) / 1e6, "final_native_update_ms": (d - c) / 1e6,
                    "total_pipeline_ms": (d - began) / 1e6, "side_angles_radians": angles,
                    "matrix_verification": matrix_verification}

        def create_disposable(phase):
            nonlocal session, templates, plans, previews, private_ids
            if session is not None:
                raise RuntimeError("Previous bone scene not closed")
            select_scene(source_scene)
            bpy.context.view_layer.update()
            protected_output = witness.frame_witness(source_scene, source_pairs, runtime, {})
            protected_props = witness.source_property_witness(source_scene)
            old_ids = witness.native_id_pointers()
            began = time.perf_counter_ns()
            source_plans = {}
            for obj in source_scene.objects:
                if obj.type == "MESH" and runtime.RECORD_KEY in obj:
                    template = core.capture(obj, bpy.context.evaluated_depsgraph_get())
                    templates.append(template)
                    plan = bone.plan_from_template(template)
                    plans.append(plan)
                    source_plans[obj] = plan
            a = time.perf_counter_ns()
            try:
                session = builder(source_scene)
            finally:
                private_ids = witness.native_id_pointers() - old_ids
            b = time.perf_counter_ns()
            scene, objects, eligible, reverse = isolation(session, source_scene, runtime)
            select_scene(scene)
            bpy.context.view_layer.update()
            converted = {}
            build_evidence = {}
            for source, target in eligible.items():
                source_rig = runtime._check_mesh(source)
                target_rig = objects[source_rig]
                plan = source_plans[source]
                preview = bone.build_isolated_preview(target, target_rig, plan,
                    template=next(item for item in templates if item.source_ids == plan.source_ids),
                    isolated_scene=scene, source_mesh=source, source_rig=source_rig, disposable=True)
                names = {name for side in plan.sides for name in (side.lower, side.hand)}
                inverses = {name: target_rig.data.bones[name].matrix_local.inverted() for name in names}
                previews[source.name] = {"preview": preview, "rest_inverses": inverses}
                converted[source.name] = {"managed_names": plan.managed_key_names,
                                         "mask_copies": dict(preview.mask_copies), "bone_route": True}
                build_evidence[source.name] = {
                    "helper_names": list(preview.helper_names.values()), "helper_count": len(preview.helper_names),
                    "managed_keys": list(plan.managed_key_names), "mask_copies": dict(preview.mask_copies),
                    "approved_weights": geometry.weight_rewrite_witness(source, target, target_rig, plan, preview),
                    "dormant_managed_coordinates": geometry.dormant_managed_keys(target, plan.managed_key_names),
                }
            c = time.perf_counter_ns()
            report["preparations"].append({"phase": phase, "source_canonical_capture_and_plan_ms": (a - began) / 1e6,
                "actor_clone_ms": (b - a) / 1e6, "bone_build_ms": (c - b) / 1e6, "total_ms": (c - began) / 1e6,
                "build_evidence": build_evidence, "core_solver_evaluations": 0})
            select_scene(source_scene)
            bpy.context.view_layer.update()
            if not witness.compare_witness(protected_output, witness.frame_witness(source_scene, source_pairs, runtime, {}))["exact"] or protected_props != witness.source_property_witness(source_scene):
                raise RuntimeError("Bone prepare changed source")
            return scene, [(source.name, target) for source, target in objects.items()], reverse, converted, build_evidence, protected_output, protected_props

        def protect_source(output, props):
            select_scene(source_scene)
            bpy.context.view_layer.update()
            same = witness.compare_witness(output, witness.frame_witness(source_scene, source_pairs, runtime, {}))
            if not same["exact"] or props != witness.source_property_witness(source_scene):
                raise RuntimeError("Bone candidate evaluation changed source")
            return {**same, "raw_source_properties_exact": True}

        def check_dormant(current, build):
            for name, info in build.items():
                if current["scope"][name]["dormant_managed_coordinates"] != info["dormant_managed_coordinates"]:
                    raise RuntimeError("Bone playback rewrote dormant managed coordinates")

        with runtime.defer_runtime(bpy.context, flush_on_exit=False):
            evaluate(source_scene, initial_context[0])
            initial_output = witness.frame_witness(source_scene, source_pairs, runtime, {})
            initial_props = witness.source_property_witness(source_scene)
            golden, vectors = {}, {}
            for frame in ALL_FRAMES:
                evaluate(source_scene, frame)
                golden[frame], raw = geometry.bone_frame_witness(source_scene, source_pairs, runtime, {}, converted_source, rig_names)
                vectors[frame] = {name: geometry.compressed_vectors(fields) for name, fields in raw.items()}
            report["golden_source_frames_before_any_clone"] = list(golden)
            report["golden_in_memory_compressed_bytes"] = sum(len(item["compressed"]) for frame in vectors.values() for mesh in frame.values() for item in mesh.values())
            scene, pairs, reverse, converted, build, protected_output, protected_props = create_disposable("differential")
            candidate_outputs = {}
            strict = True
            for frame in ALL_FRAMES:
                timing = evaluate(scene, frame, previews)
                current, raw = geometry.bone_frame_witness(scene, pairs, runtime, reverse, converted, rig_names)
                check_dormant(current, build)
                same = geometry.compare_frames(golden[frame], vectors[frame], current, raw, converted_names=converted)
                report["frame_checks"].append({"frame": frame, "side_angles_radians": timing["side_angles_radians"],
                                               "matrix_verification": timing["matrix_verification"], **same})
                candidate_outputs[frame] = {"strict_sha256": current["sha256"],
                    "vectors": {name: {field: witness.object_hash(item) for field, item in mesh.items()}
                                for name, mesh in same["meshes"].items()}}
                strict &= same["strict_nonvector_outputs_exact"]
                if frame == 1:
                    report["native_output_scope"] = current["scope"]
            report["source_unchanged_by_bone_frames"] = protect_source(protected_output, protected_props)
            close_disposable()
            report["all_30_strict_nonvector_outputs_exact"] = bool(strict)
            report["all_30_coordinates_and_normals_exact"] = all(row["all_coordinates_and_normals_exact"] for row in report["frame_checks"])
            if not strict:
                report["timing_skipped"] = "Nonhelper pose/Rest, foreign keys, topology/UV/material or unconverted geometry differed"
                report["candidate_eligible"] = False
            else:
                for index, route in enumerate(BLOCK_ORDER):
                    if route == "frozen":  # Preserve common ABBA order; this branch is paired bones.
                        scene, pairs, reverse, converted, build, protected_output, protected_props = create_disposable("ABBA block " + str(index))
                        current_previews = previews
                    else:
                        if session is not None:
                            raise RuntimeError("Authoring A must not observe clone IDs")
                        scene, pairs, reverse, converted, current_previews = source_scene, source_pairs, {}, converted_source, None
                    for frame in WARM_FRAMES:
                        evaluate(scene, frame, current_previews)
                    rows = []
                    for frame in HOT_FRAMES:
                        measured = evaluate(scene, frame, current_previews)
                        current, raw = geometry.bone_frame_witness(scene, pairs, runtime, reverse, converted, rig_names)
                        same = geometry.compare_frames(golden[frame], vectors[frame], current, raw, converted_names=converted_source)
                        if not same["strict_nonvector_outputs_exact"]:
                            raise RuntimeError("Measured block changed strict expected channels")
                        if route == "authoring" and not same["all_coordinates_and_normals_exact"]:
                            raise RuntimeError("Authoring A no longer reproduces golden geometry")
                        if route == "frozen":
                            check_dormant(current, build)
                            actual = {"strict_sha256": current["sha256"],
                                "vectors": {name: {field: witness.object_hash(item) for field, item in mesh.items()}
                                            for name, mesh in same["meshes"].items()}}
                            if actual != candidate_outputs[frame]:
                                raise RuntimeError("Bone block did not reproduce candidate's numeric differences")
                        rows.append({**measured, "strict_channels_exact": True,
                                     "coordinates_and_normals_exact": same["all_coordinates_and_normals_exact"]})
                    block = {"block": index, "route": "paired_bones" if route == "frozen" else "authoring",
                             "warm_frames": list(WARM_FRAMES), "frames": rows,
                             "median_total_pipeline_ms": statistics.median(row["total_pipeline_ms"] for row in rows),
                             "median_corrective_or_helper_ms": statistics.median(row["corrective_or_helper_update_ms"] for row in rows)}
                    report["blocks"].append(block)
                    if route == "frozen":
                        protect_source(protected_output, protected_props)
                        close_disposable()
                    print("BLOCK", index, block["route"], round(block["median_total_pipeline_ms"], 3), flush=True)
                summary = {}
                for name in ("median_total_pipeline_ms", "median_corrective_or_helper_ms"):
                    a_rows = [block[name] for block in report["blocks"] if block["route"] == "authoring"]
                    b_rows = [block[name] for block in report["blocks"] if block["route"] == "paired_bones"]
                    a, b = statistics.median(a_rows), statistics.median(b_rows)
                    summary[name] = {"authoring_blocks": a_rows, "paired_bone_blocks": b_rows,
                                     "authoring_median_ms": a, "paired_bone_median_ms": b,
                                     "observed_reduction_percent": (a - b) / a * 100 if a else None}
                report["timing_summary"] = summary
                report["candidate_eligible"] = False
                report["numeric_error_acceptance_pending"] = True
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
                        report["source_restored_exact"] = witness.compare_witness(initial_output, witness.frame_witness(source_scene, source_pairs, runtime, {}))["exact"] and initial_props == witness.source_property_witness(source_scene)
            except BaseException:
                errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        checks = {"runtime_guard_released": not runtime._BUSY,
                  "handlers_restored_exact": handlers_before == witness.handler_snapshot(),
                  "known_forearm_lifecycle_timer_gone": not bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle),
                  "issued_templates_empty": not len(core._ISSUED_TEMPLATES), "issued_plans_empty": not len(bone._ISSUED_PLANS),
                  "all_disposable_ids_removed": all(row["all_owned_ids_removed"] and not row["errors"] for row in report["disposable_cleanups"])}
        report["cleanup"] = {"errors": errors, **checks}
        report["input_after"], report["artist_after"] = witness.pin(source_file), witness.pin(artist_file)
        report["input_disk_unchanged"] = input_before == report["input_after"]
        report["artist_disk_unchanged"] = artist_before == report["artist_after"]
        report["staged_sources_unchanged"] = sources_before == witness.verify_package_manifest(package, manifest)
        if errors or not all(checks.values()):
            raise RuntimeError("Owned bone native cleanup did not complete")
        if initial_output is not None and report.get("source_restored_exact") is not True:
            raise RuntimeError("Private authoring source did not restore exactly")
        if not report["input_disk_unchanged"] or not report["artist_disk_unchanged"]:
            raise RuntimeError("Protected input or artist disk changed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite evidence")
    report = {"schema": "x.private-paired-bone-preview/1", "completed": False, "pid": os.getpid(),
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "model_and_reasoning_effort": "unrecorded",
              "no_artist_open_or_save": True, "no_scene_save": True, "no_deploy": True, "performance_acceptance": False,
              "synthetic_swing_twist": "Separate fixture run required; this run covers the saved clip only",
              "limits": ["Background native only; no GUI FPS, authoring migration or artist adoption.",
                         "Bone groups/key mute/helper counts deliberately change; original bones/channels and all foreign fields must remain exact.",
                         "Full evaluated float32 coordinates and normals report bit exactness plus max/RMS errors without a tolerance waiver.",
                         "Golden raw arrays are compressed only in worker memory; reports contain hashes/counts/metrics only.",
                         "Each helper basis/evaluated-deformation oracle must pass before geometry evidence; oracle work is outside timed pipeline.",
                         "Source golden/A blocks have no clone IDs; B blocks rebuild/warm; prepare/hash/context switching excluded.",
                         "Thirty integer saved-clip frames do not verify other animation, physics, editing, swing extrema or export.",
                         "Numeric error acceptance and actual GUI verification remain pending even if strict fields/timing pass."]}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
