import bpy, sys, json
from mathutils import Matrix, Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import root_control, limb_ik
cd.register()
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend',use_scripts=False)
rig=bpy.data.objects['CoshaRig']
bpy.context.view_layer.update()
result={'rig_matrix':[list(row) for row in rig.matrix_world],'bones':{}}
for pb in rig.pose.bones:
    if not any(t in pb.name.lower() for t in ('master','foot','toe','heel')):
        continue
    item={'head_rest':list(pb.bone.head_local),'tail_rest':list(pb.bone.tail_local),
          'head_pose':list(pb.head),'basis':[list(row) for row in pb.matrix_basis],
          'role':pb.bone.get(limb_ik.ROLE_KEY),'shape':pb.custom_shape.name if pb.custom_shape else None,
          'translation':list(pb.custom_shape_translation)}
    if pb.custom_shape:
        scale=pb.custom_shape_scale_xyz*(pb.bone.length if pb.use_custom_shape_bone_size else 1)
        local=Matrix.LocRotScale(pb.custom_shape_translation,pb.custom_shape_rotation_euler.to_quaternion(),scale)
        for key,matrix in [('rest',pb.bone.matrix_local),('pose',(pb.custom_shape_transform or pb).matrix)]:
            points=[matrix@local@v.co for v in pb.custom_shape.data.vertices]
            item[key+'_shape_bounds']=[[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]
    result['bones'][pb.name]=item
result['root_record']=root_control.get_record(rig)
print('ROOT_HEIGHT_AUDIT',json.dumps(result),flush=True)
