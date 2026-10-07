"""PREPARED ONLY: disposable exact7ac live NEW Cloth component on Blender5.2.

Actual b85 input8/seek3 remains a failed parent report. A separately completed
cold public Manual/Original component and that exact partial report are both
mandatory before native execution. Old Cloth stays paused as a non-input during
new simulation; its restored C difference is measured, not accepted or a payload
preservation claim. Author/config14/source/current-disk finally gates stay exact.
No artist/plugin deployment, valid-cache waiver, live Keys or effect acceptance.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
from types import CodeType, SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LIVE = HERE / "verify_live_direct_cloth52.py"
LIVE_SHA = "9646529e108a7ada6f04c17e013c8f70a558773e29b578ce6d00fbd97fc2f2a5"
POLICY = HERE / "verify_direct_main_manual_input52_cache_policy.py"
POLICY_SHA = "fdb26dfcab5f4b490f37ebdcd34b55b6a8702604b185dceb896c050f6e227735"
SOURCE_HELPER = HERE / "source_compatibility52_node_ui.py"
SOURCE_HELPER_SHA = "08d36c4e561c808ed40a49e6b094085ef687a8a2e02bf5413c56ea203332507b"
DISK_HELPER = HERE / "artist_disk_protection52.py"
DISK_HELPER_SHA = "11d925f0356a45d831ff84339e31bf691df21c257e195497fd36922907167b37"
INPUT_SHA = "7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f"
COLD = HERE / "verify_public_manual_original52_cold.py"
COLD_SHA = "ab9f5a04ef0462803bc467698934270461b9d521b039d69e6c788f087929f1ba"
PREVIOUS = HERE / "verify_live_direct_cloth52_cache_policy.py"
PREVIOUS_SHA = "543280b94fafd0cb3644de9ccc73490d26b1e20aa2d889ff3b3079786b1a7979"
STAGE = "LIVE_DISPOSABLE_7AC_DIRECT_CLOTH_52"


def need(condition, message):
    if not condition:
        raise RuntimeError("LiveDisposable7ac52: " + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def valid_sha(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def load(path, expected, name):
    need(sha(path) == expected, "Frozen dependency changed: " + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def critical_pose_frames(recipe, case, frames):
    """Discrete authored recipe extrema; these are frame selections, not geometry."""
    need(case in {"walk", "run", "abrupt_stop_turn", "leg_raise"} and type(frames) is int
         and 40 <= frames <= 60, "Bounded recipe selection differs")
    rows = {f: recipe(case, f, frames) for f in range(1, frames + 1)}
    need(all(set(row) == {"left", "right", "forward_height", "turn", "stopped"}
             and type(row["stopped"]) is bool and all(math.isfinite(row[k]) for k in row if k != "stopped")
             for row in rows.values()), "Recipe sample is incomplete/nonfinite")
    def maximum(key, absolute=False):
        return max(rows, key=lambda f: (abs(rows[f][key]) if absolute else rows[f][key], -f))
    roles = {}
    if case == "leg_raise":
        roles["left_maximum_absolute"] = maximum("left", True)
    elif case in {"walk", "run"}:
        # right=-left, so both absolute maxima share a frame. Signed extrema
        # retain the two genuinely raised-side images without changing actions.
        roles.update(left_maximum_absolute=maximum("left", True), right_maximum_absolute=maximum("right", True),
                     left_signed_maximum=maximum("left"), right_signed_maximum=maximum("right"))
    else:
        forward_max = max(row["forward_height"] for row in rows.values())
        turn_max = max(row["turn"] for row in rows.values())
        stop = [f for f, row in rows.items() if row["forward_height"] == forward_max
                and row["left"] == row["right"] == 0.0]
        turned = [f for f, row in rows.items() if row["turn"] == turn_max and row["stopped"]]
        need(stop and turned and turn_max == math.pi * .5, "Stop/complete-turn recipe absent")
        roles.update(gait_stop_start=min(stop), turn_completed=min(turned))
    chosen = sorted(set(roles.values()))
    return {"case": case, "frames": chosen, "roles": roles,
            "selected_recipe_values": {str(f): rows[f] for f in chosen},
            "selection_scope": "Discrete original Body Action recipe only; native inputs/final3040/Body are read at these actual frames.",
            "right_equals_negative_left": case in {"walk", "run"}, "native_captured": False, "accepted": False}


def paired_component_proof(cold_path, cold_sha, input_path, input_sha):
    """Real file SHAs and the frozen producer's actual component ABI, no mocks."""
    for path, expected in ((cold_path, cold_sha), (input_path, input_sha)):
        need(isinstance(path, Path) and path.is_absolute() and path.resolve().is_relative_to(HERE)
             and path.is_file() and valid_sha(expected) and sha(path) == expected,
             "Explicit Root-selected actual component path/SHA required")
    cold = load(COLD, COLD_SHA, "live_disposable_actual_cold")
    value = cold.paired_component_proof(cold_path, cold_sha, input_path, input_sha)
    # Neither a historical artist receipt nor a matching pair authorizes a new
    # source revision. Actual complete source remains exact to today's gate.
    source_helper = load(SOURCE_HELPER, SOURCE_HELPER_SHA, "live_disposable_current_source")
    current_source = source_helper.current_manifest()
    for path, expected in ((cold_path, cold_sha), (input_path, input_sha)):
        report = json.loads(path.read_text(encoding="utf-8"))
        need(report.get("source_before") == report.get("source_after") == current_source,
             "Actual component full source is not the current exact source")
        runtime = report.get("runtime52", {})
        need(runtime.get("version") == [5, 2, 0]
             and Path(runtime.get("binary", "")).resolve() == Path("D:/Blender5.2/blender.exe").resolve(),
             "Actual component native Blender5.2 identity differs")
        need(sha(path) == expected, "Actual component changed during strict scope check")
    return dict(value, cold_report={"path": str(cold_path), "sha256": cold_sha},
                partial_input_report={"path": str(input_path), "sha256": input_sha,
                                      "native_completed": False},
                full_actual_sources_exact_current=True,
                original_valid_or_baked_cache_waived=False,
                production_cache_preservation=False)


def compiled_dynamic_source(live):
    source = inspect.getsource(live.exercise_dynamic)
    replacements = (
        ('    report["completed_direct_prerequisite"] = completed_direct_proof(args.direct_proof, args.direct_proof_sha, _DIRECT)\n',
         '    report["paired_component_prerequisite"] = paired_component_proof(args.cold_proof, args.cold_proof_sha, args.input_proof, args.input_proof_sha)\n'),
        ('    need(not old_cloth.show_viewport and not old_cloth.show_render, "old Cloth not paused before owned seeks")\n',
         '    need(not old_cloth.show_viewport and not old_cloth.show_render, "old Cloth not paused before owned seeks")\n'
         '    report["disposable_fixture_contract"] = {"fixture_sha256": INPUT_SHA, "old_C_used_as_new_physics_input": False,\n'
         '        "valid_baked_or_storage_cache_waived": False, "old_C_restored_geometry_accepted": False,\n'
         '        "old_cache_payload_preserved": "Unknown", "current_artist_integration": False,\n'
         '        "production_cache_policy": False, "accepted": False}\n'
         '    admission = classify_cache_transition(frozen_cache, frozen_cache, {"name": "PAUSED_ACTION_SEEK",\n'
         '        "old_cloth_flags": [False, False], "frozen_frame": frozen_cache_frame, "frame": frozen_cache_frame})\n'
         '    report["disposable_old_cache_admission"] = admission; write()\n'
         '    need(admission["allowed"], "disposable fixture requires exact known invalid unbaked non-storage memory cache")\n'),
        ('    need(report["original_C_restored_error"]["maximum_m"]==0.,"original sameframe C not exact after restore")\n',
         '    report["original_C_restored_geometry_observation"] = {"error": report["original_C_restored_error"],\n'
         '        "initial_state": "Captured before FK/Manual preparation", "current_state": "Prepared Manual work_pose after owned seeks",\n'
         '        "same_input_baseline_proven": False, "accepted": False, "component_hard_gate": False,\n'
         '        "old_cache_payload_preserved": False if report.get("old_cache_content_preserved") is False else "Unknown",\n'
         '        "scope": "Disposable exact7ac NEW physics only; not old C geometry or production cache preservation"}; write()\n'),
        ('    # Public Manual Original prerequisite already belongs to completed281e. This candidate never invokes Automatic Original.\n'
         '    report["Original_scope"]={"prerequisite":"Completed281e public Manual Original roundtrip", "new_vertex_Automatic_Original":False,\n',
         '    # Actual cold public Manual Original and actual partial input8/seek3 are separate component evidence.\n'
         '    report["Original_scope"]={"prerequisite":"Actual completed cold public Manual Original plus actual failed-parent input8/seek3", "new_vertex_Automatic_Original":False,\n'),
        ('    work_pose = qa.pose_channels(rig); frozen_cache = same.cache_state(old_cloth,qa)\n',
         '    work_pose = qa.pose_channels(rig); frozen_cache = same.cache_state(old_cloth,qa)\n'
         '    frozen_cache_frame = [home.frame_current, home.frame_subframe]\n'
         '    critical = critical_pose_frames(input_recipe, args.case, args.frames)\n'
         '    critical_set = set(critical["frames"])\n'
         '    report["critical_pose_frames"] = critical\n'),
        ('"original_cache14_exact":same.cache_state(old_cloth,qa)==frozen_cache,',
         '"original_cache14_exact":(sample_old_cache := same.cache_state(old_cloth,qa))==frozen_cache,'),
        ('        samples.append(row);report["live_motion_samples"]=samples;write()\n',
         '        row["original_cache_frozen_metadata"] = dict(frozen_cache)\n'
         '        row["original_cache_current_metadata"] = dict(sample_old_cache)\n'
         '        row["original_cache_transition"] = classify_cache_transition(frozen_cache, sample_old_cache, {\n'
         '            "name": "PAUSED_ACTION_SEEK", "old_cloth_flags": [bool(old_cloth.show_viewport), bool(old_cloth.show_render)],\n'
         '            "frozen_frame": frozen_cache_frame, "frame": row["frame"]})\n'
         '        report["old_cache_content_preserved"] = False if row["original_cache_transition"]["cache_content_preserved"] is False or report.get("old_cache_content_preserved") is False else "Unknown"\n'
         '        row["critical_recipe_roles"] = [name for name, frame in critical["roles"].items() if frame == home.frame_current]\n'
         '        samples.append(row);report["live_motion_samples"]=samples;write()\n'),
        ('need(exact["maximum_m"]==0. and effect["maximum_m"]<=guard and row["original_cache14_exact"],"unchanged exactSkin/50um outside720/cache14 guard failed")',
         'need(exact["maximum_m"]==0. and effect["maximum_m"]<=guard and row["original_cache_transition"]["allowed"],"unchanged exactSkin/50um outside720/cache14 guard failed")'),
        ('            if args.render and label in {"daily_end","manual_settled"}:\n',
         '            if args.render and (label in {"daily_end","manual_settled"} or label.startswith("critical_")):\n'),
        ('    sparse={1,args.frames//2,args.frames}; stopped=set()\n',
         '    sparse={1,args.frames//2,args.frames} | critical_set; stopped=set()\n'),
        ('        current=sample("daily_end" if frame==args.frames else "daily_"+str(frame),frame in sparse)\n',
         '        current=sample("daily_end" if frame==args.frames else ("critical_" if frame in critical_set else "daily_")+str(frame),frame in sparse)\n'),
        ('    response={"knee_m":max(math.dist(first["knee"],row["native_knee_world"])*metres for row in samples),\n',
         '    measured_critical = {row["frame"][0] for row in samples if row["critical_recipe_roles"]}\n'
         '    critical["native_captured"] = critical_set <= measured_critical\n'
         '    critical["actual_contact_frames"] = [row["frame"] for row in contacts if row["frame"] in critical_set]\n'
         '    critical["render_requested"] = bool(args.render)\n'
         '    critical["render_records_complete"] = all(("daily_end" if frame==args.frames else "critical_"+str(frame)) in report.get("renders", {}) for frame in critical_set) if args.render else "NotRequested"\n'
         '    report["critical_pose_frames"] = critical; write()\n'
         '    need(critical["native_captured"] and critical_set <= {row["frame"] for row in contacts},"native peak/contact sampling incomplete")\n'
         '    if args.render: need(critical["render_records_complete"] and all(report["renders"]["daily_end" if frame==args.frames else "critical_"+str(frame)].get("success") is True for frame in critical_set),"critical pose render incomplete")\n'
         '    response={"knee_m":max(math.dist(first["knee"],row["native_knee_world"])*metres for row in samples),\n'),
        ('    # Stop NEW Cloth before author restoration. Old Cloth gets its original flags only at original author frame.\n',
         '    required_render_labels = {"daily_end", "manual_settled"} | {"daily_end" if frame==args.frames else "critical_"+str(frame) for frame in critical_set}\n'
         '    report["required_live_render_samples"] = {"requested": bool(args.render), "labels": sorted(required_render_labels),\n'
         '        "complete": all(report.get("renders", {}).get(label, {}).get("success") is True for label in required_render_labels) if args.render else "NotRequested", "accepted": False}\n'
         '    write()\n'
         '    if args.render: need(report["required_live_render_samples"]["complete"] is True,"critical/daily/manual actual render collection incomplete")\n'
         '    # Stop NEW Cloth before author restoration. Old Cloth gets its original flags only at original author frame.\n'),
    )
    for old, new in replacements:
        need(source.count(old) == 1, "Unique frozen Live adaptation differs: " + old[:70])
        source = source.replace(old, new, 1)
    reverse = source
    for old, new in reversed(replacements):
        need(reverse.count(new) == 1, "Reversible Live adaptation differs")
        reverse = reverse.replace(new, old, 1)
    need(ast.dump(ast.parse(reverse)) == ast.dump(ast.parse(inspect.getsource(live.exercise_dynamic))),
         "Native action/physics/input/held/public restore changed outside disposable prerequisites/C observation/cache receipts/critical sampling")
    need('need(same.cache_state(old_cloth,qa)==frozen_cache,"old14cache changed during live newCloth seeks")' in source,
         "Author-frame full14exact restoration disappeared")
    return source


def code_contract(code):
    return (code.co_code, tuple(code_contract(v) if isinstance(v, CodeType) else v for v in code.co_consts),
            code.co_names, code.co_varnames, code.co_freevars, code.co_cellvars)


def components(args):
    live = load(LIVE, LIVE_SHA, "live_disposable_frozen964652")
    policy = load(POLICY, POLICY_SHA, "live_disposable_frozen_classifier")
    cold = load(COLD, COLD_SHA, "live_disposable_frozen_cold")
    candidate = cold.load_candidate()
    adapter = candidate.load_current(); direct = adapter.load_direct(); core = direct.load_core(); base = core.load_base()
    candidate.current_artist_proof(base, direct, adapter, args.artist_protection, args.artist_protection_sha)
    return live, policy, cold, candidate, adapter, direct, core, base


def prepared_namespace(live, policy, cold, candidate, adapter, direct, core, base, args):
    namespace = cold.prepared_namespace(adapter, direct, core, base, args.artist_protection, args.artist_protection_sha)
    initial_main = candidate.initial_cache_program(direct, base, core)
    probe = {}; exec(compile(initial_main, "<current prepared Main code identity>", "exec"), probe)
    need(code_contract(probe["main"].__code__) == code_contract(namespace["main"].__code__), "Published current Main source/code ABI differs")
    main = initial_main
    replacements = (
        ('("objects","meshes","armatures","curves","shape_keys")', '("objects","meshes","armatures","curves","shape_keys","node_groups")'),
        ('                for kind in ("meshes","curves","armatures"):',
         '                for group in reversed(owned["node_groups"]):\n                    need(group.users==0,"Owned GN acquired foreign user"); bpy.data.node_groups.remove(group)\n                for kind in ("meshes","curves","armatures"):'),
    )
    for old, new in replacements:
        need(main.count(old) == 1, "Unique original Live GN receipt/cleanup substitution differs")
        main = main.replace(old, new, 1)
    reverse = main
    for old, new in reversed(replacements): reverse = reverse.replace(new, old, 1)
    need(ast.dump(ast.parse(reverse)) == ast.dump(ast.parse(initial_main)), "Current source/V3/finally Main changed outside exact owned GN cleanup")
    live._DIRECT, live._CORE, live._ADAPTER = direct, core, adapter
    live.STAGE = STAGE
    globals_for_dynamic = dict(vars(live))
    globals_for_dynamic.update(_DIRECT=direct, _CORE=core, _ADAPTER=adapter, STAGE=STAGE,
                               critical_pose_frames=critical_pose_frames, classify_cache_transition=policy.classify_cache_transition,
                               paired_component_proof=paired_component_proof, INPUT_SHA=INPUT_SHA, __doc__=__doc__)
    exec(compile(compiled_dynamic_source(live), str(Path(__file__)), "exec"), globals_for_dynamic)
    def exercise(values, frozen):
        try:
            return globals_for_dynamic["exercise_dynamic"](values, frozen)
        finally:
            # The compiled function replaces its _DYNAMIC dict at entry. The
            # frozen Root-restorer must see that exact new dict even on failure.
            live._DYNAMIC = globals_for_dynamic.get("_DYNAMIC", {})
    namespace["exercise_direct"] = exercise
    namespace["restore_program"] = live.restore_dynamic
    namespace["FROZEN_BASE"] = base
    namespace["__file__"] = str(Path(__file__))
    namespace["PINS"].update({LIVE: LIVE_SHA, POLICY: POLICY_SHA, SOURCE_HELPER: SOURCE_HELPER_SHA,
                               DISK_HELPER: DISK_HELPER_SHA, COLD: COLD_SHA, PREVIOUS: PREVIOUS_SHA,
                               Path(__file__): sha(Path(__file__))})
    namespace["PINS"][args.input_proof] = args.input_proof_sha
    if args.cold_proof is not None: namespace["PINS"][args.cold_proof] = args.cold_proof_sha
    original_capture = namespace["capture_program"]
    def capture(*values):
        receipt = original_capture(*values)
        core._STATE["closure"] = namespace["current_main_manual_closure"]
        report = values[-1]
        report["stage"] = STAGE
        report["live_disposable_component_adapter"] = {"immutable_live": str(LIVE), "sha256": LIVE_SHA,
            "cache_classifier": str(POLICY), "classifier_sha256": POLICY_SHA,
            "cold_producer": str(COLD), "cold_producer_sha256": COLD_SHA,
            "source_and_V3_namespace_inherited": True, "cache_original_exact_boolean_retained": True,
            "author_frame_and_finally_all14_exact_unchanged": True, "critical_native_sampling_added": True,
            "physics_action_recipe_parameters_held_input_unchanged": True,
            "old_b85_parent_remains_failed": True, "old_C_restore_geometry_component_hard_gate": False,
            "old_cache_payload_or_production_preservation": False, "new_backend_deployed": False, "accepted": False}
        return receipt
    namespace["capture_program"] = capture
    exec(compile(main, str(Path(__file__)), "exec"), namespace)
    need(namespace["main"].__globals__ is namespace and namespace["main"].__globals__["exercise_direct"] is exercise
         and namespace["restore_program"] is live.restore_dynamic
         and namespace["load"].__name__ == "compatible_load", "Actual compiled source/capture/exercise/restorer namespace differs")
    namespace["_live_private_dynamic_globals"] = globals_for_dynamic
    return namespace


def pure_checks(args):
    live, policy, cold, candidate, adapter, direct, core, base = components(args)
    old_hash = sha(LIVE)
    source = compiled_dynamic_source(live)
    # Original physics/Action/held/Original code is reverse-AST checked above.
    tree = ast.parse(source)
    key_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "keyframe_insert"]
    need(len(key_calls) == 3 and all(any(k.arg == "group" and isinstance(k.value, ast.Constant) and k.value.value == "QA Body" for k in n.keywords) for n in key_calls), "Only native Body14 Action channels permitted")
    checks = 0
    for case in ("walk", "run", "abrupt_stop_turn", "leg_raise"):
        for frames in (40, 60):
            critical = critical_pose_frames(live.input_recipe, case, frames)
            rows = {f: live.input_recipe(case, f, frames) for f in range(1, frames + 1)}
            for role, frame in critical["roles"].items():
                if "maximum_absolute" in role:
                    side = "left" if role.startswith("left") else "right"
                    need(abs(rows[frame][side]) == max(abs(row[side]) for row in rows.values()), "Selected frame is not actual absolute extremum")
                elif "signed_maximum" in role:
                    side = "left" if role.startswith("left") else "right"
                    need(rows[frame][side] == max(row[side] for row in rows.values()), "Selected frame is not actual signed extremum")
                elif role == "gait_stop_start":
                    need(rows[frame]["left"] == rows[frame]["right"] == 0.0 and rows[frame]["forward_height"] == max(row["forward_height"] for row in rows.values())
                         and all(rows[f]["forward_height"] < rows[frame]["forward_height"] for f in range(1, frame)), "Stop onset is not actual first plateau")
                else:
                    need(rows[frame]["turn"] == math.pi * .5 and rows[frame]["stopped"] and all(rows[f]["turn"] < rows[frame]["turn"] for f in range(1, frame)), "Turn completion is not actual first complete turn")
                checks += 1
    evidence = json.loads(policy.EVIDENCE.read_text(encoding="utf-8")); observations = evidence["observations"]
    frozen, current = observations[0]["current"]["value"], observations[1]["current"]["value"]
    phase = {"name": "PAUSED_ACTION_SEEK", "old_cloth_flags": [False, False], "frozen_frame": observations[0]["frame"], "frame": observations[1]["frame"]}
    classified = policy.classify_cache_transition(frozen, current, phase)
    need(classified["allowed"] and classified["public_metadata_exact"] is False and classified["cache_content_preserved"] is False, "Actual bounded phase receipt differs")
    cache_negatives = []
    for field, value in (("pointer", frozen["pointer"] + 1), ("is_baked", True), ("disk", True), ("info", "unknown")):
        changed = dict(current); changed[field] = value; cache_negatives.append((changed, phase))
    active_phase = dict(phase, old_cloth_flags=[True, True]); cache_negatives.append((current, active_phase))
    author_phase = dict(phase, name="RESTORED_AUTHOR_FRAME_SAMPLE", old_cloth_flags=[True, True], frame=phase["frozen_frame"])
    cache_negatives.append((current, author_phase))
    for changed, where in cache_negatives:
        need(policy.classify_cache_transition(frozen, changed, where)["allowed"] is False, "Cache negative silently admitted")
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "need"
                and len(n.args) > 1 and isinstance(n.args[1], ast.Constant) and n.args[1].value == "unchanged exactSkin/50um outside720/cache14 guard failed")
    for exact, outside, allowed, passes in ((0.0, 0.0, True, True), (.1, 0.0, True, False), (0.0, .1, True, False), (0.0, 0.0, False, False)):
        scope = {"need": need, "exact": {"maximum_m": exact}, "effect": {"maximum_m": outside}, "guard": 5e-5,
                 "row": {"original_cache14_exact": False, "original_cache_transition": {"allowed": allowed}}}
        try: exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.Expr(value=copy.deepcopy(node))], type_ignores=[])), "<actual live input/cache guard>", "exec"), scope)
        except RuntimeError: need(not passes, "Allowed actual input/cache guard rejected")
        else: need(passes, "Actual exactSkin/outside720/cache rejection swallowed")
    namespace = prepared_namespace(live, policy, cold, candidate, adapter, direct, core, base, args)
    need(namespace["_live_private_dynamic_globals"]["classify_cache_transition"] is policy.classify_cache_transition
         and namespace["PINS"][base.SURFACE] == "a58d0e542bca195cd1d8e767e23e76809602bfe95b698668a8cc4b4289855c12"
         and namespace["PINS"][args.artist_protection] == args.artist_protection_sha,
         "Real private classifier/a58/V3 PIN transport differs")
    need(sha(LIVE) == old_hash == LIVE_SHA, "Immutable Live file changed")
    partial_report = json.loads(args.input_proof.read_text(encoding="utf-8"))
    partial = cold.historical_dynamic_input_component(partial_report)
    need(partial["parent_report_native_completed"] is False and partial["public_Original_completed"] is False,
         "Failed b85 parent was promoted to completion")
    for mutation in (lambda r: r.update(native_completed=True), lambda r: r.update(source_disk_exact=None),
                     lambda r: r["direct_live_samples"].pop()):
        changed = copy.deepcopy(partial_report); mutation(changed)
        try: cold.historical_dynamic_input_component(changed)
        except RuntimeError: pass
        else: need(False, "Actual partial proof missing/False/Unknown was admitted")
    try: cold.completed_cold_component(partial_report)
    except RuntimeError: pass
    else: need(False, "Failed b85 parent cannot prove cold completion")
    # The only newly removed native hard gate is the explicitly unaccepted C0
    # cross-state observation. Original author-frame14 and entire Main cleanup
    # remain exact; simulation/readback/Action/render code reverse-matches5432.
    previous = load(PREVIOUS, PREVIOUS_SHA, "live_disposable_previous5432")
    prior_source = previous.compiled_dynamic_source(live)
    previous_need = '    need(report["original_C_restored_error"]["maximum_m"]==0.,"original sameframe C not exact after restore")\n'
    need(previous_need in prior_source and previous_need not in source,
         "Old C0 hard gate boundary not explicit")
    need('need(same.cache_state(old_cloth,qa)==frozen_cache,"old14cache changed during live newCloth seeks")' in source,
         "Original author-frame14 restoration was weakened")
    new_scope = [node for node in ast.walk(tree) if isinstance(node, ast.Assign) and any(isinstance(t, ast.Subscript)
                 and isinstance(t.slice, ast.Constant) and t.slice.value == "original_C_restored_geometry_observation" for t in node.targets)]
    need(len(new_scope) == 1, "Exactly one explicit restored-C observation required")
    value = new_scope[0].value
    literals = {key.value: val.value for key, val in zip(value.keys, value.values)
                if isinstance(key, ast.Constant) and isinstance(val, ast.Constant)}
    need(literals.get("accepted") is False and literals.get("component_hard_gate") is False
         and literals.get("same_input_baseline_proven") is False, "Old C loss observation was accepted")
    actual_proof = None
    if args.cold_proof is not None:
        actual_proof = paired_component_proof(args.cold_proof, args.cold_proof_sha, args.input_proof, args.input_proof_sha)
    return {"passed": True, "native": False, "old_live_unchanged": True, "old5432_unchanged": sha(PREVIOUS) == PREVIOUS_SHA,
            "reversible_native_source_AST": True, "critical_recipe_extremum_controls": checks,
            "actual_cache_classification_positive": 1, "cache_negatives_rejected": len(cache_negatives),
            "actual_input_cache_Boolean_controls": 4, "actual_current_namespace_and_GN_cleanup": True,
            "actual_b85_partial_component_only": partial, "partial_negatives_rejected": 3,
            "failed_parent_not_cold_completion": True, "old_C_observation_not_accepted": True,
            "actual_paired_components": actual_proof, "cold_native_completion_claimed": actual_proof is not None,
            "cold_evidence_status": "Unrecorded" if actual_proof is None else "Actual paired files",
            "production_cache_preservation": False, "accepted": False}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path); parser.add_argument("--cold-proof", type=Path); parser.add_argument("--cold-proof-sha")
    parser.add_argument("--input-proof", type=Path, required=True); parser.add_argument("--input-proof-sha", required=True)
    parser.add_argument("--artist-protection", type=Path, required=True); parser.add_argument("--artist-protection-sha", required=True)
    parser.add_argument("--case", choices=("walk", "run", "abrupt_stop_turn", "leg_raise"), default="run")
    parser.add_argument("--frames", type=int, default=60); parser.add_argument("--manual-steps", type=int, default=10)
    parser.add_argument("--max-seconds", type=float, default=180.); parser.add_argument("--triangle-pair-limit", type=int, default=2000000)
    parser.add_argument("--body-vertex-limit", type=int, default=500000); parser.add_argument("--render", action="store_true")
    parser.add_argument("--pure-checks", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    need(args.artist_protection.is_absolute() and args.artist_protection.resolve().is_relative_to(HERE)
         and args.artist_protection.is_file() and valid_sha(args.artist_protection_sha), "Explicit Root V3 receipt required")
    args.artist_protection = args.artist_protection.resolve()
    need(args.input_proof.is_absolute() and args.input_proof.resolve().is_relative_to(HERE)
         and args.input_proof.is_file() and valid_sha(args.input_proof_sha), "Actual partial input path/SHA required")
    args.input_proof = args.input_proof.resolve()
    cold = load(COLD, COLD_SHA, "live_disposable_CLI_cold")
    need(args.input_proof == cold.INPUT_COMPONENT.resolve() and args.input_proof_sha == cold.INPUT_COMPONENT_SHA
         and sha(args.input_proof) == args.input_proof_sha, "Only immutable actual b85 input component is admissible")
    need((args.cold_proof is None) == (args.cold_proof_sha is None), "Actual cold report path/SHA must be paired")
    if args.cold_proof is not None:
        need(args.cold_proof.is_absolute() and args.cold_proof.resolve().is_relative_to(HERE)
             and args.cold_proof.is_file() and valid_sha(args.cold_proof_sha), "Actual completed cold path/SHA required")
        args.cold_proof = args.cold_proof.resolve()
    need(40 <= args.frames <= 60 and 1 <= args.manual_steps <= 10 and 0 < args.max_seconds <= 180
         and 0 < args.triangle_pair_limit <= 2000000 and 0 < args.body_vertex_limit <= 500000, "Original bounded one-case budget differs")
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and not args.output.exists()
             and args.output.resolve().is_relative_to(HERE) and args.output.resolve() != HERE, "Fresh private output only")
        need(args.cold_proof is not None, "Actual completed cold plus partial input prerequisite required; no defaults")
    return args


def main(args):
    if args.pure_checks:
        print(json.dumps(pure_checks(args))); return 0
    live, policy, cold, candidate, adapter, direct, core, base = components(args)
    paired_component_proof(args.cold_proof, args.cold_proof_sha, args.input_proof, args.input_proof_sha)
    namespace = prepared_namespace(live, policy, cold, candidate, adapter, direct, core, base, args)
    return namespace["main"](args)


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
