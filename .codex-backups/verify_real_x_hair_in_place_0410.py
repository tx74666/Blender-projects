"""Validate cleanup and reversible original-Hair3 binding in an unsaved copy."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix

assert bpy.app.background
input_path = Path(bpy.data.filepath)
assert input_path.name == 'X.hair-in-place-0410-input.blend'
digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\tests')
from character_designer import hair_bones_binding as binding
from character_designer import hair_bones_groups as groups
from character_designer import hair_bones_rig as rig
from character_designer import hair_bones_variants as variants
from test_hair_bones_rig_blender import evaluated_points, weights
from test_hair_bones_variants_blender import source_state

source = bpy.data.objects['Hair3']
main_rig = bpy.data.objects['CoshaRig']
original_sources = {name: bpy.data.objects[name] for name in ('Hair1', 'Hair2', 'Hair3')}
source_original = source_state(source)
original_bones = {bone.name: (rig._bone_state(bone), main_rig.pose.bones[bone.name].matrix_basis.copy()) for bone in main_rig.data.bones}
cleanup = binding.remove_generated_copies(bpy.context, source)
assert cleanup == {'removed_meshes': 2, 'removed_rigs': 2}, cleanup
assert not variants.variants_for(source)
assert all(bpy.data.objects.get(name) is obj for name, obj in original_sources.items())
assert source_state(source) == source_original
binding._reveal_source(bpy.context, main_rig)
rig._mode(bpy.context, source, 'OBJECT')
assert binding.resolve_target(bpy.context, source) == (main_rig, 'Head')
_, plans = groups.build_plans(bpy.context, source=source)
assert len(plans) == 7
baseline = evaluated_points(source)
mesh_objects = {obj for obj in bpy.data.objects if obj.type == 'MESH'}
rig_objects = {obj for obj in bpy.data.objects if obj.type == 'ARMATURE'}
for cycle in range(2):
    result = binding.bind_hair(bpy.context, source, plans, bone_count=4)
    assert result['armature'] is main_rig and result['parent_bone'] == 'Head'
    assert len(result['chains']) == 13 and len(result['cap_vertices']) == 162
    assert len(main_rig.data.bones) == len(original_bones) + 52
    assert {obj for obj in bpy.data.objects if obj.type == 'MESH'} == mesh_objects
    assert {obj for obj in bpy.data.objects if obj.type == 'ARMATURE'} == rig_objects
    skin = weights(source)
    roots = {index for plan in plans for index in plan['layers'][0]}
    for index in set(result['cap_vertices']) | roots:
        assert skin[index] == {'Head': 1.0}, (index, skin[index])
    bind_error = max((first-second).length for first, second in zip(evaluated_points(source), baseline))
    assert bind_error < 2e-5, bind_error
    for chain in result['chains']:
        assert main_rig.data.bones[chain['bones'][0]].parent.name == 'Head'
    head = main_rig.pose.bones['Head']
    head.matrix_basis = Matrix.Translation((.01, .02, -.01)) @ Matrix.Rotation(.2, 4, 'Y')
    bpy.context.view_layer.update()
    delta = main_rig.matrix_world @ head.matrix @ head.bone.matrix_local.inverted() @ main_rig.matrix_world.inverted()
    expected = tuple(delta @ point for point in baseline)
    follow_error = max((first-second).length for first, second in zip(evaluated_points(source), expected))
    assert follow_error < 3e-5, follow_error
    head.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    removed = binding.remove_hair_binding(bpy.context, source)
    assert removed['removed_bones'] == 52
    assert source_state(source) == source_original
    assert len(main_rig.data.bones) == len(original_bones)
    for name, (rest, pose) in original_bones.items():
        assert rig._bone_state(main_rig.data.bones[name]) == rest
        assert main_rig.pose.bones[name].matrix_basis == pose

assert hashlib.sha256(input_path.read_bytes()).hexdigest() == digest
print('REAL_X_IN_PLACE_PASS=' + json.dumps(dict(cleanup=cleanup, source='Hair3', source_vertices=len(source.data.vertices),
      cap_vertices=162, chains=13, hair_bones=52, bind_error=bind_error, head_follow_error=follow_error,
      cycles=2, original_sources_preserved=True, original_bones_preserved=True, input_unchanged=digest)), flush=True)
