"""Read-only mesh geometry evidence for anatomical eye pivot/aim estimation."""
import json
from pathlib import Path
import numpy as np
import bpy

OUT = Path(__file__).parent
SOURCE = r'D:\Blender\Projects\Character\X\outputs\rig\X_left_foot_reset_preview.blend'
bpy.ops.wm.open_mainfile(filepath=SOURCE, load_ui=False, use_scripts=False)
rig = bpy.data.objects['CoshaRig']
mesh = bpy.data.objects['Cosha']
to_rig = rig.matrix_world.inverted() @ mesh.matrix_world
all_xyz = np.array([list(to_rig @ v.co) for v in mesh.data.vertices], dtype=float)
report = {'source':SOURCE, 'armature':rig.name,'mesh':mesh.name,'coordinate_space':'armature local','saved':False,'eyes':{}}
adj = {v.index:set() for v in mesh.data.vertices}
for e in mesh.data.edges:
    a,b=e.vertices
    adj[a].add(b)
    adj[b].add(a)
for side in ('L','R'):
    name='eye.'+side
    group=mesh.vertex_groups[name]
    ids=[v.index for v in mesh.data.vertices if any(g.group==group.index and g.weight>0.01 for g in v.groups)]
    weights=[next(g.weight for g in mesh.data.vertices[i].groups if g.group==group.index) for i in ids]
    xyz=all_xyz[ids]
    center=xyz.mean(axis=0)
    _,s,vt=np.linalg.svd(xyz-center,full_matrices=False)
    normal=vt[-1]
    if normal[1]>0: normal=-normal
    basis=vt.copy()
    sphere_a=np.column_stack([2*xyz, np.ones(len(xyz))])
    sphere_b=np.sum(xyz*xyz,axis=1)
    coeff,residuals,rank,singular=np.linalg.lstsq(sphere_a,sphere_b,rcond=None)
    sphere_center=coeff[:3]
    radius=np.sqrt(np.dot(sphere_center,sphere_center)+coeff[3])
    radial_dist=np.linalg.norm(xyz-sphere_center,axis=1)
    sphere_error=radial_dist-radius
    component=set(ids)
    queue=list(ids)
    while queue:
        i=queue.pop()
        for j in adj[i]-component:
            component.add(j)
            queue.append(j)
    faces=[p for p in mesh.data.polygons if any(i in ids for i in p.vertices)]
    material_faces={}
    for p in faces:
        mat=mesh.material_slots[p.material_index].name if p.material_index<len(mesh.material_slots) else str(p.material_index)
        material_faces[mat]=material_faces.get(mat,0)+1
    border=[i for i in ids if any(j not in ids for j in adj[i])]
    direction=np.array(rig.data.bones[name].tail_local)-np.array(rig.data.bones[name].head_local)
    direction=direction/np.linalg.norm(direction)
    pivot=np.array(rig.data.bones[name].head_local)
    pivot_center_direction=center-pivot
    pivot_center_distance=float(np.linalg.norm(pivot_center_direction))
    pivot_center_direction/=pivot_center_distance
    best_center_error=float(np.linalg.norm(np.cross(center-pivot,direction)))
    normal_offsets=(xyz-center)@normal
    neighbor_groups={}
    for i in ids:
        for g in mesh.data.vertices[i].groups:
            if g.weight>0.0001:
                gn=mesh.vertex_groups[g.group].name
                neighbor_groups[gn]=neighbor_groups.get(gn,0)+1
    normals=np.array([list((to_rig.to_3x3().inverted().transposed()@p.normal).normalized()) for p in faces])
    mean_normal=normals.mean(axis=0)
    mean_normal/=np.linalg.norm(mean_normal)
    row={'weighted_vertex_count':len(ids),'weights_range':[min(weights),max(weights)],
         'weighted_vertex_ids':ids,'vertices':xyz.tolist(),
         'bounds':[xyz.min(axis=0).tolist(),xyz.max(axis=0).tolist()],
         'centroid':center.tolist(),'pca_spread':s.tolist(),'pca_front_normal':normal.tolist(),
         'pca_axes':basis.tolist(), 'angle_front_normal_to_bone_degrees':float(np.degrees(np.arccos(np.clip(np.dot(normal,direction),-1,1)))),
         'mean_polygon_normal':mean_normal.tolist(),'surface_normal_depth_range':[float(normal_offsets.min()),float(normal_offsets.max())],
         'pivot_to_centroid_direction':pivot_center_direction.tolist(),
         'pivot_to_centroid_distance':pivot_center_distance,
         'angle_pivot_to_centroid_to_bone_degrees':float(np.degrees(np.arccos(np.clip(np.dot(pivot_center_direction,direction),-1,1)))),
         'bone_axis_distance_to_centroid':best_center_error,
         'tail_distance_to_centroid':float(np.linalg.norm(np.array(rig.data.bones[name].tail_local)-center)),
         'existing_pivot_signed_depth_from_surface':float(np.dot(pivot-center,normal)),
         'fitted_sphere_center_signed_depth_from_surface':float(np.dot(sphere_center-center,normal)),
         'all_nonzero_weight_groups_on_patch':neighbor_groups,
         'sphere_fit':{'center':sphere_center.tolist(),'radius':float(radius),'rms_error':float(np.sqrt(np.mean(sphere_error*sphere_error))),
                       'max_error':float(np.max(np.abs(sphere_error))),'rank':int(rank),'condition':float(singular[0]/singular[-1])},
         'connected_component_vertex_count':len(component),'boundary_to_non_eye_vertex_count':len(border),
         'face_count_touching_eye_vertices':len(faces),'material_faces':material_faces,
         'rest_pivot':list(rig.data.bones[name].head_local),'rest_tail':list(rig.data.bones[name].tail_local),'rest_direction':direction.tolist(),
         'material_slots':[s.name for s in mesh.material_slots],
         'faces':[list(p.vertices) for p in faces],
         'component_ids':sorted(component) if len(component)<500 else None,
         'component_bounds':[all_xyz[list(component)].min(axis=0).tolist(),all_xyz[list(component)].max(axis=0).tolist()]}
    report['eyes'][name]=row
    print('EYE_GEOMETRY',name,json.dumps({k:v for k,v in row.items() if k not in {'vertices','faces','weighted_vertex_ids','component_ids','material_slots'}}))
(OUT/'x_eye_geometry_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
