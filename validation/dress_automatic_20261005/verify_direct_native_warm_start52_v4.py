"""SOURCE_PREPARED v4: local metadata-only Library subgraph admission.

The frozen v3 actual ID inventory has no linked/override data, but its Library
parent edge and one extra native user are not unused metadata.
External library files remain read-only; native Append resolves declared dependencies.
No manual external file inspection, modification or purge.
Physics/cache/75 recipe stays v3.
"""
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PREVIOUS=HERE/'verify_direct_native_warm_start52_v3.py'
PREVIOUS_SHA='1008321dfc643deec0d8bfb080af2e9d7941677160585143f8cf900a8c394b31'
FAILED=HERE/'actual_direct_native_warm_start_v3_52_20261008_150630_311_6a8245f15b424163894e834d9c89a890/result/report.json'
FAILED_SHA='f158dcd2489ef1dfffbd14424a4d0ec3d0b98f6738ddc0507b133a59f9dfe08e'


def need(value,message):
    if not value: raise RuntimeError('NativeWarmStartMetadata52: '+message)


def verify_inventory(entry):
    need(entry.get('inventory_complete') is True and entry.get('user_map_complete') is True,
         'Native ID/library inventory is Unknown')
    rows=entry['IDs']; pointers=[row['pointer'] for row in rows]
    need(rows and len(pointers)==len(set(pointers)) and all(type(row['is_library']) is bool
         and type(row['override']) is bool for row in rows),'Incomplete native ID identity/types')
    actual=[row for row in rows if not row['is_library']]
    need(all(row['library_pointer'] is None and row['library'] is None and not row['override'] for row in actual),
         'Actual linked/override data ID refused, including indirect Geometry Node data')
    libraries=[row for row in rows if row['is_library']]
    proofs=entry['library_user_map']; library_pointers={row['pointer'] for row in libraries}
    need(len(proofs)==len(libraries) and {row['pointer'] for row in proofs}==library_pointers,
         'Library user-map coverage is Unknown')
    metadata=[]
    for row in libraries:
        proof=next(proof for proof in proofs if proof['pointer']==row['pointer'])
        users=proof['users']
        references=[item['pointer'] for item in rows if item['library_pointer']==row['pointer']]
        need(row['library_pointer'] is None and row['library'] is None and not row['override']
             and type(users) is list and all(type(pointer) is str for pointer in users)
             and len(users)==len(set(users)) and all(pointer in library_pointers for pointer in users)
             and not references and type(row['native_users']) is int
             and 0<=row['native_users']<=len(users)+1,
             'Library has actual/Unknown users, is nonlocal/override, or its native counter exceeds metadata bound')
        metadata.append(dict(pointer=row['pointer'],name=row['name'],filepath=row['filepath'],
            native_users=row['native_users'],inventory_library_referrers=references,user_map_users=list(users),
            metadata_user_count=len(users),native_user_upper_bound=len(users)+1,
            at_most_one_extra_native_user=True,user_flags=copy.deepcopy(row.get('user_flags',{})),
            metadata_only=True))
    entry['metadata_only_libraries']=metadata
    entry['all_actual_data_IDs_local']=True


def previous():
    need(hashlib.sha256(PREVIOUS.read_bytes()).hexdigest()==PREVIOUS_SHA
         and hashlib.sha256(FAILED.read_bytes()).hexdigest()==FAILED_SHA,'Frozen v3/failure changed')
    failure=json.loads(FAILED.read_text(encoding='utf-8'))
    entry=failure['owned_native_input_preflight']; request=failure['native_append_request']
    need(failure['stage']=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V3_52'
         and failure['native_component_verified'] is False and failure['native_stages_completed'] is False
         and failure['source_files_input_Artist_exact'] is True and failure['private_scene_disposed'] is True
         and failure['errors'] and entry['completed'] is False and len(entry['IDs'])==299
         and request['result']==['FINISHED'] and len(request['incremental_scene_pointers'])==1
         and 'public_install_entry' not in failure and 'input_native_preflight' not in failure
         and 'samples' not in failure,'Retain actual metadata-only pre-install/pre-cache refusal; no effect acceptance')
    admitted=copy.deepcopy(entry); verify_inventory(admitted)
    need(len(admitted['metadata_only_libraries'])==3,'Frozen actual metadata evidence changed')
    spec=importlib.util.spec_from_file_location('warm_v3_frozen',PREVIOUS)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def prepared_namespace():
    owner=previous(); n,parent,original,changed=owner.prepared_namespace()
    n['_EXTRA_PINS'].update({PREVIOUS:PREVIOUS_SHA,FAILED:FAILED_SHA})
    return n,parent,original,changed


def metadata_helpers(owner):
    # Copy real frozen v2 functions into a private validation namespace. Append
    # and owned_inputs retain their AST; only inventory's report label and
    # optional Library user-flag observations differ. No original module edit.
    values=dict(vars(owner)); values['verify_inventory']=verify_inventory
    original=ast.parse(inspect.getsource(owner.inventory)).body[0]; changed=copy.deepcopy(original)
    for node in ast.walk(changed):
        if isinstance(node,ast.keyword) and node.arg=='unused_library_metadata': node.arg='metadata_only_libraries'
    capture=next(node for node in changed.body if isinstance(node,ast.FunctionDef) and node.name=='capture')
    branch=next(node for node in ast.walk(capture) if isinstance(node,ast.If)
                and ast.unparse(node.test)=="row['is_library']")
    addition=ast.parse("""row['user_flags']={}
for field in ('use_fake_user','use_extra_user'):
    try:
        value=getattr(item,field)
        row['user_flags'][field]=dict(read_status='Read',value=value if type(value) is bool else repr(value),
                                      actual_type=type(value).__name__)
    except Exception as error:
        row['user_flags'][field]=dict(read_status='UnknownReadFailed',error=repr(error))
""").body
    branch.body.extend(addition)
    reverse=copy.deepcopy(changed)
    for node in ast.walk(reverse):
        if isinstance(node,ast.keyword) and node.arg=='metadata_only_libraries': node.arg='unused_library_metadata'
    reverse_capture=next(node for node in reverse.body if isinstance(node,ast.FunctionDef) and node.name=='capture')
    reverse_branch=next(node for node in ast.walk(reverse_capture) if isinstance(node,ast.If)
                        and ast.unparse(node.test)=="row['is_library']")
    reverse_branch.body=reverse_branch.body[:-len(addition)]
    need(ast.dump(reverse)==ast.dump(original),'Non-metadata actual inventory read/coverage behavior changed')
    append=ast.parse(inspect.getsource(owner.append_scene)).body[0]
    owned=ast.parse(inspect.getsource(owner.owned_inputs)).body[0]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[changed,append,owned],type_ignores=[])),
                 str(Path(__file__).resolve()),'exec'),values)
    return values


def namespace():
    owner=previous(); _,values,_,original=owner.namespace(); changed=copy.deepcopy(original)
    helpers=metadata_helpers(owner.previous())
    index=next(index for index,node in enumerate(changed.body) if isinstance(node,ast.Assign)
               and ast.unparse(node.targets[0])=='report')
    changed.body.insert(index+1,ast.parse("report['prior_failed_library_metadata']={'runner':str(_METADATA_PREVIOUS),'runner_sha256':_METADATA_PREVIOUS_SHA,'report':str(_METADATA_FAILED),'report_sha256':_METADATA_FAILED_SHA,'preserved_failure':True,'acceptance_borrowed':False}").body[0])
    for node in ast.walk(changed):
        if isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V3_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V4_52'
    reverse=copy.deepcopy(changed)
    reverse.body=[node for node in reverse.body if not (isinstance(node,ast.Assign)
                  and ast.unparse(node.targets[0])=="report['prior_failed_library_metadata']")]
    for node in ast.walk(reverse):
        if isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V4_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V3_52'
    need(ast.dump(reverse)==ast.dump(original),'Frozen non-metadata v3 main/finally changed')
    values.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,prepared_namespace=prepared_namespace,
        _APPEND_SCENE=helpers['append_scene'],owned_inputs=helpers['owned_inputs'],
        _METADATA_PREVIOUS=PREVIOUS,_METADATA_PREVIOUS_SHA=PREVIOUS_SHA,
        _METADATA_FAILED=FAILED,_METADATA_FAILED_SHA=FAILED_SHA)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[changed],type_ignores=[])),
                 str(Path(__file__).resolve()),'exec'),values)
    return owner,values,original,changed


def pure_checks():
    from types import SimpleNamespace as NS
    owner,values,original,changed=namespace(); owner.pure_checks()
    n,_,_,_=prepared_namespace(); values['base']=None
    need(not n['_MISSING_GLOBALS'](values['main']),'Real compiled v4 globals incomplete')
    base=dict(inventory_complete=True,user_map_complete=True,IDs=[dict(pointer='0x1',name='Node',
        is_library=False,override=False,library=None,library_pointer=None,native_users=1),
        dict(pointer='0x2',name='LibraryA',filepath='unread/arbitrary-a.blend',is_library=True,override=False,
             library=None,library_pointer=None,native_users=1),
        dict(pointer='0x3',name='LibraryB',filepath='unread/arbitrary-b.blend',is_library=True,override=False,
             library=None,library_pointer=None,native_users=1)],
        library_user_map=[dict(pointer='0x2',users=['0x3']),dict(pointer='0x3',users=[])])
    accepted=copy.deepcopy(base); verify_inventory(accepted)
    need(len(accepted['metadata_only_libraries'])==2 and accepted['all_actual_data_IDs_local'] is True
         and 'unused_library_metadata' not in accepted,'Library parent/one-extra-user metadata control failed')
    upper=copy.deepcopy(base); upper['IDs'][1]['native_users']=2; verify_inventory(upper)
    failures=[]
    def bad():
        value=copy.deepcopy(base); failures.append(value); return value
    bad()['IDs'][0].update(library='arbitrary-a.blend',library_pointer='0x2')
    bad()['IDs'][0]['override']=True
    bad()['IDs'][1]['override']=True
    bad()['IDs'][1].update(library='linked.blend',library_pointer='0x3')
    bad()['library_user_map'][0]['users']=['0x1']
    bad()['library_user_map'][0]['users']=['0xunknown']
    bad()['library_user_map'].pop()
    bad()['inventory_complete']=False
    bad()['user_map_complete']=False
    bad()['IDs'][2]['native_users']=-1
    bad()['IDs'][2]['native_users']=2
    bad()['IDs'][2]['native_users']=True
    bad()['library_user_map'][0]['users']=['0x3','0x3']
    bad()['library_user_map'][0]['users']=None
    failures[0]['IDs'][1]['user_flags']={'use_fake_user':dict(read_status='Read',value=True),
                                      'use_extra_user':dict(read_status='Read',value=True)}
    for entry in failures:
        try: verify_inventory(entry)
        except RuntimeError: pass
        else: need(False,'Linked/override/actual/Unknown users, missing coverage or counter overflow admitted')
    # Execute the real copied inventory on a small native-endpoint fixture.
    class ID:
        def __init__(self,pointer,name):
            self.pointer=pointer; self.name=name; self.library=None; self.override_library=None; self.users=1
            self.bl_rna=NS(identifier=type(self).__name__)
        def as_pointer(self): return self.pointer
    class Library(ID):
        def __init__(self,pointer,name):
            super().__init__(pointer,name); self.filepath='never-opened/'+name
            self.use_fake_user=True; self.use_extra_user=False
    node=ID(1,'Node'); a=Library(2,'A'); b=Library(3,'B')
    data=NS(node_groups=[node],libraries=[a,b],bl_rna=NS(properties=[
        NS(type='COLLECTION',identifier='node_groups'),NS(type='COLLECTION',identifier='libraries')]),
        user_map=lambda:{node:set(),a:{b},b:set()})
    helpers=metadata_helpers(owner.previous()); report={}; writes=[]
    entry=helpers['inventory'](NS(data=data,types=NS(ID=ID,Library=Library)),NS(objects=[]),report,
                               lambda:writes.append(copy.deepcopy(report)))
    need(len(entry['IDs'])==3 and entry['inventory_complete'] is True and entry['user_map_complete'] is True
         and len(entry['metadata_only_libraries'])==2 and entry['IDs'][1]['user_flags']['use_fake_user']['value'] is True
         and entry['IDs'][1]['user_flags']['use_extra_user']['value'] is False
         and writes[-2]['owned_native_input_preflight']['inventory_complete'] is True
         and not writes[-2]['owned_native_input_preflight']['metadata_only_libraries'],
         'Real inventory flags/complete-before-admission evidence lost')
    helper_tree=ast.parse('\n'.join(inspect.getsource(getattr(owner.previous(),name))
                                   for name in ('inventory','append_scene','owned_inputs')))
    need(not any(isinstance(node,ast.Call) and any(word in ast.unparse(node.func) for word in
         ('users_clear','purge','unlink','remove','make_local')) for node in ast.walk(helper_tree)),
         'External/metadata cleanup fallback appeared')
    print(json.dumps(dict(source_prepared=True,native_run=False,actual_v3_299_ID_inventory_admitted_as_metadata_only=True,
        Library_to_Library_and_one_extra_native_user_allowed=True,metadata_rejection_controls=len(failures),
        actual_linked_NodeGroup_and_override_refused=True,missing_coverage_unknown_pointer_and_counter_overflow_refused=True,
        real_inventory_user_flags_recorded=True,complete_before_guard_evidence_retained=True,
        inverse_main_and_inventory_AST_exact=True,physics_cache_high75_finally_unchanged=True,accepted=False)))


def main():
    _,values,_,_=namespace()
    return values['main']()


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
