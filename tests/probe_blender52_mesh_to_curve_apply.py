"""Isolated Blender 5.2 probe for Geometry Nodes Mesh-to-Curve baking.

Run with:
    blender.exe --background --factory-startup --python <this-file>

The probe never opens or saves a .blend file.
"""

import json

import bpy


def clear_factory_scene():
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def create_loose_edge_mesh(name):
    """Create one four-vertex edge chain plus one isolated loose vertex."""

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(
        (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
            (0.5, 0.0, 2.0),
            (1.0, 0.0, 3.0),
            (5.0, 5.0, 5.0),  # deliberately isolated
        ),
        ((0, 1), (1, 2), (2, 3)),
        (),
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_geometry_nodes(obj, name, *, with_profile):
    tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    tree.interface.new_socket(
        name="Geometry",
        in_out="INPUT",
        socket_type="NodeSocketGeometry",
    )
    tree.interface.new_socket(
        name="Geometry",
        in_out="OUTPUT",
        socket_type="NodeSocketGeometry",
    )

    group_input = tree.nodes.new("NodeGroupInput")
    group_output = tree.nodes.new("NodeGroupOutput")
    mesh_to_curve = tree.nodes.new("GeometryNodeMeshToCurve")
    mesh_to_curve.inputs["Selection"].default_value = True
    tree.links.new(group_input.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])

    if with_profile:
        circle = tree.nodes.new("GeometryNodeCurvePrimitiveCircle")
        circle.mode = "RADIUS"
        circle.inputs["Resolution"].default_value = 8
        circle.inputs["Radius"].default_value = 0.1
        curve_to_mesh = tree.nodes.new("GeometryNodeCurveToMesh")
        curve_to_mesh.inputs["Fill Caps"].default_value = False
        tree.links.new(mesh_to_curve.outputs["Curve"], curve_to_mesh.inputs["Curve"])
        tree.links.new(circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])
        tree.links.new(curve_to_mesh.outputs["Mesh"], group_output.inputs["Geometry"])
    else:
        tree.links.new(mesh_to_curve.outputs["Curve"], group_output.inputs["Geometry"])

    modifier = obj.modifiers.new(name, "NODES")
    modifier.node_group = tree
    return modifier


def add_curve_to_tube_modifier(obj, name):
    """Consume a Curve geometry component from the preceding modifier."""

    tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    tree.interface.new_socket(
        name="Geometry",
        in_out="INPUT",
        socket_type="NodeSocketGeometry",
    )
    tree.interface.new_socket(
        name="Geometry",
        in_out="OUTPUT",
        socket_type="NodeSocketGeometry",
    )
    group_input = tree.nodes.new("NodeGroupInput")
    group_output = tree.nodes.new("NodeGroupOutput")
    circle = tree.nodes.new("GeometryNodeCurvePrimitiveCircle")
    circle.mode = "RADIUS"
    circle.inputs["Resolution"].default_value = 8
    circle.inputs["Radius"].default_value = 0.1
    curve_to_mesh = tree.nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.inputs["Fill Caps"].default_value = False
    tree.links.new(group_input.outputs["Geometry"], curve_to_mesh.inputs["Curve"])
    tree.links.new(circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])
    tree.links.new(curve_to_mesh.outputs["Mesh"], group_output.inputs["Geometry"])
    modifier = obj.modifiers.new(name, "NODES")
    modifier.node_group = tree
    return modifier


def create_two_modifier_stack(name):
    obj = create_loose_edge_mesh(name)
    mesh_to_curve = add_geometry_nodes(
        obj,
        f"{name}_Mtc",
        with_profile=False,
    )
    curve_to_tube = add_curve_to_tube_modifier(
        obj,
        f"{name}_CurveToTube",
    )
    activate_only(obj)
    return obj, mesh_to_curve, curve_to_tube


def activate_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.view_layer.update()


def data_counts(obj):
    result = {
        "object_type": obj.type,
        "data_type": type(obj.data).__name__ if obj.data is not None else None,
    }
    if obj.type == "MESH":
        result.update(
            vertices=len(obj.data.vertices),
            edges=len(obj.data.edges),
            polygons=len(obj.data.polygons),
        )
    elif obj.type == "CURVE":
        splines = tuple(obj.data.splines)
        result.update(
            splines=len(splines),
            points=sum(
                len(spline.bezier_points)
                if spline.type == "BEZIER"
                else len(spline.points)
                for spline in splines
            ),
            spline_types=tuple(spline.type for spline in splines),
        )
    elif obj.type == "CURVES":
        result.update(
            curves=len(obj.data.curves),
            points=len(obj.data.points),
        )
    return result


def evaluated_counts(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    result = data_counts(evaluated)
    result["original_object_type"] = obj.type
    return result


def apply_modifier_probe(name, *, with_profile):
    obj = create_loose_edge_mesh(name)
    modifier = add_geometry_nodes(obj, f"{name}_GN", with_profile=with_profile)
    activate_only(obj)
    before = data_counts(obj)
    evaluated_before = evaluated_counts(obj)
    error = None
    try:
        operator_result = sorted(bpy.ops.object.modifier_apply(modifier=modifier.name))
    except Exception as exc:
        operator_result = None
        error = f"{type(exc).__name__}: {exc}"
    return {
        "before": before,
        "evaluated_before_apply": evaluated_before,
        "operator_result": operator_result,
        "error": error,
        "modifier_still_present": obj.modifiers.get(modifier.name) is not None,
        "after": data_counts(obj),
    }


def object_convert_probe(target, *, with_modifier):
    label = f"ObjectConvertTo{target}_{'GN' if with_modifier else 'Plain'}"
    obj = create_loose_edge_mesh(label)
    modifier = (
        add_geometry_nodes(obj, f"{label}_GN", with_profile=False)
        if with_modifier
        else None
    )
    activate_only(obj)
    evaluated_before = evaluated_counts(obj)
    error = None
    try:
        operator_result = sorted(
            bpy.ops.object.convert(target=target, keep_original=False)
        )
    except Exception as exc:
        operator_result = None
        error = f"{type(exc).__name__}: {exc}"
    converted = bpy.context.view_layer.objects.active
    source_exists = bpy.data.objects.get(obj.name) is obj
    return {
        "evaluated_before_convert": evaluated_before,
        "operator_result": operator_result,
        "error": error,
        "same_object": converted is obj,
        "source_still_exists": source_exists,
        "source_modifier_still_present": bool(
            modifier is not None
            and source_exists
            and obj.modifiers.get(modifier.name) is not None
        ),
        "after": data_counts(converted),
    }


def apply_named_modifier(obj, modifier):
    error = None
    try:
        operator_result = sorted(bpy.ops.object.modifier_apply(modifier=modifier.name))
    except Exception as exc:
        operator_result = None
        error = f"{type(exc).__name__}: {exc}"
    return {
        "operator_result": operator_result,
        "error": error,
        "base_after": data_counts(obj),
        "evaluated_after": evaluated_counts(obj),
        "remaining_modifiers": tuple(item.name for item in obj.modifiers),
    }


def two_modifier_apply_probe(which):
    obj, mesh_to_curve, curve_to_tube = create_two_modifier_stack(
        f"TwoModifier_{which}"
    )
    report = {
        "base_before": data_counts(obj),
        "evaluated_before": evaluated_counts(obj),
        "modifiers_before": tuple(item.name for item in obj.modifiers),
    }
    target = mesh_to_curve if which == "TOP" else curve_to_tube
    report["apply"] = apply_named_modifier(obj, target)
    return report


def two_modifier_top_then_bottom_probe():
    obj, mesh_to_curve, curve_to_tube = create_two_modifier_stack(
        "TwoModifier_TopThenBottom"
    )
    return {
        "base_before": data_counts(obj),
        "evaluated_before": evaluated_counts(obj),
        "modifiers_before": tuple(item.name for item in obj.modifiers),
        "apply_top": apply_named_modifier(obj, mesh_to_curve),
        "apply_bottom_after_top_failure": apply_named_modifier(obj, curve_to_tube),
    }


def two_modifier_convert_mesh_probe():
    obj, _mesh_to_curve, _curve_to_tube = create_two_modifier_stack(
        "TwoModifier_ConvertMesh"
    )
    report = {
        "base_before": data_counts(obj),
        "evaluated_before": evaluated_counts(obj),
        "modifiers_before": tuple(item.name for item in obj.modifiers),
    }
    error = None
    try:
        operator_result = sorted(
            bpy.ops.object.convert(target="MESH", keep_original=False)
        )
    except Exception as exc:
        operator_result = None
        error = f"{type(exc).__name__}: {exc}"
    converted = bpy.context.view_layer.objects.active
    report.update(
        operator_result=operator_result,
        error=error,
        same_object=converted is obj,
        after=data_counts(converted),
        remaining_modifiers=tuple(item.name for item in converted.modifiers),
    )
    return report


def main():
    clear_factory_scene()
    report = {
        "blender_version": bpy.app.version_string,
        "blend_filepath": bpy.data.filepath,
        "mesh_to_curve_only_apply": apply_modifier_probe(
            "MeshToCurveOnly",
            with_profile=False,
        ),
        "curve_profile_to_mesh_apply": apply_modifier_probe(
            "CurveProfileToMesh",
            with_profile=True,
        ),
        "plain_mesh_object_convert_to_curve": object_convert_probe(
            "CURVE",
            with_modifier=False,
        ),
        "gn_curve_object_convert_to_curve": object_convert_probe(
            "CURVE",
            with_modifier=True,
        ),
        "gn_curve_object_convert_to_curves": object_convert_probe(
            "CURVES",
            with_modifier=True,
        ),
        "two_modifier_apply_top_mtc": two_modifier_apply_probe("TOP"),
        "two_modifier_apply_bottom_curve_to_tube": two_modifier_apply_probe("BOTTOM"),
        "two_modifier_apply_top_then_bottom": two_modifier_top_then_bottom_probe(),
        "two_modifier_object_convert_mesh": two_modifier_convert_mesh_probe(),
    }
    print("BLENDER52_GN_PROBE=" + json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
