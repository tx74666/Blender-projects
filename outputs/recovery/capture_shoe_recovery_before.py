"""Save a copy of the live X scene before restoring its three shoe rings."""
import bpy
import json
from datetime import datetime
from pathlib import Path

expected = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath).resolve() == expected.resolve(), bpy.data.filepath
assert bpy.context.mode == 'OBJECT', bpy.context.mode
assert bpy.context.view_layer.objects.active.name == 'Shoes'
assert bpy.data.objects['Shoes'].type == 'MESH'
assert bpy.data.objects['Shoes_Primitive'].type == 'MESH'
output = expected.parent / 'outputs' / 'recovery'
stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup = output / ('X-before-shoe-ring-restore-' + stamp + '.blend')
assert not backup.exists()
report = {
    'backup': str(backup),
    'original_filepath': bpy.data.filepath,
    'mode': bpy.context.mode,
    'objects': {}
}
for name in ('Shoes', 'Shoes_Primitive'):
    obj = bpy.data.objects[name]
    report['objects'][name] = {
        'vertices': len(obj.data.vertices),
        'edges': len(obj.data.edges),
        'faces': len(obj.data.polygons),
        'mesh': obj.data.name,
        'matrix_world': [list(row) for row in obj.matrix_world],
        'uv_layers': [layer.name for layer in obj.data.uv_layers],
        'materials': [m.name if m else None for m in obj.data.materials],
        'vertex_groups': [g.name for g in obj.vertex_groups],
    }
result = bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
assert result == {'FINISHED'}, result
assert Path(bpy.data.filepath).resolve() == expected.resolve(), bpy.data.filepath
assert backup.is_file() and backup.stat().st_size > 1000000
(output / 'live_shoe_recovery_before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('LIVE_SHOE_BACKUP_OK', str(backup), report['objects']['Shoes'])
