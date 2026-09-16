"""Verify final state, remove audit-only callbacks and save the existing artist file."""
import bpy
import json
from pathlib import Path
from character_designer import weight_surface as surface
root = Path(r'D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915')
prepared = json.loads((root / 'live_prepared.json').read_text(encoding='utf-8'))
applied = json.loads((root / 'live_applied.json').read_text(encoding='utf-8'))
events = json.loads((root / 'live_ui_undo_events.json').read_text(encoding='utf-8'))
obj = bpy.data.objects['Cosha']
groups = [dict(name=s.name,index=s.index,lock_weight=s.lock_weight,weights=[list(w) for w in s.weights]) for s in surface.ws._capture_vertex_groups(obj)]
assert groups == applied['group_after']
assert surface._fingerprint(obj,bpy.data.objects['CoshaRig']) == prepared['geometry_fingerprint']
assert any(e['kind'] == 'UNDO' and e['equals_before'] and e['geometry_unchanged'] for e in events)
assert events[-1]['kind'] == 'REDO' and events[-1]['equals_after'] and events[-1]['geometry_unchanged']
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
for handlers, name in [(bpy.app.handlers.undo_post, 'record_weight_ui_undo'), (bpy.app.handlers.redo_post, 'record_weight_ui_redo')]:
    for handler in list(handlers):
        if getattr(handler, '__name__', '') == name:
            handlers.remove(handler)
obj.vertex_groups.active_index = prepared['original_group_index']
assert obj.mode == prepared['original_mode'] == 'OBJECT'
bpy.context.area.type = 'VIEW_3D'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
report = dict(status='SAVED_AND_VERIFIED', path=bpy.data.filepath, backup=prepared['backup'], affected_vertices=len(applied['affected']), undo_restores_all_weights=True, redo_restores_all_weights=True, geometry_unchanged=True, group_after=applied['group_after'])
(root / 'live_final_verified.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('LIVE_FINAL_SAVED_AND_VERIFIED', bpy.data.filepath)
