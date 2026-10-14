import bpy
import hashlib
import json
from pathlib import Path

BASE = Path(r'D:\Blender\Projects\Character\X\validation\arm_pole_20261009')
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
report = json.loads((BASE / 'live_repair.json').read_text(encoding='utf-8'))
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
rig = bpy.data.objects['CoshaRig']
for name, state in report['after'].items():
    assert list(rig.pose.bones[name].rotation_quaternion) == state['rotation_quaternion']
before = {p.name: [list(row) for row in p.matrix_basis] for p in rig.pose.bones}
result = bpy.ops.wm.save_mainfile()
assert result == {'FINISHED'}
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
assert before == {p.name: [list(row) for row in p.matrix_basis] for p in rig.pose.bones}
receipt = {'artist': str(ARTIST), 'native_result': sorted(result), 'is_dirty_at_nested_operator_return': bpy.data.is_dirty,
           'artist_sha256': hashlib.sha256(ARTIST.read_bytes()).hexdigest(),
           'artist_bytes': ARTIST.stat().st_size, 'frame': bpy.context.scene.frame_current,
           'mode': bpy.context.mode, 'all_pose_matrices_preserved_during_save': True,
           'layout_restore_pending': True}
(BASE / 'save_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('ARM_POLE_SAVE_VERIFIED', sorted(result), 'dirty', bpy.data.is_dirty)
