"""Read-only prior-day comparison for today's zero-weight hand vertex."""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree
ROOT=Path(r"D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915")
prior=Path(r"D:\Blender\Projects\Character\X\outputs\animation_unity_20260914\source_182347.blend")
before=hashlib.sha256(prior.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(prior),load_ui=False)
obj=bpy.data.objects['Cosha']
arm=bpy.data.objects['CoshaRig']
deform={b.name for b in arm.data.bones if b.use_deform}
tree=KDTree(len(obj.data.vertices))
for v in obj.data.vertices:tree.insert(v.co,v.index)
tree.balance()
out={'prior_file':str(prior),'prior_file_sha256':before,'vertex_count':len(obj.data.vertices),'polygon_count':len(obj.data.polygons),'vertices':[]}
for current,x in ((3273,-0.45411473512649536),(923,0.45411473512649536),(3396,-0.4549466669559479)):
    coordinate=Vector((x,0.07133638858795166,-0.4229668974876404)) if current!=3396 else Vector((x,0.07859857380390167,-0.42261961102485657))
    co,index,distance=tree.find(coordinate)
    weights={obj.vertex_groups[g.group].name:g.weight for g in obj.data.vertices[index].groups}
    out['vertices'].append({'current_index':current,'prior_nearest_index':index,'distance':distance,'local':list(co),'all_weights':weights,'deform_total':sum(w for n,w in weights.items() if n in deform),'neighbors':sorted({j for e in obj.data.edges if index in e.vertices for j in e.vertices if j!=index}),'faces':[list(p.vertices) for p in obj.data.polygons if index in p.vertices]})
out['prior_file_unchanged']=before==hashlib.sha256(prior.read_bytes()).hexdigest()
assert out['prior_file_unchanged']
(ROOT/'zero_budget_history.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
