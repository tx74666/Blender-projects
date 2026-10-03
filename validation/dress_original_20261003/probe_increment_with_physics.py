import sys
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
import bpy,character_designer
from character_designer import body_original_mode as original, skirt_original_mode as dress, skirt_rig as skirt
from test_skirt_original_mode_blender import fixture,direct_rotation
from test_skirt_shared_rig_blender import world_vertices,geometry_error
character_designer.register();source,rig,main,foreign,record=fixture()
original.enter(bpy.context,main)
direct_rotation(rig,record['chains'][0]['def'][1],.13)
entries=__import__('json').loads(main[original.SESSION])['dress_edit']
wanted=dress.capture(bpy.context,main,entries);vertices=world_vertices(source)
hem=rig.pose.bones[record['controls']['hem']];hem.location.x+=.00003
rig.update_tag(refresh={'OBJECT'});bpy.context.view_layer.update()
actual=dress.capture(bpy.context,main,entries)
print('FORCED_ERROR',max(dress._difference(matrix,actual[owner][name]) for owner,names in wanted.items() for name,matrix in names.items()))
dress.leave(bpy.context,main,entries,desired=wanted)
print('RESTORED_ERROR',dress.verify(bpy.context,main,entries,desired=wanted),'MESH',geometry_error(vertices,world_vertices(source)))
