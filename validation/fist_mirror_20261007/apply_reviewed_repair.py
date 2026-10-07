"""Apply the reviewed scene repair. Run only after the artist chooses direction."""
import hashlib
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix
from character_designer import limb_ik, finger_chain, finger_bone_mirror, finger_symmetry, finger_targets

folder = Path(__file__).resolve().parent
choice = json.loads((folder / 'artist_repair_choice.json').read_text(encoding='utf-8'))
assert choice['repair_right_arm'] is True
repair_middle = choice['repair_middle_from_left']
assert isinstance(repair_middle, bool)
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert bpy.context.area and bpy.context.area.type == 'CONSOLE'
rig = bpy.context.object
assert rig and rig.name == 'CoshaRig' and rig.type == 'ARMATURE' and rig.mode == 'POSE'
obj = bpy.data.objects['Cosha']
live = json.loads((folder / 'current_diagnostic.json').read_text(encoding='utf-8'))
isolated = json.loads((folder / 'isolated_mirror_test.json').read_text(encoding='utf-8'))
report_file = folder / 'live_repair.json'
recovery = folder / 'X_immediately_before_reviewed_repair.blend'
assert not report_file.exists() and not recovery.exists()
F = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
middle = {'f_middle.'+n+'.'+s for n in ('01', '02', '03') for s in ('L', 'R')}
right_middle = {n for n in middle if n.endswith('.R')}

def mat(m): return [list(row) for row in m]
def difference(a, b): return max(abs(x-y) for ar,br in zip(a,b) for x,y in zip(ar,br))
def raw():
    return {pb.name: {'rotation_mode': pb.rotation_mode, 'location': list(pb.location),
                     'rotation_quaternion': list(pb.rotation_quaternion), 'rotation_euler': list(pb.rotation_euler),
                     'rotation_axis_angle': list(pb.rotation_axis_angle), 'scale': list(pb.scale)} for pb in rig.pose.bones}
def rest(): return {b.name: mat(b.matrix_local) for b in rig.data.bones}
def evaluated():
    bpy.context.view_layer.update()
    return {pb.name: pb.matrix.copy() for pb in rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones}
def angle(a,b):
    return math.degrees(a.to_quaternion().rotation_difference(b.to_quaternion()).angle)
def fingerprint_mesh():
    h = hashlib.sha256()
    for v in obj.data.vertices:
        h.update(repr((v.index, tuple(v.co), tuple((g.group,g.weight) for g in v.groups))).encode())
    for p in obj.data.polygons: h.update(repr(tuple(p.vertices)).encode())
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            h.update(repr((key.name, key.value, key.mute, key.vertex_group)).encode())
            for v in key.data: h.update(repr(tuple(v.co)).encode())
    return h.hexdigest()

raw_before = raw()
rest_before = rest()
eval_before = evaluated()
selected = {p.name: p.select for p in rig.pose.bones}
active = rig.data.bones.active.name if rig.data.bones.active else None
frame = (bpy.context.scene.frame_current, bpy.context.scene.frame_subframe)
auto_key = bpy.context.scene.tool_settings.use_keyframe_insert_auto
assert auto_key is False
mesh_hash = fingerprint_mesh()
for n in sorted(middle)+['upper_arm.L','upper_arm.R','forearm.R','hand.R']:
    assert difference(rest_before[n],live['bones'][n]['rest_matrix']) < 2e-6, 'Relevant Rest changed since diagnosis: '+n
inventory = limb_ik._validate_inventory(rig)
arm = inventory['rigs'][('ARM','R')]
ik = next(c for _pb,c,record in arm['entries'] if record['role'] == 'IK')
old_angle = ik.pole_angle
diagnosed_ik = next(c for c in live['bones']['forearm.R']['constraints'] if c['type'] == 'IK' and not c['mute'])
assert abs(old_angle-diagnosed_ik['pole_angle']) < 1e-4
assert angle(rig.data.bones['upper_arm.R'].matrix_local,eval_before['upper_arm.R']) > 150, 'Current arm changed; re-diagnose instead of flipping blindly'
if repair_middle:
    finger_symmetry.guard_rig(rig)
    for name in middle:
        pb = rig.pose.bones[name]
        assert not pb.constraints and difference(mat(pb.matrix_basis),mat(Matrix.Identity(4))) < 2e-6
        expected_child = ('f_middle.'+{'01':'02','02':'03'}[name.split('.')[1]]+'.'+name[-1]
                          if name.split('.')[1] in {'01','02'} else None)
        assert {child.name for child in pb.bone.children} == ({expected_child} if expected_child else set()), 'Unexpected child under repaired finger'
    # Existing generated drivers on unrelated controls are allowed. Any Action,
    # NLA or driver that authors these six finger channels blocks this repair.
    if rig.animation_data:
        actions = ([rig.animation_data.action] if rig.animation_data.action else [])
        actions += [s.action for t in rig.animation_data.nla_tracks for s in t.strips if s.action]
        for a in actions:
            for layer in a.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        assert not any(any('pose.bones['+json.dumps(n)+']' in fc.data_path for n in middle) for fc in bag.fcurves)
        assert not any(any('pose.bones['+json.dumps(n)+']' in fc.data_path for n in middle) for fc in rig.animation_data.drivers)

saved = bpy.ops.wm.save_as_mainfile(filepath=str(recovery), copy=True)
assert saved == {'FINISHED'} and Path(bpy.data.filepath).resolve() == artist.resolve()
assert raw() == raw_before and rest() == rest_before and fingerprint_mesh() == mesh_hash
bpy.ops.ed.undo_push(message='Before reviewed right arm and middle finger repair')
old_binding = None
state = getattr(obj, 'character_designer_finger_bank', None)
slot = state.slots.get('MIDDLE.R') if state else None
if slot: old_binding = slot.bones
edit_snapshot = None
try:
    result = bpy.ops.character_designer.limb_ik_flip_pole(kind='ARM',side='R')
    assert result == {'FINISHED'}
    rig.update_tag(refresh={'OBJECT','DATA'})
    arm_after = evaluated()
    assert angle(rig.data.bones['upper_arm.R'].matrix_local,arm_after['upper_arm.R']) < 2
    assert difference(eval_before['upper_arm.L'],arm_after['upper_arm.L']) < 2e-6
    if repair_middle:
        # The existing mirror writer/verification/binding commit are used with
        # explicit reviewed names. Global UI Capture/driver restrictions do not
        # substitute for this proven, neutral, isolated FK repair preflight.
        with finger_targets.edit_rig(bpy.context,rig):
            edit_snapshot = finger_chain._snapshot_edit(rig)
            planned = {}
            for number in ('01','02','03'):
                source = rig.data.edit_bones['f_middle.'+number+'.L']
                target = rig.data.edit_bones['f_middle.'+number+'.R']
                planned[target.name] = {'head': F @ source.head, 'tail': F @ source.tail,
                                        'x': -(F.to_3x3() @ source.x_axis).normalized(),
                                        'y': (F.to_3x3() @ source.y_axis).normalized(),
                                        'z': (F.to_3x3() @ source.z_axis).normalized()}
            rig.data.use_mirror_x = False
            finger_bone_mirror._write(rig,planned,edit_snapshot)
            finger_bone_mirror._verify(rig,edit_snapshot,planned)
            finger_bone_mirror._commit_binding(obj,rig,'MIDDLE.R',planned)
            rig.update_tag(refresh={'DATA'})
    assert raw() == raw_before
    after_rest = rest()
    changed_rest = {n for n in rest_before if difference(rest_before[n],after_rest[n]) > 2e-6}
    assert changed_rest == (right_middle if repair_middle else set())
    assert fingerprint_mesh() == mesh_hash
    assert {p.name:p.select for p in rig.pose.bones} == selected
    assert (rig.data.bones.active.name if rig.data.bones.active else None) == active
    assert frame == (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
    assert auto_key == bpy.context.scene.tool_settings.use_keyframe_insert_auto
    limb_ik._validate_inventory(rig)
except Exception:
    ik.pole_angle = old_angle
    if edit_snapshot:
        with finger_targets.edit_rig(bpy.context,rig):
            finger_chain._restore_edit(rig,edit_snapshot)
            rig.update_tag(refresh={'DATA'})
    if slot: slot.bones = old_binding
    rig.update_tag(refresh={'OBJECT','DATA'})
    bpy.context.view_layer.update()
    raise
final_eval = evaluated()
bpy.ops.ed.undo_push(message='Reviewed right arm and middle finger repair')
report = {'choice':choice, 'artist':str(artist),'pre_repair_copy':str(recovery),
          'pre_repair_sha256':hashlib.sha256(recovery.read_bytes()).hexdigest(),
          'pole_before':old_angle,'pole_after':ik.pole_angle,
          'upper_arm_R_rest_angle_before':angle(rig.data.bones['upper_arm.R'].matrix_local,eval_before['upper_arm.R']),
          'upper_arm_R_rest_angle_after':angle(rig.data.bones['upper_arm.R'].matrix_local,final_eval['upper_arm.R']),
          'changed_rest':sorted(changed_rest),'rest_after':{n:after_rest[n] for n in right_middle},
          'pose_channels_unchanged':True,'mesh_weights_keys_unchanged':True,'mesh_sha256':mesh_hash,
          'mode':bpy.context.mode,'frame':frame,'selected':sorted(n for n,v in selected.items() if v),'active':active,
          'auto_key':auto_key,'inventory_verified':True,'artist_saved':False}
report_file.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('REVIEWED_REPAIR_APPLIED_AND_VERIFIED; artist still needs native save')
