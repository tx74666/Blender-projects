"""Restore only the three deleted shoe ring islands from Shoes_Primitive.

Import and call plan() for a read-only audit. Call apply() explicitly to run a
single UNDO operator. Requires Object Mode; never saves or reloads any file.
"""
import json
from collections import Counter

import bpy
from mathutils.kdtree import KDTree

SOURCE = 'Shoes_Primitive'
TARGET = 'Shoes'
SEEDS = (1912, 4184, 5320)
TOLERANCE = 1e-7
LAST_RESULT = None
TOPOLOGY_ATTRIBUTES = {'position', '.edge_verts', '.corner_vert', '.corner_edge', 'material_index'}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def cyclic(values):
    values = tuple(values)
    return min(values[n:] + values[:n] for n in range(len(values)))


def face_key(values):
    values = tuple(values)
    return min(cyclic(values), cyclic(tuple(reversed(values))))


def objects():
    source = bpy.data.objects.get(SOURCE)
    target = bpy.data.objects.get(TARGET)
    require(source and target and source.type == target.type == 'MESH', 'Expected Shoes_Primitive and Shoes mesh objects')
    require(source.data != target.data, 'Source and target must use different mesh data')
    require(source.mode == target.mode == 'OBJECT', 'Exit Edit Mode before planning or applying recovery')
    require(not target.library and not target.data.library, 'Target must be a local editable mesh')
    require(not target.data.shape_keys, 'Target has shape keys; recovery requires a different workflow')
    require(target.data.users == 1, 'Target mesh is shared by other objects; refuse to alter that relationship')
    return source, target


def source_islands(source):
    mesh = source.data
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    result = []
    for seed in SEEDS:
        require(seed < len(mesh.vertices), 'Source topology does not match the audited backup')
        indices, pending = {seed}, [seed]
        while pending:
            for index in adjacency[pending.pop()]:
                if index not in indices:
                    indices.add(index)
                    pending.append(index)
        edges = [e.index for e in mesh.edges if e.vertices[0] in indices]
        faces = [p.index for p in mesh.polygons if p.vertices[0] in indices]
        require((len(indices), len(edges), len(faces)) == (432, 864, 432), f'Source ring {seed} is not the audited complete 432-vertex ring')
        require(all(mesh.materials[mesh.polygons[i].material_index].name == 'ShoeGray' for i in faces), f'Source ring {seed} is not entirely ShoeGray')
        require(not any(indices & previous['indices'] for previous in result), 'Source rings overlap')
        result.append({'seed': seed, 'indices': indices, 'edges': edges, 'faces': faces})
    return result


def _plan(source, target, mesh=None):
    mesh = mesh or target.data
    src = source.data
    transform = target.matrix_world.inverted() @ source.matrix_world
    tree = KDTree(len(mesh.vertices))
    for v in mesh.vertices:
        tree.insert(v.co, v.index)
    tree.balance()
    edges_by_key = {}
    for e in mesh.edges:
        key = tuple(sorted(e.vertices))
        require(key not in edges_by_key, 'Target contains duplicate edges')
        edges_by_key[key] = e.index
    faces_by_key = {}
    for face in mesh.polygons:
        key = face_key(face.vertices)
        require(key not in faces_by_key, 'Target contains duplicate oriented faces')
        faces_by_key[key] = face.index
    mapping, new_vertices, new_edges, new_faces, rings = {}, [], [], [], []
    for island in source_islands(source):
        matches = {}
        for index in sorted(island['indices']):
            coordinate = transform @ src.vertices[index].co
            candidates = tree.find_range(coordinate, TOLERANCE)
            require(len(candidates) <= 1, f'Ambiguous target coordinate for source vertex {index}')
            if candidates:
                matches[index] = candidates[0][1]
        require(len(matches) in (4, 432), f'Ring {island["seed"]} has {len(matches)} matching vertices; expected the audited four-vertex remnant or a complete ring')
        require(len(set(matches.values())) == len(matches), 'Source vertices map to the same target vertex')
        target_ids = set(matches.values())
        touching_edges = [e for e in mesh.edges if any(i in target_ids for i in e.vertices)]
        touching_faces = [p for p in mesh.polygons if any(i in target_ids for i in p.vertices)]
        require(all(set(e.vertices) <= target_ids for e in touching_edges), 'Ring remnant has new external edge connections')
        require(all(set(p.vertices) <= target_ids for p in touching_faces), 'Ring remnant has new external face connections')
        expected = (4, 1) if len(matches) == 4 else (864, 432)
        require((len(touching_edges), len(touching_faces)) == expected, 'Ring remnant or restored ring topology differs from the audited case')
        source_edge_keys = {tuple(sorted((matches.get(src.edges[e].vertices[0], -1), matches.get(src.edges[e].vertices[1], -1)))) for e in island['edges']}
        source_face_keys = {face_key(matches.get(v, -1) for v in src.polygons[f].vertices): cyclic(matches.get(v, -1) for v in src.polygons[f].vertices) for f in island['faces']}
        require(all(tuple(sorted(e.vertices)) in source_edge_keys for e in touching_edges), 'Existing ring edges do not match the original')
        require(all(face_key(p.vertices) in source_face_keys for p in touching_faces), 'Existing ring faces do not match the original')
        orientations = {cyclic(p.vertices) != source_face_keys[face_key(p.vertices)] for p in touching_faces}
        require(len(orientations) == 1, 'Existing ring face normals are inconsistent')
        reverse_winding = orientations.pop()
        require(all(mesh.materials[p.material_index] and mesh.materials[p.material_index].name == 'ShoeGray' for p in touching_faces), 'Existing ring face material changed')
        for index in sorted(island['indices']):
            if index in matches:
                mapping[index] = matches[index]
            else:
                mapping[index] = len(mesh.vertices) + len(new_vertices)
                new_vertices.append((index, tuple(transform @ src.vertices[index].co)))
        for index in island['edges']:
            pair = tuple(mapping[v] for v in src.edges[index].vertices)
            key = tuple(sorted(pair))
            if key not in edges_by_key:
                edges_by_key[key] = len(mesh.edges) + len(new_edges)
                new_edges.append((index, pair))
        for index in island['faces']:
            source_face = src.polygons[index]
            source_loops = list(source_face.loop_indices)
            if reverse_winding:
                source_loops.reverse()
            vertices = tuple(mapping[src.loops[i].vertex_index] for i in source_loops)
            key = face_key(vertices)
            if key not in faces_by_key:
                faces_by_key[key] = len(mesh.polygons) + len(new_faces)
                new_faces.append((index, vertices, source_loops))
        rings.append({'seed': island['seed'], 'matching_vertices': len(matches), 'reverse_source_winding_to_match_existing': reverse_winding, 'status': 'already_restored' if len(matches) == 432 else 'restore_missing_geometry'})
    group_names = {g.index: g.name for g in source.vertex_groups}
    target_names = {g.name for g in target.vertex_groups}
    needed = {group_names[g.group] for index, _ in new_vertices for g in src.vertices[index].groups}
    require(needed <= target_names, f'Target is missing source vertex groups: {sorted(needed - target_names)}')
    summary = {'source': source.name, 'target': target.name, 'rings': rings, 'before': {'vertices': len(mesh.vertices), 'edges': len(mesh.edges), 'faces': len(mesh.polygons)}, 'add': {'vertices': len(new_vertices), 'edges': len(new_edges), 'faces': len(new_faces)}, 'existing_geometry_preserved': True}
    return {'summary': summary, 'mapping': mapping, 'new_vertices': new_vertices, 'new_edges': new_edges, 'new_faces': new_faces, 'edges_by_key': edges_by_key}


def plan():
    source, target = objects()
    return _plan(source, target)['summary']


def attribute_property(attribute):
    options = {'FLOAT': 'value', 'INT': 'value', 'INT8': 'value', 'BOOLEAN': 'value', 'FLOAT_VECTOR': 'vector', 'FLOAT2': 'vector', 'FLOAT_COLOR': 'color', 'BYTE_COLOR': 'color', 'STRING': 'value', 'INT32_2D': 'value', 'QUATERNION': 'value', 'FLOAT4X4': 'value'}
    require(attribute.data_type in options, f'Unsupported attribute type {attribute.data_type} for {attribute.name}')
    return options[attribute.data_type]


def plain(value):
    if isinstance(value, (str, bytes, bool, int, float)):
        return value
    return tuple(plain(v) for v in value)


def snapshot(mesh):
    return {'vertices': [tuple(v.co) for v in mesh.vertices], 'edges': [tuple(e.vertices) for e in mesh.edges], 'faces': [tuple(p.vertices) for p in mesh.polygons], 'loops': [(l.vertex_index, l.edge_index) for l in mesh.loops], 'weights': [tuple((g.group, g.weight) for g in v.groups) for v in mesh.vertices], 'attributes': {a.name: (a.data_type, a.domain, [plain(getattr(d, attribute_property(a))) for d in a.data]) for a in mesh.attributes}, 'materials': [m.name if m else None for m in mesh.materials], 'uv_layers': [(u.name, u.active_render, u.active_clone) for u in mesh.uv_layers], 'active_uv': mesh.uv_layers.active_index}


def assert_preserved(before, mesh):
    after = snapshot(mesh)
    for key in ('vertices', 'edges', 'faces', 'loops', 'weights'):
        require(after[key][:len(before[key])] == before[key], f'Existing {key} changed; refuse recovery')
    for name, (dtype, domain, values) in before['attributes'].items():
        require(name in after['attributes'], f'Existing attribute {name} disappeared')
        actual_type, actual_domain, actual_values = after['attributes'][name]
        require((dtype, domain) == (actual_type, actual_domain) and actual_values[:len(values)] == values, f'Existing attribute {name} changed')
    require(after['materials'][:len(before['materials'])] == before['materials'], 'Existing material slots changed')
    require(after['uv_layers'] == before['uv_layers'] and after['active_uv'] == before['active_uv'], 'Existing UV layer settings changed')


def _build_validated_copy(source, target, prepared):
    original = target.data
    before = snapshot(original)
    src = source.data
    mesh = original.copy()
    mesh.name = original.name + '_Recovered_Rings'
    holder = None
    try:
        nv, ne, nf = len(mesh.vertices), len(mesh.edges), len(mesh.polygons)
        nl = len(mesh.loops)
        # The supported constructor avoids resizing face-offset arrays on an
        # existing mesh (unsafe in Blender 5.2). Keep every original index/order.
        vertices = before['vertices'] + [coordinate for _, coordinate in prepared['new_vertices']]
        edges = before['edges'] + [pair for _, pair in prepared['new_edges']]
        faces = before['faces'] + [vertices for _, vertices, _ in prepared['new_faces']]
        mesh.clear_geometry()
        mesh.from_pydata(vertices, edges, faces, shade_flat=False)
        for name, (dtype, domain, values) in before['attributes'].items():
            attribute = mesh.attributes.get(name)
            if attribute is None:
                attribute = mesh.attributes.new(name, dtype, domain)
            require((attribute.data_type, attribute.domain) == (dtype, domain), f'Existing attribute schema changed for {name}')
            property_name = attribute_property(attribute)
            for index, value in enumerate(values):
                setattr(attribute.data[index], property_name, value)
        for name, active_render, active_clone in before['uv_layers']:
            mesh.uv_layers[name].active_render = active_render
            mesh.uv_layers[name].active_clone = active_clone
        mesh.uv_layers.active_index = before['active_uv']
        maps = {'POINT': [], 'EDGE': [], 'FACE': [], 'CORNER': []}
        for offset, (source_index, coordinate) in enumerate(prepared['new_vertices']):
            maps['POINT'].append((source_index, nv + offset))
        for offset, (source_index, pair) in enumerate(prepared['new_edges']):
            maps['EDGE'].append((source_index, ne + offset))
        loop_cursor = nl
        for offset, (source_index, vertices, source_loops) in enumerate(prepared['new_faces']):
            source_face = src.polygons[source_index]
            maps['FACE'].append((source_index, nf + offset))
            for corner, vertex in enumerate(vertices):
                maps['CORNER'].append((source_loops[corner], loop_cursor))
                loop_cursor += 1
        for source_index, target_index in maps['FACE']:
            source_face = src.polygons[source_index]
            material = src.materials[source_face.material_index]
            slot = next((i for i, candidate in enumerate(mesh.materials) if candidate == material), None)
            require(slot is not None, 'Source ring material must already exist on the target')
            mesh.polygons[target_index].material_index = slot
            mesh.polygons[target_index].use_smooth = source_face.use_smooth
        for attribute in src.attributes:
            if attribute.name in TOPOLOGY_ATTRIBUTES:
                continue
            dest_attribute = mesh.attributes.get(attribute.name)
            if dest_attribute is None:
                # Selection/hiding are UI state; do not introduce absent private layers.
                if attribute.name.startswith('.'):
                    continue
                dest_attribute = mesh.attributes.new(attribute.name, attribute.data_type, attribute.domain)
            require((dest_attribute.domain, dest_attribute.data_type) == (attribute.domain, attribute.data_type), f'Attribute schema differs for {attribute.name}')
            property_name = attribute_property(attribute)
            for source_index, target_index in maps[attribute.domain]:
                setattr(dest_attribute.data[target_index], property_name, plain(getattr(attribute.data[source_index], property_name)))
        holder = bpy.data.objects.new('_RingRecoveryValidationOnly', mesh)
        for group in target.vertex_groups:
            holder.vertex_groups.new(name=group.name)
        for index, weights in enumerate(before['weights']):
            for group_index, weight in weights:
                holder.vertex_groups[group_index].add([index], weight, 'REPLACE')
        for source_index, target_index in maps['POINT']:
            for assignment in src.vertices[source_index].groups:
                name = source.vertex_groups[assignment.group].name
                holder.vertex_groups[name].add([target_index], assignment.weight, 'REPLACE')
        mesh.update(calc_edges=False, calc_edges_loose=True)
        require(not mesh.validate(verbose=False, clean_customdata=False), 'Constructed mesh was invalid and required repair')
        assert_preserved(before, mesh)
        verified = _plan(source, target, mesh)['summary']
        require(not any(verified['add'].values()), 'Result still has incomplete rings')
        for domain, pairs in maps.items():
            for attribute in src.attributes:
                if attribute.domain != domain or attribute.name in TOPOLOGY_ATTRIBUTES:
                    continue
                destination = mesh.attributes.get(attribute.name)
                if destination is None and attribute.name.startswith('.'):
                    continue
                property_name = attribute_property(attribute)
                require(all(plain(getattr(attribute.data[si], property_name)) == plain(getattr(destination.data[ti], property_name)) for si, ti in pairs), f'Restored attribute {attribute.name} does not match source')
        for source_index, target_index in maps['POINT']:
            expected = {source.vertex_groups[g.group].name: g.weight for g in src.vertices[source_index].groups}
            actual = {target.vertex_groups[g.group].name: g.weight for g in mesh.vertices[target_index].groups}
            require(actual == expected, 'Restored vertex weights differ from the source')
        return mesh, verified
    except Exception:
        if holder:
            bpy.data.objects.remove(holder)
            holder = None
        bpy.data.meshes.remove(mesh)
        raise
    finally:
        if holder:
            bpy.data.objects.remove(holder)


class OBJECT_OT_restore_original_shoe_rings(bpy.types.Operator):
    bl_idname = 'object.restore_original_shoe_rings'
    bl_label = 'Restore Original Shoe Metal Rings'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global LAST_RESULT
        try:
            source, target = objects()
            prepared = _plan(source, target)
            LAST_RESULT = prepared['summary']
            if not any(LAST_RESULT['add'].values()):
                self.report({'INFO'}, 'All three original metal rings are already restored')
                return {'CANCELLED'}
            mesh, verified = _build_validated_copy(source, target, prepared)
            # All matching and exhaustive preservation checks finish before this swap.
            target.data = mesh
            target.update_tag()
            context.view_layer.update()
            LAST_RESULT = {**LAST_RESULT, 'after': verified['before'], 'verified_existing_geometry_uv_attributes_weights_unchanged': True}
            self.report({'INFO'}, 'Restored three original shoe rings; existing shoe edits preserved')
            return {'FINISHED'}
        except Exception as error:
            LAST_RESULT = {'error': str(error)}
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}


def apply():
    existing = getattr(bpy.types, 'OBJECT_OT_restore_original_shoe_rings', None)
    if existing:
        bpy.utils.unregister_class(existing)
    bpy.utils.register_class(OBJECT_OT_restore_original_shoe_rings)
    result = bpy.ops.object.restore_original_shoe_rings()
    return {'operator': sorted(result), 'report': LAST_RESULT}


if __name__ == '__main__':
    # Running a script without an explicit function call is strictly read-only.
    print(json.dumps(plan(), ensure_ascii=False, indent=2))
