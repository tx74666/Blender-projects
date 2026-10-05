"""Freeze only this animation task over the verified installed 0.76.2 release."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
HERE = Path(__file__).resolve().parent
BASE = REPO / 'dist/character_designer-0.76.2.zip'
BASE_SHA = 'f3b00d2e92fa9954d7816aff9ff7bb099b06395cafffa5e274e1d69b6006f9e7'
ALLOWED = {'__init__.py', 'animation.py', 'animation_link_source.py', 'animation_worklist.py', 'animation_worklist_ui.py',
           'animation_worklist_collection.py', 'animation_worklist_fingerprint.py', 'animation_worklist_queue.py'}
INSTALLED = Path('C:/Users/Randy/AppData/Roaming/Blender Foundation/Blender/5.1/scripts/addons/character_designer')
STAGE = HERE / (sys.argv[1] if len(sys.argv) > 1 else 'candidate_source')
assert STAGE.resolve().is_relative_to(HERE.resolve()) and STAGE.parent == HERE

def sha(data):
    return hashlib.sha256(data).hexdigest()

assert sha(BASE.read_bytes()) == BASE_SHA, 'Frozen base ZIP changed.'
with zipfile.ZipFile(BASE) as archive:
    assert archive.testzip() is None
    base = {name.removeprefix('character_designer/'): archive.read(name)
            for name in archive.namelist() if name.startswith('character_designer/') and not name.endswith('/')}
for name, data in base.items():
    assert (INSTALLED / name).is_file() and (INSTALLED / name).read_bytes() == data, 'Installed base differs: ' + name
installed_names = {path.relative_to(INSTALLED).as_posix() for path in INSTALLED.rglob('*')
                   if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc', '.pyo'}}
assert installed_names == set(base), 'Unexpected installed runtime files.'
canonical = REPO / 'addons/character_designer'
expected_init = base['__init__.py'].replace(b'"version": (0, 76, 2)', b'"version": (0, 76, 3)')
assert (canonical / '__init__.py').read_bytes() == expected_init, 'Initializer has unrelated changes.'
payload = {**base, **{name: (canonical / name).read_bytes() for name in ALLOWED}}
changed = sorted(name for name, data in payload.items() if base.get(name) != data)
assert set(changed) == ALLOWED, 'Unexpected candidate delta.'
for name, data in payload.items():
    destination = STAGE / 'addons/character_designer' / name
    assert destination.resolve().is_relative_to((STAGE / 'addons/character_designer').resolve())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
(STAGE / 'tools').mkdir(parents=True, exist_ok=True)
shutil.copyfile(REPO / 'tools/build_releases.py', STAGE / 'tools/build_releases.py')
subprocess.run([sys.executable, str(STAGE / 'tools/build_releases.py'), '--module', 'character_designer'], check=True)
candidate = STAGE / 'dist/character_designer-0.76.3.zip'
with zipfile.ZipFile(candidate) as archive:
    packed = {name.removeprefix('character_designer/'): archive.read(name) for name in archive.namelist()}
    assert archive.testzip() is None and packed == payload
canonical_only_changes = sorted(path.relative_to(canonical).as_posix() for path in canonical.rglob('*')
    if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc', '.pyo'}
    and path.relative_to(canonical).as_posix() not in ALLOWED
    and base.get(path.relative_to(canonical).as_posix()) != path.read_bytes())
report = {'base': str(BASE), 'base_sha256': BASE_SHA, 'base_files': len(base),
          'installed_base_equal': True, 'candidate': str(candidate), 'candidate_sha256': sha(candidate.read_bytes()),
          'candidate_files': len(payload), 'allowed_delta': changed, 'excluded_canonical_changes': canonical_only_changes,
          'file_sha256': {name: sha(data) for name, data in sorted(payload.items())},
          'native_validation': 'pending', 'installed_or_deployed': False, 'author_scene_saved': False}
(HERE / (STAGE.name + '_inventory.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({key: report[key] for key in ('candidate', 'candidate_sha256', 'candidate_files', 'allowed_delta',
                                             'excluded_canonical_changes', 'installed_or_deployed')}))
