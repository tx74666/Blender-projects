"""Import the two protected Pose assets; observe one actual Fist double-click."""
import ast
import hashlib
import json
from array import array
from pathlib import Path
import bpy
import character_designer
from character_designer import animation_retarget, control_pose_assets as poses
from character_designer import body_original_mode as original
from character_designer.control_pose_capture import _show_current_file

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert bpy.context.area.type == 'CONSOLE'
assert not (folder / 'current_imported.json').exists(), 'Inspect existing import receipt before repeating'
assert not (folder / 'live_fist_double_click.json').exists()
diagnostic = json.loads((folder / 'current_fist_diagnostic.json').read_text(encoding='utf-8'))
assert hashlib.sha256(Path(diagnostic['checkpoint']).read_bytes()).hexdigest() == diagnostic['checkpoint_sha256']
proof = json.loads((folder / 'asset_file_verification.json').read_text(encoding='utf-8'))
assert proof['verified']
fist_source = Path(r'D:\Blender\Helper\Asset-Libraries\Costom\Pose Library\Saved\Actions\Fist.asset.blend')
arm_source = Path(proof['external_arm'])
assert hashlib.sha256(fist_source.read_bytes()).hexdigest() == proof['fist_source_sha256']
assert hashlib.sha256(arm_source.read_bytes()).hexdigest() == proof['external_arm_sha256']
rig = bpy.context.view_layer.objects.active
assert rig and rig.name == 'CoshaRig' and rig.type == 'ARMATURE' and rig.mode == 'POSE'

def normalized(value):
    return json.loads(json.dumps(value))

tree = ast.parse((folder / 'import_and_backup.py').read_text(encoding='utf-8'))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {'fingerprint', 'preview', 'asset_details', 'artist_state'}]
exec(compile(ast.Module(body=functions, type_ignores=[]), 'protected_asset_fingerprints', 'exec'))

# Refresh exactly the changed function; keep registered operator and keymaps.
# Existing registered execute() resolves its module globals, including this
# refreshed helper. A full module reload would lose keymap cleanup ownership.
manifest_path = folder / 'approved_release_0772' / 'release_projection.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
runtime_file = Path(poses.__file__).resolve()
runtime_root = runtime_file.parent
assert manifest['version'] == '0.77.2'
assert all(hashlib.sha256((runtime_root / name).read_bytes()).hexdigest() == digest
           for name, digest in manifest['files'].items())
function_tree = ast.parse(runtime_file.read_text(encoding='utf-8'))
replacement = next(node for node in function_tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == '_apply_native')
exec(compile(ast.Module(body=[replacement], type_ignores=[]), str(runtime_file), 'exec'), poses.__dict__)
character_designer.bl_info['version'] = (0, 77, 2)
assert poses._apply_native.__code__.co_filename == str(runtime_file)
assert not hasattr(poses, '_fist_validation_native')

before = artist_state()
previous_actions = {a.name: fingerprint(a) for a in bpy.data.actions}
loaded = {}
for name, source, prefix in (('Fist', fist_source, 'fist'), ('Arm Flat', arm_source, 'arm')):
    assert bpy.data.actions.get(name) is None, f'{name} already exists; inspect it before importing'
    # Use ordinary current Main loads only. No temporary Main writes or reuse.
    with bpy.data.libraries.load(str(source), link=False) as (available, requested):
        assert name in available.actions
        requested.actions = [name]
    action = requested.actions[0]
    assert action and action.name == name and action.library is None and action.asset_data
    assert normalized(fingerprint(action)) == proof[prefix + '_data']
    assert preview(action) == proof[prefix + '_preview']
    expected_asset = proof[prefix + '_asset']
    if prefix == 'arm':
        expected_asset = dict(expected_asset, catalog_id=proof['fist_asset']['catalog_id'])
    assert asset_details(action) == expected_asset
    action.use_fake_user = True
    loaded[name] = action

after = artist_state()
assert before == after, 'Import changed current artist pose or editing state'
assert all(fingerprint(bpy.data.actions[name]) == data for name, data in previous_actions.items())
assert hashlib.sha256(fist_source.read_bytes()).hexdigest() == proof['fist_source_sha256']
assert hashlib.sha256(arm_source.read_bytes()).hexdigest() == proof['external_arm_sha256']
fist_names = set(poses.channels(loaded['Fist'], rig))
assert len(fist_names) == 15 and not poses._needs_control_matching(rig, poses.channels(loaded['Fist'], rig))
receipt = {'local_assets': list(loaded), 'previous_actions_preserved': sorted(previous_actions),
           'source_fist_sha256': proof['fist_source_sha256'], 'source_arm_sha256': proof['external_arm_sha256'],
           'source_files_unchanged': True, 'pose_and_editing_state_unchanged': True,
           'preview_and_pose_data_identical': True, 'runtime_version': [0, 77, 2],
           'runtime_module': str(runtime_file), 'runtime_module_sha256': manifest['files']['control_pose_assets.py'],
           'projection_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
           'latest_user_checkpoint': diagnostic['checkpoint'], 'latest_user_checkpoint_sha256': diagnostic['checkpoint_sha256']}
(folder / 'current_imported.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

def plain(value):
    if hasattr(value, 'to_dict'):
        return {k: plain(v) for k, v in value.to_dict().items()}
    if hasattr(value, 'to_list'):
        return [plain(v) for v in value.to_list()]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value

def click_state():
    state = artist_state()
    state['original'] = plain(state['original'])
    state['native_rest'] = poses.native_rest(rig)
    state['rig_matrix'] = [list(row) for row in rig.matrix_world]
    state['constraints'] = {pb.name: [(c.name, c.type, c.mute, c.influence) for c in pb.constraints]
                            for pb in rig.pose.bones}
    state['assets'] = {a.name: fingerprint(a) for a in bpy.data.actions}
    state['bbone'] = {pb.name: {prop: (list(getattr(pb, prop)) if count > 1 else getattr(pb, prop))
                              for prop, count in poses._BBONE.items()} for pb in rig.pose.bones}
    return state

native = poses._apply_native

def observe(context, values, flipped):
    if (set(values) != fist_names or flipped or context.object != rig
            or context.asset.local_id != loaded['Fist']):
        return native(context, values, flipped)
    auto_key = context.scene.tool_settings.use_keyframe_insert_auto
    result = {'passed': False, 'asset': 'Fist', 'rig': rig.name,
              'names': sorted(values), 'runtime_version': list(character_designer.bl_info['version']),
              'auto_key_before': auto_key, 'verification_auto_key_suppressed': True}
    try:
        pre = click_state()
        result.update(selected_before=pre['selected'], active_before=pre['active_bone'])
        assert not set(pre['selected']) & fist_names, 'The real no-intersection case is required'
        assert all(rig.pose.bones[name].rotation_mode == 'QUATERNION' for name in fist_names)
        context.scene.tool_settings.use_keyframe_insert_auto = False
        returned = native(context, values, flipped)
        assert returned == {'FINISHED'}, returned
        context.scene.tool_settings.use_keyframe_insert_auto = pre['auto_key']
        post = click_state()
        assert context.view_layer.objects.active == rig
        unaffected = set(rig.pose.bones.keys()) - fist_names
        outside_error = max(abs(x-y) for name in unaffected
                            for row_before, row_after in zip(pre['matrices'][name], post['matrices'][name])
                            for x,y in zip(row_before, row_after))
        assert outside_error <= 4e-6, ('Non-finger pose changed', outside_error)
        assert all(pre[key] == post[key] for key in pre
                   if key not in {'channels', 'matrices', 'bbone'})
        assert all(pre['channels'][name] == post['channels'][name] for name in unaffected)
        assert all(pre['bbone'][name] == post['bbone'][name] for name in unaffected)
        errors = []
        for name, properties in values.items():
            for prop, components in properties.items():
                actual = getattr(rig.pose.bones[name], prop)
                for index, expected in components.items():
                    scalar = actual if prop in poses._BBONE and poses._BBONE[prop] == 1 else actual[index]
                    errors.append(abs(scalar - expected))
        max_error = max(errors, default=0.)
        assert max_error <= 5e-6, ('Fist channels did not apply', max_error)
        changed = sorted(name for name in fist_names if pre['channels'][name] != post['channels'][name])
        changed_matrices = sorted(name for name in fist_names
                                  if max(abs(x-y) for left, right in zip(pre['matrices'][name], post['matrices'][name])
                                         for x,y in zip(left, right)) > 1e-6)
        assert changed and changed_matrices, 'Fist did not change evaluated finger poses'
        result.update(passed=True, native_result=sorted(returned), max_channel_error=max_error,
                      max_unaffected_matrix_error=outside_error, changed_fingers=changed,
                      visibly_changed_fingers=changed_matrices,
                      selected_after=post['selected'], active_after=post['active_bone'],
                      frame=post['frame'], animation_preserved=True, native_rest_preserved=True,
                      ik_fk_and_control_channels_preserved=True, assets_preserved=True)
        return returned
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        context.scene.tool_settings.use_keyframe_insert_auto = auto_key
        poses._apply_native = native
        del poses._fist_validation_native
        (folder / 'live_fist_double_click.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

poses._fist_validation_native = native
poses._apply_native = observe
_show_current_file(bpy.context)
print('TWO_POSES_IMPORTED; ACTUAL_FIST_DOUBLE_CLICK_AUDIT_READY')
