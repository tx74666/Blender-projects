"""SOURCE_PREPARED v5: public FK entry on a fresh owned saved-disk Scene.

The v4 actual failure did not call Body IK/FK switching. This successor captures
the current modes, invokes the real public switch and restores its checkpoint.
No originally-FK claim, source-cache operation or public runtime change.
Current source input is re-prepared for the Tuning readiness fix; the frozen v4
runtime is historical evidence, with no runtime-equivalence claim.
The new saved-copy input has only filesystem/SDNA evidence. Controls, FK and
cache safety remain unverified until the actual Native preflight.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace as NS

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
RUNTIME=Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer')
PREVIOUS=HERE/'verify_direct_native_warm_start52_v4.py'
PREVIOUS_SHA='014cc5ed63a64709d8927a10585e9ee2b2063ad2af0a35b9945e5e901f1de685'
FAILED=HERE/'actual_direct_native_warm_start_v4_52_20261008_151854_163_a90ae4180a914d4aaffeed47d9aa4e3d/result/report.json'
FAILED_SHA='a9b36ada206de8387c6dcf7c293de01bc55bf8d88995400e82f17face678d2f6'
NEW_PINS={RUNTIME/'limb_ik_fk_batch.py':'4e55f888471ffeb13aa69fe6d444772e08fdbe36c04ca51d48e2ee7deb671669',
          RUNTIME/'body_setup_transaction.py':'13d5b4c489d6ead3d9b40d8468d9019f8422ba37f35328917decc755a231f4a3'}
CURRENT_PIN_OVERRIDES={'skirt_motion_tuning.py':dict(
    historical_sha256='95fe79380b63f2b424f1df60f8b26f9a4ad4a54119fcc3eb4f2e83547e21f3ea',
    current_sha256='fa9c7d3b05c0ca6989b61387edb0ab52a9ffe4525c8c14f199222e101966f2e1')}
NEW_PINS.update({RUNTIME/name:entry['current_sha256'] for name,entry in CURRENT_PIN_OVERRIDES.items()})
HISTORICAL_INPUT_PINS=dict(
    INPUT=HERE/'private_current_controls_input_20261008_140155_539_56f2fda074bc44a1b195a3e6ea21fb54/X.controls-only-input.blend',
    INPUT_SHA='5bf64e5463fc46c625b5796852666fce251e2c0cd25dbe8aa39427a964df7812',
    INPUT_RECEIPT=HERE/'private_current_controls_input_20261008_140155_539_56f2fda074bc44a1b195a3e6ea21fb54/input-receipt.json',
    INPUT_RECEIPT_SHA='81b0984aa604402cdd9f25f610b036d0a10f44e7daa357a097761d63be9933f3')
FRESH_INPUT_DIRECTORY=HERE/'private_saved_input_20261008_181852_135_49beaefcb07040dda907599d2118b163'
CURRENT_INPUT_PINS=dict(INPUT=FRESH_INPUT_DIRECTORY/'X.saved-input.blend',
    INPUT_SHA='377140234b0354966d8e3ac4776aa936fd0921aacc53be630cac3b040727ff8d',
    INPUT_RECEIPT=FRESH_INPUT_DIRECTORY/'input-receipt.json',
    INPUT_RECEIPT_SHA='fb1ed14128515864c991626303a4f6b92fb506448ca6598b3f169e9aa7e2a39f')
INPUT_METADATA=FRESH_INPUT_DIRECTORY/'source-file-metadata.json'
INPUT_METADATA_SHA='f93c44ba0b7c6506ae3106467c990009ff794b9f0fedc300097dab6e42626bf7'
AUTHOR_FIELDS=('raw_Dress','raw_Body','Rest','pose','pose_position','constraints','drivers','bindings',
    'Body_Key_channels','Body_Key_binding','Body_data_users','charts','frame','mode','active','selected',
    'active_bone','bone_selection','bone_collections')


def need(value,message):
    if not value: raise RuntimeError('NativeWarmStartPublicFK52: '+message)


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,
                                    separators=(',',':')).encode()).hexdigest()


def current_source_parent(module):
    # Only this v5 privately loaded parent chain uses the re-prepared input.
    # Frozen file bytes and the original dictionary object remain unchanged.
    if hasattr(module,'CURRENT_PINS'):
        historical=module.CURRENT_PINS
        need(all(historical.get(name)==entry['historical_sha256']
                 for name,entry in CURRENT_PIN_OVERRIDES.items()),'Historical current-pin basis changed')
        need(all(getattr(module,name,None)==value for name,value in HISTORICAL_INPUT_PINS.items()),
             'Historical saved-input basis changed')
        module.CURRENT_PINS={**historical,**{name:entry['current_sha256']
                                           for name,entry in CURRENT_PIN_OVERRIDES.items()}}
        for name,value in CURRENT_INPUT_PINS.items():
            setattr(module,name,value)
    else:
        frozen_previous=module.previous
        module.previous=lambda:current_source_parent(frozen_previous())
    return module


def input_preparation():
    need(hashlib.sha256(INPUT_METADATA.read_bytes()).hexdigest()==INPUT_METADATA_SHA,
         'Fresh saved-input filesystem metadata changed')
    row=json.loads(INPUT_METADATA.read_text(encoding='utf-8'))
    need(Path(row['inputPath']).resolve()==CURRENT_INPUT_PINS['INPUT'].resolve()
         and row['inputSha256']==CURRENT_INPUT_PINS['INPUT_SHA'] and row['inputLength']==32393300
         and Path(row['inputReceiptPath']).resolve()==CURRENT_INPUT_PINS['INPUT_RECEIPT'].resolve()
         and row['inputReceiptSha256']==CURRENT_INPUT_PINS['INPUT_RECEIPT_SHA']
         and len(row['sceneRecords'])==1 and row['sceneRecords'][0]['sceneName']=='Scene'
         and all(row['verification'][name] is True for name in
                 ('inputBeforeAfterStatExact','inputStreamedHashExact','inputReceiptExact','sdnaDerivedFromThisFile','completeStreamENDB'))
         and all(row['verification'][name] is False for name in
                 ('controlsOnlyNativeVerified','BodyFKNativeVerified','noStoredExternalCacheNativeVerified',
                  'liveUnsavedArtistIncluded','artistSaved','deployed','nativeExecuted')),
         'Fresh filesystem proof boundary differs; no Native state inferred')
    return dict(new_saved_disk_input=True,historical_input=str(HISTORICAL_INPUT_PINS['INPUT']),
        historical_input_sha256=HISTORICAL_INPUT_PINS['INPUT_SHA'],
        current_input=str(CURRENT_INPUT_PINS['INPUT']),current_input_sha256=CURRENT_INPUT_PINS['INPUT_SHA'],
        receipt=str(CURRENT_INPUT_PINS['INPUT_RECEIPT']),receipt_sha256=CURRENT_INPUT_PINS['INPUT_RECEIPT_SHA'],
        metadata=str(INPUT_METADATA),metadata_sha256=INPUT_METADATA_SHA,filesystem_metadata=row,
        historical_Native_state_acceptance_borrowed=False,Controls_FK_cache_Native_verified=False)


def previous():
    need(hashlib.sha256(PREVIOUS.read_bytes()).hexdigest()==PREVIOUS_SHA
         and hashlib.sha256(FAILED.read_bytes()).hexdigest()==FAILED_SHA,'Frozen v4/failure changed')
    failure=json.loads(FAILED.read_text(encoding='utf-8'))
    need(failure['native_component_verified'] is False and failure['native_stages_completed'] is False
         and failure['private_authored_before_registration_exact'] is True
         and failure['source_files_input_Artist_exact'] is True and failure['private_scene_disposed'] is True
         and failure['owned_native_input_preflight']['completed'] is True
         and failure['input_native_preflight']['completed'] is True
         and failure['actual_original_input']['correction_saved'] is True
         and all(failure['author_restore'][field] is True for field in AUTHOR_FIELDS if field!='constraints')
         and failure['author_restore']['raw_Rest_Actions']['success'] is True
         and not failure['author_restore']['errors'] and failure['errors']
         and 'samples' not in failure and 'seed_checks' not in failure
         and 'movement_plan' not in failure,'Preserve pre-leg FK-precondition failure and its actual restore evidence')
    spec=importlib.util.spec_from_file_location('warm_v4_frozen',PREVIOUS)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return current_source_parent(module)


def native_api():
    from character_designer import (limb_ik,limb_ik_fk,limb_ik_fk_batch,body_setup_transaction,
                                   bone_display,body_original_mode,forearm_twist)
    return NS(limb=limb_ik,match=limb_ik_fk,batch=limb_ik_fk_batch,properties=body_setup_transaction,
              display=bone_display,original=body_original_mode,forearm=forearm_twist)


def property_state(owner,key,api):
    values,ui=api.properties._properties(owner)
    present=key in owner
    need(not present or key in values and key in ui and type(ui[key]) is dict,
         'Target property/UI cannot be completely captured before public FK: '+key)
    result=dict(present=present,value=values.get(key),ui=ui.get(key))
    digest(result)  # Refuse unreadable/nonfinite proof before a public write.
    return result


def modes_and_ui(rig,inventory,api):
    result=[]
    for key in api.batch.LIMB_KEYS:
        entry=inventory['rigs'][key]; target=rig.pose.bones[entry['target'].name]
        result.append(dict(limb=key[0]+'.'+key[1],target=target.name,
            mode=api.match.mode_for_rig(rig,entry),
            property=property_state(target,api.match.PROPERTY,api),
            version=property_state(target.bone,api.match.VERSION_KEY,api)))
    return result


def require_restorable_shape(inventory,states,api):
    need(set(inventory['rigs'])==set(api.batch.LIMB_KEYS) and len(states)==4,
         'Exactly four installed native limb chains required for this public all-limb experiment')
    all_installed=all(row['version']['present'] and type(row['version']['value']) is int
                      and row['version']['value']==api.match.VERSION for row in states)
    need(inventory['schema'] in (api.limb.ROLL_DECOUPLED_SCHEMA,api.limb.DIRECT_PREROLL_SCHEMA)
         or inventory['schema']==api.limb.LEGACY_DIRECT_PREROLL_SCHEMA and all_installed,
         'Older/Unknown switching shape cannot be completely restored; refuse before public FK')
    for row in states:
        version,prop=row['version'],row['property']
        if version['present']:
            need(type(version['value']) is int and version['value']==api.match.VERSION and prop['present']
                 and type(prop['value']) in (int,float) and math.isfinite(prop['value'])
                 and 0.<=prop['value']<=1.,'Incomplete existing FK property/version')
        else:
            need(not prop['present'],'Unrelated FK property cannot be overwritten')


def author_read(bpy,cold,p,q,direct,source,rig,body,api):
    receipt=cold.receipt(bpy,p,q,direct,source,rig,body)
    result={key:receipt[key] for key in AUTHOR_FIELDS}
    result['pose_properties']={pb.name:{key:q.custom_content(pb[key]) for key in pb.keys()} for pb in rig.pose.bones}
    result['bone_properties']={bone.name:{key:q.custom_content(bone[key]) for key in bone.keys()} for bone in rig.data.bones}
    result['display']=p.primitive(api.display._snapshot(rig))
    digest(result)
    return result


def coordinate_proof(saved):
    return dict(identity=saved['identity'],base_sha256=hashlib.sha256(saved['base'].tobytes()).hexdigest(),
                key_sha256=[hashlib.sha256(values.tobytes()).hexdigest() for values in saved['blocks']])


def capture_fk(bpy,context,cold,p,q,direct,source,rig,body,capture_coordinates,restore_coordinates,report,write):
    entry=dict(status='UnknownCapture',public_called=False,public_finished=False,all_four_FK=False,
               originally_FK_assumed=False,capture_AuthorRestoration=None,rollback=None)
    report['Body_FK_transition']=entry; write()
    try:
        api=native_api()
        need(context.view_layer.objects.active==rig and context.mode in ('OBJECT','POSE')
             and context.scene==bpy.context.scene and rig.library is None and rig.override_library is None,
             'Owned MainRig must be active in its private Scene before public FK')
        need(api.batch._require(context,rig) is None and not api.original.active(rig),'Return to Controls before public FK')
        inventory=api.limb._validate_inventory(rig)
        need(set(inventory['rigs'])==set(api.batch.LIMB_KEYS),'Four installed limb inputs missing')
        states=modes_and_ui(rig,inventory,api); entry['before']=states; entry['schema']=inventory['schema']; write()
        require_restorable_shape(inventory,states,api)
        paths={con.path_from_id('influence') for item in inventory['rigs'].values()
               for pb,con,record in item['entries'] if api.match.is_switch_constraint(rig,pb,con,record)}
        checkpoint=api.batch._checkpoint(context,rig,None)
        need(len(checkpoint['rigs'])==1 and checkpoint['rigs'][0]['rig']==rig,'Unexpected checkpoint ownership')
        before=author_read(bpy,cold,p,q,direct,source,rig,body,api)
        coords=capture_coordinates(body); protection=q.Protection()
        proof=protection.verify(); need(proof['success'] is True,'Author asset capture failed before FK')
        saved=dict(api=api,checkpoint=checkpoint,states=states,inventory=inventory,paths=paths,
            author=before,coordinates=coords,coordinate_proof=coordinate_proof(coords),protection=protection,
            context=api.limb._capture_context(context,rig),frame=[context.scene.frame_current,context.scene.frame_subframe],
            autokey=context.scene.tool_settings.use_keyframe_insert_auto,
            nla=[] if rig.animation_data is None else [(track,track.mute,track.is_solo) for track in rig.animation_data.nla_tracks],
            readers=(bpy,cold,p,q,direct,source,rig,body),capture_coordinates=capture_coordinates,
            restore_coordinates=restore_coordinates)
        need(type(saved['autokey']) is bool,'Unknown Auto Key state')
        entry['capture_AuthorRestoration']=dict(status='Measured',field_sha256={key:digest(value) for key,value in before.items()},
            coordinates=saved['coordinate_proof'],raw_Rest_Actions=proof,target_UI=states,
            owned_switch_paths=sorted(paths),autokey=saved['autokey'])
        entry['status']='Captured'; write()
        return saved
    except Exception as error:
        entry['status']='UnknownCaptureFailed'; entry['capture_error']=repr(error); write(); raise


def public_fk(bpy,context,rig,saved,report,write):
    entry=report['Body_FK_transition']; api=saved['api']
    context.scene.tool_settings.use_keyframe_insert_auto=False
    entry['public_called']=True; entry['status']='PublicSwitchAttempted'; write()
    result=bpy.ops.character_designer.body_ik_fk_switch('EXEC_DEFAULT',mode='FK',keyframe=False)
    entry['public_result']=sorted(result); write()
    need('FINISHED' in result,'Public Body FK refused the owned copy; no direct FK assignment or fallback')
    inventory=api.limb._validate_inventory(rig)
    states=modes_and_ui(rig,inventory,api); entry['after']=states
    entry['actual_new_driver_paths']=sorted(curve.data_path for curve in
        (() if rig.animation_data is None else rig.animation_data.drivers)
        if curve.as_pointer() not in saved['checkpoint']['drivers'])
    need(all(path in saved['paths'] for path in entry['actual_new_driver_paths']),
         'Public FK created a driver outside current validated owned switching paths')
    entry['new_owned_driver_paths']=sorted(path for path in saved['paths']
        if api.match._find_driver(rig,path) is not None
        and api.match._find_driver(rig,path).as_pointer() not in saved['checkpoint']['drivers'])
    entry['public_finished']=True; entry['all_four_FK']=all(row['mode']=='FK' for row in states)
    entry['status']='PublicSwitchMeasured'; write()
    need(entry['all_four_FK'] and context.scene.tool_settings.use_keyframe_insert_auto is False,
         'Public switch did not leave all actual native limbs in FK with private Auto Key off')
    entry['author_assets_after_public']=saved['protection'].verify(); write()
    need(entry['author_assets_after_public']['success'] is True,'Public FK changed raw author assets')


def rollback_fk(context,rig,body,saved,report,write):
    if saved is None: return
    entry=report['Body_FK_transition']; api=saved['api']
    result=dict(status='UnknownReadFailed',completed=False,author_fields=None,raw_Rest_Actions=None,
                target_UI=None,coordinates=None,autokey=None,errors=[])
    entry['rollback']=result
    errors=result['errors']
    def attempt(label,callback):
        try: callback()
        except Exception as error: errors.append(dict(phase=label,error=repr(error)))
    attempt('initial_report_write',write)
    with api.forearm.defer_runtime(context,flush_on_exit=False):
        # Caller already paused only its newly installed private Cloth. Existing
        # frozen finally has restored Action/NLA before this checkpoint rollback.
        attempt('batch',lambda:api.batch._rollback(context,rig,saved['checkpoint'],saved['paths']))
        for before in saved['states']:
            target=rig.pose.bones[before['target']]
            for owner,key,state in ((target,api.match.PROPERTY,before['property']),
                                    (target.bone,api.match.VERSION_KEY,before['version'])):
                # Value/presence restoration belongs to real batch._rollback;
                # only captured UI metadata is restored here, never an FK value.
                if state['present']:
                    attempt('property_UI',lambda owner=owner,key=key,state=state:owner.id_properties_ui(key).update(**state['ui']))
        for track,mute,solo in saved['nla']:
            attempt('NLA_mute',lambda track=track,mute=mute:setattr(track,'mute',mute))
            attempt('NLA_solo',lambda track=track,solo=solo:setattr(track,'is_solo',solo))
        attempt('private_frame',lambda:context.scene.frame_set(saved['frame'][0],subframe=saved['frame'][1]))
        # Frame handlers may refresh managed display even with Cloth paused.
        attempt('display',lambda:api.display._restore(rig,saved['checkpoint']['rigs'][0]['display']))
        attempt('context',lambda:api.limb._restore_context(context,rig,saved['context']))
        attempt('Body12',lambda:saved['restore_coordinates'](body,saved['coordinates'],report,write))
        attempt('AutoKey',lambda:setattr(context.scene.tool_settings,'use_keyframe_insert_auto',saved['autokey']))
        try:
            actual=author_read(*saved['readers'],api)
            result['author_fields']={key:actual[key]==value for key,value in saved['author'].items()}
            result['actual_field_sha256']={key:digest(value) for key,value in actual.items()}
            result['raw_Rest_Actions']=saved['protection'].verify()
            actual_states=modes_and_ui(rig,api.limb._validate_inventory(rig),api)
            result['actual_target_UI']=actual_states; result['target_UI']=actual_states==saved['states']
            result['autokey']=context.scene.tool_settings.use_keyframe_insert_auto==saved['autokey']
            current_coordinates=saved['capture_coordinates'](body)
            result['actual_coordinates']=coordinate_proof(current_coordinates)
            result['coordinates']=result['actual_coordinates']==saved['coordinate_proof']
            result['completed']=not errors and all(result['author_fields'].values()) and result['raw_Rest_Actions']['success'] is True
            result['completed']=result['completed'] and result['target_UI'] and result['autokey'] and result['coordinates']
            result['status']='MeasuredRestored' if result['completed'] else 'MeasuredMismatch'
        except Exception as error:
            errors.append(dict(phase='AuthorRestorationRead',error=repr(error)))
        attempt('final_report_write',write)
        if errors:
            result['completed']=False
            if result['status']=='MeasuredRestored': result['status']='MeasuredRestoreReportFailed'
    need(result['completed'] is True,'Private FK checkpoint AuthorRestoration not exact; original finally must still run')


def prepared_namespace():
    owner=previous(); n,parent,original,changed=owner.prepared_namespace()
    n['_EXTRA_PINS'].update({PREVIOUS:PREVIOUS_SHA,FAILED:FAILED_SHA,INPUT_METADATA:INPUT_METADATA_SHA,**NEW_PINS})
    old=copy.deepcopy(changed); modified=copy.deepcopy(changed)
    target=next(node for node in modified.body if isinstance(node,ast.Try))
    index=next(index for index,node in enumerate(target.body) if isinstance(node,ast.Assign)
               and ast.unparse(node.value)=='q.body_inputs(rig, installed)')
    additions=ast.parse("""fk_saved=_FK_CAPTURE(bpy,context,cold,p,q,direct,source,rig,body,capture_body_coordinates,restore_body_coordinates,report,write)
_FK_PUBLIC(bpy,context,rig,fk_saved,report,write)
""").body
    target.body[index:index]=additions
    outer_index=next(index for index,node in enumerate(modified.body) if node is target)
    modified.body.insert(outer_index,ast.parse('fk_saved=None').body[0])
    paused=next(node for node in target.finalbody if isinstance(node,ast.With))
    location=next(index for index,node in enumerate(paused.body) if isinstance(node,ast.Expr)
                  and ast.unparse(node).startswith("restore('author_context_pose_frame_Keys'"))
    cleanup=ast.parse("restore('Body_FK_checkpoint',lambda:_FK_ROLLBACK(context,rig,body,fk_saved,report,write))").body[0]
    paused.body.insert(location,cleanup)
    reverse=copy.deepcopy(modified)
    reverse.body=[node for node in reverse.body if not (isinstance(node,ast.Assign)
                  and ast.unparse(node.targets[0])=='fk_saved')]
    reverse_try=next(node for node in reverse.body if isinstance(node,ast.Try))
    reverse_try.body=[node for node in reverse_try.body if not any(name in ast.unparse(node)
                      for name in ('_FK_CAPTURE','_FK_PUBLIC',"fk_saved['capture_coordinates']"))]
    reverse_paused=next(node for node in reverse_try.finalbody if isinstance(node,ast.With))
    reverse_paused.body=[node for node in reverse_paused.body if '_FK_ROLLBACK' not in ast.unparse(node)]
    need(ast.dump(reverse)==ast.dump(old),'Frozen v4 recipe/seed/contact/original finally changed')
    n.update(_FK_CAPTURE=capture_fk,_FK_PUBLIC=public_fk,_FK_ROLLBACK=rollback_fk,__file__=str(Path(__file__).resolve()))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[modified],type_ignores=[])),str(Path(__file__).resolve()),'exec'),n)
    return n,parent,original,modified


def namespace():
    owner=previous(); _,values,_,original=owner.namespace(); changed=copy.deepcopy(original)
    index=next(index for index,node in enumerate(changed.body) if isinstance(node,ast.Assign)
               and ast.unparse(node.targets[0])=='report')
    changed.body.insert(index+1,ast.parse("report['prior_failed_FK_precondition']={'runner':str(_FK_PREVIOUS),'runner_sha256':_FK_PREVIOUS_SHA,'report':str(_FK_FAILED),'report_sha256':_FK_FAILED_SHA,'preserved_failure':True,'public_switch_called_in_failed_attempt':False,'acceptance_borrowed':False}").body[0])
    changed.body.insert(index+2,ast.parse("report['source_input_preparation']={'new_source_input':True,'current_pin_updates':copy.deepcopy(_CURRENT_PIN_OVERRIDES),'saved_disk_input':_INPUT_PREPARATION(),'historical_runtime_equivalence_claimed':False,'native_acceptance_from_preparation':False}").body[0])
    for node in ast.walk(changed):
        if isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V4_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V5_52'
    reverse=copy.deepcopy(changed)
    reverse.body=[node for node in reverse.body if not (isinstance(node,ast.Assign)
                  and ast.unparse(node.targets[0]) in ("report['prior_failed_FK_precondition']","report['source_input_preparation']"))]
    for node in ast.walk(reverse):
        if isinstance(node,ast.Constant) and node.value=='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V5_52':
            node.value='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V4_52'
    need(ast.dump(reverse)==ast.dump(original),'Frozen outer main/load/write/cleanup changed')
    values.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,prepared_namespace=prepared_namespace,
                  _FK_PREVIOUS=PREVIOUS,_FK_PREVIOUS_SHA=PREVIOUS_SHA,_FK_FAILED=FAILED,_FK_FAILED_SHA=FAILED_SHA,
                  _CURRENT_PIN_OVERRIDES=CURRENT_PIN_OVERRIDES,_INPUT_PREPARATION=input_preparation)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[changed],type_ignores=[])),str(Path(__file__).resolve()),'exec'),values)
    return owner,values,original,changed


def main():
    _,values,_,_=namespace()
    return values['main']()


def pure_checks():
    import types
    from array import array
    from contextlib import nullcontext
    owner,values,original,changed=namespace(); owner.pure_checks()
    n,_,_,_=prepared_namespace(); n['base']=None
    need(not n['_MISSING_GLOBALS'](values['main']) and not n['_MISSING_GLOBALS'](n['run_motion']),
         'Actual v5 compiled closures incomplete')
    update=CURRENT_PIN_OVERRIDES['skirt_motion_tuning.py']
    historical={'skirt_motion_tuning.py':update['historical_sha256'],'untouched.py':'a'*64}
    endpoint=NS(CURRENT_PINS=historical,**HISTORICAL_INPUT_PINS)
    scoped=current_source_parent(NS(previous=lambda:endpoint)).previous()
    need(historical['skirt_motion_tuning.py']==update['historical_sha256']
         and scoped.CURRENT_PINS is not historical and scoped.CURRENT_PINS['untouched.py']==historical['untouched.py']
         and scoped.CURRENT_PINS['skirt_motion_tuning.py']==update['current_sha256'],
         'V5 current-input override mutated historical pins or unrelated endpoints')
    try: current_source_parent(NS(CURRENT_PINS={'skirt_motion_tuning.py':'b'*64}))
    except RuntimeError: pass
    else: need(False,'Unknown historical pin basis admitted')
    for name in HISTORICAL_INPUT_PINS:
        changed_input=dict(HISTORICAL_INPUT_PINS); changed_input[name]='Unknown'
        try: current_source_parent(NS(CURRENT_PINS=historical,**changed_input))
        except RuntimeError: pass
        else: need(False,'Unknown historical saved-input basis admitted: '+name)
    input_readers=(values['main'].__globals__,values['disk_inputs'].__globals__,
                   vars(values['_APPEND_SCENE'].__globals__['previous']()))
    need(all(all(reader[name]==value for name,value in CURRENT_INPUT_PINS.items()) for reader in input_readers)
         and all(getattr(scoped,name)==value for name,value in CURRENT_INPUT_PINS.items()),
         'Actual main/disk_inputs/append or private leaf retained historical input constants')
    preparation=input_preparation()
    need(preparation['filesystem_metadata']['sceneRecords'][0]['blockOffset']==2815649
         and preparation['Controls_FK_cache_Native_verified'] is False
         and preparation['historical_Native_state_acceptance_borrowed'] is False,
         'Fresh Scene proof or unverified Native state boundary lost')
    compiled=values['main'].__globals__['CURRENT_PINS']
    need(len(compiled)==40 and compiled['skirt_motion_tuning.py']==update['current_sha256']
         and compiled==values['CURRENT_PINS']
         and n['_EXTRA_PINS'][RUNTIME/'skirt_motion_tuning.py']==update['current_sha256'],
         'Actual compiled main or prepared closure retained the historical Tuning pin')
    for path,expected in NEW_PINS.items():
        need(hashlib.sha256(path.read_bytes()).hexdigest()==expected,'New current endpoint pin changed')
    # Execute real canonical property capture and batch checkpoint/rollback AST
    # on small native endpoints. No replacement transaction/simulation logic.
    class ID(dict):
        __hash__=object.__hash__
        def __init__(self,name):
            super().__init__(); self.name=name; self.ui={}
        def as_pointer(self): return id(self)
        def id_properties_ui(self,key):
            if key not in self.ui: raise RuntimeError('injected missing property UI')
            return NS(as_dict=lambda:copy.deepcopy(self.ui[key]),update=lambda **changes:self.ui[key].update(changes))
    class Driver:
        def __init__(self,pointer,path): self.pointer=pointer; self.data_path=path
        def as_pointer(self): return self.pointer
    constants=dict(PROPERTY='ik_fk',VERSION_KEY='character_designer_limb_ik_fk_version',VERSION=1)
    limb=NS(ROLL_DECOUPLED_SCHEMA=3,DIRECT_PREROLL_SCHEMA=5,LEGACY_DIRECT_PREROLL_SCHEMA=4)
    match=NS(**constants)
    fk_tree=ast.parse((RUNTIME/'limb_ik_fk.py').read_text(encoding='utf-8'))
    fk_env=dict(math=math)
    selected=[node for node in fk_tree.body if isinstance(node,ast.FunctionDef) and node.name in ('mode_for_rig','_find_driver')]
    fk_env.update(constants)
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<real-canonical-fk-read>','exec'),fk_env)
    match.mode_for_rig=fk_env['mode_for_rig']; match._find_driver=fk_env['_find_driver']; match._update=lambda *args:None
    batch_tree=ast.parse((RUNTIME/'limb_ik_fk_batch.py').read_text(encoding='utf-8'))
    names={'_copy_value','_properties','_restore_properties','_pose_checkpoint','_restore_pose','_checkpoint',
           '_restore_animation','_remove_staged','_rollback'}
    functions=[node for node in batch_tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    package=types.ModuleType('warm_fk_pure_endpoints'); previous_package=sys.modules.get(package.__name__)
    display={}; corrective={'value':1.25}
    package.body_original_mode=NS()
    package.body_rest_resync=NS(_corrective_checkpoint=lambda rig:[copy.deepcopy(corrective)],
        restore_correctives=lambda saved:corrective.update(saved['correctives'][0]))
    package.bone_collections=NS(_FRAME_CACHE={})
    package.bone_display=NS(_snapshot=lambda rig:copy.deepcopy(display),_restore=lambda rig,state:(display.clear(),display.update(state)))
    package.skirt_original_mode=NS(rollback=lambda *args:None)
    batch_env=dict(__package__=package.__name__,bpy=NS(types=NS(ID=ID)),match=match,
                   _CHANNELS=('location','rotation_euler','rotation_quaternion','rotation_axis_angle','scale'),
                   _LOCKS=('lock_rotation','lock_rotation_w','lock_rotations_4d'))
    sys.modules[package.__name__]=package
    try:
        exec(compile(ast.Module(body=functions,type_ignores=[]),'<real-canonical-batch>','exec'),batch_env)
        batch=NS(LIMB_KEYS=(('ARM','L'),('ARM','R'),('LEG','L'),('LEG','R')),
                 _checkpoint=batch_env['_checkpoint'],_rollback=batch_env['_rollback'],_require=lambda *args:None)
        prop_tree=ast.parse((RUNTIME/'body_setup_transaction.py').read_text(encoding='utf-8'))
        prop_function=next(node for node in prop_tree.body if isinstance(node,ast.FunctionDef) and node.name=='_properties')
        prop_env=dict(_encode=lambda value:value)
        exec(compile(ast.Module(body=[prop_function],type_ignores=[]),'<real-canonical-property-capture>','exec'),prop_env)
        api=NS(limb=limb,match=match,batch=batch,properties=NS(_properties=prop_env['_properties']),
               display=package.bone_display,forearm=NS(defer_runtime=lambda *args,**kwargs:nullcontext()),
               original=NS(active=lambda rig:False))
        ui={'min':0.,'max':1.,'default':1.,'description':'captured original'}
        rig=ID('Rig'); bones={}; poses={}; inventory=dict(schema=5,rigs={})
        for index,key in enumerate(batch.LIMB_KEYS):
            bone=ID('Target'+str(index)); bone[match.VERSION_KEY]=1; bone.ui[match.VERSION_KEY]={}
            pb=ID(bone.name); pb.bone=bone; pb[match.PROPERTY]=1.; pb.ui[match.PROPERTY]=copy.deepcopy(ui)
            pb.rotation_mode='QUATERNION'; pb.location=(0.,0.,0.); pb.scale=(1.,1.,1.)
            pb.rotation_quaternion=(1.,0.,0.,0.); pb.rotation_euler=(0.,0.,0.); pb.rotation_axis_angle=(0.,0.,1.,0.)
            pb.lock_rotation=(False,False,False); pb.lock_rotation_w=False; pb.lock_rotations_4d=False
            pb.matrix_basis=[1.,0.,0.,1.]; pb.constraints=[]
            bones[bone.name]=bone; poses[pb.name]=pb
            inventory['rigs'][key]={'target':NS(name=pb.name),'entries':[]}
        class Named(dict):
            def __iter__(self): return iter(self.values())
        rig.pose=NS(bones=Named(poses)); rig.data=ID('RigData'); rig.data.bones=Named(bones)
        constraint=NS(type='IK',mute=False,influence=1.,pole_angle=.5)
        rig.pose.bones['Target0'].constraints.append(constraint)
        old_driver=Driver(10,'owned.old'); rig.animation_data=NS(action=None,action_slot=None,drivers=[old_driver],nla_tracks=[])
        limb._validate_inventory=lambda value:inventory
        states=modes_and_ui(rig,inventory,api); require_restorable_shape(inventory,states,api)
        rejections=[]
        for schema in (1,2,99):
            bad=copy.deepcopy(inventory); bad['schema']=schema; rejections.append((bad,copy.deepcopy(states)))
        bad=copy.deepcopy(inventory); bad['schema']=4; old=copy.deepcopy(states); old[0]['version']['present']=False
        rejections.append((bad,old))
        bad=copy.deepcopy(inventory); bad['rigs'].pop(('LEG','R')); rejections.append((bad,copy.deepcopy(states)))
        bad=copy.deepcopy(states); bad[0]['property']['value']=float('nan'); rejections.append((inventory,bad))
        bad=copy.deepcopy(states); bad[0]['version']['value']=2; rejections.append((inventory,bad))
        for bad,rows in rejections:
            try: require_restorable_shape(bad,rows,api)
            except RuntimeError: pass
            else: need(False,'Older/incomplete/invalid limb shape admitted')
        target=rig.pose.bones['Target0']; original_ui=target.ui.pop(match.PROPERTY)
        try: property_state(target,match.PROPERTY,api)
        except RuntimeError: pass
        else: need(False,'Unreadable current target UI admitted')
        target.ui[match.PROPERTY]=original_ui
        scene=NS(tool_settings=NS(use_keyframe_insert_auto=True),frame_current=7,frame_subframe=.25)
        scene.frame_set=lambda frame,subframe:(setattr(scene,'frame_current',frame),setattr(scene,'frame_subframe',subframe))
        context=NS(scene=scene)
        context.mode='POSE'; context.view_layer=NS(objects=NS(active=rig))
        rig.library=None; rig.override_library=None
        limb._restore_context=lambda *args:None
        display.update(visible=False)
        checkpoint=batch._checkpoint(context,rig,None)
        capture_tree=next(node for node in ast.parse(Path(__file__).read_text(encoding='utf-8')).body
                          if isinstance(node,ast.FunctionDef) and node.name=='capture_fk')
        capture_env=dict(globals(),native_api=lambda:api,
            author_read=lambda *args:(_ for _ in ()).throw(RuntimeError('injected initial author read failure')))
        exec(compile(ast.Module(body=[capture_tree],type_ignores=[]),'<actual-v5-capture>','exec'),capture_env)
        failed_capture={'Body_FK_transition':{'capture_AuthorRestoration':{'status':'Measured'}}}
        try:
            capture_env['capture_fk'](NS(context=context),context,None,None,None,None,None,rig,None,
                                     lambda *args:None,lambda *args:None,failed_capture,lambda:None)
        except RuntimeError: pass
        else: need(False,'Unknown initial author read admitted before public FK')
        need(failed_capture['Body_FK_transition']['status']=='UnknownCaptureFailed'
             and failed_capture['Body_FK_transition']['public_called'] is False
             and failed_capture['Body_FK_transition']['capture_AuthorRestoration'] is None,
             'Previous capture success leaked into a failed current capture')
        saved=dict(api=api,checkpoint=checkpoint,states=states,inventory=inventory,paths={'owned.old','owned.new'})
        for outcome in ('CANCELLED','FINISHED'):
            report={'Body_FK_transition':{}}; calls=[]
            def operator(*args,**kwargs):
                calls.append((args,kwargs,scene.tool_settings.use_keyframe_insert_auto)); return {outcome}
            try: public_fk(NS(ops=NS(character_designer=NS(body_ik_fk_switch=operator))),context,rig,saved,report,lambda:None)
            except RuntimeError: pass
            else: need(False,'Cancelled or non-FK public outcome admitted')
            need(calls==[(('EXEC_DEFAULT',),dict(mode='FK',keyframe=False),False)],'Public switch bypass or Auto Key timing wrong')
        coordinates=dict(identity=['Body12'],base=array('f',[0.,1.,2.]),blocks=[array('f',[float(index)]) for index in range(12)])
        capture=lambda body:copy.deepcopy(coordinates)
        def author_reader(*args):
            return dict(pose_properties={name:dict(pb) for name,pb in poses.items()},
                        drivers=[(curve.pointer,curve.data_path) for curve in rig.animation_data.drivers],
                        constraints=[constraint.mute,constraint.influence,constraint.pole_angle],
                        display=copy.deepcopy(display),corrective=copy.deepcopy(corrective),
                        frame=[scene.frame_current,scene.frame_subframe])
        saved.update(author=author_reader(),coordinates=copy.deepcopy(coordinates),coordinate_proof=coordinate_proof(coordinates),
            protection=NS(verify=lambda:dict(success=True)),context={},frame=[7,.25],autokey=True,nla=[],
            readers=(),capture_coordinates=capture,restore_coordinates=lambda *args:None)
        rollback_tree=next(node for node in ast.parse(Path(__file__).read_text(encoding='utf-8')).body
                           if isinstance(node,ast.FunctionDef) and node.name=='rollback_fk')
        rollback_env=dict(globals(),author_read=author_reader)
        exec(compile(ast.Module(body=[rollback_tree],type_ignores=[]),'<actual-v5-rollback>','exec'),rollback_env)
        for pb in poses.values(): pb[match.PROPERTY]=0.
        target.ui[match.PROPERTY]['description']='changed'
        constraint.mute=True; constraint.influence=0.; constraint.pole_angle=2.
        rig.animation_data.drivers.append(Driver(20,'owned.new')); display['visible']=True; corrective['value']=9.
        scene.frame_set(99,subframe=0.); scene.tool_settings.use_keyframe_insert_auto=False
        report={'Body_FK_transition':{}}
        rollback_env['rollback_fk'](context,rig,None,saved,report,lambda:None)
        proof=report['Body_FK_transition']['rollback']
        need(proof['completed'] is True and proof['status']=='MeasuredRestored'
             and rig.animation_data.drivers==[old_driver] and target.ui[match.PROPERTY]==ui
             and [constraint.mute,constraint.influence,constraint.pole_angle]==[False,1.,.5]
             and all(pb[match.PROPERTY]==1. for pb in poses.values()) and scene.tool_settings.use_keyframe_insert_auto is True,
             'Real batch/wrapper rollback lost properties/UI/driver/display/Auto Key restoration')
        for failure_at,phase in ((1,'initial_report_write'),(2,'final_report_write')):
            for pb in poses.values(): pb[match.PROPERTY]=0.
            target.ui[match.PROPERTY]['description']='changed again'
            constraint.mute=True; constraint.influence=0.; constraint.pole_angle=2.
            rig.animation_data.drivers.append(Driver(20,'owned.new'))
            display['visible']=True; corrective['value']=9.
            scene.frame_set(99,subframe=0.); scene.tool_settings.use_keyframe_insert_auto=False
            report={'Body_FK_transition':{'rollback':{'completed':True}}}
            calls=[]; persisted=[]
            def failing_write():
                calls.append(len(calls)+1)
                if len(calls)==failure_at: raise PermissionError('injected exhausted report write')
                persisted.append(copy.deepcopy(report['Body_FK_transition']['rollback']))
            try: rollback_env['rollback_fk'](context,rig,None,saved,report,failing_write)
            except RuntimeError: pass
            else: need(False,'Exhausted rollback report write admitted')
            proof=report['Body_FK_transition']['rollback']
            need(calls==[1,2] and proof['completed'] is False and proof['errors'][0]['phase']==phase
                 and all(proof['author_fields'].values()) and proof['target_UI'] is True and proof['autokey'] is True
                 and rig.animation_data.drivers==[old_driver] and target.ui[match.PROPERTY]==ui
                 and [constraint.mute,constraint.influence,constraint.pole_angle]==[False,1.,.5]
                 and all(pb[match.PROPERTY]==1. for pb in poses.values()) and corrective['value']==1.25
                 and display['visible'] is False and [scene.frame_current,scene.frame_subframe]==[7,.25]
                 and scene.tool_settings.use_keyframe_insert_auto is True and len(persisted)==1
                 and persisted[0]['completed'] is False,
                 'Report failure skipped native restoration or retained previous successful current proof')
            if failure_at==2:
                need(proof['status']=='MeasuredRestoreReportFailed','Final write failure did not withdraw measured success')
        # A later failed read must start Unknown rather than retain this success.
        rollback_env['author_read']=lambda *args:(_ for _ in ()).throw(RuntimeError('injected author read failure'))
        try: rollback_env['rollback_fk'](context,rig,None,saved,report,lambda:None)
        except RuntimeError: pass
        else: need(False,'Unknown author read admitted')
        proof=report['Body_FK_transition']['rollback']
        need(proof['completed'] is False and proof['status']=='UnknownReadFailed' and proof['author_fields'] is None,
             'Prior successful checkpoint leaked into failed current read')
        rollback_env['author_read']=author_reader
        api.batch._rollback=lambda *args:(_ for _ in ()).throw(RuntimeError('injected rollback failure'))
        try: rollback_env['rollback_fk'](context,rig,None,saved,report,lambda:None)
        except RuntimeError: pass
        else: need(False,'Rollback exception admitted')
        need(report['Body_FK_transition']['rollback']['completed'] is False
             and report['Body_FK_transition']['rollback']['errors'][0]['phase']=='batch','Rollback error proof lost')
    finally:
        if previous_package is None: sys.modules.pop(package.__name__,None)
        else: sys.modules[package.__name__]=previous_package
    print(json.dumps(dict(source_prepared=True,native_run=False,older_or_invalid_shape_rejections=len(rejections),
        unreadable_target_UI_and_initial_author_read_refused=True,public_cancel_and_non_FK_refused=True,private_AutoKey_off_before_public=True,
        actual_canonical_batch_checkpoint_and_rollback_executed=True,added_owned_driver_removed_existing_retained=True,
        target_properties_UI_display_corrective_frame_AutoKey_restored=True,failed_read_and_rollback_close_gate=True,
        initial_and_final_report_write_faults_restore_all_and_close_gate=True,
        current_source_input_reprepared=True,historical_pin_basis_refused_if_changed=True,
        actual_compiled_main_and_prepared_closure_use_current_Tuning_pin=True,historical_runtime_equivalence_claimed=False,
        actual_main_disk_inputs_append_bind_fresh_saved_copy=True,historical_input_basis_rejection_controls=4,
        fresh_SDna_proof_read=True,Controls_FK_cache_Native_verified=False,
        frozen_recipe_seed_geometry_and_both_finally_inverse_AST_exact=True,accepted=False)))


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
