import sys
sys.path.insert(0,r'D:\Blender\Projects\Character\X\tests')
import test_hair_bones_variants_blender as t
from character_designer import hair_bones_variants as v, hair_bones_rig as r
import bmesh,bpy
original=r._restore_context
def inspect(c,o,s):
 print('RESTOREMODE',s['mesh_select_mode'],s['mesh_selection']['select_mode']);original(c,o,s); bm=bmesh.from_edit_mesh(o.data); print('RESTORED', [x.index for x in bm.verts if x.select]);print('afterupdate',o.update_from_editmode());print('RESTORED2',[x.index for x in bm.verts if x.select])
r._restore_context=inspect
try:t.test_transaction_and_unrelated_weights()
except Exception:raise
