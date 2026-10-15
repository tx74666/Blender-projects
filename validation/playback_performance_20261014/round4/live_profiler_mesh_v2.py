"""Mesh profiler v2: preserve native callback arity and stop-result evidence.

The failed v1 run and both source files remain pinned and unchanged. This
loads only their definitions, repairs the temporary instrumentation, and
requires all inherited flag, raw-channel, managed-coordinate and disk proofs.
"""

import ast
import hashlib
import inspect
from pathlib import Path
import sys


V1_PATH = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\live_profiler_mesh.py")
V1_SHA256 = "df397c6ead3fdad96bbb357298721fd303f1b324493e0c835587ec54ac1e4fbd"
V2_PATH = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\live_profiler_mesh_v2.py")
V2_HELPER_NAME = "_x_playback_live_mesh_profiler_v2_20261015"

v1_raw = V1_PATH.read_bytes()
if hashlib.sha256(v1_raw).hexdigest() != V1_SHA256:
    raise RuntimeError("Mesh profiler v1 no longer matches the failed-run source pin")
v1_prefix, v1_marker, _v1_installation = v1_raw.decode("utf-8-sig").replace("\r\n", "\n").partition(
    "\nif OLD_HELPER_NAME in sys.modules or HELPER_NAME in sys.modules:\n")
if not v1_marker:
    raise RuntimeError("Pinned v1 installation boundary is missing")
exec(compile(v1_prefix, str(V1_PATH), "exec"), globals())
DERIVED_PATH = V2_PATH
HELPER_NAME = V2_HELPER_NAME

# Only alter the inherited stop-result check, preserving the complete original
# finish_sample body and the derived mesh restoration ordering.
original_finish = next(node for node in base_tree.body[-1].body
                       if isinstance(node, ast.FunctionDef) and node.name == "finish_sample")
stop_check_count = 0


class StopResultWitness(ast.NodeTransformer):
    def visit_If(self, node):
        global stop_check_count
        self.generic_visit(node)
        if ast.unparse(node.test) == "'FINISHED' not in result":
            if len(node.body) != 1 or "animation_cancel:" not in ast.unparse(node.body[0]):
                return node
            stop_check_count += 1
            replacement = ast.parse('''
sample["animation_cancel_result"] = sorted(result)
sample["animation_cancel_stopped"] = not self.screen.is_animation_playing
if (not sample["animation_cancel_stopped"]
        or ("FINISHED" not in result and "PASS_THROUGH" not in result)):
    errors.append("animation_cancel: " + repr(result) + "; playing=" + repr(self.screen.is_animation_playing))
''').body
            return [ast.copy_location(value, node) for value in replacement]
        return node


original_finish = StopResultWitness().visit(original_finish)
if stop_check_count != 1:
    raise RuntimeError("Expected exactly one pinned animation_cancel stop-result check")
finish_tree = ast.fix_missing_locations(ast.Module(body=[original_finish], type_ignores=[]))
finish_namespace = {}
exec(compile(finish_tree, str(BASE_PATH) + " [v2 stop witness]", "exec"), globals(), finish_namespace)
LiveProfiler.finish_sample = finish_namespace["finish_sample"]


class MeshLiveProfilerV2(MeshLiveProfiler):
    def timed(self, callback, key, sample):
        native_callback = key.startswith("handler:") or key.startswith("panel:")
        arity = None
        if native_callback:
            code = getattr(callback, "__code__", None)
            if code is not None:
                arity = code.co_argcount - int(inspect.ismethod(callback) and callback.__self__ is not None)
            else:
                signature = inspect.signature(callback, follow_wrapped=False)
                arity = sum(parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
                            for parameter in signature.parameters.values())
            if not 0 <= arity <= 6:
                raise RuntimeError("Unsupported native callback positional arity: " + key + " " + repr(arity))
        sample.setdefault("callback_arities", {})[key] = arity
        sample.setdefault("callback_exceptions", {})

        def invoke(*args, **kwargs):
            measuring = sample["measuring"]
            began = time.perf_counter_ns() if measuring else None
            failed = False
            try:
                return callback(*args, **kwargs)
            except BaseException:
                failed = True
                failures = sample["callback_exceptions"]
                if key not in failures:
                    failures[key] = {"count": 0, "first_traceback": traceback.format_exc(),
                                     "first_phase": sample.get("phase"),
                                     "callback": callback_name(callback), "positional_arity": arity}
                failures[key]["count"] += 1
                raise
            finally:
                if measuring:
                    elapsed = time.perf_counter_ns() - began
                    stat = sample["stats"].setdefault(key, [0, 0, 0, 0])
                    stat[0] += 1
                    stat[1] += elapsed
                    stat[2] = max(stat[2], elapsed)
                    stat[3] += int(failed)

        # Blender native callbacks inspect the real positional count. A generic
        # *args wrapper has co_argcount=0 even when functools.wraps preserves
        # inspect.signature, which can change native dispatch to the callback.
        if arity is None or arity == 0:
            def wrapped(*args, **kwargs):
                return invoke(*args, **kwargs)
        elif arity == 1:
            def wrapped(a0, *args, **kwargs):
                return invoke(a0, *args, **kwargs)
        elif arity == 2:
            def wrapped(a0, a1, *args, **kwargs):
                return invoke(a0, a1, *args, **kwargs)
        elif arity == 3:
            def wrapped(a0, a1, a2, *args, **kwargs):
                return invoke(a0, a1, a2, *args, **kwargs)
        elif arity == 4:
            def wrapped(a0, a1, a2, a3, *args, **kwargs):
                return invoke(a0, a1, a2, a3, *args, **kwargs)
        elif arity == 5:
            def wrapped(a0, a1, a2, a3, a4, *args, **kwargs):
                return invoke(a0, a1, a2, a3, a4, *args, **kwargs)
        else:
            def wrapped(a0, a1, a2, a3, a4, a5, *args, **kwargs):
                return invoke(a0, a1, a2, a3, a4, a5, *args, **kwargs)
        wrapped = functools.wraps(callback)(wrapped)
        if arity is not None and wrapped.__code__.co_argcount != arity:
            raise RuntimeError("Native wrapper did not retain positional count: " + key)
        return wrapped

    def verify_artist_channels(self, sample, errors):
        result = super().verify_artist_channels(sample, errors)
        for key, failure in sample.get("callback_exceptions", {}).items():
            errors.append("Native/function callback raised " + str(failure["count"]) + " time(s): "
                          + key + "\n" + failure["first_traceback"])
        return result

    def base_report(self, request_id, operation):
        report = super().base_report(request_id, operation)
        report.update(schema="x.playback-live-mesh-profile/2",
                      parent_profiler={"path": str(V1_PATH), "sha256": V1_SHA256, "bytes": len(v1_raw)},
                      callback_signature_scope="Native handler/panel real positional arity retained; ordinary function wrappers retain forwarding",
                      stop_result_scope="PASS_THROUGH accepted only with immediate screen.is_animation_playing=false witness; all original restoration proofs remain required")
        if self.sample is not None:
            report.update(callback_arities=self.sample.get("callback_arities", {}),
                          callback_exceptions=self.sample.get("callback_exceptions", {}),
                          animation_cancel={"attempted": "animation_cancel_result" in self.sample,
                                            "native_result": self.sample.get("animation_cancel_result"),
                                            "playing_false_witness": self.sample.get("animation_cancel_stopped"),
                                            "playing_after_restoration": bool(self.screen.is_animation_playing)})
        return report


if any(name in sys.modules for name in (OLD_HELPER_NAME, NEW_HELPER_NAME, HELPER_NAME)):
    raise RuntimeError("A round3/v1/v2 helper exists; close it before installing v2")
OUT.mkdir(parents=True, exist_ok=True)
helper = types.ModuleType(HELPER_NAME)
controller = None
try:
    controller = MeshLiveProfilerV2()
    helper.controller = controller
    helper.close = controller.close
    controller.helper_module = helper
    sys.modules[HELPER_NAME] = helper
    bpy.app.timers.register(controller.poll_callback, first_interval=0.5)
    write_json(OUT / "live_profiler_ready.json", {
        "schema": "x.playback-live-mesh-profiler-ready/2", "ready": True, "created_utc": utc_now(),
        "pid": os.getpid(), "blender": bpy.app.version_string, "addons": controller.addon_info(),
        "installation_context": controller.install_context, "view_context": controller.ready_context,
        "artist_disk": controller.install_pin, "dirty": controller.install_dirty,
        "command_path": str(OUT / "request.json"), "helper_module": HELPER_NAME,
        "poll_seconds": 0.5, "automatic_cleanup_seconds": TTL_SECONDS,
        "preexisting_request_ignored": controller.initial_request_signature is not None,
        "initial_console_returned_to_view3d": controller.initial_area_type == "CONSOLE",
        "source": file_pin(DERIVED_PATH), "original_profiler_sha256": BASE_SHA256,
        "parent_profiler_sha256": V1_SHA256,
        "allowed_objects": sorted(ALLOWED_OBJECTS),
        "allowed_modifier_types": {name: sorted(types_) for name, types_ in ALLOWED_MODIFIER_TYPES.items()},
        "save": False, "refresh": False, "addon_import": False,
    })
    print("X mesh profiler v2 ready: round4/request.json; snapshot/sample/close. No save or refresh.")
except BaseException:
    failure = traceback.format_exc()
    if controller is not None:
        controller.close("install_failed")
    write_json(OUT / "live_profiler_failure.json", {"created_utc": utc_now(), "errors": [failure], "phase": "install"})
    raise
