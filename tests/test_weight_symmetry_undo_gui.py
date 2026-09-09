"""Two-phase GUI Undo/Redo check for one-way Weight Symmetry.

Build a disposable fixture first, then launch a normal Blender window with the
fixture as the loaded-file Undo baseline.  The operator, Undo, and Redo are all
triggered through real 3D View key events.
"""

import sys
import tempfile
import traceback
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT / "addons", PROJECT_ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import character_designer
from test_weight_symmetry_blender import (
    LEFT_GROUP,
    RIGHT_GROUP,
    assert_left_to_right_contract,
    capture_groups,
    make_fixture,
)


STATE = {}
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
FIXTURE_PREFIX = "character_designer_weight_symmetry_undo"


def view3d_context():
    window = bpy.context.window_manager.windows[0]
    area = next(area for area in window.screen.areas if area.type == "VIEW_3D")
    region = next(region for region in area.regions if region.type == "WINDOW")
    x = area.x + region.x + max(1, region.width // 2)
    y = area.y + region.y + max(1, region.height // 2)
    return window, x, y


def cleanup_keymap():
    keymap = STATE.get("keymap")
    keymap_item = STATE.get("keymap_item")
    if keymap is not None and keymap_item is not None:
        try:
            keymap.keymap_items.remove(keymap_item)
        except (ReferenceError, RuntimeError):
            pass


def unregister_addon():
    if hasattr(bpy.types, "CHARACTER_DESIGNER_OT_copy_weight_to_opposite"):
        character_designer.unregister()


def cleanup_fixture_on_success():
    if not ARGS:
        return
    if len(ARGS) != 2 or ARGS[0] != "--cleanup-fixture":
        raise AssertionError(f"Unexpected GUI test arguments: {ARGS}")
    candidate = Path(ARGS[1]).resolve()
    loaded = Path(bpy.data.filepath).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if candidate != loaded:
        raise AssertionError(
            f"Cleanup target is not the loaded fixture: {candidate} != {loaded}"
        )
    if candidate.parent != temp_root:
        raise AssertionError(f"Cleanup target is outside the temp root: {candidate}")
    if candidate.suffix.lower() != ".blend" or not candidate.stem.startswith(
        FIXTURE_PREFIX
    ):
        raise AssertionError(f"Refusing unexpected fixture cleanup target: {candidate}")
    candidate.unlink()
    print(f"PASS Removed disposable Undo fixture: {candidate}", flush=True)


def fail(stage, exc):
    print(f"FAIL Weight Symmetry GUI Undo/Redo at {stage}: {exc}", flush=True)
    traceback.print_exc()
    try:
        unregister_addon()
    finally:
        cleanup_keymap()
        bpy.ops.wm.quit_blender()
    return None


def build_fixture(filepath):
    fixture = make_fixture(active_group=LEFT_GROUP)
    mesh_obj = fixture["mesh_obj"]
    if mesh_obj.vertex_groups.active is None:
        raise AssertionError("Fixture has no active source Vertex Group")
    if mesh_obj.vertex_groups.active.name != LEFT_GROUP:
        raise AssertionError("Fixture did not activate the left source group")
    result = bpy.ops.wm.save_as_mainfile(filepath=filepath, check_existing=False)
    if result != {"FINISHED"}:
        raise AssertionError(f"Could not save Undo fixture: {result}")
    print(f"PASS Built Weight Symmetry Undo fixture: {filepath}", flush=True)


def prepare_loaded_context(mesh_obj, armature_obj):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    source = mesh_obj.vertex_groups.get(LEFT_GROUP)
    if source is None:
        raise AssertionError(f"Loaded fixture has no {LEFT_GROUP} group")
    mesh_obj.vertex_groups.active_index = source.index
    result = bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
    if result != {"FINISHED"}:
        raise AssertionError(f"Could not enter Weight Paint Mode: {result}")


def setup_and_copy():
    try:
        bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
        bpy.context.preferences.edit.use_global_undo = True
        character_designer.register()

        mesh_obj = bpy.data.objects["WeightSymmetryMesh"]
        armature_obj = bpy.data.objects["WeightSymmetryRig"]
        prepare_loaded_context(mesh_obj, armature_obj)
        STATE["mesh_name"] = mesh_obj.name
        STATE["before"] = capture_groups(mesh_obj)

        window_manager = bpy.context.window_manager
        keymap = window_manager.keyconfigs.active.keymaps.get("3D View")
        if keymap is None:
            raise AssertionError("The active 3D View keymap is unavailable")
        keymap_item = keymap.keymap_items.new(
            "character_designer.copy_weight_to_opposite",
            "F8",
            "PRESS",
        )
        window_manager.keyconfigs.update()
        STATE.update(keymap=keymap, keymap_item=keymap_item)

        window, x, y = view3d_context()
        STATE.update(window=window, event_x=x, event_y=y)
        window.event_simulate(type="F8", value="PRESS", x=x, y=y)
        window.event_simulate(type="F8", value="RELEASE", x=x, y=y)
        bpy.app.timers.register(verify_copied, first_interval=0.5)
    except Exception as exc:
        return fail("setup/copy", exc)
    return None


def verify_copied():
    try:
        mesh_obj = bpy.data.objects[STATE["mesh_name"]]
        STATE["after"] = capture_groups(mesh_obj)
        if STATE["after"] == STATE["before"]:
            raise AssertionError("The hotkey-triggered operation made no change")
        assert_left_to_right_contract(mesh_obj)

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
        bpy.app.timers.register(verify_undo, first_interval=0.5)
    except Exception as exc:
        return fail("verify copied state", exc)
    return None


def verify_undo():
    try:
        mesh_obj = bpy.data.objects.get(STATE["mesh_name"])
        if mesh_obj is None:
            raise AssertionError("Undo removed the pre-existing fixture Mesh")
        if capture_groups(mesh_obj) != STATE["before"]:
            raise AssertionError(
                "One Ctrl+Z did not restore the exact pre-operation groups"
            )

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
        bpy.app.timers.register(verify_redo, first_interval=0.5)
    except Exception as exc:
        return fail("verify Undo", exc)
    return None


def verify_redo():
    try:
        mesh_obj = bpy.data.objects.get(STATE["mesh_name"])
        if mesh_obj is None:
            raise AssertionError("Redo did not restore the fixture Mesh")
        if capture_groups(mesh_obj) != STATE["after"]:
            raise AssertionError(
                "One Ctrl+Shift+Z did not restore the exact copied groups"
            )
        assert_left_to_right_contract(mesh_obj)
        if mesh_obj.vertex_groups.get(RIGHT_GROUP) is None:
            raise AssertionError("Redo did not restore the target Vertex Group")

        cleanup_fixture_on_success()
        print("PASS Weight Symmetry GUI single-step Undo/Redo", flush=True)
        unregister_addon()
        cleanup_keymap()
        bpy.ops.wm.quit_blender()
    except Exception as exc:
        return fail("verify Redo", exc)
    return None


if ARGS and ARGS[0] == "--build-fixture":
    if len(ARGS) != 2:
        raise SystemExit("Expected --build-fixture <absolute .blend path>")
    build_fixture(ARGS[1])
else:
    if ARGS and ARGS[0] != "--cleanup-fixture":
        raise SystemExit(f"Unexpected arguments: {ARGS}")
    bpy.app.timers.register(setup_and_copy, first_interval=0.5)
