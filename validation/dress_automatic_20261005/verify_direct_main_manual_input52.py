"""PREPARED ONLY: 5.2 native Direct Main Manual-input component.

Isolated exact 7ac fixture, not the artist. No private Rig, generated raw drivers,
new Cloth, automatic output, deployment or scene save. Original is exercised
only with the old public Manual influence0. Old PHYS/Tracker targets stay intact.
Frozen e939 author receipts/restoration and 50e raw80/native cleanup are reused.
5.1 measurements remain historical evidence, never labelled as 5.2 measurements.
"""
import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CORE = HERE / "verify_live_input800_main_manual_bridge.py"
CORE_SHA = "e93948a4a8cf958990ac9271e3fa92d8801f055e230b9b0462dbe16310b2f7c5"
SAVED = HERE.parent / "blender52_migration_20261006/saved52.json"
SAVED_SHA = "b077048056253defb21ed9aadf92619a006b247072e0858d64037eca5afbb970"
LIVE = HERE.parent / "blender52_migration_20261006/live52.json"
LIVE_SHA = "4ba3948878bf72619f033b8eeba62b5634c0322ef1e326fae99bb6eb956a0e49"
ARTIST_SHA = "bbfed9dc983306b79107a742b297e31311d554cdd926665cc963f6644aba8ed0"
ARTIST_BYTES = 32266934
STAGE = "DIRECT_MAIN_MANUAL_INPUT_52"
_CORE = None


def need(condition, message):
    if not condition:
        raise RuntimeError("DirectMain52: " + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load_core():
    need(sha(CORE) == CORE_SHA, "immutable e939 changed")
    spec = importlib.util.spec_from_file_location("direct_main_frozen_e939", CORE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def transition_proof(base):
    need(sha(SAVED) == SAVED_SHA and sha(LIVE) == LIVE_SHA, "final X2 migration receipts changed")
    saved, live = (json.loads(path.read_text(encoding="utf-8")) for path in (SAVED, LIVE))
    expected = {"Path", "Length", "SHA256", "SavedAt", "BlenderVersion", "ArtistPid", "UiReported", "PoseAsset", "CharacterDesigner"}
    need(set(saved) == expected and Path(saved["Path"]).resolve() == base.ARTIST.resolve()
         and saved["SHA256"].lower() == ARTIST_SHA and type(saved["Length"]) is int and saved["Length"] == ARTIST_BYTES
         and saved["BlenderVersion"] == "5.2.0 LTS" and saved["UiReported"] == "Saved X.blend"
         and type(saved["ArtistPid"]) is int and saved["ArtistPid"] == 12696,
         "typed saved52 schema/content is not the authorized final save")
    need(live["pid"] == saved["ArtistPid"] and live["blender_version"] == saved["BlenderVersion"]
         and Path(live["filepath"]).resolve() == base.ARTIST.resolve()
         and Path(live["blender_binary"]).resolve() == Path("D:/Blender5.2/blender.exe").resolve()
         and live["frame"] == 39 and live["object_mode"] == "POSE" and live["rig_bones"] == 346
         and live["hips_display_scale"] == [0., 0., 0.] and live["character_designer_enabled"] is True,
         "matching X2 live52 receipt failed")
    need(base.ARTIST.stat().st_size == ARTIST_BYTES and sha(base.ARTIST) == ARTIST_SHA,
         "current artist differs from the final X2 saved bytes")
    return {"saved52": {"path": str(SAVED), "sha256": SAVED_SHA, "receipt": saved},
            "live52": {"path": str(LIVE), "sha256": LIVE_SHA, "receipt": live},
            "current_artist_sha256": ARTIST_SHA, "artist_equals_7ac_fullraw": "Unmeasured",
            "artist_loaded_saved_or_modified_by_this_candidate": False,
            "installed_UI_release_is_canonical_QA_source": False}


def quarantine_proof(source, rig, record, actual, clone, body, cloth, graph, qa, surface):
    holder = qa.skirt.physics_control(source)[0]
    need(float(holder["physics_influence"]) == 0., "old bone physics must remain public Manual influence0")
    dress_names = {name for chain in record["chains"] for role in ("def", "manual", "phys") for name in chain[role]}
    waist = record["controls"]["waist"]
    deformer_names = {group.name for group in actual.vertex_groups if group.name in rig.data.bones}
    need(deformer_names == {waist} and actual.modifiers[0].type == "ARMATURE"
         and actual.modifiers[0].object == rig and actual.modifiers[0].use_vertex_groups
         and not actual.modifiers[0].use_bone_envelopes,
         "quarantined oldC has non-Waist bone input")
    index = actual.vertex_groups[waist].index
    need(all(any(weight.group == index and weight.weight == 1. for weight in vertex.groups)
             for vertex in actual.data.vertices), "oldC all800 Waist-only unit weights changed")
    body_rows = {}
    for obj in (body, clone):
        intersection = sorted({group.name for group in obj.vertex_groups} & dress_names)
        need(not intersection, "Body/actual Body clone groups read Dress DEF/MCH/PHYS: " + str(intersection))
        arms = [mod for mod in obj.modifiers if mod.type == "ARMATURE"]
        need(arms and all(mod.object == rig and mod.use_vertex_groups and not mod.use_bone_envelopes for mod in arms),
             "unknown Body skin/deformer target")
        body_rows[obj.name] = {"dress_group_intersection": intersection, "native_skin_rig": rig.name,
            "vertex_groups": [(group.name, int(group.index)) for group in obj.vertex_groups]}
    tracker = record["physics"]["surface"]["tracker"]
    physical = []
    for chain in record["chains"]:
        for name, phys in zip(chain["def"], chain["phys"]):
            copies = [con for con in rig.pose.bones[name].constraints if con.type == "COPY_ROTATION" and con.subtarget == phys]
            tracks = [con for con in rig.pose.bones[phys].constraints if con.type == "DAMPED_TRACK"]
            need(len(copies) == 1 and copies[0].target == rig and len(tracks) == 1
                 and tracks[0].target is not None and tracks[0].target.name == tracker,
                 "old physical target identity was changed or is unknown")
            evaluated = rig.evaluated_get(graph).pose.bones[name].constraints[copies[0].name]
            need(float(evaluated.influence) == 0., "native evaluated old PHYS copy is not zero")
            physical.append({"def": name, "phys": phys, "copy_pointer": int(copies[0].as_pointer()),
                "track_pointer": int(tracks[0].as_pointer()), "tracker": tracker, "evaluated_influence": 0.})
    return {"old_targets_retained": physical, "oldC_only_deformer": waist, "Body_group_proofs": body_rows,
            "newCloth_or_feedback_exercised": False, "oldC_flags": [bool(cloth.show_viewport), bool(cloth.show_render)]}


def audit_direct(meshes, attachment, values):
    rig, source, actual, surface, qa = (values[key] for key in ("rig", "source", "actual", "surface", "qa"))
    rows = []
    for obj in meshes:
        reference = source if obj is values["before"] else actual
        need(obj is not source and obj.data != source.data and obj.data.users == 1 and obj.parent == rig
             and surface._frame(obj) == surface._frame(reference), "independent DirectMain input chart differs")
        need(obj.modifiers[0].type == "ARMATURE" and obj.modifiers[0].object == rig
             and all(mod.type != "CLOTH" for mod in obj.modifiers), "DirectMain first skin/NoCloth structure differs")
        need(surface._rna(obj.modifiers[0]) == surface._rna(source.modifiers[0]), "copied original native skin RNA differs")
        for owner in (obj, obj.data, obj.data.shape_keys):
            need(owner is None or owner.animation_data is None, "DirectMain private input has its own animation/driver/NLA")
        rows.append({"object": obj.name, "mesh": obj.data.name, "parent": rig.name, "skin": rig.name,
                     "raw_current_Keys": values["base"].key_values(obj), "raw_contract": qa.digest(qa.raw_mesh_content(obj))})
    need(attachment.is_bound and attachment.target == values["clone"] and attachment.use_sparse_bind
         and not attachment.invert_vertex_group and attachment.strength == 1., "native raw80 copied bind changed")
    return {"native_meshes": rows, "private_Rig_created": False, "private_raw_drivers_created": 0,
            "source_first_skin_reused": True, "retarget_oldPHYS": False}


def exercise_direct(values, base):
    import bpy
    from mathutils import Quaternion, Vector
    source, rig, record, before, after, oracle, cloth, actual, clone, home, qa, diag, surface, same, read, report, write, budget, metres, guard, controls, manual, deform, upstream, waist, forbidden, ring, height, legs, axes, raw_contract, original_group_count = (
        values[key] for key in ("source", "rig", "record", "before", "after", "oracle", "cloth", "actual", "clone", "home", "qa", "diag", "surface", "same", "read", "report", "write", "budget", "metres", "guard", "controls", "manual", "deform", "upstream", "waist", "forbidden", "ring", "height", "legs", "axes", "raw_contract", "original_group_count"))
    values["base"] = base
    state = _CORE._STATE
    report["stage"] = STAGE
    report["scope"] = "Live original MainRig native Manual skin and raw80 Body attachment; old bone physics0. No input Rig/rawdriver replication, new Cloth, absolute final output, artist integration or automatic Original semantic proof."
    report["automatic_Original_semantic_acceptance"] = False
    report["live_solver_feedback_exercised"] = False
    need(base.key_values(source) is None, "this first exact7ac fixture cannot claim live Keys support")
    work_pose = qa.pose_channels(rig); state["bound_qa_action"] = None
    thigh_name, knee_name = legs["L"]["chain"][:2]
    hem_name, root_name = record["controls"]["hem"], "CTRL_master"
    thigh, root, hem = (rig.pose.bones[name] for name in (thigh_name, root_name, hem_name))
    need(root.rotation_mode == "XYZ" and thigh.rotation_mode == "QUATERNION", "native Root XYZ/leg Quaternion modes differ from exact fixture; no guessed conversion")
    old_thigh, old_root, old_hem = Quaternion(thigh.rotation_quaternion), Vector(root.rotation_euler), Vector(hem.location)
    keyed = {thigh.path_from_id("rotation_quaternion"), root.path_from_id("rotation_euler"), hem.path_from_id("location")}
    need(not any(curve.data_path in keyed for curve in rig.animation_data.drivers), "author rotation/location driver conflicts with chosen QA input")
    action = bpy.data.actions.new("QA Dress Direct Main Inputs")
    state["qa_action"], state["qa_action_pointer"] = action, action.as_pointer()
    rig.animation_data.action = action; state["bound_qa_action"] = action
    for frame, angle, turn, offset in ((1, 0., 0., 0.), (3, .35, .08, height*.03), (5, -.18, -.04, -height*.02)):
        thigh.rotation_quaternion = old_thigh @ Quaternion(axes[thigh_name], angle)
        root.rotation_euler = old_root + Vector((0., 0., turn))
        hem.location = old_hem + Vector((offset, 0., 0.))
        need(thigh.keyframe_insert(data_path="rotation_quaternion", frame=frame, group="QA Leg")
             and root.keyframe_insert(data_path="rotation_euler", frame=frame, group="QA Root")
             and hem.keyframe_insert(data_path="location", frame=frame, group="QA Dress"), "native own Action insertion failed")
    curves = qa.curve_paths(action); state["action_paths"] = {(curve.data_path, int(curve.array_index)) for curve in curves}
    expected = {(thigh.path_from_id("rotation_quaternion"), index) for index in range(4)} | {(root.path_from_id("rotation_euler"), index) for index in range(3)} | {(hem.path_from_id("location"), index) for index in range(3)}
    need(state["action_paths"] == expected and len(curves) == 10 and rig.animation_data.action_slot is not None, "native10curve ownAction/slot differs")
    for curve in curves:
        for point in curve.keyframe_points: point.interpolation = "LINEAR"
    need(not cloth.show_viewport and not cloth.show_render, "old Cloth must be paused before seeks")
    frozen_cache = same.cache_state(cloth, qa); identities = None; samples = []; sequential = {}; bodies = {}
    def sample(label):
        nonlocal identities
        budget(); began = time.perf_counter(); bpy.context.view_layer.update(); graph = bpy.context.evaluated_depsgraph_get(); graph_seconds = time.perf_counter()-began
        raw_program = _CORE.raw_source_program_guard(rig, deform)
        closure = _CORE._STATE["closure"](source, rig, record, manual, controls, upstream+[waist], forbidden, graph, surface)
        quarantine = quarantine_proof(source, rig, record, actual, clone, values["body"], cloth, graph, qa, surface)
        refs = audit_direct((before, after), after.modifiers[1], values); meshes = {}; clocks = {}
        for name, obj in (("oracle", oracle), ("before800", before), ("after800", after)):
            began = time.perf_counter(); meshes[name] = read.native_mesh(obj, graph, diag); clocks[name] = time.perf_counter()-began
        fields = ("native_vertex_index_order", "edges", "faces", "weights", "native_group_mapping")
        identity = {name: {field: mesh[field] for field in fields} for name, mesh in meshes.items()}
        need(all(len(mesh["points"]) == 800 and mesh["native_vertex_index_order"] == list(range(800)) and mesh["weights_complete"] for mesh in meshes.values()), "native800 topology/weight coverage missing")
        if identities is None: identities = identity
        need(identity == identities, "native DirectMain mapping/weights drifted")
        raw_after = qa.raw_mesh_content(after); raw_after["groups"] = raw_after["groups"][:original_group_count]
        raw_after["weights"] = [[weight for weight in row if weight[0] < original_group_count] for row in raw_after["weights"]]
        need(qa.raw_mesh_content(before) == raw_contract and raw_after == raw_contract, "author groups/UV/weights/Keys content changed")
        error = base.error_summary(meshes["before800"]["points"], meshes["oracle"]["points"], metres)
        effect = {"raw80": base.error_summary(meshes["after800"]["points"], meshes["before800"]["points"], metres, ring),
                  "outside720": base.error_summary(meshes["after800"]["points"], meshes["before800"]["points"], metres, [index for index in range(800) if index not in set(ring)])}
        charts = {"before": base.native_world_copy_proof(meshes["before800"]["matrix_world"], source.evaluated_get(graph).matrix_world, "Direct before native world"),
                  "after": base.native_world_copy_proof(meshes["after800"]["matrix_world"], actual.evaluated_get(graph).matrix_world, "Direct after native world")}
        posed = rig.evaluated_get(graph); knee = list(posed.matrix_world @ posed.pose.bones[knee_name].head)
        handle = list(posed.matrix_world @ posed.pose.bones[hem_name].matrix.translation)
        row = {"label": label, "frame": [home.frame_current, home.frame_subframe], "original_active": qa.original.active(rig),
               "before800_vs_native_Main_oracle": error, "attachment_effect": effect, "charts": charts,
               "raw_source_program": raw_program, "current_manual_closure": closure, "legacy_quarantine": quarantine, "reference_audit": refs,
               "cache_exact": same.cache_state(cloth, qa) == frozen_cache, "knee_world": knee, "hem_world": handle,
               "Root_raw_channels": base.channels(root), "original_DEF_raw_channels": {name: base.channels(rig.pose.bones[name]) for name in sorted(deform)},
               "native_timing_segments": {"graph_ready_seconds": graph_seconds, "readback_seconds": clocks, "scope": "Native Python update/readback; not solver-only time or GUI FPS"},
               "mesh_summaries": {name: same.summary(mesh["points"], qa) for name, mesh in meshes.items()}, "accepted": False}
        if label in {"action_1_sequential", "action_3_sequential"}:
            began = time.perf_counter(); points = qa.world_mesh(values["body"], graph)["points"]
            need(points and qa.finite(points), "registered actual Body unavailable/nonfinite")
            bodies[home.frame_current] = points; row["registered_Body_summary"] = same.summary(points, qa)
            row["native_timing_segments"]["registered_Body_readback_seconds"] = time.perf_counter()-began
        samples.append(row); report["direct_live_samples"] = samples; write()
        need(error["maximum_m"] == 0. and error["maximum_m"] <= guard, "DirectMain first skin not exact original native oracle")
        need(effect["outside720"]["maximum_m"] <= guard and row["cache_exact"], "raw80 outside720/originalcache guard failed")
        return {"row": row, "points": {name: mesh["points"] for name, mesh in meshes.items()}, "knee": knee, "hem": handle}
    for frame in (1, 2, 3, 4, 5, 3, 1, 5):
        budget(); began = time.perf_counter(); home.frame_set(frame); frame_seconds = time.perf_counter()-began
        current = sample("action_"+str(frame)+("_seek" if frame in sequential else "_sequential")); current["row"]["frame_set_seconds"] = frame_seconds
        if frame in sequential:
            errors = {name: base.error_summary(current["points"][name], sequential[frame]["points"][name], metres) for name in current["points"]}
            report.setdefault("native_seek_replay", []).append({"frame": frame, "errors": errors}); write()
            need(all(row["maximum_m"] <= guard for row in errors.values()), "native seek replay > original50um")
        else: sequential[frame] = current
    response = {"knee_1_3_m": math.dist(sequential[1]["knee"], sequential[3]["knee"])*metres,
                "hem_1_3_m": math.dist(sequential[1]["hem"], sequential[3]["hem"])*metres,
                "native800_1_3": base.error_summary(sequential[1]["points"]["before800"], sequential[3]["points"]["before800"], metres),
                "registered_Body_1_3": base.error_summary(bodies[1], bodies[3], metres)}
    report["live_Action_input_response"] = response; write()
    need(response["knee_1_3_m"] > height*.01*metres and response["hem_1_3_m"] > guard
         and response["native800_1_3"]["maximum_m"] > guard and response["registered_Body_1_3"]["maximum_m"] > guard, "realRoot/leg/Hem/nativeinput response absent")
    rig.animation_data.action = None; state["bound_qa_action"] = None
    _CORE.restore_pose(rig, work_pose); home.frame_set(state["frame"][0], subframe=state["frame"][1]); bpy.context.view_layer.update()
    cloth.show_viewport, cloth.show_render = state["cloth_flags"]; bpy.context.view_layer.update()
    need(same.cache_state(cloth, qa) == frozen_cache, "originalcache changed during paused seeks/restoration")
    surface.validate(source, rig, qa.skirt.read_record(source))
    original_frame = (home.frame_current, home.frame_subframe)
    c_before = qa.world_mesh(actual, bpy.context.evaluated_depsgraph_get())["points"]
    report["C_after_Action_restore_vs_before_pause"] = base.error_summary(c_before, state["initial_C"], metres); write()
    need(report["C_after_Action_restore_vs_before_pause"]["maximum_m"] == 0., "restored original sameframe C changed")
    before_switch = sample("public_Controls_before_Original")
    qa.skirt._activate(bpy.context, rig, "POSE"); qa.public_switch(bpy.ops.character_designer.body_original_mode, action="ORIGINAL")
    need(qa.original.active(rig), "public Original did not enter")
    entered = sample("public_Original_enter")
    enter_error = base.error_summary(entered["points"]["before800"], before_switch["points"]["before800"], metres)
    report["public_Original_enter_input_jump"] = enter_error; write(); need(enter_error["maximum_m"] <= guard, "Manual Original enter >50um")
    weighted = [name for name in sorted(deform) if any(source.vertex_groups[w.group].name == name and w.weight > 0. for vertex in source.data.vertices for w in vertex.groups)]
    need(weighted, "no positively weighted original DEF")
    bone = rig.pose.bones[weighted[0]]; bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = Quaternion(bone.rotation_quaternion) @ Quaternion(Vector((1., 0., 0.)), .1)
    rig.update_tag(); bpy.context.view_layer.update(); edited = sample("public_Original_DEF_edit")
    edit_error = base.error_summary(edited["points"]["before800"], entered["points"]["before800"], metres)
    report["public_Original_real_DEF_response"] = {"bone": bone.name, "angle_rad": .1, "native_input_change": edit_error}; write()
    need(edit_error["maximum_m"] > guard, "realOriginal edit did not affect native manual input")
    qa.public_switch(bpy.ops.character_designer.body_original_mode, action="CONTROLS"); need(not qa.original.active(rig), "public Controls return failed")
    returned = sample("public_Controls_after_Original")
    leave_error = base.error_summary(returned["points"]["before800"], edited["points"]["before800"], metres)
    from character_designer import skirt_original_mode
    expected_correction = {"weighted_bone": bone.name, "manual_mix_mode": rig.pose.bones[bone.name].constraints["Skirt manual pose"].mix_mode,
                           "correction_metadata_present": bool(source.get(skirt_original_mode.CORRECTIONS))}
    c_after = qa.world_mesh(actual, bpy.context.evaluated_depsgraph_get())["points"]
    cache_guard = {"maximum_m": base.error_summary(c_after, c_before, metres)["maximum_m"],
                   "frame_exact": (home.frame_current, home.frame_subframe) == original_frame, "cache_exact": same.cache_state(cloth, qa) == frozen_cache}
    report["public_Original_return_input_jump"], report["public_Original_expected_correction"], report["same_frame_C_guard"] = leave_error, expected_correction, cache_guard; write()
    need(leave_error["maximum_m"] <= guard and cache_guard["maximum_m"] == 0. and cache_guard["frame_exact"] and cache_guard["cache_exact"], "Originalreturn/C/cache guard failed")
    need(expected_correction["manual_mix_mode"] == "BEFORE_FULL" and expected_correction["correction_metadata_present"], "persistent Manual Original correction absent")
    report["Keys_exercise"] = {"source_Keys": None, "original_raw_values_preserved": True, "live_Key_Action_NLA_verified": False}
    report["direct_main_manual_input_success"] = True
    report["new_backend_coldinstall_migration_or_Unity_verified"] = False
    report["before_attachment_reproduction_complete"] = report["native_completed"] = report["native_endpoint_index_identity_exact"] = True
    values["endpoint_path"].write_text(json.dumps({"stage": STAGE, "scope": "Compact native point hashes/identities; no fullBody arrays",
        "samples": [{"label": row["label"], "frame": row["frame"], "mesh_summaries": row["mesh_summaries"]} for row in samples], "accepted": False}, indent=2, allow_nan=False), encoding="utf-8")


def modified_program(base, core):
    main, closure, inherited = core.modified_sources(base); edits = []
    def replace(text, old, new, label):
        need(text.count(old) == 1, "frozen replacement not unique: "+label); edits.append(label); return text.replace(old, new, 1)
    main = replace(main, "bpy.app.version[:2] == (5,1)", "bpy.app.version[:2] == (5,2)", "only5.2 factory minor guard")
    main = replace(main, "Root-leased empty factory Blender5.1 only", "Root-leased empty factory Blender5.2 only", "version message truthful")
    start = main.index('        budget(); input_rig=copy_object(rig,"QA Dress Input Rig")')
    stop = main.index("        # Native copied bound SurfaceDeform;", start)
    construction = '''        input_rig=rig  # Same original Main; no private Rig or raw drivers.
        wires=[]
        before=copy_object(source,"QA Direct Main Input Before Body")
        for modifier in list(before.modifiers)[1:]: before.modifiers.remove(modifier)
        link(before)
        clone=bpy.data.objects[record["physics"]["colliders"][-1]]
        original_group_count=len(source.vertex_groups)
'''
    main = main[:start]+construction+main[stop:]; edits.append("remove all privateRig/driver/derivedRest creation")
    main = replace(main, 'after.name="QA Input800 After Body"', 'after.name="QA Direct Main Input After Body"', "new helper name")
    main = replace(main, 'report["input_rig_rest"]=surface._rest(input_rig,keep);', 'report["direct_Main_Rest_reference"]=surface._rest(rig,keep);', "Main reference not claimed privateRig")
    main = replace(main, '        exercise_live(locals(), FROZEN_BASE)', '        exercise_direct(locals(), FROZEN_BASE)', "Direct nativeAction/publicManualOriginal")
    need("copy_object(rig" not in main and "driver_inventory(" not in main and "setup_live_drivers(" not in main
         and "edit_bones" not in main and "sample_raw(" not in main, "private bridge construction still executable")
    return main, closure, inherited, edits


def prepared_namespace(core, base):
    main, closure, inherited, edits = modified_program(base, core)
    namespace = dict(vars(base)); namespace.update(vars(core)); namespace.update(globals())
    namespace["__file__"] = str(Path(__file__)); namespace["FROZEN_BASE"] = base
    pins = dict(base.PINS); pins[base.ARTIST] = ARTIST_SHA
    pins.update({CORE: CORE_SHA, core.BASE_PATH: core.BASE_SHA, core.BASE_RESULT: core.BASE_RESULT_SHA,
                 SAVED: SAVED_SHA, LIVE: LIVE_SHA, Path(__file__): sha(Path(__file__))})
    namespace["PINS"] = pins
    exec(compile(closure, str(Path(__file__)), "exec"), namespace)
    exec(compile(main, str(Path(__file__)), "exec"), namespace)
    namespace["restore_program"] = core.restore_program
    def capture(*values):
        receipt = core.capture_program(*values); core._STATE["closure"] = namespace["current_main_manual_closure"]
        report = values[-1]; bpy = __import__("bpy")
        report["stage"] = STAGE; report["scope"] = __doc__
        report["runtime52"] = {"version": list(bpy.app.version), "version_string": bpy.app.version_string,
            "binary": bpy.app.binary_path, "build_hash": bpy.app.build_hash.decode("utf-8", errors="replace"),
            "build_branch": bpy.app.build_branch.decode("utf-8", errors="replace"), "python": list(sys.version_info[:3]),
            "canonical_QA_source": str(values[5].__file__), "historical_5_1_native_result_revalidated_on_5_2": False}
        report["X2_typed_artist_protection"] = transition_proof(base)
        need(tuple(bpy.app.version[:3]) == (5,2,0) and Path(bpy.app.binary_path).resolve() == Path("D:/Blender5.2/blender.exe").resolve(), "runtime differs from actual X2 target")
        report["QA_source_substitutions"] = {"immutable_e939_inherited": inherited, "direct52_only": edits}
        return receipt
    namespace["capture_program"] = capture
    core._STATE["closure"] = namespace["current_main_manual_closure"]
    return namespace


def pure_checks():
    core = load_core(); base = core.load_base(); transition = transition_proof(base)
    main, closure, inherited, edits = modified_program(base, core)
    ast.parse(main); ast.parse(closure); compile(main, str(Path(__file__)), "exec")
    need(len(inherited) == 11 and len(edits) == 6, "bounded source adaptation count differs")
    tree = ast.parse(inspect.getsource(exercise_direct)); calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    need(not any(isinstance(node.func, ast.Attribute) and node.func.attr in {"driver_add", "bake", "free_bake", "restore_channels"} for node in calls), "Direct routine has forbidden bridge/cache API")
    need('error["maximum_m"] == 0.' in inspect.getsource(exercise_direct) and 'effect["outside720"]["maximum_m"] <= guard' in inspect.getsource(exercise_direct), "exact firstSkin/original50um/outside720 gate absent")
    namespace = prepared_namespace(core, base)
    need(namespace["main"].__globals__ is namespace and namespace["capture_program"] is namespace["main"].__globals__["capture_program"]
         and namespace["restore_program"] is core.restore_program and namespace["PINS"][base.ARTIST] == ARTIST_SHA,
         "compiled native recipe/protection globals do not match")
    actual = {base.REPOSITORY/"addons/character_designer/skirt_rig.py": {"_activate": 2, "physics_control": 1},
              HERE/"validate_real_dress.py": {"curve_paths": 1, "world_mesh": 2, "pose_channels": 1, "public_switch": 1},
              HERE/"verify_actual_body_proxy_coverage.py": {"native_mesh": 3}}
    count = 0
    for path, wanted in actual.items():
        definitions = {node.name: node for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef)}
        for name, arity in wanted.items():
            need(name in definitions, "actual native API missing: "+name); node = definitions[name]
            need(len(node.args.args)-len(node.args.defaults) <= arity <= len(node.args.args), "native arity mismatch: "+name); count += 1
    return {"passed": True, "source_adaptations": len(edits), "actual_native_API_sites": count,
            "frozen_e939_pure": core.pure_checks(), "artist_typed_save_receipts_verified": bool(transition),
            "native_run": False, "accepted": False, "Keys_and_newCloth_unverified": True}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path); parser.add_argument("--max-seconds", type=float, default=120.)
    parser.add_argument("--pure-checks", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and not args.output.exists()
             and args.output.resolve().is_relative_to(HERE) and args.output.resolve() != HERE, "fresh private Validation output only")
        need(0. < args.max_seconds <= 120., "Root external180 / soft120 only")
    return args


def main(args):
    global _CORE
    if args.pure_checks:
        print(json.dumps(pure_checks(), ensure_ascii=False)); return 0
    _CORE = load_core(); base = _CORE.load_base(); transition_proof(base)
    namespace = prepared_namespace(_CORE, base)
    return namespace["main"](args)


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
