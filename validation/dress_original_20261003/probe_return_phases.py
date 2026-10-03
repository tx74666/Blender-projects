import sys,json
from pathlib import Path
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
import bpy,character_designer
from character_designer import body_original_mode as original, skirt_original_mode as dress, skirt_rig as skirt, bone_collections as groups
from test_skirt_shared_rig_blender import world_vertices,geometry_error
from mathutils import Quaternion
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend',load_ui=False,use_scripts=False)
main=bpy.data.objects['CoshaRig'];source=bpy.data.objects['Dress'];record=skirt.read_record(source)
skirt._activate(bpy.context,main,'POSE');bpy.context.scene.tool_settings.use_keyframe_insert_auto=False
names=list(record['shared']['names']); stages=[];capture_enabled=False;expected=None
def snapshot():
 evaluated=main.evaluated_get(bpy.context.evaluated_depsgraph_get())
 return {name:evaluated.pose.bones[name].matrix.copy() for name in names}
def sample(label):
 if not capture_enabled:return
 actual=snapshot();errors={name:dress._difference(expected[name],actual[name]) for name in names}
 stages.append({'stage':label,'max':max(errors.values()),'top':sorted(errors.items(),key=lambda x:x[1],reverse=True)[:10],
                'Hips':[list(row) for row in main.pose.bones['Hips'].matrix]})
orig_update=original._update
def tagged_update(*args,**kwargs):
 result=orig_update(*args,**kwargs);sample('body_update');return result
original._update=tagged_update
orig_dress_leave=dress.leave
def tagged_dress_leave(*args,**kwargs):
 sample('before_dress_leave');result=orig_dress_leave(*args,**kwargs);sample('after_dress_leave');return result
dress.leave=tagged_dress_leave
orig_frame=groups._frame_visibility
def tagged_frame(*args,**kwargs):
 sample('before_frame_visibility');result=orig_frame(*args,**kwargs);sample('after_frame_visibility');return result
groups._frame_visibility=tagged_frame
def cycle(label,edit):
 global capture_enabled,expected,stages
 original.ensure_dress_editable(bpy.context,main) if original.active(main) else original.enter(bpy.context,main)
 if edit:
  pb=main.pose.bones[record['chains'][0]['def'][1]];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=pb.matrix_basis.to_quaternion()@Quaternion((1,0,0),.08)
  main.update_tag(refresh={'OBJECT'});bpy.context.view_layer.update()
 expected=snapshot();vertices=world_vertices(source);stages=[];capture_enabled=True
 original.leave(bpy.context,main);sample('after_all_leave');bpy.context.view_layer.update();sample('after_explicit_update');after=world_vertices(source);sample('after_mesh_eval')
 capture_enabled=False
 return {'label':label,'edit':edit,'mesh':geometry_error(vertices,after),'stages':stages}
report=[]
for label,edit in [('old_active_unedited',False),('settled_fresh_edited',True),('settled_fresh_unedited_existing_correction',False)]:
 try:report.append(cycle(label,edit))
 except Exception as error:report.append({'label':label,'error':repr(error),'stages':stages});capture_enabled=False
out=Path(r'D:\Blender\Projects\Character\X\Validation\dress_original_20261003\return_phases.json');out.write_text(json.dumps(report,indent=2),encoding='utf8')
print('PHASE_REPORT',json.dumps(report))
