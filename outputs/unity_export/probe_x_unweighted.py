"""Check whether the two unweighted FBX points already exist in saved X."""
import json
from pathlib import Path
import bpy

out = Path(__file__).resolve().parent
manifest = json.loads((out / 'Cosha' / 'Cosha.cdesigner.json').read_text(encoding='utf8'))
bone_names = set(manifest['rigs']['CoshaRig'])
obj = bpy.data.objects['Cosha']
groups = {group.index for group in obj.vertex_groups if group.name in bone_names}
def unweighted(mesh):
    return [{'index': v.index, 'coordinate': list(v.co)} for v in mesh.vertices
            if not any(g.group in groups and g.weight > 1e-7 for g in v.groups)]
base = unweighted(obj.data)
for mod in obj.modifiers:
    if mod.type == 'ARMATURE':
        mod.show_viewport = False
bpy.context.view_layer.update()
evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get())
try:
    record = {'source_base_vertex_count': len(obj.data.vertices), 'source_base_unweighted': base,
              'source_evaluated_vertex_count': len(mesh.vertices), 'source_evaluated_unweighted': unweighted(mesh)}
finally:
    evaluated.to_mesh_clear()
(out / 'x_source_unweighted.json').write_text(json.dumps(record, indent=2), encoding='utf8')
print('X_SOURCE_UNWEIGHTED', json.dumps(record), flush=True)
