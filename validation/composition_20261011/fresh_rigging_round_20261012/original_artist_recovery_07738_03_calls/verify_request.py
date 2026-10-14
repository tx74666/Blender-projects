import hashlib,json,sys,os
from pathlib import Path
CONFIG_PATH=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_recovery_07738_03_calls/config.json')
CONFIG_SHA256 = 'c846d9a320655ed971fd3c14826d86fae80efe0c9ddd66164b5ca172314f63e3'
assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()==CONFIG_SHA256
assert os.getpid()==14500
helper=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/continue_original_registration_07738c.py')
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6fc450dc8a145fb2cf87f37eaf2265b1e4f7a918ed410cb5b7cf32a51f1411db'
module=sys.modules['x_original_runtime_recovery_07738_03']
assert Path(module.__file__)==helper
assert module.ACTIVE.STATE['report']['inputs']['config']['sha256']==CONFIG_SHA256
result=module.verify_after_event_loop()
print('ORIGINAL_RECOVERY_VERIFY '+json.dumps(result,ensure_ascii=False))
assert result.get('completed') is True or result.get('queued') is True,result
