import bpy,sys,json,hashlib,os
from array import array
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import root_control as root,limb_ik,torso_controls
SOURCE=Path(r'D:\Blender\Projects\Character\X\X.blend');OUT=SOURCE.parent/'outputs/rig';REPORT=OUT/'root_meshes_readonly_validation.json';PREVIEW=OUT/'X_root_extension_preview.blend'
hash_before=hashlib.sha256(SOURCE.read_bytes()).hexdigest();character_designer.register();bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['CoshaRig'];limb_ik._mode_set(bpy.context,rig,'POSE')
def update():root._update(bpy.context,rig)
def mesh_points(obj):
 dg=bpy.context.evaluated_depsgraph_get();o=obj.evaluated_get(dg);mesh=o.to_mesh();v=array('f',[0.0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',v);points=[o.matrix_world@Vector(v[i:i+3]) for i in range(0,len(v),3)];o.to_mesh_clear();return points
def weight_digest(obj):
 return hashlib.sha256(repr(([(g.name,g.index) for g in obj.vertex_groups],[(v.index,tuple((g.group,g.weight) for g in v.groups)) for v in obj.data.vertices])).encode()).hexdigest()
update();others={o.name:{'world':o.matrix_world.copy(),'bones':{p.name:(o.matrix_world@p.matrix).copy() for p in o.pose.bones}} for o in bpy.data.objects if o.type=='ARMATURE' and o!=rig};meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)];before={o.name:mesh_points(o) for o in meshes};weights={o.name:weight_digest(o) for o in meshes}
rec=root.build(bpy.context,rig);p=rig.pose.bones[rec['master']];build={o.name:max(((a-b).length for a,b in zip(before[o.name],mesh_points(o))),default=0) for o in meshes};assert max(build.values())<4e-4,build
p.location=(.12,-.08,.05);p.rotation_euler=(.13,-.11,.2);p[root.SCALE_PROPERTY]=1.2;update();T=rig.matrix_world@p.matrix@rig.matrix_world.inverted_safe();moved={o.name:max(((T@a-b).length for a,b in zip(before[o.name],mesh_points(o))),default=0) for o in meshes};other_moved={}
for name,state in others.items():
 o=bpy.data.objects[name];other_moved[name]={'parent':o.parent.name if o.parent else None,'parent_type':o.parent_type,'constraints':[(c.type,getattr(getattr(c,'target',None),'name',None),getattr(c,'subtarget',None)) for c in o.constraints],'world_matrix_max_delta':max(abs(o.matrix_world[i][j]-state['world'][i][j]) for i in range(4) for j in range(4)),'bone_world_follow_max_error':max(abs((o.matrix_world@o.pose.bones[n].matrix)[i][j]-(T@m)[i][j]) for n,m in state['bones'].items() for i in range(4) for j in range(4))}
report={'meshes':[{'name':o.name,'vertices':len(before[o.name]),'armature_modifiers':[m.object.name if m.object else None for m in o.modifiers if m.type=='ARMATURE'],'hidden':o.hide_get()} for o in meshes],'build_mesh_max_errors':build,'global_root_mesh_max_errors':moved,'other_armatures':other_moved,'weights_unchanged':{o.name:weight_digest(o)==weights[o.name] for o in meshes},'production_file_unchanged':hashlib.sha256(SOURCE.read_bytes()).hexdigest()==hash_before,'preview_path':str(PREVIEW)}
# Save neutral root channels as the reviewable preview while preserving the saved artist pose.
p.location=(0,0,0);p.rotation_euler=(0,0,0);p[root.SCALE_PROPERTY]=1;update();limb_ik._validate_inventory(rig)
for b in rig.pose.bones:b.select=False
rig.pose.bones[rec['master']].select=True;rig.data.bones.active=rig.data.bones[rec['master']]
bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW));REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8');print('X_ROOT_MESH_RESULT',json.dumps(report),flush=True)

