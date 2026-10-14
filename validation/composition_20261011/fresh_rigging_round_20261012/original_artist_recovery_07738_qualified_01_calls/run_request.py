import hashlib,json,sys,types,os
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_recovery_07738_qualified_01_calls/config.json')
CONFIG_SHA256 = 'dc5c04c767700cb5eb0e9f3c90c461cca76bd0d36018767e8db822a2d01238c1'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
assert os.getpid()==14500
helper=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/qualify_original_registration_07738.py')
raw=helper.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='3e298d40375ee01f8ebc658cabd27482115424d47c7618dc1edc8d5cadb55e28'
name='x_original_runtime_qualification_07738_01'
assert name not in sys.modules, 'Single-use qualification; inspect actual previous outcome instead of retrying'
module=types.ModuleType(name)
module.__file__=str(helper)
sys.modules[name]=module
exec(compile(raw,str(helper),'exec'),module.__dict__)
result=module.run(**json.loads(CONFIG_PATH.read_text(encoding='utf-8')))
print('ORIGINAL_QUALIFICATION_RESULT '+json.dumps(result,ensure_ascii=False))
assert result.get('completed') is True, result
