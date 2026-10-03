"""Refresh and reversibly verify Original on the current artist rig."""
import json
import sys
import traceback
from pathlib import Path
import bpy

area = bpy.context.area
output = Path(r'D:\Blender\Projects\Character\X\validation\original_0704_live.json')
result = {'success': False}
try:
    old = sys.modules['character_designer']
    old._reload_addon_deferred()
    current = sys.modules['character_designer']
    current._validate_registration_integrity()
    assert current.bl_info['version'] == (0, 70, 4)
    assert not current.ADDON_REFRESH_LAST_ERROR, current.ADDON_REFRESH_LAST_ERROR
    from character_designer import body_original_mode as original, bone_display, limb_ik
    from character_designer import control_pose_assets as poses, refine_symmetry as repair
    rig = bone_display.character_rig(bpy.context)
    assert rig.name == 'CoshaRig', rig.name
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
              and any(mod.type == 'ARMATURE' and mod.object == rig for mod in obj.modifiers)]
    protected = {obj.name: repair.fingerprint(obj) for obj in meshes}
    rest = poses.native_rest(rig)
    before = original._channels(rig)
    baseline = original._pose(rig)
    bpy.ops.wm.save_as_mainfile(filepath=r'D:\Blender\Projects\Character\X\validation\X_before_original_0704_20261002.blend', copy=True)
    entered = original.enter(bpy.context, rig)
    entered_channels = original._channels(rig)
    name = 'thigh.L'
    pb = rig.pose.bones[name]
    matrix = pb.matrix.copy()
    try:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler.x += .02
        original._update(bpy.context, rig)
        rotation_change = poses._difference(matrix, pb.matrix)
        assert rotation_change > .001, rotation_change
    finally:
        original._restore_channels(rig, entered_channels)
        original._update(bpy.context, rig)
    original.leave(bpy.context, rig)
    returned_error = original._verify(rig, baseline)
    assert before == original._channels(rig), 'Unedited return changed pose channels'
    limb_ik._validate_inventory(rig)
    assert rest == poses.native_rest(rig), 'Rest or native structure changed'
    assert protected == {obj.name: repair.fingerprint(obj) for obj in meshes}, 'Mesh, weights, keys or binding changed'
    # Leave the requested direct Original workspace ready; the test rotation was undone.
    original.enter(bpy.context, rig)
    assert rest == poses.native_rest(rig)
    assert protected == {obj.name: repair.fingerprint(obj) for obj in meshes}
    result.update(success=True, version=current.bl_info['version'], rig=rig.name,
                  native_bones=entered['bones'], suspended_constraints=entered['constraints'],
                  probe_bone=name, probe_rotation_matrix_change=rotation_change,
                  test_rotation_restored=True, return_matrix_error=returned_error,
                  exact_return_channels=True, protected_meshes=list(protected),
                  protected_meshes_preserved=True, rest_preserved=True,
                  original_active=original.active(rig), saved=False)
    print('ORIGINAL_0704_LIVE_OK', entered, rotation_change, returned_error)
except Exception:
    result['error'] = traceback.format_exc()
    print(result['error'])
finally:
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    area.type = 'NODE_EDITOR'
    area.ui_type = 'GeometryNodeTree'
