"""Independent closed-mesh sign diagnostic over immutable movement/centered QA.

Every query uses proved native indexed topology and either strict native AABB
exclusion or double solid-angle winding. Old ray failures remain Unknown, with
their first witness retained. No physical geometry, epsilon or acceptance changes.
"""
import ast
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PREVIOUS = HERE / "verify_live_direct_cloth52_movement_centered_collision.py"
PREVIOUS_SHA = "f1721a793a50e80bfd27cc641da5dd5355afe22926bc81fe8c89370332dc67ce"
EVIDENCE = HERE / "actual_movement_stress_run_centered_52_20261007_001154_735" / "result" / "input800_reproduction.json"
EVIDENCE_SHA = "cc28a9e5bae1bef471cfd1b0a5ea4cc92c7f525228bedb0ae72d5c677ae5805a"
OFFICIAL = {"project": "https://igl.ethz.ch/projects/winding-number/",
            "formula": "https://raw.githubusercontent.com/libigl/libigl/main/include/igl/solid_angle.cpp"}
FLOAT64_EPS = 2.**-52


def need(condition, message):
    if not condition:
        raise RuntimeError("MovementWindingCollision52: Unknown: " + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parent():
    need(sha(PREVIOUS) == PREVIOUS_SHA and sha(EVIDENCE) == EVIDENCE_SHA,
         "Immutable centered adapter/run failure changed")
    spec = importlib.util.spec_from_file_location("movement_winding_frozen_centered", PREVIOUS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def point3(value):
    result = [float(x) for x in value]
    need(len(result) == 3 and all(math.isfinite(x) for x in result), "Complete finite point required")
    return result


def sub(a, b):return [a[i]-b[i] for i in range(3)]
def dot(a, b):return math.fsum(a[i]*b[i] for i in range(3))
def cross(a, b):return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def integer_winding(value, count):
    tolerance = 256.*count*FLOAT64_EPS
    need(type(value) in (int,float) and math.isfinite(value), "Nonfinite winding sum")
    nearest = round(value)
    need(nearest in (0,1) and abs(value-nearest) <= tolerance,
         "Noninteger, inverted or multiply-wound query; no inside/outside substituted")
    return {"winding": value, "integer": nearest, "residual": abs(value-nearest),
            "Float64_sum_budget": tolerance, "inside": nearest == 1}


class ClosedWinding:
    def __init__(self, points, triangles):
        self.points = [point3(p) for p in points]
        self.faces = [list(face) for face in triangles]
        need(len(self.points) >= 4 and self.faces and all(len(face)==3 and len(set(face))==3
             and all(type(i) is int and 0 <= i < len(self.points) for i in face) for face in self.faces),
             "Incomplete/degenerate native triangle indices")
        need(len({tuple(sorted(face)) for face in self.faces}) == len(self.faces), "Duplicate native triangle")
        self.lower = [min(p[i] for p in self.points) for i in range(3)]
        self.upper = [max(p[i] for p in self.points) for i in range(3)]
        self.center = [(a+b)*.5 for a,b in zip(self.lower,self.upper)]
        self.local = [sub(p,self.center) for p in self.points]
        directed, neighbors, used = defaultdict(list), defaultdict(set), set()
        volume_terms=[]; minimum_area2=None
        for face in self.faces:
            a,b,c=[self.local[i] for i in face]
            ab,ac,bc=sub(b,a),sub(c,a),sub(c,b)
            area2=math.sqrt(dot(cross(ab,ac),cross(ab,ac)))
            edge2=max(dot(ab,ab),dot(ac,ac),dot(bc,bc))
            need(math.isfinite(area2) and area2 > 64.*FLOAT64_EPS*edge2,
                 "Zero/numerically degenerate native triangle")
            minimum_area2=area2 if minimum_area2 is None else min(minimum_area2,area2)
            volume_terms.append(dot(a,cross(b,c))/6.)
            used.update(face)
            for first,second in zip(face,face[1:]+face[:1]):
                directed[tuple(sorted((first,second)))].append((first,second))
                neighbors[first].add(second);neighbors[second].add(first)
        need(used == set(range(len(self.points))), "Native collider has unused/uncovered vertices")
        need(all(len(uses)==2 and uses[0] == tuple(reversed(uses[1])) for uses in directed.values()),
             "Open/nonmanifold collider or inconsistent adjacent triangle winding")
        visited=set();pending=[0]
        while pending:
            first=pending.pop()
            if first not in visited:
                visited.add(first);pending.extend(neighbors[first]-visited)
        need(len(visited)==len(self.points), "Disconnected closed collider")
        volume=math.fsum(volume_terms)
        volume_budget=256.*FLOAT64_EPS*math.fsum(abs(v) for v in volume_terms)
        need(math.isfinite(volume) and volume > volume_budget,
             "Inverted/zero/uncertain native closed volume orientation")
        self.proof={"status":"measured","native_vertices":len(self.points),"native_triangles":len(self.faces),
            "all_vertices_covered":True,"each_edge_twice_opposite":True,"single_connected_component":True,
            "duplicate_or_degenerate_triangles":False,"signed_volume_world_units3":volume,
            "volume_Float64_sum_budget":volume_budget,"minimum_double_area":minimum_area2,
            "orientation":"Consistent positive closed winding","lower_native_world":self.lower,"upper_native_world":self.upper,
            "center_world":self.center,"winding_integer_budget":256.*len(self.faces)*FLOAT64_EPS,
            "no_extra_native_coordinate_precision_claimed":True,"self_intersection_checked":False,"accepted":False}

    def winding(self, point):
        local_point=sub(point3(point),self.center)
        relative=[sub(p,local_point) for p in self.local]
        lengths=[math.sqrt(dot(v,v)) for v in relative]
        need(all(math.isfinite(length) and length > 0. for length in lengths), "Query coincides with native triangle vertex")
        angles=[]
        for ia,ib,ic in self.faces:
            a,b,c=relative[ia],relative[ib],relative[ic]
            la,lb,lc=lengths[ia],lengths[ib],lengths[ic]
            determinant=dot(a,cross(b,c))
            determinant_budget=64.*FLOAT64_EPS*math.fsum(abs(a[i]*b[j]*c[k])
                for i,j,k in ((0,1,2),(0,2,1),(1,0,2),(1,2,0),(2,0,1),(2,1,0)))
            if abs(determinant)<=determinant_budget:
                normal=cross(sub(b,a),sub(c,a));side_budget=64.*FLOAT64_EPS*dot(normal,normal)
                sides=(dot(normal,cross(a,b)),dot(normal,cross(b,c)),dot(normal,cross(c,a)))
                need(not all(side>=-side_budget for side in sides),
                     "Query is on/numerically unresolved at a native triangle boundary")
            denominator=math.fsum((la*lb*lc,dot(b,c)*la,dot(c,a)*lb,dot(a,b)*lc))
            need(math.isfinite(determinant) and math.isfinite(denominator)
                 and (determinant != 0. or denominator != 0.), "Undefined triangle solid angle")
            angles.append(math.atan2(determinant,denominator)/(2.*math.pi))
        return integer_winding(math.fsum(angles),len(self.faces))

    def classify(self, point):
        point=point3(point)
        if any(point[i] < self.lower[i] or point[i] > self.upper[i] for i in range(3)):
            return {"method":"strict_native_AABB_outside","inside":False,"winding":"NotNeededOutsideProvedBounds"}
        return dict(self.winding(point),method="double_closed_solid_angle")


class WindingCollider:
    def __init__(self, previous, model, write):
        self.previous,self.model,self.write=previous,model,write
        self.retired=False
        self.stats={"topology":model.proof,"official":OFFICIAL,"queries":0,"AABB_outside_queries":0,
            "solid_angle_queries":0,"inside_queries":0,"epsilon_band_measured_queries":0,
            "maximum_winding_integer_residual":0.,"legacy_ray_status":"Observer only, never sign ground truth",
            "signed_magnitude":"Original centered native BVH nearest; original epsilon",
            "native_collider_or_Cloth_modified":False,"accepted":False}
        previous.entry["independent_winding_sign"]=self.stats

    def observe(self, point, primary):
        old=self.previous
        if self.retired:
            old.entry["original_unmeasured_query_count"]+=1
            return
        observed={};unknown=False
        for name,collider in (("world",old.world),("centered",old.centered)):
            collider.tree.reset()
            try:
                value=collider.signed_distance(point if name=="world" else old.vector(sub(point3(point),old.geometry["center_world"])))
                need(type(value) in (int,float) and math.isfinite(value),"Legacy ray returned nonfinite")
                observed[name]={"status":"measured","signed_distance":value,"witness":collider.tree.witness()}
                if abs(value)>collider.epsilon and abs(primary)>collider.epsilon and (value<0.) != (primary<0.):unknown=True
            except Exception as error:
                observed[name]={"status":"Unknown","error":repr(error),"witness":collider.tree.witness()};unknown=True
        if all(observed[name]["status"]=="measured" for name in observed):
            unknown=unknown or abs(observed["world"]["signed_distance"]-observed["centered"]["signed_distance"])>old.centered.epsilon
        if unknown:
            self.retired=True;old.full_geometry()
            self.stats["legacy_ray_status"]="Unknown; stopped after first failure/contradiction"
            self.stats["first_legacy_unknown"]={"status":"Unknown","actual_world_query":point3(point),
                "old_ray_observations":observed,"independent_signed_distance":primary,
                "independent_classification":self.model.classify(point),"old_failed_parent_upgraded":False,"accepted":False}
            self.write()

    def signed_distance(self, point):
        old=self.previous;old.entry["queries"]+=1;self.stats["queries"]+=1
        world_point=point3(point)
        old.centered.tree.reset()
        try:
            local=old.vector(sub(world_point,old.geometry["center_world"]))
            location,normal,index,distance=old.centered.tree.find_nearest(local)
            need(location is not None and type(index) is int and 0 <= index < len(self.model.faces)
                 and type(distance) in (int,float) and math.isfinite(distance) and distance >= 0.,
                 "Invalid original centered nearest magnitude")
            sign=self.model.classify(world_point)
        except Exception as error:
            old.full_geometry()
            self.stats["query_failure"]={"status":"Unknown","error":repr(error),"actual_world_query":world_point,
                "nearest_witness":old.centered.tree.witness(),"zero_substituted":False}
            self.write();raise
        if sign["method"]=="strict_native_AABB_outside":self.stats["AABB_outside_queries"]+=1
        else:
            self.stats["solid_angle_queries"]+=1
            self.stats["maximum_winding_integer_residual"]=max(self.stats["maximum_winding_integer_residual"],sign["residual"])
        self.stats["inside_queries"]+=int(sign["inside"])
        if distance<=old.centered.epsilon:
            self.stats["epsilon_band_measured_queries"]+=1
            value=0.  # Only a resolved sign and the unchanged native distance band.
        else:value=-float(distance) if sign["inside"] else float(distance)
        self.observe(point,value)
        return value


def winding_closed_collider(previous_module, qa, obj, graph, epsilon, report, label, frame, write):
    previous=previous_module.diagnostic_closed_collider(qa,obj,graph,epsilon,report,label,frame,write)
    try:model=ClosedWinding(previous.geometry["world_points"],previous.geometry["triangles"])
    except Exception as error:
        previous.full_geometry()
        previous.entry["independent_winding_sign"]={"status":"Unknown","error":repr(error),"accepted":False}
        write();raise
    return WindingCollider(previous,model,write)


def full_surface_body_crossings(diag, final, body, bounds, limit, epsilon):
    need(len(final["points"])==3040 and set(final["free_indices"]).issubset(range(3040))
         and len(set(final["free_indices"]))==2880,"Complete final3040/fixed160 diagnostic partition required")
    complete=dict(final,free_indices=list(range(3040)))
    result=diag.triangle_crossings(complete,body,bounds,limit,epsilon)
    covered=(result.get("dress_region_triangles")==len(final["triangles"])
             and result.get("body_region_triangles")==len(body["triangles"]))
    result["full_surface_filter"]={"all_native_final_vertices":3040,"included_fixed_vertices":160,
        "excluded_fixed_vertices":0,"native_final_triangles":len(final["triangles"]),
        "tested_final_triangles":result.get("dress_region_triangles"),"native_Body_triangles":len(body["triangles"]),
        "tested_Body_triangles":result.get("body_region_triangles"),"complete":covered,"accepted":False}
    if not covered:
        result.update(status="Unknown_incomplete_full_surface",actual_crossing_pair_count=None)
    return result


def full_surface_source(source):
    changes=(
        ('crossing=diag.triangle_crossings(meshes["final3040"],body_mesh,bounds,args.triangle_pair_limit,epsilon)',
         'crossing=full_surface_body_crossings(diag,meshes["final3040"],body_mesh,bounds,args.triangle_pair_limit,epsilon)'),
        ('"actual_final_free_signed_vertices":qa.collision_metrics(meshes["final3040"]["points"],native,metres,meshes["final3040"]["free_indices"])',
         '"actual_final_all_signed_vertices":qa.collision_metrics(meshes["final3040"]["points"],native,metres,range(3040)),"sample_scope":"All3040 including fixed160"'),
        ('            contact["Unknown_if_incomplete"]=crossing["status"]!="measured" or any(contact["unresolved_counts"].values())\n',
         '            contact["full_surface_filter"]=crossing["full_surface_filter"]\n'
         '            contact["Unknown_if_incomplete"]=crossing["status"]!="measured" or any(contact["unresolved_counts"].values()) or not crossing["full_surface_filter"]["complete"]\n'),
    )
    result=source
    for old,new in changes:
        need(result.count(old)==1,"Unique complete-final diagnostic scope replacement differs")
        result=result.replace(old,new,1)
    reverse=result
    for old,new in reversed(changes):reverse=reverse.replace(new,old,1)
    need(reverse==source,"Physical/input/movement/restore changed outside complete-final diagnostic scope")
    return result


def prepared_namespace(previous, v6, v5, parts, args):
    producer=v6.dynamic_source
    try:
        v6.dynamic_source=lambda *values:full_surface_source(producer(*values))
        namespace=previous.prepared_namespace(v6,v5,parts,args)
    finally:v6.dynamic_source=producer
    namespace["_live_private_dynamic_globals"].update(
        diagnostic_closed_collider=lambda *values:winding_closed_collider(previous,*values),
        full_surface_body_crossings=full_surface_body_crossings)
    namespace["__file__"]=str(Path(__file__))
    namespace["PINS"].update({PREVIOUS:PREVIOUS_SHA,EVIDENCE:EVIDENCE_SHA,Path(__file__):sha(Path(__file__))})
    need(namespace["main"].__globals__ is namespace and namespace["restore_program"] is parts[0].restore_dynamic
         and v6.dynamic_source is producer,
         "Real Main/unchanged restorer identity differs")
    return namespace


def pure_checks():
    before=sha(EVIDENCE)
    evidence=json.loads(EVIDENCE.read_text(encoding="utf-8"))
    matches=[e for e in evidence["closed_collider_centering_diagnostics"] if e.get("frame")==30 and "resolved_disagreement" in e]
    need(len(matches)==1,"Exact f30 native disagreement fixture missing")
    entry=matches[0];geometry=entry["original_native_geometry"];query=entry["resolved_disagreement"]["actual_world_query"]
    actual=ClosedWinding(geometry["world_points"],geometry["triangles"])
    result=actual.winding(query)
    need(result["integer"]==0,"Native f30 winding does not independently prove outside")
    rays=entry["resolved_disagreement"]["world_witness"]["last_ray_steps"]
    repeated=[(a,b) for a,b in zip(rays,rays[1:]) if a["triangle"].get("native_triangle_index")==b["triangle"].get("native_triangle_index")==45]
    need(repeated and repeated[0][1]["length"]<entry["epsilon_original"],"Native tri45 repeated tiny ray hit witness differs")
    points=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
    faces=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
    model=ClosedWinding(points,faces)
    need(model.winding([.1,.1,.1])["integer"]==1 and model.winding([2.,2.,2.])["integer"]==0,"Closed tetra inside/outside failed")
    shift=[1234.5,-987.25,456.75]
    shifted=ClosedWinding([[p[i]+shift[i] for i in range(3)] for p in geometry["world_points"]],geometry["triangles"])
    need(shifted.winding([query[i]+shift[i] for i in range(3)])["integer"]==0,"Actual native geometry translation changed winding")
    negatives=0
    cases=[(points,faces[:-1]),(points,[list(reversed(faces[0]))]+faces[1:]),(points,faces+[faces[0]]),
           (points,[list(reversed(f)) for f in faces]),([points[0],points[1],points[1],points[3]],faces),
           ([[float("nan"),0.,0.]]+points[1:],faces),
           (points+[[p[0]+3.,p[1],p[2]] for p in points],faces+[[i+4 for i in f] for f in faces])]
    for p,f in cases:
        try:ClosedWinding(p,f)
        except RuntimeError:negatives+=1
        else:need(False,"Malformed/open/inverted/disconnected topology admitted")
    for value in (.5,-1.,2.,float("nan")):
        try:integer_winding(value,168)
        except RuntimeError:negatives+=1
        else:need(False,"Unresolved/inverted/multiple winding became a sign")
    for q in ([0.,0.,0.],[0.,.2,.2],[float("nan"),0.,0.]):
        try:model.winding(q)
        except RuntimeError:negatives+=1
        else:need(False,"On-surface/nonfinite query became a proved sign")
    class Crossing:
        def triangle_crossings(self,final,body,bounds,limit,epsilon):
            need(final["free_indices"]==list(range(3040)),"Fixed160 skipped by diagnostic copy")
            return {"status":"measured","dress_region_triangles":len(final["triangles"]),
                    "body_region_triangles":len(body["triangles"]),"actual_crossing_pair_count":1}
    final={"points":[[0.,0.,0.]]*3040,"triangles":[[0,1,2]],"free_indices":list(range(160,3040))}
    body={"triangles":[[0,1,2]]}
    scoped=full_surface_body_crossings(Crossing(),final,body,{},10,1.e-7)
    need(scoped["full_surface_filter"]["complete"] and final["free_indices"]==list(range(160,3040)),
         "Complete diagnostic scope mutated native final free partition")
    class Incomplete(Crossing):
        def triangle_crossings(self,*values):
            result=super().triangle_crossings(*values);result["dress_region_triangles"]=0;return result
    need(full_surface_body_crossings(Incomplete(),final,body,{},10,1.e-7)["actual_crossing_pair_count"] is None,
         "Missing full-surface coverage became zero/pass")
    need(sha(EVIDENCE)==before==EVIDENCE_SHA,"Actual native failure fixture changed")
    return {"passed":True,"native_f30_topology":actual.proof,"native_f30_winding":result,
        "original_ray_tri45_repeated_hit_confirmed":True,"double_translation_invariance":True,
        "tetra_inside_outside":True,"strict_Unknown_negatives":negatives,"all_future_native_3_proxies_use_same_proof":True,
        "full3040_and_all_triangles_scope":True,"incomplete_coverage_remains_Unknown":True,
        "new_native":False,"old_native_failure_upgraded":False,"accepted":False}


def main():
    previous=parent();v6=previous.parent();v5=v6.parent();args=v6.arguments(v5)
    if args.pure_checks:
        print(json.dumps(pure_checks(),allow_nan=False));return 0
    parts=v5.components(args)
    v5.paired_component_proof(args.cold_proof,args.cold_proof_sha,args.input_proof,args.input_proof_sha)
    return prepared_namespace(previous,v6,v5,parts,args)["main"](args)


if __name__=="__main__":
    raise SystemExit(main())
