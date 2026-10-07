"""Prepared DirectMain successor with the reviewed Node UI6 Surface pin.

Immutable1903 DirectMain/current-disk input recipe. Exactly the reviewed
ForearmTwist module and version-only Init may differ in addition to explicitly pinned
surface/worker. All other canonical inventory and SHA identities stay exact.
Old install did not validate changed code. No native/render/artist operation in
pure-checks. ROOT_FINAL_MODULE_PINS_CONFIRMED must be true before native use.
"""
import argparse
import ast
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CURRENT=HERE/"verify_direct_main_manual_input52_current_disk.py"
CURRENT_SHA="19033198def9907af52906ca8efe315593a907466d83c7f441a60d0c17a7129e"
WORKFLOW=HERE/"verify_actual_surface_workflow.py"
WORKFLOW_SHA="2e8d82bbbde00604bf3f62bc17cbcb31244ed87290e083ebb17b25f4b9216140"
FAILED=HERE/"actual_direct_main_manual_input_52_20261006_190629_958/result/input800_reproduction.json"
FAILED_SHA="d4118b560e9d7141e505b18d7fbcb707b333b04a639a1ef74f0299ffbd237243"
STAGE="DIRECT_MAIN_MANUAL_INPUT_52_NODE_UI_COMPAT"
ROOT_FINAL_MODULE_PINS_CONFIRMED=True
SOURCE_HELPER=HERE/"source_compatibility52_node_ui.py"
SOURCE_HELPER_SHA="08d36c4e561c808ed40a49e6b094085ef687a8a2e02bf5413c56ea203332507b"
PREDECESSOR=HERE/"verify_direct_main_manual_input52_source_compat.py"
PREDECESSOR_SHA="e7544206bff4824aa0df8682659cf7cece64bfcc99b51276270950b160c5c221"
NODE_FAILED=HERE/"actual_direct_main_manual_source_compat_52_20261006_194401_885/result/input800_reproduction.json"
NODE_FAILED_SHA="9d738db7d0f63850ce7fa091bd79d2dc3d20d981e95ffd1afc8b3792a2578b83"
DISK_HELPER=HERE/"artist_disk_protection52.py"
DISK_HELPER_SHA="11d925f0356a45d831ff84339e31bf691df21c257e195497fd36922907167b37"
EXTRA_MODULES={
    "forearm_twist.py":"4f159b83a2bac2aebbc9e23f03ce958da75a10728d0f21010f1178b476d66bf3",
    "__init__.py":"e8ed33bb6515cc665e2feaab4ec8bd3b55d1a32f119d50131829a166a5840aed",
}
INIT_BEFORE_SHA="f67a2febe180e03bc77e402ce44968540ac523983cde5546eff6c6b60b66d0ce"
ARTIST_RECEIPT=HERE/"artist_disk_protection_20261006_caeb.json"
ARTIST_RECEIPT_SHA="ffd821f9fc4a4d76c179bbc7d1792d9a6d7b38e86a966d649209287977685938"
ARTIST_SHA="caeb1532ebe030ef762699cd6f40eb419ed9284890b3f434108ab5277d1cf9fb"
ARTIST_BYTES=32281463
SAVE_RECEIPT=HERE.parent/"forearm_follow_20261006/apply_artist_result.json"
SAVE_RECEIPT_SHA="5c1e8fd803951b351a6963c6943b7a5e7aad3dbd3e87113c4519d14550846684"
SAVE_RECEIPT_BYTES=378886


def need(condition,message):
    if not condition:raise RuntimeError("SourceCompatibility52: "+message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    return h.hexdigest()


def load_current():
    need(sha(CURRENT)==CURRENT_SHA,"immutable1903 changed")
    spec=importlib.util.spec_from_file_location("sourcecompat_frozen1903",CURRENT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def load_helper(path,expected,name):
    need(sha(path)==expected,"frozen shared helper changed: "+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module




def typed_artist_receipt(value,base,direct):
    fields={"schema","captured_at_utc","scope","artist_path","artist_sha256","artist_bytes","artist_last_write_utc","artist_pid","artist_executable",
        "changed_by_this_capture","current_disk_equals_old_7ac_fullraw","current_disk_equals_bbfed_fullraw","live_unsaved_state","save_receipt",
        "canonical_changes","historical_migration_saved52","historical_migration_live52","accepted"}
    need(type(value) is dict and set(value)==fields,"V2 exact fieldset missing/extra")
    need(value["schema"]=="ARTIST_DISK_PROTECTION_V2" and value["scope"]=="Read-only protection of the current saved artist; not equivalence to the historical Dress QA fixture","V2 protection scope differs")
    need(type(value["artist_path"]) is str and Path(value["artist_path"]).resolve()==base.ARTIST.resolve()
         and value["artist_sha256"]==ARTIST_SHA and type(value["artist_bytes"]) is int and value["artist_bytes"]==ARTIST_BYTES,"V2 artist path/sha/typed size differs")
    need(type(value["artist_pid"]) is int and value["artist_pid"]==12696 and Path(value["artist_executable"]).resolve()==Path("D:/Blender5.2/blender.exe").resolve()
         and value["changed_by_this_capture"] is False and value["accepted"] is False,"V2 pid/runtime/read-only flags differ")
    for key in ("current_disk_equals_old_7ac_fullraw","current_disk_equals_bbfed_fullraw","live_unsaved_state"):need(value[key]=="Unmeasured","V2 unknown state promoted")
    for key in ("captured_at_utc","artist_last_write_utc"):
        need(type(value[key]) is str and datetime.fromisoformat(value[key].replace("Z","+00:00")).tzinfo is not None,"V2 timestamp untyped/untimed")
    saved=value["save_receipt"]
    expected={"path":str(SAVE_RECEIPT),"sha256":SAVE_RECEIPT_SHA,"bytes":SAVE_RECEIPT_BYTES,"status":"PASS","stage":"complete","save_result":["FINISHED"],
        "save_confirmed":True,"saved_sha256":ARTIST_SHA,"saved_bytes":ARTIST_BYTES,"blender_version":"5.2.0 LTS","original_frame":39,
        "installed_package_version":[0,76,4],"loaded_package_version":[0,76,3],"package_reloaded":False,"receipt_dirty_after":True,
        "scope":"Authorized X2 Forearm repair; selective two functions, two new owned Shape Keys and calibration metadata, not a Dress release"}
    need(type(saved) is dict and set(saved)==set(expected),"V2 save receipt schema missing/extra")
    need(type(saved["path"]) is str and Path(saved["path"]).resolve()==SAVE_RECEIPT.resolve(),"V2 SaveReceipt path differs")
    need(all(type(saved[k]) is type(v) and saved[k]==v for k,v in expected.items() if k!="path"),"V2 typed save/version/dirty/provenance differs")
    changes=value["canonical_changes"]
    need(changes=={"forearm_twist_sha256":EXTRA_MODULES["forearm_twist.py"],"init_old_sha256":INIT_BEFORE_SHA,"init_new_sha256":EXTRA_MODULES["__init__.py"],
        "init_scope":"Only bl_info.version 0.76.3 to 0.76.4; must be independently checked by byte-span reverse hash"},"V2 source compatibility scope differs")
    old=value["historical_migration_saved52"];live=value["historical_migration_live52"]
    need(set(old)=={"path","sha256","artist_sha256"} and Path(old["path"]).resolve()==direct.SAVED.resolve() and old["sha256"]==direct.SAVED_SHA and old["artist_sha256"]==direct.ARTIST_SHA,"historical saved52 reference changed")
    need(set(live)=={"path","sha256","current_live_identity_revalidated"} and Path(live["path"]).resolve()==direct.LIVE.resolve()
         and live["sha256"]==direct.LIVE_SHA and live["current_live_identity_revalidated"] is False,"historical live reference relabelled current")
    return copy.deepcopy(value)


def historical_v2_proof(base,direct,adapter):
    need(sha(ARTIST_RECEIPT)==ARTIST_RECEIPT_SHA and sha(SAVE_RECEIPT)==SAVE_RECEIPT_SHA and SAVE_RECEIPT.stat().st_size==SAVE_RECEIPT_BYTES,"V2/save evidence changed")
    value=typed_artist_receipt(json.loads(ARTIST_RECEIPT.read_text(encoding="utf-8")),base,direct)
    actual=json.loads(SAVE_RECEIPT.read_text(encoding="utf-8"));saved=actual["artist_saved"]
    need(actual["status"]=="PASS" and actual["stage"]=="complete" and actual["artist_save_confirmed"] is True and actual["artist_save_result"]==["FINISHED"]
         and actual["blender_version"]=="5.2.0 LTS" and actual["original_frame"]==39 and actual["loaded_package_version"]==[0,76,3]
         and actual["installed_addon_version"]==[0,76,4] and actual["package_reloaded"] is False
         and Path(saved["path"]).resolve()==base.ARTIST.resolve() and saved["bytes"]==ARTIST_BYTES and saved["sha256"]==ARTIST_SHA and saved["dirty_after"] is True,
         "Actual authorized save receipt does not match V2 summary")
    return {"path":str(ARTIST_RECEIPT),"sha256":ARTIST_RECEIPT_SHA,"receipt":value,"current_artist_sha256":ARTIST_SHA,
        "historical_migration":adapter.historical_migration(base,direct),"current_artist_loaded_saved_or_modified":False,
        "scope":"Historical caeb X2 save only; not current artist identity or native save proof",
        "current_identity":False,"current_artist_fullraw_vs7ac":"Unmeasured","current_live_unsaved_state":"Unmeasured","actual_save_receipt_dirty_after":True,
        "loaded_package_version":[0,76,3],"installed_package_version":[0,76,4],"full_package_reloaded":False,"Dress_release_deployed":False}






def current_artist_proof(base,direct,adapter,protection_path,protection_sha):
    disk=load_helper(DISK_HELPER,DISK_HELPER_SHA,'direct_current_disk52')
    observed=disk.proof(protection_path,protection_sha,base.ARTIST)
    observed['historical_caeb_save']=historical_v2_proof(base,direct,adapter)
    return observed


def initial_cache_program(direct,base,core):
    """Read the original cache receipt before a readonly validation can reject.

    No capture, flags, binding, evaluation or model mutation is moved. The old
    capture still obtains its complete receipts only after validation succeeds.
    """
    main,_closure,_inherited,_edits=direct.modified_program(base,core)
    old='        actual=bpy.data.objects[record["physics"]["proxy"]]; cloth=next(m for m in actual.modifiers if m.type=="CLOTH")\n'
    need(main.count(old)==1,"readonly cache initialization ABI differs")
    return main.replace(old,old+'        report["cache_before"]=same.cache_state(cloth,qa)\n',1)


def prepared_namespace(adapter,direct,core,base,protection_path,protection_sha):
    source_helper=load_helper(SOURCE_HELPER,SOURCE_HELPER_SHA,'direct_source_compat52')
    need(sha(PREDECESSOR)==PREDECESSOR_SHA and sha(NODE_FAILED)==NODE_FAILED_SHA,"immutable predecessor/node failure changed")
    if not hasattr(core,'_node_ui_original_load_base'):
        core._node_ui_original_load_base=core.load_base
        def current_base():
            loaded=core._node_ui_original_load_base()
            loaded.PINS=source_helper.current_pins(loaded.PINS,loaded.REPOSITORY)
            return loaded
        core.load_base=current_base
    # base is a newly imported private module, never the canonical or disk file.
    # Its loader and the compiled Main must see exactly the same Surface PIN.
    base.PINS=source_helper.current_pins(base.PINS,base.REPOSITORY)
    initial=current_artist_proof(base,direct,adapter,protection_path,protection_sha)
    namespace=adapter.prepared_namespace(direct,core,base)
    direct.transition_proof=lambda candidate:current_artist_proof(candidate,direct,adapter,protection_path,protection_sha)
    namespace['__file__']=str(Path(__file__))
    namespace['PINS'].update({CURRENT:CURRENT_SHA,WORKFLOW:WORKFLOW_SHA,FAILED:FAILED_SHA,Path(__file__):sha(Path(__file__)),
        SOURCE_HELPER:SOURCE_HELPER_SHA,DISK_HELPER:DISK_HELPER_SHA,PREDECESSOR:PREDECESSOR_SHA,NODE_FAILED:NODE_FAILED_SHA})
    namespace['PINS'].update(source_helper.TRANSITION_PINS)
    namespace['PINS']=source_helper.current_pins(namespace['PINS'],base.REPOSITORY)
    namespace['PINS'].update({base.REPOSITORY/'addons/character_designer'/name:value for name,value in EXTRA_MODULES.items()})
    namespace['PINS'].update({base.ARTIST:initial['current_artist_sha256'],Path(protection_path):protection_sha,
        ARTIST_RECEIPT:ARTIST_RECEIPT_SHA,SAVE_RECEIPT:SAVE_RECEIPT_SHA})
    original_load=namespace['load']
    def compatible_load(name):
        module=original_load(name)
        if name==WORKFLOW.name:
            module.motion_input_gate=source_helper.gate_namespace(vars(module),base.REPOSITORY)
            original_dependencies=module.load_dependencies
            def dependencies():
                source_helper.surface_node_layout_only(base.REPOSITORY)
                result=original_dependencies()
                need(Path(result[3].__file__).resolve()==base.SURFACE.resolve() and sha(result[3].__file__)==source_helper.SURFACE_SHA,
                     "Initial/reload canonical Surface module is not the reviewed UI6 source")
                return result
            module.load_dependencies=dependencies
        return module
    namespace['load']=compatible_load
    original_capture=namespace['capture_program']
    def capture(*values):
        result=original_capture(*values);report=values[-1]
        report['stage']=STAGE
        report['source_compatibility_adapter']={'immutable1903':str(CURRENT),'sha256':CURRENT_SHA,
            'Root_final_module_pins_confirmed':ROOT_FINAL_MODULE_PINS_CONFIRMED,'reviewed_modules':EXTRA_MODULES,
            'other_source_model_cache_ownership_gates_changed':False,'real_gate_source_helper':str(SOURCE_HELPER),
            'old_snapshot_history_not_executed':True,
            'previous_pre_input_failure':{'path':str(FAILED),'sha256':FAILED_SHA,'input_loaded':False,'author_protection_unmeasured':True},
            'node_UI6_Surface':source_helper.surface_node_layout_only(base.REPOSITORY),
            'previous_node_failure':{'path':str(NODE_FAILED),'sha256':NODE_FAILED_SHA,'native_completed':False,
                'missing_cache_receipt_cleanup_error_preserved':True},
            'cache_receipt_initialized_before_readonly_validation':True}
        report['typed_protection_adapter']['superseded070562_protection']=True
        report['typed_protection_adapter']['only_change']='Root-selected strict typedV3 current disk protection; caeb/actualX2save/070/bbfed historical only; current save, raw equivalence and live state Unmeasured'
        return result
    namespace['capture_program']=capture
    original_exercise=namespace['exercise_direct']
    def exercise(values,frozen):
        original_exercise(values,frozen);values['report']['stage']=STAGE
    namespace['exercise_direct']=exercise
    # Recompile only this one added readonly receipt. All existing statements,
    # native samples and finally cleanup remain identical to immutable281e.
    exec(compile(initial_cache_program(direct,base,core),str(Path(__file__)),'exec'),namespace)
    return namespace



def pure_checks(args):
    adapter=load_current();direct=adapter.load_direct();core=direct.load_core();base=core.load_base()
    source_helper=load_helper(SOURCE_HELPER,SOURCE_HELPER_SHA,'pure_source_compat52')
    disk=load_helper(DISK_HELPER,DISK_HELPER_SHA,'pure_disk_protection52')
    need(sha(FAILED)==FAILED_SHA,'failed1903 preserved report changed')
    source_result=source_helper.pure_checks()
    disk_result=disk.pure_checks(args.artist_protection,args.artist_protection_sha)
    old=historical_v2_proof(base,direct,adapter);receipt=old['receipt'];typed_negatives=0
    for key,val in (('artist_bytes',True),('artist_sha256',adapter.ARTIST_SHA),('changed_by_this_capture',True),
                    ('current_disk_equals_old_7ac_fullraw','True'),('live_unsaved_state','Clean')):
        altered=copy.deepcopy(receipt);altered[key]=val
        try:typed_artist_receipt(altered,base,direct)
        except RuntimeError:typed_negatives+=1
        else:raise RuntimeError('typed negative accepted')
    for key,val in (('receipt_dirty_after',False),('loaded_package_version',[0,76,4]),('save_confirmed',1),('package_reloaded',True)):
        altered=copy.deepcopy(receipt);altered['save_receipt'][key]=val
        try:typed_artist_receipt(altered,base,direct)
        except RuntimeError:typed_negatives+=1
        else:raise RuntimeError('typed save negative accepted')
    namespace=prepared_namespace(adapter,direct,core,base,args.artist_protection,args.artist_protection_sha)
    need(namespace['restore_program'] is core.restore_program and namespace['main'].__globals__ is namespace
         and namespace['main'].__globals__['load'] is namespace['load']
         and namespace['main'].__globals__['capture_program'] is namespace['capture_program'], 'compiled adapter/restorer globals differ')
    proof=direct.transition_proof(base)
    need(proof['current_artist_sha256']==disk_result['current_artist_sha256']
         and proof['current_native_save_proof']=='Unmeasured' and proof['historical_caeb_save']['current_identity'] is False,
         'after-prepared V3 current transition/historical scope differs')
    need(namespace['PINS'][base.ARTIST]==proof['current_artist_sha256']
         and namespace['PINS'][args.artist_protection]==args.artist_protection_sha
         and namespace['PINS'][SOURCE_HELPER]==SOURCE_HELPER_SHA and namespace['PINS'][DISK_HELPER]==DISK_HELPER_SHA,
         'CLI-selected protection/helper pins not in actual compiled namespace')
    need(namespace['PINS'][base.SURFACE]==base.PINS[base.SURFACE]==core.load_base().PINS[base.SURFACE]==source_helper.SURFACE_SHA
         and all(namespace['PINS'][path]==value for path,value in source_helper.TRANSITION_PINS.items()),
         'Compiled Main/base loader/proof dependency Surface PINs not synchronized')
    main,_closure,_inherited,_edits=direct.modified_program(base,core)
    actual_main=initial_cache_program(direct,base,core)
    tree=ast.parse(actual_main); old_tree=ast.parse(main)
    added=[node for node in ast.walk(tree) if isinstance(node,ast.Assign)
           and ast.get_source_segment(actual_main,node)=='report["cache_before"]=same.cache_state(cloth,qa)']
    need(len(added)==2,"cache receipt assignment count differs")
    first_try=next(node for node in tree.body[0].body if isinstance(node,ast.Try))
    index=next(i for i,node in enumerate(first_try.body) if isinstance(node,ast.Assign)
               and ast.get_source_segment(actual_main,node)=='report["cache_before"]=same.cache_state(cloth,qa)')
    need(isinstance(first_try.body[index+1],ast.Expr) and ast.get_source_segment(actual_main,first_try.body[index+1]).startswith('surface.validate('),
         'readonly cache receipt not immediately before canonical validation')
    first_try.body.pop(index)
    need(ast.dump(tree)==ast.dump(old_tree),"compiled native recipe/finally changed beyond readonly receipt")
    start=actual_main.index('        actual=bpy.data.objects[record["physics"]["proxy"]]')
    stop=actual_main.index('; report["canonical_validation_before_private_ids"]=True',start)
    snippet=actual_main[start:stop]
    from textwrap import dedent
    cloth=SimpleNamespace(type='CLOTH',show_viewport=True,show_render=True)
    baseline={'pointer':123,'is_baked':False,'info':'','is_outdated':False}
    held={}; same=SimpleNamespace(cache_state=lambda *unused:copy.deepcopy(baseline))
    def reject(*unused):raise RuntimeError('injected readonly validation failure')
    try:exec(compile(dedent(snippet),'<actual readonly pre-validation path>','exec'),
             {'bpy':SimpleNamespace(data=SimpleNamespace(objects={'actual':SimpleNamespace(modifiers=[cloth])})),
              'record':{'physics':{'proxy':'actual'}},'same':same,'qa':None,'report':held,
              'surface':SimpleNamespace(validate=reject),'source':None,'rig':None})
    except RuntimeError as error:need(str(error)=='injected readonly validation failure','wrong failure observed')
    else:raise RuntimeError('readonly validation failure swallowed')
    need(held['cache_before']==baseline and cloth.show_viewport and cloth.show_render,
         'cache receipt absent or cloth flags changed before rejection')
    assignment=next(node for node in ast.walk(old_tree) if isinstance(node,ast.Assign)
                    and ast.get_source_segment(main,node)=='args.expected_surface_sha,args.expected_worker_sha = PINS[SURFACE],PINS[WORKER]')
    native_args=SimpleNamespace()
    exec(compile(ast.Module(body=[assignment],type_ignores=[]),'<actual native expected source args>','exec'),
         {'args':native_args,'PINS':namespace['PINS'],'SURFACE':base.SURFACE,'WORKER':base.WORKER})
    need(native_args.expected_surface_sha==source_helper.SURFACE_SHA and native_args.expected_worker_sha==source_helper.WORKER_SHA,
         'native expected Surface/worker args still use historical PINs')
    # Exercise the actual nested load adapter with a bounded dependency transport;
    # it is not native import success and cannot validate a Blender module ABI.
    transport_base=core.load_base()
    dependency_surface=SimpleNamespace(__file__=str(base.SURFACE))
    dependency_result=(None,None,None,dependency_surface); calls=[]
    workflow_stub=SimpleNamespace(Path=Path,HERE=HERE,REPOSITORY=base.REPOSITORY,json=json,sha=sha,
                                  require=need,load_dependencies=lambda:(calls.append('dependencies') or dependency_result))
    transport_base.load=lambda name:(calls.append(name) or workflow_stub)
    transport=prepared_namespace(adapter,direct,core,transport_base,args.artist_protection,args.artist_protection_sha)
    loaded=transport['load'](WORKFLOW.name)
    need(loaded.load_dependencies() is dependency_result and calls==[WORKFLOW.name,'dependencies'],
         'actual load/dependencies adapter bypassed the original dependency transport')
    dependency_surface.__file__=str(base.SURFACE.with_name('UNKNOWN.py'))
    try:loaded.load_dependencies()
    except RuntimeError:pass
    else:raise RuntimeError('shadow Surface module path accepted')
    need('sealed["source_before"]' not in main and 'SEALED_ENDPOINT.open' not in main,
         'obsolete snapshot replay unexpectedly executable in Direct live recipe')
    need('"source_before":diag.source_manifest()' in main
         and 'report["source_after"]=diag.source_manifest(); report["source_disk_exact"]=report["source_before"]==report["source_after"]' in main,
         'actual full before/after source guard changed')
    need('report["input_artist_disk_exact"]=report["files_before"]==report["files_after"]' in main,
         'actual full input/artist file-state guard changed')
    audit=[]
    for line in main.splitlines():
        if any(token in line for token in ('source_manifest(', 'source_before', 'source_after', 'source_disk_exact')):audit.append(line.strip())
    compile(Path(__file__).read_text(encoding='utf-8'),str(Path(__file__)),'exec')
    return {'passed':True,'real_source_gate':source_result,'typed_current_disk':disk_result,'V2_historical_typed_positive':1,
        'V2_historical_typed_negatives_rejected':typed_negatives,'actual_saved_receipt_historical_only':True,
        'prepared_current_transition_and_compiled_namespace_pins':True,'obsolete_snapshot_history_not_executed':True,
        'Surface_PINs_base_compiled_Main_expected_args_and_loader_synchronized':True,
        'loaded_shadow_Surface_rejected':True,'cache_before_validation_failure_receipt':True,
        'compiled_Main_AST_only_one_readonly_cache_receipt_added':True,'original_restore_program_identity_kept':True,
        'inherited_source_guard_audit':audit,'native_run':False,'accepted':False}



def arguments():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path)
    parser.add_argument("--max-seconds",type=float,default=120.);parser.add_argument("--pure-checks",action="store_true")
    parser.add_argument("--artist-protection",type=Path,required=True)
    parser.add_argument("--artist-protection-sha",required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    need(args.artist_protection.is_absolute() and args.artist_protection.resolve().is_relative_to(HERE)
         and args.artist_protection.is_file() and type(args.artist_protection_sha) is str
         and len(args.artist_protection_sha)==64 and all(c in "0123456789abcdef" for c in args.artist_protection_sha),
         "Root-selected explicit complete V3 protection path/SHA required")
    args.artist_protection=args.artist_protection.resolve()
    if not args.pure_checks:
        need(ROOT_FINAL_MODULE_PINS_CONFIRMED,"Root/X2 final module hashes not yet confirmed")
        need(args.output is not None and args.output.is_absolute() and not args.output.exists() and args.output.resolve().is_relative_to(HERE)
             and args.output.resolve()!=HERE and 0.<args.max_seconds<=120.,"original fresh output/soft120 scope only")
    return args


def main(args):
    if args.pure_checks:print(json.dumps(pure_checks(args)));return 0
    adapter=load_current();direct=adapter.load_direct();core=direct.load_core();base=core.load_base()
    current_artist_proof(base,direct,adapter,args.artist_protection,args.artist_protection_sha)
    namespace=prepared_namespace(adapter,direct,core,base,args.artist_protection,args.artist_protection_sha)
    return namespace["main"](args)


if __name__=="__main__":raise SystemExit(main(arguments()))
