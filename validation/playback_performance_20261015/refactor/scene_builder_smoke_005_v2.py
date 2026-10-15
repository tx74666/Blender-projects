"""Factory registered asset-catalog / readonly Image copy smoke; no .blend open."""
import argparse
import datetime
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support_v5 as witness


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index("--")]
    if not bpy.app.background or "--factory-startup" not in native or bpy.data.filepath:
        raise RuntimeError("Empty factory-startup private background process required")
    if not any(value in ("-t", "--threads") and native[index + 1] == "1" for index, value in enumerate(native[:-1])):
        raise RuntimeError("Explicit native -t 1 required")
    artist = Path(args.artist).resolve()
    artist_before = witness.pin(artist)
    package = Path(args.addons).resolve() / "character_designer"
    manifest = json.loads(Path(args.source_manifest).read_text(encoding="utf-8-sig"))
    sources_before = witness.verify_package_manifest(package, manifest)
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module("character_designer")
    module = importlib.import_module("character_designer.forearm_twist_playback_scene")
    if Path(addon.__file__).resolve().parent != package:
        raise RuntimeError("A different addon source was imported")
    source = bpy.context.scene
    cube = source.objects.get("Cube")
    if cube is None or cube.type != "MESH" or cube.data.shape_keys:
        raise RuntimeError("Expected generated unkeyed factory Cube")
    before_ids = module._inventory()
    created_source, session, private_ids, image, image_uid = [], None, set(), None, None
    registered, runtime, properties_before = False, None, None
    before_handlers = witness.handler_snapshot()
    report.update(artist_before=artist_before, source_manifest=witness.pin(args.source_manifest),
                  sources=sources_before, script=witness.pin(__file__), witness_script=witness.pin(witness.__file__),
                  blender=bpy.app.version_string, version=list(addon.bl_info["version"]))
    try:
        addon.register()
        registered = True
        runtime = importlib.import_module("character_designer.forearm_twist")
        registered_handlers = witness.handler_snapshot()
        report["extra_witness_sources"] = witness.witness_dependency_pins()
        material = bpy.data.materials.new("Scene Smoke Material")
        material.use_nodes = True
        cube.data.materials.append(material)
        world = source.world
        if world is None:
            world = bpy.data.worlds.new("Scene Smoke World")
            source.world = world
        world.use_nodes = True
        compositor = bpy.data.node_groups.new("Scene Smoke Compositor", "CompositorNodeTree")
        child = bpy.data.node_groups.new("Scene Smoke Compositor Child", "CompositorNodeTree")
        group_node = compositor.nodes.new("CompositorNodeGroup")
        group_node.node_tree = child
        source.compositing_node_group = compositor
        image = bpy.data.images.new("Scene Smoke Readonly Image", width=8, height=8)
        image_uid = image.session_uid
        image_empty = bpy.data.objects.new("Scene Smoke Image Reference", None)
        image_empty.empty_display_type = "IMAGE"
        image_empty.data = image
        source.collection.objects.link(image_empty)
        hair_data = bpy.data.meshes.new("Scene Smoke Unlinked Hair Mesh")
        hair_data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        hair = bpy.data.objects.new("Hair1", hair_data)
        hair["source_protection_sentinel"] = "foreign-unlinked-fixture"
        hair.shape_key_add(name="Basis")
        foreign_key = hair.shape_key_add(name="Foreign Hair Fixture")
        foreign_key.data[0].co.x = 0.125
        foreign_key.value = 0.25
        setup = source.character_designer_setup
        setup.assets.clear()
        linked_row = setup.assets.add()
        linked_row.object, linked_row.role = cube, "CLOTHING"
        orphan_row = setup.assets.add()
        orphan_row.object, orphan_row.role = hair, "HAIR"
        setup.active_asset = 1
        def catalog(scene):
            state = scene.character_designer_setup
            return {"active_asset": state.active_asset,
                    "rows": [{"object": witness.logical_id(row.object, {}),
                              "pointer": row.object.as_pointer() if row.object else None,
                              "role": row.role} for row in state.assets]}
        catalog_before = catalog(source)
        bpy.context.view_layer.update()
        after_source = module._inventory()
        created_source = [(name, item.as_pointer(), getattr(item, "session_uid", None))
                          for name, values in after_source.items() for item in getattr(bpy.data, name)
                          if item.as_pointer() in values - before_ids.get(name, set())]
        def source_pointers():
            return {"scene": source.as_pointer(), "cube": cube.as_pointer(), "mesh": cube.data.as_pointer(),
                    "material": cube.data.materials[-1].as_pointer(), "material_tree": material.node_tree.as_pointer(),
                    "world": source.world.as_pointer(), "world_tree": world.node_tree.as_pointer(),
                    "compositor": source.compositing_node_group.as_pointer(),
                    "compositor_child": group_node.node_tree.as_pointer(),
                    "image_empty": image_empty.as_pointer(), "readonly_image": image.as_pointer(),
                    "image_uid": image.session_uid, "unlinked_hair": hair.as_pointer(),
                    "unlinked_hair_data": hair.data.as_pointer(), "unlinked_hair_uid": hair.session_uid}
        pointer_before = source_pointers()
        properties_before = witness.source_property_witness(source)
        protection = properties_before["registered_source_and_external_objects"]
        scope = protection["scope"]
        orphan_path = ".character_designer_setup.assets[1].object"
        coverage = {
            "scene_setup_property_set": bool(source.is_property_set("character_designer_setup")),
            "orphan_object_reference_path_exact": any(row["path"].endswith(orphan_path) and row["id"]["pointer"] == hair.as_pointer() for row in protection["reference_manifest"]),
            "foreign_hair_object_payload": any(row["pointer"] == hair.as_pointer() for row in scope["foreign_objects"]),
            "foreign_hair_mesh_payload": any(row["pointer"] == hair_data.as_pointer() and row["rna_type"] == "Mesh" for row in scope["payload_ids"]),
            "foreign_hair_key_payload": any(row["pointer"] == hair_data.shape_keys.as_pointer() and row["rna_type"] == "Key" for row in scope["payload_ids"]),
            "foreign_mesh_component_present": "external_payload:Mesh:" + hair_data.name_full in protection["components"],
            "foreign_key_component_present": "external_payload:Key:" + hair_data.shape_keys.name_full in protection["components"],
        }
        report["witness_coverage_admission"] = coverage
        report["witness_coverage_scope"] = scope
        report["source_registered_protection"] = protection
        report["source_catalog_before_clone"] = catalog_before
        if not all(coverage.values()):
            raise RuntimeError("Native stored asset/foreign Mesh/Key witness coverage is absent; no actor run permitted")
        old_ids = witness.native_id_pointers()
        source_images_before = {(item.as_pointer(), item.session_uid) for item in bpy.data.images}
        try:
            session = module.build_isolated_scene(source)
        finally:
            private_ids = witness.native_id_pointers() - old_ids
        mapping = session.id_map
        target_material, target_world = mapping[material], mapping[world]
        target_comp, target_child = mapping[compositor], mapping[child]
        target_cube = session.object_map[cube]
        target_catalog = session.scene.character_designer_setup
        detach_receipt = list(session.inspect()["detached_asset_references"])
        expected_detachment = ("character_designer_setup.assets[1].object", hair.name, hair.session_uid)
        actual_detachments = [(row["path"], row["source_object"], row["source_session_uid"]) for row in detach_receipt]
        checks = {
            "scene_private": session.scene is not source,
            "all_objects_mapped": set(session.object_map) == set(source.objects),
            "cube_mesh_private": target_cube.data is not cube.data,
            "material_slot_remapped": target_cube.data.materials[-1] == target_material,
            "material_and_tree_private": target_material is not material and target_material.node_tree is not material.node_tree,
            "world_and_tree_private": target_world is not world and target_world.node_tree is not world.node_tree,
            "scene_world_remapped": session.scene.world == target_world,
            "compositor_private": target_comp is not compositor and session.scene.compositing_node_group == target_comp,
            "compositor_child_private": target_child is not child and target_comp.nodes[group_node.name].node_tree == target_child,
            "image_empty_object_private": session.object_map[image_empty] != image_empty,
            "image_data_shared_readonly": session.object_map[image_empty].data == image,
            "readonly_image_not_owned_map": image not in mapping,
            "no_image_copy_allocated": source_images_before == {(item.as_pointer(), item.session_uid) for item in bpy.data.images},
            "source_pointers_exact": pointer_before == source_pointers(),
            "source_properties_exact": properties_before == witness.source_property_witness(source),
            "builder_registered_no_new_handlers": registered_handlers == witness.handler_snapshot(),
            "source_catalog_exact": catalog_before == catalog(source),
            "foreign_hair_stays_unlinked": not hair.users_scene and hair not in mapping and hair not in session.object_map,
            "clone_catalog_two_rows_in_order": len(target_catalog.assets) == 2 and [row.role for row in target_catalog.assets] == ["CLOTHING", "HAIR"],
            "clone_catalog_linked_object_remapped": target_catalog.assets[0].object == target_cube,
            "clone_catalog_orphan_object_none": target_catalog.assets[1].object is None,
            "clone_catalog_active_row_preserved": target_catalog.active_asset == setup.active_asset,
            "detachment_receipt_exact": actual_detachments == [expected_detachment] and bool(detach_receipt[0]["reason"]),
            "source_hair_in_witness_payload": any(row["pointer"] == hair.as_pointer() for row in properties_before["registered_source_and_external_objects"]["scope"]["foreign_objects"]),
        }
        report.update(checks=checks, source_pointers=pointer_before, session=session.inspect(), source_catalog=catalog_before,
                      source_registered_protection=properties_before["registered_source_and_external_objects"])
        if not all(checks.values()):
            raise RuntimeError("Factory Scene builder smoke failed")
        print("SCENE_BUILDER_SMOKE_PASS", len(checks), flush=True)
    finally:
        errors = []
        if session is not None:
            try:
                session.close()
            except BaseException:
                errors.append(traceback.format_exc())
        report["private_ids_removed"] = not bool(private_ids & witness.native_id_pointers())
        if properties_before is not None:
            try:
                report["source_properties_after_private_close_exact"] = properties_before == witness.source_property_witness(source)
                if not report["source_properties_after_private_close_exact"]:
                    errors.append("Source properties changed after private close")
            except BaseException:
                errors.append(traceback.format_exc())
        if not created_source:
            after_source = module._inventory()
            created_source = [(name, item.as_pointer(), getattr(item, "session_uid", None))
                              for name, values in after_source.items() for item in getattr(bpy.data, name)
                              if item.as_pointer() in values - before_ids.get(name, set())]
        try:
            module.PlaybackSceneSession(source, None, created=created_source).close()
        except BaseException:
            errors.append(traceback.format_exc())
        report["source_created_ids_removed"] = not any(pointer in witness.native_id_pointers() for _, pointer, _uid in created_source)
        if image is not None:
            try:
                current = next((item for item in bpy.data.images if item.session_uid == image_uid), None)
                if current is not None:
                    if current != image:
                        raise RuntimeError("Generated smoke Image identity changed")
                    bpy.data.images.remove(current, do_unlink=True)
                report["generated_fixture_image_removed"] = not any(item.session_uid == image_uid for item in bpy.data.images)
            except BaseException:
                errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        report["extra_witness_sources_after"] = witness.witness_dependency_pins()
        report["extra_witness_sources_unchanged"] = report.get("extra_witness_sources") == report["extra_witness_sources_after"]
        report["runtime_guard_released"] = runtime is None or not runtime._BUSY
        report["known_forearm_lifecycle_timer_gone"] = runtime is None or not bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle)
        report["artist_after"] = witness.pin(artist)
        report["artist_disk_unchanged"] = artist_before == report["artist_after"]
        report["sources_unchanged"] = sources_before == witness.verify_package_manifest(package, manifest)
        report["handlers_unchanged"] = before_handlers == witness.handler_snapshot()
        report["cleanup_errors"] = errors
        if errors or not report["private_ids_removed"] or not report["source_created_ids_removed"] or (image is not None and not report.get("generated_fixture_image_removed")):
            raise RuntimeError("Smoke owned ID cleanup failed")
        if not report["artist_disk_unchanged"] or not report["handlers_unchanged"] or not report["runtime_guard_released"] or not report["known_forearm_lifecycle_timer_gone"] or not report["extra_witness_sources_unchanged"] or bpy.data.filepath:
            raise RuntimeError("Smoke protected boundary failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite evidence")
    report = {"schema": "x.private-scene-builder-registered-catalog-smoke/2", "completed": False, "pid": os.getpid(),
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "model": "gpt-6.1-sol", "reasoning_effort": "ultra",
              "model_source": "Current root task local index verified by root; inherited task settings.",
              "no_blend_open": True, "no_artist_open_or_save": True, "owned_addon_register_then_unregister": True,
              "no_scene_save": True, "performance_claim": None,
              "limits": "Tiny generated factory graph API copy/remap/cleanup smoke; not full actor or numeric/performance validation."}
    try:
        main(args, report)
        report["completed"] = True
    except BaseException:
        report["error"] = traceback.format_exc()
        raise
    finally:
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
