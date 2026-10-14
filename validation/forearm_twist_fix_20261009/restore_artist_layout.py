import bpy
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
receipt = json.loads((BASE / 'live_fix_receipt.json').read_text(encoding='utf-8'))
assert receipt['status'] == 'SAVED'
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert bpy.context.area.type == 'CONSOLE'
before = (bpy.context.scene.frame_current, bpy.context.object.name, bpy.context.object.mode,
          bpy.context.object.data.bones.active.name,
          bpy.context.scene.tool_settings.use_keyframe_insert_auto)
assert before == (46, 'CoshaRig', 'POSE', 'CTRL_torso_bend', False)
bpy.context.area.type = 'NODE_EDITOR'
bpy.context.area.ui_type = 'ShaderNodeTree'
assert (bpy.context.scene.frame_current, bpy.context.object.name, bpy.context.object.mode,
        bpy.context.object.data.bones.active.name,
        bpy.context.scene.tool_settings.use_keyframe_insert_auto) == before
result = bpy.ops.wm.save_mainfile()
assert result == {'FINISHED'}
report = {'status': 'SAVED', 'save_result': sorted(result), 'artist': str(artist),
          'artist_sha256': hashlib.sha256(artist.read_bytes()).hexdigest(),
          'restored_area_type': bpy.context.area.type, 'restored_ui_type': bpy.context.area.ui_type,
          'artist_context_preserved': list(before)}
(BASE / 'layout_restore_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('FOREARM_LAYOUT_RESTORED_AND_SAVED', report)
