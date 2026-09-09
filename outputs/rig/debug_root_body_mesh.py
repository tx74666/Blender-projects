import bpy,sys,json
from mathutils import Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import root_control as root,limb_ik
character_designer.register();bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\outputs\rig\X_root_extension_preview.blend');r=bpy.data.objects['CoshaRig'];limb_ik._mode_set(bpy.context,r,'POSE')
def update():root._update(bpy.context,r)
def points(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=[e.matrix_world@v.co for v in m.vertices];e.to_mesh_clear();return p
update();o=bpy.data.objects['Cosha'];o.modifiers['Subdivision'].show_viewport=False;update();before=points(o);p=r.pose.bones['CTRL_master'];p.location=(.12,-.08,.05);p.rotation_euler=(.13,-.11,.2);p[root.SCALE_PROPERTY]=1.2;update();T=r.matrix_world@p.matrix@r.matrix_world.inverted_safe();after=points(o);errors=sorted([((T@a-b).length,i) for i,(a,b) in enumerate(zip(before,after))],reverse=True)
print('COSHA_MODIFIERS',[(m.name,m.type,[(q.identifier,str(getattr(m,q.identifier))) for q in m.bl_rna.properties if q.type in {'BOOLEAN','POINTER','STRING'} and not q.is_readonly]) for m in o.modifiers],flush=True)
print('ERROR_COUNTS',len([e for e,i in errors if e>1e-4]),len(errors),'nativeverts',len(o.data.vertices),flush=True)
print('BADVERTS',[(e,i,list(o.data.vertices[i].co),[(o.vertex_groups[g.group].name,g.weight, r.data.bones[o.vertex_groups[g.group].name].use_deform if o.vertex_groups[g.group].name in r.data.bones else None) for g in o.data.vertices[i].groups]) for e,i in errors[:15]],flush=True)
for a in bpy.data.objects:
 if a.type=='ARMATURE' and a!=r:
  print('OTHER_RIG',a.name,'hide',a.hide_get(),'collections',[c.name for c in a.users_collection],'bone_constraints',[(b.name,[(c.type,getattr(getattr(c,'target',None),'name',None),getattr(c,'subtarget',None),getattr(c,'mix_mode',None),getattr(c,'owner_space',None),getattr(c,'target_space',None)) for c in b.constraints]) for b in a.pose.bones if b.constraints][:30],flush=True)

