"""Private saved-Artist Direct sealed-cache/Manual/explicit Reset component QA.

Factory BG5.2 only, Root owns execution. No native work in --pure-checks.
No collision, naturalness, export, full cache-payload or artist-save acceptance.
The approved C read window writes only its owned Cloth flags, then restores them.
Native dirty status is separate from thirteen unchanged seal/configuration fields;
full cache payload remains Unproven. The old failed QA/report stay immutable.
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
ADAPTER = HERE / 'verify_direct_cold_stop_settling_tail52_dependencies.py'
ADAPTER_SHA = 'f04d6d65e514bc1839fb3abff1d2bc4eea41f75c34636e80e9c877463faaabcf'
PHYSICS = Path(r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\skirt_physics.py')
PHYSICS_SHA = '2d388f7de87ea4bb02e98f7fd28560003c3212a646682057cfe3ebfa0a3413e2'
ARTIST_RECEIPT = HERE / 'artist_disk_protection_20261007_e0b30f73fc2f.json'
ARTIST_RECEIPT_SHA = '4d092929664f9718241afabc1ba3a3c667b600eeeb3d8a98fac0aea322ff536f'
OLD_QA = HERE / 'verify_direct_sealed_manual_bake52.py'
OLD_QA_SHA = '794abac7074003bba121a48cb8a491a9f3f593f2efc5eb7ab1b5f3e0e527852b'
FAILED_REPORT = HERE / 'actual_direct_sealed_manual_bake_e0b_52_20261007_065400_531' / 'result' / 'report.json'
FAILED_REPORT_SHA = '36a958a32585a75603d3a36b48ba4670b8a2881796dd8c828bfa44bd551b54bf'


def need(value, message):
    if not value:
        raise RuntimeError('SealedManualBake52: ' + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_adapter():
    need(sha(ADAPTER) == ADAPTER_SHA and sha(PHYSICS) == PHYSICS_SHA
         and sha(ARTIST_RECEIPT) == ARTIST_RECEIPT_SHA
         and sha(OLD_QA) == OLD_QA_SHA and sha(FAILED_REPORT) == FAILED_REPORT_SHA,
         'Frozen observer/service/Artist receipt or old failure evidence differs')
    spec = importlib.util.spec_from_file_location('sealed_manual_dependency_adapter', ADAPTER)
    adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
    return adapter


def cache14(cloth, q):
    cache = cloth.point_cache
    row = {**q.cache_state(cloth), 'is_baking': cache.is_baking, 'is_outdated': cache.is_outdated,
           'info': cache.info, 'filepath': cache.filepath, 'library_path': cache.use_library_path, 'index': cache.index}
    fields = {'pointer': int, 'start': int, 'end': int, 'step': int, 'is_baked': bool, 'disk': bool,
              'external': bool, 'name': str, 'is_baking': bool, 'is_outdated': bool, 'info': str,
              'filepath': str, 'library_path': bool, 'index': int}
    need(set(row) == set(fields) and all(type(row[k]) is kind for k,kind in fields.items())
         and row['pointer'] > 0, 'Actual complete typed PointCache14 required; Unknown rejected')
    return row


def local_sealed(row):
    return row['is_baked'] is True and row['is_baking'] is False and row['disk'] is False and row['external'] is False


def manual_cache_transition(before, after):
    """Only typed native dirty status may change; no payload-preservation claim."""
    fields = {'pointer': int, 'start': int, 'end': int, 'step': int, 'is_baked': bool, 'disk': bool,
              'external': bool, 'name': str, 'is_baking': bool, 'is_outdated': bool, 'info': str,
              'filepath': str, 'library_path': bool, 'index': int}
    typed = all(type(row) is dict and set(row) == set(fields)
                and all(type(row[key]) is kind for key,kind in fields.items())
                and row['pointer'] > 0 for row in (before,after))
    changes = ({key: {'before': before[key], 'after': after[key]}
                for key in fields if before[key] != after[key]} if typed else None)
    protected = typed and all(before[key] == after[key] for key in fields if key != 'is_outdated')
    dirty_allowed = typed and not (before['is_outdated'] is True and after['is_outdated'] is False)
    sealed = typed and local_sealed(before) and local_sealed(after)
    return {'scope': 'Native dirty status only; thirteen seal/configuration fields exact',
            'admissible': bool(protected and dirty_allowed and sealed), 'typed_complete': typed,
            'protected13_exact': bool(protected), 'cache14_exact': before == after,
            'native_dirty_transition_allowed': bool(dirty_allowed), 'local_sealed': bool(sealed),
            'changed_fields': changes, 'cache_content_preserved': 'Unproven',
            'cache_payload_verified': False, 'accepted': False}


def observe_enabled_owned_cloth(cloth, read):
    """Private write/read/restore window, not a public mode switch or read-only operation."""
    flags = (cloth.show_viewport, cloth.show_render)
    need(all(type(value) is bool for value in flags), 'Native owned Cloth flags unresolved')
    try:
        cloth.show_viewport = cloth.show_render = True
        return read()
    finally:
        cloth.show_viewport, cloth.show_render = flags


BODY = '''
        report.update(stage='CURRENT_ARTIST_DIRECT_SEALED_MANUAL_BAKE52_V2',case='sealed_manual_bake',
            scope='Fresh cold Direct; two public ten-frame simulation bakes with sealed Manual and explicit Reset checks',
            motion_recipe=None,native_bake_check_completed=False,actual_bake_range=[1,10],public_bake_count=0,
            legacy_completion_field_scope='native_motion_collection_completed means only generic adapter completion; no motion recipe or performance acceptance',
            collision_accepted=False,naturalness_accepted=False,cache_content_preserved='Unproven',
            native_dirty_policy='Only typed bool same/False-to-True; protected13 exact; sampled frame10 C exact; payload Unproven',
            previous_failed_QA={'path':str(_OLD_QA),'sha256':_OLD_QA_SHA},
            previous_failed_report={'path':str(_FAILED_REPORT),'sha256':_FAILED_REPORT_SHA,'upgraded_to_PASS':False})
        need(not args.render, 'No render or collision/naturalness test in this component')
        installed = physics.add_physics(context,source,backend=direct.BACKEND,body=body,capability='BOTH')
        installed,actual_rig,c,cloth = physics.validate_physics(source)
        need(actual_rig == rig and installed['physics']['backend'] == direct.BACKEND, 'Actual public Direct installation differs')
        tuning.apply(context,[source],mode='AUTOMATIC')
        installed,_,c,cloth = physics.validate_physics(source)
        input_obj = bpy.data.objects[installed['physics']['surface']['roles']['INPUT_SURFACE'][0]]
        need(input_obj.modifiers[1].is_bound and c.modifiers[1].is_bound, 'Fresh native BodySD binding unavailable')
        metres = home.unit_settings.scale_length
        need(math.isfinite(metres) and metres > 0., 'Actual metre scale unresolved')
        if animation is not None:
            animation.action = None
            for track,_mute,_solo in old_nla: track.mute,track.is_solo = True,False
        home.tool_settings.use_keyframe_insert_auto = False
        report['input_scope'] = {'Dress_keys_created':0,'Actions_created':0,'author_actions_temporarily_detached':old_action is not None,
            'author_pose_not_neutralized':True,'timeline_motion_recipe':None,'private_cache_only':True}
        report['native_parameters'] = {'settings':q.simple_rna(cloth.settings),'collision':q.simple_rna(cloth.collision_settings)}
        report['samples'] = []
        def sample(label):
            budget(); context.view_layer.update(); graph = context.evaluated_depsgraph_get()
            meshes = {name:diag.mesh_snapshot(obj,graph) for name,obj in (('input800',input_obj),('C800',c),('final3040',source))}
            need([len(meshes[n]['points']) for n in meshes] == [800,800,3040]
                 and len(meshes['final3040']['triangles']) == 5760
                 and all(math.isfinite(v) for mesh in meshes.values() for point in mesh['points'] for v in point),
                 'Finite native actual index/topology counts differ')
            row = {'label':label,'frame':[home.frame_current,home.frame_subframe], 'cache':_CACHE14(cloth,q),
                'state':direct._state(source,installed),'Cloth_flags':[cloth.show_viewport,cloth.show_render],
                'preview_socket':direct._mode_input(direct._overlay(source,installed),installed['physics']['surface']['mode_socket']).value,
                'geometry':{name:{'vertices':len(m['points']),'triangles':len(m['triangles']),
                    'points_float32_sha256':hashlib.sha256(q.pack(m['points']).tobytes()).hexdigest()} for name,m in meshes.items()},
                'accepted':False,'cache_content_preserved':'Unproven'}
            report['samples'].append(row); write()
            return meshes,row
        def guard_snapshot(label):
            meshes,row = sample(label)
            return {'receipt':cold.receipt(bpy,p,q,direct,source,rig,body),'cache':row['cache'],
                    'state':copy.deepcopy(row['state']),'flags':list(row['Cloth_flags']),
                    'preview_socket':row['preview_socket'],'meshes':meshes}
        def equal_guard(before,after,label):
            errors = {n:cold.error(before['meshes'][n]['points'],after['meshes'][n]['points'],metres) for n in before['meshes']}
            topology = all(before['meshes'][n]['edges'] == after['meshes'][n]['edges']
                and before['meshes'][n]['faces'] == after['meshes'][n]['faces'] for n in before['meshes'])
            row = {'label':label,'receipt_exact':before['receipt'] == after['receipt'],
                'first_difference':cold.first_difference(before['receipt'],after['receipt']),
                'cache14_exact':before['cache'] == after['cache'],'state_exact':before['state'] == after['state'],
                'flags_exact':before['flags'] == after['flags'],'preview_socket_exact':before['preview_socket'] == after['preview_socket'],
                'geometry_error':errors,'topology_exact':topology,'accepted':False}
            report.setdefault('unchanged_guards',[]).append(row); write()
            need(row['receipt_exact'] and row['cache14_exact'] and row['state_exact'] and row['flags_exact'] and row['preview_socket_exact']
                 and topology and all(error['maximum_m'] == 0. for error in errors.values()),
                 'Rejected action/private C window changed protected data/cache/context/geometry: '+label)
        def reject_bake(label,reason):
            before = guard_snapshot(label+'_before'); iterator = physics.bake_steps(context,source,1,10,'SIMULATION')
            exception = None
            try:
                next(iterator)
            except (ValueError,RuntimeError) as exc: exception = repr(exc); need(reason in str(exc), 'Unexpected public Bake rejection reason')
            finally: iterator.close()
            after = guard_snapshot(label+'_after')
            report.setdefault('early_Bake_rejections',[]).append({'label':label,'first_next_exception':exception,'before_cache':before['cache'],
                'after_cache':after['cache'],'first_next_rejected':exception is not None,'accepted':False}); write()
            equal_guard(before,after,label); need(exception is not None, 'Public Bake advanced instead of refusing before writes')
        def bake(label):
            budget(); iterator = physics.bake_steps(context,source,1,10,'SIMULATION'); progress=[]; result=None
            try:
                while True:
                    budget()
                    try: progress.append(next(iterator))
                    except StopIteration as done: result=done.value; break
            finally: iterator.close()
            need(len(progress) == 10 and [r[0] for r in progress] == list(range(1,11))
                 and all(r[1] == 10 for r in progress) and result['kind'] == 'SIMULATION' and result['frames'] == 10,
                 'Public sequential Bake did not really complete ten steps')
            report['public_bake_count'] += 1
            report.setdefault('public_bakes',[]).append({'label':label,'result':result,'progress':progress,'cache':_CACHE14(cloth,q),'accepted':False}); write()
            need(_LOCAL_SEALED(_CACHE14(cloth,q)), 'Actual local native cache did not become sealed')
            home.frame_set(10); return sample(label+'_sealed_frame10')
        reset = physics.reset_simulation(context,source)
        need(reset['start'] == 1 and not reset['is_baked'], 'Actual new cache must start at frame1')
        initial,initial_row = bake('initial')
        sealed_cache = copy.deepcopy(initial_row['cache'])
        # No disabled-Cloth instrumentation occurs before this clean public boundary.
        def manual_boundary(label):
            row = {'label':label,'state':copy.deepcopy(direct._state(source,installed)),
                'Cloth_flags':[cloth.show_viewport,cloth.show_render],'cache':_CACHE14(cloth,q),
                'frame':[home.frame_current,home.frame_subframe],
                'context':{'scene':context.scene.name,'mode':context.mode,
                    'active':q.id_name(context.view_layer.objects.active),
                    'selected':sorted(obj.name for obj in context.selected_objects)},
                'view_layer_update_or_mesh_read_performed':False,'cache_content_preserved':'Unproven','accepted':False}
            report.setdefault('clean_Manual_boundary',[]).append(row); write()
            return row
        clean_pre = manual_boundary('clean_preManual')
        need(clean_pre['cache'] == sealed_cache and clean_pre['state']['mode'] == 'AUTOMATIC'
             and clean_pre['state']['pending'] is False and clean_pre['Cloth_flags'] == [True,True],
             'Clean public Manual baseline differs from initial seal')
        tuning.apply(context,[source],mode='MANUAL')
        clean_post = manual_boundary('clean_postManual_before_sample')
        post_transition = _MANUAL_TRANSITION(sealed_cache,clean_post['cache'])
        report['clean_Manual_transition'] = {'initial_cache14':copy.deepcopy(sealed_cache),
            'immediate_native_result':post_transition,'native_dirty_status_is_not_cache_payload':True,'accepted':False}; write()
        need(clean_post['state']['pending'] is True and clean_post['state']['mode'] == 'MANUAL'
             and clean_post['Cloth_flags'] == [False,False]
             and clean_post['frame'] == clean_pre['frame'] and clean_post['context'] == clean_pre['context'],
             'Sealed Manual state/flags/frame/context did not transition correctly')
        need(post_transition['admissible'], 'Sealed Manual changed protected seal/configuration or unsupported dirty status')
        manual_before,manual_row = sample('manual_visible_surface_before_edit')
        sampled_post = manual_boundary('clean_postManual_after_sample')
        sample_transition = _MANUAL_TRANSITION(clean_post['cache'],sampled_post['cache'])
        initial_transition = _MANUAL_TRANSITION(sealed_cache,sampled_post['cache'])
        report['clean_Manual_transition'].update(sample_evaluation_result=sample_transition,
            initial_to_sampled_result=initial_transition,
            postManual_cache14_baseline=copy.deepcopy(sampled_post['cache']),
            baseline_scope='Observed post-Manual current14 only for subsequent no-write checks; initial14 retained above'); write()
        need(sample_transition['admissible'] and initial_transition['admissible']
             and manual_row['cache'] == sampled_post['cache'] and sampled_post['state'] == clean_post['state']
             and sampled_post['Cloth_flags'] == [False,False] and sampled_post['frame'] == clean_pre['frame']
             and sampled_post['context'] == clean_pre['context'],
             'Manual evaluation changed protected seal/configuration/state/context')
        manual_cache = copy.deepcopy(sampled_post['cache'])
        hem = rig.pose.bones[installed['controls']['hem']]
        hem.location = Vector(hem.location)+Vector((installed['fit']['height_world']*.005,0.,0.))
        manual_after,edited_row = sample('manual_visible_surface_after_edit')
        input_delta = cold.error(manual_before['input800']['points'],manual_after['input800']['points'],metres)
        report['Manual_visible_input_edit'] = {'input_error':input_delta,
            'final_error':cold.error(manual_before['final3040']['points'],manual_after['final3040']['points'],metres),
            'C_is_disabled_preCloth_input_not_cached_output':True,'accepted':False}; write()
        need(input_delta['maximum_m'] > 1.e-6 and edited_row['cache'] == manual_cache,
             'Manual input did not really change or sealed native cache metadata changed')
        before = guard_snapshot('pending_Automatic_before'); exception=None
        try: tuning.apply(context,[source],mode='AUTOMATIC')
        except (ValueError,RuntimeError) as exc:
            exception=repr(exc); need('Reset the simulation explicitly before resuming Automatic' in str(exc), 'Unexpected pending Automatic rejection')
        after = guard_snapshot('pending_Automatic_after')
        report['pending_Automatic_rejection']={'exception':exception,'accepted':False}; write()
        equal_guard(before,after,'pending_Automatic'); need(exception is not None,'Pending Automatic was accepted')
        reject_bake('manual_pending_Bake','Reset the Direct Dress simulation and return to Automatic before baking')
        before = guard_snapshot('private_C_window_before')
        window={'scope':'Private owned Cloth flags WRITE/read/restore only, no Auto/Reset/free/seek; source GN stays Manual',
            'before_cache':before['cache'],'before_state':before['state'],'before_flags':before['flags'],
            'before_frame':[home.frame_current,home.frame_subframe],'cache_content_preserved':'Unproven','accepted':False}
        report['private_enabled_C_observation']=window; write()
        observed,_observed_row = _OBSERVE_C(cloth,lambda:sample('private_enabled_C_observation'))
        after = guard_snapshot('private_C_window_after')
        window.update(after_cache=after['cache'],after_state=after['state'],after_flags=after['flags'],
            after_frame=[home.frame_current,home.frame_subframe],
            sampled_sealed_C_error=cold.error(initial['C800']['points'],observed['C800']['points'],metres)); write()
        equal_guard(before,after,'private_C_window')
        need(_observed_row['preview_socket'] is False and _observed_row['state']['mode'] == 'MANUAL'
             and _observed_row['cache'] == before['cache'] and window['sampled_sealed_C_error']['maximum_m'] == 0.,
             'Private observed sealed C/GN/state/cache differs; payload preservation unproven')
        # Only this explicit Reset is permitted to release the private seal.
        reset = physics.reset_simulation(context,source)
        installed,_,c,cloth = physics.validate_physics(source)
        report['explicit_Reset']={'result':reset,'cache':_CACHE14(cloth,q),'state':direct._state(source,installed),
            'frame':[home.frame_current,home.frame_subframe],'saved_baked_range':installed['physics']['baked_range'],'intent':'Explicit private QA Reset frees its own bake','accepted':False}; write()
        need(reset['start'] == 1 and not reset['is_baked'] and not direct._state(source,installed)['pending']
             and installed['physics']['baked_range'] is None, 'Explicit Reset did not really clear pending/private seal')
        tuning.apply(context,[source],mode='AUTOMATIC')
        rebaked,rebaked_row = bake('edited_input_rebake')
        final_response = cold.error(initial['final3040']['points'],rebaked['final3040']['points'],metres)
        report['explicit_rebake_response']={'input_error':cold.error(initial['input800']['points'],rebaked['input800']['points'],metres),
            'final_error':final_response,'sampled_frame':10,'collision_or_naturalness_accepted':False}; write()
        need(final_response['maximum_m'] > 1.e-6 and rebaked_row['state']['mode'] == 'AUTOMATIC'
             and not rebaked_row['state']['pending'], 'Actual edited input did not affect final output after explicit rebake')
        # The intentionally disabled probe is last, after the real second Bake.
        # Its instrumentation may dirty status; only first-next before/after is a no-write test.
        original_flags = (cloth.show_viewport,cloth.show_render)
        disabled_pre = _CACHE14(cloth,q)
        try:
            cloth.show_viewport = cloth.show_render = False
            reject_bake('disabled_Cloth','Direct editing preview and Cloth output states differ')
        finally: cloth.show_viewport,cloth.show_render = original_flags
        report['disabled_Cloth_instrumentation'] = {'before_flags':list(original_flags),
            'restored_flags':[cloth.show_viewport,cloth.show_render], 'before_cache14':disabled_pre,
            'after_flags_restore_cache14':_CACHE14(cloth,q),'payload_verified':False,'accepted':False}; write()
        need((cloth.show_viewport,cloth.show_render) == original_flags, 'Last disabled-Cloth probe flags not restored')
        report['native_bake_check_completed'] = True
        report['native_motion_collection_completed'] = True
'''


def prepared_namespace(provider_sha, cold_report, cold_report_sha):
    adapter = load_adapter()
    namespace,base,_tail_run,main,_changes = adapter.prepared_namespace(provider_sha,cold_report,cold_report_sha)
    original = ast.parse(inspect.getsource(base.run_motion)).body[0]
    run = copy.deepcopy(original)
    target = next(node for node in run.body if isinstance(node,ast.Try))
    target.body = ast.parse(inspect.cleandoc(BODY)).body
    run_source = ast.unparse(ast.fix_missing_locations(run))
    original_main = main
    main = main.replace("choices=('abrupt_stop_turn',),default='abrupt_stop_turn'", "choices=('sealed_manual_bake',),default='sealed_manual_bake'")
    main = main.replace('CURRENT_ARTIST_CANONICAL_DIRECT_COLD_STOP_SETTLING_TAIL52','CURRENT_ARTIST_DIRECT_SEALED_MANUAL_BAKE52_V2')
    main = main.replace('Original stop60 unchanged, append fixed actual f60 pose/input61..134; Body12Key restore retained; not naturalness acceptance',
                        'Actual sealed-cache/Manual/explicit Reset private component; no stop60 or motion/naturalness evidence')
    main = main.replace('Original frozen source/provider/cold dependencies retained; current canonical drift must reject until Root reviews a new frozen successor',
                        'Explicit fresh completed Cold and provider pins mandatory; preserved full source/Artist gates decide readiness')
    marker = '; pins.update({_TAIL_BASE:_TAIL_BASE_SHA,_TAIL_STOP_REPORT:_TAIL_STOP_REPORT_SHA})'
    need(main.count(marker) == 1, 'Actual inherited main pin ABI differs')
    main = main.replace(marker,marker+'; pins.update({_SEALED_ADAPTER:_SEALED_ADAPTER_SHA,_SEALED_TAIL:_SEALED_TAIL_SHA,_SEALED_PHYSICS:_SEALED_PHYSICS_SHA,_OLD_QA:_OLD_QA_SHA,_FAILED_REPORT:_FAILED_REPORT_SHA})')
    namespace.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,copy=copy,
        _CACHE14=cache14,_LOCAL_SEALED=local_sealed,_OBSERVE_C=observe_enabled_owned_cloth,
        _MANUAL_TRANSITION=manual_cache_transition,_OLD_QA=OLD_QA,_OLD_QA_SHA=OLD_QA_SHA,
        _FAILED_REPORT=FAILED_REPORT,_FAILED_REPORT_SHA=FAILED_REPORT_SHA,
        _SEALED_ADAPTER=ADAPTER,_SEALED_ADAPTER_SHA=ADAPTER_SHA,_SEALED_TAIL=adapter.TAIL,
        _SEALED_TAIL_SHA=adapter.TAIL_SHA,_SEALED_PHYSICS=PHYSICS,_SEALED_PHYSICS_SHA=PHYSICS_SHA)
    exec(compile(run_source+'\n'+main,str(Path(__file__).resolve()),'exec'),namespace)
    return namespace,base,original,run,original_main,main


def pure_checks():
    import types
    module = prepared_namespace('a'*64,HERE/'future_actual_Cold'/'report.json','b'*64)
    namespace,base,original,current,_old_main,_main = module
    old_try=next(n for n in original.body if isinstance(n,ast.Try)); new_try=next(n for n in current.body if isinstance(n,ast.Try))
    need(ast.dump(ast.Module(body=old_try.finalbody,type_ignores=[])) == ast.dump(ast.Module(body=new_try.finalbody,type_ignores=[])),
         'Original author/Body12 exact finally differs')
    need(ast.dump(ast.Module(body=original.body[:original.body.index(old_try)],type_ignores=[]))
         == ast.dump(ast.Module(body=current.body[:current.body.index(new_try)],type_ignores=[])), 'Original raw/Rest/Body12 capture prefix differs')
    need(namespace['run_motion'].__globals__ is namespace and namespace['main'].__globals__ is namespace
         and namespace['restore_body_coordinates'] is base.restore_body_coordinates,'Actual globals/Body restore identity differs')
    for failure in (False,True):
        cloth=types.SimpleNamespace(show_viewport=False,show_render=False); calls=[]
        def read():
            calls.append((cloth.show_viewport,cloth.show_render))
            if failure: raise ValueError('injected read failure')
            return 'native positions'
        try: observe_enabled_owned_cloth(cloth,read)
        except ValueError: need(failure,'Unexpected read error')
        need(calls == [(True,True)] and (cloth.show_viewport,cloth.show_render) == (False,False), 'Private window finally did not restore flags')
    row={'pointer':1,'start':1,'end':10,'step':1,'is_baked':True,'disk':False,'external':False,'name':'',
         'is_baking':False,'is_outdated':False,'info':'sealed','filepath':'','library_path':False,'index':0}
    fake=types.SimpleNamespace(point_cache=types.SimpleNamespace(**row,use_library_path=False))
    q=types.SimpleNamespace(cache_state=lambda cloth:{k:row[k] for k in ('pointer','start','end','step','is_baked','disk','external','name')})
    need(cache14(fake,q)==row and local_sealed(row),'Complete native-typed sealed memory rejected')
    for key in ('disk','external','is_baking'):
        need(not local_sealed(dict(row,**{key:True})),'Foreign/storage/active cache accepted: '+key)
    need(not local_sealed(dict(row,is_baked=False)),'Unsealed cache accepted')
    fake.point_cache.is_baking='Unknown'
    try: cache14(fake,q)
    except RuntimeError: pass
    else: need(False,'Unknown native field admitted')
    witness=json.loads(FAILED_REPORT.read_text(encoding='utf-8'))
    initial_cache=witness['samples'][0]['cache']; dirty_cache=witness['samples'][1]['cache']
    proof=manual_cache_transition(initial_cache,dirty_cache)
    need(proof['admissible'] and not proof['cache14_exact'] and proof['protected13_exact']
         and set(proof['changed_fields']) == {'is_outdated'} and proof['cache_content_preserved']=='Unproven',
         'Actual old instrumentation dirty witness misclassified')
    for before_dirty,after_dirty in ((False,False),(False,True),(True,True)):
        need(manual_cache_transition(dict(row,is_outdated=before_dirty),dict(row,is_outdated=after_dirty))['admissible'],
             'Typed same/False-to-True dirty rejected')
    negatives=0
    for key,value in row.items():
        if key=='is_outdated': continue
        changed = not value if type(value) is bool else value+1 if type(value) is int else value+'changed'
        need(not manual_cache_transition(row,dict(row,**{key:changed}))['admissible'], 'Protected13 drift admitted: '+key)
        negatives+=1
    for after_dirty in ('Unknown',None,0):
        need(not manual_cache_transition(row,dict(row,is_outdated=after_dirty))['admissible'], 'Unknown dirty type admitted')
        negatives+=1
    need(not manual_cache_transition(dict(row,is_outdated=True),row)['admissible'], 'Dirty True-to-False admitted'); negatives+=1
    for altered in ({k:v for k,v in row.items() if k!='info'},dict(row,new_unknown=False),dict(row,pointer=0)):
        need(not manual_cache_transition(row,altered)['admissible'], 'Incomplete/extra/invalid native cache admitted'); negatives+=1
    need(BODY.index("clean_preManual") < BODY.index("tuning.apply(context,[source],mode='MANUAL')")
         < BODY.index("clean_postManual_before_sample") < BODY.index("manual_visible_surface_before_edit")
         and BODY.index("bake('edited_input_rebake')") < BODY.index("reject_bake('disabled_Cloth'")
         and "_observed_row['cache'] == before['cache']" in BODY and "sampled_sealed_C_error']['maximum_m'] == 0." in BODY,
         'Clean boundary/order/private C original strict gate differs')
    physics_ast=ast.parse(PHYSICS.read_text(encoding='utf-8-sig'))
    bake=next(n for n in physics_ast.body if isinstance(n,ast.FunctionDef) and n.name=='bake_steps')
    lines={name:min(n.lineno for n in ast.walk(bake) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr==name)
           for name in ('require_bake_ready','frame_set')}
    clear=min(n.lineno for n in ast.walk(bake) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='clear_cache')
    need(lines['require_bake_ready'] < min(clear,lines['frame_set']), 'Actual public bake readiness guard is after native writes')
    provider=ast.parse(namespace['PROVIDER'].read_text(encoding='utf-8-sig'))
    for name,count in (('validate',3),('set_mode',3),('require_bake_ready',2),('reset_completed',3),('_mode_input',2),('_overlay',2)):
        function=next(n for n in provider.body if isinstance(n,ast.FunctionDef) and n.name==name)
        need(len(function.args.args)==count,'Actual provider positional ABI differs: '+name)
    need("range(1,11)" in BODY and 'motion_recipe=None' in BODY and "private_enabled_C_observation" in BODY,
         'Bounded bake scope/explicit private observation missing')
    print(json.dumps({'source_prepared':True,'Native_READY':False,'native_executed':False,
        'original_Body12_capture_and_finally_AST_exact':True,'private_flag_window_success_failure_restore':True,
        'actual_public_bake_guard_before_clear_seek':True,'actual_provider_ABI_functions':6,
        'actual_old_dirty_witness':True,'protected13_and_dirty_negative_controls':negatives,
        'metadata14_exact_not_claimed_for_dirty_transition':True,'old_failed_report_upgraded':False,
        'fresh_Cold_report_created':False,'actual_bake_range':[1,10],'no_collision_naturalness_export_acceptance':True}))


def main():
    adapter=load_adapter(); separator=sys.argv.index('--')+1 if '--' in sys.argv else 1
    tokens=sys.argv[separator:]; options=('--expected-provider-sha','--cold-report','--cold-report-sha')
    need(all(sum(t.split('=',1)[0]==o for t in tokens)==1 for o in options),'Explicit provider/real Cold report pins required exactly once')
    parser=argparse.ArgumentParser(add_help=False,allow_abbrev=False)
    parser.add_argument('--expected-provider-sha',required=True); parser.add_argument('--cold-report',type=Path,required=True)
    parser.add_argument('--cold-report-sha',required=True)
    args,remaining=parser.parse_known_args(tokens)
    adapter.validate_dependencies(args.expected_provider_sha,args.cold_report,args.cold_report_sha)
    need(args.cold_report.is_file() and sha(args.cold_report)==args.cold_report_sha,'Actual fresh Cold report missing/differs')
    namespace,*_rest=prepared_namespace(args.expected_provider_sha,args.cold_report,args.cold_report_sha)
    original_argv=sys.argv
    try:
        sys.argv=original_argv[:separator]+remaining
        return namespace['main']()
    finally: sys.argv=original_argv


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
