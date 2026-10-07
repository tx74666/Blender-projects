"""Protect the current artist and read actual Arm Flat mirror inputs."""
import hashlib
import json
import sys
from pathlib import Path
import bpy

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
checkpoint = folder / 'X_before_arm_flat_mirror_repair.blend'
output = folder / 'live_before.json'
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert not checkpoint.exists() and not output.exists()
assert bpy.context.area.type == 'CONSOLE'
rig = bpy.context.view_layer.objects.active
assert rig and rig.name == 'CoshaRig' and rig.type == 'ARMATURE'
poses = sys.modules['character_designer.control_pose_assets']

def plain(v):
    if isinstance(v, bpy.types.ID):
        return {'type': type(v).__name__, 'name': v.name}
    if hasattr(v, 'to_dict'):
        return {k: plain(x) for k, x in v.to_dict().items()}
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    if hasattr(v, 'to_list'):
        return [plain(x) for x in v.to_list()]
    if isinstance(v, (tuple, list, set)):
        return [plain(x) for x in v]
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    try:
        return [plain(x) for x in v]
    except TypeError:
        return repr(v)

def mat(m):
    return [list(row) for row in m]

def props(v):
    return {k: plain(v[k]) for k in v.keys() if k != '_RNA_UI'}

def raw():
    return {p.name: {a: plain(getattr(p, a)) for a in
                    ('location', 'rotation_mode', 'rotation_euler', 'rotation_quaternion',
                     'rotation_axis_angle', 'scale')} | {'properties': props(p)}
            for p in rig.pose.bones}

def rna(v):
    result = {}
    for p in v.bl_rna.properties:
        if p.identifier == 'rna_type':
            continue
        if p.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM', 'POINTER'}:
            x = getattr(v, p.identifier)
            if p.type != 'POINTER' or isinstance(x, bpy.types.ID) or x is None:
                result[p.identifier] = plain(x)
    return result

before = raw()
actions = []
for a in bpy.data.actions:
    if not a.asset_data:
        continue
    bags = [bag for layer in a.layers for strip in layer.strips for bag in strip.channelbags]
    actions.append({'name': a.name, 'properties': props(a),
                    'slots': [s.identifier for s in a.slots],
                    'curves': [{'path': c.data_path, 'index': c.array_index, 'mute': c.mute,
                                'keys': [list(k.co) for k in c.keyframe_points]}
                               for bag in bags for c in bag.fcurves]})
bpy.context.view_layer.update()
evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
report = {'artist': str(artist), 'blender': bpy.app.version_string,
          'runtime_version': list(sys.modules['character_designer'].bl_info['version']),
          'runtime_files': {n: {'path': str(Path(m.__file__)),
                               'sha256': hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()}
                            for n, m in list(sys.modules.items())
                            if n in ('character_designer.control_pose_assets',
                                     'character_designer.control_pose_mirror')},
          'frame': bpy.context.scene.frame_current, 'mode': bpy.context.mode,
          'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto,
          'selected': [p.name for p in rig.pose.bones if (p if hasattr(p, 'select') else p.bone).select],
          'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
          'raw': before, 'native_rest': poses.native_rest(rig),
          'rig_properties': props(rig), 'rig_data_properties': props(rig.data),
          'bones': {p.name: {'rest_matrix': mat(p.bone.matrix_local),
                             'basis': mat(p.matrix_basis),
                             'evaluated': mat(evaluated.pose.bones[p.name].matrix),
                             'constraints': [rna(c) for c in p.constraints]}
                    for p in rig.pose.bones},
          'assets': actions,
          'screen': [{'type': a.type, 'rectangle': [a.x, a.y, a.width, a.height]}
                     for a in bpy.context.screen.areas]}
assert raw() == before, 'Read-only capture changed artist pose'
saved = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
assert saved == {'FINISHED'} and Path(bpy.data.filepath).resolve() == artist.resolve()
assert raw() == before
report.update({'checkpoint': str(checkpoint),
               'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
               'checkpoint_native_result': sorted(saved),
               'artist_pose_unchanged': True})
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ARM_FLAT_LIVE_PROTECTED_READ_ONLY:', len(report['bones']), 'bones;', len(actions), 'assets')
