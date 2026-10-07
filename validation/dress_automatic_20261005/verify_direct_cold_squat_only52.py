"""Private controlled FK squat C30; Root alone executes native BG5.2.

The immutable progressive recipe supplies the same cold/Air5/source/Artist
guards, native sample/contact precision and Body12 author restoration. No A/B,
timeline Action, Dress key, runtime change or foot planting is claimed here.
"""
import argparse
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
PARENT = HERE/'verify_direct_cold_progressive_pose_reset52.py'
PARENT_SHA = 'f8e0d90cbd263baec2eecc9dc5f8f2225f3f7ea7e583c14f7644e41261764050'
CONTACT_LABELS = ('C_squat16','C_squat30')


def need(value, message):
    if not value:
        raise RuntimeError('SquatOnly52: '+message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_parent():
    need(sha(PARENT)==PARENT_SHA,'Frozen progressive recipe differs')
    spec=importlib.util.spec_from_file_location('squat_only_frozen_progressive',PARENT)
    parent=importlib.util.module_from_spec(spec); spec.loader.exec_module(parent)
    return parent


def constraint_receipt(rig, record, graph, shared):
    """All actual Dress control/mechanism/deform constraints, ordered per bone."""
    names=set()
    def controls(value):
        if type(value) is str: names.add(value)
        elif type(value) is dict:
            for item in value.values(): controls(item)
        elif type(value) is list:
            for item in value: controls(item)
        else: need(False,'Unsupported saved Dress control inventory')
    controls(record['controls'])
    for chain in record['chains']:
        for layer in ('manual','phys','def'):
            need(type(chain[layer]) is list and all(type(name) is str for name in chain[layer]),'Missing actual chain inventory')
            names.update(chain[layer])
    need(names and all(rig.pose.bones.get(name) is not None for name in names),'Native Dress bone inventory unresolved')
    evaluated=rig.evaluated_get(graph)
    def read(owner):
        rows=[]
        for name in sorted(names):
            bone=owner.pose.bones.get(name)
            need(bone is not None,'Evaluated Dress bone missing')
            entries=[]
            for constraint in bone.constraints:
                target_supported=hasattr(constraint,'target'); subtarget_supported=hasattr(constraint,'subtarget')
                influence=float(constraint.influence)
                need(type(constraint.mute) is bool and 0.<=influence<=1.,'Native constraint state unresolved')
                entries.append({'name':constraint.name,'type':constraint.type,
                    'target_supported':target_supported,'target':shared._id(constraint.target) if target_supported else None,
                    'subtarget_supported':subtarget_supported,'subtarget':constraint.subtarget if subtarget_supported else None,
                    'influence':influence,'mute':constraint.mute,'native_rna':shared._rna(constraint)})
            rows.append({'bone':name,'constraints':entries})
        return rows
    return {'native_original':read(rig),'native_evaluated':read(evaluated),'bone_count':len(names),
            'scope':'Saved Dress controls plus all manual/phys/def bones; empty constraint lists retained',
            'evaluated_dependency_causality_proved':False,'accepted':False}


def contact_gate(contacts):
    parent=load_parent()
    collected=type(contacts) is list and [row.get('label') for row in contacts]==list(CONTACT_LABELS)
    measured=bool(collected and all(parent.endpoint_complete(row) for row in contacts))
    zero=bool(collected and all(parent.endpoint_zero(row) for row in contacts))
    return {'all2_samples_collected':collected,'all2_complete_measured':measured,
            'all2_complete_measured_zero':zero,'scope':'Final all3040, entire Body triangles and three closed proxies at C16/C30',
            'sparse_contact_result':'measured_zero' if zero else 'measured_penetration_or_crossing' if measured else 'Unknown',
            'full_time_contact_verified':False,'self_intersection_verified':False,
            'naturalness_evaluated':False,'overall_accepted':False}


def squat_body(parent):
    module=ast.parse(inspect.cleandoc(parent.BODY))
    first=module.body[0]
    need(isinstance(first,ast.Expr) and isinstance(first.value,ast.Call),'Frozen report update ABI differs')
    keywords={keyword.arg:keyword for keyword in first.value.keywords}
    values={'stage':'CURRENT_ARTIST_DIRECT_COLD_SQUAT_ONLY52','case':'squat_only',
        'scope':'One fresh private air5 candidate; controlled native FK deep squat C30 only',
        'motion_recipe':{'physical_steps':30,'phases':{'C':'controlled FK squat30'},'Manual_same_frame_increments':0,
                         'imported_clip':False,'foot_planted':False,'Dress_keys_created':0,'Actions_created':0}}
    for key,value in values.items(): keywords[key].value=ast.parse(repr(value),mode='eval').body
    first.value.keywords.extend(ast.keyword(arg=key,value=ast.Constant(value)) for key,value in (
        ('native_squat_sample_collection_completed',False),('squat_actual_input_verified',False),
        ('naturalness_evaluated',False),('overall_accepted',False)))
    render_guard=module.body[1].value
    need(isinstance(render_guard,ast.Call) and render_guard.args[1].value=='Same protected current Artist, six front/side images and soft180 required',
         'Frozen render guard differs')
    render_guard.args[1]=ast.Constant('Same protected current Artist, two front/side images and soft180 required')
    def phase_call(node,phase):
        return (isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name)
                and node.value.func.id=='run_phase' and len(node.value.args)==1 and node.value.args[0].value==phase)
    start=next(i for i,node in enumerate(module.body) if phase_call(node,'A'))
    end=next(i for i,node in enumerate(module.body) if phase_call(node,'C'))
    need(start<end,'Frozen A/B/C execution order differs')
    del module.body[start:end]
    text=ast.unparse(ast.fix_missing_locations(module))
    # Only observation receipts and accurate two-contact completion reporting.
    replacements=(
        ('graph = context.evaluated_depsgraph_get()\ncopy_error',
         "graph = context.evaluated_depsgraph_get()\nreport['initial_skirt_constraints'] = _CONSTRAINTS(rig, installed, graph, direct.shared)\nwrite()\ncopy_error"),
        ('if diagnose:\n        tick = time.perf_counter()',
         "if diagnose:\n        row['actual_skirt_constraints'] = _CONSTRAINTS(rig, installed, graph, direct.shared)\n        write()\n        tick = time.perf_counter()"),
        ("need(all((value >= 90.0 for value in knee_bends.values()))",
         "report['native_squat_sample_collection_completed'] = True\nreport['squat_actual_input']['scene_scale_length_m_per_world_unit'] = metres\nreport['squat_actual_input']['native_Root_world_drop_units'] = root_drop / metres\nreport['squat_actual_input_verified'] = all(value >= 90.0 for value in knee_bends.values()) and abs(root_drop - expected_drop) <= 5e-05 and all(value['actual_drop_m'] > 5e-05 for value in hip_heights.values()) and last['actual_Body_mesh_from_squat_N']['maximum_m'] > 5e-05 and first['Body_world_sha256'] != last['Body_world_sha256']\nwrite()\nneed(all((value >= 90.0 for value in knee_bends.values()))"),
        ("report['full_surface_contact_gate']['all7_samples_collected'] and report['full_surface_contact_gate']['Automatic_all6_complete_measured_zero']",
         "report['full_surface_contact_gate']['all2_samples_collected'] and report['full_surface_contact_gate']['all2_complete_measured_zero']"))
    for old,new in replacements:
        need(text.count(old)==1,'Unique squat-only observer/source ABI differs: '+old[:55])
        text=text.replace(old,new)
    return text


def prepared_namespace(expected_direct_sha,cold_report,cold_report_sha):
    parent=load_parent()
    namespace,base,original,_changed,parent_edits=parent.prepared_namespace(expected_direct_sha,cold_report,cold_report_sha)
    main=parent.load_air().load_adapter().prepared_namespace(expected_direct_sha,cold_report,cold_report_sha)[3]
    for old,new in parent_edits:
        need(main.count(old)==1,'Frozen compiled main replacement differs'); main=main.replace(old,new)
    need(main.count("choices=('progressive_reset_squat',),default='progressive_reset_squat'")==1,'Parent case parser ABI differs')
    main=main.replace("choices=('progressive_reset_squat',),default='progressive_reset_squat'","choices=('squat_only',),default='squat_only'")
    main=main.replace('CURRENT_ARTIST_DIRECT_PROGRESSIVE_POSE_RESET52','CURRENT_ARTIST_DIRECT_COLD_SQUAT_ONLY52')
    main=main.replace('Fresh private air5 paired leg and Manual Reset replay30+30 plus controlled squat30; Body12 restore retained; no naturalness or fidelity acceptance',
                      'Fresh private air5 controlled squat C30 only; actual Body inputs and final contacts; no naturalness acceptance')
    marker='pins.update({_QA_AIR:_QA_AIR_SHA,_AIR_PROOF:_AIR_PROOF_SHA})'
    need(main.count(marker)==1,'Main proof pins ABI differs'); main=main.replace(marker,marker+'; pins.update({_SQUAT_PARENT:_SQUAT_PARENT_SHA})')
    run=copy.deepcopy(original); trial=next(node for node in run.body if isinstance(node,ast.Try))
    trial.body=ast.parse(squat_body(parent)).body
    namespace.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,_SQUAT_PARENT=PARENT,_SQUAT_PARENT_SHA=PARENT_SHA,
                     _CONSTRAINTS=constraint_receipt,_FINAL_CONTACT_GATE=contact_gate,_CONTACT_LABELS=CONTACT_LABELS)
    run_source=ast.unparse(ast.fix_missing_locations(run))
    exec(compile(run_source+'\n'+main,str(Path(__file__).resolve()),'exec'),namespace)
    return namespace,base,original,run,main


def cli_preflight(parent,namespace,main):
    adapter=parent.load_air().load_adapter()
    output=HERE/'squat_only_cli_preflight_uncreated'/'result'
    argv=['blender.exe','--background','--factory-startup','--',
        '--expected-direct-sha',parent.PROVIDER_SHA,'--cold-report',str(parent.COLD),'--cold-report-sha',parent.COLD_SHA,
        '--output',str(output),'--artist-protection',str(HERE/'artist_disk_protection_20261007_e0b30f73fc2f.json'),
        '--artist-protection-sha',parent.ARTIST_RECEIPT_SHA,'--body-object','Cosha','--dress-object','Dress',
        '--case','squat_only','--soft-seconds','180','--render']
    dependencies,delegated=adapter.dependency_arguments(argv)
    need(dependencies==(parent.PROVIDER_SHA,parent.COLD.resolve(),parent.COLD_SHA),'Real dependency CLI differs')
    function=ast.parse(main).body[0]
    cut=next(i for i,node in enumerate(function.body) if isinstance(node,ast.Import) and any(item.name=='bpy' for item in node.names))
    function=copy.deepcopy(function); function.name='actual_main_parser_prefix'
    function.body=function.body[:cut]+[ast.Return(value=ast.Name(id='args',ctx=ast.Load()))]
    need(not any(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='mkdir'
                 for node in ast.walk(function)),'Native preflight would create files')
    scope=dict(namespace); exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),'<actual-squat-main-parser>','exec'),scope)
    previous=sys.argv
    try:
        sys.argv=delegated; result=scope['actual_main_parser_prefix']()
    finally: sys.argv=previous
    need(result.case=='squat_only' and result.render and result.soft_seconds==180. and not output.exists(),'Actual delegated CLI differs')


def pure_checks():
    parent=load_parent(); namespace,base,original,run,main=prepared_namespace(parent.PROVIDER_SHA,parent.COLD,parent.COLD_SHA)
    old=next(node for node in original.body if isinstance(node,ast.Try)); new=next(node for node in run.body if isinstance(node,ast.Try))
    need(ast.dump(ast.Module(body=old.finalbody,type_ignores=[]))==ast.dump(ast.Module(body=new.finalbody,type_ignores=[]))
         and ast.dump(ast.Module(body=original.body[:original.body.index(old)],type_ignores=[]))==ast.dump(ast.Module(body=run.body[:run.body.index(new)],type_ignores=[])),
         'Author/Body12 prefix or finally changed')
    need(namespace['restore_body_coordinates'] is base.restore_body_coordinates and namespace['run_motion'].__globals__ is namespace
         and namespace['main'].__globals__ is namespace,'Real compiled restore/globals differ')
    need(not parent.missing_compiled_globals(namespace['run_motion']) and not parent.missing_compiled_globals(namespace['main']),
         'Actual compiled run/closures/main global missing')
    calls=[node for node in ast.walk(ast.parse(squat_body(parent))) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='run_phase']
    need(len(calls)==1 and calls[0].args[0].value=='C','Non-squat phase would execute')
    need(namespace['_RECIPE'].__code__.co_code==parent.recipe.__code__.co_code
         and namespace['_ENDPOINT_ZERO'].__code__.co_code==parent.endpoint_zero.__code__.co_code,'Original input/contact guard changed')
    good={'strict_Body_crossing':{'status':'measured','full_surface_filter':{'complete':True},'actual_crossing_pair_count':0},
          'unresolved_counts':dict.fromkeys(('coplanar_unresolved','degenerate_unresolved','boundary_unresolved'),0),
          'Unknown_if_incomplete':False,'closed3':[{'all3040':{'sampled_vertices':3040,'inside_vertices':0,'maximum_penetration_m':0.}} for _ in range(3)]}
    contacts=[dict(copy.deepcopy(good),label=label) for label in CONTACT_LABELS]
    need(contact_gate(contacts)['all2_complete_measured_zero'],'Actual full contact positive rejected')
    negatives=0
    for index in (0,1):
        for kind in ('Unknown','penetration','partial3040'):
            bad=copy.deepcopy(contacts)
            if kind=='Unknown': bad[index]['Unknown_if_incomplete']=True
            elif kind=='penetration': bad[index]['closed3'][0]['all3040']['maximum_penetration_m']=.014
            else: bad[index]['closed3'][0]['all3040']['sampled_vertices']=2880
            need(not contact_gate(bad)['all2_complete_measured_zero'],'Unknown/penetration/partial final surface admitted'); negatives+=1
    need(not contact_gate(contacts[:1])['all2_samples_collected'],'Missing C30 admitted'); negatives+=1
    cli_preflight(parent,namespace,main)
    readers=base.load('verify_direct_cold_install52_v4.py')
    spec=importlib.util.spec_from_file_location('squat_pure_readers',readers.COMPARATOR)
    reader=importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
    source=reader.load(reader.SOURCE,reader.SOURCE_SHA,'squat_pure_manifest')
    disk=reader.load(reader.DISK,reader.DISK_SHA,'squat_pure_disk')
    prior=json.loads(parent.AIR_PROOF.read_text(encoding='utf-8'))
    need(source.current_manifest()==prior['source_before']==prior['source_after'],'Current full source changed since actual Air5')
    need(disk.proof(Path(prior['artist_after']['path']),parent.ARTIST_RECEIPT_SHA)['sha256']==parent.ARTIST_RECEIPT_SHA,
         'Current typed Artist disk proof differs')
    need(sha(PARENT)==PARENT_SHA,'Frozen progressive source modified')
    print(json.dumps({'source_prepared':True,'native_executed':False,'physical_steps':30,'only_original_C30_executed':True,
        'Body12_author_prefix_finally_exact':True,'actual_compiled_global_and_restore_identity':True,'real_dependency_and_main_CLI_preflight':True,
        'current_full_source_and_typed_Artist_preflight':True,
        'full3040_Body_closed3_contact_samples':2,'front_side_images':2,'contact_negative_controls':negatives,
        'native_knee_hip_Root_Body_verification_preserved':True,'actual_constraint_receipts':'before input and C16/C30',
        'naturalness_evaluated':False,'overall_accepted':False}))


def main():
    parent=load_parent(); adapter=parent.load_air().load_adapter()
    dependencies,delegated=adapter.dependency_arguments(sys.argv)
    need(dependencies==(parent.PROVIDER_SHA,parent.COLD.resolve(),parent.COLD_SHA),'Only reviewed current dependencies allowed')
    namespace,*_=prepared_namespace(*dependencies)
    previous=sys.argv; before=sha(Path(__file__).resolve())
    try:
        sys.argv=delegated; return namespace['main']()
    finally:
        sys.argv=previous
        need(sha(Path(__file__).resolve())==before and sha(PARENT)==PARENT_SHA,'Frozen squat/parent source changed')


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
