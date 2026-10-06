"""PREPARED ONLY: same-case private contact preview with measured Body-follow waist.

Frozen9366 is retained. Capture native N/L/T, upstream bindings/C800/H0800/raw80
before geometric gates. N-to-L world waist motion is evidence, not pin failure;
Manual L-to-T must leave Body/upstream matrices and final160 waist unchanged.
New Scene hard160 follows the explicit measured endpoint input trajectory.
Relative pin readback uses unchanged independent micro-budget. No author Action,
artist application, full Body-volume proof or artistic acceptance is implied.
"""
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CONTINUOUS_SHA="9366a924d4bf5e1cfe30dafa8ceef020db774130d9c66e153fc661517988f8fe"
STATIC_SHA="06b7f1656dcb8a68ad5ddf9b92ec005a6b7c3cf2968eb60825e48f5de5721e1e"
COVERAGE_SHA="a232ae99e26a998f911c38efd1b95fcc45fb4c76ebd5d3a2c87bd8686196a055"
# Import only frozen pure/API helper definitions; its old main is never executed.
path=HERE/"prototype_static_continuous_contact_preview.py"
import hashlib
if hashlib.sha256(path.read_bytes()).hexdigest()!=CONTINUOUS_SHA:
    raise RuntimeError("Frozen9366 helper changed")
spec=importlib.util.spec_from_file_location("body_follow_continuous_helpers",path)
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
need,sha,load_static=base.need,base.sha,base.load_static
path_weights,path_points,point_delta=base.path_weights,base.path_points,base.point_delta
readback_guard,residual,normal_diagnostics=base.readback_guard,base.residual,base.normal_diagnostics
arguments,animate=base.arguments,base.animate
PIN=base.PIN; SOFT_WEIGHT=base.SOFT_WEIGHT; OFFICIAL=base.OFFICIAL


def waist_follow(observed,requested,start,ids,metres):
    need(ids and len(set(ids))==len(ids) and all(type(i) is int and 0<=i<len(observed) for i in ids),"Explicit nonempty native waist IDs required")
    return {"count":len(ids),"relative_pin_deviation":residual(observed,requested,ids,metres),
        "requested_world_movement_from_N":residual(requested,start,ids,metres),
        "observed_world_movement_from_N":residual(observed,start,ids,metres),
        "scope":"Precision of hard waist relative to the CURRENT captured/interpolated native input. World movement from N remains separate evidence, not a fixed-location pass.","accepted":False}


def manual_isolation(body_deltas,parents_exact,waist_delta,guard):
    need(body_deltas and all(math.isfinite(x) and x>=0. for x in body_deltas.values()) and math.isfinite(waist_delta) and waist_delta>=0.,"Incomplete finite Manual isolation evidence")
    return {"body_L_to_T_maximum_delta_m":body_deltas,"upstream_native_matrices_exact":bool(parents_exact),
        "waist160_L_to_T_maximum_delta_m":waist_delta,"unchanged_micro_guard_m":guard,
        "body_parent_unchanged":bool(parents_exact and all(x<=guard for x in body_deltas.values())),
        "manual_waist_isolated":bool(parents_exact and all(x<=guard for x in body_deltas.values()) and waist_delta<=guard),
        "scope":"Same author frame L-to-T only. Actual Body/upstream parent matrices must stay unchanged; Manual may move free skirt vertices, never hard160 beyond readback precision.","accepted":False}


def native_attachment(source,rig,actual,neutral,body,record,cloth,graph,read,diag,surface,same,qa,bpy):
    objects=[source,rig,actual,neutral,body]+[bpy.data.objects[name] for name in record["physics"]["colliders"]]
    frames={obj.name:{"object_pointer":obj.as_pointer(),"data_pointer":obj.data.as_pointer() if obj.data else None,
        "parent_contract":surface._frame(obj),"evaluated_world":diag.matrix(obj.evaluated_get(graph).matrix_world),
        "evaluated_parent_world":None if obj.parent is None else diag.matrix(obj.parent.evaluated_get(graph).matrix_world)} for obj in objects}
    names=[record["controls"]["waist"]]+surface._ancestors(rig,record); posed=rig.evaluated_get(graph)
    bones={name:{"parent":rig.data.bones[name].parent.name if rig.data.bones[name].parent else None,
        "rest_matrix":diag.matrix(rig.data.bones[name].matrix_local),"pose_matrix":diag.matrix(posed.pose.bones[name].matrix),
        "world_matrix":diag.matrix(posed.matrix_world@posed.pose.bones[name].matrix)} for name in names}
    ring=list(record["fit"]["rings"][0]); mask=[mod for mod in actual.modifiers if mod.type=="SURFACE_DEFORM"]
    pin=actual.vertex_groups.get(cloth.settings.vertex_group_mass)
    attachment=mask[0] if len(mask)==1 else None
    group=actual.vertex_groups.get(attachment.vertex_group) if attachment else None
    rows=[{"index":i,"co_local":list(actual.data.vertices[i].co),
        "groups":[{"index":item.group,"weight":item.weight} for item in actual.data.vertices[i].groups]} for i in ring]
    raw={"C800":read.native_mesh(actual,graph,diag),"H0800":read.native_mesh(neutral,graph,diag)}
    clone=bpy.data.objects[record["physics"]["colliders"][-1]]
    proof={"raw_C_mesh":surface._id(actual.data),"raw_C_vertex_count":len(actual.data.vertices),"ring0_raw_ids":ring,
        "ring0_raw_rows":rows,"native_raw_group_mapping":[{"index":g.index,"name":g.name,"lock_weight":g.lock_weight} for g in actual.vertex_groups],
        "pin_group":None if pin is None else {"index":pin.index,"name":pin.name},
        "body_mask_group":None if group is None else {"index":group.index,"name":group.name},
        "modifier_order":[{"name":mod.name,"type":mod.type} for mod in actual.modifiers],
        "body_attachment_modifier":None if attachment is None else {"settings":surface._rna(attachment),"is_bound":attachment.is_bound,
            "target_pointer":None if attachment.target is None else attachment.target.as_pointer()},
        "actual_BODY_ATTACHMENT":{"object":clone.name,"pointer":clone.as_pointer(),"roles":record["physics"]["surface"]["roles"]["BODY_ATTACHMENT"],
            "constraints":[surface._rna(c) for c in clone.constraints],"data_shared_with_registered_body":clone.data==body.data},
        "cloth_cache":same.cache_state(cloth,qa),
        "scope":"Raw80 ring0/body-mask/pin evidence belongs to C800. Final160 IDs are independently measured from O3040 weights; no inferred 80-to-160 map."}
    def weight(row,index): return next((item["weight"] for item in row["groups"] if item["index"]==index),None)
    proof["raw80_body_attachment_observed"]=bool(len(ring)==80 and len(set(ring))==80 and len(actual.data.vertices)==800 and len(raw["C800"]["points"])==len(raw["H0800"]["points"])==800
        and pin is not None and group is not None and attachment.is_bound and attachment.target==clone
        and record["physics"]["surface"]["roles"]["BODY_ATTACHMENT"]==[clone.name]
        and all(weight(row,pin.index)==1. and weight(row,group.index)==1. for row in rows))
    return {"object_frames":frames,"upstream_waist_bones":bones,"raw_inputs":raw,"body_attachment":proof}


def pure_checks():
    prior=base.pure_checks(); n=[(0.,0.,0.),(1.,0.,0.)]; l=[(.004,0.,0.),(1.,0.,0.)]; ids=[0]; guard=1.e-6
    q=waist_follow(l,l,n,ids,1.)
    need(q["relative_pin_deviation"]["maximum_m"]==0. and q["observed_world_movement_from_N"]["maximum_m"]==.004,"Real moving waist with exact relative pin follows")
    need(waist_follow(n,l,n,ids,1.)["relative_pin_deviation"]["maximum_m"]>guard,"World-static pin cannot pass moving target precision")
    need(waist_follow(l,l,n,ids,.01)["observed_world_movement_from_N"]["maximum_m"]==.00004,"Waist movement in physical metres")
    need(manual_isolation({"Body":0.,"Clone":0.},True,0.,guard)["manual_waist_isolated"],"No Manual waist movement")
    need(not manual_isolation({"Body":0.,"Clone":0.},True,.004,guard)["manual_waist_isolated"],"Manual waist movement rejected despite stationary Body")
    need(not manual_isolation({"Body":.004,"Clone":0.},True,0.,guard)["body_parent_unchanged"],"Manual Body motion cannot pass isolation")
    need(not manual_isolation({"Body":0.},False,0.,guard)["manual_waist_isolated"],"Changed upstream matrix cannot pass")
    for ids in ([],[0,0],[3]):
        try: waist_follow(l,l,n,ids,1.)
        except RuntimeError: pass
        else: raise RuntimeError("Missing/ambiguous waist IDs must fail")
    return {"passed":True,"focused_controls":8,"frozen_continuous_controls":prior,"native_run":False,"accepted":False}


def main(args):
    if args.pure_checks: print(json.dumps(pure_checks())); return 0
    import bpy
    from mathutils import Quaternion
    need(bpy.app.background and bpy.app.version[:2]==(5,1) and not bpy.data.filepath and "--factory-startup" in sys.argv
         and "--disable-autoexec" in sys.argv and "--threads" in sys.argv and sys.argv[sys.argv.index("--threads")+1]=="1","Empty leased Blender5.1 factory/disable-autoexec/threads1 only")
    sys.dont_write_bytecode=True; static=load_static(); read=static.load_coverage()
    need(sha(read.INPUT)==read.INPUT_SHA and sha(read.INSTALL)==read.INSTALL_SHA,"Exact7ac installation input changed")
    for name,value in read.PINS.items(): need(sha(HERE/name)==value,"Frozen dependency changed: "+name)
    workflow=read.load("verify_actual_surface_workflow.py"); same=read.load("verify_actual_same_frame_pose.py")
    qa,diag,addon,surface=workflow.load_dependencies()
    args.input,args.install_report=read.INPUT.resolve(),read.INSTALL.resolve()
    args.expected_surface_sha,args.expected_worker_sha=read.SURFACE_SHA,read.WORKER_SHA
    artist=Path(json.loads(read.INSTALL.read_text(encoding="utf-8"))["artist_path"]).resolve()
    report={"prepared_only_source":True,"native_completed":False,"accepted":False,"artist_saved":False,
        "completion_definition":"Endpoints, synthetic input readback, steps, target residual/quality/crossings, six renders and restoration protection; all artistic acceptance remains false",
        "scope":"Private synthetic endpoint-world-vertex interpolation only, not existing author Action or actual intermediate bone motion. No original time advance or artist application.",
        "input_before":qa.file_state(read.INPUT),"artist_before":qa.file_state(artist),"source_before":diag.source_manifest(),
        "script_sha256":sha(Path(__file__)),"continuous_helper_sha256":CONTINUOUS_SHA,"coverage_helper_sha256":COVERAGE_SHA,"static_helper_sha256":STATIC_SHA,"official_interfaces":OFFICIAL,"pins":read.PINS,"pure_checks":pure_checks(),"checks":[]}
    args.output.mkdir(); destination=args.output/"body_follow_contact_preview.json"
    ids={"objects":[],"meshes":[],"collections":[],"scenes":[],"keys":[],"actions":[]}; protection=None; home=None; probe=None; started=time.perf_counter()
    def budget(): need(time.perf_counter()-started<args.max_seconds,"Private static-preview time budget exhausted; no acceptance")
    def write(): destination.write_text(json.dumps(diag.json_content(report),indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    try:
        source_name=workflow.motion_input_gate(args,report,qa,diag); addon.register()
        need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(read.INPUT),load_ui=False,use_scripts=False),"Exact input open failed")
        need(Path(bpy.data.filepath).resolve()==read.INPUT.resolve(),"Input native path differs")
        source,rig,_=qa.owned_source(source_name); protection=qa.Protection()
        record,rig,actual,old_cloth,neutral=workflow.motion_objects(source,qa,surface); home=bpy.context.scene
        report["saved_cache_preflight"]=qa.saved_cache_preflight(source,record); need(report["saved_cache_preflight"]["allowed"],"Unsafe saved cache refused before mutation")
        report["author_pose"]=qa.digest(same.pose_checkpoint(rig,qa)); report["author_playback"]=qa.digest(same.playback_state(qa)); report["author_frame"]=[home.frame_current,home.frame_subframe]
        for i,action in enumerate(protection.action_refs): home[f"CD_QA_AuthorAction_{i:04d}"]=action
        candidate=args.output/"scenes/Cosha_Body_Follow_Contact_Candidate.blend"; qa.save_candidate(candidate,read.INPUT)
        home.tool_settings.use_keyframe_insert_auto=False; report["animation_backup"]=qa.backup_animation(home,list(bpy.data.objects)+list(bpy.data.shape_keys),protection.action_refs)
        qa.skirt._activate(bpy.context,rig,"POSE"); qa.public_switch(bpy.ops.character_designer.body_ik_fk_switch,mode="FK")
        legs,axes,height=qa.body_inputs(rig,record); body,report["registered_body"]=qa.registered_body(bpy.context,rig,args)
        need(body is not None and report["registered_body"]["measured"] and body.name==record["physics"]["surface"]["body"],"Exact registered Body absent")
        qa.tuning.apply(bpy.context,(source,),mode="AUTOMATIC"); home.frame_start,home.frame_end=1,2
        old_cloth.point_cache.frame_start,old_cloth.point_cache.frame_end=1,2
        settings=bpy.context.window_manager.character_designer_skirt; settings.source,settings.use_scene_range=source,True
        qa.save_candidate(candidate,read.INPUT); cache_dir=args.output/"source_private_cache"; cache_dir.mkdir()
        old_cloth.point_cache.filepath=str(cache_dir); old_cloth.point_cache.use_library_path=False; old_cloth.point_cache.use_disk_cache=True
        need(not old_cloth.point_cache.use_external and Path(bpy.path.abspath(old_cloth.point_cache.filepath)).resolve()==cache_dir.resolve(),"Original source cache ownership not private")
        qa.public_switch(bpy.ops.character_designer.dress_motion_reset); home.frame_set(1); bpy.context.view_layer.update()
        graph=bpy.context.evaluated_depsgraph_get(); meters=float(home.unit_settings.scale_length)
        need(math.isfinite(meters) and meters>0. and len(record["physics"]["colliders"])==4,"Physical units or exact3proxy+Body collider inventory missing")
        endpoints={}; endpoints_evidence={}; attachments={}
        def capture(label):
            need(home.frame_current==1 and home.frame_subframe==0.,"Original frame/subframe changed during endpoint capture")
            graph=bpy.context.evaluated_depsgraph_get(); record=qa.skirt.read_record(source)
            native={"O3040":read.native_mesh(source,graph,diag),"RegisteredBody":read.native_mesh(body,graph,diag)}
            for name in record["physics"]["colliders"]: native[name]=read.native_mesh(bpy.data.objects[name],graph,diag)
            evaluated=rig.evaluated_get(graph); keys=source.data.shape_keys
            endpoints[label]=native; endpoints_evidence[label]={"frame":home.frame_current,"subframe":home.frame_subframe,
                "rig_world":diag.matrix(evaluated.matrix_world),"native_pose_matrices":{p.name:diag.matrix(p.matrix) for p in evaluated.pose.bones},
                "manual_matrix_basis":diag.matrix(rig.pose.bones[record["controls"]["hem"]].matrix_basis),
                "source_key_values":[] if keys is None else [{"name":k.name,"value":k.value,"mute":k.mute} for k in keys.key_blocks],
                "bounds":diag.framing(rig,record,graph)}
            attachments[label]=native_attachment(source,rig,actual,neutral,body,record,old_cloth,graph,read,diag,surface,same,qa,bpy)
            return native
        initial_body=capture("N")["RegisteredBody"]; posed=rig.evaluated_get(graph); knee_before=posed.matrix_world@posed.pose.bones[legs["L"]["chain"][1]].head
        thigh=rig.pose.bones[legs["L"]["chain"][0]]; need(not any(thigh.lock_rotation) and not(thigh.lock_rotations_4d and thigh.lock_rotation_w),"Actual thigh locked")
        base=thigh.matrix_basis.to_quaternion().copy(); thigh.rotation_mode="QUATERNION"; thigh.rotation_quaternion=base@Quaternion(axes[thigh.name],.55); rig.update_tag(refresh={"OBJECT"}); bpy.context.view_layer.update()
        leg_surface=capture("L")["O3040"]
        control=rig.pose.bones[record["controls"]["hem"]]; same.unoccupied_handle(rig,control); original_control=control.matrix.copy()
        direction=rig.matrix_world.to_3x3().col[0].normalized(); step=float(record["fit"]["height_world"])*.04; posed=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        hem=posed.matrix_world@posed.pose.bones[control.name].matrix.translation
        candidates=[(side,(posed.matrix_world@posed.pose.bones[item["chain"][1]].head-hem).dot(direction)) for side,item in legs.items()]
        candidates=[item for item in candidates if item[1]<0.]; need(candidates and step>0.,"No measured reverse-knee target; refused guessing")
        side,projection=min(candidates,key=lambda item:abs(item[1])); offset=max(2.*step,abs(projection)+step)
        target=original_control.copy(); target.translation-=rig.matrix_world.to_3x3().inverted()@(direction*offset)
        local=rig.convert_space(pose_bone=control,matrix=target,from_space="POSE",to_space="LOCAL")
        need(not any(locked and abs(local.translation[i]-control.matrix_basis.translation[i])>1.e-10 for i,locked in enumerate(control.lock_location)),"Hem lock would be bypassed")
        control.matrix_basis=local; rig.update_tag(refresh={"OBJECT"}); bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get()
        record=qa.skirt.read_record(source); native=capture("T")
        original=native["O3040"]; waist_group=source.vertex_groups.get(record["controls"]["waist"])
        waist=None if waist_group is None else waist_group.index
        fixed=[] if waist is None else [i for i,row in enumerate(original["weights"]) if next((item["weight"] for item in row if item["index"]==waist),0.)>=.999]
        # All N/L/T and upstream/body-attachment data are persisted before unified geometry gates.
        endpoint_file=args.output/"native_endpoints.json"
        endpoint_file.write_text(json.dumps(diag.json_content({"frame":1,"units_to_metres":meters,"endpoints":endpoints,
            "evidence":endpoints_evidence,"attachments":attachments,"fixed160":fixed,"accepted":False}),indent=2,allow_nan=False),encoding="utf-8")
        report["native_endpoint_file"]={"path":str(endpoint_file),"sha256":sha(endpoint_file),"all_N_L_T_captured_before_gates":True}; write()
        clone_name=record["physics"]["colliders"][-1]; need(record["physics"]["surface"]["roles"]["BODY_ATTACHMENT"]==[clone_name],"Actual clone identity differs")
        posed=rig.evaluated_get(graph); knee_after=posed.matrix_world@posed.pose.bones[legs["L"]["chain"][1]].head; hem_after=posed.matrix_world@posed.pose.bones[control.name].matrix.translation
        need(initial_body["native_vertex_face_edge_sha256"]==native["RegisteredBody"]["native_vertex_face_edge_sha256"] and leg_surface["native_vertex_face_edge_sha256"]==native["O3040"]["native_vertex_face_edge_sha256"],"Actual Body/O point correspondence changed")
        body_delta=max((a-b).length*meters for a,b in zip(initial_body["points"],native["RegisteredBody"]["points"]))
        manual_delta=max((a-b).length*meters for a,b in zip(leg_surface["points"],native["O3040"]["points"]))
        need((knee_after-knee_before).length*meters>height*.01*meters and min(body_delta,manual_delta,(hem_after-hem).length*meters)>qa.geometry_guard(meters),"Actual leg/Hem input swallowed")
        report["actual_input"]={"frame":home.frame_current,"thigh":thigh.name,"angle_rad":.55,"hem":control.name,"target_leg":side,"reverse_offset_world":offset,"knee_delta_m":(knee_after-knee_before).length*meters,"body_delta_m":body_delta,"hem_delta_m":(hem_after-hem).length*meters,"manual_O_delta_m":manual_delta,"confirmed":True}
        report["body_collision_comparison"]=read.body_collision_comparison(native["RegisteredBody"],native[clone_name],meters)
        report["input_visibility"]=read.visibility_evidence([bpy.data.objects[mesh["object"]] for mesh in native.values()],old_cloth,home)
        bounds=diag.framing(rig,record,graph)
        need(len(original["points"])==3040 and original["weights_complete"] and waist is not None,"Exact O3040/native weights missing")
        need(len(fixed)==160 and PIN not in {row["name"] for row in original["native_group_mapping"]},"Exactly160 hard-waist IDs or independent Pin name missing")
        original["free_indices"]=[i for i in range(3040) if i not in set(fixed)]
        report["endpoint_crossings"]={}
        report["native_input_guard"]=readback_guard((point for meshes in endpoints.values() for mesh in meshes.values() for point in mesh["points"]),meters)
        input_guard=report["native_input_guard"]["metres"]
        report["public_motion_geometry_guard_m"]=qa.geometry_guard(meters)
        report["endpoint_identity"]={}; report["endpoint_waist160_world_movement_from_N"]={}
        report["waist_follow_policy"]="Measured N-to-L Body-follow movement is allowed and disclosed. Hard160 precision is relative to each CURRENT native target; Manual L-to-T may not move Body/parents/waist. Safe-rest-N displacement is diagnostic, never a fixed-pass."
        report["endpoint_upstream_deltas"]={}
        for first,last in (("N","L"),("N","T"),("L","T")):
            report["endpoint_upstream_deltas"][first+"_to_"+last]={"O3040_waist160":residual(endpoints[last]["O3040"]["points"],endpoints[first]["O3040"]["points"],fixed,meters),
                "raw_inputs":{name:{"all800":residual(attachments[last]["raw_inputs"][name]["points"],attachments[first]["raw_inputs"][name]["points"],list(range(800)),meters),
                    "raw80_ring0":residual(attachments[last]["raw_inputs"][name]["points"],attachments[first]["raw_inputs"][name]["points"],attachments[last]["body_attachment"]["ring0_raw_ids"],meters)} for name in ("C800","H0800")}}
        unchanged=(attachments["L"]["object_frames"]==attachments["T"]["object_frames"] and attachments["L"]["upstream_waist_bones"]==attachments["T"]["upstream_waist_bones"])
        report["manual_waist_isolation"]=manual_isolation({name:max(point_delta(endpoints["L"][name]["points"],endpoints["T"][name]["points"],meters)) for name in ("RegisteredBody",clone_name)},
            unchanged,report["endpoint_upstream_deltas"]["L_to_T"]["O3040_waist160"]["maximum_m"],input_guard)
        report["raw80_attachment_all_endpoints_observed"]=all(row["body_attachment"]["raw80_body_attachment_observed"] for row in attachments.values()); write()
        need(report["raw80_attachment_all_endpoints_observed"],"Raw80/C800/H0800 BodyAttachment native evidence incomplete")
        need(report["manual_waist_isolation"]["body_parent_unchanged"],"Manual L-to-T changed actual Body/upstream parent matrices; refused")
        need(report["manual_waist_isolation"]["manual_waist_isolated"],"Manual L-to-T moved final160 waist beyond unchanged readback micro-budget; refused")
        for label,meshes in endpoints.items():
            for name,mesh in meshes.items():
                base=endpoints["N"][name]
                exact=all(mesh[field]==base[field] for field in ("native_vertex_index_order","edges","faces","weights","native_group_mapping"))
                report["endpoint_identity"][label+":"+name]={"native_index_edges_faces_groups_weights_exact":exact,"triangulation_changed":mesh["triangles"]!=base["triangles"]}
                need(exact,"Endpoint native identity changed: "+label+":"+name)
            points=meshes["O3040"]["points"]; report["endpoint_waist160_world_movement_from_N"][label]=residual(points,endpoints["N"]["O3040"]["points"],fixed,meters)
            meshes["O3040"]["free_indices"]=original["free_indices"]; band=endpoints_evidence[label]["bounds"]
            epsilon=max(1.e-8,(band["upper"]-band["lower"])*1.e-6)
            report["endpoint_crossings"][label]={name:diag.triangle_crossings(meshes["O3040"],mesh,band,args.triangle_pair_limit,epsilon)
                for name,mesh in meshes.items() if name!="O3040"}
        for name in ("RegisteredBody",clone_name):
            observed=report["endpoint_crossings"]["N"][name]
            need(observed.get("status")=="measured" and observed.get("actual_crossing_pair_count")==0,
                 "Native N lacks measured zero actualBody crossings; no safe-start hypothesis")
        report["safe_start_scope"]="Measured zero finite triangle crossings in registered waist-knee band only. Open Body/boundary/coplanar/degenerate pairs remain Unknown; no complete inside/outside proof."
        manual_motion=point_delta(endpoints["L"]["O3040"]["points"],original["points"],meters)
        influenced=[i for i,value in enumerate(manual_motion) if value>input_guard]; outside=[i for i,value in enumerate(manual_motion) if value<=input_guard]
        report["measured_manual_region"]={"criterion":"Actual L-to-T native same-index displacement exceeds native input guard; no bone/group-name guess", "affected_ids":influenced,"outside_ids":outside,"per_vertex_manual_motion_m":manual_motion,"accepted":False}
        need(influenced,"Actual Manual target has no measurable influence")
        surface.validate(source,rig,record); report["canonical_validation_before_private_scene"]=True
        budget(); private=bpy.data.scenes.new("Body Follow Contact Preview"); ids["scenes"].append(private)
        private.frame_start,private.frame_end=1,args.steps+1; private.gravity=(0.,0.,0.); private.use_gravity=False; private.unit_settings.scale_length=meters
        private.render.fps,private.render.fps_base=home.render.fps,home.render.fps_base
        collision=bpy.data.collections.new("Continuous Native Collision"); ids["collections"].append(collision); private.collection.children.link(collision)
        collision.hide_viewport=collision.hide_render=False
        dress=static.freeze(endpoints["N"]["O3040"],"Continuous Dress",private.collection,ids,bpy)
        pin=dress.vertex_groups.new(name=PIN); pin.add(fixed,1.,"REPLACE"); pin.add(original["free_indices"],SOFT_WEIGHT,"REPLACE")
        animated={"O3040":dress}; animations={"O3040":animate(dress,*(endpoints[x]["O3040"] for x in ("N","L","T")),args.steps,ids,bpy,qa)}
        for name in ["RegisteredBody"]+list(record["physics"]["colliders"]):
            obj=static.freeze(endpoints["N"][name],"Continuous "+name,private.collection if name=="RegisteredBody" else collision,ids,bpy)
            animated[name]=obj; animations[name]=animate(obj,*(endpoints[x][name] for x in ("N","L","T")),args.steps,ids,bpy,qa)
            if name!="RegisteredBody":
                obj.modifiers.new("Continuous Collision","COLLISION"); surface._copy_scalars(bpy.data.objects[name].collision,obj.collision)
        probe=bpy.data.objects.new("Continuous Pre-Cloth Input",dress.data); ids["objects"].append(probe); private.collection.objects.link(probe)
        for group in dress.vertex_groups:
            made=probe.vertex_groups.new(name=group.name); need(made.index==group.index,"Shared pre-Cloth input group mapping differs"); made.lock_weight=group.lock_weight
        probe.hide_render=True
        cloth=dress.modifiers.new("Continuous Contact Cloth","CLOTH"); surface._copy_scalars(old_cloth.settings,cloth.settings)
        surface._copy_scalars(old_cloth.collision_settings,cloth.collision_settings); surface._copy_scalars(old_cloth.settings.effector_weights,cloth.settings.effector_weights)
        cloth.settings.vertex_group_mass=pin.name; cloth.settings.rest_shape_key=None; cloth.settings.use_dynamic_mesh=False
        cloth.settings.effector_weights.gravity=0.; cloth.collision_settings.collection=collision
        need(cloth.collision_settings.use_collision and cloth.settings.pin_stiffness==1.,"Copied contact or explicit native pin stiffness differs")
        cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step=1,args.steps+1,1
        need(not cloth.point_cache.is_baked and not cloth.point_cache.use_external,"New private cache unexpectedly sealed/external")
        need(bpy.context.window is not None,"Native background Window unavailable for private Scene graph")
        bpy.context.window.scene=private; private.frame_set(1); bpy.context.view_layer.update()
        need(bpy.context.scene==private and source.name not in bpy.context.view_layer.objects,"Original scene leaked into synthetic graph")
        for prop in cloth.settings.bl_rna.properties:
            if prop.identifier.startswith("vertex_group_"):
                name=getattr(cloth.settings,prop.identifier); need(not name or dress.vertex_groups.get(name) is not None,"Copied Cloth group unavailable: "+prop.identifier)
        qa.save_candidate(candidate,read.INPUT); owned_cache=args.output/"continuous_private_cache"; owned_cache.mkdir()
        cloth.point_cache.filepath=str(owned_cache); cloth.point_cache.use_library_path=False; cloth.point_cache.use_disk_cache=True
        need(Path(bpy.path.abspath(cloth.point_cache.filepath)).resolve()==owned_cache.resolve(),"Continuous cache escaped private output")
        report["parameters"]={"cloth":surface._rna(cloth.settings),"collision":surface._rna(cloth.collision_settings),"effectors":surface._rna(cloth.settings.effector_weights),
            "units_to_metres":meters,"fps":private.render.fps,"fps_base":private.render.fps_base,"hard160":fixed,"soft_goal_raw_weight":SOFT_WEIGHT,
            "soft_goal_after_native_pow4":SOFT_WEIGHT**4,"soft_goal_hypothesis":"Unvalidated fractional positional goal; residual determines actual tracking. No hard forcing of penetrating Manual T.",
            "rest_policy":"Safe N at initialisation, rest_shape_key=None/use_dynamic_mesh=False. Input ShapeKeys change xconst targets, not xrest; soft goal force is native.",
            "synthetic_path":"World-vertex piecewise linear N->L->T, half steps per phase, fresh owned ShapeKey Action. Not original author Action or actual intermediate skeletal pose.",
            "hard_waist_policy":"Weight1 targets follow observed pre-Cloth input each synthetic step; allowed Body-follow world motion is measured separately. L-to-T native Manual isolation must hold.",
            "private_steps":args.steps,"nominal_path_seconds":args.steps*private.render.fps_base/private.render.fps,"source_original_frame_held":1}
        report["private_cache_policy"]="Only fresh candidate source/preview caches, no free_bake; exact owned ID removal releases runtime. Private disk evidence remains; artist/input cache refused if sealed/external/disk."
        report["owned_receipt"]={name:[{"name":item.name,"pointer":item.as_pointer()} for item in items] for name,items in ids.items()}
        report["owned_synthetic_action_slots"]={name:item["slot"] for name,item in animations.items()}
        report["private_visibility"]=read.visibility_evidence(ids["objects"],cloth,private)
        need(not collision.hide_viewport and not collision.hide_render and not any(obj.hide_get(view_layer=bpy.context.view_layer) or obj.hide_viewport or obj.hide_render for obj in animated.values()),"Private simulated/collision geometry hidden")
        report["path_readback"]=[]; report["samples"]={}; initial=None; midpoint=None; final=None
        hard_ids=set(fixed)
        for frame in range(1,args.steps+2):
            budget(); private.frame_set(frame); bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get(); weights=path_weights(frame,args.steps)
            need(probe.data==dress.data and len(probe.modifiers)==0 and probe.data.shape_keys.animation_data.action==animations["O3040"]["action"],"Exact shared pre-Cloth input unavailable")
            observed={"O3040":read.native_mesh(probe,graph,diag)}
            for name,obj in animated.items():
                if name!="O3040": observed[name]=read.native_mesh(obj,graph,diag)
            row={"frame":frame,"synthetic_leg_weight":weights[0],"synthetic_manual_weight":weights[1],"objects":{}}
            for name,mesh in observed.items():
                expected=path_points(*(endpoints[x][name]["points"] for x in ("N","L","T")),weights)
                maximum=max(point_delta(mesh["points"],expected,meters)); need(maximum<=input_guard,"Native path input deviates from captured endpoints: "+name)
                base=endpoints["N"][name]; need(mesh["faces"]==base["faces"] and mesh["edges"]==base["edges"] and mesh["native_vertex_index_order"]==base["native_vertex_index_order"],"Synthetic input topology/index changed")
                filtered=[[item for item in items if item["index"]!=pin.index] for items in mesh["weights"]] if name=="O3040" else mesh["weights"]
                need(filtered==base["weights"],"Synthetic input original native weights changed")
                mapping=[item for item in mesh["native_group_mapping"] if item["index"]!=pin.index] if name=="O3040" else mesh["native_group_mapping"]
                need(mapping==base["native_group_mapping"],"Synthetic input original native group mapping changed")
                actual_keys=animations[name]["keys"].evaluated_get(graph)
                key_values=[actual_keys.key_blocks[block.name].value for block in animations[name]["blocks"]]
                row["objects"][name]={"actual_world_points_sha256":read.digest([list(x) for x in mesh["points"]]),"expected_world_points_sha256":read.digest(expected),
                    "maximum_input_error_m":maximum,"native_triangles_sha256":mesh["native_triangulation_sha256"],
                    "triangulation_changed_from_N":mesh["triangles"]!=base["triangles"],"observed_evaluated_owned_key_values":key_values}
                need(all(abs(actual-value)<=1.e-6 for actual,value in zip(key_values,weights)),"Native evaluated synthetic key values differ from explicit path")
            report["path_readback"].append(row)
            cloth_mesh=read.native_mesh(dress,graph,diag)
            need(cloth_mesh["faces"]==original["faces"] and cloth_mesh["edges"]==original["edges"] and cloth_mesh["native_vertex_index_order"]==original["native_vertex_index_order"],"Simulated cloth topology/index changed")
            need(all(math.isfinite(float(x)) for point in cloth_mesh["points"] for x in point),"Cloth produced nonfinite points")
            need([[item for item in items if item["index"]!=pin.index] for items in cloth_mesh["weights"]]==original["weights"],"Simulated original weights changed")
            need([item for item in cloth_mesh["native_group_mapping"] if item["index"]!=pin.index]==original["native_group_mapping"],"Simulated original group mapping changed")
            need(len([items for items in cloth_mesh["weights"] if any(item["index"]==pin.index and item["weight"]==1. for item in items)])==160,"Private hard-goal inventory differs")
            need(all(next((item["weight"] for item in items if item["index"]==pin.index),None)==(1. if i in hard_ids else SOFT_WEIGHT) for i,items in enumerate(cloth_mesh["weights"])),"Native private hard/soft-goal weights differ from declared hypothesis")
            row["hard_waist_trajectory"]=waist_follow(cloth_mesh["points"],observed["O3040"]["points"],endpoints["N"]["O3040"]["points"],fixed,meters)
            need(row["hard_waist_trajectory"]["relative_pin_deviation"]["maximum_m"]<=input_guard,"Native hard160 deviates from CURRENT Body-follow input trajectory")
            if frame in (1,args.steps//2+1,args.steps+1):
                label="initial" if frame==1 else "leg" if frame==args.steps//2+1 else "final"
                bodies={name:mesh for name,mesh in observed.items() if name!="O3040"}; proxies={name:animated[name] for name in record["physics"]["colliders"][:-1]}
                cloth_mesh,crossings=static.sample(dress,bodies,bounds,fixed,graph,read,diag,args,qa,proxies,meters)
                if initial is None: initial=cloth_mesh
                if label=="leg": midpoint=cloth_mesh
                if label=="final": final=cloth_mesh
                report["samples"][label]={"frame":frame,"crossings":crossings,"hard_waist_trajectory":row["hard_waist_trajectory"],
                    "safe_rest_quality_waist_scope":"maximum_hard_waist_displacement_m below is world movement from safe-rest N, not a pin pass. See hard_waist_trajectory.relative_pin_deviation for precision.","quality_relative_safe_rest_N":static.metrics(endpoints["N"]["O3040"]["points"],cloth_mesh["points"],original["edges"],cloth_mesh["triangles"],fixed,meters),
                    "quality_relative_current_requested_input":static.metrics(observed["O3040"]["points"],cloth_mesh["points"],original["edges"],cloth_mesh["triangles"],fixed,meters),
                    "normal_diagnostics_relative_current_target":normal_diagnostics(observed["O3040"]["points"],cloth_mesh["points"],cloth_mesh["triangles"]),
                    "target_residual_all":residual(cloth_mesh["points"],observed["O3040"]["points"],list(range(3040)),meters),
                    "target_residual_manual_region":residual(cloth_mesh["points"],observed["O3040"]["points"],influenced,meters),
                    "target_residual_outside_manual_region":residual(cloth_mesh["points"],observed["O3040"]["points"],outside,meters),
                    "outside_manual_region_displacement_from_N":residual(cloth_mesh["points"],endpoints["N"]["O3040"]["points"],outside,meters),
                    "body_collision_comparison":read.body_collision_comparison(bodies["RegisteredBody"],bodies[clone_name],meters)}
                (args.output/(label+"_native_sample.json")).write_text(json.dumps(diag.json_content({"observed_input_and_bodies":observed,"simulated_cloth":cloth_mesh,"units_to_metres":meters}),indent=2,allow_nan=False),encoding="utf-8")
                write(); print("Body-follow private sample:"+label+" frame"+str(frame),flush=True)
        need(initial is not None and midpoint is not None and final is not None,"Required initial/leg/final sample absent")
        report["final_target_residual"]=residual(final["points"],original["points"],list(range(3040)),meters)
        report["hard_pin_trajectory_precision_verified"]=all(row["hard_waist_trajectory"]["relative_pin_deviation"]["maximum_m"]<=input_guard for row in report["path_readback"])
        report["hard_pin_trajectory_precision_scope"]="All steps: current simulated hard160 versus observed current pre-Cloth target, physical micro-budget unchanged. World Body-follow movement is not hidden or counted as a fixed-location pass."
        report["manual_phase_motion_diagnostic"]={"manual_region_final_minus_leg":residual(final["points"],midpoint["points"],influenced,meters),
            "outside_region_final_minus_leg":residual(final["points"],midpoint["points"],outside,meters),
            "scope":"Motion during synthetic Manual phase, potentially mixed with collision/inertia; not a causal Manual-preservation proof.","accepted":False}
        report["render"]={"requested":True,"visual_quality_accepted":False,"comparison":"Both snapshots use the same native target RegisteredBody; requested T versus continuous simulated final, not safe neutral versus target."}
        for label,mesh in (("requested_target",original),("continuous_final",final)):
            budget(); folder=args.output/label; folder.mkdir()
            report["render"][label]=diag.native_render(SimpleNamespace(frame=args.steps+1,output=folder),mesh,native["RegisteredBody"],bounds)
            report["render"][label].update(source_author_frame=1,private_synthetic_frame=args.steps+1,
                provenance="Requested T is the actual captured source frame1 endpoint; continuous final is the private synthetic Cloth result. Both use the same captured target Body. Private frame number does not identify any author Action result.")
        report["six_native_images_collected"]=all(report["render"][label].get("success") and set(report["render"][label].get("views",{}))=={"front","side","back"} for label in ("requested_target","continuous_final"))
        need(report["six_native_images_collected"],"Six native target/final renders not collected; incomplete preview")
        report["actual_body_crossing_evidence_collected"]=all(row["crossings"]["strict_crossings"][name].get("status")=="measured" for row in report["samples"].values() for name in ("RegisteredBody",clone_name))
        need(report["actual_body_crossing_evidence_collected"],"Actual Body/clone crossings could not be measured; incomplete preview")
        report["native_completed"]=True; report["source_frame_after_private_steps"]=home.frame_current
        need(home.frame_current==1,"Original author/Cloth timeline advanced")
    except Exception as error: report["native_completed"]=False; report["error"]={"reason":str(error),"traceback":traceback.format_exc()}
    finally:
        try:
            report["owned_receipt_at_cleanup"]={name:[{"name":item.name,"pointer":item.as_pointer()} for item in items] for name,items in ids.items()}
            if home is not None and bpy.context.window is not None: bpy.context.window.scene=home
            key_receipt=[(item.as_pointer(),item.name) for item in ids["keys"]]
            action_receipt=[(item.as_pointer(),item.name) for item in ids["actions"]]
            if probe is not None:
                need(probe in ids["objects"] and probe.data in ids["meshes"],"Shared pre-Cloth probe is not exactly owned")
                bpy.data.objects.remove(probe,do_unlink=True)
            for pointer,name in key_receipt:
                keys=bpy.data.shape_keys.get(name); need(keys is not None and keys.as_pointer()==pointer,"Owned Key identity changed before clearing")
                owners=bpy.data.user_map(subset={keys}).get(keys,set())
                need(len(owners)==1,"Owned Key has nonunique/foreign native owners")
                mesh=next(iter(owners)); need(mesh in ids["meshes"] and mesh.shape_keys==keys and mesh.users==1,"Owned Key does not belong to a unique owned Mesh")
                objects=[obj for obj in ids["objects"] if obj is not probe and obj.data==mesh]
                need(len(objects)==1,"Owned Key clearing requires its exact one Mesh object")
                objects[0].shape_key_clear(); need(mesh.shape_keys is None,"Native owned Key clearing did not detach Mesh")
                remaining=bpy.data.shape_keys.get(name)
                if remaining is not None:
                    need(remaining.as_pointer()==pointer and not bpy.data.user_map(subset={remaining}).get(remaining,set()),"Owned Key acquired foreign users during clearing")
                    bpy.data.batch_remove(ids=(remaining,)); need(bpy.data.shape_keys.get(name) is None,"Exact owned Key remains")
            for obj in reversed(ids["objects"]):
                if obj is not probe: bpy.data.objects.remove(obj,do_unlink=True)
            for scene in ids["scenes"]: bpy.data.scenes.remove(scene)
            for collection in ids["collections"]: bpy.data.collections.remove(collection)
            for mesh in ids["meshes"]:
                need(mesh.users==0,"New preview mesh still referenced; no broad orphan clearing")
                bpy.data.meshes.remove(mesh)
            report["owned_keys_detached_and_removed"]=not any(item.as_pointer()==pointer for item in bpy.data.shape_keys for pointer,_ in key_receipt)
            need(report["owned_keys_detached_and_removed"],"Owned preview Key remains after exact clearing/Mesh removal")
            for action in ids["actions"]:
                need(action.users==0,"Owned preview Action still referenced; no forced unlink")
                bpy.data.actions.remove(action)
            need(not any(item.as_pointer()==pointer for item in bpy.data.actions for pointer,_ in action_receipt),"Owned preview Action remains")
            report["only_owned_private_ids_removed"]=True
        except Exception as error: report["cleanup_error"]=str(error); report["native_completed"]=False
        if protection is not None:
            try:
                source,rig,_=qa.owned_source(report["install_input"]["source"]); surface.validate(source,rig,qa.skirt.read_record(source)); report["raw_before_reload"]=protection.verify()
            except Exception as error:
                report["pre_reload_protection_error"]=str(error); report["native_completed"]=False
            try:
                need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(read.INPUT),load_ui=False,use_scripts=False),"Exact input reload failed")
                need(Path(bpy.data.filepath).resolve()==read.INPUT.resolve(),"Restored native path differs")
                source,rig,_=qa.owned_source(report["install_input"]["source"]); report["raw_after_reload"]=protection.verify()
                report["author_pose_restored"]=qa.digest(same.pose_checkpoint(rig,qa))==report["author_pose"]
                report["author_playback_restored"]=qa.digest(same.playback_state(qa))==report["author_playback"]
                report["author_frame_restored"]=[bpy.context.scene.frame_current,bpy.context.scene.frame_subframe]==report["author_frame"]
                report["native_completed"] &= report.get("raw_before_reload",{}).get("success",False) and report["raw_after_reload"]["success"] and all(report[key] for key in ("author_pose_restored","author_playback_restored","author_frame_restored"))
            except Exception as error: report["restore_error"]=str(error); report["native_completed"]=False
        report["input_disk_exact"]=qa.file_state(read.INPUT)==report["input_before"]; report["artist_disk_exact"]=qa.file_state(artist)==report["artist_before"]
        report["code_exact"]=diag.source_manifest()==report["source_before"] and sha(HERE/"verify_actual_body_proxy_coverage.py")==COVERAGE_SHA and all(sha(HERE/name)==value for name,value in read.PINS.items()) and sha(HERE/"prototype_static_final_cloth_relax.py")==STATIC_SHA and sha(HERE/"prototype_static_continuous_contact_preview.py")==CONTINUOUS_SHA and sha(Path(__file__))==report["script_sha256"]
        report["native_completed"] &= report["input_disk_exact"] and report["artist_disk_exact"] and report["code_exact"]
        report["ready_for_independent_evaluation"]=bool(report["native_completed"] and report.get("six_native_images_collected",False) and report.get("hard_pin_trajectory_precision_verified",False)); report["elapsed_seconds"]=time.perf_counter()-started; write()
        print(json.dumps({"native_completed":report["native_completed"],"accepted":False,"report":str(destination)}),flush=True)
    return 0 if report["native_completed"] else 2

if __name__=="__main__": raise SystemExit(main(arguments()))
