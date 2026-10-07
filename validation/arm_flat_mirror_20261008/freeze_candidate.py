"""Freeze the previously approved release with only the mirror correction."""
import hashlib
import json
import sys
from pathlib import Path

folder = Path(__file__).resolve().parent
repo = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path.insert(0, str(repo / 'tools'))
from release_projection import load_source

previous = folder.parent / 'fist_current_file_20261007/approved_release_0772/release_projection.json'
base = load_source('character_designer', previous, root=repo)
assert base.version == '0.77.2'
destination = folder / 'approved_release_0773'
assert not destination.exists(), 'Do not overwrite a frozen release'
files = dict(base.files)
old = b'"version": (0, 77, 2)'
assert files[Path('__init__.py')].count(old) == 1
files[Path('__init__.py')] = files[Path('__init__.py')].replace(old, b'"version": (0, 77, 3)')
files[Path('control_pose_mirror.py')] = (repo / 'addons/character_designer/control_pose_mirror.py').read_bytes()
changed = sorted(p.as_posix() for p in files if files[p] != base.files[p])
assert changed == ['__init__.py', 'control_pose_mirror.py']
source = destination / 'addons/character_designer'
for path, payload in files.items():
    target = source / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
manifest = destination / 'release_projection.json'
manifest.write_text(json.dumps({
    'schema_version': 1, 'module': 'character_designer', 'version': '0.77.3',
    'source_root': str(source),
    'files': {p.as_posix(): hashlib.sha256(v).hexdigest() for p, v in sorted(files.items())},
    'source_provenance': {'previous_projection': str(previous),
                          'previous_projection_sha256': base.projection_sha256,
                          'canonical_mirror_source': str(repo / 'addons/character_designer/control_pose_mirror.py'),
                          'approved_delta': changed,
                          'scope': 'Managed complete Pose local deformation mirror only; pending Dress source excluded'}
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
verified = load_source('character_designer', manifest, root=repo)
assert verified.files == files and verified.version == '0.77.3'
print(json.dumps({'manifest': str(manifest), 'sha256': verified.projection_sha256,
                  'files': len(files), 'changed': changed}, indent=2))
