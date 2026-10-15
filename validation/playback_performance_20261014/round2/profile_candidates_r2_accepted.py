"""Compare the immutable Rest projection and matrix rows against shipped .39.

Single disposable process, staged and ABBA frame steps. No scene saves or
live artist inputs; preserve exact pose/output/display witnesses.
"""
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


def read_functions(path, namespace, names):
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == set(names)
    local = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace, local)
    return {name: local[name] for name in names}


def main(args, report):
    assert bpy.app.background, 'Use a disposable background Blender process'
    report['script'] = pin(__file__)
    sys.path.insert(0, str(Path(args.addons).resolve()))
    import character_designer as addon
    from character_designer import forearm_twist as runtime
    from character_designer import forearm_twist_math as geometry
    from character_designer import animation_worklist_target as target
    from character_designer import unity_animation as ua
    report['blender'] = bpy.app.version_string
    report['metadata_version'] = list(addon.bl_info['version'])
    report['input'] = before = pin(args.input)
    report['artist_before'] = pin(args.artist)
    assert before['sha256'] == report['artist_before']['sha256']
    assert Path(args.input).resolve() != Path(args.artist).resolve()
    report['sources'] = [pin(module.__file__) for module in (runtime, geometry, target, ua)]
    report['baseline_sources'] = [pin(FOLDER/'baseline_07739'/name) for name in
                                  ('forearm_twist.py','forearm_twist_math.py',
                                   'animation_worklist_target.py','unity_animation.py')]
    report['rest_matrix_candidate'] = pin(FOLDER/'rest_matrix_candidate.py')
    addon.register()
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.input).resolve()))
    scene = bpy.context.scene
    report['scene'] = scene.name
    report['actions'] = {obj.name: obj.animation_data.action.name for obj in scene.objects
                         if obj.animation_data and obj.animation_data.action}
    report['calibrated_meshes'] = calibrated = {obj.name: {
        side: {'enabled': record.get('enabled', True),
               'support_vertices': len(record['vertices'])}
        for side, record in runtime._records(obj).items()}
        for obj in scene.objects if obj.type == 'MESH' and runtime.RECORD_KEY in obj}
    assert any(record['enabled'] and record['support_vertices']
               for records in calibrated.values() for record in records.values()), \
        'No enabled calibrated support; the proposed fix is not exercised'
    report['frames'] = frames = [2, 6, 10, 14, 18, 22, 26, 30]
    original_math = {name:getattr(geometry,name) for name in
                     ('blended_matrix','desired_vertex','corrected_vertex')}
    baseline_math = read_functions(FOLDER/'baseline_07739/forearm_twist_math.py', geometry.__dict__, original_math)
    original_target = {name:getattr(target,name) for name in ('control_rest_view','validation_rest_view')}
    baseline_target = read_functions(FOLDER/'baseline_07739/animation_worklist_target.py', target.__dict__, original_target)
    original_calculate = runtime._calculate_records
    original_rest_matrix = ua._same_rest_bone
    candidate_rest_matrix = read_functions(FOLDER/'rest_matrix_candidate.py', ua.__dict__,
                                          ('_same_rest_bone',))['_same_rest_bone']
    baseline_calculate = read_functions(FOLDER/'baseline_07739/forearm_twist.py', runtime.__dict__,
                                       ('_calculate_records',))['_calculate_records']
    cases = report['cases'] = []
    expected = None
    try:
        labels = ['baseline_39','rest_only','matrix_only','combined',
                  'combined','matrix_only','rest_only','baseline_39']
        if args.include_rest_matrix:
            labels.extend(('combined_before_rest_matrix','full_candidate',
                           'full_candidate','combined_after_rest_matrix'))
        for label in labels:
            combined = label.startswith('combined') or label == 'full_candidate'
            use_rest = label == 'rest_only' or combined
            use_math = label == 'matrix_only' or combined
            ua._same_rest_bone = candidate_rest_matrix if label == 'full_candidate' else original_rest_matrix
            for name, function in (original_target if use_rest else baseline_target).items():
                setattr(target,name,function)
            for name, function in (original_math if use_math else baseline_math).items():
                setattr(geometry,name,function)
            runtime.corrected_vertex = geometry.corrected_vertex
            runtime._calculate_records = original_calculate if use_math else baseline_calculate
            runtime._CACHE.clear()
            runtime._OUTPUT_CACHE.clear()
            runtime.validation_cache.clear()
            target._compile_rest_record.cache_clear()
            instrument = Instrumentation(runtime)
            # Rest-entry timing is nested inside inventory; aggregate only.
            extra = []
            for name in ('_load','_load_rest_record','control_rest_view','_prove_motion_data'):
                function = getattr(target,name)
                extra.append((name,function))
                setattr(target,name,instrument.wrap(function,target.__name__+'.'+name))
            try:
                warm_calculations = [0]
                selected_corrected = runtime.corrected_vertex
                def counted_corrected(*args, **kwargs):
                    warm_calculations[0] += 1
                    return selected_corrected(*args, **kwargs)
                runtime.corrected_vertex = counted_corrected
                try:
                    for frame in (1,3):
                        scene.frame_set(frame)
                        bpy.context.view_layer.update()
                finally:
                    runtime.corrected_vertex = selected_corrected
                assert warm_calculations[0] > 0, 'Forearm correction did not execute'
                instrument.reset()
                elapsed, outputs = [], []
                for frame in frames:
                    start = time.perf_counter()
                    scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    elapsed.append((time.perf_counter()-start)*1000)
                    outputs.append(witness(runtime,scene))
                errors = dict(runtime._ERRORS)
                assert not errors, errors
                assert instrument.calls[target.__name__+'.control_rest_view'] > 0, \
                    'Worklist control Rest path did not execute'
                loader = '_load_rest_record' if use_rest else '_load'
                assert instrument.calls[target.__name__+'.'+loader] > 0, \
                    'Expected Worklist record loader did not execute'
                assert instrument.calls[target.__name__+'._prove_motion_data'] > 0, \
                    'Fresh native Rest proof did not execute'
                if expected is None:
                    expected = outputs
                same = outputs == expected
                assert same, 'Pose/managed output/collection/display changed'
                row = {'label':label,'milliseconds':elapsed,'median_ms':statistics.median(elapsed),
                       'calls':dict(instrument.calls),'nested_seconds':dict(instrument.seconds),
                       'outputs_equal_to_baseline':same,'errors':errors,
                       'warm_correction_calls':warm_calculations[0],
                       'projection_cache':target._compile_rest_record.cache_info()._asdict(),
                       'timing_note':'Nested component times overlap; do not add them.'}
                cases.append(row)
                print('CASE',label,round(row['median_ms'],3),flush=True)
            finally:
                for name,function in reversed(extra):
                    setattr(target,name,function)
                instrument.restore()
    finally:
        for name,function in original_target.items():
            setattr(target,name,function)
        for name,function in original_math.items():
            setattr(geometry,name,function)
        runtime.corrected_vertex = original_math['corrected_vertex']
        runtime._calculate_records = original_calculate
        ua._same_rest_bone = original_rest_matrix
    if args.probe_weight_reuse:
        sys.path.insert(0, str(FOLDER))
        from weight_reuse_probe import probe
        report['weight_probe_source'] = pin(FOLDER/'weight_reuse_probe.py')
        report['weight_reuse'] = probe(runtime, geometry, scene)
    report['input_after'] = pin(args.input)
    report['artist_after'] = pin(args.artist)
    assert report['input_after'] == before
    report['artist_disk_unchanged'] = report['artist_before'] == report['artist_after']
    report['limits'] = ['Background frame-step evaluation is not viewport FPS.',
                        'One saved snapshot, one thread, small warm samples, shared system load.',
                        'Exact observed managed output/pose/display equivalence, not all-world/model equality.',
                        'No live artist refresh or scene save; unsaved changes excluded.']
    report['no_scene_save'] = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input','artist','addons','report'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--include-rest-matrix',action='store_true')
    parser.add_argument('--probe-weight-reuse',action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema':'x.playback-remaining-cost-comparison/1','completed':False,'pid':os.getpid(),
              'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'model_and_reasoning_effort':'unrecorded'}
    try:
        main(args,report)
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
