import json, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector
sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/addons')
from character_designer import finger_internal as internal
path = Path('D:/Blender/Projects/Character/X/outputs/mark_alignment_diagnostic_20260922.json')
d = json.loads(path.read_text())
mesh = bpy.data.meshes.new('readonly_diagnostic_copy')
mesh.from_pydata(d['mesh_vertices'], [], d['mesh_faces'])
bm = bmesh.new(); bm.from_mesh(mesh)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
body = d['body']; points = list(map(Vector, d['points']))
used = {bm.faces[i] for i in body['faces']}
report = []
for layer in range(4):
    borders = {e for f in used for e in f.edges if sum(g in used for g in e.link_faces) == 1}
    ring=[]
    todo=set(borders)
    edge=next(iter(todo)); vert=edge.verts[0]
    while todo:
        choices=[e for e in vert.link_edges if e in todo]
        if not choices: break
        edge=choices[0]; todo.remove(edge); ring.append(vert.index); vert=edge.other_vert(vert)
    local=dict(body, faces=sorted(f.index for f in used), rings=[ring]+body['rings'][1:])
    try:
        v=internal.Volume(bm, local)
        row={'layer':layer, 'faces':len(used), 'boundary':ring, 'root_inside':v.inside(points[0]), 'root_distance':v.distance(points[0]),
             'segments':[v.certify((a,b),d['margin']*.5) for a,b in zip(points,points[1:])]}
    except Exception as exc:
        row={'layer':layer,'error':str(exc)}
    report.append(row)
    used.update(g for e in borders for g in e.link_faces)
print('ACTUAL_ROOT_PATCH',json.dumps(report),flush=True)
bm.free()
