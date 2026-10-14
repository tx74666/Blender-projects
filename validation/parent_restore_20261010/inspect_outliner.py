import bpy
import json
from pathlib import Path
rows = []
for area in bpy.context.screen.areas:
    if area.type == 'OUTLINER':
        space = area.spaces.active
        props = []
        for p in space.bl_rna.properties:
            if any(word in p.identifier for word in ('hierarchy', 'children', 'filter_object', 'filter_collection')):
                props.append({'id': p.identifier, 'description': p.description,
                              'value': getattr(space, p.identifier)})
        rows.append({'area': area.as_pointer(), 'display_mode': space.display_mode, 'props': props})
result = {'outliners': rows, 'server_port': bpy.context.scene.blendermcp_port}
Path(r'D:\Blender\Projects\Character\X\validation\parent_restore_20261010\outliner_before.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
