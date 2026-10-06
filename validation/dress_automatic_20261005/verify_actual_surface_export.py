"""Static Dress-only FBX roundtrip in one disposable factory/background child.

Requires the passing actual-surface installation JSON and its exact saved QA
blend. Uses the real model exporter/worker; does not launch another process,
deploy, publish, save the artist, reset/bake Cloth, or write any Unity project.
An asymmetric Shape Key is a disposable QA input, never an artist modification.
FBX/Blender roundtrip is not Unity importer or Magica simulation acceptance.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time
import traceback
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from mathutils import Matrix, Vector


HERE = Path(__file__).resolve().parent
REPOSITORY = Path(r"D:\MyRepository\Blender-addons-by-Randy")
BACKEND = "ACTUAL_SURFACE_DELTA_V1"
FILENAME = "Cosha_Dress_StaticQA.fbx"
COORDINATE_GUARD = 3.e-6  # Existing native exporter fixture's coordinate guard.
WEIGHT_GUARD = 1.e-6      # Existing native exporter fixture's weight guard.
REST_MATRIX_GUARD = 3.e-6
DEPENDENCIES = {
    "validate_real_dress.py": "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046",
    "diagnose_skin_transfer.py": "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Exact passing installation QA blend")
    parser.add_argument("--install-report", type=Path, required=True)
    parser.add_argument("--expected-surface-sha", required=True, help="Explicit final reviewed skirt_surface.py SHA256")
    parser.add_argument("--expected-worker-sha", required=True, help="Explicit final reviewed unity_export_worker.py SHA256")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", help="Exact owned source, never a naming heuristic")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.input, args.install_report, args.output = (path.resolve() for path in
                                                  (args.input, args.install_report, args.output))
    args.expected_surface_sha = args.expected_surface_sha.casefold()
    require(len(args.expected_surface_sha) == 64 and all(character in "0123456789abcdef" for character in args.expected_surface_sha),
            "Provide the full explicit frozen surface SHA256")
    args.expected_worker_sha = args.expected_worker_sha.casefold()
    require(len(args.expected_worker_sha) == 64 and all(character in "0123456789abcdef" for character in args.expected_worker_sha),
            "Provide the full explicit frozen worker SHA256")
    require(args.input.is_file() and args.input.suffix.casefold() == ".blend"
            and args.input.is_relative_to(HERE), "Use an existing QA blend under this Validation directory")
    require(args.install_report.is_file() and args.install_report.is_relative_to(HERE), "Use the installation gate JSON")
    require(args.output.is_relative_to(HERE) and args.output != HERE
            and not args.input.is_relative_to(args.output) and not args.install_report.is_relative_to(args.output),
            "Use a new dedicated Validation child output directory")
    for relative in ("result/surface_export.json", "scenes/Cosha_Dress_QA_export_snapshot.blend",
                     "scenes/Cosha_Dress_QA_public_library.blend", "result/public_job.json", "stage/" + FILENAME):
        require(not (args.output / relative).exists(), "Refusing to overwrite a QA artifact: " + relative)
    return args


def modules():
    for name, expected in DEPENDENCIES.items():
        require(sha(HERE / name) == expected, "Frozen QA dependency changed: " + name)
    sys.path[:0] = [str(HERE), str(REPOSITORY / "addons")]
    import validate_real_dress as qa
    import diagnose_skin_transfer as diag
    import character_designer as addon
    from character_designer import skirt_surface as surface, unity_export as exporter, unity_export_worker as worker
    require(Path(addon.__file__).resolve().is_relative_to(REPOSITORY / "addons"), "Canonical source was shadowed")
    return qa, diag, addon, surface, exporter, worker


def canonical_hashes(manifest):
    return {str(Path(path).resolve()).casefold(): state["sha256"] for path, state in manifest.items()
            if Path(path).resolve().is_relative_to(REPOSITORY / "addons/character_designer")}


def approved_runtime_difference(current, installed, expected_surface_sha, expected_worker_sha):
    before, after = canonical_hashes(installed), canonical_hashes(current)
    surface_path = str((REPOSITORY / "addons/character_designer/skirt_surface.py").resolve()).casefold()
    worker_path = str((REPOSITORY / "addons/character_designer/unity_export_worker.py").resolve()).casefold()
    require(set(before) == set(after), "Canonical file inventory changed since installation")
    for path, expected in ((surface_path, expected_surface_sha), (worker_path, expected_worker_sha)):
        require(isinstance(expected, str) and len(expected) == 64
                and all(character in "0123456789abcdef" for character in expected.casefold()),
                "Both surface and worker require explicit complete frozen SHA256 values")
        require(after.get(path) == expected.casefold(), "Current canonical source differs from its explicit final reviewed SHA: " + path)
    differences = [path for path in before if before[path] != after[path]]
    require(set(differences) <= {surface_path, worker_path}, "A canonical module other than the explicitly reviewed surface/worker changed after installation")
    return [{"path": path, "install_sha256": before[path], "export_sha256": after[path],
             "scope": "This export run is a new compatibility validation of explicit surface/worker code; the old install did not validate changed code"}
            for path in differences]


def check(report, qa, name, condition, **facts):
    qa.report_check(report, name, condition, **facts)
    require(condition, "Static export gate failed: " + name)


def inventory():
    return {key: sorted(block.name for block in getattr(bpy.data, key)) for key in
            ("objects", "meshes", "armatures", "curves", "node_groups", "collections", "actions", "shape_keys")}


def key_inventory():
    return {key.name: {"pointer": key.as_pointer(), "users": key.users} for key in bpy.data.shape_keys}


def capture_owned_key(data, label, before, owned):
    key = data.shape_keys
    if key is None:
        return
    name, pointer = key.name, key.as_pointer()
    require(pointer not in {item["pointer"] for item in before.values()}, "A transient Mesh borrowed an original Key ID")
    entry = {"name": name, "pointer": pointer, "mesh": data.name, "mesh_pointer": data.as_pointer(), "stage": label}
    if name in owned:
        require(owned[name]["pointer"] == pointer and owned[name]["mesh_pointer"] == data.as_pointer(),
                "A transient Key ID changed ownership")
    else:
        owned[name] = entry


def remove_owned_keys(owned):
    removed = []
    for name, entry in owned.items():
        key = bpy.data.shape_keys.get(name)
        if key is None:
            removed.append({**entry, "already_removed_with_owned_mesh": True})
            continue
        native_users = bpy.data.user_map(subset={key}).get(key, set())
        require(key.as_pointer() == entry["pointer"] and key.library is None and not native_users,
                "A captured owned transient Key changed identity or acquired a user: " + name)
        counter_before_removal = key.users
        bpy.data.batch_remove(ids=(key,))
        require(bpy.data.shape_keys.get(name) is None, "Blender did not remove the exact owned transient Key")
        removed.append({**entry, "removed_after_owned_mesh": True,
                        "native_reverse_users": [], "counter_before_removal": counter_before_removal})
    return removed


def point_error(first, second):
    require(len(first) == len(second), "Vertex correspondence changed")
    require(all(len(point) == 3 and all(math.isfinite(value) for value in point)
                for points in (first, second) for point in points), "Nonfinite or invalid vertex coordinates")
    return max(((Vector(a) - Vector(b)).length for a, b in zip(first, second)), default=0.)


def named_weights(obj):
    names = {group.index: group.name for group in obj.vertex_groups}
    return [{names[item.group]: float(item.weight) for item in vertex.groups if item.weight > 0.}
            for vertex in obj.data.vertices]


def weight_error(first, second):
    require(len(first) == len(second), "Weight correspondence changed")
    require(all(math.isfinite(value) and 0. <= value <= 1. for weights in (first, second)
                for vertex in weights for value in vertex.values()), "Nonfinite or invalid skin weight")
    require(all(set(a) == set(b) for a, b in zip(first, second)), "Weighted group identity changed")
    return max((abs(value - other[name]) for values, other in zip(first, second)
                for name, value in values.items()), default=0.)


def retained_skin_weights(vertices, deform_names):
    return [{name: value for name, value in vertex.items() if name in deform_names} for vertex in vertices]


def static_mesh(obj):
    keys = obj.data.shape_keys
    return {"vertices": [list(vertex.co) for vertex in obj.data.vertices],
            "faces": [list(face.vertices) for face in obj.data.polygons],
            "edges": sorted(sorted(edge.vertices) for edge in obj.data.edges),
            "weights": named_weights(obj),
            "keys": {} if keys is None else {key.name: [list(point.co) for point in key.data] for key in keys.key_blocks},
            "matrix_world": [list(row) for row in obj.matrix_world]}


def strip_boundary(source, rig, cloth, qa, surface):
    return {"raw": qa.digest(qa.raw_mesh_content(source)), "source_data_pointer": source.data.as_pointer(),
            "rest": qa.digest(qa.rest_content(rig)),
            "actions": {action.name: qa.digest(qa.action_content(action)) for action in bpy.data.actions},
            "cache": qa.cache_state(cloth)}


def negative_capture_tests(source, rig, record, proof, report, qa, surface, exporter, worker):
    objects = [rig, source]
    job = {"dress_surfaces": [proof]}
    initial = {"inventory": inventory(), "record": source[qa.skirt.RECORD_KEY],
               "graph": qa.digest(surface._node_content(source.modifiers[record["physics"]["surface"]["overlay"]].node_group)),
               "raw": qa.digest(qa.raw_mesh_content(source)), "rest": qa.digest(qa.rest_content(rig))}
    group = source.modifiers[record["physics"]["surface"]["overlay"]].node_group
    node = group.nodes["Cloth Index"]
    clamp = node.clamp
    rejected = None
    try:
        node.clamp = not clamp
        try:
            worker._capture_dress_snapshot(job, objects)
        except Exception as error:
            rejected = {"type": type(error).__name__, "message": str(error)}
    finally:
        node.clamp = clamp
    surface.validate_snapshot(source, proof)
    check(report, qa, "edited_position_graph_rejected_before_strip", rejected is not None,
          rejection=rejected, edit="Only owned Sample Index clamp was temporarily changed")
    mesh = bpy.data.meshes.new("QA External Node User Mesh")
    foreign = bpy.data.objects.new("QA External Node User", mesh)
    bpy.context.scene.collection.objects.link(foreign)
    rejected = None
    try:
        foreign.modifiers.new("QA Shared Owned Graph", "NODES").node_group = group
        require(group.users == 2, "The external-user negative case is not an exact second native user")
        try:
            worker._capture_dress_snapshot(job, objects)
        except Exception as error:
            rejected = {"type": type(error).__name__, "message": str(error)}
    finally:
        bpy.data.objects.remove(foreign, do_unlink=True)
        require(mesh.users == 0, "The foreign test mesh acquired another user")
        bpy.data.meshes.remove(mesh)
    surface.validate_snapshot(source, proof)
    check(report, qa, "external_owned_node_user_rejected_before_strip", rejected is not None,
          rejection=rejected, original_group_users=group.users)
    helper = bpy.data.objects[record["physics"]["surface"]["roles"]["CLOTH_PROXY"][0]]
    role = helper[surface.ROLE_KEY]
    rejected = None
    try:
        helper[surface.ROLE_KEY] = "QA_UNKNOWN_ROLE"
        try:
            exporter._dress_surface_helper(helper)
        except Exception as error:
            rejected = {"type": type(error).__name__, "message": str(error)}
    finally:
        helper[surface.ROLE_KEY] = role
    surface.validate_snapshot(source, proof)
    check(report, qa, "unknown_helper_role_rejected", rejected is not None, rejection=rejected)
    final = {"inventory": inventory(), "record": source[qa.skirt.RECORD_KEY],
             "graph": qa.digest(surface._node_content(group)), "raw": qa.digest(qa.raw_mesh_content(source)),
             "rest": qa.digest(qa.rest_content(rig))}
    check(report, qa, "negative_test_inputs_restored_exact", final == initial)
    for name in record["physics"]["colliders"] + [name for names in record["physics"]["surface"]["roles"].values() for name in names]:
        helper = bpy.data.objects[name]
        require(exporter._dress_surface_helper(helper), "An exact owned helper was not classified for exclusion: " + name)
        rejected = None
        try:
            worker._capture_dress_snapshot(job, objects + [helper])
        except Exception as error:
            rejected = str(error)
        require(rejected is not None, "An owned helper was accepted in the explicit FBX inventory: " + name)
    check(report, qa, "every_owned_helper_excluded_from_explicit_fbx_inventory", True,
          owned_helper_names=sorted(set(record["physics"]["colliders"]) |
                                   {name for names in record["physics"]["surface"]["roles"].values() for name in names}),
          criterion="Native role/source/owner inventory; visibility is not the exclusion rule")


def add_qa_key(source, record, report):
    added_basis = source.data.shape_keys is None
    if added_basis:
        source.shape_key_add(name="Basis", from_mix=False)
    require(source.data.shape_keys.use_relative, "The relative Shape Key export contract is required")
    name = "QA Dress Static Asymmetric"
    require(name not in source.data.shape_keys.key_blocks, "The source already contains this QA key name")
    key = source.shape_key_add(name=name, from_mix=False)
    key.relative_key = source.data.shape_keys.reference_key
    ring = record["fit"]["rings"][len(record["fit"]["rings"]) // 2]
    indices = ring[:2]
    height = max(vertex.co.z for vertex in source.data.vertices) - min(vertex.co.z for vertex in source.data.vertices)
    require(math.isfinite(height) and height > 0. and len(indices) == 2, "The exact fitted QA key input is invalid")
    for index in indices:
        key.data[index].co.x += .02 * height
        key.data[index].co.z += .01 * height
    key.value = .37
    source.data.update()
    report["qa_key_input"] = {"name": name, "raw_indices": indices, "added_basis": added_basis,
                              "local_delta": [.02 * height, 0., .01 * height], "value": key.value,
                              "scope": "Disposable QA input; initial source/artist is restored by reopening the exact input QA file"}
    return name


def plain_static_reference(source, record, owned_keys, qa, surface, worker, report):
    # Independent geometry chart from author Basis/Key coordinates and the
    # original static modifier stack. The physical C coordinates are never read
    # into this reference. Remove only the clone's owned overlay before baking.
    before_keys = key_inventory()
    owned_key_ids = {}
    source_raw = qa.digest(qa.raw_mesh_content(source))
    lifecycle = report["plain_reference_key_lifecycle"] = {"before": before_keys, "owned_captured": [],
        "scope": "Only Key IDs read directly from this independent copied Mesh and its returned native baked Mesh; no global orphan purge"}
    probe = source.copy()
    probe.data = source.data.copy()
    copied_data = probe.data
    capture_owned_key(copied_data, "owned copied source Mesh", before_keys, owned_key_ids)
    probe.name = "QA Plain Source Static Reference"
    for key in tuple(probe.keys()):
        if key.startswith("character_designer_"):
            del probe[key]
    bpy.context.scene.collection.objects.link(probe)
    probe.modifiers.remove(probe.modifiers[record["physics"]["surface"]["overlay"]])
    try:
        warnings = []
        facts = worker._bake_mesh(bpy.context, probe, owned_keys, warnings)
        return static_mesh(probe), {"worker_mesh": facts, "warnings": warnings,
                                  "source": "Original Basis/Keys and original modifiers, without the owned overlay"}
    finally:
        baked_data = probe.data  # Also cover a late exception after native data assignment.
        capture_owned_key(baked_data, "owned native returned baked Mesh", before_keys, owned_key_ids)
        lifecycle["owned_captured"] = list(owned_key_ids.values())
        bpy.data.objects.remove(probe, do_unlink=True)
        for data in {copied_data, baked_data} - {None}:
            require(data.users == 0, "The disposable static reference acquired an outside user")
            bpy.data.meshes.remove(data)
        lifecycle["cleanup"] = remove_owned_keys(owned_key_ids)
        lifecycle["after"] = key_inventory()
        lifecycle["original_key_table_exact"] = lifecycle["after"] == before_keys
        lifecycle["unclaimed_new_keys"] = {name: entry for name, entry in lifecycle["after"].items()
                                           if name not in before_keys or before_keys[name]["pointer"] != entry["pointer"]}
        require(not lifecycle["unclaimed_new_keys"], "Native baker left unclaimed Key IDs; no arbitrary cleanup: "
                + json.dumps(lifecycle["unclaimed_new_keys"], ensure_ascii=False))
        require(lifecycle["original_key_table_exact"] and qa.digest(qa.raw_mesh_content(source)) == source_raw,
                "The independent static reference changed original Key IDs/users or source Key/mesh content")
        surface.validate(source, source[qa.skirt.RIG_KEY], qa.skirt.read_record(source))


def observe_export(job, source, rig, cloth, record, report, qa, surface, worker):
    old_strip, old_clear, old_clean, old_bpy = (worker._strip_dress_snapshot, worker._clear_animation,
                                             worker._clean_skeleton, worker.bpy)
    events = []

    def strip(captured):
        before = strip_boundary(source, rig, cloth, qa, surface)
        modifiers = [surface._rna(modifier) for modifier in source.modifiers
                     if modifier.name != record["physics"]["surface"]["overlay"]]
        result = old_strip(captured)
        after = strip_boundary(source, rig, cloth, qa, surface)
        require(after == before and [surface._rna(modifier) for modifier in source.modifiers] == modifiers,
                "Owned overlay stripping changed Basis/Keys/weights/Rest/Actions/cache/original modifiers")
        events.append("strip")
        report["strip_boundary"] = {"raw_mesh_sha256": before["raw"], "rest_sha256": before["rest"],
                                    "all_original_inputs_and_modifiers_exact": True,
                                    "same_mesh_data_pointer": True, "native_cache_exact": True,
                                    "simulation_coordinates_written_to_basis": False}
        return result

    def clear(block):
        require(events and events[0] == "strip", "Worker cleared animation before native overlay proof/strip")
        events.append("clear")
        return old_clear(block)

    def clean(context, obj, objects):
        before = qa.rest_content(obj)
        geometry = {bone.name: {"head": list(bone.head_local), "tail": list(bone.tail_local)}
                    for bone in obj.data.bones}
        result = old_clean(context, obj, objects)
        differences = []
        for name in result:
            bone = obj.data.bones[name]
            entries = [(abs(before[name]["matrix"][row][col] - bone.matrix_local[row][col]), row, col)
                       for row in range(4) for col in range(4)]
            difference, row, col = max(entries)
            differences.append({"bone": name, "matrix_max_error": difference,
                "worst_entry": [row, col], "before_matrix": before[name]["matrix"],
                "after_matrix": [list(entry) for entry in bone.matrix_local],
                "before_geometry": geometry[name],
                "after_geometry": {"head": list(bone.head_local), "tail": list(bone.tail_local)},
                "before_length": before[name]["length"], "after_length": bone.length,
                "before_parent": before[name]["parent"], "after_parent": bone.parent.name if bone.parent else None,
                "before_connect": before[name]["connect"], "after_connect": bone.use_connect})
        maximum = max((entry["matrix_max_error"] for entry in differences), default=0.)
        report["retained_source_rest"] = {"names": result, "matrix_max_error": maximum,
                                          "guard": REST_MATRIX_GUARD,
                                          "outside_guard_bones": sorted(entry["bone"] for entry in differences
                                                                         if entry["matrix_max_error"] > REST_MATRIX_GUARD),
                                          "worst_bones": sorted(differences, key=lambda item: item["matrix_max_error"], reverse=True)[:8],
                                          "scope": "Retained native Rest matrices; control filtering reconnects retained parents and clears use_connect as existing export behavior"}
        require(maximum <= REST_MATRIX_GUARD, "Static worker cleanup changed retained native Rest matrices")
        return result

    class Delegate:
        def __init__(self, target, **overrides):
            self.target, self.overrides = target, overrides
        def __getattr__(self, name):
            return self.overrides[name] if name in self.overrides else getattr(self.target, name)

    def actual_fbx(**options):
        require(all(options.get(name) is False for name in
                    ("bake_anim", "bake_anim_use_nla_strips", "bake_anim_use_all_actions")),
                "The ordinary static model worker attempted animation baking")
        report["actual_fbx_options"] = {key: sorted(value) if isinstance(value, set) else value for key, value in options.items()}
        return bpy.ops.export_scene.fbx(**options)

    try:
        worker._strip_dress_snapshot, worker._clear_animation, worker._clean_skeleton = strip, clear, clean
        worker.bpy = Delegate(bpy, ops=Delegate(bpy.ops, export_scene=Delegate(bpy.ops.export_scene, fbx=actual_fbx)))
        result = worker.export_job(job)
        require(events and events[0] == "strip", "The real worker never reached its owned overlay boundary")
        report["worker_order"] = {"first_event": events[0], "clear_calls_after_strip": events.count("clear")}
        return result
    finally:
        worker._strip_dress_snapshot, worker._clear_animation, worker._clean_skeleton, worker.bpy = old_strip, old_clear, old_clean, old_bpy


def roundtrip(filepath, mesh_expected, rest_expected, meters, expected_names, report, qa):
    # All references needed below are plain dictionaries, not stale RNA.
    physical_guard = min(COORDINATE_GUARD, COORDINATE_GUARD * meters)
    diagnostic = {"status": "collecting", "filepath": str(filepath),
                  "blender_version": str(bpy.app.version_string),
                  "source_meters": float(meters), "imported_meters": None,
                  "guards": {"coordinates_and_heads_m": float(physical_guard),
                             "weights": float(WEIGHT_GUARD), "normalized_axis_vectors": float(REST_MATRIX_GUARD)},
                  "coordinates_max_error_m": None, "shape_key_errors_m": {},
                  "weights_max_error": None, "rest_head_max_error_m": None, "rest_axis_max_error": None,
                  "per_bone": {}, "worst_bones": [], "outside_guard": {},
                  "scope": "Existing guard diagnostics only; missing measurements are not accepted as zero/Pass"}
    report["native_static_fbx_roundtrip_diagnostics"] = diagnostic
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before_actions = {action.name for action in bpy.data.actions}
    bpy.ops.preferences.addon_enable(module="io_scene_fbx")
    diagnostic["importer_options"] = {"explicit": {"filepath": str(filepath), "use_anim": True},
                                      "native_rna_defaults": {}}
    # Record defaults without passing new options or changing the native call.
    try:
        for prop in bpy.ops.import_scene.fbx.get_rna_type().properties:
            if prop.identifier == "rna_type":
                continue
            if getattr(prop, "is_array", False):
                value = list(prop.default_array)
            else:
                value = getattr(prop, "default", None)
            if isinstance(value, set):
                value = sorted(value)
            diagnostic["importer_options"]["native_rna_defaults"][prop.identifier] = value
    except Exception as error:
        diagnostic["importer_options"]["defaults_read_error"] = str(error)
    result = bpy.ops.import_scene.fbx(filepath=str(filepath), use_anim=True)
    diagnostic["import_operator_result"] = sorted(result)
    require("FINISHED" in result, "Native FBX reimport did not finish")
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    diagnostic["imported_objects"] = [{"name": obj.name, "type": obj.type} for obj in bpy.context.scene.objects]
    require(len(rigs) == len(meshes) == 1, "Dress-only FBX did not contain exactly one Mesh and one Rig")
    rig, mesh = rigs[0], meshes[0]
    diagnostic["root_transform"] = {
        "rig": rig.name, "parent": rig.parent.name if rig.parent else None,
        "matrix_world": [[float(value) for value in row] for row in rig.matrix_world],
        "matrix_local": [[float(value) for value in row] for row in rig.matrix_local],
        "matrix_basis": [[float(value) for value in row] for row in rig.matrix_basis],
        "location": [float(value) for value in rig.location],
        "rotation_mode": rig.rotation_mode, "rotation_euler": [float(value) for value in rig.rotation_euler],
        "rotation_quaternion": [float(value) for value in rig.rotation_quaternion],
        "rotation_axis_angle": [float(value) for value in rig.rotation_axis_angle],
        "scale": [float(value) for value in rig.scale],
        "expected_root_bones": sorted(name for name, item in rest_expected.items() if item["parent"] is None),
        "imported_root_bones": sorted(bone.name for bone in rig.data.bones if bone.parent is None)}
    require({rig.name, mesh.name} == set(expected_names), "FBX imported extra/missing helper objects")
    require(len(bpy.context.scene.objects) == 2, "The static Dress FBX contains unexpected non-Mesh/Rig objects")
    actual = static_mesh(mesh)
    imported_meters = float(bpy.context.scene.unit_settings.scale_length)
    diagnostic["imported_meters"] = imported_meters
    require(math.isfinite(imported_meters) and imported_meters > 0., "Invalid imported metre scale")
    expected_world = Matrix(mesh_expected["matrix_world"])
    actual_world = mesh.matrix_world
    diagnostic["mesh_transform"] = {
        "expected_world": [[float(value) for value in row] for row in expected_world],
        "imported_world": [[float(value) for value in row] for row in actual_world]}
    diagnostic["topology"] = {"expected_vertices": len(mesh_expected["vertices"]), "imported_vertices": len(actual["vertices"]),
                              "faces_equal": actual["faces"] == mesh_expected["faces"],
                              "edges_equal": actual["edges"] == mesh_expected["edges"]}
    require(actual["faces"] == mesh_expected["faces"] and actual["edges"] == mesh_expected["edges"],
            "FBX roundtrip changed the explicit vertex-index topology")
    coordinate_error = point_error([expected_world @ Vector(point) * meters for point in mesh_expected["vertices"]],
                                   [actual_world @ Vector(point) * imported_meters for point in actual["vertices"]])
    diagnostic["coordinates_max_error_m"] = float(coordinate_error)
    diagnostic["coordinates_max_error_source_world"] = float(coordinate_error / meters)
    diagnostic["outside_guard"]["coordinate_vertex_indices"] = [index for index, (expected, imported) in
        enumerate(zip(mesh_expected["vertices"], actual["vertices"])) if
        (expected_world @ Vector(expected) * meters - actual_world @ Vector(imported) * imported_meters).length > physical_guard]
    deform_names = {name for name, item in rest_expected.items() if item["deform"]}
    weights = weight_error(retained_skin_weights(mesh_expected["weights"], deform_names),
                           retained_skin_weights(actual["weights"], deform_names))
    diagnostic["weights_max_error"] = float(weights)
    weight_errors = {name: {"max_error": 0., "compared_positive_entries": 0, "outside_guard_vertices": []}
                     for name in sorted(deform_names)}
    for index, (expected, imported) in enumerate(zip(mesh_expected["weights"], actual["weights"])):
        for name in expected.keys() & deform_names:
            error = abs(expected[name] - imported[name])
            weight_errors[name]["max_error"] = max(weight_errors[name]["max_error"], float(error))
            weight_errors[name]["compared_positive_entries"] += 1
            if error > WEIGHT_GUARD:
                weight_errors[name]["outside_guard_vertices"].append(index)
    diagnostic["weights_per_deform_bone"] = weight_errors
    diagnostic["outside_guard"]["weight_bones"] = sorted(name for name, item in weight_errors.items()
                                                        if item["max_error"] > WEIGHT_GUARD)
    diagnostic["shape_key_inventory"] = {"expected": sorted(mesh_expected["keys"]), "imported": sorted(actual["keys"])}
    require(set(actual["keys"]) == set(mesh_expected["keys"]), "FBX dropped or added an artist/QA Shape Key")
    key_errors = {name: point_error([expected_world @ Vector(point) * meters for point in points],
                                   [actual_world @ Vector(point) * imported_meters for point in actual["keys"][name]])
                  for name, points in mesh_expected["keys"].items()}
    diagnostic["shape_key_errors_m"] = {name: float(error) for name, error in key_errors.items()}
    diagnostic["outside_guard"]["shape_key_names"] = sorted(name for name, error in key_errors.items() if error > physical_guard)
    diagnostic["shape_key_outside_guard_vertices"] = {name: [index for index, (expected, imported) in
        enumerate(zip(points, actual["keys"][name])) if
        (expected_world @ Vector(expected) * meters - actual_world @ Vector(imported) * imported_meters).length > physical_guard]
        for name, points in mesh_expected["keys"].items()}
    diagnostic["bone_inventory"] = {"expected": sorted(rest_expected), "imported": sorted(rig.data.bones.keys())}
    require(set(rig.data.bones.keys()) == set(rest_expected), "FBX changed retained deform/attachment inventory")
    head_error, axis_error = 0., 0.
    for name, expected in rest_expected.items():
        bone = rig.data.bones[name]
        details = {"bone": name, "expected_parent": expected["parent"],
                   "imported_parent": bone.parent.name if bone.parent else None,
                   "expected_deform": bool(expected["deform"]), "imported_deform": bool(bone.use_deform),
                   "weight_max_error": weight_errors.get(name, {}).get("max_error"),
                   "weight_compared_positive_entries": weight_errors.get(name, {}).get("compared_positive_entries", 0)}
        diagnostic["per_bone"][name] = details
        require((bone.parent.name if bone.parent else None) == expected["parent"], "FBX changed retained parent: " + name)
        matrix = rig.matrix_world @ bone.matrix_local
        native = Matrix(expected["world"])
        require(all(math.isfinite(value) for owner in (matrix, native) for row in owner for value in row)
                and all(owner.to_3x3().col[index].length > 1.e-12
                        for owner in (matrix, native) for index in range(3)), "Nonfinite or degenerate retained Rest matrix")
        bone_head_error = (matrix.translation * imported_meters - native.translation * meters).length
        bone_axis_errors = [(matrix.to_3x3().col[index].normalized()
                             - native.to_3x3().col[index].normalized()).length for index in range(3)]
        head_error = max(head_error, bone_head_error)
        axis_error = max(axis_error, max(bone_axis_errors))
        details.update({"head_error_m": float(bone_head_error), "axis_errors": [float(value) for value in bone_axis_errors],
                        "axis_max_error": float(max(bone_axis_errors)),
                        "expected_world_rest": [[float(value) for value in row] for row in native],
                        "imported_world_rest": [[float(value) for value in row] for row in matrix],
                        "imported_local_rest": [[float(value) for value in row] for row in bone.matrix_local],
                        "expected_head_m": [float(value * meters) for value in native.translation],
                        "imported_head_m": [float(value * imported_meters) for value in matrix.translation],
                        "expected_normalized_axes": [[float(value) for value in native.to_3x3().col[index].normalized()] for index in range(3)],
                        "imported_normalized_axes": [[float(value) for value in matrix.to_3x3().col[index].normalized()] for index in range(3)]})
        diagnostic["rest_head_max_error_m"], diagnostic["rest_axis_max_error"] = float(head_error), float(axis_error)
    diagnostic["outside_guard"]["head_bones"] = sorted(name for name, item in diagnostic["per_bone"].items()
                                                      if item["head_error_m"] > physical_guard)
    diagnostic["outside_guard"]["axis_bones"] = sorted(name for name, item in diagnostic["per_bone"].items()
                                                      if item["axis_max_error"] > REST_MATRIX_GUARD)
    diagnostic["worst_bones_order"] = "Maximum of head/physical_guard, axis/REST_MATRIX_GUARD and weight/WEIGHT_GUARD"
    diagnostic["worst_bones"] = sorted(diagnostic["per_bone"].values(), key=lambda item: max(
        item["head_error_m"] / physical_guard, item["axis_max_error"] / REST_MATRIX_GUARD,
        (item["weight_max_error"] or 0.) / WEIGHT_GUARD), reverse=True)[:8]
    diagnostic["status"] = "all_guard_metrics_collected_before_acceptance"
    require(coordinate_error <= physical_guard and max(key_errors.values(), default=0.) <= physical_guard,
            "FBX changed source static Basis or Shape Key coordinates beyond the existing native-world and metre guards")
    require(weights <= WEIGHT_GUARD and head_error <= physical_guard and axis_error <= REST_MATRIX_GUARD,
            "FBX changed skin weights or retained Rest beyond the declared guards")
    arms = [modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE"]
    require(len(arms) == 1 and arms[0].object == rig and all(not bone.constraints for bone in rig.pose.bones),
            "The imported static skin has missing binding or runtime constraints")
    require({action.name for action in bpy.data.actions} == before_actions,
            "Static FBX unexpectedly imported animation Actions")
    require(all(owner.animation_data is None or
                (owner.animation_data.action is None and not owner.animation_data.nla_tracks)
                for owner in (rig, mesh, mesh.data.shape_keys) if owner is not None),
            "Static FBX unexpectedly imported an Action/NLA binding")
    diagnostic["status"] = "accepted_by_existing_guards"
    check(report, qa, "native_static_fbx_roundtrip", True,
          vertices=len(mesh.data.vertices), faces=len(mesh.data.polygons), retained_bones=len(rest_expected),
          coordinates_max_error_m=coordinate_error, shape_key_errors_m=key_errors,
          coordinates_guard_m=physical_guard, coordinates_max_error_source_world=coordinate_error / meters,
          weights_max_error=weights, rest_head_max_error_m=head_error, rest_axis_max_error=axis_error,
          weight_scope="Exact named positive weights on retained deform bones; FBX does not encode generic Blender mask groups",
          imported_objects=sorted(expected_names), imported_new_actions=0,
          original_fbx_tail_lengths_and_use_connect="Not encoded/accepted as Blender author metadata by this check")


def public_snapshot(source, rig, report, qa, surface, exporter, args):
    """Real public host/write, with explicit Dress-only scope and no child launch.

    The ordinary whole-character scope is covered elsewhere. Restrict the
    collected native binding inventory here to this one Dress for a focused
    static roundtrip; all remaining launcher/proof/library code is unchanged.
    """
    record = qa.skirt.read_record(source)
    _actual, cloth = surface.validate(source, rig, record)
    before = strip_boundary(source, rig, cloth, qa, surface)
    before_inventory = inventory()
    scope = exporter._collection_scope(bpy.context, rig)
    require(source in scope['eligible'] and scope['bindings'][source] == {rig},
            "This focused Dress is not natively bound only to its proved Main Rig")
    scope = {**scope, 'eligible': [source]}
    native_collect = exporter.collect_character
    config = SimpleNamespace(directory=str(args.output / 'unpublished'),
                             filename=Path(FILENAME).stem, asset_id='', extras=[], simple_materials=[])

    def collect(context, selected_rig, selected_config):
        require(selected_rig == rig and selected_config is config, "Public launcher changed focused scope")
        result = native_collect(context, selected_rig, selected_config, _scope=scope)
        require(set(result['objects']) == {rig, source}, "The explicit FBX scope grew unexpectedly")
        return result

    require(exporter._ACTIVE_JOB is None, "The disposable process already owns an export")
    with patch.object(exporter, 'collect_character', side_effect=collect), \
            patch.object(exporter.subprocess, 'Popen') as process:
        job = exporter.begin_export(bpy.context, rig, config)
    try:
        require(process.call_count == 1, "Public launcher did not reach its intercepted process boundary")
        require(strip_boundary(source, rig, cloth, qa, surface) == before and inventory() == before_inventory,
                "The public host snapshot changed original native inputs or datablock inventory")
        specification = json.loads((job['root'] / 'job.json').read_text(encoding='utf-8'))
        require(set(specification['objects']) == {rig.name, source.name}
                and len(specification['dress_surfaces']) == 1,
                "Public snapshot lost or expanded its captured source inventory")
        library = args.output / 'scenes/Cosha_Dress_QA_public_library.blend'
        library.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(job['root'] / 'character.blend', library)
        (args.output / 'result').mkdir(parents=True, exist_ok=True)
        shutil.copy2(job['root'] / 'job.json', args.output / 'result/public_job.json')
        report['public_library_snapshot'] = {
            'path': str(library), 'sha256': sha(library), 'bytes': library.stat().st_size,
            'public_begin_export_reached': True, 'native_libraries_write': True,
            'host_inputs_exact': True, 'child_process_launched': False,
            'objects': specification['objects'],
            'scope': 'Native bound Dress-only collected subset; no whole-character scope or publication acceptance'}
        return job, specification, library
    except Exception:
        exporter._dispose(job)
        raise


def run(args, report, qa, surface, exporter, worker, protection):
    source, rig, record = qa.owned_source(args.source)
    require(record.get("physics", {}).get("backend") == BACKEND, "Install the actual-surface backend first")
    actual, cloth = surface.validate(source, rig, record)
    report["input_source"] = {"source": source.name, "rig": rig.name, "owner": record["owner"],
                              "cloth_raw_vertices": len(actual.data.vertices)}
    check(report, qa, "loaded_install_assets_exact_before_qa_inputs", protection.verify()["success"])
    source_name, rig_name = source.name, rig.name
    owned_keys = exporter._owned_keys([source]).get(source.name, [])
    qa_name = add_qa_key(source, record, report)
    surface.validate(source, rig, record)
    proof = exporter._capture_dress_surfaces([rig, source])
    require(len(proof) == 1, "Coordinator did not capture exactly this owned surface")
    report["captured_proof_sha256"] = qa.digest(proof)
    negative_capture_tests(source, rig, record, proof[0], report, qa, surface, exporter, worker)
    plain, plain_facts = plain_static_reference(source, record, owned_keys, qa, surface, worker, report)
    report["plain_source_reference"] = plain_facts
    require(qa_name in plain["keys"] and point_error(plain["keys"][qa_name], plain["keys"]["Basis"]) > COORDINATE_GUARD,
            "The asymmetric QA Shape Key did not survive the plain native static baker")
    # Freeze this independently of worker filtering, so deleting a weighted
    # source bone cannot remove that same weight from both sides of the check.
    deform_names = {bone.name for bone in rig.data.bones if bone.use_deform}
    required_weighted_deforms = {name for weights in plain['weights'] for name, weight in weights.items()
                                if name in deform_names and weight > 0.}
    require(required_weighted_deforms, "The independent source has no positive deform skin weights")
    # Retain original Action assets through the disposable snapshot/worker.
    for index, action in enumerate(protection.action_refs):
        bpy.context.scene[f"CD_QA_ExportAuthorAction_{index:04d}"] = action
    qa.save_candidate(args.output / "scenes/Cosha_Dress_QA_export_snapshot.blend", args.input)
    host_job, job, library = public_snapshot(source, rig, report, qa, surface, exporter, args)
    try:
        bpy.ops.wm.open_mainfile(filepath=str(library), load_ui=False, use_scripts=False)
        source, rig, record = qa.owned_source(source_name)
        surface.validate_snapshot(source, job['dress_surfaces'][0])
        _actual, cloth = surface.validate(source, rig, record)
        check(report, qa, "native_public_library_retains_exact_home_scene_proof", True,
              home_scene=record['physics']['surface']['home_scene'],
              explicit_objects=job['objects'], replacement_scene_or_repair_created=False)
        result = observe_export(job, source, rig, cloth, record, report, qa, surface, worker)
        require(result.get("ok") is True, "The native model worker did not finish")
        exporter._dress_publication(job, result)  # Facts validation only; no publication.
        report["worker_result"] = result
        generated = static_mesh(bpy.data.objects[source_name])
        retained = bpy.data.objects[rig_name]
        check(report, qa, "original_weighted_deform_bones_remain_native_deforms",
              all(name in retained.data.bones and retained.data.bones[name].use_deform
                  for name in required_weighted_deforms),
              independent_required_deforms=sorted(required_weighted_deforms),
              criterion="Frozen from original native deform flags and positive source skin weights before worker filtering")
        check(report, qa, "worker_output_is_plain_source_basis_keys_skin",
              generated["faces"] == plain["faces"] and generated["edges"] == plain["edges"]
              and point_error(generated["vertices"], plain["vertices"]) <= COORDINATE_GUARD
              and weight_error(retained_skin_weights(generated["weights"], deform_names),
                               retained_skin_weights(plain["weights"], deform_names)) <= WEIGHT_GUARD
              and set(generated["keys"]) == set(plain["keys"])
              and all(point_error(generated["keys"][name], plain["keys"][name]) <= COORDINATE_GUARD for name in plain["keys"]),
              plain_basis_max_error=point_error(generated["vertices"], plain["vertices"]),
              scope="Original author Basis/Keys and retained deform skin plus the normal static modifier bake; never C coordinates. All raw groups/weights were exact at strip.")
        rest = {bone.name: {"parent": bone.parent.name if bone.parent else None,
                            "deform": bone.use_deform,
                            "world": [list(row) for row in retained.matrix_world @ bone.matrix_local]}
                for bone in retained.data.bones}
        filepath = args.output / "stage" / FILENAME
        filepath.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(job['stage']) / FILENAME, filepath)
        report["fbx"] = {"path": str(filepath), "sha256": sha(filepath), "bytes": filepath.stat().st_size}
        roundtrip(filepath, generated, rest, float(job["unit_scale"]), [rig_name, source_name], report, qa)
    finally:
        temporary_path = Path(host_job['root'])
        exporter._dispose(host_job)
        check(report, qa, "public_host_job_fully_disposed",
              not temporary_path.exists() and exporter._ACTIVE_JOB is None,
              temporary_directory_removed=not temporary_path.exists(),
              active_job_cleared=exporter._ACTIVE_JOB is None,
              child_process_launched=False)


def main(args):
    require(bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath,
            "Refusing export QA outside an empty factory background child")
    qa, diag, addon, surface, exporter, worker = modules()
    gate = json.loads(args.install_report.read_text(encoding="utf-8"))
    require(gate.get("success") is True and gate.get("stage") == "install" and gate.get("artist_disk_exact") is True,
            "Installation/native protection gate did not pass")
    require(len(gate.get("checks", ())) >= 17 and all(item.get("passed") is True for item in gate["checks"]),
            "Use the complete passing installation mechanics gate")
    prepared = gate["prepared_candidate"]
    require(Path(prepared["path"]).resolve() == args.input and sha(args.input) == prepared["sha256"],
            "Input is not the exact passing prepared QA blend")
    current = diag.source_manifest()
    runtime_differences = approved_runtime_difference(current, gate["source_manifest_after"],
                                                      args.expected_surface_sha, args.expected_worker_sha)
    artist = Path(gate["artist_path"]).resolve()
    report = {"success": False, "production_export_accepted": False, "artist_saved_by_verifier": False,
              "input": {"path": str(args.input), **qa.file_state(args.input)},
              "install_gate": {"path": str(args.install_report), "sha256": sha(args.install_report)},
              "artist_before": qa.file_state(artist), "source_manifest_before": current,
              "expected_surface_sha256": args.expected_surface_sha, "expected_worker_sha256": args.expected_worker_sha,
              "install_to_export_runtime_differences": runtime_differences,
              "harness_sha256": sha(Path(__file__)), "checks": [],
              "limits": ["Static Dress and MainRig only, not all character parts/material fidelity",
                         "QA asymmetric Key is synthetic; original Key assets are protected after input reload",
                         "Blender native FBX roundtrip is not Unity importer or Magica physics validation",
                         "Blender vertex Cloth animation is not exported; animation baking remains disabled",
                         "Dependency graph reads may evaluate cold Cloth; no forward replay or simulation bake is performed",
                         "FBX retained Rest head/orientation/parent are checked; Blender bone tail/connect metadata is not claimed"]}
    args.output.mkdir(parents=True, exist_ok=True)
    protection = None
    started = time.perf_counter()
    try:
        addon.register()
        bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
        protection = qa.Protection()
        report["protected_initial_qa_assets"] = protection.summary()
        run(args, report, qa, surface, exporter, worker, protection)
        report["success"] = all(item["passed"] for item in report["checks"])
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        if protection is not None:
            try:
                bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
                source, rig, record = qa.owned_source(args.source)
                surface.validate(source, rig, record)
                report["restored_initial_qa_assets"] = protection.verify()
                report["success"] = report["success"] and report["restored_initial_qa_assets"]["success"]
            except Exception as error:
                report["success"] = False
                report["qa_restore_error"] = str(error)
        report["artist_after"] = qa.file_state(artist)
        report["artist_disk_exact"] = report["artist_after"] == report["artist_before"]
        report["input_after"] = {"path": str(args.input), **qa.file_state(args.input)}
        report["input_qa_disk_exact"] = report["input_after"] == report["input"]
        report["source_manifest_after"] = diag.source_manifest()
        report["canonical_and_frozen_code_exact"] = report["source_manifest_after"] == report["source_manifest_before"]
        report["harness_code_exact"] = sha(Path(__file__)) == report["harness_sha256"]
        report["success"] = report["success"] and all(report[key] for key in
            ("artist_disk_exact", "input_qa_disk_exact", "canonical_and_frozen_code_exact", "harness_code_exact"))
        report["elapsed_seconds"] = time.perf_counter() - started
        destination = args.output / "result/surface_export.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(diag.json_content(report), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"success": report["success"], "report": str(destination),
                          "elapsed_seconds": report["elapsed_seconds"]}, ensure_ascii=False), flush=True)
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
