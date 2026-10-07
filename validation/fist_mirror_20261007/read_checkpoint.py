"""Read the protected current artist checkpoint in an isolated process."""
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
assert not report_file.exists()
checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
sys.path.insert(0, str(folder.parent / 'fist_current_file_20261007' / 'approved_release_0772' / 'addons'))
import character_designer
bpy.ops.wm.open_mainfile(filepath=str(checkpoint), load_ui=False)
rig = bpy.data.objects['CoshaRig']
assert rig.type == 'ARMATURE'
tree = ast.parse((folder / 'capture_current.py').read_text(encoding='utf-8'))
start = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.FunctionDef) and n.name == 'plain')
end = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == 'saved' for t in n.targets))
exec(compile(ast.Module(body=tree.body[start:end], type_ignores=[]), 'read_only_snapshot', 'exec'))
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == checkpoint_hash
report.update({'checkpoint': str(checkpoint), 'checkpoint_sha256': checkpoint_hash,
               'source': 'Protected current artist checkpoint, isolated read-only process',
               'scene_saved_by_background_process': False,
               'read_only_pose_channels_unchanged': True})
report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=list), encoding='utf-8')
print('CURRENT_CHECKPOINT_DIAGNOSTIC_CAPTURED:', len(report['bones']), 'bones;',
      [(m['object'], m['middle_vertex_count']) for m in report['meshes']])
