import hashlib,json,sys,os
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_recovery_07738_02_calls/config.json')
CONFIG_SHA256 = '9cd391ccd70d46ce1866a55e8ffe367bc5eb790e0dc3f5348b975502599be0f3'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
assert os.getpid()==14500
helper=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/recover_original_registration_07738b.py')
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='3636e8b0f15bcf6e1df5a3b511adfd8684db265f58610b89a4a7666daad339bb'
module=sys.modules['x_original_runtime_recovery_07738_02']
assert Path(module.__file__)==helper
assert module.STATE['report']['inputs']['config']['sha256']==CONFIG_SHA256
result=module.verify_after_event_loop()
print('ORIGINAL_RECOVERY_VERIFY '+json.dumps(result,ensure_ascii=False))
assert result.get('completed') is True or result.get('queued') is True,result
