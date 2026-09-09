"""Render native control geometry from the saved review copy; never save edits."""
from pathlib import Path
import json
import bpy
from mathutils import Matrix, Vector

root = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root / "Previews/X_Skirt_Setup_0.40.0.blend"),
                        load_ui=False, use_scripts=False)
scene = bpy.context.scene
scene.frame_set(1)
source = bpy.data.objects["Dress"]
record = json.loads(source["character_designer_skirt_v1"])
rig = bpy.data.objects[record["rig"]]
for obj in scene.objects:
    obj.hide_render = obj.name not in {"Dress", "Cosha"}
source.color = (0.13, 0.32, 0.38, 1)
bpy.data.objects["Cosha"].color = (0.64, 0.67, 0.70, 1)
for name in record["cage"]:
    original = bpy.data.objects[name]
    wire = original.copy()
    wire.data = original.data.copy()
    scene.collection.objects.link(wire)
    wire.hide_render = False
    wire.hide_set(False)
    wire.data.bevel_depth = 0.0009
    wire.data.bevel_resolution = 2
    wire.color = (0.96, 0.58, 0.08, 1)

# The control shapes are native bone widgets, which Blender does not render.
# Trace their exact edges into disposable render curves to show the handles.
controls = record["controls"]
names = [controls[key] for key in ("waist", "mid", "hem")]
names += [name for chain in controls["chains"] for name in chain.values()]
for name in names:
    bone = rig.pose.bones[name]
    shape = bone.custom_shape
    if not shape:
        continue
    data = bpy.data.curves.new("Rendered native control", "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = 0.0012 if name in names[:3] else 0.0007
    data.bevel_resolution = 2
    for edge in shape.data.edges:
        spline = data.splines.new("POLY")
        spline.points.add(1)
        for point, index in zip(spline.points, edge.vertices):
            point.co = (*shape.data.vertices[index].co, 1)
    obj = bpy.data.objects.new("Native control preview", data)
    scene.collection.objects.link(obj)
    obj.matrix_world = rig.matrix_world @ bone.matrix
    obj.color = (0.06, 0.72, 0.92, 1)
target = Vector((0, 0.08, 1.06))
direction = Vector((1.25, -2.8, 0.7)).normalized()
data = bpy.data.cameras.new("Skirt detail camera")
camera = bpy.data.objects.new("Skirt detail camera", data)
scene.collection.objects.link(camera)
camera.location = target + direction * 2
camera.rotation_euler = (target-camera.location).to_track_quat("-Z", "Y").to_euler()
data.type = "ORTHO"
data.ortho_scale = 0.48
scene.camera = camera
scene.render.engine = "BLENDER_WORKBENCH"
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "OBJECT"
shading.show_shadows = True
shading.show_cavity = True
shading.cavity_type = "BOTH"
shading.show_object_outline = True
shading.background_type = "WORLD"
scene.world.color = (0.055, 0.065, 0.085)
scene.render.resolution_x, scene.render.resolution_y = 1100, 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(root / "Previews/Skirt_Setup_0.40.0.png")
bpy.ops.render.render(write_still=True)
print("SKIRT_DETAIL_RENDERED", flush=True)
