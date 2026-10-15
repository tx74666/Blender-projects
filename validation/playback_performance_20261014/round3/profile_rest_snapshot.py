"""Isolated ABBA for one-call Rest snapshot reuse, with exact output witnesses."""
import argparse
import ast
import datetime
import json
import os
from pathlib import Path
import statistics
import sys
import time
import traceback

import bpy

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER.parent))
from profile_saved_forearm_display import Instrumentation, pin, witness


def frozen_functions(path, namespace, names):
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in names]
    assert {node.name for node in nodes} == set(names)
    local = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace, local)
    return {name: local[name] for name in names}


def main(args, report):
    assert bpy.app.background, 'Only a disposable background process is supported'
    sys.path.insert(0, str(Path(args.addons).resolve()))
    import character_designer as addon
    from character_designer import forearm_twist as runtime
    from character_designer import forearm_twist_math as geometry
    from character_designer import animation_worklist_target as target
    from character_designer import unity_animation as ua
    report.update(script=pin(__file__), blender=bpy.app.version_string,
                  metadata_version=list(addon.bl_info['version']))
    report['input_before'] = pin(args.input)
    report['artist_before'] = pin(args.artist)
    assert Path(args.input).resolve() != Path(args.artist).resolve()
    assert report['input_before']['sha256'] == report['artist_before']['sha256']
    report['candidate_sources'] = [pin(module.__file__) for module in (runtime, geometry, target, ua)]
    baseline = FOLDER / 'baseline_07740'
    report['baseline_sources'] = [pin(baseline / name) for name in
                                  ('animation_worklist_target.py', 'unity_animation.py',
                                   'forearm_twist.py', 'forearm_twist_math.py')]
    names = ('_rest_state', '_matches_rest_state', '_same_rest_bone', '_matches_saved_rest_state')
    current_ua = {name: getattr(ua, name) for name in names}
    old_ua = frozen_functions(baseline / 'unity_animation.py', ua.__dict__, names)
    current_proof = target._prove_motion_data
    old_proof = frozen_functions(baseline / 'animation_worklist_target.py',
                                 target.__dict__, ('_prove_motion_data',))['_prove_motion_data']
    math_names = ('blended_matrix', 'desired_vertex', 'corrected_vertex')
    current_math = {name: getattr(geometry, name) for name in math_names}
    old_math = frozen_functions(baseline / 'forearm_twist_math.py', geometry.__dict__, math_names)
    current_calculate = runtime._calculate_records
    old_calculate = frozen_functions(baseline / 'forearm_twist.py', runtime.__dict__,
                                     ('_calculate_records',))['_calculate_records']
    addon.register()
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.input).resolve()))
    scene = bpy.context.scene
    report['scene'] = scene.name
    report['actions'] = {obj.name: obj.animation_data.action.name for obj in scene.objects
                         if obj.animation_data and obj.animation_data.action}
    report['support'] = {obj.name: {side: len(record['vertices'])
                                    for side, record in runtime._records(obj).items()}
                         for obj in scene.objects if obj.type == 'MESH' and runtime.RECORD_KEY in obj}
    assert report['support'], 'No calibrated live Forearm output'
    frames = [2, 6, 10, 14, 18, 22, 26, 30] * 2
    report['frames'] = frames
    expected = None
    report['blocks'] = []
    try:
        for label in ('baseline_07740', 'rest_only', 'math_only', 'combined',
                      'combined', 'math_only', 'rest_only', 'baseline_07740'):
            use_rest = label in ('rest_only', 'combined')
            use_math = label in ('math_only', 'combined')
            for name, function in (current_ua if use_rest else old_ua).items():
                setattr(ua, name, function)
            target._prove_motion_data = current_proof if use_rest else old_proof
            for name, function in (current_math if use_math else old_math).items():
                setattr(geometry, name, function)
            runtime.corrected_vertex = geometry.corrected_vertex
            runtime._calculate_records = current_calculate if use_math else old_calculate
            runtime._CACHE.clear()
            runtime._OUTPUT_CACHE.clear()
            runtime.validation_cache.clear()
            target._compile_rest_record.cache_clear()
            instrumentation = Instrumentation(runtime)
            extras = []
            for module, functions in ((target, ('control_rest_view', '_prove_motion_data')),
                                       (ua, ('_rest_state', '_matches_rest_state',
                                             '_read_matched_rest_state', '_matches_current_rest_state'))):
                for name in functions:
                    original = getattr(module, name)
                    extras.append((module, name, original))
                    setattr(module, name, instrumentation.wrap(original, module.__name__ + '.' + name))
            try:
                for frame in (1, 3):
                    scene.frame_set(frame)
                    bpy.context.view_layer.update()
                instrumentation.reset()
                milliseconds, outputs = [], []
                for frame in frames:
                    before = time.perf_counter()
                    scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    milliseconds.append((time.perf_counter() - before) * 1000)
                    outputs.append(witness(runtime, scene))
                errors = dict(runtime._ERRORS)
                assert not errors, errors
                assert instrumentation.calls[target.__name__ + '._prove_motion_data'] > 0
                assert instrumentation.calls[ua.__name__ + '._rest_state'] > 0
                if expected is None:
                    expected = outputs
                equal = outputs == expected
                assert equal, 'Managed key coordinates/state, pose, display or records differ'
                block = {'label': label, 'milliseconds': milliseconds,
                         'median_ms': statistics.median(milliseconds),
                         'calls': dict(instrumentation.calls),
                         'nested_seconds': dict(instrumentation.seconds),
                         'outputs_equal_to_baseline': equal, 'errors': errors}
                report['blocks'].append(block)
                print('BLOCK', label, round(block['median_ms'], 3), flush=True)
            finally:
                for module, name, function in reversed(extras):
                    setattr(module, name, function)
                instrumentation.restore()
    finally:
        for name, function in current_ua.items():
            setattr(ua, name, function)
        target._prove_motion_data = current_proof
        for name, function in current_math.items():
            setattr(geometry, name, function)
        runtime.corrected_vertex = current_math['corrected_vertex']
        runtime._calculate_records = current_calculate
    report['artist_after'] = pin(args.artist)
    report['input_after'] = pin(args.input)
    assert report['artist_after'] == report['artist_before']
    assert report['input_after'] == report['input_before']
    report['limits'] = ['Single saved snapshot, one private single-thread process, shared system load.',
                        'Background evaluation is not viewport FPS.',
                        'Nested component timings overlap and cannot be summed.',
                        'Exact observed managed output/pose/display equivalence; no all-world equivalence.',
                        'No live artist operation, refresh or scene save.']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for argument in ('addons', 'input', 'artist', 'report'):
        parser.add_argument('--' + argument, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    report = {'schema': 'x.playback-rest-and-blend-abba/1', 'completed': False,
              'pid': os.getpid(),
              'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'model_and_reasoning_effort': 'unrecorded'}
    try:
        main(args, report)
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
