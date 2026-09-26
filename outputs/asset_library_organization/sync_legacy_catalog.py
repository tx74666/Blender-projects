import json
import shutil
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\outputs\asset_library_organization')
manifest_path = out / 'organization_manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
legacy = Path(r'D:\Blender\Addons\Ultimate\Ultimate Blender Procedural Material Pack-0.0.11\blender_assets.cats.txt')
current = Path(manifest['material_root']) / 'blender_assets.cats.txt'
def entries(path):
    result = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line and not line.startswith('#') and line.count(':') >= 2:
            uid, category, simple = line.split(':', 2)
            result[uid] = (category, simple)
    return result
old = entries(legacy)
new = entries(current)
assert len(old) == 21 and set(old) == set(manifest['preserved_category_ids'])
for uid, (category, simple) in old.items():
    assert new[uid] == ('Procedural Material/' + category, simple)
backup = Path(manifest['backup']) / 'legacy_procedural_blender_assets.cats.txt'
assert not backup.exists()
shutil.copy2(legacy, backup)
temp = legacy.with_name(legacy.name + '.organizing.tmp')
temp.write_bytes(current.read_bytes())
temp.replace(legacy)
assert entries(legacy) == new
manifest['legacy_catalog_synchronized'] = str(legacy)
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Legacy catalog synchronized; 21 original UUIDs preserved; backup:', backup)
