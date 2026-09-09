"""Back up X and apply validated head/neck displays to its current pose."""
from datetime import datetime
from pathlib import Path
from array import array
import hashlib
import json
import bpy
import character_designer as cd
from character_designer import head_neck_visuals as service, limb_ik, limb_ik_fk, torso_controls

ROOT = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (ROOT / 'X.blend').resolve()
assert cd.bl_info['version'] == (0, 52, 0), cd.bl_info['version']
rig = bpy.data.objects['CoshaRig']
assert bpy.context.scene.character_designer_setup.rig == rig
assert bpy.context.object == rig and rig.mode in {'POSE', 'OBJECT'}
assert not bpy.context.scene.tool_settings.use_keyframe_insert_auto

def asset_digest():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'
                       and not o.get(limb_ik.OWNER_KEY)), key=lambda o: o.name):
        digest.update(obj.name.encode())
        coords = array('f', [0.0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coords)
        digest.update(coords.tobytes())
        digest.update(json.dumps({'groups': [g.name for g in obj.vertex_groups],
            'weights': [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
            'faces': [list(p.vertices) for p in obj.data.polygons]}, sort_keys=True).encode())
    return digest.hexdigest()

limb_ik_fk._update(bpy.context, rig)
before = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
rest = {b.name: torso_controls._state(b) for b in rig.data.bones}
collections = {c.name: sorted(c.bones.keys()) for c in rig.data.collections_all}
assets = asset_digest()
backup = ROOT / 'outputs/rig/backups' / ('X_before_head_neck_052_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
backup.parent.mkdir(parents=True, exist_ok=True)
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}
assert bpy.ops.character_designer.head_neck_visuals(action='BUILD') == {'FINISHED'}
record = service.validate(rig)
assert {binding['role'] for binding in record['bindings'].values()} == {'HEAD', 'NECK'}
limb_ik_fk._update(bpy.context, rig)
pose_error = max(abs(rig.pose.bones[n].matrix[i][j]-m[i][j])
                 for n,m in before.items() for i in range(4) for j in range(4))
assert pose_error < 2e-6, pose_error
assert len(rig.data.bones) == len(before)
assert all(torso_controls._same_rest(rig.data.bones[n], state) for n,state in rest.items())
assert {c.name: sorted(c.bones.keys()) for c in rig.data.collections_all} == collections
assert asset_digest() == assets
limb_ik._validate_inventory(rig)
bpy.context.window_manager.character_designer.ui_page = 'RIG'
bpy.context.window_manager.character_designer.rig_section = 'BODY'
report = {'ok': True, 'version': list(cd.bl_info['version']), 'backup': str(backup),
          'source': bpy.data.filepath, 'main_file_saved': False,
          'bindings': {name: {'role': entry['role'], 'shape': rig.pose.bones[name].custom_shape.name}
                       for name,entry in record['bindings'].items()},
          'pose_error': pose_error, 'native_rest_unchanged': True,
          'bone_count_unchanged': True, 'geometry_weights_unchanged': True,
          'collections_unchanged': True}
(ROOT / 'outputs/rig/head_neck_052_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('HEAD_NECK_052_LIVE', json.dumps(report))
