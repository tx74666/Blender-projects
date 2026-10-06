"""Thin read-only extension of pinned 27e6 Original run60 observations.

Same arguments as diagnose_original_surface_stages.py; new empty background
factory child and fresh output only. No cache/pose/constraint/driver change.
Full neutral/main subset, native wires/tracker and effective constraints locate
the first changed branch. They do not prove a solver's internal cause, speed,
formal mechanics validation, or artistic/Unity acceptance. Extra reads can warm
the graph. Evaluated spline RNA alone is not a post-Hook path proof; the native
to_mesh centreline is collected separately and remains tessellated evidence.
"""
import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
BASE = HERE / "diagnose_original_surface_stages.py"
BASE_SHA = "27e6c7780a7bc89dfb4bb21d20b5d0b7ba783282676f73702322dda5e4b40c2a"
SAMPLE_IDS = (25, 87, 99, 109, 194, 198, 199, 779, 783)


def require(value, message):
    if not value:
        raise RuntimeError(message)


def spline_rna(obj):
    # Primitive RNA values, explicitly not claimed to be the evaluated path cache.
    return [{"type": spline.type, "order_u": spline.order_u, "resolution_u": spline.resolution_u,
             "use_endpoint_u": spline.use_endpoint_u, "use_cyclic_u": spline.use_cyclic_u,
             "points": [{"co": [float(x) for x in point.co], "radius": float(point.radius),
                         "tilt": float(point.tilt)} for point in spline.points]}
            for spline in obj.data.splines]


def constraint_rows(obj, names, graph, surface):
    posed = obj.evaluated_get(graph)
    return {name: {"original": [surface._rna(item) for item in obj.pose.bones[name].constraints],
                   "evaluated": [surface._rna(item) for item in posed.pose.bones[name].constraints]}
            for name in names}


def physics_drivers(obj, names):
    paths = {item.path_from_id() + ".influence" for name in names
             for item in obj.pose.bones[name].constraints if item.name == "Skirt physics delta"}
    curves = obj.animation_data.drivers if obj.animation_data else ()
    return [{"path": curve.data_path, "array_index": curve.array_index, "mute": curve.mute,
             "is_valid": curve.is_valid, "type": curve.driver.type, "expression": curve.driver.expression,
             "variables": [{"name": variable.name, "type": variable.type,
                            "targets": [{"id": target.id.name if target.id else None,
                                         "data_path": target.data_path, "bone_target": target.bone_target}
                                        for target in variable.targets]} for variable in curve.driver.variables]}
            for curve in curves if curve.data_path in paths]


def mesh_weights(obj, graph, points, base):
    posed = obj.evaluated_get(graph)
    mesh = posed.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    try:
        base.require(len(mesh.vertices) == len(points) and all(vertex.index == i for i, vertex in enumerate(mesh.vertices)),
                     "dependency weights changed native index identity")
        repeated = [[float(x) for x in posed.matrix_world @ vertex.co] for vertex in mesh.vertices]
        base.require(repeated == points, "extra same-graph weight readback changed coordinates")
        mapping = {group.index: group.name for group in obj.vertex_groups}
        weights = [[[entry.group, float(entry.weight)] for entry in vertex.groups] for vertex in mesh.vertices]
        base.require(all(index in mapping and math.isfinite(weight) for rows in weights for index, weight in rows),
                     "dependency weight indices/nonfinite values are invalid")
        return mapping, weights
    finally:
        posed.to_mesh_clear()


def main():
    require(bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath,
            "Dependency diagnostic requires an empty isolated factory background child")
    import hashlib
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    own_sha = sha(Path(__file__))
    require(sha(BASE) == BASE_SHA, "Pinned Original stage diagnostic changed")
    spec = importlib.util.spec_from_file_location("observed_original_stage_base", BASE)
    require(spec.name not in sys.modules, "Original stage base is already loaded")
    base = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base
    spec.loader.exec_module(base)
    old_observed, old_pose, old_mesh = base.observed_roundtrip, base.pose_row, base.native_mesh

    def observed(original, workflow, diagnostic, source, rig, actual, cloth, neutral, result, qa, surface, metres):
        record = qa.skirt.read_record(source)
        roles = record["physics"]["surface"]["roles"]
        reference = bpy.data.objects[roles["NEUTRAL_RIG"][0]]
        subset = list(reference.pose.bones.keys())
        base.require(subset and set(subset) <= set(rig.pose.bones.keys()), "complete neutral subset lost main counterparts")
        layers = {name: layer for chain in record["chains"] for layer in ("manual", "phys", "def") for name in chain[layer]}
        wires = [bpy.data.objects[name] for name in roles["NEUTRAL_WIRE"]]
        tracker = bpy.data.objects[roles["TRACKER"][0]]
        base.require(len(wires) == record["chain_count"] == 8, "expected eight exact native neutral wires")
        target_names = {reference.pose.bones[name].constraints[0].subtarget
                        for chain in record["chains"] for name in chain["phys"]}
        marker = {"script": str(Path(__file__)), "sha256": own_sha, "base_sha256": BASE_SHA,
                  "same_graph_extra_reads": True, "formal_validation": False, "production_effect_accepted": False,
                  "scope": "All main/neutral same-name subset matrices, generated constraint/driver input, wire RNA plus tessellated native centreline, tracker points/weights; no solver-internal cause proof",
                  "subset": subset, "bone_layers": layers, "representative_native_indices": list(SAMPLE_IDS)}
        diagnostic["dependency_chain_probe"] = marker

        def pose(obj, _upstream_names, graph):
            base.require(obj is rig or obj is reference, "unexpected pose-row object")
            row = old_pose(obj, subset, graph)
            row["constraint_inputs"] = constraint_rows(obj, subset, graph, surface)
            row["physics_influence_drivers"] = physics_drivers(obj, subset)
            if obj is reference:
                native_wires = {}
                for wire in wires:
                    posed_wire = wire.evaluated_get(graph)
                    native_wires[wire.name] = {"original_matrix_world": base.matrix(wire.matrix_world),
                        "evaluated_matrix_world": base.matrix(posed_wire.matrix_world),
                        "original_spline_rna": spline_rna(wire), "evaluated_spline_rna": spline_rna(posed_wire),
                        "rna_scope": "RNA control-point values; post-Hook cache correspondence not assumed",
                        "native_tessellated_centreline": old_mesh(wire, graph)}
                tracker_mesh = old_mesh(tracker, graph)
                mapping, weights = mesh_weights(tracker, graph, tracker_mesh["points"], base)
                base.require(target_names <= set(mapping.values()), "an exact PHYS tracker target group is absent")
                targets = {}
                for group_index, name in mapping.items():
                    total = math.fsum(weight for rows in weights for index, weight in rows if index == group_index)
                    if name in target_names:
                        base.require(total > 0., "tracker target has no actual native weight")
                        targets[name] = {"group_index": group_index, "weight_sum": total,
                            "native_weighted_world_centroid": [math.fsum(point[axis]*weight
                                for point, rows in zip(tracker_mesh["points"], weights)
                                for index, weight in rows if index == group_index)/total for axis in range(3)]}
                holder, driver_id, path = qa.skirt.physics_control(source)
                posed_main = rig.evaluated_get(graph)
                evaluated_holder = posed_main.pose.bones[holder.name] if hasattr(holder, "bone") else posed_main
                row["native_auxiliary"] = {"graph_pointer": graph.as_pointer(), "neutral_wires": native_wires,
                    "tracker": {"mesh": tracker_mesh, "group_mapping": mapping, "weights": weights,
                                "target_centroids": targets, "centroid_scope": "Actual weighted target position, not complete native target matrix/cache proof"},
                    "physics_control": {"id": driver_id.name, "path": path,
                        "original_influence": float(holder.get("physics_influence")),
                        "evaluated_influence": float(evaluated_holder.get("physics_influence"))}}
            return row

        def mesh(obj, graph):
            row = old_mesh(obj, graph)
            if row["count"] == 800:
                mapping, weights = mesh_weights(obj, graph, row["points"], base)
                row["native_deform_group_mapping"] = mapping
                row["native_deform_weights_available"] = any(weights)
                row["representative_native_deform_weights"] = {str(index): weights[index] for index in SAMPLE_IDS}
            return row

        base.pose_row, base.native_mesh = pose, mesh
        try:
            return old_observed(original, workflow, diagnostic, source, rig, actual, cloth, neutral, result, qa, surface, metres)
        finally:
            base.pose_row, base.native_mesh = old_pose, old_mesh
            marker["wrapper_source_exact_after_observed_roundtrip"] = sha(Path(__file__)) == own_sha and sha(BASE) == BASE_SHA
            marker["top_matrix_differences"] = {stage["label"]: {
                comparison: sorted(stage[comparison]["matrix_element_errors"].items(), key=lambda item: item[1], reverse=True)[:24]
                for comparison in ("from_active_baseline", "from_previous_stage") if comparison in stage}
                for stage in diagnostic["stages"]}
            base.require(marker["wrapper_source_exact_after_observed_roundtrip"], "dependency wrapper source changed")

    base.observed_roundtrip = observed
    try:
        return base.main()  # Full unchanged workflow/bake/failure/50um/reload/source/raw/disk AND remains in pinned base.
    finally:
        base.observed_roundtrip, base.pose_row, base.native_mesh = old_observed, old_pose, old_mesh
        require(sha(Path(__file__)) == own_sha and sha(BASE) == BASE_SHA, "dependency source changed during full workflow")
        print(json.dumps({"dependency_chain_wrapper_source_exact_after_full_workflow": True,
                          "script_sha256": own_sha, "base_sha256": BASE_SHA,
                          "formal_validation": False}), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
