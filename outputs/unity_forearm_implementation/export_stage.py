import hashlib
import json
import sys
import time
from pathlib import Path
import bpy
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import unity_forearm, unity_export_worker, forearm_twist

root = Path(r'D:\Blender\Projects\Character\X\outputs\unity_forearm_implementation')
stage = root / 'export'
source = Path(bpy.data.filepath)
digest = hashlib.sha256(source.read_bytes()).hexdigest()
body = bpy.data.objects['Cosha']
started = time.perf_counter()
captured = unity_forearm.capture(body)
(root/'Cosha.capture.json').write_text(json.dumps(captured,separators=(',',':')),encoding='utf8')
records = forearm_twist._records(body)
result = unity_export_worker.export_job({'objects':['CoshaRig','Cosha','Clothes','Stocking'],
    'rig':'CoshaRig', 'filename':'Cosha.fbx', 'stage':str(stage),
    'unit_scale':bpy.context.scene.unit_settings.scale_length,
    'owned_keys':{'Cosha':[r['key'] for r in records.values()]},
    'forearm':{'Cosha':captured}})
result['elapsed_seconds'] = time.perf_counter()-started
result['source_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == digest
result['source_sha256'] = digest
(stage/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
sidecar = json.loads((stage/'Cosha.forearm.json').read_text(encoding='utf8'))
spec = sidecar['meshes'][0]
assert spec['vertexCount'] == len(body.data.vertices)
uv = body.data.uv_layers[unity_forearm.UV_NAME]
assert all(tuple(uv.data[loop.index].uv) == (float(loop.vertex_index+1),.375) for loop in body.data.loops)
assert len(body.data.shape_keys.key_blocks) == 8
assert result['source_unchanged']
print('REAL_EXPORT_OK ' + json.dumps({'seconds':result['elapsed_seconds'], 'sources':len(spec['sources']),
    'dense':spec['vertexCount'], 'stencils':len(spec['stencils']), 'idUvChannel':spec['idUvChannel'],
    'stencilCheckMaxError':spec['stencilCheckMaxError'], 'files':result['files'],
    'fbxSha256':sidecar['fbxSha256'], 'warnings':result['warnings']}),flush=True)
