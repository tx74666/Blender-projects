"""Freeze only the approved 0.77.1 package plus the canonical Fist fix."""
import hashlib
import json
from pathlib import Path
import sys

repo = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path.insert(0, str(repo / 'tools'))
from release_projection import load_source

folder = Path(__file__).resolve().parent
previous_manifest = Path(r'D:\Blender\Projects\Character\X\validation\pose_asset_sync_20261007\approved_release_0771\release_projection.json')
previous = load_source('character_designer', previous_manifest, root=repo)
assert previous.projection_sha256 == '96cb0675d2fe72377fbfa4ca4e717bf47663640ba32e79624f306755f55c9f80'
source = folder / 'approved_release_0772' / 'addons' / 'character_designer'
assert not source.exists(), 'Inspect the existing projection before repeating'
canonical = repo / 'addons' / 'character_designer'
files = dict(previous.files)
files[Path('__init__.py')] = files[Path('__init__.py')].replace(b'"version": (0, 77, 1)', b'"version": (0, 77, 2)', 1)
files[Path('control_pose_assets.py')] = (canonical / 'control_pose_assets.py').read_bytes()
# README contains only the newly approved usage section plus the prior bytes.
new_readme = (canonical / 'README.md').read_text(encoding='utf-8')
old_readme = previous.files[Path('README.md')].decode('utf-8').replace('\r\n', '\n')
tail = new_readme.split('## Independent Hair strand motion (0.76.0)', 1)[1]
assert tail == old_readme.split('## Independent Hair strand motion (0.76.0)', 1)[1]
files[Path('README.md')] = new_readme.encode('utf-8')
delta = {p.as_posix(): {'before': hashlib.sha256(previous.files[p]).hexdigest(),
                      'after': hashlib.sha256(content).hexdigest()}
         for p, content in files.items() if content != previous.files[p]}
assert set(delta) == {'__init__.py', 'control_pose_assets.py', 'README.md'}
source.mkdir(parents=True)
for path, content in files.items():
    (source / path).parent.mkdir(parents=True, exist_ok=True)
    (source / path).write_bytes(content)
manifest = {'schema_version': 1, 'module': 'character_designer', 'version': '0.77.2',
            'source_root': str(source),
            'files': {p.as_posix(): hashlib.sha256(content).hexdigest() for p, content in sorted(files.items())},
            'source_provenance': {'previous_manifest': str(previous_manifest),
                                  'previous_manifest_sha256': previous.projection_sha256,
                                  'canonical_source': str(canonical), 'approved_delta': delta,
                                  'scope': 'Legacy native Pose destination selection only; pending Dress sources excluded'}}
target = source.parents[1] / 'release_projection.json'
target.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
verified = load_source('character_designer', target, root=repo)
print('FROZEN_RELEASE', verified.version, len(verified.files), verified.projection_sha256)

# Tests import the frozen package through their ordinary ROOT / addons path.
tests = source.parents[1] / 'tests'
tests.mkdir()
for name in ('test_control_pose_native_selection_blender.py', 'test_control_pose_activation_blender.py'):
    (tests / name).write_bytes((repo / 'tests' / name).read_bytes())
