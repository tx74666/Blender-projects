"""Read exported ring and nearby surface geometry, reporting wire intersections."""
import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(r'D:\Blender\Projects\Character\X\outputs/rig')
geometry = json.loads((OUT / 'body_detail_0530_geometry.json').read_text())
report = {'coordinate_space': geometry['coordinate_space'], 'modes': {}}
for mode in ('rest', 'pose'):
    meshes = {}
    for name, states in geometry['meshes'].items():
        data = states[mode]
        meshes[name] = BVHTree.FromPolygons([Vector(v) for v in data['vertices']], data['faces'])
    results = {}
    for role, data in geometry['rings'].items():
        points = [Vector(v) for v in data[mode]]
        results[role] = {}
        for name, tree in meshes.items():
            hits = []
            nearest = []
            for i, (a, b) in enumerate(data['edges']):
                delta = points[b] - points[a]
                hit = tree.ray_cast(points[a], delta.normalized(), delta.length)[0]
                if hit is not None:
                    hits.append({'edge': i, 'position': list(hit)})
                for step in range(17):
                    point = points[a].lerp(points[b], step / 16)
                    location, normal, index, distance = tree.find_nearest(point)
                    if location is not None:
                        nearest.append((distance, (point-location).dot(normal)))
            results[role][name] = {'crossing_count': len(hits), 'hits': hits,
                'minimum_distance': min(value[0] for value in nearest),
                'minimum_signed_distance': min(value[1] for value in nearest),
                'maximum_signed_distance': max(value[1] for value in nearest),
                'negative_nearest_samples': sum(value[1] < -1e-7 for value in nearest)}
    report['modes'][mode] = results
target = OUT / 'body_detail_0530_clearance.json'
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BODY_DETAIL_CLEARANCE', json.dumps(report), flush=True)
