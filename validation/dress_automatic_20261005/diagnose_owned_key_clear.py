"""Factory-only Blender Key-copy lifecycle diagnostic; no artist loaded."""
import bpy
import json
from pathlib import Path
import sys

assert bpy.app.background and '--factory-startup' in sys.argv and not bpy.data.filepath
folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
assert folder.is_relative_to(Path(__file__).resolve().parent) and not folder.exists()
folder.mkdir()

def table():
    users = bpy.data.user_map()
    return [{'name': key.name, 'pointer': key.as_pointer(), 'users': key.users,
             'fake_user': key.use_fake_user,
             'owners': sorted((type(user).__name__, user.name) for user in users.get(key, set()))}
            for key in bpy.data.shape_keys]

mesh = bpy.data.meshes.new('QA Key Source Mesh')
mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0)], [], [(0,1,2)])
source = bpy.data.objects.new('QA Key Source', mesh)
bpy.context.scene.collection.objects.link(source)
source.shape_key_add(name='Basis', from_mix=False)
key = source.shape_key_add(name='Asymmetric', from_mix=False)
key.data[1].co.z = .1
key.value = .3
facts = {'original': table()}
temporary = source.copy()
temporary.data = source.data.copy()
bpy.context.scene.collection.objects.link(temporary)
owned_key = temporary.data.shape_keys
owned_name, owned_ptr = owned_key.name, owned_key.as_pointer()
facts['copied'] = table()
temporary.shape_key_clear()
facts['cleared'] = table()
facts['copied_mesh_key_after_clear'] = temporary.data.shape_keys.name if temporary.data.shape_keys else None
data = temporary.data
bpy.data.objects.remove(temporary, do_unlink=True)
bpy.data.meshes.remove(data)
facts['removed_mesh'] = table()
remaining = bpy.data.shape_keys.get(owned_name)
if remaining is not None:
    assert remaining.as_pointer() == owned_ptr
    owners = bpy.data.user_map(subset={remaining}).get(remaining, set())
    assert not owners, [(type(owner).__name__, owner.name) for owner in owners]
    bpy.data.batch_remove(ids=(remaining,))
facts['exact_owned_key_cleanup'] = table()
assert facts['exact_owned_key_cleanup'] == facts['original']
result = bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'KeyCopyQA.blend'), check_existing=False)
assert result == {'FINISHED'}
facts['native_save'] = sorted(result)
(folder / 'result.json').write_text(json.dumps(facts, indent=2), encoding='utf-8')
print(json.dumps(facts), flush=True)
