"""Write a current artist Scene and its dependencies to an isolated test file."""
import bpy
import hashlib
import json
from pathlib import Path
from character_designer import body_original_mode, forearm_original_inventory

out = Path(r'D:\Blender\Projects\Character\X\validation\original_rig_return_20261011')
scene = bpy.data.scenes['Scene']
rig = bpy.data.objects['CoshaRig']
assert body_original_mode.active(rig)
body_original_mode._validate_session_rest(rig)
forearm_original_inventory.validate(rig)

def signature():
    return [bpy.data.filepath, bpy.data.is_dirty, bpy.context.scene.name,
        bpy.context.scene.frame_current, bpy.context.scene.frame_subframe,
        bpy.context.object.name if bpy.context.object else None,
        bpy.context.object.mode if bpy.context.object else None,
        sorted(o.name for o in bpy.context.selected_objects),
        sorted(o.name for o in bpy.data.objects), sorted(a.name for a in bpy.data.actions),
        [(p.name, [(c.name, c.mute, c.influence) for c in p.constraints]) for p in rig.pose.bones],
        rig[body_original_mode.SESSION]]

before = signature()
test_file = out / 'original_scene_current_isolated.blend'
assert test_file.resolve() != Path(bpy.data.filepath).resolve()
bpy.data.libraries.write(str(test_file), {scene}, fake_user=True, compress=False)
receipt = {'artist_filepath': bpy.data.filepath, 'isolated_scene': scene.name,
           'snapshot_path': str(test_file), 'snapshot_bytes': test_file.stat().st_size,
           'snapshot_sha256': hashlib.sha256(test_file.read_bytes()).hexdigest(),
           'state_unchanged': signature() == before, 'artist_dirty': bpy.data.is_dirty,
           'operation': 'libraries.write; current artist file was not saved or switched'}
(out / 'snapshot_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
assert receipt['state_unchanged']
print(json.dumps(receipt))
