"""Compact exact native output witnesses, imported only inside private Blender.

No operations or registrations are performed by importing this file. Geometry
hashing reuses the previously accepted pinned native RNA oracle, so its supported
fields/rejection behavior are unchanged. Raw arrays are never put in reports.
"""
from array import array
import hashlib
import json
from pathlib import Path
import types


ORACLE_PATH = Path(__file__).resolve().parents[2] / "playback_performance_20261014" / "round4" / "probe_shoes_merge_07741.py"
ORACLE_SHA256 = "b7da2d785422d8d46e26b77ae0bd3899f6a64dbf2919d5a7174ee255f85191f5"
_ORACLE = None


def pin(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def object_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def oracle():
    global _ORACLE
    if _ORACLE is None:
        raw = ORACLE_PATH.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ORACLE_SHA256:
            raise RuntimeError("Accepted native geometry oracle source changed")
        prefix, boundary, _ = raw.decode("utf-8-sig").replace("\r\n", "\n").partition('\nif __name__ == "__main__":\n')
        if not boundary:
            raise RuntimeError("Accepted native geometry oracle main boundary is absent")
        module = types.ModuleType("_x_frozen_playback_geometry_oracle")
        module.__file__ = str(ORACLE_PATH)
        exec(compile(prefix, str(ORACLE_PATH), "exec"), module.__dict__)
        _ORACLE = module
    return _ORACLE


def exact_matrix(matrix):
    return [[float(value).hex() for value in row] for row in matrix]


def logical_id(value, id_reverse):
    """Normalize only display identity of explicitly paired cloned native IDs."""
    if value is None:
        return None
    value = getattr(value, "original", value)
    source = id_reverse.get(value.as_pointer(), value)
    return [type(source).__name__, source.name_full,
            source.library.filepath if source.library else None]


def geometry_witness(obj, id_reverse):
    """Hash the complete evaluated mesh using exact accepted native fields."""
    import bpy
    result = oracle().evaluated_shoes(obj)
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    # This is the only name-sensitive component in the inherited oracle. ID
    # data itself remains exact; candidate names map through explicit pairs.
    result["components"]["materials"] = object_hash([
        logical_id(material, id_reverse) for material in evaluated.data.materials])
    result["sha256"] = object_hash(result["components"])
    return result


def shape_keys_witness(obj, id_reverse, *, exclude_managed=()):
    keys = obj.data.shape_keys
    if keys is None:
        return {"sha256": object_hash(None), "count": 0, "components": {}}
    excluded = set(exclude_managed)
    components = {}
    for index, key in enumerate(keys.key_blocks):
        if key.name in excluded:
            continue
        values = array("f", [0.0]) * (len(key.data) * 3)
        key.data.foreach_get("co", values)
        relative = key.relative_key
        value = {
            "index": index, "name": key.name, "count": len(key.data),
            "coordinates_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
            "value": float(key.value).hex(), "mute": bool(key.mute),
            "relative_key": relative.name if relative else None,
            "vertex_group": key.vertex_group,
            "interpolation": key.interpolation,
            "slider_min": float(key.slider_min).hex(),
            "slider_max": float(key.slider_max).hex(),
        }
        components[key.name] = object_hash(value)
    return {"sha256": object_hash(components), "count": len(components),
            "components": components, "use_relative": bool(keys.use_relative),
            "eval_time": float(keys.eval_time).hex()}


def rig_witness(obj):
    import bpy
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    pose = {bone.name: exact_matrix(bone.matrix) for bone in evaluated.pose.bones}
    rest = {bone.name: exact_matrix(bone.matrix_local) for bone in obj.data.bones}
    return {"sha256": object_hash({"pose": pose, "rest": rest,
                                   "world": exact_matrix(evaluated.matrix_world)}),
            "pose_sha256": object_hash(pose), "rest_sha256": object_hash(rest),
            "bone_count": len(rest)}


def forearm_health(runtime, obj):
    records = runtime._records(obj)
    if not records:
        raise RuntimeError("Expected calibrated playback mesh has no records")
    rows = []
    for side, record in records.items():
        key = runtime._managed_key(obj, side, record, required=True, repair_name=False)
        row = {"side": side, "support_vertices": len(record["vertices"]),
               "enabled": record.get("enabled", True), "key": key.name,
               "value": float(key.value), "mute": bool(key.mute)}
        if not row["enabled"] or row["value"] != 1.0 or row["mute"]:
            raise RuntimeError("Corrective output is disabled or muted: " + repr(row))
        rows.append(row)
    if obj.name in runtime._ERRORS:
        raise RuntimeError("Authoring error on expected owner: " + runtime._ERRORS[obj.name])
    return sorted(rows, key=lambda row: row["side"])


def frame_witness(scene, pairs, runtime, id_reverse, *, expected_forearm=None):
    """Pairs are (logical source name, current native object) in a single scene."""
    components, scopes = {}, {}
    if scene.frame_current < 1:
        raise RuntimeError("Invalid validation frame")
    for name, obj in sorted(pairs, key=lambda item: item[0]):
        if obj.name not in scene.objects:
            raise RuntimeError("Paired output object is absent from selected scene")
        if obj.type == "MESH":
            geometry = geometry_witness(obj, id_reverse)
            components["mesh:" + name] = geometry["sha256"]
            # Individual geometry components enable diagnosis without arrays.
            scopes[name] = {"geometry": geometry["scope"],
                            "geometry_components": geometry["components"]}
            keys = shape_keys_witness(obj, id_reverse)
            components["keys:" + name] = object_hash(keys)
            scopes[name]["shape_key_components"] = keys["components"]
            if expected_forearm and name in expected_forearm:
                health = []
                for expected in expected_forearm[name]:
                    key = obj.data.shape_keys.key_blocks.get(expected["key"])
                    if key is None:
                        raise RuntimeError("Expected private corrective key disappeared")
                    row = {**expected, "value": float(key.value), "mute": bool(key.mute)}
                    if row["value"] != 1.0 or row["mute"] or not row["enabled"]:
                        raise RuntimeError("Private corrective output is paused or muted")
                    health.append(row)
                components["forearm_health:" + name] = object_hash(health)
                scopes[name]["forearm_health"] = health
            elif runtime.RECORD_KEY in obj:
                health = forearm_health(runtime, obj)
                components["forearm_health:" + name] = object_hash(health)
                scopes[name]["forearm_health"] = health
        elif obj.type == "ARMATURE":
            rig = rig_witness(obj)
            components["rig:" + name] = rig["sha256"]
            scopes[name] = rig
    if not any(key.startswith("mesh:") for key in components):
        raise RuntimeError("No full-model mesh outputs were covered")
    if not any(key.startswith("forearm_health:") for key in components):
        raise RuntimeError("No active Forearm outputs were covered")
    return {"sha256": object_hash(components), "components": components,
            "scope": scopes, "frame": scene.frame_current,
            "subframe": float(scene.frame_subframe).hex()}


def compare_witness(before, after):
    keys = set(before["components"]) | set(after["components"])
    changed = sorted(key for key in keys if before["components"].get(key) != after["components"].get(key))
    return {"exact": not changed and before["frame"] == after["frame"]
                     and before["subframe"] == after["subframe"],
            "changed_components": changed,
            "source_sha256": before["sha256"], "playback_sha256": after["sha256"]}


def raw_native(value):
    """Exact source custom-property values, including live native references."""
    import bpy
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return {"float_hex": value.hex()}
    if isinstance(value, bpy.types.ID):
        return {"id": logical_id(value, {}), "pointer": value.as_pointer()}
    if hasattr(value, "items"):
        return {str(key): raw_native(item) for key, item in value.items()}
    try:
        return [raw_native(item) for item in value]
    except TypeError as exc:
        raise RuntimeError("Unsupported source native property type: " + type(value).__name__) from exc


def source_property_witness(scene):
    """Protect raw authoring channels, Rest and native ownership properties."""
    components = {"scene_properties": object_hash(raw_native(dict(scene.items())))}
    for obj in scene.objects:
        channels = {name: raw_native(getattr(obj, name)) for name in
                    ("location", "rotation_mode", "rotation_euler", "rotation_quaternion",
                     "rotation_axis_angle", "scale", "delta_location", "delta_rotation_euler",
                     "delta_rotation_quaternion", "delta_scale", "matrix_parent_inverse")}
        props = {"object": raw_native(dict(obj.items())), "channels": channels}
        if obj.data is not None:
            props["data"] = raw_native(dict(obj.data.items()))
        if obj.type == "ARMATURE":
            props["bones"] = {bone.name: {"properties": raw_native(dict(bone.items())),
                                         "rest": exact_matrix(bone.matrix_local)}
                              for bone in obj.data.bones}
            props["pose"] = {bone.name: {"properties": raw_native(dict(bone.items())),
                                        "basis": exact_matrix(bone.matrix_basis)}
                             for bone in obj.pose.bones}
        if obj.type == "MESH" and obj.data.shape_keys:
            props["shape_key_properties"] = raw_native(dict(obj.data.shape_keys.items()))
        components[obj.name] = object_hash(props)
    return {"sha256": object_hash(components), "components": components}


def native_id_pointers():
    import bpy
    result = set()
    for prop in bpy.data.bl_rna.properties:
        if prop.type != "COLLECTION":
            continue
        for item in getattr(bpy.data, prop.identifier):
            if isinstance(item, bpy.types.ID):
                result.add(item.as_pointer())
    return result


def handler_snapshot():
    import bpy
    return {name: [id(callback) for callback in value]
            for name in dir(bpy.app.handlers)
            if isinstance((value := getattr(bpy.app.handlers, name)), list)}


def package_pins(package):
    package = Path(package).resolve()
    return {str(path.relative_to(package)).replace("\\", "/"): pin(path)
            for path in sorted(package.rglob("*.py")) if "__pycache__" not in path.parts}


def verify_package_manifest(package, manifest):
    expected = manifest["files"]
    actual = package_pins(package)
    if set(actual) != set(expected):
        raise RuntimeError("Staged Python source inventory changed")
    for name, source in actual.items():
        if source["sha256"] != expected[name]["sha256"] or source["bytes"] != expected[name]["bytes"]:
            raise RuntimeError("Staged source pin changed: " + name)
    return actual
