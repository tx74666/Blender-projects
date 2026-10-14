import hashlib,json,sys,types,os
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_recovery_07738_01_calls/config.json')
CONFIG_SHA256 = 'cb9f03c25f892074ded92aa7a67538597936772fc9f8db7f9fd4fdfdb7bb6cca'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
assert os.getpid()==14500
helper=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/recover_original_registration_07738.py')
raw=helper.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='f236c632a8158c785344a9a79545470cf9c6367aff4efdf6224ec635c1a6ac80'
name='x_original_runtime_recovery_07738_01'
assert name not in sys.modules, 'Single-use original recovery; inspect previous outcome instead of retrying'
module=types.ModuleType(name)
module.__file__=str(helper)
sys.modules[name]=module
exec(compile(raw,str(helper),'exec'),module.__dict__)
result=module.run(config_path=str(CONFIG_PATH),config_sha256=CONFIG_SHA256,script_sha256='f236c632a8158c785344a9a79545470cf9c6367aff4efdf6224ec635c1a6ac80')
print('ORIGINAL_RECOVERY_RESULT '+json.dumps(result,ensure_ascii=False))
assert result.get('queued') is True and result.get('completed') is False, result
