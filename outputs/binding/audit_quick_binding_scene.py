"""Read-only scene audit; opening or saving a live scene is deliberately unsupported."""
import bpy
import json
from pathlib import Path
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).with_suffix('.json')

def vector(v):
    return [round(float(x), 9) for x in v]

def inspect_mesh(obj):
    mesh = obj.data
    counts = {g.index: 0 for g in obj.vertex_groups}
    totals = {g.index: 0.0 for g in obj.vertex_groups}
    per_vertex = []
    for vertex in mesh.vertices:
        per_vertex.append(sum(g.weight for g in vertex.groups if g.weight > 0))
        for group in vertex.groups:
            if group.weight > 0:
                counts[group.group] += 1
                totals[group.group] += group.weight
    return {
        'name': obj.name, 'data': mesh.name, 'users': mesh.users,
        'vertices': len(mesh.vertices), 'faces': len(mesh.polygons),
        'hidden': obj.hide_get(), 'hide_viewport': obj.hide_viewport,
        'parent': obj.parent.name if obj.parent else None,
        'matrix_world': [vector(r) for r in obj.matrix_world],
        'location': vector(obj.location), 'rotation': vector(obj.rotation_euler), 'scale': vector(obj.scale),
        'bounds_world': [vector(obj.matrix_world @ __import__('mathutils').Vector(c)) for c in obj.bound_box],
        'shape_keys': [{'name': k.name, 'value': k.value} for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
        'modifiers': [{
            'name': m.name, 'type': m.type, 'enabled': m.show_viewport,
            **({'armature': m.object.name if m.object else None, 'vertex_groups': m.use_vertex_groups, 'preserve_volume': m.use_deform_preserve_volume} if m.type == 'ARMATURE' else {}),
            **({'axes': list(m.use_axis), 'mirror_group_names': m.use_mirror_vertex_groups, 'mirror_object': m.mirror_object.name if m.mirror_object else None} if m.type == 'MIRROR' else {}),
        } for m in obj.modifiers],
        'groups': [{'name': g.name, 'count': counts[g.index], 'total': round(totals[g.index], 5)} for g in obj.vertex_groups],
        'unweighted_vertices': sum(s <= 0 for s in per_vertex),
        'collections': [c.name for c in obj.users_collection],
        'custom_property_names': list(obj.keys()),
    }

def inspect_rig(obj):
    return {
        'name': obj.name, 'pose_position': obj.data.pose_position,
        'matrix_world': [vector(r) for r in obj.matrix_world],
        'bones': [{'name': b.name, 'parent': b.parent.name if b.parent else None,
                   'deform': b.use_deform, 'head': vector(b.head_local), 'tail': vector(b.tail_local)}
                  for b in obj.data.bones],
        'posed_bones': [p.name for p in obj.pose.bones if max(abs(p.matrix_basis[i][j] - Matrix.Identity(4)[i][j]) for i in range(4) for j in range(4)) > 1e-6],
        'deform_rest_matrix_deviation': {p.name: max(abs(p.matrix[i][j] - p.bone.matrix_local[i][j]) for i in range(4) for j in range(4)) for p in obj.pose.bones if p.bone.use_deform},
    }

def percentiles(values):
    ordered = sorted(values)
    return {str(p): round(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))], 9) for p in (0, .5, .95, .99, 1)}

def binding_feasibility():
    body = bpy.data.objects['Cosha']
    arm = bpy.data.objects['CoshaRig']
    deform = {b.name for b in arm.data.bones if b.use_deform}
    groups = {g.index: g.name for g in body.vertex_groups if g.name in deform}
    weights = [{groups[g.group]: g.weight for g in v.groups if g.group in groups and g.weight > 0} for v in body.data.vertices]
    sums = [sum(w.values()) for w in weights]
    body.data.calc_loop_triangles()
    coords = [body.matrix_world @ v.co for v in body.data.vertices]
    triangles = [tuple(t.vertices) for t in body.data.loop_triangles]
    tree = BVHTree.FromPolygons(coords, triangles, all_triangles=True)
    result = {
        'body_deform_group_count': len(groups),
        'body_deform_weight_sums': percentiles(sums),
        'body_deform_unweighted': [{'index': i, 'world': vector(coords[i])} for i, s in enumerate(sums) if s <= 1e-8],
        'targets': {},
    }
    for name in ('Clothes', 'Stocking', 'Shoes'):
        obj = bpy.data.objects[name]
        distances = []
        unweighted = []
        touched = set()
        adjacency = [[] for _ in obj.data.vertices]
        for edge in obj.data.edges:
            a, b = edge.vertices
            adjacency[a].append(b)
            adjacency[b].append(a)
        sizes = []
        seen = set()
        for v in obj.data.vertices:
            if v.index not in seen:
                seen.add(v.index)
                queue = [v.index]
                for idx in queue:
                    for next_idx in adjacency[idx]:
                        if next_idx not in seen:
                            seen.add(next_idx)
                            queue.append(next_idx)
                sizes.append(len(queue))
            location, normal, triangle, distance = tree.find_nearest(obj.matrix_world @ v.co)
            distances.append(distance)
            ids = triangles[triangle]
            a, b, c = (coords[i] for i in ids)
            ab, ac, ap = b - a, c - a, location - a
            d00, d01, d11 = ab.dot(ab), ab.dot(ac), ac.dot(ac)
            d20, d21 = ap.dot(ab), ap.dot(ac)
            denom = d00 * d11 - d01 * d01
            wb = (d11 * d20 - d01 * d21) / denom if abs(denom) > 1e-20 else 0
            wc = (d00 * d21 - d01 * d20) / denom if abs(denom) > 1e-20 else 0
            blend = (1 - wb - wc, wb, wc)
            total = sum(sums[i] * w for i, w in zip(ids, blend))
            if total <= 1e-8:
                unweighted.append(v.index)
            for i, w in zip(ids, blend):
                if w > 1e-8:
                    touched.update(g for g, value in weights[i].items() if value > 1e-8)
        result['targets'][name] = {'nearest_body_distance': percentiles(distances),
                                    'expected_unweighted_vertices': unweighted,
                                    'touched_deform_groups': sorted(touched),
                                    'connected_islands': len(sizes), 'island_sizes': sorted(sizes)}
    return result

report = {
    'file': bpy.data.filepath, 'version': bpy.app.version_string,
    'objects': [inspect_mesh(obj) for obj in bpy.data.objects if obj.type == 'MESH'],
    'rigs': [inspect_rig(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'],
    'binding_feasibility': binding_feasibility(),
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BINDING_AUDIT_REPORT', str(OUT))
