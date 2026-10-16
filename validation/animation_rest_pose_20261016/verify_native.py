"""Small isolated native fixture; never opens or saves the artist file."""
import bpy
import bmesh
import json
from pathlib import Path
import sys

folder = Path(r'D:\Blender\Projects\Character\X\validation\animation_rest_pose_20261016')
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as addon
addon.register()
from character_designer import animation_rest_pose as rest

assert hasattr(bpy.ops.character_designer, 'worklist_pose_position')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
data = bpy.data.armatures.new('Rest Display Fixture')
rig = bpy.data.objects.new('Fixture Rig', data)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bone = data.edit_bones.new('root')
bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
bpy.ops.object.mode_set(mode='OBJECT')
scene = bpy.context.scene
scene.character_designer_setup.rig = rig
scene.character_designer_animation_worklist.rig = rig
pb = rig.pose.bones['root']
pb.location.x = 0
pb.keyframe_insert('location', frame=1)
pb.location.x = 3
pb.keyframe_insert('location', frame=10)
scene.frame_set(10)
mesh = bpy.data.meshes.new('Fixture Mesh')
mesh.from_pydata([(0, 0, .5)], [], [])
obj = bpy.data.objects.new('Fixture Shoes', mesh)
bpy.context.collection.objects.link(obj)
group = obj.vertex_groups.new(name='root')
group.add([0], 1, 'REPLACE')
modifier = obj.modifiers.new('Armature', 'ARMATURE')
modifier.object = rig
action, slot = rig.animation_data.action, rig.animation_data.action_slot
matrix = data.bones['root'].matrix_local.copy()
pose = pb.matrix_basis.copy()
def vertices():
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return tuple(evaluated.data.vertices[0].co)
def keys():
    return [[curve.data_path, curve.array_index, [tuple(k.co) for k in curve.keyframe_points]]
        for layer in action.layers for strip in layer.strips
        for bag in strip.channelbags for curve in bag.fcurves]
before_keys = keys()
posed = vertices()
assert abs(posed[0] - 3) < 1e-6, posed
assert bpy.ops.character_designer.worklist_pose_position(position='REST') == {'FINISHED'}
rest_vertices = vertices()
assert abs(rest_vertices[0]) < 1e-6, rest_vertices
assert rest.is_rest(rig)
assert action == rig.animation_data.action and slot.handle == rig.animation_data.action_slot.handle
assert keys() == before_keys and data.bones['root'].matrix_local == matrix
assert pb.matrix_basis == pose
rest.show_pose(bpy.context)
assert vertices() == posed
rig.select_set(False)
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.verts[0].select_set(True)
mesh_selection = tuple(v.select for v in bm.verts)
rest.show_rest(bpy.context)
rest.show_pose(bpy.context)
assert bpy.context.mode == 'EDIT_MESH' and bpy.context.object is obj
assert tuple(v.select for v in bmesh.from_edit_mesh(mesh).verts) == mesh_selection
assert keys() == before_keys and data.bones['root'].matrix_local == matrix
bpy.ops.object.mode_set(mode='OBJECT')
rest.show_rest(bpy.context)
try:
    with rest.resume_for_operation(bpy.context, rig):
        assert data.pose_position == 'POSE'
        raise ValueError('fixture refusal')
except ValueError:
    pass
assert data.pose_position == 'REST' and rest.PREVIEW_KEY in rig
with rest.resume_for_operation(bpy.context, rig):
    assert data.pose_position == 'POSE'
assert data.pose_position == 'POSE' and rest.PREVIEW_KEY not in rig
rest.show_rest(bpy.context)
assert bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'native_fixture.blend')) == {'FINISHED'}
report = {'passed': True, 'version': addon.bl_info['version'], 'posed_vertices': posed,
          'rest_vertices': rest_vertices, 'keyframes_preserved': keys() == before_keys,
          'bone_rest_preserved': data.bones['root'].matrix_local == matrix,
          'mesh_edit_and_selection_preserved': True, 'failure_rest_rollback': True,
          'success_pose_resume': True, 'standard_registration': True,
          'artist_opened': False, 'artist_saved': False}
(folder / 'native_fixture_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
