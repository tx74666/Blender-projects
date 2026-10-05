"""Unreleased QA: actual Basis Cloth -> native Surface Deform tracker -> 32 DEF.

Run only in a fresh serial --background --factory-startup --disable-autoexec
--threads 1 child: --python <file> -- --output <fresh Validation directory> --render
One abrupt_stop input, frames 1..60 forward once. No native public reset, bake,
mode switch, or canonical graph validator is called after the graph mutation.
The independent saved candidate uses an unbaked RAM cache and must be replayed
from frame 1. This is a geometry-transfer experiment, not production acceptance.
"""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
BODY_HELPER = HERE / "experimental_body_collision.py"
BODY_HELPER_SHA256 = "08f07d27a5aaf83aa42f15ff579d47d473d6eb901ab0a52ee62022b54a7880b9"
if hashlib.sha256(BODY_HELPER.read_bytes()).hexdigest() != BODY_HELPER_SHA256:
    raise RuntimeError("Frozen Body collision helper differs; refuse this experiment")
sys.path.insert(0, str(HERE))
import experimental_body_collision as bodyqa

diag, qa, skirt, physics = bodyqa.diag, bodyqa.qa, bodyqa.skirt, bodyqa.physics
ARTIST = bodyqa.ARTIST
FRAMES = (1, 7, 25, 30)
BIND_WORLD_LIMIT = 5.e-6
BIND_METRES_LIMIT = 5.e-6
FINAL_PENETRATION_LIMIT_M = .002


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ARTIST)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--body-vertex-limit", type=int, default=100000)
    parser.add_argument("--triangle-pair-limit", type=int, default=2000)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.input, args.output = args.input.resolve(), args.output.resolve()
    require(args.input == ARTIST.resolve() and args.input.is_file(), "Only the saved X.blend is allowed")
    require(args.output.is_relative_to(diag.VALIDATION) and args.output != diag.VALIDATION,
            "Use a separate unique owned Validation output")
    require(1000 <= args.body_vertex_limit and 1 <= args.triangle_pair_limit <= 20000, "Invalid budgets")
    require(not args.output.exists() or (args.output.is_dir() and
            all(item.is_file() and item.suffix == ".log" for item in args.output.iterdir())),
            "Output must be new or contain only this child launcher logs; do not reuse any candidate/cache/report")
    return args


def manifest():
    values = diag.source_manifest()
    for path in (BODY_HELPER, Path(__file__).resolve()):
        values[str(path)] = qa.file_state(path)
    return values


def copy_scalars(source, target):
    """Copy writable native solver settings, without RNA pointers or identity."""
    copied = {}
    for prop in source.bl_rna.properties:
        name = prop.identifier
        if name == "rna_type" or prop.is_readonly or prop.type not in {"BOOLEAN", "INT", "FLOAT", "ENUM"}:
            continue
        value = getattr(source, name)
        if getattr(prop, "is_array", False):
            value = list(value)
        setattr(target, name, value)
        copied[name] = value
    for name, value in copied.items():
        actual = getattr(target, name)
        if getattr(target.bl_rna.properties[name], "is_array", False):
            actual = list(actual)
        require(actual == value, "Native setting copy changed " + name)
    return copied


def topology_content(obj):
    return {"vertices": len(obj.data.vertices),
            "edges": [list(edge.vertices) for edge in obj.data.edges],
            "faces": [list(face.vertices) for face in obj.data.polygons]}


def channels_hash(rig):
    return qa.digest({"pose": qa.pose_channels(rig), "basis": diag.matrix(rig.matrix_basis),
                      "action": qa.action_content(rig.animation_data.action) if rig.animation_data and rig.animation_data.action else None})


def dress_contract(rig, record, source):
    """No new final bones, no skin/shape-key edits, no manual correction changes."""
    names = record["shared"]["names"]
    return qa.digest({"rest": qa.rest_content(rig),
        "constraints": {name: [bodyqa.copied_parameters(c) for c in rig.pose.bones[name].constraints] for name in names},
        "source_modifiers": [bodyqa.copied_parameters(m) for m in source.modifiers],
        "source_record": source.get(skirt.RECORD_KEY),
        "corrections": {key: source[key] for key in source.keys() if "correction" in key},
        "shared_names": list(names)})


def actual_basis(source, record):
    require(source.mode == "OBJECT" and source.library is None and source.data.library is None,
            "Actual Dress raw mesh must be local and outside Edit Mode")
    keys = source.data.shape_keys
    require(keys is None or keys.use_relative, "Absolute Dress Shape Keys are unsupported")
    require(keys is None or all(key == keys.reference_key or key.mute or key.value == 0 for key in keys.key_blocks),
            "This Basis-only experiment refuses active non-Basis Dress shape deformation")
    vertices = [item.co.copy() for item in (keys.reference_key.data if keys else source.data.vertices)]
    faces = [tuple(face.vertices) for face in source.data.polygons]
    plan = record["fit"]
    rings = plan["rings"]
    require(len(vertices) == 800 and len(faces) == 720 and len(rings) == 10 and all(len(ring) == 80 for ring in rings),
            "This isolated experiment expects the documented 800-vertex, 10x80, 720-quad Dress")
    require(all(len(face) == 4 for face in faces), "Actual source Cloth topology must be raw quads")
    require(sorted(index for ring in rings for index in ring) == list(range(len(vertices))), "Fit rings do not partition actual vertices")
    require(len(plan["vertices"]) == len(vertices) and
            max((a - Vector(b)).length for a, b in zip(vertices, plan["vertices"])) <= 1.e-7,
            "Saved fit source positions differ from the actual raw Basis; no guessed remapping")
    expected = {frozenset((upper[col], upper[(col + 1) % 80], lower[(col + 1) % 80], lower[col]))
                for upper, lower in zip(rings, rings[1:]) for col in range(80)}
    require(expected == {frozenset(face) for face in faces}, "Actual face/ring ownership differs")
    require(qa.finite(vertices), "Actual raw Basis contains nonfinite coordinates")
    return vertices, faces


def mapped_pin_weights(tracker, old_cloth, record, count):
    rows, columns = record["physics"]["rows"], record["physics"]["columns"]
    require(rows == 13 and columns == 32 and len(tracker.data.vertices) == 416,
            "This experiment expects the documented 416 tracker / 13x32 grid")
    pin = tracker.vertex_groups.get(old_cloth.settings.vertex_group_mass)
    require(pin is not None, "Frozen tracker pin group missing")
    weights = [next((item.weight for item in vertex.groups if item.group == pin.index), 0.)
               for vertex in tracker.data.vertices]
    require(all(math.isfinite(value) and 0 <= value <= 1 for value in weights), "Native pin weights are invalid")
    mapped = [None] * count
    plan = record["fit"]
    require(len(plan["ring_t"]) == len(plan["rings"]), "Fit ring progression differs")
    for row, (ring, t) in enumerate(zip(plan["rings"], plan["ring_t"])):
        require(math.isfinite(t) and 0 <= t <= 1, "Invalid fit ring progression")
        vertical = t * (rows - 1)
        lo, hi = min(int(math.floor(vertical)), rows - 1), min(int(math.floor(vertical)) + 1, rows - 1)
        blend = vertical - lo
        for col, index in enumerate(ring):
            angular = col * columns / len(ring)
            left, right = int(math.floor(angular)) % columns, (int(math.floor(angular)) + 1) % columns
            fraction = angular - math.floor(angular)
            a = weights[lo * columns + left] * (1 - fraction) + weights[lo * columns + right] * fraction
            b = weights[hi * columns + left] * (1 - fraction) + weights[hi * columns + right] * fraction
            mapped[index] = a * (1 - blend) + b * blend
        if row == 0:
            require(all(mapped[index] == 1 for index in ring), "Mapped first ring must remain fully pinned")
    require(all(value is not None and math.isfinite(value) and 0 <= value <= 1 for value in mapped), "Pin mapping is incomplete")
    return mapped, {"old_group": pin.name, "old_weights": weights, "actual_weights": mapped,
        "mapping": "Saved exact fit.rings/ring_t; bilinear interpolation on native 13x32 pin grid; no nearest vertex pairing",
        "fully_pinned_vertices": sum(value == 1 for value in mapped)}


def projected_face_audit(vertices, faces):
    """Conservative projected winding audit; does not pretend to read native errors."""
    incidence = Counter()
    concave, degenerate = [], []
    for face_index, face in enumerate(faces):
        points = [vertices[index] for index in face]
        for a, b in zip(face, face[1:] + face[:1]):
            incidence[tuple(sorted((a, b)))] += 1
        normal = sum((a.cross(b) for a, b in zip(points, points[1:] + points[:1])), Vector())
        if normal.length <= 1.e-15:
            degenerate.append(face_index)
            continue
        normal.normalize()
        turns = []
        for i, point in enumerate(points):
            before = point - points[i - 1]
            after = points[(i + 1) % len(points)] - point
            before -= normal * before.dot(normal)
            after -= normal * after.dot(normal)
            if min(before.length, after.length) <= 1.e-12:
                degenerate.append(face_index)
                break
            turns.append(before.normalized().cross(after.normalized()).dot(normal))
        else:
            if min(turns, default=0) < -1.1920929e-7:
                concave.append({"face": face_index, "vertices": list(face), "signed_normalized_turns": turns})
            if any(abs(value) <= 1.1920929e-7 for value in turns):
                degenerate.append(face_index)
    return {"concave_projected_faces": concave, "degenerate_or_collinear_faces": sorted(set(degenerate)),
            "edges_more_than_two_faces": [list(edge) for edge, value in incidence.items() if value > 2],
            "native_error_string_claim": False,
            "method": "Newell face normal and normalized projected signed turns; diagnostic inference only"}


def make_actual_cloth(source, rig, tracker, old_cloth, record, collection, report):
    vertices, faces = actual_basis(source, record)
    mapped, pin_report = mapped_pin_weights(tracker, old_cloth, record, len(vertices))
    actual = physics._mesh("QA Actual Basis Dress Cloth", [tuple(v) for v in vertices], faces,
                           collection, skirt.fit_rest_world(source, record), record)
    actual["CD_QA_ActualSurfaceCloth"] = True
    physics._bind_single(actual, rig, record["controls"]["waist"])
    pin = actual.vertex_groups.new(name=old_cloth.settings.vertex_group_mass)
    for index, weight in enumerate(mapped):
        if weight:
            pin.add([index], weight, "REPLACE")
    require(all(prop.identifier == "vertex_group_mass" or not getattr(old_cloth.settings, prop.identifier)
                for prop in old_cloth.settings.bl_rna.properties if prop.identifier.startswith("vertex_group_")),
            "Additional native Cloth group semantics cannot be guessed on the actual topology")
    require(old_cloth.settings.rest_shape_key is None and old_cloth.settings.effector_weights.collection is None,
            "Cloth rest Shape Key or effector collection mapping is unsupported")
    cloth = actual.modifiers.new("QA Actual Surface Cloth", "CLOTH")
    copied = {"settings": copy_scalars(old_cloth.settings, cloth.settings),
              "collision": copy_scalars(old_cloth.collision_settings, cloth.collision_settings),
              "effector_weights": copy_scalars(old_cloth.settings.effector_weights, cloth.settings.effector_weights)}
    cloth.settings.vertex_group_mass = pin.name
    copied["mapped_vertex_group_mass"] = pin.name
    cloth.collision_settings.collection = collection
    cloth.point_cache.frame_start, cloth.point_cache.frame_end, cloth.point_cache.frame_step = 1, 60, 1
    cloth.point_cache.use_disk_cache = False
    require(len(actual.vertex_groups) == 2 and actual.data.shape_keys is None and actual.animation_data is None
            and [m.type for m in actual.modifiers] == ["ARMATURE", "CLOTH"], "Actual Cloth native stack is not exact")
    require(actual.data != source.data and actual.data != tracker.data, "Physical topology is not independent")
    report.update(object=actual.name, mesh=actual.data.name, vertices=len(vertices), faces=len(faces),
        raw_basis_sha256=qa.digest([list(v) for v in vertices]), topology_sha256=qa.digest(topology_content(actual)),
        native_copied_parameters=copied, mapped_pin=pin_report, waist_only_group=record["controls"]["waist"],
        rest_world=diag.matrix(actual.matrix_world), projected_face_audit=projected_face_audit(vertices, faces),
        limitation="Same per-vertex native mass and stiffness settings on 800 rather than 416 vertices; total mass/discretization differ. No automatic material calibration.")
    return actual, cloth


def bind_tracker(rig, tracker, actual, cloth, report):
    scene = bpy.context.scene
    frame, pose_position = scene.frame_current, rig.data.pose_position
    active, mode = bpy.context.view_layer.objects.active, bpy.context.mode
    before_channels = channels_hash(rig)
    show_viewport, show_render = cloth.show_viewport, cloth.show_render
    raw_points = [tracker.matrix_world @ vertex.co for vertex in tracker.data.vertices]
    report["before"] = {"pose_position": pose_position, "frame": frame,
        "pose_action_channels_sha256": before_channels, "tracker_modifiers": [m.type for m in tracker.modifiers]}
    try:
        skirt._activate(bpy.context, tracker, "OBJECT")
        scene.frame_set(0)
        rig.data.pose_position = "REST"
        cloth.show_viewport = cloth.show_render = False
        bpy.context.view_layer.update()
        surface = tracker.modifiers.new("QA Native Actual Surface Transfer", "SURFACE_DEFORM")
        surface.target, surface.strength = actual, 1.0
        result = bpy.ops.object.surfacedeform_bind(modifier=surface.name)
        bpy.context.view_layer.update()
        report["first_attempt"] = {"operator": sorted(result), "is_bound": surface.is_bound,
            "native_error_if_exposed": getattr(surface, "error", None)}
        if not surface.is_bound:
            audit = projected_face_audit([v.co.copy() for v in actual.data.vertices],
                                         [tuple(f.vertices) for f in actual.data.polygons])
            require(audit["concave_projected_faces"] and not audit["edges_more_than_two_faces"]
                    and not audit["degenerate_or_collinear_faces"],
                    "Native binding failed without a safely isolated projected-concave-face diagnosis; refuse fallback")
            tracker.modifiers.remove(surface)
            tri = actual.modifiers.new("QA Concave Target Triangulate After Cloth", "TRIANGULATE")
            tri.quad_method, tri.ngon_method = "FIXED", "CLIP"
            bpy.context.view_layer.update()
            surface = tracker.modifiers.new("QA Native Actual Surface Transfer", "SURFACE_DEFORM")
            surface.target, surface.strength = actual, 1.0
            result = bpy.ops.object.surfacedeform_bind(modifier=surface.name)
            bpy.context.view_layer.update()
            report["triangulate_fallback"] = {"operator": sorted(result), "is_bound": surface.is_bound,
                "audit": audit, "stack": [m.type for m in actual.modifiers],
                "reason": "Native bind was unbound; independent projected-winding audit confirms concave raw quads. Cause is an explicit inference, not an exposed native error string.",
                "solver_quad_topology_unchanged": True, "fixed_triangles_only_after_solver": True}
        require("FINISHED" in result and surface.is_bound, "Native Surface Deform did not bind")
        require([m.type for m in tracker.modifiers] == ["SURFACE_DEFORM"], "Tracker must have one native transfer and no additional skin")
        graph = bpy.context.evaluated_depsgraph_get()
        snapshot = diag.mesh_snapshot(tracker, graph)
        require(len(raw_points) == len(snapshot["points"]) and qa.finite(snapshot["points"]), "Bound tracker changed topology or became nonfinite")
        delta = max(((a - b).length for a, b in zip(raw_points, snapshot["points"])), default=0.)
        meters = scene.unit_settings.scale_length
        require(math.isfinite(meters) and meters > 0 and delta <= BIND_WORLD_LIMIT and delta * meters <= BIND_METRES_LIMIT,
                "Neutral Rest Surface Deform binding displaced the tracker")
        report.update(is_bound=True, neutral_baseline_max_world=delta, neutral_baseline_max_m=delta * meters,
            maximum_allowed_world=BIND_WORLD_LIMIT, maximum_allowed_m=BIND_METRES_LIMIT,
            native_modifier=bodyqa.copied_parameters(surface),
            tracker_relative_to_target_at_bind=diag.matrix(tracker.matrix_world.inverted() @ actual.matrix_world),
            target_evaluated_vertices=len(diag.mesh_snapshot(actual, graph)["points"]),
            target_evaluated_faces=len(diag.mesh_snapshot(actual, graph)["faces"]))
    finally:
        rig.data.pose_position = pose_position
        cloth.show_viewport, cloth.show_render = show_viewport, show_render
        scene.frame_set(frame)
        if active is not None:
            skirt._activate(bpy.context, active, "POSE" if mode == "POSE" else "OBJECT")
        bpy.context.view_layer.update()
        report["restored"] = {"pose_position": rig.data.pose_position, "frame": scene.frame_current,
            "pose_action_channels_sha256": channels_hash(rig), "active": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
            "mode": bpy.context.mode}
        require(channels_hash(rig) == before_channels and scene.frame_current == frame and rig.data.pose_position == pose_position,
                "Binding did not restore candidate pose/action/object channels exactly")
    return surface


def free_indices(snapshot, group):
    require(any(snapshot["weights"]), "Native evaluated weight layer missing")
    return [index for index, weights in enumerate(snapshot["weights"])
            if next((item["weight"] for item in weights if item["index"] == group.index), 0.) < .999]


def make_skin_probe(source, actual, collection, report):
    """Disposable object copy: shared raw data, only its own Subsurf removed."""
    require([m.type for m in source.modifiers] == ["ARMATURE", "SUBSURF"],
            "Same-index skin probe requires the exact native Armature/Subsurf source stack")
    require(all(m.show_viewport and m.show_render for m in source.modifiers), "Source skin/Subsurf visibility differs")
    source_properties = qa.digest(qa.custom_content({key: source[key] for key in source.keys()}))
    data_properties = qa.digest(qa.custom_content({key: source.data[key] for key in source.data.keys()}))
    original_modifiers = [bodyqa.copied_parameters(m) for m in source.modifiers]
    probe = source.copy()
    try:
        probe.name = "QA Disposable Same Index Skin Probe"
        collection.objects.link(probe)
        require(probe.data == source.data and probe.data != actual.data, "Probe must share only the artist raw mesh read-only")
        require([bodyqa.copied_parameters(m) for m in probe.modifiers] == original_modifiers,
                "Native object copy changed source modifier parameters")
        probe.modifiers.remove(probe.modifiers[1])
        probe.hide_render = True
        probe.hide_set(False)
        require([m.type for m in probe.modifiers] == ["ARMATURE"] and
                bodyqa.copied_parameters(probe.modifiers[0]) == original_modifiers[0], "Probe changed Armature semantics")
        require(diag.matrix(probe.matrix_world) == diag.matrix(source.matrix_world) and
                [(g.index, g.name) for g in probe.vertex_groups] == [(g.index, g.name) for g in source.vertex_groups],
                "Probe changed transform or native vertex-group index mapping")
        require(source_properties == qa.digest(qa.custom_content({key: source[key] for key in source.keys()})) and
                data_properties == qa.digest(qa.custom_content({key: source.data[key] for key in source.data.keys()})),
                "Probe construction changed source metadata")
        report.update(object=probe.name, shared_raw_mesh=source.data.name, independent_object=True,
            source_properties_sha256=source_properties, source_data_properties_sha256=data_properties,
            original_modifier_parameters=original_modifiers, clone_armature_parameters=bodyqa.copied_parameters(probe.modifiers[0]),
            removed_modifier_type="SUBSURF", raw_vertex_count=len(source.data.vertices),
            definition="Native object.copy shares artist raw Mesh/Shape Keys read-only; only clone Subsurf removed. No source modifier, coordinate, weight, group, key, or transform edits.")
    except Exception:
        bpy.data.objects.remove(probe, do_unlink=True)
        raise
    return probe


def remove_skin_probe(probe, source, report):
    if probe is None:
        return
    name = probe.name
    require(probe.data == source.data, "Disposable probe no longer shares the protected source mesh")
    bpy.data.objects.remove(probe, do_unlink=True)
    require(name not in bpy.data.objects and source.data.name in bpy.data.meshes, "Disposable probe cleanup failed")
    require(report["source_properties_sha256"] == qa.digest(qa.custom_content({key: source[key] for key in source.keys()})) and
            report["source_data_properties_sha256"] == qa.digest(qa.custom_content({key: source.data[key] for key in source.data.keys()})),
            "Probe lifetime changed source metadata")
    report["removed_before_candidate_save"] = True


def endpoint_measurements(rig, tracker, cage, record, graph, meters):
    evaluated = rig.evaluated_get(graph)
    segments = []
    for ci, chain in enumerate(record["chains"]):
        for si in range(record["segment_count"]):
            names = {layer: chain[layer][si] for layer in ("manual", "phys", "def")}
            aim = rig.pose.bones[names["phys"]].constraints.get("CD Physics Aim")
            require(aim is not None and aim.type == "DAMPED_TRACK" and aim.target == tracker,
                    "Exact frozen native PHYS aim target changed")
            target = diag.weighted_target(tracker, cage, aim.subtarget)
            require(target["available"] and target["single_native_target_vertex"] is not None,
                    "Native PHYS endpoint group no longer contains its exact single target")
            center = Vector(target["weighted_world_center"])
            layers = {layer: diag.bone_content(rig, evaluated, name) for layer, name in names.items()}
            errors = {layer: diag.residual(evaluated, names[layer], center, meters) for layer in ("phys", "def")}
            require(all(item["available"] for item in errors.values()), "Native endpoint coincides with bone head")
            manual = layers["manual"]
            segments.append({"chain": ci, "segment": si, "names": names, "exact_target_group": aim.subtarget,
                "exact_tracker_vertex": target["single_native_target_vertex"], "exact_target_world": target["weighted_world_center"],
                "phys_tail_vs_tracker": errors["phys"], "def_tail_vs_tracker": errors["def"],
                "def_rest_length_m": layers["def"]["rest_length_world_at_current_object_transform"] * meters,
                "def_eval_length_m": layers["def"]["eval_length_world"] * meters,
                "manual_eval_length_m": manual["eval_length_world"] * meters,
                "manual_raw_scale": manual["channels"]["scale"],
                "manual_evaluated_channel_scale": manual["evaluated_channels"]["scale"],
                "manual_eval_to_rest_length_ratio": manual["eval_length_world"] / manual["rest_length_world_at_current_object_transform"]})
    require(len(segments) == 32, "Endpoint diagnostic must cover all exact 32 segments")
    worst = sorted(segments, key=lambda item: max(item["phys_tail_vs_tracker"]["tail_to_target_error_m"],
                                                item["def_tail_vs_tracker"]["tail_to_target_error_m"]), reverse=True)[:8]
    return {"segment_count": len(segments), "phys_tail_target_max_m": max(s["phys_tail_vs_tracker"]["tail_to_target_error_m"] for s in segments),
        "def_tail_target_max_m": max(s["def_tail_vs_tracker"]["tail_to_target_error_m"] for s in segments),
        "phys_target_distance_minus_length_max_abs_m": max(abs(s["phys_tail_vs_tracker"]["target_distance_minus_bone_length_m"]) for s in segments),
        "phys_axis_target_max_angle_rad": max(s["phys_tail_vs_tracker"]["axis_y_to_exact_target_angle_rad"] for s in segments),
        "segments": segments, "worst8": worst,
        "definition": "Exact evaluated CD Physics Aim target groups on bound tracker; native PHYS and final DEF endpoints/lengths, all 32 segments. No nearest target inference."}


def same_index_skin_gap(source, probe, actual, physical, record, graph, meters):
    skinned = diag.mesh_snapshot(probe, graph)
    raw_faces = [tuple(face.vertices) for face in source.data.polygons]
    raw_edges = [tuple(edge.vertices) for edge in source.data.edges]
    raw_groups = {group.index: group.name for group in source.vertex_groups}
    raw_weights = [[{"index": item.group, "name": raw_groups[item.group], "weight": item.weight} for item in vertex.groups]
                   for vertex in source.data.vertices]
    require(len(skinned["points"]) == len(physical["points"]) == len(source.data.vertices) == 800,
            "Same-index skin/physical diagnostic lost raw 800-vertex correspondence")
    require(skinned["faces"] == raw_faces and skinned["edges"] == raw_edges and skinned["weights"] == raw_weights,
            "Armature-only probe changed raw indices/topology or evaluated vertex weights")
    require([tuple(face.vertices) for face in actual.data.polygons] == raw_faces,
            "Actual physical Cloth raw face-index mapping differs from the source")
    require(diag.matrix(probe.matrix_world) == diag.matrix(source.matrix_world) and qa.finite(skinned["points"]),
            "Same-index probe transform or finite evaluation failed")
    gaps = [(a-b).length * meters for a, b in zip(skinned["points"], physical["points"])]
    ring_indices = {index: (row, col) for row, ring in enumerate(record["fit"]["rings"]) for col, index in enumerate(ring)}
    worst = [{"raw_vertex_index": index, "exact_saved_ring_column": list(ring_indices[index]), "gap_m": gaps[index],
        "skinned_world": diag.vector(skinned["points"][index]), "physical_world": diag.vector(physical["points"][index]),
        "skin_minus_physical_world": diag.vector(skinned["points"][index]-physical["points"][index]),
        "native_source_weights": raw_weights[index]} for index in sorted(range(800), key=lambda i: gaps[i], reverse=True)[:16]]
    return {"raw_vertex_count": 800, "same_indices_proved": True, "raw_faces_edges_weights_exact": True,
        "shared_mesh_read_only": probe.data == source.data, "clone_modifiers": [m.type for m in probe.modifiers],
        "gap_max_m": max(gaps), "gap_rms_m": math.sqrt(sum(value*value for value in gaps)/len(gaps)), "worst16": worst,
        "definition": "Exact raw source indices: native Armature-only clone vs independent actual-topology Cloth. No correspondence inferred from the subdivided final mesh."}


def measured_frame(args, source, rig, tracker, actual, cloth, record, body, clone, probe, frame):
    graph = bpy.context.evaluated_depsgraph_get()
    physical, cage, final = (diag.mesh_snapshot(obj, graph) for obj in (actual, tracker, source))
    body_mesh, clone_mesh = (diag.mesh_snapshot(obj, graph) for obj in (body, clone))
    require(body_mesh["faces"] == clone_mesh["faces"] and len(body_mesh["points"]) == len(clone_mesh["points"]),
            "Actual Body collider clone topology changed")
    body_delta = max(((a - b).length for a, b in zip(body_mesh["points"], clone_mesh["points"])), default=0.)
    require(body_delta <= 1.e-8, "Actual Body collision clone moved away from the registered Body")
    require(all(qa.finite(mesh["points"]) for mesh in (physical, cage, final)), "Simulated geometry is nonfinite")
    final["free_indices"] = free_indices(final, source.vertex_groups[record["controls"]["waist"]])
    physical["free_indices"] = free_indices(physical, actual.vertex_groups[cloth.settings.vertex_group_mass])
    cage["free_indices"] = free_indices(cage, tracker.vertex_groups[cloth.settings.vertex_group_mass])
    bounds = diag.framing(rig, record, graph)
    roles = {name: layer for chain in record["chains"] for layer in ("manual", "phys", "def") for name in chain[layer]}
    roles[record["controls"]["waist"]] = "waist"
    meters = bpy.context.scene.unit_settings.scale_length
    epsilon = max(1.e-8, record["fit"]["height_world"] * 1.e-6)
    final_body, _ = diag.body_diagnostics(body, graph, final, bounds, args, meters, roles, epsilon)
    physical_body, _ = diag.body_diagnostics(body, graph, physical, bounds, args, meters, roles, epsilon)
    tracker_body, _ = diag.body_diagnostics(body, graph, cage, bounds, args, meters, roles, epsilon)
    colliders = diag.collider_diagnostics(final, physical, record, graph, meters, roles, epsilon)
    max_penetration = max(item["final_free"]["maximum_penetration_m"] for item in colliders.values())
    item = {"frame": frame, "body_clone_actual_max_delta_world": body_delta,
        "physical_vertices": len(physical["points"]), "physical_faces": len(physical["faces"]),
        "tracker_vertices": len(cage["points"]), "final_vertices": len(final["points"]),
        "old3_owned_colliders": colliders,
        "final_free_penetration_2mm_diagnostic": {"maximum_penetration_m": max_penetration,
            "unchanged_limit_m": FINAL_PENETRATION_LIMIT_M, "within_limit": max_penetration <= FINAL_PENETRATION_LIMIT_M,
            "production_effect_acceptance": False},
        "actual_registered_body_vs_final": final_body, "actual_registered_body_vs_physical_cloth": physical_body,
        "actual_registered_body_vs_surface_deform_tracker": tracker_body,
        "native_endpoint_transfer": endpoint_measurements(rig, tracker, cage, record, graph, meters),
        "same_index_basis_skin_vs_physical_cloth": same_index_skin_gap(source, probe, actual, physical, record, graph, meters),
        "free_definitions": {"final_waist": record["controls"]["waist"], "physical_pin": cloth.settings.vertex_group_mass,
            "fully_pinned_weights_excluded_at": .999},
        "physical_world": [diag.vector(point) for point in physical["points"]],
        "tracker_world": [diag.vector(point) for point in cage["points"]],
        "final_world": [diag.vector(point) for point in final["points"]], "final_actual_weights": final["weights"]}
    if args.render and frame == 25:
        item["render"] = diag.native_render(SimpleNamespace(frame=frame, output=args.output), final, body_mesh, bounds)
    return item


def main(args):
    isolation = qa.require_isolated_background()  # Before register, open, mkdir or save.
    require(Path(diag.character_designer.__file__).resolve().is_relative_to(diag.REPOSITORY / "addons"), "Canonical import proof failed")
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "experimental_actual_surface.json"
    candidate = args.output / "Cosha_Dress_QA_experimental_actual_surface.blend"
    report = {"success": False, "production_effect_accepted": False, "canonical_full_graph_pass": False,
        "purpose": "Unreleased actual raw Basis Cloth -> Surface Deform tracker -> existing final DEF diagnostic",
        "artist_operation": False, "isolation": isolation, "frozen_body_helper_sha256": BODY_HELPER_SHA256,
        "artist_before": qa.file_state(args.input), "code_before": manifest(), "frames": [], "errors": [],
        "body_inside_outside_claim": False, "render_requested": args.render, "render_focus_frame": 25,
        "sample_frames": list(FRAMES), "simulation_frames": 60, "simulation_passes": 1,
        "post_experimental_cache_reset_bake_public_mode_or_canonical_validator_calls": [],
        "limitations": ["Representative QA abrupt-stop Action, not production animation",
            "Registered Body is open: unsigned distances/normal estimates do not prove inside/outside; exact finite triangle crossing diagnostics are separate",
            "800-vertex Cloth discretization/material response differs from the 416 cage despite exact copied native settings",
            "Surface Deform may bind to a neighboring pleat when the tracker lies far from the actual source surface",
            "Final 32-bone skin interpolation may still differ from physical surface; no topology or weights replacement",
            "Unbaked RAM cache is not persistent after reopening; replay frames 1..60 forward for candidate motion"]}
    started, protection, probe, source = time.perf_counter(), None, None, None
    try:
        diag.character_designer.register()
        require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False), "Artist copy open failed")
        protection = qa.Protection()
        report["original_assets_before"] = protection.summary()
        source, rig, record = qa.owned_source(args.source)
        report["artist_cache_preflight"] = qa.saved_cache_preflight(source, record)
        require(report["artist_cache_preflight"]["allowed"], report["artist_cache_preflight"].get("reason", "Unsafe sealed/external artist cache"))
        for index, action in enumerate(protection.action_refs):
            bpy.context.scene[f"CD_QA_AuthorAction_{index:04d}"] = action
        report["initial_owned_save"] = qa.save_candidate(candidate, args.input)
        record, rig, tracker, old_cloth = bodyqa.prepare_copy(source, rig, record, protection, report)
        body, report["registered_body_status"] = qa.registered_body(bpy.context, rig, args)
        require(body is not None, "Registered Body proof/budget failed")
        require(skirt.is_shared(record) and record["chain_count"] == 8 and record["segment_count"] == 4,
                "Only the current shared eight-chain/four-segment Dress graph is supported")
        require(len(record["physics"]["colliders"]) == 3 and not old_cloth.point_cache.is_baked
                and not old_cloth.point_cache.use_disk_cache, "Expected unsealed 3-collider baseline")
        report["canonical_graph_proved_before_experiment"] = True
        report["frozen_record"] = record
        report["frozen_record_raw"] = source.get(skirt.RECORD_KEY)
        report["frozen_dress_contract"] = dress_contract(rig, record, source)
        report["qa_action_hash"] = qa.digest(qa.action_content(rig.animation_data.action))
        report["binding_input_order"] = "Frozen preparation helper authors the abrupt_stop input first; neutral Rest binding then restores those exact pre-bind pose/action/object channels at frame 0 before the first simulation frame. No Action is regenerated or edited by binding."
        report["native_settings_before_experiment"] = {"cloth": qa.simple_rna(old_cloth.settings),
            "collision": qa.simple_rna(old_cloth.collision_settings), "effector_weights": qa.simple_rna(old_cloth.settings.effector_weights)}
        old_collection = old_cloth.collision_settings.collection
        collection = bpy.data.collections.new("QA Actual Surface old3 plus Body Collision")
        bpy.context.scene.collection.children.link(collection)
        report["body_clone"] = {}
        clone = bodyqa.clone_body(body, rig, record, collection, report["body_clone"])
        for name in record["physics"]["colliders"]:
            collection.objects.link(bpy.data.objects[name])
        report["actual_cloth"] = {}
        # The physical mesh belongs outside its own collision collection.
        cloth_collection = bpy.data.collections.new("QA Actual Surface Physical Mesh")
        bpy.context.scene.collection.children.link(cloth_collection)
        actual, cloth = make_actual_cloth(source, rig, tracker, old_cloth, record, cloth_collection, report["actual_cloth"])
        cloth.collision_settings.collection = collection
        exact = set(record["physics"]["colliders"] + [clone.name])
        require(set(collection.objects.keys()) == exact and not collection.children and actual.name not in exact,
                "Collision collection must contain exactly old3 and the independent Body")
        tracker_topology = qa.digest(topology_content(tracker))
        actual_topology = qa.digest(topology_content(actual))
        # Begin the intentionally noncanonical graph. No validated public API below.
        require([m.type for m in tracker.modifiers] == ["ARMATURE", "CLOTH"], "Frozen tracker modifier stack differs")
        for modifier in reversed(list(tracker.modifiers)):
            tracker.modifiers.remove(modifier)
        report["binding"] = {}
        surface = bind_tracker(rig, tracker, actual, cloth, report["binding"])
        report["experimental_graph"] = {"physical_mesh": actual.name, "physical_data": actual.data.name,
            "physical_modifiers": [m.type for m in actual.modifiers], "tracker": tracker.name,
            "tracker_modifiers": [m.type for m in tracker.modifiers], "tracker_target": surface.target.name,
            "old_collision_collection": old_collection.name, "new_collision_collection": collection.name,
            "exact_collision_members": sorted(exact), "same_final_DEF_count": 32,
            "canonical_validator_intentionally_not_called": True,
            "declaration": "UNRELEASED QA graph: tracker now has Surface Deform instead of recorded Cloth. Source record intentionally remains unchanged; no production setup/bake/reset operation may be applied."}
        bpy.context.scene["CD_QA_ExperimentalGraph"] = json.dumps(report["experimental_graph"], ensure_ascii=False)
        require(dress_contract(rig, record, source) == report["frozen_dress_contract"], "Binding changed final bones/constraints/skin/corrections")
        report["disposable_skin_probe"] = {}
        probe = make_skin_probe(source, actual, cloth_collection, report["disposable_skin_probe"])
        relative = tracker.matrix_world.inverted() @ actual.matrix_world
        relative_max_delta = 0.
        expected_target_faces = None
        expected_tracker_faces = None
        for frame in range(1, 61):
            bpy.context.scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            physical = diag.mesh_snapshot(actual, graph)  # Force one native solver forward evaluation per frame.
            tracked = diag.mesh_snapshot(tracker, graph)
            require(qa.finite(physical["points"]) and qa.finite(tracked["points"]) and surface.is_bound, "Native physical/transfer evaluation failed")
            if expected_target_faces is None:
                expected_target_faces, expected_tracker_faces = physical["faces"], tracked["faces"]
            require(physical["faces"] == expected_target_faces and tracked["faces"] == expected_tracker_faces,
                    "Evaluated native Surface Deform topology changed during replay")
            actual_relative = tracker.matrix_world.inverted() @ actual.matrix_world
            relative_delta = max(abs(a-b) for row_a, row_b in zip(relative, actual_relative) for a,b in zip(row_a,row_b))
            relative_max_delta = max(relative_max_delta, relative_delta)
            require(relative_delta <= 1.e-6,
                    "Surface Deform bind-relative object transform changed; refusing frozen-matrix double motion")
            if frame in FRAMES:
                report["frames"].append(measured_frame(args, source, rig, tracker, actual, cloth, record, body, clone, probe, frame))
            if frame % 10 == 0:
                print(f"QA ACTUAL SURFACE {frame}/60", flush=True)
        require(qa.digest(topology_content(tracker)) == tracker_topology and qa.digest(topology_content(actual)) == actual_topology,
                "Experiment modified owned raw tracker/physical topology")
        require(dress_contract(rig, record, source) == report["frozen_dress_contract"], "Replay modified final-bone/source contract")
        require(qa.digest(qa.action_content(rig.animation_data.action)) == report["qa_action_hash"], "Replay changed authored QA input")
        require(set(collection.objects.keys()) == exact and cloth.collision_settings.collection == collection,
                "Exact collision graph changed")
        require(not cloth.point_cache.is_baked and not cloth.point_cache.use_disk_cache, "Experiment unexpectedly sealed/wrote a disk cache")
        report["native_cache_after"] = qa.cache_state(cloth)
        report["bind_relative_matrix_max_numeric_delta"] = relative_max_delta
        remove_skin_probe(probe, source, report["disposable_skin_probe"])
        probe = None
        report["saved_candidate"] = qa.save_candidate(candidate, args.input)
        report["candidate_file"] = qa.file_state(candidate)
        report["candidate_visual_keyframes"] = list(FRAMES)
        report["candidate_replay_required_after_reopen"] = True
        report["diagnostic_completed"] = len(report["frames"]) == len(FRAMES)
    except Exception:
        report["errors"].append(traceback.format_exc())
        if probe is not None:
            try:
                remove_skin_probe(probe, source, report["disposable_skin_probe"])
                probe = None
            except Exception:
                report["errors"].append("Disposable probe cleanup: " + traceback.format_exc())
        # Preserve the independent diagnostic graph/inputs when a late failure permits.
        if probe is None and protection is not None and bpy.data.filepath and Path(bpy.data.filepath).resolve() == candidate.resolve():
            try:
                report["failed_candidate_saved"] = qa.save_candidate(candidate, args.input)
            except Exception:
                report["errors"].append("Failed candidate save: " + traceback.format_exc())
    finally:
        if probe is not None:
            try:
                remove_skin_probe(probe, source, report["disposable_skin_probe"])
                probe = None
            except Exception:
                report["errors"].append("Final disposable probe cleanup: " + traceback.format_exc())
        if protection is not None:
            report["original_asset_protection"] = protection.verify()
        report["artist_after"], report["code_after"] = qa.file_state(args.input), manifest()
        report["artist_disk_exact"] = report["artist_after"] == report["artist_before"]
        report["code_exact"] = report["code_after"] == report["code_before"]
        rendered = [item["render"] for item in report["frames"] if "render" in item]
        report["success"] = report.get("diagnostic_completed", False) and not report["errors"] \
            and report.get("original_asset_protection", {}).get("success", False) and report["artist_disk_exact"] and report["code_exact"] \
            and (not args.render or len(rendered) == 1 and rendered[0]["success"])
        report["elapsed_seconds"] = time.perf_counter() - started
        conversions = []
        serializable = diag.json_content(report, conversions=conversions)
        serializable["json_mathutils_conversions"] = conversions
        path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print("EXPERIMENTAL_ACTUAL_SURFACE_REPORT=" + str(path), flush=True)
        print("EXPERIMENTAL_ACTUAL_SURFACE_COMPLETED=" + str(report["success"]), flush=True)
    return report


if __name__ == "__main__":
    result = main(arguments())
    if not result["success"]:
        raise RuntimeError("QA actual surface experiment incomplete; inspect its JSON")
