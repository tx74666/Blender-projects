"""Unreleased QA: one native Surface Deform axis reference and one roll constraint.

Same fresh factory background entry as the frozen actual-surface/Stretch tests:
 --background --factory-startup --disable-autoexec --threads 1 --python <file>
 -- --output <fresh Validation result folder> --render
Only saved exact chain 2/segment 3 (PHYS_03_04/DEF_03_04) is tested. One owned
one-vertex/no-face helper, its own vertex group and one native Surface Deform;
one appended LOCKED_TRACK(TRACK_X, LOCK_Y) after the existing native Stretch.
No adjustable/hardcoded roll angle. Off-surface reference transfer is unproved;
this pilot cannot represent the observed variation of roll within one segment.
"""

import copy
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
FROZEN = {"experimental_actual_surface.py": "188fd43531133a42aa7c12cf689a3dcb0fc5e1bfbfb2bc2f9527f83fa6ce5bae",
          "experimental_stretch_transfer.py": "aa6dd7340dad26c612c178f7c7d7ef34d238dda2c72af1cb33a492e269b4758a"}
for name, expected in FROZEN.items():
    if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != expected:
        raise RuntimeError("Frozen dependency differs: " + name)
sys.path.insert(0, str(HERE))
import experimental_stretch_transfer as stretch

base, diag, qa, bodyqa, skirt = stretch.base, stretch.diag, stretch.qa, stretch.bodyqa, stretch.skirt
require = base.require
ORIGINAL_VERIFY = stretch.verify_active_constraints
ORIGINAL_GRAPH = stretch.graph_content
ORIGINAL_GUARD = stretch.guarded_contract
ORIGINAL_PROBE_TRANSFER = stretch.probe_then_transfer
ORIGINAL_MEASURE = stretch.measured_transfer
ORIGINAL_MANIFEST = stretch.experiment_manifest
ORIGINAL_MESH_SNAPSHOT = diag.mesh_snapshot
ROLL = {"installed": False}
GROUP = "QA One Segment Axis Reference"
LOCK_NAME = "QA One Segment Surface Roll"


def matrix_error(a, b):
    return max(abs(x-y) for ra, rb in zip(a, b) for x, y in zip(ra, rb))


def helper_content(reference):
    return {"object": reference.name, "mesh": reference.data.name,
        "coordinates": [list(vertex.co) for vertex in reference.data.vertices],
        "edges": [list(edge.vertices) for edge in reference.data.edges],
        "faces": [list(face.vertices) for face in reference.data.polygons],
        "groups": [(group.index, group.name) for group in reference.vertex_groups],
        "weights": [[(item.group, item.weight) for item in vertex.groups] for vertex in reference.data.vertices],
        "parent": reference.parent.name if reference.parent else None, "parent_type": reference.parent_type,
        "parent_bone": reference.parent_bone, "parent_inverse": diag.matrix(reference.matrix_parent_inverse),
        "basis": diag.matrix(reference.matrix_basis), "constraints": [bodyqa.copied_parameters(c) for c in reference.constraints],
        "modifiers": [bodyqa.copied_parameters(m) for m in reference.modifiers],
        "object_properties": qa.custom_content({key: reference[key] for key in reference.keys()}),
        "mesh_properties": qa.custom_content({key: reference.data[key] for key in reference.data.keys()})}


def bind_reference(reference, actual, cloth, rig, report):
    scene = bpy.context.scene
    frame, pose_position = scene.frame_current, rig.data.pose_position
    active, mode = bpy.context.view_layer.objects.active, bpy.context.mode
    old_flags = (cloth.show_viewport, cloth.show_render)
    channels = base.channels_hash(rig)
    raw_world = reference.matrix_world @ reference.data.vertices[0].co
    try:
        skirt._activate(bpy.context, reference, "OBJECT")
        scene.frame_set(0)
        rig.data.pose_position = "REST"
        cloth.show_viewport = cloth.show_render = False
        bpy.context.view_layer.update()
        surface = reference.modifiers.new("QA One Vertex Surface Deform", "SURFACE_DEFORM")
        surface.target, surface.strength = actual, 1.
        result = bpy.ops.object.surfacedeform_bind(modifier=surface.name)
        bpy.context.view_layer.update()
        report.update(operator=sorted(result), is_bound=surface.is_bound,
            source_vertices=1, source_faces=0, target=actual.name,
            native_error_if_exposed=getattr(surface, "error", None),
            no_source_faces_fallback_or_topology_replacement=True)
        require("FINISHED" in result and surface.is_bound,
                "Native Surface Deform did not support this one-vertex/no-face source; stop without alternate geometry")
        snapshot = diag.mesh_snapshot(reference, bpy.context.evaluated_depsgraph_get())
        require(len(snapshot["points"]) == 1 and not snapshot["faces"] and not snapshot["edges"]
                and qa.finite(snapshot["points"]), "Native reference evaluation changed its exact point topology")
        error = (snapshot["points"][0]-raw_world).length
        meters = scene.unit_settings.scale_length
        report.update(neutral_reference_max_world=error, neutral_reference_max_m=error*meters,
            maximum_allowed_world=base.BIND_WORLD_LIMIT, maximum_allowed_m=base.BIND_METRES_LIMIT)
        require(error <= base.BIND_WORLD_LIMIT and error*meters <= base.BIND_METRES_LIMIT,
                "Neutral native reference binding moved the rest point")
    finally:
        rig.data.pose_position = pose_position
        cloth.show_viewport, cloth.show_render = old_flags
        scene.frame_set(frame)
        if active is not None:
            skirt._activate(bpy.context, active, "POSE" if mode == "POSE" else "OBJECT")
        bpy.context.view_layer.update()
        report["restoration"] = {"frame": scene.frame_current, "pose_position": rig.data.pose_position,
            "cloth_flags": [cloth.show_viewport, cloth.show_render], "pose_action_channels_exact": base.channels_hash(rig) == channels,
            "active_object": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
            "mode": bpy.context.mode}
        require(scene.frame_current == frame and rig.data.pose_position == pose_position
                and (cloth.show_viewport, cloth.show_render) == old_flags and base.channels_hash(rig) == channels,
                "Reference binding did not restore frame/Pose/Cloth/action channels exactly")
    return surface


def verify_pilot():
    rig, reference, actual = ROLL["rig"], ROLL["reference"], ROLL["actual"]
    require(qa.digest(helper_content(reference)) == ROLL["helper_hash"], "New reference/helper contract changed")
    require(reference.data != actual.data and reference.data.shape_keys is None and reference.animation_data is None
            and reference.data.animation_data is None and not reference.constraints,
            "Reference must be independent, static input except its native Surface Deform")
    require(reference.parent == rig and reference.parent_type == "OBJECT" and reference.parent_bone == "",
            "Reference may inherit the Rig object transform only, never a pose-bone transform")
    require(len(reference.modifiers) == 1 and reference.modifiers[0] == ROLL["surface"]
            and ROLL["surface"].type == "SURFACE_DEFORM" and ROLL["surface"].target == actual
            and ROLL["surface"].is_bound and ROLL["surface"].strength == 1., "Exact bound one-point Surface Deform changed")
    relative = reference.matrix_world.inverted() @ actual.matrix_world
    require(matrix_error(relative, ROLL["relative"]) <= 1.e-6, "Reference/target bind-relative object transform changed")
    bone = rig.pose.bones[ROLL["phys"]]
    original_constraints = list(bone.constraints)[:2]
    require(len(bone.constraints) == 3 and tuple(original_constraints) == ROLL["old_constraints"]
            and bone.constraints[2] == ROLL["lock"], "Only one appended constraint on the exact pilot is allowed")
    lock = ROLL["lock"]
    require(lock.name == LOCK_NAME and lock.type == "LOCKED_TRACK" and lock.target == reference and lock.subtarget == GROUP
            and lock.track_axis == "TRACK_X" and lock.lock_axis == "LOCK_Y"
            and lock.owner_space == lock.target_space == "WORLD" and lock.influence == 1.
            and not lock.mute and lock.enabled and not lock.active,
            "Exact enabled pilot Locked Track contract failed")
    require(bodyqa.copied_parameters(lock) == ROLL["lock_parameters"], "New Locked Track full native parameters changed")
    require([c.name for c in original_constraints] == ROLL["old_names"]
            and [c.type for c in original_constraints] == ROLL["old_types"], "Pilot original constraint identity/type/name changed")


def extended_verify(rig, rows):
    if not ROLL["installed"]:
        return ORIGINAL_VERIFY(rig, rows)
    verify_pilot()
    others = [row for row in rows if row["names"]["phys"] != ROLL["phys"]]
    require(len(others) == 31, "Exactly one of the original 32 verifier rows may use the explicit extension")
    ORIGINAL_VERIFY(rig, others)
    row = next(row for row in rows if row["names"]["phys"] == ROLL["phys"])
    aim, active_stretch, _roll = rig.pose.bones[row["names"]["phys"]].constraints
    scale = rig.pose.bones[row["names"]["def"]].constraints[2]
    # Original frozen verifier predicates, explicitly extended only from 2 to 3 PHYS items.
    require(aim.name == "CD Physics Aim" and aim.type == "DAMPED_TRACK" and aim.mute and not aim.enabled,
            "Pilot original retained aim differs")
    require(active_stretch.name == stretch.STRETCH_NAME and active_stretch.type == "STRETCH_TO"
            and not active_stretch.mute and active_stretch.enabled and not active_stretch.active
            and active_stretch.target == aim.target and active_stretch.subtarget == aim.subtarget
            and active_stretch.volume == "NO_VOLUME" and active_stretch.keep_axis == "SWING_Y"
            and active_stretch.owner_space == active_stretch.target_space == "WORLD" and active_stretch.influence == 1.
            and active_stretch.rest_length == row["rest_length_rig"] and active_stretch.rest_length > 0.,
            "Pilot frozen active Stretch proof failed")
    require(len(rig.pose.bones[row["names"]["def"]].constraints) == 3 and scale.name == stretch.SCALE_NAME
            and scale.type == "COPY_SCALE" and not scale.mute and scale.enabled and not scale.active
            and scale.target == rig and scale.subtarget == row["names"]["phys"]
            and scale.owner_space == scale.target_space == "LOCAL" and scale.influence == 1.
            and scale.use_x and scale.use_y and scale.use_z and scale.use_offset and not scale.use_add
            and not scale.use_make_uniform and scale.power == 1., "Pilot frozen DEF scale proof failed")


def normalized_graph(rig):
    actual = ORIGINAL_GRAPH(rig)
    if not ROLL["installed"]:
        return actual
    verify_pilot()
    expected = copy.deepcopy(ROLL["graph_before"])
    expected[ROLL["phys"]].append(ROLL["lock_parameters"])
    require(actual == expected, "Roll graph escaped its one exact appended-constraint whitelist")
    normalized = copy.deepcopy(actual)
    normalized[ROLL["phys"]].pop(2)
    require(normalized == ROLL["graph_before"], "Identified pilot normalization does not recover the exact frozen Stretch graph")
    ROLL["report"]["actual_graph"] = actual
    ROLL["report"]["normalized_stretch_graph_exact"] = True
    return normalized


def combined_guard(rig, record, source):
    if ROLL["installed"]:
        verify_pilot()
    # Frozen guard still checks normalized ALL constraints, drivers, Rest, skin, records and corrections.
    return ORIGINAL_GUARD(rig, record, source)


def install_roll(source, actual, collection, probe, report):
    rig, record, tracker = stretch.STATE["rig"], stretch.STATE["record"], stretch.STATE["tracker"]
    require(stretch.STATE["installed"] and bpy.context.scene.frame_current == 0, "Install roll only after proved Stretch and before frame 1")
    names = {layer: record["chains"][2][layer][3] for layer in ("manual", "phys", "def")}
    require(names["phys"] == "SK_Dress_PHYS_03_04" and names["def"] == "SK_Dress_DEF_03_04", "Saved exact pilot identity differs")
    before = ORIGINAL_GRAPH(rig)
    before_hash = ORIGINAL_GUARD(rig, record, source)
    require(tracker.parent == rig and tracker.parent_type == "OBJECT" and tracker.parent_bone == "",
            "Frozen tracker must use the proved Rig OBJECT parent, without bone feedback")
    bone = rig.data.bones[names["phys"]]
    head_world, tail_world = rig.matrix_world @ bone.head_local, rig.matrix_world @ bone.tail_local
    x_world = (rig.matrix_world @ bone.matrix_local).to_3x3().col[0].normalized()
    point_world = head_world + x_world * ((tail_world-head_world).length * .25)
    local = tracker.matrix_world.inverted() @ point_world
    data, reference, lock = None, None, None
    try:
        data = bpy.data.meshes.new("QA One Segment Axis Reference")
        data.from_pydata([tuple(local)], [], [])
        data.update()
        reference = bpy.data.objects.new("QA One Segment Axis Reference", data)
        collection.objects.link(reference)
        reference.parent, reference.parent_type, reference.parent_bone = tracker.parent, tracker.parent_type, tracker.parent_bone
        reference.matrix_parent_inverse = tracker.matrix_parent_inverse.copy()
        reference.matrix_basis = tracker.matrix_basis.copy()
        reference.matrix_world = tracker.matrix_world.copy()
        reference.hide_render, reference.display_type = True, "WIRE"
        reference["CD_QA_RollReference"] = data["CD_QA_RollReference"] = True
        reference["CD_QA_Source"] = data["CD_QA_Source"] = source
        reference["CD_QA_PhysicalBone"] = names["phys"]
        group = reference.vertex_groups.new(name=GROUP)
        group.add([0], 1., "REPLACE")
        require(matrix_error(reference.matrix_world, tracker.matrix_world) <= 1.e-7
                and reference.parent == tracker.parent and reference.parent_type == tracker.parent_type
                and reference.parent_bone == tracker.parent_bone
                and matrix_error(reference.matrix_parent_inverse, tracker.matrix_parent_inverse) == 0.,
                "Reference did not copy the proved tracker parent/matrix contract")
        cloth = next(m for m in actual.modifiers if m.type == "CLOTH")
        require(skirt.OWNER_KEY not in reference and skirt.OWNER_KEY not in data
                and reference.name not in cloth.collision_settings.collection.objects,
                "Reference must not borrow canonical UUID or become a collision/feedback object")
        report.update(pilot=names, rest_head_world=diag.vector(head_world), rest_x_world=diag.vector(x_world),
            rest_reference_world=diag.vector(point_world), offset_fraction_of_rest_length=.25,
            binding={}, graph_before=before, original_stretch_contract_sha256=before_hash,
            added_ids={"object": reference.name, "mesh": data.name, "vertex_group": GROUP},
            definition="Fresh one-vertex/no-face Mesh; exact tracker parent/type/bone/inverse/basis/world transform, no copied UUID/modifiers/groups. Point is rest bone head plus rest world X times one quarter rest world length.")
        surface = bind_reference(reference, actual, cloth, rig, report["binding"])
        graph = bpy.context.evaluated_depsgraph_get()
        evaluated = rig.evaluated_get(graph)
        matrices_before = {layer: evaluated.matrix_world @ evaluated.pose.bones[names[layer]].matrix for layer in ("phys", "def")}
        native_before = {layer: diag.bone_content(rig, evaluated, names[layer]) for layer in ("phys", "def")}
        skin_before = diag.mesh_snapshot(probe, graph)["points"]
        phys = rig.pose.bones[names["phys"]]
        old_constraints, old_names, old_types = tuple(phys.constraints), [c.name for c in phys.constraints], [c.type for c in phys.constraints]
        require(len(old_constraints) == 2, "Pilot must begin with the exact frozen two-constraint PHYS stack")
        lock = phys.constraints.new("LOCKED_TRACK")
        lock.name, lock.target, lock.subtarget = LOCK_NAME, reference, GROUP
        lock.track_axis, lock.lock_axis = "TRACK_X", "LOCK_Y"
        lock.owner_space = lock.target_space = "WORLD"
        lock.influence = 1.
        stretch.restore_original_active(rig, before, [(phys, lock)])
        bpy.context.view_layer.update()
        after = ORIGINAL_GRAPH(rig)
        parameters = bodyqa.copied_parameters(lock)
        expected = copy.deepcopy(before)
        expected[names["phys"]].append(parameters)
        report.update(actual_graph=after, exact_allowed_constraint_addition=parameters,
            whitelist_differences=stretch.field_differences(expected, after))
        require(after == expected, "One-segment roll changed other frozen constraint fields")
        graph = bpy.context.evaluated_depsgraph_get()
        evaluated = rig.evaluated_get(graph)
        pose_delta = max(matrix_error(matrices_before[layer], evaluated.matrix_world @ evaluated.pose.bones[names[layer]].matrix)
                         for layer in ("phys", "def"))
        skin_after = diag.mesh_snapshot(probe, graph)["points"]
        skin_delta = max((a-b).length for a,b in zip(skin_before, skin_after))
        meters = bpy.context.scene.unit_settings.scale_length
        report["neutral_current_input_no_jump"] = {"pilot_world_matrix_max_component_delta": pose_delta,
            "skin800_max_world_delta": skin_delta, "skin800_max_m_delta": skin_delta*meters,
            "matrix_limit": 5.e-5, "skin_world_limit": base.BIND_WORLD_LIMIT, "skin_m_limit": base.BIND_METRES_LIMIT,
            "native_bones_before": native_before,
            "native_bones_after": {layer: diag.bone_content(rig, evaluated, names[layer]) for layer in ("phys", "def")},
            "world_normalized_shear_before": {layer: stretch.local_shear(matrices_before[layer]) for layer in ("phys", "def")},
            "world_normalized_shear_after": {layer: stretch.local_shear(evaluated.matrix_world @ evaluated.pose.bones[names[layer]].matrix) for layer in ("phys", "def")}}
        require(pose_delta <= 5.e-5 and skin_delta <= base.BIND_WORLD_LIMIT and skin_delta*meters <= base.BIND_METRES_LIMIT,
                "Rest-bound reference introduces a frame-0 pose/skin jump; stop without calibrated roll offset")
        ROLL.update(installed=True, rig=rig, source=source, record=record, tracker=tracker, actual=actual,
            reference=reference, surface=surface, lock=lock, phys=names["phys"], names=names,
            old_constraints=old_constraints, old_names=old_names, old_types=old_types,
            graph_before=before, lock_parameters=parameters, relative=reference.matrix_world.inverted() @ actual.matrix_world,
            helper_hash=qa.digest(helper_content(reference)), report=report, rest_world_length=(tail_world-head_world).length,
            reference_samples=[], reference_seen_frames=set(), reference_previous=None)
        combined_guard(rig, record, source)
        report["helper_contract"] = helper_content(reference)
        report["helper_contract_sha256"] = ROLL["helper_hash"]
        report["reference_direction_each_forward_frame"] = ROLL["reference_samples"]
        report["dynamic_before_after_method"] = "No simulated-frame constraint toggles or graph writes. Compare the reported four-frame native head/Y/length/tail, local-scale/shear and exact physical/tracker arrays against the frozen same-input Stretch-only job; reference projection is sampled read-only on all 60 forward frames."
        bpy.context.scene["CD_QA_OneSegmentRoll"] = json.dumps({"unreleased": True, "physical_bone": names["phys"],
            "helper": reference.name, "allowed_additions": "one independent point Mesh/Object/group/Surface Deform and one exact Locked Track only",
            "off_surface_roll_transfer_not_production_proved": True})
    except Exception:
        ROLL["installed"] = False
        if lock is not None:
            rig.pose.bones[names["phys"]].constraints.remove(lock)
        stretch.restore_original_active(rig, before)
        if reference is not None:
            bpy.data.objects.remove(reference, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
        report["rollback_graph"] = ORIGINAL_GRAPH(rig)
        report["rollback_differences"] = stretch.field_differences(before, report["rollback_graph"])
        require(report["rollback_graph"] == before and ORIGINAL_GUARD(rig, record, source) == before_hash,
                "One-segment roll rollback did not recover the exact frozen Stretch state")
        raise


def probe_then_roll(source, actual, collection, report):
    probe = ORIGINAL_PROBE_TRANSFER(source, actual, collection, report)
    try:
        report["one_segment_roll"] = {}
        install_roll(source, actual, collection, probe, report["one_segment_roll"])
    except Exception:
        base.remove_skin_probe(probe, source, report)
        raise
    return probe


def reference_direction(graph, frame):
    """Pure evaluation reads; no mute toggles, pose writes or point-cache mutations."""
    rig, reference = ROLL["rig"], ROLL["reference"]
    snapshot = ORIGINAL_MESH_SNAPSHOT(reference, graph)
    require(len(snapshot["points"]) == 1 and qa.finite(snapshot["points"]), "Exact one-point reference became nonfinite")
    evaluated = rig.evaluated_get(graph)
    bone = evaluated.pose.bones[ROLL["phys"]]
    world = evaluated.matrix_world @ bone.matrix
    head, tail = evaluated.matrix_world @ bone.head, evaluated.matrix_world @ bone.tail
    y = world.to_3x3().col[1].normalized()
    toward = snapshot["points"][0]-head
    projection = toward-y*toward.dot(y)
    limit = max(1.e-10, ROLL["rest_world_length"]*1.e-8)
    row = {"frame": frame, "reference_world": diag.vector(snapshot["points"][0]), "phys_head_world": diag.vector(head),
        "phys_axis_y_world": diag.vector(y), "phys_axis_y_column_length_world": world.to_3x3().col[1].length,
        "phys_head_tail_world_length": (tail-head).length, "phys_world_normalized_shear": stretch.local_shear(world),
        "reference_to_head_y_projection_world_length": projection.length,
        "degeneracy_limit_world": limit, "projection_degenerate": projection.length <= limit,
        "continuity_definition": "Consecutive reference radial vectors after the minimum rotation transporting the preceding native Y to the current Y. A negative dot marks a greater-than-90-degree direction change; near-antiparallel Y is separately marked. This is a diagnostic and cannot establish material/pleat correspondence."}
    ROLL["reference_samples"].append(row)
    require(qa.finite([head, tail, y, projection]) and y.length > .5 and projection.length > limit,
            "Axis-reference direction projects degenerately onto the native Y-perpendicular plane; refusing unproved roll")
    radial = projection.normalized()
    x = world.to_3x3().col[0].normalized()
    previous = ROLL["reference_previous"]
    row["native_x_to_reference_projection_cosine"] = x.dot(radial)
    if previous is not None:
        prior_y, prior_radial = previous
        near_antiparallel = prior_y.dot(y) < -1.+1.e-7
        transported = prior_y.rotation_difference(y) @ prior_radial
        cosine = max(-1., min(1., transported.dot(radial)))
        row.update(previous_y_near_antiparallel=near_antiparallel,
            transported_reference_cosine=cosine,
            transported_reference_signed_angle_rad=math.atan2(y.dot(transported.cross(radial)), cosine),
            greater_than_90_degree_reference_flip_diagnostic=cosine < 0.,
            continuity_ambiguous_due_antiparallel_y=near_antiparallel)
    ROLL["reference_previous"] = (y.copy(), radial.copy())
    return row


def observed_mesh_snapshot(obj, graph):
    snapshot = ORIGINAL_MESH_SNAPSHOT(obj, graph)
    frame = bpy.context.scene.frame_current
    if ROLL["installed"] and obj == ROLL["tracker"] and 1 <= frame <= 60 and frame not in ROLL["reference_seen_frames"]:
        reference_direction(graph, frame)
        ROLL["reference_seen_frames"].add(frame)
    return snapshot


def measured_roll(*args):
    item = ORIGINAL_MEASURE(*args)
    require(ROLL["installed"], "Pilot reference missing during measurement")
    source, rig, tracker, actual, cloth, record, body, clone, probe, _frame = args
    graph = bpy.context.evaluated_depsgraph_get()
    reference = diag.mesh_snapshot(ROLL["reference"], graph)
    target = diag.weighted_target(ROLL["reference"], reference, GROUP)
    require(target["available"] and target["single_native_target_vertex"] == 0 and target["weight_sum"] == 1.,
            "Pilot must track its exact sole native point, not a guessed location")
    skin, physical = diag.mesh_snapshot(probe, graph), diag.mesh_snapshot(actual, graph)
    require(len(skin["points"]) == len(physical["points"]) == 800, "Pilot raw-index measurement requires original 800 vertices")
    points = []
    for index in (395, 399):
        positive = [weight for weight in skin["weights"][index] if weight["weight"] > 0]
        require(len(positive) == 1 and positive[0]["name"] == ROLL["names"]["def"] and positive[0]["weight"] == 1.,
                "Pilot explanatory points must keep their exact 100% single-DEF weights")
        points.append({"raw_vertex_index": index, "native_weights": positive,
            "skinned_world": diag.vector(skin["points"][index]), "physical_world": diag.vector(physical["points"][index]),
            "gap_m": (skin["points"][index]-physical["points"][index]).length*bpy.context.scene.unit_settings.scale_length})
    evaluated = rig.evaluated_get(graph)
    item["one_segment_roll"] = {"pilot": ROLL["names"], "reference_exact_native_target": target,
        "raw395_399": points, "native_bones": {layer: diag.bone_content(rig, evaluated, ROLL["names"][layer]) for layer in ("phys", "def")},
        "reference_projection": next(row for row in ROLL["reference_samples"] if row["frame"] == _frame),
        "helper_and_one_added_constraint_exact": True, "frozen_all_other_stretch_guards_still_exact": True,
        "limitation": "One off-surface native reference is an experimental local orientation cue. It cannot provide different roll to the two heights of a single rigid segment, and FULL-inheritance/local shear remains."}
    return item


def manifest():
    values = ORIGINAL_MANIFEST()
    values[str(Path(__file__).resolve())] = qa.file_state(Path(__file__).resolve())
    return values


def main():
    require(not stretch.PREFLIGHT_ONLY, "This pilot requires the same full 60-frame comparison")
    stretch.graph_content, stretch.verify_active_constraints = normalized_graph, extended_verify
    stretch.guarded_contract, stretch.probe_then_transfer = combined_guard, probe_then_roll
    stretch.measured_transfer, stretch.experiment_manifest = measured_roll, manifest
    diag.mesh_snapshot = observed_mesh_snapshot
    result = stretch.main()
    result["purpose"] = "Unreleased one-segment native off-surface reference roll over the frozen actual-surface/Stretch comparison"
    result["frozen_roll_dependencies"] = FROZEN
    result["one_segment_only"] = True
    result["production_effect_accepted"] = result["canonical_full_graph_pass"] = False
    result["limitations"].append("Only one segment has native roll reference. Off-surface Surface Deform may transfer a different local face than intended; one rigid roll cannot fit the measured approximately ten-degree within-segment variation.")
    output = Path(sys.argv[sys.argv.index("--output")+1]).resolve() / "experimental_actual_surface.json"
    conversions = []
    serializable = diag.json_content(result, conversions=conversions)
    serializable["json_mathutils_conversions"] = conversions
    output.write_text(json.dumps(serializable, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("EXPERIMENTAL_ONE_SEGMENT_ROLL_REPORT=" + str(output), flush=True)
    return result


if __name__ == "__main__":
    main()
