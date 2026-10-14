"""Pin the released 0.77.22 runtime for tests; do not deploy to the artist."""
import hashlib
import json
from pathlib import Path
import zipfile

folder = Path(__file__).resolve().parent
archive = Path(r'D:\MyRepository\Blender-addons-by-Randy\dist\character_designer-0.77.22.zip')
expected_sha = '77fc7cfd82a2f8f1448b885597b8a89d61487055bd6ed3c3d256255b2292cfb5'
actual_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
assert actual_sha == expected_sha, (actual_sha, expected_sha)
root = folder / 'addon_runtime_07722'
with zipfile.ZipFile(archive) as z:
    for entry in z.infolist():
        target = (root / entry.filename).resolve()
        assert target.is_relative_to(root.resolve()), entry.filename
        z.extract(entry, root)
runtime = json.loads((folder / 'live_control_graph.json').read_text(encoding='utf-8'))
hashes = {}
for name, expected in runtime['module_sha256'].items():
    path = root.joinpath(*name.split('.')).with_suffix('.py')
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, (name, actual, expected)
    hashes[name] = actual
report = {'archive': str(archive), 'archive_sha256': actual_sha, 'addon_root': str(root),
          'version': runtime['addon_version'], 'module_sha256': hashes,
          'artist_deployed_or_refreshed': False}
(folder / 'pinned_runtime_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
failure = folder / 'isolated_return_report.json'
if failure.exists():
    previous = json.loads(failure.read_text(encoding='utf-8'))
    assert previous.get('failure') == 'Blender/add-on versions differ from the captured live runtime.'
    failure.rename(folder / 'isolated_return_version_mismatch.json')
log = folder / 'isolated_return.log'
if log.exists():
    log.rename(folder / 'isolated_return_version_mismatch.log')
print(json.dumps(report))
