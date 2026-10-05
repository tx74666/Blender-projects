"""Read one isolated saved X; registry writes remain in this disposable process."""
from pathlib import Path
import sys, json, hashlib
import bpy
sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/addons')
from character_designer import hair_strand_registry as registry, hair_motion_profiles as profiles
from character_designer import hair_bones_rig as hair
source=bpy.data.objects['Hair']
rig=source.get(hair.RIG_KEY)
before={key:source.get(key) for key in source.keys()}
mesh_before=tuple(tuple(v.co) for v in source.data.vertices)
weights_before=tuple(tuple((v.group,v.weight) for v in vertex.groups) for vertex in source.data.vertices)
rest_before=tuple((bone.name,hair._bone_state(bone)) for bone in rig.data.bones)
data=registry.initialize(source)
profiles.initialize(source,registry=data)
profiles.assign_suggested_groups(source,registry=data)
details=[]
for item in data['strands']:
    rest=item['rest']
    length=sum(sum((a-b)**2 for a,b in zip(s['head'],s['tail']))**.5 for s in rest)
    details.append({'strand_id':item['strand_id'],'order':item['order'],'root':rest[0]['head'],
        'tip':rest[-1]['tail'],'length':length,'side':item['side'],'pair_proof':item['pair_proof'],
        'mirror_id':item['mirror_id'],'bone_count':len(item['bones']),'bones':item['bones']})
assert mesh_before==tuple(tuple(v.co) for v in source.data.vertices)
assert weights_before==tuple(tuple((v.group,v.weight) for v in vertex.groups) for vertex in source.data.vertices)
assert rest_before==tuple((bone.name,hair._bone_state(bone)) for bone in rig.data.bones)
assert all(source.get(key)==value for key,value in before.items())
result={'ok':True,'blender':bpy.app.version_string,'source':source.name,'rig':rig.name,
        'source_uid':data['source_uid'],'topology':data['topology'],
        'counts':{side:sum(item['side']==side for item in data['strands']) for side in ('L','R','C','U')},
        'diagnostics':data['diagnostics'],'groups':{g:sum(v['group']==g for v in profiles.effective_all(source,registry=data).values()) for g in profiles.DEFAULTS},'strands':details,'artist_saved':False}
output=Path(__file__).with_name('saved_hair_registry_extended.json')
output.write_text(json.dumps(result,indent=2),encoding='utf8')
print('REAL_HAIR_REGISTRY',json.dumps({key:result[key] for key in ('ok','source_uid','counts','diagnostics','artist_saved')}))

