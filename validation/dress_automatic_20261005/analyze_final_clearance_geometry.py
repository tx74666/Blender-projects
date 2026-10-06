"""Offline geometry observations from exact native final-surface A/B snapshots.

Uses only Python's standard library. No Blender, Unity, subprocess, artist save,
deployment or ledger writes. Completion means data collection, never art quality.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys


REGIONS = ("hard_fixed_waist", "mixed_waist_transition", "free_skirt")
FIXED_WEIGHT = .999  # Exact cutoff already used by the native snapshot writer.
NORMAL_CANDIDATE_DOT = -.5  # >120 degrees; observation only, not a flip guard.
COORDINATES = ("Actual evaluated world units, in unchanged exact native vertex order; "
               "multiply by units_to_metres for metres")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def file_state(path):
    stat = path.stat()
    return {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def vector(value):
    return isinstance(value, list) and len(value) == 3 and all(number(item) for item in value)


def load_snapshot(path, label):
    def reject_constant(value):
        raise ValueError("Nonfinite JSON constant: " + value)
    data = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    require(data.get("label") == label, "Filename/native operation label mismatch")
    require(type(data.get("frame")) is int and data["frame"] >= 1, "Missing integer native frame")
    require(number(data.get("units_to_metres")) and data["units_to_metres"] > 0., "Unknown physical units")
    require(data.get("coordinates") == COORDINATES, "Unknown coordinate or vertex-order declaration")
    surfaces = data.get("points", {})
    for name, count in (("Body", None), ("C800", 800), ("H0800", 800), ("O3040", 3040)):
        points = surfaces.get(name)
        require(isinstance(points, list) and points and all(vector(point) for point in points),
                "Missing/nonfinite evaluated " + name)
        require((count is None and len(points) <= 100000) or len(points) == count,
                "Unexpected exact evaluated vertex count: " + name)
    require(isinstance(data.get("knees"), dict) and set(data["knees"]) == {"L", "R"}
            and all(vector(point) for point in data["knees"].values()) and vector(data.get("hem")),
            "Missing/nonfinite native input markers")
    fields = data.get("final_per_vertex_diagnostic_fields", {})
    require(fields.get("status") == "measured" and fields.get("weight_layer_complete") is True
            and fields.get("final_vertices") == 3040, "Final native identity/weight proof missing")
    weights = fields.get("waist_weights_by_exact_final_vertex_index")
    require(isinstance(weights, list) and len(weights) == 3040
            and all(number(weight) and 0. <= weight <= 1. for weight in weights), "Incomplete native waist weights")
    free = [index for index, weight in enumerate(weights) if weight < FIXED_WEIGHT]
    fixed = [index for index, weight in enumerate(weights) if weight >= FIXED_WEIGHT]
    require(free and fixed and fields.get("free_vertex_indices") == free
            and fields.get("hard_fixed_vertex_indices") == fixed
            and fields.get("final_free_vertices") == len(free), "Native free/fixed index partition is incomplete")
    topology = fields.get("native_topology")
    require(isinstance(topology, dict) and set(topology) == {"edges", "faces", "triangles"}, "Missing full native topology")
    for name, arity in (("edges", 2), ("faces", None), ("triangles", 3)):
        entries = topology[name]
        require(isinstance(entries, list) and entries, "Empty native topology: " + name)
        require(all(isinstance(entry, list) and (len(entry) == arity if arity else len(entry) >= 3)
                    and all(type(index) is int and 0 <= index < 3040 for index in entry) for entry in entries),
                "Invalid native topology indices: " + name)
    require(fields.get("native_topology_sha256") == digest(topology), "Native topology hash does not match content")
    return data


def region(indices, weights):
    selected = [weights[index] for index in indices]
    if all(weight >= FIXED_WEIGHT for weight in selected):
        return "hard_fixed_waist"
    if any(weight > 0. for weight in selected):
        return "mixed_waist_transition"
    return "free_skirt"


def subtract(first, second):
    return tuple(a-b for a, b in zip(first, second))


def cross(first, second):
    return (first[1]*second[2]-first[2]*second[1], first[2]*second[0]-first[0]*second[2],
            first[0]*second[1]-first[1]*second[0])


def finite(value, reason):
    require(number(value), reason)
    return float(value)


def scalar_summary(records, key):
    valid = [item for item in records if item[key] is not None]
    unknown = [item["index"] for item in records if item[key] is None]
    values = sorted(item[key] for item in valid)
    return {"status": "no_samples" if not records else "unproven_denominators" if unknown else "measured",
            "total_samples": len(records), "measured_samples": len(values), "unknown_indices": unknown,
            "minimum": values[0] if values else None, "maximum": values[-1] if values else None,
            "median": statistics.median(values) if values else None,
            "p95_nearest_rank": values[max(0, math.ceil(.95*len(values))-1)] if values else None,
            "worst_low": sorted(valid, key=lambda item: (item[key], item["index"]))[:8],
            "worst_high": sorted(valid, key=lambda item: (-item[key], item["index"]))[:8]}


def summarize_geometry(vertices, edges, triangles):
    candidates = [item["index"] for item in triangles
                  if item["normal_dot"] is not None and item["normal_dot"] < NORMAL_CANDIDATE_DOT]
    return {"vertex_displacement_m": scalar_summary(vertices, "displacement_m"),
            "edge_length_ratio_projected_over_baseline": scalar_summary(edges, "length_ratio"),
            "triangle_area_ratio_projected_over_baseline": scalar_summary(triangles, "area_ratio"),
            "nondegenerate_triangle_normal_dot": scalar_summary(triangles, "normal_dot"),
            "baseline_low_area_triangle_indices": [item["index"] for item in triangles if item["baseline_low_area"]],
            "projected_low_area_triangle_indices": [item["index"] for item in triangles if item["projected_low_area"]],
            "baseline_low_length_edge_indices": [item["index"] for item in edges if item["baseline_low_length"]],
            "projected_low_length_edge_indices": [item["index"] for item in edges if item["projected_low_length"]],
            "opposed_normal_candidate_triangle_indices": candidates,
            "opposed_normal_candidate_dot_cutoff": NORMAL_CANDIDATE_DOT,
            "true_flips_accepted": False}


def analyze_pair(case, baseline, projected, edge_floor, area_floor):
    require(baseline["frame"] == projected["frame"] and baseline["units_to_metres"] == projected["units_to_metres"],
            "A/B native frame or physical units differ")
    a_fields, b_fields = (item["final_per_vertex_diagnostic_fields"] for item in (baseline, projected))
    for name in ("native_topology", "native_topology_sha256", "waist_weights_by_exact_final_vertex_index",
                 "free_vertex_indices", "hard_fixed_vertex_indices"):
        require(a_fields[name] == b_fields[name], "A/B exact final order/topology/weights differ: " + name)
    units = float(baseline["units_to_metres"])
    input_deltas = {}
    for name in ("Body", "C800", "H0800"):
        first, second = baseline["points"][name], projected["points"][name]
        require(len(first) == len(second), "A/B non-Dress evaluated identity differs: " + name)
        input_deltas[name] = finite(max(math.dist(a, b)*units for a, b in zip(first, second)), "Nonfinite input delta")
    for name in ("L", "R"):
        input_deltas["knee."+name] = finite(math.dist(baseline["knees"][name], projected["knees"][name])*units,
                                            "Nonfinite knee delta")
    input_deltas["hem"] = finite(math.dist(baseline["hem"], projected["hem"])*units, "Nonfinite hem delta")
    same_input = all(value == 0. for value in input_deltas.values())
    first = [tuple(value*units for value in point) for point in baseline["points"]["O3040"]]
    second = [tuple(value*units for value in point) for point in projected["points"]["O3040"]]
    require(all(all(number(value) for value in point) for point in first+second), "Nonfinite metre conversion")
    weights = a_fields["waist_weights_by_exact_final_vertex_index"]
    vertices = [{"index": index, "region": region((index,), weights),
                 "displacement_m": finite(math.dist(a, b), "Nonfinite final vertex displacement")}
                for index, (a, b) in enumerate(zip(first, second))]
    edges = []
    for index, ids in enumerate(a_fields["native_topology"]["edges"]):
        a = finite(math.dist(first[ids[0]], first[ids[1]]), "Nonfinite baseline edge")
        b = finite(math.dist(second[ids[0]], second[ids[1]]), "Nonfinite projected edge")
        edges.append({"index": index, "vertices": ids, "region": region(ids, weights),
                      "baseline_length_m": a, "projected_length_m": b, "baseline_low_length": a <= edge_floor,
                      "projected_low_length": b <= edge_floor,
                      "length_ratio": finite(b/a, "Nonfinite edge ratio") if a > edge_floor else None})
    triangles = []
    for index, ids in enumerate(a_fields["native_topology"]["triangles"]):
        normals = [cross(subtract(points[ids[1]], points[ids[0]]), subtract(points[ids[2]], points[ids[0]]))
                   for points in (first, second)]
        sizes = [finite(math.hypot(*normal), "Nonfinite triangle area vector") for normal in normals]
        areas = [size*.5 for size in sizes]
        valid_normals = all(area > area_floor for area in areas)
        dot = finite(sum((a/sizes[0])*(b/sizes[1]) for a, b in zip(*normals)), "Nonfinite normal dot") if valid_normals else None
        triangles.append({"index": index, "vertices": ids, "region": region(ids, weights),
                          "baseline_area_m2": areas[0], "projected_area_m2": areas[1],
                          "baseline_low_area": areas[0] <= area_floor, "projected_low_area": areas[1] <= area_floor,
                          "area_ratio": finite(areas[1]/areas[0], "Nonfinite area ratio") if areas[0] > area_floor else None,
                          "normal_dot": min(1., max(-1., dot)) if dot is not None else None})
    complete = all(item["length_ratio"] is not None for item in edges) and all(
        item["area_ratio"] is not None and item["normal_dot"] is not None for item in triangles)
    changed = any(item["displacement_m"] > 0. for item in vertices)
    return {"case": case, "status": "measured" if same_input and complete else "unproven",
            "analysis_completed": True, "native_frame": baseline["frame"], "units_to_metres": units,
            "final_surface_change_observed": changed,
            "projection_change_observed": changed if same_input else None,
            "projection_attribution": "conditional_on_recorded_input_subset_only" if same_input else "unknown_recorded_inputs_differ",
            "change_interpretation": ("final_surface_change_observed" if changed else "no_final_surface_change_observed")
                + ("; recorded input subset equal, full attribution not independently proven" if same_input
                   else "; projection attribution Unknown because recorded inputs differ"),
            "final_vertices": len(vertices), "native_edges": len(edges), "native_triangles": len(triangles),
            "exact_native_topology_sha256": a_fields["native_topology_sha256"], "same_recorded_input_exact": same_input,
            "recorded_input_equality_scope": "Body/C800/H0800/knee/Hem only; not an independent proof of S, complete Pose or cache state",
            "waist_vertex_partition": {"native_hard_fixed_vertices": len(a_fields["hard_fixed_vertex_indices"]),
                "native_free_vertices": len(a_fields["free_vertex_indices"]),
                "soft_waist_vertices_within_native_free": sum(0. < weight < FIXED_WEIGHT for weight in weights),
                "zero_waist_vertices_within_native_free": sum(weight == 0. for weight in weights)},
            "non_Dress_input_maximum_deltas_m": input_deltas, "global": summarize_geometry(vertices, edges, triangles),
            "regions": {name: summarize_geometry([item for item in vertices if item["region"] == name],
                [item for item in edges if item["region"] == name], [item for item in triangles if item["region"] == name])
                for name in REGIONS}, "all_global_ratio_and_normal_denominators_measured": complete,
            "geometry_quality_accepted": False, "true_flips_accepted": False}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", nargs="+", help="Default: union of existing baseline/projected case names")
    parser.add_argument("--edge-denominator-floor-m", type=float, default=1.e-12)
    parser.add_argument("--area-denominator-floor-m2", type=float, default=1.e-18)
    args = parser.parse_args()
    args.points_dir, args.output = args.points_dir.resolve(), args.output.resolve()
    require(not args.output.exists() and args.output.suffix == ".json", "Use one fresh explicitly named JSON output")
    require(number(args.edge_denominator_floor_m) and args.edge_denominator_floor_m > 0.
            and number(args.area_denominator_floor_m2) and args.area_denominator_floor_m2 > 0., "Invalid numerical denominator floors")
    if args.cases:
        require(len(args.cases) == len(set(args.cases)) and all(name and all(character.isalnum() or character == "_"
                for character in name) for name in args.cases), "Case names must be distinct filename stems")
    return args


def main(args):
    cases = args.cases or sorted({path.name[:-len(suffix)] for suffix in ("_baseline.json", "_projected.json")
                                 for path in args.points_dir.glob("*"+suffix)})
    report = {"tool": str(Path(__file__).resolve()), "tool_sha256": file_state(Path(__file__))["sha256"],
              "points_directory": str(args.points_dir), "status": "unproven", "analysis_completed": False,
              "cases": [], "geometry_quality_accepted": False, "true_flips_accepted": False,
              "numerical_denominator_floors": {"edge_length_m": args.edge_denominator_floor_m,
                  "triangle_area_m2": args.area_denominator_floor_m2, "meaning": "Arithmetic reliability only; no quality tolerance or pass guard"},
              "region_definition": {"hard_fixed_waist": "All vertices native waist weight >=0.999",
                  "mixed_waist_transition": "Not wholly fixed and at least one positive waist weight",
                  "free_skirt": "Every vertex has zero waist weight; subset of native free (<0.999), which also includes soft waist weights"},
              "limitations": ["Compares actual snapshot final3040 order only; no nearest-neighbour pairing or missing-data substitution",
                  "Same frame alone is insufficient; recorded Body/C/H0/knee/Hem must match exactly; equality does not independently prove S, complete Pose or cache state",
                  "Opposed nondegenerate normals are rotation candidates, not proof of a true local inversion or topology flip",
                  "No self-intersection, Body/collider separation, continuous-time, silhouette or artistic-quality acceptance",
                  "Missing pairs, empty samples and unreliable denominators remain Unproven; completion never means geometry Pass"]}
    for case in cases:
        paths = [args.points_dir / (case+suffix) for suffix in ("_baseline.json", "_projected.json")]
        item = {"case": case, "status": "unproven", "analysis_completed": False}
        before = {}
        try:
            require(all(path.is_file() for path in paths), "Missing complete A/B pair")
            require(args.output not in paths, "Output must not replace a snapshot")
            before = {str(path): file_state(path) for path in paths}
            snapshots = [load_snapshot(path, case+suffix) for path, suffix in zip(paths, ("_baseline", "_projected"))]
            item = analyze_pair(case, *snapshots, args.edge_denominator_floor_m, args.area_denominator_floor_m2)
        except Exception as error:
            item["unknown_reason"] = str(error)
        finally:
            item["input_files"] = before
            try:
                item["input_files_exact_after_analysis"] = bool(before) and all(
                    file_state(Path(path)) == state for path, state in before.items())
            except OSError as error:
                item["input_files_exact_after_analysis"] = False
                item["input_identity_unknown_reason"] = str(error)
            if not item["input_files_exact_after_analysis"]:
                item["status"], item["analysis_completed"] = "unproven", False
            report["cases"].append(item)
    report["analysis_completed"] = bool(report["cases"]) and all(item["analysis_completed"] for item in report["cases"])
    report["status"] = "measured" if report["analysis_completed"] and all(item["status"] == "measured"
                                                                         for item in report["cases"]) else "unproven"
    if not cases:
        report["unknown_reason"] = "No native A/B snapshot cases found"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "analysis_completed": report["analysis_completed"],
                      "cases": len(report["cases"]), "output": str(args.output)}))
    return 0 if report["status"] == "measured" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(arguments()))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
