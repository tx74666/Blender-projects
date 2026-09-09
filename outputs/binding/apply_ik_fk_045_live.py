"""Back up and upgrade only the active X character's existing limb controls."""
from datetime import datetime
from pathlib import Path
import json
import bpy
import character_designer
from character_designer import bone_collections, limb_ik, limb_ik_fk

ROOT = Path(r"D:\Blender\Projects\Character\X")
assert Path(bpy.data.filepath).resolve() == (ROOT / "X.blend").resolve()
assert character_designer.bl_info["version"] == (0, 45, 0)


class CD_OT_apply_existing_045(bpy.types.Operator):
    bl_idname = "character_designer.apply_existing_045"
    bl_label = "Upgrade Existing Limb Controls"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        rig = bpy.data.objects.get("CoshaRig")
        assert rig is not None and rig.type == "ARMATURE"
        assert context.scene.character_designer_setup.rig == rig
        assert rig.mode in {"OBJECT", "POSE"}
        inventory = limb_ik._validate_inventory(rig)
        assert inventory["rigs"]
        before = {bone.name: rig.pose.bones[bone.name].matrix.copy()
                  for bone in rig.data.bones if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE}
        layout = bone_collections.snapshot_layout(rig)
        missing = {key for key, side in inventory["rigs"].items()
                   if limb_ik_fk.VERSION_KEY not in side["target"]}
        backup = ROOT / "outputs" / "binding" / "backups" / ("X_before_ik_fk_045_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".blend")
        backup.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
        try:
            limb_ik_fk.ensure_switching(rig, inventory)
            context.view_layer.update()
            limb_ik_fk._verify(rig, before)
            bone_collections.simplify_body_collections(rig, original_layout=layout)
            limb_ik_fk._verify(rig, before)
        except Exception:
            for key in missing:
                side = inventory["rigs"][key]
                target = rig.pose.bones[side["target"].name]
                for entry in side["entries"]:
                    if limb_ik_fk.is_switch_constraint(rig, *entry):
                        entry[1].driver_remove("influence")
                        entry[1].influence = 1.0
                for owner, prop in ((target, limb_ik_fk.PROPERTY), (target.bone, limb_ik_fk.VERSION_KEY)):
                    if prop in owner:
                        del owner[prop]
            bone_collections.restore_layout(rig, layout)
            context.view_layer.update()
            raise
        context.window_manager.character_designer.ui_page = "RIG"
        context.window_manager.character_designer.rig_section = "BODY"
        for obj in context.selected_objects:
            obj.select_set(False)
        rig.select_set(True)
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="POSE")
        settings = context.window_manager.character_designer_limb_ik
        bpy.ops.character_designer.limb_ik_analyze()
        settings.selected_limb = "LEFT_LEG"
        report = {"ok": True, "backup": str(backup), "source_file": bpy.data.filepath,
                  "version": list(character_designer.bl_info["version"]),
                  "limbs": [list(key) for key in inventory["rigs"]],
                  "pose_errors": list(limb_ik_fk._pose_errors(rig, before)),
                  "collections": [{"name": c.name, "visible": c.is_visible, "bones": len(c.bones)} for c in rig.data.collections],
                  "main_file_overwritten": False}
        (ROOT / "outputs" / "binding" / "ik_fk_045_live_result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("IK_FK_045_LIVE", json.dumps(report))
        self.report({"INFO"}, "Existing limb controls upgraded; current pose preserved and original layout backed up.")
        return {"FINISHED"}


if hasattr(bpy.types, "CD_OT_apply_existing_045"):
    bpy.utils.unregister_class(bpy.types.CD_OT_apply_existing_045)
bpy.utils.register_class(CD_OT_apply_existing_045)
bpy.ops.character_designer.apply_existing_045()
