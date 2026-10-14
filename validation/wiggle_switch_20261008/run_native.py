"""Preload the frozen release so tests cannot import held canonical changes."""
import argparse
import runpy
from pathlib import Path
import sys

args = sys.argv[sys.argv.index('--') + 1:]
test = Path(args[0]).resolve()
HERE = Path(__file__).resolve().parent
addons = HERE / 'approved_release_0775' / 'addons'
sys.path.insert(0, str(addons))
import character_designer
assert Path(character_designer.__file__).resolve().parent.parent == addons.resolve()
assert character_designer.bl_info['version'] == (0, 77, 5)
sys.argv = [str(test), '--', *args[1:]]
runpy.run_path(str(test), run_name='__main__')
