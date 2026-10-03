"""Exercise Dress visibility on the saved Cosha only; never save X.blend."""
import hashlib
import json
import sys
from pathlib import Path
import bpy

sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/addons')
import character_designer
from character_designer import bone_display as display, body_original_mode as original
from character_designer import refine_symmetry as repair, control_pose_assets as poses

character_designer.register()
bpy.ops.wm.open_mainfile(filepath='D:/Blender/Projects/Character/X/X.blend')
main = bpy.data.objects['CoshaRig']
groups = original._native_groups(bpy.context, main)
dress, names = next(iter(groups['DRESS'].items()))
assert original.active(main)
assert not dress.visible_get() and dress.hide_get()
layer = bpy.context.view_layer
before_pose = original._pose(main)
before_channels = original._channels(main)
before_dress_channels = original._channels(dress)

def protected():
    meshes = [(obj.name, repair.fingerprint(obj)) for obj in bpy.context.scene.objects if obj.type == 'MESH']
    rest = [(obj.name, [(b.name, b.parent.name if b.parent else None,
                        tuple(tuple(row) for row in b.matrix_local), b.use_deform)
                       for b in obj.data.bones],
             obj.parent.name if obj.parent else None, obj.parent_type, obj.parent_bone,
             tuple(tuple(row) for row in obj.matrix_parent_inverse))
            for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    return hashlib.sha256(repr((meshes, rest)).encode()).hexdigest()

def helpers():
    return {obj.name: (obj.hide_viewport, obj.hide_get(), obj.hide_render)
            for obj in bpy.context.scene.objects if obj.type != 'ARMATURE'}

before_hash, before_helpers = protected(), helpers()
raw = main[original.SESSION]
saved = json.loads(raw)
before_error = max(poses._difference(before_pose[n], main.pose.bones[n].matrix) for n in before_pose)
result = {'version': list(character_designer.bl_info['version']), 'rig': dress.name,
          'target_bones': len(names), 'before_object_hidden': dress.hide_get(),
          'before_group_blue': original.group_visible(bpy.context, main, 'DRESS'),
          'legacy_object_snapshot_missing': all('object_visibility' not in state
              for state in saved['extra_display'].values()), 'saved_artist_scene': False}
assert not result['before_group_blue']
original.show_group(bpy.context, main, 'DRESS')
assert original.group_visible(bpy.context, main, 'DRESS') and dress.visible_get()
assert all(not getattr(dress.pose.bones[n], 'hide', dress.data.bones[n].hide) for n in names)
assert protected() == before_hash and helpers() == before_helpers
assert original._channels(main) == before_channels
assert original._channels(dress) == before_dress_channels
updated = json.loads(main[original.SESSION])
assert all(updated[k] == saved[k] for k in saved if k != 'extra_display')
assert any(state.get('object_visibility', {}).get('hidden') is True
           for state in updated['extra_display'].values())
result.update(legacy_reveal_visible=True, legacy_snapshot_added=True,
              reveal_pose_channels_unchanged=True, unrelated_objects_unchanged=True)
original.show_group(bpy.context, main, 'DRESS')
assert not original.group_visible(bpy.context, main, 'DRESS')
assert dress.visible_get(), 'Turning off a group must not hide the whole rig object'
original.show_group(bpy.context, main, 'DRESS')
original.leave(bpy.context, main)
assert dress.hide_get() and not display._object_visible(dress)
assert protected() == before_hash
original._verify(main, before_pose)
result['legacy_controls_return_restored_object_hidden'] = True

pairs = display._control_collections(bpy.context, main, 'DRESS')
assert not display._controls_visible(pairs)
display.show_controls(bpy.context, main, 'DRESS', toggle=True)
assert dress.visible_get() and display._controls_visible(pairs)
assert protected() == before_hash and helpers() == before_helpers
result['controls_hidden_object_revealed'] = True

dress.hide_set(True)
assert not display._controls_visible(pairs)
original.enter(bpy.context, main)
assert dress.visible_get() and original.group_visible(bpy.context, main, 'DRESS')
original.leave(bpy.context, main)
assert dress.hide_get(), 'New sessions must restore their original object flag'
assert protected() == before_hash and helpers() == before_helpers
original._verify(main, before_pose)
result.update(new_session_reveal_and_restore=True, protected_hash=before_hash,
              protected_content_unchanged=True, helper_visibility_unchanged=True,
              layer=layer.name, baseline_pose_error=before_error)
out = Path('D:/Blender/Projects/Character/X/validation/dress_visibility_0711_real_verification_20261003.json')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('DRESS_REAL_VERIFICATION', json.dumps(result), flush=True)
