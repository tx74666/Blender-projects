"""Verify saved review copy using native Blender evaluation without the add-on."""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Previews" / "X_Skirt_Setup_0.40.0.blend"),
                        load_ui=False, use_scripts=False)
source = bpy.data.objects["Dress"]
record = json.loads(source["character_designer_skirt_v1"])
result = json.loads(source["character_designer_skirt_last_bake"])
bpy.data.collections[result["collection"]].hide_viewport = False
baked = bpy.data.objects[result["mesh"]]
proxy = bpy.data.objects[record["physics"]["proxy"]]
cloth = next(m for m in proxy.modifiers if m.type == "CLOTH")
print("REOPEN_CACHE", cloth.point_cache.is_baked, cloth.point_cache.info, flush=True)

def points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ v.co for v in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()

errors = []
for frame in (61, 1, 31, 16, 46, 8, 54):
    bpy.context.scene.frame_set(frame)
    error = max((a-b).length for a,b in zip(points(source), points(baked)))
    print("REOPEN_MATCH", frame, error, flush=True)
    errors.append(error)
assert max(errors) < 2e-4, errors
print("REAL_X_SKIRT_REOPEN_OK", flush=True)
