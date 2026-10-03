"""Measure solver output separately from protected inputs in disposable scenes."""
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
from character_designer import skirt_rig as service, skirt_shared_rig as shared
import test_skirt_shared_rig_blender as tests


def extent(vertices):
    return max(max(v[axis] for v in vertices) - min(v[axis] for v in vertices) for axis in range(3))


def pose_errors(before, after, names):
    result = {'position': (0.0, ''), 'axis_radians': (0.0, ''), 'linear': (0.0, '')}
    for name in names:
        left, right = Matrix(before[name]), Matrix(after[name])
        position = max(abs(left[axis][3] - right[axis][3]) for axis in range(3))
        angles = []
        for axis in range(3):
            a, b = left.to_3x3().col[axis].normalized(), right.to_3x3().col[axis].normalized()
            angles.append(math.atan2(a.cross(b).length, max(-1.0, min(1.0, a.dot(b)))))
        linear = max(abs(left[row][column] - right[row][column]) for row in range(3) for column in range(3))
        for key, value in (('position', position), ('axis_radians', max(angles)), ('linear', linear)):
            if value > result[key][0]:
                result[key] = value, name
    return result


character_designer.register()
report = []
for case in ('unposed', 'posed', 'animated', 'physics_fixture', 'physics_animated', 'positive_similarity'):
    source, old, main, record = tests.fixture(posed=case not in {'unposed', 'physics_fixture', 'physics_animated'})
    if case in {'physics_fixture', 'physics_animated'}:
        service.remove_skirt(bpy.context, source)
        record = service.build_skirt(bpy.context, source, chain_count=4, segment_count=3, armature=main, shared=False)
        old = source[service.RIG_KEY]
    if case == 'positive_similarity':
        old.scale *= 0.9330823
        bpy.context.view_layer.update()
    scene = bpy.context.scene
    if case in {'animated', 'physics_animated'}:
        main.pose.bones['Hips'].keyframe_insert('rotation_euler', frame=1)
        main.pose.bones['Hips'].rotation_euler.z += 0.12
        main.pose.bones['Hips'].keyframe_insert('rotation_euler', frame=9)
        frames = ((1, 0.0), (4, 0.375), (9, 0.0))
    else:
        frames = ((scene.frame_current, scene.frame_subframe),)
    names = set(old.data.bones.keys())
    controls, deform, mechanism = service._bone_collection_layout(record)
    samples = {}
    for frame, subframe in frames:
        scene.frame_set(frame, subframe=subframe)
        samples[(frame, subframe)] = {'world': tests.world_vertices(source),
                                     'cage': tests.world_cage(source, record),
                                     'pose': tests.world_pose(old)}
    scene.frame_set(*frames[0][:1], subframe=frames[0][1])
    protected_mesh = tests.meshes_content()
    protected_main_channels = tests.pose_channels(main)
    protected_dress_channels = tests.pose_channels(old)
    row = {'case': case, 'samples': []}

    def inspect(context, plan):
        row['unit_scale'] = plan['unit_scale']
        row['protected_mesh_exact'] = tests.meshes_content() == protected_mesh
        row['protected_main_channels_exact'] = tests.pose_channels(main, protected_main_channels) == protected_main_channels
        row['protected_dress_channels_exact'] = all(
            tests.pose_channels(main, (name,))[name] == tuple(
                tuple(Vector(value) * plan['unit_scale']) if index == 1 else value
                for index, value in enumerate(protected_dress_channels[name])) for name in names)
        for frame, subframe in frames:
            scene.frame_set(frame, subframe=subframe)
            context.view_layer.update()
            baseline = samples[(frame, subframe)]
            actual = tests.world_vertices(source)
            new_pose, reevaluated_pose = tests.world_pose(main, names), tests.world_pose(old)
            cage = tests.world_cage(source, record)
            geometry_error = tests.geometry_error(baseline['world'], actual)
            sample = {'frame': frame, 'subframe': subframe,
                'extent': extent(baseline['world']), 'geometry': geometry_error,
                'geometry_relative': geometry_error / extent(baseline['world']),
                'cage': max(tests.geometry_error(baseline['cage'][name], cage[name]) for name in cage),
                'all': pose_errors(baseline['pose'], new_pose, names),
                'controls': pose_errors(baseline['pose'], new_pose, controls),
                'solver': pose_errors(baseline['pose'], new_pose, deform | mechanism),
                'old_reevaluated': pose_errors(baseline['pose'], reevaluated_pose, names)}
            current = shared._state(source)
            modifier = source.modifiers[record['modifier']]
            state = next(state for obj, state in plan['children'] if obj == source)
            try:
                shared._restore_object(source, state)
                modifier.object = old
                context.view_layer.update()
                sample['old_source_reevaluated'] = tests.geometry_error(baseline['world'], tests.world_vertices(source))
            finally:
                modifier.object = main
                shared._restore_object(source, current)
                context.view_layer.update()
            row['samples'].append(sample)
        scene.frame_set(plan['frame'], subframe=plan['subframe'])
        raise RuntimeError('bounded-solver diagnostic rollback')

    try:
        with patch.object(shared, '_validate_result', side_effect=inspect):
            service.unify_skirt(bpy.context, source, main)
    except service.SkirtRigError as exc:
        row['rollback_message'] = str(exc)
    row['rollback_mesh_exact'] = tests.meshes_content() == protected_mesh
    report.append(row)

print('SHARED_NUMERICAL_BOUNDS', json.dumps(report), flush=True)
