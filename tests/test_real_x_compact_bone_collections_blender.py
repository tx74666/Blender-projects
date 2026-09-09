"""Validate compact groups on saved X; write a separate preview, never overwrite X."""
import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, r"D:\MyRepository\Blender-addons-by-Randy\addons")
from character_designer import bone_collections as groups, limb_ik, skirt_rig


def source_hash():
    return hashlib.sha256((ROOT / "X.blend").read_bytes()).hexdigest()


def graph(rig):
    return [(b.name, b.parent.name if b.parent else None, b.use_deform,
             tuple(tuple(row) for row in b.matrix_local),
             tuple(tuple(row) for row in rig.pose.bones[b.name].matrix_basis),
             [(c.name, c.type, c.mute, c.influence,
               getattr(c, "target", None).name if getattr(c, "target", None) else None,
               getattr(c, "subtarget", "")) for c in rig.pose.bones[b.name].constraints])
            for b in rig.data.bones]


def mesh_hash(obj):
    digest = hashlib.sha256()
    blocks = [obj.data.vertices]
    if obj.data.shape_keys:
        blocks += [key.data for key in obj.data.shape_keys.key_blocks]
    for block in blocks:
        values = array("f", [0.0]) * (len(block) * 3)
        block.foreach_get("co", values)
        digest.update(values.tobytes())
    digest.update(repr([(g.name, g.lock_weight) for g in obj.vertex_groups]).encode())
    digest.update(repr([[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices]).encode())
    digest.update(repr([(m.name, m.type) for m in obj.modifiers]).encode())
    return digest.hexdigest()


before_hash = source_hash()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "X.blend"), load_ui=False)
for cls in groups.BONE_COLLECTION_CLASSES:
    bpy.utils.register_class(cls)
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
rig = bpy.data.objects["CoshaRig"]
skirt = bpy.data.objects["Dress"][skirt_rig.RIG_KEY]
for obj in bpy.context.selected_objects:
    obj.select_set(False)
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
before_graph = {obj.name: graph(obj) for obj in (rig, skirt)}
meshes = [bpy.data.objects[name] for name in ("Cosha", "Dress", "Hair1", "Hair2", "Hair3")]
before_mesh = {obj.name: mesh_hash(obj) for obj in meshes}
assert bpy.ops.character_designer.simplify_bone_collections() == {"FINISHED"}
assert tuple(rig.data.collections.keys()) == groups.BODY_NAMES
assert tuple(skirt.data.collections.keys()) == ("Skirt",)
assert len(rig.data.collections["Original"].bones) == 56
assert len(rig.data.collections["Controls"].bones) == 12
assert len(rig.data.collections["Animation"].bones) == 52
assert all(name in rig.data.collections["Animation"].bones for name in ("Hips", "Head", "eye.L", "f_index.01.L", "toe.L"))
limb_ik._removal_resources(bpy.context, rig, limb_ik._validate_inventory(rig))
assert {obj.name: graph(obj) for obj in (rig, skirt)} == before_graph
assert {obj.name: mesh_hash(obj) for obj in meshes} == before_mesh
output = ROOT / "Previews" / "X_Bone_Collections_0.42.3.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(output))
bpy.ops.wm.open_mainfile(filepath=str(output), load_ui=False)
rig = bpy.data.objects["CoshaRig"]
assert tuple(rig.data.collections.keys()) == groups.BODY_NAMES
assert len(rig.data.collections["Animation"].bones) == 52
assert source_hash() == before_hash
report = {"preview": str(output), "original_unchanged": True, "original_sha256": before_hash,
          "body_collections": {c.name: len(c.bones) for c in rig.data.collections},
          "skirt_collection": "Skirt", "rig_graph_and_mesh_weights_unchanged": True,
          "save_reopen_passed": True}
(ROOT / "outputs" / "animation" / "compact_bone_collections_verification.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
print("REAL_X_COMPACT_BONE_COLLECTIONS_PASSED")
