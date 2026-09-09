"""Two-phase GUI Undo/Redo check for selected-bone Automatic Weights.

Build a temporary fixture first, then launch a normal Blender window with that
file so the loaded file is the global Undo baseline.
"""

import sys
import traceback
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT / "addons", PROJECT_ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import character_designer
from character_designer import selected_bone_weights
from test_selected_bone_weights_blender import (
    _deform_total,
    make_fixture,
    prepare_pose_context,
)


STATE = {}
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def view3d_context():
    window = bpy.context.window_manager.windows[0]
    area = next(area for area in window.screen.areas if area.type == "VIEW_3D")
    region = next(region for region in area.regions if region.type == "WINDOW")
    x = area.x + region.x + max(1, region.width // 2)
    y = area.y + region.y + max(1, region.height // 2)
    return window, area, region, x, y


def cleanup_keymap():
    keymap = STATE.get("keymap")
    keymap_item = STATE.get("keymap_item")
    if keymap is not None and keymap_item is not None:
        try:
            keymap.keymap_items.remove(keymap_item)
        except (ReferenceError, RuntimeError):
            pass


def fail(stage, exc):
    print(f"FAIL Selected Bone Weights GUI Undo at {stage}: {exc}", flush=True)
    traceback.print_exc()
    try:
        if hasattr(bpy.types, "CHARACTERDESIGNER_PT_weight_tools"):
            character_designer.unregister()
    finally:
        cleanup_keymap()
        bpy.ops.wm.quit_blender()
    return None


def build_fixture(filepath):
    mesh_obj, armature_obj, _modifier = make_fixture()
    mesh_obj.vertex_groups.remove(mesh_obj.vertex_groups["Bone.L"])
    prepare_pose_context(mesh_obj, armature_obj, ("Bone.L",))
    result = bpy.ops.wm.save_as_mainfile(filepath=filepath, check_existing=False)
    if result != {"FINISHED"}:
        raise AssertionError(f"Could not save Undo fixture: {result}")
    print(f"PASS Built Selected Bone Weights Undo fixture: {filepath}", flush=True)


def setup_and_weight():
    try:
        bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
        bpy.context.preferences.edit.use_global_undo = True
        character_designer.register()
        mesh_obj = bpy.data.objects["SelectedWeightMesh"]
        armature_obj = bpy.data.objects["SelectedWeightRig"]
        if bpy.context.mode != "POSE" or bpy.context.active_object is not armature_obj:
            prepare_pose_context(mesh_obj, armature_obj, ("Bone.L",))
        STATE["mesh_name"] = mesh_obj.name
        STATE["before"] = selected_bone_weights._capture_vertex_groups(mesh_obj)
        window_manager = bpy.context.window_manager
        keymap = window_manager.keyconfigs.active.keymaps.get("3D View")
        if keymap is None:
            raise AssertionError("The active 3D View keymap is unavailable")
        keymap_item = keymap.keymap_items.new(
            "character_designer.auto_weight_selected_bones",
            "F8",
            "PRESS",
        )
        keymap_item.properties.normalize_affected_deform_weights = True
        window_manager.keyconfigs.update()
        STATE.update(keymap=keymap, keymap_item=keymap_item)
        window, _area, _region, x, y = view3d_context()
        STATE.update(window=window, event_x=x, event_y=y)
        window.event_simulate(type="F8", value="PRESS", x=x, y=y)
        window.event_simulate(type="F8", value="RELEASE", x=x, y=y)
        bpy.app.timers.register(verify_weighted, first_interval=0.4)
    except Exception as exc:
        return fail("setup", exc)
    return None


def verify_weighted():
    try:
        mesh_obj = bpy.data.objects[STATE["mesh_name"]]
        STATE["after"] = selected_bone_weights._capture_vertex_groups(mesh_obj)
        if STATE["after"] == STATE["before"]:
            raise AssertionError("Automatic Weights made no change")
        if mesh_obj.vertex_groups.get("Bone.L") is None:
            raise AssertionError("Selected target group was not created")
        affected = tuple(
            vertex_index
            for vertex_index, weight in dict(
                selected_bone_weights._group_state_map(STATE["after"])["Bone.L"][
                    "weights"
                ]
            ).items()
            if weight > 1.0e-8
        )
        if not affected:
            raise AssertionError("Normalized operation has no affected vertices")
        armature_obj = bpy.data.objects["SelectedWeightRig"]
        if any(
            abs(_deform_total(mesh_obj, armature_obj, vertex_index) - 1.0) > 1.0e-5
            for vertex_index in affected
        ):
            raise AssertionError("The GUI operation did not normalize Deform totals")
        window = STATE["window"]
        window.event_simulate(
            type="Z",
            value="PRESS",
            ctrl=True,
            x=STATE["event_x"],
            y=STATE["event_y"],
        )
        window.event_simulate(
            type="Z",
            value="RELEASE",
            ctrl=True,
            x=STATE["event_x"],
            y=STATE["event_y"],
        )
        bpy.app.timers.register(verify_undo, first_interval=0.4)
    except Exception as exc:
        return fail("weighted", exc)
    return None


def verify_undo():
    try:
        mesh_obj = bpy.data.objects[STATE["mesh_name"]]
        actual = selected_bone_weights._capture_vertex_groups(mesh_obj)
        if actual != STATE["before"]:
            raise AssertionError("One Undo did not restore the exact pre-operation groups")
        if mesh_obj.vertex_groups.get("Bone.L") is not None:
            raise AssertionError("Undo did not remove the newly created selected group")
        window = STATE["window"]
        window.event_simulate(
            type="Z",
            value="PRESS",
            ctrl=True,
            shift=True,
            x=STATE["event_x"],
            y=STATE["event_y"],
        )
        window.event_simulate(
            type="Z",
            value="RELEASE",
            ctrl=True,
            shift=True,
            x=STATE["event_x"],
            y=STATE["event_y"],
        )
        bpy.app.timers.register(verify_redo, first_interval=0.4)
    except Exception as exc:
        return fail("verify undo", exc)
    return None


def verify_redo():
    try:
        mesh_obj = bpy.data.objects[STATE["mesh_name"]]
        actual = selected_bone_weights._capture_vertex_groups(mesh_obj)
        if actual != STATE["after"]:
            raise AssertionError("One Redo did not restore the exact weighted result")
        print("PASS Selected Bone Weights GUI Undo/Redo", flush=True)
        character_designer.unregister()
        cleanup_keymap()
        bpy.ops.wm.quit_blender()
    except Exception as exc:
        return fail("verify redo", exc)
    return None


if ARGS and ARGS[0] == "--build-fixture":
    if len(ARGS) != 2:
        raise SystemExit("Expected --build-fixture <absolute .blend path>")
    build_fixture(ARGS[1])
else:
    bpy.app.timers.register(setup_and_weight, first_interval=0.5)
