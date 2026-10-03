"""Disposable migration diagnostic; never opens or saves the artist scene."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path[:0] = [str(ROOT / 'addons'), str(ROOT / 'tests')]
import bpy
from mathutils import Vector
import character_designer
from character_designer import skirt_rig as service, skirt_shared_rig as shared
import test_skirt_shared_rig_blender as tests

character_designer.register()
source, old, main, record = tests.fixture()
curve = bpy.data.objects[record['cage'][0]]

def matrix(value):
    return [list(row) for row in value]

def snapshot():
    return {'curve_world': matrix(curve.matrix_world), 'curve_base': matrix(curve.matrix_basis),
            'curve_parent_inverse': matrix(curve.matrix_parent_inverse),
            'curve_vertices': tests.world_vertices(curve)[:8],
            'hooks': [{'object': mod.object.name, 'bone': mod.subtarget,
                       'inverse': matrix(mod.matrix_inverse), 'center': list(mod.center),
                       'indices': list(mod.vertex_indices)} for mod in curve.modifiers if mod.type == 'HOOK']}

before = snapshot()
report = {'before': before}
def inspect(context, plan):
    context.view_layer.update()
    report['after'] = snapshot()
    errors = [(name, tests.matrix_error(main.matrix_world @ main.pose.bones[name].matrix,
                                       old.matrix_world @ old.pose.bones[name].matrix)) for name in plan['names']]
    report['bone_errors'] = sorted(errors, key=lambda item: item[1], reverse=True)[:14]
    controls = record['controls']
    report['channels'] = {name: {'old': shared._body_channels(old)[name], 'new': shared._body_channels(main)[name]}
                          for name in (controls['waist'], controls['mid'], controls['hem'])}
    report['geometry_error'] = tests.geometry_error(before['curve_vertices'], report['after']['curve_vertices'])
    raise RuntimeError('diagnostic rollback')

with patch.object(shared, '_validate_result', side_effect=inspect):
    try:
        service.unify_skirt(bpy.context, source, main)
    except Exception as exc:
        report['error'] = str(exc)
report['rollback'] = snapshot()
report['rollback_curve_error'] = tests.geometry_error(before['curve_vertices'], report['rollback']['curve_vertices'])

def json_vector(value):
    if isinstance(value, Vector):
        return list(value)
    raise TypeError(f'Unsupported diagnostic JSON value: {type(value).__name__}')

print('SHARED_DIAGNOSTIC', json.dumps(report, ensure_ascii=False, default=json_vector), flush=True)
