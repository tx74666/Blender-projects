import hashlib, json, os, re, sys
from pathlib import Path
CONFIG_PATH = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_calls_07736_03_DRAFT/refresh_kwargs_PENDING.json')
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
assert not pending(kwargs), 'No pending evidence or authorization fields may be executed'
assert kwargs['external_authorization_confirmed'] is True and kwargs['authorization_token'], 'Fresh root admission is required'
assert type(kwargs['expected_pid']) is int and os.getpid() == kwargs['expected_pid'], 'Wrong original process'
assert isinstance(kwargs['external_process_filetime'], str) and kwargs['external_process_filetime'].isdigit(), 'FILETIME must retain decimal precision'
kwargs['external_process_filetime'] = int(kwargs['external_process_filetime'])
bpy = sys.modules.get('bpy')
assert bpy is not None and not bpy.app.background and Path(bpy.data.filepath).resolve() == Path(r'D:/Blender/Projects/Character/X/X.blend').resolve(), 'Only the existing original artist process is admitted'
helper_path = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/refresh_original_artist_runtime_07736.py')
helper_raw = helper_path.read_bytes()
assert hashlib.sha256(helper_raw).hexdigest() == kwargs['script_sha256'] == 'f9c28504ce0453bfe4232dc0231fc484f18db8793dfd34302f5ec3a6edf38cc7', 'Helper source drift'
ns = {'__file__': str(helper_path), '__name__': 'x_original_refresh36_request'}
exec(compile(helper_raw, str(helper_path), 'exec'), ns)
result = ns['run'](**kwargs)
print('ORIGINAL_ARTIST_CALL_RESULT ' + json.dumps(result, ensure_ascii=False))
assert result['completed'] is True, result
