"""Read-only unified planner audit on the saved immutable X fixture."""
import hashlib
import json
import sys
from pathlib import Path
import bpy

OUT = Path(__file__).parent
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import body_setup_plan

source = Path(bpy.data.filepath)
checksum = hashlib.sha256(source.read_bytes()).hexdigest()
rig = bpy.data.objects['CoshaRig']
before = {'data': repr(dict(rig.data.items())), 'object': repr(dict(rig.items())),
          'bone_count': len(rig.data.bones), 'objects': len(bpy.data.objects)}
report = {'source': str(source), 'sha256': checksum,
          'plan': body_setup_plan.plan(bpy.context, rig)}
after = {'data': repr(dict(rig.data.items())), 'object': repr(dict(rig.items())),
         'bone_count': len(rig.data.bones), 'objects': len(bpy.data.objects)}
report['unchanged'] = before == after
report['source_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == checksum
(OUT / 'body_setup_0546_saved_plan.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('BODY_SETUP_SAVED_PLAN', json.dumps(report), flush=True)
assert report['unchanged'] and report['source_unchanged']
