"""Read-only acceptance probe for the real Strap chain in an X autosave.

This script intentionally mutates only the in-memory background copy and never
saves. Run with Blender 5.2 and an autosave path before ``--python``.
"""

import json
import sys
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

import character_designer
from character_designer import spline_ik_setup


CHAIN = (
    "DEF_Strap_02.L",
    "DEF_Strap_03.L",
    "DEF_Strap_04.L",
    "DEF_Strap_05.L",
    "DEF_Strap_06.L",
    "DEF_Strap_C",
    "DEF_Strap_06.R",
    "DEF_Strap_05.R",
    "DEF_Strap_04.R",
    "DEF_Strap_03.R",
    "DEF_Strap_02.R",
)


def main():
    source_path = bpy.data.filepath
    if not source_path.lower().endswith(".blend") or "autosave" not in source_path.lower():
        raise AssertionError("Run this verifier only against a copied/read-only autosave file")
    source_mtime = Path(source_path).stat().st_mtime_ns
    source_size = Path(source_path).stat().st_size

    armature = bpy.data.objects.get("Strap.001")
    old_line = bpy.data.objects.get("Line")
    if armature is None or armature.type != "ARMATURE" or old_line is None:
        raise AssertionError("The expected Strap.001 Armature and Line Curve were not found")
    if any(armature.data.bones.get(name) is None for name in CHAIN):
        raise AssertionError("The audited eleven-bone Strap chain changed")

    character_designer.register()
    try:
        if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        armature.hide_set(False)
        armature.hide_viewport = False
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="POSE")
        selected = set(CHAIN)
        for pose_bone in armature.pose.bones:
            pose_bone.select = pose_bone.name in selected
        armature.data.bones.active = armature.data.bones[CHAIN[-1]]

        if bpy.ops.character_designer.spline_ik_capture_chain() != {"FINISHED"}:
            raise AssertionError("Could not capture the audited Strap chain")
        settings = bpy.context.window_manager.character_designer_spline_ik
        if tuple(json.loads(settings.chain_names_json)) != CHAIN:
            raise AssertionError("Capture reordered or expanded the real Strap chain")
        settings.point_count = 5
        settings.replace_existing = True
        if bpy.ops.character_designer.spline_ik_build() != {"FINISHED"}:
            raise AssertionError(settings.last_message)

        rig_id = settings.active_rig_id
        inventory = spline_ik_setup._rig_inventory(
            bpy.context,
            armature,
            CHAIN,
            rig_id,
        )
        constraint = inventory["constraint"]
        controls = inventory["controls"]
        curve = inventory["curve_object"]
        if (
            inventory["constraint_owner"].name != CHAIN[-1]
            or constraint.chain_count != 11
            or constraint.y_scale_mode != "NONE"
            or constraint.xz_scale_mode != "NONE"
            or constraint.use_curve_radius
            or len(controls) != 5
            or len(curve.data.splines) != 1
            or len(curve.data.splines[0].bezier_points) != 5
        ):
            raise AssertionError("The generated real Strap setup violates its contract")
        if bpy.data.objects.get(old_line.name) is not old_line or old_line.type != "CURVE":
            raise AssertionError("Replacing the old constraint deleted its user-owned Line target")
        if any(
            constraint.type == "SPLINE_IK" and constraint.target is old_line
            for pose_bone in armature.pose.bones
            for constraint in pose_bone.constraints
        ):
            raise AssertionError("The replaced foreign Spline IK constraint survived")
        if Path(source_path).stat().st_mtime_ns != source_mtime or Path(source_path).stat().st_size != source_size:
            raise AssertionError("The read-only verifier unexpectedly changed the autosave file")
        print(
            "PASS real Strap autosave:",
            "11 bones, 5 controls, old Line preserved, no stretch, no save",
        )
    finally:
        if hasattr(bpy.types.WindowManager, "character_designer"):
            character_designer.unregister()


if __name__ == "__main__":
    main()
