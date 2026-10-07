"""Protect the artist file and collect read-only mirror/finger diagnostic data."""
import hashlib
import json
import sys
from pathlib import Path
import bpy

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
checkpoint = folder / 'X_before_mirror_diagnosis.blend'
report_file = folder / 'current_diagnostic.json'
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert not checkpoint.exists() and not report_file.exists()
rig = bpy.context.view_layer.objects.active
assert rig and rig.name == 'CoshaRig' and rig.type == 'ARMATURE' and rig.mode == 'POSE'
assert bpy.context.area and bpy.context.area.type == 'CONSOLE'

def plain(value):
    if hasattr(value, 'to_dict'):
        return {k: plain(v) for k, v in value.to_dict().items()}
    if hasattr(value, 'to_list'):
        return [plain(v) for v in value.to_list()]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, bpy.types.ID):
        return {'id_type': type(value).__name__, 'name': value.name}
    if value is None or isinstance(value, (str, float, int, bool)):
        return value
    return repr(value)

def mat(value):
    return [list(row) for row in value]

def props(value):
    return {k: plain(value[k]) for k in value.keys() if k != '_RNA_UI'}

def rna(value):
    result = {}
    for prop in value.bl_rna.properties:
        if prop.identifier == 'rna_type':
            continue
        if prop.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}:
            item = getattr(value, prop.identifier)
            result[prop.identifier] = (list(item) if getattr(prop, 'is_array', False)
                                       else sorted(item) if isinstance(item, set) else item)
        elif prop.type == 'POINTER':
            item = getattr(value, prop.identifier)
            if isinstance(item, bpy.types.ID):
                result[prop.identifier] = plain(item)
    return result

def raw():
    return {pb.name: {'rotation_mode': pb.rotation_mode,
                     'location': list(pb.location), 'rotation_euler': list(pb.rotation_euler),
                     'rotation_quaternion': list(pb.rotation_quaternion),
                     'rotation_axis_angle': list(pb.rotation_axis_angle), 'scale': list(pb.scale),
                     'properties': props(pb)} for pb in rig.pose.bones}

before = raw()
bpy.context.view_layer.update()
evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
animation = rig.animation_data
assigned = animation.action if animation else None
report = {'artist': str(artist), 'runtime_version': list(sys.modules['character_designer'].bl_info['version']),
          'blender_version': bpy.app.version_string, 'build': bpy.app.build_hash.decode(),
          'mode': bpy.context.mode, 'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
          'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
          'selected': sorted(pb.name for pb in rig.pose.bones if (pb if hasattr(pb, 'select') else pb.bone).select),
          'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto,
          'assigned_action': assigned.name if assigned else None,
          'assigned_slot': animation.action_slot.identifier if animation and animation.action_slot else None,
          'rig_matrix_world': mat(rig.matrix_world), 'rig_properties': props(rig),
          'rig_data_properties': props(rig.data), 'raw': before,
          'bones': {pb.name: {'parent': pb.parent.name if pb.parent else None,
                             'rest_matrix': mat(pb.bone.matrix_local),
                             'head': list(pb.bone.head_local), 'tail': list(pb.bone.tail_local),
                             'bone_rna': rna(pb.bone), 'bone_properties': props(pb.bone),
                             'basis': mat(pb.matrix_basis), 'evaluated_matrix': mat(evaluated.pose.bones[pb.name].matrix),
                             'constraints': [rna(c) for c in pb.constraints]}
                    for pb in rig.pose.bones},
          'assets': [{'name': a.name, 'marked': a.asset_data is not None} for a in bpy.data.actions],
          'meshes': []}

for obj in bpy.data.objects:
    if obj.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
        continue
    groups = {g.index: g.name for g in obj.vertex_groups}
    middle = {index for index, name in groups.items() if name.startswith('f_middle.')}
    if not middle:
        continue
    chosen = {v.index for v in obj.data.vertices if any(g.group in middle and g.weight > 1e-5 for g in v.groups)}
    if not chosen:
        continue
    mesh = obj.data
    item = {'object': obj.name, 'mesh': mesh.name, 'matrix_world': mat(obj.matrix_world),
            'vertices_total': len(mesh.vertices), 'edges_total': len(mesh.edges), 'faces_total': len(mesh.polygons),
            'modifiers': [rna(m) for m in obj.modifiers], 'middle_vertex_count': len(chosen),
            'vertices': [{'index': v.index, 'co': list(v.co),
                          'weights': {groups[g.group]: g.weight for g in v.groups if g.group in groups}}
                         for v in mesh.vertices if v.index in chosen],
            'faces': [{'index': p.index, 'vertices': list(p.vertices)} for p in mesh.polygons
                      if any(index in chosen for index in p.vertices)],
            'support_positions': {}, 'shape_keys': []}
    support = {index for p in item['faces'] for index in p['vertices']} - chosen
    item['support_positions'] = {str(index): list(mesh.vertices[index].co) for index in sorted(support)}
    if mesh.shape_keys:
        item['shape_keys'] = [{'name': key.name, 'value': key.value, 'mute': key.mute,
                              'relative_key': key.relative_key.name if key.relative_key else None,
                              'vertex_group': key.vertex_group,
                              'coordinates': {str(index): list(key.data[index].co) for index in sorted(chosen)}}
                             for key in mesh.shape_keys.key_blocks]
    report['meshes'].append(item)

assert raw() == before, 'Read-only collection changed pose channels'
saved = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
assert saved == {'FINISHED'} and Path(bpy.data.filepath).resolve() == artist.resolve()
assert raw() == before, 'Checkpoint operation changed pose channels'
report['checkpoint'] = str(checkpoint)
report['checkpoint_sha256'] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
report['checkpoint_native_result'] = sorted(saved)
report['artist_channels_unchanged'] = True
report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=list), encoding='utf-8')
print('MIRROR_DIAGNOSTIC_CAPTURED:', report_file, '; checkpoint saved; no pose or mesh edits')
