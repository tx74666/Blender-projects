"""New blank factory GUI: normal current SaveCopy load, frame1, natural settle.

The sealed010 constructor/start/finish are compiled in private globals. Only
current input/stage provenance changes; no old module, constant or pin mutates.
Root launches this later; source preparation does not start Blender.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE/'native_fixed_baseline_gui_010.py'
BASE_SHA = '421efa17f7ab048ea73cecc5fb04ca662f2d034991501382a42bf251ef09f914'
if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != BASE_SHA:
    raise RuntimeError('Sealed baseline startup010 changed')
sys.path.insert(0, str(HERE))
import native_fixed_baseline_gui_010 as original
import current_model_private_gui_fps_probe_011 as playback
require, pin = original.require, original.pin
require(Path(original.__file__).resolve() == BASE_PATH and Path(playback.__file__).resolve()
    == HERE/'current_model_private_gui_fps_probe_011.py', 'Different baseline startup/probe module imported')
SESSION = None


def private_base(snapshot):
    source = BASE_PATH.read_text(encoding='utf8')
    require(hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() == BASE_SHA, 'Sealed startup010 changed')
    tree = ast.parse(source)
    nodes = [node for node in tree.body if (isinstance(node, ast.ClassDef) and node.name == 'BaselineGUI')
        or (isinstance(node, ast.FunctionDef) and node.name == 'stage_pins')]
    require(len(nodes) == 2, 'Expected sealed startup class and stage pin helper')
    scope = {**vars(original), '__file__': str(Path(__file__).resolve()),
        'INPUT': Path(snapshot['copy']['path']), 'INPUT_SHA': snapshot['copy']['sha256'],
        'INPUT_BYTES': snapshot['copy']['bytes'], 'STAGE': playback.STAGE, 'MANIFEST_SHA': playback.MANIFEST_SHA}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(BASE_PATH), 'exec'), scope)
    return scope['BaselineGUI'], hashlib.sha256(ast.dump(ast.Module(body=nodes, type_ignores=[]), include_attributes=False).encode()).hexdigest()


def source_context(bpy):
    scene, layer = bpy.context.scene, bpy.context.view_layer
    return {'scene': int(scene.as_pointer()), 'frame': [scene.frame_current, float(scene.frame_subframe)],
        'layer': int(layer.as_pointer()), 'objects': sorted((int(obj.as_pointer()), obj.session_uid,
            bool(obj.hide_get(view_layer=layer)), bool(obj.select_get(view_layer=layer))) for obj in layer.objects),
        'active': int(layer.objects.active.as_pointer()) if layer.objects.active else None,
        'dirty': bool(bpy.data.is_dirty), 'filepath': bpy.data.filepath}


def start(args):
    snapshot, snapshot_pin = playback.current.load_snapshot(args.snapshot_report, args.snapshot_report_sha256,
        args.input_sha256, args.input_bytes)
    base, ast_sha = private_base(snapshot)

    class CurrentGUI(base):
        def __init__(self):
            self.aligned = self.finished = False
            try:
                super().__init__(args.report)
                self.report.update(schema='x.current-private-baseline-gui/1', current_snapshot_receipt=snapshot_pin,
                    current_snapshot_verified=True, current_input_scope='Actual guarded current SaveCopy, not fixed40644; later artist edits require a new capture.',
                    adapter_base_startup=pin(BASE_PATH), adapter_class_ast_sha256=ast_sha,
                    current_helpers={Path(playback.__file__).name: pin(playback.__file__),
                        Path(playback.current.__file__).name: pin(playback.current.__file__)},
                    normal_source_frame1_settled=False, readonly_v9_witness_completed=False,
                    readonly_context_unchanged=False, normal_handlers_unchanged=False, current_dependencies_unchanged=False)
            except BaseException:
                if hasattr(self, 'stream'):
                    self.stream.close()
                raise

        def start(self):
            super().start()
            import bpy
            identity = snapshot['source_identity']
            require(bpy.context.scene.name_full == identity['scene']
                and [bpy.context.scene.frame_current, float(bpy.context.scene.frame_subframe)] == identity['frame'],
                'Normally loaded current Source Scene/frame differs from SaveCopy identity')
            layer = bpy.context.scene.view_layers.get(identity['view_layer'])
            require(layer is not None, 'Saved Source View Layer missing')
            bpy.context.window.view_layer = layer

        def tick(self):
            import bpy
            try:
                require(original.time.monotonic()-self.started < 180., 'Current baseline normal-settle timeout')
                require(Path(bpy.data.filepath).resolve() == Path(snapshot['copy']['path']), 'Different private baseline loaded')
                runtime = self.runtime
                state = {key: bool(getattr(runtime, key)) for key in ('_RUNTIME_REGISTERED', '_SCENE_STATE_ACTIVE',
                    '_BUSY', '_INITIALIZE_PENDING', '_SCENE_CLEANUP_PENDING')}
                state['natural_lifecycle_timer'] = bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle)
                state['errors'] = dict(runtime._ERRORS)
                if state != self.last:
                    self.report['natural_lifecycle_changes'].append(state)
                    self.last = state
                require(not state['errors'], 'Normal current baseline runtime emitted errors')
                ready = state['_RUNTIME_REGISTERED'] and state['_SCENE_STATE_ACTIVE'] and not any(state[key] for key in
                    ('_BUSY', '_INITIALIZE_PENDING', '_SCENE_CLEANUP_PENDING', 'natural_lifecycle_timer'))
                self.ready_count = self.ready_count+1 if ready else 0
                if self.ready_count < 2:
                    return .1
                require(bpy.context.scene.name_full == snapshot['source_identity']['scene']
                    and bpy.context.view_layer.name == snapshot['source_identity']['view_layer'], 'Current Source context changed')
                if not self.aligned:
                    bpy.context.scene.frame_set(1, subframe=0.)
                    self.aligned, self.ready_count, self.last = True, 0, None
                    return .1  # normal event-loop yield before observing/verifying frame1
                require(bpy.context.scene.frame_current == 1 and bpy.context.scene.frame_subframe == 0., 'Private baseline frame1 changed')
                self.report['normal_source_frame1_settled'] = True
                self.report['settled_scene'] = {'name': bpy.context.scene.name_full, 'frame': 1, 'subframe': 0.,
                    'view_layer': bpy.context.view_layer.name, 'sync_mode': bpy.context.scene.sync_mode}
                self.finish()
                return None
            except BaseException:
                self.finish(traceback.format_exc())
                return None

        def finish(self, error=None):
            if self.finished:
                return
            self.finished = True
            try:
                require(self.aligned and self.report['normal_source_frame1_settled'], 'Normal frame1 alignment not verified')
                import bpy
                witness = playback.importlib.import_module('native_validation_support_v9')
                before, callbacks = source_context(bpy), witness.handler_snapshot()
                proof = witness.source_property_witness(bpy.context.scene)
                self.report.update(readonly_v9_witness_completed=True, source_properties_sha256=proof['sha256'],
                    readonly_context_unchanged=before == source_context(bpy),
                    normal_handlers_unchanged=callbacks == witness.handler_snapshot(),
                    callbacks_after_natural_settle=callbacks)
                require(self.report['readonly_context_unchanged'] and self.report['normal_handlers_unchanged'], 'Readonly startup proof changed protected state')
                _, observed = playback.current.load_snapshot(args.snapshot_report, args.snapshot_report_sha256, args.input_sha256, args.input_bytes)
                self.report['current_dependencies_unchanged'] = (observed == snapshot_pin and self.report['adapter_base_startup'] == pin(BASE_PATH)
                    and all(item == pin(item['path']) for item in self.report['current_helpers'].values()))
                require(self.report['current_dependencies_unchanged'], 'Current startup receipt/dependency changed')
            except BaseException:
                extra = traceback.format_exc()
                error = error+'\nCurrent startup proof:\n'+extra if error else extra
            super().finish(error)

    controller = CurrentGUI()
    try:
        controller.start()
    except BaseException:
        controller.finish(traceback.format_exc())
        raise
    return controller


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for field in ('snapshot-report', 'snapshot-report-sha256', 'input-sha256', 'report'):
        parser.add_argument('--'+field, required=True)
    parser.add_argument('--input-bytes', type=int, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    SESSION = start(args)
