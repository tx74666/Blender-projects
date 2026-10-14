"""Run isolated native regression tests and read-only saved Shoes preflight."""
import bpy
import hashlib
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent
expected = json.loads((ROOT / 'test_projection.json').read_text(encoding='utf-8'))
STAGE = Path(expected['stage'])
sys.path.insert(0, str(STAGE / 'tests'))
sys.path.insert(0, str(STAGE / 'addons'))
assert bpy.app.background, 'This runner is only for an isolated background process'
assert not bpy.data.filepath, 'Native fixture tests must start from factory startup'
import character_designer
from character_designer import quick_bind
assert Path(character_designer.__file__).resolve() == (STAGE / 'addons/character_designer/__init__.py').resolve()
assert Path(quick_bind.__file__).resolve() == (STAGE / 'addons/character_designer/quick_bind.py').resolve()
assert hashlib.sha256(Path(quick_bind.__file__).read_bytes()).hexdigest() == expected['quick_bind_sha256']
runpy.run_path(str(STAGE / 'tests/test_quick_bind_blender.py'), run_name='__main__')
import test_quick_bind_rebind_blender as existing
import test_quick_bind_additive_blender as additive

count = 9
for case in (existing.QuickBindRebindTests, additive.QuickBindAdditiveTests):
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    if not result.wasSuccessful():
        raise SystemExit(1)
    count += result.testsRun
    existing.character_designer.unregister()

# Read the saved artist file in this isolated process; never bind or save it.
artist = Path('D:/Blender/Projects/Character/X/X.blend')
before_sha = hashlib.sha256(artist.read_bytes()).hexdigest()
existing.character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(artist), load_ui=False, use_scripts=False)
service = existing.service
rig, target, body = (bpy.data.objects[name] for name in ('CoshaRig', 'Shoes', 'Cosha'))
context = SimpleNamespace(mode='OBJECT', view_layer=bpy.context.view_layer)
names, modifier = service._validate(context, target, rig, body, 'TRANSFER', check_locks=False)
record = service._read_backup(target)
scoped = service._rebind_scope_names(target, rig, record, names, body=body, mode='TRANSFER')
service._backup_modifier(target, record)
service._check_locked_groups(target, scoped)
from character_designer import unity_export
collected = unity_export.collect_character(bpy.context, rig, rig.character_designer_unity_export)
assert target in collected['objects']
assert set(scoped) == set(record['names'])
assert hashlib.sha256(artist.read_bytes()).hexdigest() == before_sha
report = {
    'passed': True, 'native_tests_passed': count,
    'tested_baseline_manifest_sha256': expected['baseline_manifest_sha256'],
    'tested_baseline_version': expected['baseline_version'],
    'tested_quick_bind_sha256': hashlib.sha256((STAGE / 'addons/character_designer/quick_bind.py').read_bytes()).hexdigest(),
    'artist_saved_sha256': before_sha, 'artist_file_unchanged': True,
    'artist_weights_recalculated': False, 'artist_rebind_preflight_passed': True,
    'modifier_viewport': modifier.show_viewport, 'modifier_render': modifier.show_render,
    'saved_scope_bones': len(scoped), 'ignored_unweighted_added_bones': len(set(names) - set(scoped)),
    'previous_weights_topology_matches': service._topology_signature(target) == record['topology'],
    'export_objects': [obj.name for obj in collected['objects']],
}
(ROOT / 'native_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('SHOES_NATIVE_VALIDATION_OK', json.dumps(report))
