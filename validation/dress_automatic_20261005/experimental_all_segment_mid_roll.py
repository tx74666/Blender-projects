"""Unreleased QA: 32 Rest-midpoint native axis references and native roll locks.

Fresh factory background only; same 60-frame representative abrupt-stop input
and physical/Body/tracker graphs as the frozen actual-surface/Stretch experiment.
One new 32-vertex/no-edge/no-face Mesh, 32 sole-vertex groups, one Surface Deform;
one appended WORLD Locked Track (X about locked Y) on each exact saved PHYS bone.
No angle fitting, pose handlers, simulation-frame graph writes or rewinding.
Original, mode switching, partial physics/manual scale and production are unproved.
"""

import copy
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
FROZEN = {
    "experimental_actual_surface.py": "188fd43531133a42aa7c12cf689a3dcb0fc5e1bfbfb2bc2f9527f83fa6ce5bae",
    "experimental_stretch_transfer.py": "aa6dd7340dad26c612c178f7c7d7ef34d238dda2c72af1cb33a492e269b4758a",
    "experimental_one_segment_roll.py": "62bb0d74b7f67db6fba814a233272220ff5298a8ac734d30a26a9148cb8a73c9",
    "experimental_one_segment_mid_roll.py": "fc424e018cb3ef668cbc98545bf527e95c5fcd4c8e795c57dd6ba50e77a62b35",
}
for name, expected in FROZEN.items():
    if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != expected:
        raise RuntimeError("Frozen dependency differs: " + name)
sys.path.insert(0, str(HERE))
import experimental_one_segment_mid_roll as pilot

stretch, base, diag, qa, bodyqa, skirt = pilot.stretch, pilot.base, pilot.diag, pilot.qa, pilot.bodyqa, pilot.skirt
require, matrix_error, helper_content = base.require, pilot.matrix_error, pilot.helper_content
ORIGINAL_VERIFY, ORIGINAL_GRAPH, ORIGINAL_GUARD = pilot.ORIGINAL_VERIFY, pilot.ORIGINAL_GRAPH, pilot.ORIGINAL_GUARD
ORIGINAL_PROBE_TRANSFER, ORIGINAL_MEASURE = pilot.ORIGINAL_PROBE_TRANSFER, pilot.ORIGINAL_MEASURE
ORIGINAL_MANIFEST, ORIGINAL_MESH_SNAPSHOT = pilot.ORIGINAL_MANIFEST, pilot.ORIGINAL_MESH_SNAPSHOT
ALL = {"installed": False}
LOCK_NAME = "QA Midpoint Surface Roll"
SURFACE_NAME = "QA 32 Midpoint Surface Deform"


def bind_reference(reference, actual, cloth, rig, report):
    """Explicit 32-point extension of the frozen one-point neutral bind reader."""
    scene = bpy.context.scene
    frame, pose_position = scene.frame_current, rig.data.pose_position
    active, mode = bpy.context.view_layer.objects.active, bpy.context.mode
    flags, channels = (cloth.show_viewport, cloth.show_render), base.channels_hash(rig)
    raw_world = [reference.matrix_world @ vertex.co for vertex in reference.data.vertices]
    require(len(raw_world) == 32, "Bind exactly 32 saved midpoint reference points")
    try:
        skirt._activate(bpy.context, reference, "OBJECT")
        scene.frame_set(0)
        rig.data.pose_position = "REST"
        cloth.show_viewport = cloth.show_render = False
        bpy.context.view_layer.update()
        surface = reference.modifiers.new(SURFACE_NAME, "SURFACE_DEFORM")
        surface.target, surface.strength = actual, 1.
        result = bpy.ops.object.surfacedeform_bind(modifier=surface.name)
        bpy.context.view_layer.update()
        report.update(operator=sorted(result), is_bound=surface.is_bound, source_vertices=32, source_faces=0,
            target=actual.name, native_error_if_exposed=getattr(surface, "error", None), no_geometry_fallback=True)
        require("FINISHED" in result and surface.is_bound,
                "Native 32-point/no-face Surface Deform did not bind; refuse alternate source geometry")
        snapshot = ORIGINAL_MESH_SNAPSHOT(reference, bpy.context.evaluated_depsgraph_get())
        require(len(snapshot["points"]) == 32 and not snapshot["faces"] and not snapshot["edges"]
                and qa.finite(snapshot["points"]), "Reference evaluated topology or finite points changed")
        errors = [(a-b).length for a,b in zip(snapshot["points"], raw_world)]
        meters = scene.unit_settings.scale_length
        report.update(neutral_reference_errors_world=errors, neutral_reference_max_world=max(errors),
            neutral_reference_max_m=max(errors)*meters,
            maximum_allowed_world=base.BIND_WORLD_LIMIT, maximum_allowed_m=base.BIND_METRES_LIMIT)
        require(max(errors) <= base.BIND_WORLD_LIMIT and max(errors)*meters <= base.BIND_METRES_LIMIT,
                "Neutral binding displaced at least one Rest midpoint reference")
    finally:
        rig.data.pose_position = pose_position
        cloth.show_viewport, cloth.show_render = flags
        scene.frame_set(frame)
        if active is not None:
            skirt._activate(bpy.context, active, "POSE" if mode == "POSE" else "OBJECT")
        bpy.context.view_layer.update()
        report["restoration"] = {"frame": scene.frame_current, "pose_position": rig.data.pose_position,
            "cloth_flags": [cloth.show_viewport, cloth.show_render],
            "pose_action_channels_exact": base.channels_hash(rig) == channels,
            "active_object": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
            "mode": bpy.context.mode}
        require(scene.frame_current == frame and rig.data.pose_position == pose_position
                and (cloth.show_viewport, cloth.show_render) == flags and base.channels_hash(rig) == channels
                and bpy.context.view_layer.objects.active == active and bpy.context.mode == mode,
                "Neutral reference binding did not restore frame/Pose/Cloth/action channels exactly")
    return surface


def verify_reference():
    reference, actual, rig, surface = ALL["reference"], ALL["actual"], ALL["rig"], ALL["surface"]
    require(qa.digest(helper_content(reference)) == ALL["helper_hash"], "Exact independent 32-point helper changed")
    require(reference.data != actual.data and reference.data != ALL["source"].data and reference.data.shape_keys is None
            and reference.animation_data is None and reference.data.animation_data is None and not reference.constraints,
            "Reference must have independent static data and only native Surface Deform evaluation")
    require(reference.parent == rig and reference.parent_type == "OBJECT" and reference.parent_bone == "",
            "Reference may inherit only the Rig object transform, without bone feedback")
    require(len(reference.data.vertices) == len(reference.vertex_groups) == 32
            and not reference.data.edges and not reference.data.polygons, "Exact reference count/no-face topology changed")
    for row in ALL["rows"]:
        i = row["point_index"]
        group = reference.vertex_groups[i]
        assignments = list(reference.data.vertices[i].groups)
        require(group.index == i and group.name == row["group"] and len(assignments) == 1
                and assignments[0].group == i and assignments[0].weight == 1., "Reference sole-vertex group ownership changed")
    require(len(reference.modifiers) == 1 and reference.modifiers[0] == surface and surface.name == SURFACE_NAME
            and surface.type == "SURFACE_DEFORM" and surface.target == actual and surface.is_bound and surface.strength == 1.,
            "Exact one native Surface Deform helper contract changed")
    require(skirt.OWNER_KEY not in reference and skirt.OWNER_KEY not in reference.data
            and reference.name not in ALL["cloth"].collision_settings.collection.objects,
            "Reference borrowed a canonical UUID or entered the physical collision graph")
    require(matrix_error(reference.matrix_world.inverted() @ actual.matrix_world, ALL["relative"]) <= 1.e-6,
            "Reference/actual Cloth bind-relative object matrix changed")


def verify_locks():
    for row in ALL["rows"]:
        bone = ALL["rig"].pose.bones[row["names"]["phys"]]
        old = list(bone.constraints)[:2]
        lock = row["lock"]
        require(len(bone.constraints) == 3 and tuple(old) == row["old_constraints"] and bone.constraints[2] == lock
                and [c.name for c in old] == row["old_names"] and [c.type for c in old] == row["old_types"],
                "Each saved PHYS must retain both original constraints and append exactly its identified roll")
        require(lock.name == LOCK_NAME and lock.type == "LOCKED_TRACK" and lock.target == ALL["reference"]
                and lock.subtarget == row["group"] and lock.track_axis == "TRACK_X" and lock.lock_axis == "LOCK_Y"
                and lock.owner_space == lock.target_space == "WORLD" and lock.influence == 1.
                and not lock.mute and lock.enabled and not lock.active,
                "Exact enabled Locked Track target/axes/space/alias/activity proof failed")
        require(bodyqa.copied_parameters(lock) == row["lock_parameters"], "Added roll full native parameters changed")


def extended_verify(rig, rows):
    if not ALL["installed"]:
        return ORIGINAL_VERIFY(rig, rows)
    require(rig == ALL["rig"] and len(rows) == 32
            and [row["names"] for row in rows] == [row["names"] for row in ALL["rows"]],
            "Extended proof must cover all exact 32 saved Stretch verifier rows")
    verify_reference()
    verify_locks()
    for row in rows:
        aim, active_stretch, _roll = rig.pose.bones[row["names"]["phys"]].constraints
        deform = rig.pose.bones[row["names"]["def"]]
        # Frozen native Stretch/Scale predicates, explicitly extended PHYS 2 -> 3 on all 32.
        require(aim.name == "CD Physics Aim" and aim.type == "DAMPED_TRACK" and aim.mute and not aim.enabled,
                "Retained original aim differs")
        require(active_stretch.name == stretch.STRETCH_NAME and active_stretch.type == "STRETCH_TO"
                and not active_stretch.mute and active_stretch.enabled and not active_stretch.active
                and active_stretch.target == aim.target and active_stretch.subtarget == aim.subtarget
                and active_stretch.volume == "NO_VOLUME" and active_stretch.keep_axis == "SWING_Y"
                and active_stretch.owner_space == active_stretch.target_space == "WORLD" and active_stretch.influence == 1.
                and active_stretch.rest_length == row["rest_length_rig"] and active_stretch.rest_length > 0.,
                "Frozen native Stretch proof failed")
        require(len(deform.constraints) == 3, "Final DEF must retain the frozen exact three-constraint stack")
        scale = deform.constraints[2]
        require(scale.name == stretch.SCALE_NAME and scale.type == "COPY_SCALE"
                and not scale.mute and scale.enabled and not scale.active and scale.target == rig
                and scale.subtarget == row["names"]["phys"] and scale.owner_space == scale.target_space == "LOCAL"
                and scale.influence == 1. and scale.use_x and scale.use_y and scale.use_z
                and scale.use_offset and not scale.use_add and not scale.use_make_uniform and scale.power == 1.,
                "Frozen native local offset Scale proof failed")


def normalized_graph(rig):
    actual = ORIGINAL_GRAPH(rig)  # Original proof includes enabled == not mute on every constraint.
    if not ALL["installed"]:
        return actual
    verify_reference()
    verify_locks()
    expected = copy.deepcopy(ALL["graph_before"])
    for row in ALL["rows"]:
        expected[row["names"]["phys"]].append(row["lock_parameters"])
    require(actual == expected, "Graph escaped the exact 32 appended native-roll whitelist")
    normalized = copy.deepcopy(actual)
    for row in ALL["rows"]:
        normalized[row["names"]["phys"]].pop(2)
    require(normalized == ALL["graph_before"], "Identified 32-roll normalization failed to recover frozen Stretch graph")
    ALL["report"]["actual_graph"] = actual
    ALL["report"]["normalized_stretch_graph_exact"] = True
    return normalized


def combined_guard(rig, record, source):
    # Original guard still verifies ALL normalized graph, drivers, Rest, source, records and corrections.
    if ALL["installed"] and bpy.context.scene.frame_current == 60:
        require(len(ALL["reference_samples"]) == 60 and ALL["reference_seen_frames"] == set(range(1,61)),
                "All32 reference diagnostics must cover every forward frame before candidate save")
        ALL["report"]["complete_60_forward_frame_reference_diagnostics"] = True
    return ORIGINAL_GUARD(rig, record, source)


def native_bones(rig, evaluated, rows):
    return [{"chain": row["chain"], "segment": row["segment"], "names": row["names"],
        "phys": diag.bone_content(rig, evaluated, row["names"]["phys"]),
        "def": diag.bone_content(rig, evaluated, row["names"]["def"])} for row in rows]


def install_rolls(source, actual, collection, probe, report):
    rig, record, tracker = stretch.STATE["rig"], stretch.STATE["record"], stretch.STATE["tracker"]
    require(stretch.STATE["installed"] and bpy.context.scene.frame_current == 0,
            "Install all midpoint references only after proved Stretch and before frame 1")
    require(tracker.parent == rig and tracker.parent_type == "OBJECT" and tracker.parent_bone == "",
            "Tracker must use the proved Rig OBJECT parent, without pose-bone feedback")
    before, before_hash = ORIGINAL_GRAPH(rig), ORIGINAL_GUARD(rig, record, source)
    rows, points, definitions = [], [], []
    for i, old_row in enumerate(stretch.STATE["rows"]):
        row = {key: copy.deepcopy(old_row[key]) for key in ("chain", "segment", "names", "rest_length_rig")}
        ci, si, names = row["chain"], row["segment"], row["names"]
        require(all(names[layer] == record["chains"][ci][layer][si] for layer in ("manual", "phys", "def")),
                "Reference row differs from exact saved ownership")
        bone = rig.data.bones[names["phys"]]
        head, tail = rig.matrix_world @ bone.head_local, rig.matrix_world @ bone.tail_local
        x = (rig.matrix_world @ bone.matrix_local).to_3x3().col[0].normalized()
        length = (tail-head).length
        point = (head+tail)*.5 + x*(length*.25)
        row.update(point_index=i, group=f"QA Mid Axis {ci+1:02d}.{si+1:02d}", rest_world_length=length)
        points.append(tracker.matrix_world.inverted() @ point)
        definitions.append({"chain":ci, "segment":si, "names":names, "point_index":i, "group":row["group"],
            "rest_head_world":diag.vector(head), "rest_tail_world":diag.vector(tail), "rest_x_world":diag.vector(x),
            "rest_reference_world":diag.vector(point), "rest_world_length":length})
        rows.append(row)
    require(len(rows) == 32 and len({row["names"]["phys"] for row in rows}) == 32, "Require exact 32 unique owned PHYS bones")
    data, reference, added = None, None, []
    report.update(binding={}, graph_before=before, original_stretch_contract_sha256=before_hash, exact_reference_definitions=definitions,
        offset_fraction_of_rest_world_length=.25, reference_fraction_along_rest_segment=.5,
        diff_whitelist="Only 32 appended native Locked Track constraints, and one independent 32-point/no-face object/data, its sole-vertex groups and one Surface Deform. Original UI active flags preserved. Everything else exact.")
    try:
        data = bpy.data.meshes.new("QA 32 Midpoint Axis Reference")
        data.from_pydata([tuple(point) for point in points], [], [])
        data.update()
        reference = bpy.data.objects.new("QA 32 Midpoint Axis Reference", data)
        collection.objects.link(reference)
        reference.parent, reference.parent_type, reference.parent_bone = tracker.parent, tracker.parent_type, tracker.parent_bone
        reference.matrix_parent_inverse = tracker.matrix_parent_inverse.copy()
        reference.matrix_basis = tracker.matrix_basis.copy()
        reference.matrix_world = tracker.matrix_world.copy()
        reference.hide_render, reference.display_type = True, "WIRE"
        reference["CD_QA_AllMidRollReference"] = data["CD_QA_AllMidRollReference"] = True
        reference["CD_QA_Source"] = data["CD_QA_Source"] = source
        for row in rows:
            group = reference.vertex_groups.new(name=row["group"])
            require(group.index == row["point_index"], "Native group index no longer equals exact reference vertex index")
            group.add([row["point_index"]], 1., "REPLACE")
        require(matrix_error(reference.matrix_world, tracker.matrix_world) <= 1.e-7
                and matrix_error(reference.matrix_parent_inverse, tracker.matrix_parent_inverse) == 0.
                and matrix_error(reference.matrix_basis, tracker.matrix_basis) <= 1.e-7,
                "Reference object did not copy the proved tracker matrices")
        cloth = next(modifier for modifier in actual.modifiers if modifier.type == "CLOTH")
        require(reference.name not in cloth.collision_settings.collection.objects
                and skirt.OWNER_KEY not in reference and skirt.OWNER_KEY not in data,
                "Reference must not become a collider or reuse canonical ownership UUID")
        surface = bind_reference(reference, actual, cloth, rig, report["binding"])
        graph = bpy.context.evaluated_depsgraph_get()
        evaluated = rig.evaluated_get(graph)
        matrices_before = {row["names"][layer]: evaluated.matrix_world @ evaluated.pose.bones[row["names"][layer]].matrix
                           for row in rows for layer in ("phys", "def")}
        native_before, skin_before = native_bones(rig, evaluated, rows), ORIGINAL_MESH_SNAPSHOT(probe, graph)["points"]
        require(len(skin_before) == 800, "Neutral no-jump measurement requires exact raw 800 skin vertices")
        for row in rows:
            phys = rig.pose.bones[row["names"]["phys"]]
            row.update(old_constraints=tuple(phys.constraints), old_names=[c.name for c in phys.constraints], old_types=[c.type for c in phys.constraints])
            require(len(row["old_constraints"]) == 2, "Each PHYS must begin with the frozen two-constraint stack")
            lock = phys.constraints.new("LOCKED_TRACK")
            added.append((phys, lock))
            lock.name, lock.target, lock.subtarget = LOCK_NAME, reference, row["group"]
            lock.track_axis, lock.lock_axis = "TRACK_X", "LOCK_Y"
            lock.owner_space = lock.target_space = "WORLD"
            lock.influence = 1.
            row["lock"] = lock
        stretch.restore_original_active(rig, before, added)
        bpy.context.view_layer.update()
        expected = copy.deepcopy(before)
        for row in rows:
            row["lock_parameters"] = bodyqa.copied_parameters(row["lock"])
            expected[row["names"]["phys"]].append(row["lock_parameters"])
        after = ORIGINAL_GRAPH(rig)
        report.update(actual_graph=after, graph_whitelist_expected=expected,
            exact_allowed_additions=[{"phys":row["names"]["phys"], "group":row["group"], "parameters":row["lock_parameters"]} for row in rows],
            whitelist_differences=stretch.field_differences(expected, after))
        require(after == expected, "All-segment roll changed non-whitelisted native constraint fields")
        graph = bpy.context.evaluated_depsgraph_get()
        evaluated = rig.evaluated_get(graph)
        pose_errors = {name:matrix_error(matrix, evaluated.matrix_world @ evaluated.pose.bones[name].matrix)
                       for name,matrix in matrices_before.items()}
        skin_after = ORIGINAL_MESH_SNAPSHOT(probe, graph)["points"]
        require(len(skin_after) == len(skin_before) == 800, "Roll changed neutral raw skin vertex count")
        skin_error = max((a-b).length for a,b in zip(skin_before, skin_after))
        meters = bpy.context.scene.unit_settings.scale_length
        report["neutral_current_input_no_jump"] = {"all64_world_matrix_component_errors":pose_errors,
            "world_matrix_max_component_delta":max(pose_errors.values()), "native_bones_before":native_before,
            "native_bones_after":native_bones(rig, evaluated, rows), "skin800_max_world_delta":skin_error,
            "skin800_max_m_delta":skin_error*meters, "matrix_limit":5.e-5,
            "skin_world_limit":base.BIND_WORLD_LIMIT, "skin_m_limit":base.BIND_METRES_LIMIT}
        require(max(pose_errors.values()) <= 5.e-5 and skin_error <= base.BIND_WORLD_LIMIT and skin_error*meters <= base.BIND_METRES_LIMIT,
                "At least one midpoint roll introduces a neutral pose/skin jump; refuse calibrated roll offsets")
        ALL.update(installed=True, rig=rig, source=source, record=record, tracker=tracker, actual=actual,
            cloth=cloth, reference=reference, surface=surface, rows=rows, graph_before=before,
            relative=reference.matrix_world.inverted() @ actual.matrix_world, helper_hash=qa.digest(helper_content(reference)),
            report=report, reference_samples=[], reference_seen_frames=set(), reference_previous={})
        combined_guard(rig, record, source)
        report["helper_contract"], report["helper_contract_sha256"] = helper_content(reference), ALL["helper_hash"]
        report["reference_direction_each_forward_frame"] = ALL["reference_samples"]
        report["dynamic_before_after_method"] = "Read-only all32 reference projection each forward frame; no simulated-frame constraint toggles. Compare four-frame native matrices/head/Y/length/tails, local scale/shear and exact physical/tracker arrays with the frozen same-input baseline."
        bpy.context.scene["CD_QA_AllMidpointRoll"] = json.dumps({"unreleased":True, "reference":reference.name,
            "exact_owned_phys_bones":[row["names"]["phys"] for row in rows], "additional_roll_count":32,
            "Original_mode_switching_partial_physics_manual_scale_production_unproved":True})
    except Exception:
        ALL["installed"] = False
        for phys,lock in reversed(added):
            phys.constraints.remove(lock)
        stretch.restore_original_active(rig, before)
        if reference is not None:
            bpy.data.objects.remove(reference, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
        report["rollback_graph"] = ORIGINAL_GRAPH(rig)
        report["rollback_differences"] = stretch.field_differences(before, report["rollback_graph"])
        require(report["rollback_graph"] == before and ORIGINAL_GUARD(rig, record, source) == before_hash,
                "All-midpoint roll rollback did not restore the exact frozen Stretch graph/drivers/contract")
        raise


def probe_then_roll(source, actual, collection, report):
    probe = ORIGINAL_PROBE_TRANSFER(source, actual, collection, report)
    try:
        report["all_segment_mid_roll"] = {}
        install_rolls(source, actual, collection, probe, report["all_segment_mid_roll"])
    except Exception:
        base.remove_skin_probe(probe, source, report)
        raise
    return probe


def reference_directions(graph, frame):
    """Pure native evaluation reads on the 60 forward frames; no graph/cache writes."""
    snapshot = ORIGINAL_MESH_SNAPSHOT(ALL["reference"], graph)
    require(len(snapshot["points"]) == 32 and qa.finite(snapshot["points"]), "Exact 32 reference points became nonfinite")
    evaluated = ALL["rig"].evaluated_get(graph)
    sample = {"frame":frame, "segments":[],
        "continuity_definition":"Consecutive radial vectors after minimum rotation transporting prior native Y to current Y; negative dot marks >90-degree change, near-antiparallel Y is ambiguous. Diagnostic only; no material/pleat correspondence proof."}
    ALL["reference_samples"].append(sample)
    for row in ALL["rows"]:
        names, i = row["names"], row["point_index"]
        bone = evaluated.pose.bones[names["phys"]]
        world = evaluated.matrix_world @ bone.matrix
        head, tail = evaluated.matrix_world @ bone.head, evaluated.matrix_world @ bone.tail
        y = world.to_3x3().col[1].normalized()
        toward = snapshot["points"][i]-head
        projection = toward-y*toward.dot(y)
        limit = max(1.e-10, row["rest_world_length"]*1.e-8)
        item = {"chain":row["chain"], "segment":row["segment"], "phys":names["phys"], "point_index":i,
            "reference_world":diag.vector(snapshot["points"][i]), "phys_head_world":diag.vector(head),
            "phys_axis_y_world":diag.vector(y), "phys_axis_y_column_length_world":world.to_3x3().col[1].length,
            "phys_head_tail_world_length":(tail-head).length, "phys_world_normalized_shear":stretch.local_shear(world),
            "reference_to_head_y_projection_world_length":projection.length,
            "degeneracy_limit_world":limit, "projection_degenerate":projection.length <= limit}
        sample["segments"].append(item)
        require(qa.finite([head,tail,y,projection]) and y.length > .5 and projection.length > limit,
                "Midpoint axis-reference projects degenerately onto a native Y-perpendicular plane")
        radial = projection.normalized()
        item["native_x_to_reference_projection_cosine"] = world.to_3x3().col[0].normalized().dot(radial)
        previous = ALL["reference_previous"].get(i)
        if previous is not None:
            prior_y, prior_radial = previous
            near_antiparallel = prior_y.dot(y) < -1.+1.e-7
            transported = prior_y.rotation_difference(y) @ prior_radial
            cosine = max(-1., min(1., transported.dot(radial)))
            item.update(previous_y_near_antiparallel=near_antiparallel, transported_reference_cosine=cosine,
                transported_reference_signed_angle_rad=math.atan2(y.dot(transported.cross(radial)), cosine),
                greater_than_90_degree_reference_flip_diagnostic=cosine < 0., continuity_ambiguous_due_antiparallel_y=near_antiparallel)
        ALL["reference_previous"][i] = (y.copy(), radial.copy())
    return sample


def observed_mesh_snapshot(obj, graph):
    snapshot = ORIGINAL_MESH_SNAPSHOT(obj, graph)
    frame = bpy.context.scene.frame_current
    if ALL["installed"] and obj == ALL["tracker"] and 1 <= frame <= 60 and frame not in ALL["reference_seen_frames"]:
        reference_directions(graph, frame)
        ALL["reference_seen_frames"].add(frame)
    return snapshot


def measured_roll(cli, source, rig, tracker, actual, cloth, record, body, clone, probe, frame):
    item = ORIGINAL_MEASURE(cli, source, rig, tracker, actual, cloth, record, body, clone, probe, frame)
    require(ALL["installed"], "All midpoint references must be installed before measurement")
    graph = bpy.context.evaluated_depsgraph_get()
    reference = ORIGINAL_MESH_SNAPSHOT(ALL["reference"], graph)
    targets = []
    for row in ALL["rows"]:
        target = diag.weighted_target(ALL["reference"], reference, row["group"])
        require(target["available"] and target["single_native_target_vertex"] == row["point_index"]
                and target["group_index"] == row["point_index"] and target["weight_sum"] == 1.,
                "Each native roll must target its exact sole reference vertex, without guessed correspondences")
        targets.append({"phys":row["names"]["phys"], "exact_native_target":target})
    skin = ORIGINAL_MESH_SNAPSHOT(probe, graph)
    require(len(skin["points"]) == 800 and qa.finite(skin["points"]), "Exact raw source skin800 changed or became nonfinite")
    item["raw_skin800_world"] = [diag.vector(point) for point in skin["points"]]
    item["all_segment_mid_roll"] = {"exact_added_constraint_count":32, "reference_targets":targets,
        "native_bones":native_bones(rig, rig.evaluated_get(graph), ALL["rows"]),
        "reference_projection":next(sample for sample in ALL["reference_samples"] if sample["frame"] == frame),
        "all32_helper_and_added_constraints_exact":True, "frozen_other_graph_drivers_Rest_source_records_exact":True,
        "limitation":"Off-surface native references can bind a neighboring pleat. Per-segment rigid roll and interpolated 32-bone skin cannot reproduce arbitrary Cloth deformation or FULL-parent local shear; diagnostic only."}
    return item


def manifest():
    values = ORIGINAL_MANIFEST()
    for name in ("experimental_one_segment_roll.py", "experimental_one_segment_mid_roll.py"):
        values[str(HERE/name)] = qa.file_state(HERE/name)
    values[str(Path(__file__).resolve())] = qa.file_state(Path(__file__).resolve())
    return values


def main():
    require(not stretch.PREFLIGHT_ONLY, "All-midpoint experiment requires the same full 60 forward frames")
    stretch.graph_content, stretch.verify_active_constraints = normalized_graph, extended_verify
    stretch.guarded_contract, stretch.probe_then_transfer = combined_guard, probe_then_roll
    stretch.measured_transfer, stretch.experiment_manifest = measured_roll, manifest
    diag.mesh_snapshot = observed_mesh_snapshot
    result = stretch.main()
    result["purpose"] = "Unreleased all32 Rest-midpoint native axis-reference roll over frozen actual-surface/Stretch comparison"
    result["frozen_roll_dependencies"] = FROZEN
    result["exact_roll_count"] = 32
    result["production_effect_accepted"] = result["canonical_full_graph_pass"] = False
    result["Original_mode_switching_partial_physics_manual_scale_supported"] = False
    result["limitations"].append("All32 off-surface references remain experimental. Original switching, partial physics/manual scaling, arbitrary artist constraints, persistent bake/production acceptance are unproved. No angle fitting or pose/cache handlers are added.")
    output = Path(sys.argv[sys.argv.index("--output")+1]).resolve()/"experimental_actual_surface.json"
    conversions = []
    serializable = diag.json_content(result, conversions=conversions)
    serializable["json_mathutils_conversions"] = conversions
    output.write_text(json.dumps(serializable, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("EXPERIMENTAL_ALL_SEGMENT_MID_ROLL_REPORT="+str(output), flush=True)
    return result


if __name__ == "__main__":
    main()
