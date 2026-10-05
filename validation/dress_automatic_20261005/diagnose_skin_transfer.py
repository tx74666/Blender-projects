"""Read-only native skin-transfer diagnostics on one sealed QA candidate.

Launch only a factory background child, with its TEMP/TMP isolated by the caller:
  --background --factory-startup --disable-autoexec --threads 1 --python <file>
  -- --input <sealed QA.blend> --output <new diagnostic directory> --frame 25
     [--frames 1 7 25 30] [--render] [--probe]

Only JSON and optional native Workbench PNGs are written. No blend, preference,
weight, rig, constraint, Action or cache is saved/reset/baked. Rendering uses
native evaluated Body/Dress geometry snapshots in a disposable empty scene.
This is a QA-copy diagnostic, not artist/production acceptance or a Body sign
claim. Open/coplanar/degenerate surfaces have explicit limits.
"""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import struct
import sys
import time
import traceback

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree


HERE = Path(__file__).resolve().parent
REPOSITORY = Path(r"D:\MyRepository\Blender-addons-by-Randy")
VALIDATION = Path(r"D:\Blender\Projects\Character\X\Validation\dress_automatic_20261005")
sys.path[:0] = [str(HERE), str(REPOSITORY / "addons")]
import validate_real_dress as qa
import character_designer
from character_designer import skirt_rig as skirt, skirt_physics as physics
from character_designer import skirt_topology as topology, skirt_original_mode


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=25, help="Render focus frame")
    parser.add_argument("--frames", nargs="+", type=int, default=[1, 7, 25, 30])
    parser.add_argument("--source", help="Exact owned Dress source if the QA copy has several")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--probe", action="store_true", help="Temporary fitted cage skinned to existing DEF bones")
    parser.add_argument("--body-vertex-limit", type=int, default=100000)
    parser.add_argument("--triangle-pair-limit", type=int, default=2000)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.input, args.output = args.input.resolve(), args.output.resolve()
    require(args.input.is_file() and args.input.suffix.casefold() == ".blend", "Input must be a saved QA blend")
    require(args.input.is_relative_to(VALIDATION) and args.input.name.startswith("Cosha_Dress_QA_"),
            "Refusing an artist or non-QA input; use the existing Validation candidate")
    require(args.output.is_relative_to(VALIDATION) and args.output != VALIDATION
            and args.output != args.input.parent, "Use a separate dedicated Validation output directory")
    require(args.body_vertex_limit >= 1000 and 1 <= args.triangle_pair_limit <= 20000, "Invalid diagnostic budgets")
    args.frames = sorted(set(args.frames + [args.frame]))
    return args


def matrix(value):
    return [list(row) for row in value]


def vector(value):
    return list(value)


def json_content(value, path="$", conversions=None):
    """Convert only declared numeric mathutils types; reject unknown wrappers."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Matrix):
        if conversions is not None:
            conversions.append({"path":path,"native_type":"Matrix"})
        return [[json_content(component,f"{path}[{row_index}][{column_index}]",conversions)
                 for column_index,component in enumerate(row)] for row_index,row in enumerate(value)]
    if isinstance(value, (Vector, Euler, Quaternion)):
        if conversions is not None:
            conversions.append({"path":path,"native_type":type(value).__name__})
        return [json_content(component,f"{path}[{index}]",conversions) for index,component in enumerate(value)]
    if isinstance(value, dict):
        if not all(isinstance(key,str) for key in value):
            raise TypeError(f"Unsupported diagnostic dictionary key at {path}; string keys are required")
        return {key:json_content(item,path+"["+json.dumps(key)+"]",conversions) for key,item in value.items()}
    if isinstance(value, (tuple,list)):
        return [json_content(item,f"{path}[{index}]",conversions) for index,item in enumerate(value)]
    raise TypeError(f"Unsupported diagnostic type at {path}: {type(value).__module__}.{type(value).__name__}")


def source_manifest():
    files = [path for path in (REPOSITORY / "addons/character_designer").rglob("*")
             if path.is_file() and "__pycache__" not in path.parts
             and not any(part.startswith(".") for part in path.relative_to(REPOSITORY).parts)
             and path.suffix not in {".pyc", ".pyo"}]
    files.extend((Path(qa.__file__), Path(__file__)))
    return {str(path): qa.file_state(path) for path in sorted(files)}


def mesh_snapshot(obj, graph):
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    try:
        mesh.calc_loop_triangles()
        names = {group.index: group.name for group in obj.vertex_groups}
        return {"object": obj.name, "points": [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices],
                "faces": [tuple(face.vertices) for face in mesh.polygons],
                "edges": [tuple(edge.vertices) for edge in mesh.edges],
                "triangles": [tuple(triangle.vertices) for triangle in mesh.loop_triangles],
                "weights": [[{"index": item.group, "name": names.get(item.group), "weight": item.weight}
                             for item in vertex.groups] for vertex in mesh.vertices],
                "matrix_world": matrix(evaluated.matrix_world)}
    finally:
        evaluated.to_mesh_clear()


def channels(pose):
    return {"rotation_mode": pose.rotation_mode, "location": vector(pose.location),
            "rotation_euler": vector(pose.rotation_euler), "rotation_quaternion": vector(pose.rotation_quaternion),
            "rotation_axis_angle": vector(pose.rotation_axis_angle), "scale": vector(pose.scale),
            "custom": {key: qa.custom_content(value) for key, value in pose.items()}}


def constraint_content(constraint):
    values = qa.simple_rna(constraint)
    values["observed_fields"] = {name: getattr(constraint, name, None) for name in
        ("mix_mode", "influence", "mute", "owner_space", "target_space", "head_tail", "track_axis")}
    values["missing_fields"] = [name for name in ("mix_mode", "head_tail", "track_axis") if not hasattr(constraint, name)]
    return values


def bone_content(rig, evaluated, name):
    raw, posed = rig.pose.bones[name], evaluated.pose.bones[name]
    rest = raw.bone
    rest_head, rest_tail = rig.matrix_world @ rest.head_local, rig.matrix_world @ rest.tail_local
    head, tail = evaluated.matrix_world @ posed.head, evaluated.matrix_world @ posed.tail
    return {"name": name, "parent": rest.parent.name if rest.parent else None,
            "connect": rest.use_connect, "inherit_scale": rest.inherit_scale,
            "inherit_rotation": rest.use_inherit_rotation, "use_deform": rest.use_deform,
            "rest_matrix_rig": matrix(rest.matrix_local), "pose_matrix_rig": matrix(posed.matrix),
            "pose_matrix_world": matrix(evaluated.matrix_world @ posed.matrix),
            "basis_matrix_rig": matrix(raw.matrix_basis), "evaluated_basis_matrix_rig": matrix(posed.matrix_basis),
            "rest_head_rig": vector(rest.head_local), "rest_tail_rig": vector(rest.tail_local),
            "rest_head_world_at_current_object_transform": vector(rest_head),
            "rest_tail_world_at_current_object_transform": vector(rest_tail),
            "eval_head_world": vector(head), "eval_tail_world": vector(tail),
            "rest_length_rig": rest.length, "rest_length_world_at_current_object_transform": (rest_tail-rest_head).length,
            "eval_length_rig": (posed.tail-posed.head).length, "eval_length_world": (tail-head).length,
            "channels": channels(raw), "evaluated_channels": channels(posed),
            "constraints": [constraint_content(item) for item in raw.constraints],
            "evaluated_constraints": [constraint_content(item) for item in posed.constraints]}


def weighted_target(proxy, cage, group_name):
    group = proxy.vertex_groups.get(group_name)
    if group is None:
        return {"available": False, "reason": "Exact native target group is missing", "group": group_name}
    members = [{"vertex": index, "weight": assignment["weight"], "world": vector(cage["points"][index])}
               for index, assignments in enumerate(cage["weights"]) for assignment in assignments
               if assignment["index"] == group.index and assignment["weight"] > 0]
    total = sum(item["weight"] for item in members)
    if not total:
        return {"available": False, "reason": "No positive native evaluated target weights", "group": group_name}
    center = sum((Vector(item["world"])*item["weight"] for item in members), Vector()) / total
    return {"available": True, "group": group_name, "group_index": group.index,
            "weight_sum": total, "members": members, "weighted_world_center": vector(center),
            "single_native_target_vertex": members[0]["vertex"] if len(members) == 1 else None,
            "single_native_target_world": members[0]["world"] if len(members) == 1 else None,
            "definition": "Actual evaluated deform weights; a weighted center is not assumed to be one vertex"}


def residual(evaluated, bone_name, target, meters):
    bone = evaluated.pose.bones[bone_name]
    head, tail = evaluated.matrix_world @ bone.head, evaluated.matrix_world @ bone.tail
    aim, shaft = target-head, tail-head
    length = shaft.length
    axis_y = (evaluated.matrix_world @ bone.matrix).to_3x3().col[1].normalized()
    if aim.length <= 1.e-12:
        return {"available": False, "reason": "Target coincides with native bone head"}
    direction = aim.normalized()
    error = tail-target
    along = error.dot(direction)
    cross = error-direction*along
    cosine = max(-1., min(1., axis_y.dot(direction)))
    return {"available": True, "axis_y_world": vector(axis_y),
            "axis_y_to_exact_target_angle_rad": math.acos(cosine),
            "head_to_target_world": vector(aim), "head_to_target_length_m": aim.length*meters,
            "bone_world_length_m": length*meters, "target_distance_minus_bone_length_m": (aim.length-length)*meters,
            "tail_minus_target_world": vector(error), "tail_to_target_error_m": error.length*meters,
            "tail_residual_along_m": along*meters, "tail_residual_cross_world": vector(cross),
            "tail_residual_cross_m": cross.length*meters}


def curve_content(obj, graph):
    evaluated = obj.evaluated_get(graph)
    def points(curve_data, world):
        values = []
        for spline in curve_data.splines:
            native = list(spline.points)
            values.append({"type": spline.type, "point_count": len(native),
                "points_local_homogeneous": [list(point.co) for point in native],
                "native_data_points_world": [vector(world @ Vector(point.co[:3])) for point in native],
                "bezier_point_count": len(spline.bezier_points)})
        return values
    result = {"object": obj.name, "original_splines": points(obj.data, obj.matrix_world),
              "definition": "Native to_curve(apply_modifiers=True) deform-modified control points; also native evaluated tessellation",
              "native_api_source": "https://github.com/blender/blender/blob/v5.1.0/source/blender/makesrna/intern/rna_object_api.cc#L1018",
              "modifiers": [qa.simple_rna(item) for item in obj.modifiers]}
    native_curve = obj.to_curve(depsgraph=graph, apply_modifiers=True)
    try:
        require(native_curve is not None, "Native deform-modified Curve control points are unavailable")
        result["evaluated_splines"] = points(native_curve, evaluated.matrix_world)
    finally:
        obj.to_curve_clear()
    mesh = evaluated.to_mesh()
    try:
        result["native_evaluated_tessellation_world"] = [vector(evaluated.matrix_world @ item.co) for item in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()
    return result


def vertex_content(final, index, roles):
    weights = [{**assignment, "role": roles.get(assignment["name"], "native_or_other")}
               for assignment in final["weights"][index]]
    return {"evaluated_vertex_index": index, "world": vector(final["points"][index]), "evaluated_weights": weights,
            "index_definition": "Native evaluated mesh index; no original-vertex correspondence is assumed"}


def nearest_content(collider, point, meters):
    location, normal, triangle, distance = collider.tree.find_nearest(point)
    require(location is not None and math.isfinite(distance), "Native nearest-surface query failed")
    return {"native_closest_world": vector(location), "native_normal_world": vector(normal),
            "native_unsigned_distance_m": distance*meters, "triangle_index": triangle,
            "triangle_vertex_indices": list(collider.triangles[triangle]),
            "triangle_world": [vector(collider.points[index]) for index in collider.triangles[triangle]]}


def collider_diagnostics(final, cage, record, graph, meters, roles, epsilon):
    result = {}
    for name in record["physics"]["colliders"]:
        obj = bpy.data.objects[name]
        collider = qa.ClosedCollider(obj, graph, epsilon)
        signed = [(collider.signed_distance(final["points"][index])*meters, index) for index in final["free_indices"]]
        worst = []
        for distance, index in sorted(signed)[:32]:
            if distance >= 0:
                break
            item = vertex_content(final, index, roles)
            item.update(signed_distance_m=distance, penetration_m=-distance,
                        closest_surface=nearest_content(collider, final["points"][index], meters))
            worst.append(item)
        result[name] = {"binding_group": obj.vertex_groups[0].name,
            "sign_method": "proved_convex_normal" if collider.convex else "three_ray_parity",
            "final_free": qa.collision_metrics(final["points"], collider, meters, final["free_indices"]),
            "final_all": qa.collision_metrics(final["points"], collider, meters),
            "cloth": qa.collision_metrics(cage["points"], collider, meters),
            "cloth_surface_samples_and_edges": proxy_surface(cage, collider, meters, epsilon),
            "worst_penetrated_free_vertices": worst}
    return result


def proxy_surface(cage, collider, meters, epsilon):
    """Samples are finite evidence; native BVH edge hits are tested geometrically."""
    result = {"surface_separation_claim": False, "bvh_overlap_is_not_crossing": True}
    for label, indices in (("triangle_centroids", cage["triangles"]), ("edge_midpoints", cage["edges"])):
        samples = [sum((cage["points"][index] for index in vertices), Vector())/len(vertices)
                   for vertices in indices]
        distances = [collider.signed_distance(point)*meters for point in samples]
        worst = [{"sample_index": index, "native_vertex_indices": list(indices[index]),
                  "world": vector(samples[index]), "signed_distance_m": distance,
                  "closest_surface": nearest_content(collider, samples[index], meters)}
                 for distance,index in sorted((distance,index) for index,distance in enumerate(distances))[:32]
                 if distance < 0]
        result[label] = {"sampled_points": len(samples), "minimum_signed_distance_m": min(distances, default=None),
                         "inside_sample_count": sum(distance < 0 for distance in distances),
                         "maximum_sample_penetration_m": max(0.,-min(distances,default=0.)), "worst_inside_samples": worst,
                         "limitation": "Finite samples do not establish triangle separation"}
    crossings, unresolved, capped = [], [], []
    crossing_count = 0
    for edge_index,(first,second) in enumerate(cage["edges"]):
        start,end = cage["points"][first],cage["points"][second]
        length = (end-start).length
        if length <= epsilon:
            unresolved.append({"edge":edge_index,"reason":"Degenerate edge"})
            continue
        direction = (end-start)/length
        travelled = 0.
        for hit_index in range(16):
            location,normal,triangle,distance = collider.tree.ray_cast(start+direction*travelled,direction,length-travelled)
            if location is None: break
            vertices = collider.triangles[triangle]
            exact = segment_triangle(start,end,[collider.points[index] for index in vertices],epsilon)
            observed = {"edge":edge_index,"edge_vertices":[first,second],"edge_world":[vector(start),vector(end)],
                        "native_hit_world":vector(location),"collider_triangle":triangle,
                        "collider_triangle_vertices":list(vertices),"native_direction_dot_normal":direction.dot(normal),
                        "exact_segment_triangle":exact}
            if exact is not None and exact["strict_crossing"]:
                crossing_count += 1
                if len(crossings) < 64: crossings.append(observed)
            elif len(unresolved) < 64:
                unresolved.append({**observed,"reason":"Boundary, coplanar or unresolved finite segment hit"})
            travelled += distance+epsilon*2
            if travelled >= length-epsilon: break
        else:
            capped.append(edge_index)
    result["finite_native_edge_crossings"] = {"tested_edges":len(cage["edges"]),
        "actual_crossing_hit_count":crossing_count,"crossing_examples":crossings,
        "unresolved_examples":unresolved,"hit_limit_per_edge":16,"hit_limit_reached_edges":capped,
        "definition":"Native finite BVH ray hit verified by nonparallel strict-interior segment/triangle intersection",
        "limitation":"Crossings prove contact with collider surface; capped, boundary and coplanar cases stay unresolved"}
    return result


def framing(rig, record, graph):
    # This existing helper validates the saved native LEG inventory/FK and does
    # not switch modes, write Actions, or author another representative input.
    legs, _axes, height = qa.body_inputs(rig, record)
    evaluated = rig.evaluated_get(graph)
    up = evaluated.matrix_world.to_3x3().col[2].normalized()
    right = evaluated.matrix_world.to_3x3().col[0]
    right = (right-up*right.dot(up)).normalized()
    forward = up.cross(right).normalized()
    waist_name = record["controls"]["waist"]
    waist = evaluated.matrix_world @ evaluated.pose.bones[waist_name].head
    knees = {side: evaluated.matrix_world @ evaluated.pose.bones[item["chain"][1]].head for side, item in legs.items()}
    depth = min((point-waist).dot(up) for point in knees.values())
    require(depth < 0 and height > 0, "Proved knees do not lie below the posed waist")
    lower, upper = depth-height*.02, height*.08
    return {"waist": waist, "knees": knees, "up": up, "right": right, "forward": forward,
            "lower": lower, "upper": upper, "height": height, "waist_bone": waist_name,
            "leg_chains": {side: list(item["chain"]) for side, item in legs.items()}}


def segment_triangle(start, end, triangle, epsilon):
    """Finite nonparallel segment/triangle intersection; boundary is unresolved."""
    a, b, c = triangle
    direction, first, second = end-start, b-a, c-a
    p = direction.cross(second)
    determinant = first.dot(p)
    scale = direction.length*first.length*second.length
    if abs(determinant) <= max(1.e-30, scale*1.e-10):
        return None
    offset = start-a
    u = offset.dot(p)/determinant
    q = offset.cross(first)
    v, along = direction.dot(q)/determinant, second.dot(q)/determinant
    tolerance = epsilon/max(direction.length, first.length, second.length, epsilon)
    if not (-tolerance <= along <= 1+tolerance and u >= -tolerance and v >= -tolerance and u+v <= 1+tolerance):
        return None
    strict = tolerance < along < 1-tolerance and u > tolerance and v > tolerance and u+v < 1-tolerance
    return {"world": vector(start+direction*along), "strict_crossing": strict,
            "segment_parameter": along, "triangle_barycentric": [1-u-v, u, v]}


def triangle_crossings(final, body_mesh, bounds, limit, epsilon):
    def in_band(points, triangle):
        projections = [(points[index]-bounds["waist"]).dot(bounds["up"]) for index in triangle]
        return min(projections) <= bounds["upper"] and max(projections) >= bounds["lower"]
    free = set(final["free_indices"])
    dress_ids = [index for index, triangle in enumerate(final["triangles"])
                 if any(vertex in free for vertex in triangle) and in_band(final["points"], triangle)]
    body_ids = [index for index, triangle in enumerate(body_mesh["triangles"])
                if in_band(body_mesh["points"], triangle)]
    result = {"body_inside_outside_claim": False, "definition": "Finite triangle-edge/triangle crossings in proved waist-knee band",
              "dress_region_triangles": len(dress_ids), "body_region_triangles": len(body_ids), "candidate_limit": limit,
              "epsilon_world": epsilon, "crossing_pairs": [], "coplanar_unresolved": [], "degenerate_unresolved": [],
              "boundary_unresolved": [], "exact_tested_pairs": 0}
    if not dress_ids or not body_ids:
        return {**result, "status": "skipped_empty_region"}
    dress_tree = BVHTree.FromPolygons(final["points"], [final["triangles"][index] for index in dress_ids], all_triangles=True)
    body_tree = BVHTree.FromPolygons(body_mesh["points"], [body_mesh["triangles"][index] for index in body_ids], all_triangles=True)
    pairs = dress_tree.overlap(body_tree)
    result["bvh_candidate_pairs"] = len(pairs)
    if len(pairs) > limit:
        return {**result, "status": "skipped_candidate_limit", "reason": "No exact crossings asserted for an over-budget candidate set"}
    for dress_index, body_index in pairs:
        di, bi = dress_ids[dress_index], body_ids[body_index]
        first = [final["points"][index] for index in final["triangles"][di]]
        second = [body_mesh["points"][index] for index in body_mesh["triangles"][bi]]
        na, nb = (first[1]-first[0]).cross(first[2]-first[0]), (second[1]-second[0]).cross(second[2]-second[0])
        pair = {"dress_triangle": di, "body_triangle": bi,
                "dress_vertices": list(final["triangles"][di]), "body_vertices": list(body_mesh["triangles"][bi])}
        if min(na.length, nb.length) <= epsilon*epsilon:
            result["degenerate_unresolved"].append(pair)
            continue
        na.normalize(); nb.normalize()
        if na.cross(nb).length <= 1.e-8 and max(abs((point-first[0]).dot(na)) for point in second) <= epsilon:
            result["coplanar_unresolved"].append(pair)
            continue
        result["exact_tested_pairs"] += 1
        hits = []
        for triangle, other in ((first, second), (second, first)):
            for index in range(3):
                hit = segment_triangle(triangle[index], triangle[(index+1)%3], other, epsilon)
                if hit and bounds["lower"] <= (Vector(hit["world"])-bounds["waist"]).dot(bounds["up"]) <= bounds["upper"]:
                    hits.append(hit)
        if any(hit["strict_crossing"] for hit in hits):
            result["crossing_pairs"].append({**pair, "points": hits})
        elif hits:
            result["boundary_unresolved"].append({**pair, "points": hits})
    result.update(status="measured", actual_crossing_pair_count=len(result["crossing_pairs"]),
                  limitation="Open Body permitted; no volume sign. Coplanar, degenerate and boundary pairs remain unresolved; no-intersection acceptance is not claimed")
    return result


def body_diagnostics(body, graph, final, bounds, args, meters, roles, epsilon):
    body_mesh = mesh_snapshot(body, graph)
    if len(body_mesh["points"]) > args.body_vertex_limit:
        return {"measured": False, "reason": "Native evaluated Body exceeds vertex budget"}, None
    tree = BVHTree.FromPolygons(body_mesh["points"], body_mesh["triangles"], all_triangles=True)
    selected = [index for index in final["free_indices"]
                if bounds["lower"] <= (final["points"][index]-bounds["waist"]).dot(bounds["up"]) <= bounds["upper"]]
    nearest = []
    for index in selected:
        point = final["points"][index]
        hit, normal, triangle, distance = tree.find_nearest(point)
        if hit is not None:
            nearest.append({"vertex": index, "closest_world": vector(hit), "normal_world": vector(normal),
                "triangle": triangle, "unsigned_distance_m": distance*meters,
                "unproven_nearest_normal_offset_m": (point-hit).dot(normal)*meters})
    incidence = Counter(tuple(sorted((a,b))) for tri in body_mesh["triangles"] for a,b in zip(tri,tri[1:]+tri[:1]))
    def enrich(items):
        return [{**item, **vertex_content(final, item["vertex"], roles)} for item in items]
    result = {"measured": True, "registered_pointer_only": True, "body": body.name,
        "evaluated_vertices": len(body_mesh["points"]), "sampled_free_vertices": len(selected),
        "open_or_nonmanifold_triangle_edges": sum(count != 2 for count in incidence.values()),
        "body_inside_outside_claim": False, "body_penetration_from_normal_claim": False,
        "minimum_unsigned_distance_m": min((item["unsigned_distance_m"] for item in nearest), default=None),
        "minimum_unproven_nearest_normal_offset_m": min((item["unproven_nearest_normal_offset_m"] for item in nearest), default=None),
        "nearest_free_vertices": enrich(sorted(nearest, key=lambda item: item["unsigned_distance_m"])[:32]),
        "most_negative_unproven_normal_vertices": enrich(sorted(nearest, key=lambda item: item["unproven_nearest_normal_offset_m"])[:32]),
        "limitation": "Unsigned distance and nearest normal cannot prove Body penetration or collider coverage",
        "triangle_crossings": triangle_crossings(final, body_mesh, bounds, args.triangle_pair_limit, epsilon)}
    return result, body_mesh


def fitted_probe(source, rig, record, temporary_objects, temporary_meshes):
    skin = source.modifiers.get(record.get("modifier", ""))
    require(skin is not None and skin.type == "ARMATURE" and skin.object == rig, "Saved native Dress Armature modifier is missing")
    require(skin.use_vertex_groups and not skin.use_bone_envelopes and not skin.vertex_group and not skin.use_multi_modifier,
            "Probe does not guess envelope/mask/multi-modifier skin semantics")
    columns, rows = record["physics"]["columns"], record["physics"]["rows"]
    segments, chains = record["segment_count"], record["chain_count"]
    points = [topology.sample_fit(record["fit"], row/(rows-1), math.tau*col/columns)
              for row in range(rows) for col in range(columns)]
    faces = [(row*columns+col, row*columns+(col+1)%columns,
              (row+1)*columns+(col+1)%columns, (row+1)*columns+col)
             for row in range(rows-1) for col in range(columns)]
    mesh = bpy.data.meshes.new("Skin Transfer QA Probe Mesh")
    temporary_meshes.append(mesh)
    mesh.from_pydata(points, [], faces); mesh.update()
    obj = bpy.data.objects.new("Skin Transfer QA Fitted Probe", mesh)
    temporary_objects.append(obj)
    bpy.context.scene.collection.objects.link(obj)
    obj.hide_render = True
    obj.parent = rig
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = skirt.fit_rest_world(source, record)
    groups = {}
    for name in [record["controls"]["waist"]]+[name for chain in record["chains"] for name in chain["def"]]:
        groups[name] = obj.vertex_groups.new(name=name)
    for row in range(rows):
        along = topology._longitudinal_weights(row/(rows-1), segments)
        for col in range(columns):
            phase = col*chains/columns
            chain = int(math.floor(phase)); fraction = topology._smoothstep(phase-chain)
            combined = defaultdict(float)
            for ci, angular in ((chain%chains,1-fraction),((chain+1)%chains,fraction)):
                for segment, longitudinal in along:
                    name = record["controls"]["waist"] if segment == -1 else record["chains"][ci]["def"][segment]
                    combined[name] += angular*longitudinal
            active = {name: value for name,value in combined.items() if value > 1.e-12}
            total = sum(active.values())
            for name,value in active.items():
                groups[name].add([row*columns+col], value/total, "REPLACE")
    armature = obj.modifiers.new("Existing DEF native skin probe", "ARMATURE")
    armature.object = rig
    armature.use_deform_preserve_volume = skin.use_deform_preserve_volume
    armature.use_vertex_groups = True
    armature.use_bone_envelopes = False
    return obj, {"requested": True, "created": True, "temporary_only": True, "points": len(points),
        "source_preserve_volume": skin.use_deform_preserve_volume, "binding": "fit_rest_world, never fit_world",
        "weights": "Canonical _longitudinal_weights and angular _smoothstep, normalized exactly as analyze_skirt",
        "limitation": "Fitted shell through existing DEF skin only; excludes Dress contour, Shape Keys and Subsurf"}


def native_render(args, dress_mesh, body_mesh, bounds):
    result = {"requested": True, "success": False, "engine": "BLENDER_WORKBENCH", "frame": args.frame,
              "provenance": "Geometry snapshots from actual native evaluated Body/Dress at this frame; no invented deformation",
              "resolution": [512,512], "views": {}, "source_visibility_modified": False,
              "native_geometry": {data["object"]:{"vertices":len(data["points"]),"faces":len(data["faces"]),
                  "world_geometry_sha256":qa.digest({"points":[vector(point) for point in data["points"]],"faces":data["faces"]})}
                  for data in (dress_mesh,body_mesh)}}
    scene = None; objects = []; meshes = []; camera_data = None
    try:
        scene = bpy.data.scenes.new("Skin Transfer QA Render")
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = scene.render.resolution_y = 512
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        shading = scene.display.shading
        shading.color_type = "OBJECT"
        shading.light = "STUDIO"
        shading.background_type = "VIEWPORT"
        shading.background_color = (.035,.035,.035)
        for mesh_data, label, color in ((body_mesh,"Registered Body",(.70,.55,.42,1)),
                                        (dress_mesh,"Dress",(.13,.43,.90,1))):
            mesh = bpy.data.meshes.new("Skin Transfer QA " + label)
            meshes.append(mesh)
            mesh.from_pydata([vector(point) for point in mesh_data["points"]], [], mesh_data["faces"])
            mesh.update()
            obj = bpy.data.objects.new("Skin Transfer QA " + label, mesh)
            objects.append(obj); scene.collection.objects.link(obj)
            obj.color = color; obj.hide_render = False
        camera_data = bpy.data.cameras.new("Skin Transfer QA Camera")
        camera = bpy.data.objects.new("Skin Transfer QA Camera", camera_data)
        objects.append(camera); scene.collection.objects.link(camera); scene.camera = camera
        camera_data.type = "ORTHO"
        band = [point for data in (dress_mesh,body_mesh) for point in data["points"]
                if bounds["lower"] <= (point-bounds["waist"]).dot(bounds["up"]) <= bounds["upper"]]
        require(band, "No actual geometry in proved waist-knee focus region")
        center = bounds["waist"]+bounds["up"]*(bounds["lower"]+bounds["upper"])*.5
        height = bounds["upper"]-bounds["lower"]
        distance = max(height,max((point-center).length for point in band))*4
        camera_data.clip_start = max(1.e-6,distance*.001)
        camera_data.clip_end = distance*4
        for label,direction in (("front",bounds["forward"]),("side",bounds["right"]),("back",-bounds["forward"])):
            right = bounds["up"].cross(direction).normalized()
            horizontal = [(point-center).dot(right) for point in band]
            camera_data.ortho_scale = max(height,max(horizontal)-min(horizontal))*1.08
            view_center = center+right*(min(horizontal)+max(horizontal))*.5
            location = view_center+direction*distance
            up = bounds["up"]
            camera.matrix_world = Matrix(((right.x,up.x,direction.x,location.x),
                (right.y,up.y,direction.y,location.y),(right.z,up.z,direction.z,location.z),(0,0,0,1)))
            path = args.output / f"frame_{args.frame:03d}_{label}.png"
            require(not path.exists(), "Refusing to replace an existing diagnostic PNG")
            scene.render.filepath = str(path)
            native = bpy.ops.render.render(write_still=True, scene=scene.name)
            require("FINISHED" in native and path.is_file(), "Native Workbench did not write the requested PNG")
            with path.open("rb") as handle:
                header = handle.read(24)
            require(header[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II",header[16:24]) == (512,512),
                    "Native render output is not a 512px PNG")
            result["views"][label] = {"native_result": sorted(native), "file": str(path),
                "file_state": qa.file_state(path), "camera_world": matrix(camera.matrix_world),
                "ortho_scale_world": camera_data.ortho_scale,
                "rig_axis_definition": {"front":"MainRig +Y","side":"MainRig +X","back":"MainRig -Y"}[label]}
        result.update(success=True,status="rendered")
    except Exception:
        result.update(status="failed_or_unsupported", error=traceback.format_exc(),
                      limitation="No renderer fallback or fabricated successful image")
    finally:
        for obj in reversed(objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            if mesh.users == 0: bpy.data.meshes.remove(mesh)
        if camera_data is not None and camera_data.users == 0: bpy.data.cameras.remove(camera_data)
        if scene is not None: bpy.data.scenes.remove(scene)
    return result


def main(args):
    isolation = qa.require_isolated_background()
    require(Path(character_designer.__file__).resolve().is_relative_to(REPOSITORY / "addons"), "Canonical import proof failed")
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / "skin_transfer_diagnostic.json"
    require(not report_path.exists(), "Use a fresh diagnostic output directory")
    report = {"success": False, "geometry_success": False, "purpose": "Sealed QA-copy skin-transfer diagnosis",
        "artist_operation": False, "body_inside_outside_claim": False, "isolation": isolation,
        "input": str(args.input), "input_before": qa.file_state(args.input),
        "source_manifest_before": source_manifest(), "blender": bpy.app.version_string,
        "addon_metadata_version": list(character_designer.bl_info["version"]),
        "frames": [], "errors": [], "render": {"requested": args.render,"success": False,"status":"not_requested"},
        "probe": {"requested": args.probe,"created": False}, "explicit_cache_write_operations": []}
    started = time.perf_counter(); protection = None; probe = None
    temporary_objects, temporary_meshes = [], []
    try:
        character_designer.register()
        native_open = bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
        require("FINISHED" in native_open and Path(bpy.data.filepath).resolve() == args.input, "Native candidate open failed")
        protection = qa.Protection()
        report["assets_before"] = protection.summary()
        source, rig, saved = qa.owned_source(args.source)
        record, proved_rig, proxy, cloth = physics.validate_physics(source)
        require(rig == proved_rig, "Native source rig proof disagrees")
        require(cloth.point_cache.is_baked and record["physics"].get("baked_range"), "Input is not sealed; no bake/reset will be attempted")
        baked = record["physics"]["baked_range"]
        require(all(baked[0] <= frame <= baked[1] for frame in args.frames), "Requested frame outside sealed interval")
        report.update(original_record=record, original_record_raw=source.get(skirt.RECORD_KEY),
            native_cache_before=qa.cache_state(cloth), source=source.name, rig=rig.name, cloth=proxy.name,
            source_modifiers=[qa.simple_rna(item) for item in source.modifiers],
            corrections_key=skirt_original_mode.CORRECTIONS,
            corrections_raw=source.get(skirt_original_mode.CORRECTIONS),
            missing_fields=[], basis_source_local=[vector(item.co) for item in source.data.vertices])
        raw_corrections = report["corrections_raw"]
        if raw_corrections is None:
            report["corrections_status"] = "Missing native property; no correction is inferred"
        else:
            report["corrections_json"] = json.loads(raw_corrections)
        keys = source.data.shape_keys
        report["basis_shape_key_source_local"] = [vector(item.co) for item in keys.reference_key.data] if keys else None
        fit_vertices = record.get("fit",{}).get("vertices")
        report["fit_original_vertices_source_local"] = fit_vertices
        if fit_vertices is None: report["missing_fields"].append("fit.vertices")
        elif len(fit_vertices) == len(source.data.vertices):
            report["fit_to_current_basis_max_coordinate_delta_local"] = max((Vector(point)-vertex.co).length for point,vertex in zip(fit_vertices,source.data.vertices))
        meters = bpy.context.scene.unit_settings.scale_length
        require(math.isfinite(meters) and meters > 0, "Invalid scene metre scale")
        report["scene_units_to_meters"] = meters
        body, report["registered_body_status"] = qa.registered_body(bpy.context, rig, args)
        roles = {name: layer for chain in record["chains"] for layer in ("manual","phys","def") for name in chain[layer]}
        roles[record["controls"]["waist"]] = "waist"
        if args.probe:
            try: probe, report["probe"] = fitted_probe(source,rig,record,temporary_objects,temporary_meshes)
            except Exception: report["probe"] = {"requested": True,"created": False,"status":"skipped_unsupported_schema","error":traceback.format_exc()}
        for frame in args.frames:
            bpy.context.scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            evaluated = rig.evaluated_get(graph)
            cage, final = mesh_snapshot(proxy,graph), mesh_snapshot(source,graph)
            require(qa.finite(cage["points"]) and qa.finite(final["points"]), "Native surface became nonfinite")
            require(any(final["weights"]), "Evaluated Dress weight layer is unavailable; free surface is unmeasured")
            waist_group = source.vertex_groups[record["controls"]["waist"]].index
            final["free_indices"] = [index for index,weights in enumerate(final["weights"])
                if next((item["weight"] for item in weights if item["index"] == waist_group),0.) < .999]
            epsilon = max(1.e-8,record["fit"]["height_world"]*1.e-6)
            item = {"frame":frame,"cloth_vertices":len(cage["points"]),"final_vertices":len(final["points"]),
                "cloth_world": [vector(point) for point in cage["points"]],"cloth_actual_weights":cage["weights"],
                "final_world": [vector(point) for point in final["points"]],"final_actual_weights":final["weights"],
                "free_evaluated_vertex_indices":final["free_indices"],"chains":[],
                "shape_key_values": {key.name:{"value":key.value,"mute":key.mute,"relative_key":key.relative_key.name} for key in keys.key_blocks} if keys else {},
                "source_matrix_world":matrix(source.matrix_world),"rig_matrix_world":matrix(evaluated.matrix_world),
                "corrections_raw":source.get(skirt_original_mode.CORRECTIONS)}
            control_names = [record["controls"][name] for name in ("waist","mid","hem")]
            control_names += [name for values in record["controls"]["chains"] for name in values.values()]
            item["manual_controls"] = [bone_content(rig,evaluated,name) for name in control_names]
            for ci,chain in enumerate(record["chains"]):
                chain_data = {"index":ci,"segments":[],"curve":curve_content(bpy.data.objects[chain["curve"]],graph)}
                for si in range(record["segment_count"]):
                    names = {layer:chain[layer][si] for layer in ("manual","phys","def")}
                    aim = rig.pose.bones[names["phys"]].constraints.get("CD Physics Aim")
                    require(aim is not None and aim.target == proxy, "Exact native PHYS target is missing")
                    target = weighted_target(proxy,cage,aim.subtarget)
                    segment = {"index":si,"layers":{layer:bone_content(rig,evaluated,name) for layer,name in names.items()},
                               "exact_native_constraint_target":target}
                    if target["available"]:
                        center = Vector(target["weighted_world_center"])
                        segment["tail_vs_target"] = {layer:residual(evaluated,name,center,meters) for layer,name in names.items()}
                    chain_data["segments"].append(segment)
                chain_data["layer_total_eval_length_m"] = {layer:sum(segment["layers"][layer]["eval_length_world"] for segment in chain_data["segments"])*meters for layer in ("manual","phys","def")}
                item["chains"].append(chain_data)
            item["owned_colliders"] = collider_diagnostics(final,cage,record,graph,meters,roles,epsilon)
            try:
                bounds = framing(rig,record,graph)
                item["framing_proof"] = {key:({k:vector(v) for k,v in value.items()} if key == "knees" else vector(value)
                    if isinstance(value,Vector) else value) for key,value in bounds.items()}
                body_mesh = None
                if body is not None:
                    item["registered_body_surface"], body_mesh = body_diagnostics(body,graph,final,bounds,args,meters,roles,epsilon)
                else: item["registered_body_surface"] = {"measured":False,"reason":report["registered_body_status"].get("reason"),"body_inside_outside_claim":False}
                if args.render and frame == args.frame:
                    report["render"] = native_render(args,final,body_mesh,bounds) if body_mesh else {
                        "requested":True,"success":False,"status":"skipped_unproved_body","reason":item["registered_body_surface"]}
            except Exception:
                item["framing_or_body_error"] = traceback.format_exc()
                if args.render and frame == args.frame:
                    report["render"] = {"requested":True,"success":False,"status":"skipped_unproved_region","error":traceback.format_exc()}
            if probe is not None:
                fitted = mesh_snapshot(probe,graph)
                require(len(fitted["points"]) == len(cage["points"]), "Probe/cage native vertex correspondence changed")
                distances = [(first-second).length*meters for first,second in zip(fitted["points"],cage["points"])]
                fitted["free_indices"] = [index for index,weights in enumerate(fitted["weights"])
                    if next((assignment["weight"] for assignment in weights if assignment["name"] == record["controls"]["waist"]),0.) < .999]
                item["fitted_DEF_probe"] = {"world":[vector(point) for point in fitted["points"]],"weights":fitted["weights"],
                    "cloth_gap_m_per_vertex":distances,"cloth_gap_max_m":max(distances),
                    "cloth_gap_rms_m":math.sqrt(sum(value*value for value in distances)/len(distances)),
                    "owned_colliders":collider_diagnostics(fitted,cage,record,graph,meters,roles,epsilon)}
            report["frames"].append(item)
        report["geometry_success"] = len(report["frames"]) == len(args.frames)
        report["record_unchanged"] = source.get(skirt.RECORD_KEY) == report["original_record_raw"]
        report["corrections_unchanged"] = source.get(skirt_original_mode.CORRECTIONS) == report["corrections_raw"]
        report["native_cache_after"] = qa.cache_state(cloth)
        require(report["native_cache_before"] == report["native_cache_after"], "Native sealed cache fields changed")
        require(report["record_unchanged"] and report["corrections_unchanged"], "Source record/corrections changed")
    except Exception:
        report["errors"].append(traceback.format_exc())
    finally:
        try:
            for obj in reversed(temporary_objects):
                bpy.data.objects.remove(obj,do_unlink=True)
            for mesh in reversed(temporary_meshes):
                if mesh.users == 0: bpy.data.meshes.remove(mesh)
        except Exception:
            report["errors"].append("Temporary probe cleanup failed:\n"+traceback.format_exc())
        if protection is not None:
            report["asset_protection"] = protection.verify()
            report["assets_after"] = qa.Protection().summary()
            report["asset_inventory_exact"] = report["assets_before"] == report["assets_after"]
        report["input_after"] = qa.file_state(args.input)
        report["input_disk_exact"] = report["input_after"] == report["input_before"]
        report["source_manifest_after"] = source_manifest()
        report["source_files_exact"] = report["source_manifest_after"] == report["source_manifest_before"]
        report["success"] = report["geometry_success"] and not report["errors"] \
            and report.get("asset_protection",{}).get("success",False) and report["input_disk_exact"] \
            and report.get("asset_inventory_exact",False) and report["source_files_exact"] \
            and (not args.render or report["render"]["success"])
        report["elapsed_seconds"] = time.perf_counter()-started
        # simple_rna() turns matrix RNA into list(Matrix), leaving Vector rows.
        # In particular Curve Hook matrix_inverse needs recursive conversion.
        conversions = []
        serializable = json_content(report,conversions=conversions)
        serializable["json_mathutils_conversions"] = conversions
        report_path.write_text(json.dumps(serializable,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        print("SKIN_TRANSFER_DIAGNOSTIC="+str(report_path),flush=True)
        print("SKIN_TRANSFER_SUCCESS="+str(report["success"]),flush=True)
    return report


if __name__ == "__main__":
    result = main(arguments())
    if not result["success"]:
        raise RuntimeError("Native skin-transfer diagnosis incomplete; inspect JSON evidence")
