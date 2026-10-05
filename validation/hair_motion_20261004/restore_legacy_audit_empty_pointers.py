"""Undo only empty nullable-pointer materialization caused by the first audit."""
import json, datetime, hashlib
from pathlib import Path
import bpy

DIRECTORY=Path(__file__).parent
ORIGINAL=DIRECTORY/'live_legacy_wiggle_read_20261005_005917_002501.json'
def run(scope):
    require=scope['require']
    modules=scope['runtime']()
    require(bpy.app.version[:2]==(5,1) and Path(bpy.data.filepath).resolve()==scope['ARTIST'], 'Unexpected artist context.')
    scope['no_live_preview'](modules)
    original=json.loads(ORIGINAL.read_text(encoding='utf8'))
    require(original['source_sha256']==scope['LEGACY_SHA256'], 'Original audited legacy source differs.')
    changes=[]
    for row in original['rows']:
        if row['type']=='Scene': owner=bpy.data.scenes.get(row['name'])
        elif row['type']=='Object': owner=bpy.data.objects.get(row['name'])
        elif row['type']=='PoseBone':
            obj=bpy.data.objects.get(row['armature'])
            owner=obj.pose.bones.get(row['name']) if obj and obj.type=='ARMATURE' else None
        else: raise RuntimeError('Unexpected audited RNA owner.')
        require(owner is not None,'An original audit owner no longer exists.')
        for key, before in row['top'].items():
            prop=owner.bl_rna.properties.get(key)
            require(prop is not None,'An audited legacy RNA declaration changed.')
            if prop.type=='POINTER' and not before['set']:
                require(before['value'] is None,'An unset audited pointer has a nonempty value.')
                if owner.is_property_set(key):
                    require(getattr(owner,key) is None,'An audited pointer acquired a user value; keep it untouched.')
                    changes.append((owner,key))
    helpers=scope['read_helpers'](modules)
    asset=helpers.asset_fingerprint(scope['find_source'](modules['hair_bones_rig']))
    pose=scope['full_pose'](modules,helpers)
    selection=scope['selection_snapshot']()
    display=scope['display_snapshot'](modules)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    recovery=DIRECTORY/('X_before_audit_pointer_restore_'+stamp+'.blend')
    result=bpy.ops.wm.save_as_mainfile(filepath=str(recovery),copy=True,check_existing=False)
    require(result=={'FINISHED'} and recovery.is_file(),'Native pre-correction recovery save failed.')
    for owner,key in changes:
        owner.property_unset(key)
        require(not owner.is_property_set(key),'Empty pointer presence could not be restored.')
    after=helpers.asset_fingerprint(scope['find_source'](modules['hair_bones_rig']))
    require(asset['sha256']==after['sha256'] and asset['portable_sha256']==after['portable_sha256'],'Artist raw data changed.')
    scope['check_pose'](pose,modules)
    require(scope['selection_snapshot']()==selection and scope['display_snapshot'](modules)==display,'Artist context/display changed.')
    report={'status':'passed','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'original_audit':str(ORIGINAL),'original_audit_sha256':hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            'restored_empty_nullable_pointers':len(changes),'nonempty_values_modified':0,
            'raw_exact':True,'pose_exact':True,'selection_exact':True,'display_exact':True,
            'recovery':str(recovery),'recovery_save_result':sorted(result),
            'artist_saved':False,'artist_reloaded':False}
    path=DIRECTORY/('restore_legacy_audit_empty_pointers_'+stamp+'.json')
    with path.open('x',encoding='utf8') as stream: json.dump(report,stream,ensure_ascii=False,indent=2)
    print('AUDIT_EMPTY_POINTER_RESTORED',str(path),len(changes))
    return report
