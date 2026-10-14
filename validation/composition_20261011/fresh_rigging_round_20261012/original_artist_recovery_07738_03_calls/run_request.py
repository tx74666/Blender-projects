import hashlib,json,sys,types,os
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_recovery_07738_03_calls/config.json')
CONFIG_SHA256 = 'c846d9a320655ed971fd3c14826d86fae80efe0c9ddd66164b5ca172314f63e3'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
assert os.getpid()==14500
helper=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/continue_original_registration_07738c.py')
raw=helper.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='6fc450dc8a145fb2cf87f37eaf2265b1e4f7a918ed410cb5b7cf32a51f1411db'
name='x_original_runtime_recovery_07738_03'
assert name not in sys.modules, 'Single-use original recovery; inspect previous outcome instead of retrying'
module=types.ModuleType(name)
module.__file__=str(helper)
sys.modules[name]=module
exec(compile(raw,str(helper),'exec'),module.__dict__)
result=module.run(config_path=str(CONFIG_PATH),config_sha256=CONFIG_SHA256,script_sha256='6fc450dc8a145fb2cf87f37eaf2265b1e4f7a918ed410cb5b7cf32a51f1411db')
print('ORIGINAL_RECOVERY_RESULT '+json.dumps(result,ensure_ascii=False))
assert result.get('queued') is True and result.get('completed') is False, result
