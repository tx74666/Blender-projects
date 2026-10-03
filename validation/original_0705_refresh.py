"""Refresh while Original is active; validate persistent recovery without edits."""
import json
import sys
from pathlib import Path
import bpy

area = bpy.context.area
try:
    from character_designer import body_original_mode as original, refine_symmetry as repair, control_pose_assets as poses
    rig = bpy.data.objects['CoshaRig']
    state = rig[original.SESSION]
    before = original._channels(rig)
    rest = poses.native_rest(rig)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
              and any(mod.type == 'ARMATURE' and mod.object == rig for mod in obj.modifiers)]
    protected = {obj.name: repair.fingerprint(obj) for obj in meshes}
    sys.modules['character_designer']._reload_addon_deferred()
    current = sys.modules['character_designer']
    current._validate_registration_integrity()
    assert current.bl_info['version'] == (0, 70, 5)
    assert not current.ADDON_REFRESH_LAST_ERROR
    from character_designer import body_original_mode as new, control_pose_assets as new_poses, refine_symmetry as new_repair
    assert new.active(rig) and state == rig[new.SESSION]
    assert before == new._channels(rig) and rest == new_poses.native_rest(rig)
    assert protected == {obj.name: new_repair.fingerprint(obj) for obj in meshes}
    # Prove the refreshed runtime can still return, then leave direct bones ready.
    desired = new._pose(rig)
    new.leave(bpy.context, rig)
    new._verify(rig, desired)
    new.enter(bpy.context, rig)
    assert rest == new_poses.native_rest(rig)
    assert protected == {obj.name: new_repair.fingerprint(obj) for obj in meshes}
    assert bpy.ops.wm.save_as_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend') == {'FINISHED'}
    result = dict(version=current.bl_info['version'], original_active=new.active(rig),
                  active_session_refresh_preserved=True, refreshed_return_checked=True,
                  mesh_keys_weights_preserved=True, rest_preserved=True, saved=True,
                  blend=bpy.data.filepath, native_bones=len(json.loads(rig[new.SESSION])['names']))
    Path(r'D:\Blender\Projects\Character\X\validation\original_0705_live.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('ORIGINAL_0705_SAVED', result)
finally:
    area.type = 'NODE_EDITOR'
    area.ui_type = 'GeometryNodeTree'
