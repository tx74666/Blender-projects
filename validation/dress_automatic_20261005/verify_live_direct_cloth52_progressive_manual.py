"""PREPARED ONLY: one isolated native N -> leg -> Manual -> hold trajectory.

Reuses immutable V5 construction and complete author/source/cache restoration.
This changes only explicit unkeyed input timing and endpoint measurements. It is
not an artist repair, settled-shape acceptance, imported animation or deployment.
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V5 = HERE / "verify_live_direct_cloth52_disposable_fixture_v5.py"
V5_SHA = "53f40ddddfc89e4912835130fc14c36a1cb544eeb41f63ebed16b3b6e2b3cc7b"
DIAG = HERE / "diagnose_skin_transfer.py"
DIAG_SHA = "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28"
STAGE = "LIVE_DIRECT52_PROGRESSIVE_UNKEYED_MANUAL_60"
ENDPOINTS = {1: "N", 16: "L", 31: "T", 60: "hold_final"}


def need(value, message):
    if not value:
        raise RuntimeError("ProgressiveManual52: " + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_v5():
    need(sha(V5) == V5_SHA, "Immutable V5 changed")
    spec = importlib.util.spec_from_file_location("progressive_frozen_V5", V5)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def progressive_recipe(frame):
    need(type(frame) is int and 1 <= frame <= 60, "Exact60-frame input range required")
    leg = min(1., max(0., (frame - 1) / 15.))
    hem = min(1., max(0., (frame - 16) / 15.))
    return {"left_rad": -.55 * leg, "Hem_height_fraction": -.04 * hem,
            "stage": ENDPOINTS.get(frame), "holding": frame >= 32}


def zero_contact(value):
    """A measured zero is a narrow endpoint guard, never volume/ART acceptance."""
    return (value.get("status") == "measured"
            and type(value.get("strict_crossing_count")) is int and value["strict_crossing_count"] == 0
            and not value.get("Unknown_if_incomplete", True)
            and len(value.get("closed3", [])) == 3
            and all(type(row.get("metrics", {}).get("sampled_vertices")) is int
                    and row["metrics"]["sampled_vertices"] == 3040
                    and type(row["metrics"].get("inside_vertices")) is int
                    and row["metrics"]["inside_vertices"] == 0
                    and type(row["metrics"].get("maximum_penetration_m")) in (int, float)
                    and math.isfinite(row["metrics"]["maximum_penetration_m"])
                    and row["metrics"]["maximum_penetration_m"] == 0.
                    for row in value["closed3"]))


def endpoint_contact(mesh, body, bounds, colliders, graph, metres, args, epsilon, diag, qa):
    # Diagnostic-only copy: include all3040, retaining raw/native group contracts.
    complete = dict(mesh, free_indices=list(range(3040)))
    crossing = diag.triangle_crossings(complete, body, bounds, args.triangle_pair_limit, epsilon)
    result = {"object": mesh["object"], "status": crossing["status"],
              "strict_crossing_count": crossing.get("actual_crossing_pair_count"),
              "exact_tested_pairs": crossing["exact_tested_pairs"],
              "first_pairs": crossing["crossing_pairs"][:8],
              "unresolved_counts": {key: len(crossing[key]) for key in
                                    ("coplanar_unresolved", "degenerate_unresolved", "boundary_unresolved")},
              "filter": {"all_native_vertices": 3040, "excluded_fixed_vertices": 0,
                         "tested_dress_triangles": crossing["dress_region_triangles"],
                         "native_dress_triangles": len(mesh["triangles"]),
                         "tested_Body_triangles": crossing["body_region_triangles"],
                         "native_Body_triangles": len(body["triangles"])},
              "actual_open_Body_inside_outside": False, "closed3": [], "accepted": False}
    for collider in colliders:
        qa.physics._closed_collider(collider)
        native = qa.ClosedCollider(collider, graph, epsilon)
        result["closed3"].append({"object": collider.name,
                                 "metrics": qa.collision_metrics(mesh["points"], native, metres, range(3040))})
    result["Unknown_if_incomplete"] = (crossing["status"] != "measured"
        or any(result["unresolved_counts"].values())
        or result["filter"]["tested_dress_triangles"] != len(mesh["triangles"])
        or result["filter"]["tested_Body_triangles"] != len(body["triangles"]))
    result["measured_endpoint_zero"] = zero_contact(result)
    return result


def two_view_renderer(diag):
    """Reuse native renderer/cleanup, selecting actual -Y anterior and +X side."""
    source = inspect.getsource(diag.native_render)
    old = 'for label,direction in (("front",bounds["forward"]),("side",bounds["right"]),("back",-bounds["forward"])):'
    new = 'for label,direction in (("front",-bounds["forward"]),("side",bounds["right"])):'
    old_label = '{"front":"MainRig +Y","side":"MainRig +X","back":"MainRig -Y"}[label]'
    new_label = '{"front":"Cosha anterior MainRig -Y","side":"MainRig +X"}[label]'
    need(source.count(old) == source.count(old_label) == 1, "Frozen native render view ABI differs")
    changed = source.replace(old, new).replace(old_label, new_label)
    need(ast.dump(ast.parse(changed.replace(new, old).replace(new_label, old_label))) == ast.dump(ast.parse(source)),
         "Renderer changed outside selected actual camera directions/labels")
    scope = dict(vars(diag)); exec(compile(changed, "<two actual native QA views>", "exec"), scope)
    return scope["native_render"]


def compiled_source(v5, live):
    original = v5.compiled_dynamic_source(live); source = original; edits = []
    def replace(old, new, reason):
        nonlocal source
        need(source.count(old) == 1, "Unique V5 adaptation differs: " + reason)
        source = source.replace(old, new, 1); edits.append((old, new, reason))
    critical_old = ('    critical = critical_pose_frames(input_recipe, args.case, args.frames)\n'
                    '    critical_set = set(critical["frames"])\n'
                    '    report["critical_pose_frames"] = critical\n')
    replace(critical_old, '    critical = {"roles": dict((name, frame) for frame, name in ENDPOINTS.items()), "frames": list(ENDPOINTS), "accepted": False}\n',
            "Explicit N/L/T/hold endpoints instead of old cyclic/held recipe")
    start = source.index('    action = bpy.data.actions.new("QA Dress Body Motion")\n')
    end = source.index('    remember, link, copy_object =', start)
    replace(source[start:end], '''    need(home.render.fps == 30 and home.render.fps_base == 1., "Original30fps fixture required")
    need(state["qa_action"] is None, "Unexpected own Action before unkeyed input")
    rig.animation_data.action = None; state["bound_qa_action"] = None
    hem_control = rig.pose.bones[record["controls"]["hem"]]
    old_hem = Vector(hem_control.location)
    report["synthetic_Action"] = {"created": False, "Body_keys": 0, "Dress_keys": 0, "real_imported_clip": False}
    report["progressive_recipe"] = {"frames": 60, "fps": 30, "endpoints": dict((name, frame) for frame, name in ENDPOINTS.items()),
        "L_angle_rad": -.55, "T_Hem_height_fraction": -.04, "hold_frames": list(range(32,61)),
        "input": "Explicit native unkeyed raw Body/Hem assignments before forward frame_set; not world-mesh interpolation",
        "held_teleport_repeated": False, "physics_parameters_changed": False, "settled_or_artist_acceptance": False}
    write()
''', "No Action or keys; absolute baseline-relative native input")
    replace('cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step=1,args.frames+args.manual_steps,1',
            'cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step=1,60,1', "Exact new60-frame owned cache interval")
    start = source.index('        if diagnose:\n'); end = source.index('        return current\n', start)
    replace(source[start:end], '''        if diagnose:
            tick=time.perf_counter();body_mesh=diag.mesh_snapshot(values["body"],graph);body_seconds=time.perf_counter()-tick
            need(len(body_mesh["points"])<=args.body_vertex_limit and qa.finite(body_mesh["points"]),"actual Body diagnostic exceeds budget/nonfinite")
            row["actual_registered_Body_vs_initial"]=base.error_summary(body_mesh["points"],first["body"]["points"] if "body" in first else body_mesh["points"],metres)
            render_bounds=diag.framing(rig,record,graph);bounds=dict(render_bounds)
            projections=[(p-bounds["waist"]).dot(bounds["up"]) for mesh in (meshes["requested3040"],meshes["final3040"],body_mesh) for p in mesh["points"]]
            need(projections,"complete collision envelope empty");bounds["lower"],bounds["upper"]=min(projections)-1.e-4,max(projections)+1.e-4
            epsilon=max(1.e-8,record["fit"]["height_world"]*1.e-6)
            colliders=[bpy.data.objects[name] for name in record["physics"]["colliders"][:-1]]
            need(len(colliders)==3,"Exact native three closed colliders required")
            tick=time.perf_counter()
            pair={name:endpoint_contact(meshes[name],body_mesh,bounds,colliders,graph,metres,args,epsilon,diag,qa) for name in ("requested3040","final3040")}
            contact={"label":label,"frame":row["frame"],"same_native_graph":True,"outputs":pair,
                "geometry_quality":row["geometry_quality"],"requested_vs_final_native_triangulation_exact":meshes["requested3040"]["triangles"]==meshes["final3040"]["triangles"],
                "actual_open_Body_volume_claim":False,"area_Unknown_is_not_PASS":True,"accepted":False,
                "timings":{"Body_readback_seconds":body_seconds,"two_output_collision_seconds":time.perf_counter()-tick}}
            contacts.append(contact);report["progressive_endpoint_contacts"]=contacts;write()
            current["body"]=body_mesh;current["bounds"]=bounds
            if label=="N":
                report["N_safe_start"]={"passed":all(zero_contact(value) for value in pair.values()),"scope":"Measured full3040 triangle crossings and three proxy signed vertices, not open-Body volume or ART", "accepted":False};write()
                need(report["N_safe_start"]["passed"],"N safety unknown or intersecting; no progressive simulation acceptance")
            if args.render:
                renderer=two_view_renderer(diag)
                for name in ("requested3040","final3040"):
                    budget();folder=args.output/(label+"_"+name);folder.mkdir()
                    render=renderer(SimpleNamespace(output=folder,frame=home.frame_current),meshes[name],body_mesh,render_bounds)
                    render["provenance"]="Same native graph endpoint; original waist-knee crop; actual -Y anterior/+X side; Requested input and final Cloth output"
                    report.setdefault("progressive_renders",{}).setdefault(label,{})[name]=render;write()
                    need(render.get("success") is True and set(render.get("views",{}))=={"front","side"},"Native stage target/final anterior/side images incomplete")
''', "Both actual targets/final outputs, complete collision envelope and same cropped native views")
    start = source.index('    sparse={1,args.frames//2,args.frames} | critical_set; stopped=set()\n')
    end = source.index('    # Stop NEW Cloth before author restoration.', start)
    replace(source[start:end], '''    input_rows=[];last_rows=[]
    for frame in range(1,61):
        budget();move=progressive_recipe(frame)
        root.location=old_location;root.rotation_euler=old_euler
        thighs["L"].rotation_quaternion=old_rotations["L"]@Quaternion(axes[thigh_names["L"]],move["left_rad"])
        thighs["R"].rotation_quaternion=old_rotations["R"]
        hem_control.location=old_hem+Vector((height*move["Hem_height_fraction"],0.,0.))
        rig.update_tag();need(rig.animation_data.action is None and state.get("qa_action") is None and state.get("bound_qa_action") is None,"Unkeyed input acquired Action")
        commanded={"frame":frame,"left":list(thighs["L"].rotation_quaternion),"right":list(thighs["R"].rotation_quaternion),"Hem":list(hem_control.location),"recipe":move,"keys_created":0}
        tick=time.perf_counter();home.frame_set(frame);frame_seconds=time.perf_counter()-tick
        need(commanded["left"]==list(thighs["L"].rotation_quaternion) and commanded["right"]==list(thighs["R"].rotation_quaternion) and commanded["Hem"]==list(hem_control.location),"Native raw input was overwritten during frame evaluation")
        label=ENDPOINTS.get(frame,"progressive_"+str(frame));current=sample(label,frame in ENDPOINTS)
        current["row"]["native_timing_segments"]["frame_set_seconds"]=frame_seconds
        input_rows.append(commanded);report["progressive_native_raw_inputs"]=input_rows
        if frame>=51:last_rows.append(current["row"]["final_hem_Waist_rigid_step_m"])
        daily_last=current;write()
    L_row=next(row for row in samples if row["label"]=="L")
    knee_delta=Vector(L_row["native_knee_world"])-Vector(first["knee"])
    forward_motion=knee_delta.dot(-first["bounds"]["forward"])*metres
    upward_motion=knee_delta.dot(first["bounds"]["up"])*metres
    report["progressive_collection"]={"native_frames":len(samples),"stage_contact_labels":[row["label"] for row in contacts],
        "all_forward_pin_microguards_passed":all(row["hard80_pin_microguard_passed"] is True for row in samples),
        "last10_frame_steps_m":last_rows,"last10_duration_seconds":9/30.,"equilibrium_claim":False,"area_Unknown_is_not_PASS":True,
        "actual_knee_delta_N_to_L_world_m":[v*metres for v in knee_delta],"actual_anterior_motion_m":forward_motion,"actual_upward_motion_m":upward_motion,
        "target_feasibility_and_final_contacts_are_separate":True,"effects_accepted":False,"accepted":False}
    report["required_progressive_renders"]={"requested":bool(args.render),"labels":list(ENDPOINTS.values()),"complete":all(report.get("progressive_renders",{}).get(label,{}).get(name,{}).get("success") is True for label in ENDPOINTS.values() for name in ("requested3040","final3040")) if args.render else "NotRequested","accepted":False};write()
    need(len(samples)==60 and report["progressive_collection"]["all_forward_pin_microguards_passed"] and len(last_rows)==10 and {row["label"] for row in contacts}==set(ENDPOINTS.values()),"Progressive input/contact collection incomplete")
    need(forward_motion>height*.01*metres and upward_motion>0.,"Actual forward/upward native leg response missing")
    if args.render:need(report["required_progressive_renders"]["complete"] is True,"Progressive target/final stage views incomplete")
''', "One unkeyed gradual60 trajectory; no repeated held teleport/old extra10")
    reverse=source
    for old,new,_reason in reversed(edits):
        need(reverse.count(new)==1,"Reversible progressive substitution differs");reverse=reverse.replace(new,old,1)
    need(ast.dump(ast.parse(reverse))==ast.dump(ast.parse(original)),"V5 construction/fullRNA/precision/restoration changed outside bounded trajectory and measurements")
    return source,[reason for _old,_new,reason in edits]


def prepared_namespace(v5, parts, args):
    live,policy,cold,candidate,adapter,direct,core,base=parts
    namespace=v5.prepared_namespace(*parts,args)
    source,reasons=compiled_source(v5,live)
    scope=dict(vars(live))
    scope.update(_DIRECT=direct,_CORE=core,_ADAPTER=adapter,STAGE=STAGE,
        classify_cache_transition=policy.classify_cache_transition,paired_component_proof=v5.paired_component_proof,
        INPUT_SHA=v5.INPUT_SHA,hard_pin_identity=v5.hard_pin_identity,PIN_FAILURE=v5.PIN_FAILURE,PIN_FAILURE_SHA=v5.PIN_FAILURE_SHA,
        modifier_rna_pair=v5.modifier_rna_pair,RNA_FAILURE=v5.RNA_FAILURE,RNA_FAILURE_SHA=v5.RNA_FAILURE_SHA,
        hard_pin_sample_policy=v5.hard_pin_sample_policy,OBS_HELD_LABELS=v5.OBS_HELD_LABELS,
        progressive_recipe=progressive_recipe,ENDPOINTS=ENDPOINTS,endpoint_contact=endpoint_contact,
        zero_contact=zero_contact,two_view_renderer=two_view_renderer)
    exec(compile(source,str(Path(__file__)),"exec"),scope)
    def exercise(values,frozen):
        try:return scope["exercise_dynamic"](values,frozen)
        finally:live._DYNAMIC=scope.get("_DYNAMIC",{})
    namespace["exercise_direct"]=exercise
    namespace["__file__"]=str(Path(__file__))
    namespace["PINS"].update({V5:V5_SHA,DIAG:DIAG_SHA,Path(__file__):sha(Path(__file__))})
    old_capture=namespace["capture_program"]
    def capture(*values):
        receipt=old_capture(*values);report=values[-1];report["stage"]=STAGE
        report["progressive_adapter"]={"immutable_V5":str(V5),"sha256":V5_SHA,"changes":reasons,
            "physical_settings_weights_and_author_finally_unchanged":True,"old_recipe_repeated":False,
            "historical_held_failure_accepted":False,"input_is_imported_animation":False,"accepted":False}
        report["live_disposable_component_adapter"]["physics_action_recipe_parameters_held_input_unchanged"]=False
        return receipt
    namespace["capture_program"]=capture
    return namespace,source


def pure_checks(v5,parts,args):
    rows=[progressive_recipe(frame) for frame in range(1,61)]
    need(rows[0]["left_rad"]==rows[0]["Hem_height_fraction"]==0.,"N input differs")
    need(rows[15]["left_rad"]==-.55 and rows[15]["Hem_height_fraction"]==0.,"L endpoint differs")
    need(rows[30]["left_rad"]==-.55 and rows[30]["Hem_height_fraction"]==-.04,"T endpoint differs")
    need(all(row["left_rad"]==-.55 and row["Hem_height_fraction"]==-.04 for row in rows[31:]) and sum(row["holding"] for row in rows)>=15,"Hold path incomplete")
    need(all(rows[i]["left_rad"]<=rows[i-1]["left_rad"] for i in range(1,16)) and all(rows[i]["Hem_height_fraction"]<=rows[i-1]["Hem_height_fraction"] for i in range(16,31)),"Progressive path is not monotonic")
    for frame in (0,61,True,1.5):
        try:progressive_recipe(frame)
        except RuntimeError:pass
        else:raise RuntimeError("Out-of-range path admitted")
    valid={"status":"measured","strict_crossing_count":0,"Unknown_if_incomplete":False,
           "closed3":[{"metrics":{"sampled_vertices":3040,"inside_vertices":0,"maximum_penetration_m":0.}} for _ in range(3)]}
    need(zero_contact(valid),"Measured endpoint-zero control failed")
    negatives=[dict(valid,status="skipped_candidate_limit"),dict(valid,strict_crossing_count=1),dict(valid,Unknown_if_incomplete=True)]
    for key,value in (("sampled_vertices",2880),("inside_vertices",1),("maximum_penetration_m",float("nan"))):
        row=json.loads(json.dumps(valid));row["closed3"][0]["metrics"][key]=value;negatives.append(row)
    need(all(not zero_contact(row) for row in negatives),"Unknown/contact/excluded-vertex scope admitted as N-safe")
    namespace,source=prepared_namespace(v5,parts,args);live=parts[0]
    need(namespace["restore_program"] is live.restore_dynamic,"Frozen Root/author restorer replaced")
    need('keyframe_insert' not in source and 'bpy.data.actions.new' not in source and 'held_leg_unkeyed' not in source and 'held_manual_unkeyed' not in source,"Old keyed/teleport recipe survived")
    need('need(row["hard80_pin_sample_policy"]["allowed"]' in source and 'copied C native skin/boundSD RNA differs' in source and 'old14cache changed during live newCloth seeks' in source,"Strict pin/RNA/author-cache guard missing")
    need(sha(DIAG)==DIAG_SHA,"Frozen native diagnostic changed")
    renderer_tree=ast.parse(DIAG.read_text(encoding="utf-8"))
    render_node=next(node for node in renderer_tree.body if isinstance(node,ast.FunctionDef) and node.name=="native_render")
    scope={};exec(compile(ast.Module(body=[render_node],type_ignores=[]),str(DIAG),"exec"),scope)
    renderer=two_view_renderer(type("FrozenDiag",(),{"native_render":staticmethod(scope["native_render"])})())
    return {"passed":True,"native":False,"trajectory":60,"hold_frames":29,"invalid_frame_controls":4,
            "endpoint_zero_positive":1,"endpoint_Unknown_contact_scope_negatives":len(negatives),
            "reversible_V5_AST":True,"strict_all_forward_pins":True,"native_Action_or_keys_created":False,
            "current_namespace_and_original_restorer":True,"renderer_precompiled":renderer is not None,"accepted":False}


def arguments(v5):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("cold-proof","input-proof","artist-protection"):
        parser.add_argument("--"+name,type=Path,required=True);parser.add_argument("--"+name+"-sha",required=True)
    parser.add_argument("--output",type=Path);parser.add_argument("--render",action="store_true")
    parser.add_argument("--max-seconds",type=float,default=180.)
    parser.add_argument("--triangle-pair-limit",type=int,default=2000000);parser.add_argument("--body-vertex-limit",type=int,default=500000)
    parser.add_argument("--pure-checks",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    for name in ("cold_proof","input_proof","artist_protection"):
        path=getattr(args,name);expected=getattr(args,name+"_sha")
        need(path.is_absolute() and path.resolve().is_relative_to(HERE) and path.is_file() and v5.valid_sha(expected) and sha(path)==expected,"Explicit actual protected proof required: "+name)
        setattr(args,name,path.resolve())
    need(0<args.max_seconds<=180 and 0<args.triangle_pair_limit<=2000000 and 0<args.body_vertex_limit<=500000,"Bounded test differs")
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and args.output.resolve()!=HERE and not args.output.exists(),"Fresh isolated output required")
    args.case="leg_raise";args.frames=60;args.manual_steps=0;args.leg_raise_sign=-1
    return args


def main():
    v5=load_v5();args=arguments(v5);parts=v5.components(args)
    v5.paired_component_proof(args.cold_proof,args.cold_proof_sha,args.input_proof,args.input_proof_sha)
    if args.pure_checks:
        print(json.dumps(pure_checks(v5,parts,args)));return 0
    namespace,_source=prepared_namespace(v5,parts,args)
    return namespace["main"](args)


if __name__=="__main__":
    raise SystemExit(main())
