"""Tiny factory Scene/Material/World/compositor copy smoke; no .blend open."""
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
import native_validation_support as witness


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index("--")]
    if not bpy.app.background or "--factory-startup" not in native or bpy.data.filepath:
        raise RuntimeError("Empty factory-startup private background process required")
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
    created_source, session, private_ids = [], None, set()
    before_handlers = witness.handler_snapshot()
    report.update(artist_before=artist_before, source_manifest=witness.pin(args.source_manifest),
                  sources=sources_before, script=witness.pin(__file__), witness_script=witness.pin(witness.__file__),
                  blender=bpy.app.version_string, version=list(addon.bl_info["version"]))
    try:
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
                    "compositor_child": group_node.node_tree.as_pointer()}
        pointer_before = source_pointers()
        properties_before = witness.source_property_witness(source)
        old_ids = witness.native_id_pointers()
        try:
            session = module.build_isolated_scene(source)
        finally:
            private_ids = witness.native_id_pointers() - old_ids
        mapping = session.id_map
        target_material, target_world = mapping[material], mapping[world]
        target_comp, target_child = mapping[compositor], mapping[child]
        target_cube = session.object_map[cube]
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
            "source_pointers_exact": pointer_before == source_pointers(),
            "source_properties_exact": properties_before == witness.source_property_witness(source),
            "no_registered_handlers": before_handlers == witness.handler_snapshot(),
        }
        report.update(checks=checks, source_pointers=pointer_before, session=session.inspect())
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
        report["artist_after"] = witness.pin(artist)
        report["artist_disk_unchanged"] = artist_before == report["artist_after"]
        report["sources_unchanged"] = sources_before == witness.verify_package_manifest(package, manifest)
        report["handlers_unchanged"] = before_handlers == witness.handler_snapshot()
        report["cleanup_errors"] = errors
        if errors or not report["private_ids_removed"] or not report["source_created_ids_removed"]:
            raise RuntimeError("Smoke owned ID cleanup failed")
        if not report["artist_disk_unchanged"] or not report["handlers_unchanged"] or bpy.data.filepath:
            raise RuntimeError("Smoke protected boundary failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("artist", "addons", "source-manifest", "report"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = Path(args.report).resolve()
    if path.exists():
        raise RuntimeError("Never overwrite evidence")
    report = {"schema": "x.private-scene-builder-api-smoke/1", "completed": False, "pid": os.getpid(),
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "model": "gpt-6.1-sol", "reasoning_effort": "ultra",
              "model_source": "Current root task local index verified by root; inherited task settings.",
              "no_blend_open": True, "no_artist_open_or_save": True, "no_addon_register": True,
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
