"""Apply verified eye targets to the open X scene, preserving its current edits."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
from array import array

import bpy
from mathutils import Quaternion, Vector
import character_designer as cd
from character_designer import eye_controls as eyes, limb_ik, limb_ik_fk

ROOT = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (ROOT / 'X.blend').resolve()
assert cd.bl_info['version'] == (0, 49, 0), cd.bl_info['version']
rig = bpy.data.objects['CoshaRig']
assert bpy.context.scene.character_designer_setup.rig == rig
assert bpy.context.object == rig and rig.mode in {'POSE', 'OBJECT'}
assert not eyes.get_record(rig), 'Eye controls already present; not applying twice.'


def assets_digest():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH' and not o.get(eyes.OWNER_KEY)), key=lambda o: o.name):
        digest.update(obj.name.encode())
        coords = array('f', [0.0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coords)
        digest.update(coords.tobytes())
        data = {'groups': [g.name for g in obj.vertex_groups],
                'weights': [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
                'faces': [list(p.vertices) for p in obj.data.polygons]}
        digest.update(json.dumps(data, sort_keys=True).encode())
    return digest.hexdigest()


limb_ik_fk._update(bpy.context, rig)
before = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
rest = {bone.name: eyes._state(bone) for bone in rig.data.bones}
assets = assets_digest()
backup = ROOT / 'outputs/rig/backups' / ('X_before_eye_controls_049_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
backup.parent.mkdir(parents=True, exist_ok=True)
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}
assert bpy.ops.character_designer.eye_controls(action='BUILD') == {'FINISHED'}
record = eyes.validate(rig)
limb_ik_fk._update(bpy.context, rig)
eyes._verify_pose(rig, before)
assert all(eyes._same_rest(rig.data.bones[name], state) for name, state in rest.items())
assert assets_digest() == assets
limb_ik._validate_inventory(rig)
state = bpy.context.window_manager.character_designer
state.ui_page, state.rig_section = 'RIG', 'BODY'
assert bpy.ops.character_designer.eye_controls(action='SELECT', bone=record['master']) == {'FINISHED'}

# Frame the face and targets in the existing main Modeling viewport.
mid = sum((rig.pose.bones[name].head for name in record['sources']), Vector()) * .5
target = rig.pose.bones[record['master']].head
center = rig.matrix_world @ ((mid + target) * .5)
screen = bpy.data.workspaces['Modeling'].screens[0]
areas = [area for area in screen.areas if area.type == 'VIEW_3D']
area = max(areas, key=lambda a: a.width*a.height)
view = area.spaces.active
view.region_3d.view_rotation = Quaternion((1, 0, 0), 1.5707963267948966)
view.region_3d.view_location = center
view.region_3d.view_distance = .52
view.region_3d.view_perspective = 'ORTHO'
view.show_region_ui = True

report = {'ok': True, 'version': list(cd.bl_info['version']), 'backup': str(backup),
          'source': bpy.data.filepath, 'main_file_saved': False,
          'controls': record['bones'], 'head': record['head'], 'sources': record['sources'],
          'pose_error': max(abs(rig.pose.bones[name].matrix[i][j]-matrix[i][j]) for name,matrix in before.items() for i in range(4) for j in range(4)),
          'native_rest_unchanged': True, 'geometry_weights_unchanged': True,
          'original_bones': len(before), 'current_bones': len(rig.data.bones)}
(ROOT / 'outputs/rig/eye_controls_049_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('EYE_CONTROLS_049_LIVE', json.dumps(report))
