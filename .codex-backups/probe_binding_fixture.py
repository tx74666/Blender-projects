import sys
sys.path.insert(0,r'D:/MyRepository/Blender-addons-by-Randy/tests')
from test_hair_bones_binding_blender import *
import bmesh
from character_designer import hair_bones_topology as t
s, p, a=scene_fixture()
bm=bmesh.new();bm.from_mesh(s.data)
bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table();bm.verts.index_update();allowed,e,adj=t._visible_graph(bm)
d=t._discover(s,bm,allowed,e,adj,set())
print([(len(x['vertices']),x['layers'][0],x['layers'][-1]) for x in d])
print('PREVIOUS',[(len(x['vertices']),x['layers'][0],x['layers'][-1]) for x in p])
print('cap',set(range(len(s.data.vertices)))-{i for x in d for i in x['vertices']})

