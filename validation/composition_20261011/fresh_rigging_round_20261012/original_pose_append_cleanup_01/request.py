import hashlib,json,os,sys
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_pose_append_cleanup_01/config.json')
CONFIG_SHA256 = 'c0e6f28b5acd1ea60539987e29ef27f2cbb24c7a2ca5f46ee1e9011ca7a7786b'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
assert os.getpid()==cfg['expected_pid']==14500
import bpy
prior=sys.modules['x_original_runtime_recovery_07738_03'].ACTIVE
light=prior.STATE['light'];refresh=prior.STATE['refresh'];verifier=prior.STATE['verifier']
for key in ('baseline','diagnostic','failed_integration','backup'): refresh.pin(cfg[key]['path'],cfg[key]['sha256'])
baseline=refresh.document(cfg['baseline']);diag=refresh.document(cfg['diagnostic']);failed=refresh.document(cfg['failed_integration'])
assert failed['fresh_qualified_full_before_mutation_verified'] is True and failed['original_artist_save_attempted'] is False and failed['public_failure_close_completed'] is True
assert failed['error']=='RuntimeError: Pose restoration added unexpected native data.'
helper=refresh.load_source(Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/integrate_original20_saved_artist_07738e.py'),'38ad7aa9fd6e40bdabca9aeb24340d0d5f52a160d6370d6daf2611ffbfc5e34b','x_owned_pose_cleanup_helper')
qual=refresh.load_source(Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/qualify_original_registration_07738.py'),'3e298d40375ee01f8ebc658cabd27482115424d47c7618dc1edc8d5cadb55e28','x_owned_pose_cleanup_compare')
package=sys.modules['character_designer']
old={str(row['native_pointer']):{k:v for k,v in row.items() if k not in ('users','use_fake_user')} for row in baseline['all_IDs']}
old.update({str(row['identity']['native_pointer']):row['identity'] for row in baseline['light']['actions']})
assert helper.id_inventory(bpy,light)=={**old,**diag['added']}
assert diag['removed']==diag['changed']=={} and len(diag['added'])==2
assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()=='cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'
pose=bpy.data.actions.get('Pose');lib=bpy.data.libraries.get('Pose.blend')
assert pose is not None and int(pose.as_pointer())==2558007772496 and pose.library is None and pose.users==0 and pose.use_fake_user is False
assert helper.pose_digest(helper.pose_content(pose))=='acdd30eda498c058f9fea9a7a019ec11ffd355e7409b666e26cb98e69d225d3f'
backup=Path(cfg['backup']['path']).resolve()
def admit_library():
    assert lib is not None and int(lib.as_pointer())==2558998407896 and lib.users==1 and lib.use_fake_user is False
    assert Path(bpy.path.abspath(lib.filepath)).resolve()==backup
    refs=bpy.data.user_map();blocks=set(refs)|set(bpy.data.actions)
    assert not refs.get(lib,set()) and not any(block.library==lib for block in blocks)
    assert not any(other.parent==lib for other in bpy.data.libraries)
    for block in blocks:
        weak=getattr(block,'library_weak_reference',None)
        assert weak is None or Path(bpy.path.abspath(weak.filepath)).resolve()!=backup
    return refs
refs=admit_library();assert not refs.get(pose,set())
report={'schema':'x.validation.owned-Pose-append-cleanup/1','completed':False,'inputs':cfg,'pid':os.getpid(),'Pose_removed':False,'Library_removed':False,'original_file_saved':False,'full_geometry_recapture_performed':False,'scene_scope':'Only two IDs just created by failed integration03; originals excluded by exact native inventory.'}
output=Path(cfg['output']);assert not output.exists()
def write(): output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
write()
try:
    with light.original_context(bpy,'Scene','CoshaRig') as (ctx,rig):
        refresh.idle(package,ctx,bpy)
        assert package.unity_animation_original_inputs.current(rig) is None
        bpy.data.actions.remove(pose,do_unlink=False,do_id_user=True,do_ui_user=True)
        report['Pose_removed']=True;write()
        admit_library()
        bpy.data.libraries.remove(lib,do_unlink=True,do_id_user=True,do_ui_user=True)
        report['Library_removed']=True;write()
        assert helper.id_inventory(bpy,light)==old
        observed={'light':light.snapshot(ctx,rig,bpy,package.unity_animation),'scenes':verifier.scene_capture(),'wm':verifier.wm_capture(package),'context':verifier.native_context(),'pose':verifier.native_pose_channels(),'all_IDs':sorted((dict(light.reference(block),users=block.users,use_fake_user=block.use_fake_user) for block in bpy.data.user_map()),key=lambda row:row['native_pointer']),'raw':prior.corrected_raw_snapshot(bpy,prior.STATE['observed'])}
        for key,value in observed.items(): assert qual.encoded(verifier.public(value))==qual.encoded(baseline[key]), 'Original baseline differs after owned cleanup: '+key
        assert bpy.data.is_dirty is True
        assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()=='cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'
        report.update(completed=True,original_IDs_exact=True,fresh_light_raw_Scene_WM_context_pose_ID_users_flags_exact_BE4C=True,dirty_still_true=True,original_disk_unchanged=True)
except Exception as error:
    import traceback
    report.update(error=type(error).__name__+': '+str(error),traceback=traceback.format_exc())
finally: write()
print('OWNED_POSE_CLEANUP '+json.dumps({'completed':report['completed'],'error':report.get('error'),'report':str(output)},ensure_ascii=False))
assert report['completed'] is True
