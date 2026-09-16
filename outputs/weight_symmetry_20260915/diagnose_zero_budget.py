"""Inspect two zero-deform-total hand vertices; never save or alter weights."""
from pathlib import Path
import hashlib
import json
import struct
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT=Path(r"D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915")
INPUT=ROOT/"X_saved_input.blend"
EXPECTED="5FB5B96E5C629340FEC5CC2696E0861A5C0884A1F1E03BBFEAF9C608CB96CA79"
assert hashlib.sha256(INPUT.read_bytes()).hexdigest().upper()==EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(INPUT),load_ui=False)
obj=bpy.data.objects['Cosha']
arm=bpy.data.objects['CoshaRig']
mesh=obj.data
coords=[v.co.copy() for v in mesh.vertices]
transform=obj.matrix_world.inverted_safe()@arm.matrix_world
bones={b.name:(transform@b.head_local,transform@b.tail_local) for b in arm.data.bones if b.use_deform}
def snapshot():
    return (tuple(tuple(v.co) for v in mesh.vertices),tuple(tuple(e.vertices) for e in mesh.edges),tuple(tuple(p.vertices) for p in mesh.polygons),tuple((g.name,g.index,g.lock_weight) for g in obj.vertex_groups),tuple(tuple((g.group,g.weight) for g in v.groups) for v in mesh.vertices))
before=snapshot()
def weights(index):
    return {obj.vertex_groups[g.group].name:float(g.weight) for g in mesh.vertices[index].groups}
def segment(point,a,b):
    ab=b-a
    t=(point-a).dot(ab)/ab.length_squared if ab.length_squared else 0
    nearest=a+max(0,min(1,t))*ab
    return {"distance":(point-nearest).length,"fraction":t,"length":ab.length,"head":list(a),"tail":list(b),"vector":list(ab),"normalized_vector":list(ab.normalized())}
def nearest(point):
    return sorted(({"name":name,**segment(point,a,b)} for name,(a,b) in bones.items()),key=lambda r:r['distance'])[:8]
def deform_weights(index):
    return {n:w for n,w in weights(index).items() if n in bones and w>1e-8}
def bary(p,a,b,c):
    v0,v1,v2=b-a,c-a,p-a
    d00,d01,d11,d20,d21=v0.dot(v0),v0.dot(v1),v1.dot(v1),v2.dot(v0),v2.dot(v1)
    denom=d00*d11-d01*d01
    if abs(denom)<1e-24:return None
    v=(d11*d20-d01*d21)/denom;w=(d00*d21-d01*d20)/denom
    return [1-v-w,v,w]
mesh.calc_loop_triangles()
triangles=[tuple(t.vertices) for t in mesh.loop_triangles]
out={"input_sha256":EXPECTED,"mesh":obj.name,"vertex_count":len(mesh.vertices),"vertices":[]}
for index in (3273,923):
    co=coords[index]
    reflected=Vector((-co.x,co.y,co.z))
    side=-1 if co.x>0 else 1
    source_name='hand.L' if side>0 else 'hand.R'
    source_tris=[t for t in triangles if all(coords[i].x*side>=-1.9505614642319843e-5 for i in t) and any(coords[i].x*side>1.9505614642319843e-5 for i in t)]
    bvh=BVHTree.FromPolygons(coords,source_tris,all_triangles=True)
    surface,normal,tri_index,distance=bvh.find_nearest(reflected)
    tri=source_tris[tri_index]
    bc=bary(surface,*(coords[i] for i in tri))
    sampled={}
    if bc:
        for factor,vertex in zip(bc,tri):
            for name,weight in deform_weights(vertex).items():
                sampled[name]=sampled.get(name,0)+factor*weight
    source_indices=[i for i,c in enumerate(coords) if c.x*side>1.9505614642319843e-5]
    tree=KDTree(len(source_indices))
    for i in source_indices:tree.insert(coords[i],i)
    tree.balance()
    nc,ni,nd=tree.find(reflected)
    neighbors=sorted({j for e in mesh.edges if index in e.vertices for j in e.vertices if j!=index})
    faces=[{"index":p.index,"vertices":list(p.vertices)} for p in mesh.polygons if index in p.vertices]
    out['vertices'].append({"index":index,"local":list(co),"world":list(obj.matrix_world@co),"all_weights":weights(index),"positive_deform_weights":deform_weights(index),"deform_total":sum(w for n,w in weights(index).items() if n in bones),"nearest_bones":nearest(co),"neighbors":[{"index":i,"local":list(coords[i]),"edge_length":(coords[i]-co).length,"positive_deform_weights":deform_weights(i),"deform_total":sum(w for n,w in weights(i).items() if n in bones)} for i in neighbors],"faces":faces,"source_group":source_name,"reflected_local":list(reflected),"nearest_reflected_vertex":{"index":ni,"distance":nd,"weights":deform_weights(ni)},"surface":{"triangle":tri,"point":list(surface),"distance":distance,"normal":list(normal),"barycentric":bc,"triangle_deform_weights":[deform_weights(i) for i in tri],"sampled_positive_deform_weights":{n:w for n,w in sampled.items() if w>1e-8},"sampled_deform_total":sum(sampled.values()),"sampled_hand_weight":sampled.get(source_name,0),"source_hand_bone":segment(surface,*bones[source_name])}})
out['state_unchanged']=snapshot()==before
out['file_unchanged']=hashlib.sha256(INPUT.read_bytes()).hexdigest().upper()==EXPECTED
assert out['state_unchanged'] and out['file_unchanged']
(ROOT/'zero_budget_diagnostic.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
