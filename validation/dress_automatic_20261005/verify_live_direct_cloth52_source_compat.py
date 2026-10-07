"""Prepared LiveCloth successor: frozen physics/action code, strict V3/source gates.

Only immutable7ac is loaded by native QA. The completed e754 Direct input proof
is hash-selected independently of current artist disk-only protection. Its artist
state is historical, never current save/UI/fullraw proof. New artist integration,
Automatic Original, Keys, Unity export and effect acceptance remain unproved.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
LIVE=HERE/"verify_live_direct_cloth52.py"
LIVE_SHA="9646529e108a7ada6f04c17e013c8f70a558773e29b578ce6d00fbd97fc2f2a5"
SOURCE_DIRECT=HERE/"verify_direct_main_manual_input52_source_compat.py"
SOURCE_DIRECT_SHA="e7544206bff4824aa0df8682659cf7cece64bfcc99b51276270950b160c5c221"
SOURCE_HELPER=HERE/"source_compatibility52.py"
SOURCE_HELPER_SHA="438e36cd95a9c11f4e1d650f78b58d79fd2866eae8e59a929b993bd42dfbbbdf"
DISK_HELPER=HERE/"artist_disk_protection52.py"
DISK_HELPER_SHA="11d925f0356a45d831ff84339e31bf691df21c257e195497fd36922907167b37"
STAGE="LIVE_DIRECT_MAIN_CLOTH_52_SOURCE_COMPAT"
INPUT_SHA="7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f"
POSITIVE=("direct_main_manual_input_success","native_completed","ready_for_next_private_gate","owned_cleanup_exact","cache_metadata_exact",
          "source_disk_exact","input_artist_disk_exact","script_disk_exact","frozen_pins_disk_exact","canonical_validation_after_reload",
          "pose_after_reload_exact","playback_after_reload_exact","author_frame_after_reload_exact")
RESTORE=("constraint_pointers_and_RNA_exact","raw_pose_exact","id_properties_exact","frame_exact","cloth_flags_exact","cache_exact")
_RUN=None


def need(condition,message):
    if not condition:raise RuntimeError("LiveClothSourceCompat52: "+message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1048576),b""):h.update(block)
    return h.hexdigest()


def load(path,expected,name):
    need(sha(path)==expected,"frozen source changed: "+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def valid_sha(value):
    return type(value) is str and len(value)==64 and all(c in "0123456789abcdef" for c in value)


def validate_completed_report(report,source_compat,source_helper,disk,base):
    """An in-memory validation used after caller verifies the actual report hash."""
    need(type(report) is dict and report.get("stage")==source_compat.STAGE
         and report.get("script_sha256")==SOURCE_DIRECT_SHA,"prerequisite is not completed immutable e754 DirectMain")
    need(all(report.get(k) is True for k in POSITIVE) and report.get("cleanup_errors")==[]
         and report.get("protection_before_reload",{}).get("success") is True
         and report.get("protection_after_reload",{}).get("success") is True,"Direct terminal AND/author protection incomplete")
    need(report.get("accepted") is False and report.get("artist_saved") is False
         and report.get("automatic_Original_semantic_acceptance") is False
         and report.get("runtime52",{}).get("version")==[5,2,0]
         and Path(report["runtime52"].get("binary","")).resolve()==Path("D:/Blender5.2/blender.exe").resolve(),"native5.2/Manual-only scope differs")
    need(report.get("install_input",{}).get("candidate_sha256")==INPUT_SHA,"Direct proof uses different native input")
    restore=report.get("live_author_restore",{})
    need(restore.get("errors")==[] and all(restore.get(k) is True for k in RESTORE),"Direct author restore incomplete")
    current=source_helper.current_manifest()
    need(report.get("source_before")==report.get("source_after")==current,
         "completed Direct canonical/helper full manifest differs from current")
    explicit=report.get("explicit_source_compatibility",{})
    need(explicit.get("reviewed_extra_modules")==source_helper.explicit_modules(base.REPOSITORY)
         and explicit.get("version_only_Init")==source_helper.init_version_only(base.REPOSITORY)
         and explicit.get("canonical_inventory_exact") is True and explicit.get("all_other_canonical_modules_exact") is True
         and explicit.get("old_install_validated_changed_code") is False,"Direct source compatibility recipe incomplete/different")
    pins=report.get("pins",{})
    need(type(pins) is dict,"Direct pin inventory missing")
    normalized={str(Path(path).resolve()).casefold():value for path,value in pins.items()}
    need(len(normalized)==len(pins),"Direct normalized pins duplicated")
    required={SOURCE_DIRECT:SOURCE_DIRECT_SHA,SOURCE_HELPER:SOURCE_HELPER_SHA,DISK_HELPER:DISK_HELPER_SHA,
              base.INPUT:INPUT_SHA,base.SURFACE:base.PINS[base.SURFACE],base.WORKER:base.PINS[base.WORKER]}
    for path,expected in required.items():
        need(normalized.get(str(path.resolve()).casefold())==expected,"Direct prerequisite graph/source pin differs: "+str(path))
    historical=report.get("current_artist_disk_protection",{})
    need(type(historical) is dict and valid_sha(historical.get("sha256")),"Direct historical artist protection missing")
    receipt=disk.typed_receipt(historical.get("receipt"),base.ARTIST)
    need(historical.get("current_artist_sha256")==receipt["artist_sha256"]
         and historical.get("current_artist_bytes")==receipt["artist_bytes"]
         and historical.get("current_artist_mtime_ns")==receipt["artist_mtime_ns"]
         and historical.get("current_native_save_proof")=="Unmeasured"
         and normalized.get(str(Path(historical.get("path","")).resolve()).casefold())==historical["sha256"]
         and normalized.get(str(base.ARTIST.resolve()).casefold())==receipt["artist_sha256"],"Direct historical disk evidence/pins inconsistent")
    return {"script_sha256":SOURCE_DIRECT_SHA,"mechanism_completed":True,"native_input_sha256":INPUT_SHA,
            "source_and_graph_recipe_exact_current":True,"prior_artist_sha256":receipt["artist_sha256"],
            "prior_artist_is_current_protection":False,"prior_artist_vs_current_fullraw":"Unmeasured",
            "scope":"Completed immutable7ac input and Manual Original only; prior artist protection is historical. No Cloth/effect/Keys/Automatic Original acceptance."}


def completed_direct_proof(path,expected,direct):
    need(path.is_absolute() and path.resolve().is_relative_to(HERE) and path.is_file() and valid_sha(expected)
         and sha(path)==expected,"Root-selected completed Direct report absent/changed")
    source_compat=load(SOURCE_DIRECT,SOURCE_DIRECT_SHA,"live_source_direct_proof")
    source_helper=load(SOURCE_HELPER,SOURCE_HELPER_SHA,"live_source_helper_proof")
    disk=load(DISK_HELPER,DISK_HELPER_SHA,"live_disk_helper_proof")
    base=direct.load_core().load_base()
    report=json.loads(path.read_text(encoding="utf-8"))
    result=validate_completed_report(report,source_compat,source_helper,disk,base)
    need(sha(path)==expected,"completed Direct report changed during proof")
    return dict(result,path=str(path.resolve()),sha256=expected)


def prepared_namespace(live,source_compat,adapter,direct,core,base,args):
    """Reuse original Live compiler, including extra Root restoration and GN cleanup."""
    global _RUN
    _RUN=args
    live._DIRECT,live._CORE,live._ADAPTER=direct,core,adapter
    live.STAGE=STAGE
    live.completed_direct_proof=completed_direct_proof
    # The frozen Live compiler's three native substitutions stay unchanged.
    # Only its adapter factory now delegates to the already reviewed e754 namespace.
    live.load_adapter=lambda:SimpleNamespace(prepared_namespace=lambda candidate,worker,original:
        source_compat.prepared_namespace(adapter,candidate,worker,original,args.artist_protection,args.artist_protection_sha))
    namespace,edits=live.prepared_namespace(direct,core,base,args)
    namespace["__file__"]=str(Path(__file__))
    namespace["PINS"].update({LIVE:LIVE_SHA,SOURCE_DIRECT:SOURCE_DIRECT_SHA,SOURCE_HELPER:SOURCE_HELPER_SHA,
        DISK_HELPER:DISK_HELPER_SHA,Path(__file__):sha(Path(__file__)),args.direct_proof:args.direct_proof_sha})
    old_capture=namespace["capture_program"]
    def capture(*values):
        result=old_capture(*values)
        values[-1]["live_source_compatibility_adapter"]={"immutable_live":str(LIVE),"sha256":LIVE_SHA,
            "immutable_Direct_source_adapter":str(SOURCE_DIRECT),"Direct_sha256":SOURCE_DIRECT_SHA,
            "native_physics_action_collision_timing_restore_functions_changed":False,
            "prior_Direct_artist_protection":"Historical only; current strict V3 proof is separate",
            "current_artist_fullraw_integration":"Unmeasured","new_backend_deployed":False,"accepted":False}
        return result
    namespace["capture_program"]=capture
    need(namespace["restore_program"] is live.restore_dynamic
         and namespace["main"].__globals__ is namespace and namespace["main"].__globals__["capture_program"] is capture,
         "real compiled Live capture/restorer scope differs")
    return namespace,edits


def components(args):
    live=load(LIVE,LIVE_SHA,"live_frozen9646")
    source_compat=load(SOURCE_DIRECT,SOURCE_DIRECT_SHA,"live_source_e754")
    adapter=source_compat.load_current();direct=adapter.load_direct();core=direct.load_core();base=core.load_base()
    source_compat.current_artist_proof(base,direct,adapter,args.artist_protection,args.artist_protection_sha)
    return live,source_compat,adapter,direct,core,base


def pure_checks(args):
    live,source_compat,adapter,direct,core,base=components(args)
    source_helper=load(SOURCE_HELPER,SOURCE_HELPER_SHA,"live_pure_source_helper")
    disk=load(DISK_HELPER,DISK_HELPER_SHA,"live_pure_disk_helper")
    functions=("input_recipe","precision_guard","geometry_quality","graph_contract","exercise_dynamic","restore_dynamic")
    original={name:ast.dump(ast.parse(inspect.getsource(getattr(live,name))),include_attributes=False) for name in functions}
    pure_args=SimpleNamespace(**vars(args));pure_args.direct_proof=HERE/"UNMEASURED_e754_PREREQUISITE.json";pure_args.direct_proof_sha="0"*64
    namespace,edits=prepared_namespace(live,source_compat,adapter,direct,core,base,pure_args)
    need(len(edits)==3 and namespace["restore_program"] is live.restore_dynamic,"original Live three substitutions/restorer changed")
    need(all(ast.dump(ast.parse(inspect.getsource(getattr(live,name))),include_attributes=False)==original[name] for name in functions),
         "frozen native/action/physics/timing/restore function AST changed")
    # Original nine lightweight recipe/API controls; no prerequisites fabricated.
    original_controls=live.pure_checks()
    proof=direct.transition_proof(base)
    need(namespace["PINS"][base.ARTIST]==proof["current_artist_sha256"]
         and namespace["PINS"][args.artist_protection]==args.artist_protection_sha
         and namespace["load"].__name__=="compatible_load","CLI protection and source gate not in real compiled namespace")
    current=source_helper.current_manifest()
    # Explicitly synthetic in-memory validator fixture. Never written as native
    # evidence and never substitutes for the CLI hash-selected completed report.
    synthetic={k:True for k in POSITIVE}
    synthetic.update(stage=source_compat.STAGE,script_sha256=SOURCE_DIRECT_SHA,cleanup_errors=[],accepted=False,artist_saved=False,
        automatic_Original_semantic_acceptance=False,protection_before_reload={"success":True},protection_after_reload={"success":True},
        runtime52={"version":[5,2,0],"binary":"D:/Blender5.2/blender.exe"},install_input={"candidate_sha256":INPUT_SHA},
        live_author_restore=dict({k:True for k in RESTORE},errors=[]),source_before=copy.deepcopy(current),source_after=copy.deepcopy(current),
        explicit_source_compatibility={"reviewed_extra_modules":source_helper.explicit_modules(base.REPOSITORY),
            "version_only_Init":source_helper.init_version_only(base.REPOSITORY),"canonical_inventory_exact":True,
            "all_other_canonical_modules_exact":True,"old_install_validated_changed_code":False},
        current_artist_disk_protection=proof,pins={str(path):value for path,value in namespace["PINS"].items()})
    synthetic["pins"][str(SOURCE_DIRECT)]=SOURCE_DIRECT_SHA
    validate_completed_report(synthetic,source_compat,source_helper,disk,base)
    rejected=0
    changes=(lambda v:v.__setitem__("native_completed",False),lambda v:v.__setitem__("direct_main_manual_input_success",None),
        lambda v:v.__setitem__("script_sha256",LIVE_SHA),lambda v:v.__setitem__("stage",adapter.STAGE),
        lambda v:v["runtime52"].__setitem__("version",[5,1,0]),lambda v:v["live_author_restore"].__setitem__("cache_exact",False),
        lambda v:v["install_input"].__setitem__("candidate_sha256","1"*64),lambda v:v.__setitem__("automatic_Original_semantic_acceptance",True),
        lambda v:v["source_after"][next(p for p in v["source_after"] if Path(p).name=="skirt.py")].__setitem__("sha256","0"*64))
    for change in changes:
        value=copy.deepcopy(synthetic);change(value)
        try:validate_completed_report(value,source_compat,source_helper,disk,base)
        except RuntimeError:rejected+=1
        else:raise RuntimeError("unknown/incomplete prerequisite accepted")
    need(all(ast.dump(ast.parse(inspect.getsource(getattr(live,name))),include_attributes=False)==original[name] for name in functions),
         "old Live function changed during controls")
    return {"passed":True,"original_live_controls":original_controls,"native_functions_AST_exact":list(functions),
        "synthetic_completed_validator_positive":1,"prerequisite_negatives_rejected":rejected,
        "synthetic_fixture_written":False,"actual_completed_report_proved":False,"current_V3_and_compiled_namespace":True,
        "native_run":False,"accepted":False}


def arguments():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path);parser.add_argument("--direct-proof",type=Path);parser.add_argument("--direct-proof-sha")
    parser.add_argument("--artist-protection",type=Path,required=True);parser.add_argument("--artist-protection-sha",required=True)
    parser.add_argument("--case",choices=("walk","run","abrupt_stop_turn","leg_raise"),default="run")
    parser.add_argument("--frames",type=int,default=60);parser.add_argument("--manual-steps",type=int,default=10)
    parser.add_argument("--max-seconds",type=float,default=180.);parser.add_argument("--triangle-pair-limit",type=int,default=2000000)
    parser.add_argument("--body-vertex-limit",type=int,default=500000);parser.add_argument("--render",action="store_true")
    parser.add_argument("--pure-checks",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    need(args.artist_protection.is_absolute() and args.artist_protection.resolve().is_relative_to(HERE)
         and args.artist_protection.is_file() and valid_sha(args.artist_protection_sha),"explicit Root V3 receipt path/SHA required")
    args.artist_protection=args.artist_protection.resolve()
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and not args.output.exists()
             and args.output.resolve().is_relative_to(HERE) and args.output.resolve()!=HERE,"fresh private output required")
        need(args.direct_proof is not None and args.direct_proof.is_absolute() and args.direct_proof.resolve().is_relative_to(HERE)
             and args.direct_proof.is_file() and valid_sha(args.direct_proof_sha),"hash-selected completed e754 Direct prerequisite required")
        args.direct_proof=args.direct_proof.resolve()
        need(40<=args.frames<=60 and 1<=args.manual_steps<=10 and 0.<args.max_seconds<=180.
             and 0<args.triangle_pair_limit<=2000000,"unchanged bounded one-case scope only")
    return args


def main(args):
    if args.pure_checks:print(json.dumps(pure_checks(args)));return 0
    live,source_compat,adapter,direct,core,base=components(args)
    completed_direct_proof(args.direct_proof,args.direct_proof_sha,direct)
    namespace,_edits=prepared_namespace(live,source_compat,adapter,direct,core,base,args)
    return namespace["main"](args)


if __name__=="__main__":raise SystemExit(main(arguments()))
