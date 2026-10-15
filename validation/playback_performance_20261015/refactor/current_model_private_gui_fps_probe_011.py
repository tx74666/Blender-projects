"""Current SaveCopy baseline admission; sealed009 normal playback machinery.

The constructor's two legacy admission branches are removed explicitly, and
V5 is replaced with the reviewedV9 helper. No original module or pin is changed.
Root alone installs in a new owned GUI after actual normal startup011 PASS.
"""
import ast
import copy
import hashlib
import importlib
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
CORE_PATH = HERE/'private_gui_fps_probe_009.py'
CORE_SHA = 'a6ce26f86c4fa6aee5dc58fc68f59010a12c9983324133f56e01e2ab2db471ed'
INPUT_PATH = HERE/'mesh_cache_current_input_007.py'
INPUT_SHA = '24468bd93de3ed4b63f2a6e2ab6354f299bfe191d714cde3ff39e55a5b415a90'
STARTUP_PATH = HERE/'native_current_baseline_gui_011.py'
STARTUP_SHA = '6be987d7fa9f8926ce87bbd8102b2ae057e3c25f32512d0ea1399031595240f0'
STAGE = HERE/'staged_20261015_06'
MANIFEST_SHA = '5c7965ef74e99ed8036bc57ad639cb4db37e6501bb580483a676d4b2fd6cc3c0'
SESSION = None
for path, sha in ((CORE_PATH, CORE_SHA), (INPUT_PATH, INPUT_SHA),
    (HERE/'mesh_cache_private_gui_fps_probe_005.py', 'f0982d415695d1e61ebc0d581933b616efde32c8529b1c6634aad382ee097264'),
    (HERE/'native_validation_support_v9.py', '55f4b4b75a2ff5991f250d845fbbb295e7ef153874fb03dbeb7f169b5c048ed5'),
    (HERE/'native_artifact_action_witness_008.py', 'c6881b78c9de8af661b6ecbf264e4e8a4f9861ce645246d9e8dccb1fc298b680')):
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise RuntimeError('Reviewed current baseline dependency changed: '+path.name)
sys.path.insert(0, str(HERE))
import private_gui_fps_probe_009 as core
import mesh_cache_current_input_007 as current
import mesh_cache_private_gui_fps_probe_005 as cache_tools
require, pin = core.require, core.pin
require(Path(core.__file__).resolve() == CORE_PATH and Path(current.__file__).resolve() == INPUT_PATH,
        'Different current baseline helper imported')
STARTUP_FLAGS = ('current_snapshot_verified', 'normal_source_frame1_settled', 'readonly_v9_witness_completed',
    'readonly_context_unchanged', 'normal_handlers_unchanged', 'own_timer_removed',
    'factory_layout_retained', 'addon_left_registered', 'current_dependencies_unchanged')


def validate_config(config, current_pid):
    fields = {'expected_pid', 'private_blend', 'private_sha256', 'private_bytes', 'artist', 'addons',
        'source_manifest', 'source_manifest_sha256', 'mode', 'kind', 'report',
        'snapshot_report', 'snapshot_report_sha256', 'startup_report', 'startup_report_sha256'}
    require(isinstance(config, dict) and set(config) == fields, 'Explicit current-baseline CONFIG required')
    require(type(config['expected_pid']) is int and config['expected_pid'] == current_pid and current_pid > 0,
            'Fresh owned baseline GUI PID required')
    require(config['kind'] == 'current-baseline' and config['mode'] in {'SOLID', 'MATERIAL'}, 'Explicit current baseline mode required')
    require(type(config['private_bytes']) is int and config['private_bytes'] > 0, 'Actual current input byte length required')
    for name in ('private_blend', 'artist', 'addons', 'source_manifest', 'report', 'snapshot_report', 'startup_report'):
        require(isinstance(config[name], str) and config[name], 'Nonempty current baseline path required')
    for name in ('private_sha256', 'source_manifest_sha256', 'snapshot_report_sha256', 'startup_report_sha256'):
        require(cache_tools.valid_sha(config[name]), 'Invalid current baseline SHA')
    require(Path(config['addons']).resolve() == STAGE/'addons'
        and Path(config['source_manifest']).resolve() == STAGE/'source_manifest.json'
        and config['source_manifest_sha256'] == MANIFEST_SHA, 'Matching Stage06 authoring package required')
    return dict(config)


def validate_startup(report, pid, snapshot_pin, receipt_pin):
    require(report.get('schema') == 'x.current-private-baseline-gui/1' and report.get('completed') is True
        and report.get('pid') == pid and report.get('errors') == [] and all(report.get(key) is True for key in STARTUP_FLAGS),
        'Actual same-PID normal current baseline startup PASS required')
    require(report.get('input_before') == snapshot_pin and report.get('current_snapshot_receipt') == receipt_pin,
        'Baseline startup used another current SaveCopy')
    require(report.get('script') == pin(STARTUP_PATH) and report['script']['sha256'] == STARTUP_SHA,
        'Different current startup source')
    require(report.get('settled_scene', {}).get('frame') == 1 and report['settled_scene'].get('subframe') == 0.,
        'Current baseline startup must restore private frame1')


def sealed_constructor():
    tree = ast.parse(CORE_PATH.read_text(encoding='utf8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Probe')
    node = copy.deepcopy(next(item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name == '__init__'))
    removed = []
    kept = []
    for item in node.body:
        if isinstance(item, ast.If) and ast.unparse(item.test) in {"config['kind'] == 'baseline'", "config['kind'] == 'baked'"}:
            removed.append(ast.unparse(item.test))
        else:
            kept.append(item)
    require(set(removed) == {"config['kind'] == 'baseline'", "config['kind'] == 'baked'"} and len(removed) == 2,
            'Expected exactly the two sealed legacy admission branches')
    node.body = kept
    changed = 0
    for item in ast.walk(node):
        if isinstance(item, ast.Constant) and item.value in {'native_validation_support_v5', 'native_validation_support_v5.py'}:
            item.value = item.value.replace('_v5', '_v9')
            changed += 1
    require(changed == 2, 'Expected only V5 import/path literals')
    scope = dict(vars(core))
    scope['validate_config'] = validate_config
    # Preserve core009's __file__: its finish re-pins that exact original core.
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(CORE_PATH), 'exec'), scope)
    return scope['__init__'], {'removed_legacy_branches': removed, 'v5_to_v9_literal_changes': changed,
        'constructor_ast_sha256': hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()}


_initialize, EXTRACTION = sealed_constructor()


VIEW_FIELDS = ('area_size', 'region_size', 'sync_mode', 'clip', 'fps', 'fps_base_hex', 'shading', 'overlays',
    'sidebar', 'toolbar', 'clip_start_hex', 'clip_end_hex', 'view_location', 'view_rotation',
    'view_distance_hex', 'perspective', 'lens_hex', 'local_view', 'render_engine')


def comparison_view(context):
    require(context['perspective'] in {'PERSP', 'ORTHO'} and not context['local_view'], 'Non-camera full-scene view required')
    return {key: context[key] for key in VIEW_FIELDS}


def scene_settings(scene):
    return tuple(getattr(scene, name) for name in ('frame_start', 'frame_end', 'use_preview_range',
        'frame_preview_start', 'frame_preview_end', 'sync_mode')) + (scene.render.fps, scene.render.fps_base)


def action_witness(scene):
    """V9 complete native Action/owner RNA, one payload at a time, no new bulk implementation."""
    import bpy
    extension = importlib.import_module('native_source_reference_witness_v9')
    reader = extension.Reader(bpy.types.ID)
    actions = {}
    for action in sorted(bpy.data.actions, key=lambda value: value.name_full):
        require(action.name_full not in actions, 'Ambiguous Action names unsupported')
        actions[action.name_full] = extension.object_hash(reader.rna(action, 'Action:'+action.name_full))
    owners = (scene,) + tuple(obj for obj in scene.objects if obj.type == 'ARMATURE')
    controls = {type(owner).__name__+':'+owner.name_full:
        extension.object_hash(reader.rna(owner.animation_data, 'animation:'+owner.name_full))
        if owner.animation_data is not None else None for owner in owners}
    return {'actions': actions, 'scene_and_rig_animation': controls,
        'native_bookkeeping_excluded': sorted(reader.OMIT_ID_FIELDS),
        'bulk_keyframe_collections': reader.bulk_keyframe_collections, 'bulk_keyframe_points': reader.bulk_keyframe_points,
        'scope': 'All actual Actions including unused, complete slots/layers/curves/points and raw/setbits; original Scene/Rig animation owners. V9 representation, process-local references; no portable reopen claim.'}


def sealed_full_state():
    tree = ast.parse(CORE_PATH.read_text(encoding='utf8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Probe')
    node = copy.deepcopy(next(item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name == 'full_state'))
    changed = 0
    for item in ast.walk(node):
        if isinstance(item, ast.Assign) and len(item.targets) == 1 and ast.unparse(item.targets[0]) == "parts['stored_actions']":
            require(ast.unparse(item.value) == 'self.portable.capture(self.scene, tuple(bpy.data.actions))', 'Unexpected stored Action proof')
            item.value = ast.copy_location(ast.parse('action_witness(self.scene)', mode='eval').body, item.value)
            changed += 1
    require(changed == 1, 'Expected exactly one stored Action witness substitution')
    scope = {**vars(core), 'action_witness': action_witness}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(CORE_PATH), 'exec'), scope)
    return scope['full_state'], hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


_full_state, FULL_STATE_AST_SHA = sealed_full_state()


class Probe(core.Probe):
    def __init__(self, config):
        config = validate_config(config, __import__('os').getpid())
        self.snapshot, self.snapshot_receipt_pin = current.load_snapshot(config['snapshot_report'],
            config['snapshot_report_sha256'], config['private_sha256'], config['private_bytes'])
        startup, startup_pin = core.load_pinned_json(config['startup_report'], config['startup_report_sha256'])
        validate_startup(startup, config['expected_pid'], self.snapshot['copy'], self.snapshot_receipt_pin)
        require(Path(config['private_blend']).resolve() == Path(self.snapshot['copy']['path']).resolve(), 'Different current snapshot path')
        self.startup, self.startup_pin = startup, startup_pin
        try:
            _initialize(self, config)
            require(self.handlers_before == startup['callbacks_after_natural_settle'],
                'Normal callback identities/order changed since current startup')
            self.loaded_filepath_literal = __import__('bpy').data.filepath
            self.hot_objects = frozenset((int(obj.as_pointer()), obj.session_uid) for obj in self.scene.objects)
            self.hot_layer = int(self.window.view_layer.as_pointer())
            self.gui_pin = self.snapshot_receipt_pin
            self.artifact_receipt_pin = startup_pin
            self.dependencies.update(current_baseline=pin(__file__), current_input=pin(INPUT_PATH), startup=pin(STARTUP_PATH))
            self.report.update(schema='x.current-private-gui-normal-playback/1', adapter_script=pin(__file__),
                current_snapshot_receipt=self.snapshot_receipt_pin, startup_receipt=startup_pin, input_scope='Current guarded SaveCopy at capture timestamp; no later artist edit equivalence.',
                adapter_extraction=EXTRACTION, full_state_ast_sha256=FULL_STATE_AST_SHA,
                model=None, reasoning_effort=None, model_source='Unrecorded for this new entry.',
                gpu_context_before_timing=cache_tools.gpu_context_info(),
                proof_representation='V9 native complete Action RNA/15field bulk plus unchanged mesh/key/rig/registered proof; same representation at both endpoints.')
            self.report.pop('gui008', None)
            self.report['inherited_receipt_pin_fields'] = {'gui_pin': 'Current guarded SaveCopy receipt',
                'artifact_receipt_pin': 'Current normal baseline startup receipt'}
            self.report['loaded_addon_version'] = list(self.addon.bl_info['version'])
            self.flush()
        except BaseException:
            if hasattr(self, 'stream'):
                self.stream.close()
            raise

    def assert_runtime(self):
        super().assert_runtime()
        identity = self.snapshot['source_identity']
        require(self.scene.name_full == identity['scene'] and self.window.view_layer.name == identity['view_layer'],
                'Current source Scene/View Layer differs')
        require(any(obj.type == 'MESH' and self.runtime.RECORD_KEY in obj for obj in self.scene.objects),
                'Actual normal authoring baseline required')

    def assert_owned(self):
        if not self.collecting:
            return super().assert_owned()
        import bpy
        require(__import__('os').getpid() == self.config['expected_pid'] and bpy.data.filepath == self.loaded_filepath_literal
            and self.window.screen == self.screen and self.window.scene == self.scene
            and any(area == self.area for area in self.screen.areas) and self.area.type == 'VIEW_3D', 'Owned baseline context changed')
        self.assert_runtime()
        require(int(self.window.view_layer.as_pointer()) == self.hot_layer and self.area.spaces.active.region_3d.view_perspective in {'PERSP', 'ORTHO'}
            and frozenset((int(obj.as_pointer()), obj.session_uid) for obj in self.scene.objects) == self.hot_objects
            and scene_settings(self.scene) == self.hot_scene_settings,
            'Baseline View Layer/Object membership changed')

    def full_state(self):
        state = _full_state(self)
        require(self.scene.frame_current == 1 and self.scene.frame_subframe == 0., 'Aligned baseline frame1 required')
        require(self.area.spaces.active.shading.type == self.config['mode'], 'Prewarm and align the requested shading before install')
        view = comparison_view(state['context'])
        if not self.closed:
            self.report['comparison_view'] = view
            self.hot_scene_settings = scene_settings(self.scene)
        else:
            self.report['comparison_view_after_exact'] = view == self.report['comparison_view']
            require(self.report['comparison_view_after_exact'], 'Comparable baseline viewport changed')
        return state

    def finish(self, error=None):
        global SESSION
        if self.closed:
            return
        self.collecting = False
        self.report['observed_frame_advances'] = {'frame_change': cache_tools.observed_advances(self.post_events),
            'changed_post_pixel_tokens': cache_tools.observed_advances(core.changed_draw_events(self.draw_events))}
        try:
            super().finish(error)
        finally:
            if SESSION is self:
                SESSION = None


def install(config):
    global SESSION
    import bpy
    require(SESSION is None and core.SESSION is None and cache_tools.SESSION is None, 'Another GUI probe owns a session')
    controller = Probe(config)
    SESSION = core.SESSION = controller
    try:
        bpy.app.timers.register(controller.timer, first_interval=.1)
    except BaseException:
        controller.finish(traceback.format_exc())
        raise
    return controller
