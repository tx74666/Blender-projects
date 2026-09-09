import sys
sys.path.insert(0, r'D:\Blender\Projects\Character\X\tests')
import test_hair_bones_variants_blender as t
try:t.test_owned_source_rebinding_and_transforms()
except Exception as e:
 import bpy
 from character_designer import hair_bones_variants as v,hair_bones_rig as r
 s=bpy.data.objects['Hair']; c=v.variants_for(s)[0]; n=c.get(v.MESH_KEY); a=c.get(v.ARMATURE_KEY); old=bpy.data.objects['Character']
 for o in (s,n,a,old):
  print('OBJ',o.name,'WORLD',list(o.matrix_world),'BASIS',list(o.matrix_basis),'PARENTINV',list(o.matrix_parent_inverse))
  if o.type=='ARMATURE':
   for p in o.pose.bones:
    if p.name in ('Hair Attachment','spine.006'): print('BONE',p.name,'REST',list(p.bone.matrix_local),'POSE',list(p.matrix))
 print('POINTS',t.evaluated_points(s)[:2],t.evaluated_points(n)[:2])
 print('WEIGHTS',t.weights(s)[0],t.weights(n)[0])
 print('MIRROR',list(s.get(r.MIRROR_KEY).matrix_world),list(n.get(r.MIRROR_KEY).matrix_world))
 raise
