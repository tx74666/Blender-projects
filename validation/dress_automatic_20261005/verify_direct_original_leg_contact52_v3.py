"""Private Original/leg30 v3: restore the pre-install native bone UI receipt.
Only QA selection recovery; v2 remains failed and unmodified. No runtime repair,
physics changes, weaker author guard, save/deploy or whole-effect acceptance.
"""
import ast, copy, hashlib, importlib.util, json, sys
from pathlib import Path
from types import SimpleNamespace as NS
HERE=Path(__file__).resolve().parent
BASE=HERE/'verify_direct_original_leg_contact52_v2.py'; BASE_SHA='54bed2926a057e759f0c2c4f137323579f99ebd31d7858f428056fec88613be5'
FAILED=HERE/'actual_direct_original_leg_contact_v2_e0b_52_20261007_133444_077_1537c94644d54278a3206415808fecb0/result/report.json'; FAILED_SHA='77f7b41bd311c7b9affda4e1d0494e4e7bd81a9806464b315b2555d57459dd9f'
def need(value,message):
    if not value: raise RuntimeError('OriginalLegSelection52: '+message)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load_base():
    need(sha(BASE)==BASE_SHA and sha(FAILED)==FAILED_SHA,'Immutable v2/source evidence differs')
    spec=importlib.util.spec_from_file_location('original_leg_render_v2',BASE); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
def native_selection(rig,cold):
    return {'active_bone':None if rig.data.bones.active is None else rig.data.bones.active.name,
            'bone_selection':cold.bone_selection(rig)}
def capture_selection(original,report,write):
    report['initial_author_bone_UI']=copy.deepcopy({k:original[k] for k in ('active_bone','bone_selection')})
    report['prior_v2_selection_failure']={'path':str(FAILED),'sha256':FAILED_SHA,'accepted':False,
        'actual_initial_and_restored_bone_names_recorded':False,'scope':'v2 compared booleans only; no inferred differing bone'}
    write()
def restore_selection(rig,original,cold,report,write):
    expected=copy.deepcopy({k:original[k] for k in ('active_bone','bone_selection')})
    entry={'scope':'Restore pre-public-install native PoseBone selection/hide and DataBone hide/active only',
           'expected':expected,'before':native_selection(rig,cold),'errors':[],'completed':False}
    report['author_bone_UI_restore']=entry; write()
    rows=expected['bone_selection']; current=entry['before']['bone_selection']
    need(type(rows) is list and len(rows)==len(current),'Native bone selection inventory differs')
    names=[r['name'] for r in rows]
    need(all(type(n) is str for n in names) and len(set(names))==len(names)
         and names==[r['name'] for r in current],'Native bone names/order unresolved')
    active=expected['active_bone']
    need(active is None or (type(active) is str and active in names and rig.data.bones.get(active) is not None),'Native active bone missing')
    for saved,actual in zip(rows,current):
        need(set(saved)==set(actual) and saved['selection_owner']==actual['selection_owner']
             and saved['unavailable_fields']==actual['unavailable_fields']
             and saved['EditBone_head_tail_sampled'] is False and actual['EditBone_head_tail_sampled'] is False
             and set(saved['fields'])==set(actual['fields']) and 'select' in saved['fields']
             and all(type(v) is bool for v in saved['fields'].values())
             and type(saved['pose_bone_hide']) is bool and type(saved['data_bone_hide']) is bool,'Native selection receipt/schema incomplete')
    def attempt(label,callback):
        try: callback()
        except Exception as exc: entry['errors'].append({'field':label,'error':repr(exc)})
    # Visibility first, then active, then selection: any native UI side effect
    # must precede the exact original flags. No mode/seek/update is introduced.
    for row in rows:
        pb=rig.pose.bones[row['name']]
        for obj,attr,value,label in ((pb,'hide',row['pose_bone_hide'],'pose_hide'),(pb.bone,'hide',row['data_bone_hide'],'data_hide')):
            if getattr(obj,attr)!=value: attempt(pb.name+'/'+label,lambda o=obj,a=attr,v=value:setattr(o,a,v))
    attempt('active_bone',lambda:setattr(rig.data.bones,'active',None if active is None else rig.data.bones.get(active)))
    for row in rows:
        pb=rig.pose.bones[row['name']]; owner=pb if hasattr(pb,'select') else pb.bone
        for attr,value in row['fields'].items():
            if getattr(owner,attr)!=value: attempt(pb.name+'/'+attr,lambda o=owner,a=attr,v=value:setattr(o,a,v))
    entry['after']=native_selection(rig,cold)
    entry['before_difference']=cold.first_difference(expected,entry['before'])
    entry['after_difference']=cold.first_difference(expected,entry['after'])
    entry['completed']=not entry['errors'] and entry['after']==expected; write()
    need(entry['completed'],'Native author bone UI readback differs; original hard failure remains')
CAPTURE_MARKER='original = cold.receipt(bpy, p, q, direct, source, rig, body)'
RESTORE_MARKER='restored = cold.receipt(bpy, p, q, direct, source, rig, body)'
CAPTURE_ADD='\n    _CAPTURE_SELECTION(original,report,write)'
RESTORE_ADD="restore('author_bone_UI',lambda:_RESTORE_SELECTION(rig,original,cold,report,write))\n        "
def prepared_namespace():
    base=load_base(); n,_,old,topo=base.prepared_namespace()
    updated=base._BASE.replace_once(old,CAPTURE_MARKER,CAPTURE_MARKER+CAPTURE_ADD)
    updated=base._BASE.replace_once(updated,RESTORE_MARKER,RESTORE_ADD+RESTORE_MARKER)
    main=base._BASE.replace_once(n['_MAIN_SOURCE'],"'CURRENT_DIRECT_ORIGINAL_LEG_CONTACT52'","'CURRENT_DIRECT_ORIGINAL_LEG_CONTACT_SELECTION_V3_52'")
    n.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,_CAPTURE_SELECTION=capture_selection,_RESTORE_SELECTION=restore_selection)
    n['_EXTRA_PINS'].update({BASE:BASE_SHA,FAILED:FAILED_SHA})
    exec(compile(updated+'\n'+main,str(Path(__file__).resolve()),'exec'),n); n['_MAIN_SOURCE']=main
    return n,old,updated,base
def pure_checks():
    n,old,updated,base=prepared_namespace(); n['base']=NS()
    need(not set().union(*(set(base._BASE.missing_globals(n[k])) for k in ('main','run_motion','exercise'))),'Real compiled global missing')
    reversed_source=updated.replace(CAPTURE_ADD,'',1).replace(RESTORE_ADD,'',1)
    need(ast.dump(ast.parse(reversed_source))==ast.dump(ast.parse(old)),'Recipe/contacts/two independent cleanup/Body12 finally changed')
    need(n['restore_body_coordinates'] is n['_STOP'].restore_body_coordinates and n['main'].__globals__ is n and n['run_motion'].__globals__ is n,'Original restore/global identity differs')
    # Use the actual frozen reader, extracted without any bpy/mathutils import.
    cold_ast=ast.parse((HERE/'verify_direct_cold_install52_v4.py').read_text(encoding='utf-8'))
    values={'need':need}; functions=[x for x in cold_ast.body if isinstance(x,ast.FunctionDef) and x.name in ('bone_selection','first_difference')]
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual-selection-readers>','exec'),values); cold=NS(**{k:values[k] for k in ('bone_selection','first_difference')})
    class Bones(dict):
        active=None
        def __iter__(self): return iter(self.values())
    bones=Bones({name:NS(name=name,hide=False) for name in ('A','B')})
    pose=Bones({name:NS(name=name,bone=bones[name],select=name=='A',hide=False,bl_rna=NS(identifier='PoseBone')) for name in bones.keys()})
    bones.active=bones['A']; rig=NS(data=NS(bones=bones),pose=NS(bones=pose)); expected=native_selection(rig,cold); report={}; writes=[]
    capture_selection(expected,report,lambda:writes.append(True)); pose['A'].select=False; pose['B'].select=True; pose['A'].hide=True; bones['B'].hide=True; bones.active=bones['B']
    restore_selection(rig,expected,cold,report,lambda:writes.append(True))
    need(native_selection(rig,cold)==expected and report['author_bone_UI_restore']['completed'] and report['author_bone_UI_restore']['before_difference'] is not None,'Real receipt restore control failed')
    bad=copy.deepcopy(expected); bad['bone_selection'][0]['fields']['select']=0
    try: restore_selection(rig,bad,cold,{},lambda:None)
    except RuntimeError: pass
    else: raise RuntimeError('Unknown typed selection allowed')
    need(native_selection(rig,cold)==expected,'Bad receipt wrote native fields')
    print('SOURCE PREPARED: real compiled globals; two inverse-AST additions; original Body12/contacts/finally identity; actual selection reader restore and unknown-type refusal. No Native.')
def main():
    if '--pure-checks' in sys.argv: pure_checks(); return 0
    n,_,_,base=prepared_namespace()
    try: return n['main']()
    finally: need(all(sha(p)==v for p,v in n['_EXTRA_PINS'].items()),'Frozen selection/source guards changed')
if __name__=='__main__': raise SystemExit(main())
