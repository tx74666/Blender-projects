"""Offline arithmetic on the captured JSON; no Blender import or model writes."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = ROOT / 'current_diagnostic.json'
j = json.loads(source.read_text(encoding='utf-8'))

def dot(a, b):
    return sum(x*y for x, y in zip(a, b))

def sub(a, b):
    return [x-y for x, y in zip(a, b)]

def length(a):
    return math.sqrt(dot(a, a))

def norm(a):
    return [x/length(a) for x in a]

def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

def cols(m):
    x = norm([m[r][0] for r in range(3)])
    y = [m[r][1] for r in range(3)]
    y = norm([v-dot(x, y)*u for v, u in zip(y, x)])
    z = cross(x, y)
    return x, y, z

def angle(a, b):
    trace = sum(dot(x, y) for x, y in zip(cols(a), cols(b)))
    return math.degrees(math.acos(max(-1., min(1., (trace-1)/2))))

def axis_angles(a, b):
    return [math.degrees(math.acos(max(-1., min(1., dot(x,y)))))
            for x, y in zip(cols(a), cols(b))]

def maxdiff(a, b):
    return max(abs(x-y) for ar, br in zip(a, b) for x,y in zip(ar,br))

def mirror(m):
    sign = (-1, 1, 1, 1)
    return [[m[r][c]*sign[r]*sign[c] for c in range(4)] for r in range(4)]

def origin(m):
    return [m[r][3] for r in range(3)]

def compact_constraint(c):
    return {k:c[k] for k in ('name','type','mute','enabled','influence',
                             'subtarget','pole_subtarget','pole_angle','chain_count') if k in c}

fingers = sorted(n for n in j['bones'] if n.endswith('.R') and n.startswith(('f_', 'thumb.')))
measurements = {}
for stem in ('shoulder', 'upper_arm', 'forearm', 'hand', 'CTRL_hand_IK', 'CTRL_elbow_pole'):
    left, right = j['bones'][stem+'.L'], j['bones'][stem+'.R']
    measurements[stem] = {
        'left_rest_to_evaluated_rotation_degrees': angle(left['rest_matrix'], left['evaluated_matrix']),
        'right_rest_to_evaluated_rotation_degrees': angle(right['rest_matrix'], right['evaluated_matrix']),
        'right_rest_to_evaluated_axis_angles_XYZ_degrees': axis_angles(right['rest_matrix'], right['evaluated_matrix']),
        'right_vs_X_mirrored_left_rest_rotation_degrees': angle(mirror(left['rest_matrix']), right['rest_matrix']),
        'right_vs_X_mirrored_left_rest_max_matrix_difference': maxdiff(mirror(left['rest_matrix']), right['rest_matrix']),
        'right_vs_X_mirrored_left_evaluated_rotation_degrees': angle(mirror(left['evaluated_matrix']), right['evaluated_matrix']),
        'right_rotation_quaternion': j['raw'][stem+'.R']['rotation_quaternion'],
        'right_constraints': [compact_constraint(c) for c in right['constraints']],
    }

limbs = {}
for side in ('L','R'):
    arm = j['bones']['upper_arm.'+side]
    lower = j['bones']['forearm.'+side]
    hand = j['bones']['hand.'+side]
    target = j['bones']['CTRL_hand_IK.'+side]
    pole = j['bones']['CTRL_elbow_pole.'+side]
    start, joint, end = map(origin, (arm['evaluated_matrix'], lower['evaluated_matrix'], hand['evaluated_matrix']))
    axis = norm(sub(end,start))
    radial = sub(joint,start)
    radial = sub(radial, [dot(radial,axis)*x for x in axis])
    pr = sub(origin(pole['evaluated_matrix']),start)
    pr = sub(pr, [dot(pr,axis)*x for x in axis])
    limbs[side] = {
        'ik_fk': j['raw']['CTRL_hand_IK.'+side]['properties'].get('ik_fk'),
        'ik_constraint': [compact_constraint(c) for c in lower['constraints'] if c['type']=='IK'],
        'joint_radial_distance': length(radial),
        'joint_radial_over_endpoint_length': length(radial)/length(sub(end,start)),
        'joint_radial_dot_pole_radial_normalized': dot(norm(radial),norm(pr)),
        'hand_origin_to_target_origin_distance': length(sub(end, origin(target['evaluated_matrix']))),
        'target_location': j['raw']['CTRL_hand_IK.'+side]['location'],
        'target_quaternion': j['raw']['CTRL_hand_IK.'+side]['rotation_quaternion'],
        'pole_location': j['raw']['CTRL_elbow_pole.'+side]['location'],
    }

rest_events = json.loads(j['rig_properties']['character_designer_body_rest_resync_v1'])['events']
event_summary = []
for e in rest_events:
    record = {k:e.get(k) for k in ('accepted_utc','schema','changed','pose_assets_retargeted','body_calibration_reconfirmed')}
    for stem in ('prior_direct_entries', 'accepted_direct_entries'):
        record[stem+'_arm_rolls'] = {entry['side']:{n: b['roll'] for n,b in entry['applied'].items()}
                                     for entry in e.get(stem,{}).values() if entry['kind']=='ARM'}
    record['accepted_native_rest_matches_current'] = {n:maxdiff(v['matrix'],j['bones'][n]['rest_matrix'])
                                                     for n,v in e.get('accepted_native_rest',{}).items()}
    event_summary.append(record)

proof = {
    'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'analysis': 'JSON-only arithmetic; no Blender process, GUI, source edits, or artist/model writes.',
    'method': 'Rotation measured after Gram-Schmidt orthonormalization of matrix columns; X reflection uses F*M*F. This symmetry convention is diagnostic, not a requirement that every opposite bone use identical local axes.',
    'runtime_version': j['runtime_version'], 'blender_version':j['blender_version'],
    'mode':j['mode'], 'frame':j['frame'], 'active_bone':j['active_bone'], 'selected':j['selected'],
    'auto_key':j['auto_key'], 'assigned_action':j['assigned_action'],
    'right_finger_count':len(fingers),
    'right_finger_constraints':{n:j['bones'][n]['constraints'] for n in fingers},
    'pose_baseline_present':'character_designer_pose_rest_v1' in j['rig_properties'],
    'original_session_keys':[k for k in j['rig_properties'] if 'original' in k],
    'measurements':measurements, 'limb_geometry':limbs, 'rest_history':event_summary,
    'findings':[
        'All 15 right finger destinations have no constraints. Legacy native mirror routing therefore needs no IK/FK matching or Rest baseline.',
        'Both hands are in IK. Right upper-arm raw quaternion is identity while evaluated orientation differs from current Rest by approximately 180 degrees, with longitudinal Y direction nearly retained.',
        'The active forearm.R IK has a two-bone chain, so it affects upper_arm.R even though upper_arm.R has no constraints itself.',
        'Current upper-arm Rest exactly matches the previously accepted Rest in recorded 2026-10-03 UTC resync history. That event changed right upper-arm roll by approximately 180 degrees and marked calibration reconfirmation false.',
    ],
    'limits':[
        'This is a single post-reset snapshot. It cannot establish whether Shift-double-click created, revealed, or had no effect on the upper-arm twist.',
        'A stale Pole Angle after accepted Rest edits is supported as a diagnostic candidate but is not proven until an isolated solve is compared.',
        'No conclusions about finger topology or weights are established by these bone matrix measurements.',
    ],
}
output = ROOT/'readonly_rig_review.json'
output.write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(output), 'measurements':measurements, 'limb_geometry':limbs,
                  'rest_history':event_summary},ensure_ascii=False,indent=2))
