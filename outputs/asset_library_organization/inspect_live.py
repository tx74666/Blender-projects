import bpy
import json
from pathlib import Path

def browser(space):
    params = getattr(space, 'params', None)
    return {'type': space.type, 'browse_mode': getattr(space, 'browse_mode', None),
            'library': getattr(params, 'asset_library_reference', None),
            'catalog_id': getattr(params, 'catalog_id', None),
            'directory': str(getattr(params, 'directory', ''))}

report = {
    'filepath': bpy.data.filepath,
    'dirty': bpy.data.is_dirty,
    'asset_libraries': [{'name': a.name, 'path': a.path, 'import_method': a.import_method}
                        for a in bpy.context.preferences.filepaths.asset_libraries],
    'windows': [{'screen': w.screen.name, 'workspace': w.workspace.name,
                 'areas': [browser(a.spaces.active) for a in w.screen.areas]}
                for w in bpy.context.window_manager.windows],
    'rigs': [o.name for o in bpy.context.scene.objects if o.type == 'ARMATURE'],
    'actions': [{'name': a.name, 'asset': a.asset_data is not None,
                 'catalog_id': str(a.asset_data.catalog_id) if a.asset_data else None,
                 'range': list(a.frame_range)} for a in bpy.data.actions],
}
Path(r'D:\Blender\Projects\Character\X\outputs\asset_library_organization\live_inventory.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ASSET_LIBRARY_INVENTORY_SAVED', report['asset_libraries'])
