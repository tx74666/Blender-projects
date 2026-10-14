import bpy,json
from pathlib import Path
scene=bpy.data.scenes['Animation Worklist · Cosha']
out={'scene':scene.name,'objects':[],'collections':[]}
for obj in scene.objects:
    out['objects'].append({'name':obj.name,'type':obj.type,'scenes':[s.name for s in obj.users_scene],'collections':[c.name for c in obj.users_collection],'data':obj.data.name if obj.data else None,'keys':list(obj.keys()),'action':obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None})
for c in scene.collection.children:
    out['collections'].append({'name':c.name,'users':c.users,'objects':[obj.name for obj in c.all_objects],'keys':list(c.keys())})
Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011\cleanup_scope.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
