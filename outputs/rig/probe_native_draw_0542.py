import bpy,json
from pathlib import Path
rig=bpy.data.objects['CoshaRig']
out=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
def data():
    result={}
    for tag,obj in [('original',rig),('evaluated',rig.evaluated_get(bpy.context.evaluated_depsgraph_get()))]:
        result[tag]={}
        for name in ['shin.L','shin.R','MCH_foot_tip.L','MCH_foot_tip.R']:
            pb=obj.pose.bones[name]
            result[tag][name]={
              'hide':pb.bone.hide,'hide_select':pb.bone.hide_select,'shape':pb.custom_shape.name if pb.custom_shape else None,
              'shape_transform':pb.custom_shape_transform.name if pb.custom_shape_transform else None,
              'shape_scale':list(pb.custom_shape_scale_xyz),'shape_translation':list(pb.custom_shape_translation),
              'head':list(pb.head),'tail':list(pb.tail),
              'collection_visible':[(c.name,c.is_visible,c.is_visible_effectively) for c in pb.bone.collections],
              'props':{p.identifier:str(getattr(pb.bone,p.identifier)) for p in pb.bone.bl_rna.properties if p.identifier not in {'rna_type'}}}
    return result
before=data()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'X_original_draw_0542_live_input.blend'),copy=True)
rig.data.update_tag()
rig.update_tag(refresh={'OBJECT','DATA'})
bpy.context.view_layer.update()
bpy.context.evaluated_depsgraph_get().update()
after=data()
(out/'native_draw_0542_probe.json').write_text(json.dumps({'before':before,'after':after},indent=2),encoding='utf-8')
if bpy.context.area.type=='CONSOLE':bpy.context.area.type='VIEW_3D'
for win in bpy.context.window_manager.windows:
    for area in win.screen.areas:area.tag_redraw()
print('NATIVE_DRAW_PROBE_DONE')
