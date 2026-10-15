"""Tiny native Keyframe bulk API/field/mutation smoke; no actor/addon/scene IO."""
from array import array
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support_v8 as witness
import native_source_reference_witness_v8 as bulk
import native_source_reference_witness_v7 as previous


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index("--")]
    require(bpy.app.background and "--factory-startup" in native and not bpy.data.filepath, "Fresh factory background worker required")
    require(any(value in ("-t", "--threads") and native[index + 1] == "1" for index, value in enumerate(native[:-1])), "Native -t1 required")
    artist_before = witness.pin(args.artist)
    manifest_path = Path(args.source_manifest).resolve()
    manifest_before = witness.pin(manifest_path)
    require(manifest_before["sha256"] == "d62c3178ca6f0615fa4517440c157bba0ab2ced87cb64aa560ac1830197bac34", "Expected protected Stage05 manifest")
    package = Path(args.addons).resolve() / "character_designer"
    manifest = json.loads(manifest_path.read_text())
    sources = witness.verify_package_manifest(package, manifest)
    scripts = {p.name: witness.pin(p) for p in (Path(__file__), Path(witness.__file__), Path(bulk.__file__), Path(previous.__file__))}
    handlers, original_ids = witness.handler_snapshot(), witness.native_id_pointers()
    obj = action = None
    obj_uid = action_uid = None
    report.update(artist_before=artist_before, source_manifest=manifest_before, scripts=scripts,
                  blender=bpy.app.version_string, witness_sources=witness.witness_dependency_pins())
    try:
        obj = bpy.data.objects.new("Owned Keyframe Bulk Fixture", None)
        obj_uid = obj.session_uid
        # Native insertion creates a normal layered Action/slot/channelbag.
        # Only our unlinked object is touched; no active Scene frame is sought.
        for frame, value in ((1, 0.125), (2, -0.0), (3, -0.75)):
            obj.location.x = value
            try:
                inserted = obj.keyframe_insert(data_path="location", index=0, frame=frame)
            finally:
                if action is None and obj.animation_data is not None and obj.animation_data.action is not None:
                    action = obj.animation_data.action
                    action_uid = action.session_uid
            require(inserted, "Fixture insertion failed")
        action = obj.animation_data.action
        action_uid = action.session_uid
        bag = action.layers[0].strips[0].channelbags[0]
        curve = bag.fcurves[0]
        points = curve.keyframe_points
        for index, point in enumerate(points):
            point.handle_left_type = point.handle_right_type = "FREE"
            point.handle_left = (point.co.x - 0.2, point.co.y - 0.1)
            point.handle_right = (point.co.x + 0.2, point.co.y + 0.1)
            point.interpolation = "BEZIER"
            point.easing = "EASE_IN" if index % 2 else "EASE_OUT"
            point.type = "BREAKDOWN" if index % 2 else "EXTREME"
            point.back, point.amplitude, point.period = 0.7 + index, 0.5 + index, 0.3 + index
            point.select_control_point = bool(index % 2)
            point.select_left_handle = not bool(index % 2)
            point.select_right_handle = bool(index % 2)
        fixed_type = curve.bl_rna.properties["keyframe_points"].fixed_type
        def read():
            return bulk.keyframe_collection_witness(points, fixed_type, bulk.Reader(bpy.types.ID))
        old_reader = previous.Reader(bpy.types.ID)
        before_points = [old_reader.rna(point, "Fixture.Keyframe[" + str(index) + "]") for index, point in enumerate(points)]
        initial = read()
        after_points = [old_reader.rna(point, "Fixture.Keyframe[" + str(index) + "]") for index, point in enumerate(points)]
        require(before_points == after_points, "Bulk read changed the old full point witness")
        report["bulk_read_did_not_write_old_point_state"] = True
        report["old_point_state_sha256_before_after"] = [bulk.object_hash(before_points), bulk.object_hash(after_points)]
        field_checks = {}
        enum_checks = {}
        for name, definition in initial["definition"].items():
            kind, width = definition["type"], definition["width"]
            flat = []
            enum = dict(definition.get("enum_identifiers_and_values", ()))
            for point in points:
                value = getattr(point, name)
                flat.extend(value if width > 1 else [enum[value] if kind == "ENUM" else value])
            if kind == "BOOLEAN":
                expected = bytes(int(value) for value in flat)
            else:
                expected = array("f" if kind == "FLOAT" else "i", flat).tobytes()
            field_checks[name] = hashlib.sha256(expected).hexdigest() == initial["fields"][name]["sha256"]
            if kind == "ENUM":
                enum_checks[name] = all(getattr(point, name) in enum for point in points)
        # The ordinary old reader covers exactly the same point field set.
        old_fields = before_points[0]["properties"]
        require(set(old_fields) == set(initial["fields"]), "Old/native field coverage differs")
        require(all(field_checks.values()) and all(enum_checks.values()), "A native foreach_get field differs from per-point old reading")
        report.update(field_checks=field_checks, enum_api_checks=enum_checks, initial_bulk=initial,
                      all15_field_coverage_exact=True)
        original_co, original_handle = tuple(points[0].co), tuple(points[1].handle_right)
        points[0].co.x += 0.25
        points[1].handle_right.y -= 0.125
        changed = read()
        co_handle_trap = changed["fields"]["co"] != initial["fields"]["co"] and changed["fields"]["handle_right"] != initial["fields"]["handle_right"]
        points[0].co, points[1].handle_right = original_co, original_handle
        points[0].interpolation = "LINEAR"
        enum_trap = read()["fields"]["interpolation"] != initial["fields"]["interpolation"]
        points[0].interpolation = "BEZIER"
        points.add(1)
        points[-1].co = (4, 0.25)
        add_trap = read()["count"] == 4
        points.remove(points[-1])
        points.remove(points[-1])
        remove_trap = read()["count"] == 2
        custom_unsupported = False
        try:
            points[0]["owned_custom_trap"] = "must-not-be-skipped"
        except TypeError as error:
            custom_unsupported = True
            report["native_custom_assignment_rejected"] = str(error)
        require(custom_unsupported, "Native custom storage became supported; bulk must not infer zero")
        report["mutation_traps"] = {"co_and_handle": co_handle_trap, "enum": enum_trap,
                                    "add_key": add_trap, "remove_key": remove_trap,
                                    "native_custom_storage_unsupported": custom_unsupported}
        require(all(report["mutation_traps"].values()), "A deliberate mutation escaped witness")
        # Exercise the actual Reader.rna dispatch, rather than only the helper.
        dispatched = bulk.Reader(bpy.types.ID).rna(curve, "Fixture.FCurve")
        require(dispatched["properties"]["keyframe_points"]["schema"] == "x.native-keyframe-collection-bulk/1", "FCurve bulk dispatch not used")
        report["reader_dispatch_bulk"] = True
        print("KEYFRAME_BULK_FACTORY_PASS", len(field_checks), flush=True)
    finally:
        errors = []
        for collection, item, uid in ((bpy.data.objects, obj, obj_uid), (bpy.data.actions, action, action_uid)):
            if item is not None:
                try:
                    found = next((entry for entry in collection if entry.session_uid == uid), None)
                    require(found is not None and found.as_pointer() == item.as_pointer(), "Owned fixture ID identity changed")
                    collection.remove(found, do_unlink=True)
                except BaseException:
                    errors.append(traceback.format_exc())
        report["cleanup_errors"] = errors
        report["all_fixture_ids_removed"] = original_ids == witness.native_id_pointers()
        report["handlers_unchanged"] = handlers == witness.handler_snapshot()
        report["artist_disk_unchanged"] = artist_before == witness.pin(args.artist)
        report["stage_unchanged"] = sources == witness.verify_package_manifest(package, manifest) and manifest_before == witness.pin(manifest_path)
        report["witness_sources_unchanged"] = report["witness_sources"] == witness.witness_dependency_pins()
        report["scripts_unchanged"] = scripts == {name: witness.pin(value["path"]) for name, value in scripts.items()}
        require(not errors and all(report[name] for name in ("all_fixture_ids_removed", "handlers_unchanged", "artist_disk_unchanged", "stage_unchanged", "witness_sources_unchanged", "scripts_unchanged")), "Factory cleanup/protected boundary failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    require(not path.exists(), "Never overwrite evidence")
    report = {"schema": "x.native-keyframe-bulk-factory/1", "completed": False, "pid": os.getpid(),
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "no_blend_open_or_save": True, "no_addon_register": True, "performance_acceptance": False}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
