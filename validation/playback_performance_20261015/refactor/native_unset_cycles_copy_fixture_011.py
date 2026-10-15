"""Fixed Stage10 factory proof using sealed010 diagnosis in owned globals."""
import ast
import hashlib
import importlib
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE/'native_unset_cycles_copy_fixture_010.py'
BASE_SHA = '4688f47225758c35bed33dcecc3e60a5ce09ed2097b4967bea25ff05a6d444b2'
STAGE = HERE/'staged_20261015_10'
MANIFEST_SHA = 'e1859b8b56ca5b63a5c91dcec0e4fed9d9da48d1bffa30263b191692ebed91c4'
SCENE_SHA = 'be291c9e70e7de4160027300ba7c4d7d4ac56ea86738e6ba9aecbd1af0360cb2'
SCHEMA = 'x.native-unset-cycles-copy-fixture/2'
FLAGS = ('direct_copy_preserves_state', 'builder_preserves_state', 'source_after_direct_copy_exact',
    'source_after_build_exact', 'source_after_close_exact', 'stored_value_preserved')
if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != BASE_SHA:
    raise RuntimeError('Sealed diagnostic010 changed')
sys.path.insert(0, str(HERE))
import native_unset_cycles_copy_fixture_010 as original
require = original.require
require(Path(original.__file__).resolve() == BASE_PATH, 'Foreign diagnostic module')


def private_main():
    require(hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() == BASE_SHA, 'Sealed diagnostic010 changed')
    scope = dict(vars(original))
    scope.update(__file__=str(Path(__file__).resolve()), STAGE=STAGE,
        MANIFEST_SHA=MANIFEST_SHA, SCENE_SHA=SCENE_SHA)
    return types.FunctionType(original.main.__code__, scope, original.main.__name__,
        original.main.__defaults__, original.main.__closure__)


_factory = private_main()


def main(args, report):
    report.update(schema=SCHEMA, fixture_adapter=original.base.pin(BASE_PATH),
        diagnostic_only=True, fixed_stage10_preserves_unset_pg=False,
        scope='Own factory World/Material copy versus Stage10 builder; no shader-domain/current-model/performance acceptance.')
    _factory(args, report)
    # The copied010 cleanup checked the overridden STAGE10 pins. Rename its
    # literal label honestly, without altering a native operation or guard.
    report['cleanup']['stage10_unchanged'] = report['cleanup'].pop('stage09_unchanged')
    report['fixture_adapter_unchanged'] = original.base.pin(BASE_PATH) == report['fixture_adapter']
    require(all(report.get(key) is True for key in FLAGS)
        and report.get('reproduced_remapper_materialization') is False
        and report['fixture_adapter_unchanged'], 'Stage10 did not preserve factory unset/stored PG state')
    report['fixed_stage10_preserves_unset_pg'] = True


def entry():
    require(hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() == BASE_SHA, 'Sealed diagnostic010 changed')
    tree = ast.parse(BASE_PATH.read_bytes())
    block = next(node for node in tree.body if isinstance(node, ast.If)
        and ast.dump(node.test, include_attributes=False) == ast.dump(
            ast.parse("__name__ == '__main__'", mode='eval').body, include_attributes=False))
    scope = dict(vars(original))
    scope.update(globals())
    exec(compile(ast.Module(body=block.body, type_ignores=[]), str(BASE_PATH), 'exec'), scope)


if __name__ == '__main__':
    entry()
