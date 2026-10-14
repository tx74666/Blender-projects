import hashlib,json,os,sys,types
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_save_finalization_07738_01_calls/config.json')
CONFIG_SHA256 = 'f43e20d6abc3034ba21588c2857614cedeebff9ab8e681cdf4f9af9c99c01a33'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
kwargs=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
assert os.getpid()==kwargs['expected_pid']==14500
kwargs['external_process_filetime']=int(kwargs['external_process_filetime'])
helper=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/finalize_original20_saved_artist_07738.py');raw=helper.read_bytes()
assert hashlib.sha256(raw).hexdigest()==kwargs['script_sha256']=='31afd23f27feee5ab6cfda13218dab61f4692a6f6c5104857a8ba0441738143a'
name='x_original_save_finalizer_07738_01'
assert name not in sys.modules, 'Single-use read-only finalizer: inspect previous outcome instead of retrying'
module=types.ModuleType(name);module.__file__=str(helper);sys.modules[name]=module
exec(compile(raw,str(helper),'exec'),module.__dict__)
result=module.run(**kwargs)
print('ORIGINAL_SAVE_FINALIZATION_RESULT '+json.dumps(result,ensure_ascii=False))
assert result['completed'] is True, result
