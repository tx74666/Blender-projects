"""Restore transient inspection UI/connection state; do not edit artist data."""
import bpy
import json
from pathlib import Path

folder = Path(r'D:\Blender\Projects\Character\X\validation\original_bone_diagnosis_20261010')
initial = json.loads((folder / 'live_readonly.json').read_text(encoding='utf-8'))

for area in bpy.context.screen.areas:
    if area.type == 'PROPERTIES':
        area.spaces.active.context = 'DATA'

result = {
    'scene': bpy.context.scene.name,
    'frame': bpy.context.scene.frame_current,
    'active': bpy.context.view_layer.objects.active.name,
    'selected': [obj.name for obj in bpy.context.selected_objects],
    'dirty': bpy.data.is_dirty,
    'properties_context': [area.spaces.active.context for area in bpy.context.screen.areas if area.type == 'PROPERTIES'],
}

# This inspection started an initially disconnected local BlenderMCP server.
result['stop_result'] = sorted(bpy.ops.blendermcp.stop_server())
result['local_server_running'] = bpy.context.scene.blendermcp_server_running
(folder / 'inspection_end_state.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
