"""Read Rain foot graph and exercise transforms in this disposable process only."""
import json
import math
import re
from pathlib import Path

import bpy
from mathutils import Euler, Matrix

OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)
PATTERN = re.compile(r'foot|toe|heel|ball|ankle|leg', re.I)


def simple(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bpy.types.ID):
        return {'id_type': type(value).__name__, 'name': value.name}
    if hasattr(value, 'to_dict'):
        return {k: simple(v) for k, v in value.to_dict().items()}
    try:
        return [simple(v) for v in value]
    except TypeError:
        return str(value)


def constraint(con):
    result = {}
    for prop in con.bl_rna.properties:
        key = prop.identifier
        if key in {'rna_type', 'error_location', 'error_rotation'}:
            continue
        try:
            result[key] = simple(getattr(con, key))
        except Exception:
            pass
    if con.type == 'ARMATURE':
        result['targets'] = [{'target': simple(t.target), 'subtarget': t.subtarget, 'weight': t.weight}
                             for t in con.targets]
    return result


def rotation_error(a, b):
    angle = abs(a.to_quaternion().rotation_difference(b.to_quaternion()).angle)
    return min(angle, abs(2 * math.pi - angle))


def main():
    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    rig = next(obj for obj in armatures if 'ROLL-Foot_Control.R' in obj.pose.bones)
    selected = [pb for pb in rig.pose.bones if PATTERN.search(pb.name)]
    selected_names = {pb.name for pb in selected}
    for pb in tuple(selected):
        parent = pb.parent
        while parent:
            selected_names.add(parent.name)
            parent = parent.parent
    report = {'source_file': bpy.data.filepath, 'armature': rig.name,
              'all_armatures': [(a.name, len(a.data.bones)) for a in armatures],
              'all_bone_names': list(rig.data.bones.keys()),
              'armature_world': simple(rig.matrix_world),
              'credit': 'Rain Rig (CC) Blender Foundation | studio.blender.org',
              'license': 'CC BY 4.0',
              'bones': {}, 'drivers': [], 'probes': [], 'production_file_saved': False}
    for name in sorted(selected_names):
        pb = rig.pose.bones[name]
        report['bones'][name] = {
            'head_rest': simple(pb.bone.head_local), 'tail_rest': simple(pb.bone.tail_local),
            'rest_matrix': simple(pb.bone.matrix_local),
            'pose_matrix': simple(pb.matrix), 'basis': simple(pb.matrix_basis),
            'parent': pb.parent.name if pb.parent else None,
            'children': [child.name for child in pb.children],
            'deform': pb.bone.use_deform, 'hide': pb.bone.hide,
            'collections': [c.name for c in pb.bone.collections],
            'rotation_mode': pb.rotation_mode,
            'locks': {'location': simple(pb.lock_location), 'rotation': simple(pb.lock_rotation),
                      'scale': simple(pb.lock_scale)},
            'properties': {k: simple(pb[k]) for k in pb.keys()},
            'constraints': [constraint(c) for c in pb.constraints],
            'custom_shape': pb.custom_shape.name if pb.custom_shape else None,
            'custom_shape_transform': pb.custom_shape_transform.name if pb.custom_shape_transform else None,
            'shape_scale': simple(pb.custom_shape_scale_xyz),
            'shape_rotation': simple(pb.custom_shape_rotation_euler),
            'shape_translation': simple(pb.custom_shape_translation),
            'use_custom_shape_bone_size': pb.use_custom_shape_bone_size,
            'length': pb.length,
        }
    for owner in (rig, rig.data):
        if owner.animation_data:
            for curve in owner.animation_data.drivers:
                variables = []
                relevant = any(name in curve.data_path for name in selected_names)
                for variable in curve.driver.variables:
                    targets = []
                    for target in variable.targets:
                        row = {key: simple(getattr(target, key)) for key in
                               ('id', 'data_path', 'bone_target', 'transform_type', 'transform_space', 'rotation_mode')}
                        relevant |= target.bone_target in selected_names or any(name in target.data_path for name in selected_names)
                        targets.append(row)
                    variables.append({'name': variable.name, 'type': variable.type, 'targets': targets})
                if relevant:
                    report['drivers'].append({'owner': owner.name, 'data_path': curve.data_path,
                        'array_index': curve.array_index, 'expression': curve.driver.expression,
                        'valid': curve.is_valid, 'variables': variables,
                        'modifiers': [simple(m.type) for m in curve.modifiers]})

    # Store raw and unit-sized geometry; retain original mesh origin as pivot.
    wires = {'source_file': bpy.data.filepath, 'credit': report['credit'], 'license': report['license'], 'controls': {}}
    control_names = ['ROLL-Foot_Control.R', 'FK-Toe.R', 'IK-Foot.R', 'FK-Foot.R', 'MSTR-Foot.R']
    for name in control_names:
        pb = rig.pose.bones.get(name)
        if pb is None or pb.custom_shape is None:
            continue
        shape = pb.custom_shape
        if shape.type != 'MESH':
            continue
        vertices = [list(vertex.co) for vertex in shape.data.vertices]
        minima = [min(v[i] for v in vertices) for i in range(3)]
        maxima = [max(v[i] for v in vertices) for i in range(3)]
        scale = max(b - a for a, b in zip(minima, maxima))
        wires['controls'][name] = {'shape_object': shape.name,
            'raw_vertices': vertices, 'edges': [list(e.vertices) for e in shape.data.edges],
            'normalized_vertices': [[component / scale for component in vertex] for vertex in vertices],
            'normalization_divisor': scale, 'raw_bounds': [minima, maxima],
            'normalization': 'Divide by largest raw dimension; preserve origin/pivot and raw axes.',
            'shape_object_matrix': simple(shape.matrix_world),
            'shape_display': {key: value for key, value in report['bones'][name].items()
                              if key.startswith('shape_') or key in ('custom_shape_transform', 'use_custom_shape_bone_size', 'length')},
        }
    (OUT / 'rain_foot_wires.json').write_text(json.dumps(wires, indent=2), encoding='utf-8')

    # Probe each of the two requested control bones on all local Euler axes.
    # Native/simple drivers evaluate without enabling embedded Rain UI scripts.
    if rig.animation_data:
        report['source_action'] = rig.animation_data.action.name if rig.animation_data.action else None
        rig.animation_data.action = None
    baseline = {pb.name: (pb.rotation_mode, pb.matrix_basis.copy()) for pb in rig.pose.bones}
    def update():
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get().update()
    update()
    for control in control_names[:2]:
        pb = rig.pose.bones[control]
        probes = [(axis, 15) for axis in range(3)]
        if control == 'ROLL-Foot_Control.R':
            probes += [(0, -15), (0, 100)]
        for axis, degrees in probes:
            for name, (rotation_mode, basis) in baseline.items():
                rig.pose.bones[name].rotation_mode = rotation_mode
                rig.pose.bones[name].matrix_basis = basis
            update()
            matrices = {name: rig.pose.bones[name].matrix.copy() for name in selected_names}
            heads = {name: rig.pose.bones[name].head.copy() for name in selected_names}
            tails = {name: rig.pose.bones[name].tail.copy() for name in selected_names}
            angle = [0.0, 0.0, 0.0]
            angle[axis] = math.radians(degrees)
            pb.rotation_mode = 'XYZ'
            pb.matrix_basis = baseline[control][1] @ Euler(angle).to_matrix().to_4x4()
            update()
            changed = []
            for name in sorted(selected_names):
                other = rig.pose.bones[name]
                distance = (other.head - heads[name]).length
                tail_distance = (other.tail - tails[name]).length
                rotation = rotation_error(other.matrix, matrices[name])
                if max(distance, tail_distance, rotation) > 1e-5:
                    changed.append({'bone': name, 'head_delta': distance, 'tail_delta': tail_distance,
                                    'rotation_degrees': math.degrees(rotation),
                                    'head_after': simple(other.head), 'tail_after': simple(other.tail)})
            report['probes'].append({'control': control, 'local_axis': 'XYZ'[axis],
                'degrees': degrees, 'changed_bones': changed})
    report['driver_invalid_after_probes'] = [c.data_path for c in rig.animation_data.drivers if not c.is_valid] if rig.animation_data else []
    (OUT / 'rain_foot_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('RAIN_FOOT_AUDIT_OK', rig.name, len(report['bones']), len(report['drivers']),
          [(p['control'], p['local_axis'], len(p['changed_bones'])) for p in report['probes']])


main()
