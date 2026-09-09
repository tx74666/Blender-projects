import bpy
import bmesh
import hashlib
import json
import math
import struct
from mathutils import Vector
from mathutils.kdtree import KDTree


EXPECTED_OBJECT = "Cosha"
EXPECTED_MESH = "Vert"
EXPECTED_KEY = "Mouth_O"
EXPECTED_COUNTS = (3557, 7037, 3488)
EXPECTED_SELECTED = {32, 78, 1826, 1863}
REPAIR_PAIRS = ((32, 1826), (78, 1863))
SIGNATURE_TOLERANCE = 1.0e-5
ZERO_DELTA_TOLERANCE = 1.0e-6


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


def reflected(vector):
    return Vector((-vector.x, vector.y, vector.z))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def mirror_residuals(basis, key):
    count = len(basis.data)
    tree = KDTree(count)
    for index, point in enumerate(basis.data):
        tree.insert(point.co, index)
    tree.balance()

    nearest = []
    for point in basis.data:
        _co, index, distance = tree.find(reflected(point.co))
        nearest.append((int(index), float(distance)))

    residuals = []
    seen = set()
    for index, (other, distance) in enumerate(nearest):
        back, back_distance = nearest[other]
        if back != index or distance > SIGNATURE_TOLERANCE or back_distance > SIGNATURE_TOLERANCE:
            continue
        pair = tuple(sorted((index, other)))
        if pair in seen:
            continue
        seen.add(pair)
        delta_a = key.data[index].co - basis.data[index].co
        delta_b = key.data[other].co - basis.data[other].co
        residual = math.sqrt(
            (delta_a.x + delta_b.x) ** 2
            + (delta_a.y - delta_b.y) ** 2
            + (delta_a.z - delta_b.z) ** 2
        )
        if residual > 1.0e-7:
            residuals.append((float(residual), index, other))
    residuals.sort(reverse=True)
    return residuals


obj = bpy.data.objects.get(EXPECTED_OBJECT)
require(obj is not None and obj.type == "MESH", "Expected the Cosha mesh object")
require(obj.data.name == EXPECTED_MESH, f"Unexpected mesh datablock: {obj.data.name}")
mesh = obj.data
require(
    (len(mesh.vertices), len(mesh.edges), len(mesh.polygons)) == EXPECTED_COUNTS,
    "Mesh topology counts changed; refusing the point repair",
)
require(mesh.shape_keys is not None, "Cosha has no Shape Keys")
keys = mesh.shape_keys.key_blocks
require("Basis" in keys and EXPECTED_KEY in keys, "Expected Basis and Mouth_O")
require(all(len(key.data) == EXPECTED_COUNTS[0] for key in keys), "Shape Key data lengths differ")
basis = keys["Basis"]
mouth = keys[EXPECTED_KEY]
require(mouth.relative_key == basis, "Mouth_O is no longer relative to Basis")

bpy.context.view_layer.objects.active = obj
obj.select_set(True)
obj.active_shape_key_index = list(keys).index(mouth)
require(obj.active_shape_key == mouth, "Could not activate Mouth_O")

original_mode = obj.mode
original_select_mode = tuple(bpy.context.tool_settings.mesh_select_mode)
if original_mode == "EDIT":
    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()
    original_selected = {vertex.index for vertex in bm.verts if vertex.select}
else:
    original_selected = {vertex.index for vertex in mesh.vertices if vertex.select}
require(original_selected == EXPECTED_SELECTED, f"Unexpected selected vertices: {sorted(original_selected)}")

# Verify the exact saved corruption signature before writing anything.
require((basis.data[32].co - reflected(basis.data[1826].co)).length < SIGNATURE_TOLERANCE, "32/1826 are no longer a Basis mirror pair")
require((basis.data[78].co - reflected(basis.data[1863].co)).length < SIGNATURE_TOLERANCE, "78/1863 are no longer a Basis mirror pair")
require((mouth.data[1826].co - basis.data[1826].co).length < ZERO_DELTA_TOLERANCE, "Mouth_O[1826] is no longer the healthy zero-delta source")
require((mouth.data[1863].co - basis.data[1863].co).length < ZERO_DELTA_TOLERANCE, "Mouth_O[1863] is no longer the healthy zero-delta source")
require((mouth.data[32].co - basis.data[78].co).length < SIGNATURE_TOLERANCE, "Mouth_O[32] no longer carries Basis[78]")
require((mouth.data[78].co - basis.data[32].co).length < SIGNATURE_TOLERANCE, "Mouth_O[78] no longer carries Basis[32]")
before_residuals = mirror_residuals(basis, mouth)
require({tuple(sorted((a, b))) for _value, a, b in before_residuals if _value > SIGNATURE_TOLERANCE} == {(32, 1826), (78, 1863)}, "Unexpected Mouth_O asymmetry beyond the two diagnosed pairs")

if obj.mode == "EDIT":
    bpy.ops.object.mode_set(mode="OBJECT")

before_topology = topology_hash(mesh)
before_hashes = {key.name: coord_hash(key.data) for key in keys}
before_meta = [(key.name, key.relative_key.name, len(key.data)) for key in keys]
before_mouth = [point.co.copy() for point in mouth.data]

for target, source in REPAIR_PAIRS:
    source_delta = mouth.data[source].co - basis.data[source].co
    mouth.data[target].co = basis.data[target].co + reflected(source_delta)
mesh.update()

changed = [
    index
    for index, (before, after) in enumerate(zip(before_mouth, mouth.data))
    if (before - after.co).length > 1.0e-9
]
after_hashes = {key.name: coord_hash(key.data) for key in keys}
after_meta = [(key.name, key.relative_key.name, len(key.data)) for key in keys]
after_residuals = mirror_residuals(basis, mouth)

require(changed == [32, 78], f"Repair changed unexpected Mouth_O vertices: {changed}")
require(topology_hash(mesh) == before_topology, "Topology hash changed")
require(after_meta == before_meta, "Shape Key metadata changed")
for key_name, before_hash in before_hashes.items():
    if key_name != EXPECTED_KEY:
        require(after_hashes[key_name] == before_hash, f"Unexpected change to Shape Key {key_name}")
require((mouth.data[32].co - basis.data[32].co).length < 1.0e-9, "Mouth_O[32] was not reset to Basis")
require((mouth.data[78].co - basis.data[78].co).length < 1.0e-9, "Mouth_O[78] was not reset to Basis")
require(not [entry for entry in after_residuals if entry[0] > 1.0e-7], "Mouth_O still has asymmetric deltas")

# Restore the artist-facing state before persisting the repaired candidate.
obj.active_shape_key_index = list(keys).index(mouth)
for vertex in mesh.vertices:
    vertex.select = vertex.index in original_selected
bpy.context.tool_settings.mesh_select_mode = original_select_mode
if original_mode == "EDIT":
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()
    for vertex in bm.verts:
        vertex.select_set(vertex.index in original_selected)
    bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

save_result = bpy.ops.wm.save_as_mainfile(
    filepath=bpy.data.filepath,
    check_existing=False,
    relative_remap=False,
)
require("FINISHED" in save_result, f"Saving repaired candidate failed: {save_result}")

print(
    "CODEX_MOUTH_O_REPAIR="
    + json.dumps(
        {
            "filepath": bpy.data.filepath,
            "changed_indices": changed,
            "selected": sorted(original_selected),
            "mode": obj.mode,
            "active_shape_key": obj.active_shape_key.name if obj.active_shape_key else None,
            "topology_sha256": before_topology,
            "before_shape_key_sha256": before_hashes,
            "after_shape_key_sha256": after_hashes,
            "before_residual_count": len(before_residuals),
            "after_residual_count": len(after_residuals),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
