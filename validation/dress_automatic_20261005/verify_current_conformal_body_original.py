"""One bounded real Body change and official Original/Controls roundtrip.

Reuse frozen V5 construction and its complete raw/ID/cache/reload/source/disk
AND. The source still uses legacy reference; private CFK output and legacy
output have independent results. No source/schema installation, private flag
substitution, new Action/curve, animation detachment, cache work or run60.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import traceback

import bpy
from mathutils import Quaternion, Vector

HERE = Path(__file__).resolve().parent
COMPONENT = HERE / "prototype_neutral_manual_current_conformal_fk_reference_v5.py"
COMPONENT_SHA = "eff319f4dbca6290aa9f02a61d3ab57eef57690017e198786a3b48d1c30e8441"
ROOT_CONTROL = "CTRL_master"


def require(condition, message):
    if not condition:
        raise RuntimeError("Current CFK Body/Original QA: " + message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(source, actual, neutral, graph, diag, helper):
    result = {}
    for label,obj in (("H0",neutral),("O",source),("C",actual)):
        mesh = diag.json_content(diag.mesh_snapshot(obj,graph))
        result[label] = {"points": mesh["points"], "structure": {key:mesh[key] for key in ("faces","edges","weights")},
                         "native_triangles": mesh["triangles"], "points_sha256": helper.sha_values(mesh["points"])}
    require([len(result[key]["points"]) for key in ("H0","O","C")] == [800,3040,800], "snapshot layout differs")
    return result


def chart_now(component, surface, rig, reference, record, graph):
    rows = {}
    upstream = surface._ancestors(rig,record) + [record["controls"]["waist"]]
    for label,obj in (("MainObject",rig),("CurrentCFKObject",reference)):
        posed = obj.evaluated_get(graph)
        rows[label] = component.conformal_matrix(posed.matrix_world)
        for name in upstream:
            bone = posed.pose.bones.get(name)
            rows[label+"/"+name] = (component.conformal_matrix(posed.matrix_world @ bone.matrix) if bone is not None
                                     else {"admissible_current_chart":False,"bone_exists":False})
    return {"samples":rows, "within_declared_current_domain":all(row["admissible_current_chart"] for row in rows.values()),
            "relative_F32_storage_bound":1.e-6, "future_body_domain_proved":False}


def transform_conflicts(rig, bone, qa):
    fields = ("location","rotation_euler","rotation_quaternion","rotation_axis_angle","scale","rotation_mode")
    paths = {bone.path_from_id(field) for field in fields}

    def targeted(path):
        if path in paths:
            return True
        match = re.fullmatch(r"pose\.bones\[(.+)\]\.([A-Za-z_]+)",path)
        if match is None or match.group(2) not in fields:
            return False
        try:
            return ast.literal_eval(match.group(1)) == bone.name
        except (SyntaxError, ValueError):
            return False

    animation = rig.animation_data
    actions = [animation.action] if animation and animation.action else []
    if animation:
        actions += [strip.action for track in animation.nla_tracks if not track.mute for strip in track.strips if strip.action]
    return {"active_action_or_unmuted_NLA": [curve.data_path for action in actions for curve in qa.curve_paths(action) if targeted(curve.data_path)],
            "drivers": [curve.data_path for curve in animation.drivers if targeted(curve.data_path)] if animation else []}


def pose_restore(rig, channels):
    errors = []
    for name,row in channels.items():
        try:
            bone = rig.pose.bones[name]
            bone.rotation_mode = row["mode"]
            bone.location, bone.scale = row["location"],row["scale"]
            bone.rotation_quaternion, bone.rotation_euler = row["quaternion"],row["euler"]
            bone.rotation_axis_angle = row["axis_angle"]
        except Exception as error:
            errors.append(name+": "+str(error))
    rig.update_tag()
    bpy.context.view_layer.update()
    require(not errors, "original raw pose restore incomplete: "+"; ".join(errors))


def comparison(component, before, after, metres):
    row = component.geometry_receipts(before,after,metres)
    measures = row["measurements"]
    row["within_unchanged_50um_C0_structure"] = (measures["H0"]["maximum_m"] <= 5.e-5
        and measures["O"]["maximum_m"] <= 5.e-5 and measures["C"]["maximum_m"] == 0.
        and all(item["structure_exact"] for item in measures.values()))
    return row


def body_comparison(before, after, metres):
    left,right = before["points"],after["points"]
    count_exact = bool(left) and len(left)==len(right)
    distances = [math.dist(a,b)*metres for a,b in zip(left,right)]
    require(all(math.isfinite(value) for value in distances), "registered Body comparison has nonfinite geometry")
    index = max(range(len(distances)),key=distances.__getitem__) if distances else None
    row = {"count_exact":count_exact,"edges_exact":before["edges"]==after["edges"],
           "maximum_m":distances[index] if index is not None else None,"worst_vertex_index":index,
           "before_world":left[index] if index is not None else None,"after_world":right[index] if index is not None else None,
           "unchanged_body_guard_m":5.e-5}
    row["same_evaluated_body_within_50um"] = (count_exact and row["edges_exact"] and row["maximum_m"]<=5.e-5)
    return row


def exercise(component, values, wrapper_sha):
    report,source,rig,actual,cloth,neutral = (values[name] for name in ("report","source","rig","actual","cloth","neutral"))
    preview,reference,h0 = (values[name] for name in ("preview","candidate","clone_surface"))
    qa,diag,surface,helper,record,destination = (values[name] for name in ("qa","diag","surface","helper","record","destination"))
    from character_designer import skirt_original_mode
    row = {"private_component_public_switch_success":False, "legacy_source_public_nojump":False,
           "formal_schema_installed":False, "production_effect_accepted":False, "public_source_repaired":False,
           "private_current_domain_only":True, "wrapper_sha256":wrapper_sha, "stages":[],
           "scope":"Official Body coordinator on unchanged legacy source; measured independent private CFK output"}
    report["bounded_body_original_regression"] = row
    channels = qa.pose_channels(rig)
    cache = helper.cache_semantics(cloth,qa,surface)
    bindings = helper.author_bindings(surface)
    correction = source.get(skirt_original_mode.CORRECTIONS)
    context_state = surface.skirt._context_state(bpy.context)
    frame = (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
    private_birth = values["after"]
    body,status = qa.registered_body(bpy.context,rig,argparse.Namespace(body_vertex_limit=100000))
    row["registered_body"] = status
    require(body is not None, "actual registered Body mesh is unavailable; no guessed replacement")
    require(not qa.original.active(rig), "fixture must start in actual Controls without an Original session")
    control = rig.pose.bones.get(ROOT_CONTROL)
    require(control is not None and not control.bone.use_deform, "real native root control is unavailable")
    conflicts = transform_conflicts(rig,control,qa)
    row["input_guard"] = {"control":ROOT_CONTROL,"angle_rad":.10,"rig_axis":"Z","authored_transform_conflicts":conflicts,
                          "no_Action_NLA_curve_driver_was_changed":True}
    require(not any(conflicts.values()), "author transform playback controls the real Body input; preserve it")

    def persist():
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")

    def sample(label):
        graph = bpy.context.evaluated_depsgraph_get()
        result = {"label":label,"frame":bpy.context.scene.frame_current,"subframe":bpy.context.scene.frame_subframe,
                  "same_graph_pointer":graph.as_pointer(),"original_session_active":qa.original.active(rig),
                  "legacy":snapshot(source,actual,neutral,graph,diag,helper),
                  "private":snapshot(preview,actual,h0,graph,diag,helper),
                  "Body":diag.json_content(qa.world_mesh(body,graph)),"current_domain":chart_now(component,surface,rig,reference,record,graph),
                  "Hips_evaluated_matrix":surface._matrix(rig.evaluated_get(graph).pose.bones["Hips"].matrix),
                  "cache_exact":helper.cache_semantics(cloth,qa,surface)==cache,
                  "frame_exact":(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)==frame}
        result["private_vs_legacy"] = comparison(component,result["legacy"],result["private"],bpy.context.scene.unit_settings.scale_length)
        row["stages"].append(result)
        persist()
        return result

    primary_error = None
    cleanup_errors = []
    try:
        initial = sample("before_real_body_change")
        axis = (control.bone.matrix_local.to_3x3().inverted() @ Vector((0.,0.,1.))).normalized()
        before_rotation = control.matrix_basis.to_quaternion()
        control.rotation_mode = "QUATERNION"
        control.rotation_quaternion = before_rotation @ Quaternion(axis,.10)
        rig.update_tag()
        bpy.context.view_layer.update()
        changed = sample("after_real_body_change")
        metres = bpy.context.scene.unit_settings.scale_length
        row["real_body_input"] = {"body_world_delta_m":max(math.dist(a,b)*metres for a,b in zip(initial["Body"]["points"],changed["Body"]["points"])),
                                  "Hips_matrix_delta":max(abs(initial["Hips_evaluated_matrix"][i][j]-changed["Hips_evaluated_matrix"][i][j]) for i in range(4) for j in range(4)),
                                  "body_count_exact":len(initial["Body"]["points"])==len(changed["Body"]["points"]),
                                  "C_real_body_delta_m":comparison(component,initial["private"],changed["private"],metres)["measurements"]["C"]["maximum_m"],
                                  "C_real_body_delta_is_diagnostic_only":True}
        persist()
        surface.skirt._activate(bpy.context,rig,"POSE")
        qa.public_switch(bpy.ops.character_designer.body_original_mode,action="ORIGINAL")
        entered = sample("after_official_public_Original")
        row["public_enter"] = {"coordinator":"bpy.ops.character_designer.body_original_mode(action=ORIGINAL)",
            "actual_session_active":qa.original.active(rig),"private":comparison(component,changed["private"],entered["private"],metres),
            "legacy":comparison(component,changed["legacy"],entered["legacy"],metres),
            "evaluated_Body":body_comparison(changed["Body"],entered["Body"],metres)}
        persist()
        qa.public_switch(bpy.ops.character_designer.body_original_mode,action="CONTROLS")
        returned = sample("after_official_public_Controls")
        row["public_return"] = {"coordinator":"bpy.ops.character_designer.body_original_mode(action=CONTROLS)",
            "actual_session_inactive":not qa.original.active(rig),"private":comparison(component,changed["private"],returned["private"],metres),
            "legacy":comparison(component,changed["legacy"],returned["legacy"],metres),
            "evaluated_Body":body_comparison(changed["Body"],returned["Body"],metres)}
        persist()
    except Exception:
        primary_error = traceback.format_exc()
        row["error"] = primary_error
    finally:
        # Use the official leave, then restore the original raw pose without any
        # helper that detaches Action/NLA or rewrites object basis/cache/frame.
        try:
            if qa.original.active(rig):
                qa.public_switch(bpy.ops.character_designer.body_original_mode,action="CONTROLS")
        except Exception as error:
            cleanup_errors.append("official Controls cleanup: "+str(error))
        try:
            pose_restore(rig,channels)
        except Exception as error:
            cleanup_errors.append("raw pose cleanup: "+str(error))
        try:
            surface.skirt._restore_context(bpy.context,context_state)
            bpy.context.view_layer.update()
            restored = sample("after_raw_body_input_restore")
            row["birth_output_restore"] = comparison(component,private_birth,restored["private"],bpy.context.scene.unit_settings.scale_length)
            row["raw_pose_exact"] = qa.pose_channels(rig)==channels
            row["bindings_exact"] = helper.author_bindings(surface)==bindings
            row["correction_metadata_exact"] = source.get(skirt_original_mode.CORRECTIONS)==correction
            row["actual_public_session_closed"] = not qa.original.active(rig)
        except Exception as error:
            cleanup_errors.append("final stage/current state proof: "+str(error))
        row["cleanup_errors"] = cleanup_errors
        expected = ["before_real_body_change","after_real_body_change","after_official_public_Original","after_official_public_Controls","after_raw_body_input_restore"]
        stages = row["stages"]
        body_input = row.get("real_body_input",{})
        row["wrapper_component_source_exact"] = sha(COMPONENT)==COMPONENT_SHA and sha(Path(__file__))==wrapper_sha
        row["same_pose_body_change_equivalence"] = (len(stages)>=2
            and all(stage["private_vs_legacy"]["within_unchanged_50um_C0_structure"] for stage in stages[:2]))
        row["private_component_public_switch_success"] = (primary_error is None and not cleanup_errors
            and [stage["label"] for stage in stages]==expected and body_input.get("body_count_exact") is True
            and body_input.get("body_world_delta_m",0.)>1.e-5 and body_input.get("Hips_matrix_delta",0.)>4.e-5
            and all(stage["current_domain"]["within_declared_current_domain"] and stage["cache_exact"] and stage["frame_exact"] for stage in stages)
            and row.get("public_enter",{}).get("actual_session_active") is True
            and row.get("public_return",{}).get("actual_session_inactive") is True
            and row.get("public_enter",{}).get("evaluated_Body",{}).get("same_evaluated_body_within_50um") is True
            and row.get("public_return",{}).get("evaluated_Body",{}).get("same_evaluated_body_within_50um") is True
            and row.get("public_enter",{}).get("private",{}).get("within_unchanged_50um_C0_structure") is True
            and row.get("public_return",{}).get("private",{}).get("within_unchanged_50um_C0_structure") is True
            and row.get("birth_output_restore",{}).get("within_unchanged_50um_C0_structure") is True
            and all(row.get(key) is True for key in ("same_pose_body_change_equivalence","raw_pose_exact","bindings_exact","correction_metadata_exact","actual_public_session_closed","wrapper_component_source_exact")))
        row["legacy_source_public_nojump"] = (row.get("public_enter",{}).get("legacy",{}).get("within_unchanged_50um_C0_structure") is True
            and row.get("public_return",{}).get("legacy",{}).get("within_unchanged_50um_C0_structure") is True)
        persist()
    require(row["private_component_public_switch_success"], "bounded private CFK Body/official Original regression failed; all receipts are preserved")


def main():
    require(sha(COMPONENT)==COMPONENT_SHA, "frozen actual-native V5 component changed")
    wrapper_sha = sha(Path(__file__))
    spec = importlib.util.spec_from_file_location("bounded_current_cfk_component",COMPONENT)
    component = importlib.util.module_from_spec(spec)
    require(spec.name not in sys.modules, "private V5 module already loaded")
    sys.modules[spec.name] = component
    spec.loader.exec_module(component)
    original = component.guarded_comparison
    receipt = set()

    def after_comparison(*args,**kwargs):
        result = original(*args,**kwargs)
        if args[1]=="converted_vs_original":
            frame = sys._getframe(1)
            require(frame.f_code is component.main.__code__ and not receipt, "bounded callback caller/count differs")
            receipt.add("bounded_body_original")
            exercise(component,dict(frame.f_locals),wrapper_sha)
        return result

    component.guarded_comparison = after_comparison
    try:
        result = component.main()
        require(result!=0 or receipt=={"bounded_body_original"}, "V5 success did not exercise the real public regression")
        return result
    finally:
        component.guarded_comparison = original
        require(sha(COMPONENT)==COMPONENT_SHA and sha(Path(__file__))==wrapper_sha, "frozen wrapper/component source changed")


if __name__=="__main__":
    raise SystemExit(main())
