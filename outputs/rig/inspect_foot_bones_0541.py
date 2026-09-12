import bpy, json
from pathlib import Path
rig=bpy.data.objects['CoshaRig']
rows=[]
for b in rig.data.bones:
    p=rig.pose.bones[b.name]
    rows.append({'name':b.name,'parent':b.parent.name if b.parent else None,
      'head':list(p.head),'tail':list(p.tail),'rest_head':list(b.head_local),'rest_tail':list(b.tail_local),
      'deform':b.use_deform,'hide':b.hide,'hide_select':b.hide_select,'visible':not b.hide and (not b.collections or any(c.is_visible_effectively for c in b.collections)),
      'collections':[c.name for c in b.collections], 'props':dict(b.items()),
      'shape':p.custom_shape.name if p.custom_shape else None,'pose_scale':list(p.scale),'pose_matrix':[list(row) for row in p.matrix],
      'constraints':[{'type':c.type,'name':c.name,'target':getattr(getattr(c,'target',None),'name',None),'subtarget':getattr(c,'subtarget',None)} for c in p.constraints]})
out={'mode':bpy.context.mode,'frame':bpy.context.scene.frame_current,'filepath':bpy.data.filepath,'display_type':rig.data.display_type,'show_shapes':rig.data.show_bone_custom_shapes,'bones':rows,'collections':[{'name':c.name,'visible':c.is_visible,'effective':c.is_visible_effectively,'parent':c.parent.name if c.parent else None} for c in rig.data.collections_all], 'view':rig.data.get('character_designer_bone_display_view_v1')}
Path(r'D:\Blender\Projects\Character\X\outputs\rig\original_shin_live_inspect.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
print('FOOT_INSPECT_DONE')
