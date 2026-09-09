"""Synthetic probe for per-pose corrective-key dependency graph timing.

Never opens or writes production assets. Run with factory-startup Blender.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from array import array

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector


RIG = "ForearmHandlerProbeRig"
MESH = "ForearmHandlerProbeMesh"
state = {"guard": False, "last": None, "mode": "plain", "calls": [], "errors": []}
original = [Vector((0.3, 1.5, 0.0)), Vector((-0.3, 1.5, 0.0)), Vector((0.0, 1.8, 0.3))]


def fixture():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    data = bpy.data.armatures.new(RIG + "Data")
    rig = bpy.data.objects.new(RIG, data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    lower = data.edit_bones.new("lower")
    lower.head, lower.tail = (0, 0, 0), (0, 2, 0)
    hand = data.edit_bones.new("hand")
    hand.head, hand.tail = (0, 2, 0), (0, 3, 0)
    hand.parent, hand.use_connect = lower, True
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.pose.bones["hand"].rotation_mode = "XYZ"
    mesh = bpy.data.meshes.new(MESH + "Data")
    mesh.from_pydata(original, [], [(0, 1, 2)])
    obj = bpy.data.objects.new(MESH, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for name in ("lower", "hand"):
        group = obj.vertex_groups.new(name=name)
        group.add([0, 1, 2], 0.5, "REPLACE")
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = rig
    obj.shape_key_add(name="Basis")
    key = obj.shape_key_add(name="Probe correction")
    key.value = 1
    bpy.context.view_layer.update()
    return rig, obj


def angle_of(rig):
    pose = rig.pose.bones["hand"]
    return float((pose.matrix @ pose.bone.matrix_local.inverted()).to_euler("XYZ").y)


def update_correction(scene, depsgraph, source):
    if state["guard"]:
        return
    rig, obj = bpy.data.objects.get(RIG), bpy.data.objects.get(MESH)
    if not rig or not obj:
        return
    state["guard"] = True
    try:
        evaluated = rig.evaluated_get(depsgraph)
        angle = angle_of(evaluated)
        state["calls"].append((source, int(scene.frame_current), round(angle, 6)))
        if state["last"] is not None and abs(angle - state["last"]) < 1e-7:
            return
        state["last"] = angle
        key = obj.data.shape_keys.key_blocks["Probe correction"]
        for point, baseline in zip(key.data, original):
            point.co = baseline + Vector((0, 0, angle))
        obj.data.shape_keys.update_tag()
        obj.data.update()
        if state["mode"] == "depsgraph_update":
            depsgraph.update()
        elif state["mode"] == "view_layer_update":
            bpy.context.view_layer.update()
    except Exception as exc:
        state["errors"].append((source, str(exc)))
    finally:
        state["guard"] = False


@persistent
def depsgraph_post(scene, depsgraph):
    update_correction(scene, depsgraph, "depsgraph_post")


@persistent
def frame_post(scene, depsgraph=None):
    update_correction(scene, depsgraph or bpy.context.evaluated_depsgraph_get(), "frame_post")


@persistent
def load_post(_):
    state["last"] = None
    state["calls"].append(("load_post", 0, 0))


def inspect(label, *, use_context_get=False):
    rig, obj = bpy.data.objects[RIG], bpy.data.objects[MESH]
    depsgraph = bpy.context.evaluated_depsgraph_get() if use_context_get else bpy.context.view_layer.depsgraph
    evaluated_rig = rig.evaluated_get(depsgraph)
    angle = angle_of(evaluated_rig)
    source = original[0] + Vector((0, 0, angle))
    expected = Vector((0, 0, 0))
    for name in ("lower", "hand"):
        pose = evaluated_rig.pose.bones[name]
        expected += (pose.matrix @ pose.bone.matrix_local.inverted() @ source) * 0.5
    actual = obj.evaluated_get(depsgraph).data.vertices[0].co.copy()
    row = {"label": label, "angle": round(angle, 6), "mesh_error": round((actual - expected).length, 8),
           "key_offset": round(obj.data.shape_keys.key_blocks["Probe correction"].data[0].co.z, 6),
           "calls": list(state["calls"]), "errors": list(state["errors"])}
    state["calls"].clear()
    state["errors"].clear()
    print("PROBE " + json.dumps(row), flush=True)
    assert row["mesh_error"] < 1e-6, row
    assert not row["errors"], row
    return row


def main():
    rig, obj = fixture()
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_post)
    bpy.app.handlers.frame_change_post.append(frame_post)
    bpy.app.handlers.load_post.append(load_post)
    for mode in ("plain", "depsgraph_update", "view_layer_update"):
        state["mode"], state["last"] = mode, None
        for number, degrees in enumerate((10, 70, -40)):
            rig.pose.bones["hand"].rotation_euler.y = math.radians(degrees)
            bpy.context.view_layer.update()
            inspect(f"{mode}:manual:{degrees}")
            inspect(f"{mode}:manual:{degrees}:ensure", use_context_get=True)
    state["mode"], state["last"] = "plain", None
    for frame, degrees in ((1, 0), (2, 80), (3, -40)):
        rig.pose.bones["hand"].rotation_euler.y = math.radians(degrees)
        rig.pose.bones["hand"].keyframe_insert("rotation_euler", frame=frame)
    for frame in (1, 2, 3, 2, 1):
        bpy.context.scene.frame_set(frame)
        inspect(f"frame_set:{frame}")
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Probe camera")
    camera = bpy.data.objects.new("Probe camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0, 1.5, 10)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 3
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_lock_interface = True
    scene.frame_start, scene.frame_end = 1, 3
    with tempfile.TemporaryDirectory(prefix="cd_twist_handler_probe_") as temporary:
        scene.render.filepath = os.path.join(temporary, "frame_")
        bpy.ops.render.render(animation=True)
        inspect("animation_render_finished")
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_post)
        bpy.app.handlers.frame_change_post.remove(frame_post)
        pixel_rows = []
        animated_pixels = []
        for frame in (1, 2, 3):
            scene.frame_set(frame)
            state["last"] = None
            update_correction(scene, bpy.context.evaluated_depsgraph_get(), "static_reference")
            bpy.context.view_layer.update()
            scene.render.filepath = os.path.join(temporary, f"reference_{frame}.png")
            bpy.ops.render.render(write_still=True)
            images = [bpy.data.images.load(path, check_existing=False) for path in (
                os.path.join(temporary, f"frame_{frame:04}.png"), scene.render.filepath)]
            pixels = [array("f", [0.0]) * len(image.pixels) for image in images]
            for image, values in zip(images, pixels):
                image.pixels.foreach_get(values)
            maximum = max(abs(a - b) for a, b in zip(*pixels))
            animated_pixels.append(pixels[0])
            pixel_rows.append({"frame": frame, "pixel_error": maximum})
            for image in images:
                bpy.data.images.remove(image)
        print("RENDER_PIXEL_PROBE " + json.dumps(pixel_rows), flush=True)
        assert all(row["pixel_error"] < 1e-7 for row in pixel_rows), pixel_rows
        assert max(abs(a - b) for a, b in zip(animated_pixels[0], animated_pixels[1])) > 0.1
        assert max(abs(a - b) for a, b in zip(animated_pixels[1], animated_pixels[2])) > 0.1
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_post)
        bpy.app.handlers.frame_change_post.append(frame_post)
        path = os.path.join(temporary, "synthetic.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        bpy.context.scene.frame_set(2)
        inspect("reloaded_frame_set:2")


if __name__ == "__main__":
    main()
