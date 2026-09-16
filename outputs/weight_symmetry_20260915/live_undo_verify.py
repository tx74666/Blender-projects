"""Exercise the real window's Undo/Redo, verifying all weights at each step."""
import bpy
import json
from pathlib import Path
from character_designer import weight_surface as surface

root = Path(r'D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915')
prepared = json.loads((root / 'live_prepared.json').read_text(encoding='utf-8'))
applied = json.loads((root / 'live_applied.json').read_text(encoding='utf-8'))

def groups_now():
    return [dict(name=s.name, index=s.index, lock_weight=s.lock_weight,
                 weights=[list(w) for w in s.weights])
            for s in surface.ws._capture_vertex_groups(bpy.data.objects['Cosha'])]

def fingerprint_now():
    return surface._fingerprint(bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig'])

assert groups_now() == applied['group_after'], 'Live state differs from applied result'
assert fingerprint_now() == prepared['geometry_fingerprint']
view = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in view.regions if r.type == 'WINDOW')
report = dict(undo=False, redo=False, geometry_unchanged=True)
with bpy.context.temp_override(area=view, region=region):
    assert bpy.ops.ed.undo.poll(), 'Undo unavailable in real window'
    result = bpy.ops.ed.undo()
assert result == {'FINISHED'}, result
report['undo'] = groups_now() == prepared['group_snapshot']
report['undo_equals_applied'] = groups_now() == applied['group_after']
report['undo_changed_groups'] = [s['name'] for s, p in zip(groups_now(), prepared['group_snapshot']) if s != p]
report['undo_geometry_unchanged'] = fingerprint_now() == prepared['geometry_fingerprint']
(root / 'live_undo_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
# Reapply only through Blender's corresponding Redo, regardless of comparison outcome.
view = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in view.regions if r.type == 'WINDOW')
with bpy.context.temp_override(area=view, region=region):
    assert bpy.ops.ed.redo.poll(), 'Redo unavailable; backed-up pre-edit state retained'
    result = bpy.ops.ed.redo()
assert result == {'FINISHED'}, result
report['redo'] = groups_now() == applied['group_after']
report['redo_geometry_unchanged'] = fingerprint_now() == prepared['geometry_fingerprint']
(root / 'live_undo_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert report['undo'] and report['redo'] and report['undo_geometry_unchanged'] and report['redo_geometry_unchanged'], report
bpy.data.objects['Cosha'].vertex_groups.active_index = prepared['original_group_index']
print('LIVE_UNDO_REDO_VERIFIED', report)
