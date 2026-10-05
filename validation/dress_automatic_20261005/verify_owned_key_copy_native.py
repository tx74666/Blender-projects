"""Factory-only native copied-Key cleanup regression, no artist loaded."""
import bpy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

assert bpy.app.background and '--factory-startup' in sys.argv and not bpy.data.filepath
module_path = Path(r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\mesh_copy.py')
assert hashlib.sha256(module_path.read_bytes()).hexdigest() == 'a43aabff39a1ed9525df53352b859943a5571edeb30405d34338a5bebf264150'
spec = importlib.util.spec_from_file_location('qa_mesh_copy', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
assert folder.is_relative_to(Path(__file__).resolve().parent) and not folder.exists()
folder.mkdir()

def table():
    return {key.name: [key.as_pointer(), key.users] for key in bpy.data.shape_keys}

mesh = bpy.data.meshes.new('QA Key Source Mesh')
mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0)], [], [(0,1,2)])
source = bpy.data.objects.new('QA Key Source', mesh)
bpy.context.scene.collection.objects.link(source)
source.shape_key_add(name='Basis', from_mix=False)
key = source.shape_key_add(name='Asymmetric', from_mix=False)
key.data[1].co.z = .1
key.value = .3
before = table()
coordinates = [[list(point.co) for point in block.data] for block in mesh.shape_keys.key_blocks]
checks = []
for fake in (False, True):
    mesh.shape_keys.use_fake_user = fake
    expected = table()
    duplicate = source.copy()
    duplicate.data = mesh.copy()
    bpy.context.scene.collection.objects.link(duplicate)
    owned = duplicate.data
    module.clear_copied_shape_keys(source, duplicate)
    assert owned.shape_keys is None and table() == expected
    bpy.data.objects.remove(duplicate, do_unlink=True)
    bpy.data.meshes.remove(owned)
    assert coordinates == [[list(point.co) for point in block.data] for block in mesh.shape_keys.key_blocks]
    assert key.value == .3 or abs(key.value - .3) < 1.e-7
    checks.append({'fake_user': fake, 'source_keys_exact': True, 'owned_orphan_count': 0})
mesh.shape_keys.use_fake_user = False
assert table() == before
duplicate = source.copy()
duplicate.data = mesh.copy()
bpy.context.scene.collection.objects.link(duplicate)
owned = duplicate.data
foreign = bpy.data.objects.new('QA External Key Reference', None)
bpy.context.scene.collection.objects.link(foreign)
foreign['qa_key_reference'] = owned.shape_keys
copied_key = owned.shape_keys
try:
    module.clear_copied_shape_keys(source, duplicate)
except ValueError:
    assert owned.shape_keys == copied_key and source.data.shape_keys == mesh.shape_keys
else:
    raise AssertionError('Outside native Key reference accepted')
del foreign['qa_key_reference']
bpy.data.objects.remove(foreign, do_unlink=True)
module.clear_copied_shape_keys(source, duplicate)
bpy.data.objects.remove(duplicate, do_unlink=True)
bpy.data.meshes.remove(owned)
assert table() == before
checks.append({'outside_native_reference_rejected': True, 'source_keys_exact': True})
result = bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'KeyCopyQA.blend'), check_existing=False)
assert result == {'FINISHED'}
facts = {'success': True, 'runtime': bpy.app.version_string, 'checks': checks, 'native_save': sorted(result)}
(folder / 'result.json').write_text(json.dumps(facts, indent=2), encoding='utf-8')
print(json.dumps(facts), flush=True)
