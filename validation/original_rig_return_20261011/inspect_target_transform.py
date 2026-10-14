"""Compare raw Object channels with an inactive Scene's cached world matrix."""
import bpy
import json
from pathlib import Path
from mathutils import Matrix

rig = bpy.data.objects['CoshaRig']
rotation = (rig.rotation_quaternion.copy() if rig.rotation_mode == 'QUATERNION'
            else rig.rotation_euler.to_quaternion())
raw = Matrix.LocRotScale(rig.location, rotation, rig.scale)
result = {'active_scene': bpy.context.scene.name,
          'rig_scenes': [s.name for s in bpy.data.scenes if rig.name in s.objects],
          'parent': rig.parent.name if rig.parent else None,
          'object_constraint_count': len(rig.constraints),
          'raw_location': list(rig.location), 'raw_scale': list(rig.scale),
          'raw_rotation_mode': rig.rotation_mode,
          'raw_channel_matrix': [list(row) for row in raw],
          'cached_matrix_world': [list(row) for row in rig.matrix_world],
          'maximum_raw_cached_element_difference': max(abs(raw[r][c] - rig.matrix_world[r][c]) for r in range(4) for c in range(4)),
          'operation': 'Read only; no scene switch or depsgraph update requested'}
folder = Path(r'D:\Blender\Projects\Character\X\validation\original_rig_return_20261011')
(folder / 'inactive_scene_transform_check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
