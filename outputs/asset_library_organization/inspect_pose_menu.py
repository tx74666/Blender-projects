import addon_utils
import bpy
import json
import sys
from pathlib import Path

area_to_restore = bpy.context.area
assert area_to_restore.type == 'CONSOLE'
report = {
    'blender': bpy.app.version_string,
    'pose_library_check': list(addon_utils.check('pose_library')),
    'preference_enabled': 'pose_library' in bpy.context.preferences.addons,
    'mode': bpy.context.mode,
    'object': bpy.context.object.name if bpy.context.object else None,
    'shelf_registered': hasattr(bpy.types, 'VIEW3D_AST_pose_library'),
    'header_menu_registered': hasattr(bpy.types, 'ASSETBROWSER_MT_asset'),
    'module': getattr(sys.modules.get('pose_library'), '__file__', None),
    'menu_callbacks': [f'{f.__module__}.{f.__name__}' for f in
        getattr(bpy.types.ASSETBROWSER_MT_context_menu.draw, '_draw_funcs', ())],
    'browsers': [],
}
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type != 'FILE_BROWSER' or area.ui_type != 'ASSETS':
            continue
        region = next(r for r in area.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(window=window, area=area, region=region):
            asset = bpy.context.asset
            ref = getattr(bpy.context, 'asset_library_reference', None)
            report['browsers'].append({
                'selected_asset': asset.name if asset else None,
                'asset_type': asset.id_type if asset else None,
                'library_context_present': ref is not None,
                'library_context_type': type(ref).__name__,
                'library_selected': area.spaces.active.params.asset_library_reference,
            })
target = Path(r'D:\Blender\Projects\Character\X\outputs\asset_library_organization\pose_menu_inventory.json')
target.write_text(json.dumps(report, indent=2), encoding='utf8')
print(json.dumps(report, indent=2))

def restore_image_editor():
    area_to_restore.ui_type = 'IMAGE_EDITOR'
    area_to_restore.tag_redraw()

bpy.app.timers.register(restore_image_editor, first_interval=.25)
