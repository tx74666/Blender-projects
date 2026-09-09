"""Read completed comparison files; export source geometry and owned rest bones."""
import json
from pathlib import Path
import bpy

directory = Path(__file__).resolve().parent
rows = []
for filename, mode, count in (("X-Hair-A-Per-Strand.blend", "PER_STRAND", 18),
                              ("X-Hair-B-Grouped.blend", "GROUPED", 6)):
    path = directory / filename
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    source = bpy.data.objects["Hair2"]
    candidates = [collection for collection in bpy.data.collections
                  if collection.get("character_designer_hair_variant_source") is source
                  and collection.get("character_designer_hair_variant_mode") == mode]
    assert len(candidates) == 1, (filename, len(candidates))
    collection = candidates[0]
    mesh = collection["character_designer_hair_variant_mesh"]
    armature = collection["character_designer_hair_variant_armature"]
    record = json.loads(mesh["character_designer_hair_bones_v1"])
    assert sum(len(chain["bones"]) for chain in record["chains"]) == count
    chains = []
    for chain in record["chains"]:
        bones = []
        for name in chain["bones"]:
            bone = armature.data.bones[name]
            bones.append([list(armature.matrix_world @ bone.head_local),
                          list(armature.matrix_world @ bone.tail_local)])
        chains.append({"bones": bones, "vertices": chain["vertices"]})
    rows.append({"mode": mode, "coordinates": [list(source.matrix_world @ vertex.co) for vertex in source.data.vertices],
                 "faces": [list(face.vertices) for face in source.data.polygons], "chains": chains})
assert len(rows[0]["coordinates"]) == len(rows[1]["coordinates"])
assert rows[0]["coordinates"] == rows[1]["coordinates"], "Both panels must show the same original mesh"
assert set(i for chain in rows[0]["chains"] for i in chain["vertices"]) == set(i for chain in rows[1]["chains"] for i in chain["vertices"])
(directory / "plot-data.json").write_text(json.dumps(rows), encoding="utf-8")
print("HAIR_COMPARISON_PLOT_DATA_OK")
