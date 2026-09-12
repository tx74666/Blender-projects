"""Apply the verified Roll-only repair to the open X, with a fresh backup."""
import bpy, json, runpy
from datetime import datetime
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
assert bpy.context.mode == 'OBJECT', 'Finish the current edit first.'
assert bpy.context.object and bpy.context.object.name == 'CoshaRig'
backup = out/'backups'/('X_before_roll_repair_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
bpy.ops.ed.undo_push(message='Before native Roll repair')
repair_ns = runpy.run_path(str(out/'repair_reversal_20260912.py'))
report = repair_ns['repair']()
report['backup'] = str(backup)
bpy.ops.ed.undo_push(message='Restore native bone Roll')
(out/'reversal_0550_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('ROLL_REPAIR_OK', len(report['restored_roll_bones']), 'native bones; mesh and weights unchanged')
