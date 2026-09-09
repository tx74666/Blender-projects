"""Blender 5.2 regression coverage for Direct foot-widget geometry fitting."""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import test_limb_ik_blender as base


limb_ik = base.limb_ik
SIDES = ("L", "R")
SHOE_LIMITS = {
    "L": ((0.07, 0.25), (-0.35, 0.07), (-0.035, 0.075)),
    "R": ((-0.25, -0.07), (-0.35, 0.07), (-0.035, 0.075)),
}
SEED_LIMITS = {
    "L": ((0.11, 0.19), (-0.28, -0.01), (-0.01, 0.05)),
    "R": ((-0.19, -0.11), (-0.28, -0.01), (-0.01, 0.05)),
}
OUTLIER_LIMITS = {
    "L": ((0.38, 0.45), (-0.45, -0.40), (-0.02, 0.02)),
    "R": ((-0.45, -0.38), (-0.45, -0.40), (-0.02, 0.02)),
}
ANATOMICAL_YAW_DEGREES = {"L": 14.0, "R": -14.0}
ANATOMICAL_FOOT_CENTER = {"L": (0.16, -0.14), "R": (-0.16, -0.14)}
SMOOTH_SOLE_SPECS = {
    "L": {
        "center": (0.16, -0.14),
        "yaw_degrees": 17.0,
        "half_length": 0.19,
        "inner_width": 0.052,
        "outer_width": 0.069,
        "toe_bias": 0.12,
    },
    "R": {
        "center": (-0.16, -0.14),
        "yaw_degrees": -13.0,
        "half_length": 0.17,
        "inner_width": 0.047,
        "outer_width": 0.061,
        "toe_bias": -0.08,
    },
}


def _append_box(vertices, faces, limits):
    """Append a closed eight-vertex box and return its vertex indices."""
    (x_min, x_max), (y_min, y_max), (z_min, z_max) = limits
    start = len(vertices)
    vertices.extend(
        (
            (x_min, y_min, z_min),
            (x_max, y_min, z_min),
            (x_max, y_max, z_min),
            (x_min, y_max, z_min),
            (x_min, y_min, z_max),
            (x_max, y_min, z_max),
            (x_max, y_max, z_max),
            (x_min, y_max, z_max),
        )
    )
    faces.extend(
        tuple(start + index for index in face)
        for face in (
            (0, 1, 2, 3),
            (4, 7, 6, 5),
            (0, 4, 5, 1),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (4, 0, 3, 7),
        )
    )
    return tuple(range(start, start + 8))


def _make_box_object(name, limits_by_side):
    vertices = []
    faces = []
    indices_by_side = {}
    for side in SIDES:
        indices_by_side[side] = _append_box(vertices, faces, limits_by_side[side])
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, (), faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj, indices_by_side


def _make_weighted_foot_seed(armature):
    seed, indices_by_side = _make_box_object("WeightedFootSeed", SEED_LIMITS)
    for side in SIDES:
        group = seed.vertex_groups.new(name=f"foot.{side}")
        group.add(indices_by_side[side], 1.0, "REPLACE")
    modifier = seed.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = armature
    return seed


def _anatomical_forward(side):
    return (
        Matrix.Rotation(math.radians(ANATOMICAL_YAW_DEGREES[side]), 3, "Z")
        @ Vector((0.0, -1.0, 0.0))
    ).normalized()


def _anatomical_outline_uv(side, scale=1.0):
    """Return a mirrored heel-to-toe outline with a wider medial toe side."""
    levels = (
        (-0.18, -0.045, 0.045),
        (-0.06, -0.060, 0.055),
        (0.10, -0.078, 0.060),
        (0.18, -0.085, 0.045),
    )
    if side == "R":
        levels = tuple((v, -u_max, -u_min) for v, u_min, u_max in levels)
    left = tuple((u_min * scale, v * scale) for v, u_min, _u_max in levels)
    right = tuple((u_max * scale, v * scale) for v, _u_min, u_max in reversed(levels))
    return left + right


def _append_anatomical_foot(vertices, faces, side, *, scale, z_min, z_max):
    center_x, center_y = ANATOMICAL_FOOT_CENTER[side]
    forward = _anatomical_forward(side)
    lateral = Vector((-forward.y, forward.x, 0.0)).normalized()
    outline = _anatomical_outline_uv(side, scale)
    start = len(vertices)
    for z in (z_min, z_max):
        for u, v in outline:
            point = Vector((center_x, center_y, z)) + lateral * u + forward * v
            vertices.append(tuple(point))
    count = len(outline)
    faces.append(tuple(start + index for index in range(count)))
    faces.append(tuple(start + count + index for index in reversed(range(count))))
    for index in range(count):
        following = (index + 1) % count
        faces.append(
            (
                start + index,
                start + following,
                start + count + following,
                start + count + index,
            )
        )
    return tuple(range(start, start + count * 2))


def _make_anatomical_feet(name, *, scale, z_min, z_max):
    vertices = []
    faces = []
    indices_by_side = {}
    for side in SIDES:
        indices_by_side[side] = _append_anatomical_foot(
            vertices,
            faces,
            side,
            scale=scale,
            z_min=z_min,
            z_max=z_max,
        )
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, (), faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj, indices_by_side


def _make_anatomical_seed(armature):
    seed, indices_by_side = _make_anatomical_feet(
        "AnatomicalFootSeed",
        scale=0.68,
        z_min=-0.01,
        z_max=0.05,
    )
    for side in SIDES:
        group = seed.vertex_groups.new(name=f"foot.{side}")
        group.add(indices_by_side[side], 1.0, "REPLACE")
    modifier = seed.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = armature
    return seed


def _smooth_sole_forward(side):
    return (
        Matrix.Rotation(math.radians(SMOOTH_SOLE_SPECS[side]["yaw_degrees"]), 3, "Z")
        @ Vector((0.0, -1.0, 0.0))
    ).normalized()


def _smooth_sole_outline_uv(side, *, scale=1.0, samples=33):
    """Sample a smooth sole with a nearly straight medial and curved outer edge."""
    spec = SMOOTH_SOLE_SPECS[side]
    medial_sign = -1.0 if side == "L" else 1.0
    inner = []
    outer = []
    for index in range(samples):
        t = -1.0 + 2.0 * index / (samples - 1)
        v = spec["half_length"] * t * scale
        # The sixth-power cap stays nearly vertical through the middle of the
        # medial edge, then eases smoothly into the heel and toe.
        inner_cap = math.sqrt(max(0.0, 1.0 - abs(t) ** 6))
        outer_cap = math.sqrt(max(0.0, 1.0 - t * t))
        inner_u = medial_sign * spec["inner_width"] * inner_cap * scale
        outer_u = (
            -medial_sign
            * spec["outer_width"]
            * outer_cap
            * (1.0 + spec["toe_bias"] * t)
            * scale
        )
        inner.append((inner_u, v))
        outer.append((outer_u, v))
    # The two cap endpoints coincide.  Keep only one copy of each so the mesh
    # is one simple cycle rather than a cycle with zero-length cap edges.
    return tuple(inner + list(reversed(outer[1:-1])))


def _smooth_sole_world_outline(side, *, scale=1.0):
    spec = SMOOTH_SOLE_SPECS[side]
    center = Vector((*spec["center"], 0.0))
    forward = _smooth_sole_forward(side)
    lateral = Vector((-forward.y, forward.x, 0.0)).normalized()
    return tuple(
        center + lateral * u + forward * v
        for u, v in _smooth_sole_outline_uv(side, scale=scale)
    )


def _append_smooth_sole(vertices, faces, side, *, scale, z_min, z_max):
    outline = _smooth_sole_world_outline(side, scale=scale)
    start = len(vertices)
    for z in (z_min, z_max):
        vertices.extend((point.x, point.y, z) for point in outline)
    count = len(outline)
    faces.append(tuple(start + index for index in range(count)))
    faces.append(tuple(start + count + index for index in reversed(range(count))))
    for index in range(count):
        following = (index + 1) % count
        faces.append(
            (
                start + index,
                start + following,
                start + count + following,
                start + count + index,
            )
        )
    return tuple(range(start, start + count * 2))


def _make_smooth_independent_feet(name, *, scale, z_min, z_max):
    vertices = []
    faces = []
    indices_by_side = {}
    for side in SIDES:
        indices_by_side[side] = _append_smooth_sole(
            vertices,
            faces,
            side,
            scale=scale,
            z_min=z_min,
            z_max=z_max,
        )
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, (), faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj, indices_by_side


def _make_smooth_independent_seed(armature):
    seed, indices_by_side = _make_smooth_independent_feet(
        "SmoothIndependentFootSeed",
        scale=0.72,
        z_min=-0.01,
        z_max=0.05,
    )
    for side in SIDES:
        group = seed.vertex_groups.new(name=f"foot.{side}")
        group.add(indices_by_side[side], 1.0, "REPLACE")
    modifier = seed.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = armature
    return seed


def _evaluated_points_in_armature(obj, armature):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        transform = armature.matrix_world.inverted_safe() @ evaluated.matrix_world
        return tuple(transform @ vertex.co for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def _shape_display_points(pose_bone):
    """Reconstruct Blender's displayed custom-shape vertices in Armature space."""
    if pose_bone.custom_shape is None:
        raise AssertionError(f"{pose_bone.name} has no custom shape")
    scale = Matrix.Diagonal(Vector((*pose_bone.custom_shape_scale_xyz, 1.0)))
    rotation = pose_bone.custom_shape_rotation_euler.to_matrix().to_4x4()
    translation = Matrix.Translation(pose_bone.custom_shape_translation)
    display = pose_bone.matrix @ translation @ rotation @ scale
    return tuple(display @ vertex.co for vertex in pose_bone.custom_shape.data.vertices)


def _shape_display_matrix(pose_bone):
    if pose_bone.custom_shape is None:
        raise AssertionError(f"{pose_bone.name} has no custom shape")
    scale = Matrix.Diagonal(Vector((*pose_bone.custom_shape_scale_xyz, 1.0)))
    rotation = pose_bone.custom_shape_rotation_euler.to_matrix().to_4x4()
    translation = Matrix.Translation(pose_bone.custom_shape_translation)
    return pose_bone.matrix @ translation @ rotation @ scale


def _ordered_display_loop(pose_bone):
    shape = pose_bone.custom_shape
    if shape is None or shape.type != "MESH":
        raise AssertionError(f"{pose_bone.name} has no Mesh Custom Shape")
    vertex_count = len(shape.data.vertices)
    adjacency = {index: [] for index in range(vertex_count)}
    for edge in shape.data.edges:
        left, right = (int(value) for value in edge.vertices)
        adjacency[left].append(right)
        adjacency[right].append(left)
    if vertex_count < 32 or len(shape.data.edges) != vertex_count:
        raise AssertionError(
            f"{pose_bone.name} is not a sufficiently smooth single-cycle outline: "
            f"vertices={vertex_count}, edges={len(shape.data.edges)}"
        )
    invalid = [index for index, neighbours in adjacency.items() if len(neighbours) != 2]
    if invalid:
        raise AssertionError(f"{pose_bone.name} outline is not a simple degree-2 loop: {invalid[:4]}")

    start = min(adjacency)
    order = [start]
    previous = None
    current = start
    while True:
        choices = [index for index in adjacency[current] if index != previous]
        following = min(choices) if previous is None else choices[0]
        if following == start:
            break
        if following in order:
            raise AssertionError(f"{pose_bone.name} outline contains a premature cycle")
        order.append(following)
        previous, current = current, following
    if len(order) != vertex_count:
        raise AssertionError(
            f"{pose_bone.name} outline has disconnected cycles: visited={len(order)}, "
            f"vertices={vertex_count}"
        )
    display = _shape_display_matrix(pose_bone)
    return tuple(display @ shape.data.vertices[index].co for index in order)


def _project_to_smooth_sole_frame(points, side):
    spec = SMOOTH_SOLE_SPECS[side]
    center = Vector((*spec["center"], 0.0))
    forward = _smooth_sole_forward(side)
    lateral = Vector((-forward.y, forward.x, 0.0)).normalized()
    return tuple(
        (float((point - center).dot(lateral)), float((point - center).dot(forward)))
        for point in points
    )


def _orientation_2d(left, middle, right):
    return (middle[0] - left[0]) * (right[1] - left[1]) - (middle[1] - left[1]) * (right[0] - left[0])


def _point_on_segment_2d(point, left, right, tolerance=1.0e-9):
    if abs(_orientation_2d(left, right, point)) > tolerance:
        return False
    return (
        min(left[0], right[0]) - tolerance <= point[0] <= max(left[0], right[0]) + tolerance
        and min(left[1], right[1]) - tolerance <= point[1] <= max(left[1], right[1]) + tolerance
    )


def _segments_intersect_2d(a, b, c, d, tolerance=1.0e-9):
    orientations = (
        _orientation_2d(a, b, c),
        _orientation_2d(a, b, d),
        _orientation_2d(c, d, a),
        _orientation_2d(c, d, b),
    )
    if orientations[0] * orientations[1] < -tolerance and orientations[2] * orientations[3] < -tolerance:
        return True
    return any(
        abs(value) <= tolerance and _point_on_segment_2d(point, left, right, tolerance)
        for value, point, left, right in (
            (orientations[0], c, a, b),
            (orientations[1], d, a, b),
            (orientations[2], a, c, d),
            (orientations[3], b, c, d),
        )
    )


def _assert_simple_polygon(points, label):
    count = len(points)
    for left_index in range(count):
        a = points[left_index]
        b = points[(left_index + 1) % count]
        for right_index in range(left_index + 1, count):
            if right_index in {left_index, (left_index + 1) % count}:
                continue
            if left_index == 0 and right_index == count - 1:
                continue
            c = points[right_index]
            d = points[(right_index + 1) % count]
            if _segments_intersect_2d(a, b, c, d):
                raise AssertionError(
                    f"{label} outline self-intersects between edges {left_index} and {right_index}"
                )


def _polygon_area_2d(points):
    return abs(
        sum(
            left[0] * right[1] - right[0] * left[1]
            for left, right in zip(points, points[1:] + points[:1])
        )
    ) * 0.5


def _point_inside_polygon_2d(point, polygon):
    inside = False
    for left, right in zip(polygon, polygon[1:] + polygon[:1]):
        if _point_on_segment_2d(point, left, right):
            return True
        if (left[1] > point[1]) != (right[1] > point[1]):
            crossing_x = left[0] + (point[1] - left[1]) * (right[0] - left[0]) / (right[1] - left[1])
            if crossing_x > point[0]:
                inside = not inside
    return inside


def _point_segment_distance_2d(point, left, right):
    axis_x = right[0] - left[0]
    axis_y = right[1] - left[1]
    length_squared = axis_x * axis_x + axis_y * axis_y
    if length_squared <= 1.0e-16:
        return math.hypot(point[0] - left[0], point[1] - left[1])
    factor = max(
        0.0,
        min(1.0, ((point[0] - left[0]) * axis_x + (point[1] - left[1]) * axis_y) / length_squared),
    )
    closest = (left[0] + factor * axis_x, left[1] + factor * axis_y)
    return math.hypot(point[0] - closest[0], point[1] - closest[1])


def _outline_clearance(point, polygon):
    return min(
        _point_segment_distance_2d(point, left, right)
        for left, right in zip(polygon, polygon[1:] + polygon[:1])
    )


def _cross_section_intersections(polygon, v):
    intersections = []
    for left, right in zip(polygon, polygon[1:] + polygon[:1]):
        if (left[1] <= v < right[1]) or (right[1] <= v < left[1]):
            factor = (v - left[1]) / (right[1] - left[1])
            intersections.append(left[0] + factor * (right[0] - left[0]))
    intersections.sort()
    compact = []
    for value in intersections:
        if not compact or abs(value - compact[-1]) > 1.0e-7:
            compact.append(value)
    return compact


def _principal_horizontal_axis(points, preferred):
    mean_x = sum(float(point.x) for point in points) / len(points)
    mean_y = sum(float(point.y) for point in points) / len(points)
    xx = sum((float(point.x) - mean_x) ** 2 for point in points)
    yy = sum((float(point.y) - mean_y) ** 2 for point in points)
    xy = sum((float(point.x) - mean_x) * (float(point.y) - mean_y) for point in points)
    angle = 0.5 * math.atan2(2.0 * xy, xx - yy)
    axis = Vector((math.cos(angle), math.sin(angle), 0.0))
    if axis.dot(preferred) < 0.0:
        axis.negate()
    return axis.normalized()


def _assert_smooth_independent_outline(side, display_points):
    label = f"{side} Foot"
    polygon = _project_to_smooth_sole_frame(display_points, side)
    _assert_simple_polygon(polygon, label)

    shoe = _smooth_sole_outline_uv(side)
    shoe_samples = []
    for left, right in zip(shoe, shoe[1:] + shoe[:1]):
        for index in range(5):
            factor = index / 5.0
            shoe_samples.append(
                (
                    left[0] + factor * (right[0] - left[0]),
                    left[1] + factor * (right[1] - left[1]),
                )
            )
    clearances = []
    for point in shoe_samples:
        if not _point_inside_polygon_2d(point, polygon):
            raise AssertionError(f"{label} outline does not surround its visible sole at {point}")
        clearances.append(_outline_clearance(point, polygon))
    shoe_minor_span = max(value[0] for value in shoe) - min(value[0] for value in shoe)
    if min(clearances) < shoe_minor_span * 0.01:
        raise AssertionError(f"{label} outline is not measurably larger than its sole: {min(clearances)}")
    if max(clearances) > shoe_minor_span * 0.22:
        raise AssertionError(f"{label} outline margin is no longer slight: {max(clearances)}")
    area_ratio = _polygon_area_2d(polygon) / _polygon_area_2d(shoe)
    if not 1.02 <= area_ratio <= 1.45:
        raise AssertionError(f"{label} outline/sole area ratio is not slight: {area_ratio}")

    spec = SMOOTH_SOLE_SPECS[side]
    cross_sections = []
    for index in range(15):
        t = -0.7 + 1.4 * index / 14.0
        intersections = _cross_section_intersections(polygon, spec["half_length"] * t)
        if len(intersections) != 2:
            raise AssertionError(
                f"{label} has {len(intersections)} outline crossings at longitudinal t={t}"
            )
        cross_sections.append(intersections)
    if side == "L":
        inner = [values[0] for values in cross_sections]
        outer = [values[1] for values in cross_sections]
    else:
        inner = [values[1] for values in cross_sections]
        outer = [values[0] for values in cross_sections]
    mean_width = sum(right - left for left, right in cross_sections) / len(cross_sections)
    inner_range = max(inner) - min(inner)
    outer_range = max(outer) - min(outer)
    if inner_range > mean_width * 0.10:
        raise AssertionError(f"{label} medial edge is not sufficiently straight: {inner_range}")
    if outer_range < mean_width * 0.04 or outer_range <= inner_range * 1.25:
        raise AssertionError(
            f"{label} outer edge is not the continuous curved edge: "
            f"inner_range={inner_range}, outer_range={outer_range}"
        )
    second_differences = [
        outer[index - 1] - 2.0 * outer[index] + outer[index + 1]
        for index in range(1, len(outer) - 1)
    ]
    if max((abs(value) for value in second_differences), default=0.0) > mean_width * 0.08:
        raise AssertionError(f"{label} outer curvature contains a visible kink")
    slopes = [right - left for left, right in zip(outer, outer[1:])]
    signed_slopes = [value if side == "L" else -value for value in slopes]
    meaningful = [1 if value > 1.0e-5 else -1 for value in signed_slopes if abs(value) > 1.0e-5]
    sign_changes = sum(left != right for left, right in zip(meaningful, meaningful[1:]))
    if sign_changes > 1:
        raise AssertionError(f"{label} outer curvature oscillates instead of flowing continuously")

    expected_forward = _smooth_sole_forward(side)
    principal = _principal_horizontal_axis(display_points, expected_forward)
    if principal.dot(expected_forward) < 0.99:
        raise AssertionError(
            f"{label} yaw does not follow its visible sole: "
            f"axis={tuple(principal)}, expected={tuple(expected_forward)}"
        )


def _smooth_widget_snapshot(armature):
    targets = {
        side: armature.pose.bones[f"CTRL_foot_IK.{side}"]
        for side in SIDES
    }
    left_shape = targets["L"].custom_shape
    right_shape = targets["R"].custom_shape
    if left_shape is None or right_shape is None:
        raise AssertionError("A generated Foot target has no Custom Shape")
    if left_shape is right_shape or left_shape.data is right_shape.data:
        raise AssertionError("Left and Right Foot controls still share one outline instead of independent soles")

    snapshot = {}
    for side, target in targets.items():
        display_points = _ordered_display_loop(target)
        _assert_smooth_independent_outline(side, display_points)
        snapshot[side] = {
            "object_name": target.custom_shape.name,
            "mesh_name": target.custom_shape.data.name,
            "vertices": tuple(tuple(float(value) for value in vertex.co) for vertex in target.custom_shape.data.vertices),
            "edges": tuple(tuple(int(value) for value in edge.vertices) for edge in target.custom_shape.data.edges),
            "display": tuple(tuple(float(value) for value in point) for point in display_points),
        }
    return snapshot


def _assert_smooth_widget_snapshots_equal(before, after):
    for side in SIDES:
        for field in ("object_name", "mesh_name", "edges"):
            if before[side][field] != after[side][field]:
                raise AssertionError(
                    f"{side} Foot {field} changed across Rebuild: "
                    f"{before[side][field]} != {after[side][field]}"
                )
        for field in ("vertices", "display"):
            left = before[side][field]
            right = after[side][field]
            if len(left) != len(right):
                raise AssertionError(f"{side} Foot {field} count changed across Rebuild")
            error = max(
                (
                    abs(left[index][axis] - right[index][axis])
                    for index in range(len(left))
                    for axis in range(3)
                ),
                default=0.0,
            )
            if error > 1.0e-6:
                raise AssertionError(f"{side} Foot {field} changed across Rebuild by {error}")


def _bounds(points):
    return tuple(
        (min(float(point[axis]) for point in points), max(float(point[axis]) for point in points))
        for axis in range(3)
    )


def _side_points(points, side):
    return tuple(point for point in points if (point.x >= 0.0) == (side == "L"))


def _assert_minimal_direct_legs(armature):
    inventory = limb_ik._validate_inventory(armature)
    expected_bones = {
        "CTRL_foot_IK.L",
        "CTRL_knee_pole.L",
        "MCH_knee_pole_aim.L",
        "CTRL_foot_IK.R",
        "CTRL_knee_pole.R",
        "MCH_knee_pole_aim.R",
    }
    if inventory["schema"] != limb_ik.DIRECT_PREROLL_SCHEMA:
        raise AssertionError(f"Direct legs used schema {inventory['schema']!r}")
    if set(inventory["rigs"]) != {("LEG", "L"), ("LEG", "R")}:
        raise AssertionError(f"Unexpected Direct leg rigs: {set(inventory['rigs'])}")
    if {bone.name for bone in inventory["bones"]} != expected_bones:
        raise AssertionError(
            "Direct legs were not Target + Pole + hidden display helper per limb: "
            f"{sorted(bone.name for bone in inventory['bones'])}"
        )
    if inventory["master"] is not None:
        raise AssertionError("Direct legs unexpectedly generated a Master control")
    for side in SIDES:
        rig = inventory["rigs"][("LEG", side)]
        expected_side = {
            f"CTRL_foot_IK.{side}",
            f"CTRL_knee_pole.{side}",
            f"MCH_knee_pole_aim.{side}",
        }
        side_bones = {
            bone.name
            for bone in inventory["bones"]
            if bone.get(limb_ik.RIG_ID_KEY) == rig["rig_id"]
        }
        if side_bones != expected_side:
            raise AssertionError(f"{side} leg generated {sorted(side_bones)}, expected {sorted(expected_side)}")
        roles = {record["role"] for _owner, _constraint, record in rig["entries"]}
        if roles != {
            "IK",
            "END_ROTATION",
            "AUTO_OFFSET_ROTATION",
            "POLE_DISPLAY_TRACK",
        } or len(rig["entries"]) != 4:
            raise AssertionError(f"{side} Direct leg generated unexpected constraint roles: {sorted(roles)}")


def _assert_visible_shoe_fit(side, shoe_bounds, widget_bounds):
    shoe_width = shoe_bounds[0][1] - shoe_bounds[0][0]
    shoe_length = shoe_bounds[1][1] - shoe_bounds[1][0]
    gaps = (
        shoe_bounds[0][0] - widget_bounds[0][0],
        widget_bounds[0][1] - shoe_bounds[0][1],
        shoe_bounds[1][0] - widget_bounds[1][0],
        widget_bounds[1][1] - shoe_bounds[1][1],
    )
    if min(gaps) <= 0.002:
        raise AssertionError(
            f"{side} Foot outline does not surround the visible shoe on every horizontal edge: {gaps}"
        )
    if max(gaps) >= min(shoe_width, shoe_length) * 0.20:
        raise AssertionError(f"{side} Foot outline margin is no longer slight: {gaps}")
    widget_width = widget_bounds[0][1] - widget_bounds[0][0]
    widget_length = widget_bounds[1][1] - widget_bounds[1][0]
    if not (shoe_width < widget_width < shoe_width * 1.4):
        raise AssertionError(f"{side} Foot width did not fit the shoe: shoe={shoe_width}, widget={widget_width}")
    if not (shoe_length < widget_length < shoe_length * 1.4):
        raise AssertionError(f"{side} Foot length did not fit the shoe: shoe={shoe_length}, widget={widget_length}")

    shoe_sole = shoe_bounds[2][0]
    widget_top = widget_bounds[2][1]
    if widget_top >= shoe_sole - 0.002:
        raise AssertionError(
            f"{side} Foot outline is not wholly below the sole: top={widget_top}, sole={shoe_sole}"
        )
    if side == "L" and widget_bounds[0][0] <= 0.0:
        raise AssertionError(f"Left Foot outline crossed the body center: {widget_bounds[0]}")
    if side == "R" and widget_bounds[0][1] >= 0.0:
        raise AssertionError(f"Right Foot outline crossed the body center: {widget_bounds[0]}")


def _build_scene(*, hidden_outlier):
    base.reset_scene()
    armature = base.make_humanoid(name="DirectFootWidgetRig")
    _make_weighted_foot_seed(armature)
    shoes, _indices = _make_box_object("VisibleShoes", SHOE_LIMITS)
    if hidden_outlier:
        outlier, _indices = _make_box_object("HiddenFootwearOutlier", OUTLIER_LIMITS)
        outlier.hide_render = True
        outlier.hide_viewport = True
        outlier.hide_set(True)
        if outlier.visible_get(view_layer=bpy.context.view_layer):
            raise AssertionError("Hidden outlier fixture is still visible")

    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_leg() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()

    _assert_minimal_direct_legs(armature)
    shoe_points = _evaluated_points_in_armature(shoes, armature)
    snapshot = {}
    for side in SIDES:
        shoe_bounds = _bounds(_side_points(shoe_points, side))
        target = armature.pose.bones[f"CTRL_foot_IK.{side}"]
        widget_bounds = _bounds(_shape_display_points(target))
        _assert_visible_shoe_fit(side, shoe_bounds, widget_bounds)
        snapshot[side] = {
            "bounds": widget_bounds,
            "scale": tuple(float(value) for value in target.custom_shape_scale_xyz),
            "translation": tuple(float(value) for value in target.custom_shape_translation),
            "rotation": tuple(float(value) for value in target.custom_shape_rotation_euler),
        }
    return snapshot


def _assert_snapshots_close(without_outlier, with_hidden_outlier):
    for side in SIDES:
        for field in ("bounds", "scale", "translation", "rotation"):
            baseline = without_outlier[side][field]
            hidden = with_hidden_outlier[side][field]
            if field == "bounds":
                differences = [
                    abs(baseline[axis][edge] - hidden[axis][edge])
                    for axis in range(3)
                    for edge in range(2)
                ]
            else:
                differences = [abs(left - right) for left, right in zip(baseline, hidden)]
            if max(differences, default=0.0) > 1.0e-6:
                raise AssertionError(
                    f"Hidden outlier changed {side} Foot {field}: "
                    f"baseline={baseline}, hidden={hidden}"
                )


def test_direct_foot_widget_fits_visible_shoes_and_ignores_hidden_outlier():
    baseline = _build_scene(hidden_outlier=False)
    with_hidden_outlier = _build_scene(hidden_outlier=True)
    _assert_snapshots_close(baseline, with_hidden_outlier)


def test_direct_foot_widget_preserves_anatomical_axes_on_yawed_asymmetric_feet():
    base.reset_scene()
    armature = base.make_humanoid(name="YawedAnatomicalFootWidgetRig")
    _make_anatomical_seed(armature)
    _make_anatomical_feet(
        "YawedAsymmetricShoes",
        scale=1.0,
        z_min=-0.035,
        z_max=0.075,
    )

    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_leg() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()

    _assert_minimal_direct_legs(armature)
    for side in SIDES:
        target = armature.pose.bones[f"CTRL_foot_IK.{side}"]
        display = _shape_display_matrix(target)
        origin = display @ Vector((0.0, 0.0, 0.0))
        raw_positive_x = (display @ Vector((1.0, 0.0, 0.0))) - origin
        raw_positive_y = (display @ Vector((0.0, 1.0, 0.0))) - origin
        if min(raw_positive_x.length, raw_positive_y.length) <= 1.0e-8:
            raise AssertionError(f"{side} Foot widget produced a degenerate display frame")
        raw_positive_x.normalize()
        raw_positive_y.normalize()

        expected_forward = _anatomical_forward(side)
        if raw_positive_y.dot(expected_forward) < 0.98:
            raise AssertionError(
                f"{side} Foot raw +Y no longer maps toward the toes: "
                f"actual={tuple(raw_positive_y)}, expected={tuple(expected_forward)}"
            )
        medial = Vector((-1.0 if side == "L" else 1.0, 0.0, 0.0))
        if raw_positive_x.dot(medial) < 0.95:
            raise AssertionError(
                f"{side} Foot raw +X no longer maps toward the body centerline: "
                f"actual={tuple(raw_positive_x)}"
            )

        scale_x = float(target.custom_shape_scale_xyz.x)
        if (side == "L" and scale_x >= 0.0) or (side == "R" and scale_x <= 0.0):
            raise AssertionError(
                f"{side} Foot has the wrong signed X scale for the shared Rain outline: {scale_x}"
            )
        if abs(raw_positive_x.z) > 1.0e-5 or abs(raw_positive_y.z) > 1.0e-5:
            raise AssertionError(
                f"{side} Foot display plane is tilted: "
                f"raw+X.z={raw_positive_x.z}, raw+Y.z={raw_positive_y.z}"
            )
        plane_normal = raw_positive_x.cross(raw_positive_y).normalized()
        if abs(plane_normal.dot(Vector((0.0, 0.0, 1.0)))) < 0.99999:
            raise AssertionError(
                f"{side} Foot display plane is not horizontal: normal={tuple(plane_normal)}"
            )


def test_direct_foot_widget_fallback_is_flat_and_anatomical_without_mesh():
    base.reset_scene()
    armature = base.make_humanoid(
        name="FallbackFootWidgetRig",
        roll_offset=0.73,
    )
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_leg() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()

    _assert_minimal_direct_legs(armature)
    for side in SIDES:
        target = armature.pose.bones[f"CTRL_foot_IK.{side}"]
        foot = armature.pose.bones[f"foot.{side}"]
        display = _shape_display_matrix(target)
        origin = display @ Vector((0.0, 0.0, 0.0))
        raw_positive_x = (display @ Vector((1.0, 0.0, 0.0))) - origin
        raw_positive_y = (display @ Vector((0.0, 1.0, 0.0))) - origin
        raw_positive_x.normalize()
        raw_positive_y.normalize()

        expected_forward = Vector(foot.tail) - Vector(foot.head)
        expected_forward.z = 0.0
        expected_forward.normalize()
        if raw_positive_y.dot(expected_forward) < 0.999:
            raise AssertionError(
                f"{side} fallback Foot +Y does not follow horizontal Foot forward: "
                f"actual={tuple(raw_positive_y)}, expected={tuple(expected_forward)}"
            )
        medial = Vector((-1.0 if side == "L" else 1.0, 0.0, 0.0))
        if raw_positive_x.dot(medial) < 0.95:
            raise AssertionError(
                f"{side} fallback Foot +X is not medial: {tuple(raw_positive_x)}"
            )
        if abs(raw_positive_x.z) > 1.0e-5 or abs(raw_positive_y.z) > 1.0e-5:
            raise AssertionError(
                f"{side} fallback Foot inherited source pitch/roll: "
                f"raw+X.z={raw_positive_x.z}, raw+Y.z={raw_positive_y.z}"
            )

        points = _shape_display_points(target)
        foot_length = (Vector(foot.tail) - Vector(foot.head)).length
        display_center = sum(points, Vector()) / len(points)
        lateral = Vector((-expected_forward.y, expected_forward.x, 0.0)).normalized()
        lateral_offset = abs((display_center - Vector(foot.head)).dot(lateral))
        if lateral_offset > foot_length * 0.1:
            raise AssertionError(
                f"{side} fallback Foot is laterally offset from its Foot axis: {lateral_offset}"
            )
        if max(point.z for point in points) >= min(float(foot.head.z), float(foot.tail.z)):
            raise AssertionError(f"{side} fallback Foot is not below the source Foot")


def test_direct_foot_widgets_are_independent_smooth_sole_outlines_and_rebuild_deterministically():
    base.reset_scene()
    armature = base.make_humanoid(name="IndependentSmoothFootWidgetRig")
    _make_smooth_independent_seed(armature)
    _make_smooth_independent_feet(
        "VisibleIndependentSmoothShoes",
        scale=1.0,
        z_min=-0.035,
        z_max=0.075,
    )

    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_leg() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()

    _assert_minimal_direct_legs(armature)
    built = _smooth_widget_snapshot(armature)

    if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()
    _assert_minimal_direct_legs(armature)
    rebuilt = _smooth_widget_snapshot(armature)
    _assert_smooth_widget_snapshots_equal(built, rebuilt)


def _convert_direct_legs_to_legacy_shared_foot(armature):
    """Emulate the shared FOOT ownership written by pre-sided Direct builds."""
    inventory = limb_ik._validate_inventory(armature)
    armature_id = inventory["armature_id"]
    collection = next(
        collection
        for collection in bpy.data.collections
        if limb_ik._owned(collection, armature_id, role="WIDGET_COLLECTION")
    )
    name = "WGT_Randy_FootIK"
    if bpy.data.objects.get(name) is not None or bpy.data.meshes.get(name) is not None:
        raise AssertionError("Legacy shared Foot fixture name is unexpectedly occupied")
    mesh = bpy.data.meshes.new(name)
    vertices, edges = limb_ik._widget_geometry("FOOT", schema=limb_ik.DIRECT_PREROLL_SCHEMA)
    mesh.from_pydata(vertices, edges, ())
    mesh.update()
    limb_ik._tag(mesh, armature_id, role="WIDGET_DATA", kind="FOOT")
    shared = bpy.data.objects.new(name, mesh)
    collection.objects.link(shared)
    limb_ik._tag(shared, armature_id, role="WIDGET", kind="FOOT")
    shared.hide_render = True
    shared.display_type = "WIRE"

    sided = set()
    for side in SIDES:
        target = armature.pose.bones[f"CTRL_foot_IK.{side}"]
        sided.add(target.custom_shape)
        target.custom_shape = shared
    for obj in sided:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)
    bpy.context.view_layer.update()
    limb_ik._removal_resources(bpy.context, armature, limb_ik._validate_inventory(armature))
    return shared


def _legacy_shared_foot_signature(armature):
    inventory = limb_ik._validate_inventory(armature)
    limb_ik._removal_resources(bpy.context, armature, inventory)
    targets = tuple(armature.pose.bones[f"CTRL_foot_IK.{side}"] for side in SIDES)
    shape = targets[0].custom_shape
    if shape is None or any(target.custom_shape is not shape for target in targets):
        raise AssertionError("Legacy fixture no longer has one shared Foot assignment")
    if shape.name != "WGT_Randy_FootIK" or shape.get(limb_ik.KIND_KEY) != "FOOT":
        raise AssertionError("Legacy shared Foot name/KIND changed")
    return {
        "rig_ids": tuple(sorted(rig["rig_id"] for rig in inventory["rigs"].values())),
        "object_name": shape.name,
        "mesh_name": shape.data.name,
        "kind": shape.get(limb_ik.KIND_KEY),
        "vertices": tuple(tuple(float(value) for value in vertex.co) for vertex in shape.data.vertices),
        "edges": tuple(tuple(int(value) for value in edge.vertices) for edge in shape.data.edges),
        "target_shapes": tuple(target.custom_shape.name for target in targets),
        "target_scale": tuple(tuple(float(value) for value in target.custom_shape_scale_xyz) for target in targets),
        "target_translation": tuple(tuple(float(value) for value in target.custom_shape_translation) for target in targets),
        "target_rotation": tuple(tuple(float(value) for value in target.custom_shape_rotation_euler) for target in targets),
    }


def test_legacy_shared_direct_foot_remove_rebuild_upgrade_and_failure_recovery():
    # First prove that an old saved shared-FOOT rig can be removed directly,
    # without requiring a migration Rebuild as an intermediate step.
    base.reset_scene()
    removable = base.make_humanoid(name="LegacySharedDirectFootRemoveRig")
    result, settings = base.analyze(removable)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_leg() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _convert_direct_legs_to_legacy_shared_foot(removable)
    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if bpy.data.collections.get(limb_ik.WIDGET_COLLECTION_NAME) is not None:
        raise AssertionError("Legacy shared FOOT Remove left its widget collection")

    base.reset_scene()
    armature = base.make_humanoid(name="LegacySharedDirectFootWidgetRig")
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    if bpy.ops.character_designer.limb_ik_build_leg() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _convert_direct_legs_to_legacy_shared_foot(armature)
    before = _legacy_shared_foot_signature(armature)

    original_create = limb_ik._create_constraints_and_shapes
    calls = {"count": 0}

    def fail_new_build_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("injected sided Foot rebuild failure")
        return original_create(*args, **kwargs)

    limb_ik._create_constraints_and_shapes = fail_new_build_once
    try:
        if base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild) != {"CANCELLED"}:
            raise AssertionError("Injected sided Foot Rebuild failure did not cancel")
    finally:
        limb_ik._create_constraints_and_shapes = original_create
    if calls["count"] < 2:
        raise AssertionError("Failed sided Foot Rebuild did not invoke snapshot recovery")
    after = _legacy_shared_foot_signature(armature)
    if after != before:
        raise AssertionError("Failed Rebuild did not exactly restore the legacy shared FOOT")

    if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()
    targets = tuple(armature.pose.bones[f"CTRL_foot_IK.{side}"] for side in SIDES)
    if targets[0].custom_shape is targets[1].custom_shape:
        raise AssertionError("Successful Rebuild did not upgrade legacy FOOT to sided widgets")
    if {target.custom_shape.get(limb_ik.KIND_KEY) for target in targets} != {"FOOT_L", "FOOT_R"}:
        raise AssertionError("Successful Rebuild produced the wrong sided Foot KIND set")
    limb_ik._removal_resources(bpy.context, armature, limb_ik._validate_inventory(armature))
    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if bpy.data.collections.get(limb_ik.WIDGET_COLLECTION_NAME) is not None:
        raise AssertionError("Sided Foot Remove left the owned widget collection")


def test_renamed_owned_widget_resource_fails_closed_before_destructive_rebuild():
    base.reset_scene()
    armature = base.make_humanoid(name="RenamedOwnedFootWidgetRig")
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "DIRECT_PREROLL"
    settings.selected_limb = "LEFT_LEG"
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    before_ids = {
        rig["rig_id"]
        for rig in limb_ik._validate_inventory(armature)["rigs"].values()
    }
    before_bones = {bone.name for bone in armature.data.bones}
    shape = armature.pose.bones["CTRL_foot_IK.L"].custom_shape
    canonical_object_name = shape.name
    canonical_mesh_name = shape.data.name

    shape.name = "ArtistRenamedOwnedFoot"
    if base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild) != {"CANCELLED"}:
        raise AssertionError("Rebuild accepted a renamed owned widget Object")
    if {bone.name for bone in armature.data.bones} != before_bones:
        raise AssertionError("Renamed widget Object caused a destructive partial Rebuild")
    if {
        rig["rig_id"]
        for rig in limb_ik._validate_inventory(armature)["rigs"].values()
    } != before_ids:
        raise AssertionError("Renamed widget Object changed the old rig before refusal")
    shape.name = canonical_object_name

    shape.data.name = "ArtistRenamedOwnedFootMesh"
    if base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild) != {"CANCELLED"}:
        raise AssertionError("Rebuild accepted a renamed owned widget Mesh")
    if {bone.name for bone in armature.data.bones} != before_bones:
        raise AssertionError("Renamed widget Mesh caused a destructive partial Rebuild")
    shape.data.name = canonical_mesh_name
    limb_ik._removal_resources(bpy.context, armature, limb_ik._validate_inventory(armature))


def main():
    base.ensure_registered()
    try:
        test_direct_foot_widget_fits_visible_shoes_and_ignores_hidden_outlier()
        print("PASS test_direct_foot_widget_fits_visible_shoes_and_ignores_hidden_outlier")
        test_direct_foot_widget_preserves_anatomical_axes_on_yawed_asymmetric_feet()
        print("PASS test_direct_foot_widget_preserves_anatomical_axes_on_yawed_asymmetric_feet")
        test_direct_foot_widget_fallback_is_flat_and_anatomical_without_mesh()
        print("PASS test_direct_foot_widget_fallback_is_flat_and_anatomical_without_mesh")
        test_direct_foot_widgets_are_independent_smooth_sole_outlines_and_rebuild_deterministically()
        print("PASS test_direct_foot_widgets_are_independent_smooth_sole_outlines_and_rebuild_deterministically")
        test_legacy_shared_direct_foot_remove_rebuild_upgrade_and_failure_recovery()
        print("PASS test_legacy_shared_direct_foot_remove_rebuild_upgrade_and_failure_recovery")
        test_renamed_owned_widget_resource_fails_closed_before_destructive_rebuild()
        print("PASS test_renamed_owned_widget_resource_fails_closed_before_destructive_rebuild")
    finally:
        base.reset_scene()
        base.ensure_unregistered()


if __name__ == "__main__":
    main()
