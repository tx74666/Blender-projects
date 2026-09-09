"""Use canonical sources for the existing real-Hair3 integration check."""
from pathlib import Path
import runpy
import sys

canonical = Path(r"D:\MyRepository\Blender-addons-by-Randy\addons")
sys.path.insert(0, str(canonical))
import character_designer
import bpy
assert character_designer.bl_info["version"] == (0, 40, 3)
assert Path(character_designer.__file__).resolve().is_relative_to(canonical.resolve())
assert bpy.app.background
assert Path(bpy.data.filepath).name == "X.hair-independent-input.blend"
# Reveal only the source collection path in this private, unsaved test process.
source = bpy.data.objects["Hair3"]
def reveal_source(layer, path=()):
    path = (*path, layer)
    if source.name in layer.collection.objects:
        for item in path:
            item.hide_viewport = False
    for child in layer.children:
        reveal_source(child, path)
reveal_source(bpy.context.view_layer.layer_collection)
source.hide_set(False)
bpy.context.view_layer.update()
assert source.visible_get(), "Source must be visible for the Edit Mode integration fixture"
runpy.run_path(str(Path(__file__).resolve().parents[1] / "tests" / "test_real_x_hair_mirror_controls_blender.py"), run_name="__main__")
