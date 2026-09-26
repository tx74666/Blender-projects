import sys
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
import bpy,character_designer as cd
import test_shape_key_tools_blender as f
cd.register()
try:f.test_selected_dependency_chain_stops_at_unselected_key()
except Exception as exc:
 print('ERROR',exc)
 obj=bpy.context.object
 print('ACTIVE',obj.active_shape_key_index,obj.active_shape_key.name,obj.show_only_shape_key)
 for k in obj.data.shape_keys.key_blocks:print('KEY',k.name,k.value,k.relative_key.name,list(k.data[0].co))
 obj.data.shape_keys.key_blocks['Untouched'].value=0
 obj.show_only_shape_key=False
 obj.update_tag(refresh={'OBJECT','DATA'});obj.data.update();bpy.context.view_layer.update()
 print('UPDATED',list(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices[0].co))
