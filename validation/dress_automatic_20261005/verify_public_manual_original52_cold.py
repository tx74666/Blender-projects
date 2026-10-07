"""Disposable7ac cold Manual/Original component, without timeline playback.

No QA Action, Dress Keys, new Cloth, old C geometry restoration or memory-payload
preservation is claimed. ActualSurface's unchanged contract excludes modifier
evaluation flags; its public Original service is tested with old Cloth paused.
All author RNA/assets, original public cache metadata and files retain their
existing finally/reload guards. This never opens or saves the artist file.
"""
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CANDIDATE = HERE / "verify_direct_main_manual_input52_node_ui.py"
CANDIDATE_SHA = "fe61357686cdb6ab43fd801c722e6b5eb60967cad23b22fd4e72d45579b681af"
INPUT_COMPONENT = HERE / "actual_direct_main_cache_policy_52_20261006_213910_924/result/input800_reproduction.json"
INPUT_COMPONENT_SHA = "b85cf133f3da0ecff893494f881fde3906f8840a01a44c21f7cf2d4990d88e55"
INPUT_COMPONENT_SCRIPT = HERE / "verify_direct_main_manual_input52_cache_policy.py"
INPUT_COMPONENT_SCRIPT_SHA = "fdb26dfcab5f4b490f37ebdcd34b55b6a8702604b185dceb896c050f6e227735"
INPUT_SHA = "7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f"
STAGE = "COLD_MANUAL_PUBLIC_ORIGINAL_52"
GEOMETRY_GUARD = 5.e-5
ACTION_LABELS = ["action_1_sequential", "action_2_sequential", "action_3_sequential", "action_4_sequential",
                 "action_5_sequential", "action_3_seek", "action_1_seek", "action_5_seek"]
ACTION_FRAMES = [1, 2, 3, 4, 5, 3, 1, 5]
COLD_LABELS = ["cold_Controls_baseline", "cold_Original_enter", "cold_Original_DEF_edit", "cold_Controls_return"]
TERMINAL_TRUE = ("owned_cleanup_exact", "Main_Rest_flags_pointers_before_reload_exact", "cache_metadata_exact",
                 "pose_after_reload_exact", "playback_after_reload_exact", "author_frame_after_reload_exact",
                 "canonical_validation_after_reload", "source_disk_exact", "input_artist_disk_exact",
                 "script_disk_exact", "frozen_pins_disk_exact")


def need(condition, message):
    if not condition:
        raise RuntimeError("Cold Manual52: " + message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""): digest.update(block)
    return digest.hexdigest()


def load_candidate():
    need(sha(CANDIDATE) == CANDIDATE_SHA and sha(INPUT_COMPONENT) == INPUT_COMPONENT_SHA
         and sha(INPUT_COMPONENT_SCRIPT) == INPUT_COMPONENT_SCRIPT_SHA, "Frozen input component/dependencies changed")
    spec = importlib.util.spec_from_file_location("cold_manual_frozen_direct52", CANDIDATE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _error(value, count, maximum):
    return (type(value) is dict and value.get("count") == count and _finite(value.get("maximum_m"))
            and _finite(value.get("rms_m")) and 0. <= value["rms_m"] <= value["maximum_m"] <= maximum)


def _terminal(report):
    need(type(report) is dict and all(report.get(name) is True for name in TERMINAL_TRUE)
         and report.get("cleanup_errors") == [] and report.get("source_before") == report.get("source_after")
         and bool(report.get("source_before")), "Incomplete/exact author/source cleanup proof")
    need(all(type(report.get(name)) is dict and report[name].get("success") is True
             for name in ("protection_before_reload", "protection_after_reload")), "Native reload protection missing")
    restore = report.get("live_author_restore")
    need(type(restore) is dict and restore.get("errors") == [] and all(restore.get(name) is True for name in
         ("constraint_pointers_and_RNA_exact", "raw_pose_exact", "id_properties_exact", "frame_exact", "cloth_flags_exact", "cache_exact")),
         "Complete author RNA restoration missing")
    install = report.get("install_input")
    need(type(install) is dict and install.get("candidate_sha256") == INPUT_SHA
         and report.get("geometry_guard_m") == GEOMETRY_GUARD and report.get("units_to_metres") == 1.,
         "Exact7ac/physical50um input identity missing")


def historical_dynamic_input_component(report):
    """Validate only the actual b85 input8/seek3 proof, retaining its C failure.

    It is never a completed Direct/Original/Cloth/old-cache-preservation proof.
    File SHA is enforced by the caller before passing this parsed value.
    """
    _terminal(report)
    need(report.get("stage") == "DIRECT_MAIN_MANUAL_INPUT_52_CACHE_POLICY"
         and report.get("script_sha256") == INPUT_COMPONENT_SCRIPT_SHA
         and report.get("native_completed") is False and report.get("ready_for_next_private_gate") is False
         and report.get("accepted") is False, "Historical failed component provenance/status differs")
    exception = report.get("exception")
    need(type(exception) is dict and exception.get("type") == "RuntimeError"
         and exception.get("message") == "DirectMain52: restored original sameframe C changed", "Unknown historical terminal failure")
    rows = report.get("direct_live_samples")
    need(type(rows) is list and len(rows) == 8 and [row.get("label") for row in rows] == ACTION_LABELS
         and [row.get("frame") for row in rows] == [[frame, 0.] for frame in ACTION_FRAMES], "Actual8 native sample/seek sequence missing")
    for row in rows:
        need(_error(row.get("before800_vs_native_Main_oracle"), 800, 0.)
             and _error(row.get("attachment_effect", {}).get("outside720"), 720, 0.), "Historical exact800/outside720 proof missing")
        quarantine = row.get("legacy_quarantine", {})
        need(quarantine.get("newCloth_or_feedback_exercised") is False and quarantine.get("oldC_flags") == [False, False]
             and len(quarantine.get("old_targets_retained", [])) == 32
             and all(item.get("evaluated_influence") == 0. for item in quarantine["old_targets_retained"])
             and len(quarantine.get("Body_group_proofs", {})) == 2
             and all(item.get("dress_group_intersection") == [] for item in quarantine["Body_group_proofs"].values()),
             "Historical Body/oldPHYS quarantine proof missing")
        summaries = row.get("mesh_summaries", {})
        need(set(summaries) == {"oracle", "before800", "after800"}
             and all(item.get("vertices") == 800 and item.get("finite") is True for item in summaries.values()), "Historical native coverage missing")
        cache = row.get("cache_transition", {})
        need(row.get("cache_exact") is False and cache.get("policy") == "KNOWN_INVALID_UNBAKED_MEMORY_52_V1"
             and cache.get("allowed") is True and cache.get("classification") == "KNOWN_INVALID_MEMORY_SUMMARY_DISCARDED"
             and cache.get("cache_content_preserved") is False, "Historical invalid-memory loss was not retained")
    replay = report.get("native_seek_replay")
    need(type(replay) is list and len(replay) == 3 and [row.get("frame") for row in replay] == [3, 1, 5]
         and all(set(row.get("errors", {})) == {"oracle", "before800", "after800"}
                 and all(_error(value, 800, 0.) for value in row["errors"].values()) for row in replay), "Native3 exact seek proof missing")
    response = report.get("live_Action_input_response", {})
    need(all(_finite(response.get(name)) and response[name] > GEOMETRY_GUARD for name in ("knee_1_3_m", "hem_1_3_m"))
         and all(type(response.get(name)) is dict and _finite(response[name].get("maximum_m"))
                 and response[name]["maximum_m"] > GEOMETRY_GUARD for name in ("native800_1_3", "registered_Body_1_3")), "Actual native Body/leg/Hem input response missing")
    loss = report.get("C_after_Action_restore_vs_before_pause")
    need(_error(loss, 800, math.inf) and loss["maximum_m"] > GEOMETRY_GUARD
         and report.get("cache_content_preserved") is False, "Historical real C-loss failure not retained")
    return {"component": "NATIVE_DIRECT_INPUT8_SEEK3_ONLY", "component_success": True, "native_samples": 8,
            "native_seek_replays": 3, "parent_report_native_completed": False,
            "parent_failure": exception["message"], "old_C_geometry_preserved": False, "cache_content_preserved": False,
            "public_Original_completed": False, "physics_or_ART_accepted": False, "accepted": False}


def completed_cold_component(report):
    """Require an actually completed cold component; not satisfied by b85."""
    _terminal(report)
    need(report.get("stage") == STAGE and report.get("script_sha256") == sha(Path(__file__))
         and report.get("native_completed") is True and report.get("ready_for_next_private_gate") is True
         and report.get("cold_public_manual_original_success") is True and "exception" not in report,
         "Actual completed cold component required")
    scope = report.get("cold_component_scope", {})
    need(scope.get("timeline_seek") is False and scope.get("QA_Action_created") is False
         and scope.get("new_Cloth") is False and scope.get("old_C_geometry_preservation_claimed") is False
         and scope.get("old_cache_memory_payload_preserved") == "Unknown", "Cold scope differs")
    rows = report.get("cold_manual_samples")
    need(type(rows) is list and [row.get("label") for row in rows] == COLD_LABELS
         and all(row.get("frame") == report.get("author_frame") and row.get("old_Cloth_flags") == [False, False]
                 and _error(row.get("before800_vs_native_Main_oracle"), 800, 0.)
                 and _error(row.get("attachment_effect", {}).get("outside720"), 720, 0.) for row in rows), "Cold same-frame exact input samples missing")
    need([row.get("original_active") for row in rows] == [False, True, True, False], "Actual public Original sequence missing")
    proof = report.get("cold_public_Original_geometry", {})
    need(all(_error(proof.get(name), count, GEOMETRY_GUARD) for name, count in
             (("enter800", 800), ("leave800", 800), ("enter_final3040", 3040), ("leave_final3040", 3040)))
         and all(_error(proof.get(name), count, math.inf) and proof[name]["maximum_m"] > GEOMETRY_GUARD
                 for name, count in (("edit800", 800), ("edit_final3040", 3040)))
         and proof.get("angle_rad") == .08 and proof.get("manual_mix_mode") == "BEFORE_FULL"
         and proof.get("persistent_correction_metadata") is True, "Actual visible cold edit/switch/correction proof missing")
    return {"component": STAGE, "component_success": True, "public_Original_completed": True,
            "physics_or_ART_accepted": False, "cache_payload_preserved": "Unknown", "accepted": False}


def paired_component_proof(cold_path, cold_sha, input_path, input_sha):
    for path, expected in ((cold_path, cold_sha), (input_path, input_sha)):
        need(type(expected) is str and len(expected) == 64 and all(c in "0123456789abcdef" for c in expected)
             and Path(path).is_file() and sha(path) == expected, "Pinned real component report required")
    need(Path(input_path).resolve() == INPUT_COMPONENT.resolve() and input_sha == INPUT_COMPONENT_SHA,
         "Only the actual reviewed b85 partial component may be reused")
    cold = json.loads(Path(cold_path).read_text(encoding="utf-8")); partial = json.loads(Path(input_path).read_text(encoding="utf-8"))
    first, second = completed_cold_component(cold), historical_dynamic_input_component(partial)
    need(cold["source_before"] == partial["source_before"], "Components do not use the same exact actual source manifest")
    need(sha(cold_path) == cold_sha and sha(input_path) == input_sha, "Component report changed while reading")
    return {"cold": first, "dynamic_input": second, "current_artist_protection_reused": False,
            "scope": "Disposable exact7ac components only; current artist integration/Cloth/ART/Keys/export unproved",
            "accepted": False}


def exercise_public_manual_original_cold(values, base):
    import bpy
    from mathutils import Quaternion, Vector
    source, rig, record, before, after, oracle, cloth, actual, clone, home, qa, diag, surface, same, read, report, write, budget, metres, guard, controls, manual, deform, upstream, waist, forbidden, ring, raw_contract, original_group_count = (
        values[key] for key in ("source", "rig", "record", "before", "after", "oracle", "cloth", "actual", "clone", "home", "qa", "diag", "surface", "same", "read", "report", "write", "budget", "metres", "guard", "controls", "manual", "deform", "upstream", "waist", "forbidden", "ring", "raw_contract", "original_group_count"))
    state = _CORE._STATE
    need((home.frame_current, home.frame_subframe) == state["frame"] and not cloth.show_viewport and not cloth.show_render,
         "Cold component must begin at untouched author frame with old Cloth paused")
    need(state["qa_action"] is None and (rig.animation_data is None or rig.animation_data.action is None), "No QA/active Action permitted in this cold component")
    need(base.key_values(source) is None, "Exact fixture Keys absent; no live Keys support is claimed")
    surface.validate(source, rig, qa.skirt.read_record(source))  # No flag waiver.
    report["stage"] = STAGE
    report["cold_component_scope"] = {"disposable_exact7ac": True, "timeline_seek": False, "QA_Action_created": False,
        "new_Cloth": False, "Dress_Keys_written": False, "old_Cloth_paused_throughout_public_Original": True,
        "old_C_geometry_preservation_claimed": False, "old_cache_memory_payload_preserved": "Unknown",
        "current_artist_loaded_saved_or_integrated": False, "automatic_Original_semantics_verified": False, "accepted": False}
    rows = []; identities = None; frozen_frame = (home.frame_current, home.frame_subframe)
    def sample(label):
        nonlocal identities
        budget(); started = __import__("time").perf_counter(); bpy.context.view_layer.update(); graph = bpy.context.evaluated_depsgraph_get()
        graph_seconds = __import__("time").perf_counter() - started
        need((home.frame_current, home.frame_subframe) == frozen_frame and not cloth.show_viewport and not cloth.show_render,
             "Cold public operation advanced time or enabled old Cloth")
        surface.validate(source, rig, qa.skirt.read_record(source))
        raw_program = _CORE.raw_source_program_guard(rig, deform)
        closure = state["closure"](source, rig, record, manual, controls, upstream+[waist], forbidden, graph, surface)
        quarantine = _DIRECT.quarantine_proof(source, rig, record, actual, clone, values["body"], cloth, graph, qa, surface)
        refs = _DIRECT.audit_direct((before, after), after.modifiers[1], values)
        meshes = {}; timing = {}
        for name, obj in (("oracle", oracle), ("before800", before), ("after800", after), ("visible_final3040", source)):
            began = __import__("time").perf_counter(); meshes[name] = read.native_mesh(obj, graph, diag)
            timing[name] = __import__("time").perf_counter() - began
            count = 3040 if name == "visible_final3040" else 800
            need(len(meshes[name]["points"]) == count and meshes[name]["native_vertex_index_order"] == list(range(count))
                 and qa.finite(meshes[name]["points"]), "Cold native evaluated coverage/index/finite gate failed")
        fields = ("native_vertex_index_order", "edges", "faces", "weights", "native_group_mapping")
        identity = {name: {field: mesh[field] for field in fields} for name, mesh in meshes.items() if name != "visible_final3040"}
        need(all(mesh["weights_complete"] for name, mesh in meshes.items() if name != "visible_final3040"), "Cold native800 weight coverage incomplete")
        if identities is None: identities = identity
        need(identity == identities, "Cold native800 mapping/weights drifted")
        raw_after = qa.raw_mesh_content(after); raw_after["groups"] = raw_after["groups"][:original_group_count]
        raw_after["weights"] = [[weight for weight in row if weight[0] < original_group_count] for row in raw_after["weights"]]
        need(qa.raw_mesh_content(before) == raw_contract and raw_after == raw_contract, "Cold author33groups/UV/weights/raw Keys changed")
        error = base.error_summary(meshes["before800"]["points"], meshes["oracle"]["points"], metres)
        effect = {"raw80": base.error_summary(meshes["after800"]["points"], meshes["before800"]["points"], metres, ring),
                  "outside720": base.error_summary(meshes["after800"]["points"], meshes["before800"]["points"], metres,
                      [index for index in range(800) if index not in set(ring)])}
        charts = {"before": base.native_world_copy_proof(meshes["before800"]["matrix_world"], source.evaluated_get(graph).matrix_world, "Cold before world"),
                  "after": base.native_world_copy_proof(meshes["after800"]["matrix_world"], actual.evaluated_get(graph).matrix_world, "Cold after world")}
        row = {"label": label, "frame": [home.frame_current, home.frame_subframe], "original_active": qa.original.active(rig),
            "old_Cloth_flags": [bool(cloth.show_viewport), bool(cloth.show_render)], "before800_vs_native_Main_oracle": error,
            "attachment_effect": effect, "charts": charts, "raw_source_program": raw_program, "current_manual_closure": closure,
            "legacy_quarantine": quarantine, "reference_audit": refs, "old_cache_metadata": same.cache_state(cloth, qa),
            "cache_payload_preserved": "Unknown", "native_timing_segments": {"graph_ready_seconds": graph_seconds,
                "readback_seconds": timing, "scope": "Native update/readback; not GUI FPS or solver-only"},
            "mesh_summaries": {name: same.summary(mesh["points"], qa) for name, mesh in meshes.items()}, "accepted": False}
        rows.append(row); report["cold_manual_samples"] = rows; write()
        need(error["maximum_m"] == 0. and effect["outside720"]["maximum_m"] <= guard, "Cold exact800/outside720 geometry gate failed")
        return {name: mesh["points"] for name, mesh in meshes.items()}
    baseline = sample(COLD_LABELS[0]); need(not qa.original.active(rig), "Cold baseline must be Controls")
    qa.skirt._activate(bpy.context, rig, "POSE")
    qa.public_switch(bpy.ops.character_designer.body_original_mode, action="ORIGINAL")
    need(qa.original.active(rig), "Public Original did not enter")
    entered = sample(COLD_LABELS[1])
    proof = {"enter800": base.error_summary(entered["before800"], baseline["before800"], metres),
             "enter_final3040": base.error_summary(entered["visible_final3040"], baseline["visible_final3040"], metres)}
    report["cold_public_Original_geometry"] = proof; write()
    need(all(value["maximum_m"] <= guard for value in proof.values()), "Cold public Original entry >50um")
    weighted = [name for name in sorted(deform) if any(source.vertex_groups[weight.group].name == name and weight.weight > 0.
                for vertex in source.data.vertices for weight in vertex.groups)]
    need(weighted, "No positively weighted original DEF")
    bone = rig.pose.bones[weighted[0]]; bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = Quaternion(bone.rotation_quaternion) @ Quaternion(Vector((1., 0., 0.)), .08)
    rig.update_tag(); bpy.context.view_layer.update(); edited = sample(COLD_LABELS[2])
    proof.update({"weighted_bone": bone.name, "angle_rad": .08,
        "edit800": base.error_summary(edited["before800"], entered["before800"], metres),
        "edit_final3040": base.error_summary(edited["visible_final3040"], entered["visible_final3040"], metres)})
    write(); need(proof["edit800"]["maximum_m"] > guard and proof["edit_final3040"]["maximum_m"] > guard,
                  "Real weighted Original edit did not affect native800/final3040")
    qa.public_switch(bpy.ops.character_designer.body_original_mode, action="CONTROLS")
    need(not qa.original.active(rig), "Public Controls did not return")
    returned = sample(COLD_LABELS[3])
    from character_designer import skirt_original_mode
    proof.update({"leave800": base.error_summary(returned["before800"], edited["before800"], metres),
        "leave_final3040": base.error_summary(returned["visible_final3040"], edited["visible_final3040"], metres),
        "manual_mix_mode": rig.pose.bones[bone.name].constraints["Skirt manual pose"].mix_mode,
        "persistent_correction_metadata": bool(source.get(skirt_original_mode.CORRECTIONS))})
    write(); need(proof["leave800"]["maximum_m"] <= guard and proof["leave_final3040"]["maximum_m"] <= guard
                  and proof["manual_mix_mode"] == "BEFORE_FULL" and proof["persistent_correction_metadata"], "Cold Controls return/correction failed")
    report["cold_public_manual_original_success"] = True
    report["before_attachment_reproduction_complete"] = report["native_completed"] = report["native_endpoint_index_identity_exact"] = True
    report["cache_content_preserved"] = "Unknown"
    values["endpoint_path"].write_text(json.dumps({"stage": STAGE, "samples": [{"label": row["label"], "frame": row["frame"],
        "mesh_summaries": row["mesh_summaries"]} for row in rows], "scope": "Compact cold geometry only; no old C/payload preservation", "accepted": False}, indent=2, allow_nan=False), encoding="utf-8")


def prepared_namespace(adapter, direct, core, base, protection_path, protection_sha):
    candidate = load_candidate()
    namespace = candidate.prepared_namespace(adapter, direct, core, base, protection_path, protection_sha)
    namespace["__file__"] = str(Path(__file__))
    namespace["PINS"].update({CANDIDATE: CANDIDATE_SHA, INPUT_COMPONENT: INPUT_COMPONENT_SHA,
                             INPUT_COMPONENT_SCRIPT: INPUT_COMPONENT_SCRIPT_SHA, Path(__file__): sha(Path(__file__))})
    function_globals = dict(globals()); function_globals.update(_CORE=core, _DIRECT=direct)
    exec(compile(inspect.getsource(exercise_public_manual_original_cold), str(Path(__file__)), "exec"), function_globals)
    namespace["exercise_direct"] = function_globals["exercise_public_manual_original_cold"]
    original_capture = namespace["capture_program"]
    def capture(*values):
        receipt = original_capture(*values)
        report = values[-1]; report["stage"] = STAGE
        report["historical_partial_input_component"] = {"path": str(INPUT_COMPONENT), "sha256": INPUT_COMPONENT_SHA,
            "proof": historical_dynamic_input_component(json.loads(INPUT_COMPONENT.read_text(encoding="utf-8")))}
        report["disposable_contract"] = {"old_b85_report_remains_failed": True,
            "old_C_geometry_preservation_tested": False, "old_cache_payload_preserved": "Unknown", "accepted": False}
        return receipt
    namespace["capture_program"] = capture
    need(namespace["main"].__globals__ is namespace and namespace["restore_program"] is core.restore_program,
         "Actual compiled Main/restore transport changed")
    return namespace


def pure_checks(args):
    candidate = load_candidate(); adapter = candidate.load_current(); direct = adapter.load_direct(); core = direct.load_core(); base = core.load_base()
    actual = json.loads(INPUT_COMPONENT.read_text(encoding="utf-8")); proof = historical_dynamic_input_component(actual)
    negatives = []
    for change in (lambda r: r.update(native_completed=True), lambda r: r.update(ready_for_next_private_gate=True),
                   lambda r: r["direct_live_samples"].pop(), lambda r: r["direct_live_samples"][0]["before800_vs_native_Main_oracle"].update(maximum_m=1.e-6),
                   lambda r: r["native_seek_replay"].pop(), lambda r: r["direct_live_samples"][0]["legacy_quarantine"]["old_targets_retained"][0].update(evaluated_influence=1.),
                   lambda r: r.update(cache_content_preserved=True), lambda r: r.update(cleanup_errors=[{}]),
                   lambda r: r["exception"].update(message="other"), lambda r: r.update(source_disk_exact=False)):
        altered = copy.deepcopy(actual); change(altered); negatives.append(altered)
    for value in negatives:
        try: historical_dynamic_input_component(value)
        except RuntimeError: pass
        else: need(False, "Historical partial-input negative accepted")
    try: completed_cold_component(actual)
    except RuntimeError: pass
    else: need(False, "Failed parent report cannot prove actual cold completion")
    source = inspect.getsource(exercise_public_manual_original_cold); tree = ast.parse(source)
    forbidden = {"frame_set", "keyframe_insert", "driver_add", "bake", "free_bake", "restore_channels"}
    need(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in forbidden for node in ast.walk(tree)),
         "Cold exercise contains forbidden timeline/key/cache API")
    need('actions.new' not in source and 'modifiers.new' not in source and 'initial_C' not in source,
         "Cold exercise claims timeline/simulation/C preservation")
    # Actual production proof, rather than an assumed flag allowance.
    surface_text = base.SURFACE.read_text(encoding="utf-8"); functions = {node.name: node for node in ast.parse(surface_text).body if isinstance(node, ast.FunctionDef)}
    helper = ast.get_source_segment(surface_text, functions["_helper_contract"])
    need('_rna(modifier, {"show_viewport", "show_render", "is_active"})' in helper,
         "ActualSurface paused-helper flag contract differs")
    physics_text = (base.REPOSITORY/"addons/character_designer/skirt_physics.py").read_text(encoding="utf-8")
    physics = {node.name: node for node in ast.parse(physics_text).body if isinstance(node, ast.FunctionDef)}
    need('return _surface_module().validate(source, rig, record)' in ast.get_source_segment(physics_text, physics["_physics_graph"]),
         "Actual physics no longer delegates unchanged surface validation")
    namespace = prepared_namespace(adapter, direct, core, base, args.artist_protection, args.artist_protection_sha)
    need(namespace["exercise_direct"].__globals__["_CORE"] is core and namespace["exercise_direct"].__globals__["_DIRECT"] is direct
         and namespace["main"].__globals__["exercise_direct"] is namespace["exercise_direct"] and namespace["restore_program"] is core.restore_program,
         "Actual cold namespace/callback/finally identity differs")
    need(namespace["PINS"][Path(__file__)] == sha(Path(__file__)) and namespace["PINS"][INPUT_COMPONENT] == INPUT_COMPONENT_SHA,
         "Cold/current CLI proof pins missing")
    return {"passed": True, "actual_partial_input8_seek3_positive": 1, "partial_negatives_rejected": len(negatives),
            "failed_parent_not_cold_completion": True, "no_timeline_action_newCloth": True,
            "paused_flags_follow_actual_production_contract": True, "actual_callback_finally_transport": True,
            "cold_native_completion": False, "native_run": False, "accepted": False}


def main(args):
    if args.pure_checks:
        print(json.dumps(pure_checks(args))); return 0
    candidate = load_candidate(); adapter = candidate.load_current(); direct = adapter.load_direct(); core = direct.load_core(); base = core.load_base()
    candidate.current_artist_proof(base, direct, adapter, args.artist_protection, args.artist_protection_sha)
    return prepared_namespace(adapter, direct, core, base, args.artist_protection, args.artist_protection_sha)["main"](args)


if __name__ == "__main__":
    raise SystemExit(main(load_candidate().arguments()))
