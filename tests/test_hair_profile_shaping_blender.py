"""Blender 5.2 integration tests for generated hair Curve shaping.

Run with::

    blender --background --factory-startup --python tests/test_hair_profile_shaping_blender.py

The fixtures are created in memory.  This test never opens or saves a .blend.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

import character_designer


TOLERANCE = 1.0e-5
ORIENTATION_TOLERANCE = 0.999
TIP_RADIUS = 0.015


def assert_close(actual, expected, tolerance=TOLERANCE, message=""):
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(message or f"Expected {expected}, got {actual}")


def assert_vector_close(actual, expected, tolerance=TOLERANCE):
    actual = Vector(actual)
    expected = Vector(expected)
    if (actual - expected).length > tolerance:
        raise AssertionError(f"Expected {tuple(expected)}, got {tuple(actual)}")


def assert_matrix_close(actual, expected, tolerance=TOLERANCE):
    for row in range(4):
        for column in range(4):
            assert_close(actual[row][column], expected[row][column], tolerance)


def reset_scene():
    settings = getattr(bpy.context.window_manager, "character_designer", None)
    if settings is not None and settings.live_preview_enabled:
        settings.live_preview_enabled = False
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for curve in list(bpy.data.curves):
        if curve.users == 0:
            bpy.data.curves.remove(curve)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def make_mesh_object(name, vertices, faces):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def select_vertices(obj, indices):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bm = bmesh.from_edit_mesh(obj.data)
    selected = set(indices)
    for vertex in bm.verts:
        vertex.select_set(vertex.index in selected)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)


def confirm_full_selection(obj):
    select_vertices(obj, range(len(obj.data.vertices)))
    settings = bpy.context.window_manager.character_designer
    settings.live_preview_enabled = True
    character_designer._live_preview_tick()
    if not settings.preview_valid or not settings.preview_confirmable:
        raise AssertionError(f"Fixture did not infer a centerline: {settings.preview_message}")
    if bpy.ops.character_designer.confirm_centerline() != {"FINISHED"}:
        raise AssertionError("Confirm Centerline failed")
    output = settings.output_object
    if output is None or output.type != "CURVE":
        raise AssertionError("Confirm did not create one Curve")
    return output


def build_from_root(obj, root_indices):
    select_vertices(obj, root_indices)
    if bpy.ops.character_designer.capture_root_slice() != {"FINISHED"}:
        raise AssertionError("Root capture failed")
    select_vertices(obj, range(len(obj.data.vertices)))
    if bpy.ops.character_designer.build_centerline() != {"FINISHED"}:
        raise AssertionError("Build Center Curve failed")
    output = bpy.context.window_manager.character_designer.output_object
    if output is None or output.type != "CURVE":
        raise AssertionError("Build did not create one Curve")
    return output


def read_metadata(curve_obj):
    marker = curve_obj.get("character_designer_metadata_version")
    if marker != character_designer.METADATA_VERSION:
        raise AssertionError(f"Unexpected metadata marker {marker}")
    payload = json.loads(curve_obj["character_designer_cross_sections"])
    if payload.get("version") != character_designer.METADATA_VERSION:
        raise AssertionError("Metadata payload/marker version mismatch")
    if payload.get("space") != "SOURCE_OBJECT_LOCAL":
        raise AssertionError("Hair shaping metadata left source local space")
    if payload.get("point_count") != len(payload.get("sections", ())):
        raise AssertionError("Metadata section count mismatch")
    return payload


def make_closed_quad_strand(name, *, reverse_faces=False):
    """Three rectangular CLOSED sections plus one collapsed POINT tip.

    The strand sits at positive local Y while the object origin remains at the
    character/head center.  This makes the outward broad face unambiguous.
    """

    centers = (
        Vector((0.00, 2.00, 0.00)),
        Vector((0.00, 2.02, 0.48)),
        Vector((0.00, 2.06, 0.91)),
    )
    widths = (0.40, 0.30, 0.18)
    thicknesses = (0.10, 0.08, 0.05)
    vertices = []
    for center, width, thickness in zip(centers, widths, thicknesses):
        vertices.extend(
            (
                (center.x - width * 0.5, center.y - thickness * 0.5, center.z),
                (center.x + width * 0.5, center.y - thickness * 0.5, center.z),
                (center.x + width * 0.5, center.y + thickness * 0.5, center.z),
                (center.x - width * 0.5, center.y + thickness * 0.5, center.z),
            )
        )

    faces = []
    for ring in range(len(centers) - 1):
        current = ring * 4
        following = (ring + 1) * 4
        for side in range(4):
            next_side = (side + 1) % 4
            faces.append(
                (
                    current + side,
                    current + next_side,
                    following + next_side,
                    following + side,
                )
            )

    tip = Vector((0.00, 2.10, 1.24))
    tip_index = len(vertices)
    vertices.append(tuple(tip))
    last = (len(centers) - 1) * 4
    for side in range(4):
        next_side = (side + 1) % 4
        faces.append((last + side, last + next_side, tip_index))

    if reverse_faces:
        faces = [tuple(reversed(face)) for face in faces]
    return make_mesh_object(name, vertices, faces), widths, (*centers, tip)


def make_curved_rounded_rectangle(name, *, reverse_faces=False):
    """Eight-point rounded rectangles whose object origin points to the wrong side."""

    centers = (
        Vector((0.00, 5.00, 0.00)),
        Vector((0.00, 5.05, 0.42)),
        Vector((0.00, 5.18, 0.82)),
        Vector((0.00, 5.40, 1.18)),
        Vector((0.00, 5.70, 1.48)),
    )
    widths = (0.62, 0.54, 0.45, 0.35, 0.25)
    thicknesses = (0.14, 0.13, 0.11, 0.085, 0.06)
    vertices = []
    expected_fronts = []
    for center, tangent, width, thickness in zip(
        centers,
        character_designer._center_tangents(centers),
        widths,
        thicknesses,
    ):
        front = Vector((0.0, -1.0, 0.0))
        front -= tangent * front.dot(tangent)
        front.normalize()
        expected_fronts.append(front.copy())
        width_axis = tangent.cross(front).normalized()
        bevel = min(width * 0.12, thickness * 0.28)
        half_width = width * 0.5
        half_thickness = thickness * 0.5
        offsets = (
            (-half_width + bevel, -half_thickness),
            (half_width - bevel, -half_thickness),
            (half_width, -half_thickness + bevel),
            (half_width, half_thickness - bevel),
            (half_width - bevel, half_thickness),
            (-half_width + bevel, half_thickness),
            (-half_width, half_thickness - bevel),
            (-half_width, -half_thickness + bevel),
        )
        vertices.extend(
            tuple(center + width_axis * width_offset + front * front_offset)
            for width_offset, front_offset in offsets
        )

    faces = []
    layers = []
    for layer_index in range(len(centers)):
        start = layer_index * 8
        layers.append(tuple(range(start, start + 8)))
        if layer_index == len(centers) - 1:
            continue
        following = start + 8
        for side in range(8):
            next_side = (side + 1) % 8
            faces.append((start + side, start + next_side, following + next_side, following + side))
    if reverse_faces:
        faces = [tuple(reversed(face)) for face in faces]
    return make_mesh_object(name, vertices, faces), tuple(layers), tuple(expected_fronts)


def make_open_rows(name):
    centers = (
        Vector((0.00, 0.70, 0.00)),
        Vector((0.00, 0.72, 0.45)),
        Vector((0.00, 0.76, 0.88)),
    )
    row_offsets = (
        (-0.50, 0.00, 0.50),
        (-0.36, 0.00, 0.36),
        (-0.20, 0.00, 0.20),
    )
    vertices = []
    for center, offsets in zip(centers, row_offsets):
        vertices.extend((center.x + offset, center.y, center.z) for offset in offsets)
    faces = []
    for row in range(len(centers) - 1):
        current = row * 3
        following = (row + 1) * 3
        for column in range(2):
            faces.append(
                (
                    current + column,
                    current + column + 1,
                    following + column + 1,
                    following + column,
                )
            )
    return make_mesh_object(name, vertices, faces), (1.0, 0.72, 0.40)


def make_regular_octagon_strand(name):
    """Three regular CLOSED octagons whose artist width is the diameter."""

    centers = (
        Vector((0.0, 1.50, 0.00)),
        Vector((0.0, 1.50, 0.48)),
        Vector((0.0, 1.50, 0.91)),
    )
    radii = (0.40, 0.30, 0.18)
    side_count = 8
    vertices = []
    for center, radius in zip(centers, radii):
        for side in range(side_count):
            angle = math.tau * side / side_count
            vertices.append(
                (
                    center.x + math.cos(angle) * radius,
                    center.y + math.sin(angle) * radius,
                    center.z,
                )
            )
    faces = []
    for ring in range(len(centers) - 1):
        current = ring * side_count
        following = (ring + 1) * side_count
        for side in range(side_count):
            next_side = (side + 1) % side_count
            faces.append(
                (
                    current + side,
                    current + next_side,
                    following + next_side,
                    following + side,
                )
            )
    return make_mesh_object(name, vertices, faces), tuple(2.0 * radius for radius in radii)


def evaluated_rings(curve_obj):
    evaluated = curve_obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        vertices = [vertex.co.copy() for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()
    point_count = len(curve_obj.data.splines[0].points)
    if not vertices or len(vertices) % point_count:
        raise AssertionError(
            f"Evaluated bevel did not produce one regular ring per point: "
            f"{len(vertices)} vertices / {point_count} points"
        )
    ring_size = len(vertices) // point_count
    if ring_size < 3:
        raise AssertionError("Evaluated HALF profile has fewer than three vertices")
    return tuple(
        vertices[index * ring_size : (index + 1) * ring_size]
        for index in range(point_count)
    )


def ring_bulge_direction(ring, center):
    centroid = sum(ring, Vector()) / len(ring)
    direction = centroid - Vector(center)
    if direction.length <= 1.0e-8:
        raise AssertionError("HALF profile has no measurable bulge direction")
    return direction.normalized()


def ring_span(ring):
    return max((first - second).length for first in ring for second in ring)


def expected_point_radius(sections, point_index, span_key, maximum_span):
    if sections[point_index]["kind"] != "POINT":
        raise AssertionError("Expected a POINT section")
    adjacent_index = 1 if point_index == 0 else point_index - 1
    adjacent = sections[adjacent_index]
    if adjacent["kind"] == "POINT":
        raise AssertionError("A POINT tip has no adjacent regular section")
    return float(adjacent[span_key]) / maximum_span * TIP_RADIUS


def expected_point_span(sections, point_index, span_key):
    adjacent_index = 1 if point_index == 0 else point_index - 1
    adjacent = sections[adjacent_index]
    return float(adjacent[span_key]) * TIP_RADIUS


def assert_round_half_profile(curve_obj):
    data = curve_obj.data
    if data.bevel_mode != "ROUND":
        raise AssertionError(f"Expected ROUND bevel, got {data.bevel_mode}")
    if data.fill_mode != "HALF":
        raise AssertionError(f"Expected HALF fill, got {data.fill_mode}")
    if data.bevel_resolution != character_designer.HAIR_PROFILE_BEVEL_RESOLUTION:
        raise AssertionError("Generated Curve lost the configured bevel resolution")
    if data.bevel_depth <= 0.0:
        raise AssertionError("Generated Curve did not derive a positive bevel Depth")
    if data.extrude != 0.0 or data.taper_object is not None:
        raise AssertionError("Hair shaping unexpectedly added Extrude or a Taper object")


def test_closed_quad_round_half_size_tip_and_front():
    reset_scene()
    source, source_widths, _expected_centers = make_closed_quad_strand("ClosedQuadHair")
    curve = confirm_full_selection(source)
    metadata = read_metadata(curve)
    sections = metadata["sections"]
    points = curve.data.splines[0].points
    assert_round_half_profile(curve)

    if [section["kind"] for section in sections] != ["CLOSED", "CLOSED", "CLOSED", "POINT"]:
        raise AssertionError("CLOSED quad fixture did not preserve its point-tip topology")
    shape_spans = [section["shape_span_local"] for section in sections[:-1]]
    for actual, expected in zip(shape_spans, source_widths):
        assert_close(actual, expected, message="CLOSED shaping used a diagonal instead of a boundary width")

    maximum_span = max(shape_spans)
    assert_close(
        curve.data.bevel_depth,
        maximum_span * 0.5,
        message="Depth must be half of the largest real CLOSED cross-section width",
    )
    for index, (point, span) in enumerate(zip(points[:-1], shape_spans)):
        assert_close(
            point.radius,
            span / maximum_span,
            message=f"CLOSED point {index} Radius is not proportional to source width",
        )
    expected_tip_radius = expected_point_radius(
        sections,
        len(sections) - 1,
        "shape_span_local",
        maximum_span,
    )
    assert_close(
        points[-1].radius,
        expected_tip_radius,
        message="POINT tip Radius is not 1.5% of its adjacent regular Radius",
    )
    assert_close(metadata.get("profile_tip_radius"), TIP_RADIUS)

    rings = evaluated_rings(curve)
    for index, (ring, point, section) in enumerate(zip(rings, points, sections)):
        expected_span = (
            expected_point_span(
                sections,
                index,
                "shape_span_local",
            )
            if section["kind"] == "POINT"
            else section["shape_span_local"]
        )
        assert_close(
            ring_span(ring),
            expected_span,
            message=f"Evaluated HALF profile width mismatch at section {index}",
        )
        normal = Vector(section["shape_normal_local"]).normalized()
        bulge = ring_bulge_direction(ring, point.co.xyz)
        if bulge.dot(normal) < ORIENTATION_TOLERANCE:
            raise AssertionError(
                f"Section {index} HALF bulge does not face its recorded front: "
                f"dot={bulge.dot(normal)}"
            )

    if any(section["shape_source"] != "FRONT_WIDE_FACE" for section in sections):
        raise AssertionError("The unambiguous CLOSED quad did not use its broad front face")


def test_point_root_and_tip_scale_from_the_adjacent_regular_radius():
    def build(point_at_root):
        reset_scene()
        source, _widths, _centers = make_closed_quad_strand(
            "PointRootHair" if point_at_root else "PointTipHair"
        )
        if point_at_root:
            curve = build_from_root(source, (len(source.data.vertices) - 1,))
        else:
            curve = confirm_full_selection(source)
        metadata = read_metadata(curve)
        sections = metadata["sections"]
        points = curve.data.splines[0].points
        point_index = 0 if point_at_root else len(sections) - 1
        if sections[point_index]["kind"] != "POINT":
            raise AssertionError("The requested endpoint was not preserved as POINT")
        maximum_span = max(
            section["shape_span_local"]
            for section in sections
            if section["kind"] != "POINT"
        )
        expected_radius = expected_point_radius(
            sections,
            point_index,
            "shape_span_local",
            maximum_span,
        )
        assert_close(
            points[point_index].radius,
            expected_radius,
            message="Endpoint POINT is not 1.5% of its adjacent normal Radius",
        )
        rings = evaluated_rings(curve)
        assert_close(
            ring_span(rings[point_index]),
            expected_point_span(sections, point_index, "shape_span_local"),
            message="Endpoint POINT evaluated width is not 1.5% of its neighbor",
        )

    build(False)
    build(True)


def test_regular_octagon_closed_uses_full_profile_diameter():
    reset_scene()
    source, expected_diameters = make_regular_octagon_strand("RegularOctagonHair")
    curve = build_from_root(source, tuple(range(8)))
    metadata = read_metadata(curve)
    sections = metadata["sections"]
    points = curve.data.splines[0].points
    if any(section["kind"] != "CLOSED" for section in sections):
        raise AssertionError("Regular octagon layers were not preserved as CLOSED")

    for index, (section, expected_diameter) in enumerate(zip(sections, expected_diameters)):
        assert_close(
            section["shape_span_local"],
            expected_diameter,
            message=f"Octagon {index} used one boundary edge instead of its full diameter",
        )
        if section["boundary_edge_span_local"] >= expected_diameter * 0.5:
            raise AssertionError("The octagon fixture no longer distinguishes an edge from a diameter")

    maximum_diameter = max(expected_diameters)
    assert_close(curve.data.bevel_depth, maximum_diameter * 0.5)
    for point, expected_diameter in zip(points, expected_diameters):
        assert_close(point.radius, expected_diameter / maximum_diameter)
    for index, (ring, point, section, expected_diameter) in enumerate(
        zip(evaluated_rings(curve), points, sections, expected_diameters)
    ):
        assert_close(ring_span(ring), expected_diameter)
        bulge = ring_bulge_direction(ring, point.co.xyz)
        normal = Vector(section["shape_normal_local"]).normalized()
        if bulge.dot(normal) < ORIENTATION_TOLERANCE:
            raise AssertionError(f"Octagon section {index} Tilt lost its profile normal")
    if any(section["shape_source"] == "FRONT_WIDE_FACE" for section in sections):
        raise AssertionError("A regular octagon was mistaken for a rounded rectangle")


def test_curved_rounded_rectangle_tracks_one_outward_ribbon():
    def build(reverse_faces):
        reset_scene()
        source, layers, expected_fronts = make_curved_rounded_rectangle(
            "RoundedReverse" if reverse_faces else "RoundedForward",
            reverse_faces=reverse_faces,
        )
        curve = build_from_root(source, layers[0])
        payload = read_metadata(curve)
        normals = tuple(
            Vector(section["shape_normal_local"]).normalized()
            for section in payload["sections"]
        )
        if any(section["shape_source"] != "FRONT_WIDE_FACE" for section in payload["sections"]):
            raise AssertionError("Rounded rectangle did not use its dominant broad-face ribbon")
        if any(not section["front_face_indices"] for section in payload["sections"]):
            raise AssertionError("Rounded rectangle did not record its outward source faces")
        for index, (normal, expected, center) in enumerate(
            zip(normals, expected_fronts, (Vector(value) for value in (
                (0.00, 5.00, 0.00),
                (0.00, 5.05, 0.42),
                (0.00, 5.18, 0.82),
                (0.00, 5.40, 1.18),
                (0.00, 5.70, 1.48),
            )))
        ):
            if normal.dot(expected) < 0.95:
                raise AssertionError(f"Rounded section {index} faces the curvature interior")
            if normal.dot(center.normalized()) > -0.25:
                raise AssertionError("Fixture no longer makes the object-origin fallback incorrect")
        return normals

    forward = build(False)
    reverse = build(True)
    for index, (first, second) in enumerate(zip(forward, reverse)):
        if first.dot(second) < ORIENTATION_TOLERANCE:
            raise AssertionError(f"Reversed winding flipped rounded-ribbon front {index}")


def test_curvature_threshold_uses_the_real_turn_magnitude():
    almost_straight = (
        Vector((0.0, 0.0, 0.0)),
        Vector((0.0, 0.0, 1.0)),
        Vector((0.0, 1.0e-8, 2.0)),
    )
    if character_designer._band_curve_outward(almost_straight, 0) is not None:
        raise AssertionError("Near-straight numerical noise became full-strength curvature")


def test_open_rows_use_complete_row_span():
    reset_scene()
    source, expected_spans = make_open_rows("OpenHairRows")
    curve = build_from_root(source, (0, 1, 2))
    metadata = read_metadata(curve)
    sections = metadata["sections"]
    points = curve.data.splines[0].points
    assert_round_half_profile(curve)

    if any(section["kind"] != "OPEN" for section in sections):
        raise AssertionError("Open rows were not preserved as OPEN")
    for section, expected in zip(sections, expected_spans):
        assert_close(
            section["shape_span_local"],
            expected,
            message="OPEN shaping did not use the entire row span",
        )
    maximum_span = max(expected_spans)
    assert_close(curve.data.bevel_depth, maximum_span * 0.5)
    for point, expected in zip(points, expected_spans):
        assert_close(point.radius, expected / maximum_span)

    for index, (ring, point, section, expected) in enumerate(
        zip(evaluated_rings(curve), points, sections, expected_spans)
    ):
        assert_close(ring_span(ring), expected, message=f"OPEN evaluated width mismatch at {index}")
        bulge = ring_bulge_direction(ring, point.co.xyz)
        normal = Vector(section["shape_normal_local"]).normalized()
        if bulge.dot(normal) < ORIENTATION_TOLERANCE:
            raise AssertionError(f"OPEN section {index} Tilt lost its shape normal")


def test_closed_front_is_stable_under_reversed_winding():
    def build(reverse):
        reset_scene()
        source, _widths, _centers = make_closed_quad_strand(
            "ClosedReverse" if reverse else "ClosedForward",
            reverse_faces=reverse,
        )
        curve = confirm_full_selection(source)
        metadata = read_metadata(curve)
        normals = [Vector(section["shape_normal_local"]).normalized() for section in metadata["sections"]]
        bulges = [
            ring_bulge_direction(ring, point.co.xyz)
            for ring, point in zip(evaluated_rings(curve), curve.data.splines[0].points)
        ]
        return curve.data.bevel_depth, [point.radius for point in curve.data.splines[0].points], normals, bulges

    forward_depth, forward_radii, forward_normals, forward_bulges = build(False)
    reverse_depth, reverse_radii, reverse_normals, reverse_bulges = build(True)
    assert_close(forward_depth, reverse_depth)
    for forward, reverse in zip(forward_radii, reverse_radii):
        assert_close(forward, reverse)
    for index, (forward_normal, reverse_normal, forward_bulge, reverse_bulge) in enumerate(
        zip(forward_normals, reverse_normals, forward_bulges, reverse_bulges)
    ):
        if forward_normal.dot(reverse_normal) < ORIENTATION_TOLERANCE:
            raise AssertionError(f"Reversed winding flipped geometric front at section {index}")
        if forward_bulge.dot(reverse_bulge) < ORIENTATION_TOLERANCE:
            raise AssertionError(f"Reversed winding flipped evaluated HALF bulge at section {index}")


def test_nonuniform_source_transform_is_not_baked_twice():
    reset_scene()
    source, _widths, _centers = make_closed_quad_strand("TransformedClosedHair")
    source.matrix_world = (
        Matrix.Translation((12.0, -7.5, 3.25))
        @ Matrix.Rotation(math.radians(37.0), 4, "Z")
        @ Matrix.Diagonal((2.0, 0.5, 1.4, 1.0))
    )
    source_matrix = source.matrix_world.copy()
    curve = confirm_full_selection(source)
    metadata = read_metadata(curve)
    assert_matrix_close(curve.matrix_world, source_matrix)

    shape_spans = [
        section["shape_span_local"]
        for section in metadata["sections"]
        if section["kind"] != "POINT"
    ]
    assert_close(curve.data.bevel_depth, max(shape_spans) * 0.5)
    for point, section in zip(curve.data.splines[0].points, metadata["sections"]):
        expected = (
            expected_point_radius(
                metadata["sections"],
                len(metadata["sections"]) - 1,
                "shape_span_local",
                max(shape_spans),
            )
            if section["kind"] == "POINT"
            else section["shape_span_local"] / max(shape_spans)
        )
        assert_close(point.radius, expected)

    # Local evaluated geometry must remain source-local; matrix_world applies
    # the non-uniform transform exactly once at object evaluation/render time.
    for ring, point, section in zip(
        evaluated_rings(curve),
        curve.data.splines[0].points,
        metadata["sections"],
    ):
        expected = (
            expected_point_span(
                metadata["sections"],
                len(metadata["sections"]) - 1,
                "shape_span_local",
            )
            if section["kind"] == "POINT"
            else section["shape_span_local"]
        )
        assert_close(ring_span(ring), expected)


def test_version_two_metadata_remains_readable_for_legacy_curves():
    reset_scene()
    source, _widths, _centers = make_closed_quad_strand("LegacyMetadataHair")
    curve = confirm_full_selection(source)
    payload = read_metadata(curve)

    payload["version"] = 2
    payload.pop("profile_tip_radius", None)
    version_three_keys = {
        "boundary_edge_span_local",
        "boundary_edge_pair",
        "boundary_edge_vector_local",
        "shape_span_local",
        "shape_width_axis_local",
        "shape_normal_local",
        "shape_source",
        "front_face_indices",
    }
    for section in payload["sections"]:
        for key in version_three_keys:
            section.pop(key, None)
    curve["character_designer_metadata_version"] = 2
    curve["character_designer_cross_sections"] = json.dumps(
        payload,
        separators=(",", ":"),
        allow_nan=False,
    )

    parsed = character_designer._curve_cross_section_metadata(curve)
    if parsed is None or parsed.get("version") != 2:
        raise AssertionError("A valid metadata-v2 Curve was rejected after the v3 upgrade")
    depth, radii, tilts = character_designer._curve_profile_parameters(parsed)
    legacy_spans = [
        section["max_profile_span_local"]
        for section in parsed["sections"]
        if section["kind"] != "POINT"
    ]
    maximum_span = max(legacy_spans)
    assert_close(depth, maximum_span * 0.5)
    for radius, section in zip(radii, parsed["sections"]):
        expected = (
            expected_point_radius(
                parsed["sections"],
                len(parsed["sections"]) - 1,
                "max_profile_span_local",
                maximum_span,
            )
            if section["kind"] == "POINT"
            else section["max_profile_span_local"] / maximum_span
        )
        assert_close(radius, expected)
    if len(tilts) != len(parsed["sections"]) or not all(math.isfinite(value) for value in tilts):
        raise AssertionError("Legacy v2 Tilt fallback is incomplete or non-finite")


def main():
    character_designer.register()
    tests = (
        test_closed_quad_round_half_size_tip_and_front,
        test_point_root_and_tip_scale_from_the_adjacent_regular_radius,
        test_regular_octagon_closed_uses_full_profile_diameter,
        test_curved_rounded_rectangle_tracks_one_outward_ribbon,
        test_curvature_threshold_uses_the_real_turn_magnitude,
        test_open_rows_use_complete_row_span,
        test_closed_front_is_stable_under_reversed_winding,
        test_nonuniform_source_transform_is_not_baked_twice,
        test_version_two_metadata_remains_readable_for_legacy_curves,
    )
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        if hasattr(bpy.types.WindowManager, "character_designer"):
            character_designer.unregister()
    print(f"PASS Hair Profile Shaping {len(tests)} tests")


if __name__ == "__main__":
    main()
