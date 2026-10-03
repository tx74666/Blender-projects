import sys
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
import bpy
import character_designer
from character_designer import skirt_original_mode as d, body_original_mode as o
from test_skirt_original_mode_blender import fixture
character_designer.register()
source,rig,main,foreign,record=fixture()
entries=d.prepare(bpy.context,main)
entry=entries[0]
from mathutils import Matrix
desired={name:Matrix(value) for name,value in entry['pose'].items()}
targets=d._resolve(bpy.context,main,entries)
for _,t,s,r,relations in targets:
 for pb,copy,rot in relations:
  basis=d._local(pb,desired[pb.name],desired)
  print('BEFORE',pb.name,'inherit',pb.bone.inherit_scale,'connect',pb.bone.use_connect,'basisloc',list(basis.translation),'basisScale',list(basis.to_scale()))
  copy.mute=rot.mute=True;pb.matrix_basis=basis
d._update(bpy.context,[rig])
for name in desired:
 pb=rig.pose.bones[name];error=d._difference(desired[name],pb.matrix)
 print('FREEZE',name,error,'actual',list(pb.matrix.translation),'desired',list(desired[name].translation),'scaleActual',list(pb.matrix.to_scale()),'scaleDesired',list(desired[name].to_scale()))
