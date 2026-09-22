"""Replay read-only coordinates in a disposable process; never load X.blend."""
import json, sys, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import bpy, bmesh
from mathutils import Vector, Matrix
sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/addons')
from character_designer import finger_loop_marks as marks, finger_internal as internal
d=json.loads(Path('D:/Blender/Projects/Character/X/outputs/mark_alignment_diagnostic_20260922.json').read_text())
mesh=bpy.data.meshes.new('LiveCoordinateReplay')
mesh.from_pydata(d['mesh_vertices'], [], d['mesh_faces'])
bm=bmesh.new(); bm.from_mesh(mesh)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
transform=SimpleNamespace(matrix_world=Matrix.Identity(4))
reference={'body':d['body'], 'basis':d['basis']}
points=list(map(Vector,d['points']))
old=list(map(Vector,d['original_nodes']))
start=time.perf_counter()
with patch.object(internal,'_component',side_effect=AssertionError('Whole model traversal')):
    print('COVERAGE_DEBUG', [marks._covered_span(a,b,list(zip(old,old[1:])),max(1e-7,d['body']['length']*1e-6)) for a,b in zip(points,points[1:])], flush=True)
    marks._certify(transform, transform, reference, points, bm,
                   original_nodes=old, bone_names=d['bone_names'])
result={'certified':True,'bone_names':d['bone_names'],'milliseconds':(time.perf_counter()-start)*1000,
        'source_version':d['version'], 'vertices':len(bm.verts),'faces':len(bm.faces)}
Path('D:/Blender/Projects/Character/X/outputs/mark_alignment_replay_result_20260922.json').write_text(json.dumps(result,indent=2))
print('ACTUAL_MARK_ALIGNMENT_REPLAY',json.dumps(result),flush=True)
bm.free()
