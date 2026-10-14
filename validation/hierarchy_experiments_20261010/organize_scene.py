"""Move only Jacket outside the rig; compact only the current Outliner."""
import ast
import bpy
import hashlib
import json
from mathutils import Matrix
from pathlib import Path
import struct
from character_designer import unity_export
from character_designer import quick_bind_parenting as parenting

folder = Path('D:/Blender/Projects/Character/X/validation/hierarchy_experiments_20261010')
artist = Path('D:/Blender/Projects/Character/X/X.blend')
assert Path(bpy.data.filepath) == artist and not bpy.app.background
assert bpy.context.scene.name == 'Scene'
assert bpy.context.mode == 'OBJECT', 'Keep active artist mesh edits outside this hierarchy operation'
rig = bpy.data.objects['CoshaRig']
jacket, shoes = (bpy.data.objects[name] for name in ('Jacket', 'Shoes'))
assert jacket.parent == rig and jacket.parent_type == 'OBJECT'
assert not jacket.library
assert not any(not c.mute and c.influence != 0 for c in jacket.constraints)
assert parenting._record(jacket) is None, 'A newer owned parent record needs separate review'
identity = Matrix.Identity(4)
effective = rig.matrix_world @ jacket.matrix_parent_inverse
assert max(abs(a-b) for ra,rb in zip(effective,identity) for a,b in zip(ra,rb)) <= 1e-5, 'Parent transform is no longer cancelled; preserve channels before choosing another detach method'
outliners = [(a.spaces.active, a.spaces.active.use_filter_object_others)
             for a in bpy.context.screen.areas if a.type == 'OUTLINER' and a.spaces.active.display_mode == 'VIEW_LAYER']
assert outliners
assert len(outliners) == 1, 'Review multiple Outliners before applying this display preference'
wires = [o for o in bpy.context.scene.objects if o.type == 'CURVE' and o.name.startswith('SK_Dress_Wire')]
assert len(wires) == 11
others = [o for o in bpy.context.scene.objects if o.type not in {'MESH','ARMATURE','EMPTY','LIGHT','CAMERA'}]
extra_curves = [o for o in others if o not in wires]
assert {o.name for o in extra_curves} == {'Line.001', 'Strap.001_SplineIK_Curve.001'}
assert all(o.type == 'CURVE' and not o.visible_get() and
           {c.name for c in o.users_collection} == {'ShoeDone_Backup'} for o in extra_curves), 'Review any other visible artist object before hiding this Outliner type'

# Restore Shoes and the rig after an incidental Outliner selection during UI access.
assert bpy.context.view_layer.objects.active in {bpy.data.objects['SK_Dress_Wire_02'], shoes}, 'User active object changed since this cleanup began'
for obj in bpy.context.selected_objects:
    obj.select_set(False)
for obj in (rig, shoes):
    obj.select_set(True)
bpy.context.view_layer.objects.active = shoes

# Save a copy of current unsaved artist work before changing the hierarchy.
backup = folder / 'X.before_organizing_final.blend'
assert not backup.exists()
backup_result = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True, check_existing=False))
assert backup_result == ['FINISHED'] and Path(bpy.data.filepath) == artist, 'Backup copy changed current filepath or did not finish'
helper = Path('D:/Blender/Projects/Character/X/validation/parent_restore_20261010/restore_and_check.py')
tree = ast.parse(helper.read_text(encoding='utf-8'))
defs = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)], type_ignores=[])
exec(compile(defs, str(helper), 'exec'), globals())
state = parenting.capture_state(jacket)
before = {o.name: content(o) for o in (jacket, shoes)}
shoe_parent = (shoes.parent, shoes.parent_type, shoes.parent_bone, shoes.matrix_parent_inverse.copy(), shoes.matrix_world.copy())
context_before = context_state()
before_eval = evaluated_world(jacket)
wire_state = tuple((o.as_pointer(), o.data.as_pointer(), o.parent, o.parent_type, o.parent_bone,
                    o.hide_viewport, o.hide_render, o.hide_get(), tuple(c.as_pointer() for c in o.users_collection)) for o in wires)
try:
    jacket.parent = None
    jacket.matrix_parent_inverse = state['inverse']
    for space, _ in outliners:
        space.use_filter_object_others = False
    bpy.context.view_layer.update()
    parenting._verify_world(jacket, state['world'])
    assert jacket.matrix_parent_inverse == state['inverse'], 'Jacket inverse matrix changed automatically when clearing parent'
    assert before == {o.name: content(o) for o in (jacket, shoes)}, 'Artist mesh/weights/modifiers/action/channels changed'
    assert context_state() == context_before, 'Artist pose/frame/selection changed'
    assert (shoes.parent, shoes.parent_type, shoes.parent_bone, shoes.matrix_parent_inverse) == shoe_parent[:4], 'Shoes parent or inverse changed'
    parenting._verify_world(shoes, shoe_parent[4])
    assert wire_state == tuple((o.as_pointer(), o.data.as_pointer(), o.parent, o.parent_type, o.parent_bone,
                               o.hide_viewport, o.hide_render, o.hide_get(), tuple(c.as_pointer() for c in o.users_collection)) for o in wires), 'Wire relationship or visibility changed'
    after_eval = evaluated_world(jacket)
    assert len(before_eval) == len(after_eval), 'Jacket evaluated vertex count changed'
    error = max((abs(a-b) for va,vb in zip(before_eval,after_eval) for a,b in zip(va,vb)), default=0.0)
    assert error <= 1e-5, 'Jacket evaluated geometry moved'
    exported = unity_export.collect_character(bpy.context, rig, rig.character_designer_unity_export)
    assert shoes in exported['objects'], 'Shoes missing from current export inventory'
except Exception:
    parenting.rollback(bpy.context, jacket, state)
    for space, old in outliners:
        space.use_filter_object_others = old
    raise
report = {
    'passed': True, 'jacket_parent': None, 'jacket_original_data_preserved': True,
    'jacket_evaluated_max_world_delta': error, 'shoes_unchanged': True,
    'shoes_parent': shoes.parent.name if shoes.parent else None,
    'shoes_in_export_inventory': True, 'export_objects': [o.name for o in exported['objects']],
    'wire_objects_hidden_only_from_current_outliner': len(wires),
    'already_invisible_backup_curves_also_filtered': [o.name for o in extra_curves],
    'wire_parents_data_visibility_and_collections_preserved': True,
    'rig_pose_frame_mode_selection_preserved': True, 'backup': str(backup),
    'backup_save_result': backup_result,
}
report['stop_result'] = sorted(bpy.ops.blendermcp.stop_server())
report['save_result'] = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(artist), check_existing=False))
assert report['save_result'] == ['FINISHED']
assert Path(bpy.data.filepath) == artist and artist.is_file() and artist.stat().st_size > 0
report['artist_is_dirty_immediately_after_save'] = bpy.data.is_dirty
report['artist_saved_sha256'] = hashlib.sha256(artist.read_bytes()).hexdigest()
for area in bpy.context.screen.areas:
    area.tag_redraw()
(folder/'organized.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
