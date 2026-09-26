"""Group existing catalog UUIDs without modifying any asset blend file."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid
from datetime import datetime

OUTPUT = Path(__file__).resolve().parent
ROOT = Path(r'D:\Blender\Helper\Asset-Libraries\Costom')
OLD = Path(r'D:\Blender\Addons\Ultimate\Ultimate Blender Procedural Material Pack-0.0.11')
MATERIAL = ROOT / 'Procedural Material'
POSE = ROOT / 'Pose Library'
FILENAME = 'Ultimate Procedural Material Pack-0.0.11.blend'

def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()

def parse(text):
    return [line.split(':', 2) for line in text.splitlines()
            if line.strip() and not line.startswith('#') and not line.startswith('VERSION')]

assert digest(OLD / FILENAME) == digest(MATERIAL / FILENAME), 'Material copies differ; stop'
catalog = MATERIAL / 'blender_assets.cats.txt'
entries = parse(catalog.read_text(encoding='utf-8-sig'))
assert len(entries) == 21 and len({row[0] for row in entries}) == 21
assert all('/' not in row[1] for row in entries), 'Catalog already changed; inspect before running again'
assert not POSE.exists(), 'Pose Library already exists; inspect instead of overwriting'
backup = OUTPUT / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
backup.mkdir(parents=True)
shutil.copy2(catalog, backup / 'procedural_blender_assets.cats.txt')
prefs = Path(os.environ['APPDATA']) / 'Blender Foundation/Blender/5.2/config/userpref.blend'
shutil.copy2(prefs, backup / 'userpref.blend')
material_id, pose_id, character_id = (str(uuid.uuid4()) for _ in range(3))
header = '# Asset catalogs. Existing asset UUID assignments are preserved.\nVERSION 1\n\n'
new_entries = [[material_id, 'Procedural Material', 'Procedural Material']]
new_entries += [[identity, 'Procedural Material/' + path, name] for identity, path, name in entries]
temporary = catalog.with_name('.blender_assets.cats.organizing.tmp')
temporary.write_text(header + '\n'.join(':'.join(row) for row in new_entries) + '\n', encoding='utf-8')
temporary.replace(catalog)
POSE.mkdir()
pose_catalog = POSE / 'blender_assets.cats.txt'
pose_catalog.write_text(header + f'{pose_id}:Pose Library:Pose Library\n'
                        + f'{character_id}:Pose Library/Crossa:Crossa\n', encoding='utf-8')
assert {row[0] for row in entries} <= {row[0] for row in parse(catalog.read_text())}
assert digest(MATERIAL / FILENAME) == digest(OLD / FILENAME)
report = {'backup': str(backup), 'material_root': str(MATERIAL), 'pose_root': str(POSE),
          'nodes_root': str(ROOT / 'Nodes'), 'material_catalog_id': material_id,
          'pose_catalog_id': pose_id, 'character_catalog_id': character_id,
          'material_categories': 21, 'material_asset_sha256': digest(MATERIAL / FILENAME),
          'preserved_category_ids': [row[0] for row in entries]}
(OUTPUT / 'organization_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
