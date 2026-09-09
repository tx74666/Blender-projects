"""Grouped FK chains: unequal strips, editable guides, welded roots, native save/reopen."""

import copy
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hair_bones_rig_blender import (
    activate, assert_chains, assert_native_reopen, assert_points, build,
    evaluated_points, expect_atomic_failure, make_armature, plain_snapshot,
    reset, service, weights,
)


def fixture(*, shared=False, three=False):
    coordinates, faces, plans = [], [], []
    specs = ((7, 3, True, 1.2), (11, 4, False, 2.4))
    if three:
        specs += ((9, 5, True, 1.8),)
    for strand, (rows, width, closed, length) in enumerate(specs):
        layers, centers = [], []
        for row in range(rows):
            center = Vector((0.35 + strand * 0.35, 0.05 * strand, 2.2 - length * row / (rows - 1)))
            if shared and row == 0:
                if strand:
                    layers.append(plans[0]["layers"][0])
                    centers.append(plans[0]["centers"][0])
                    continue
                # All shared-root test members use the same 3-vertex profile.
            if shared:
                width, closed = 3, True
            layer = tuple(range(len(coordinates), len(coordinates) + width))
            for corner in range(width):
                offset = (Vector((0.06 * math.cos(corner * math.tau / width),
                                  0.06 * math.sin(corner * math.tau / width), 0))
                          if closed else Vector(((corner / (width - 1) - 0.5) * 0.12, 0, 0)))
                coordinates.append(tuple(center + offset))
            layers.append(layer)
            centers.append(tuple(center))
        for upper, lower in zip(layers, layers[1:]):
            for corner in range(width if closed else width - 1):
                following = (corner + 1) % width
                faces.append((upper[corner], upper[following], lower[following], lower[corner]))
        plans.append({"signature": f"member-{strand}", "layers": tuple(layers),
                      "centers": tuple(centers), "vertices": tuple(i for layer in layers for i in layer),
                      "direction_confirmable": True, "root_tip_rule": "EXPLICIT"})
    # One unselected point must remain attached to the character head.
    coordinates.append((0, 0, 2.4))
    data = bpy.data.meshes.new("GroupedFixtureMesh")
    data.from_pydata(coordinates, [], faces)
    data.update()
    obj = bpy.data.objects.new("GroupedFixture", data)
    bpy.context.scene.collection.objects.link(obj)
    return obj, tuple(plans)


def group(members, *, name="Back Hair", centers=None):
    members = tuple(members)
    if centers is None:
        centers = tuple(tuple(sum((Vector(member["centers"][end]) for member in members), Vector()) / len(members))
                        for end in (0, -1))
    signature = "group:" + hashlib.sha256(repr(sorted(member["signature"] for member in members)).encode()).hexdigest()
    return {"signature": signature, "members": members, "centers": tuple(centers),
            "vertices": tuple(sorted({i for member in members for i in member["vertices"]})),
            "group_id": name, "group_name": name, "direction_confirmable": True,
            "root_tip_rule": "GROUP_GUIDE"}


def test_unequal_open_closed_members_and_guide_repeat():
    reset()
    arm = make_armature()
    obj, members = fixture()
    plan = group(members)
    artist = obj.vertex_groups.new(name="ArtistMask")
    artist.add(list(range(len(obj.data.vertices))), 0.37, "REPLACE")
    artist.lock_weight = True
    before = evaluated_points(obj)
    result = build(obj, (plan,), bone_count=3)
    assert len(result["chains"]) == result["created"] == 1
    assert_chains(obj, (plan,), result, count=3)
    assert_points(evaluated_points(obj), before, "shared chain binds without moving either strand")
    names = result["chains"][0]["bones"]
    for member in members:
        middle = member["layers"][len(member["layers"]) // 2]
        for index in middle:
            actual = weights(obj, (index,))[index]
            assert abs(actual[names[1]] - 1.0) < 1e-6, ("each member's half length", actual)
            assert abs(actual["ArtistMask"] - 0.37) < 1e-6
        for layer in member["layers"]:
            for actual in weights(obj, layer).values():
                assert abs(sum(value for name, value in actual.items() if name != "ArtistMask") - 1.0) < 1e-6
        for actual in weights(obj, member["layers"][0]).values():
            assert actual["spine.006"] == 1.0
    record = service._read_records(obj)
    assert record["version"] == 2 and record["chains"][0]["layers"] == []
    assert len(record["chains"][0]["members"]) == 2
    arm.pose.bones[names[0]].rotation_mode = "XYZ"
    arm.pose.bones[names[0]].rotation_euler.x = 0.3
    after = evaluated_points(obj)
    for member in members:
        assert (after[member["layers"][-1][0]] - before[member["layers"][-1][0]]).length > 0.1
        assert_points(tuple(after[i] for i in member["layers"][0]),
                      tuple(before[i] for i in member["layers"][0]), "individual roots stay attached")
    repeated = build(obj, (copy.deepcopy(plan),), bone_count=3)
    assert repeated["created"] == 0 and repeated["reused"] == 1
    assert_points(evaluated_points(obj), after, "repeat preserves artist FK pose")
    changed = dict(plan, centers=(plan["centers"][0], tuple(Vector(plan["centers"][-1]) + Vector((0.1, 0, 0)))))
    expect_atomic_failure(obj, (changed,), "changed guide cannot silently reuse old bones", bone_count=3)
    changed = copy.deepcopy(plan)
    changed["members"][0]["centers"] = tuple(
        tuple(Vector(point) + Vector((0.1, 0, 0))) for point in changed["members"][0]["centers"])
    expect_atomic_failure(obj, (changed,), "changed member arc cannot silently reuse old weights", bone_count=3)
    return obj, arm, members, result


def test_shared_roots_across_and_inside_groups():
    reset()
    arm = make_armature()
    obj, members = fixture(shared=True, three=True)
    first, second = group(members[:2]), group(members[2:], name="Accent")
    before = evaluated_points(obj)
    built = build(obj, (first,), bone_count=3)
    arm.pose.bones[built["chains"][0]["bones"][0]].rotation_mode = "XYZ"
    arm.pose.bones[built["chains"][0]["bones"][0]].rotation_euler.x = 0.4
    first_bent = evaluated_points(obj)
    appended = build(obj, (second,), bone_count=3)
    assert appended["created"] == 1 and appended["armature"] is arm
    assert_points(evaluated_points(obj), first_bent, "append shared-root group preserves existing pose")
    arm.pose.bones[appended["chains"][0]["bones"][0]].rotation_mode = "XYZ"
    arm.pose.bones[appended["chains"][0]["bones"][0]].rotation_euler.x = -0.3
    both = evaluated_points(obj)
    assert_points(tuple(both[i] for i in first["vertices"]), tuple(first_bent[i] for i in first["vertices"]),
                  "separate groups deform independently")
    root = members[0]["layers"][0]
    assert_points(tuple(both[i] for i in root), tuple(before[i] for i in root), "welded common root remains fixed")
    assert all(value == {"spine.006": 1.0} for value in weights(obj, root).values())


def test_group_preflight_and_commit_rollback():
    reset()
    make_armature()
    obj, members = fixture()
    duplicate = group((members[0], members[0]))
    expect_atomic_failure(obj, (duplicate,), "duplicate member")
    expect_atomic_failure(obj, (group(members), members[0]), "member also assigned its own chain")
    bad = dict(members[1], layers=(members[1]["layers"][0], members[0]["layers"][1]) + members[1]["layers"][2:])
    bad["vertices"] = tuple(i for layer in bad["layers"] for i in layer)
    expect_atomic_failure(obj, (group((members[0], bad)),), "interior overlap")
    obj.modifiers.new("ArtistMirror", "MIRROR")
    original = service._validate_owned
    calls = 0

    def fail_commit(*args, **kwargs):
        nonlocal calls
        value = original(*args, **kwargs)
        calls += 1
        if calls == 2:
            assert json.loads(obj[service.RECORD_KEY])["version"] == 2
            raise RuntimeError("Injected grouped metadata failure")
        return value

    service._validate_owned = fail_commit
    try:
        expect_atomic_failure(obj, (group(members),), "group commit restores original mesh, mirror and rig")
    finally:
        service._validate_owned = original


def test_group_native_mirror_head_and_reopen():
    reset()
    arm = make_armature()
    obj, members = fixture()
    mirror = obj.modifiers.new("ArtistMirror", "MIRROR")
    mirror.use_mirror_merge = False
    before = evaluated_points(obj)
    result = build(obj, (group(members),), bone_count=3)
    assert_points(evaluated_points(obj), before, "mirror rest binding")
    first = arm.pose.bones[result["chains"][0]["bones"][0]]
    first.rotation_mode = "XYZ"
    first.rotation_euler.x = 0.3
    bent = evaluated_points(obj)
    count = len(obj.data.vertices)
    assert_points(tuple(Vector((-p.x, p.y, p.z)) for p in bent[:count]), bent[count:], "group mirror symmetry")
    head = arm.pose.bones[result["parent_bone"]]
    head_before = head.matrix.copy()
    head.rotation_mode = "XYZ"
    head.rotation_euler.y = 0.4
    head.location.x = 0.2
    bpy.context.view_layer.update()
    delta = arm.matrix_world @ head.matrix @ head_before.inverted() @ arm.matrix_world.inverted()
    assert_points(evaluated_points(obj), tuple(delta @ point for point in bent), "all grouped mirrored hair follows head")
    assert_native_reopen(obj, arm, members, result)


if __name__ == "__main__":
    for test in (test_unequal_open_closed_members_and_guide_repeat,
                 test_shared_roots_across_and_inside_groups,
                 test_group_preflight_and_commit_rollback,
                 test_group_native_mirror_head_and_reopen):
        test()
        print("PASS", test.__name__)
    print("HAIR_BONES_GROUPED_RIG_TESTS_OK")
