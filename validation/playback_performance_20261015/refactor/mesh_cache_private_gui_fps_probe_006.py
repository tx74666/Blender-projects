"""Sealed FPS005 clocks plus the published cache visibility contract.

Only its constructor is compiled in private globals to select reviewed006
dependencies. Existing timing, callbacks, normal playback and restoration stay
in the original classes. Root installs this in the verified private GUI only.
"""
import ast
import hashlib
import importlib
from pathlib import Path
import sys
import traceback
import types

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE/'mesh_cache_private_gui_fps_probe_005.py'
BASE_SHA = 'f0982d415695d1e61ebc0d581933b616efde32c8529b1c6634aad382ee097264'
CONTRACT_PATH = HERE/'mesh_cache_artifact_contract_006.py'
CONTRACT_SHA = '176877414933e79ae6776c3fefc78dca69e60011d79daab292102b12a326bfc8'
GUI_PATH = HERE/'mesh_cache_artifact_reopen_gui_006.py'
GUI_SHA = '0002e7b85769b7249f542039a9c12000fdb9fee33ea4f211422063e94e3a0703'
SESSION = None

if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != BASE_SHA:
    raise RuntimeError('Sealed FPS005 changed')
sys.path.insert(0, str(HERE))
import mesh_cache_private_gui_fps_probe_005 as original
if Path(original.__file__).resolve() != BASE_PATH:
    raise RuntimeError('Another FPS005 module imported')
core, require, pin = original.core, original.require, original.pin
VISIBILITY_FLAGS = ('visibility_initial_exact', 'visibility_after_exact',
    'visibility_current_layer_all_frames_exact', 'source_active_view_layer_restored')


def validate_gui(receipt, pid, artifact_pin):
    require(receipt.get('schema') == 'x.pc2-actor-artifact-gui-reopen/2'
            and receipt.get('completed') is True and receipt.get('pid') == pid
            and 'error' not in receipt and receipt.get('cleanup_errors') == [],
            'Actual completed GUI006 receipt from this private PID required')
    require(all(receipt.get(key) is True for key in original.GUI_FLAGS+VISIBILITY_FLAGS),
            'GUI006 lifecycle/geometry/visibility proof incomplete')
    require(receipt.get('artifact') == artifact_pin, 'GUI006 artifact differs from the loaded private file')
    frames, visibility = receipt.get('frames'), receipt.get('visibility_frames')
    require(isinstance(frames, list) and isinstance(visibility, list)
            and [row.get('frame') for row in frames] == list(range(1, 31))
            and [row.get('frame') for row in visibility] == list(range(1, 31)),
            'GUI006 complete1-30 geometry/visibility visits required')
    for row, visible in zip(frames, visibility):
        require(row.get('full69_geometry_exact') is True and row.get('mesh_count') == 69
                and row.get('current_layer_visibility_exact') is True
                and original.valid_sha(row.get('check_sha256')) and visible.get('exact') is True
                and visible.get('check_sha256') == row['check_sha256'],
                'GUI006 per-frame geometry/visibility proof differs')
    return receipt['callbacks_after_natural_settle']


def routed_import(name, package=None):
    return importlib.import_module('mesh_cache_artifact_contract_006'
        if name == 'mesh_cache_artifact_contract_005' else name, package)


def sealed_constructor():
    source = BASE_PATH.read_bytes()
    require(hashlib.sha256(source).hexdigest() == BASE_SHA, 'Sealed FPS005 changed')
    tree = ast.parse(source.decode('utf-8'))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CacheProbe']
    require(len(classes) == 1, 'Expected one sealed cache probe class')
    nodes = [node for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name == '__init__']
    require(len(nodes) == 1, 'Expected one sealed cache constructor')
    scope = dict(vars(original))
    scope.update(__file__=str(Path(__file__).resolve()), CONTRACT_PATH=CONTRACT_PATH,
        CONTRACT_SHA=CONTRACT_SHA, GUI_PATH=GUI_PATH, GUI_SHA=GUI_SHA, validate_gui=validate_gui,
        importlib=types.SimpleNamespace(import_module=routed_import))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(BASE_PATH), 'exec'), scope)
    return scope['__init__'], hashlib.sha256(ast.dump(nodes[0], include_attributes=False).encode()).hexdigest()


_sealed_init, BASE_CONSTRUCTOR_AST_SHA = sealed_constructor()


class CacheProbe(original.CacheProbe):
    def __init__(self, config):
        _sealed_init(self, config)
        try:
            self.dependencies['base_cache_probe005'] = pin(BASE_PATH)
            self.report.update(schema='x.pc2-private-gui-normal-playback/2',
                adapter_base_probe=pin(BASE_PATH), adapter_constructor_ast_sha256=BASE_CONSTRUCTOR_AST_SHA,
                gui006=self.report.pop('gui005'), visibility_initial_exact=True,
                visibility_after_exact=False, source_active_view_layer=self.contract['visibility']['context_view_layer'],
                visibility_scope='Full expected Base/selection/Collection table checked before/after; current-layer flags and collection topology checked by literal RNA during timer polls.')
            self.flush()
        except BaseException:
            self.stream.close()
            raise

    def assert_runtime(self):
        super().assert_runtime()
        require(self.window.view_layer.name == self.contract['visibility']['context_view_layer'],
                'Saved source context View Layer changed')
        result = self.shared.check_visibility(self.scene, self.contract, all_layers=True)
        require(result.get('exact') is True, 'Full source visibility table differs')

    def capture_hot_bindings(self):
        super().capture_hot_bindings()
        state = self.contract['visibility']
        require(state.get('schema') == 'character-designer.private-view-layer-state/1', 'Wrong visibility contract')
        self.hot_layer = self.scene.view_layers[state['context_view_layer']]
        self.hot_layer_pointer = int(self.hot_layer.as_pointer())
        expected = [row for row in state['layers'] if row['name'] == state['context_view_layer']]
        require(len(expected) == 1, 'Unique saved context View Layer required')
        expected = expected[0]
        self.hot_visibility = tuple((self.hot_layer.objects[row['name']], row['name'],
            int(self.hot_layer.objects[row['name']].as_pointer()), self.hot_layer.objects[row['name']].session_uid,
            row['hidden'], row['selected']) for row in expected['objects'])
        self.hot_active = self.hot_layer.objects.get(expected['active']) if expected['active'] is not None else None
        require((self.hot_active is not None) == (expected['active'] is not None), 'Saved active Object missing')
        objects, seen = {}, set()
        def walk(collection):
            pointer = int(collection.as_pointer())
            if pointer in seen:
                return
            seen.add(pointer)
            require(collection.name_full not in objects, 'Ambiguous Collection name in visibility contract')
            objects[collection.name_full] = collection
            for child in collection.children:
                walk(child)
        walk(self.scene.collection)
        require(set(objects) == {row['name'] for row in state['collection_hide_select']}, 'Collection inventory differs')
        self.hot_collections = tuple((objects[row['name']], row['name'], int(objects[row['name']].as_pointer()),
            objects[row['name']].session_uid, row['hide_select'],
            frozenset(int(child.as_pointer()) for child in objects[row['name']].children))
            for row in state['collection_hide_select'])
        self.hot_master = self.scene.collection
        self.assert_hot_bindings()

    def assert_hot_bindings(self):
        super().assert_hot_bindings()
        import bpy
        layer = self.window.view_layer
        require(int(layer.as_pointer()) == self.hot_layer_pointer
                and int(bpy.context.view_layer.as_pointer()) == self.hot_layer_pointer
                and layer.name == self.contract['visibility']['context_view_layer'],
                'Source context View Layer changed during playback')
        require({(int(obj.as_pointer()), obj.session_uid) for obj in layer.objects}
                == {(row[2], row[3]) for row in self.hot_visibility}, 'Context-layer Object membership changed')
        require(layer.objects.active is self.hot_active, 'Context-layer active Object changed')
        for obj, name, pointer, uid, hidden, selected in self.hot_visibility:
            require(int(obj.as_pointer()) == pointer and obj.session_uid == uid and obj.name_full == name
                    and bool(obj.hide_get(view_layer=layer)) == hidden
                    and bool(obj.select_get(view_layer=layer)) == selected, 'Context-layer hiding/selection changed')
        require(self.scene.collection is self.hot_master, 'Scene master Collection changed')
        for collection, name, pointer, uid, hidden_select, children in self.hot_collections:
            require(int(collection.as_pointer()) == pointer and collection.session_uid == uid
                    and collection.name_full == name and bool(collection.hide_select) == hidden_select
                    and frozenset(int(child.as_pointer()) for child in collection.children) == children,
                    'Collection membership/selectability changed')

    def full_state(self):
        state = super().full_state()
        result = self.shared.check_visibility(self.scene, self.contract, all_layers=True)
        require(result.get('exact') is True, 'Full restored visibility table differs')
        parts = {'sealed005': state['sha256'], 'visibility': self.contract['visibility'], 'visibility_check': result}
        state['sha256'] = self.witness.object_hash(parts)
        state['components']['source_view_layer_state'] = self.witness.object_hash(parts['visibility'])
        if self.closed:
            self.report['visibility_after_exact'] = True
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
    """Root Console entry; requires real006 published+reopen receipts, no launch."""
    global SESSION
    import bpy
    require(SESSION is None and original.SESSION is None and core.SESSION is None,
            'Another playback probe already owns a session')
    controller = CacheProbe(config)
    SESSION = original.SESSION = core.SESSION = controller
    try:
        bpy.app.timers.register(controller.timer, first_interval=.1)
    except BaseException:
        controller.finish(traceback.format_exc())
        raise
    return controller
