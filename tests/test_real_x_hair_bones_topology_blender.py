"""Read-only real-X discovery check; load X on Blender's command line."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
from character_designer import hair_bones_topology as topology


def main():
    path = Path(bpy.data.filepath)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    count_objects = len(bpy.data.objects)
    results = []
    try:
        for name in ("Hair1", "Hair2", "Hair3"):
            obj = bpy.data.objects[name]
            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            for item in bpy.context.selected_objects:
                item.select_set(False)
            obj.hide_set(False)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            source = (tuple(tuple(v.co) for v in obj.data.vertices),
                      tuple(tuple(e.vertices) for e in obj.data.edges),
                      tuple(tuple(f.vertices) for f in obj.data.polygons),
                      tuple((m.name, m.type) for m in obj.modifiers))
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="DESELECT")
            result_obj, plans = topology.discover_strands(bpy.context)
            assert result_obj == obj
            assert plans, name + ": no strand found"
            assert len(plans) >= {"Hair1": 1, "Hair2": 9, "Hair3": 3}[name], (name, len(plans))
            if name == "Hair2":
                assert len(plans) == 9, "The nine real islands must each yield one strand"
            if name == "Hair3":
                assert {(268,), (324,), (400,)}.issubset({plan["layers"][-1] for plan in plans}), "Welded point-tip strands must remain separately identifiable"
            assert len({plan["signature"] for plan in plans}) == len(plans)
            for index, first in enumerate(plans):
                assert len(first["layers"]) == len(first["centers"])
                assert len(first["vertices"]) < len(obj.data.vertices), "A joined hair sheet became one strand"
                for second in plans[index + 1:]:
                    overlap = set(first["vertices"]) & set(second["vertices"])
                    assert not overlap or (overlap.issubset(first["layers"][0]) and overlap.issubset(second["layers"][0]))
            result_obj, selected = topology.select_strands(bpy.context)
            assert selected == plans
            assert topology.selected_strands(bpy.context)[1] == plans
            bm = bmesh.from_edit_mesh(obj.data)
            actual_selected = {v.index for v in bm.verts if v.select}
            expected_selected = {i for plan in plans for i in plan["vertices"]}
            assert actual_selected == expected_selected, {"object": name, "missing": sorted(expected_selected - actual_selected), "extra": sorted(actual_selected - expected_selected), "mode":tuple(bpy.context.tool_settings.mesh_select_mode)}
            record = {"object": name, "count": len(plans), "coverage": len({i for p in plans for i in p["vertices"]}),
                      "plans": [{key: plan[key] for key in ("root_tip_rule", "aspect_ratio", "length_world", "profile_kind", "direction_confirmable")}
                                | {"root_layer": plan["layers"][0], "tip_layer": plan["layers"][-1],
                                   "layers": len(plan["layers"]), "vertices": len(plan["vertices"])} for plan in plans]}
            results.append(record)
            print("REAL_X_HAIR_TOPOLOGY=" + json.dumps(record), flush=True)
            bpy.ops.object.mode_set(mode="OBJECT")
            assert source == (tuple(tuple(v.co) for v in obj.data.vertices),
                              tuple(tuple(e.vertices) for e in obj.data.edges),
                              tuple(tuple(f.vertices) for f in obj.data.polygons),
                              tuple((m.name, m.type) for m in obj.modifiers))
        assert len(bpy.data.objects) == count_objects
        print("REAL_X_HAIR_TOPOLOGY_PASS=" + json.dumps({r["object"]: r["count"] for r in results}), flush=True)
    finally:
        after = hashlib.sha256(path.read_bytes()).hexdigest()
        assert before == after
        print("REAL_X_HAIR_INPUT_UNCHANGED=" + after, flush=True)


if __name__ == "__main__":
    main()
