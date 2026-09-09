"""Automatic legacy migration, Rest rebind, undo and reload on disposable X.

All saves go below .codex-backups/forearm-twist-probe; X.blend is read-only.
"""

import copy
import hashlib
import importlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import addon_utils
import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".codex-backups" / "forearm-twist-probe"
sys.path.insert(0, str(ROOT / "addons"))
sys.path.insert(0, str(ROOT / "tests"))
from verify_real_x_forearm_twist_blender import activate, mesh_signature, pose_channels, skeleton_signature

MODULE = None
runtime = None
ENABLE_ERRORS = []


def enable_module():
    global MODULE, runtime
    def error_handler():
        import traceback
        ENABLE_ERRORS.append(traceback.format_exc())
    MODULE = addon_utils.enable("character_designer", default_set=False, persistent=False, handle_error=error_handler)
    assert MODULE is not None and not ENABLE_ERRORS, ENABLE_ERRORS
    runtime = importlib.import_module("character_designer.forearm_twist")
    assert Path(MODULE.__file__).resolve().parent == ROOT / "addons" / "character_designer"
    bpy.context.scene.frame_set(bpy.context.scene.frame_current + 1)
    assert runtime._RUNTIME_REGISTERED and not runtime._INITIALIZE_PENDING
    MODULE._validate_registration_integrity()


def disable_module():
    addon_utils.disable("character_designer", default_set=False)
    assert not addon_utils.check("character_designer")[1]
    assert not runtime._RUNTIME_REGISTERED
    if runtime._SCENE_CLEANUP_PENDING:
        runtime._complete_runtime_lifecycle()


@contextmanager
def suspended_updates():
    previous = runtime._BUSY
    runtime._BUSY = True
    try:
        yield
    finally:
        runtime._BUSY = previous


def key_snapshot(obj):
    return {key.name: {"co": [tuple(point.co) for point in key.data], "value": key.value, "mute": key.mute}
            for key in obj.data.shape_keys.key_blocks}


def protected(obj, armature):
    return {"mesh": mesh_signature(obj), "pose": pose_channels(armature), "bones": skeleton_signature(armature)}


def assert_protected(obj, armature, before):
    after = protected(obj, armature)
    assert after["pose"] == before["pose"]
    assert after["bones"] == before["bones"]
    for name in ("vertices", "edges", "polygons", "groups", "weights", "modifiers"):
        assert after["mesh"][name] == before["mesh"][name], name
    for name, key in before["mesh"]["keys"].items():
        if not name.startswith(runtime.KEY_PREFIX):
            assert after["mesh"]["keys"][name] == key, name


def open_source():
    assert runtime._SESSION is None
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "X.blend"), load_ui=False, use_scripts=False)
    obj = bpy.data.objects["Cosha"]
    armature = obj.modifiers[0].object
    activate(obj)
    # The project may now be saved with the previous version's calibration.
    # Clear only its owned outputs in this isolated fixture; keep the actual
    # saved IK and all existing non-owned shape keys, weights and topology.
    with suspended_updates():
        for side, record in runtime._records(obj).items():
            key = runtime._managed_key(obj, side, record, required=False, repair_name=False)
            if key is not None:
                obj.shape_key_remove(key)
        for name in (runtime.RECORD_KEY, runtime.PREVIEW_KEY):
            if name in obj:
                del obj[name]
        for identity in tuple(runtime._KEY_REFERENCES):
            if identity[0] == obj.as_pointer():
                runtime._KEY_REFERENCES.pop(identity, None)
        runtime._CACHE.pop(obj.as_pointer(), None)
        runtime._OUTPUT_CACHE.pop(obj.as_pointer(), None)
        runtime._ERRORS.pop(obj.name, None)
        runtime._set_render_lock(bpy.context.scene)
    _arm, rig = runtime._resolve_rig(obj, "R")
    target = armature.pose.bones[rig["target"].name]
    if target.rotation_mode == "XYZ":
        target.rotation_euler.x += 0.12
    else:
        target.rotation_quaternion = Quaternion((1, 0, 0), 0.12)
    bpy.context.view_layer.update()
    return obj, armature


def seed_legacy(obj, armature, side="L", *, enabled=True):
    """Simulate an old saved single-side record without running its handler."""
    with suspended_updates():
        _arm, rig = runtime._resolve_rig(obj, side)
        record = runtime._capture_record(obj, armature, rig, side, {})
        record.pop("paired", None)
        record.pop("profile_source", None)
        record["rings"][2]["ratio"] = 0.23
        record["rings"][4]["ratio"] = 0.67
        record["enabled"] = enabled
        key = obj.shape_key_add(name=record["key"], from_mix=False)
        key.relative_key = obj.data.shape_keys.reference_key
        key.value = 1.0
        runtime._KEY_REFERENCES[(obj.as_pointer(), side)] = key
        runtime._write_records(obj, {side: record})
    return copy.deepcopy(record)


def tick(obj=None):
    bpy.context.view_layer.update()
    runtime.update_runtime(bpy.context.scene)
    if obj is not None:
        assert obj.name not in runtime._ERRORS, runtime._ERRORS.get(obj.name)


def assert_pair(obj, armature, *, source="L", enabled=True):
    records = runtime._records(obj)
    assert set(records) == {"L", "R"}, records.keys()
    pairs = runtime.mirror_ring_pairs(obj, armature, records["L"], records["R"])
    assert len(pairs) == 7
    for left, right in pairs:
        assert records["L"]["rings"][left]["ratio"] == records["R"]["rings"][right]["ratio"]
    for side, record in records.items():
        _arm, rig = runtime._resolve_rig(obj, side)
        native = runtime._capture_record(obj, armature, rig, side,
                                         {other: value for other, value in records.items() if other != side},
                                         owned_record=record)
        assert record["vertices"] == native["vertices"]
        assert record["positions"] == native["positions"]
        assert record["rest"] == runtime._rest_signature(armature, record["chain"])
        assert record["enabled"] is enabled
        assert record.get("paired") is True and record.get("profile_source") == source
        key = obj.data.shape_keys.key_blocks[record["key"]]
        assert key.value == 1.0 and key.mute is not enabled
        assert runtime.controller_status(armature, rig["target"].name)[0] is enabled
    assert len([key for key in obj.data.shape_keys.key_blocks if key.name.startswith(runtime.KEY_PREFIX)]) == 2
    return records


def assert_idempotent(obj, count=12):
    expected_json = obj[runtime.RECORD_KEY]
    expected_keys = key_snapshot(obj)
    for _ in range(count):
        runtime.update_runtime(bpy.context.scene)
        bpy.context.view_layer.update()
    assert obj[runtime.RECORD_KEY] == expected_json
    assert key_snapshot(obj) == expected_keys


def move_rest(obj, armature):
    with suspended_updates():
        activate(armature)
        mirror = armature.data.use_mirror_x
        armature.data.use_mirror_x = False
        bpy.ops.object.mode_set(mode="EDIT")
        for side in ("L", "R"):
            upper, lower, hand = [armature.data.edit_bones[stem + "." + side] for stem in ("upper_arm", "forearm", "hand")]
            delta = Vector((0, 0.003, 0))
            points = [bone.head.copy() for bone in (lower, hand)] + [bone.tail.copy() for bone in (upper, lower, hand)]
            upper.tail = points[2] + delta
            lower.head, lower.tail = points[0] + delta, points[3] + delta
            hand.head, hand.tail = points[1] + delta, points[4] + delta
            lower.roll += 0.13 if side == "L" else -0.13
            hand.roll += 0.07 if side == "L" else -0.07
        bpy.ops.object.mode_set(mode="OBJECT")
        armature.data.use_mirror_x = mirror
        activate(obj)


def case_migration_and_rebind():
    results = {}
    for source in ("L", "R"):
        obj, armature = open_source()
        before = protected(obj, armature)
        legacy = seed_legacy(obj, armature, source)
        old_json, old_keys = obj[runtime.RECORD_KEY], key_snapshot(obj)
        prepared = runtime._prepare_runtime_records(obj)
        assert set(prepared) == {"L", "R"}
        assert obj[runtime.RECORD_KEY] == old_json and key_snapshot(obj) == old_keys
        tick(obj)
        records = assert_pair(obj, armature, source=source)
        assert records[source]["rings"][2]["ratio"] == legacy["rings"][2]["ratio"]
        assert records[source]["rings"][4]["ratio"] == legacy["rings"][4]["ratio"]
        assert_protected(obj, armature, before)
        assert_idempotent(obj)
        pointers = {side: obj.data.shape_keys.key_blocks[record["key"]].as_pointer() for side, record in records.items()}
        old_records = copy.deepcopy(records)
        move_rest(obj, armature)
        after_rest = protected(obj, armature)
        old_json, old_keys = obj[runtime.RECORD_KEY], key_snapshot(obj)
        prepared = runtime._prepare_runtime_records(obj)
        assert obj[runtime.RECORD_KEY] == old_json and key_snapshot(obj) == old_keys
        assert any(prepared[side]["rest"] != old_records[side]["rest"] for side in ("L", "R"))
        tick(obj)
        records = assert_pair(obj, armature, source=source)
        for side in ("L", "R"):
            assert obj.data.shape_keys.key_blocks[records[side]["key"]].as_pointer() == pointers[side]
            assert {frozenset(ring["vertices"]): ring["ratio"] for ring in records[side]["rings"]} == {
                frozenset(ring["vertices"]): ring["ratio"] for ring in old_records[side]["rings"]}
        assert_protected(obj, armature, after_rest)
        assert_idempotent(obj)
        results[source] = {"automatic_pair": True, "automatic_rest_rebind": True, "same_key_identity": True,
                           "read_only_preparation": True, "repeated_updates_stable": True}
    return results


def case_preview_isolation():
    obj, armature = open_source()
    before = protected(obj, armature)
    runtime.start_test(bpy.context, obj, "L", symmetry=True)
    runtime.set_ratio(bpy.context, 2, 0.91)
    for _ in range(6):
        tick(obj)
        assert set(runtime._records(obj)) == {"L"}
        assert runtime.KEY_PREFIX + "R" not in obj.data.shape_keys.key_blocks
    runtime.finish_test(bpy.context, confirm=False)
    tick()
    assert runtime.RECORD_KEY not in obj
    assert_protected(obj, armature, before)

    # A serialized marker without its live Python session must block automatic
    # pairing too, until the lifecycle callback restores its old state.
    runtime.start_test(bpy.context, obj, "L", symmetry=True)
    runtime.set_ratio(bpy.context, 2, 0.93)
    runtime._SESSION = None
    orphan_json = obj[runtime.RECORD_KEY]
    for _ in range(3):
        tick(obj)
        assert obj[runtime.RECORD_KEY] == orphan_json
        assert set(runtime._prepare_runtime_records(obj)) == {"L"}
        assert runtime.KEY_PREFIX + "R" not in obj.data.shape_keys.key_blocks
    runtime._undo_post(None)
    tick()
    assert runtime.RECORD_KEY not in obj and runtime.PREVIEW_KEY not in obj
    assert_protected(obj, armature, before)

    legacy = seed_legacy(obj, armature)
    expected_baseline = runtime._prepare_runtime_records(obj)
    runtime.start_test(bpy.context, obj, "L", symmetry=True)
    # Normal persistent migration runs before taking the preview snapshot.
    # Cancel restores that upgraded baseline, retaining the artist's shares;
    # it does not roll back a required single-side -> paired schema upgrade.
    baseline_json = runtime._SESSION["old_json"]
    assert json.loads(baseline_json) == expected_baseline
    right_baseline = copy.deepcopy(runtime._records(obj)["R"])
    right_key = runtime._records(obj)["R"]["key"]
    right_output = key_snapshot(obj)[right_key]
    runtime.set_ratio(bpy.context, 2, 0.92)
    for _ in range(6):
        tick(obj)
        assert set(runtime._records(obj)) == {"L", "R"}
        assert runtime._records(obj)["R"] == right_baseline
        assert key_snapshot(obj)[right_key] == right_output
        assert runtime._prepare_runtime_records(obj) == runtime._records(obj)
    runtime.finish_test(bpy.context, confirm=False, refresh=False)
    assert obj[runtime.RECORD_KEY] == baseline_json, "Cancel did not restore the whole upgraded baseline"
    tick(obj)
    records = assert_pair(obj, armature)
    assert records["L"]["rings"][2]["ratio"] == legacy["rings"][2]["ratio"]
    assert_protected(obj, armature, before)

    # Orphaned preview marker, as restored by undo/autosave or module reload.
    committed = obj[runtime.RECORD_KEY]
    runtime.start_test(bpy.context, obj, "L", symmetry=True)
    runtime.set_ratio(bpy.context, 2, 0.94)
    runtime._SESSION = None
    before_recovery = obj[runtime.RECORD_KEY]
    assert runtime._prepare_runtime_records(obj) == runtime._records(obj)
    assert obj[runtime.RECORD_KEY] == before_recovery
    runtime._undo_post(None)
    tick(obj)
    assert runtime.PREVIEW_KEY not in obj and runtime._SESSION is None
    assert obj[runtime.RECORD_KEY] == committed
    assert_protected(obj, armature, before)
    return {"new_preview_no_counterpart_before_confirm": True, "cancel_restores_whole_upgraded_baseline": True,
            "existing_preview_preserves_other_side": True, "orphan_marker_blocks_migration": True,
            "orphan_marker_recovered_before_migration": True}


def case_failure_and_edit_mode():
    obj, armature = open_source()
    before = protected(obj, armature)
    seed_legacy(obj, armature)
    old_json, old_keys = obj[runtime.RECORD_KEY], key_snapshot(obj)
    key_name = runtime.KEY_PREFIX + "L"
    old_pointer = obj.data.shape_keys.key_blocks[key_name].as_pointer()
    observed = {"added_counterpart_seen": False}
    def fail_calculation(*args, **kwargs):
        observed["added_counterpart_seen"] |= runtime.KEY_PREFIX + "R" in obj.data.shape_keys.key_blocks
        obj.data.shape_keys.key_blocks[key_name].data[0].co.x += 0.3
        raise ValueError("Injected automatic migration output failure")
    with mock.patch.object(runtime, "corrected_vertex", side_effect=fail_calculation):
        for _ in range(3):
            runtime.update_runtime(bpy.context.scene)
            assert obj[runtime.RECORD_KEY] == old_json
            assert runtime.KEY_PREFIX + "R" not in obj.data.shape_keys.key_blocks
            assert obj.data.shape_keys.key_blocks[key_name].as_pointer() == old_pointer
            assert obj.data.shape_keys.key_blocks[key_name].mute
            for name, key in old_keys.items():
                assert key_snapshot(obj)[name]["co"] == key["co"]
            assert obj.name in runtime._ERRORS
    assert observed["added_counterpart_seen"]
    tick(obj)
    assert_pair(obj, armature)
    assert_protected(obj, armature, before)
    assert_idempotent(obj)

    # Rebinding existing outputs must have the same transaction guarantees as
    # adding a counterpart: a failure cannot commit either new Rest metadata
    # or a partially written correction, and a later valid evaluation recovers.
    move_rest(obj, armature)
    after_rest = protected(obj, armature)
    old_json, old_keys = obj[runtime.RECORD_KEY], key_snapshot(obj)
    pointers = {side: obj.data.shape_keys.key_blocks[record["key"]].as_pointer()
                for side, record in runtime._records(obj).items()}
    with mock.patch.object(runtime, "corrected_vertex", side_effect=fail_calculation):
        runtime.update_runtime(bpy.context.scene)
        assert obj[runtime.RECORD_KEY] == old_json
        for name, key in old_keys.items():
            assert key_snapshot(obj)[name]["co"] == key["co"]
        assert all(obj.data.shape_keys.key_blocks[record["key"]].mute
                   for record in runtime._records(obj).values())
        assert obj.name in runtime._ERRORS
    tick(obj)
    records = assert_pair(obj, armature)
    for side, record in records.items():
        assert obj.data.shape_keys.key_blocks[record["key"]].as_pointer() == pointers[side]
    assert_protected(obj, armature, after_rest)
    assert_idempotent(obj)

    obj, armature = open_source()
    seed_legacy(obj, armature)
    old_json = obj[runtime.RECORD_KEY]
    with suspended_updates():
        bpy.ops.object.mode_set(mode="EDIT")
    runtime.update_runtime(bpy.context.scene)
    assert obj[runtime.RECORD_KEY] == old_json
    assert runtime.KEY_PREFIX + "R" not in obj.data.shape_keys.key_blocks
    assert obj.name in runtime._ERRORS
    bpy.ops.object.mode_set(mode="OBJECT")
    tick(obj)
    assert_pair(obj, armature)
    return {"partial_migration_rolled_back": True, "repeated_failures_no_extra_keys": True,
            "retry_recovers_automatically": True, "rest_rebind_failure_rolled_back": True,
            "mesh_edit_pauses_and_recovers": True}


def case_save_enable_reload():
    obj, armature = open_source()
    before = protected(obj, armature)
    seed_legacy(obj, armature)
    legacy_json = obj[runtime.RECORD_KEY]
    disable_module()
    assert obj[runtime.RECORD_KEY] == legacy_json
    assert obj.data.shape_keys.key_blocks[runtime.KEY_PREFIX + "L"].mute
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "X-legacy-forearm-auto-migration.blend"
    assert path.resolve() != (ROOT / "X.blend").resolve()
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True)
    enable_module()
    tick(obj)
    assert_pair(obj, armature)
    assert_protected(obj, armature, before)
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    obj, armature = bpy.data.objects["Cosha"], bpy.data.objects["CoshaRig"]
    tick(obj)
    assert_pair(obj, armature)
    assert_protected(obj, armature, before)
    committed = obj[runtime.RECORD_KEY]
    disable_module()
    assert all(obj.data.shape_keys.key_blocks[record["key"]].mute for record in runtime._records(obj).values())
    # Full package module replacement, matching a real code reload rather than
    # merely re-registering the same Python function objects.
    for name in tuple(sys.modules):
        if name == "character_designer" or name.startswith("character_designer."):
            del sys.modules[name]
    importlib.invalidate_caches()
    enable_module()
    tick(obj)
    assert obj[runtime.RECORD_KEY] == committed
    assert_pair(obj, armature)
    for name, handler in runtime._HANDLERS:
        assert getattr(bpy.app.handlers, name).count(handler) == 1
    assert_protected(obj, armature, before)
    assert_idempotent(obj)
    # Disabled calibration is a persistent artist choice across add-on reload.
    records = runtime._records(obj)
    records["L"]["enabled"] = False
    with suspended_updates():
        runtime._write_records(obj, records)
    tick(obj)
    assert_pair(obj, armature, enabled=False)
    disable_module()
    enable_module()
    tick(obj)
    assert_pair(obj, armature, enabled=False)
    return {"legacy_file": str(path), "save_reopen_auto_pairs": True, "disable_enable_recovers": True,
            "full_module_reload_recovers": True, "one_handler_per_event": True, "disabled_choice_preserved": True}


def case_real_undo_redo():
    obj, armature = open_source()
    seed_legacy(obj, armature)
    bpy.context.preferences.edit.use_global_undo = True
    # Snapshot an actual old single-side state. Undo into it must normalize
    # automatically without copying preview output into Basis or adding .001 keys.
    with suspended_updates():
        assert bpy.ops.ed.undo_push(message="Legacy single-side calibration") == {"FINISHED"}
    tick(obj)
    assert_pair(obj, armature)
    initial_ratio = runtime._records(obj)["L"]["rings"][2]["ratio"]
    assert bpy.ops.ed.undo_push(message="Automatic pair restored") == {"FINISHED"}
    with suspended_updates():
        records = runtime._records(obj)
        for record in records.values():
            record["rings"][2]["ratio"] = 0.73
        runtime._write_records(obj, records)
    tick(obj)
    assert bpy.ops.ed.undo_push(message="Changed paired loop share") == {"FINISHED"}
    assert bpy.ops.ed.undo() == {"FINISHED"}
    obj, armature = bpy.data.objects["Cosha"], bpy.data.objects["CoshaRig"]
    tick(obj)
    assert_pair(obj, armature)
    assert runtime._records(obj)["L"]["rings"][2]["ratio"] == initial_ratio
    assert bpy.ops.ed.redo() == {"FINISHED"}
    obj, armature = bpy.data.objects["Cosha"], bpy.data.objects["CoshaRig"]
    tick(obj)
    assert_pair(obj, armature)
    assert runtime._records(obj)["L"]["rings"][2]["ratio"] == 0.73
    assert bpy.ops.ed.undo() == {"FINISHED"}
    assert bpy.ops.ed.undo() == {"FINISHED"}
    obj, armature = bpy.data.objects["Cosha"], bpy.data.objects["CoshaRig"]
    tick(obj)
    assert_pair(obj, armature)
    assert runtime._records(obj)["L"]["rings"][2]["ratio"] == initial_ratio
    assert_idempotent(obj)
    return {"real_undo_redo": True, "legacy_undo_state_automatically_pairs": True, "no_duplicate_keys": True}


def main():
    source_hash = hashlib.sha256((ROOT / "X.blend").read_bytes()).hexdigest()
    enable_module()
    cases = {"migration_rebind": case_migration_and_rebind, "preview": case_preview_isolation,
             "failure_edit": case_failure_and_edit_mode, "reload": case_save_enable_reload,
             "undo": case_real_undo_redo}
    selected = sys.argv[sys.argv.index("--case") + 1] if "--case" in sys.argv else None
    results = {name: test() for name, test in cases.items() if selected is None or selected == name}
    assert hashlib.sha256((ROOT / "X.blend").read_bytes()).hexdigest() == source_hash
    results["source_sha256_unchanged"] = source_hash
    OUT.mkdir(parents=True, exist_ok=True)
    output = "auto-lifecycle-test.json" if selected is None else "auto-lifecycle-" + selected + ".json"
    (OUT / output).write_text(json.dumps(results, indent=2), encoding="utf8")
    print("FOREARM_TWIST_AUTO_LIFECYCLE_TEST=" + json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    main()
