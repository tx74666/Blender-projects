"""Read saved X rig structure in a disposable Blender process; never save the scene."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "X.blend"
OUTPUT = Path(__file__).with_name("saved_rig_adapter_audit.json")


def digest():
    return hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def props(block):
    return {key: str(block[key]) for key in block.keys()
            if key.startswith(("character_designer", "cd_", "skirt_"))}


before = digest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
armatures = []
for obj in bpy.data.objects:
    if obj.type != "ARMATURE":
        continue
    bones = [{"name": b.name, "parent": b.parent.name if b.parent else None,
              "deform": b.use_deform, "properties": props(b),
              "head_rest": list(b.head_local), "tail_rest": list(b.tail_local),
              "constraints": [{"type": c.type, "name": c.name, "mute": c.mute,
                               "target": getattr(c, "target", None).name if getattr(c, "target", None) else None,
                               "subtarget": getattr(c, "subtarget", "")}
                              for c in obj.pose.bones[b.name].constraints]}
             for b in obj.data.bones]
    ad = obj.animation_data
    armatures.append({"name": obj.name, "bones": bones, "bone_count": len(bones),
                      "deform_count": sum(b["deform"] for b in bones),
                      "collections": [{"name": c.name, "parent": c.parent.name if c.parent else None,
                                       "visible": c.is_visible, "properties": props(c),
                                       "bones": [b.name for b in c.bones]} for c in obj.data.collections_all],
                      "owner_counts": dict(Counter(b["properties"].get("character_designer_owner", "untagged") for b in bones)),
                      "properties": props(obj), "data_properties": props(obj.data),
                      "action": ad.action.name if ad and ad.action else None,
                      "nla_tracks": len(ad.nla_tracks) if ad else 0})
meshes = [{"name": obj.name, "parent": obj.parent.name if obj.parent else None,
           "parent_bone": obj.parent_bone, "properties": props(obj),
           "armatures": [mod.object.name if mod.object else None for mod in obj.modifiers if mod.type == "ARMATURE"],
           "modifiers": [mod.type for mod in obj.modifiers],
           "shape_keys": [key.name for key in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else []}
          for obj in bpy.data.objects if obj.type == "MESH"]
after = digest()
assert before == after, "The saved source changed during this read-only audit."
report = {"source": str(SOURCE), "source_sha256": before, "source_unchanged": True,
          "scope": "Saved file structure only; not a live-window or evaluated animation validation.",
          "blender_version": bpy.app.version_string,
          "armatures": armatures, "meshes": meshes,
          "actions": [a.name for a in bpy.data.actions]}
OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"report": str(OUTPUT), "armatures": [{k: a[k] for k in ("name", "bone_count", "deform_count", "owner_counts", "action", "nla_tracks")} for a in armatures], "actions": report["actions"], "source_unchanged": True}, ensure_ascii=False))
