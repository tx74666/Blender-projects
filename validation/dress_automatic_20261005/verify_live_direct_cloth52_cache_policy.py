"""PREPARED ONLY: frozen live Cloth recipe with current source and narrow cache gates.

Uses the actual current Direct cache-policy namespace and a Root-selected completed
Direct report. The old exact cache Boolean remains recorded. Only the known invalid
memory summary can change while BOTH old Cloth flags are false; author-frame and
finally all14 metadata remain exact. Critical recipe frames are measured natively,
not interpolated geometry. No artist/plugin deployment or effect acceptance.
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
STAGE = "LIVE_DIRECT_MAIN_CLOTH_52_CACHE_POLICY"
POSITIVE = ("direct_main_manual_input_success", "native_completed", "ready_for_next_private_gate",
            "owned_cleanup_exact", "cache_metadata_exact", "source_disk_exact", "input_artist_disk_exact",
            "script_disk_exact", "frozen_pins_disk_exact", "canonical_validation_after_reload",
            "pose_after_reload_exact", "playback_after_reload_exact", "author_frame_after_reload_exact")
RESTORE = ("constraint_pointers_and_RNA_exact", "raw_pose_exact", "id_properties_exact",
           "frame_exact", "cloth_flags_exact", "cache_exact")


def need(condition, message):
    if not condition:
        raise RuntimeError("LiveCachePolicy52: " + message)


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


def validate_completed_report(report, policy, candidate, source_helper, disk, base):
    """Only called for a real file whose complete SHA the Root explicitly selects."""
    need(type(report) is dict and report.get("stage") == policy.STAGE
         and report.get("script_sha256") == POLICY_SHA, "Prerequisite is not the immutable completed new Direct policy")
    need(all(report.get(k) is True for k in POSITIVE) and report.get("cleanup_errors") == []
         and report.get("protection_before_reload", {}).get("success") is True
         and report.get("protection_after_reload", {}).get("success") is True, "Direct terminal AND/author protection incomplete")
    need(report.get("accepted") is False and report.get("artist_saved") is False
         and report.get("automatic_Original_semantic_acceptance") is False
         and report.get("runtime52", {}).get("version") == [5, 2, 0]
         and Path(report["runtime52"].get("binary", "")).resolve() == Path("D:/Blender5.2/blender.exe").resolve(),
         "Native5.2/Manual-only input scope differs")
    need(report.get("install_input", {}).get("candidate_sha256") == INPUT_SHA, "Different native input fixture")
    restore = report.get("live_author_restore", {})
    need(restore.get("errors") == [] and all(restore.get(k) is True for k in RESTORE), "Direct author restoration incomplete")
    current = source_helper.current_manifest()
    need(report.get("source_before") == report.get("source_after") == current, "Actual complete source manifests differ")
    explicit = report.get("explicit_source_compatibility", {})
    need(explicit.get("reviewed_extra_modules") == source_helper.explicit_modules(base.REPOSITORY)
         and explicit.get("version_only_Init") == source_helper.init_version_only(base.REPOSITORY)
         and explicit.get("canonical_inventory_exact") is True and explicit.get("all_other_canonical_modules_exact") is True
         and explicit.get("old_install_validated_changed_code") is False, "Explicit current source gate missing/different")
    adapter_proof = report.get("source_compatibility_adapter", {})
    need(adapter_proof.get("node_UI6_Surface") == source_helper.surface_node_layout_only(base.REPOSITORY)
         and adapter_proof.get("cache_receipt_initialized_before_readonly_validation") is True, "Actual UI6/source namespace proof missing")
    cache = report.get("cache_policy", {})
    need(cache.get("id") == policy.POLICY_ID and cache.get("evidence") == {"path": str(policy.EVIDENCE), "sha256": policy.EVIDENCE_SHA}
         and cache.get("baseline_not_rebased") is True and cache.get("original_cache_exact_boolean_retained") is True
         and cache.get("final_metadata_exact_and_restored_C_guards_unchanged") is True
         and cache.get("deployed_runtime_policy") is False and cache.get("accepted") is False,
         "Completed Direct lacks exact bounded cache policy")
    pins = report.get("pins")
    need(type(pins) is dict, "Actual prerequisite PIN manifest absent")
    normalized = {str(Path(p).resolve()).casefold(): value for p, value in pins.items()}
    need(len(normalized) == len(pins), "Duplicate normalized prerequisite PIN paths")
    required = {POLICY: POLICY_SHA, policy.CANDIDATE: policy.CANDIDATE_SHA, policy.DIAGNOSTIC: policy.DIAGNOSTIC_SHA,
                policy.EVIDENCE: policy.EVIDENCE_SHA, SOURCE_HELPER: SOURCE_HELPER_SHA, DISK_HELPER: DISK_HELPER_SHA,
                base.INPUT: INPUT_SHA, base.SURFACE: base.PINS[base.SURFACE], base.WORKER: base.PINS[base.WORKER]}
    for path, expected in required.items():
        need(normalized.get(str(path.resolve()).casefold()) == expected, "Actual prerequisite graph PIN differs: " + str(path))
    historical = report.get("current_artist_disk_protection", {})
    need(type(historical) is dict and valid_sha(historical.get("sha256")), "Historical prerequisite disk protection absent")
    receipt = disk.typed_receipt(historical.get("receipt"), base.ARTIST)
    need(historical.get("current_artist_sha256") == receipt["artist_sha256"]
         and historical.get("current_artist_bytes") == receipt["artist_bytes"]
         and historical.get("current_artist_mtime_ns") == receipt["artist_mtime_ns"]
         and historical.get("current_native_save_proof") == "Unmeasured"
         and normalized.get(str(Path(historical.get("path", "")).resolve()).casefold()) == historical["sha256"]
         and normalized.get(str(base.ARTIST.resolve()).casefold()) == receipt["artist_sha256"], "Historical disk evidence inconsistent")
    return {"script_sha256": POLICY_SHA, "mechanism_completed": True, "native_input_sha256": INPUT_SHA,
            "actual_source_and_graph_exact_current": True, "prior_artist_sha256": receipt["artist_sha256"],
            "prior_artist_is_current_protection": False, "prior_artist_vs_current_fullraw": "Unmeasured",
            "scope": "Actual completed Direct input/Manual Original prerequisite only; not Cloth/effect/Keys/Automatic Original acceptance."}


def completed_direct_proof(path, expected, direct):
    need(isinstance(path, Path) and path.is_absolute() and path.resolve().is_relative_to(HERE)
         and path.is_file() and valid_sha(expected) and sha(path) == expected, "Root-selected actual completed proof absent/changed")
    policy = load(POLICY, POLICY_SHA, "live_completed_cache_policy")
    candidate = policy.load_candidate()
    source_helper = load(SOURCE_HELPER, SOURCE_HELPER_SHA, "live_completed_source08d")
    disk = load(DISK_HELPER, DISK_HELPER_SHA, "live_completed_disk11d")
    base = direct.load_core().load_base()
    value = validate_completed_report(json.loads(path.read_text(encoding="utf-8")), policy, candidate, source_helper, disk, base)
    need(sha(path) == expected, "Actual completed prerequisite changed during validation")
    return dict(value, path=str(path.resolve()), sha256=expected)


def compiled_dynamic_source(live):
    source = inspect.getsource(live.exercise_dynamic)
    replacements = (
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
         "Native action/physics/input/held/public restore changed outside cache receipts/critical sampling")
    need('need(same.cache_state(old_cloth,qa)==frozen_cache,"old14cache changed during live newCloth seeks")' in source,
         "Author-frame full14exact restoration disappeared")
    return source


def code_contract(code):
    return (code.co_code, tuple(code_contract(v) if isinstance(v, CodeType) else v for v in code.co_consts),
            code.co_names, code.co_varnames, code.co_freevars, code.co_cellvars)


def components(args):
    live = load(LIVE, LIVE_SHA, "live_frozen964652")
    policy = load(POLICY, POLICY_SHA, "live_policy_frozenfdb")
    candidate = policy.load_candidate()
    adapter = candidate.load_current(); direct = adapter.load_direct(); core = direct.load_core(); base = core.load_base()
    candidate.current_artist_proof(base, direct, adapter, args.artist_protection, args.artist_protection_sha)
    return live, policy, candidate, adapter, direct, core, base


def prepared_namespace(live, policy, candidate, adapter, direct, core, base, args):
    namespace = policy.prepared_namespace(adapter, direct, core, base, args.artist_protection, args.artist_protection_sha)
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
    live.completed_direct_proof = completed_direct_proof
    globals_for_dynamic = dict(vars(live))
    globals_for_dynamic.update(_DIRECT=direct, _CORE=core, _ADAPTER=adapter, STAGE=STAGE,
                               critical_pose_frames=critical_pose_frames, classify_cache_transition=policy.classify_cache_transition)
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
                               DISK_HELPER: DISK_HELPER_SHA, Path(__file__): sha(Path(__file__))})
    if args.direct_proof is not None: namespace["PINS"][args.direct_proof] = args.direct_proof_sha
    original_capture = namespace["capture_program"]
    def capture(*values):
        receipt = original_capture(*values)
        core._STATE["closure"] = namespace["current_main_manual_closure"]
        report = values[-1]
        report["stage"] = STAGE
        report["live_cache_policy_adapter"] = {"immutable_live": str(LIVE), "sha256": LIVE_SHA,
            "current_Direct_policy": str(POLICY), "Direct_sha256": POLICY_SHA,
            "source_and_V3_namespace_inherited": True, "cache_original_exact_boolean_retained": True,
            "author_frame_and_finally_all14_exact_unchanged": True, "critical_native_sampling_added": True,
            "physics_action_recipe_parameters_held_input_unchanged": True, "new_backend_deployed": False, "accepted": False}
        return receipt
    namespace["capture_program"] = capture
    exec(compile(main, str(Path(__file__)), "exec"), namespace)
    need(namespace["main"].__globals__ is namespace and namespace["main"].__globals__["exercise_direct"] is exercise
         and namespace["restore_program"] is live.restore_dynamic
         and namespace["load"].__name__ == "compatible_load", "Actual compiled source/capture/exercise/restorer namespace differs")
    namespace["_live_private_dynamic_globals"] = globals_for_dynamic
    return namespace


def pure_checks(args):
    live, policy, candidate, adapter, direct, core, base = components(args)
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
    namespace = prepared_namespace(live, policy, candidate, adapter, direct, core, base, args)
    need(namespace["_live_private_dynamic_globals"]["classify_cache_transition"] is policy.classify_cache_transition
         and namespace["PINS"][base.SURFACE] == "a58d0e542bca195cd1d8e767e23e76809602bfe95b698668a8cc4b4289855c12"
         and namespace["PINS"][args.artist_protection] == args.artist_protection_sha,
         "Real private classifier/a58/V3 PIN transport differs")
    need(sha(LIVE) == old_hash == LIVE_SHA, "Immutable Live file changed")
    actual_proof = None
    if args.direct_proof is not None:
        actual_proof = completed_direct_proof(args.direct_proof, args.direct_proof_sha, direct)
    return {"passed": True, "native": False, "old_live_unchanged": True, "reversible_native_source_AST": True,
            "critical_recipe_extremum_controls": checks, "actual_cache_classification_positive": 1,
            "cache_negatives_rejected": len(cache_negatives), "actual_input_cache_Boolean_controls": 4,
            "actual_current_namespace_and_GN_cleanup": True, "completed_native_Direct_proof": actual_proof,
            "completed_Direct_not_fabricated": True, "accepted": False}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path); parser.add_argument("--direct-proof", type=Path); parser.add_argument("--direct-proof-sha")
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
    need((args.direct_proof is None) == (args.direct_proof_sha is None), "Actual proof path/SHA must be paired")
    if args.direct_proof is not None:
        need(args.direct_proof.is_absolute() and args.direct_proof.resolve().is_relative_to(HERE)
             and args.direct_proof.is_file() and valid_sha(args.direct_proof_sha), "Actual completed Direct path/SHA required")
        args.direct_proof = args.direct_proof.resolve()
    need(40 <= args.frames <= 60 and 1 <= args.manual_steps <= 10 and 0 < args.max_seconds <= 180
         and 0 < args.triangle_pair_limit <= 2000000 and 0 < args.body_vertex_limit <= 500000, "Original bounded one-case budget differs")
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and not args.output.exists()
             and args.output.resolve().is_relative_to(HERE) and args.output.resolve() != HERE, "Fresh private output only")
        need(args.direct_proof is not None, "Actual completed Direct prerequisite required; no defaults")
    return args


def main(args):
    if args.pure_checks:
        print(json.dumps(pure_checks(args))); return 0
    live, policy, candidate, adapter, direct, core, base = components(args)
    completed_direct_proof(args.direct_proof, args.direct_proof_sha, direct)
    namespace = prepared_namespace(live, policy, candidate, adapter, direct, core, base, args)
    return namespace["main"](args)


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
