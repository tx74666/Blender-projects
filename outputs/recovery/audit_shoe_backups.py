import bpy, json, os
from collections import Counter

PATHS = [r'D:\Blender\Projects\Character\X\Previews\X_Bone_Collections_0.42.3.blend', r'D:\Blender\Projects\Character\X\X.blend']
out = []
for path in PATHS:
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    item = {'file': path, 'objects': []}
    for ob in bpy.data.objects:
        if ob.type != 'MESH': continue
        mats = [m.name if m else None for m in ob.data.materials]
        if not any(s in (ob.name+' '+str(mats)).lower() for s in ['shoe','strap','metal','buckle']): continue
        mesh = ob.data
        adj = [set() for _ in mesh.vertices]
        for e in mesh.edges:
            a,b=e.vertices; adj[a].add(b); adj[b].add(a)
        unseen=set(range(len(mesh.vertices))); islands=[]
        while unseen:
            seed=min(unseen); unseen.remove(seed); stack=[seed]; ids=[]
            while stack:
                v=stack.pop(); ids.append(v)
                for n in adj[v]:
                    if n in unseen: unseen.remove(n); stack.append(n)
            vertset=set(ids)
            coords=[ob.matrix_world @ mesh.vertices[i].co for i in ids]
            polys=[p for p in mesh.polygons if p.vertices[0] in vertset]
            islands.append({'verts':len(ids),'faces':len(polys),'first_vertices':sorted(ids)[:10], 'material_counts':dict(Counter(mats[p.material_index] if p.material_index<len(mats) else str(p.material_index) for p in polys)), 'bbox_world':[[round(min(co[k] for co in coords),5) for k in range(3)],[round(max(co[k] for co in coords),5) for k in range(3)]], 'vertex_ids':sorted(ids)})
        item['objects'].append({'name':ob.name,'mesh':mesh.name,'vertices':len(mesh.vertices),'edges':len(mesh.edges),'faces':len(mesh.polygons),'materials':mats,'islands':islands})
    out.append(item)
dest=r'D:\Blender\Projects\Character\X\outputs\recovery\shoe_backup_audit.json'
with open(dest,'w',encoding='utf8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
for item in out:
    print('FILE', item['file'])
    for ob in item['objects']:
        print(json.dumps({k:v for k,v in ob.items() if k!='islands'},ensure_ascii=False))
        for island in ob['islands']:
            print(json.dumps({k:v for k,v in island.items() if k!='vertex_ids'},ensure_ascii=False))
print('AUDIT_OUTPUT',dest)
