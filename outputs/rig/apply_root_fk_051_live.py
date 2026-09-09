"""Back up the current X and add tested whole-body / FK display controls."""
from datetime import datetime
from pathlib import Path
from array import array
import hashlib
import json

import bpy
from mathutils import Quaternion, Vector
import character_designer as cd
from character_designer import root_control, limb_fk_visuals, limb_ik, limb_ik_fk, torso_controls

ROOT = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (ROOT / 'X.blend').resolve()
assert cd.bl_info['version'] == (0, 51, 0), cd.bl_info['version']
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
limb_ik._validate_inventory(rig)
before = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
rest = {b.name: torso_controls._state(b) for b in rig.data.bones}
assets = asset_digest()
backup = ROOT / 'outputs/rig/backups' / ('X_before_root_fk_051_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
backup.parent.mkdir(parents=True, exist_ok=True)
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}
assert bpy.ops.character_designer.root_control(action='BUILD') == {'FINISHED'}
assert bpy.ops.character_designer.limb_fk_visuals(action='BUILD') == {'FINISHED'}
assert bpy.ops.character_designer.limb_fk_visuals(action='FIT_IK') == {'FINISHED'}
limb_ik_fk._update(bpy.context, rig)
root_control._verify_pose(rig, before)
root = root_control.get_record(rig)
for name, state in rest.items():
    expected = dict(state, parent=root['master']) if name in root['controls'] else state
    assert torso_controls._same_rest(rig.data.bones[name], expected), name
assert asset_digest() == assets
limb_ik._validate_inventory(rig)

ui = bpy.context.window_manager.character_designer
ui.ui_page, ui.rig_section = 'RIG', 'BODY'
# The root is at the feet; frame the full character so its control is visible.
screen = bpy.data.workspaces['Modeling'].screens[0]
area = max((a for a in screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
view = area.spaces.active
head = rig.matrix_world @ rig.pose.bones['Head'].head
ground = rig.matrix_world @ rig.pose.bones[root['master']].head
view.region_3d.view_rotation = Quaternion((1, 0, 0), 1.5707963267948966)
view.region_3d.view_location = (head + ground) * .5
view.region_3d.view_distance = max(2.8, (head-ground).length * 2.5)
view.region_3d.view_perspective = 'ORTHO'
view.show_region_ui = True

report = {'ok': True, 'version': list(cd.bl_info['version']), 'backup': str(backup),
    'source': bpy.data.filepath, 'main_file_saved': False, 'root': root['master'],
    'root_sources': root['sources'], 'root_inputs': root['controls'],
    'fk_rings': sorted(limb_fk_visuals.get_record(rig)['bindings']),
    'ik_size_fit': json.loads(rig.data[limb_fk_visuals.IK_SIZE_RECORD_KEY]),
    'geometry_weights_unchanged': True, 'native_rest_unchanged': True,
    'unweighted_body_vertices': [v.index for v in bpy.data.objects['Cosha'].data.vertices if not v.groups],
    'pose_error': max(abs(rig.pose.bones[n].matrix[i][j]-m[i][j])
                      for n,m in before.items() for i in range(4) for j in range(4))}
(ROOT / 'outputs/rig/root_fk_051_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('ROOT_FK_051_LIVE', json.dumps(report))
