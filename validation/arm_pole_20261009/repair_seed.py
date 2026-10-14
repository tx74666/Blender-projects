"""Restore only the six arm source rotations from the last verified neutral seed."""
import bpy
import hashlib
import json
import math
import struct
from array import array
from pathlib import Path

BASE = Path(r'D:\Blender\Projects\Character\X\validation\arm_pole_20261009')
REFERENCE = json.loads((BASE.parent / 'arm_flat_mirror_20261008' / 'live_before.json').read_text(encoding='utf-8'))
CAPTURE = json.loads((BASE / 'live_before.json').read_text(encoding='utf-8'))
NAMES = [n + '.' + side for side in ('L', 'R') for n in ('upper_arm', 'forearm', 'hand')]

def matrix_rows(matrix):
    return [list(row) for row in matrix]

def channels(rig):
    return {p.name: {'location': list(p.location), 'rotation_mode': p.rotation_mode,
                    'rotation_quaternion': list(p.rotation_quaternion),
                    'rotation_euler': list(p.rotation_euler), 'rotation_axis_angle': list(p.rotation_axis_angle),
                    'scale': list(p.scale)} for p in rig.pose.bones}

def protected(rig):
    rest = {b.name: {'matrix': matrix_rows(b.matrix_local), 'parent': b.parent.name if b.parent else None,
                    'head': list(b.head_local), 'tail': list(b.tail_local), 'use_deform': b.use_deform}
            for b in rig.data.bones}
    actions = []
    for action in bpy.data.actions:
        bags = [bag for layer in action.layers for strip in layer.strips for bag in getattr(strip, 'channelbags', ())]
        actions.append({'name': action.name, 'slots': [s.identifier for s in action.slots],
                        'curves': [(c.data_path, c.array_index, c.mute,
                                    [(list(k.co), list(k.handle_left), list(k.handle_right), k.interpolation)
                                     for k in c.keyframe_points]) for bag in bags for c in bag.fcurves]})
    meshes = {}
    for mesh in bpy.data.meshes:
        digest = hashlib.sha256()
        coords = array('f', [0.0]) * (len(mesh.vertices) * 3)
        mesh.vertices.foreach_get('co', coords)
        digest.update(coords.tobytes())
        for vertex in mesh.vertices:
            for group in vertex.groups:
                digest.update(struct.pack('<IIf', vertex.index, group.group, group.weight))
        if mesh.shape_keys:
            for key in mesh.shape_keys.key_blocks:
                digest.update(key.name.encode('utf-8'))
                key.data.foreach_get('co', coords)
                digest.update(coords.tobytes())
        meshes[mesh.name] = [len(mesh.vertices), len(mesh.edges), len(mesh.polygons), digest.hexdigest()]
    angles = {p.name: [(c.name, c.pole_angle, c.pole_subtarget, c.chain_count, c.mute)
                      for c in p.constraints if c.type == 'IK'] for p in rig.pose.bones}
    return {'rest': rest, 'actions': actions, 'meshes': meshes, 'ik_constraints': angles}

def repair(rig):
    assert rig.type == 'ARMATURE'
    assert 'character_designer_body_original_mode_v1' not in rig
    assert not rig.animation_data or (not rig.animation_data.action and not rig.animation_data.nla_tracks)
    before = channels(rig)
    expected_channels = {n: {key: b[key] for key in next(iter(before.values()))} for n, b in CAPTURE['bones'].items()}
    assert before == expected_channels, 'Artist pose changed since read-only capture; recapture before applying'
    assert matrix_rows(rig.matrix_world) == CAPTURE['rig_matrix_world']
    for side in ('L', 'R'):
        target = rig.pose.bones['CTRL_hand_IK.' + side]
        pole = rig.pose.bones['CTRL_elbow_pole.' + side]
        assert target.get('ik_fk') == 1.0
        assert target.bone.get('character_designer_owner') == 'limb_ik'
        assert pole.bone.get('character_designer_owner') == 'limb_ik'
        assert max(abs(x) for x in target.location) < 1e-7
        assert max(abs(x) for x in pole.location) < 1e-7
        ik = next(c for c in rig.pose.bones['forearm.' + side].constraints if c.type == 'IK')
        expected_ik = next(c for c in CAPTURE['bones']['forearm.' + side]['constraints'] if c['type'] == 'IK')
        assert not ik.mute and ik.influence == 1.0
        assert ik.target == rig and ik.pole_target == rig
        assert ik.subtarget == expected_ik['subtarget'] and ik.pole_subtarget == expected_ik['pole_subtarget']
        assert ik.pole_angle == expected_ik['pole_angle'] and ik.chain_count == expected_ik['chain_count']
    if rig.animation_data:
        for fc in rig.animation_data.drivers:
            assert not any(fc.data_path.startswith('pose.bones["' + name + '"].' + channel)
                           for name in NAMES for channel in ('rotation_', 'location', 'scale', 'matrix_basis')), 'Animated source seed'
    for name in NAMES:
        pb = rig.pose.bones[name]
        assert pb.rotation_mode == 'QUATERNION'
        assert max(abs(pb.rotation_quaternion[i] - CAPTURE['bones'][name]['rotation_quaternion'][i]) for i in range(4)) < 1e-6
        expected_rest = REFERENCE['bones'][name]['rest_matrix']
        assert max(abs(pb.bone.matrix_local[i][j] - expected_rest[i][j]) for i in range(4) for j in range(4)) < 1e-6
    asset_state = protected(rig)
    endpoints = {side: rig.pose.bones['hand.' + side].matrix.translation.copy() for side in ('L', 'R')}
    try:
        for name in NAMES:
            rig.pose.bones[name].rotation_quaternion = REFERENCE['raw'][name]['rotation_quaternion']
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        after = channels(rig)
        for name in before:
            expected = dict(before[name])
            if name in NAMES:
                expected['rotation_quaternion'] = REFERENCE['raw'][name]['rotation_quaternion']
            assert after[name] == expected, ('Unexpected pose channel change', name)
        assert protected(rig) == asset_state, 'Protected model or action changed'
        endpoint_error = max((rig.pose.bones['hand.' + side].matrix.translation - endpoints[side]).length for side in ('L', 'R'))
        assert endpoint_error < 1e-5, ('Hand endpoint moved', endpoint_error)
    except BaseException:
        for name, state in before.items():
            pb = rig.pose.bones[name]
            for key in ('rotation_mode', 'location', 'scale', 'rotation_euler', 'rotation_axis_angle', 'rotation_quaternion'):
                setattr(pb, key, state[key])
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        assert channels(rig) == before, 'Rollback could not restore the complete pose snapshot'
        raise
    return {'changed_source_rotations': NAMES, 'before': {n: before[n] for n in NAMES},
            'after': {n: after[n] for n in NAMES}, 'max_hand_endpoint_error': endpoint_error,
            'rest_weights_shape_key_geometry_action_curves_and_pole_angles_preserved': True,
            'all_other_pose_channels_preserved': True}

if globals().get('RUN_LIVE_REPAIR', False):
    artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
    assert Path(bpy.data.filepath).resolve() == artist.resolve()
    backup = json.loads((BASE / 'backup_receipt.json').read_text(encoding='utf-8'))
    assert Path(backup['artist']).resolve() == artist.resolve()
    checkpoint = Path(backup['backup'])
    assert checkpoint.resolve() == (BASE / 'X_before_arm_pole_seed_repair.blend').resolve()
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == backup['backup_sha256']
    assert bpy.context.scene.frame_current == CAPTURE['frame'] and bpy.context.mode == CAPTURE['mode']
    assert not (BASE / 'live_repair.json').exists(), 'Inspect existing repair receipt before repeating'
    rig = bpy.data.objects['CoshaRig']
    report = repair(rig)
    report.update(artist=str(artist), frame=bpy.context.scene.frame_current,
                  mode=bpy.context.mode, runtime_version=CAPTURE['runtime']['character_designer']['bl_info']['version'])
    (BASE / 'live_repair.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ARM_POLE_SEED_REPAIR_OK', report['max_hand_endpoint_error'])
