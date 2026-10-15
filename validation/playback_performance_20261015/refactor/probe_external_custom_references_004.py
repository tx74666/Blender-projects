"""Read private saved-copy custom references; no addon, scene write or save."""
import hashlib
import json
from pathlib import Path
import bpy

root = Path(__file__).resolve().parent
input_path = root.parents[1] / 'playback_performance_20261014/round4/input_saved_20261015.blend'
if hashlib.sha256(input_path.read_bytes()).hexdigest() != '40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721':
    raise RuntimeError('Private input pin changed')
bpy.ops.wm.open_mainfile(filepath=str(input_path))
scene = bpy.context.scene
members = set(scene.objects)
rows = []

def walk(group, path):
    try:
        items = tuple(group.items())
    except (TypeError, AttributeError):
        return
    for name, value in items:
        current = path + '/' + str(name)
        if isinstance(value, bpy.types.Object):
            if value not in members:
                rows.append({'path': current, 'object': value.name_full,
                             'type': value.type, 'scenes': [item.name_full for item in value.users_scene],
                             'library': value.library.filepath if value.library else None})
        elif not isinstance(value, bpy.types.ID) and hasattr(value, 'items'):
            walk(value, current)

walk(scene, 'Scene:' + scene.name_full)
for obj in scene.objects:
    walk(obj, 'Object:' + obj.name_full)
    if obj.data is not None:
        walk(obj.data, 'Data:' + obj.data.name_full)
    if obj.type == 'ARMATURE':
        for bone in obj.data.bones:
            walk(bone, obj.name_full + '/Bone:' + bone.name)
        for bone in obj.pose.bones:
            walk(bone, obj.name_full + '/Pose:' + bone.name)
report = {'schema': 'x.private-external-custom-references/1', 'input': str(input_path),
          'scene': scene.name_full, 'references': rows, 'no_addon_register': True,
          'no_scene_save': True, 'limits': 'Serialized custom properties only; not full RNA dependency closure.'}
output = root / 'external_custom_references_004.json'
if output.exists():
    raise RuntimeError('Do not overwrite evidence')
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False), flush=True)
