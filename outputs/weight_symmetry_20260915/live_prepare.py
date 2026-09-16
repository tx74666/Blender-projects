"""Back up the paused live X scene and prepare a fresh weight-only plan."""
import bpy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from datetime import datetime

root = Path(r'D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915')
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
obj = bpy.data.objects['Cosha']
rig = bpy.data.objects['CoshaRig']
assert bpy.context.object is obj, 'Expected the artist-selected Cosha mesh'
original_mode = obj.mode
original_group = obj.vertex_groups.active_index
selected_names = [o.name for o in bpy.context.selected_objects]
if original_mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
backup = root / ('X_before_live_weight_mirror_' + datetime.now().strftime('%H%M%S_%f') + '.blend')
assert not backup.exists()
bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
assert Path(bpy.data.filepath).name == 'X.blend'

canonical = Path(r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer')
package = types.ModuleType('cd_live_weight_validation')
package.__path__ = [str(canonical)]
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location(package.__name__ + '.weight_surface', canonical / 'weight_surface.py')
surface = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = surface
spec.loader.exec_module(surface)
plan = surface.build_surface_plan_for_sources(bpy.context, obj, rig, ('upper_arm.L',))
report = dict(backup=str(backup), original_mode=original_mode,
              original_group_index=original_group, original_selected_objects=selected_names,
              geometry_fingerprint=plan.fingerprint, sampled=plan.sampled_count,
              affected=list(plan.affected_indices), max_distance=plan.max_sample_distance,
              group_snapshot=[dict(name=s.name,index=s.index,lock_weight=s.lock_weight,weights=s.weights)
                              for s in plan.group_snapshot])
(root / 'live_prepared.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('LIVE_BACKUP_AND_PREFLIGHT_READY', backup.name, len(plan.affected_indices))
bpy.ops.character_designer.refresh_addon()
