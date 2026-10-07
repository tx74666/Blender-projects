"""Native mirror and two diagnosed repair candidates, on the protected copy only."""
import ast
import hashlib
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

folder = Path(__file__).resolve().parent
checkpoint = folder / 'X_before_mirror_diagnosis.blend'
live = json.loads((folder / 'current_diagnostic.json').read_text(encoding='utf-8'))
output = folder / 'isolated_mirror_test.json'
assert not output.exists()
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == live['checkpoint_sha256']
bpy.ops.wm.open_mainfile(filepath=str(checkpoint), load_ui=False)
assert Path(bpy.data.filepath).resolve() == checkpoint.resolve()
rig = bpy.data.objects['CoshaRig']
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
assert rig.mode == 'POSE'
assert bpy.context.scene.tool_settings.use_keyframe_insert_auto is False
action = bpy.data.actions['Fist']
assert action.asset_data is not None
F = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))

def matrix(m):
    return [list(row) for row in m]

def curves(a):
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves

def channels():
    return {pb.name: {'location': list(pb.location), 'rotation_mode': pb.rotation_mode,
                     'rotation_quaternion': list(pb.rotation_quaternion),
                     'rotation_euler': list(pb.rotation_euler),
                     'rotation_axis_angle': list(pb.rotation_axis_angle), 'scale': list(pb.scale)}
            for pb in rig.pose.bones}

def restore(raw):
    for name, values in raw.items():
        pb = rig.pose.bones[name]
        for attr, value in values.items():
            setattr(pb, attr, value)
    rig.update_tag(refresh={'OBJECT', 'DATA'})
    bpy.context.view_layer.update()

def evaluated():
    bpy.context.view_layer.update()
    e = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {p.name: p.matrix.copy() for p in e.pose.bones}

def angle(a, b):
    return math.degrees(a.to_quaternion().rotation_difference(b.to_quaternion()).angle)

def delta(a, b):
    return max(abs(x-y) for ar, br in zip(a, b) for x, y in zip(ar, br))

initial = channels()
assert all(initial[n]['rotation_quaternion'] == live['raw'][n]['rotation_quaternion'] for n in initial)
rest_before = {b.name: b.matrix_local.copy() for b in rig.data.bones}
before_eval = evaluated()
report = {'blender_version': bpy.app.version_string, 'checkpoint_sha256': live['checkpoint_sha256'],
          'method': 'Blender Action.flip_with_pose and Pose.apply_pose_from_action; same C++ mirror/evaluate functions as native Asset apply; no GUI keymap/undo/autokey coverage',
          'unit_settings': {'system': bpy.context.scene.unit_settings.system,
                            'scale_length': bpy.context.scene.unit_settings.scale_length},
          'baseline_arm_rest_angle': {n: angle(rest_before[n], before_eval[n])
                                     for n in ('upper_arm.L', 'upper_arm.R', 'forearm.R', 'hand.R')}}
paths = sorted({ast.literal_eval(fc.data_path.split('pose.bones[', 1)[1].split(']', 1)[0])
                for fc in curves(action) if fc.data_path.startswith('pose.bones[')})
assert len(paths) == 15 and all(n.endswith('.L') for n in paths)
targets = {bpy.utils.flip_name(n) for n in paths}
assert all(not rig.pose.bones[n].constraints for n in targets)
for pb in rig.pose.bones:
    (pb if hasattr(pb, 'select') else pb.bone).select = False
mirror_action = action.copy()
mirror_action.flip_with_pose(rig)
assert channels() == initial, 'Native Action flip changed raw channels'
after_flip_eval = evaluated()
report['flip_only_eval_changes'] = {n: delta(before_eval[n], after_flip_eval[n]) for n in initial
                                    if delta(before_eval[n], after_flip_eval[n]) > 1e-6}
rig.pose.apply_pose_from_action(mirror_action, evaluation_time=0.0)
after_raw = channels()
after_eval = evaluated()
report['mirror'] = {'changed_raw': [n for n in initial if after_raw[n] != initial[n]],
                    'changed_eval': {n: delta(before_eval[n], after_eval[n]) for n in initial
                                     if delta(before_eval[n], after_eval[n]) > 1e-6},
                    'upper_arm_R_eval_delta': delta(before_eval['upper_arm.R'], after_eval['upper_arm.R']),
                    'upper_arm_R_rest_angle': angle(rest_before['upper_arm.R'], after_eval['upper_arm.R'])}
assert set(report['mirror']['changed_raw']) <= targets
assert report['mirror']['upper_arm_R_eval_delta'] < 1e-6
restore(initial)
constraint = next(c for c in rig.pose.bones['forearm.R'].constraints if c.type == 'IK' and not c.mute)
original_angle = constraint.pole_angle
report['pole_candidates'] = []
for offset in (math.pi, -math.pi):
    restore(initial)
    constraint.pole_angle = original_angle + offset
    rig.update_tag(refresh={'OBJECT', 'DATA'})
    e = evaluated()
    report['pole_candidates'].append({'offset': offset, 'stored_angle': constraint.pole_angle,
                                     'upper_arm_R_rest_angle': angle(rest_before['upper_arm.R'], e['upper_arm.R']),
                                     'upper_arm_R_mirror_left_angle': angle(F @ e['upper_arm.L'] @ F, e['upper_arm.R']),
                                     'hand_R_location_delta': (e['hand.R'].translation-before_eval['hand.R'].translation).length,
                                     'hand_R_rotation_delta': angle(before_eval['hand.R'], e['hand.R']),
                                     'forearm_R_rest_angle': angle(rest_before['forearm.R'], e['forearm.R']),
                                     'changed_raw': [n for n in initial if channels()[n] != initial[n]],
                                     'upper_arm_R_evaluated': matrix(e['upper_arm.R'])})
constraint.pole_angle = original_angle
restore(initial)

# Isolate the middle-finger deformation from wrist and arm pose. The evaluated
# mesh uses its actual Armature modifier and keeps existing shape key values;
# Subdivision is disabled in this temporary process to preserve vertex indices.
obj = bpy.data.objects['Cosha']
mesh_before = [[*v.co] for v in obj.data.vertices]
weights_before = [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices]
key_before = {k.name: [[*v.co] for v in k.data] for k in obj.data.shape_keys.key_blocks}
modifier_before = [(m, m.show_viewport) for m in obj.modifiers]
for mod in obj.modifiers:
    if mod.type != 'ARMATURE':
        mod.show_viewport = False
mesh_data = live['meshes'][0]
core = {v['index']: v for v in mesh_data['vertices']}
left = [v for v in core.values() if any(n.endswith('.L') and n.startswith('f_middle.') and w > 1e-5
                                      for n, w in v['weights'].items())]
right = [v for v in core.values() if any(n.endswith('.R') and n.startswith('f_middle.') and w > 1e-5
                                       for n, w in v['weights'].items())]
pairs = []
for a in left:
    reflected = F @ Vector(a['co'])
    match = [b for b in right if (Vector(b['co'])-reflected).length < 1e-7]
    assert len(match) == 1
    b = match[0]
    deform_names = {n for n, w in a['weights'].items() if w > 1e-5 and n in rig.data.bones
                    and rig.data.bones[n].use_deform}
    isolated = deform_names <= {'f_middle.01.L', 'f_middle.02.L', 'f_middle.03.L'}
    distal = deform_names <= {'f_middle.02.L', 'f_middle.03.L'}
    pairs.append((a['index'], b['index'], isolated, distal))
assert len(pairs) == 84

def paired_mesh():
    restore(initial)
    for pb in rig.pose.bones:
        (pb if hasattr(pb, 'select') else pb.bone).select = False
    rig.pose.apply_pose_from_action(action, evaluation_time=0.0)
    temporary = action.copy()
    temporary.flip_with_pose(rig)
    rig.pose.apply_pose_from_action(temporary, evaluation_time=0.0)
    ev = evaluated()
    dg = bpy.context.evaluated_depsgraph_get()
    evaluated_obj = obj.evaluated_get(dg)
    mesh = evaluated_obj.to_mesh()
    try:
        assert len(mesh.vertices) == len(obj.data.vertices)
        object_to_rig = rig.matrix_world.inverted() @ obj.matrix_world
        normalized = {}
        for side, index_set in (('L', {p[0] for p in pairs}), ('R', {p[1] for p in pairs})):
            transform = rig.data.bones['hand.'+side].matrix_local @ ev['hand.'+side].inverted() @ object_to_rig
            for index in index_set:
                normalized[index] = transform @ mesh.vertices[index].co
        distances = [(a, b, isolated, distal, (F @ normalized[a]-normalized[b]).length)
                     for a, b, isolated, distal in pairs]
        result = {}
        for label, select in (('all_middle', lambda x: True), ('middle_only', lambda x: x[2]),
                              ('distal_only', lambda x: x[3])):
            chosen = [p for p in distances if select(p)]
            result[label] = {'pairs': len(chosen), 'max_rig_space_distance': max((p[4] for p in chosen), default=0),
                             'rms_rig_space_distance': math.sqrt(sum(p[4]**2 for p in chosen)/len(chosen)) if chosen else 0}
        result['largest_pairs'] = [{'left': p[0], 'right': p[1], 'distance': p[4], 'distal_only': p[3]}
                                   for p in sorted(distances, key=lambda p: p[4], reverse=True)[:8]]
        result['normalized_positions'] = {str(k): list(v) for k,v in normalized.items()}
        return result
    finally:
        evaluated_obj.to_mesh_clear()
        bpy.data.actions.remove(temporary)

report['finger_before'] = paired_mesh()
restore(initial)
bpy.ops.object.mode_set(mode='EDIT')
edits = []
for number in ('01', '02', '03'):
    source = rig.data.edit_bones['f_middle.'+number+'.L']
    target = rig.data.edit_bones['f_middle.'+number+'.R']
    old = {'head': list(target.head), 'tail': list(target.tail), 'roll': target.roll}
    target.head = F @ source.head
    target.tail = F @ source.tail
    target.align_roll(F.to_3x3() @ source.z_axis)
    edits.append({'bone': target.name, 'before': old,
                  'candidate': {'head': list(target.head), 'tail': list(target.tail), 'roll': target.roll}})
bpy.ops.object.mode_set(mode='POSE')
report['finger_candidate_edits'] = edits
report['finger_after_rest_candidate'] = paired_mesh()
assert mesh_before == [[*v.co] for v in obj.data.vertices]
assert weights_before == [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices]
assert key_before == {k.name: [[*v.co] for v in k.data] for k in obj.data.shape_keys.key_blocks}
report['finger_candidate_mesh_weights_keys_unchanged'] = True
report['artist_file_not_loaded_or_saved'] = True
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ISOLATED_MIRROR_DIAGNOSIS_COMPLETE', output)
