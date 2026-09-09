"""Actual runtime animation render versus static reference, on a synthetic rig.

Run Blender --background --factory-startup --python-exit-code 1 --python this
file. Only synthetic fixtures and temporary PNGs are created.
"""
from array import array
import json
import math
import os
import sys
import tempfile

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import test_forearm_twist_blender as fixture_module
from character_designer import forearm_twist as runtime


def pixels(path):
    image = bpy.data.images.load(path, check_existing=False)
    try:
        result = array("f", [0.0]) * len(image.pixels)
        image.pixels.foreach_get(result)
        return result
    finally:
        bpy.data.images.remove(image)


def main():
    data = fixture_module.make_fixture("DIRECT_PREROLL")
    mesh, armature, target = data["mesh"], data["armature"], data["target"]
    runtime.start_test(bpy.context, mesh)
    preview_rotation = tuple(target.rotation_euler)
    rotations = [tuple(value * fraction for value in preview_rotation) for fraction in (1.0, -0.4, 0.7)]
    runtime.finish_test(bpy.context, True)
    shaped = mesh.data.shape_keys.key_blocks["ExistingForearm"]
    shape_values = (0.3, 0.3, 0.3) if "--constant-shape" in sys.argv else (0.1, 0.8, 0.3)
    for frame, (rotation, value) in enumerate(zip(rotations, shape_values), 1):
        target.rotation_euler = rotation
        target.keyframe_insert("rotation_euler", frame=frame)
        shaped.value = value
        shaped.keyframe_insert("value", frame=frame)
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Twist render probe camera")
    camera = bpy.data.objects.new("Twist render probe camera", camera_data)
    scene.collection.objects.link(camera)
    lower = armature.data.bones[data["lower_name"]]
    center = (lower.head_local + lower.tail_local) * 0.5
    camera.location = center + Vector((0, -2, 0))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = lower.length * 1.55
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_lock_interface = True
    scene.frame_start, scene.frame_end = 1, 3
    scene.frame_set(1)
    render_coordinates = {}
    original_update = runtime.update_runtime

    def observed_update(scene, depsgraph=None):
        original_update(scene, depsgraph)
        if depsgraph is not None and depsgraph.mode == "RENDER":
            managed = mesh.data.shape_keys.key_blocks[runtime.KEY_PREFIX + "L"]
            render_coordinates[int(scene.frame_current)] = [point.co.copy() for point in managed.data]
            print("RENDER_UPDATE " + json.dumps({"frame": int(scene.frame_current),
                  "shape": shaped.value,
                  "evaluated_shape": mesh.data.shape_keys.evaluated_get(depsgraph).key_blocks[shaped.name].value}), flush=True)

    runtime.update_runtime = observed_update
    with tempfile.TemporaryDirectory(prefix="cd_actual_twist_render_") as directory:
        scene.render.filepath = os.path.join(directory, "animated_")
        bpy.ops.render.render(animation=True)
        assert not runtime._ERRORS, runtime._ERRORS
        bpy.app.handlers.depsgraph_update_post.remove(runtime._graph_post)
        bpy.app.handlers.frame_change_post.remove(runtime._frame_post)
        animated = []
        results = []
        try:
            for frame in (1, 2, 3):
                scene.frame_set(frame)
                runtime._CACHE.clear()
                runtime.update_runtime(scene, bpy.context.evaluated_depsgraph_get())
                bpy.context.view_layer.update()
                assert not runtime._ERRORS, runtime._ERRORS
                scene.render.filepath = os.path.join(directory, f"reference_{frame}.png")
                bpy.ops.render.render(write_still=True)
                before = pixels(os.path.join(directory, f"animated_{frame:04}.png"))
                after = pixels(scene.render.filepath)
                error = max(abs(a - b) for a, b in zip(before, after))
                coordinate_error = max((point.co - saved).length for point, saved in zip(
                    mesh.data.shape_keys.key_blocks[runtime.KEY_PREFIX + "L"].data, render_coordinates[frame]))
                animated.append(before)
                results.append({"frame": frame, "pixel_error": error, "key_coordinate_error": coordinate_error})
                print("ACTUAL_TWIST_RENDER_FRAME " + json.dumps(results[-1]), flush=True)
            # Protect against a vacuous comparison of empty/same images.
            assert max(abs(a - b) for a, b in zip(animated[0], animated[1])) > 0.05
            assert max(abs(a - b) for a, b in zip(animated[1], animated[2])) > 0.05
            print("ACTUAL_TWIST_RENDER " + json.dumps(results), flush=True)
            assert all(row["pixel_error"] < 1e-7 for row in results), results
        finally:
            bpy.app.handlers.depsgraph_update_post.append(runtime._graph_post)
            bpy.app.handlers.frame_change_post.append(runtime._frame_post)
            runtime.update_runtime = original_update


if __name__ == "__main__":
    main()
