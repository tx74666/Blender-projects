"""Freeze the single-table release on the verified 0.77.14 package."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source

BASE = Path('D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/import_queue_07714_runtime/release_projection_07714.json')
BASE_SHA = '17a62f31b1b7c71ced1add9aae18465363420a63942f777b9f51422af851b6eb'
DEST = ROOT / 'release_07715_final/character_designer'
MANIFEST = DEST.parent / 'release_projection_07715.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


if sha(BASE.read_bytes()) != BASE_SHA:
    raise AssertionError('Verified 0.77.14 baseline manifest changed')
base = load_source('character_designer', BASE, root=REPO)
if base.version != '0.77.14' or len(base.files) != 152 or DEST.exists() or MANIFEST.exists():
    raise AssertionError('Unexpected baseline or release destination already exists')
payload = dict(base.files)
edited = ('animation_worklist_ui.py', 'animation_worklist_collection.py')
canonical = REPO / 'addons/character_designer'
for name in edited:
    payload[Path(name)] = (canonical / name).read_bytes()
old = b'"version": (0, 77, 14)'
new = b'"version": (0, 77, 15)'
if payload[Path('__init__.py')].count(old) != 1 or new not in (canonical / '__init__.py').read_bytes():
    raise AssertionError('Unexpected baseline or canonical version')
payload[Path('__init__.py')] = payload[Path('__init__.py')].replace(old, new, 1)
changed = sorted(path.as_posix() for path in payload if payload[path] != base.files[path])
if changed != ['__init__.py', 'animation_worklist_collection.py', 'animation_worklist_ui.py']:
    raise AssertionError('Unexpected release scope')
diff = []
for name in changed:
    path = Path(name)
    diff.extend(difflib.unified_diff(base.files[path].decode('utf-8').splitlines(True),
        payload[path].decode('utf-8').splitlines(True), fromfile='0.77.14/' + name,
        tofile='0.77.15/' + name))
(ROOT / 'changes.diff').write_text(''.join(diff), encoding='utf-8')
for path, data in payload.items():
    if path.suffix == '.py':
        ast.parse(data, filename=str(path))
    target = DEST / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
manifest = {
    'schema_version': 1, 'module': 'character_designer', 'version': '0.77.15',
    'source_root': str(DEST),
    'files': {path.as_posix(): sha(payload[path]) for path in sorted(payload)},
    'source_provenance': {
        'baseline_manifest': str(BASE), 'baseline_sha256': BASE_SHA,
        'changed_files': changed,
        'canonical_changes': {name: sha((canonical / name).read_bytes()) for name in edited},
        'scope': 'One imported animation list with two same-name icon buttons; latest prepared import and automatic proven-change export, including launch-time checks.',
        'validation': '43 collection and 60 UI contract tests passed, independently reviewed; no live Blender UI or Unity calls.',
        'runtime_loading': 'Save the artist blend and reload/reopen Blender to load the updated interface; no artist session was reloaded by this task.',
    },
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
release = load_source('character_designer', MANIFEST, root=REPO)
receipt = {
    'prepared': True, 'version': release.version, 'file_count': len(release.files),
    'manifest': str(MANIFEST), 'manifest_sha256': release.projection_sha256,
    'changed_files': changed, 'canonical_sources': manifest['source_provenance']['canonical_changes'],
    'scene_operations': False, 'unity_operations': False, 'native_validation': False,
}
(ROOT / 'preparation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt))
