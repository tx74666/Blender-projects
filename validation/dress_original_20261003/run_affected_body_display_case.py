"""Rerun only the revised Original-period Dress channel snapshot assertion."""
from pathlib import Path
import sys
import unittest

root = Path('D:/MyRepository/Blender-addons-by-Randy')
sys.path[:0] = [str(root / 'addons'), str(root / 'tests')]
from test_body_original_mode_blender import OriginalTests

suite = unittest.TestSuite((OriginalTests(
    'test_unified_original_groups_and_explicit_modes_preserve_pose'),))
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print('PASS Body Original affected native-display case', flush=True)
