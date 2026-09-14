import bpy
import character_designer
from pathlib import Path
import json

assert tuple(character_designer.bl_info['version']) == (0, 57, 1)
assert bpy.data.filepath == r'D:\Blender\Projects\Character\X\X.blend'
rig = bpy.data.objects['CoshaRig']
config = rig.character_designer_unity_export
config.directory = r'D:\Blender\Projects\Character\X\outputs\unity_export\LiveTest'
config.filename = 'Cosha'
for name in ('Hair', 'Dress', 'Jacket'):
    obj = bpy.context.scene.objects.get(name)
    if obj and not any(entry.object == obj for entry in config.extras):
        entry = config.extras.add()
        entry.object = obj
        entry.enabled = True
config.show_objects = False
bpy.context.window_manager.character_designer.ui_page = 'MISCELLANEOUS'
Path(r'D:\Blender\Projects\Character\X\outputs\unity_export\live_configured.json').write_text(
    json.dumps({'version': character_designer.bl_info['version'],
                'folder': config.directory, 'extras':[e.object.name for e in config.extras]}), encoding='utf8')
bpy.context.area.type = 'VIEW_3D'
