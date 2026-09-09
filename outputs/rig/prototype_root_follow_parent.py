import bpy,sys,json
from mathutils import Matrix
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import limb_ik,limb_ik_fk
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend')
r=bpy.data.objects['CoshaRig']; limb_ik._mode_set(bpy.context,r,'POSE')
roots=[p.name for p in r.pose.bones if p.parent is None]
before={p.name:p.matrix.copy() for p in r.pose.bones}
limb_ik._mode_set(bpy.context,r,'EDIT')
b=r.data.edit_bones.new('TEST_ROOT');b.head=(0,0,0);b.tail=(0,.1,0);b.use_deform=False
for n in roots:
 if n!='Hips': r.data.edit_bones[n].parent=b
limb_ik._mode_set(bpy.context,r,'POSE')
for n in ['Hips']:
 c=r.pose.bones[n].constraints.new('COPY_TRANSFORMS');c.target=r;c.subtarget='TEST_ROOT';c.owner_space=c.target_space='POSE';c.mix_mode='BEFORE'
p=r.pose.bones['TEST_ROOT'];p.rotation_mode='XYZ'
for label,loc,rot,scale in [('translate',(.1,.05,-.02),(0,0,0),(1,1,1)),('rotate',(.1,.05,-.02),(.1,.2,.15),(1,1,1)),('scale',(.1,.05,-.02),(.1,.2,.15),(1.2,)*3)]:
 p.location=loc;p.rotation_euler=rot;p.scale=scale
 limb_ik_fk._update(bpy.context,r)
 transform=p.matrix.copy()
 errors={n:max(abs(r.pose.bones[n].matrix[i][j]-(transform@m)[i][j]) for i in range(4) for j in range(4)) for n,m in before.items()}
 print('ROOT_PROTOTYPE',label,json.dumps(sorted(errors.items(),key=lambda v:v[1],reverse=True)[:15]),flush=True)

