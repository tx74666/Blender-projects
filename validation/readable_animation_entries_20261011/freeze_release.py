"""Freeze readable workspace entries onto the deployed 0.77.20 ZIP."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source, shipped_files

archive = REPO / 'dist' / 'character_designer-0.77.20.zip'
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    payload = {Path(name.removeprefix('character_designer/')): package.read(name)
               for name in package.namelist() if not name.endswith('/')}
assert b'"version": (0, 77, 20)' in payload[Path('__init__.py')]
targets = [Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer'),
           Path(r'D:\Blender\Projects\Character\X\addons\character_designer')]
for target in targets:
    assert set(shipped_files(target)) == set(payload), str(target)
    assert all((target / name).read_bytes() == raw for name, raw in payload.items()), 'Installed baseline changed; reconcile before release.'
baseline = dict(payload)
canonical = REPO / 'addons' / 'character_designer'
old_workspace = ast.parse(payload[Path('animation_workspace.py')])
new_workspace = ast.parse((canonical / 'animation_workspace.py').read_bytes())
reader_functions = {'_decode_json', 'parse_workspace', '_uuid', '_parse_reference', '_read_bytes', '_load_reference', 'load_workspace'}
def stable_nodes(tree):
    return [ast.dump(node, include_attributes=False) for node in tree.body
            if not (isinstance(node, ast.FunctionDef) and node.name in reader_functions)
            and not (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id.startswith('REFERENCE_') for t in node.targets))
            and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))]
assert stable_nodes(old_workspace) == stable_nodes(new_workspace), 'Unrelated workspace source changes.'
payload[Path('animation_workspace.py')] = (canonical / 'animation_workspace.py').read_bytes()
old_ui = payload[Path('animation_worklist_ui.py')].decode('utf-8')
new_ui = (canonical / 'animation_worklist_ui.py').read_text(encoding='utf-8')
def connect_nodes(text):
    cls = next(node for node in ast.parse(text).body if isinstance(node, ast.ClassDef) and node.name == 'CHARACTERDESIGNER_OT_worklist_connect')
    return {node.name if isinstance(node, ast.FunctionDef) else next(t.id for t in node.targets if isinstance(t, ast.Name)): node
            for node in cls.body if isinstance(node, (ast.FunctionDef, ast.Assign))}
old, new = connect_nodes(old_ui), connect_nodes(new_ui)
lines = old_ui.splitlines(keepends=True)
for name in sorted(('bl_description', 'invoke'), key=lambda name: old[name].lineno, reverse=True):
    node = new[name]
    replacement = new_ui.splitlines(keepends=True)[node.lineno - 1:node.end_lineno]
    lines[old[name].lineno - 1:old[name].end_lineno] = replacement
payload[Path('animation_worklist_ui.py')] = ''.join(lines).encode('utf-8')
payload[Path('__init__.py')] = payload[Path('__init__.py')].replace(b'(0, 77, 20)', b'(0, 77, 21)', 1)
assert b'"version": (0, 77, 21)' in (canonical / '__init__.py').read_bytes()
changed = sorted(name.as_posix() for name in payload if payload[name] != baseline[name])
assert changed == ['__init__.py', 'animation_worklist_ui.py', 'animation_workspace.py']
source = HERE / 'release_07721' / 'character_designer'
assert not source.exists(), 'Freeze a fresh source directory.'
for name, raw in payload.items():
    if name.suffix == '.py':
        ast.parse(raw, filename=str(name))
    path = source / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
manifest = {'schema_version': 1, 'module': 'character_designer', 'version': '0.77.21',
            'source_root': str(source), 'files': {name.as_posix(): hashlib.sha256(raw).hexdigest() for name, raw in sorted(payload.items())},
            'source_provenance': {'baseline_zip': str(archive), 'baseline_zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                                  'baseline_matches_installed_and_X': True, 'changed_files': changed,
                                  'canonical_files': {name: hashlib.sha256((canonical / name).read_bytes()).hexdigest()
                                                      for name in ('animation_workspace.py', 'animation_worklist_ui.py')},
                                  'scope': 'Explicit readable workspace entry reader, Connect readable directory default, version only.',
                                  'excluded': 'Other pending canonical changes; Unity files and data lifecycle unchanged.'}}
manifest_path = source.parent / 'release_projection_07721.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
release = load_source('character_designer', manifest_path, root=REPO)
diff = ''.join(''.join(difflib.unified_diff(baseline[Path(name)].decode('utf-8').splitlines(True),
                                        payload[Path(name)].decode('utf-8').splitlines(True),
                                        fromfile='0.77.20/' + name, tofile='0.77.21/' + name)) for name in changed)
(HERE / 'changes.diff').write_text(diff, encoding='utf-8')
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
(HERE / 'artist_file_before.json').write_text(json.dumps({'path': str(artist), 'sha256': hashlib.sha256(artist.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
print(json.dumps({'version': release.version, 'files': len(payload), 'changed': changed, 'projection_sha256': release.projection_sha256}))
