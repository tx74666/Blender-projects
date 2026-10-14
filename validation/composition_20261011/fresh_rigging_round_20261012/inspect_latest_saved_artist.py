"""Read a protected byte-copy of the latest saved X using the released .24 runtime.

No original is opened or saved. This captures current disk state, never claims
to represent the closed artist process's unsaved state.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
import bpy

ROOT = Path(__file__).resolve().parent
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
SEED = ROOT / 'original_artist_disk_20261012T150645Z/X_before_return.blend'
EXPECTED = 'cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'
LIGHT = ROOT / 'snapshot_latest_original_artist.py'
LIGHT_SHA = '6df88f6e605a2a4e96eb1d3f261ed456dbe150c3e54a0d1e68f0f5aa962ff971'
HISTORY = ROOT.parents[1] / 'direct_original_rig_return_20261011'
OUT = ROOT / 'latest_saved_artist_inspection_01'

def pin(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    value = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    if expected is not None:
        assert value['sha256'] == expected, str(path)
    return value

def load(path, name, package=False):
    spec = importlib.util.spec_from_file_location(name, path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

sys.dont_write_bytecode = True
assert bpy.app.background and not bpy.data.filepath
assert not any(n == 'character_designer' or n.startswith('character_designer.') for n in sys.modules)
assert OUT.is_dir() and not any(OUT.iterdir())
protected = pin(ARTIST, EXPECTED)
seed = pin(SEED, EXPECTED)
pin(LIGHT, LIGHT_SHA)
projection = HISTORY / 'release_projection_07724.json'
manifest = json.loads(projection.read_text(encoding='utf-8-sig'))
assert manifest['version'] == '0.77.24'
runtime_root = Path(manifest['source_root'])
for relative, expected in manifest['files'].items():
    pin(runtime_root / relative, expected)
light = load(LIGHT, 'saved_artist_light_reader')
report = {'schema': 'x.validation.latest-original-artist-snapshot/1',
    'completed': False, 'backup_verified': True, 'full_preservation_verified': False,
    'source': pin(LIGHT), 'collector_source': pin(__file__), 'backup': seed,
    'protected_artist': protected, 'runtime_version': [0, 77, 24],
    'runtime_projection': pin(projection), 'runtime_root': str(runtime_root),
    'oracle': pin(HISTORY / 'validation_preservation.py'), 'pid': os.getpid(),
    'artist_opened_or_written': False, 'original_artist_saved': False,
    'scope': 'Read-only reopened byte-copy of latest user-saved disk file; no live-memory claim.'}
try:
    cd = load(runtime_root / '__init__.py', 'character_designer', package=True)
    cd.register()
    assert bpy.ops.wm.open_mainfile(filepath=str(SEED), use_scripts=False, load_ui=False) == {'FINISHED'}
    scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
    layer = scene.view_layers['ViewLayer']
    with bpy.context.temp_override(scene=scene, view_layer=layer):
        before = light.snapshot(bpy.context, rig, bpy, cd.unity_animation)
        after = light.snapshot(bpy.context, rig, bpy, cd.unity_animation)
    assert before == after
    assert all(before[name]['known'] for name in
        ('modifier_stacks', 'full_worklist', 'original_MainRig_session_and_rawRest'))
    report.update(before=before, after=after, before_signature=light.digest(before),
        after_signature=light.digest(after), metadata_preservation_verified=True)
    report['Pose'] = None
    if bpy.data.actions.get('Pose') is not None:
        integration = load(ROOT / 'integrate_original20_artist_07729.py', 'pose_content_reader')
        action = bpy.data.actions['Pose']
        content = integration.pose_content(action)
        report['Pose'] = {'users': action.users, 'fake_user': action.use_fake_user,
            'asset': action.asset_data is not None, 'content_sha256': integration.pose_digest(content),
            'curve_count': len(content['curves'])}
    report['completed'] = True
except Exception as error:
    report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
finally:
    report['original_artist_disk_unchanged'] = pin(ARTIST, EXPECTED) == protected
    report['backup_disk_unchanged'] = pin(SEED, EXPECTED) == seed
    report['completed'] = bool(report['completed'] and report['original_artist_disk_unchanged'] and report['backup_disk_unchanged'])
    (OUT / 'artist_latest_snapshot_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('LATEST_SAVED_ARTIST ' + json.dumps({k: report.get(k) for k in ('completed', 'error', 'Pose', 'pid')}), flush=True)
if not report['completed']:
    raise RuntimeError(report.get('error', 'Latest saved artist inspection failed.'))
