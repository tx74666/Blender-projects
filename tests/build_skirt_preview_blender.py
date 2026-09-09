"""Create a review copy of saved X without editing its source blend."""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
import character_designer as cd
from character_designer import skirt_rig, skirt_physics


def checksum(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def evaluated_positions(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ v.co for v in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


source_path = ROOT / "X.blend"
before = checksum(source_path)
bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False, use_scripts=False)
cd.register()
scene = bpy.context.scene
scene.frame_set(1)
source = bpy.data.objects["Dress"]
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
for obj in bpy.context.selected_objects:
    obj.select_set(False)
source.hide_set(False)
source.select_set(True)
bpy.context.view_layer.objects.active = source
original_positions = evaluated_positions(source)
record = skirt_rig.build_skirt(bpy.context, source, armature=bpy.data.objects["CoshaRig"])
rig = bpy.data.objects[record["rig"]]
rest_positions = evaluated_positions(source)
rest_error = max((a - b).length for a, b in zip(original_positions, rest_positions))
record = skirt_physics.add_physics(bpy.context, source)
first_positions = evaluated_positions(source)
physics_rest_error = max((a - b).length for a, b in zip(original_positions, first_positions))
print("REAL_X_BUILD", json.dumps({"rest_error_world": rest_error, "physics_frame1_error_world": physics_rest_error,
                                 "bones": len(rig.data.bones), "physics": record["physics"]}), flush=True)
# A gentle loop demonstrates controls and secondary sway without changing the character's original action.
waist = rig.pose.bones[record["controls"]["waist"]]
hem = rig.pose.bones[record["controls"]["hem"]]
for frame, waist_angle, hem_angle in [(1, 0, 0), (16, 0.09, -0.06), (31, 0, 0), (46, -0.09, 0.06), (61, 0, 0)]:
    waist.rotation_euler[1] = waist_angle
    hem.rotation_euler[1] = hem_angle
    waist.keyframe_insert("rotation_euler", frame=frame)
    hem.keyframe_insert("rotation_euler", frame=frame)
scene.frame_start, scene.frame_end = 1, 61
steps = skirt_physics.bake_steps(bpy.context, source, 1, 61, "ANIMATION")
while True:
    try:
        completed, total, message = next(steps)
        if completed == 1 or completed % 10 == 0:
            print("BAKE_PROGRESS", completed, total, message, flush=True)
    except StopIteration as done:
        result = done.value
        break
source["character_designer_skirt_last_bake"] = json.dumps(result)
print("REAL_X_BAKED", json.dumps(result), flush=True)
collection = bpy.data.collections[result["collection"]]
collection.hide_viewport = False
baked = bpy.data.objects[result["mesh"]]
errors = []
for frame in (61, 1, 31, 16, 46, 8, 54):
    scene.frame_set(frame)
    a, b = evaluated_positions(source), evaluated_positions(baked)
    error = max((x-y).length for x,y in zip(a,b))
    errors.append(error)
    print("BAKED_MESH_MATCH",frame,error,flush=True)
assert max(errors) < 2e-4, errors
collection.hide_viewport = True
scene.frame_set(1)
bpy.context.window_manager.character_designer.ui_page = "CLOTHING"
bpy.context.window_manager.character_designer_skirt.source = source
skirt_rig.select_controls(bpy.context, source)
# Store a useful waist-to-knee viewport framing in the review copy.
target = Vector((0.0, 0.08, 1.08))
view_direction = Vector((1.45, -2.8, 1.1)).normalized()
orientation = view_direction.to_track_quat("Z", "Y")
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_location = target
            space.region_3d.view_rotation = orientation
            space.region_3d.view_distance = 0.92
            space.region_3d.view_perspective = "ORTHO"
            space.overlay.show_extras = False
            space.show_region_ui = True
preview_dir = ROOT / "Previews"
preview_dir.mkdir(exist_ok=True)
output = preview_dir / "X_Skirt_Setup_0.40.0.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(output))
print("PREVIEW_SAVED", output, flush=True)
# Render-only geometry makes the actual native control wire readable in an image.
# These copies are made after saving and are not part of the review blend.
skirt_rig._activate(bpy.context, source)
visible = {source, bpy.data.objects.get("Cosha")}
for obj in scene.objects:
    obj.hide_render = obj not in visible
source.color = (0.13, 0.32, 0.38, 1)
bpy.data.objects["Cosha"].color = (0.64, 0.67, 0.70, 1)
for name in record["cage"]:
    original = bpy.data.objects.get(name)
    if not original:
        continue
    wire = original.copy()
    wire.data = original.data.copy()
    scene.collection.objects.link(wire)
    wire.name = "Preview wire " + original.name
    wire.hide_render = False
    wire.hide_set(False)
    wire.data.bevel_depth = 0.0013
    wire.data.bevel_resolution = 2
    wire.color = (0.98, 0.62, 0.12, 1)
cam_data = bpy.data.cameras.new("Skirt review camera")
camera = bpy.data.objects.new("Skirt review camera", cam_data)
scene.collection.objects.link(camera)
camera.location = target + view_direction * 2
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
cam_data.type = "ORTHO"
cam_data.ortho_scale = 0.64
scene.camera = camera
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.display.shading.show_object_outline = True
scene.display.shading.background_type = "WORLD"
scene.world.color = (0.055, 0.065, 0.085)
scene.render.resolution_x = 1100
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(preview_dir / "Skirt_Setup_0.40.0.png")
bpy.ops.render.render(write_still=True)
assert checksum(source_path) == before, "Original X file changed"
print("REAL_X_SKIRT_PREVIEW_OK",flush=True)
