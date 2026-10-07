"""Read-only arm loop candidates in the active artist scene."""
import bpy
import json
import importlib.util
import io
import unittest
from pathlib import Path
from character_designer.forearm_twist_topology import detect_rings, expand_rings

out = Path(r'D:\Blender\Projects\Character\X\Validation\forearm_follow_20261006')
rig = bpy.data.objects['CoshaRig']
body = bpy.data.objects['Cosha']
report = {}
for side in ('L', 'R'):
    found = detect_rings(body, rig, f'forearm.{side}', f'hand.{side}')
    expanded = []
    error = None
    if found:
        try:
            expanded = expand_rings(body, rig, f'forearm.{side}', found[0]['vertices'])
        except Exception as exc:
            error = str(exc)
    report[side] = {'detected': found, 'expanded': expanded, 'error': error}
(out / 'topology_probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('FOREARM_READ_ONLY_LOOPS', {s: (len(r['detected']), len(r['expanded']), r['error']) for s, r in report.items()})
spec = importlib.util.spec_from_file_location('twist_math_check', r'D:\MyRepository\Blender-addons-by-Randy\tests\test_forearm_twist_follow_math_blender.py')
test_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_module)
buffer = io.StringIO()
result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(test_module.FollowTwistMathTests))
(out / 'math_live52.json').write_text(json.dumps({'version': bpy.app.version_string, 'scene_data_written': False,
    'tests': result.testsRun, 'success': result.wasSuccessful(), 'output': buffer.getvalue()}, indent=2), encoding='utf-8')
print('FOREARM_PURE_MATH', result.testsRun, result.wasSuccessful())
bpy.context.area.ui_type = 'ShaderNodeTree'
