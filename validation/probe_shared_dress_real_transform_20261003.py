"""Inspect the saved X attachment scale in an isolated unsaved process."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path[:0] = [str(ROOT / 'addons')]
import bpy
from mathutils import Matrix
import character_designer
from character_designer import skirt_rig as skirt, skirt_shared_rig as shared
from character_designer import body_original_mode as original

character_designer.register()
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend')
source, main = bpy.data.objects['Dress'], bpy.data.objects['CoshaRig']
old = source[skirt.RIG_KEY]
if original.active(main):
    original.leave(bpy.context, main)
bpy.context.view_layer.update()


def measure(matrix):
    linear = matrix.to_3x3()
    columns = [linear.col[index] for index in range(3)]
    lengths = [column.length for column in columns]
    normalized = Matrix.Identity(3)
    for index, column in enumerate(columns):
        normalized.col[index] = column.normalized()
    return {'matrix': [list(row) for row in matrix], 'determinant': linear.determinant(),
            'column_lengths': lengths, 'uniform_spread': max(lengths) - min(lengths),
            'normalized_orthogonal_error': shared._difference(normalized.transposed() @ normalized, Matrix.Identity(3))}


report = {'main_world': measure(main.matrix_world), 'old_world': measure(old.matrix_world),
          'old_basis': measure(old.matrix_basis), 'old_parent_inverse': measure(old.matrix_parent_inverse),
          'main_anchor_rest': measure(main.data.bones[old.parent_bone].matrix_local),
          'main_anchor_pose': measure(main.pose.bones[old.parent_bone].matrix),
          'main_scale': list(main.scale), 'old_scale': list(old.scale)}


def inspect(matrix):
    report['migration_transform'] = measure(matrix)
    return False


try:
    with patch.object(shared, '_rigid', side_effect=inspect):
        shared.preflight(bpy.context, source, main)
except skirt.SkirtRigError as exc:
    report['preflight_message'] = str(exc)
print('SHARED_REAL_TRANSFORM', json.dumps(report), flush=True)
