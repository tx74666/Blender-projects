"""Run one existing native fixture suite against the frozen candidate only.

Root owns launching Blender. This runner refuses foreground artist sessions.
"""
import argparse
from pathlib import Path
import runpy
import sys


HERE = Path(__file__).resolve().parent
REPOSITORY = Path('D:/MyRepository/Blender-addons-by-Randy')
CANDIDATE = HERE / 'forearm_roll_07712_runtime/character_designer'
MANIFEST = CANDIDATE.parent / 'release_projection_07712.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    test = (REPOSITORY / 'tests' / args.test).resolve()
    if (test.parent != (REPOSITORY / 'tests').resolve() or not test.is_file()
            or not test.name.startswith(('test_forearm_', 'test_unity_forearm_'))):
        raise ValueError('Choose one existing Forearm fixture suite in the repository tests directory.')
    import bpy
    if not bpy.app.background:
        raise ValueError('Native fixtures require a disposable background Blender, never the artist UI.')
    sys.path.insert(0, str(REPOSITORY / 'tools'))
    from release_projection import load_source
    source = load_source('character_designer', MANIFEST, root=REPOSITORY)
    if source.version != '0.77.12' or source.root != CANDIDATE.resolve():
        raise ValueError('The frozen native test input differs from this candidate.')
    sys.path[:0] = [str(CANDIDATE.parent), str(REPOSITORY / 'tests')]
    import character_designer
    if Path(character_designer.__file__).resolve().parent != CANDIDATE.resolve():
        raise ValueError('Blender already imported another Character Designer runtime.')
    # The suites may prepend canonical tests/addons paths. Preloading this
    # package fixes all relative runtime imports to the verified frozen tree.
    print('FROZEN_FOREARM_NATIVE_INPUT', source.projection_sha256, test.name, flush=True)
    sys.argv = [str(test)]
    runpy.run_path(str(test), run_name='__main__')


if __name__ == '__main__':
    main()
