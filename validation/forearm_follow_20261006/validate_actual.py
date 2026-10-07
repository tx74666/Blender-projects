"""Isolated Blender 5.2 Cosha validation; never opens or saves artist X.blend.

Run only with --background --factory-startup --python-exit-code 1 --python
this_file.py. Arguments after --: --snapshot, --snapshot-sha256, --addons,
--output-dir. Failed guards write actual_result.json and preserve tracebacks.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import traceback

import bpy
from mathutils import Quaternion, Vector

HERE = Path(__file__).resolve().parent
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
DEFAULT_SHA = '070562F905ECBD8111E2E622213F05738B68B12186D5C16BD1C62226581DF5E0'
TOL = 3.e-6


def digest(value):
    return hashlib.sha256(repr(value).encode('utf-8')).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def floats(collection, field, width=3):
    values = array('f', [0.0]) * (len(collection) * width)
    collection.foreach_get(field, values)
    return values


def coordinates(key):
    return floats(key.data, 'co')


def matrix_values(matrix):
    return tuple(float(v) for row in matrix for v in row)


def color(value):
    return (value.palette, tuple(value.custom.normal), tuple(value.custom.select),
            tuple(value.custom.active))


def rna_properties(value):
    """Stable constraint/modifier scalar, array and ID references, not pointers."""
    result = {}
    for prop in value.bl_rna.properties:
        name = prop.identifier
        if prop.is_readonly or name in {'rna_type', 'type', 'name', 'is_valid', 'error_location', 'error_rotation'}:
            continue
        try:
            item = getattr(value, name)
            if isinstance(item, (str, bool, int, float)) or item is None:
                result[name] = item
            elif prop.type == 'POINTER':
                result[name] = (type(item).__name__, getattr(item, 'name', None))
            elif prop.is_array:
                result[name] = tuple(item)
        except (AttributeError, TypeError, RuntimeError):
            continue
    return result


def pose_state(arm):
    return {p.name: (p.rotation_mode, tuple(p.location), tuple(p.rotation_euler),
                     tuple(p.rotation_quaternion), tuple(p.rotation_axis_angle), tuple(p.scale))
            for p in arm.pose.bones}


def restore_pose(arm, saved):
    for name, values in saved.items():
        p = arm.pose.bones[name]
        p.rotation_mode = values[0]
        p.location, p.rotation_euler, p.rotation_quaternion = values[1:4]
        p.rotation_axis_angle, p.scale = values[4:6]


def assert_pose(arm, saved):
    current = pose_state(arm)
    assert set(current) == set(saved), 'Pose bone inventory changed'
    for name, before in saved.items():
        after = current[name]
        assert before[0] == after[0], f'{name}: rotation mode changed'
        assert max(abs(a-b) for x, y in zip(before[1:], after[1:])
                   for a, b in zip(x, y)) < TOL, f'{name}: pose channels changed'


def selection_state():
    context = bpy.context
    active = context.view_layer.objects.active
    return {'active': active.name if active else None,
            'mode': active.mode if active else 'OBJECT',
            'objects': {o.name: bool(o.select_get()) for o in context.view_layer.objects},
            'bones': {o.name: {'active': o.data.bones.active.name if o.data.bones.active else None,
                             'selected': {p.name: bool(p.select) for p in o.pose.bones}}
                      for o in context.view_layer.objects if o.type == 'ARMATURE'}}


def object_mode():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


def restore_selection(saved):
    object_mode()
    for name, selected in saved['objects'].items():
        bpy.context.view_layer.objects[name].select_set(selected)
    for name, data in saved['bones'].items():
        arm = bpy.data.objects[name]
        for bone_name, selected in data['selected'].items():
            arm.pose.bones[bone_name].select = selected
        arm.data.bones.active = arm.data.bones.get(data['active']) if data['active'] else None
    bpy.context.view_layer.objects.active = bpy.data.objects.get(saved['active'])
    if saved['active'] and saved['mode'] != 'OBJECT':
        bpy.ops.object.mode_set(mode=saved['mode'])


def protected_state(original_keys):
    """Hash original meshes, weights, UVs, keys, bones, displays and Actions."""
    state = {'meshes': {}, 'armatures': {}, 'actions': {}}
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            keys = mesh.shape_keys
            state['meshes'][obj.name] = {
                'data': mesh.name,
                'geometry': digest(floats(mesh.vertices, 'co').tobytes()),
                'topology': digest((tuple(tuple(e.vertices) for e in mesh.edges),
                                    tuple(tuple(p.vertices) for p in mesh.polygons))),
                'uv': digest([(layer.name, floats(layer.data, 'uv', 2).tobytes())
                              for layer in mesh.uv_layers]),
                'weights': digest((tuple(g.name for g in obj.vertex_groups),
                                   tuple(tuple((g.group, g.weight) for g in v.groups)
                                         for v in mesh.vertices))),
                'modifiers': digest([(m.name, m.type, rna_properties(m)) for m in obj.modifiers]),
                'original_keys': {name: digest((coordinates(keys.key_blocks[name]).tobytes(),
                                      keys.key_blocks[name].value, keys.key_blocks[name].mute,
                                      keys.key_blocks[name].relative_key.name,
                                      keys.key_blocks[name].vertex_group,
                                      keys.key_blocks[name].slider_min, keys.key_blocks[name].slider_max))
                                  for name in original_keys.get(obj.name, ())},
            }
        elif obj.type == 'ARMATURE':
            state['armatures'][obj.name] = digest([
                (b.name, b.parent.name if b.parent else None, b.use_connect, b.use_deform,
                 matrix_values(b.matrix_local), color(b.color), color(obj.pose.bones[b.name].color),
                 tuple(c.name for c in b.collections),
                 obj.pose.bones[b.name].custom_shape.name if obj.pose.bones[b.name].custom_shape else None,
                 tuple(obj.pose.bones[b.name].custom_shape_scale_xyz),
                 tuple(obj.pose.bones[b.name].custom_shape_translation),
                 tuple(obj.pose.bones[b.name].custom_shape_rotation_euler),
                 [(c.name, c.type, rna_properties(c)) for c in obj.pose.bones[b.name].constraints])
                for b in obj.data.bones])
    from character_designer import limb_ik
    for action in bpy.data.actions:
        state['actions'][action.name] = digest((
            [(s.identifier, s.target_id_type) for s in action.slots],
            [(f.data_path, f.array_index, f.extrapolation,
              [(tuple(k.co), tuple(k.handle_left), tuple(k.handle_right), k.interpolation,
                k.handle_left_type, k.handle_right_type, k.easing) for k in f.keyframe_points],
              tuple(tuple(p.co) for p in f.sampled_points),
              [(m.type, rna_properties(m)) for m in f.modifiers])
             for f in limb_ik._fcurves_for_action(action)]))
    return state


def check_protection(expected, original_keys):
    actual = protected_state(original_keys)
    differences = []
    for category in expected:
        for name in set(expected[category]) | set(actual[category]):
            old, new = expected[category].get(name), actual[category].get(name)
            if old != new:
                if isinstance(old, dict) and isinstance(new, dict):
                    differences.extend(f'{category}/{name}/{part}' for part in set(old) | set(new)
                                       if old.get(part) != new.get(part))
                else:
                    differences.append(f'{category}/{name}')
    assert not differences, 'Protected data changed: ' + ', '.join(differences)


def rings_summary(rings):
    return [{'position': r['position'], 'count': len(r['vertices']),
             'vertices': list(r['vertices'])} for r in rings]


def refresh(runtime):
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    runtime.update_runtime(bpy.context.scene, graph)
    bpy.context.view_layer.update()
    assert not runtime._ERRORS, repr(dict(runtime._ERRORS))
    return graph


def twist_measure(arm, record, graph):
    from character_designer.forearm_twist_math import twist_angle
    evaluated = arm.evaluated_get(graph)
    transforms = {n: evaluated.pose.bones[n].matrix @ arm.data.bones[n].matrix_local.inverted()
                  for n in record['chain']}
    upper, lower, hand = record['chain']
    axis = (arm.data.bones[lower].tail_local - arm.data.bones[lower].head_local).normalized()
    return [math.degrees(twist_angle(transforms[upper], transforms[lower], axis)),
            math.degrees(twist_angle(transforms[lower], transforms[hand], axis))]


def skinned_ring_state(body, arm, record, runtime, graph):
    """Evaluate the unchanged Armature LBS on captured base-ring vertices.

    This deliberately precedes Subdivision. Pure lower/hand influence vertices
    can prove a rigid common-alpha rotation; upper-arm blend vertices are
    reported separately, without claiming that existing elbow weights are rigid.
    """
    from character_designer.forearm_twist_math import blended_matrix
    indices = sorted({i for r in record['rings'] for i in r['vertices']})
    owned = {r['key'] for r in runtime._records(body).values()}
    base = runtime._input_mix(body, indices, owned, graph)
    weights = runtime._weights(body, arm, indices)
    evaluated_arm = arm.evaluated_get(graph)
    to_arm = evaluated_arm.matrix_world.inverted() @ body.evaluated_get(graph).matrix_world
    transforms = {n: evaluated_arm.pose.bones[n].matrix @ arm.data.bones[n].matrix_local.inverted()
                  for n in {name for item in weights.values() for name in item}}
    basis = body.data.shape_keys.reference_key
    key = body.data.shape_keys.key_blocks[record['key']]
    points = {i: blended_matrix(transforms, weights[i]) @ (to_arm @
                  (base[i] + (key.data[i].co - basis.data[i].co) * (0.0 if key.mute else key.value)))
              for i in indices}
    lower, hand = record['chain'][1:]
    rigid_indices = {i for i in indices
                     if weights[i].get(lower, 0.) + weights[i].get(hand, 0.) > 1. - 1.e-6}
    return {'points': points, 'rigid_indices': rigid_indices,
            'lower_matrix': evaluated_arm.pose.bones[lower].matrix.copy()}


def common_alpha_diagnostic(before, after, record, commanded_degrees):
    """Prove alpha is a common rigid rotation, rather than an axial profile."""
    rigid_transform = after['lower_matrix'] @ before['lower_matrix'].inverted()
    eligible = before['rigid_indices'] & after['rigid_indices']
    assert eligible, 'No fully lower/hand weighted ring vertices for common-alpha evidence'
    max_rigid_error = max((after['points'][i] - rigid_transform @ before['points'][i]).length
                          for i in eligible)
    axis = (before['lower_matrix'].to_3x3() @ Vector((0, 1, 0))).normalized()
    pivot = before['lower_matrix'].translation

    def angle(index):
        a, b = before['points'][index] - pivot, after['points'][index] - pivot
        a, b = a - axis * a.dot(axis), b - axis * b.dot(axis)
        return math.atan2(axis.dot(a.cross(b)), a.dot(b))

    def summarize(indices):
        angles = [angle(i) for i in indices]
        if not angles:
            return None
        mean = math.atan2(sum(math.sin(v) for v in angles), sum(math.cos(v) for v in angles))
        return {'mean_degrees': math.degrees(mean),
                'angular_spread_degrees': math.degrees(max(abs(math.remainder(v-mean, math.tau)) for v in angles))}

    rings = []
    for ring in record['rings']:
        selected = [i for i in ring['vertices'] if i in eligible]
        rings.append({'position': ring['position'], 'vertices': len(ring['vertices']),
                      'fully_lower_hand_vertices': len(selected),
                      'rigid_only_angle': summarize(selected),
                      'all_vertices_angle_including_original_elbow_blends': summarize(ring['vertices'])})
    first_strip = None
    if rings[0]['rigid_only_angle'] and rings[1]['rigid_only_angle']:
        first_strip = math.degrees(math.remainder(math.radians(
            rings[1]['rigid_only_angle']['mean_degrees'] - rings[0]['rigid_only_angle']['mean_degrees']), math.tau))
    result = {'commanded_common_alpha_degrees': commanded_degrees,
              'rigid_vertex_count': len(eligible), 'rigid_max_position_error': max_rigid_error,
              'rings': rings, 'first_strip_extra_twist_degrees': first_strip,
              'expected_first_strip_extra_twist_degrees': 0.0,
              'violations': [],
              'limitation': 'Rigid assertions use vertices fully weighted to lower/hand; existing upper-arm elbow blends remain unchanged.'}
    if max_rigid_error >= 1.e-4:
        result['violations'].append(f'Common alpha was redistributed: rigid error {max_rigid_error}')
    for ring in rings:
        measured = ring['rigid_only_angle']
        if measured:
            difference = math.degrees(math.remainder(math.radians(measured['mean_degrees'] - commanded_degrees), math.tau))
            if abs(difference) >= .03 or measured['angular_spread_degrees'] >= .03:
                result['violations'].append(f'Ring at {ring["position"]}: common alpha was profiled')
    if first_strip is not None:
        if abs(first_strip) >= .03:
            result['violations'].append('New reverse twist introduced in the first strip')
    return result


def reference_sample(record, position):
    """Independent saved-ratio interpolation and support mask; no runtime sampler."""
    rings = record['rings']
    first = record.get('range_start', 0)
    last = record.get('range_end', len(rings) - 1)
    continuous = record.get('distribution') == 'WRIST_CONTINUOUS'
    chosen = rings[first:last + 1] if continuous else rings
    knots = [(float(r['position']), float(r['ratio'])) for r in chosen]
    if 'range_start' not in record:
        knots = [(0., 0.)] + [(p, r) for p, r in knots if 1.e-6 < p < 1. - 1.e-6] + [(1., 1.)]

    def smooth(amount):
        amount = max(0., min(1., amount))
        return amount * amount * (3. - 2. * amount)

    ratio = knots[0][1] if position <= knots[0][0] else knots[-1][1]
    for left, right in zip(knots, knots[1:]):
        if position == right[0]:
            ratio = right[1]
            break
        if left[0] < position < right[0]:
            blend = smooth((position - left[0]) / (right[0] - left[0]))
            ratio = left[1] + blend * (right[1] - left[1])
            break
    start, end = rings[first]['position'], rings[last]['position']
    influence = 1.
    if continuous:
        influence = 0. if position < start else 1.
    elif 'range_start' in record:
        if position <= start or position >= end:
            influence = 0.
        elif record.get('transition', .1):
            width = record.get('transition', .1) * (end - start)
            influence = smooth(min((position - start) / width, (end - position) / width))
    return ratio, influence


def post_armature_diagnostic(body, arm, record, runtime, graph, beta_degrees):
    """Compare actual correction with an independent articulated beta-only LBS.

    The expected expression rotates lower inputs by r*beta, hand inputs by
    (r-1)*beta, and retains every other bone contribution. Common forearm alpha
    stays in the actual deformation matrices. This uses neither desired_vertex
    nor corrected_vertex; profile interpolation is independently sampled above.
    All saved support vertices, including the irregular corridor, are checked.
    """
    records = runtime._records(body)
    indices = record['vertices']
    owned = {r['key'] for r in records.values()}
    source = runtime._input_mix(body, indices, owned, graph)
    weights = runtime._weights(body, arm, indices)
    evaluated_arm = arm.evaluated_get(graph)
    to_arm = evaluated_arm.matrix_world.inverted() @ body.evaluated_get(graph).matrix_world
    transforms = {name: evaluated_arm.pose.bones[name].matrix @ arm.data.bones[name].matrix_local.inverted()
                  for name in {n for influence in weights.values() for n in influence}}
    lower, hand = record['chain'][1:]
    axis = (arm.data.bones[lower].tail_local - arm.data.bones[lower].head_local).normalized()
    pivot = arm.data.bones[hand].head_local
    keys = body.data.shape_keys
    basis = keys.reference_key
    beta = math.radians(beta_degrees)

    def linear_skin(point, influences):
        if not influences:
            return point.copy()
        result = Vector((0., 0., 0.))
        for name, weight in influences.items():
            result += weight * (transforms[name] @ point)
        return result

    errors, expected_changes, actual_changes = [], [], []
    worst_vertex, worst_error = None, -1.
    for index, position in zip(indices, record['positions']):
        point = to_arm @ source[index]
        uncorrected = linear_skin(point, weights[index])
        ratio, influence = reference_sample(record, position)
        desired = Vector((0., 0., 0.)) if weights[index] else point.copy()
        for name, weight in weights[index].items():
            angle = ratio * beta if name == lower else (ratio - 1.) * beta if name == hand else 0.
            rotated = pivot + Quaternion(axis, angle) @ (point - pivot)
            desired += weight * (transforms[name] @ rotated)
        expected = uncorrected.lerp(desired, influence)
        actual_input = source[index].copy()
        # Include every owned key to detect a counterpart accidentally leaking
        # into this sleeve. Source mixing already excludes those owned outputs.
        for name in owned:
            key = keys.key_blocks[name]
            if not key.mute:
                actual_input += (key.data[index].co - basis.data[index].co) * key.value
        actual = linear_skin(to_arm @ actual_input, weights[index])
        error = (actual - expected).length
        if error > worst_error:
            worst_vertex, worst_error = index, error
        errors.append(error)
        expected_changes.append((expected - uncorrected).length)
        actual_changes.append((actual - uncorrected).length)
    maximum = max(errors, default=0.)
    expected_max = max(expected_changes, default=0.)
    actual_max = max(actual_changes, default=0.)
    tolerance = 1.e-4
    assert indices, 'No saved support vertices for post-Armature evidence'
    assert maximum < tolerance, f'Beta loop correction differs from independent LBS reference: {maximum} at vertex {worst_vertex}'
    if abs(beta_degrees) > .1:
        assert expected_max > 1.e-6, 'Nonzero beta has no expected loop correction; this support cannot prove wrist response'
        assert actual_max > 1.e-6, 'Nonzero beta did not change post-Armature loop geometry'
    return {'coordinate_space': 'Armature local, immediately after Armature LBS',
            'vertex_count': len(indices), 'beta_degrees': beta_degrees,
            'maximum_position_error': maximum, 'worst_vertex': worst_vertex,
            'position_tolerance': tolerance, 'expected_max_correction': expected_max,
            'actual_max_correction': actual_max,
            'reference': 'Independent saved ratio/mask, lower r*beta, hand (r-1)*beta, other weights unchanged.'}


def validate_pose(body, arm, side, name, lower_degrees, hand_degrees, bend_axis,
                  bend_degrees, original_pose, runtime, records):
    restore_pose(arm, original_pose)
    graph = refresh(runtime)
    other = 'R' if side == 'L' else 'L'
    other_key = body.data.shape_keys.key_blocks[records[other]['key']]
    opposite_before = coordinates(other_key)
    opposite_matrices = {n: matrix_values(arm.evaluated_get(graph).pose.bones[n].matrix)
                         for n in records[other]['chain']}
    lower_name, hand_name = records[side]['chain'][1:]
    baseline_twist = twist_measure(arm, records[side], graph)
    source_before = {n: matrix_values(arm.evaluated_get(graph).pose.bones[n].matrix)
                     for n in (lower_name, hand_name)}
    alpha_only = bool(lower_degrees and not hand_degrees and not bend_degrees)
    ring_before = skinned_ring_state(body, arm, records[side], runtime, graph) if alpha_only else None
    lower, hand = arm.pose.bones[lower_name], arm.pose.bones[hand_name]
    lower_original, hand_original = lower.matrix_basis.to_quaternion(), hand.matrix_basis.to_quaternion()
    axis = (lower.bone.tail_local - lower.bone.head_local).normalized()
    hand_axis = (hand.bone.matrix_local.to_3x3().inverted() @ axis).normalized()
    lower.rotation_mode = hand.rotation_mode = 'QUATERNION'
    lower.rotation_quaternion = lower_original @ Quaternion((0, 1, 0), math.radians(lower_degrees))
    hand.rotation_quaternion = hand_original @ Quaternion(hand_axis, math.radians(hand_degrees))
    if bend_degrees:
        hand.rotation_quaternion @= Quaternion(Vector(bend_axis), math.radians(bend_degrees))
    commanded_pose = pose_state(arm)
    graph = refresh(runtime)
    assert_pose(arm, commanded_pose)
    first = {s: coordinates(body.data.shape_keys.key_blocks[r['key']]) for s, r in records.items()}
    assert all(math.isfinite(v) for values in first.values() for v in values), 'Non-finite corrective coordinates'
    for p in arm.evaluated_get(graph).pose.bones:
        assert all(math.isfinite(v) for v in matrix_values(p.matrix)), f'{p.name}: non-finite pose matrix'
    basis = coordinates(body.data.shape_keys.reference_key)
    support = set(records[side]['vertices'])
    outsider_delta = max((abs(first[side][i] - basis[i]) for i in range(len(basis))
                          if i // 3 not in support), default=0.)
    assert outsider_delta < TOL, 'Correction escaped record.vertices support'
    opposite_delta = max((abs(a-b) for a, b in zip(opposite_before, first[other])), default=0.)
    assert opposite_delta < TOL, 'Opposite corrective key changed'
    for n, before in opposite_matrices.items():
        after = matrix_values(arm.evaluated_get(graph).pose.bones[n].matrix)
        assert max(abs(a-b) for a, b in zip(before, after)) < TOL, f'Opposite pose changed: {n}'
    measured = twist_measure(arm, records[side], graph)
    beta_evidence = post_armature_diagnostic(body, arm, records[side], runtime, graph, measured[1])
    key_max_delta = max(abs(a-b) for a, b in zip(first[side], basis))
    if abs(measured[1]) > .1:
        assert key_max_delta > 1.e-6, 'Nonzero beta corrective key stayed at Basis'
    source_delta = max(abs(a-b) for n in source_before
                       for a, b in zip(source_before[n], matrix_values(arm.evaluated_get(graph).pose.bones[n].matrix)))
    assert source_delta > 1.e-4, 'Test rotation did not reach the evaluated native bones'
    if lower_degrees or hand_degrees:
        assert max(abs(a-b) for a, b in zip(baseline_twist, measured)) > 5., 'Axial input did not produce axial twist'
    alpha_evidence = (common_alpha_diagnostic(ring_before,
                      skinned_ring_state(body, arm, records[side], runtime, graph),
                      records[side], lower_degrees) if alpha_only else None)
    for _ in range(3):
        refresh(runtime)
        assert_pose(arm, commanded_pose)
    repeated = {s: coordinates(body.data.shape_keys.key_blocks[r['key']]) for s, r in records.items()}
    drift = max((abs(a-b) for s in first for a, b in zip(first[s], repeated[s])), default=0.)
    assert drift < TOL, 'Repeated evaluation accumulated a correction'
    return {'side': side, 'case': name, 'input_degrees': [lower_degrees, hand_degrees, bend_degrees],
            'measured_degrees_lower_hand': measured, 'outside_support_max': outsider_delta,
            'baseline_degrees_lower_hand': baseline_twist, 'source_pose_max_change': source_delta,
            'opposite_key_max_change': opposite_delta, 'repeat_max_change': drift,
            'key_max_delta': key_max_delta,
            'commanded_pose_sha256': digest(commanded_pose),
            'commanded_pose_unchanged': True,
            'post_armature_beta_evidence': beta_evidence,
            'common_alpha_rigid_evidence': alpha_evidence,
            'runtime_errors': dict(runtime._ERRORS)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path, default=HERE / 'artist_disk_20261006_185029_821.blend')
    parser.add_argument('--snapshot-sha256', default=DEFAULT_SHA)
    parser.add_argument('--addons', type=Path, default=HERE / 'candidate_source' / 'addons')
    parser.add_argument('--output-dir', type=Path, default=HERE)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output, receipt = args.output_dir / 'calibrated_actual.blend', args.output_dir / 'actual_result.json'
    report = {'status': 'FAILED', 'stage': 'preflight', 'version': bpy.app.version_string,
              'pid': os.getpid(), 'snapshot': str(args.snapshot.resolve()), 'tests': [],
              'topology': {}, 'tracebacks': [], 'saved_output': None}
    rig = runtime = pose = selection = None
    frame = subframe = None
    try:
        assert bpy.app.background and bpy.app.version[:2] == (5, 2), 'Only isolated background Blender 5.2 allowed'
        snapshot = args.snapshot.resolve()
        assert snapshot != ARTIST and snapshot.name.lower() != 'x.blend', 'Artist file is forbidden'
        assert output.resolve() not in {ARTIST, snapshot}, 'Output must be independent'
        assert not output.exists(), 'Existing calibrated output is protected; use a new --output-dir'
        report['snapshot_sha256'] = file_hash(snapshot)
        assert report['snapshot_sha256'].lower() == args.snapshot_sha256.lower(), 'Protected snapshot hash mismatch'
        sys.path.insert(0, str(args.addons.resolve()))
        import character_designer
        from character_designer import forearm_twist as runtime
        from character_designer.forearm_twist_topology import detect_rings, expand_rings
        assert Path(character_designer.__file__).resolve().parent.parent == args.addons.resolve(), 'Wrong addon imported'
        character_designer.register()
        bpy.ops.wm.open_mainfile(filepath=str(snapshot), load_ui=False)
        report['addon_path'] = character_designer.__file__
        report['addon_version'] = list(character_designer.bl_info['version'])
        report['source_sha256'] = {n: file_hash(Path(runtime.__file__).parent / n)
                                 for n in ('forearm_twist.py', 'forearm_twist_math.py', 'unity_forearm.py')}
        body, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
        pose, selection = pose_state(rig), selection_state()
        frame, subframe = bpy.context.scene.frame_current, bpy.context.scene.frame_subframe
        report['original_frame'] = frame
        report['original_selection'] = selection
        report['original_pose_sha256'] = digest(pose)
        assert selection['mode'] in {'OBJECT', 'POSE'}, 'Only saved Object/Pose state is supported'
        assert not runtime._SESSION and runtime.PREVIEW_KEY not in body, 'Snapshot has an unfinished preview; preserved'
        existing = runtime._records(body)
        owned = {r['key'] for r in existing.values()}
        original_keys = {o.name: [k.name for k in o.data.shape_keys.key_blocks
                                  if o is not body or k.name not in owned]
                         for o in bpy.data.objects if o.type == 'MESH' and o.data.shape_keys}
        protected = protected_state(original_keys)
        report['protected_before'] = protected
        report['existing_records'] = existing
        report['stage'] = 'topology_inventory'
        for side in ('L', 'R'):
            resolved_arm, resolved = runtime._resolve_rig(body, side)
            assert resolved_arm is rig
            detected = detect_rings(body, rig, resolved['chain'][1], resolved['chain'][2])
            diagnostics, expanded = [], []
            item = report['topology'][side] = {'chain': list(resolved['chain']),
                'target': resolved['target'].name, 'native_source': resolved.get('native_source', False),
                'fk_source': resolved.get('fk_source', False), 'detected': rings_summary(detected)}
            if detected:
                try:
                    expanded = expand_rings(body, rig, resolved['chain'][1], detected[0]['vertices'], diagnostics=diagnostics)
                except Exception:
                    item['expand_traceback'] = traceback.format_exc()
            item.update(expanded=rings_summary(expanded), expand_diagnostics=diagnostics)
        assert all(len(item['detected']) >= 3 and len(item['expanded']) >= 3
                   for item in report['topology'].values()), 'Insufficient genuine closed loops; no ring guessed'
        object_mode()
        for o in bpy.context.selected_objects:
            o.select_set(False)
        body.select_set(True)
        bpy.context.view_layer.objects.active = body
        report['stage'] = 'paired_capture'
        runtime.start_test(bpy.context, body, 'L', symmetry=True, recapture=bool(existing),
                           continuous=True, initial_angle=None)
        runtime.finish_test(bpy.context, confirm=True)
        assert_pose(rig, pose)
        records = runtime._records(body)
        assert set(records) == {'L', 'R'}, 'Both arm calibrations required'
        assert all('twist_mode' not in r and r.get('distribution') == 'WRIST_CONTINUOUS'
                   and r.get('paired') for r in records.values()), 'Capture mode did not propagate to both arms'
        report['rotation_model'] = 'Existing common forearm alpha stays rigid; only relative wrist beta uses the saved loop ratios (alpha + ratio * beta).'
        assert not set(records['L']['vertices']).intersection(records['R']['vertices']), 'Sleeves overlap'
        from character_designer.forearm_twist_symmetry import mirror_ring_pairs
        report['mirror_pairs'] = mirror_ring_pairs(body, rig, records['L'], records['R'])
        report['records'] = records
        check_protection(protected, original_keys)
        report['stage'] = 'pose_cases'
        cases = [('hand_axial_pos', 0, 60, (1, 0, 0), 0),
                 ('hand_axial_neg', 0, -60, (1, 0, 0), 0),
                 ('forearm_localY_pos', 60, 0, (1, 0, 0), 0),
                 ('forearm_localY_neg', -60, 0, (1, 0, 0), 0),
                 ('mixed', 40, -25, (1, 0, 0), 0),
                 ('mixed_bend', 30, 25, (1, 0, 0), 25),
                 ('wrist_bend_X', 0, 0, (1, 0, 0), 30),
                 ('wrist_bend_Z', 0, 0, (0, 0, 1), -30)]
        for side in ('L', 'R'):
            for case in cases:
                report['current_case'] = {'side': side, 'case': case[0]}
                try:
                    row = validate_pose(body, rig, side, *case, pose, runtime, records)
                    report['tests'].append(row)
                    evidence = row['common_alpha_rigid_evidence']
                    assert evidence is None or not evidence['violations'], repr(evidence['violations'])
                finally:
                    restore_pose(rig, pose)
                    refresh(runtime)
                assert_pose(rig, pose)
        check_protection(protected, original_keys)
        restore_selection(selection)
        assert selection_state() == selection, 'Original selection or mode not restored'
        assert bpy.context.scene.frame_current == frame and bpy.context.scene.frame_subframe == subframe
        assert_pose(rig, pose)
        report['protected_after'] = protected_state(original_keys)
        report['pose_restored'] = report['selection_restored'] = report['protected_data_unchanged'] = True
        report['runtime_errors_final'] = dict(runtime._ERRORS)
        assert file_hash(snapshot) == report['snapshot_sha256'], 'Input copy changed'
        report['stage'] = 'save_independent_calibration'
        result = bpy.ops.wm.save_as_mainfile(filepath=str(output), copy=True)
        assert result == {'FINISHED'} and output.exists(), repr(result)
        assert Path(bpy.data.filepath).resolve() == snapshot, 'Opened snapshot identity changed'
        report['saved_output'] = {'path': str(output), 'bytes': output.stat().st_size, 'sha256': file_hash(output)}
        report['status'], report['stage'] = 'PASS', 'complete'
    except BaseException:
        report['tracebacks'].append(traceback.format_exc())
        if runtime is not None and runtime._SESSION:
            try:
                runtime.finish_test(bpy.context, confirm=False)
            except Exception:
                report['tracebacks'].append('PREVIEW CLEANUP\n' + traceback.format_exc())
        if rig is not None and pose is not None:
            try:
                restore_pose(rig, pose)
                if bpy.context.scene.frame_current != frame or bpy.context.scene.frame_subframe != subframe:
                    bpy.context.scene.frame_set(frame, subframe=subframe)
                if selection is not None:
                    restore_selection(selection)
                assert_pose(rig, pose)
                report['failure_pose_restored'] = True
            except Exception:
                report['tracebacks'].append('RESTORE\n' + traceback.format_exc())
        if runtime is not None:
            report['runtime_errors_final'] = dict(runtime._ERRORS)
    finally:
        receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('FOREARM_ACTUAL_RESULT', report['status'], report['stage'], str(receipt), flush=True)
    if report['status'] != 'PASS':
        raise RuntimeError('\n'.join(report['tracebacks']))


if __name__ == '__main__':
    main()
