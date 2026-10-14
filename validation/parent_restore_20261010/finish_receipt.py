import bpy
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
folder = Path(r'D:\Blender\Projects\Character\X\validation\parent_restore_20261010')
file = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath) == file
rig = bpy.data.objects['CoshaRig']
names = ('Cosha', 'Clothes', 'Dress', 'Hair', 'Jacket', 'Shoes', 'Stocking')
state = {'parents': {n: getattr(bpy.data.objects[n].parent, 'name', None) for n in names},
         'dirty_before_save': bpy.data.is_dirty,
         'frame': bpy.context.scene.frame_current, 'mode': bpy.context.mode,
         'outliner_children': [a.spaces.active.use_filter_children for a in bpy.context.screen.areas if a.type == 'OUTLINER']}
assert all(bpy.data.objects[n].parent == rig for n in names), str(state)
assert all(state['outliner_children']), str(state)
state['stop_result'] = sorted(bpy.ops.blendermcp.stop_server())
state['save_result'] = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(file), check_existing=False))
assert state['save_result'] == ['FINISHED'], str(state)
state['dirty_after_save'] = bpy.data.is_dirty
state['file_size'] = file.stat().st_size
state['file_sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
state['local_server_running'] = bpy.context.scene.blendermcp_server_running
state['saved_at_utc'] = datetime.now(timezone.utc).isoformat()
report = json.loads((folder / 'restoration.json').read_text(encoding='utf-8'))
report.update({'saved': True, 'save_operator_result': state['save_result'], 'save_receipt': state})
(folder / 'restoration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(state, ensure_ascii=False))
