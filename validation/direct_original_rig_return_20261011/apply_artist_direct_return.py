import bpy,sys,json,hashlib,traceback,importlib
from pathlib import Path
evidence=Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011')
sys.path.insert(0,str(evidence))
import validation_preservation
importlib.reload(validation_preservation)
import verify_direct_return_isolated as verifier
importlib.reload(verifier)
from validation_preservation import asset_snapshot,digest
from character_designer import animation_worklist as worklist, animation_worklist_target as target, unity_animation as ua, body_original_mode as original
from character_designer import animation_worklist_fingerprint as fp
import character_designer as cd

artist=Path(r'D:\Blender\Projects\Character\X\X.blend')
packet_path=Path(r'D:\Blender\Projects\Character\Animation\UnityExports\CharacterTuning\20261009-233830-d8fa2427ba96\Cosha_Walk_N.cdanim.json')
workspace_path=Path(r'D:\Blender\Projects\Character\Animation\UnityExports\CharacterTuning\Workspaces\16c8d53b-f513-46c0-9778-4789d512ea56\3207a6768cff4594fb4b180b85f70a37\character_animation_workspace.json')
assert Path(bpy.data.filepath).resolve()==artist.resolve()
assert tuple(cd.bl_info['version'])==(0,77,24)
assert not (evidence/'artist_direct_return_receipt.json').exists(), 'Inspect existing receipt before retrying an applied task.'
backup=evidence/'artist_before_direct_return.blend'
assert hashlib.sha256(backup.read_bytes()).hexdigest()=='079d12824d4fc75a2abba00f7bf68d606e07ab558634c0f430acfe1e4c475337'
rows=verifier.old_worklist_proofs(fp)
assert len(rows)==1 and rows[0]['entire_action_equal'], 'Existing Custom gained edits; preserve them before migrating.'
prior_proof=json.loads((evidence/'live_action_edits.json').read_text(encoding='utf-8'))['worklists'][0]['items'][0]['source']['complete_motion_proof']['action_fingerprint']
assert rows[0]['source_proof']['action_fingerprint']==prior_proof, 'Source content changed since the recovery backup.'
report={'completed':False,'file':str(artist),'runtime':list(cd.bl_info['version']),'backup':str(backup),'packet':str(packet_path),'old_actions':verifier.public_proofs(rows)}
save_committed=False
cache_root=Path(bpy.utils.user_resource('DATAFILES',path='character_designer/animation_sources'))
assert len(str(cache_root/'d3444e049cfd4afebb343e61e518c768'/'2ae2067c9794fc7767f6abb35b6af33df496986a006c870fc9d0dc47eaa55db5'/('0'*32+'.blend@'))) < 260, 'Source cache path is too long for the native Blender write.'
scene=bpy.data.scenes['Scene']
rig=bpy.data.objects['CoshaRig']
verifier.select_rig(scene,rig)
before=asset_snapshot(scene,rig,ua)
original_data=rig.data
original_rest=digest(ua._rest_state(original_data))
try:
    immediate_backup=evidence/'artist_before_apply_final.blend'
    assert not immediate_backup.exists(), 'Inspect the latest pre-application backup before retry.'
    backup_result=bpy.ops.wm.save_as_mainfile(filepath=str(immediate_backup),copy=True,check_existing=False)
    assert 'FINISHED' in backup_result and Path(bpy.data.filepath).resolve()==artist.resolve()
    report['immediate_backup']={'path':str(immediate_backup),'sha256':hashlib.sha256(immediate_backup.read_bytes()).hexdigest(),'save_result':sorted(backup_result)}
    assert scene.character_designer_setup.rig is rig
    saved=worklist.connect(bpy.context,str(workspace_path))
    assert not saved.items and saved.rig is None, 'Original scene already has worklist edits.'
    target.adopt_main_rig(bpy.context)
    packet=ua.load_package(str(packet_path))
    mapping=ua._mapping(rig,packet,scene.unit_settings.scale_length)
    ready=[entry for entry in saved.catalog if entry.ready]
    assert len(ready)==1
    item=worklist.add(bpy.context,ready[0].clip_key)
    assert item.rig is rig and saved.rig is rig and bpy.context.scene is scene
    worklist.activate(bpy.context,item.item_id,'CUSTOM')
    report['samples'],authored=verifier.samples(scene,rig,packet,mapping,ua,2.0e-4)
    report['preservation']=verifier.require_assets(scene,rig,ua,before,original_data,original_rest,authored)
    verifier.verify_old_actions(rows,fp)
    assert item.source_action.library and not item.custom_action.library
    source_proof=fp.fingerprint_action(item.source_action,item.source_slot)
    custom_proof=fp.fingerprint_action(item.custom_action,item.custom_slot)
    assert source_proof['fingerprint_known'] and source_proof['action_fingerprint']==custom_proof['action_fingerprint']
    archive={'source_action':rows[0]['source'],'custom_action':rows[0]['custom'],'source_slot':rows[0]['source_slot'],'custom_slot':rows[0]['custom_slot'],
        'source_file':rows[0]['source_file'],'source_sha256':rows[0]['source_file_hash'],'packet':str(packet_path),'packet_sha256':packet['_sha256'],
        'source_backup':str(evidence/'previous_source_Walk_N.blend')}
    assert hashlib.sha256((evidence/'previous_source_Walk_N.blend').read_bytes()).hexdigest()==rows[0]['source_file_hash']
    rig['character_designer_animation_previous_import_archive']=archive
    rows[0]['custom'].use_fake_user=True
    ua._set_frame(scene,18.0)
    bpy.context.view_layer.update()
    if rig.mode!='POSE': bpy.ops.object.mode_set(mode='POSE')
    scene.tool_settings.use_keyframe_insert_auto=False
    result=bpy.ops.wm.save_as_mainfile(filepath=str(artist),check_existing=False)
    assert 'FINISHED' in result and Path(bpy.data.filepath).resolve()==artist.resolve()
    save_committed=True
    report.update({'save_result':sorted(result),'file_sha256':hashlib.sha256(artist.read_bytes()).hexdigest(),'rig':rig.name,'scene':scene.name,
        'item_id':item.item_id,'source':item.source_action.name,'custom':item.custom_action.name,'source_fingerprint':source_proof,
        'frame':scene.frame_current_final,'original_mode':original.active(rig),'completed':True})
except Exception as exc:
    report.update({'error':str(exc),'traceback':traceback.format_exc()})
    # Before a successful save the persistent recovery path can restore the
    # exact artist transaction; keep imported local drafts for diagnosis.
    if not save_committed and target.is_adopted(rig):
        try:
            target.restore_main_rig(bpy.context)
            report['rolled_back_artist']=True
        except Exception as restore_exc:
            report['recovery_error']=str(restore_exc)
    raise
finally:
    (evidence/'artist_direct_return_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'completed':report['completed'],'save':report.get('save_result'),'rig':rig.name,'scene':scene.name,'worst':report.get('samples',{}).get('worst')},ensure_ascii=False))
