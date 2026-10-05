"""Read-only Hair pairing evidence in an isolated saved X process.

No nearest point, tolerance bucket, bone/object name pairing or metadata write
is used. The optional existing pure topology prover uses exactly X=0 seam
seeds. This script emits diagnostics only and never saves its opened blend.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/addons')
from character_designer import hair_strand_registry as registry
from character_designer import hair_bones_rig as hair
from character_designer import symmetry_pairs


def cyclic(face):
    face = tuple(face)
    reversed_face = tuple(reversed(face))
    return min(tuple(order[offset:] + order[:offset])
               for order in (face, reversed_face) for offset in range(len(face)))


def digest(value):
    return hashlib.sha256(repr(value).encode('utf8')).hexdigest()


def native_state(source, armature):
    mesh = source.data
    return digest((
        tuple((key, repr(source[key])) for key in sorted(source.keys())),
        tuple(tuple(vertex.co) for vertex in mesh.vertices),
        tuple(tuple(edge.vertices) for edge in mesh.edges),
        tuple(tuple(face.vertices) for face in mesh.polygons),
        tuple((layer.name, tuple(tuple(point.uv) for point in layer.data)) for layer in mesh.uv_layers),
        tuple((key.name, tuple(tuple(point.co) for point in key.data)) for key in mesh.shape_keys.key_blocks)
            if mesh.shape_keys else (),
        tuple((group.name, group.lock_weight) for group in source.vertex_groups),
        tuple(tuple((entry.group, entry.weight) for entry in vertex.groups) for vertex in mesh.vertices),
        tuple((bone.name, hair._bone_state(bone), tuple((key, repr(bone[key])) for key in sorted(bone.keys())))
              for bone in armature.data.bones),
        tuple((bone.name, tuple(tuple(row) for row in bone.matrix_basis)) for bone in armature.pose.bones),
        source.mode, armature.mode,
        tuple(tuple(row) for row in source.matrix_world), tuple(tuple(row) for row in armature.matrix_world)))


def exact_lookup(points):
    buckets = defaultdict(list)
    for index, point in enumerate(points):
        buckets[tuple(point)].append(index)
    lookup, duplicate, absent = {}, [], []
    for index, (x, y, z) in enumerate(points):
        original, reflected = buckets[(x, y, z)], buckets.get((-x, y, z), ())
        if len(original) != 1 or len(reflected) > 1:
            duplicate.append(index)
        elif not reflected:
            absent.append(index)
        else:
            lookup[index] = reflected[0]
    assert all(lookup.get(value) == key for key, value in lookup.items())
    return lookup, duplicate, absent


def proof_candidates(strands, lookup, edges, faces):
    adjacency = defaultdict(set)
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    edge_sets, face_sets, incident_edges, incident_faces = {}, {}, {}, {}
    domains = {item['order']: set(item['vertices']) for item in strands}
    for item in strands:
        order, domain = item['order'], domains[item['order']]
        edge_sets[order] = {tuple(sorted(edge)) for edge in edges if set(edge) <= domain}
        face_sets[order] = {cyclic(face) for face in faces if set(face) <= domain}
        incident_edges[order] = {tuple(sorted(edge)) for edge in edges if set(edge) & domain}
        incident_faces[order] = {cyclic(face) for face in faces if set(face) & domain}
    candidates, rows = {}, []
    for item in strands:
        order, domain = item['order'], domains[item['order']]
        mapped = {index: lookup[index] for index in domain if index in lookup}
        row = {'order': order, 'strand_id': item['strand_id'], 'vertices': len(domain),
               'mapped_vertices': len(mapped), 'layers': len(item['layers']), 'bones': len(item['bones']),
               'layer_lengths': [len(layer) for layer in item['layers']],
               'candidate_orders': [], 'complete': len(mapped) == len(domain)}
        if row['complete']:
            target_domain = set(mapped.values())
            matching = [other for other in strands if domains[other['order']] == target_domain
                        and registry._compatible(item, other)
                        and all({mapped[index] for index in layer} == set(other_layer)
                                for layer, other_layer in zip(item['layers'], other['layers']))]
            row['candidate_orders'] = [other['order'] for other in matching]
            if len(matching) == 1:
                other = matching[0]
                target = other['order']
                row['induced_edges_exact'] = {
                    tuple(sorted(mapped[index] for index in edge)) for edge in edge_sets[order]} == edge_sets[target]
                row['induced_faces_exact'] = {
                    cyclic(tuple(mapped[index] for index in face)) for face in face_sets[order]} == face_sets[target]
                row['vertex_degrees_equal'] = all(len(adjacency[index]) == len(adjacency[mapped[index]]) for index in domain)
                one_ring = domain | {neighbor for index in domain for neighbor in adjacency[index]}
                face_ring = one_ring | {index for face in incident_faces[order] for index in face}
                row['boundary_map_complete'] = all(index in lookup for index in face_ring)
                if row['boundary_map_complete']:
                    row['incident_edges_exact'] = {
                        tuple(sorted(lookup[index] for index in edge)) for edge in incident_edges[order]} == incident_edges[target]
                    row['incident_faces_exact'] = {
                        cyclic(tuple(lookup[index] for index in face)) for face in incident_faces[order]} == incident_faces[target]
                if row['induced_edges_exact'] and row['induced_faces_exact'] and row['vertex_degrees_equal']:
                    candidates[order] = target
        rows.append(row)
    reciprocal = [(order, target) for order, target in sorted(candidates.items())
                  if order <= target and candidates.get(target) == order]
    by_order = {row['order']: row for row in rows}
    full_incidence = [(order, target) for order, target in reciprocal
                      if all(by_order[key].get('incident_edges_exact') and by_order[key].get('incident_faces_exact')
                             for key in {order, target})]
    return {'reciprocal_induced_pairs': reciprocal,
            'reciprocal_complete_incidence_pairs': full_incidence, 'strands': rows}


def metadata_summary(source, record):
    result = {'binding_version': record['version'], 'mirror_layout': record.get('mirror_layout'),
              'saved_mirrors': record.get('mirrors', []),
              'native_modifiers': [(item.name, item.type) for item in source.modifiers],
              'mesh_property_keys': sorted(source.data.keys()), 'source_property_keys': sorted(source.keys())}
    for key in ('character_designer_hair_groups', 'character_designer_cross_sections', 'character_designer_hair_binding_v1'):
        raw = source.get(key)
        if not isinstance(raw, str):
            continue
        try:
            data = json.loads(raw)
        except ValueError:
            result[key] = {'unreadable': True}
            continue
        if not isinstance(data, dict):
            result[key] = {'unsupported_type': type(data).__name__}
        elif key.endswith('_groups'):
            result[key] = {'keys': sorted(data), 'strands': len(data.get('strands', [])),
                           'groups': len(data.get('groups', [])),
                           'pair_fields': sorted({field for item in data.get('strands', [])
                               for field in item if any(word in field.lower() for word in ('mirror', 'pair', 'side'))})}
        elif key.endswith('_cross_sections'):
            result[key] = {'keys': sorted(data), 'section_count': len(data.get('sections', [])),
                           'point_count': data.get('point_count'), 'space': data.get('space'),
                           'pair_fields': sorted({field for item in data.get('sections', [])
                               for field in item if any(word in field.lower() for word in ('mirror', 'pair', 'side'))})}
        else:
            result[key] = {'keys': sorted(data), 'mirror_count': len(data.get('mirrors', [])),
                           'tip_patch_count': len(data.get('tip_patches', {})),
                           'cap_vertex_count': len(data.get('cap_vertices', []))}
    return result


source = bpy.data.objects['Hair']
armature = source[hair.RIG_KEY]
before = native_state(source, armature)
data, record, geometry = registry._live(source)
points, edges, faces = geometry
lookup, duplicate, absent = exact_lookup(points)
exact = proof_candidates(data['strands'], lookup, edges, faces)
pure_result = None
try:
    pure = symmetry_pairs.build_vertex_pairs(points, edges, faces, centerline_tolerance=0.0)
    pure_lookup = {index: index for index in pure.centerline}
    for negative, positive in pure.pairs:
        pure_lookup[negative], pure_lookup[positive] = positive, negative
    pure_result = {'matched_vertices': len(pure_lookup), 'unmatched': len(pure.unmatched),
                   'ambiguous': len(pure.ambiguous), 'diagnostics': pure.diagnostics,
                   **proof_candidates(data['strands'], pure_lookup, edges, faces)}
except symmetry_pairs.SymmetryPairError as exc:
    pure_result = {'error': str(exc)}
after = native_state(source, armature)
assert before == after, 'The diagnostic modified native Hair data or metadata.'
result = {'ok': True, 'blender': bpy.app.version_string, 'source': source.name,
          'source_uid': data['source_uid'], 'topology': data['topology'], 'artist_saved': False,
          'metadata_model_exact': before == after, 'metadata': metadata_summary(source, record),
          'exact_reflection': {'axis': 'X', 'tolerance': 0, 'vertex_count': len(points),
               'mapped_vertices': len(lookup), 'exact_centers': sum(index == other for index, other in lookup.items()),
               'duplicate_coordinate_vertices': len(duplicate), 'missing_exact_reflection_vertices': len(absent), **exact},
          'existing_pure_topology_exact_seam': pure_result}
path = Path(__file__).with_name('hair_pair_proof_diagnostics.json')
path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
print('HAIR_PAIR_PROOFS', json.dumps({'ok': result['ok'], 'metadata_model_exact': result['metadata_model_exact'],
      'exact_vertices': len(lookup), 'exact_pairs': exact['reciprocal_induced_pairs'],
      'exact_complete_incidence_pairs': exact['reciprocal_complete_incidence_pairs'],
      'pure_pairs': pure_result.get('reciprocal_induced_pairs', []), 'artist_saved': False}))
