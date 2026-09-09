"""Small disposable Blender fixture for the FK hair builder service."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
from character_designer.hair_bones_rig import build_hair_bones

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
verts = [(x, y, z) for z in range(6) for x, y in ((-.1, -.1), (.1, -.1), (.1, .1), (-.1, .1))]
faces = [(4*r+c, 4*r+(c+1)%4, 4*(r+1)+(c+1)%4, 4*(r+1)+c) for r in range(5) for c in range(4)]
data = bpy.data.meshes.new("Hair")
data.from_pydata(verts, [], faces)
obj = bpy.data.objects.new("Hair", data)
bpy.context.collection.objects.link(obj)
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
plans = [{"layers": tuple(tuple(range(4*r, 4*r+4)) for r in range(6)),
          "centers": tuple((0, 0, r) for r in range(6)), "vertices": tuple(range(24)),
          "signature": "smoke", "direction_confirmable": True}]
result = build_hair_bones(bpy.context, obj, plans)
arm = result["armature"]
assert result["created"] == 1 and result["rig_created"]
assert len(arm.data.bones) == 5 and len(obj.modifiers) == 1
first = result["chains"][0]["bones"][0]
arm.pose.bones[first].rotation_mode = "XYZ"
arm.pose.bones[first].rotation_euler.y = .2
bpy.context.view_layer.update()
before = len(arm.data.bones)
assert build_hair_bones(bpy.context, obj, plans)["created"] == 0
assert len(arm.data.bones) == before
print("PASS FK Hair builder smoke")
