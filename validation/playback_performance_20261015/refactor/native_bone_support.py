"""Compact witnesses for the experimental bone route; no native operations.

Golden float32 coordinates/normals are compressed only in worker memory for
max/RMS comparisons. Reports contain hashes/counts/metrics, never raw arrays.
"""
from array import array
import hashlib
import math
import zlib

import native_validation_support as base


VECTOR_FIELDS = ("vertex_coordinates", "vertex_normals", "polygon_normals", "corner_normals")


def vector_bytes(obj):
    import bpy
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.data
    result = {}
    for name, collection, field in (
        ("vertex_coordinates", mesh.vertices, "co"), ("vertex_normals", mesh.vertices, "normal"),
        ("polygon_normals", mesh.polygons, "normal"), ("corner_normals", mesh.corner_normals, "vector"),
    ):
        values = array("f", [0.0]) * (len(collection) * 3)
        collection.foreach_get(field, values)
        result[name] = values.tobytes()
    return result


def compressed_vectors(values):
    return {name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                   "compressed": zlib.compress(raw, level=1)} for name, raw in values.items()}


def vector_difference(golden, current, *, coordinates=False):
    raw = zlib.decompress(golden["compressed"])
    if len(raw) != golden["bytes"] or hashlib.sha256(raw).hexdigest() != golden["sha256"]:
        raise RuntimeError("In-memory golden vector integrity failed")
    if len(raw) != len(current) or len(raw) % 12:
        raise RuntimeError("Coordinate/normal vector scope changed")
    left, right = array("f"), array("f")
    left.frombytes(raw)
    right.frombytes(current)
    squared_sum, max_squared, max_component = 0.0, 0.0, 0.0
    minimum, maximum = [math.inf] * 3, [-math.inf] * 3
    for index in range(0, len(left), 3):
        deltas = []
        for axis in range(3):
            a, b = left[index + axis], right[index + axis]
            if not math.isfinite(a) or not math.isfinite(b):
                raise RuntimeError("A native geometry/normal component is non-finite")
            if coordinates:
                minimum[axis] = min(minimum[axis], a)
                maximum[axis] = max(maximum[axis], a)
            deltas.append(float(b) - float(a))
        squared = sum(delta * delta for delta in deltas)
        squared_sum += squared
        max_squared = max(max_squared, squared)
        max_component = max(max_component, *(abs(delta) for delta in deltas))
    count = len(left) // 3
    result = {"exact": raw == current, "vector_count": count,
            "golden_sha256": golden["sha256"], "candidate_sha256": hashlib.sha256(current).hexdigest(),
            "max_vector_error": math.sqrt(max_squared),
            "rms_vector_error": math.sqrt(squared_sum / count) if count else 0.0,
            "max_component_error": max_component}
    result["units"] = "object_model_coordinate_units" if coordinates else "unitless_normal_components"
    if coordinates:
        diagonal = math.sqrt(sum((maximum[axis] - minimum[axis]) ** 2 for axis in range(3))) if count else 0.0
        result.update(source_bbox_min=minimum if count else None, source_bbox_max=maximum if count else None,
                      source_bbox_diagonal=diagonal,
                      max_error_fraction_of_bbox_diagonal=result["max_vector_error"] / diagonal if diagonal else None,
                      rms_error_fraction_of_bbox_diagonal=result["rms_vector_error"] / diagonal if diagonal else None)
    return result


def foreign_shape_keys(obj, managed_names=(), mask_copies=None):
    """Compare foreign keys and effective masks after an intentional rename."""
    import bpy
    keys = obj.data.shape_keys
    if keys is None:
        return {"sha256": base.object_hash(None), "count": 0, "components": {}}
    managed = set(managed_names)
    reverse_masks = {target: source for source, target in (mask_copies or {}).items()}
    evaluated_keys = keys.evaluated_get(bpy.context.evaluated_depsgraph_get())
    components = {}
    for index, key in enumerate(keys.key_blocks):
        if key.name in managed:
            continue
        coordinates = array("f", [0.0]) * (len(key.data) * 3)
        key.data.foreach_get("co", coordinates)
        effective = array("f", [0.0]) * len(obj.data.vertices)
        if key.vertex_group:
            group = obj.vertex_groups.get(key.vertex_group)
            if group is not None:
                for vertex in obj.data.vertices:
                    effective[vertex.index] = next((item.weight for item in vertex.groups if item.group == group.index), 0.0)
        evaluated_key = evaluated_keys.key_blocks.get(key.name)
        components[key.name] = base.object_hash({
            "index": index, "coordinates_sha256": hashlib.sha256(coordinates.tobytes()).hexdigest(),
            "count": len(key.data), "raw_value": float(key.value).hex(),
            "evaluated_value": float(evaluated_key.value if evaluated_key else key.value).hex(),
            "mute": bool(key.mute), "relative_key": key.relative_key.name,
            "logical_vertex_group": reverse_masks.get(key.vertex_group, key.vertex_group),
            "effective_mask_sha256": hashlib.sha256(effective.tobytes()).hexdigest(),
            "interpolation": key.interpolation, "slider_min": float(key.slider_min).hex(),
            "slider_max": float(key.slider_max).hex(),
        })
    return {"sha256": base.object_hash(components), "components": components,
            "count": len(components), "use_relative": bool(keys.use_relative),
            "eval_time": float(keys.eval_time).hex()}


def rig_original_witness(rig, original_names):
    import bpy
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    names = tuple(original_names)
    if not all(name in rig.data.bones and name in evaluated.pose.bones for name in names):
        raise RuntimeError("An original bone disappeared")
    rest = {name: base.exact_matrix(rig.data.bones[name].matrix_local) for name in names}
    pose = {name: base.exact_matrix(evaluated.pose.bones[name].matrix) for name in names}
    channels = {name: {
        "basis": base.exact_matrix(rig.pose.bones[name].matrix_basis),
        "rotation_mode": rig.pose.bones[name].rotation_mode,
        "location": base.raw_native(rig.pose.bones[name].location),
        "rotation_euler": base.raw_native(rig.pose.bones[name].rotation_euler),
        "rotation_quaternion": base.raw_native(rig.pose.bones[name].rotation_quaternion),
        "rotation_axis_angle": base.raw_native(rig.pose.bones[name].rotation_axis_angle),
        "scale": base.raw_native(rig.pose.bones[name].scale),
    } for name in names}
    return {"sha256": base.object_hash({"rest": rest, "pose": pose, "channels": channels,
                                        "world": base.exact_matrix(evaluated.matrix_world)}),
            "rest_sha256": base.object_hash(rest), "pose_sha256": base.object_hash(pose),
            "channels_sha256": base.object_hash(channels), "original_bone_count": len(names)}


def geometry_strict(geometry, *, converted=False):
    components = geometry["components"]
    omitted = set(VECTOR_FIELDS)
    if converted:
        omitted.update(("weights", "vertex_groups"))
    result = {}
    for key, value in components.items():
        if key in omitted:
            continue
        # Built-in position is the same numeric output already compared through
        # vertex_coordinates. Every other stored attribute remains strict.
        if key.startswith("attribute:") and key.rsplit(":", 1)[-1] == "position":
            continue
        result[key] = value
    return result


def dormant_managed_keys(obj, names):
    components = {}
    for name in names:
        key = obj.data.shape_keys.key_blocks.get(name)
        if key is None or not key.mute or key.value != 0.0:
            raise RuntimeError("Bone route has an active/missing managed corrective key")
        values = array("f", [0.0]) * (len(key.data) * 3)
        key.data.foreach_get("co", values)
        components[name] = hashlib.sha256(values.tobytes()).hexdigest()
    return components


def weight_rewrite_witness(source, target, rig, plan, preview):
    """Validate only approved float32 raw transfers and copied foreign masks."""
    source_names = {group.index: group.name for group in source.vertex_groups}
    target_names = {group.index: group.name for group in target.vertex_groups}
    rewrites = {row.index: row for row in plan.rewrites}
    helper_names = preview.helper_names
    mask_copies = preview.mask_copies
    managed = set(plan.managed_key_names)
    affected = {name for row in plan.rewrites for name, _helper, _a in row.transfers}
    for key in target.data.shape_keys.key_blocks:
        if key.name not in managed:
            original = source.data.shape_keys.key_blocks[key.name]
            expected_mask = mask_copies.get(original.vertex_group, original.vertex_group)
            if key.vertex_group != expected_mask:
                raise RuntimeError("A foreign key's mask binding changed unexpectedly")
    expected_groups = set(source_names.values()) | set(helper_names.values()) | set(mask_copies.values())
    if set(target_names.values()) != expected_groups:
        raise RuntimeError("Unexpected vertex-group addition/removal")
    def f32(value):
        return array("f", [value])[0]
    rows_hash = hashlib.sha256()
    for source_vertex, target_vertex in zip(source.data.vertices, target.data.vertices):
        expected = {source_names[item.group]: float(item.weight) for item in source_vertex.groups}
        for original, copied in mask_copies.items():
            if original not in affected or copied in rig.data.bones:
                raise RuntimeError("Foreign mask copy is not an approved nondeform group")
            if expected.get(original, 0.0) > 0.0:
                expected[copied] = expected[original]
        rewrite = rewrites.get(source_vertex.index)
        if rewrite is not None:
            raw = dict(expected)
            for original, helper_key, influence in rewrite.transfers:
                amount = raw[original]
                if influence == 1.0:
                    expected.pop(original, None)
                else:
                    expected[original] = f32(amount * (1.0 - influence))
                expected[helper_names[helper_key]] = f32(amount * influence)
        actual = {target_names[item.group]: float(item.weight) for item in target_vertex.groups}
        if actual != expected:
            raise RuntimeError("Unexpected raw weight change at vertex " + str(source_vertex.index))
        rows_hash.update(base.object_hash(sorted(actual.items())).encode("ascii"))
    return {"approved_raw_float32_transfers_only": True, "vertices": len(source.data.vertices),
            "rewrite_vertices": len(rewrites), "helper_groups": len(helper_names),
            "mask_copies": dict(mask_copies), "raw_weights_sha256": rows_hash.hexdigest()}


def bone_frame_witness(scene, pairs, runtime, reverse, converted, rig_names):
    """Converted maps logical mesh name to {managed_names, mask_copies}."""
    import bpy
    components, scope, vectors = {}, {}, {}
    for name, obj in sorted(pairs, key=lambda row: row[0]):
        if obj.type == "MESH":
            geometry = base.geometry_witness(obj, reverse)
            info = converted.get(name, {})
            strict = geometry_strict(geometry, converted=bool(info))
            components["strict_geometry:" + name] = base.object_hash(strict)
            components["foreign_keys:" + name] = base.object_hash(foreign_shape_keys(
                obj, info.get("managed_names", ()), info.get("mask_copies", {})))
            vectors[name] = vector_bytes(obj)
            scope[name] = {"geometry_scope": geometry["scope"], "strict_geometry_components": strict,
                           "full_geometry_sha256": geometry["sha256"],
                           "evaluated_object_world_matrix_hex": base.exact_matrix(obj.evaluated_get(
                               bpy.context.evaluated_depsgraph_get()).matrix_world)}
            if info and info.get("bone_route"):
                scope[name]["dormant_managed_coordinates"] = dormant_managed_keys(obj, info["managed_names"])
            elif runtime.RECORD_KEY in obj:
                scope[name]["healthy_forearm"] = base.forearm_health(runtime, obj)
        elif obj.type == "ARMATURE":
            rig = rig_original_witness(obj, rig_names[name])
            components["original_rig:" + name] = rig["sha256"]
            scope[name] = rig
    return {"frame": scene.frame_current, "sha256": base.object_hash(components),
            "components": components, "scope": scope}, vectors


def compare_frames(golden, golden_vectors, candidate, candidate_vectors, *, converted_names=()):
    changed = sorted(key for key in set(golden["components"]) | set(candidate["components"])
                     if golden["components"].get(key) != candidate["components"].get(key))
    if set(golden_vectors) != set(candidate_vectors):
        raise RuntimeError("Complete mesh coordinate coverage changed")
    metrics = {name: {field: vector_difference(golden_vectors[name][field], raw, coordinates=field == "vertex_coordinates")
                      for field, raw in values.items()} for name, values in candidate_vectors.items()}
    converted = set(converted_names)
    changed.extend("unconverted_vectors:" + name for name, values in metrics.items()
                   if name not in converted and not all(item["exact"] for item in values.values()))
    changed.sort()
    return {"strict_nonvector_outputs_exact": not changed, "changed_strict_components": changed,
            "all_coordinates_and_normals_exact": all(item["exact"] for mesh in metrics.values() for item in mesh.values()),
            "source_strict_sha256": golden["sha256"], "candidate_strict_sha256": candidate["sha256"],
            "meshes": metrics}
