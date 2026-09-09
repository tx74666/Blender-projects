"""Blender 5.2 integration tests for editable Hair Centerline front alignment.

Run with::

    blender --background --factory-startup --python-exit-code 1 \
        --python tests/test_hair_front_alignment_blender.py

All fixtures are created in memory.  The script never opens or saves a .blend.
"""

import json
import math
import os
import sys
import traceback
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

import character_designer


TOLERANCE = 2.0e-5
FRONT_TOLERANCE = 4.0e-4
RECORDED_SOURCE_PLANE_TOLERANCE = 1.0e-4
V3_SECTION_KEYS = {
    "kind",
    "max_width_local",
    "diameter_pair",
    "diameter_vector_local",
    "max_profile_span_local",
    "profile_span_pair",
    "profile_span_vector_local",
    "boundary_edge_span_local",
    "boundary_edge_pair",
    "boundary_edge_vector_local",
    "anchor_vertex",
    "tangent_local",
    "width_axis_local",
    "normal_local",
    "mesh_normal_local",
    "band_face_count",
    "width_axis_source",
    "orientation_source",
    "shape_span_local",
    "shape_width_axis_local",
    "shape_normal_local",
    "shape_source",
    "front_face_indices",
}


def assert_close(actual, expected, tolerance=TOLERANCE, message=""):
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(message or f"Expected {expected}, got {actual}")


def assert_vector_close(actual, expected, tolerance=TOLERANCE, message=""):
    difference = (Vector(actual) - Vector(expected)).length
    if difference > tolerance:
        raise AssertionError(message or f"Expected {tuple(expected)}, got {tuple(actual)}")


def assert_contract():
    state = bpy.context.window_manager.character_designer
    if not hasattr(state, "centerline_placement"):
        raise AssertionError("CharacterDesignerState is missing centerline_placement")
    if not hasattr(state, "centerline_blend_factor"):
        raise AssertionError("CharacterDesignerState is missing centerline_blend_factor")
    if not hasattr(state, "align_front_surface"):
        raise AssertionError("CharacterDesignerState is missing align_front_surface")
    if not hasattr(state, "update_target_curve"):
        raise AssertionError("CharacterDesignerState is missing update_target_curve")
    if not hasattr(state, "centerline_control_target"):
        raise AssertionError("CharacterDesignerState is missing centerline_control_target")
    for identifier in (
        "CHARACTER_DESIGNER_OT_set_front_alignment",
        "CHARACTER_DESIGNER_OT_set_update_target",
        "CHARACTER_DESIGNER_OT_update_existing_centerline",
        "CHARACTER_DESIGNER_OT_generate_or_update_centerline",
    ):
        if bpy.types.Operator.bl_rna_get_subclass_py(identifier) is None:
            raise AssertionError(f"Missing operator contract {identifier}")
    placement_property = state.bl_rna.properties["centerline_placement"]
    identifiers = tuple(item.identifier for item in placement_property.enum_items)
    expected = (
        character_designer.HAIR_ALIGNMENT_CENTERED,
        character_designer.HAIR_ALIGNMENT_FRONT_FLUSH,
        character_designer.HAIR_ALIGNMENT_BLEND,
    )
    if identifiers != expected or placement_property.is_enum_flag:
        raise AssertionError(
            f"Placement must be one three-way enum; got {identifiers}"
        )
    if character_designer._alignment_label(character_designer.HAIR_ALIGNMENT_BLEND) != "Blend":
        raise AssertionError("Blend alignment has no truthful status label")
    factor_property = state.bl_rna.properties["centerline_blend_factor"]
    if (
        factor_property.type != "FLOAT"
        or factor_property.subtype != "FACTOR"
        or float(factor_property.hard_min) != 0.0
        or float(factor_property.hard_max) != 1.0
    ):
        raise AssertionError("Blend factor must be one 0..1 FACTOR slider")
    assert_close(state.centerline_blend_factor, 0.5, message="Blend default is not 0.5")


def reset_scene():
    state = getattr(bpy.context.window_manager, "character_designer", None)
    if state is not None:
        if hasattr(state, "centerline_control_target"):
            state.centerline_control_target = None
        if getattr(state, "live_preview_enabled", False):
            state.live_preview_enabled = False
        if hasattr(state, "centerline_placement"):
            state.centerline_placement = character_designer.HAIR_ALIGNMENT_CENTERED
        if hasattr(state, "centerline_blend_factor"):
            state.centerline_blend_factor = character_designer.HAIR_BLEND_DEFAULT
        if hasattr(state, "align_front_surface"):
            state.align_front_surface = False
        if hasattr(state, "update_target_curve"):
            state.update_target_curve = None
        state.output_object = None
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


def center_tangents(centers):
    tangents = []
    for index, center in enumerate(centers):
        if index == 0:
            tangent = centers[1] - center
        elif index == len(centers) - 1:
            tangent = center - centers[index - 1]
        else:
            tangent = (center - centers[index - 1]).normalized()
            tangent += (centers[index + 1] - center).normalized()
        tangent.normalize()
        tangents.append(tangent)
    return tuple(tangents)


def make_curved_quad_strand(name, *, reverse_faces=False, point_tip=True):
    """Five curved, differently-sized rectangles and an optional point tip."""

    centers = (
        Vector((0.00, 2.00, 0.00)),
        Vector((0.09, 2.04, 0.38)),
        Vector((-0.04, 2.10, 0.77)),
        Vector((0.12, 2.17, 1.15)),
        Vector((0.04, 2.25, 1.49)),
    )
    widths = (0.48, 0.39, 0.31, 0.23, 0.14)
    thicknesses = (0.13, 0.11, 0.09, 0.065, 0.045)
    vertices = []
    for center, tangent, width, thickness in zip(
        centers, center_tangents(centers), widths, thicknesses
    ):
        front = Vector((0.0, 1.0, 0.0))
        front -= tangent * front.dot(tangent)
        front.normalize()
        width_axis = tangent.cross(front).normalized()
        vertices.extend(
            tuple(
                center + width_axis * width_sign * width * 0.5
                + front * front_sign * thickness * 0.5
            )
            for width_sign, front_sign in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        )

    faces = []
    for layer_index in range(len(centers) - 1):
        first = layer_index * 4
        second = (layer_index + 1) * 4
        for side in range(4):
            following = (side + 1) % 4
            faces.append((first + side, first + following, second + following, second + side))

    layers = [tuple(range(index * 4, index * 4 + 4)) for index in range(len(centers))]
    if point_tip:
        last_center = centers[-1]
        prior = centers[-2]
        tip = last_center + (last_center - prior).normalized() * 0.31
        tip_index = len(vertices)
        vertices.append(tuple(tip))
        last = (len(centers) - 1) * 4
        for side in range(4):
            faces.append((last + side, last + (side + 1) % 4, tip_index))
        layers.append((tip_index,))

    if reverse_faces:
        faces = [tuple(reversed(face)) for face in faces]
    return make_mesh_object(name, vertices, faces), tuple(layers)


def select_vertices(obj, indices, *, active_index=None):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.select_history.clear()
    selected = set(indices)
    for vertex in bm.verts:
        vertex.select_set(vertex.index in selected)
    bm.select_flush_mode()
    if active_index is not None:
        bm.select_history.add(bm.verts[active_index])
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)


def build_centerline(source, layers, *, included_layer_count=None, front_flush=False):
    included = layers if included_layer_count is None else layers[:included_layer_count]
    select_vertices(source, included[0])
    if bpy.ops.character_designer.capture_root_slice() != {"FINISHED"}:
        raise AssertionError("Root capture failed")
    selected_indices = tuple(index for layer in included for index in layer)
    select_vertices(source, selected_indices)
    state = bpy.context.window_manager.character_designer
    state.align_front_surface = bool(front_flush)
    result = bpy.ops.character_designer.build_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Build Center Curve failed: {result}")
    curve = state.output_object
    if curve is None or curve.type != "CURVE":
        raise AssertionError("Build did not create one Curve")
    return curve


def activate_object(obj):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def enter_curve_edit(curve, selected_indices=(1, 3)):
    activate_object(curve)
    if bpy.ops.object.mode_set(mode="EDIT") != {"FINISHED"}:
        raise AssertionError("Could not enter Curve Edit Mode")
    selected = set(selected_indices)
    for spline in curve.data.splines:
        for index, point in enumerate(spline.points):
            point.select = index in selected
    return curve_edit_context_snapshot(curve)


def curve_edit_context_snapshot(curve):
    return (
        bpy.context.mode,
        bpy.context.edit_object.as_pointer() if bpy.context.edit_object else 0,
        bpy.context.view_layer.objects.active.as_pointer()
        if bpy.context.view_layer.objects.active
        else 0,
        tuple(sorted(obj.as_pointer() for obj in bpy.context.selected_objects)),
        tuple(
            tuple((bool(point.select), bool(getattr(point, "hide", False))) for point in spline.points)
            for spline in curve.data.splines
        ),
    )


def stored_layers(curve):
    return tuple(
        tuple(int(index) for index in layer)
        for layer in json.loads(curve["character_designer_layer_vertices"])
    )


def source_centers(source, layers):
    return tuple(
        sum((source.data.vertices[index].co for index in layer), Vector()) / len(layer)
        for layer in layers
    )


def curve_points(curve):
    return tuple(point.co.xyz.copy() for point in curve.data.splines[0].points)


def metadata(curve):
    return json.loads(curve["character_designer_cross_sections"])


def assert_centered(curve, source, *, tolerance=TOLERANCE):
    layers = stored_layers(curve)
    centers = source_centers(source, layers)
    points = curve_points(curve)
    if len(points) != len(centers):
        raise AssertionError("Curve/source layer count mismatch")
    for index, (point, center) in enumerate(zip(points, centers)):
        assert_vector_close(
            point,
            center,
            tolerance,
            f"Centered point {index} is not the exact source-layer mean",
        )


def evaluated_rings(curve):
    evaluated = curve.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        vertices = tuple(vertex.co.copy() for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()
    point_count = len(curve.data.splines[0].points)
    if not vertices or len(vertices) % point_count:
        raise AssertionError("Evaluated HALF profile cannot be divided into control-point rings")
    ring_size = len(vertices) // point_count
    return tuple(
        vertices[index * ring_size : (index + 1) * ring_size]
        for index in range(point_count)
    )


def target_planes(curve, source):
    """Independently reconstruct the authored front plane at every source layer."""

    layers = stored_layers(curve)
    centers = source_centers(source, layers)
    payload = metadata(curve)
    bm = bmesh.new()
    try:
        bm.from_mesh(source.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        bands = character_designer._front_band_descriptors(bm, layers)
        results = []
        for index, (layer, center, section) in enumerate(
            zip(layers, centers, payload["sections"])
        ):
            normal = Vector(section["shape_normal_local"]).normalized()
            if section["kind"] == "POINT":
                results.append((center.copy(), normal))
                continue
            distances = []
            for band_index in (index - 1, index):
                if band_index < 0 or band_index >= len(bands):
                    continue
                descriptor = bands[band_index]
                if descriptor is None:
                    continue
                same_layer = character_designer._face_same_layer_edge(
                    descriptor["face"], set(layer)
                )
                if same_layer is not None:
                    first, second = same_layer[0]
                    midpoint = (bm.verts[first].co + bm.verts[second].co) * 0.5
                    distances.append((midpoint - center).dot(normal))
                    continue
                face = descriptor["face"]
                denominator = face.normal.dot(normal)
                if abs(denominator) > 1.0e-8:
                    distances.append(
                        face.normal.dot(face.calc_center_median() - center) / denominator
                    )
            if not distances:
                raise AssertionError(f"Fixture section {index} has no reconstructable front plane")
            distance = sum(distances) / len(distances)
            results.append((center + normal * distance, normal))
        return tuple(results)
    finally:
        bm.free()


def assert_front_flush(curve, source, *, world_space=False):
    rings = evaluated_rings(curve)
    planes = target_planes(curve, source)
    if len(rings) != len(planes):
        raise AssertionError("Evaluated/target section count mismatch")
    linear = curve.matrix_world.to_3x3()
    world_normal_matrix = linear.inverted().transposed()
    for index, (ring, (plane_point, normal)) in enumerate(zip(rings, planes)):
        # The source plane is immutable. Projecting its normal to the displaced
        # Curve tangent would test the bevel's effective frame instead and can
        # hide an actual miss against the authored hair surface.
        if world_space:
            transformed_ring = tuple(curve.matrix_world @ point for point in ring)
            transformed_point = curve.matrix_world @ plane_point
            transformed_normal = (world_normal_matrix @ normal).normalized()
            error = max((point - transformed_point).dot(transformed_normal) for point in transformed_ring)
            scale = max(curve.matrix_world.to_scale())
            tolerance = FRONT_TOLERANCE * max(1.0, float(scale))
        else:
            error = max((point - plane_point).dot(normal) for point in ring)
            tolerance = FRONT_TOLERANCE
        if abs(error) > tolerance:
            raise AssertionError(
                f"Section {index} evaluated front misses the authored plane by {error}"
            )


def assert_profile_faces_outward(curve):
    """Verify the evaluated Half profile stays on the recorded outward side."""

    rings = evaluated_rings(curve)
    points = curve_points(curve)
    sections = metadata(curve)["sections"]
    spline_points = curve.data.splines[0].points
    if not (len(rings) == len(points) == len(sections) == len(spline_points)):
        raise AssertionError("Profile/outward section count mismatch")
    for index, (ring, axis, section, point) in enumerate(
        zip(rings, points, sections, spline_points)
    ):
        normal = Vector(section["shape_normal_local"]).normalized()
        projections = tuple((vertex - axis).dot(normal) for vertex in ring)
        expected_radius = float(curve.data.bevel_depth) * float(point.radius)
        if max(projections) <= max(1.0e-7, expected_radius * 0.25):
            raise AssertionError(
                f"Section {index} has no evaluated bulge along the recorded front"
            )
        if abs(min(projections)) > max(projections) + FRONT_TOLERANCE:
            raise AssertionError(
                f"Section {index} Half profile points toward the recorded back"
            )


def shape_normals(curve):
    return tuple(
        Vector(section["shape_normal_local"]).normalized()
        for section in metadata(curve)["sections"]
    )


def assert_same_outward_metadata(first, second):
    if len(first) != len(second):
        raise AssertionError("Placement switch changed the outward section count")
    for index, (left, right) in enumerate(zip(first, second)):
        if left.dot(right) < 0.999999:
            raise AssertionError(f"Placement switch flipped outward normal {index}")


def assert_recorded_source_plane_flush(curve, *, world_space=False):
    """Measure against v4's fixed source plane, never a reprojected Curve normal."""

    payload = metadata(curve)
    rings = evaluated_rings(curve)
    sections = payload.get("sections", ())
    if len(rings) != len(sections):
        raise AssertionError("Evaluated/source-plane section count mismatch")
    linear = curve.matrix_world.to_3x3()
    world_normal_matrix = linear.inverted().transposed()
    for index, (ring, section) in enumerate(zip(rings, sections)):
        plane_point = Vector(section["front_target_local"])
        source_normal = Vector(section["shape_normal_local"]).normalized()
        if world_space:
            transformed_ring = tuple(curve.matrix_world @ point for point in ring)
            transformed_point = curve.matrix_world @ plane_point
            transformed_normal = (world_normal_matrix @ source_normal).normalized()
            error = max(
                (point - transformed_point).dot(transformed_normal)
                for point in transformed_ring
            )
            tolerance = RECORDED_SOURCE_PLANE_TOLERANCE * max(
                1.0, float(max(curve.matrix_world.to_scale()))
            )
        else:
            error = max((point - plane_point).dot(source_normal) for point in ring)
            tolerance = RECORDED_SOURCE_PLANE_TOLERANCE
        if abs(error) > tolerance:
            raise AssertionError(
                f"Section {index} HALF front misses its recorded shape-normal plane "
                f"by {error}; tolerance={tolerance}"
            )


def data_fingerprint(curve):
    properties = tuple(sorted((str(key), repr(curve[key])) for key in curve.keys()))
    points = tuple(
        (
            tuple(float(value) for value in point.co),
            float(point.radius),
            float(point.tilt),
        )
        for point in curve.data.splines[0].points
    )
    return (
        curve.data.as_pointer(),
        properties,
        points,
        curve.data.bevel_mode,
        curve.data.fill_mode,
        float(curve.data.bevel_depth),
        int(curve.data.splines[0].material_index),
    )


def curve_data_fingerprint(data):
    return (
        data.dimensions,
        data.bevel_mode,
        data.fill_mode,
        float(data.bevel_depth),
        tuple(material.as_pointer() if material is not None else 0 for material in data.materials),
        tuple(
            (
                spline.type,
                bool(spline.use_cyclic_u),
                int(spline.material_index),
                tuple(
                    (
                        tuple(float(value) for value in point.co),
                        float(point.radius),
                        float(point.tilt),
                    )
                    for point in spline.points
                ),
            )
            for spline in data.splines
        ),
    )


def add_test_materials(curve, prefix):
    first = bpy.data.materials.new(f"{prefix}_First")
    second = bpy.data.materials.new(f"{prefix}_Second")
    curve.data.materials.append(first)
    curve.data.materials.append(second)
    curve.data.splines[0].material_index = 1
    return first, second


def link_shared_data_object(curve, name):
    shared = bpy.data.objects.new(name, curve.data)
    bpy.context.scene.collection.objects.link(shared)
    return shared


def assert_object_envelope_preserved(curve, object_pointer, matrix, collections, materials):
    if curve.as_pointer() != object_pointer:
        raise AssertionError("Update replaced the target Object")
    for row in range(4):
        for column in range(4):
            assert_close(curve.matrix_world[row][column], matrix[row][column])
    if tuple(curve.users_collection) != collections:
        raise AssertionError("Update changed the target's collection links")
    if tuple(curve.data.materials) != materials:
        raise AssertionError("Update did not preserve Curve material slots")
    if curve.data.splines[0].material_index != 1:
        raise AssertionError("Update lost the spline's material-slot assignment")


def selection_snapshot(obj):
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    active = bm.select_history.active
    active_signature = (
        type(active).__name__,
        getattr(active, "index", -1),
    ) if active is not None else None
    return (
        tuple(vertex.index for vertex in bm.verts if vertex.select),
        tuple(edge.index for edge in bm.edges if edge.select),
        tuple(face.index for face in bm.faces if face.select),
        tuple(bool(value) for value in bpy.context.tool_settings.mesh_select_mode),
        active_signature,
    )


def set_alignment(curve, mode):
    activate_object(curve)
    result = bpy.ops.character_designer.set_front_alignment(mode=mode)
    if result != {"FINISHED"}:
        raise AssertionError(f"set_front_alignment({mode}) failed: {result}")


def assert_blend_factor(curve, expected):
    key = character_designer.HAIR_BLEND_FACTOR_KEY
    if key not in curve:
        raise AssertionError("Curve did not persist its Blend factor")
    assert_close(
        curve[key],
        expected,
        tolerance=1.0e-8,
        message=f"Expected persisted Blend factor {expected}, got {curve.get(key)}",
    )


def test_toggle_off_is_exactly_centered_and_selection_records_target():
    reset_scene()
    source, layers = make_curved_quad_strand("ToggleOff")
    curve = build_centerline(source, layers, front_flush=False)
    if curve.get("character_designer_alignment") != "CENTERED":
        raise AssertionError("Toggle-off output is not tagged CENTERED")
    assert_centered(curve, source)
    activate_object(curve)
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("Selected generated Curve could not become the update target")
    state = bpy.context.window_manager.character_designer
    if state.update_target_curve is not curve:
        raise AssertionError("Update target did not follow the selected Curve")
    if state.align_front_surface:
        raise AssertionError("CENTERED target did not drive the alignment toggle off")


def test_toggle_on_builds_evaluated_front_flush_including_point():
    reset_scene()
    source, layers = make_curved_quad_strand("ToggleOn")
    curve = build_centerline(source, layers, front_flush=True)
    if curve.get("character_designer_alignment") != "FRONT_FLUSH":
        raise AssertionError("Toggle-on output is not tagged FRONT_FLUSH")
    if metadata(curve)["sections"][-1]["kind"] != "POINT":
        raise AssertionError("Fixture lost its POINT tip")
    assert_front_flush(curve, source)
    state = bpy.context.window_manager.character_designer
    state.align_front_surface = False
    activate_object(curve)
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("FRONT_FLUSH Curve could not become the update target")
    if not state.align_front_surface:
        raise AssertionError("FRONT_FLUSH target did not drive the alignment toggle on")


def test_single_action_switches_three_placements_on_the_matching_curve():
    reset_scene()
    source, layers = make_curved_quad_strand("SingleAction")
    selected = tuple(index for layer in layers for index in layer)
    select_vertices(source, selected, active_index=layers[0][0])
    before_selection = selection_snapshot(source)
    state = bpy.context.window_manager.character_designer
    state.centerline_placement = character_designer.HAIR_ALIGNMENT_CENTERED

    result = bpy.ops.character_designer.generate_or_update_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Single-action create failed: {result}")
    curve = state.output_object
    if curve is None or curve.get("character_designer_alignment") != "CENTERED":
        raise AssertionError("Single-action create ignored Centered placement")
    if state.centerline_placement != character_designer.HAIR_ALIGNMENT_CENTERED:
        raise AssertionError("Single-action create changed the selected placement")
    assert_centered(curve, source)
    assert_profile_faces_outward(curve)
    centered_points = curve_points(curve)
    centered_normals = shape_normals(curve)
    centered_radii = tuple(point.radius for point in curve.data.splines[0].points)
    centered_depth = float(curve.data.bevel_depth)
    object_pointer = curve.as_pointer()
    object_name = curve.name
    candidates = tuple(
        obj
        for obj in bpy.context.scene.objects
        if obj.get("character_designer_source") == source.name
        and obj.get("character_designer_generator") == character_designer.GENERATOR_ID
    )
    if candidates != (curve,):
        raise AssertionError("Single-action create produced an unexpected candidate set")

    state.centerline_placement = character_designer.HAIR_ALIGNMENT_FRONT_FLUSH
    result = bpy.ops.character_designer.generate_or_update_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Surface overwrite failed: {result}")
    if state.output_object.as_pointer() != object_pointer or state.output_object.name != object_name:
        raise AssertionError("Single-action overwrite replaced the Curve object")
    if curve.get("character_designer_alignment") != "FRONT_FLUSH":
        raise AssertionError("Single-action overwrite ignored Surface placement")
    if state.centerline_placement != character_designer.HAIR_ALIGNMENT_FRONT_FLUSH:
        raise AssertionError("Surface overwrite changed the selected placement")
    assert_front_flush(curve, source)
    assert_profile_faces_outward(curve)
    surface_points = curve_points(curve)
    assert_same_outward_metadata(centered_normals, shape_normals(curve))
    surface_radii = tuple(point.radius for point in curve.data.splines[0].points)
    if surface_radii != centered_radii or float(curve.data.bevel_depth) != centered_depth:
        raise AssertionError("Surface placement changed profile sizing")

    state.centerline_placement = character_designer.HAIR_ALIGNMENT_BLEND
    state.centerline_blend_factor = 0.25
    result = bpy.ops.character_designer.generate_or_update_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Blend overwrite failed: {result}")
    if state.output_object.as_pointer() != object_pointer or state.output_object.name != object_name:
        raise AssertionError("Blend overwrite replaced the Curve object")
    if curve.get("character_designer_alignment") != "BLEND":
        raise AssertionError("Single-action overwrite ignored Blend placement")
    if state.centerline_placement != character_designer.HAIR_ALIGNMENT_BLEND:
        raise AssertionError("Blend overwrite changed the selected placement")
    assert_close(state.centerline_blend_factor, 0.25)
    assert_blend_factor(curve, 0.25)
    blend_points = curve_points(curve)
    for index, (centered, surface, blended) in enumerate(
        zip(centered_points, surface_points, blend_points)
    ):
        assert_vector_close(
            blended,
            centered + (surface - centered) * 0.25,
            message=f"Blend point {index} does not use Mix 0.25",
        )
    assert_profile_faces_outward(curve)
    assert_same_outward_metadata(centered_normals, shape_normals(curve))
    blend_radii = tuple(point.radius for point in curve.data.splines[0].points)
    if blend_radii != centered_radii or float(curve.data.bevel_depth) != centered_depth:
        raise AssertionError("Blend placement changed profile sizing")
    if selection_snapshot(source) != before_selection:
        raise AssertionError("Single-action workflow changed the artist's mesh selection")
    candidates = tuple(
        obj
        for obj in bpy.context.scene.objects
        if obj.get("character_designer_source") == source.name
        and obj.get("character_designer_generator") == character_designer.GENERATOR_ID
    )
    if candidates != (curve,):
        raise AssertionError("Single-action overwrite created a duplicate Curve")

    quarter_data_pointer = curve.data.as_pointer()
    state.centerline_blend_factor = 0.75
    result = bpy.ops.character_designer.generate_or_update_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Blend 0.75 overwrite failed: {result}")
    if curve.as_pointer() != object_pointer:
        raise AssertionError("Changing Blend Mix replaced the Curve object")
    if curve.data.as_pointer() == quarter_data_pointer:
        raise AssertionError("Changing Blend Mix was incorrectly treated as a no-op")
    assert_blend_factor(curve, 0.75)
    for index, (centered, surface, blended) in enumerate(
        zip(centered_points, surface_points, curve_points(curve))
    ):
        assert_vector_close(
            blended,
            centered + (surface - centered) * 0.75,
            message=f"Blend point {index} does not use Mix 0.75",
        )
    assert_profile_faces_outward(curve)

    unchanged_data_pointer = curve.data.as_pointer()
    unchanged_fingerprint = data_fingerprint(curve)
    result = bpy.ops.character_designer.generate_or_update_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Repeated Blend 0.75 update failed: {result}")
    if (
        curve.data.as_pointer() != unchanged_data_pointer
        or data_fingerprint(curve) != unchanged_fingerprint
    ):
        raise AssertionError("Repeated Blend 0.75 rewrote an unchanged Curve")

    select_vertices(source, selected, active_index=layers[-1][0])
    result = bpy.ops.character_designer.generate_or_update_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Reversed-layer overwrite failed: {result}")
    if state.output_object.as_pointer() != object_pointer:
        raise AssertionError("Reversed selection order did not match the same Curve")
    assert_blend_factor(curve, 0.75)
    assert_profile_faces_outward(curve)


def test_single_action_object_mode_refresh_preserves_saved_blend_factor():
    reset_scene()
    source, layers = make_curved_quad_strand("SingleRefresh")
    curve = build_centerline(source, layers, front_flush=False)
    object_pointer = curve.as_pointer()
    state = bpy.context.window_manager.character_designer
    state.centerline_blend_factor = 0.37
    state.centerline_placement = character_designer.HAIR_ALIGNMENT_BLEND
    if bpy.ops.character_designer.generate_or_update_centerline() != {"FINISHED"}:
        raise AssertionError("Could not prepare a saved Blend 0.37 Curve")
    assert_blend_factor(curve, 0.37)
    payload = metadata(curve)
    centered_points = character_designer._curve_profile_solution(
        payload,
        character_designer.HAIR_ALIGNMENT_CENTERED,
    )[0]
    surface_points = character_designer._curve_profile_solution(
        payload,
        character_designer.HAIR_ALIGNMENT_FRONT_FLUSH,
    )[0]
    for index, (centered, surface, blended) in enumerate(
        zip(centered_points, surface_points, curve_points(curve))
    ):
        assert_vector_close(
            blended,
            centered + (surface - centered) * 0.37,
            message=f"Prepared Blend point {index} does not use Mix 0.37",
        )
    assert_profile_faces_outward(curve)

    activate_object(curve)
    state.centerline_placement = character_designer.HAIR_ALIGNMENT_FRONT_FLUSH
    state.centerline_blend_factor = 0.91
    data_pointer = curve.data.as_pointer()
    before = data_fingerprint(curve)
    if bpy.ops.character_designer.generate_or_update_centerline() != {"FINISHED"}:
        raise AssertionError("Saved Blend Object Mode refresh failed")
    if curve.as_pointer() != object_pointer:
        raise AssertionError("Object Mode refresh replaced the Curve object")
    if curve.data.as_pointer() != data_pointer or data_fingerprint(curve) != before:
        raise AssertionError("Unchanged Object Mode refresh rewrote the saved Blend Curve")
    if curve.get("character_designer_alignment") != "BLEND":
        raise AssertionError("Object Mode refresh used session placement instead of saved Blend")
    assert_blend_factor(curve, 0.37)
    if state.centerline_placement != character_designer.HAIR_ALIGNMENT_BLEND:
        raise AssertionError("Object Mode refresh did not hydrate the saved placement")
    assert_close(state.centerline_blend_factor, 0.37)
    if curve.get("character_designer_metadata_version") != character_designer.METADATA_VERSION:
        raise AssertionError("Object Mode refresh did not upgrade centerline metadata")

    state.centerline_placement = character_designer.HAIR_ALIGNMENT_CENTERED
    state.centerline_blend_factor = 0.12
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("Saved Blend Curve could not hydrate the update target")
    if state.centerline_placement != character_designer.HAIR_ALIGNMENT_BLEND:
        raise AssertionError("Update target did not restore the saved Blend placement")
    assert_close(state.centerline_blend_factor, 0.37)


def test_curve_edit_controls_update_placement_and_mix_immediately():
    reset_scene()
    source, layers = make_curved_quad_strand("CurveEditLive")
    curve = build_centerline(source, layers, front_flush=False)
    payload = metadata(curve)
    centered = character_designer._curve_profile_solution(
        payload,
        character_designer.HAIR_ALIGNMENT_CENTERED,
    )[0]
    surface = character_designer._curve_profile_solution(
        payload,
        character_designer.HAIR_ALIGNMENT_FRONT_FLUSH,
    )[0]
    object_pointer = curve.as_pointer()
    data_pointer = curve.data.as_pointer()
    object_count = len(bpy.context.scene.objects)
    curve_data_count = len(bpy.data.curves)
    edit_context = enter_curve_edit(curve)
    state = bpy.context.window_manager.character_designer
    character_designer._bind_centerline_controls(state, curve)

    if bpy.ops.character_designer.set_front_alignment(
        mode=character_designer.HAIR_ALIGNMENT_FRONT_FLUSH
    ) != {"FINISHED"}:
        raise AssertionError("Surface did not apply in Curve Edit Mode")
    for index, (actual, expected) in enumerate(zip(curve_points(curve), surface)):
        assert_vector_close(actual, expected, message=f"Edit Surface point {index} did not move")
    if curve.get("character_designer_alignment") != character_designer.HAIR_ALIGNMENT_FRONT_FLUSH:
        raise AssertionError("Edit Surface did not persist its alignment")
    if curve_edit_context_snapshot(curve) != edit_context:
        raise AssertionError("Edit Surface changed Curve Edit Mode or point selection")

    if bpy.ops.character_designer.set_front_alignment(
        mode=character_designer.HAIR_ALIGNMENT_CENTERED
    ) != {"FINISHED"}:
        raise AssertionError("Centered did not apply in Curve Edit Mode")
    for index, (actual, expected) in enumerate(zip(curve_points(curve), centered)):
        assert_vector_close(actual, expected, message=f"Edit Centered point {index} did not reset")
    if curve_edit_context_snapshot(curve) != edit_context:
        raise AssertionError("Edit Centered changed Curve Edit Mode or point selection")

    if bpy.ops.character_designer.set_front_alignment(
        mode=character_designer.HAIR_ALIGNMENT_BLEND
    ) != {"FINISHED"}:
        raise AssertionError("Blend did not apply in Curve Edit Mode")
    state.centerline_blend_factor = 0.25
    assert_blend_factor(curve, 0.25)
    for index, (centered_point, surface_point, actual) in enumerate(
        zip(centered, surface, curve_points(curve))
    ):
        expected = centered_point + (surface_point - centered_point) * 0.25
        assert_vector_close(actual, expected, message=f"Edit Mix 0.25 point {index} is wrong")
    if curve_edit_context_snapshot(curve) != edit_context:
        raise AssertionError("Edit Mix 0.25 changed Curve Edit Mode or point selection")

    state.centerline_blend_factor = 0.75
    assert_blend_factor(curve, 0.75)
    for index, (centered_point, surface_point, actual) in enumerate(
        zip(centered, surface, curve_points(curve))
    ):
        expected = centered_point + (surface_point - centered_point) * 0.75
        assert_vector_close(actual, expected, message=f"Edit Mix 0.75 point {index} is wrong")
    if curve_edit_context_snapshot(curve) != edit_context:
        raise AssertionError("Edit Mix 0.75 changed Curve Edit Mode or point selection")

    # Reproduce the old false-success state: tags say 0.75 while geometry is
    # still centered. The real-geometry no-op check must repair it.
    for point, coordinate in zip(curve.data.splines[0].points, centered):
        point.co = (*coordinate, 1.0)
    character_designer._set_centerline_blend_factor_silently(state, 0.25)
    state.centerline_blend_factor = 0.75
    for index, (centered_point, surface_point, actual) in enumerate(
        zip(centered, surface, curve_points(curve))
    ):
        expected = centered_point + (surface_point - centered_point) * 0.75
        assert_vector_close(
            actual,
            expected,
            message=f"Tagged-but-centered point {index} was not repaired",
        )

    before_repeat = data_fingerprint(curve)
    state.centerline_blend_factor = 0.75
    if data_fingerprint(curve) != before_repeat:
        raise AssertionError("Repeated Edit Mix 0.75 drifted or rewrote the Curve")
    if curve.as_pointer() != object_pointer or curve.data.as_pointer() != data_pointer:
        raise AssertionError("Live Edit placement replaced the Curve object or data")
    if len(bpy.context.scene.objects) != object_count or len(bpy.data.curves) != curve_data_count:
        raise AssertionError("Live Edit placement created an object or Curve datablock")
    if curve_edit_context_snapshot(curve) != edit_context:
        raise AssertionError("Live Edit placement did not preserve the final context")


def test_curve_edit_mix_control_ignores_an_ordinary_curve():
    reset_scene()
    data = bpy.data.curves.new("OrdinaryEditData", "CURVE")
    data.dimensions = "3D"
    spline = data.splines.new("POLY")
    spline.points.add(1)
    spline.points[0].co = (0.0, 0.0, 0.0, 1.0)
    spline.points[1].co = (0.0, 0.0, 1.0, 1.0)
    curve = bpy.data.objects.new("OrdinaryEditCurve", data)
    bpy.context.scene.collection.objects.link(curve)
    edit_context = enter_curve_edit(curve, selected_indices=(0,))
    before = data_fingerprint(curve)
    object_count = len(bpy.context.scene.objects)
    curve_data_count = len(bpy.data.curves)
    state = bpy.context.window_manager.character_designer
    character_designer._bind_centerline_controls(state, curve)
    state.centerline_placement = character_designer.HAIR_ALIGNMENT_BLEND
    state.centerline_blend_factor = 0.8
    if data_fingerprint(curve) != before:
        raise AssertionError("The live controls mutated an ordinary Curve")
    if state.centerline_control_target is not None:
        raise AssertionError("An ordinary Curve became a live control target")
    if len(bpy.context.scene.objects) != object_count or len(bpy.data.curves) != curve_data_count:
        raise AssertionError("Ordinary Curve controls created extra data")
    if curve_edit_context_snapshot(curve) != edit_context:
        raise AssertionError("Ordinary Curve controls changed Edit Mode or selection")


def test_blend_solution_uses_full_factor_range_and_is_idempotent():
    reset_scene()
    source, layers = make_curved_quad_strand("BlendSolution")
    curve = build_centerline(source, layers, front_flush=False)
    payload = metadata(curve)
    centered = character_designer._curve_profile_solution(
        payload,
        character_designer.HAIR_ALIGNMENT_CENTERED,
    )
    surface = character_designer._curve_profile_solution(
        payload,
        character_designer.HAIR_ALIGNMENT_FRONT_FLUSH,
    )
    centered_points, centered_depth, centered_radii, _centered_tilts = centered
    surface_points, surface_depth, surface_radii, _surface_tilts = surface
    for factor in (0.0, 0.23, 0.5, 0.77, 1.0):
        blended = character_designer._curve_profile_solution(
            payload,
            character_designer.HAIR_ALIGNMENT_BLEND,
            blend_factor=factor,
        )
        blend_points, blend_depth, blend_radii, blend_tilts = blended
        if centered_depth != blend_depth or blend_depth != surface_depth:
            raise AssertionError(f"Blend {factor} changed the profile Depth")
        if centered_radii != blend_radii or blend_radii != surface_radii:
            raise AssertionError(f"Blend {factor} changed the point Radii")
        for index, (centered_point, blend_point, surface_point) in enumerate(
            zip(centered_points, blend_points, surface_points)
        ):
            assert_vector_close(
                blend_point,
                centered_point + (surface_point - centered_point) * factor,
                message=f"Pure Blend {factor} point {index} is not exact",
            )
        if any(not math.isfinite(float(tilt)) for tilt in blend_tilts):
            raise AssertionError(f"Blend {factor} produced a non-finite Tilt")
        for first, second in zip(blend_tilts, blend_tilts[1:]):
            if abs(float(second) - float(first)) > math.pi + 1.0e-6:
                raise AssertionError(f"Blend {factor} Tilt continuity was not unwrapped")

    activate_object(curve)
    set_alignment(curve, character_designer.HAIR_ALIGNMENT_BLEND)
    assert_blend_factor(curve, 0.5)
    assert_profile_faces_outward(curve)
    data_pointer = curve.data.as_pointer()
    before = data_fingerprint(curve)
    set_alignment(curve, character_designer.HAIR_ALIGNMENT_BLEND)
    if curve.data.as_pointer() != data_pointer or data_fingerprint(curve) != before:
        raise AssertionError("Repeated default Blend rewrote or drifted an unchanged Curve")


def test_legacy_fixed_blend_without_factor_refreshes_as_half():
    reset_scene()
    source, layers = make_curved_quad_strand("LegacyBlendFactor")
    curve = build_centerline(source, layers, front_flush=False)
    activate_object(curve)
    set_alignment(curve, character_designer.HAIR_ALIGNMENT_BLEND)
    if character_designer.HAIR_BLEND_FACTOR_KEY not in curve:
        raise AssertionError("Blend setup did not create a factor before legacy simulation")
    del curve[character_designer.HAIR_BLEND_FACTOR_KEY]
    if curve.get("character_designer_alignment") != "BLEND":
        raise AssertionError("Legacy Blend simulation lost its alignment tag")

    state = bpy.context.window_manager.character_designer
    state.centerline_placement = character_designer.HAIR_ALIGNMENT_CENTERED
    state.centerline_blend_factor = 0.12
    if bpy.ops.character_designer.generate_or_update_centerline() != {"FINISHED"}:
        raise AssertionError("Legacy fixed Blend could not refresh")
    assert_blend_factor(curve, 0.5)
    assert_close(state.centerline_blend_factor, 0.5)
    payload = metadata(curve)
    centered_points = character_designer._curve_profile_solution(
        payload,
        character_designer.HAIR_ALIGNMENT_CENTERED,
    )[0]
    surface_points = character_designer._curve_profile_solution(
        payload,
        character_designer.HAIR_ALIGNMENT_FRONT_FLUSH,
    )[0]
    for index, (centered, surface, actual) in enumerate(
        zip(centered_points, surface_points, curve_points(curve))
    ):
        assert_vector_close(
            actual,
            centered + (surface - centered) * 0.5,
            message=f"Legacy Blend point {index} did not default to 0.5",
        )
    assert_profile_faces_outward(curve)


def test_single_action_ambiguous_exact_matches_make_no_changes():
    reset_scene()
    source, layers = make_curved_quad_strand("SingleAmbiguous")
    curve = build_centerline(source, layers, front_flush=False)
    duplicate = curve.copy()
    duplicate.data = curve.data.copy()
    duplicate.name = f"{curve.name}_Duplicate"
    bpy.context.scene.collection.objects.link(duplicate)
    first_before = data_fingerprint(curve)
    second_before = data_fingerprint(duplicate)
    state = bpy.context.window_manager.character_designer
    state.output_object = None
    state.update_target_curve = None
    selected = tuple(index for layer in layers for index in layer)
    select_vertices(source, selected, active_index=layers[0][0])
    before_selection = selection_snapshot(source)
    before_count = len(bpy.context.scene.objects)

    result = bpy.ops.character_designer.generate_or_update_centerline()
    if result != {"CANCELLED"}:
        raise AssertionError("Ambiguous single-action update did not stop safely")
    if len(bpy.context.scene.objects) != before_count:
        raise AssertionError("Ambiguous single-action update created another object")
    if data_fingerprint(curve) != first_before or data_fingerprint(duplicate) != second_before:
        raise AssertionError("Ambiguous single-action update mutated a candidate")
    if selection_snapshot(source) != before_selection:
        raise AssertionError("Ambiguous single-action update changed the selection")


def test_single_action_hidden_legacy_target_cannot_rebind_loops():
    reset_scene()
    source, layers = make_curved_quad_strand("SingleHiddenTarget")
    curve = build_centerline(source, layers, included_layer_count=3, front_flush=False)
    state = bpy.context.window_manager.character_designer
    state.output_object = curve
    state.update_target_curve = curve
    before = data_fingerprint(curve)
    selected = tuple(index for layer in layers for index in layer)
    select_vertices(source, selected, active_index=layers[0][0])
    before_count = len(bpy.context.scene.objects)

    result = bpy.ops.character_designer.generate_or_update_centerline()
    if result != {"CANCELLED"}:
        raise AssertionError("A hidden legacy target rebound to different loops")
    if data_fingerprint(curve) != before:
        raise AssertionError("A hidden legacy target was mutated")
    if len(bpy.context.scene.objects) != before_count:
        raise AssertionError("A nonmatching hidden target caused a duplicate")


def test_selected_existing_curve_front_flush_is_idempotent_and_reset_exact():
    reset_scene()
    source, layers = make_curved_quad_strand("Existing")
    curve = build_centerline(source, layers, front_flush=False)
    original_centers = curve_points(curve)
    set_alignment(curve, "FRONT_FLUSH")
    if not bpy.context.window_manager.character_designer.align_front_surface:
        raise AssertionError("FRONT_FLUSH did not drive the state toggle on")
    assert_front_flush(curve, source)
    first = data_fingerprint(curve)
    first_data = curve.data
    set_alignment(curve, "FRONT_FLUSH")
    if curve.data is not first_data:
        raise AssertionError("Repeated FRONT_FLUSH was not a true no-op")
    if data_fingerprint(curve) != first:
        raise AssertionError("Repeated FRONT_FLUSH drifted or rewrote an unchanged Curve")
    set_alignment(curve, "CENTERED")
    if bpy.context.window_manager.character_designer.align_front_surface:
        raise AssertionError("CENTERED reset did not drive the state toggle off")
    if curve.get("character_designer_alignment") != "CENTERED":
        raise AssertionError("Reset did not persist CENTERED state")
    for point, original in zip(curve_points(curve), original_centers):
        assert_vector_close(point, original, message="Reset did not restore the exact layer mean")
    assert_centered(curve, source)


def test_reversed_winding_front_flush_stays_on_the_same_geometric_side():
    def build(reverse):
        reset_scene()
        source, layers = make_curved_quad_strand(
            "Reverse" if reverse else "Forward", reverse_faces=reverse
        )
        curve = build_centerline(source, layers, front_flush=True)
        normals = tuple(
            Vector(section["shape_normal_local"]).normalized()
            for section in metadata(curve)["sections"]
        )
        displacements = tuple(
            center - point
            for center, point in zip(source_centers(source, stored_layers(curve)), curve_points(curve))
        )
        assert_front_flush(curve, source)
        return normals, displacements

    forward_normals, forward_displacements = build(False)
    reverse_normals, reverse_displacements = build(True)
    for index, (first, second) in enumerate(zip(forward_normals, reverse_normals)):
        if first.dot(second) < 0.999:
            raise AssertionError(f"Reversed winding flipped front normal {index}")
    for index, (first, second) in enumerate(zip(forward_displacements, reverse_displacements)):
        if (first - second).length > FRONT_TOLERANCE:
            raise AssertionError(
                f"Reversed winding changed front offset {index}: "
                f"difference={(first - second).length}, first={tuple(first)}, second={tuple(second)}"
            )


def test_nonuniform_object_matrix_front_flush_is_correct_in_world_space():
    reset_scene()
    source, layers = make_curved_quad_strand("Nonuniform")
    source.matrix_world = (
        Matrix.Translation((8.0, -3.0, 1.5))
        @ Matrix.Rotation(math.radians(31.0), 4, "Z")
        @ Matrix.Diagonal((2.1, 0.55, 1.35, 1.0))
    )
    curve = build_centerline(source, layers, front_flush=True)
    for row in range(4):
        for column in range(4):
            assert_close(curve.matrix_world[row][column], source.matrix_world[row][column])
    assert_front_flush(curve, source, world_space=True)


def test_curved_nonuniform_front_flush_hits_recorded_source_planes():
    reset_scene()
    source, layers = make_curved_quad_strand("RecordedSourcePlane")
    source.matrix_world = (
        Matrix.Translation((-6.0, 4.5, 2.0))
        @ Matrix.Rotation(math.radians(-39.0), 4, "Z")
        @ Matrix.Diagonal((2.4, 0.45, 1.7, 1.0))
    )
    curve = build_centerline(source, layers, front_flush=True)
    if curve.get("character_designer_alignment") != "FRONT_FLUSH":
        raise AssertionError("Recorded-source-plane fixture was not built FRONT_FLUSH")
    if int(curve.get("character_designer_metadata_version", 0)) < 4:
        raise AssertionError("Recorded source planes require v4 metadata")
    # This deliberately differs from assert_front_flush(): the plane normal is
    # the immutable source shape_normal stored at capture time. Reprojecting it
    # to the displaced Curve tangent can hide a visible source-plane miss.
    assert_recorded_source_plane_flush(curve, world_space=True)


def test_ordinary_curve_is_rejected_without_mutation():
    reset_scene()
    data = bpy.data.curves.new("OrdinaryData", "CURVE")
    data.dimensions = "3D"
    spline = data.splines.new("POLY")
    spline.points.add(1)
    spline.points[0].co = (0.0, 0.0, 0.0, 1.0)
    spline.points[1].co = (0.0, 0.0, 1.0, 1.0)
    curve = bpy.data.objects.new("OrdinaryCurve", data)
    bpy.context.scene.collection.objects.link(curve)
    activate_object(curve)
    before = data_fingerprint(curve)
    try:
        result = bpy.ops.character_designer.set_front_alignment(mode="FRONT_FLUSH")
    except RuntimeError:
        result = {"CANCELLED"}
    if result != {"CANCELLED"}:
        raise AssertionError("An ordinary Curve was accepted as a Character Designer output")
    if data_fingerprint(curve) != before:
        raise AssertionError("Rejecting an ordinary Curve mutated it")


def test_duplicate_stored_layer_vertices_are_rejected_atomically():
    reset_scene()
    source, layers = make_curved_quad_strand("DuplicateLayers")
    curve = build_centerline(source, layers, front_flush=False)
    malformed = [list(layer) for layer in stored_layers(curve)]
    malformed[1].append(malformed[1][0])
    curve["character_designer_layer_vertices"] = json.dumps(
        malformed, separators=(",", ":")
    )
    activate_object(curve)
    before = data_fingerprint(curve)
    try:
        result = bpy.ops.character_designer.set_front_alignment(mode="FRONT_FLUSH")
    except RuntimeError:
        result = {"CANCELLED"}
    if result != {"CANCELLED"}:
        raise AssertionError("A repeated vertex in stored source layers was accepted")
    if data_fingerprint(curve) != before:
        raise AssertionError("Rejecting duplicate stored layers mutated the Curve")


def test_version_three_curve_is_upgraded_in_place():
    reset_scene()
    source, layers = make_curved_quad_strand("VersionThree")
    curve = build_centerline(source, layers, front_flush=False)
    payload = metadata(curve)
    payload["version"] = 3
    payload.pop("profile_front_alignment", None)
    for section in payload["sections"]:
        for key in tuple(section):
            if key not in V3_SECTION_KEYS:
                section.pop(key)
    curve["character_designer_metadata_version"] = 3
    curve["character_designer_cross_sections"] = json.dumps(
        payload, separators=(",", ":"), allow_nan=False
    )
    if "character_designer_alignment" in curve:
        del curve["character_designer_alignment"]
    materials = add_test_materials(curve, "V3")
    old_data = curve.data
    old_data_fingerprint = curve_data_fingerprint(old_data)
    shared = link_shared_data_object(curve, "V3SharedData")
    object_pointer = curve.as_pointer()
    matrix = curve.matrix_world.copy()
    collections = tuple(curve.users_collection)
    set_alignment(curve, "BLEND")
    current_version = int(character_designer.METADATA_VERSION)
    if current_version <= 3:
        raise AssertionError("Front-alignment metadata did not introduce a post-v3 schema")
    if curve.get("character_designer_metadata_version") != current_version:
        raise AssertionError("v3 Curve was not upgraded to current metadata")
    if metadata(curve).get("version") != current_version:
        raise AssertionError("Upgraded payload version does not match its marker")
    assert_object_envelope_preserved(
        curve, object_pointer, matrix, collections, materials
    )
    if curve.data is old_data:
        raise AssertionError("v3 upgrade mutated a potentially shared Curve datablock")
    if shared.data is not old_data or curve_data_fingerprint(old_data) != old_data_fingerprint:
        raise AssertionError("v3 upgrade changed another Object sharing the legacy data")
    upgraded = metadata(curve)
    centered_points = character_designer._curve_profile_solution(
        upgraded,
        character_designer.HAIR_ALIGNMENT_CENTERED,
    )[0]
    surface_points = character_designer._curve_profile_solution(
        upgraded,
        character_designer.HAIR_ALIGNMENT_FRONT_FLUSH,
    )[0]
    for index, (centered, surface, actual) in enumerate(
        zip(centered_points, surface_points, curve_points(curve))
    ):
        assert_vector_close(
            actual,
            centered + (surface - centered) * 0.5,
            message=f"Upgraded v3 Blend point {index} is not the midpoint",
        )
    if curve.get("character_designer_alignment") != "BLEND":
        raise AssertionError("v3 Curve upgrade did not retain Blend alignment")
    assert_blend_factor(curve, 0.5)
    assert_profile_faces_outward(curve)


def test_missing_source_update_fails_atomically():
    reset_scene()
    source, layers = make_curved_quad_strand("MissingSource")
    curve = build_centerline(source, layers, front_flush=False)
    activate_object(curve)
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("Could not record update target")
    bpy.data.objects.remove(source, do_unlink=True)
    before = data_fingerprint(curve)
    try:
        result = bpy.ops.character_designer.update_existing_centerline()
    except RuntimeError:
        result = {"CANCELLED"}
    if result != {"CANCELLED"}:
        raise AssertionError("Update unexpectedly succeeded after source deletion")
    if data_fingerprint(curve) != before:
        raise AssertionError("Failed source update was not atomic")


def test_object_mode_update_from_source_reuses_curve_and_new_centers():
    reset_scene()
    source, layers = make_curved_quad_strand("ObjectUpdate")
    curve = build_centerline(source, layers, front_flush=False)
    activate_object(curve)
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("Could not record Object Mode update target")
    materials = add_test_materials(curve, "ObjectUpdate")
    old_data = curve.data
    old_data_fingerprint = curve_data_fingerprint(old_data)
    shared = link_shared_data_object(curve, "ObjectUpdateSharedData")
    object_pointer = curve.as_pointer()
    matrix = curve.matrix_world.copy()
    collections = tuple(curve.users_collection)
    old_metadata = curve["character_designer_cross_sections"]
    for layer_index, layer in enumerate(stored_layers(curve)):
        displacement = Vector((0.015 * (layer_index + 1), -0.004 * layer_index, 0.0))
        for vertex_index in layer:
            source.data.vertices[vertex_index].co += displacement
    source.data.update()
    result = bpy.ops.character_designer.update_existing_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Object Mode Update From Source failed: {result}")
    assert_object_envelope_preserved(
        curve, object_pointer, matrix, collections, materials
    )
    if curve.data is old_data:
        raise AssertionError("Object Mode update mutated a potentially shared Curve datablock")
    if shared.data is not old_data or curve_data_fingerprint(old_data) != old_data_fingerprint:
        raise AssertionError("Object Mode update changed another Object sharing the old data")
    if curve["character_designer_cross_sections"] == old_metadata:
        raise AssertionError("Object Mode update left stale cross-section metadata")
    if bpy.context.mode != "OBJECT" or bpy.context.view_layer.objects.active is not curve:
        raise AssertionError("Object Mode update did not preserve active Curve context")
    assert_centered(curve, source)


def test_mesh_edit_update_from_selection_changes_count_and_preserves_context():
    reset_scene()
    source, layers = make_curved_quad_strand("SelectionUpdate")
    curve = build_centerline(source, layers, included_layer_count=3, front_flush=False)
    if len(curve.data.splines[0].points) != 3:
        raise AssertionError("Initial partial selection did not produce three points")
    activate_object(curve)
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("Could not record Mesh Edit update target")
    materials = add_test_materials(curve, "SelectionUpdate")
    old_data = curve.data
    old_data_fingerprint = curve_data_fingerprint(old_data)
    shared = link_shared_data_object(curve, "SelectionUpdateSharedData")
    object_pointer = curve.as_pointer()
    source.matrix_world = (
        Matrix.Translation((-4.0, 6.0, 2.25))
        @ Matrix.Rotation(math.radians(-24.0), 4, "Z")
        @ Matrix.Diagonal((0.8, 1.3, 1.1, 1.0))
    )
    matrix = source.matrix_world.copy()
    collections = tuple(curve.users_collection)
    select_vertices(source, tuple(index for layer in layers for index in layer), active_index=layers[0][0])
    before_selection = selection_snapshot(source)
    result = bpy.ops.character_designer.update_existing_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"Mesh Edit Update From Selection failed: {result}")
    if bpy.context.mode != "EDIT_MESH" or bpy.context.edit_object is not source:
        raise AssertionError("Mesh Edit update did not restore the same object/mode")
    if selection_snapshot(source) != before_selection:
        raise AssertionError("Mesh Edit update changed the artist's selection or active element")
    assert_object_envelope_preserved(
        curve, object_pointer, matrix, collections, materials
    )
    if curve.data is old_data:
        raise AssertionError("Mesh Edit update mutated a potentially shared Curve datablock")
    if shared.data is not old_data or curve_data_fingerprint(old_data) != old_data_fingerprint:
        raise AssertionError("Mesh Edit update changed another Object sharing the old data")
    if len(curve.data.splines[0].points) != len(layers):
        raise AssertionError("Mesh Edit update did not replace the Curve point count")
    payload = metadata(curve)
    if payload.get("point_count") != len(layers) or len(payload.get("sections", ())) != len(layers):
        raise AssertionError("Mesh Edit update left stale point-count metadata")
    if stored_layers(curve) != layers:
        raise AssertionError("Mesh Edit update did not record the replacement selection")
    assert_centered(curve, source)


def test_mesh_edit_update_obeys_current_alignment_toggle():
    reset_scene()
    source, layers = make_curved_quad_strand("SelectionToggle")
    curve = build_centerline(source, layers, front_flush=False)
    activate_object(curve)
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("Could not record alignment-toggle update target")
    select_vertices(
        source,
        tuple(index for layer in layers for index in layer),
        active_index=layers[0][0],
    )
    state = bpy.context.window_manager.character_designer
    before_selection = selection_snapshot(source)

    state.align_front_surface = True
    result = bpy.ops.character_designer.update_existing_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"FRONT_FLUSH selection update failed: {result}")
    if curve.get("character_designer_alignment") != "FRONT_FLUSH":
        raise AssertionError(
            "Mesh Edit update ignored the enabled Align Front Surface toggle"
        )
    if bpy.context.mode != "EDIT_MESH" or bpy.context.edit_object is not source:
        raise AssertionError("FRONT_FLUSH selection update changed Edit Mode context")
    if selection_snapshot(source) != before_selection:
        raise AssertionError("FRONT_FLUSH selection update changed the selection")
    assert_front_flush(curve, source)

    state.align_front_surface = False
    result = bpy.ops.character_designer.update_existing_centerline()
    if result != {"FINISHED"}:
        raise AssertionError(f"CENTERED selection update failed: {result}")
    if curve.get("character_designer_alignment") != "CENTERED":
        raise AssertionError(
            "Mesh Edit update ignored the disabled Align Front Surface toggle"
        )
    if bpy.context.mode != "EDIT_MESH" or bpy.context.edit_object is not source:
        raise AssertionError("CENTERED selection update changed Edit Mode context")
    if selection_snapshot(source) != before_selection:
        raise AssertionError("CENTERED selection update changed the selection")
    assert_centered(curve, source)


def test_update_internal_failure_rolls_back_data_materials_and_shared_users():
    reset_scene()
    source, layers = make_curved_quad_strand("FailureRollback")
    curve = build_centerline(source, layers, front_flush=False)
    activate_object(curve)
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("Could not record failure-rollback target")
    materials = add_test_materials(curve, "FailureRollback")
    old_data = curve.data
    shared = link_shared_data_object(curve, "FailureRollbackSharedData")
    before = data_fingerprint(curve)
    old_data_fingerprint = curve_data_fingerprint(old_data)
    curve_datablocks = set(bpy.data.curves)
    source.data.vertices[0].co += Vector((0.025, 0.0, 0.0))
    source.data.update()

    original_configure = character_designer._configure_centerline_data

    def injected_failure(curve_data, solution):
        original_configure(curve_data, solution)
        raise character_designer.CenterlineError("injected post-configuration failure")

    character_designer._configure_centerline_data = injected_failure
    try:
        try:
            result = bpy.ops.character_designer.update_existing_centerline()
        except RuntimeError:
            result = {"CANCELLED"}
    finally:
        character_designer._configure_centerline_data = original_configure
    if result != {"CANCELLED"}:
        raise AssertionError("Injected update failure unexpectedly committed")
    if curve.data is not old_data or data_fingerprint(curve) != before:
        raise AssertionError("Failed update did not restore the exact target state")
    if tuple(curve.data.materials) != materials:
        raise AssertionError("Failed update changed material slots")
    if shared.data is not old_data or curve_data_fingerprint(old_data) != old_data_fingerprint:
        raise AssertionError("Failed update changed a shared old Curve datablock")
    if set(bpy.data.curves) != curve_datablocks:
        raise AssertionError("Failed update leaked a temporary Curve datablock")


def test_reset_after_mesh_change_uses_refreshed_source_means():
    reset_scene()
    source, layers = make_curved_quad_strand("ResetChangedMesh")
    curve = build_centerline(source, layers, front_flush=True)
    activate_object(curve)
    if bpy.ops.character_designer.set_update_target() != {"FINISHED"}:
        raise AssertionError("Could not record changed-mesh target")
    for vertex_index in stored_layers(curve)[2]:
        source.data.vertices[vertex_index].co += Vector((0.07, -0.025, 0.015))
    source.data.update()
    if bpy.ops.character_designer.update_existing_centerline() != {"FINISHED"}:
        raise AssertionError("Changed source mesh could not update its Curve")
    set_alignment(curve, "CENTERED")
    assert_centered(curve, source)


def test_alignment_change_is_undoable_when_background_undo_is_available():
    reset_scene()
    source, layers = make_curved_quad_strand("UndoAlignment")
    curve = build_centerline(source, layers, front_flush=False)
    curve_name = curve.name
    centered = curve_points(curve)
    set_alignment(curve, "FRONT_FLUSH")
    if not bpy.ops.ed.undo.poll():
        print("SKIP test_alignment_change_is_undoable_when_background_undo_is_available")
        return
    try:
        result = bpy.ops.ed.undo()
    except RuntimeError:
        print("SKIP test_alignment_change_is_undoable_when_background_undo_is_available")
        return
    if result != {"FINISHED"}:
        print("SKIP test_alignment_change_is_undoable_when_background_undo_is_available")
        return
    restored = bpy.data.objects.get(curve_name)
    if restored is None:
        raise AssertionError("Undo removed the pre-existing target Curve")
    for point, expected in zip(curve_points(restored), centered):
        assert_vector_close(point, expected, message="Undo did not restore centered points")
    if restored.get("character_designer_alignment") != "CENTERED":
        raise AssertionError("Undo did not restore the CENTERED alignment tag")


def main():
    character_designer.register()
    all_tests = (
        test_toggle_off_is_exactly_centered_and_selection_records_target,
        test_toggle_on_builds_evaluated_front_flush_including_point,
        test_single_action_switches_three_placements_on_the_matching_curve,
        test_single_action_object_mode_refresh_preserves_saved_blend_factor,
        test_curve_edit_controls_update_placement_and_mix_immediately,
        test_curve_edit_mix_control_ignores_an_ordinary_curve,
        test_blend_solution_uses_full_factor_range_and_is_idempotent,
        test_legacy_fixed_blend_without_factor_refreshes_as_half,
        test_single_action_ambiguous_exact_matches_make_no_changes,
        test_single_action_hidden_legacy_target_cannot_rebind_loops,
        test_selected_existing_curve_front_flush_is_idempotent_and_reset_exact,
        test_reversed_winding_front_flush_stays_on_the_same_geometric_side,
        test_nonuniform_object_matrix_front_flush_is_correct_in_world_space,
        test_curved_nonuniform_front_flush_hits_recorded_source_planes,
        test_ordinary_curve_is_rejected_without_mutation,
        test_duplicate_stored_layer_vertices_are_rejected_atomically,
        test_version_three_curve_is_upgraded_in_place,
        test_missing_source_update_fails_atomically,
        test_object_mode_update_from_source_reuses_curve_and_new_centers,
        test_mesh_edit_update_from_selection_changes_count_and_preserves_context,
        test_mesh_edit_update_obeys_current_alignment_toggle,
        test_update_internal_failure_rolls_back_data_materials_and_shared_users,
        test_reset_after_mesh_change_uses_refreshed_source_means,
        test_alignment_change_is_undoable_when_background_undo_is_available,
    )
    requested = set(sys.argv[sys.argv.index("--") + 1 :]) if "--" in sys.argv else set()
    tests = tuple(test for test in all_tests if not requested or test.__name__ in requested)
    if requested and len(tests) != len(requested):
        missing = requested - {test.__name__ for test in tests}
        raise AssertionError(f"Unknown requested tests: {sorted(missing)}")
    try:
        assert_contract()
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        if hasattr(bpy.types.WindowManager, "character_designer"):
            character_designer.unregister()
    print(f"PASS Hair Front Alignment {len(tests)} tests")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        # Blender normally exits 0 after an uncaught --python exception. Make
        # standalone/CI callers unambiguously observe a failed regression run,
        # even when they forgot --python-exit-code.
        os._exit(1)
