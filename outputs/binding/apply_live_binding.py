import bpy
import json
from pathlib import Path
import character_designer
from character_designer import character_setup, quick_bind
from character_designer.selected_bone_weights import _capture_vertex_groups, _restore_vertex_groups

root = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (root / 'X.blend').resolve()
assert character_designer.bl_info['version'] == (0, 43, 1)
assert bpy.context.mode == 'OBJECT'
backup = json.loads((root / 'outputs/binding/live_binding_backup.json').read_text(encoding='utf-8'))
assert Path(backup['backup']).is_file()
rig = bpy.data.objects['CoshaRig']
body = bpy.data.objects['Cosha']
targets = [bpy.data.objects[name] for name in ('Clothes', 'Stocking', 'Shoes')]
state = bpy.context.scene.character_designer_setup
assert state.rig in (None, rig) and state.body in (None, body)
for target in targets:
    assert not quick_bind.has_binding_backup(target), 'This mesh already has a reversible Quick Bind'
    quick_bind._validate(bpy.context, target, rig, body, 'TRANSFER')

def geometry(obj):
    return (obj.data.as_pointer(), tuple(tuple(v.co) for v in obj.data.vertices),
            tuple(tuple(p.vertices) for p in obj.data.polygons),
            tuple(tuple(e.vertices) for e in obj.data.edges),
            tuple(tuple(row) for row in obj.matrix_world),
            tuple((uv.name, tuple(tuple(x.uv) for x in uv.data)) for uv in obj.data.uv_layers))

before = {obj: (geometry(obj), _capture_vertex_groups(obj), list(obj.modifiers)) for obj in targets}
source_before = geometry(body), _capture_vertex_groups(body)
result = {'backup': backup['backup'], 'version': '0.43.1', 'targets': {}}
assert bpy.ops.ed.undo_push(message='Before Character Quick Bind') == {'FINISHED'}
try:
    for obj in targets:
        result['targets'][obj.name] = quick_bind.bind_weights(bpy.context, obj, rig, body=body, mode='TRANSFER')
        assert geometry(obj) == before[obj][0]
    assert (geometry(body), _capture_vertex_groups(body)) == source_before
except Exception:
    for obj, (_, groups, modifiers) in before.items():
        if quick_bind.has_binding_backup(obj):
            quick_bind.restore_binding(bpy.context, obj)
        _restore_vertex_groups(obj, groups)
        for modifier in tuple(obj.modifiers):
            if modifier not in modifiers:
                obj.modifiers.remove(modifier)
    raise

state.rig = rig
state.body = body
for name, role in [('Clothes', 'CLOTHING'), ('Stocking', 'STOCKINGS'), ('Shoes', 'SHOES'),
                   ('Hair1', 'HAIR'), ('Hair2', 'HAIR'), ('Hair3', 'HAIR'), ('Dress', 'SKIRT')]:
    if name in bpy.data.objects:
        character_setup.remember_asset(bpy.context, bpy.data.objects[name], role)
state.active_asset = next(i for i, item in enumerate(state.assets) if item.object == bpy.data.objects['Clothes'])
state.last_message = 'Clothes, Stocking and Shoes bound. Ready for weight painting.'
bpy.context.window_manager.character_designer.ui_page = 'WEIGHT'
assert bpy.ops.ed.undo_push(message='Character Quick Bind') == {'FINISHED'}
result['geometry_uv_transforms_preserved'] = True
result['body_source_unchanged'] = True
result['saved_restore_available'] = all(quick_bind.has_binding_backup(obj) for obj in targets)
(root / 'outputs/binding/live_binding_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('LIVE_CHARACTER_BINDING_VERIFIED', result)
