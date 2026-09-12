import bpy
import json
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
assert Path(bpy.data.filepath).resolve() == (out.parents[1] / 'X.blend').resolve()
rig = bpy.data.objects['CoshaRig']
snapshot = out / 'fixtures/X_auto_align_before_20260912_foot.blend'
assert not snapshot.exists(), 'Do not replace the original diagnostic snapshot'
if bpy.context.area.type == 'CONSOLE':
    bpy.context.area.type = 'VIEW_3D'
bpy.ops.wm.save_as_mainfile(filepath=str(snapshot), copy=True)
report = {'file': bpy.data.filepath, 'copy': str(snapshot), 'bone_count': len(rig.data.bones),
          'data': {k: str(v) for k, v in rig.data.items() if 'foot' in k}, 'feet': {}}
for name in ('CTRL_foot_IK.L', 'CTRL_foot_IK.R'):
    bone = rig.pose.bones.get(name)
    if bone:
        report['feet'][name] = {'properties': dict(bone.bone.items()),
                                'matrix': [list(row) for row in bone.matrix]}
(out/'auto_align_foot_live_capture.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf8')
print('AUTO_ALIGN_CAPTURE_OK', str(snapshot))
