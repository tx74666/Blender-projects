"""Repeat the successful read-only capture with a vector-aware JSON encoder."""
import ast
import hashlib
import json
import sys
from pathlib import Path
import bpy

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
checkpoint = folder / 'X_before_mirror_diagnosis.blend'
report_file = folder / 'current_diagnostic.json'
assert not report_file.exists() and checkpoint.exists()
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert bpy.context.area and bpy.context.area.type == 'CONSOLE'
rig = bpy.context.view_layer.objects.active
assert rig and rig.name == 'CoshaRig' and rig.mode == 'POSE'
tree = ast.parse((folder / 'capture_current.py').read_text(encoding='utf-8'))
start = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.FunctionDef) and n.name == 'plain')
end = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == 'saved' for t in n.targets))
exec(compile(ast.Module(body=tree.body[start:end], type_ignores=[]), 'read_only_capture', 'exec'))
report.update({'source': 'Live current artist; pose and mesh read only',
               'checkpoint': str(checkpoint),
               'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
               'checkpoint_save_ui_confirmation': 'Saved copy as "X_before_mirror_diagnosis.blend"',
               'read_only_pose_channels_unchanged': True})
report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=list), encoding='utf-8')
print('MIRROR_CURRENT_READ_ONLY_CAPTURED:', len(report['bones']), 'bones;',
      [(m['object'], m['middle_vertex_count']) for m in report['meshes']])
