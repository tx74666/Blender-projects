import bpy
import hashlib
import json
from pathlib import Path

BASE = Path(r'D:\Blender\Projects\Character\X\validation\arm_pole_20261009')
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
BACKUP = BASE / 'X_before_arm_pole_seed_repair.blend'
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
assert not BACKUP.exists(), 'Protection copy already exists; inspect its receipt instead of overwriting it'
rig = bpy.data.objects['CoshaRig']
before = {p.name: [list(row) for row in p.matrix_basis] for p in rig.pose.bones}
before_angles = {p.name: [(c.name, c.pole_angle) for c in p.constraints if c.type == 'IK'] for p in rig.pose.bones}
artist_sha = hashlib.sha256(ARTIST.read_bytes()).hexdigest()
result = bpy.ops.wm.save_as_mainfile(filepath=str(BACKUP), copy=True)
assert result == {'FINISHED'}
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
assert {p.name: [list(row) for row in p.matrix_basis] for p in rig.pose.bones} == before
assert {p.name: [(c.name, c.pole_angle) for c in p.constraints if c.type == 'IK'] for p in rig.pose.bones} == before_angles
assert hashlib.sha256(ARTIST.read_bytes()).hexdigest() == artist_sha
receipt = {'artist': str(ARTIST), 'artist_sha256_before': artist_sha, 'backup': str(BACKUP),
           'backup_sha256': hashlib.sha256(BACKUP.read_bytes()).hexdigest(),
           'native_result': sorted(result), 'all_pose_channels_preserved': True,
           'all_pole_angles_preserved': True, 'artist_filepath_preserved': True}
(BASE / 'backup_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('ARM_POLE_ARTIST_PROTECTION_OK', str(BACKUP))
