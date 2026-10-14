"""Freeze the Scene feedback patch onto the verified CD 0.77.18 release."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source

BASE = HERE.parent / 'shoes_binding_20261010' / 'release_07718' / 'release_projection_07718.json'
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == '6ab500acf3fe43528df763a73b4c20c53b9e7598de91f01fbeebd358c1fdbd7b'
baseline = load_source('character_designer', BASE, root=REPO)
assert baseline.version == '0.77.18' and len(baseline.files) == 153
installed = Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer')
project = Path(r'D:\Blender\Projects\Character\X\addons\character_designer')
assert all((target / name).read_bytes() == content
           for target in (installed, project) for name, content in baseline.files.items()), 'Installed baseline changed; reconcile instead of overwriting.'
canonical = REPO / 'addons' / 'character_designer'
payload = dict(baseline.files)
edited = ['animation_worklist_ui.py', 'animation_worklist_collection.py']
for name in edited:
    payload[Path(name)] = (canonical / name).read_bytes()
payload[Path('__init__.py')] = payload[Path('__init__.py')].replace(b'(0, 77, 18)', b'(0, 77, 19)', 1)
assert ast.literal_eval(next(node.value for node in ast.parse((canonical / '__init__.py').read_bytes()).body
                             if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'bl_info' for t in node.targets)))['version'] == (0, 77, 19)
changed = sorted(name.as_posix() for name in payload if payload[name] != baseline.files[name])
assert changed == ['__init__.py', 'animation_worklist_collection.py', 'animation_worklist_ui.py']
source = HERE / 'release_07719' / 'character_designer'
diff = []
for name in changed:
    diff.extend(difflib.unified_diff(baseline.files[Path(name)].decode('utf-8').splitlines(True),
                                   payload[Path(name)].decode('utf-8').splitlines(True),
                                   fromfile='0.77.18/' + name, tofile='0.77.19/' + name))
(HERE / 'changes.diff').write_text(''.join(diff), encoding='utf-8')
for name, content in payload.items():
    if name.suffix == '.py':
        ast.parse(content, filename=str(name))
    destination = source / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
manifest = {'schema_version': 1, 'module': 'character_designer', 'version': '0.77.19',
            'source_root': str(source),
            'files': {name.as_posix(): hashlib.sha256(payload[name]).hexdigest() for name in sorted(payload)},
            'source_provenance': {
                'baseline_manifest': str(BASE), 'baseline_sha256': baseline.projection_sha256,
                'changed_files': changed,
                'canonical_files': {name: hashlib.sha256(payload[Path(name)]).hexdigest() for name in edited},
                'scope': 'Display current Scene, explain create/reuse on Import Prepared, and report actual import Scene/count.',
                'excluded': 'All other pending canonical source changes; no import/data lifecycle or Unity changes.'}}
manifest_path = source.parent / 'release_projection_07719.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
release = load_source('character_designer', manifest_path, root=REPO)
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
(HERE / 'artist_file_before.json').write_text(json.dumps({'path': str(artist), 'bytes': artist.stat().st_size,
              'sha256': hashlib.sha256(artist.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
print(json.dumps({'version': release.version, 'files': len(release.files),
                  'projection_sha256': release.projection_sha256, 'changed': changed}, indent=2))
