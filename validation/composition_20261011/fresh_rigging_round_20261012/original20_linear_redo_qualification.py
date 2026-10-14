"""Pure, evidence-bound qualification of the observed Custom20 LINEAR handle-X rewrite.

This does not replace the product Action fingerprint or qualify Source/Body data.
"""
import copy
import hashlib
import json
import math
import struct

POLICY = 'original20.linear-handle-x-observed-f32-transition/1'
LOCATIONS = ((0, 'handle_right'), (1, 'handle_left'), (2, 'handle_right'),
    (3, 'handle_left'), (6, 'handle_right'), (7, 'handle_left'),
    (14, 'handle_right'), (15, 'handle_left'), (30, 'handle_right'), (31, 'handle_left'))
CHANNELS = tuple(('[' + json.dumps('cd_rigging_' + side + '_' + field) + ']', index)
    for side in ('right', 'left') for field, count in
    (('targetPosition', 3), ('targetRotation', 4), ('hintPosition', 3)) for index in range(count))


def require(value, message):
    if not value: raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def float32_bits(value):
    require(type(value) is float and math.isfinite(value), 'Require a finite native float.')
    packed = struct.pack('<f', value)
    require(struct.unpack('<f', packed)[0] == value, 'Require an exactly represented float32.')
    return struct.unpack('<I', packed)[0]


def full_diff(before, after, path=()):
    """Exact ordered structural comparison, including float signed-zero bits."""
    require(type(before) is type(after), 'Payload field type changed: ' + str(path))
    if isinstance(before, dict):
        require(before.keys() == after.keys(), 'Payload fields changed: ' + str(path))
        return [row for key in before for row in full_diff(before[key], after[key], path + (key,))]
    if isinstance(before, list):
        require(len(before) == len(after), 'Payload sequence length changed: ' + str(path))
        return [row for index, (a, b) in enumerate(zip(before, after))
                for row in full_diff(a, b, path + (index,))]
    exact = struct.pack('<d', before) == struct.pack('<d', after) if type(before) is float else before == after
    return [] if exact else [{'path': list(path), 'before': before, 'after': after}]


def domain(payload, expected_times=None):
    require(set(payload) == {'settings', 'slot_type', 'layers'} and payload['slot_type'] == 'OBJECT'
        and len(payload['layers']) == 1 and len(payload['layers'][0]['strips']) == 1,
        'Require the original one-layer, one-strip Object carrier.')
    curves = payload['layers'][0]['strips'][0]['curves']
    require(len(curves) == 20 and tuple((curve['data_path'], curve['array_index']) for curve in curves) == CHANNELS,
        'Require exactly the original ordered twenty scalar channels.')
    times = None
    for curve in curves:
        points = curve['keyframe_points']
        require(len(points) == 59 and not curve['sampled_points'] and not curve['modifiers']
            and curve['mute'] is False and curve['extrapolation'] == 'CONSTANT',
            'Require exactly59 saved keys with no samples/modifiers.')
        actual_times = tuple(point['co'][0] for point in points)
        if times is None: times = actual_times
        require(actual_times == times and (expected_times is None or actual_times == tuple(expected_times)),
            'The authenticated key-time domain changed.')
        for point in points:
            require(point['interpolation'] == 'LINEAR', 'Qualification is only for every segment being LINEAR.')
            for field in ('co', 'handle_left', 'handle_right'):
                require(len(point[field]) == 2, 'Unexpected native key coordinate shape.')
                for value in point[field]: float32_bits(value)
    return curves, times


def transition_rows(changes):
    require(len(changes) == 200, 'Only the complete observed200-field rewrite may differ.')
    expected = {(curve, key, handle) for curve in range(20) for key, handle in LOCATIONS}
    observed, transitions = set(), []
    for row in changes:
        path = row['path']
        require(len(path) == 10 and path[:5] == ['layers', 0, 'strips', 0, 'curves']
            and path[6] == 'keyframe_points' and path[9] == 0, 'A field outside handle-X changed.')
        key = (path[5], path[7], path[8])
        require(key in expected and key not in observed, 'An unproved handle/key position changed.')
        a, b = float32_bits(row['before']), float32_bits(row['after'])
        require(row['before'] > 0 and row['after'] > 0 and abs(a - b) == 1,
            'Only an exactly adjacent positive float32 handle-X may differ.')
        observed.add(key); transitions.append((tuple(path), a, b))
    require(observed == expected, 'The exact observed positions were not preserved.')
    return sorted(transitions)


def masked_payload(payload):
    value = copy.deepcopy(payload)
    curves = value['layers'][0]['strips'][0]['curves']
    for curve in curves:
        for key, handle in LOCATIONS: curve['keyframe_points'][key][handle][0] = None
    return value


def masked_digest(payload):
    return digest(masked_payload(payload))


def qualify_redo(before, after, diagnostic_before, diagnostic_after):
    """Caller authenticates diagnostic file pins; this rechecks all its actual data."""
    _, times = domain(diagnostic_before)
    domain(diagnostic_after, times)
    proven = transition_rows(full_diff(diagnostic_before, diagnostic_after))
    require(masked_digest(diagnostic_before) == masked_digest(diagnostic_after), 'Diagnostic changed another field.')
    domain(before, times); domain(after, times)
    changes = full_diff(before, after)
    if changes:
        require(transition_rows(changes) == proven, 'Handle-X rewrite differs from the exact proven bit transitions.')
    other_before, other_after = masked_digest(before), masked_digest(after)
    require(other_before == other_after, 'A non-qualified payload field changed.')
    return {'policy': POLICY, 'qualified_semantic20_equal': True,
        'whole_payload_exact': not changes, 'difference_count': len(changes),
        'qualification_used': bool(changes), 'all1180_interpolation_LINEAR': True,
        'all_other_payload_fields_exact': True, 'masked_other_payload_sha256': other_before,
        'diagnostic_transition_sha256': digest(proven), 'differences': changes}
