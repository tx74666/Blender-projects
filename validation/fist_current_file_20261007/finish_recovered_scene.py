"""Append Fist to the recovered live scene and save; no temporary Main use."""
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
checkpoint = folder / 'X_before_fist_import.blend'
source = Path(r'D:\Blender\Helper\Asset-Libraries\Costom\Pose Library\Saved\Actions\Fist.asset.blend')
proof = json.loads((folder / 'asset_file_verification.json').read_text(encoding='utf-8'))
assert proof['verified']
assert Path(bpy.data.filepath).resolve() == checkpoint.resolve(), 'Must restore the newest live checkpoint'
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == proof['checkpoint_sha256']
assert hashlib.sha256(source.read_bytes()).hexdigest() == proof['fist_source_sha256']
assert hashlib.sha256(Path(proof['external_arm']).read_bytes()).hexdigest() == proof['external_arm_sha256']
assert tuple(character_designer.bl_info['version']) == (0, 77, 1)
assert not (folder / 'saved.json').exists(), 'Inspect completion receipt before repeating'
rig = bpy.context.view_layer.objects.active
assert rig and rig.name == 'CoshaRig' and rig.type == 'ARMATURE'
assert bpy.context.area.type == 'CONSOLE'
tree = ast.parse((folder / 'import_and_backup.py').read_text(encoding='utf-8'))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {'fingerprint', 'preview', 'asset_details', 'artist_state'}]
exec(compile(ast.Module(body=functions, type_ignores=[]), 'recovery_fingerprint', 'exec'))

def normalized(value):
    return json.loads(json.dumps(value))

arm = bpy.data.actions.get('Arm Flat')
assert arm and arm.asset_data
assert normalized(fingerprint(arm)) == proof['arm_data'], 'Current arm data differs from checkpoint verification'
assert preview(arm) == proof['arm_preview']
assert asset_details(arm) == proof['arm_asset']
before = artist_state()
actions_before = {a.name: fingerprint(a) for a in bpy.data.actions}
assert bpy.data.actions.get('Fist') is None, 'Fist already exists; inspect before importing'
with bpy.data.libraries.load(str(source), link=False) as (available, requested):
    requested.actions = ['Fist']
action = requested.actions[0]
assert action and action.name == 'Fist' and action.library is None and action.asset_data
assert normalized(fingerprint(action)) == proof['fist_data'], 'Fist Action data differs'
assert preview(action) == proof['fist_preview'], 'Fist preview differs'
assert asset_details(action) == proof['fist_asset'], 'Fist asset metadata differs'
action.use_fake_user = True
try:
    values = poses.channels(action, rig)
    compatibility = {'readable': True, 'names': sorted(values),
                     'control_matching_needed': poses._needs_control_matching(rig, values)}
except (ValueError, RuntimeError, KeyError, TypeError) as error:
    compatibility = {'readable': False, 'reason': str(error)}

def verify_artist():
    assert bpy.context.view_layer.objects.active == rig
    state = artist_state()
    error = max(abs(x-y) for name, rows in before['matrices'].items()
                for left, right in zip(rows, state['matrices'][name]) for x,y in zip(left,right))
    assert all(before[key] == state[key] for key in before if key != 'matrices'), 'Artist state changed'
    assert error <= 4e-6, ('Pose changed', error)
    assert all(fingerprint(bpy.data.actions[name]) == data for name, data in actions_before.items())
    assert normalized(fingerprint(action)) == proof['fist_data']
    assert preview(action) == proof['fist_preview'] and asset_details(action) == proof['fist_asset']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == proof['fist_source_sha256']
    assert hashlib.sha256(Path(proof['external_arm']).read_bytes()).hexdigest() == proof['external_arm_sha256']
    return error

error = verify_artist()
_show_current_file(bpy.context)
receipt = {'source': str(source), 'source_sha256': proof['fist_source_sha256'],
           'source_unchanged': True, 'local_asset': action.name,
           'fist_curves': len(proof['fist_data']['curves']), 'fist_slots': proof['fist_data']['slots'],
           'fist_preview': proof['fist_preview'], 'fist_compatibility': compatibility,
           'fist_asset_details': proof['fist_asset'], 'max_pose_matrix_error': error,
           'existing_actions_preserved': sorted(actions_before), 'artist_state_unchanged': True,
           'checkpoint': str(checkpoint), 'checkpoint_sha256': proof['checkpoint_sha256'],
           'external_arm': proof['external_arm'], 'external_arm_sha256': proof['external_arm_sha256'],
           'local_assets': [a.name for a in bpy.data.actions if a.asset_data],
           'mode': before['mode'], 'frame': before['frame'], 'selected': before['selected'],
           'runtime_version': list(character_designer.bl_info['version']),
           'recovered_latest_live_checkpoint': True}
(folder / 'imported.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
window, area = bpy.context.window, bpy.context.area

def finish():
    try:
        assert Path(bpy.data.filepath).resolve() == checkpoint.resolve()
        verify_artist()
        area.type = 'NODE_EDITOR'
        area.ui_type = 'ShaderNodeTree'
        with bpy.context.temp_override(window=window):
            result = bpy.ops.wm.save_as_mainfile(filepath=str(artist))
        assert result == {'FINISHED'}, 'Artist save not confirmed'
        assert Path(bpy.data.filepath).resolve() == artist.resolve()
        receipt['post_save_matrix_error'] = verify_artist()
        receipt.update(saved_file=str(artist), save_result=sorted(result),
                       artist_sha256=hashlib.sha256(artist.read_bytes()).hexdigest(),
                       artist_bytes=artist.stat().st_size, dirty_after=bpy.data.is_dirty)
        (folder / 'saved.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
        print('FIST_AND_ARM_SAVED_IN_BOTH_LOCATIONS', receipt['local_assets'])
    except Exception as error:
        (folder / 'save_error.json').write_text(json.dumps({'error': repr(error)}), encoding='utf-8')
        raise
    return None

bpy.app.timers.register(finish, first_interval=.5)
print('FIST_IMPORTED_FROM_PROTECTED_SOURCE; ARTIST_SAVE_QUEUED')
