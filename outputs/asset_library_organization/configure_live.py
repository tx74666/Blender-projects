import bpy
import json
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\outputs\asset_library_organization')
manifest = json.loads((out / 'organization_manifest.json').read_text(encoding='utf-8'))
baseline = json.loads((out / 'live_inventory.json').read_text(encoding='utf-8'))
assert Path(bpy.data.filepath) == Path(baseline['filepath']), 'Unexpected Blender project'
libs = bpy.context.preferences.filepaths.asset_libraries
before = [{'name': lib.name, 'path': lib.path, 'import_method': lib.import_method} for lib in libs]
assert before == baseline['asset_libraries'], 'Library preferences changed since inspection'
assert bpy.context.area.type == 'CONSOLE', 'Run from the temporary asset-area console'
for key in ('material_root', 'nodes_root', 'pose_root'):
    assert (Path(manifest[key]) / 'blender_assets.cats.txt').is_file(), key

libs['Nodes'].path = manifest['nodes_root']
libs['Procedural Material'].path = manifest['material_root']
pose_lib = libs.new(name='Pose Library', directory=manifest['pose_root'])
assert pose_lib.name == 'Pose Library'
pose_lib.import_method = 'PACK'
after = [{'name': lib.name, 'path': lib.path, 'import_method': lib.import_method} for lib in libs]
assert after[1] == before[1], 'BlenderKit settings must be preserved'
result = bpy.ops.wm.save_userpref()
assert result == {'FINISHED'}, result

receipt = {'before': before, 'after': after, 'preferences_saved': True,
           'project_filepath': bpy.data.filepath, 'project_saved': False}
(out / 'live_configuration_result.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
asset_window = bpy.context.window
asset_area = bpy.context.area
asset_area.ui_type = 'ASSETS'

def refresh_asset_browser():
    try:
        space = asset_area.spaces.active
        if space.type != 'FILE_BROWSER' or space.params is None:
            return 0.2
        space.params.asset_library_reference = 'ALL'
        space.params.asset_catalog_visibility = 'ALL'
        space.params.filter_search = ''
        region = next(region for region in asset_area.regions if region.type == 'WINDOW')
        with bpy.context.temp_override(window=asset_window, area=asset_area, region=region):
            result = bpy.ops.asset.library_refresh(use_remote_listing=False)
        receipt['refresh_result'] = list(result)
        receipt['browser_library'] = space.params.asset_library_reference
        receipt['browser_type'] = asset_area.ui_type
        asset_area.tag_redraw()
    except Exception as exc:
        receipt['refresh_error'] = repr(exc)
    (out / 'live_configuration_result.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return None

bpy.app.timers.register(refresh_asset_browser, first_interval=0.25)
print('ASSET LIBRARIES SAVED; RESTORING ASSET BROWSER')
