import bpy
import json
import hashlib
from pathlib import Path

ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
BASE = ARTIST.parent / 'validation' / 'arm_flat_fix_20261009'
BASE.mkdir(exist_ok=True)
BACKUP = BASE / 'X_before_arm_flat_fix.blend'
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
assert not BACKUP.exists(), 'Already protected: do not replace the original checkpoint.'
capture = Path(__file__).with_name('capture_live.py').read_text(encoding='utf-8')
capture = capture.replace("OUT = Path(r'D:\\Blender\\Projects\\Character\\X\\validation\\arm_pole_20261009')", 'OUT = Path(' + repr(str(BASE)) + ')')
exec(compile(capture, 'arm_flat_live_capture', 'exec'), {})
rig = bpy.data.objects['CoshaRig']
state = {p.name: [list(r) for r in p.matrix_basis] for p in rig.pose.bones}
sha = hashlib.sha256(ARTIST.read_bytes()).hexdigest()
result = bpy.ops.wm.save_as_mainfile(filepath=str(BACKUP), copy=True)
assert result == {'FINISHED'}
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
assert state == {p.name: [list(r) for r in p.matrix_basis] for p in rig.pose.bones}
assert sha == hashlib.sha256(ARTIST.read_bytes()).hexdigest()
(BASE / 'backup_receipt.json').write_text(json.dumps({'artist':str(ARTIST), 'backup':str(BACKUP),
    'artist_sha256':sha, 'backup_sha256':hashlib.sha256(BACKUP.read_bytes()).hexdigest(),
    'native_result':sorted(result)}, indent=2), encoding='utf-8')
print('ARM_FLAT_FIX_BACKUP_OK', str(BACKUP))
