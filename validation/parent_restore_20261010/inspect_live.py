"""Inspect original artist meshes before the authorized parent restoration."""
import bpy
import json
from pathlib import Path
from character_designer import quick_bind

folder = Path(r'D:\Blender\Projects\Character\X\validation\parent_restore_20261010')
assert bpy.data.filepath == r'D:\Blender\Projects\Character\X\X.blend'
assert not bpy.app.background
rig = bpy.data.objects['CoshaRig']
assert rig.type == 'ARMATURE' and rig.name in bpy.context.scene.objects
report = {
    'scene': bpy.context.scene.name,
    'filepath': bpy.data.filepath,
    'mode': bpy.context.mode,
    'frame': bpy.context.scene.frame_current,
    'active': getattr(bpy.context.view_layer.objects.active, 'name', None),
    'selected': [o.name for o in bpy.context.selected_objects],
    'dirty': bpy.data.is_dirty,
    'rig_world': [list(row) for row in rig.matrix_world],
    'meshes': [],
}
for name in ('Cosha', 'Clothes', 'Dress', 'Hair', 'Jacket', 'Shoes', 'Stocking'):
    obj = bpy.data.objects[name]
    assert obj.type == 'MESH' and name in bpy.context.scene.objects
    report['meshes'].append({
        'name': name,
        'parent': getattr(obj.parent, 'name', None),
        'parent_type': obj.parent_type,
        'parent_bone': obj.parent_bone,
        'library': getattr(obj.library, 'filepath', None),
        'collections': [c.name for c in obj.users_collection],
        'vertex_count': len(obj.data.vertices),
        'vertex_groups': len(obj.vertex_groups),
        'modifiers': [{'name': m.name, 'type': m.type,
                       'target': getattr(getattr(m, 'object', None), 'name', None),
                       'viewport': m.show_viewport, 'render': m.show_render}
                      for m in obj.modifiers],
        'constraints': [{'name': c.name, 'type': c.type, 'mute': c.mute,
                         'influence': c.influence} for c in obj.constraints],
        'removed_binding': quick_bind.has_removed_binding(obj),
        'binding_owner': getattr(obj.get(quick_bind.RIG_KEY), 'name', None),
        'parent_metadata': {k: str(obj[k]) for k in obj.keys() if 'parent' in k},
        'action': getattr(getattr(obj.animation_data, 'action', None), 'name', None),
        'world': [list(row) for row in obj.matrix_world],
    })
folder.mkdir(parents=True, exist_ok=True)
(folder / 'inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
