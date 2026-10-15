"""Private native Delete diagnosis matching the artist's clarified sequence.

Reopen the fixed .40 saved copy for complete, Delete Cosha, Delete Cosha then
Shoes, and Delete Shoes alone. Never access the live artist scene or save.
Removing the only calibrated mesh is distinguished from validation failure.
"""

import hashlib
from pathlib import Path


PARENT_PROBE = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\probe_shoes_removal.py")
PARENT_PROBE_SHA256 = "896bec93ab8df423238d115410130e4fedd6380cfbab673a820c81b9d8a2833d"
parent_probe_raw = PARENT_PROBE.read_bytes()
if hashlib.sha256(parent_probe_raw).hexdigest() != PARENT_PROBE_SHA256:
    raise RuntimeError("Original prepared shoes probe changed")
parent_prefix, parent_marker, _parent_main = parent_probe_raw.decode("utf-8-sig").replace("\r\n", "\n").partition(
    '\nif __name__ == "__main__":\n')
if not parent_marker:
    raise RuntimeError("Pinned original probe main boundary is missing")
exec(compile(parent_prefix, str(PARENT_PROBE), "exec"), globals())

DELETE_CASES = (("complete", ()), ("delete_cosha", ("Cosha",)),
                ("delete_cosha_then_shoes", ("Cosha", "Shoes")),
                ("delete_shoes", ("Shoes",)))


def mesh_id_names(obj):
    names = {obj.name, obj.data.name}
    if obj.animation_data and obj.animation_data.action:
        names.add(obj.animation_data.action.name)
    keys = obj.data.shape_keys
    if keys is not None:
        names.add(keys.name)
        if keys.animation_data and keys.animation_data.action:
            names.add(keys.animation_data.action.name)
    return names


def tracked_references(target, rig, names):
    result = reference_summary(target, rig, names)
    result["related_mesh_and_key_references"] = result.pop("shoe_related_references", [])
    result["tracked_mesh_object_data_key_action_names"] = sorted(names)
    return result


def route_state(runtime, scene):
    managed = managed_summary(runtime, scene)
    present = set(managed)
    errors = dict(runtime._ERRORS)
    return {"calibrated_mesh_count": len(present), "calibrated_mesh_names": sorted(present),
            "no_calibrated_mesh_in_scene": not present,
            "errors_for_present_calibrated_meshes": {key: value for key, value in errors.items() if key in present},
            "errors_for_other_or_removed_meshes": {key: value for key, value in errors.items() if key not in present},
            "managed": managed}


def native_delete_mesh(scene, obj):
    name, data_name = obj.name, obj.data.name
    key_name = obj.data.shape_keys.name if obj.data.shape_keys else None
    active = bpy.context.view_layer.objects.active
    if active and active.mode != "OBJECT":
        mode_result = bpy.ops.object.mode_set(mode="OBJECT")
        if "FINISHED" not in mode_result:
            raise RuntimeError("Private Object Mode transition failed: " + repr(mode_result))
    for selected in bpy.context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    assert {selected.name for selected in bpy.context.selected_objects} == {name}
    result = bpy.ops.object.delete(use_global=False)
    if "FINISHED" not in result:
        raise RuntimeError("Private native Delete failed: " + name + " " + repr(result))
    return {"object": name, "operation": "bpy.ops.object.delete(use_global=False)",
            "native_result": sorted(result), "object_still_in_scene": scene.objects.get(name) is not None,
            "object_still_in_bpy_data": bpy.data.objects.get(name) is not None,
            "mesh_data_still_in_bpy_data": bpy.data.meshes.get(data_name) is not None,
            "key_data_still_in_bpy_data": bpy.data.shape_keys.get(key_name) is not None if key_name else None,
            "no_live_scene_access": True}


class RouteTiming:
    def __init__(self, runtime, inventory, target):
        self.saved = []
        self.reset()
        for module, names in ((runtime, ("update_runtime", "_calculate_object", "_prepare_runtime_records", "_calculate_records")),
                              (inventory, ("validate",)), (target, ("control_rest_view", "_load_rest_record", "_prove_motion_data"))):
            for name in names:
                original = getattr(module, name)
                key = module.__name__ + "." + name
                wrapped = self.wrap(original, key)
                self.saved.append((module, name, original, wrapped))
                setattr(module, name, wrapped)

    def wrap(self, original, key):
        @functools.wraps(original)
        def measured(*args, **kwargs):
            began = time.perf_counter_ns()
            try:
                return original(*args, **kwargs)
            finally:
                self.calls[key] += 1
                self.nanoseconds[key] += time.perf_counter_ns() - began
        return measured

    def reset(self):
        self.calls, self.nanoseconds = Counter(), Counter()

    def summary(self):
        return {key: {"calls": count, "inclusive_ms": self.nanoseconds[key] / 1_000_000,
                      "mean_call_ms": self.nanoseconds[key] / count / 1_000_000}
                for key, count in self.calls.items()}

    def restore(self):
        for module, name, original, wrapped in reversed(self.saved):
            if getattr(module, name) is not wrapped:
                raise RuntimeError("Private function timing wrapper ownership changed: " + name)
            setattr(module, name, original)


def main(args, report):
    assert bpy.app.background, "Only a private background process is permitted"
    input_path, artist_path = Path(args.input).resolve(), Path(args.artist).resolve()
    assert input_path != artist_path, "Never open the artist file for this probe"
    input_before, artist_before = pin(input_path), pin(artist_path)
    assert input_before["sha256"] == EXPECTED_INPUT_SHA256 and input_before["bytes"] == EXPECTED_INPUT_BYTES
    report.update(input_before=input_before, artist_before=artist_before,
                  input_matches_artist_at_start=input_before["sha256"] == artist_before["sha256"],
                  script=pin(__file__), parent_probe={"path": str(PARENT_PROBE), "sha256": PARENT_PROBE_SHA256},
                  blender=bpy.app.version_string, frame_sequence=list(FRAMES), deletion_method="native_operator_default")
    sys.path.insert(0, str(Path(args.addons).resolve()))
    import character_designer as addon
    from character_designer import forearm_twist as runtime, animation_worklist_target as target
    from character_designer import forearm_original_inventory as inventory, limb_ik
    assert Path(addon.__file__).resolve().parent == Path(args.addons).resolve() / "character_designer"
    assert tuple(addon.bl_info["version"]) == (0, 77, 40), "Use installed .40 before candidate deployment"
    report.update(source_version=list(addon.bl_info["version"]),
                  sources=[pin(module.__file__) for module in (addon, runtime, target, inventory, limb_ik)],
                  source_metadata_changed=False)
    addon.register()
    report["cases"] = []
    for label, delete_order in DELETE_CASES:
        opened = bpy.ops.wm.open_mainfile(filepath=str(input_path))
        assert "FINISHED" in opened and Path(bpy.data.filepath).resolve() == input_path
        scene = bpy.context.scene
        rig, cosha, shoe = (scene.objects.get(name) for name in ("CoshaRig", "Cosha", "Shoes"))
        assert rig and cosha and shoe and cosha.type == shoe.type == "MESH"
        related_names = mesh_id_names(cosha) | mesh_id_names(shoe)
        row = {"label": label, "delete_order": list(delete_order), "scene": scene.name,
               "references_before": tracked_references(target, rig, related_names),
               "control_rest_before": proof_result(lambda: target.control_rest_view(rig)),
               "inventory_before": proof_result(lambda: inventory.validate(rig)),
               "route_before": route_state(runtime, scene), "managed_before": managed_summary(runtime, scene, coordinates=True)}
        assert not runtime._ERRORS and row["inventory_before"]["passed"] and row["control_rest_before"]["passed"], "Complete input must begin with valid inventory and Rest proof"
        baseline_sides = row["managed_before"].get("Cosha", [])
        assert row["route_before"]["calibrated_mesh_names"] == ["Cosha"], "Complete input requires exactly the Cosha owner"
        assert (len(baseline_sides) == 2 and {entry["side"] for entry in baseline_sides} == {"L", "R"}
                and all(entry["support_vertices"] == 191 and entry["enabled"] is True
                        and entry["key"] is not None and entry["mute"] is False and entry["value"] == 1.0
                        for entry in baseline_sides)), "Complete input requires enabled healthy L/R 191-vertex outputs"
        row["deletions"] = []
        for name in delete_order:
            obj = scene.objects.get(name)
            assert obj is not None and obj.type == "MESH"
            row["deletions"].append(native_delete_mesh(scene, obj))
        row.update(references_after_mutation=tracked_references(target, rig, related_names),
                   control_rest_after_mutation=proof_result(lambda: target.control_rest_view(rig)),
                   inventory_after_mutation=proof_result(lambda: inventory.validate(rig)),
                   route_after_mutation=route_state(runtime, scene))
        timing = RouteTiming(runtime, inventory, target)
        try:
            for frame in (1, 3):
                scene.frame_set(frame)
                bpy.context.view_layer.update()
            frames = []
            for frame in FRAMES:
                timing.reset()
                began = time.perf_counter_ns()
                scene.frame_set(frame)
                frame_set_done = time.perf_counter_ns()
                bpy.context.view_layer.update()
                done = time.perf_counter_ns()
                functions = timing.summary()
                runtime_row = functions.get(runtime.__name__ + ".update_runtime", {})
                frames.append({"frame": frame, "frame_set_ms": (frame_set_done - began) / 1_000_000,
                               "view_layer_update_ms": (done - frame_set_done) / 1_000_000,
                               "total_evaluation_ms": (done - began) / 1_000_000,
                               "runtime_calls": runtime_row.get("calls", 0),
                               "runtime_inclusive_ms": runtime_row.get("inclusive_ms", 0),
                               "functions": functions, "route": route_state(runtime, scene),
                               "errors": dict(runtime._ERRORS)})
            row.update(frames=frames, median_total_evaluation_ms=statistics.median(value["total_evaluation_ms"] for value in frames),
                       median_runtime_inclusive_ms=statistics.median(value["runtime_inclusive_ms"] for value in frames),
                       errors_after=dict(runtime._ERRORS), route_after=route_state(runtime, scene),
                       managed_after=managed_summary(runtime, scene, coordinates=True),
                       performance_acceptance=False, no_scene_save=True)
            report["cases"].append(row)
            print("CASE", label, round(row["median_total_evaluation_ms"], 3),
                  "calibrated", row["route_after"]["calibrated_mesh_count"], row["errors_after"], flush=True)
        finally:
            timing.restore()
    report["input_after"], report["artist_after"] = pin(input_path), pin(artist_path)
    assert report["input_after"] == input_before and report["artist_after"] == artist_before
    report.update(input_disk_unchanged=True, artist_disk_unchanged=True, no_save_operation=True,
                  no_live_artist_access=True, no_deploy=True, no_refresh=True,
                  limits=["Private saved-copy background native Delete/frame evaluation; not GUI FPS or current unsaved artist state.",
                          "Each case reopens the saved copy; live Ctrl Z behavior is not tested or represented as passed.",
                          "Removing the only calibrated mesh eliminates its workload and outputs; this is distinct from invalid provenance or paused correction.",
                          "Only Character Designer registered; external GUI handlers, drawing and shader costs are absent.",
                          "Failed/muted/removed correction is diagnostic, not a valid optimization or whole-model equivalence.",
                          "Nested function times overlap and are inside total evaluation; do not add them.",
                          "Eight hot frames after two warm frames per case under shared load; not final paired acceptance."])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    report = {"schema": "x.native-mesh-delete-private-probe/2", "completed": False,
              "pid": os.getpid(), "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "model_and_reasoning_effort": "unrecorded"}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
