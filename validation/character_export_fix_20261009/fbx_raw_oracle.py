"""Read-only binary FBX oracle for the captured Character Designer export.

Only ``audit_raw_fbx`` imports Blender/numpy dependencies, so AST checks and
source imports can run without Blender.  This module never invokes the exporter,
the importer, bpy operators, a scene save, or a vertex correction routine.

The caller supplies independent, post-bake expectations in Blender coordinates
after removing the export origin.  The supported export contract is forward -Z,
up Y, primary bone Y, secondary bone X, global_scale 1,
apply_scale_options FBX_SCALE_UNITS, and bake_space_transform False.  Raw mesh
and shape coordinates therefore stay in object space; raw world bind matrices
are C @ BlenderWorld and UnitScaleFactor is 100 * scene unit_scale.

The actual FBX PoseNode matrices, cluster matrices, geometry arrays, and OO
connections are the evidence.  Blender's parser only deserializes bytes.  No
imported or exporter-reconstructed geometry participates in this gate.
"""

from collections import Counter, defaultdict
import hashlib
import math
from pathlib import Path


MATRIX_COORD_TOLERANCE = 2e-5
WEIGHT_TOLERANCE = 1e-6


def _children(elem, key):
    return [child for child in elem.elems if child.id == key]


def _one(elem, key, required=True):
    values = _children(elem, key)
    if len(values) != 1:
        if not values and not required:
            return None
        raise ValueError(f"{elem.id!r} has {len(values)} {key!r} elements; expected one")
    return values[0]


def _first(elem, key, required=True, default=None):
    child = _one(elem, key, required)
    if child is None:
        return default
    if len(child.props) != 1:
        raise ValueError(f"{key!r} has {len(child.props)} properties; expected one")
    return child.props[0]


def _name(elem):
    if len(elem.props) < 3:
        raise ValueError(f"{elem.id!r} object lacks id/name/type properties")
    name = elem.props[1]
    if not isinstance(name, bytes):
        raise ValueError("FBX name is not a byte string")
    return name.split(b"\x00\x01", 1)[0].decode("utf-8", errors="strict")


def _kind(elem, key, subtype):
    return elem.id == key and len(elem.props) >= 3 and elem.props[2] == subtype


def _properties(elem):
    result = {}
    for props in _children(elem, b"Properties70"):
        for prop in _children(props, b"P"):
            if len(prop.props) < 5:
                raise ValueError("Malformed Properties70/P record")
            key = prop.props[0].decode("utf-8", errors="strict")
            if key in result:
                raise ValueError(f"Duplicate property {key!r}")
            result[key] = list(prop.props[4:])
    return result


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value):
    """Keep a failing nonfinite raw payload serializable without NaN/Infinity."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def audit_raw_fbx(fbx_path, expected_bones_world, expected_meshes, unit_scale,
                  root_name, root_world):
    """Return a JSON-safe report; every raw mismatch makes ``passed`` False.

    ``expected_bones_world``: {bone_name: mathutils.Matrix world rest matrix}.
    ``expected_meshes``: {object_name: {'world': Matrix, 'vertices': N x 3 Basis
    array, 'weights': length-N list of {bone_name: raw_weight},
    'shapes': {key_name: N x 3 object-space delta},
    'shape_values': {key_name: Blender key value}}}.  Shapes must exclude Basis
    and contain the raw shape-relative_key displacement.  The captured worker
    has flattened shape vertex-group masks, so every FullWeights entry must be
    100.  DeformPercent must equal shape_values[key] * 100, defaulting to zero.
    Skin weights are compared as stored, never normalized.  Root and every world
    matrix must already have the export origin removed.  ``unit_scale`` is
    Blender scene scale_length, normally 1.0.

    Matrices and coordinates use component-wise absolute tolerance 2e-5; raw
    skin weights use 1e-6.  Sparse zero shapes must retain Blender's literal
    one-point zero dummy (Indexes=[0], Vertices=[0,0,0]).  Failures are accumulated
    rather than turning a malformed or incomplete FBX into an accidental PASS.
    """
    import numpy as np
    from bpy_extras.io_utils import axis_conversion
    from io_scene_fbx import parse_fbx
    from io_scene_fbx.fbx_utils import RIGHT_HAND_AXES

    path = Path(fbx_path).resolve()
    report = {
        "oracle": "raw_binary_fbx_pose_cluster_geometry_v1",
        "fbx_path": str(path),
        "passed": False,
        "tolerances": {"matrix_coordinate_abs": MATRIX_COORD_TOLERANCE,
                       "skin_weight_abs": WEIGHT_TOLERANCE},
        "contract": {"axis_forward": "-Z", "axis_up": "Y",
                     "primary_bone_axis": "Y", "secondary_bone_axis": "X",
                     "global_scale": 1.0, "bake_space_transform": False,
                     "apply_scale_options": "FBX_SCALE_UNITS",
                     "scene_unit_scale": float(unit_scale),
                     "export_origin_already_removed": True,
                     "root_name": str(root_name)},
        "expected_counts": {"bones": len(expected_bones_world),
                            "meshes": len(expected_meshes),
                            "shapes": sum(len(m.get("shapes", {}))
                                          for m in expected_meshes.values())},
        "actual_counts": {}, "global_settings": {}, "bones": {},
        "meshes": {}, "bind_poses": [], "root": {}, "failures": [],
    }

    def fail(code, location, **details):
        report["failures"].append({"code": code, "location": str(location), **details})

    def finite(values, location):
        if not np.isfinite(values).all():
            fail("nonfinite_raw_data", location)
            return False
        return True

    def input_matrix(value):
        result = np.asarray([tuple(row) for row in value], dtype=np.float64)
        if result.shape != (4, 4) or not np.isfinite(result).all():
            raise ValueError("Expected world matrix must be a finite 4 x 4 matrix")
        return result

    def raw_matrix(elem, key, location):
        values = np.asarray(_first(elem, key), dtype=np.float64)
        if values.size != 16:
            raise ValueError(f"{location}/{key.decode()} has {values.size} values, expected 16")
        # FBX serialization concatenates columns; Blender matrices use rows.
        result = values.reshape(4, 4).T.copy()
        finite(result, location)
        return result

    def matrix_metrics(actual, expected):
        if not np.isfinite(actual).all():
            return {"max_abs": None, "axes": {}, "translation_max_abs": None}
        delta = np.abs(actual - expected)
        axes = {}
        for index, label in enumerate("XYZ"):
            av, ev = actual[:3, index], expected[:3, index]
            denom = float(np.linalg.norm(av) * np.linalg.norm(ev))
            angle = math.degrees(math.acos(float(np.clip(np.dot(av, ev) / denom, -1, 1)))) if denom else None
            axes[label] = {"vector_error": float(np.linalg.norm(av - ev)),
                           "max_abs": float(np.max(np.abs(av - ev))),
                           "angle_degrees": angle}
        return {"max_abs": float(delta.max()), "axes": axes,
                "translation_max_abs": float(delta[:3, 3].max())}

    def compare_matrix(actual, expected, location, bone_name=None):
        metrics = matrix_metrics(actual, expected)
        error = metrics["max_abs"]
        if error is None or error > MATRIX_COORD_TOLERANCE:
            fail("bind_matrix_mismatch", location, metrics=metrics)
        if bone_name is not None:
            entry = report["bones"][bone_name]
            entry["matrix_samples"] += 1
            if error is not None and (entry["worst"] is None or error > entry["worst"]["max_abs"]):
                entry["worst"] = {"location": str(location), **metrics}
        return metrics

    def raw_array(elem, key, dtype, location, required=True):
        value = _first(elem, key, required=required, default=())
        result = np.asarray(value, dtype=dtype)
        if result.ndim != 1:
            raise ValueError(f"{location}/{key.decode()} is not flat")
        finite(result, location + "/" + key.decode())
        return result

    def name_table(nodes, label):
        table = defaultdict(list)
        for node in nodes:
            table[_name(node)].append(int(node.props[0]))
        for name, ids in table.items():
            if len(ids) != 1:
                fail("duplicate_model_name", f"{label}/{name}", ids=ids)
        return table

    def exact_names(actual, expected, location):
        missing, extra = sorted(set(expected) - set(actual)), sorted(set(actual) - set(expected))
        if missing or extra:
            fail("name_set_mismatch", location, missing=missing, extra=extra)

    try:
        if not math.isfinite(float(unit_scale)) or float(unit_scale) <= 0:
            raise ValueError("Scene unit_scale must be finite and positive")
        report["fbx_sha256"] = _sha256(path)
        report["parser_source"] = str(Path(parse_fbx.__file__).resolve())
        report["parser_source_sha256"] = _sha256(parse_fbx.__file__)
        tree, version = parse_fbx.parse(str(path), use_namedtuple=True)
        report["fbx_version"] = int(version)
        objects = _one(tree, b"Objects")
        connections = _one(tree, b"Connections")
        global_settings = _properties(_one(tree, b"GlobalSettings"))
        report["global_settings"] = {
            key: global_settings.get(key, [None])[0]
            for key in ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign",
                        "CoordAxis", "CoordAxisSign", "UnitScaleFactor", "OriginalUnitScaleFactor")
        }
        axes = RIGHT_HAND_AXES[("Y", "-Z")]
        expected_settings = dict(zip(
            ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign"),
            (axes[0][0], axes[0][1], axes[1][0], axes[1][1], axes[2][0], axes[2][1])))
        expected_settings["UnitScaleFactor"] = 100.0 * float(unit_scale)
        for key, value in expected_settings.items():
            actual = report["global_settings"][key]
            if actual is None or not isinstance(actual, (int, float)) or not math.isfinite(actual) or abs(actual - value) > WEIGHT_TOLERANCE:
                fail("global_setting_mismatch", key, expected=value, actual=actual)

        c = input_matrix(axis_conversion(to_forward="-Z", to_up="Y").to_4x4())
        expected_bones = {str(name): c @ input_matrix(world)
                          for name, world in expected_bones_world.items()}
        expected_mesh_world = {str(name): c @ input_matrix(item["world"])
                               for name, item in expected_meshes.items()}
        expected_root = c @ input_matrix(root_world)
        report["contract"]["Blender_to_FBX_world"] = c.tolist()

        by_id = {}
        for node in objects.elems:
            if not node.props or not isinstance(node.props[0], int):
                raise ValueError("Malformed Objects entry id")
            identifier = int(node.props[0])
            if identifier in by_id:
                fail("duplicate_object_id", identifier)
            by_id[identifier] = node
        parents, children = defaultdict(list), defaultdict(list)
        duplicate_connections = Counter()
        for conn in connections.elems:
            if conn.id != b"C" or len(conn.props) < 3:
                raise ValueError("Malformed Connections/C entry")
            if conn.props[0] != b"OO":
                continue
            source, destination = int(conn.props[1]), int(conn.props[2])
            duplicate_connections[(source, destination)] += 1
            parents[source].append(destination)
            children[destination].append(source)
            if source not in by_id or (destination != 0 and destination not in by_id):
                fail("dangling_oo_connection", f"{source}->{destination}")
        for pair, count in duplicate_connections.items():
            if count > 1:
                fail("duplicate_oo_connection", f"{pair[0]}->{pair[1]}", count=count)

        def connected(identifier, direction, key, subtype):
            links = children[identifier] if direction == "children" else parents[identifier]
            return [other for other in links
                    if other in by_id and _kind(by_id[other], key, subtype)]

        models = [node for node in objects.elems if node.id == b"Model"]
        model_names = name_table(models, "Model")
        root_ids = model_names.get(str(root_name), [])
        if len(root_ids) != 1:
            fail("root_model_count", root_name, actual=len(root_ids))
        root_id = root_ids[0] if len(root_ids) == 1 else None
        bone_models = [node for node in models if _kind(node, b"Model", b"LimbNode")
                       and int(node.props[0]) != root_id]
        mesh_models = [node for node in models if _kind(node, b"Model", b"Mesh")]
        bone_names = name_table(bone_models, "BoneModel")
        mesh_names = name_table(mesh_models, "MeshModel")
        exact_names(bone_names, expected_bones, "Model/LimbNode")
        exact_names(mesh_names, expected_meshes, "Model/Mesh")
        exact_names(model_names, set(expected_bones) | set(expected_meshes) | {str(root_name)}, "Model/all")
        expected_raw_by_id = {}
        bone_by_id = {}
        for name, expected in expected_bones.items():
            identifiers = bone_names.get(name, [])
            report["bones"][name] = {"model_ids": identifiers, "pose_samples": 0,
                                     "cluster_samples": 0, "matrix_samples": 0,
                                     "worst": None}
            if len(identifiers) == 1:
                expected_raw_by_id[identifiers[0]] = expected
                bone_by_id[identifiers[0]] = name
        for name, expected in expected_mesh_world.items():
            ids = mesh_names.get(name, [])
            if len(ids) == 1:
                expected_raw_by_id[ids[0]] = expected
        if root_id is not None:
            expected_raw_by_id[root_id] = expected_root

        poses = [node for node in objects.elems if _kind(node, b"Pose", b"BindPose")]
        skin_nodes = [node for node in objects.elems if _kind(node, b"Deformer", b"Skin")]
        cluster_nodes = [node for node in objects.elems if _kind(node, b"Deformer", b"Cluster")]
        shape_nodes = [node for node in objects.elems if _kind(node, b"Geometry", b"Shape")]
        channel_nodes = [node for node in objects.elems if _kind(node, b"Deformer", b"BlendShapeChannel")]
        mesh_geometries = [node for node in objects.elems if _kind(node, b"Geometry", b"Mesh")]
        report["actual_counts"] = {
            "objects": len(objects.elems), "models": len(models), "bones": len(bone_models),
            "meshes": len(mesh_models), "mesh_geometries": len(mesh_geometries),
            "bind_poses": len(poses), "pose_nodes": 0, "skins": len(skin_nodes),
            "clusters": len(cluster_nodes), "shapes": len(shape_nodes),
            "blend_shape_channels": len(channel_nodes),
        }
        bone_id_set = set(bone_by_id)
        pose_model_sets = []
        root_pose_samples = 0
        for pose in poses:
            pose_id = int(pose.props[0])
            pose_nodes = _children(pose, b"PoseNode")
            declared = int(_first(pose, b"NbPoseNodes"))
            if declared != len(pose_nodes):
                fail("pose_node_count", pose_id, declared=declared, actual=len(pose_nodes))
            ids = []
            worst = 0.0
            for index, pose_node in enumerate(pose_nodes):
                node_id = int(_first(pose_node, b"Node"))
                ids.append(node_id)
                location = f"Pose/{pose_id}/PoseNode/{index}:{node_id}"
                actual = raw_matrix(pose_node, b"Matrix", location)
                expected = expected_raw_by_id.get(node_id)
                if expected is None:
                    fail("unexpected_pose_node", location)
                    continue
                bone_name = bone_by_id.get(node_id)
                metrics = compare_matrix(actual, expected, location, bone_name)
                if metrics["max_abs"] is not None:
                    worst = max(worst, metrics["max_abs"])
                if bone_name is not None:
                    report["bones"][bone_name]["pose_samples"] += 1
                if node_id == root_id:
                    root_pose_samples += 1
            if len(ids) != len(set(ids)):
                fail("duplicate_pose_node", pose_id)
            id_set = set(ids)
            if id_set & bone_id_set and not bone_id_set.issubset(id_set):
                fail("incomplete_skeleton_bind_pose", pose_id,
                     missing_bones=[bone_by_id[i] for i in sorted(bone_id_set - id_set)])
            pose_model_sets.append(id_set)
            report["actual_counts"]["pose_nodes"] += len(pose_nodes)
            report["bind_poses"].append({"id": pose_id, "name": _name(pose),
                                         "nodes": len(ids), "bones": len(id_set & bone_id_set),
                                         "max_matrix_abs_error": worst})
        for name, item in report["bones"].items():
            if item["pose_samples"] == 0:
                fail("missing_bone_bind_pose", name)
        report["root"] = {"model_id": root_id, "pose_samples": root_pose_samples}
        if root_pose_samples == 0:
            fail("missing_root_bind_pose", root_name)

        reached_geometries, reached_skins, reached_clusters = set(), set(), set()
        reached_shapes, reached_channels, reached_blends = set(), set(), set()
        for mesh_name, expectation in expected_meshes.items():
            ids = mesh_names.get(mesh_name, [])
            if len(ids) != 1:
                continue
            mesh_id = ids[0]
            geometry_ids = connected(mesh_id, "children", b"Geometry", b"Mesh")
            if len(geometry_ids) != 1:
                fail("mesh_geometry_count", mesh_name, ids=geometry_ids)
                continue
            geometry_id = geometry_ids[0]
            reached_geometries.add(geometry_id)
            geom = by_id[geometry_id]
            location = f"Mesh/{mesh_name}"
            basis = np.asarray(expectation["vertices"], dtype=np.float64)
            if basis.ndim != 2 or basis.shape[1] != 3 or not np.isfinite(basis).all():
                raise ValueError(f"{mesh_name}: expected Basis must be a finite N x 3 array")
            nverts = len(basis)
            raw_vertices = raw_array(geom, b"Vertices", np.float64, location)
            raw_nverts = raw_vertices.size // 3
            item = {"model_id": mesh_id, "geometry_id": geometry_id,
                    "vertices": raw_nverts, "expected_vertices": nverts,
                    "basis_max_abs_error": None, "weight_max_abs_error": 0.0,
                    "weight_mismatches": 0, "weights_nonzero": 0,
                    "skins": [], "clusters": {}, "shapes": {}}
            report["meshes"][mesh_name] = item
            if raw_vertices.size != nverts * 3:
                fail("basis_vertex_count", location, expected=nverts, actual_values=int(raw_vertices.size))
            elif np.isfinite(raw_vertices).all():
                basis_error = float(np.abs(raw_vertices.reshape(nverts, 3) - basis).max(initial=0.0))
                item["basis_max_abs_error"] = basis_error
                if basis_error > MATRIX_COORD_TOLERANCE:
                    fail("basis_coordinate_mismatch", location, max_abs=basis_error)

            expected_weights = expectation["weights"]
            if len(expected_weights) != nverts:
                raise ValueError(f"{mesh_name}: expected weight list does not match Basis count")
            weights_by_bone = {name: {} for name in expected_bones}
            expected_sums = np.zeros(nverts, dtype=np.float64)
            actual_sums = np.zeros(nverts, dtype=np.float64)
            for vertex_index, weights in enumerate(expected_weights):
                for name, weight in weights.items():
                    value = float(weight)
                    if name not in weights_by_bone or not math.isfinite(value) or value < 0:
                        raise ValueError(f"{mesh_name}: invalid expected bone weight {name!r}")
                    if value:
                        weights_by_bone[name][vertex_index] = value
                        expected_sums[vertex_index] += value
            required_pose = bone_id_set | {mesh_id, root_id}
            if not any(required_pose.issubset(pose_ids) for pose_ids in pose_model_sets):
                fail("missing_complete_mesh_bind_pose", location)
            skin_ids = connected(geometry_id, "children", b"Deformer", b"Skin")
            item["skins"] = skin_ids
            if len(skin_ids) != 1:
                fail("mesh_skin_count", location, actual=len(skin_ids))
            seen_cluster_bones = []
            for skin_id in skin_ids:
                reached_skins.add(skin_id)
                if connected(skin_id, "parents", b"Geometry", b"Mesh") != [geometry_id]:
                    fail("skin_geometry_connection", skin_id)
                cluster_ids = connected(skin_id, "children", b"Deformer", b"Cluster")
                for cluster_id in cluster_ids:
                    reached_clusters.add(cluster_id)
                    cluster = by_id[cluster_id]
                    cluster_location = f"{location}/Cluster/{cluster_id}"
                    bone_ids = connected(cluster_id, "children", b"Model", b"LimbNode")
                    if len(bone_ids) != 1 or bone_ids[0] not in bone_by_id:
                        fail("cluster_bone_connection", cluster_location, bone_ids=bone_ids)
                        continue
                    bone_name = bone_by_id[bone_ids[0]]
                    seen_cluster_bones.append(bone_name)
                    if _name(cluster) != bone_name:
                        fail("cluster_bone_name", cluster_location, name=_name(cluster), expected=bone_name)
                    if connected(cluster_id, "parents", b"Deformer", b"Skin") != [skin_id]:
                        fail("cluster_skin_connection", cluster_location)
                    raw_link = raw_matrix(cluster, b"TransformLink", cluster_location)
                    raw_transform = raw_matrix(cluster, b"Transform", cluster_location)
                    raw_associate = raw_matrix(cluster, b"TransformAssociateModel", cluster_location)
                    link_metrics = compare_matrix(raw_link, expected_bones[bone_name],
                                                  cluster_location + "/TransformLink", bone_name)
                    relative = np.linalg.inv(expected_bones[bone_name]) @ expected_mesh_world[mesh_name]
                    transform_metrics = compare_matrix(raw_transform, relative, cluster_location + "/Transform")
                    associate_metrics = compare_matrix(raw_associate, expected_root,
                                                       cluster_location + "/TransformAssociateModel")
                    closure_metrics = compare_matrix(raw_link @ raw_transform, expected_mesh_world[mesh_name],
                                                     cluster_location + "/TransformLink@Transform")
                    report["bones"][bone_name]["cluster_samples"] += 1
                    idx_node, w_node = _one(cluster, b"Indexes", False), _one(cluster, b"Weights", False)
                    if (idx_node is None) != (w_node is None):
                        fail("cluster_weight_arrays_missing_pair", cluster_location)
                    indices = raw_array(cluster, b"Indexes", np.int64, cluster_location, False)
                    weights = raw_array(cluster, b"Weights", np.float64, cluster_location, False)
                    if len(indices) != len(weights):
                        fail("cluster_weight_array_count", cluster_location, indices=len(indices), weights=len(weights))
                    if len(indices) != len(set(indices.tolist())):
                        fail("duplicate_cluster_vertex_index", cluster_location)
                    if ((indices < 0) | (indices >= nverts)).any():
                        fail("cluster_vertex_index_range", cluster_location)
                    if ((weights < 0) | (weights > 1.0 + WEIGHT_TOLERANCE)).any():
                        fail("cluster_weight_range", cluster_location)
                    actual_weights = {int(i): float(w) for i, w in zip(indices, weights)
                                      if 0 <= i < nverts and math.isfinite(float(w))}
                    wanted = weights_by_bone[bone_name]
                    errors = [abs(actual_weights.get(i, 0.0) - wanted.get(i, 0.0))
                              for i in set(actual_weights) | set(wanted)]
                    worst_weight = max(errors, default=0.0)
                    mismatch_count = sum(error > WEIGHT_TOLERANCE for error in errors)
                    item["weight_max_abs_error"] = max(item["weight_max_abs_error"], worst_weight)
                    item["weight_mismatches"] += mismatch_count
                    item["weights_nonzero"] += sum(weight != 0 for weight in actual_weights.values())
                    for index, weight in actual_weights.items():
                        actual_sums[index] += weight
                    if mismatch_count:
                        fail("raw_skin_weight_mismatch", cluster_location, bone=bone_name,
                             max_abs=worst_weight, vertex_count=mismatch_count)
                    item["clusters"][bone_name] = {
                        "id": cluster_id, "weight_entries": len(indices),
                        "weight_max_abs_error": worst_weight, "weight_mismatches": mismatch_count,
                        "TransformLink": link_metrics, "Transform": transform_metrics,
                        "TransformAssociateModel": associate_metrics,
                        "mesh_bind_closure": closure_metrics,
                    }
            exact_names(seen_cluster_bones, expected_bones, location + "/cluster_bones")
            for bone_name, count in Counter(seen_cluster_bones).items():
                if count != 1:
                    fail("duplicate_mesh_bone_cluster", location, bone=bone_name, count=count)
            item["weight_sum_max_abs_error"] = float(np.abs(actual_sums - expected_sums).max(initial=0.0))
            item["unweighted_vertices"] = int(np.count_nonzero(actual_sums == 0.0))

            expected_shapes = expectation.get("shapes", {})
            blend_ids = connected(geometry_id, "children", b"Deformer", b"BlendShape")
            if len(blend_ids) != (1 if expected_shapes else 0):
                fail("mesh_blend_shape_count", location, expected=int(bool(expected_shapes)), actual=len(blend_ids))
            channel_names = []
            for blend_id in blend_ids:
                reached_blends.add(blend_id)
                if connected(blend_id, "parents", b"Geometry", b"Mesh") != [geometry_id]:
                    fail("blend_shape_mesh_connection", blend_id)
                channel_ids = connected(blend_id, "children", b"Deformer", b"BlendShapeChannel")
                for channel_id in channel_ids:
                    reached_channels.add(channel_id)
                    channel = by_id[channel_id]
                    shape_name = _name(channel)
                    channel_names.append(shape_name)
                    shape_location = f"{location}/Shape/{shape_name}"
                    if connected(channel_id, "parents", b"Deformer", b"BlendShape") != [blend_id]:
                        fail("shape_channel_blend_connection", shape_location)
                    shape_ids = connected(channel_id, "children", b"Geometry", b"Shape")
                    if len(shape_ids) != 1:
                        fail("channel_shape_geometry_count", shape_location, actual=len(shape_ids))
                        continue
                    shape_id = shape_ids[0]
                    reached_shapes.add(shape_id)
                    shape = by_id[shape_id]
                    if connected(shape_id, "parents", b"Deformer", b"BlendShapeChannel") != [channel_id]:
                        fail("shape_geometry_channel_connection", shape_location)
                    if _name(shape) != shape_name:
                        fail("shape_geometry_channel_name", shape_location, name=_name(shape))
                    indices = raw_array(shape, b"Indexes", np.int64, shape_location)
                    values = raw_array(shape, b"Vertices", np.float64, shape_location)
                    full_weights = raw_array(channel, b"FullWeights", np.float64, shape_location)
                    deform_percent = float(_first(channel, b"DeformPercent"))
                    if not math.isfinite(deform_percent):
                        fail("shape_deform_percent_nonfinite", shape_location)
                    wanted_percent = float(expectation.get("shape_values", {}).get(shape_name, 0.0)) * 100.0
                    if not math.isfinite(wanted_percent):
                        raise ValueError(f"{mesh_name}/{shape_name}: expected shape value must be finite")
                    if not math.isfinite(deform_percent) or abs(deform_percent - wanted_percent) > WEIGHT_TOLERANCE:
                        fail("shape_deform_percent_mismatch", shape_location,
                             expected=wanted_percent, actual=deform_percent)
                    if len(full_weights) != len(indices):
                        fail("shape_full_weights_count", shape_location,
                             indices=len(indices), full_weights=len(full_weights))
                    if not np.isfinite(full_weights).all() or (np.abs(full_weights - 100.0) > WEIGHT_TOLERANCE).any():
                        fail("shape_full_weights_mismatch", shape_location,
                             expected=100.0,
                             max_abs=float(np.abs(full_weights - 100.0).max(initial=0.0)))
                    if values.size != len(indices) * 3 or not len(indices):
                        fail("shape_sparse_array_count", shape_location,
                             indices=len(indices), vertex_values=int(values.size))
                        continue
                    if len(indices) != len(set(indices.tolist())):
                        fail("duplicate_shape_vertex_index", shape_location)
                    if ((indices < 0) | (indices >= nverts)).any():
                        fail("shape_vertex_index_range", shape_location)
                        continue
                    if shape_name not in expected_shapes:
                        continue
                    wanted = np.asarray(expected_shapes[shape_name], dtype=np.float64)
                    if wanted.shape != (nverts, 3) or not np.isfinite(wanted).all():
                        raise ValueError(f"{mesh_name}/{shape_name}: expected delta must be finite N x 3")
                    dense = np.zeros((nverts, 3), dtype=np.float64)
                    dense[indices] = values.reshape(-1, 3)
                    delta_error = float(np.abs(dense - wanted).max(initial=0.0)) if np.isfinite(dense).all() else None
                    expected_zero = bool(np.all(wanted == 0.0))
                    raw_dummy = bool(len(indices) == 1 and int(indices[0]) == 0 and np.all(values == 0.0))
                    if expected_zero and not raw_dummy:
                        fail("zero_shape_dummy_mismatch", shape_location,
                             sparse_vertices=len(indices), raw_all_zero=bool(np.all(values == 0.0)))
                    if delta_error is None or delta_error > MATRIX_COORD_TOLERANCE:
                        fail("shape_delta_mismatch", shape_location, max_abs=delta_error)
                    item["shapes"][shape_name] = {
                        "channel_id": channel_id, "geometry_id": shape_id,
                        "sparse_vertices": len(indices), "delta_max_abs_error": delta_error,
                        "expected_all_zero": expected_zero, "raw_zero_dummy": raw_dummy,
                        "DeformPercent": deform_percent, "expected_DeformPercent": wanted_percent,
                        "FullWeights_min": float(full_weights.min()) if len(full_weights) else None,
                        "FullWeights_max": float(full_weights.max()) if len(full_weights) else None,
                    }
            exact_names(channel_names, expected_shapes, location + "/shape_channels")
            for shape_name, count in Counter(channel_names).items():
                if count != 1:
                    fail("duplicate_shape_channel_name", location, shape=shape_name, count=count)

        for label, nodes, reached in (
            ("MeshGeometry", mesh_geometries, reached_geometries),
            ("Skin", skin_nodes, reached_skins),
            ("Cluster", cluster_nodes, reached_clusters),
            ("ShapeGeometry", shape_nodes, reached_shapes),
            ("BlendShapeChannel", channel_nodes, reached_channels),
            ("BlendShape", [node for node in objects.elems if _kind(node, b"Deformer", b"BlendShape")], reached_blends),
        ):
            orphan_ids = sorted(int(node.props[0]) for node in nodes if int(node.props[0]) not in reached)
            if orphan_ids:
                fail("unmatched_raw_objects", label, ids=orphan_ids)
        report["passed"] = not report["failures"]
    except Exception as exc:
        fail("audit_exception", type(exc).__name__, message=str(exc))
    report["failure_count"] = len(report["failures"])
    return _json_safe(report)
