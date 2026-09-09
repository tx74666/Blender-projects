"""Head/neck integration on saved X; never saves production."""
import sys
import json
import hashlib
from array import array
from pathlib import Path
import bpy

REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
ROOT = Path(r'D:\Blender\Projects\Character\X')
sys.path.insert(0, str(REPO / 'addons'))
import character_designer as cd
from character_designer import head_neck_visuals as service, limb_ik, limb_ik_fk, torso_controls

cd.register()
rig = bpy.data.objects['CoshaRig']
bpy.context.view_layer.objects.active = rig
if bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
rig.select_set(True)
source = ROOT / 'X.blend'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
limb_ik_fk._update(bpy.context, rig)
before = {p.name: p.matrix.copy() for p in rig.pose.bones}
rest = {b.name: torso_controls._state(b) for b in rig.data.bones}
before_display = {n: limb_ik._pose_shape_json_state(rig.pose.bones[n]) for n in ('Head', 'Neck')}
before_collections = {c.name: sorted(c.bones.keys()) for c in rig.data.collections_all}

def assets():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'
                       and not o.get(limb_ik.OWNER_KEY)), key=lambda o: o.name):
        coords = array('f', [0.0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coords)
        digest.update(obj.name.encode())
        digest.update(coords.tobytes())
        digest.update(json.dumps([[list((g.group, g.weight)) for g in v.groups]
                                  for v in obj.data.vertices]).encode())
    return digest.hexdigest()

asset_hash = assets()
assert bpy.ops.character_designer.head_neck_visuals(action='BUILD') == {'FINISHED'}
record = service.validate(rig)
assert {e['role'] for e in record['bindings'].values()} == {'HEAD', 'NECK'}
assert bpy.ops.character_designer.head_neck_visuals(action='BUILD') == {'FINISHED'}
assert service.get_record(rig) == record
for action, name in (('SELECT_HEAD', 'Head'), ('SELECT_NECK', 'Neck')):
    assert bpy.ops.character_designer.head_neck_visuals(action=action) == {'FINISHED'}
    assert rig.data.bones.active.name == name
    assert rig.pose.bones[name].color.palette == 'CUSTOM'
    assert rig.pose.bones[name].custom_shape is not None
limb_ik_fk._update(bpy.context, rig)
pose_error = max(abs(rig.pose.bones[n].matrix[i][j]-m[i][j])
                 for n,m in before.items() for i in range(4) for j in range(4))
assert pose_error < 2e-6, pose_error
assert assets() == asset_hash
assert {c.name: sorted(c.bones.keys()) for c in rig.data.collections_all} == before_collections
assert all(torso_controls._same_rest(rig.data.bones[n], state) for n,state in rest.items())
limb_ik._validate_inventory(rig)
preview = ROOT / 'outputs/rig/X_head_neck_052_preview.blend'
assert bpy.ops.wm.save_as_mainfile(filepath=str(preview), copy=True) == {'FINISHED'}
assert bpy.ops.character_designer.head_neck_visuals(action='REMOVE') == {'FINISHED'}
assert service.get_record(rig) is None
assert {n: limb_ik._pose_shape_json_state(rig.pose.bones[n]) for n in ('Head', 'Neck')} == before_display
assert assets() == asset_hash
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
report = {'ok': True, 'source_unchanged': True, 'source_sha256': source_hash,
          'source': str(source), 'preview': str(preview), 'pose_error': pose_error,
          'bone_count_unchanged': len(rig.data.bones) == len(before),
          'rest_unchanged': True, 'geometry_weights_unchanged': True,
          'collections_unchanged': True, 'record': record, 'restoration_passed': True}
(ROOT / 'outputs/rig/head_neck_052_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('HEAD_NECK_X_VALIDATED', pose_error, flush=True)
