"""Read-only old-production FBX bind diagnostic; no Blender/Unity execution.

Run with ordinary Python. The Blender 5.2 official binary parser is loaded
without the add-on registration module, and array decompression is serialized.
Comparisons use the captured author Rest, shifted by the new export's origin.
This is historical diagnosis, not a gate on the new export or proof of Unity
runtime behavior. No input FBX or .blend is written.
"""
import argparse
from collections import defaultdict
import importlib
import json
import math
from pathlib import Path
import sys
import types

from fbx_raw_oracle import _children, _first, _kind, _name, _one, _properties, _sha256


def multiply(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def raw_matrix(element, key):
    values = list(_first(element, key))
    if len(values) != 16 or not all(math.isfinite(v) for v in values):
        raise ValueError(f"Invalid {key!r} matrix")
    return [[values[j * 4 + i] for j in range(4)] for i in range(4)]


def metrics(actual, expected):
    errors = [abs(actual[i][j] - expected[i][j]) for i in range(4) for j in range(4)]
    axes = {}
    for j, name in enumerate("XYZ"):
        av, ev = [actual[i][j] for i in range(3)], [expected[i][j] for i in range(3)]
        denominator = math.sqrt(sum(v * v for v in av) * sum(v * v for v in ev))
        dot = sum(a * b for a, b in zip(av, ev)) / denominator if denominator else None
        axes[name] = {"angle_degrees": math.degrees(math.acos(max(-1, min(1, dot)))) if dot is not None else None,
                      "max_abs": max(abs(a - b) for a, b in zip(av, ev))}
    return {"max_abs": max(errors), "translation_max_abs": max(abs(actual[i][3] - expected[i][3]) for i in range(3)),
            "axes": axes}


def load_parser(directory):
    package_name = "_production_diagnostic_official_fbx"
    package = types.ModuleType(package_name)
    package.__path__ = [str(directory)]
    sys.modules[package_name] = package
    parser = importlib.import_module(package_name + ".parse_fbx")
    threading = importlib.import_module(package_name + ".fbx_utils_threading")
    threading._MULTITHREADING_ENABLED = False
    return parser


def main():
    args = argparse.ArgumentParser(description=__doc__)
    for option in ("capture", "export-proof", "production-fbx", "report"):
        args.add_argument("--" + option, required=True, type=Path)
    args.add_argument("--parser-directory", type=Path,
                      default=Path(r"D:\Blender5.2\5.2\scripts\addons_core\io_scene_fbx"))
    options = args.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    inputs = {name: getattr(options, name).resolve() for name in ("capture", "export_proof", "production_fbx")}
    output = options.report.resolve()
    if output in inputs.values():
        raise ValueError("Report must not overwrite an input")
    before = {name: _sha256(path) for name, path in inputs.items()}
    report = {"diagnostic": "historical_production_fbx_vs_captured_author_rest_v1", "completed": False,
              "scope": "Raw PoseNode and connected Cluster.TransformLink only; no Blender scene or Unity execution",
              "input_paths": {name: str(path) for name, path in inputs.items()}, "sha256_before": before,
              "tolerance_matrix_abs": 2e-5, "bones": {}, "focus": {}, "errors": []}
    try:
        capture = json.loads(inputs["capture"].read_text(encoding="utf-8"))
        proof = json.loads(inputs["export_proof"].read_text(encoding="utf-8"))
        if not capture.get("passed") or not proof.get("passed"):
            raise ValueError("Captured author Rest and new-export proof must have passed")
        result = proof["export_result"]
        if len(result["rigs"]) != 1:
            raise ValueError("Expected exactly one captured export rig")
        rig_name, retained = next(iter(result["rigs"].items()))
        source = capture["source_rest"][rig_name]
        origin = result["origin"]
        shift = [[1, 0, 0, -origin[0]], [0, 1, 0, -origin[1]], [0, 0, 1, -origin[2]], [0, 0, 0, 1]]
        # Blender +Y forward/+Z up -> FBX -Z forward/+Y up, matching axis_conversion.
        c = [[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]]
        expected = {name: multiply(c, multiply(shift, multiply(source["object_world"], source["bones"][name]["matrix"])))
                    for name in retained}
        parser = load_parser(options.parser_directory.resolve())
        report["parser_source"] = str(Path(parser.__file__).resolve())
        report["parser_sha256"] = _sha256(parser.__file__)
        tree, version = parser.parse(str(inputs["production_fbx"]), use_namedtuple=True)
        report["fbx_version"] = int(version)
        props = _properties(_one(tree, b"GlobalSettings"))
        report["global_settings"] = {name: props.get(name, [None])[0] for name in (
            "UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign", "UnitScaleFactor")}
        expected_axes = {"UpAxis": 1, "UpAxisSign": 1, "FrontAxis": 2, "FrontAxisSign": 1,
                         "CoordAxis": 0, "CoordAxisSign": 1, "UnitScaleFactor": 100 * float(result["unit_scale"])}
        report["axis_unit_contract_matches"] = report["global_settings"] == expected_axes
        nodes = _one(tree, b"Objects").elems
        by_id = {int(node.props[0]): node for node in nodes}
        bone_names = {int(node.props[0]): _name(node) for node in nodes if _kind(node, b"Model", b"LimbNode")}
        children = defaultdict(list)
        for conn in _one(tree, b"Connections").elems:
            if conn.id == b"C" and len(conn.props) >= 3 and conn.props[0] == b"OO":
                children[int(conn.props[2])].append(int(conn.props[1]))
        for name in retained:
            report["bones"][name] = {"pose_samples": 0, "cluster_samples": 0, "worst": None}

        def compare(identifier, actual, location, kind):
            name = bone_names.get(identifier)
            if name not in expected:
                return
            entry = report["bones"][name]
            entry[kind + "_samples"] += 1
            error = metrics(actual, expected[name])
            if entry["worst"] is None or error["max_abs"] > entry["worst"]["max_abs"]:
                entry["worst"] = {"location": location, **error}

        pose_count = cluster_count = 0
        for node in nodes:
            if _kind(node, b"Pose", b"BindPose"):
                pose_count += 1
                for index, item in enumerate(_children(node, b"PoseNode")):
                    compare(int(_first(item, b"Node")), raw_matrix(item, b"Matrix"),
                            f"Pose/{node.props[0]}/{index}", "pose")
            elif _kind(node, b"Deformer", b"Cluster"):
                cluster_count += 1
                identifiers = [i for i in children[int(node.props[0])] if i in bone_names]
                if len(identifiers) != 1:
                    report["errors"].append(f"Cluster {node.props[0]} has {len(identifiers)} connected bone models")
                else:
                    compare(identifiers[0], raw_matrix(node, b"TransformLink"), f"Cluster/{node.props[0]}/TransformLink", "cluster")
        report["counts"] = {"retained_bones": len(retained), "production_bone_models": len(bone_names),
                            "bind_poses": pose_count, "clusters": cluster_count}
        report["missing_pose_bones"] = [name for name, entry in report["bones"].items() if not entry["pose_samples"]]
        report["missing_cluster_bones"] = [name for name, entry in report["bones"].items() if not entry["cluster_samples"]]
        mismatches = [(name, entry["worst"]) for name, entry in report["bones"].items()
                      if entry["worst"] and entry["worst"]["max_abs"] > 2e-5]
        report["mismatch_bones"] = [name for name, _ in mismatches]
        measured = [(name, entry["worst"]) for name, entry in report["bones"].items() if entry["worst"]]
        report["all_retained_worst"] = None
        if measured:
            name, worst = max(measured, key=lambda x: x[1]["max_abs"])
            report["all_retained_worst"] = {"bone": name, **worst}
        focus = [f"{bone}.{side}" for bone in ("forearm", "hand", "thigh", "shin", "foot") for side in "LR"]
        report["focus"] = {name: report["bones"].get(name) for name in focus}
        report["bind_matches_captured_author_rest"] = bool(measured) and report["axis_unit_contract_matches"] and not (
            mismatches or report["missing_pose_bones"] or report["missing_cluster_bones"] or report["errors"])
        report["completed"] = True
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        report["sha256_after"] = {name: _sha256(path) for name, path in inputs.items()}
        report["inputs_unchanged"] = report["sha256_after"] == before
        if not report["inputs_unchanged"]:
            report["completed"] = False
            report["errors"].append("Input file changed during read-only diagnostic")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report.get(key) for key in ("completed", "bind_matches_captured_author_rest", "inputs_unchanged", "errors")}))
    return 0 if report["completed"] and report["inputs_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
