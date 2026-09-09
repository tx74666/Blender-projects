"""Read the final Hair3 mirror preview without saving or registering add-ons."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[2]
path = root / "Previews" / "X_Hair3_Full_Mirror_0.40.2.blend"
digest = hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
objects = []
for obj in bpy.data.objects:
    if obj.type == "MESH" and obj.name.startswith("Hair3") and obj.get("character_designer_hair_bones_v1"):
        record = json.loads(obj["character_designer_hair_bones_v1"])
        if len(record["chains"]) == 13:
            objects.append((obj, record))
assert len(objects) == 1, [(obj.name, len(record["chains"])) for obj, record in objects]
obj, record = objects[0]
armature = obj["character_designer_hair_bones_armature"]
assert Counter(chain["mirror_side"] for chain in record["chains"]) == {"L": 6, "R": 6, "C": 1}
assert all(len(chain["bones"]) == 4 for chain in record["chains"])
bpy.context.view_layer.update()
chains = []
inverse = obj.matrix_world.inverted()
for chain in record["chains"]:
    bones = []
    for name in chain["bones"]:
        bone = armature.data.bones[name]
        pose = armature.pose.bones[name]
        assert max(abs(pose.matrix_basis[i][j] - float(i == j)) for i in range(4) for j in range(4)) < 1e-6, name
        head, tail = armature.matrix_world @ bone.head_local, armature.matrix_world @ bone.tail_local
        if chain["mirror_side"] == "C":
            assert max(abs((inverse @ point).x) for point in (head, tail)) < 1e-6, (name, head, tail)
        bones.append([list(head), list(tail)])
    chains.append({"side": chain["mirror_side"], "bones": bones})
evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = evaluated.to_mesh()
try:
    points = [list(evaluated.matrix_world @ vertex.co) for vertex in mesh.vertices]
    faces = [list(face.vertices) for face in mesh.polygons]
finally:
    evaluated.to_mesh_clear()
seam = obj.matrix_world @ Vector((0, 0, 0))
data = {"coordinates": points, "faces": faces, "chains": chains, "seam_world": list(seam),
        "source": obj.name, "source_hash": digest, "mirror_layout": record.get("mirror_layout")}
(Path(__file__).resolve().parent / "Hair3_Full_Mirror_0.40.2-plot-data.json").write_text(json.dumps(data), encoding="utf-8")
assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
print("FULL_HAIR3_PLOT_DATA_OK", obj.name, len(points), len(faces), Counter(chain["side"] for chain in chains), digest)
