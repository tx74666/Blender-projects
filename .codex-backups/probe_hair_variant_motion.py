import sys,json,bpy
sys.path.insert(0,r'D:\Blender\Projects\Character\X\addons')
from character_designer import hair_bones_rig as r,hair_bones_variants as v,hair_bones_topology as t
from mathutils import Vector,kdtree

def activate(o,mode='OBJECT'):
 if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
 for x in bpy.context.selected_objects:x.select_set(False)
 o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 if mode!='OBJECT':bpy.ops.object.mode_set(mode=mode)

def points(o):
 bpy.context.view_layer.update();e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
 try:return tuple(e.matrix_world @ x.co for x in m.vertices)
 finally:e.to_mesh_clear()

def nearest(a,b):
 kd=kdtree.KDTree(len(b))
 for i,p in enumerate(b):kd.insert(p,i)
 kd.balance();return max(kd.find(p)[2] for p in a)

for name in ('Hair1','Hair3'):
 s=bpy.data.objects[name];activate(s,'EDIT');bpy.ops.mesh.select_all(action='DESELECT');_,p=t.select_strands(bpy.context)
 # arclength normalized average exactly as grouping service produces
 from character_designer import hair_bones_groups as g
 g.capture_plans(s,p)
 bm=__import__('bmesh').from_edit_mesh(s.data)
 for f in bm.faces:f.select=False
 for e in bm.edges:e.select=False
 seeds={x['layers'][-1][0] for x in p}
 for x in bm.verts:x.select=x.index in seeds
 __import__('bmesh').update_edit_mesh(s.data,loop_triangles=False,destructive=False)
 g.group_selected(bpy.context);_,plans=g.build_plans(bpy.context,mode='GROUPED')
 a=v.build_variant(bpy.context,s,plans,mode='GROUPED',bone_count=3);o=a['mesh'];full0=points(o);mods=[(m,m.show_viewport) for m in o.modifiers if m.type!='ARMATURE']
 for m,_ in mods:m.show_viewport=False
 raw0=points(o)
 for m,flag in mods:m.show_viewport=flag
 pbone=a['armature'].pose.bones[a['chains'][0]['bones'][0]];pbone.rotation_mode='XYZ';pbone.rotation_euler.x=.24
 full1=points(o)
 for m,_ in mods:m.show_viewport=False
 raw1=points(o)
 rawmove=max((x-y).length for x,y in zip(raw0,raw1));fullnearest=max(nearest(full0,full1),nearest(full1,full0))
 print('DEFORMATION_DIAG',json.dumps(dict(source=name,mods=[m.type for m,_ in mods],raw_counts=[len(raw0),len(raw1)],full_counts=[len(full0),len(full1)],raw_max_motion=rawmove,full_nearest_motion=fullnearest,full_index_motion=max((x-y).length for x,y in zip(full0,full1)) if len(full0)==len(full1) else None)),flush=True)
