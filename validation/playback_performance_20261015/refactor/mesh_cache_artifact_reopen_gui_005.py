"""Normal independent PC2 artifact GUI reopen; Root alone launches this process.

Keep the factory UI, ordinary add-on/load handlers and timers. Advance one
integer frame, yield to the event loop, then read the complete cache oracle.
After 1-30 and a verified return to saved frame 1, leave the owned GUI alive.
No save, manual solver, defer, callback replacement or FPS measurement exists.
"""
import argparse
import datetime
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ARTIST = HERE.parents[2]/'X.blend'
CONTRACT_PATH = HERE/'mesh_cache_artifact_contract_005.py'
CONTRACT_SHA = 'a4e68220734435de8f8ac52bbbca73c2b7259253626c1bc301dfcfc9b55efad6'
SESSION = None


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def handlers(bpy):
    return {name: [{'module': getattr(item, '__module__', None),
                    'name': getattr(item, '__qualname__', repr(item)), 'identity': id(item)} for item in value]
            for name in dir(bpy.app.handlers) if isinstance((value := getattr(bpy.app.handlers, name)), list)}


def ui_snapshot(bpy):
    return [{'window': window.as_pointer(), 'screen': window.screen.name,
             'areas': [area.type for area in window.screen.areas]}
            for window in bpy.context.window_manager.windows]


class PythonErrorTee:
    def __init__(self, original):
        self.original, self.text, self.tail, self.detected, self.truncated = original, '', '', False, False

    def write(self, text):
        self.original.write(text)
        combined = self.tail+text
        self.detected |= ('Traceback (most recent call last)' in combined or 'Error in bpy.app.handlers' in combined)
        self.tail = combined[-256:]
        available = max(0, 32768-len(self.text))
        self.text += text[:available]
        self.truncated |= len(text) > available
        return len(text)

    def flush(self):
        self.original.flush()

    def __getattr__(self, name):
        return getattr(self.original, name)


class ReopenSession:
    def __init__(self, args, stream, report):
        self.args, self.stream, self.report = args, stream, report
        require(pin(CONTRACT_PATH)['sha256'] == CONTRACT_SHA, 'Shared artifact contract source changed')
        sys.path.insert(0, str(HERE))
        self.helper = importlib.import_module('mesh_cache_artifact_contract_005')
        require(Path(self.helper.__file__).resolve() == CONTRACT_PATH, 'Another contract helper imported')
        self.receipt, self.receipt_pin = self.helper.load_published_receipt(args.artifact_report, args.artifact_report_sha256)
        self.helper.verify_external_pins(self.receipt)
        self.contract = self.receipt['reopen_contract']
        self.artifact = Path(self.receipt['artifact']['path']).resolve(strict=True)
        require(self.artifact != ARTIST.resolve() and not os.path.samefile(self.artifact, ARTIST),
                'Never open artist or its hardlink')
        self.artist_pin = pin(ARTIST)
        require(self.artist_pin == self.receipt['artist_before'], 'Artist disk differs from published artifact proof')
        self.package = Path(self.contract['package']['path']).resolve(strict=True)
        require(math.isfinite(args.timeout) and 0 < args.timeout <= 3600, 'Invalid bounded verification timeout')
        self.timer, self.phase, self.frame = self.tick, 'WAIT_STANDARD_LOAD', 1
        self.started, self.stable_ticks, self.last_lifecycle = time.monotonic(), 0, None
        self.scene = self.runtime = self.tee = self.standard_handlers = None
        self.finished = False
        self.report.update(artifact_receipt=self.receipt_pin, artifact=self.receipt['artifact'],
            artist_before=self.artist_pin, script=pin(__file__), shared_contract_helper=pin(CONTRACT_PATH),
            source_package=self.contract['package'], frames=[], lifecycle_observations=[],
            external_pins_verified_before=True, load_ui=False)

    def flush(self):
        self.stream.seek(0)
        self.stream.write(json.dumps(self.report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        self.stream.truncate()
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def start(self):
        import bpy
        require(not bpy.app.background and '--factory-startup' in sys.argv
                and not bpy.data.filepath and not bpy.data.is_dirty, 'New blank clean factory-startup GUI required')
        require(bpy.app.version_string == self.receipt['blender'], 'Native Blender version differs from artifact proof')
        self.factory_ui = ui_snapshot(bpy)
        self.tee = PythonErrorTee(sys.stderr)
        sys.stderr = self.tee
        self.report['callbacks_before_registration'] = handlers(bpy)
        sys.path.insert(0, str(self.package.parent))
        self.addon = importlib.import_module('character_designer')
        self.runtime = importlib.import_module('character_designer.forearm_twist')
        require(Path(self.addon.__file__).resolve().parent == self.package
                and Path(self.runtime.__file__).resolve().parent == self.package, 'Different standard add-on imported')
        self.addon.register()
        self.report['callbacks_after_standard_registration'] = handlers(bpy)
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(self.artifact), load_ui=False), 'Artifact open failed')
        require(Path(bpy.data.filepath).resolve() == self.artifact, 'Another file opened')
        self.scene = bpy.data.scenes.get(self.contract['scene']['name'])
        require(self.scene is not None and bpy.context.scene is self.scene, 'Candidate Scene was not selected by normal load')
        require(self.scene.frame_current == self.contract['scene']['saved_frame'] == 1
                and self.scene.frame_subframe == 0., 'Serialized saved frame must be 1')
        self.assert_cache_health()
        self.helper.check_binding(self.scene, self.contract)
        self.report.update(loaded_file=bpy.data.filepath, blender=bpy.app.version_string,
            addon_version=list(self.addon.bl_info['version']), factory_ui=self.factory_ui,
            ui_after_open=ui_snapshot(bpy), callbacks_after_standard_open=handlers(bpy))
        self.flush()
        # Register after open: ordinary load may discard nonpersistent timers.
        bpy.app.timers.register(self.timer, first_interval=.1)

    def lifecycle(self, bpy):
        runtime = self.runtime
        state = {name: bool(getattr(runtime, name)) for name in
            ('_RUNTIME_REGISTERED', '_SCENE_STATE_ACTIVE', '_INITIALIZE_PENDING', '_SCENE_CLEANUP_PENDING', '_BUSY')}
        state['natural_lifecycle_timer_registered'] = bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle)
        state['errors'] = dict(runtime._ERRORS)
        return state

    @staticmethod
    def ready(state):
        return (state['_RUNTIME_REGISTERED'] and state['_SCENE_STATE_ACTIVE'] and not state['errors']
            and not any(state[key] for key in ('_INITIALIZE_PENDING', '_SCENE_CLEANUP_PENDING', '_BUSY',
                                                'natural_lifecycle_timer_registered')))

    def assert_cache_health(self):
        meshes = [obj for obj in self.scene.objects if obj.type == 'MESH']
        require(len(meshes) == len(self.contract['objects']) == 69, 'Full cached actor Mesh count changed')
        require(not any(self.runtime.RECORD_KEY in obj for obj in meshes), 'Cache Mesh unexpectedly enrolled authoring solver')
        self.report['cached_meshes_not_authoring_enrolled'] = True

    def verify_frame(self, bpy):
        require(self.scene.frame_current == self.frame and self.scene.frame_subframe == 0., 'Frame changed during event-loop yield')
        self.assert_cache_health()
        result = self.helper.check_frame(self.scene, self.contract, self.frame)
        require(result['exact'] is True and result['frame'] == self.frame and len(result['meshes']) == 69
                and all(row['exact'] is True and not row['changed_components'] for row in result['meshes']),
                'Reopened full actor geometry/world/normals differ')
        require(handlers(bpy) == self.standard_handlers, 'Standard callback identities changed')
        return {'frame': self.frame, 'full69_geometry_exact': True, 'check_sha256': object_hash(result),
                'mesh_count': 69}

    def finish(self, error=None):
        import bpy
        if self.finished:
            return
        self.finished = True
        errors = [error] if error else []
        if error:
            self.report['error'] = error
        try:
            if bpy.app.timers.is_registered(self.timer):
                bpy.app.timers.unregister(self.timer)
            require(not bpy.app.timers.is_registered(self.timer), 'Own verification timer retained')
            self.report['own_verification_timer_removed'] = True
        except BaseException:
            errors.append(traceback.format_exc())
        try:
            self.helper.verify_external_pins(self.receipt)
            require(pin(self.receipt_pin['path']) == self.receipt_pin, 'Artifact publication receipt changed')
            require(pin(ARTIST) == self.artist_pin and pin(self.artifact) == self.receipt['artifact'], 'Protected disk changed')
            require(pin(__file__) == self.report['script'] and pin(CONTRACT_PATH) == self.report['shared_contract_helper'],
                    'GUI entry/shared helper changed')
            require(self.standard_handlers is not None and handlers(bpy) == self.standard_handlers,
                    'Normal callbacks changed or never settled')
            require(self.ready(self.lifecycle(bpy)), 'Normal runtime did not remain settled/error-free')
            self.helper.check_binding(self.scene, self.contract)
            require(self.helper.check_serialized_dependencies(self.scene, self.contract)['exact'] is True,
                    'Serialized dependency closure changed')
            self.report['serialized_dependencies_after_exact'] = True
            require(self.tee is not None and not self.tee.detected, 'Standard Python callback errors emitted')
            require(ui_snapshot(bpy) == self.factory_ui, 'Factory GUI layout changed')
            self.report['callbacks_at_finish'] = handlers(bpy)
            self.report['protected_disks_sources_callbacks_unchanged'] = True
            self.report['factory_layout_retained'] = True
        except BaseException:
            errors.append(traceback.format_exc())
        if self.tee is not None:
            self.report['python_stderr'] = {'text': self.tee.text, 'truncated': self.tee.truncated,
                'scope': 'Python stderr only; Root must also inspect the native process log.'}
            owned = sys.stderr is self.tee
            if owned:
                sys.stderr = self.tee.original
            self.report['own_stderr_restored'] = owned and sys.stderr is self.tee.original
            if not self.report['own_stderr_restored']:
                errors.append('Stderr ownership changed; foreign stream preserved')
        else:
            self.report['own_stderr_restored'] = False
        self.report['cleanup_errors'] = errors
        self.report['addon_left_registered'] = bool(getattr(self.runtime, '_RUNTIME_REGISTERED', False))
        complete = (not errors and len(self.report['frames']) == 30
            and [row['frame'] for row in self.report['frames']] == list(range(1, 31))
            and self.report.get('saved_frame_restored_verified') is True
            and self.report.get('portable_animation_start_end_exact') is True
            and self.report.get('cached_meshes_not_authoring_enrolled') is True
            and self.report.get('own_stderr_restored') is True and self.report['addon_left_registered'])
        self.report['completed'] = self.report['normal_addon_lifecycle_reopen_verified'] = complete
        try:
            self.flush()
        finally:
            self.stream.close()

    def tick(self):
        import bpy
        try:
            require(time.monotonic()-self.started < self.args.timeout, 'GUI verification timeout')
            require(Path(bpy.data.filepath).resolve() == self.artifact and bpy.context.scene is self.scene,
                    'Owned preview changed file/Scene')
            state = self.lifecycle(bpy)
            require(not state['errors'] and not self.tee.detected, 'Normal lifecycle/callback reported errors')
            if self.phase == 'WAIT_STANDARD_LOAD':
                if state != self.last_lifecycle:
                    self.report['lifecycle_observations'].append(state)
                    self.last_lifecycle = state
                self.stable_ticks = self.stable_ticks+1 if self.ready(state) else 0
                if self.stable_ticks < 2:
                    return .1
                self.standard_handlers = handlers(bpy)
                self.report['callbacks_after_natural_settle'] = self.standard_handlers
                require(self.scene.frame_current == 1 and self.scene.frame_subframe == 0.,
                        'Natural load left the serialized saved frame1')
                require(self.helper.check_serialized_dependencies(self.scene, self.contract)['exact'] is True,
                        'Reopened dependency closure differs')
                self.report['serialized_dependencies_initial_exact'] = True
                require(self.helper.animation_state(self.scene, self.contract) == self.contract['portable_animation'],
                        'Natural load changed serialized Action/animation state')
                self.report['portable_animation_initial_exact'] = True
                self.phase = 'ADVANCE'
            require(self.ready(state), 'Normal runtime became pending/busy during validation')
            if self.phase in ('ADVANCE', 'RESTORE_ADVANCE'):
                self.scene.frame_set(self.frame, subframe=0.)
                self.phase = 'RESTORE_VERIFY' if self.phase == 'RESTORE_ADVANCE' else 'VERIFY'
                return .05
            row = self.verify_frame(bpy)
            if self.phase == 'RESTORE_VERIFY':
                self.report['saved_frame_verification'] = row
                self.report['saved_frame_restored_verified'] = self.frame == self.contract['scene']['saved_frame'] == 1
                require(self.helper.animation_state(self.scene, self.contract) == self.contract['portable_animation'],
                        'Restored frame1 Action/animation state changed')
                self.report['portable_animation_after_restore_exact'] = True
                self.report['portable_animation_start_end_exact'] = True
                self.finish()
                return None
            self.report['frames'].append(row)
            self.flush()
            if self.frame == 30:
                self.frame, self.phase = 1, 'RESTORE_ADVANCE'
            else:
                self.frame, self.phase = self.frame+1, 'ADVANCE'
            return .05
        except BaseException:
            self.finish(traceback.format_exc())
            return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('artifact-report', 'artifact-report-sha256', 'report'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--timeout', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report_path = Path(args.report).resolve()
    require(report_path.parent == HERE and report_path.suffix == '.json' and not report_path.exists(),
            'Unused direct project JSON report required')
    report = {'schema': 'x.pc2-actor-artifact-gui-reopen/1', 'completed': False, 'pid': os.getpid(),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'gui_fps_verified': False,
        'no_scene_save': True, 'no_manual_solver_or_parent_helper_calls': True,
        'no_handler_disable_or_runtime_defer': True, 'preview_process_left_alive': True,
        'limits': ['Only integer clip frames1-30 geometry/stored animation reopening; no GUI FPS acceptance.',
                   'Stored Action/animation payload checked at naturally settled frame1 and after restored frame1, not every intermediate frame.',
                   'Earlier fixed40644 private input only; no equivalence to the current live artist model is claimed.',
                   'Root aligns camera/viewport/material/resolution and prewarms before FPS measurement.']}
    stream = report_path.open('x', encoding='utf-8')
    try:
        SESSION = ReopenSession(args, stream, report)
        SESSION.start()
    except BaseException:
        error = traceback.format_exc()
        if SESSION is not None:
            SESSION.finish(error)
        else:
            report.update(error=error, cleanup_errors=[], completed=False)
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
            stream.close()
        raise
