import bpy,sys,json
from mathutils import Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import root_control as root,limb_ik
character_designer.register();bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\outputs\rig\X_root_extension_preview.blend');r=bpy.data.objects['CoshaRig'];limb_ik._mode_set(bpy.context,r,'POSE');o=bpy.data.objects['Cosha'];p=r.pose.bones['CTRL_master']
def update():root._update(bpy.context,r)
def points():
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@a.co for a in m.vertices];e.to_mesh_clear();return v
update();before=points();hook=o.modifiers.new('TEST Root unweighted follow','HOOK');hook.object=r;hook.subtarget=p.name;hook.vertex_indices_set([3574,3575]);hook.falloff_type='NONE';hook.matrix_inverse=(r.matrix_world@p.matrix).inverted_safe()@o.matrix_world;o.modifiers.move(len(o.modifiers)-1,1);update();build=max((a-b).length for a,b in zip(before,points()));p.location=(.12,-.08,.05);p.rotation_euler=(.13,-.11,.2);p[root.SCALE_PROPERTY]=1.2;update();T=r.matrix_world@p.matrix@r.matrix_world.inverted_safe();e=max((T@a-b).length for a,b in zip(before,points()));print('HOOK_PROTOTYPE',json.dumps({'build_error':build,'global_motion_error':e,'count':len(before)}),flush=True)
