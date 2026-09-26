import bpy
import json
import os
import sys
from pathlib import Path

def safe(obj, attr, default=None):
    try:
        return getattr(obj, attr)
    except Exception:
        return default

def mesh_info(mesh):
    keys = mesh.shape_keys
    key_count = len(keys.key_blocks) if keys else 0
    return {
        'name': mesh.name, 'users': mesh.users, 'fake_user': mesh.use_fake_user,
        'vertices': len(mesh.vertices), 'edges': len(mesh.edges),
        'polygons': len(mesh.polygons), 'loops': len(mesh.loops),
        'shape_keys': key_count,
        'shape_coordinates_bytes_estimate': len(mesh.vertices) * key_count * 12,
        'attributes': [{'name': a.name, 'domain': a.domain, 'type': a.data_type,
                        'length': len(a.data)} for a in mesh.attributes],
    }

meshes = [mesh_info(m) for m in bpy.data.meshes]
images = []
for im in bpy.data.images:
    # Image.size may decode a previously unloaded file. Inspect only loaded buffers.
    loaded = im.has_data
    size = list(im.size) if loaded else [0, 0]
    images.append({'name': im.name, 'users': im.users, 'fake_user': im.use_fake_user,
        'has_data': loaded, 'size': size, 'channels': im.channels if loaded else 0,
        'is_float': im.is_float if loaded else None, 'source': im.source,
        'pixel_buffer_bytes_estimate': size[0] * size[1] * im.channels * (4 if im.is_float else 1) if loaded else 0,
        'packed': bool(im.packed_file), 'filepath': im.filepath,
        'tile_count': len(im.tiles), 'dirty': im.is_dirty})

objects = []
for obj in bpy.data.objects:
    modifiers = []
    for mod in obj.modifiers:
        info = {'name': mod.name, 'type': mod.type,
                'viewport': mod.show_viewport, 'render': mod.show_render}
        for attr in ('levels', 'render_levels', 'sculpt_levels', 'total_levels',
                     'subdivision_type', 'show_only_control_edges'):
            value = safe(mod, attr)
            if value is not None:
                info[attr] = value
        modifiers.append(info)
    objects.append({'name': obj.name, 'type': obj.type, 'data': safe(obj.data, 'name'),
        'users': obj.users, 'hide_viewport': obj.hide_viewport,
        'hide_render': obj.hide_render, 'visible': obj.visible_get() if obj.name in bpy.context.view_layer.objects else False,
        'mode': obj.mode, 'modifiers': modifiers})

prefs = bpy.context.preferences
scene = bpy.context.scene
report = {
    'pid': os.getpid(), 'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
    'frame': scene.frame_current, 'workspace': bpy.context.workspace.name,
    'counts': {name: len(getattr(bpy.data, name)) for name in
               ('objects','meshes','materials','images','node_groups','actions','armatures','scenes')},
    'undo': {k: safe(prefs.edit, k) for k in ('use_global_undo','undo_steps','undo_memory_limit')},
    'render': {k: safe(scene.render,k) for k in ('engine','use_persistent_data','use_simplify','simplify_subdivision','simplify_subdivision_render')},
    'cycles': {k: safe(scene.cycles,k) for k in ('texture_limit','texture_limit_render','use_texture_limit')},
    'meshes': sorted(meshes, key=lambda m: (m['shape_coordinates_bytes_estimate'],m['loops']), reverse=True),
    'images': sorted(images, key=lambda im: im['pixel_buffer_bytes_estimate'], reverse=True),
    'objects': objects,
    'node_groups': [{'name':g.name,'users':g.users,'nodes':len(g.nodes),'fake_user':g.use_fake_user} for g in bpy.data.node_groups],
    'materials': [{'name':m.name,'users':m.users,'fake_user':m.use_fake_user,'nodes':len(m.node_tree.nodes) if m.node_tree else 0} for m in bpy.data.materials],
    'addons': list(prefs.addons.keys()),
    'handlers': {name: [str(f) for f in getattr(bpy.app.handlers,name)] for name in
                 ('depsgraph_update_post','frame_change_post','load_post','save_post')},
    'areas': [{'type':a.type,'ui_type':a.ui_type,
               'shading':safe(safe(a.spaces.active,'shading'),'type')}
              for a in bpy.context.screen.areas],
}
cache_summary = {}
for name, mod in list(sys.modules.items()):
    if not (('character_designer' in name or 'rr_helper' in name or 'rr_builder' in name) and mod):
        continue
    values = {}
    for attr in ('_SESSION', '_CACHE', '_OUTPUT_CACHE', '_TOPOLOGY', '_MIRROR', '_SELECTION_CACHE', 'PREVIEW_COLLECTIONS'):
        value = vars(mod).get(attr)
        if value is None:
            continue
        info = {'type': type(value).__name__, 'shallow_bytes': sys.getsizeof(value)}
        if hasattr(value, '__len__'):
            info['length'] = len(value)
        if isinstance(value, dict):
            info['keys'] = [str(k) for k in list(value)[:30]]
            history = value.get('history')
            if isinstance(history, (list,tuple)):
                info['history_length'] = len(history)
        values[attr] = info
    if values:
        cache_summary[name] = values
report['addon_caches'] = cache_summary
out = Path(r'D:\Blender\Projects\Character\X\outputs\memory_health')
out.mkdir(parents=True, exist_ok=True)
target = out / (Path(bpy.data.filepath).stem + '_live_memory.json')
target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('READ-ONLY MEMORY AUDIT SAVED:', str(target), report['counts'])
