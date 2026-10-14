"""Only inspect saved counts, preferences and small top-level cache inventories."""
import bpy
import json
import sys

inventory = []
for name, module in list(sys.modules.items()):
    if not name.startswith(('character_designer', 'random_realm_builder_exporter', 'blender_mcp')):
        continue
    for key, value in list(vars(module).items()):
        if any(token in key.lower() for token in ('cache', 'worker', 'process', 'snapshot', 'job', 'runtime')) and isinstance(value, (dict, list, tuple, set)):
            inventory.append({'module': name, 'name': key, 'entries': len(value), 'shallow_bytes': sys.getsizeof(value)})
report = {'schema': 'x.memory.idle-inventory/1',
          'undo': {k: getattr(bpy.context.preferences.edit, k, None) for k in ('undo_steps', 'undo_memory_limit', 'use_global_undo')},
          'caches': sorted(inventory, key=lambda x: x['shallow_bytes'], reverse=True),
          'handlers': {k: [{'module': getattr(f, '__module__', ''), 'name': getattr(f, '__name__', str(type(f)))} for f in getattr(bpy.app.handlers, k)] for k in ('load_post', 'undo_post', 'redo_post', 'depsgraph_update_post', 'frame_change_pre', 'frame_change_post')},
          'scenes': [{'name': s.name, 'sequence_editor_exists': s.sequence_editor is not None} for s in bpy.data.scenes],
          'dirty': bpy.data.is_dirty}
print(json.dumps(report, ensure_ascii=True))
