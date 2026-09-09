"""Read-only Basis/topology symmetry audit of saved X; never saves a blend."""

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".codex-backups" / "forearm-twist-probe"
sys.path.insert(0, str(ROOT / "addons"))
from character_designer.forearm_twist_topology import detect_rings


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sleeve(obj, armature, side, rings):
    lower_name, hand_name = "forearm." + side, "hand." + side
    group_names = {group.index: group.name for group in obj.vertex_groups
                   if group.name in armature.data.bones and armature.data.bones[group.name].use_deform}
    weights = {}
    for vertex in obj.data.vertices:
        values = {group_names[group.group]: group.weight for group in vertex.groups if group.group in group_names and group.weight > 0}
        total = sum(values.values())
        weights[vertex.index] = {name: weight / total for name, weight in values.items()} if total else {}
    lower = armature.data.bones[lower_name]
    axis = (lower.tail_local - lower.head_local).normalized()
    to_arm = armature.matrix_world.inverted() @ obj.matrix_world
    basis = obj.data.shape_keys.reference_key
    positions = {index: (to_arm @ point.co - lower.head_local).dot(axis) / lower.length for index, point in enumerate(basis.data)}
    last = max(ring["position"] for ring in rings)
    corridor = {index for index, position in positions.items() if position >= 0 and (
        position <= last and weights[index].get(lower_name, 0) + weights[index].get(hand_name, 0) > 0.5
        or position > 1 and weights[index].get(lower_name, 0) > 1e-6)}
    selected = {index for ring in rings for index in ring["vertices"]}
    adjacency = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        first, second = edge.vertices
        adjacency[first].append(second)
        adjacency[second].append(first)
    pending = list(selected)
    while pending:
        index = pending.pop()
        for neighbor in adjacency[index]:
            if neighbor in corridor and neighbor not in selected:
                selected.add(neighbor)
                pending.append(neighbor)
    return selected, weights, positions


def main():
    blend_path = ROOT / "X.blend"
    before = file_digest(blend_path)
    bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False, use_scripts=False)
    obj = bpy.data.objects["Cosha"]
    armature = obj.modifiers[0].object
    basis = obj.data.shape_keys.reference_key
    coordinates = [point.co.copy() for point in basis.data]
    to_arm = armature.matrix_world.inverted() @ obj.matrix_world
    tree = KDTree(len(coordinates))
    for index, point in enumerate(coordinates):
        tree.insert(point, index)
    tree.balance()
    extents = Vector(tuple(max(point[axis] for point in coordinates) - min(point[axis] for point in coordinates) for axis in range(3)))
    tolerance = max(extents.length * 1e-6, 1e-7)
    rings = {side: detect_rings(obj, armature, "forearm." + side, "hand." + side) for side in ("L", "R")}
    sleeves = {side: sleeve(obj, armature, side, rings[side]) for side in ("L", "R")}
    local_region = sleeves["L"][0] | sleeves["R"][0]
    mapping = {}
    distances = {}
    ambiguous = []
    unmatched = []
    for index in sorted(local_region):
        point = coordinates[index].copy()
        point.x = -point.x
        found = tree.find_range(point, tolerance)
        if len(found) > 1:
            ambiguous.append({"source": index, "targets": [item[1] for item in found]})
        elif not found:
            unmatched.append(index)
        else:
            mapping[index] = found[0][1]
            distances[index] = found[0][2]
    assert not ambiguous and not unmatched, (ambiguous, unmatched)
    assert len(set(mapping.values())) == len(mapping)
    for source, target in mapping.items():
        reverse_point = coordinates[target].copy()
        reverse_point.x = -reverse_point.x
        reverse = tree.find_range(reverse_point, tolerance)
        assert len(reverse) == 1 and reverse[0][1] == source

    edge_keys = {tuple(sorted(edge.vertices)) for edge in obj.data.edges}
    ring_pairs = []
    for left_index, left_ring in enumerate(rings["L"]):
        mirrored = {mapping[index] for index in left_ring["vertices"]}
        matches = [index for index, ring in enumerate(rings["R"]) if mirrored == set(ring["vertices"])]
        assert len(matches) == 1, (left_index, matches)
        right_index = matches[0]
        right_ring = rings["R"][right_index]
        cycle = [mapping[index] for index in left_ring["vertices"]]
        assert all(tuple(sorted((cycle[index], cycle[(index + 1) % len(cycle)]))) in edge_keys for index in range(len(cycle)))
        ring_pairs.append({"left_index": left_index, "right_index": right_index, "vertices": len(cycle),
                           "left_position": left_ring["position"], "right_position": right_ring["position"],
                           "position_error": abs(left_ring["position"] - right_ring["position"]),
                           "vertex_pairs": list(zip(left_ring["vertices"], cycle))})
    assert len(ring_pairs) == len(rings["R"]) == 7
    mapped_left = {mapping[index] for index in sleeves["L"][0]}
    mapped_right = {mapping[index] for index in sleeves["R"][0]}
    reflected_edges = [(first, second) for first, second in edge_keys if first in local_region and second in local_region
                       and tuple(sorted((mapping[first], mapping[second]))) not in edge_keys]
    assert not reflected_edges, reflected_edges
    plane = Matrix.Diagonal(Vector((-1.0, 1.0, 1.0)))
    bone_errors = {}
    for stem in ("upper_arm", "forearm", "hand"):
        left, right = armature.data.bones[stem + ".L"], armature.data.bones[stem + ".R"]
        bone_errors[stem] = {"head_error": (plane @ left.head_local - right.head_local).length,
                             "tail_error": (plane @ left.tail_local - right.tail_local).length,
                             "left_name": left.name, "right_name": right.name}
    lower_left, lower_right = armature.data.bones["forearm.L"], armature.data.bones["forearm.R"]
    axis_left = (lower_left.tail_local - lower_left.head_local).normalized()
    axis_right = (lower_right.tail_local - lower_right.head_local).normalized()
    pivot_left = lower_left.tail_local
    pivot_right = lower_right.tail_local
    mirrored_rotation_errors = []
    equal_sign_errors = []
    for index in sleeves["L"][0]:
        point = to_arm @ coordinates[index]
        other = to_arm @ coordinates[mapping[index]]
        ratio = min(1.0, max(0.0, sleeves["L"][2][index]))
        angle = math.pi / 2 * ratio
        left_rotated = pivot_left + Quaternion(axis_left, angle) @ (point - pivot_left)
        right_rotated = pivot_right + Quaternion(axis_right, -angle) @ (other - pivot_right)
        wrong_sign = pivot_right + Quaternion(axis_right, angle) @ (other - pivot_right)
        mirrored_rotation_errors.append((plane @ left_rotated - right_rotated).length)
        equal_sign_errors.append((plane @ left_rotated - wrong_sign).length)
    assert max(mirrored_rotation_errors) < 2e-6
    deform_weight_errors = []
    for source in sleeves["L"][0]:
        target = mapping[source]
        for stem in ("upper_arm", "forearm", "hand"):
            deform_weight_errors.append(abs(sleeves["L"][1][source].get(stem + ".L", 0) - sleeves["R"][1][target].get(stem + ".R", 0)))
    result = {
        "source": str(blend_path), "source_sha256": before,
        "mirror_plane": "Mesh Basis local X = 0", "matching_tolerance": tolerance,
        "mapped_region_vertices": len(mapping), "maximum_mirror_distance": max(distances.values()),
        "ambiguous": ambiguous, "unmatched": unmatched, "ring_pairs": ring_pairs,
        "mirrored_edges_preserved": True, "bone_rest_mirror_errors": bone_errors,
        "to_armature_matrix": [list(row) for row in to_arm],
        "left_native_support": len(sleeves["L"][0]), "right_native_support": len(sleeves["R"][0]),
        "right_native_not_in_mirrored_left": sorted(sleeves["R"][0] - mapped_left),
        "mirrored_left_not_in_right_native": sorted(mapped_left - sleeves["R"][0]),
        "left_native_not_in_mirrored_right": sorted(sleeves["L"][0] - mapped_right),
        "max_corresponding_weight_difference": max(deform_weight_errors),
        "opposite_sign_rotation_mirror_error": max(mirrored_rotation_errors),
        "same_sign_rotation_mirror_error": max(equal_sign_errors),
        "pose_channels_modified": False,
    }
    assert file_digest(blend_path) == before
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "real-x-symmetry-probe.json").write_text(json.dumps(result, indent=2), encoding="utf8")
    print("REAL_X_TWIST_SYMMETRY_PROBE=" + json.dumps({key: value for key, value in result.items() if key != "ring_pairs"}, sort_keys=True))


if __name__ == "__main__":
    main()
