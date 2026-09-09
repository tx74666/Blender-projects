"""Mode/reload recovery of generated strand partitions; disposable scene only."""

import importlib
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
sys.path.insert(0, str(ROOT / "tests"))
from character_designer import hair_bones_topology as topology, hair_bones_rig as rig
from test_hair_bones_topology_blender import Fixture, select
from test_hair_bones_rig_blender import activate, make_armature


def main():
    fixture = Fixture()
    fixture.tube(sides=3, origin=(-0.5, 0, 1.8))
    fixture.tube(sides=5, origin=(0.5, 0, 1.8))
    obj = fixture.object("OwnedSelectionHair")
    armature = make_armature("OwnedSelectionRig")
    activate(obj, "EDIT")
    select(obj, ())
    _, plans = topology.select_strands(bpy.context)
    assert len(plans) == 2
    result = rig.build_hair_bones(bpy.context, obj, plans, bone_count=3,
                                armature=armature, parent_bone="spine.006")
    assert result["created"] == 2 and obj.mode == "OBJECT"
    signatures = {plan["signature"] for plan in plans}
    bone_count = len(armature.data.bones)
    activate(obj, "EDIT")
    _, restored = topology.selected_strands(bpy.context)
    assert {plan["signature"] for plan in restored} == signatures
    repeat = rig.build_hair_bones(bpy.context, obj, restored, bone_count=3,
                                 armature=armature, parent_bone="spine.006")
    assert repeat["created"] == 0 and len(armature.data.bones) == bone_count
    activate(obj, "EDIT")
    importlib.reload(topology)
    assert not topology._SELECTION_CACHE
    _, reloaded = topology.selected_strands(bpy.context)
    assert {plan["signature"] for plan in reloaded} == signatures
    expected = {plan["signature"]: plan["centers"] for plan in reloaded}
    delta = Vector((0.01, -0.02, 0.03))
    bm = bmesh.from_edit_mesh(obj.data)
    for vertex in bm.verts:
        vertex.co += delta
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    _, moved = topology.selected_strands(bpy.context)
    for plan in moved:
        for actual, old in zip(plan["centers"], expected[plan["signature"]]):
            assert (Vector(actual) - Vector(old) - delta).length < 2.0e-6, "Owned recovery reused stale centers"
    for vertex in bm.verts:
        vertex.co -= delta
    bm.edges.remove(next(iter(bm.edges)))
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=True)
    try:
        topology.selected_strands(bpy.context)
    except topology.HairTopologyError as exc:
        assert "topology" in str(exc).lower(), str(exc)
    else:
        raise AssertionError("Owned recovery accepted changed connectivity")
    print("HAIR_OWNED_SELECTION_PASS=mode roundtrip, repeat build, module reload, current centers, changed-topology refusal", flush=True)


if __name__ == "__main__":
    main()
