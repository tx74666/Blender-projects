"""Remove the read-only observer, verify the new local Pose, and save X."""
import json
from pathlib import Path

import bpy
import character_designer
from character_designer import control_pose_assets as poses

folder = Path(__file__).resolve().parent
if hasattr(poses, '_pose_validation_apply'):
    poses.apply_channels = poses._pose_validation_apply
    del poses._pose_validation_apply
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
if Path(bpy.data.filepath).resolve() != artist.resolve():
    raise RuntimeError('Unexpected artist file; refusing to save.')
asset = bpy.data.actions.get('手臂平舉')
if asset is None or asset.asset_data is None or poses.asset_metadata(asset) is None:
    raise RuntimeError('The internal arm Pose has not been verified.')
click = json.loads((folder / 'live_double_click.json').read_text(encoding='utf-8'))
if not click.get('passed') or not click.get('metadata_present'):
    raise RuntimeError('The actual synchronized application was not successful.')
before = json.loads((folder / 'live_before_create.json').read_text(encoding='utf-8'))
after = json.loads((folder / 'live_after_click.json').read_text(encoding='utf-8'))
for field in ('mode', 'frame', 'active_object', 'active_bone', 'selected', 'auto_key',
              'assigned_action', 'assigned_slot', 'action_curves', 'original', 'rest'):
    if before[field] != after[field]:
        raise RuntimeError('Protected artist state changed: ' + field)
max_error = max(abs(a-b) for name, rows in before['matrices'].items()
                for row_a, row_b in zip(rows, after['matrices'][name])
                for a, b in zip(row_a, row_b))
if max_error > 4e-4:
    raise RuntimeError('The GUI application changed the visible pose: ' + str(max_error))
window, console = bpy.context.window, bpy.context.area
if window is None or console is None or console.type != 'CONSOLE':
    raise RuntimeError('Run this final check from the temporary Blender console.')

def finish():
    try:
        # Restore the artist's Shader Editor after the Console operator returns.
        console.type = 'NODE_EDITOR'
        console.ui_type = 'ShaderNodeTree'
        with bpy.context.temp_override(window=window):
            result = bpy.ops.wm.save_as_mainfile(filepath=str(artist))
        if result != {'FINISHED'} or not artist.is_file():
            raise RuntimeError('Blender did not confirm the artist save.')
        receipt = {'file': str(artist), 'result': sorted(result),
                   'version': character_designer.bl_info['version'],
                   'asset': asset.name, 'library': 'Current File',
                   'names': poses.asset_metadata(asset)['names'],
                   'mode': bpy.context.mode, 'frame': bpy.context.scene.frame_current,
                   'max_native_matrix_error': max_error,
                   'restored_editor': console.ui_type}
        (folder / 'live_saved.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
        print('POSE_ARTIST_SAVED', receipt)
    except Exception as error:
        (folder / 'live_save_error.json').write_text(json.dumps({'error': repr(error)}), encoding='utf-8')
        raise
    return None

bpy.app.timers.register(finish, first_interval=.5)
print('POSE_FINAL_CHECK_PASSED; SAVE_QUEUED')
