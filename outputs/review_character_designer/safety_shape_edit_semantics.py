import sys
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
import bpy,bmesh,character_designer as cd
import test_shape_key_tools_blender as f
cd.register()
for active_index in [1,0]:
 obj,basis,parent,child=f.make_fixture()
 bpy.ops.object.mode_set(mode='OBJECT');obj.active_shape_key_index=active_index;bpy.ops.object.mode_set(mode='EDIT')
 bm=bmesh.from_edit_mesh(obj.data);bm.verts.ensure_lookup_table()
 def state(label):
  print(label,'active',active_index,'mesh',[k.data[0].co.y for k in [basis,parent,child]],'layers',[bm.verts[0][bm.verts.layers.shape.get(k.name)].y for k in [basis,parent,child]],'co',bm.verts[0].co.y)
 state('original');bm.verts[0].co.y+=1;state('edit')
 obj.update_from_editmode();state('flushed')
 obj.update_from_editmode();state('flushed_twice')
 bpy.ops.object.mode_set(mode='OBJECT');print('exit',[k.data[0].co.y for k in [basis,parent,child]])
