import sys,json
from pathlib import Path
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
import bpy,character_designer
from character_designer import body_original_mode as original, skirt_original_mode as dress, skirt_rig as skirt
from test_skirt_shared_rig_blender import world_vertices,geometry_error
from mathutils import Matrix,Quaternion
character_designer.register();bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend',load_ui=False,use_scripts=False)
main=bpy.data.objects['CoshaRig'];source=bpy.data.objects['Dress'];record=skirt.read_record(source)
skirt._activate(bpy.context,main,'POSE');bpy.context.scene.tool_settings.use_keyframe_insert_auto=False
names=[name for chain in record['chains'] for name in chain['def']]+[record['controls']['waist']]
original.ensure_dress_editable(bpy.context,main)
pb=main.pose.bones[record['chains'][0]['def'][1]];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=pb.matrix_basis.to_quaternion()@Quaternion((1,0,0),.08)
main.update_tag(refresh={'OBJECT'});bpy.context.view_layer.update()
def evaluated():return main.evaluated_get(bpy.context.evaluated_depsgraph_get())
def snapshot():return {name:evaluated().pose.bones[name].matrix.copy() for name in names}
desired=snapshot();vertices=world_vertices(source);original.leave(bpy.context,main)
report=[]
for attempt in range(7):
 actual=snapshot();errors={name:dress._difference(desired[name],actual[name]) for name in names}
 report.append({'attempt':attempt,'error':max(errors.values()),'mesh':geometry_error(vertices,world_vertices(source)),'top':sorted(errors.items(),key=lambda x:x[1],reverse=True)[:3]})
 rig_eval=evaluated();proposals=[]
 for name in names[:-1]:
  pb=rig_eval.pose.bones[name];orig=main.pose.bones[name]
  copy=orig.constraints['Skirt manual pose']
  if copy.mix_mode=='REPLACE': orig.matrix_basis=Matrix.Identity(4);copy.mix_mode='BEFORE_FULL'
  kwargs={'parent_matrix':pb.parent.matrix,'parent_matrix_local':pb.parent.bone.matrix_local} if pb.parent else {}
  currentLocal=pb.bone.convert_local_to_pose(actual[name],pb.bone.matrix_local,invert=True,**kwargs)
  kwargs={'parent_matrix':desired.get(pb.parent.name,pb.parent.matrix),'parent_matrix_local':pb.parent.bone.matrix_local} if pb.parent else {}
  wantedLocal=pb.bone.convert_local_to_pose(desired[name],pb.bone.matrix_local,invert=True,**kwargs)
  delta=currentLocal.inverted()@wantedLocal
  proposal=orig.matrix_basis@delta
  proposals.append((orig,proposal))
 for orig,proposal in proposals:orig.matrix_basis=proposal
 main.update_tag(refresh={'OBJECT'});bpy.context.view_layer.update()
path=Path(r'D:\Blender\Projects\Character\X\Validation\dress_original_20261003\native_compensation.json');path.write_text(json.dumps(report,indent=2),encoding='utf8')
print('COMPENSATION',json.dumps(report))
