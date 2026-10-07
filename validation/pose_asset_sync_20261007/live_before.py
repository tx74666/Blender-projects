import json
import os
from pathlib import Path
import bpy
import character_designer
from character_designer import body_original_mode, control_pose_assets, limb_ik_fk

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath).resolve() == artist.resolve()
rig = bpy.context.view_layer.objects.active
assert rig and rig.type == 'ARMATURE'
checkpoint = folder / 'X_before_pose_asset_sync.blend'
assert not checkpoint.exists(), 'Do not overwrite the artist checkpoint'
report = {'pid': os.getpid(), 'runtime': bpy.app.version_string,
          'addon': character_designer.bl_info['version'], 'source': character_designer.__file__,
          'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty, 'mode': bpy.context.mode,
          'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
          'rig': rig.name, 'original': body_original_mode.active(rig),
          'selected': [pb.name for pb in rig.pose.bones if (pb if hasattr(pb, 'select') else pb.bone).select],
          'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
          'rest': control_pose_assets.native_rest(rig),
          'pose': {p.name: [list(row) for row in p.matrix] for p in rig.pose.bones},
          'actions': [{'name': a.name, 'asset': bool(a.asset_data), 'users': a.users} for a in bpy.data.actions],
          'camera': bpy.context.scene.camera.name if bpy.context.scene.camera else None}
result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
assert result == {'FINISHED'} and checkpoint.exists()
report['checkpoint'] = str(checkpoint)
assert Path(bpy.data.filepath).resolve() == artist.resolve()
(folder / 'live_before.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('POSE_SYNC_CHECKPOINT', report['addon'], report['rig'], report['selected'], report['original'])
