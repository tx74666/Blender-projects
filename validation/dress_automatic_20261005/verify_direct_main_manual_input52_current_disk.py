"""Prepared only: immutable281e DirectMain52 with CURRENT disk-byte protection.

Only immutable7ac QA input is loaded. The artist is never opened, modified or
saved. The new070562 receipt protects current bytes; it proves neither save UI,
actor, unsaved state nor raw identity with oldbbfed/7ac. Historical saved52/live52
retain their original schema/hash/bbfed provenance. Native5.2, source/raw/cache,
ownership, Action and restoration gates are unchanged from immutable281e.
"""
import argparse
import ast
import copy
from datetime import datetime
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DIRECT=HERE/"verify_direct_main_manual_input52.py"
DIRECT_SHA="281e9d90ca1c2896c7e07f53e43ee34be57b48960eb57977b630bfebde7192a3"
CURRENT=HERE/"artist_disk_protection_20261006_070562.json"
CURRENT_SHA="ff2f0463613d8f98d827be1d0b1a03581d444331f1ffd6d20b41467ff661a597"
ARTIST_SHA="070562f905ecbd8111e2e622213f05738b68b12186d5c16bd1c62226581df5e0"
ARTIST_BYTES=32267743
STAGE="DIRECT_MAIN_MANUAL_INPUT_52_CURRENT_DISK"
_DIRECT=None


def need(condition,message):
    if not condition:raise RuntimeError("CurrentDisk52: "+message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    return h.hexdigest()


def load_direct():
    need(sha(DIRECT)==DIRECT_SHA,"immutable281e changed")
    spec=importlib.util.spec_from_file_location("currentdisk_frozen281e",DIRECT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def typed_receipt(value,base,direct):
    fields={"schema","captured_at_utc","scope","artist_path","artist_sha256","artist_bytes","artist_last_write_utc","stable_double_read",
        "artist_pid","artist_executable","artist_process_is_background","changed_by_this_capture","save_actor","save_ui_success","live_unsaved_state",
        "current_disk_equals_old_7ac_fullraw","current_disk_equals_bbfed_fullraw","x2_report","historical_migration_saved52","historical_migration_live52","accepted"}
    need(type(value) is dict and set(value)==fields,"exact current protection schema missing/extra")
    need(value["schema"]=="ARTIST_DISK_PROTECTION_V1" and value["scope"]=="Read-only current disk protection only; no scene load, validation, save, or repair","wrong disk-only scope")
    need(type(value["artist_path"]) is str and Path(value["artist_path"]).resolve()==base.ARTIST.resolve()
         and type(value["artist_sha256"]) is str and value["artist_sha256"]==ARTIST_SHA
         and type(value["artist_bytes"]) is int and value["artist_bytes"]==ARTIST_BYTES,"exact current path/bytes/SHA typed content differs")
    need(value["stable_double_read"] is True and value["changed_by_this_capture"] is False
         and value["artist_process_is_background"] is False and value["accepted"] is False,"disk stability/read-only flags differ")
    need(type(value["artist_pid"]) is int and value["artist_pid"]==12696 and type(value["artist_executable"]) is str
         and Path(value["artist_executable"]).resolve()==Path("D:/Blender5.2/blender.exe").resolve(),"typed5.2 artist identity differs")
    for field in ("captured_at_utc","artist_last_write_utc"):
        need(type(value[field]) is str,"timestamp not primitive string")
        stamp=datetime.fromisoformat(value[field].replace("Z","+00:00"));need(stamp.tzinfo is not None,"timestamp timezone missing")
    need(value["save_actor"]==value["save_ui_success"]=="Unrecorded"
         and value["live_unsaved_state"]==value["current_disk_equals_old_7ac_fullraw"]==value["current_disk_equals_bbfed_fullraw"]=="Unmeasured","unknown save/raw/live status promoted")
    need(value["x2_report"]=="X2 reports no artist overwrite; source and scope of the intervening save remain unrecorded","X2 provenance altered")
    saved,live=value["historical_migration_saved52"],value["historical_migration_live52"]
    need(type(saved) is dict and set(saved)=={"path","sha256","artist_sha256"} and type(live) is dict
         and set(live)=={"path","sha256","current_live_identity_revalidated"},"historical references missing/extra")
    need(type(saved["path"]) is str and Path(saved["path"]).resolve()==direct.SAVED.resolve()
         and saved["sha256"]==direct.SAVED_SHA and saved["artist_sha256"]==direct.ARTIST_SHA
         and type(live["path"]) is str and Path(live["path"]).resolve()==direct.LIVE.resolve()
         and live["sha256"]==direct.LIVE_SHA and live["current_live_identity_revalidated"] is False,"historical migration falsely relabelled current")
    return copy.deepcopy(value)


def historical_migration(base,direct):
    # Keep all281e saved/live type/schema/content gates. Only its final comparison
    # of CURRENT artist bytes to historicalbbfed is replaced by a historical label.
    need(sha(DIRECT)==DIRECT_SHA,"historical pinned281e changed")
    text=DIRECT.read_text(encoding="utf-8")
    nodes=[node for node in ast.parse(text).body if isinstance(node,ast.FunctionDef) and node.name=="transition_proof"]
    need(len(nodes)==1,"historical source function absent/duplicate")
    source=ast.get_source_segment(text,nodes[0])+"\n"
    old='''    need(base.ARTIST.stat().st_size == ARTIST_BYTES and sha(base.ARTIST) == ARTIST_SHA,
         "current artist differs from the final X2 saved bytes")
'''
    need(source.count(old)==1 and source.count('"current_artist_sha256": ARTIST_SHA')==1,"frozen historical proof ABI differs")
    source=source.replace(old,"",1).replace("def transition_proof(base):","def historical_transition_proof(base):",1)
    source=source.replace('"current_artist_sha256": ARTIST_SHA','"historical_saved_artist_sha256": ARTIST_SHA',1)
    namespace=dict(vars(direct));exec(compile(source,str(Path(__file__)),"exec"),namespace)
    result=namespace["historical_transition_proof"](base)
    result.update(current_artist_UI_save_revalidated=False,current_live_identity_revalidated=False,
        scope="Historical X2 saved52/live52 migration evidence only. Originalbbfed schema and bytes provenance; no claim about current070562 scene content.")
    return result


def protection_proof(base,direct):
    need(sha(CURRENT)==CURRENT_SHA,"current Root disk receipt changed")
    receipt=typed_receipt(json.loads(CURRENT.read_text(encoding="utf-8")),base,direct)
    need(base.ARTIST.stat().st_size==ARTIST_BYTES and sha(base.ARTIST)==ARTIST_SHA,"current artist protected bytes changed")
    return {"path":str(CURRENT),"sha256":CURRENT_SHA,"receipt":receipt,"current_artist_sha256":ARTIST_SHA,
        "current_artist_loaded_saved_or_modified":False,"current_artist_fullraw": "Unmeasured",
        "current_artist_unsaved_state":"Unmeasured","current_save_UI_success":"Unrecorded","current_save_actor":"Unrecorded",
        "historical_migration":historical_migration(base,direct)}


def prepared_namespace(direct,core,base):
    # All changes are confined to this private module/compiled QA namespace.
    # The original disk source and original saved/live receipts are immutable.
    direct._CORE=core
    direct.STAGE=STAGE
    direct.transition_proof=lambda candidate:protection_proof(candidate,direct)
    namespace=direct.prepared_namespace(core,base)
    namespace["__file__"]=str(Path(__file__))
    namespace["PINS"][base.ARTIST]=ARTIST_SHA
    namespace["PINS"].update({DIRECT:DIRECT_SHA,CURRENT:CURRENT_SHA,Path(__file__):sha(Path(__file__))})
    original_capture=namespace["capture_program"]
    def capture(*values):
        result=original_capture(*values);report=values[-1]
        report["current_artist_disk_protection"]=report.pop("X2_typed_artist_protection")
        report["protected_artist_equals_loaded7ac_fullraw"]="Unmeasured"
        report["typed_protection_adapter"]={"immutable281e":str(DIRECT),"sha256":DIRECT_SHA,"newstage":STAGE,
            "only_change":"Historicalbbfed current-disk comparison replaced by exacttyped070562 disk-byte protection; no save/content permission inferred",
            "other_source_raw_cache_native_ownership_guards_changed":False}
        return result
    namespace["capture_program"]=capture
    return namespace


def pure_checks():
    direct=load_direct();core=direct.load_core();base=core.load_base()
    receipt=json.loads(CURRENT.read_text(encoding="utf-8"));proof=protection_proof(base,direct);typed_receipt(receipt,base,direct)
    rejected=0
    changes=(lambda v:v.__setitem__("artist_bytes",True),lambda v:v.__setitem__("artist_sha256",direct.ARTIST_SHA),
        lambda v:v.__setitem__("artist_path",str(base.ARTIST.parent/"Other.blend")),lambda v:v.__setitem__("stable_double_read",False),
        lambda v:v.__setitem__("artist_process_is_background",True),lambda v:v.__setitem__("save_actor","Known"),
        lambda v:v.__setitem__("live_unsaved_state","Saved"),lambda v:v.__setitem__("artist_pid",True),
        lambda v:v["historical_migration_saved52"].__setitem__("artist_sha256",ARTIST_SHA),
        lambda v:v["historical_migration_live52"].__setitem__("current_live_identity_revalidated",True),
        lambda v:v.__delitem__("accepted"),lambda v:v.__setitem__("new_claim",True))
    for change in changes:
        wrong=copy.deepcopy(receipt);change(wrong)
        try:typed_receipt(wrong,base,direct)
        except (RuntimeError,ValueError,TypeError):rejected+=1
        else:raise RuntimeError("negative typed receipt accepted")
    namespace=prepared_namespace(direct,core,base)
    rebound=direct.transition_proof(base)
    need(rebound["current_artist_sha256"]==ARTIST_SHA and rebound["historical_migration"]["historical_saved_artist_sha256"]==direct.ARTIST_SHA,
         "installed capture transition cannot re-enter pinned historical source")
    need(namespace["PINS"][base.ARTIST]==ARTIST_SHA and namespace["PINS"][DIRECT]==DIRECT_SHA
         and namespace["PINS"][CURRENT]==CURRENT_SHA and namespace["restore_program"] is core.restore_program,"pins/restoration identity changed")
    need(namespace["main"].__globals__ is namespace and namespace["main"].__globals__["capture_program"] is namespace["capture_program"],"compiled capture global not adapter")
    need(core.BASE_SHA=="50e508ef3e9ee7adb2d03086c6aa0536f558eb3f2359bf2a645189164cb72a56","basepin drift")
    compile(Path(__file__).read_text(encoding="utf-8"),str(Path(__file__)),"exec")
    return {"passed":True,"typed_positive":1,"typed_negatives_rejected":rejected,"historical_schema_kept":bool(proof["historical_migration"]),
        "compiled_pins_capture_restoration":True,"installed_transition_reentry":True,"native_run":False,"current_disk_only":True,"save_UI_actor_raw_unsaved":"Unrecorded/Unmeasured","accepted":False}


def arguments():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path);parser.add_argument("--max-seconds",type=float,default=120.)
    parser.add_argument("--pure-checks",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and not args.output.exists() and args.output.resolve().is_relative_to(HERE)
             and args.output.resolve()!=HERE,"fresh private Validation output only")
        need(0.<args.max_seconds<=120.,"original soft120/external180 only")
    return args


def main(args):
    global _DIRECT
    if args.pure_checks:print(json.dumps(pure_checks()));return 0
    _DIRECT=load_direct();core=_DIRECT.load_core();base=core.load_base();protection_proof(base,_DIRECT)
    namespace=prepared_namespace(_DIRECT,core,base)
    return namespace["main"](args)


if __name__=="__main__":raise SystemExit(main(arguments()))
