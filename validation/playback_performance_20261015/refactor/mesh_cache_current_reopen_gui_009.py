"""Thin current009 normal-GUI binding over sealed008; no native launch.

Only private namespaces select current009 dependencies. Existing loading,
readiness, frame-yield verification, Base checks and cleanup are unchanged.
"""
import ast
import hashlib
import importlib
from pathlib import Path
import sys
import traceback
import types

HERE = Path(__file__).resolve().parent
PREVIOUS_PATH = HERE/'mesh_cache_current_reopen_gui_008.py'
PREVIOUS_SHA = '053baf1c5a9c89b04d7018bf75ce5bfde1ce4c301a6418d609835c4f919671e5'
CONTRACT_PATH = HERE/'mesh_cache_current_contract_009.py'
CONTRACT_SHA = 'a6c50c83dfdb5cad6c4487f5e7b1cceeabc5d126e1e1fc9f20dba1bb19485532'
SOURCE_SEAL_PATH = HERE/'current_cache_sources_009.json'
SOURCE_SEAL_SHA = '8cc19753b95df9fe1a7c90ec76a60ada673be4fef31282949791d6d2c0f541ee'
SESSION = None
if hashlib.sha256(PREVIOUS_PATH.read_bytes()).hexdigest() != PREVIOUS_SHA:
    raise RuntimeError('Sealed GUI008 source changed')
sys.path.insert(0, str(HERE))
import mesh_cache_current_reopen_gui_008 as previous
require, pin, SCHEMA = previous.require, previous.pin, previous.SCHEMA
require(Path(previous.__file__).resolve() == PREVIOUS_PATH, 'Foreign GUI008 module')


def routed_import(name, package=None):
    return importlib.import_module(CONTRACT_PATH.stem
        if name == 'mesh_cache_artifact_contract_005' else name, package)


def private_binding():
    source = PREVIOUS_PATH.read_bytes()
    require(hashlib.sha256(source).hexdigest() == PREVIOUS_SHA, 'Sealed GUI008 source changed')
    scope = dict(vars(previous))
    scope.update(__file__=str(Path(__file__).resolve()), __name__=__name__,
        CONTRACT_PATH=CONTRACT_PATH, CONTRACT_SHA=CONTRACT_SHA,
        SOURCE_SEAL_PATH=SOURCE_SEAL_PATH, SOURCE_SEAL_SHA=SOURCE_SEAL_SHA, routed_import=routed_import)
    factory = types.FunctionType(previous.private_class.__code__, scope,
        previous.private_class.__name__, previous.private_class.__defaults__, previous.private_class.__closure__)
    scope['_CurrentSession'], scope['EXTRACTION'] = factory()
    cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'ReopenSession')
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(PREVIOUS_PATH), 'exec'), scope)
    return scope['ReopenSession'], scope, {
        'previous_binding_class_ast_sha256': hashlib.sha256(ast.dump(cls, include_attributes=False).encode()).hexdigest(),
        'changes': 'Owned globals select contract009/source seal009; complete008 binding class and all007/005/006 native lifecycle operations unchanged.'}


_PreviousSession, _OWNED_SCOPE, EXTRACTION = private_binding()


class ReopenSession(_PreviousSession):
    def __init__(self, args, stream, report):
        super().__init__(args, stream, report)
        self.report.update(adapter_previous_gui=pin(PREVIOUS_PATH), previous_binding_extraction=EXTRACTION,
            adapter_previous_gui_unchanged=False)

    def finish(self, error=None):
        if self.finished:
            return
        try:
            self.report['adapter_previous_gui_unchanged'] = pin(PREVIOUS_PATH) == self.report['adapter_previous_gui']
            require(self.report['adapter_previous_gui_unchanged'], 'Sealed GUI008 binding source changed')
        except BaseException:
            extra = traceback.format_exc()
            error = error+'\nCurrent009 binding:\n'+extra if error else extra
        super().finish(error)


def main():
    # GUI008.main executes the unchanged007 CLI/error block in this owned
    # namespace. Synchronize the ordinary diagnostic SESSION even on failure.
    _OWNED_SCOPE['ReopenSession'] = ReopenSession
    entry = types.FunctionType(previous.main.__code__, _OWNED_SCOPE,
        previous.main.__name__, previous.main.__defaults__, previous.main.__closure__)
    try:
        entry()
    finally:
        globals()['SESSION'] = _OWNED_SCOPE.get('SESSION')


if __name__ == '__main__':
    main()
