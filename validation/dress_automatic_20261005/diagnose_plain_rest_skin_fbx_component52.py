"""Read-only reimport diagnostics inserted before the fixed REST component gate.

No gate, worker, parent script, historical report, or native cleanup is changed.
Root alone may invoke the bounded launcher after coordinating native resources.
"""
import ast
from collections import Counter
import hashlib
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARENT = HERE/'verify_plain_rest_skin_fbx_component52.py'
PARENT_SHA = '9b93aab9edde5cbf6065e2e8ab9bf81ef27d07a79cd7cb9b792451f466e8564f'
INSERTED_CALL = '_diagnose_reimport'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def cyclic_face(face):
    """Only rotate the starting corner; retain winding and duplicate faces."""
    face = tuple(face)
    return min(face[i:] + face[:i] for i in range(len(face))) if face else face


def ordered_difference(first, second):
    common = min(len(first), len(second))
    mismatch = next((i for i in range(common) if first[i] != second[i]), None)
    return {'exact': first == second, 'expected_count': len(first), 'reimport_count': len(second),
            'changed_at_common_indices': sum(first[i] != second[i] for i in range(common)),
            'first_changed_index': mismatch,
            'first_expected': first[mismatch] if mismatch is not None else None,
            'first_reimport': second[mismatch] if mismatch is not None else None}


def _diagnose_reimport(report, write, target, expected_skin, mesh, arm, graph, base, cold,
                       ordered_skin, skin_reader, matrix_errors, bone_names, parents, rest, metres):
    row = {'scope': 'READ_ONLY_REIMPORT_DIAGNOSTICS_BEFORE_UNCHANGED_STRICT_GATE',
           'status': 'incomplete', 'gate_changed': False, 'remapping_used': False,
           'public_export_verified': False, 'Unity_verified': False, 'errors': []}
    report['REST_reimport_diagnostic'] = row
    try:
        observed = base.native_mesh(mesh, graph)
        observed_skin = ordered_skin(mesh, graph, skin_reader)
        counts = lambda native, skin: {'vertices': len(native['points']), 'edges': len(native['edges']),
            'faces': len(native['faces']), 'loops': len(skin['loops']), 'triangles': len(native['triangles'])}
        row['counts'] = {'expected': counts(target, expected_skin),
                         'reimport': counts(observed, observed_skin)}
        row['ordered_geometry'] = {key: ordered_difference(target[key], observed[key])
                                   for key in ('edges', 'faces', 'triangles')}
        expected_edges = Counter(tuple(sorted(edge)) for edge in target['edges'])
        imported_edges = Counter(tuple(sorted(edge)) for edge in observed['edges'])
        expected_faces = Counter(cyclic_face(face) for face in target['faces'])
        imported_faces = Counter(cyclic_face(face) for face in observed['faces'])
        row['undirected_edge_multiset'] = {'exact': expected_edges == imported_edges,
            'missing_occurrences': sum((expected_edges - imported_edges).values()),
            'extra_occurrences': sum((imported_edges - expected_edges).values())}
        row['winding_preserved_face_cyclic_multiset'] = {'exact': expected_faces == imported_faces,
            'missing_occurrences': sum((expected_faces - imported_faces).values()),
            'extra_occurrences': sum((imported_faces - expected_faces).values())}
        row['loops'] = {'vertex_order': ordered_difference(
            [entry[0] for entry in expected_skin['loops']], [entry[0] for entry in observed_skin['loops']]),
            'edge_index_order': ordered_difference(
            [entry[1] for entry in expected_skin['loops']], [entry[1] for entry in observed_skin['loops']]),
            'full_ordered_pairs': ordered_difference(expected_skin['loops'], observed_skin['loops'])}
        row['skin_fields'] = {'expected': expected_skin, 'reimport': observed_skin,
            'groups_order_exact': expected_skin['groups'] == observed_skin['groups'],
            'groups_name_set_exact': set(expected_skin['groups']) == set(observed_skin['groups']),
            'fields_exact': {key: expected_skin[key] == observed_skin[key]
                for key in ('weights', 'UV', 'materials', 'material_indices', 'loops')}}
        row['same_index_coordinates'] = {'evaluated': False, 'remapping_used': False}
        if len(target['points']) == len(observed['points']):
            row['same_index_coordinates'].update(evaluated=True,
                **cold.error(target['points'], observed['points'], metres))
        else:
            row['same_index_coordinates']['reason'] = 'Vertex counts differ; no coordinate remapping attempted'
        imported_names = set(arm.data.bones.keys())
        complete = imported_names == bone_names
        imported_parents = {name: bone.parent.name if bone.parent else None
                            for name, bone in arm.data.bones.items()}
        row['complete_Rest'] = {'expected_count': len(bone_names), 'reimport_count': len(imported_names),
            'names_exact': complete, 'parents_exact': parents == imported_parents,
            'expected_names': sorted(bone_names), 'reimport_names': sorted(imported_names),
            'expected_parents': parents, 'reimport_parents': imported_parents,
            'matrix_error_evaluated': False}
        if complete:
            names = sorted(bone_names)
            imported_rest = {name: arm.matrix_world @ arm.data.bones[name].matrix_local for name in names}
            row['complete_Rest'].update(matrix_error_evaluated=True,
                matrix_error=matrix_errors([rest[name] for name in names],
                                          [imported_rest[name] for name in names], metres),
                expected_world_matrices={name: [list(values) for values in rest[name]] for name in names},
                reimport_world_matrices={name: [list(values) for values in imported_rest[name]] for name in names})
        row['status'] = 'measured'
    except Exception as error:
        row['status'] = 'diagnostic_failed'
        row['errors'].append({'error': repr(error), 'traceback': traceback.format_exc()})
    # Persist evidence before the original gate can fail, then let original main/finally continue.
    write()


def instrument(tree):
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    matches = []

    class Insert(ast.NodeTransformer):
        def visit_Assign(self, node):
            if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Subscript)
                    and isinstance(node.targets[0].value, ast.Name) and node.targets[0].value.id == 'report'
                    and isinstance(node.targets[0].slice, ast.Constant)
                    and node.targets[0].slice.value == 'REST_reimport_error'):
                if not (isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                        and node.value.func.attr == 'geometry_pair'):
                    raise RuntimeError('Fixed parent reimport geometry ABI differs')
                matches.append(node)
                call = ast.parse('_diagnose_reimport(report, write, target, expected_skin, mesh, arm, graph, '
                    'base, cold, ordered_skin, skin, matrix_errors, bone_names, parents, rest, metres)').body[0]
                ast.increment_lineno(call, node.lineno - 1)
                return [ast.copy_location(call, node), node]
            return node

    Insert().visit(main)
    if len(matches) != 1:
        raise RuntimeError('Exactly one fixed reimport gate must be instrumented')
    return ast.fix_missing_locations(tree)


def main():
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if arguments.count('--expected-script-sha') != 1:
        raise RuntimeError('One exact diagnostic script SHA is required')
    index = arguments.index('--expected-script-sha') + 1
    expected = arguments[index]
    wrapper = Path(__file__).resolve()
    if sha(wrapper) != expected or sha(PARENT) != PARENT_SHA:
        raise RuntimeError('Diagnostic wrapper or fixed parent source changed')
    tree = instrument(ast.parse(PARENT.read_text(encoding='utf-8'), filename=str(PARENT)))
    namespace = {'__file__': str(PARENT), '__name__': 'private_fixed_rest_parent',
                 INSERTED_CALL: _diagnose_reimport}
    exec(compile(tree, str(PARENT), 'exec'), namespace)
    # Parent keeps its own real __file__/SHA. The wrapper is an additional before/after input pin.
    namespace['PINS'][PARENT] = PARENT_SHA
    namespace['PINS'][wrapper] = expected
    forwarded = arguments.copy()
    forwarded[index] = PARENT_SHA
    original_argv = sys.argv
    try:
        sys.argv = [str(PARENT), '--', *forwarded]
        return namespace['main']()
    finally:
        sys.argv = original_argv


if __name__ == '__main__':
    raise SystemExit(main())
