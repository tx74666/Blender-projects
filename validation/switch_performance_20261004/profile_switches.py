"""Isolated current saved Cosha switch profile; never writes the artist file."""
import ast
import cProfile
import json
import pstats
import sys
import time
import traceback
from pathlib import Path

import bpy

FOLDER = Path(__file__).resolve().parent
PREVIOUS = FOLDER.parent / 'fk_ik_display_20261004' / 'measure_extra_solve.py'
# Reuse the verified definition-only readers, without running its benchmark.
scope = {'__file__': str(PREVIOUS)}
tree = ast.parse(PREVIOUS.read_text(encoding='utf-8'))
nodes = tree.body[:next(i for i, node in enumerate(tree.body)
                       if isinstance(node, ast.FunctionDef) and node.name == 'run')]
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(PREVIOUS), 'exec'), scope)
for name in ('character_designer', 'limb_ik', 'limb_ik_fk', 'limb_ik_fk_batch',
             'body_original_mode', 'forearm_twist', 'control_pose_assets',
             'body_setup_removal', 'states', 'check_preserved', 'file_hash',
             'assert_pose_surface'):
    globals()[name] = scope[name]
ARTIST = FOLDER.parents[1] / 'X.blend'
REPORT = FOLDER / 'profile_switches.json'


def profile_call(label, operation, measured):
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    try:
        result = operation()
    finally:
        profiler.disable()
        seconds = time.perf_counter() - started
    stats = pstats.Stats(profiler)
    rows = [{'file': Path(filename).name, 'line': line, 'function': name,
             'primitive_calls': primitive, 'calls': calls,
             'self_seconds': self_time, 'cumulative_seconds': cumulative}
            for (filename, line, name), (primitive, calls, self_time, cumulative, _callers)
            in stats.stats.items()]
    rows.sort(key=lambda row: row['cumulative_seconds'], reverse=True)
    measured.append({'label': label, 'seconds': seconds, 'profile': rows})
    print(label, round(seconds, 4), flush=True)
    return result


def run():
    if not bpy.app.background:
        raise RuntimeError('Isolated background only.')
    before_hash = file_hash(ARTIST)
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(ARTIST), load_ui=False, use_scripts=False)
    rig = bpy.data.objects['CoshaRig']
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    limb_ik._settings(bpy.context).armature = rig
    limb_ik_fk._update(bpy.context, rig)
    if body_original_mode.active(rig) or limb_ik_fk_batch.mode_for_keys(rig) != 'FK':
        raise RuntimeError('Expected the saved ordinary FK baseline.')
    rest_names = tuple(control_pose_assets.native_rest(rig))
    surfaces = body_setup_removal._bound_surfaces(bpy.context, rig)
    before = states(rig, set(), set(), rest_names)
    checkpoint = limb_ik_fk_batch._checkpoint(bpy.context, rig, None)
    facts = {'passed': False, 'runtime': bpy.app.version_string,
             'version': list(character_designer.bl_info['version']),
             'source': character_designer.__file__, 'artist_sha_before': before_hash,
             'scope': 'background cProfile, includes profiler overhead; excludes reset/external proof; no GUI/Undo measurement',
             'samples': [], 'protection': [], 'threads_requested': 1}
    def reset():
        with forearm_twist.defer_runtime(bpy.context, flush_on_exit=False):
            limb_ik_fk_batch._rollback(bpy.context, rig, checkpoint, set())
        facts['protection'].append(assert_pose_surface(rig, before, surfaces, rest_names))
    try:
        # One warmup and two profiled rounds per operation. Every round starts
        # from the same exact checkpoint outside its timing interval.
        for index in range(3):
            reset()
            sample = []
            profile_call('IK', lambda: limb_ik_fk_batch.switch_all(bpy.context, rig, 'IK', keyframe=False), sample)
            profile_call('FK', lambda: limb_ik_fk_batch.switch_all(bpy.context, rig, 'FK', keyframe=False), sample)
            facts['protection'].append(assert_pose_surface(rig, before, surfaces, rest_names))
            reset()
            profile_call('Original', lambda: body_original_mode.enter(bpy.context, rig), sample)
            profile_call('Controls_no_edit', lambda: body_original_mode.leave(bpy.context, rig), sample)
            facts['protection'].append(assert_pose_surface(rig, before, surfaces, rest_names))
            facts['samples'].append({'round': index, 'warmup': index == 0, 'operations': sample})
        reset()
        check_preserved(facts, 'final', rig, before, surfaces, set(), set(), rest_names)
        facts['artist_sha_after'] = file_hash(ARTIST)
        if facts['artist_sha_after'] != before_hash:
            raise RuntimeError('Artist file changed during isolated profiling.')
        facts['passed'] = True
    except Exception:
        facts['error'] = traceback.format_exc()
        raise
    finally:
        REPORT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')


run()
