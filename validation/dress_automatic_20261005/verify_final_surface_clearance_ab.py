"""Isolated native interface/safety gate first, optional actual same-frame A/B.

PREPARED ONLY. Root must lease one Blender 5.1 --background --factory-startup
--disable-autoexec --threads 1 process. Default --mode interface never authors
Pose input; it tests installation, actual evaluated diagnostics and exact removal
at the privately reset start frame. --mode ab adds the frozen same-frame inputs.
No artist save/deployment/export/Unity/second process. A successful collection
does NOT mean prototype clearance, whole-Body collision or actual art accepted.
"""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import time
import traceback
from types import SimpleNamespace

import bpy
from mathutils import Quaternion

HERE = Path(__file__).resolve().parent
PINS = {
    "prototype_final_surface_clearance.py": "6280862bd2b7602dd1252a2c959202f394c9ce9498d41c2b9f47e4dc83e2767b",
    "verify_actual_same_frame_pose.py": "812841f31309bea8ee923dd8299c0240ec1576d2ed4842ba46793c854d1830ff",
    "verify_actual_surface_workflow.py": "2e8d82bbbde00604bf3f62bc17cbcb31244ed87290e083ebb17b25f4b9216140",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-surface-sha", required=True)
    parser.add_argument("--expected-worker-sha", required=True)
    parser.add_argument("--mode", choices=("interface", "ab"), default="interface")
    parser.add_argument("--output-mode", choices=("AUTOMATIC", "MANUAL"), default="AUTOMATIC")
    parser.add_argument("--margin-m", type=float, default=.002)
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--triangle-pair-limit", type=int, default=10000)
    parser.add_argument("--body-vertex-limit", type=int, default=100000)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.output = args.output.resolve()
    require(args.output.is_relative_to(HERE) and args.output != HERE and not args.output.exists(),
            "Use a fresh dedicated child of this Validation directory; existing evidence is not overwritten")
    require(1 <= args.passes <= 8 and 1 <= args.repeats <= 9 and math.isfinite(args.margin_m) and args.margin_m > 0.,
            "Invalid explicit projection/repeat bounds")
    require(1000 <= args.triangle_pair_limit <= 100000 and 1000 <= args.body_vertex_limit <= 100000,
            "Invalid bounded native collision budgets")
    return args


def load(name):
    path = HERE / name
    require(path.is_file() and sha(path) == PINS[name], "Pinned private dependency changed: " + name)
    spec = importlib.util.spec_from_file_location("final_clearance_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PHASE_CLOCK = time.perf_counter()


def phase(name):
    print(json.dumps({"qa_phase": name, "elapsed_from_module_load_seconds":
                      time.perf_counter() - PHASE_CLOCK}), flush=True)


def check(report, name, passed, **facts):
    report["checks"].append({"name": name, "passed": bool(passed), **facts})
    phase("check_" + name + ("_passed" if passed else "_failed"))


def fields(source, handle, qa, record, projected):
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = source.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    try:
        require(len(mesh.vertices) == 3040, "The actual final GN output is not the exact evaluated3040 layout")
        waist = source.vertex_groups[record["controls"]["waist"]].index
        complete_weights = all(vertex.groups for vertex in mesh.vertices)
        waist_weights = [next((assignment.weight for assignment in vertex.groups if assignment.group == waist), 0.)
                         for vertex in mesh.vertices]
        free = [index for index, weight in enumerate(waist_weights) if weight < .999]
        fixed = [index for index, weight in enumerate(waist_weights) if weight >= .999]
        require(complete_weights and free and fixed, "Final native weight/free/fixed coverage is unavailable; absence is not a Pass")
        mesh.calc_loop_triangles()
        topology = {"edges": [list(edge.vertices) for edge in mesh.edges],
                    "faces": [list(face.vertices) for face in mesh.polygons],
                    "triangles": [list(triangle.vertices) for triangle in mesh.loop_triangles]}
        measured = []
        for spec in handle["report"]["diagnostic_attributes"] if projected else ():
            attribute = mesh.attributes.get(spec["name"])
            require(attribute is not None and attribute.domain == "POINT" and attribute.data_type == spec["type"]
                    and len(attribute.data) == 3040, "Native diagnostic field is missing or changed: " + spec["name"])
            values = [item.value for item in attribute.data]
            if spec["type"] == "FLOAT":
                require(all(math.isfinite(value) and value >= 0. for value in values), "Nonfinite or negative native residual field")
                item = {"maximum_free_m": max(values[index] for index in free),
                        "free_vertices_above_1um": sum(values[index] > 1.e-6 for index in free)}
            else:
                item = {"unproven_free_vertices": sum(bool(values[index]) for index in free),
                        "unproven_all_vertices": sum(bool(value) for value in values)}
            measured.append({**spec, **item, "values_by_exact_final_vertex_index": values})
        return {"status": "measured", "diagnostic_fields_status": "collected" if projected else "not_applicable_modifier_disabled",
                "final_vertices": 3040, "final_free_vertices": len(free),
                "weight_layer_complete": complete_weights, "free_vertex_indices": free, "hard_fixed_vertex_indices": fixed,
                "waist_weights_by_exact_final_vertex_index": waist_weights, "attributes": measured,
                "native_topology": topology, "native_topology_sha256": qa.digest(topology),
                "native_world_points": [list(evaluated.matrix_world @ vertex.co) for vertex in mesh.vertices],
                "plane_fields_small_and_lookup_valid": bool(projected) and all(
                    item.get("maximum_free_m", 0.) <= 1.e-6 and item.get("unproven_all_vertices", 0) == 0 for item in measured),
                "separation_accepted": False,
                "limitation": "GN scalar plane fields only. Independent signed closed-mesh and final-triangle/Body diagnostics are required."}
    finally:
        evaluated.to_mesh_clear()


def render(label, source, rig, body, record, frame, args, diag):
    graph = bpy.context.evaluated_depsgraph_get()
    directory = args.output / "render" / label
    directory.mkdir(parents=True)
    return diag.native_render(SimpleNamespace(frame=frame, output=directory),
        diag.mesh_snapshot(source, graph), diag.mesh_snapshot(body, graph), diag.framing(rig, record, graph))


def collect(label, projected, handle, common, record, args, same, qa, diag, workflow, prototype,
            meters, collision_baseline, initial_contacts, report):
    phase("collect_begin_" + label)
    source, rig, actual, neutral, body, legs, cloth, scene, frame = common
    modifier = handle["modifier"]
    modifier.show_viewport = modifier.show_render = projected
    source.update_tag(refresh={"OBJECT"})
    clock = time.perf_counter()
    cold = same.capture(*common, qa, meters)
    operation = {"label": label, "projected": projected,
                 "cold_update_and_Body_C_H0_O_reads_seconds": cold["native_read_seconds"],
                 "cold_including_geometry_summaries_seconds": time.perf_counter() - clock,
                 "cold": cold["public"], "repeat_timings_seconds": [],
                 "repeat_native_timing_segments": [], "whole_body_clearance_accepted": False}
    report["operations"].append(operation)
    references = cold
    maximum = {name: 0. for name in cold["points"]}
    repeated_cache_equal = True
    for _index in range(args.repeats):
        repeat = same.capture(*common, qa, meters)
        operation["repeat_timings_seconds"].append(repeat["native_read_seconds"])
        operation["repeat_native_timing_segments"].append(repeat["public"]["native_timing_segments"])
        difference = same.differences(references, repeat, qa, meters, qa.geometry_guard(meters))
        for name, entry in difference["surfaces"].items():
            maximum[name] = max(maximum[name], entry["maximum_delta_m"])
        repeated_cache_equal = repeated_cache_equal and difference["cache_metadata_equal"]
    operation["unchanged_repeat_surface_maximum_delta_m"] = maximum
    operation["unchanged_repeat_cache_metadata_equal"] = repeated_cache_equal
    operation["same_frame_repeat_is_stable"] = repeated_cache_equal and all(
        value <= qa.geometry_guard(meters) for value in maximum.values())
    operation["unchanged_repeat_median_seconds"] = statistics.median(operation["repeat_timings_seconds"])
    operation["unchanged_repeat_worst_seconds"] = max(operation["repeat_timings_seconds"])
    operation["timing_scope"] = "First after changed native flags/input, not OS/cache coldness. Native update/depsgraph + Body/C/H0/O extraction; explicit summaries, BVH collision/proof/render and evidence writes timed separately. Not UI/FPS."
    if projected:
        phase("current_pose_collider_proof_begin_" + label)
        clock = time.perf_counter()
        operation["prototype_current_pose_proof"] = prototype.validate_preview(handle)
        operation["prototype_current_pose_proof_seconds"] = time.perf_counter() - clock
        phase("current_pose_collider_proof_end_" + label)
    field_data = fields(source, handle, qa, record, projected)
    field_points = field_data.pop("native_world_points")
    field_drift = max((math.sqrt(sum((point[axis] - cold["points"]["O3040"][index][axis]) ** 2 for axis in range(3)))
                       * meters for index, point in enumerate(field_points)), default=0.)
    require(field_drift <= qa.geometry_guard(meters), "Per-vertex field readback differs from the recorded actual final O3040")
    operation["final_fields_readback_maximum_drift_m"] = field_drift
    cold["native_final"] = {"topology_sha256": field_data["native_topology_sha256"],
        "waist_weights": field_data["waist_weights_by_exact_final_vertex_index"],
        "fixed_indices": field_data["hard_fixed_vertex_indices"]}
    points_dir = args.output / "actual_points"
    points_dir.mkdir(exist_ok=True)
    points_path = points_dir / (label + ".json")
    clock = time.perf_counter()
    points_path.write_text(json.dumps({"label": label, "frame": frame, "units_to_metres": meters,
        "coordinates": "Actual evaluated world units, in unchanged exact native vertex order; multiply by units_to_metres for metres",
        "points": {name: [list(point) for point in points] for name, points in cold["points"].items()},
        "knees": {side: list(point) for side, point in cold["knees"].items()}, "hem": list(cold["hem"]),
        "final_per_vertex_diagnostic_fields": field_data}, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    operation["native_points_and_fields"] = {"path": str(points_path), "sha256": sha(points_path),
                                            "write_seconds": time.perf_counter() - clock}
    operation["diagnostic_fields"] = {**{key: value for key, value in field_data.items()
            if key not in {"attributes", "free_vertex_indices", "hard_fixed_vertex_indices",
                           "waist_weights_by_exact_final_vertex_index", "native_topology"}}, "attributes": [
                {key: value for key, value in entry.items() if key != "values_by_exact_final_vertex_index"}
                for entry in field_data["attributes"]]}
    phase("native_points_and_fields_written_" + label)
    if args.mode == "ab":
        phase("whole_body_diagnostic_begin_" + label)
        operation["collision"], _render_data = same.checked_collision(
            "initial_pose" if label == "initial_baseline" else label,
            source, rig, actual, body, cloth, record, frame, args, qa, diag, workflow, meters,
            collision_baseline, initial_contacts)
        phase("whole_body_diagnostic_end_" + label)
    else:
        operation["collision"] = {
            "status": "not_requested_structural_interface",
            "whole_surface_separation_accepted": False,
            "reason": "Interface mode checks construction, fields, protection and removal only. Actual pose/manual A/B must independently check final Body triangles."}
    if args.render:
        clock = time.perf_counter()
        operation["render"] = render(label, source, rig, body, record, frame, args, diag)
        operation["render_seconds"] = time.perf_counter() - clock
    check(report, "same_frame_repeat_stable_" + label, operation["same_frame_repeat_is_stable"],
          maximum_delta_m=maximum, cache_metadata_equal=repeated_cache_equal)
    return cold


def comparison(case, baseline, projected, same, qa, meters):
    first, second = baseline["native_final"], projected["native_final"]
    same_fixed = first["fixed_indices"] == second["fixed_indices"]
    fixed_delta = max(((projected["points"]["O3040"][index] - baseline["points"]["O3040"][index]).length * meters
                       for index in first["fixed_indices"]), default=0.)
    return {"case": case, "A_B": same.differences(baseline, projected, qa, meters, qa.geometry_guard(meters)),
        "native_final_topology_equal": first["topology_sha256"] == second["topology_sha256"],
        "native_final_waist_weights_equal": first["waist_weights"] == second["waist_weights"],
        "native_fixed_mask_equal": same_fixed, "hard_fixed_vertices": len(first["fixed_indices"]),
        "hard_fixed_waist_maximum_projection_delta_m": fixed_delta}


def main(args):
    require(bpy.app.background and bpy.app.version[:2] == (5, 1) and not bpy.data.filepath
            and "--factory-startup" in sys.argv and "--disable-autoexec" in sys.argv,
            "Use an empty root-leased Blender 5.1 factory background child, never the artist UI")
    require("--threads" in sys.argv and sys.argv[sys.argv.index("--threads") + 1] == "1", "Root must use --threads 1")
    same, workflow, prototype = (load(name) for name in
        ("verify_actual_same_frame_pose.py", "verify_actual_surface_workflow.py", "prototype_final_surface_clearance.py"))
    args.input, args.install_report = same.INPUT.resolve(), same.INSTALL.resolve()
    require(sha(args.input) == same.INPUT_SHA, "The exact installed Cosha QA bytes changed")
    require(not args.input.is_relative_to(args.output), "Output overlaps the exact installed input")
    qa, diag, addon, surface = workflow.load_dependencies()
    artist = Path(json.loads(args.install_report.read_text(encoding="utf-8"))["artist_path"]).resolve()
    report = {"success": False, "mechanism_success": False, "mode": args.mode, "output_mode": args.output_mode,
        "success_scope": "Native construction, fields, data protection and complete removal/reload only" if args.mode == "interface"
            else "Native actual pose/manual A/B mechanics and diagnostic collection only; effect acceptance is separate",
        "independent_collision_samples_collected": False, "initial_contact_pair_classification_collected": False,
        "operations": [], "checks": [],
        "prototype_effect_accepted": False, "production_effect_accepted": False, "artist_saved": False,
        "dependencies": PINS, "script_sha256": sha(Path(__file__)), "input_before": qa.file_state(args.input),
        "artist_before": qa.file_state(artist), "canonical_before": diag.source_manifest(),
        "limits": ["Only private installed Cosha start frame, zero animation keys authored",
                   "Interface/collection success is not union point separation, Body/final-triangle clearance or contour acceptance",
                   "Open Body, old baseline contacts, unresolved/budgeted pairs remain Unknown, not Pass",
                   "Canonical validation only before GN install and after exact remove",
                   "Private prototype must be removed before export/artist save; no export acceptance",
                   "Repeated cached extraction cost is not changing-pose simulation cost or GUI FPS"]}
    args.output.mkdir(parents=True)
    destination = args.output / "final_clearance_ab.json"
    handle = protection = None
    source = rig = None
    began = time.perf_counter()
    try:
        source_name = workflow.motion_input_gate(args, report, qa, diag)
        addon.register()
        result = bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
        require("FINISHED" in result, "Exact installed QA did not open")
        phase("installed_input_opened")
        source, rig, _record = qa.owned_source(source_name)
        protection = qa.Protection()
        record, rig, actual, cloth, neutral = workflow.motion_objects(source, qa, surface)
        scene = bpy.context.scene
        require(scene.name == record["physics"]["surface"]["home_scene"], "Exact installation Scene differs")
        require(qa.saved_cache_preflight(source, record)["allowed"], "Installed input has an unknown cache")
        candidate = args.output / "scenes/Cosha_Dress_QA_clearance_interface.blend"
        qa.save_candidate(candidate, args.input)
        phase("private_candidate_saved")
        scene.tool_settings.use_keyframe_insert_auto = False
        qa.backup_animation(scene, list(bpy.data.objects) + list(bpy.data.shape_keys), protection.action_refs)
        qa.skirt._activate(bpy.context, rig, "POSE")
        qa.public_switch(bpy.ops.character_designer.body_ik_fk_switch, mode="FK")
        legs, axes, height = qa.body_inputs(rig, record)
        body, report["registered_body"] = qa.registered_body(bpy.context, rig, args)
        require(body is not None and report["registered_body"]["measured"]
                and body == bpy.data.objects.get(record["physics"]["surface"]["body"]), "Exact registered Body was not proved")
        qa.tuning.apply(bpy.context, (source,), mode=args.output_mode)
        bpy.context.window_manager.character_designer_skirt.source = source
        cache_dir = args.output / "native_cache"
        cache_dir.mkdir()
        cloth.point_cache.filepath, cloth.point_cache.use_library_path, cloth.point_cache.use_disk_cache = str(cache_dir), False, False
        require(not cloth.point_cache.use_external, "External cache is refused")
        qa.public_switch(bpy.ops.character_designer.dress_motion_reset)
        phase("private_motion_reset_returned")
        frame = int(cloth.point_cache.frame_start)
        require(scene.frame_current == frame and not cloth.point_cache.is_baked, "Private Reset did not reach the unbaked start frame")
        meters = float(scene.unit_settings.scale_length)
        require(math.isfinite(meters) and meters > 0., "Invalid native physical metre scale")
        common = (source, rig, actual, neutral, body, legs, cloth, scene, frame)
        before = same.capture(*common, qa, meters)
        original_nodes = workflow.inventory()
        check(report, "canonical_preflight_before_prototype", bool(surface.validate(source, rig, qa.skirt.read_record(source))))
        clock = time.perf_counter()
        phase("prototype_install_begin")
        handle = prototype.install_preview(source, rig, qa.skirt.read_record(source), args.margin_m, args.passes)
        phase("prototype_install_end")
        report["native_install_seconds"] = time.perf_counter() - clock
        report["prototype_spec"] = handle["report"]
        check(report, "native_node_construction_FINISHED", True, node_sha256=handle["fingerprint"])
        baseline_contacts = {}
        initial_contacts = {}  # Only the first disabled baseline seals initial triangle pairs.
        baseline = collect("initial_baseline", False, handle, common, record, args, same, qa, diag, workflow,
                           prototype, meters, baseline_contacts, initial_contacts, report)
        install_difference = same.differences(before, baseline, qa, meters, qa.geometry_guard(meters))
        check(report, "disabled_install_preserves_original_native_outputs", all(
            entry["maximum_delta_m"] <= qa.geometry_guard(meters) for entry in install_difference["surfaces"].values()),
            measured=install_difference)
        projected = collect("initial_projected", True, handle, common, record, args, same, qa, diag, workflow,
                            prototype, meters, baseline_contacts, initial_contacts, report)
        pairs = [comparison("initial", baseline, projected, same, qa, meters)]
        if args.mode == "ab":
            thigh_name = legs["L"]["chain"][0]
            thigh = rig.pose.bones[thigh_name]
            require(not any(thigh.lock_rotation) and not (thigh.lock_rotations_4d and thigh.lock_rotation_w),
                    "Real FK thigh lock cannot be bypassed")
            thigh_base = thigh.matrix_basis.to_quaternion().copy()
            thigh.rotation_mode = "QUATERNION"
            thigh.rotation_quaternion = thigh_base @ Quaternion(axes[thigh_name], .55)
            rig.update_tag(refresh={"OBJECT"})
            leg = collect("leg_baseline", False, handle, common, record, args, same, qa, diag, workflow,
                          prototype, meters, baseline_contacts, initial_contacts, report)
            leg_projected = collect("leg_projected", True, handle, common, record, args, same, qa, diag, workflow,
                                    prototype, meters, baseline_contacts, initial_contacts, report)
            response = same.differences(baseline, leg, qa, meters, qa.geometry_guard(meters))
            check(report, "same_frame_real_leg_reaches_knee_and_Body", response["knee_delta_m"]["L"] > height * .01 * meters
                  and response["surfaces"]["Body"]["maximum_delta_m"] > qa.geometry_guard(meters),
                  measured=response, native_required_knee_delta_m=height * .01 * meters)
            pairs.append(comparison("leg", leg, leg_projected, same, qa, meters))
            control = rig.pose.bones[record["controls"]["hem"]]
            same.unoccupied_handle(rig, control)
            bpy.context.view_layer.update()
            control_pose = control.matrix.copy()
            step = float(record["fit"]["height_world"]) * .04
            direction = rig.matrix_world.to_3x3().col[0].normalized()
            require(math.isfinite(step) and step > 0. and direction.length > .99, "Hem input uses no proved native axis/height")
            reverse = [(side, (point - leg["hem"]).dot(direction)) for side, point in leg["knees"].items()
                       if (point - leg["hem"]).dot(direction) < 0.]
            require(reverse, "No actual knee along reverse Rig X; no penetration target is guessed")
            side, projection = min(reverse, key=lambda item: abs(item[1]))
            report["manual_input"] = {"exact_handle": control.name, "positive_world_units": step,
                "reverse_target_leg": side, "reverse_native_knee_projection_world_units": projection,
                "reverse_world_units": -max(2. * step, abs(projection) + step)}
            for label, offset in (("hem_positive", step), ("hem_reverse", report["manual_input"]["reverse_world_units"])):
                target = control_pose.copy()
                target.translation += rig.matrix_world.to_3x3().inverted() @ (direction * offset)
                local = rig.convert_space(pose_bone=control, matrix=target, from_space="POSE", to_space="LOCAL")
                delta = local.translation - control.matrix_basis.translation
                require(not any(locked and abs(delta[index]) > 1.e-10 for index, locked in enumerate(control.lock_location)),
                        "Real Hem translation lock cannot be bypassed")
                control.matrix_basis = local
                rig.update_tag(refresh={"OBJECT"})
                manual = collect(label + "_baseline", False, handle, common, record, args, same, qa, diag, workflow,
                                 prototype, meters, baseline_contacts, initial_contacts, report)
                manual_projected = collect(label + "_projected", True, handle, common, record, args, same, qa, diag, workflow,
                                           prototype, meters, baseline_contacts, initial_contacts, report)
                change = same.differences(leg, manual, qa, meters, qa.geometry_guard(meters))
                check(report, "same_frame_" + label + "_reaches_final_O", change["hem_handle_delta_m"] > qa.geometry_guard(meters)
                      and change["surfaces"]["O3040"]["maximum_delta_m"] > qa.geometry_guard(meters), measured=change)
                pairs.append(comparison(label, manual, manual_projected, same, qa, meters))
        report["pairs"] = pairs
        report["independent_collision_samples_collected"] = args.mode == "ab" and bool(report["operations"]) and all(
            operation.get("collision", {}).get("status") == "sampled_only" for operation in report["operations"])
        report["initial_contact_pair_classification_collected"] = args.mode == "ab" and bool(
            initial_contacts.get("snapshot") and initial_contacts["snapshot"].get("complete"))
        report["collision_observation_limit"] = "Collection is not completeness or separation: bounded unresolved/open Body/baseline contacts remain Unknown; actual prototype effect is unaccepted."
        if args.mode == "ab":
            collision_complete = (len(report["operations"]) == 8
                and report["independent_collision_samples_collected"]
                and report["initial_contact_pair_classification_collected"]
                and all(operation.get("collision", {}).get("native_sample", {}).get(
                    "same_frame_initial_contact_classification", {}).get("status") == "measured"
                    for operation in report["operations"]))
            report["actual_ab_diagnostic_collection_complete"] = collision_complete
            check(report, "all_eight_actual_Body_and_initial_pair_diagnostics_collected", collision_complete)
        if args.render:
            render_files = []
            render_complete = len(report["operations"]) == (8 if args.mode == "ab" else 2)
            for operation in report["operations"]:
                native_render = operation.get("render", {})
                views = native_render.get("views", {})
                render_complete = render_complete and native_render.get("success") is True \
                    and set(views) == {"front", "side", "back"}
                for view in views.values():
                    path = Path(view["file"]).resolve()
                    render_files.append(str(path))
                    render_complete = render_complete and path.is_relative_to(
                        args.output / "render" / operation["label"]) and path.is_file() \
                        and "FINISHED" in view.get("native_result", ()) \
                        and qa.file_state(path) == view.get("file_state")
            render_complete = render_complete and len(render_files) == len(report["operations"]) * 3 \
                and len(set(render_files)) == len(render_files)
            report["native_three_view_render_collection_complete"] = render_complete
            check(report, "all_requested_actual_native_three_view_PNGs_collected", render_complete,
                  files=render_files)
        check(report, "native_final_topology_weights_and_hard_fixed_waist_unchanged", all(
            pair["native_final_topology_equal"] and pair["native_final_waist_weights_equal"] and pair["native_fixed_mask_equal"]
            and pair["hard_fixed_vertices"] > 0 and pair["hard_fixed_waist_maximum_projection_delta_m"] <= qa.geometry_guard(meters)
            for pair in pairs), pairs=pairs)
        check(report, "projection_does_not_change_same_frame_Body_C_H0", all(
            pair["A_B"]["surfaces"][name]["maximum_delta_m"] <= qa.geometry_guard(meters)
            for pair in pairs for name in ("Body", "C800", "H0800")), pairs=pairs)
        protected_with_prototype = protection.verify()
        check(report, "raw_artist_keys_groups_rest_actions_exact_with_prototype", protected_with_prototype["success"], details=protected_with_prototype)
        # Compare removal at the current tested pose, rather than silently rewinding a manual edit.
        handle["modifier"].show_viewport = handle["modifier"].show_render = False
        source.update_tag(refresh={"OBJECT"})
        removed_reference = same.capture(*common, qa, meters)
        report["prototype_remove"] = prototype.remove_preview(handle)
        handle = None
        after = same.capture(*common, qa, meters)
        difference = same.differences(removed_reference, after, qa, meters, qa.geometry_guard(meters))
        check(report, "native_remove_exact_ID_inventory_and_final_geometry", workflow.inventory() == original_nodes
              and all(entry["maximum_delta_m"] <= qa.geometry_guard(meters) for entry in difference["surfaces"].values()), measured=difference)
        check(report, "canonical_preflight_after_removal", bool(surface.validate(source, rig, qa.skirt.read_record(source))))
        protected_after_cleanup = protection.verify()
        check(report, "raw_artist_after_exact_cleanup", protected_after_cleanup["success"], details=protected_after_cleanup)
        report["native_interface_completed"] = True
        report["mechanism_success"] = all(item["passed"] for item in report["checks"])
        report["success"] = report["mechanism_success"]
    except Exception as error:
        report["error"] = {"message": str(error), "traceback": traceback.format_exc()}
    finally:
        phase("terminal_cleanup_begin")
        if handle is not None:
            try:
                report["failure_exact_cleanup"] = prototype.remove_preview(handle)
                handle = None
            except Exception as error:
                report["failure_cleanup_error"] = str(error)
        if source is not None and handle is None:
            try:
                report["canonical_validation_after_terminal_cleanup"] = bool(surface.validate(source, rig, qa.skirt.read_record(source)))
            except Exception as error:
                report["terminal_canonical_validation_error"] = str(error)
        if protection is not None:
            try:
                report["protected_raw_before_reload"] = protection.verify()
            except Exception as error:
                report["protected_raw_before_reload_error"] = str(error)
        try:
            phase("protected_input_reload_begin")
            result = bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
            require("FINISHED" in result, "Private input cleanup reopen failed")
            report["protected_raw_after_reload"] = protection.verify() if protection else None
            require(report["protected_raw_after_reload"] and report["protected_raw_after_reload"]["success"], "Final protected input check failed")
            phase("protected_input_reload_end")
        except Exception as error:
            report["cleanup_reload_error"] = str(error)
            report["success"] = report["mechanism_success"] = False
        report["input_disk_exact"] = qa.file_state(args.input) == report["input_before"]
        report["artist_disk_exact"] = qa.file_state(artist) == report["artist_before"]
        report["dependency_code_exact"] = all(sha(HERE / name) == expected for name, expected in PINS.items())
        report["canonical_and_frozen_code_exact"] = diag.source_manifest() == report["canonical_before"]
        report["script_code_exact"] = sha(Path(__file__)) == report["script_sha256"]
        terminal_clean = (handle is None and report.get("canonical_validation_after_terminal_cleanup") is True
            and report.get("protected_raw_before_reload", {}).get("success") is True
            and report.get("protected_raw_after_reload", {}).get("success") is True
            and not any(name in report for name in
                ("failure_cleanup_error", "terminal_canonical_validation_error", "protected_raw_before_reload_error", "cleanup_reload_error")))
        report["terminal_cleanup_proved"] = terminal_clean
        report["mechanism_success"] = report["mechanism_success"] and terminal_clean and all(report[key] for key in
            ("input_disk_exact", "artist_disk_exact", "dependency_code_exact", "canonical_and_frozen_code_exact", "script_code_exact"))
        report["success"] = report["mechanism_success"]
        report["elapsed_seconds"] = time.perf_counter() - began
        destination.write_text(json.dumps(diag.json_content(report), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"success": report["success"], "report": str(destination), "elapsed_seconds": report["elapsed_seconds"]}), flush=True)
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
