import bpy
import json
from datetime import datetime
from pathlib import Path

root = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (root / 'X.blend').resolve()
assert bpy.context.mode == 'OBJECT'
for name, kind in [('Cosha', 'MESH'), ('CoshaRig', 'ARMATURE'), ('Clothes', 'MESH'), ('Stocking', 'MESH'), ('Shoes', 'MESH')]:
    assert bpy.data.objects.get(name) and bpy.data.objects[name].type == kind
backup = root / 'outputs/binding' / ('X-before-quick-binding-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.blend')
assert not backup.exists()
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}
assert Path(bpy.data.filepath).resolve() == (root / 'X.blend').resolve()
report = {'backup': str(backup), 'original': bpy.data.filepath}
(root / 'outputs/binding/live_binding_backup.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('LIVE_BINDING_BACKUP_READY', report)
import character_designer
if character_designer.bl_info['version'] != (0, 43, 1):
    print(bpy.ops.character_designer.refresh_addon())
else:
    print('CHARACTER_DESIGNER_0_43_1_ALREADY_LOADED')
