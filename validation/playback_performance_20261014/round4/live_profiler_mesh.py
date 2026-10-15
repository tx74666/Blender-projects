"""Pinned round3 foreground profiler with reversible mesh diagnostics.

Install only in the paused original X artist after GUI recovery authorization.
Requests may add hide_objects=["Cosha", "Shoes"] and disable_modifiers={
"Cosha": ["Subdivision"], "Shoes": ["Armature", "Mirror"]}. Names must match
the existing objects/modifiers exactly. Cosha permits only SUBSURF; Shoes
permits only ARMATURE/MIRROR. suspend_actions is deliberately unsupported.
The inherited warmup defaults to 2 seconds, measurement to 8 seconds. No save,
refresh, add-on import, deletion, action change or cross-frame proof cache.
"""

import ast
import hashlib
from pathlib import Path
import sys


BASE_PATH = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round3\live_profiler.py")
BASE_SHA256 = "6dd7a0adf34390abc74ad2cf80838981f8e2a89f7fdb72968b276b16df464551"
DERIVED_PATH = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\live_profiler_mesh.py")
OLD_HELPER_NAME = "_x_playback_live_profiler_20261014"
NEW_HELPER_NAME = "_x_playback_live_mesh_profiler_20261014"

base_raw = BASE_PATH.read_bytes()
if hashlib.sha256(base_raw).hexdigest() != BASE_SHA256:
    raise RuntimeError("Original round3 profiler no longer matches its fixed pin")
base_text = base_raw.decode("utf-8-sig").replace("\r\n", "\n")
base_prefix, base_marker, _base_installation = base_text.partition("\nif HELPER_NAME in sys.modules:\n")
if not base_marker:
    raise RuntimeError("Pinned original installation boundary is missing")
base_tree = ast.parse(base_prefix, filename=str(BASE_PATH))
if not (isinstance(base_tree.body[-1], ast.ClassDef) and base_tree.body[-1].name == "LiveProfiler"):
    raise RuntimeError("Unexpected original definition boundary")
if any(not isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign,
                             ast.FunctionDef, ast.ClassDef)) for node in base_tree.body):
    raise RuntimeError("Unexpected original top-level execution in definitions")
# Execute the pinned definitions, never the original helper installation.
exec(compile(base_tree, str(BASE_PATH), "exec"), globals())
OUT = DERIVED_PATH.parent
HELPER_NAME = NEW_HELPER_NAME
ALLOWED_OBJECTS = frozenset(("Cosha", "Shoes"))
ALLOWED_MODIFIER_TYPES = {"Cosha": frozenset(("SUBSURF",)),
                          "Shoes": frozenset(("MIRROR", "ARMATURE"))}


class MeshLiveProfiler(LiveProfiler):
    def runtime_error_state(self):
        return {root: {"errors": dict(getattr(module, "_ERRORS", {})),
                       "busy": bool(getattr(module, "_BUSY", False))}
                for root in self.root_names
                if (module := sys.modules.get(root + ".forearm_twist")) is not None}

    def mesh_control_state(self):
        state = []
        for name in sorted(ALLOWED_OBJECTS):
            obj = self.scene.objects.get(name)
            if obj is None:
                state.append({"name": name, "present": False})
                continue
            state.append({"name": name, "present": True,
                          "pointer": obj.as_pointer(), "type": obj.type,
                          "hide_set": bool(obj.hide_get(view_layer=self.window.view_layer)),
                          "hide_viewport": bool(obj.hide_viewport),
                          "hide_render": bool(obj.hide_render),
                          "modifiers": [{"name": modifier.name,
                                         "pointer": modifier.as_pointer(),
                                         "type": modifier.type,
                                         "show_viewport": bool(modifier.show_viewport),
                                         "show_render": bool(modifier.show_render)}
                                        for modifier in obj.modifiers]})
        return state

    @staticmethod
    def action_summary(animation):
        if animation is None:
            return None
        action = animation.action
        result = {"action": action.name if action else None,
                  "driver_count": len(animation.drivers),
                  "driver_paths": sorted({curve.data_path for curve in animation.drivers})[:64],
                  "nla_track_count": len(animation.nla_tracks)}
        if action is None:
            return result
        curves = {}
        try:
            curves.update({curve.as_pointer(): curve for curve in action.fcurves})
        except (AttributeError, RuntimeError):
            pass
        for layer in getattr(action, "layers", ()):
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", ()):
                    curves.update({curve.as_pointer(): curve for curve in bag.fcurves})
        paths = sorted({curve.data_path for curve in curves.values()})
        result.update(fcurve_count=len(curves), curve_paths=paths[:64],
                      curve_paths_truncated=len(paths) > 64,
                      slot_handle=getattr(animation, "action_slot_handle", None))
        return result

    def geometry_summary(self):
        result = []
        for name in sorted(ALLOWED_OBJECTS):
            obj = self.scene.objects.get(name)
            if obj is None:
                result.append({"name": name, "present": False})
                continue
            entry = {"name": name, "present": True, "type": obj.type,
                     "object_pointer": obj.as_pointer(),
                     "hide_set": bool(obj.hide_get(view_layer=self.window.view_layer)),
                     "hide_viewport": bool(obj.hide_viewport),
                     "action": self.action_summary(obj.animation_data),
                     "modifiers": []}
            if obj.type == "MESH":
                keys = obj.data.shape_keys
                entry.update(mesh=obj.data.name, base_vertices=len(obj.data.vertices),
                             base_edges=len(obj.data.edges), base_faces=len(obj.data.polygons),
                             vertex_group_count=len(obj.vertex_groups),
                             shape_key_count=len(keys.key_blocks) if keys else 0,
                             key_animation=self.action_summary(keys.animation_data) if keys else None,
                             material_slot_count=len(obj.material_slots),
                             evaluated_geometry_scope="Not extracted; original base counts and current modifier flags only")
            for modifier in obj.modifiers:
                item = {"name": modifier.name, "type": modifier.type,
                        "viewport": bool(modifier.show_viewport),
                        "render": bool(modifier.show_render)}
                if modifier.type == "SUBSURF":
                    item.update(levels=modifier.levels, render_levels=modifier.render_levels)
                if modifier.type == "ARMATURE":
                    item.update(rig=modifier.object.name if modifier.object else None,
                                vertex_groups=bool(modifier.use_vertex_groups),
                                envelopes=bool(modifier.use_bone_envelopes),
                                preserve_volume=bool(modifier.use_deform_preserve_volume))
                entry["modifiers"].append(item)
            result.append(entry)
        return result

    def prepare_mesh_request(self, request):
        if "suspend_actions" in request:
            raise ValueError("suspend_actions is unsupported; actions are retained")
        hide_names = request.get("hide_objects", [])
        disable = request.get("disable_modifiers", {})
        if (not isinstance(hide_names, list) or len(hide_names) > 2
                or any(not isinstance(name, str) or name not in ALLOWED_OBJECTS for name in hide_names)
                or len(set(hide_names)) != len(hide_names)):
            raise ValueError("hide_objects must be a unique list drawn from Cosha and Shoes")
        if (not isinstance(disable, dict) or len(disable) > 2
                or any(not isinstance(name, str) or name not in ALLOWED_OBJECTS for name in disable)):
            raise ValueError("disable_modifiers must map Cosha/Shoes to exact modifier name lists")
        touched = set(hide_names) | set(disable)
        objects = {}
        for name in touched:
            obj = self.scene.objects.get(name)
            if (obj is None or obj.type != "MESH" or obj.library or obj.override_library
                    or self.window.view_layer.objects.get(name) is not obj):
                raise ValueError("Diagnostic target must be the existing local scene/view-layer Mesh: " + name)
            if obj.mode == "EDIT":
                raise ValueError("Leave Mesh Edit Mode before diagnostic playback")
            objects[name] = obj
        hides, modifiers = [], []
        for name in hide_names:
            obj = objects[name]
            hides.append((obj, bool(obj.hide_get(view_layer=self.window.view_layer))))
        for name, modifier_names in disable.items():
            if (not isinstance(modifier_names, list) or len(modifier_names) > 4
                    or any(not isinstance(value, str) or not value for value in modifier_names)
                    or len(set(modifier_names)) != len(modifier_names)):
                raise ValueError("Each modifier list must contain unique exact names")
            obj = objects[name]
            for modifier_name in modifier_names:
                modifier = obj.modifiers.get(modifier_name)
                if modifier is None or modifier.type not in ALLOWED_MODIFIER_TYPES[name]:
                    raise ValueError("Disallowed or absent diagnostic modifier: " + name + "/" + modifier_name)
                owners = self.potential_animation_owners(obj, modifier.path_from_id("show_viewport"))
                if owners:
                    raise ValueError("Animated or uncertain viewport flag cannot be overridden: " + name + "/" + modifier_name + " " + repr(owners))
                modifiers.append((obj, modifier, bool(modifier.show_viewport)))
        return {"request": {"hide_objects": list(hide_names),
                            "disable_modifiers": {name: list(names) for name, names in disable.items()}},
                "hide_entries": hides, "modifier_entries": modifiers,
                "before_controls": self.mesh_control_state(),
                "before_geometry": self.geometry_summary(),
                "runtime_errors_before": self.runtime_error_state()}

    def begin_sample(self, request_id, request):
        self.assert_context()
        if self.any_playing():
            raise RuntimeError("Pause all existing window playback before sampling")
        if bpy.context.mode not in {"OBJECT", "POSE"}:
            raise RuntimeError("Diagnostic sampling requires Object or Pose Mode")
        self._prepared_mesh_sample = self.prepare_mesh_request(request)
        try:
            super().begin_sample(request_id, request)
        finally:
            self._prepared_mesh_sample = None

    def instrument(self, sample):
        mesh = self._prepared_mesh_sample
        if mesh is None:
            raise RuntimeError("Mesh diagnostic request was not prepared")
        sample["mesh_diagnostic"] = mesh
        sample["request"].update(mesh["request"])
        super().instrument(sample)
        for obj, _before in mesh["hide_entries"]:
            obj.hide_set(True, view_layer=self.window.view_layer)
        for _obj, modifier, _before in mesh["modifier_entries"]:
            modifier.show_viewport = False
        mesh["diagnostic_controls"] = self.mesh_control_state()
        mesh["diagnostic_geometry"] = self.geometry_summary()

    def restore_instrumentation(self, sample, errors):
        result = super().restore_instrumentation(sample, errors)
        mesh = sample.get("mesh_diagnostic")
        if mesh is None:
            result["mesh_controls_restored"] = False
            errors.append("Mesh diagnostic restoration record missing")
            return result
        mesh["runtime_errors_at_measurement_end"] = self.runtime_error_state()
        mesh["controls_at_measurement_end"] = self.mesh_control_state()
        # Playback is already stopped. Restore flags BEFORE the inherited
        # frame_set, raw-channel restoration and managed-coordinate proof.
        for obj, modifier, before in reversed(mesh["modifier_entries"]):
            try:
                if (self.scene.objects.get(obj.name) is not obj
                        or not any(value.as_pointer() == modifier.as_pointer() for value in obj.modifiers)):
                    raise RuntimeError("Original diagnostic object/modifier identity disappeared")
                if bool(modifier.show_viewport) != before:
                    modifier.show_viewport = before
            except BaseException:
                errors.append(traceback.format_exc())
        for obj, before in reversed(mesh["hide_entries"]):
            try:
                if self.scene.objects.get(obj.name) is not obj:
                    raise RuntimeError("Original hidden diagnostic object identity disappeared")
                if bool(obj.hide_get(view_layer=self.window.view_layer)) != before:
                    obj.hide_set(before, view_layer=self.window.view_layer)
            except BaseException:
                errors.append(traceback.format_exc())
        result["mesh_controls_restored"] = self.mesh_control_state() == mesh["before_controls"]
        return result

    def verify_artist_channels(self, sample, errors):
        result = super().verify_artist_channels(sample, errors)
        mesh = sample.get("mesh_diagnostic")
        if mesh is None:
            errors.append("Mesh restoration proof missing")
            return result
        mesh["after_controls"] = self.mesh_control_state()
        mesh["after_geometry"] = self.geometry_summary()
        mesh["runtime_errors_after_restoration"] = self.runtime_error_state()
        mesh["controls_equal_after_frame_and_channel_restore"] = mesh["after_controls"] == mesh["before_controls"]
        mesh["runtime_errors_restored_equal"] = mesh["runtime_errors_after_restoration"] == mesh["runtime_errors_before"]
        if not mesh["controls_equal_after_frame_and_channel_restore"] or not mesh["runtime_errors_restored_equal"]:
            path = OUT / ("recovery_" + sample["id"] + "_mesh_controls.json")
            write_json(path, {"schema": "x.playback-live-mesh-recovery/1", "id": sample["id"],
                              "before": mesh["before_controls"], "after": mesh["after_controls"],
                              "runtime_before": mesh["runtime_errors_before"],
                              "runtime_after": mesh["runtime_errors_after_restoration"]})
            errors.append("Mesh flags or runtime error state did not restore; recovery evidence: " + str(path))
        return result

    def base_report(self, request_id, operation):
        report = super().base_report(request_id, operation)
        report.update(schema="x.playback-live-mesh-profile/1",
                      original_profiler={"path": str(BASE_PATH), "sha256": BASE_SHA256, "bytes": len(base_raw)},
                      derived_profiler=file_pin(DERIVED_PATH),
                      mesh_scope="Reversible hide_set and allowed show_viewport only; no evaluated mesh extraction, deletion, action change or accepted-model optimization")
        if self.sample is not None and "mesh_diagnostic" in self.sample:
            report["mesh_diagnostic"] = {key: value for key, value in self.sample["mesh_diagnostic"].items()
                                         if key not in {"hide_entries", "modifier_entries"}}
        return report

    def snapshot(self, request_id):
        self.assert_context()
        report = self.base_report(request_id, "snapshot")
        report.update(completed=True, context=self.context_info(), dirty=bool(bpy.data.is_dirty),
                      disk=file_pin(ARTIST), mesh_controls=self.mesh_control_state(),
                      mesh_geometry=self.geometry_summary(), runtime_errors=self.runtime_error_state(),
                      handlers={kind: [callback_name(callback) for callback in getattr(bpy.app.handlers, kind)]
                                for kind in HANDLER_KINDS})
        self.respond(request_id, report)


if OLD_HELPER_NAME in sys.modules or HELPER_NAME in sys.modules:
    raise RuntimeError("A round3/round4 helper already exists; close it before installing another profiler")
OUT.mkdir(parents=True, exist_ok=True)
helper = types.ModuleType(HELPER_NAME)
controller = None
try:
    controller = MeshLiveProfiler()
    helper.controller = controller
    helper.close = controller.close
    controller.helper_module = helper
    sys.modules[HELPER_NAME] = helper
    bpy.app.timers.register(controller.poll_callback, first_interval=0.5)
    write_json(OUT / "live_profiler_ready.json", {
        "schema": "x.playback-live-mesh-profiler-ready/1", "ready": True, "created_utc": utc_now(),
        "pid": os.getpid(), "blender": bpy.app.version_string, "addons": controller.addon_info(),
        "installation_context": controller.install_context, "view_context": controller.ready_context,
        "artist_disk": controller.install_pin, "dirty": controller.install_dirty,
        "command_path": str(OUT / "request.json"), "helper_module": HELPER_NAME,
        "poll_seconds": 0.5, "automatic_cleanup_seconds": TTL_SECONDS,
        "preexisting_request_ignored": controller.initial_request_signature is not None,
        "initial_console_returned_to_view3d": controller.initial_area_type == "CONSOLE",
        "source": file_pin(DERIVED_PATH), "original_profiler_sha256": BASE_SHA256,
        "allowed_objects": sorted(ALLOWED_OBJECTS),
        "allowed_modifier_types": {name: sorted(types_) for name, types_ in ALLOWED_MODIFIER_TYPES.items()},
        "save": False, "refresh": False, "addon_import": False,
    })
    print("X mesh profiler ready: round4/request.json; snapshot/sample/close. No save or refresh.")
except BaseException:
    failure = traceback.format_exc()
    if controller is not None:
        controller.close("install_failed")
    write_json(OUT / "live_profiler_failure.json", {"created_utc": utc_now(), "errors": [failure], "phase": "install"})
    raise
