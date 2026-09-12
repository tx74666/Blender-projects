"""Small disposable-process validation. Never saves the source blend."""
import hashlib
import json
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

SOURCE = Path(r'D:\Blender\Projects\Character\X\X.blend')
OUT = Path(__file__).with_suffix('.json')
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import animation_retarget, limb_ik, limb_ik_fk

report = {'source': str(SOURCE), 'blender': bpy.app.version_string,
          'source_sha256_before': hashlib.sha256(SOURCE.read_bytes()).hexdigest()}

def update():
    rig.update_tag(refresh={'OBJECT'})
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()

def positions():
    update()
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {name: list(evaluated.pose.bones[name].head) for name in names}

def body_vertices():
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return [v.co.copy() for v in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()

try:
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False)
    rig = bpy.data.objects['CoshaRig']
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    rig.data.use_mirror_x = False
    report['existing_action'] = rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None
    try:
        animation_retarget._check_target(rig, tuple(animation_retarget.SOMA_BODY_MAP.values()))
        report['generated_motion_target_preflight'] = {'accepted': True}
    except animation_retarget.RetargetError as error:
        report['generated_motion_target_preflight'] = {'accepted': False, 'reason': str(error)}
    if rig.animation_data:
        rig.animation_data.action = None
        for track in rig.animation_data.nla_tracks:
            track.mute = True
    bpy.context.scene.frame_set(1)
    inventory = limb_ik._validate_inventory(rig)
    report['limbs'] = {str(key): {'mode': limb_ik_fk.mode_for_rig(rig, item),
                                'target': item['target'].name} for key, item in inventory['rigs'].items()}
    targets = []
    for side in ('L', 'R'):
        limb_ik_fk.switch_limb(bpy.context, rig, ('ARM', side), 'IK', keyframe=False)
        targets.append(rig.pose.bones[inventory['rigs'][('ARM', side)]['target'].name])
    names = [p.name for p in targets] + ['hand.L', 'hand.R']
    update()
    bases = {p.name: p.matrix.copy() for p in targets}
    for p in targets:
        p.keyframe_insert(data_path='location', frame=1, group=p.name)
    for p, side in zip(targets, ('L', 'R')):
        matrix = bases[p.name].copy()
        shoulder = rig.pose.bones['upper_arm.' + side].head
        toward_shoulder = (shoulder - matrix.translation).normalized()
        matrix.translation += toward_shoulder * .035 + Vector((0, 0, .015))
        p.matrix = matrix
        update()
        p.keyframe_insert(data_path='location', frame=25, group=p.name)
    action = rig.animation_data.action
    action.name = 'VERIFY ONLY - two control poses'
    curves = animation_retarget._curves(action)
    for curve in curves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    samples = {}
    for frame in (1, 7, 13, 19, 25):
        bpy.context.scene.frame_set(frame)
        samples[str(frame)] = positions()
    errors = {}
    for index, target in enumerate(targets):
        hand = 'hand.' + ('L', 'R')[index]
        start_target = Vector(samples['1'][target.name])
        end_target = Vector(samples['25'][target.name])
        start_hand = Vector(samples['1'][hand])
        errors[target.name] = {
            'control_travel': (end_target - start_target).length,
            'midpoint_linear_error': (Vector(samples['13'][target.name]) - (start_target + end_target) / 2).length,
            'max_hand_follow_delta_error': max(((Vector(s[target.name]) - start_target) - (Vector(s[hand]) - start_hand)).length for s in samples.values()),
        }
    candidates = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
    def arm_weight_score(obj):
        indices = {g.index for g in obj.vertex_groups if g.name in {'upper_arm.L', 'forearm.L', 'hand.L', 'upper_arm.R', 'forearm.R', 'hand.R'}}
        return sum(g.weight for v in obj.data.vertices for g in v.groups if g.group in indices)
    body = max(candidates, key=arm_weight_score)
    bpy.context.scene.frame_set(1)
    update()
    start_vertices = body_vertices()
    bpy.context.scene.frame_set(25)
    update()
    end_vertices = body_vertices()
    report['mesh'] = {'name': body.name, 'vertex_count': len(start_vertices),
                      'max_vertex_movement': max((b-a).length for a, b in zip(start_vertices, end_vertices))}
    bpy.context.scene.frame_set(13)
    before_tweak = positions()
    target = targets[0]
    target.location += Vector((.01, 0, 0))
    target.keyframe_insert(data_path='location', frame=13, group=target.name)
    bpy.context.scene.frame_set(1)
    bpy.context.scene.frame_set(13)
    after_tweak = positions()
    report['manual_tweak'] = {
        'control_delta': (Vector(after_tweak[target.name]) - Vector(before_tweak[target.name])).length,
        'hand_delta': (Vector(after_tweak['hand.L']) - Vector(before_tweak['hand.L'])).length,
        'hand_follow_delta_error': ((Vector(after_tweak[target.name]) - Vector(before_tweak[target.name])) - (Vector(after_tweak['hand.L']) - Vector(before_tweak['hand.L']))).length,
    }
    for frame in (1, 25):
        bpy.context.scene.frame_set(frame)
        state = positions()
        report['manual_tweak']['endpoint_' + str(frame) + '_error'] = max((Vector(state[n]) - Vector(samples[str(frame)][n])).length for n in names)
    report['interpolation'] = errors
    report['samples'] = samples
    report['action_curves'] = len(curves)
    assert all(e['control_travel'] > .01 and e['midpoint_linear_error'] < 2e-5 and e['max_hand_follow_delta_error'] < 2e-4 for e in errors.values()), errors
    assert report['mesh']['max_vertex_movement'] > .001
    assert report['manual_tweak']['control_delta'] > .005
    assert report['manual_tweak']['hand_delta'] > .005
    assert report['manual_tweak']['hand_follow_delta_error'] < 2e-4
    assert report['manual_tweak']['endpoint_1_error'] < 2e-4 and report['manual_tweak']['endpoint_25_error'] < 2e-4
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
finally:
    report['source_sha256_after'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    report['source_unchanged'] = report['source_sha256_before'] == report['source_sha256_after']
    OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('CONTROL_ANIMATION_CHECK', json.dumps({k: v for k, v in report.items() if k != 'samples'}), flush=True)
if report['status'] != 'passed':
    raise RuntimeError(report.get('error'))
