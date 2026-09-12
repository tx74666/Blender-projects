"""Exercise controller rotations only in an immutable saved-X copy; never save."""
import bpy
import hashlib
import json
import math
import traceback
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector, Euler

OUT = Path(__file__).parent


def mat(m):
    return [list(row) for row in m]


def update(rig):
    rig.update_tag(refresh={'OBJECT'})
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()


def world_display(rig, pb):
    anchor = pb.custom_shape_transform or pb
    size = pb.bone.length if pb.use_custom_shape_bone_size else 1.0
    scale = Vector(pb.custom_shape_scale_xyz) * size
    return (rig.matrix_world @ anchor.matrix @ Matrix.Translation(pb.custom_shape_translation)
            @ Euler(pb.custom_shape_rotation_euler).to_matrix().to_4x4()
            @ Matrix.Diagonal((*scale, 1.0)))


def state(rig, side):
    result = {}
    for role, name in (('control', 'CTRL_hand_IK.' + side), ('hand', 'hand.' + side),
                       ('forearm', 'forearm.' + side)):
        pb = rig.pose.bones[name]
        world = rig.matrix_world @ pb.matrix
        result[role] = {'rotation': list(world.to_quaternion()), 'matrix': mat(world),
                        'head': list(rig.matrix_world @ pb.head), 'tail': list(rig.matrix_world @ pb.tail)}
    displayed = world_display(rig, rig.pose.bones['CTRL_hand_IK.' + side])
    result['widget'] = {'rotation': list(displayed.to_quaternion()), 'matrix': mat(displayed),
                        'head': list(displayed.translation)}
    return result


def delta(before, after):
    result = {}
    for name, value in before.items():
        q = (Quaternion(after[name]['rotation']) @ Quaternion(value['rotation']).inverted()).normalized()
        if q.w < 0:
            q.negate()
        axis, angle = q.to_axis_angle()
        result[name] = {'rotation_vector_degrees': list(axis * math.degrees(angle)),
                        'head_delta': list(Vector(after[name]['head']) - Vector(value['head']))}
    c = Vector(result['control']['rotation_vector_degrees'])
    for role in ('hand', 'forearm', 'widget'):
        v = Vector(result[role]['rotation_vector_degrees'])
        result[role]['alignment_with_control'] = c.normalized().dot(v.normalized()) if c.length > 1e-6 and v.length > 1e-6 else None
        result[role]['angle_ratio_to_control'] = v.length / c.length if c.length > 1e-6 else None
    return result


def info(pb):
    fields = ('target_space', 'owner_space', 'mix_mode', 'use_offset', 'euler_order',
              'use_x', 'use_y', 'use_z', 'invert_x', 'invert_y', 'invert_z', 'subtarget')
    return {'name': pb.name, 'parent': pb.parent.name if pb.parent else None,
            'rest': mat(pb.bone.matrix_local), 'pose': mat(pb.matrix), 'basis': mat(pb.matrix_basis),
            'local_scale': list(pb.scale), 'rest_determinant': pb.bone.matrix_local.to_3x3().determinant(),
            'pose_determinant': pb.matrix.to_3x3().determinant(), 'basis_determinant': pb.matrix_basis.to_3x3().determinant(),
            'rotation_mode': pb.rotation_mode, 'rotation_euler': list(pb.rotation_euler),
            'custom_shape': pb.custom_shape.name if pb.custom_shape else None,
            'custom_shape_transform': pb.custom_shape_transform.name if pb.custom_shape_transform else None,
            'custom_shape_scale': list(pb.custom_shape_scale_xyz),
            'custom_shape_translation': list(pb.custom_shape_translation),
            'custom_shape_rotation': list(pb.custom_shape_rotation_euler),
            'use_transform_at_custom_shape': getattr(pb, 'use_transform_at_custom_shape', None),
            'use_transform_around_custom_shape': getattr(pb, 'use_transform_around_custom_shape', None),
            'use_custom_shape_bone_size': pb.use_custom_shape_bone_size,
            'use_local_location': pb.bone.use_local_location, 'inherit_scale': pb.bone.inherit_scale,
            'lock_rotation': list(pb.lock_rotation),
            'properties': {k: v for k, v in pb.items() if isinstance(v, (int, float, str, bool))},
            'constraints': [dict({'name': c.name, 'type': c.type, 'influence': c.influence,
                                  'mute': c.mute, 'target': getattr(c, 'target', None).name if getattr(c, 'target', None) else None},
                                 **{k: getattr(c, k) for k in fields if hasattr(c, k)}) for c in pb.constraints]}


def main():
    source = Path(bpy.data.filepath)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    rig = bpy.data.objects['CoshaRig']
    report = {'input': str(source), 'sha256': digest, 'ok': False, 'sides': {}, 'operations': []}
    try:
        report['world_matrix'] = mat(rig.matrix_world)
        report['world_determinant'] = rig.matrix_world.to_3x3().determinant()
        report['saved_mode'] = rig.mode
        report['saved_orientation'] = bpy.context.scene.transform_orientation_slots[0].type
        report['target_rotation_version'] = rig.data.get('character_designer_limb_ik_target_rotation_version')
        report['sides'] = {s: {n: info(rig.pose.bones[n + '.' + s]) for n in ('CTRL_hand_IK', 'hand', 'forearm')}
                           for s in ('L', 'R')}
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        for collection in rig.data.collections_all:
            collection.is_visible, collection.is_solo = True, False
        window, area, region = next((w, a, r) for w in bpy.context.window_manager.windows
            for a in w.screen.areas if a.type == 'VIEW_3D' for r in a.regions if r.type == 'WINDOW')
        view = area.spaces.active.region_3d
        report['view'] = {'screen': window.screen.name, 'rotation': list(view.view_rotation),
                          'perspective': view.view_perspective,
                          'z_world': list(view.view_rotation @ Vector((0, 0, 1)))}
        update(rig)
        basis = {pb.name: pb.matrix_basis.copy() for pb in rig.pose.bones}
        for side in ('L', 'R'):
            pb = rig.pose.bones['CTRL_hand_IK.' + side]
            for other in rig.pose.bones:
                if hasattr(other, 'select'):
                    other.select = other == pb
                else:
                    other.bone.select = other == pb
            pb.bone.hide, pb.bone.hide_select = False, False
            if hasattr(pb, 'hide'):
                pb.hide = False
            rig.data.bones.active = pb.bone
            before = state(rig, side)
            operations = [('VIEW', 'Z', v) for v in (-5, 5, 17)]
            operations += [('GLOBAL', axis, v) for axis in 'XYZ' for v in (-5, 5)]
            for orient, axis, degrees in operations:
                try:
                    with bpy.context.temp_override(window=window, area=area, region=region):
                        result = bpy.ops.transform.rotate(value=math.radians(degrees), orient_axis=axis,
                            orient_type=orient, constraint_axis=tuple(a == axis for a in 'XYZ'),
                            use_proportional_edit=False)
                    update(rig)
                    after = state(rig, side)
                    report['operations'].append({'side': side, 'orientation': orient, 'axis': axis,
                        'degrees': degrees, 'status': list(result), 'delta': delta(before, after)})
                finally:
                    for name, value in basis.items():
                        rig.pose.bones[name].matrix_basis = value
                    update(rig)
                    restored = state(rig, side)
                    error = max(abs(a - b) for role in before for ra, rb in zip(before[role]['matrix'], restored[role]['matrix'])
                                for a, b in zip(ra, rb))
                    report['max_restore_matrix_error'] = max(report.get('max_restore_matrix_error', 0), error)
        report['ok'] = True
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    report['source_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == digest
    (OUT / 'wrist_rotation_0544_diagnostic.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print('WRIST_ROTATION_DIAGNOSTIC', json.dumps({k: v for k, v in report.items() if k != 'sides'}), flush=True)
    assert report['ok'] and report['source_unchanged'], report.get('error')


if __name__ == '__main__':
    main()
