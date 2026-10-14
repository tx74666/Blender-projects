import hashlib,json,sys,types,os
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_recovery_07738_02_calls/config.json')
CONFIG_SHA256 = '9cd391ccd70d46ce1866a55e8ffe367bc5eb790e0dc3f5348b975502599be0f3'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
assert os.getpid()==14500
helper=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/recover_original_registration_07738b.py')
raw=helper.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='3636e8b0f15bcf6e1df5a3b511adfd8684db265f58610b89a4a7666daad339bb'
name='x_original_runtime_recovery_07738_02'
assert name not in sys.modules, 'Single-use original recovery; inspect previous outcome instead of retrying'
module=types.ModuleType(name)
module.__file__=str(helper)
sys.modules[name]=module
exec(compile(raw,str(helper),'exec'),module.__dict__)
result=module.run(config_path=str(CONFIG_PATH),config_sha256=CONFIG_SHA256,script_sha256='3636e8b0f15bcf6e1df5a3b511adfd8684db265f58610b89a4a7666daad339bb')
print('ORIGINAL_RECOVERY_RESULT '+json.dumps(result,ensure_ascii=False))
assert result.get('queued') is True and result.get('completed') is False, result
