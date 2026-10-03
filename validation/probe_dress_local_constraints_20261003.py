import bpy, math
from mathutils import Matrix, Vector
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
data=bpy.data.armatures.new('Probe'); rig=bpy.data.objects.new('Probe', data)
bpy.context.collection.objects.link(rig); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name in ('parent','manual','phys','def'):
 b=data.edit_bones.new(name); b.head=(0,0,0); b.tail=(0,1,0)
 if name !='parent': b.parent=data.edit_bones['parent']
bpy.ops.object.mode_set(mode='POSE')
for pb in rig.pose.bones: pb.rotation_mode='XYZ'
m=rig.pose.bones['manual']; p=rig.pose.bones['phys']; d=rig.pose.bones['def']
m.location=(.2,.3,.4); m.rotation_euler=(.1,.2,.3); m.scale=(1.2,.8,1.1)
p.rotation_euler=(.2,.1,-.3)
d.location=(.4,-.2,.3); d.rotation_euler=(.4,.3,.1); d.scale=(.9,1.1,.8)
c=d.constraints.new('COPY_TRANSFORMS'); c.target=rig; c.subtarget='manual'; c.target_space=c.owner_space='LOCAL'
r=d.constraints.new('COPY_ROTATION'); r.target=rig;r.subtarget='phys'; r.target_space=r.owner_space='LOCAL';r.mix_mode='BEFORE'
print('ENUM',[(x.identifier,x.description) for x in c.bl_rna.properties['mix_mode'].enum_items])
def diff(a,b): return max(abs(x-y) for ar,br in zip(a,b) for x,y in zip(ar,br))
for mode in ('REPLACE','BEFORE_FULL','AFTER_FULL','BEFORE','AFTER','BEFORE_SPLIT','AFTER_SPLIT'):
 try: c.mix_mode=mode
 except TypeError: continue
 r.mute=True;bpy.context.view_layer.update()
 out=d.matrix.copy(); product=m.matrix_basis@d.matrix_basis
 print(mode,'M*O',diff(out,product),'O*M',diff(out,d.matrix_basis@m.matrix_basis), 'out',list(out.translation))
 r.mute=False;bpy.context.view_layer.update()
 l,q,s=out.decompose(); expected=Matrix.LocRotScale(l,p.rotation_euler.to_quaternion()@q,s)
 print('PHYS',diff(d.matrix,expected))
