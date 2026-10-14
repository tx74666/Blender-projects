"""Run relevant existing tests on the exact frozen release source."""
import importlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
SOURCE = HERE / 'release_07721' / 'character_designer'
sys.path.insert(0, str(REPO / 'tests'))
suite = unittest.TestSuite()
for name in ('test_animation_worklist_ui', 'test_animation_worklist_collection', 'test_animation_worklist'):
    module = importlib.import_module(name)
    module.SOURCE = SOURCE
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
for name, attr, source in (('test_animation_workspace', 'workspace', SOURCE / 'animation_workspace.py'),
                            ('test_animation_worklist_queue', 'queue', SOURCE / 'animation_worklist_queue.py')):
    module = importlib.import_module(name)
    spec = importlib.util.spec_from_file_location('_frozen_' + attr, source)
    runtime = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runtime
    spec.loader.exec_module(runtime)
    setattr(module, attr, runtime)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
(HERE / 'tests.log').write_text(stream.getvalue(), encoding='utf-8')
report = {'passed': result.wasSuccessful(), 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'source': str(SOURCE)}
(HERE / 'tests.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
if not result.wasSuccessful():
    print(stream.getvalue()[-5000:])
    raise SystemExit(1)
