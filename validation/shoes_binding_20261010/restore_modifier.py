"""Restore the existing Shoes binding switch without recalculating weights."""
import ast
import bpy
import hashlib
import json
import shutil
import struct
from pathlib import Path
from character_designer import quick_bind, unity_export
from character_designer import quick_bind_parenting as parenting

file = Path(r'D:\Blender\Projects\Character\X\X.blend')
folder = Path(r'D:\Blender\Projects\Character\X\validation\shoes_binding_20261010')
assert Path(bpy.data.filepath) == file and bpy.context.scene.name == 'Scene'
rig = bpy.data.objects['CoshaRig']
obj = bpy.data.objects['Shoes']
assert obj.parent == rig and not quick_bind.has_removed_binding(obj)
record = quick_bind._read_backup(obj)
modifier = quick_bind._backup_modifier(obj, record)
assert modifier.object == rig and modifier.use_vertex_groups and not modifier.vertex_group
assert modifier.show_render and not modifier.show_viewport
# Reuse the already-reviewed read-only signatures, without any scene-operation code.
helper = Path(r'D:\Blender\Projects\Character\X\validation\parent_restore_20261010\restore_and_check.py')
tree = ast.parse(helper.read_text(encoding='utf-8'))
defs = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)], type_ignores=[])
exec(compile(defs, str(helper), 'exec'), globals())
before = content(obj)
expected = list(before)
for pointer, values in expected[3]:
    if pointer == modifier.as_pointer():
        values['show_viewport'] = True
context_before = context_state()
world = obj.matrix_world.copy()
config = rig.character_designer_unity_export
overrides = [(e, e.enabled) for e in config.extras if e.object == obj]
backup = folder/'X.before_shoes_modifier_last_saved.blend'
assert not backup.exists()
shutil.copy2(file, backup)
try:
    modifier.show_viewport = True
    for entry, _ in overrides:
        entry.enabled = True
    bpy.context.view_layer.update()
    assert content(obj) == tuple(expected), 'Shoes original data changed unexpectedly'
    assert context_state() == context_before, 'Rig pose/context changed'
    parenting._verify_world(obj, world)
    collected = unity_export.collect_character(bpy.context, rig, config)
    assert obj in collected['objects'], 'Shoes is still missing from export'
except Exception:
    modifier.show_viewport = False
    for entry, old in overrides:
        entry.enabled = old
    raise
report = {'status': 'PASS', 'viewport_binding_restored': True,
          'weights_mesh_keys_modifiers_except_switch_metadata_action_channels_preserved': True,
          'parent_and_world_preserved': True, 'rig_pose_and_context_preserved': True,
          'export_objects': [o.name for o in collected['objects']],
          'rebind_pending_additive_bone_fix': True, 'backup': str(backup), 'saved': False}
report['stop_result'] = sorted(bpy.ops.blendermcp.stop_server())
report['save_result'] = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(file), check_existing=False))
assert report['save_result'] == ['FINISHED']
report['saved'] = True
report['sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
for area in bpy.context.screen.areas:
    area.tag_redraw()
(folder/'modifier_restored.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
