"""Thin current008 normal-GUI binding; Root alone launches a fresh GUI.

The sealed007 class and entry block retain the normal005/006 lifecycle,
ADVANCE/yield/VERIFY loop and cleanup. Only owned namespaces route contract008.
"""
import ast
import hashlib
import importlib
from pathlib import Path
import sys
import traceback
import types

HERE = Path(__file__).resolve().parent
CURRENT_PATH = HERE/'mesh_cache_current_reopen_gui_007.py'
CURRENT_SHA = 'f7f9f81b1262005e0773793a8f8960bf2cce2b11464e92490f030e0882cd63f6'
CONTRACT_PATH = HERE/'mesh_cache_current_contract_008.py'
CONTRACT_SHA = '768696ca5af847103485b9da3b48b7cd1517bf2b850092b6673a50c3c28bf5eb'
SOURCE_SEAL_PATH = HERE/'current_cache_sources_008.json'
SOURCE_SEAL_SHA = '8fbffc3763e21efc694ea5775aa96c3ca43ad20d74a63e2e680d8c84789e8665'
SESSION = None
if hashlib.sha256(CURRENT_PATH.read_bytes()).hexdigest() != CURRENT_SHA:
    raise RuntimeError('Sealed current GUI007 source changed')
sys.path.insert(0, str(HERE))
import mesh_cache_current_reopen_gui_007 as original
require, pin, SCHEMA = original.require, original.pin, original.SCHEMA
require(Path(original.__file__).resolve() == CURRENT_PATH, 'Foreign current GUI module')


def routed_import(name, package=None):
    return importlib.import_module(CONTRACT_PATH.stem
        if name == 'mesh_cache_artifact_contract_005' else name, package)


def sealed_tree():
    source = CURRENT_PATH.read_bytes()
    require(hashlib.sha256(source).hexdigest() == CURRENT_SHA, 'Sealed current GUI007 source changed')
    return ast.parse(source.decode('utf-8'))


def private_class():
    tree = sealed_tree()
    scope = dict(vars(original))
    scope.update(__file__=str(Path(__file__).resolve()), CONTRACT_PATH=CONTRACT_PATH,
        CONTRACT_SHA=CONTRACT_SHA, routed_import=routed_import)
    factory = types.FunctionType(original.private_classes.__code__, scope,
        original.private_classes.__name__, original.private_classes.__defaults__, original.private_classes.__closure__)
    base, layer, extraction = factory()
    scope.update(_BaseSession=base, _VisibilitySession=layer, EXTRACTION=extraction)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ReopenSession')
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(CURRENT_PATH), 'exec'), scope)
    return scope['ReopenSession'], {
        'current_class_ast_sha256': hashlib.sha256(ast.dump(cls, include_attributes=False).encode()).hexdigest(),
        'inherited_extraction': extraction,
        'changes': 'Owned globals route contract008; sealed007 class and005/006 lifecycle methods are unchanged.'}


_CurrentSession, EXTRACTION = private_class()


class ReopenSession(_CurrentSession):
    def __init__(self, args, stream, report):
        super().__init__(args, stream, report)
        source_seal = pin(SOURCE_SEAL_PATH)
        require(source_seal['sha256'] == SOURCE_SEAL_SHA
            and self.receipt['current_source_seal'] == source_seal, 'Current008 source seal differs')
        require(pin(CONTRACT_PATH)['sha256'] == CONTRACT_SHA, 'Current008 contract source changed')
        require(self.helper.verify_sources(source_seal) == self.receipt['current_sources'],
            'Current008 explicit source inventory differs')
        self.report.update(adapter_current_gui=pin(CURRENT_PATH), adapter_current_extraction=EXTRACTION,
            current_source_seal=source_seal, current_binding_verified=True,
            adapter_current_gui_unchanged=False, current_binding_unchanged=False)

    def finish(self, error=None):
        if self.finished:
            return
        try:
            self.report['adapter_current_gui_unchanged'] = (
                pin(CURRENT_PATH) == self.report['adapter_current_gui'])
            self.report['current_binding_unchanged'] = (
                pin(CONTRACT_PATH)['sha256'] == CONTRACT_SHA
                and pin(SOURCE_SEAL_PATH) == self.report['current_source_seal'])
            require(all(self.report.get(name) is True for name in ('current_binding_verified',
                'adapter_current_gui_unchanged', 'current_binding_unchanged')), 'Current008 GUI binding changed')
        except BaseException:
            extra = traceback.format_exc()
            error = error+'\nCurrent008 binding:\n'+extra if error else extra
        super().finish(error)


def main():
    """Execute the pinned007 CLI/report/error boundary with only this class bound."""
    tree = sealed_tree()
    block = next(node for node in tree.body if isinstance(node, ast.If)
        and ast.dump(node.test, include_attributes=False) == ast.dump(
            ast.parse("__name__ == '__main__'", mode='eval').body, include_attributes=False))
    scope = dict(vars(original))
    scope.update(globals())
    try:
        exec(compile(ast.Module(body=block.body, type_ignores=[]), str(CURRENT_PATH), 'exec'), scope)
    finally:
        globals()['SESSION'] = scope.get('SESSION')


if __name__ == '__main__':
    main()
