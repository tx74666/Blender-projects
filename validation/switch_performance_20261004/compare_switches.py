"""Same-process paired comparison on the latest saved Cosha.

The frozen 0.75.1 function bodies and current source run against the same
native graph. Every condition starts from an exact checkpoint outside timing.
"""
import ast
import json
import statistics
import sys
import time
import traceback
from pathlib import Path

import bpy

FOLDER = Path(__file__).resolve().parent
PREVIOUS = FOLDER.parent / 'fk_ik_display_20261004' / 'measure_extra_solve.py'
scope = {'__file__': str(PREVIOUS)}
tree = ast.parse(PREVIOUS.read_text(encoding='utf-8'))
nodes = tree.body[:next(i for i, node in enumerate(tree.body)
                       if isinstance(node, ast.FunctionDef) and node.name == 'run')]
own_argv = sys.argv[:]
try:
    sys.argv = [str(PREVIOUS)]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(PREVIOUS), 'exec'), scope)
finally:
    sys.argv = own_argv
for name in ('character_designer', 'limb_ik', 'limb_ik_fk', 'limb_ik_fk_batch',
             'body_original_mode', 'forearm_twist', 'control_pose_assets',
             'body_setup_removal', 'states', 'check_preserved', 'file_hash',
             'assert_pose_surface'):
    globals()[name] = scope[name]
from character_designer import skirt_original_mode
ARTIST = FOLDER.parents[1] / 'X.blend'
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
REPORT = FOLDER / (ARGS[0] if ARGS else 'compare_switches.json')
REVERSE = len(ARGS) > 1 and ARGS[1] == 'reverse'
if REPORT.parent.resolve() != FOLDER.resolve() or REPORT.suffix != '.json':
    raise RuntimeError('Report must remain within this validation folder.')


def implementations(module):
    source = FOLDER / 'baseline' / 'character_designer' / (module.__name__.split('.')[-1] + '.py')
    parsed = ast.parse(source.read_text(encoding='utf-8'))
    functions = [node for node in parsed.body if isinstance(node, ast.FunctionDef)]
    old_scope = dict(module.__dict__)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), old_scope)
    names = [node.name for node in functions]
    return names, {name: getattr(module, name) for name in names}, old_scope


def run():
    if not bpy.app.background:
        raise RuntimeError('Background only; never benchmark the artist window.')
    artist_hash = file_hash(ARTIST)
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
    modules = [(module, *implementations(module))
               for module in (limb_ik_fk, body_original_mode, skirt_original_mode)]
    counter = {'timed': False, 'matcher_updates': 0, 'dress_resolves': 0}
    native_update = limb_ik_fk._update
    native_resolve = skirt_original_mode._resolve
    def count_update(*args, **kwargs):
        if counter['timed']:
            counter['matcher_updates'] += 1
        return native_update(*args, **kwargs)
    def count_resolve(*args, **kwargs):
        if counter['timed']:
            counter['dress_resolves'] += 1
        return native_resolve(*args, **kwargs)
    def choose(condition):
        for module, names, current, old_scope in modules:
            for name in names:
                setattr(module, name, old_scope[name] if condition == 'baseline_0.75.1' else current[name])
            if module is limb_ik_fk:
                old_scope['_update'] = count_update
            if module is skirt_original_mode:
                old_scope['_resolve'] = count_resolve
        limb_ik_fk._update = count_update
        skirt_original_mode._resolve = count_resolve
    facts = {'passed': False, 'runtime': bpy.app.version_string,
             'version': list(character_designer.bl_info['version']),
             'scope': 'same-process background function wall time, no profiler; excludes reset/external proof; no GUI/Undo measurement',
             'source': character_designer.__file__, 'baseline_version': [0, 75, 1],
             'threads_requested': 1, 'warmup_pairs': 1, 'measured_pairs': 5,
             'reverse_initial_order': REVERSE,
             'source_sha256': {module.__name__: file_hash(Path(module.__file__))
                               for module, *_rest in modules},
             'script_sha256': file_hash(Path(__file__)),
             'artist_sha_before': artist_hash, 'rounds': [], 'samples': [], 'protection': []}
    def reset():
        choose('optimized')
        with forearm_twist.defer_runtime(bpy.context, flush_on_exit=False):
            limb_ik_fk_batch._rollback(bpy.context, rig, checkpoint, set())
        facts['protection'].append(assert_pose_surface(rig, before, surfaces, rest_names))
    def timed(label, operation, pair, condition):
        counter.update(timed=True, matcher_updates=0, dress_resolves=0)
        started = time.perf_counter()
        try:
            result = operation()
        finally:
            seconds = time.perf_counter() - started
            counter['timed'] = False
        proof = assert_pose_surface(rig, before, surfaces, rest_names)
        record = {'pair': pair, 'warmup': pair == 0, 'condition': condition,
                  'operation': label, 'seconds': seconds,
                  'matcher_update_calls': counter['matcher_updates'],
                  'dress_resolve_calls': counter['dress_resolves'], **proof}
        facts['rounds'].append(record)
        if pair:
            facts['samples'].append(record)
        print(pair, condition, label, round(seconds, 5), flush=True)
        return result
    try:
        for pair in range(6):
            conditions = ('baseline_0.75.1', 'optimized') if (pair % 2 == 0) != REVERSE else ('optimized', 'baseline_0.75.1')
            for condition in conditions:
                reset()
                choose(condition)
                for mode in ('IK', 'FK'):
                    result = timed(mode, lambda: limb_ik_fk_batch.switch_all(bpy.context, rig, mode, keyframe=False), pair, condition)
                    if not result['changed'] or limb_ik_fk_batch.mode_for_keys(rig) != mode:
                        raise RuntimeError('Sample did not perform the intended switch.')
                reset()
                choose(condition)
                timed('Original', lambda: body_original_mode.enter(bpy.context, rig), pair, condition)
                timed('Controls_no_edit', lambda: body_original_mode.leave(bpy.context, rig), pair, condition)
                reset()
        check_preserved(facts, 'final', rig, before, surfaces, set(), set(), rest_names)
        facts['artist_sha_after'] = file_hash(ARTIST)
        if facts['artist_sha_after'] != artist_hash:
            raise RuntimeError('The artist file changed during isolated comparison.')
        facts['summary'] = {condition: {mode: {
            'count': len(rows), 'median_seconds': statistics.median([row['seconds'] for row in rows]),
            'minimum_seconds': min(row['seconds'] for row in rows),
            'maximum_seconds': max(row['seconds'] for row in rows),
            'matcher_update_calls': sorted({row['matcher_update_calls'] for row in rows}),
            'dress_resolve_calls': sorted({row['dress_resolve_calls'] for row in rows})}
            for mode in ('IK', 'FK', 'Original', 'Controls_no_edit')
            for rows in ([row for row in facts['samples'] if row['condition'] == condition and row['operation'] == mode],)}
            for condition in ('baseline_0.75.1', 'optimized')}
        facts['passed'] = True
        print('PAIRED_SWITCH_PASS', json.dumps(facts['summary']), flush=True)
    except Exception:
        facts['error'] = traceback.format_exc()
        raise
    finally:
        counter['timed'] = False
        for module, names, current, _old_scope in modules:
            for name in names:
                setattr(module, name, current[name])
        REPORT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')


run()
