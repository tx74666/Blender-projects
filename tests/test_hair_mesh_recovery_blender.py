"""Blender 5.2 integration tests for applied hair Mesh -> editable Curve recovery.

Run with::

    blender --background --factory-startup --python-exit-code 1 \
        --python tests/test_hair_mesh_recovery_blender.py

All fixtures are generated in memory.  This script never opens or saves a .blend.
"""

import json
import math
import sys
import traceback
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

import character_designer


TOLERANCE = 2.0e-4


def assert_close(actual, expected, tolerance=TOLERANCE, message=""):
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(message or f"Expected {expected}, got {actual}")


def assert_vector_close(actual, expected, tolerance=TOLERANCE, message=""):
    if (Vector(actual) - Vector(expected)).length > tolerance:
        raise AssertionError(message or f"Expected {tuple(expected)}, got {tuple(actual)}")


def reset_scene():
    state = getattr(bpy.context.window_manager, "character_designer", None)
    if state is not None:
        if getattr(state, "recovery_preview_enabled", False):
            state.recovery_preview_enabled = False
        if getattr(state, "live_preview_enabled", False):
            state.live_preview_enabled = False
        if getattr(state, "preview_active", False):
            character_designer._stop_live_preview(settings=state, clear_capture=True)
        state.output_object = None
        state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
        state.recovery_control_points = character_designer.RECOVERY_CONTROL_POINTS_DEFAULT
        state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD
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


def make_half_round_curve(
    name,
    *,
    x_offset=0.0,
    radii=(1.0, 0.82, 0.61, 0.44),
    tilts=(-0.38, -0.12, 0.24, 0.57),
    bevel_depth=0.18,
    extrude=0.07,
    offset=0.025,
    bevel_resolution=3,
    straight=False,
):
    points = (
        tuple(Vector((x_offset, 0.0, value))) for value in (0.0, 0.4, 0.8, 1.2)
    ) if straight else (
        Vector((x_offset + 0.00, 0.00, 0.00)),
        Vector((x_offset + 0.05, 0.02, 0.42)),
        Vector((x_offset - 0.04, 0.08, 0.83)),
        Vector((x_offset + 0.02, 0.15, 1.22)),
    )
    points = tuple(Vector(value) for value in points)
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.render_resolution_u = 1
    data.twist_mode = "MINIMUM"
    data.fill_mode = "HALF"
    data.bevel_mode = "ROUND"
    data.bevel_depth = bevel_depth
    data.bevel_resolution = bevel_resolution
    data.extrude = extrude
    data.offset = offset
    data.use_fill_caps = False
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate, radius, tilt in zip(spline.points, points, radii, tilts):
        point.co = (*coordinate, 1.0)
        point.radius = radius
        point.tilt = tilt
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj, points


def make_dense_half_round_curve(name, point_count=11):
    points = []
    radii = []
    tilts = []
    for index in range(point_count):
        factor = index / (point_count - 1)
        points.append(
            Vector(
                (
                    0.16 * math.sin(factor * math.pi * 1.15),
                    0.12 * factor * factor,
                    1.65 * factor,
                )
            )
        )
        radii.append(1.0 - 0.62 * factor + 0.035 * math.sin(factor * math.pi))
        tilts.append(-0.52 + 1.08 * factor)
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.render_resolution_u = 1
    data.twist_mode = "MINIMUM"
    data.fill_mode = "HALF"
    data.bevel_mode = "ROUND"
    data.bevel_depth = 0.15
    data.bevel_resolution = 3
    data.extrude = 0.055
    data.offset = 0.018
    data.use_fill_caps = False
    spline = data.splines.new("POLY")
    spline.points.add(point_count - 1)
    for point, coordinate, radius, tilt in zip(
        spline.points,
        points,
        radii,
        tilts,
    ):
        point.co = (*coordinate, 1.0)
        point.radius = radius
        point.tilt = tilt
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def make_rectangle_curve(name):
    points = tuple(Vector((0.03 * math.sin(index), 0.04 * index, index * 0.39)) for index in range(4))
    radii = (1.0, 0.79, 0.58, 0.41)
    tilts = (-0.31, -0.08, 0.27, 0.49)
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.render_resolution_u = 1
    data.twist_mode = "MINIMUM"
    data.fill_mode = "FULL"
    data.bevel_depth = 0.075
    data.extrude = 0.115
    data.offset = 0.0
    character_designer._configure_rectangle_bevel_profile(data)
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate, radius, tilt in zip(spline.points, points, radii, tilts):
        point.co = (*coordinate, 1.0)
        point.radius = radius
        point.tilt = tilt
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def curve_to_mesh_object(curve_obj, name):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(
        curve_obj.evaluated_get(depsgraph),
        depsgraph=depsgraph,
    )
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = curve_obj.matrix_world.copy()
    curve_data = curve_obj.data
    bpy.data.objects.remove(curve_obj, do_unlink=True)
    if curve_data.users == 0:
        bpy.data.curves.remove(curve_data)
    return obj


def select_all_mesh(obj):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.ops.mesh.select_all(action="SELECT")


def select_mesh_edges(obj, edge_keys):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (False, True, False)
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.select_history.clear()
    wanted = {tuple(sorted(key)) for key in edge_keys}
    for vertex in bm.verts:
        vertex.select_set(False)
    for edge in bm.edges:
        key = tuple(sorted((edge.verts[0].index, edge.verts[1].index)))
        edge.select_set(key in wanted)
        if key in wanted:
            bm.select_history.add(edge)
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)


def select_mesh_faces(obj, face_indices):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.select_history.clear()
    wanted = set(face_indices)
    for vertex in bm.verts:
        vertex.select_set(False)
    for face in bm.faces:
        face.select_set(face.index in wanted)
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)


def selection_snapshot(obj):
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    active = bm.select_history.active
    return (
        tuple(vertex.index for vertex in bm.verts if vertex.select),
        tuple(edge.index for edge in bm.edges if edge.select),
        tuple(face.index for face in bm.faces if face.select),
        tuple(bool(value) for value in bpy.context.tool_settings.mesh_select_mode),
        (type(active).__name__, active.index) if active is not None else None,
    )


def mesh_fingerprint(obj):
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return (
        obj.as_pointer(),
        obj.data.as_pointer(),
        tuple(tuple(float(value) for value in vertex.co) for vertex in bm.verts),
        tuple(
            sorted(tuple(sorted((edge.verts[0].index, edge.verts[1].index))) for edge in bm.edges)
        ),
        tuple(tuple(vertex.index for vertex in face.verts) for face in bm.faces),
        selection_snapshot(obj),
    )


def evaluated_vertex_cloud(obj, digits=4):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
    try:
        return tuple(
            sorted(
                (
                    round(float((obj.matrix_world @ vertex.co).x), digits),
                    round(float((obj.matrix_world @ vertex.co).y), digits),
                    round(float((obj.matrix_world @ vertex.co).z), digits),
                )
                for vertex in mesh.vertices
            )
        )
    finally:
        bpy.data.meshes.remove(mesh)


def assert_vertex_clouds_equivalent(first, second, tolerance=5.0e-4):
    if len(first) != len(second):
        raise AssertionError(f"Vertex-cloud sizes differ: {len(first)} != {len(second)}")
    first_vectors = tuple(Vector(value) for value in first)
    second_vectors = tuple(Vector(value) for value in second)
    for source, targets in ((first_vectors, second_vectors), (second_vectors, first_vectors)):
        maximum = max(min((value - candidate).length for candidate in targets) for value in source)
        if maximum > tolerance:
            raise AssertionError(
                f"Evaluated profile differs by {maximum:.6f}, over tolerance {tolerance:.6f}"
            )


def recovered_curves(source):
    return tuple(
        obj
        for obj in bpy.context.scene.objects
        if obj.get("character_designer_generator")
        == character_designer.RECOVERY_GENERATOR_ID
        and obj.get(character_designer.RECOVERY_SOURCE_OBJECT_KEY) is source
    )


def generated_recovery_curves():
    return tuple(
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "CURVE"
        and obj.get("character_designer_generator")
        == character_designer.RECOVERY_GENERATOR_ID
    )


def add_supported_recovery_modifiers(obj, order):
    modifiers = []
    for index, modifier_type in enumerate(order, start=1):
        modifier = obj.modifiers.new(
            name=f"Recovery {index:02d} {modifier_type.title()}",
            type=modifier_type,
        )
        if modifier_type == "MIRROR":
            modifier.use_axis = (True, False, False)
            modifier.use_bisect_axis = (False, False, False)
            modifier.use_bisect_flip_axis = (False, False, False)
            modifier.use_clip = False
            modifier.use_mirror_merge = False
            modifier.merge_threshold = 0.0025
        elif modifier_type == "SUBSURF":
            modifier.subdivision_type = "CATMULL_CLARK"
            modifier.levels = 1
            modifier.render_levels = 1
            modifier.quality = 2
            modifier.show_only_control_edges = False
            modifier.use_limit_surface = True
        else:
            raise AssertionError(f"Unsupported test modifier type: {modifier_type}")
        modifiers.append(modifier)
    return tuple(modifiers)


def supported_modifier_stack_snapshot(obj):
    stack = []
    for modifier in obj.modifiers:
        values = {
            "name": modifier.name,
            "type": modifier.type,
            "show_viewport": bool(modifier.show_viewport),
            "show_render": bool(modifier.show_render),
        }
        if modifier.type == "MIRROR":
            mirror_object = modifier.mirror_object
            values.update(
                {
                    "use_axis": tuple(bool(value) for value in modifier.use_axis),
                    "use_bisect_axis": tuple(
                        bool(value) for value in modifier.use_bisect_axis
                    ),
                    "use_bisect_flip_axis": tuple(
                        bool(value) for value in modifier.use_bisect_flip_axis
                    ),
                    "use_clip": bool(modifier.use_clip),
                    "use_mirror_merge": bool(modifier.use_mirror_merge),
                    "merge_threshold": float(modifier.merge_threshold),
                    "mirror_object": mirror_object,
                }
            )
        elif modifier.type == "SUBSURF":
            values.update(
                {
                    "subdivision_type": modifier.subdivision_type,
                    "levels": int(modifier.levels),
                    "render_levels": int(modifier.render_levels),
                    "quality": int(modifier.quality),
                    "show_only_control_edges": bool(modifier.show_only_control_edges),
                    "use_limit_surface": bool(modifier.use_limit_surface),
                }
            )
        stack.append(values)
    return tuple(stack)


def assert_supported_modifier_stack(obj, expected):
    actual = supported_modifier_stack_snapshot(obj)
    if len(actual) != len(expected):
        raise AssertionError(
            f"Recovered modifier count changed: {len(actual)} != {len(expected)}"
        )
    for index, (actual_values, expected_values) in enumerate(zip(actual, expected)):
        if actual_values.keys() != expected_values.keys():
            raise AssertionError(f"Modifier {index} property contract changed")
        for key, expected_value in expected_values.items():
            actual_value = actual_values[key]
            if isinstance(expected_value, float):
                assert_close(
                    actual_value,
                    expected_value,
                    tolerance=1.0e-7,
                    message=f"Modifier {index} changed {key}",
                )
            elif actual_value != expected_value:
                raise AssertionError(
                    f"Modifier {index} changed {key}: {actual_value!r} != {expected_value!r}"
                )

    expected_identity = tuple((item["name"], item["type"]) for item in expected)
    try:
        ownership = tuple(
            tuple(item)
            for item in json.loads(
                obj[character_designer.RECOVERY_MODIFIER_OWNERSHIP_KEY]
            )
        )
        stored_stack = json.loads(obj[character_designer.RECOVERY_MODIFIER_STACK_KEY])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AssertionError("Recovered modifier ownership metadata is unreadable") from exc
    if ownership != expected_identity:
        raise AssertionError(
            f"Recovered modifier ownership order changed: {ownership!r}"
        )
    if tuple((item.get("name"), item.get("type")) for item in stored_stack) != expected_identity:
        raise AssertionError("Recovered modifier stack metadata changed its order or types")


def recovery_managed_properties_snapshot(obj):
    return tuple(
        (key, key in obj, obj.get(key))
        for key in character_designer.RECOVERY_MANAGED_KEYS
    )


def assert_aligned_bezier_handles(spline, coordinates, tolerance=1.0e-6):
    expected_handles = character_designer._recovery_aligned_handles(coordinates)
    if len(expected_handles) != len(spline.bezier_points):
        raise AssertionError("Aligned-handle helper returned the wrong point count")
    for index, (point, (expected_left, expected_right)) in enumerate(
        zip(spline.bezier_points, expected_handles)
    ):
        if point.handle_left_type != "ALIGNED" or point.handle_right_type != "ALIGNED":
            raise AssertionError(f"Bezier point {index} does not use Aligned handles")
        assert_vector_close(
            point.handle_left,
            expected_left,
            tolerance=tolerance,
            message=f"Bezier point {index} has the wrong left handle",
        )
        assert_vector_close(
            point.handle_right,
            expected_right,
            tolerance=tolerance,
            message=f"Bezier point {index} has the wrong right handle",
        )
        left_vector = Vector(point.co) - Vector(point.handle_left)
        right_vector = Vector(point.handle_right) - Vector(point.co)
        if left_vector.length > tolerance and right_vector.length > tolerance:
            cross_error = left_vector.cross(right_vector).length
            cross_scale = left_vector.length * right_vector.length
            if cross_error > tolerance * max(1.0, cross_scale):
                raise AssertionError(f"Bezier point {index} handles are not collinear")
            if left_vector.dot(right_vector) < -tolerance:
                raise AssertionError(f"Bezier point {index} handles point to different axes")


def join_mesh_objects(objects, name):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    objects[0].name = name
    return objects[0]


def find_longitudinal_rail(obj):
    """Find one simple 4-vertex rail by grouping this fixture along Z."""

    vertices = tuple(obj.data.vertices)
    groups = []
    for target_z in sorted({round(float(vertex.co.z), 3) for vertex in vertices}):
        group = [vertex for vertex in vertices if abs(float(vertex.co.z) - target_z) < 0.09]
        if group:
            groups.append(group)
    if len(groups) != 4:
        raise AssertionError(f"Expected four evaluated rings, got {len(groups)}")
    chosen = [max(group, key=lambda vertex: (vertex.co.y, vertex.co.x)) for group in groups]
    existing = {
        tuple(sorted((edge.vertices[0], edge.vertices[1])))
        for edge in obj.data.edges
    }
    edge_keys = tuple(
        tuple(sorted((first.index, second.index)))
        for first, second in zip(chosen, chosen[1:])
    )
    if any(edge_key not in existing for edge_key in edge_keys):
        # Curved/tilted profiles can change which extremum corresponds across
        # rings. Walk the real edge graph from the first ring instead.
        ring_sets = [set(vertex.index for vertex in group) for group in groups]
        current = chosen[0].index
        edge_keys = []
        for next_ring in ring_sets[1:]:
            candidates = [
                edge_key
                for edge_key in existing
                if current in edge_key and (set(edge_key) - {current}).issubset(next_ring)
            ]
            if len(candidates) != 1:
                raise AssertionError("Could not identify one longitudinal fixture rail")
            edge_key = candidates[0]
            edge_keys.append(edge_key)
            current = next(index for index in edge_key if index != current)
        edge_keys = tuple(edge_keys)
    return edge_keys


def test_half_round_extrude_offset_recovers_equivalent_editable_curve():
    reset_scene()
    original, expected_points = make_half_round_curve("AppliedOriginal")
    source = curve_to_mesh_object(original, "AppliedHair")
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    source_cloud = evaluated_vertex_cloud(source)

    result = bpy.ops.character_designer.recover_applied_curve()
    if result != {"FINISHED"}:
        raise AssertionError(f"Recovery failed: {result}")
    if bpy.context.mode != "EDIT_MESH" or bpy.context.edit_object is not source:
        raise AssertionError("Recovery changed the artist's Mesh Edit Mode context")
    if mesh_fingerprint(source) != before:
        raise AssertionError("Recovery changed the source mesh or its selection")

    curves = recovered_curves(source)
    if len(curves) != 1:
        raise AssertionError(f"Expected one recovered Curve, got {len(curves)}")
    recovered = curves[0]
    if recovered.data.fill_mode != "HALF" or recovered.data.bevel_mode != "ROUND":
        raise AssertionError("Half Round profile type was not recovered")
    if not math.isfinite(float(recovered.data.offset)):
        raise AssertionError("Recovered Offset is not finite")
    if recovered.data.extrude <= 0.0:
        raise AssertionError("Applied Extrude was flattened instead of recovered")
    points = recovered.data.splines[0].points
    if len(points) != len(expected_points):
        raise AssertionError("Recovered point count changed")
    if len({round(float(point.radius), 4) for point in points}) == 1:
        raise AssertionError("Per-point Radius / Alt+S variation was not recovered")
    if len({round(float(point.tilt), 4) for point in points}) == 1:
        raise AssertionError("Per-point Tilt variation was not recovered")
    assert_vertex_clouds_equivalent(evaluated_vertex_cloud(recovered), source_cloud)


def test_full_round_capsule_recovers_equivalent_editable_curve():
    reset_scene()
    original, _points = make_half_round_curve(
        "FullRoundOriginal",
        bevel_depth=0.14,
        extrude=0.085,
        offset=0.0,
        bevel_resolution=3,
    )
    original.data.fill_mode = "FULL"
    source = curve_to_mesh_object(original, "FullRoundApplied")
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    source_cloud = evaluated_vertex_cloud(source)

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Full Round capsule recovery failed")
    if mesh_fingerprint(source) != before:
        raise AssertionError("Full Round recovery changed the source Mesh or selection")
    curves = recovered_curves(source)
    if len(curves) != 1:
        raise AssertionError("Full Round recovery did not create exactly one Curve")
    recovered = curves[0]
    if recovered.get(character_designer.RECOVERY_PROFILE_KEY) != "ROUND_FULL":
        raise AssertionError("Full Round capsule profile was not identified")
    if recovered.data.fill_mode != "FULL" or recovered.data.bevel_mode != "ROUND":
        raise AssertionError("Full Round output has the wrong bevel mode")
    if recovered.data.extrude <= 0.0:
        raise AssertionError("Full Round capsule Extrude was flattened")
    assert_vertex_clouds_equivalent(
        evaluated_vertex_cloud(recovered),
        source_cloud,
        tolerance=8.0e-4,
    )


def test_supported_modifier_stacks_preserve_order_profiles_and_evaluation():
    cases = (
        (
            "HalfMirrorThenSubdivision",
            "HALF",
            ("MIRROR", "SUBSURF"),
        ),
        (
            "FullSubdivisionThenMirror",
            "FULL",
            ("SUBSURF", "MIRROR"),
        ),
    )
    for name, fill_mode, modifier_order in cases:
        reset_scene()
        original, _points = make_half_round_curve(
            f"{name}Original",
            x_offset=0.72,
            bevel_depth=0.14,
            extrude=0.075,
            offset=0.0 if fill_mode == "FULL" else 0.018,
            bevel_resolution=3,
        )
        original.data.fill_mode = fill_mode
        source = curve_to_mesh_object(original, f"{name}Source")
        add_supported_recovery_modifiers(source, modifier_order)
        expected_stack = supported_modifier_stack_snapshot(source)
        select_all_mesh(source)
        before = mesh_fingerprint(source)
        source_cloud = evaluated_vertex_cloud(source)
        state = bpy.context.window_manager.character_designer
        state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
        state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD

        if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
            raise AssertionError(f"{name} modifier-aware Add recovery failed")
        if bpy.context.edit_object is not source or mesh_fingerprint(source) != before:
            raise AssertionError(f"{name} recovery changed its source Mesh cage")
        curves = recovered_curves(source)
        if len(curves) != 1:
            raise AssertionError(f"{name} recovery did not create exactly one Curve")
        target = curves[0]
        target_pointer = target.as_pointer()
        if target.data.fill_mode != fill_mode:
            raise AssertionError(f"{name} recovery changed the Half/Full profile mode")
        assert_supported_modifier_stack(target, expected_stack)
        assert_vertex_clouds_equivalent(
            evaluated_vertex_cloud(target),
            source_cloud,
            tolerance=3.0e-3,
        )

        source_subdivision = next(
            modifier for modifier in source.modifiers if modifier.type == "SUBSURF"
        )
        source_subdivision.subdivision_type = "SIMPLE"
        expected_updated_stack = supported_modifier_stack_snapshot(source)
        updated_source_cloud = evaluated_vertex_cloud(source)
        if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
            raise AssertionError(f"{name} modifier-stack update failed")
        updated_curves = recovered_curves(source)
        if len(updated_curves) != 1 or updated_curves[0].as_pointer() != target_pointer:
            raise AssertionError(f"{name} modifier update replaced or duplicated the Curve Object")
        target = updated_curves[0]
        assert_supported_modifier_stack(target, expected_updated_stack)
        assert_vertex_clouds_equivalent(
            evaluated_vertex_cloud(target),
            updated_source_cloud,
            tolerance=3.0e-3,
        )

        if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
            raise AssertionError(f"{name} unchanged repeat recovery failed")
        repeated = recovered_curves(source)
        if len(repeated) != 1 or repeated[0].as_pointer() != target_pointer:
            raise AssertionError(f"{name} repeat recovery duplicated its output Object")
        assert_supported_modifier_stack(repeated[0], expected_updated_stack)


def test_supported_modifier_preview_is_gpu_only_and_describes_preserved_stack():
    reset_scene()
    original, _points = make_half_round_curve(
        "ModifierPreviewOriginal",
        x_offset=0.7,
    )
    source = curve_to_mesh_object(original, "ModifierPreviewSource")
    add_supported_recovery_modifiers(source, ("MIRROR", "SUBSURF"))
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    before_objects = {obj.as_pointer() for obj in bpy.data.objects}
    before_curves = {curve.as_pointer() for curve in bpy.data.curves}
    before_meshes = {mesh.as_pointer() for mesh in bpy.data.meshes}
    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD
    state.recovery_preview_enabled = True

    if not state.preview_valid or not state.preview_confirmable:
        raise AssertionError("Supported modifier stack did not produce a valid Preview")
    if "Preserves Mirror \u2192 Subdivision." not in state.preview_message:
        raise AssertionError(
            f"Modifier Preview did not describe its preserved stack: {state.preview_message!r}"
        )
    if not character_designer._LIVE_PREVIEW_PATHS:
        raise AssertionError("Modifier Preview did not publish a GPU path")
    if (
        {obj.as_pointer() for obj in bpy.data.objects} != before_objects
        or {curve.as_pointer() for curve in bpy.data.curves} != before_curves
        or {mesh.as_pointer() for mesh in bpy.data.meshes} != before_meshes
    ):
        raise AssertionError("Modifier Preview created or removed a Blender datablock")
    if mesh_fingerprint(source) != before:
        raise AssertionError("Modifier Preview changed the source base cage")

    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE
    character_designer._update_recovery_live_preview(bpy.context, force=True)
    if not state.preview_valid or not state.preview_confirmable:
        raise AssertionError("Supported full-selection Replace Preview was rejected")
    if not state.preview_message.startswith(
        "Preview ready - Mesh is removed only after Recover."
    ) or "Preserves Mirror \u2192 Subdivision." not in state.preview_message:
        raise AssertionError(
            f"Replace Preview did not describe deletion timing and stack: {state.preview_message!r}"
        )
    if bpy.data.objects.get(source.name) is not source or mesh_fingerprint(source) != before:
        raise AssertionError("Replace Preview changed or deleted the source Mesh")
    if (
        {obj.as_pointer() for obj in bpy.data.objects} != before_objects
        or {curve.as_pointer() for curve in bpy.data.curves} != before_curves
        or {mesh.as_pointer() for mesh in bpy.data.meshes} != before_meshes
    ):
        raise AssertionError("Replace Preview changed Blender datablocks")

    state.recovery_preview_enabled = False
    if (
        state.preview_active
        or character_designer._LIVE_PREVIEW_PATHS
        or character_designer._LIVE_PREVIEW_WORLD_POINTS
        or character_designer._LIVE_PREVIEW_HANDLE_POINTS
    ):
        raise AssertionError("Modifier Preview did not stop and clear its GPU cache")


def test_replace_mesh_preserves_supported_stack_and_base_mesh_datablock():
    reset_scene()
    original, _points = make_half_round_curve(
        "ModifierReplaceOriginal",
        x_offset=0.74,
    )
    source = curve_to_mesh_object(original, "ModifierReplaceSource")
    add_supported_recovery_modifiers(
        source,
        ("MIRROR", "SUBSURF"),
    )
    expected_stack = supported_modifier_stack_snapshot(source)
    source_name = source.name
    source_pointer = source.as_pointer()
    source_mesh = source.data
    source_mesh_name = source_mesh.name
    source_cloud = evaluated_vertex_cloud(source)
    select_all_mesh(source)
    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Replace Mesh rejected a supported modifier stack")
    if bpy.data.objects.get(source_name) is not None or any(
        obj.as_pointer() == source_pointer for obj in bpy.data.objects
    ):
        raise AssertionError("Modifier-aware Replace retained the source Mesh Object")
    if bpy.data.meshes.get(source_mesh_name) is not source_mesh or source_mesh.users != 0:
        raise AssertionError("Modifier-aware Replace removed the base Mesh datablock")
    outputs = generated_recovery_curves()
    if len(outputs) != 1:
        raise AssertionError("Modifier-aware Replace did not create exactly one Curve")
    target = outputs[0]
    assert_supported_modifier_stack(target, expected_stack)
    mirror = next(modifier for modifier in target.modifiers if modifier.type == "MIRROR")
    if mirror.mirror_object is not None:
        raise AssertionError("Replace retained a dangling self Mirror Object reference")
    assert_vertex_clouds_equivalent(
        evaluated_vertex_cloud(target),
        source_cloud,
        tolerance=3.0e-3,
    )


def test_bezier_recovery_controls_have_bounded_defaults():
    reset_scene()
    state = bpy.context.window_manager.character_designer
    action_property = state.bl_rna.properties["recovery_source_action"]
    mode_property = state.bl_rna.properties["recovery_curve_mode"]
    count_property = state.bl_rna.properties["recovery_control_points"]
    action_identifiers = tuple(item.identifier for item in action_property.enum_items)
    if action_identifiers != (
        character_designer.RECOVERY_SOURCE_ACTION_ADD,
        character_designer.RECOVERY_SOURCE_ACTION_REPLACE,
    ):
        raise AssertionError(f"Recovery source-action enum is ambiguous: {action_identifiers}")
    if action_property.default != character_designer.RECOVERY_SOURCE_ACTION_ADD:
        raise AssertionError("Add is not the default recovery source action")
    if state.recovery_source_action != character_designer.RECOVERY_SOURCE_ACTION_ADD:
        raise AssertionError("A reset recovery state did not return to Add mode")
    mode_identifiers = tuple(item.identifier for item in mode_property.enum_items)
    if mode_identifiers != (
        character_designer.RECOVERY_CURVE_MODE_BEZIER,
        character_designer.RECOVERY_CURVE_MODE_EXACT,
    ):
        raise AssertionError(f"Recovery mode enum is ambiguous: {mode_identifiers}")
    if mode_property.default != character_designer.RECOVERY_CURVE_MODE_BEZIER:
        raise AssertionError("Bezier is not the default applied-Curve recovery mode")
    if int(count_property.default) != character_designer.RECOVERY_CONTROL_POINTS_DEFAULT:
        raise AssertionError("Bezier control-point default does not match the contract")
    if int(count_property.hard_min) != character_designer.RECOVERY_CONTROL_POINTS_MIN:
        raise AssertionError("Bezier control-point lower bound is not exposed")
    if int(count_property.hard_max) != character_designer.RECOVERY_CONTROL_POINTS_MAX:
        raise AssertionError("Bezier control-point upper bound is not exposed")
    if int(count_property.soft_max) != character_designer.RECOVERY_CONTROL_POINTS_MAX:
        raise AssertionError("The visible control-point slider does not reach its upper bound")
    state.recovery_control_points = 1
    if state.recovery_control_points != character_designer.RECOVERY_CONTROL_POINTS_MIN:
        raise AssertionError("Control-point input did not clamp to its lower bound")
    state.recovery_control_points = 100
    if state.recovery_control_points != character_designer.RECOVERY_CONTROL_POINTS_MAX:
        raise AssertionError("Control-point input did not clamp to its upper bound")


def test_recovery_preview_is_gpu_only_and_tracks_parameters():
    reset_scene()
    original = make_dense_half_round_curve("RecoveryPreviewOriginal", point_count=11)
    source = curve_to_mesh_object(original, "RecoveryPreviewApplied")
    select_all_mesh(source)
    before_fingerprint = mesh_fingerprint(source)
    before_objects = {obj.as_pointer() for obj in bpy.data.objects}
    before_curves = {curve.as_pointer() for curve in bpy.data.curves}
    before_meshes = {mesh.as_pointer() for mesh in bpy.data.meshes}

    source_obj, bm, records = character_designer._infer_selected_recovery_components(
        bpy.context
    )
    exact_plans = character_designer._build_recovery_plans(
        bpy.context,
        source_obj,
        bm,
        records,
        curve_mode=character_designer.RECOVERY_CURVE_MODE_EXACT,
    )
    if len(exact_plans) != 1:
        raise AssertionError("Recovery Preview fixture did not infer one strand")
    exact_section_count = len(exact_plans[0]["profile"]["coordinates"])

    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_BEZIER
    state.recovery_control_points = 3
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD
    state.recovery_preview_enabled = True

    if (
        not state.recovery_preview_enabled
        or not state.preview_active
        or state.preview_mode != "RECOVERY"
        or not state.preview_valid
        or not state.preview_confirmable
    ):
        raise AssertionError("Recovery Preview did not start as a valid RECOVERY session")
    if len(character_designer._LIVE_PREVIEW_WORLD_POINTS) != 3:
        raise AssertionError("Three-point Bezier Preview has the wrong control-point count")
    if len(character_designer._LIVE_PREVIEW_PATHS) != 1:
        raise AssertionError("Three-point Bezier Preview did not publish one path")
    if not character_designer._LIVE_PREVIEW_HANDLE_POINTS:
        raise AssertionError("Bezier Preview did not publish its Aligned handle guides")
    three_point_path = tuple(character_designer._LIVE_PREVIEW_PATHS[0])
    three_point_revision = int(state.preview_revision)

    if {obj.as_pointer() for obj in bpy.data.objects} != before_objects:
        raise AssertionError("Starting Recovery Preview created or removed an Object")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curves:
        raise AssertionError("Starting Recovery Preview created or removed Curve data")
    if {mesh.as_pointer() for mesh in bpy.data.meshes} != before_meshes:
        raise AssertionError("Starting Recovery Preview created or removed Mesh data")
    if mesh_fingerprint(source) != before_fingerprint:
        raise AssertionError("Starting Recovery Preview changed the source Mesh")

    state.recovery_control_points = 5
    if not character_designer._update_recovery_live_preview(bpy.context, force=True):
        raise AssertionError("Forced five-point Recovery Preview update did not run")
    if len(character_designer._LIVE_PREVIEW_WORLD_POINTS) != 5:
        raise AssertionError("Five-point Bezier Preview has the wrong control-point count")
    five_point_path = tuple(character_designer._LIVE_PREVIEW_PATHS[0])
    if five_point_path == three_point_path:
        raise AssertionError("Changing Bezier controls from three to five did not change the path")
    if int(state.preview_revision) <= three_point_revision:
        raise AssertionError("Changing Bezier controls did not publish a new Preview revision")

    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE
    character_designer._update_recovery_live_preview(bpy.context, force=True)
    if not state.preview_valid:
        raise AssertionError("Full-selection Replace Preview was rejected")
    if state.preview_message != "Preview ready - Mesh is removed only after Recover.":
        raise AssertionError(f"Replace Preview has the wrong message: {state.preview_message!r}")
    if bpy.data.objects.get(source.name) is not source:
        raise AssertionError("Replace Preview deleted the source Mesh Object")

    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD
    character_designer._update_recovery_live_preview(bpy.context, force=True)
    if state.preview_message != "Preview ready - source Mesh will be kept.":
        raise AssertionError(f"Add Preview has the wrong message: {state.preview_message!r}")
    if bpy.data.objects.get(source.name) is not source:
        raise AssertionError("Switching Replace Preview back to Add deleted the source Object")

    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
    character_designer._update_recovery_live_preview(bpy.context, force=True)
    if character_designer._LIVE_PREVIEW_HANDLE_POINTS:
        raise AssertionError("Exact Recovery Preview unexpectedly published Bezier handles")
    if len(character_designer._LIVE_PREVIEW_WORLD_POINTS) != exact_section_count:
        raise AssertionError(
            "Exact Recovery Preview control points do not match source cross-sections"
        )
    if (
        len(character_designer._LIVE_PREVIEW_PATHS) != 1
        or len(character_designer._LIVE_PREVIEW_PATHS[0]) != exact_section_count
    ):
        raise AssertionError("Exact Recovery Preview path does not match source cross-sections")

    if {obj.as_pointer() for obj in bpy.data.objects} != before_objects:
        raise AssertionError("Recovery Preview parameter changes altered the Object set")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curves:
        raise AssertionError("Recovery Preview parameter changes altered Curve data")
    if {mesh.as_pointer() for mesh in bpy.data.meshes} != before_meshes:
        raise AssertionError("Recovery Preview parameter changes altered Mesh data")
    if mesh_fingerprint(source) != before_fingerprint:
        raise AssertionError("Recovery Preview parameter changes altered the source Mesh")

    state.recovery_preview_enabled = False
    if state.preview_active or state.preview_mode:
        raise AssertionError("Turning off Recovery Preview left the session active")
    if (
        character_designer._LIVE_PREVIEW_PATHS
        or character_designer._LIVE_PREVIEW_WORLD_POINTS
        or character_designer._LIVE_PREVIEW_HANDLE_POINTS
        or character_designer._LIVE_PREVIEW_LAYERS
    ):
        raise AssertionError("Turning off Recovery Preview left GPU geometry cached")
    if mesh_fingerprint(source) != before_fingerprint:
        raise AssertionError("Turning off Recovery Preview changed the source Mesh")


def test_recovery_preview_partial_replace_clears_and_add_recovers():
    reset_scene()
    original, _points = make_half_round_curve(
        "PartialRecoveryPreviewOriginal",
        straight=True,
        tilts=(0.0, 0.0, 0.0, 0.0),
        offset=0.0,
    )
    source = curve_to_mesh_object(original, "PartialRecoveryPreviewSource")
    wanted_faces = tuple(
        polygon.index
        for polygon in source.data.polygons
        if min(source.data.vertices[index].co.z for index in polygon.vertices) >= 0.39
    )
    select_mesh_faces(source, wanted_faces)
    before_fingerprint = mesh_fingerprint(source)
    before_objects = {obj.as_pointer() for obj in bpy.data.objects}
    before_curves = {curve.as_pointer() for curve in bpy.data.curves}
    before_meshes = {mesh.as_pointer() for mesh in bpy.data.meshes}

    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_BEZIER
    state.recovery_control_points = 4
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD
    state.recovery_preview_enabled = True
    if not state.preview_valid or not character_designer._LIVE_PREVIEW_PATHS:
        raise AssertionError("Partial Add Preview did not produce a recoverable path")

    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE
    character_designer._update_recovery_live_preview(bpy.context, force=True)
    if state.preview_valid or state.preview_level != "ERROR" or state.preview_confirmable:
        raise AssertionError("Partial Replace Preview was not marked invalid")
    if state.preview_message != (
        "Replace Mesh needs the complete source Mesh selected; use Add for a partial band."
    ):
        raise AssertionError(
            f"Partial Replace Preview has the wrong message: {state.preview_message!r}"
        )
    if (
        character_designer._LIVE_PREVIEW_PATHS
        or character_designer._LIVE_PREVIEW_WORLD_POINTS
        or character_designer._LIVE_PREVIEW_HANDLE_POINTS
        or character_designer._LIVE_PREVIEW_LAYERS
    ):
        raise AssertionError("Invalid partial Replace Preview retained stale GPU geometry")
    if bpy.data.objects.get(source.name) is not source:
        raise AssertionError("Invalid partial Replace Preview deleted the source Object")

    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD
    character_designer._update_recovery_live_preview(bpy.context, force=True)
    if (
        not state.preview_valid
        or not state.preview_confirmable
        or not character_designer._LIVE_PREVIEW_PATHS
        or not character_designer._LIVE_PREVIEW_WORLD_POINTS
    ):
        raise AssertionError("Switching an invalid partial Replace Preview to Add did not recover")
    if state.preview_message != "Preview ready - source Mesh will be kept.":
        raise AssertionError("Recovered partial Add Preview has the wrong message")

    if {obj.as_pointer() for obj in bpy.data.objects} != before_objects:
        raise AssertionError("Partial Preview switching altered the Object set")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curves:
        raise AssertionError("Partial Preview switching altered Curve data")
    if {mesh.as_pointer() for mesh in bpy.data.meshes} != before_meshes:
        raise AssertionError("Partial Preview switching altered Mesh data")
    if mesh_fingerprint(source) != before_fingerprint:
        raise AssertionError("Partial Preview switching altered the source Mesh")

    state.recovery_preview_enabled = False
    if state.preview_active or character_designer._LIVE_PREVIEW_PATHS:
        raise AssertionError("Partial Recovery Preview did not stop cleanly")


def test_aligned_handle_geometry_is_explicit_and_stable():
    coordinates = (
        Vector((0.0, 0.0, 0.0)),
        Vector((3.0, 0.0, 0.0)),
        Vector((3.0, 4.0, 0.0)),
    )
    handles = character_designer._recovery_aligned_handles(coordinates)
    expected = (
        (Vector((-1.0, 0.0, 0.0)), Vector((1.0, 0.0, 0.0))),
        (Vector((2.5, -0.5, 0.0)), Vector((11.0 / 3.0, 2.0 / 3.0, 0.0))),
        (Vector((3.0, 8.0 / 3.0, 0.0)), Vector((3.0, 16.0 / 3.0, 0.0))),
    )
    if len(handles) != len(expected):
        raise AssertionError("Aligned-handle helper returned the wrong number of pairs")
    for index, ((actual_left, actual_right), (expected_left, expected_right)) in enumerate(
        zip(handles, expected)
    ):
        assert_vector_close(
            actual_left,
            expected_left,
            tolerance=5.0e-7,
            message=f"Explicit left handle {index} is unstable",
        )
        assert_vector_close(
            actual_right,
            expected_right,
            tolerance=5.0e-7,
            message=f"Explicit right handle {index} is unstable",
        )
        left_vector = coordinates[index] - Vector(actual_left)
        right_vector = Vector(actual_right) - coordinates[index]
        if left_vector.cross(right_vector).length > 1.0e-7:
            raise AssertionError(f"Explicit handle pair {index} is not collinear")
        if left_vector.dot(right_vector) < -1.0e-8:
            raise AssertionError(f"Explicit handle pair {index} is not Aligned")

    folded_coordinates = (
        Vector((-1.0, 0.0, 0.0)),
        Vector((0.0, 0.0, 0.0)),
        Vector((-1.0, 0.0, 0.0)),
    )
    folded = character_designer._recovery_aligned_handles(folded_coordinates)
    assert_vector_close(folded[1][0], folded_coordinates[1], tolerance=1.0e-8)
    assert_vector_close(folded[1][1], folded_coordinates[1], tolerance=1.0e-8)
    if not all(math.isfinite(float(value)) for pair in folded for handle in pair for value in handle):
        raise AssertionError("A folded path produced a non-finite Aligned handle")


def test_bezier_profile_resampling_uses_uniform_arc_length():
    profile = {
        "coordinates": (
            Vector((0.0, 0.0, 0.0)),
            Vector((0.0, 0.0, 1.0)),
            Vector((0.0, 0.0, 3.0)),
        ),
        "radii": (1.0, 2.0, 4.0),
        "tilts": (0.0, 0.5, 1.5),
    }
    sampled = character_designer._resample_recovery_profile(profile, 3)
    expected_coordinates = (
        Vector((0.0, 0.0, 0.0)),
        Vector((0.0, 0.0, 1.5)),
        Vector((0.0, 0.0, 3.0)),
    )
    expected_radii = (1.0, 2.5, 4.0)
    expected_tilts = (0.0, 0.75, 1.5)
    for actual, expected in zip(sampled["coordinates"], expected_coordinates):
        assert_vector_close(actual, expected, tolerance=1.0e-8)
    for actual, expected in zip(sampled["radii"], expected_radii):
        assert_close(actual, expected, tolerance=1.0e-8)
    for actual, expected in zip(sampled["tilts"], expected_tilts):
        assert_close(actual, expected, tolerance=1.0e-8)
    try:
        character_designer._resample_recovery_profile(profile, 2)
    except character_designer.CenterlineError:
        pass
    else:
        raise AssertionError("Bezier resampling accepted fewer than three control points")
    try:
        character_designer._resample_recovery_profile(profile, 33)
    except character_designer.CenterlineError:
        pass
    else:
        raise AssertionError("Bezier resampling accepted more than 32 control points")

    wrapped_profile = {
        "coordinates": (
            Vector((0.0, 0.0, 0.0)),
            Vector((0.0, 0.0, 1.0)),
            Vector((0.0, 0.0, 2.0)),
        ),
        "radii": (1.0, 1.0, 1.0),
        "tilts": (3.0, -3.0, -2.8),
    }
    wrapped = character_designer._resample_recovery_profile(wrapped_profile, 5)
    if max(
        abs(second - first)
        for first, second in zip(wrapped["tilts"], wrapped["tilts"][1:])
    ) >= math.pi:
        raise AssertionError("Bezier Tilt interpolation crossed the long way around ±π")
    assert_close(wrapped["tilts"][1], math.pi, tolerance=1.0e-6)


def test_bezier_count_updates_in_place_and_exact_remains_available():
    reset_scene()
    original = make_dense_half_round_curve("DenseBezierOriginal", point_count=11)
    source = curve_to_mesh_object(original, "DenseBezierApplied")
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    source_cloud = evaluated_vertex_cloud(source)
    state = bpy.context.window_manager.character_designer

    source_obj, bm, records = character_designer._infer_selected_recovery_components(
        bpy.context
    )
    exact_plan = character_designer._build_recovery_plans(
        bpy.context,
        source_obj,
        bm,
        records,
        curve_mode=character_designer.RECOVERY_CURVE_MODE_EXACT,
    )[0]
    exact_profile = exact_plan["profile"]
    source_point_count = len(exact_profile["coordinates"])
    if source_point_count != 11:
        raise AssertionError(f"Dense fixture recovered {source_point_count} source layers, not 11")

    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_BEZIER
    target = None
    target_pointer = None
    prior_data_pointer = None
    for requested_count in (3, 5, 32):
        state.recovery_control_points = requested_count
        expected = character_designer._resample_recovery_profile(
            exact_profile,
            requested_count,
        )
        if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
            raise AssertionError(f"Bezier recovery with {requested_count} points failed")
        if (
            bpy.context.mode != "EDIT_MESH"
            or bpy.context.edit_object is not source
            or bpy.context.active_object is not source
        ):
            raise AssertionError("Bezier recovery changed the active Mesh Edit Mode context")
        curves = recovered_curves(source)
        if len(curves) != 1:
            raise AssertionError("Changing Bezier point count created a duplicate output")
        target = curves[0]
        if target_pointer is None:
            target_pointer = target.as_pointer()
        elif target.as_pointer() != target_pointer:
            raise AssertionError("Changing Bezier point count replaced the Curve Object")
        if prior_data_pointer is not None and target.data.as_pointer() == prior_data_pointer:
            raise AssertionError("Changing Bezier point count was incorrectly treated as unchanged")
        prior_data_pointer = target.data.as_pointer()
        spline = target.data.splines[0]
        if spline.type != "BEZIER" or len(spline.bezier_points) != requested_count:
            raise AssertionError(f"Requested {requested_count} Bezier points were not created")
        if int(target.data.resolution_u) != character_designer.RECOVERY_BEZIER_RESOLUTION:
            raise AssertionError("Bezier output did not receive its smooth Curve resolution")
        for point, coordinate, radius, tilt in zip(
            spline.bezier_points,
            expected["coordinates"],
            expected["radii"],
            expected["tilts"],
        ):
            assert_vector_close(point.co, coordinate, tolerance=1.0e-6)
            assert_close(point.radius, radius, tolerance=1.0e-6)
            assert_close(point.tilt, tilt, tolerance=1.0e-6)
        assert_aligned_bezier_handles(
            spline,
            expected["coordinates"],
            tolerance=1.0e-6,
        )
        if target.get(character_designer.RECOVERY_CURVE_MODE_KEY) != "BEZIER":
            raise AssertionError("Bezier mode was not recorded on the recovery Object")
        if target.get(character_designer.RECOVERY_CONTROL_POINTS_KEY) != requested_count:
            raise AssertionError("Bezier control-point count was not recorded")
        metadata = character_designer._curve_cross_section_metadata(
            target,
            validate_spline=False,
        )
        if metadata is None or metadata["point_count"] != source_point_count:
            raise AssertionError("Bezier output lost its complete source-section metadata")
        if not character_designer._is_recovered_curve(target):
            raise AssertionError("A valid reduced Bezier output was considered unreadable")
        if mesh_fingerprint(source) != before:
            raise AssertionError("Bezier recovery changed the source Mesh or selection")

    unchanged_data_pointer = target.data.as_pointer()
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Repeating an unchanged Bezier recovery failed")
    if target.data.as_pointer() != unchanged_data_pointer:
        raise AssertionError("Unchanged Bezier recovery unnecessarily replaced Curve data")

    bezier_mutations = (
        (
            "spline resolution",
            lambda spline: setattr(spline, "resolution_u", 2),
            lambda spline: int(spline.resolution_u)
            == character_designer.RECOVERY_BEZIER_RESOLUTION,
        ),
        (
            "Radius interpolation",
            lambda spline: setattr(spline, "radius_interpolation", "CARDINAL"),
            lambda spline: spline.radius_interpolation == "LINEAR",
        ),
        (
            "Tilt interpolation",
            lambda spline: setattr(spline, "tilt_interpolation", "EASE"),
            lambda spline: spline.tilt_interpolation == "LINEAR",
        ),
        (
            "Bezier handle type",
            lambda spline: setattr(spline.bezier_points[1], "handle_left_type", "FREE"),
            lambda spline: spline.bezier_points[1].handle_left_type == "ALIGNED",
        ),
        (
            "Bezier handle coordinate",
            lambda spline: setattr(
                spline.bezier_points[1],
                "handle_left",
                spline.bezier_points[1].handle_left + Vector((0.17, -0.09, 0.04)),
            ),
            lambda spline: (
                Vector(spline.bezier_points[1].handle_left)
                - Vector(
                    character_designer._recovery_aligned_handles(
                        tuple(point.co.copy() for point in spline.bezier_points)
                    )[1][0]
                )
            ).length
            <= 1.0e-6,
        ),
    )
    for label, mutate, repaired in bezier_mutations:
        old_data_pointer = target.data.as_pointer()
        mutate(target.data.splines[0])
        if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
            raise AssertionError(f"Repairing Bezier {label} failed")
        if target.as_pointer() != target_pointer:
            raise AssertionError(f"Repairing Bezier {label} replaced the Curve Object")
        if target.data.as_pointer() == old_data_pointer:
            raise AssertionError(f"Damaged Bezier {label} was falsely reported unchanged")
        if not repaired(target.data.splines[0]):
            raise AssertionError(f"Bezier {label} was not restored")
        repaired_spline = target.data.splines[0]
        assert_aligned_bezier_handles(
            repaired_spline,
            tuple(point.co.copy() for point in repaired_spline.bezier_points),
            tolerance=1.0e-6,
        )

    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
    exact_old_data_pointer = target.data.as_pointer()
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Switching a Bezier recovery back to Exact failed")
    if target.as_pointer() != target_pointer or target.data.as_pointer() == exact_old_data_pointer:
        raise AssertionError("Bezier-to-Exact did not update the same Curve Object")
    spline = target.data.splines[0]
    if spline.type != "POLY" or len(spline.points) != source_point_count:
        raise AssertionError("Exact mode did not restore one Poly point per source section")
    if target.get(character_designer.RECOVERY_CURVE_MODE_KEY) != "EXACT":
        raise AssertionError("Exact mode was not recorded on the recovery Object")
    if target.get(character_designer.RECOVERY_CONTROL_POINTS_KEY) != source_point_count:
        raise AssertionError("Exact mode did not record its full source point count")
    for point, coordinate, radius, tilt in zip(
        spline.points,
        exact_profile["coordinates"],
        exact_profile["radii"],
        exact_profile["tilts"],
    ):
        assert_vector_close(point.co.xyz, coordinate, tolerance=1.0e-6)
        assert_close(point.radius, radius, tolerance=1.0e-6)
        assert_close(point.tilt, tilt, tolerance=1.0e-6)
    if (
        bpy.context.mode != "EDIT_MESH"
        or bpy.context.edit_object is not source
        or bpy.context.active_object is not source
    ):
        raise AssertionError("Switching to Exact changed the active Mesh Edit Mode context")
    assert_vertex_clouds_equivalent(
        evaluated_vertex_cloud(target),
        source_cloud,
        tolerance=8.0e-4,
    )
    if mesh_fingerprint(source) != before:
        raise AssertionError("Bezier-to-Exact update changed the source Mesh or selection")


def test_legacy_exact_recovery_upgrades_to_bezier_in_place():
    reset_scene()
    original, _points = make_half_round_curve("LegacyExactOriginal")
    source = curve_to_mesh_object(original, "LegacyExactApplied")
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Legacy fixture Exact recovery failed")
    target = recovered_curves(source)[0]
    target_pointer = target.as_pointer()
    stored_profile = target[character_designer.RECOVERY_PROFILE_KEY]
    target[character_designer.RECOVERY_PROFILE_KEY] = [1, 2]
    if character_designer._is_recovered_curve(target):
        raise AssertionError("A non-string recovery profile was accepted")
    target[character_designer.RECOVERY_PROFILE_KEY] = stored_profile
    target[character_designer.RECOVERY_CURVE_MODE_KEY] = [1, 2]
    if character_designer._is_recovered_curve(target):
        raise AssertionError("A non-string recovery mode was accepted")
    del target[character_designer.RECOVERY_CURVE_MODE_KEY]
    del target[character_designer.RECOVERY_CONTROL_POINTS_KEY]
    if not character_designer._is_recovered_curve(target):
        raise AssertionError("A valid 0.16-style Exact recovery was not recognized")

    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_BEZIER
    state.recovery_control_points = 4
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Legacy Exact output could not upgrade to Bezier")
    if target.as_pointer() != target_pointer:
        raise AssertionError("Legacy upgrade replaced its Curve Object")
    if target.data.splines[0].type != "BEZIER":
        raise AssertionError("Legacy output did not upgrade to a Bezier spline")
    if len(target.data.splines[0].bezier_points) != 4:
        raise AssertionError("Legacy upgrade did not honor the chosen point count")
    if target.get(character_designer.RECOVERY_CURVE_MODE_KEY) != "BEZIER":
        raise AssertionError("Legacy upgrade did not write the new mode metadata")
    if target.get(character_designer.RECOVERY_CONTROL_POINTS_KEY) != 4:
        raise AssertionError("Legacy upgrade did not write the new point-count metadata")
    if (
        bpy.context.mode != "EDIT_MESH"
        or bpy.context.edit_object is not source
        or bpy.context.active_object is not source
    ):
        raise AssertionError("Legacy upgrade changed the active Mesh Edit Mode context")
    if mesh_fingerprint(source) != before:
        raise AssertionError("Legacy upgrade changed the source Mesh or selection")


def test_exact_mode_is_not_capped_by_bezier_point_limit():
    reset_scene()
    source_sections = character_designer.RECOVERY_CONTROL_POINTS_MAX + 8
    original = make_dense_half_round_curve(
        "LongExactOriginal",
        point_count=source_sections,
    )
    source = curve_to_mesh_object(original, "LongExactApplied")
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
    state.recovery_control_points = character_designer.RECOVERY_CONTROL_POINTS_MAX
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Exact recovery with more than 32 source sections failed")
    target = recovered_curves(source)[0]
    spline = target.data.splines[0]
    if spline.type != "POLY" or len(spline.points) != source_sections:
        raise AssertionError("Exact mode was incorrectly capped by the Bezier slider")
    if target.get(character_designer.RECOVERY_CONTROL_POINTS_KEY) != source_sections:
        raise AssertionError("Exact mode stored the Bezier cap instead of the source layer count")
    if (
        bpy.context.mode != "EDIT_MESH"
        or bpy.context.edit_object is not source
        or bpy.context.active_object is not source
        or mesh_fingerprint(source) != before
    ):
        raise AssertionError("Long Exact recovery changed the source Mesh context")


def test_two_disconnected_strands_are_created_and_reused_independently():
    reset_scene()
    first, _points = make_half_round_curve("FirstApplied", x_offset=-0.8)
    second, _points = make_half_round_curve("SecondApplied", x_offset=0.9)
    first_mesh = curve_to_mesh_object(first, "FirstMesh")
    second_mesh = curve_to_mesh_object(second, "SecondMesh")
    source = join_mesh_objects((first_mesh, second_mesh), "TwoAppliedStrands")
    select_all_mesh(source)

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Batch recovery failed")
    curves = recovered_curves(source)
    if len(curves) != 2:
        raise AssertionError(f"Expected two recovered Curve objects, got {len(curves)}")
    pointers = {curve.as_pointer() for curve in curves}
    signatures = {curve.get(character_designer.RECOVERY_SIGNATURE_KEY) for curve in curves}
    if len(signatures) != 2:
        raise AssertionError("Disconnected strands received the same component signature")

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Idempotent batch recovery failed")
    repeated = recovered_curves(source)
    if len(repeated) != 2 or {curve.as_pointer() for curve in repeated} != pointers:
        raise AssertionError("Repeated recovery created duplicates or replaced Curve Objects")

    bm = bmesh.from_edit_mesh(source.data)
    bm.verts.ensure_lookup_table()
    selected_vertices = {vertex.index for vertex in bm.verts if vertex.select}
    components = character_designer._vertex_components(
        selected_vertices,
        character_designer._selected_edge_keys(bm, selected_vertices),
    )
    component = min(components, key=lambda value: min(value))
    matching = []
    for curve in repeated:
        stored = {
            index
            for layer in json.loads(curve["character_designer_layer_vertices"])
            for index in layer
        }
        if stored == set(component):
            matching.append(curve)
    if len(matching) != 1:
        raise AssertionError("Could not resolve one recovered Curve for the first component")
    changed_target = matching[0]
    untouched_target = next(curve for curve in repeated if curve is not changed_target)
    changed_object_pointer = changed_target.as_pointer()
    changed_data_pointer = changed_target.data.as_pointer()
    untouched_fingerprint = (
        untouched_target.as_pointer(),
        untouched_target.data.as_pointer(),
        tuple(point.co.copy() for point in untouched_target.data.splines[0].points),
    )
    bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(source.data)
    bm.verts.ensure_lookup_table()
    for index in component:
        bm.verts[index].co.x += 0.045
        bm.verts[index].select_set(True)
    bmesh.update_edit_mesh(source.data, loop_triangles=False, destructive=False)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Independent component update failed")
    if changed_target.as_pointer() != changed_object_pointer:
        raise AssertionError("Component update replaced its Curve Object")
    if changed_target.data.as_pointer() == changed_data_pointer:
        raise AssertionError("Changed source geometry was incorrectly treated as unchanged")
    after_untouched = (
        untouched_target.as_pointer(),
        untouched_target.data.as_pointer(),
        tuple(point.co.copy() for point in untouched_target.data.splines[0].points),
    )
    if after_untouched != untouched_fingerprint:
        raise AssertionError("Updating one component modified the other recovered strand")
    if len(recovered_curves(source)) != 2:
        raise AssertionError("Independent update created an extra recovered Curve")


def test_closed_rectangle_profile_recovers_without_helper_object():
    reset_scene()
    original = make_rectangle_curve("RectangleOriginal")
    source = curve_to_mesh_object(original, "RectangleApplied")
    select_all_mesh(source)
    source_cloud = evaluated_vertex_cloud(source)

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Rectangle recovery failed")
    curves = recovered_curves(source)
    if len(curves) != 1:
        raise AssertionError("Rectangle recovery did not create exactly one Curve")
    recovered = curves[0]
    if recovered.get(character_designer.RECOVERY_PROFILE_KEY) != "RECTANGLE":
        raise AssertionError("Rectangle profile was not identified")
    if recovered.data.bevel_mode != "PROFILE" or recovered.data.fill_mode != "FULL":
        raise AssertionError("Rectangle was not rebuilt with an embedded Curve Profile")
    if any(obj.type == "EMPTY" for obj in bpy.context.scene.objects):
        raise AssertionError("Rectangle recovery created an unnecessary helper Empty")
    assert_vertex_clouds_equivalent(
        evaluated_vertex_cloud(recovered),
        source_cloud,
        tolerance=8.0e-4,
    )


def test_selected_face_band_stops_at_its_exact_range():
    reset_scene()
    original, _points = make_half_round_curve(
        "PartialOriginal",
        straight=True,
        tilts=(0.0, 0.0, 0.0, 0.0),
        offset=0.0,
    )
    source = curve_to_mesh_object(original, "PartialApplied")
    wanted_faces = tuple(
        polygon.index
        for polygon in source.data.polygons
        if min(source.data.vertices[index].co.z for index in polygon.vertices) >= 0.39
    )
    if not wanted_faces:
        raise AssertionError("Partial-band fixture selected no faces")
    select_mesh_faces(source, wanted_faces)
    before = mesh_fingerprint(source)

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Selected partial face-band recovery failed")
    if mesh_fingerprint(source) != before:
        raise AssertionError("Partial recovery changed its exact face selection")
    curves = recovered_curves(source)
    if len(curves) != 1 or len(curves[0].data.splines[0].points) != 3:
        raise AssertionError("Partial recovery crossed into unselected adjacent hair rows")


def test_longitudinal_guide_edge_path_expands_to_complete_sections():
    reset_scene()
    original, _points = make_half_round_curve(
        "GuideOriginal",
        tilts=(0.0, 0.0, 0.0, 0.0),
        offset=0.0,
        straight=True,
    )
    source = curve_to_mesh_object(original, "GuideAppliedHair")
    edge_keys = find_longitudinal_rail(source)
    select_mesh_edges(source, edge_keys)
    before = mesh_fingerprint(source)

    result = bpy.ops.character_designer.recover_applied_curve()
    if result != {"FINISHED"}:
        raise AssertionError(f"Guide-edge recovery failed: {result}")
    if mesh_fingerprint(source) != before:
        raise AssertionError("Guide-edge recovery changed the selection or source")
    curves = recovered_curves(source)
    if len(curves) != 1 or len(curves[0].data.splines[0].points) != 4:
        raise AssertionError("Guide path did not recover the four complete cross-sections")


def test_add_mode_is_default_and_preserves_source_edit_context():
    reset_scene()
    state = bpy.context.window_manager.character_designer
    if state.recovery_source_action != character_designer.RECOVERY_SOURCE_ACTION_ADD:
        raise AssertionError("Applied-Curve recovery did not default to Add")
    original, _points = make_half_round_curve("DefaultAddOriginal")
    source = curve_to_mesh_object(original, "DefaultAddSource")
    source_name = source.name
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    source_pointer = source.as_pointer()

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Default Add recovery failed")
    if bpy.context.scene.objects.get(source_name) is not source or source.as_pointer() != source_pointer:
        raise AssertionError("Default Add removed or replaced the source Mesh Object")
    if (
        bpy.context.mode != "EDIT_MESH"
        or bpy.context.edit_object is not source
        or bpy.context.active_object is not source
        or mesh_fingerprint(source) != before
    ):
        raise AssertionError("Default Add changed Mesh Edit Mode, selection, or geometry")
    if len(recovered_curves(source)) != 1:
        raise AssertionError("Default Add did not create one source-linked Curve")


def test_replace_mesh_removes_only_source_object_and_selects_result():
    reset_scene()
    original, _points = make_half_round_curve("ReplaceOriginal")
    source = curve_to_mesh_object(original, "ReplaceSource")
    source_name = source.name
    source_pointer = source.as_pointer()
    source_mesh = source.data
    source_mesh_name = source_mesh.name
    shared_user = bpy.data.objects.new("ReplaceSharedMeshUser", source_mesh)
    bpy.context.scene.collection.objects.link(shared_user)
    if source_mesh.users != 2:
        raise AssertionError("Shared Mesh-data fixture did not have two users")
    select_all_mesh(source)
    state = bpy.context.window_manager.character_designer
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Replace fixture could not create its initial Add output")
    existing = recovered_curves(source)
    if len(existing) != 1:
        raise AssertionError("Replace fixture Add did not create one reusable output")
    existing_pointer = existing[0].as_pointer()
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Replace Mesh recovery failed")
    if bpy.context.mode != "OBJECT" or bpy.context.edit_object is not None:
        raise AssertionError("Replace Mesh did not finish in Object Mode")
    if bpy.data.objects.get(source_name) is not None or any(
        obj.as_pointer() == source_pointer for obj in bpy.data.objects
    ):
        raise AssertionError("Replace Mesh did not delete the source Object")
    if bpy.data.meshes.get(source_mesh_name) is not source_mesh:
        raise AssertionError("Replace Mesh deleted the source Mesh datablock")
    if shared_user.data is not source_mesh or source_mesh.users != 1:
        raise AssertionError("Replace Mesh damaged another Object sharing the Mesh data")
    outputs = generated_recovery_curves()
    if len(outputs) != 1:
        raise AssertionError(f"Replace Mesh created {len(outputs)} outputs instead of one")
    if outputs[0].as_pointer() != existing_pointer:
        raise AssertionError("Replace Mesh replaced an existing recovery Object")
    if outputs[0].get(character_designer.RECOVERY_SOURCE_OBJECT_KEY) is not None:
        raise AssertionError("Replaced output retained a dangling source-Object pointer")
    selected_pointers = {obj.as_pointer() for obj in bpy.context.selected_objects}
    output_pointers = {obj.as_pointer() for obj in outputs}
    if selected_pointers != output_pointers or bpy.context.active_object not in outputs:
        raise AssertionError("Replace Mesh did not select only its generated Curve result")


def test_replace_mesh_supports_two_disconnected_strands():
    reset_scene()
    first, _points = make_half_round_curve("ReplaceStrandA", x_offset=-0.8)
    second, _points = make_half_round_curve("ReplaceStrandB", x_offset=0.9)
    source = join_mesh_objects(
        (
            curve_to_mesh_object(first, "ReplaceMeshA"),
            curve_to_mesh_object(second, "ReplaceMeshB"),
        ),
        "ReplaceTwoStrands",
    )
    source_name = source.name
    source_mesh = source.data
    source_mesh_name = source_mesh.name
    select_all_mesh(source)
    state = bpy.context.window_manager.character_designer
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE

    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Two-strand Replace Mesh recovery failed")
    if bpy.data.objects.get(source_name) is not None:
        raise AssertionError("Two-strand Replace Mesh retained its source Object")
    if bpy.data.meshes.get(source_mesh_name) is not source_mesh or source_mesh.users != 0:
        raise AssertionError("Two-strand Replace Mesh removed its recoverable Mesh datablock")
    outputs = generated_recovery_curves()
    if len(outputs) != 2:
        raise AssertionError(f"Two-strand Replace created {len(outputs)} Curve Objects")
    signatures = {
        output.get(character_designer.RECOVERY_SIGNATURE_KEY) for output in outputs
    }
    if len(signatures) != 2 or None in signatures:
        raise AssertionError("Two-strand Replace lost independent component signatures")
    if bpy.context.mode != "OBJECT":
        raise AssertionError("Two-strand Replace did not finish in Object Mode")
    if {obj.as_pointer() for obj in bpy.context.selected_objects} != {
        obj.as_pointer() for obj in outputs
    }:
        raise AssertionError("Two-strand Replace did not select both generated Curves")
    if bpy.context.active_object not in outputs:
        raise AssertionError("Two-strand Replace did not leave a result active")


def test_partial_selection_replace_is_rejected_without_writes():
    reset_scene()
    original, _points = make_half_round_curve(
        "PartialReplaceOriginal",
        straight=True,
        tilts=(0.0, 0.0, 0.0, 0.0),
        offset=0.0,
    )
    source = curve_to_mesh_object(original, "PartialReplaceSource")
    wanted_faces = tuple(
        polygon.index
        for polygon in source.data.polygons
        if min(source.data.vertices[index].co.z for index in polygon.vertices) >= 0.39
    )
    select_mesh_faces(source, wanted_faces)
    before = mesh_fingerprint(source)
    before_objects = {obj.as_pointer() for obj in bpy.data.objects}
    before_curves = {curve.as_pointer() for curve in bpy.data.curves}
    state = bpy.context.window_manager.character_designer
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE

    result = bpy.ops.character_designer.recover_applied_curve()
    if result != {"CANCELLED"}:
        raise AssertionError("Replace Mesh accepted a partial source selection")
    if bpy.context.edit_object is not source or mesh_fingerprint(source) != before:
        raise AssertionError("Rejected partial Replace changed source mode, selection, or geometry")
    if {obj.as_pointer() for obj in bpy.data.objects} != before_objects:
        raise AssertionError("Rejected partial Replace created or removed an Object")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curves:
        raise AssertionError("Rejected partial Replace created or removed Curve data")


def test_unsupported_modifier_is_rejected_without_writes():
    reset_scene()
    original, _points = make_half_round_curve("UnsupportedModifierOriginal")
    source = curve_to_mesh_object(original, "UnsupportedModifierSource")
    modifier = source.modifiers.new("Unsupported Solidify", "SOLIDIFY")
    modifier.thickness = 0.031
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    before_objects = {obj.as_pointer() for obj in bpy.data.objects}
    before_curves = {curve.as_pointer() for curve in bpy.data.curves}
    before_meshes = {mesh.as_pointer() for mesh in bpy.data.meshes}
    state = bpy.context.window_manager.character_designer
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD

    state.recovery_preview_enabled = True
    if state.preview_valid or state.preview_confirmable or state.preview_level != "ERROR":
        raise AssertionError("Recovery Preview accepted an unsupported modifier")
    if (
        "only Mirror and Subdivision" not in state.preview_message
        or "unsupported:" not in state.preview_message
    ):
        raise AssertionError(
            f"Unsupported modifier Preview has the wrong message: {state.preview_message!r}"
        )
    if (
        character_designer._LIVE_PREVIEW_PATHS
        or character_designer._LIVE_PREVIEW_WORLD_POINTS
        or character_designer._LIVE_PREVIEW_HANDLE_POINTS
    ):
        raise AssertionError("Unsupported modifier Preview retained stale GPU geometry")
    state.recovery_preview_enabled = False

    result = bpy.ops.character_designer.recover_applied_curve()
    if result != {"CANCELLED"}:
        raise AssertionError("Recovery accepted an unsupported Solidify modifier")
    if bpy.context.edit_object is not source or mesh_fingerprint(source) != before:
        raise AssertionError("Rejected unsupported modifier changed its source")
    if (
        source.modifiers.get("Unsupported Solidify") is None
        or source.modifiers.get("Unsupported Solidify").as_pointer()
        != modifier.as_pointer()
    ):
        raise AssertionError("Rejected recovery changed the unsupported source Modifier")
    if {obj.as_pointer() for obj in bpy.data.objects} != before_objects:
        raise AssertionError("Rejected unsupported modifier created or removed an Object")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curves:
        raise AssertionError("Rejected unsupported modifier created or removed Curve data")
    if {mesh.as_pointer() for mesh in bpy.data.meshes} != before_meshes:
        raise AssertionError("Rejected unsupported modifier created or removed Mesh data")


def test_replace_rejects_recovery_output_in_another_scene():
    reset_scene()
    original, _points = make_half_round_curve("CrossSceneReplaceOriginal")
    source = curve_to_mesh_object(original, "CrossSceneReplaceSource")
    select_all_mesh(source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Cross-Scene Replace fixture could not create its Add output")
    target = recovered_curves(source)[0]
    target_pointer = target.as_pointer()

    bpy.ops.object.mode_set(mode="OBJECT")
    other_scene = bpy.data.scenes.new("RecoveryOutputOtherScene")
    other_scene.collection.objects.link(target)
    for collection in tuple(target.users_collection):
        if collection is not other_scene.collection:
            collection.objects.unlink(target)
    select_all_mesh(source)
    before = mesh_fingerprint(source)
    state = bpy.context.window_manager.character_designer
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE
    try:
        result = bpy.ops.character_designer.recover_applied_curve()
        if result != {"CANCELLED"}:
            raise AssertionError("Replace ignored a source-linked output in another Scene")
        if bpy.context.edit_object is not source or mesh_fingerprint(source) != before:
            raise AssertionError("Rejected cross-Scene Replace changed the source Mesh")
        if target.as_pointer() != target_pointer or target.get(
            character_designer.RECOVERY_SOURCE_OBJECT_KEY
        ) is not source:
            raise AssertionError("Rejected cross-Scene Replace damaged the remote output")
    finally:
        if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if target.name in bpy.data.objects:
            bpy.data.objects.remove(target, do_unlink=True)
        if other_scene.name in bpy.data.scenes:
            bpy.data.scenes.remove(other_scene)


def test_replace_failure_before_delete_rolls_back_every_write():
    reset_scene()
    original, _points = make_half_round_curve("ReplaceRollbackOriginal")
    source = curve_to_mesh_object(original, "ReplaceRollbackSource")
    companion_data = bpy.data.curves.new("ReplaceRollbackCompanionData", "CURVE")
    companion_spline = companion_data.splines.new("POLY")
    companion_spline.points.add(1)
    companion = bpy.data.objects.new("ReplaceRollbackCompanion", companion_data)
    bpy.context.scene.collection.objects.link(companion)
    select_all_mesh(source)
    companion.select_set(True)
    if not companion.select_get():
        raise AssertionError("Rollback fixture could not retain an extra Object selection")
    before = mesh_fingerprint(source)
    before_objects = {obj.as_pointer() for obj in bpy.data.objects}
    before_curves = {curve.as_pointer() for curve in bpy.data.curves}
    state = bpy.context.window_manager.character_designer
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_REPLACE
    original_apply = character_designer._apply_recovered_curve_plan

    def fail_after_curve_write(context, plan):
        original_apply(context, plan)
        raise character_designer.CenterlineError("Injected Replace pre-delete failure")

    character_designer._apply_recovered_curve_plan = fail_after_curve_write
    try:
        result = bpy.ops.character_designer.recover_applied_curve()
    finally:
        character_designer._apply_recovered_curve_plan = original_apply
    if result != {"CANCELLED"}:
        raise AssertionError("Injected Replace transaction failure did not cancel")
    if bpy.context.edit_object is not source or mesh_fingerprint(source) != before:
        raise AssertionError("Failed Replace did not restore source Edit Mode and selection")
    if not companion.select_get():
        raise AssertionError("Failed Replace did not restore the extra Object selection")
    if {obj.as_pointer() for obj in bpy.data.objects} != before_objects:
        raise AssertionError("Failed Replace left behind or deleted an Object")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curves:
        raise AssertionError("Failed Replace left behind or deleted Curve data")
    if generated_recovery_curves():
        raise AssertionError("Failed Replace left behind a generated Curve")


def test_modifier_update_property_failure_rolls_back_every_write():
    reset_scene()
    original, _points = make_half_round_curve(
        "ModifierRollbackOriginal",
        x_offset=0.71,
    )
    source = curve_to_mesh_object(original, "ModifierRollbackSource")
    add_supported_recovery_modifiers(source, ("MIRROR", "SUBSURF"))
    select_all_mesh(source)
    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Modifier rollback fixture recovery failed")
    targets = recovered_curves(source)
    if len(targets) != 1:
        raise AssertionError("Modifier rollback fixture did not create one managed Curve")
    target = targets[0]
    target_pointer = target.as_pointer()
    old_data = target.data
    old_modifier_stack = supported_modifier_stack_snapshot(target)
    old_properties = recovery_managed_properties_snapshot(target)

    source.modifiers.move(1, 0)
    source.modifiers[0].subdivision_type = "SIMPLE"
    source.modifiers[1].use_mirror_merge = True
    source.modifiers[1].merge_threshold = 0.009
    changed_source_stack = supported_modifier_stack_snapshot(source)
    before_source = mesh_fingerprint(source)
    before_objects = {obj.as_pointer() for obj in bpy.data.objects}
    before_curves = {curve.as_pointer() for curve in bpy.data.curves}
    before_meshes = {mesh.as_pointer() for mesh in bpy.data.meshes}

    original_write = character_designer._write_recovery_properties
    writes = []

    def fail_after_managed_properties(curve_obj, plan):
        original_write(curve_obj, plan)
        writes.append(curve_obj.as_pointer())
        raise character_designer.CenterlineError(
            "Injected modifier property-write failure"
        )

    character_designer._write_recovery_properties = fail_after_managed_properties
    try:
        result = bpy.ops.character_designer.recover_applied_curve()
    finally:
        character_designer._write_recovery_properties = original_write

    if result != {"CANCELLED"} or writes != [target_pointer]:
        raise AssertionError("Injected modifier property-write failure did not cancel once")
    restored = recovered_curves(source)
    if len(restored) != 1 or restored[0].as_pointer() != target_pointer:
        raise AssertionError("Modifier rollback replaced or duplicated the managed Curve Object")
    target = restored[0]
    if target.data is not old_data:
        raise AssertionError("Modifier rollback did not restore the original Curve Data")
    if supported_modifier_stack_snapshot(target) != old_modifier_stack:
        raise AssertionError("Modifier rollback did not restore stack order and parameters")
    if recovery_managed_properties_snapshot(target) != old_properties:
        raise AssertionError("Modifier rollback did not restore all managed properties")
    if supported_modifier_stack_snapshot(source) != changed_source_stack:
        raise AssertionError("Failed recovery changed the artist's source modifier stack")
    if bpy.context.edit_object is not source or mesh_fingerprint(source) != before_source:
        raise AssertionError("Modifier rollback changed source Edit Mode or selection")
    if {obj.as_pointer() for obj in bpy.data.objects} != before_objects:
        raise AssertionError("Modifier rollback changed the Object datablock set")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curves:
        raise AssertionError("Modifier rollback leaked or removed Curve data")
    if {mesh.as_pointer() for mesh in bpy.data.meshes} != before_meshes:
        raise AssertionError("Modifier rollback changed the Mesh datablock set")
    if state.last_level != "INFO" or "Injected modifier" not in state.last_message:
        raise AssertionError("Injected safe failure was not reported as ordinary information")


def test_artist_added_modifier_cancels_without_overwriting_output():
    reset_scene()
    original, _points = make_half_round_curve(
        "ArtistModifierOriginal",
        x_offset=0.69,
    )
    source = curve_to_mesh_object(original, "ArtistModifierSource")
    add_supported_recovery_modifiers(source, ("MIRROR", "SUBSURF"))
    select_all_mesh(source)
    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_EXACT
    state.recovery_source_action = character_designer.RECOVERY_SOURCE_ACTION_ADD
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Artist modifier fixture recovery failed")
    targets = recovered_curves(source)
    if len(targets) != 1:
        raise AssertionError("Artist modifier fixture did not create one managed Curve")
    target = targets[0]
    target_pointer = target.as_pointer()
    target_data = target.data
    extra = target.modifiers.new("Artist Extra Mirror", "MIRROR")
    extra.use_axis = (False, True, False)
    extra.use_mirror_merge = False
    extra.merge_threshold = 0.0123
    extra_pointer = extra.as_pointer()
    before_modifier_stack = supported_modifier_stack_snapshot(target)
    before_properties = recovery_managed_properties_snapshot(target)
    before_source = mesh_fingerprint(source)
    before_objects = {obj.as_pointer() for obj in bpy.data.objects}
    before_curves = {curve.as_pointer() for curve in bpy.data.curves}
    before_meshes = {mesh.as_pointer() for mesh in bpy.data.meshes}

    result = bpy.ops.character_designer.recover_applied_curve()
    if result != {"CANCELLED"}:
        raise AssertionError("Recovery overwrote an artist-added Modifier")
    targets = recovered_curves(source)
    if len(targets) != 1 or targets[0].as_pointer() != target_pointer:
        raise AssertionError("Rejected artist modifier recovery replaced its output Object")
    target = targets[0]
    if target.data is not target_data:
        raise AssertionError("Rejected artist modifier recovery replaced Curve Data")
    if supported_modifier_stack_snapshot(target) != before_modifier_stack:
        raise AssertionError("Rejected recovery changed the artist-edited modifier stack")
    retained_extra = target.modifiers.get("Artist Extra Mirror")
    if retained_extra is None or retained_extra.as_pointer() != extra_pointer:
        raise AssertionError("Rejected recovery removed or replaced the artist Modifier")
    if recovery_managed_properties_snapshot(target) != before_properties:
        raise AssertionError("Rejected artist modifier recovery changed managed properties")
    if bpy.context.edit_object is not source or mesh_fingerprint(source) != before_source:
        raise AssertionError("Rejected artist modifier recovery changed source Edit selection")
    if {obj.as_pointer() for obj in bpy.data.objects} != before_objects:
        raise AssertionError("Rejected artist modifier recovery changed Object datablocks")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curves:
        raise AssertionError("Rejected artist modifier recovery changed Curve datablocks")
    if {mesh.as_pointer() for mesh in bpy.data.meshes} != before_meshes:
        raise AssertionError("Rejected artist modifier recovery changed Mesh datablocks")
    if state.last_level != "INFO" or "modifier stack was edited" not in state.last_message:
        raise AssertionError("Artist modifier refusal was not an ordinary informative cancel")


def test_batch_failure_rolls_back_prior_update_and_partial_create():
    reset_scene()
    first, _points = make_half_round_curve("RollbackA", x_offset=-0.8)
    first_source = curve_to_mesh_object(first, "RollbackSource")
    select_all_mesh(first_source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Rollback fixture setup failed")
    existing = recovered_curves(first_source)[0]
    old_data = existing.data
    old_points = tuple(point.co.copy() for point in old_data.splines[0].points)
    old_matrix = existing.matrix_world.copy()
    old_properties = tuple(
        (key, key in existing, existing.get(key))
        for key in character_designer.RECOVERY_MANAGED_KEYS
    )

    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    second, _points = make_half_round_curve("RollbackB", x_offset=1.0)
    second_mesh = curve_to_mesh_object(second, "RollbackSecond")
    source = join_mesh_objects((first_source, second_mesh), "RollbackSource")
    select_all_mesh(source)
    bm = bmesh.from_edit_mesh(source.data)
    bm.verts.ensure_lookup_table()
    first_component = min(
        character_designer._vertex_components(
            {vertex.index for vertex in bm.verts if vertex.select},
            character_designer._selected_edge_keys(
                bm,
                {vertex.index for vertex in bm.verts if vertex.select},
            ),
        ),
        key=lambda component: min(component),
    )
    for index in first_component:
        bm.verts[index].co.x += 0.04
    bmesh.update_edit_mesh(source.data, loop_triangles=False, destructive=False)
    source.matrix_world.translation.x += 0.2
    before_selection = selection_snapshot(source)
    before_object_pointers = {obj.as_pointer() for obj in bpy.data.objects}
    before_curve_pointers = {curve.as_pointer() for curve in bpy.data.curves}
    state = bpy.context.window_manager.character_designer
    state.recovery_curve_mode = character_designer.RECOVERY_CURVE_MODE_BEZIER
    state.recovery_control_points = 3

    original_apply = character_designer._apply_recovered_curve_plan
    calls = []

    def fail_after_second_write(context, plan):
        result = original_apply(context, plan)
        calls.append(result)
        if len(calls) == 2:
            raise character_designer.CenterlineError("Injected post-write failure")
        return result

    character_designer._apply_recovered_curve_plan = fail_after_second_write
    try:
        result = bpy.ops.character_designer.recover_applied_curve()
    finally:
        character_designer._apply_recovered_curve_plan = original_apply
    if result != {"CANCELLED"}:
        raise AssertionError("Injected transaction failure did not cancel")
    if existing.data is not old_data:
        raise AssertionError("Prior updated Curve data was not restored")
    for actual, expected in zip(existing.data.splines[0].points, old_points):
        assert_vector_close(actual.co, expected)
    for row in range(4):
        for column in range(4):
            assert_close(
                existing.matrix_world[row][column],
                old_matrix[row][column],
                tolerance=1.0e-9,
                message="Rollback did not restore the recovery Object matrix",
            )
    if tuple(
        (key, key in existing, existing.get(key))
        for key in character_designer.RECOVERY_MANAGED_KEYS
    ) != old_properties:
        raise AssertionError("Rollback did not restore all managed Object properties")
    if bpy.context.edit_object is not source or selection_snapshot(source) != before_selection:
        raise AssertionError("Failed recovery changed Mesh Edit Mode or selection")
    if {obj.as_pointer() for obj in bpy.data.objects} != before_object_pointers:
        raise AssertionError("Rollback left behind or removed an Object datablock")
    if {curve.as_pointer() for curve in bpy.data.curves} != before_curve_pointers:
        raise AssertionError("Rollback left behind or removed a Curve datablock")
    if len(recovered_curves(source)) != 1:
        raise AssertionError("Partially created recovery object survived rollback")


def test_reused_source_name_never_overwrites_another_recovery():
    reset_scene()
    original, _points = make_half_round_curve("IdentityOriginal", x_offset=-0.7)
    first_source = curve_to_mesh_object(original, "AppliedHair")
    select_all_mesh(first_source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("First identity recovery failed")
    first_target = recovered_curves(first_source)[0]
    first_target_pointer = first_target.as_pointer()
    first_data_pointer = first_target.data.as_pointer()
    first_cloud = evaluated_vertex_cloud(first_target)

    bpy.ops.object.mode_set(mode="OBJECT")
    first_source.name = "RetiredAppliedHair"
    second_original, _points = make_half_round_curve("ReplacementOriginal", x_offset=1.4)
    second_source = curve_to_mesh_object(second_original, "AppliedHair")
    select_all_mesh(second_source)
    second_selection = selection_snapshot(second_source)
    second_cloud = evaluated_vertex_cloud(second_source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Replacement source recovery failed")
    if selection_snapshot(second_source) != second_selection or bpy.context.edit_object is not second_source:
        raise AssertionError("Replacement recovery changed Mesh Edit Mode or selection")
    second_curves = recovered_curves(second_source)
    if len(second_curves) != 1 or second_curves[0] is first_target:
        raise AssertionError("A reused source name silently reused the old recovery target")
    if second_curves[0].get(character_designer.RECOVERY_SIGNATURE_KEY) != first_target.get(
        character_designer.RECOVERY_SIGNATURE_KEY
    ):
        raise AssertionError("Identity fixture did not reproduce the same-signature collision")
    if first_target.as_pointer() != first_target_pointer or first_target.data.as_pointer() != first_data_pointer:
        raise AssertionError("Recovering the replacement source overwrote the retired source output")
    if evaluated_vertex_cloud(first_target) != first_cloud:
        raise AssertionError("The retired source output geometry changed")
    assert_vertex_clouds_equivalent(evaluated_vertex_cloud(second_curves[0]), second_cloud)

    select_all_mesh(first_source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Renamed original source could not refresh its existing output")
    if len(recovered_curves(first_source)) != 1:
        raise AssertionError("Renamed original source created a duplicate output")
    if recovered_curves(first_source)[0].as_pointer() != first_target_pointer:
        raise AssertionError("Renamed source no longer resolved by stable Object identity")
    all_recovered = tuple(
        obj
        for obj in bpy.context.scene.objects
        if obj.get("character_designer_generator")
        == character_designer.RECOVERY_GENERATOR_ID
    )
    if len(all_recovered) != 2:
        raise AssertionError("Source rename/name reuse produced the wrong output count")


def test_two_updated_targets_sharing_curve_data_commit_safely():
    reset_scene()
    first, _points = make_half_round_curve("SharedA", x_offset=-0.8)
    second, _points = make_half_round_curve("SharedB", x_offset=0.9)
    source = join_mesh_objects(
        (
            curve_to_mesh_object(first, "SharedMeshA"),
            curve_to_mesh_object(second, "SharedMeshB"),
        ),
        "SharedSource",
    )
    select_all_mesh(source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Shared-data fixture recovery failed")
    targets = recovered_curves(source)
    if len(targets) != 2:
        raise AssertionError("Shared-data fixture did not create two outputs")
    target_pointers = {target.as_pointer() for target in targets}

    bpy.ops.object.mode_set(mode="OBJECT")
    discarded_data = targets[1].data
    shared_data = targets[0].data
    shared_data_name = shared_data.name
    targets[1].data = shared_data
    if discarded_data.users == 0:
        bpy.data.curves.remove(discarded_data)
    select_all_mesh(source)
    before_selection = selection_snapshot(source)
    bm = bmesh.from_edit_mesh(source.data)
    bm.verts.ensure_lookup_table()
    selected = {vertex.index for vertex in bm.verts if vertex.select}
    components = character_designer._vertex_components(
        selected,
        character_designer._selected_edge_keys(bm, selected),
    )
    if len(components) != 2:
        raise AssertionError("Shared-data fixture lost its two components")
    for component_index, component in enumerate(sorted(components, key=lambda value: min(value))):
        for index in component:
            bm.verts[index].co.x += 0.025 * (component_index + 1)
    bmesh.update_edit_mesh(source.data, loop_triangles=False, destructive=False)
    before_selection = selection_snapshot(source)

    result = bpy.ops.character_designer.recover_applied_curve()
    if result != {"FINISHED"}:
        raise AssertionError("Two targets sharing Curve data did not commit safely")
    if bpy.context.edit_object is not source or selection_snapshot(source) != before_selection:
        raise AssertionError("Shared-data update changed source mode or selection")
    updated = recovered_curves(source)
    if {target.as_pointer() for target in updated} != target_pointers:
        raise AssertionError("Shared-data update replaced recovery Objects")
    if updated[0].data is updated[1].data:
        raise AssertionError("Both updated outputs still share one Curve datablock")
    if bpy.data.curves.get(shared_data_name) is not None:
        raise AssertionError("The shared zero-user Curve datablock was not cleaned exactly once")


def test_invalid_unrelated_recovery_does_not_block_component_refresh():
    reset_scene()
    first, _points = make_half_round_curve("CorruptA", x_offset=-0.8)
    second, _points = make_half_round_curve("CorruptB", x_offset=0.9)
    source = join_mesh_objects(
        (
            curve_to_mesh_object(first, "CorruptMeshA"),
            curve_to_mesh_object(second, "CorruptMeshB"),
        ),
        "CorruptSource",
    )
    select_all_mesh(source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Unrelated-corruption fixture recovery failed")
    targets = recovered_curves(source)
    bm = bmesh.from_edit_mesh(source.data)
    bm.verts.ensure_lookup_table()
    selected = {vertex.index for vertex in bm.verts if vertex.select}
    components = sorted(
        character_designer._vertex_components(
            selected,
            character_designer._selected_edge_keys(bm, selected),
        ),
        key=lambda value: min(value),
    )
    target_by_component = {}
    for component in components:
        for target in targets:
            stored = {
                index
                for layer in json.loads(target["character_designer_layer_vertices"])
                for index in layer
            }
            if stored == set(component):
                target_by_component[min(component)] = target
                break
    if len(target_by_component) != 2:
        raise AssertionError("Could not map corrupt fixture outputs to source components")
    corrupt_target = target_by_component[min(target_by_component)]
    refresh_target = target_by_component[max(target_by_component)]
    corrupt_target["character_designer_cross_sections"] = "{broken recovery metadata"
    if character_designer._is_recovered_curve(corrupt_target):
        raise AssertionError("The deliberately corrupted recovery was still considered valid")
    corrupt_object_pointer = corrupt_target.as_pointer()
    corrupt_data_pointer = corrupt_target.data.as_pointer()
    corrupt_point_count = len(corrupt_target.data.splines[0].points)
    corrupt_properties = tuple(
        (key, corrupt_target.get(key)) for key in character_designer.RECOVERY_MANAGED_KEYS
    )
    refresh_object_pointer = refresh_target.as_pointer()
    refresh_data_pointer = refresh_target.data.as_pointer()

    bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(source.data)
    bm.verts.ensure_lookup_table()
    refresh_component = components[-1]
    for index in refresh_component:
        bm.verts[index].co.x += 0.04
        bm.verts[index].select_set(True)
    bmesh.update_edit_mesh(source.data, loop_triangles=False, destructive=False)
    before_selection = selection_snapshot(source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("An unrelated corrupt output blocked a valid component refresh")
    if bpy.context.edit_object is not source or selection_snapshot(source) != before_selection:
        raise AssertionError("Independent refresh changed source mode or exact selection")
    if (
        corrupt_target.as_pointer() != corrupt_object_pointer
        or corrupt_target.data.as_pointer() != corrupt_data_pointer
        or len(corrupt_target.data.splines[0].points) != corrupt_point_count
        or tuple(
            (key, corrupt_target.get(key))
            for key in character_designer.RECOVERY_MANAGED_KEYS
        )
        != corrupt_properties
    ):
        raise AssertionError("Refreshing one component modified the unrelated corrupt output")
    if refresh_target.as_pointer() != refresh_object_pointer:
        raise AssertionError("Independent refresh replaced its recovery Object")
    if refresh_target.data.as_pointer() == refresh_data_pointer:
        raise AssertionError("Independent refresh was incorrectly reported unchanged")
    if len(recovered_curves(source)) != 2:
        raise AssertionError("Independent refresh created a duplicate output")


def test_repeat_repairs_every_managed_curve_setting():
    reset_scene()
    original, _points = make_half_round_curve("ManagedOriginal")
    source = curve_to_mesh_object(original, "ManagedSource")
    select_all_mesh(source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Managed-setting fixture recovery failed")
    target = recovered_curves(source)[0]
    target_pointer = target.as_pointer()

    taper_data = bpy.data.curves.new("RecoveryTaper", "CURVE")
    taper_spline = taper_data.splines.new("POLY")
    taper_spline.points.add(1)
    taper_object = bpy.data.objects.new("RecoveryTaper", taper_data)
    bpy.context.scene.collection.objects.link(taper_object)

    mutations = (
        (
            "dimensions",
            lambda data: setattr(data, "dimensions", "2D"),
            lambda data: data.dimensions == "3D",
        ),
        (
            "resolution_u",
            lambda data: setattr(data, "resolution_u", 7),
            lambda data: int(data.resolution_u) == 1,
        ),
        (
            "render_resolution_u",
            lambda data: setattr(data, "render_resolution_u", 9),
            lambda data: int(data.render_resolution_u) == 1,
        ),
        (
            "twist_mode",
            lambda data: setattr(data, "twist_mode", "Z_UP"),
            lambda data: data.twist_mode == "MINIMUM",
        ),
        (
            "twist_smooth",
            lambda data: setattr(data, "twist_smooth", 0.5),
            lambda data: abs(float(data.twist_smooth)) <= 1.0e-6,
        ),
        (
            "use_fill_caps",
            lambda data: setattr(data, "use_fill_caps", True),
            lambda data: not data.use_fill_caps,
        ),
        (
            "taper_object",
            lambda data: setattr(data, "taper_object", taper_object),
            lambda data: data.taper_object is None,
        ),
        (
            "use_cyclic_u",
            lambda data: setattr(data.splines[0], "use_cyclic_u", True),
            lambda data: not data.splines[0].use_cyclic_u,
        ),
        (
            "point_co_w",
            lambda data: setattr(data.splines[0].points[0].co, "w", 0.4),
            lambda data: abs(float(data.splines[0].points[0].co.w) - 1.0) <= 1.0e-6,
        ),
    )
    for label, mutate, repaired in mutations:
        old_data_pointer = target.data.as_pointer()
        mutate(target.data)
        before_selection = selection_snapshot(source)
        if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
            raise AssertionError(f"Repairing managed field {label} failed")
        if target.as_pointer() != target_pointer:
            raise AssertionError(f"Repairing {label} replaced the Curve Object")
        if target.data.as_pointer() == old_data_pointer:
            raise AssertionError(f"Managed field {label} was falsely reported unchanged")
        if not repaired(target.data):
            raise AssertionError(f"Managed field {label} was not restored")
        if bpy.context.edit_object is not source or selection_snapshot(source) != before_selection:
            raise AssertionError(f"Repairing {label} changed source mode or selection")

    reset_scene()
    rectangle = make_rectangle_curve("ManagedRectangleOriginal")
    rectangle_source = curve_to_mesh_object(rectangle, "ManagedRectangleSource")
    select_all_mesh(rectangle_source)
    if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
        raise AssertionError("Managed rectangle fixture recovery failed")
    rectangle_target = recovered_curves(rectangle_source)[0]
    rectangle_pointer = rectangle_target.as_pointer()
    profile_mutations = (
        (
            "first endpoint",
            lambda profile: setattr(profile.points[0], "location", (0.8, 0.0)),
        ),
        (
            "corner position",
            lambda profile: setattr(profile.points[1], "location", (0.9, 1.0)),
        ),
        (
            "last endpoint",
            lambda profile: setattr(profile.points[2], "location", (0.0, 0.8)),
        ),
        (
            "corner incoming handle",
            lambda profile: setattr(profile.points[1], "handle_type_1", "AUTO"),
        ),
        (
            "corner outgoing handle",
            lambda profile: setattr(profile.points[1], "handle_type_2", "AUTO"),
        ),
        (
            "extra point",
            lambda profile: profile.points.add(0.5, 0.5),
        ),
    )
    for label, mutate in profile_mutations:
        old_data_pointer = rectangle_target.data.as_pointer()
        mutate(rectangle_target.data.bevel_profile)
        if bpy.ops.character_designer.recover_applied_curve() != {"FINISHED"}:
            raise AssertionError(f"Repairing rectangle Profile {label} failed")
        if rectangle_target.as_pointer() != rectangle_pointer:
            raise AssertionError(f"Repairing Profile {label} replaced its Curve Object")
        if rectangle_target.data.as_pointer() == old_data_pointer:
            raise AssertionError(f"Damaged Profile {label} was falsely reported unchanged")
        if not character_designer._curve_profile_matches_rectangle(rectangle_target.data):
            raise AssertionError(f"Rectangle Profile {label} was not restored canonically")


def main():
    character_designer.register()
    tests = (
        test_half_round_extrude_offset_recovers_equivalent_editable_curve,
        test_full_round_capsule_recovers_equivalent_editable_curve,
        test_supported_modifier_stacks_preserve_order_profiles_and_evaluation,
        test_supported_modifier_preview_is_gpu_only_and_describes_preserved_stack,
        test_replace_mesh_preserves_supported_stack_and_base_mesh_datablock,
        test_bezier_recovery_controls_have_bounded_defaults,
        test_recovery_preview_is_gpu_only_and_tracks_parameters,
        test_recovery_preview_partial_replace_clears_and_add_recovers,
        test_aligned_handle_geometry_is_explicit_and_stable,
        test_bezier_profile_resampling_uses_uniform_arc_length,
        test_bezier_count_updates_in_place_and_exact_remains_available,
        test_legacy_exact_recovery_upgrades_to_bezier_in_place,
        test_exact_mode_is_not_capped_by_bezier_point_limit,
        test_two_disconnected_strands_are_created_and_reused_independently,
        test_closed_rectangle_profile_recovers_without_helper_object,
        test_selected_face_band_stops_at_its_exact_range,
        test_longitudinal_guide_edge_path_expands_to_complete_sections,
        test_add_mode_is_default_and_preserves_source_edit_context,
        test_replace_mesh_removes_only_source_object_and_selects_result,
        test_replace_mesh_supports_two_disconnected_strands,
        test_partial_selection_replace_is_rejected_without_writes,
        test_unsupported_modifier_is_rejected_without_writes,
        test_replace_rejects_recovery_output_in_another_scene,
        test_replace_failure_before_delete_rolls_back_every_write,
        test_modifier_update_property_failure_rolls_back_every_write,
        test_artist_added_modifier_cancels_without_overwriting_output,
        test_batch_failure_rolls_back_prior_update_and_partial_create,
        test_reused_source_name_never_overwrites_another_recovery,
        test_two_updated_targets_sharing_curve_data_commit_safely,
        test_invalid_unrelated_recovery_does_not_block_component_refresh,
        test_repeat_repairs_every_managed_curve_setting,
    )
    failures = []
    try:
        for test in tests:
            try:
                test()
                print(f"PASS {test.__name__}")
            except Exception:
                failures.append(test.__name__)
                print(f"FAIL {test.__name__}")
                traceback.print_exc()
    finally:
        character_designer.unregister()
    if failures:
        raise SystemExit(f"{len(failures)} recovery test(s) failed: {', '.join(failures)}")
    print(f"All {len(tests)} applied-hair recovery tests passed.")


if __name__ == "__main__":
    main()
