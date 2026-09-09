"""Explicit live-scene entry point, used only after offline verification."""
import bpy
import importlib.util
import json
from pathlib import Path

root = Path(r'D:\Blender\Projects\Character\X')
output = root / 'outputs' / 'recovery'
assert Path(bpy.data.filepath).resolve() == (root / 'X.blend').resolve()
assert bpy.context.mode == 'OBJECT'
backup_report = json.loads((output / 'live_shoe_recovery_before.json').read_text(encoding='utf-8'))
assert Path(backup_report['backup']).is_file()
offline_report = json.loads((output / 'shoe_ring_recovery_verification.json').read_text(encoding='utf-8'))
assert offline_report['apply']['operator'] == ['FINISHED']
assert offline_report['original_file_unchanged']

spec = importlib.util.spec_from_file_location('live_shoe_ring_recovery', output / 'restore_shoe_rings.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
plan = module.plan()
assert plan['add'] == {'vertices': 1284, 'edges': 2580, 'faces': 1293}, plan
report = {'plan': plan, 'backup': backup_report['backup'], 'filepath': bpy.data.filepath}
(output / 'live_shoe_recovery_plan.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
report['apply'] = module.apply()
(output / 'live_shoe_recovery_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert report['apply']['operator'] == ['FINISHED'], report
assert not any(module.plan()['add'].values())
print('LIVE_SHOE_RINGS_RESTORED_AND_VERIFIED', report['apply'])
