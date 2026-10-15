"""Stage04 admission probe: observe a failed custom-property remap, then rethrow.

The protected v4 admission runner owns all input/scene/cleanup proof. This file
only installs one temporary in-memory exception observer around the unchanged
Stage04 function. It performs no alternate remap and prints no vertex arrays.
Root alone may run this in its serialized private background window.
"""
import argparse
import datetime
import hashlib
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
STAGE = HERE / "staged_20261015_04"
PINS = {
    "private_playback_native_runner_v4.py": "1eee3fdb64a940773f512a110d9e8b786541530250e04ead60dd110c91647696",
    "native_validation_support.py": "3994f58288244684679ffd48d0837ac88bcfd9768f0a3a12c3e1d7d5b6265c0a",
    "staged_20261015_04/source_manifest.json": "477f104ef7a0dc96994f7d287df38a2c5786cf9f726df4c93b45576dd3153a38",
    "staged_20261015_04/addons/character_designer/forearm_twist_playback_scene.py": "8e0ff44b3623037baa760a228d71a1d6797912971d85a542c18c4e4848e259f1",
}
BUILDER = "character_designer.forearm_twist_playback_scene"


def _pin(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def protected_pins():
    result = {}
    for relative, expected in PINS.items():
        row = _pin(HERE / relative)
        if row["sha256"] != expected:
            raise RuntimeError("Protected diagnostic dependency changed: " + relative)
        result[relative] = row
    return result


def _read(value, name, default=None):
    try:
        return getattr(value, name, default)
    except BaseException as error:
        return {"read_error": type(error).__name__ + ": " + str(error)}


def _pointer(value):
    try:
        return int(value.as_pointer()) if value is not None else None
    except BaseException:
        return None


def _identity(value):
    if value is None:
        return None
    rna = _read(value, "bl_rna")
    row = {"python_type": type(value).__name__, "rna_type": _read(rna, "identifier"),
           "pointer": _pointer(value)}
    for name in ("name_full", "name", "session_uid", "type", "is_evaluated"):
        observed = _read(value, name)
        if observed is not None:
            row[name] = observed
    library = _read(value, "library")
    row["library"] = {"pointer": _pointer(library), "filepath": _read(library, "filepath")} if library else None
    return row


def _rna_context(value):
    row = {"struct": _identity(value), "owner": _identity(_read(value, "id_data"))}
    try:
        row["path_from_id"] = value.path_from_id()
    except BaseException as error:
        row["path_from_id_error"] = type(error).__name__ + ": " + str(error)
    return row


def _map_matches(value, id_map):
    pointer = _pointer(value)
    rows = []
    for source, target in id_map.items():
        source_pointer, target_pointer = _pointer(source), _pointer(target)
        source_match = value is source or (pointer is not None and pointer == source_pointer)
        target_match = value is target or (pointer is not None and pointer == target_pointer)
        if source_match or target_match:
            rows.append({"matches_source": source_match, "matches_owned_target": target_match,
                         "source": _identity(source), "owned_target": _identity(target)})
    return rows


def _id_reference(value, id_map):
    row = _identity(value)
    row["map_matches"] = _map_matches(value, id_map)
    original = _read(value, "original")
    if original is not None and not isinstance(original, dict):
        row["original"] = _identity(original)
        row["original_map_matches"] = _map_matches(original, id_map)
    else:
        row["original"] = original
    try:
        row["users_scene"] = [_identity(scene) for scene in value.users_scene]
    except AttributeError:
        pass
    except BaseException as error:
        row["users_scene_error"] = type(error).__name__ + ": " + str(error)
    return row


def _brief(value, id_map, id_type):
    if isinstance(value, id_type):
        return {"kind": "native_ID", "value": _id_reference(value, id_map)}
    if value is None or isinstance(value, (bool, int)):
        return {"kind": type(value).__name__, "value": value}
    if isinstance(value, float):
        return {"kind": "float", "hex": value.hex(), "finite": math.isfinite(value)}
    if isinstance(value, str):
        return {"kind": "str", "length": len(value), "preview": value[:256],
                "sha256_utf8": hashlib.sha256(value.encode("utf-8")).hexdigest()}
    row = {"kind": type(value).__name__, "pointer": _pointer(value)}
    try:
        row["length"] = len(value)
    except (TypeError, AttributeError):
        pass
    return row


def _custom_rows(group, id_map, id_type):
    """Every direct custom-property row; sequences stay compact in the report."""
    rows = []
    try:
        keys = tuple(group.keys())
    except BaseException as error:
        return {"rows": rows, "keys_error": type(error).__name__ + ": " + str(error)}
    for key in keys:
        try:
            rows.append({"key": str(key), **_brief(group[key], id_map, id_type)})
        except BaseException as error:
            rows.append({"key": str(key), "read_error": type(error).__name__ + ": " + str(error)})
    return {"rows": rows, "all_direct_rows_recorded": True, "row_count": len(keys)}


def _reference_walk(root, id_map, id_type, failing_group=None):
    """Read mappings AND sequences; never descend into native IDs or strings.

    Scalar sequences are streamed through a compact digest, not reported as
    arrays. Limits are explicit and cannot establish absence when reached.
    """
    result = {"id_references": [], "errors": [], "limits_reached": [], "failing_group_paths": [],
              "scalar_leaf_count": 0, "max_depth": 64, "max_containers": 4096}
    digest, visited = hashlib.sha256(), set()
    failing_pointer = _pointer(failing_group)

    def walk(value, path, depth):
        if isinstance(value, id_type):
            result["id_references"].append({"path": path, **_id_reference(value, id_map)})
            return
        if value is None or isinstance(value, (str, bytes, bool, int, float)):
            digest.update(json.dumps([path, _brief(value, id_map, id_type)], sort_keys=True, allow_nan=False).encode("utf-8"))
            result["scalar_leaf_count"] += 1
            return
        pointer = _pointer(value)
        if value is failing_group or (pointer is not None and pointer == failing_pointer):
            result["failing_group_paths"].append(path)
        token = (type(value).__name__, pointer) if pointer is not None else (type(value).__name__, id(value))
        if token in visited:
            return
        if depth > result["max_depth"] or len(visited) >= result["max_containers"]:
            result["limits_reached"].append(path)
            return
        visited.add(token)
        mapped = False
        try:
            keys_method = getattr(value, "keys", None)
            if callable(keys_method):
                for key in tuple(keys_method()):
                    try:
                        walk(value[key], path + [str(key)], depth + 1)
                    except BaseException as error:
                        result["errors"].append({"path": path + [str(key)], "error": type(error).__name__ + ": " + str(error)})
                mapped = True
        except TypeError as error:
            if "doesn't support IDProperties" not in str(error):
                result["errors"].append({"path": path, "error": type(error).__name__ + ": " + str(error)})
        except BaseException as error:
            result["errors"].append({"path": path, "error": type(error).__name__ + ": " + str(error)})
        # Collections can expose duplicate/empty named keys. Inspect sequence
        # members as well, even after successful mapping lookup; this is why
        # the older raw mapping-only observation was not absence proof.
        try:
            iterator = iter(value)
        except TypeError as error:
            if not mapped:
                result["errors"].append({"path": path, "error": type(error).__name__ + ": " + str(error)})
            return
        try:
            for index, item in enumerate(iterator):
                walk(item, path + [index], depth + 1)
        except BaseException as error:
            result["errors"].append({"path": path, "error": type(error).__name__ + ": " + str(error)})

    # A target may itself be an ID; custom properties, rather than native ID
    # internals, are this observer's entire scope.
    try:
        keys = tuple(root.keys())
        if root is failing_group or (_pointer(root) is not None and _pointer(root) == failing_pointer):
            result["failing_group_paths"].append([])
        for key in keys:
            walk(root[key], [str(key)], 0)
    except BaseException as error:
        result["errors"].append({"path": [], "error": type(error).__name__ + ": " + str(error)})
    result["containers_visited"] = len(visited)
    result["scalar_leaf_digest_sha256"] = digest.hexdigest()
    result["absence_conclusive_within_scope"] = not result["errors"] and not result["limits_reached"]
    return result


def diagnose(error, source, target, id_map, id_type):
    row = {"exception": {"type": type(error).__name__, "message": str(error)},
           "target": _rna_context(target), "source_argument": _rna_context(source) if source is not None else None,
           "target_custom_properties": _custom_rows(target, id_map, id_type),
           "map_count": len(id_map), "observation_after_original_failure": True,
           "read_only_diagnostic": True, "native_ID_internals_traversed": False}
    failing_group, key, value = target, None, None
    tb = error.__traceback__
    while tb is not None:
        local = tb.tb_frame.f_locals
        if tb.tb_frame.f_code.co_name == "walk" and "group" in local:
            failing_group, key, value = local["group"], local.get("key"), local.get("value")
        tb = tb.tb_next
    row["failing_key"] = str(key)
    row["failing_group"] = _rna_context(failing_group)
    row["failing_group_custom_properties"] = _custom_rows(failing_group, id_map, id_type)
    row["failing_value"] = _brief(value, id_map, id_type)
    row["target_custom_reference_walk"] = _reference_walk(target, id_map, id_type, failing_group)
    row["rna_remap_stack"] = []
    frame = inspect.currentframe()
    try:
        frame = frame.f_back
        while frame is not None:
            if frame.f_code.co_name == "_remap_rna" and "struct" in frame.f_locals:
                context = _rna_context(frame.f_locals["struct"])
                prop = frame.f_locals.get("prop")
                context["active_property_identifier"] = _read(prop, "identifier")
                row["rna_remap_stack"].append(context)
            frame = frame.f_back
    finally:
        del frame
    owner = _read(target, "id_data")
    row["source_owner_observations"] = []
    for original, owned in id_map.items():
        if _pointer(owner) is None or _pointer(owner) != _pointer(owned):
            continue
        observation = {"source_owner": _identity(original), "owned_target_owner": _identity(owned),
                       "source_owner_custom_reference_walk": _reference_walk(original, id_map, id_type)}
        try:
            path = target.path_from_id()
            source_struct = original.path_resolve(path) if path else original
            observation["resolved_rna_path"] = path
            observation["source_struct"] = _rna_context(source_struct)
            observation["source_struct_custom_properties"] = _custom_rows(source_struct, id_map, id_type)
            observation["source_struct_custom_reference_walk"] = _reference_walk(source_struct, id_map, id_type)
        except BaseException as lookup_error:
            observation["source_path_resolution_error"] = type(lookup_error).__name__ + ": " + str(lookup_error)
        row["source_owner_observations"].append(observation)
    return row


def main(args, report):
    import bpy
    if not bpy.app.background:
        raise RuntimeError("Private background process required")
    if Path(args.addons).resolve() != (STAGE / "addons").resolve() or Path(args.source_manifest).resolve() != (STAGE / "source_manifest.json").resolve():
        raise RuntimeError("This diagnostic is restricted to original protected Stage04")
    before = protected_pins()
    report["protected_dependencies_before"] = before
    sys.path.insert(0, str(HERE))
    witness = importlib.import_module("native_validation_support")
    package = STAGE / "addons" / "character_designer"
    manifest = json.loads((STAGE / "source_manifest.json").read_text(encoding="utf-8-sig"))
    report["staged_sources_before_observer_import"] = witness.verify_package_manifest(package, manifest)
    sys.path.insert(0, str(package.parent))
    runner = importlib.import_module("private_playback_native_runner_v4")
    scene_module = importlib.import_module(BUILDER)
    if Path(scene_module.__file__).resolve().parent != package.resolve():
        raise RuntimeError("Diagnostic imported a different builder package")
    original = scene_module._copy_id_properties
    report["copy_id_property_diagnostics"] = []

    def observe_copy_id_properties(source, target, id_map):
        try:
            return original(source, target, id_map)
        except BaseException as error:
            try:
                observation = diagnose(error, source, target, id_map, bpy.types.ID)
                report["copy_id_property_diagnostics"].append(observation)
                print("CUSTOM_PROPERTY_DIAGNOSTIC " + json.dumps(observation, ensure_ascii=False, sort_keys=True, allow_nan=False), flush=True)
            except BaseException:
                # Diagnostic failures must never replace the original error.
                report.setdefault("diagnostic_observer_errors", []).append(traceback.format_exc())
            raise

    args.builder_module, args.builder_function, args.admission_only = BUILDER, "build_isolated_scene", True
    scene_module._copy_id_properties = observe_copy_id_properties
    try:
        runner.main(args, report)
    finally:
        owned = scene_module._copy_id_properties is observe_copy_id_properties
        if owned:
            scene_module._copy_id_properties = original
        report["observer_cleanup"] = {"owned_hook_before_restore": owned,
                                      "original_function_restored": scene_module._copy_id_properties is original}
        after = protected_pins()
        report["protected_dependencies_after"] = after
        report["protected_dependencies_unchanged"] = before == after
        if not owned or scene_module._copy_id_properties is not original:
            raise RuntimeError("Diagnostic no longer owned its observer hook")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite native evidence")
    report = {"schema": "x.stage04-custom-property-exception-observer/1", "completed": False,
              "pid": os.getpid(), "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "diagnostic_script": _pin(__file__), "no_artist_open_or_save": True, "no_scene_save": True,
              "no_deploy": True, "performance_acceptance": False, "all_30_complete_outputs_exact": False,
              "limits": ["Saved-frame admission only; no 30-frame, timing or GUI FPS claim.",
                         "Observer reads only after the original custom-property exception and rethrows that exception.",
                         "A completed admission is not artist adoption; no copy or admission guard is relaxed.",
                         "Custom mapping and sequence references are inspected; scalar arrays remain hashes/counts."]}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
