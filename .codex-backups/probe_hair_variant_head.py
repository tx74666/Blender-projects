import sys,bpy
sys.path.insert(0,r'D:\Blender\Projects\Character\X\addons')
from character_designer import hair_bones_rig as r, hair_bones_variants as v
old=bpy.data.objects['CoshaRig'];name=r._head_bone(old); b=old.data.bones[name];p=old.pose.bones[name]
print('HEAD',name,'REST',list(b.matrix_local),'HEAD',b.head_local,'TAIL',b.tail_local,'LENGTH',b.length,'POSE',list(p.matrix))
collection=bpy.data.collections.new('probe');bpy.context.scene.collection.children.link(collection)
a=v._create_anchor(bpy.context,collection,bpy.data.objects['Hair2'],old,name,'Hair Attachment')
bb=a.data.bones['Hair Attachment'];print('COPY',list(bb.matrix_local),'HEAD',bb.head_local,'TAIL',bb.tail_local,'LENGTH',bb.length)
