"""Read current_diagnostic.json; write a bounded local middle-finger comparison.

No Blender process, scene, source, mesh, weights or bone writes are involved.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'current_diagnostic.json'
source_bytes = SOURCE.read_bytes()
data = json.loads(source_bytes)
mesh = data['meshes'][0]
vertices = {v['index']: v for v in mesh['vertices']}
points = {i: v['co'] for i, v in vertices.items()}
points.update({int(i): co for i, co in mesh['support_positions'].items()})


def reflect(point):
    return [-point[0], point[1], point[2]]


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def flip(name):
    suffixes = {'.L': '.R', '.R': '.L', '.l': '.r', '.r': '.l'}
    return name[:-2] + suffixes[name[-2:]] if name[-2:] in suffixes else name


def canonical_cycle(ids):
    return min(tuple(ids[k:] + ids[:k]) for k in range(len(ids)))


left = {i: co for i, co in points.items() if co[0] > 0}
right = {i: co for i, co in points.items() if co[0] < 0}
pairs = {}
coordinate_errors = []
for index, co in left.items():
    matches = sorted((distance(reflect(co), target), j) for j, target in right.items())
    assert matches[0][0] < 1e-7 and matches[1][0] > 1e-7, (index, matches[:2])
    pairs[index] = matches[0][1]
    coordinate_errors.append(matches[0][0])
assert len(pairs) == len(right) == len(set(pairs.values()))
core_pairs = {i: j for i, j in pairs.items() if i in vertices and j in vertices}
assert len(core_pairs) * 2 == len(vertices)

existing_deform = {n for n, bone in data['bones'].items() if bone['bone_rna']['use_deform']}
deform_errors = []
all_group_errors = []
unbound_group_names = set()
for i, j in core_pairs.items():
    a = {flip(n): weight for n, weight in vertices[i]['weights'].items()}
    b = vertices[j]['weights']
    for name in set(a) | set(b):
        error = abs(a.get(name, 0) - b.get(name, 0))
        all_group_errors.append(error)
        if name in existing_deform:
            deform_errors.append(error)
        elif error > 1e-6 and name not in data['bones']:
            unbound_group_names.add(name)
zero_deform = [i for i, v in vertices.items() if sum(
    w for n, w in v['weights'].items() if n in existing_deform) < 1e-8]
effective_subsets = {}
for side in ('L', 'R'):
    middle_names = {f'f_middle.{i:02d}.{side}' for i in (1, 2, 3)}
    distal_names = {f'f_middle.{i:02d}.{side}' for i in (2, 3)}
    middle_only, distal_only, outside_middle = [], [], {}
    for index, vertex in vertices.items():
        names = {n for n, w in vertex['weights'].items() if n in existing_deform and w > 1e-8}
        if not names & middle_names:
            continue
        if names <= middle_names:
            middle_only.append(index)
        if names <= distal_names:
            distal_only.append(index)
        for name in names - middle_names:
            outside_middle[name] = outside_middle.get(name, 0) + 1
    effective_subsets[side] = {
        'middle01_02_03_only_vertices': middle_only,
        'middle02_03_only_vertices': distal_only,
        'other_effective_deform_names_counts': outside_middle,
    }

left_faces = [f for f in mesh['faces'] if all(points[i][0] > 0 for i in f['vertices'])]
right_faces = [f for f in mesh['faces'] if all(points[i][0] < 0 for i in f['vertices'])]
right_cycles = {canonical_cycle(f['vertices']) for f in right_faces}
unmatched_faces = [f['index'] for f in left_faces if canonical_cycle(
    list(reversed([pairs[i] for i in f['vertices']]))) not in right_cycles]
assert len(left_faces) == len(right_faces) and not unmatched_faces

key_comparisons = []
for key in mesh['shape_keys']:
    coords = key['coordinates']
    key_comparisons.append({
        'name': key['name'], 'value': key['value'], 'mute': key['mute'],
        'relative_key': key['relative_key'], 'vertex_group': key['vertex_group'],
        'max_local_reflection_error': max(distance(reflect(coords[str(i)]), coords[str(j)])
                                          for i, j in core_pairs.items()),
        'max_basis_delta': max(distance(coords[str(i)], vertices[i]['co']) for i in vertices),
    })

rig_matrix = data['rig_matrix_world']
mesh_matrix = mesh['matrix_world']
assert all(abs(mesh_matrix[i][j]) < 1e-7 for i in range(3) for j in range(3) if i != j)


def rig_to_mesh(point):
    return [(sum(rig_matrix[row][c] * point[c] for c in range(3))
             + rig_matrix[row][3] - mesh_matrix[row][3]) / mesh_matrix[row][row]
            for row in range(3)]


def world_displacement_length(a, b):
    delta = [a[i] - b[i] for i in range(3)]
    return math.sqrt(sum(sum(rig_matrix[row][col] * delta[col] for col in range(3)) ** 2
                         for row in range(3)))


bone_comparisons = []
for ordinal in (1, 2, 3):
    name = f'f_middle.{ordinal:02d}'
    a, b = data['bones'][name + '.L'], data['bones'][name + '.R']
    axis_angles = []
    for column in range(3):
        expected = reflect([a['rest_matrix'][row][column] for row in range(3)])
        if column == 0:
            expected = [-v for v in expected]  # axial Local X bend convention
        actual = [b['rest_matrix'][row][column] for row in range(3)]
        cosine = sum(x*y for x, y in zip(expected, actual)) / math.sqrt(
            sum(x*x for x in expected) * sum(x*x for x in actual))
        axis_angles.append(math.degrees(math.acos(max(-1, min(1, cosine)))))
    left_length, right_length = a['bone_rna']['length'], b['bone_rna']['length']
    bone_comparisons.append({
        'bone': name, 'left_parent': a['parent'], 'right_parent': b['parent'],
        'head_reflection_error_rig_units': distance(reflect(a['head']), b['head']),
        'head_reflection_error_world_units': world_displacement_length(reflect(a['head']), b['head']),
        'tail_reflection_error_rig_units': distance(reflect(a['tail']), b['tail']),
        'left_length_rig_units': left_length, 'right_length_rig_units': right_length,
        'right_over_left_length': right_length / left_length,
        'axis_reflection_angles_degrees_xyz': axis_angles,
        'left_segments': a['bone_rna']['bbone_segments'],
        'right_segments': b['bone_rna']['bbone_segments'],
        'left_basis_identity_max_error': max(abs(v - (1 if row == col else 0))
            for row, values in enumerate(a['basis']) for col, v in enumerate(values)),
        'right_basis_identity_max_error': max(abs(v - (1 if row == col else 0))
            for row, values in enumerate(b['basis']) for col, v in enumerate(values)),
        'left_constraints': a['constraints'], 'right_constraints': b['constraints'],
    })

transition_comparisons = {}
for side in ('L', 'R'):
    root = rig_to_mesh(data['bones']['f_middle.01.' + side]['head'])
    tip = rig_to_mesh(data['bones']['f_middle.03.' + side]['tail'])
    length = distance(root, tip)
    axis = [(tip[i] - root[i]) / length for i in range(3)]
    project = lambda point: sum((point[i] - root[i]) * axis[i] for i in range(3)) / length
    distal_pivot = project(rig_to_mesh(data['bones']['f_middle.03.' + side]['head']))
    rows = []
    for index, vertex in vertices.items():
        w2 = vertex['weights'].get('f_middle.02.' + side, 0)
        w3 = vertex['weights'].get('f_middle.03.' + side, 0)
        if w2 > 0 and w3 > 0:
            rows.append({'index': index, 'root_tip_fraction': project(vertex['co']),
                         'middle02_weight': w2, 'middle03_weight': w3,
                         'middle03_pair_fraction': w3 / (w2 + w3)})
    rows.sort(key=lambda row: row['root_tip_fraction'])
    transition_comparisons[side] = {
        'distal_pivot_root_tip_fraction': distal_pivot,
        'mixed02_03_vertices': rows,
        'distal_majority_points_before_distal_pivot': [row['index'] for row in rows
            if row['middle03_pair_fraction'] > 0.8 and row['root_tip_fraction'] < distal_pivot],
    }

report = {
    'source': str(SOURCE), 'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
    'analysis': 'read-only JSON; no Blender process or scene mutation',
    'runtime_version': data['runtime_version'], 'blender_version': data['blender_version'],
    'scope': '168 current middle-influenced vertices and 44 adjacent-face support vertices only',
    'mirror_plane': 'mesh local X=0; current-coordinate unique reflected pairs, tolerance 1e-7',
    'paired_coordinates': len(pairs), 'core_pairs': len(core_pairs),
    'max_coordinate_reflection_error': max(coordinate_errors),
    'current_vertex_pairs': [[i, j] for i, j in sorted(pairs.items())],
    'left_adjacent_face_count': len(left_faces), 'right_adjacent_face_count': len(right_faces),
    'topology_reflected_reversed_winding_match': not unmatched_faces,
    'max_existing_deform_weight_reflection_error': max(deform_errors),
    'zero_existing_deform_weight_vertices': zero_deform,
    'effective_weight_subsets': effective_subsets,
    'max_all_group_name_flipped_error': max(all_group_errors),
    'mismatching_names_without_current_bones': sorted(unbound_group_names),
    'shape_keys': key_comparisons, 'bones': bone_comparisons,
    'distal_weight_transition': transition_comparisons,
    'modifiers': mesh['modifiers'],
    'observed': 'local geometry, face connectivity and effective deform weights are exactly mirrored; middle Rest joints and axes differ',
    'inference': 'right distal pivot lies beyond the same symmetric weight transition, so rotation can pull vertices behind its pivot; isolated deformation experiment is required for causal confirmation',
    'limits': 'no evaluated bent geometry, corner normals or unit_settings in source; no whole-mesh symmetry claim; no artist repairs authorized by this report',
}
assert SOURCE.read_bytes() == source_bytes
target = ROOT / 'current_middle_readonly_review.json'
target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('CURRENT_MIDDLE_JSON_REVIEW_COMPLETE', json.dumps({
    'report': str(target), 'paired_coordinates': len(pairs), 'core_pairs': len(core_pairs),
    'deform_weight_error': max(deform_errors),
    'right_distal_pivot': transition_comparisons['R']['distal_pivot_root_tip_fraction'],
    'right_distal_majority_points_before_pivot': transition_comparisons['R']['distal_majority_points_before_distal_pivot'],
}))
