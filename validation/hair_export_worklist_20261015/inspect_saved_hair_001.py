"""Read-only proof comparison on the pinned saved X in a disposable process."""
import ast
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import bpy

HERE = Path(__file__).resolve().parent
ARTIST = HERE.parents[1] / 'X.blend'
EXPECTED = '468bb6b297c56dd4b9c5f2dcd171ac240e31b9e87c4d6af998a1f64e76aafd29'
REPORT = HERE / 'saved_hair_diagnosis_001.json'
assert bpy.app.background and '--factory-startup' in sys.argv
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
assert hashlib.sha256(ARTIST.read_bytes()).hexdigest() == EXPECTED
assert not REPORT.exists()
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('_x_hair_diagnostic_support', HERE / 'inspect_live_hair.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
source = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and helper.PROFILE in obj)
rig = source[helper.RIG]
before = helper._snapshot(bpy, source)
report = {'schema': 'x.saved-hair-diagnosis/1', 'completed': False,
          'input': {'path': str(ARTIST), 'sha256': EXPECTED, 'bytes': ARTIST.stat().st_size},
          'limits': 'Saved-file diagnostic only; current unsaved geometry and active runtime are not observed.',
          'blender': bpy.app.version_string, 'source': source.name, 'rig': rig.name}
with REPORT.open('x', encoding='utf8') as stream:
    try:
        original, report['adoption'] = helper._authored_data(rig)
        report['chain_flags'] = helper._chain_flags(source, rig, original)
        for label, folder in (
                ('baseline', ARTIST.parent / 'addons' / 'character_designer'),
                ('candidate', HERE / 'release_07743' / 'character_designer')):
            name = '_x_saved_hair_' + label
            package = types.ModuleType(name)
            package.__path__ = [str(folder)]
            package.__package__ = name
            package.__file__ = str(folder / '__init__.py')
            package.bl_info = next(ast.literal_eval(n.value) for n in ast.parse(
                (folder / '__init__.py').read_bytes()).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'bl_info' for t in n.targets))
            sys.modules[name] = package
            registry = importlib.import_module(name + '.hair_strand_registry')
            report[label] = helper._registry_result(registry, source)
            report[label]['version'] = package.bl_info['version']
        after = helper._snapshot(bpy, source)
        report['protected_state_unchanged'] = before == after
        report['before_sha256'] = before['sha256']
        report['after_sha256'] = after['sha256']
        report['artist_disk_unchanged'] = hashlib.sha256(ARTIST.read_bytes()).hexdigest() == EXPECTED
        assert report['protected_state_unchanged'] and report['artist_disk_unchanged']
        assert report['baseline']['ok'] is False and 'connection or ordered parent' in report['baseline']['error']
        assert report['candidate']['ok'] is True
        report['completed'] = True
    finally:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
print(json.dumps(report, ensure_ascii=False), flush=True)
