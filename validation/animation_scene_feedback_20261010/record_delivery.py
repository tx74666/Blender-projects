"""Record the verified local patch delivery, without changing artist data."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
MANIFEST = HERE / 'release_07719' / 'release_projection_07719.json'
manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == '1614071a766cb9d5d9a4e8565ef549012e353546b463f2e9f2118cceb81f368e'
archive = REPO / 'dist' / 'character_designer-0.77.19.zip'
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    assert {name.removeprefix('character_designer/'): hashlib.sha256(package.read(name)).hexdigest()
            for name in package.namelist()} == manifest['files']
targets = [Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer'),
           Path(r'D:\Blender\Projects\Character\X\addons\character_designer')]
for target in targets:
    assert all(hashlib.sha256((target / name).read_bytes()).hexdigest() == digest
               for name, digest in manifest['files'].items())
tests = json.loads((HERE / 'tests.json').read_text(encoding='utf-8'))
smoke = json.loads((HERE / 'installed_addon_smoke.json').read_text(encoding='utf-8'))
assert tests['passed'] and tests['tests'] == 142
assert smoke['passed'] and smoke['disabled'] and smoke['addon_version'] == [0, 77, 19]
artist_before = json.loads((HERE / 'artist_file_before.json').read_text(encoding='utf-8'))
artist_after = hashlib.sha256(Path(artist_before['path']).read_bytes()).hexdigest()
assert artist_before['sha256'] == artist_after
report = {
    'utc': datetime.now(timezone.utc).isoformat(),
    'version': '0.77.19',
    'projection': str(MANIFEST),
    'projection_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
    'archive': str(archive),
    'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'changed_files': manifest['source_provenance']['changed_files'],
    'targets': [str(target) for target in targets],
    'verified_files_per_target': 153,
    'tests_passed': 142,
    'installed_factory_smoke_passed': True,
    'live_artist_refresh_verified': False,
    'live_refresh_limit': 'Shared Computer Use helper reported an active request; later screenshot showed another application over Blender. No further input or reload was attempted.',
    'artist_file_sha256_unchanged': artist_after,
    'artist_scene_data_operations': False,
    'artist_saved_by_task': False,
    'unity_operations': False,
    'git_commit_push_public_release': False,
    'model_reasoning_effort': 'unrecorded',
}
(HERE / 'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('CD_07719_LOCAL_DELIVERY_VERIFIED', json.dumps(report, ensure_ascii=False))
