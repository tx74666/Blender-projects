"""Release only the tested rebind patch on top of the completed bone-length release."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
BASE = Path('D:/Blender/Projects/Character/X/validation/bone_rest_lengths_20261010/release_07717/release_projection_07717.json')
DEST = ROOT / 'release_07718/character_designer'
MANIFEST = DEST.parent / 'release_projection_07718.json'
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source


def sha(data):
    return hashlib.sha256(data).hexdigest()


native = json.loads((ROOT / 'native_validation.json').read_text(encoding='utf-8'))
assert native['passed'] and native['native_tests_passed'] == 18 and native['artist_rebind_preflight_passed']
assert native['artist_file_unchanged'] and not native['artist_weights_recalculated']
assert not DEST.exists() and not MANIFEST.exists()
base = load_source('character_designer', BASE, root=REPO)
assert base.version == '0.77.17' and len(base.files) == 153
payload = dict(base.files)
edited = REPO / 'addons/character_designer/quick_bind.py'
payload[Path('quick_bind.py')] = edited.read_bytes()
assert sha(payload[Path('quick_bind.py')]) == native['tested_quick_bind_sha256']
assert sha(BASE.read_bytes()) == native['tested_baseline_manifest_sha256']
init = REPO / 'addons/character_designer/__init__.py'
canonical_init = init.read_bytes()
assert b'"version": (0, 77, 17)' in canonical_init
payload[Path('__init__.py')] = payload[Path('__init__.py')].replace(b'"version": (0, 77, 17)', b'"version": (0, 77, 18)', 1)
changed = sorted(p.as_posix() for p in payload if payload[p] != base.files[p])
assert changed == ['__init__.py', 'quick_bind.py'], changed
# First prove both deployment targets still contain the completed baseline.
deploy_args = [sys.executable, 'tools/deploy_local.py', '--module', 'character_designer', '--blender-version', '5.2',
               '--project-addons', 'D:/Blender/Projects/Character/X/addons']
check = subprocess.run(deploy_args + ['--projection', str(BASE), '--check'], cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
(ROOT / 'baseline_check.log').write_text(check.stdout, encoding='utf-8')
print(check.stdout, end='')
assert check.returncode == 0, 'The baseline deployment changed; do not overwrite it'
diff = []
for name in changed:
    path = Path(name)
    diff.extend(difflib.unified_diff(base.files[path].decode('utf-8').splitlines(True),
        payload[path].decode('utf-8').splitlines(True), fromfile='0.77.17/' + name, tofile='0.77.18/' + name))
(ROOT / 'changes.diff').write_text(''.join(diff), encoding='utf-8')
for path, data in payload.items():
    if path.suffix == '.py':
        ast.parse(data, filename=str(path))
    target = DEST / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
manifest = {
    'schema_version': 1, 'module': 'character_designer', 'version': '0.77.18', 'source_root': str(DEST),
    'files': {path.as_posix(): sha(payload[path]) for path in sorted(payload)},
    'source_provenance': {
        'baseline_manifest': str(BASE), 'baseline_sha256': sha(BASE.read_bytes()),
        'changed_files': changed,
        'canonical_quick_bind_sha256': sha(payload[Path('quick_bind.py')]),
        'scope': 'Rebind within the first weight backup when unrelated unweighted deform bones were added; constrain private AUTO solver to this same scope.',
        'native_validation': str(ROOT / 'native_validation.json'),
        'artist_scene_repair': str(ROOT / 'modifier_restored.json'),
        'limits': 'No artist weights recalculated, Unity operations or FBX publication.',
    },
}
MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
release = load_source('character_designer', MANIFEST, root=REPO)
assert init.read_bytes() == canonical_init, 'Canonical package changed during preparation'
init.write_bytes(canonical_init.replace(b'"version": (0, 77, 17)', b'"version": (0, 77, 18)', 1))
commands = {
    'build': [sys.executable, 'tools/build_releases.py', '--module', 'character_designer', '--projection', str(MANIFEST)],
    'deploy': deploy_args + ['--projection', str(MANIFEST)],
    'check': deploy_args + ['--projection', str(MANIFEST), '--check'],
}
for name, command in commands.items():
    completed = subprocess.run(command, cwd=REPO, text=True, encoding='utf-8', errors='replace',
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (ROOT / (name + '.log')).write_text(completed.stdout, encoding='utf-8')
    print(completed.stdout, end='')
    if completed.returncode:
        raise SystemExit(completed.returncode)
receipt = {
    'passed': True, 'version': release.version, 'file_count': len(release.files),
    'manifest': str(MANIFEST), 'manifest_sha256': release.projection_sha256,
    'changed_files': changed, 'native_tests_passed': native['native_tests_passed'],
    'artist_rebind_preflight_passed': True, 'artist_weights_recalculated': False,
    'native_validation_sha256': sha((ROOT / 'native_validation.json').read_bytes()),
    'unity_operations': False, 'fbx_published': False, 'live_quick_bind_refreshed': False,
}
(ROOT / 'delivery.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt))
