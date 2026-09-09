"""Real-X mirror calibration transactions; only disposable copies are saved."""

import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest import mock

import bpy
import bmesh
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".codex-backups" / "forearm-twist-probe"
sys.path.insert(0, str(ROOT / "addons"))
sys.path.insert(0, str(ROOT / "tests"))
import character_designer
from character_designer import forearm_twist as twist
from character_designer.forearm_twist_symmetry import mirror_ring_pairs
from verify_real_x_forearm_twist_blender import activate, mesh_signature, pose_channels, skeleton_signature


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def open_source():
    assert twist._SESSION is None
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "X.blend"), load_ui=False, use_scripts=False)
    obj = bpy.data.objects["Cosha"]
    armature = obj.modifiers[0].object
    activate(obj)
    # Deliberately distinct poses: copying ratios must not synchronize hands.
    armature.pose.bones["hand.R"].rotation_quaternion = Quaternion((1, 0, 0), 0.12)
    bpy.context.view_layer.update()
    return obj, armature


def protected(obj, armature):
    return {"mesh": mesh_signature(obj), "pose": pose_channels(armature), "bones": skeleton_signature(armature)}


def assert_protected(obj, armature, before, *, allow_owned_keys=True):
    actual = protected(obj, armature)
    assert actual["pose"] == before["pose"], "A hand pose or rotation representation changed"
    assert actual["bones"] == before["bones"], "The bone/constraint structure changed"
    for field in ("vertices", "edges", "polygons", "groups", "weights", "modifiers"):
        assert actual["mesh"][field] == before["mesh"][field], field
    for name, value in before["mesh"]["keys"].items():
        if not name.startswith(twist.KEY_PREFIX):
            assert actual["mesh"]["keys"][name] == value, name
    if not allow_owned_keys:
        assert actual["mesh"]["keys"] == before["mesh"]["keys"]


def geometry_only(record):
    result = copy.deepcopy(record)
    result.pop("enabled", None)
    for ring in result["rings"]:
        ring.pop("ratio", None)
    return result


def key_snapshot(obj):
    return {key.name: {"coordinates": [tuple(point.co) for point in key.data], "value": key.value, "mute": key.mute}
            for key in obj.data.shape_keys.key_blocks}


def assert_pair(obj, armature):
    records = twist._records(obj)
    assert set(records) == {"L", "R"}
    pairs = mirror_ring_pairs(obj, armature, records["L"], records["R"])
    assert len(pairs) == 7
    assert all(records["L"]["rings"][left]["ratio"] == records["R"]["rings"][right]["ratio"] for left, right in pairs)
    assert len(records["L"]["vertices"]) == 96
    assert len(records["R"]["vertices"]) == 120
    assert set(records["L"]["vertices"]).isdisjoint(records["R"]["vertices"])
    return records


def case_cancel():
    obj, armature = open_source()
    before = protected(obj, armature)
    right_before = pose_channels(armature)["hand.R"]
    twist.start_test(bpy.context, obj, "L", symmetry=True)
    assert set(twist._records(obj)) == {"L"}
    assert twist.KEY_PREFIX + "R" not in obj.data.shape_keys.key_blocks
    assert pose_channels(armature)["hand.R"] == right_before
    twist.set_ratio(bpy.context, 2, 0.31)
    twist.finish_test(bpy.context, confirm=False)
    assert twist.RECORD_KEY not in obj and twist.PREVIEW_KEY not in obj
    assert_protected(obj, armature, before, allow_owned_keys=False)
    assert twist.controller_status(armature, "hand.L") == (False, "Forearm Twist: not calibrated")
    return {"right_not_created": True, "pose_and_source_data_exact": True}


def case_confirm_update_and_reopen():
    obj, armature = open_source()
    before = protected(obj, armature)
    right_before = pose_channels(armature)["hand.R"]
    twist.start_test(bpy.context, obj, "L", symmetry=True)
    assert twist.controller_status(armature, "hand.L")[0] is True
    assert twist.controller_status(armature, "hand.R")[0] is False
    twist.set_ratio(bpy.context, 2, 0.33)
    twist.set_ratio(bpy.context, 4, 0.82)
    assert pose_channels(armature)["hand.R"] == right_before
    twist.finish_test(bpy.context, confirm=True)
    records = assert_pair(obj, armature)
    assert records["L"]["rings"][2]["ratio"] == records["R"]["rings"][2]["ratio"] == 0.33
    assert records["L"]["enabled"] and records["R"]["enabled"]
    assert_protected(obj, armature, before)
    shapes_before = {side: geometry_only(record) for side, record in records.items()}
    key_pointers = {side: obj.data.shape_keys.key_blocks[record["key"]].as_pointer() for side, record in records.items()}

    # R -> L updates existing calibration, preserving its capture and key.
    twist.start_test(bpy.context, obj, "R", symmetry=True)
    twist.set_ratio(bpy.context, 1, 0.19)
    twist.set_ratio(bpy.context, 3, 0.57)
    twist.finish_test(bpy.context, confirm=True)
    records = assert_pair(obj, armature)
    for side in ("L", "R"):
        assert geometry_only(records[side]) == shapes_before[side]
        assert obj.data.shape_keys.key_blocks[records[side]["key"]].as_pointer() == key_pointers[side]
    assert records["L"]["rings"][3]["ratio"] == 0.57
    assert_protected(obj, armature, before)

    # Independent sync after a one-sided calibration change.
    twist.start_test(bpy.context, obj, "R", symmetry=False)
    twist.set_ratio(bpy.context, 2, 0.62)
    twist.finish_test(bpy.context, confirm=True)
    assert twist._records(obj)["L"]["rings"][2]["ratio"] == 0.33
    returned = twist.mirror_calibration(bpy.context, obj, "R")
    assert returned["chain"][1] == "forearm.L"
    records = assert_pair(obj, armature)
    assert records["L"]["rings"][2]["ratio"] == 0.62
    assert_protected(obj, armature, before)
    for side in ("L", "R"):
        assert geometry_only(records[side]) == shapes_before[side]

    statuses = {"active": twist.controller_status(armature, "hand.R")}
    assert statuses["active"] == (True, "Forearm Twist controls sleeve rotation")
    records["R"]["enabled"] = False
    twist._write_records(obj, records)
    twist.update_runtime(bpy.context.scene)
    statuses["disabled"] = twist.controller_status(armature, "hand.R")
    assert statuses["disabled"] == (False, "Forearm Twist disabled: original skinning")
    twist.mirror_calibration(bpy.context, obj, "R")
    assert not any(record["enabled"] for record in twist._records(obj).values())
    twist._ERRORS[obj.name] = "Injected status error"
    statuses["error"] = twist.controller_status(armature, "hand.R")
    assert statuses["error"] == (False, "Forearm Twist paused: check body panel")
    twist._ERRORS.pop(obj.name)
    records = twist._records(obj)
    records["R"]["enabled"] = True
    twist._write_records(obj, records)
    twist.mirror_calibration(bpy.context, obj, "R")
    assert all(record["enabled"] for record in twist._records(obj).values())
    assert twist.controller_status(armature, "hand.L")[0] is True
    assert twist.controller_status(armature, "hand.R")[0] is True
    assert_protected(obj, armature, before)

    # An existing target transaction must restore both keys if calculation fails.
    before_json, before_keys = obj[twist.RECORD_KEY], key_snapshot(obj)
    original_calculate = twist._calculate_object
    def fail_existing(mesh_obj, graph):
        mesh_obj.data.shape_keys.key_blocks[twist.KEY_PREFIX + "L"].data[0].co.x += 0.2
        raise ValueError("Injected existing target failure")
    with mock.patch.object(twist, "_calculate_object", side_effect=fail_existing):
        try:
            twist.mirror_calibration(bpy.context, obj, "R")
        except ValueError as error:
            assert "Injected" in str(error)
        else:
            raise AssertionError("Expected existing-target rollback")
    assert twist._calculate_object is original_calculate
    assert obj[twist.RECORD_KEY] == before_json
    assert key_snapshot(obj) == before_keys
    assert_protected(obj, armature, before)

    OUT.mkdir(parents=True, exist_ok=True)
    preview = OUT / "X-forearm-twist-symmetry-test.blend"
    assert preview.resolve() != (ROOT / "X.blend").resolve()
    saved_records = twist._records(obj)
    saved_pose = pose_channels(armature)
    bpy.ops.wm.save_as_mainfile(filepath=str(preview), copy=True)
    bpy.ops.wm.open_mainfile(filepath=str(preview), load_ui=False, use_scripts=False)
    obj = bpy.data.objects["Cosha"]
    armature = obj.modifiers[0].object
    bpy.context.view_layer.update()
    twist.update_runtime(bpy.context.scene)
    assert twist._records(obj) == saved_records
    assert pose_channels(armature) == saved_pose
    assert_pair(obj, armature)
    assert all(not obj.data.shape_keys.key_blocks[record["key"]].mute for record in saved_records.values())
    assert twist.controller_status(armature, "hand.L")[0] is True
    assert twist.controller_status(armature, "hand.R")[0] is True
    assert_protected(obj, armature, before)
    return {"directions": ["L -> R", "R -> L"], "native_support": {"L": 96, "R": 120},
            "existing_keys_reused": True, "status": statuses, "saved_copy": str(preview), "reopened_enabled": True}


def case_new_target_failure_keeps_cancel():
    obj, armature = open_source()
    before = protected(obj, armature)
    twist.start_test(bpy.context, obj, "L", symmetry=False)
    twist.set_ratio(bpy.context, 2, 0.27)
    twist.finish_test(bpy.context, confirm=True)
    initial_json = obj[twist.RECORD_KEY]
    initial_keys = key_snapshot(obj)
    twist.start_test(bpy.context, obj, "L", symmetry=True)
    twist.set_ratio(bpy.context, 2, 0.71)
    before_json, before_keys = obj[twist.RECORD_KEY], key_snapshot(obj)
    session = twist._SESSION
    preview_pose = pose_channels(armature)
    observed = {"right_key_created": False}
    def fail_new(mesh_obj, graph):
        observed["right_key_created"] = twist.KEY_PREFIX + "R" in mesh_obj.data.shape_keys.key_blocks
        assert set(twist._records(mesh_obj)) == {"L", "R"}
        mesh_obj.data.shape_keys.key_blocks[twist.KEY_PREFIX + "L"].data[0].co.x += 0.3
        raise ValueError("Injected new target failure")
    with mock.patch.object(twist, "_calculate_object", side_effect=fail_new):
        try:
            twist.finish_test(bpy.context, confirm=True)
        except ValueError as error:
            assert "Injected" in str(error)
        else:
            raise AssertionError("Expected new-target rollback")
    assert observed["right_key_created"]
    assert twist._SESSION is session
    assert twist.PREVIEW_KEY in obj
    assert obj[twist.RECORD_KEY] == before_json
    assert key_snapshot(obj) == before_keys
    assert twist.KEY_PREFIX + "R" not in obj.data.shape_keys.key_blocks
    assert pose_channels(armature) == preview_pose
    twist.finish_test(bpy.context, confirm=False)
    assert twist._SESSION is None and twist.PREVIEW_KEY not in obj
    assert obj[twist.RECORD_KEY] == initial_json
    assert key_snapshot(obj) == initial_keys
    assert_protected(obj, armature, before)
    return {"added_right_key_rolled_back": True, "all_key_coordinates_restored": True,
            "session_kept_cancel_available": True, "cancel_returned_original_left_calibration": True}


def edit_rest(obj, armature, *, both=True, along_axis=False):
    """Change actual Rest data in this disposable process, without posing."""
    activate(armature)
    mirror_editing = armature.data.use_mirror_x
    armature.data.use_mirror_x = False
    bpy.ops.object.mode_set(mode="EDIT")
    for side in (("L", "R") if both else ("L",)):
        upper = armature.data.edit_bones["upper_arm." + side]
        lower = armature.data.edit_bones["forearm." + side]
        hand = armature.data.edit_bones["hand." + side]
        if along_axis:
            head = lower.head + (lower.tail - lower.head).normalized() * 0.08
            upper.tail = head
            lower.head = head
        elif both:
            # Move the elbow and wrist perpendicular to the forearm by 3 mm.
            # This changes real head/tail data while retaining all seven loops.
            from mathutils import Vector
            delta = Vector((0, 0.003, 0))
            old_upper_tail, old_lower_head = upper.tail.copy(), lower.head.copy()
            old_lower_tail, old_hand_head, old_hand_tail = lower.tail.copy(), hand.head.copy(), hand.tail.copy()
            upper.tail = old_upper_tail + delta
            lower.head = old_lower_head + delta
            lower.tail = old_lower_tail + delta
            hand.head = old_hand_head + delta
            hand.tail = old_hand_tail + delta
        lower.roll += 0.13 if side == "L" else -0.13
        hand.roll += 0.07 if side == "L" else -0.07
    bpy.ops.object.mode_set(mode="OBJECT")
    armature.data.use_mirror_x = mirror_editing
    activate(obj)
    bpy.context.view_layer.update()
    twist.update_runtime(bpy.context.scene)


def assert_paused(obj, armature):
    assert obj.name in twist._ERRORS, "Stale Rest was not reported"
    assert "Rest" in twist._ERRORS[obj.name], twist._ERRORS[obj.name]
    assert twist.controller_status(armature, "hand.L")[0] is False
    assert all(obj.data.shape_keys.key_blocks[record["key"]].mute for record in twist._records(obj).values())


def ratios_by_vertices(record):
    return {frozenset(ring["vertices"]): ring["ratio"] for ring in record["rings"]}


def assert_rebind_current(obj, armature, keys_before, ratios_before):
    records = twist._records(obj)
    assert obj.name not in twist._ERRORS, twist._ERRORS.get(obj.name)
    for side, record in records.items():
        assert record["rest"] == twist._rest_signature(armature, record["chain"])
        assert obj.data.shape_keys.key_blocks[record["key"]].as_pointer() == keys_before[side]
        assert ratios_by_vertices(record) == ratios_before[side]
        assert not obj.data.shape_keys.key_blocks[record["key"]].mute
        assert twist.controller_status(armature, "hand." + side)[0] is True
    return records


def case_explicit_rest_rebind():
    obj, armature = open_source()
    twist.start_test(bpy.context, obj, "L", symmetry=True)
    twist.set_ratio(bpy.context, 2, 0.37)
    twist.finish_test(bpy.context, confirm=True)
    original_records = twist._records(obj)
    keys_before = {side: obj.data.shape_keys.key_blocks[record["key"]].as_pointer() for side, record in original_records.items()}
    ratios_before = {side: ratios_by_vertices(record) for side, record in original_records.items()}
    ownership_before = {side: record["created_basis"] for side, record in original_records.items()}
    edit_rest(obj, armature, both=True)
    assert_paused(obj, armature)
    assert all(original_records[side]["rest"] != twist._rest_signature(armature, original_records[side]["chain"]) for side in ("L", "R"))
    after_rest = protected(obj, armature)
    stale_json, stale_keys = obj[twist.RECORD_KEY], key_snapshot(obj)

    # Both sides stale: refuse preview before mutation; explicit Sync repairs
    # the pair without temporarily changing the unselected hand's calibration.
    try:
        twist.start_test(bpy.context, obj, "L", symmetry=True)
    except ValueError as error:
        assert "Sync" in str(error), str(error)
    else:
        raise AssertionError("Both-stale preview should request explicit Sync")
    assert twist._SESSION is None
    assert obj[twist.RECORD_KEY] == stale_json and key_snapshot(obj) == stale_keys
    assert_protected(obj, armature, after_rest)

    def fail_rebind(mesh_obj, graph):
        assert all(record["rest"] == twist._rest_signature(armature, record["chain"])
                   for record in twist._records(mesh_obj).values())
        mesh_obj.data.shape_keys.key_blocks[twist.KEY_PREFIX + "L"].data[0].co.y += 0.2
        raise ValueError("Injected rebind failure")
    with mock.patch.object(twist, "_calculate_object", side_effect=fail_rebind):
        try:
            twist.mirror_calibration(bpy.context, obj, "L")
        except ValueError as error:
            assert "Injected" in str(error)
        else:
            raise AssertionError("Expected atomic rebind rollback")
    assert obj[twist.RECORD_KEY] == stale_json and key_snapshot(obj) == stale_keys
    assert_paused(obj, armature)
    assert_protected(obj, armature, after_rest)
    twist.mirror_calibration(bpy.context, obj, "L")
    current_records = assert_rebind_current(obj, armature, keys_before, ratios_before)
    assert any(current_records[side]["positions"] != original_records[side]["positions"] for side in ("L", "R"))
    assert {side: record["created_basis"] for side, record in current_records.items()} == ownership_before
    assert_protected(obj, armature, after_rest)

    # Only source Rest is stale now. Its explicit preview may rebind, while
    # Cancel must restore the old stale JSON and leave the rig's Rest untouched.
    edit_rest(obj, armature, both=False)
    right_actual_rest = twist._rest_signature(armature, current_records["R"]["chain"])
    right_roundtrip_error = max(abs(first - second)
        for (_name, before_values), (_name2, after_values) in zip(current_records["R"]["rest"], right_actual_rest)
        for first, second in zip(before_values, after_values))
    print("SINGLE_SIDE_EDIT_OTHER_REST_ERROR=" + str(right_roundtrip_error))
    assert_paused(obj, armature)
    after_single_rest = protected(obj, armature)
    single_stale_json, single_stale_keys = obj[twist.RECORD_KEY], key_snapshot(obj)
    twist.start_test(bpy.context, obj, "L", symmetry=True)
    assert twist._records(obj)["L"]["rest"] == twist._rest_signature(armature, current_records["L"]["chain"])
    twist.set_ratio(bpy.context, 2, 0.41)
    twist.finish_test(bpy.context, confirm=False)
    assert obj[twist.RECORD_KEY] == single_stale_json
    assert key_snapshot(obj) == single_stale_keys
    assert_paused(obj, armature)
    assert_protected(obj, armature, after_single_rest)
    twist.start_test(bpy.context, obj, "L", symmetry=True)
    twist.set_ratio(bpy.context, 2, 0.41)
    twist.finish_test(bpy.context, confirm=True)
    expected_ratios = copy.deepcopy(ratios_before)
    for side in ("L", "R"):
        expected_ratios[side][frozenset(current_records[side]["rings"][2]["vertices"])] = 0.41
    assert_rebind_current(obj, armature, keys_before, expected_ratios)
    assert_protected(obj, armature, after_single_rest)

    # Actual Rest motion that loses captured loops is not migrated by index.
    edit_rest(obj, armature, both=False, along_axis=True)
    after_changed_loops = protected(obj, armature)
    changed_json, changed_keys = obj[twist.RECORD_KEY], key_snapshot(obj)
    try:
        twist.start_test(bpy.context, obj, "L", symmetry=False)
    except ValueError as error:
        assert "loops" in str(error).lower(), str(error)
        loop_error = str(error)
    else:
        raise AssertionError("Different captured loop sets must not migrate")
    assert twist._SESSION is None
    assert obj[twist.RECORD_KEY] == changed_json and key_snapshot(obj) == changed_keys
    assert_protected(obj, armature, after_changed_loops)

    # Actual topology edit (an extra diagonal) must refuse before any repair.
    record = twist._records(obj)["L"]
    first, second = record["rings"][3]["vertices"][0], record["rings"][3]["vertices"][2]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.new((bm.verts[first], bm.verts[second]))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    bpy.context.view_layer.update()
    twist.update_runtime(bpy.context.scene)
    after_topology = protected(obj, armature)
    topology_json, topology_keys = obj[twist.RECORD_KEY], key_snapshot(obj)
    try:
        twist.mirror_calibration(bpy.context, obj, "L")
    except ValueError as error:
        assert "topology" in str(error).lower(), str(error)
        topology_error = str(error)
    else:
        raise AssertionError("Changed topology must not be rebound")
    assert obj[twist.RECORD_KEY] == topology_json and key_snapshot(obj) == topology_keys
    assert_protected(obj, armature, after_topology)
    return {"stale_runtime_paused": True, "both_stale_preview_refused_without_mutation": True,
            "explicit_sync_rebound_same_keys_and_ratios": True, "single_stale_cancel_restored_json": True,
            "single_stale_confirm_committed": True, "rebind_failure_rolled_back": True,
            "different_loops_rejected": loop_error, "changed_topology_rejected": topology_error}


def main():
    source_digest = digest(ROOT / "X.blend")
    character_designer.register()
    if "--rest-only" in sys.argv:
        results = {"rest_rebind": case_explicit_rest_rebind()}
    else:
        results = {"cancel": case_cancel(), "confirm_update_reopen": case_confirm_update_and_reopen(),
                   "failure": case_new_target_failure_keeps_cancel(), "rest_rebind": case_explicit_rest_rebind()}
    assert digest(ROOT / "X.blend") == source_digest
    results["source_sha256_unchanged"] = source_digest
    OUT.mkdir(parents=True, exist_ok=True)
    output_name = "mirror-rest-rebind-test.json" if "--rest-only" in sys.argv else "mirror-runtime-test.json"
    (OUT / output_name).write_text(json.dumps(results, indent=2), encoding="utf8")
    print("FOREARM_TWIST_MIRROR_RUNTIME_TEST=" + json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    main()
