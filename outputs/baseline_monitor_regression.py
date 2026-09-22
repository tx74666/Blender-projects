"""Verify the new idle regression fails against the pre-fix functions."""
import ast
import sys
from pathlib import Path

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\tests')
import test_finger_monitor_idle_blender as test

source = Path(r'C:\Users\Randy\AppData\Local\Temp\cd-monitor-fix-baseline-20260920\finger_workflow_ui.py')
tree = ast.parse(source.read_text(encoding='utf-8'))
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'_show', '_refresh'}]
namespace = dict(test.ui.__dict__)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
for node in nodes:
    getattr(test.ui, node.name).__code__ = namespace[node.name].__code__
test.character_designer.register()
for name in ('test_unprepared_active_finger_skips_mesh_proof_and_settles',
             'test_stale_prepared_source_settles_and_actual_restoration_revalidates'):
    try:
        getattr(test, name)()
    except AssertionError as exc:
        print('EXPECTED_BASELINE_FAILURE', name, str(exc), flush=True)
    else:
        raise AssertionError('Baseline unexpectedly passed: '+name)
print('BASELINE_REGRESSION_CONFIRMED', flush=True)
