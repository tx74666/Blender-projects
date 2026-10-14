"""Root-run, read-only native fingerprint of the protected actual X copy."""
import importlib.util
import json
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('forearm_actual_fingerprint_proof', HERE / 'validate_fresh_actual.py')
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)
assert bpy.app.background and not bpy.data.filepath, 'Require factory-startup disposable background Blender.'
backup = HERE / 'X_before_forearm_twist_fix.blend'
assert proof.sha(backup) == proof.BACKUP_SHA
sys.path.insert(0, str(proof.REPOSITORY / 'tools'))
from release_projection import load_source
source = load_source('character_designer', proof.MANIFEST, root=proof.REPOSITORY)
assert source.projection_sha256 == proof.PROJECTION_SHA and source.version == '0.77.12'
sys.path.insert(0, str(proof.CANDIDATE.parent))
import character_designer
assert Path(character_designer.__file__).resolve().parent == proof.CANDIDATE.resolve()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(backup))
from character_designer import forearm_twist as runtime
runtime._complete_runtime_lifecycle()
assert runtime._SESSION is None and runtime._records(bpy.data.objects['Cosha']) == {}
snapshot = proof.protected_snapshot()
result = {'backup': str(backup), 'backup_sha256': proof.BACKUP_SHA,
          'projection_sha256': source.projection_sha256, 'runtime': character_designer.bl_info['version'],
          'blender': bpy.app.version_string, 'protected_sha256': proof.digest(snapshot),
          'protected': snapshot, 'status': 'PASS', 'saved': False}
out = HERE / 'protected_backup_fingerprint.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
assert proof.sha(backup) == proof.BACKUP_SHA
print('ACTUAL_FOREARM_BACKUP_FINGERPRINT_PASS', result['protected_sha256'], str(out), flush=True)
