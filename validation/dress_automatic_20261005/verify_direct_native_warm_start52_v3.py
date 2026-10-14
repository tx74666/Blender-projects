"""SOURCE_PREPARED v3: only bounded atomic report-write OSError retry.

Recursive Append, local-ID/cache refusal, high75 recipe and both finally blocks
are frozen v2 behavior. No previous attempt completed the warm experiment.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PREVIOUS=HERE/'verify_direct_native_warm_start52_v2.py'
PREVIOUS_SHA='365e5bb92061c00d2de2990ebcc6ce03880b363a713076e1b0aa3793ab3ea409'
FAILED=HERE/'actual_direct_native_warm_start_v2_52_20261008_145550_465_e1f4798dba734cd998c8e90050a4dffe/result/report.json'
FAILED_SHA='cdb858256a11ab661118b3c3e881ef1e1f62fee45739b4853be017382732866e'


def need(value,message):
    if not value: raise RuntimeError('NativeWarmStartWrite52: '+message)


def previous():
    need(hashlib.sha256(PREVIOUS.read_bytes()).hexdigest()==PREVIOUS_SHA
         and hashlib.sha256(FAILED.read_bytes()).hexdigest()==FAILED_SHA,'Frozen v2/failure changed')
    failure=json.loads(FAILED.read_text(encoding='utf-8'))
    need(failure['native_component_verified'] is False and failure['native_stages_completed'] is False
         and failure['source_files_input_Artist_exact'] is True and failure['private_scene_disposed'] is True
         and failure['errors'] and 'native_append_request' not in failure
         and 'public_install_entry' not in failure and 'input_native_preflight' not in failure
         and 'samples' not in failure,'Retain actual pre-Append atomic-write failure; no effect acceptance')
    spec=importlib.util.spec_from_file_location('warm_v2_frozen',PREVIOUS)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def prepared_namespace():
    owner=previous(); n,parent,original,changed=owner.prepared_namespace()
    n['_EXTRA_PINS'].update({PREVIOUS:PREVIOUS_SHA,FAILED:FAILED_SHA})
    return n,parent,original,changed


def namespace():
    owner=previous(); _,values,_,original=owner.namespace(); changed=copy.deepcopy(original)
    writer=next(node for node in changed.body if isinstance(node,ast.FunctionDef) and node.name=='write')
    old_writer=copy.deepcopy(writer)
    writer.body=ast.parse("""payload=json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2)
target=args.output/'report.json'; temporary=args.output/'report.json.part'
for attempt in range(5):
    try:
        temporary.write_text(payload,encoding='utf-8')
        os.replace(temporary,target)
        return
    except OSError:
        if attempt==4:
            raise
        time.sleep((0.05,0.1,0.2,0.4)[attempt])
""").body
    index=next(index for index,node in enumerate(changed.body) if isinstance(node,ast.Assign)
               and ast.unparse(node.targets[0])=='report')
    addition=ast.parse("report['prior_failed_atomic_write']={'runner':str(_WRITE_PREVIOUS),'runner_sha256':_WRITE_PREVIOUS_SHA,'report':str(_WRITE_FAILED),'report_sha256':_WRITE_FAILED_SHA,'preserved_failure':True,'acceptance_borrowed':False}").body[0]
    changed.body.insert(index+1,addition)
    for node in ast.walk(changed):
        if isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V2_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V3_52'
    # Inverse only the writer, stage and provenance additions: every other
    # generated main statement, load/ownership path and finally is identical.
    reverse=copy.deepcopy(changed)
    old_index=next(index for index,node in enumerate(reverse.body) if isinstance(node,ast.FunctionDef) and node.name=='write')
    reverse.body[old_index]=old_writer
    reverse.body=[node for node in reverse.body if not (isinstance(node,ast.Assign)
                  and ast.unparse(node.targets[0])=="report['prior_failed_atomic_write']")]
    for node in ast.walk(reverse):
        if isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V3_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V2_52'
    need(ast.dump(reverse)==ast.dump(original),'Non-write frozen v2 main behavior changed')
    values.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,prepared_namespace=prepared_namespace,
        _WRITE_PREVIOUS=PREVIOUS,_WRITE_PREVIOUS_SHA=PREVIOUS_SHA,_WRITE_FAILED=FAILED,_WRITE_FAILED_SHA=FAILED_SHA)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[changed],type_ignores=[])),str(Path(__file__).resolve()),'exec'),values)
    return owner,values,original,changed


def pure_checks():
    from types import SimpleNamespace as NS
    owner,values,original,changed=namespace(); owner.pure_checks()
    n,_,_,_=prepared_namespace(); values['base']=None
    need(not n['_MISSING_GLOBALS'](values['main']),'Real compiled v3 globals incomplete')
    writer=next(node for node in changed.body if isinstance(node,ast.FunctionDef) and node.name=='write')
    def control(write_failures=0,replace_failures=0,value=1.25):
        store={'report.json':'{"status":"old"}'}; calls=dict(write=0,replace=0,sleep=[])
        class Endpoint:
            def __init__(self,name): self.name=name
            def write_text(self,payload,encoding):
                calls['write']+=1
                if calls['write']<=write_failures: raise PermissionError('injected temporary write failure')
                need(encoding=='utf-8','Writer encoding changed'); store[self.name]=payload
        class Output:
            def __truediv__(self,name): return Endpoint(name)
        def replace(source,target):
            calls['replace']+=1
            if calls['replace']<=replace_failures: raise PermissionError('injected atomic replace failure')
            store[target.name]=store.pop(source.name)
        env=dict(json=json,args=NS(output=Output()),report=dict(value=value,status='new'),
                 os=NS(replace=replace),time=NS(sleep=lambda delay:calls['sleep'].append(delay)))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(writer)],type_ignores=[])),
                     '<actual-generated-v3-write>','exec'),env)
        error=None
        try: env['write']()
        except (OSError,ValueError) as exc: error=exc
        return store,calls,error
    for write_failures,replace_failures,count,delays in ((0,0,1,[]),(2,0,3,[.05,.1]),(0,1,2,[.05]),(0,4,5,[.05,.1,.2,.4])):
        store,calls,error=control(write_failures,replace_failures)
        need(error is None and calls['write']==count and calls['sleep']==delays
             and json.loads(store['report.json'])==dict(value=1.25,status='new'), 'Real retry/success/new JSON control failed')
    for write_failures,replace_failures in ((5,0),(0,5)):
        store,calls,error=control(write_failures,replace_failures)
        need(isinstance(error,OSError) and calls['write']==5 and calls['sleep']==[.05,.1,.2,.4]
             and sum(calls['sleep'])<1. and store['report.json']=='{"status":"old"}', 'Exhaustion ignored or old report overwritten')
    for value in (float('nan'),float('inf'),float('-inf')):
        store,calls,error=control(value=value)
        need(isinstance(error,ValueError) and calls==dict(write=0,replace=0,sleep=[])
             and store['report.json']=='{"status":"old"}', 'Nonfinite JSON retried/written')
    need(not any(isinstance(node,ast.Call) and any(word in ast.unparse(node.func) for word in
         ('unlink','remove','rmtree')) for node in ast.walk(writer)), 'Target deletion fallback appeared')
    print(json.dumps(dict(source_prepared=True,native_run=False,sole_behavior_delta='actual generated write OSError retry',
        inverse_main_AST_exact=True,max_attempts=5,total_backoff_seconds=.75,
        real_writer_pure_controls=9,exhaustion_raises=True,old_report_retained=True,nonfinite_JSON_refused=True,accepted=False)))


def main():
    _,values,_,_=namespace()
    return values['main']()


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
