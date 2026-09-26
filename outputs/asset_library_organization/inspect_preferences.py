import bpy
import json
from pathlib import Path
bpy.ops.wm.read_userpref()
libraries = [{'name': a.name, 'path': a.path, 'import_method': a.import_method}
             for a in bpy.context.preferences.filepaths.asset_libraries]
Path(r'D:\Blender\Projects\Character\X\outputs\asset_library_organization\saved_libraries.json').write_text(
    json.dumps(libraries, indent=2), encoding='utf-8')
print('SAVED_LIBRARIES', json.dumps(libraries))
