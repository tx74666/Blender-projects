import bpy, importlib.util, json
from pathlib import Path
root=Path(r'D:\Blender\Projects\Character\X\outputs\review_character_designer')
spec=importlib.util.spec_from_file_location('export_worker',r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\unity_export_worker.py')
worker=importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)
bpy.ops.wm.read_factory_settings(use_empty=True)
a=bpy.data.armatures.new('ProbeArm'); rig=bpy.data.objects.new('ProbeRig',a); bpy.context.scene.collection.objects.link(rig); bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); b=a.edit_bones.new('Hips'); b.head=(0,0,0); b.tail=(0,0,1); bpy.ops.object.mode_set(mode='OBJECT')
d=bpy.data.meshes.new('ProbeMesh'); d.from_pydata([(0,0,0),(1,0,0),(0,0,1)],[],[(0,1,2)]); obj=bpy.data.objects.new('ProbeBody',d); bpy.context.scene.collection.objects.link(obj)
v=obj.vertex_groups.new(name='Hips'); v.add([0,1,2],1,'REPLACE'); m=obj.modifiers.new('Skin','ARMATURE'); m.object=rig
mat=bpy.data.materials.new('Working Principled'); mat.use_nodes=True; obj.data.materials.append(mat)
path=root/'export_unused_texture_source.png'
im=bpy.data.images.new('Unused Offline Texture',width=2,height=2); im.filepath_raw=str(path); im.file_format='PNG'; im.save(); bpy.data.images.remove(im); im=bpy.data.images.load(str(path)); path.unlink()
node=mat.node_tree.nodes.new('ShaderNodeTexImage'); node.image=im
print('PROBE image',im.source,im.is_dirty,'node_outputs_linked',any(s.is_linked for s in node.outputs))
try:
    r=worker.export_job({'objects':[rig.name,obj.name],'rig':rig.name,'filename':'export_unused_texture.fbx','stage':str(root/'export_unused_texture'),'unit_scale':1})
    print('PROBE unused_node_result',r['ok'])
except Exception as ex: print('PROBE unused_node_result',type(ex).__name__,str(ex))
mat.node_tree.nodes.remove(node)
r=worker.export_job({'objects':[rig.name,obj.name],'rig':rig.name,'filename':'export_removed_unused_texture.fbx','stage':str(root/'export_removed_unused_texture'),'unit_scale':1})
print('PROBE removed_unused_node_result',r['ok'])
