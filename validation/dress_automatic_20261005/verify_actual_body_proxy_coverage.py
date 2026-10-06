"""PREPARED ONLY: exact saved Cosha, two start-frame Body/proxy coverage samples.

Root must lease Blender 5.1 --background --factory-startup --disable-autoexec
--threads 1. No native run is implied by preparation or pure checks. This reads
actual evaluated geometry; only a separately saved private candidate receives
public FK/Automatic/Reset and one unkeyed left-thigh .55 rad input. No projection,
Hull, artist save, render, replay, bake, child process, deployment or Unity call.

--pure-checks runs only standard-library geometric controls, without bpy import.
Coverage is bounded witness evidence, never Body volume or artistic acceptance.
"""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
REPOSITORY = Path(r"D:\MyRepository\Blender-addons-by-Randy")
INSTALL = HERE / "actual_install_51_20261006_031045_111/result/workflow_install.json"
INPUT = INSTALL.parent.parent / "scenes/Cosha_Dress_QA_surface_install.blend"
INPUT_SHA = "7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f"
INSTALL_SHA = "a2157ba399bfe32cc28401847c2556f776761fd607eaa3ba7ea23b61aaec6a32"
SURFACE_SHA = "3905846f751659a6970cc80b70118201eaea068a657c69cd764b789e893b127b"
WORKER_SHA = "069fb0f21b02e36a23dd02b1978d2a917c2873f290fc3331cdf0d55e877ce5bc"
PINS = {
    "verify_actual_surface_workflow.py": "2e8d82bbbde00604bf3f62bc17cbcb31244ed87290e083ebb17b25f4b9216140",
    "verify_actual_same_frame_pose.py": "812841f31309bea8ee923dd8299c0240ec1576d2ed4842ba46793c854d1830ff",
    "validate_real_dress.py": "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046",
    "diagnose_skin_transfer.py": "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28",
    "prototype_native_dress_overlay.py": "574c121fa2b7adf2892ceec032ab5629254b2f846818bdd677c6d94e2400c909",
    # Proof-only reuse. install_preview/remove_preview and GN construction are never called.
    "prototype_final_surface_clearance.py": "6280862bd2b7602dd1252a2c959202f394c9ce9498d41c2b9f47e4dc83e2767b",
}


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def subtract(a, b):
    return tuple(float(x) - float(y) for x, y in zip(a, b))


def dot(a, b):
    return math.fsum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def length(a):
    return math.sqrt(dot(a, a))


def plane_model(points, triangles, metres, external_micro_proof=None, operation_limit=1000000):
    """Double halfspaces of exact recorded points, with explicit inner/outer scopes.

    The outer envelope contains every native mesh vertex, therefore every face
    and its convex hull. Strictly outside it is a conservative missing-coverage
    witness. Near-convex micro-budget never grants exact hull/Body separation.
    Interior results name the strict inner-plane core, not a whole-Body Pass.
    """
    base = {"status": "unknown", "whole_body_coverage_accepted": False}
    try:
        p = [tuple(float(x) for x in row) for row in points]
        t = [tuple(row) for row in triangles]
        need(math.isfinite(metres) and metres > 0., "invalid physical units")
        need(len(p) >= 4 and all(len(row) == 3 and all(math.isfinite(x) for x in row) for row in p), "incomplete finite native points")
        need(len(t) >= 4 and len(t) * len(p) <= operation_limit, "convex support budget exceeded")
        need(all(len(row) == 3 and len(set(row)) == 3 and all(type(i) is int and 0 <= i < len(p) for i in row) for row in t), "invalid native triangle identities")
        edges, adjacency = {}, [set() for _ in p]
        for row in t:
            for a, b in zip(row, row[1:] + row[:1]):
                edges.setdefault(tuple(sorted((a, b))), []).append((a, b))
                adjacency[a].add(b); adjacency[b].add(a)
        need(all(len(rows) == 2 and rows[0] == rows[1][::-1] for rows in edges.values()), "nonclosed or inconsistent native winding")
        visited, todo = set(), [0]
        while todo:
            i = todo.pop()
            if i not in visited:
                visited.add(i); todo.extend(adjacency[i] - visited)
        need(len(visited) == len(p), "native collider disconnected or has unused vertices")
        center = tuple(math.fsum(row[j] for row in p) / len(p) for j in range(3))
        diameter = max(length(subtract(row, center)) for row in p) * 2.
        need(diameter > 0. and math.isfinite(diameter), "zero native collider extent")
        arithmetic = max(math.ulp(max(abs(x) for row in p for x in row)) * 256., diameter * 1.e-14)
        allowed_m = 0.
        if external_micro_proof is not None:
            allowed_m = float(external_micro_proof["maximum_allowed_support_deviation_m"])
            need(0. < allowed_m <= 1.e-6 and external_micro_proof["maximum_excess_over_bounded_rounding_envelope_units"] <= 0., "unproved near-convex micro-budget")
            need(external_micro_proof["maximum_positive_support_deviation_m_upper_bound"] <= allowed_m, "native positive support exceeds physical micro-cap")
        need(arithmetic * metres < (allowed_m or 1.e-6) / 32., "double arithmetic cannot resolve the physical micro-budget")
        allowed = allowed_m / metres if external_micro_proof is not None else arithmetic
        guard = max(2.e-6 / metres, 2. * allowed, arithmetic * 4.)
        planes, volumes, maximum = [], [], 0.
        for i, row in enumerate(t):
            a, b, c = (p[index] for index in row)
            raw = cross(subtract(b, a), subtract(c, a)); magnitude = length(raw)
            need(magnitude > max(diameter * diameter * 1.e-14, 1.e-30), "degenerate native face")
            normal = tuple(x / magnitude for x in raw)
            support = max(dot(subtract(point, a), normal) for point in p)
            maximum = max(maximum, support)
            need(support <= allowed, "native concavity exceeds explicit numerical proof budget")
            planes.append({"triangle": i, "vertices": list(row), "origin": list(a), "outward_normal": list(normal),
                           "native_vertex_maximum_support_units": support,
                           "outer_envelope_offset_units": max(0., support) + guard})
            volumes.append(dot(subtract(a, center), cross(subtract(b, center), subtract(c, center))) / 6.)
        volume = math.fsum(volumes)
        need(volume > max(diameter ** 3 * 1.e-14, 1.e-30), "zero or inverted native volume")
        return {**base, "status": "bounded_native_halfspace_model", "planes": planes,
                "positive_volume_units3": volume, "maximum_support_units": maximum,
                "core_boundary_guard_units": guard, "core_boundary_guard_m": guard * metres,
                "allowed_support_deviation_m": allowed_m, "double_arithmetic_guard_units": arithmetic,
                "units_to_metres": metres,
                "near_convex_micro_scope": external_micro_proof is not None,
                "definition": "Inner: all outward native planes strictly negative beyond guard. Outer: relaxed planes containing all native vertices/faces/convex hull. No exact Hull/Body volume claim."}
    except Exception as error:
        return {**base, "reason": str(error)}


def classify_point(point, model):
    if model.get("status") != "bounded_native_halfspace_model":
        return {"status": "unknown", "reason": model.get("reason", "no native proof")}
    if len(point) != 3 or not all(math.isfinite(float(x)) for x in point):
        return {"status": "unknown", "reason": "nonfinite witness point"}
    values = [(dot(subtract(point, row["origin"]), row["outward_normal"]), row) for row in model["planes"]]
    max_core, core_plane = max(values, key=lambda row: row[0])
    exterior, outside_plane = max(((value - row["outer_envelope_offset_units"], row) for value, row in values), key=lambda row: row[0])
    status = ("strict_inner_plane_core" if max_core < -model["core_boundary_guard_units"]
              else "strictly_outside_outer_envelope" if exterior > 0. else "boundary_or_shell_unknown")
    return {"status": status, "maximum_native_plane_distance_units": max_core,
            "maximum_native_plane_distance_m": max_core * model["units_to_metres"],
            "core_worst_triangle": core_plane["triangle"], "outer_envelope_excess_units": exterior,
            "outer_envelope_excess_m": exterior * model["units_to_metres"],
            "outer_worst_triangle": outside_plane["triangle"]}


def triangle_coverage(points, models, crossing_points=()):
    """Split membership never certifies triangle or union coverage."""
    per = {name: [classify_point(point, model) for point in points] for name, model in models.items()}
    common = [name for name, rows in per.items() if len(rows) == 3 and all(row["status"] == "strict_inner_plane_core" for row in rows)]
    witness = []
    for kind, rows in (("body_triangle_vertex", points), ("actual_crossing_point", crossing_points)):
        for index, point in enumerate(rows):
            evidence = {name: classify_point(point, model) for name, model in models.items()}
            if len(evidence) == 3 and all(row["status"] == "strictly_outside_outer_envelope" for row in evidence.values()):
                witness.append({"kind": kind, "index": index, "world": list(point), "per_proxy": evidence})
    split = bool(len(models) == 3 and len(points) == 3 and not common and all(
        any(rows[i]["status"] == "strict_inner_plane_core" for rows in per.values()) for i in range(3)))
    return {"status": "outside_all_proxy_envelopes_witness" if witness else "single_proxy_strict_core_contains_triangle" if common else "split_union_unknown" if split else "unknown",
            "single_proxy_core_contains_all_three_vertices": common, "split_vertex_union_membership_only": split,
            "per_proxy_vertex_evidence": per, "outside_all_proxy_witnesses": witness,
            "whole_body_coverage_accepted": False, "actual_final_clearance_accepted": False,
            "limitation": "One strict convex inner-plane core can contain a whole triangle; separate per-vertex proxy memberships do not prove union containment. Open Body has no signed volume proof."}


def pure_checks():
    def cube(center):
        x, y, z = center
        p = [(x+a, y+b, z+c) for a,b,c in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
        t = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
        return p, t
    p,t = cube((0.,0.,0.)); m = plane_model(p,t,1.)
    need(m["status"] == "bounded_native_halfspace_model", "cube proof")
    inside = ((0.,0.,0.),(.1,0.,0.),(0.,.1,0.))
    need(triangle_coverage(inside,{"a":m,"b":m,"c":m})["status"] == "single_proxy_strict_core_contains_triangle", "same proxy contains complete triangle")
    models = {name: plane_model(*cube(center),1.) for name,center in (("a",(-3.,0.,0.)),("b",(3.,0.,0.)),("c",(0.,3.,0.)))}
    split = triangle_coverage(((-3.,0.,0.),(3.,0.,0.),(0.,3.,0.)),models)
    need(split["status"] == "split_union_unknown" and not split["single_proxy_core_contains_all_three_vertices"], "split union must not Pass")
    need(triangle_coverage(((8.,8.,8.),)*3,models)["status"] == "outside_all_proxy_envelopes_witness", "outside all envelope counterexample")
    need(classify_point((1.,0.,0.),m)["status"] == "boundary_or_shell_unknown", "boundary remains Unknown")
    need(plane_model(p,t[:-1],1.)["status"] == "unknown", "open collider refusal")
    need(plane_model(p,[row[::-1] for row in t],1.)["status"] == "unknown", "inverted winding refusal")
    dent = list(p); dent[6] = (0.,0.,0.)
    need(plane_model(dent,t,1.)["status"] == "unknown", "substantive concavity refusal")
    need(plane_model(p,t,1.,operation_limit=1)["status"] == "unknown", "budget remains Unknown")
    need(plane_model(*cube((1.e12,1.e12,1.e12)),1.)["status"] == "unknown", "unresolved coordinate precision remains Unknown")
    shifted = plane_model(*cube((100.,-100.,20.)),.01)
    need(shifted["status"] == "bounded_native_halfspace_model", "nonzero coordinate/physical units proof")
    return {"pure_checks_passed": True, "controls": 11, "native_run": False,
            "limits": "Synthetic polyhedra/control classification only; no Blender interface, actual Body coverage or projection acceptance."}


def load(name):
    path = HERE / name
    need(sha(path) == PINS[name], "Frozen dependency changed: " + name)
    spec = importlib.util.spec_from_file_location("body_proxy_coverage_" + path.stem, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pure-checks", action="store_true")
    p.add_argument("--output", type=Path)
    p.add_argument("--body-vertex-limit", type=int, default=100000)
    p.add_argument("--triangle-pair-limit", type=int, default=10000)
    p.add_argument("--witness-triangle-limit", type=int, default=64)
    values = (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv
              else sys.argv[1:] if "--pure-checks" in sys.argv else [])
    args = p.parse_args(values)
    if args.pure_checks:
        return args
    need(args.output is not None, "Use one fresh private --output")
    args.output = args.output.resolve()
    need(args.output.is_relative_to(HERE) and args.output != HERE and not args.output.exists(), "Refuse existing or non-Validation output")
    need(1000 <= args.body_vertex_limit <= 100000 and 1000 <= args.triangle_pair_limit <= 100000
         and 1 <= args.witness_triangle_limit <= 256, "Declared bounded budgets required")
    args.input, args.install_report = INPUT.resolve(), INSTALL.resolve()
    args.expected_surface_sha, args.expected_worker_sha = SURFACE_SHA, WORKER_SHA
    return args


def matrix(m):
    return [[float(x) for x in row] for row in m]


def native_mesh(obj, graph, diag):
    evaluated = obj.evaluated_get(graph)
    snapshot = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    try:
        snapshot.calc_loop_triangles()
        names = {group.index: group.name for group in obj.vertex_groups}
        mesh = {"object":obj.name,
            "points":[evaluated.matrix_world @ vertex.co for vertex in snapshot.vertices],
            "native_vertex_index_order":[int(vertex.index) for vertex in snapshot.vertices],
            "faces":[tuple(face.vertices) for face in snapshot.polygons],
            "edges":[tuple(edge.vertices) for edge in snapshot.edges],
            "triangles":[tuple(triangle.vertices) for triangle in snapshot.loop_triangles],
            "weights":[[{"index":item.group,"name":names.get(item.group),"weight":item.weight}
                for item in vertex.groups] for vertex in snapshot.vertices],
            "matrix_world":matrix(evaluated.matrix_world)}
    finally:
        evaluated.to_mesh_clear()
    need(mesh["native_vertex_index_order"]==list(range(len(mesh["points"]))), "Native vertex index order cannot address the captured triangle IDs")
    mesh["native_group_mapping"] = [{"index": group.index, "name": group.name, "lock_weight": bool(group.lock_weight)} for group in obj.vertex_groups]
    mesh["runtime_identity"] = {"object_pointer": obj.as_pointer(), "data_pointer": obj.data.as_pointer(),
                               "object": obj.name, "mesh": obj.data.name}
    mesh["native_topology_sha256"] = digest({k: mesh[k] for k in ("faces", "edges", "triangles")})
    mesh["native_vertex_face_edge_sha256"] = digest({k:mesh[k] for k in ("native_vertex_index_order","faces","edges")})
    mesh["native_triangulation_sha256"] = digest(mesh["triangles"])
    names = {group.index: group.name for group in obj.vertex_groups}
    mesh["weights_complete"] = (len(mesh["weights"]) == len(mesh["points"]) and all(mesh["weights"])
        and all(item["index"] in names and names[item["index"]] == item["name"] and math.isfinite(item["weight"])
                and 0. <= item["weight"] <= 1. for row in mesh["weights"] for item in row))
    mesh["index_scope"] = "Exact evaluated mesh IDs at this sample; no original/subdivision correspondence inferred"
    return mesh


def visibility_evidence(objects, cloth, scene):
    """Read actual viewport/render filtering paths; never toggle any flag."""
    import bpy
    def read_bool(owner, key):
        try:
            value=getattr(owner,key)
            need(type(value) is bool,"RNA value is not boolean")
            return {"status":"observed","value":value}
        except Exception as error:
            return {"status":"unknown","reason":str(error)}
    def collection_row(collection):
        return {"name":collection.name,"pointer":collection.as_pointer(),
            "hide_viewport":read_bool(collection,"hide_viewport"),"hide_render":read_bool(collection,"hide_render")}
    targets=set()
    result={"scope":"Observed native flags only. Explicit collision collection, object hiding and collection filtering remain distinct; no collision-enabled or visibility repair inferred.",
        "scene":scene.name,"view_layer":bpy.context.view_layer.name,"objects":{},"collection_parent_paths":{},"layer_collection_parent_paths":{}}
    def object_row(obj):
        try:
            memberships=list(obj.users_collection); targets.update(x.as_pointer() for x in memberships)
            member_rows=[collection_row(x) for x in memberships]
            member_status={"status":"observed"}
        except Exception as error:
            member_rows=[]; member_status={"status":"unknown","reason":str(error)}
        try:
            hidden={"status":"observed","value":bool(obj.hide_get(view_layer=bpy.context.view_layer))}
        except Exception as error:
            hidden={"status":"unknown","reason":str(error)}
        return {"name":obj.name,"object_pointer":obj.as_pointer(),"hide_get_current_view_layer":hidden,
            "hide_viewport":read_bool(obj,"hide_viewport"),"hide_render":read_bool(obj,"hide_render"),
            "native_users_collections":member_rows,"native_users_collections_read":member_status,
            "collision_modifiers":[{"name":modifier.name,"viewport_enabled":read_bool(modifier,"show_viewport"),
                "render_enabled":read_bool(modifier,"show_render"),"native_is_active":read_bool(modifier,"is_active")}
                for modifier in obj.modifiers if modifier.type=="COLLISION"]}
    for obj in objects: result["objects"][obj.name]=object_row(obj)
    try:
        selected=cloth.collision_settings.collection
        need(selected is not None,"Cloth has no explicit native collision collection")
        targets.add(selected.as_pointer())
        result["explicit_cloth_collision_collection"]={**collection_row(selected),
            "direct_objects":[object_row(x) for x in selected.objects]}
    except Exception as error:
        result["explicit_cloth_collision_collection"]={"status":"unknown","reason":str(error)}
    def walk_collection(node,path,active,budget):
        budget[0]+=1; need(budget[0]<=2048,"native collection path budget exceeded")
        pointer=node.as_pointer(); need(pointer not in active,"cyclic native collection ancestry")
        rows=path+[collection_row(node)]
        if pointer in targets: result["collection_parent_paths"].setdefault(str(pointer),[]).append(rows)
        for child in node.children: walk_collection(child,rows,active|{pointer},budget)
    def walk_layer(node,path,active,budget):
        budget[0]+=1; need(budget[0]<=2048,"native LayerCollection path budget exceeded")
        pointer=node.as_pointer(); need(pointer not in active,"cyclic native LayerCollection ancestry")
        rows=path+[{"name":node.name,"layer_pointer":pointer,"collection":collection_row(node.collection),
            "exclude":read_bool(node,"exclude"),"hide_viewport":read_bool(node,"hide_viewport")}]
        if node.collection.as_pointer() in targets:
            result["layer_collection_parent_paths"].setdefault(str(node.collection.as_pointer()),[]).append(rows)
        for child in node.children: walk_layer(child,rows,active|{pointer},budget)
    for key,fn,root in (("collection_tree",walk_collection,scene.collection),
                        ("layer_tree",walk_layer,bpy.context.view_layer.layer_collection)):
        try:
            fn(root,[],set(),[0]); result[key+"_read"]={"status":"observed"}
        except Exception as error:
            result[key+"_read"]={"status":"unknown","reason":str(error)}
    result["target_path_status"]={str(pointer):{
        "current_scene":"observed" if str(pointer) in result["collection_parent_paths"] else "unknown_not_found_in_current_scene_paths",
        "current_view_layer":"observed" if str(pointer) in result["layer_collection_parent_paths"] else "unknown_not_found_in_current_layer_paths"}
        for pointer in targets}
    return result


def body_collision_comparison(body, clone, metres, keep_snapshot=True):
    """Exact graph readback comparison, never an inferred shared-mesh equality."""
    point_hash=lambda mesh:digest([list(point) for point in mesh["points"]])
    hashes=lambda mesh:{key:digest(mesh[key]) for key in ("native_vertex_index_order","edges","faces","triangles","weights","native_group_mapping")}
    original_hashes,clone_hashes=hashes(body),hashes(clone)
    original_points,clone_points=point_hash(body),point_hash(clone)
    identity=(len(body["points"])==len(clone["points"]) and body["native_vertex_index_order"]==clone["native_vertex_index_order"])
    maximum=(max((length(subtract(a,b)) for a,b in zip(body["points"],clone["points"])),default=0.) if identity else None)
    equal={key:original_hashes[key]==clone_hashes[key] for key in original_hashes}
    coordinate_exact=identity and original_points==clone_points
    geometry_exact=coordinate_exact and all(equal[key] for key in ("native_vertex_index_order","edges","faces","triangles"))
    result={"status":"exact_native_geometry_match" if geometry_exact else "different_native_geometry" if identity else "unknown_native_vertex_correspondence",
        "registered_body_identity":body["runtime_identity"],"actual_collision_clone_identity":clone["runtime_identity"],
        "counts":{name:{"vertices":len(mesh["points"]),"edges":len(mesh["edges"]),"faces":len(mesh["faces"]),"triangles":len(mesh["triangles"])}
            for name,mesh in (("registered_body",body),("actual_collision_clone",clone))},
        "registered_body_hashes":original_hashes,"actual_clone_hashes":clone_hashes,
        "registered_body_world_points_sha256":original_points,"actual_clone_world_points_sha256":clone_points,
        "equal_native_fields":equal,"vertex_index_correspondence_observed":identity,"world_coordinates_exact":coordinate_exact,
        "maximum_corresponding_world_point_error_units":maximum,"maximum_corresponding_world_point_error_m":None if maximum is None else maximum*metres,
        "units_to_metres":metres,"whole_body_coverage_accepted":False,"actual_final_clearance_accepted":False,
        "scope":"Same depsgraph actual mesh readback, exact native IDs/topology/points compared. Shared data/binding does not substitute for this measurement; lock/group differences are independent diagnostics."}
    if keep_snapshot and not geometry_exact:
        result["actual_clone_native_snapshot"]=clone
    return result


def collect(label, common, args, qa, diag, same, proof, surface, report):
    import bpy
    source, rig, actual, neutral, body, legs, cloth, scene, frame = common
    need(scene.frame_current == frame and scene.frame_subframe == 0., "Same frame/subframe changed")
    cache_before = same.cache_state(cloth, qa)
    began = time.perf_counter(); bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    record = qa.skirt.read_record(source)
    native = {"Body": native_mesh(body, graph, diag), "O3040": native_mesh(source, graph, diag)}
    need(len(native["Body"]["points"]) <= args.body_vertex_limit and len(native["O3040"]["points"]) == 3040, "Actual native vertex budget/layout changed")
    waist = source.vertex_groups[record["controls"]["waist"]].index
    native["O3040"]["free_indices"] = [i for i,row in enumerate(native["O3040"]["weights"])
        if next((item["weight"] for item in row if item["index"] == waist),0.) < .999]
    weight_identity_complete = native["Body"]["weights_complete"] and native["O3040"]["weights_complete"]
    names = record["physics"]["colliders"][:-1]
    need(len(names) == 3 and set(names) == set(record["physics"]["surface"]["colliders"])
         and all(x.get("version") == 2 for x in record["physics"]["surface"]["colliders"].values()), "Exact V2 pelvis/two thighs inventory missing")
    models, collider_proofs = {}, {}
    meters = float(scene.unit_settings.scale_length)
    need(math.isfinite(meters) and meters > 0., "Invalid physical scene units")
    for name in names:
        obj = bpy.data.objects.get(name)
        need(obj is not None and obj.type == "MESH", "Exact owned collider absent")
        native[name] = native_mesh(obj,graph,diag)
        try:
            contract = proof._collider_proof(obj,source,rig,record,qa.physics,graph,.002)
            geometry = {"points": [list(point) for point in native[name]["points"]], "triangles": [list(row) for row in native[name]["triangles"]]}
            need(proof._digest(geometry) == contract["evaluated_world"]["coords_triangles_sha256"], "Native collider snapshot differs from proof readback")
            collider_proofs[name] = contract
            models[name] = plane_model(geometry["points"], geometry["triangles"], meters, contract["evaluated_world"])
        except Exception as error:
            collider_proofs[name] = {"status": "unknown", "reason": str(error)}
            models[name] = {"status": "unknown", "reason": str(error)}
    clone=None
    try:
        clone_name=record["physics"]["colliders"][-1]
        need(record["physics"]["surface"]["roles"]["BODY_ATTACHMENT"]==[clone_name],"Exact BODY_ATTACHMENT/collider record identity differs")
        clone=bpy.data.objects.get(clone_name)
        need(clone is not None and clone.type=="MESH","Exact actual Body collision clone unavailable")
        clone_comparison=body_collision_comparison(native["Body"],native_mesh(clone,graph,diag),meters)
    except Exception as error:
        clone_comparison={"status":"unknown","reason":str(error),"whole_body_coverage_accepted":False,"actual_final_clearance_accepted":False}
    posed = rig.evaluated_get(graph)
    knees = {side: posed.matrix_world @ posed.pose.bones[item["chain"][1]].head for side,item in legs.items()}
    all_pose = {bone.name: {"pose_matrix":matrix(bone.matrix), "matrix_basis":matrix(bone.matrix_basis),
                          "world_matrix":matrix(posed.matrix_world @ bone.matrix)} for bone in posed.pose.bones}
    keys = {obj.name: {"data":obj.data.shape_keys.name, "values": {key.name:float(key.value) for key in obj.data.shape_keys.key_blocks}}
            for obj in (source,body,actual,neutral) if obj.data.shape_keys is not None}
    bounds = diag.framing(rig,record,graph)
    epsilon = max(1.e-8,record["fit"]["height_world"]*1.e-6)
    crossing = (diag.triangle_crossings(native["O3040"],native["Body"],bounds,args.triangle_pair_limit,epsilon)
                if weight_identity_complete else {"status":"unmeasured_native_weights", "crossing_pairs":[],
                    "reason":"Body/O evaluated weight identity is incomplete; no missing weight is inferred as free"})
    triangles = {}
    for pair in crossing.get("crossing_pairs",[]):
        bi = pair["body_triangle"]
        need(native["Body"]["triangles"][bi] == tuple(pair["body_vertices"]), "Exact Body crossing vertex IDs changed")
        entry = triangles.setdefault(bi,{"pairs":[],"points":[]}); entry["pairs"].append(pair["dress_triangle"])
        entry["points"].extend(hit["world"] for hit in pair.get("points",[]) if hit["strict_crossing"])
    witnesses = []
    for bi, entry in sorted(triangles.items())[:args.witness_triangle_limit]:
        ids = native["Body"]["triangles"][bi]
        witnesses.append({"body_triangle":bi,"body_vertices":list(ids),"dress_triangle_ids":entry["pairs"],
            "native_body_weights":[native["Body"]["weights"][i] for i in ids],
            **triangle_coverage([native["Body"]["points"][i] for i in ids],models,entry["points"])})
    unresolved = [name for name in ("coplanar_unresolved","degenerate_unresolved","boundary_unresolved") if crossing.get(name)]
    complete = crossing.get("status") == "measured" and not unresolved and len(triangles) <= args.witness_triangle_limit
    need(scene.frame_current == frame and scene.frame_subframe == 0., "Native reads changed the held frame/subframe")
    repeat = {}
    for name,mesh in native.items():
        again = native_mesh(bpy.data.objects.get(mesh["object"]),graph,diag)
        repeat[name] = {"same_depsgraph_pointer":graph.as_pointer(),
            "coordinates_exact":digest(diag.json_content(mesh["points"]))==digest(diag.json_content(again["points"])),
            "vertex_face_edge_exact":mesh["native_vertex_face_edge_sha256"]==again["native_vertex_face_edge_sha256"],
            "group_mapping_and_weights_exact":mesh["native_group_mapping"]==again["native_group_mapping"] and mesh["weights"]==again["weights"],
            "triangles_exact":mesh["triangles"]==again["triangles"],
            "first_triangles_sha256":mesh["native_triangulation_sha256"],"repeat_triangles_sha256":again["native_triangulation_sha256"],
            "definition":"No input, update, frame advance or new depsgraph between reads; corresponding unchanged coordinates require exact derived triangles."}
        need(all(repeat[name][key] for key in ("coordinates_exact","vertex_face_edge_exact","group_mapping_and_weights_exact","triangles_exact")),
            "Same-frame no-input native repeat changed coordinates/topology/weights/triangles: "+name)
    try:
        need(clone is not None,"Actual collision clone unavailable for repeated readback")
        body_again=native_mesh(body,graph,diag)
        clone_again=body_collision_comparison(body_again,native_mesh(clone,graph,diag),meters,keep_snapshot=False)
        clone_comparison["same_graph_no_input_repeat"]={"summary":clone_again,
            "exact_summary_stable":{key:value for key,value in clone_comparison.items() if key!="actual_clone_native_snapshot"}==clone_again,
            "depsgraph_pointer":graph.as_pointer(),"frame":frame}
    except Exception as error:
        clone_comparison["same_graph_no_input_repeat"]={"status":"unknown","reason":str(error),"exact_summary_stable":False}
    need(scene.frame_current == frame and scene.frame_subframe == 0., "Native repeat changed the held frame/subframe")
    evidence = {"label":label,"frame":frame,"subframe":float(scene.frame_subframe),"depsgraph_pointer":graph.as_pointer(),
        "units_to_metres":meters,"coordinates":"Actual evaluated world units; multiply by units_to_metres. Same depsgraph and fixed frame; no Body volume sign.",
        "native_scene_units":{"system":scene.unit_settings.system,"scale_length":meters,"length_unit":scene.unit_settings.length_unit},
        "native_meshes":native,"rig_world_matrix":matrix(posed.matrix_world),"pose_matrices":all_pose,
        "native_rest_bones":{bone.name:{"parent":None if bone.parent is None else bone.parent.name,
            "use_deform":bool(bone.use_deform),"matrix_local":matrix(bone.matrix_local)} for bone in rig.data.bones},
        "shape_key_values":keys,"leg_chains":{side:list(x["chain"]) for side,x in legs.items()},
        "knee_world":{side:list(point) for side,point in knees.items()},"cache_before":cache_before,"cache_after":same.cache_state(cloth,qa),
        "native_collider_proofs":collider_proofs,"halfspace_models":models,"crossing":crossing,
        "coverage_summary":{"strict_crossing_pairs":len(crossing.get("crossing_pairs",[])),"unique_crossing_body_triangles":len(triangles),
            "witness_triangles_retained":len(witnesses),"witness_limit":args.witness_triangle_limit,"bounded_witness_inventory_complete":complete,
            "native_weight_identity_complete":bool(weight_identity_complete),
            "outside_all_proxy_witness_triangles":sum(x["status"]=="outside_all_proxy_envelopes_witness" for x in witnesses),
            "single_proxy_strict_core_triangles":sum(x["status"]=="single_proxy_strict_core_contains_triangle" for x in witnesses),
            "split_union_unknown_triangles":sum(x["status"]=="split_union_unknown" for x in witnesses),
            "unknown_triangles":sum(x["status"]=="unknown" for x in witnesses),"unresolved_crossing_categories":unresolved,
            "whole_body_coverage_accepted":False,"body_inside_outside_proven":False,"production_effect_accepted":False},
        "coverage_witnesses":witnesses,"same_graph_no_input_repeat":repeat,"read_and_witness_seconds":time.perf_counter()-began}
    evidence["actual_body_collision_comparison"]=clone_comparison
    evidence["native_visibility_and_collision_filters"]=visibility_evidence(
        [bpy.data.objects.get(mesh["object"]) for mesh in native.values()],cloth,scene)
    path = args.output / (label+"_native.json")
    path.write_text(json.dumps(diag.json_content(evidence),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    report["samples"].append({"label":label,"path":str(path),"sha256":sha(path),"coverage_summary":evidence["coverage_summary"],
                              "frame":frame,"native_topology_sha256":{name:mesh["native_topology_sha256"] for name,mesh in native.items()}})
    points = {"Body":native["Body"]["points"],"O3040":native["O3040"]["points"]}
    return {"points":points,"knees":knees,"hem":posed.matrix_world @ posed.pose.bones[record["controls"]["hem"]].matrix.translation,
            "public":{"cache":evidence["cache_after"]},"evidence":evidence}


def main(args):
    if args.pure_checks:
        print(json.dumps(pure_checks(),allow_nan=False)); return 0
    import bpy
    from mathutils import Quaternion
    need(bpy.app.background and bpy.app.version[:2] == (5,1) and not bpy.data.filepath
         and "--factory-startup" in sys.argv and "--disable-autoexec" in sys.argv, "Root-leased empty Blender 5.1 factory background only")
    need("--threads" in sys.argv and sys.argv.index("--threads")+1<len(sys.argv) and sys.argv[sys.argv.index("--threads")+1]=="1", "Single root-owned --threads 1 only")
    need(sha(INPUT)==INPUT_SHA and sha(INSTALL)==INSTALL_SHA, "Exact installed input/report changed")
    sys.dont_write_bytecode=True
    for name,expected in PINS.items(): need(sha(HERE/name)==expected,"Frozen dependency changed: "+name)
    workflow=load("verify_actual_surface_workflow.py"); same=load("verify_actual_same_frame_pose.py")
    proof=load("prototype_final_surface_clearance.py")
    qa,diag,addon,surface=workflow.load_dependencies()
    artist=Path(json.loads(INSTALL.read_text(encoding="utf-8"))["artist_path"]).resolve()
    need(artist != INPUT.resolve() and artist.is_file(),"Exact artist origin unavailable")
    report={"prepared_only_source":True,"native_collection_completed":False,"production_effect_accepted":False,
        "artist_saved":False,"samples":[],"checks":[],"pins":PINS,"input_before":qa.file_state(INPUT),"artist_before":qa.file_state(artist),
        "source_manifest_before":diag.source_manifest(),"script_sha256":sha(Path(__file__)),"pure_checks":pure_checks(),
        "scope":"Two actual start-frame samples only. No projection/Hull/bake/replay/render or whole-Body coverage acceptance."}
    args.output.mkdir(); destination=args.output/"body_proxy_coverage.json"
    protection=None; began=time.perf_counter()
    try:
        source_name=workflow.motion_input_gate(args,report,qa,diag); addon.register()
        need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(INPUT),load_ui=False,use_scripts=False),"Exact installed input open failed")
        need(Path(bpy.data.filepath).resolve()==INPUT.resolve(),"Native filepath mismatch")
        source,rig,_saved=qa.owned_source(source_name); protection=qa.Protection()
        record,rig,actual,cloth,neutral=workflow.motion_objects(source,qa,surface); scene=bpy.context.scene
        need(scene.name==record["physics"]["surface"]["home_scene"],"Exact native home Scene missing")
        preflight=qa.saved_cache_preflight(source,record); report["saved_cache_preflight"]=preflight
        need(preflight["allowed"],"Saved cache unsafe; no input/artist cache touched")
        report["author_pose_sha256"]=qa.digest(same.pose_checkpoint(rig,qa)); report["author_playback_sha256"]=qa.digest(same.playback_state(qa))
        report["author_frame"]=[int(scene.frame_current),float(scene.frame_subframe)]; report["raw_protection_before"]=protection.summary()
        for i,action in enumerate(protection.action_refs): scene[f"CD_QA_AuthorAction_{i:04d}"]=action
        candidate=args.output/"scenes/Cosha_Dress_QA_proxy_coverage.blend"; qa.save_candidate(candidate,INPUT)
        scene.tool_settings.use_keyframe_insert_auto=False
        report["animation_backup"]=qa.backup_animation(scene,list(bpy.data.objects)+list(bpy.data.shape_keys),protection.action_refs)
        qa.skirt._activate(bpy.context,rig,"POSE"); qa.public_switch(bpy.ops.character_designer.body_ik_fk_switch,mode="FK")
        legs,axes,height=qa.body_inputs(rig,record)
        body,report["registered_body"]=qa.registered_body(bpy.context,rig,args)
        need(body is not None and report["registered_body"]["measured"] and body==bpy.data.objects.get(record["physics"]["surface"]["body"]),"Exact registered Body is unavailable")
        qa.tuning.apply(bpy.context,(source,),mode="AUTOMATIC")
        scene.frame_start,scene.frame_end=1,20; cloth.point_cache.frame_start,cloth.point_cache.frame_end,cloth.point_cache.frame_step=1,20,1
        settings=bpy.context.window_manager.character_designer_skirt; settings.source,settings.use_scene_range=source,True
        qa.save_candidate(candidate,INPUT)
        cache_dir=args.output/"native_cache"; cache_dir.mkdir(); cache=cloth.point_cache
        cache.filepath,cache.use_library_path,cache.use_disk_cache=str(cache_dir),False,True
        need(not cache.use_external and Path(bpy.path.abspath(cache.filepath)).resolve()==cache_dir.resolve(),"Cache outside private candidate")
        qa.public_switch(bpy.ops.character_designer.dress_motion_reset); scene.frame_set(1)
        report["cache_ownership"]={"candidate":str(candidate),"path":str(cache_dir),"artist_or_input_cache_reset":False}
        thigh_name=legs["L"]["chain"][0]; thigh=rig.pose.bones[thigh_name]
        need(not any(thigh.lock_rotation) and not (thigh.lock_rotations_4d and thigh.lock_rotation_w),"Native thigh locked; no override")
        common=(source,rig,actual,neutral,body,legs,cloth,scene,1)
        initial=collect("initial",common,args,qa,diag,same,proof,surface,report)
        base=thigh.matrix_basis.to_quaternion().copy(); thigh.rotation_mode="QUATERNION"
        thigh.rotation_quaternion=base @ Quaternion(axes[thigh_name],.55); rig.update_tag(refresh={"OBJECT"})
        leg=collect("left_thigh_0_55_same_frame",common,args,qa,diag,same,proof,surface,report)
        meters=float(scene.unit_settings.scale_length); delta=same.differences(initial,leg,qa,meters,qa.geometry_guard(meters))
        report["actual_leg_input"]={"thigh":thigh_name,"angle_rad":.55,"bone_local_axis":list(axes[thigh_name]),
            "definition":"Frozen QA actual native Rest inverse @ MainRig X; unkeyed FK channels, frame1 held",**delta,
            "confirmed":delta["knee_delta_m"]["L"]>height*.01*meters and delta["surfaces"]["Body"]["maximum_delta_m"]>qa.geometry_guard(meters)}
        report["native_identity_stable"]={name:initial["evidence"]["native_meshes"][name]["native_vertex_face_edge_sha256"]==leg["evidence"]["native_meshes"][name]["native_vertex_face_edge_sha256"]
            and initial["evidence"]["native_meshes"][name]["runtime_identity"]==leg["evidence"]["native_meshes"][name]["runtime_identity"]
            and initial["evidence"]["native_meshes"][name]["native_group_mapping"]==leg["evidence"]["native_meshes"][name]["native_group_mapping"]
            and initial["evidence"]["native_meshes"][name]["weights"]==leg["evidence"]["native_meshes"][name]["weights"] for name in initial["evidence"]["native_meshes"]}
        report["native_triangulation_changes"]={}
        for name,old in initial["evidence"]["native_meshes"].items():
            new=leg["evidence"]["native_meshes"][name]
            changed=[index for index,(a,b) in enumerate(zip(old["triangles"],new["triangles"])) if a!=b]
            report["native_triangulation_changes"][name]={"initial_sha256":old["native_triangulation_sha256"],
                "posed_sha256":new["native_triangulation_sha256"],"initial_count":len(old["triangles"]),"posed_count":len(new["triangles"]),
                "changed_corresponding_triangle_count":len(changed),"first_changed_triangle_ids":changed[:32],
                "changed":old["triangles"]!=new["triangles"],
                "scope":"Per-sample actual triangles stay exact in that sample only; coordinate-dependent tessellation is not a source topology edit or cross-Pose triangle correspondence proof."}
        surface.validate(source,rig,qa.skirt.read_record(source))
        report["canonical_validation_after_samples"]=True
        report["protected_raw_before_reload"]=protection.verify()
        report["native_collection_completed"]=bool(report["actual_leg_input"]["confirmed"] and all(report["native_identity_stable"].values())
            and report["protected_raw_before_reload"]["success"] and len(report["samples"])==2)
    except Exception as error:
        report["error"]={"reason":str(error),"traceback":traceback.format_exc()}
    finally:
        if protection is not None:
            try:
                need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(INPUT),load_ui=False,use_scripts=False),"Exact input reload failed")
                need(Path(bpy.data.filepath).resolve()==INPUT.resolve(),"Restored native filepath mismatch")
                source,rig,_saved=qa.owned_source(report["install_input"]["source"])
                report["protected_raw_after_reload"]=protection.verify()
                report["author_pose_restored"]=qa.digest(same.pose_checkpoint(rig,qa))==report["author_pose_sha256"]
                report["author_playback_restored"]=qa.digest(same.playback_state(qa))==report["author_playback_sha256"]
                report["author_frame_restored"]=[int(bpy.context.scene.frame_current),float(bpy.context.scene.frame_subframe)]==report["author_frame"]
                report["native_collection_completed"] &= report["protected_raw_after_reload"]["success"] and all(report[x] for x in ("author_pose_restored","author_playback_restored","author_frame_restored"))
            except Exception as error:
                report["native_collection_completed"]=False; report["restore_error"]=str(error)
        report["input_disk_exact"]=qa.file_state(INPUT)==report["input_before"]
        report["artist_disk_exact"]=qa.file_state(artist)==report["artist_before"]
        report["source_manifest_after"]=diag.source_manifest(); report["canonical_code_exact"]=report["source_manifest_after"]==report["source_manifest_before"]
        report["dependency_code_exact"]=all(sha(HERE/name)==expected for name,expected in PINS.items())
        report["script_code_exact"]=sha(Path(__file__))==report["script_sha256"]
        report["native_collection_completed"] &= all(report[x] for x in ("input_disk_exact","artist_disk_exact","canonical_code_exact","dependency_code_exact","script_code_exact"))
        report["elapsed_seconds"]=time.perf_counter()-began
        destination.write_text(json.dumps(diag.json_content(report),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        print(json.dumps({"native_collection_completed":report["native_collection_completed"],"report":str(destination),"production_effect_accepted":False}),flush=True)
    return 0 if report["native_collection_completed"] else 2


if __name__=="__main__":
    raise SystemExit(main(arguments()))
