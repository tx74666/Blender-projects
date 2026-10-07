"""Private fixed-input REST FBX semantics; Root alone owns native execution.

Only the frozen parent's reimport geometry/skin checks change. In-process bake,
complete Rest thresholds, author RNA protection and native finally are intact.
Vertex/face/corner order is never remapped; only unique undirected edge numbering
and omitted named zero-weight entries are compared by their FBX meaning.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARENT = HERE/'verify_plain_rest_skin_fbx_component52.py'
PARENT_SHA = '9b93aab9edde5cbf6065e2e8ab9bf81ef27d07a79cd7cb9b792451f466e8564f'
PRIOR_FAILURE = HERE/'actual_plain_rest_skin_fbx_component_52_20261007_202017_345_a43f05222eed4890918d6f73579ab9ab/result/report.json'
PRIOR_FAILURE_SHA = 'd780cf55aef3bb8a30855fa94ec688d44f9c6415ba44a996dbc11200e4125fd3'
DIAGNOSTIC = HERE/'actual_diagnose_plain_rest_skin_fbx_component_52_20261007_205631_502_627e29bb41874a44a60bbcec1607ce6f/result/report.json'
DIAGNOSTIC_SHA = 'abfcda559443708304f097dbea8bf730f41ad1000a7291c82fd3e17346f52854'
MANIFEST_READER = HERE/'source_compatibility52_node_ui.py'
MANIFEST_READER_SHA = '08d36c4e561c808ed40a49e6b094085ef687a8a2e02bf5413c56ea203332507b'
OLD_SKIN_FIELD = 'skin_UV_named_weights_material_indices_loops_exact'
NEW_SKIN_FIELD = 'skin_UV_named_weights_material_indices_corner_edges_semantic_exact'


def need(value, reason):
    if not value:
        raise RuntimeError('PlainRestFBXSemantic52: ' + reason)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def integer(value, upper):
    return type(value) is int and 0 <= value < upper


def geometry_semantics(first, first_skin, second, second_skin):
    count = len(first['points'])
    need(count > 0 and len(second['points']) == count, 'Same-index vertex count differs')
    for native in (first, second):
        need(all(len(p) == 3 and all(math.isfinite(v) for v in p) for p in native['points']),
             'Nonfinite or incomplete same-index coordinates')
        for field, minimum in (('faces', 3), ('triangles', 3)):
            need(all(len(f) >= minimum and (field != 'triangles' or len(f) == 3)
                     and len(set(f)) == len(f) and all(integer(v, count) for v in f)
                     for f in native[field]), 'Invalid/duplicate polygon or triangle vertex')
    faces = [tuple(f) for f in first['faces']]
    triangles = [tuple(f) for f in first['triangles']]
    need(faces and faces == [tuple(f) for f in second['faces']], 'Ordered faces/winding differ')
    need(triangles and triangles == [tuple(f) for f in second['triangles']], 'Ordered triangles differ')
    lookups = []
    for native in (first, second):
        lookup = {}
        for index, edge in enumerate(native['edges']):
            need(len(edge) == 2 and all(integer(v, count) for v in edge) and edge[0] != edge[1],
                 'Invalid/self/bounds edge endpoint')
            pair = tuple(sorted(edge))
            need(pair not in lookup, 'Duplicate undirected edge prevents a unique bijection')
            lookup[pair] = index
        lookups.append(lookup)
    need(lookups[0] and set(lookups[0]) == set(lookups[1]), 'Undirected edge connectivity differs')
    bijection = [lookups[1][tuple(sorted(edge))] for edge in first['edges']]
    need(len(bijection) == len(second['edges']) and set(bijection) == set(range(len(second['edges']))),
         'Edge correspondence is not a full bijection')
    corner_vertices = [v for face in faces for v in face]
    for native, skin in ((first, first_skin), (second, second_skin)):
        loops = skin['loops']
        need(len(loops) == len(corner_vertices)
             and all(len(loop) == 2 and integer(loop[0], count)
                     and integer(loop[1], len(native['edges'])) for loop in loops),
             'Incomplete or out-of-bounds corner/edge indices')
        need([loop[0] for loop in loops] == corner_vertices, 'Ordered corner vertices differ')
        offset = 0
        for face in faces:
            for corner, current in enumerate(face):
                following = face[(corner + 1) % len(face)]
                actual_edge = native['edges'][loops[offset + corner][1]]
                need(tuple(sorted(actual_edge)) == tuple(sorted((current, following))),
                     'Loop edge does not connect its current and next face corners')
            offset += len(face)
    need(all(bijection[a[1]] == b[1] for a, b in zip(first_skin['loops'], second_skin['loops'])),
         'Paired loops do not identify the same mapped vertex pair')
    return {'same_index_vertices': True, 'vertex_remapping_used': False,
        'ordered_faces_exact': True, 'ordered_triangles_exact': True, 'ordered_corner_vertices_exact': True,
        'unique_undirected_edge_bijection': True, 'edge_bijection_expected_to_reimport': bijection,
        'loop_edges_connect_current_to_next_corner': True, 'paired_loop_edge_vertex_pairs_exact': True,
        'raw_ordered_edges_exact': first['edges'] == second['edges'],
        'raw_edge_entries_changed': sum(a != b for a, b in zip(first['edges'], second['edges'])),
        'raw_loop_edge_indices_exact': all(a[1] == b[1] for a, b in zip(first_skin['loops'], second_skin['loops'])),
        'raw_loop_edge_indices_changed': sum(a[1] != b[1] for a, b in zip(first_skin['loops'], second_skin['loops'])),
        'raw_ordered_loop_pairs_exact': first_skin['loops'] == second_skin['loops'],
        'counts': {'vertices': count, 'edges': len(first['edges']), 'faces': len(faces),
                   'loops': len(corner_vertices), 'triangles': len(triangles)}}


def skin_semantics(first, second, vertices, loops, faces):
    for skin in (first, second):
        groups = skin['groups']
        need(all(type(n) is str and n for n in groups) and len(groups) == len(set(groups)),
             'Empty/duplicate named groups')
        need(len(skin['weights']) == vertices, 'Named weight vertex count differs')
        need(all(type(row) is dict and set(row) <= set(groups)
                 and all(type(w) in (int, float) and math.isfinite(w) and 0. <= w <= 1. for w in row.values())
                 for row in skin['weights']), 'Unknown/nonfinite/out-of-bounds named weight')
        layers = skin['UV']
        need(len({layer[0] for layer in layers}) == len(layers)
             and all(len(layer) == 2 and type(layer[0]) is str and layer[0]
                     and len(layer[1]) == loops and all(len(p) == 2 and all(math.isfinite(v) for v in p)
                                                       for p in layer[1]) for layer in layers),
             'Invalid/duplicate/incomplete named UV layer')
        slots = len(skin['materials'])
        need(slots > 0 and len(skin['material_indices']) == faces
             and all(integer(i, slots) for i in skin['material_indices']), 'Material face/slot bounds differ')
    need(set(first['groups']) == set(second['groups']), 'Named group set differs')
    need(first['UV'] == second['UV'], 'Ordered named UV corner values differ')
    need(len(first['materials']) == len(second['materials']), 'Material slot count differs')
    need(first['material_indices'] == second['material_indices'], 'Ordered material indices differ')
    names = sorted(set(first['groups']) | set(second['groups']))
    raw_changed = []
    omitted_zero = added_zero = 0
    maximum = 0.
    for index, (a, b) in enumerate(zip(first['weights'], second['weights'])):
        if a != b:
            raw_changed.append(index)
        omitted_zero += sum(name not in b and value == 0. for name, value in a.items())
        added_zero += sum(name not in a and value == 0. for name, value in b.items())
        need({n: w for n, w in a.items() if w != 0.} == {n: w for n, w in b.items() if w != 0.},
             'Named nonzero weight value/support differs')
        need({n for n, w in a.items() if w > 0.} == {n for n, w in b.items() if w > 0.},
             'Positive named support differs')
        for name in names:
            error = abs(a.get(name, 0.) - b.get(name, 0.))
            maximum = max(maximum, error)
            need(error == 0., 'All-name default-zero weight value differs')
    return {'group_name_set_exact': True, 'raw_group_order_exact': first['groups'] == second['groups'],
        'named_nonzero_values_exact': True, 'positive_support_exact': True,
        'all_name_default0_values_exact': True, 'maximum_named_weight_error': maximum,
        'raw_weight_entries_exact': first['weights'] == second['weights'],
        'raw_weight_entry_changed_vertices': raw_changed, 'omitted_zero_entries': omitted_zero,
        'added_zero_entries': added_zero, 'zero_default_is_checker_only': True, 'model_weights_modified': False,
        'ordered_named_UV_corner_values_exact': True, 'ordered_material_indices_exact': True,
        'material_slot_count_exact': True, 'material_slot_count': len(first['materials']),
        'raw_material_names_exact': first['materials'] == second['materials'],
        'raw_material_names': {'expected': first['materials'], 'reimport': second['materials']},
        'material_texture_verified': False}


def checked_reimport(report, write, target, expected_skin, mesh, graph, base, cold, ordered_skin, skin, metres, limit_m):
    row = {'scope': 'PRIVATE_FIXED_INPUT_REST_FBX_SEMANTIC_CHECKER_V2', 'passed': False,
           'reason': 'Measured FBX edge renumbering and zero-entry omission; original raw-identity failure is preserved.',
           'prior_failure': {'path': str(PRIOR_FAILURE), 'sha256': PRIOR_FAILURE_SHA, 'preserved': True},
           'diagnostic': {'path': str(DIAGNOSTIC), 'sha256': DIAGNOSTIC_SHA},
           'vertex_remapping_used': False, 'material_texture_verified': False,
           'public_export_verified': False, 'Unity_verified': False, 'export_accepted': False}
    report['REST_reimport_semantic_checker'] = row
    try:
        observed = base.native_mesh(mesh, graph)
        observed_skin = ordered_skin(mesh, graph, skin)
        row['geometry'] = geometry_semantics(target, expected_skin, observed, observed_skin)
        counts = row['geometry']['counts']
        row['skin'] = skin_semantics(expected_skin, observed_skin, counts['vertices'], counts['loops'], counts['faces'])
        error = dict(cold.error(target['points'], observed['points'], metres), triangles_exact=True)
        row['same_index_coordinate_error'] = error
        row['coordinate_threshold_m'] = limit_m
        row['coordinate_threshold_passed'] = error['maximum_m'] <= limit_m
        row['passed'] = row['coordinate_threshold_passed']
        return error
    except Exception as error:
        row['failure'] = repr(error)
        raise
    finally:
        write()


def instrument(tree):
    original = copy.deepcopy(tree)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    assignments = {n.targets[0].slice.value: n for n in ast.walk(main)
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript)
        and isinstance(n.targets[0].value, ast.Name) and n.targets[0].value.id == 'report'
        and isinstance(n.targets[0].slice, ast.Constant)}
    geometry = assignments['REST_reimport_error']; skin = assignments[OLD_SKIN_FIELD]
    expected_geometry = ast.parse('base.geometry_pair(cold, target, base.native_mesh(mesh, graph), metres)', mode='eval').body
    expected_skin = ast.parse('skin_exact(expected_skin, ordered_skin(mesh, graph, skin))', mode='eval').body
    need(ast.dump(geometry.value) == ast.dump(expected_geometry) and ast.dump(skin.value) == ast.dump(expected_skin),
         'Frozen reimport assignment ABI differs')
    geometry.value = ast.parse('_checked_reimport(report, write, target, expected_skin, mesh, graph, base, cold, ordered_skin, skin, metres, LIMIT_M)', mode='eval').body
    skin.value = ast.parse("report['REST_reimport_semantic_checker']['passed']", mode='eval').body
    renamed = []
    for node in ast.walk(main):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == 'report' \
                and isinstance(node.slice, ast.Constant) and node.slice.value == OLD_SKIN_FIELD:
            node.slice.value = NEW_SKIN_FIELD; renamed.append(node)
    need(len(renamed) == 2, 'Exactly one reimport assignment and one original skin gate required')
    # Reverse precisely those changes and require every other parent node to remain exact.
    audit = copy.deepcopy(tree)
    audit_main = next(n for n in audit.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    for node in ast.walk(audit_main):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == 'report' \
                and isinstance(node.slice, ast.Constant) and node.slice.value == NEW_SKIN_FIELD:
            node.slice.value = OLD_SKIN_FIELD
    for node in ast.walk(audit_main):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Subscript) \
                and isinstance(node.targets[0].slice, ast.Constant):
            if node.targets[0].slice.value == 'REST_reimport_error': node.value = expected_geometry
            if node.targets[0].slice.value == OLD_SKIN_FIELD: node.value = expected_skin
    need(ast.dump(audit) == ast.dump(original), 'Parent changed beyond the two reimport assignments/skin field')
    return ast.fix_missing_locations(tree)


def prepared(expected):
    need(sha(PARENT) == PARENT_SHA, 'Frozen parent differs')
    tree = instrument(ast.parse(PARENT.read_text(encoding='utf-8'), filename=str(PARENT)))
    namespace = {'__file__': str(PARENT), '__name__': 'private_fixed_rest_semantic_parent', '_checked_reimport': checked_reimport}
    exec(compile(tree, str(PARENT), 'exec'), namespace)
    namespace['PINS'].update({PARENT: PARENT_SHA, Path(__file__).resolve(): expected,
        PRIOR_FAILURE: PRIOR_FAILURE_SHA, DIAGNOSTIC: DIAGNOSTIC_SHA, MANIFEST_READER: MANIFEST_READER_SHA})
    return namespace


def current_manifest():
    need(sha(MANIFEST_READER) == MANIFEST_READER_SHA, 'Frozen full manifest reader differs')
    spec = importlib.util.spec_from_file_location('private_rest_full_manifest', MANIFEST_READER)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    result = module.current_manifest()
    need(type(result) is dict and len(result) == 159, 'Complete current canonical 159-file inventory differs')
    return result


def pure_checks():
    prepared(sha(__file__))
    native = {'points': [[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.]],
              'edges': [(0, 1), (1, 2), (2, 3), (3, 0)], 'faces': [(0, 1, 2, 3)],
              'triangles': [(0, 1, 2), (0, 2, 3)]}
    skin = {'groups': ['a', 'zero'], 'weights': [{'a': .5, 'zero': 0.} for _ in range(4)],
            'UV': [('UVMap', [[0., 0.], [1., 0.], [1., 1.], [0., 1.]])],
            'materials': ['Purple'], 'material_indices': [0], 'loops': [(0, 0), (1, 1), (2, 2), (3, 3)]}
    reordered = copy.deepcopy(native); reordered['edges'] = [(2, 3), (0, 3), (1, 0), (2, 1)]
    imported = copy.deepcopy(skin); imported.update(groups=['zero', 'a'], weights=[{'a': .5} for _ in range(4)],
        loops=[(0, 2), (1, 3), (2, 0), (3, 1)], materials=['Purple.001'])
    g = geometry_semantics(native, skin, reordered, imported)
    s = skin_semantics(skin, imported, 4, 4, 1)
    need(g['unique_undirected_edge_bijection'] and not g['raw_loop_edge_indices_exact']
         and s['omitted_zero_entries'] == 4 and not s['raw_weight_entries_exact'], 'Allowed measured semantics differ')
    rejected = []
    cases = []
    def candidate(label, native_edit=None, skin_edit=None):
        a, b = copy.deepcopy(reordered), copy.deepcopy(imported)
        if native_edit: native_edit(a)
        if skin_edit: skin_edit(b)
        cases.append((label, a, b))
    candidate('wrong_vertex_index', skin_edit=lambda s: s['loops'].__setitem__(0, (1, 2)))
    candidate('face_winding', native_edit=lambda n: n['faces'].__setitem__(0, (0, 3, 2, 1)))
    candidate('triangle_order', native_edit=lambda n: n['triangles'].reverse())
    candidate('edge_endpoint', native_edit=lambda n: n['edges'].__setitem__(0, (0, 2)))
    candidate('duplicate_edge', native_edit=lambda n: n['edges'].__setitem__(0, (0, 3)))
    candidate('loop_next_corner', skin_edit=lambda s: s['loops'].__setitem__(0, (0, 0)))
    candidate('loop_bounds', skin_edit=lambda s: s['loops'].__setitem__(0, (0, 4)))
    candidate('positive_weight', skin_edit=lambda s: s['weights'][0].__setitem__('a', .5001))
    candidate('UV_value', skin_edit=lambda s: s['UV'][0][1][0].__setitem__(0, .1))
    candidate('material_index', skin_edit=lambda s: s['material_indices'].__setitem__(0, 1))
    candidate('material_slot_count', skin_edit=lambda s: s['materials'].append('Extra'))
    for label, a, b in cases:
        try:
            geometry_semantics(native, skin, a, b); skin_semantics(skin, b, 4, 4, 1)
        except RuntimeError: rejected.append(label)
        else: raise RuntimeError('Invalid pure control admitted: ' + label)
    need(len(rejected) == len(cases), 'Pure controls incomplete')
    print(json.dumps({'source_only': True, 'native_executed': False, 'parent_only_two_reimport_assignments_changed': True,
        'parent_Rest_thresholds_and_entire_finally_exact': True, 'allow_edge_reordering_and_zero_omission': True,
        'rejected': rejected, 'material_texture_verified': False, 'export_accepted': False}))
    return 0


def main():
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    need(arguments.count('--expected-script-sha') == arguments.count('--output') == arguments.count('--soft-seconds') == 1,
         'One explicit wrapper SHA/output/soft budget required')
    index = arguments.index('--expected-script-sha') + 1
    expected = arguments[index]
    need(sha(__file__) == expected and 0. < float(arguments[arguments.index('--soft-seconds') + 1]) <= 180.,
         'Wrapper SHA or original bounded soft budget differs')
    need('--threads' in sys.argv and sys.argv[sys.argv.index('--threads') + 1] == '1', 'Root launcher must use one native thread')
    output = Path(arguments[arguments.index('--output') + 1])
    need(output.is_absolute() and output.resolve().is_relative_to(HERE.resolve()) and not output.exists(), 'Fresh private output required')
    namespace = prepared(expected)
    need(all(sha(path) == value for path, value in namespace['PINS'].items()), 'Frozen inputs/helper/history differ')
    before = current_manifest()
    forwarded = arguments.copy(); forwarded[index] = PARENT_SHA
    original_argv = sys.argv; result = 2
    try:
        sys.argv = [str(PARENT), '--', *forwarded]
        result = namespace['main']()
    finally:
        sys.argv = original_argv
        path = output/'report.json'
        final_errors = []; after = None; source_exact = immutable = False
        try:
            after = current_manifest(); source_exact = before == after
        except Exception as error:
            final_errors.append({'source_manifest_after': repr(error)})
        try:
            immutable = all(sha(p) == value for p, value in namespace['PINS'].items())
        except Exception as error:
            final_errors.append({'immutable_pins_after': repr(error)})
        if path.is_file():
            report = json.loads(path.read_text(encoding='utf-8'))
            report.update(checker_version='PRIVATE_REST_FBX_REIMPORT_SEMANTICS_V2',
                artifact_provenance={'actual_input': str(namespace['SNAPSHOT']),
                    'input_sha256': namespace['PINS'][namespace['SNAPSHOT']], 'fixed_completed_PNS_input': True,
                    'current_artist_loaded': False, 'current_artist_validation': 'Unmeasured',
                    'current_live_unsaved_state': 'Unmeasured', 'material_texture_verified': False},
                source_before=before, source_after=after, canonical_source_files_exact=source_exact,
                wrapper_and_historical_files_unchanged=immutable,
                prior_strict_failure={'path': str(PRIOR_FAILURE), 'sha256': PRIOR_FAILURE_SHA, 'preserved': True})
            if not source_exact or not immutable:
                report['errors'].append({'wrapper_final_protection': 'Current source or frozen input/history changed'})
                report['native_component_verified'] = False
            report['errors'].extend(final_errors)
            path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        need(source_exact and immutable, 'Complete current source or frozen input/history changed')
    return result


if __name__ == '__main__':
    raise SystemExit(pure_checks() if '--pure-checks' in sys.argv else main())
