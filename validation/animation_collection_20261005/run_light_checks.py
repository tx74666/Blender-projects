from pathlib import Path
import contextlib
import json
import sys
import time
import unittest

root = Path('D:/MyRepository/Blender-addons-by-Randy')
here = Path(__file__).resolve().parent
patterns = ['test_animation_worklist.py', 'test_animation_worklist_ui.py',
            'test_animation_worklist_queue.py', 'test_animation_worklist_fingerprint.py',
            'test_animation_worklist_collection.py', 'test_animation_workspace.py',
            'test_animation_link.py', 'test_animation_link_performance.py', 'test_animation_link_source_images.py']
suite = unittest.TestSuite(unittest.defaultTestLoader.discover(str(root / 'tests'), pattern=p) for p in patterns)
started = time.perf_counter()
with (here / 'light_checks.log').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    result = unittest.TextTestRunner(stream=log, verbosity=1).run(suite)
report = {'passed': result.wasSuccessful(), 'tests': result.testsRun, 'failures': len(result.failures),
          'errors': len(result.errors), 'seconds': time.perf_counter() - started, 'patterns': patterns,
          'native': False, 'installed': False, 'model': 'unrecorded', 'reasoning_effort': 'unrecorded'}
(here / 'light_checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
raise SystemExit(not result.wasSuccessful())
