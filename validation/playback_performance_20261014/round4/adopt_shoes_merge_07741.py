"""Deferred single-boolean artist optimization, guarded by pinned full witnesses.

No frame set, runtime repair, deployment, artist save or file open. Prediction
changes only an owned capture reader's returned dict, never native scene data.
Failure after mutation restores only the boolean and records exact rollback.
"""
import ast
from array import array
import datetime
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import time
import traceback
import types
import uuid

ROUND = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4")
ARTIST = Path(r"D:\Blender\Projects\Character\X\X.blend")
CAPTURE_SOURCE = ROUND / "protected_refresh_07741_v3.py"
CAPTURE_SHA = "069fe18afcb46a11b6faf63dac3846281dde3c4c0fbc9da90d3c50f105a71eef"
REFRESH_RECEIPT = ROUND / "refresh_07741_20261014T184749Z_eb541cbd852e" / "refresh_receipt.json"
REFRESH_SHA = "c1e2aa7675826ceb5b1a884eb353e79891291f180748760a0e38a16edea567c8"
MERGE_SOURCE = ROUND / "probe_shoes_merge_07741.py"
MERGE_SHA = "b7da2d785422d8d46e26b77ae0bd3899f6a64dbf2919d5a7174ee255f85191f5"
MERGE_REPORT = ROUND / "native_shoes_merge_report_20261015.json"
MERGE_REPORT_SHA = "f8de14c1a26f2dcab033ac42bcb07bda19194da4e3d47110a782d2935a21098f"
PARENT_SOURCE = ROUND / "probe_native_mesh_delete_v2.py"
PARENT_SHA = "c4a3338ce6efc3220759f502e205a122d9d5dfc1f04a9d41afc8c853f20c9b39"
MANAGED_SOURCE = ROUND / "probe_shoes_removal.py"
MANAGED_SHA = "896bec93ab8df423238d115410130e4fedd6380cfbab673a820c81b9d8a2833d"
HELPER_NAME = "_x_shoes_merge_adopt_07741_20261015"
SOURCE_NAME = HELPER_NAME + "_source"
CAPTURE_NAME = HELPER_NAME + "_capture"
CAPTURE_FUNCTIONS = frozenset(("require", "utc", "pin", "identity", "exact", "digest", "id_properties", "rna", "pg",
                             "memory_guard", "load_oracle", "idle", "complete_artist_owners",
                             "context_record", "handler_witness", "animation_data", "capture", "differences"))
MERGE_FUNCTIONS = frozenset(("object_hash", "bulk_hash", "attribute_fields", "evaluated_shoes", "healthy_forearm"))
CHANGED_COMPONENT = "objects_modifiers_constraints_transforms"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def pin(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    row = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    if expected:
        require(all(row[key] == value for key, value in expected.items()), "Pin changed: " + str(path))
    return row


def pinned_tree(path, sha):
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == sha, "Source changed: " + str(path))
    return ast.parse(raw.decode("utf-8-sig"), filename=str(path))


def selected_functions(path, sha, names):
    nodes = [node for node in pinned_tree(path, sha).body if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in nodes} == set(names), "Pinned definition inventory changed")
    return ast.Module(body=nodes, type_ignores=[])


class Adoption:
    def __init__(self, window, screen, area, scene):
        self.window, self.screen, self.area, self.scene = window, screen, area, scene
        self.source_module = sys.modules.get(SOURCE_NAME)
        require(self.source_module is not None and vars(self.source_module) is globals(), "Use the owned pinned installer")
        self.capture_module = self.oracle = self.helper = None
        self.poll_callback, self.cleanup_callback = self.poll, self.cleanup
        self.closed = self.mutated = False
        self.before = self.predicted = self.mirror = self.shoe = None
        self.geometry_scope = None
        self.output = ROUND / ("adopt_shoes_merge_" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:12])
        self.output.mkdir()
        self.report = {"schema": "x.protected-shoes-merge-adoption-07741/1", "pid": os.getpid(),
                       "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source": pin(__file__),
                       "completed": False, "phase": "preflight", "errors": [], "native_mutations": [],
                       "no_artist_save": True, "no_file_open": True, "no_frame_set": True,
                       "no_manual_solver_update": True, "no_channel_repair": True, "no_deployment": True,
                       "limits": ["Private proof covers pinned clip integer frames 1–30; live proof covers current frame 21.",
                                  "One reversible Mirror setting; no Undo-stack preservation proof.",
                                  "Background timing is not a GUI FPS measurement; final artist save is a separate step."]}
        # Accepted full-content captures take about 40 seconds each. A phase
        # may contain three captures; bound each phase separately, never carry
        # elapsed preflight time into an already-mutated postproof phase.
        self.deadline = time.monotonic() + 300.0
        self.write()

    def write(self):
        path = self.output / "adoption_receipt.json"
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(self.report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temp.replace(path)

    def admit(self):
        import bpy
        require(os.getpid() == 24416 and not bpy.app.background, "Wrong foreground artist process")
        require(Path(bpy.data.filepath).resolve() == ARTIST.resolve(), "Wrong artist filepath")
        require(self.window.screen == self.screen and self.window.scene == self.scene
                and any(item == self.area for item in self.screen.areas) and self.area.type == "CONSOLE", "Owning Console context changed")
        require(self.scene.name == "Scene" and self.scene.frame_current == 21 and self.scene.frame_subframe == 0.0, "Artist frame changed")
        require(bpy.context.mode == "OBJECT" and bpy.context.view_layer.objects.active is self.scene.objects.get("Cosha")
                and not bpy.context.selected_objects, "Expected Object Mode active Cosha and empty selection")
        require(not any(window.screen and window.screen.is_animation_playing for window in bpy.context.window_manager.windows), "Pause all playback")
        require(not any(name.startswith(("_x_playback", "_x_protected_refresh", "_x_final_save")) for name in sys.modules), "Old worker remains")
        cd = sys.modules.get("character_designer")
        require(cd is not None and tuple(cd.bl_info["version"]) == (0, 77, 41), "Loaded .41 required")
        require(Path(cd.__file__).resolve().parent == Path(r"C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer").resolve(), "Wrong installed source root")
        require(not cd.ADDON_REFRESH_PENDING and not cd.ADDON_REFRESH_LAST_ERROR, "Refresh is pending or failed")
        cd._validate_registration_integrity()
        return cd

    def load_definitions(self):
        import bpy
        tree = pinned_tree(CAPTURE_SOURCE, CAPTURE_SHA)
        nodes = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign))
                 or isinstance(node, ast.FunctionDef) and node.name in CAPTURE_FUNCTIONS]
        require({node.name for node in nodes if isinstance(node, ast.FunctionDef)} == CAPTURE_FUNCTIONS, "Protection definitions changed")
        require(CAPTURE_NAME not in sys.modules and CAPTURE_NAME + "_oracle" not in sys.modules, "Protection module already owned")
        module = types.ModuleType(CAPTURE_NAME)
        module.__file__ = str(CAPTURE_SOURCE)
        sys.modules[CAPTURE_NAME] = module
        self.capture_module = module
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CAPTURE_SOURCE), "exec"), module.__dict__)
        module.HELPER_NAME = CAPTURE_NAME
        self.oracle = module.load_oracle()
        # Load only the hash functions; neither probe entry point nor its import
        # chain is executed. Verify the original parent's managed-helper pin.
        parent = pinned_tree(PARENT_SOURCE, PARENT_SHA)
        parent_pins = [node.value.value for node in parent.body if isinstance(node, ast.Assign)
                       and any(isinstance(item, ast.Name) and item.id == "PARENT_PROBE_SHA256" for item in node.targets)
                       and isinstance(node.value, ast.Constant)]
        require(parent_pins == [MANAGED_SHA], "Managed definition chain changed")
        scope = {"__name__": HELPER_NAME + "_hash_definitions", "bpy": bpy, "array": array,
                 "hashlib": hashlib, "json": json, "struct": struct}
        exec(compile(selected_functions(MANAGED_SOURCE, MANAGED_SHA, {"managed_summary"}), str(MANAGED_SOURCE), "exec"), scope)
        exec(compile(selected_functions(MERGE_SOURCE, MERGE_SHA, MERGE_FUNCTIONS), str(MERGE_SOURCE), "exec"), scope)
        self.geometry_scope = scope
        self.report["protection_sources"] = {"capture": pin(CAPTURE_SOURCE), "oracle": module.pin(module.ORACLE, {"sha256": module.ORACLE_SHA}),
                                             "geometry": pin(MERGE_SOURCE), "parent": pin(PARENT_SOURCE), "managed_definition": pin(MANAGED_SOURCE)}

    def live_output(self):
        runtime = sys.modules["character_designer.forearm_twist"]
        target = sys.modules["character_designer.animation_worklist_target"]
        inventory = sys.modules["character_designer.forearm_original_inventory"]
        self.capture_module.complete_artist_owners(self.scene)
        rig = self.scene.objects["CoshaRig"]
        ft = self.geometry_scope["healthy_forearm"](runtime, target, inventory, self.scene, rig, full_proof=True)
        geom = self.geometry_scope["evaluated_shoes"](self.shoe)
        obj = self.scene.objects["Cosha"]
        require(obj.as_pointer() in runtime._CACHE, "Published input cache missing")
        cached = runtime._OUTPUT_CACHE.get(obj.as_pointer())
        require(cached is not None, "Published output cache missing")
        actual = []
        for side, record in runtime._records(obj).items():
            key = runtime._managed_key(obj, side, record, required=True, repair_name=False)
            values = array("f", [0.0]) * (len(key.data) * 3)
            key.data.foreach_get("co", values)
            actual.append(values.tobytes())
        require(actual == cached, "Managed coordinates do not match last published output; no repair")
        return {"geometry_sha256": geom["sha256"], "forearm_and_pose_sha256": ft, "published_output_exact": True}

    def compare_full(self, expected, actual):
        source = self.capture_module
        changes = source.differences(expected, actual)
        require(not changes and set(actual["components"]) == set(expected["components"]), "Protected components changed: " + repr(changes))
        require(source.exact(expected["context"]) == source.exact(actual["context"]), "Protected context changed")
        require(actual["dirty"] == expected["dirty"] and actual["counts"] == expected["counts"]
                and actual["managed"] == expected["managed"], "Protected dirty/counts/managed witness changed")

    def prepare(self, cd):
        require(pin(REFRESH_RECEIPT)["sha256"] == REFRESH_SHA, "Accepted refresh receipt changed")
        require(pin(MERGE_REPORT)["sha256"] == MERGE_REPORT_SHA and pin(MERGE_REPORT)["bytes"] == 33154, "Private differential receipt changed")
        refresh = json.loads(REFRESH_RECEIPT.read_text(encoding="utf-8"))
        evidence = json.loads(MERGE_REPORT.read_text(encoding="utf-8"))
        require(refresh["completed"] and not refresh["errors"] and refresh["loaded_version"] == [0, 77, 41]
                and refresh["changed_components"] == [] and refresh["savecopy_result"] == ["FINISHED"], "Refresh proof incomplete")
        require(evidence["completed"] and evidence["all_30_geometry_and_forearm_exact"] and evidence["candidate_eligible"]
                and evidence["source_version"] == [0, 77, 41], "Private differential did not pass")
        require(len(evidence["geometry_frame_checks"]) == 30 and {row["frame"] for row in evidence["geometry_frame_checks"]} == set(range(1, 31)), "Private frame coverage changed")
        for row in evidence["geometry_frame_checks"]:
            require(row["geometry_exact"] and row["forearm_and_pose_exact"] and row["healthy_inventory_and_rest"], "Private proof failed")
        for source_pin in evidence["sources"]:
            pin(source_pin["path"], source_pin)
        self.expected_frame = next(row for row in evidence["geometry_frame_checks"] if row["frame"] == 21)
        self.report["evidence"] = {"refresh_receipt": pin(REFRESH_RECEIPT), "merge_report": pin(MERGE_REPORT),
                                   "protected_SaveCopy": pin(refresh["savecopy"]["path"], refresh["savecopy"])}
        require(refresh["savecopy"]["sha256"] == "ff7b9caa4e87fed74751fdac9222775ea4f184f8e912e432a57d0601125d066a", "Wrong protected recovery copy")
        self.report["artist_before"] = pin(ARTIST)
        require(self.report["artist_before"] == refresh["final_artist_disk"], "Artist file changed since refresh")
        self.load_definitions()
        source = self.capture_module
        source.idle(cd)
        self.report["handlers_before"] = source.handler_witness()
        require(self.report["handlers_before"] == refresh["handlers_after"], "Callbacks changed since accepted refresh")
        self.shoe = self.scene.objects["Shoes"]
        modifiers = [modifier for modifier in self.shoe.modifiers if modifier.type == "MIRROR"]
        require(len(modifiers) == 1 and modifiers[0].show_viewport and modifiers[0].use_mirror_merge, "Expected unique active merge-enabled Mirror")
        self.mirror = modifiers[0]
        self.report["modifier"] = {"object": source.identity(self.shoe), "name": self.mirror.name, "type": self.mirror.type,
                                   "pointer": self.mirror.as_pointer(), "before_use_mirror_merge": True}
        self.before, _ = source.capture(cd, self.oracle)
        self.report["before"] = self.before
        changed = [name for name in source.differences(refresh["after"], self.before) if name != "context"]
        require(not changed and set(self.before["components"]) == set(refresh["after"]["components"]), "Live assets differ from accepted refresh: " + repr(changed))
        require(self.before["dirty"] is True, "Expected accepted unsaved artist state before flag change")
        self.report["output_before"] = self.live_output()
        require(self.report["output_before"]["geometry_sha256"] == self.expected_frame["baseline_geometry_sha256"]
                and self.report["output_before"]["forearm_and_pose_sha256"] == self.expected_frame["baseline_forearm_sha256"], "Live frame21 differs from private exact baseline")
        original_reader = source.rna
        hits = []
        target_pointer = self.mirror.as_pointer()
        def predicted_reader(value, **kwargs):
            result = original_reader(value, **kwargs)
            if value.as_pointer() == target_pointer:
                require(result.get("use_mirror_merge") is True, "Prediction baseline flag changed")
                result = dict(result)
                result["use_mirror_merge"] = False
                hits.append(target_pointer)
            return result
        source.rna = predicted_reader
        try:
            self.predicted, _ = source.capture(cd, self.oracle)
        finally:
            source.rna = original_reader
        require(hits == [target_pointer] and self.mirror.use_mirror_merge, "Prediction failed exact pointer/read-only guard")
        require(source.differences(self.before, self.predicted) == [CHANGED_COMPONENT], "Prediction changes more than the authorized modifier component")
        require(source.exact(self.before["context"]) == source.exact(self.predicted["context"])
                and self.before["dirty"] == self.predicted["dirty"] and self.before["managed"] == self.predicted["managed"]
                and self.before["counts"] == self.predicted["counts"], "Prediction changed context/dirty/managed/counts")
        self.report["predicted"] = self.predicted
        self.report["prediction"] = {"only_owned_reader_wrapped": True, "native_mutation": False, "target_hits": 1,
                                     "reader_restored_identity": source.rna is original_reader, "changed_components": [CHANGED_COMPONENT]}
        # The modifier component aggregates many properties. A third actual
        # capture after restoring the reader proves that prediction did not
        # include another simultaneous property change in that same component.
        actual, _ = source.capture(cd, self.oracle)
        self.compare_full(self.before, actual)
        require(self.live_output() == self.report["output_before"], "Native output changed during read-only prediction")
        source.idle(cd)
        require(source.handler_witness() == self.report["handlers_before"], "Callback identity changed during prediction")
        self.admit()
        require(time.monotonic() < self.deadline, "Preflight expired before native mutation")
        self.deadline = time.monotonic() + 300.0
        self.mirror.use_mirror_merge = False
        self.mutated = True
        require(self.mirror.use_mirror_merge is False, "Native flag setter did not take effect")
        self.report["native_mutations"].append({"object": "Shoes", "modifier": self.mirror.name,
                                               "property": "use_mirror_merge", "before": True, "after": False})
        self.report["phase"] = "waiting_natural_evaluation"
        self.write()

    def postproof(self, cd):
        import bpy
        source = self.capture_module
        source.idle(cd)
        require(self.mirror.use_mirror_merge is False, "Candidate boolean changed")
        # Update the existing native graph at its current frame. Never invoke
        # the add-on's update_runtime or write a managed output directly.
        bpy.context.view_layer.update()
        self.report["native_view_layer_update"] = True
        source.idle(cd)
        self.report["output_after"] = self.live_output()
        require(self.report["output_after"] == self.report["output_before"], "Candidate changed evaluated Shoes or current Forearm/pose")
        after, _ = source.capture(cd, self.oracle)
        self.report["after"] = after
        self.compare_full(self.predicted, after)
        self.report["handlers_after"] = source.handler_witness()
        require(self.report["handlers_after"] == self.report["handlers_before"], "Callbacks changed during adoption")
        source.idle(cd)
        self.report["artist_after"] = pin(ARTIST)
        require(self.report["artist_after"] == self.report["artist_before"], "Artist file changed during no-save adoption")
        self.report.update(only_expected_component_changed=True, all_12_predicted_components_exact=True,
                           context_and_dirty_exact=True, live_frame21_output_exact=True,
                           artist_disk_unchanged=True, adopted_use_mirror_merge=False)

    def rollback(self, cd):
        import bpy
        row = {"attempted": self.mutated, "only_boolean_restore": True, "proof_passed": False}
        self.report["rollback"] = row
        if not self.mutated:
            row["proof_passed"] = True
            return
        try:
            require(self.scene.objects.get("Shoes") is self.shoe and self.mirror.as_pointer() == self.report["modifier"]["pointer"], "Rollback target ownership changed")
            require(self.mirror.use_mirror_merge is False, "Rollback value differs from our mutation; do not overwrite")
            self.mirror.use_mirror_merge = True
            bpy.context.view_layer.update()
            row["restored_use_mirror_merge"] = bool(self.mirror.use_mirror_merge)
            row["outputs"] = self.live_output()
            actual, _ = self.capture_module.capture(cd, self.oracle)
            row["full_witness"] = actual
            self.compare_full(self.before, actual)
            require(row["outputs"] == self.report["output_before"], "Rollback output mismatch")
            require(self.capture_module.handler_witness() == self.report["handlers_before"], "Rollback callbacks changed")
            require(pin(ARTIST) == self.report["artist_before"], "Rollback artist file changed")
            row["proof_passed"] = True
        except BaseException:
            row["error"] = traceback.format_exc()
            self.report["errors"].append(row["error"])

    def poll(self):
        import bpy
        cd = None
        try:
            require(time.monotonic() < self.deadline, "Deferred adoption timed out")
            with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area):
                cd = self.admit()
                if self.report["phase"] == "preflight":
                    self.prepare(cd)
                    return 0.1
                require(self.report["phase"] == "waiting_natural_evaluation", "Unknown adoption phase")
                self.postproof(cd)
            self.finish()
        except BaseException:
            self.report["errors"].append(traceback.format_exc())
            if self.mutated:
                try:
                    cd = cd or sys.modules.get("character_designer")
                    require(cd is not None, "Cannot prove rollback without loaded runtime")
                    with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area):
                        self.rollback(cd)
                except BaseException:
                    self.report["errors"].append(traceback.format_exc())
                    self.report["rollback_admission_failed"] = True
            self.finish(failed=True)
        return None

    def finish(self, failed=False):
        import bpy
        self.closed = True
        self.report.update(completed=not failed, phase="failed" if failed else "completed",
                           finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           helper_cleanup="Next idle event-loop turn")
        self.write()
        bpy.app.timers.register(self.cleanup_callback, first_interval=0.01)

    def cleanup(self):
        import bpy
        try:
            require(self.closed and not bpy.app.timers.is_registered(self.poll_callback), "Worker timer still active")
            owned = ((CAPTURE_NAME + "_oracle", self.oracle), (CAPTURE_NAME, self.capture_module),
                     (HELPER_NAME, self.helper), (SOURCE_NAME, self.source_module))
            require(all(module is None or sys.modules.get(name) is module for name, module in owned), "Cleanup ownership changed; retain helpers")
            removed = []
            for name, module in owned:
                if module is not None and sys.modules.get(name) is module:
                    del sys.modules[name]
                    removed.append(name)
            self.report["helper_cleanup"] = {"poll_timer_gone": True, "owned_modules_removed": removed,
                                             "cleanup_callback_returns_none": True}
        except BaseException:
            self.report["completed"] = False
            self.report["errors"].append(traceback.format_exc())
        self.write()
        print(json.dumps({"completed": self.report["completed"], "receipt": str(self.output / "adoption_receipt.json")}, ensure_ascii=False))
        return None


def begin(window, screen, area, scene):
    import bpy
    require(HELPER_NAME not in sys.modules, "Adoption worker already owned")
    worker = Adoption(window, screen, area, scene)
    helper = types.ModuleType(HELPER_NAME)
    helper.controller = worker
    worker.helper = helper
    sys.modules[HELPER_NAME] = helper
    bpy.app.timers.register(worker.poll_callback, first_interval=0.25)
    return worker
