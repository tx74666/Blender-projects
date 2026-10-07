"""Private single quality8 motion; unregister CD before data-only factory disposal."""
import argparse, hashlib, importlib.util, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE / 'verify_direct_current_motion_single52.py'
PREVIOUS_SHA = '09c7f5b192d87e89b83d39883d384b46cfaf22335af679225ea574cb30aa9a2c'
PARENT = HERE / 'verify_direct_quality_ab52_v2.py'
PARENT_SHA = '3e058918cc6411a2d88458d0910d6fe7321278522b4f0628f405a0baba77b3e8'

def need(value, reason):
    if not value: raise RuntimeError(reason)

def selection(tokens):
    parser=argparse.ArgumentParser(add_help=False,allow_abbrev=False)
    parser.add_argument('--case',choices=('walk','run','abrupt_stop_turn'),default='walk')
    parser.add_argument('--pure-checks',action='store_true')
    need(sum(t.split('=',1)[0]=='--case' for t in tokens)<=1,'Duplicate case')
    return parser.parse_known_args(tokens)

def private_dispose(bpy):
    errors=[]; package=sys.modules.get('character_designer')
    try:
        if package is not None: package.unregister()
    except Exception as error: errors.append({'unregister':repr(error)})
    try:
        need('FINISHED' in bpy.ops.wm.read_homefile(use_factory_startup=True,use_empty=True),'Private factory data disposal failed')
    except Exception as error: errors.append({'factory_data':repr(error)})
    need(not errors,'Private disposal errors: '+repr(errors))

def handler_states(bpy):
    return {name:[{'module':getattr(f,'__module__',None),'qualname':getattr(f,'__qualname__',None),'id':id(f)} for f in value]
            for name in dir(bpy.app.handlers) if isinstance((value:=getattr(bpy.app.handlers,name)),list)}

def main():
    need(all(hashlib.sha256(p.read_bytes()).hexdigest()==s for p,s in ((PARENT,PARENT_SHA),(PREVIOUS,PREVIOUS_SHA))),'Frozen source differs')
    spec=importlib.util.spec_from_file_location('single_motion_parent',PARENT)
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    bulk=parent.load_bulk();adapter=bulk.frozen(bulk.DEPENDENCIES,bulk.DEPENDENCIES_SHA,'single_motion_cli')
    dependencies,delegated=adapter.dependency_arguments(sys.argv)
    split=delegated.index('--')+1 if '--' in delegated else 1
    args,remaining=selection(delegated[split:]);need('--render' not in remaining,'Unrendered single case only')
    n,base,run,program=parent.prepared_namespace(bulk,dependencies,8,time.perf_counter())
    n.update(__file__=str(Path(__file__).resolve()),_SINGLE_CASE=args.case,_SINGLE_DISPOSE=private_dispose)
    n['PINS']={**n['PINS'],PREVIOUS.name:PREVIOUS_SHA,PARENT.name:PARENT_SHA,parent.BULK.name:parent.BULK_SHA,str(parent.REFERENCE):parent.REFERENCE_SHA}
    program=program.replace("'quality_ab_candidate':True","'single_case_current_source_candidate':True",1)
    program=program.replace("'scope':'One fresh pipeline of same-process quality8/6 Auto run60; collision4/Air3 unchanged; no held, GUI FPS or ART acceptance'",
        "'scope':'Single fresh quality8/collision4/Air3 '+_SINGLE_CASE+'60; no held, render, GUI FPS or ART acceptance'",1)
    disposal='bpy.ops.wm.read_factory_settings(use_empty=True)'
    need(program.count(disposal)==1,'Unique compiled private disposal differs')
    program=program.replace(disposal,'_SINGLE_DISPOSE(bpy)',1)
    exec(compile(program,str(Path(__file__).resolve()),'exec'),n)
    if args.pure_checks:
        need(n['run_motion'].__globals__ is n and n['main'].__globals__ is n and n['restore_body_coordinates'] is base.restore_body_coordinates,'Namespace/restore differs')
        need(not bulk.missing_globals(n['run_motion'].__code__,n) and not bulk.missing_globals(n['main'].__code__,n),'Missing real compiled globals')
        need(all(selection(['--case',case])[0].case==case for case in ('walk','run','abrupt_stop_turn')) and selection([])[0].case=='walk','Actual CLI choices differ')
        print('SOURCE PREPARED: compiled globals/restore, CLI3 and one disposal replacement; no Native');return 0
    need('--threads' in sys.argv and sys.argv[sys.argv.index('--threads')+1]=='1','Launch actual BG with --threads 1')
    import bpy
    handlers={name:tuple(getattr(bpy.app.handlers,name)) for name in dir(bpy.app.handlers) if isinstance(getattr(bpy.app.handlers,name),list)}
    before=handler_states(bpy); output=Path(remaining[remaining.index('--output')+1]); original=sys.argv
    try:
        sys.argv=delegated[:split]+remaining+['--case',args.case]
        return n['main']()
    finally:
        sys.argv=original
        exact=all(tuple(getattr(bpy.app.handlers,k))==v for k,v in handlers.items())
        clear=not hasattr(bpy.types.Scene,'character_designer_setup') and not hasattr(bpy.types.WindowManager,'character_designer_skirt')
        if output.is_dir() and output.resolve().is_relative_to(HERE):
            (output/'single_handler_closure.json').write_text(json.dumps({'before':before,'after':handler_states(bpy),'handler_exact':exact,'RNA_clear':clear,'accepted':False},allow_nan=False,indent=2),encoding='utf8')
        need(exact,'Native handlers not restored')
        need(clear,'CD RNA remains')
        need(bulk.sha(PARENT)==PARENT_SHA and bulk.sha(parent.BULK)==parent.BULK_SHA and bulk.sha(PREVIOUS)==PREVIOUS_SHA,'Frozen source differs on exit')

if __name__=='__main__': raise SystemExit(main())
