"""Serial, disposable real-model QA for the actual Dress surface backend.

First run --stage install in an empty --background --factory-startup child.
This stage performs no forward 60-frame replay. Native dependency-graph reads
and binding can nevertheless evaluate cold Cloth; this is not a zero-evaluation
claim. Only independently named QA blends and JSON under Validation are saved.

The motion stage requires an exact passing install artifact. Its synthetic
cases and sampled collision/render evidence are not production acceptance.
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
from array import array
from types import SimpleNamespace

import bpy
from mathutils import Matrix, Vector


HERE = Path(__file__).resolve().parent
REPOSITORY = Path(r"D:\MyRepository\Blender-addons-by-Randy")
PROJECT = Path(r"D:\Blender\Projects\Character\X")
BACKEND = "ACTUAL_SURFACE_DELTA_V1"
DEPENDENCIES = {
    "validate_real_dress.py": "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046",
    "diagnose_skin_transfer.py": "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28",
    "prototype_native_dress_overlay.py": "574c121fa2b7adf2892ceec032ab5629254b2f846818bdd677c6d94e2400c909",
}
CASES = ("walk", "run", "turn", "leg_raise", "squat", "abrupt_stop", "abrupt_stop_turn")
ROLE_NAMES = frozenset({"CLOTH_PROXY", "BODY_ATTACHMENT", "NEUTRAL_RIG",
                        "NEUTRAL_WIRE", "NEUTRAL_SURFACE", "TRACKER"})
NATIVE_WORLD_LIMIT = 5.e-6
NATIVE_METRES_LIMIT = 5.e-6


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("install", "motion"), default="install")
    parser.add_argument("--input", type=Path, default=PROJECT / "X.blend")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", help="Exact owned Dress source; no naming heuristic")
    parser.add_argument("--body-vertex-limit", type=int, default=100000)
    parser.add_argument("--install-report", type=Path)
    parser.add_argument("--expected-surface-sha")
    parser.add_argument("--expected-worker-sha")
    parser.add_argument("--cases", nargs="+", choices=CASES, default=["abrupt_stop"])
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--triangle-pair-limit", type=int, default=50000)
    parser.add_argument("--max-penetration-mm", type=float, default=2.0,
                        help="Existing bounded diagnostic limit from validate_real_dress.py; not whole-body/visual acceptance")
    parser.add_argument("--max-stop-jitter-mm", type=float, default=1.0,
                        help="Existing final hem last-ten-frame diagnostic limit; not long-run equilibrium acceptance")
    parser.add_argument("--max-edge-ratio", type=float, default=3.0,
                        help="Existing connectivity/stretch diagnostic limit; not an artistic quality threshold")
    parser.add_argument("--no-render", action="store_true", help="Numerical-only diagnostic; render coverage remains explicitly absent")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.input, args.output = args.input.resolve(), args.output.resolve()
    require(args.input.is_file() and args.input.suffix.casefold() == ".blend", "Use a saved input blend")
    require(args.output.is_relative_to(HERE) and args.output != HERE
            and not args.input.is_relative_to(args.output), "Use an independent child of this Validation directory")
    require(1000 <= args.body_vertex_limit <= 100000, "Body budget must be between 1000 and 100000 vertices")
    require(30 <= args.frames <= 120 and 1000 <= args.triangle_pair_limit <= 100000, "Motion budgets are out of range")
    require(len(args.cases) == len(set(args.cases)), "Repeated motion cases are refused")
    require(all(math.isfinite(value) and value > 0. for value in
                (args.max_penetration_mm, args.max_stop_jitter_mm, args.max_edge_ratio)), "Diagnostic limits must be finite and positive")
    if args.install_report is None:
        args.install_report = args.input.parent.parent / "result/workflow_install.json"
    args.install_report = args.install_report.resolve()
    relatives = ("result/workflow_install.json", "scenes/Cosha_Dress_QA_initial_copy.blend",
                 "scenes/Cosha_Dress_QA_surface_install.blend") if args.stage == "install" else (
                 "result/workflow_motion.json", "scenes/Cosha_Dress_QA_motion_clean.blend")
    for relative in relatives:
        require(not (args.output / relative).exists(), "Refusing to overwrite an existing QA artifact: " + relative)
    if args.stage == "motion":
        require(args.expected_surface_sha and len(args.expected_surface_sha) == 64
                and all(value in "0123456789abcdef" for value in args.expected_surface_sha.lower()),
                "Motion requires the explicit frozen runtime --expected-surface-sha")
        require(args.expected_worker_sha and len(args.expected_worker_sha) == 64
                and all(value in "0123456789abcdef" for value in args.expected_worker_sha.lower()),
                "Motion requires the explicit frozen runtime --expected-worker-sha")
        for case in args.cases:
            require(not (args.output / "cases" / case).exists(), "Motion case output already exists: " + case)
    return args


def load_dependencies():
    # This happens only after the empty factory/background gate in main().
    for name, expected in DEPENDENCIES.items():
        require(sha(HERE / name) == expected, "Frozen QA dependency changed: " + name)
    sys.path[:0] = [str(HERE), str(REPOSITORY / "addons")]
    import validate_real_dress as qa
    import diagnose_skin_transfer as diag
    import character_designer
    from character_designer import skirt_surface as surface
    require(Path(character_designer.__file__).resolve().is_relative_to(REPOSITORY / "addons"),
            "The QA child loaded an installed or shadow add-on instead of canonical sources")
    require(surface.BACKEND == BACKEND and surface.OBJECT_ROLES == ROLE_NAMES, "Surface ABI changed")
    return qa, diag, character_designer, surface


def inventory():
    return {name: sorted(item.name for item in getattr(bpy.data, name)) for name in
            ("objects", "meshes", "armatures", "curves", "collections", "node_groups", "actions", "shape_keys")}


def context_content(context):
    active = context.view_layer.objects.active
    return {"frame": context.scene.frame_current, "subframe": context.scene.frame_subframe,
            "active": active.name if active else None, "mode": active.mode if active else "OBJECT",
            "selected": sorted(obj.name for obj in context.view_layer.objects if obj.select_get())}


def graph_content(source, rig, qa, surface):
    # Complete writable modifier/constraint/driver RNA, plus actual channels.
    return {"record": source[qa.skirt.RECORD_KEY], "inventory": inventory(),
            "source_modifiers": [surface._rna(modifier) for modifier in source.modifiers],
            "constraints": {bone.name: [surface._rna(item) for item in bone.constraints]
                            for bone in rig.pose.bones},
            "drivers": surface._drivers(rig), "channels": qa.pose_channels(rig),
            "context": context_content(bpy.context)}


def checked(report, qa, name, condition, **evidence):
    qa.report_check(report, name, condition, **evidence)
    require(condition, "Installation gate failed: " + name)


def protected(protection, replaced_proxy=None):
    result = protection.verify()
    expected = [] if replaced_proxy is None else [("mesh", replaced_proxy)]
    # The installer intentionally destroys exactly the proven old generated
    # endpoint. Keep its original hash in the report rather than hiding it from
    # the original Protection inventory. No other absent/changed asset is allowed.
    result["expected_owned_endpoint_removal"] = expected
    result["success"] = (result["missing"] == expected and not any(result["changed"].values()))
    return result


def cache_content(cloth, qa, surface):
    return {"native": qa.cache_state(cloth), "settings": surface._rna(cloth.settings),
            "collision": surface._rna(cloth.collision_settings),
            "effector_weights": surface._rna(cloth.settings.effector_weights)}


def mode_content(source, rig, record, cloth, qa, surface):
    overlay = source.modifiers[record["physics"]["surface"]["overlay"]]
    holder, _identifier, _path = qa.skirt.physics_control(source)
    return {"record": source[qa.skirt.RECORD_KEY], "profile": source.get(qa.profiles.PROFILE_KEY),
            "influence": float(holder["physics_influence"]),
            "flags": [overlay.show_viewport, overlay.show_render],
            "cache": cache_content(cloth, qa, surface), "channels": qa.pose_channels(rig),
            "drivers": surface._drivers(rig), "context": context_content(bpy.context)}


def complete_raw_partition(rings, count):
    require(isinstance(rings, list) and rings and all(isinstance(ring, list) and ring for ring in rings),
            "Saved fit.rings are not an explicit complete partition")
    ids = [index for ring in rings for index in ring]
    require(all(type(index) is int and 0 <= index < count for index in ids), "Invalid raw ring index")
    require(len(ids) == count and sorted(ids) == list(range(count)), "Repeated or missing raw ring index")
    return list(rings[0])


def reject_saved_bake(source, rig, record, body, report, qa, surface):
    require(record.get("physics") and qa.physics.backend(record) == qa.physics.LEGACY_BACKEND,
            "The install gate needs the saved legacy graph, not an implicit reconstruction")
    before = graph_content(source, rig, qa, surface)
    proxy = bpy.data.objects[record["physics"]["proxy"]]
    cache_before = cache_content(proxy.modifiers[-1], qa, surface)
    pending = copy.deepcopy(record)
    pending["physics"]["baked_range"] = [1, 2]
    rejection = None
    try:
        qa.skirt.write_record(source, pending)
        try:
            qa.physics.add_physics(bpy.context, source, backend=BACKEND, body=body)
        except Exception as error:
            rejection = {"type": type(error).__name__, "message": str(error)}
        require(rejection is not None, "A declared sealed legacy cache was silently upgraded")
        require(source[qa.skirt.RECORD_KEY] == json.dumps(pending, ensure_ascii=False, separators=(",", ":")),
                "The rejected install changed its saved pending record")
    finally:
        source[qa.skirt.RECORD_KEY] = before["record"]
    after = graph_content(source, rig, qa, surface)
    checked(report, qa, "saved_bake_rejected_before_install", rejection is not None and after == before
            and cache_content(proxy.modifiers[-1], qa, surface) == cache_before,
            rejection=rejection, scope="Only the independent QA record's declared baked range was temporarily changed; no native bake was fabricated")
    qa.physics.validate_physics(source)


def installation_layout(source, rig, record, report, qa, surface):
    actual, cloth = surface.validate(source, rig, record)
    roles = record["physics"]["surface"]["roles"]
    count = len(source.data.vertices)
    require(count == 800, "This real-model fixture must have exactly 800 raw source vertices")
    pinned = complete_raw_partition(record["fit"]["rings"], count)
    tracker = bpy.data.objects[roles["TRACKER"][0]]
    expected_grid = record["physics"]["rows"] * record["physics"]["columns"]
    weights = record["physics"]["pin_weights"]
    checked(report, qa, "actual800_tracker416_index_and_pin_mapping",
            len(actual.data.vertices) == count and len(tracker.data.vertices) == expected_grid == 416
            and len(weights) == count and all(weights[index] == 1. for index in pinned),
            raw_source_vertices=count, cloth_vertices=len(actual.data.vertices),
            tracker_vertices=len(tracker.data.vertices), virtual_grid=[record["physics"]["rows"], record["physics"]["columns"]],
            ring0_raw_indices=pinned, role_counts={role: len(names) for role, names in roles.items()},
            pin_mapping="fit.rings contains every raw ID exactly once; production validate checks all saved/native pin weights")
    graph = bpy.context.evaluated_depsgraph_get()
    native = {"source": qa.world_mesh(source, graph), "cloth": qa.world_mesh(actual, graph)}
    neutral = bpy.data.objects[roles["NEUTRAL_SURFACE"][0]]
    native["neutral"] = qa.world_mesh(neutral, graph)
    checked(report, qa, "cold_native_surface_outputs_finite",
            all(qa.finite(mesh["points"]) for mesh in native.values())
            and len(native["cloth"]["points"]) == len(native["neutral"]["points"]) == count,
            evaluated_vertex_counts={key: len(value["points"]) for key, value in native.items()},
            explicit_forward_replay=False, caveat="Native cold Cloth may be evaluated by graph reads and binding")
    return actual, cloth


def reject_install_detached_key(source, rig, body, report, qa, surface):
    """A copied Key detached before helper completion must not escape rollback."""
    from character_designer import mesh_copy
    before_original = graph_content(source, rig, qa, surface)
    raw_original = qa.digest(qa.raw_mesh_content(source))
    original_key = source.data.shape_keys
    active_key, show_only = source.active_shape_key_index, source.show_only_shape_key
    before_ids = {name: sorted((item.name, item.as_pointer()) for item in getattr(bpy.data, name))
                  for name in ("objects", "meshes", "shape_keys", "actions")}
    seeded_key = None
    clear = mesh_copy.clear_copied_shape_keys
    observed, rejection = {}, None
    try:
        if original_key is None:
            source.shape_key_add(name="Basis", from_mix=False)
            asymmetric = source.shape_key_add(name="QA Install Rollback Asymmetric", from_mix=False)
            index = qa.skirt.read_record(source)["fit"]["rings"][-1][0]
            asymmetric.data[index].co.x += .001
            asymmetric.value = .37
            seeded_key = source.data.shape_keys
        before = graph_content(source, rig, qa, surface)
        raw_before = qa.digest(qa.raw_mesh_content(source))
        profile_before = source.get(qa.profiles.PROFILE_KEY)
        holder, _identifier, _path = qa.skirt.physics_control(source)
        influence_before = holder.get("physics_influence")
        influence_ui_before = holder.id_properties_ui("physics_influence").as_dict()
        keys = source.data.shape_keys
        key_pointer = keys.as_pointer()
        key_action = keys.animation_data.action if keys.animation_data else None
        key_channels = (keys.eval_time, [(block.name, block.value, block.mute) for block in keys.key_blocks])
        ids_before = {name: sorted((item.name, item.as_pointer()) for item in getattr(bpy.data, name))
                      for name in ("objects", "meshes", "shape_keys", "actions")}

        def fail_after_detach(original, duplicate):
            if original != source:
                return clear(original, duplicate)
            copied = duplicate.data.shape_keys
            observed.update(name=copied.name, pointer=copied.as_pointer(), users_before=copied.users)
            duplicate.shape_key_clear()
            remaining = bpy.data.shape_keys.get(observed["name"])
            observed.update(detached=duplicate.data.shape_keys is None,
                            retained_exact=remaining is not None and remaining.as_pointer() == observed["pointer"],
                            native_users=[] if remaining is None else sorted(item.name for item in
                                bpy.data.user_map(subset={remaining}).get(remaining, set())))
            raise RuntimeError("QA deliberate failure after copied Key detach")

        mesh_copy.clear_copied_shape_keys = fail_after_detach
        try:
            qa.physics.add_physics(bpy.context, source, backend=BACKEND, body=body, capability="BOTH")
        except Exception as error:
            rejection = {"type": type(error).__name__, "message": str(error)}
        finally:
            mesh_copy.clear_copied_shape_keys = clear
        ids_after = {name: sorted((item.name, item.as_pointer()) for item in getattr(bpy.data, name))
                     for name in ("objects", "meshes", "shape_keys", "actions")}
        checked(report, qa, "install_detached_copy_key_failure_restores_native_IDs",
                rejection is not None and "deliberate failure after copied Key detach" in rejection["message"]
                and observed.get("detached") is True and ids_after == ids_before
                and graph_content(source, rig, qa, surface) == before
                and qa.digest(qa.raw_mesh_content(source)) == raw_before
                and source.get(qa.profiles.PROFILE_KEY) == profile_before
                and holder.get("physics_influence") == influence_before
                and holder.id_properties_ui("physics_influence").as_dict() == influence_ui_before
                and source.data.shape_keys.as_pointer() == key_pointer
                and (keys.animation_data.action if keys.animation_data else None) == key_action
                and (keys.eval_time, [(block.name, block.value, block.mute) for block in keys.key_blocks]) == key_channels,
                rejection=rejection, copied_key_at_failure=observed,
                hook="Private saved QA only; native install/helper detach and transaction rollback executed")
    finally:
        mesh_copy.clear_copied_shape_keys = clear
        if seeded_key is not None:
            require(source.data.shape_keys == seeded_key, "The QA-only seeded Key owner changed; preserve it")
            source.shape_key_clear()
        source.active_shape_key_index, source.show_only_shape_key = active_key, show_only
    after_ids = {name: sorted((item.name, item.as_pointer()) for item in getattr(bpy.data, name))
                 for name in ("objects", "meshes", "shape_keys", "actions")}
    checked(report, qa, "install_copy_key_regression_restores_pre_QA_assets",
            after_ids == before_ids and graph_content(source, rig, qa, surface) == before_original
            and qa.digest(qa.raw_mesh_content(source)) == raw_original
            and source.data.shape_keys == original_key,
            seeded_asymmetric_key=seeded_key is not None)
    qa.physics.validate_physics(source)


def reject_install_profile_write(source, rig, body, report, qa, surface):
    """A real late install failure must precede removal of the old graph."""
    before = graph_content(source, rig, qa, surface)
    profile_before = source.get(qa.profiles.PROFILE_KEY)
    holder, _identifier, _path = qa.skirt.physics_control(source)
    influence_before = holder.get("physics_influence")
    influence_ui_before = holder.id_properties_ui("physics_influence").as_dict()
    write = qa.profiles.write
    rejection = None
    observed = {}

    def fail_after_profile_write(*args, **kwargs):
        write(*args, **kwargs)
        current = qa.skirt.read_record(source)
        overlay = source.modifiers[current["physics"]["surface"]["overlay"]]
        observed.update(capability=args[1]["capability"], mode=args[1]["mode"],
                        influence=holder.get("physics_influence"),
                        flags=[overlay.show_viewport, overlay.show_render])
        raise RuntimeError("QA deliberate failure after installation profile write")

    try:
        qa.profiles.write = fail_after_profile_write
        try:
            qa.physics.add_physics(bpy.context, source, backend=BACKEND, body=body, capability="BOTH")
        except Exception as error:
            rejection = {"type": type(error).__name__, "message": str(error)}
    finally:
        qa.profiles.write = write
    checked(report, qa, "install_profile_failure_restores_full_legacy_graph",
            rejection is not None and "deliberate failure" in rejection["message"]
            and graph_content(source, rig, qa, surface) == before
            and source.get(qa.profiles.PROFILE_KEY) == profile_before
            and holder.get("physics_influence") == influence_before
            and holder.id_properties_ui("physics_influence").as_dict() == influence_ui_before
            and observed == {"capability": "BOTH", "mode": "AUTOMATIC", "influence": 1., "flags": [True, True]},
            rejection=rejection, candidate_endpoint_before_injected_failure=observed,
            hook="QA-only in-memory write hook; native install and rollback executed")
    qa.physics.validate_physics(source)


def mode_tests(source, rig, record, cloth, report, qa, surface):
    # Direct endpoint capture/restore does not claim an intermediate whole mode
    # is valid: the holder has not been changed in this ABI-only roundtrip.
    before = mode_content(source, rig, record, cloth, qa, surface)
    opaque = surface.capture_mode(source, record)
    opposite = "MANUAL" if all(before["flags"]) else "AUTOMATIC"
    try:
        surface.set_mode(source, record, opposite)
        overlay = source.modifiers[record["physics"]["surface"]["overlay"]]
        require((overlay.show_viewport, overlay.show_render) == (opposite == "AUTOMATIC",) * 2,
                "The surface endpoint did not apply both flags")
    finally:
        surface.restore_mode(source, record, opaque)
    checked(report, qa, "surface_endpoint_capture_restore_exact",
            mode_content(source, rig, record, cloth, qa, surface) == before)
    surface.validate(source, rig, record)
    qa.tuning.initialize(source)
    qa.tuning.apply(bpy.context, (source,), mode="AUTOMATIC")
    record = qa.skirt.read_record(source)
    auto_before = mode_content(source, rig, record, cloth, qa, surface)
    qa.tuning.apply(bpy.context, (source,), mode="MANUAL")
    manual_record = qa.skirt.read_record(source)
    manual = mode_content(source, rig, manual_record, cloth, qa, surface)
    checked(report, qa, "whole_manual_endpoint", manual["influence"] == 0.
            and manual["flags"] == [False, False] and manual["cache"] == auto_before["cache"])
    qa.tuning.apply(bpy.context, (source,), mode="AUTOMATIC")
    record = qa.skirt.read_record(source)
    checked(report, qa, "whole_auto_return_exact",
            mode_content(source, rig, record, cloth, qa, surface) == auto_before)
    original_set = surface.set_mode
    injected = None

    def partial_write_then_fail(item, saved, mode):
        overlay = item.modifiers[saved["physics"]["surface"]["overlay"]]
        overlay.show_viewport = not overlay.show_viewport
        raise RuntimeError("QA deliberate failure after one surface endpoint flag write")

    try:
        surface.set_mode = partial_write_then_fail
        try:
            qa.tuning.apply(bpy.context, (source,), mode="MANUAL")
        except Exception as error:
            injected = {"type": type(error).__name__, "message": str(error)}
    finally:
        surface.set_mode = original_set
    checked(report, qa, "whole_mode_partial_write_rollback_exact", injected is not None
            and mode_content(source, rig, record, cloth, qa, surface) == auto_before,
            injected=injected, hook="In-memory QA monkeypatch only; no source file was edited")
    qa.physics.validate_physics(source)
    return record


def removal_preflight(source, rig, record, report, qa, surface):
    before = graph_content(source, rig, qa, surface)
    opaque = surface.preflight_remove(bpy.context, source, rig, record)
    names = {obj.name for obj in opaque["owned_objects"]}
    expected = {name for entries in record["physics"]["surface"]["roles"].values() for name in entries}
    checked(report, qa, "remove_preflight_exact_owned_inventory", names == expected
            and graph_content(source, rig, qa, surface) == before,
            owned_object_names=sorted(names), allowed_dependency_count=len(opaque["allowed_dependencies"]),
            scope="Read-only preflight; no artist/source/shared Rig or helpers were removed")
    foreign = bpy.data.objects.new("QA Foreign Dress Dependency", None)
    bpy.context.scene.collection.objects.link(foreign)
    rejection = None
    try:
        constraint = foreign.constraints.new("COPY_LOCATION")
        constraint.target = bpy.data.objects[record["physics"]["proxy"]]
        try:
            surface.preflight_remove(bpy.context, source, rig, record)
        except Exception as error:
            rejection = {"type": type(error).__name__, "message": str(error)}
    finally:
        bpy.data.objects.remove(foreign, do_unlink=True)
    checked(report, qa, "remove_foreign_user_rejected_before_write", rejection is not None
            and graph_content(source, rig, qa, surface) == before, rejection=rejection)


def original_replacement(report):
    endpoint = report.get("legacy_endpoint_replacement", {})
    return endpoint.get("name") if report.get("replacement_committed") and endpoint.get("present_in_artist") else None


def install_stage(args, report, qa, surface, protection, guards):
    source, rig, record = qa.owned_source(args.source)
    require(qa.physics.backend(record) == qa.physics.LEGACY_BACKEND,
            "This stage requires saved Dress controls without an already-installed actual surface")
    report["initial_saved_physics_present"] = bool(record.get("physics"))
    cache_gate = qa.saved_cache_preflight(source, record)
    report["saved_cache_preflight"] = cache_gate
    require(cache_gate["allowed"], cache_gate["reason"])
    for index, action in enumerate(protection.action_refs):
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
        report["copy_only_original_exit"] = True
    qa.skirt._require_controls_for_setup(source)
    checked(report, qa, "controls_exit_preserved_original_assets", protected(protection)["success"],
            details=protected(protection))
    body, body_status = qa.registered_body(bpy.context, rig, args)
    report["registered_body"] = body_status
    require(body is not None and body_status["measured"], "The exact registered Body input is unavailable")
    record = qa.skirt.read_record(source)
    if not record.get("physics"):
        # Exercise the real Manual-only adoption path before adding physics.
        # These saved profile edits occur only in this already-saved QA copy.
        qa.tuning.initialize(source, capability="MANUAL", context=bpy.context)
        report["manual_only_adoption_regression"] = True
        # This is an explicit public legacy construction inside the saved QA
        # copy. Its generated cage is not described as an artist/saved asset.
        started = time.perf_counter()
        qa.physics.add_physics(bpy.context, source)
        report["qa_legacy_creation_seconds"] = time.perf_counter() - started
        report["legacy_proof_origin"] = "Public legacy add_physics in the independent QA copy after its first save"
        checked(report, qa, "qa_legacy_creation_preserved_artist_assets", protected(protection)["success"],
                details=protected(protection))
    else:
        report["legacy_proof_origin"] = "Saved artist legacy physics, validated without reconstructing it"
    record, rig, legacy_proxy, legacy_cloth = qa.physics.validate_physics(source)
    checked(report, qa, "pre_upgrade_legacy_graph_proved", True, proxy=legacy_proxy.name,
            origin=report["legacy_proof_origin"], modifiers=[modifier.type for modifier in legacy_proxy.modifiers])
    # Protect the complete proven legacy baseline, including any QA-generated
    # cage/colliders. The initial artist Protection remains independent.
    guards["upgrade"] = qa.Protection()
    report["protected_pre_upgrade_inventory"] = guards["upgrade"].summary()
    report["legacy_endpoint_replacement"] = {"name": legacy_proxy.name, "data": legacy_proxy.data.name,
        "present_in_artist": report["initial_saved_physics_present"], "origin": report["legacy_proof_origin"],
        "raw_mesh_sha256": qa.digest(qa.raw_mesh_content(legacy_proxy)),
        "native_cache": qa.cache_state(legacy_cloth), "proof": "Full production legacy graph validated before replacement"}
    reject_saved_bake(source, rig, record, body, report, qa, surface)
    reject_install_detached_key(source, rig, body, report, qa, surface)
    reject_install_profile_write(source, rig, body, report, qa, surface)
    before_context = context_content(bpy.context)
    before_channels = qa.pose_channels(rig)
    before_drivers = surface._drivers(rig)
    before_record = source[qa.skirt.RECORD_KEY]
    started = time.perf_counter()
    record = qa.physics.add_physics(bpy.context, source, backend=BACKEND, body=body)
    report["explicit_install_seconds"] = time.perf_counter() - started
    replaced = report["legacy_endpoint_replacement"]["name"]
    report["replacement_committed"] = True
    checked(report, qa, "explicit_install_restored_context_channels_drivers",
            context_content(bpy.context) == before_context and qa.pose_channels(rig) == before_channels
            and surface._drivers(rig) == before_drivers,
            old_record_sha256=qa.digest(before_record), new_record_sha256=qa.digest(source[qa.skirt.RECORD_KEY]))
    actual, cloth = installation_layout(source, rig, record, report, qa, surface)
    if report.get("manual_only_adoption_regression"):
        holder, _identifier, _path = qa.skirt.physics_control(source)
        overlay = source.modifiers[record["physics"]["surface"]["overlay"]]
        checked(report, qa, "manual_profile_install_native_endpoint_consistent",
                holder.get("physics_influence") == 0.
                and not overlay.show_viewport and not overlay.show_render)
        before_cache = qa.cache_state(cloth)
        profile = qa.tuning.initialize(source, capability="BOTH", context=bpy.context)
        checked(report, qa, "manual_to_both_initialization_all_endpoints_automatic",
                profile["capability"] == "BOTH" and profile["mode"] == "AUTOMATIC"
                and holder.get("physics_influence") == 1.
                and overlay.show_viewport and overlay.show_render
                and qa.cache_state(cloth) == before_cache,
                scope="Native installation and initialization functions; public operator selection/UI not exercised")
    exact = graph_content(source, rig, qa, surface)
    returned = qa.physics.add_physics(bpy.context, source, backend=BACKEND, body=body)
    checked(report, qa, "explicit_install_idempotent_exact", returned == record
            and graph_content(source, rig, qa, surface) == exact,
            native_id_counts={name: len(values) for name, values in exact["inventory"].items()})
    record = mode_tests(source, rig, record, cloth, report, qa, surface)
    removal_preflight(source, rig, record, report, qa, surface)
    proof = surface.export_capture(source)
    before = graph_content(source, rig, qa, surface)
    surface.validate_snapshot(source, proof)
    checked(report, qa, "static_export_capture_validate_readonly",
            graph_content(source, rig, qa, surface) == before,
            proof_version=proof["version"], proof_backend=proof["backend"], proof_sha256=qa.digest(proof),
            scope="Capture and proof validation only; worker/strip/FBX/Keys export are not accepted by this stage")
    details = protected(protection, original_replacement(report))
    checked(report, qa, "original_mesh_rest_actions_preserved", details["success"], details=details)
    details = protected(guards["upgrade"], replaced)
    checked(report, qa, "pre_upgrade_baseline_preserved_except_owned_replaced_proxy", details["success"], details=details)
    destination = args.output / "scenes/Cosha_Dress_QA_surface_install.blend"
    qa.save_candidate(destination, args.input)
    report["prepared_candidate"] = {"path": str(destination), **qa.file_state(destination)}
    report["source"] = source.name
    report["rig"] = rig.name
    report["owner"] = record["owner"]
    report["backend"] = record["physics"]["backend"]
    report["native_cache_after"] = qa.cache_state(cloth)


def motion_check(report, qa, name, condition, **facts):
    qa.report_check(report, name, condition, **facts)
    require(condition, "Motion mechanism check failed: " + name)


def motion_input_gate(args, report, qa, diag):
    require(args.input.is_relative_to(HERE) and args.install_report.is_relative_to(HERE)
            and args.install_report.is_file(), "Motion reads only an installed Validation QA and its report")
    installed = json.loads(args.install_report.read_text(encoding="utf-8"))
    candidate = installed.get("prepared_candidate", {})
    require(installed.get("success") is True and installed.get("stage") == "install"
            and len(installed.get("checks", [])) >= 17
            and all(item.get("passed") is True for item in installed["checks"])
            and installed.get("artist_disk_exact") is True
            and installed.get("canonical_and_frozen_code_exact") is True
            and installed.get("protected_original_after", {}).get("success") is True
            and installed.get("protected_pre_upgrade_after", {}).get("success") is True,
            "The installation report is not a passing protected native gate")
    require(Path(candidate.get("path", "")).resolve() == args.input
            and candidate.get("sha256") == sha(args.input), "The exact installed QA bytes changed")
    def canonical(manifest):
        return {str(Path(path).resolve()).casefold(): value["sha256"] for path, value in manifest.items()
                if Path(path).resolve().is_relative_to(REPOSITORY / "addons/character_designer")}
    before = canonical(installed["source_manifest_after"])
    after = canonical(diag.source_manifest())
    surface_path = str((REPOSITORY / "addons/character_designer/skirt_surface.py").resolve()).casefold()
    worker_path = str((REPOSITORY / "addons/character_designer/unity_export_worker.py").resolve()).casefold()
    require(set(before) == set(after), "Current canonical inventory differs from the installed exact inventory")
    for path, expected in ((surface_path, args.expected_surface_sha), (worker_path, args.expected_worker_sha)):
        require(isinstance(expected, str) and len(expected) == 64
                and all(character in "0123456789abcdef" for character in expected.casefold()),
                "Both surface and worker require explicit complete frozen SHA256 values")
        require(after.get(path) == expected.casefold(), "Current canonical source differs from its explicit final reviewed SHA: " + path)
    changed = [path for path in before if before[path] != after[path]]
    require(set(changed) <= {surface_path, worker_path}, "A canonical module other than the explicit surface/worker changed since install")
    report["install_input"] = {"report": str(args.install_report), "report_sha256": sha(args.install_report),
        "candidate_sha256": candidate["sha256"], "native_install_checks": len(installed["checks"]),
        "source": installed["source"], "rig": installed["rig"], "owner": installed["owner"],
        "runtime_differences": [{"path": path, "install_sha256": before[path], "motion_sha256": after[path],
                                 "scope": "This motion run is a new compatibility validation; the old install did not validate changed code"}
                                for path in changed],
        "scope": "This new run validates current-runtime compatibility; the old install did not validate changed code"}
    motion_check(report, qa, "sealed_install_input_and_explicit_runtime", True,
                 input_sha256=candidate["sha256"], surface_sha256=after[surface_path],
                 worker_sha256=after[worker_path], changed_modules=len(changed))
    return installed["source"]


def motion_objects(source, qa, surface):
    record, rig, actual, cloth = qa.physics.validate_physics(source)
    require(record["physics"].get("backend") == BACKEND, "Motion must use the actual surface backend")
    native = record["physics"]["surface"]
    neutral = bpy.data.objects[native["roles"]["NEUTRAL_SURFACE"][0]]
    require(len(source.data.vertices) == len(actual.data.vertices) == len(neutral.data.vertices) == 800,
            "This Cosha motion fixture requires the proven raw800 exact-index graph")
    surface.validate(source, rig, record)
    return record, rig, actual, cloth, neutral


def motion_probe(obj, scene, label, keep):
    """Independent QA data; never share artist/source Keys or add a second GN user."""
    probe, data = obj.copy(), obj.data.copy()
    probe.data = data
    try:
        require(data != obj.data and (obj.data.shape_keys is None or
                data.shape_keys is not None and data.shape_keys != obj.data.shape_keys), "QA probe shares source data/Keys")
        require(data.users == 1, "QA probe mesh has an unexpected native user")
        copied_key = data.shape_keys
        if copied_key is not None:
            require(bpy.data.shape_keys.get(copied_key.name) == copied_key
                    and bpy.data.user_map(subset={copied_key}).get(copied_key, set()) == {data},
                    "QA probe Key does not belong uniquely to the exact independent mesh")
        for owner in (probe, data, data.shape_keys):
            if owner is not None:
                owner.use_fake_user = False  # Declared QA-copy metadata; originals are untouched.
                for key in list(owner.keys()):
                    del owner[key]
        probe.name = "QA Motion " + label
        for modifier in list(probe.modifiers):
            if not keep(modifier):
                probe.modifiers.remove(modifier)
        scene.collection.objects.link(probe)
        probe.hide_viewport = probe.hide_render = False
        probe.hide_select = True
        probe.hide_set(True)
        probe.update_tag()
        return probe
    except Exception:
        remove_motion_probe(probe)
        raise


def remove_motion_probe(probe):
    if probe is None:
        return
    data, keys = probe.data, probe.data.shape_keys
    key_identity = (keys.name, keys.as_pointer()) if keys is not None else None
    if keys is not None:
        # Native Mesh removal alone can leave an orphan Key pointing at freed
        # geometry. Detach this exact owned Key before deleting its mesh.
        require(data.users == 1 and bpy.data.shape_keys.get(key_identity[0]) == keys
                and bpy.data.user_map(subset={keys}).get(keys, set()) == {data},
                "The exact owned probe Key has an unexpected native owner")
        probe.shape_key_clear()
        require(data.shape_keys is None, "Native owned probe Key clearing did not detach its mesh")
        remaining = bpy.data.shape_keys.get(key_identity[0])
        if remaining is not None:
            require(remaining.as_pointer() == key_identity[1]
                    and not bpy.data.user_map(subset={remaining}).get(remaining, set()),
                    "Independent QA probe Key acquired a foreign user")
            bpy.data.batch_remove(ids=(remaining,))
            require(bpy.data.shape_keys.get(key_identity[0]) is None, "The exact owned probe Key was not removed")
    bpy.data.objects.remove(probe, do_unlink=True)
    require(data.users == 0, "Independent QA probe mesh acquired a foreign user")
    bpy.data.batch_remove(ids=(data,))


def point_error(first, second, meters=1.):
    require(len(first) == len(second), "Exact vertex count/order changed")
    return max(((a - b).length * meters for a, b in zip(first, second)), default=0.)


def motion_state(qa, surface, source, rig):
    scene = bpy.context.scene
    from character_designer import skirt_original_mode
    record = qa.skirt.read_record(source)
    overlay = source.modifiers[record["physics"]["surface"]["overlay"]]
    return {"channels": qa.pose_channels(rig), "basis": [list(row) for row in rig.matrix_basis],
            "rotation_mode": rig.rotation_mode, "context": context_content(bpy.context),
            "range": [scene.frame_start, scene.frame_end], "auto_key": scene.tool_settings.use_keyframe_insert_auto,
            "record": source[qa.skirt.RECORD_KEY], "profile": source.get(qa.profiles.PROFILE_KEY),
            "correction_key": skirt_original_mode.CORRECTIONS, "correction": source.get(skirt_original_mode.CORRECTIONS),
            "constraints": {bone.name: [(item.name, item.mute, item.influence,
                               getattr(item, "mix_mode", None)) for item in bone.constraints] for bone in rig.pose.bones},
            "pose_properties": {bone.name: {key: value for key, value in bone.items()
                                if type(value) in (bool, int, float, str)} for bone in rig.pose.bones},
            "key_values": {key.name: key.value for key in source.data.shape_keys.key_blocks}
                          if source.data.shape_keys else {},
            "key_eval_time": source.data.shape_keys.eval_time if source.data.shape_keys else None,
            "scene_action_refs": {key: value.name for key, value in scene.items()
                                  if key.startswith("CD_QA_AuthorAction_") and isinstance(value, bpy.types.Action)},
            "scene_animation_backup": scene.get("CD_QA_AuthorAnimationBackup"),
            "overlay_flags": [overlay.show_viewport, overlay.show_render],
            "drivers": surface._drivers(rig)}


def restore_animation(backup):
    for item in backup:
        owner_type, name, _library = item["owner"]
        collection = {"Object": bpy.data.objects, "Key": bpy.data.shape_keys}.get(owner_type)
        require(collection is not None and name in collection, "Unsupported/missing saved animation owner: " + name)
        owner = collection[name]
        animation = owner.animation_data_create()
        action = item["action"]
        animation.action = bpy.data.actions[action[1]] if action else None
        if action and item["slot"] is not None:
            slot = next((slot for slot in animation.action.slots if slot.identifier == item["slot"]), None)
            require(slot is not None, "Original Action slot disappeared")
            animation.action_slot = slot
        require([track.name for track in animation.nla_tracks] == [entry[0] for entry in item["nla_track_flags"]],
                "Original NLA track inventory changed")
        for track, (_name, mute, solo) in zip(animation.nla_tracks, item["nla_track_flags"]):
            track.mute, track.is_solo = mute, solo


def restore_motion_state(state, backup, source, rig, qa, surface, action_name):
    qa.skirt._activate(bpy.context, rig, "POSE")
    if qa.original.active(rig):
        qa.public_switch(bpy.ops.character_designer.body_original_mode, action="CONTROLS")
    bpy.context.window_manager.character_designer_skirt.source = source
    qa.public_switch(bpy.ops.character_designer.dress_motion_reset)
    _record, _rig, _actual, cloth, _neutral = motion_objects(source, qa, surface)
    cloth.point_cache.use_disk_cache = False
    cloth.point_cache.filepath = state["cache_filepath"]
    cloth.point_cache.use_library_path = state["cache_library_path"]
    scene = bpy.context.scene
    qa.restore_channels(rig, state["channels"], Matrix(state["basis"]), state["rotation_mode"])
    for name, entries in state["constraints"].items():
        require(len(rig.pose.bones[name].constraints) == len(entries), "Original constraint inventory changed")
        for item, (saved_name, mute, influence, mix) in zip(rig.pose.bones[name].constraints, entries):
            require(item.name == saved_name, "Original constraint inventory changed")
            item.mute, item.influence = mute, influence
            if mix is not None:
                item.mix_mode = mix
    for name, values in state["pose_properties"].items():
        for key, value in values.items():
            rig.pose.bones[name][key] = value
    for key, value in ((state["correction_key"], state["correction"]),
                       (qa.profiles.PROFILE_KEY, state["profile"])):
        if value is None:
            if key in source:
                del source[key]
        else:
            source[key] = value
    source[qa.skirt.RECORD_KEY] = state["record"]
    original_record = qa.skirt.read_record(source)
    overlay = source.modifiers[original_record["physics"]["surface"]["overlay"]]
    overlay.show_viewport, overlay.show_render = state["overlay_flags"]
    # Cache range belongs to the saved native cache, not guessed record fields.
    cloth.point_cache.frame_start, cloth.point_cache.frame_end, cloth.point_cache.frame_step = state["cache_range"]
    restore_animation(backup)
    if source.data.shape_keys:
        for name, value in state["key_values"].items():
            source.data.shape_keys.key_blocks[name].value = value
        source.data.shape_keys.eval_time = state["key_eval_time"]
    scene.frame_start, scene.frame_end = state["range"]
    scene.tool_settings.use_keyframe_insert_auto = state["auto_key"]
    scene.frame_set(state["context"]["frame"], subframe=state["context"]["subframe"])
    bpy.context.view_layer.update()
    for key in list(scene.keys()):
        if key.startswith("CD_QA_AuthorAction_") or key == "CD_QA_AuthorAnimationBackup":
            del scene[key]
    for key, name in state["scene_action_refs"].items():
        scene[key] = bpy.data.actions[name]
    if state["scene_animation_backup"] is not None:
        scene["CD_QA_AuthorAnimationBackup"] = state["scene_animation_backup"]
    action = bpy.data.actions.get(action_name)
    if action is not None:
        require(action.get("CD_QA_SyntheticInput") is True, "QA Action ownership changed")
        action.use_fake_user = False
        require(action.users == 0, "Synthetic QA Action still has a native user")
        bpy.data.actions.remove(action)
    qa.skirt._activate(bpy.context, rig, "OBJECT")
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for name in state["context"]["selected"]:
        bpy.context.view_layer.objects[name].select_set(True)
    active = state["context"]["active"]
    bpy.context.view_layer.objects.active = bpy.data.objects.get(active) if active else None
    if active and state["context"]["mode"] != "OBJECT":
        bpy.ops.object.mode_set(mode=state["context"]["mode"])
    motion_objects(source, qa, surface)
    require(surface._drivers(rig) == state["drivers"], "Original native drivers changed")


def crossing_scalars(value):
    arrays = ("crossing_pairs", "coplanar_unresolved", "degenerate_unresolved", "boundary_unresolved")
    return {**{key: entry for key, entry in value.items() if key not in arrays},
            **{key + "_count": len(value.get(key, [])) for key in arrays},
            "first_crossing_ids": [{key: item[key] for key in ("dress_triangle", "body_triangle")}
                                   for item in value.get("crossing_pairs", [])[:8]]}


def rigid_frame(matrix):
    """Orthogonal native world axes: retain distance, remove only rigid motion.

    A full inverse matrix would divide by the rig/bone scale. These normalized
    axes keep each projected coordinate in the original world distance units.
    """
    linear = matrix.to_3x3()
    require(all(math.isfinite(value) for row in matrix for value in row), "Nonfinite native frame")
    require(linear.col[2].length > 1.e-12, "Degenerate native frame up axis")
    up = linear.col[2].normalized()
    right = linear.col[0] - up * linear.col[0].dot(up)
    require(right.length > 1.e-12, "Degenerate native frame right axis")
    right.normalize()
    forward = up.cross(right).normalized()
    axes = (right, forward, up)
    rotation = Matrix(tuple(tuple(axis[row] for axis in axes) for row in range(3))).to_quaternion()
    return {"origin": matrix.translation.copy(), "axes": axes, "rotation": rotation}


def rigid_points(points, frame):
    return [Vector(tuple((point-frame["origin"]).dot(axis) for axis in frame["axes"])) for point in points]


def motion_collision_sample(source, rig, actual, body, record, frame, args, qa, diag, meters, baseline):
    graph = bpy.context.evaluated_depsgraph_get()
    physical = diag.mesh_snapshot(actual, graph)
    final = diag.mesh_snapshot(source, graph)
    body_mesh = diag.mesh_snapshot(body, graph)
    require(len(body_mesh["points"]) <= args.body_vertex_limit, "Native Body exceeds the declared evaluated budget")
    pin = actual.vertex_groups[record["physics"]["surface"]["pin_group"]].index
    waist = source.vertex_groups[record["controls"]["waist"]].index
    for mesh, group in ((physical, pin), (final, waist)):
        require(any(mesh["weights"]), "Evaluated native weight layer is unavailable")
        mesh["free_indices"] = [index for index, weights in enumerate(mesh["weights"])
                               if next((item["weight"] for item in weights if item["index"] == group), 0.) < .999]
    bounds = diag.framing(rig, record, graph)
    epsilon = max(1.e-8, record["fit"]["height_world"] * 1.e-6)
    item = {"frame": frame, "physical_vertices": len(physical["points"]), "final_vertices": len(final["points"]),
            "body_vertices": len(body_mesh["points"]), "actual_body_inside_outside_proven": False,
            "physical_body": crossing_scalars(diag.triangle_crossings(physical, body_mesh, bounds,
                                               args.triangle_pair_limit, epsilon)),
            "final_weight_layer_complete": all(final["weights"]),
            "body_weight_layer_complete": all(body_mesh["weights"]),
            "final_free_vertices": len(final["free_indices"]), "old3": []}
    # Keep fixed waist/transition contacts separate from independently moving
    # free skirt/leg crossings. Exact native triangle IDs are stable in this
    # saved fixture; a baseline contact alone is not a new dynamic crossing.
    crossing = diag.triangle_crossings(final, body_mesh, bounds, args.triangle_pair_limit, epsilon)
    item["final_body"] = crossing_scalars(crossing)
    evaluated = rig.evaluated_get(graph)
    waist_frame = rigid_frame(evaluated.matrix_world @ evaluated.pose.bones[record["controls"]["waist"]].matrix)
    local = rigid_points(final["points"], waist_frame)
    if not baseline:
        baseline.update(frame=frame, local=local,
                        complete=(crossing["status"] == "measured" and all(final["weights"]) and all(body_mesh["weights"])
                                  and all(not crossing[name] for name in
                                          ("coplanar_unresolved", "degenerate_unresolved", "boundary_unresolved"))),
                        pairs={(entry["dress_triangle"], entry["body_triangle"]) for entry in crossing["crossing_pairs"]})
    require(len(local) == len(baseline["local"]), "Final surface identity changed between collision samples")
    legs, _axes, _height = qa.body_inputs(rig, record)
    leg_names = {name for entry in legs.values() for name in entry["chain"]}
    free = set(final["free_indices"])
    categories = {name: [] for name in ("waist_transition_contacts", "baseline_unproven_free_contacts", "baseline_or_stationary_free_contacts",
                                        "moving_free_leg_crossings", "moving_free_other_body_crossings")}
    for entry in crossing["crossing_pairs"]:
        pair = (entry["dress_triangle"], entry["body_triangle"])
        indices = entry["dress_vertices"]
        displacement = point_error([local[index] for index in indices],
                                   [baseline["local"][index] for index in indices], meters)
        body_leg = any(weight["name"] in leg_names and weight["weight"] > 0.
                       for index in entry["body_vertices"] for weight in body_mesh["weights"][index])
        if not all(index in free for index in indices):
            category = "waist_transition_contacts"
        elif not baseline["complete"]:
            category = "baseline_unproven_free_contacts"
        elif pair in baseline["pairs"] or displacement <= qa.geometry_guard(meters):
            category = "baseline_or_stationary_free_contacts"
        else:
            category = "moving_free_leg_crossings" if body_leg else "moving_free_other_body_crossings"
        categories[category].append({"dress_triangle": pair[0], "body_triangle": pair[1],
                                     "waist_relative_vertex_motion_m": displacement, "body_leg_weight_present": body_leg})
    item["final_body_contact_classification"] = {
        "baseline_frame": baseline["frame"], "movement_guard_m": qa.geometry_guard(meters),
        "baseline_coverage_complete": baseline["complete"],
        "counts": {name: len(entries) for name, entries in categories.items()},
        "first_pairs": {name: entries[:8] for name, entries in categories.items()},
        "definition": "All-three-free triangles moving in normalized Waist axes, absent from frame1 exact pair set; leg region uses actual positive native Body leg weights",
        "limitation": "Existing free contacts and waist-transition contacts remain reported, not cleared or silently treated as separation"}
    for name in record["physics"]["colliders"]:
        collider = bpy.data.objects[name]
        if collider == bpy.data.objects[record["physics"]["surface"]["roles"]["BODY_ATTACHMENT"][0]]:
            continue
        qa.physics._closed_collider(collider)  # The verifier raises; it returns no boolean.
        native = qa.ClosedCollider(collider, graph, epsilon)
        binding = collider.vertex_groups[0].name
        side = next((side for side, entry in legs.items() if binding == entry["chain"][0]), None)
        item["old3"].append({"object": name,
            "binding_bone": binding, "role": "leg." + side if side else "pelvis_or_other",
            "physical_free_vertices": qa.collision_metrics(physical["points"], native, meters, physical["free_indices"]),
            "final_free_vertices": qa.collision_metrics(final["points"], native, meters, final["free_indices"]),
            "limitation": "Signed free-vertex samples on a verified closed owned collider; not whole-surface separation"})
    require(len(item["old3"]) == 3, "Expected exactly the three proved old owned colliders")
    return item, final, body_mesh, bounds


def frozen_delta_tests(source, rig, actual, cloth, neutral, record, args, result, qa, surface, meters):
    """Cloth stays sealed while the original S delta is exercised through O."""
    scene = bpy.context.scene
    scene.frame_set(25)
    before_cache = qa.cache_state(cloth)
    guard = min(NATIVE_METRES_LIMIT, NATIVE_WORLD_LIMIT * meters)
    skin = motion_probe(source, scene, "Original Skin Delta", lambda modifier: modifier.type != "NODES")
    original_keys = source.data.shape_keys
    original_key_names = [key.name for key in original_keys.key_blocks] if original_keys else []
    original_key_pointer = original_keys.as_pointer() if original_keys else None
    qa_key = None
    owned_source_basis = None
    try:
        def snapshots():
            graph = bpy.context.evaluated_depsgraph_get()
            values = {key: qa.world_mesh(obj, graph)["points"] for key, obj in
                      (("O", source), ("S", skin), ("C", actual), ("H0", neutral))}
            require(len(values["O"]) == len(values["S"]) == 3040 and len(values["C"]) == len(values["H0"]) == 800
                    and all(qa.finite(points) for points in values.values()), "Nonfinite or changed manual/Key output layout")
            return values
        def delta_error(before, after):
            return point_error([a-b for a, b in zip(after["O"], before["O"])],
                               [a-b for a, b in zip(after["S"], before["S"])], meters)
        profile = qa.tuning.effective(source)
        motion_check(result, qa, "manual_capability_present", profile["capability"] == "BOTH")
        baseline = snapshots()
        try:
            qa.tuning.apply(bpy.context, (source,), mode="MANUAL")
            manual = snapshots()
            motion_check(result, qa, "manual_mode_native_endpoint", point_error(manual["O"], manual["S"], meters) <= guard
                         and qa.cache_state(cloth) == before_cache
                         and point_error(baseline["O"], manual["O"], meters) > 1.e-5,
                         endpoint_error_m=point_error(manual["O"], manual["S"], meters),
                         automatic_output_effect_m=point_error(baseline["O"], manual["O"], meters))
        finally:
            qa.tuning.apply(bpy.context, (source,), mode="AUTOMATIC")
        restored = snapshots()
        motion_check(result, qa, "automatic_manual_automatic_no_jump", point_error(baseline["O"], restored["O"], meters) <= guard
                     and qa.cache_state(cloth) == before_cache, error_m=point_error(baseline["O"], restored["O"], meters))
        control = rig.pose.bones[record["controls"]["hem"]]
        saved = control.matrix_basis.copy()
        try:
            control.location += control.bone.matrix_local.to_3x3().inverted() @ Vector((record["fit"]["height_world"] * .02, 0, 0))
            rig.update_tag(); bpy.context.view_layer.update()
            after = snapshots()
            motion_check(result, qa, "manual_hem_delta_preserved", delta_error(baseline, after) <= guard
                         and point_error(after["O"], baseline["O"], meters) > 1.e-5
                         and point_error(after["C"], baseline["C"], meters) <= guard
                         and point_error(after["H0"], baseline["H0"], meters) <= guard
                         and qa.cache_state(cloth) == before_cache,
                         output_delta_m=point_error(after["O"], baseline["O"], meters), delta_error_m=delta_error(baseline, after))
        finally:
            control.matrix_basis = saved
            rig.update_tag(); bpy.context.view_layer.update()
        motion_check(result, qa, "manual_hem_restore", point_error(snapshots()["O"], baseline["O"], meters) <= guard)
        if source.data.shape_keys is None:
            source.shape_key_add(name="Basis", from_mix=False)
            created_basis_key = source.data.shape_keys
            owned_source_basis = (created_basis_key.name, created_basis_key.as_pointer())
        if skin.data.shape_keys is None:
            skin.shape_key_add(name="Basis", from_mix=False)
        qa_key = source.shape_key_add(name="QA Motion Asymmetric Key", from_mix=False)
        skin_key = skin.shape_key_add(name="QA Motion Asymmetric Key", from_mix=False)
        source_basis, skin_basis = source.data.shape_keys.reference_key, skin.data.shape_keys.reference_key
        ids = [index for index in record["fit"]["rings"][6] if source_basis.data[index].co.x > 0.]
        require(ids and len(ids) < len(record["fit"]["rings"][6]), "QA asymmetric Key region is not explicit")
        for index in ids:
            qa_key.data[index].co.z += .008
            skin_key.data[index].co.z += .008
        qa_key.relative_key, skin_key.relative_key = source_basis, skin_basis
        qa_key.value = skin_key.value = 0.
        source.data.update(); skin.data.update(); bpy.context.view_layer.update()
        key_before = snapshots()
        qa_key.value = skin_key.value = .75
        source.data.update(); skin.data.update(); bpy.context.view_layer.update()
        after = snapshots()
        motion_check(result, qa, "asymmetric_key_O_minus_S_preserved", delta_error(key_before, after) <= guard
                     and point_error(after["O"], key_before["O"], meters) > 1.e-5
                     and point_error(after["C"], key_before["C"], meters) <= guard
                     and point_error(after["H0"], key_before["H0"], meters) <= guard
                     and qa.cache_state(cloth) == before_cache,
                     raw_region_count=len(ids), local_delta_z=.008, value=.75,
                     delta_error_m=delta_error(key_before, after), output_delta_m=point_error(after["O"], key_before["O"], meters))
    finally:
        if qa_key is not None:
            qa_key.value = 0.
            source.shape_key_remove(qa_key)
        if original_keys is None and source.data.shape_keys is not None:
            owned_key = source.data.shape_keys
            require(owned_source_basis == (owned_key.name, owned_key.as_pointer())
                    and bpy.data.shape_keys.get(owned_source_basis[0]) == owned_key
                    and bpy.data.user_map(subset={owned_key}).get(owned_key, set()) == {source.data},
                    "The captured QA Basis Key changed identity or acquired an outside native owner")
            owned_identity = owned_source_basis
            source.shape_key_clear()
            require(source.data.shape_keys is None, "Native QA Basis clearing did not detach its mesh")
            remaining = bpy.data.shape_keys.get(owned_identity[0])
            if remaining is not None:
                require(remaining.as_pointer() == owned_identity[1]
                        and not bpy.data.user_map(subset={remaining}).get(remaining, set()),
                        "Owned QA Basis Key retained a foreign user")
                bpy.data.batch_remove(ids=(remaining,))
                require(bpy.data.shape_keys.get(owned_identity[0]) is None, "The exact captured QA Basis Key was not removed")
        remove_motion_probe(skin)
        source.data.update(); rig.update_tag(); bpy.context.view_layer.update()
    motion_check(result, qa, "qa_keys_removed_original_key_identity_preserved",
                 (source.data.shape_keys is None if original_keys is None else
                  source.data.shape_keys.as_pointer() == original_key_pointer
                  and [key.name for key in source.data.shape_keys.key_blocks] == original_key_names))
    motion_objects(source, qa, surface)


def original_roundtrip(source, rig, actual, cloth, neutral, result, qa, surface, meters):
    from character_designer import skirt_original_mode
    graph = bpy.context.evaluated_depsgraph_get()
    before = {key: qa.pack(qa.world_mesh(obj, graph)["points"]) for key, obj in
              (("O", source), ("C", actual), ("H0", neutral))}
    correction_before = source.get(skirt_original_mode.CORRECTIONS)
    cached = qa.cache_state(cloth)
    action, slot = rig.animation_data.action, rig.animation_data.action_slot
    # Only our declared QA Action is detached; original author Actions remain assets.
    require(action is not None and action.get("CD_QA_SyntheticInput") is True, "Unexpected Original QA Action")
    rig.animation_data.action = None
    saved_basis = None
    entered_channels = None
    def restore_edited_bone():
        if entered_channels is not None:
            bone.rotation_mode = entered_channels["mode"]
            bone.location, bone.scale = entered_channels["location"], entered_channels["scale"]
            bone.rotation_quaternion = entered_channels["quaternion"]
            bone.rotation_euler = entered_channels["euler"]
            bone.rotation_axis_angle = entered_channels["axis_angle"]
    try:
        qa.skirt._activate(bpy.context, rig, "POSE")
        qa.public_switch(bpy.ops.character_designer.body_original_mode, action="ORIGINAL")
        require(qa.original.active(rig), "Public coordinator did not establish its native session")
        motion_objects(source, qa, surface)
        guard = qa.geometry_guard(meters)
        graph = bpy.context.evaluated_depsgraph_get()
        enter_errors = {key: qa.packed_error(before[key], qa.world_mesh(obj, graph)["points"], meters)
                        for key, obj in (("O", source), ("C", actual), ("H0", neutral))}
        motion_check(result, qa, "public_original_enter_no_jump", max(enter_errors.values()) <= guard
                     and qa.cache_state(cloth) == cached,
                     errors_m=enter_errors, coordinator="body_original_mode", cache_unchanged=qa.cache_state(cloth) == cached)
        record = qa.skirt.read_record(source)
        bone = rig.pose.bones[record["chains"][0]["def"][-1]]
        saved_basis = bone.matrix_basis.copy()
        entered_channels = qa.pose_channels(rig)[bone.name]
        before_edit = qa.pack(qa.world_mesh(source, graph)["points"])
        # A connected DEF can discard location channels. A local rotation is
        # an actual reversible author edit on this same native bone.
        bone.matrix_basis = saved_basis @ Matrix.Rotation(.10, 4, "X")
        rig.update_tag(); bpy.context.view_layer.update()
        edit_graph = bpy.context.evaluated_depsgraph_get()
        changed = qa.world_mesh(source, edit_graph)["points"]
        input_errors = {key: qa.packed_error(before[key], qa.world_mesh(obj, edit_graph)["points"], meters)
                        for key, obj in (("C", actual), ("H0", neutral))}
        motion_check(result, qa, "public_original_def_edit_visible_and_inputs_fixed",
                     qa.packed_error(before_edit, changed, meters) > 1.e-5
                     and max(input_errors.values()) <= guard and qa.cache_state(cloth) == cached,
                     bone=bone.name, local_X_rotation_rad=.10,
                     output_delta_m=qa.packed_error(before_edit, changed, meters), input_errors_m=input_errors)
        restore_edited_bone()
        rig.update_tag(); bpy.context.view_layer.update()
        saved_basis = None
        qa.public_switch(bpy.ops.character_designer.body_original_mode, action="CONTROLS")
        require(not qa.original.active(rig), "Public coordinator retained a Body Original session")
    finally:
        if saved_basis is not None:
            restore_edited_bone()
            rig.update_tag(); bpy.context.view_layer.update()
        if qa.original.active(rig):
            qa.public_switch(bpy.ops.character_designer.body_original_mode, action="CONTROLS")
        rig.animation_data.action = action
        rig.animation_data.action_slot = slot
        rig.update_tag(); bpy.context.view_layer.update()
    motion_objects(source, qa, surface)
    graph = bpy.context.evaluated_depsgraph_get()
    errors = {key: qa.packed_error(before[key], qa.world_mesh(obj, graph)["points"], meters)
              for key, obj in (("O", source), ("C", actual), ("H0", neutral))}
    motion_check(result, qa, "public_original_controls_restore", max(errors.values()) <= qa.geometry_guard(meters)
                 and qa.cache_state(cloth) == cached and source.get(skirt_original_mode.CORRECTIONS) == correction_before,
                 errors_m=errors, original_correction_metadata_exact=source.get(skirt_original_mode.CORRECTIONS) == correction_before,
                 scope="No-edit return plus a reverted QA edit; persistent author correction editing is not tested")


def synthetic_run_values(phase, height):
    """Explicit synthetic stress gait, not an imported/foot-planted run clip."""
    cycle = math.tau * 4. * phase
    move = Vector((0., height * .9 * phase, height * .012 * math.sin(cycle * 2.)))
    angles = {}
    for side, offset in (("L", 0.), ("R", math.pi)):
        swing = math.sin(cycle + offset)
        angles[side] = [math.radians(35.) * swing, -math.radians(50.) * max(swing, 0.),
                        math.radians(10.) * swing]
    return move, 0., angles


def synthetic_stop_turn_values(phase, height, frozen_values):
    """Frozen advance/gait stop at .55, then finite .55-.65 ninety-degree turn."""
    move, _yaw, angles = frozen_values("abrupt_stop", phase, height)
    progress = max(0., min(1., (phase - .55) / .10))
    yaw = math.radians(90.) * progress * progress * (3. - 2. * progress)
    return move, yaw, angles


def author_motion_input(case, rig, legs, axes, channels, basis, height, frames, qa):
    if case not in {"run", "abrupt_stop_turn"}:
        return qa.author_case(case, rig, legs, axes, channels, basis, height, frames)
    animation = rig.animation_data
    require(animation is None or animation.action is None and all(track.mute for track in animation.nla_tracks),
            "Detach author playback in the private candidate before creating synthetic stress input")
    previous = qa.representative_values
    original_actions = {action.as_pointer() for action in bpy.data.actions}
    def values(which, phase, native_height):
        if which == "run":
            return synthetic_run_values(phase, native_height)
        if which == "abrupt_stop_turn":
            return synthetic_stop_turn_values(phase, native_height, previous)
        return previous(which, phase, native_height)
    try:
        # Reuse the frozen native Action/slot/FCurve authoring and axis handling;
        # this local callback override is restored even after a native failure.
        # No frozen file, artist Action, runtime constraint or driver is edited.
        qa.representative_values = values
        action = qa.author_case(case, rig, legs, axes, channels, basis, height, frames)
        require(action.as_pointer() not in original_actions and action.get("CD_QA_SyntheticInput") is True
                and rig.animation_data.action == action, "Synthetic stress did not create its own marked native Action")
        action["CD_QA_InputDescription"] = (
            "Synthetic Run stress gait; not an imported, foot-planted or production clip" if case == "run" else
            "Synthetic advance/alternating legs, stop at 55%, ninety-degree turn through 65%, then full hold; not a real imported clip")
        return action
    finally:
        qa.representative_values = previous


def native_input_summary(case, args, measurements, height, meters, result, qa):
    """Independent evaluated bone/Body input proof, never inferred from Cloth."""
    threshold = height * meters * .01  # Same meaning/value as old qa.summarize_motion.
    knees = {side: max(item["native_knee_motion_without_root_m"][side] for item in measurements)
             for side in ("L", "R")}
    required_sides = () if case == "turn" else (("L",) if case == "leg_raise" else ("L", "R"))
    body = max(item["native_body_rig_frame_motion_m"] for item in measurements)
    root = max(item["native_rig_translation_m"] for item in measurements)
    waist = max(item["native_waist_translation_m"] for item in measurements)
    rotations = {name: max(item["native_" + name + "_rotation_rad"] for item in measurements)
                 for name in ("rig", "waist")}
    result["native_input_response"] = {"required_leg_sides": list(required_sides),
        "evaluated_knee_max_motion_without_root_m": knees, "evaluated_body_max_rig_frame_motion_m": body,
        "evaluated_root_max_translation_m": root, "evaluated_waist_max_translation_m": waist,
        "evaluated_max_rotation_rad": rotations, "minimum_response_m": threshold,
        "threshold_provenance": "validate_real_dress.py summarize_motion: 1% native Body Rest height times scene metres/unit",
        "body_measurement": "Actual registered evaluated Body vertices in normalized rigid Rig axes; root translation/rotation removed, physical distance retained"}
    if required_sides:
        motion_check(result, qa, "representative_native_leg_inputs_reach_evaluated_bones",
                     all(knees[side] > threshold for side in required_sides),
                     required_sides=list(required_sides), maximum_knee_motion_m=knees, minimum_response_m=threshold)
        motion_check(result, qa, "representative_native_leg_input_reaches_actual_body_skin", body > threshold,
                     maximum_body_motion_without_root_m=body, minimum_response_m=threshold)
    if case in {"walk", "run", "abrupt_stop", "abrupt_stop_turn", "squat"}:
        motion_check(result, qa, "representative_root_translation_reaches_evaluated_rig_and_waist",
                     root > threshold and waist > threshold,
                     root_translation_m=root, waist_translation_m=waist, minimum_response_m=threshold)
    if case in {"turn", "abrupt_stop_turn"}:
        expected = abs(qa.representative_values(case, 1., height)[1]) if case == "turn" else math.radians(90.)
        # Native angular roundoff uses the existing 5e-6 numerical guard. A
        # Waist on the turn axis may have no translation at all.
        motion_check(result, qa, "representative_turn_reaches_evaluated_rig_and_waist_rotation",
                     expected > 0. and all(value >= expected-NATIVE_WORLD_LIMIT for value in rotations.values()),
                     expected_authored_yaw_rad=expected, evaluated_max_rotation_rad=rotations,
                     native_roundoff_guard_rad=NATIVE_WORLD_LIMIT, translation_response_required=case == "abrupt_stop_turn")


def motion_quality_summary(case, args, measurements, samples, peak, result):
    """Bounded final-surface diagnostics; separate from mechanism/visual acceptance."""
    checks = []
    def quality(name, passed, **facts):
        require(passed is None or type(passed) is bool, "Quality evidence must distinguish pass/fail/unproven")
        checks.append({"name": name, "passed": passed, **facts})

    worst_edge = max(measurements, key=lambda item: item["final_max_edge_ratio_to_frame1"], default=None)
    final_ratio = worst_edge["final_max_edge_ratio_to_frame1"] if worst_edge else None
    connected = bool(measurements) and all(item["final_edge_connectivity_exact"] for item in measurements)
    ratio_complete = connected and all(item["final_positive_reference_edges"] > 0 for item in measurements)
    quality("final_surface_neighbor_continuity", final_ratio <= args.max_edge_ratio if ratio_complete else None,
            maximum_ratio=final_ratio, worst_frame=worst_edge["frame"] if worst_edge else None,
            diagnostic_limit=args.max_edge_ratio,
            definition="Final evaluated3040 native edge connectivity and lengths relative to frame1; old diagnostic max_edge_ratio=3, not artistic contour acceptance")

    hem_complete = bool(measurements) and all(item["final_hem_identity_complete"] for item in measurements)
    result["final_waist_frame_motion"] = {
        "frame_count": len(measurements), "hem_identity_complete": hem_complete,
        "hem_vertices": measurements[0]["final_free_hem_vertices"] if measurements else None,
        "maximum_hem_step_m": max((item["final_hem_waist_step_max_m"] for item in measurements
                                    if item["final_hem_waist_step_max_m"] is not None), default=None),
        "maximum_hem_displacement_from_frame1_m": max((item["final_hem_waist_from_frame1_max_m"] for item in measurements
                                                        if item["final_hem_waist_from_frame1_max_m"] is not None), default=None),
        "definition": "Actual final free hem in normalized orthogonal evaluated Waist world axes; no inverse scale, physical metres retained",
        "dragging_acceptance": "UNPROVEN: displacement alone does not establish appropriate leg/skirt response; inspect real worst-frame views and trajectory"}
    worst_tail = None
    tail_rejected = False
    if case in {"abrupt_stop", "abrupt_stop_turn"}:
        tail = measurements[-10:]
        complete = hem_complete and len(tail) == 10 and all(item["final_hem_waist_step_max_m"] is not None for item in tail)
        jitter = max((item["final_hem_waist_step_max_m"] for item in tail
                      if item["final_hem_waist_step_max_m"] is not None), default=None)
        stopped = all(item["synthetic_input_stopped"] for item in tail)
        worst_tail = max((item for item in tail if item["final_hem_waist_step_max_m"] is not None),
                         key=lambda item: item["final_hem_waist_step_max_m"], default=None)
        tail_rejected = bool(complete and stopped and jitter > args.max_stop_jitter_mm/1000.)
        quality("final_free_hem_stop_tail_settling", jitter <= args.max_stop_jitter_mm/1000. if complete and stopped else None,
                frames=[item["frame"] for item in tail], maximum_m_per_frame=jitter,
                worst_step_frame=worst_tail["frame"] if worst_tail else None,
                diagnostic_limit_m_per_frame=args.max_stop_jitter_mm/1000., native_free_hem_complete=complete,
                authored_inputs_stopped=stopped, threshold_provenance="Existing validate_real_dress.py default 1mm/frame",
                limitation="Last ten frames only; does not establish long-run equilibrium or visual acceptance")

    colliders = {}
    signed_complete = bool(samples)
    worst = None
    for sample in samples:
        signed_complete = signed_complete and sample["final_weight_layer_complete"] and sample["final_free_vertices"] > 0
        signed_complete = signed_complete and len(sample["old3"]) == 3
        for entry in sample["old3"]:
            metric = entry["final_free_vertices"]
            value = metric["maximum_penetration_m"]
            measured = (metric["sampled_vertices"] > 0 and math.isfinite(value)
                        and math.isfinite(metric["minimum_signed_distance_m"]))
            signed_complete = signed_complete and measured
            summary = colliders.setdefault(entry["object"], {"role": entry["role"], "sampled_frames": [],
                        "maximum_penetration_m": None, "worst_frame": None, "minimum_sampled_vertices": None})
            summary["sampled_frames"].append(sample["frame"])
            if measured:
                if summary["maximum_penetration_m"] is None or value > summary["maximum_penetration_m"]:
                    summary["maximum_penetration_m"], summary["worst_frame"] = value, sample["frame"]
                summary["minimum_sampled_vertices"] = min(summary["minimum_sampled_vertices"] or metric["sampled_vertices"], metric["sampled_vertices"])
                if worst is None or value > worst["penetration_m"]:
                    worst = {"frame": sample["frame"], "object": entry["object"], "role": entry["role"], "penetration_m": value}
    roles = {entry["role"] for entry in colliders.values()}
    signed_complete = signed_complete and len(colliders) == 3 and {"leg.L", "leg.R"} <= roles
    signed_complete = signed_complete and all(len(entry["sampled_frames"]) == len(samples) for entry in colliders.values())
    limit = args.max_penetration_mm/1000.
    rejected = worst is not None and worst["penetration_m"] > limit
    signed_passed = False if rejected else (True if signed_complete else None)
    quality("sampled_final_free_closed_collider_penetration", signed_passed,
            diagnostic_limit_m=limit, threshold_provenance="Existing validate_real_dress.py default 2mm, converted mm/1000",
            worst=worst, complete=signed_complete, frames=[entry["frame"] for entry in samples],
            limitation="Final evaluated free vertices against three proved closed owned colliders at declared samples; not whole Body/triangle/time separation")
    result["signed_final_collider_summary"] = {"passed": signed_passed, "colliders": colliders,
                                             "worst": worst, "diagnostic_limit_m": limit, "complete": signed_complete}

    moving = []
    body_complete = bool(samples)
    uncertain_contacts = 0
    for sample in samples:
        body = sample["final_body"]
        counts = sample["final_body_contact_classification"]["counts"]
        dynamic = counts["moving_free_leg_crossings"] + counts["moving_free_other_body_crossings"]
        if dynamic:
            moving.append({"frame": sample["frame"], "moving_free_strict_pairs": dynamic, "counts": counts})
        uncertain_contacts += counts["baseline_or_stationary_free_contacts"] + counts["baseline_unproven_free_contacts"]
        body_complete = body_complete and body.get("status") == "measured" and sample["body_weight_layer_complete"]
        body_complete = body_complete and sample["final_body_contact_classification"]["baseline_coverage_complete"]
        body_complete = body_complete and sample["final_weight_layer_complete"] and sample["final_free_vertices"] > 0
        body_complete = body_complete and all(type(body.get(name + "_count")) is int and body[name + "_count"] == 0 for name in
                                              ("coplanar_unresolved", "degenerate_unresolved", "boundary_unresolved"))
    body_passed = False if moving else (True if body_complete and not uncertain_contacts else None)
    quality("sampled_new_moving_free_body_triangle_crossings", body_passed,
            moving_samples=moving, baseline_or_stationary_free_contacts=uncertain_contacts,
            measured_without_unresolved_pairs=body_complete,
            limitation="Fixed waist transition contacts classified separately; existing free contacts remain Unproven. Zero new strict crossings does not prove Body volume separation, especially an open Body")

    if moving and (worst is None or worst["penetration_m"] <= limit):
        render = {"frame": max(moving, key=lambda item: item["moving_free_strict_pairs"])["frame"],
                  "reason": "worst_sampled_new_moving_free_body_strict_crossing_count"}
    elif rejected:
        render = {"frame": worst["frame"], "reason": "worst_sampled_final_free_signed_collider_penetration", **worst}
    elif ratio_complete and final_ratio > args.max_edge_ratio:
        render = {"frame": worst_edge["frame"], "reason": "worst_final_surface_neighbor_edge_ratio",
                  "maximum_ratio": final_ratio}
    elif tail_rejected:
        render = {"frame": worst_tail["frame"], "reason": "worst_final_free_hem_stop_tail_step",
                  "maximum_step_m": jitter,
                  "limitation": "A single still frame locates the measured step; it cannot establish visual settling or jitter acceptance"}
    elif worst is not None and worst["penetration_m"] > 0.:
        render = {"frame": worst["frame"], "reason": "worst_sampled_final_free_signed_collider_penetration", **worst}
    else:
        render = {"frame": peak, "reason": "cloth_effect_peak_no_observed_positive_signed_or_new_moving_strict_crossing",
                  "collision_coverage_complete": signed_complete and body_complete}
    quality_status = "REJECTED_BY_BOUNDED_DIAGNOSTIC" if any(entry["passed"] is False for entry in checks) else (
        "UNPROVEN" if any(entry["passed"] is None for entry in checks) else "BOUNDED_DIAGNOSTICS_PASS_VISUAL_REVIEW_REQUIRED")
    result["effect_quality"] = {"status": quality_status, "checks": checks,
        "bounded_diagnostics_passed": all(entry["passed"] is True for entry in checks),
        "thresholds": {"sampled_signed_penetration_m": limit, "final_stop_hem_step_m": args.max_stop_jitter_mm/1000.,
                       "final_edge_ratio": args.max_edge_ratio},
        "visual_acceptance": "PENDING_HUMAN_REVIEW", "long_run_settling_acceptance": "UNPROVEN",
        "whole_body_separation_acceptance": "UNPROVEN", "render_selection": render}
    # This is whole-motion collision acceptance, not an optimistic label for a
    # few collider samples. Known defects reject; incomplete volume/time proof
    # remains explicit unknown even when bounded diagnostics all pass.
    result["collision_acceptance"] = False if signed_passed is False or body_passed is False else None
    result["collision_acceptance_scope"] = "Whole-body/whole-motion acceptance is Unproven; consult separate bounded final-surface diagnostics"
    return render


def motion_case(case, args, source_name, qa, diag, surface):
    from character_designer import skirt as skirt_ui
    output = args.output / "cases" / case
    output.mkdir(parents=True)
    result = {"name": case, "success": False, "mechanism_success": False,
              "success_scope": "Native mechanics/input response only; effect_quality and actual visual review are separate gates",
              "checks": [], "frames": args.frames,
              "production_effect_accepted": False, "collision_acceptance": None,
              "sampled_frames_only": True, "body_inside_outside_proven": False}
    began = time.perf_counter()
    input_probe = None
    action_name = None
    try:
        native_open = bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
        require("FINISHED" in native_open, "Installed QA open failed")
        source, rig, saved = qa.owned_source(source_name)
        protection = qa.Protection()
        initial_inventory = inventory()
        state = motion_state(qa, surface, source, rig)
        record, rig, actual, cloth, neutral = motion_objects(source, qa, surface)
        state["cache_range"] = [cloth.point_cache.frame_start, cloth.point_cache.frame_end, cloth.point_cache.frame_step]
        state["cache_filepath"] = cloth.point_cache.filepath
        state["cache_library_path"] = cloth.point_cache.use_library_path
        cache_preflight = qa.saved_cache_preflight(source, record)
        require(cache_preflight["allowed"], "Installed QA has a pre-existing cache not owned by this motion run")
        result["saved_cache_preflight"] = cache_preflight
        candidate = output / ("Cosha_Dress_QA_motion_" + case + ".blend")
        qa.save_candidate(candidate, args.input)
        scene = bpy.context.scene
        scene.tool_settings.use_keyframe_insert_auto = False
        owners = list(bpy.data.objects) + list(bpy.data.shape_keys)
        backup = qa.backup_animation(scene, owners, tuple(bpy.data.actions))
        qa.skirt._activate(bpy.context, rig, "POSE")
        qa.public_switch(bpy.ops.character_designer.body_ik_fk_switch, mode="FK")
        legs, axes, height = qa.body_inputs(rig, record)
        channels, basis = qa.pose_channels(rig), rig.matrix_basis.copy()
        action = author_motion_input(case, rig, legs, axes, channels, basis, height, args.frames, qa)
        action_name = action.name
        result["synthetic_action"] = {"name": action_name, "sha256": qa.digest(qa.action_content(action)),
            "description": "Synthetic representative stress input, not an imported, foot-planted or production animation",
            "input_origin": "Owning X QA explicit synthetic formula with frozen native Action authoring" if case in {"run", "abrupt_stop_turn"} else "Frozen representative formula",
            "real_imported_clip": False}
        if case == "run":
            result["synthetic_action"]["run_definition"] = {
                "cycles_over_requested_frame_window": 4., "root_forward_body_height_multiple": .9,
                "root_vertical_body_height_amplitude": .012, "thigh_swing_degrees": 35.,
                "shin_positive_swing_bend_degrees": -50., "foot_swing_degrees": 10.,
                "rotation_axis": "MainRig local X converted through frozen qa.body_inputs into each native source bone local space",
                "fps_and_speed_claim": "Phase-normalized stress input only; a longer requested frame window lowers cycle frequency",
                "limitation": "No foot contacts, flight-phase authenticity, imported gait fidelity or runtime/Unity acceptance"}
        elif case == "abrupt_stop_turn":
            result["synthetic_action"]["stop_turn_definition"] = {
                "advance_and_alternating_legs": "Exact frozen abrupt_stop formula, including its smooth gait fade",
                "translation_and_gait_stop_phase": .55, "root_local_z_turn_interval": [.55, .65],
                "root_turn_degrees": 90., "all_authored_inputs_fully_stopped_phase": .65,
                "first_fully_stopped_frame": math.ceil(.65 * (args.frames - 1)) + 1,
                "last_ten_frames": list(range(args.frames - 9, args.frames + 1)),
                "last_ten_after_full_stop": (args.frames - 10) / (args.frames - 1) > .65,
                "limitation": "Synthetic stop/turn stress only; no planted feet, imported locomotion clip or long-run acceptance"}
            require(result["synthetic_action"]["stop_turn_definition"]["last_ten_after_full_stop"],
                    "The combined stop-turn window does not leave all last ten frames after full input stop")
        scene.frame_start, scene.frame_end = 1, args.frames
        cloth.point_cache.frame_start, cloth.point_cache.frame_end, cloth.point_cache.frame_step = 1, args.frames, 1
        bpy.context.window_manager.character_designer_skirt.source = source
        bpy.context.window_manager.character_designer_skirt.use_scene_range = True
        qa.tuning.apply(bpy.context, (source,), mode="AUTOMATIC")
        # Save the unique candidate BEFORE enabling its private cache.
        qa.save_candidate(candidate, args.input)
        cache_dir = output / "native_cache"
        cache_dir.mkdir()
        cloth.point_cache.filepath = str(cache_dir)
        cloth.point_cache.use_library_path = False
        cloth.point_cache.use_disk_cache = True
        require(not cloth.point_cache.use_external and Path(bpy.path.abspath(cloth.point_cache.filepath)).resolve() == cache_dir.resolve(),
                "Native cache path is not the explicit QA-owned directory")
        result["cache_ownership"] = {"candidate": str(candidate), "explicit_native_filepath": str(cache_dir),
            "use_external": False, "policy": "Candidate first saved in its unique directory; no input/artist cache is reset or enumerated"}
        body, body_status = qa.registered_body(bpy.context, rig, args)
        require(body is not None and body_status["measured"], "The exact registered Body input is unavailable")
        result["body"] = body_status
        pin_ids = complete_raw_partition(record["fit"]["rings"], 800)
        input_probe = motion_probe(actual, scene, "ARM Body Attachment Input", lambda modifier: modifier.type != "CLOTH")
        require([modifier.type for modifier in input_probe.modifiers] == ["ARMATURE", "SURFACE_DEFORM"]
                and input_probe.modifiers[1].is_bound and input_probe.modifiers[1].target == actual.modifiers[1].target,
                "The exact native Cloth input prefix was not preserved")
        meters = scene.unit_settings.scale_length
        require(math.isfinite(meters) and meters > 0., "Scene metres/unit must be finite and positive")
        guard = qa.geometry_guard(meters)
        result["units_to_metres"] = meters
        reference = {}
        measurements = []
        base_lengths = None
        base_edges = None
        previous_physical = None
        final_base_edges = None
        final_base_lengths = None
        previous_final_hem = None
        first_final_hem = None
        first_hem_ids = None
        native_baseline = None
        body_vertex_count = None
        qa.public_switch(bpy.ops.character_designer.dress_motion_reset)
        motion_check(result, qa, "public_reset_start_unbaked", scene.frame_current == 1 and not cloth.point_cache.is_baked)
        for frame in range(1, args.frames + 1):
            phase_began = time.perf_counter()
            scene.frame_set(frame)
            frame_set_seconds = time.perf_counter() - phase_began
            phase_began = time.perf_counter()
            graph = bpy.context.evaluated_depsgraph_get()
            graph_acquisition_seconds = time.perf_counter() - phase_began
            mesh_readback_seconds = {}
            phase_began = time.perf_counter()
            physical = qa.world_mesh(actual, graph)
            mesh_readback_seconds["C800"] = time.perf_counter() - phase_began
            phase_began = time.perf_counter()
            final = qa.world_mesh(source, graph, record["controls"]["waist"],
                                  [chain["def"][-1] for chain in record["chains"]])
            mesh_readback_seconds["O3040"] = time.perf_counter() - phase_began
            phase_began = time.perf_counter()
            prefix = qa.world_mesh(input_probe, graph)
            mesh_readback_seconds["current_prefix800"] = time.perf_counter() - phase_began
            phase_began = time.perf_counter()
            body_mesh = qa.world_mesh(body, graph)
            mesh_readback_seconds["Body"] = time.perf_counter() - phase_began
            require(len(physical["points"]) == len(prefix["points"]) == 800 and len(final["points"]) == 3040,
                    "Raw800/final3040 evaluated layout changed")
            require(all(qa.finite(mesh["points"]) for mesh in (physical, final, prefix, body_mesh)), "Nonfinite evaluated motion geometry")
            if body_vertex_count is None:
                body_vertex_count = len(body_mesh["points"])
            require(0 < len(body_mesh["points"]) == body_vertex_count <= args.body_vertex_limit,
                    "Registered evaluated Body vertex layout/budget changed")
            evaluated = rig.evaluated_get(graph)
            root_frame = rigid_frame(evaluated.matrix_world)
            waist_frame = rigid_frame(evaluated.matrix_world @ evaluated.pose.bones[record["controls"]["waist"]].matrix)
            knee_heads = {side: evaluated.pose.bones[entry["chain"][1]].head.copy() for side, entry in legs.items()}
            body_local = rigid_points(body_mesh["points"], root_frame)
            if native_baseline is None:
                native_baseline = {"root": root_frame, "waist": waist_frame, "knees": knee_heads, "body": body_local}
            native = {
                "native_knee_motion_without_root_m": {side: (evaluated.matrix_world.to_3x3() @
                    (point-native_baseline["knees"][side])).length*meters for side, point in knee_heads.items()},
                "native_body_rig_frame_motion_m": point_error(body_local, native_baseline["body"], meters),
                "native_body_vertices": body_vertex_count,
                "native_rig_translation_m": (root_frame["origin"]-native_baseline["root"]["origin"]).length*meters,
                "native_waist_translation_m": (waist_frame["origin"]-native_baseline["waist"]["origin"]).length*meters,
                "native_rig_rotation_rad": root_frame["rotation"].rotation_difference(native_baseline["root"]["rotation"]).angle,
                "native_waist_rotation_rad": waist_frame["rotation"].rotation_difference(native_baseline["waist"]["rotation"]).angle,
                "native_waist_world_origin": list(waist_frame["origin"]),
                "native_waist_normalized_world_axes": [list(axis) for axis in waist_frame["axes"]]}
            require(all(math.isfinite(value) for value in native["native_knee_motion_without_root_m"].values())
                    and all(math.isfinite(native[name]) for name in ("native_body_rig_frame_motion_m",
                        "native_rig_translation_m", "native_waist_translation_m", "native_rig_rotation_rad", "native_waist_rotation_rad")),
                    "Nonfinite native evaluated input response")
            pin_error = point_error([physical["points"][index] for index in pin_ids],
                                    [prefix["points"][index] for index in pin_ids], meters)
            if base_edges is None:
                base_edges = physical["edges"]
                base_lengths = qa.edge_lengths(physical["points"], base_edges)
            require(physical["edges"] == base_edges, "Cloth edge topology/order changed during playback")
            step = point_error(physical["points"], previous_physical, meters) if previous_physical is not None else 0.
            if final_base_edges is None:
                final_base_edges = final["edges"]
                final_base_lengths = qa.edge_lengths(final["points"], final_base_edges)
            final_connectivity = final["edges"] == final_base_edges
            require(final_connectivity, "Final evaluated Dress edge connectivity/order changed during playback")
            free_ids = set(final["free_indices"])
            hem_ids = [index for index in final["hem_indices"] if index in free_ids]
            if first_hem_ids is None:
                first_hem_ids = hem_ids
            hem_complete = bool(hem_ids) and final["weights_available"] and hem_ids == first_hem_ids
            hem = rigid_points([final["points"][index] for index in hem_ids], waist_frame) if hem_complete else None
            if first_final_hem is None and hem is not None:
                first_final_hem = hem
            hem_step = point_error(hem, previous_final_hem, meters) if hem is not None and previous_final_hem is not None else None
            hem_rms = math.sqrt(sum((point-old).length_squared for point, old in zip(hem, previous_final_hem))/len(hem))*meters \
                      if hem is not None and previous_final_hem is not None else None
            hem_from_start = point_error(hem, first_final_hem, meters) if hem is not None and first_final_hem is not None else None
            reference[frame] = {"physical": qa.pack(physical["points"]), "final": qa.pack(final["points"])}
            measurements.append({"frame": frame, "waist_hard_pin_max_m": pin_error,
                                 "native_timing_segments": {
                                     "frame_set_seconds": frame_set_seconds,
                                     "depsgraph_acquisition_seconds": graph_acquisition_seconds,
                                     "world_mesh_readback_seconds_by_surface": mesh_readback_seconds,
                                     "scope": "Direct phase timings in sequential playback; depsgraph acquisition excludes an explicit view-layer update. Readback includes realization/extraction/cleanup; not GUI FPS."},
                                 **native,
                                 "physical_world_max_step_m": step,
                                 "physical_max_edge_ratio_to_frame1": qa.edge_ratio(physical["points"], base_edges, base_lengths),
                                 "final_edge_connectivity_exact": final_connectivity,
                                 "final_edges": len(final_base_edges),
                                 "final_positive_reference_edges": sum(length > 1.e-10 for length in final_base_lengths),
                                 "final_max_edge_ratio_to_frame1": qa.edge_ratio(final["points"], final_base_edges, final_base_lengths),
                                 "final_free_vertices": len(free_ids), "final_free_hem_vertices": len(hem_ids),
                                 "final_hem_identity_complete": hem_complete,
                                 "final_hem_waist_step_max_m": hem_step, "final_hem_waist_step_rms_m": hem_rms,
                                 "final_hem_waist_from_frame1_max_m": hem_from_start,
                                 "synthetic_input_stopped": (case == "abrupt_stop" and (frame-1)/(args.frames-1) >= .55)
                                     or (case == "abrupt_stop_turn" and (frame-1)/(args.frames-1) >= .65),
                                 "cloth_vs_current_native_prefix_max_m": point_error(physical["points"], prefix["points"], meters)})
            previous_physical = physical["points"]
            previous_final_hem = hem
            if frame % 10 == 0 or frame == args.frames:
                print(f"CD actual motion {case}: sequential {frame}/{args.frames}", flush=True)
        result["all_frame_measurements"] = measurements
        result["final_edge_reference"] = {"edges": len(final_base_edges), "connectivity_sha256": qa.digest(final_base_edges),
                                          "positive_reference_edges": sum(length > 1.e-10 for length in final_base_lengths)}
        native_input_summary(case, args, measurements, height, meters, result, qa)
        if case in {"abrupt_stop", "abrupt_stop_turn"}:
            result["stop_last10_observation"] = {"frames": [item["frame"] for item in measurements[-10:]],
                "maximum_physical_world_step_m": max(item["physical_world_max_step_m"] for item in measurements[-10:]),
                "limitation": "World-coordinate vertex displacement in this ten-frame tail only; not long-run equilibrium or a jitter acceptance threshold"}
            if case == "abrupt_stop_turn":
                tail = measurements[-10:]
                result["stop_last10_observation"].update({
                    "all_authored_inputs_stopped": all(item["synthetic_input_stopped"] for item in tail),
                    "evaluated_rotation_magnitude_from_frame1_range_rad": {name: [
                        min(item["native_" + name + "_rotation_rad"] for item in tail),
                        max(item["native_" + name + "_rotation_rad"] for item in tail)] for name in ("rig", "waist")},
                    "evaluated_waist_position_span_m": max((Vector(item["native_waist_world_origin"])
                        - Vector(tail[0]["native_waist_world_origin"])).length * meters for item in tail),
                    "evaluated_waist_normalized_axis_span": max((Vector(axis) - Vector(old)).length
                        for item in tail for axis, old in zip(item["native_waist_normalized_world_axes"],
                                                           tail[0]["native_waist_normalized_world_axes"])),
                    "scope": "Actual evaluated Rig/Waist rotation and Waist rigid frame during fully held synthetic input; final hem settling is separately bounded"})
                motion_check(result, qa, "combined_stop_turn_last_ten_after_full_authored_input_stop",
                             result["stop_last10_observation"]["all_authored_inputs_stopped"],
                             frames=[item["frame"] for item in tail], all_input_stop_phase=.65)
        motion_check(result, qa, "all_frames_finite_counts_and_hard_pin", max(item["waist_hard_pin_max_m"] for item in measurements) <= guard,
                     frames=args.frames, physical_count=800, final_count=3040, hard_pin_count=len(pin_ids), guard_m=guard,
                     hard_pin_max_m=max(item["waist_hard_pin_max_m"] for item in measurements))
        effect = max(item["cloth_vs_current_native_prefix_max_m"] for item in measurements)
        motion_check(result, qa, "actual_cloth_has_nonzero_motion_effect", effect > 1.e-5, maximum_m=effect)
        peak = max(measurements, key=lambda item: item["cloth_vs_current_native_prefix_max_m"])["frame"]
        sample_frames = sorted({1, 7, 25, 30, peak, args.frames})
        sample_frames = sorted(set(sample_frames) | {
            max(measurements, key=lambda item: item["final_max_edge_ratio_to_frame1"])["frame"]})
        if case in {"abrupt_stop", "abrupt_stop_turn"}:
            tail_steps = [item for item in measurements[-10:] if item["final_hem_waist_step_max_m"] is not None]
            if tail_steps:
                sample_frames = sorted(set(sample_frames) | {
                    max(tail_steps, key=lambda item: item["final_hem_waist_step_max_m"])["frame"]})
        result["critical_frames"] = sample_frames
        qa.public_switch(bpy.ops.character_designer.dress_motion_reset)
        maximum = {"physical": 0., "final": 0.}
        for frame in range(1, args.frames + 1):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            for key, obj in (("physical", actual), ("final", source)):
                maximum[key] = max(maximum[key], qa.packed_error(reference[frame][key], qa.world_mesh(obj, graph)["points"], meters))
        motion_check(result, qa, "public_reset_sequential_replay", max(maximum.values()) <= guard, maximum_error_m=maximum, guard_m=guard)
        native_bake = bpy.ops.character_designer.skirt_bake_physics("EXEC_DEFAULT")
        motion_check(result, qa, "public_bake_native_FINISHED_and_sealed", "FINISHED" in native_bake and cloth.point_cache.is_baked
                     and qa.skirt.read_record(source)["physics"]["baked_range"] == [1, args.frames]
                     and not skirt_ui._ACTIVE_BAKES,
                     native_result=sorted(native_bake), native_cache=qa.cache_state(cloth), registered_modal_bakes=len(skirt_ui._ACTIVE_BAKES))
        native_cache_files = sorted(path for path in output.rglob("*.bphys") if path.is_file())
        motion_check(result, qa, "private_QA_native_disk_cache_written", bool(native_cache_files)
                     and all(path.resolve().is_relative_to(output.resolve()) for path in native_cache_files),
                     file_count=len(native_cache_files), candidate_path=str(candidate), native_filepath=cloth.point_cache.filepath)
        result["cache_ownership"]["observed_native_cache_files"] = [{"path": str(path), **qa.file_state(path)} for path in native_cache_files]
        result["cache_ownership"]["filepath_scope"] = "Configured RNA path is recorded; observed .bphys locations establish the actual QA-local writes, including native blendcache fallback"
        order = list(dict.fromkeys([args.frames, 1, 25, 7, 30, peak, args.frames]))
        def seeks(objects):
            errors = {"physical": 0., "final": 0.}
            for frame in order:
                bpy.context.scene.frame_set(frame)
                graph = bpy.context.evaluated_depsgraph_get()
                for key, obj in objects:
                    errors[key] = max(errors[key], qa.packed_error(reference[frame][key], qa.world_mesh(obj, graph)["points"], meters))
            return errors
        errors = seeks((("physical", actual), ("final", source)))
        motion_check(result, qa, "sealed_cache_random_seek", max(errors.values()) <= guard, order=order, maximum_error_m=errors, guard_m=guard)
        result["sampled_collisions"] = []
        collision_baseline = {}
        for frame in sample_frames:
            scene.frame_set(frame)
            item, final_mesh, body_mesh, bounds = motion_collision_sample(source, rig, actual, body,
                       qa.skirt.read_record(source), frame, args, qa, diag, meters, collision_baseline)
            result["sampled_collisions"].append(item)
        render_selection = motion_quality_summary(case, args, measurements, result["sampled_collisions"], peak, result)
        render_frame = render_selection["frame"]
        require(render_frame in sample_frames, "Render selection is outside measured critical frames")
        scene.frame_set(render_frame)
        if args.no_render:
            result["render"] = {"requested": False, "success": False, "status": "explicit_numerical_only"}
        else:
            require("--threads" in sys.argv and sys.argv[sys.argv.index("--threads") + 1] == "1",
                    "Motion render requires the root-owned child startup --threads 1")
            graph = bpy.context.evaluated_depsgraph_get()
            final_mesh, body_mesh = diag.mesh_snapshot(source, graph), diag.mesh_snapshot(body, graph)
            bounds = diag.framing(rig, qa.skirt.read_record(source), graph)
            render_dir = output / "render"
            render_dir.mkdir()
            result["render"] = diag.native_render(SimpleNamespace(frame=render_frame, output=render_dir), final_mesh, body_mesh, bounds)
            motion_check(result, qa, "actual_evaluated_critical_three_views", result["render"]["success"] is True
                         and result["render"]["frame"] == render_frame
                         and set(result["render"]["views"]) == {"front", "side", "back"},
                         selection=render_selection, actual_frame=render_frame,
                         visual_quality_accepted=False)
        result["visual_review"] = {"status": "NOT_GENERATED" if args.no_render else "PENDING_HUMAN_REVIEW",
                                   "render_selection": render_selection,
                                   "rendered_frames": [] if args.no_render else [render_frame],
                                   "unrendered_critical_frames": [frame for frame in sample_frames if args.no_render or frame != render_frame],
                                   "scope": "One actually evaluated critical frame in front/side/back; no whole-trajectory visual pass"}
        frozen_delta_tests(source, rig, actual, cloth, neutral, qa.skirt.read_record(source), args, result, qa, surface, meters)
        original_roundtrip(source, rig, actual, cloth, neutral, result, qa, surface, meters)
        from verify_actual_original_refinement import verify_sealed_original_refinement
        refinement = verify_sealed_original_refinement(source, rig, actual, cloth, neutral, body,
                     result, qa, surface, sys.modules[__name__], meters)
        motion_check(result, qa, "public_original_persistent_refinement_and_new_only_keys",
                     refinement["success"] and refinement["cleanup_complete"],
                     details=refinement,
                     scope="One real weighted Dress DEF, public Original/edit/Controls and three frames over sealed private cache")
        remove_motion_probe(input_probe)
        input_probe = None
        expected_inventory = {key: values.copy() for key, values in initial_inventory.items()}
        expected_inventory["actions"] = sorted(expected_inventory["actions"] + [action_name])
        motion_check(result, qa, "temporary_mesh_and_key_IDs_clean_before_save", inventory() == expected_inventory,
                     inventories_sha256={"expected": qa.digest(expected_inventory), "actual": qa.digest(inventory())})
        motion_check(result, qa, "original_raw_assets_rest_author_actions_preserved", protection.verify()["success"],
                     details=protection.verify())
        result["packed_references"] = {}
        for key in ("physical", "final"):
            values = array("f")
            for frame in range(1, args.frames + 1):
                values.extend(reference[frame][key])
            result["packed_references"][key] = {**qa.save_reference(output / (key + "_all_frames.float32"), values),
                "frames": list(range(1, args.frames + 1)), "vertices_per_frame": 800 if key == "physical" else 3040,
                "layout": "frame-major then exact native vertex index then world XYZ; no final-to-raw provenance inference"}
        scene.frame_set(25)
        result["asset_protection_before_sealed_save"] = protection.verify()
        require(result["asset_protection_before_sealed_save"]["success"], "Protected assets changed before sealed save")
        qa.save_candidate(candidate, args.input)
        result["sealed_candidate"] = {"path": str(candidate), **qa.file_state(candidate), "synthetic_action_retained_for_replay": True}
        cache_before_open = {key: value for key, value in qa.cache_state(cloth).items() if key != "pointer"}
        native_open = bpy.ops.wm.open_mainfile(filepath=str(candidate), load_ui=False, use_scripts=False)
        require("FINISHED" in native_open, "Sealed independent candidate reopen failed")
        source, rig, record = qa.owned_source(source_name)
        record, rig, actual, cloth, neutral = motion_objects(source, qa, surface)
        bpy.context.window_manager.character_designer_skirt.source = source
        motion_check(result, qa, "sealed_save_reopen_author_assets_preserved", protection.verify()["success"], details=protection.verify())
        errors = seeks((("physical", actual), ("final", source)))
        cache_after_open = {key: value for key, value in qa.cache_state(cloth).items() if key != "pointer"}
        motion_check(result, qa, "native_save_reopen_sealed_cache_and_seek", cloth.point_cache.is_baked
                     and cache_before_open == cache_after_open and max(errors.values()) <= guard,
                     maximum_error_m=errors, guard_m=guard, cache_before=cache_before_open, cache_after=cache_after_open)
        restore_motion_state(state, backup, source, rig, qa, surface, action_name)
        action_name = None
        details = protection.verify()
        motion_check(result, qa, "qa_animation_cleanup_original_assets_exact", details["success"], details=details)
        motion_check(result, qa, "original_ID_inventory_restored", inventory() == initial_inventory,
                     inventories_sha256={"expected": qa.digest(initial_inventory), "actual": qa.digest(inventory())})
        motion_check(result, qa, "original_context_channels_metadata_restored", context_content(bpy.context) == state["context"]
                     and qa.pose_channels(rig) == state["channels"] and source[qa.skirt.RECORD_KEY] == state["record"]
                     and source.get(state["correction_key"]) == state["correction"]
                     and source.get(qa.profiles.PROFILE_KEY) == state["profile"])
        clean = output / "Cosha_Dress_QA_motion_clean.blend"
        qa.save_candidate(clean, args.input)
        result["clean_candidate"] = {"path": str(clean), **qa.file_state(clean)}
        native = bpy.ops.wm.open_mainfile(filepath=str(clean), load_ui=False, use_scripts=False)
        require("FINISHED" in native, "Clean independent candidate reopen failed")
        source, rig, record = qa.owned_source(source_name)
        motion_objects(source, qa, surface)
        motion_check(result, qa, "clean_save_reopen_no_QA_IDs_and_author_assets_exact",
                     inventory() == initial_inventory and protection.verify()["success"], details=protection.verify())
        result["full_visual_coverage"] = not result["visual_review"]["unrendered_critical_frames"]
        result["mechanism_success"] = all(item["passed"] for item in result["checks"])
        result["success"] = result["mechanism_success"]
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        if input_probe is not None:
            try:
                remove_motion_probe(input_probe)
            except Exception as error:
                result["probe_cleanup_error"] = str(error)
        # Reload the sealed installed QA after failures as well. This never saves
        # input and discards only disposable in-process synthetic changes.
        try:
            native = bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
            require("FINISHED" in native, "Installed input cleanup reload failed")
            result["final_input_asset_protection"] = protection.verify() if "protection" in locals() else None
            require(result["final_input_asset_protection"] is not None and result["final_input_asset_protection"]["success"],
                    "Final installed input Protection failed")
        except Exception as error:
            result["success"] = False
            result["mechanism_success"] = False
            result["final_reload_error"] = str(error)
        result["elapsed_seconds"] = time.perf_counter() - began
        path = output / "motion_case.json"
        path.write_text(json.dumps(diag.json_content(result), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        result["report_path"] = str(path)
    return result


def motion_stage(args, report, qa, diag, surface, source_name):
    report["explicit_forward_replay"] = True
    report["cases"] = []
    for case in args.cases:
        result = motion_case(case, args, source_name, qa, diag, surface)
        report["cases"].append({"name": case, "success": result["success"], "report_path": result["report_path"],
                                "mechanism_success": result["mechanism_success"],
                                "effect_quality_status": result.get("effect_quality", {}).get("status", "UNPROVEN"),
                                "bounded_diagnostics_passed": result.get("effect_quality", {}).get("bounded_diagnostics_passed", False),
                                "visual_review_status": result.get("visual_review", {}).get("status", "NOT_GENERATED"),
                                "elapsed_seconds": result["elapsed_seconds"], "full_visual_coverage": result.get("full_visual_coverage", False)})
        motion_check(report, qa, "bounded_motion_" + case, result["success"], report_path=result["report_path"])
    qa.save_candidate(args.output / "scenes/Cosha_Dress_QA_motion_clean.blend", args.input)
    report["mechanism_success"] = all(case["mechanism_success"] for case in report["cases"])
    report["success_scope"] = "Native mechanics/input response only; effect diagnostics and actual visual review remain separate"
    report["effect_quality_summary"] = {
        "all_requested_bounded_diagnostics_passed": all(case["bounded_diagnostics_passed"] for case in report["cases"]),
        "rejected_cases": [case["name"] for case in report["cases"] if case["effect_quality_status"] == "REJECTED_BY_BOUNDED_DIAGNOSTIC"],
        "unproven_cases": [case["name"] for case in report["cases"] if case["effect_quality_status"] == "UNPROVEN"],
        "requested_cases": list(args.cases), "unexercised_cases": [case for case in CASES if case not in args.cases],
        "visual_acceptance": "PENDING_HUMAN_REVIEW" if not args.no_render else "NOT_GENERATED",
        "production_effect_accepted": False, "whole_body_separation_acceptance": "UNPROVEN",
        "long_run_settling_acceptance": "UNPROVEN"}
    report["full_visual_coverage"] = all(case["full_visual_coverage"] for case in report["cases"])


def main(args):
    # Fail before module registration, opening any file or creating output.
    isolation = {"background": bool(bpy.app.background), "factory_startup": "--factory-startup" in sys.argv,
                 "initial_filepath": bpy.data.filepath}
    require(isolation["background"] and isolation["factory_startup"] and not isolation["initial_filepath"],
            "Refusing workflow QA outside an empty factory background child")
    if args.stage == "motion" and not args.no_render:
        require("--threads" in sys.argv and sys.argv.index("--threads") + 1 < len(sys.argv)
                and sys.argv[sys.argv.index("--threads") + 1] == "1",
                "Root must start this rendering child with --threads 1")
    qa, diag, addon, surface = load_dependencies()
    report = {"success": False, "stage": args.stage, "production_effect_accepted": False,
              "artist_saved_by_verifier": False, "artist_path": str(args.input),
              "artist_before": qa.file_state(args.input), "isolated_process": isolation,
              "blender_version": bpy.app.version_string, "addon_version": list(addon.bl_info["version"]),
              "source_manifest_before": diag.source_manifest(), "harness_sha256": sha(Path(__file__)),
              "explicit_forward_replay": False, "checks": [],
              "limits": ["Saved artist file only; current unsaved live scene is not inspected",
                         "No forward 60-frame simulation, collision clearance, render or equilibrium claim",
                         "Native cold Cloth may evaluate during binding or dependency graph reads",
                         "Static source export capture is not a Cloth animation/FBX/Unity acceptance"]}
    if args.stage == "motion":
        report["mechanism_success"] = False
        report["success_scope"] = "Native mechanics/input response only; inspect separate effect_quality_summary and actual views"
        report["limits"] = ["Exact saved installation QA only; no live artist/Unity/GUI inspection or save",
                            "Frozen synthetic representative inputs; no production animation acceptance",
                            "Collision samples only at frames1/7/25/30, measured Cloth-effect/edge-ratio/stop-tail-step peaks and final frame",
                            "Open Body has no inside/outside proof; coplanar/boundary/degenerate intersections remain unresolved",
                            "Signed old3 free-vertex samples are not whole-surface separation",
                            "2mm penetration, 1mm/frame final hem settling and edge-ratio3 are existing bounded diagnostics, not artistic/visual/long-run acceptance",
                            "Three real views use a measured collision, edge-ratio or stop-step issue frame, otherwise Cloth-effect peak; other critical frames and temporal jitter remain unrendered",
                            "Manual/Key delta, reverted Original edit and one public persistent Original correction with three new-only keyed frames are bounded mechanics checks, not exhaustive authoring/export acceptance",
                            "Native cold Cloth can evaluate during loading/Reset; no zero-evaluation claim"]
    report["source_manifest_before"][str(Path(__file__).resolve())] = qa.file_state(Path(__file__))
    if args.stage == "motion":
        report["source_manifest_before"][str(HERE / "verify_actual_original_refinement.py")] = qa.file_state(
            HERE / "verify_actual_original_refinement.py")
    protection = None
    guards = {"upgrade": None}
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        source_name = motion_input_gate(args, report, qa, diag) if args.stage == "motion" else None
        addon.register()
        bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
        protection = qa.Protection()
        report["protected_original_inventory"] = protection.summary()
        if args.stage == "install":
            install_stage(args, report, qa, surface, protection, guards)
        else:
            require(args.source is None or args.source == source_name, "Explicit source disagrees with the installed exact source")
            source, rig, record = qa.owned_source(source_name)
            require(rig.name == report["install_input"]["rig"] and record["owner"] == report["install_input"]["owner"],
                    "Installed source/rig/owner changed")
            motion_objects(source, qa, surface)
            motion_stage(args, report, qa, diag, surface, source_name)
        report["success"] = all(check["passed"] for check in report["checks"])
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        if protection is not None:
            try:
                report["protected_original_after"] = protected(protection, original_replacement(report))
                report["success"] = report["success"] and report["protected_original_after"]["success"]
                if guards["upgrade"] is not None:
                    replaced = report.get("legacy_endpoint_replacement", {}).get("name") if report.get("replacement_committed") else None
                    report["protected_pre_upgrade_after"] = protected(guards["upgrade"], replaced)
                    report["success"] = report["success"] and report["protected_pre_upgrade_after"]["success"]
            except Exception as error:
                report["success"] = False
                report["protection_error"] = str(error)
        report["artist_after"] = qa.file_state(args.input)
        report["artist_disk_exact"] = report["artist_after"] == report["artist_before"]
        report["source_manifest_after"] = diag.source_manifest()
        report["source_manifest_after"][str(Path(__file__).resolve())] = qa.file_state(Path(__file__))
        if args.stage == "motion":
            report["source_manifest_after"][str(HERE / "verify_actual_original_refinement.py")] = qa.file_state(
                HERE / "verify_actual_original_refinement.py")
        report["canonical_and_frozen_code_exact"] = report["source_manifest_after"] == report["source_manifest_before"]
        report["success"] = report["success"] and report["artist_disk_exact"] and report["canonical_and_frozen_code_exact"]
        if args.stage == "motion":
            report["mechanism_success"] = report["success"]
        report["elapsed_seconds"] = time.perf_counter() - started
        destination = args.output / ("result/workflow_install.json" if args.stage == "install" else "result/workflow_motion.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(diag.json_content(report), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"success": report["success"], "stage": args.stage, "report": str(destination),
                          "elapsed_seconds": report["elapsed_seconds"]}, ensure_ascii=False), flush=True)
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
