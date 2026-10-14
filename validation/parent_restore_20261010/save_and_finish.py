"""Save the verified artist scene and close only this task's local connection."""
import bpy
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

folder = Path(r'D:\Blender\Projects\Character\X\validation\parent_restore_20261010')
file = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath) == file and not bpy.app.background
report = json.loads((folder / 'restoration.json').read_text(encoding='utf-8'))
assert report['status'] == 'PASS'
rig = bpy.data.objects['CoshaRig']
names = ('Cosha', 'Clothes', 'Dress', 'Hair', 'Jacket', 'Shoes', 'Stocking')
assert all(bpy.data.objects[n].parent == rig for n in names)
assert bpy.context.scene.name == 'Scene' and bpy.context.scene.frame_current == 46
assert bpy.context.mode == 'POSE' and bpy.context.view_layer.objects.active == rig
assert bpy.ops.wm.save_as_mainfile.poll()
previous = file.stat()
report['stop_result'] = sorted(bpy.ops.blendermcp.stop_server())
assert not bpy.context.scene.blendermcp_server_running
result = bpy.ops.wm.save_as_mainfile(filepath=str(file), check_existing=False)
assert result == {'FINISHED'}, 'Blender did not confirm saving'
assert Path(bpy.data.filepath) == file and not bpy.data.is_dirty
assert all(bpy.data.objects[n].parent == rig for n in names)
assert all(a.spaces.active.use_filter_children for a in bpy.context.screen.areas if a.type == 'OUTLINER')
current = file.stat()
assert current.st_size > 0 and current.st_mtime_ns != previous.st_mtime_ns
report.update({'saved': True, 'save_operator_result': sorted(result), 'filepath': str(file),
               'dirty_after_save': bpy.data.is_dirty, 'local_server_running': False,
               'size': current.st_size, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
               'saved_at_utc': datetime.now(timezone.utc).isoformat()})
(folder / 'restoration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
