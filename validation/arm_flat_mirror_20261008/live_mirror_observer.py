"""Console preparation: reload only the approved mirror; observe one UI apply."""
import hashlib, importlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
folder = Path(__file__).resolve().parent
output, ready, after_file = [folder / n for n in ('live_mirror_apply.json', 'live_mirror_observer_ready.json', 'live_mirror_after.json')]
assert not any(p.exists() for p in (output, ready, after_file)), 'Audit already exists; do not repeat'
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
assert bpy.context.area.type == 'CONSOLE' and not bpy.context.scene.tool_settings.use_keyframe_insert_auto
rig = bpy.context.object
assert rig and rig.name == 'CoshaRig' and rig.mode == 'POSE'
poses, addon = sys.modules['character_designer.control_pose_assets'], sys.modules['character_designer']
module = sys.modules['character_designer.control_pose_mirror']
manifest = json.loads((folder / 'approved_release_0773/release_projection.json').read_text(encoding='utf-8'))
assert manifest['version'] == '0.77.3'
for relative, loaded in (('control_pose_mirror.py', module), ('__init__.py', addon)):
    assert hashlib.sha256(Path(loaded.__file__).read_bytes()).hexdigest() == manifest['files'][relative]
prior = json.loads((folder / 'live_before.json').read_text(encoding='utf-8'))
assert poses.native_rest(rig) == prior['native_rest'] and len(rig.pose.bones) == 346
assert not getattr(poses.apply_channels, '_arm_flat_mirror_observer', False)

def plain(v):
    if isinstance(v, bpy.types.ID): return {'type': type(v).__name__, 'name': v.name}
    if hasattr(v, 'to_dict'): return {k: plain(x) for k, x in v.to_dict().items()}
    if isinstance(v, dict): return {k: plain(x) for k, x in v.items()}
    if hasattr(v, 'to_list'): return [plain(x) for x in v.to_list()]
    if isinstance(v, (tuple, list, set)): return [plain(x) for x in v]
    if v is None or isinstance(v, (str, int, float, bool)): return v
    try: return [plain(x) for x in v]
    except TypeError: return repr(v)
def mat(m): return [list(row) for row in m]
def props(v): return {k: plain(v[k]) for k in v.keys() if k != '_RNA_UI'}
def raw():
    return {p.name: {a: plain(getattr(p, a)) for a in ('location', 'rotation_mode', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')} | {'properties': props(p)} for p in rig.pose.bones}
def bags(a): return [bag for layer in a.layers for strip in layer.strips for bag in strip.channelbags]
def old_asset(a):
    return {'name': a.name, 'properties': props(a), 'slots': [s.identifier for s in a.slots], 'curves': [{'path': c.data_path, 'index': c.array_index, 'mute': c.mute, 'keys': [list(k.co) for k in c.keyframe_points]} for bag in bags(a) for c in bag.fcurves]}
def action_signature():
    return [old_asset(a) | {'asset': a.asset_data is not None, 'fake_user': a.use_fake_user, 'details': [(c.data_path, c.array_index, c.extrapolation, c.lock, [(list(k.co), k.interpolation, list(k.handle_left), list(k.handle_right)) for k in c.keyframe_points]) for bag in bags(a) for c in bag.fcurves]} for a in bpy.data.actions]
def mesh_hash():
    obj, h = bpy.data.objects['Cosha'], hashlib.sha256()
    for v in obj.data.vertices: h.update(repr((v.index, tuple(v.co), tuple((g.group, g.weight) for g in v.groups))).encode())
    for face in obj.data.polygons: h.update(repr(tuple(face.vertices)).encode())
    for group in obj.vertex_groups: h.update(repr((group.index, group.name)).encode())
    for key in obj.data.shape_keys.key_blocks if obj.data.shape_keys else ():
        h.update(repr((key.name, key.value, key.mute, key.vertex_group)).encode())
        for v in key.data: h.update(repr(tuple(v.co)).encode())
    return h.hexdigest()
def limb_state():
    result = {}
    for key, entry in poses.limb_ik._validate_inventory(rig)['rigs'].items():
        angles = [c.pole_angle for _p, c, record in entry['entries'] if record['role'] == 'IK']
        result['/'.join(key)] = {'mode': poses.match.mode_for_rig(rig, entry), 'value': rig.pose.bones[entry['target'].name].get('ik_fk'), 'pole_angles': angles}
    return result
def evaluated():
    bpy.context.view_layer.update()
    return {p.name: p.matrix.copy() for p in rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones}
def difference(a, b): return max(abs(x-y) for ar, br in zip(a, b) for x, y in zip(ar, br))
action = bpy.data.actions['Arm Flat']
assert old_asset(action) == next(a for a in prior['assets'] if a['name'] == 'Arm Flat')
metadata, values = poses.asset_metadata(action), poses.channels(action, rig)
assert metadata and set(values) == {'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L'}
bindings = []
for label in ('addon', 'user'):
    config = getattr(bpy.context.window_manager.keyconfigs, label)
    for km in config.keymaps if config else ():
        if km.name != 'Asset Browser Main': continue
        for item in km.keymap_items:
            if item.active and item.idname == 'character_designer.apply_control_pose' and item.type == 'LEFTMOUSE' and item.value == 'DOUBLE_CLICK' and item.shift:
                bindings.append({'config': label, 'map': km.name, 'flipped': item.properties.flipped})
    assert any(b['config'] == label and b['flipped'] for b in bindings), 'Missing mirrored double-click binding: ' + label
before = {'raw': raw(), 'assets': action_signature(), 'rest': poses.native_rest(rig), 'mesh_sha256': mesh_hash(), 'limbs': limb_state()}
checkpoint = folder / 'X_immediately_before_verified_mirror.blend'
assert not checkpoint.exists(), 'Immediate protection already exists; inspect it before retrying'
assert bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True) == {'FINISHED'}
assert Path(bpy.data.filepath).resolve() == Path(prior['artist']).resolve()
assert raw() == before['raw'] and action_signature() == before['assets']
current, expected, reflection = evaluated(), {}, Matrix.Diagonal((-1., 1., 1., 1.))
for name in sorted(values, key=lambda n: len(rig.pose.bones[n].parent_recursive)):
    fields, target = values[name], rig.data.bones[bpy.utils.flip_name(name)]
    location = Vector([fields['location'][i] for i in range(3)])
    if rig.data.bones[name].use_connect: location.zero()
    basis = Matrix.LocRotScale(location, Quaternion([fields['rotation_quaternion'][i] for i in range(4)]).normalized(), Vector([fields['scale'][i] for i in range(3)]))
    source_rest = rig.data.bones[name].matrix_local
    delta = reflection @ source_rest @ basis @ source_rest.inverted() @ reflection
    parent_pose = expected.get(target.parent.name, current[target.parent.name]) if target.parent else Matrix.Identity(4)
    parent_rest = target.parent.matrix_local if target.parent else Matrix.Identity(4)
    expected[target.name] = parent_pose @ parent_rest.inverted() @ delta @ target.matrix_local
original = poses.apply_channels
module = importlib.reload(module)
addon.bl_info['version'] = (0, 77, 3)
assert raw() == before['raw'] and action_signature() == before['assets']
environment = {'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe], 'mode': bpy.context.mode, 'selected': sorted(p.name for p in rig.pose.bones if (p if hasattr(p, 'select') else p.bone).select), 'active': rig.data.bones.active.name if rig.data.bones.active else None}
ready.write_text(json.dumps({'before': before, 'expected': {n: mat(m) for n, m in expected.items()}, 'bindings': bindings, 'environment': environment, 'original_function_id': id(original), 'mirror_sha256': manifest['files']['control_pose_mirror.py'], 'runtime_version': list(addon.bl_info['version']), 'immediate_checkpoint': str(checkpoint), 'immediate_checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest()}, ensure_ascii=False, indent=2), encoding='utf-8')

def observe(context, target, applied, *, metadata=None):
    report = {'passed': False, 'artist_saved': False, 'incoming': plain(applied), 'managed': metadata is not None}
    try:
        assert target is rig and metadata == globals()['metadata'] and set(applied) == set(expected)
        report['result'] = original(context, target, applied, metadata=metadata)
        report['original_completed'] = True
        actual, now_raw, now_limbs = evaluated(), raw(), limb_state()
        errors = {n: difference(actual[n], wanted) for n, wanted in expected.items()}
        left_error = max(difference(actual[n], current[n]) for n in current if n.endswith('.L'))
        checks = {'matrix_target': max(errors.values()) < 4e-4, 'left_unchanged': left_error < 4e-4, 'rest': poses.native_rest(rig) == before['rest'], 'assets': action_signature() == before['assets'], 'mesh': mesh_hash() == before['mesh_sha256'], 'modes_and_poles': now_limbs == before['limbs'], 'auto_key_off': not context.scene.tool_settings.use_keyframe_insert_auto}
        report.update({'checks': checks, 'right_matrix_errors': errors, 'max_left_error': left_error, 'raw_changed': [n for n in now_raw if now_raw[n] != before['raw'][n]], 'raw_after': now_raw, 'right_matrices': {n: mat(actual[n]) for n in expected}, 'right_vs_rest_degrees': {n: math.degrees(actual[n].to_quaternion().rotation_difference(rig.data.bones[n].matrix_local.to_quaternion()).angle) for n in expected}, 'limbs_after': now_limbs, 'passed': all(checks.values())})
        if not report['passed']: report['audit_error'] = 'Independent audit failed after original completed; no audit rollback claimed'
        return report['result']
    except Exception as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        report['transaction_channels_restored'] = raw() == before['raw']
        raise
    finally:
        poses.apply_channels = original
        report['hook_removed'] = poses.apply_channels is original
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
observe._arm_flat_mirror_observer = True
poses.apply_channels = observe
print('ARM_FLAT_MIRROR_READY: approved mirror only reloaded; one UI application observer armed')
