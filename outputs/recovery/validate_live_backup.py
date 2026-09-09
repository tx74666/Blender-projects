import bpy
import json
from pathlib import Path

folder = Path(r'D:\Blender\Projects\Character\X\outputs\recovery')
report = json.loads((folder / 'live_shoe_recovery_before.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=report['backup'], load_ui=False)
for name, expected in report['objects'].items():
    obj = bpy.data.objects[name]
    actual = (len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons))
    assert actual == (expected['vertices'], expected['edges'], expected['faces'])
    assert [list(row) for row in obj.matrix_world] == expected['matrix_world']
    assert [g.name for g in obj.vertex_groups] == expected['vertex_groups']
    assert [u.name for u in obj.data.uv_layers] == expected['uv_layers']
result = {'backup': report['backup'], 'reopened_successfully': True, 'objects_verified': list(report['objects'])}
(folder / 'live_backup_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('LIVE_BACKUP_REOPEN_VERIFIED', result)
