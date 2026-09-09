import bpy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import eye_controls as eyes

root = Path(r'D:\Blender\Projects\Character\X')
source = root / 'X.blend'
before = hashlib.sha256(source.read_bytes()).hexdigest()
cd.register()
bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
rig = bpy.data.objects['CoshaRig']
record = eyes.validate(rig)
report = {'source': str(source), 'sha256': before, 'frame': bpy.context.scene.frame_current,
          'record': record, 'head_length': rig.data.bones[record['head']].length,
          'bone_count': len(rig.data.bones), 'rig_scale': list(rig.scale), 'controls': {}}
for role, name in record['bones'].items():
    pb = rig.pose.bones[name]
    report['controls'][role] = {'name': name, 'position': list(pb.matrix.translation),
        'translation': list(pb.custom_shape_translation), 'scale': list(pb.custom_shape_scale_xyz),
        'rotation': list(pb.custom_shape_rotation_euler), 'bone_size': pb.use_custom_shape_bone_size,
        'matrix': [list(row) for row in pb.matrix]}
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
(root / 'outputs/rig/eye_display_0521_audit.json').write_text(json.dumps(report, indent=2))
print('EYE_DISPLAY_AUDIT', json.dumps({k: v for k, v in report.items() if k != 'record'}), flush=True)
