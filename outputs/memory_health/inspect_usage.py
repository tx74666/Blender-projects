import bpy
import json
import sys
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\outputs\memory_health')
def tree_images(tree, seen=None):
    seen = set() if seen is None else seen
    if tree is None or tree.as_pointer() in seen:
        return set()
    seen.add(tree.as_pointer())
    result = set()
    for node in tree.nodes:
        image = getattr(node, 'image', None)
        if image:
            result.add(image.name)
        result.update(tree_images(getattr(node, 'node_tree', None), seen))
    return result

materials = {}
for mat in bpy.data.materials:
    objs = [o for o in bpy.data.objects if any(s.material == mat for s in o.material_slots)]
    materials[mat.name] = {'images': sorted(tree_images(mat.node_tree)), 'users':mat.users,
        'fake_user':mat.use_fake_user,
        'objects':[{'name':o.name, 'visible': o.visible_get() if o.name in bpy.context.view_layer.objects else False} for o in objs]}
active_images = set()
for info in materials.values():
    if any(o['visible'] for o in info['objects']):
        active_images.update(info['images'])
editors=[]
for screen in bpy.data.screens:
    for area in screen.areas:
        image = getattr(area.spaces.active, 'image', None)
        if image:
            editors.append({'screen':screen.name, 'type':area.type, 'image':image.name})
            active_images.add(image.name)
for scene in bpy.data.scenes:
    active_images.update(tree_images(getattr(scene, 'compositing_node_group', None)))
    if scene.world:
        active_images.update(tree_images(scene.world.node_tree))
for obj in bpy.data.objects:
    if isinstance(obj.data, bpy.types.Image):
        active_images.add(obj.data.name)
    for mod in obj.modifiers:
        active_images.update(tree_images(getattr(mod, 'node_group', None)))
candidate=[]
for im in bpy.data.images:
    if im.name not in active_images and im.has_data and im.packed_file and not im.is_dirty and im.source=='FILE':
        candidate.append({'name':im.name,'size':list(im.size),'users':im.users})
caches={}
for name, mod in list(sys.modules.items()):
    if mod and any(x in name for x in ('random_realm_builder_exporter','character_designer')):
        values={}
        for attr,val in vars(mod).items():
            if any(x in attr.lower() for x in ('cache','preview','session')) and isinstance(val,(dict,list,set,tuple)):
                values[attr]={'length':len(val),'shallow_bytes':sys.getsizeof(val)}
        if values:caches[name]=values
report={'materials':materials,'image_editors':editors,'active_images':sorted(active_images),'buffer_candidates':candidate,'addon_caches':caches}
(out/'image_usage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('IMAGE USAGE SAVED; safe inactive packed buffer candidates:',candidate)
