"""Private current-source public Original correction, Reset and progressive leg30.
Source-only preparation; Root runs one disposable factory5.2. No save/reopen,
strip, Dress keys, imported clip, defaults change or ART/whole-time acceptance.
"""
import ast, builtins, copy, dis, hashlib, importlib.util, inspect, json, sys
from pathlib import Path
from types import CodeType, SimpleNamespace as NS
HERE=Path(__file__).resolve().parent
PNS=HERE/'verify_plain_native_skin_model52_v4.py'; PNS_SHA='c3f59ff67196cd4cf205a2d6e0a2868df39ab7b35f99bf667c41c8f4a27d4d85'
STOP=HERE/'verify_direct_cold_stop_body_keys52.py'; STOP_SHA='7fb52720375b97d68508c0ff17b1b0b9c0fb6f696748689b0fe0f2291ca7527c'
PROG=HERE/'verify_direct_cold_progressive_pose_reset52.py'; PROG_SHA='f8e0d90cbd263baec2eecc9dc5f8f2225f3f7ea7e583c14f7644e41261764050'
def need(value,message):
    if not value: raise RuntimeError('OriginalLeg52: '+message)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path,expected,name):
    need(sha(path)==expected,'Frozen dependency differs: '+str(path)); spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
def replace_once(text,old,new):
    need(text.count(old)==1,'Unique source ABI differs: '+old[:60]); return text.replace(old,new,1)
def prepared_namespace():
    pns=load(PNS,PNS_SHA,'original_leg_pns'); stop=load(STOP,STOP_SHA,'original_leg_stop'); prog=load(PROG,PROG_SHA,'original_leg_progressive')
    original=ast.parse(inspect.getsource(stop.run_motion)).body[0]; changed=copy.deepcopy(original)
    original_prefix=inspect.getsource(pns.exercise).split('    baseline = base.authored_contract',1)[0].split('    context = bpy.context\n',1)[1]
    original_prefix='    context = bpy.context\n'+original_prefix
    original_prefix=original_prefix.replace('    installed = public_install(', '    installed = _PNS.public_install(',1)
    original_prefix=replace_once(original_prefix,'installed, actual_rig, _actual, cloth =','installed, actual_rig, c, cloth =')
    marker="    need('FINISHED' in bpy.ops.character_designer.body_original_mode('EXEC_DEFAULT', action='ORIGINAL'),"
    original_prefix=replace_once(original_prefix,marker,"    original_checkpoint=skirt_original_mode.checkpoint(context,rig,skirt_original_mode.prepare(context,rig))\n"+marker)
    prefix=inspect.cleandoc(original_prefix)
    body=inspect.cleandoc(prog.BODY); end=body.index("need(home.render.fps/home.render.fps_base")
    body=prefix+'\n'+body[end:body.index("run_phase('A')")]
    body=replace_once(body,'legs,axes,height=q.body_inputs(rig,installed)',"legs,axes,height=q.body_inputs(rig,installed)\ncorrection=source.get(skirt_original_mode.CORRECTIONS); report['correction_exact_saved']=json.loads(correction)\nneed(type(correction) is str and report['correction_exact_saved'].get('bones'),'Actual saved correction is missing')")
    setup="input_obj=bpy.data.objects[installed['physics']['surface']['roles']['INPUT_SURFACE'][0]]\nclone=input_obj.modifiers[1].target\ncolliders=[bpy.data.objects[n] for n in installed['physics']['colliders'][:-1]]\nneed(len(colliders)==3 and input_obj.modifiers[1].is_bound and c.modifiers[1].is_bound,'Fresh bound relay/three proxies required')"
    body=replace_once(body,'need(home.render.fps/home.render.fps_base',setup+'\nneed(home.render.fps/home.render.fps_base')
    body=replace_once(body,"and len(final['triangles'])==5760 and len(body_mesh['points'])<=args.body_vertex_limit", "and len(final['triangles'])==5760 and len(body_mesh['points'])==14470 and len(body_mesh['triangles'])==28624 and len(body_mesh['points'])<=args.body_vertex_limit")
    body=replace_once(body,"need(body.data.users==1 and row['input_bound'] and row['C_bound']", "need(source.get(skirt_original_mode.CORRECTIONS)==correction,'Saved correction changed during replay')\n    need(body.data.users==1 and row['input_bound'] and row['C_bound']")
    body=replace_once(body,'render=index==30','render=args.render and index==30')
    body+='''same_frame=[home.frame_current,home.frame_subframe]
static_meshes,static_row=sample('Manual_static',0,manual=True)
need([home.frame_current,home.frame_subframe]==same_frame,'Static observation sought timeline')
report['static_observation']={'frame':same_frame,'C_is_disabled_input':True,'recalculated':False,'accepted':False}
run_phase('A')
report['leg_input_response']=cold.error(endpoints[('A',1)]['input800']['points'],endpoints[('A',30)]['input800']['points'],metres)
report['complete_final_contacts']=len(contacts)==3 and [r['label'] for r in contacts]==list(_CONTACT_LABELS) and all(_ENDPOINT_ZERO(r) for r in contacts)
report['timing_scope']='Native frame_set includes handlers/depsgraph; mesh extraction/diagnostics separate, not solver-only or GUI FPS'
write(); need(report['leg_input_response']['maximum_m']>5.e-5 and report['complete_final_contacts'],'Actual leg response/final3040 contact is nonzero or Unknown')
report['native_stages_completed']=True
'''
    new_try=next(n for n in changed.body if isinstance(n,ast.Try)); new_try.body=ast.parse(body).body
    cleanup_source="try:\n    if original_checkpoint is not None and body_original_mode.active(rig):\n        need('FINISHED' in bpy.ops.character_designer.body_original_mode('EXEC_DEFAULT',action='CONTROLS'),'Original failure cleanup failed')\nexcept Exception as exc:\n    restore_errors.append({'phase':'Original_Controls','error':repr(exc)})\ntry:\n    if original_checkpoint is not None:\n        skirt_original_mode.rollback(context,original_checkpoint)\nexcept Exception as exc:\n    restore_errors.append({'phase':'Original_checkpoint','error':repr(exc)})"
    cleanup=ast.parse(cleanup_source).body
    new_try.finalbody=cleanup+new_try.finalbody
    changed.body.insert(0,ast.parse('from character_designer import skirt_original_mode, body_original_mode').body[0]); changed.body.insert(-1,ast.parse('original_checkpoint=None').body[0])
    run=ast.unparse(ast.fix_missing_locations(changed)); main=inspect.getsource(pns.main)
    main=replace_once(main,"parser.add_argument('--pure-checks', action='store_true')", "parser.add_argument('--pure-checks', action='store_true'); parser.add_argument('--render',action='store_true'); parser.add_argument('--body-vertex-limit',type=int,default=100000); parser.add_argument('--triangle-pair-limit',type=int,default=2000)")
    main=replace_once(main,'0. < args.soft_seconds <= 240.', '0. < args.soft_seconds <= 180. and 1 <= args.triangle_pair_limit <= 20000')
    main=replace_once(main,"need(args.output.is_absolute()", "need(not args.render,'Unrendered component only: inherited renderer lacks exact owned Render Result cleanup')\n    need(args.output.is_absolute()")
    main=replace_once(main,"'PRIVATE_MODEL_PNS_LIBRARY_REOPEN52'","'CURRENT_DIRECT_ORIGINAL_LEG_CONTACT52'")
    main=replace_once(main,"'timeline_seek_by_QA': False", "'timeline_seek_by_QA': True,'recipe':'One public Original .08 correction; Manual static read; Reset-Auto left leg -.55 over30; sparse final3040 contacts1/16/30','collision_accepted':False,'naturalness_accepted':False")
    main=replace_once(main,"need(all(sha(path) == value for path, value in pins.items()),", "pins.update(_EXTRA_PINS); need(all(sha(path) == value for path, value in pins.items()),")
    n=dict(vars(pns)); n.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,capture_body_coordinates=stop.capture_body_coordinates,restore_body_coordinates=stop.restore_body_coordinates,_PNS=pns,_STOP=stop,_PROG=prog,_EXTRA_PINS={PNS:PNS_SHA,STOP:STOP_SHA,PROG:PROG_SHA,**{HERE/k:v for k,v in stop.PINS.items()}},_RECIPE=prog.recipe,_TIMING=prog.timing_summary,_ENDPOINT_ZERO=prog.endpoint_zero,_CONTACT_LABELS=('A_N1','A_L16','A_L30'),smooth=prog.smooth,NS=NS)
    n.update(_MAIN_SOURCE=main,_CLEANUP_SOURCE=cleanup_source); exec(compile(run+'\n'+inspect.getsource(exercise)+'\n'+main,str(Path(__file__).resolve()),'exec'),n); return n,original,changed
def exercise(bpy,args,base,cold,p,q,direct,plain,source,rig,body,report,write,budget):
    observers=[_STOP.load(name) for name in ('validate_real_dress.py','diagnose_skin_transfer.py','verify_live_direct_cloth52.py','verify_live_direct_cloth52_disposable_fixture_v6.py','verify_live_direct_cloth52_movement_winding_collision.py','verify_live_direct_cloth52_movement_centered_collision.py','verify_live_direct_cloth52_progressive_manual.py')]
    actual_q,diag,live,movement,winding,centered,progressive=observers; actual_q.simple_rna=q.simple_rna; sys.modules['validate_real_dress']=actual_q
    run_motion.__globals__.update(base=base); run_motion(bpy,args,p,cold,actual_q,diag,live,movement,winding,centered,progressive,direct,source,rig,body,direct.skirt.read_record(source),report,write,budget)
def missing_globals(function):
    def visit(code):
        missing={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL' and i.argval not in function.__globals__ and not hasattr(builtins,i.argval)}
        return missing|set().union(*(visit(c) for c in code.co_consts if isinstance(c,CodeType)))
    return sorted(visit(function.__code__))
def cleanup_control(n,original,changed):
    calls=[]; values=dict(n,original_checkpoint='saved',body_original_mode=NS(active=lambda rig:True),bpy=NS(ops=NS(character_designer=NS(body_original_mode=lambda *a,**k:{'CANCELLED'}))),skirt_original_mode=NS(rollback=lambda *a:calls.append('rollback')),context=None,rig=None,restore_errors=[])
    exec(compile(n['_CLEANUP_SOURCE'],__file__,'exec'),values); need(calls==['rollback'] and [r['phase'] for r in values['restore_errors']]==['Original_Controls'],'Controls failure skipped checkpoint rollback')
    old_try=next(x for x in original.body if isinstance(x,ast.Try)); new_try=next(x for x in changed.body if isinstance(x,ast.Try)); need(ast.dump(ast.Module(body=new_try.finalbody[2:],type_ignores=[]))==ast.dump(ast.Module(body=old_try.finalbody,type_ignores=[])),'Original Body12 finally changed')
    need("need(not args.render," in n['_MAIN_SOURCE'] and n['_MAIN_SOURCE'].index('need(not args.render,')<n['_MAIN_SOURCE'].index('import bpy'),'Rendering not rejected before Native')
def pure_checks():
    n,original,changed=prepared_namespace(); n['base']=NS()
    need(not set().union(*(set(missing_globals(n[name])) for name in ('main','run_motion','exercise'))),'Actual compiled globals missing')
    old_try=next(x for x in original.body if isinstance(x,ast.Try)); new_try=next(x for x in changed.body if isinstance(x,ast.Try))
    cleanup_control(n,original,changed)
    need(ast.dump(ast.Module(body=original.body[:original.body.index(old_try)],type_ignores=[]))==ast.dump(ast.Module(body=changed.body[1:changed.body.index(new_try)-1],type_ignores=[])),'Original author capture changed')
    need(n['_RECIPE']('A',16)['leg']['L'][0]==-.55 and n['_RECIPE']('A',30)['hem_fraction']==0.,'Frozen leg recipe changed')
    for unsafe in ({},{'Unknown_if_incomplete':True},{'strict_Body_crossing':{'status':'measured','actual_crossing_pair_count':1}}): need(not n['_ENDPOINT_ZERO'](unsafe),'Incomplete/penetrating contact allowed')
    zero={'strict_Body_crossing':{'status':'measured','full_surface_filter':{'complete':True},'actual_crossing_pair_count':0},'unresolved_counts':dict.fromkeys(('coplanar_unresolved','degenerate_unresolved','boundary_unresolved'),0),'Unknown_if_incomplete':False,'closed3':[{'all3040':{'sampled_vertices':3040,'inside_vertices':0,'maximum_penetration_m':0.}} for _ in range(3)]}; need(n['_ENDPOINT_ZERO'](zero),'Complete zero contact rejected'); zero['closed3'][0]['all3040']['inside_vertices']=1; need(not n['_ENDPOINT_ZERO'](zero),'Actual proxy penetration accepted')
    need(not {'libraries.write','wm.open_mainfile','strip'}&{ast.unparse(c.func) for c in ast.walk(changed) if isinstance(c,ast.Call)},'Forbidden snapshot route')
    source=n['_MAIN_SOURCE']; parser_source=source[:source.index('if args.pure_checks')]
    parser_source=parser_source.replace('def main():','def parse_only():',1)+'return args\n'; values=dict(n); exec(compile(parser_source,str(PNS),'exec'),values); argv=sys.argv
    try:
        sys.argv=['qa','--output',str(HERE/'UNCREATED_CLI_ONLY'),'--artist-protection',str(HERE/'artist_disk_protection_20261007_e0b30f73fc2f.json'),'--artist-protection-sha','4d092929664f9718241afabc1ba3a3c667b600eeeb3d8a98fac0aea322ff536f','--expected-source-manifest-sha','0'*64,'--body-object','Cosha','--dress-object','Dress','--soft-seconds','180']; need(values['parse_only']().soft_seconds==180.,'Real delegated parser failed')
    finally: sys.argv=argv
    print('SOURCE PREPARED: compiled globals, Original prefix, original Body12 finally, leg30 and incomplete-contact negative controls PASS; no Native')
def main():
    n,_,_=prepared_namespace(); original_argv=sys.argv
    try:
        if '--pure-checks' in sys.argv: pure_checks(); return 0
        return n['main']()
    finally:
        sys.argv=original_argv; need(all(sha(p)==v for p,v in n['_EXTRA_PINS'].items()),'Frozen observer changed')
if __name__=='__main__': raise SystemExit(main())
