import bpy
import importlib.util
import json
from pathlib import Path
out = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
spec = importlib.util.spec_from_file_location('verify0540', out / 'validate_bone_display_0540.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
v.cd.register()
bpy.ops.wm.open_mainfile(filepath=str(v.FIXTURE), use_scripts=False)
rig = bpy.data.objects['CoshaRig']
v.activate(rig)
before = v.capture_current(details=True)
v.modules()['bone_collections'].simplify_body_collections(rig)
after = v.capture_current(details=True)
diff = []
def compare(a,b,path):
    if type(a) != type(b):
        diff.append([path,a,b]); return
    if isinstance(a,dict):
        for k in set(a)|set(b):
            if k not in a or k not in b: diff.append([path+'/'+str(k),a.get(k),b.get(k)])
            else: compare(a[k],b[k],path+'/'+str(k))
    elif isinstance(a,(list,tuple)):
        if len(a)!=len(b): diff.append([path,a,b]); return
        for i,(x,y) in enumerate(zip(a,b)): compare(x,y,path+'/'+str(i))
    elif a!=b: diff.append([path,a,b])
compare(before['details']['objects'],after['details']['objects'],'objects')
(out/'bone_display_0540_object_delta.json').write_text(json.dumps(diff,indent=2),encoding='utf-8')
print('OBJECT_DELTA',json.dumps(diff)[:20000], 'OBJECT',before['details']['objects'][7][:3],flush=True)
