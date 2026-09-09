"""Round the stock head widget only; validate a preview or save X with backup."""
import bpy
import hashlib
import json
import shutil
import sys
from array import array
from datetime import datetime
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import head_neck_visuals as hn, eye_controls as eyes, limb_ik, limb_ik_fk

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
source = ROOT / 'X.blend'
apply = '--apply' in sys.argv
sha = hashlib.sha256(source.read_bytes()).hexdigest()
cd.register()
bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
rig = bpy.data.objects['CoshaRig']
record = hn.validate(rig)
head = rig.pose.bones[record['head']]
widget = head.custom_shape.data
local = head.bone.matrix_local.inverted() @ Matrix(record['fit']['head_frame'])
legacy, legacy_edges = hn._geometry('HEAD', record['fit'], rounded=False)
assert len(legacy) == len(widget.vertices), 'Preserve artist-edited geometry for review.'
assert max((local @ Vector(p) - v.co).length for p,v in zip(legacy, widget.vertices)) < 1e-6
assert {tuple(sorted(e)) for e in legacy_edges} == {tuple(sorted(e.vertices)) for e in widget.edges}

def digest():
    data = {'objects': [], 'bones': [], 'collections': [], 'actions': []}
    for obj in sorted(bpy.data.objects, key=lambda o:o.name):
        item = [obj.name, obj.type, [list(row) for row in obj.matrix_world]]
        if obj.type == 'MESH' and obj.data != widget:
            item += [[list(v.co) for v in obj.data.vertices],
                     [list(p.vertices) for p in obj.data.polygons],
                     [g.name for g in obj.vertex_groups],
                     [[(g.group,g.weight) for g in v.groups] for v in obj.data.vertices]]
        data['objects'].append(item)
    for pb in rig.pose.bones:
        data['bones'].append([pb.name, eyes._state(pb.bone), limb_ik._pose_shape_json_state(pb),
                              [list(row) for row in pb.matrix_basis], list(pb.color.custom.normal),
                              list(pb.color.custom.select), list(pb.color.custom.active)])
    data['collections'] = [[c.name, sorted(c.bones.keys()), c.is_visible] for c in rig.data.collections_all]
    for action in bpy.data.actions:
        curves = []
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves += [[fc.data_path,fc.array_index,[(list(p.co),p.interpolation) for p in fc.keyframe_points]] for fc in bag.fcurves]
        data['actions'].append([action.name,curves])
    data['eye_record'] = rig.data.get(eyes.RECORD_KEY)
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

def poses():
    limb_ik_fk._update(bpy.context,rig)
    return {pb.name:pb.matrix.copy() for pb in rig.pose.bones}

before = poses()
unchanged = digest()
vertices, edges = hn._geometry('HEAD', record['fit'])
widget.clear_geometry()
widget.from_pydata([local @ Vector(p) for p in vertices],edges,[])
widget.update()
hn.validate(rig)
eyes.validate(rig)
limb_ik._validate_inventory(rig)
after = poses()
pose_error = max(abs(after[n][i][j]-m[i][j]) for n,m in before.items() for i in range(4) for j in range(4))
assert pose_error < 2e-6
assert digest() == unchanged, 'Non-head display data changed.'

# Verify the softened outline against the evaluated body, in its actual pose.
dg = bpy.context.evaluated_depsgraph_get()
body = bpy.data.objects['Cosha'].evaluated_get(dg)
mesh = body.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
world_body = [body.matrix_world @ v.co for v in mesh.vertices]
bvh = BVHTree.FromPolygons(world_body,[list(p.vertices) for p in mesh.polygons])
body.to_mesh_clear()
display = rig.matrix_world @ (head.custom_shape_transform or head).matrix
scale = head.custom_shape_scale_xyz * (head.bone.length if head.use_custom_shape_bone_size else 1)
display @= Matrix.LocRotScale(head.custom_shape_translation,head.custom_shape_rotation_euler.to_quaternion(),scale)
world_vertices = [display @ v.co for v in widget.vertices]
clearance, crossings = [], 0
for a,b in edges:
    delta = world_vertices[b]-world_vertices[a]
    hit = bvh.ray_cast(world_vertices[a],delta.normalized(),delta.length)[0]
    crossings += hit is not None
    for step in range(17):
        p = world_vertices[a].lerp(world_vertices[b],step/16)
        nearest,normal,index,distance = bvh.find_nearest(p)
        clearance.append((p-nearest).dot(normal))
assert crossings == 0 and min(clearance) > 0, (crossings,min(clearance))
assert hashlib.sha256(source.read_bytes()).hexdigest() == sha
report = {'ok':True, 'version':list(cd.bl_info['version']), 'pose_error':pose_error,
          'other_geometry_weights_displays_animation_unchanged':True,
          'body_crossings':crossings,'minimum_clearance_world':min(clearance),
          'source_sha_before':sha,'before':{'vertices':legacy,'edges':legacy_edges},
          'after':{'vertices':vertices,'edges':edges},'fit':record['fit'],'main_file_saved':apply}
if apply:
    backup = OUT / 'backups' / ('X_before_head_round_0522_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,backup)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == sha
    assert bpy.ops.wm.save_as_mainfile(filepath=str(source)) == {'FINISHED'}
    report['backup'] = str(backup)
    target = source
else:
    target = OUT / 'X_head_round_0522_preview.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(target),copy=True)
bpy.ops.wm.open_mainfile(filepath=str(target),use_scripts=False)
rig = bpy.data.objects['CoshaRig']
record = hn.validate(rig)
head = rig.pose.bones[record['head']]
widget = head.custom_shape.data
eyes.validate(rig)
poses()
assert digest() == unchanged
eyes._verify_pose(rig,before)
assert len(widget.vertices) == len(vertices) and len(widget.edges) == len(edges)
assert max((local @ Vector(p)-v.co).length for p,v in zip(vertices,widget.vertices)) < 1e-6
report['reopened_verified'] = True
(OUT / ('head_round_0522_applied.json' if apply else 'head_round_0522_validation.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEAD_ROUND_0522',json.dumps({k:v for k,v in report.items() if k not in {'before','after','fit'}}),flush=True)
