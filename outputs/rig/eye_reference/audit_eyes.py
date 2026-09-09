"""Read eye rig topology and custom-shape geometry without saving source files."""
import json
import re
from pathlib import Path

import bpy
from mathutils import Euler, Matrix

OUT = Path(__file__).parent
EYE = re.compile(r'head|eye(?!brow|lid|ring|dot)', re.I)


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
    row = {}
    for prop in con.bl_rna.properties:
        key = prop.identifier
        if key in {'rna_type', 'error_location', 'error_rotation'}:
            continue
        try:
            row[key] = simple(getattr(con, key))
        except Exception:
            pass
    if con.type == 'ARMATURE':
        row['targets'] = [{'target':simple(t.target),'subtarget':t.subtarget,'weight':t.weight} for t in con.targets]
    return row


def curves(action):
    result = []
    if hasattr(action, 'fcurves'):
        result.extend(action.fcurves)
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                try:
                    bag = strip.channelbag(slot, ensure=False)
                    if bag:
                        result.extend(bag.fcurves)
                except Exception:
                    pass
    return result


def audit(source, prefix):
    bpy.ops.wm.open_mainfile(filepath=source, load_ui=False, use_scripts=False)
    armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    report = {'source_file': source, 'saved_source': False,
              'frame_current': bpy.context.scene.frame_current,
              'armatures': {}, 'mesh_eye_groups': [], 'actions': []}
    wires = {'source_file': source, 'controls': {}}
    if prefix == 'rain':
        wires.update(credit='Rain Rig (CC) Blender Foundation | studio.blender.org', license='CC BY 4.0')
    for rig in armatures:
        wanted = {pb.name for pb in rig.pose.bones if EYE.search(pb.name)}
        if 'Properties_Face' in rig.pose.bones:
            wanted.add('Properties_Face')
        for name in tuple(wanted):
            pb = rig.pose.bones[name]
            for con in pb.constraints:
                if hasattr(con, 'target') and con.target == rig and hasattr(con, 'subtarget') and con.subtarget:
                    wanted.add(con.subtarget)
            parent = pb.parent
            while parent:
                wanted.add(parent.name)
                parent = parent.parent
        row = {'all_bone_names': list(rig.data.bones.keys()), 'matrix_world': simple(rig.matrix_world),
               'bones': {}, 'drivers': [], 'active_action': None, 'nla_tracks': []}
        for name in sorted(wanted):
            pb = rig.pose.bones[name]
            row['bones'][name] = {
                'head_rest': simple(pb.bone.head_local), 'tail_rest': simple(pb.bone.tail_local),
                'rest_direction': simple((pb.bone.tail_local - pb.bone.head_local).normalized()),
                'rest_matrix': simple(pb.bone.matrix_local), 'pose_matrix': simple(pb.matrix),
                'head_pose': simple(pb.head), 'tail_pose': simple(pb.tail),
                'basis': simple(pb.matrix_basis), 'parent': pb.parent.name if pb.parent else None,
                'children': [c.name for c in pb.children], 'deform': pb.bone.use_deform,
                'hide': pb.bone.hide, 'collections': [c.name for c in pb.bone.collections],
                'rotation_mode': pb.rotation_mode,
                'locks': {'location': simple(pb.lock_location), 'rotation': simple(pb.lock_rotation), 'scale': simple(pb.lock_scale)},
                'properties': {k: simple(pb[k]) for k in pb.keys()},
                'constraints': [constraint(c) for c in pb.constraints],
                'custom_shape': pb.custom_shape.name if pb.custom_shape else None,
                'custom_shape_transform': pb.custom_shape_transform.name if pb.custom_shape_transform else None,
                'shape_scale': simple(pb.custom_shape_scale_xyz),
                'shape_rotation': simple(pb.custom_shape_rotation_euler),
                'shape_translation': simple(pb.custom_shape_translation),
                'use_custom_shape_bone_size': pb.use_custom_shape_bone_size, 'length': pb.length,
            }
            if name in {'TGT-Eyes','TGT-Eye.L','TGT-Eye.R'} and pb.custom_shape and pb.custom_shape.type == 'MESH':
                shape = pb.custom_shape
                vertices = [list(v.co) for v in shape.data.vertices]
                minima = [min(v[i] for v in vertices) for i in range(3)]
                maxima = [max(v[i] for v in vertices) for i in range(3)]
                scale = max(b-a for a,b in zip(minima,maxima))
                factor = pb.length if pb.use_custom_shape_bone_size else 1.0
                sm = Matrix.Translation(pb.custom_shape_translation) @ Euler(pb.custom_shape_rotation_euler).to_matrix().to_4x4() @ Matrix.Diagonal([s*factor for s in pb.custom_shape_scale_xyz]+[1.0])
                shape_rest = pb.custom_shape_transform.bone.matrix_local if pb.custom_shape_transform else pb.bone.matrix_local
                display_points = [shape_rest @ sm @ v.co for v in shape.data.vertices]
                wires['controls'][name] = {
                    'armature': rig.name, 'shape_object': shape.name, 'raw_vertices': vertices,
                    'edges': [list(e.vertices) for e in shape.data.edges],
                    'normalized_vertices': [[c/scale for c in v] for v in vertices],
                    'normalization_divisor': scale, 'raw_bounds': [minima,maxima],
                    'normalization': 'Divide largest raw dimension, preserving axes and origin.',
                    'shape_object_matrix': simple(shape.matrix_world),
                    'display_rest_vertices_armature': simple(display_points),
                    'display_rest_bounds_armature': [[min(v[i] for v in display_points) for i in range(3)],[max(v[i] for v in display_points) for i in range(3)]],
                    'shape_display': {k:v for k,v in row['bones'][name].items() if k.startswith('shape_') or k in ('custom_shape_transform','use_custom_shape_bone_size','length')},
                }
        for owner in (rig, rig.data):
            if not owner.animation_data:
                continue
            for curve in owner.animation_data.drivers:
                variables = []
                relevant = bool(EYE.search(curve.data_path))
                for variable in curve.driver.variables:
                    targets = []
                    for target in variable.targets:
                        item = {k: simple(getattr(target,k)) for k in ('id','data_path','bone_target','transform_type','transform_space','rotation_mode')}
                        relevant |= bool(EYE.search(target.data_path) or EYE.search(target.bone_target))
                        targets.append(item)
                    variables.append({'name': variable.name, 'type': variable.type, 'targets': targets})
                if relevant:
                    row['drivers'].append({'owner':owner.name,'data_path':curve.data_path,'array_index':curve.array_index,
                                           'expression':curve.driver.expression,'valid':curve.is_valid,'variables':variables})
        if rig.animation_data:
            row['active_action'] = rig.animation_data.action.name if rig.animation_data.action else None
            row['nla_tracks'] = [{'name':t.name,'mute':t.mute,'strips':[{'name':s.name,'action':s.action.name if s.action else None} for s in t.strips]} for t in rig.animation_data.nla_tracks]
        report['armatures'][rig.name] = row
    for action in bpy.data.actions:
        found = [{'data_path':c.data_path,'array_index':c.array_index,'keys':len(c.keyframe_points),'frame_range':simple(c.range())} for c in curves(action) if EYE.search(c.data_path)]
        if found:
            report['actions'].append({'name':action.name,'eye_head_curves':found})
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.vertex_groups:
            continue
        groups = {g.index:g.name for g in obj.vertex_groups if 'eye' in g.name.lower()}
        if not groups:
            continue
        found = {}
        for index,name in groups.items():
            points = [v.co.copy() for v in obj.data.vertices if any(g.group==index and g.weight>0.01 for g in v.groups)]
            if points:
                found[name] = {'vertices':len(points),'bounds_local':[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]}
        if found:
            report['mesh_eye_groups'].append({'object':obj.name,'matrix_world':simple(obj.matrix_world),
                'armature_modifiers':[m.object.name if m.object else None for m in obj.modifiers if m.type=='ARMATURE'],'groups':found})
    (OUT / f'{prefix}_eye_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (OUT / f'{prefix}_eye_wires.json').write_text(json.dumps(wires,indent=2),encoding='utf-8')
    print('EYE_AUDIT_OK',prefix,[(name,len(row['bones'])) for name,row in report['armatures'].items()],list(wires['controls']))


audit(r'D:\Blender Samples\Characters\Rain v3.3\rain_v3.2.blend','rain')
audit(r'D:\Blender\Projects\Character\X\outputs\rig\X_left_foot_reset_preview.blend','x')
