"""PREPARED ONLY: two fresh61-frame AfterBody800 L-hold/T-late-hold paths.
Root exclusive factory5.2/disable-autoexec/threads1; soft180/external240.
Frozen6000 constructors and protections; identical physics, synthetic world input.
Reviewed UI6-only Surface successor; current and historical source PIN maps stay separate.
Root CLI-selected V3 disk bytes/mtime are protected only; current save/live/raw identity Unmeasured.
No artist/canonical edits or prior cache/output substitution. Target may intersect
Body: collection, small drift and response do not accept Manual/Both/live workflow.
"""
import argparse,hashlib,importlib.util,json,math,sys,time,traceback
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASE=HERE/"prototype_dynamic_rest800_after_body_contact_preview.py"
BASE_SHA="6000b340275e5361265240a6e89c90036bfc8785db81087876aeef82fda13a87"
AFTER_COMPLETE=HERE/"actual_dynamic_rest800_after_body_contact_51_20261006_172535_775/result/dynamic_rest800_preview.json"
EXTRA_PINS={BASE:BASE_SHA,AFTER_COMPLETE:"88c59f744a3cbf5c485e6d9b85c55da01bf1e8faf19cbafab1e66ddf848cf4d1"}
MIGRATION=HERE.parent/"blender52_migration_20261006"
SAVED52=MIGRATION/"saved52.json";LIVE52=MIGRATION/"live52.json"
ARTIST52_SHA="bbfed9dc983306b79107a742b297e31311d554cdd926665cc963f6644aba8ed0"
EXTRA_PINS.update({SAVED52:"b077048056253defb21ed9aadf92619a006b247072e0858d64037eca5afbb970",
    LIVE52:"4ba3948878bf72619f033b8eeba62b5634c0322ef1e326fae99bb6eb956a0e49"})
def file_sha(path):
    result=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):result.update(block)
    return result.hexdigest()
if file_sha(BASE)!=BASE_SHA:raise RuntimeError("Frozen6000 changed")
spec=importlib.util.spec_from_file_location("frozen_after_body6000",BASE)
frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)  # No main/native executes.
for name in ("need","sha","helper","current_pins","artist_transition","no_contact_proof","historical_cache_proof","history_proof","gold_samples","after_body_samples","after_body_proof","contact_baseline_proof","geometry_comparison","response_summary","timed_diagnostic_write","INPUT_HELPER","CONTINUOUS","STATIC","NO_CONTACT_REPORT","FRESH_REPORTS","POINTER_FAILURE","POINTER_PREDECESSOR","AFTER_REPORT","AFTER_ENDPOINT","PIN","OFFICIAL"):
    globals()[name]=getattr(frozen,name)
OLD_HOLD=HERE/"prototype_dynamic_rest800_twin_hold_preview.py"
DISK_RECEIPT=HERE/"artist_disk_protection_20261006_070562.json"
EXTRA_PINS.update({OLD_HOLD:"9ae09fffd141cc433e7f91c48434e218a32d73d099730eb2eccd3b0372505ce4",
    DISK_RECEIPT:"ff2f0463613d8f98d827be1d0b1a03581d444331f1ffd6d20b41467ff661a597"})
SOURCE_HELPER=HERE/"source_compatibility52_node_ui.py"
DISK_HELPER=HERE/"artist_disk_protection52.py"
PRIOR_DISK_SOURCE=HERE/"prototype_dynamic_rest800_twin_hold_current_disk_preview.py"
PRIOR_SOURCE=HERE/"prototype_dynamic_rest800_twin_hold_source52_preview.py"
EXTRA_PINS.update({SOURCE_HELPER:"08d36c4e561c808ed40a49e6b094085ef687a8a2e02bf5413c56ea203332507b",
    DISK_HELPER:"11d925f0356a45d831ff84339e31bf691df21c257e195497fd36922907167b37",
    PRIOR_DISK_SOURCE:"bacd283cbfc02d92b70ef88f364aa7e50a35ea65a178e3f6a484e3b60c5fd6f0",
    PRIOR_SOURCE:"e83f4470abec7653a75c2d27f7a4d858b782bc946426607d6f69990083ef685c"})
CONTEXT={"source_history":[]}

def shared_module(path):
    need(file_sha(path)==EXTRA_PINS[path],"Frozen shared adapter changed: "+str(path))
    spec=importlib.util.spec_from_file_location("shared_"+path.stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

source_compat=shared_module(SOURCE_HELPER)
disk_compat=shared_module(DISK_HELPER)
EXTRA_PINS.update(source_compat.TRANSITION_PINS)

ENDPOINT_FRAMES=(1,16,31,61)


def migration_history_proof(saved=None,live=None):
    if saved is None:
        need(file_sha(SAVED52)==EXTRA_PINS[SAVED52] and file_sha(LIVE52)==EXTRA_PINS[LIVE52],"Frozen52 save/live receipt changed")
        saved=json.loads(SAVED52.read_text(encoding="utf-8"));live=json.loads(LIVE52.read_text(encoding="utf-8"))
    need(type(saved) is dict and set(saved)=={"Path","Length","SHA256","SavedAt","BlenderVersion","ArtistPid","UiReported","PoseAsset","CharacterDesigner"},"saved52 actual schema differs")
    need(all(type(saved[k]) is str for k in set(saved)-{"Length","ArtistPid"}) and type(saved["Length"]) is int and type(saved["ArtistPid"]) is int,"saved52 actual types differ")
    need(Path(saved["Path"]).resolve()==frozen.ARTIST_CURRENT.resolve() and saved["Length"]==32266934 and saved["SHA256"].lower()==ARTIST52_SHA
        and saved["BlenderVersion"]=="5.2.0 LTS" and saved["ArtistPid"]==12696 and saved["UiReported"]=="Saved X.blend"
        and saved["SavedAt"]=="2026-10-06T18:20:44.3492606+08:00"
        and saved["CharacterDesigner"]=="0.76.3 R8 frozen 147 files, deployment check zero differences","saved52 actual saved baseline differs")
    need(type(live) is dict and set(live)=={"pid","blender_version","blender_binary","filepath","frame","object_mode","rig_bones","active_bone","hips_display_scale","character_designer_file","character_designer_version","character_designer_enabled","asset_libraries","actions"},"live52 actual schema differs")
    need(type(live["pid"]) is int and live["pid"]==saved["ArtistPid"] and live["blender_version"]==saved["BlenderVersion"]
        and Path(live["filepath"]).resolve()==frozen.ARTIST_CURRENT.resolve() and Path(live["blender_binary"]).resolve()==Path(r"D:\Blender5.2\blender.exe").resolve()
        and type(live["frame"]) is int and live["frame"]==39 and live["object_mode"]=="POSE" and type(live["rig_bones"]) is int and live["rig_bones"]==346
        and live["active_bone"]=="f_index.01.L" and live["hips_display_scale"]==[0.,0.,0.] and all(type(x) is float for x in live["hips_display_scale"])
        and live["character_designer_version"]==[0,76,3] and live["character_designer_enabled"] is True
        and type(live["asset_libraries"]) is list and type(live["actions"]) is list,"live52 actual native metadata differs")
    return {"saved_receipt":str(SAVED52),"saved_receipt_sha256":EXTRA_PINS[SAVED52],"live_receipt":str(LIVE52),"live_receipt_sha256":EXTRA_PINS[LIVE52],
        "current_artist_sha256":ARTIST52_SHA,"current_artist_bytes":32266934,"artist_runtime_version":"5.2.0 LTS","artist_observed_pid":12696,
        "old_capture_artist_sha256":frozen.OLD_ARTIST_SHA,"prior6000_disk_artist_sha256":frozen.CURRENT_ARTIST_SHA,
        "old_capture_or6000_vs_new_artist_full_raw_geometry":"Unmeasured","all_other_rig_data_unchanged":"Unrecorded",
        "artist_loaded_for_physics":False,"accepted":False,"scope":"Typed final5.2 save/live receipts establish the current protected disk baseline only; they do not supply a full raw comparison with5.1 gold or prove this5.2 private diagnostic."}



def current_disk_proof():
    need("disk" in CONTEXT,"Root CLI V3 proof not initialized")
    return CONTEXT["disk"]


def artist_state_guard(files):
    """Bind actual new-run boundary state to the CLI receipt, not just each other."""
    matches=[state for path,state in files.items() if Path(path).resolve()==frozen.ARTIST_CURRENT.resolve()]
    need(len(matches)==1,"Actual artist boundary identity missing/ambiguous")
    state=matches[0];disk=current_disk_proof()
    need(type(state) is dict and set(state)=={"sha256","bytes","mtime_ns"}
        and type(state["sha256"]) is str and type(state["bytes"]) is int and type(state["mtime_ns"]) is int,"Actual artist boundary state untyped")
    expected={"sha256":disk["current_artist_sha256"],"bytes":disk["current_artist_bytes"],"mtime_ns":disk["current_artist_mtime_ns"]}
    need(state==expected,"Actual artist boundary bytes/SHA/mtime differs from Root CLI V3 receipt")
    return {"expected_receipt_state":expected,"observed_boundary_state":dict(state),"exact_V3_boundary_match":True,
        "scope":"Disk bytes/SHA/mtime only; current native save/live/model identity remains Unmeasured","accepted":False}


def artist_transition():
    return {"current_disk_protection":current_disk_proof(),"historical_migration_52":migration_history_proof(),
        "historical_caeb_v2":current_disk_proof()["receipt"]["historical_caeb_v2"],
        "history_scope":"bbfed migration and caeb V2 are pinned historical receipts, not current bytes/live/model equivalence",
        "current_native_save_proof":"Unmeasured","current_raw_equivalence":"Unmeasured","artist_loaded_for_physics":False,"accepted":False}


def current_pins(prepared,args):
    # Only this privately imported module is adapted; frozen source files stay exact.
    prepared.PINS=source_compat.current_pins(prepared.PINS,prepared.REPOSITORY)
    pins=frozen.current_pins(prepared);need(pins[prepared.ARTIST]==frozen.CURRENT_ARTIST_SHA,"Expected preceding disk provenance differs")
    pins=source_compat.current_pins(pins,prepared.REPOSITORY)
    need(prepared.PINS[prepared.SURFACE]==pins[prepared.SURFACE]==source_compat.SURFACE_SHA,"Private loader/runtime Surface PIN differs")
    CONTEXT["disk"]=disk_compat.proof(args.artist_receipt,args.artist_receipt_sha256,prepared.ARTIST)
    pins[prepared.ARTIST]=CONTEXT["disk"]["current_artist_sha256"]
    return pins|EXTRA_PINS|{Path(CONTEXT["disk"]["path"]):CONTEXT["disk"]["sha256"]}


def legacy_pins(pins):
    """Old-report comparison sees Surface9d/artist2b36; never a runtime guard."""
    key=frozen.ARTIST_CURRENT;need(pins[key]==current_disk_proof()["current_artist_sha256"],"Current CLI disk protection baseline missing")
    return source_compat.historical_surface_pins(pins)|{key:frozen.OLD_ARTIST_SHA}


def legacy_files(recorded,current,old_sha=frozen.OLD_ARTIST_SHA,old_bytes=32254503):
    before={str(Path(p).resolve()).casefold():v for p,v in recorded.items()};after={str(Path(p).resolve()).casefold():v for p,v in current.items()}
    need(set(before)==set(after),"Historical file inventory differs")
    artist=str(frozen.ARTIST_CURRENT.resolve()).casefold()
    for path,value in before.items():
        if path==artist:
            need(value["sha256"]==old_sha and value["bytes"]==old_bytes and after[path]["sha256"]==current_disk_proof()["current_artist_sha256"] and after[path]["bytes"]==current_disk_proof()["current_artist_bytes"],"Historical/current disk identity differs")
        else:need(value==after[path],"Non-artist historical file changed: "+path)
    return recorded


def historical_source(row,path,pins,current_source):
    path=Path(path);need(path in pins and file_sha(path)==pins[path],"Historical source report is not pinned")
    need(row["source_before"]==row["source_after"],"Historical own complete source protection failed")
    view,proof=source_compat.history_view(row["source_before"],current_source,source_compat.REPOSITORY)
    CONTEXT["source_history"].append({"report":str(path),"report_sha256":pins[path],"proof":proof})
    return view


def no_contact_proof(prior,pins,current_source,current_files):
    historical=legacy_files(prior["files_before"],current_files)
    old_source=historical_source(prior,NO_CONTACT_REPORT,pins,current_source)
    result=frozen.no_contact_proof(prior,legacy_pins(pins),old_source,historical)
    result["current52_raw_geometry_comparison"]="Unmeasured";return result


def history_proof(sealed,fresh,current_source,pins,endpoint_path,endpoint_hash):
    prepared=helper(INPUT_HELPER)
    old_source=historical_source(sealed,prepared.SEALED_REPORT,pins,current_source)
    for label,row in fresh.items():
        need(historical_source(row,FRESH_REPORTS[label],pins,current_source)==old_source,"Pinned historical source literals differ")
    return frozen.history_proof(sealed,fresh,old_source,legacy_pins(pins),endpoint_path,endpoint_hash)


def after_body_proof(row,data,gold,current_source,pins,prepared,raw):
    old_source=historical_source(row,AFTER_REPORT,pins,current_source)
    return frozen.after_body_proof(row,data,gold,old_source,legacy_pins(pins),prepared,raw)


def contact_baseline_proof(pins,current_source,current_files):
    row=json.loads(frozen.CONTACT_COMPLETE.read_text(encoding="utf-8"))
    old_source=historical_source(row,frozen.CONTACT_COMPLETE,pins,current_source)
    return frozen.contact_baseline_proof(legacy_pins(pins),old_source,legacy_files(row["files_before"],current_files))


def after_complete_proof(pins,current_source,current_files):
    row=json.loads(AFTER_COMPLETE.read_text(encoding="utf-8"))
    old_source=historical_source(row,AFTER_COMPLETE,pins,current_source)
    required=("native_completed","terminal_AND","owned_cleanup_exact","original_ID_inventory_exact","cache_metadata_exact","canonical_validation_after_cleanup","pose_after_reload_exact","playback_after_reload_exact","author_frame_after_reload_exact","source_disk_exact","input_artist_disk_exact","script_disk_exact","frozen_pins_disk_exact","six_native_images_collected")
    need(all(name in row and row[name] is True for name in required) and not row["cleanup_errors"] and all(row[name]["success"] is True for name in ("protection_before_reload","protection_after_reload")),"Actual6000 protection incomplete/failed")
    current={str(Path(path).resolve()).casefold():value for path,value in source_compat.historical_surface_pins(pins).items()}
    legacy_files(row["files_before"],current_files,frozen.CURRENT_ARTIST_SHA,32263264)
    historical_current=current|{str(frozen.ARTIST_CURRENT.resolve()).casefold():frozen.CURRENT_ARTIST_SHA}
    need(row["accepted"] is False and row["source_before"]==row["source_after"]==old_source and row["script_sha256"]==BASE_SHA and row["artist_saved"] is False and all(historical_current.get(str(Path(path).resolve()).casefold())==value for path,value in row["pins"].items()),"Actual6000 provenance differs")
    phase=row["trials"]["contact"];need(phase["completed"] is True and len(phase["path_readback"])==31,"Actual6000 path incomplete")
    return {"path":str(AFTER_COMPLETE),"sha256":pins[AFTER_COMPLETE],"historical_runtime":"5.1","native_completed":True,"terminal_AND":True,"accepted":False,"manual_fidelity_accepted":False,"live_or_current_artist_geometry_accepted":False,"scope":"Protected5.1 31-step collection only; source compatibility is preflight metadata, not native verification of changed code."}


def drift_summary(rows,metres,fps,tolerance_m):
    need(len(rows)==10 and [f for f,_ in rows]==list(range(52,62)),"Last10 incomplete")
    need(math.isfinite(fps) and fps>0 and math.isfinite(tolerance_m) and tolerance_m>0,"Tail physical measure invalid")
    count=len(rows[0][1]);need(count==3040 and all(len(p)==count and all(math.isfinite(float(x)) for v in p for x in v) for _,p in rows),"Tail native3040 invalid")
    norms=lambda a,b:[math.sqrt(math.fsum((x-y)**2 for x,y in zip(p,q)))*metres for p,q in zip(a,b)]
    first,last=rows[0][1],rows[-1][1];excursion=max(max(norms(p,first)) for _,p in rows)
    delta=norms(last,first);interval=[norms(rows[i][1],rows[i-1][1]) for i in range(1,10)]
    return {"frames":[f for f,_ in rows],"window_seconds":9/fps,"maximum_excursion_from52_m":excursion,"final_minus52_maximum_m":max(delta),"final_minus52_rms_m":math.sqrt(math.fsum(x*x for x in delta)/count),"interval_RMS_speed_m_s":[math.sqrt(math.fsum(x*x for x in v)/count)*fps for v in interval],"maximum_interval_vertex_speed_m_s":max(max(v)*fps for v in interval),"diagnostic_excursion_limit_m":tolerance_m,"low_drift_diagnostic":excursion<=tolerance_m,"equilibrium_proven":False,"accepted":False,"scope":"Last10 diagnostic limit0.1*unchanged contact distance_min; not equilibrium or Manual/clearance acceptance."}


def target_scope(crossings,closed,count):
    need(count==3040,"Exact native3040 required");vertices=set();unresolved=False;total=0
    for role,row in crossings.items():
        if row.get("status")!="measured":unresolved=True;continue
        total+=len(row["crossing_pairs"])
        for pair in row["crossing_pairs"]:vertices.update(pair["dress_vertices"])
        unresolved=unresolved or any(row.get(k) for k in ("boundary_unresolved","coplanar_unresolved","degenerate_unresolved"))
    unknown=any("inside_vertices" not in row for row in closed.values());infeasible=total>0 or any(row.get("inside_vertices",0)>0 for row in closed.values())
    return {"all_target_native_triangles":True,"actual_triangle_crossings":crossings,"closed_proxy_sampled_vertices":closed,"vertices_on_measured_target_crossing_triangles":sorted(vertices),"complement_native_vertex_count":count-len(vertices),"full_exact_target_contact_feasible":False if infeasible else "Unknown","classification":"intersecting_requested_target" if infeasible else "unresolved" if unresolved or unknown else "no_measured_crossing_but_margin_volume_unproved","manual_full_shape_accepted":False,"complement_contact_margin_proven":False,"accepted":False,"scope":"Strict intersections exclude full-target nonintersection acceptance. No-crossing/openBody/vertex sign alone cannot prove feasible volume or margin; complement is not declared contact-free."}


def source_adapter_controls():
    """Small real-ABI PIN/loader checks; no historical geometry or native imports."""
    prepared=helper(INPUT_HELPER);original=dict(prepared.PINS)
    fresh=source_compat.current_pins(original,prepared.REPOSITORY)
    historical=source_compat.historical_surface_pins(fresh,prepared.REPOSITORY)
    need(original==historical and original[prepared.SURFACE]==source_compat.SURFACE_BEFORE_SHA
        and fresh[prepared.SURFACE]==source_compat.SURFACE_SHA and original!=fresh,"Fresh/historical Surface PIN separation differs")
    need(all(fresh[path]==value for path,value in original.items() if path!=prepared.SURFACE),"Unrelated private PIN changed")
    prepared.PINS=fresh
    # Execute the exact loader guard with an AST-only module-body stub: workflow
    # imports mathutils in Blender, which a standard-library control must not fake.
    import ast
    loader_tree=ast.parse(Path(prepared.__file__).read_text(encoding="utf-8"))
    loader_def=next(node for node in loader_tree.body if isinstance(node,ast.FunctionDef) and node.name=="load")
    def load_spec(name,path):
        def syntax_only(module):ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        return SimpleNamespace(origin=str(path),loader=SimpleNamespace(exec_module=syntax_only))
    loader_namespace={"HERE":prepared.HERE,"PINS":prepared.PINS,"need":need,"sha":sha,
        "importlib":SimpleNamespace(util=SimpleNamespace(spec_from_file_location=load_spec,
            module_from_spec=lambda spec:SimpleNamespace(__file__=spec.origin)))}
    exec(compile(ast.Module(body=[loader_def],type_ignores=[]),str(prepared.__file__),"exec"),loader_namespace)
    loaded=loader_namespace["load"](str(prepared.SURFACE))
    need(Path(loaded.__file__).resolve()==prepared.SURFACE.resolve()
        and prepared.PINS[prepared.SURFACE]==source_compat.SURFACE_SHA,"Private loader Surface PIN not synchronized")
    for name,adapter in (("current",source_compat.current_pins),("historical",source_compat.historical_surface_pins)):
        bad=dict(fresh);bad[prepared.SURFACE]="0"*64
        try:adapter(bad,prepared.REPOSITORY)
        except RuntimeError:continue
        raise RuntimeError("Unknown Surface PIN accepted: "+name)
    need(original[prepared.SURFACE]==source_compat.SURFACE_BEFORE_SHA,"Original PIN map was mutated")
    return {"passed":True,"current_Surface_sha256":fresh[prepared.SURFACE],"historical_Surface_sha256":historical[prepared.SURFACE],
        "private_loader_PINS_synced":True,"compiled_loader_body":"AST parsed only; native imports not executed",
        "unrelated_PIN_values_exact":True,"unknown_Surface_PIN_negatives":2,"native_run":False,"accepted":False}


def pure_checks():
    base=helper(CONTINUOUS);n=[[0.,0.,0.]];l=[[1.,0.,0.]];t=[[2.,0.,0.]]
    need(base.path_weights(1,30)==(0.,0.) and base.path_weights(16,30)==(1.,0.) and base.path_weights(31,30)==(0.,1.),"N/L/T timing")
    need(all(abs(base.path_points(n,l,l,base.path_weights(min(f,31),30))[0][0]-1.)<1e-15 for f in range(16,62)),"L not held")
    need(base.path_points(n,l,t,base.path_weights(31,30))==t,"T hold target")
    points=[[0.,0.,0.]]*3040;rows=[(f,points) for f in range(52,62)];need(drift_summary(rows,1.,30.,.0002)["low_drift_diagnostic"],"Stationary tail")
    rows=[(f,[[.001*(f-52),0.,0.]]*3040) for f in range(52,62)];need(not drift_summary(rows,1.,30.,.0002)["low_drift_diagnostic"],"Moving tail falsely stable")
    empty={"status":"measured","crossing_pairs":[],"boundary_unresolved":[],"coplanar_unresolved":[],"degenerate_unresolved":[]}
    need(target_scope({"Body":empty},{"P":{"inside_vertices":0}},3040)["full_exact_target_contact_feasible"]=="Unknown","No-crossing falsely feasible")
    row=dict(empty,crossing_pairs=[{"dress_vertices":[1,2,3]}]);scope=target_scope({"Body":row},{"P":{"inside_vertices":0}},3040);need(scope["full_exact_target_contact_feasible"] is False and scope["vertices_on_measured_target_crossing_triangles"]==[1,2,3],"Target crossing accepted")
    saved=json.loads(SAVED52.read_text(encoding="utf-8"));live=json.loads(LIVE52.read_text(encoding="utf-8"));migration_history_proof(saved,live)
    import copy
    negatives=[]
    for name,owner,field,value in (("unsaved",0,"UiReported","Unknown"),("wrong_sha",0,"SHA256","0"*64),("missing_save",0,"Length",None),("old_runtime",1,"blender_version","5.1.0"),("unknown_enabled",1,"character_designer_enabled",None),("bool_pid",1,"pid",True)):
        rows=[copy.deepcopy(saved),copy.deepcopy(live)]
        if value is None and name=="missing_save":del rows[owner][field]
        else:rows[owner][field]=value
        try:migration_history_proof(*rows)
        except (RuntimeError,KeyError,TypeError):negatives.append(name);continue
        raise RuntimeError("False/Unknown52 receipt accepted: "+name)
    observed=current_disk_proof();disk_negatives=[]
    for name,field,value in (("wrong_sha","artist_sha256","bad"),("bool_size","artist_bytes",True),("missing_mtime","artist_mtime_ns",None),("invented_save","current_native_save_proof","PASS"),("invented_raw","current_disk_equals_old_7ac_fullraw",True),("invented_live","live_unsaved_state","Clean")):
        bad=copy.deepcopy(observed["receipt"])
        if value is None:del bad[field]
        else:bad[field]=value
        try:disk_compat.typed_receipt(bad)
        except (RuntimeError,KeyError,TypeError):disk_negatives.append(name);continue
        raise RuntimeError("False/Unknown V3 disk integration accepted: "+name)
    state={"sha256":observed["current_artist_sha256"],"bytes":observed["current_artist_bytes"],"mtime_ns":observed["current_artist_mtime_ns"]}
    artist_state_guard({str(frozen.ARTIST_CURRENT):state});boundary_negatives=[]
    for name,field,value in (("mtime_drift_same_bytes","mtime_ns",state["mtime_ns"]+1),("bytes_drift","bytes",state["bytes"]+1),("sha_drift","sha256","0"*64),("bool_mtime","mtime_ns",True),("missing_mtime","mtime_ns",None),("bool_bytes","bytes",True)):
        bad=dict(state)
        if value is None:del bad[field]
        else:bad[field]=value
        try:artist_state_guard({str(frozen.ARTIST_CURRENT):bad})
        except (RuntimeError,KeyError,TypeError):boundary_negatives.append(name);continue
        raise RuntimeError("V3 boundary mismatch accepted: "+name)
    return {"passed":True,"source_adapter_controls":source_adapter_controls(),"V3_boundary_positive":1,"V3_boundary_negatives":boundary_negatives,"CLI_V3_disk_positive":1,"CLI_V3_disk_negatives":disk_negatives,"focused_path_drift_target_controls":6,"typed52_history_positive":1,"typed52_history_negatives":negatives,"native_run":False,"accepted":False}


def arguments():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path);parser.add_argument("--pure-checks",action="store_true");parser.add_argument("--max-seconds",type=float,default=180.);parser.add_argument("--render",action="store_true",default=True);parser.add_argument("--artist-receipt",type=Path,required=True);parser.add_argument("--artist-receipt-sha256",required=True)
    values=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:] if "--pure-checks" in sys.argv else [];args=parser.parse_args(values)
    if not args.pure_checks:
        need(args.output is not None and 30.<=args.max_seconds<=180.,"Fresh output/soft30..180; root external240 for soft180")
        args.output=args.output.resolve();need(args.output.is_relative_to(HERE) and args.output!=HERE and not args.output.exists(),"Refuse existing/non-Validation output")
    args.steps=30;args.body_vertex_limit=100000;args.triangle_pair_limit=10000
    return args

def main(args):
    prepared=helper(INPUT_HELPER);pins=current_pins(prepared,args)
    need(all(sha(path)==value for path,value in pins.items()),"Frozen input/helper/CLI receipt changed")
    if args.pure_checks:print(json.dumps(pure_checks()));return 0
    import bpy
    from mathutils import Matrix,Vector
    need(bpy.app.background and bpy.app.version[:2]==(5,2) and not bpy.data.filepath and "--factory-startup" in sys.argv
        and "--disable-autoexec" in sys.argv and "--threads" in sys.argv and sys.argv[sys.argv.index("--threads")+1]=="1","Root-leased empty factory5.2 only")
    need(Path(bpy.app.binary_path).resolve()==Path(r"D:\Blender5.2\blender.exe").resolve(),"Explicit5.2 binary differs")
    base=helper(CONTINUOUS);static=helper(STATIC)
    workflow,same,read=(prepared.load(name) for name in ("verify_actual_surface_workflow.py","verify_actual_same_frame_pose.py","verify_actual_body_proxy_coverage.py"))
    qa,diag,addon,surface=workflow.load_dependencies();args.input,args.install_report=prepared.INPUT,prepared.INSTALL
    args.expected_surface_sha,args.expected_worker_sha=pins[prepared.SURFACE],pins[prepared.WORKER]
    args.output.mkdir();destination=args.output/"dynamic_rest800_preview.json";started=time.perf_counter()
    report={"prepared_only_source":True,"native_completed":False,"accepted":False,"artist_saved":False,"stage":"NATIVE_AFTER_BODY800_TWIN61_HOLD_PREVIEW_52",
        "scope":"Two independent61-frame synthetic world paths from5.1 native50e AfterBody800; identical N1-to-L16 prefix, L_hold stays L, T_late_hold reaches T31 then stays T through61. Sole Cloth800 -> native Subsurf3040. Root CLI-selected V3 current disk bytes/mtime are protected; current native save/live/raw vsoldfixture remain Unmeasured. Only reviewed UI6-only Surface9d-to-a58 plus Forearm and Init source deltas admitted by pinned source adapter; actual full source manifests stay unmodified. No live BodyAttachment/author Actions/Original/intermediate bonepose test or deployment. Old5.1 results remain history, not current runtime acceptance.",
        "runtime_version":bpy.app.version_string,"runtime_binary":bpy.app.binary_path,"current_artist_geometry":"Unmeasured","INPUT_CLOTH_support":"UnsupportedUntilEndToEndVerified",
        "script_sha256":sha(Path(__file__)),"pins":{str(path):value for path,value in pins.items()},"pure_checks":pure_checks(),
        "source_before":diag.source_manifest(),"files_before":{str(p):qa.file_state(p) for p in (prepared.INPUT,prepared.INSTALL,prepared.ARTIST)},"trials":{},"cleanup_errors":[]}
    report["artist_disk_protection_and_migration_history"]=artist_transition()
    report["historical_source_compatibility_proofs"]=CONTEXT["source_history"]
    report["source_compatibility_helper"]={"path":str(SOURCE_HELPER),"sha256":EXTRA_PINS[SOURCE_HELPER],"native_compatibility_accepted":False}
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
    def lightweight_body(obj,graph):
        """Exact native positions/index/topology each step; omit unused weights/triangulation hashes."""
        evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh(preserve_all_data_layers=False,depsgraph=graph)
        try:
            return {"points":[evaluated.matrix_world @ vertex.co for vertex in mesh.vertices],
                "native_vertex_index_order":[int(vertex.index) for vertex in mesh.vertices],
                "edges":[tuple(edge.vertices) for edge in mesh.edges],"faces":[tuple(face.vertices) for face in mesh.polygons],
                "native_triangulation_sha256":"UnmeasuredOnNonEndpointLightRead"}
        finally:evaluated.to_mesh_clear()
    def identity(mesh,expected):
        keys=("native_vertex_index_order","edges","faces")
        need(diag.json_content({k:mesh[k] for k in keys})=={k:expected[k] for k in keys},"Private native topology/index identity changed")
    try:
        report["current_artist_before_V3_receipt"]=artist_state_guard(report["files_before"])
        source_gate=source_compat.gate_namespace(vars(workflow),prepared.REPOSITORY)
        source_name=source_gate(args,report,qa,diag);addon.register()
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
        after_history=json.loads(AFTER_REPORT.read_text(encoding="utf-8"))
        with AFTER_ENDPOINT.open(encoding="utf-8") as stream:after_input=after_body_samples(stream)
        report["native_after_body_input_proof"]=after_body_proof(after_history,after_input,gold,report["source_before"],pins,prepared,diag.json_content(qa.raw_mesh_content(source)))
        report["completed_before_body_contact_baseline"]=contact_baseline_proof(pins,report["source_before"],report["files_before"])
        report["completed_after_body_51_baseline"]=after_complete_proof(pins,report["source_before"],report["files_before"])
        write()
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
            "captured_native_after_body_attachment_input":True,"live_C_H0_SurfaceDeform_exercised":False,"classification":"Raw80 follows measured native50e AfterBody N/L/T waist trajectory. World movement is input, and pin error remains relative to CURRENT actual input; no physical pin deviation is forgiven."}
        report["waist_scope"]["Manual_L_to_T_80_movement"]=base.residual(gold["T"]["native_meshes"]["ManualOracle800"]["points"],gold["L"]["native_meshes"]["ManualOracle800"]["points"],fixed,metres)
        need(report["waist_scope"]["Manual_L_to_T_80_movement"]["maximum_m"]==0.,"Captured Manual action moves hard80; reject this isolated input")
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
        (args.output/"after_body_geometry_index.json").write_text(json.dumps({"sealed_reference":report["sealed_gold"],"actual_after_body_reference":report["native_after_body_input_proof"],"endpoint_geometry_hashes":{l:{r:m["native_geometry_sha256"] for r,m in rs.items()} for l,rs in snapshots.items()},"accepted":False},indent=2),encoding="utf-8")
        del snapshots;write()
        reference_gold=gold;prefixes={};held={};previous_c={}
        need(all(reference_gold["L"]["native_meshes"][role]["points"]==reference_gold["T"]["native_meshes"][role]["points"] for role in roles[1:]),"Hold comparison Body/colliders must be exact same L/T")
        for name in ("L_hold","T_late_hold"):
            gold={label:reference_gold[label if label!="T" or name=="T_late_hold" else "L"] for label in ("N","L","T")}
            contact=True
            budget();trial={"completed":False,"accepted":False,"path_readback":[],"samples":{},"timings":[],"parameters":{}}
            report["trials"][name]=trial;write()
            private=own("scenes",bpy.data.scenes.new("QA Dynamic800 "+name));private.unit_settings.system,private.unit_settings.scale_length=home.unit_settings.system,home.unit_settings.scale_length
            private.render.fps,private.render.fps_base=home.render.fps,home.render.fps_base;private.gravity=home.gravity;private.use_gravity=home.use_gravity;private.frame_start,private.frame_end=1,61
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
            for captured in (animation,*body_animations.values()):
                for key,value in zip(captured["blocks"],(0.,1.)):
                    key.value=value;need(key.keyframe_insert(data_path="value",frame=61),"Owned hold key insertion failed")
                for curve in qa.curve_paths(captured["action"]):
                    curve.extrapolation="CONSTANT"
                    for point in curve.keyframe_points:point.interpolation="LINEAR"
            cloth=c.modifiers.new("QA Dynamic Rest Cloth","CLOTH");surface._copy_scalars(old_cloth.settings,cloth.settings)
            surface._copy_scalars(old_cloth.collision_settings,cloth.collision_settings);surface._copy_scalars(old_cloth.settings.effector_weights,cloth.settings.effector_weights)
            cloth.settings.vertex_group_mass=pin.name;cloth.settings.rest_shape_key=None;cloth.settings.use_dynamic_mesh=True
            cloth.collision_settings.use_collision=contact;cloth.collision_settings.collection=collision
            if not contact:cloth.settings.effector_weights.gravity=0.
            for prop in cloth.settings.bl_rna.properties:
                if prop.identifier.startswith("vertex_group_"):
                    group_name=getattr(cloth.settings,prop.identifier);need(not group_name or c.vertex_groups.get(group_name) is not None,"Copied Cloth group unavailable: "+prop.identifier)
            cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step=1,61,1
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
                "synthetic_action_slot":animation["slot"],"gravity_policy":"No-contact0 isolates limited Manual response; contact copies current original effector gravity, disclosed distinct condition.","official_implementation_51_history":OFFICIAL,"official_implementation_52":"https://raw.githubusercontent.com/blender/blender/v5.2.0/source/blender/blenkernel/intern/cloth.cc","internal_synthetic_end":61,"two_branch_prefix_end":16,"target_reached_frame":16 if name=="L_hold" else 31}
            physical_fields=("cloth","collision","effectors","collider_scalars","pin_weights","hard80","fps","fps_base","steps","scene_gravity","scene_use_gravity")
            trial["prior_partial_contact_parameters_exact"]={field:diag.json_content(trial["parameters"][field])==prior["trials"]["contact"]["parameters"][field] for field in physical_fields};write()
            need(all(trial["prior_partial_contact_parameters_exact"].values()),"Contact physics/gravity/culling/normal/pin/fps parameters changed from original partial trial")
            trial["visibility"]=read.visibility_evidence([c,probe,target,final,*bodies.values()],cloth,private)
            need(not collision.hide_viewport and not collision.hide_render and all(not obj.hide_get() and not obj.hide_viewport and not obj.hide_render for obj in [c,probe,target,final,*bodies.values()]),"Private collision/output filtering hidden")
            fixed_final=None;target_l=out_l=target_t=out_t=None;last_bodies=None;last_quality=None;target_raw_contract=qa.raw_mesh_content(target);tail=[]
            trial["sample_frames"]=list(ENDPOINT_FRAMES);trial["timing_scope"]="Frame_set/view_layer excludes graph_get and extraction; no GUI FPS/solver-only/AB performance claim"
            for frame in range(1,62):
                budget();tick=time.perf_counter();private.frame_set(frame);bpy.context.view_layer.update();frame_cost=time.perf_counter()-tick
                graph=bpy.context.evaluated_depsgraph_get();tick=time.perf_counter();weights=base.path_weights(min(frame,31),30)
                endpoint=frame in ENDPOINT_FRAMES;read_final=endpoint or frame>=52
                observed=native(probe,graph);cmesh=native(c,graph)
                requested=native(target,graph) if endpoint else None;output=native(final,graph) if read_final else None
                body_meshes={role:(native(obj,graph) if endpoint else lightweight_body(obj,graph)) for role,obj in bodies.items()}
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
                receipt_needed=endpoint or any(error.get("status")!="measured" or error.get("maximum_m",math.inf)>min(prepared.GEOMETRY_GUARD_M,precision["metres"]) for error in row["input_errors"].values())
                receipt_io=write() if receipt_needed else {"diagnostic_conversion_serialization_seconds":0.,"diagnostic_disk_write_seconds":0.}
                # All six receipts exist in report before guards; any throw writes them before cleanup.
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
                if endpoint:
                    need(len(requested["points"])==len(output["points"])==3040 and requested["native_vertex_index_order"]==output["native_vertex_index_order"],"Native Subsurf3040 identity differs")
                    need(requested["edges"]==output["edges"] and requested["faces"]==output["faces"],"Final/target native topology differs")
                    need(requested["weights"]==output["weights"] and requested["native_group_mapping"]==output["native_group_mapping"],"Final/target native weights/groups differ")
                    now_fixed=[i for i,row in enumerate(requested["weights"]) if any(x["index"]==waist_index and x["weight"]>=.999 for x in row)]
                    need(len(now_fixed)==160 and (fixed_final is None or fixed_final==now_fixed),"Native final hard-waist identity differs");fixed_final=now_fixed
                    for mesh in (requested,output):mesh["free_indices"]=[i for i in range(3040) if i not in set(fixed_final)]
                pin_error=prepared.error_summary(cmesh["points"],observed["points"],metres,fixed);row["raw80_relative_current_pin_error"]=pin_error
                row["gold80_world_movement_from_N"]=prepared.error_summary(observed["points"],original["points"],metres,fixed)
                need(pin_error["maximum_m"]<=precision["metres"],"Raw80 deviates from CURRENT gold pin trajectory")
                need(all(math.isfinite(float(x)) for mesh in (observed,cmesh) for p in mesh["points"] for x in p),"C800/input finite guard")
                if frame==15:previous_c[name]=[list(p) for p in cmesh["points"]]
                if read_final:
                    need(len(output["points"])==3040 and all(math.isfinite(float(x)) for p in output["points"] for x in p),"Actual final3040 finite/identity guard")
                if frame>=52:tail.append((frame,[list(p) for p in output["points"]]))
                if endpoint:
                    quality=static.metrics(requested["points"],output["points"],requested["edges"],output["triangles"],fixed_final,metres)
                    row["final_quality_relative_current_target"]=quality;row["target_residual_all"]=base.residual(output["points"],requested["points"],list(range(3040)),metres)
                    row["normal_diagnostics"]=base.normal_diagnostics(requested["points"],output["points"],output["triangles"])
                row["metrics_seconds"]=time.perf_counter()-tick-sum(receipt_io.values());row.update(receipt_io)
                trial["timings"].append({k:row[k] for k in ("frame","frame_set_and_view_layer_seconds","native_extraction_seconds","metrics_seconds","diagnostic_conversion_serialization_seconds","diagnostic_disk_write_seconds")})
                if endpoint:
                    endpoint_tick=time.perf_counter()
                    label={1:"N",16:"L",31:"ramp_end",61:"held_end"}[frame];epsilon=max(1.e-8,(bounds["upper"]-bounds["lower"])*1.e-6)
                    cross={role:diag.triangle_crossings(output,mesh,bounds,args.triangle_pair_limit,epsilon) for role,mesh in body_meshes.items()}
                    closed={}
                    for role in closed_names:
                        try:
                            qa.physics._closed_collider(bodies[role]);collider=qa.ClosedCollider(bodies[role],graph,epsilon,mesh=body_meshes[role])
                            closed[role]=qa.collision_metrics(output["points"],collider,metres,output["free_indices"])
                        except Exception as error:closed[role]={"status":"unknown","reason":str(error)}
                    feasibility={"full_exact_target_contact_feasible":"Unknown","accepted":False,"scope":"Target feasibility sampled only at T_late_hold61; old5.1 target intersections remain historical evidence. Final actual output collision/quality still measured at every1/16/31/61 endpoint."}
                    if name=="T_late_hold" and frame==61:
                        all_target=dict(requested,free_indices=list(range(3040)))
                        target_cross={role:diag.triangle_crossings(all_target,mesh,bounds,args.triangle_pair_limit,epsilon) for role,mesh in body_meshes.items()}
                        target_closed={}
                        for role in closed_names:
                            try:
                                qa.physics._closed_collider(bodies[role]);collider=qa.ClosedCollider(bodies[role],graph,epsilon,mesh=body_meshes[role])
                                target_closed[role]=qa.collision_metrics(requested["points"],collider,metres,list(range(3040)))
                            except Exception as error:target_closed[role]={"status":"unknown","reason":str(error)}
                        feasibility=target_scope(target_cross,target_closed,3040)
                    trial["samples"][label]={"frame":frame,"requested_target_feasibility":feasibility,"final3040_crossings":cross,"closed_proxy_final_vertex_diagnostics":closed,
                        "quality":quality,"target_residual":row["target_residual_all"],"Body_clone":geometry_comparison(body_meshes["RegisteredBody"],body_meshes[clone_name],metres,read.digest,"Private current same-graph native world geometry; uses actual clone snapshot even when different"),
                        "whole_body_separation_proven":False,"accepted":False}
                    trial["samples"][label]["final_collision_filter"]={"native_triangle_count":len(output["triangles"]),
                        "tested_triangles_in_band":cross["RegisteredBody"].get("dress_region_triangles","Unknown"),
                        "excluded_all_fixed_triangles":sum(all(vertex in set(fixed_final) for vertex in triangle) for triangle in output["triangles"]),
                        "closed_proxy_requested_test_vertex_count":len(output["free_indices"]),"excluded_derived_waist_vertices":len(fixed_final),
                        "scope":"Triangle test includes any free corner inside captured full-Body envelope. Closed-depth samples free2880; derived160 is not an independent hard-fixed/separation proof. Counts describe filters, not successful tests or Body volume clearance."}
                    trial["samples"][label]["collision_and_endpoint_metric_seconds"]=time.perf_counter()-endpoint_tick
                    if frame==61:
                        trial["samples"][label]["native_snapshot_IO"]=timed_diagnostic_write(args.output/(name+"_"+label+"_native.json"),{"input800":observed,"C800":cmesh,"target3040":requested,"final3040":output,
                            "actual_bodies":body_meshes,"units_to_metres":metres,"accepted":False},diag.json_content)
                    else:
                        trial["samples"][label]["native_mesh_digest"]={role:{"count":len(mesh["points"]),"points_sha256":read.digest([list(p) for p in mesh["points"]]),"native_vertex_face_edge_sha256":mesh["native_vertex_face_edge_sha256"],"native_triangulation_sha256":mesh["native_triangulation_sha256"]} for role,mesh in {"input800":observed,"C800":cmesh,"target3040":requested,"final3040":output,**body_meshes}.items()}
                    trial["samples"][label]["endpoint_report_IO"]=write()
                    if frame==1:
                        need(all(cross[role].get("status")=="measured" and cross[role].get("actual_crossing_pair_count")==0 for role in ("RegisteredBody",clone_name)),"N final3040 actual Body crossing count not measured zero; no volume/separation claim")
                    if frame==16:
                        target_l,out_l=requested,output
                        prefixes[name]={"C15":previous_c[name],"C16":[list(p) for p in cmesh["points"]],"O16":[list(p) for p in output["points"]]}
                        if name=="T_late_hold":
                            prefix={role:base.residual(prefixes[name][role],prefixes["L_hold"][role],list(range(len(prefixes[name][role]))),metres) for role in prefixes[name]}
                            report["same_prefix_actual_geometry"]=prefix;write()
                            need(all(item["maximum_m"]<=precision["metres"] for item in prefix.values()),"Two fresh simulations diverge before identical L prefix")
                            report["prefix_internal_native_velocity_or_solver_state"]="Unmeasured; position-only same15/16 prefix evidence, caches independent"
                    if frame==61:
                        held[name]={"requested":requested,"output":output,"quality":quality,"bodies":body_meshes}
                    if frame==31:target_t,out_t=requested,output;last_bodies=body_meshes;last_quality=quality
            need(target_l is not None and target_t is not None and len(trial["path_readback"])==61 and len(tail)==10,"Incomplete60 native steps/tail")
            trial["late10_drift"]=drift_summary(tail,metres,private.render.fps/private.render.fps_base,float(cloth.collision_settings.distance_min)*metres*.1)
            trial["manual_response"]=response_summary(target_l["points"],target_t["points"],out_l["points"],out_t["points"],last_quality,prepared.GEOMETRY_GUARD_M,metres)
            trial["performance_scope"]="Frame_set/view_layer, extraction, finite/index/raw/input/pin/hash checks and serialization/disk clocks are separate. Full target/final quality/collision and snapshots only1,16,31,61; final extraction additionally52..61. Receipt IO only endpoints/failures; all six pending role receipts persist via catch before cleanup. Graph_get is outside timing blocks. Setup/render/terminal costs excluded; not GUI latency/FPS or solver-only cost."
            trial["completed"]=True;write()
            if name=="T_late_hold":
                report["render"]={"accepted":False,"comparison":"Requested native50e AfterBody T versus sole Cloth800 final at internal61 after30 hold steps; same actual captured Body/cameras. Internal61 is not author frame61."}
                for label,mesh in (("requested_target",held[name]["requested"]),("contact_final",held[name]["output"])):
                    budget();folder=args.output/label;folder.mkdir();report["render"][label]=diag.native_render(SimpleNamespace(frame=61,output=folder),mesh,held[name]["bodies"]["RegisteredBody"],render_bounds);write()
                report["six_native_images_collected"]=all(report["render"][label].get("success") and set(report["render"][label].get("views",{}))=={"front","side","back"} for label in ("requested_target","contact_final"))
                need(report["six_native_images_collected"],"Six native images not collected")
        report["same_time61_manual_response"]=response_summary(held["L_hold"]["requested"]["points"],held["T_late_hold"]["requested"]["points"],held["L_hold"]["output"]["points"],held["T_late_hold"]["output"]["points"],held["T_late_hold"]["quality"],prepared.GEOMETRY_GUARD_M,metres)
        report["same_time61_manual_response"]["scope"]="Same61 clock under two independent caches, matching15/16 position prefix, exact same captured L/T Body. Gain and residual are diagnostics; late10 does not prove equilibrium, target may intersect. Contact-safe Manual/Both and live workflow remain unaccepted."
        report["manual_acceptance_scope"]={"target_scope":report["trials"]["T_late_hold"]["samples"]["held_end"]["requested_target_feasibility"],"natural_Both_accepted":False,"Manual_fidelity_accepted":False,"complement_contact_safe_proven":False,"scope":"Full target may be infeasible. Same-time response and low last10 drift are diagnostics, not convergence/contact-safe subset/live acceptance. No shape changes installed."}
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
        try:
            report["current_artist_after_V3_receipt"]=artist_state_guard({str(prepared.ARTIST):qa.file_state(prepared.ARTIST)})
        except Exception as error:
            report["current_artist_after_V3_receipt"]={"exact_V3_boundary_match":False,"reason":str(error)}
            report["cleanup_errors"].append("V3 artist boundary:"+str(error));report["native_completed"]=False
        report["script_disk_exact"]=sha(Path(__file__))==report["script_sha256"];report["frozen_pins_disk_exact"]=all(sha(path)==value for path,value in pins.items())
        terminal=("owned_cleanup_exact","original_ID_inventory_exact","cache_metadata_exact","canonical_validation_after_cleanup","pose_after_reload_exact","playback_after_reload_exact","author_frame_after_reload_exact","source_disk_exact","input_artist_disk_exact","script_disk_exact","frozen_pins_disk_exact")
        report["terminal_AND"]=all(report.get(name) is True for name in terminal) and all(report.get(name,{}).get("success") is True for name in ("protection_before_reload","protection_after_reload")) and not report["cleanup_errors"]
        report["terminal_AND"]=report["terminal_AND"] and all(report.get(name,{}).get("exact_V3_boundary_match") is True for name in ("current_artist_before_V3_receipt","current_artist_after_V3_receipt"))
        report["native_completed"]=bool(report["native_completed"] and report["terminal_AND"]);report["elapsed_seconds"]=time.perf_counter()-started;write()
    return 0 if report["native_completed"] else 2

if __name__=="__main__":raise SystemExit(main(arguments()))
