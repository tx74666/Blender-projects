"""Freeze and deploy the two successful-import display defaults."""
import ast
import difflib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
BASE = Path('D:/Blender/Projects/Character/X/validation/animation_single_table_20261010/release_07715_final/release_projection_07715.json')
EXPECTED_BASE = '1864c248f235c3591e6359df514c7536e8ae99b2035fab5f55ac40e12a6e8eb2'
DEST = ROOT / 'release_07716/character_designer'
MANIFEST = DEST.parent / 'release_projection_07716.json'
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source


def sha(data):
    return hashlib.sha256(data).hexdigest()


if sha(BASE.read_bytes()) != EXPECTED_BASE or DEST.exists() or MANIFEST.exists():
    raise AssertionError('Baseline changed or release destination already exists')
base = load_source('character_designer', BASE, root=REPO)
if base.version != '0.77.15' or len(base.files) != 152:
    raise AssertionError('Unexpected baseline version or file count')
payload = dict(base.files)
edited = ('animation_link_source.py', 'animation_worklist.py')
for name in edited:
    payload[Path(name)] = (REPO / 'addons/character_designer' / name).read_bytes()
payload[Path('__init__.py')] = payload[Path('__init__.py')].replace(
    b'"version": (0, 77, 15)', b'"version": (0, 77, 16)', 1)
changed = sorted(path.as_posix() for path in payload if payload[path] != base.files[path])
if changed != ['__init__.py', 'animation_link_source.py', 'animation_worklist.py']:
    raise AssertionError('Unexpected release scope')
diff = []
for name in changed:
    path = Path(name)
    diff.extend(difflib.unified_diff(base.files[path].decode('utf-8').splitlines(True),
        payload[path].decode('utf-8').splitlines(True), fromfile='0.77.15/' + name,
        tofile='0.77.16/' + name))
(ROOT / 'changes.diff').write_text(''.join(diff), encoding='utf-8')
for path, content in payload.items():
    if path.suffix == '.py':
        ast.parse(content, filename=str(path))
    target = DEST / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
manifest = {
    'schema_version': 1, 'module': 'character_designer', 'version': '0.77.16',
    'source_root': str(DEST),
    'files': {path.as_posix(): sha(payload[path]) for path in sorted(payload)},
    'source_provenance': {
        'baseline_manifest': str(BASE), 'baseline_sha256': EXPECTED_BASE,
        'changed_files': changed,
        'canonical_changes': {name: sha(payload[Path(name)]) for name in edited},
        'scope': 'Enable armature In Front after successful new-source import and worklist import into a reused rig.',
        'limits': 'No live artist scene, Unity calls, native Blender process or runtime reload.',
    },
}
MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
release = load_source('character_designer', MANIFEST, root=REPO)
sys.path.insert(0, str(REPO / 'tests'))
import test_animation_worklist as worklist_tests
import test_animation_link_source_images as source_tests
suite = unittest.TestSuite()
for module in (worklist_tests, source_tests):
    module.SOURCE = release.root
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream).run(suite)
(ROOT / 'tests.log').write_text(stream.getvalue(), encoding='utf-8')
if not result.wasSuccessful():
    print(stream.getvalue())
    raise SystemExit('Existing tests failed')
commands = {
    'build': [sys.executable, 'tools/build_releases.py', '--module', 'character_designer', '--projection', str(MANIFEST)],
    'deploy': [sys.executable, 'tools/deploy_local.py', '--module', 'character_designer', '--blender-version', '5.2',
               '--project-addons', 'D:/Blender/Projects/Character/X/addons', '--projection', str(MANIFEST)],
}
commands['check'] = commands['deploy'] + ['--check']
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
    'changed_files': changed, 'existing_tests_passed': result.testsRun,
    'native_validation': False, 'artist_scene_modified_or_saved': False,
    'unity_operations': False, 'live_addon_reloaded': False,
}
(ROOT / 'delivery.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt))
