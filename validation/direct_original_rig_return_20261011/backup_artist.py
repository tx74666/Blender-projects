"""Full recoverable copy of the current unsaved artist file, without scene changes."""
import bpy
import hashlib
import json
import sys
from pathlib import Path

folder = Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011')
folder.mkdir(parents=True, exist_ok=True)
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
backup = folder / 'artist_before_direct_return.blend'
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert not backup.exists(), 'Keep the initial artist backup; do not overwrite it.'
before = {'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
          'scene': bpy.context.scene.name, 'frame': bpy.context.scene.frame_current,
          'object': bpy.context.object.name if bpy.context.object else None,
          'mode': bpy.context.object.mode if bpy.context.object else None}
result = bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True, check_existing=False)
assert 'FINISHED' in result and backup.is_file()
after = {'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
         'scene': bpy.context.scene.name, 'frame': bpy.context.scene.frame_current,
         'object': bpy.context.object.name if bpy.context.object else None,
         'mode': bpy.context.object.mode if bpy.context.object else None}
assert before['filepath'] == after['filepath']
assert all(before[k] == after[k] for k in ('scene', 'frame', 'object', 'mode'))
record = {'before': before, 'after': after, 'backup_path': str(backup),
          'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
          'save_result': sorted(result), 'runtime_version': sys.modules['character_designer'].bl_info['version'],
          'blender': bpy.app.version_string,
          'scenes': [{'name': s.name, 'objects': len(s.objects)} for s in bpy.data.scenes]}
(folder / 'artist_backup_receipt.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(record, ensure_ascii=False))
