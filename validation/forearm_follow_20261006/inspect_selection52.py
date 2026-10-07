import bpy
assert bpy.app.background
arm = bpy.data.armatures.new('Selection probe')
obj = bpy.data.objects.new('Selection probe', arm)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bone = arm.edit_bones.new('Bone')
bone.tail = (0, 1, 0)
bpy.ops.object.mode_set(mode='POSE')
for item in (arm.bones['Bone'], obj.pose.bones['Bone'], arm.bones):
    print('SELECTION_RNA', type(item).__name__, [(p.identifier, p.type, p.is_readonly) for p in item.bl_rna.properties if 'select' in p.identifier or p.identifier == 'active'], flush=True)
