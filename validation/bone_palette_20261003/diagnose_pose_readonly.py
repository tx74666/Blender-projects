"""Compare saved pose channels across recovery files; never save a scene."""
import importlib.util
import json
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('palette_verifier_diagnostic', ROOT / 'verify_saved_x.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
baseline = json.loads((ROOT / 'actual_x_before_palette.json').read_text(encoding='utf-8'))
fields = ('location', 'rotation_mode', 'rotation_euler', 'rotation_quaternion',
          'rotation_axis_angle', 'scale', 'matrix_basis')

def capture():
    obj = bpy.data.objects['CoshaRig']
    return {
        'active_bone': obj.data.bones.active.name if obj.data.bones.active else None,
        'context': {'active': bpy.context.object.name if bpy.context.object else None,
                    'mode': bpy.context.mode, 'frame': bpy.context.scene.frame_current},
        'channels': {pb.name: {f: v.plain(getattr(pb, f)) for f in fields} for pb in obj.pose.bones},
        'props': v.properties(obj),
    }

old = baseline['protected']['armatures']['CoshaRig']
old_channels = {name: {f: data['channels'][f] for f in fields} for name, data in old['pose'].items()}
report = {'baseline_sha256': baseline['artist_sha256'], 'files': {}}
paths = [ROOT / 'before_live_change' / 'X_before_palette.blend',
         ROOT / 'before_live_change' / 'X_recovered_autosave.blend',
         Path('D:/Blender/Projects/Character/X/X.blend')]
for path in paths:
    before_hash = v.sha_file(path)
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    bpy.context.view_layer.update()
    current = capture()
    differences = v.compare(current['channels'], old_channels, path='pose')
    report['files'][str(path)] = dict(current, sha256=before_hash, input_unchanged=v.sha_file(path)==before_hash,
                                     differences=differences, difference_count=len(differences))
    print('POSE_DIAGNOSTIC', path.name, 'differences', len(differences), flush=True)
(ROOT / 'pose_recovery_diagnosis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
