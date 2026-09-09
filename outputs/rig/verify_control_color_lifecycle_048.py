import sys
sys.path[:0] = [r'D:\MyRepository\Blender-addons-by-Randy\addons', r'D:\MyRepository\Blender-addons-by-Randy\tests']
import bpy
import test_limb_ik_blender as base
import test_hair_bones_binding_blender as hair_test
from character_designer import limb_ik, control_colors as colors, hair_bones_binding as binding
base.ensure_registered()
base.reset_scene()
arm = base.make_humanoid()
_, settings = base.analyze(arm)
shoulder_original = colors.capture_bone(arm.pose.bones['shoulder.L'])
assert bpy.ops.character_designer.limb_ik_build_arm() == {'FINISHED'}
assert colors.BACKUP_KEY in arm.pose.bones['CTRL_hand_IK.L']
assert colors.BACKUP_KEY in arm.pose.bones['shoulder.L']
for name in ('CTRL_hand_IK.L', 'CTRL_elbow_pole.R'):
    arm.pose.bones[name].color.custom.normal = (.231, .412, .532)
tracked = {pb.name: colors.capture_bone(pb) for pb in arm.pose.bones if colors.BACKUP_KEY in pb}
assert bpy.ops.character_designer.limb_ik_rebuild() == {'FINISHED'}
assert all(colors.capture_bone(arm.pose.bones[name]) == state for name, state in tracked.items()), 'Successful rebuild lost artist color or backup'
original_remove = limb_ik._remove_owned
def fail_after_remove(*args, **kwargs):
    original_remove(*args, **kwargs)
    raise RuntimeError('injected post-remove color recovery test')
limb_ik._remove_owned = fail_after_remove
try:
    assert base.cancelled_result(lambda: bpy.ops.character_designer.limb_ik_remove('EXEC_DEFAULT')) == {'CANCELLED'}
finally:
    limb_ik._remove_owned = original_remove
assert all(colors.capture_bone(arm.pose.bones[name]) == state for name, state in tracked.items()), 'Failed removal lost artist color or backup'
assert bpy.ops.character_designer.limb_ik_remove('EXEC_DEFAULT') == {'FINISHED'}
assert colors.capture_bone(arm.pose.bones['shoulder.L']) == shoulder_original, 'Native source did not restore its original palette'
assert not colors.has_backup(arm)
print('LIMB_COLOR_LIFECYCLE_PASSED')
source, plans, arm = hair_test.scene_fixture()
result = binding.bind_hair(bpy.context, source, plans, bone_count=4, armature=arm)
colors.apply(arm)
names = [name for chain in result['chains'] for name in chain['bones']]
arm.pose.bones[names[0]].color.custom.normal = (.234, .345, .456)
before = {name: colors.capture_bone(arm.pose.bones[name]) for name in names}
states = binding._owned_bone_snapshot(arm, names)
binding.rig._mode(bpy.context, arm, 'EDIT')
for name in reversed(names):
    arm.data.edit_bones.remove(arm.data.edit_bones[name])
binding._restore_owned_bones(bpy.context, arm, states)
assert all(colors.capture_bone(arm.pose.bones[name]) == state for name, state in before.items()), 'Hair reconstruction lost pose palette or original backup'
binding.rig._mode(bpy.context, source, 'OBJECT')
binding.remove_hair_binding(bpy.context, source)
assert not colors.has_backup(arm)
print('HAIR_COLOR_RECOVERY_PASSED')
