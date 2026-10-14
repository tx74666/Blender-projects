"""SOURCE_PREPARED v2: recursive native Append of the same fixed private Scene.

Frozen v1 recipe, seed, physical/author gates and both finally blocks remain.
Only local actual IDs may advance; unused Library metadata is evidenced, never
whitelisted by path. No Artist load, make_local, cache repair or public hookup.
"""
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PREVIOUS = HERE/'verify_direct_native_warm_start52_v1.py'
PREVIOUS_SHA = '5670497b6618ef093e6db1fd50d6652b4d78dc1bfff0901465875870ccf1d724'
FAILED = HERE/'actual_direct_native_warm_start_v1_52_20261008_144100_545_ec5cca21dc444bbd9e93af689dca1711/result/report.json'
FAILED_SHA = '3c29bda77ca6b4a56b580a53ccc726b9ef43932fea4dcbf3e28352b685757c5c'


def need(value, message):
    if not value:
        raise RuntimeError('NativeWarmStartAppend52: '+message)


def previous():
    need(hashlib.sha256(PREVIOUS.read_bytes()).hexdigest()==PREVIOUS_SHA
         and hashlib.sha256(FAILED.read_bytes()).hexdigest()==FAILED_SHA, 'Frozen v1 or failed actual report changed')
    failure=json.loads(FAILED.read_text(encoding='utf-8'))
    need(failure['native_component_verified'] is False and failure['native_stages_completed'] is False
         and failure['source_files_input_Artist_exact'] is True and failure['private_scene_disposed'] is True
         and failure['owned_native_input_preflight']['completed'] is False
         and failure['owned_native_input_preflight']['IDs']==[] and failure['errors']
         and 'public_install_entry' not in failure and 'samples' not in failure and 'input_native_preflight' not in failure,
         'Preserve actual pre-install/pre-cache failure, without borrowed effect acceptance')
    spec=importlib.util.spec_from_file_location('warm_v1_frozen',PREVIOUS)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def verify_inventory(entry):
    need(entry.get('inventory_complete') is True and entry.get('user_map_complete') is True,
         'Native ID/library inventory is Unknown')
    rows=entry['IDs']; pointers=[row['pointer'] for row in rows]
    need(rows and len(pointers)==len(set(pointers)) and all(type(row['is_library']) is bool
         and type(row['override']) is bool for row in rows), 'Incomplete native ID identity/types')
    actual=[row for row in rows if not row['is_library']]
    need(all(row['library_pointer'] is None and row['library'] is None and not row['override'] for row in actual),
         'Actual linked/override data ID refused, including indirect Geometry Node data')
    libraries=[row for row in rows if row['is_library']]
    proofs=entry['library_user_map']; library_pointers={row['pointer'] for row in libraries}
    need(len(proofs)==len(libraries) and {row['pointer'] for row in proofs}==library_pointers,
         'Library user-map coverage is Unknown')
    unused=[]
    for row in libraries:
        proof=next(proof for proof in proofs if proof['pointer']==row['pointer'])
        references=[item['pointer'] for item in rows if item['library_pointer']==row['pointer']]
        need(row['library_pointer'] is None and row['library'] is None and not row['override']
             and type(row['native_users']) is int and row['native_users']==0
             and not references and not proof['users'], 'Library still has an actual/Unknown user; refuse')
        unused.append(dict(pointer=row['pointer'],name=row['name'],filepath=row['filepath'],
                           native_users=0,inventory_library_referrers=references,user_map_users=proof['users'],
                           unused_metadata_only=True))
    entry['unused_library_metadata']=unused
    entry['all_actual_data_IDs_local']=True


def inventory(bpy, scene, report, write):
    entry=dict(completed=False,inventory_complete=False,user_map_complete=False,IDs=[],collections=[],
               library_user_map=[],unused_library_metadata=[],all_actual_data_IDs_local=False,
               simulation_objects=[obj.name for obj in scene.objects])
    report['owned_native_input_preflight']=entry; write()
    ids={}; rows={}
    def capture(item, origin):
        need(isinstance(item,bpy.types.ID), 'Non-ID in actual BlendData/user-map inventory')
        pointer=hex(item.as_pointer()); need(item.as_pointer()!=0, 'Native ID pointer unavailable')
        if pointer not in ids:
            ids[pointer]=item
            library=item.library
            row=dict(pointer=pointer,name=item.name,rna=item.bl_rna.identifier,seen_in=[],
                     library=None if library is None else library.filepath,
                     library_pointer=None if library is None else hex(library.as_pointer()),
                     override=item.override_library is not None,is_library=isinstance(item,bpy.types.Library),
                     native_users=item.users)
            if row['is_library']: row['filepath']=item.filepath
            rows[pointer]=row; entry['IDs'].append(row)
        if origin not in rows[pointer]['seen_in']: rows[pointer]['seen_in'].append(origin)
    try:
        for prop in bpy.data.bl_rna.properties:
            if prop.type!='COLLECTION': continue
            collection=getattr(bpy.data,prop.identifier)
            entry['collections'].append(dict(name=prop.identifier,count=len(collection)))
            for item in collection: capture(item,'BlendData.'+prop.identifier)
        user_map=bpy.data.user_map()
        for dependency,users in user_map.items():
            capture(dependency,'user_map.dependency')
            for user in users: capture(user,'user_map.user')
        # Embedded Material/World trees and the Scene master Collection are
        # native IDs even when not exposed as a top-level data collection.
        for owner in list(ids.values()):
            for field in ('node_tree','collection'):
                item=getattr(owner,field,None)
                if isinstance(item,bpy.types.ID): capture(item,owner.name+'.'+field)
        for pointer,item in ids.items():
            if isinstance(item,bpy.types.Library):
                need(item in user_map, 'Native Library user-map key missing: Unknown')
                entry['library_user_map'].append(dict(pointer=pointer,users=sorted(hex(user.as_pointer()) for user in user_map[item])))
        entry['inventory_complete']=entry['user_map_complete']=True
    except Exception as error:
        entry['read_error']=repr(error); write(); raise
    write()  # Preserve the complete actual inventory before any local-ID refusal.
    verify_inventory(entry); write()
    return entry


def append_scene(bpy, args, report, write):
    owner=previous()
    rna=bpy.ops.wm.append.get_rna_type()
    names=('directory','filename','link','do_reuse_local_id','autoselect','use_recursive')
    properties={name:rna.properties.get(name) for name in names}
    report['native_append_RNA']={name:None if prop is None else
        dict(identifier=prop.identifier,type=prop.type,is_readonly=prop.is_readonly) for name,prop in properties.items()}
    write()
    need(all(properties[name] is not None and not properties[name].is_readonly for name in names)
         and all(properties[name].type=='BOOLEAN' for name in ('link','do_reuse_local_id','autoselect','use_recursive'))
         and all(properties[name].type=='STRING' for name in ('directory','filename')),
         'Actual recursive Append RNA missing; refuse before load, no fallback')
    # List only. No requested ID is assigned in this library context.
    with bpy.data.libraries.load(str(owner.INPUT),link=False) as (available,_requested):
        report['available_saved_scenes']=list(available.scenes); write()
        need(args.scene in available.scenes, 'Explicit saved Scene missing; no fallback')
    before={scene.as_pointer() for scene in bpy.data.scenes}
    directory=str(owner.INPUT)+'\\Scene\\'
    report['native_append_request']=dict(directory=directory,filename=args.scene,link=False,
        do_reuse_local_id=False,autoselect=False,use_recursive=True,result=None,incremental_scene_pointers=[])
    write()
    result=bpy.ops.wm.append(directory=directory,filename=args.scene,link=False,
                           do_reuse_local_id=False,autoselect=False,use_recursive=True)
    report['native_append_request']['result']=sorted(result)
    added=[scene for scene in bpy.data.scenes if scene.as_pointer() not in before]
    report['native_append_request']['incremental_scene_pointers']=[dict(name=scene.name,pointer=hex(scene.as_pointer())) for scene in added]
    write()
    need('FINISHED' in result and len(added)==1, 'Append must create exactly one new native Scene pointer')
    inventory(bpy,added[0],report,write)
    return added[0]


def owned_inputs(bpy, scene, source, rig, body, report, write):
    entry=report['owned_native_input_preflight']
    verify_inventory(entry)
    need(all(scene.objects.get(obj.name)==obj for obj in (source,rig,body))
         and source.data is not body.data and body.data.users==1,
         'Explicit owned Scene Body/Dress/rig inputs differ')
    entry['completed']=True; write()


def prepared_namespace():
    owner=previous(); n,parent,original,changed=owner.prepared_namespace()
    n['_EXTRA_PINS'].update({PREVIOUS:PREVIOUS_SHA,FAILED:FAILED_SHA})
    return n,parent,original,changed


def namespace():
    owner=previous(); values=dict(vars(owner))
    original=ast.parse(inspect.getsource(owner.main)).body[0]; changed=copy.deepcopy(original)
    before_try=next(node for node in original.body if isinstance(node,ast.Try))
    target=next(node for node in changed.body if isinstance(node,ast.Try))
    index=next(index for index,node in enumerate(target.body) if isinstance(node,ast.With)
               and ast.unparse(node.items[0].context_expr)=='bpy.data.libraries.load(str(INPUT), link=False)')
    need([ast.unparse(node) for node in target.body[index+1:index+4]]==[
        "need(len(requested.scenes) == 1 and requested.scenes[0] is not None, 'Native private Scene closure load failed')",
        'scene = requested.scenes[0]','bpy.context.window.scene = scene'], 'Unique frozen load ABI changed')
    target.body[index:index+4]=ast.parse('scene=_APPEND_SCENE(bpy,args,report,write)\nbpy.context.window.scene=scene').body
    report_assignment=next(index for index,node in enumerate(changed.body) if isinstance(node,ast.Assign)
                           and ast.unparse(node.targets[0])=='report')
    changed.body[report_assignment+1:report_assignment+1]=ast.parse("report['prior_failed_library_load']={'runner':str(_PREVIOUS),'runner_sha256':_PREVIOUS_SHA,'report':str(_FAILED),'report_sha256':_FAILED_SHA,'preserved_failure':True,'acceptance_borrowed':False}").body
    for node in ast.walk(changed):
        if isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V1_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V2_52'
    need(ast.dump(ast.Module(body=target.finalbody,type_ignores=[]))==ast.dump(ast.Module(body=before_try.finalbody,type_ignores=[])),
         'Frozen outer native cleanup/source/finally changed')
    values.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,prepared_namespace=prepared_namespace,
                  owned_inputs=owned_inputs,_APPEND_SCENE=append_scene,
                  _PREVIOUS=PREVIOUS,_PREVIOUS_SHA=PREVIOUS_SHA,_FAILED=FAILED,_FAILED_SHA=FAILED_SHA)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[changed],type_ignores=[])),str(Path(__file__).resolve()),'exec'),values)
    return owner,values,original,changed


def pure_checks():
    from types import SimpleNamespace as NS
    owner,values,original,changed=namespace(); owner.pure_checks()
    n,_,_,_=prepared_namespace(); values['base']=None
    need(not n['_MISSING_GLOBALS'](values['main']), 'Actual v2 compiled main closure incomplete')
    base=dict(inventory_complete=True,user_map_complete=True,IDs=[dict(pointer='0x1',name='Node',rna='GeometryNodeTree',
        seen_in=['BlendData.node_groups'],is_library=False,override=False,library=None,library_pointer=None,native_users=1)],library_user_map=[])
    verify_inventory(copy.deepcopy(base))
    unused=copy.deepcopy(base); unused['IDs'].append(dict(pointer='0x2',name='Library',filepath='D:/official-or-any.blend',
        is_library=True,override=False,library=None,library_pointer=None,native_users=0)); unused['library_user_map']=[dict(pointer='0x2',users=[])]
    verify_inventory(unused); need(len(unused['unused_library_metadata'])==1,'Unused metadata control failed')
    bad=[]
    linked=copy.deepcopy(unused); linked['IDs'][0].update(library='D:/official-or-any.blend',library_pointer='0x2'); bad.append(linked)
    overridden=copy.deepcopy(unused); overridden['IDs'][0]['override']=True; bad.append(overridden)
    actual_user=copy.deepcopy(unused); actual_user['library_user_map'][0]['users']=['0x1']; bad.append(actual_user)
    native_user=copy.deepcopy(unused); native_user['IDs'][1]['native_users']=1; bad.append(native_user)
    incomplete=copy.deepcopy(unused); incomplete['inventory_complete']=False; bad.append(incomplete)
    for entry in bad:
        try: verify_inventory(entry)
        except RuntimeError: pass
        else: need(False,'Actual linked/override/user/Unknown library evidence admitted')
    report={}; fake_bpy=NS(ops=NS(wm=NS(append=NS(get_rna_type=lambda:NS(properties={})))))
    try: append_scene(fake_bpy,NS(scene='Scene'),report,lambda:None)
    except RuntimeError: pass
    else: need(False,'Missing recursive RNA did not stop before data/library access')
    need(all(value is None for value in report['native_append_RNA'].values()), 'Missing RNA actual evidence lost')
    source=inspect.getsource(append_scene)
    tree=ast.parse(source)
    need(not any(isinstance(node,ast.Assign) and 'requested.' in ast.unparse(node) for node in ast.walk(tree)),
         'Names-only library context requested an ID')
    need('use_recursive=True' in source and 'do_reuse_local_id=False' in source
         and source.index('Actual recursive Append RNA missing')<source.index('with bpy.data.libraries.load'), 'Actual RNA/load ownership ordering differs')
    need(not any(isinstance(node,ast.Call) and 'make_local' in ast.unparse(node.func) for node in ast.walk(ast.parse(Path(__file__).read_text(encoding='utf-8')))), 'make_local fallback appeared')
    print(json.dumps(dict(source_prepared=True,native_run=False,outer_finally_AST_exact=True,
        frozen_v1_recipe_and_inner_finally_unchanged=True,actual_linked_NodeGroup_rejected=True,
        unused_Library_metadata_distinguished=True,library_guard_rejection_controls=5,
        missing_recursive_RNA_refused_before_data_access=True,accepted=False)))


def main():
    _,values,_,_=namespace()
    return values['main']()


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
