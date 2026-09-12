"""Read saved X and test Blender's real global Z translation in memory only."""
import bpy
import hashlib
import json
import traceback
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
SOURCE = ROOT / 'X.blend'
REPORT = OUT / 'breast_gz_0531_diagnosis.json'


def matrix(value):
    return [list(row) for row in value]


def update():
    rig.data.update_tag()
    rig.update_tag(refresh={'OBJECT'})
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()


def colorshape(pb):
    anchor = pb.custom_shape_transform or pb
    scale = pb.custom_shape_scale_xyz * (pb.bone.length if pb.use_custom_shape_bone_size else 1.)
    display = rig.matrix_world @ anchor.matrix @ Matrix.LocRotScale(
        pb.custom_shape_translation, pb.custom_shape_rotation_euler.to_quaternion(), scale)
    points = [display @ v.co for v in pb.custom_shape.data.vertices]
    return {'anchor': anchor.name, 'center': list(sum(points, Vector()) / len(points)),
            'minimum': [min(p[i] for p in points) for i in range(3)],
            'maximum': [max(p[i] for p in points) for i in range(3)]}


def state(pb):
    return {'location': list(pb.location), 'basis': matrix(pb.matrix_basis), 'pose': matrix(pb.matrix),
            'head_world': list(rig.matrix_world @ pb.head), 'tail_world': list(rig.matrix_world @ pb.tail),
            'shape': colorshape(pb)}


def mesh_points():
    dg = bpy.context.evaluated_depsgraph_get()
    result = {}
    for name in ('Cosha', 'Clothes'):
        obj = bpy.data.objects[name].evaluated_get(dg)
        mesh = obj.to_mesh()
        try:
            result[name] = [obj.matrix_world @ v.co for v in mesh.vertices]
        finally:
            obj.to_mesh_clear()
    return result


def mesh_delta(before):
    result = {}
    for name, points in mesh_points().items():
        assert len(points) == len(before[name])
        deltas = [p-q for p,q in zip(points, before[name])]
        affected = [v for v in deltas if v.length > 1e-6]
        result[name] = {'affected_vertices': len(affected),
            'maximum_delta': list(max(deltas, key=lambda v:v.length)),
            'average_affected_delta': list(sum(affected, Vector()) / len(affected)) if affected else [0.,0.,0.],
            'min_z': min(v.z for v in deltas), 'max_z': max(v.z for v in deltas)}
    return result


def parent_state(pb):
    result = []
    while pb:
        bone = pb.bone
        constraints = []
        for con in pb.constraints:
            entry = {'name':con.name, 'type':con.type, 'influence':con.influence, 'mute':con.mute}
            for key in ('owner_space','target_space','mix_mode','subtarget'):
                if hasattr(con,key): entry[key] = getattr(con,key)
            if hasattr(con,'target'): entry['target'] = con.target.name if con.target else None
            constraints.append(entry)
        result.append({'name':pb.name,'parent':pb.parent.name if pb.parent else None,
            'use_local_location':bone.use_local_location,'inherit_scale':bone.inherit_scale,
            'use_inherit_rotation':bone.use_inherit_rotation,'use_deform':bone.use_deform,
            'lock_location':list(pb.lock_location),'scale':list(pb.scale),
            'pose_determinant':pb.matrix.to_3x3().determinant(),
            'rest_determinant':bone.matrix_local.to_3x3().determinant(),
            'basis_determinant':pb.matrix_basis.to_3x3().determinant(),
            'rest':matrix(bone.matrix_local),'basis':matrix(pb.matrix_basis),
            'pose':matrix(pb.matrix),'constraints':constraints})
        pb = pb.parent
    return result


def main():
    global rig
    assert bpy.app.background
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    report = {'ok':False,'source':str(SOURCE),'source_sha_before':source_hash,'tests':{}}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        report['saved_orientation'] = bpy.context.scene.transform_orientation_slots[0].type
        report['saved_active_object'] = bpy.context.object.name if bpy.context.object else None
        report['saved_active_bone'] = rig.data.bones.active.name if rig.data.bones.active else None
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects: obj.select_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        update()
        report['rig'] = {'matrix_world':matrix(rig.matrix_world),'scale':list(rig.scale),
                         'determinant':rig.matrix_world.to_3x3().determinant()}
        report['parents'] = {name:parent_state(rig.pose.bones[name]) for name in ('breast.L','breast.R')}
        areas = [(window, area, region) for window in bpy.context.window_manager.windows
                 for area in window.screen.areas if area.type == 'VIEW_3D'
                 for region in area.regions if region.type == 'WINDOW']
        report['view3d_context_available'] = bool(areas)
        for name in ('breast.L','breast.R'):
            pb = rig.pose.bones[name]
            for other in rig.pose.bones: other.select = other == pb
            rig.data.bones.active = pb.bone
            pb.bone.hide = False
            original_location = pb.location.copy()
            old = state(pb)
            mesh_before = mesh_points()
            try:
                if areas:
                    window, area, region = areas[0]
                    with bpy.context.temp_override(window=window, area=area, region=region):
                        status = bpy.ops.transform.translate(value=(0,0,.01), orient_type='GLOBAL',
                            constraint_axis=(False,False,True), use_proportional_edit=False)
                else:
                    status = bpy.ops.transform.translate(value=(0,0,.01), orient_type='GLOBAL',
                            constraint_axis=(False,False,True), use_proportional_edit=False)
                update()
                new = state(pb)
                report['tests'][name] = {'operator_result':list(status), 'before':old,'after':new,
                    'head_world_delta':list(Vector(new['head_world'])-Vector(old['head_world'])),
                    'shape_center_world_delta':list(Vector(new['shape']['center'])-Vector(old['shape']['center'])),
                    'deformed_meshes':mesh_delta(mesh_before)}
            finally:
                pb.location = original_location
                update()
                assert (Vector(state(pb)['head_world'])-Vector(old['head_world'])).length < 1e-6
        report['ok'] = True
    except Exception as exc:
        report.update(error=str(exc),traceback=traceback.format_exc())
    finally:
        report['source_sha_after'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        report['source_file_unchanged'] = report['source_sha_after'] == source_hash
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
        compact = {k:v for k,v in report.items() if k not in {'parents','tests'}}
        compact['tests'] = {name:{key:value for key,value in test.items() if key not in {'before','after'}}
                            for name,test in report['tests'].items()}
        print('BREAST_GZ_DIAGNOSIS',json.dumps(compact),flush=True)
    assert report['ok'] and report['source_file_unchanged'], report.get('error')


if __name__ == '__main__': main()
