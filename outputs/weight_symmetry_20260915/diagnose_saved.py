"""Read-only diagnosis of the user's frozen 2026-09-15 saved input."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import struct
import sys
import types

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(r"D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915")
INPUT = ROOT / "X_saved_input.blend"
EXPECTED = "5FB5B96E5C629340FEC5CC2696E0861A5C0884A1F1E03BBFEAF9C608CB96CA79"
CANONICAL = Path(r"D:\MyRepository\Blender-addons-by-Randy\addons\character_designer")
NAMES = [f"{stem}.{side}" for stem in ("upper_arm", "forearm", "hand", "shoulder") for side in ("L", "R")]

def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

assert file_hash(INPUT) == EXPECTED, "Frozen input hash changed"
pkg = types.ModuleType("diagnostic_character_designer")
pkg.__path__ = [str(CANONICAL)]
sys.modules[pkg.__name__] = pkg
spec = importlib.util.spec_from_file_location(pkg.__name__ + ".weight_symmetry", CANONICAL / "weight_symmetry.py")
ws = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ws
spec.loader.exec_module(ws)
bpy.ops.wm.open_mainfile(filepath=str(INPUT), load_ui=False)

def digest_geometry(obj):
    h = hashlib.sha256()
    for v in obj.data.vertices:
        h.update(struct.pack("<3f", *v.co))
    for e in obj.data.edges:
        h.update(struct.pack("<2I", *e.vertices))
    for p in obj.data.polygons:
        h.update(struct.pack("<I", len(p.vertices)))
        h.update(struct.pack("<" + "I" * len(p.vertices), *p.vertices))
    if obj.data.shape_keys:
        for block in obj.data.shape_keys.key_blocks:
            h.update(block.name.encode())
            for v in block.data:
                h.update(struct.pack("<3f", *v.co))
    return h.hexdigest()

def digest_groups(obj):
    return hashlib.sha256(repr(ws._capture_vertex_groups(obj)).encode()).hexdigest()

def segment_details(co, a, b):
    ab = b - a
    fraction = (co-a).dot(ab) / ab.length_squared if ab.length_squared else 0.0
    closest = a + min(1.0, max(0.0, fraction)) * ab
    return {"distance": (co-closest).length, "fraction": fraction, "segment_length": ab.length}

meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups.get("upper_arm.L")]
report = {"input": str(INPUT), "input_sha256": EXPECTED, "canonical_algorithm_sha256": file_hash(CANONICAL / "weight_symmetry.py"), "candidate_meshes": [{"name": o.name, "vertices": len(o.data.vertices)} for o in meshes]}
active = bpy.context.view_layer.objects.active
assert active in meshes, "Saved active Mesh must own the source group"
obj = active
arm = ws._armature_for_mesh(obj, "upper_arm.L", "upper_arm.R")
verts = obj.data.vertices
coords = [v.co.copy() for v in verts]
before_geometry = digest_geometry(obj)
before_groups = digest_groups(obj)
snap = ws._capture_vertex_groups(obj)
state = ws._state_map(snap)
tol = ws._automatic_tolerance(obj)
transform = obj.matrix_world.inverted_safe() @ arm.matrix_world
bones = {b.name: (transform @ b.head_local, transform @ b.tail_local) for b in arm.data.bones if b.use_deform}
adj = [set() for _ in verts]
for edge in obj.data.edges:
    a,b = edge.vertices
    adj[a].add(b)
    adj[b].add(a)
obj.data.calc_loop_triangles()
tris = [tuple(t.vertices) for t in obj.data.loop_triangles]

def nearest_bones(co, count=6):
    return sorted(({"name": name, **segment_details(co, a, b)} for name,(a,b) in bones.items()), key=lambda d: d["distance"])[:count]

def local_record(index, name, side):
    co = coords[index]
    weights = {obj.vertex_groups[g.group].name: float(g.weight) for g in verts[index].groups if g.weight > ws.WEIGHT_EPSILON}
    return {"vertex": index, "local": list(co), "weight": weights.get(name, 0), "side": "source" if co.x*side>tol else ("opposite" if co.x*side < -tol else "center"), "all_positive_weights": weights, "nearest_bones": nearest_bones(co), "source_bone_relation": segment_details(co, *bones[name])}

def surface_for(side):
    eligible = [t for t in tris if all(coords[i].x*side >= -tol for i in t) and any(coords[i].x*side > tol for i in t)]
    return BVHTree.FromPolygons(coords, eligible, all_triangles=True), eligible

surfaces = {side: surface_for(side) for side in (-1,1)}

def barycentric(point,a,b,c):
    v0,v1,v2=b-a,c-a,point-a
    d00,d01,d11,d20,d21=v0.dot(v0),v0.dot(v1),v1.dot(v1),v2.dot(v0),v2.dot(v1)
    denom=d00*d11-d01*d01
    if abs(denom)<1e-24:
        return None
    v=(d11*d20-d01*d21)/denom
    w=(d00*d21-d01*d20)/denom
    return [1-v-w,v,w]

def surface_record(point, side, name):
    bvh,triangles = surfaces[side]
    co,normal,tri_index,distance=bvh.find_nearest(point)
    if co is None:
        return None
    triangle=triangles[tri_index]
    bary=barycentric(co,*(coords[i] for i in triangle))
    weightmap=ws._weight_map(state.get(name))
    return {"distance": distance, "point": list(co), "triangle": triangle, "barycentric": bary, "triangle_weights": [weightmap.get(i,0) for i in triangle], "interpolated_weight": sum(c*weightmap.get(i,0) for c,i in zip(bary,triangle)) if bary else None, "nearest_bones": nearest_bones(co), "bone_relation": segment_details(co,*bones[name])}

group_reports={}
for name in NAMES:
    if name not in state or name not in bones:
        group_reports[name]={"exists": False}
        continue
    opposite=ws._strict_opposite_name(name)
    side=ws._bone_source_side(obj,arm,name,opposite,tol)
    si,ti,ci=ws._classify_mesh_halves(obj,side,tol)
    weights=ws._weight_map(state[name])
    support={i for i,w in weights.items() if w>ws.WEIGHT_EPSILON}
    components=[]
    unvisited=set(support)
    while unvisited:
        start=min(unvisited)
        unvisited.remove(start)
        component=[start]
        pending=[start]
        while pending:
            current=pending.pop()
            next_items=adj[current]&unvisited
            unvisited.difference_update(next_items)
            pending.extend(next_items)
            component.extend(next_items)
        component.sort()
        source_count=sum(coords[i].x*side>tol for i in component)
        target_count=sum(coords[i].x*side < -tol for i in component)
        center_count=len(component)-source_count-target_count
        is_wrong=target_count==len(component)
        components.append({"vertices": component, "count": len(component), "weight_sum": sum(weights[i] for i in component), "max_weight": max(weights[i] for i in component), "source_count": source_count, "opposite_count": target_count, "center_count": center_count, "entirely_wrong_side": is_wrong, "bbox": [[min(coords[i][a] for i in component) for a in range(3)],[max(coords[i][a] for i in component) for a in range(3)]], "vertex_weights": [[i,weights[i]] for i in component], "wrong_side_vertex_details": [local_record(i,name,side) for i in component] if is_wrong else []})
    tree=KDTree(len(ti))
    for i in ti:
        tree.insert(coords[i],i)
    tree.balance()
    support_on_source=tuple(i for i in si if i in support)
    misses=[]
    ambiguous=[]
    exact=[]
    used=set()
    for i in support_on_source:
        reflected=coords[i].copy()
        reflected.x=-reflected.x
        hits=sorted(tree.find_range(reflected,tol),key=lambda item:(item[2],item[1]))
        if not hits:
            near_co,near_i,near_distance=tree.find(reflected)
            record=local_record(i,name,side)
            record.update({"reflected_local": list(reflected), "nearest_reflected_vertex": near_i, "nearest_reflected_vertex_local": list(near_co), "nearest_reflected_vertex_distance": near_distance, "opposite_surface": surface_record(reflected,-side,opposite), "neighbors": sorted(adj[i])})
            misses.append(record)
        elif len(hits)!=1 or hits[0][1] in used:
            ambiguous.append(i)
        else:
            used.add(hits[0][1])
            exact.append((i,hits[0][1]))
    try:
        ws._spatial_pairs(obj,support_on_source,ti,tol)
        algorithm_result="ok"
    except Exception as error:
        algorithm_result=f"{type(error).__name__}: {error}"
    # Each destination vertex samples the reflected source surface. Record only
    # target samples with this group's nonzero interpolated weight.
    sampling=[]
    for i in ti:
        reflected=coords[i].copy()
        reflected.x=-reflected.x
        sample=surface_record(reflected,side,name)
        if sample and (sample["interpolated_weight"] or 0)>ws.WEIGHT_EPSILON:
            sampling.append({"target_vertex": i, "target_local": list(coords[i]), "source_surface": sample, "current_target_weight": ws._weight_map(state.get(opposite)).get(i,0), "exact_paired_target": i in used})
    group_reports[name]={"bone_side_sign": side, "bone_head": list(bones[name][0]), "bone_tail": list(bones[name][1]), "all_membership_count": len(weights), "positive_support_count": len(support), "positive_source_count": len(support&set(si)), "positive_opposite_count": len(support&set(ti)), "positive_center_count": len(support&set(ci)), "components": components, "wrong_side_island_count": sum(c["entirely_wrong_side"] for c in components), "wrong_side_island_vertex_count": sum(c["count"] for c in components if c["entirely_wrong_side"]), "canonical_spatial_result": algorithm_result, "exact_pair_count": len(exact), "unmatched_count": len(misses), "unmatched": misses, "ambiguous": ambiguous, "destination_sampling_nonzero_count": len(sampling), "destination_samples_without_exact_pair": [s for s in sampling if not s["exact_paired_target"]], "destination_sampling_max_distance": max((s["source_surface"]["distance"] for s in sampling),default=0)}
report.update({"mesh": obj.name, "armature": arm.name, "vertex_count": len(verts), "edge_count": len(obj.data.edges), "polygon_count": len(obj.data.polygons), "tolerance": tol, "groups": group_reports, "geometry_digest_before": before_geometry, "geometry_digest_after": digest_geometry(obj), "groups_digest_before": before_groups, "groups_digest_after": digest_groups(obj), "input_sha256_after": file_hash(INPUT)})
assert report["geometry_digest_before"]==report["geometry_digest_after"]
assert report["groups_digest_before"]==report["groups_digest_after"]
assert report["input_sha256_after"]==EXPECTED
(ROOT/"saved_input_diagnostic.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
summary={"mesh": obj.name, "tolerance": tol, "groups": {name:{key:data.get(key) for key in ("positive_support_count","positive_source_count","positive_opposite_count","positive_center_count","wrong_side_island_count","wrong_side_island_vertex_count","unmatched_count","canonical_spatial_result","destination_sampling_max_distance")} for name,data in group_reports.items()}, "geometry_and_weights_unchanged": True}
print(json.dumps(summary,indent=2))
