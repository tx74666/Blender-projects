import ast
import hashlib
import json
import zipfile
from pathlib import Path

REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
BASE = Path(__file__).resolve().parent
ARCHIVE = REPO / 'dist' / 'character_designer-0.77.9.zip'
DEST = BASE / 'approved_07711' / 'character_designer'
DEST.mkdir(parents=True, exist_ok=True)
digest = lambda data: hashlib.sha256(data).hexdigest()
with zipfile.ZipFile(ARCHIVE) as z:
    approved = {n.removeprefix('character_designer/'): z.read(n) for n in z.namelist() if not n.endswith('/')}
assert len(approved) == 152
payload = dict(approved)
original_init = payload['__init__.py'].decode('utf-8')
assert original_init.count('"version": (0, 77, 9)') == 1
payload['__init__.py'] = original_init.replace('"version": (0, 77, 9)', '"version": (0, 77, 11)').encode('utf-8')
payload['control_pose_assets.py'] = (REPO / 'addons' / 'character_designer' / 'control_pose_assets.py').read_bytes()
for relative, data in payload.items():
    path = DEST / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == '.py': ast.parse(data, filename=relative)
    path.write_bytes(data)
changed = [n for n in payload if payload[n] != approved[n]]
assert set(changed) == {'__init__.py','control_pose_assets.py'}
manifest = {'schema_version':1,'module':'character_designer','version':'0.77.11',
    'source_root':str(DEST),'files':{n:digest(data) for n,data in sorted(payload.items())},
    'source_provenance':{'base_release':str(ARCHIVE),'base_sha256':digest(ARCHIVE.read_bytes()),
        'changed_files':changed,'canonical_module':str(REPO/'addons'/'character_designer'/'control_pose_assets.py'),
        'scope':'Arm Flat explicit stable IK bend and reference seed; no pending Dress/Cloth changes'}}
(BASE/'release_projection.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ARM_FLAT_PROJECTION_READY',len(payload),changed)
