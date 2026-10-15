"""One profiled frame after warmup on the disposable copy; no scene saves."""
import cProfile
import json
from pathlib import Path
import pstats
import sys
import bpy

FOLDER = Path(__file__).resolve().parent
ROOT = Path('D:/MyRepository/Blender-addons-by-Randy')
sys.path[:0] = [str(ROOT / 'addons'), str(FOLDER)]
from profile_saved_forearm import pin
import character_designer as addon
from character_designer import forearm_twist as runtime

addon.register()
input_path = FOLDER / 'input_snapshot.blend'
before = pin(input_path)
bpy.ops.wm.open_mainfile(filepath=str(input_path))
scene = bpy.context.scene
for frame in (1, 2, 3):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
profile = cProfile.Profile()
profile.enable()
scene.frame_set(14)
bpy.context.view_layer.update()
profile.disable()
stats = pstats.Stats(profile)
rows = []
for (filename, line, name), (primitive, calls, own, cumulative, _callers) in stats.stats.items():
    rows.append({'file': filename, 'line': line, 'function': name, 'calls': calls,
                 'primitive_calls': primitive, 'self_seconds': own, 'cumulative_seconds': cumulative})
assert pin(input_path) == before
report = {'schema': 'x.forearm-call-tree/1', 'completed': True, 'input': before,
          'source': pin(runtime.__file__), 'blender': bpy.app.version_string,
          'original_mode_active': runtime.forearm_original_inventory.__name__ and
              __import__('character_designer.body_original_mode', fromlist=['active']).active(bpy.data.objects['CoshaRig']),
          'errors': dict(runtime._ERRORS), 'total_profiled_seconds': stats.total_tt,
          'top_cumulative': sorted(rows, key=lambda r: r['cumulative_seconds'], reverse=True)[:35],
          'top_self': sorted(rows, key=lambda r: r['self_seconds'], reverse=True)[:35],
          'limit': 'Instrumented background frame; profiling overhead excluded from prior warm sample timings.',
          'no_scene_save': True}
(FOLDER / 'call_tree_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('FOREARM_CALL_TREE_PASS', flush=True)
