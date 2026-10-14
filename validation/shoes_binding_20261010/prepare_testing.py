"""Stage the verified release plus only the Quick Bind patch for native tests."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
BASE = Path('D:/Blender/Projects/Character/X/validation/animation_in_front_20261010/release_07716/release_projection_07716.json')
expected_base = 'e18f17e6cd5d82d068821c9c24c9ed367e4c3cd552234169daa6d5bf9cb9a436'
if len(sys.argv) == 3:
    BASE, expected_base = Path(sys.argv[1]), sys.argv[2]
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == expected_base
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source

base = load_source('character_designer', BASE, root=REPO)
assert base.version in {'0.77.16', '0.77.17'}
stage = ROOT / ('native_stage_' + base.version.replace('.', '_') + '_' + expected_base[:8])
assert not stage.exists()
payload = dict(base.files)
payload[Path('quick_bind.py')] = (REPO / 'addons/character_designer/quick_bind.py').read_bytes()
changed = [p.as_posix() for p in payload if payload[p] != base.files[p]]
assert changed == ['quick_bind.py'], changed
for relative, data in payload.items():
    if relative.suffix == '.py':
        ast.parse(data, filename=str(relative))
    dest = stage / 'addons/character_designer' / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
for name in ('test_quick_bind_blender.py', 'test_quick_bind_rebind_blender.py', 'test_quick_bind_additive_blender.py'):
    dest = stage / 'tests' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / 'tests' / name, dest)
(ROOT / 'test_projection.json').write_text(json.dumps({
    'baseline_manifest': str(BASE), 'baseline_manifest_sha256': expected_base,
    'baseline_version': base.version, 'stage': str(stage),
    'changed_files': changed, 'quick_bind_sha256': hashlib.sha256(payload[Path('quick_bind.py')]).hexdigest(),
    'files': {p.as_posix(): hashlib.sha256(data).hexdigest() for p, data in sorted(payload.items())},
}, indent=2), encoding='utf-8')
print('NATIVE_STAGE_READY', len(payload), changed)
