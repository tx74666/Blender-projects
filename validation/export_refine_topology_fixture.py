"""Read only saved Basis/topology for private local symmetry diagnostics."""
import bpy
import hashlib
import json
from pathlib import Path
import sys

source, destination = map(Path, sys.argv[sys.argv.index('--') + 1:])
before = hashlib.sha256(source.read_bytes()).hexdigest()
with bpy.data.libraries.load(str(source), link=False) as (available, requested):
    requested.objects = ['Cosha']
obj = requested.objects[0]
mesh = obj.data
points = mesh.shape_keys.reference_key.data if mesh.shape_keys else mesh.vertices
payload = {'source_sha256': before, 'coordinates': [tuple(point.co) for point in points],
           'edges': [tuple(edge.vertices) for edge in mesh.edges],
           'faces': [tuple(face.vertices) for face in mesh.polygons]}
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
destination.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')
print('EXPORTED_READ_ONLY_TOPOLOGY', len(points), len(mesh.edges), len(mesh.polygons),
      sum(abs(point.co.x) <= 1e-6 for point in points))
