"""Read only Blender metadata; do not evaluate meshes or load image pixels."""
import bpy
import json
import os
import sys

prefs = bpy.context.preferences
images = []
for image in bpy.data.images:
    size = list(image.size)
    images.append({"name": image.name, "size": size, "channels": image.channels,
                   "float": image.is_float, "has_data": image.has_data,
                   "users": image.users, "packed": bool(image.packed_file),
                   "estimated_uncompressed_mb": round(size[0] * size[1] * max(1, image.channels) * (4 if image.is_float else 1) / 1048576, 3)})
objects = []
for obj in bpy.data.objects:
    row = {"name": obj.name, "type": obj.type, "users": obj.users,
           "modifiers": [{"name": m.name, "type": m.type, "viewport": m.show_viewport,
                          "levels": getattr(m, "levels", None)} for m in obj.modifiers]}
    if obj.type == 'MESH':
        row.update(vertices=len(obj.data.vertices), polygons=len(obj.data.polygons),
                   shape_keys=len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0)
    if obj.type == 'ARMATURE':
        row['bones'] = len(obj.data.bones)
    objects.append(row)
modules = {}
for name, module in list(sys.modules.items()):
    if name in ('character_designer', 'random_realm_builder_exporter', 'blender_mcp', 'blender_mcp_addon'):
        modules[name] = {"file": getattr(module, '__file__', None),
                         "version": getattr(module, 'bl_info', {}).get('version')}
report = {"schema": "x.memory.readonly/1", "pid": os.getpid(),
          "blender": bpy.app.version_string, "filepath": bpy.data.filepath,
          "dirty": bpy.data.is_dirty, "mode": bpy.context.mode,
          "frame": bpy.context.scene.frame_current,
          "scene_names": [s.name for s in bpy.data.scenes],
          "counts": {k: len(getattr(bpy.data, k)) for k in ('objects', 'meshes', 'actions', 'materials', 'images', 'armatures', 'collections', 'node_groups')},
          "preferences": {k: getattr(prefs.system, k, None) for k in ('undo_steps', 'undo_memory_limit', 'use_global_undo', 'memory_cache_limit', 'texture_time_out', 'texture_collection_rate', 'console_scrollback')},
          "enabled_addons": list(prefs.addons.keys()), "modules": modules,
          "images": images, "objects": objects,
          "persistent_data": bpy.context.scene.render.use_persistent_data,
          "simplify": bpy.context.scene.render.use_simplify}
print(json.dumps(report, ensure_ascii=True))
