"""Final local delivery evidence, with input integrity and exact payload checks."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
MANIFEST = HERE / 'release_07721' / 'release_projection_07721.json'
manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == '39fa6580fd7e7ed4d5bd74e57f54bc0a5d71c5b738b8dc85458005161d3e15ec'
archive = REPO / 'dist' / 'character_designer-0.77.21.zip'
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    assert {name.removeprefix('character_designer/'): hashlib.sha256(package.read(name)).hexdigest()
            for name in package.namelist()} == manifest['files']
targets = [Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer'),
           Path(r'D:\Blender\Projects\Character\X\addons\character_designer')]
latest_archive = REPO / 'dist' / 'character_designer-0.77.22.zip'
with zipfile.ZipFile(latest_archive) as package:
    assert package.testzip() is None
    current_payload = {name.removeprefix('character_designer/'): package.read(name) for name in package.namelist()}
assert set(current_payload) == set(manifest['files'])
assert all(hashlib.sha256(current_payload[name]).hexdigest() == manifest['files'][name]
           for name in ('animation_workspace.py', 'animation_worklist_ui.py'))
assert current_payload['__init__.py'].replace(b'(0, 77, 22)', b'(0, 77, 21)', 1) == (HERE / 'release_07721' / 'character_designer' / '__init__.py').read_bytes()
current_hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in current_payload.items()}
allowed_delta = {'__init__.py', 'unity_runtime/Editor/CharacterMaterialMatching.cs', 'unity_runtime/Editor/CharacterMaterialMatchingVerification.cs'}
assert {name for name in current_hashes if current_hashes[name] != manifest['files'][name]} == allowed_delta
for target in targets:
    assert all(hashlib.sha256((target / name).read_bytes()).hexdigest() == digest for name, digest in current_hashes.items())
tests = json.loads((HERE / 'tests.json').read_text(encoding='utf-8'))
smoke = json.loads((HERE / 'installed_addon_smoke.json').read_text(encoding='utf-8'))
shortcuts = json.loads((HERE / 'shortcuts_check.json').read_text(encoding='utf-8-sig'))
assert tests['passed'] and tests['tests'] == 174
assert smoke['passed'] and smoke['disabled'] and smoke['version'] == [0, 77, 22]
assert shortcuts['passed'] and shortcuts['check_only'] and len(shortcuts['shortcuts']) == 7
plan = json.loads((HERE / 'shortcut_plan.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256(Path(source['path']).read_bytes()).hexdigest() == source['sha256'] for source in plan['source_metadata'])
spec = importlib.util.spec_from_file_location('_installed_workspace', targets[0] / 'animation_workspace.py')
reader = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reader
spec.loader.exec_module(reader)
loaded = reader.load_workspace(plan['reference_path'])
assert loaded['_manifest_path'] == plan['workspace_manifest'] and [clip['clipName'] for clip in loaded['clips']] == ['Walk_N']
artist = json.loads((HERE / 'artist_file_before.json').read_text(encoding='utf-8'))
artist_after = hashlib.sha256(Path(artist['path']).read_bytes()).hexdigest()
assert artist_after == artist['sha256']
report = {'utc': datetime.now(timezone.utc).isoformat(), 'version': '0.77.21',
          'current_installed_version': '0.77.22', 'current_archive': str(latest_archive),
          'current_archive_sha256': hashlib.sha256(latest_archive.read_bytes()).hexdigest(),
          'readable_reader_and_UI_retained_byte_equal_in_07722': True,
          'projection_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
          'archive': str(archive), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'targets': [str(target) for target in targets], 'files_per_target': 157,
          'changed_files': manifest['source_provenance']['changed_files'], 'tests_passed': 174,
          'entry': plan['reference_path'], 'prepared': 1, 'history': 6,
          'installed_connect_refresh_smoke': True, 'shortcut_readback_passed': 7,
          'source_metadata_unchanged': len(plan['source_metadata']), 'artist_file_sha256_unchanged': artist_after,
          'live_artist_runtime_refreshed': False, 'artist_scene_saved_by_task': False,
          'unity_operations': False, 'git_commit_push_public_release': False,
          'model_reasoning_effort': 'unrecorded'}
(HERE / 'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('READABLE_ANIMATION_ENTRIES_DELIVERED', json.dumps(report, ensure_ascii=False))
