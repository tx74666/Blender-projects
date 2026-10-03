import sys
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
import bpy
import character_designer
from character_designer import skirt_original_mode as d
from test_skirt_original_mode_blender import fixture
from mathutils import Matrix, Quaternion
character_designer.register()
source,rig,main,foreign,record=fixture()
pb=rig.pose.bones[record['chains'][0]['def'][0]]
for con in pb.constraints:
 print('CONPROPS',con.name,[(key,getattr(con,key,None)) for key in ('remove_target_shear','use_x','use_y','use_z','invert_x','invert_y','invert_z','use_offset','euler_order','mix_mode','owner_space','target_space')])
entries=d.prepare(bpy.context,main);entry=entries[0]
desired={name:Matrix(value) for name,value in entry['pose'].items()}
for chain in record['chains']:
 for name in chain['def']:
  pb=rig.pose.bones[name];pb.constraints['Skirt manual pose'].mix_mode='BEFORE_FULL';pb.matrix_basis=Matrix.Identity(4)
d._update(bpy.context,[rig])
print('IDENTITY_ERROR',max(d._difference(matrix,rig.pose.bones[name].matrix) for name,matrix in desired.items()))
pb=rig.pose.bones[record['chains'][0]['def'][1]];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion((1,0,0),.14)
d._update(bpy.context,[rig]); print('EDIT_EFFECT',d._difference(desired[pb.name],pb.matrix))
now={name:rig.pose.bones[name].matrix.copy() for name in desired}
d._update(bpy.context,[rig]);print('REPEAT_ERROR',max(d._difference(matrix,rig.pose.bones[name].matrix) for name,matrix in now.items()))
