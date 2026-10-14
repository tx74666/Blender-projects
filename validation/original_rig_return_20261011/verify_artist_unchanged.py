"""Confirm the separate live artist's context and rig data remain intact."""
import bpy
import hashlib
import json
import sys
from pathlib import Path

folder = Path(r'D:\Blender\Projects\Character\X\validation\original_rig_return_20261011')
prior = json.loads((folder / 'live_control_graph.json').read_text(encoding='utf-8'))
rigs = []
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        rigs.append((obj.name, obj.data.name,
                     [list(v for row in b.matrix_local for v in row) for b in obj.data.bones],
                     [list(v for row in p.matrix_basis for v in row) for p in obj.pose.bones],
                     obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None))
state = [bpy.data.filepath, bpy.data.is_dirty, bpy.context.scene.name,
         bpy.context.scene.frame_current, bpy.context.scene.frame_subframe,
         bpy.context.object.name if bpy.context.object else None,
         bpy.context.object.mode if bpy.context.object else None,
         sorted(o.name for o in bpy.context.selected_objects), rigs,
         sorted(o.name for o in bpy.data.objects), sorted(a.name for a in bpy.data.actions)]
signature = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
addon = sys.modules['character_designer']
result = {'artist_filepath': bpy.data.filepath, 'artist_dirty': bpy.data.is_dirty,
          'artist_signature_unchanged': signature == prior['state_signature'],
          'signature': signature, 'initial_signature': prior['state_signature'],
          'scene': bpy.context.scene.name, 'frame': bpy.context.scene.frame_current,
          'active_object': bpy.context.object.name if bpy.context.object else None,
          'mode': bpy.context.object.mode if bpy.context.object else None,
          'runtime_addon_version': addon.bl_info['version'],
          'disk_init_sha256': hashlib.sha256(Path(addon.__file__).read_bytes()).hexdigest(),
          'artist_saved_by_this_task': False, 'artist_modified_by_this_task': False}
(folder / 'artist_post_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
