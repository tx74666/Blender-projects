"""Disposable integration of foot controls on the saved X character."""
from pathlib import Path
import hashlib
import json
import sys
import traceback

import bpy

ROOT = Path(r"D:\Blender\Projects\Character\X")
SOURCE = ROOT / "X.blend"
OUT = ROOT / "outputs" / "rig" / "foot_controls_046_verification.json"
sys.path.insert(0, r"D:\MyRepository\Blender-addons-by-Randy\addons")
import character_designer
from character_designer import foot_controls, limb_ik, limb_ik_fk, bone_collections

report = {"ok": False, "source": str(SOURCE), "checks": []}
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def matrices(rig, names):
    limb_ik_fk._update(bpy.context, rig)
    return limb_ik_fk._matrices(rig, names)


def weights_and_geometry():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == "MESH" and not o.get("character_designer_owner")), key=lambda o: o.name):
        data = {"name": obj.name, "vertices": [list(v.co) for v in obj.data.vertices],
                "groups": [g.name for g in obj.vertex_groups],
                "weights": [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
                "faces": [list(p.vertices) for p in obj.data.polygons],
                "uv": [[list(item.uv) for item in layer.data] for layer in obj.data.uv_layers]}
        digest.update(json.dumps(data, sort_keys=True).encode())
    return digest.hexdigest()


try:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    character_designer.register()
    rig = bpy.data.objects["CoshaRig"]
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    assert bpy.ops.character_designer.limb_ik_analyze() == {"FINISHED"}
    names = [b.name for b in rig.data.bones if b.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE]
    initial = matrices(rig, names)
    immutable = weights_and_geometry()
    for side in ("L", "R"):
        before_layout = bone_collections.capture_managed_layout(rig)
        foot_controls.build(bpy.context, rig, ("LEG", side))
        bone_collections.finish_rig_edit(rig, before_layout)
        limb_ik_fk._verify(rig, initial)
    report["checks"].append("Build both sides preserves every native bone pose")
    inventory = limb_ik._validate_inventory(rig)
    foot_controls.validate(rig, inventory)
    assert weights_and_geometry() == immutable
    preview = ROOT / "outputs" / "rig" / "X_foot_controls_046_preview.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(preview), copy=True)
    report["preview"] = str(preview)
    for side in ("L", "R"):
        key = ("LEG", side)
        record = foot_controls.get_record(rig, key)
        toe = rig.pose.bones[record["toe_control"]]
        roll = rig.pose.bones[record["roll"]]
        saved_toe, saved_roll = toe.matrix_basis.copy(), roll.matrix_basis.copy()
        for angle in (-0.25, 0.30, 1.05):
            roll.rotation_euler.x = angle
            toe.rotation_euler.x = 0.12
            desired = matrices(rig, names)
            limb_ik_fk.switch_limb(bpy.context, rig, key, "FK")
            limb_ik_fk._verify(rig, desired)
            limb_ik_fk.switch_limb(bpy.context, rig, key, "IK")
            limb_ik_fk._verify(rig, desired)
        # Independent toe bending must not move the foot or its ankle.
        foot_name = inventory["rigs"][key]["chain"][2]
        foot_before = matrices(rig, (foot_name,))
        toe.rotation_euler.x += 0.2
        limb_ik_fk._update(bpy.context, rig)
        limb_ik_fk._verify(rig, foot_before)
        toe.matrix_basis, roll.matrix_basis = saved_toe, saved_roll
        limb_ik_fk._update(bpy.context, rig)
    report["checks"].append("Positive, negative and high roll plus toe bend match through FK/IK on both sides")
    report["checks"].append("Toe Bend leaves the ankle and foot unchanged")
    assert weights_and_geometry() == immutable
    for side in ("L", "R"):
        desired = matrices(rig, names)
        layout = bone_collections.capture_managed_layout(rig)
        foot_controls.remove(bpy.context, rig, ("LEG", side))
        bone_collections.finish_rig_edit(rig, layout)
        limb_ik_fk._verify(rig, desired)
    assert not foot_controls.records(rig)
    assert not [b for b in rig.data.bones if b.get(foot_controls.OWNER_KEY) == foot_controls.OWNER_VALUE]
    limb_ik._validate_inventory(rig)
    assert weights_and_geometry() == immutable
    report["checks"].append("Remove restores base controls without a pose jump; weights, geometry and UV unchanged")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    report["source_unchanged"] = True
    report["ok"] = True
except Exception as exc:
    report["error"] = str(exc)
    report["traceback"] = traceback.format_exc()
    raise
finally:
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FOOT_CONTROLS_X_RESULT", json.dumps(report, ensure_ascii=False))
