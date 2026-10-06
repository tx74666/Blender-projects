"""Private-QA-only final Dress point clearance experiment; not production/export.

install_preview(source, rig, record, margin_m=.002, passes=3) appends one GN
modifier AFTER the existing Subsurf.  It samples the actual three owned fitted
pelvis/thigh meshes; it never infers capsules, changes raw mesh/Keys/weights,
copies Actions, installs Cloth, advances time, or registers handlers.

Each pass projects free final vertices sequentially against three near-convex
meshes, subject to a reported physical micro-budget; not exact hull convexity.
Proximity supplies the nearest surface point. A short ray to that point supplies
the native triangle normal, avoiding interpolated normals for deep penetration.
Only the numerical near-surface case may use a sampled normal if the ray misses.
Finite passes do NOT guarantee separation from their overlapping union, nor
triangle separation, Body clearance, acceptable shape, or simulation acceptance.
The QA must measure those independently after every tested pose/manual edit.

Sockets are based on Blender v5.1.0 source declarations (links in report). This
file has only been AST-checked; no native node construction/effect claim follows.
Unknown interfaces reject and remove only this call's owned partial artifacts.
Canonical validation/export are deliberately NOT taught about this prototype:
remove_preview(handle) BEFORE invoking canonical Reset/Tuning/export or saving
an artist file. The candidate remains isolated under this Validation directory.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import uuid

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
MARKER = "character_designer_QA_final_clearance"
SPEC_VERSION = 1
INTERFACE_SOURCES = [
    "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/nodes/geometry/nodes/node_geo_proximity.cc",
    "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/nodes/geometry/nodes/node_geo_raycast.cc",
    "https://raw.githubusercontent.com/blender/blender/v5.1.0/source/blender/nodes/geometry/nodes/node_geo_sample_nearest_surface.cc",
]


def _require(condition, message):
    if not condition:
        raise ValueError("Private final-clearance prototype: " + message)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                   allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def _matrix(value):
    return [[float(number) for number in row] for row in value]


def _private_scene():
    path = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    _require(bpy.app.background and path is not None and path.is_relative_to(ROOT)
             and path.suffix.lower() == ".blend" and path.name.startswith("Cosha_Dress_QA"),
             "save/open a dedicated Cosha_Dress_QA*.blend inside this Validation directory first; artist/UI use refused")
    _require(not any(obj.mode == "EDIT" for obj in bpy.context.scene.objects), "finish QA Edit Mode first")
    return str(path)


def _conformal(matrix):
    _require(all(math.isfinite(value) for row in matrix for value in row), "nonfinite source world transform")
    linear = matrix.to_3x3()
    lengths = [column.length for column in linear.col]
    scale = sum(lengths) / 3.
    _require(scale > 1.e-10 and linear.determinant() > 0., "source world transform must have positive nonzero orientation")
    _require(max(abs(value - scale) for value in lengths) <= scale * 1.e-6
             and all(abs(linear.col[a].dot(linear.col[b])) <= scale * scale * 1.e-6
                     for a, b in ((0, 1), (0, 2), (1, 2))),
             "source world transform must be uniform and orthogonal; no guessed margin under shear/nonuniform scale")
    return scale


def _convex(points, triangles, label, *, metres_per_unit_upper_bound, support_cap_m):
    # These exact stored Float32 coordinates are promoted before every operation.
    # mathutils Vector cross/normal/dot would round the proof back to Float32.
    values = [tuple(float(value) for value in point) for point in points]
    _require(len(values) >= 4 and triangles and all(len(point) == 3 and all(math.isfinite(x) for x in point)
             for point in values), label + " lacks finite geometry")

    def subtract(first, second):
        return tuple(a - b for a, b in zip(first, second))

    def cross(first, second):
        return (first[1] * second[2] - first[2] * second[1],
                first[2] * second[0] - first[0] * second[2],
                first[0] * second[1] - first[1] * second[0])

    def dot(first, second):
        return math.fsum(a * b for a, b in zip(first, second))

    def length(value):
        return math.sqrt(dot(value, value))

    def ulp32(value):
        absolute = abs(value)
        return math.ldexp(1., -149 if absolute < math.ldexp(1., -126) else math.frexp(absolute)[1] - 24)

    center = tuple(math.fsum(point[axis] for point in values) / len(values) for axis in range(3))
    diameter = max(length(subtract(point, center)) for point in values) * 2.
    # This shape-scale threshold only diagnoses degenerate faces/winding. It is
    # not the convex support allowance or the independent affine proof guard.
    epsilon = max(1.e-10, diameter * 1.e-7)
    _require(diameter > epsilon * 100., label + " is degenerate")
    _require(math.isfinite(metres_per_unit_upper_bound) and metres_per_unit_upper_bound > 0.
             and math.isfinite(support_cap_m) and 0. < support_cap_m <= 1.e-6,
             label + " has no explicit conservative physical micro-budget")
    cap = math.nextafter(support_cap_m / metres_per_unit_upper_bound, 0.)
    absolute_maximum = max(abs(value) for point in values for value in point)
    arithmetic = max(128. * max(math.ulp(value) for point in values for value in point), diameter * 2.e-14, 1.e-30)
    _require(arithmetic < cap / 32., label + " Python-double arithmetic cannot resolve the physical micro-budget")
    # A nearest Float32 storage step has at most half an ULP per coordinate.
    # The support-plane error includes both point error and face-normal error.
    # This is a rounding envelope, not evidence that an arbitrary fitted mesh
    # was once a particular ideal ellipsoid or an exact convex hull.
    radii = [.5 * length(tuple(ulp32(value) for value in point)) for point in values]
    maximum_ulp32 = max(ulp32(value) for point in values for value in point)
    _require(max(radii) < cap, label + " Float32 coordinate resolution exceeds the micro-budget: "
             + json.dumps({"maximum_absolute_coordinate_units": absolute_maximum,
                           "maximum_coordinate_ulp32_units": maximum_ulp32,
                           "maximum_half_ulp_point_radius_units": max(radii), "cap_units": cap}))
    volumes = []
    maximum = maximum_excess = -math.inf
    minimum_cross = math.inf
    worst_plane = worst_excess = None
    for triangle_index, triangle in enumerate(triangles):
        _require(len(triangle) == 3 and len(set(triangle)) == 3
                 and all(type(index) is int and 0 <= index < len(values) for index in triangle),
                 label + " has an invalid triangle")
        ai, bi, ci = triangle
        a, b, c = (values[index] for index in triangle)
        first, second = subtract(b, a), subtract(c, a)
        product = cross(first, second)
        area = length(product)
        minimum_cross = min(minimum_cross, area)
        _require(math.isfinite(area) and area > epsilon * epsilon, label + " has a degenerate native face triangle: "
                 + json.dumps({"triangle": triangle_index, "indices": triangle, "cross_units2": area, "epsilon_units": epsilon}))
        first_error, second_error = radii[bi] + radii[ai], radii[ci] + radii[ai]
        cross_error = length(first) * second_error + length(second) * first_error + first_error * second_error
        _require(area > cross_error * 2., label + " native face normal is unresolved at Float32 precision: "
                 + json.dumps({"triangle": triangle_index, "cross_units2": area, "cross_error_bound_units2": cross_error}))
        normal = tuple(value / area for value in product)
        normal_error = 2. * cross_error / (area - cross_error)
        inward = dot(subtract(center, a), normal)
        winding_guard = max(epsilon, radii[ai] + max(radii) + diameter * normal_error + arithmetic)
        _require(inward < -winding_guard, label + " has inward/ambiguous native winding: "
                 + json.dumps({"triangle": triangle_index, "center_plane_units": inward, "winding_guard_units": winding_guard}))
        for point_index, point in enumerate(values):
            difference = subtract(point, a)
            distance = dot(difference, normal)
            envelope = radii[point_index] + radii[ai] + length(difference) * normal_error + arithmetic
            allowed = min(cap, envelope)
            witness = {"triangle": triangle_index, "indices": list(triangle), "point": point_index,
                       "support_plane_violation_units": distance, "float32_rounding_envelope_units": envelope,
                       "allowed_support_violation_units": allowed, "normal_error_bound": normal_error,
                       "point_coordinates": list(point), "triangle_coordinates": [list(a), list(b), list(c)]}
            if distance > maximum:
                maximum, worst_plane = distance, witness
            if distance - allowed > maximum_excess:
                maximum_excess, worst_excess = distance - allowed, witness
        volumes.append(dot(subtract(a, center), cross(subtract(b, center), subtract(c, center))) / 6.)
    volume = math.fsum(volumes)
    _require(math.isfinite(volume) and volume > epsilon ** 3, label + " has no positive closed volume")
    geometry = {"points": [list(point) for point in values], "triangles": [list(triangle) for triangle in triangles]}
    diagnostic = {"vertices": len(values), "triangles": len(triangles), "positive_volume_units3": volume,
        "maximum_support_plane_violation_units": maximum, "epsilon_units": epsilon,
        "minimum_triangle_cross_length_units2": minimum_cross, "coords_triangles_sha256": _digest(geometry),
        "proof_arithmetic": "Python double cross/normal and math.fsum dot/centroid/volume from exact stored Float32 coordinates",
        "maximum_absolute_coordinate_units": absolute_maximum, "maximum_coordinate_ulp32_units": maximum_ulp32,
        "python_double_arithmetic_budget_units": arithmetic, "maximum_allowed_support_deviation_units": cap,
        "metres_per_input_unit_upper_bound": metres_per_unit_upper_bound, "maximum_allowed_support_deviation_m": support_cap_m,
        "maximum_positive_support_deviation_m_upper_bound": max(0., maximum) * metres_per_unit_upper_bound,
        "maximum_excess_over_bounded_rounding_envelope_units": maximum_excess,
        "worst_support_plane": worst_plane, "worst_envelope_excess": worst_excess,
        "convexity_scope": "Numerically near-convex: support deviations fit each triangle's final nearest-Float32 storage envelope AND the explicit physical micro-cap; not exact hull/Body separation",
        "rounding_limit": "This storage-step envelope is not a bound/proof for the multi-operation ellipsoid generator, nor evidence that Float32 caused any measured deviation",
        "physical_unit_contract": "Raw-rig metres/unit uses the exact evaluated single-bone affine's conservative operator-norm upper bound; evaluated-world metres/unit uses scene scale"}
    _require(maximum_excess <= 0., label + " exceeds the bounded Float32 convexity envelope; fitted geometry is preserved: "
             + json.dumps({**diagnostic, "input_geometry": geometry}, ensure_ascii=False, allow_nan=False))
    return diagnostic


def _collider_proof(obj, source, rig, record, physics, graph, margin_m):
    physics._owned_mesh(obj, source, record)
    physics._closed_collider(obj)  # Native closed/connected/winding preflight, not a convexity proof.
    groups = physics._weights(obj)
    _require(len(groups) == 1, obj.name + " needs one complete deform-bone group")
    bone = next(iter(groups))
    _require(groups == {bone: {index: 1. for index in range(len(obj.data.vertices))}}, obj.name + " weights are not exactly one-bone")
    physics._binding(obj, rig, bone, ["ARMATURE", "COLLISION"])
    physics._relative_frame(obj, Matrix.Identity(4))
    _require(rig.data.pose_position == "POSE" and rig.data.bones[bone].use_deform
             and rig.data.bones[bone].bbone_segments == 1
             and not obj.modifiers[0].use_deform_preserve_volume, obj.name + " has no proven affine one-bone deformation")
    solved = rig.evaluated_get(graph)
    affine = solved.matrix_world @ solved.pose.bones[bone].matrix @ rig.data.bones[bone].matrix_local.inverted()
    _require(all(math.isfinite(value) for row in affine for value in row) and affine.to_3x3().determinant() > 0.,
             obj.name + " deform has nonfinite/reflected/singular transform")
    metres = float(bpy.context.scene.unit_settings.scale_length)
    _require(math.isfinite(metres) and metres > 0. and math.isfinite(margin_m) and margin_m > 0.,
             obj.name + " has no proved physical margin")
    # Frobenius >= spectral/operator norm: raw-space support errors cannot be
    # enlarged beyond the stated physical cap by an affine scale or shear.
    affine_norm_upper = math.nextafter(math.sqrt(math.nextafter(
        math.fsum(float(affine[row][column]) ** 2 for row in range(3) for column in range(3)), math.inf)), math.inf)
    _require(math.isfinite(affine_norm_upper) and affine_norm_upper > 0., obj.name + " affine norm is invalid")
    support_cap_m = min(1.e-6, margin_m * .001)
    obj.data.calc_loop_triangles()  # Derived tessellation only; no raw-coordinate/topology writes.
    raw_points = [vertex.co.copy() for vertex in obj.data.vertices]
    raw_triangles = [list(triangle.vertices) for triangle in obj.data.loop_triangles]
    raw = _convex(raw_points, raw_triangles, obj.name + " raw fitted mesh",
                  metres_per_unit_upper_bound=metres * affine_norm_upper, support_cap_m=support_cap_m)
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    try:
        mesh.calc_loop_triangles()
        world = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        triangles = [list(triangle.vertices) for triangle in mesh.loop_triangles]
        _require(triangles == raw_triangles, obj.name + " native topology changed")
        native = _convex(world, triangles, obj.name + " evaluated world mesh",
                         metres_per_unit_upper_bound=metres, support_cap_m=support_cap_m)
        expected_world = [affine @ old for old in raw_points]
        error = max(math.sqrt(math.fsum((float(a) - float(b)) ** 2 for a, b in zip(point, expected)))
                    for point, expected in zip(world, expected_world))
        affine_guard_m = 1.e-6  # Separate fixed physical guard, never convex-epsilon * N.
        _require(len(world) == len(raw_points) and error * metres <= affine_guard_m,
                 obj.name + " native deformation is not the proved affine one-bone transform")
        return {"object": obj.name, "mesh": obj.data.name, "bone": bone,
                "shape": "actual fitted closed native mesh; near-convex within the explicit micro-budget, not an inferred capsule or exact convex hull",
                "raw": raw, "evaluated_world": native, "evaluated_object_matrix_world": _matrix(evaluated.matrix_world),
                "evaluated_bone_affine_world": _matrix(affine), "affine_error_world_units": error,
                "affine_error_m": error * metres, "affine_guard_m": affine_guard_m,
                "raw_affine_operator_norm_upper_bound_world_per_raw_unit": affine_norm_upper,
                "support_cap_m": support_cap_m, "support_cap_to_margin_ratio": support_cap_m / margin_m,
                "collision_RNA": {name: float(getattr(obj.collision, name)) for name in
                                  ("thickness_outer", "thickness_inner", "damping")}}
    finally:
        evaluated.to_mesh_clear()


def _artist_signature(source, rig, surface):
    keys = source.data.shape_keys
    return _digest({"source_data_pointer": source.data.as_pointer(), "coords": [list(v.co) for v in source.data.vertices],
        "topology": surface._topology(source.data), "groups": surface._groups(source),
        "uv": [{"name": layer.name, "values": [list(item.uv) for item in layer.data]} for layer in source.data.uv_layers],
        "keys": None if keys is None else {"pointer": keys.as_pointer(), "relative": keys.use_relative,
          "blocks": [{"name": key.name, "value": key.value, "mute": key.mute, "relative": key.relative_key.name,
                      "coords": [list(point.co) for point in key.data]} for key in keys.key_blocks]},
        "rig_data_pointer": rig.data.as_pointer(), "rest": surface._rest(rig, set(rig.data.bones.keys())),
        "drivers": surface._drivers(rig), "record": source.get(surface.skirt.RECORD_KEY),
        "action_pointers": [owner.animation_data.action.as_pointer() if owner is not None and owner.animation_data
                            and owner.animation_data.action else None for owner in (source, source.data, keys, rig, rig.data)]})


def _socket(node, direction, key):
    sockets = getattr(node, direction)
    if isinstance(key, int):
        return sockets[key]
    matches = [socket for socket in sockets if (socket.name == key or socket.identifier == key)
               and not getattr(socket, "is_unavailable", False)]
    _require(len(matches) == 1, node.bl_idname + " has an unknown/ambiguous " + direction + " socket: " + key)
    return matches[0]


def _new(group, kind, name):
    node = group.nodes.new(kind)
    node.name = name
    _require(node.name == name, "node identity collision")
    return node


def _wire(group, output, node, key):
    group.links.new(output, _socket(node, "inputs", key))


def _vector(group, name, operation, first, second=None, scale=None):
    node = _new(group, "ShaderNodeVectorMath", name)
    node.operation = operation
    _wire(group, first, node, 0)
    if second is not None:
        _wire(group, second, node, 1)
    if scale is not None:
        _wire(group, scale, node, "Scale")
    return _socket(node, "outputs", "Value" if operation in {"DOT_PRODUCT", "LENGTH"} else "Vector")


def _math(group, name, operation, first, second):
    node = _new(group, "ShaderNodeMath", name)
    node.operation = operation
    for index, value in enumerate((first, second)):
        if isinstance(value, (float, int)):
            _socket(node, "inputs", index).default_value = value
        else:
            _wire(group, value, node, index)
    return _socket(node, "outputs", 0)


def _boolean(group, name, operation, first, second=None):
    node = _new(group, "FunctionNodeBooleanMath", name)
    node.operation = operation
    _wire(group, first, node, 0)
    if second is not None:
        _wire(group, second, node, 1)
    return _socket(node, "outputs", 0)


def _nearest(group, prefix, geometry, position, epsilon):
    proximity = _new(group, "GeometryNodeProximity", prefix + " Nearest")
    proximity.target_element = "FACES"
    _wire(group, geometry, proximity, "Target")
    _wire(group, position, proximity, "Source Position")
    closest = _socket(proximity, "outputs", "Position")
    delta = _vector(group, prefix + " Toward Surface", "SUBTRACT", closest, position)
    ray = _new(group, "GeometryNodeRaycast", prefix + " Native Face Normal")
    ray.data_type = "FLOAT"
    _wire(group, geometry, ray, "Target Geometry")
    _wire(group, position, ray, "Source Position")
    _wire(group, delta, ray, "Ray Direction")
    length = _math(group, prefix + " Ray Length", "ADD", _socket(proximity, "outputs", "Distance"), epsilon)
    _wire(group, length, ray, "Ray Length")
    normal_input = _new(group, "GeometryNodeInputNormal", prefix + " Normal Field")
    sample = _new(group, "GeometryNodeSampleNearestSurface", prefix + " Boundary Normal Only")
    sample.data_type = "FLOAT_VECTOR"
    _wire(group, geometry, sample, "Mesh")
    _wire(group, _socket(normal_input, "outputs", "Normal"), sample, "Value")
    _wire(group, closest, sample, "Sample Position")
    choice = _new(group, "GeometryNodeSwitch", prefix + " Ray Or Boundary Normal")
    choice.input_type = "VECTOR"
    _wire(group, _socket(ray, "outputs", "Is Hit"), choice, "Switch")
    _wire(group, _socket(sample, "outputs", "Value"), choice, "False")
    _wire(group, _socket(ray, "outputs", "Hit Normal"), choice, "True")
    normal = _vector(group, prefix + " Unit Normal", "NORMALIZE", _socket(choice, "outputs", "Output"))
    near = _math(group, prefix + " Boundary Epsilon", "LESS_THAN", _socket(proximity, "outputs", "Distance"), epsilon)
    boundary = _boolean(group, prefix + " Valid Boundary", "AND", near, _socket(sample, "outputs", "Is Valid"))
    normal_valid = _boolean(group, prefix + " Normal Lookup", "OR", _socket(ray, "outputs", "Is Hit"), boundary)
    nonzero = _math(group, prefix + " Nonzero Normal", "GREATER_THAN", _vector(group, prefix + " Normal Length", "LENGTH", normal), .5)
    valid = _boolean(group, prefix + " Finite Nonzero Lookup", "AND", normal_valid, nonzero)
    valid = _boolean(group, prefix + " Valid Surface Lookup", "AND", valid, _socket(proximity, "outputs", "Is Valid"))
    difference = _vector(group, prefix + " From Surface", "SUBTRACT", position, closest)
    signed = _vector(group, prefix + " Signed Plane Distance", "DOT_PRODUCT", difference, normal)
    return normal, signed, valid


def _fingerprint(group):
    def default(socket):
        value = getattr(socket, "default_value", None)
        if isinstance(value, bpy.types.ID):
            return {"type": value.bl_rna.identifier, "name": value.name_full}
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        try:
            return list(value)
        except TypeError:
            return str(value)
    content = {"interface": [(item.name, item.socket_type, item.in_out) for item in group.interface.items_tree
                               if item.item_type == "SOCKET"],
        "nodes": [{"name": node.name, "type": node.bl_idname, "mute": node.mute,
                   "settings": {key: getattr(node, key) for key in ("operation", "target_element", "data_type",
                                "transform_space", "domain", "input_type", "clamp") if hasattr(node, key)},
                   "inputs": [(socket.identifier, default(socket)) for socket in node.inputs]} for node in group.nodes],
        "links": [(link.from_node.name, link.from_socket.identifier, link.to_node.name, link.to_socket.identifier,
                   link.is_valid) for link in group.links]}
    return _digest(content), content


def _build(group, colliders, waist_name, margin_local, epsilon_local, passes, metres_per_local):
    group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    incoming = _new(group, "NodeGroupInput", "Input")
    outgoing = _new(group, "NodeGroupOutput", "Output")
    outgoing.is_active_output = True
    position = _socket(_new(group, "GeometryNodeInputPosition", "Current Final Position"), "outputs", "Position")
    weight = _new(group, "GeometryNodeInputNamedAttribute", "Native Waist Weight")
    weight.data_type = "FLOAT"
    _socket(weight, "inputs", "Name").default_value = waist_name
    free = _math(group, "Free Final Vertex", "LESS_THAN", _socket(weight, "outputs", "Attribute"), .999)
    free = _boolean(group, "Known Free Weight", "AND", free, _socket(weight, "outputs", "Exists"))
    targets = []
    for index, collider in enumerate(colliders):
        obj = _new(group, "GeometryNodeObjectInfo", "Actual Collider " + str(index))
        obj.transform_space = "RELATIVE"
        _socket(obj, "inputs", "Object").default_value = collider
        _socket(obj, "inputs", "As Instance").default_value = False
        targets.append(_socket(obj, "outputs", "Geometry"))
    geometry = _socket(incoming, "outputs", "Geometry")
    for iteration in range(passes):
        for index, target in enumerate(targets):
            prefix = "Pass " + str(iteration + 1) + " Collider " + str(index)
            normal, signed, valid = _nearest(group, prefix, target, position, epsilon_local)
            deficit = _math(group, prefix + " Margin Shortfall", "SUBTRACT", margin_local, signed)
            amount = _math(group, prefix + " Positive Correction", "MAXIMUM", deficit, 0.)
            offset = _vector(group, prefix + " Outward Offset", "SCALE", normal, scale=amount)
            selection = _boolean(group, prefix + " Known Free Projection", "AND", free, valid)
            step = _new(group, "GeometryNodeSetPosition", prefix + " Set Final Position")
            _wire(group, geometry, step, "Geometry")
            _wire(group, selection, step, "Selection")
            _wire(group, offset, step, "Offset")
            geometry = _socket(step, "outputs", "Geometry")
    attributes = []
    for index, target in enumerate(targets):
        prefix = "Final Residual Collider " + str(index)
        _normal, signed, valid = _nearest(group, prefix, target, position, epsilon_local)
        deficit = _math(group, prefix + " Shortfall", "SUBTRACT", margin_local, signed)
        deficit = _math(group, prefix + " Nonnegative", "MAXIMUM", deficit, 0.)
        deficit = _math(group, prefix + " Metres", "MULTIPLY", deficit, metres_per_local)
        invalid = _boolean(group, prefix + " Invalid Lookup", "NOT", valid)
        unknown_weight = _boolean(group, prefix + " Unknown Weights", "NOT", _socket(weight, "outputs", "Exists"))
        invalid = _boolean(group, prefix + " Invalid Free Lookup", "AND", invalid, free)
        invalid = _boolean(group, prefix + " Missing Proof", "OR", invalid, unknown_weight)
        for suffix, kind, value, selection in (("shortfall_m", "FLOAT", deficit, free),
                                                ("lookup_unproven", "BOOLEAN", invalid, None)):
            name = "QA final clearance collider " + str(index) + " " + suffix
            store = _new(group, "GeometryNodeStoreNamedAttribute", prefix + " " + suffix)
            store.data_type, store.domain = kind, "POINT"
            _socket(store, "inputs", "Name").default_value = name
            _wire(group, geometry, store, "Geometry")
            if selection is not None:
                _wire(group, selection, store, "Selection")
            _wire(group, value, store, "Value")
            geometry = _socket(store, "outputs", "Geometry")
            attributes.append({"name": name, "type": kind, "scope": "final evaluated free vertices; fixed waist excluded"})
    _wire(group, geometry, outgoing, "Geometry")
    _require(all(link.is_valid for link in group.links), "native GN link validation rejected the provisional interface")
    return attributes


def install_preview(source, rig, record, margin_m=.002, passes=3):
    """Install ONLY on a saved private candidate. Return opaque handle + plain report."""
    path = _private_scene()
    _require(type(passes) is int and 1 <= passes <= 8, "passes must be an integer in 1..8")
    _require(type(margin_m) in (int, float) and math.isfinite(margin_m) and margin_m > 0., "margin_m must be positive finite metres")
    from character_designer import skirt_surface as surface, skirt_physics as physics
    _require(source.type == "MESH" and source.get(surface.skirt.RIG_KEY) == rig, "exact owned source/rig required")
    surface.validate(source, rig, record)
    metadata = record["physics"]["surface"]
    _require(metadata["colliders"] and all(value.get("version") == 2 for value in metadata["colliders"].values()),
             "explicit fitted-collider V2 contract required")
    names = record["physics"]["colliders"][:-1]
    _require(len(names) == 3 and set(names) == set(metadata["colliders"]), "three exact owned pelvis/thigh colliders required")
    _require(any(mod.type == "SUBSURF" and mod.show_viewport and mod.show_render for mod in source.modifiers),
             "the final owned native Subsurf must be enabled in both outputs")
    _require(not any(group.get(MARKER) and group.get("source") == source for group in bpy.data.node_groups), "remove the previous exact prototype first")
    _require(not any(attribute.name.startswith("QA final clearance collider ") for attribute in source.data.attributes),
             "artist attributes already use prototype diagnostic names")
    graph = bpy.context.evaluated_depsgraph_get()
    scale = _conformal(source.evaluated_get(graph).matrix_world)
    metres = bpy.context.scene.unit_settings.scale_length
    _require(math.isfinite(metres) and metres > 0., "scene metres/unit is invalid")
    colliders = [bpy.data.objects[name] for name in names]
    proof = [_collider_proof(obj, source, rig, record, physics, graph, margin_m) for obj in colliders]
    before = _artist_signature(source, rig, surface)
    active_before = [(item, item.is_active) for item in source.modifiers]
    owner = uuid.uuid4().hex
    group = modifier = None
    try:
        group = bpy.data.node_groups.new("QA Final Dress Clearance", "GeometryNodeTree")
        group[MARKER], group["source"], group["rig"] = owner, source, rig
        margin_local = margin_m / (scale * metres)
        epsilon_local = max(1.e-9, min(margin_local * .001, 1.e-6 / (scale * metres)))
        attributes = _build(group, colliders, record["controls"]["waist"], margin_local, epsilon_local, passes, scale * metres)
        modifier = source.modifiers.new("QA Final Dress Clearance", "NODES")
        modifier.node_group = group
        modifier.show_viewport = modifier.show_render = True
        modifier.is_active = False
        for item, active in active_before:
            item.is_active = active
        _require(source.modifiers[-1] == modifier, "prototype modifier is not after every existing source modifier")
        fingerprint, nodes = _fingerprint(group)
        _require(_artist_signature(source, rig, surface) == before, "installation unexpectedly changed protected raw author data")
        report = {"prototype": "QA_FINAL_SURFACE_CONVEX_CLEARANCE", "version": SPEC_VERSION,
            "candidate": path, "runtime": bpy.app.version_string, "owner": owner, "source": source.name, "rig": rig.name,
            "modifier": modifier.name, "node_group": group.name, "node_sha256": fingerprint, "node_content": nodes,
            "passes": passes, "colliders_per_pass": 3, "margin_m": margin_m, "margin_source_units": margin_local,
            "normal_boundary_epsilon_source_units": epsilon_local, "metres_per_source_unit": scale * metres,
            "source_world_scale": scale, "scene_metres_per_unit": metres,
            "source_world_matrix": _matrix(source.evaluated_get(graph).matrix_world), "colliders": proof,
            "diagnostic_attributes": attributes, "artist_raw_unchanged_at_install": True,
            "selection": "native final Waist weight < .999 with an existing GN weight attribute; hard-fixed waist untouched",
            "mode": "prototype enabled independently of C overlay, in both Automatic and Manual output",
            "formula": "Pnext = P + n * max(0, margin - dot(P-q,n)); q exact nearest mesh surface, n native ray triangle normal except numerical boundary",
            "transform_contract": "positive uniform conformal source world transform; collider raw/native evaluated shapes proved outward/affine and near-convex within the reported micro-budget at this pose",
            "native_interface_status": "NATIVE_NODE_CONSTRUCTION_ONLY_EFFECT_UNVERIFIED", "interface_sources": INTERFACE_SOURCES,
            "limits": ["Finite overlap passes can re-enter another collider; independently measure final residuals",
                       "Diagnostic signed plane shortfall is not exact signed-distance/triangle/whole-Body proof",
                       "Fixed waist excluded; source world scale changes require explicit revalidation",
                       "No protection claim for self-collision, inversion, stretch, silhouette or long-run dynamics",
                       "No export proof/strip integration; remove prototype before canonical actions or artist save",
                       "No frame Python handler, new Cloth or artist-key creation"]}
        return {"source": source, "rig": rig, "modifier": modifier, "group": group, "owner": owner,
                "record": record, "fingerprint": fingerprint, "report": report}
    except Exception:
        if modifier is not None and source.modifiers.get(modifier.name) == modifier and modifier.node_group == group:
            source.modifiers.remove(modifier)
        if group is not None and bpy.data.node_groups.get(group.name) == group and group.get(MARKER) == owner and group.users == 0:
            bpy.data.node_groups.remove(group)
        for item, active in active_before:
            if source.modifiers.get(item.name) == item:
                item.is_active = active
        raise


def validate_preview(handle):
    """Explicit QA reproof after a changed pose; not a draw/frame callback."""
    _private_scene()
    source, rig, modifier, group = (handle[name] for name in ("source", "rig", "modifier", "group"))
    _require(source.modifiers.get(modifier.name) == modifier and modifier.node_group == group
             and bpy.data.node_groups.get(group.name) == group and group.get(MARKER) == handle["owner"]
             and group.get("source") == source and group.get("rig") == rig, "exact owned prototype pointers changed")
    _require(source.modifiers[-1] == modifier and _fingerprint(group)[0] == handle["fingerprint"], "prototype graph/order was edited")
    from character_designer import skirt_physics as physics
    graph = bpy.context.evaluated_depsgraph_get()
    scale = _conformal(source.evaluated_get(graph).matrix_world)
    _require(abs(scale - handle["report"]["source_world_scale"]) <= scale * 1.e-6
             and bpy.context.scene.unit_settings.scale_length == handle["report"]["scene_metres_per_unit"],
             "source physical margin scale changed; remove and explicitly reinstall")
    return {"colliders": [_collider_proof(bpy.data.objects[entry["object"]], source, rig, handle["record"], physics, graph,
                                         handle["report"]["margin_m"])
                           for entry in handle["report"]["colliders"]], "node_sha256": handle["fingerprint"],
            "clearance_accepted": False, "scope": "structural current-pose proof only; actual final residual/crossing/shape checks remain required"}


def remove_preview(handle):
    """Remove only the exact owned modifier/node group; no orphan sweeps or rewinds."""
    _private_scene()
    source, rig, modifier, group = (handle[name] for name in ("source", "rig", "modifier", "group"))
    _require(source.modifiers.get(modifier.name) == modifier and modifier.node_group == group
             and bpy.data.node_groups.get(group.name) == group and group.get(MARKER) == handle["owner"]
             and group.get("source") == source and group.get("rig") == rig and group.users == 1,
             "owned pointers changed or node group acquired an external user; cleanup refused")
    _require(_fingerprint(group)[0] == handle["fingerprint"], "preserve the edited prototype graph; cleanup refused")
    from character_designer import skirt_surface as surface
    before = _artist_signature(source, rig, surface)
    source.modifiers.remove(modifier)
    _require(group.users == 0, "owned node group still has users after exact modifier removal")
    bpy.data.node_groups.remove(group)
    _require(_artist_signature(source, rig, surface) == before, "removal changed protected raw author data")
    return {"removed_exact_owned_modifier_and_group": True, "artist_raw_unchanged": True,
            "other_orphans_removed": False, "frames_actions_restored_or_rewritten": False}
