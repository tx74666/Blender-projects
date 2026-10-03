"""Isolated unsaved pose experiment; no addon registration or artist mutation."""
import hashlib
import json
import math
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector

OUT = Path(__file__).parent
SOURCE = OUT.parent.parent / 'X.blend'
before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
rig = bpy.data.objects['CoshaRig']
thigh = rig.pose.bones['thigh.L']
hips = rig.pose.bones['Hips']
old = thigh.matrix_basis.copy()
old_hips = hips.matrix_basis.copy()
# Only the owned experiment process hides subdivision to compare corresponding
# skinned cage vertices without changing source data or the artist window.
for name in ('Dress', 'Cosha'):
    for m in bpy.data.objects[name].modifiers:
        if m.type == 'SUBSURF':
            m.show_viewport = False
def sample(name):
    bpy.context.view_layer.update()
    obj = bpy.data.objects[name]
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [obj.matrix_world @ v.co for v in evaluated.data.vertices]
baseline = {name: sample(name) for name in ('Dress', 'Cosha')}
results = []
axis = thigh.bone.matrix_local.to_3x3().inverted() @ Vector((1,0,0))
for degrees in (30, 60):
    thigh.matrix_basis = old @ Quaternion(axis.normalized(), math.radians(degrees)).to_matrix().to_4x4()
    rig.update_tag(refresh={'OBJECT'})
    moved = {name: sample(name) for name in baseline}
    results.append({'degrees': degrees, 'max_vertex_displacement_m': {
        name: max((a-b).length for a,b in zip(baseline[name], moved[name])) for name in baseline},
        'hips_basis_error': max(abs(old_hips[r][c]-hips.matrix_basis[r][c]) for r in range(4) for c in range(4))})
thigh.matrix_basis = old
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
report = {'source': str(SOURCE), 'scope':'saved Original, physics influence 0, independent in-memory poses; no addon handlers or GUI input',
          'blender_version': bpy.app.version_string, 'source_sha256': before, 'source_unchanged':True,
          'scene_saved':False, 'results':results}
(OUT / 'leg_follow_probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('LEG_FOLLOW_PROBE', json.dumps(report), flush=True)
