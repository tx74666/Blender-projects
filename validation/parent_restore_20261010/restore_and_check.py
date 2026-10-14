"""Restore only missing artist object parents; keep deformation data intact."""
import bpy
import hashlib
import json
import shutil
import struct
from pathlib import Path
from character_designer import quick_bind
from character_designer import quick_bind_parenting as parenting

folder = Path(r'D:\Blender\Projects\Character\X\validation\parent_restore_20261010')
file = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath) == file and not bpy.app.background
assert bpy.context.scene.name == 'Scene'
rig = bpy.data.objects['CoshaRig']
meshes = [bpy.data.objects[n] for n in ('Cosha', 'Clothes', 'Dress', 'Hair', 'Jacket', 'Shoes', 'Stocking')]
targets = [bpy.data.objects[n] for n in ('Jacket', 'Shoes')]
assert all(o.parent == rig and o.parent_type == 'OBJECT' for o in meshes if o not in targets)

def simple(value):
    if isinstance(value, bpy.types.ID):
        return (value.bl_rna.identifier, value.as_pointer(), value.name)
    if hasattr(value, 'to_dict'):
        return {k: simple(v) for k, v in value.to_dict().items()}
    if hasattr(value, 'to_list'):
        return value.to_list()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return tuple(value)
    except TypeError:
        return str(value)

def rna_values(value):
    return {p.identifier: simple(getattr(value, p.identifier)) for p in value.bl_rna.properties
            if p.identifier != 'rna_type' and p.type != 'COLLECTION'}

def animation_signature(obj):
    anim = obj.animation_data
    if not anim:
        return None
    action = anim.action
    curves = []
    if action:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, 'channelbags', []):
                    for curve in bag.fcurves:
                        curves.append((curve.data_path, curve.array_index,
                                       [rna_values(p) for p in curve.keyframe_points],
                                       [rna_values(m) for m in curve.modifiers]))
    return (rna_values(anim), curves, [(d.data_path, d.array_index, rna_values(d.driver)) for d in anim.drivers],
            [(t.name, [rna_values(s) for s in t.strips]) for t in anim.nla_tracks])

def content(obj):
    digest = hashlib.sha256()
    for v in obj.data.vertices:
        digest.update(struct.pack('<3f', *v.co))
        for member in v.groups:
            digest.update(struct.pack('<If', member.group, member.weight))
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            digest.update(repr((key.name, key.value, key.mute)).encode())
            for point in key.data:
                digest.update(struct.pack('<3f', *point.co))
    return (obj.data.as_pointer(), digest.hexdigest(),
            [(g.name, g.lock_weight) for g in obj.vertex_groups],
            [(m.as_pointer(), rna_values(m)) for m in obj.modifiers],
            {k: simple(obj[k]) for k in obj.keys()}, animation_signature(obj),
            parenting._channels(obj), obj.rotation_mode,
            [c.as_pointer() for c in obj.users_collection], obj.hide_viewport, obj.hide_render)

def context_state():
    return (bpy.context.scene.as_pointer(), bpy.context.view_layer.as_pointer(), bpy.context.mode,
            bpy.context.view_layer.objects.active, tuple(bpy.context.selected_objects),
            bpy.context.scene.frame_current, bpy.context.scene.frame_subframe,
            bpy.context.scene.tool_settings.use_keyframe_insert_auto,
            tuple((p.name, tuple(tuple(row) for row in p.matrix_basis)) for p in rig.pose.bones),
            tuple(tuple(row) for row in rig.matrix_world))

def evaluated_world(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return [tuple(evaluated.matrix_world @ v.co) for v in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()

for obj in targets:
    assert obj.parent is None and obj.name in bpy.context.scene.objects and obj.mode == 'OBJECT'
    assert not quick_bind.has_removed_binding(obj)
    parenting._validate_objects(bpy.context, obj, rig)
    parenting._check_parent_change(obj)
    parenting._check_cycle(obj, rig)
    record = parenting._record(obj)
    assert record is None or obj.get(parenting.PARENT_RIG_KEY) == rig
states = {o.name: parenting.capture_state(o) for o in meshes}
before_content = {o.name: content(o) for o in meshes}
before_context = context_state()
before_eval = {o.name: evaluated_world(o) for o in targets}
outliners = [(a.spaces.active, a.spaces.active.use_filter_children)
             for a in bpy.context.screen.areas if a.type == 'OUTLINER']
backup = folder / 'X.pre_restore_last_saved.blend'
assert not backup.exists(), 'Do not replace the existing recovery file'
shutil.copy2(file, backup)
geometry_changes = {}
try:
    for obj in targets:
        obj.parent = rig
        obj.parent_type = 'OBJECT'
        obj.parent_bone = ''
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
    for space, _ in outliners:
        space.use_filter_children = True
    bpy.context.view_layer.update()
    assert context_state() == before_context, 'Artist context or rig pose changed'
    for obj in meshes:
        assert obj.parent == rig and obj.parent_type == 'OBJECT'
        parenting._verify_world(obj, states[obj.name]['world'])
        assert content(obj) == before_content[obj.name], obj.name + ': original data changed'
    for obj in targets:
        after = evaluated_world(obj)
        before = before_eval[obj.name]
        assert len(after) == len(before)
        error = max((abs(x-y) for a,b in zip(after,before) for x,y in zip(a,b)), default=0.0)
        assert error <= 1e-5, obj.name + ': evaluated mesh moved'
        geometry_changes[obj.name] = {'vertices': len(after), 'max_world_coordinate_delta': error}
except Exception:
    for obj in reversed(targets):
        parenting.rollback(bpy.context, obj, states[obj.name])
    for space, old in outliners:
        space.use_filter_children = old
    raise
report = {'status': 'PASS', 'restored_parents': [o.name for o in targets],
          'already_correct': [o.name for o in meshes if o not in targets], 'parent': rig.name,
          'outliner_children_enabled': True, 'content_weights_keys_modifiers_metadata_animation_preserved': True,
          'world_transform_preserved': True, 'context_and_rig_pose_preserved': True,
          'evaluated_mesh_comparison': geometry_changes,
          'jacket_has_skinning': False, 'shoes_armature_viewport': False,
          'backup': str(backup), 'saved': False}
(folder / 'restoration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
for area in bpy.context.screen.areas:
    area.tag_redraw()
print(json.dumps(report, ensure_ascii=False))
