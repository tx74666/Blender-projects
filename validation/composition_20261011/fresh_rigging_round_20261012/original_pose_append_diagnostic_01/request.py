import hashlib,json,os,sys
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_pose_append_diagnostic_01/config.json')
CONFIG_SHA256 = 'ab8489e6dba50537b0e43fa0eda6105737bee23144ceb022ca8dd065f4368c74'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
assert os.getpid()==cfg['expected_pid']
import bpy
prior=sys.modules['x_original_runtime_recovery_07738_03'].ACTIVE
light=prior.STATE['light']
refresh=prior.STATE['refresh']
baseline=refresh.document(cfg['baseline'])
helper=refresh.load_source(Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/integrate_original20_saved_artist_07738e.py'),'38ad7aa9fd6e40bdabca9aeb24340d0d5f52a160d6370d6daf2611ffbfc5e34b','x_pose_append_readonly_helper')
old={str(row['native_pointer']):{k:v for k,v in row.items() if k not in ('users','use_fake_user')} for row in baseline['all_IDs']}
old.update({str(row['identity']['native_pointer']):row['identity'] for row in baseline['light']['actions']})
current=helper.id_inventory(bpy,light)
added={k:v for k,v in current.items() if k not in old}
removed={k:v for k,v in old.items() if k not in current}
changed={k:{'before':old[k],'after':current[k]} for k in old.keys() & current.keys() if old[k]!=current[k]}
user_map=bpy.data.user_map()
blocks={str(int(block.as_pointer())):block for block in user_map}
blocks.update({str(int(a.as_pointer())):a for a in bpy.data.actions})
extra=[{'identity':row,'users':blocks[k].users,'fake_user':blocks[k].use_fake_user,'referenced_by':[light.reference(b) for b in user_map.get(blocks[k],set())]} for k,row in added.items()]
pose=bpy.data.actions.get('Pose')
report={'schema':'x.validation.pose-append-readonly-diagnostic/1','pid':os.getpid(),'added':added,'removed':removed,'changed':changed,'added_details':extra,'libraries':[dict(light.reference(lib),filepath=lib.filepath,users=lib.users) for lib in bpy.data.libraries],'Pose':None if pose is None else {'identity':light.reference(pose),'content_sha256':helper.pose_digest(helper.pose_content(pose)),'users':pose.users,'fake_user':pose.use_fake_user},'dirty':bool(bpy.data.is_dirty),'original_disk_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'scene_mutation_performed':False}
p=Path(cfg['output']);assert not p.exists();p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('POSE_APPEND_DIAGNOSTIC '+json.dumps({'added_count':len(added),'removed_count':len(removed),'changed_count':len(changed),'report':str(p)},ensure_ascii=False))
