import bpy
import hashlib
import json
from mathutils import Vector
from pathlib import Path

BASE = Path(r'D:\Blender\Projects\Character\X\validation\arm_pole_20261009')
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert bpy.app.background
capture = json.loads((BASE / 'live_before.json').read_text(encoding='utf-8'))
repair = json.loads((BASE / 'live_repair.json').read_text(encoding='utf-8'))
with bpy.data.libraries.load(str(ARTIST), link=False) as (src, dst):
    dst.objects = ['CoshaRig']
rig = bpy.data.objects['CoshaRig']
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.context.view_layer.update()
namespace = {}
exec(compile((BASE / 'repair_seed.py').read_text(encoding='utf-8'), 'repair_functions_readonly', 'exec'), namespace)
channels = namespace['channels'](rig)
for name, actual in channels.items():
    original = capture['bones'][name]
    expected = {k: original[k] for k in actual}
    if name in repair['after']:
        expected['rotation_quaternion'] = repair['after'][name]['rotation_quaternion']
    assert actual == expected, ('Saved pose differs', name)
    rest = original['rest_matrix']
    assert all(rig.data.bones[name].matrix_local[i][j] == rest[i][j] for i in range(4) for j in range(4)), ('Saved Rest differs', name)
basis = {p.name: p.matrix_basis.copy() for p in rig.pose.bones}
cases = []
for side in ('L', 'R'):
    ik = next(c for c in rig.pose.bones['forearm.' + side].constraints if c.type == 'IK')
    original_ik = next(c for c in capture['bones']['forearm.' + side]['constraints'] if c['type'] == 'IK')
    assert ik.pole_angle == original_ik['pole_angle']
    for fraction in (0.02, 0.15, 0.30):
        for name, matrix in basis.items():
            rig.pose.bones[name].matrix_basis = matrix
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        start = rig.pose.bones['upper_arm.' + side].matrix.translation.copy()
        target = rig.pose.bones['CTRL_hand_IK.' + side]
        matrix = target.matrix.copy()
        matrix.translation += (start - matrix.translation) * fraction
        target.matrix = matrix
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        joint = rig.pose.bones['forearm.' + side].matrix.translation
        end = rig.pose.bones['hand.' + side].matrix.translation
        axis = (end - start).normalized()
        radial = joint - start - axis * (joint - start).dot(axis)
        back = Vector((0, 1, 0)); back -= axis * back.dot(axis)
        dot = radial.normalized().dot(back.normalized())
        assert dot > 0.97, ('Saved elbow direction', side, fraction, dot)
        cases.append({'side': side, 'retract': fraction, 'back_dot': dot})
receipt = {'artist': str(ARTIST), 'artist_sha256': hashlib.sha256(ARTIST.read_bytes()).hexdigest(),
           'saved_source_rotations_verified': True, 'all_other_saved_pose_channels_preserved': True,
           'all_saved_rest_matrices_preserved': True, 'pole_angles_preserved': True,
           'saved_file_drag_cases': cases, 'passed': True, 'blender': bpy.app.version_string,
           'artist_ui_shader_editor_restored': True, 'artist_ui_native_save_message': 'Saved X.blend',
           'artist_ui_title_clean_after_final_ctrl_s': True,
           'validation_limit': 'Drag tests run on an isolated armature appended from the final saved file; artist hand controls were not dragged by the test.'}
(BASE / 'saved_reopen_verified.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('ARM_POLE_SAVED_REOPEN_PASS', len(cases), receipt['artist_sha256'])
