"""Save the verified artist scene after restoring its World editor."""
import hashlib, json, sys
from pathlib import Path
import bpy
from mathutils import Matrix

folder = Path(__file__).resolve().parent
receipt = folder / 'live_saved.json'
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert not receipt.exists()
assert Path(bpy.data.filepath).resolve() == artist.resolve()
assert bpy.context.area.type == 'CONSOLE'
after = json.loads((folder / 'live_mirror_after.json').read_text(encoding='utf-8'))
apply = json.loads((folder / 'live_mirror_apply.json').read_text(encoding='utf-8'))
assert after['passed'] and apply['passed'] and apply['hook_removed'] and after['mirror_verified']
rig = bpy.context.object
assert rig.name == 'CoshaRig' and bpy.context.mode == after['mode']
assert [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe] == after['frame']
assert not bpy.context.scene.tool_settings.use_keyframe_insert_auto
window, console = bpy.context.window, bpy.context.area

def finish():
    try:
        for name, rows in after['raw_basis'].items():
            assert max(abs(a-b) for x,y in zip(rig.pose.bones[name].matrix_basis, rows)
                       for a,b in zip(x,y)) < 2e-6, 'Pose changed since UI verification'
        console.type = 'PROPERTIES'
        console.spaces.active.context = 'WORLD'
        with bpy.context.temp_override(window=window):
            result = bpy.ops.wm.save_as_mainfile(filepath=str(artist))
        assert result == {'FINISHED'} and artist.is_file()
        with artist.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        receipt.write_text(json.dumps({'passed': True, 'result': sorted(result),
            'artist': str(artist), 'sha256': digest, 'bytes': artist.stat().st_size,
            'mtime_ns': artist.stat().st_mtime_ns,
            'runtime_version': list(sys.modules['character_designer'].bl_info['version']),
            'restored_editor': 'PROPERTIES/WORLD', 'mirror_ui_verified': True,
            'verification_entry': 'Asset Browser Apply Mirrored Pose menu; Shift keymap read',
            'one_shot_save_callback_completed': True}, ensure_ascii=False, indent=2), encoding='utf-8')
        print('ARM_FLAT_ARTIST_SAVED: native save FINISHED; World editor restored')
    except Exception as exc:
        (folder / 'live_save_error.json').write_text(json.dumps({'error': repr(exc)}), encoding='utf-8')
        raise
    return None

bpy.app.timers.register(finish, first_interval=.5)
print('ARM_FLAT_FINAL_CHECK_PASSED; verified artist save queued once')
