import hashlib,json,os,sys
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_saved_status_07738_01/config.json')
CONFIG_SHA256 = '39701c15513096bcfdde6ed46552076254bc5af82e6b693a148f415287924fc9'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8'));assert os.getpid()==cfg['expected_pid']
import bpy
prior=sys.modules['x_original_runtime_recovery_07738_03'].ACTIVE
refresh=prior.STATE['refresh'];light=prior.STATE['light']
writer=refresh.document(cfg['writer_report'])
refresh.pin(cfg['writer_report']['path'],cfg['writer_report']['sha256'])
report={'schema':'x.validation.original-saved-eventloop-status/1','pid':os.getpid(),'writer_report':cfg['writer_report'],'dirty_after_event_loop':bool(bpy.data.is_dirty),'filepath':bpy.data.filepath,'actual_saved_file':refresh.pin(bpy.data.filepath,writer['original_artist_disk_after']['sha256']),'runtime_version':list(sys.modules['character_designer'].bl_info['version']),'Pose_fake_user':bpy.data.actions['Pose'].use_fake_user,'Pose_identity':light.reference(bpy.data.actions['Pose']),'CoshaRig_identity':light.reference(bpy.data.objects['CoshaRig']),'read_only':True,'saved_or_closed':False}
p=Path(cfg['output']);assert not p.exists();p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SAVED_STATUS '+json.dumps(report,ensure_ascii=False))
