import hashlib
import json
import sys
from array import array
from pathlib import Path
from datetime import datetime

import bpy
from mathutils import Vector

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import eye_controls as eyes, limb_ik, limb_ik_fk, foot_controls, torso_controls, bone_collections

PATH = r'D:\Blender\Projects\Character\X\X.blend'
REPORT = Path(r'D:\Blender\Projects\Character\X\outputs\rig\latest_x_eye_controls_validation.json')
source_digest = hashlib.sha256(Path(PATH).read_bytes()).hexdigest()
source_stat = Path(PATH).stat()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=PATH)
rig = bpy.data.objects['CoshaRig']
limb_ik._mode_set(bpy.context, rig, 'POSE')
source_preflight = {
    'path': PATH,
    'saved_mtime_local': datetime.fromtimestamp(source_stat.st_mtime).isoformat(),
    'size_bytes': source_stat.st_size,
    'sha256_before': source_digest,
    'existing_eye_controls': eyes.get_record(rig) is not None,
    'resolved_bones': eyes.resolve_eyes(bpy.context, rig),
    'eye_constraints': {name: [(con.name, con.type) for con in rig.pose.bones[name].constraints]
                        for name in ('eye.L', 'eye.R')},
    'eye_animation_or_drivers': eyes._animated(rig, {'eye.L', 'eye.R'}),
    'active_action': rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None,
    'driver_count': len(rig.animation_data.drivers) if rig.animation_data else 0,
    'native_eye_basis': {name: [list(row) for row in rig.pose.bones[name].matrix_basis]
                         for name in ('eye.L', 'eye.R')},
    'torso_controls': {pb.name: {'location': list(pb.location), 'rotation': list(pb.rotation_euler),
                               'scale': list(pb.scale)} for pb in rig.pose.bones
                       if pb.bone.get(torso_controls.OWNER_KEY) == torso_controls.OWNER_VALUE
                       and pb.name.startswith('CTRL_')},
}
print('LATEST_X_PREFLIGHT', json.dumps(source_preflight), flush=True)


def update():
    eyes._update(bpy.context, rig)


def pose_snapshot():
    update()
    return {pb.name: pb.matrix.copy() for pb in rig.pose.bones}


def rest_snapshot():
    return {bone.name: eyes._state(bone) for bone in rig.data.bones}


def mesh_snapshot():
    result = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        coords = array('f', [0.0]) * (len(mesh.vertices) * 3)
        mesh.vertices.foreach_get('co', coords)
        result[obj.name] = coords
        evaluated.to_mesh_clear()
    return result


def weight_snapshot():
    result = {}
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.get(eyes.OWNER_KEY) != eyes.OWNER_VALUE:
            result[obj.name] = (tuple(g.name for g in obj.vertex_groups),
                tuple((v.index, tuple((g.group, g.weight) for g in v.groups)) for v in obj.data.vertices))
    return result


def max_pose_error(expected):
    return max(abs(rig.pose.bones[name].matrix[i][j] - matrix[i][j])
               for name, matrix in expected.items() for i in range(4) for j in range(4))


def max_mesh_error(expected):
    current = mesh_snapshot()
    assert current.keys() == expected.keys()
    return {name: max((abs(a-b) for a,b in zip(data, current[name])), default=0.0)
            for name, data in expected.items()}


rest = rest_snapshot()
weights = weight_snapshot()
digest = limb_ik._armature_digest(rig)
other_rigs = {o.name: {pb.name: pb.matrix.copy() for pb in o.pose.bones}
              for o in bpy.data.objects if o.type == 'ARMATURE' and o != rig}
records_before = {key: rig.data[key] for key in (torso_controls.RECORD_KEY, foot_controls.RECORD_KEY)}
before = pose_snapshot()
geometry = mesh_snapshot()
record = eyes.build(bpy.context, rig)
build_error = max_pose_error(before)
build_mesh = max_mesh_error(geometry)
assert build_error < 4e-4, build_error
assert max(build_mesh.values()) < 4e-4, build_mesh
assert weight_snapshot() == weights
assert limb_ik._armature_digest(rig) == digest
for name, state in rest.items():
    assert eyes._same_rest(rig.data.bones[name], state)
limb_ik._validate_inventory(rig)
assert all(name in rig.data.collections_all['Animation'].bones for name in record['bones'].values())
assert all(name not in rig.data.collections_all['Animation'].bones for name in record['sources'])
assert bpy.ops.character_designer.eye_controls(action='SELECT', bone=record['master']) == {'FINISHED'}
assert rig.data.bones.active.name == record['master']

# Pose existing optional controls and each gaze control simultaneously.
torso = torso_controls.get_record(rig)
rig.pose.bones[torso['bend']].rotation_euler.x += .09
feet = foot_controls.records(rig)
rig.pose.bones[feet['L']['roll']].rotation_euler.x += .15
rig.pose.bones[feet['R']['toe_control']].rotation_euler.x -= .12
rig.pose.bones[record['master']].location += Vector((.016, 0, .009))
rig.pose.bones[record['targets']['L']].location.z += .004
rig.pose.bones['Head'].rotation_mode = 'XYZ'
rig.pose.bones['Head'].rotation_euler.z += .12
desired = pose_snapshot()
assert before['eye.L'].to_quaternion().rotation_difference(desired['eye.L'].to_quaternion()).angle > .05
limb_ik._validate_inventory(rig)
geometry = mesh_snapshot()
native_desired = {name: matrix for name, matrix in desired.items() if name not in record['bones'].values()}
result = eyes.remove(bpy.context, rig)
remove_error = max_pose_error(native_desired)
remove_mesh = max_mesh_error(geometry)
assert remove_error < 4e-4, remove_error
assert max(remove_mesh.values()) < 4e-4, remove_mesh
assert weight_snapshot() == weights
assert eyes.get_record(rig) is None
assert set(rig.data.bones.keys()) == set(rest)
assert all(name in rig.data.collections_all['Animation'].bones for name in record['sources'])
assert limb_ik._armature_digest(rig) == digest
assert records_before == {key: rig.data[key] for key in records_before}
limb_ik._validate_inventory(rig)
for name, bones in other_rigs.items():
    other = bpy.data.objects[name]
    assert max(abs(other.pose.bones[bone].matrix[i][j] - matrix[i][j])
               for bone, matrix in bones.items() for i in range(4) for j in range(4)) < 1e-6

# Rebuild in the resulting non-neutral native gaze: visible offsets preserve it.
desired = pose_snapshot()
geometry = mesh_snapshot()
record = eyes.build(bpy.context, rig)
rebuild_error = max_pose_error(desired)
assert rebuild_error < 4e-4
assert max(max_mesh_error(geometry).values()) < 4e-4
assert any(rig.pose.bones[name].location.length > 1e-3 for name in record['targets'].values())
for name in record['bones'].values():
    rig.pose.bones[name].location = (0, 0, 0)
update()
head = rig.pose.bones[record['head']]
rest_to_pose = head.matrix @ head.bone.matrix_local.inverted()
neutral = {}
for source in record['sources']:
    bone = rig.data.bones[source]
    wanted = (rest_to_pose.to_3x3() @ (bone.tail_local - bone.head_local)).normalized()
    actual = rig.pose.bones[source].matrix.to_3x3().col[1].normalized()
    neutral[source] = actual.dot(wanted)
    assert neutral[source] > .999999
eyes.remove(bpy.context, rig)
assert weight_snapshot() == weights
report = {'build_pose_max': build_error, 'build_mesh_max': build_mesh,
    'remove_pose_max': remove_error, 'remove_mesh_max': remove_mesh, 'rebuild_pose_max': rebuild_error,
    'neutral_axis_dots': neutral, 'rest_bones': len(rest), 'other_rigs': list(other_rigs),
    'limbs': 4, 'foot_controls': list(feet), 'torso': True, 'saved': False,
    'source_preflight': source_preflight,
    'sha256_after': hashlib.sha256(Path(PATH).read_bytes()).hexdigest()}
report['source_file_unchanged'] = report['sha256_after'] == source_digest
REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('X_EYE_INTEGRATION_RESULT', json.dumps(report), flush=True)
