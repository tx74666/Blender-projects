"""Read production X, export to test folder, compare source, never save X."""
import bpy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import character_setup, unity_export

character_designer.register()
out = Path(r'D:\Blender\Projects\Character\X\outputs\unity_export')
out.mkdir(exist_ok=True)
rig = bpy.data.objects['CoshaRig']
setup = character_setup.settings(bpy.context)
inventory = {
    'source': bpy.data.filepath, 'mode': bpy.context.mode,
    'rig': setup.rig.name if setup.rig else None,
    'body': setup.body.name if setup.body else None,
    'assets': [(a.object.name if a.object else None, a.role) for a in setup.assets],
    'meshes': [{'name': o.name, 'parent': o.parent.name if o.parent else None,
                'collections': [c.name for c in o.users_collection],
                'modifiers': [(m.name, m.type, m.show_viewport,
                               m.object.name if m.type == 'ARMATURE' and m.object else None)
                              for m in o.modifiers],
                'vertices': len(o.data.vertices),
                'keys': list(o.data.shape_keys.key_blocks.keys()) if o.data.shape_keys else []}
               for o in bpy.context.scene.objects if o.type == 'MESH'],
}
(out / 'source_inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf8')
print('X_EXPORT_INVENTORY', json.dumps({k:v for k,v in inventory.items() if k != 'meshes'}))

def digest():
    h = hashlib.sha256()
    def add(value):
        h.update(repr(value).encode('utf8'))
    add((bpy.context.mode, bpy.context.scene.frame_current, bpy.context.view_layer.objects.active.name))
    for obj in sorted(bpy.context.scene.objects, key=lambda o:o.name):
        add((obj.name, obj.type, list(map(tuple, obj.matrix_world)), obj.select_get(),
             obj.hide_get(), obj.hide_viewport, obj.hide_render, obj.parent.name if obj.parent else None,
             [(m.name,m.type) for m in obj.modifiers],
             obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None))
        if obj.type == 'ARMATURE':
            for pb in obj.pose.bones:
                add((pb.name, list(map(tuple, pb.matrix_basis)), pb.bone.parent.name if pb.bone.parent else None,
                     list(map(tuple,pb.bone.matrix_local)), pb.custom_shape.name if pb.custom_shape else None,
                     [(c.name,c.type,c.influence,c.mute) for c in pb.constraints]))
        if obj.type == 'MESH':
            add([(tuple(v.co),[(g.group,g.weight) for g in v.groups]) for v in obj.data.vertices])
            add([tuple(p.vertices) for p in obj.data.polygons])
            if obj.data.shape_keys:
                for key in obj.data.shape_keys.key_blocks:
                    add((key.name,key.value,key.relative_key.name,key.vertex_group, [tuple(v.co) for v in key.data]))
    return h.hexdigest()

config = SimpleNamespace(directory=str(out / 'Cosha'), filename='Cosha',
                         asset_id='x-validation-0570', extras=[])
if '--export' in sys.argv:
    # Main scene meshes are inventoried above before choosing any unbound extras.
    for name in ('Hair', 'Dress', 'Clothes', 'Jacket', 'Shoes', 'Stocking'):
        obj = bpy.context.scene.objects.get(name)
        if obj:
            config.extras.append(SimpleNamespace(object=obj, enabled=True))
    before = digest()
    result = unity_export.export_character(bpy.context, rig, config)
    after = digest()
    assert before == after, 'Source geometry/rig/pose/selection changed during export'
    result['source_unchanged'] = before == after
    result['source_digest'] = before
    (out / 'x_validation.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print('X_EXPORT_VALIDATED', json.dumps(result))
