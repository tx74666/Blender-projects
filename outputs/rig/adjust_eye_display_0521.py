"""Validate/apply eye outline spacing to the latest saved X, keeping a backup."""
import bpy
import hashlib
import json
import shutil
import sys
from array import array
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import eye_controls as eyes, limb_ik, limb_ik_fk, head_neck_visuals

root = Path(r'D:\Blender\Projects\Character\X')
source = root / 'X.blend'
apply = '--apply' in sys.argv
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
cd.register()
bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
rig = bpy.data.objects['CoshaRig']
assert cd.bl_info['version'] == (0, 52, 1)
assert bpy.context.object == rig and rig.mode in {'POSE', 'OBJECT'}
assert bpy.context.scene.character_designer_setup.rig == rig
record = eyes.validate(rig)
assert record and eyes.display_spacing(rig) == 0.0, 'Existing spacing needs review first.'

def asset_digest():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: o.name):
        digest.update(obj.name.encode())
        coords = array('f', [0.0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coords)
        digest.update(coords.tobytes())
        digest.update(json.dumps({'groups': [g.name for g in obj.vertex_groups],
            'weights': [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
            'faces': [list(p.vertices) for p in obj.data.polygons]}, sort_keys=True).encode())
    return digest.hexdigest()

def poses():
    limb_ik_fk._update(bpy.context, rig)
    return {pb.name: pb.matrix.copy() for pb in rig.pose.bones}

def outlines():
    # Blender draw order: bone pose * translation * rotation * shape scale.
    from mathutils import Matrix, Vector
    result = {}
    for role, name in record['bones'].items():
        pb = rig.pose.bones[name]
        shape_scale = pb.custom_shape_scale_xyz.copy()
        if pb.use_custom_shape_bone_size:
            shape_scale *= pb.bone.length
        matrix = rig.matrix_world @ pb.matrix @ Matrix.Translation(pb.custom_shape_translation)
        matrix = matrix @ pb.custom_shape_rotation_euler.to_matrix().to_4x4()
        matrix = matrix @ Matrix.Diagonal((*shape_scale, 1.0))
        result[role] = {'vertices': [list(matrix @ v.co) for v in pb.custom_shape.data.vertices],
                        'edges': [list(e.vertices) for e in pb.custom_shape.data.edges]}
    return result

before = poses()
old_outlines = outlines()
rest = {b.name: eyes._state(b) for b in rig.data.bones}
assets = asset_digest()
collections = {c.name: sorted(c.bones.keys()) for c in rig.data.collections_all}
distance = eyes.recommended_display_spacing(rig)
assert bpy.ops.character_designer.eye_controls(action='SPACING', distance=distance) == {'FINISHED'}
eyes.validate(rig)
limb_ik._validate_inventory(rig)
head_neck_visuals.validate(rig)
after = poses()
pose_error = max(abs(after[n][i][j]-m[i][j]) for n,m in before.items() for i in range(4) for j in range(4))
assert pose_error < 2e-6, pose_error
assert {b.name: eyes._state(b) for b in rig.data.bones} == rest
assert asset_digest() == assets
assert {c.name: sorted(c.bones.keys()) for c in rig.data.collections_all} == collections
new_outlines = outlines()
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha, 'Source changed while preparing.'
report = {'ok': True, 'version': list(cd.bl_info['version']), 'source': str(source),
          'source_sha_before': source_sha, 'main_file_saved': False,
          'extra_spacing_rig_units': distance, 'extra_spacing_world_units': distance * rig.scale.x,
          'pose_error': pose_error, 'native_rest_unchanged': True,
          'geometry_weights_unchanged': True, 'collections_unchanged': True,
          'before_outlines': old_outlines, 'after_outlines': new_outlines}
if apply:
    backup = root / 'outputs/rig/backups' / ('X_before_eye_spacing_0521_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, backup)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == source_sha
    assert bpy.ops.wm.save_as_mainfile(filepath=str(source)) == {'FINISHED'}
    report['backup'] = str(backup)
    report['main_file_saved'] = True
    report['saved_at'] = datetime.now().isoformat()
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    rig = bpy.data.objects['CoshaRig']
    assert abs(eyes.display_spacing(rig) - distance) < 1e-6
    assert asset_digest() == assets
    eyes._verify_pose(rig, before)
    head_neck_visuals.validate(rig)
    report['reopened_verified'] = True
filename = 'eye_display_0521_applied.json' if apply else 'eye_display_0521_validation.json'
(root / 'outputs/rig' / filename).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('EYE_DISPLAY_0521', json.dumps({k:v for k,v in report.items() if not k.endswith('_outlines')}), flush=True)
