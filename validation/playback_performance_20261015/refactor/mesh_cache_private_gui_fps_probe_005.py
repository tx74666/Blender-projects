"""Observe normal GUI playback of a previously verified, private PC2 artifact.

Reuse only sealed FPS009's clock/callback/playback/restoration machinery. Its
Bone constructor and full-state witness are never called. No launch/open/save,
add-on registration, manual solver, runtime override or cache repair is offered.
"""
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
CORE_PATH = HERE / 'private_gui_fps_probe_009.py'
CORE_SHA = 'a6ce26f86c4fa6aee5dc58fc68f59010a12c9983324133f56e01e2ab2db471ed'
CONTRACT_PATH = HERE / 'mesh_cache_artifact_contract_005.py'
CONTRACT_SHA = 'a4e68220734435de8f8ac52bbbca73c2b7259253626c1bc301dfcfc9b55efad6'
GUI_PATH = HERE / 'mesh_cache_artifact_reopen_gui_005.py'
GUI_SHA = 'd30819f81998d3a262792e4b33d0af0040988307557b07b4972e5c16909f035e'
PORTABLE_SHA = 'c6881b78c9de8af661b6ecbf264e4e8a4f9861ce645246d9e8dccb1fc298b680'
BASE_SHA = '3994f58288244684679ffd48d0837ac88bcfd9768f0a3a12c3e1d7d5b6265c0a'
SESSION = None

if hashlib.sha256(CORE_PATH.read_bytes()).hexdigest() != CORE_SHA:
    raise RuntimeError('Sealed normal playback core changed')
sys.path.insert(0, str(HERE))
import private_gui_fps_probe_009 as core
if Path(core.__file__).resolve() != CORE_PATH:
    raise RuntimeError('Another FPS core was imported')
require, pin = core.require, core.pin

GUI_FLAGS = (
    'normal_addon_lifecycle_reopen_verified', 'own_verification_timer_removed',
    'own_stderr_restored', 'protected_disks_sources_callbacks_unchanged',
    'cached_meshes_not_authoring_enrolled', 'addon_left_registered',
    'saved_frame_restored_verified', 'portable_animation_initial_exact',
    'portable_animation_after_restore_exact', 'portable_animation_start_end_exact',
    'serialized_dependencies_initial_exact', 'serialized_dependencies_after_exact',
)


def valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_config(config, current_pid):
    fields = {'expected_pid', 'private_blend', 'private_sha256', 'artist', 'gui_report',
              'gui_report_sha256', 'mode', 'report'}
    require(isinstance(config, dict) and set(config) == fields, 'Explicit cache-only configuration required')
    require(type(config['expected_pid']) is int and config['expected_pid'] > 0
            and config['expected_pid'] == current_pid, 'Root-observed private PID differs')
    require(config['mode'] in {'MATERIAL', 'SOLID'}, 'Explicit MATERIAL or SOLID required')
    for key in ('private_blend', 'artist', 'gui_report', 'report'):
        require(isinstance(config[key], str) and bool(config[key]), 'Nonempty path strings required')
    require(valid_sha(config['private_sha256']) and valid_sha(config['gui_report_sha256']), 'Invalid content SHA')
    return dict(config)


def validate_gui(receipt, pid, artifact_pin):
    require(receipt.get('schema') == 'x.pc2-actor-artifact-gui-reopen/1'
            and receipt.get('completed') is True and receipt.get('pid') == pid
            and 'error' not in receipt and receipt.get('cleanup_errors') == [],
            'Actual completed GUI005 receipt from this private PID required')
    require(all(receipt.get(key) is True for key in GUI_FLAGS), 'GUI005 lifecycle/cache/restoration proof failed')
    require(receipt.get('artifact') == artifact_pin, 'GUI005 artifact differs from the loaded private file')
    frames = receipt.get('frames')
    require(isinstance(frames, list) and [row.get('frame') for row in frames] == list(range(1, 31))
            and all(row.get('full69_geometry_exact') is True and row.get('mesh_count') == 69
                    and valid_sha(row.get('check_sha256')) for row in frames), 'GUI005 complete69-by30 proof required')
    return receipt['callbacks_after_natural_settle']


def observed_advances(events):
    """Forward-loop token gaps; full unseen loops cannot be inferred from tokens."""
    counts, outside = {}, []
    repeats = wraps = skipped = 0
    for left, right in zip(events, events[1:]):
        a, b = int(left[1]), int(right[1])
        if not (1 <= a <= 30 and 1 <= b <= 30):
            outside.append([a, b])
            continue
        step = (b - a) % 30
        counts[step] = counts.get(step, 0) + 1
        repeats += step == 0
        wraps += b < a
        skipped += max(0, step - 1)
    return {'transitions': max(0, len(events) - 1), 'forward_modulo30_step_histogram': dict(sorted(counts.items())),
            'repeated_integer_tokens': repeats, 'observed_wraps': wraps,
            'minimum_unobserved_integer_frames': skipped, 'outside_clip_transitions': outside,
            'scope': 'Observed token gaps only; cannot distinguish playback skip from seek, or count full unseen loops. No GPU presentation/dropped-display-frame claim.'}


def gpu_context_info():
    """Optional actual GUI context metadata, captured once before timing."""
    result = {'renderer': 'unknown', 'vendor': 'unknown', 'version': 'unknown', 'unavailable': {}}
    try:
        platform = importlib.import_module('gpu').platform
    except Exception as error:
        result['unavailable']['platform'] = type(error).__name__
        return result
    for name in ('renderer', 'vendor', 'version'):
        try:
            value = getattr(platform, name + '_get')()
            if isinstance(value, str) and value:
                result[name] = value
            else:
                result['unavailable'][name] = 'empty/non-string result'
        except Exception as error:
            result['unavailable'][name] = type(error).__name__
    return result


def modifier_values(modifier, fields):
    return tuple(tuple(getattr(modifier, name)) if name == 'flip_axis' else getattr(modifier, name)
                 for name in fields)


class CacheProbe(core.Probe):
    def __init__(self, config):
        import bpy
        self.config = validate_config(config, os.getpid())
        require(not bpy.app.background and '--factory-startup' in sys.argv, 'Owned factory-startup GUI required')
        require(pin(CONTRACT_PATH)['sha256'] == CONTRACT_SHA and pin(GUI_PATH)['sha256'] == GUI_SHA,
                'Final reviewed cache contract and GUI source pins required')
        for name, expected in (('native_validation_support.py', BASE_SHA),
                               ('native_artifact_action_witness_008.py', PORTABLE_SHA)):
            require(pin(HERE / name)['sha256'] == expected, 'Generic proof dependency changed')
        self.shared = importlib.import_module('mesh_cache_artifact_contract_005')
        self.witness = importlib.import_module('native_validation_support')
        self.portable = importlib.import_module('native_artifact_action_witness_008')
        for module, name in ((self.shared, CONTRACT_PATH.name), (self.witness, 'native_validation_support.py'),
                             (self.portable, 'native_artifact_action_witness_008.py')):
            require(Path(module.__file__).resolve() == HERE / name, 'Another cache proof helper imported')
        self.private, self.artist = Path(config['private_blend']).resolve(strict=True), Path(config['artist']).resolve(strict=True)
        require(self.artist == (HERE.parents[2] / 'X.blend').resolve(), 'Canonical artist boundary required')
        require(self.private != self.artist and not os.path.samefile(self.private, self.artist), 'Never profile artist or a hardlink')
        require(Path(bpy.data.filepath).resolve() == self.private, 'Different private file loaded')
        self.loaded_filepath_literal = bpy.data.filepath
        self.private_pin, self.artist_pin = pin(self.private), pin(self.artist)
        require(self.private_pin['sha256'] == config['private_sha256'], 'Private artifact SHA differs')
        gui, self.gui_pin = core.load_pinned_json(config['gui_report'], config['gui_report_sha256'])
        callbacks = validate_gui(gui, os.getpid(), self.private_pin)
        require(gui['script'] == pin(GUI_PATH) and gui['shared_contract_helper'] == pin(CONTRACT_PATH), 'GUI005 source proof differs')
        self.receipt, self.artifact_receipt_pin = self.shared.load_published_receipt(
            gui['artifact_receipt']['path'], gui['artifact_receipt']['sha256'])
        require(gui['artifact_receipt'] == self.artifact_receipt_pin and self.receipt['artifact'] == self.private_pin
                and self.receipt['artist_before'] == self.artist_pin, 'Publication/file/artist proof differs')
        self.contract = self.receipt['reopen_contract']
        self.package = Path(self.contract['package']['path']).resolve(strict=True)
        self.manifest_pin = self.contract['package']['manifest']
        self.manifest, observed_manifest = core.load_pinned_json(self.manifest_pin['path'], self.manifest_pin['sha256'])
        require(observed_manifest == self.manifest_pin, 'Package manifest differs')
        self.sources = self.witness.verify_package_manifest(self.package, self.manifest)
        require(self.sources == self.contract['package']['files'], 'Standard package payload differs')
        self.dependencies = {name: pin(path) for name, path in (
            ('timing_core', CORE_PATH), ('cache_probe', Path(__file__)), ('shared_contract', CONTRACT_PATH),
            ('gui_entry', GUI_PATH), ('portable_context', Path(self.portable.__file__)),
            ('base_oracle', Path(self.witness.__file__)), ('geometry_oracle', self.witness.ORACLE_PATH))}
        self.addon, self.runtime = sys.modules.get('character_designer'), sys.modules.get('character_designer.forearm_twist')
        require(self.addon is not None and self.runtime is not None
                and Path(self.addon.__file__).resolve().parent == self.package
                and Path(self.runtime.__file__).resolve().parent == self.package, 'Expected standard loaded add-on required')
        self.window, self.screen, self.scene, self.area = bpy.context.window, bpy.context.screen, bpy.context.scene, bpy.context.area
        require(self.window and self.screen and self.scene and self.area and self.area.type in {'CONSOLE', 'VIEW_3D'}, 'Owned Console/VIEW3D context required')
        require(self.scene.name_full == self.contract['scene']['name'] and len(bpy.data.scenes) == 1
                and self.scene.frame_current == self.contract['scene']['saved_frame'] == 1
                and self.scene.frame_subframe == 0., 'Only the verified artifact Scene at restored frame1 required')
        require(not any(window.screen.is_animation_playing for window in bpy.context.window_manager.windows if window.screen), 'Playback must already be stopped')
        self.initial_area_type = self.area.type
        self.region = self.before_context = self.before_state = self.draw_handle = self.tee = None
        self.timer = self.tick
        self.pre_callback, self.post_callback, self.draw_callback = self.on_pre, self.on_post, self.on_draw
        self.phase, self.collecting, self.closed = 'PREPARE', False, False
        self.start_ns = self.end_ns = self.play_start_ns = None
        self.pre_pending, self.post_events, self.draw_events, self.eval_events, self.callback_errors = None, [], [], [], []
        self.handlers_before, self.owned_handlers = core.handler_snapshot(bpy), []
        require({name: [row['identity'] for row in rows] for name, rows in callbacks.items()} == self.handlers_before,
                'Standard callback identities changed since GUI005')
        mapping = {row['source_name']: row['target_name'] for row in self.contract['objects']}
        self.required_meshes = tuple(mapping[name] for name in ('Cosha', 'Shoes'))
        self.assert_runtime()
        self.capture_hot_bindings()
        self.shared.verify_external_pins(self.receipt)
        report_path = Path(config['report']).resolve()
        require(report_path.is_relative_to(HERE) and report_path.suffix == '.json' and not report_path.exists(),
                'Exclusive unused project JSON report required')
        self.stream = report_path.open('x', encoding='utf-8')
        try:
            self.report = {'schema': 'x.pc2-private-gui-normal-playback/1', 'completed': False, 'pid': os.getpid(),
                'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'config': dict(config),
                'script': pin(CORE_PATH), 'adapter_script': pin(__file__), 'private_before': self.private_pin,
                'artist_before': self.artist_pin, 'source_manifest': self.manifest_pin, 'dependencies': self.dependencies,
                'gui005': self.gui_pin, 'artifact_receipt': self.artifact_receipt_pin, 'blender': bpy.app.version_string,
                'gpu_context_before_timing': gpu_context_info(),
                'installation_area_type': self.initial_area_type, 'no_open_save_deploy': True,
                'normal_callbacks_preserved': True, 'no_manual_solver_or_helper_calls': True,
                'no_runtime_defer_or_override': True, 'performance_acceptance': False,
                'inherited_cleanup_aliases': {'all_mesh_key_pose_raw_action_outputs_exact':
                    'Exact complete69 cache geometry/world/normals/attributes, declared portable animation and binding/visibility; no separate full rig-pose or ShapeKey proof claimed.'},
                'limits': ['Fixed2s warmup and16s normal animation_play; no GPU completion or compositor presentation proof.',
                    'Frame-change and POST_PIXEL changed-token cadence are separate; no reciprocal-ms FPS.',
                    'Observed modulo30 gaps are minimum unseen token counts, not total dropped/presented frames.',
                    'Appended pre-to-post spans exclude earlier standard frame-pre callbacks; not total frame CPU time.',
                    'One literal RNA binding/record health poll runs with the existing0.1s timer; no filesystem path resolution, file hash or geometry/Action proof occurs in the hot window.',
                    'Material compilation completion is unmeasured; Root must prewarm matching view/shading before comparisons.',
                    'Saved1-30 integer clip only; no subframe, shader visual, physics or automatic30FPS adoption.',
                    'Console install normalizes its area to VIEW3D as the sealed core does; the restored context check refers to that normalized viewport.']}
            self.flush()
        except BaseException:
            self.stream.close()
            raise

    def assert_runtime(self):
        require(not self.collecting, 'Full cache health/disk proofs are outside the hot window')
        super().assert_runtime()
        require(not any(obj.type == 'MESH' and self.runtime.RECORD_KEY in obj for obj in self.scene.objects),
                'A cached Mesh is enrolled in the authoring solver')
        binding = self.shared.check_binding(self.scene, self.contract)
        require(binding.get('healthy') is True and binding.get('meshes') == 69, 'Cache binding health failed')
        self.shared.verify_external_pins(self.receipt)

    def capture_hot_bindings(self):
        require(not self.collecting, 'Binding capture is outside the hot window')
        self.hot_fields = tuple(self.shared.CACHE_SETTINGS)
        self.hot_scene_state = self.shared.scene_state(self.scene)
        self.hot_bindings = []
        for row in self.contract['objects']:
            obj = self.scene.objects[row['target_name']]
            modifier = obj.modifiers[0]
            self.hot_bindings.append((obj, int(obj.as_pointer()), obj.session_uid,
                int(obj.data.as_pointer()), obj.data.session_uid, int(modifier.as_pointer()), modifier.name,
                modifier.filepath, modifier_values(modifier, self.hot_fields)))

    def assert_hot_bindings(self):
        require(not self.runtime._ERRORS, 'Runtime error during cached playback')
        require(self.shared.scene_state(self.scene) == self.hot_scene_state, 'Cache clip/sync/FPS settings changed')
        meshes = [obj for obj in self.scene.objects if obj.type == 'MESH']
        require(len(meshes) == 69 and {(int(obj.as_pointer()), obj.session_uid) for obj in meshes}
                == {(row[1], row[2]) for row in self.hot_bindings}, 'Cache Mesh membership changed')
        for obj, pointer, uid, data_pointer, data_uid, mod_pointer, mod_name, filepath, settings in self.hot_bindings:
            require(int(obj.as_pointer()) == pointer and obj.session_uid == uid
                    and int(obj.data.as_pointer()) == data_pointer and obj.data.session_uid == data_uid
                    and self.runtime.RECORD_KEY not in obj and len(obj.modifiers) == 1,
                    'Cache data binding or authoring enrollment changed')
            modifier = obj.modifiers[0]
            require(int(modifier.as_pointer()) == mod_pointer and modifier.name == mod_name
                    and modifier.type == 'MESH_CACHE' and modifier.filepath == filepath
                    and modifier_values(modifier, self.hot_fields) == settings,
                    'Literal PC2 modifier binding/settings changed')

    def assert_owned(self):
        if not self.collecting:
            return super().assert_owned()
        import bpy
        # Same ownership boundaries as the sealed core, with a stricter saved
        # filepath literal in place of filesystem resolution during timing.
        require(os.getpid() == self.config['expected_pid'] and bpy.data.filepath == self.loaded_filepath_literal
                and self.window.screen == self.screen and self.window.scene == self.scene,
                'Owned PID/file/Window/Scene changed during playback')
        require(any(area == self.area for area in self.screen.areas) and self.area.type == 'VIEW_3D',
                'Owned viewport changed during playback')
        self.assert_hot_bindings()

    def full_state(self):
        import bpy
        require(not self.collecting and self.scene.frame_current == 1 and self.scene.frame_subframe == 0.,
                'Full restoration proof only outside timing at the verified saved frame1')
        with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
            self.window.view_layer.update()
            proof = self.shared.check_frame(self.scene, self.contract, 1)
            require(proof['exact'] is True and proof['frame'] == 1 and len(proof['meshes']) == 69
                    and all(row['exact'] is True and not row['changed_components'] for row in proof['meshes']),
                    'Complete cached actor no longer matches accepted source geometry')
            animation = self.shared.animation_state(self.scene, self.contract)
            require(animation == self.contract['portable_animation'], 'Stored animation/bindings differ at saved frame1')
            closure = self.shared.check_serialized_dependencies(self.scene, self.contract)
            require(closure.get('exact') is True, 'Serialized Scene/dependency closure differs')
            parts = {'complete69_cache': proof, 'portable_animation': animation,
                     'serialized_dependency_closure': closure,
                     'cache_binding': self.shared.check_binding(self.scene, self.contract),
                     'mesh_visibility': self.visibility_state()}
            return {'sha256': self.witness.object_hash(parts),
                    'components': {key: self.witness.object_hash(value) for key, value in parts.items()},
                    'mesh_names': sorted(row['target_name'] for row in self.contract['objects']),
                    'rig_names': [], 'rig_pose_scope': 'Unclaimed separately; cache world geometry and declared animation are covered.',
                    'context': self.context_state()}

    def finish(self, error=None):
        global SESSION
        if self.closed:
            return
        self.collecting = False
        self.report['observed_frame_advances'] = {
            'frame_change': observed_advances(self.post_events),
            'changed_post_pixel_tokens': observed_advances(core.changed_draw_events(self.draw_events))}
        try:
            super().finish(error)
        finally:
            if SESSION is self:
                SESSION = None


def install(config):
    """Root's Console entry in the already verified private GUI; never launches."""
    global SESSION
    import bpy
    require(SESSION is None and core.SESSION is None, 'Another playback probe already owns a session')
    controller = CacheProbe(config)
    SESSION = core.SESSION = controller
    try:
        bpy.app.timers.register(controller.timer, first_interval=.1)
    except BaseException:
        controller.finish(traceback.format_exc())
        raise
    return controller
