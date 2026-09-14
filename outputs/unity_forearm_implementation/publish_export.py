import json
from pathlib import Path
import sys
import bpy

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import unity_export as exporter

stage = Path(r'D:\Blender\Projects\Character\X\outputs\unity_forearm_implementation\export')
destination = Path(r'D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha')
manifest = destination / 'Cosha.cdesigner.json'
prior = json.loads(manifest.read_text(encoding='utf8'))
result = json.loads((stage / 'result.json').read_text(encoding='utf8'))
job = {'directory': destination, 'stage': stage, 'filename': 'Cosha.fbx',
       'asset_id': prior['asset_id'], 'manifest_hash': exporter._hash(manifest),
       'rig': bpy.data.objects['CoshaRig'], 'objects': result['objects']}
published = exporter._publish(job, result)
(stage.parent / 'published.json').write_text(json.dumps(published, indent=2), encoding='utf8')
print('PUBLISHED', json.dumps(published))
