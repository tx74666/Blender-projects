"""Native, copy-only same-frame Pose diagnosis for the exact installed Cosha.

Preparation is not execution. Run only in a root-leased Blender 5.1 factory
background child. No artist save, deployment, child process or runtime change.
Timing covers native evaluation and mesh reads, never GUI latency or FPS.
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
from mathutils import Quaternion, Vector


HERE = Path(__file__).resolve().parent
WORKFLOW = HERE / "verify_actual_surface_workflow.py"
INSTALL = HERE / "actual_install_51_20261006_031045_111/result/workflow_install.json"
INPUT = INSTALL.parent.parent / "scenes/Cosha_Dress_QA_surface_install.blend"
INPUT_SHA = "7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f"
STATES = ("start", "simulated", "baked")
FRAMES = 20


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--install-report", type=Path, default=INSTALL)
    parser.add_argument("--expected-surface-sha", required=True)
    parser.add_argument("--expected-worker-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--states", choices=STATES, nargs="+", default=["start"])
    parser.add_argument("--body-vertex-limit", type=int, default=100000)
    parser.add_argument("--triangle-pair-limit", type=int, default=10000)
    render = parser.add_mutually_exclusive_group()
    render.add_argument("--render", dest="render", action="store_true")
    render.add_argument("--no-render", dest="render", action="store_false")
    parser.set_defaults(render=False)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.input, args.install_report, args.output = (path.resolve() for path in
        (args.input, args.install_report, args.output))
    require(args.input == INPUT.resolve() and args.install_report == INSTALL.resolve()
            and args.input.is_file() and args.install_report.is_file(), "Use the exact 7ac installed QA/report")
    require(sha(args.input) == INPUT_SHA, "The installed QA bytes changed")
    require(args.output.is_relative_to(HERE) and args.output != HERE
            and not args.input.is_relative_to(args.output), "Use a separate dedicated Validation child")
    require(len(args.states) == len(set(args.states)), "Repeated states are refused")
    require(1000 <= args.body_vertex_limit <= 100000 and 1000 <= args.triangle_pair_limit <= 100000,
            "Native collision budgets are outside the declared bounds")
    for relative in ["same_frame_pose.json", *("states/" + state for state in args.states)]:
        require(not (args.output / relative).exists(), "Refusing to replace an existing diagnostic: " + relative)
    return args


def cache_state(cloth, qa):
    cache = cloth.point_cache
    return {**qa.cache_state(cloth), "is_baking": bool(cache.is_baking),
            "is_outdated": bool(cache.is_outdated), "info": str(cache.info),
            "filepath": str(cache.filepath), "library_path": bool(cache.use_library_path),
            "index": int(cache.index)}


def summary(points, qa):
    finite = bool(points) and all(math.isfinite(value) for point in points for value in point)
    return {"vertices": len(points), "finite": finite,
            "world_coordinates_f32_sha256": hashlib.sha256(qa.pack(points).tobytes()).hexdigest(),
            "minimum_world": [float(min(point[axis] for point in points)) for axis in range(3)] if finite else None,
            "maximum_world": [float(max(point[axis] for point in points)) for axis in range(3)] if finite else None}


def capture(source, rig, actual, neutral, body, legs, cloth, scene, frame, qa, meters):
    require(scene.frame_current == frame and scene.frame_subframe == 0., "A same-frame read changed frame/subframe")
    began = time.perf_counter()
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    graph_ready_seconds = time.perf_counter() - began
    points, mesh_readback_seconds = {}, {}
    for label, obj in (("Body", body), ("C800", actual), ("H0800", neutral), ("O3040", source)):
        read_began = time.perf_counter()
        points[label] = qa.world_mesh(obj, graph)["points"]
        mesh_readback_seconds[label] = time.perf_counter() - read_began
    require(len(points["C800"]) == len(points["H0800"]) == 800 and len(points["O3040"]) == 3040,
            "The proved native evaluated surface counts changed; no index correspondence is guessed")
    require(all(qa.finite(values) for values in points.values()), "Nonfinite actual evaluated native geometry")
    evaluated = rig.evaluated_get(graph)
    knees = {side: evaluated.matrix_world @ evaluated.pose.bones[entry["chain"][1]].head
             for side, entry in legs.items()}
    hem_name = qa.skirt.read_record(source)["controls"]["hem"]
    hem = evaluated.matrix_world @ evaluated.pose.bones[hem_name].matrix.translation
    native_read_seconds = time.perf_counter() - began
    public = {"frame": int(scene.frame_current), "subframe": float(scene.frame_subframe),
              "surfaces": {label: summary(values, qa) for label, values in points.items()},
              "knee_world": {side: [float(value) for value in point] for side, point in knees.items()},
              "hem_handle_world": [float(value) for value in hem], "cache": cache_state(cloth, qa),
              "units_to_metres": float(meters),
              "native_timing_segments": {
                  "view_layer_update_and_graph_ready_seconds": graph_ready_seconds,
                  "world_mesh_readback_seconds_by_surface": mesh_readback_seconds,
                  "scope": "Direct non-overlapping phase timings; readback includes native mesh realization, Python extraction and cleanup. Not pure solver or GUI FPS."}}
    return {"points": points, "knees": knees, "hem": hem, "public": public, "native_read_seconds": native_read_seconds}


def differences(before, after, qa, meters, guard):
    result = {}
    for label, points in after["points"].items():
        old = before["points"][label]
        require(len(old) == len(points), "Exact evaluated vertex identity changed: " + label)
        distances = [(point - previous).length * meters for point, previous in zip(points, old)]
        result[label] = {"maximum_delta_m": float(max(distances, default=0.)),
                         "rms_delta_m": float(math.sqrt(sum(value * value for value in distances) / len(distances)))
                         if distances else None,
                         "vertices_above_geometry_guard": sum(value > guard for value in distances)}
    return {"surfaces": result,
            "knee_delta_m": {side: float((after["knees"][side] - old).length * meters)
                             for side, old in before["knees"].items()},
            "hem_handle_delta_m": float((after["hem"] - before["hem"]).length * meters),
            "cache_metadata_equal": before["public"]["cache"] == after["public"]["cache"],
            "geometry_guard_m": float(guard)}


def same_frame_contact_snapshot(final, body_mesh, crossing, final_local, body_local, leg_names):
    """Copy exact evaluated identities and initial-contact evidence into plain data."""
    problems = []
    identities = {}
    for label, mesh, local in (("final", final, final_local), ("body", body_mesh, body_local)):
        points = tuple(tuple(float(value) for value in point) for point in local)
        triangles = tuple(tuple(int(index) for index in triangle) for triangle in mesh.get("triangles", ()))
        weights = tuple(tuple((int(item["index"]), item["name"], float(item["weight"]))
                              for item in vertex) for vertex in mesh.get("weights", ()))
        if (not points or len(points) != len(mesh.get("points", ()))
                or any(len(point) != 3 or not all(math.isfinite(value) for value in point) for point in points)
                or not triangles or any(len(triangle) != 3 or any(index < 0 or index >= len(points)
                                                               for index in triangle) for triangle in triangles)):
            problems.append(label + "_native_geometry_identity_incomplete")
        if not isinstance(mesh.get("object"), str) or not mesh["object"]:
            problems.append(label + "_native_object_identity_missing")
        if (len(weights) != len(points) or not all(weights)
                or any(name is None or not math.isfinite(weight) or weight < 0.
                       for vertex in weights for _index, name, weight in vertex)):
            problems.append(label + "_native_weights_incomplete")
        identities[label] = {"object": mesh.get("object"), "triangles": triangles, "weights": weights,
                             "vertices": len(points)}
        identities[label + "_local"] = points
    free = tuple(sorted(int(index) for index in final.get("free_indices", ())))
    if not free or len(free) != len(set(free)) or any(index < 0 or index >= identities["final"]["vertices"] for index in free):
        problems.append("final_free_identity_incomplete")
    identities["final"]["free_indices"] = free
    if not leg_names:
        problems.append("native_leg_binding_identity_missing")
    unresolved = ("coplanar_unresolved", "degenerate_unresolved", "boundary_unresolved")
    if crossing.get("status") != "measured" or any(name not in crossing or crossing[name] for name in unresolved):
        problems.append("native_crossing_budget_or_unresolved_coverage")
    pairs = {}
    for entry in crossing.get("crossing_pairs", ()):
        pair = (int(entry["dress_triangle"]), int(entry["body_triangle"]))
        if (pair in pairs or not 0 <= pair[0] < len(identities["final"]["triangles"])
                or not 0 <= pair[1] < len(identities["body"]["triangles"])):
            problems.append("native_crossing_pair_identity_incomplete")
            continue
        indices = (identities["final"]["triangles"][pair[0]], identities["body"]["triangles"][pair[1]])
        if indices != (tuple(entry["dress_vertices"]), tuple(entry["body_vertices"])):
            problems.append("native_crossing_pair_vertices_changed")
        pairs[pair] = indices
    if "crossing_pairs" not in crossing or crossing.get("actual_crossing_pair_count") != len(pairs):
        problems.append("native_crossing_pair_set_incomplete")
    return {**identities, "pairs": pairs, "leg_names": tuple(sorted(leg_names)),
            "complete": not problems, "problems": sorted(set(problems))}


def same_frame_contact_classification(label, frame, current, initial, meters, guard):
    """New crossings are exact initial-pair differences, even for a still skirt."""
    # Seal the first operation attempt, including failure. A later successful
    # Pose sample must never become an invented pre-input baseline.
    if label == "initial_pose":
        require(not initial.get("attempted"), "Initial same-frame contacts were already sealed")
        initial.update(attempted=True, frame=frame, snapshot=current)
    reference = initial.get("snapshot")
    report = {"status": "unknown", "baseline_operation": "initial_pose", "baseline_frame": initial.get("frame"),
              "current_operation": label, "current_frame": frame, "movement_guard_m": float(guard),
              "initial_complete": bool(reference and reference["complete"]),
              "current_complete": bool(current and current["complete"]),
              "new_free_crossing_observed": None, "whole_surface_separation_accepted": False,
              "definition": "Exact native initial strict triangle-pair difference at this held frame; skirt motion is not required for a new crossing",
              "limitation": "Waist-transition contacts remain separate; open Body has no volume sign, and zero new pairs is not separation acceptance"}
    problems = []
    if not reference or not reference["complete"]:
        problems.append("initial_contact_proof_missing_or_incomplete")
    if not current or not current["complete"]:
        problems.append("current_contact_proof_missing_or_incomplete")
    if current:
        report["current_observed_strict_pair_count"] = len(current["pairs"])
        report["current_problems"] = current["problems"]
    if reference:
        report["initial_observed_strict_pair_count"] = len(reference["pairs"])
        report["initial_problems"] = reference["problems"]
        report["initial_exact_pair_set_sha256"] = hashlib.sha256(json.dumps(sorted(reference["pairs"]),
                                                                           separators=(",", ":")).encode()).hexdigest()
    if reference and current and (frame != initial["frame"] or any(reference[name] != current[name]
                                                         for name in ("final", "body", "leg_names"))):
        problems.append("same_frame_native_topology_weight_or_binding_identity_changed")
    if problems:
        report["unknown_reasons"] = problems
        return report
    free = set(current["final"]["free_indices"])
    legs = set(current["leg_names"])
    categories = {name: [] for name in ("waist_transition_contacts", "baseline_free_contacts",
                                        "new_free_leg_crossings", "new_free_other_body_crossings")}
    for pair, (dress_ids, body_ids) in sorted(current["pairs"].items()):
        skirt_move = max(math.dist(current["final_local"][index], reference["final_local"][index]) * meters for index in dress_ids)
        body_move = max(math.dist(current["body_local"][index], reference["body_local"][index]) * meters for index in body_ids)
        body_leg = any(name in legs and weight > 0. for index in body_ids
                       for _group, name, weight in current["body"]["weights"][index])
        initial_pair = pair in reference["pairs"]
        category = ("waist_transition_contacts" if not all(index in free for index in dress_ids)
                    else "baseline_free_contacts" if initial_pair
                    else "new_free_leg_crossings" if body_leg else "new_free_other_body_crossings")
        categories[category].append({"dress_triangle": pair[0], "body_triangle": pair[1],
            "present_in_initial_exact_set": initial_pair, "body_leg_weight_present": body_leg,
            "skirt_waist_relative_vertex_motion_m": float(skirt_move), "body_waist_relative_vertex_motion_m": float(body_move),
            "skirt_triangle_moved_above_guard": skirt_move > guard, "body_triangle_moved_above_guard": body_move > guard})
    report.update(status="measured", counts={name: len(entries) for name, entries in categories.items()},
                  first_pairs={name: entries[:8] for name, entries in categories.items()},
                  maximum_current_pair_skirt_motion_m=max((entry["skirt_waist_relative_vertex_motion_m"]
                                                        for entries in categories.values() for entry in entries), default=None),
                  maximum_current_pair_body_motion_m=max((entry["body_waist_relative_vertex_motion_m"]
                                                       for entries in categories.values() for entry in entries), default=None),
                  new_free_crossing_observed=bool(categories["new_free_leg_crossings"] or categories["new_free_other_body_crossings"]))
    return report


def checked_collision(label, source, rig, actual, body, cloth, record, frame, args, qa, diag, workflow, meters, baseline, initial_contacts):
    began = time.perf_counter()
    cache_before = cache_state(cloth, qa)
    try:
        item, final, body_mesh, bounds = workflow.motion_collision_sample(
            source, rig, actual, body, record, frame, args, qa, diag, meters, baseline)
        item["same_frame_definition"] = (
            "Frozen helper classification relative to this state's initial pose at the same frame; "
            "its skirt-motion filter may label a newly crossing moving Body as stationary. "
            "Use the independent initial-contact proof below; open Body has no inside/outside sign.")
        # Reuse the exact returned native mesh snapshots, without another mesh
        # evaluation. Only this bounded BVH pair test is repeated to retain the
        # full pair set which the frozen sequence scalar report truncates.
        try:
            epsilon = max(1.e-8, record["fit"]["height_world"] * 1.e-6)
            crossing = diag.triangle_crossings(final, body_mesh, bounds, args.triangle_pair_limit, epsilon)
            graph = bpy.context.evaluated_depsgraph_get()
            evaluated = rig.evaluated_get(graph)
            waist = workflow.rigid_frame(evaluated.matrix_world @ evaluated.pose.bones[record["controls"]["waist"]].matrix)
            snapshot = same_frame_contact_snapshot(final, body_mesh, crossing,
                workflow.rigid_points(final["points"], waist), workflow.rigid_points(body_mesh["points"], waist),
                {name for chain in bounds["leg_chains"].values() for name in chain})
            item["same_frame_initial_contact_classification"] = same_frame_contact_classification(
                label, frame, snapshot, initial_contacts, meters, qa.geometry_guard(meters))
        except Exception as error:
            if label == "initial_pose" and not initial_contacts.get("attempted"):
                initial_contacts.update(attempted=True, frame=frame, snapshot=None)
            item["same_frame_initial_contact_classification"] = {
                "status": "unknown", "baseline_operation": "initial_pose", "baseline_frame": initial_contacts.get("frame"),
                "current_operation": label, "reason": str(error), "new_free_crossing_observed": None,
                "whole_surface_separation_accepted": False}
        item["whole_surface_separation_accepted"] = False
        return {"status": "sampled_only", "native_sample": item,
                "wall_seconds": time.perf_counter() - began,
                "cache_before": cache_before, "cache_after": cache_state(cloth, qa)}, (final, body_mesh, bounds)
    except Exception as error:
        if label == "initial_pose" and not initial_contacts.get("attempted"):
            initial_contacts.update(attempted=True, frame=frame, snapshot=None)
        return {"status": "unmeasured", "reason": str(error), "traceback": traceback.format_exc(),
                "wall_seconds": time.perf_counter() - began,
                "cache_before": cache_before, "cache_after": cache_state(cloth, qa),
                "whole_surface_separation_accepted": False}, None


def operation(label, mutate, source, rig, actual, neutral, body, legs, cloth, scene, frame,
              before, baseline, initial_contacts, args, qa, diag, surface, workflow, meters, result):
    evidence = {"operation": label, "frame": frame, "cache_before_input": cache_state(cloth, qa)}
    result["operations"].append(evidence)  # Keep partial evidence if a native read fails.
    began = time.perf_counter()
    if mutate is not None:
        mutate()
        rig.update_tag(refresh={"OBJECT"})
    input_seconds = time.perf_counter() - began
    cold = capture(source, rig, actual, neutral, body, legs, cloth, scene, frame, qa, meters)
    evidence["cold_native_update_and_reads_seconds"] = input_seconds + cold["native_read_seconds"]
    evidence["cold_including_geometry_summaries_seconds"] = time.perf_counter() - began
    evidence["cold"] = cold["public"]
    evidence["delta_from_previous_operation"] = differences(before, cold, qa, meters, qa.geometry_guard(meters)) if before else None
    repeats = []
    last = cold
    for index in range(3):
        began = time.perf_counter()
        last = capture(source, rig, actual, neutral, body, legs, cloth, scene, frame, qa, meters)
        repeats.append({"repeat": index + 1, "seconds": last["native_read_seconds"],
                        "native_timing_segments": last["public"]["native_timing_segments"],
                        "including_geometry_summaries_seconds": time.perf_counter() - began,
                        "delta_from_cold": differences(cold, last, qa, meters, qa.geometry_guard(meters)),
                        "cache": last["public"]["cache"]})
    evidence["same_frame_repeated_native_reads"] = repeats
    evidence["same_frame_repeated_median_seconds"] = statistics.median(item["seconds"] for item in repeats)
    evidence["timing_scope"] = ("Cold includes native Pose assignment when present, view-layer update, depsgraph and actual Body/C/H0/O mesh reads; "
                                "three unchanged same-frame repeats include update/depsgraph/mesh reads. First-after-input does not promise OS/cache coldness. "
                                "Geometry hash/bounds summaries have separate inclusive timings; no GUI latency/FPS; collision/render excluded.")
    record = qa.skirt.read_record(source)
    evidence["collision"], render_data = checked_collision(
        label, source, rig, actual, body, cloth, record, frame, args, qa, diag, workflow, meters, baseline, initial_contacts)
    if label == "hem_reverse_toward_leg" and args.render:
        if render_data is None:
            evidence["render"] = {"requested": True, "success": False, "status": "unmeasured_no_native_snapshot"}
        else:
            folder = Path(result["directory"]) / "render"
            folder.mkdir()
            evidence["render"] = diag.native_render(SimpleNamespace(frame=frame, output=folder), *render_data)
            evidence["render"]["visual_quality_accepted"] = False
    return last


def unoccupied_handle(rig, control):
    animation = rig.animation_data
    if animation is None:
        return
    root = control.path_from_id()
    prefixes = tuple(root + "." + name for name in
                     ("location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale"))
    require(not any(curve.data_path.startswith(prefixes) for curve in animation.drivers),
            "The exact hem handle has an authored transform driver; preserved, not bypassed")
    require(animation.action is None and all(track.mute for track in animation.nla_tracks),
            "Author playback is still bound; no hem input will override it")


def playback_state(qa):
    return [{"owner": qa.id_name(owner), "action": qa.id_name(animation.action),
             "slot": getattr(animation.action_slot, "identifier", None),
             "nla": [(track.name, bool(track.mute), bool(track.is_solo)) for track in animation.nla_tracks]}
            for owner in list(bpy.data.objects) + list(bpy.data.shape_keys)
            if (animation := owner.animation_data) is not None]


def pose_checkpoint(rig, qa):
    return {"channels": qa.pose_channels(rig),
            "basis": [[float(value) for value in row] for row in rig.matrix_basis], "rotation_mode": rig.rotation_mode}


def run_state(state, source_name, args, qa, diag, addon, surface, workflow, artist):
    directory = args.output / "states" / state
    directory.mkdir(parents=True)
    result = {"state": state, "directory": str(directory), "diagnostic_complete": False,
              "input_response_confirmed": None, "manual_response_confirmed": None,
              "production_effect_accepted": False, "operations": [], "forward_frames": [],
              "render_requested": bool(args.render)}
    protection = None
    began = time.perf_counter()
    input_before, artist_before = qa.file_state(args.input), qa.file_state(artist)
    try:
        native = bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
        require("FINISHED" in native and Path(bpy.data.filepath).resolve() == args.input, "Exact installed input did not open")
        source, rig, _saved = qa.owned_source(source_name)
        protection = qa.Protection()
        record, rig, actual, cloth, neutral = workflow.motion_objects(source, qa, surface)
        scene = bpy.context.scene
        require(scene.name == record["physics"]["surface"]["home_scene"], "The proved native home Scene is not active")
        preflight = qa.saved_cache_preflight(source, record)
        result["saved_cache_preflight"] = preflight
        require(preflight["allowed"], "Input cache is not proved safe for this independent candidate")
        result["author_pose_checkpoint_sha256"] = qa.digest(pose_checkpoint(rig, qa))
        result["author_playback_checkpoint_sha256"] = qa.digest(playback_state(qa))
        result["author_frame_checkpoint"] = [int(scene.frame_current), float(scene.frame_subframe)]
        for index, action in enumerate(protection.action_refs):
            scene[f"CD_QA_AuthorAction_{index:04d}"] = action
        candidate = directory / "scenes" / ("Cosha_Dress_QA_same_frame_" + state + ".blend")
        qa.save_candidate(candidate, args.input)  # Move filepath before any Pose/cache operation.
        scene.tool_settings.use_keyframe_insert_auto = False
        result["author_animation_backup"] = qa.backup_animation(
            scene, list(bpy.data.objects) + list(bpy.data.shape_keys), protection.action_refs)
        qa.skirt._activate(bpy.context, rig, "POSE")
        qa.public_switch(bpy.ops.character_designer.body_ik_fk_switch, mode="FK")
        legs, axes, body_height = qa.body_inputs(rig, record)
        body, result["registered_body"] = qa.registered_body(bpy.context, rig, args)
        require(body is not None and result["registered_body"]["measured"], "Exact registered Body is unmeasured; no binding guessed")
        require(body == bpy.data.objects.get(record["physics"]["surface"]["body"]), "Registered Body differs from the proved surface Body")
        thigh_name = legs["L"]["chain"][0]
        control_name = record["controls"]["hem"]
        thigh, control = rig.pose.bones[thigh_name], rig.pose.bones.get(control_name)
        require(control is not None, "The saved real hem handle is missing")
        require(not any(thigh.lock_rotation), "The real source FK thigh has rotation locks; no Pose lock is bypassed")
        require(not (thigh.lock_rotations_4d and thigh.lock_rotation_w),
                "The real source FK thigh locks the required quaternion W channel; no Pose lock is bypassed")
        unoccupied_handle(rig, control)
        qa.tuning.apply(bpy.context, (source,), mode="AUTOMATIC")
        scene.frame_start, scene.frame_end = 1, FRAMES
        cloth.point_cache.frame_start, cloth.point_cache.frame_end, cloth.point_cache.frame_step = 1, FRAMES, 1
        settings = bpy.context.window_manager.character_designer_skirt
        settings.source, settings.use_scene_range = source, True
        qa.save_candidate(candidate, args.input)  # Configured candidate still saved before disk cache activation.
        cache_dir = directory / "native_cache"
        cache_dir.mkdir()
        cache = cloth.point_cache
        cache.filepath, cache.use_library_path, cache.use_disk_cache = str(cache_dir), False, True
        require(not cache.use_external and Path(bpy.path.abspath(cache.filepath)).resolve() == cache_dir.resolve(),
                "Native cache is outside this exact private candidate directory")
        result["cache_ownership"] = {"candidate": str(candidate), "explicit_native_filepath": str(cache_dir),
                                     "input_or_artist_cache_reset": False}
        qa.public_switch(bpy.ops.character_designer.dress_motion_reset)
        result["reset_cache"] = cache_state(cloth, qa)
        meters = float(scene.unit_settings.scale_length)
        require(math.isfinite(meters) and meters > 0., "Invalid native metre scale")
        result["input_definition"] = {"native_thigh": thigh_name, "leg_chains": {side: list(item["chain"]) for side, item in legs.items()},
            "axis_native_bone_local": [float(value) for value in axes[thigh_name]], "angle_rad": 0.55,
            "axis_definition": "Frozen qa.body_inputs: inv(native Rest bone 3x3) @ MainRig-local X; no second world inverse",
            "native_hem_handle": control_name, "skirt_keys_added_or_keyed": False,
            "body_height_world": float(body_height), "fit_height_world": float(record["fit"]["height_world"]),
            "units_to_metres": meters}
        frame = 1
        if state in ("simulated", "baked"):
            for frame in range(1, FRAMES + 1):
                clock = time.perf_counter()
                scene.frame_set(frame)
                snapshot = capture(source, rig, actual, neutral, body, legs, cloth, scene, frame, qa, meters)
                result["forward_frames"].append({"frame": frame, "wall_seconds": time.perf_counter() - clock,
                    "surfaces": snapshot["public"]["surfaces"], "cache": snapshot["public"]["cache"]})
            require(not cache.is_baked, "The unbaked sequential state unexpectedly became sealed")
        else:
            scene.frame_set(1)
        if state == "baked":
            from character_designer import skirt as skirt_ui
            clock = time.perf_counter()
            native = bpy.ops.character_designer.skirt_bake_physics("EXEC_DEFAULT")
            result["public_bake"] = {"operator_result": sorted(native), "wall_seconds": time.perf_counter() - clock,
                                     "native_cache": cache_state(cloth, qa), "registered_active_bakes": len(skirt_ui._ACTIVE_BAKES)}
            require("FINISHED" in native and cache.is_baked and not cache.is_baking
                    and qa.skirt.read_record(source)["physics"]["baked_range"] == [1, FRAMES]
                    and not skirt_ui._ACTIVE_BAKES, "Public Bake did not finish and seal this private twenty-frame cache")
            scene.frame_set(FRAMES)
            frame = FRAMES
        result["state_frame"] = frame
        qa.skirt._activate(bpy.context, rig, "POSE")
        require(rig.mode == "POSE" and scene.frame_current == frame, "Native Pose context changed the state frame")
        baseline = {}
        initial_contacts = {}
        common = (source, rig, actual, neutral, body, legs, cloth, scene, frame)
        initial = operation("initial_pose", None, *common, None, baseline, initial_contacts, args, qa, diag, surface, workflow, meters, result)
        thigh_base = thigh.matrix_basis.to_quaternion().copy()
        def bend():
            thigh.rotation_mode = "QUATERNION"
            thigh.rotation_quaternion = thigh_base @ Quaternion(axes[thigh_name], 0.55)
        leg = operation("left_thigh_rig_x_0_55", bend, *common, initial, baseline, initial_contacts, args, qa, diag, surface, workflow, meters, result)
        response = differences(initial, leg, qa, meters, qa.geometry_guard(meters))
        result["leg_input_response"] = {**response, "native_knee_required_delta_m": body_height * .01 * meters,
            "definition": "Actual evaluated left knee plus actual registered Body must move; Cloth gravity alone is insufficient"}
        result["input_response_confirmed"] = (response["knee_delta_m"]["L"] > body_height * .01 * meters
            and response["surfaces"]["Body"]["maximum_delta_m"] > qa.geometry_guard(meters))
        step = float(record["fit"]["height_world"]) * .04
        rig_x = rig.matrix_world.to_3x3().col[0]
        require(math.isfinite(step) and step > 0. and rig_x.length > 1.e-12, "Unmeasured fit height or Rig X axis")
        direction = rig_x.normalized()
        bpy.context.view_layer.update()
        control_pose = control.matrix.copy()
        def handle_at(world_delta):
            target = control_pose.copy()
            target.translation += rig.matrix_world.to_3x3().inverted() @ world_delta
            local = rig.convert_space(pose_bone=control, matrix=target, from_space="POSE", to_space="LOCAL")
            delta = local.translation - control.matrix_basis.translation
            require(not any(locked and abs(delta[index]) > 1.e-10 for index, locked in enumerate(control.lock_location)),
                    "The real hem handle locks a required translation axis; no Pose lock is bypassed")
            control.matrix_basis = local
        forward = operation("hem_positive_rig_x", lambda: handle_at(direction * step), *common,
                            leg, baseline, initial_contacts, args, qa, diag, surface, workflow, meters, result)
        reverse_candidates = [(side, (point - leg["hem"]).dot(direction)) for side, point in leg["knees"].items()
                              if (point - leg["hem"]).dot(direction) < 0.]
        if not reverse_candidates:
            result["reverse_handle_input"] = {"status": "unmeasured", "reason": "No real evaluated knee lies along reverse Rig X; no target guessed"}
        else:
            side, projection = min(reverse_candidates, key=lambda item: abs(item[1]))
            reverse_step = max(2. * step, abs(projection) + step)
            result["reverse_handle_input"] = {"status": "defined_from_native_knee", "target_leg": side,
                "knee_projection_from_original_handle_world": float(projection), "offset_from_original_handle_world": -reverse_step,
                "positive_offset_world": step, "positive_to_reverse_travel_world": step + reverse_step,
                "limitation": "Moves handle beyond the actual knee's Rig-X projection only; contact/clearance must be measured on final triangles"}
            reverse = operation("hem_reverse_toward_leg", lambda: handle_at(-direction * reverse_step), *common,
                                forward, baseline, initial_contacts, args, qa, diag, surface, workflow, meters, result)
            positive_delta, reverse_delta = differences(leg, forward, qa, meters, qa.geometry_guard(meters)), differences(forward, reverse, qa, meters, qa.geometry_guard(meters))
            result["manual_response_confirmed"] = all(item["hem_handle_delta_m"] > qa.geometry_guard(meters)
                and item["surfaces"]["O3040"]["maximum_delta_m"] > qa.geometry_guard(meters)
                for item in (positive_delta, reverse_delta))
        result["author_actions_exact_before_reload"] = all(bpy.data.actions.get(name) is not None
            and qa.digest(qa.action_content(bpy.data.actions[name])) == expected for name, expected in protection.actions.items())
        result["private_cache_files"] = [{"path": str(path), **qa.file_state(path)}
                                         for path in sorted(directory.rglob("*.bphys")) if path.is_file()]
        require(all(Path(item["path"]).resolve().is_relative_to(directory.resolve()) for item in result["private_cache_files"]),
                "Observed native cache path is outside this state")
        result["diagnostic_complete"] = result["author_actions_exact_before_reload"] and result["manual_response_confirmed"] is not None
    except Exception as error:
        result["unmeasured"] = {"reason": str(error), "traceback": traceback.format_exc()}
    finally:
        if protection is not None:
            try:
                require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False), "Exact input reload failed")
                result["restored_initial_assets"] = protection.verify()
                _restored_source, restored_rig, _restored_record = qa.owned_source(source_name)
                result["restored_author_pose_sha256"] = qa.digest(pose_checkpoint(restored_rig, qa))
                result["initial_author_pose_restored_by_exact_input"] = result["restored_author_pose_sha256"] == result["author_pose_checkpoint_sha256"]
                result["author_playback_restored_exact"] = qa.digest(playback_state(qa)) == result["author_playback_checkpoint_sha256"]
                result["author_frame_restored_exact"] = [int(bpy.context.scene.frame_current), float(bpy.context.scene.frame_subframe)] == result["author_frame_checkpoint"]
                result["diagnostic_complete"] = result["diagnostic_complete"] and result["restored_initial_assets"]["success"] and all(
                    result[key] for key in ("initial_author_pose_restored_by_exact_input", "author_playback_restored_exact", "author_frame_restored_exact"))
            except Exception as error:
                result["diagnostic_complete"] = False
                result["restore_error"] = str(error)
        result["input_disk_exact"] = qa.file_state(args.input) == input_before
        result["artist_disk_exact"] = qa.file_state(artist) == artist_before
        result["diagnostic_complete"] = result["diagnostic_complete"] and result["input_disk_exact"] and result["artist_disk_exact"]
        result["elapsed_seconds"] = time.perf_counter() - began
    return result


def main(args):
    require(bpy.app.background and bpy.app.version[:2] == (5, 1) and not bpy.data.filepath
            and "--factory-startup" in sys.argv and "--disable-autoexec" in sys.argv,
            "Use a new isolated Blender 5.1 factory background child; never an artist Console")
    require("--threads" in sys.argv and sys.argv[sys.argv.index("--threads") + 1] == "1", "Use the root-owned --threads 1 child")
    spec = importlib.util.spec_from_file_location("same_frame_workflow", WORKFLOW)
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)
    qa, diag, addon, surface = workflow.load_dependencies()
    artist = Path(json.loads(args.install_report.read_text(encoding="utf-8"))["artist_path"]).resolve()
    report = {"success": False, "diagnostic_scope": "Complete native read/input/protection collection; inspect response booleans and collision Unknowns separately",
              "production_effect_accepted": False, "visual_quality_accepted": False, "artist_saved": False,
              "input": {"path": str(args.input), **qa.file_state(args.input)}, "artist_before": qa.file_state(artist),
              "workflow_sha256_before": sha(WORKFLOW), "script_sha256": sha(Path(__file__)),
              "source_manifest_before": diag.source_manifest(), "states": [], "checks": [],
              "limits": ["Real same-frame Pose mesh reads; no GUI latency/FPS claim",
                         "Static same-frame checks do not prove future simulation response or long-run settling",
                         "Whole-Body sign remains Unknown for open Body; budget/unresolved triangle cases are not Pass",
                         "No skirt Keys or synthetic animation curves are added; author Action assets are never edited/deleted",
                         "All Reset/Bake/cache writes belong to separately saved QA candidates; no artist/input save"]}
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / "same_frame_pose.json"
    try:
        source_name = workflow.motion_input_gate(args, report, qa, diag)
        addon.register()
        for state in args.states:
            report["states"].append(run_state(state, source_name, args, qa, diag, addon, surface, workflow, artist))
            destination.write_text(json.dumps(diag.json_content(report), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
            print(json.dumps({"state": state, "diagnostic_complete": report["states"][-1]["diagnostic_complete"],
                              "elapsed_seconds": report["states"][-1]["elapsed_seconds"]}), flush=True)
        report["success"] = all(item["diagnostic_complete"] for item in report["states"])
    except Exception as error:
        report["error"] = {"reason": str(error), "traceback": traceback.format_exc()}
    finally:
        report["artist_after"] = qa.file_state(artist)
        report["artist_disk_exact"] = report["artist_after"] == report["artist_before"]
        report["input_disk_exact"] = {"path": str(args.input), **qa.file_state(args.input)} == report["input"]
        report["workflow_sha256_after"] = sha(WORKFLOW)
        report["workflow_code_exact"] = report["workflow_sha256_after"] == report["workflow_sha256_before"]
        report["script_code_exact"] = sha(Path(__file__)) == report["script_sha256"]
        report["source_manifest_after"] = diag.source_manifest()
        report["canonical_and_frozen_code_exact"] = report["source_manifest_after"] == report["source_manifest_before"]
        report["success"] = report["success"] and all(report[key] for key in
            ("artist_disk_exact", "input_disk_exact", "workflow_code_exact", "script_code_exact", "canonical_and_frozen_code_exact"))
        report["elapsed_seconds"] = time.perf_counter() - started
        destination.write_text(json.dumps(diag.json_content(report), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"success": report["success"], "report": str(destination), "elapsed_seconds": report["elapsed_seconds"]}), flush=True)
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
