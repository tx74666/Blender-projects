"""Compare original hair/main bones with the live cleanup backup, without saves."""
import hashlib
from pathlib import Path
import sys
import bpy

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import hair_bones_rig as rig
from character_designer import hair_bones_binding as binding
from character_designer.selected_bone_weights import _capture_vertex_groups

assert bpy.app.background
saved = Path(r'D:\Blender\Projects\Character\X\X.blend')
backup = saved.parent / '.character_designer_backups' / 'X-before-hair-copy-cleanup-20260908-145318-971885.blend'
digests = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (saved, backup)}
def mesh_state(obj):
    snapshot = rig._mesh_snapshot(obj)
    keys = obj.data.shape_keys
    return (obj.data.name, snapshot['coordinates'], snapshot['topology'],
            tuple((key.name, key.value, tuple(tuple(point.co) for point in key.data)) for key in keys.key_blocks) if keys else ())
def bones(obj):
    return {bone.name: (rig._bone_state(bone), tuple(tuple(row) for row in obj.pose.bones[bone.name].matrix_basis))
            for bone in obj.data.bones}
bpy.ops.wm.open_mainfile(filepath=str(backup), load_ui=False, use_scripts=False)
original = {name: mesh_state(bpy.data.objects[name]) for name in ('Hair1', 'Hair2', 'Hair3')}
original_weights = _capture_vertex_groups(bpy.data.objects['Hair3'])
original_bones = bones(bpy.data.objects['CoshaRig'])
bpy.ops.wm.open_mainfile(filepath=str(saved), load_ui=False, use_scripts=False)
assert all(mesh_state(bpy.data.objects[name]) == value for name, value in original.items())
current = bones(bpy.data.objects['CoshaRig'])
assert all(current[name] == value for name, value in original_bones.items())
source = bpy.data.objects['Hair3']
assert binding.remove_hair_binding(bpy.context, source) == {'removed_bones': 52}
assert _capture_vertex_groups(source) == original_weights
assert bones(bpy.data.objects['CoshaRig']) == original_bones
assert source.parent is None and not any(item.type == 'ARMATURE' for item in source.modifiers)
assert all(hashlib.sha256(path.read_bytes()).hexdigest() == value for path, value in digests.items())
print('SAVED_X_PRESERVATION_AND_REOPEN_REMOVE_PASS: Hair1/Hair2/Hair3 geometry + shape keys, original 56 bones, restored weights; files unchanged', flush=True)
