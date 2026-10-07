"""Diagnostic closed-collider BVH coordinates only, over immutable movement V6.

The native Cloth/collider/input/RNA, epsilon, movement, and restore guards remain
unchanged. Original world failures are retained as Unknown with native witnesses.
Centered readback may measure a distance, but is never an effect acceptance.
"""
import ast
from collections import deque
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V6 = HERE / "verify_live_direct_cloth52_disposable_fixture_v6.py"
V6_SHA = "bb040e1694612542b520c313d7b59e5ceb0fd3de5cfda75d1ffd422ef8160d94"
QA = HERE / "validate_real_dress.py"
QA_SHA = "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046"
FAILURE = HERE / "actual_movement_stress_walk_v6_52_20261006_234851_024" / "result" / "input800_reproduction.json"
FAILURE_SHA = "7f478b983f14666a201d72ef87cc5e32533eca7e04419278611e3634201b1ec8"


def need(condition, message):
    if not condition:
        raise RuntimeError("MovementCenteredCollision52: " + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parent():
    need(sha(V6) == V6_SHA and sha(QA) == QA_SHA and sha(FAILURE) == FAILURE_SHA,
         "Immutable V6/ClosedCollider/failure evidence changed")
    spec = importlib.util.spec_from_file_location("movement_centered_frozen_v6", V6)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def point3(value):
    result = [float(x) for x in value]
    need(len(result) == 3 and all(math.isfinite(x) for x in result), "Complete finite native point required")
    return result


def centered_geometry(points, triangles):
    points = [point3(point) for point in points]
    triangles = [list(triangle) for triangle in triangles]
    need(points and triangles and all(len(face) == 3 and all(type(i) is int and 0 <= i < len(points) for i in face) for face in triangles),
         "Complete native indexed triangles required")
    center = [(min(p[i] for p in points) + max(p[i] for p in points)) * .5 for i in range(3)]
    local = [[p[i]-center[i] for i in range(3)] for p in points]
    return {"world_points": points, "triangles": triangles, "center_world": center, "centered_points": local}


def number(value):
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else {"status": "Unknown", "nonfinite": repr(value)}


def optional_point(value):
    return None if value is None else [number(x) for x in value]


class ObservedTree:
    """Read-only BVH proxy; preserve all native returns and retain last ray steps."""
    def __init__(self, tree, mesh_points, triangles):
        self.tree, self.points, self.triangles = tree, mesh_points, triangles
        self.reset()

    def reset(self):
        self.nearest, self.rays, self.calls = None, deque(maxlen=8), 0

    def triangle(self, index):
        if type(index) is int and 0 <= index < len(self.triangles):
            face = list(self.triangles[index])
            return {"native_triangle_index": index, "vertex_indices": face,
                    "points": [optional_point(self.points[i]) for i in face]}
        return {"native_triangle_index": index, "status": "Unknown"}

    def find_nearest(self, point):
        result = self.tree.find_nearest(point)
        location, normal, index, distance = result
        self.nearest = {"query": optional_point(point), "location": optional_point(location),
                        "normal": optional_point(normal), "distance": number(distance),
                        "triangle": self.triangle(index)}
        return result

    def ray_cast(self, origin, direction, remaining):
        result = self.tree.ray_cast(origin, direction, remaining)
        hit, normal, index, length = result
        self.calls += 1
        self.rays.append({"call": self.calls, "origin": optional_point(origin),
                          "direction": optional_point(direction), "remaining": number(remaining),
                          "hit": optional_point(hit), "normal": optional_point(normal), "length": number(length),
                          "triangle": self.triangle(index)})
        return result

    def witness(self):
        return {"nearest": self.nearest, "native_ray_calls": self.calls, "last_ray_steps": list(self.rays),
                "last_step_limit": 8, "algorithm_and_native_returns_changed": False}


def resolved_distance(value):
    need(type(value) in (int, float) and math.isfinite(value), "Centered distance remains Unknown/nonfinite")
    return float(value)


class DiagnosticCollider:
    def __init__(self, world, centered, geometry, entry, write, vector):
        self.world, self.centered, self.geometry = world, centered, geometry
        self.entry, self.write, self.vector = entry, write, vector
        self.world_retired = False
        world.tree = ObservedTree(world.tree, world.points, world.triangles)
        centered.tree = ObservedTree(centered.tree, centered.points, centered.triangles)

    def full_geometry(self):
        self.entry["original_native_geometry"] = {k: self.geometry[k] for k in ("world_points", "triangles")}

    def signed_distance(self, point):
        world_point = point3(point)
        self.entry["queries"] += 1
        world_value = None
        if not self.world_retired:
            self.world.tree.reset()
            try:
                world_value = resolved_distance(self.world.signed_distance(point))
            except Exception as error:
                self.world_retired = True
                self.full_geometry()
                self.entry["original_world_failure"] = {"status": "Unknown", "error": repr(error),
                    "actual_world_query": world_point, "witness": self.world.tree.witness(),
                    "subsequent_original_queries_unmeasured": True}
                self.write()  # The original failure survives any centered failure.
        else:
            self.entry["original_unmeasured_query_count"] += 1
        local = self.vector([world_point[i]-self.geometry["center_world"][i] for i in range(3)])
        self.centered.tree.reset()
        try:
            value = resolved_distance(self.centered.signed_distance(local))
        except Exception as error:
            self.full_geometry()
            self.entry["centered_failure"] = {"status": "Unknown", "error": repr(error),
                "actual_world_query": world_point, "centered_query": point3(local),
                "witness": self.centered.tree.witness(), "zero_substituted": False}
            self.write()
            raise RuntimeError("Centered diagnostic collider remains Unknown; no signed distance substituted") from error
        if world_value is not None:
            difference = abs(value-world_value)
            self.entry["maximum_resolved_world_centered_difference"] = max(self.entry["maximum_resolved_world_centered_difference"], difference)
            if difference > self.centered.epsilon:
                self.full_geometry()
                self.entry["resolved_disagreement"] = {"status": "Unknown", "actual_world_query": world_point,
                    "original_distance": world_value, "centered_distance": value, "difference": difference,
                    "unchanged_epsilon": self.centered.epsilon, "world_witness": self.world.tree.witness(),
                    "centered_witness": self.centered.tree.witness()}
                self.write()
                raise RuntimeError("World/centered signed diagnostics disagree beyond the original epsilon")
        elif "centered_first_retry" not in self.entry:
            self.entry["centered_first_retry"] = {"status": "measured", "actual_world_query": world_point,
                "centered_query": point3(local), "signed_distance": value, "witness": self.centered.tree.witness(),
                "original_world_status": "Unknown", "accepted": False}
            self.write()
        return value


def diagnostic_closed_collider(qa, obj, graph, epsilon, report, label, frame, write):
    from mathutils import Vector
    mesh = qa.world_mesh(obj, graph, triangles=True)
    geometry = centered_geometry(mesh["points"], mesh["triangles"])
    centered_mesh = {"points": [Vector(point) for point in geometry["centered_points"]], "triangles": mesh["triangles"]}
    world = qa.ClosedCollider(obj, graph, epsilon, mesh=mesh)
    centered = qa.ClosedCollider(obj, graph, epsilon, mesh=centered_mesh)
    entry = {"object": obj.name, "object_pointer": obj.as_pointer(), "label": label, "frame": frame,
        "native_vertices": len(mesh["points"]), "native_triangles": len(mesh["triangles"]),
        "geometry_sha256": hashlib.sha256(json.dumps(geometry, separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
        "center_world": geometry["center_world"], "epsilon_original": epsilon, "epsilon_changed": False,
        "world_convex": world.convex, "centered_convex": centered.convex,
        "queries": 0, "original_unmeasured_query_count": 0, "maximum_resolved_world_centered_difference": 0.,
        "scope": "Only numerical coordinates of read-only diagnostic BVH/query; physical objects and Cloth unchanged",
        "original_failure_or_unmeasured_is_not_a_zero_distance": True, "accepted": False}
    report.setdefault("closed_collider_centering_diagnostics", []).append(entry)
    return DiagnosticCollider(world, centered, geometry, entry, write, Vector)


def prepared_namespace(v6, v5, parts, args):
    producer = v6.dynamic_source
    old = 'native=qa.ClosedCollider(collider,graph,epsilon)'
    new = 'native=diagnostic_closed_collider(qa,collider,graph,epsilon,report,label,home.frame_current,write)'
    def modified(*values):
        source = producer(*values)
        need(source.count(old) == 1, "Unique closed-collider diagnostic call differs")
        result = source.replace(old, new, 1)
        need(result.replace(new, old, 1) == source, "V6 movement/physics/restore changed beyond diagnostic constructor")
        return result
    try:
        v6.dynamic_source = modified
        namespace = v6.prepared_namespace(v5, parts, args)
    finally:
        v6.dynamic_source = producer
    namespace["_live_private_dynamic_globals"]["diagnostic_closed_collider"] = diagnostic_closed_collider
    namespace["__file__"] = str(Path(__file__))
    namespace["PINS"].update({V6: V6_SHA, QA: QA_SHA, FAILURE: FAILURE_SHA, Path(__file__): sha(Path(__file__))})
    need(namespace["main"].__globals__ is namespace and v6.dynamic_source is producer,
         "Real Main globals or V6 source producer restoration differs")
    return namespace


def pure_checks():
    points = [[-1.,-2.,-3.], [4.,-2.,-3.], [-1.,5.,-3.], [-1.,-2.,6.]]
    faces = [[0,2,1], [0,1,3], [0,3,2], [1,2,3]]
    before = centered_geometry(points, faces)
    shift = [1234.5,-987.25,456.75]
    after = centered_geometry([[p[i]+shift[i] for i in range(3)] for p in points], faces)
    need(before["centered_points"] == after["centered_points"] and before["triangles"] == after["triangles"],
         "Translation changed diagnostic indexed geometry")
    query = [2.,3.,4.]
    need([query[i]-before["center_world"][i] for i in range(3)]
         == [query[i]+shift[i]-after["center_world"][i] for i in range(3)], "Query translation differs from geometry")
    class Tree:
        def find_nearest(self, point):return [0.,0.,0.],[0.,0.,1.],0,1.
        def ray_cast(self, *args):return [0.,0.,0.],[0.,0.,1.],0,0.
    observed = ObservedTree(Tree(),points,faces)
    expected = observed.tree.find_nearest(query)
    need(observed.find_nearest(query) == expected, "Nearest native return changed")
    for i in range(12):need(observed.ray_cast(query,[1.,0.,0.],1.) == ([0.,0.,0.],[0.,0.,1.],0,0.), "Ray native return changed")
    need(observed.witness()["native_ray_calls"] == 12 and len(observed.witness()["last_ray_steps"]) == 8,
         "Bounded ray witness missing")
    for value in (None,float("nan"),float("inf")):
        try:resolved_distance(value)
        except RuntimeError:pass
        else:need(False,"Unknown distance became zero/success")
    class Collider:
        def __init__(self,value):self.tree=Tree();self.points=points;self.triangles=faces;self.epsilon=1.e-6;self.value=value
        def signed_distance(self,point):
            self.tree.find_nearest(point);self.tree.ray_cast(point,[1.,0.,0.],1.)
            if self.value is None:raise RuntimeError("Unresolved parity ray at a collider seam")
            return self.value
    written=[]; entry={"queries":0,"original_unmeasured_query_count":0,"maximum_resolved_world_centered_difference":0.}
    diagnostic=DiagnosticCollider(Collider(None),Collider(-.25),before,entry,lambda:written.append(True),list)
    need(diagnostic.signed_distance(query)==-.25 and entry["original_world_failure"]["status"]=="Unknown"
         and entry["original_world_failure"]["actual_world_query"]==query and written,
         "Original native failure witness lost on centered retry")
    entry={"queries":0,"original_unmeasured_query_count":0,"maximum_resolved_world_centered_difference":0.}
    diagnostic=DiagnosticCollider(Collider(None),Collider(None),before,entry,lambda:written.append(True),list)
    try:diagnostic.signed_distance(query)
    except RuntimeError:need(entry["centered_failure"]["status"]=="Unknown" and not entry["centered_failure"]["zero_substituted"],"Unresolved status lost")
    else:need(False,"Both unresolved collider methods became success")
    return {"passed":True,"translation_and_query_invariance":True,"read_only_native_return_controls":True,
            "original_witness_persisted":True,"both_unknown_rejected":True,"nonfinite_negatives":3,"native":False,"accepted":False}


def main():
    v6=parent();v5=v6.parent();args=v6.arguments(v5)
    if args.pure_checks:
        print(json.dumps(pure_checks(),allow_nan=False));return 0
    parts=v5.components(args)
    v5.paired_component_proof(args.cold_proof,args.cold_proof_sha,args.input_proof,args.input_proof_sha)
    return prepared_namespace(v6,v5,parts,args)["main"](args)


if __name__ == "__main__":
    raise SystemExit(main())
