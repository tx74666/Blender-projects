"""Read only the new preview and check full breast-ring edges against surfaces."""
import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

OUT = Path(r'D:\Blender\Projects\Character\X\outputs/rig')
PREVIEW = OUT / 'X_body_wrap_0531_preview.blend'
sha_before = hashlib.sha256(PREVIEW.read_bytes()).hexdigest()
assert bpy.app.background
bpy.ops.wm.open_mainfile(filepath=str(PREVIEW), use_scripts=False)
rig = bpy.data.objects['CoshaRig']
rig.data.update_tag()
rig.update_tag(refresh={'OBJECT'})
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
record = json.loads(rig.data['character_designer_body_detail_visuals_v1'])
assert all(record['fit']['roles'][role].get('profile') == 'WRAP' for role in ('BREAST_L', 'BREAST_R'))
report = {'preview': str(PREVIEW), 'coordinate_space': 'armature',
          'samples_per_edge': 17, 'modes': {}}
for mode in ('rest', 'pose'):
    trees = {}
    for name in ('Cosha', 'Clothes'):
        obj = bpy.data.objects[name]
        evaluated = obj.evaluated_get(dg) if mode == 'pose' else None
        mesh = evaluated.to_mesh() if evaluated is not None else obj.data
        matrix = rig.matrix_world.inverted_safe() @ (evaluated.matrix_world if evaluated else obj.matrix_world)
        try:
            trees[name] = BVHTree.FromPolygons([matrix @ v.co for v in mesh.vertices],
                                              [list(p.vertices) for p in mesh.polygons])
        finally:
            if evaluated is not None:
                evaluated.to_mesh_clear()
    report['modes'][mode] = {}
    for role in ('BREAST_L', 'BREAST_R'):
        pb = rig.pose.bones[record['names'][role]]
        anchor = pb.custom_shape_transform or pb
        frame = anchor.matrix if mode == 'pose' else anchor.bone.matrix_local
        scale = pb.custom_shape_scale_xyz * (pb.bone.length if pb.use_custom_shape_bone_size else 1.)
        frame = frame @ Matrix.LocRotScale(pb.custom_shape_translation,
                    pb.custom_shape_rotation_euler.to_quaternion(), scale)
        vertices = [frame @ v.co for v in pb.custom_shape.data.vertices]
        edges = [list(edge.vertices) for edge in pb.custom_shape.data.edges]
        report['modes'][mode][role] = {}
        for name, tree in trees.items():
            hits, nearest = [], []
            for index, (a, b) in enumerate(edges):
                delta = vertices[b] - vertices[a]
                hit = tree.ray_cast(vertices[a], delta.normalized(), delta.length)[0]
                if hit is not None:
                    hits.append({'edge': index, 'position': list(hit)})
                for step in range(17):
                    point = vertices[a].lerp(vertices[b], step / 16)
                    location, normal, _, distance = tree.find_nearest(point)
                    nearest.append((distance, (point - location).dot(normal)))
            report['modes'][mode][role][name] = {
                'edges_checked': len(edges), 'crossings': len(hits),
                'minimum_distance': min(value[0] for value in nearest),
                'minimum_signed_distance': min(value[1] for value in nearest),
                'negative_nearest_samples': sum(value[1] < -1e-7 for value in nearest),
            }
            if hits:
                report['modes'][mode][role][name]['hits'] = hits
entries = [entry for mode in report['modes'].values() for ring in mode.values() for entry in ring.values()]
report['ok'] = all(entry['crossings'] == 0 and entry['minimum_signed_distance'] > 0 for entry in entries)
report['preview_file_unchanged'] = hashlib.sha256(PREVIEW.read_bytes()).hexdigest() == sha_before
assert report['preview_file_unchanged']
(OUT / 'body_wrap_0531_clearance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BODY_WRAP_0531_CLEARANCE', json.dumps(report), flush=True)
assert report['ok'], 'Breast ring clearance needs review.'
