"""PREPARED ONLY: native LIVE MainManual/raw Original bridge, not deployment.

The frozen 50e constructor, derived Manual-only disconnect, native raw80 bind,
50 micrometre geometry guards and exact source cleanup are reused in memory.
Private MCH follows independent Main MCH BONE_DONE; private DEF passthrough
uses only SINGLE_PROP raw channels and constraint mix/mute BONE_LOCAL. No Main
Dress DEF matrix/transform variable or private input snapshot replay is used.
Native animation and public Original are exercised only in the isolated 7ac QA.
Rotation modes are born static and explicitly synchronized at public operator
boundaries: that candidate adapter is not an installed runtime hook. No Keys
claim, new C time stepping, tracker feedback retarget, artistic/FPS acceptance.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "prototype_input800_main_manual_reuse.py"
BASE_SHA = "50e508ef3e9ee7adb2d03086c6aa0536f558eb3f2359bf2a645189164cb72a56"
ARTIST_SHA = "a595d1eee9f2f86908d2be816fbcfedbf7619a2c15e589def8721cc1e9998411"
TRANSITION = HERE.parent / "hips_display_20261006/final_saved_scene.json"
TRANSITION_SHA = "d532359b582762d8594985894b1e3739f7e027b2382659851a6f1261c407fc97"
BASE_RESULT = HERE / "actual_input800_main_manual_reuse_51_51_20261006_161641_269/result/input800_reproduction.json"
BASE_RESULT_SHA = "9b714e07a24003834fadbb22b19a173bf6d7a439b02242c317c6d63c4e728bc1"
RAW_FIELDS = ("location", "scale", "rotation_quaternion", "rotation_euler", "rotation_axis_angle")
RAW_SIZES = {"location":3, "scale":3, "rotation_quaternion":4, "rotation_euler":3, "rotation_axis_angle":4}
_STATE = {}
OFFICIAL = {
    "raw_and_constraint_RNA_BONE_LOCAL": "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/depsgraph/intern/builder/deg_builder_rna.cc",
    "SINGLE_PROP_exit_RNA_not_TRANSFORMS_BONE_DONE": "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/depsgraph/intern/builder/deg_builder_relations.cc",
    "Constraint_mix_mode_mute_native_properties": "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/makesrna/intern/rna_constraint.cc",
    "enum_driver_numeric_read": "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/blenkernel/intern/fcurve_driver.cc",
    "enum_driver_native_write": "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/blenkernel/intern/anim_sys.cc",
    "rotation_mode_setter_changes_rotation_arrays": "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/makesrna/intern/rna_pose.cc",
}


def need(condition, message):
    if not condition:
        raise RuntimeError("LIVE bridge: " + message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576), b""): h.update(block)
    return h.hexdigest()


def load_base():
    need(sha(BASE_PATH)==BASE_SHA, "frozen 50e changed")
    spec=importlib.util.spec_from_file_location("live_bridge_frozen50e", BASE_PATH)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def clone_value(value):
    if hasattr(value,"to_dict"): return {k:clone_value(v) for k,v in value.to_dict().items()}
    if hasattr(value,"to_list"): return [clone_value(v) for v in value.to_list()]
    if isinstance(value,dict): return {k:clone_value(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clone_value(v) for v in value]
    if type(value).__module__=="mathutils": return [clone_value(v) for v in value]
    return value  # Preserve native ID references, never deepcopy or recreate them.


def props(owner):
    return {key:clone_value(owner[key]) for key in owner.keys()}


def restore_props(owner, saved):
    for key in list(owner.keys()):
        if key not in saved: del owner[key]
    for key,value in saved.items():
        if key not in owner or clone_value(owner[key])!=value: owner[key]=value


def scalar_values(owner):
    result={}
    for prop in owner.bl_rna.properties:
        name=prop.identifier
        if name=="rna_type" or prop.is_readonly or prop.type not in {"BOOLEAN","INT","FLOAT","STRING","ENUM"}: continue
        value=getattr(owner,name)
        result[name]=(set(value) if isinstance(value,set) else list(value) if getattr(prop,"is_array",False) else value)
    return result


def writable_pointers(owner):
    return {p.identifier:getattr(owner,p.identifier) for p in owner.bl_rna.properties
            if p.identifier!="rna_type" and not p.is_readonly and p.type=="POINTER"}


def constraint_inventory(rig, surface):
    return {owner.name if owner is not rig else "$Object":
            [{"pointer":c.as_pointer(), "name":c.name,"type":c.type,"rna":surface._rna(c)} for c in owner.constraints]
            for owner in [rig,*rig.pose.bones]}


def capture_program(source, rig, cloth, home, qa, surface, same, actual, report):
    """Receipts precede any QA binding, mode or pause write; no stale Edit RNA."""
    animation=rig.animation_data
    need(animation is None or not animation.use_tweak_mode, "author NLA tweak mode is active")
    owners=[home,source,rig,rig.data,*rig.data.bones,*rig.pose.bones,*rig.data.collections_all]
    _STATE.clear()
    _STATE.update({"source":source,"rig":rig,"cloth":cloth,"home":home,"qa":qa,"surface":surface,"same":same,
        "idprops":[(o,props(o)) for o in owners], "pose":qa.pose_channels(rig),
        "object_mode":rig.rotation_mode,"object_basis":rig.matrix_basis.copy(),
        "context":qa.skirt._context_state(__import__("bpy").context),
        "frame":(home.frame_current,home.frame_subframe),"tool_auto":home.tool_settings.use_keyframe_insert_auto,
        "cloth_flags":(cloth.show_viewport,cloth.show_render),"source_modifier_flags":[(m,m.show_viewport,m.show_render) for m in source.modifiers],
        "constraints":constraint_inventory(rig,surface),
        "constraint_scalars":[(c,{**scalar_values(c),**writable_pointers(c)}) for o in [rig,*rig.pose.bones] for c in o.constraints],
        "bone_flags":[(b,scalar_values(b)) for b in rig.data.bones],
        "pose_flags":[(b,{k:clone_value(getattr(b,k)) for k in ("lock_location","lock_rotation","lock_rotation_w","lock_rotations_4d","lock_scale","custom_shape","custom_shape_transform","custom_shape_scale_xyz","custom_shape_translation","custom_shape_rotation_euler","use_custom_shape_bone_size")}) for b in rig.pose.bones],
        "collections":[(c,c.is_visible,c.is_solo) for c in rig.data.collections_all],
        "armature_display":{k:getattr(rig.data,k) for k in ("show_bone_custom_shapes","display_type","show_names","show_axes")},
        "animation":animation,"action":animation.action if animation else None,"slot":animation.action_slot if animation else None,
        "nla":[(t,t.mute,t.is_solo) for t in animation.nla_tracks] if animation else [],
        "animation_use_nla":animation.use_nla if animation else None,
        "qa_action":None,"qa_action_pointer":None,"action_paths":set(),"expected_drivers":[],"rotation_modes":{},
        "initial_cache":same.cache_state(cloth,qa),"initial_Main_rest":load_base().main_rest_receipt(rig,surface)})
    report["cache_before"]=_STATE["initial_cache"]
    report["live_initial_C_read"]={"measured":False,"cache_before":_STATE["initial_cache"]}
    graph=__import__("bpy").context.evaluated_depsgraph_get()
    _STATE["initial_C"]=qa.world_mesh(actual,graph)["points"]
    need(len(_STATE["initial_C"])==800 and qa.finite(_STATE["initial_C"]),"initial original C native point evidence missing")
    report["live_initial_C_read"].update({"measured":True,"C_summary":same.summary(_STATE["initial_C"],qa),"cache_after":same.cache_state(cloth,qa)})
    need(report["live_initial_C_read"]["cache_after"]==_STATE["initial_cache"],"initial native C read altered original cache before pause")
    return {"captured":True,"all_original_constraint_pointers_recorded":True,"cache":_STATE["initial_cache"],"initial_C_summary":same.summary(_STATE["initial_C"],qa),
            "NLA_tracks":[t.name for t,_,_ in _STATE["nla"]],"no_author_Keys_exercise":True}


def restore_pose(rig, saved):
    for name,row in saved.items():
        bone=rig.pose.bones[name]; bone.rotation_mode=row["mode"]
        # Live Root loc/scale drivers are observed, not overridden by QA writes.
        if name!="CTRL_master": bone.location,bone.scale=row["location"],row["scale"]
        bone.rotation_quaternion,bone.rotation_euler=row["quaternion"],row["euler"]
        bone.rotation_axis_angle=row["axis_angle"]
    rig.update_tag()


def restore_program(report, qa, surface):
    """Attempt every restoration before reporting failures; original IDs remain."""
    import bpy
    if "source" not in _STATE: return
    state=_STATE; source,rig,home,cloth=(state[k] for k in ("source","rig","home","cloth")); errors=[]
    def attempt(label,fn):
        try: fn()
        except Exception as error: errors.append({"step":label,"message":str(error)})
    cloth.show_viewport=cloth.show_render=False
    if qa.original.active(rig):
        attempt("public Controls",lambda:qa.public_switch(bpy.ops.character_designer.body_original_mode,action="CONTROLS"))
    if rig.animation_data: rig.animation_data.action=None
    attempt("raw pose",lambda:restore_pose(rig,state["pose"]))
    for owner,saved in state["constraint_scalars"]:
        def change(o=owner,s=saved):
            for key,value in s.items():
                if getattr(o,key)!=value: setattr(o,key,value)
        attempt("existing constraint scalar "+owner.name,change)
    for owner,saved in state["pose_flags"]:
        def change(o=owner,s=saved):
            for key,value in s.items():
                if clone_value(getattr(o,key))!=value: setattr(o,key,value)
        attempt("pose flags "+owner.name,change)
    for owner,saved in state["bone_flags"]:
        def change(o=owner,s=saved):
            for key,value in s.items():
                if clone_value(getattr(o,key))!=clone_value(value): setattr(o,key,value)
        attempt("bone flags "+owner.name,change)
    for owner,visible,solo in state["collections"]:
        attempt("bone collection "+owner.name,lambda o=owner,v=visible,s=solo:(setattr(o,"is_visible",v),setattr(o,"is_solo",s)))
    for key,value in state["armature_display"].items():
        attempt("Armature display "+key,lambda k=key,v=value:setattr(rig.data,k,v))
    for owner,saved in state["idprops"]: attempt("ID properties "+owner.name,lambda o=owner,s=saved:restore_props(o,s))
    rig.rotation_mode=state["object_mode"]
    if rig.matrix_basis!=state["object_basis"]: rig.matrix_basis=state["object_basis"]
    if state["animation"] is not None:
        animation=rig.animation_data; need(animation is state["animation"] or animation.as_pointer()==state["animation"].as_pointer(), "author AnimData replaced")
        animation.action=state["action"]
        if state["slot"] is not None: animation.action_slot=state["slot"]
        animation.use_nla=state["animation_use_nla"]
        for track,mute,solo in state["nla"]: track.mute,track.is_solo=mute,solo
    elif rig.animation_data is not None:
        need(not rig.animation_data.drivers and not rig.animation_data.nla_tracks and rig.animation_data.action is None,"unexpected author AnimData dependency")
        rig.animation_data_clear()
    attempt("author frame while paused",lambda:home.frame_set(state["frame"][0],subframe=state["frame"][1]))
    for modifier,viewport,render in state["source_modifier_flags"]: modifier.show_viewport,modifier.show_render=viewport,render
    cloth.show_viewport,cloth.show_render=state["cloth_flags"]
    home.tool_settings.use_keyframe_insert_auto=state["tool_auto"]
    action=state["qa_action"]
    if action is not None:
        attempt("own Action remove",lambda:(need(action.as_pointer()==state["qa_action_pointer"] and action.users==0,"QA Action foreign user"),bpy.data.actions.remove(action)))
    attempt("original context",lambda:qa.skirt._restore_context(bpy.context,state["context"]))
    attempt("final native update",lambda:bpy.context.view_layer.update())
    report["live_author_restore"]={"errors":errors,"constraint_pointers_and_RNA_exact":constraint_inventory(rig,surface)==state["constraints"],
        "raw_pose_exact":qa.pose_channels(rig)==state["pose"],"id_properties_exact":all(props(o)==s for o,s in state["idprops"]),
        "frame_exact":(home.frame_current,home.frame_subframe)==state["frame"],"cloth_flags_exact":(cloth.show_viewport,cloth.show_render)==state["cloth_flags"],
        "cache_exact":state["same"].cache_state(cloth,qa)==state["initial_cache"]}
    need(not errors and all(value is True for key,value in report["live_author_restore"].items() if key!="errors"),"complete author restoration failed")


def bounded_animation_binding(rig):
    animation=rig.animation_data
    need(animation is not None and all(t.mute and not t.is_solo for t in animation.nla_tracks), "author NLA not completely paused")
    expected=_STATE.get("bound_qa_action")
    need(animation.action==expected,"Main has an unknown playback Action")
    if expected is not None:
        curves=_STATE["qa"].curve_paths(expected)
        paths={(c.data_path,int(c.array_index)) for c in curves}
        need(paths==_STATE["action_paths"] and len(curves)==len(paths),"QA Action whitelist/order identity unresolved")
        need(all(c.mute is False for c in curves),"QA input curve is muted")
    return True


def driver_inventory(input_rig):
    animation=input_rig.animation_data
    need(animation is not None and animation.action is None and not animation.nla_tracks,"private driver owner acquired playback")
    current=list(animation.drivers); rows=[]; expected=_STATE["expected_drivers"]
    need(len(current)==len(expected) and {(c.data_path,c.array_index) for c in current}=={(r["output"],r["index"]) for r in expected},"private generated driver identity changed")
    by={(r["output"],r["index"]):r for r in expected}
    for curve in current:
        spec=by[(curve.data_path,curve.array_index)]; d=curve.driver
        need(not curve.mute and curve.is_valid and d.is_valid and not d.use_self and d.type=="SCRIPTED" and d.expression=="var" and d.is_simple_expression,
             "generated raw driver invalid/changed")
        variables=list(d.variables)
        need(len(variables)==1 and variables[0].name=="var" and variables[0].type=="SINGLE_PROP" and len(variables[0].targets)==1,"nonraw driver variable")
        target=variables[0].targets[0]
        need(target.id==_STATE["rig"] and target.data_path==spec["target"],"raw target ID/path changed")
        rows.append(spec)
    return {"count":len(rows),"all_exact_SINGLE_PROP":True,"MainDEF_BONE_DONE_matrix_or_transform_variables":False,"paths":rows}


def setup_live_drivers(input_rig, rig, record, report):
    rows=[]; mode_receipt={}; enum_receipt={}
    def passthrough(owner,field,path,index=None):
        prop=owner.bl_rna.properties[field]
        need(not prop.is_readonly and prop.is_animatable,"native target RNA is not driverable: "+field)
        curve=owner.driver_add(field) if index is None else owner.driver_add(field,index)
        driver=curve.driver; driver.type="SCRIPTED"; driver.expression="var"; driver.use_self=False
        variable=driver.variables.new(); variable.name="var"; variable.type="SINGLE_PROP"
        variable.targets[0].id=rig; variable.targets[0].data_path=path
        rows.append({"output":curve.data_path,"index":int(curve.array_index),"target":path,"dependency_operation":"BONE_LOCAL"})
    for chain in record["chains"]:
        for name in chain["def"]:
            main,private=rig.pose.bones[name],input_rig.pose.bones[name]
            private.rotation_mode=main.rotation_mode; mode_receipt[name]=main.rotation_mode
            for field in RAW_FIELDS:
                need(len(getattr(main,field))==len(getattr(private,field))==RAW_SIZES[field],"raw array ABI changed")
                for index in range(RAW_SIZES[field]): passthrough(private,field,main.path_from_id(field)+"["+str(index)+"]",index)
            old=main.constraints["Skirt manual pose"]; new=private.constraints[0]
            for field in ("mix_mode","mute"):
                if field=="mix_mode":
                    left={e.identifier:e.value for e in old.bl_rna.properties[field].enum_items}
                    right={e.identifier:e.value for e in new.bl_rna.properties[field].enum_items}
                    need(left==right and {"REPLACE","BEFORE_FULL"}<=set(left),"native mix enum ABI differs")
                    enum_receipt[name]=left
                passthrough(new,field,old.path_from_id(field))
    _STATE["expected_drivers"],_STATE["rotation_modes"]=rows,mode_receipt
    report["live_driver_construction"]={"count":len(rows),"native_mix_enum_values":enum_receipt,"born_modes":mode_receipt,
        "official_primary_source":OFFICIAL,"rotation_mode_driver_used":False,
        "scope":"SINGLE_PROP raw DEF arrays and manual mix/mute BONE_LOCAL; private Manual only follows Main MCH BONE_DONE"}
    need(len(rows)==32*(17+2),"incomplete 32 DEF passthrough driver count")


def raw_source_program_guard(rig, deform):
    """Raw channel/enum writers could themselves read C: reject, not assume."""
    paths=set()
    for name in deform:
        bone=rig.pose.bones[name]
        paths.update(bone.path_from_id(field) for field in (*RAW_FIELDS,"rotation_mode"))
        manual=bone.constraints["Skirt manual pose"]
        paths.update(manual.path_from_id(field) for field in ("mix_mode","mute"))
    animation=rig.animation_data
    def primitive_path(path): return ast.dump(ast.parse(path,mode="eval"),include_attributes=False)
    targets={primitive_path(path) for path in paths}
    conflicts=[{"path":curve.data_path,"index":int(curve.array_index)} for curve in animation.drivers
               if primitive_path(curve.data_path) in targets] if animation else []
    need(not conflicts,"Main raw/mix/mode has authored driver writers: "+str(conflicts[:3]))
    # The one active Action is checked separately and writes Body/CTRL only.
    bounded_animation_binding(rig)
    return {"raw_DEF_and_manual_enum_driver_writers_absent":True,"future_Action_or_NLA_Key_writer_closure_proved":False}


def boundary_sync(input_rig, rig, deform, label, report):
    modes={}
    for name in sorted(deform):
        main,private=rig.pose.bones[name],input_rig.pose.bones[name]
        private.rotation_mode=main.rotation_mode; modes[name]=main.rotation_mode
    _STATE["rotation_modes"]=modes
    report.setdefault("explicit_operator_boundary_mode_sync",[]).append({"label":label,"modes":modes,"formal_hook_installed":False})


def sample_raw(rig, input_rig, deform, graph, base):
    posed,private=rig.evaluated_get(graph),input_rig.evaluated_get(graph); rows={}
    for name in sorted(deform):
        left,right=posed.pose.bones[name],private.pose.bones[name]
        need(left.rotation_mode==right.rotation_mode==_STATE["rotation_modes"][name],"rotation mode changed outside explicit boundary")
        original,copied=base.channels(left),base.channels(right)
        need(original==copied and all(math.isfinite(x) for field in RAW_FIELDS for x in original[field]),"native evaluated raw passthrough differs")
        old,new=left.constraints["Skirt manual pose"],right.constraints[0]
        need(old.mix_mode==new.mix_mode and old.mute==new.mute,"native mix/mute passthrough differs")
        proof=base.native_trs_copy_proof(original,original,copied,left.matrix_basis,right.matrix_basis,
            bool(rig.data.bones[name].use_connect),bool(input_rig.data.bones[name].use_connect),"live raw "+name)
        rows[name]={"raw":original,"native_TRS":proof,"mix_mode":old.mix_mode,"mute":old.mute}
    return rows


def exercise_live(values, base):
    import bpy
    from mathutils import Quaternion, Vector
    required=("source","rig","record","input_rig","before","after","oracle","cloth","actual","clone","home","qa","diag","surface","same","read","report","write","audit","budget","metres","guard","controls","manual","deform","upstream","waist","forbidden","ring","height","legs","axes","raw_contract","original_group_count")
    need(all(k in values for k in required),"frozen constructor local ABI changed")
    source,rig,record,input_rig,before,after,oracle,cloth,actual,clone,home,qa,diag,surface,same,read,report,write,audit,budget,metres,guard,controls,manual,deform,upstream,waist,forbidden,ring,height,legs,axes,raw_contract,original_group_count=(values[k] for k in required)
    report["stage"]="LIVE_INPUT800_MAIN_MANUAL_BRIDGE"
    report["scope"]="LIVE native own CTRL/Body Action and public Original, independent MainMCH plus MainDEF raw SINGLE_PROP. No private raw snapshot replay. Pause original Cloth only during native Action seek; no reset/free/bake. No new C solver/feedback/Keys/artist deployment claim."
    report["feedback_loop_native_exercised"]=False
    report["feedback_loop_scope"]="Deferred: original PHYS/Tracker/C target identities remain untouched. Primary granular dependency source proof does not prove future live solver feedback performance or Automatic Original semantics."
    transition=json.loads(TRANSITION.read_text(encoding="utf-8"))
    need(transition["artist_sha256"]==ARTIST_SHA and transition["main_artist_saved"] is True and transition["all_other_recorded_rig_data_unchanged"] is True
         and transition["blender_save_result"]==["FINISHED"] and transition["restore_property"]=="character_designer_hips_display_restore_v1","typed artist save transition invalid")
    report["artist_provenance"]={"disk_sha256":ARTIST_SHA,"typed_transition":str(TRANSITION),"typed_transition_sha256":TRANSITION_SHA,
        "old7ac_fullraw_equals_current_artist":False,"current_artist_native_integration_verified":False}
    need(base.key_values(source) is None,"this first no-Keys fixture gate cannot silently claim animated Keys support")
    setup_live_drivers(input_rig,rig,record,report); input_rig.update_tag(); bpy.context.view_layer.update()
    work_pose=qa.pose_channels(rig); _STATE["bound_qa_action"]=None
    knee_name=legs["L"]["chain"][1]; thigh_name=legs["L"]["chain"][0]; hem_name=record["controls"]["hem"]
    neutral_handle=Vector(rig.pose.bones[hem_name].location); thigh=rig.pose.bones[thigh_name]; original_thigh=Quaternion(thigh.rotation_quaternion)
    # Reject active authored output drivers; only new temporary QA curves may write these controls.
    keyed={thigh.path_from_id("rotation_quaternion"),rig.pose.bones[hem_name].path_from_id("location")}
    need(not any(c.data_path in keyed for c in rig.animation_data.drivers),"author transform driver controls selected QA input")
    action=bpy.data.actions.new("QA Dress Live Inputs"); _STATE["qa_action"],_STATE["qa_action_pointer"]=action,action.as_pointer()
    rig.animation_data.action=action; _STATE["bound_qa_action"]=action
    thigh.rotation_mode="QUATERNION"
    for frame,angle,hem_delta in ((1,0.,0.),(3,.35,height*.03),(5,-.18,-height*.02)):
        thigh.rotation_quaternion=original_thigh@Quaternion(axes[thigh_name],angle)
        rig.pose.bones[hem_name].location=neutral_handle+Vector((hem_delta,0.,0.))
        need(thigh.keyframe_insert(data_path="rotation_quaternion",frame=frame,group="QA Body") and rig.pose.bones[hem_name].keyframe_insert(data_path="location",frame=frame,group="QA Dress Control"),"native own Action key insertion failed")
    curves=qa.curve_paths(action); _STATE["action_paths"]={(c.data_path,int(c.array_index)) for c in curves}
    expected_paths={(thigh.path_from_id("rotation_quaternion"),i) for i in range(4)}|{(rig.pose.bones[hem_name].path_from_id("location"),i) for i in range(3)}
    need(_STATE["action_paths"]==expected_paths and len(curves)==7 and rig.animation_data.action_slot is not None,"native Action/slot exact input whitelist failed")
    for curve in curves:
        for point in curve.keyframe_points: point.interpolation="LINEAR"
    need(cloth.show_viewport is False and cloth.show_render is False,"original Cloth must be paused before native seek")
    frozen_cache=same.cache_state(cloth,qa); baseline_identity=None; seq={}; samples=[]; body_samples={}
    def sample(label,original_mode=False):
        nonlocal baseline_identity
        budget(); began=time.perf_counter(); bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get(); graph_seconds=time.perf_counter()-began
        raw_program=raw_source_program_guard(rig,deform)
        raw=sample_raw(rig,input_rig,deform,graph,base); generated=driver_inventory(input_rig)
        matrix=base.manual_matrix_receipt(rig,input_rig,manual,graph,diag,metres)
        posed=rig.evaluated_get(graph);private_pose=input_rig.evaluated_get(graph)
        transform_proof={"input_object":base.conformal(private_pose.matrix_world,"live input world"),
            "source_object":base.conformal(source.evaluated_get(graph).matrix_world,"live source world"),
            "upstream":{name:base.conformal(posed.matrix_world@posed.pose.bones[name].matrix,"live upstream "+name) for name in upstream+[waist]},
            "native_space_diagnostic":base.upstream_pose_diagnostic(posed.matrix_world,private_pose.matrix_world,
                {name:posed.pose.bones[name].matrix for name in upstream+[waist]},
                {name:private_pose.pose.bones[name].matrix for name in upstream+[waist]},metres)}
        need(transform_proof["native_space_diagnostic"]["rig_world_exact"],"live POSE follow requires exact Rig world")
        closure=current_closure(source,rig,record,manual,controls,upstream+[waist],forbidden,graph,surface)
        refs=audit((before,after),after.modifiers[1]); meshes={}; read_clocks={}
        for key,obj in (("oracle",oracle),("before800",before),("after800",after)):
            began=time.perf_counter(); meshes[key]=read.native_mesh(obj,graph,diag);read_clocks[key]=time.perf_counter()-began
        transform_proof["before_world_chart"]=base.native_world_copy_proof(meshes["before800"]["matrix_world"],source.evaluated_get(graph).matrix_world,"live before Body")
        transform_proof["after_world_chart"]=base.native_world_copy_proof(meshes["after800"]["matrix_world"],actual.evaluated_get(graph).matrix_world,"live after Body")
        fields=("native_vertex_index_order","edges","faces","weights","native_group_mapping")
        identity={key:{field:mesh[field] for field in fields} for key,mesh in meshes.items()}
        need(all(len(mesh["points"])==800 and mesh["native_vertex_index_order"]==list(range(800)) and mesh["weights_complete"] for mesh in meshes.values()),"native 800 identity/weights missing")
        if baseline_identity is None: baseline_identity=identity
        need(identity==baseline_identity,"live input topology/groups/weights drifted")
        copied_raw=qa.raw_mesh_content(after);copied_raw["groups"]=copied_raw["groups"][:original_group_count]
        copied_raw["weights"]=[[w for w in row if w[0]<original_group_count] for row in copied_raw["weights"]]
        need(qa.raw_mesh_content(before)==raw_contract and copied_raw==raw_contract,"source/raw UV/groups/Keys changed")
        err=base.error_summary(meshes["before800"]["points"],meshes["oracle"]["points"],metres)
        effect={"raw80":base.error_summary(meshes["after800"]["points"],meshes["before800"]["points"],metres,ring),
            "outside720":base.error_summary(meshes["after800"]["points"],meshes["before800"]["points"],metres,[i for i in range(800) if i not in set(ring)])}
        pose=rig.evaluated_get(graph); knee=pose.matrix_world@pose.pose.bones[knee_name].head
        hem=pose.matrix_world@pose.pose.bones[hem_name].matrix.translation
        row={"label":label,"frame":[home.frame_current,home.frame_subframe],"original_active":qa.original.active(rig),"manual32":matrix,"raw_live_drivers":raw,"transform_proof":transform_proof,
             "generated_driver_inventory":{"count":generated["count"],"all_exact_SINGLE_PROP":True,"path_sha256":qa.digest(generated["paths"])},"raw_source_program":raw_program,"closure":closure,"reference_audit":refs,"before800_vs_native_Main_oracle":err,"attachment_effect":effect,
             "cache_exact":same.cache_state(cloth,qa)==frozen_cache,"physics_influence":float(qa.skirt.physics_control(source)[0]["physics_influence"]),
             "knee_world":list(knee),"hem_world":list(hem),"native_timing_segments":{"graph_ready_seconds":graph_seconds,"readback_seconds":read_clocks,"scope":"Direct phase clocks; excludes metrics/report/protection. Native Python update/readback, not GUI FPS."},
             "mesh_summaries":{key:same.summary(mesh["points"],qa) for key,mesh in meshes.items()},"accepted":False}
        if label in {"action_1_sequential","action_3_sequential"}:
            began=time.perf_counter(); points=qa.world_mesh(values["body"],graph)["points"]
            need(points and qa.finite(points),"registered Body native points unavailable/nonfinite")
            body_samples[home.frame_current]=points
            row["registered_Body_summary"]=same.summary(points,qa)
            row["native_timing_segments"]["registered_Body_readback_seconds"]=time.perf_counter()-began
        samples.append(row);report["live_samples"]=samples;write()
        need(matrix["same_native_Rig_world_exact"] and matrix["maximum_component_error"]<=4.e-5,"live Manual matrix > original4e-5")
        need(err["maximum_m"]<=guard and effect["outside720"]["maximum_m"]<=guard and row["cache_exact"],"live 50um/raw80/cache guard failed")
        return {"row":row,"points":{key:mesh["points"] for key,mesh in meshes.items()},"knee":list(knee),"hem":list(hem)}
    for frame in (1,2,3,4,5,3,1,5):
        budget(); began=time.perf_counter(); home.frame_set(frame); elapsed=time.perf_counter()-began
        current=sample("action_"+str(frame)+("_seek" if frame in seq else "_sequential"));current["row"]["frame_set_seconds"]=elapsed
        if frame in seq:
            repeated={key:base.error_summary(current["points"][key],seq[frame]["points"][key],metres) for key in current["points"]}
            report.setdefault("native_seek_replay",[]).append({"frame":frame,"errors":repeated});write()
            need(all(row["maximum_m"]<=guard for row in repeated.values()),"native seek input replay changed >50um")
        else: seq[frame]=current
    response={"knee_1_3_m":math.dist(seq[1]["knee"],seq[3]["knee"])*metres,"hem_1_3_m":math.dist(seq[1]["hem"],seq[3]["hem"])*metres,
              "native800_1_3":base.error_summary(seq[1]["points"]["before800"],seq[3]["points"]["before800"],metres),
              "actual_registered_Body_1_3":base.error_summary(body_samples[1],body_samples[3],metres)}
    report["live_Action_input_response"]=response;write()
    need(response["knee_1_3_m"]>height*.01*metres and response["hem_1_3_m"]>guard and response["native800_1_3"]["maximum_m"]>guard
         and response["actual_registered_Body_1_3"]["maximum_m"]>guard,"real Body/hem/native800 input response absent")
    # Detach only the new QA Action, restore artist frame/work pose while paused.
    rig.animation_data.action=None;_STATE["bound_qa_action"]=None
    restore_pose(rig,work_pose);home.frame_set(_STATE["frame"][0],subframe=_STATE["frame"][1]);bpy.context.view_layer.update()
    cloth.show_viewport,cloth.show_render=_STATE["cloth_flags"];bpy.context.view_layer.update()
    need(same.cache_state(cloth,qa)==frozen_cache,"original Cloth cache changed across pause/restore seek")
    report["original_phase_cache_scope"]={"original_cloth_flags_restored":True,"author_frame_restored":True,"no_frame_change_during_Original":True,"physics_bearing_automatic_original_exercised":False}
    surface.validate(source,rig,qa.skirt.read_record(source))
    original_frame=(home.frame_current,home.frame_subframe);c_before=qa.world_mesh(actual,bpy.context.evaluated_depsgraph_get())["points"]
    report["C_after_Action_restore_vs_before_pause"]=base.error_summary(c_before,_STATE["initial_C"],metres)
    write();need(report["C_after_Action_restore_vs_before_pause"]["maximum_m"]==0.,"restored same-frame original C changed after Action seek")
    before_switch=sample("public_Controls_before_Original")
    qa.skirt._activate(bpy.context,rig,"POSE");qa.public_switch(bpy.ops.character_designer.body_original_mode,action="ORIGINAL")
    need(qa.original.active(rig),"public Original did not enter")
    boundary_sync(input_rig,rig,deform,"public Original enter",report)
    entered=sample("public_Original_enter",True)
    enter_error=base.error_summary(entered["points"]["before800"],before_switch["points"]["before800"],metres)
    report["public_Original_enter_input_jump"]=enter_error;write();need(enter_error["maximum_m"]<=guard,"public Original enter changed manual input >50um")
    weighted=[name for name in sorted(deform) if any(weight>0. and group==rig.pose.bones[name].name for vertex in source.data.vertices for group,weight in [(source.vertex_groups[w.group].name,w.weight) for w in vertex.groups])]
    need(weighted,"no positively weighted original DEF")
    bone=rig.pose.bones[weighted[0]];bone.rotation_mode="QUATERNION";bone.rotation_quaternion=Quaternion(bone.rotation_quaternion)@Quaternion(Vector((1,0,0)),.1)
    boundary_sync(input_rig,rig,deform,"explicit Original edit rotation mode",report)
    rig.update_tag();bpy.context.view_layer.update();edited=sample("public_Original_DEF_edit",True)
    edit_error=base.error_summary(edited["points"]["before800"],entered["points"]["before800"],metres)
    report["public_Original_real_DEF_response"]={"bone":bone.name,"angle_rad":.1,"native_input_change":edit_error};write()
    need(edit_error["maximum_m"]>guard,"Original DEF edit did not affect actual native input")
    qa.public_switch(bpy.ops.character_designer.body_original_mode,action="CONTROLS");need(not qa.original.active(rig),"public Controls return failed")
    boundary_sync(input_rig,rig,deform,"public Controls return",report)
    returned=sample("public_Controls_after_Original")
    leave_error=base.error_summary(returned["points"]["before800"],edited["points"]["before800"],metres)
    report["public_Original_return_input_jump"]=leave_error
    report["public_Original_expected_correction"]={"weighted_bone":bone.name,"manual_mix_mode":rig.pose.bones[bone.name].constraints["Skirt manual pose"].mix_mode,
        "correction_metadata_present":bool(source.get(__import__("character_designer.skirt_original_mode",fromlist=["CORRECTIONS"]).CORRECTIONS))}
    c_after=qa.world_mesh(actual,bpy.context.evaluated_depsgraph_get())["points"]
    report["same_frame_C_guard"]={"maximum_m":base.error_summary(c_after,c_before,metres)["maximum_m"],"frame_exact":(home.frame_current,home.frame_subframe)==original_frame,
        "cache_exact":same.cache_state(cloth,qa)==frozen_cache};write()
    need(leave_error["maximum_m"]<=guard and report["same_frame_C_guard"]["maximum_m"]==0. and report["same_frame_C_guard"]["frame_exact"] and report["same_frame_C_guard"]["cache_exact"],"Original return/C/cache guard failed")
    need(report["public_Original_expected_correction"]["manual_mix_mode"]=="BEFORE_FULL" and report["public_Original_expected_correction"]["correction_metadata_present"],"public Original persistent correction rules missing")
    report["Keys_exercise"]={"source_Keys":None,"deliberately_exercised":False,"live_Key_Action_NLA_verified":False}
    report["live_manual_bridge_success"]=True;report["automatic_Original_semantic_acceptance"]=False
    report["before_attachment_reproduction_complete"]=True;report["native_completed"]=True
    report["native_endpoint_index_identity_exact"]=True
    values["endpoint_path"].write_text(json.dumps({"stage":report["stage"],"scope":"Compact native identity/point hashes; full vertex arrays deliberately not recorded",
        "samples":[{"label":row["label"],"frame":row["frame"],"mesh_summaries":row["mesh_summaries"]} for row in samples],"accepted":False},indent=2,allow_nan=False),encoding="utf-8")


def modified_sources(base):
    """Pinned, exact-count QA substitutions; canonical and frozen files untouched."""
    text=BASE_PATH.read_text(encoding="utf-8"); tree=ast.parse(text); nodes={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    main=ast.get_source_segment(text,nodes["main"]); closure=ast.get_source_segment(text,nodes["current_main_manual_closure"])
    edits=[]
    def replace(text,old,new,label):
        need(text.count(old)==1,"frozen replacement ABI not unique: "+label);edits.append(label);return text.replace(old,new,1)
    start=main.index('        sealed=json.loads(SEALED_REPORT.read_text(encoding="utf-8"))')
    stop=main.index('        # Build only after complete actual N/L/T evidence has been persisted.',start)
    main=main[:start]+'''        graph=bpy.context.evaluated_depsgraph_get()
        report["snapshot_replay_removed"]=True
        report["native_endpoint_index_identity_exact"]=False
'''+main[stop:];edits.append("remove frozen snapshot Main N/L/T replay")
    start=main.index('        def apply_input(snap):');stop=main.index('        # Native copied bound SurfaceDeform;',start)
    main=main[:start]+main[stop:];edits.append("remove private raw replay and first snapshot loop")
    start=main.index('        for label,snap in snapshots.items():');stop=main.index('    except Exception as error:',start)
    main=main[:start]+'''        exercise_live(locals(), FROZEN_BASE)
'''+main[stop:];edits.append("replace final snapshot loop by real live Action/public Original")
    main=replace(main,'        report["cache_before"]=same.cache_state(cloth,qa)',
                 '        report["live_program_receipt"]=capture_program(source,rig,cloth,home,qa,surface,same,actual,report)\n        report["cache_before"]=same.cache_state(cloth,qa)',"capture before any pause/binding")
    old='''            for obj in [input_rig,*wires,*mesh_objects]:
                for owner in (obj,obj.data,getattr(obj.data,"shape_keys",None)):
                    need(owner is None or owner.animation_data is None,"Owned input acquired Action/NLA/driver dependency")'''
    new='''            driver_inventory(input_rig)
            for obj in [input_rig,*wires,*mesh_objects]:
                for owner in (obj,obj.data,getattr(obj.data,"shape_keys",None)):
                    if owner is input_rig: continue
                    need(owner is None or owner.animation_data is None,"Owned non-driver input acquired animation")'''
    main=replace(main,old,new,"only input Rig exact generated drivers allowed")
    main=replace(main,'"private_drivers_actions_nla_absent":True',
                 '"private_playback_actions_nla_absent":True,"private_raw_drivers_exact":True',"report allowed raw drivers accurately")
    pause='        disabled.append((cloth,cloth.show_viewport,cloth.show_render)); cloth.show_viewport=cloth.show_render=False\n'
    main=replace(main,pause,'',"public setup validators run before original Cloth pause")
    main=replace(main,'        raw_contract=qa.raw_mesh_content(source); report["source_raw_contract"]=raw_contract',
                 pause+'        raw_contract=qa.raw_mesh_content(source); report["source_raw_contract"]=raw_contract',"pause before private construction and Action seeks")
    main=replace(main,'        cleanup_errors=[]', '''        cleanup_errors=[]
        try: restore_program(report,qa,surface)
        except Exception as error: cleanup_errors.append({"phase":"live_author_restore","message":str(error),"traceback":traceback.format_exc()})''',"all restoration then original cleanup")
    main=replace(main,'main_rest_receipt(rig,surface)==report["Main_Rest_flags_pointers_before"]',
                 'main_rest_receipt(rig,surface)==_STATE["initial_Main_rest"]',"final Main rest compared to pre-FK artist receipt")
    closure=replace(closure,'    need(anim is None or anim.action is None and not anim.nla_tracks,"Main playback binding must be privately detached by existing backup")',
                    '    bounded_animation_binding(rig)',"owned bounded Action/paused author NLA only")
    # No forbidden raw replay remains in either executable main or live routine.
    need("snapshots" not in main and "apply_input" not in main and "qa.restore_channels" not in main,"snapshot replay not fully removed")
    return main,closure,edits


def prepared_namespace(base):
    namespace=dict(vars(base));namespace.update(globals());namespace["__file__"]=str(Path(__file__))
    pins=dict(base.PINS);pins[base.ARTIST]=ARTIST_SHA;pins[BASE_PATH]=BASE_SHA;pins[TRANSITION]=TRANSITION_SHA;pins[BASE_RESULT]=BASE_RESULT_SHA
    namespace["PINS"]=pins;namespace["FROZEN_BASE"]=base
    main,closure,edits=modified_sources(base)
    exec(compile(closure,str(Path(__file__)),"exec"),namespace)
    namespace["current_closure"]=namespace["current_main_manual_closure"]
    # The helper remains in a separate immutable module; only this main's globals
    # supply the bounded closure and exact driver whitelist.
    namespace["exercise_live"]=lambda values,_unused:exercise_live(values,base)
    exec(compile(main,str(Path(__file__)),"exec"),namespace)
    return namespace,edits


def current_closure(*args):
    return _STATE["closure"](*args)


def pure_checks():
    from types import SimpleNamespace as NS
    base=load_base();main,closure,edits=modified_sources(base)
    ast.parse(main);ast.parse(closure)
    need(len(edits)==11,"expected eleven bounded substitutions")
    need("native_trs_copy_proof" in inspect.getsource(sample_raw) and "TRANSFORMS" not in inspect.getsource(setup_live_drivers),"raw driver route source guard")
    tree=ast.parse(inspect.getsource(exercise_live));calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
    need(not any(isinstance(n.func,ast.Name) and n.func.id=="replay" or isinstance(n.func,ast.Attribute) and n.func.attr in {"restore_channels","free_bake","bake"} for n in calls),"live exercise uses forbidden replay/cache APIs")
    need("home.frame_set" in inspect.getsource(exercise_live) and 'action="ORIGINAL"' in inspect.getsource(exercise_live) and 'action="CONTROLS"' in inspect.getsource(exercise_live),"real Action/public operation source missing")
    need(set(RAW_SIZES)==set(RAW_FIELDS) and sum(RAW_SIZES.values())==17,"raw arrays whitelist")
    saved_state=dict(_STATE); rejected=0
    try:
        action=object(); curves=[NS(data_path='pose.bones["Body"].rotation_quaternion',array_index=i,mute=False) for i in range(4)]
        track=NS(mute=True,is_solo=False);animation=NS(action=action,nla_tracks=[track],drivers=[]);rig=NS(animation_data=animation)
        _STATE.clear();_STATE.update({"bound_qa_action":action,"qa":NS(curve_paths=lambda a:curves),"action_paths":{(c.data_path,c.array_index) for c in curves}})
        need(bounded_animation_binding(rig),"owned Action whitelist positive")
        def refuses(change,undo):
            nonlocal rejected
            change()
            try: bounded_animation_binding(rig)
            except RuntimeError: rejected+=1
            else: raise RuntimeError("negative playback binding accepted")
            finally: undo()
        refuses(lambda:setattr(animation,"action",object()),lambda:setattr(animation,"action",action))
        refuses(lambda:setattr(track,"mute",False),lambda:setattr(track,"mute",True))
        refuses(lambda:setattr(track,"is_solo",True),lambda:setattr(track,"is_solo",False))
        refuses(lambda:setattr(curves[0],"mute",True),lambda:setattr(curves[0],"mute",False))
        previous=curves[0].data_path
        refuses(lambda:setattr(curves[0],"data_path",'pose.bones["DEF"].rotation_quaternion'),lambda:setattr(curves[0],"data_path",previous))
        need(rejected==5,"five unknown/muted/foreign binding controls")
        # Quote aliases are semantically identical native RNA paths; no tolerance.
        need(ast.dump(ast.parse('pose.bones["DEF"].location',mode="eval"))==ast.dump(ast.parse("pose.bones['DEF'].location",mode="eval")),"raw writer quote alias guard")
    finally:
        _STATE.clear();_STATE.update(saved_state)
    # Check true existing native transport interfaces instead of invented mocks.
    abi={base.REPOSITORY/"addons/character_designer/skirt_rig.py":{"_context_state":1,"_restore_context":2,"_activate":2,"physics_control":1},
         HERE/"validate_real_dress.py":{"public_switch":1,"curve_paths":1,"body_inputs":2,"world_mesh":2,"pose_channels":1},
         HERE/"verify_actual_body_proxy_coverage.py":{"native_mesh":3},HERE/"verify_actual_same_frame_pose.py":{"summary":2,"cache_state":2}}
    count=0
    for path,wanted in abi.items():
        definitions={n.name:n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n,ast.FunctionDef)}
        for name,positionals in wanted.items():
            need(name in definitions,"actual native API missing: "+name)
            node=definitions[name];minimum=len(node.args.posonlyargs)+len(node.args.args)-len(node.args.defaults)
            need(minimum<=positionals<=len(node.args.posonlyargs)+len(node.args.args),"actual native API arity: "+name);count+=1
    need(sha(TRANSITION)==TRANSITION_SHA and sha(BASE_RESULT)==BASE_RESULT_SHA,"new typed provenance pin")
    old=json.loads(BASE_RESULT.read_text(encoding="utf-8"))
    need(old["native_completed"] and old["ready_for_next_private_gate"] and not old["cleanup_errors"],"50e component evidence invalid")
    return {"passed":True,"bounded_QA_substitutions":edits,"actual_native_API_sites":count,"playback_whitelist_controls":1+rejected,"native_run":False,"accepted":False,
            "automatic_original_and_live_solver_feedback_unproven":True}


def arguments():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path);parser.add_argument("--max-seconds",type=float,default=120.);parser.add_argument("--pure-checks",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and not args.output.exists() and args.output.resolve().is_relative_to(HERE) and args.output.resolve()!=HERE,"fresh private Validation output required")
        need(0.<args.max_seconds<=120.,"Root external180s / soft120s only")
    return args


def main(args):
    if args.pure_checks:
        print(json.dumps(pure_checks()));return 0
    base=load_base(); namespace,edits=prepared_namespace(base)
    _STATE["closure"]=namespace["current_main_manual_closure"]
    # capture_program clears state: pass the closure independently via a wrapper.
    original_capture=capture_program
    def capture(*values):
        receipt=original_capture(*values);_STATE["closure"]=namespace["current_main_manual_closure"];return receipt
    namespace["capture_program"]=capture
    return namespace["main"](args)


if __name__=="__main__": raise SystemExit(main(arguments()))
