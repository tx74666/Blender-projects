"""Disposable real-file verification for the normalized full-rig breast blend.

The caller loads ``X.blend`` in a background Blender process.  This script runs
the operator in memory, audits the repaired result, and intentionally never
saves the file.
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
from character_designer import selected_bone_weights


MESH_NAME = "Cosha"
ARMATURE_NAME = "metarig"
TARGET_NAME = "breast.L"
PAIR_NAME = "breast.R"


def state_weight_map(states, name):
    state = selected_bone_weights._group_state_map(states).get(name)
    return selected_bone_weights._state_weight_map(state)


def main():
    character_designer.register()
    mesh_obj = bpy.data.objects[MESH_NAME]
    armature_obj = bpy.data.objects[ARMATURE_NAME]
    before = selected_bone_weights._capture_vertex_groups(mesh_obj)
    before_target = state_weight_map(before, TARGET_NAME)

    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in armature_obj.pose.bones:
        pose_bone.select = pose_bone.name == TARGET_NAME
    armature_obj.data.bones.active = armature_obj.data.bones[TARGET_NAME]

    result = bpy.ops.character_designer.auto_weight_selected_bones(
        normalize_affected_deform_weights=True,
    )
    if result != {"FINISHED"}:
        raise AssertionError(f"Real breast Full Auto Blend failed: {result}")

    after = selected_bone_weights._capture_vertex_groups(mesh_obj)
    after_target = state_weight_map(after, TARGET_NAME)
    pair = state_weight_map(after, PAIR_NAME)
    deform_names = tuple(
        bone.name
        for bone in armature_obj.data.bones
        if bone.use_deform and mesh_obj.vertex_groups.get(bone.name) is not None
    )
    after_by_name = selected_bone_weights._group_state_map(after)
    deform_maps = {
        name: selected_bone_weights._state_weight_map(after_by_name.get(name))
        for name in deform_names
    }
    affected = sorted(
        set(index for index, weight in before_target.items() if weight > 1.0e-8)
        | set(index for index, weight in after_target.items() if weight > 1.0e-8)
    )
    totals = {
        index: sum(weights.get(index, 0.0) for weights in deform_maps.values())
        for index in affected
    }
    target_indices = tuple(
        index for index, weight in after_target.items() if weight > 1.0e-8
    )
    target_min_z = min(
        (float(mesh_obj.data.vertices[index].co.z) for index in target_indices),
        default=0.0,
    )
    payload = {
        "operator_result": sorted(result),
        "before_target_vertices": sum(
            1 for weight in before_target.values() if weight > 1.0e-8
        ),
        "after_target_vertices": len(target_indices),
        "affected_union_vertices": len(affected),
        "after_target_max": max(after_target.values(), default=0.0),
        "after_target_ge_099": sum(
            1 for weight in after_target.values() if weight >= 0.99
        ),
        "after_target_min_local_z": target_min_z,
        "pair_memberships": len(pair),
        "deform_total_min": min(totals.values(), default=0.0),
        "deform_total_max": max(totals.values(), default=0.0),
        "off_budget_vertices": sum(
            1 for value in totals.values() if abs(value - 1.0) > 1.0e-5
        ),
    }
    if payload["after_target_max"] < 0.999:
        raise AssertionError("The real breast result has no full-weight core")
    if payload["after_target_min_local_z"] < -0.5:
        raise AssertionError("The repaired breast still reaches lower-body vertices")
    if pair:
        raise AssertionError("The generated-side breast.R base group is not empty")
    if payload["off_budget_vertices"]:
        raise AssertionError("The repaired breast region is not normalized")
    print("REAL_BREAST_FULL_AUTO_BLEND_JSON=" + json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
