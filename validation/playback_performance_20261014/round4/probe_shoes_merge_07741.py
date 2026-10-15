"""Private fixed-input .41 Mirror merge differential. No scene save or artist open.

Thirty complete-model frames must retain exactly the same evaluated Shoes and
Forearm/rig output. Eight 8-frame ABBA timing blocks exclude fingerprint work.
Unsupported native attribute fields fail closed; reports contain hashes only.
"""
import hashlib
from pathlib import Path

PARENT = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4\probe_native_mesh_delete_v2.py")
PARENT_SHA = "c4a3338ce6efc3220759f502e205a122d9d5dfc1f04a9d41afc8c853f20c9b39"
raw = PARENT.read_bytes()
assert hashlib.sha256(raw).hexdigest() == PARENT_SHA, "Definition source pin changed"
prefix, marker, _ = raw.decode("utf-8-sig").replace("\r\n", "\n").partition('\nif __name__ == "__main__":\n')
assert marker
exec(compile(prefix, str(PARENT), "exec"), globals())
import struct

SOURCE_PINS = {
    "__init__.py": "b52eb75709c3c18d819afffcaf0a45e3fb36314e453c7a05a67c2a4da196627a",
    "forearm_twist.py": "d7a28470d61b74b1f2d4f146135bf14424e1633c0a88ded706c1e6be5adc1b10",
    "animation_worklist_target.py": "e6ffa5cfefeb12941055e4cef43bdb060c069cbeed9fee6c5d39a810b3e68db3",
    "forearm_original_inventory.py": "28a86885c5cba5579cd054a41d27933787f33ec0d19cf452f4a858da4ca069ac",
}
ALL_FRAMES = tuple(range(1, 31))
BLOCK_ORDER = ("baseline", "candidate", "candidate", "baseline") * 2


def object_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def bulk_hash(collection, field, kind, width=1):
    values = array(kind, [0]) * (len(collection) * width)
    collection.foreach_get(field, values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def attribute_fields(collection):
    """Hash every actual native value field, including future known scalar types."""
    if not len(collection):
        return {"count": 0}
    result = {"count": len(collection)}
    for prop in collection[0].bl_rna.properties:
        name = prop.identifier
        if name == "rna_type":
            continue
        width = prop.array_length if prop.is_array else 1
        assert width >= 1, "Unexpected variable array: " + name
        if prop.type in ("FLOAT", "INT", "BOOLEAN"):
            kind = {"FLOAT": "f", "INT": "i", "BOOLEAN": "b"}[prop.type]
            digest = bulk_hash(collection, name, kind, width)
        elif prop.type in ("STRING", "ENUM") and width == 1:
            digest_state = hashlib.sha256()
            for item in collection:
                text = json.dumps(getattr(item, name), ensure_ascii=False).encode("utf-8")
                digest_state.update(struct.pack("<I", len(text)))
                digest_state.update(text)
            digest = digest_state.hexdigest()
        else:
            raise RuntimeError("Unsupported evaluated attribute RNA field: " + name + " " + prop.type)
        result[name] = {"type": prop.type, "width": width, "sha256": digest}
    assert len(result) > 1, "Attribute has no supported native value fields"
    return result


def evaluated_shoes(shoe):
    evaluated_obj = shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated_obj.data
    assert isinstance(mesh, bpy.types.Mesh)
    nv, ne, np, nl = len(mesh.vertices), len(mesh.edges), len(mesh.polygons), len(mesh.loops)
    components = {
        "counts": object_hash([nv, ne, np, nl]),
        "vertex_coordinates": bulk_hash(mesh.vertices, "co", "f", 3),
        "vertex_normals": bulk_hash(mesh.vertices, "normal", "f", 3),
        "edges": bulk_hash(mesh.edges, "vertices", "i", 2),
        "loop_vertices": bulk_hash(mesh.loops, "vertex_index", "i"),
        "loop_edges": bulk_hash(mesh.loops, "edge_index", "i"),
        "polygon_loop_start": bulk_hash(mesh.polygons, "loop_start", "i"),
        "polygon_loop_total": bulk_hash(mesh.polygons, "loop_total", "i"),
        "polygon_material_index": bulk_hash(mesh.polygons, "material_index", "i"),
        "polygon_smooth": bulk_hash(mesh.polygons, "use_smooth", "b"),
        "polygon_normals": bulk_hash(mesh.polygons, "normal", "f", 3),
        "object_matrix_world": object_hash([[float(x).hex() for x in row] for row in evaluated_obj.matrix_world]),
        "normal_metadata": object_hash([mesh.normals_domain, mesh.has_custom_normals]),
        "materials": object_hash([[mat.name_full, mat.library.filepath if mat.library else None]
                                  if mat else None for mat in mesh.materials]),
        "vertex_groups": object_hash([[group.index, group.name] for group in evaluated_obj.vertex_groups]),
    }
    assert len(mesh.corner_normals) == nl, "Incomplete evaluated corner normal coverage"
    components["corner_normals"] = bulk_hash(mesh.corner_normals, "vector", "f", 3)
    weights = bytearray()
    for vertex in mesh.vertices:
        weights.extend(struct.pack("<II", vertex.index, len(vertex.groups)))
        for group in vertex.groups:
            weights.extend(struct.pack("<If", group.group, group.weight))
    components["weights"] = hashlib.sha256(weights).hexdigest()
    attribute_scope = []
    for index, attr in enumerate(mesh.attributes):
        values = attribute_fields(attr.data)
        attr_metadata = [attr.name, attr.data_type, attr.domain, len(attr.data)]
        components["attribute:" + str(index) + ":" + attr.name] = object_hash([attr_metadata, values])
        attribute_scope.append({"name": attr.name, "type": attr.data_type, "domain": attr.domain,
                                "count": len(attr.data), "fields": list(values)[1:]})
    uv_scope = []
    for index, layer in enumerate(mesh.uv_layers):
        uv_metadata = [layer.name, layer.active_render, layer.active_clone]
        values = attribute_fields(layer.data)
        components["uv:" + str(index) + ":" + layer.name] = object_hash([uv_metadata, values])
        uv_scope.append({"name": layer.name, "count": len(layer.data), "fields": list(values)[1:]})
    components["uv_active_index"] = object_hash(mesh.uv_layers.active_index)
    return {"sha256": object_hash(components), "components": components,
            "scope": {"vertices": nv, "edges": ne, "faces": np, "loops": nl,
                      "attributes": attribute_scope, "uv_layers": uv_scope}}


def healthy_forearm(runtime, target, inventory, scene, rig, full_proof=False):
    assert scene.objects.get("Cosha") and scene.objects.get("Shoes")
    assert not runtime._ERRORS, "Forearm errors: " + repr(runtime._ERRORS)
    managed = managed_summary(runtime, scene, coordinates=True)
    assert set(managed) == {"Cosha"}
    assert {entry["side"] for entry in managed["Cosha"]} == {"L", "R"}
    assert all(entry["support_vertices"] == 191 and entry["enabled"] is True
               and entry["value"] == 1.0 and entry["mute"] is False for entry in managed["Cosha"])
    if full_proof:
        inventory.validate(rig)
        target.control_rest_view(rig)
    pose = {bone.name: [[float(x).hex() for x in row] for row in bone.matrix]
            for bone in rig.pose.bones}
    cosha = scene.objects["Cosha"]
    return object_hash({"managed": managed, "rig_pose": pose,
                        "calibration_record": cosha[runtime.RECORD_KEY], "errors": dict(runtime._ERRORS)})


def set_case(shoe, mirror, label):
    assert mirror.show_viewport and shoe.type == "MESH"
    mirror.use_mirror_merge = label == "baseline"
    assert mirror.use_mirror_merge is (label == "baseline")


def main(args, report):
    assert bpy.app.background
    native_args = sys.argv[:sys.argv.index("--")]
    assert any(value in ("-t", "--threads") and native_args[index + 1] == "1"
               for index, value in enumerate(native_args[:-1])), "Native -t 1 required"
    input_path, artist_path = Path(args.input).resolve(), Path(args.artist).resolve()
    assert input_path != artist_path
    report["input_before"], report["artist_before"] = pin(input_path), pin(artist_path)
    assert report["input_before"]["sha256"] == EXPECTED_INPUT_SHA256
    assert report["input_before"]["bytes"] == EXPECTED_INPUT_BYTES
    addons = Path(args.addons).resolve()
    sys.path.insert(0, str(addons))
    import character_designer as addon
    from character_designer import forearm_twist as runtime, animation_worklist_target as target
    from character_designer import forearm_original_inventory as inventory, limb_ik
    assert Path(addon.__file__).resolve().parent == addons / "character_designer"
    assert tuple(addon.bl_info["version"]) == (0, 77, 41)
    sources = [pin(module.__file__) for module in (addon, runtime, target, inventory)]
    assert all(source["sha256"] == SOURCE_PINS[Path(source["path"]).name] for source in sources)
    report.update(source_version=list(addon.bl_info["version"]), sources=sources, script=pin(__file__),
                  definition_source={"path": str(PARENT), "sha256": PARENT_SHA},
                  blender=bpy.app.version_string, native_thread_request=1,
                  differential_frames=list(ALL_FRAMES), hot_frames=list(FRAMES),
                  geometry_frame_checks=[], blocks=[])
    addon.register()

    def fresh_scene():
        result = bpy.ops.wm.open_mainfile(filepath=str(input_path))
        assert "FINISHED" in result and Path(bpy.data.filepath).resolve() == input_path
        scene = bpy.context.scene
        rig, shoe = scene.objects.get("CoshaRig"), scene.objects.get("Shoes")
        assert rig and shoe and scene.objects.get("Cosha") and not runtime._ERRORS
        modifiers = [modifier for modifier in shoe.modifiers if modifier.type == "MIRROR"]
        assert len(modifiers) == 1
        mirror = modifiers[0]
        assert mirror.show_viewport and mirror.use_mirror_merge, "Expected saved merge-enabled baseline"
        assert all(modifier.show_viewport for modifier in shoe.modifiers if modifier.type == "ARMATURE")
        path = mirror.path_from_id("use_mirror_merge")
        if shoe.animation_data:
            assert not any(curve.data_path == path for curve in shoe.animation_data.drivers), "Animated merge flag"
        for action in limb_ik._actions_for_id(shoe):
            assert not any(curve.data_path == path for curve in limb_ik._fcurves_for_action(action)), "Animated merge flag"
        healthy_forearm(runtime, target, inventory, scene, rig, full_proof=True)
        return scene, rig, shoe, mirror

    baseline = {}
    for label in ("baseline", "candidate"):
        scene, rig, shoe, mirror = fresh_scene()
        set_case(shoe, mirror, label)
        for frame in ALL_FRAMES:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            health = healthy_forearm(runtime, target, inventory, scene, rig, full_proof=True)
            geometry = evaluated_shoes(shoe)
            if label == "baseline":
                baseline[frame] = {"geometry": geometry, "forearm_sha256": health}
                if frame == 1:
                    report["evaluated_geometry_scope"] = geometry["scope"]
            else:
                prior = baseline[frame]
                changed = sorted(key for key in set(prior["geometry"]["components"]) | set(geometry["components"])
                                 if prior["geometry"]["components"].get(key) != geometry["components"].get(key))
                row = {"frame": frame, "geometry_exact": not changed,
                       "changed_components": changed, "baseline_geometry_sha256": prior["geometry"]["sha256"],
                       "candidate_geometry_sha256": geometry["sha256"],
                       "forearm_and_pose_exact": health == prior["forearm_sha256"],
                       "baseline_forearm_sha256": prior["forearm_sha256"], "candidate_forearm_sha256": health,
                       "healthy_inventory_and_rest": True}
                report["geometry_frame_checks"].append(row)
        print("DIFFERENTIAL", label, "30", flush=True)
    exact = all(row["geometry_exact"] and row["forearm_and_pose_exact"] for row in report["geometry_frame_checks"])
    report["all_30_geometry_and_forearm_exact"] = exact
    if not exact:
        report["candidate_eligible"] = False
        report["timing_skipped"] = "Exact differential failed; stop candidate branch"
    else:
        scene, rig, shoe, mirror = fresh_scene()
        for index, label in enumerate(BLOCK_ORDER):
            set_case(shoe, mirror, label)
            for frame in (1, 3):
                scene.frame_set(frame)
                bpy.context.view_layer.update()
            healthy_forearm(runtime, target, inventory, scene, rig, full_proof=True)
            measurements = []
            for frame in FRAMES:
                began = time.perf_counter_ns()
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                elapsed = (time.perf_counter_ns() - began) / 1_000_000
                assert not runtime._ERRORS and mirror.use_mirror_merge is (label == "baseline")
                output_hash = healthy_forearm(runtime, target, inventory, scene, rig)
                assert output_hash == baseline[frame]["forearm_sha256"], "Timing changed current Forearm output"
                measurements.append({"frame": frame, "native_evaluation_ms": elapsed})
            row = {"block": index, "case": label, "warm_frames": [1, 3], "frames": measurements,
                   "median_ms": statistics.median(value["native_evaluation_ms"] for value in measurements),
                   "healthy_complete_forearm": True}
            report["blocks"].append(row)
            print("BLOCK", index, label, round(row["median_ms"], 3), flush=True)
        base_blocks = [row["median_ms"] for row in report["blocks"] if row["case"] == "baseline"]
        candidate_blocks = [row["median_ms"] for row in report["blocks"] if row["case"] == "candidate"]
        base_median, candidate_median = statistics.median(base_blocks), statistics.median(candidate_blocks)
        report["timing_summary"] = {"baseline_block_medians_ms": base_blocks,
                                    "candidate_block_medians_ms": candidate_blocks,
                                    "baseline_median_ms": base_median, "candidate_median_ms": candidate_median,
                                    "observed_reduction_percent": (base_median - candidate_median) / base_median * 100.0}
        report["candidate_eligible"] = candidate_median < base_median
    report["input_after"], report["artist_after"] = pin(input_path), pin(artist_path)
    assert report["input_before"] == report["input_after"] and report["artist_before"] == report["artist_after"]
    assert all(pin(source["path"]) == source for source in sources)
    report.update(input_disk_unchanged=True, artist_disk_unchanged=True, no_scene_save=True,
                  no_artist_scene_access=True, no_deployment=True,
                  limits=["Private background evaluation; no viewport rendering or GUI FPS conclusion.",
                          "Eight ABBA blocks share one process and system load; noise and final adoption need review.",
                          "Eligibility only combines measured direction with exact outputs; no artist edit was performed.",
                          "Hashes include native float32 geometry fields and exact hex matrix/Forearm state; no raw arrays written."])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("input", "artist", "addons", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    report = {"schema": "x.private-shoes-merge-differential-07741/1", "completed": False,
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
