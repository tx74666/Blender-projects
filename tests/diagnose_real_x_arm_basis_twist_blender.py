"""Disposable search for a Pose basis twist that decouples X arm roll from bend."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT / "addons", PROJECT_ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import character_designer
from character_designer import limb_ik
import diagnose_real_x_arm_ik_frame_tradeoff_blender as tradeoff
import diagnose_real_x_arm_twist_blender as twist
import probe_limb_ik_real_x_blender as probe
import probe_real_x_0292_rebuild_blender as repeat_probe
import test_real_x_pole_direction_migration_blender as migration


def _candidate(angle, metrics):
    return {
        "basis_y_degrees": angle,
        "bend_dot": metrics["bend_to_projected_plus_y_dot"],
        "upper_roll": metrics["bones"][next(name for name in metrics["bones"] if "upper_arm" in name)]["roll_degrees"],
        "forearm_roll": metrics["bones"][next(name for name in metrics["bones"] if "forearm" in name)]["roll_degrees"],
        "max_abs_roll": metrics["max_abs_roll_degrees"],
    }


def _search(armature, baseline, side, apply_upper, apply_forearm):
    names = (f"upper_arm.{side}", f"forearm.{side}")
    bones = [armature.pose.bones[name] for name in names]
    bases = [bone.matrix_basis.copy() for bone in bones]
    records = []
    try:
        for angle in range(-180, 181, 2):
            rotation = Matrix.Rotation(math.radians(angle), 4, "Y")
            bones[0].matrix_basis = bases[0] @ rotation if apply_upper else bases[0]
            bones[1].matrix_basis = bases[1] @ rotation if apply_forearm else bases[1]
            bpy.context.view_layer.update()
            records.append((float(angle), tradeoff._arm_metrics(armature, baseline, side)))
        coarse = min(
            records,
            key=lambda item: (
                0.0 if item[1]["bend_to_projected_plus_y_dot"] >= 0.999 else 1000.0,
                item[1]["max_abs_roll_degrees"],
                -item[1]["bend_to_projected_plus_y_dot"],
            ),
        )[0]
        for index in range(-40, 41):
            angle = coarse + index * 0.05
            if not -180.0 <= angle <= 180.0:
                continue
            rotation = Matrix.Rotation(math.radians(angle), 4, "Y")
            bones[0].matrix_basis = bases[0] @ rotation if apply_upper else bases[0]
            bones[1].matrix_basis = bases[1] @ rotation if apply_forearm else bases[1]
            bpy.context.view_layer.update()
            records.append((angle, tradeoff._arm_metrics(armature, baseline, side)))
    finally:
        for bone, basis in zip(bones, bases):
            bone.matrix_basis = basis
        bpy.context.view_layer.update()
    bend_feasible = [item for item in records if item[1]["bend_to_projected_plus_y_dot"] >= 0.999]
    best_joint = min(
        bend_feasible,
        key=lambda item: item[1]["max_abs_roll_degrees"],
    ) if bend_feasible else None
    best_roll = min(records, key=lambda item: item[1]["max_abs_roll_degrees"])
    best_bend = max(records, key=lambda item: item[1]["bend_to_projected_plus_y_dot"])
    return {
        "apply_upper": apply_upper,
        "apply_forearm": apply_forearm,
        "best_with_bend_dot_ge_0_999": _candidate(*best_joint) if best_joint else None,
        "best_roll": _candidate(*best_roll),
        "best_bend": _candidate(*best_bend),
        "simultaneous_under_5deg": bool(best_joint and best_joint[1]["max_abs_roll_degrees"] <= 5.0),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    path = Path(args[0]).resolve()
    fingerprint = twist._fingerprint(path)
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    character_designer.register()
    armature = migration._find_real_armature()
    migration._mode_set(bpy.context, armature, "POSE")
    inventory = limb_ik._validate_inventory(armature)
    repeat_probe._repair_known_collection_drift(armature, inventory)
    assert bpy.ops.character_designer.limb_ik_remove() == {"FINISHED"}
    baseline = twist._bone_only_snapshot(armature)
    assert bpy.ops.character_designer.limb_ik_analyze() == {"FINISHED"}
    settings = bpy.context.window_manager.character_designer_limb_ik
    for key in (("ARM", "L"), ("ARM", "R")):
        settings.selected_limb = probe.SELECTED_LIMBS[key]
        assert bpy.ops.character_designer.limb_ik_default_pole_direction() == {"FINISHED"}
    assert bpy.ops.character_designer.limb_ik_build_arm() == {"FINISHED"}
    result = {"sides": {}, "fingerprint": fingerprint}
    for side in ("L", "R"):
        result["sides"][side] = {
            "both": _search(armature, baseline, side, True, True),
            "upper_only": _search(armature, baseline, side, True, False),
            "forearm_only": _search(armature, baseline, side, False, True),
        }
    result["disk_unchanged"] = twist._fingerprint(path) == fingerprint
    print("REAL_X_ARM_BASIS_TWIST_JSON=" + json.dumps(result, sort_keys=True))
    print("PASS real-X basis twist search")


if __name__ == "__main__":
    main()
