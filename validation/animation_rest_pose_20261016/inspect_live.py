"""Read-only artist identity and compact animation/editing witness."""
import bpy
import hashlib
import json
import os
from pathlib import Path
import sys

folder = Path(r'D:\Blender\Projects\Character\X\validation\animation_rest_pose_20261016')
rig = bpy.context.scene.character_designer_setup.rig
saved = bpy.context.scene.character_designer_animation_worklist
assert bpy.data.filepath == r'D:\Blender\Projects\Character\X\X.blend'
assert rig is not None and rig.name == 'CoshaRig'

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()

def action_witness(action):
    if action is None:
        return None
    channels = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    channels.append((curve.data_path, curve.array_index,
                        [(tuple(point.co), tuple(point.handle_left), tuple(point.handle_right),
                          point.interpolation) for point in curve.keyframe_points]))
    return {'name': action.name, 'pointer': action.as_pointer(), 'key_data_sha256': digest(channels)}

report = {
    'filepath': bpy.data.filepath, 'pid': os.getpid(), 'version': bpy.app.version_string,
    'addon_version': sys.modules['character_designer'].bl_info['version'],
    'is_saved': bpy.data.is_saved, 'is_dirty': bpy.data.is_dirty,
    'mode': bpy.context.mode, 'object': getattr(bpy.context.object, 'name', None),
    'scene': bpy.context.scene.name, 'frame': bpy.context.scene.frame_current,
    'rig': rig.name, 'data': rig.data.name, 'data_pointer': rig.data.as_pointer(),
    'pose_position': rig.data.pose_position,
    'rest_sha256': digest([(b.name, list(map(list, b.matrix_local)), b.parent.name if b.parent else None)
                           for b in rig.data.bones]),
    'adopted': 'character_designer_worklist_main_session_v1' in rig,
    'restored': bool(rig.get('character_designer_worklist_main_restored_v1')),
    'active_index': saved.active_index,
    'items': [{'id': item.item_id, 'name': item.name, 'side': item.side,
               'source': action_witness(item.source_action), 'custom': action_witness(item.custom_action)}
              for item in saved.items],
    'armature_data_bound_objects': [obj.name for obj in bpy.data.objects
                                   if obj.type == 'ARMATURE' and obj.data is rig.data],
    'save_keys': [{'config': cfg.name, 'map': km.name, 'op': k.idname,
                   'shift': k.shift, 'alt': k.alt, 'active': k.active}
                 for cfg in (bpy.context.window_manager.keyconfigs.user,)
                 for km in cfg.keymaps for k in km.keymap_items
                 if k.type == 'S' and k.ctrl],
}
(folder / 'live_before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
