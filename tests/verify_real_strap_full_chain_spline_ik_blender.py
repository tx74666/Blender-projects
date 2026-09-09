"""Read-only acceptance probe for the real full 13-bone Strap chain.

The loaded autosave is changed only in memory and is never saved.
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

import character_designer
from character_designer import spline_ik_setup


CHAIN = (
    "DEF_Strap_01.L",
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
    "DEF_Strap_01.R",
)


def assert_vector_close(actual, expected, tolerance=1.0e-5):
    if (Vector(actual) - Vector(expected)).length > tolerance:
        raise AssertionError(f"Expected {tuple(expected)}, got {tuple(actual)}")


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
        raise AssertionError("The audited full thirteen-bone Strap chain changed")

    expected_root = Vector(armature.data.bones[CHAIN[0]].head_local)
    expected_tip = Vector(armature.data.bones[CHAIN[-1]].tail_local)

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
            raise AssertionError("Could not capture the audited full Strap chain")
        settings = bpy.context.window_manager.character_designer_spline_ik
        if tuple(json.loads(settings.chain_names_json)) != CHAIN:
            raise AssertionError("Capture reordered or shortened the full Strap chain")

        # Reproduce the user's screenshot: Build from Object Mode while a Mesh,
        # rather than the captured Armature, is active.
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        unrelated = bpy.data.objects.get("Wide Strap")
        if unrelated is None or unrelated.type != "MESH":
            raise AssertionError("The expected Wide Strap Mesh was not found")
        unrelated.hide_set(False)
        unrelated.hide_viewport = False
        unrelated.select_set(True)
        bpy.context.view_layer.objects.active = unrelated

        settings.point_count = 5
        settings.replace_existing = False
        if bpy.ops.character_designer.spline_ik_build() != {"FINISHED"}:
            raise AssertionError(settings.last_message)

        inventory = spline_ik_setup._rig_inventory(
            bpy.context,
            armature,
            CHAIN,
            settings.active_rig_id,
        )
        constraint = inventory["constraint"]
        controls = inventory["controls"]
        curve = inventory["curve_object"]
        spline = curve.data.splines[0]
        if (
            inventory["constraint_owner"].name != CHAIN[-1]
            or constraint.chain_count != 13
            or constraint.y_scale_mode != "NONE"
            or constraint.xz_scale_mode != "NONE"
            or constraint.use_curve_radius
            or len(controls) != 5
            or len(spline.bezier_points) != 5
        ):
            raise AssertionError("The generated full Strap setup violates its contract")
        assert_vector_close(spline.bezier_points[0].co, expected_root)
        assert_vector_close(spline.bezier_points[-1].co, expected_tip)

        if bpy.ops.character_designer.spline_ik_select_controls() != {"FINISHED"}:
            raise AssertionError(settings.last_message)
        selected_controls = {
            obj for obj in bpy.context.selected_objects if obj in set(controls)
        }
        if selected_controls != set(controls) or bpy.context.view_layer.objects.active is not controls[2]:
            raise AssertionError("Select & Reveal did not select all controls and activate the middle one")
        if bpy.data.objects.get(old_line.name) is not old_line:
            raise AssertionError("The full-chain setup changed the old user-owned Line")
        if Path(source_path).stat().st_mtime_ns != source_mtime or Path(source_path).stat().st_size != source_size:
            raise AssertionError("The read-only verifier unexpectedly changed the autosave file")
        print(
            "PASS real full Strap autosave:",
            "13 bones, root Head to tip Tail, 5 revealed controls, no stretch, no save",
        )
    finally:
        if hasattr(bpy.types.WindowManager, "character_designer"):
            character_designer.unregister()


if __name__ == "__main__":
    main()
