"""Strict, read-only ring symmetry tests, including the saved X character."""

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
from character_designer.forearm_twist_symmetry import mirror_ring_pairs
from character_designer.forearm_twist_topology import detect_rings


def capture(obj, armature, side):
    return {"chain": [name + "." + side for name in ("upper_arm", "forearm", "hand")],
            "rings": detect_rings(obj, armature, "forearm." + side, "hand." + side)}


def fixture(*, duplicate=False, shape_keys=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = bpy.data.armatures.new("MirrorRig")
    armature = bpy.data.objects.new("MirrorRig", data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for side, x in (("L", 1.0), ("R", -1.0)):
        parent = None
        for stem, start, end in (("upper_arm", -0.5, 0.0), ("forearm", 0.0, 1.0), ("hand", 1.0, 1.3)):
            bone = data.edit_bones.new(stem + "." + side)
            bone.head = (x, start, 0)
            bone.tail = (x, end, 0)
            bone.parent = parent
            parent = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    positions = [-0.1, 0.0, 0.25, 0.5, 0.75, 1.0, 1.1]
    left = [(1.0 + 0.1 * math.cos(math.tau * index / 8), position, 0.1 * math.sin(math.tau * index / 8))
            for position in positions for index in range(8)]
    count = len(left)
    vertices = left + [(-x, y, z) for x, y, z in reversed(left)]
    faces = []
    for ring in range(len(positions) - 1):
        for index in range(8):
            face = (ring * 8 + index, ring * 8 + (index + 1) % 8,
                    (ring + 1) * 8 + (index + 1) % 8, (ring + 1) * 8 + index)
            faces.append(face)
            faces.append(tuple(2 * count - 1 - index for index in reversed(face)))
    if duplicate:
        vertices.append(vertices[2 * count - 1 - 16])
    mesh = bpy.data.meshes.new("MirrorSleeves")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new("MirrorSleeves", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.vertex_groups.new(name="forearm.L").add(list(range(count)), 1.0, "REPLACE")
    obj.vertex_groups.new(name="forearm.R").add(list(range(count, 2 * count)), 1.0, "REPLACE")
    if shape_keys:
        obj.shape_key_add(name="Basis")
        expression = obj.shape_key_add(name="Expression")
        for point in expression.data:
            point.co.z += 0.3
        expression.value = 0.8
        obj.active_shape_key_index = 1
    transform = Matrix.Translation((2, -1, 3)) @ Matrix.Rotation(0.7, 4, "Z") @ Matrix.Scale(0.78, 4)
    obj.matrix_world = armature.matrix_world = transform
    armature.pose.bones["hand.L"].rotation_mode = "XYZ"
    armature.pose.bones["hand.L"].rotation_euler.y = 0.8
    armature.pose.bones["hand.R"].rotation_mode = "XYZ"
    armature.pose.bones["hand.R"].rotation_euler.x = -0.4
    bpy.context.view_layer.update()
    return obj, armature, capture(obj, armature, "L"), capture(obj, armature, "R")


def assert_rejected(obj, armature, source, target):
    try:
        mirror_ring_pairs(obj, armature, source, target)
    except ValueError as error:
        assert str(error) and len(str(error)) < 180
        return str(error)
    raise AssertionError("Invalid symmetry input was accepted")


def signature(obj, armature):
    return {
        "vertices": [tuple(vertex.co) for vertex in obj.data.vertices],
        "keys": [] if not obj.data.shape_keys else [(key.name, key.value, [tuple(point.co) for point in key.data])
                                                    for key in obj.data.shape_keys.key_blocks],
        "weights": [[(group.group, group.weight) for group in vertex.groups] for vertex in obj.data.vertices],
        "pose": [(bone.name, bone.rotation_mode, tuple(bone.rotation_euler), tuple(bone.rotation_quaternion), tuple(bone.location))
                 for bone in armature.pose.bones],
        "modifiers": [(mod.name, mod.type) for mod in obj.modifiers],
        "bone_names": [bone.name for bone in armature.data.bones],
    }


def main():
    obj, armature, source, target = fixture()
    assert len(source["rings"]) == len(target["rings"]) == 5
    target["rings"].reverse()
    for ring in target["rings"]:
        ring["vertices"].reverse()
    before = signature(obj, armature)
    records_before = copy.deepcopy((source, target))
    pairs = mirror_ring_pairs(obj, armature, source, target)
    assert pairs == [(index, 4 - index) for index in range(5)], pairs
    assert signature(obj, armature) == before and (source, target) == records_before
    errors = {}
    bad_target = copy.deepcopy(target)
    bad_target["rings"][0]["vertices"][1], bad_target["rings"][0]["vertices"][3] = bad_target["rings"][0]["vertices"][3], bad_target["rings"][0]["vertices"][1]
    errors["wrong_cycle"] = assert_rejected(obj, armature, source, bad_target)
    bad_target = copy.deepcopy(target)
    bad_target["rings"][0]["position"] += 0.01
    errors["stale_position"] = assert_rejected(obj, armature, source, bad_target)
    index = target["rings"][1]["vertices"][0]
    obj.data.shape_keys.reference_key.data[index].co.x += 0.001
    errors["asymmetric_basis"] = assert_rejected(obj, armature, source, target)
    obj, armature, source, target = fixture(duplicate=True)
    errors["ambiguous_vertex"] = assert_rejected(obj, armature, source, target)
    obj, armature, source, target = fixture(shape_keys=False)
    vertices = [tuple(vertex.co) for vertex in obj.data.vertices]
    faces = [tuple(face.vertices) for face in obj.data.polygons]
    first, second = target["rings"][2]["vertices"][0], target["rings"][2]["vertices"][2]
    obj.data.clear_geometry()
    obj.data.from_pydata(vertices, [(first, second)], faces)
    errors["changed_surface_topology"] = assert_rejected(obj, armature, source, target)
    obj, armature, source, target = fixture()
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    armature.data.edit_bones["hand.R"].tail.z += 0.01
    bpy.ops.object.mode_set(mode="OBJECT")
    errors["asymmetric_rest_bones"] = assert_rejected(obj, armature, source, target)

    blend_path = ROOT / "X.blend"
    before_digest = hashlib.sha256(blend_path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False, use_scripts=False)
    obj = bpy.data.objects["Cosha"]
    armature = obj.modifiers[0].object
    source, target = capture(obj, armature, "L"), capture(obj, armature, "R")
    before = signature(obj, armature)
    pairs = mirror_ring_pairs(obj, armature, source, target)
    assert pairs == [(index, index) for index in range(7)], pairs
    assert mirror_ring_pairs(obj, armature, target, source) == pairs
    assert signature(obj, armature) == before
    assert hashlib.sha256(blend_path.read_bytes()).hexdigest() == before_digest
    print("FOREARM_TWIST_SYMMETRY_TEST=" + json.dumps({"synthetic": "PASS", "rejections": errors,
                                                     "real_x_pairs": pairs, "read_only": True}, sort_keys=True))


if __name__ == "__main__":
    main()
