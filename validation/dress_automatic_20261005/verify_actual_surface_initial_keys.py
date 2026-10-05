"""Initial Shape Keys regression in one disposable factory/background child.

The real saved artist is opened read-only, then saved to a uniquely owned QA
path before Controls, generated physics or synthetic Shape Key operations.
The asymmetric QA Key exists BEFORE explicit actual-surface installation.
No live artist, Unity, forward Cloth replay, export bake or preferences save.
Only exact Key inventories are checked; this harness never purges Key IDs.
"""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy


HERE = Path(__file__).resolve().parent
REPOSITORY = Path(r"D:\MyRepository\Blender-addons-by-Randy")
PROJECT = Path(r"D:\Blender\Projects\Character\X")
BACKEND = "ACTUAL_SURFACE_DELTA_V1"
QA_KEY_NAME = "QA Initial Actual Asymmetric"
DEPENDENCIES = {
    "validate_real_dress.py": "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046",
    "diagnose_skin_transfer.py": "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_argument(value):
    value = value.casefold()
    require(len(value) == 64 and all(letter in "0123456789abcdef" for letter in value),
            "Use the full explicitly frozen source SHA256")
    return value


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT / "X.blend")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", help="Exact registered Dress source; no naming heuristic")
    parser.add_argument("--expected-surface-sha", required=True)
    parser.add_argument("--expected-worker-sha", required=True)
    parser.add_argument("--body-vertex-limit", type=int, default=100000)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.input, args.output = args.input.resolve(), args.output.resolve()
    args.expected_surface_sha = hash_argument(args.expected_surface_sha)
    args.expected_worker_sha = hash_argument(args.expected_worker_sha)
    require(args.input.is_file() and args.input.suffix.casefold() == ".blend", "Use the existing saved input blend")
    require(args.output.is_relative_to(HERE) and args.output != HERE and not args.input.is_relative_to(args.output),
            "Use an independent new Validation child")
    require(1000 <= args.body_vertex_limit <= 100000, "Declared Body vertex budget is out of range")
    for relative in ("result/initial_keys.json", "scenes/Cosha_Dress_QA_initial_copy.blend",
                     "scenes/Cosha_Dress_QA_initial_keys_before_install.blend",
                     "scenes/Cosha_Dress_QA_initial_keys_installed.blend"):
        require(not (args.output / relative).exists(), "Refusing to overwrite an existing QA artifact: " + relative)
    return args


def modules(args):
    for name, expected in DEPENDENCIES.items():
        require(sha(HERE / name) == expected, "Frozen QA dependency changed: " + name)
    # Explicit pins precede imports/registration: no old install gate silently
    # accepts a new worker or actual-surface implementation.
    for name, expected in (("skirt_surface.py", args.expected_surface_sha),
                           ("unity_export_worker.py", args.expected_worker_sha)):
        require(sha(REPOSITORY / "addons/character_designer" / name) == expected,
                "Canonical runtime differs from the explicit frozen SHA: " + name)
    sys.path[:0] = [str(HERE), str(REPOSITORY / "addons")]
    import validate_real_dress as qa
    import diagnose_skin_transfer as diag
    import character_designer as addon
    from character_designer import skirt_surface as surface
    require(Path(addon.__file__).resolve().is_relative_to(REPOSITORY / "addons") and surface.BACKEND == BACKEND,
            "Canonical import/backend proof failed")
    return qa, diag, addon, surface


def check(report, qa, name, condition, **evidence):
    qa.report_check(report, name, condition, **evidence)
    require(condition, "Initial Keys regression failed: " + name)


def context_content():
    context = bpy.context
    active = context.view_layer.objects.active
    return {"frame": context.scene.frame_current, "subframe": context.scene.frame_subframe,
            "active": active.name if active else None, "mode": active.mode if active else "OBJECT",
            "selected": sorted(obj.name for obj in context.view_layer.objects if obj.select_get())}


def key_inventory():
    keys = list(bpy.data.shape_keys)
    users = bpy.data.user_map(subset=set(keys)) if keys else {}
    return {key.name: {"pointer": key.as_pointer(), "users": key.users, "fake_user": key.use_fake_user,
                      "owners": sorted((item.bl_rna.identifier, item.name_full) for item in users.get(key, set()))}
            for key in keys}


def key_signatures(qa):
    """Every native Key block coordinate/value is read; JSON carries hashes."""
    return {keys.name: {"relative": keys.use_relative, "reference": keys.reference_key.name,
             "eval_time": float(keys.eval_time),
             "blocks": [{"name": key.name, "value": float(key.value), "relative_key": key.relative_key.name,
                         "mute": key.mute, "slider_min": key.slider_min, "slider_max": key.slider_max,
                         "vertex_group": key.vertex_group, "interpolation": key.interpolation, "frame": key.frame,
                         "point_count": len(key.data),
                         "coordinates_sha256": qa.digest([tuple(point.co) for point in key.data])}
                        for key in keys.key_blocks]} for keys in bpy.data.shape_keys}


def exact_key_ids(before, after, pointers=True):
    if set(before) != set(after):
        return False
    fields = ("pointer", "users", "fake_user", "owners") if pointers else ("users", "fake_user", "owners")
    return all(all(before[name][field] == after[name][field] for field in fields) for name in before)


def complete_rings(rings, count):
    require(isinstance(rings, list) and len(rings) > 6
            and all(isinstance(row, list) and row for row in rings), "Explicit saved fit rings are missing")
    indices = [index for row in rings for index in row]
    require(all(type(index) is int and 0 <= index < count for index in indices)
            and len(indices) == count and sorted(indices) == list(range(count)), "Saved rings do not exactly partition raw vertices")
    return rings


def original_key_subset(before, after):
    """The new QA block is the sole allowed extension; original blocks exact."""
    for name, value in before.items():
        current = after.get(name)
        if current is None:
            return False
        if any(current[key] != value[key] for key in ("relative", "reference", "eval_time")):
            return False
        blocks = {item["name"]: item for item in current["blocks"]}
        if any(blocks.get(item["name"]) != item for item in value["blocks"]):
            return False
    return True


def protection_with_known_removal(protection, removed_proxy=None):
    proof = protection.verify()
    expected = [] if removed_proxy is None else [("mesh", removed_proxy)]
    proof["expected_owned_endpoint_removal"] = expected
    proof["success"] = proof["missing"] == expected and not any(proof["changed"].values())
    return proof


def artist_subset_proof(protection, source, original_raw, original_keys, qa, removed_proxy=None):
    proof = protection.verify()
    expected_missing = [] if removed_proxy is None else [("mesh", removed_proxy)]
    current_raw = qa.raw_mesh_content(source)
    source_structure_exact = {key: value for key, value in current_raw.items() if key != "keys"} == {
        key: value for key, value in original_raw.items() if key != "keys"}
    preserved_keys = original_key_subset(original_keys, key_signatures(qa))
    expected_changed = [] if current_raw == original_raw else [source.name]
    proof["source_original_geometry_topology_weights_materials_exact"] = source_structure_exact
    proof["original_key_blocks_coordinates_values_exact"] = preserved_keys
    proof["expected_source_QA_key_extension"] = expected_changed
    proof["expected_owned_endpoint_removal"] = expected_missing
    proof["success"] = (proof["missing"] == expected_missing and source_structure_exact and preserved_keys
                         and proof["changed"]["meshes"] == expected_changed
                         and not any(value for key, value in proof["changed"].items() if key != "meshes"))
    return proof


def body_snapshot(body, qa):
    graph = bpy.context.evaluated_depsgraph_get()
    mesh = qa.world_mesh(body, graph)
    require(qa.finite(mesh["points"]), "Registered Body has nonfinite geometry")
    return mesh


def body_error(before, after, meters):
    require(len(before["points"]) == len(after["points"]) and before["edges"] == after["edges"],
            "Registered Body evaluated layout changed")
    return max(((a-b).length * meters for a, b in zip(before["points"], after["points"])), default=0.)


def installed_proof(source, qa, surface, expected_keys, expected_signatures, pointers=True):
    record, rig, actual, cloth = qa.physics.validate_physics(source)
    require(record["physics"]["backend"] == BACKEND, "Explicit actual backend is absent")
    native = record["physics"]["surface"]
    neutral = bpy.data.objects[native["roles"]["NEUTRAL_SURFACE"][0]]
    require(actual.data.shape_keys is None and neutral.data.shape_keys is None,
            "Physical C or fixed Basis H0 retained copied Keys")
    require(len(actual.data.vertices) == len(neutral.data.vertices) == len(source.data.vertices) == 800,
            "The Cosha exact-index800 surface layout changed")
    surface.validate(source, rig, record)
    after = key_inventory()
    require(exact_key_ids(expected_keys, after, pointers=pointers),
            "Exact Key inventory/owners changed; unexpected copied Key IDs are not purged")
    require(key_signatures(qa) == expected_signatures, "Initial source/original Key coordinates, values or metadata changed")
    return record, rig, actual, cloth, neutral, after


def run(args, report, qa, surface, artist_protection):
    source, rig, record = qa.owned_source(args.source)
    require(qa.physics.backend(record) == qa.physics.LEGACY_BACKEND,
            "Use artist Dress controls/legacy physics before actual-surface installation")
    initial_proxy = record.get("physics", {}).get("proxy") if record.get("physics") else None
    report["initial_saved_physics_present"] = bool(record.get("physics"))
    gate = qa.saved_cache_preflight(source, record)
    report["saved_cache_preflight"] = gate
    require(gate["allowed"], gate.get("reason", "Saved cache is unsafe to release"))
    report["artist_key_inventory"] = key_inventory()
    for index, action in enumerate(artist_protection.action_refs):
        bpy.context.scene[f"CD_QA_AuthorAction_{index:04d}"] = action
    qa.save_candidate(args.output / "scenes/Cosha_Dress_QA_initial_copy.blend", args.input)
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    qa.skirt._activate(bpy.context, rig, "POSE")
    owner = rig.get(qa.skirt.ORIGINAL_DISPLAY_OWNER_KEY)
    if qa.original.active(rig) or owner:
        if isinstance(owner, bpy.types.Object) and owner.type == "ARMATURE" and qa.original.active(owner):
            qa.skirt._activate(bpy.context, owner, "POSE")
        qa.public_switch(bpy.ops.character_designer.body_original_mode, action="CONTROLS")
        qa.skirt._activate(bpy.context, rig, "POSE")
    qa.skirt._require_controls_for_setup(source)
    check(report, qa, "public_controls_preserved_original_raw_rest_actions", artist_protection.verify()["success"],
          details=artist_protection.verify())
    body, body_status = qa.registered_body(bpy.context, rig, args)
    require(body is not None and body_status["measured"], "The exact registered Body is unavailable")
    report["registered_body"] = body_status
    original_raw, original_keys = qa.raw_mesh_content(source), key_signatures(qa)
    if not record.get("physics"):
        qa.physics.add_physics(bpy.context, source)
        check(report, qa, "QA_legacy_setup_preserved_original_assets", artist_protection.verify()["success"],
              details=artist_protection.verify())
    record, rig, old_proxy, old_cloth = qa.physics.validate_physics(source)
    require(qa.physics.backend(record) == qa.physics.LEGACY_BACKEND and not old_cloth.point_cache.is_baked,
            "The old unbaked owned endpoint is not proved")
    report["old_owned_proxy"] = {"name": old_proxy.name, "data": old_proxy.data.name,
                                 "raw_sha256": qa.digest(qa.raw_mesh_content(old_proxy)),
                                 "present_in_artist": initial_proxy == old_proxy.name}
    require(source.data.users == 1 and not source.show_only_shape_key, "Use the unshared ordinary source Shape Key input")
    keys = source.data.shape_keys
    require(keys is None or keys.use_relative, "Absolute original Shape Keys are preserved without guessing a conversion")
    require(keys is None or QA_KEY_NAME not in keys.key_blocks, "The QA Key name already belongs to an original asset")
    initial_active = source.active_shape_key_index
    before_QA_ids = key_inventory()
    if keys is None:
        source.shape_key_add(name="Basis", from_mix=False)
    basis = source.data.shape_keys.reference_key
    rings = complete_rings(record["fit"]["rings"], len(source.data.vertices))
    selected = [index for index in rings[6] if basis.data[index].co.x > 0.]
    require(0 < len(selected) < len(rings[6]), "The explicit partial-ring asymmetric QA region is unavailable")
    key = source.shape_key_add(name=QA_KEY_NAME, from_mix=False)
    # Explicit Basis copy avoids from_mix=False depending on an artist's active Key.
    for destination, origin in zip(key.data, basis.data):
        destination.co = origin.co
    for index in selected:
        key.data[index].co.z += .008
    key.relative_key, key.value = basis, .375
    source.active_shape_key_index = initial_active
    source.data.update(); bpy.context.view_layer.update()
    before_keys, signatures = key_inventory(), key_signatures(qa)
    created_QA_ids = {name: value for name, value in before_keys.items() if name not in before_QA_ids}
    require(len(created_QA_ids) == (0 if keys is not None else 1), "QA creation changed unexpected Key IDs")
    check(report, qa, "initial_asymmetric_key_exists_before_actual_install", key.name == QA_KEY_NAME
          and key.value == .375 and original_key_subset(original_keys, signatures),
          source_key_id=source.data.shape_keys.name, synthetic_key=QA_KEY_NAME, value=.375,
          local_Z_delta=.008, raw_indices=selected, created_QA_key_IDs=created_QA_ids)
    subset = artist_subset_proof(artist_protection, source, original_raw, original_keys, qa)
    check(report, qa, "QA_key_extension_preserves_all_original_assets", subset["success"], details=subset)
    qa_protection = qa.Protection()
    report["expected_key_inventory_before_install"] = before_keys
    report["expected_key_signatures_before_install"] = signatures
    report["source"] = source.name
    report["rig"] = rig.name
    report["owner"] = record["owner"]
    report["QA_input_declared"] = {"key": QA_KEY_NAME, "value": .375, "retained_in_QA_artifacts": True,
        "purpose": "Initial nonzero Shape Key must survive actual installation and native save/reopen"}
    qa.save_candidate(args.output / "scenes/Cosha_Dress_QA_initial_keys_before_install.blend", args.input)
    before_context, channels = context_content(), qa.pose_channels(rig)
    source_data_pointer = source.data.as_pointer()
    before_body = body_snapshot(body, qa)
    started = time.perf_counter()
    qa.physics.add_physics(bpy.context, source, backend=BACKEND, body=body)
    report["actual_install_seconds"] = time.perf_counter() - started
    report["replacement_committed"] = True
    record, rig, actual, cloth, neutral, after_keys = installed_proof(source, qa, surface, before_keys, signatures)
    report["key_inventory_after_install"] = after_keys
    check(report, qa, "actual_C_H0_no_Keys_exact_source_key_inventory", True,
          C=actual.name, H0=neutral.name, C_keys=None, H0_keys=None, raw_count=800,
          original_key_ID_count=len(before_QA_ids), declared_QA_key_ID_count=len(created_QA_ids), final_key_ID_count=len(after_keys))
    check(report, qa, "source_data_context_channels_preserved", source.data.as_pointer() == source_data_pointer
          and context_content() == before_context and qa.pose_channels(rig) == channels)
    error = body_error(before_body, body_snapshot(body, qa), bpy.context.scene.unit_settings.scale_length)
    check(report, qa, "registered_Body_geometry_unchanged", error <= min(5.e-6, 5.e-6 * bpy.context.scene.unit_settings.scale_length),
          maximum_native_evaluated_delta_m=error, body=body.name,
          scope="Complete evaluated Body at this saved frame; no forward Cloth replay or volume sign")
    removed = report["old_owned_proxy"]["name"]
    subset = artist_subset_proof(artist_protection, source, original_raw, original_keys, qa,
                                removed if report["old_owned_proxy"]["present_in_artist"] else None)
    check(report, qa, "installed_original_raw_rest_weights_Body_actions_preserved", subset["success"], details=subset)
    proof = protection_with_known_removal(qa_protection, removed)
    check(report, qa, "initial_QA_Keys_and_pre_upgrade_assets_exact", proof["success"], details=proof)
    destination = args.output / "scenes/Cosha_Dress_QA_initial_keys_installed.blend"
    qa.save_candidate(destination, args.input)
    report["installed_candidate"] = {"path": str(destination), **qa.file_state(destination)}
    result = bpy.ops.wm.open_mainfile(filepath=str(destination), load_ui=False, use_scripts=False)
    require("FINISHED" in result and Path(bpy.data.filepath).resolve() == destination.resolve(), "Native installed QA reopen failed")
    source, rig, record = qa.owned_source(report["source"])
    require(rig.name == report["rig"] and record["owner"] == report["owner"], "Reopened source/rig/owner changed")
    record, rig, actual, cloth, neutral, reopened = installed_proof(source, qa, surface, before_keys, signatures, pointers=False)
    report["key_inventory_after_reopen"] = reopened
    proof = protection_with_known_removal(qa_protection, removed)
    check(report, qa, "native_save_reopen_initial_Keys_and_all_assets_exact", proof["success"], details=proof,
          pointer_policy="Runtime pointers are re-created on open; native names/users/owners/content remain exact")
    body, status = qa.registered_body(bpy.context, rig, args)
    require(body is not None and status["measured"], "Reopened registered Body is unavailable")
    error = body_error(before_body, body_snapshot(body, qa), bpy.context.scene.unit_settings.scale_length)
    check(report, qa, "native_save_reopen_registered_Body_unchanged", error <= min(5.e-6, 5.e-6 * bpy.context.scene.unit_settings.scale_length),
          maximum_evaluated_delta_m=error)
    report["success"] = all(item["passed"] for item in report["checks"])


def main(args):
    isolation = {"background": bool(bpy.app.background), "factory_startup": "--factory-startup" in sys.argv,
                 "initial_filepath": bpy.data.filepath}
    require(isolation["background"] and isolation["factory_startup"] and not isolation["initial_filepath"],
            "Refusing initial Keys QA outside an empty factory background child")
    qa, diag, addon, surface = modules(args)
    report = {"success": False, "purpose": "Initial Shape Keys actual installation/native save regression",
        "production_effect_accepted": False, "artist_saved_by_verifier": False, "artist_path": str(args.input),
        "artist_before": qa.file_state(args.input), "isolated_process": isolation, "checks": [],
        "blender_version": bpy.app.version_string, "addon_version": list(addon.bl_info["version"]),
        "expected_surface_sha256": args.expected_surface_sha, "expected_worker_sha256": args.expected_worker_sha,
        "source_manifest_before": diag.source_manifest(), "harness_sha256": sha(Path(__file__)),
        "explicit_forward_replay": False, "worker_bake_exercised": False,
        "limits": ["Saved artist only; no live unsaved UI/Unity inspection, deployment or preferences save",
                   "QA asymmetric Key is intentionally retained only in independent QA artifacts",
                   "Native loading/binding can evaluate cold Cloth; no zero-evaluation claim",
                   "No simulation clearance, equilibrium, manual/key authoring exhaustiveness, export/FBX/Unity acceptance",
                   "Only exact inventories checked; no global purge or unknown Key removal"]}
    began = time.perf_counter()
    protection = None
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        addon.register()
        result = bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
        require("FINISHED" in result and Path(bpy.data.filepath).resolve() == args.input, "Native saved artist open failed")
        protection = qa.Protection()
        report["protected_artist_inventory"] = protection.summary()
        run(args, report, qa, surface, protection)
    except Exception as error:
        report["success"] = False
        report["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        try:
            report["failure_key_inventory"] = key_inventory()
        except Exception as inventory_error:
            report["failure_key_inventory_error"] = str(inventory_error)
    finally:
        if protection is not None:
            try:
                native = bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
                require("FINISHED" in native, "Readonly artist cleanup reload failed")
                report["final_artist_asset_protection"] = protection.verify()
                report["success"] = report["success"] and report["final_artist_asset_protection"]["success"]
            except Exception as error:
                report["success"] = False
                report["final_reload_error"] = str(error)
        report["artist_after"] = qa.file_state(args.input)
        report["artist_disk_exact"] = report["artist_after"] == report["artist_before"]
        report["source_manifest_after"] = diag.source_manifest()
        report["code_exact_during_run"] = (report["source_manifest_after"] == report["source_manifest_before"]
                                           and sha(Path(__file__)) == report["harness_sha256"])
        report["success"] = report["success"] and report["artist_disk_exact"] and report["code_exact_during_run"]
        report["elapsed_seconds"] = time.perf_counter() - began
        destination = args.output / "result/initial_keys.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(diag.json_content(report), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"success": report["success"], "report": str(destination), "elapsed_seconds": report["elapsed_seconds"]}), flush=True)
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
