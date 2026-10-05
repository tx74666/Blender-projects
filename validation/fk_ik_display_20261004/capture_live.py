"""Preserve the artist's current unsaved work before isolated native FK checks."""
import datetime
import hashlib
import json
import sys
from pathlib import Path
import bpy

folder = Path(__file__).resolve().parent
folder.mkdir(parents=True, exist_ok=True)
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
if Path(bpy.data.filepath).resolve() != artist.resolve():
    raise RuntimeError('The current file must be the artist X.blend.')
rig = bpy.context.view_layer.objects.active
if rig is None or rig.type != 'ARMATURE' or rig.name != 'CoshaRig':
    raise RuntimeError('Keep CoshaRig active before capturing this scene.')
if bpy.context.mode not in {'OBJECT', 'POSE'}:
    raise RuntimeError('Finish the active model edit before capturing this scene.')
forearm = sys.modules.get('character_designer.forearm_twist')
if forearm is not None and forearm._SESSION is not None:
    raise RuntimeError('Finish the Forearm preview before capturing this scene.')
target = folder / 'X_live_input.blend'
if target.exists():
    raise RuntimeError('The independent checkpoint already exists; do not overwrite it.')
facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'artist': str(artist), 'runtime': bpy.app.version_string,
         'addon_version': list(sys.modules['character_designer'].bl_info['version']),
         'scene': bpy.context.scene.name, 'view_layer': bpy.context.view_layer.name,
         'frame': bpy.context.scene.frame_current, 'mode': bpy.context.mode,
         'active': rig.name,
         'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
         'selected_bones': [bone.name for bone in rig.pose.bones if bone.select],
         'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto,
         'original_active': bool(rig.get('character_designer_body_original_mode_v1')),
         'file_dirty': bpy.data.is_dirty}
result = bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True, check_existing=False)
if result != {'FINISHED'} or Path(bpy.data.filepath).resolve() != artist.resolve():
    raise RuntimeError('Native independent save did not finish as a copy.')
facts.update({'save': sorted(result), 'checkpoint': str(target),
              'bytes': target.stat().st_size,
              'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
(folder / 'capture_live.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
print('NATIVE_FK_CHECKPOINT_SAVED', facts['bytes'], facts['sha256'], flush=True)
