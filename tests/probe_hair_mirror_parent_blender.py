"""Disposable proof of a head-following native Mirror reference plane."""
import bpy
from mathutils import Matrix, Vector

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
mesh = bpy.data.meshes.new("Hair")
mesh.from_pydata([(1,0,0),(1,0,1),(1,.1,1),(1,.1,0)], [], [(0,1,2,3)])
obj = bpy.data.objects.new("Hair",mesh)
bpy.context.collection.objects.link(obj)
armdata = bpy.data.armatures.new("Rig")
arm = bpy.data.objects.new("Rig",armdata)
bpy.context.collection.objects.link(arm)
arm.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode="EDIT")
bone=armdata.edit_bones.new("head")
bone.head=(0,0,.2)
bone.tail=(0,0,1.2)
bpy.ops.object.mode_set(mode="OBJECT")
group=obj.vertex_groups.new(name="head")
group.add(list(range(4)),1.0,"REPLACE")
mod=obj.modifiers.new("Skin","ARMATURE")
mod.object=arm
mirror=obj.modifiers.new("Mirror","MIRROR")
ref=bpy.data.objects.new("Plane",None)
bpy.context.collection.objects.link(ref)
rest_world=obj.matrix_world.copy()
obj.parent=arm
obj.matrix_parent_inverse=Matrix.Identity(4)
obj.matrix_basis=arm.matrix_world.inverted()@rest_world
ref.matrix_world=rest_world
head_rest=arm.matrix_world@arm.data.bones['head'].matrix_local
child=ref.constraints.new("CHILD_OF")
child.target=arm
child.subtarget="head"
child.inverse_matrix=head_rest.inverted()
mirror.mirror_object=ref
bpy.context.view_layer.update()
def coords():
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m=evaluated.to_mesh()
    result=[evaluated.matrix_world@v.co for v in m.vertices]
    evaluated.to_mesh_clear()
    return result
baseline=coords()
print('REF_REST_ERR', max(abs(ref.matrix_world[i][j]-obj.matrix_world[i][j]) for i in range(4) for j in range(4)))
arm.pose.bones['head'].rotation_mode='XYZ'
arm.pose.bones['head'].location.x=.4
arm.pose.bones['head'].rotation_euler.y=.3
bpy.context.view_layer.update()
head_pose=arm.matrix_world@arm.pose.bones['head'].matrix
deform=head_pose@head_rest.inverted()
print('REF_POSE_ERR', max(abs(ref.matrix_world[i][j]-(deform@obj.matrix_world)[i][j]) for i in range(4) for j in range(4)))
error=max((actual-deform@rest).length for actual,rest in zip(coords(),baseline))
print('MIRROR_HEAD_FOLLOW_ERROR',error)
assert error < 1e-5
before=coords()
arm.location.x=.5
arm.rotation_euler.z=.4
bpy.context.view_layer.update()
expected=arm.matrix_world
error=max((actual-expected@rest).length for actual,rest in zip(coords(),before))
print('ARMATURE_OBJECT_FOLLOW_ERROR',error)
print('ARM', [list(r) for r in arm.matrix_world])
print('OBJ', [list(r) for r in obj.matrix_world])
print('REF', [list(r) for r in ref.matrix_world])
print('EXPECTED_REF', [list(r) for r in (arm.matrix_world@deform@rest_world)])
print('ERRORS', [(a-expected@b).length for a,b in zip(coords(),before)])
assert error < 1e-5
