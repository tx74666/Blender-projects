import bpy, json
from pathlib import Path
scene = bpy.data.scenes['Animation Worklist · Cosha']
users = bpy.data.user_map()
rows = [{'object': obj.name, 'type': obj.type,
         'users': [{'type': owner.bl_rna.identifier, 'name': owner.name}
                   for owner in users.get(obj, set())],
         'scene_names': [s.name for s in obj.users_scene]}
        for obj in scene.objects]
report = {'scenes': list(bpy.data.scenes.keys()), 'objects': rows}
Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011\cleanup_users_before_migration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
