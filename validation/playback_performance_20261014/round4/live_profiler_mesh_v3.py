"""Mesh profiler v3: distinguish hide_set from viewport evaluation disabling.

disable_viewport_objects accepts only existing local Cosha/Shoes Mesh objects.
Object hide_viewport flags with any potential action/driver ownership or an
uncertain ownership scan are rejected. Existing v2 native callback handling,
mesh/pose/key restoration, managed-coordinate and disk proofs are retained.
"""

import hashlib
from pathlib import Path
import sys


PARENT_V2_PATH = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\live_profiler_mesh_v2.py")
PARENT_V2_SHA256 = "c362f4151a4bd45a5a1106631842cc875b7934d90b845e495e782b46949bd7a4"
V3_PATH = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\live_profiler_mesh_v3.py")
V3_HELPER_NAME = "_x_playback_live_mesh_profiler_v3_20261015"

parent_v2_raw = PARENT_V2_PATH.read_bytes()
if hashlib.sha256(parent_v2_raw).hexdigest() != PARENT_V2_SHA256:
    raise RuntimeError("Mesh profiler v2 no longer matches the accepted sample source pin")
parent_v2_prefix, parent_v2_marker, _parent_v2_installation = parent_v2_raw.decode("utf-8-sig").replace("\r\n", "\n").partition(
    "\nif any(name in sys.modules for name in (OLD_HELPER_NAME, NEW_HELPER_NAME, HELPER_NAME)):\n")
if not parent_v2_marker:
    raise RuntimeError("Pinned v2 installation boundary is missing")
exec(compile(parent_v2_prefix, str(PARENT_V2_PATH), "exec"), globals())
DERIVED_PATH = V3_PATH
HELPER_NAME = V3_HELPER_NAME


class MeshLiveProfilerV3(MeshLiveProfilerV2):
    def prepare_mesh_request(self, request):
        names = request.get("disable_viewport_objects", [])
        if (not isinstance(names, list) or len(names) > 2
                or any(not isinstance(name, str) or name not in ALLOWED_OBJECTS for name in names)
                or len(set(names)) != len(names)):
            raise ValueError("disable_viewport_objects must be a unique list drawn from Cosha and Shoes")
        entries = []
        for name in names:
            obj = self.scene.objects.get(name)
            if (obj is None or obj.type != "MESH" or obj.library or obj.override_library
                    or self.window.view_layer.objects.get(name) is not obj):
                raise ValueError("Viewport-disable target must be the existing local scene/view-layer Mesh: " + name)
            if obj.mode == "EDIT":
                raise ValueError("Leave Mesh Edit Mode before viewport-disable sampling")
            owners = self.potential_animation_owners(obj, "hide_viewport")
            if owners:
                raise ValueError("Animated or uncertain object viewport flag cannot be overridden: " + name + " " + repr(owners))
            entries.append((obj, bool(obj.hide_viewport)))
        mesh = super().prepare_mesh_request(request)
        mesh["request"]["disable_viewport_objects"] = list(names)
        mesh["viewport_entries"] = entries
        return mesh

    def instrument(self, sample):
        super().instrument(sample)
        mesh = sample["mesh_diagnostic"]
        for obj, _before in mesh["viewport_entries"]:
            obj.hide_viewport = True
        mesh["diagnostic_controls"] = self.mesh_control_state()
        mesh["diagnostic_geometry"] = self.geometry_summary()

    def restore_instrumentation(self, sample, errors):
        mesh = sample.get("mesh_diagnostic")
        if mesh is None:
            return super().restore_instrumentation(sample, errors)
        controls_at_end = self.mesh_control_state()
        runtime_at_end = self.runtime_error_state()
        # The inherited finish_sample has already stopped playback. Restore
        # all object evaluation flags before inherited frame_set and proofs.
        for obj, before in reversed(mesh.get("viewport_entries", [])):
            try:
                if self.scene.objects.get(obj.name) is not obj:
                    raise RuntimeError("Original viewport-disabled object identity disappeared")
                if bool(obj.hide_viewport) != before:
                    obj.hide_viewport = before
            except BaseException:
                errors.append(traceback.format_exc())
        result = super().restore_instrumentation(sample, errors)
        # Keep the actual measurement-end observation, before ANY flags were
        # restored, rather than the parent's intermediate restoration state.
        mesh["controls_at_measurement_end"] = controls_at_end
        mesh["runtime_errors_at_measurement_end"] = runtime_at_end
        result["object_viewport_flags_restored"] = all(
            self.scene.objects.get(obj.name) is obj and bool(obj.hide_viewport) == before
            for obj, before in mesh.get("viewport_entries", []))
        return result

    def base_report(self, request_id, operation):
        report = super().base_report(request_id, operation)
        report.update(schema="x.playback-live-mesh-profile/3",
                      accepted_parent_profiler={"path": str(PARENT_V2_PATH),
                                                "sha256": PARENT_V2_SHA256,
                                                "bytes": len(parent_v2_raw)},
                      object_viewport_scope="Existing local Cosha/Shoes hide_viewport only; animated/uncertain flags refused; original flags restored before frame_set and all inherited proofs")
        if "mesh_diagnostic" in report:
            report["mesh_diagnostic"].pop("viewport_entries", None)
        return report


if any(name in sys.modules for name in (OLD_HELPER_NAME, NEW_HELPER_NAME, V2_HELPER_NAME, HELPER_NAME)):
    raise RuntimeError("A round3/v1/v2/v3 helper exists; close it before installing v3")
OUT.mkdir(parents=True, exist_ok=True)
helper = types.ModuleType(HELPER_NAME)
controller = None
try:
    controller = MeshLiveProfilerV3()
    helper.controller = controller
    helper.close = controller.close
    controller.helper_module = helper
    sys.modules[HELPER_NAME] = helper
    bpy.app.timers.register(controller.poll_callback, first_interval=0.5)
    write_json(OUT / "live_profiler_ready.json", {
        "schema": "x.playback-live-mesh-profiler-ready/3", "ready": True, "created_utc": utc_now(),
        "pid": os.getpid(), "blender": bpy.app.version_string, "addons": controller.addon_info(),
        "installation_context": controller.install_context, "view_context": controller.ready_context,
        "artist_disk": controller.install_pin, "dirty": controller.install_dirty,
        "command_path": str(OUT / "request.json"), "helper_module": HELPER_NAME,
        "poll_seconds": 0.5, "automatic_cleanup_seconds": TTL_SECONDS,
        "preexisting_request_ignored": controller.initial_request_signature is not None,
        "initial_console_returned_to_view3d": controller.initial_area_type == "CONSOLE",
        "source": file_pin(DERIVED_PATH), "original_profiler_sha256": BASE_SHA256,
        "parent_profiler_sha256": PARENT_V2_SHA256,
        "allowed_objects": sorted(ALLOWED_OBJECTS),
        "allowed_modifier_types": {name: sorted(types_) for name, types_ in ALLOWED_MODIFIER_TYPES.items()},
        "disable_viewport_objects_supported": True,
        "save": False, "refresh": False, "addon_import": False,
    })
    print("X mesh profiler v3 ready: round4/request.json; snapshot/sample/close. No save or refresh.")
except BaseException:
    failure = traceback.format_exc()
    if controller is not None:
        controller.close("install_failed")
    write_json(OUT / "live_profiler_failure.json", {"created_utc": utc_now(), "errors": [failure], "phase": "install"})
    raise
