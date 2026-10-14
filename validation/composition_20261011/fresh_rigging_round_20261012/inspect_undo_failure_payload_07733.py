"""Read only the saved session payload; no add-on load, activation or save."""
import hashlib
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import bpy

root = Path(__file__).resolve().parent
source = root / 'recovery_gun_undo_07733_01/failed_original20_recovery_gun_undo.blend'
expected = '557d3180d5c7b2989a9f3ab7379aca85a49c6efd8a1f10a0ed51748320ebe4dc'
output = root / 'undo_failure_payload_07733_01/payload_report.json'
assert bpy.app.background and not bpy.data.filepath and not output.exists()
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
assert not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules)
assert bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False, load_ui=False) == {'FINISHED'}
rig = bpy.data.objects['CoshaRig']
raw = json.loads(rig['character_designer_rigging_session_v1'])
payload = raw['payload']
report = {'completed': True, 'pid': os.getpid(), 'background': True,
    'read_only': True, 'addon_loaded': False, 'activation_or_save': False,
    'source': {'path': str(source), 'sha256': expected},
    'rig': rig.name, 'mode': rig.mode, 'payload_keys': sorted(payload),
    'session': {key: payload.get(key) for key in ('owner', 'enabled', 'tweak_enabled',
        'edit_role', 'source_read_only', 'committed', 'preview_error', 'scene_start')},
    'use_tweak_mode': rig.animation_data.use_tweak_mode,
    'action': rig.animation_data.action.name if rig.animation_data.action else None,
    'action_slot': rig.animation_data.action_slot_handle,
    'frames': {scene.name: [scene.frame_current, scene.frame_subframe] for scene in bpy.data.scenes}}
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False), flush=True)
