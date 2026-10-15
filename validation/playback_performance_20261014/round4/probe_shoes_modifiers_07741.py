"""Prepared only: private .41 Shoes modifier cost after native Delete Cosha.

Run with --background --factory-startup -t 1. Four fresh-copy cases keep Shoes
intact, disable Mirror, disable Armature, or disable both. No scene save or
artist access; no GUI-FPS or usable-model optimization claim.
"""
import hashlib
from pathlib import Path

PARENT = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\probe_native_mesh_delete_v2.py")
PARENT_SHA = "c4a3338ce6efc3220759f502e205a122d9d5dfc1f04a9d41afc8c853f20c9b39"
raw = PARENT.read_bytes()
if hashlib.sha256(raw).hexdigest() != PARENT_SHA:
    raise RuntimeError("Prepared native Delete probe pin changed")
prefix, marker, _main = raw.decode("utf-8-sig").replace("\r\n", "\n").partition('\nif __name__ == "__main__":\n')
if not marker:
    raise RuntimeError("Pinned helper definition boundary missing")
exec(compile(prefix, str(PARENT), "exec"), globals())
MODIFIER_CASES = (("shoes_intact", ()), ("mirror_off", ("MIRROR",)),
                  ("armature_off", ("ARMATURE",)), ("mirror_and_armature_off", ("MIRROR", "ARMATURE")))


def main(args, report):
    assert bpy.app.background, "Private background process only"
    native_args = sys.argv[:sys.argv.index("--")]
    assert any(value in ("-t", "--threads") and native_args[index + 1] == "1"
               for index, value in enumerate(native_args[:-1])), "Explicit native -t 1 is required"
    input_path, artist_path = Path(args.input).resolve(), Path(args.artist).resolve()
    assert input_path != artist_path
    report["input_before"], report["artist_before"] = pin(input_path), pin(artist_path)
    assert report["input_before"]["sha256"] == EXPECTED_INPUT_SHA256 and report["input_before"]["bytes"] == EXPECTED_INPUT_BYTES
    sys.path.insert(0, str(Path(args.addons).resolve()))
    import character_designer as addon
    from character_designer import forearm_twist as runtime, animation_worklist_target as target
    from character_designer import forearm_original_inventory as inventory
    assert Path(addon.__file__).resolve().parent == Path(args.addons).resolve() / "character_designer"
    assert tuple(addon.bl_info["version"]) == (0, 77, 41), "Use the actual deployed .41 source in all cases"
    report.update(source_version=list(addon.bl_info["version"]), sources=[pin(module.__file__) for module in (addon, runtime, target, inventory)],
                  script=pin(__file__), parent_source={"path": str(PARENT), "sha256": PARENT_SHA},
                  blender=bpy.app.version_string, native_thread_request=1, frame_sequence=list(FRAMES), cases=[])
    addon.register()
    for label, disabled_types in MODIFIER_CASES:
        opened = bpy.ops.wm.open_mainfile(filepath=str(input_path))
        assert "FINISHED" in opened and Path(bpy.data.filepath).resolve() == input_path
        scene = bpy.context.scene
        rig, cosha, shoe = (scene.objects.get(name) for name in ("CoshaRig", "Cosha", "Shoes"))
        assert rig and cosha and shoe and not runtime._ERRORS
        assert proof_result(lambda: inventory.validate(rig))["passed"]
        assert proof_result(lambda: target.control_rest_view(rig))["passed"]
        before = managed_summary(runtime, scene)
        assert set(before) == {"Cosha"} and {value["side"] for value in before["Cosha"]} == {"L", "R"}
        assert all(value["enabled"] is True and value["support_vertices"] == 191
                   and value["mute"] is False and value["value"] == 1.0 for value in before["Cosha"])
        row = {"label": label, "private_cosha_deletion": native_delete_mesh(scene, cosha),
               "disabled_modifier_types": list(disabled_types)}
        for kind in ("MIRROR", "ARMATURE"):
            modifiers = [modifier for modifier in shoe.modifiers if modifier.type == kind]
            assert len(modifiers) == 1 and modifiers[0].show_viewport
            if kind in disabled_types:
                modifiers[0].show_viewport = False
        row["modifiers"] = [{"name": modifier.name, "type": modifier.type, "viewport": modifier.show_viewport}
                            for modifier in shoe.modifiers]
        timing = RouteTiming(runtime, inventory, target)
        try:
            for frame in (1, 3):
                scene.frame_set(frame); bpy.context.view_layer.update()
            rows = []
            for frame in FRAMES:
                timing.reset()
                began = time.perf_counter_ns()
                scene.frame_set(frame); bpy.context.view_layer.update()
                total_ms = (time.perf_counter_ns() - began) / 1_000_000
                route = route_state(runtime, scene)
                assert route["no_calibrated_mesh_in_scene"] and runtime.__name__ + "._calculate_records" not in timing.calls
                rows.append({"frame": frame, "total_evaluation_ms": total_ms,
                             "functions": timing.summary(), "errors": dict(runtime._ERRORS)})
            evaluated = shoe.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            row.update(frames=rows, median_total_evaluation_ms=statistics.median(value["total_evaluation_ms"] for value in rows),
                       evaluated_shoes={"vertices": len(evaluated.vertices), "edges": len(evaluated.edges), "faces": len(evaluated.polygons)},
                       route_after=route_state(runtime, scene), performance_acceptance=False)
            report["cases"].append(row)
            print("CASE", label, round(row["median_total_evaluation_ms"], 3), flush=True)
        finally:
            timing.restore()
    report["input_after"], report["artist_after"] = pin(input_path), pin(artist_path)
    assert report["input_before"] == report["input_after"] and report["artist_before"] == report["artist_after"]
    report.update(input_disk_unchanged=True, artist_disk_unchanged=True, no_live_artist_access=True,
                  no_scene_save=True, no_source_or_metadata_change=True,
                  limits=["Same .41 private process and saved input; no .40-to-.41 speed comparison.",
                          "Native background evaluation only; no viewport rendering or GUI-FPS conclusion.",
                          "Cosha and its corrective output are absent in every case; modifier disabling changes the test model.",
                          "Eight hot frames after two warm frames, sequential order and shared load; not controlled final acceptance.",
                          "Nested function times overlap; compound gains are not additive."])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    report = {"schema": "x.private-shoes-modifier-diagnostic-07741/1", "completed": False,
              "pid": os.getpid(), "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "model_and_reasoning_effort": "unrecorded"}
    try:
        main(args, report); report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc(); raise
    finally:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
