import bpy, json
from pathlib import Path
from character_designer import skirt_rig
rig = bpy.data.objects['CoshaRig']
out = []
for pb in rig.pose.bones:
    for c in pb.constraints:
        if c.name == 'Skirt manual wire':
            wire = c.target
            out.append({'bone': pb.name, 'flags': {key: getattr(c, key) for key in ('use_chain_offset','use_original_scale','use_even_divisions','use_curve_radius','chain_count','y_scale_mode','xz_scale_mode')}, 'wire': wire.name, 'parent': wire.parent.name if wire.parent else None, 'basis': [list(r) for r in wire.matrix_basis], 'parent_inverse': [list(r) for r in wire.matrix_parent_inverse]})
records = []
for owner, source in rig.get(skirt_rig.SHARED_SOURCES_KEY, {}).items():
    rec = skirt_rig.read_record(source)
    records.append({'owner': owner, 'source': source.name, 'shared': rec.get('shared'), 'physics': rec.get('physics')})
Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011\manual_wire_inventory.json').write_text(json.dumps({'wires': out, 'records': records}, indent=2, default=str), encoding='utf-8')
print(json.dumps({'wires': out[:1], 'records': records}, default=str))
