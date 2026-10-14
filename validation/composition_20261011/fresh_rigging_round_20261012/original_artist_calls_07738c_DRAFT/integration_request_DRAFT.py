import hashlib, json, os, re, sys
from pathlib import Path
CONFIG_PATH = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_artist_calls_07738c_DRAFT/integration_kwargs_PENDING.json')
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
# This preflight is outside integration.run and therefore outside its failure-close path.
# It reads only cheap existing ownership/job/idle state, with no current/capture/dense hash.
refresh_path = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/refresh_original_artist_runtime_07736.py')
refresh_raw = refresh_path.read_bytes()
assert hashlib.sha256(refresh_raw).hexdigest() == 'f9c28504ce0453bfe4232dc0231fc484f18db8793dfd34302f5ec3a6edf38cc7'
preflight = {'__file__': str(refresh_path), '__name__': 'x_original36_preflight_readonly'}
exec(compile(refresh_raw, str(refresh_path), 'exec'), preflight)
package = sys.modules.get('character_designer')
assert package is not None and tuple(package.bl_info['version']) == (0, 77, 38) and getattr(package, '__addon_enabled__', False), 'Require actual completed .38 registration recovery'
light = preflight['load_source'](Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/snapshot_latest_original_artist.py'), '6df88f6e605a2a4e96eb1d3f261ed456dbe150c3e54a0d1e68f0f5aa962ff971', 'original36_entry_light')
with light.original_context(bpy, 'Scene', 'CoshaRig') as (ctx, rig):
    preflight['idle'](package, ctx, bpy)
    assert 'character_designer_original_inputs_pair_v1' not in rig, 'Pre-existing pair: do not run integration or close it'
    assert 'character_designer_composition_weapon_v1' not in rig, 'Pre-existing weapon record: preserve untouched'
    assert 'character_designer_rigging_session_v1' not in rig and 'character_designer_rigging_refs_v1' not in rig, 'Pre-existing native session or refs: preserve untouched'
    owner_key = 'character_designer_composition_weapon_owner'
    assert not any(owner_key in obj for obj in bpy.data.objects), 'Pre-existing tagged weapon Object: preserve untouched'
    assert not any(owner_key in collection for collection in bpy.data.collections), 'Pre-existing tagged weapon Collection: preserve untouched'
# A failure above never enters run(), never invokes close, and has no cleanup handler.
helper_path = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/integrate_original20_saved_artist_07738c.py')
helper_raw = helper_path.read_bytes()
assert hashlib.sha256(helper_raw).hexdigest() == kwargs['script_sha256'] == 'cd6169c9ea3d77a3feda8c634e3d699f6f6dc0c741f036491d814bb60e606a09', 'Helper source drift'
ns = {'__file__': str(helper_path), '__name__': 'x_original_integration36_request'}
exec(compile(helper_raw, str(helper_path), 'exec'), ns)
result = ns['run'](**kwargs)
print('ORIGINAL_ARTIST_CALL_RESULT ' + json.dumps(result, ensure_ascii=False))
assert result['completed'] is True, result
