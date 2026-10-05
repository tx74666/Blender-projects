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
import sys
import time
import traceback

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
    for relative in ("result/surface_export.json", "scenes/Cosha_Dress_QA_export_snapshot.blend", "stage/" + FILENAME):
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
        require(key.as_pointer() == entry["pointer"] and key.users == 0,
                "A captured owned transient Key changed identity or acquired a user: " + name)
        bpy.data.batch_remove(ids=(key,))
        require(bpy.data.shape_keys.get(name) is None, "Blender did not remove the exact owned transient Key")
        removed.append({**entry, "removed_after_owned_mesh": True})
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
        result = old_clean(context, obj, objects)
        maximum = max((abs(before[name]["matrix"][row][col] - obj.data.bones[name].matrix_local[row][col])
                       for name in result for row in range(4) for col in range(4)), default=0.)
        require(maximum <= REST_MATRIX_GUARD, "Static worker cleanup changed retained native Rest matrices")
        report["retained_source_rest"] = {"names": result, "matrix_max_error": maximum,
                                          "guard": REST_MATRIX_GUARD,
                                          "scope": "Retained native Rest matrices; control filtering reconnects retained parents and clears use_connect as existing export behavior"}
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
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before_actions = {action.name for action in bpy.data.actions}
    bpy.ops.preferences.addon_enable(module="io_scene_fbx")
    result = bpy.ops.import_scene.fbx(filepath=str(filepath), use_anim=True)
    require("FINISHED" in result, "Native FBX reimport did not finish")
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    require(len(rigs) == len(meshes) == 1, "Dress-only FBX did not contain exactly one Mesh and one Rig")
    rig, mesh = rigs[0], meshes[0]
    require({rig.name, mesh.name} == set(expected_names), "FBX imported extra/missing helper objects")
    require(len(bpy.context.scene.objects) == 2, "The static Dress FBX contains unexpected non-Mesh/Rig objects")
    actual = static_mesh(mesh)
    imported_meters = float(bpy.context.scene.unit_settings.scale_length)
    require(math.isfinite(imported_meters) and imported_meters > 0., "Invalid imported metre scale")
    expected_world = Matrix(mesh_expected["matrix_world"])
    actual_world = mesh.matrix_world
    require(actual["faces"] == mesh_expected["faces"] and actual["edges"] == mesh_expected["edges"],
            "FBX roundtrip changed the explicit vertex-index topology")
    coordinate_error = point_error([expected_world @ Vector(point) * meters for point in mesh_expected["vertices"]],
                                   [actual_world @ Vector(point) * imported_meters for point in actual["vertices"]])
    deform_names = {name for name, item in rest_expected.items() if item["deform"]}
    weights = weight_error(retained_skin_weights(mesh_expected["weights"], deform_names),
                           retained_skin_weights(actual["weights"], deform_names))
    require(set(actual["keys"]) == set(mesh_expected["keys"]), "FBX dropped or added an artist/QA Shape Key")
    key_errors = {name: point_error([expected_world @ Vector(point) * meters for point in points],
                                   [actual_world @ Vector(point) * imported_meters for point in actual["keys"][name]])
                  for name, points in mesh_expected["keys"].items()}
    require(set(rig.data.bones.keys()) == set(rest_expected), "FBX changed retained deform/attachment inventory")
    head_error, axis_error = 0., 0.
    for name, expected in rest_expected.items():
        bone = rig.data.bones[name]
        require((bone.parent.name if bone.parent else None) == expected["parent"], "FBX changed retained parent: " + name)
        matrix = rig.matrix_world @ bone.matrix_local
        native = Matrix(expected["world"])
        require(all(math.isfinite(value) for owner in (matrix, native) for row in owner for value in row)
                and all(owner.to_3x3().col[index].length > 1.e-12
                        for owner in (matrix, native) for index in range(3)), "Nonfinite or degenerate retained Rest matrix")
        head_error = max(head_error, (matrix.translation * imported_meters - native.translation * meters).length)
        axis_error = max(axis_error, max((matrix.to_3x3().col[index].normalized()
                                         - native.to_3x3().col[index].normalized()).length for index in range(3)))
    physical_guard = min(COORDINATE_GUARD, COORDINATE_GUARD * meters)
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
    check(report, qa, "native_static_fbx_roundtrip", True,
          vertices=len(mesh.data.vertices), faces=len(mesh.data.polygons), retained_bones=len(rest_expected),
          coordinates_max_error_m=coordinate_error, shape_key_errors_m=key_errors,
          coordinates_guard_m=physical_guard, coordinates_max_error_source_world=coordinate_error / meters,
          weights_max_error=weights, rest_head_max_error_m=head_error, rest_axis_max_error=axis_error,
          weight_scope="Exact named positive weights on retained deform bones; FBX does not encode generic Blender mask groups",
          imported_objects=sorted(expected_names), imported_new_actions=0,
          original_fbx_tail_lengths_and_use_connect="Not encoded/accepted as Blender author metadata by this check")


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
    # Retain original Action assets through the disposable snapshot/worker.
    for index, action in enumerate(protection.action_refs):
        bpy.context.scene[f"CD_QA_ExportAuthorAction_{index:04d}"] = action
    qa.save_candidate(args.output / "scenes/Cosha_Dress_QA_export_snapshot.blend", args.input)
    job = {"stage": str(args.output / "stage"), "filename": FILENAME, "rig": rig_name,
           "objects": [rig_name, source_name], "unit_scale": bpy.context.scene.unit_settings.scale_length,
           "owned_keys": {source_name: owned_keys}, "dress_surfaces": proof, "warnings": []}
    result = observe_export(job, source, rig, cloth, record, report, qa, surface, worker)
    require(result.get("ok") is True, "The native model worker did not finish")
    exporter._dress_publication(job, result)  # Facts validation only; no publication.
    report["worker_result"] = result
    generated = static_mesh(bpy.data.objects[source_name])
    retained = bpy.data.objects[rig_name]
    deform_names = {bone.name for bone in retained.data.bones if bone.use_deform}
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
    report["fbx"] = {"path": str(filepath), "sha256": sha(filepath), "bytes": filepath.stat().st_size}
    roundtrip(filepath, generated, rest, float(job["unit_scale"]), [rig_name, source_name], report, qa)


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
