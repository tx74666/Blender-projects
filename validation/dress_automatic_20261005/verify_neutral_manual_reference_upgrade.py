"""Private native upgrade mechanics; preparation alone is not a native PASS.

Use a root-owned empty factory/background Blender 5.1 child. This keeps the
legacy fixture's existing author Actions, advances its private cache 1..60,
checks explicit upgrade rollback/no-op, and saves/reopens only a unique copy.
No synthetic action, render, collision or public Original acceptance is claimed.
The soft limit is checked between native calls; the parent must own a hard lease.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy

HERE = Path(__file__).resolve().parent
REPOSITORY = Path(r"D:\MyRepository\Blender-addons-by-Randy")
ARTIST = Path(r"D:\Blender\Projects\Character\X\X.blend")
INPUT = HERE / "actual_install_51_20261006_031045_111/scenes/Cosha_Dress_QA_surface_install.blend"
INSTALL = INPUT.parent.parent / "result/workflow_install.json"
TEST = REPOSITORY / "tests/test_skirt_neutral_manual_reference.py"
SURFACE_SHA = "9d7a928e27464e772330304d03e9ca81462f800951b3172921c87429cf78891c"
WORKER_SHA = "069fb0f21b02e36a23dd02b1978d2a917c2873f290fc3331cdf0d55e877ce5bc"
PINS = {
    INPUT: "7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f",
    INSTALL: "a2157ba399bfe32cc28401847c2556f776761fd607eaa3ba7ea23b61aaec6a32",
    ARTIST: "2b36fb936082cbe7a81dd29e1dba22b9f9fbefa935015bfb29cc37b5b496ca9a",
    HERE / "verify_actual_surface_workflow.py": "2e8d82bbbde00604bf3f62bc17cbcb31244ed87290e083ebb17b25f4b9216140",
    REPOSITORY / "addons/character_designer/skirt_surface.py": SURFACE_SHA,
    REPOSITORY / "addons/character_designer/unity_export_worker.py": WORKER_SHA,
    TEST: "39c29d7ea496b5bb94735ba6e5c46a40201a1c15f310d08f9d6f3a0985b57411",
}


def require(condition, message):
    if not condition:
        raise RuntimeError("Neutral FK upgrade QA: " + message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, name):
    require(name not in sys.modules, "diagnostic module already loaded")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identities(record):
    return {name: {"object": obj.as_pointer(), "data": obj.data.as_pointer(), "role": role}
            for role, names in record["physics"]["surface"]["roles"].items()
            for name in names for obj in (bpy.data.objects[name],)}


def author_bindings(surface):
    result = {}
    for kind in ("objects", "shape_keys"):
        for owner in getattr(bpy.data, kind):
            animation = owner.animation_data
            result[kind + "/" + owner.name] = None if animation is None else {
                "rna": surface._rna(animation),
                "slot": getattr(getattr(animation, "action_slot", None), "identifier", None),
                "tracks": [{"rna": surface._rna(track), "strips": [surface._rna(strip) for strip in track.strips]}
                           for track in animation.nla_tracks]}
    return result


def sample(source, actual, neutral, diag):
    graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for label, obj in (("H0", neutral), ("O", source), ("C", actual)):
        mesh = diag.json_content(diag.mesh_snapshot(obj, graph))
        require(mesh["points"] and all(math.isfinite(x) for point in mesh["points"] for x in point), "nonfinite readback")
        result[label] = {"points": mesh["points"], "structure": {key: mesh[key] for key in ("faces", "edges", "weights")},
                         "native_triangles": mesh["triangles"], "points_sha256": sha_values(mesh["points"])}
    require([len(result[key]["points"]) for key in ("H0", "O", "C")] == [800, 3040, 800], "native layout changed")
    return result


def sha_values(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def cache_semantics(cloth, qa, surface):
    native = qa.cache_state(cloth)
    native.pop("pointer")
    return {"native": native, "filepath": cloth.point_cache.filepath,
            "library_path": cloth.point_cache.use_library_path,
            "settings": surface._rna(cloth.settings), "collision": surface._rna(cloth.collision_settings),
            "effectors": surface._rna(cloth.settings.effector_weights)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--soft-seconds", type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    args.output = args.output.resolve()
    require(args.output.is_relative_to(HERE) and args.output != HERE and not args.output.exists(), "use a fresh unique Validation child")
    require(0. < args.soft_seconds <= 180. and math.isfinite(args.soft_seconds), "soft limit exceeds the parent lease")
    require(bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath
            and bpy.app.version[:2] == (5, 1), "use empty factory/background Blender 5.1")
    pins_before = {str(path): sha(path) for path in PINS}
    require(all(pins_before[str(path)] == expected for path, expected in PINS.items()), "fixed input/source/artist hash changed")
    own_sha = sha(Path(__file__))
    workflow = load(HERE / "verify_actual_surface_workflow.py", "neutral_upgrade_frozen_workflow")
    prepared = load(TEST, "neutral_upgrade_prepared_native_tests")
    qa, diag, addon, surface = workflow.load_dependencies()
    require(Path(surface.__file__).resolve() == REPOSITORY / "addons/character_designer/skirt_surface.py", "wrong runtime module")
    source_manifest = diag.source_manifest()
    disks = {str(path): qa.file_state(path) for path in (INPUT, INSTALL, ARTIST)}
    report = {"success": False, "checks": [], "production_effect_accepted": False, "public_original_nojump_proved": False,
              "artist_saved_by_verifier": False, "prepared_script_sha256": own_sha, "pins_before": pins_before,
              "source_manifest_before": source_manifest, "disk_before": disks, "geometry_guard_m": 5e-5,
              "scope": "Explicit neutral-reference migration mechanics at the existing author pose; no new/removed author Action or Rest edit",
              "soft_limit_seconds": args.soft_seconds, "parent_hard_lease_required": True,
              "geometry_guard_calls": [], "phases": []}
    started = time.perf_counter()
    protection = None
    completed = False
    args.output.mkdir()

    def phase(name):
        elapsed = time.perf_counter()-started
        report["phases"].append({"name": name, "elapsed_seconds": elapsed})
        print(json.dumps({"neutral_upgrade_phase": name, "elapsed_seconds": elapsed}), flush=True)
        require(elapsed < args.soft_seconds, "soft budget exhausted before " + name)

    def check(name, value, **facts):
        qa.report_check(report, name, value, **facts)
        require(value, name)

    try:
        gate_args = argparse.Namespace(input=INPUT.resolve(), install_report=INSTALL.resolve(),
                                       expected_surface_sha=SURFACE_SHA, expected_worker_sha=WORKER_SHA)
        source_name = workflow.motion_input_gate(gate_args, report, qa, diag)
        addon.register()
        require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(INPUT), load_ui=False, use_scripts=False), "open exact old input")
        protection = qa.Protection()
        source, rig, record = qa.owned_source(source_name)
        record, rig, actual, cloth, neutral = workflow.motion_objects(source, qa, surface)
        reference = surface._object(record, "NEUTRAL_RIG", source)
        check("legacy_marker_absent", "neutral_manual" not in record["physics"]["surface"]
              and surface.NEUTRAL_MANUAL_KEY not in reference)
        saved_cache = qa.saved_cache_preflight(source, record)
        check("actual_old_input_is_unsealed_ram", saved_cache["allowed"] and cloth.point_cache.is_baked is False
              and record["physics"].get("baked_range") is None, saved_cache=saved_cache,
              explanation="A saved installation blend is not a sealed simulation: native is_baked False and absent baked_range are checked after actual reopen")
        original_inventory, owner_ids = workflow.inventory(), identities(record)
        bindings = author_bindings(surface)
        reject_raw, reject_contract = source[qa.skirt.RECORD_KEY], surface._helper_contract(reference)
        reject_inputs = surface._upgrade_inputs(bpy.context, source, rig, record, cloth)
        reject_cache = workflow.cache_content(cloth, qa, surface)
        phase("before_unsealed_rejection")
        try:
            surface.upgrade_neutral_manual(bpy.context, source)
        except surface.SkirtSurfaceError as error:
            check("unsealed_API_refused_by_seal_gate", "cannot be rolled back" in str(error), error=str(error))
        else:
            raise RuntimeError("Unsealed legacy reference was unexpectedly upgraded")
        check("unsealed_rejection_exact_no_mutation", source[qa.skirt.RECORD_KEY] == reject_raw
              and surface._helper_contract(reference) == reject_contract
              and surface._upgrade_inputs(bpy.context, source, rig, record, cloth) == reject_inputs
              and workflow.cache_content(cloth, qa, surface) == reject_cache
              and workflow.inventory() == original_inventory and identities(record) == owner_ids
              and author_bindings(surface) == bindings
              and protection.verify()["success"])
        phase("private_cache_setup")
        candidate = args.output / "scenes/Cosha_Dress_QA_neutral_fk.blend"
        qa.save_candidate(candidate, INPUT)
        scene = bpy.context.scene
        # Keep even currently unused author Actions reachable in this private
        # saved Scene, without changing their bindings, curves or fake-user flag.
        for index, action in enumerate(bpy.data.actions):
            key = "CD_QA_NeutralReferenceAction_" + str(index)
            require(key not in scene, "private author Action retention key already exists")
            scene[key] = action
        scene.frame_start, scene.frame_end = 1, 60
        cloth.point_cache.frame_start, cloth.point_cache.frame_end, cloth.point_cache.frame_step = 1, 60, 1
        settings = bpy.context.window_manager.character_designer_skirt
        settings.source, settings.use_scene_range = source, True
        cache_dir = args.output / "native_cache"
        cache_dir.mkdir()
        cloth.point_cache.filepath, cloth.point_cache.use_library_path = str(cache_dir), False
        cloth.point_cache.use_disk_cache = True
        qa.save_candidate(candidate, INPUT)
        qa.public_switch(bpy.ops.character_designer.dress_motion_reset)
        check("public_Reset_private_unsealed", scene.frame_current == 1 and not cloth.point_cache.is_baked)
        for frame in range(1, 61):
            require(time.perf_counter()-started < args.soft_seconds, "forward60 exceeded soft limit")
            scene.frame_set(frame)
            points = surface._points(actual, bpy.context)
            require(len(points) == 800, "forward native Cloth changed count")
        phase("before_public_Bake_1_60")
        native_bake = bpy.ops.character_designer.skirt_bake_physics("EXEC_DEFAULT")
        from character_designer import skirt as skirt_ui
        record = qa.skirt.read_record(source)
        check("public_Bake_sealed_private_1_60", "FINISHED" in native_bake and cloth.point_cache.is_baked
              and record["physics"].get("baked_range") == [1, 60] and not skirt_ui._ACTIVE_BAKES,
              result=sorted(native_bake), cache=qa.cache_state(cloth))
        phase("before_postcommit_rollback_real_upgrade_noop")
        before = sample(source, actual, neutral, diag)
        cache_before = cache_semantics(cloth, qa, surface)
        original_guard = surface._reference_upgrade_errors

        def observed_guard(*values):
            result = original_guard(*values)
            report["geometry_guard_calls"].append({"sequence": len(report["geometry_guard_calls"])+1, "maximum_error_m": result})
            return result

        surface._reference_upgrade_errors = observed_guard
        try:
            report["prepared_native_tests"] = prepared.native_upgrade_checks(bpy.context, source)
        finally:
            surface._reference_upgrade_errors = original_guard
        after = sample(source, actual, neutral, diag)
        check("four_actual_candidate_and_commit_guards", len(report["geometry_guard_calls"]) == 4)
        check("upgrade_structure_and_original_owner_IDs_exact", all(before[key]["structure"] == after[key]["structure"] for key in before)
              and workflow.inventory() == original_inventory and identities(qa.skirt.read_record(source)) == owner_ids)
        check("sealed_cache_semantics_and_original_assets_exact", cache_semantics(cloth, qa, surface) == cache_before
              and author_bindings(surface) == bindings and protection.verify()["success"], protection=protection.verify(),
              action_binding_sha256=sha_values(bindings))
        report["native_geometry"] = {"before": before, "after": after}
        phase("before_private_save_reopen")
        saved_raw = source[qa.skirt.RECORD_KEY]
        saved_contract = surface._helper_contract(reference)
        qa.save_candidate(candidate, INPUT)
        require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(candidate), load_ui=False, use_scripts=False), "candidate reopen")
        source, rig, record = qa.owned_source(source_name)
        record, rig, actual, cloth, neutral = workflow.motion_objects(source, qa, surface)
        reference = surface._object(record, "NEUTRAL_RIG", source)
        reopened = sample(source, actual, neutral, diag)
        errors = surface._reference_upgrade_errors({key: after[key]["points"] for key in after},
                     {key: reopened[key]["points"] for key in reopened}, bpy.context.scene.unit_settings.scale_length)
        check("saved_rest_FK_marker_and_reference_contract_exact", source[qa.skirt.RECORD_KEY] == saved_raw
              and surface._helper_contract(reference) == saved_contract
              and surface._neutral_manual_record(record["physics"]["surface"]) == surface.NEUTRAL_MANUAL_FK)
        check("save_reopen_sealed_cache_keys_actions_rest_and_output", cloth.point_cache.is_baked
              and cache_semantics(cloth, qa, surface) == cache_before and protection.verify()["success"]
              and author_bindings(surface) == bindings
              and workflow.inventory() == original_inventory
              and all(after[key]["structure"] == reopened[key]["structure"] for key in after), maximum_error_m=errors,
              cache_scope="Native sealed flag/configuration and exact same-frame C; no whole-trajectory replay claim")
        files = sorted(path for path in args.output.rglob("*.bphys") if path.is_file())
        check("actual_cache_writes_are_unique_QA_local", bool(files) and all(path.resolve().is_relative_to(args.output) for path in files),
              files=[{"path": str(path), **qa.file_state(path)} for path in files])
        report["saved_candidate"] = {"path": str(candidate), **qa.file_state(candidate)}
        phase("upgrade_mechanics_complete")
        completed = True
    except Exception:
        report["error"] = traceback.format_exc()
    finally:
        try:
            require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(INPUT), load_ui=False, use_scripts=False), "exact input reload")
            report["final_input_protection"] = protection.verify() if protection is not None else None
            report["final_reload_complete"] = report["final_input_protection"] is not None and report["final_input_protection"]["success"]
        except Exception:
            report["final_reload_complete"] = False
            report["cleanup_error"] = traceback.format_exc()
        report["pins_after"] = {str(path): sha(path) for path in PINS}
        report["pins_and_script_exact"] = report["pins_after"] == pins_before and sha(Path(__file__)) == own_sha
        report["disk_after"] = {str(path): qa.file_state(path) for path in (INPUT, INSTALL, ARTIST)}
        report["input_install_artist_disk_exact"] = report["disk_after"] == disks
        report["source_manifest_after"] = diag.source_manifest()
        report["canonical_inventory_exact"] = report["source_manifest_after"] == source_manifest
        report["elapsed_seconds"] = time.perf_counter()-started
        report["success"] = (completed and report["final_reload_complete"] and report["pins_and_script_exact"]
                             and report["input_install_artist_disk_exact"] and report["canonical_inventory_exact"]
                             and "error" not in report
                             and all(row["passed"] for row in report["checks"]))
        destination = args.output / "result/neutral_manual_reference_upgrade.json"
        destination.parent.mkdir()
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"success": report["success"], "report": str(destination)}), flush=True)
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
