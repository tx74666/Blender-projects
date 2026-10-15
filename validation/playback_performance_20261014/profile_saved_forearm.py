"""Frame-step comparison on a disposable saved-file copy; never save a scene.

Only the two changed preparation functions are exchanged in this process.
Samples are background evaluation time, not viewport playback FPS.
"""
import argparse
import ast
from array import array
from collections import Counter
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time
import traceback

import bpy


def pin(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
            size += len(block)
    return {'path': str(Path(path).resolve()), 'sha256': digest.hexdigest(), 'bytes': size}


def functions(path, namespace):
    names = {'_prepare_runtime_records', '_prepare_mirror'}
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    local = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace, local)
    return {name: local[name] for name in names}


class Instrumentation:
    def __init__(self, runtime):
        self.saved, self.handler_saved = [], []
        self.calls, self.seconds = Counter(), Counter()
        for module, names in (
            (runtime, ('update_runtime', '_calculate_object', '_prepare_runtime_records',
                       '_prepare_mirror', '_current_record', '_calculate_records',
                       '_weights', '_input_mix', '_topology')),
            (runtime.forearm_original_inventory, ('validate',)),
        ):
            for name in names:
                original = getattr(module, name)
                self.saved.append((module, name, original))
                setattr(module, name, self.wrap(original, module.__name__ + '.' + name))
        for group in ('depsgraph_update_post', 'frame_change_post'):
            handlers = getattr(bpy.app.handlers, group)
            for index, original in enumerate(list(handlers)):
                wrapped = self.wrap(original, group + ':' + original.__module__ + '.' + original.__name__)
                self.handler_saved.append((group, original, wrapped))
                handlers[index] = wrapped

    def wrap(self, function, name):
        @wraps(function)
        def measured(*args, **kwargs):
            start = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                self.calls[name] += 1
                self.seconds[name] += time.perf_counter() - start
        return measured

    def reset(self):
        self.calls.clear()
        self.seconds.clear()

    def restore(self):
        for group, original, wrapped in self.handler_saved:
            handlers = getattr(bpy.app.handlers, group)
            if wrapped in handlers:
                handlers[handlers.index(wrapped)] = original
        for module, name, original in reversed(self.saved):
            setattr(module, name, original)


def witness(runtime, scene):
    result = {}
    for obj in scene.objects:
        if obj.type == 'ARMATURE':
            result[obj.name] = {'pose': hashlib.sha256(repr(
                [(bone.name, tuple(v for row in bone.matrix for v in row))
                 for bone in obj.pose.bones]).encode()).hexdigest()}
        elif obj.type == 'MESH' and runtime.RECORD_KEY in obj:
            keys = {}
            for record in runtime._records(obj).values():
                key = obj.data.shape_keys.key_blocks[record['key']]
                coords = array('f', [0]) * (3 * len(key.data))
                key.data.foreach_get('co', coords)
                keys[key.name] = {'sha256': hashlib.sha256(coords.tobytes()).hexdigest(),
                                  'value': key.value, 'mute': key.mute}
            result[obj.name] = {'records': obj[runtime.RECORD_KEY], 'keys': keys}
    return result


def main(args, report):
    report['input'] = pin(args.input)
    report['artist_before'] = pin(args.artist)
    assert Path(args.input).resolve() != Path(args.artist).resolve()
    assert report['input']['sha256'] == report['artist_before']['sha256']
    sys.path.insert(0, str(Path(args.addons).resolve()))
    import character_designer as addon
    from character_designer import forearm_twist as runtime
    report['blender'] = bpy.app.version_string
    report['source_version'] = list(addon.bl_info['version'])
    report['loaded_module'] = str(Path(runtime.__file__).resolve())
    report['candidate_source'] = pin(runtime.__file__)
    report['baseline_source'] = pin(args.baseline)
    addon.register()
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.input).resolve()))
    scene = bpy.context.scene
    report['scene'] = scene.name
    report['frames'] = frames = [2, 6, 10, 14, 18, 22, 26, 30]
    report['actions'] = {obj.name: obj.animation_data.action.name
                         for obj in scene.objects if obj.animation_data and obj.animation_data.action}
    report['calibrated_meshes'] = {obj.name: {
        'vertices': len(obj.data.vertices),
        'records': {side: {'enabled': record.get('enabled', True), 'support_vertices': len(record['vertices'])}
                    for side, record in runtime._records(obj).items()}}
        for obj in scene.objects if obj.type == 'MESH' and runtime.RECORD_KEY in obj}
    report['modifiers'] = {obj.name: [{'name': mod.name, 'type': mod.type, 'viewport': mod.show_viewport}
                                     for mod in obj.modifiers]
                           for obj in scene.objects if obj.type == 'MESH'}
    report['handlers'] = {group: [fn.__module__ + '.' + fn.__name__
                                 for fn in getattr(bpy.app.handlers, group)]
                          for group in ('depsgraph_update_post', 'frame_change_post')}
    assert report['calibrated_meshes'], 'No calibrated mesh; this does not exercise the proposed fix'
    candidate = {name: getattr(runtime, name) for name in ('_prepare_runtime_records', '_prepare_mirror')}
    baseline = functions(args.baseline, runtime.__dict__)
    samples = report['cases'] = []
    reference = None
    try:
        for label in ('baseline', 'candidate', 'candidate', 'baseline', 'forearm_path_isolated'):
            chosen = baseline if label == 'baseline' else candidate
            for name, function in chosen.items():
                setattr(runtime, name, function)
            runtime._CACHE.clear()
            runtime._OUTPUT_CACHE.clear()
            runtime.validation_cache.clear()
            saved_busy = runtime._BUSY
            runtime._BUSY = label == 'forearm_path_isolated'
            instrument = Instrumentation(runtime)
            try:
                for frame in (1, 3):
                    scene.frame_set(frame)
                    bpy.context.view_layer.update()
                instrument.reset()
                elapsed, outputs = [], []
                for frame in frames:
                    start = time.perf_counter()
                    scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    elapsed.append((time.perf_counter() - start) * 1000)
                    outputs.append(witness(runtime, scene))
                errors = dict(runtime._ERRORS)
                row = {'label': label, 'milliseconds': elapsed, 'median_ms': statistics.median(elapsed),
                       'calls': dict(instrument.calls), 'nested_seconds': dict(instrument.seconds),
                       'errors': errors, 'nested_timing_note': 'Components overlap; do not sum their durations.'}
                if label != 'forearm_path_isolated':
                    assert not errors, errors
                    if reference is None:
                        reference = outputs
                    row['outputs_equal_to_baseline'] = outputs == reference
                    assert row['outputs_equal_to_baseline'], 'Candidate pose/managed outputs differ from baseline'
                samples.append(row)
                print('CASE', label, round(row['median_ms'], 3), flush=True)
            finally:
                instrument.restore()
                runtime._BUSY = saved_busy
    finally:
        for name, function in candidate.items():
            setattr(runtime, name, function)
    report['input_after'] = pin(args.input)
    report['artist_after'] = pin(args.artist)
    assert report['input_after'] == report['input']
    report['artist_disk_unchanged'] = report['artist_after'] == report['artist_before']
    report['no_save_operation'] = True
    report['limits'] = ['Background frame-step time is not viewport FPS.',
                        'Saved snapshot excludes unsaved live artist changes.',
                        'Only Character Designer registered; external GUI add-on callbacks are not represented.',
                        'Forearm isolation is diagnostic only, with stale corrective output; it is not a usable fix.',
                        'Small warm samples and shared machine load; no whole-model deformation equivalence claim.']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--artist', required=True)
    parser.add_argument('--addons', required=True)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    report = {'schema': 'x.forearm-frame-step-profile/1', 'completed': False, 'pid': os.getpid(),
              'model_and_reasoning_effort': 'unrecorded', 'started_utc': __import__('datetime').datetime.now(
                  __import__('datetime').timezone.utc).isoformat()}
    try:
        main(args, report)
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
