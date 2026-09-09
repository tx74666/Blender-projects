import bpy,json,sys
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend')
report={}
for n in ('Strap2.001','Wide Strap.001','Line.001','Strap.001_SplineIK_Curve.001','Cosha'):
 o=bpy.data.objects[n];report[n]={'visible':o.visible_get(),'hide_viewport':o.hide_viewport,'hide_render':o.hide_render,'parent':o.parent.name if o.parent else None,'parent_type':o.parent_type,'parent_bone':o.parent_bone,'matrix_world':[list(r) for r in o.matrix_world],'collections':[{'name':c.name,'hide_viewport':c.hide_viewport,'hide_render':c.hide_render} for c in o.users_collection],'modifiers':[{'name':m.name,'type':m.type,'target':getattr(getattr(m,'object',None),'name',None),'subtarget':getattr(m,'subtarget',None)} for m in o.modifiers],'constraints':[{'type':c.type,'target':getattr(getattr(c,'target',None),'name',None)} for c in o.constraints]}
def layer(l,p=False):
 hidden=p or l.exclude or l.hide_viewport or l.collection.hide_viewport
 if l.name=='ShoeDone_Backup':report['layer']={'exclude':l.exclude,'hide_viewport':l.hide_viewport,'effectively_hidden':hidden}
 for child in l.children:layer(child,hidden)
layer(bpy.context.view_layer.layer_collection)
m=bpy.data.objects['Cosha'].data;report['loose_vertices']={i:len([p for p in m.polygons if i in p.vertices]) for i in (3574,3575)}
print('ROOT_ATTACHMENT_VISIBILITY',json.dumps(report),flush=True)
from pathlib import Path
Path(r'D:\Blender\Projects\Character\X\outputs\rig\root_attachment_visibility.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
