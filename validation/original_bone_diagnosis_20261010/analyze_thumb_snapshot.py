"""Analyze the saved read-only JSON; never imports bpy or opens an artist file."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "live_readonly.json"
raw = SOURCE.read_bytes()
snap = json.loads(raw)


def maxerr(a, b):
    return max(abs(x - y) for ra, rb in zip(a, b) for x, y in zip(ra, rb))


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def columns(matrix):
    return [math.sqrt(sum(matrix[r][c] ** 2 for r in range(3))) for c in range(3)]


def point(matrix, co):
    return [sum(matrix[r][c] * co[c] for c in range(3)) + matrix[r][3] for r in range(3)]


def box(points):
    if not points:
        return None
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    return {"min": low, "max": high, "extent": [b - a for a, b in zip(low, high)]}


def mesh_summary(mesh, rig):
    vertices = mesh["thumb_vertices"]
    result = {
        "vertices_total": mesh["vertices"],
        "thumb_selected_vertices": len(vertices),
        "armature_target": mesh["rig"],
        "modifiers": mesh["modifiers"],
        "shape_keys": mesh["shape_keys"],
        "rig_relative": mesh["rig_relative"],
        "raw_thumb_bbox": box([v["co"] for v in vertices]),
        "rig_space_thumb_bbox": box([point(mesh["rig_relative"], v["co"]) for v in vertices]),
        "side_stats": {},
    }
    for side in ("L", "R"):
        subset = [v for v in vertices if any(n.startswith("thumb.") and n.endswith("." + side) and w > 0 for n, w in v["weights"].items())]
        thumb_sums = [sum(w for n, w in v["weights"].items() if n.startswith("thumb.") and n.endswith("." + side)) for v in subset]
        grouped = {}
        for v in subset:
            for name, weight in v["weights"].items():
                row = grouped.setdefault(name, {"count": 0, "sum": 0.0, "min": math.inf, "max": 0.0})
                row["count"] += 1
                row["sum"] += weight
                row["min"] = min(row["min"], weight)
                row["max"] = max(row["max"], weight)
        result["side_stats"][side] = {
            "count": len(subset),
            "raw_bbox": box([v["co"] for v in subset]),
            "rig_space_bbox": box([point(mesh["rig_relative"], v["co"]) for v in subset]),
            "thumb_weight_sum_min": min(thumb_sums) if thumb_sums else None,
            "thumb_weight_sum_max": max(thumb_sums) if thumb_sums else None,
            "weights": grouped,
            "high_weight_regions": {},
        }
        for index in (1, 2, 3):
            name = f"thumb.{index:02}.{side}"
            head, tail = rig["bones"][name]["head"], rig["bones"][name]["tail"]
            axis = [(t - h) / distance(head, tail) for h, t in zip(head, tail)]
            for threshold in (0.5, 0.99):
                region = [point(mesh["rig_relative"], v["co"]) for v in subset if v["weights"].get(name, 0) >= threshold]
                projections = [sum((p[i] - head[i]) * axis[i] for i in range(3)) for p in region]
                result["side_stats"][side]["high_weight_regions"][f"{name}>={threshold}"] = {
                    "count": len(region), "bbox": box(region),
                    "rest_axis_projection_min": min(projections) if projections else None,
                    "rest_axis_projection_max": max(projections) if projections else None,
                }
    return result


a = snap["armatures"]["CoshaRig"]
b = snap["armatures"]["CoshaRig.001"]
result = {
    "scope": "offline_json_only_no_scene_operations",
    "input_sha256": hashlib.sha256(raw).hexdigest(),
    "captured_utc": snap["captured_utc"],
    "scenes": [{k: s[k] for k in ("name", "frame", "armatures")} for s in snap["scenes"]],
    "rigs": {},
    "thumb_comparison": {},
    "meshes": {},
    "limitations": [
        "Scenes are at different frames and poses; current evaluated thumb appearance cannot be compared as the same pose.",
        "Source base and returned baked subdivision have different vertex counts; raw index/weight comparison is not equivalent.",
        "Mesh thumb_vertices include only recorded base coordinates and weights, not evaluated displayed coordinates or shape-key deltas.",
        "The snapshot records active Action names and driver paths, not Action curves, NLA tracks or complete driver dependencies.",
    ],
    "findings": [
        "All six native thumb bones and all six thumb weight groups are present; parent/deform contracts match.",
        "thumb.01/.02 heads/tails and all six Rest matrices are nearly unchanged. Both terminal thumb.03 tails are approximately 18% shorter while their heads/Rest axes remain nearly unchanged.",
        "At the captured frame, thumb/hand/forearm scales and evaluated pose column norms are approximately one. Returned thumb bones have no constraints or armature drivers; current scale stretch is not supported.",
        "Returned scene frame 1 has Walk_N Custom active while source frame 46 has no active Action; thumb rotations differ considerably. This prevents a direct displayed-pose comparison.",
        "High-weight thumb.03 raw Basis regions have nearly the same distal reach after rig-space conversion; returned reach is slightly shorter, consistent with smoothing rather than clear base mesh elongation.",
        "Source correction-owned Forearm Twist .002 keys are one; returned mesh omits those keys. Their actual thumb-region deltas are absent from this snapshot.",
    ],
    "minimal_next_readonly_measurements": [
        "Read active returned Action thumb/hand/forearm location/scale FCurves at frame 1 and NLA track state; do not switch frames or Actions.",
        "Read source .002 ShapeKey deltas on the high-weight thumb regions and key mute/relative state; do not toggle values.",
        "Record current depsgraph-evaluated returned high-weight thumb-region coordinates alongside raw Basis coordinates. For an import-fidelity proof, compare with source subdivision Basis/weights in an isolated or already-captured equal-pose reference, using explicit vertex/stencil correspondence rather than unproven index identity.",
        "Read the complete Deform bone-name inventory before judging removed legacy arm_stretch/forearm_stretch/forearm_twist groups; this snapshot only lists selected bones.",
    ],
}
for name, rig in (("CoshaRig", a), ("CoshaRig.001", b)):
    result["rigs"][name] = {k: rig[k] for k in ("data", "bone_count", "object_scale", "matrix_world", "pose_position", "action")}
    result["rigs"][name]["thumb_driver_paths"] = [d for d in rig["animation_drivers"] if "thumb" in d["path"]]
    result["rigs"][name]["drivers_count"] = len(rig["animation_drivers"])
    result["rigs"][name]["related_bones"] = {
        name: {k: bone[k] for k in ("parent", "scale", "location", "rotation_quaternion", "constraints")}
        | {"pose_column_norms": columns(bone["pose"])}
        for name, bone in rig["bones"].items() if name.startswith(("thumb.", "hand.", "forearm."))
    }
for side in ("L", "R"):
    for index in (1, 2, 3):
        name = f"thumb.{index:02}.{side}"
        sa, sb = a["bones"].get(name), b["bones"].get(name)
        if sa is None or sb is None:
            result["thumb_comparison"][name] = {"missing_source": sa is None, "missing_returned": sb is None}
            continue
        result["thumb_comparison"][name] = {
            "head_distance": distance(sa["head"], sb["head"]),
            "tail_distance": distance(sa["tail"], sb["tail"]),
            "source_length": sa["length"],
            "returned_length": sb["length"],
            "length_ratio": sb["length"] / sa["length"],
            "rest_max_error": maxerr(sa["rest"], sb["rest"]),
            "basis_max_error": maxerr(sa["basis"], sb["basis"]),
            "source_scale": sa["scale"],
            "returned_scale": sb["scale"],
            "source_pose_column_norms": columns(sa["pose"]),
            "returned_pose_column_norms": columns(sb["pose"]),
            "parent_equal": sa["parent"] == sb["parent"],
            "source_constraints": sa["constraints"],
            "returned_constraints": sb["constraints"],
            "source_shape": sa["shape"],
            "returned_shape": sb["shape"],
            "source_deform": sa["use_deform"],
            "returned_deform": sb["use_deform"],
        }
for name, rig in (("Cosha", a), ("Cosha.001", b)):
    result["meshes"][name] = mesh_summary(snap["meshes"][name], rig)

output = HERE / "thumb_snapshot_analysis.json"
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == result["input_sha256"]
print(json.dumps({"output": str(output), "thumb_comparison": result["thumb_comparison"], "mesh_summary": {name: {"vertices": row["vertices_total"], "thumb_count": row["thumb_selected_vertices"], "rig": row["armature_target"], "side_summary": {side: {k: sub[k] for k in ("count", "rig_space_bbox", "thumb_weight_sum_min", "thumb_weight_sum_max")} for side, sub in row["side_stats"].items()}} for name, row in result["meshes"].items()}}, ensure_ascii=False, indent=2))
