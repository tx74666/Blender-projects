"""Protect the user's reopened scene and inspect Fist destinations without applying it."""
import ast
import hashlib
import json
from pathlib import Path
import bpy
import character_designer
from character_designer import control_pose_assets as poses

folder = Path(__file__).resolve().parent
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
rig = bpy.context.view_layer.objects.active
assert rig and rig.name == 'CoshaRig' and rig.type == 'ARMATURE'
proof = json.loads((folder / 'asset_file_verification.json').read_text(encoding='utf-8'))
names = sorted({ast.literal_eval(poses._PATH.fullmatch(curve[0])[1]) for curve in proof['fist_data']['curves']})
selected = sorted(pb.name for pb in rig.pose.bones if (pb if hasattr(pb, 'select') else pb.bone).select)
missing = [name for name in names if name not in rig.pose.bones]
report = {'runtime_version': list(character_designer.bl_info['version']), 'frame': bpy.context.scene.frame_current,
          'mode': bpy.context.mode, 'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
          'selected': selected, 'fist_names': names, 'intersection': sorted(set(selected) & set(names)),
          'missing': missing, 'baseline': poses.BASELINE in rig,
          'fingers': {name: {'rotation_mode': rig.pose.bones[name].rotation_mode,
                            'constraints': [{'name': c.name, 'type': c.type, 'mute': c.mute} for c in rig.pose.bones[name].constraints]}
                      for name in names if name in rig.pose.bones},
          'local_actions': [{'name': a.name, 'asset': bool(a.asset_data)} for a in bpy.data.actions]}
checkpoint = folder / 'X_after_user_reopen_before_pose_import.blend'
if checkpoint.exists():
    raise RuntimeError('Latest-user checkpoint already exists; inspect before repeating.')
result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
assert result == {'FINISHED'}
report.update(checkpoint=str(checkpoint), checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
              checkpoint_bytes=checkpoint.stat().st_size, backup_result=sorted(result))
(folder / 'current_fist_diagnostic.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('CURRENT_USER_SCENE_PROTECTED; FIST_DIAGNOSTIC', report['intersection'], report['selected'])
