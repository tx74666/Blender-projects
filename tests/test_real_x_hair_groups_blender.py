"""Exercise captured groups on X's actual strands without saving the input."""

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
from character_designer import hair_bones_groups as groups
from character_designer import hair_bones_topology as topology


def main():
    path = Path(bpy.data.filepath)
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    results = []
    try:
        for name in ("Hair1", "Hair2", "Hair3"):
            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            obj = bpy.data.objects[name]
            obj.hide_set(False)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="DESELECT")
            _, discovered = topology.select_strands(bpy.context)
            assert discovered
            groups.capture_plans(obj, discovered)
            _, single = groups.build_plans(bpy.context, mode="PER_STRAND")
            assert len(single) == len(discovered)
            assert {p["signature"] for p in single} == {p["signature"] for p in discovered}
            for before, after in zip(discovered, single):
                assert before["layers"] == after["layers"]
                assert before["centers"] == after["centers"]
            if len(single) >= 2:
                group_id = groups.group_selected(bpy.context, "All Real Strands")
                _, merged = groups.build_plans(bpy.context, mode="GROUPED")
                assert len(merged) == 1 and len(merged[0]["members"]) == len(single)
                assert set(merged[0]["vertices"]) == {index for p in single for index in p["vertices"]}
                guide = groups.create_group_guide(bpy.context, group_id)
                bpy.context.view_layer.update()
                _, guided = groups.build_plans(bpy.context, mode="GROUPED")
                assert guided[0]["root_tip_rule"] == "GROUP_GUIDE"
                assert len(guided[0]["members"]) == len(single)
                bm = bmesh.from_edit_mesh(obj.data)
                tip = single[0]["layers"][-1][0]
                for face in bm.faces:
                    face.select_set(False)
                for edge in bm.edges:
                    edge.select_set(False)
                for vertex in bm.verts:
                    vertex.select_set(vertex.index == tip)
                bmesh.update_edit_mesh(obj.data)
                groups.split_selected(bpy.context)
                _, split = groups.build_plans(bpy.context, mode="GROUPED")
                assert len(split) == 2
                assert sorted(len(p["members"]) for p in split) == sorted((1, len(single) - 1))
            results.append({"object": name, "strands": len(single), "status": "passed"})
            print("REAL_X_HAIR_GROUP=" + json.dumps(results[-1]), flush=True)
        print("REAL_X_HAIR_GROUP_RESULT=passed", flush=True)
    finally:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == original
        print("REAL_X_HAIR_GROUP_INPUT_UNCHANGED=" + original, flush=True)


if __name__ == "__main__":
    main()
