"""Temporary foreground playback profiler for the original X artist only.

Execute this file in the original X.blend Python Console after the operator
has observed that the artist is paused and approved returning this area to
VIEW_3D. No add-on is imported, refreshed, re-registered or saved. Commands
are small JSON files in this directory. POST_PIXEL measures draw callbacks,
not physical monitor presentation. All measured times are inclusive; nested
components must not be added together.
"""

import bpy
from array import array
import datetime
import functools
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time
import traceback
import types


ARTIST = Path(r"D:\Blender\Projects\Character\X\X.blend")
OUT = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round3")
HELPER_NAME = "_x_playback_live_profiler_20261014"
HANDLER_KINDS = (
    "frame_change_pre", "frame_change_post",
    "depsgraph_update_pre", "depsgraph_update_post",
)
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
MAX_EVENTS = 4096
TTL_SECONDS = 15 * 60


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def file_pin(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(),
            "bytes": path.stat().st_size}


def write_json(path, value):
    # A response becomes visible as one complete file, never half-written JSON.
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    temp.replace(path)


def callback_name(callback):
    return str(getattr(callback, "__module__", "")) + "." + str(
        getattr(callback, "__qualname__", getattr(callback, "__name__", type(callback).__name__)))


def distribution(values, scale=1.0):
    converted = [value * scale for value in values]
    if not converted:
        return {"count": 0, "median": None, "mean": None, "min": None, "max": None}
    return {"count": len(converted), "median": statistics.median(converted),
            "mean": statistics.fmean(converted), "min": min(converted),
            "max": max(converted)}


def intervals(events):
    return [(right[0] - left[0]) / 1_000_000
            for left, right in zip(events, events[1:])]


class LiveProfiler:
    def __init__(self):
        self.created = time.monotonic()
        self.closed = False
        self.in_poll = False
        self.seen_ids = set()
        self.sample = None
        self.last_restoration = None
        # Blender timers identify the exact callable object. A fresh bound
        # method object on each attribute read is unsuitable for unregister.
        self.poll_callback = self.poll
        self.helper_module = None
        request_path = OUT / "request.json"
        request_stat = request_path.stat() if request_path.exists() else None
        self.initial_request_signature = (request_stat.st_mtime_ns, request_stat.st_size) if request_stat else None
        self.window = bpy.context.window
        self.screen = bpy.context.screen
        self.area = bpy.context.area
        self.scene = bpy.context.scene
        self.region = None
        self.initial_area_type = self.area.type if self.area else None
        self.root_names = tuple(name for name, module in tuple(sys.modules.items())
                                if module is not None and
                                (name == "character_designer" or name.endswith(".character_designer")))
        self.install_pin = file_pin(ARTIST)
        self.install_dirty = bool(bpy.data.is_dirty)
        self.install_context = self.context_info()
        self._assert_artist()
        if not self.window or not self.screen or not self.area:
            raise RuntimeError("A foreground window, screen and area are required")
        if self.any_playing():
            raise RuntimeError("Artist is already playing; leave it untouched and pause manually")
        if self.area.type not in {"CONSOLE", "VIEW_3D"}:
            raise RuntimeError("Install only in the observed Console or VIEW_3D area")
        # This is the one explicitly authorized installation display change.
        if self.area.type == "CONSOLE":
            self.area.type = "VIEW_3D"
        self.region = next((region for region in self.area.regions if region.type == "WINDOW"), None)
        if self.region is None:
            raise RuntimeError("VIEW_3D WINDOW region is missing")
        self.ready_context = self.context_info()

    def _assert_artist(self):
        if bpy.app.background or not bpy.data.filepath:
            raise RuntimeError("Foreground saved original X.blend is required")
        if Path(bpy.data.filepath).resolve() != ARTIST.resolve():
            raise RuntimeError("Current filepath is not the original X.blend")

    def assert_context(self):
        self._assert_artist()
        if self.window.screen != self.screen or self.window.scene != self.scene:
            raise RuntimeError("Window screen or scene changed during profiling")
        if not any(area == self.area for area in self.screen.areas) or self.area.type != "VIEW_3D":
            raise RuntimeError("Observed VIEW_3D area changed during profiling")

    @staticmethod
    def any_playing():
        return any(window.screen and window.screen.is_animation_playing
                   for window in bpy.context.window_manager.windows)

    def context_info(self):
        active = bpy.context.view_layer.objects.active if bpy.context.view_layer else None
        result = {
            "window_pointer": self.window.as_pointer() if self.window else None,
            "scene": self.scene.name if self.scene else None,
            "scene_pointer": self.scene.as_pointer() if self.scene else None,
            "screen": self.screen.name if self.screen else None,
            "screen_pointer": self.screen.as_pointer() if self.screen else None,
            "area_type": self.area.type if self.area else None,
            "area_pointer": self.area.as_pointer() if self.area else None,
            "area_size": [self.area.width, self.area.height] if self.area else None,
            "mode": bpy.context.mode,
            "active_object": active.name if active else None,
            "selected_objects": sorted(obj.name for obj in bpy.context.selected_objects),
        }
        if self.scene:
            result.update(frame=int(self.scene.frame_current),
                          subframe=float(self.scene.frame_subframe),
                          sync_mode=self.scene.sync_mode)
        if self.screen:
            result["playing"] = bool(self.screen.is_animation_playing)
        if self.area and self.area.type == "VIEW_3D":
            result.update(shading=self.area.spaces.active.shading.type,
                          show_region_ui=bool(self.area.spaces.active.show_region_ui))
        return result

    def addon_info(self):
        result = {}
        for name in self.root_names:
            module = sys.modules.get(name)
            if module is None:
                continue
            entry = {"version": list(getattr(module, "bl_info", {}).get("version", ())),
                     "source_path": getattr(module, "__file__", None)}
            runtime = sys.modules.get(name + ".forearm_twist")
            if runtime is not None:
                entry["forearm_errors"] = dict(getattr(runtime, "_ERRORS", {}))
                entry["forearm_busy"] = bool(getattr(runtime, "_BUSY", False))
            result[name] = entry
        return result

    @staticmethod
    def pose_channels(bone):
        return {"rotation_mode": bone.rotation_mode,
                "location": tuple(bone.location),
                "rotation_euler": tuple(bone.rotation_euler),
                "rotation_quaternion": tuple(bone.rotation_quaternion),
                "rotation_axis_angle": tuple(bone.rotation_axis_angle),
                "scale": tuple(bone.scale)}

    @staticmethod
    def key_coordinates(key):
        coordinates = array("f", [0.0]) * (len(key.data) * 3)
        key.data.foreach_get("co", coordinates)
        return coordinates.tobytes()

    def capture_artist_channels(self):
        poses, shapes, managed = [], [], []
        seen_keys, seen_managed = set(), set()
        runtimes = [sys.modules.get(root + ".forearm_twist") for root in self.root_names]
        runtimes = [runtime for runtime in runtimes if runtime is not None]
        for obj in self.scene.objects:
            if obj.type == "ARMATURE" and obj.pose is not None:
                for bone in obj.pose.bones:
                    poses.append((obj, bone, self.pose_channels(bone)))
            if obj.type != "MESH" or obj.data.shape_keys is None:
                continue
            keys = obj.data.shape_keys
            for key in keys.key_blocks:
                if key.as_pointer() not in seen_keys:
                    seen_keys.add(key.as_pointer())
                    shapes.append((keys, key, {"value": float(key.value), "mute": bool(key.mute)}))
            if "character_designer_forearm_twist_v1" in obj and not runtimes:
                raise RuntimeError("Forearm calibration exists but its loaded runtime is unavailable; cannot prove managed output ownership")
            for runtime in runtimes:
                if getattr(runtime, "RECORD_KEY", "") not in obj:
                    continue
                for side, record in runtime._records(obj).items():
                    key = runtime._managed_key(obj, side, record, required=True, repair_name=False)
                    if key.as_pointer() not in seen_managed:
                        seen_managed.add(key.as_pointer())
                        raw = self.key_coordinates(key)
                        managed.append({"object": obj, "keys": keys, "key": key,
                                        "side": side, "coordinates": raw,
                                        "sha256": hashlib.sha256(raw).hexdigest()})
        snapshot = {"poses": poses, "shapes": shapes, "managed": managed}
        snapshot["before_token"] = self.artist_channel_token(snapshot)
        return snapshot

    def artist_channel_token(self, snapshot):
        poses = [{"object": obj.name, "object_pointer": obj.as_pointer(),
                  "bone": bone.name, "bone_pointer": bone.as_pointer(),
                  "channels": self.pose_channels(bone)}
                 for obj, bone, _before in snapshot["poses"]]
        shapes = [{"keys": keys.name, "keys_pointer": keys.as_pointer(),
                   "key": key.name, "key_pointer": key.as_pointer(),
                   "value": float(key.value), "mute": bool(key.mute)}
                  for keys, key, _before in snapshot["shapes"]]
        layout = [{"object": obj.name, "pointer": obj.as_pointer(), "type": obj.type,
                   "pose_bones": [(bone.name, bone.as_pointer()) for bone in obj.pose.bones]
                   if obj.type == "ARMATURE" and obj.pose is not None else None,
                   "shape_keys": [(key.name, key.as_pointer()) for key in obj.data.shape_keys.key_blocks]
                   if obj.type == "MESH" and obj.data.shape_keys is not None else None}
                  for obj in self.scene.objects]
        raw = json.dumps({"poses": poses, "shapes": shapes, "layout": layout}, ensure_ascii=False,
                         sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return {"sha256": hashlib.sha256(raw).hexdigest(),
                "pose_bones": len(poses), "shape_key_blocks": len(shapes)}

    @staticmethod
    def animation_owners(owner, path):
        """Conservatively report existing driver/action ownership, never alter it."""
        animation = getattr(owner, "animation_data", None)
        if animation is None:
            return []
        found = []
        for curve in animation.drivers:
            if curve.data_path == path:
                found.append("driver")
        actions = []
        if animation.action is not None:
            actions.append(("active_action", animation.action))
        for track in animation.nla_tracks:
            for strip in track.strips:
                if getattr(strip, "action", None) is not None:
                    actions.append(("nla_action", strip.action))
        for kind, action in actions:
            curves = []
            try:
                curves.extend(action.fcurves)
            except (AttributeError, RuntimeError):
                pass
            # All slot bags are checked conservatively. A reported potential
            # owner is not a claim that this channel is currently evaluated.
            for layer in getattr(action, "layers", ()):
                for strip in layer.strips:
                    for bag in getattr(strip, "channelbags", ()):
                        curves.extend(bag.fcurves)
            if any(curve.data_path == path for curve in curves):
                found.append(kind + ":" + action.name)
        return sorted(set(found))

    def potential_animation_owners(self, owner, path):
        try:
            return self.animation_owners(owner, path)
        except BaseException as exc:
            # Metadata inspection must not prevent assigning the captured raw
            # value. Its uncertainty is visible in the restoration report.
            return ["ownership_scan_failed:" + type(exc).__name__ + ":" + str(exc)]

    def restore_artist_channels(self, snapshot, errors):
        changed, conflicts = 0, []
        live_objects = {obj.as_pointer() for obj in self.scene.objects}
        for obj, bone, before in snapshot["poses"]:
            try:
                if obj.as_pointer() not in live_objects or obj.pose is None or not any(candidate.as_pointer() == bone.as_pointer() for candidate in obj.pose.bones):
                    raise RuntimeError("Original pose bone is no longer in the sampled scene")
                for channel, value in before.items():
                    current = getattr(bone, channel)
                    current = current if channel == "rotation_mode" else tuple(current)
                    if current == value:
                        continue
                    owners = self.potential_animation_owners(obj, bone.path_from_id(channel))
                    if owners:
                        conflicts.append({"object": obj.name, "bone": bone.name,
                                          "channel": channel, "potential_owners": owners})
                    setattr(bone, channel, value)
                    changed += 1
            except BaseException:
                errors.append(traceback.format_exc())
        for keys, key, before in snapshot["shapes"]:
            try:
                if not any(candidate.as_pointer() == key.as_pointer() for candidate in keys.key_blocks):
                    raise RuntimeError("Original Shape Key is no longer a member of its Key datablock")
                for channel, value in before.items():
                    if getattr(key, channel) == value:
                        continue
                    owners = self.potential_animation_owners(keys, key.path_from_id(channel))
                    if owners:
                        conflicts.append({"keys": keys.name, "key": key.name,
                                          "channel": channel, "potential_owners": owners})
                    setattr(key, channel, value)
                    changed += 1
            except BaseException:
                errors.append(traceback.format_exc())
        if changed:
            try:
                with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
                    self.window.view_layer.update()
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                    for root in self.root_names:
                        runtime = sys.modules.get(root + ".forearm_twist")
                        if runtime is not None:
                            runtime.update_runtime(self.scene, depsgraph)
            except BaseException:
                errors.append(traceback.format_exc())
        return changed, conflicts

    def verify_artist_channels(self, sample, errors):
        snapshot = sample["artist_channels"]
        token_before = snapshot["before_token"]
        try:
            token_after = self.artist_channel_token(snapshot)
        except BaseException:
            token_after = None
            errors.append(traceback.format_exc())
        coordinate_checks = []
        coordinate_backups = []
        for index, entry in enumerate(snapshot["managed"]):
            try:
                current = self.key_coordinates(entry["key"])
                equal = current == entry["coordinates"]
                after_sha = hashlib.sha256(current).hexdigest()
            except BaseException:
                equal, after_sha = False, None
                errors.append(traceback.format_exc())
            check = {"object": entry["object"].name, "key": entry["key"].name,
                     "before_sha256": entry["sha256"], "after_sha256": after_sha,
                     "bytes": len(entry["coordinates"]), "equal": equal}
            coordinate_checks.append(check)
            if not equal:
                path = OUT / ("recovery_" + sample["id"] + "_managed_" + str(index) + ".float32.bin")
                path.write_bytes(entry["coordinates"])
                backup_pin = file_pin(path)
                if backup_pin["sha256"] != entry["sha256"] or backup_pin["bytes"] != len(entry["coordinates"]):
                    raise RuntimeError("Managed coordinate recovery backup did not verify")
                coordinate_backups.append({**check, "path": str(path), "byte_order": sys.byteorder})
        raw_equal = token_before == token_after
        coordinates_equal = all(check["equal"] for check in coordinate_checks)
        if not raw_equal or not coordinates_equal:
            # Private recovery evidence is separate from the small report.
            # Do not guess at driver ownership or force stored coordinates into
            # an evaluated output after the runtime failed to reproduce it.
            recovery_path = OUT / ("recovery_" + sample["id"] + "_channels.json")
            write_json(recovery_path, {
                "schema": "x.playback-live-channel-recovery/1", "id": sample["id"],
                "artist": str(ARTIST), "created_utc": utc_now(),
                "before_token": token_before, "after_token": token_after,
                "pose_channels": [{"object": obj.name, "bone": bone.name, "channels": values}
                                  for obj, bone, values in snapshot["poses"]],
                "shape_channels": [{"keys": keys.name, "key": key.name, "channels": values}
                                   for keys, key, values in snapshot["shapes"]],
                "managed_coordinate_backups": coordinate_backups,
            })
            errors.append("Artist raw channels or managed coordinate bytes were not reproduced; private recovery evidence: " + str(recovery_path))
        return {"before": token_before, "after": token_after, "raw_channels_equal": raw_equal,
                "managed_coordinate_checks": coordinate_checks,
                "managed_coordinates_equal": coordinates_equal,
                "coordinate_backups": coordinate_backups,
                "raw_channel_scope": "Standard PoseBone transform channels and all scene mesh KeyBlock value/mute only; not a complete artist state proof."}

    def base_report(self, request_id, operation):
        return {
            "schema": "x.playback-live-profile/1", "id": request_id,
            "operation": operation, "created_utc": utc_now(), "pid": os.getpid(),
            "blender": bpy.app.version_string, "addons": self.addon_info(),
            "installation_context": self.install_context,
            "view_context": self.ready_context,
            "no_save": True, "no_refresh": True, "no_addon_import": True,
            "timing_scope": "Inclusive timings overlap; do not sum nested components. POST_PIXEL is a draw callback, not monitor presentation. Instrumentation adds wrapper, clock, counter, draw-handler and 0.5-second polling overhead; this instrumented sample does not independently measure that overhead or all GPU/native costs. Warmup is excluded from counters and events.",
        }

    def respond(self, request_id, report):
        write_json(OUT / ("response_" + request_id + ".json"), report)

    def snapshot(self, request_id):
        self.assert_context()
        report = self.base_report(request_id, "snapshot")
        report.update(completed=True, context=self.context_info(),
                      dirty=bool(bpy.data.is_dirty), disk=file_pin(ARTIST),
                      handlers={kind: [callback_name(callback) for callback in getattr(bpy.app.handlers, kind)]
                                for kind in HANDLER_KINDS})
        self.respond(request_id, report)

    def timed(self, callback, key, sample):
        @functools.wraps(callback)
        def wrapped(*args, **kwargs):
            if not sample["measuring"]:
                return callback(*args, **kwargs)
            began = time.perf_counter_ns()
            failed = False
            try:
                return callback(*args, **kwargs)
            except BaseException:
                failed = True
                raise
            finally:
                elapsed = time.perf_counter_ns() - began
                stat = sample["stats"].setdefault(key, [0, 0, 0, 0])
                stat[0] += 1
                stat[1] += elapsed
                stat[2] = max(stat[2], elapsed)
                stat[3] += int(failed)
        return wrapped

    def instrument(self, sample):
        sample["handler_originals"] = {kind: tuple(getattr(bpy.app.handlers, kind)) for kind in HANDLER_KINDS}
        sample["handler_replacements"] = []
        sample["function_replacements"] = []
        sample["panel_replacements"] = []
        sample["boundaries"] = []
        sample["draw_handle"] = None
        for kind in HANDLER_KINDS:
            handlers = getattr(bpy.app.handlers, kind)
            for index, original in enumerate(sample["handler_originals"][kind]):
                wrapped = self.timed(original, "handler:" + kind + ":" + str(index) + ":" + callback_name(original), sample)
                handlers[index] = wrapped
                sample["handler_replacements"].append((handlers, original, wrapped))
        # These two markers bracket frame handlers and native frame evaluation.
        def frame_pre(scene, *args):
            if sample["measuring"] and scene == self.scene:
                sample["pending_frames"].append((time.perf_counter_ns(), int(scene.frame_current), float(scene.frame_subframe)))

        def frame_post(scene, *args):
            if sample["measuring"] and scene == self.scene:
                ended = time.perf_counter_ns()
                if sample["pending_frames"]:
                    began, frame, subframe = sample["pending_frames"].pop()
                    if len(sample["eval_events"]) < MAX_EVENTS:
                        sample["eval_events"].append([began, ended, frame, subframe])
                    else:
                        sample["event_limit_reached"] = True

        bpy.app.handlers.frame_change_pre.insert(0, frame_pre)
        sample["boundaries"].append((bpy.app.handlers.frame_change_pre, frame_pre))
        bpy.app.handlers.frame_change_post.append(frame_post)
        sample["boundaries"].append((bpy.app.handlers.frame_change_post, frame_post))
        functions = {
            "forearm_twist": ("update_runtime", "_prepare_runtime_records", "_calculate_object", "_calculate_records"),
            "forearm_original_inventory": ("validate",),
            "animation_worklist_target": ("control_rest_view", "_prove_motion_data"),
            "unity_animation": ("_rest_state",),
        }
        for root in self.root_names:
            for suffix, names in functions.items():
                module = sys.modules.get(root + "." + suffix)
                if module is None:
                    continue
                for name in names:
                    original = getattr(module, name, None)
                    if not callable(original):
                        continue
                    wrapped = self.timed(original, "function:" + root + "." + suffix + "." + name, sample)
                    setattr(module, name, wrapped)
                    sample["function_replacements"].append((module, name, original, wrapped))
        seen_classes = set()
        for name, module in tuple(sys.modules.items()):
            if module is None or not any(name == root or name.startswith(root + ".") for root in self.root_names):
                continue
            for cls in tuple(vars(module).values()):
                if not isinstance(cls, type) or cls in seen_classes:
                    continue
                seen_classes.add(cls)
                if not any(getattr(cls, "__module__", "") == root or getattr(cls, "__module__", "").startswith(root + ".") for root in self.root_names):
                    continue
                if not issubclass(cls, bpy.types.Panel) or not bool(getattr(cls, "is_registered", False)):
                    continue
                original = cls.__dict__.get("draw")
                if not callable(original):
                    continue
                wrapped = self.timed(original, "panel:" + callback_name(original), sample)
                setattr(cls, "draw", wrapped)
                sample["panel_replacements"].append((cls, "draw", original, wrapped))

        def drawn():
            if not sample["measuring"] or bpy.context.area != self.area:
                return
            if len(sample["display_events"]) < MAX_EVENTS:
                sample["display_events"].append([time.perf_counter_ns(), int(self.scene.frame_current), float(self.scene.frame_subframe)])
            else:
                sample["event_limit_reached"] = True

        sample["draw_handle"] = bpy.types.SpaceView3D.draw_handler_add(drawn, (), "WINDOW", "POST_PIXEL")

    def begin_sample(self, request_id, request):
        self.assert_context()
        if self.any_playing():
            raise RuntimeError("Cannot start a sample while any window is already playing")
        shading = request.get("shading", "MATERIAL")
        if shading not in {"MATERIAL", "SOLID"}:
            raise ValueError("shading must be MATERIAL or SOLID")
        seconds = request.get("seconds", 8)
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 3 <= seconds <= 20:
            raise ValueError("seconds must be a finite number between 3 and 20")
        warmup_seconds = request.get("warmup_seconds", 2)
        if isinstance(warmup_seconds, bool) or not isinstance(warmup_seconds, (int, float)) or not math.isfinite(warmup_seconds) or not 0 <= warmup_seconds <= 5:
            raise ValueError("warmup_seconds must be a finite number between 0 and 5")
        hide_sidebar = request.get("hide_sidebar", False)
        if not isinstance(hide_sidebar, bool):
            raise ValueError("hide_sidebar must be boolean")
        artist_channels = self.capture_artist_channels()
        sample = {
            "id": request_id, "request": {"shading": shading, "seconds": seconds,
                                              "warmup_seconds": warmup_seconds, "hide_sidebar": hide_sidebar},
            "before": self.context_info(), "before_disk": file_pin(ARTIST),
            "dirty_before": bool(bpy.data.is_dirty), "stats": {},
            "pending_frames": [], "eval_events": [], "display_events": [],
            "event_limit_reached": False, "measuring": False,
            "phase": "warmup", "total_start_ns": None,
            "playback_start_ns": None, "playback_stop_ns": None,
            "measurement_stop_ns": None,
            "artist_channels": artist_channels,
        }
        self.sample = sample
        try:
            self.instrument(sample)
            self.area.spaces.active.shading.type = shading
            if hide_sidebar:
                self.area.spaces.active.show_region_ui = False
            self.scene.sync_mode = "NONE"
            self.area.tag_redraw()
            sample["total_start_ns"] = time.perf_counter_ns()
            sample["warmup_deadline"] = time.monotonic() + warmup_seconds
            with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
                result = bpy.ops.screen.animation_play(reverse=False, sync=False)
            if "FINISHED" not in result or not self.screen.is_animation_playing:
                raise RuntimeError("animation_play did not enter playback: " + repr(result))
        except BaseException:
            self.finish_sample("start_failed", traceback.format_exc())

    def restore_instrumentation(self, sample, errors):
        # Restore only our substitutions; never delete another task's callbacks.
        for handlers, boundary in sample.get("boundaries", []):
            try:
                if boundary in handlers:
                    handlers.remove(boundary)
            except BaseException:
                errors.append(traceback.format_exc())
        for handlers, original, wrapped in reversed(sample.get("handler_replacements", [])):
            try:
                for index, value in enumerate(handlers):
                    if value is wrapped:
                        handlers[index] = original
            except BaseException:
                errors.append(traceback.format_exc())
        restored_functions = True
        restored_panels = True
        for replacements, kind in ((sample.get("function_replacements", []), "function"),
                                   (sample.get("panel_replacements", []), "panel")):
            for owner, name, original, wrapped in reversed(replacements):
                try:
                    current = getattr(owner, name, None)
                    if current is wrapped:
                        setattr(owner, name, original)
                    if getattr(owner, name, None) is not original:
                        if kind == "function":
                            restored_functions = False
                        else:
                            restored_panels = False
                except BaseException:
                    errors.append(traceback.format_exc())
                    if kind == "function":
                        restored_functions = False
                    else:
                        restored_panels = False
        draw_removed = True
        if sample.get("draw_handle") is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(sample["draw_handle"], "WINDOW")
                sample["draw_handle"] = None
            except BaseException:
                draw_removed = False
                errors.append(traceback.format_exc())
        handlers_equal = {kind: tuple(getattr(bpy.app.handlers, kind)) == originals
                          for kind, originals in sample.get("handler_originals", {}).items()}
        return {"handlers_equal": handlers_equal, "functions_equal": restored_functions,
                "panels_equal": restored_panels, "draw_handler_removed": draw_removed}

    def finish_sample(self, reason="elapsed", failure=None):
        sample = self.sample
        if sample is None:
            return
        sample["measurement_stop_ns"] = time.perf_counter_ns()
        sample["measuring"] = False
        errors = []
        if failure:
            errors.append(failure)
        # Stop playback before restoring wrappers or artist frame. Every cleanup
        # step is attempted even if an earlier one failed.
        try:
            if self.screen.is_animation_playing:
                with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area, region=self.region):
                    result = bpy.ops.screen.animation_cancel(restore_frame=False)
                if "FINISHED" not in result:
                    errors.append("animation_cancel: " + repr(result))
        except BaseException:
            errors.append(traceback.format_exc())
        sample["playback_stop_ns"] = time.perf_counter_ns()
        instrumentation = self.restore_instrumentation(sample, errors)
        before = sample["before"]
        try:
            self.scene.sync_mode = before["sync_mode"]
        except BaseException:
            errors.append(traceback.format_exc())
        try:
            self.scene.frame_set(before["frame"], subframe=before["subframe"])
        except BaseException:
            errors.append(traceback.format_exc())
        restored_channel_count, channel_conflicts = self.restore_artist_channels(sample["artist_channels"], errors)
        channel_check = self.verify_artist_channels(sample, errors)
        try:
            if self.area.type != "VIEW_3D":
                raise RuntimeError("User changed profiler area type; do not override it during cleanup")
            self.area.spaces.active.shading.type = before["shading"]
            self.area.spaces.active.show_region_ui = before["show_region_ui"]
            self.area.tag_redraw()
        except BaseException:
            errors.append(traceback.format_exc())
        after = self.context_info()
        fields = ("frame", "subframe", "sync_mode", "playing", "shading", "show_region_ui",
                  "scene_pointer", "screen_pointer", "area_pointer", "mode", "active_object", "selected_objects")
        restored = {key: after.get(key) == before.get(key) for key in fields}
        restored.update(instrumentation)
        restored["raw_channels_equal"] = channel_check["raw_channels_equal"]
        restored["managed_coordinates_equal"] = channel_check["managed_coordinates_equal"]
        self.last_restoration = restored
        report = self.base_report(sample["id"], "sample")
        start = sample.get("playback_start_ns")
        stop = sample.get("measurement_stop_ns")
        elapsed = (stop - start) / 1_000_000_000 if start is not None and stop is not None else None
        total_start = sample.get("total_start_ns")
        total_stop = sample.get("playback_stop_ns")
        total_elapsed = (total_stop - total_start) / 1_000_000_000 if total_start is not None and total_stop is not None else None
        warmup_end = start if start is not None else stop
        warmup_elapsed = (warmup_end - total_start) / 1_000_000_000 if total_start is not None and warmup_end is not None else None
        display = sample["display_events"]
        changed = []
        for event in display:
            if not changed or event[1:] != changed[-1][1:]:
                changed.append(event)
        evaluation = sample["eval_events"]
        frame_starts = [[event[0], event[2], event[3]] for event in evaluation]
        before_disk = sample["before_disk"]
        try:
            after_disk = file_pin(ARTIST)
        except BaseException:
            after_disk = None
            errors.append(traceback.format_exc())
        restoration_ok = all(value for key, value in restored.items() if key != "handlers_equal") and all(restored["handlers_equal"].values())
        report.update(
            completed=reason == "elapsed" and not errors and restoration_ok and before_disk == after_disk,
            stop_reason=reason, request=sample["request"], before=before, after=after,
            restored=restored, dirty_before=sample["dirty_before"], dirty_after=bool(bpy.data.is_dirty),
            artist_channel_check=channel_check, restored_raw_channel_count=restored_channel_count,
            raw_channel_animation_conflicts=channel_conflicts,
            raw_channel_restoration_note="Only existing changed channels were assigned. Existing action/driver ownership is reported conservatively; update_runtime is the already-loaded Forearm evaluator, not an add-on refresh. Any post-update mismatch fails the sample and retains private recovery evidence.",
            disk_before=before_disk, disk_after=after_disk, disk_unchanged=before_disk == after_disk,
            playback_elapsed_seconds=elapsed, total_playback_elapsed_seconds=total_elapsed,
            actual_warmup_seconds=warmup_elapsed, measurement_started=start is not None,
            event_limit_reached=sample["event_limit_reached"],
            frame_evaluation_ms=distribution([(event[1] - event[0]) / 1_000_000 for event in evaluation]),
            frame_pre_interval_ms=distribution(intervals(frame_starts)),
            post_pixel_interval_ms=distribution(intervals(display)),
            displayed_frame_change_interval_ms=distribution(intervals(changed)),
            evaluated_frame_count=len(evaluation), post_pixel_count=len(display), displayed_frame_change_count=len(changed),
            observed_post_pixel_hz=(len(display) - 1) / ((display[-1][0] - display[0][0]) / 1_000_000_000) if len(display) > 1 and display[-1][0] > display[0][0] else None,
            observed_displayed_frame_change_hz=(len(changed) - 1) / ((changed[-1][0] - changed[0][0]) / 1_000_000_000) if len(changed) > 1 and changed[-1][0] > changed[0][0] else None,
            components={key: {"count": value[0], "total_ms": value[1] / 1_000_000,
                              "mean_ms": value[1] / value[0] / 1_000_000,
                              "max_ms": value[2] / 1_000_000, "exception_count": value[3]}
                        for key, value in sorted(sample["stats"].items())},
            frame_boundaries=[{"pre_ms": (event[0] - start) / 1_000_000,
                               "post_ms": (event[1] - start) / 1_000_000,
                               "frame": event[2], "subframe": event[3]}
                              for event in evaluation] if start is not None else [],
            display_boundaries=[{"at_ms": (event[0] - start) / 1_000_000,
                                 "frame": event[1], "subframe": event[2]}
                                for event in display] if start is not None else [],
            errors=errors,
        )
        self.sample = None
        self.respond(sample["id"], report)

    def close(self, reason="close"):
        if self.closed:
            return
        try:
            if self.sample is not None:
                self.finish_sample(reason)
        finally:
            self.closed = True
            try:
                # Returning None removes the currently executing timer. Only
                # unregister explicitly when close() was called externally.
                if not self.in_poll and bpy.app.timers.is_registered(self.poll_callback):
                    bpy.app.timers.unregister(self.poll_callback)
            finally:
                if sys.modules.get(HELPER_NAME) is self.helper_module:
                    del sys.modules[HELPER_NAME]

    def poll(self):
        if self.closed:
            return None
        self.in_poll = True
        try:
            if time.monotonic() - self.created >= TTL_SECONDS:
                self.close("automatic_15_minute_cleanup")
                write_json(OUT / "live_profiler_closed.json", {"closed": True, "reason": "ttl", "created_utc": utc_now(), "last_restoration": self.last_restoration})
                return None
            if self.sample is not None:
                self.assert_context()
                if not self.screen.is_animation_playing:
                    self.finish_sample("playback_stopped_early")
                elif self.sample["phase"] == "warmup" and time.monotonic() >= self.sample["warmup_deadline"]:
                    # Ignore cold mode/shader work and begin one clean hot
                    # interval. Boundary callbacks do not collect warmup.
                    self.sample["pending_frames"].clear()
                    self.sample["playback_start_ns"] = time.perf_counter_ns()
                    self.sample["deadline"] = time.monotonic() + self.sample["request"]["seconds"]
                    self.sample["phase"] = "measuring"
                    self.sample["measuring"] = True
                elif self.sample["phase"] == "measuring" and time.monotonic() >= self.sample["deadline"]:
                    self.finish_sample()
            request_path = OUT / "request.json"
            if request_path.exists():
                request_stat = request_path.stat()
                # Installing a helper must never replay a stale sample command
                # left by a previous invocation. Write commands after ready.
                if (request_stat.st_mtime_ns, request_stat.st_size) == self.initial_request_signature:
                    return 0.5
                if request_stat.st_size > 32768:
                    raise ValueError("request.json exceeds 32 KiB")
                # An incomplete writer is retried next tick; no command is run.
                try:
                    request = json.loads(request_path.read_text(encoding="utf-8-sig"))
                except json.JSONDecodeError:
                    return 0.5
                if not isinstance(request, dict):
                    raise ValueError("request.json must contain an object")
                request_id = request.get("id")
                if not isinstance(request_id, str) or not ID_PATTERN.fullmatch(request_id):
                    raise ValueError("request id must be 1–64 ASCII letters, digits, underscores or hyphens")
                if request_id not in self.seen_ids:
                    self.seen_ids.add(request_id)
                    operation = request.get("operation")
                    try:
                        if operation == "close":
                            self.close()
                            report = self.base_report(request_id, operation)
                            report.update(completed=True, closed=True, last_restoration=self.last_restoration,
                                          context=self.context_info(), dirty=bool(bpy.data.is_dirty))
                            self.respond(request_id, report)
                            return None
                        if self.sample is not None:
                            raise RuntimeError("Another sample is active; only close is accepted during playback")
                        if operation == "snapshot":
                            self.snapshot(request_id)
                        elif operation == "sample":
                            self.begin_sample(request_id, request)
                        else:
                            raise ValueError("operation must be snapshot, sample or close")
                    except BaseException:
                        report = self.base_report(request_id, operation)
                        report.update(completed=False, errors=[traceback.format_exc()])
                        self.respond(request_id, report)
            return 0.5
        except BaseException:
            failure = traceback.format_exc()
            try:
                if self.sample is not None:
                    self.finish_sample("poll_failed", failure)
                self.close("poll_failed")
            finally:
                write_json(OUT / "live_profiler_failure.json", {"created_utc": utc_now(), "errors": [failure], "closed": self.closed, "last_restoration": self.last_restoration})
            return None
        finally:
            self.in_poll = False


if HELPER_NAME in sys.modules:
    raise RuntimeError("A live profiler helper already exists; send operation=close before reinstalling")
OUT.mkdir(parents=True, exist_ok=True)
helper = types.ModuleType(HELPER_NAME)
controller = None
try:
    controller = LiveProfiler()
    helper.controller = controller
    helper.close = controller.close
    controller.helper_module = helper
    sys.modules[HELPER_NAME] = helper
    bpy.app.timers.register(controller.poll_callback, first_interval=0.5)
    write_json(OUT / "live_profiler_ready.json", {
        "schema": "x.playback-live-profiler-ready/1", "ready": True, "created_utc": utc_now(),
        "pid": os.getpid(), "blender": bpy.app.version_string, "addons": controller.addon_info(),
        "installation_context": controller.install_context, "view_context": controller.ready_context,
        "artist_disk": controller.install_pin, "dirty": controller.install_dirty,
        "command_path": str(OUT / "request.json"), "helper_module": HELPER_NAME,
        "poll_seconds": 0.5, "automatic_cleanup_seconds": TTL_SECONDS,
        "preexisting_request_ignored": controller.initial_request_signature is not None,
        "initial_console_returned_to_view3d": controller.initial_area_type == "CONSOLE",
        "save": False, "refresh": False, "addon_import": False,
    })
    print("X live profiler ready: request.json; send snapshot/sample/close. No save or refresh.")
except BaseException:
    failure = traceback.format_exc()
    if controller is not None:
        controller.close("install_failed")
    write_json(OUT / "live_profiler_failure.json", {"created_utc": utc_now(), "errors": [failure], "phase": "install"})
    raise
