"""Freeze only the authorized bone-length patch onto verified CD 0.77.16."""
import ast
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source

BASELINE = Path(r'D:\Blender\Projects\Character\X\validation\animation_in_front_20261010\release_07716\release_projection_07716.json')
baseline = load_source('character_designer', BASELINE)
folder = Path(__file__).resolve().parent / 'release_07717'
source = folder / 'character_designer'
canonical = REPO / 'addons' / 'character_designer'
payload = dict(baseline.files)

# Runtime implementation is developed in canonical sources. Freeze the exact
# new block onto the previously deployed worker, excluding unrelated pending
# Dress and evaluation-copy work in the shared development tree.
current_worker = (canonical / 'unity_export_worker.py').read_text(encoding='utf-8')
start = current_worker.index('    length_spec = importlib.util.spec_from_file_location(')
end = current_worker.index('    files.insert(0, filename)', start)
block = current_worker[start:end]
worker = payload[Path('unity_export_worker.py')].decode('utf-8')
assert 'bone_rest_lengths' not in worker
worker = worker.replace('import importlib\n', 'import importlib\nimport importlib.util\n', 1)
worker = worker.replace("    if job.get('simple_materials'):\n        import importlib.util\n",
                        "    if job.get('simple_materials'):\n", 1)
worker = worker.replace('    files.insert(0, filename)', block + '    files.insert(0, filename)', 1)
worker = worker.replace("            'objects': [obj.name for obj in objects], 'rigs': rigs,\n",
                        "            'objects': [obj.name for obj in objects], 'rigs': rigs,\n"
                        "            **({'bone_rest_lengths': bone_lengths} if bone_lengths is not None else {}),\n", 1)
assert worker.count("'bone_rest_lengths': bone_lengths") == 1
payload[Path('unity_export_worker.py')] = worker.encode('utf-8')

# This module differs from the deployed baseline only by the new import and
# recovery hook. Enforce that rather than shipping another task's source edit.
link_source = (canonical / 'animation_link_source.py').read_text(encoding='utf-8')
hook_start = link_source.index('        # Optional CD metadata belongs to this exact FBX,')
hook_end = link_source.index('        # _mapping checks every bind origin and parent;', hook_start)
without_hook = link_source[:hook_start] + link_source[hook_end:]
without_hook = without_hook.replace('from . import animation_link, unity_animation, bone_rest_lengths',
                                   'from . import animation_link, unity_animation', 1)
assert without_hook == payload[Path('animation_link_source.py')].decode('utf-8')
payload[Path('animation_link_source.py')] = link_source.encode('utf-8')
payload[Path('bone_rest_lengths.py')] = (canonical / 'bone_rest_lengths.py').read_bytes()
payload[Path('__init__.py')] = payload[Path('__init__.py')].replace(
    b'"version": (0, 77, 16)', b'"version": (0, 77, 17)', 1)

for relative, content in payload.items():
    if relative.suffix == '.py':
        ast.parse(content, filename=str(relative))
    target = source / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

manifest = {'schema_version': 1, 'module': 'character_designer', 'version': '0.77.17',
            'source_root': str(source),
            'files': {relative.as_posix(): hashlib.sha256(content).hexdigest()
                      for relative, content in sorted(payload.items())},
            'source_provenance': {
                'canonical_root': str(canonical), 'baseline_manifest': str(BASELINE),
                'baseline_manifest_sha256': baseline.projection_sha256,
                'scope': 'CD terminal bone length metadata and exact-FBX import recovery only',
                'new_module': 'bone_rest_lengths.py',
                'modified_modules': ['unity_export_worker.py', 'animation_link_source.py', '__init__.py'],
                'worker_projection': 'Exact canonical bone-length block on verified deployed worker',
                'artist_scene_modified': False}}
path = folder / 'release_projection_07717.json'
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
verified = load_source('character_designer', path)
print(json.dumps({'version': verified.version, 'files': len(verified.files),
                  'projection': str(path), 'sha256': verified.projection_sha256}, indent=2))
