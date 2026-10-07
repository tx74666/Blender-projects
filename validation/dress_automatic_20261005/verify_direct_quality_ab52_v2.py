"""SOURCE candidate: one process, two fresh Auto pipelines, quality 8 versus 6.

No render, no default change, no imported clip, no GUI FPS or ART acceptance.
Root owns the 300 s external lease; both runs share a 240 s soft budget.
"""
import ast
import copy
import ctypes
import json
import math
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BULK = HERE / 'verify_direct_cold_motion_bulk52_v2.py'
BULK_SHA = 'dd1eec6e7d57432613894a5f0d1801926954d75424de241cf91e3fe61bd0ce4d'
REFERENCE = HERE / 'actual_direct_motion_bulk_v2_render_run_e0b_52_20261007_112155_967_036059bc72f9428cac1582b15e62eba9/result/report.json'
REFERENCE_SHA = 'e57337c99f67d827908289b48c8c92510688e6b0404c298091823d6c0638eb0e'
PROVIDER_SHA = 'e07634927c790323ffa70c19e52320ce0068fbd65e0447770ff515bea3fdd9c3'
TRANSITIONS = {
    'skirt_surface_direct.py': ('eb1ad005da9c98082b577c4dca4ab32a111ec684fa2ba27e3612b0c396205e99', PROVIDER_SHA),
    'skirt.py': ('f5d08c213d9b98d47199996b3baced92e3d7cf20fdcedc85987e0e80d676804d', '5f6baf35bad958d4235ebc4c1d935e38e168b1eb4deec0abe7fab462102ea742'),
    'dress_plain_native_skin.py': ('2508f3b94a1322f786297feec9517a3627837a1b4f770b45380a4e4c11dce3eb', '8e2477f7cb5756ee0b479d7749344cbaa41b6a838d85f3f20792240cd54e6980'),
}


def need(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def load_bulk():
    import hashlib
    import importlib.util
    need(hashlib.sha256(BULK.read_bytes()).hexdigest() == BULK_SHA, 'Frozen bulk source differs')
    spec = importlib.util.spec_from_file_location('quality_ab_frozen_bulk', BULK)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source_admission(bulk, old, current, report):
    need(bulk.sha(REFERENCE) == REFERENCE_SHA, 'Historical run evidence differs')
    reference = json.loads(REFERENCE.read_text(encoding='utf8'))
    need(reference['native_motion_collection_completed'] is True and reference['errors'] == []
         and reference['private_scene_disposed'] is True and reference['source_files_Artist_exact'] is True
         and reference['source_before'] == reference['source_after']
         and reference['cold_source_compatibility']['passed'] is True
         and reference['cold_prerequisite']['sha256'] == report['_actual_cold_sha'], 'Incomplete prior source/Cold proof')
    need(set(reference['source_before']) == set(current), 'Source inventory changed')
    changed = {}
    for key, before in reference['source_before'].items():
        now = current[key]
        need(bulk.sha(Path(key)) == now['sha256'], 'Actual current source differs')
        if before != now:
            name = Path(key).name
            need(name in TRANSITIONS and (before['sha256'], now['sha256']) == TRANSITIONS[name], 'Unknown source transition')
            changed[name] = {'before': before, 'after': now}
    need(set(changed) == set(TRANSITIONS), 'Exact three reviewed source transitions required')
    need(old == json.loads(Path(reference['cold_prerequisite']['path']).read_text(encoding='utf8'))['source_after'], 'Different actual Cold source')
    report['cold_source_compatibility'] = {'passed': True, 'reference': str(REFERENCE), 'reference_sha256': REFERENCE_SHA,
        'explicit_three_transitions': changed, 'actual_manifest_not_normalized': True,
        'scope': 'Reviewed Manual-only, public-route and unused plain-helper transitions; Auto recipe does not call these changed branches.',
        'native_or_export_acceptance': False}
    return True


def geometry_snapshot(mesh):
    return {'points_world': [list(p) for p in mesh['points']],
            'edges': [list(e) for e in mesh['edges']], 'polygons': [list(f) for f in mesh['faces']]}


def native_quality(actual, requested, metres):
    """Use exact native edges and ordered quads; never use nearest matching."""
    result = {'status': 'Unknown', 'accepted': False, 'triangle_quality_replaced': False,
        'limitation': 'Fixed-index edge/Newell quad diagnostics; not self-intersection, real flip or appearance acceptance.'}
    if actual['edges'] != requested['edges'] or actual['polygons'] != requested['polygons']:
        return dict(result, reason='Native edge/polygon index order differs')
    a, b = actual['points_world'], requested['points_world']
    if len(a) != len(b) or not a or not all(math.isfinite(v) for pts in (a,b) for p in pts for v in p):
        return dict(result, reason='Missing or nonfinite native coordinates')
    def length(p, q): return math.sqrt(sum((x-y)**2 for x,y in zip(p,q)))
    ratios, area_ratios, unresolved = [], [], []
    for index, (i,j) in enumerate(actual['edges']):
        denominator = length(b[i],b[j]); numerator = length(a[i],a[j])
        if denominator == 0. or numerator == 0.: unresolved.append({'edge':index,'vertices':[i,j],'reason':'zero native edge'})
        else: ratios.append((numerator/denominator,index,[i,j],(numerator-denominator)*metres))
    def area(points, face):
        normal = [0.,0.,0.]
        for i,j in zip(face,face[1:]+face[:1]):
            p,q = points[i],points[j]
            normal[0] += (p[1]-q[1])*(p[2]+q[2]); normal[1] += (p[2]-q[2])*(p[0]+q[0]); normal[2] += (p[0]-q[0])*(p[1]+q[1])
        return math.sqrt(sum(v*v for v in normal))*.5
    for index, face in enumerate(actual['polygons']):
        if len(face) != 4: unresolved.append({'polygon':index,'reason':'nonquad native polygon'}); continue
        denominator = area(b,face); numerator = area(a,face)
        if denominator == 0. or numerator == 0.: unresolved.append({'polygon':index,'reason':'zero native Newell area'})
        else: area_ratios.append((numerator/denominator,index,face))
    if not all(math.isfinite(row[0]) for row in ratios+area_ratios): unresolved.append({'reason':'nonfinite ratio'})
    result.update(status='measured' if not unresolved else 'Unknown', native_vertices=len(a),
        native_edges=len(actual['edges']), native_polygons=len(actual['polygons']),
        maximum_edge_ratio=max(ratios,default=None), minimum_edge_ratio=min(ratios,default=None),
        maximum_quad_area_ratio=max(area_ratios,default=None), minimum_quad_area_ratio=min(area_ratios,default=None), unresolved=unresolved)
    return result


def store_geometry(meshes, row, args, metres):
    import hashlib
    data = {'frame':row['frame'], 'actual':geometry_snapshot(meshes['final3040']),
        'requested':geometry_snapshot(meshes['requested3040']), 'metres':metres}
    path = args.output / ('native_geometry_'+str(row['index'])+'.json')
    content = json.dumps(data,allow_nan=False,separators=(',',':')).encode('utf8'); path.write_bytes(content)
    row['native_edge_quad_geometry'] = {'path':str(path),'sha256':hashlib.sha256(content).hexdigest(),
        'quality':native_quality(data['actual'],data['requested'],metres), 'same_graph_snapshot':True, 'accepted':False}


def prepared_namespace(bulk, dependencies, quality, session_start):
    expected, cold, cold_sha = dependencies
    need(expected == PROVIDER_SHA and bulk.sha(cold) == cold_sha and bulk.sha(REFERENCE)==REFERENCE_SHA, 'Current provider/actual Cold proof required')
    base = bulk.frozen(bulk.BASE,bulk.BASE_SHA,'quality_ab_frozen_stop'); run, main = bulk.programs(base)
    marker = "        tuning.apply(context, [source], mode='AUTOMATIC')"
    need(run.count(marker)==1, 'Unique fresh Auto constructor missing')
    run = run.replace(marker, marker+"\n        tuning.apply(context, [source], {'quality': _AB_QUALITY})",1)
    run = run.replace("profile['settings']['quality'] == cloth.settings.quality == 8", "profile['settings']['quality'] == cloth.settings.quality == _AB_QUALITY",1)
    marker = "            final, target = meshes['final3040'], meshes['requested3040']"
    need(run.count(marker)==1,'Full geometry observer ABI differs')
    # Write after row exists, using precisely the same native meshes already read.
    marker = "            row['native_graph_pointer'] = graph.as_pointer()"
    need(run.count(marker)==1,'Unique full row insertion missing')
    run = run.replace(marker, marker+"\n            _AB_STORE_GEOMETRY(meshes,row,args,metres)",1)
    main = main.replace('args.soft_seconds <= 150.', 'args.soft_seconds <= 240.',1).replace("'allowed_upper_seconds':150.","'allowed_upper_seconds':240.",1)
    main = main.replace("'external_max_seconds':None", "'external_max_seconds':300.",1)
    main = main.replace("time.perf_counter()-started < args.soft_seconds", "time.perf_counter()-_AB_SESSION_START < args.soft_seconds",1)
    main = main.replace("'source_prepared_only':True", "'quality_ab_candidate':True,'tested_quality':_AB_QUALITY,'speedup_causal_accepted':False",1)
    main = main.replace("'scope':'One frozen walk/run/stop60 input; default Air3; bulk Input/C/final positions and sparse full geometry/contact QA; no held tests, GUI FPS or ART acceptance',",
        "'scope':'One fresh pipeline of same-process quality8/6 Auto run60; collision4/Air3 unchanged; no held, GUI FPS or ART acceptance', '_actual_cold_sha':COLD_PROOF_SHA,")
    n = dict(vars(base)); n.update(__file__=str(Path(__file__).resolve()), PROVIDER_SHA=expected,COLD_PROOF=cold,COLD_PROOF_SHA=cold_sha,
        _BULK_POINTS=bulk.bulk_points,_BULK_MATCH=bulk.full_match,_BULK_CONTACT_COMPLETE=bulk.contact_complete,
        _BULK_PARAMETERS=bulk.parameters,_BULK_CANONICAL=bulk.canonical,_BULK_INDICES=bulk.sparse_indices,
        _BULK_SOURCE_ADMISSION=lambda old,current,report:source_admission(bulk,old,current,report),
        _BULK_BASE=bulk.BASE,_BULK_BASE_SHA=bulk.BASE_SHA,_BULK_DEPENDENCIES=bulk.DEPENDENCIES,_BULK_DEPENDENCIES_SHA=bulk.DEPENDENCIES_SHA,
        _BULK_MAP=bulk.DELTA_MAP,_BULK_MAP_SHA=bulk.DELTA_MAP_SHA,_BULK_PARENT=bulk.PARENT,_BULK_PARENT_SHA=bulk.PARENT_SHA,
        _BULK_PLAIN=base.REPO/'addons/character_designer/dress_plain_native_skin.py',_BULK_PLAIN_SHA=TRANSITIONS['dress_plain_native_skin.py'][1],
        _AB_QUALITY=quality,_AB_SESSION_START=session_start,_AB_STORE_GEOMETRY=store_geometry)
    exec(compile(run+'\n'+main,str(Path(__file__).resolve()),'exec'),n)
    return n, base, run, main


def cpu_snapshot():
    class FILETIME(ctypes.Structure): _fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
    idle,kernel,user = FILETIME(),FILETIME(),FILETIME()
    if os.name!='nt' or not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle),ctypes.byref(kernel),ctypes.byref(user)):
        return {'system_cpu':'Unmeasured','process_seconds':time.process_time(),'wall_seconds':time.perf_counter()}
    return {'idle':(idle.high<<32)+idle.low,'kernel':(kernel.high<<32)+kernel.low,'user':(user.high<<32)+user.low,
            'process_seconds':time.process_time(),'wall_seconds':time.perf_counter()}


def pure_checks(bulk, dependencies):
    for quality in (8,6):
        n,base,run,main=prepared_namespace(bulk,dependencies,quality,0.)
        need(n['run_motion'].__globals__ is n and n['main'].__globals__ is n
             and n['restore_body_coordinates'] is base.restore_body_coordinates,'Compiled globals/author restore differs')
        need(not bulk.missing_globals(n['run_motion'].__code__,n) and not bulk.missing_globals(n['main'].__code__,n),'Missing compiled globals')
    quad={'points_world':[[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,1.,0.]],'edges':[[0,1],[1,2],[2,3],[3,0]],'polygons':[[0,1,2,3]]}
    need(native_quality(quad,quad,1.)['status']=='measured','Identical native quad missing')
    bad=copy.deepcopy(quad);bad['edges'].reverse();need(native_quality(bad,quad,1.)['status']=='Unknown','Changed edge order accepted')
    bad=copy.deepcopy(quad);bad['points_world'][1]=bad['points_world'][0];need(native_quality(quad,bad,1.)['status']=='Unknown','Zero denominator accepted')
    need(native_quality(bad,quad,1.)['status']=='Unknown','Zero actual edge accepted')
    old=json.loads(dependencies[1].read_text(encoding='utf8'))['source_after']
    current={key:{'bytes':Path(key).stat().st_size,'mtime_ns':Path(key).stat().st_mtime_ns,'sha256':bulk.sha(Path(key))}
             for key in json.loads(REFERENCE.read_text(encoding='utf8'))['source_before']}
    need(source_admission(bulk,old,current,{'_actual_cold_sha':dependencies[2]}),'Current exact source admission failed')
    unknown=copy.deepcopy(current);unknown[str(HERE/'unknown.py')]={'bytes':1,'mtime_ns':1,'sha256':'0'*64}
    try: source_admission(bulk,old,unknown,{'_actual_cold_sha':dependencies[2]})
    except RuntimeError: pass
    else: raise RuntimeError('Unknown added source accepted')
    print('SOURCE PREPARED: two actual compiled namespaces/restore, fixed-index quad and changed/zero-edge controls PASS; no Native')


def main():
    bulk=load_bulk();dependency=bulk.frozen(bulk.DEPENDENCIES,bulk.DEPENDENCIES_SHA,'quality_ab_cli')
    dependencies,delegated=dependency.dependency_arguments(sys.argv)
    if '--pure-checks' in delegated: pure_checks(bulk,dependencies);return 0
    import bpy
    need('--threads' in sys.argv and sys.argv[sys.argv.index('--threads')+1]=='1','Exact one-thread BG required')
    tokens=delegated[delegated.index('--')+1:] if '--' in delegated else delegated[1:]
    need(tokens.count('--output')==1 and '--render' not in tokens and '--case' in tokens and tokens[tokens.index('--case')+1]=='run','Only unrendered frozen run60')
    need(tokens.count('--artist-protection')==tokens.count('--artist-protection-sha')==1
         and Path(tokens[tokens.index('--artist-protection')+1]).resolve()==bulk.ARTIST_RECEIPT.resolve()
         and tokens[tokens.index('--artist-protection-sha')+1]==bulk.ARTIST_RECEIPT_SHA,'Exact current e0b Artist proof required')
    root=Path(tokens[tokens.index('--output')+1]);need(root.is_absolute() and root.resolve().is_relative_to(HERE) and not root.exists(),'Fresh private AB directory required')
    need('--soft-seconds' in tokens and 0.<float(tokens[tokens.index('--soft-seconds')+1])<=240.,'Explicit total soft budget at most240')
    original=sys.argv;start=time.perf_counter();records=[];root.mkdir()
    handlers={name:tuple(value) for name in dir(bpy.app.handlers) if isinstance(value := getattr(bpy.app.handlers,name),list)}
    try:
        for label,quality in [('A8',8),('B6',6)]:
            n,base,run,program=prepared_namespace(bulk,dependencies,quality,start)
            argv=list(delegated);argv[argv.index('--output')+1]=str(root/label)
            before_cpu=cpu_snapshot();sys.argv=argv
            try: result=n['main']()
            finally:
                package=sys.modules.get('character_designer')
                if package is not None: package.unregister()
                need(all(tuple(getattr(bpy.app.handlers,k))==v for k,v in handlers.items()),'Handler inventory not restored; no next run')
                need(not hasattr(bpy.types.Scene,'character_designer_setup') and not hasattr(bpy.types.WindowManager,'character_designer_skirt'),'CD RNA remains; no next run')
            row=json.loads((root/label/'report.json').read_text(encoding='utf8'))
            records.append({'label':label,'quality':quality,'result':result,'cpu_before':before_cpu,'cpu_after':cpu_snapshot(),
                'scene_disposed':row['private_scene_disposed'],'report':str(root/label/'report.json')})
            need(result==0 and row['native_motion_collection_completed'] is True and row['errors']==[],'Incomplete actual pipeline; stop AB')
        a,b=[json.loads(Path(r['report']).read_text(encoding='utf8')) for r in records]
        expected=copy.deepcopy(a['native_defaults']);expected['profile']['settings']['quality']=6;expected['cloth_settings']['quality']=6
        need(b['native_defaults']==expected and a['Body_input_baseline']==b['Body_input_baseline'] and a['source_before']==b['source_before'],'Other native parameter/author/source input differs')
        need([(r['frame'],r['native_Root_world'],r['native_left_knee_world']) for r in a['samples']]==[(r['frame'],r['native_Root_world'],r['native_left_knee_world']) for r in b['samples']],'Native time/Root/knee inputs differ')
        comparisons=[]
        for left,right in zip(a['full_samples'],b['full_samples']):
            need(left['index']==right['index'] and left['frame']==right['frame'],'Sparse sample times differ')
            pair=[json.loads(Path(r['native_edge_quad_geometry']['path']).read_text(encoding='utf8')) for r in (left,right)]
            need(pair[0]['requested']==pair[1]['requested'],'Native requested geometry/input differs at paired time')
            exact=pair[0]['actual']['edges']==pair[1]['actual']['edges'] and pair[0]['actual']['polygons']==pair[1]['actual']['polygons']
            known=exact and all(r['native_edge_quad_geometry']['quality']['status']=='measured' for r in (left,right))
            comparisons.append({'index':left['index'],'status':'measured' if known else 'Unknown','native_edges_polygons_exact':exact,
                'A':left['native_edge_quad_geometry']['quality'],'B':right['native_edge_quad_geometry']['quality'],
                'original_triangle_quality_A':left['geometry_quality'],'original_triangle_quality_B':right['geometry_quality'],'accepted':False})
        records.append({'same_input_parameters_except_quality':True,'native_edge_quad_comparisons':comparisons,
                        'speedup_causal_accepted':False,'GUI_FPS_or_ART_accepted':False})
    finally:
        sys.argv=original
        (root/'quality_ab_summary.json').write_text(json.dumps({'records':records,'elapsed_seconds':time.perf_counter()-start,
            'accepted':False,'order':['A8','B6'],'residual_confounders':['fixed order/module and native warm-up','thermal state and external CPU load'],
            'scope':'Current-source fresh A8/B6; system CPU cumulative counters and same-process order recorded; no GUI or causal speedup claim'},allow_nan=False,indent=2),encoding='utf8')
        need(bulk.sha(BULK)==BULK_SHA and bulk.sha(REFERENCE)==REFERENCE_SHA,'Frozen evidence changed')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
