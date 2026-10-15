"""Observe ordinary playback in one explicitly owned private GUI process.

Import/install does not open/save a blend, register an addon or replace a
runtime/helper/handler. Only owned frame markers, draw callback and timer are
installed. Full state proofs and disk hashing stay outside the 16-second window.
"""
import collections
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
WARM_SECONDS, MEASURE_SECONDS = 2.0, 16.0
FIXED_BASELINE = ("40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721", 34691613)
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


def same_pin(left, right):
    return (left["sha256"], left["bytes"]) == (right["sha256"], right["bytes"])


def load_pinned_json(path, expected_sha):
    observed = pin(path)
    require(observed["sha256"] == expected_sha, "Evidence/source JSON SHA changed")
    return json.loads(Path(observed["path"]).read_text(encoding="utf-8-sig")), observed


def validate_config(config, current_pid):
    required = {"expected_pid", "private_blend", "private_sha256", "artist", "addons",
                "source_manifest", "source_manifest_sha256", "mode", "kind", "report"}
    optional = {"allow_fixed_baseline", "gui008_report", "gui008_report_sha256"}
    require(isinstance(config, dict) and required <= set(config) and set(config) <= required | optional,
            "Unexpected/incomplete FPS probe configuration")
    require(type(config["expected_pid"]) is int and config["expected_pid"] > 0
            and config["expected_pid"] == current_pid, "Root-supplied owned PID differs")
    require(config["mode"] in {"MATERIAL", "SOLID"}, "Explicit MATERIAL or SOLID mode required")
    require(config["kind"] in {"baked", "baseline"}, "Explicit baked or baseline route required")
    for key in ("private_blend", "artist", "addons", "source_manifest", "report"):
        require(isinstance(config[key], str) and bool(config[key]), "Configuration paths must be nonempty strings")
    for key in ("private_sha256", "source_manifest_sha256"):
        require(isinstance(config[key], str) and len(config[key]) == 64
                and all(char in "0123456789abcdef" for char in config[key]), "Invalid expected SHA256")
    if config["kind"] == "baseline":
        require(config.get("allow_fixed_baseline") is True and config["private_sha256"] == FIXED_BASELINE[0],
                "Baseline requires explicit permission and the known 40644 input")
    else:
        require(config.get("allow_fixed_baseline", False) is False
                and config.get("gui008_report") and config.get("gui008_report_sha256"),
                "Baked route requires a completed pinned GUI008 report")
        require(isinstance(config["gui008_report"], str) and isinstance(config["gui008_report_sha256"], str)
                and len(config["gui008_report_sha256"]) == 64, "Invalid GUI008 receipt configuration")
    return dict(config)


def distribution(values):
    values = sorted(values)
    if not values:
        return {"count": 0, "mean": None, "median": None, "p95": None, "max": None}
    return {"count": len(values), "mean": statistics.mean(values), "median": statistics.median(values),
            "p95": values[max(0, math.ceil(len(values) * .95) - 1)], "max": values[-1]}


def cadence(events, seconds=MEASURE_SECONDS):
    hist = collections.Counter(int(row[1]) for row in events)
    intervals = [(right[0] - left[0]) / 1e6 for left, right in zip(events, events[1:])]
    span = (events[-1][0] - events[0][0]) / 1e9 if len(events) > 1 else 0.0
    return {"count": len(events), "count_per_fixed_window_hz": len(events) / seconds,
            "interevent_hz": (len(events) - 1) / span if span > 0 else None,
            "interval_ms": distribution(intervals), "frame_histogram": dict(sorted(hist.items())),
            "unique_integer_frames": sorted(hist)}


def changed_draw_events(events):
    result = []
    for event in events:
        if not result or event[1:] != result[-1][1:]:
            result.append(event)
    return result


def handler_snapshot(bpy):
    return {name: [id(callback) for callback in value] for name in dir(bpy.app.handlers)
            if isinstance((value := getattr(bpy.app.handlers, name)), list)}


class ErrorObserver:
    """Tee Python stderr; never wrap native callbacks or runtime functions."""
    def __init__(self, original):
        self.original, self.text, self.truncated = original, "", False
    def write(self, value):
        result = self.original.write(value)
        remaining = max(0, 32768 - len(self.text))
        self.text += value[:remaining]
        self.truncated |= len(value) > remaining
        return result
    def flush(self):
        self.original.flush()
    def __getattr__(self, name):
        return getattr(self.original, name)
    def has_error(self):
        return "Traceback (most recent call last)" in self.text or "Error in bpy.app.handlers" in self.text


class Probe:
    def __init__(self, config):
        import bpy
        import importlib
        self.config = validate_config(config, os.getpid())
        require(not bpy.app.background and "--factory-startup" in sys.argv, "New owned factory-startup GUI process required")
        self.private = Path(config["private_blend"]).resolve(strict=True)
        self.artist = Path(config["artist"]).resolve(strict=True)
        canonical_artist = HERE.parents[2] / "X.blend"
        require(self.artist == canonical_artist.resolve(), "Expected canonical artist disk boundary")
        require(self.private != self.artist and not os.path.samefile(self.private, self.artist), "Never profile artist or its hard link")
        require(Path(bpy.data.filepath).resolve() == self.private, "Owned GUI has a different loaded file")
        self.private_pin, self.artist_pin = pin(self.private), pin(self.artist)
        require(self.private_pin["sha256"] == config["private_sha256"], "Private blend SHA differs")
        if config["kind"] == "baseline":
            require((self.private_pin["sha256"], self.private_pin["bytes"]) == FIXED_BASELINE, "Unknown baseline input")
        self.package = Path(config["addons"]).resolve() / "character_designer"
        self.manifest, self.manifest_pin = load_pinned_json(config["source_manifest"], config["source_manifest_sha256"])
        require(self.manifest.get("schema") == "x.frozen-playback-source-seal/1", "Unexpected staged package seal")
        require(str(HERE) in sys.path or HERE == Path.cwd(), "Load the probe from its own source directory")
        self.witness = importlib.import_module("native_validation_support_v5")
        self.portable = importlib.import_module("native_artifact_action_witness_008")
        require(Path(self.witness.__file__).resolve() == HERE / "native_validation_support_v5.py"
                and Path(self.portable.__file__).resolve() == HERE / "native_artifact_action_witness_008.py", "Different proof helper imported")
        self.sources = self.witness.verify_package_manifest(self.package, self.manifest)
        self.dependencies = self.witness.witness_dependency_pins()
        self.dependencies["portable"] = pin(self.portable.__file__)
        self.dependencies["oracle"] = pin(self.witness.ORACLE_PATH)
        self.addon = sys.modules.get("character_designer")
        self.runtime = sys.modules.get("character_designer.forearm_twist")
        require(self.addon is not None and self.runtime is not None
                and Path(self.addon.__file__).resolve().parent == self.package
                and Path(self.runtime.__file__).resolve().parent == self.package,
                "Expected already loaded standard staged addon/runtime")
        self.window, self.screen, self.scene, self.area = bpy.context.window, bpy.context.screen, bpy.context.scene, bpy.context.area
        require(self.window and self.screen and self.scene and self.area and self.area.type in {"CONSOLE", "VIEW_3D"},
                "Install only in owned Console or VIEW_3D context")
        require(not any(window.screen.is_animation_playing for window in bpy.context.window_manager.windows if window.screen),
                "Playback must already be stopped; no foreign screen is stopped by the probe")
        self.initial_area_type = self.area.type
        self.region = self.before_context = self.before_state = self.draw_handle = self.tee = None
        self.timer = self.tick
        self.pre_callback, self.post_callback, self.draw_callback = self.on_pre, self.on_post, self.on_draw
        self.phase, self.collecting, self.closed = "PREPARE", False, False
        self.start_ns = self.end_ns = self.play_start_ns = None
        self.pre_pending, self.post_events, self.draw_events, self.eval_events, self.callback_errors = None, [], [], [], []
        self.handlers_before = handler_snapshot(bpy)
        self.owned_handlers = []
        self.gui_pin = self.artifact_receipt_pin = None
        self.required_meshes = ("Cosha", "Shoes")
        if config["kind"] == "baked":
            gui, self.gui_pin = load_pinned_json(config["gui008_report"], config["gui008_report_sha256"])
            require(gui.get("schema") == "x.independent-artifact-gui-reopen/1" and gui.get("completed") is True
                    and gui.get("pid") == os.getpid() and not gui.get("error") and gui.get("cleanup_errors") == [],
                    "GUI008 did not complete in this owned PID")
            require(all(gui.get(name) is True for name in ("normal_addon_lifecycle_reopen_verified", "own_verification_timer_removed",
                    "protected_disks_sources_callbacks_unchanged", "addon_left_registered")), "GUI008 lifecycle/cleanup gate failed")
            require(same_pin(gui["artifact"], self.private_pin) and Path(gui["artifact"]["path"]).resolve() == self.private,
                    "GUI008 artifact differs from loaded private file")
            require(same_pin(gui["portable_helper"], self.dependencies["portable"]), "GUI008 portable proof helper differs")
            require(Path(gui["script"]["path"]).resolve() == HERE / "native_artifact_reopen_gui_008.py"
                    and same_pin(gui["script"], pin(gui["script"]["path"])), "GUI008 verifier source differs")
            self.dependencies["gui008_entry"] = pin(gui["script"]["path"])
            require({name: [row["identity"] for row in values] for name, values in gui["callbacks_after_natural_settle"].items()}
                    == self.handlers_before, "Standard handler identities changed since GUI008")
            require({row["frame"] for row in gui["frames"]} == set(range(1, 31)) and len(gui["frames"]) == 30
                    and all(row["all_full_coordinates_normals_exact"] and row["portable_animation_exact"] for row in gui["frames"]),
                    "GUI008 full frame proof is incomplete")
            receipt, self.artifact_receipt_pin = load_pinned_json(gui["artifact_receipt"]["path"], gui["artifact_receipt"]["sha256"])
            require(receipt.get("completed") is True and same_pin(receipt["artifact"], self.private_pin)
                    and same_pin(receipt["source_manifest"], self.manifest_pin), "Artifact/source evidence differs")
            require(self.scene.name == receipt["reopen_contract"]["scene_name"]
                    and set(self.scene.objects.keys()) == set(receipt["reopen_contract"]["logical_objects"].values()),
                    "Loaded candidate Scene/object scope differs")
            self.required_meshes = tuple(receipt["reopen_contract"]["logical_objects"][name] for name in ("Cosha", "Shoes"))
            require(not any(obj.type == "MESH" and self.runtime.RECORD_KEY in obj for obj in self.scene.objects),
                    "Baked preview unexpectedly enrolled the authoring solver")
        self.assert_runtime()
        report_path = Path(config["report"]).resolve()
        protected = {self.private, self.artist, Path(__file__).resolve(), Path(config["source_manifest"]).resolve()}
        protected.update(Path(value["path"]).resolve() for value in (self.gui_pin, self.artifact_receipt_pin) if value)
        require(report_path.is_relative_to(HERE) and report_path.suffix == ".json" and report_path not in protected
                and not report_path.exists(), "Exclusive unused project report required")
        self.stream = report_path.open("x", encoding="utf-8")
        self.report = {"schema": "x.owned-private-gui-normal-playback/1", "completed": False, "pid": os.getpid(),
            "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "config": dict(config),
            "script": pin(__file__), "private_before": self.private_pin, "artist_before": self.artist_pin,
            "source_manifest": self.manifest_pin, "dependencies": self.dependencies, "gui008": self.gui_pin,
            "artifact_receipt": self.artifact_receipt_pin, "blender": bpy.app.version_string,
            "installation_area_type": self.initial_area_type, "model": "gpt-6.1-sol", "reasoning_effort": "ultra",
            "model_source": "Root task local-index metadata; inherited task settings.",
            "no_open_save_deploy": True, "normal_callbacks_preserved": True, "no_manual_solver_or_helper_calls": True,
            "no_runtime_defer_or_override": True, "performance_acceptance": False,
            "limits": ["Frame-change and target POST_PIXEL callback cadence are observed separately.",
                       "Changed draw tokens are consecutive scene-frame changes, not GPU time or compositor presentation.",
                       "Appended own pre-to-post span excludes earlier standard frame-pre callbacks; it is not total frame CPU time.",
                       "No reciprocal-duration FPS inference. A valid sample does not automatically accept 30 FPS.",
                       "Material compilation/cache completion is unmeasured; two warmup seconds do not prove compilation finished. Root must prewarm matching input/camera/resolution/shading before comparisons.",
                       "Only the saved integer 1-30 clip/context is sampled; physics/subframes/other clips are unverified."]}
        self.flush()

    def assert_runtime(self):
        import bpy
        r = self.runtime
        require(r._RUNTIME_REGISTERED and r._SCENE_STATE_ACTIVE and not r._BUSY
                and not r._INITIALIZE_PENDING and not r._SCENE_CLEANUP_PENDING and not r._ERRORS
                and not bpy.app.timers.is_registered(r._complete_runtime_lifecycle), "Standard runtime is not naturally settled/error-free")

    def assert_owned(self):
        import bpy
        require(os.getpid() == self.config["expected_pid"] and Path(bpy.data.filepath).resolve() == self.private
                and self.window.screen == self.screen and self.window.scene == self.scene,
                "Owned PID/file/Window/Scene changed")
        require(any(area == self.area for area in self.screen.areas) and self.area.type == "VIEW_3D",
                "Owned viewport changed; do not overwrite another area")

    def context_state(self):
        import bpy
        with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
            return self._context_state()

    def _context_state(self):
        import bpy
        space, scene = self.area.spaces.active, self.scene
        view = space.region_3d
        active = self.window.view_layer.objects.active
        return {"window": self.window.as_pointer(), "screen": self.screen.as_pointer(), "scene": scene.as_pointer(),
            "view_layer": self.window.view_layer.as_pointer(), "area": self.area.as_pointer(),
            "area_type": self.area.type, "area_size": [self.area.width, self.area.height],
            "region_size": [self.region.width, self.region.height], "mode": bpy.context.mode,
            "active": active.as_pointer() if active else None,
            "selected": sorted(obj.as_pointer() for obj in self.window.view_layer.objects if obj.select_get()),
            "frame": scene.frame_current, "subframe_hex": float(scene.frame_subframe).hex(),
            "playing": bool(self.screen.is_animation_playing), "sync_mode": scene.sync_mode,
            "clip": {name: getattr(scene, name) for name in ("frame_start", "frame_end", "use_preview_range", "frame_preview_start", "frame_preview_end")},
            "fps": scene.render.fps, "fps_base_hex": float(scene.render.fps_base).hex(),
            "shading": self.portable.state(space.shading), "overlays": self.portable.state(space.overlay),
            "sidebar": space.show_region_ui, "toolbar": space.show_region_toolbar,
            "clip_start_hex": float(space.clip_start).hex(), "clip_end_hex": float(space.clip_end).hex(),
            "view_location": self.witness.raw_native(view.view_location), "view_rotation": self.witness.raw_native(view.view_rotation),
            "view_distance_hex": float(view.view_distance).hex(), "perspective": view.view_perspective,
            "lens_hex": float(space.lens).hex(), "local_view": bool(space.local_view),
            "render_engine": scene.render.engine}

    def visibility_state(self):
        result, layer = {}, self.window.view_layer
        for obj in self.scene.objects:
            if obj.type != "MESH":
                continue
            member = layer.objects.get(obj.name) == obj
            result[obj.name_full] = {"in_view_layer": member,
                "visible": bool(obj.visible_get(view_layer=layer)) if member else False,
                "hidden": bool(obj.hide_get(view_layer=layer)) if member else None,
                "hide_viewport": bool(obj.hide_viewport), "hide_render": bool(obj.hide_render),
                "display_type": obj.display_type}
        return result

    def full_state(self):
        import bpy
        require(not self.collecting, "Full proof is forbidden in the hot window")
        with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
            self.window.view_layer.update()
            parts, meshes, rigs = {}, [], []
            for obj in sorted(self.scene.objects, key=lambda value: value.name_full):
                if obj.type == "MESH":
                    parts["mesh:" + obj.name_full] = self.witness.geometry_witness(obj, {})
                    parts["keys:" + obj.name_full] = self.witness.shape_keys_witness(obj, {})
                    meshes.append(obj.name_full)
                elif obj.type == "ARMATURE":
                    parts["rig:" + obj.name_full] = self.witness.rig_witness(obj)
                    rigs.append(obj.name_full)
            require(meshes and rigs, "Full mesh and rig scope required")
            parts["source_properties"] = self.witness.source_property_witness(self.scene)
            parts["stored_actions"] = self.portable.capture(self.scene, tuple(bpy.data.actions))
            parts["mesh_visibility"] = self.visibility_state()
            return {"sha256": self.witness.object_hash(parts), "components": {key: self.witness.object_hash(value) for key, value in parts.items()},
                    "mesh_names": meshes, "rig_names": rigs, "context": self.context_state()}

    def in_hot(self, now):
        return self.collecting and self.start_ns <= now < self.end_ns

    def callback_failed(self):
        if len(self.callback_errors) < 4:
            self.callback_errors.append(traceback.format_exc())

    def on_pre(self, scene, *unused):
        if scene != self.scene:
            return
        try:
            now = time.perf_counter_ns()
            self.pre_pending = (now, scene.frame_current, float(scene.frame_subframe)) if self.in_hot(now) else None
        except BaseException:
            self.callback_failed()

    def on_post(self, scene, *unused):
        if scene != self.scene:
            return
        try:
            now = time.perf_counter_ns()
            if self.in_hot(now):
                require(len(self.post_events) < 8192, "Frame-event cap exceeded")
                token = (scene.frame_current, float(scene.frame_subframe))
                self.post_events.append((now, *token))
                if self.pre_pending and self.pre_pending[1:] == token:
                    self.eval_events.append((self.pre_pending[0], now, *token))
                elif self.pre_pending:
                    raise RuntimeError("Own appended pre/post frame tokens differ")
                self.pre_pending = None
        except BaseException:
            self.callback_failed()

    def on_draw(self):
        import bpy
        try:
            if bpy.context.window != self.window or bpy.context.area != self.area or bpy.context.region != self.region:
                return
            now = time.perf_counter_ns()
            if self.in_hot(now):
                require(len(self.draw_events) < 8192, "Draw-event cap exceeded")
                self.draw_events.append((now, self.scene.frame_current, float(self.scene.frame_subframe)))
        except BaseException:
            self.callback_failed()

    def flush(self):
        self.stream.seek(0)
        self.stream.write(json.dumps(self.report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        self.stream.truncate()
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def tick(self):
        import bpy
        try:
            if self.phase == "PREPARE":
                require(self.window.screen == self.screen and self.window.scene == self.scene, "Install context changed")
                if self.area.type == "CONSOLE":
                    self.area.type = "VIEW_3D"
                    return .1
                self.region = next((region for region in self.area.regions if region.type == "WINDOW"), None)
                require(self.region is not None, "Target VIEW_3D WINDOW region missing")
                self.assert_owned()
                self.assert_runtime()
                self.before_context = self.context_state()
                self.before_shading_type = self.area.spaces.active.shading.type
                self.before_frame = (self.scene.frame_current, float(self.scene.frame_subframe))
                require(not self.area.spaces.active.local_view and not self.area.spaces.active.region_quadviews,
                        "Single full VIEW_3D required; do not alter local/quad view")
                visibility = self.visibility_state()
                require(all(name in visibility and visibility[name]["visible"] and not visibility[name]["hide_viewport"]
                            for name in self.required_meshes), "Full Cosha and Shoes must remain visible")
                require(self.scene.frame_start == 1 and self.scene.frame_end == 30
                        and (not self.scene.use_preview_range or (self.scene.frame_preview_start, self.scene.frame_preview_end) == (1, 30)),
                        "Do not modify clip: this probe requires the existing 1-30 playback range")
                self.before_state = self.full_state()
                self.area.spaces.active.shading.type = self.config["mode"]
                self.area.tag_redraw()
                self.report.update(before=self.before_state, sample_context=self.context_state(), phase="WARM_AND_MEASURE",
                                   mesh_visibility=visibility, required_visible_meshes=list(self.required_meshes),
                                   dirty_before=bool(bpy.data.is_dirty), fixed_warm_seconds=WARM_SECONDS,
                                   fixed_measure_seconds=MEASURE_SECONDS)
                self.tee = ErrorObserver(sys.stderr)
                sys.stderr = self.tee
                for callbacks, own in ((bpy.app.handlers.frame_change_pre, self.pre_callback), (bpy.app.handlers.frame_change_post, self.post_callback)):
                    callbacks.append(own)
                    self.owned_handlers.append((callbacks, own))
                self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback, (), "WINDOW", "POST_PIXEL")
                self.flush()
                self.phase = "PLAY"
                with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
                    result = bpy.ops.screen.animation_play(reverse=False)
                require("FINISHED" in result and self.screen.is_animation_playing, "Normal animation_play did not start")
                self.play_start_ns = time.perf_counter_ns()
                self.start_ns = self.play_start_ns + int(WARM_SECONDS * 1e9)
                self.end_ns = self.start_ns + int(MEASURE_SECONDS * 1e9)
                self.collecting = True
                return .1
            self.assert_owned()
            require(self.screen.is_animation_playing, "Playback stopped before the fixed window ended")
            require(not self.callback_errors and not self.tee.has_error() and not self.runtime._ERRORS, "Callback/runtime error during playback")
            if time.perf_counter_ns() >= self.end_ns:
                self.finish()
                return None
            return .1
        except BaseException:
            self.finish(traceback.format_exc())
            return None

    def finish(self, error=None):
        global SESSION
        import bpy
        if self.closed:
            return
        finish_entered_ns = time.perf_counter_ns()
        self.closed, self.collecting = True, False
        errors = [error] if error else []
        cleanup = {}
        try:
            self.assert_owned()
            if self.screen.is_animation_playing:
                with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
                    result = bpy.ops.screen.animation_cancel(restore_frame=False)
                require(not self.screen.is_animation_playing and ("FINISHED" in result or "PASS_THROUGH" in result), "Own playback failed to stop")
            cleanup["playback_stopped"] = not self.screen.is_animation_playing
        except BaseException:
            errors.append(traceback.format_exc())
        for callbacks, own in reversed(self.owned_handlers):
            try:
                count = sum(item is own for item in callbacks)
                while any(item is own for item in callbacks):
                    callbacks.remove(own)
                require(count == 1, "Own callback membership changed")
            except BaseException:
                errors.append(traceback.format_exc())
        try:
            if self.draw_handle is not None:
                bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, "WINDOW")
                self.draw_handle = None
            cleanup["own_draw_handler_removed"] = self.draw_handle is None
        except BaseException:
            errors.append(traceback.format_exc())
        try:
            if bpy.app.timers.is_registered(self.timer):
                bpy.app.timers.unregister(self.timer)
            cleanup["own_timer_removed"] = not bpy.app.timers.is_registered(self.timer)
        except BaseException:
            errors.append(traceback.format_exc())
        try:
            cleanup["normal_handler_lists_exact"] = self.handlers_before == handler_snapshot(bpy)
            require(cleanup["normal_handler_lists_exact"], "Standard callback identities/order changed")
        except BaseException:
            errors.append(traceback.format_exc())
        try:
            self.assert_owned()
            if self.before_context is not None:
                with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
                    self.scene.frame_set(self.before_frame[0], subframe=self.before_frame[1])
                    self.area.spaces.active.shading.type = self.before_shading_type
                    if self.scene.sync_mode != self.before_context["sync_mode"]:
                        self.scene.sync_mode = self.before_context["sync_mode"]
                    self.window.view_layer.update()
                self.area.tag_redraw()
                after = self.full_state()
                self.report["after"] = after
                cleanup["all_mesh_key_pose_raw_action_outputs_exact"] = self.before_state["sha256"] == after["sha256"]
                cleanup["normalized_VIEW3D_context_exact"] = self.before_context == after["context"]
                require(cleanup["all_mesh_key_pose_raw_action_outputs_exact"] and cleanup["normalized_VIEW3D_context_exact"], "Original frame/shading/context/model output did not restore exactly")
            self.assert_runtime()
            self.report["private_after"], self.report["artist_after"] = pin(self.private), pin(self.artist)
            cleanup["disks_exact"] = self.private_pin == self.report["private_after"] and self.artist_pin == self.report["artist_after"]
            cleanup["staged_sources_exact"] = self.sources == self.witness.verify_package_manifest(self.package, self.manifest)
            cleanup["manifest_exact"] = self.manifest_pin == pin(self.manifest_pin["path"])
            cleanup["probe_source_exact"] = self.report["script"] == pin(__file__)
            cleanup["proof_dependencies_exact"] = all(value == pin(value["path"]) for value in self.dependencies.values())
            cleanup["receipt_pins_exact"] = all(value == pin(value["path"]) for value in (self.gui_pin, self.artifact_receipt_pin) if value)
            require(all(cleanup.values()), "Protected state/source cleanup proof failed")
        except BaseException:
            errors.append(traceback.format_exc())
        try:
            cleanup["normal_handler_lists_exact"] = self.handlers_before == handler_snapshot(bpy)
            require(cleanup["normal_handler_lists_exact"], "Standard callback identities/order changed after restoration/full proof")
        except BaseException:
            errors.append(traceback.format_exc())
        if self.tee is not None:
            self.report["python_stderr"] = {"text": self.tee.text, "truncated": self.tee.truncated,
                "scope": "Python stderr only; root must inspect native process stderr separately"}
            if self.tee.has_error() or self.tee.truncated:
                errors.append("Python stderr traceback or truncation observed")
            if sys.stderr is self.tee:
                sys.stderr = self.tee.original
                cleanup["stderr_identity_restored"] = True
            else:
                errors.append("Stderr observer ownership changed; foreign stream left untouched")
        changed = changed_draw_events(self.draw_events)
        frame_stats, draw_stats = cadence(self.post_events), cadence(changed)
        coverage = {"frame_change_all_1_30": frame_stats["unique_integer_frames"] == list(range(1, 31)),
                    "changed_draw_all_1_30": draw_stats["unique_integer_frames"] == list(range(1, 31)),
                    "paired_pre_post_observed": bool(self.eval_events),
                    "subframes_zero": all(row[2] == 0.0 for row in self.post_events + self.draw_events)}
        try:
            restored_area_type = self.area.type
        except ReferenceError:
            restored_area_type = None
        self.report.update(completed=error is None and not errors and not self.callback_errors and all(cleanup.values()) and all(coverage.values()),
            phase="CLOSED", errors=errors, callback_errors=self.callback_errors, cleanup=cleanup, coverage=coverage,
            frame_change=frame_stats, changed_scene_frame_draw_callback=draw_stats, all_post_pixel_callbacks=cadence(self.draw_events),
            appended_pre_to_post_ms=distribution([(row[1] - row[0]) / 1e6 for row in self.eval_events]),
            frame_boundary_rows=[{"pre_ms": (row[0]-self.start_ns)/1e6, "post_ms": (row[1]-self.start_ns)/1e6,
                                  "frame": row[2], "subframe": row[3]} for row in self.eval_events],
            draw_boundary_rows=[{"at_ms": (row[0]-self.start_ns)/1e6, "frame": row[1], "subframe": row[2]} for row in self.draw_events],
            dirty_after=bool(bpy.data.is_dirty), restored_area_type=restored_area_type,
            normal_callbacks_preserved=cleanup.get("normal_handler_lists_exact", False),
            clocks={"play_start_ns": self.play_start_ns, "fixed_hot_start_ns": self.start_ns,
                    "fixed_hot_end_ns": self.end_ns, "stop_callback_entered_ns": finish_entered_ns,
                    "finish_proof_ns": time.perf_counter_ns()})
        try:
            self.flush()
        finally:
            self.stream.close()
            if SESSION is self:
                SESSION = None

    def cancel(self):
        self.finish("Owned probe cancelled before completion")


def install(config):
    """Root Console entry; returns a controller with cancel(), never launches."""
    global SESSION
    import bpy
    require(SESSION is None, "This probe already owns an active session")
    controller = Probe(config)
    SESSION = controller
    try:
        bpy.app.timers.register(controller.timer, first_interval=.1)
    except BaseException:
        controller.finish(traceback.format_exc())
        raise
    return controller
