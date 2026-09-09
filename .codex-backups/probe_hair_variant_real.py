import sys
sys.path.insert(0,r'D:\Blender\Projects\Character\X\tests')
import test_real_x_hair_variants_blender as t
try:t.main()
except Exception:
 import bpy
 from character_designer import hair_bones_variants as v,hair_bones_rig as r
 s=bpy.data.objects['Hair2'];c=v.variants_for(s)[0];n=c.get(v.MESH_KEY);a=c.get(v.ARMATURE_KEY);old=bpy.data.objects['CoshaRig']
 for o in (s,n,a,old):
  print('OBJ',o.name,'WORLD',list(o.matrix_world),'BASIS',list(o.matrix_basis),'PARENT',o.parent,'SCALE',o.scale,'DELTA',o.delta_scale)
  if o.type=='ARMATURE':
   for p in o.pose.bones:
    if p.name in ('Hair Attachment','spine.006') or p.select:print('BONE',p.name,'REST',list(p.bone.matrix_local),'POSE',list(p.matrix),'SKIN',list(p.matrix @ p.bone.matrix_local.inverted()))
 print('COORD ERR', max((sv.co-nv.co).length for sv,nv in zip(s.data.vertices,n.data.vertices)))
 print('POINTS',t.points(s)[:2],t.points(n)[:2])
 print('MODS',[(m.type,m.name) for m in n.modifiers]);raise
