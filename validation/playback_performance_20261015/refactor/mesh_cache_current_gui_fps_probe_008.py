"""Current-cache FPS adapter: sealed005 playback plus006 native Base guards.

Only private class namespaces select the current contract and actual mesh
count. No original module is patched. Root installs in a genuinely verified
owned cache GUI; this entry never opens/saves a file or launches Blender.
"""
import ast
import copy
import hashlib
import importlib
from pathlib import Path
import sys
import traceback
import types

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE/'mesh_cache_private_gui_fps_probe_005.py'
BASE_SHA = 'f0982d415695d1e61ebc0d581933b616efde32c8529b1c6634aad382ee097264'
VISIBILITY_PATH = HERE/'mesh_cache_private_gui_fps_probe_006.py'
VISIBILITY_SHA = 'a192d0ef91e780d2f490c29ed5bfa648c14e0f54ab19599b8e10d741dcecdec6'
BASELINE_PATH = HERE/'current_model_private_gui_fps_probe_011.py'
BASELINE_SHA = 'a130ac3a263165d0b9691f976d86c94daef7ea6532ad0b11e6311d39f40b39e3'
CONTRACT_PATH = HERE/'mesh_cache_current_contract_008.py'
CONTRACT_SHA = '768696ca5af847103485b9da3b48b7cd1517bf2b850092b6673a50c3c28bf5eb'
GUI_PATH = HERE/'mesh_cache_current_reopen_gui_008.py'
GUI_SHA = '053baf1c5a9c89b04d7018bf75ce5bfde1ce4c301a6418d609835c4f919671e5'
SOURCE_SEAL_PATH = HERE/'current_cache_sources_008.json'
SOURCE_SEAL_SHA = '8fbffc3763e21efc694ea5775aa96c3ca43ad20d74a63e2e680d8c84789e8665'
GUI_SCHEMA = 'x.current-pc2-artifact-gui-reopen/1'
SESSION = None
for path, expected in ((BASE_PATH, BASE_SHA), (VISIBILITY_PATH, VISIBILITY_SHA), (BASELINE_PATH, BASELINE_SHA)):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Reviewed playback adapter changed: '+path.name)
sys.path.insert(0, str(HERE))
import mesh_cache_private_gui_fps_probe_005 as original
import mesh_cache_private_gui_fps_probe_006 as visibility
import current_model_private_gui_fps_probe_011 as baseline
core, require, pin = original.core, original.require, original.pin
require(all(Path(module.__file__).resolve() == path for module, path in (
    (original, BASE_PATH), (visibility, VISIBILITY_PATH), (baseline, BASELINE_PATH))), 'Foreign playback adapter module')
CURRENT_FLAGS = ('current_snapshot_provenance_verified', 'current_materials_all_frames_exact',
    'current_material_resources_initial_exact', 'current_material_resources_after_exact',
    'current_material_saved_frame_exact', 'adapter_visibility_gui_unchanged')
BINDING_FLAGS = ('adapter_current_gui_unchanged', 'current_binding_verified', 'current_binding_unchanged')
GUI_FLAGS = original.GUI_FLAGS + visibility.VISIBILITY_FLAGS + CURRENT_FLAGS + BINDING_FLAGS


def validate_gui(receipt, pid, artifact_pin):
    require(receipt.get('schema') == GUI_SCHEMA and receipt.get('completed') is True
        and receipt.get('pid') == pid and 'error' not in receipt and receipt.get('cleanup_errors') == [],
        'Actual completed current cache GUI receipt from this private PID required')
    require(all(receipt.get(key) is True for key in GUI_FLAGS), 'Current GUI lifecycle/material/visibility proof incomplete')
    require(receipt.get('artifact') == artifact_pin, 'Current GUI verified another private artifact')
    count = receipt.get('expected_mesh_count')
    require(type(count) is int and count > 0, 'Explicit actual current mesh count required')
    frames, visible, shaders = (receipt.get(key) for key in ('frames', 'visibility_frames', 'shader_frames'))
    require(all(isinstance(rows, list) and [row.get('frame') for row in rows] == list(range(1, 31))
        for rows in (frames, visible, shaders)), 'Complete current geometry/visibility/shader1-30 visits required')
    for row, vis, shader in zip(frames, visible, shaders):
        require(row.get('full_current_geometry_exact') is True and row.get('mesh_count') == count
            and row.get('current_layer_visibility_exact') is True and row.get('visibility_exact') is True
            and row.get('shader_exact') is True and original.valid_sha(row.get('check_sha256'))
            and original.valid_sha(row.get('shader_sha256')) and vis.get('exact') is True
            and shader.get('exact') is True and shader.get('sha256') == row['shader_sha256']
            and vis.get('check_sha256') == shader.get('check_sha256') == row['check_sha256'],
            'Current per-frame full actor/material/visibility proof differs')
    return receipt['callbacks_after_natural_settle']


def routed_import(name, package=None):
    return importlib.import_module(CONTRACT_PATH.stem if name == 'mesh_cache_artifact_contract_005' else name, package)


def private_classes():
    """Three count literals only; every006 class method AST stays unchanged."""
    base_source, layer_source = BASE_PATH.read_bytes(), VISIBILITY_PATH.read_bytes()
    require(hashlib.sha256(base_source).hexdigest() == BASE_SHA
        and hashlib.sha256(layer_source).hexdigest() == VISIBILITY_SHA, 'Sealed playback source changed')
    base_class = copy.deepcopy(next(node for node in ast.parse(base_source.decode('utf8')).body
        if isinstance(node, ast.ClassDef) and node.name == 'CacheProbe'))
    count_changes = 0
    class Counts(ast.NodeTransformer):
        def visit_Constant(self, node):
            nonlocal count_changes
            if type(node.value) is int and node.value == 69:
                count_changes += 1
                return ast.copy_location(ast.parse('self.expected_mesh_count', mode='eval').body, node)
            return node
    base_class = Counts().visit(base_class)
    require(count_changes == 3, 'Expected exactly three sealed mesh-count checks')
    ast.fix_missing_locations(base_class)
    scope = dict(vars(original))
    scope.update(__file__=str(Path(__file__).resolve()), CONTRACT_PATH=CONTRACT_PATH, CONTRACT_SHA=CONTRACT_SHA,
        GUI_PATH=GUI_PATH, GUI_SHA=GUI_SHA, validate_gui=validate_gui,
        importlib=types.SimpleNamespace(import_module=routed_import))
    exec(compile(ast.Module(body=[base_class], type_ignores=[]), str(BASE_PATH), 'exec'), scope)
    base_class_object = scope['CacheProbe']
    base_ast = hashlib.sha256(ast.dump(base_class, include_attributes=False).encode()).hexdigest()
    constructor = next(node for node in base_class.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
    constructor_ast = hashlib.sha256(ast.dump(constructor, include_attributes=False).encode()).hexdigest()
    layer_class = next(node for node in ast.parse(layer_source.decode('utf8')).body
        if isinstance(node, ast.ClassDef) and node.name == 'CacheProbe')
    layer_scope = dict(vars(visibility))
    layer_scope.update(__file__=str(Path(__file__).resolve()), _sealed_init=base_class_object.__init__,
        original=types.SimpleNamespace(CacheProbe=base_class_object), BASE_CONSTRUCTOR_AST_SHA=constructor_ast,
        CONTRACT_PATH=CONTRACT_PATH, CONTRACT_SHA=CONTRACT_SHA, GUI_PATH=GUI_PATH, GUI_SHA=GUI_SHA)
    exec(compile(ast.Module(body=[layer_class], type_ignores=[]), str(VISIBILITY_PATH), 'exec'), layer_scope)
    return base_class_object, layer_scope['CacheProbe'], {'mesh_count_literal_changes': count_changes,
        'base_class_ast_sha256': base_ast,
        'base_constructor_ast_sha256': constructor_ast,
        'visibility_class_ast_sha256': hashlib.sha256(ast.dump(layer_class, include_attributes=False).encode()).hexdigest(),
        'unchanged': '005 timing/playback/callbacks/cleanup and006 whole visibility class; three count constants now actual contract size.'}


_BaseProbe, _VisibilityProbe, EXTRACTION = private_classes()


class CacheProbe(_VisibilityProbe):
    @property
    def expected_mesh_count(self):
        return len(self.contract['objects'])

    def __init__(self, config):
        super().__init__(config)
        try:
            require(self.expected_mesh_count > 0 and self.receipt['schema'] == 'x.current-pc2-artifact/1'
                and self.contract['schema'] == 'x.current-pc2-artifact-contract/1', 'Actual nonempty current publication required')
            expected_seal = pin(SOURCE_SEAL_PATH)
            require(expected_seal['sha256'] == SOURCE_SEAL_SHA
                and self.receipt['current_source_seal'] == expected_seal, 'Reviewed current source seal differs')
            sources = self.shared.verify_sources(expected_seal)
            require(sources == self.receipt['current_sources'], 'Current source dependency inventory differs')
            gui, observed = core.load_pinned_json(self.gui_pin['path'], self.gui_pin['sha256'])
            require(observed == self.gui_pin and gui['expected_mesh_count'] == self.expected_mesh_count
                and gui['current_snapshot_receipt'] == self.receipt['current_snapshot_receipt']
                and gui['current_input'] == self.receipt['input_before'], 'GUI/current SaveCopy provenance differs')
            require(self.receipt['current_snapshot_receipt'] == self.contract['current_snapshot_receipt'],
                'Publication/reopen snapshot receipt differs')
            for name, path in (('sealed_fps005', BASE_PATH), ('sealed_fps006', VISIBILITY_PATH),
                ('baseline011_view_comparator', BASELINE_PATH), ('current_source_seal', SOURCE_SEAL_PATH)):
                self.dependencies[name] = pin(path)
            self.dependencies.update({'current_source:'+name: value for name, value in sources.items()})
            self.dependencies['current_snapshot_receipt'] = self.receipt['current_snapshot_receipt']
            self.dependencies['current_input_copy'] = self.receipt['input_before']
            self.report.update(schema='x.current-pc2-private-gui-normal-playback/1',
                adapter_visibility_probe=pin(VISIBILITY_PATH), adapter_extraction=EXTRACTION,
                current_gui=self.report.pop('gui006'), expected_mesh_count=self.expected_mesh_count,
                current_snapshot_receipt=self.receipt['current_snapshot_receipt'], current_input=self.receipt['input_before'],
                current_source_seal=expected_seal, current_snapshot_provenance_verified=True,
                model=None, reasoning_effort=None, model_source='Unrecorded for this new entry.',
                current_material_saved_frame_initial_exact=False, current_material_saved_frame_after_exact=False,
                current_material_resources_initial_exact=False, current_material_resources_after_exact=False,
                comparison_view_after_exact=False,
                inherited_component_aliases={'complete69_cache': 'Legacy component label; the actual current contract mesh count and shader proof are checked.'},
                inherited_cleanup_aliases={'all_mesh_key_pose_raw_action_outputs_exact':
                    'Current actual-count complete Mesh geometry/world/normals/attributes, declared portable animation, shader graph/parameters/resources and Base/bindings; no separate full rig-pose/ShapeKey/pixel proof.'})
            self.report['limits'].append('Input is the actual guarded current SaveCopy at its timestamp; later artist edits and shader pixels/implicit coordinates are unverified. Same input provenance and comparison_view are required before comparing with baseline011.')
            self.flush()
        except BaseException:
            self.stream.close()
            raise

    def full_state(self):
        state = super().full_state()
        require(self.area.spaces.active.shading.type == self.config['mode'],
            'Root must select and prewarm the requested comparison shading before installation')
        # super005's exact current check_frame includes shader_exact; its
        # animation_state verifies the captured live resource readers first.
        require(self.shared.verify_shader_resources(self.scene, self.contract) is True,
            'Current material resource verification failed')
        view = baseline.comparison_view(state['context'])
        if self.closed:
            require(self.report.get('comparison_view') == view, 'Comparable viewport did not restore exactly')
            self.report.update(current_material_saved_frame_after_exact=True,
                current_material_resources_after_exact=True, comparison_view_after_exact=True)
        else:
            self.report.update(comparison_view=view, current_material_saved_frame_initial_exact=True,
                current_material_resources_initial_exact=True)
        return state

    def finish(self, error=None):
        global SESSION
        if self.closed:
            return
        try:
            super().finish(error)
        finally:
            if SESSION is self:
                SESSION = None


def install(config):
    """Root's existing owned-cache Console entry, after actual current GUI PASS."""
    global SESSION
    import bpy
    require(SESSION is None and original.SESSION is None and visibility.SESSION is None and core.SESSION is None,
        'Another normal playback probe already owns a session')
    controller = CacheProbe(config)
    SESSION = core.SESSION = controller
    try:
        bpy.app.timers.register(controller.timer, first_interval=.1)
    except BaseException:
        controller.finish(traceback.format_exc())
        raise
    return controller
