"""Disposable saved-X display fit verification. Never writes the production blend."""
import hashlib
import json
import os
import sys

import bpy
from mathutils import Matrix

ROOT = r'D:\MyRepository\Blender-addons-by-Randy'
SOURCE = r'D:\Blender\Projects\Character\X\X.blend'
OUTPUT = r'D:\Blender\Projects\Character\X\outputs\rig'
sys.path.insert(0, os.path.join(ROOT, 'addons'))
from character_designer import foot_controls as feet, limb_ik, limb_ik_fk


def digest_file(path):
    with open(path, 'rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def mesh_state():
    digest = hashlib.sha256()
    for obj in sorted((obj for obj in bpy.data.objects if obj.type == 'MESH'), key=lambda obj: obj.name):
        digest.update(obj.name.encode())
        for vertex in obj.data.vertices:
            digest.update(repr((tuple(vertex.co), [(item.group, item.weight) for item in vertex.groups])).encode())
        for polygon in obj.data.polygons:
            digest.update(repr(tuple(polygon.vertices)).encode())
    return digest.hexdigest()


def rest_state(rig):
    return {bone.name: [list(row) for row in bone.matrix_local] for bone in rig.data.bones}


def action_state(rig):
    return [(action.name, curve.data_path, curve.array_index,
             [(list(point.co), point.interpolation) for point in curve.keyframe_points])
            for action in limb_ik._actions_for_id(rig) for curve in limb_ik._fcurves_for_action(action)]


def shape_points(rig, roll):
    offset = Matrix.LocRotScale(roll.custom_shape_translation,
                               roll.custom_shape_rotation_euler.to_quaternion(), roll.custom_shape_scale_xyz)
    matrix = rig.matrix_world @ roll.custom_shape_transform.matrix @ offset
    return [matrix @ vertex.co for vertex in roll.custom_shape.data.vertices]


source_sha = digest_file(SOURCE)
bpy.ops.wm.open_mainfile(filepath=SOURCE, load_ui=False)
rig, shoe = bpy.data.objects['CoshaRig'], bpy.data.objects['Shoes']
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
feet._update(bpy.context, rig)
mesh_before, rest_before, action_before = mesh_state(), rest_state(rig), action_state(rig)
poses = {bone.name: bone.matrix.copy() for bone in rig.pose.bones if bone.bone.use_deform}
bases = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
report = {'source': SOURCE, 'source_sha256': source_sha, 'legs': {}}
for side in ('L', 'R'):
    key = ('LEG', side)
    record = feet.get_record(rig, key)
    assert record, side
    old_display = feet._roll_visual_state(rig.pose.bones[record['roll']])
    fitted = feet.fit_roll_visual(bpy.context, rig, key, shoe)
    roll = rig.pose.bones[record['roll']]
    assert roll.custom_shape_transform.name == record['chain'][2]
    rotation, _ball, _tip = feet._foot_display_frame(rig, record['chain'][2], record['toe'])
    points = feet._shoe_points(bpy.context, rig, record['chain'][2], record['toe'], shoe, rotation)
    inv = (rig.matrix_world @ roll.custom_shape_transform.matrix).inverted()
    local = [inv @ point for point in shape_points(rig, roll)]
    displayed = [rotation.transposed() @ point for point in local]
    actual_heel = min(point.y for point in points)
    actual_sole = min(point.z for point in points)
    assert max(point.y for point in displayed) < actual_heel - 0.02
    assert min(point.z for point in displayed) > actual_sole + 0.02
    limb_ik_fk._verify(rig, poses)
    assert rest_state(rig) == rest_before and action_state(rig) == action_before
    assert all(rig.pose.bones[name].matrix_basis == basis for name, basis in bases.items())
    feet.restore_roll_visual(bpy.context, rig, key)
    assert feet._roll_visual_state(roll) == old_display
    feet.fit_roll_visual(bpy.context, rig, key, shoe)
    target = rig.pose.bones[record['target']]
    for angle in (-0.25, 0.6, 1.0):
        roll.rotation_euler.x = angle
        target.rotation_euler.x += 0.2
        target.rotation_euler.z += 0.1
        target.location.z += 0.02
        feet._update(bpy.context, rig)
        world = rig.matrix_world @ rig.pose.bones[record['chain'][2]].matrix
        error = max((world @ expected - actual).length for expected, actual in zip(local, shape_points(rig, roll)))
        assert error < 1e-5
    for name, basis in bases.items():
        rig.pose.bones[name].matrix_basis = basis
    feet._update(bpy.context, rig)
    limb_ik_fk._verify(rig, poses)
    report['legs'][side] = {'native_foot': record['chain'][2], 'fit': fitted['roll_visual_fit'],
                           'whole_wire_rear_gap': actual_heel - max(point.y for point in displayed),
                           'whole_wire_sole_clearance': min(point.z for point in displayed) - actual_sole,
                           'motion_follow_max_error': error, 'restore_exact': True}
assert mesh_state() == mesh_before
assert rest_state(rig) == rest_before and action_state(rig) == action_before
limb_ik._validate_inventory(rig)
preview = os.path.join(OUTPUT, 'X_foot_visual_047_preview.blend')
bpy.ops.wm.save_as_mainfile(filepath=preview, copy=True, check_existing=False)
assert digest_file(SOURCE) == source_sha
report.update(ok=True, preview=preview, geometry_weights_unchanged=True, rest_unchanged=True,
              animation_unchanged=True, source_unchanged=True)
with open(os.path.join(OUTPUT, 'foot_visual_047_verification.json'), 'w', encoding='utf8') as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print('FOOT_VISUAL_REAL_X_PASS', json.dumps(report), flush=True)
