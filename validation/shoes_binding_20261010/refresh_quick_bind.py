"""Refresh only the tested Quick Bind service; never calculate artist weights."""
import ast
import bpy
import hashlib
import importlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from character_designer import quick_bind, unity_export, character_setup
from character_designer import quick_bind_parenting as parenting

folder = Path('D:/Blender/Projects/Character/X/validation/shoes_binding_20261010')
artist = Path('D:/Blender/Projects/Character/X/X.blend')
assert Path(bpy.data.filepath) == artist and not bpy.app.background
assert bpy.context.scene.name == 'Scene'
rig, obj, body = (bpy.data.objects[name] for name in ('CoshaRig', 'Shoes', 'Cosha'))
assert obj.parent == rig and obj.parent_type == 'OBJECT'
settings = character_setup.settings(bpy.context)
assert settings.rig == rig and settings.body == body, 'Saved Quick Bind references differ from the tested character'
delivery_path = folder / 'delivery.json'
delivery = json.loads(delivery_path.read_text(encoding='utf-8'))
assert delivery['passed'] and delivery['version'] == '0.77.18'
manifest = json.loads(Path(delivery['manifest']).read_text(encoding='utf-8'))
source = Path(quick_bind.__file__).resolve()
allowed = (
    Path('C:/Users/Randy/AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons/character_designer/quick_bind.py').resolve(),
    Path('D:/Blender/Projects/Character/X/addons/character_designer/quick_bind.py').resolve(),
)
assert source in allowed, str(source)
assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest['files']['quick_bind.py']
helper = Path('D:/Blender/Projects/Character/X/validation/parent_restore_20261010/restore_and_check.py')
tree = ast.parse(helper.read_text(encoding='utf-8'))
defs = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)], type_ignores=[])
exec(compile(defs, str(helper), 'exec'), globals())
before, context_before, world = content(obj), context_state(), obj.matrix_world.copy()
importlib.invalidate_caches()
quick_bind = importlib.reload(quick_bind)
assert Path(quick_bind.__file__).resolve() == source
preflight_context = SimpleNamespace(mode='OBJECT', view_layer=bpy.context.view_layer)
names, modifier = quick_bind._validate(preflight_context, obj, rig, body, 'TRANSFER', check_locks=False)
record = quick_bind._read_backup(obj)
scoped = quick_bind._rebind_scope_names(obj, rig, record, names, body=body, mode='TRANSFER')
quick_bind._backup_modifier(obj, record)
quick_bind._check_locked_groups(obj, scoped)
auto_names, _ = quick_bind._validate(preflight_context, obj, rig, body, 'AUTO', check_locks=False)
auto_scope = quick_bind._rebind_scope_names(obj, rig, record, auto_names, mode='AUTO')
quick_bind._check_locked_groups(obj, auto_scope)
assert set(auto_scope) == set(scoped)
collected = unity_export.collect_character(bpy.context, rig, rig.character_designer_unity_export)
assert obj in collected['objects']
assert content(obj) == before, 'Shoes data changed during module refresh'
assert context_state() == context_before, 'Artist context or rig pose changed'
parenting._verify_world(obj, world)
report = {
    'passed': True, 'version_on_disk': delivery['version'], 'refreshed_module': str(source),
    'quick_bind_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'artist_weights_recalculated': False, 'shoes_original_data_preserved': True,
    'rig_pose_and_context_preserved': True, 'transfer_rebind_preflight_passed': True,
    'automatic_rebind_preflight_passed': True, 'saved_binding_method': settings.binding_method,
    'saved_scope_bones': len(scoped), 'ignored_unweighted_added_bones': len(set(names) - set(scoped)),
    'export_objects': [o.name for o in collected['objects']],
    'full_addon_reloaded': False,
}
report['stop_result'] = sorted(bpy.ops.blendermcp.stop_server())
report['save_result'] = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(artist), check_existing=False))
assert report['save_result'] == ['FINISHED']
report['artist_saved_sha256'] = hashlib.sha256(artist.read_bytes()).hexdigest()
for area in bpy.context.screen.areas:
    area.tag_redraw()
(folder / 'runtime_refresh.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
delivery['live_quick_bind_refreshed'] = True
delivery['runtime_refresh'] = str(folder / 'runtime_refresh.json')
delivery_path.write_text(json.dumps(delivery, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
