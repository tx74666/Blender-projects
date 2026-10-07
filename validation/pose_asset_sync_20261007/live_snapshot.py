"""Read-only snapshot from the artist's Blender Python Console."""
import json
import os
from pathlib import Path

import bpy
import character_designer
from character_designer import control_pose_assets as poses, bone_display
from character_designer import body_original_mode as original

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
if Path(bpy.data.filepath).resolve() != artist.resolve():
    raise RuntimeError('Unexpected artist file; no snapshot made.')
rig = bpy.context.view_layer.objects.active
if rig is None or rig.type != 'ARMATURE' or rig.name != 'CoshaRig':
    raise RuntimeError('Select CoshaRig before this verification.')
bpy.context.view_layer.update()
evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
animation = rig.animation_data
action = animation.action if animation else None
def curves(item):
    from character_designer import animation_retarget
    return [(c.data_path, c.array_index, c.mute,
             [(list(p.co), p.interpolation, list(p.handle_left), list(p.handle_right))
              for p in c.keyframe_points])
            for c in animation_retarget._curves(item, None)]
data = {
    'stage': STAGE, 'pid': os.getpid(), 'file': bpy.data.filepath,
    'version': character_designer.bl_info['version'], 'source': character_designer.__file__,
    'current_screen': bpy.context.window.screen.name if bpy.context.window else None,
    'mode': bpy.context.mode, 'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
    'active_object': rig.name, 'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
    'selected': sorted(pb.name for pb in rig.pose.bones
                       if (pb if hasattr(pb, 'select') else pb.bone).select),
    'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto,
    'assigned_action': action.name if action else None,
    'assigned_slot': animation.action_slot.identifier if animation and animation.action_slot else None,
    'action_curves': curves(action) if action else None,
    'original': rig.get(original.SESSION), 'rest': poses.native_rest(rig),
    'display': bone_display._snapshot(rig),
    'matrices': {n: [list(row) for row in evaluated.pose.bones[n].matrix] for n in poses.native_rest(rig)},
    'channels': {pb.name: {k: list(getattr(pb,k)) for k in poses._TRANSFORMS} | {
        'mode': pb.rotation_mode, 'ik_fk': pb.get('ik_fk')} for pb in rig.pose.bones},
    'assets': [{ 'name': a.name, 'metadata': a.get(poses.ASSET_METADATA),
                'curves': curves(a), 'fake_user': a.use_fake_user}
               for a in bpy.data.actions if a.asset_data],
    'browsers': [{'screen': s.name, 'library': a.spaces.active.params.asset_library_reference,
                  'actions_visible': a.spaces.active.params.filter_asset_id.filter_action,
                  'search': a.spaces.active.params.filter_search,
                  'catalog_visibility': a.spaces.active.params.asset_catalog_visibility}
                 for s in bpy.data.screens for a in s.areas
                 if a.type == 'FILE_BROWSER' and a.spaces.active.params is not None
                 and hasattr(a.spaces.active.params, 'asset_library_reference')],
}
target = folder / ('live_' + STAGE + '.json')
target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('POSE_LIVE_SNAPSHOT', STAGE, data['version'], data['selected'],
      [a['name'] for a in data['assets']])
