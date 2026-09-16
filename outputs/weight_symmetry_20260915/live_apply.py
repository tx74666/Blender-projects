"""Apply the freshly backed-up live plan using the installed Undo operator."""
import bpy
import json
from pathlib import Path
import character_designer
from character_designer import weight_surface as surface

root = Path(r'D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915')
prepared = json.loads((root / 'live_prepared.json').read_text(encoding='utf-8'))
assert character_designer.bl_info['version'] == (0, 60, 0)
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
obj = bpy.data.objects['Cosha']
rig = bpy.data.objects['CoshaRig']
assert obj.mode == 'OBJECT' and bpy.context.object is obj
snapshot = surface.ws._capture_vertex_groups(obj)
serialized = [dict(name=s.name,index=s.index,lock_weight=s.lock_weight,weights=[list(w) for w in s.weights]) for s in snapshot]
assert serialized == prepared['group_snapshot'], 'Weights changed since backup; do not overwrite artist edits'
plan = surface.build_surface_plan_for_sources(bpy.context, obj, rig, ('upper_arm.L',))
assert plan.fingerprint == prepared['geometry_fingerprint'], 'Mesh/rest geometry changed since backup'
assert list(plan.affected_indices) == prepared['affected']
assert bpy.context.preferences.edit.use_global_undo, 'Global Undo is disabled; no weights applied'
obj.vertex_groups.active_index = obj.vertex_groups['upper_arm.L'].index
view = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in view.regions if r.type == 'WINDOW')
with bpy.context.temp_override(area=view, region=region):
    bpy.ops.ed.undo_push(message='Before verified upper-arm weight mirror')
    result = bpy.ops.character_designer.surface_weight_mirror('EXEC_DEFAULT', True)
assert result == {'FINISHED'}, result
obj = bpy.data.objects['Cosha']
surface._verify_surface_state(obj, plan)
obj.vertex_groups.active_index = prepared['original_group_index']
after = surface.ws._capture_vertex_groups(obj)
report = dict(version=character_designer.bl_info['version'], backup=prepared['backup'],
              affected=list(plan.affected_indices), source_names=plan.source_names,
              group_after=[dict(name=s.name,index=s.index,lock_weight=s.lock_weight,weights=s.weights) for s in after],
              geometry_fingerprint=surface._fingerprint(obj, rig), status='APPLIED',
              original_mode=prepared['original_mode'])
(root / 'live_applied.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('LIVE_UPPER_ARM_APPLIED', len(plan.affected_indices), 'Undo validation pending')
