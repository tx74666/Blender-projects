import bpy, sys, json, hashlib
from pathlib import Path
from mathutils import Matrix, Vector, Euler
from mathutils.bvhtree import BVHTree
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import head_neck_visuals
ROOT = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
source = ROOT / 'X_head_neck_052_preview.blend'
sha = hashlib.sha256(source.read_bytes()).hexdigest()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['CoshaRig']
record = head_neck_visuals.validate(rig)
bpy.context.view_layer.update()
head = rig.pose.bones[record['head']]
frame = rig.matrix_world @ head.matrix @ head.bone.matrix_local.inverted() @ Matrix(record['fit']['head_frame'])
inverse = frame.inverted()
body = bpy.data.objects['Cosha']
dg = bpy.context.evaluated_depsgraph_get()
obj = body.evaluated_get(dg)
mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
world_vertices = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
all_faces = [list(p.vertices) for p in mesh.polygons]
bvh = BVHTree.FromPolygons(world_vertices, all_faces)
selected_groups = {g.index for g in body.vertex_groups if g.name in {'Head', 'Neck', 'eye.L', 'eye.R'}}
selected = {v.index for v in mesh.vertices if sum(g.weight for g in v.groups if g.group in selected_groups) >= .05}
faces = [face for face in all_faces if all(i in selected for i in face)]
points = [list(inverse @ p) for p in world_vertices]
obj.to_mesh_clear()
widgets = {}
for name, entry in record['bindings'].items():
    pb = rig.pose.bones[name]
    anchor = pb.custom_shape_transform or pb
    scale = Vector(pb.custom_shape_scale_xyz) * (pb.length if pb.use_custom_shape_bone_size else 1)
    matrix = rig.matrix_world @ anchor.matrix @ Matrix.LocRotScale(pb.custom_shape_translation, Euler(pb.custom_shape_rotation_euler).to_quaternion(), scale)
    verts = [matrix @ v.co for v in pb.custom_shape.data.vertices]
    edges = [list(e.vertices) for e in pb.custom_shape.data.edges]
    crossings, signed_samples = [], []
    for index, (a,b) in enumerate(edges):
        delta = verts[b] - verts[a]
        hit, normal, face_index, distance = bvh.ray_cast(verts[a], delta.normalized(), delta.length)
        if hit is not None:
            crossings.append({'edge': index, 'point': list(inverse @ hit)})
        for step in range(41):
            point = verts[a].lerp(verts[b], step/40)
            nearest, normal, face_index, distance = bvh.find_nearest(point)
            signed_samples.append((point-nearest).dot(normal))
    widgets[name] = {'role': entry['role'], 'vertices': [list(inverse @ p) for p in verts], 'edges': edges,
        'body_intersecting_edges': crossings, 'minimum_signed_surface_clearance': min(signed_samples),
        'negative_samples': sum(d < -1e-4 for d in signed_samples), 'sample_count': len(signed_samples)}
payload = {'preview': str(source), 'frame': 'Head anatomical display frame: X right, Y back, Z up; evaluated saved pose',
    'vertices': points, 'faces': faces, 'widgets': widgets, 'fit': record['fit'],
    'preview_unchanged': hashlib.sha256(source.read_bytes()).hexdigest() == sha}
(ROOT/'head_neck_visual_qa_geometry.json').write_text(json.dumps(payload), encoding='utf-8')
print('HEAD_NECK_VISUAL_QA', json.dumps({name: {k:v for k,v in w.items() if k not in {'vertices','edges'}} for name,w in widgets.items()}), flush=True)
