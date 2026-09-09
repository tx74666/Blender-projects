import bpy, json
from mathutils.kdtree import KDTree
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend', load_ui=False)
with open(r'D:\Blender\Projects\Character\X\outputs\recovery\shoe_backup_audit.json',encoding='utf8') as f: audit=json.load(f)[1]
src=bpy.data.objects['Shoes_Primitive']; dst=bpy.data.objects['Shoes']
islands=next(o for o in audit['objects'] if o['name']=='Shoes_Primitive')['islands']
tree=KDTree(len(dst.data.vertices))
for v in dst.data.vertices: tree.insert(dst.matrix_world@v.co,v.index)
tree.balance()
out={'source':src.name,'target':dst.name,'objects':{},'rings':[]}
for ob in (src,dst):
    out['objects'][ob.name]={'matrix_world':[list(r) for r in ob.matrix_world], 'modifiers':[{'name':m.name,'type':m.type,'show_viewport':m.show_viewport} for m in ob.modifiers], 'uv_layers':[u.name for u in ob.data.uv_layers], 'vertex_groups':[g.name for g in ob.vertex_groups], 'attributes':[(a.name,a.data_type,a.domain) for a in ob.data.attributes], 'shape_keys':ob.data.shape_keys.name if ob.data.shape_keys else None}
for island in islands:
    if island['first_vertices'][0] not in (1912,4184,5320):continue
    ids=island['vertex_ids']; near=[]
    for i in ids:
        _,j,d=tree.find(src.matrix_world@src.data.vertices[i].co)
        if d<1e-6:near.append((i,j,d))
    item={k:v for k,v in island.items() if k!='vertex_ids'};item['coordinate_matches']=near
    out['rings'].append(item)
dest=r'D:\Blender\Projects\Character\X\outputs\recovery\shoe_ring_match_audit.json'
with open(dest,'w',encoding='utf8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=False))
