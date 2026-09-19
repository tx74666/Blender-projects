"""Apply only safe surface-weight repairs to a copied current X.blend.

The source X.blend is opened by Blender before this script runs.  This script
never opens or saves the user's source file; the command line supplies a
review-copy path and an audit-report path.
"""

from pathlib import Path
import hashlib
import json
import math
import sys

import bpy


ROOT = Path(__file__).resolve().parent
CANONICAL = Path(r"D:\MyRepository\Blender-addons-by-Randy\addons")
sys.path.insert(0, str(CANONICAL))
from character_designer import weight_surface as surface
from character_designer import weight_symmetry as ws


def group_maps(states):
    return {state.name: dict(state.weights) for state in states}


def geometry_snapshot(obj, rig):
    mesh = obj.data
    shapes = mesh.shape_keys
    return (
        tuple(tuple(v.co) for v in mesh.vertices),
        tuple(tuple(e.vertices) for e in mesh.edges),
        tuple((tuple(p.vertices), p.material_index, p.use_smooth)
              for p in mesh.polygons),
        tuple((uv.name, tuple(tuple(v.uv) for v in uv.data))
              for uv in mesh.uv_layers),
        tuple(material.name_full if material else None for material in mesh.materials),
        None if shapes is None else (
            shapes.name,
            tuple((key.name, key.value, key.mute, key.slider_min, key.slider_max,
                   key.vertex_group, key.relative_key.name if key.relative_key else None,
                   tuple(tuple(v.co) for v in key.data))
                  for key in shapes.key_blocks),
        ),
        tuple((bone.name, bone.parent.name if bone.parent else None,
               bone.use_deform, tuple(bone.head_local), tuple(bone.tail_local),
               tuple(tuple(row) for row in bone.matrix_local))
              for bone in rig.data.bones),
        tuple(tuple(row) for row in obj.matrix_world),
        tuple(tuple(row) for row in rig.matrix_world),
    )


def object_fingerprints():
    result = {}
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        payload = (
            obj.type,
            obj.parent.name if obj.parent else None,
            tuple(obj.location), tuple(obj.rotation_euler), tuple(obj.scale),
            tuple(tuple(row) for row in obj.matrix_world),
            tuple((mod.name, mod.type,
                   getattr(getattr(mod, "object", None), "name", None))
                  for mod in obj.modifiers),
        )
        if obj.type == "MESH":
            mesh = obj.data
            payload += (
                tuple(tuple(vertex.co) for vertex in mesh.vertices),
                tuple(tuple(edge.vertices) for edge in mesh.edges),
                tuple((tuple(poly.vertices), poly.material_index, poly.use_smooth)
                      for poly in mesh.polygons),
            )
        elif obj.type == "ARMATURE":
            payload += (tuple((bone.name, bone.parent.name if bone.parent else None,
                               bone.use_deform, tuple(bone.head_local), tuple(bone.tail_local),
                               tuple(tuple(row) for row in bone.matrix_local))
                              for bone in obj.data.bones),)
        result[obj.name] = hashlib.sha256(repr(payload).encode()).hexdigest()
    return result


def changed_groups(before, after):
    before_map = group_maps(before)
    after_map = group_maps(after)
    result = {}
    for name in sorted(set(before_map) | set(after_map)):
        old = before_map.get(name, {})
        new = after_map.get(name, {})
        indices = sorted(index for index in set(old) | set(new)
                         if old.get(index) != new.get(index))
        if indices:
            result[name] = indices
    return result


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    review = Path(args[0]).resolve() if args else ROOT / "X_current_weight_mirror_review.blend"
    report_path = Path(args[1]).resolve() if len(args) > 1 else ROOT / "current_weight_mirror_report.json"

    obj = bpy.data.objects["Cosha"]
    rig = bpy.data.objects["CoshaRig"]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    before_groups = ws._capture_vertex_groups(obj)
    before_maps = group_maps(before_groups)
    before_geometry = geometry_snapshot(obj, rig)
    before_objects = object_fingerprints()
    deform_names = {bone.name for bone in rig.data.bones if bone.use_deform}
    active_group_index = obj.vertex_groups.active_index
    before_totals = [sum(before_maps.get(name, {}).get(index, 0.0)
                         for name in deform_names)
                     for index in range(len(obj.data.vertices))]
    tolerance = ws._automatic_tolerance(obj)
    source_name = "upper_arm.L"
    source_side = ws._bone_source_side(
        obj, rig, source_name, ws._strict_opposite_name(source_name), tolerance
    )
    source_indices, _target_indices, center_indices = ws._classify_mesh_halves(
        obj, source_side, tolerance
    )
    protected_indices = set(source_indices) | set(center_indices)

    operations = []
    affected = set()
    for source in ("upper_arm.L", "forearm.L", "thumb.03.L"):
        plan = surface.build_surface_plan_for_sources(
            bpy.context, obj, rig, (source,)
        )
        surface.apply_surface_plan(plan)
        affected.update(plan.affected_indices)
        operations.append({
            "source": source,
            "target": plan.target_names[0],
            "sampled_count": plan.sampled_count,
            "affected_count": len(plan.affected_indices),
            "affected_indices": list(plan.affected_indices),
            "max_sample_distance": plan.max_sample_distance,
            "distance_limit": plan.distance_limit,
        })

    after_groups = ws._capture_vertex_groups(obj)
    changes = changed_groups(before_groups, after_groups)
    after_maps = group_maps(after_groups)
    changed_indices = sorted({index for indices in changes.values() for index in indices})
    assert geometry_snapshot(obj, rig) == before_geometry
    assert object_fingerprints() == before_objects
    assert set(changes) <= deform_names
    assert set(changed_indices) <= affected
    assert not set(changed_indices) & protected_indices
    assert obj.vertex_groups.active_index == active_group_index
    budget_deltas = []
    for index, before_total in enumerate(before_totals):
        after_total = sum(after_maps.get(name, {}).get(index, 0.0)
                          for name in deform_names)
        budget_deltas.append(abs(after_total - before_total))
    assert max(budget_deltas, default=0.0) <= ws.WEIGHT_TOLERANCE
    bpy.ops.wm.save_as_mainfile(filepath=str(review), check_existing=False)
    report = {
        "status": "PASS",
        "input": str(bpy.data.filepath),
        "review": str(review),
        "canonical_weight_surface_sha256": hashlib.sha256(
            (CANONICAL / "character_designer" / "weight_surface.py").read_bytes()
        ).hexdigest(),
        "vertex_count": len(obj.data.vertices),
        "automatic_tolerance": tolerance,
        "operations": operations,
        "changed_groups": {name: {"count": len(indices), "indices": indices}
                           for name, indices in changes.items()},
        "changed_vertex_count": len(changed_indices),
        "max_deform_budget_delta": max(budget_deltas, default=0.0),
        "source_and_center_unchanged": not (set(changed_indices) & protected_indices),
        "geometry_shape_keys_rest_pose_unchanged": geometry_snapshot(obj, rig) == before_geometry,
        "all_other_object_state_unchanged": object_fingerprints() == before_objects,
        "review_sha256": hashlib.sha256(
            Path(bpy.data.filepath).read_bytes()
        ).hexdigest(),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("CURRENT_WEIGHT_MIRROR_REVIEW_PASS", json.dumps({
        key: report[key] for key in (
            "status", "vertex_count", "changed_vertex_count",
            "max_deform_budget_delta", "source_and_center_unchanged",
            "geometry_shape_keys_rest_pose_unchanged",
        )
    }))


if __name__ == "__main__":
    main()
