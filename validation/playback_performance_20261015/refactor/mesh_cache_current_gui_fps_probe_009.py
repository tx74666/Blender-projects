"""Current009 receipt binding over the frozen008 normal GUI FPS adapter.

No timing, callbacks, native health, state restoration or comparison-view
algorithm changes. Only private class globals select current009 dependencies.
"""
import ast
import hashlib
import importlib
from pathlib import Path
import sys
import traceback
import types

HERE = Path(__file__).resolve().parent
PREVIOUS_PATH = HERE/'mesh_cache_current_gui_fps_probe_008.py'
PREVIOUS_SHA = '9f1b630b6613560912bb4f39d0ed01d6f47095b3cbe2b5c8b1012a1006f3d5b1'
CONTRACT_PATH = HERE/'mesh_cache_current_contract_009.py'
CONTRACT_SHA = 'a6c50c83dfdb5cad6c4487f5e7b1cceeabc5d126e1e1fc9f20dba1bb19485532'
GUI_PATH = HERE/'mesh_cache_current_reopen_gui_009.py'
GUI_SHA = '3f60b61750e78cf58d3ec1de2fdb43118a72b1aa29d1c81ef8b6e3f59871f99b'
SOURCE_SEAL_PATH = HERE/'current_cache_sources_009.json'
SOURCE_SEAL_SHA = '8cc19753b95df9fe1a7c90ec76a60ada673be4fef31282949791d6d2c0f541ee'
SESSION = None
if hashlib.sha256(PREVIOUS_PATH.read_bytes()).hexdigest() != PREVIOUS_SHA:
    raise RuntimeError('Frozen current FPS008 changed')
sys.path.insert(0, str(HERE))
import mesh_cache_current_gui_fps_probe_008 as previous
core, require, pin = previous.core, previous.require, previous.pin
require(Path(previous.__file__).resolve() == PREVIOUS_PATH, 'Foreign FPS008 module')
GUI_FLAGS = previous.GUI_FLAGS + ('adapter_previous_gui_unchanged',)


def validate_gui(receipt, pid, artifact_pin):
    callbacks = previous.validate_gui(receipt, pid, artifact_pin)
    require(receipt.get('adapter_previous_gui_unchanged') is True,
        'Current GUI009 previous-binding source proof incomplete')
    return callbacks


def routed_import(name, package=None):
    return importlib.import_module(CONTRACT_PATH.stem
        if name == 'mesh_cache_artifact_contract_005' else name, package)


def private_binding():
    source = PREVIOUS_PATH.read_bytes()
    require(hashlib.sha256(source).hexdigest() == PREVIOUS_SHA, 'Frozen current FPS008 changed')
    scope = dict(vars(previous))
    scope.update(__file__=str(Path(__file__).resolve()), __name__=__name__,
        CONTRACT_PATH=CONTRACT_PATH, CONTRACT_SHA=CONTRACT_SHA, GUI_PATH=GUI_PATH, GUI_SHA=GUI_SHA,
        SOURCE_SEAL_PATH=SOURCE_SEAL_PATH, SOURCE_SEAL_SHA=SOURCE_SEAL_SHA,
        routed_import=routed_import, validate_gui=validate_gui, GUI_FLAGS=GUI_FLAGS)
    factory = types.FunctionType(previous.private_classes.__code__, scope,
        previous.private_classes.__name__, previous.private_classes.__defaults__, previous.private_classes.__closure__)
    scope['_BaseProbe'], scope['_VisibilityProbe'], scope['EXTRACTION'] = factory()
    cls = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == 'CacheProbe')
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(PREVIOUS_PATH), 'exec'), scope)
    return scope['CacheProbe'], {
        'previous_binding_class_ast_sha256': hashlib.sha256(ast.dump(cls, include_attributes=False).encode()).hexdigest(),
        'inherited_extraction': scope['EXTRACTION'],
        'changes': 'Only owned globals bind current009 contract/GUI/source seal; complete008 class and005/006 health/009 timing/011 comparison remain unchanged.'}


_PreviousProbe, EXTRACTION = private_binding()


class CacheProbe(_PreviousProbe):
    def __init__(self, config):
        super().__init__(config)
        try:
            self.dependencies['previous_current_fps008'] = pin(PREVIOUS_PATH)
            self.report.update(adapter_previous_fps=pin(PREVIOUS_PATH), previous_binding_extraction=EXTRACTION,
                previous_binding_final_gate='The existing proof_dependencies_exact cleanup flag rechecks this frozen008 source together with current009 dependencies.')
            self.flush()
        except BaseException:
            self.stream.close()
            raise

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
    """Root's same owned-cache Console entry, after actual current GUI009 PASS."""
    global SESSION
    import bpy
    require(SESSION is None and previous.SESSION is None and previous.original.SESSION is None
        and previous.visibility.SESSION is None and core.SESSION is None, 'Another normal playback probe owns a session')
    controller = CacheProbe(config)
    SESSION = core.SESSION = controller
    try:
        bpy.app.timers.register(controller.timer, first_interval=.1)
    except BaseException:
        controller.finish(traceback.format_exc())
        raise
    return controller
