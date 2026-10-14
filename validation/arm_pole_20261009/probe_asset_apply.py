"""Disposable native reproduction of Apply Arm Flat -> retract Hand IK."""
import bpy
import json
import os
import sys
import traceback
import copy
from pathlib import Path
from mathutils import Vector, Matrix

assert bpy.app.background
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'approved_0779'))
import character_designer
character_designer.register()
from character_designer import control_pose_assets as poses, control_pose_mirror as mirror
from character_designer import limb_ik, limb_ik_fk as match

with bpy.data.libraries.load(str(BASE.parent.parent / 'X.blend'), link=False) as (src, dst):
    dst.objects = ['CoshaRig']
    dst.actions = ['Arm Flat']
    dst.collections = [n for n in src.collections if 'widget' in n.lower() or 'shape' in n.lower()]
rig = bpy.data.objects['CoshaRig']
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
limb_ik._mode_set(bpy.context, rig, 'POSE')
bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
asset = bpy.data.actions['Arm Flat']
metadata = poses.asset_metadata(asset)
values = poses.channels(asset, rig)
flat_values = copy.deepcopy(values)
reference = poses.desired_pose(rig, values, metadata)
upper = reference['upper_arm.L']
lower = reference['forearm.L'].copy()
alignment = lower.to_3x3().col[1].normalized().rotation_difference(upper.to_3x3().col[1].normalized())
lower = Matrix.LocRotScale(lower.translation, alignment @ lower.to_quaternion(), lower.to_scale())
hand = reference['hand.L'].copy()
hand.translation = lower.translation + lower.to_3x3().col[1].normalized() * rig.data.bones['forearm.L'].length
for name, pose, parent in (('forearm.L', lower, upper), ('hand.L', hand, lower)):
    basis = poses._convert(rig.data.bones[name], pose, parent, invert=True)
    loc, rot, scale = basis.decompose()
    flat_values[name]['rotation_quaternion'] = dict(enumerate(rot))
    flat_values[name]['location'] = dict(enumerate(loc))
initial = {p.name: (p.rotation_mode, p.matrix_basis.copy(), p.get('ik_fk')) for p in rig.pose.bones}

def update():
    match._update(bpy.context, rig)

def restore(state):
    for n, (mode, basis, switch) in state.items():
        p = rig.pose.bones[n]
        p.rotation_mode = mode
        p.matrix_basis = basis
        if switch is not None:
            p['ik_fk'] = switch
    update()

def read(side):
    a, b, c = [rig.pose.bones[n + '.' + side].matrix.translation.copy()
               for n in ('upper_arm', 'forearm', 'hand')]
    axis = (c - a).normalized()
    radial = b - a - axis * (b - a).dot(axis)
    back = Vector((0, 1, 0)); back -= axis * back.dot(axis)
    return {'a': list(a), 'b': list(b), 'c': list(c), 'radial': list(radial),
            'radial_ratio': radial.length / (c - a).length,
            'direction': list(radial.normalized()),
            'back_dot': radial.normalized().dot(back.normalized()),
            'source_quats': {n: list(rig.pose.bones[n + '.' + side].rotation_quaternion)
                             for n in ('upper_arm', 'forearm', 'hand')},
            'pole': list(rig.pose.bones['CTRL_elbow_pole.' + side].matrix.translation)}

report = {'runtime': character_designer.bl_info['version'], 'cases': []}
original_switch = match.switch_limb
original_match = poses._match
original_plane = match._match_pole_plane
plane_text = (BASE / 'approved_0779' / 'character_designer' / 'limb_ik_fk.py').read_text(encoding='utf-8')
plane_text = plane_text[plane_text.index('def _match_pole_plane('):plane_text.index('def _fk_parent_dependencies(')]
exec(plane_text.replace('* 0.01', '* 0.02').replace('def _match_pole_plane(', 'def _probe_plane('), match.__dict__)

def preserving_switch(context, armature, key, mode, **kwargs):
    if mode == 'FK':
        return original_switch(context, armature, key, mode, **kwargs)
    entry = limb_ik._validate_inventory(armature)['rigs'][key]
    for n in entry['chain']:
        armature.pose.bones[n].matrix_basis = initial[n][1]
    match._update(context, armature)
    return original_switch(context, armature, key, mode, **kwargs)

outer_desired = None
def intent_match(context, armature, desired, changed, **kwargs):
    global outer_desired
    outer_desired = desired
    return original_match(context, armature, desired, changed, **kwargs)

def intent_switch(context, armature, key, mode, **kwargs):
    if mode == 'FK':
        return {'mode': 'FK', 'probe_only': True}
    entry = limb_ik._validate_inventory(armature)['rigs'][key]
    wanted = kwargs['desired_pose']
    plane = {n: m.copy() for n, m in wanted.items()}
    a, b, c = [wanted[n].translation for n in entry['chain']]
    axis = (c-a).normalized()
    plane[entry['chain'][1]].translation = a + axis * (b-a).dot(axis)
    match._match_ik(context, armature, limb_ik._validate_inventory(armature), entry, plane)
    update()
    errors = {'pos': match._pose_errors(armature, wanted)[0],
              'rot': match._pose_errors(armature, wanted)[1]}
    print('INTENT_ADJUST', key, errors, flush=True)
    for n in entry['chain'][:2]:
        wanted[n] = outer_desired[n] = armature.pose.bones[n].matrix.copy()
    return {'mode': 'IK', 'adjust': errors}

try:
    for variant in ('dirty_seed_intent',):
        match.switch_limb = intent_switch
        poses._match = intent_match
        match._match_pole_plane = original_plane
        for flipped, side in ((False, 'L'), (True, 'R')):
            restore(initial)
            dirty = json.loads((BASE / 'live_before.json').read_text(encoding='utf-8'))
            for n in ('upper_arm.'+side, 'forearm.'+side, 'hand.'+side):
                rig.pose.bones[n].matrix_basis = Matrix(dirty['bones'][n]['matrix_basis'])
            update()
            authored = mirror.mirrored_channels(rig, values, metadata=metadata) if flipped else values
            before = read(side)
            outcome = poses.apply_channels(bpy.context, rig, authored, metadata=metadata)
            after = read(side)
            applied = {p.name: (p.rotation_mode, p.matrix_basis.copy(), p.get('ik_fk')) for p in rig.pose.bones}
            for clear in (False, True):
                for fraction in (.02, .15, .30):
                    restore(applied)
                    if clear:
                        for n in ('CTRL_hand_IK.', 'CTRL_elbow_pole.'):
                            rig.pose.bones[n + side].location = (0, 0, 0)
                            rig.pose.bones[n + side].rotation_quaternion = (1, 0, 0, 0)
                        update()
                    origin = read(side)
                    target = rig.pose.bones['CTRL_hand_IK.' + side]
                    m = target.matrix.copy()
                    a, c = Vector(origin['a']), Vector(origin['c'])
                    m.translation += (a - c) * fraction
                    target.matrix = m
                    update()
                    record = dict(variant=variant, flipped=flipped, side=side, clear_controls=clear,
                                  retract=fraction, before=before, applied=after, outcome=outcome,
                                  result=read(side))
                    report['cases'].append(record)
                    print('APPLY_DRAG', variant, side, clear, fraction,
                          'back', record['result']['back_dot'], 'dir', record['result']['direction'], flush=True)
except Exception:
    report['error'] = traceback.format_exc()
    raise
finally:
    match.switch_limb = original_switch
    poses._match = original_match
    match._match_pole_plane = original_plane
    report['flat_values'] = flat_values
    (BASE / 'asset_apply_dirty_intent_probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
