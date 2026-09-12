import bpy, sys, json
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons']
from character_designer import limb_ik, forearm_twist
rig=bpy.data.objects['CoshaRig']; inv=limb_ik._validate_inventory(rig)
def xyz(v):return list(v)
rows={}
for key,r in inv['rigs'].items():
 if key[0]!='ARM':continue
 target=rig.pose.bones[r['target'].name]
 rows[str(key)]={k:r[k] for k in ('chain','auto_align','auto_rotation_space')}
 rows[str(key)].update(target=target.name,at_shape=target.use_transform_at_custom_shape,around=target.use_transform_around_custom_shape,shape_transform=target.custom_shape_transform.name if target.custom_shape_transform else None)
 rows[str(key)]['bones']=[dict(name=n,head=xyz(rig.data.bones[n].head_local),tail=xyz(rig.data.bones[n].tail_local),pose_head=xyz(rig.pose.bones[n].head),parent=rig.data.bones[n].parent.name if rig.data.bones[n].parent else None) for n in r['chain']]
mesh=bpy.data.objects['Cosha']
print('REAL_INSPECT',json.dumps(dict(rows=rows,rig_matrix=[list(row) for row in rig.matrix_world],modifiers=[dict(name=m.name,type=m.type,show=m.show_viewport,obj=m.object.name if m.type=='ARMATURE' and m.object else None,preserve=m.use_deform_preserve_volume if m.type=='ARMATURE' else None) for m in mesh.modifiers],shape_keys=[dict(name=k.name,value=k.value,mute=k.mute) for k in mesh.data.shape_keys.key_blocks] if mesh.data.shape_keys else [],records=forearm_twist._records(mesh),action=rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None),default=str),flush=True)
