import bpy
import json
from pathlib import Path

def layer_paths(layer, parent=()):
    route = parent + (layer.name,)
    yield layer, route
    for child in layer.children:
        yield from layer_paths(child, route)

layers = list(layer_paths(bpy.context.view_layer.layer_collection))
report = []
for obj in bpy.context.scene.objects:
    if obj.type == 'CURVE' and not obj.name.startswith('SK_Dress_Wire'):
        report.append({
            'name': obj.name, 'visible': obj.visible_get(), 'hide_viewport': obj.hide_viewport,
            'hide_render': obj.hide_render, 'hide_get': obj.hide_get(),
            'collections': [{'name': c.name, 'hide_viewport': c.hide_viewport,
                             'paths': [{'names': names, 'exclude': layer.exclude, 'visible': layer.is_visible}
                                       for layer, names in layers if layer.collection == c]}
                            for c in obj.users_collection],
        })
folder = Path('D:/Blender/Projects/Character/X/validation/hierarchy_experiments_20261010')
(folder/'auxiliary_curves.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
