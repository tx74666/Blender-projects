import bpy

source = bpy.data.objects['Hair3']
def visit(layer, path=()):
    path = (*path, layer)
    if source.name in layer.collection.objects:
        print('HAIR_COLLECTION_PATH', [(item.name, item.exclude, item.hide_viewport,
              item.collection.hide_viewport) for item in path], flush=True)
    for child in layer.children:
        visit(child, path)

print('VIEW_LAYER', bpy.context.view_layer.name, 'VISIBLE', source.visible_get(), flush=True)
visit(bpy.context.view_layer.layer_collection)
