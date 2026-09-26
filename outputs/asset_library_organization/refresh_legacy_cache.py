import bpy
import json
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\outputs\asset_library_organization')
manifest = json.loads((out / 'organization_manifest.json').read_text(encoding='utf-8'))
lib = bpy.context.preferences.filepaths.asset_libraries['Procedural Material']
original_path = lib.path
assert original_path == manifest['material_root']
legacy_path = str(Path(manifest['legacy_catalog_synchronized']).parent)
asset_window = bpy.context.window
asset_area = bpy.context.area
log = []
step = 0

def refresh_legacy_and_current():
    global step
    try:
        space = asset_area.spaces.active
        if space.type != 'FILE_BROWSER' or space.params is None:
            return 0.25
        region = next(r for r in asset_area.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(window=asset_window, area=asset_area, region=region):
            if step == 0:
                lib.path = legacy_path
                space.params.asset_library_reference = lib.name
                log.append({'step': 'old-path', 'path': lib.path})
            elif step == 1:
                log.append({'step': 'old-refresh', 'result': list(bpy.ops.asset.library_refresh(use_remote_listing=False))})
            elif step == 2:
                lib.path = original_path
                space.params.asset_library_reference = 'ALL'
                space.params.asset_library_reference = lib.name
                log.append({'step': 'restore-path', 'path': lib.path})
            elif step == 3:
                log.append({'step': 'current-refresh', 'result': list(bpy.ops.asset.library_refresh(use_remote_listing=False))})
            elif step == 4:
                space.params.asset_library_reference = 'ALL'
                space.params.asset_catalog_visibility = 'ALL'
                log.append({'step': 'all-refresh', 'result': list(bpy.ops.asset.library_refresh(use_remote_listing=False))})
                log.append({'step': 'save-final-preferences', 'result': list(bpy.ops.wm.save_userpref())})
        asset_area.tag_redraw()
        (out / 'cache_refresh_result.json').write_text(json.dumps(log, indent=2), encoding='utf-8')
        step += 1
        return 0.8 if step <= 4 else None
    except Exception as exc:
        lib.path = original_path
        log.append({'error': repr(exc), 'restored_path': lib.path})
        (out / 'cache_refresh_result.json').write_text(json.dumps(log, indent=2), encoding='utf-8')
        return None

def start_cache_refresh():
    asset_area.ui_type = 'ASSETS'
    bpy.app.timers.register(refresh_legacy_and_current, first_interval=0.25)
    return None

bpy.app.timers.register(start_cache_refresh, first_interval=0.2)
print('Refreshing legacy material catalog cache, then restoring configured library')
