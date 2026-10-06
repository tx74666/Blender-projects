"""Read an existing FBX's serialized Rest bind data without Blender or bpy.

This diagnostic does not export, import into Blender/Unity, evaluate animation,
or mutate its FBX/library/source-report inputs. Only its requested JSON output is
written. Run with Python 3.12 and the installed official Blender FBX parser.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def fingerprint(path):
    path = Path(path).resolve(strict=True)
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": hasher.hexdigest()}


def read_report(path):
    proof = fingerprint(path)
    content = json.loads(Path(proof["path"]).read_text(encoding="utf-8-sig"))
    return content, proof


def reported_input(item):
    actual = fingerprint(item["path"])
    require(actual["sha256"] == item["sha256"], "Input differs from recorded SHA: " + actual["path"])
    if "bytes" in item:
        require(actual["bytes"] == item["bytes"], "Input differs from recorded size: " + actual["path"])
    return actual


def stable_digest(content):
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True,
                                    allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def official_parser(path):
    path = Path(path).resolve(strict=True)
    require(path.name == "parse_fbx.py", "Expected official parse_fbx.py")
    package_name = "static_bind_official_fbx_parser"
    package = types.ModuleType(package_name)
    package.__path__ = [str(path.parent)]
    sys.modules[package_name] = package
    spec = importlib.util.spec_from_file_location(package_name + ".parse_fbx", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # Only the private Python module is changed; its official disk source is untouched.
    # The helper's stdlib thread-support probe has returned before this assignment.
    sys.modules[package_name + ".fbx_utils_threading"]._MULTITHREADING_ENABLED = False
    dependencies = {name: fingerprint(path.parent / name) for name in
                    ("parse_fbx.py", "data_types.py", "fbx_utils_threading.py")}
    return module, dependencies


def child(element, key):
    matches = [item for item in element.elems if item.id == key]
    require(len(matches) == 1, "Expected exactly one FBX child: " + repr(key))
    return matches[0]


def model_name(element):
    return element.props[1].split(b"\0\1", 1)[0].decode("utf-8")


def matrix(array):
    require(len(array) == 16, "FBX matrix is not 4 x 4")
    result = [[float(array[row + 4 * column]) for column in range(4)] for row in range(4)]
    require(all(math.isfinite(value) for row in result for value in row), "Nonfinite FBX matrix")
    return result


def inverse(value):
    rows = [list(row) + [float(index == column) for column in range(4)]
            for index, row in enumerate(value)]
    for column in range(4):
        pivot = max(range(column, 4), key=lambda index: abs(rows[index][column]))
        require(abs(rows[pivot][column]) > 1e-15, "Singular FBX armature bind matrix")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        rows[column] = [item / divisor for item in rows[column]]
        for index in range(4):
            if index != column:
                factor = rows[index][column]
                rows[index] = [item - factor * normalized for item, normalized in
                               zip(rows[index], rows[column])]
    return [row[4:] for row in rows]


def multiply(left, right):
    return [[sum(left[row][index] * right[index][column] for index in range(4))
             for column in range(4)] for row in range(4)]


def comparison(left, right):
    require(len(right) == 4 and all(len(row) == 4 for row in right), "Source matrix is not 4 x 4")
    require(all(math.isfinite(value) for row in right for value in row), "Nonfinite source Rest matrix")
    components = [(abs(left[row][column] - right[row][column]), row, column)
                  for row in range(4) for column in range(4)]
    maximum, row, column = max(components)
    axis_errors = []
    for column_index in range(3):
        first = [left[index][column_index] for index in range(3)]
        second = [right[index][column_index] for index in range(3)]
        first_norm = math.sqrt(sum(item * item for item in first))
        second_norm = math.sqrt(sum(item * item for item in second))
        require(min(first_norm, second_norm) > 1e-15, "Degenerate Rest axis")
        axis_errors.append(math.sqrt(sum((a / first_norm - b / second_norm) ** 2
                                        for a, b in zip(first, second))))
    return {"matrix_max_abs_error": maximum, "worst_component": [row, column],
            "head_max_abs_error_armature_units": max(abs(left[index][3] - right[index][3])
                                                     for index in range(3)),
            "normalized_axis_vector_max_error": max(axis_errors)}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-report", required=True, type=Path)
    parser.add_argument("--source-export-report", required=True, type=Path)
    parser.add_argument("--source-rest-report", required=True, type=Path)
    parser.add_argument("--parser-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rig", default="CoshaRig")
    parser.add_argument("--expected-bones", default=217, type=int)
    return parser.parse_args()


def main():
    args = arguments()
    current, current_proof = read_report(args.export_report)
    source_export, source_export_proof = read_report(args.source_export_report)
    source, source_proof = read_report(args.source_rest_report)
    fbx_proof = reported_input(current["fbx"])
    library_proof = reported_input(current["public_library_snapshot"])
    source_library_proof = reported_input(source_export["public_library_snapshot"])
    rest_library_proof = reported_input(source["input_before"])
    require(rest_library_proof == source_library_proof, "Source Rest was not measured from the linked library")
    reference = source["source"]["original_rest"]
    # This is the existing validate_real_dress.rest_content fingerprint schema.
    rest_fields = ("parent", "matrix", "length", "connect", "deform", "inherit_scale",
                   "inherit_rotation", "local_location")
    projected_rest = {name: {key: item[key] for key in rest_fields} for name, item in reference.items()}
    projected_sha = stable_digest(projected_rest)
    current_sha = current["protected_initial_qa_assets"]["rest_sha256"][args.rig]
    source_sha = source_export["protected_initial_qa_assets"]["rest_sha256"][args.rig]
    require(projected_sha == current_sha == source_sha, "Source Rest content/fingerprints differ between captures")
    parser, parser_proofs = official_parser(args.parser_file)
    tree, version = parser.parse(fbx_proof["path"])
    objects = child(tree, b"Objects")
    models = {item.props[0]: item for item in objects.elems if item.id == b"Model"}
    require(len(models) == sum(item.id == b"Model" for item in objects.elems), "Duplicate FBX model ID")
    by_name = {model_name(item): identifier for identifier, item in models.items()}
    require(len(by_name) == len(models), "Duplicate FBX model name")
    require(args.rig in by_name, "FBX armature model is missing")
    bones = {identifier: item for identifier, item in models.items() if item.props[-1] == b"LimbNode"}
    require(len(bones) == args.expected_bones, "Unexpected retained FBX bone count")
    poses = {}
    pose_count = 0
    pose_node_total = 0
    repeated_pose_nodes_exact = 0
    for pose in objects.elems:
        if pose.id != b"Pose":
            continue
        pose_count += 1
        for node in pose.elems:
            if node.id == b"PoseNode":
                pose_node_total += 1
                identifier = child(node, b"Node").props[0]
                node_matrix = matrix(child(node, b"Matrix").props[0])
                if identifier in poses:
                    require(poses[identifier] == node_matrix, "Repeated FBX PoseNode has different matrices")
                    repeated_pose_nodes_exact += 1
                poses[identifier] = node_matrix
    armature_inverse = inverse(poses[by_name[args.rig]])
    bind_comparisons = []
    for identifier, item in bones.items():
        name = model_name(item)
        require(name in reference and identifier in poses, "Missing source or serialized bind for " + name)
        local = multiply(armature_inverse, poses[identifier])
        bind_comparisons.append({"bone": name, **comparison(local, reference[name]["matrix"])})
    connections = child(tree, b"Connections")
    cluster_comparisons = []
    seen_cluster_bones = set()
    for deformer in objects.elems:
        if deformer.id != b"Deformer" or deformer.props[-1] != b"Cluster":
            continue
        linked = [connection.props[1] for connection in connections.elems if
                  connection.props[0] == b"OO" and connection.props[2] == deformer.props[0]
                  and connection.props[1] in bones]
        require(len(linked) == 1, "Cluster lacks an unambiguous retained bone connection")
        identifier = linked[0]
        require(identifier not in seen_cluster_bones, "More than one Cluster for retained bone")
        seen_cluster_bones.add(identifier)
        cluster_comparisons.append({"bone": model_name(models[identifier]),
            **comparison(matrix(child(deformer, b"TransformLink").props[0]), poses[identifier])})
    require(seen_cluster_bones == set(bones), "Not all retained bones have Cluster.TransformLink proof")
    settings = {item.props[0].decode("utf-8"): item.props[4:] for item in
                child(child(tree, b"GlobalSettings"), b"Properties70").elems if item.id == b"P"}
    setting_keys = ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign",
                    "UnitScaleFactor", "OriginalUnitScaleFactor")
    inputs = {"fbx": fbx_proof, "public_library_snapshot": library_proof,
              "source_rest_library_snapshot": rest_library_proof,
              "current_export_report": current_proof, "source_export_report": source_export_proof,
              "source_rest_report": source_proof, "official_parser_files": parser_proofs,
              "diagnostic_script": fingerprint(__file__)}
    input_proofs = [fbx_proof, library_proof, rest_library_proof, current_proof, source_export_proof,
                    source_proof, *parser_proofs.values(), inputs["diagnostic_script"]]
    for proof in input_proofs:
        require(fingerprint(proof["path"]) == proof, "Input changed during pure comparison: " + proof["path"])
    sort_key = lambda item: (item["matrix_max_abs_error"], item["bone"])
    bind_worst = sorted(bind_comparisons, key=sort_key, reverse=True)
    cluster_worst = sorted(cluster_comparisons, key=sort_key, reverse=True)
    report = {
        "schema": "STATIC_SERIALIZED_FBX_BIND_DIAGNOSTIC_V1",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "serialized_bind_comparison_complete",
        "scope": {"blender_native_import_validated": False, "unity_import_validated": False,
                  "animation_validated": False, "artist_scene_modified": False,
                  "new_export_performed": False, "bpy_imported": "bpy" in sys.modules,
                  "warning": "This result is not native import, Unity, animation, or final model acceptance."},
        "inputs": inputs, "all_inputs_unchanged": True,
        "source_rest_link": {"rig": args.rig, "source_bone_count": len(reference),
            "rest_report_native_content_sha256": source["source"]["rest_sha256_before"],
            "projected_validate_real_dress_schema_sha256": projected_sha,
            "current_capture_rest_sha256": current_sha, "source_capture_rest_sha256": source_sha,
            "fingerprints_equal": True, "source_rest_library_file_link_exact": True},
        "coordinate_convention": {
            "fbx_matrix_storage": "16 double values in column-major order; converted to four plain-float rows",
            "comparison": "inverse(FBX armature PoseNode world matrix) * FBX bone PoseNode world matrix versus native Bone.matrix_local plain floats",
            "units": "Armature object units. The common file-world/root transformation and scale cancel in the inverse product; head metric is not a world/metre head guard.",
            "axis_metric": "Euclidean difference of separately normalized 3-vector matrix columns; no roll/Euler decomposition",
            "source_rest_schema_projection": list(rest_fields),
            "cluster_comparison": "Cluster.TransformLink world matrix versus its bone PoseNode world matrix, in the same serialized FBX coordinates",
            "parser_runtime": "Official installed parse_fbx.py; array decoding forced serial in this private pure-Python module; no bpy or mathutils"},
        "fbx": {"version": version, "global_settings": {key: settings.get(key) for key in setting_keys},
                "model_count": len(models), "pose_count": pose_count, "pose_node_count": len(poses),
                "pose_node_total": pose_node_total, "repeated_pose_nodes_exact": repeated_pose_nodes_exact,
                "retained_bones": len(bones)},
        "bind_summary": {"compared_bones": len(bind_comparisons),
            "matrix_max_abs_error": bind_worst[0]["matrix_max_abs_error"],
            "head_max_abs_error_armature_units": max(item["head_max_abs_error_armature_units"] for item in bind_comparisons),
            "normalized_axis_vector_max_error": max(item["normalized_axis_vector_max_error"] for item in bind_comparisons),
            "worst8": bind_worst[:8]},
        "cluster_summary": {"compared_bones": len(cluster_comparisons),
            "matrix_max_abs_error": cluster_worst[0]["matrix_max_abs_error"],
            "all_transformlink_pose_matrices_exact": all(item["matrix_max_abs_error"] == 0. for item in cluster_comparisons),
            "worst8": cluster_worst[:8]},
        "per_bone_compact": [{**item, "cluster_pose_matrix_max_abs_error":
            next(entry["matrix_max_abs_error"] for entry in cluster_comparisons if entry["bone"] == item["bone"])}
            for item in sorted(bind_comparisons, key=lambda item: item["bone"])],
        "reproduction": {"python": sys.version, "argv": sys.argv}}
    require(not report["scope"]["bpy_imported"], "Unexpected bpy in pure parser session")
    output = args.output.resolve()
    require(output not in {Path(proof["path"]) for proof in input_proofs}, "Output overlaps a protected input")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": fingerprint(output), "status": report["status"],
                      "bind_summary": report["bind_summary"], "cluster_summary": report["cluster_summary"],
                      "all_inputs_unchanged": True}, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
