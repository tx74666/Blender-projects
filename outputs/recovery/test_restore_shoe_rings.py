import bpy, importlib.util, json, hashlib
from pathlib import Path

ROOT = Path(r'D:\Blender\Projects\Character\X')
original = ROOT / 'X.blend'
before_hash = hashlib.sha256(original.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(original), load_ui=False)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
spec = importlib.util.spec_from_file_location('restore_shoe_rings', ROOT / 'outputs/recovery/restore_shoe_rings.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
source, target = module.objects()
original_data = target.data
baseline = module.snapshot(original_data)
source_baseline = module.snapshot(source.data)
report = {'plan': module.plan()}
assert report['plan']['add'] == {'vertices': 1284, 'edges': 2580, 'faces': 1293}
report['apply'] = module.apply()
assert report['apply']['operator'] == ['FINISHED'], report
module.assert_preserved(baseline, target.data)
assert module.snapshot(source.data) == source_baseline
assert module.snapshot(original_data) == baseline
report['second_apply'] = module.apply()
assert report['second_apply']['operator'] == ['CANCELLED']
assert not any(module.plan()['add'].values())
report['final_counts'] = [len(target.data.vertices), len(target.data.edges), len(target.data.polygons)]
preview = ROOT / 'outputs/recovery/X_Shoe_Rings_Restored_Preview.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(preview), copy=True)
assert hashlib.sha256(original.read_bytes()).hexdigest() == before_hash
report['original_file_unchanged'] = True
report['source_and_original_datablock_unchanged'] = True
report['preview'] = str(preview)
(ROOT / 'outputs/recovery/shoe_ring_recovery_verification.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print(json.dumps(report, indent=2))
print('SHOE_RING_RECOVERY_VERIFICATION_PASSED')
