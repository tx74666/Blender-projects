import bpy, sys, json
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import character_setup
cd.register()
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend',use_scripts=False)
rig=bpy.data.objects['CoshaRig']
setup=character_setup.settings(bpy.context)
body=setup.body
rows=[]
for pb in rig.pose.bones:
    bone=pb.bone
    rows.append({'name':pb.name,'parent':bone.parent.name if bone.parent else None,
      'owner':bone.get('character_designer_owner'), 'shape':pb.custom_shape.name if pb.custom_shape else None,
      'head':list(bone.head_local),'tail':list(bone.tail_local),
      'constraints':[(c.name,c.type) for c in pb.constraints],
      'color':pb.color.palette, 'hide':bone.hide,
      'collections':[c.name for c in bone.collections]})
result={'rig':rig.name,'body':body.name if body else None,'bones':rows,'fitting':{}}
if body:
    tr=rig.matrix_world.inverted()@body.matrix_world
    for pb in rig.pose.bones:
        if not any(k in pb.name.lower() for k in ('breast','chest','hips')):continue
        vg=body.vertex_groups.get(pb.name)
        pts=[tr@v.co for v in body.data.vertices if vg and any(g.group==vg.index and g.weight>.1 for g in v.groups)]
        result['fitting'][pb.name]={'count':len(pts),'bounds':[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]] if pts else None}
out=Path(r'D:\Blender\Projects\Character\X\outputs\rig\body_rings_0524_audit.json')
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print('BODY_RINGS_AUDIT',json.dumps(result),flush=True)
