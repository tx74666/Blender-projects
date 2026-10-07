"""PREPARED ONLY: one live DirectMain Cloth800 -> absolute final3040 case.

Factory Blender5.2, exact7ac isolated input. Original Main Manual skin, original
33 author groups and native-bound raw80 Body attachment feed NEW owned Cloth.
The final owned skirt uses indexed absolute C positions before original Subsurf;
no S+C-H0 and no new private Rig/raw drivers. Old PHYS targets remain unchanged
and public bone-physics influence stays0. Only body channels receive QA keys.
Synthetic walk/run/stop-turn/raise-leg are stress inputs, not imported clips.
Manual/held-frame observations are separate. No artist deployment or acceptance.
The frozen 281e input proof must actually finish before this candidate may run.
Current typed artist protection is deliberately inherited, never silently waived.
"""
import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DIRECT = HERE / "verify_direct_main_manual_input52.py"
DIRECT_SHA = "281e9d90ca1c2896c7e07f53e43ee34be57b48960eb57977b630bfebde7192a3"
ADAPTER = HERE / "verify_direct_main_manual_input52_current_disk.py"
ADAPTER_SHA = "19033198def9907af52906ca8efe315593a907466d83c7f441a60d0c17a7129e"
STAGE = "LIVE_DIRECT_MAIN_CLOTH_52"
_DIRECT = _CORE = _ADAPTER = None
_DYNAMIC = {}


def need(condition, message):
    if not condition:
        raise RuntimeError("LiveCloth52: " + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load_direct():
    need(sha(DIRECT) == DIRECT_SHA, "frozen281e changed")
    spec = importlib.util.spec_from_file_location("live_cloth_frozen281e", DIRECT)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def load_adapter():
    need(sha(ADAPTER) == ADAPTER_SHA, "frozen current-disk adapter changed")
    spec=importlib.util.spec_from_file_location("live_cloth_currentdisk1903",ADAPTER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def completed_direct_proof(path, expected, direct):
    need(type(expected) is str and len(expected) == 64 and all(c in "0123456789abcdef" for c in expected), "explicit proof SHA required")
    need(path.is_absolute() and path.resolve().is_relative_to(HERE) and path.is_file() and sha(path) == expected, "exact private DirectMain proof absent/changed")
    report = json.loads(path.read_text(encoding="utf-8"))
    adapter=load_adapter()
    need(report.get("stage") == adapter.STAGE and report.get("script_sha256") == ADAPTER_SHA, "proof is not completed immutable current-disk DirectMain")
    positive = ("direct_main_manual_input_success", "native_completed", "ready_for_next_private_gate", "owned_cleanup_exact", "cache_metadata_exact",
                "source_disk_exact", "input_artist_disk_exact", "script_disk_exact", "frozen_pins_disk_exact", "canonical_validation_after_reload",
                "pose_after_reload_exact", "playback_after_reload_exact", "author_frame_after_reload_exact")
    need(all(report.get(k) is True for k in positive) and not report.get("cleanup_errors")
         and report.get("protection_before_reload", {}).get("success") is True and report.get("protection_after_reload", {}).get("success") is True,
         "DirectMain terminal AND/author protection incomplete")
    need(report.get("runtime52", {}).get("version") == [5, 2, 0]
         and report.get("automatic_Original_semantic_acceptance") is False, "native5.2/Manual scope not recorded")
    need(report.get("current_artist_disk_protection", {}).get("current_artist_sha256") == adapter.ARTIST_SHA, "different typed current disk baseline; requires separately reviewed adapter")
    restore=report.get("live_author_restore",{})
    need(not restore.get("errors") and all(restore.get(k) is True for k in ("constraint_pointers_and_RNA_exact","raw_pose_exact","id_properties_exact","frame_exact","cloth_flags_exact","cache_exact")),"Direct live author restore incomplete")
    return {"path": str(path), "sha256": expected, "script_sha256": ADAPTER_SHA, "mechanism_completed": True,
            "scope": "Input and Manual Original prerequisite only; does not prove live Cloth/effect/Keys/Automatic Original"}


def input_recipe(case, frame, frames):
    need(case in {"walk", "run", "abrupt_stop_turn", "leg_raise"} and frames >= 40 and 1 <= frame <= frames, "invalid bounded synthetic input")
    p = (frame - 1.) / (frames - 1.)
    if case == "leg_raise":
        lift = math.sin(math.pi * min(p / .6, 1.)) * .95 if p < .6 else 0.
        return {"left": lift, "right": 0., "forward_height": 0., "turn": 0., "stopped": p >= .6}
    stop = .55
    moving = min(p / stop, 1.) if case == "abrupt_stop_turn" else p
    gait = math.sin(2. * math.pi * (3. if case == "run" else 2.) * moving)
    amplitude = .65 if case == "run" else .35
    turn = min(max((p - stop) / .17, 0.), 1.) * math.pi * .5 if case == "abrupt_stop_turn" else 0.
    if case == "abrupt_stop_turn" and p >= stop:
        gait = 0.
    return {"left": amplitude * gait, "right": -amplitude * gait,
            "forward_height": (.7 if case == "run" else .35) * moving, "turn": turn,
            "stopped": case == "abrupt_stop_turn" and p >= .72}


def precision_guard(points, metres):
    values = [float(x) for point in points for x in point]
    need(values and all(math.isfinite(x) for x in values) and math.isfinite(metres) and metres > 0., "precision input missing/nonfinite")
    bound = max(1.e-7, 8. * 2.**-23 * max(abs(x) for x in values) * metres)
    need(bound <= 1.e-5, "native world precision exceeds independent10um cap")
    return {"metres": bound, "floor_m": 1.e-7, "cap_m": 1.e-5, "Float32_multiplier": 8.,
            "scope": "Native readback allowance only, separate from unchanged50um input/motion guard"}


def geometry_quality(observed, requested, metres):
    """All actual final edges/triangles; denominator failures stay Unknown."""
    need(observed["edges"] == requested["edges"] and observed["faces"] == requested["faces"], "same-frame edge/face correspondence unavailable")
    a, b = observed["points"], requested["points"]
    edge_rows, area_rows, rotations, unresolved = [], [], [], []
    for index, (i, j) in enumerate(observed["edges"]):
        old, new = (b[i]-b[j]).length, (a[i]-a[j]).length
        if old <= 1.e-12: unresolved.append({"edge": index, "reason": "zero/low requested denominator"}); continue
        edge_rows.append({"edge": index, "vertices": [i,j], "ratio": new/old})
    triangles_same=observed["triangles"] == requested["triangles"]
    if not triangles_same:unresolved.append({"reason":"native geometry-derived triangulation differs; face/edge topology still exact"})
    for index, (i,j,k) in enumerate(observed["triangles"] if triangles_same else []):
        old, new = (b[j]-b[i]).cross(b[k]-b[i]), (a[j]-a[i]).cross(a[k]-a[i])
        if min(old.length, new.length) <= 1.e-16: unresolved.append({"triangle": index, "reason": "low/degenerate normal or area"}); continue
        area_rows.append({"triangle": index, "ratio": new.length/old.length})
        dot = old.normalized().dot(new.normalized())
        if dot < 0.: rotations.append({"triangle": index, "dot": dot})
    return {"status": "Unknown" if unresolved or not edge_rows or not area_rows else "measured",
            "maximum_edge_ratio": max(edge_rows, key=lambda x:x["ratio"]) if edge_rows else None,
            "minimum_area_ratio": min(area_rows, key=lambda x:x["ratio"]) if area_rows else None,
            "normal_rotation_over90_candidates": len(rotations), "first_rotation_candidates": rotations[:8],
            "unresolved_count": len(unresolved), "first_unresolved": unresolved[:8], "same_native_triangulation":triangles_same,
            "limitation": "Same-frame requested-vs-final geometry only. Normal rotation is not independent proof of flipped topology; no self-intersection or aesthetic acceptance.", "accepted": False}


def graph_contract(values, c, final, requested, graph):
    rig, source, record, actual, clone, body, cloth, qa, surface = (values[k] for k in ("rig","source","record","actual","clone","body","cloth","qa","surface"))
    original = _DIRECT.quarantine_proof(source, rig, record, actual, clone, body, cloth, graph, qa, surface)
    forbidden = {c, final, requested}
    for owner in (source, rig, body, clone, actual, *rig.pose.bones):
        for con in owner.constraints:
            need(getattr(con,"target",None) not in forbidden and getattr(con,"pole_target",None) not in forbidden, "new output feeds original constraint")
        for id_owner in (owner, getattr(owner,"data",None)):
            animation = getattr(id_owner,"animation_data",None)
            if animation:
                for curve in animation.drivers:
                    for variable in curve.driver.variables:
                        for target in variable.targets:
                            need(target.id not in forbidden and target.id not in {obj.data for obj in forbidden}, "new output feeds original driver")
    need(c.parent == rig and [m.type for m in c.modifiers] == ["ARMATURE","SURFACE_DEFORM","CLOTH"]
         and c.modifiers[0].object == rig and c.modifiers[1].target == clone, "single-writer input dependency differs")
    need(c.modifiers[2].show_viewport and c.modifiers[2].show_render,"new Cloth must be enabled during live measurements")
    for obj in (final, requested):
        need(obj.parent == rig and [m.type for m in obj.modifiers] == ["ARMATURE","NODES","SUBSURF"], "absolute final modifier order differs")
    return {"legacy_quarantine": original, "edges": ["MainManual/rawDEF -> original native ARM800", "Body-only clone -> copied bound SD80",
            "native preCloth800 -> NEW dynamic-rest Cloth800", "NEW C800 -> indexed absolute GN -> original Subsurf3040"],
            "newC_target_in_original_constraints_or_drivers": False, "oldPHYS_targets_retargeted": False,
            "scope": "Current loaded fixture and actual target inventory; no generic future-driver or Keys claim"}


def exercise_dynamic(values, base):
    import bpy
    from mathutils import Quaternion, Vector
    global _DYNAMIC
    _DYNAMIC = {}
    source, rig, record, before, after, oracle, old_cloth, actual, clone, home, qa, diag, surface, same, read, report, write, budget, metres, guard, controls, manual, deform, upstream, waist, forbidden, ring, height, legs, axes, raw_contract, original_group_count, args = (
        values[k] for k in ("source","rig","record","before","after","oracle","cloth","actual","clone","home","qa","diag","surface","same","read","report","write","budget","metres","guard","controls","manual","deform","upstream","waist","forbidden","ring","height","legs","axes","raw_contract","original_group_count","args"))
    values["base"] = base; state = _CORE._STATE
    report["stage"], report["scope"] = STAGE, __doc__
    report["lease_budget"]={"soft_seconds":args.max_seconds,"root_external_seconds_required":args.max_seconds+60.,"one_case_only":True}
    report["completed_direct_prerequisite"] = completed_direct_proof(args.direct_proof, args.direct_proof_sha, _DIRECT)
    report.update(accepted=False, automatic_Original_semantic_acceptance=False, live_solver_feedback_exercised=False,
                  artist_saved=False, new_backend_deployed=False, Keys_verified=False, Unity_export_verified=False,
                  visual_acceptance=False, long_run_settling_accepted=False)
    need(base.key_values(source) is None, "exact fixture KeysNone only; live Key animation not exercised")
    work_pose = qa.pose_channels(rig); frozen_cache = same.cache_state(old_cloth,qa)
    need(not old_cloth.show_viewport and not old_cloth.show_render, "old Cloth not paused before owned seeks")
    root = rig.pose.bones["CTRL_master"]
    thigh_names = {side:legs[side]["chain"][0] for side in ("L","R")}
    thighs = {side:rig.pose.bones[name] for side,name in thigh_names.items()}
    need(root.rotation_mode == "XYZ" and all(b.rotation_mode == "QUATERNION" for b in thighs.values()), "existing RootXYZ/legQuaternion modes required")
    paths = {root.path_from_id("location"),root.path_from_id("rotation_euler"),*(b.path_from_id("rotation_quaternion") for b in thighs.values())}
    need(not any(curve.data_path in paths for curve in rig.animation_data.drivers), "author driver owns requested Body Action channel")
    _DYNAMIC["Root_location"] = (root, list(root.location))
    old_location, old_euler = Vector(root.location), Vector(root.rotation_euler)
    old_rotations = {side:Quaternion(b.rotation_quaternion) for side,b in thighs.items()}
    action = bpy.data.actions.new("QA Dress Body Motion")
    state["qa_action"], state["qa_action_pointer"] = action, action.as_pointer()
    rig.animation_data.action = action; state["bound_qa_action"] = action
    for frame in range(1,args.frames+1):
        move = input_recipe(args.case,frame,args.frames)
        root.location = old_location + Vector((0.,height*move["forward_height"],0.))
        root.rotation_euler = old_euler + Vector((0.,0.,move["turn"]))
        for side,bone in thighs.items():
            bone.rotation_quaternion = old_rotations[side] @ Quaternion(axes[thigh_names[side]],move["left" if side=="L" else "right"])
            need(bone.keyframe_insert(data_path="rotation_quaternion",frame=frame,group="QA Body"),"native leg key insertion failed")
        need(root.keyframe_insert(data_path="location",frame=frame,group="QA Body")
             and root.keyframe_insert(data_path="rotation_euler",frame=frame,group="QA Body"),"native Root key insertion failed")
    curves = qa.curve_paths(action); state["action_paths"] = {(f.data_path,int(f.array_index)) for f in curves}
    expected = {(root.path_from_id(field),i) for field in ("location","rotation_euler") for i in range(3)} | {(bone.path_from_id("rotation_quaternion"),i) for bone in thighs.values() for i in range(4)}
    need(len(curves)==14 and state["action_paths"]==expected and rig.animation_data.action_slot is not None, "Body-only14curve native Action/slot differs")
    for curve in curves:
        for point in curve.keyframe_points: point.interpolation="LINEAR"
    report["synthetic_Action"] = {"name":action.name,"curve_paths":sorted(state["action_paths"]),"frames":args.frames,"case":args.case,
        "Dress_keys":0,"mode_conversion":False,"real_imported_clip":False,"stopped_final10":all(input_recipe(args.case,f,args.frames)["stopped"] for f in range(args.frames-9,args.frames+1))}
    if args.case == "abrupt_stop_turn": need(report["synthetic_Action"]["stopped_final10"],"last10 not fully stationary")
    remember, link, copy_object = (values[k] for k in ("remember","link","copy_object"))
    c = copy_object(after,"QA Dress Cloth"); link(c)
    need(surface._frame(c)==surface._frame(after) and c.modifiers[1].is_bound and c.modifiers[1].target==clone, "live copied Body bind/chart unavailable")
    pin_name = old_cloth.settings.vertex_group_mass
    need(pin_name and pin_name not in c.vertex_groups and pin_name not in rig.data.bones,"owned pin group name collision")
    native_pins = qa.physics._weights(actual)[pin_name]; pin_values=[native_pins.get(i,0.) for i in range(800)]
    need(len(pin_values)==800 and all(math.isfinite(v) and 0.<=v<=1. for v in pin_values) and [i for i,v in enumerate(pin_values) if v==1.]==ring,"native hard80 pin identity incomplete")
    pin = c.vertex_groups.new(name=pin_name)
    for i,v in enumerate(pin_values): pin.add([i],v,"REPLACE")
    cloth = c.modifiers.new("Dress Physics","CLOTH"); _DYNAMIC["cloth"]=cloth
    surface._copy_scalars(old_cloth.settings,cloth.settings); surface._copy_scalars(old_cloth.collision_settings,cloth.collision_settings)
    surface._copy_scalars(old_cloth.settings.effector_weights,cloth.settings.effector_weights)
    cloth.settings.vertex_group_mass=pin.name; cloth.settings.rest_shape_key=None; cloth.settings.use_dynamic_mesh=True
    cloth.collision_settings.collection=old_cloth.collision_settings.collection
    need(cloth.collision_settings.collection is not None and set(cloth.collision_settings.collection.objects)=={bpy.data.objects[n] for n in record["physics"]["colliders"]},"explicit original4 collision collection differs")
    for prop in cloth.settings.bl_rna.properties:
        if prop.identifier.startswith("vertex_group_"):
            name=getattr(cloth.settings,prop.identifier); need(not name or c.vertex_groups.get(name) is not None,"copied Cloth group missing: "+prop.identifier)
    cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step=1,args.frames+args.manual_steps,1
    cloth.point_cache.use_external=cloth.point_cache.use_disk_cache=False
    need(not cloth.point_cache.is_baked,"new runtime cache unexpectedly baked")
    def absolute_output(name, upstream_obj):
        obj=copy_object(source,name)
        for modifier in list(obj.modifiers)[1:]:obj.modifiers.remove(modifier)
        link(obj)
        group=remember("node_groups",bpy.data.node_groups.new(name+" Output","GeometryNodeTree"))
        group.interface.new_socket(name="Geometry",in_out="INPUT",socket_type="NodeSocketGeometry")
        group.interface.new_socket(name="Geometry",in_out="OUTPUT",socket_type="NodeSocketGeometry")
        inp=group.nodes.new("NodeGroupInput");out=group.nodes.new("NodeGroupOutput");info=group.nodes.new("GeometryNodeObjectInfo")
        info.transform_space="RELATIVE";info.inputs["Object"].default_value=upstream_obj;info.inputs["As Instance"].default_value=False
        pos=group.nodes.new("GeometryNodeInputPosition");index=group.nodes.new("GeometryNodeInputIndex")
        sample=group.nodes.new("GeometryNodeSampleIndex");sample.data_type="FLOAT_VECTOR";sample.domain="POINT";sample.clamp=False
        setpos=group.nodes.new("GeometryNodeSetPosition");setpos.inputs["Selection"].default_value=True;setpos.inputs["Offset"].default_value=(0.,0.,0.)
        for a,b in ((inp.outputs["Geometry"],setpos.inputs["Geometry"]),(info.outputs["Geometry"],sample.inputs["Geometry"]),
            (pos.outputs["Position"],sample.inputs["Value"]),(index.outputs["Index"],sample.inputs["Index"]),
            (sample.outputs["Value"],setpos.inputs["Position"]),(setpos.outputs["Geometry"],out.inputs["Geometry"])): group.links.new(a,b)
        need(all(edge.is_valid for edge in group.links),"native absolute index links invalid")
        obj.modifiers.new("Dress Output","NODES").node_group=group
        surface._copy_scalars(source.modifiers[-1],obj.modifiers.new("Dress Smooth","SUBSURF"))
        return obj
    requested=absolute_output("QA Dress Requested",after); final=absolute_output("QA Dress Final",c)
    need(source.modifiers[-1].type=="SUBSURF" and source.modifiers[-1].levels==1,"original3040 Subsurf changed")
    report["physics_parameters"]={"cloth":surface._rna(cloth.settings),"collision":surface._rna(cloth.collision_settings),
        "effectors":surface._rna(cloth.settings.effector_weights),"pin_weights":pin_values,"fps":home.render.fps,"fps_base":home.render.fps_base,
        "scene_gravity":list(home.gravity),"scene_use_gravity":home.use_gravity,"colliders":{n:surface._rna(bpy.data.objects[n].collision) for n in record["physics"]["colliders"]},
        "dynamic_rest":True,"rest_shape_key":None,"old_cache_reset_baked_or_freed":False,"output":"absolute indexed C800 then original native Subsurf3040",
        "changing_rest_is_hard_input_positions":False,"limitation":"Dynamic rest updates spring rest structure. Free simulated vertices are not required to equal moving input."}
    report["collision_visibility"]=read.visibility_evidence([c,after,final,requested,values["body"],clone,*[bpy.data.objects[n] for n in record["physics"]["colliders"]]],cloth,home)
    samples=[]; contacts=[]; identities={}; first=None; daily_last=None; root_rows=[]; previous_hem=None; tail=[]
    outside=[i for i in range(800) if i not in set(ring)]; waist_index=source.vertex_groups[waist].index
    def sample(label,diagnose=False):
        nonlocal first,previous_hem
        budget(); tick=time.perf_counter();bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get();graph_seconds=time.perf_counter()-tick
        meshes={};clocks={}
        for name,obj in (("oracle",oracle),("before800",before),("after800",after),("C800",c),("requested3040",requested),("final3040",final)):
            tick=time.perf_counter();meshes[name]=read.native_mesh(obj,graph,diag);clocks[name]=time.perf_counter()-tick
        tick=time.perf_counter()
        for name,mesh in meshes.items():
            count=3040 if "3040" in name else 800
            need(len(mesh["points"])==count and mesh["native_vertex_index_order"]==list(range(count)) and mesh["weights_complete"] and qa.finite(mesh["points"]),"actual native count/index/finite/weight coverage missing: "+name)
            identity={k:mesh[k] for k in ("edges","faces","native_group_mapping","weights")}
            if name not in identities:identities[name]=identity
            need(identity==identities[name],"actual native mapping/weights/connectivity drift: "+name)
        exact=base.error_summary(meshes["before800"]["points"],meshes["oracle"]["points"],metres)
        effect=base.error_summary(meshes["after800"]["points"],meshes["before800"]["points"],metres,outside)
        pin_error=base.error_summary(meshes["C800"]["points"],meshes["after800"]["points"],metres,ring)
        micro=precision_guard(meshes["after800"]["points"],metres)
        output_identity=all(meshes["final3040"][k]==meshes["requested3040"][k] for k in ("edges","faces","weights","native_group_mapping"))
        need(output_identity,"final/requested3040 original weights/connectivity differ")
        fixed=[i for i,row in enumerate(meshes["final3040"]["weights"]) if any(x["index"]==waist_index and x["weight"]>=.999 for x in row)]
        need(len(fixed)==160,"final hard160 Waist set incomplete")
        for name in ("final3040","requested3040"):meshes[name]["free_indices"]=[i for i in range(3040) if i not in set(fixed)]
        posed=rig.evaluated_get(graph);root_world=posed.matrix_world@posed.pose.bones[root.name].matrix;waist_world=posed.matrix_world@posed.pose.bones[waist].matrix
        knee=list(posed.matrix_world@posed.pose.bones[legs["L"]["chain"][1]].head)
        hem_names={chain["def"][-1] for chain in record["chains"]}
        hem=[i for i,row in enumerate(meshes["final3040"]["weights"]) if any(x["name"] in hem_names and x["weight"]>0. for x in row) and i not in set(fixed)]
        need(hem,"actual free weighted final collection empty")
        # Normalized native Waist axes retain physical world distance; no scale inverse.
        from mathutils import Matrix
        linear=waist_world.to_3x3();up=linear.col[2].normalized();right=linear.col[0]-up*linear.col[0].dot(up);need(right.length>1.e-12,"degenerate Waist axes");right.normalize();forward=up.cross(right).normalized()
        local=[Vector(tuple((meshes["final3040"]["points"][i]-waist_world.translation).dot(axis) for axis in (right,forward,up))) for i in hem]
        local_step=base.error_summary(local,previous_hem,metres)["maximum_m"] if previous_hem is not None else None;previous_hem=local
        closure=_CORE._STATE["closure"](source,rig,record,manual,controls,upstream+[waist],forbidden,graph,surface)
        contract=graph_contract(values,c,final,requested,graph)
        _CORE.raw_source_program_guard(rig,deform)
        _DIRECT.audit_direct((before,after),after.modifiers[1],values)
        copied=qa.raw_mesh_content(after);copied["groups"]=copied["groups"][:original_group_count];copied["weights"]=[[w for w in row if w[0]<original_group_count] for row in copied["weights"]]
        c_raw=qa.raw_mesh_content(c);c_raw["groups"]=c_raw["groups"][:original_group_count];c_raw["weights"]=[[w for w in row if w[0]<original_group_count] for row in c_raw["weights"]]
        need(qa.raw_mesh_content(before)==raw_contract and copied==raw_contract and c_raw==raw_contract and qa.raw_mesh_content(final)==raw_contract,"raw source33 groups/UV/weights/Keys differ")
        need(surface._rna(c.modifiers[0])==surface._rna(before.modifiers[0]) and surface._rna(c.modifiers[1])==surface._rna(after.modifiers[1]),"copied C native skin/boundSD RNA differs")
        need(all(next((x["weight"] for x in row if x["index"]==pin.index),None)==pin_values[index] for index,row in enumerate(meshes["C800"]["weights"])),"new C exact native pin values/explicit0 coverage differ")
        row={"label":label,"frame":[home.frame_current,home.frame_subframe],"original_active":qa.original.active(rig),"first_skin_vs_actual_oracle":exact,
            "raw80_outside720":effect,"raw80_current_pin_error":pin_error,"microguard":micro,"original_cache14_exact":same.cache_state(old_cloth,qa)==frozen_cache,
            "new_cache":same.cache_state(cloth,qa),"native_knee_world":knee,"native_Root_world":diag.matrix(root_world),"native_Waist_world":diag.matrix(waist_world),
            "actual_C800_vs_current_input":base.error_summary(meshes["C800"]["points"],meshes["after800"]["points"],metres),
            "final_hem_weighted_vertices":len(hem),"final_hem_Waist_rigid_step_m":local_step,"geometry_quality":geometry_quality(meshes["final3040"],meshes["requested3040"],metres),
            "mesh_summaries":{n:same.summary(m["points"],qa) for n,m in meshes.items()},"current_Main_closure":closure,"graph_contract":contract,
            "native_timing_segments":{"graph_ready_seconds":graph_seconds,"mesh_readback_seconds":clocks,"stats_and_current_guards_seconds":time.perf_counter()-tick,
                "scope":"Direct phase clocks; native update/readback plus separately measured Python guards/stats. Not GUI FPS or solver-only time."},"accepted":False}
        samples.append(row);report["live_motion_samples"]=samples;write()
        need(exact["maximum_m"]==0. and effect["maximum_m"]<=guard and row["original_cache14_exact"],"unchanged exactSkin/50um outside720/cache14 guard failed")
        need(pin_error["maximum_m"]<=micro["metres"],"hard80 deviates from CURRENT actual input beyond unchanged native microguard")
        current={"row":row,"meshes":meshes,"local":local,"knee":knee}
        if first is None:first=current
        root_rows.append({"frame":home.frame_current,"Root":diag.matrix(root_world),"Waist":diag.matrix(waist_world)})
        if diagnose:
            tick=time.perf_counter();body_mesh=diag.mesh_snapshot(values["body"],graph);body_seconds=time.perf_counter()-tick
            need(len(body_mesh["points"])<=args.body_vertex_limit and qa.finite(body_mesh["points"]),"actual Body diagnostic exceeds budget/nonfinite")
            row["actual_registered_Body_vs_initial"]=base.error_summary(body_mesh["points"],first["body"]["points"] if "body" in first else body_mesh["points"],metres)
            bounds=diag.framing(rig,record,graph)
            projections=[(p-bounds["waist"]).dot(bounds["up"]) for mesh in (meshes["final3040"],body_mesh) for p in mesh["points"]]
            need(projections,"collision projection scope empty");bounds["lower"],bounds["upper"]=min(projections)-1.e-4,max(projections)+1.e-4
            epsilon=max(1.e-8,record["fit"]["height_world"]*1.e-6);tick=time.perf_counter()
            crossing=diag.triangle_crossings(meshes["final3040"],body_mesh,bounds,args.triangle_pair_limit,epsilon)
            contact={"label":label,"frame":home.frame_current,"region":"Complete observed Body/final projection envelope",
                "actual_open_Body_inside_outside":False,"status":crossing["status"],"strict_crossing_count":crossing.get("actual_crossing_pair_count"),
                "exact_tested_pairs":crossing.get("exact_tested_pairs"),"first_pairs":crossing["crossing_pairs"][:8],
                "unresolved_counts":{k:len(crossing[k]) for k in ("coplanar_unresolved","degenerate_unresolved","boundary_unresolved")},"closed3":[],"accepted":False}
            for name in record["physics"]["colliders"][:-1]:
                collider=bpy.data.objects[name];qa.physics._closed_collider(collider);native=qa.ClosedCollider(collider,graph,epsilon)
                contact["closed3"].append({"object":name,"actual_final_free_signed_vertices":qa.collision_metrics(meshes["final3040"]["points"],native,metres,meshes["final3040"]["free_indices"])})
            contact["timings"]={"Body_readback_seconds":body_seconds,"collision_stats_seconds":time.perf_counter()-tick}
            contact["Unknown_if_incomplete"]=crossing["status"]!="measured" or any(contact["unresolved_counts"].values())
            contacts.append(contact);report["sparse_actual_final_contacts"]=contacts;write()
            current["body"]=body_mesh;current["bounds"]=bounds
            if args.render and label in {"daily_end","manual_settled"}:
                folder=args.output/label;folder.mkdir();render_args=SimpleNamespace(output=folder,frame=home.frame_current)
                render=diag.native_render(render_args,meshes["final3040"],body_mesh,bounds)
                render["provenance"]="Actual live Main body Action/current unkeyed Manual input -> NEW Cloth800 -> absolute final3040; private QA scene only"
                report.setdefault("renders",{})[label]=render;write()
        return current
    sparse={1,args.frames//2,args.frames}; stopped=set()
    for frame in range(1,args.frames+1):
        budget();tick=time.perf_counter();home.frame_set(frame);frame_seconds=time.perf_counter()-tick
        current=sample("daily_end" if frame==args.frames else "daily_"+str(frame),frame in sparse)
        current["row"]["native_timing_segments"]["frame_set_seconds"]=frame_seconds
        if input_recipe(args.case,frame,args.frames)["stopped"]:tail.append(current["row"]["final_hem_Waist_rigid_step_m"]);stopped.add(frame)
        daily_last=current
    response={"knee_m":max(math.dist(first["knee"],row["native_knee_world"])*metres for row in samples),
        "Root_translation_m":max(math.dist([first["row"]["native_Root_world"][i][3] for i in range(3)],[row["native_Root_world"][i][3] for i in range(3)])*metres for row in samples),
        "native_root_and_Waist_matrix_series":root_rows,"final_stop_tail_hem_steps_m":tail[-10:],
        "stop_tail_complete":len(stopped)>=10,"settling_acceptance":False,"long_term_or_GUI_performance_measured":False}
    from mathutils import Matrix
    for role in ("Root","Waist"):
        reference=Matrix(first["row"]["native_"+role+"_world"]).to_quaternion()
        response["native_"+role+"_angular_response_rad"]=max(reference.rotation_difference(Matrix(row["native_"+role+"_world"]).to_quaternion()).angle for row in samples)
    report["real_body_motion_response"]=response;write()
    body_response=base.error_summary(daily_last["body"]["points"],first["body"]["points"],metres)
    response["actual_registered_Body_first_last_change"]=body_response
    response["actual_registered_Body_sparse_maximum_change_m"]=max(row["actual_registered_Body_vs_initial"]["maximum_m"] for row in samples if "actual_registered_Body_vs_initial" in row)
    response["nontrivial_native_Cloth_effect_observed"]=max(row["actual_C800_vs_current_input"]["maximum_m"] for row in samples)>guard
    need(response["knee_m"]>height*.01*metres,"actual evaluated knee input response absent")
    need(response["actual_registered_Body_sparse_maximum_change_m"]>guard,"actual registered Body response absent")
    if args.case!="leg_raise":need(body_response["maximum_m"]>guard,"actual registered Body travel response absent")
    if args.case!="leg_raise":need(response["Root_translation_m"]>height*.01*metres,"actual evaluated Root travel absent")
    if args.case=="abrupt_stop_turn":need(response["native_Root_angular_response_rad"]>1. and response["native_Waist_angular_response_rad"]>1.,"actual native Root/Waist turn response absent")
    # Held frame: explicitly detach only our Action before unkeyed input edits.
    rig.animation_data.action=None;state["bound_qa_action"]=None
    detached=sample("held_after_ownAction_detach")
    detach_error=base.error_summary(detached["meshes"]["after800"]["points"],daily_last["meshes"]["after800"]["points"],metres)
    report["ownAction_detach_input_error"]=detach_error;write();need(detach_error["maximum_m"]<=guard,"ownAction detachment changed actual input >50um")
    held_frame=(home.frame_current,home.frame_subframe)
    thigh=thighs["L"];thigh.rotation_quaternion=Quaternion(thigh.rotation_quaternion)@Quaternion(axes[thigh.name],.55);rig.update_tag()
    leg_held=sample("held_leg_unkeyed",True)
    hem=rig.pose.bones[record["controls"]["hem"]];hem.location=Vector(hem.location)+Vector((-height*.04,0.,0.));rig.update_tag()
    manual_held=sample("held_manual_unkeyed",True)
    def held_receipt(previous,current):
        return {"same_frame_exact":(home.frame_current,home.frame_subframe)==held_frame,
            "actual_input800_change":base.error_summary(current["meshes"]["after800"]["points"],previous["meshes"]["after800"]["points"],metres),
            "cached_C800_change":base.error_summary(current["meshes"]["C800"]["points"],previous["meshes"]["C800"]["points"],metres),
            "final3040_change":base.error_summary(current["meshes"]["final3040"]["points"],previous["meshes"]["final3040"]["points"],metres),
            "current_input_vs_C800":base.error_summary(current["meshes"]["C800"]["points"],current["meshes"]["after800"]["points"],metres),
            "cache_before":previous["row"]["new_cache"],"cache_after":current["row"]["new_cache"],
            "interpretation":"Observation only: native Cloth may require forward time and may be stale/invalidated at held frame. No hidden keys/reset/projected pose correction.","preview_accepted":False}
    report["held_frame_observations"]={"leg":held_receipt(detached,leg_held),"Manual":held_receipt(leg_held,manual_held)};write()
    need(all(row["same_frame_exact"] for row in report["held_frame_observations"].values()),"held probe advanced frame")
    need(all(row["actual_input800_change"]["maximum_m"]>guard for row in report["held_frame_observations"].values()),"real unkeyed leg/Manual input missing")
    for frame in range(args.frames+1,args.frames+args.manual_steps+1):
        budget();tick=time.perf_counter();home.frame_set(frame);elapsed=time.perf_counter()-tick
        current=sample("manual_settled" if frame==args.frames+args.manual_steps else "manual_forward_"+str(frame),frame==args.frames+args.manual_steps)
        current["row"]["native_timing_segments"]["frame_set_seconds"]=elapsed
    # Stop NEW Cloth before author restoration. Old Cloth gets its original flags only at original author frame.
    cloth.show_viewport=cloth.show_render=False
    root.location=old_location;_CORE.restore_pose(rig,work_pose);home.frame_set(state["frame"][0],subframe=state["frame"][1]);bpy.context.view_layer.update()
    old_cloth.show_viewport,old_cloth.show_render=state["cloth_flags"];bpy.context.view_layer.update()
    need(same.cache_state(old_cloth,qa)==frozen_cache,"old14cache changed during live newCloth seeks")
    old_points=qa.world_mesh(actual,bpy.context.evaluated_depsgraph_get())["points"]
    report["original_C_restored_error"]=base.error_summary(old_points,state["initial_C"],metres);write()
    need(report["original_C_restored_error"]["maximum_m"]==0.,"original sameframe C not exact after restore")
    # Public Manual Original prerequisite already belongs to completed281e. This candidate never invokes Automatic Original.
    report["Original_scope"]={"prerequisite":"Completed281e public Manual Original roundtrip", "new_vertex_Automatic_Original":False,
        "same_frame_Original_vs_newCloth_exercised":False,"limitation":"New final writer does not automatically inherit legacy Automatic Original compensation contract."}
    report["mechanism_collection_success"]=True
    report["before_attachment_reproduction_complete"]=report["native_endpoint_index_identity_exact"]=report["native_completed"]=True
    report["effect_quality_accepted"]=False
    values["endpoint_path"].write_text(json.dumps({"stage":STAGE,"case":args.case,"scope":"Compact actual live mesh hashes/counts, no historical world interpolation",
        "samples":[{"label":row["label"],"frame":row["frame"],"mesh_summaries":row["mesh_summaries"]} for row in samples],"accepted":False},indent=2,allow_nan=False),encoding="utf-8")


def restore_dynamic(report,qa,surface):
    """Additional owned solver pause and Root translation restored before frozen author AND."""
    errors=[]
    try:
        if "cloth" in _DYNAMIC:_DYNAMIC["cloth"].show_viewport=_DYNAMIC["cloth"].show_render=False
        if "Root_location" in _DYNAMIC:
            state=_CORE._STATE;rig=state["rig"]
            if rig.animation_data and rig.animation_data.action == state.get("qa_action"):
                rig.animation_data.action=None;state["bound_qa_action"]=None
            owner,value=_DYNAMIC["Root_location"];owner.location=value
    except Exception as error:errors.append(str(error))
    _CORE.restore_program(report,qa,surface)
    report["dynamic_restore_errors"]=errors
    need(not errors,"additional dynamic restoration failed")


def prepared_namespace(direct,core,base,args):
    adapter=load_adapter();namespace=adapter.prepared_namespace(direct,core,base)
    main,closure,_inherited,_direct_edits=direct.modified_program(base,core)
    edits=[]
    def replace(old,new,label):
        nonlocal main
        need(main.count(old)==1,"frozen substitution nonunique: "+label);main=main.replace(old,new,1);edits.append(label)
    replace('("objects","meshes","armatures","curves","shape_keys")','("objects","meshes","armatures","curves","shape_keys","node_groups")',"own new GN receipts")
    replace('        exercise_direct(locals(), FROZEN_BASE)','        exercise_dynamic(locals(), FROZEN_BASE)',"new live single-writer observation")
    replace('                for kind in ("meshes","curves","armatures"):', '                for group in reversed(owned["node_groups"]):\n                    need(group.users==0,"Owned GN acquired foreign user"); bpy.data.node_groups.remove(group)\n                for kind in ("meshes","curves","armatures"):',"release exact owned GN after object users removed")
    namespace.update(globals());namespace["FROZEN_BASE"]=base;namespace["__file__"]=str(Path(__file__))
    namespace["PINS"].update({DIRECT:DIRECT_SHA,ADAPTER:ADAPTER_SHA,Path(__file__):sha(Path(__file__)),args.direct_proof:args.direct_proof_sha})
    namespace["restore_program"]=restore_dynamic
    old_capture=namespace["capture_program"]
    def capture(*values):
        result=old_capture(*values);core._STATE["closure"]=namespace["current_main_manual_closure"]
        values[-1]["live_cloth_source_substitutions"]=edits
        return result
    namespace["capture_program"]=capture
    exec(compile(closure,str(Path(__file__)),"exec"),namespace)
    exec(compile(main,str(Path(__file__)),"exec"),namespace)
    return namespace,edits


def pure_checks():
    direct=load_direct();core=direct.load_core();base=core.load_base()
    # Source-only: current artist transition and future Direct terminal report are NOT fabricated.
    fake=SimpleNamespace(direct_proof=HERE/"UNMEASURED_DIRECT52.json",direct_proof_sha="0"*64)
    namespace,edits=prepared_namespace(direct,core,base,fake)
    need(len(edits)==3 and namespace["restore_program"] is restore_dynamic,"bounded constructor/cleanup substitutions differ")
    tree=ast.parse(inspect.getsource(exercise_dynamic))
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
    need(not any(isinstance(n.func,ast.Attribute) and n.func.attr in {"driver_add","free_bake","bake","restore_channels","shape_key_add"} for n in calls),"forbidden native edit/cache/Key API")
    keys=[n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=="keyframe_insert"]
    need(len(keys)==3 and all(any(k.arg=="group" and isinstance(k.value,ast.Constant) and k.value.value=="QA Body" for k in n.keywords) for n in keys),"Dress/precomputed geometry Action added")
    for case in ("walk","run","abrupt_stop_turn","leg_raise"):
        recipes=[input_recipe(case,f,60) for f in range(1,61)]
        need(all(all(math.isfinite(x) for x in row.values()) for row in recipes),"nonfinite synthetic recipe")
    final10=[input_recipe("abrupt_stop_turn",f,60) for f in range(51,61)]
    need(all(x==final10[0] and x["stopped"] and x["left"]==x["right"]==0. for x in final10),"combined stopturn final10 not fixed")
    need(abs(final10[0]["turn"]-math.pi*.5)<1.e-15,"stopturn not90deg")
    need('info.transform_space="RELATIVE"' in inspect.getsource(exercise_dynamic) and 'sample.clamp=False' in inspect.getsource(exercise_dynamic)
         and 'cloth.settings.use_dynamic_mesh=True' in inspect.getsource(exercise_dynamic),"absolute/dynamic-rest construction absent")
    source=inspect.getsource(exercise_dynamic)
    need('old_cloth.collision_settings.collection' in source and 'raw80_current_pin_error' in source and 'micro["metres"]' in source
         and 'exact["maximum_m"]==0.' in source and 'effect["maximum_m"]<=guard' in source,"original input/80/output guards absent")
    need('report["effect_quality_accepted"]=False' in source and 'preview_accepted' in source,"effect/held acceptance falsely inferred")
    compile(Path(__file__).read_text(encoding="utf-8"),str(Path(__file__)),"exec")
    return {"passed":True,"bounded_substitutions":len(edits),"pure_controls":9,"Native":False,
            "current_disk_adapter_pinned":ADAPTER_SHA,"completed_Direct52_proof_required":True,"accepted":False}


def arguments():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path);parser.add_argument("--direct-proof",type=Path);parser.add_argument("--direct-proof-sha")
    parser.add_argument("--case",choices=("walk","run","abrupt_stop_turn","leg_raise"),default="run")
    parser.add_argument("--frames",type=int,default=60);parser.add_argument("--manual-steps",type=int,default=10)
    parser.add_argument("--max-seconds",type=float,default=180.);parser.add_argument("--triangle-pair-limit",type=int,default=2000000)
    parser.add_argument("--body-vertex-limit",type=int,default=500000);parser.add_argument("--render",action="store_true");parser.add_argument("--pure-checks",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and not args.output.exists() and args.output.resolve().is_relative_to(HERE)
             and args.output.resolve()!=HERE,"fresh private output only")
        need(args.direct_proof is not None and args.direct_proof_sha is not None,"completed native Direct prerequisite required")
        need(40<=args.frames<=60 and 1<=args.manual_steps<=10 and 0.<args.max_seconds<=180. and 0<args.triangle_pair_limit<=2000000,"bounded one-case scope only")
    return args


def main(args):
    global _DIRECT,_CORE,_ADAPTER
    if args.pure_checks:print(json.dumps(pure_checks()));return 0
    _DIRECT=load_direct();_CORE=_DIRECT.load_core();base=_CORE.load_base();_ADAPTER=load_adapter()
    _ADAPTER.protection_proof(base,_DIRECT)  # Current bytes only, no UI/save/fullraw identity claim.
    completed_direct_proof(args.direct_proof,args.direct_proof_sha,_DIRECT)
    namespace,_edits=prepared_namespace(_DIRECT,_CORE,base,args)
    return namespace["main"](args)


if __name__=="__main__":raise SystemExit(main(arguments()))
