"""Record actual UI undo events without invoking undo from a console operator."""
import bpy
import json
from pathlib import Path
from character_designer import weight_surface as surface
root = Path(r'D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915')
prepared = json.loads((root / 'live_prepared.json').read_text(encoding='utf-8'))
applied = json.loads((root / 'live_applied.json').read_text(encoding='utf-8'))
events = []

def record_weight_ui_event(kind):
    obj = bpy.data.objects['Cosha']
    groups = [dict(name=s.name, index=s.index, lock_weight=s.lock_weight,
                   weights=[list(w) for w in s.weights])
              for s in surface.ws._capture_vertex_groups(obj)]
    events.append(dict(kind=kind, equals_before=groups == prepared['group_snapshot'],
                       equals_after=groups == applied['group_after'],
                       geometry_unchanged=surface._fingerprint(obj, bpy.data.objects['CoshaRig']) == prepared['geometry_fingerprint']))
    (root / 'live_ui_undo_events.json').write_text(json.dumps(events, indent=2), encoding='utf-8')

def record_weight_ui_undo(*args):
    record_weight_ui_event('UNDO')

def record_weight_ui_redo(*args):
    record_weight_ui_event('REDO')

bpy.app.handlers.undo_post.append(record_weight_ui_undo)
bpy.app.handlers.redo_post.append(record_weight_ui_redo)
record_weight_ui_event('INITIAL')
bpy.context.area.type = 'VIEW_3D'
