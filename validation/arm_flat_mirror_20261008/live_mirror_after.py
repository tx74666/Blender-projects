"""Read-only Console audit after the actual mirrored UI application."""
import ast, hashlib, importlib, json, sys
from pathlib import Path
import bpy
folder = Path(__file__).resolve().parent
output = folder / 'live_mirror_after.json'
assert not output.exists(), 'After-audit already exists; do not repeat'
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
rig, poses = bpy.context.object, sys.modules['character_designer.control_pose_assets']
assert rig and rig.name == 'CoshaRig' and rig.mode == 'POSE' and not bpy.context.scene.tool_settings.use_keyframe_insert_auto
apply = json.loads((folder / 'live_mirror_apply.json').read_text(encoding='utf-8'))
ready = json.loads((folder / 'live_mirror_observer_ready.json').read_text(encoding='utf-8'))
assert apply['passed'] and apply['hook_removed']
assert not getattr(poses.apply_channels, '_arm_flat_mirror_observer', False), 'Observer still installed'
manifest = json.loads((folder / 'approved_release_0773/release_projection.json').read_text(encoding='utf-8'))
function_source = Path(poses.apply_channels.__code__.co_filename).resolve()
assert function_source == Path(poses.__file__).resolve(), 'Unexpected apply implementation'
assert hashlib.sha256(function_source.read_bytes()).hexdigest() == manifest['files']['control_pose_assets.py'], 'Apply source differs from verified release'
mirror_was_loaded = 'character_designer.control_pose_mirror' in sys.modules
mirror = importlib.import_module('character_designer.control_pose_mirror')
assert hashlib.sha256(Path(mirror.__file__).read_bytes()).hexdigest() == ready['mirror_sha256']
assert list(sys.modules['character_designer'].bl_info['version']) == [0, 77, 3]
assert poses.native_rest(rig) == ready['before']['rest']
# Reuse only the read-only data serializers, without rerunning preparation,
# reload, protection, or the observer installation.
tree = ast.parse((folder / 'live_mirror_observer.py').read_text(encoding='utf-8'))
helpers = {'plain', 'props', 'raw', 'bags', 'old_asset', 'action_signature', 'mesh_hash', 'limb_state'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in helpers], type_ignores=[]), 'read_only_audit_helpers', 'exec'))
assert raw() == apply['raw_after'], 'Current pose no longer matches verified mirrored application'
assert plain(action_signature()) == ready['before']['assets'], 'Action data changed after verification'
assert mesh_hash() == ready['before']['mesh_sha256'], 'Mesh data changed after verification'
assert limb_state() == apply['limbs_after'] == ready['before']['limbs'], 'Control mode or Pole changed'
assert bpy.context.mode == ready['environment']['mode']
assert [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe] == ready['environment']['frame']
assert apply['managed'] and apply['original_completed'] and all(apply['checks'].values())
assert set(apply['incoming']) == set(ready['expected']) == {'shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R'}
operators = [{'idname': op.bl_idname, 'rna': op.bl_rna.identifier, 'flipped': bool(op.properties.flipped)} for op in bpy.context.window_manager.operators if (op.bl_idname in ('CHARACTERDESIGNER_OT_apply_control_pose', 'character_designer.apply_control_pose') or op.bl_rna.identifier == 'CHARACTERDESIGNER_OT_apply_control_pose') and hasattr(op.properties, 'flipped')]
bpy.context.view_layer.update()
evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
matrix_errors = {}
for name, wanted in ready['expected'].items():
    actual = evaluated.pose.bones[name].matrix
    errors = [max(abs(a-b) for x,y in zip(actual, reference) for a,b in zip(x,y)) for reference in (wanted, apply['right_matrices'][name])]
    assert max(errors) < 4e-4, 'Evaluated mirrored pose changed: ' + name
    matrix_errors[name] = errors
result = {'passed': True, 'artist_saved': False, 'hook_removed': True, 'original_function_id': ready['original_function_id'], 'current_function_id': id(poses.apply_channels), 'function_identity_preserved': id(poses.apply_channels) == ready['original_function_id'], 'approved_apply_source': str(function_source), 'operator_history': operators, 'historical_last_flipped': operators[-1]['flipped'] if operators else None, 'operator_history_is_validation_source': False, 'mirror_verified': True, 'verification_source': 'Observed mirrored UI application, all 346 raw channels, independent target matrices and protected data', 'matrix_errors': matrix_errors, 'raw_basis': {p.name: [list(row) for row in p.matrix_basis] for p in rig.pose.bones}, 'right_matrices': {n: [list(row) for row in evaluated.pose.bones[n].matrix] for n in apply['right_matrices']}, 'runtime_version': list(sys.modules['character_designer'].bl_info['version']), 'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe], 'mode': bpy.context.mode, 'auto_key': False, 'active_object': rig.name, 'active_bone': rig.data.bones.active.name if rig.data.bones.active else None, 'selected': sorted(p.name for p in rig.pose.bones if (p if hasattr(p, 'select') else p.bone).select)}
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('ARM_FLAT_MIRROR_UI_VERIFIED: current pose matches observed mirrored apply; protected data intact; one-shot hook removed')
