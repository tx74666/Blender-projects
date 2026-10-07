import bpy
import json
import os
from pathlib import Path

folder = Path(__file__).resolve().parent
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve(), bpy.data.filepath
groups = ('actions', 'materials', 'objects', 'collections', 'node_groups', 'worlds', 'brushes')
report = {'pid': os.getpid(), 'runtime': bpy.app.version_string, 'filepath': bpy.data.filepath,
          'dirty': bpy.data.is_dirty, 'mode': bpy.context.mode,
          'libraries': [{'name': x.name, 'path': x.path} for x in bpy.context.preferences.filepaths.asset_libraries],
          'linked_libraries': [x.filepath for x in bpy.data.libraries], 'assets': {}, 'browser': [],
          'library_load_doc': bpy.data.libraries.load.__doc__}
for group in groups:
    entries = []
    for block in getattr(bpy.data, group):
        if not block.asset_data:
            continue
        used_objects = []
        if group == 'materials':
            used_objects = [o.name for o in bpy.data.objects if any(s.material == block for s in o.material_slots)]
        info = {'name': block.name, 'users': block.users,
                'fake_user': block.use_fake_user,
                'library': block.library.filepath if block.library else None,
                'catalog': block.asset_data.catalog_id, 'description': block.asset_data.description,
                'used_objects': used_objects,
                'custom_keys': list(block.keys()),
                'tags': [t.name for t in block.asset_data.tags]}
        entries.append(info)
    report['assets'][group] = entries
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type != 'FILE_BROWSER':
            continue
        space = area.spaces.active
        if space.browse_mode != 'ASSETS':
            continue
        params = space.params
        report['browser'].append({'screen': screen.name, 'width': area.width, 'height': area.height,
            'asset_library_ref': params.asset_library_reference,
            'catalog_id': params.catalog_id,
            'filter_search': params.filter_search,
            'directory': str(params.directory)})
kit = bpy.context.preferences.addons.get('blenderkit')
if kit:
    prefs = kit.preferences
    report['blenderkit'] = {p.identifier: getattr(prefs, p.identifier) for p in prefs.bl_rna.properties
                            if p.type == 'STRING' and any(k in p.identifier.lower() for k in ('dir', 'path'))}
folder.mkdir(parents=True, exist_ok=True)
(folder / 'live_inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ASSET_LIBRARY_INVENTORY_SAVED', {k: len(v) for k, v in report['assets'].items()})
