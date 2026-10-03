"""Disposable native Spline IK stability measurements; no scene saving."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path[:0] = [str(ROOT / 'addons'), str(ROOT / 'tests')]
import bpy
import character_designer
from character_designer import skirt_rig as service, skirt_shared_rig as shared
import test_skirt_shared_rig_blender as tests

character_designer.register()
source, old, main, record = tests.fixture()
before_geometry = tests.world_vertices(source)
before_pose = tests.world_pose(old)
before_cage = tests.world_cage(source, record)
before_body = tests.rest_state(main)
report = {'samples': []}

def sample(label):
    geometry = tests.world_vertices(source)
    pose = tests.world_pose(old)
    cage = tests.world_cage(source, record)
    errors = [(name, tests.matrix_error(before_pose[name], pose[name])) for name in before_pose]
    report['samples'].append({'label': label, 'geometry_error': tests.geometry_error(before_geometry, geometry),
                              'bone_errors': sorted(errors, key=lambda item: item[1], reverse=True)[:5],
                              'cage_error': max(tests.geometry_error(before_cage[name], cage[name]) for name in cage),
                              'body_rest_changed': tests.rest_state(main) != before_body})

sample('initial')
for index in range(3):
    bpy.context.view_layer.update()
    sample('view_layer_update_' + str(index))
service._activate(bpy.context, main, 'EDIT')
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
sample('unchanged_main_edit_roundtrip')
old.update_tag(refresh={'OBJECT'})
bpy.context.view_layer.update()
sample('old_rig_update_tag')
frame = bpy.context.scene.frame_current
bpy.context.scene.frame_set(frame)
bpy.context.view_layer.update()
sample('unchanged_frame_set')

source, old, main, record = tests.fixture()
old_pose = tests.world_pose(old)
before_geometry = tests.world_vertices(source)
def inspect(context, plan):
    context.view_layer.update()
    new_pose = tests.world_pose(main, plan['names'])
    reevaluated = tests.world_pose(old)
    report['migration'] = {'geometry_error': tests.geometry_error(before_geometry, tests.world_vertices(source)),
                           'new_vs_saved': sorted([(name, tests.matrix_error(old_pose[name], new_pose[name]))
                                                   for name in plan['names']], key=lambda item: item[1], reverse=True)[:5],
                           'old_reevaluated_vs_saved': sorted([(name, tests.matrix_error(old_pose[name], reevaluated[name]))
                                                              for name in plan['names']], key=lambda item: item[1], reverse=True)[:5],
                           'spline_bindings': []}
    for chain in record['chains'][:2]:
        name = chain['manual'][-1]
        left = next(con for con in old.pose.bones[name].constraints if con.type == 'SPLINE_IK')
        right = next(con for con in main.pose.bones[name].constraints if con.type == 'SPLINE_IK')
        report['migration']['spline_bindings'].append({'bone': name,
            'old': list(getattr(left, 'joint_bindings', ())), 'new': list(getattr(right, 'joint_bindings', ())),
            'old_original_scale': getattr(left, 'use_original_scale', None),
            'new_original_scale': getattr(right, 'use_original_scale', None)})
    raise RuntimeError('stability diagnostic rollback')
try:
    with patch.object(shared, '_validate_result', side_effect=inspect):
        service.unify_skirt(bpy.context, source, main)
except Exception as exc:
    report['migration_error'] = str(exc)
print('SHARED_STABILITY', json.dumps(report), flush=True)
