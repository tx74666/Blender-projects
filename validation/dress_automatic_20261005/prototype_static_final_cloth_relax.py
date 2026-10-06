"""PREPARED ONLY: private frozen-pose O3040 Cloth relaxation, never artist repair.

Root leases factory Blender 5.1 --background --disable-autoexec --threads 1.
Exact saved Cosha receives public FK/Automatic/Reset only in a private candidate.
Actual thigh .55 + reverse Hem geometry is frozen into a separate Scene; its
30 steps are unrelated to original Cloth/author action time. No bake/global
free, canonical edits, installation or accepted Body-volume/artistic result.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
COVERAGE_SHA="a232ae99e26a998f911c38efd1b95fcc45fb4c76ebd5d3a2c87bd8686196a055"
PIN="Static Waist Pin"

def need(ok,message):
    if not ok: raise RuntimeError(message)

def sha(path):
    result=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""): result.update(block)
    return result.hexdigest()

def load_coverage():
    path=HERE/"verify_actual_body_proxy_coverage.py"
    need(sha(path)==COVERAGE_SHA,"Frozen coverage helper changed")
    spec=importlib.util.spec_from_file_location("static_relax_read_helpers",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def metrics(before,after,edges,triangles,fixed,metres):
    def distance(a,b): return math.sqrt(math.fsum((float(x)-float(y))**2 for x,y in zip(a,b)))
    def area(points,t):
        a,b,c=(points[i] for i in t); u=[b[i]-a[i] for i in range(3)]; v=[c[i]-a[i] for i in range(3)]
        return .5*math.sqrt((u[1]*v[2]-u[2]*v[1])**2+(u[2]*v[0]-u[0]*v[2])**2+(u[0]*v[1]-u[1]*v[0])**2)
    need(len(before)==len(after) and all(math.isfinite(float(x)) for row in after for x in row),"Nonfinite or noncorresponding relaxation points")
    lengths=[distance(before[a],before[b]) for a,b in edges]; areas=[area(before,t) for t in triangles]
    edge_ratios=[distance(after[a],after[b])/base if base>1.e-12 else None for (a,b),base in zip(edges,lengths)]
    area_ratios=[area(after,t)/base if base>1.e-18 else None for t,base in zip(triangles,areas)]
    def extrema(values,ids):
        valid=[(value,i) for i,value in enumerate(values) if value is not None]
        return {"minimum":None if not valid else min(valid)[0],"maximum":None if not valid else max(valid)[0],
            "minimum_element":None if not valid else list(ids[min(valid)[1]]),"maximum_element":None if not valid else list(ids[max(valid)[1]]),
            "unresolved_degenerate_baseline":sum(value is None for value in values)}
    delta=[distance(a,b)*metres for a,b in zip(before,after)]
    return {"edge_ratios":extrema(edge_ratios,edges),"triangle_area_ratios_on_recorded_corner_triplets":extrema(area_ratios,triangles),
        "actual_areas_on_recorded_triplets_m2":{"minimum":min((area(after,t)*metres**2 for t in triangles),default=None),
            "maximum":max((area(after,t)*metres**2 for t in triangles),default=None)},
        "hard_waist_count":len(fixed),"maximum_hard_waist_displacement_m":max((delta[i] for i in fixed),default=None),
        "maximum_same_index_delta_m":max(delta,default=0.),"rms_same_index_delta_m":math.sqrt(math.fsum(x*x for x in delta)/len(delta)),
        "accepted":False,"scope":"Same-index frozen preview only; extreme shape ratios and degeneracy remain diagnostics, never artistic acceptance."}

def pure_checks():
    p=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]; edges=[(0,1),(1,2),(2,0)]; tri=[(0,1,2)]
    q=metrics(p,p,edges,tri,[0],.01)
    need(q["edge_ratios"]["minimum"]==1. and q["maximum_hard_waist_displacement_m"]==0.,"identity quality control")
    q=metrics(p,[(0.,0.,0.),(2.,0.,0.),(0.,1.,0.)],edges,tri,[1],.01)
    need(q["triangle_area_ratios_on_recorded_corner_triplets"]["maximum"]==2. and q["maximum_hard_waist_displacement_m"]==.01,"physical delta/area control")
    q=metrics(p,p,[(0,0)],[(0,0,0)],[0],1.)
    need(q["edge_ratios"]["unresolved_degenerate_baseline"]==1 and q["triangle_area_ratios_on_recorded_corner_triplets"]["minimum"] is None,"degenerate remains unresolved")
    return {"passed":True,"controls":3,"native_run":False}

def arguments():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path); parser.add_argument("--pure-checks",action="store_true")
    parser.add_argument("--render",action="store_true"); parser.add_argument("--max-seconds",type=float,default=180.)
    values=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:] if "--pure-checks" in sys.argv else []
    args=parser.parse_args(values)
    if args.pure_checks: return args
    need(args.output is not None,"Use one fresh private Validation output")
    args.output=args.output.resolve()
    need(args.output.is_relative_to(HERE) and args.output!=HERE and not args.output.exists(),"Refuse existing/non-Validation output")
    need(30.<=args.max_seconds<=180.,"Root lease maximum is 180 seconds")
    args.body_vertex_limit=100000; args.triangle_pair_limit=10000
    return args

def freeze(mesh,name,collection,ids,bpy):
    data=bpy.data.meshes.new(name+" Mesh"); ids["meshes"].append(data)
    data.from_pydata([list(point) for point in mesh["points"]],mesh["edges"],mesh["faces"]); data.update()
    obj=bpy.data.objects.new(name,data); ids["objects"].append(obj); collection.objects.link(obj)
    for item in sorted(mesh["native_group_mapping"],key=lambda row:row["index"]):
        group=obj.vertex_groups.new(name=item["name"])
        need(group.index==item["index"] and group.name==item["name"],"Native group identity changed while freezing")
        group.lock_weight=item["lock_weight"]
    for index,row in enumerate(mesh["weights"]):
        for item in row: obj.vertex_groups[item["index"]].add([index],item["weight"],"REPLACE")
    obj.hide_viewport=obj.hide_render=False  # New object's per-view-layer flag is read after its private Scene is active.
    return obj

def sample(obj,bodies,bounds,fixed,graph,read,diag,args,qa,proxy_objects,metres):
    mesh=read.native_mesh(obj,graph,diag); mesh["free_indices"]=[i for i in range(len(mesh["points"])) if i not in set(fixed)]
    epsilon=max(1.e-8,(bounds["upper"]-bounds["lower"])*1.e-6)
    result={"strict_crossings":{name:diag.triangle_crossings(mesh,body,bounds,args.triangle_pair_limit,epsilon) for name,body in bodies.items()},
        "closed_proxy_sampled_vertex_distance":{},"whole_body_separation_proven":False,"accepted":False}
    for name,proxy in proxy_objects.items():
        try:
            qa.physics._closed_collider(proxy)
            collider=qa.ClosedCollider(proxy,graph,epsilon,mesh=bodies[name])
            result["closed_proxy_sampled_vertex_distance"][name]={**qa.collision_metrics(mesh["points"],collider,metres,mesh["free_indices"]),
                "scope":"Existing closed-proxy convex/parity vertex diagnostic only; excludes open Body volume and complete triangle clearance", "accepted":False}
        except Exception as error: result["closed_proxy_sampled_vertex_distance"][name]={"status":"unknown","reason":str(error)}
    return mesh,result

def main(args):
    if args.pure_checks: print(json.dumps(pure_checks())); return 0
    import bpy
    from mathutils import Quaternion
    need(bpy.app.background and bpy.app.version[:2]==(5,1) and not bpy.data.filepath and "--factory-startup" in sys.argv
         and "--disable-autoexec" in sys.argv and "--threads" in sys.argv and sys.argv[sys.argv.index("--threads")+1]=="1","Empty leased Blender5.1 factory/disable-autoexec/threads1 only")
    sys.dont_write_bytecode=True; read=load_coverage()
    need(sha(read.INPUT)==read.INPUT_SHA and sha(read.INSTALL)==read.INSTALL_SHA,"Exact7ac installation input changed")
    for name,value in read.PINS.items(): need(sha(HERE/name)==value,"Frozen dependency changed: "+name)
    workflow=read.load("verify_actual_surface_workflow.py"); same=read.load("verify_actual_same_frame_pose.py")
    qa,diag,addon,surface=workflow.load_dependencies()
    args.input,args.install_report=read.INPUT.resolve(),read.INSTALL.resolve()
    args.expected_surface_sha,args.expected_worker_sha=read.SURFACE_SHA,read.WORKER_SHA
    artist=Path(json.loads(read.INSTALL.read_text(encoding="utf-8"))["artist_path"]).resolve()
    report={"prepared_only_source":True,"native_completed":False,"accepted":False,"artist_saved":False,
        "completion_definition":"30-step/end-point collection plus restoration protection only; residuals/shape/render may fail or remain Unknown; accepted is always false",
        "scope":"Frozen failing pose static-preview candidate only; no original Cloth/action timeline advances, artist application or Body-volume proof.",
        "input_before":qa.file_state(read.INPUT),"artist_before":qa.file_state(artist),"source_before":diag.source_manifest(),
        "script_sha256":sha(Path(__file__)),"coverage_helper_sha256":COVERAGE_SHA,"pins":read.PINS,"pure_checks":pure_checks(),"checks":[]}
    args.output.mkdir(); destination=args.output/"static_final_relax.json"
    ids={"objects":[],"meshes":[],"collections":[],"scenes":[]}; protection=None; home=None; started=time.perf_counter()
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
        candidate=args.output/"scenes/Cosha_Static_Final_Cloth_Candidate.blend"; qa.save_candidate(candidate,read.INPUT)
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
        initial_body=read.native_mesh(body,graph,diag); posed=rig.evaluated_get(graph); knee_before=posed.matrix_world@posed.pose.bones[legs["L"]["chain"][1]].head
        thigh=rig.pose.bones[legs["L"]["chain"][0]]; need(not any(thigh.lock_rotation) and not(thigh.lock_rotations_4d and thigh.lock_rotation_w),"Actual thigh locked")
        base=thigh.matrix_basis.to_quaternion().copy(); thigh.rotation_mode="QUATERNION"; thigh.rotation_quaternion=base@Quaternion(axes[thigh.name],.55); rig.update_tag(refresh={"OBJECT"}); bpy.context.view_layer.update()
        leg_surface=read.native_mesh(source,bpy.context.evaluated_depsgraph_get(),diag)
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
        record=qa.skirt.read_record(source); native={"O3040":read.native_mesh(source,graph,diag),"RegisteredBody":read.native_mesh(body,graph,diag)}
        for name in record["physics"]["colliders"]: native[name]=read.native_mesh(bpy.data.objects[name],graph,diag)
        clone_name=record["physics"]["colliders"][-1]; need(record["physics"]["surface"]["roles"]["BODY_ATTACHMENT"]==[clone_name],"Actual clone identity differs")
        posed=rig.evaluated_get(graph); knee_after=posed.matrix_world@posed.pose.bones[legs["L"]["chain"][1]].head; hem_after=posed.matrix_world@posed.pose.bones[control.name].matrix.translation
        need(initial_body["native_vertex_face_edge_sha256"]==native["RegisteredBody"]["native_vertex_face_edge_sha256"] and leg_surface["native_vertex_face_edge_sha256"]==native["O3040"]["native_vertex_face_edge_sha256"],"Actual Body/O point correspondence changed")
        body_delta=max((a-b).length*meters for a,b in zip(initial_body["points"],native["RegisteredBody"]["points"]))
        manual_delta=max((a-b).length*meters for a,b in zip(leg_surface["points"],native["O3040"]["points"]))
        need((knee_after-knee_before).length*meters>height*.01*meters and min(body_delta,manual_delta,(hem_after-hem).length*meters)>qa.geometry_guard(meters),"Actual leg/Hem input swallowed")
        report["actual_input"]={"frame":home.frame_current,"thigh":thigh.name,"angle_rad":.55,"hem":control.name,"target_leg":side,"reverse_offset_world":offset,"knee_delta_m":(knee_after-knee_before).length*meters,"body_delta_m":body_delta,"hem_delta_m":(hem_after-hem).length*meters,"manual_O_delta_m":manual_delta,"confirmed":True}
        report["body_collision_comparison"]=read.body_collision_comparison(native["RegisteredBody"],native[clone_name],meters)
        report["input_visibility"]=read.visibility_evidence([bpy.data.objects[mesh["object"]] for mesh in native.values()],old_cloth,home)
        bounds=diag.framing(rig,record,graph); original=native["O3040"]; waist=source.vertex_groups[record["controls"]["waist"]].index
        need(len(original["points"])==3040 and original["weights_complete"],"Exact O3040/native weights missing")
        fixed=[i for i,row in enumerate(original["weights"]) if next((item["weight"] for item in row if item["index"]==waist),0.)>=.999]
        need(len(fixed)==160 and PIN not in {row["name"] for row in original["native_group_mapping"]},"Exactly160 hard-waist IDs or independent Pin name missing")
        original["free_indices"]=[i for i in range(3040) if i not in set(fixed)]
        surface.validate(source,rig,record); report["canonical_validation_before_private_scene"]=True
        (args.output/"frozen_pose_native.json").write_text(json.dumps(diag.json_content({"frame":1,"units_to_metres":meters,"native_meshes":native,"bounds":bounds,"fixed160":fixed}),indent=2,allow_nan=False),encoding="utf-8")
        budget(); private=bpy.data.scenes.new("Static Final Cloth Preview"); ids["scenes"].append(private)
        private.frame_start,private.frame_end=1,31; private.gravity=(0.,0.,0.); private.use_gravity=False; private.unit_settings.scale_length=meters
        private.render.fps,private.render.fps_base=home.render.fps,home.render.fps_base
        collision=bpy.data.collections.new("Static Frozen Collision"); ids["collections"].append(collision); private.collection.children.link(collision)
        collision.hide_viewport=collision.hide_render=False; dress=freeze(original,"Static Final Dress",private.collection,ids,bpy)
        frozen_colliders={}
        for name in record["physics"]["colliders"]:
            obj=freeze(native[name],"Static "+name,collision,ids,bpy); obj.modifiers.new("Static Collision","COLLISION")
            surface._copy_scalars(bpy.data.objects[name].collision,obj.collision)
            frozen_colliders[name]=obj
        cloth=dress.modifiers.new("Static Final Cloth","CLOTH"); surface._copy_scalars(old_cloth.settings,cloth.settings)
        surface._copy_scalars(old_cloth.collision_settings,cloth.collision_settings); surface._copy_scalars(old_cloth.settings.effector_weights,cloth.settings.effector_weights)
        pin=dress.vertex_groups.new(name=PIN); pin.add(fixed,1.,"REPLACE"); cloth.settings.vertex_group_mass=pin.name
        cloth.settings.rest_shape_key=None; cloth.settings.use_dynamic_mesh=False; cloth.settings.effector_weights.gravity=0.
        cloth.collision_settings.collection=collision; need(cloth.collision_settings.use_collision,"Existing collision parameters disabled contact")
        cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step=1,31,1
        need(not cloth.point_cache.is_baked and not cloth.point_cache.use_external,"New private cache unexpectedly sealed/external")
        need(bpy.context.window is not None,"Native background Window unavailable for private Scene graph")
        bpy.context.window.scene=private; bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get()
        need(bpy.context.scene==private and source.name not in bpy.context.view_layer.objects,"Original scene leaked into static graph")
        preview=read.native_mesh(dress,graph,diag); need(preview["faces"]==original["faces"] and preview["edges"]==original["edges"] and preview["native_vertex_index_order"]==original["native_vertex_index_order"],"Native frozen topology/index changed")
        without_pin=[[item for item in row if item["index"]!=pin.index] for row in preview["weights"]]
        need(without_pin==original["weights"],"Native original weights changed while freezing")
        report["frozen_collision_geometry_exact"]={}
        for name,obj in frozen_colliders.items():
            observed=read.native_mesh(obj,graph,diag)
            exact=observed["native_topology_sha256"]==native[name]["native_topology_sha256"] and read.digest([list(x) for x in observed["points"]])==read.digest([list(x) for x in native[name]["points"]])
            report["frozen_collision_geometry_exact"][name]=exact; need(exact,"Frozen collision geometry differs from its actual native input: "+name)
        for prop in cloth.settings.bl_rna.properties:
            if prop.identifier.startswith("vertex_group_"):
                name=getattr(cloth.settings,prop.identifier); need(not name or dress.vertex_groups.get(name) is not None,"Copied Cloth group reference unavailable: "+prop.identifier)
        qa.save_candidate(candidate,read.INPUT); owned_cache=args.output/"static_private_cache"; owned_cache.mkdir()
        cloth.point_cache.filepath=str(owned_cache); cloth.point_cache.use_library_path=False; cloth.point_cache.use_disk_cache=True
        need(Path(bpy.path.abspath(cloth.point_cache.filepath)).resolve()==owned_cache.resolve(),"Static cache escaped private output")
        report["parameters"]={"cloth":surface._rna(cloth.settings),"collision":surface._rna(cloth.collision_settings),"effectors":surface._rna(cloth.settings.effector_weights),"units_to_metres":meters,"fps":private.render.fps,"fps_base":private.render.fps_base,"hard160":fixed,"new_pin_group":PIN,"source_original_frame_held":1,"private_steps":30}
        report["private_cache_policy"]="Only this new candidate's source/preview caches; no free_bake call. Exact new helper ID deletion releases its runtime cache; isolated disk files retained as private QA evidence. Artist/input cache refused if sealed/external/disk."
        report["private_visibility"]=read.visibility_evidence(ids["objects"],cloth,private)
        need(not collision.hide_viewport and not collision.hide_render and not any(obj.hide_get(view_layer=bpy.context.view_layer) or obj.hide_viewport or obj.hide_render for obj in ids["objects"]),"New private objects/explicit collision collection hidden")
        bodies={"RegisteredBody":native["RegisteredBody"],**{name:native[name] for name in record["physics"]["colliders"]}}
        proxies={name:frozen_colliders[name] for name in record["physics"]["colliders"][:-1]}
        private.frame_set(1); graph=bpy.context.evaluated_depsgraph_get(); initial,report["initial_crossings"]=sample(dress,bodies,bounds,fixed,graph,read,diag,args,qa,proxies,meters)
        report["initial_quality"]=metrics(original["points"],initial["points"],original["edges"],original["triangles"],fixed,meters)
        write(); print("Static private preview frame1 captured;30 steps pending",flush=True)
        for frame in range(2,32):
            budget(); private.frame_set(frame); bpy.context.view_layer.update(); evaluated=dress.evaluated_get(bpy.context.evaluated_depsgraph_get())
            step_mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
            try: need(len(step_mesh.vertices)==3040,"Cloth step changed native index count")
            finally: evaluated.to_mesh_clear()
        budget(); graph=bpy.context.evaluated_depsgraph_get(); final,report["final_crossings"]=sample(dress,bodies,bounds,fixed,graph,read,diag,args,qa,proxies,meters)
        need(final["faces"]==original["faces"] and final["edges"]==original["edges"] and final["native_vertex_index_order"]==original["native_vertex_index_order"],"Relaxed native topology/index changed")
        need([[item for item in row if item["index"]!=pin.index] for row in final["weights"]]==original["weights"],"Relaxed original native weights changed")
        report["final_quality"]=metrics(initial["points"],final["points"],original["edges"],final["triangles"],fixed,meters)
        report["final_quality"]["triplet_scope"]="Actual final native triangle corner IDs, compared to initial positions of those same vertices; no cross-frame loop-triangle identity inferred"
        report["native_triangulation_changed"]=initial["triangles"]!=final["triangles"]
        report["hard_pin_within_guard"]=report["final_quality"]["maximum_hard_waist_displacement_m"]<=qa.geometry_guard(meters)
        (args.output/"static_preview_same_index_delta.json").write_text(json.dumps(diag.json_content({"initial":initial,"final":final,"delta_world":[list(b-a) for a,b in zip(initial["points"],final["points"])],"units_to_metres":meters,"accepted":False,"artist_applied":False}),indent=2,allow_nan=False),encoding="utf-8")
        report["render"]={"requested":args.render,"visual_quality_accepted":False}
        if args.render:
            for label,mesh,frame in (("baseline",initial,1),("final",final,31)):
                budget(); folder=args.output/label; folder.mkdir()
                report["render"][label]=diag.native_render(SimpleNamespace(frame=frame,output=folder),mesh,native["RegisteredBody"],bounds)
        report["native_completed"]=True; report["source_frame_after_private_steps"]=home.frame_current
        need(home.frame_current==1,"Original author/Cloth timeline advanced")
    except Exception as error: report["native_completed"]=False; report["error"]={"reason":str(error),"traceback":traceback.format_exc()}
    finally:
        try:
            if home is not None and bpy.context.window is not None: bpy.context.window.scene=home
            for obj in reversed(ids["objects"]): bpy.data.objects.remove(obj,do_unlink=True)
            for scene in ids["scenes"]: bpy.data.scenes.remove(scene)
            for collection in ids["collections"]: bpy.data.collections.remove(collection)
            for mesh in ids["meshes"]:
                need(mesh.users==0,"New preview mesh still referenced; no broad orphan clearing")
                bpy.data.meshes.remove(mesh)
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
        report["code_exact"]=diag.source_manifest()==report["source_before"] and sha(HERE/"verify_actual_body_proxy_coverage.py")==COVERAGE_SHA and all(sha(HERE/name)==value for name,value in read.PINS.items()) and sha(Path(__file__))==report["script_sha256"]
        report["native_completed"] &= report["input_disk_exact"] and report["artist_disk_exact"] and report["code_exact"]
        report["elapsed_seconds"]=time.perf_counter()-started; write()
        print(json.dumps({"native_completed":report["native_completed"],"accepted":False,"report":str(destination)}),flush=True)
    return 0 if report["native_completed"] else 2

if __name__=="__main__": raise SystemExit(main(arguments()))
