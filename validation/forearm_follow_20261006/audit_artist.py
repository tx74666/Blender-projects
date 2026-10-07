"""Read current artist forearm state and save an independent safety copy."""
import bpy
import json
import os
from pathlib import Path

OUT = Path(r'D:\Blender\Projects\Character\X\Validation\forearm_follow_20261006')
OUT.mkdir(parents=True, exist_ok=True)
import character_designer
from character_designer import forearm_twist as twist, limb_ik_fk

rig = bpy.data.objects.get('CoshaRig')
report = {'pid': os.getpid(), 'version': bpy.app.version_string,
          'addon_version': character_designer.bl_info['version'],
          'addon_path': character_designer.__file__, 'filepath': bpy.data.filepath,
          'dirty_before_copy': bpy.data.is_dirty, 'frame': bpy.context.scene.frame_current,
          'mode': bpy.context.object.mode if bpy.context.object else None,
          'active_bone': rig.data.bones.active.name if rig and rig.data.bones.active else None,
          'bone_count': len(rig.data.bones) if rig else None,
          'runtime_errors': dict(twist._ERRORS), 'preview_active': twist._SESSION is not None,
          'meshes': {}, 'bones': {}, 'pose_library': []}
for obj in bpy.data.objects:
    if obj.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
        continue
    keys = obj.data.shape_keys
    report['meshes'][obj.name] = {
        'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons),
        'records': twist._records(obj),
        'keys': [{'name': k.name, 'value': k.value, 'mute': k.mute} for k in keys.key_blocks] if keys else [],
        'modifiers': [{'type': m.type, 'name': m.name,
                       'preserve_volume': m.use_deform_preserve_volume if m.type == 'ARMATURE' else None}
                      for m in obj.modifiers],
        'groups': [g.name for g in obj.vertex_groups if any(s in g.name.lower() for s in ('arm', 'hand', 'wrist'))]}
for side in ('L', 'R'):
    for stem in ('upper_arm', 'forearm', 'hand', 'CTRL_hand_ik', 'MCH_hand_rotation'):
        name = f'{stem}.{side}'
        pb = rig.pose.bones.get(name)
        if pb is None:
            continue
        report['bones'][name] = {
            'parent': pb.parent.name if pb.parent else None, 'rotation_mode': pb.rotation_mode,
            'location': list(pb.location), 'rotation_euler': list(pb.rotation_euler),
            'rotation_quaternion': list(pb.rotation_quaternion), 'scale': list(pb.scale),
            'basis': [list(row) for row in pb.matrix_basis],
            'matrix': [list(row) for row in pb.matrix],
            'rest': [list(row) for row in pb.bone.matrix_local],
            'custom_shape': pb.custom_shape.name if pb.custom_shape else None,
            'color': pb.color.palette, 'bone_color': pb.bone.color.palette,
            'constraints': [{'name': c.name, 'type': c.type, 'mute': c.mute, 'influence': c.influence,
                             'subtarget': getattr(c, 'subtarget', '')} for c in pb.constraints]}
report['pose_library'] = [{'name': x.name, 'path': x.path} for x in bpy.context.preferences.filepaths.asset_libraries]
copy_path = OUT / 'artist_before_twist.blend'
assert not copy_path.exists(), 'Never replace an existing safety copy.'
result = bpy.ops.wm.save_as_mainfile(filepath=str(copy_path), copy=True)
assert result == {'FINISHED'}, result
assert bpy.data.filepath == report['filepath'], 'Artist filepath changed.'
report['safety_copy'] = str(copy_path)
report['copy_result'] = sorted(result)
(OUT / 'artist_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('FOREARM_AUDIT_AND_SAFETY_COPY_OK', os.getpid(), report['version'])
bpy.context.area.ui_type = 'ShaderNodeTree'
