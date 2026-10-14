"""Run existing relevant UI/collection/state checks against the frozen payload."""
import importlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
SOURCE = HERE / 'release_07719' / 'character_designer'
sys.path.insert(0, str(REPO / 'tests'))
suite = unittest.TestSuite()
for name in ('test_animation_worklist_ui', 'test_animation_worklist_collection', 'test_animation_worklist'):
    module = importlib.import_module(name)
    module.SOURCE = SOURCE
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
queue_tests = importlib.import_module('test_animation_worklist_queue')
spec = importlib.util.spec_from_file_location('_frozen_worklist_queue', SOURCE / 'animation_worklist_queue.py')
queue_tests.queue = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = queue_tests.queue
spec.loader.exec_module(queue_tests.queue)
suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(queue_tests))
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
(HERE / 'tests.log').write_text(stream.getvalue(), encoding='utf-8')
(HERE / 'tests.json').write_text(json.dumps({'passed': result.wasSuccessful(), 'tests': result.testsRun,
             'failures': len(result.failures), 'errors': len(result.errors), 'source': str(SOURCE)}, indent=2), encoding='utf-8')
print(stream.getvalue()[-4500:])
if not result.wasSuccessful():
    raise SystemExit(1)
