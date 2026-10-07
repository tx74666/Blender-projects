"""Finish the current artist file after successful native Fist integration."""
import ast
import hashlib
import json
from array import array
from datetime import datetime
from pathlib import Path
import bpy
import character_designer
from character_designer import animation_retarget, control_pose_assets as poses
from character_designer import body_original_mode as original

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert bpy.context.area.type == 'CONSOLE'
assert not (folder / 'current_saved.json').exists(), 'Inspect the existing save receipt before repeating'
assert not hasattr(poses, '_fist_validation_native'), 'The validation observer must be removed'
assert tuple(character_designer.bl_info['version']) == (0, 77, 2)
click = json.loads((folder / 'live_fist_double_click.json').read_text(encoding='utf-8'))
assert click['passed'] and click['native_result'] == ['FINISHED']
receipt = json.loads((folder / 'current_imported.json').read_text(encoding='utf-8'))
proof = json.loads((folder / 'asset_file_verification.json').read_text(encoding='utf-8'))
rig = bpy.context.view_layer.objects.active
assert rig and rig.name == 'CoshaRig' and rig.mode == 'POSE'
tree = ast.parse((folder / 'import_and_backup.py').read_text(encoding='utf-8'))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {'fingerprint', 'preview', 'asset_details', 'artist_state'}]
exec(compile(ast.Module(body=functions, type_ignores=[]), 'save_pose_fingerprints', 'exec'))

def normalized(value):
    return json.loads(json.dumps(value))

fist, arm = bpy.data.actions['Fist'], bpy.data.actions['Arm Flat']
for action, prefix in ((fist, 'fist'), (arm, 'arm')):
    assert action.library is None and action.asset_data and action.use_fake_user
    assert normalized(fingerprint(action)) == proof[prefix + '_data']
    assert preview(action) == proof[prefix + '_preview']
metadata = poses.asset_metadata(arm)
assert metadata and poses._compatible(rig, metadata['names'], metadata)
fist_source = Path(r'D:\Blender\Helper\Asset-Libraries\Costom\Pose Library\Saved\Actions\Fist.asset.blend')
arm_source = Path(proof['external_arm'])
assert hashlib.sha256(fist_source.read_bytes()).hexdigest() == proof['fist_source_sha256']
assert hashlib.sha256(arm_source.read_bytes()).hexdigest() == proof['external_arm_sha256']
before = artist_state()
area, window = bpy.context.area, bpy.context.window
# Keep the executing Console stable until the receipt is written. Restore the
# Shader Editor through the UI afterward, then save that layout with Ctrl+S.
result = bpy.ops.wm.save_mainfile()
receipt.update(native_save_return=sorted(result))
(folder / 'native_save_return.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
assert result == {'FINISHED'}
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert bpy.context.view_layer.objects.active == rig
assert artist_state() == before, 'Save changed the artist pose, selection or animation'
assert not bpy.data.is_dirty
receipt.update(saved_file=str(artist), save_result=sorted(result),
               artist_sha256=hashlib.sha256(artist.read_bytes()).hexdigest(),
               artist_bytes=artist.stat().st_size, dirty_after=bpy.data.is_dirty,
               saved_at=datetime.now().astimezone().isoformat(),
               final_frame=before['frame'], final_mode=before['mode'],
               final_selected=before['selected'], final_active_bone=before['active_bone'],
               post_save_artist_state_preserved=True, arm_native_rest_compatible=True,
               fist_native_double_click_passed=True, observer_removed=True,
               shader_editor_restored=False, final_layout_save_pending=True, auto_sync_between_copies=False,
               final_action_assets=sorted(a.name for a in bpy.data.actions if a.asset_data))
(folder / 'current_saved.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('TWO_POSES_CURRENT_AND_EXTERNAL; ARTIST_SAVED', receipt['artist_sha256'])
