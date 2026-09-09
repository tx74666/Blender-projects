import bpy
import bmesh
import hashlib
import json
import math
import struct
from mathutils import Vector
from mathutils.kdtree import KDTree


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def coord_hash(points):
    digest = hashlib.sha256()
    for point in points:
        digest.update(struct.pack("<3f", float(point.co.x), float(point.co.y), float(point.co.z)))
    return digest.hexdigest()


def topology_hash(mesh):
    digest = hashlib.sha256()
    digest.update(struct.pack("<III", len(mesh.vertices), len(mesh.edges), len(mesh.polygons)))
    for edge in mesh.edges:
        digest.update(struct.pack("<II", int(edge.vertices[0]), int(edge.vertices[1])))
    for polygon in mesh.polygons:
        vertices = tuple(int(index) for index in polygon.vertices)
        digest.update(struct.pack("<I", len(vertices)))
        digest.update(struct.pack("<" + "I" * len(vertices), *vertices))
    return digest.hexdigest()


obj = bpy.data.objects.get("Cosha")
require(obj is not None and obj.type == "MESH", "Cosha mesh not found")
mesh = obj.data
require((len(mesh.vertices), len(mesh.edges), len(mesh.polygons)) == (3557, 7037, 3488), "Topology counts changed")
keys = mesh.shape_keys.key_blocks
require([key.name for key in keys] == ["Basis", "Eye_Close_L", "Eye_Close_R", "Mouth_O"], "Shape Key order changed")
basis = keys["Basis"]
mouth = keys["Mouth_O"]
require((mouth.data[32].co - basis.data[32].co).length < 1.0e-9, "Mouth_O[32] is not Basis")
require((mouth.data[78].co - basis.data[78].co).length < 1.0e-9, "Mouth_O[78] is not Basis")
require((mouth.data[1826].co - basis.data[1826].co).length < 1.0e-9, "Mouth_O[1826] changed")
require((mouth.data[1863].co - basis.data[1863].co).length < 1.0e-9, "Mouth_O[1863] changed")

tree = KDTree(len(basis.data))
for index, point in enumerate(basis.data):
    tree.insert(point.co, index)
tree.balance()
nearest = []
for point in basis.data:
    _co, index, distance = tree.find(Vector((-point.co.x, point.co.y, point.co.z)))
    nearest.append((int(index), float(distance)))
residuals = []
seen = set()
for index, (other, distance) in enumerate(nearest):
    back, back_distance = nearest[other]
    if back != index or distance > 1.0e-5 or back_distance > 1.0e-5:
        continue
    pair = tuple(sorted((index, other)))
    if pair in seen:
        continue
    seen.add(pair)
    delta_a = mouth.data[index].co - basis.data[index].co
    delta_b = mouth.data[other].co - basis.data[other].co
    residual = math.sqrt(
        (delta_a.x + delta_b.x) ** 2
        + (delta_a.y - delta_b.y) ** 2
        + (delta_a.z - delta_b.z) ** 2
    )
    if residual > 1.0e-7:
        residuals.append((residual, index, other))
require(not residuals, f"Mouth_O still has mirror residuals: {residuals[:10]}")

if obj.mode == "EDIT":
    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()
    selected = sorted(vertex.index for vertex in bm.verts if vertex.select)
else:
    selected = sorted(vertex.index for vertex in mesh.vertices if vertex.select)
require(selected == [32, 78, 1826, 1863], f"Selection changed: {selected}")
require(
    obj.active_shape_key is not None
    and obj.active_shape_key.as_pointer() == mouth.as_pointer(),
    "Active Shape Key is not Mouth_O",
)

print(
    "CODEX_MOUTH_O_VERIFY="
    + json.dumps(
        {
            "filepath": bpy.data.filepath,
            "mode": obj.mode,
            "active_shape_key": obj.active_shape_key.name,
            "selected": selected,
            "topology_sha256": topology_hash(mesh),
            "shape_key_sha256": {key.name: coord_hash(key.data) for key in keys},
            "mirror_residual_count": len(residuals),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
