"""Review-only reproduction. Run in factory background Blender, no saved scenes."""
import json
import sys
from pathlib import Path

REPO = Path(r"D:\MyRepository\Blender-addons-by-Randy")
sys.path[:0] = [str(REPO / "addons"), str(REPO / "tests")]
import bpy
import character_designer as cd
import test_shape_key_tools_blender as fixture
from character_designer import shape_key_tools as sk

cd.register()
results = {}
try:
    obj, basis, parent, child = fixture.make_fixture()
    child.select = True
    fixture.select_vertices(obj, (0,))
    results["relative_chain_before"] = [parent.data[0].co.y, child.data[0].co.y]
    results["relative_chain_result"] = sorted(bpy.ops.character_designer.clear_shape_key_selected())
    results["relative_chain_after_first"] = [parent.data[0].co.y, child.data[0].co.y]
    results["relative_chain_residual_first"] = (child.data[0].co - child.relative_key.data[0].co).length
    bpy.ops.object.mode_set(mode="OBJECT")
    parent.value = 0
    child.value = 1
    dg = bpy.context.evaluated_depsgraph_get()
    results["relative_chain_evaluated_y"] = obj.evaluated_get(dg).data.vertices[0].co.y
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.character_designer.clear_shape_key_selected()
    results["relative_chain_after_second"] = [parent.data[0].co.y, child.data[0].co.y]

    obj, basis, parent, child = fixture.make_fixture()
    parent.select = False
    child.select = True
    fixture.select_vertices(obj, (0,))
    bm = sk.bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.verts[0].co.y = 1.5
    sk.bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    results["live_edit_before"] = {"mesh_parent_y": parent.data[0].co.y, "edit_parent_y": bm.verts[0].co.y}
    results["live_edit_result"] = sorted(bpy.ops.character_designer.clear_shape_key_selected())
    bpy.ops.object.mode_set(mode="OBJECT")
    results["live_edit_after_exit"] = [parent.data[0].co.y, child.data[0].co.y]
    results["live_edit_residual"] = (child.data[0].co - parent.data[0].co).length
finally:
    fixture.reset_scene()
    cd.unregister()
Path(__file__).with_suffix(".json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print("SHAPE_KEY_REVIEW " + json.dumps(results))
