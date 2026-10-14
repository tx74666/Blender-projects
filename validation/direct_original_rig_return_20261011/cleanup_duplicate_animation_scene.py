import bpy,sys,json,hashlib,importlib
from pathlib import Path
evidence=Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011')
sys.path.insert(0,str(evidence))
import validation_preservation
importlib.reload(validation_preservation)
from validation_preservation import asset_snapshot,changes
from character_designer import unity_animation as ua,animation_worklist as worklist,animation_worklist_target as target
from character_designer import animation_worklist_fingerprint as fp
artist=Path(r'D:\Blender\Projects\Character\X\X.blend')
receipt=json.loads((evidence/'artist_direct_return_receipt.json').read_text(encoding='utf-8'))
assert receipt['completed'] and Path(bpy.data.filepath).resolve()==artist.resolve()
assert bpy.context.scene.name=='Scene'
rig=bpy.data.objects['CoshaRig']
saved=worklist.state(bpy.context)
item=worklist._item(saved,receipt['item_id'])
target.ensure_active(bpy.context,rig)
assert item.rig is rig and rig.animation_data.action is item.custom_action
source_proof=fp.fingerprint_action(item.source_action,item.source_slot)
custom_proof=fp.fingerprint_action(item.custom_action,item.custom_slot)
assert source_proof['action_fingerprint']==custom_proof['action_fingerprint']==receipt['source_fingerprint']['action_fingerprint']
expected=json.loads((evidence/'cleanup_scope.json').read_text(encoding='utf-8'))
retired_rig_rows=[row for row in expected['objects'] if row['type']=='ARMATURE']
assert len(retired_rig_rows)==1
retired_rig=bpy.data.objects[retired_rig_rows[0]['name']]
assert retired_rig is not rig and len(retired_rig.users_scene)==1
old_scene=retired_rig.users_scene[0]
assert old_scene is not bpy.context.scene
old_objects=list(old_scene.objects)
assert sorted(obj.name for obj in old_objects)==sorted(row['name'] for row in expected['objects'])
old_collections=list(old_scene.collection.children)
assert len(old_collections)==1 and old_collections[0].name=='Unity Source - CoshaRig' and old_collections[0].users==1
for obj in old_objects:
    assert list(obj.users_scene)==[old_scene]
    assert set(obj.users_collection)<=set(old_collections)
    assert obj is not rig
cleared_transient_references=[]
wm_animation=bpy.context.window_manager.character_designer_animation
assert wm_animation.target is rig
if wm_animation.source in old_objects:
    cleared_transient_references.append({'field':'WindowManager.character_designer_animation.source','object':wm_animation.source.name})
    wm_animation.source=None
incoming=bpy.data.user_map()
allowed=set(old_objects+old_collections+[old_scene])
for obj in old_objects:
    external=[owner for owner in incoming.get(obj,set()) if owner not in allowed]
    assert not external, 'The duplicate object gained external users: '+obj.name+' '+str([owner.name for owner in external])
before=asset_snapshot(bpy.context.scene,rig,ua)
backup=evidence/'artist_before_cleanup.blend'
assert not backup.exists(), 'Inspect existing cleanup backup before retry.'
result=bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True,check_existing=False)
assert 'FINISHED' in result and backup.is_file() and Path(bpy.data.filepath).resolve()==artist.resolve()
report={'backup':str(backup),'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),
        'cleared_transient_references':cleared_transient_references,
        'removed_scene':old_scene.name,'removed_objects':[obj.name for obj in old_objects],'removed_collections':[c.name for c in old_collections],
        'old_actions_retained':{key:value.name for key,value in rig['character_designer_animation_previous_import_archive'].items() if isinstance(value,bpy.types.Action)}}
bpy.data.scenes.remove(old_scene)
for obj in old_objects: bpy.data.objects.remove(obj,do_unlink=True)
for collection in old_collections: bpy.data.collections.remove(collection)
assert not changes(before,asset_snapshot(bpy.context.scene,rig,ua)), 'Original assets changed during cleanup.'
assert rig.animation_data.action is item.custom_action and target.is_adopted(rig)
result=bpy.ops.wm.save_as_mainfile(filepath=str(artist),check_existing=False)
assert 'FINISHED' in result and Path(bpy.data.filepath).resolve()==artist.resolve()
report.update({'completed':True,'save_result':sorted(result),'filepath':bpy.data.filepath,
    'file_sha256':hashlib.sha256(artist.read_bytes()).hexdigest(),'scene':bpy.context.scene.name,'scenes':[scene.name for scene in bpy.data.scenes],
    'rig':rig.name,'bone_count':len(rig.data.bones),'widgets':sum(pb.custom_shape is not None for pb in rig.pose.bones),
    'frame':bpy.context.scene.frame_current_final,'mode':bpy.context.mode,'dirty':bpy.data.is_dirty,
    'source':item.source_action.name,'custom':item.custom_action.name,'original_assets_preserved':True})
report.update({'item_id':item.item_id,'packet':receipt['packet'],
    'action_fingerprint':source_proof['action_fingerprint'],'original_assets_after_cleanup':asset_snapshot(bpy.context.scene,rig,ua)})
(evidence/'artist_cleanup_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
