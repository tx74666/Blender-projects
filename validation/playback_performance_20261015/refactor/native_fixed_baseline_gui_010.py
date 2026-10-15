"""Fixed private baseline GUI: standard load, retain factory UI, observe settle.

No frame seeking, geometry calculation, playback, benchmarking or save exists.
Root alone launches a new factory-startup GUI; this script leaves it alive.
"""
import argparse
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
INPUT = PROJECT / "validation/playback_performance_20261014/round4/input_saved_20261015.blend"
ARTIST = PROJECT / "X.blend"
STAGE = HERE / "staged_20261015_05"
INPUT_SHA, INPUT_BYTES = "40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721", 34691613
MANIFEST_SHA = "d62c3178ca6f0615fa4517440c157bba0ab2ced87cb64aa560ac1830197bac34"
SESSION = None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def pin(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def stage_pins(manifest):
    package = STAGE / "addons/character_designer"
    paths = {str(path.relative_to(package)).replace("\\", "/"): path for path in package.rglob("*.py")
             if "__pycache__" not in path.parts}
    require(set(paths) == set(manifest["files"]), "Stage05 Python inventory differs")
    result = {name: pin(path) for name, path in sorted(paths.items())}
    require(all((row["sha256"], row["bytes"]) == (manifest["files"][name]["sha256"], manifest["files"][name]["bytes"])
                for name, row in result.items()), "Stage05 source pin differs")
    return result


def ui_snapshot(bpy):
    return [{"window": window.as_pointer(), "screen": window.screen.name,
             "areas": [{"type": area.type, "size": [area.width, area.height]} for area in window.screen.areas]}
            for window in bpy.context.window_manager.windows]


def ui_structure(snapshot):
    return [(row["window"], row["screen"], [area["type"] for area in row["areas"]]) for row in snapshot]


class BaselineGUI:
    def __init__(self, report_path):
        import bpy
        require(not bpy.app.background and "--factory-startup" in sys.argv
                and not bpy.data.filepath and not bpy.data.is_dirty, "New blank clean factory-startup GUI required")
        require(INPUT.resolve() != ARTIST.resolve() and not os.path.samefile(INPUT, ARTIST), "Never open artist/hardlink")
        self.input_pin, self.artist_pin = pin(INPUT), pin(ARTIST)
        require((self.input_pin["sha256"], self.input_pin["bytes"]) == (INPUT_SHA, INPUT_BYTES), "Fixed baseline input differs")
        self.manifest_pin = pin(STAGE / "source_manifest.json")
        require(self.manifest_pin["sha256"] == MANIFEST_SHA, "Stage05 manifest differs")
        self.manifest = json.loads(Path(self.manifest_pin["path"]).read_text(encoding="utf-8-sig"))
        require(self.manifest.get("schema") == "x.frozen-playback-source-seal/1", "Unexpected source seal")
        self.sources, self.factory_ui = stage_pins(self.manifest), ui_snapshot(bpy)
        path = Path(report_path).resolve()
        require(path.is_relative_to(HERE) and path.suffix == ".json" and not path.exists(), "Unused project report required")
        self.stream = path.open("x", encoding="utf-8")
        self.report = {"schema": "x.fixed-private-baseline-gui/1", "completed": False, "pid": os.getpid(),
            "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "script": pin(__file__),
            "input_before": self.input_pin, "artist_before": self.artist_pin, "source_manifest": self.manifest_pin,
            "source_pins": self.sources, "factory_ui": self.factory_ui, "natural_lifecycle_changes": [],
            "load_ui": False, "no_scene_save": True, "no_manual_calculation_or_playback": True,
            "no_defer_or_handler_override": True, "preview_process_left_alive": True, "gui_fps_verified": False,
            "limits": "Startup/normal-settle observation only; Root still aligns view/material/resolution and prewarms before FPS009."}
        self.timer, self.started, self.ready_count, self.last = self.tick, time.monotonic(), 0, None

    def flush(self):
        self.stream.seek(0)
        self.stream.write(json.dumps(self.report, ensure_ascii=False, indent=2) + "\n")
        self.stream.truncate()
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def start(self):
        import bpy
        sys.path.insert(0, str(STAGE / "addons"))
        self.addon = importlib.import_module("character_designer")
        self.runtime = importlib.import_module("character_designer.forearm_twist")
        require(Path(self.addon.__file__).resolve().parent == STAGE / "addons/character_designer",
                "Different addon imported")
        self.addon.register()
        require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(INPUT), load_ui=False), "Fixed baseline open failed")
        require(Path(bpy.data.filepath).resolve() == INPUT.resolve(), "Loaded another file")
        self.report.update(loaded_file=bpy.data.filepath, blender=bpy.app.version_string,
                           addon_version=list(self.addon.bl_info["version"]), ui_after_open=ui_snapshot(bpy))
        self.flush()
        # Register after open so the ordinary file-load operation cannot drop
        # this observer before its first natural-settle observation.
        bpy.app.timers.register(self.timer, first_interval=.1)

    def finish(self, error=None):
        import bpy
        errors = [error] if error else []
        try:
            if bpy.app.timers.is_registered(self.timer):
                bpy.app.timers.unregister(self.timer)
            require(not bpy.app.timers.is_registered(self.timer), "Own observer timer retained")
            after_input, after_artist = pin(INPUT), pin(ARTIST)
            self.report.update(input_after=after_input, artist_after=after_artist, ui_at_finish=ui_snapshot(bpy),
                               dirty_at_finish=bool(bpy.data.is_dirty), own_timer_removed=True)
            require(after_input == self.input_pin and after_artist == self.artist_pin, "Protected disk changed")
            require(self.manifest_pin == pin(self.manifest_pin["path"]) and self.sources == stage_pins(self.manifest),
                    "Stage05 changed")
            require(self.report["script"] == pin(__file__), "Startup source changed")
            self.report["factory_layout_retained"] = ui_structure(self.factory_ui) == ui_structure(self.report["ui_at_finish"])
            require(self.report["factory_layout_retained"], "Factory UI structure changed")
        except BaseException:
            errors.append(traceback.format_exc())
        self.report.update(completed=not errors and self.ready_count >= 2, errors=errors,
                           addon_left_registered=bool(getattr(getattr(self, "runtime", None), "_RUNTIME_REGISTERED", False)))
        try:
            self.flush()
        finally:
            self.stream.close()

    def tick(self):
        import bpy
        try:
            require(time.monotonic() - self.started < 180, "Normal lifecycle did not settle within 180 seconds")
            require(Path(bpy.data.filepath).resolve() == INPUT.resolve(), "Private baseline file changed")
            runtime = self.runtime
            state = {name: bool(getattr(runtime, name)) for name in
                     ("_RUNTIME_REGISTERED", "_SCENE_STATE_ACTIVE", "_BUSY", "_INITIALIZE_PENDING", "_SCENE_CLEANUP_PENDING")}
            state["natural_lifecycle_timer"] = bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle)
            state["errors"] = dict(runtime._ERRORS)
            if state != self.last:
                self.report["natural_lifecycle_changes"].append(state)
                self.last = state
            require(not state["errors"], "Standard lifecycle emitted Forearm errors")
            ready = state["_RUNTIME_REGISTERED"] and state["_SCENE_STATE_ACTIVE"] and not any(state[name] for name in
                    ("_BUSY", "_INITIALIZE_PENDING", "_SCENE_CLEANUP_PENDING", "natural_lifecycle_timer"))
            self.ready_count = self.ready_count + 1 if ready else 0
            if self.ready_count >= 2:
                self.report["settled_scene"] = {"name": bpy.context.scene.name, "frame": bpy.context.scene.frame_current,
                    "subframe": bpy.context.scene.frame_subframe, "sync_mode": bpy.context.scene.sync_mode,
                    "frame_start": bpy.context.scene.frame_start, "frame_end": bpy.context.scene.frame_end}
                self.finish()
                return None
            return .1
        except BaseException:
            self.finish(traceback.format_exc())
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    try:
        SESSION = BaselineGUI(args.report)
        SESSION.start()
    except BaseException:
        if SESSION is not None:
            SESSION.finish(traceback.format_exc())
        raise
