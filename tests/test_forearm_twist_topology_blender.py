"""Read-only topology tests; optionally inspect saved X.blend with --real-x."""

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix


PROJECT_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "forearm_twist_topology",
    PROJECT_ROOT / "addons" / "character_designer" / "forearm_twist_topology.py",
)
topology = importlib.util.module_from_spec(spec)
spec.loader.exec_module(topology)


def make_fixture(*, open_seam=False, triangulate=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = bpy.data.armatures.new("TwistTopologyRig")
    armature = bpy.data.objects.new("TwistTopologyRig", data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    lower = data.edit_bones.new("forearm.L")
    lower.head, lower.tail = (0, 0, 0), (0, 1, 0)
    hand = data.edit_bones.new("hand.L")
    hand.head, hand.tail, hand.parent = (0, 1, 0), (0, 1.3, 0), lower
    bpy.ops.object.mode_set(mode="OBJECT")
    count = 8
    positions = [-0.1, 0.0, 0.25, 0.5, 0.75, 1.0, 1.1]
    vertices = [
        (0.1 * math.cos(math.tau * i / count), t, 0.1 * math.sin(math.tau * i / count))
        for t in positions
        for i in range(count)
    ]
    faces = []
    for ring in range(len(positions) - 1):
        for i in range(count):
            if open_seam and i == count - 1:
                continue
            quad = (ring * count + i, ring * count + (i + 1) % count,
                    (ring + 1) * count + (i + 1) % count, (ring + 1) * count + i)
            if triangulate:
                faces.extend((quad[:3], (quad[0], quad[2], quad[3])))
            else:
                faces.append(quad)
    mesh = bpy.data.meshes.new("TwistTopologyTube")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new("TwistTopologyTube", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.vertex_groups.new(name="forearm.L").add(list(range(len(vertices))), 1.0, "REPLACE")
    # Obsolete groups must not dilute support: they have no deform bone.
    obj.vertex_groups.new(name="unused_forearm_group").add(list(range(len(vertices))), 1.0, "REPLACE")
    obj.matrix_world = armature.matrix_world = Matrix.Translation((2, -1, 3)) @ Matrix.Scale(0.78, 4)
    bpy.context.view_layer.update()
    return obj, armature


def assert_closed(obj, rings):
    edge_keys = {tuple(sorted(edge.vertices)) for edge in obj.data.edges}
    for ring in rings:
        ids = ring["vertices"]
        assert len(set(ids)) == len(ids) >= 4
        for index, first in enumerate(ids):
            assert tuple(sorted((first, ids[(index + 1) % len(ids)]))) in edge_keys


def main():
    obj, armature = make_fixture()
    rings = topology.detect_rings(obj, armature, "forearm.L", "hand.L")
    assert len(rings) == 5, rings
    assert all(len(ring["vertices"]) == 8 for ring in rings)
    assert all(abs(ring["position"] - expected) < 1.0e-6
               for ring, expected in zip(rings, (0.0, 0.25, 0.5, 0.75, 1.0)))
    assert_closed(obj, rings)
    assert topology.detect_rings(obj, armature, "forearm.R", "hand.R") == []
    # Detection uses Basis even while a different key is displayed/edited.
    obj.shape_key_add(name="Basis")
    expression = obj.shape_key_add(name="Expression")
    for vertex in expression.data:
        vertex.co.x += 5.0
    expression.value = 1.0
    obj.active_shape_key_index = 1
    assert topology.detect_rings(obj, armature, "forearm.L", "hand.L") == rings

    obj, armature = make_fixture(open_seam=True)
    assert topology.detect_rings(obj, armature, "forearm.L", "hand.L") == []
    obj, armature = make_fixture(triangulate=True)
    assert topology.detect_rings(obj, armature, "forearm.L", "hand.L") == []

    result = {"synthetic": "PASS"}
    if "--real-x" in sys.argv:
        blend_path = PROJECT_ROOT / "X.blend"
        before = (blend_path.stat().st_size, blend_path.stat().st_mtime_ns)
        bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False, use_scripts=False)
        obj, armature = bpy.data.objects["Cosha"], bpy.data.objects["CoshaRig"]
        real_rings = {}
        for side in ("L", "R"):
            rings = topology.detect_rings(obj, armature, "forearm." + side, "hand." + side)
            assert len(rings) >= 3, (side, rings)
            assert rings[0]["position"] < 0.26 and rings[-1]["position"] > 0.83
            assert_closed(obj, rings)
            real_rings[side] = [
                {"position": ring["position"], "count": len(ring["vertices"])}
                for ring in rings
            ]
        left_ids = {i for r in topology.detect_rings(obj, armature, "forearm.L", "hand.L") for i in r["vertices"]}
        right_ids = {i for r in topology.detect_rings(obj, armature, "forearm.R", "hand.R") for i in r["vertices"]}
        assert left_ids.isdisjoint(right_ids)
        assert before == (blend_path.stat().st_size, blend_path.stat().st_mtime_ns)
        result["real_x"] = real_rings
    print("FOREARM_TWIST_TOPOLOGY_TEST=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
