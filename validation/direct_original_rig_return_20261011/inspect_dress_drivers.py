import bpy
import json
from pathlib import Path

rig = bpy.data.objects['CoshaRig']
rows = []
for pb in rig.pose.bones:
    for con in pb.constraints:
        if con.name != 'Skirt physics delta':
            continue
        path = con.path_from_id('influence')
        for f in rig.animation_data.drivers:
            if f.data_path != path:
                continue
            mods = []
            for m in f.modifiers:
                attrs = ('type', 'mode', 'poly_order', 'mute', 'use_additive', 'use_restricted_range',
                         'frame_start', 'frame_end', 'blend_in', 'blend_out', 'use_influence', 'influence')
                mods.append({k: getattr(m, k) for k in attrs if hasattr(m, k)} |
                            {'coefficients': list(m.coefficients) if hasattr(m, 'coefficients') else None})
            rows.append({'bone': pb.name, 'path': path, 'index': f.array_index, 'extrapolation': f.extrapolation,
                         'mute': f.mute, 'driver_type': f.driver.type, 'expression': f.driver.expression,
                         'modifiers': mods, 'keyframe_count': len(f.keyframe_points), 'samples': len(f.sampled_points),
                         'keys': [{'co': list(k.co), 'left': list(k.handle_left), 'right': list(k.handle_right),
                                   'left_type': k.handle_left_type, 'right_type': k.handle_right_type,
                                   'interpolation': k.interpolation} for k in f.keyframe_points]})
folder = Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011')
(folder / 'dress_driver_inventory.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print(json.dumps({'count': len(rows), 'first': rows[0] if rows else None}))
