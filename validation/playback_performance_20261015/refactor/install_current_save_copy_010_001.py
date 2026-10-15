"""One-shot pinned current SaveCopy installer; no deferred task or UI repair."""
from pathlib import Path
import hashlib, importlib.util, json, os, sys
assert os.getpid()==24416
root=Path(r'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor')
p=root/'current_model_save_copy_010.py'
expected='0de04db4929e725446ee9ec0e9414b26894274776edda6ad28852d9b1b29c9d4'
assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
old_path=list(sys.path)
before_modules=dict(sys.modules)
owned={}
try:
    spec=importlib.util.spec_from_file_location('_x_current_save_copy010_001',p)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owned={name:value for name,value in sys.modules.items() if name not in before_modules and name.startswith(('native_validation_support','native_source_reference_witness'))}
    receipt=module.run({'expected_pid':24416,'artist':r'D:/Blender/Projects/Character/X/X.blend','artist_sha256':'468bb6b297c56dd4b9c5f2dcd171ac240e31b9e87c4d6af998a1f64e76aafd29','copy':str(root/'blendcache_current_snapshot_001/current.blend'),'report':str(root/'current_model_save_copy_report_010.json')})
    print(json.dumps({'completed':receipt['completed'],'copy':receipt.get('copy'),'loaded_metadata':receipt.get('loaded_metadata')},ensure_ascii=False))
finally:
    for name,value in owned.items():
        if sys.modules.get(name) is value:
            del sys.modules[name]
    sys.path[:]=old_path
