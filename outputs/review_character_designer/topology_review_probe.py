"""Review-only loss-of-data probe using the repository's disposable fixture."""
import json
import sys
from pathlib import Path
REPO = Path(r"D:\MyRepository\Blender-addons-by-Randy")
sys.path[:0] = [str(REPO / "addons"), str(REPO / "tests")]
import bpy
import character_designer as cd
import test_topology_symmetry_blender as fixture

cd.register()
results = {}
try:
    obj, rig = fixture.make_fixture()
    bpy.ops.object.mode_set(mode="OBJECT")
    original = obj.data
    artist = original.shape_keys.key_blocks["ArtistExpression"]
    artist.value = 0.2
    artist.keyframe_insert(data_path="value", frame=1)
    artist.value = 0.8
    artist.keyframe_insert(data_path="value", frame=20)
    driven = obj.shape_key_add(name="DrivenExpression")
    driven.driver_add("value").driver.expression = "0.37"
    for name, domain in (("crease_edge", "EDGE"), ("bevel_weight_edge", "EDGE"), ("bevel_weight_vertex", "POINT")):
        attr = original.attributes.new(name, "FLOAT", domain)
        for value in attr.data:
            value.value = 0.75
    for edge in original.edges:
        edge.use_edge_sharp = True
    results["before"] = {
        "action": original.shape_keys.animation_data.action.name,
        "drivers": len(original.shape_keys.animation_data.drivers),
        "sharp_edges": sum(edge.use_edge_sharp for edge in original.edges),
        "attributes": [a.name for a in original.attributes],
    }
    bpy.ops.object.mode_set(mode="EDIT")
    results["operator_result"] = sorted(bpy.ops.character_designer.topology_mirror())
    bpy.ops.object.mode_set(mode="OBJECT")
    current = obj.data
    ad = current.shape_keys.animation_data
    results["after"] = {
        "action": ad.action.name if ad and ad.action else None,
        "drivers": len(ad.drivers) if ad else 0,
        "sharp_edges": sum(edge.use_edge_sharp for edge in current.edges),
        "attributes": [a.name for a in current.attributes],
        "original_mesh_users": original.users,
        "mesh_count": len(bpy.data.meshes),
    }
    sample = []
    for frame in (1, 20):
        bpy.context.scene.frame_set(frame)
        sample.append({"frame": frame, "artist_value": current.shape_keys.key_blocks["ArtistExpression"].value,
                       "driven_value": current.shape_keys.key_blocks["DrivenExpression"].value})
    results["after_frame_values"] = sample
finally:
    fixture.reset_scene()
    cd.unregister()
Path(__file__).with_suffix(".json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print("TOPOLOGY_REVIEW " + json.dumps(results))
