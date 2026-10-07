"""Private Original/Controls and Auto leg30 images with exact RenderResult cleanup.
Only SOURCE preparation. Original e106 contacts/Body12/finally remain unchanged;
four native front/side diagnostics do not accept physics, cache payload or ART.
"""
import ast, copy, inspect, json, sys
from pathlib import Path
from types import SimpleNamespace as NS
HERE=Path(__file__).resolve().parent
BASE=HERE/'verify_direct_original_leg_contact52.py'; BASE_SHA='e1063eb9dab5e943661136c5f3504ada31a7cb056b6916b6d9aef40c723fd8c9'
TOPO=HERE/'diagnose_current_dress_topology52_v2.py'; TOPO_SHA='53cacf811cb6de18e7a19decfc31b8c6a9e8ff0ae31966e0f45e37b323488f68'
TOPO_PROOF=HERE/'actual_saved_dress_topology_v2_e0b_52_20261007_103940_623_eab5149b75b542479f234316bfa8da5d/result/report.json'; TOPO_PROOF_SHA='1f6f44a99a3b602a1e5be1d2c1ea37b72a1296d2520dbec7b848835aeed2af4a'
def load_helpers():
    import hashlib, importlib.util
    modules=[]
    for path,expected in ((BASE,BASE_SHA),(TOPO,TOPO_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected: raise RuntimeError('Frozen render dependency differs')
        spec=importlib.util.spec_from_file_location('render_owned_'+path.stem,path); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); modules.append(value)
    base,topo=modules; base.need(base.sha(TOPO_PROOF)==TOPO_PROOF_SHA,'Actual targeted Image cleanup evidence differs'); proof=json.loads(TOPO_PROOF.read_text())
    base.need(proof['collection_success'] is True and proof['private_scene_disposed'] is True and proof['render_image_cleanup']['completed'] is True and proof['new_render_images_removed_exact'] is True and not proof['errors'],'Actual prior cleanup was incomplete')
    return base,topo
def safe_renderer(topo,progressive,diag,bpy,cold,report,write):
    renderer=progressive.two_view_renderer(diag)
    def render(args,final,body,bounds):
        inventory=cold.inventory(bpy); images={x.as_pointer() for x in bpy.data.images}; pointers={p for rows in inventory.values() for _,p in rows}
        topo.need(all(x.type!='RENDER_RESULT' and x.source!='VIEWER' for x in bpy.data.images),'Refuse to overwrite an existing author/viewer Image')
        states=topo.image_user_states(bpy,list(bpy.data.images),pointers); topo.need(all(r['measured'] is True for r in states),'Original Image user state Unknown')
        context=bpy.context; before_context=(context.scene.name,context.scene.frame_current,context.scene.frame_subframe,context.mode)
        receipt=report.setdefault('owned_render_windows',{}).setdefault(args.output.name,{}); receipt.update(before_inventory=inventory,before_context=before_context); write()
        try:
            result=renderer(args,final,body,bounds); receipt['native_render_result']=result; write(); return result
        finally:
            topo.cleanup_new_render_images(bpy,images,states,pointers,receipt,write)
            receipt['all_ID_inventory_exact']=cold.inventory(bpy)==inventory; receipt['after_context']=(context.scene.name,context.scene.frame_current,context.scene.frame_subframe,context.mode); write(); topo.need(receipt['all_ID_inventory_exact'] and receipt['after_context']==before_context,'Private renderer retained native IDs or changed context')
    return render
def static_views(bpy,args,cold,q,diag,renderer,rig,installed,body,meshes,row,report,write,budget):
    budget(); graph=bpy.context.evaluated_depsgraph_get(); body_mesh=diag.mesh_snapshot(body,graph)
    import hashlib
    _BASE.need(hashlib.sha256(q.pack(body_mesh['points']).tobytes()).hexdigest()==row['Body_world_sha256'],'Static render Body differs from measured same-frame input')
    before=(bpy.context.scene.name,bpy.context.scene.frame_current,bpy.context.scene.frame_subframe,bpy.context.mode)
    folder=args.output/'Manual_Controls'; folder.mkdir(); row['render']=renderer(NS(output=folder,frame=bpy.context.scene.frame_current),meshes['final3040'],body_mesh,diag.framing(rig,installed,graph)); row['render']['provenance']='Actual Manual visible pre-Cloth source after public Original/Controls; no static Cloth recalculation'
    write(); _BASE.need(row['render']['success'] is True and set(row['render']['views'])=={'front','side'} and before==(bpy.context.scene.name,bpy.context.scene.frame_current,bpy.context.scene.frame_subframe,bpy.context.mode),'Static native images/context incomplete')
def prepared_namespace():
    global _BASE
    _BASE,topo=load_helpers(); n,original,changed=_BASE.prepared_namespace(); updated=copy.deepcopy(changed)
    source=ast.unparse(updated); source=_BASE.replace_once(source,'renderer = progressive.two_view_renderer(diag)','renderer = _SAFE_RENDERER(progressive,diag,bpy,cold,report,write)')
    marker="report['static_observation'] = {'frame': same_frame, 'C_is_disabled_input': True, 'recalculated': False, 'accepted': False}"
    source=_BASE.replace_once(source,marker,marker+'\n        _STATIC_VIEWS(bpy,args,cold,q,diag,renderer,rig,installed,body,static_meshes,static_row,report,write,budget)')
    main=_BASE.replace_once(n['_MAIN_SOURCE'],"need(not args.render,'Unrendered component only: inherited renderer lacks exact owned Render Result cleanup')","need(args.render,'Four native Manual/Auto front-side diagnostics required')")
    n.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,_SAFE_RENDERER=lambda *v:safe_renderer(topo,*v),_STATIC_VIEWS=static_views); n['_EXTRA_PINS'].update({BASE:BASE_SHA,TOPO:TOPO_SHA,TOPO_PROOF:TOPO_PROOF_SHA})
    exec(compile(source+'\n'+main,str(Path(__file__).resolve()),'exec'),n); n['_MAIN_SOURCE']=main; return n,changed,source,topo
def pure_checks():
    n,old,source,topo=prepared_namespace(); n['base']=NS(); _BASE.need(all(not _BASE.missing_globals(n[k]) for k in ('main','run_motion','exercise')),'Compiled render closure incomplete')
    restored=source.replace('renderer = _SAFE_RENDERER(progressive,diag,bpy,cold,report,write)','renderer = progressive.two_view_renderer(diag)').replace('\n        _STATIC_VIEWS(bpy,args,cold,q,diag,renderer,rig,installed,body,static_meshes,static_row,report,write,budget)','')
    _BASE.need(ast.dump(ast.parse(restored).body[0])==ast.dump(old),'Original recipe/contacts/Body12/finally changed')
    topo.render_cleanup_checks()
    _BASE.need(n['restore_body_coordinates'] is n['_STOP'].restore_body_coordinates and n['main'].__globals__ is n and n['run_motion'].__globals__ is n,'Restore/PINS globals differs')
    print('SOURCE PREPARED: two reversible run additions, exact Body12/contacts, prior native cleanup and strict Image controls; no Native')
def main():
    if '--pure-checks' in sys.argv: pure_checks(); return 0
    n,_,_,_=prepared_namespace()
    try: return n['main']()
    finally: _BASE.need(all(_BASE.sha(p)==v for p,v in n['_EXTRA_PINS'].items()),'Frozen render guards changed')
if __name__=='__main__': raise SystemExit(main())
