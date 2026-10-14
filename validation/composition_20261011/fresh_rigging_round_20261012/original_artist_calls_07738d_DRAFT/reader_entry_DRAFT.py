import hashlib, json, os, re, sys
from pathlib import Path
CONFIG_PATH = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_calls_07738d_DRAFT/reader_kwargs_PENDING.json')
CONFIG_SHA256 = 'PENDING_MATERIALIZED_CONFIG_SHA256'
assert re.fullmatch(r'[0-9a-f]{64}', CONFIG_SHA256), 'Draft only: bind finalized config before execution'
raw = CONFIG_PATH.read_bytes()
assert hashlib.sha256(raw).hexdigest() == CONFIG_SHA256, 'Request config drift'
kwargs = json.loads(raw)
def pending(value):
    if isinstance(value, str): return 'PENDING' in value
    if isinstance(value, dict): return any(pending(v) for v in value.values())
    if isinstance(value, list): return any(pending(v) for v in value)
    return False
assert not pending({k:v for k,v in kwargs.items() if k not in {'expected_pid','external_process_filetime'}}), 'No pending evidence or authorization fields may be executed'
assert kwargs['external_authorization_confirmed'] is True and kwargs['authorization_token'], 'Fresh root admission is required'
# One external retained-process launcher writes this identity after Start-Process.
# No identity means stop before mounting an add-on or opening any file.
import time
identity_path = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_calls_07736_03_DRAFT/reader_caller/launch_identity.json')
deadline = time.monotonic() + 30
while not identity_path.exists() and time.monotonic() < deadline:
    time.sleep(0.05)
assert identity_path.is_file(), 'Missing fresh external reader identity; no file opened'
identity = json.loads(identity_path.read_text(encoding='utf-8-sig'))
assert identity['pid'] == os.getpid() and identity['resource_token'] == kwargs['authorization_token']
assert identity['request_sha256'] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
assert isinstance(identity['process_filetime'], str) and identity['process_filetime'].isdigit()
kwargs['expected_pid'] = identity['pid']
kwargs['external_process_filetime'] = int(identity['process_filetime'])
helper_path = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/verify_original20_saved_artist_readonly_07738d.py')
helper_raw = helper_path.read_bytes()
assert hashlib.sha256(helper_raw).hexdigest() == kwargs['script_sha256'] == '577084d7e65b4292ded3d3c2a9b942a6932254dc0a8f06b00821a8d7fac29a6e', 'Helper source drift'
ns = {'__file__': str(helper_path), '__name__': 'x_original_reader36_request'}
exec(compile(helper_raw, str(helper_path), 'exec'), ns)
result = ns['run'](**kwargs)
print('ORIGINAL_ARTIST_CALL_RESULT ' + json.dumps(result, ensure_ascii=False))
assert result['completed'] is True, result
