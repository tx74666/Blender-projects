"""Source-only deferred final artist save after the accepted .41 closeout.

The pinned installer calls begin(). The original Hair command is observed as
unexecuted Console input, never compiled/evaluated/executed. UI transitions
precede the full protected witness. No channels, mesh flags, WM values, frame,
solver output or scene content are repaired. A failed post-save proof retains
its receipt and recovery copies; it does not perform an automatic rollback.
"""
import ast
from array import array
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import types
import uuid

ROUND = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4")
ARTIST = Path(r"D:\Blender\Projects\Character\X\X.blend")
CAPTURE_SOURCE = ROUND / "protected_refresh_07741.py"
CAPTURE_SOURCE_SHA256 = "0ce167ce3448f6e48140601dda54c4704589fa574bc65ddaaa1e83a0520a460d"
SOURCE_NAME = "_x_final_save_07741_20261015_source"
HELPER_NAME = "_x_final_save_07741_20261015"
CAPTURE_NAME = HELPER_NAME + "_capture"
EXPECTED_PID = 24416
PENDING_HAIR_TEXT = "hair_install_result = hair_install_scope['run'](previous_editor={'type': 'VIEW_3D', 'ui_type': 'VIEW_3D'},approved_official_install=True)"
EXPECTED_UI = {"type": "VIEW_3D", "shading": "MATERIAL", "sidebar": True}
WAIT_INPUT_SECONDS = 90.0
WAIT_SAVE_POST_SECONDS = 30.0
CAPTURE_FUNCTIONS = frozenset(("require", "utc", "pin", "identity", "exact", "digest", "rna", "pg",
                               "memory_guard", "load_oracle", "idle", "complete_artist_owners",
                               "context_record", "handler_witness", "animation_data", "capture", "differences"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def pin(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}


class FinalSave:
    def __init__(self, window, screen, area, scene, pending_console_text):
        require(pending_console_text == PENDING_HAIR_TEXT, "Use the exact previously observed unexecuted Hair text")
        self.window, self.screen, self.area, self.scene = window, screen, area, scene
        self.pending_console_text = pending_console_text
        self.console_space = None
        self.capture_module = self.oracle = self.helper = None
        self.source_module = sys.modules.get(SOURCE_NAME)
        require(self.source_module is not None and vars(self.source_module) is globals(), "Install through the owned pinned source module")
        self.poll_callback, self.cleanup_callback = self.poll, self.cleanup
        self.closed = False
        self.deadline = time.monotonic() + WAIT_INPUT_SECONDS
        self.output = ROUND / ("final_save_07741_" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:12])
        self.output.mkdir()
        self.report = {"schema": "x.protected-native-final-save-07741/1", "created_utc": utc(),
                       "pid": os.getpid(), "completed": False, "phase": "waiting_unexecuted_Hair_input",
                       "artist_saved": False, "source": pin(__file__), "errors": [],
                       "pending_console_text_sha256": hashlib.sha256(pending_console_text.encode("utf-8")).hexdigest(),
                       "no_console_command_execution": True, "no_frame_set": True,
                       "no_manual_runtime_update": True, "no_channel_or_mesh_repair": True,
                       "no_refresh_or_deployment": True, "automatic_scene_rollback": False,
                       "limits": ["Protected in-memory content witness across native save; no independent saved-file reopen/readback in this script.",
                                  "No Undo-stack preservation proof.",
                                  "Healthy managed outputs must match their last published runtime cache; this does not independently recompute the complete deformation mathematics."]}
        self.write()

    def write(self):
        target = self.output / "final_save_receipt.json"
        temp = target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(self.report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temp.replace(target)

    def admit(self, area_type):
        import bpy
        require(os.getpid() == EXPECTED_PID and not bpy.app.background, "Wrong foreground artist process")
        require(Path(bpy.data.filepath).resolve() == ARTIST.resolve(), "Current artist filepath changed")
        require(self.window.screen == self.screen and self.window.scene == self.scene
                and any(area == self.area for area in self.screen.areas) and self.area.type == area_type,
                "Observed window/screen/scene/area changed")
        require(self.scene.name == "Scene" and self.scene.frame_current == 21 and self.scene.frame_subframe == 0.0,
                "Expected paused artist frame 21/subframe zero")
        require(not any(window.screen and window.screen.is_animation_playing
                        for window in bpy.context.window_manager.windows), "Pause all artist process playback")
        require(bpy.context.mode == "OBJECT" and bpy.context.view_layer.objects.active is self.scene.objects.get("Cosha")
                and not bpy.context.selected_objects, "Expected Object Mode, active Cosha and empty selection")
        cd = sys.modules.get("character_designer")
        require(cd is not None and tuple(cd.bl_info["version"]) == (0, 77, 41), "Loaded runtime must be .41")
        require(Path(cd.__file__).resolve().parent == Path(r"C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer").resolve(),
                "Unexpected current installed runtime root")
        require(not cd.ADDON_REFRESH_PENDING and not cd.ADDON_REFRESH_LAST_ERROR, "Official refresh is pending or failed")
        require(not any(name.startswith(("_x_playback", "_x_protected_refresh")) for name in sys.modules),
                "Profiler or protected-refresh helper remains; release its own ownership first")
        cd._validate_registration_integrity()
        return cd

    def pending_input(self):
        space = self.area.spaces.active
        require(space.bl_rna.identifier == "SpaceConsole"
                and space.bl_rna.properties.get("history") is not None, "Native Console history API unavailable; no automatic save")
        history = space.history
        require(len(history) > 0, "Native Console input history is empty")
        line = history[-1]
        require(line.bl_rna.properties.get("body") is not None and isinstance(line.body, str),
                "Native ConsoleLine body API unavailable; no automatic save")
        line_type = getattr(line, "type", None)
        type_property = line.bl_rna.properties.get("type")
        if type_property is not None and any(item.identifier == "INPUT" for item in getattr(type_property, "enum_items", ())):
            require(line_type == "INPUT", "Observed Console history tail is not an INPUT line")
        if line.body != self.pending_console_text:
            return False
        self.console_space = space
        self.report["pending_console_input"] = {"native_history_api_verified": True,
                                               "exact_body_match": True, "line_type": line_type,
                                               "unexecuted_input_path": "SpaceConsole.history[-1].body",
                                               "command_execution_called": False}
        return True

    def load_capture(self):
        raw = CAPTURE_SOURCE.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == CAPTURE_SOURCE_SHA256, "Pinned protection source changed")
        tree = ast.parse(raw.decode("utf-8-sig"), filename=str(CAPTURE_SOURCE))
        definitions = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign))
                       or isinstance(node, ast.FunctionDef) and node.name in CAPTURE_FUNCTIONS]
        require({node.name for node in definitions if isinstance(node, ast.FunctionDef)} == CAPTURE_FUNCTIONS,
                "Pinned protection definition inventory changed")
        require(CAPTURE_NAME not in sys.modules and CAPTURE_NAME + "_oracle" not in sys.modules,
                "Save capture/oracle ownership already exists")
        module = types.ModuleType(CAPTURE_NAME)
        module.__file__ = str(CAPTURE_SOURCE)
        sys.modules[CAPTURE_NAME] = module
        self.capture_module = module
        exec(compile(ast.Module(body=definitions, type_ignores=[]), str(CAPTURE_SOURCE), "exec"), module.__dict__)
        # Change only this temporary definition module's helper namespace.
        module.HELPER_NAME = CAPTURE_NAME
        self.oracle = module.load_oracle()
        self.report["protection_sources"] = {"capture": pin(CAPTURE_SOURCE), "oracle": module.pin(module.ORACLE, {"sha256": module.ORACLE_SHA})}

    def healthy_outputs(self):
        source = self.capture_module
        summary = source.complete_artist_owners(self.scene)
        ft = sys.modules["character_designer.forearm_twist"]
        obj = self.scene.objects["Cosha"]
        require(obj.as_pointer() in ft._CACHE, "Current published Forearm input cache is missing")
        cached = ft._OUTPUT_CACHE.get(obj.as_pointer())
        require(cached is not None, "Current published Forearm output cache is missing")
        snapshots = []
        for side, record in ft._records(obj).items():
            key = ft._managed_key(obj, side, record, required=True, repair_name=False)
            coords = array("f", [0.0]) * (3 * len(key.data))
            key.data.foreach_get("co", coords)
            snapshots.append(coords.tobytes())
        require(snapshots == cached, "Managed coordinate bytes differ from the last published runtime output; no repair performed")
        summary["published_output_cache_equal"] = True
        return summary

    def poll(self):
        import bpy
        if self.closed:
            return None
        try:
            require(time.monotonic() < self.deadline, "Deferred final-save phase timed out")
            with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area):
                if self.report["phase"] == "waiting_unexecuted_Hair_input":
                    self.admit("CONSOLE")
                    if not self.pending_input():
                        return 0.25
                    self.area.type = EXPECTED_UI["type"]
                    self.area.spaces.active.shading.type = EXPECTED_UI["shading"]
                    self.area.spaces.active.show_region_ui = EXPECTED_UI["sidebar"]
                    self.area.tag_redraw()
                    self.report["ui_restored_before_capture"] = dict(EXPECTED_UI)
                    self.report["phase"] = "capture_and_native_save"
                    self.deadline = time.monotonic() + WAIT_SAVE_POST_SECONDS
                    self.write()
                    return 0.1
                cd = self.admit("VIEW_3D")
                require(self.area.spaces.active.shading.type == "MATERIAL" and self.area.spaces.active.show_region_ui,
                        "Expected Material viewport with sidebar before/after save")
                require(self.console_space is not None and self.console_space.history[-1].body == self.pending_console_text,
                        "Unexecuted original Hair line was not retained in its Console space")
                if self.report["phase"] == "capture_and_native_save":
                    self.load_capture()
                    source = self.capture_module
                    source.idle(cd)
                    self.report["healthy_owners_before"] = self.healthy_outputs()
                    self.report["handlers_before"] = source.handler_witness()
                    self.report["artist_before_save"] = pin(ARTIST)
                    self.before, _wm = source.capture(cd, self.oracle)
                    self.report["before"] = self.before
                    source.idle(cd)
                    require(self.healthy_outputs() == self.report["healthy_owners_before"], "Owner/output admission changed during capture")
                    self.report["phase"] = "native_save_started"
                    self.write()
                    require(bpy.ops.wm.save_mainfile.poll(), "Native save_mainfile poll failed")
                    returned = bpy.ops.wm.save_mainfile("EXEC_DEFAULT")
                    self.report["native_save_result"] = sorted(returned)
                    self.report["dirty_immediate_after_save"] = bool(bpy.data.is_dirty)
                    self.report["artist_saved"] = returned == {"FINISHED"} and ARTIST.is_file()
                    require(returned == {"FINISHED"} and ARTIST.is_file(), "Native mainfile save did not finish")
                    require(Path(bpy.data.filepath).resolve() == ARTIST.resolve(), "Native save changed artist filepath")
                    self.report["final_file_immediate"] = pin(ARTIST)
                    self.report["phase"] = "waiting_native_save_post"
                    self.deadline = time.monotonic() + WAIT_SAVE_POST_SECONDS
                    self.write()
                    return 0.1
                require(self.report["phase"] == "waiting_native_save_post", "Unknown save phase")
                if bpy.data.is_dirty:
                    return 0.1
                source = self.capture_module
                source.idle(cd)
                self.report["healthy_owners_after"] = self.healthy_outputs()
                self.report["handlers_after"] = source.handler_witness()
                after, _wm = source.capture(cd, self.oracle)
                self.report["after"] = after
                changed = [name for name in source.differences(self.before, after) if name != "context"]
                before_context = {key: value for key, value in self.before["context"].items() if key != "filepath"}
                after_context = {key: value for key, value in after["context"].items() if key != "filepath"}
                self.report["changed_asset_components"] = changed
                self.report["context_equal_except_filepath"] = source.exact(before_context) == source.exact(after_context)
                require(not changed and self.report["context_equal_except_filepath"], "Protected content/context changed across save")
                require(self.report["handlers_before"] == self.report["handlers_after"], "Callback objects/order changed across save")
                require(self.report["healthy_owners_before"] == self.report["healthy_owners_after"], "Complete owner/output witness changed across save")
                require(not bpy.data.is_dirty and not after["dirty"] and ARTIST.is_file(), "Artist must be clean after event-loop post-save proof")
                self.report["final_file"] = pin(ARTIST)
                self.report["final_dirty"] = False
                self.report["loaded_version"] = [0, 77, 41]
                self.report["pending_Hair_text_retained_unexecuted"] = True
                self.finish()
                return None
        except BaseException:
            self.finish(traceback.format_exc())
            return None

    def finish(self, failure=None):
        import bpy
        self.closed = True
        self.report.update(completed=failure is None, phase="completed" if failure is None else "failed",
                           finished_utc=utc(), helper_cleanup="Awaiting the next idle event-loop turn")
        if failure:
            self.report["errors"].append(failure)
            self.report["final_dirty_observed"] = bool(bpy.data.is_dirty)
            self.report["final_filepath_observed"] = bpy.data.filepath
            if ARTIST.is_file():
                self.report["final_file_observed"] = pin(ARTIST)
        self.write()
        bpy.app.timers.register(self.cleanup_callback, first_interval=0.01)

    def cleanup(self):
        import bpy
        try:
            require(self.closed and not bpy.app.timers.is_registered(self.poll_callback), "Final-save timer is still registered; keep owned helpers")
            owned = ((CAPTURE_NAME + "_oracle", self.oracle), (CAPTURE_NAME, self.capture_module),
                     (HELPER_NAME, self.helper), (SOURCE_NAME, self.source_module))
            for name, module in owned:
                require(module is None or sys.modules.get(name) is module, "Helper ownership changed; do not delete foreign module: " + name)
            removed = []
            for name, module in owned:
                if module is not None and sys.modules.get(name) is module:
                    del sys.modules[name]
                    removed.append(name)
            self.report["helper_cleanup"] = {"poll_timer_gone": True, "owned_modules_removed": removed,
                                             "cleanup_callback_returns_none": True, "finished_utc": utc()}
        except BaseException:
            self.report["completed"] = False
            self.report["errors"].append(traceback.format_exc())
            self.report["helper_cleanup"] = "Failed ownership/timer guard; foreign or active resources retained"
        self.write()
        print(json.dumps({"completed": self.report["completed"], "artist_saved": self.report["artist_saved"],
                          "receipt": str(self.output / "final_save_receipt.json")}, ensure_ascii=False))
        return None


def begin(window, screen, area, scene, pending_console_text=PENDING_HAIR_TEXT):
    """Call only from the pinned installer after Console's operator returns."""
    import bpy
    require(HELPER_NAME not in sys.modules, "An owned final-save worker already exists")
    controller = FinalSave(window, screen, area, scene, pending_console_text)
    helper = types.ModuleType(HELPER_NAME)
    helper.controller = controller
    controller.helper = helper
    sys.modules[HELPER_NAME] = helper
    bpy.app.timers.register(controller.poll_callback, first_interval=0.25)
    return controller
