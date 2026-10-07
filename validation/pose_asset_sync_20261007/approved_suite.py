"""Run a repository test against the exact frozen approved release payload."""
import os
import runpy
import sys
from pathlib import Path

source = Path(os.environ['POSE_APPROVED_SOURCE_ROOT']).resolve()
test = Path(os.environ['POSE_APPROVED_TEST']).resolve()
sys.path.insert(0, str(source))
import character_designer
assert Path(character_designer.__file__).resolve() == source / 'character_designer' / '__init__.py'
print('POSE_APPROVED_TEST_SOURCE', character_designer.__file__, flush=True)
sys.argv = [str(test)]
runpy.run_path(str(test), run_name='__main__')
