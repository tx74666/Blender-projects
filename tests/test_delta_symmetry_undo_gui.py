"""Hidden-GUI integration check for Delta Symmetry Undo/Redo and Esc cancel."""

import sys
import traceback
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT / "addons", PROJECT_ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import character_designer
from character_designer import delta_symmetry
from test_delta_symmetry_blender import assert_vector_close, deselect_all, make_open_grid, prepare_bmesh, reset_scene


STATE = {}


def view3d_context():
    window = bpy.context.window_manager.windows[0]
    area = next(area for area in window.screen.areas if area.type == "VIEW_3D")
    region = next(region for region in area.regions if region.type == "WINDOW")
    x = area.x + region.x + max(1, region.width // 2)
    y = area.y + region.y + max(1, region.height // 2)
    return window, area, region, x, y


def fail(stage, exc):
    print(f"FAIL Delta Symmetry GUI Undo at {stage}: {exc}", flush=True)
    traceback.print_exc()
    try:
        if hasattr(bpy.types.WindowManager, "character_designer"):
            character_designer.unregister()
    finally:
        bpy.ops.wm.quit_blender()
    return None


def setup_and_move():
    try:
        bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
        character_designer.register()
        reset_scene()
        obj, bm = make_open_grid(rows=3, columns=5)
        if bpy.ops.character_designer.delta_build_pairs() != {"FINISHED"}:
            raise AssertionError("Pair build failed")
        negative, positive = delta_symmetry._CAPTURE["pairs"][0]
        deselect_all(bm)
        bm.verts[negative].select = True
        bm.select_history.add(bm.verts[negative])
        bpy.context.window_manager.character_designer_delta.auto_select_opposite = True
        if not bm.verts[positive].select:
            raise AssertionError("Auto Select Opposite did not add the modal transform partner")
        bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
        bm = bmesh.from_edit_mesh(obj.data)
        prepare_bmesh(bm)
        STATE.update(
            object_name=obj.name,
            negative=negative,
            positive=positive,
            negative_base=bm.verts[negative].co.copy(),
            positive_base=bm.verts[positive].co.copy(),
            delta=Vector((0.20, 0.10, 0.05)),
        )
        bpy.ops.ed.undo_push(message="Delta Symmetry GUI Baseline")
        bpy.context.window_manager.character_designer_delta.live_enabled = True
        window, area, region, x, y = view3d_context()
        STATE.update(window=window, event_x=x, event_y=y)
        with bpy.context.temp_override(window=window, area=area, region=region):
            result = bpy.ops.transform.translate(
                "INVOKE_DEFAULT",
                value=STATE["delta"],
                orient_type="GLOBAL",
            )
        if result != {"RUNNING_MODAL"}:
            raise AssertionError(f"Native modal translate did not start: {result}")
        bpy.app.timers.register(confirm_move, first_interval=0.15)
    except Exception as exc:
        return fail("move", exc)
    return None


def confirm_move():
    try:
        STATE["window"].event_simulate(
            type="RET",
            value="PRESS",
            x=STATE["event_x"],
            y=STATE["event_y"],
        )
        STATE["window"].event_simulate(
            type="RET",
            value="RELEASE",
            x=STATE["event_x"],
            y=STATE["event_y"],
        )
        bpy.app.timers.register(verify_move, first_interval=0.2)
    except Exception as exc:
        return fail("confirm", exc)
    return None


def verify_move():
    try:
        obj = bpy.data.objects[STATE["object_name"]]
        bpy.context.view_layer.update()
        delta_symmetry._delta_runtime_tick()
        bm = bmesh.from_edit_mesh(obj.data)
        prepare_bmesh(bm)
        assert_vector_close(
            bm.verts[STATE["negative"]].co,
            STATE["negative_base"] + STATE["delta"],
        )
        assert_vector_close(
            bm.verts[STATE["positive"]].co,
            STATE["positive_base"] + Vector((-0.20, 0.10, 0.05)),
        )
        bpy.app.timers.register(run_undo, first_interval=0.1)
    except Exception as exc:
        return fail("verify move", exc)
    return None


def run_undo():
    try:
        if bpy.ops.ed.undo() != {"FINISHED"}:
            raise AssertionError("Undo failed")
        obj = bpy.data.objects[STATE["object_name"]]
        bm = bmesh.from_edit_mesh(obj.data)
        prepare_bmesh(bm)
        assert_vector_close(bm.verts[STATE["negative"]].co, STATE["negative_base"])
        assert_vector_close(bm.verts[STATE["positive"]].co, STATE["positive_base"])
        bpy.app.timers.register(run_redo, first_interval=0.1)
    except Exception as exc:
        return fail("undo", exc)
    return None


def run_redo():
    try:
        if bpy.ops.ed.redo() != {"FINISHED"}:
            raise AssertionError("Redo failed")
        obj = bpy.data.objects[STATE["object_name"]]
        bm = bmesh.from_edit_mesh(obj.data)
        prepare_bmesh(bm)
        assert_vector_close(
            bm.verts[STATE["negative"]].co,
            STATE["negative_base"] + STATE["delta"],
        )
        assert_vector_close(
            bm.verts[STATE["positive"]].co,
            STATE["positive_base"] + Vector((-0.20, 0.10, 0.05)),
        )
        delta_symmetry._delta_runtime_tick()
        STATE["cancel_negative_base"] = bm.verts[STATE["negative"]].co.copy()
        STATE["cancel_positive_base"] = bm.verts[STATE["positive"]].co.copy()
        window, area, region, _x, _y = view3d_context()
        with bpy.context.temp_override(window=window, area=area, region=region):
            result = bpy.ops.transform.translate(
                "INVOKE_DEFAULT",
                value=Vector((-0.11, 0.07, 0.03)),
                orient_type="GLOBAL",
            )
        if result != {"RUNNING_MODAL"}:
            raise AssertionError(f"Cancel-check translate did not start: {result}")
        bpy.app.timers.register(cancel_move, first_interval=0.15)
    except Exception as exc:
        return fail("redo", exc)
    return None


def cancel_move():
    try:
        STATE["window"].event_simulate(
            type="ESC",
            value="PRESS",
            x=STATE["event_x"],
            y=STATE["event_y"],
        )
        STATE["window"].event_simulate(
            type="ESC",
            value="RELEASE",
            x=STATE["event_x"],
            y=STATE["event_y"],
        )
        bpy.app.timers.register(verify_cancel, first_interval=0.2)
    except Exception as exc:
        return fail("cancel", exc)
    return None


def verify_cancel():
    try:
        obj = bpy.data.objects[STATE["object_name"]]
        bm = bmesh.from_edit_mesh(obj.data)
        prepare_bmesh(bm)
        assert_vector_close(
            bm.verts[STATE["negative"]].co,
            STATE["cancel_negative_base"],
        )
        assert_vector_close(
            bm.verts[STATE["positive"]].co,
            STATE["cancel_positive_base"],
        )
        print("PASS Delta Symmetry GUI Undo/Redo/Esc", flush=True)
        character_designer.unregister()
        bpy.ops.wm.quit_blender()
    except Exception as exc:
        return fail("verify cancel", exc)
    return None


bpy.app.timers.register(setup_and_move, first_interval=0.5)
