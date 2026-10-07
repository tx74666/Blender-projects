"""SOURCE B6 only; keep actual A8/AB failure and every native cleanup gate."""
import argparse
import copy
import hashlib
import importlib.util
import json
import statistics
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
SINGLE=HERE/'verify_direct_current_motion_single52.py'
SINGLE_SHA='09c7f5b192d87e89b83d39883d384b46cfaf22335af679225ea574cb30aa9a2c'
A8=HERE/'actual_direct_quality_ab_v2_run_e0b_52_20261007_122632_660_6b2b5b7326714d428255a6051b7e8b3e/result/A8/report.json'
A8_SHA='b92dcfa6db03289e597318cb633a2980d6adea7952ee0764a6558ae81f2f1138'

def need(value,reason):
    if not value: raise RuntimeError(reason)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def timings(report):
    rows={name:sorted(r['timing'][name]*1000. for r in report['samples']) for name in ('frame_set_seconds','bulk_three_position_extraction_seconds')}
    return {name:{'count':len(v),'median_ms':statistics.median(v),'nearest_rank_p95_ms':v[(95*len(v)+99)//100-1],'maximum_ms':v[-1]} for name,v in rows.items()}

def a8_proof(path,digest):
    need(Path(path).resolve()==A8.resolve() and digest==A8_SHA and sha(path)==digest,'Exact actual A8 path/SHA required')
    a=json.loads(A8.read_text(encoding='utf8'))
    need(a['native_motion_collection_completed'] is True and a['errors']==[] and a['private_scene_disposed'] is True and a['source_files_Artist_exact'] is True and a['source_before']==a['source_after'],'A8 inner measurement/protection incomplete')
    need(len(a['samples'])==60 and [r['index'] for r in a['full_samples']]==[1,6,55,60],'A8 actual sample schedule differs')
    for r in a['full_samples']:
        p=Path(r['native_edge_quad_geometry']['path']);need(p.parent.resolve()==A8.parent.resolve() and sha(p)==r['native_edge_quad_geometry']['sha256'],'A8 native geometry file differs')
    return a

def handler_states(bpy):
    return {name:{'list_type':type(value).__module__+'.'+type(value).__qualname__,'list_id':id(value),
        'handlers':[{'module':getattr(f,'__module__',None),'qualname':getattr(f,'__qualname__',None),'id':id(f)} for f in value]}
        for name in dir(bpy.app.handlers) if isinstance((value:=getattr(bpy.app.handlers,name)),list)}

def comparison(a,b):
    expected=copy.deepcopy(a['native_defaults']);expected['profile']['settings']['quality']=6;expected['cloth_settings']['quality']=6
    need(b['native_motion_collection_completed'] is True and b['errors']==[] and b['private_scene_disposed'] is True and b['source_files_Artist_exact'] is True,'B6 inner measurement/protection incomplete')
    need(b['native_defaults']==expected and a['Body_input_baseline']==b['Body_input_baseline'] and a['author_restore']==b['author_restore'] and a['source_before']==b['source_before']==b['source_after'],'Nonquality parameter/Body/author/source difference')
    need([(r['frame'],r['native_Root_world'],r['native_left_knee_world']) for r in a['samples']]==[(r['frame'],r['native_Root_world'],r['native_left_knee_world']) for r in b['samples']],'Native time/Root/knee differs')
    rows=[];need([r['index'] for r in b['full_samples']]==[1,6,55,60],'B6 sparse schedule differs')
    for left,right in zip(a['full_samples'],b['full_samples']):
        pair=[json.loads(Path(r['native_edge_quad_geometry']['path']).read_text(encoding='utf8')) for r in (left,right)]
        need(left['frame']==right['frame'] and pair[0]['requested']==pair[1]['requested'],'Paired native requested geometry/time differs')
        exact=pair[0]['actual']['edges']==pair[1]['actual']['edges'] and pair[0]['actual']['polygons']==pair[1]['actual']['polygons']
        rows.append({'index':left['index'],'status':'measured' if exact and all(r['native_edge_quad_geometry']['quality']['status']=='measured' for r in (left,right)) else 'Unknown','native_indices_exact':exact,
            'A':left['native_edge_quad_geometry']['quality'],'B':right['native_edge_quad_geometry']['quality'],'triangles_A':left['geometry_quality'],'triangles_B':right['geometry_quality'],'accepted':False})
    return {'quality_only_parameters_and_native_input_exact':True,'timing_A':timings(a),'timing_B':timings(b),'geometry':rows,'causal_speedup_accepted':False,'GUI_FPS_accepted':False,'ART_accepted':False,'scope':'Separate-process A8/B6 observations; load/thermal/warm-up confounders remain; A8 outer cleanup failure unchanged'}

def main():
    parser=argparse.ArgumentParser(add_help=False,allow_abbrev=False);parser.add_argument('--a8-report',type=Path,required=True);parser.add_argument('--a8-report-sha',required=True);parser.add_argument('--pure-checks',action='store_true')
    split=sys.argv.index('--')+1 if '--' in sys.argv else 1;args,remaining=parser.parse_known_args(sys.argv[split:]);a=a8_proof(args.a8_report,args.a8_report_sha)
    need(sha(SINGLE)==SINGLE_SHA,'Frozen single source differs');spec=importlib.util.spec_from_file_location('b6_single',SINGLE);single=importlib.util.module_from_spec(spec);spec.loader.exec_module(single)
    parent=importlib.util.module_from_spec(spec:=importlib.util.spec_from_file_location('b6_parent',single.PARENT));spec.loader.exec_module(parent);need(sha(single.PARENT)==single.PARENT_SHA,'Frozen parent differs')
    bulk=parent.load_bulk();adapter=bulk.frozen(bulk.DEPENDENCIES,bulk.DEPENDENCIES_SHA,'b6_dependencies');dependencies,argv=adapter.dependency_arguments(sys.argv[:split]+remaining)
    tokens=argv[argv.index('--')+1:] if '--' in argv else argv[1:];need('--case' in tokens and tokens[tokens.index('--case')+1]=='run' and '--render' not in tokens,'Unrendered frozen run60 only')
    n,base,run,program=parent.prepared_namespace(bulk,dependencies,6,time.perf_counter());n['__file__']=str(Path(__file__).resolve())
    n['PINS']={**n['PINS'],SINGLE.name:SINGLE_SHA,single.PARENT.name:single.PARENT_SHA,parent.BULK.name:parent.BULK_SHA,str(A8):A8_SHA,str(parent.REFERENCE):parent.REFERENCE_SHA,**{r['native_edge_quad_geometry']['path']:r['native_edge_quad_geometry']['sha256'] for r in a['full_samples']}}
    program=program.replace("'quality_ab_candidate':True","'separate_process_B6_candidate':True",1).replace("'scope':'One fresh pipeline of same-process quality8/6 Auto run60; collision4/Air3 unchanged; no held, GUI FPS or ART acceptance'","'scope':'Fresh-process B6 run60 versus actual A8; collision4/Air3 unchanged; no GUI or causal speedup acceptance'",1);exec(compile(program,str(Path(__file__).resolve()),'exec'),n)
    if args.pure_checks:
        need(not bulk.missing_globals(n['main'].__code__,n) and not bulk.missing_globals(n['run_motion'].__code__,n) and n['restore_body_coordinates'] is base.restore_body_coordinates,'Real compiled globals/restore differs')
        b=copy.deepcopy(a);b['native_defaults']['profile']['settings']['quality']=6;b['native_defaults']['cloth_settings']['quality']=6;comparison(a,b)
        b['native_defaults']['cloth_settings']['mass']+=1.
        try: comparison(a,b)
        except RuntimeError: pass
        else: raise RuntimeError('Nonquality parameter accepted')
        print('SOURCE PREPARED: actual A8/4 hashes, compiled B6 globals/restore, comparison parameter negative PASS; no Native');return 0
    need('--threads' in sys.argv and sys.argv[sys.argv.index('--threads')+1]=='1','Actual BG threads1 required');import bpy
    output=Path(tokens[tokens.index('--output')+1]);original=sys.argv;before=handler_states(bpy);handler_objects={k:tuple(getattr(bpy.app.handlers,k)) for k in before};diagnostic={'before':before,'CPU_before':parent.cpu_snapshot(),'A_CPU_load':'Unrecorded','whole_component_completed':False,'accepted':False};result=2
    try:
        sys.argv=argv;result=n['main']()
    finally:
        sys.argv=original;diagnostic['CPU_after']=parent.cpu_snapshot();package=sys.modules.get('character_designer')
        try:
            if package is not None: package.unregister()
        except Exception as error: diagnostic['unregister_error']=repr(error)
        diagnostic['after']=handler_states(bpy);diagnostic['handler_exact']=all(tuple(getattr(bpy.app.handlers,k))==v for k,v in handler_objects.items());diagnostic['RNA_clear']=not hasattr(bpy.types.Scene,'character_designer_setup') and not hasattr(bpy.types.WindowManager,'character_designer_skirt')
        if (output/'report.json').is_file():
            try: diagnostic['comparison']=comparison(a,json.loads((output/'report.json').read_text(encoding='utf8')))
            except Exception as error: diagnostic['comparison_error']=repr(error)
        diagnostic['whole_component_completed']=result==0 and diagnostic['handler_exact'] and diagnostic['RNA_clear'] and 'unregister_error' not in diagnostic and 'comparison' in diagnostic
        if output.is_dir(): (output/'B6_comparison_and_handlers.json').write_text(json.dumps(diagnostic,allow_nan=False,indent=2),encoding='utf8')
        a8_proof(args.a8_report,args.a8_report_sha);need(sha(SINGLE)==SINGLE_SHA and sha(single.PARENT)==single.PARENT_SHA and sha(parent.BULK)==parent.BULK_SHA,'Frozen files differ on exit')
        need(diagnostic['whole_component_completed'],'B6 cleanup/comparison failed; inner observation retained, no whole-component PASS')
    return 0

if __name__=='__main__': raise SystemExit(main())
