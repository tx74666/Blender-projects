import bpy
import json
from datetime import datetime
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\outputs\memory_health')
for job in ('RENDER', 'RENDER_PREVIEW', 'OBJECT_BAKE'):
    if bpy.app.is_job_running(job):
        raise RuntimeError('Wait for current Blender job to finish: ' + job)
usage = json.loads((out / 'image_usage.json').read_text(encoding='utf8'))
targets = [item['name'] for item in usage['buffer_candidates']]
images=[]
for name in targets:
    im = bpy.data.images.get(name)
    if im is None or im.source != 'FILE' or not im.packed_file or im.is_dirty:
        raise RuntimeError('Image no longer meets safe release requirements: ' + name)
    materials=[mat for mat in bpy.data.materials if name in usage['materials'][mat.name]['images']]
    if not materials or any(mat.users != 1 or not mat.use_fake_user for mat in materials):
        raise RuntimeError('Material is now used: ' + name)
    images.append(im)
before={im.name:{'loaded':im.has_data,'users':im.users,'packed_size':im.packed_file.size} for im in images}
for im in images:
    im.buffers_free()
after={im.name:{'loaded':im.has_data,'users':im.users,'packed_size':im.packed_file.size} for im in images}
assert all(not entry['loaded'] for entry in after.values())
assert all(before[name]['users']==after[name]['users'] and before[name]['packed_size']==after[name]['packed_size'] for name in targets)
report={'time':datetime.now().isoformat(),'operation':'buffers_free only; no datablocks removed','before':before,'after':after,
        'counts':{name:len(getattr(bpy.data,name)) for name in ('objects','meshes','materials','images','actions','armatures')},
        'frame':bpy.context.scene.frame_current,'filepath':bpy.data.filepath}
(out/'cache_release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('Released',len(images),'inactive image buffers; all packed data and references preserved.')
