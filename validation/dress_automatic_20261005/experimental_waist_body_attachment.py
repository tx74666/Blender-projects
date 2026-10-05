"""Unreleased sole-ring waist attachment QA; frozen direct Cloth output retained.

Factory background only, the same abrupt_stop 1..60 forward replay. Independent
actual800 gains one Surface Deform and one exact saved ring0 mask, between its
unchanged waist Armature and unchanged Cloth. No source/Body/Rig edits, no target
triangulation, no fallback pairing, no public bake/reset and no production claim.
"""

import hashlib
import json
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
FROZEN = {"experimental_direct_cloth_render.py":"835d7f8caba4220f7aef2d74857d25a4c0c08a31a56dc9c5a7daf8b87fb28a2f",
    "experimental_actual_surface.py":"188fd43531133a42aa7c12cf689a3dcb0fc5e1bfbfb2bc2f9527f83fa6ce5bae",
    "experimental_body_collision.py":"08f07d27a5aaf83aa42f15ff579d47d473d6eb901ab0a52ee62022b54a7880b9"}
for name,expected in FROZEN.items():
    if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != expected:
        raise RuntimeError("Frozen waist-attachment dependency differs: "+name)
sys.path.insert(0,str(HERE))
import experimental_direct_cloth_render as direct

base,diag,qa,bodyqa,skirt,require = direct.base,direct.diag,direct.qa,direct.bodyqa,direct.skirt,direct.require
ORIGINAL_CLONE,ORIGINAL_ACTUAL = bodyqa.clone_body,base.make_actual_cloth
ORIGINAL_BIND = base.bind_tracker
ORIGINAL_GUARD,ORIGINAL_MEASURE = direct.combined_guard,direct.measured_frame
ORIGINAL_REMOVE,ORIGINAL_MANIFEST,ORIGINAL_SNAPSHOT = direct.remove_probe,direct.manifest,diag.mesh_snapshot
STATE = {"installed":False,"input_probe":None,"frame_proofs":{}}
MASK_NAME = "QA Sole Saved Waist Ring Body Attachment"


def group_content(obj,count=None):
    groups = list(obj.vertex_groups) if count is None else list(obj.vertex_groups)[:count]
    indices = {group.index for group in groups}
    return {"groups":[(group.index,group.name,group.lock_weight) for group in groups],
        "weights":[[(item.group,item.weight) for item in vertex.groups if item.group in indices] for vertex in obj.data.vertices]}


def actual_protected(actual,cloth):
    return {"raw_mesh":qa.digest({"topology":base.topology_content(actual),
        "coords":[diag.vector(vertex.co) for vertex in actual.data.vertices],"attributes":direct.attribute_content(actual.data)}),
        "old_groups":group_content(actual,2),"object_properties":direct.properties(actual),
        "data_properties":direct.properties(actual.data),"parent":qa.id_name(actual.parent),
        "parent_type":actual.parent_type,"parent_bone":actual.parent_bone,
        "parent_inverse":diag.matrix(actual.matrix_parent_inverse),"basis":diag.matrix(actual.matrix_basis),
        "cloth_settings":direct.strict_rna(cloth.settings),"collision":direct.strict_rna(cloth.collision_settings),
        "effectors":direct.strict_rna(cloth.settings.effector_weights),"cache":qa.cache_state(cloth),
        "cache_writable":direct.strict_rna(cloth.point_cache)}


def body_signature(clone):
    return qa.digest({"raw_object_mesh_keys_modifiers":direct.source_signature(clone),
        "collision":direct.strict_rna(clone.collision)})


def target_topology(clone,graph):
    evaluated = clone.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=graph)
    try:
        mesh.calc_loop_triangles()
        content = {"vertices":len(mesh.vertices),"edges":[tuple(edge.vertices) for edge in mesh.edges],
            "faces":[tuple(face.vertices) for face in mesh.polygons],
            "loops":[(loop.vertex_index,loop.edge_index) for loop in mesh.loops],
            "triangles":[(tuple(triangle.vertices),tuple(triangle.loops),triangle.polygon_index) for triangle in mesh.loop_triangles]}
        require(content["vertices"] and content["faces"],"Body target must retain complete evaluated native topology")
        return {"sha256":qa.digest(content),"vertices":content["vertices"],"edges":len(content["edges"]),
            "faces":len(content["faces"]),"loops":len(content["loops"]),"triangles":len(content["triangles"]),
            "sample_evaluated_triangle_indices":list(direct.BODY_TRIANGLE_SAMPLES),
            "sample_evaluated_triangles":[content["triangles"][index] for index in direct.BODY_TRIANGLE_SAMPLES]}
    finally:
        evaluated.to_mesh_clear()


def selection_content():
    objects,armatures = [],{}
    for obj in bpy.context.view_layer.objects:
        objects.append((obj.name,obj.select_get(),obj.hide_get()))
        if obj.type == "ARMATURE":
            armatures[obj.name] = {"active":obj.data.bones.active.name if obj.data.bones.active else None,"flags":[]}
            for owner_kind,owners in (("bone",obj.data.bones),("pose",obj.pose.bones)):
                for bone in owners:
                    flags = {name:getattr(bone,name) for name in ("select","select_head","select_tail") if hasattr(bone,name)}
                    armatures[obj.name]["flags"].append((owner_kind,bone.name,flags))
    active = bpy.context.view_layer.objects.active
    return {"objects":objects,"armatures":armatures,"active":active.name if active else None,
        "mode":active.mode if active else "OBJECT"}


def restore_selection(saved):
    current = bpy.context.view_layer.objects.active
    if current and current.mode != "OBJECT":
        require("FINISHED" in bpy.ops.object.mode_set(mode="OBJECT"),"Unable to restore pre-bind object mode")
    for name,selected,hidden in saved["objects"]:
        obj = bpy.context.view_layer.objects[name]
        obj.hide_set(hidden)
        obj.select_set(selected)
    for name,values in saved["armatures"].items():
        obj = bpy.context.view_layer.objects[name]
        for kind,bone_name,flags in values["flags"]:
            owner = obj.data.bones[bone_name] if kind == "bone" else obj.pose.bones[bone_name]
            for key,value in flags.items():
                setattr(owner,key,value)
        obj.data.bones.active = obj.data.bones.get(values["active"]) if values["active"] else None
    active = bpy.context.view_layer.objects.get(saved["active"]) if saved["active"] else None
    bpy.context.view_layer.objects.active = active
    if active and saved["mode"] != "OBJECT":
        require("FINISHED" in bpy.ops.object.mode_set(mode=saved["mode"]),"Unable to restore pre-bind pose mode")
    require(selection_content() == saved,"Binding changed original object/bone selection, active, mode or hide state")


def point_nojump(before,after,report,label):
    require(len(before["points"]) == len(after["points"]) == 800 and qa.finite(before["points"]) and qa.finite(after["points"]),
            "Neutral attachment proof needs exact finite800 input")
    require(before["faces"] == after["faces"] and before["edges"] == after["edges"],"Attachment changed input topology")
    error = max((a-b).length for a,b in zip(before["points"],after["points"]))
    meters = bpy.context.scene.unit_settings.scale_length
    report[label] = {"maximum_world":error,"maximum_m":error*meters,
        "limit_world":base.BIND_WORLD_LIMIT,"limit_m":base.BIND_METRES_LIMIT,"all800_proved":True}
    require(error <= base.BIND_WORLD_LIMIT and error*meters <= base.BIND_METRES_LIMIT,
            label+" displaced the original no-Cloth pin input")


def restore_modifier_active(actual):
    STATE["surface"].is_active = False
    actual.modifiers[0].is_active = STATE["old_modifier_settings"][0]["is_active"]
    actual.modifiers[2].is_active = STATE["old_modifier_settings"][1]["is_active"]


def verify_attachment():
    actual,cloth,clone = STATE["actual"],STATE["cloth"],STATE["clone"]
    surface,mask = STATE["surface"],STATE["mask"]
    require([m.type for m in actual.modifiers] == ["ARMATURE","SURFACE_DEFORM","CLOTH"]
            and actual.modifiers[1] == surface and actual.modifiers[2] == cloth
            and [direct.strict_rna(actual.modifiers[index]) for index in (0,2)] == STATE["old_modifier_settings"],
            "Only one SD insertion between exact old Armature/Cloth is allowed")
    require(actual_protected(actual,cloth) == STATE["protected"] and body_signature(clone) == STATE["body_hash"],
            "Attachment changed raw mesh, original groups/pin/settings/cache, Body or object channels")
    require(len(actual.vertex_groups) == 3 and actual.vertex_groups[2] == mask and mask.index == 2
            and mask.name == MASK_NAME and not mask.lock_weight,"Only one identified sole-ring mask may be added")
    require(all(item.group in {0,1,2} for vertex in actual.data.vertices for item in vertex.groups),
            "Unregistered native deform-group assignments are forbidden")
    members = [(vertex.index,item.weight) for vertex in actual.data.vertices for item in vertex.groups if item.group == mask.index]
    require(sorted(members) == [(index,1.) for index in sorted(STATE["ring0"])],"Attachment mask must be exactly the saved80 raw IDs, no other assignments")
    require(surface.type == "SURFACE_DEFORM" and surface.target == clone and surface.vertex_group == mask.name
            and not surface.invert_vertex_group and surface.strength == 1. and surface.use_sparse_bind
            and surface.is_bound and direct.strict_rna(surface) == STATE["surface_settings"],
            "Native sole-ring sparse SD target/group/strength/flags/full RNA changed")
    probe = STATE.get("input_probe")
    if probe is not None:
        expected_probe_settings = [direct.strict_rna(m) for m in actual.modifiers[:2]]
        require(expected_probe_settings[1]["is_active"] is False,"Original actual SD must retain its inactive UI flag")
        expected_probe_settings[1]["is_active"] = True
        require(probe != actual and probe.data == actual.data and [m.type for m in probe.modifiers] == ["ARMATURE","SURFACE_DEFORM"]
                and probe.modifiers[1].is_bound and probe.modifiers[1].target == clone
                and expected_probe_settings == STATE["probe_modifier_settings"]
                and [direct.strict_rna(m) for m in probe.modifiers] == STATE["probe_modifier_settings"]
                and group_content(probe) == group_content(actual) and probe.animation_data is None and not probe.constraints
                and direct.properties(probe) == STATE["probe_properties"]
                and probe.parent == actual.parent and probe.parent_type == actual.parent_type and probe.parent_bone == actual.parent_bone
                and diag.matrix(probe.matrix_parent_inverse) == diag.matrix(actual.matrix_parent_inverse)
                and diag.matrix(probe.matrix_basis) == diag.matrix(actual.matrix_basis)
                and diag.matrix(probe.matrix_world) == diag.matrix(actual.matrix_world),"Owned read-only pre-Cloth probe changed")
        require(probe.name not in STATE["collision_collection"].objects,"Pin-input probe cannot join the frozen final collision graph")


def captured_clone(body,rig,record,collection,report):
    clone = ORIGINAL_CLONE(body,rig,record,collection,report)
    require(STATE.get("clone") is None,"Only the single frozen Body clone is permitted")
    STATE.update(clone=clone,body_hash=body_signature(clone),collision_collection=collection)
    return clone


def remove_input_probe():
    probe = STATE.get("input_probe")
    if probe is not None:
        name = probe.name
        require(probe != STATE["actual"] and probe.data == STATE["actual"].data,"Refusing guessed pin-probe deletion")
        try:
            bpy.data.objects.remove(probe,do_unlink=True)
        finally:
            if bpy.data.objects.get(name) is None:
                STATE["input_probe"] = None
        require(name not in bpy.data.objects,"Owned temporary pin-input probe was not removed")
        STATE["report"]["temporary_pin_input_probe_removed_before_candidate_save"] = True


def rollback_attachment(report):
    STATE["installed"] = False
    remove_input_probe()
    actual,cloth = STATE["actual"],STATE["cloth"]
    surface,mask = STATE.get("surface"),STATE.get("mask")
    if surface is not None:
        actual.modifiers.remove(surface)
        STATE["surface"] = None
    if mask is not None:
        actual.vertex_groups.remove(mask)
        STATE["mask"] = None
    for modifier,saved in zip(actual.modifiers,STATE["old_modifier_settings"]):
        modifier.is_active = saved["is_active"]
    require([m.type for m in actual.modifiers] == ["ARMATURE","CLOTH"] and len(actual.vertex_groups) == 2
            and [direct.strict_rna(m) for m in actual.modifiers] == STATE["old_modifier_settings"]
            and actual_protected(actual,cloth) == STATE["protected"] and body_signature(STATE["clone"]) == STATE["body_hash"],
            "Attachment rollback did not restore complete original candidate groups/modifier RNA/pin/cache/Body")
    report["rollback_removed_only_owned_SD_and_mask_originals_exact"] = True


def install_attachment(actual,cloth,rig,record,report):
    scene = bpy.context.scene
    require(scene.frame_current == 0 and scene.frame_subframe == 0. and rig.data.pose_position == "POSE" and bpy.context.mode in {"OBJECT","POSE"},
            "Attachment is only installed before the first simulation frame in the frozen POSE0 fixture")
    require(STATE.get("clone") is not None and [m.type for m in actual.modifiers] == ["ARMATURE","CLOTH"]
            and len(actual.vertex_groups) == 2 and actual.animation_data is None and not actual.constraints,
            "Expected frozen independent actual800 with two original groups and exact native stack")
    require(MASK_NAME not in rig.data.bones and MASK_NAME not in actual.vertex_groups,
            "The added mask must not accidentally become an existing Armature bone group")
    ring0 = list(record["fit"]["rings"][0])
    mass = actual.vertex_groups[cloth.settings.vertex_group_mass]
    armature,waist = actual.modifiers[0],record["controls"]["waist"]
    require(armature.object == rig and armature.use_vertex_groups and not armature.use_bone_envelopes
            and not armature.use_deform_preserve_volume and not armature.use_multi_modifier and not armature.vertex_group
            and rig.data.bones[waist].use_deform and actual.vertex_groups[0].name == waist
            and (mass.name not in rig.data.bones or not rig.data.bones[mass.name].use_deform)
            and all(next((item.weight for item in vertex.groups if item.group == 0),0.) == 1. for vertex in actual.data.vertices),
            "Unmasked input proof requires the exact generated single-weight linear waist Armature contract")
    hard = [vertex.index for vertex in actual.data.vertices if next((item.weight for item in vertex.groups if item.group == mass.index),0.) == 1.]
    require(len(ring0) == len(set(ring0)) == 80 and sorted(ring0) == sorted(hard),"Saved ring0 must be the exact80 sole mass1 raw IDs")
    STATE.update(actual=actual,cloth=cloth,rig=rig,record=record,ring0=ring0,report=report,surface=None,mask=None,
        old_modifier_settings=[direct.strict_rna(m) for m in actual.modifiers],protected=actual_protected(actual,cloth))
    frame,subframe,pose_position = scene.frame_current,scene.frame_subframe,rig.data.pose_position
    selections = selection_content()
    channels,actions = base.channels_hash(rig),{action.name:qa.digest(qa.action_content(action)) for action in bpy.data.actions}
    flags = (cloth.show_viewport,cloth.show_render)
    report.update(exact_raw_mask_ids=ring0,old_groups=STATE["protected"]["old_groups"],old_modifier_RNA=STATE["old_modifier_settings"],
        body_target=STATE["clone"].name,body_before_sha256=STATE["body_hash"],
        policy="Only SD+one mask on independent actual800; no source/Body/Rig changes, no fallback, no public physics operation. Native internal bind IDs are not exposed/read.")
    try:
        mask = actual.vertex_groups.new(name=MASK_NAME)
        STATE["mask"] = mask
        require(mask.name == MASK_NAME and mask.index == 2,"Attachment mask identity was not fresh/exact")
        mask.add(ring0,1.,"REPLACE")
        surface = actual.modifiers.new("QA Sole Waist Ring Native Body Attachment","SURFACE_DEFORM")
        STATE["surface"] = surface
        surface.target,surface.vertex_group = STATE["clone"],mask.name
        surface.strength,surface.invert_vertex_group,surface.use_sparse_bind = 1.,False,True
        actual.modifiers.move(2,1)
        restore_modifier_active(actual)
        surface.show_viewport = surface.show_render = False
        cloth.show_viewport = cloth.show_render = False
        try:
            skirt._activate(bpy.context,actual,"OBJECT")
            scene.frame_set(0,subframe=0.)
            bpy.context.view_layer.update()
            before_pose = ORIGINAL_SNAPSHOT(actual,bpy.context.evaluated_depsgraph_get())
            require(max((a-b).length for a,b in zip(before_pose["points"],waist_armature_points(bpy.context.evaluated_depsgraph_get())))
                    <= base.BIND_WORLD_LIMIT,"Single-weight native waist matrix prediction does not match all800 unmodified input")
            rig.data.pose_position = "REST"
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            before_rest = ORIGINAL_SNAPSHOT(actual,graph)
            STATE["target_topology"] = target_topology(STATE["clone"],graph)
            STATE["relative"] = diag.matrix(actual.matrix_world.inverted() @ STATE["clone"].matrix_world)
            surface.show_viewport = surface.show_render = True
            result = bpy.ops.object.surfacedeform_bind(modifier=surface.name)
            bpy.context.view_layer.update()
            report["native_bind"] = {"operator":sorted(result),"is_bound":surface.is_bound,"no_fallback":True,
                "error_if_exposed":getattr(surface,"error",None),"target_complete_evaluated_topology":STATE["target_topology"],
                "body_relative_to_actual_at_bind":STATE["relative"]}
            require("FINISHED" in result and surface.is_bound,"Body attachment native bind failed; no triangulation/nearest fallback allowed")
            point_nojump(before_rest,ORIGINAL_SNAPSHOT(actual,bpy.context.evaluated_depsgraph_get()),report,"rest0_bind_nojump")
            rig.data.pose_position = pose_position
            scene.frame_set(frame,subframe=subframe)
            bpy.context.view_layer.update()
            point_nojump(before_pose,ORIGINAL_SNAPSHOT(actual,bpy.context.evaluated_depsgraph_get()),report,"restored_pose0_bind_nojump")
        finally:
            rig.data.pose_position = pose_position
            cloth.show_viewport,cloth.show_render = flags
            scene.frame_set(frame,subframe=subframe)
            restore_selection(selections)
            bpy.context.view_layer.update()
            report["restored"] = {"frame":scene.frame_current,"subframe":scene.frame_subframe,"pose_position":rig.data.pose_position,
                "channels_sha256":base.channels_hash(rig),"actions_sha256":{action.name:qa.digest(qa.action_content(action)) for action in bpy.data.actions},
                "selection_active_mode_hide_exact":selection_content() == selections,"cloth_flags":[cloth.show_viewport,cloth.show_render]}
            require(scene.frame_current == frame and scene.frame_subframe == subframe and rig.data.pose_position == pose_position
                    and base.channels_hash(rig) == channels and report["restored"]["actions_sha256"] == actions
                    and (cloth.show_viewport,cloth.show_render) == flags,"Binding did not restore complete candidate input/action/flags")
        STATE["surface_settings"] = direct.strict_rna(surface)
        probe = actual.copy()
        STATE["input_probe"] = probe
        probe.name = "QA Temporary Waist Attachment Pin Input"
        bpy.context.scene.collection.objects.link(probe)
        for key in list(probe.keys()):
            del probe[key]
        probe["CD_QA_TemporaryPinInput"] = True
        probe.hide_render = True
        require(probe.data == actual.data and probe.modifiers[-1].type == "CLOTH","Native pre-Cloth copy lost its independent candidate data")
        probe.modifiers.remove(probe.modifiers[-1])
        probe.modifiers[0].is_active = actual.modifiers[0].is_active
        probe.modifiers[1].is_active = True
        STATE["probe_modifier_settings"] = [direct.strict_rna(m) for m in actual.modifiers[:2]]
        require(STATE["probe_modifier_settings"][1]["is_active"] is False,"Original actual SD activation changed during probe copy")
        STATE["probe_modifier_settings"][1]["is_active"] = True
        report["owned_probe_UI_metadata_contract"] = {"allowed_difference":{"modifier_index":1,"type":"SURFACE_DEFORM",
            "field":"is_active","actual_expected":False,"probe_expected":True},
            "reason":"Native removal of the copied final Cloth activates copied SD; False setter preserves the last active modifier. Only this owned probe UI field differs; all other full RNA fields remain exact.",
            "old_actual_modifier_active_flags":[(modifier.name,modifier.is_active) for modifier in actual.modifiers],
            "expected_probe_complete_modifier_RNA":STATE["probe_modifier_settings"]}
        bpy.context.view_layer.update()
        STATE["probe_properties"] = direct.properties(probe)
        STATE["installed"] = True
        verify_attachment()
        report.update(complete_SD_RNA=STATE["surface_settings"],temporary_pin_input_probe=probe.name,
            original_protected_sha256=qa.digest(STATE["protected"]),native_mapping_claim="Exact source mask IDs and evaluated target topology indices; internal bind face/weight IDs not exposed")
    except Exception:
        rollback_attachment(report)
        raise


def make_actual(source,rig,tracker,old_cloth,record,collection,report):
    actual,cloth = ORIGINAL_ACTUAL(source,rig,tracker,old_cloth,record,collection,report)
    report["waist_body_attachment"] = {}
    install_attachment(actual,cloth,rig,record,report["waist_body_attachment"])
    return actual,cloth


def bind_tracker(rig,tracker,actual,cloth,report):
    # Frozen base assigns the already-created collision collection after make_actual
    # returns. Prove this one original assignment; the attachment never writes it.
    collection = STATE["collision_collection"]
    require(cloth.collision_settings.collection == collection and
            set(collection.objects.keys()) == set(record_name for record_name in STATE["record"]["physics"]["colliders"]) | {STATE["clone"].name},
            "Frozen base final collision assignment differs from its exact old3 plus Body collection")
    expected = dict(STATE["protected"]["collision"])
    expected["collection"] = qa.id_name(collection)
    require(direct.strict_rna(cloth.collision_settings) == expected,
            "Frozen base changed collision settings beyond its original explicit collection assignment")
    STATE["protected"]["collision"] = expected
    STATE["report"]["frozen_base_final_collision_assignment_proved"] = {"collection":collection.name,
        "members":sorted(collection.objects.keys()),"attachment_did_not_write_collection":True}
    verify_attachment()
    return ORIGINAL_BIND(rig,tracker,actual,cloth,report)


def waist_armature_points(graph):
    rig,actual = STATE["rig"],STATE["actual"]
    evaluated = rig.evaluated_get(graph)
    name = STATE["record"]["controls"]["waist"]
    deformation = evaluated.matrix_world @ evaluated.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted()
    deformation = deformation @ evaluated.matrix_world.inverted() @ actual.evaluated_get(graph).matrix_world
    return [deformation @ vertex.co for vertex in actual.data.vertices]


def guarded_contract(rig,record,source):
    if STATE["installed"]:
        verify_attachment()
    return ORIGINAL_GUARD(rig,record,source)


def attachment_snapshot(obj,graph):
    snapshot = ORIGINAL_SNAPSHOT(obj,graph)
    if STATE["installed"] and obj == STATE["actual"] and 1 <= bpy.context.scene.frame_current <= 60:
        frame = bpy.context.scene.frame_current
        if frame not in STATE["frame_proofs"]:
            verify_attachment()
            topology = target_topology(STATE["clone"],graph)
            require(topology == STATE["target_topology"],"Full evaluated Body topology/loop-triangle/sample IDs differ; native tessellation may vary even without an artist edit")
            relative = diag.matrix(STATE["actual"].matrix_world.inverted() @ STATE["clone"].matrix_world)
            delta = max(abs(a-b) for row_a,row_b in zip(relative,STATE["relative"]) for a,b in zip(row_a,row_b))
            require(delta <= 1.e-6,"Native Body attachment bind-relative object transform changed")
            pin_input = ORIGINAL_SNAPSHOT(STATE["input_probe"],graph)
            require(len(pin_input["points"]) == len(snapshot["points"]) == 800 and qa.finite(pin_input["points"]) and qa.finite(snapshot["points"]),
                    "Pin input/actual must remain finite indexed800")
            error = max((pin_input["points"][index]-snapshot["points"][index]).length for index in STATE["ring0"])
            unchanged = max((pin_input["points"][index]-point).length for index,point in enumerate(waist_armature_points(graph))
                if index not in STATE["ring0"])
            meters = bpy.context.scene.unit_settings.scale_length
            require(unchanged <= base.BIND_WORLD_LIMIT and unchanged*meters <= base.BIND_METRES_LIMIT,
                    "Body attachment changed one of the720 unmasked native waist inputs")
            require(error <= base.BIND_WORLD_LIMIT and error*meters <= base.BIND_METRES_LIMIT,"Actual hardpin80 did not follow its native SD input")
            STATE["frame_proofs"][frame] = {"frame":frame,"target_topology_sha256":topology["sha256"],
                "target_relative_matrix_max_delta":delta,"hardpin80_vs_native_input_max_world":error,"hardpin80_vs_native_input_max_m":error*meters,
                "unmasked720_vs_single_weight_waist_input_max_world":unchanged,"unmasked720_vs_single_weight_waist_input_max_m":unchanged*meters}
    return snapshot


def measured_attachment(args,source,rig,tracker,actual,cloth,record,body,clone,probe,frame):
    item = ORIGINAL_MEASURE(args,source,rig,tracker,actual,cloth,record,body,clone,probe,frame)
    graph = bpy.context.evaluated_depsgraph_get()
    pin_input = ORIGINAL_SNAPSHOT(STATE["input_probe"],graph)
    pin_input["free_indices"] = list(range(800))
    roles = {name:layer for chain in record["chains"] for layer in ("manual","phys","def") for name in chain[layer]}
    roles[record["controls"]["waist"]] = "waist"
    bounds,meters = diag.framing(rig,record,graph),bpy.context.scene.unit_settings.scale_length
    epsilon = max(1.e-8,record["fit"]["height_world"]*1.e-6)
    input_body,_ = diag.body_diagnostics(body,graph,pin_input,bounds,args,meters,roles,epsilon)
    item["waist_body_attachment"] = {"native_frame_proof":STATE["frame_proofs"][frame],
        "pin_input_preCloth800_body":input_body,"pin_input_preCloth800_world":[diag.vector(point) for point in pin_input["points"]],
        "hardpin80_input_world":[{"raw_vertex_index":index,"world":diag.vector(pin_input["points"][index])} for index in STATE["ring0"]],
        "actual800_body":item["actual_registered_body_vs_physical_cloth"],
        "wrapper_final3040_body":item["direct_cloth_output"]["final3040"]["actual_registered_body"],
        "body_surface_unsigned_only":True,"production_effect_accepted":False,
        "input_scope":"Pre-Cloth full800 diagnostic candidates: free_indices is deliberately all800, not physical free/pin classification. Hardpin80 input positions are separately identified; not all pre-Cloth crossings are pinned-face crossings"}
    return item


def remove_probes(probe,source,report):
    errors = []
    try:
        remove_input_probe()
        if STATE["installed"]:
            verify_attachment()
    except Exception as exc:
        errors.append(exc)
    try:
        ORIGINAL_REMOVE(probe,source,report)
    except Exception as exc:
        errors.append(exc)
    if errors:
        STATE["report"].setdefault("cleanup_errors",[]).extend(str(exc) for exc in errors)
        raise RuntimeError("Waist/direct temporary cleanup proof failed: "+"; ".join(str(exc) for exc in errors)) from errors[0]


def manifest():
    values = ORIGINAL_MANIFEST()
    values[str(Path(__file__).resolve())] = qa.file_state(Path(__file__).resolve())
    return values


def main():
    bodyqa.clone_body,base.make_actual_cloth = captured_clone,make_actual
    base.bind_tracker = bind_tracker
    direct.combined_guard,direct.measured_frame,direct.remove_probe,direct.manifest = guarded_contract,measured_attachment,remove_probes,manifest
    diag.mesh_snapshot = attachment_snapshot
    output = Path(sys.argv[sys.argv.index("--output")+1]).resolve()/"experimental_actual_surface.json"
    original_error = None
    try:
        result = direct.main()
    except Exception as exc:
        original_error = exc
        if not output.is_file():
            raise
        result = json.loads(output.read_text(encoding="utf-8"))
    result["frozen_direct_diagnostic_success"] = result["success"]
    proofs = [STATE["frame_proofs"][frame] for frame in sorted(STATE["frame_proofs"])]
    complete = STATE["installed"] and [item["frame"] for item in proofs] == list(range(1,61)) and STATE["input_probe"] is None
    result["waist_attachment_native60_proofs"] = proofs
    result["waist_attachment_completion"] = {"success":bool(complete),"input_probe_removed":STATE["input_probe"] is None,
        "frozen_dependencies":FROZEN,"accepted_model_effect":False}
    result["success"] = bool(result["success"] and complete)
    result["purpose"] = "Unreleased sole hardpin80 Body attachment before unchanged Cloth; frozen direct output/source metrics remain separate"
    result["limitations"].append("Sparse Body SD retains bind normal offsets and native multi-face interpolation; no guaranteed clearance. The 0.2743 transitional ring stays on original waist input. Fixed Basis only; manual/Keys/Original/modes/export unresolved. Target internal bind IDs are not exposed.")
    if not complete:
        result["errors"].append("Waist native60 topology/relative/hardpin/probe completion proof incomplete")
    conversions = []
    serializable = diag.json_content(result,conversions=conversions)
    serializable["json_mathutils_conversions"] = conversions
    output.write_text(json.dumps(serializable,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("EXPERIMENTAL_WAIST_BODY_ATTACHMENT_REPORT="+str(output),flush=True)
    if original_error is not None:
        raise RuntimeError("Frozen direct QA failed; waist evidence retained without overriding its failure") from original_error
    require(result["success"],"Waist Body attachment QA incomplete; inspect preserved report/candidate")
    return result


if __name__ == "__main__":
    main()
