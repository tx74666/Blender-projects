"""Read-only background comparison of the live before/after saved assets."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import bpy

ROOT = Path(r'D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915')
CANONICAL = Path(r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer')
prepared = json.loads((ROOT / 'live_prepared.json').read_text(encoding='utf-8'))
applied = json.loads((ROOT / 'live_applied.json').read_text(encoding='utf-8'))
before_file = Path(prepared['backup'])
after_file = Path(sys.argv[sys.argv.index('--') + 1])
assert before_file.resolve() != after_file.resolve()

package = types.ModuleType('cd_independent_live_audit')
package.__path__ = [str(CANONICAL)]
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location(package.__name__ + '.weight_surface', CANONICAL / 'weight_surface.py')
surface = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = surface
spec.loader.exec_module(surface)
ws = surface.ws

# Reuse only the previously reviewed invariant helper definitions, never its
# operator, save, or test execution body.
names = {'digest', 'scalar', 'properties', 'rna_settings', 'geometry', 'stable_scene_state'}
source = ast.parse((ROOT / 'validate_surface_character.py').read_text(encoding='utf-8'))
helpers = ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
exec(compile(helpers, 'reviewed_invariant_helpers', 'exec'), globals())

def serialized_groups(obj):
    return [dict(name=s.name, index=s.index, lock_weight=s.lock_weight,
                 weights=[list(w) for w in s.weights]) for s in ws._capture_vertex_groups(obj)]

def snapshot(path):
    initial_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    mesh, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
    tolerance = ws._automatic_tolerance(mesh)
    side = ws._bone_source_side(mesh, rig, 'upper_arm.L', 'upper_arm.R', tolerance)
    same, other, center = ws._classify_mesh_halves(mesh, side, tolerance)
    data = dict(path=str(path), sha256=initial_hash, groups=serialized_groups(mesh),
                invariants=stable_scene_state('Cosha'),
                fingerprint=surface._fingerprint(mesh, rig), source=list(same), center=list(center),
                deform=[b.name for b in rig.data.bones if b.use_deform],
                vertex_count=len(mesh.data.vertices), frame=bpy.context.scene.frame_current,
                active_group=mesh.vertex_groups.active.name if mesh.vertex_groups.active else None)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == initial_hash, 'File changed during read audit'
    return data

before, after = snapshot(before_file), snapshot(after_file)
bm = {g['name']:dict(g['weights']) for g in before['groups']}
am = {g['name']:dict(g['weights']) for g in after['groups']}
changed = {n:[i for i in sorted(bm.get(n,{}).keys() | am.get(n,{}).keys())
              if bm.get(n,{}).get(i) != am.get(n,{}).get(i)] for n in bm.keys() | am.keys()}
changed = {n:ids for n,ids in sorted(changed.items()) if ids}
changed_indices = sorted({i for ids in changed.values() for i in ids})
source, center = set(before['source']), set(before['center'])
deform = set(before['deform'])
invariant_differences = [n for n in before['invariants'].keys() | after['invariants'].keys()
                         if before['invariants'].get(n) != after['invariants'].get(n)]
report = dict(
    before={k:v for k,v in before.items() if k not in {'groups','source','center','deform'}},
    after={k:v for k,v in after.items() if k not in {'groups','source','center','deform'}},
    backup_matches_live_snapshot=before['groups'] == prepared['group_snapshot'],
    final_matches_live_after=after['groups'] == applied['group_after'],
    invariant_differences=sorted(invariant_differences),
    mesh_rest_fingerprint_unchanged=before['fingerprint'] == after['fingerprint'],
    source_half_unchanged=not (set(changed_indices) & source),
    center_unchanged=not (set(changed_indices) & center),
    nondeform_groups_unchanged=not (set(changed) - deform),
    outside_affected_unchanged=set(changed_indices) == set(prepared['affected']),
    changed_groups=changed, changed_vertices=changed_indices,
    changed_vertex_count=len(changed_indices),
    max_deform_budget_difference=max(abs(sum(bm.get(n,{}).get(i,0) for n in deform) -
                                       sum(am.get(n,{}).get(i,0) for n in deform))
                                     for i in range(before['vertex_count'])),
    hand_zero_weight_vertices_still_unchanged={str(i):all(bm[n].get(i) == am[n].get(i) for n in bm)
                                             for i in (3273,3396)},
)
report['passed'] = all(report[k] for k in ('backup_matches_live_snapshot', 'final_matches_live_after',
    'mesh_rest_fingerprint_unchanged','source_half_unchanged','center_unchanged',
    'nondeform_groups_unchanged','outside_affected_unchanged')) and not invariant_differences
(ROOT / 'live_independent_saved_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('INDEPENDENT_LIVE_SAVED_AUDIT', json.dumps({k:report[k] for k in ('passed','changed_vertex_count',
      'invariant_differences','source_half_unchanged','center_unchanged','max_deform_budget_difference')}))
assert report['passed'], 'See live_independent_saved_audit.json for differences'
