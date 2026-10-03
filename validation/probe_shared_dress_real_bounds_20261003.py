"""Measure saved Cosha's similarity and solver precision without saving."""
import json
import math
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path[:0] = [str(ROOT / 'addons'), str(ROOT / 'tests')]
import bpy
from mathutils import Matrix, Vector
import character_designer
from character_designer import skirt_rig as skirt, skirt_shared_rig as shared
from character_designer import body_original_mode as original
import test_skirt_shared_rig_blender as tests

character_designer.register()
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend')
source, main = bpy.data.objects['Dress'], bpy.data.objects['CoshaRig']
old = source[skirt.RIG_KEY]
if original.active(main):
    original.leave(bpy.context, main)
bpy.context.view_layer.update()
report = {}
record = skirt.read_record(source)
names = set(old.data.bones.keys())
controls, deform, mechanism = skirt._bone_collection_layout(record)
geometry = tests.world_vertices(source)
cage = tests.world_cage(source, record)
frames = {name: shared._bone_frame(old, name) for name in names}
mesh = tests.meshes_content()
main_channels = tests.pose_channels(main)
old_channels = tests.pose_channels(old)
old_frame, old_subframe = bpy.context.scene.frame_current, bpy.context.scene.frame_subframe


def errors(before, after, names, unit_scale=1.0):
    result = {'position': (0.0, ''), 'axis_radians': (0.0, ''), 'scale_ratio': (0.0, '')}
    for name in names:
        values = shared._frame_error(before[name], after[name], unit_scale)
        for key, value in zip(result, values):
            if value > result[key][0]:
                result[key] = value, name
    return result


def inspect(context, plan):
    context.view_layer.update()
    newframes = {name: shared._bone_frame(main, name) for name in names}
    reevaluated = {name: shared._bone_frame(old, name) for name in names}
    actual_cage = tests.world_cage(source, record)
    report.update(unit_scale=plan['unit_scale'], extent=plan['extent'],
        source_geometry=tests.geometry_error(geometry, tests.world_vertices(source)),
        cage=max(tests.geometry_error(cage[name], actual_cage[name]) for name in cage),
        controls=errors(frames, newframes, controls, plan['unit_scale']),
        solver=errors(frames, newframes, deform | mechanism, plan['unit_scale']),
        old_reevaluated=errors(frames, reevaluated, names),
        meshes_exact=tests.meshes_content() == mesh,
        main_channels_exact=tests.pose_channels(main, main_channels) == main_channels)
    report['source_relative'] = report['source_geometry'] / plan['extent']
    # The old source still has its original object frame saved by preflight.
    # Temporarily restore that one routing to measure the legacy solver against
    # exactly the same re-evaluated wire inputs, then restore the candidate.
    current = shared._state(source)
    modifier = source.modifiers[record['modifier']]
    state = next(state for obj, state in plan['children'] if obj == source)
    try:
        shared._restore_object(source, state)
        modifier.object = old
        context.view_layer.update()
        report['old_source_reevaluated'] = tests.geometry_error(geometry, tests.world_vertices(source))
    finally:
        modifier.object = main
        shared._restore_object(source, current)
        context.view_layer.update()
    report['bone_channels_mapped_exact'] = all(
        tests.pose_channels(main, (name,))[name] == tuple(
            tuple(Vector(value) * plan['unit_scale']) if index == 1 else value
            for index, value in enumerate(old_channels[name])) for name in names)
    raise RuntimeError('real precision diagnostic rollback')


try:
    with patch.object(shared, '_validate_result', side_effect=inspect):
        skirt.unify_skirt(bpy.context, source, main)
except skirt.SkirtRigError as exc:
    report['rollback_message'] = str(exc)
report['rollback_meshes_exact'] = tests.meshes_content() == mesh
report['frame_subframe_restored'] = (bpy.context.scene.frame_current == old_frame
                                   and bpy.context.scene.frame_subframe == old_subframe)
print('SHARED_REAL_BOUNDS', json.dumps(report), flush=True)
