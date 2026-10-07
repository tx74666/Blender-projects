"""PREPARED ONLY: contact-only gold800 dynamic-Rest Cloth -> Subsurf3040.

Root leases factory Blender5.1/disable-autoexec/threads1. Default soft120s /
external180s; explicit soft180s requires root's external240s lease.
One owned 30-step world-geometry N/L/T path is synthetic, not author Actions /
intermediate skeletal poses / live Original. Reuse only the immutable completed
no-contact limited gate; its partially completed total run remains failed.
Actual gold input50um remains strict. Output residual is not a readback pass.
No artist application/bake/cache replacement/accepted artistic result.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time
import traceback
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
INPUT_HELPER=HERE/"prototype_input800_reproduction_v5.py"
CONTINUOUS=HERE/"prototype_static_continuous_contact_preview.py"
STATIC=HERE/"prototype_static_final_cloth_relax.py"
PREDECESSOR=HERE/"prototype_dynamic_rest800_contact_preview.py"
CONTACT_BASE=HERE/"prototype_dynamic_rest800_contact_preview_v2.py"
POINTER_PREDECESSOR=HERE/"prototype_dynamic_rest800_contact_only_preview.py"
POINTER_FAILURE=HERE/"actual_dynamic_rest800_contact_only_51_20261006_163108_162/result/dynamic_rest800_preview.json"
NO_CONTACT_REPORT=HERE/"actual_dynamic_rest800_contact_v2_51_20261006_160848_037/result/dynamic_rest800_preview.json"
FRESH_REPORTS={
    "V4":HERE/"actual_input800_reproduction_v4_51_20261006_150056_469/result/input800_reproduction.json",
    "V5":HERE/"actual_input800_reproduction_v5_51_20261006_151817_951/result/input800_reproduction.json"}
LOCAL_PINS={INPUT_HELPER:"5fd504b518b8a76e1a1faec1cc03cebcbe07eff07ce2570ef8b779af2df3f305",
    CONTINUOUS:"9366a924d4bf5e1cfe30dafa8ceef020db774130d9c66e153fc661517988f8fe",
    STATIC:"06b7f1656dcb8a68ad5ddf9b92ec005a6b7c3cf2968eb60825e48f5de5721e1e",
    PREDECESSOR:"c7c409c6621b128699bbaf59f3b995cf32e3181d29500ba39dbc5e73edc7593c",
    CONTACT_BASE:"a10e633e80f95fb8ba16d198d5c4429a2ca331210f3540e684e6551e725c961d",
    POINTER_PREDECESSOR:"dd75243261da55395e13508863b20f46eaec76a13ca682e9386cf97816f5901c",
    POINTER_FAILURE:"af5c3d1598cc23746d909845eedef3a4b63ec6f2c3235fb2162df8e217ec513c",
    NO_CONTACT_REPORT:"6f34bc55b6f895d27d368da68320328e86d874ea0d0ce814108d7dd4ff82a855",
    FRESH_REPORTS["V4"]:"0666a7fbe5b5625f30cd738ee5930f63de2e5169049852cefbbdb0329353b1c4",
    FRESH_REPORTS["V5"]:"620ef945bd3e6a8dc8f31b9815b4b35c946d6256bea926f43349feb41bcf6d03"}
PIN="QA Dynamic Rest Pin"
STEPS=30
LIMITS={"edge_min":.25,"edge_max":2.,"area_min":.1}
OFFICIAL="https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/blenkernel/intern/cloth.cc"
V2_FIELDS=set("""accepted actual_inputs animation_backup artist_saved author_frame author_frame_after_reload_exact
author_playback author_pose cache_after cache_before cache_metadata_exact canonical_validation_after_reload
canonical_validation_before_private_ids checks cleanup_errors elapsed_seconds exception files_after files_before
geometry_guard_m input_artist_disk_exact input_rig_native_parent_map input_rig_rest install_input native_completed
native_endpoint_file native_endpoint_index_identity_exact owned_cleanup_exact pins playback_after_reload_exact
pose_after_reload_exact protection_after_reload protection_before_reload pure_checks ready_for_next_private_gate
registered_body samples saved_cache_preflight scope script_disk_exact script_sha256 source_after source_before
source_disk_exact source_raw_contract source_raw_keys_initial stage units_to_metres""".split())
HISTORY_TRUE_FIELDS=("canonical_validation_before_private_ids","canonical_validation_after_reload",
    "native_endpoint_index_identity_exact","owned_cleanup_exact","cache_metadata_exact",
    "pose_after_reload_exact","playback_after_reload_exact","author_frame_after_reload_exact",
    "source_disk_exact","input_artist_disk_exact","script_disk_exact")
CACHE_FIELD_TYPES={"pointer":int,"start":int,"end":int,"step":int,"index":int,
    "is_baked":bool,"disk":bool,"external":bool,"is_baking":bool,"is_outdated":bool,"library_path":bool,
    "name":str,"info":str,"filepath":str}


def need(ok,message):
    if not ok:raise RuntimeError(message)


def sha(path):
    result=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):result.update(block)
    return result.hexdigest()


def helper(path):
    need(sha(path)==LOCAL_PINS[path],"Frozen helper changed: "+str(path))
    spec=importlib.util.spec_from_file_location("dynamic800_"+path.stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module  # No helper main/native arguments are executed.


def history_proof(sealed,fresh,current_source,pins,endpoint_path,endpoint_hash):
    """Actual pinned report ABI. Missing V2 helper-final status stays Unrecorded.

    The failed private stages are not successes. Current hashes and later
    protected exact Main800/Body replays support only this fixed snapshot input.
    Later reports did not replay the four colliders: their worldgeometry remains
    the original same-graph capture, never relabelled a fresh collider test.
    """
    need(set(sealed)==V2_FIELDS,"Pinned V2 report schema differs")
    need(set(fresh)=={"V4","V5"},"Both protected fresh Main replay reports required")
    current={str(Path(path).resolve()).casefold():value for path,value in pins.items()}
    receipt={"V2_helper_final_status":"Unrecorded","fresh_main_replays":{},
        "current_pin_validation":"Exact hashes checked independently before native and in final AND",
        "collider_provenance":"Original V2 same-depsgraph four-collider world meshes from exact installed INPUT",
        "fresh_collider_replay_measured":False,"private_input_reproduction_accepted":False,
        "snapshot_reuse_only":True,"accepted":False}
    for label,row in (("V2",sealed),*fresh.items()):
        expected=V2_FIELDS if label=="V2" else V2_FIELDS|{"sealed_input_replay","frozen_pins_disk_exact"}|({"native_space_diagnostics"} if label=="V5" else set())
        need(set(row)==expected,"Pinned history schema differs: "+label)
        need(all(name in row and row[name] is True for name in HISTORY_TRUE_FIELDS),"Recorded history protection failed/missing: "+label)
        need(not row["cleanup_errors"] and all(row[name]["success"] is True for name in ("protection_before_reload","protection_after_reload")),"Recorded raw/reload protection failed: "+label)
        need(row["source_before"]==row["source_after"]==current_source and row["files_before"]==row["files_after"],"Historical source/input identity differs: "+label)
        need(row["geometry_guard_m"]==5.e-5 and row["accepted"] is False and row["artist_saved"] is False
            and row["native_completed"] is False and row["ready_for_next_private_gate"] is False,"Failed private stage must stay failed: "+label)
        need(all(current.get(str(Path(path).resolve()).casefold())==value for path,value in row["pins"].items()),"Recorded historical pin is outside current exact pins: "+label)
        script=HERE/("prototype_input800_reproduction_"+label.lower()+".py")
        need(row["script_sha256"]==current[str(script.resolve()).casefold()],"Historical script identity differs: "+label)
        if label=="V2":
            need("frozen_pins_disk_exact" not in row and Path(row["native_endpoint_file"]["path"]).resolve()==Path(endpoint_path).resolve()
                and row["native_endpoint_file"]["sha256"]==endpoint_hash,"Original capture identity differs")
            continue
        need(row["frozen_pins_disk_exact"] is True,"Recorded later helper-final status failed: "+label)
        replay=row["sealed_input_replay"]
        need(replay["endpoint_sha256"]==endpoint_hash and Path(replay["endpoint"]).resolve()==Path(endpoint_path).resolve()
            and replay["report_sha256"]==current[str(Path(replay["report"]).resolve()).casefold()],"Later replay provenance differs: "+label)
        proofs=replay["fresh_main_oracle_and_body"];need(set(proofs)=={"N","L","T"},"Fresh replay incomplete: "+label)
        for state,meshes in proofs.items():
            need(set(meshes)=={"oracle","Body"},"Fresh Main replay mesh schema differs")
            for role,count in (("oracle",800),("Body",14470)):
                value=meshes[role]
                need(value["count"]==count and value["maximum_m"]==value["rms_m"]==0.,"Fresh Main replay is not exact: "+label+"/"+state+"/"+role)
            for field in ("main_native_pose_channels","native_Key_values","main_native_oracle_identity","source_frame","rig_world","upstream_world"):
                need(replay["primitive_comparisons"][state][field]["primitive_exact_equal"] is True,"Fresh Main ABI/inputs differ: "+label)
        receipt["fresh_main_replays"][label]={"helper_final_status":"RecordedTrue","source_raw_cache_reload_AND":True,
            "actual_Main800_Body_N_L_T":proofs,"failed_private_stage_completed":row["native_completed"],
            "original_private_failure":row["exception"]["message"]}
    return receipt


def history_abi_controls():
    """Read the actual small reports, not invented default booleans or schema."""
    prepared=helper(INPUT_HELPER);pins=prepared.PINS|LOCAL_PINS
    paths={"V2":prepared.SEALED_REPORT,**FRESH_REPORTS}
    need(all(sha(path)==pins[path] for path in paths.values()),"Pinned report ABI fixture changed")
    rows={label:json.loads(path.read_text(encoding="utf-8")) for label,path in paths.items()}
    source=rows["V2"]["source_after"]
    proof=history_proof(rows["V2"],{label:rows[label] for label in FRESH_REPORTS},source,pins,prepared.SEALED_ENDPOINT,pins[prepared.SEALED_ENDPOINT])
    need(proof["V2_helper_final_status"]=="Unrecorded" and proof["fresh_collider_replay_measured"] is False,"Missing history must not become True")
    import copy
    cases=[]
    def reject(a,b,p=pins):
        try:history_proof(a,b,source,p,prepared.SEALED_ENDPOINT,pins[prepared.SEALED_ENDPOINT])
        except (RuntimeError,KeyError):return
        raise RuntimeError("Corrupt historical fixture accepted")
    fresh={label:rows[label] for label in FRESH_REPORTS}
    bad=copy.deepcopy(rows["V2"]);del bad["cache_metadata_exact"];reject(bad,fresh);cases.append("missing_recorded_cache")
    bad=copy.deepcopy(rows["V2"]);bad["cache_metadata_exact"]=False;reject(bad,fresh);cases.append("false_recorded_cache")
    bad=copy.deepcopy(rows["V2"]);bad["frozen_pins_disk_exact"]=True;reject(bad,fresh);cases.append("invented_V2_helper_status")
    bad=copy.deepcopy(fresh);bad["V5"]["frozen_pins_disk_exact"]=False;reject(rows["V2"],bad);cases.append("later_helper_failed")
    bad=copy.deepcopy(fresh);bad["V4"]["sealed_input_replay"]["fresh_main_oracle_and_body"]["T"]["Body"]["maximum_m"]=1.e-9;reject(rows["V2"],bad);cases.append("nonexact_actual_Body")
    bad=copy.deepcopy(fresh);bad["V5"]["sealed_input_replay"]["primitive_comparisons"]["L"]["source_frame"]["primitive_exact_equal"]=False;reject(rows["V2"],bad);cases.append("fresh_parent_chart_changed")
    bad=dict(pins);bad[prepared.SURFACE]="0"*64;reject(rows["V2"],fresh,bad);cases.append("current_source_pin_changed")
    return {"passed":True,"real_report_field_counts":{label:len(row) for label,row in rows.items()},"positive":1,"negative":cases,
        "history_missing_status":"Unrecorded","native_run":False,"accepted":False}


def no_contact_proof(prior,pins,current_source,current_files):
    """Reuse the measured limited phase only; no upgrade of the failed total."""
    required=("canonical_validation_before_owned","owned_cleanup_exact","original_ID_inventory_exact",
        "cache_metadata_exact","canonical_validation_after_cleanup","pose_after_reload_exact",
        "playback_after_reload_exact","author_frame_after_reload_exact","source_disk_exact",
        "input_artist_disk_exact","script_disk_exact","frozen_pins_disk_exact","terminal_AND")
    need(all(name in prior and prior[name] is True for name in required) and not prior["cleanup_errors"],"Prior no-contact terminal protection missing/failed")
    need(all(prior[name]["success"] is True for name in ("protection_before_reload","protection_after_reload")),"Prior no-contact raw/reload protection failed")
    need(prior["native_completed"] is False and prior["accepted"] is False and prior["artist_saved"] is False
        and prior["error"]["reason"]=="Private preview soft120s phase budget exhausted", "Prior partial total must stay failed")
    need(prior["source_before"]==prior["source_after"]==current_source and prior["files_before"]==current_files
        and prior["cache_before"]==prior["cache_after"],"Prior no-contact input/source/cache provenance differs")
    current={str(Path(path).resolve()).casefold():value for path,value in pins.items()}
    need(prior["script_sha256"]==current[str(CONTACT_BASE.resolve()).casefold()]
        and all(current.get(str(Path(path).resolve()).casefold())==value for path,value in prior["pins"].items()),"Prior no-contact exact pins differ")
    phase=prior["trials"]["no_contact"];partial=prior["trials"]["contact"]
    need(phase["completed"] is True and phase["accepted"] is False and partial["completed"] is False
        and len(partial["path_readback"])==6,"Prior phase-completion schema differs")
    response=phase["manual_response"]
    need(all(response[name] is True for name in ("limited_response_gate","limited_shape_gate","proceed_to_contact"))
        and response["manual_fidelity_accepted"] is False and response["accepted"] is False
        and response["limits"]==LIMITS and len(response["measured_manual_region_ids"])==2880,"Prior limited Manual gate failed/differs")
    need(prior["input_guard_m"]==5.e-5 and phase["parameters"]["effectors"]["gravity"]==0.
        and phase["parameters"]["steps"]==30,"Prior no-contact condition differs")
    gain,response_max=response["aggregate_dot_gain"],response["response_maximum_m"]
    need(math.isfinite(gain) and gain>0. and math.isfinite(response_max) and response_max>prior["input_guard_m"],"Prior measured response is not positive")
    rows=phase["path_readback"];precision=prior["input_readback_microguard"]["metres"]
    need(math.isfinite(precision) and 0.<precision<=1.e-5 and [row["frame"] for row in rows]==list(range(1,32))
        and set(phase["samples"])=={"N","L","T"},"Prior 30-step / microguard evidence incomplete")
    roles=set(rows[0]["input_errors"])
    need(roles=={"ManualOracle800","RegisteredBody"}|set(partial["parameters"]["collider_scalars"]) and len(roles)==6,"Prior exact input role inventory incomplete")
    for row in rows:
        need(set(row["input_errors"])==roles,"Prior same-frame role input evidence incomplete")
        for error in row["input_errors"].values():
            need(math.isfinite(error["maximum_m"]) and 0.<=error["maximum_m"]<=min(5.e-5,precision),"Prior actual input precision failed")
        pin=row["raw80_relative_current_pin_error"]
        need(pin["count"]==80 and math.isfinite(pin["maximum_m"]) and 0.<=pin["maximum_m"]<=precision,"Prior raw80 current pin guard failed")
    edge=phase["samples"]["T"]["quality"]["edge_ratios"];area=phase["samples"]["T"]["quality"]["triangle_area_ratios_on_recorded_corner_triplets"]
    need(edge["unresolved_degenerate_baseline"]==area["unresolved_degenerate_baseline"]==0
        and edge["minimum"]>=LIMITS["edge_min"] and edge["maximum"]<=LIMITS["edge_max"] and area["minimum"]>=LIMITS["area_min"],"Prior limited shape metrics failed")
    for role in ("RegisteredBody",prior["Body_clone_endpoints"]["N"]["actual_clone_object"]):
        crossing=phase["samples"]["N"]["final3040_crossings"][role]
        need(crossing["status"]=="measured" and crossing["actual_crossing_pair_count"]==0,"Prior safe N crossing prerequisite failed")
    return {"path":str(NO_CONTACT_REPORT),"sha256":pins[NO_CONTACT_REPORT],"script_sha256":prior["script_sha256"],
        "original_total_native_completed":False,"original_partial_contact_frames":len(partial["path_readback"]),
        "completed_no_contact_frames":len(rows),"source_raw_cache_reload_AND":True,"limited_response_shape_gate":True,
        "aggregate_dot_gain":gain,"response_rms_m":response["response_rms_m"],
        "T_minus_L_response_residual_maximum_m":response["T_minus_L_response_residual_maximum_m"],
        "manual_fidelity_accepted":False,"scope":"Only the completed finite/positive-response prerequisite is reused; prior partial total, contact clearance, Manual fidelity and artwork remain unaccepted.","accepted":False}


def no_contact_abi_controls():
    prepared=helper(INPUT_HELPER);pins=prepared.PINS|LOCAL_PINS
    need(sha(NO_CONTACT_REPORT)==pins[NO_CONTACT_REPORT],"Actual no-contact ABI fixture changed")
    prior=json.loads(NO_CONTACT_REPORT.read_text(encoding="utf-8"));proof=no_contact_proof(prior,pins,prior["source_after"],prior["files_before"])
    need(proof["original_total_native_completed"] is False and proof["completed_no_contact_frames"]==31,"Partial total must not become complete")
    import copy
    cases=[]
    def reject(row):
        try:no_contact_proof(row,pins,prior["source_after"],prior["files_before"])
        except (RuntimeError,KeyError):return
        raise RuntimeError("Corrupt no-contact history accepted")
    for field in ("terminal_AND","cache_metadata_exact"):
        bad=copy.deepcopy(prior);bad[field]=False;reject(bad);cases.append(field+"_false")
    bad=copy.deepcopy(prior);del bad["source_disk_exact"];reject(bad);cases.append("required_field_missing")
    bad=copy.deepcopy(prior);bad["native_completed"]=True;reject(bad);cases.append("partial_total_upgraded")
    bad=copy.deepcopy(prior);bad["trials"]["no_contact"]["manual_response"]["limited_response_gate"]=False;reject(bad);cases.append("response_false")
    bad=copy.deepcopy(prior);bad["trials"]["no_contact"]["path_readback"].pop();reject(bad);cases.append("incomplete_30_steps")
    bad=copy.deepcopy(prior);bad["trials"]["no_contact"]["path_readback"][3]["raw80_relative_current_pin_error"]["maximum_m"]=5.e-5;reject(bad);cases.append("pin_guard_failed")
    bad=copy.deepcopy(prior);next(iter(bad["trials"]["no_contact"]["path_readback"][3]["input_errors"].values()))["maximum_m"]=5.e-5;reject(bad);cases.append("actual_input_guard_failed")
    return {"passed":True,"actual_fixture_sha256":pins[NO_CONTACT_REPORT],"positive":1,"negative":cases,"native_run":False,"accepted":False}


def historical_cache_proof(current,prior):
    """Cross-process 14-field ABI: compare all 13 non-pointer fields exactly.

    Native PointCache addresses are process-local identity, not persisted data.
    This exception is only for prior-vs-current provenance; the unchanged fresh
    before/after guard still compares the full current dict including pointer.
    Info/outdated flags are deliberately retained: no other field is stripped.
    """
    for label,cache in (("current",current),("prior",prior)):
        need(type(cache) is dict and set(cache)==set(CACHE_FIELD_TYPES),"Historical cache ABI missing/unknown field: "+label)
        need(all(type(cache[name]) is expected for name,expected in CACHE_FIELD_TYPES.items()),"Historical cache ABI field type unknown: "+label)
        need(0<cache["pointer"]<2**64,"Historical process-local native pointer unavailable: "+label)
    fields=sorted(set(CACHE_FIELD_TYPES)-{"pointer"})
    differences=[name for name in fields if current[name]!=prior[name]]
    need(not differences,"Historical cache semantic fields differ: "+",".join(differences))
    return {"semantic_fields":fields,"semantic_field_count":len(fields),"semantic_metadata_exact":True,
        "prior_native_pointer":prior["pointer"],"current_native_pointer":current["pointer"],
        "pointer_values_differ":current["pointer"]!=prior["pointer"],
        "historical_pointer_comparison":"NotComparableAcrossProcesses",
        "current_process_before_after_policy":"Unchanged complete14-field equality, including this process native pointer",
        "scope":"Cache provenance only; no prior crash/source terminal status or simulation acceptance is upgraded."}


def cache_abi_controls():
    need(sha(POINTER_FAILURE)==LOCAL_PINS[POINTER_FAILURE] and sha(NO_CONTACT_REPORT)==LOCAL_PINS[NO_CONTACT_REPORT],"Actual cache ABI fixture changed")
    failed=json.loads(POINTER_FAILURE.read_text(encoding="utf-8"));prior=json.loads(NO_CONTACT_REPORT.read_text(encoding="utf-8"))
    current=failed["cache_before"];old=prior["cache_before"]
    need(failed["native_completed"] is False and "terminal_AND" not in failed and "source_after" not in failed,"Crash receipt must remain unrecorded, not positive provenance")
    need(all(failed[name]==prior[name] for name in ("author_pose","author_playback","author_frame")),"Actual pointer fixture has a different artist input")
    need([name for name in current if current[name]!=old[name]]==["pointer"],"Actual historical field differences changed")
    proof=historical_cache_proof(current,old)
    need(proof["pointer_values_differ"] and proof["semantic_field_count"]==13 and current==failed["cache_after"],"Actual cross-pointer positive or same-process protection fixture differs")
    import copy
    negatives=[]
    def reject(cache):
        try:historical_cache_proof(cache,old)
        except RuntimeError:return
        raise RuntimeError("Invalid historical cache ABI accepted")
    changed=copy.deepcopy(current);changed["start"]+=1;reject(changed);negatives.append("persisted_start_changed")
    changed=copy.deepcopy(current);changed["library_path"]=False;reject(changed);negatives.append("recorded_true_flag_false")
    changed=copy.deepcopy(current);changed["is_baked"]=True;reject(changed);negatives.append("recorded_false_flag_true")
    changed=copy.deepcopy(current);changed["info"]+=" changed";reject(changed);negatives.append("info_retained_changed")
    changed=copy.deepcopy(current);del changed["step"];reject(changed);negatives.append("field_missing")
    changed=copy.deepcopy(current);changed["step"]=None;reject(changed);negatives.append("field_unknown")
    changed=copy.deepcopy(current);changed["unknown_native"]=1;reject(changed);negatives.append("unknown_extra_field")
    changed=copy.deepcopy(current);changed["pointer"]=0;reject(changed);negatives.append("native_pointer_unknown")
    changed=copy.deepcopy(current);changed["pointer"]=2**64;reject(changed);negatives.append("native_pointer_out_of_range")
    changed=copy.deepcopy(current);changed["pointer"]+=1
    need(changed!=current,"Same-process whole-cache equality must reject pointer mutation")
    return {"passed":True,"actual_different_pointer_positive":1,"negative":negatives,
        "same_process_full_pointer_negative":1,"failed_terminal_AND":"Unrecorded","native_run":False,"accepted":False}


def gold_samples(stream):
    """Exact pinned two-space actual samples, never failed private meshes.

    Retain complete gold800 and geometry of actual Body/four colliders. Their
    dense evaluated weights remain in the immutable original file, not loaded
    again. No nearest correspondence or reconstructed collider geometry.
    """
    fields={"label","author_frame","key_values","rig_world","source_frame"}
    mesh_fields={"object","points","matrix_world","native_vertex_index_order","edges","faces","triangles",
        "native_vertex_face_edge_sha256","native_triangulation_sha256","native_group_mapping","weights_complete"}
    samples={};label=None;sample=False;role=None;inside_meshes=False;iterator=iter(stream)
    def value(text,indent):
        text=text.strip().rstrip(",")
        if text not in {"[","{"}:return json.loads(text)
        close="]" if text=="[" else "}";lines=[text+"\n"]
        for line in iterator:
            lines.append(line)
            if len(line)-len(line.lstrip())==indent and line.strip() in {close,close+","}:
                return json.loads("".join(lines).strip().rstrip(","))
        raise RuntimeError("Truncated sealed native field")
    for line in iterator:
        indent=len(line)-len(line.lstrip());match=re.match(r'^\s*"([^"\\]+)": (.*)$',line)
        if sample and indent==6 and line.strip() in {"}","},"}:sample=False;role=None;inside_meshes=False;continue
        if inside_meshes and indent==8 and line.strip() in {"}","},"}:inside_meshes=False;role=None;continue
        if role is not None and indent==10 and line.strip() in {"}","},"}:role=None;continue
        if match is None:continue
        name,text=match.groups()
        if indent==4 and name in {"N","L","T"}:
            need(name not in samples,"Duplicate actual endpoint");label=name;samples[label]={"native_meshes":{}};sample=False;inside_meshes=False
        elif label is not None and indent==6 and name=="sample":sample=True
        elif sample and indent==8 and name in fields:samples[label][name]=value(text,indent)
        elif sample and indent==8 and name=="native_meshes":inside_meshes=True
        elif sample and inside_meshes and indent==10 and text.strip()=="{":
            role=name;samples[label]["native_meshes"][name]={}
        elif sample and role is not None and indent==12 and (name in mesh_fields or (role=="ManualOracle800" and name=="weights")):
            samples[label]["native_meshes"][role][name]=value(text,indent)
    need(set(samples)=={"N","L","T"} and all(fields<=set(row) for row in samples.values()),"Actual sample header incomplete")
    for row in samples.values():
        need(len(row["native_meshes"])==6 and {"ManualOracle800","RegisteredBody"}<=set(row["native_meshes"]),"Six actual native meshes required")
        for role,mesh in row["native_meshes"].items():
            need(mesh_fields<=set(mesh),"Native geometry incomplete: "+role)
            if role=="ManualOracle800":need("weights" in mesh and len(mesh["points"])==800,"Gold800 weights/layout missing")
    return samples


def response_summary(target_l,target_t,out_l,out_t,quality,guard,metres):
    need(len(target_l)==len(target_t)==len(out_l)==len(out_t)>0,"Response correspondence missing")
    target=[[float(t[j])-float(l[j]) for j in range(3)] for l,t in zip(target_l,target_t)]
    actual=[[float(t[j])-float(l[j]) for j in range(3)] for l,t in zip(out_l,out_t)]
    ids=[i for i,row in enumerate(target) if math.sqrt(math.fsum(x*x for x in row))*metres>guard]
    denominator=math.fsum(x*x for i in ids for x in target[i])
    dot=math.fsum(target[i][j]*actual[i][j] for i in ids for j in range(3))
    lengths=[math.sqrt(math.fsum(x*x for x in actual[i]))*metres for i in ids]
    errors=[math.sqrt(math.fsum((actual[i][j]-target[i][j])**2 for j in range(3)))*metres for i in ids]
    edge=quality["edge_ratios"];area=quality["triangle_area_ratios_on_recorded_corner_triplets"]
    finite_shape=all(math.isfinite(x) for row in out_t for x in row)
    shape_gate=finite_shape and edge["unresolved_degenerate_baseline"]==0 and area["unresolved_degenerate_baseline"]==0
    shape_gate=shape_gate and edge["minimum"] is not None and area["minimum"] is not None
    shape_gate=shape_gate and edge["minimum"]>=LIMITS["edge_min"] and edge["maximum"]<=LIMITS["edge_max"] and area["minimum"]>=LIMITS["area_min"]
    response=bool(ids and denominator>0. and dot>0. and max(lengths)>guard)
    return {"measured_manual_region_ids":ids,"aggregate_dot_gain":None if denominator==0. else dot/denominator,
        "response_rms_m":None if not ids else math.sqrt(math.fsum(x*x for x in lengths)/len(ids)),
        "response_maximum_m":max(lengths,default=None),"T_minus_L_response_residual_maximum_m":max(errors,default=None),
        "T_minus_L_response_residual_rms_m":None if not ids else math.sqrt(math.fsum(x*x for x in errors)/len(ids)),
        "limited_response_gate":response,"limited_shape_gate":bool(shape_gate),"proceed_to_contact":bool(response and shape_gate),
        "limits":LIMITS,"manual_fidelity_accepted":False,"accepted":False,
        "scope":"Some correctly directed finite response only. Inertia during L-to-T is not isolated by an L-hold control; gain/residual disclose fidelity, no causal Manual/artist acceptance."}


def geometry_comparison(body,clone,metres,digest,origin):
    """Geometry-only comparison; omitted dense weights stay in sealed evidence."""
    fields=("native_vertex_index_order","edges","faces","triangles")
    equal={key:digest(body[key])==digest(clone[key]) for key in fields}
    a,b=[list(point) for point in body["points"]],[list(point) for point in clone["points"]]
    correspondence=len(a)==len(b) and equal["native_vertex_index_order"]
    maximum=max((math.sqrt(math.fsum((x-y)**2 for x,y in zip(p,q)))*metres for p,q in zip(a,b)),default=0.) if correspondence else None
    exact=correspondence and digest(a)==digest(b) and all(equal.values())
    return {"status":"exact_geometry_match" if exact else "different_geometry" if correspondence else "unknown_correspondence",
        "origin":origin,"Body_object":body["object"],"actual_clone_object":clone["object"],"counts":{role:{"points":len(mesh["points"]),"faces":len(mesh["faces"]),"edges":len(mesh["edges"]),"triangles":len(mesh["triangles"])} for role,mesh in (("Body",body),("clone",clone))},
        "equal_native_geometry_fields":equal,"world_points_exact":digest(a)==digest(b),"maximum_world_point_error_m":maximum,
        "original_dense_weights_reloaded":False,"whole_body_coverage_accepted":False,"actual_final_clearance_accepted":False}


def pure_checks():
    static=helper(STATIC);base=helper(CONTINUOUS);prior=static.pure_checks()
    points=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)];target=[(0.,0.,0.),(1.01,0.,0.),(0.,1.,0.)]
    quality=static.metrics(target,target,[(0,1),(1,2),(2,0)],[(0,1,2)],[],1.)
    q=response_summary(points,target,points,target,quality,5.e-5,1.)
    need(q["proceed_to_contact"] and q["aggregate_dot_gain"]==1. and q["T_minus_L_response_residual_maximum_m"]==0.,"Exact manual response control")
    need(not response_summary(points,target,points,points,quality,5.e-5,1.)["proceed_to_contact"],"No response cannot pass")
    reversed_points=[(0.,0.,0.),(.99,0.,0.),(0.,1.,0.)]
    need(not response_summary(points,target,points,reversed_points,quality,5.e-5,1.)["limited_response_gate"],"Reverse response cannot pass")
    poor=dict(quality,edge_ratios=dict(quality["edge_ratios"],maximum=2.001))
    need(not response_summary(points,target,points,target,poor,5.e-5,1.)["proceed_to_contact"],"Finite bad shape must stop before contact")
    mesh={key:[] for key in ("points","matrix_world","native_vertex_index_order","edges","faces","triangles","native_group_mapping")}
    mesh.update(object="x",native_vertex_face_edge_sha256="x",native_triangulation_sha256="x",weights_complete=True)
    gold=dict(mesh,points=[[0.,0.,0.]]*800,weights=[[]]*800)
    sample={"label":"N","author_frame":[39,0.],"key_values":None,"rig_world":[],"source_frame":{},"rig_channels":{"NotAMesh":{"mode":"XYZ"}},
        "native_meshes":dict(ManualOracle800=gold,RegisteredBody=dict(mesh,weights=[{"dense":"skip"}]),P=dict(mesh),L=dict(mesh),R=dict(mesh),B=dict(mesh))}
    import io
    data={"endpoints":{label:{"sample":dict(sample,label=label),"private_native_inputs":{"ManualOracle800":{"points":[[999.,999.,999.]]}}} for label in ("N","L","T")}}
    parsed=gold_samples(io.StringIO(json.dumps(data,indent=2)))
    need(all("weights" not in row["native_meshes"]["RegisteredBody"] and row["native_meshes"]["ManualOracle800"]["points"][0]==[0.,0.,0.] for row in parsed.values()),"Reader must exclude failed private and dense Body weights")
    del data["endpoints"]["T"]["sample"]["native_meshes"]["B"]
    try:gold_samples(io.StringIO(json.dumps(data,indent=2)))
    except RuntimeError:pass
    else:raise RuntimeError("Missing collider must reject")
    need(base.path_weights(1,30)==(0.,0.) and base.path_weights(16,30)==(1.,0.) and base.path_weights(31,30)==(0.,1.),"Exact synthetic endpoints")
    digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    body={"object":"Body","points":[[0.,0.,0.]],"native_vertex_index_order":[0],"edges":[],"faces":[],"triangles":[]}
    need(geometry_comparison(body,dict(body,object="Clone"),1.,digest,"pure")["status"]=="exact_geometry_match","Omitted weight geometry comparison control")
    changed=dict(body,object="Clone",points=[[.001,0.,0.]])
    need(geometry_comparison(body,changed,1.,digest,"pure")["status"]=="different_geometry","Different actual clone must remain different")
    return {"passed":True,"focused_controls":9,"history_ABI":history_abi_controls(),"no_contact_ABI":no_contact_abi_controls(),"cache_ABI":cache_abi_controls(),"diagnostic_IO":diagnostic_io_controls(),"legacy_metrics":prior,"native_run":False,"accepted":False}


def timed_diagnostic_write(path,value,converter,clock=time.perf_counter):
    """Conversion+JSON and disk clocks separated; neither is simulation time."""
    tick=clock();payload=json.dumps(converter(value),indent=2,ensure_ascii=False,allow_nan=False)
    serialization=clock()-tick;tick=clock();path.write_text(payload,encoding="utf-8");disk=clock()-tick
    return {"diagnostic_conversion_serialization_seconds":serialization,"diagnostic_disk_write_seconds":disk}


def diagnostic_io_controls():
    """Use actual writer and actual main receipt loop; no disk or native calls."""
    from types import SimpleNamespace as NS
    import ast,copy
    captured=[];times=iter((10.,12.,20.,23.))
    writer=NS(write_text=lambda payload,encoding:captured.append((json.loads(payload),encoding)))
    clock=timed_diagnostic_write(writer,{"proof":True},lambda value:value,lambda:next(times))
    need(clock=={"diagnostic_conversion_serialization_seconds":2.,"diagnostic_disk_write_seconds":3.}
        and captured==[({"proof":True},"utf-8")],"Actual conversion/disk clocks control")
    tree=ast.parse(Path(__file__).read_text(encoding="utf-8"));entry=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="main")
    block=None
    for loop in ast.walk(entry):
        if not isinstance(loop,ast.For):continue
        for index,node in enumerate(loop.body):
            if isinstance(node,ast.For) and isinstance(node.body[0],ast.Try) and "input_meshes.items()"==ast.unparse(node.iter):
                block=loop.body[index:index+3];break
    need(block is not None and len(block)==3 and isinstance(block[1],ast.Assign) and isinstance(block[2],ast.For),"Actual all-role receipt/one-write/guard ABI changed")
    receipt_code=compile(ast.fix_missing_locations(ast.Module(body=block,type_ignores=[])),"actual receipt loop","exec")
    base=helper(CONTINUOUS);prepared=helper(INPUT_HELPER)
    mesh=lambda x:{"points":[[x,0.,0.]],"native_triangulation_sha256":"fixture"}
    meshes={"Role"+str(i):mesh(float("nan") if i==0 else 0.) for i in range(6)}
    gold={label:{"native_meshes":{role:mesh(0.) for role in meshes}} for label in ("N","L","T")}
    row={"input_errors":{}};saved=[]
    environment={"input_meshes":meshes,"gold":gold,"weights":(0.,0.),"metres":1.,"prepared":prepared,"base":base,
        "read":NS(digest=lambda value:"fixture"),"row":row,"precision":{"metres":1.e-6},"identity":lambda *args:None,"need":need,
        "write":lambda:(saved.append(copy.deepcopy(row["input_errors"])) or {"diagnostic_conversion_serialization_seconds":0.,"diagnostic_disk_write_seconds":0.})}
    try:exec(receipt_code,environment)
    except RuntimeError as error:need("Unknown" in str(error),"Expected first invalid input guard")
    else:raise RuntimeError("Unknown receipt must reject")
    need(len(saved)==1 and set(saved[0])==set(meshes) and saved[0]["Role0"]["status"]=="unknown"
        and all(saved[0]["Role"+str(i)]["status"]=="measured" for i in range(1,6)),"All roles must persist before first failure throw")
    return {"passed":True,"clock_positive":1,"actual_main_failure_receipt_control":1,"disk_written":False,"native_run":False}


def arguments():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path);parser.add_argument("--pure-checks",action="store_true")
    parser.add_argument("--max-seconds",type=float,default=120.);parser.add_argument("--render",action="store_true",default=True)
    values=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:] if "--pure-checks" in sys.argv else []
    args=parser.parse_args(values)
    if not args.pure_checks:
        need(args.output is not None and 30.<=args.max_seconds<=180.,"Fresh output and explicit soft budget30..180 required; soft180 needs root external240 lease")
        args.output=args.output.resolve();need(args.output.is_relative_to(HERE) and args.output!=HERE and not args.output.exists(),"Refuse existing/non-Validation output")
    args.steps=STEPS;args.body_vertex_limit=100000;args.triangle_pair_limit=10000
    return args


def main(args):
    if args.pure_checks:print(json.dumps(pure_checks()));return 0
    import bpy
    from mathutils import Matrix,Vector
    need(bpy.app.background and bpy.app.version[:2]==(5,1) and not bpy.data.filepath and "--factory-startup" in sys.argv
        and "--disable-autoexec" in sys.argv and "--threads" in sys.argv and sys.argv[sys.argv.index("--threads")+1]=="1","Root-leased empty factory5.1 only")
    prepared=helper(INPUT_HELPER);base=helper(CONTINUOUS);static=helper(STATIC)
    pins=prepared.PINS|LOCAL_PINS
    need(all(sha(path)==value for path,value in pins.items()),"Frozen input/helper changed")
    workflow,same,read=(prepared.load(name) for name in ("verify_actual_surface_workflow.py","verify_actual_same_frame_pose.py","verify_actual_body_proxy_coverage.py"))
    qa,diag,addon,surface=workflow.load_dependencies();args.input,args.install_report=prepared.INPUT,prepared.INSTALL
    args.expected_surface_sha,args.expected_worker_sha=pins[prepared.SURFACE],pins[prepared.WORKER]
    args.output.mkdir();destination=args.output/"dynamic_rest800_preview.json";started=time.perf_counter()
    report={"prepared_only_source":True,"native_completed":False,"accepted":False,"artist_saved":False,"stage":"GOLD800_CONTACT_ONLY_PREVIEW",
        "scope":"One private synthetic world-geometry N-to-L-to-T 30-step CONTACT path after pinned completed no-contact limited gate. Prior total remains failed. No author Actions/live Original or intermediate skeletal poses. Single Cloth800 output then native Subsurf3040; no cached-C substitution.",
        "script_sha256":sha(Path(__file__)),"pins":{str(path):value for path,value in pins.items()},"pure_checks":pure_checks(),
        "source_before":diag.source_manifest(),"files_before":{str(p):qa.file_state(p) for p in (prepared.INPUT,prepared.INSTALL,prepared.ARTIST)},"trials":{},"cleanup_errors":[]}
    report["lease_budget"]={"soft_seconds":args.max_seconds,"root_external_lease_required_seconds":args.max_seconds+60.,
        "scope":"Execution/proof/render allowance only. No input, output, pin, collision, shape or artistic-acceptance threshold changed."}
    ids={name:[] for name in ("objects","meshes","scenes","collections","keys","actions","node_groups")};shared_probes=[]
    home=protection=inventory=source=rig=old_cloth=None
    def write():return timed_diagnostic_write(destination,report,diag.json_content)
    def budget():need(time.perf_counter()-started<args.max_seconds,f"Private contact preview soft{args.max_seconds:g}s phase budget exhausted")
    def own(kind,value):ids[kind].append(value);return value
    def link(obj,collection):
        collection.objects.link(obj);obj.hide_viewport=obj.hide_render=False
        # New private Scene has no current view-layer Base until activation.
        # Read its actual hide_get after activation; do not call hide_set in home.
        return obj
    def copy_raw(name,collection):
        obj=own("objects",source.copy());obj.name=name;obj.data=own("meshes",source.data.copy())
        need(obj.data.shape_keys is None,"This fixed-Key fixture has no source Keys; other Key setups not exercised")
        obj.animation_data_clear();obj.data.animation_data_clear();surface._clear(obj.constraints);surface._clear(obj.modifiers)
        for owner in (obj,obj.data):
            prepared.clear_metadata(owner);owner.use_fake_user=False
        obj.parent=None;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=Matrix.Identity(4)
        return link(obj,collection)
    def freeze_geometry(mesh,name,collection):
        data=own("meshes",bpy.data.meshes.new(name+" Mesh"));data.from_pydata(mesh["points"],mesh["edges"],mesh["faces"]);data.update()
        return link(own("objects",bpy.data.objects.new(name,data)),collection)
    def absolute_output(name,upstream,collection,subsurf):
        obj=copy_raw(name,collection);group=own("node_groups",bpy.data.node_groups.new(name+" Exact Index","GeometryNodeTree"))
        group.interface.new_socket(name="Geometry",in_out="INPUT",socket_type="NodeSocketGeometry")
        group.interface.new_socket(name="Geometry",in_out="OUTPUT",socket_type="NodeSocketGeometry")
        inp=group.nodes.new("NodeGroupInput");out=group.nodes.new("NodeGroupOutput");info=group.nodes.new("GeometryNodeObjectInfo")
        info.transform_space="RELATIVE";info.inputs["Object"].default_value=upstream;info.inputs["As Instance"].default_value=False
        pos=group.nodes.new("GeometryNodeInputPosition");index=group.nodes.new("GeometryNodeInputIndex")
        sample=group.nodes.new("GeometryNodeSampleIndex");sample.data_type="FLOAT_VECTOR";sample.domain="POINT";sample.clamp=False
        setpos=group.nodes.new("GeometryNodeSetPosition");setpos.inputs["Selection"].default_value=True;setpos.inputs["Offset"].default_value=(0.,0.,0.)
        for a,b in ((inp.outputs["Geometry"],setpos.inputs["Geometry"]),(info.outputs["Geometry"],sample.inputs["Geometry"]),
            (pos.outputs["Position"],sample.inputs["Value"]),(index.outputs["Index"],sample.inputs["Index"]),
            (sample.outputs["Value"],setpos.inputs["Position"]),(setpos.outputs["Geometry"],out.inputs["Geometry"])):group.links.new(a,b)
        need(all(link.is_valid for link in group.links),"Absolute native index output link invalid")
        modifier=obj.modifiers.new("Exact Cloth position output","NODES");modifier.node_group=group
        modifier=obj.modifiers.new("Original native Subsurf","SUBSURF");surface._copy_scalars(subsurf,modifier)
        return obj
    def native(obj,graph):return read.native_mesh(obj,graph,diag)
    def identity(mesh,expected):
        keys=("native_vertex_index_order","edges","faces")
        need(diag.json_content({k:mesh[k] for k in keys})=={k:expected[k] for k in keys},"Private native topology/index identity changed")
    try:
        source_name=workflow.motion_input_gate(args,report,qa,diag);addon.register()
        need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(prepared.INPUT),load_ui=False,use_scripts=False),"Exact input open failed")
        source,rig,record=qa.owned_source(source_name);home=bpy.context.scene;protection=qa.Protection();inventory=prepared.inventory(bpy)
        report["author_pose"]=qa.digest(same.pose_checkpoint(rig,qa));report["author_playback"]=qa.digest(same.playback_state(qa));report["author_frame"]=[home.frame_current,home.frame_subframe]
        report["cache_preflight"]=qa.saved_cache_preflight(source,record);need(report["cache_preflight"]["allowed"],"Original sealed/external/disk cache refused")
        surface.validate(source,rig,record);report["canonical_validation_before_owned"]=True
        actual=bpy.data.objects[record["physics"]["proxy"]];old_cloth=next(m for m in actual.modifiers if m.type=="CLOTH")
        report["cache_before"]=same.cache_state(old_cloth,qa);need(source.data.shape_keys is None,"Current Keys fixture changed/unsupported; artist Keys not modified")
        prior=json.loads(NO_CONTACT_REPORT.read_text(encoding="utf-8"))
        report["reused_no_contact_prerequisite"]=no_contact_proof(prior,pins,report["source_before"],report["files_before"]);write()
        report["historical_cache_comparison"]=historical_cache_proof(report["cache_before"],prior["cache_before"]);write()
        report["previous_pointer_failure"]={"path":str(POINTER_FAILURE),"sha256":pins[POINTER_FAILURE],
            "script_sha256":pins[POINTER_PREDECESSOR],"terminal_AND":"Unrecorded","source_after":"Unrecorded",
            "scope":"Preserved failed historical candidate; not used as completed physics or positive source-terminal provenance."}
        need(all(report[field]==prior[field] for field in ("author_pose","author_playback","author_frame")),"Current artist pose/playback/frame differs from measured no-contact input")
        sealed=json.loads(prepared.SEALED_REPORT.read_text(encoding="utf-8"))
        fresh={label:json.loads(path.read_text(encoding="utf-8")) for label,path in FRESH_REPORTS.items()}
        report["historical_protection_schema"]={"V2_recorded_fields":sorted(sealed),
            "V2_helper_final_status":"Unrecorded" if "frozen_pins_disk_exact" not in sealed else "UnexpectedField",
            "fresh_report_references":{label:{"path":str(path),"sha256":pins[path]} for label,path in FRESH_REPORTS.items()}}
        write()  # Actual schema persists even if a required recorded field rejects.
        report["historical_snapshot_proof"]=history_proof(sealed,fresh,report["source_before"],pins,prepared.SEALED_ENDPOINT,pins[prepared.SEALED_ENDPOINT]);write()
        budget()
        with prepared.SEALED_ENDPOINT.open(encoding="utf-8") as stream:gold=gold_samples(stream)
        roles=["ManualOracle800","RegisteredBody"]+list(record["physics"]["colliders"]);need(len(set(roles))==6 and all(set(x["native_meshes"])==set(roles) for x in gold.values()),"Exact collider names unresolved")
        clone_name=record["physics"]["colliders"][-1];closed_names=record["physics"]["colliders"][:-1]
        metres=float(home.unit_settings.scale_length);need(math.isfinite(metres) and metres>0.,"Invalid physical units")
        report["sealed_gold"]={"endpoint":str(prepared.SEALED_ENDPOINT),"sha256":pins[prepared.SEALED_ENDPOINT],"report":str(prepared.SEALED_REPORT),"report_sha256":pins[prepared.SEALED_REPORT],"dense_evaluated_Body_weights_reloaded":False}
        need(all(gold[label]["key_values"] is None for label in gold),"Gold Key fixture changed")
        original=gold["N"]["native_meshes"]["ManualOracle800"]
        need(len(original["weights"])==800 and original["weights_complete"],"Gold800 full weights missing")
        for row in gold.values():
            for role in roles:
                mesh=row["native_meshes"][role];identity(mesh,gold["N"]["native_meshes"][role])
                if role=="ManualOracle800":need(mesh["weights"]==original["weights"] and mesh["native_group_mapping"]==original["native_group_mapping"],"Gold800 native groups changed")
        report["Body_clone_endpoints"]={label:geometry_comparison(row["native_meshes"]["RegisteredBody"],row["native_meshes"][clone_name],metres,read.digest,"Sealed actual same-graph native geometry; original IDs/source/weights protection receipts remain pinned") for label,row in gold.items()}
        waist_index=source.vertex_groups[record["controls"]["waist"]].index
        fixed=[i for i,row in enumerate(original["weights"]) if any(x["index"]==waist_index and x["weight"]==1. for x in row)]
        native_pins=qa.physics._weights(actual)[old_cloth.settings.vertex_group_mass]
        need(all(type(index) is int and 0<=index<800 for index in native_pins),"Native pin index inventory invalid")
        pin_values=[native_pins.get(index,0.) for index in range(800)]
        declared_pins=list(record["physics"]["pin_weights"])
        need(len(declared_pins)==800 and all(math.isfinite(v) and 0.<=v<=1. for v in declared_pins),"Declared native pin recipe missing")
        need(len(fixed)==80 and len(pin_values)==800 and [i for i,v in enumerate(pin_values) if v==1.]==fixed,"Exact current hard80/native gold Waist identity differs")
        need(all(math.isfinite(v) and 0.<=v<=1. for v in pin_values),"Native pin weights invalid")
        report["waist_scope"]={"hard80_ids":fixed,"gold80_movement":{label:base.residual(gold[label]["native_meshes"]["ManualOracle800"]["points"],original["points"],fixed,metres) for label in ("L","T")},
            "native_pin_weights":pin_values,"declared_record_pin_weights":declared_pins,"record_native_pin_maximum_delta":max(abs(a-b) for a,b in zip(declared_pins,pin_values)),
            "pin_policy":"Existing record recipe verified by canonical preflight; copy actual current native Float32 weights, including explicit zero assignments. No new arbitrary soft weight.",
            "existing_C_H0_SurfaceDeform_Body_follow_exercised":False,"classification":"Gold800-before-BodyAttachment fixed Waist trajectory; previous C/H0 Body-follow4.64mm is a different input, not relaxed or reclassified as pass."}
        need(all(x["maximum_m"]==0. for x in report["waist_scope"]["gold80_movement"].values()),"Gold hard80 actual world trajectory changed")
        report["units_to_metres"]=metres;report["input_guard_m"]=prepared.GEOMETRY_GUARD_M
        precision=base.readback_guard((p for row in gold.values() for mesh in row["native_meshes"].values() for p in mesh["points"]),metres)
        report["input_readback_microguard"]=precision
        need(precision==prior["input_readback_microguard"] and pin_values==prior["waist_scope"]["native_pin_weights"],"Current native precision or800pin values differ from reused prerequisite")
        subsurf=source.modifiers[-1];need(subsurf.type=="SUBSURF" and subsurf.levels==1 and subsurf.show_viewport,"Native final3040 Subsurf unsupported")
        render_bounds=diag.framing(rig,record,bpy.context.evaluated_depsgraph_get());bounds=dict(render_bounds)
        projections=[(Vector(point)-bounds["waist"]).dot(bounds["up"]) for row in gold.values() for mesh in row["native_meshes"].values() for point in mesh["points"]]
        bounds["lower"],bounds["upper"]=min(projections)-1.e-4,max(projections)+1.e-4
        report["collision_region"]={"scope":"Full captured Body/collider/input projection envelope, not guessed intermediate bones or open-Body volume", "lower":bounds["lower"],"upper":bounds["upper"],"pair_limit":args.triangle_pair_limit}
        # No main pose/action/frame replay or author Cloth evaluation is used.
        snapshots={label:{role:{"points":mesh["points"],"native_geometry_sha256":read.digest({"points":mesh["points"],"faces":mesh["faces"]})} for role,mesh in row["native_meshes"].items()} for label,row in gold.items()}
        (args.output/"gold_geometry_index.json").write_text(json.dumps({"sealed_reference":report["sealed_gold"],"endpoint_geometry_hashes":{l:{r:m["native_geometry_sha256"] for r,m in rs.items()} for l,rs in snapshots.items()},"accepted":False},indent=2),encoding="utf-8")
        del snapshots;write()
        for contact in (True,):
            budget();name="contact" if contact else "no_contact";trial={"completed":False,"accepted":False,"path_readback":[],"samples":{},"timings":[],"parameters":{}}
            report["trials"][name]=trial;write()
            private=own("scenes",bpy.data.scenes.new("QA Dynamic800 "+name));private.unit_settings.system,private.unit_settings.scale_length=home.unit_settings.system,home.unit_settings.scale_length
            private.render.fps,private.render.fps_base=home.render.fps,home.render.fps_base;private.gravity=home.gravity;private.use_gravity=home.use_gravity;private.frame_start,private.frame_end=1,31
            collision=own("collections",bpy.data.collections.new("QA Dynamic800 Collision "+name));private.collection.children.link(collision)
            collision.hide_viewport=collision.hide_render=False
            c=copy_raw("QA Cloth800 "+name,private.collection);c.data.vertices.foreach_set("co",[float(x) for p in original["points"] for x in p]);c.data.update()
            pin=c.vertex_groups.new(name=PIN)
            need(pin.name==PIN,"Private pin name collision")
            for index,weight in enumerate(pin_values):pin.add([index],weight,"REPLACE")
            animation=base.animate(c,*(gold[label]["native_meshes"]["ManualOracle800"] for label in ("N","L","T")),30,ids,bpy,qa)
            probe=own("objects",c.copy());probe.name="QA Exact Input800 "+name;link(probe,private.collection);shared_probes.append(probe)
            need(probe.data==c.data and len(probe.modifiers)==0,"Shared pre-Cloth input has modifiers")
            bodies={};body_animations={}
            for role in roles[1:]:
                obj=freeze_geometry(gold["N"]["native_meshes"][role],"QA Frozen "+role+" "+name,private.collection if role=="RegisteredBody" else collision)
                bodies[role]=obj;body_animations[role]=base.animate(obj,*(gold[label]["native_meshes"][role] for label in ("N","L","T")),30,ids,bpy,qa)
                if contact and role!="RegisteredBody":
                    obj.modifiers.new("Exact native collision","COLLISION");surface._copy_scalars(bpy.data.objects[role].collision,obj.collision)
            cloth=c.modifiers.new("QA Dynamic Rest Cloth","CLOTH");surface._copy_scalars(old_cloth.settings,cloth.settings)
            surface._copy_scalars(old_cloth.collision_settings,cloth.collision_settings);surface._copy_scalars(old_cloth.settings.effector_weights,cloth.settings.effector_weights)
            cloth.settings.vertex_group_mass=pin.name;cloth.settings.rest_shape_key=None;cloth.settings.use_dynamic_mesh=True
            cloth.collision_settings.use_collision=contact;cloth.collision_settings.collection=collision
            if not contact:cloth.settings.effector_weights.gravity=0.
            for prop in cloth.settings.bl_rna.properties:
                if prop.identifier.startswith("vertex_group_"):
                    group_name=getattr(cloth.settings,prop.identifier);need(not group_name or c.vertex_groups.get(group_name) is not None,"Copied Cloth group unavailable: "+prop.identifier)
            cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step=1,31,1
            cloth.point_cache.use_external=cloth.point_cache.use_disk_cache=False
            need(not cloth.point_cache.is_baked and not cloth.point_cache.use_external and not cloth.point_cache.use_disk_cache,"Private fresh runtime cache not isolated")
            target=absolute_output("QA Requested3040 "+name,probe,private.collection,subsurf)
            final=absolute_output("QA Final3040 "+name,c,private.collection,subsurf)
            need(bpy.context.window is not None,"Private Scene graph has no native Window")
            bpy.context.window.scene=private;private.frame_set(1);bpy.context.view_layer.update()
            need(source.name not in bpy.context.view_layer.objects,"Artist/source leaked into private graph")
            trial["parameters"]={"cloth":surface._rna(cloth.settings),"collision":surface._rna(cloth.collision_settings),"effectors":surface._rna(cloth.settings.effector_weights),
                "collider_scalars":{role:surface._rna(obj.collision) for role,obj in bodies.items() if contact and role!="RegisteredBody"},
                "pin_weights":pin_values,"hard80":fixed,"fps":private.render.fps,"fps_base":private.render.fps_base,"steps":30,
                "scene_gravity":list(private.gravity),"scene_use_gravity":private.use_gravity,
                "rest_policy":"Native use_dynamic_mesh=True updates spring lengths/bending rest angles from input; does not overwrite simulated free positions. rest_shape_key=None.",
                "output_policy":"C800 sole Cloth writer -> exact unclamped index absolute GN output -> copied original native Subsurf3040, no S+C-H0 delta",
                "synthetic_action_slot":animation["slot"],"gravity_policy":"No-contact0 isolates limited Manual response; contact copies current original effector gravity, disclosed distinct condition.","official_implementation":OFFICIAL}
            physical_fields=("cloth","collision","effectors","collider_scalars","pin_weights","hard80","fps","fps_base","steps","scene_gravity","scene_use_gravity")
            trial["prior_partial_contact_parameters_exact"]={field:diag.json_content(trial["parameters"][field])==prior["trials"]["contact"]["parameters"][field] for field in physical_fields};write()
            need(all(trial["prior_partial_contact_parameters_exact"].values()),"Contact physics/gravity/culling/normal/pin/fps parameters changed from original partial trial")
            trial["visibility"]=read.visibility_evidence([c,probe,target,final,*bodies.values()],cloth,private)
            need(not collision.hide_viewport and not collision.hide_render and all(not obj.hide_get() and not obj.hide_viewport and not obj.hide_render for obj in [c,probe,target,final,*bodies.values()]),"Private collision/output filtering hidden")
            fixed_final=None;target_l=out_l=target_t=out_t=None;last_bodies=None;last_quality=None;target_raw_contract=qa.raw_mesh_content(target)
            for frame in range(1,32):
                budget();tick=time.perf_counter();private.frame_set(frame);bpy.context.view_layer.update();frame_cost=time.perf_counter()-tick
                graph=bpy.context.evaluated_depsgraph_get();tick=time.perf_counter();weights=base.path_weights(frame,30)
                observed=native(probe,graph);cmesh=native(c,graph);requested=native(target,graph);output=native(final,graph)
                body_meshes={role:native(obj,graph) for role,obj in bodies.items()}
                extraction=time.perf_counter()-tick;tick=time.perf_counter()
                row={"frame":frame,"synthetic_weights":weights,"input_errors":{},"frame_set_and_view_layer_seconds":frame_cost,"native_extraction_seconds":extraction}
                trial["path_readback"].append(row)
                input_meshes={"ManualOracle800":observed,**body_meshes}
                for role,mesh in input_meshes.items():
                    try:
                        expected=base.path_points(*(gold[label]["native_meshes"][role]["points"] for label in ("N","L","T")),weights)
                        error=prepared.error_summary(mesh["points"],expected,metres);worst=error["worst_native_index"]
                        row["input_errors"][role]={**error,"status":"measured","worst_observed_world":list(mesh["points"][worst]),"worst_expected_world":expected[worst],
                            "actual_world_points_sha256":read.digest([list(point) for point in mesh["points"]]),"expected_world_points_sha256":read.digest(expected),
                            "actual_triangles_sha256":mesh["native_triangulation_sha256"]}
                    except Exception as error:
                        row["input_errors"][role]={"status":"unknown","reason":str(error)}
                receipt_io=write()  # All six measured/Unknown receipts persist before any input throw.
                for role,mesh in input_meshes.items():
                    error=row["input_errors"][role];need(error["status"]=="measured","Actual input receipt Unknown: "+role)
                    identity(mesh,gold["N"]["native_meshes"][role])
                    need(error["maximum_m"]<=prepared.GEOMETRY_GUARD_M and error["maximum_m"]<=precision["metres"],"Actual gold input readback exceeds unchanged budget: "+role)
                need(qa.raw_mesh_content(target)==target_raw_contract,"Final target source raw Mesh/UV/groups changed")
                for mesh in (observed,cmesh):
                    need(len(mesh["points"])==800,"C/input is not800");identity(mesh,original)
                    filtered=[[x for x in row if x["index"]!=pin.index] for row in mesh["weights"]]
                    mapping=[x for x in mesh["native_group_mapping"] if x["index"]!=pin.index]
                    need(filtered==original["weights"] and mapping==original["native_group_mapping"],"Private original raw weights/group mapping changed")
                    need(all(next((x["weight"] for x in row if x["index"]==pin.index),None)==pin_values[index] for index,row in enumerate(mesh["weights"])),"Exact original native pin values changed")
                need(len(requested["points"])==len(output["points"])==3040 and requested["native_vertex_index_order"]==output["native_vertex_index_order"],"Native Subsurf3040 identity differs")
                need(requested["edges"]==output["edges"] and requested["faces"]==output["faces"],"Final/target native topology differs")
                need(requested["weights"]==output["weights"] and requested["native_group_mapping"]==output["native_group_mapping"],"Final/target native weights/groups differ")
                now_fixed=[i for i,row in enumerate(requested["weights"]) if any(x["index"]==waist_index and x["weight"]>=.999 for x in row)]
                need(len(now_fixed)==160 and (fixed_final is None or fixed_final==now_fixed),"Native final hard-waist identity differs");fixed_final=now_fixed
                for mesh in (requested,output):mesh["free_indices"]=[i for i in range(3040) if i not in set(fixed_final)]
                pin_error=prepared.error_summary(cmesh["points"],observed["points"],metres,fixed);row["raw80_relative_current_pin_error"]=pin_error
                row["gold80_world_movement_from_N"]=prepared.error_summary(observed["points"],original["points"],metres,fixed)
                need(pin_error["maximum_m"]<=precision["metres"],"Raw80 deviates from CURRENT gold pin trajectory")
                quality=static.metrics(requested["points"],output["points"],requested["edges"],output["triangles"],fixed_final,metres)
                row["final_quality_relative_current_target"]=quality;row["target_residual_all"]=base.residual(output["points"],requested["points"],list(range(3040)),metres)
                row["normal_diagnostics"]=base.normal_diagnostics(requested["points"],output["points"],output["triangles"])
                row["metrics_seconds"]=time.perf_counter()-tick-sum(receipt_io.values());row.update(receipt_io)
                trial["timings"].append({k:row[k] for k in ("frame","frame_set_and_view_layer_seconds","native_extraction_seconds","metrics_seconds","diagnostic_conversion_serialization_seconds","diagnostic_disk_write_seconds")})
                if frame in (1,16,31):
                    endpoint_tick=time.perf_counter()
                    label={1:"N",16:"L",31:"T"}[frame];epsilon=max(1.e-8,(bounds["upper"]-bounds["lower"])*1.e-6)
                    cross={role:diag.triangle_crossings(output,mesh,bounds,args.triangle_pair_limit,epsilon) for role,mesh in body_meshes.items()}
                    closed={}
                    for role in closed_names:
                        try:
                            qa.physics._closed_collider(bodies[role]);collider=qa.ClosedCollider(bodies[role],graph,epsilon,mesh=body_meshes[role])
                            closed[role]=qa.collision_metrics(output["points"],collider,metres,output["free_indices"])
                        except Exception as error:closed[role]={"status":"unknown","reason":str(error)}
                    trial["samples"][label]={"frame":frame,"final3040_crossings":cross,"closed_proxy_final_vertex_diagnostics":closed,
                        "quality":quality,"target_residual":row["target_residual_all"],"Body_clone":geometry_comparison(body_meshes["RegisteredBody"],body_meshes[clone_name],metres,read.digest,"Private current same-graph native world geometry; uses actual clone snapshot even when different"),
                        "whole_body_separation_proven":False,"accepted":False}
                    trial["samples"][label]["collision_and_endpoint_metric_seconds"]=time.perf_counter()-endpoint_tick
                    trial["samples"][label]["native_snapshot_IO"]=timed_diagnostic_write(args.output/(name+"_"+label+"_native.json"),{"input800":observed,"C800":cmesh,"target3040":requested,"final3040":output,
                        "actual_bodies":body_meshes,"units_to_metres":metres,"accepted":False},diag.json_content)
                    trial["samples"][label]["endpoint_report_IO"]=write()
                    if frame==1:
                        need(all(cross[role].get("status")=="measured" and cross[role].get("actual_crossing_pair_count")==0 for role in ("RegisteredBody",clone_name)),"N final3040 actual Body crossing count not measured zero; no volume/separation claim")
                    if frame==16:target_l,out_l=requested,output
                    if frame==31:target_t,out_t=requested,output;last_bodies=body_meshes;last_quality=quality
            need(target_l is not None and target_t is not None and len(trial["path_readback"])==31,"Incomplete30 native steps")
            trial["manual_response"]=response_summary(target_l["points"],target_t["points"],out_l["points"],out_t["points"],last_quality,prepared.GEOMETRY_GUARD_M,metres)
            trial["performance_scope"]="Separated native frame_set/view_layer, extraction, readback/hash/topology/shape metrics, full-report diagnostic conversion/JSON and disk clocks for this synthetic path. One all-role receipt write per frame. Hash construction stays in metrics. Endpoint collision/metric, full snapshot IO and endpoint report IO recorded separately. Setup/terminal writes and rendering are excluded; not GUI latency/FPS or live author workflow."
            trial["completed"]=True;write()
            if not contact:need(trial["manual_response"]["proceed_to_contact"],"No-contact limited Manual response/shape gate refused; no contact run")
            else:
                report["render"]={"accepted":False,"comparison":"Requested actual-gold T through native Subsurf versus sole Cloth800 output native Subsurf, same actual target Body and cameras; synthetic31 is not author frame31."}
                for label,mesh in (("requested_target",target_t),("contact_final",out_t)):
                    budget();folder=args.output/label;folder.mkdir();report["render"][label]=diag.native_render(SimpleNamespace(frame=31,output=folder),mesh,last_bodies["RegisteredBody"],render_bounds);write()
                report["six_native_images_collected"]=all(report["render"][label].get("success") and set(report["render"][label].get("views",{}))=={"front","side","back"} for label in ("requested_target","contact_final"))
                need(report["six_native_images_collected"],"Six native images not collected")
        report["native_completed"]=True;need([home.frame_current,home.frame_subframe]==report["author_frame"],"Artist original timeline moved")
    except Exception as error:
        report["native_completed"]=False;report["error"]={"reason":str(error),"traceback":traceback.format_exc()};write()
    finally:
        try:
            report["owned_receipt_before_cleanup"]={kind:[{"name":item.name,"pointer":item.as_pointer()} for item in items] for kind,items in ids.items()};write()
            if home is not None and bpy.context.window is not None:bpy.context.window.scene=home
            for probe in shared_probes:bpy.data.objects.remove(probe,do_unlink=True)
            live_objects=[obj for obj in ids["objects"] if all(obj is not probe for probe in shared_probes)]
            key_receipt=[(item.as_pointer(),item.name) for item in ids["keys"]]
            for pointer,name in key_receipt:
                key=bpy.data.shape_keys.get(name);need(key is not None and key.as_pointer()==pointer,"Owned Key identity changed")
                users=bpy.data.user_map(subset={key}).get(key,set());need(len(users)==1,"Owned Key has foreign/nonunique owner")
                mesh=next(iter(users));need(mesh in ids["meshes"] and mesh.shape_keys==key and mesh.users==1,"Owned Key Mesh not unique")
                objects=[obj for obj in live_objects if obj.data==mesh];need(len(objects)==1,"Owned Key lacks exact one Object")
                objects[0].shape_key_clear();remaining=bpy.data.shape_keys.get(name)
                if remaining is not None:
                    need(remaining.as_pointer()==pointer and not bpy.data.user_map(subset={remaining}).get(remaining,set()),"Key acquired foreign users")
                    bpy.data.batch_remove(ids=(remaining,))
            for obj in reversed(live_objects):bpy.data.objects.remove(obj,do_unlink=True)
            for scene in ids["scenes"]:bpy.data.scenes.remove(scene)
            for collection in ids["collections"]:bpy.data.collections.remove(collection)
            for kind in ("meshes","actions","node_groups"):
                for item in ids[kind]:need(item.users==0,"Owned ID still referenced: "+item.name);getattr(bpy.data,kind).remove(item)
            need(not any(item.as_pointer()==pointer for item in bpy.data.shape_keys for pointer,_ in key_receipt),"Owned Key remains")
            report["owned_cleanup_exact"]=True
            if inventory is not None:report["original_ID_inventory_exact"]=prepared.inventory(bpy)==inventory;need(report["original_ID_inventory_exact"],"Original ID inventory changed")
        except Exception as error:report["cleanup_errors"].append(str(error));report["native_completed"]=False
        if protection is not None:
            try:
                report["protection_before_reload"]=protection.verify();report["cache_after"]=same.cache_state(old_cloth,qa)
                report["cache_metadata_exact"]=report["cache_after"]==report["cache_before"]
                surface.validate(source,rig,qa.skirt.read_record(source));report["canonical_validation_after_cleanup"]=True
            except Exception as error:report["cleanup_errors"].append("pre-reload:"+str(error));report["native_completed"]=False
            write()
            try:
                need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(prepared.INPUT),load_ui=False,use_scripts=False),"Exact input reload failed")
                need(Path(bpy.data.filepath).resolve()==prepared.INPUT.resolve(),"Reopened input identity differs")
                source,rig,_=qa.owned_source(source_name);report["protection_after_reload"]=protection.verify()
                report["pose_after_reload_exact"]=qa.digest(same.pose_checkpoint(rig,qa))==report["author_pose"]
                report["playback_after_reload_exact"]=qa.digest(same.playback_state(qa))==report["author_playback"]
                report["author_frame_after_reload_exact"]=[bpy.context.scene.frame_current,bpy.context.scene.frame_subframe]==report["author_frame"]
            except Exception as error:report["cleanup_errors"].append("reload:"+str(error));report["native_completed"]=False
        report["source_after"]=diag.source_manifest();report["source_disk_exact"]=report["source_after"]==report["source_before"]
        report["input_artist_disk_exact"]={str(p):qa.file_state(p) for p in (prepared.INPUT,prepared.INSTALL,prepared.ARTIST)}==report["files_before"]
        report["script_disk_exact"]=sha(Path(__file__))==report["script_sha256"];report["frozen_pins_disk_exact"]=all(sha(path)==value for path,value in pins.items())
        terminal=("owned_cleanup_exact","original_ID_inventory_exact","cache_metadata_exact","canonical_validation_after_cleanup","pose_after_reload_exact","playback_after_reload_exact","author_frame_after_reload_exact","source_disk_exact","input_artist_disk_exact","script_disk_exact","frozen_pins_disk_exact")
        report["terminal_AND"]=all(report.get(name) is True for name in terminal) and all(report.get(name,{}).get("success") is True for name in ("protection_before_reload","protection_after_reload")) and not report["cleanup_errors"]
        report["native_completed"]=bool(report["native_completed"] and report["terminal_AND"]);report["elapsed_seconds"]=time.perf_counter()-started;write()
    return 0 if report["native_completed"] else 2


if __name__=="__main__":raise SystemExit(main(arguments()))
