import bpy
C=bpy.context
main=C.area
other=next(a for a in C.screen.areas if a.type=='VIEW_3D' and a!=main)
view=other.spaces.active.region_3d
values={k:getattr(view,k).copy() if hasattr(getattr(view,k),'copy') else getattr(view,k) for k in ('view_distance','view_location','view_rotation','view_perspective')}
main.type='VIEW_3D'
for key,value in values.items(): setattr(main.spaces.active.region_3d,key,value)
main.tag_redraw()
