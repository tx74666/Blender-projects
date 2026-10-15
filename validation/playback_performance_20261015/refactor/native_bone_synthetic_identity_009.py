"""Separate generated-fixture swing/twist experiment; no .blend is opened.

Only use staged pinned fixture modules. This verifies two subdivision levels,
object transforms and an affected foreign Shape Key mask, independently of the
saved actor's clip. Numerical differences are recorded without tolerance waiver.
"""
import argparse
import datetime
import importlib
import json
import math
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support_v6 as witness
import native_bone_support_v7 as geometry
from private_playback_native_runner_v7 import field, isolation, select_scene

CASES = (
    ("rest", 0.0, 0.0, 0.0, 0.0),
    ("twist_plus90", 90.0, 0.0, 0.0, 0.0),
    ("twist_minus90", -90.0, 0.0, 0.0, 0.0),
    ("swing", 0.0, 0.35, 0.20, 0.0),
    ("combined45", 45.0, 0.25, -0.18, 0.02),
)


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index("--")]
    if not bpy.app.background or "--factory-startup" not in native:
        raise RuntimeError("Private factory-startup background required")
    if not any(value in ("-t", "--threads") and native[i + 1] == "1" for i, value in enumerate(native[:-1])):
        raise RuntimeError("Explicit native -t 1 required")
    if bpy.data.filepath:
        raise RuntimeError("Synthetic probe must never load an artist/input file")
    artist = Path(args.artist).resolve()
    artist_before = witness.pin(artist)
    package = Path(args.addons).resolve() / "character_designer"
    manifest = json.loads(Path(args.source_manifest).read_text(encoding="utf-8-sig"))
    source_pins = witness.verify_package_manifest(package, manifest)
    fixture_manifest = json.loads(Path(args.fixture_manifest).read_text(encoding="utf-8-sig"))
    if fixture_manifest.get("schema") != "x.playback-synthetic-fixture-seal/1":
        raise RuntimeError("Unexpected fixture seal")
    tests = Path(fixture_manifest["directory"]).resolve()
    def verify_fixtures():
        for name, expected in fixture_manifest["files"].items():
            actual = witness.pin(tests / name)
            if actual["sha256"] != expected["sha256"] or actual["bytes"] != expected["bytes"]:
                raise RuntimeError("Staged fixture changed: " + name)
    verify_fixtures()
    sys.path[:0] = [str(package.parent), str(tests)]
    addon = importlib.import_module("character_designer")
    runtime = importlib.import_module("character_designer.forearm_twist")
    core = importlib.import_module("character_designer.forearm_twist_playback_core")
    bone = importlib.import_module("character_designer.forearm_twist_bone_preview")
    scene_module = importlib.import_module("character_designer.forearm_twist_playback_scene")
    fixtures = importlib.import_module("test_forearm_twist_blender")
    if Path(addon.__file__).resolve().parent != package or Path(fixtures.__file__).resolve().parent != tests or Path(fixtures.base.__file__).resolve().parent != tests:
        raise RuntimeError("A nonstaged package/fixture module was imported")
    report.update(artist_before=artist_before, sources=source_pins, source_manifest=witness.pin(args.source_manifest),
                  fixture_manifest=witness.pin(args.fixture_manifest), script=witness.pin(__file__),
                  bone_witness_script=witness.pin(geometry.__file__), witness_script=witness.pin(witness.__file__),
                  frozen_runner_dependency=witness.pin(HERE / "private_playback_native_runner_v7.py"),
                  model="gpt-6.1-sol", reasoning_effort="ultra",
                  model_and_reasoning_effort="gpt-6.1-sol / ultra",
                  model_source="Current root task local index verified by root; inherited task settings.",
                  blender=bpy.app.version_string, version=list(addon.bl_info["version"]), cases=[], disposables=[])
    before_handlers = witness.handler_snapshot()
    report["extra_witness_sources"] = witness.witness_dependency_pins()
    registered, session, template, plan, source_scene, preview = False, None, None, None, None, None
    source_created, private_ids = [], set()
    errors = []

    def close_candidate():
        nonlocal session, template, plan, private_ids, preview
        if preview is not None:
            preview.close()
        if template is not None:
            core.discard_template(template)
        if plan is not None:
            bone.discard_plan(plan)
        if source_scene is not None:
            select_scene(source_scene)
        if session is not None:
            session.close()
        remaining = sorted(private_ids & witness.native_id_pointers())
        report["disposables"].append({"remaining_owned_id_pointers": remaining, "all_removed": not remaining})
        session, template, plan, private_ids, preview = None, None, None, set(), None
        if remaining:
            raise RuntimeError("Synthetic candidate cleanup retained IDs")

    try:
        addon.register()
        registered = True
        fixtures.base.reset_scene()
        baseline_inventory = scene_module._inventory()
        source_scene = bpy.context.scene
        report["observed_scene_units"] = {"system": source_scene.unit_settings.system,
            "scale_length": float(source_scene.unit_settings.scale_length), "length_unit": source_scene.unit_settings.length_unit,
            "coordinate_error_units": "object-local native model units; not automatically millimeters"}
        try:
            fixture = fixtures.make_fixture("ROLL_DECOUPLED", transformed_objects=True)
            mesh, rig = fixture["mesh"], fixture["armature"]
            # Exercise a foreign mask whose deform weights will be transferred.
            mesh.data.shape_keys.key_blocks["ExistingForearm"].vertex_group = fixture["lower_name"]
            runtime.start_test(bpy.context, mesh, side="L", symmetry=False, initial_angle=math.pi / 2)
            runtime.finish_test(bpy.context, confirm=True)
        finally:
            after_fixture = scene_module._inventory()
            source_created = [
                (name, item.as_pointer(), getattr(item, "session_uid", None))
                for name, values in after_fixture.items()
                for item in getattr(bpy.data, name)
                if item.as_pointer() in values - baseline_inventory.get(name, set())
            ]
            report["generated_fixture_ownership"] = {
                "scope": "factory process with exact pre-registration handlers; known staged fixture builders only",
                "builder": "test_forearm_twist_blender.make_fixture + forearm.start_test/finish_test",
                "created_native_ids": [{"collection": name, "pointer": pointer, "session_uid": uid}
                                       for name, pointer, uid in source_created],
                "limits": "Creation delta is scoped diagnostic evidence; cleanup additionally checks each actual native session UID.",
            }
        pairs = [(obj.name, obj) for obj in source_scene.objects]
        rig_names = {obj.name: tuple(item.name for item in obj.data.bones) for obj in source_scene.objects if obj.type == "ARMATURE"}
        managed = tuple(record["key"] for record in runtime._records(mesh).values())
        source_converted = {mesh.name: {"managed_names": managed}}
        with runtime.defer_runtime(bpy.context, flush_on_exit=False):
            for subdivision in (0, 1):
                select_scene(source_scene)
                mesh.modifiers[1].levels = subdivision
                golden, vectors = {}, {}
                for case in CASES:
                    name, angle, bend, wave, offset = case
                    fixtures.pose_target(fixture, angle, bend=bend, side_wave=wave, elbow_offset=offset)
                    runtime._calculate_object(mesh, bpy.context.evaluated_depsgraph_get())
                    bpy.context.view_layer.update()
                    golden[name], raw = geometry.bone_frame_witness(source_scene, pairs, runtime, {}, source_converted, rig_names)
                    vectors[name] = {obj_name: geometry.compressed_vectors(fields) for obj_name, fields in raw.items()}
                protected_output = witness.frame_witness(source_scene, pairs, runtime, {})
                protected_props = witness.source_property_witness(source_scene)
                template = core.capture(mesh, bpy.context.evaluated_depsgraph_get())
                plan = bone.plan_from_template(template)
                before_private = witness.native_id_pointers()
                try:
                    session = scene_module.build_isolated_scene(source_scene)
                finally:
                    private_ids = witness.native_id_pointers() - before_private
                scene, objects, eligible, reverse = isolation(session, source_scene, runtime)
                select_scene(scene)
                bpy.context.view_layer.update()
                target, target_rig = objects[mesh], objects[rig]
                preview = bone.build_isolated_preview(target, target_rig, plan, template=template,
                    isolated_scene=scene, source_mesh=mesh, source_rig=rig, disposable=True, helper_rest_mode="identity")
                approved = geometry.weight_rewrite_witness(mesh, target, target_rig, plan, preview)
                converted = {mesh.name: {"managed_names": managed, "mask_copies": preview.mask_copies, "bone_route": True}}
                dormant = geometry.dormant_managed_keys(target, managed)
                target_pairs = [(source.name, clone) for source, clone in objects.items()]
                controller = target_rig.pose.bones[fixture["target"].name]
                names = {item for side in plan.sides for item in (side.lower, side.hand)}
                inverses = {name: target_rig.data.bones[name].matrix_local.inverted() for name in names}
                for case in CASES:
                    name, angle, bend, wave, offset = case
                    controller.rotation_euler = (bend, math.radians(angle), wave)
                    controller.location = (0.0, offset, 0.0)
                    bpy.context.view_layer.update()
                    graph = bpy.context.evaluated_depsgraph_get()
                    evaluated = target_rig.evaluated_get(graph)
                    try:
                        angles = preview.update_from_deformations({name: evaluated.pose.bones[name].matrix @ inverse for name, inverse in inverses.items()})
                    except BaseException:
                        report["helper_update_failure"] = {"case": name, "subdivision": subdivision,
                            "last_basis_report": preview.last_basis_report,
                            "last_verification": preview.last_verification, "last_error": preview.last_error}
                        raise
                    bpy.context.view_layer.update()
                    try:
                        matrix_verification = preview.verify_evaluated(bpy.context.evaluated_depsgraph_get())
                        if matrix_verification.get("completed") is not True or matrix_verification.get("within_tolerance") is not True:
                            raise RuntimeError("Synthetic helper matrix oracle did not pass")
                        matrix_verification["basis_readback"] = preview.last_basis_report
                    except BaseException:
                        report["matrix_verification_failure"] = {"case": name, "subdivision": subdivision,
                            "last_verification": preview.last_verification}
                        raise
                    actual, raw = geometry.bone_frame_witness(scene, target_pairs, runtime, reverse, converted, rig_names)
                    if actual["scope"][mesh.name]["dormant_managed_coordinates"] != dormant:
                        raise RuntimeError("Synthetic bone playback rewrote dormant key data")
                    comparison = geometry.compare_frames(golden[name], vectors[name], actual, raw, converted_names=converted)
                    report["cases"].append({"case": name, "subdivision": subdivision,
                        "input_pose": {"twist_degrees": angle, "bend_radians": bend, "side_wave_radians": wave, "elbow_offset": offset},
                        "side_angles_radians": angles, "matrix_verification": matrix_verification,
                        "helper_count": len(preview.helper_names), "approved_weights": approved, **comparison})
                select_scene(source_scene)
                bpy.context.view_layer.update()
                if not witness.compare_witness(protected_output, witness.frame_witness(source_scene, pairs, runtime, {}))["exact"] or protected_props != witness.source_property_witness(source_scene):
                    raise RuntimeError("Synthetic bone candidate changed its source fixture")
                close_candidate()
    finally:
        try:
            close_candidate()
        except BaseException:
            errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        if source_scene is not None and source_created:
            try:
                cleanup = scene_module.PlaybackSceneSession(source_scene, None, created=source_created)
                cleanup.close()
            except BaseException:
                errors.append(traceback.format_exc())
        report["cleanup"] = {"errors": errors, "guard_released": not runtime._BUSY,
            "handlers_restored_exact": before_handlers == witness.handler_snapshot(),
            "known_forearm_lifecycle_timer_gone": not bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle),
            "issued_templates_empty": not len(core._ISSUED_TEMPLATES), "issued_plans_empty": not len(bone._ISSUED_PLANS),
            "fixture_owned_ids_removed": not any(pointer in witness.native_id_pointers() for _collection, pointer, _uid in source_created)}
        report["artist_after"] = witness.pin(artist)
        report["artist_disk_unchanged"] = artist_before == report["artist_after"]
        report["staged_sources_unchanged"] = source_pins == witness.verify_package_manifest(package, manifest)
        report["extra_witness_sources_after"] = witness.witness_dependency_pins()
        report["extra_witness_sources_unchanged"] = report["extra_witness_sources"] == report["extra_witness_sources_after"]
        if not report["extra_witness_sources_unchanged"]:
            raise RuntimeError("Source witness dependencies changed")
        verify_fixtures()
        if errors or not all(value for key, value in report["cleanup"].items() if key != "errors"):
            raise RuntimeError("Synthetic owned cleanup did not complete")
        if not report["artist_disk_unchanged"] or bpy.data.filepath:
            raise RuntimeError("Synthetic process touched artist or loaded a file")
    report["all_strict_nonvector_outputs_exact"] = all(row["strict_nonvector_outputs_exact"] for row in report["cases"])
    report["all_coordinates_and_normals_exact"] = all(row["all_coordinates_and_normals_exact"] for row in report["cases"])
    report["numeric_error_acceptance_pending"] = True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("artist", "addons", "source-manifest", "fixture-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite evidence")
    report = {"schema": "x.private-bone-synthetic-pose/2", "completed": False, "pid": __import__("os").getpid(),
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "model_and_reasoning_effort": "unrecorded",
        "no_blend_open": True, "no_artist_open_or_save": True, "no_scene_save": True, "no_deploy": True,
        "performance_acceptance": False, "helper_rest_mode": "identity",
        "limits": ["Generated transformed ROLL_DECOUPLED fixture; not proof of the saved actor or all animations.",
                   "Five rest/twist/swing/combined poses at Subsurf0/1 with a foreign mask; all differences are reported without tolerance waiver.",
                   "Helper basis/evaluated-deformation oracle is required before geometry evidence; failure retains the original native verification.",
                   "No .blend is opened; only protected artist disk pins are read.",
                   "No GUI FPS or performance measurements; numerical error acceptance remains pending."]}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
