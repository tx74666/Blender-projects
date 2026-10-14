"""SOURCE_PREPARED v6: unchanged native75/paired200 experiment, larger budget.

The frozen v5 actual stopped at A_41 under its shared-load 180-second soft
budget. Seed and the mid31 endpoint were measured; full75 and Manual were not
completed. This successor borrows no acceptance. Private callable-site timers
observe validation wall time; they cannot change the effect gates or artist FPS.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import math
import inspect
from pathlib import Path
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PREVIOUS=HERE/'verify_direct_native_warm_start52_v5.py'
PREVIOUS_SHA='48d6c261019994a9d6c1230a5b4cc9b76568d1ef3ee6c92818525773ff91e442'
FAILED=HERE/'actual_direct_native_warm_start_v5_52_20261008_183742_222_91453edd22c84d3db6d41658f2e063f5/result/report.json'
FAILED_SHA='a9f583b9f0b53a57a2180cae2bce1e52db9d9b492ba1d79e9d4086a01342e127'
RUNTIME=Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer')
CURRENT_TREE_PINS={
    RUNTIME/'animation_workspace.py':'598b4c62c9320091ce0ad7330f312bfa54eaaa56d5d75f25b0a0e722f53eff04',
    RUNTIME/'animation_link.py':'0488ed5b8dad40c4f406afe0888503778740a1e270c7928d568b5060de664793',
    RUNTIME/'animation_worklist.py':'7408c6c37821f5f37cf3a1244ab81f24960b8afbd1d2c6d7702357a4ca280a73',
    RUNTIME/'animation_worklist_collection.py':'802e1216689b26a1fceb01968cc7e9414422cb44c34e59fab6cfe89f92a7ba48',
    RUNTIME/'animation_worklist_ui.py':'58e4130b9bf30baef204aaa11000f33807946657d8d2a27fbf69adf8df55da86'}
_clock=time.perf_counter


def timing_initial():
    return dict(status='ObservationOnly',scope='Private validation callable sites only; inclusive times may overlap',
        artist_FPS_verified=False,complete_runtime_cost_verified=False,
        write_boundary='This artifact contains completed prior writes; its current write elapsed is Unknown until after serialization',
        entries={},unknown_records=[])


def timing_unknown(report,label,error):
    try:
        observer=report['validation_call_timing']; observer['status']='Unknown'
        if len(observer['unknown_records'])<8: observer['unknown_records'].append(dict(label=label,error=repr(error)))
        entry=observer['entries'].setdefault(label,{})
        entry['status']='Unknown'; entry['current_call_status']='Unknown'
    except Exception:
        pass  # Observation failure never replaces the real callback/cleanup.


def timing_change(report,label,begin,elapsed=None,succeeded=False):
    entries=report['validation_call_timing']['entries']
    entry=dict(entries.get(label,dict(status='Unmeasured',calls=0,measured_calls=0,raised_calls=0,
        in_flight_calls=0,total_seconds=0.,minimum_seconds=None,maximum_seconds=None)))
    for key in ('calls','measured_calls','raised_calls','in_flight_calls'):
        if type(entry[key]) is not int or entry[key]<0: raise ValueError('Unknown timing counter')
    if not math.isfinite(entry['total_seconds']) or entry['total_seconds']<0.: raise ValueError('Unknown timing total')
    if begin:
        entry['calls']+=1; entry['in_flight_calls']+=1
        entry['current_call_status']='UnknownUntilWriteCompletes' if label=='report_write' else 'InProgress'
        entry['current_elapsed_seconds']=None
    else:
        if entry['in_flight_calls']<1: raise ValueError('Unknown timing start')
        entry['in_flight_calls']-=1
        if not succeeded: entry['raised_calls']+=1
        if elapsed is None:
            entry['status']='Unknown'; entry['current_call_status']='Unknown'
        else:
            if not math.isfinite(elapsed) or elapsed<0.: raise ValueError('Unknown timing duration')
            total=entry['total_seconds']+elapsed
            if not math.isfinite(total): raise ValueError('Unknown timing accumulation')
            entry['measured_calls']+=1; entry['total_seconds']=total
            entry['minimum_seconds']=elapsed if entry['minimum_seconds'] is None else min(entry['minimum_seconds'],elapsed)
            entry['maximum_seconds']=elapsed if entry['maximum_seconds'] is None else max(entry['maximum_seconds'],elapsed)
            if entry['status']!='Unknown': entry['status']='MeasuredCompletedCalls'
            entry['current_call_status']='Returned' if succeeded else 'Raised'
            entry['current_elapsed_seconds']=elapsed
    entries[label]=entry


def timed_call(report,label,callback,*args,**kwargs):
    started=None; succeeded=False
    try: timing_change(report,label,True)
    except Exception as error: timing_unknown(report,label,error)
    try:
        started=_clock()
        if not math.isfinite(started): raise ValueError('Unknown timing clock')
    except Exception as error:
        started=None; timing_unknown(report,label,error)
    try:
        result=callback(*args,**kwargs); succeeded=True
        return result
    finally:
        elapsed=None
        try:
            ended=_clock()
            if started is not None:
                elapsed=ended-started
                if not math.isfinite(elapsed) or elapsed<0.: raise ValueError('Unknown timing clock interval')
        except Exception as error:
            elapsed=None; timing_unknown(report,label,error)
        try: timing_change(report,label,False,elapsed,succeeded)
        except Exception as error: timing_unknown(report,label,error)


def timed_bind(report,label,callback):
    try:
        def measured(*args,**kwargs): return timed_call(report,label,callback,*args,**kwargs)
        return measured
    except Exception as error:
        timing_unknown(report,label,error)
        return callback


def wrap_call(node,label):
    return ast.copy_location(ast.Call(func=ast.Name(id='_TIME_CALL',ctx=ast.Load()),
        args=[ast.Name(id='report',ctx=ast.Load()),ast.Constant(value=label),node.func,*node.args],
        keywords=node.keywords),node)


def untime(tree):
    class Undo(ast.NodeTransformer):
        def visit_Call(self,node):
            node=self.generic_visit(node)
            if isinstance(node.func,ast.Name) and node.func.id=='_TIME_CALL':
                return ast.copy_location(ast.Call(func=node.args[2],args=node.args[3:],keywords=node.keywords),node)
            return node
    tree=Undo().visit(copy.deepcopy(tree))
    for node in ast.walk(tree):
        if hasattr(node,'body') and isinstance(node.body,list):
            node.body=[item for item in node.body if not (isinstance(item,ast.Assign)
                and isinstance(item.value,ast.Call) and isinstance(item.value.func,ast.Name)
                and item.value.func.id in ('_TIME_BIND','_TIME_INIT'))]
    return tree


def instrument_motion(n,owner,original):
    changed=copy.deepcopy(original); counts={}
    class Sites(ast.NodeTransformer):
        def visit_Call(self,node):
            node=self.generic_visit(node); name=ast.unparse(node.func); label=None
            if name=='_PNS.public_install': label='install_public_boundary'
            elif name=='_FK_CAPTURE': label='FK_checkpoint_capture'
            elif name=='physics.validate_physics': label='physics_validate_private_sites'
            elif name=='bpy.ops.character_designer.body_original_mode':
                action=next(k.value.value for k in node.keywords if k.arg=='action')
                label='Original_operator_'+action
            if label:
                counts[label]=counts.get(label,0)+1
                return wrap_call(node,label)
            return node
    changed=Sites().visit(changed)
    need(counts=={'install_public_boundary':1,'Original_operator_ORIGINAL':1,'Original_operator_CONTROLS':2,
                  'FK_checkpoint_capture':1,'physics_validate_private_sites':2},'Frozen timed call sites changed')
    target=next(node for node in changed.body if isinstance(node,ast.Try))
    index=next(index for index,node in enumerate(target.body) if isinstance(node,ast.FunctionDef) and node.name=='apply_move')
    target.body.insert(index+1,ast.parse("apply_move=_TIME_BIND(report,'apply_move',apply_move)").body[0])
    need(ast.dump(untime(changed))==ast.dump(original),'Timing changed frozen motion/physics/FK/finally')
    # Private copy of the real public-FK wrapper; the actual operator stays real.
    fk=ast.parse(inspect.getsource(owner.public_fk)).body[0]; timed_fk=copy.deepcopy(fk); found=0
    for node in ast.walk(timed_fk):
        for field,value in ast.iter_fields(node):
            if isinstance(value,ast.Call) and ast.unparse(value.func)=='bpy.ops.character_designer.body_ik_fk_switch':
                setattr(node,field,wrap_call(value,'FK_actual_public_operator')); found+=1
    need(found==1 and ast.dump(untime(timed_fk))==ast.dump(fk),'Timing changed actual public-FK wrapper')
    fk_values=dict(owner.public_fk.__globals__); fk_values['_TIME_CALL']=timed_call
    exec(compile(ast.fix_missing_locations(ast.Module(body=[timed_fk],type_ignores=[])),str(Path(__file__).resolve()),'exec'),fk_values)
    n.update(_TIME_CALL=timed_call,_TIME_BIND=timed_bind,_FK_PUBLIC=fk_values['public_fk'])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[changed],type_ignores=[])),str(Path(__file__).resolve()),'exec'),n)
    return changed


def need(value,message):
    if not value: raise RuntimeError('NativeWarmStartBudget52: '+message)


def previous():
    need(hashlib.sha256(PREVIOUS.read_bytes()).hexdigest()==PREVIOUS_SHA
         and hashlib.sha256(FAILED.read_bytes()).hexdigest()==FAILED_SHA,'Frozen v5/budget failure changed')
    failure=json.loads(FAILED.read_text(encoding='utf-8'))
    need(failure['stage']=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V5_52'
         and failure['native_component_verified'] is False and failure['native_stages_completed'] is False
         and failure['accepted'] is False and failure['effect_accepted'] is False
         and len(failure['errors'])==1 and 'Owned native budget exhausted' in failure['errors'][0]['exception']
         and len(failure['samples'])==41 and failure['samples'][-1]['label']=='A_41'
         and len(failure['seed_checks'])==1 and failure['seed_checks'][0]['native800_zero'] is True
         and failure['seed_checks'][0]['final3040_zero'] is True
         and failure['owned_native_input_preflight']['completed'] is True
         and failure['input_native_preflight']['completed'] is True
         and failure['Body_FK_transition']['public_finished'] is True
         and failure['Body_FK_transition']['all_four_FK'] is True
         and failure['Body_FK_transition']['rollback']['completed'] is True
         and not failure['Body_FK_transition']['rollback']['errors']
         and all(value is True for value in failure['Body_FK_transition']['rollback']['author_fields'].values())
         and failure['private_scene_disposed'] is True and failure['source_files_input_Artist_exact'] is True
         and not failure['author_restore']['errors'] and failure['author_restore']['raw_Rest_Actions']['success'] is True
         and all(value is True for value in failure['author_restore'].values() if type(value) is bool)
         and 'paired_body_exact' not in failure,
         'Preserve actual soft-budget refusal, completed restoration and unfinished full75/Manual scope')
    spec=importlib.util.spec_from_file_location('warm_v5_frozen',PREVIOUS)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def prepared_namespace():
    owner=previous(); n,parent,original,changed=owner.prepared_namespace()
    n['_EXTRA_PINS'].update({PREVIOUS:PREVIOUS_SHA,FAILED:FAILED_SHA,**CURRENT_TREE_PINS})
    n['__file__']=str(Path(__file__).resolve())
    changed=instrument_motion(n,owner,changed)
    return n,parent,original,changed


def namespace():
    owner=previous(); _,values,_,original=owner.namespace(); changed=copy.deepcopy(original)
    bounds=[node for node in ast.walk(changed) if isinstance(node,ast.Constant)
            and type(node.value) is float and node.value==180.]
    need(len(bounds)==2,'Frozen soft default/admission shape changed')
    for node in bounds: node.value=420.
    index=next(index for index,node in enumerate(changed.body) if isinstance(node,ast.Assign)
               and ast.unparse(node.targets[0])=='report')
    changed.body.insert(index+1,ast.parse("report['prior_failed_soft_budget']={'runner':str(_BUDGET_PREVIOUS),'runner_sha256':_BUDGET_PREVIOUS_SHA,'report':str(_BUDGET_FAILED),'report_sha256':_BUDGET_FAILED_SHA,'preserved_failure':True,'prior_soft_seconds':180.,'prior_last_label':'A_41','prior_full75_completed':False,'prior_Manual_branch_completed':False,'soft_seconds':420.,'private_callable_timing_added':True,'shared_Unity_load_observation':True,'acceptance_borrowed':False}").body[0])
    changed.body.insert(index+2,ast.parse("report['validation_call_timing']=_TIME_INIT()").body[0])
    changed.body.insert(index+3,ast.parse("report['current_tree_source_preparation']={'current_tree_input_reprepared':True,'stable_source_updates':{str(path):value for path,value in _CURRENT_TREE_PINS.items()},'historical_full_manifest_sha256':'d1b8d5018910af6826b3cb1473a3f2c51fd394171fc7ba62d498b33f58c57e20','current_full_manifest_sha256':args.expected_source_manifest_sha,'old_Dress_core_pins_relaxed':False,'historical_runtime_equivalence_claimed':False,'acceptance_borrowed':False}").body[0])
    writer_index=next(index for index,node in enumerate(changed.body) if isinstance(node,ast.FunctionDef) and node.name=='write')
    changed.body.insert(writer_index+1,ast.parse("write=_TIME_BIND(report,'report_write',write)").body[0])
    for node in ast.walk(changed):
        if isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V5_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V6_52'
    reverse=untime(changed)
    reverse.body=[node for node in reverse.body if not (isinstance(node,ast.Assign)
                  and ast.unparse(node.targets[0]) in ("report['prior_failed_soft_budget']","report['current_tree_source_preparation']"))]
    for node in ast.walk(reverse):
        if isinstance(node,ast.Constant) and type(node.value) is float and node.value==420.: node.value=180.
        elif isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V6_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V5_52'
    need(ast.dump(reverse)==ast.dump(original),'Frozen non-budget main/Native guards/finally changed')
    values.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,prepared_namespace=prepared_namespace,
        _BUDGET_PREVIOUS=PREVIOUS,_BUDGET_PREVIOUS_SHA=PREVIOUS_SHA,
        _BUDGET_FAILED=FAILED,_BUDGET_FAILED_SHA=FAILED_SHA,_TIME_INIT=timing_initial,_TIME_BIND=timed_bind,
        _CURRENT_TREE_PINS=CURRENT_TREE_PINS)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[changed],type_ignores=[])),
                 str(Path(__file__).resolve()),'exec'),values)
    return owner,values,original,changed


def pure_checks():
    owner,values,original,changed=namespace(); owner.pure_checks()
    n,_,_,motion=prepared_namespace(); prior,_,_,prior_motion=owner.prepared_namespace()
    need(ast.dump(untime(motion))==ast.dump(prior_motion),'Frozen native75/200 sample motion/FK/full rollback changed')
    need(n['_EXTRA_PINS'][PREVIOUS]==PREVIOUS_SHA and n['_EXTRA_PINS'][FAILED]==FAILED_SHA
         and not n['_MISSING_GLOBALS'](values['main']),'Actual compiled closure/pins incomplete')
    need(all(hashlib.sha256(path.read_bytes()).hexdigest()==value for path,value in CURRENT_TREE_PINS.items()),
         'Stable current-tree input pin changed')
    add=next(node for node in changed.body if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)
             and ast.unparse(node.value.func)=='parser.add_argument'
             and node.value.args[0].value=='--soft-seconds')
    need(next(k.value.value for k in add.value.keywords if k.arg=='default')==420.,'Actual CLI soft default differs')
    admission=next(node.value.args[0] for node in changed.body if isinstance(node,ast.Expr)
                   and isinstance(node.value,ast.Call) and ast.unparse(node.value.func)=='need'
                   and 'args.soft_seconds' in ast.unparse(node.value.args[0]))
    from types import SimpleNamespace as NS
    predicate=compile(ast.Expression(body=admission),'<real-v6-admission>','eval')
    def allowed(value):
        return eval(predicate,{},dict(args=NS(soft_seconds=value,expected_source_manifest_sha='0'*64)))
    need(allowed(420.) and allowed(180.) and not any(allowed(value) for value in (0.,-1.,420.001,float('inf'),float('nan'))),
         'Actual soft-bound rejection controls failed')
    print(json.dumps(dict(source_prepared=True,native_run=False,soft_seconds=420.,hard_seconds_in_launcher=480,
        actual_admission_rejection_controls=5,stage_budget_provenance_and_private_timing_inverse_AST_exact=True,
        native75_paired200_endpoint_order_public_FK_full_rollback_unchanged=True,
        private_callable_timing_added=True,prior_full75_and_Manual_unfinished=True,acceptance_borrowed=False,accepted=False)))
    timing_pure_checks()


def timing_pure_checks():
    tree=ast.parse(Path(__file__).read_text(encoding='utf-8'))
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in
              ('timing_initial','timing_unknown','timing_change','timed_call','timed_bind')]
    ticks=iter((10.,10.25)); env=dict(math=math,_clock=lambda:next(ticks))
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual-private-timing>','exec'),env)
    report={'validation_call_timing':env['timing_initial']()}; identity=object(); calls=[]
    result=env['timed_bind'](report,'control',lambda value:calls.append(value) or identity)(identity)
    need(result is identity and calls==[identity] and report['validation_call_timing']['entries']['control']['total_seconds']==.25,
         'Timer changed return/argument identity or real callback count')
    faults=0
    for kind in ('start_clock','end_clock','stats_begin','stats_end'):
        report={'validation_call_timing':env['timing_initial']()}; calls=[]; cleanup=[]
        clock_calls=[]; update=env['timing_change']; clock=env['_clock']
        def broken_clock():
            clock_calls.append(True)
            if kind=='start_clock' and len(clock_calls)==1 or kind=='end_clock' and len(clock_calls)==2:
                raise RuntimeError('injected clock failure')
            return 1.+len(clock_calls)
        def broken_stats(*args):
            if kind=='stats_begin' and args[2] or kind=='stats_end' and not args[2]:
                raise RuntimeError('injected stats failure')
            return update(*args)
        env['_clock']=broken_clock; env['timing_change']=broken_stats
        try:
            try: result=env['timed_call'](report,'fault',lambda:calls.append(True) or identity)
            finally: cleanup.append(True)
            need(result is identity and calls==[True] and cleanup==[True]
                 and report['validation_call_timing']['status']=='Unknown','Timer fault skipped real callback/finally or retained known observation')
            error=RuntimeError('original callback failure'); calls.clear(); cleanup.clear(); clock_calls.clear()
            def failing_callback(): calls.append(True); raise error
            try:
                try: env['timed_call'](report,'error',failing_callback)
                finally: cleanup.append(True)
            except RuntimeError as actual: need(actual is error,'Timer replaced the original exception identity')
            else: need(False,'Timer swallowed original callback exception')
            need(calls==[True] and cleanup==[True],'Timer fault skipped failing callback/finally')
            faults+=1
        finally: env['_clock']=clock; env['timing_change']=update
    # The serialized final-write view cannot contain its own completion time.
    snapshots=[]; report={'validation_call_timing':env['timing_initial']()}; ticks=iter((1.,1.5,2.,2.75));env['_clock']=lambda:next(ticks)
    callback=lambda:snapshots.append(copy.deepcopy(report))
    for _ in range(2): env['timed_call'](report,'report_write',callback)
    last=snapshots[-1]['validation_call_timing']['entries']['report_write']
    need(last['calls']==2 and last['measured_calls']==1 and last['in_flight_calls']==1
         and last['current_elapsed_seconds'] is None and last['current_call_status']=='UnknownUntilWriteCompletes'
         and last['total_seconds']==.5 and report['validation_call_timing']['entries']['report_write']['total_seconds']==1.25,
         'Serialized final write falsely claimed its own completed duration')
    owner,values,_,_=namespace(); n,_,_,motion=prepared_namespace(); _,_,_,frozen=owner.prepared_namespace()
    n['base']=None  # The unchanged real exercise binds this reader before run_motion.
    need(ast.dump(untime(motion))==ast.dump(frozen) and not n['_MISSING_GLOBALS'](n['run_motion'])
         and not n['_MISSING_GLOBALS'](values['main']), 'Timed actual closures/physics/full finally changed')
    print(json.dumps(dict(source_prepared=True,native_run=False,real_timing_callback_identity_passed=True,
        clock_and_stats_fault_controls=faults,original_exception_identity_and_cleanup_preserved=True,
        serialized_last_write_current_elapsed_Unknown=True,private_call_sites_only=True,
        motion_and_public_FK_and_main_inverse_AST_exact=True,artist_FPS_verified=False,accepted=False)))


def main():
    _,values,_,_=namespace()
    return values['main']()


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    elif '--timing-pure-checks' in sys.argv: timing_pure_checks()
    else: raise SystemExit(main())
