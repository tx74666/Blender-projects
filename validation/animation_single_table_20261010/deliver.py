"""Verify the frozen UI release, package, deploy with backups, and verify bytes."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
MANIFEST = ROOT / 'release_07715_final/release_projection_07715.json'
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


release = load_source('character_designer', MANIFEST, root=REPO)
for name, checksum in release.source_provenance['canonical_changes'].items():
    if sha(REPO / 'addons/character_designer' / name) != checksum:
        raise AssertionError('Reviewed canonical module changed: ' + name)
sys.path.insert(0, str(REPO / 'tests'))
import test_animation_worklist_collection as collection_tests
import test_animation_worklist_ui as ui_tests
suite = unittest.TestSuite()
for module in (collection_tests, ui_tests):
    module.SOURCE = release.root
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream).run(suite)
(ROOT / 'frozen_tests.log').write_text(stream.getvalue(), encoding='utf-8')
if not result.wasSuccessful():
    print(stream.getvalue())
    raise SystemExit('Frozen release tests failed')

commands = {
    'build': [sys.executable, 'tools/build_releases.py', '--module', 'character_designer',
              '--projection', str(MANIFEST)],
    'deploy': [sys.executable, 'tools/deploy_local.py', '--module', 'character_designer',
               '--blender-version', '5.2', '--project-addons', 'D:/Blender/Projects/Character/X/addons',
               '--projection', str(MANIFEST)],
}
commands['check'] = commands['deploy'] + ['--check']
reports = {}
for name, command in commands.items():
    completed = subprocess.run(command, cwd=REPO, text=True, encoding='utf-8',
                               errors='replace', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (ROOT / (name + '.log')).write_text(completed.stdout, encoding='utf-8')
    print(completed.stdout, end='')
    reports[name] = {'exit_code': completed.returncode, 'log': str(ROOT / (name + '.log'))}
    if completed.returncode:
        raise SystemExit(completed.returncode)
report = {
    'passed': True, 'version': release.version, 'file_count': len(release.files),
    'manifest': str(MANIFEST), 'manifest_sha256': release.projection_sha256,
    'changed_files': release.source_provenance['changed_files'],
    'frozen_tests': {'passed': True, 'count': result.testsRun, 'log': str(ROOT / 'frozen_tests.log')},
    'commands': reports,
    'archive': str(REPO / 'dist/character_designer-0.77.15.zip'),
    'archive_sha256': sha(REPO / 'dist/character_designer-0.77.15.zip'),
    'canonical_sources': release.source_provenance['canonical_changes'],
    'limits': {'native_blender_validation': False, 'live_ui_reload': False,
              'unity_operations': False, 'artist_scene_edits_or_save': False},
}
(ROOT / 'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'passed': True, 'version': release.version, 'tests': result.testsRun,
                  'report': str(ROOT / 'delivery.json')}))
