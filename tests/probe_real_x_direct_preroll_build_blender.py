"""Disposable in-memory Direct Pre-Roll acceptance probe for the real X.blend.

This script intentionally never saves.  It opens X.blend in a background
Blender process, removes an existing owned Limb IK rig only in memory, builds
and exercises the minimal Direct Pre-Roll rig, measures the effective Hand and
Foot widget frames against the real character geometry, verifies Rebuild and
Remove, and proves that the input file fingerprint did not change.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for root in (PROJECT_ROOT / "addons", PROJECT_ROOT / "tests"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

import character_designer
from character_designer import limb_ik
import test_real_x_pole_direction_migration_blender as migration


HAND_FRAME_MAX_DEGREES = 0.1
FOOT_BOUNDS_TOLERANCE = 2.0e-5
FOOT_MIN_MARGIN_RATIO = 0.01
FOOT_MAX_MARGIN_RATIO = 0.12
FOOT_MIN_SIZE_RATIO = 1.01
FOOT_MAX_SIZE_RATIO = 1.25
FOOT_MIN_SOLE_GAP_RATIO = 0.005
FOOT_MAX_SOLE_GAP_RATIO = 0.08


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "sha256": digest.hexdigest().upper(),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def source_rest_snapshot(armature):
    result = {}
    for bone in armature.data.bones:
        if bone.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE:
            continue
        result[bone.name] = {
            "head": Vector(bone.head_local).copy(),
            "tail": Vector(bone.tail_local).copy(),
            "matrix": bone.matrix_local.copy(),
            "parent": bone.parent.name if bone.parent is not None else "",
            "use_connect": bool(bone.use_connect),
            "use_deform": bool(bone.use_deform),
        }
    return result


def max_matrix_delta(left, right):
    return max(
        abs(float(left[row][column] - right[row][column]))
        for row in range(4)
        for column in range(4)
    )


def deformed_mesh_snapshot(armature):
    """Capture evaluated world-space vertices for meshes driven by armature."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or not any(
            modifier.type == "ARMATURE"
            and modifier.object is armature
            and modifier.show_viewport
            for modifier in obj.modifiers
        ):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            world = evaluated.matrix_world
            result[obj.name] = tuple(world @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    if not result:
        raise AssertionError("No evaluated meshes driven by the real X armature were found")
    return result


def assert_deformed_mesh_equal(armature, expected, label):
    actual = deformed_mesh_snapshot(armature)
    if set(actual) != set(expected):
        raise AssertionError(f"{label}: driven mesh set changed")
    maximum = 0.0
    vertices = 0
    for name, expected_vertices in expected.items():
        actual_vertices = actual[name]
        if len(actual_vertices) != len(expected_vertices):
            raise AssertionError(
                f"{label}: evaluated vertex count changed on {name}: "
                f"{len(expected_vertices)} -> {len(actual_vertices)}"
            )
        vertices += len(actual_vertices)
        maximum = max(
            maximum,
            max(
                ((actual_co - expected_co).length for actual_co, expected_co in zip(actual_vertices, expected_vertices)),
                default=0.0,
            ),
        )
    if maximum > 5.0e-5:
        raise AssertionError(f"{label}: evaluated skin moved by {maximum} m")
    return {"meshes": len(actual), "vertices": vertices, "max_world_error": float(maximum)}


def assert_source_rest_equal(armature, expected, label):
    actual_names = {
        bone.name
        for bone in armature.data.bones
        if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    }
    if actual_names != set(expected):
        raise AssertionError(f"{label}: source bone names changed")
    maxima = {"head": 0.0, "tail": 0.0, "matrix": 0.0}
    for name, state in expected.items():
        bone = armature.data.bones[name]
        maxima["head"] = max(maxima["head"], (Vector(bone.head_local) - state["head"]).length)
        maxima["tail"] = max(maxima["tail"], (Vector(bone.tail_local) - state["tail"]).length)
        maxima["matrix"] = max(maxima["matrix"], max_matrix_delta(bone.matrix_local, state["matrix"]))
        if (bone.parent.name if bone.parent is not None else "") != state["parent"]:
            raise AssertionError(f"{label}: parent changed on {name}")
        if bool(bone.use_connect) != state["use_connect"]:
            raise AssertionError(f"{label}: use_connect changed on {name}")
        if bool(bone.use_deform) != state["use_deform"]:
            raise AssertionError(f"{label}: use_deform changed on {name}")
    if max(maxima.values()) > 2.0e-6:
        raise AssertionError(f"{label}: source Rest mismatch {maxima}")
    return maxima


def pole_alignment(armature, rig):
    upper = armature.pose.bones[rig["chain"][0]]
    lower = armature.pose.bones[rig["chain"][1]]
    pole = armature.pose.bones[rig["pole"].name]
    start = Vector(upper.head)
    joint = Vector(lower.head)
    end = Vector(lower.tail)
    axis = end - start
    if axis.length <= limb_ik.EPSILON:
        return None
    projection = start + axis * (joint - start).dot(axis) / axis.length_squared
    bend = joint - projection
    toward_pole = limb_ik._project_perpendicular(Vector(pole.head) - projection, axis)
    if min(bend.length, toward_pole.length) <= limb_ik.EPSILON:
        return None
    return float(bend.normalized().dot(toward_pole.normalized()))


def direct_metrics(armature, inventory):
    metrics = {}
    for key, rig in sorted(inventory["rigs"].items()):
        kind, side = key
        item = {"alignment": pole_alignment(armature, rig), "bones": {}}
        for name in rig["chain"][:2]:
            pose_matrix = armature.pose.bones[name].matrix.copy()
            rest_matrix = armature.data.bones[name].matrix_local.copy()
            deform = pose_matrix @ rest_matrix.inverted()
            position_error = (pose_matrix.translation - rest_matrix.translation).length
            rotation_error = limb_ik._rotation_error(pose_matrix, rest_matrix)
            deform_rotation = float(deform.to_quaternion().angle)
            values = (position_error, rotation_error, deform_rotation)
            if any(not math.isfinite(value) for value in values):
                raise AssertionError(f"{kind}.{side} {name} produced non-finite start metrics")
            if position_error > 2.0e-5 or rotation_error > 2.0e-4 or deform_rotation > 2.0e-4:
                raise AssertionError(
                    f"{kind}.{side} {name} Direct start is not identity: "
                    f"position={position_error}, rotation={rotation_error}, deform={deform_rotation}"
                )
            item["bones"][name] = {
                "position_error": float(position_error),
                "rotation_error_radians": float(rotation_error),
                "deform_rotation_radians": float(deform_rotation),
            }
        if item["alignment"] is None or item["alignment"] < 0.999:
            raise AssertionError(f"{kind}.{side} Direct Pole alignment failed: {item['alignment']}")
        metrics[f"{kind}.{side}"] = item
    return metrics


def _angle_degrees(left, right):
    left = Vector(left).normalized()
    right = Vector(right).normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, float(left.dot(right))))))


def _rotation_error_degrees(left, right):
    relative = left.inverted_safe() @ right
    return math.degrees(float(relative.to_quaternion().angle))


def _constraint_for_role(rig, role):
    matches = [
        (pose_bone, constraint)
        for pose_bone, constraint, record in rig["entries"]
        if record["role"] == role
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"{rig['rig_id']} expected one {role} constraint, got {len(matches)}"
        )
    return matches[0]


def _effective_custom_shape_points(pose_bone):
    shape = pose_bone.custom_shape
    if shape is None or shape.type != "MESH":
        raise AssertionError(f"{pose_bone.name} has no Mesh custom shape")
    if pose_bone.use_custom_shape_bone_size:
        raise AssertionError(f"{pose_bone.name} unexpectedly scales its widget by bone length")
    transform = pose_bone.custom_shape_transform or pose_bone
    transform_matrix = transform.matrix.copy()
    rotation = pose_bone.custom_shape_rotation_euler.to_matrix()
    scale = Vector(pose_bone.custom_shape_scale_xyz)
    translation = Vector(pose_bone.custom_shape_translation)
    points = []
    for vertex in shape.data.vertices:
        local = Vector(
            (
                vertex.co.x * scale.x,
                vertex.co.y * scale.y,
                vertex.co.z * scale.z,
            )
        )
        points.append(transform_matrix @ (translation + rotation @ local))
    if len(points) < 4:
        raise AssertionError(f"{pose_bone.name} custom shape has too little geometry")
    return tuple(points)


def _real_shoe_points(armature):
    shoe = bpy.data.objects.get("Shoes")
    if shoe is None or shoe.type != "MESH":
        raise AssertionError("The real X Shoes Mesh was not found")
    if not shoe.visible_get(view_layer=bpy.context.view_layer):
        raise AssertionError("The real X Shoes Mesh is not visible")
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = shoe.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        transform = armature.matrix_world.inverted_safe() @ evaluated.matrix_world
        points = tuple(transform @ vertex.co for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()
    if len(points) < 8:
        raise AssertionError("The evaluated real X Shoes Mesh has too little geometry")
    return points


def _source_center_x(armature):
    roots = [
        bone
        for bone in armature.data.bones
        if bone.parent is None and bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    ]
    if not roots:
        raise AssertionError("The real X armature has no source roots")
    return sum(float(bone.head_local.x) for bone in roots) / len(roots)


def _horizontal_frame(points, preferred_forward):
    mean_x = sum(float(point.x) for point in points) / len(points)
    mean_y = sum(float(point.y) for point in points) / len(points)
    covariance_xx = sum((float(point.x) - mean_x) ** 2 for point in points)
    covariance_yy = sum((float(point.y) - mean_y) ** 2 for point in points)
    covariance_xy = sum(
        (float(point.x) - mean_x) * (float(point.y) - mean_y)
        for point in points
    )
    angle = 0.5 * math.atan2(
        2.0 * covariance_xy,
        covariance_xx - covariance_yy,
    )
    forward = Vector((math.cos(angle), math.sin(angle), 0.0))
    preferred = Vector(preferred_forward)
    preferred.z = 0.0
    if preferred.length <= limb_ik.EPSILON:
        preferred = Vector((0.0, -1.0, 0.0))
    preferred.normalize()
    if forward.dot(preferred) < 0.0:
        forward.negate()
    lateral = Vector((-forward.y, forward.x, 0.0))
    return lateral, forward


def _projected_bounds(points, lateral, forward):
    u_values = [float(point.dot(lateral)) for point in points]
    v_values = [float(point.dot(forward)) for point in points]
    z_values = [float(point.z) for point in points]
    return {
        "u_min": min(u_values),
        "u_max": max(u_values),
        "v_min": min(v_values),
        "v_max": max(v_values),
        "z_min": min(z_values),
        "z_max": max(z_values),
    }


def _hand_acceptance_metrics(armature, rig):
    kind, side = rig["entries"][0][2]["kind"], rig["entries"][0][2]["side"]
    if kind != "ARM":
        raise AssertionError(f"{kind}.{side} is not an arm")
    lower_rest = armature.data.bones[rig["chain"][1]].matrix_local.to_3x3().normalized()
    target_rest_bone = armature.data.bones[rig["target"].name]
    target_rest = target_rest_bone.matrix_local.to_3x3().normalized()
    target_forward_error = _angle_degrees(lower_rest.col[1], target_rest.col[1])
    target_frame_error = _rotation_error_degrees(lower_rest, target_rest)
    target_head_error = (
        Vector(target_rest_bone.head_local)
        - Vector(armature.data.bones[rig["chain"][1]].tail_local)
    ).length

    lower_pose = armature.pose.bones[rig["chain"][1]].matrix.to_3x3().normalized()
    target_pose = armature.pose.bones[rig["target"].name]
    display_frame = (
        (target_pose.custom_shape_transform or target_pose).matrix.to_3x3().normalized()
        @ target_pose.custom_shape_rotation_euler.to_matrix()
    )
    display_forward_error = _angle_degrees(lower_pose.col[1], display_frame.col[1])
    display_frame_error = _rotation_error_degrees(lower_pose, display_frame)
    frame_values = (
        target_forward_error,
        target_frame_error,
        display_forward_error,
        display_frame_error,
    )
    if any(not math.isfinite(value) for value in frame_values):
        raise AssertionError(f"ARM.{side} produced non-finite hand frame metrics")
    if target_head_error > 2.0e-5:
        raise AssertionError(
            f"ARM.{side} target is not anchored at the Forearm tail: {target_head_error}"
        )
    if target_forward_error > HAND_FRAME_MAX_DEGREES:
        raise AssertionError(
            f"ARM.{side} target does not point with the Forearm: {target_forward_error} deg"
        )
    if target_frame_error > HAND_FRAME_MAX_DEGREES:
        raise AssertionError(
            f"ARM.{side} target Rest frame is twisted from the Forearm: {target_frame_error} deg"
        )
    if display_forward_error > HAND_FRAME_MAX_DEGREES:
        raise AssertionError(
            f"ARM.{side} hand widget does not point with the Forearm: {display_forward_error} deg"
        )
    if display_frame_error > HAND_FRAME_MAX_DEGREES:
        raise AssertionError(
            f"ARM.{side} hand widget is visually tilted: {display_frame_error} deg"
        )

    end_owner, end_rotation = _constraint_for_role(rig, "END_ROTATION")
    if (
        end_owner.name != rig["chain"][2]
        or end_rotation.type != "COPY_ROTATION"
        or end_rotation.target is not armature
        or end_rotation.subtarget != rig["target"].name
        or end_rotation.target_space != "LOCAL_OWNER_ORIENT"
        or end_rotation.owner_space != "LOCAL_WITH_PARENT"
        or getattr(end_rotation, "mix_mode", "") != "REPLACE"
    ):
        raise AssertionError(
            f"ARM.{side} wrist Copy Rotation is not the required local-space mapping"
        )
    return {
        "target_head_error": float(target_head_error),
        "target_forward_error_degrees": float(target_forward_error),
        "target_frame_error_degrees": float(target_frame_error),
        "display_forward_error_degrees": float(display_forward_error),
        "display_frame_error_degrees": float(display_frame_error),
        "end_rotation_target_space": end_rotation.target_space,
        "end_rotation_owner_space": end_rotation.owner_space,
    }


def _foot_acceptance_metrics(armature, rig, shoe_points, center_x):
    kind, side = rig["entries"][0][2]["kind"], rig["entries"][0][2]["side"]
    if kind != "LEG":
        raise AssertionError(f"{kind}.{side} is not a leg")
    side_sign = 1.0 if side == "L" else -1.0
    side_shoe_points = tuple(
        point
        for point in shoe_points
        if side_sign * (float(point.x) - center_x) >= -FOOT_BOUNDS_TOLERANCE
    )
    if len(side_shoe_points) < 4:
        raise AssertionError(f"LEG.{side} has too little Shoes geometry on its side")
    target = armature.pose.bones[rig["target"].name]
    display_points = _effective_custom_shape_points(target)
    foot = armature.pose.bones[rig["chain"][2]]
    preferred_forward = Vector(foot.tail) - Vector(foot.head)
    lateral, forward = _horizontal_frame(side_shoe_points, preferred_forward)
    transform = target.custom_shape_transform or target
    display_axes = (
        transform.matrix.to_3x3().normalized()
        @ target.custom_shape_rotation_euler.to_matrix()
    )
    scale = Vector(target.custom_shape_scale_xyz)
    raw_positive_x = display_axes @ Vector((scale.x, 0.0, 0.0))
    raw_positive_y = display_axes @ Vector((0.0, scale.y, 0.0))
    raw_positive_x.normalize()
    raw_positive_y.normalize()
    toe_alignment = float(raw_positive_y.dot(forward))
    medial = Vector((center_x - float(foot.head.x), 0.0, 0.0))
    if medial.length <= limb_ik.EPSILON:
        raise AssertionError(f"LEG.{side} has no measurable medial direction")
    medial.normalize()
    medial_alignment = float(raw_positive_x.dot(medial))
    if toe_alignment < 0.995:
        raise AssertionError(
            f"LEG.{side} Foot raw +Y does not point to the shoe toes: {toe_alignment}"
        )
    if medial_alignment < 0.995:
        raise AssertionError(
            f"LEG.{side} Foot raw +X does not point to the big-toe/medial side: "
            f"{medial_alignment}"
        )
    if max(abs(float(raw_positive_x.z)), abs(float(raw_positive_y.z))) > 1.0e-5:
        raise AssertionError(
            f"LEG.{side} Foot widget plane is tilted: "
            f"raw+X.z={raw_positive_x.z}, raw+Y.z={raw_positive_y.z}"
        )
    shoe = _projected_bounds(side_shoe_points, lateral, forward)
    display = _projected_bounds(display_points, lateral, forward)
    shoe_width = shoe["u_max"] - shoe["u_min"]
    shoe_length = shoe["v_max"] - shoe["v_min"]
    display_width = display["u_max"] - display["u_min"]
    display_length = display["v_max"] - display["v_min"]
    if min(shoe_width, shoe_length, display_width, display_length) <= limb_ik.EPSILON:
        raise AssertionError(f"LEG.{side} produced a degenerate shoe/widget footprint")
    width_ratio = display_width / shoe_width
    length_ratio = display_length / shoe_length
    margins = {
        "u_min": shoe["u_min"] - display["u_min"],
        "u_max": display["u_max"] - shoe["u_max"],
        "v_min": shoe["v_min"] - display["v_min"],
        "v_max": display["v_max"] - shoe["v_max"],
    }
    margin_ratio = min(margins.values()) / min(shoe_width, shoe_length)
    min_signed_center_distance = min(
        side_sign * (float(point.x) - center_x) for point in display_points
    )
    sole_clearance = shoe["z_min"] - display["z_max"]
    sole_clearance_ratio = sole_clearance / shoe_length
    values = (
        width_ratio,
        length_ratio,
        min_signed_center_distance,
        sole_clearance,
        sole_clearance_ratio,
        margin_ratio,
        *margins.values(),
    )
    if any(not math.isfinite(value) for value in values):
        raise AssertionError(f"LEG.{side} produced non-finite shoe widget metrics")
    if min(margins.values()) < -FOOT_BOUNDS_TOLERANCE:
        raise AssertionError(
            f"LEG.{side} widget does not surround the Shoes bounds: {margins}"
        )
    if not FOOT_MIN_MARGIN_RATIO <= margin_ratio <= FOOT_MAX_MARGIN_RATIO:
        raise AssertionError(
            f"LEG.{side} widget border is not a small ring around Shoes: {margin_ratio}"
        )
    if not FOOT_MIN_SIZE_RATIO <= width_ratio <= FOOT_MAX_SIZE_RATIO:
        raise AssertionError(
            f"LEG.{side} widget width ratio is not slightly larger than Shoes: {width_ratio}"
        )
    if not FOOT_MIN_SIZE_RATIO <= length_ratio <= FOOT_MAX_SIZE_RATIO:
        raise AssertionError(
            f"LEG.{side} widget length ratio is not slightly larger than Shoes: {length_ratio}"
        )
    if min_signed_center_distance < -FOOT_BOUNDS_TOLERANCE:
        raise AssertionError(
            f"LEG.{side} widget crosses the armature centerline by "
            f"{-min_signed_center_distance}"
        )
    if not FOOT_MIN_SOLE_GAP_RATIO <= sole_clearance_ratio <= FOOT_MAX_SOLE_GAP_RATIO:
        raise AssertionError(
            f"LEG.{side} widget is not slightly below the Shoes sole: "
            f"clearance={sole_clearance}, ratio={sole_clearance_ratio}"
        )

    end_owner, end_rotation = _constraint_for_role(rig, "END_ROTATION")
    if (
        end_owner.name != rig["chain"][2]
        or end_rotation.type != "COPY_ROTATION"
        or end_rotation.target is not armature
        or end_rotation.subtarget != rig["target"].name
        or end_rotation.target_space != "WORLD"
        or end_rotation.owner_space != "WORLD"
        or getattr(end_rotation, "mix_mode", "") != "REPLACE"
    ):
        raise AssertionError(f"LEG.{side} Foot Copy Rotation spaces changed")
    return {
        "shoe_bounds": {name: float(value) for name, value in shoe.items()},
        "display_bounds": {name: float(value) for name, value in display.items()},
        "display_margins": {name: float(value) for name, value in margins.items()},
        "minimum_margin_to_shoe_minor_span": float(margin_ratio),
        "shoe_width": float(shoe_width),
        "shoe_length": float(shoe_length),
        "display_width": float(display_width),
        "display_length": float(display_length),
        "width_ratio": float(width_ratio),
        "length_ratio": float(length_ratio),
        "shoe_aspect_ratio": float(shoe_length / shoe_width),
        "display_aspect_ratio": float(display_length / display_width),
        "shoe_sole_z": float(shoe["z_min"]),
        "display_top_z": float(display["z_max"]),
        "display_bottom_z": float(display["z_min"]),
        "sole_clearance": float(sole_clearance),
        "sole_clearance_to_shoe_length": float(sole_clearance_ratio),
        "min_signed_center_distance": float(min_signed_center_distance),
        "raw_positive_y_toe_alignment": toe_alignment,
        "raw_positive_x_medial_alignment": medial_alignment,
        "end_rotation_target_space": end_rotation.target_space,
        "end_rotation_owner_space": end_rotation.owner_space,
    }


def control_acceptance_metrics(armature, inventory):
    shoe_points = _real_shoe_points(armature)
    center_x = _source_center_x(armature)
    hands = {}
    feet = {}
    for key, rig in sorted(inventory["rigs"].items()):
        kind, side = key
        if kind == "ARM":
            hands[side] = _hand_acceptance_metrics(armature, rig)
        else:
            feet[side] = _foot_acceptance_metrics(
                armature,
                rig,
                shoe_points,
                center_x,
            )
    return {
        "center_x": float(center_x),
        "hands": hands,
        "feet": feet,
    }


def assert_minimal_inventory(armature):
    inventory = limb_ik._validate_inventory(armature)
    if inventory["schema"] != limb_ik.DIRECT_PREROLL_SCHEMA:
        raise AssertionError(f"Expected Direct schema, got {inventory['schema']}")
    if set(inventory["rigs"]) != {
        ("ARM", "L"), ("ARM", "R"), ("LEG", "L"), ("LEG", "R")
    }:
        raise AssertionError(f"Direct Build All did not produce 4 limbs: {set(inventory['rigs'])}")
    expected = {
        name
        for kind, side in inventory["rigs"]
        for name in (
            limb_ik.LIMB_SPEC[kind]["target"].format(side=side),
            limb_ik.LIMB_SPEC[kind]["pole"].format(side=side),
        )
    }
    actual = {bone.name for bone in inventory["bones"]}
    if actual != expected:
        raise AssertionError(f"Direct rig is not Target+Pole minimal: {sorted(actual)}")
    if any(token in name for name in actual for token in ("MCH_upper", "MCH_forearm", "MCH_thigh", "MCH_shin", "ORI_")):
        raise AssertionError(f"Direct rig unexpectedly contains MCH/ORI helpers: {sorted(actual)}")
    registry = limb_ik._load_direct_rest_registry(armature, strict=True)
    if len(registry["limbs"]) != 4:
        raise AssertionError("Direct Rest registry does not contain exactly four limbs")
    source_widgets = inventory.get("source_widgets")
    if source_widgets is None:
        raise AssertionError("Direct Build did not create the source-control Custom Shape registry")
    if source_widgets.get("version") != limb_ik.SOURCE_WIDGETS_VERSION:
        raise AssertionError(
            f"Direct Build source-widget registry is v{source_widgets.get('version')}, "
            f"expected v{limb_ik.SOURCE_WIDGETS_VERSION}"
        )
    source_counts = {
        kind: sum(1 for record in source_widgets["bones"].values() if record["kind"] == kind)
        for kind in ("FINGER", "SHOULDER")
    }
    if source_counts != {"FINGER": 30, "SHOULDER": 2}:
        raise AssertionError(
            f"Direct Build did not decorate exactly 30 Finger + 2 Shoulder source bones: {source_counts}; "
            f"records={sorted(source_widgets['bones'])}"
        )
    for bone_name, record in source_widgets["bones"].items():
        if record["kind"] != "FINGER":
            continue
        generated_translation = tuple(float(value) for value in record["generated"]["translation"])
        live_translation = tuple(
            float(value)
            for value in armature.pose.bones[bone_name].custom_shape_translation
        )
        if any(abs(value) > 1.0e-7 for value in (*generated_translation, *live_translation)):
            raise AssertionError(
                f"Finger '{bone_name}' is not centered on its joint Head: "
                f"generated={generated_translation}, live={live_translation}"
            )
    widgets = {
        obj.get(limb_ik.KIND_KEY): obj
        for obj in bpy.data.objects
        if limb_ik._owned(obj, inventory["armature_id"], role="WIDGET")
    }
    for kind, expected in (("FINGER", (32, 32)), ("SHOULDER", (44, 44))):
        obj = widgets.get(kind)
        topology = (
            (len(obj.data.vertices), len(obj.data.edges))
            if obj is not None
            else None
        )
        if topology != expected:
            raise AssertionError(f"{kind} source widget topology is {topology}, expected {expected}")
    return inventory, registry


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("Expected exactly one X.blend path after --")
    path = Path(args[0]).resolve()
    disk_before = fingerprint(path)
    if bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False) != {"FINISHED"}:
        raise AssertionError(f"Could not open {path}")
    character_designer.register()
    armature = migration._find_real_armature()
    migration._mode_set(bpy.context, armature, "POSE")

    # The real file may preserve a per-view-layer Shoes hide flag even when the
    # artist has it visible in the working UI.  Reveal it only in this disposable
    # process so the acceptance test always exercises footwear-aware fitting.
    shoes_object = bpy.data.objects.get("Shoes")
    shoes_visibility = None
    if shoes_object is not None:
        shoes_visibility = (bool(shoes_object.hide_viewport), bool(shoes_object.hide_get()))
        shoes_object.hide_viewport = False
        shoes_object.hide_set(False)

    opened_inventory = limb_ik._validate_inventory(armature)
    opened_summary = {
        "schema": int(opened_inventory["schema"]),
        "rigs": len(opened_inventory["rigs"]),
        "generated_bones": len(opened_inventory["bones"]),
    }
    settings = bpy.context.window_manager.character_designer_limb_ik
    if opened_inventory["rigs"]:
        problems = limb_ik._foreign_dependency_problems(armature, opened_inventory)
        if problems:
            raise AssertionError(f"Existing generated rig cannot be removed in memory: {problems[0]}")
        result = bpy.ops.character_designer.limb_ik_remove()
        if result != {"FINISHED"}:
            raise AssertionError(f"Could not remove existing rig in memory: {settings.last_message}")

    migration._mode_set(bpy.context, armature, "POSE")
    if bpy.ops.character_designer.limb_ik_analyze() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    for key in limb_ik.DEFAULT_POLE_DIRECTIONS:
        kind, side = key
        setattr(
            settings,
            limb_ik._pole_direction_field(kind, side),
            limb_ik.DEFAULT_POLE_DIRECTIONS[key],
        )
    settings.build_method = "DIRECT_PREROLL"

    source_before = source_rest_snapshot(armature)
    source_digest_before = limb_ik._armature_digest(armature)
    skin_before = deformed_mesh_snapshot(armature)
    readiness = {}
    for key, selection in {
        ("ARM", "L"): "LEFT_ARM",
        ("ARM", "R"): "RIGHT_ARM",
        ("LEG", "L"): "LEFT_LEG",
        ("LEG", "R"): "RIGHT_LEG",
    }.items():
        settings.selected_limb = selection
        result = bpy.ops.character_designer.limb_ik_direct_preroll_check()
        if result != {"FINISHED"}:
            raise AssertionError(settings.last_message)
        readiness[f"{key[0]}.{key[1]}"] = json.loads(settings.direct_preroll_json)["result"]

    build_result = bpy.ops.character_designer.limb_ik_build_all()
    if build_result != {"FINISHED"}:
        raise AssertionError(f"Direct Build All failed: {settings.last_message}")
    inventory, registry = assert_minimal_inventory(armature)
    start_metrics = direct_metrics(armature, inventory)
    build_control_metrics = control_acceptance_metrics(armature, inventory)
    build_skin_metrics = assert_deformed_mesh_equal(armature, skin_before, "Direct Build")
    applied_digest = limb_ik._armature_digest(armature)
    if applied_digest == source_digest_before:
        raise AssertionError("Direct Build did not apply the reported source Rest re-plane")

    auto_align_metrics = {}
    selection_by_key = {
        ("ARM", "L"): "LEFT_ARM",
        ("ARM", "R"): "RIGHT_ARM",
        ("LEG", "L"): "LEFT_LEG",
        ("LEG", "R"): "RIGHT_LEG",
    }
    for key, selection in selection_by_key.items():
        rig = inventory["rigs"][key]
        target = armature.pose.bones[rig["target"].name]
        solver = armature.pose.bones[rig["solver_target"].name]
        end = armature.pose.bones[rig["chain"][2]]
        end_rotation = next(
            constraint
            for _owner, constraint, record in rig["entries"]
            if record["role"] == "END_ROTATION"
        )
        saved_mode = target.rotation_mode
        saved_basis = target.matrix_basis.copy()
        saved_mute = bool(end_rotation.mute)
        saved_auto_present = limb_ik.AUTO_ALIGN_KEY in target.bone
        saved_auto = target.bone.get(limb_ik.AUTO_ALIGN_KEY, None)
        try:
            if rig["auto_align"] or saved_auto is not False or saved_mute:
                raise AssertionError(f"Real X {key} did not start in Manual mode")

            settings.selected_limb = selection
            solver_before_enable = armature.matrix_world @ solver.matrix.copy()
            target_basis_before_enable = target.matrix_basis.copy()
            if (
                bpy.ops.character_designer.limb_ik_auto_align_target(action="ENABLE")
                != {"FINISHED"}
            ):
                raise AssertionError(
                    f"Real X Auto Align ENABLE {key} failed: {settings.last_message}"
                )
            enabled_rig = limb_ik._validate_inventory(armature)["rigs"][key]
            if (
                not enabled_rig["auto_align"]
                or target.bone.get(limb_ik.AUTO_ALIGN_KEY, None) is not True
                or not end_rotation.mute
            ):
                raise AssertionError(f"Real X Auto Align ENABLE {key} did not persist its mode")
            enable_solver_error = (
                (armature.matrix_world @ solver.matrix).to_translation()
                - solver_before_enable.to_translation()
            ).length
            enable_target_write = max_matrix_delta(
                target.matrix_basis,
                target_basis_before_enable,
            )
            if enable_solver_error > 2.0e-4 or enable_target_write > 1.0e-7:
                raise AssertionError(
                    f"Real X Auto Align ENABLE {key} changed authored transforms: "
                    f"solver={enable_solver_error}, target_basis={enable_target_write}"
                )

            # Auto is a persistent evaluation mode: rotating the visible
            # Target must be ignored while translating it still drives IK and
            # leaves the end in its natural, lower-bone-inherited frame.
            natural_end_before_rotation = armature.matrix_world @ end.matrix.copy()
            solver_before_rotation = armature.matrix_world @ solver.matrix.copy()
            target.matrix_basis = target.matrix_basis @ Matrix.Rotation(
                0.19 if key[1] == "L" else -0.17,
                4,
                "Z",
            )
            bpy.context.view_layer.update()
            auto_rotation_leak = limb_ik._rotation_error(
                armature.matrix_world @ end.matrix,
                natural_end_before_rotation,
            )
            auto_rotation_solver_error = (
                (armature.matrix_world @ solver.matrix).to_translation()
                - solver_before_rotation.to_translation()
            ).length
            if auto_rotation_leak > 3.0e-3 or auto_rotation_solver_error > 2.0e-4:
                raise AssertionError(
                    f"Real X Auto Align {key} still consumed Target rotation: "
                    f"end={auto_rotation_leak}, solver={auto_rotation_solver_error}"
                )

            upper = armature.pose.bones[rig["chain"][0]]
            lower = armature.pose.bones[rig["chain"][1]]
            chain_axis = Vector(lower.tail) - Vector(upper.head)
            if chain_axis.length <= 1.0e-8:
                raise AssertionError(f"Real X {key} has a zero-length evaluated limb axis")
            chain_axis.normalize()
            reference_axis = min(
                (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0))),
                key=lambda axis: abs(chain_axis.dot(axis)),
            )
            move_direction = chain_axis.cross(reference_axis).normalized()
            limb_length = max(
                (Vector(upper.tail) - Vector(upper.head)).length
                + (Vector(lower.tail) - Vector(lower.head)).length,
                1.0e-3,
            )
            target_before_move = armature.matrix_world @ target.matrix.copy()
            solver_before_move = armature.matrix_world @ solver.matrix.copy()
            moved_target = target.matrix.copy()
            moved_target.translation += move_direction * limb_length * 0.02
            target.matrix = moved_target
            bpy.context.view_layer.update()
            target_after_move = armature.matrix_world @ target.matrix.copy()
            solver_after_move = armature.matrix_world @ solver.matrix.copy()
            auto_target_motion = (
                target_after_move.to_translation() - target_before_move.to_translation()
            ).length
            auto_solver_motion = (
                solver_after_move.to_translation() - solver_before_move.to_translation()
            ).length
            inherited_end = (
                lower.matrix
                @ lower.bone.matrix_local.inverted_safe()
                @ end.bone.matrix_local
                @ end.matrix_basis
            )
            natural_end_error = limb_ik._rotation_error(end.matrix, inherited_end)
            if (
                auto_target_motion < limb_length * 0.01
                or auto_solver_motion < limb_length * 0.005
                or natural_end_error > 3.0e-3
                or target.bone.get(limb_ik.AUTO_ALIGN_KEY, None) is not True
                or not end_rotation.mute
            ):
                raise AssertionError(
                    f"Real X Auto Align {key} did not follow naturally: "
                    f"target_move={auto_target_motion}, solver_move={auto_solver_motion}, "
                    f"natural_end={natural_end_error}"
                )

            solver_before_disable = armature.matrix_world @ solver.matrix.copy()
            end_before_disable = armature.matrix_world @ end.matrix.copy()
            target_before_disable = armature.matrix_world @ target.matrix.copy()
            if (
                bpy.ops.character_designer.limb_ik_auto_align_target(action="DISABLE")
                != {"FINISHED"}
            ):
                raise AssertionError(
                    f"Real X Auto Align DISABLE {key} failed: {settings.last_message}"
                )
            disabled_rig = limb_ik._validate_inventory(armature)["rigs"][key]
            disable_solver_error = (
                (armature.matrix_world @ solver.matrix).to_translation()
                - solver_before_disable.to_translation()
            ).length
            disable_end_error = limb_ik._rotation_error(
                armature.matrix_world @ end.matrix,
                end_before_disable,
            )
            disable_target_sync = limb_ik._rotation_error(
                armature.matrix_world @ target.matrix,
                target_before_disable,
            )
            if (
                disabled_rig["auto_align"]
                or target.bone.get(limb_ik.AUTO_ALIGN_KEY, None) is not False
                or end_rotation.mute
                or disable_solver_error > 2.0e-4
                or disable_end_error > 3.0e-3
                or disable_target_sync < 2.0e-3
            ):
                raise AssertionError(
                    f"Real X Auto Align DISABLE {key} missed its pop-free handoff: "
                    f"solver={disable_solver_error}, end={disable_end_error}, "
                    f"target_sync={disable_target_sync}"
                )

            # Once Manual is restored, Target rotation must drive the end again
            # without moving the IK solver point.
            manual_end_before = armature.matrix_world @ end.matrix.copy()
            manual_solver_before = armature.matrix_world @ solver.matrix.copy()
            target.matrix_basis = (
                target.matrix_basis
                @ Matrix.Rotation(0.11, 4, "X")
                @ Matrix.Rotation(-0.07, 4, "Z")
            )
            bpy.context.view_layer.update()
            manual_end_response = limb_ik._rotation_error(
                armature.matrix_world @ end.matrix,
                manual_end_before,
            )
            manual_solver_error = (
                (armature.matrix_world @ solver.matrix).to_translation()
                - manual_solver_before.to_translation()
            ).length
            if (
                manual_end_response < 2.0e-2
                or manual_solver_error > 2.0e-4
                or target.bone.get(limb_ik.AUTO_ALIGN_KEY, None) is not False
                or end_rotation.mute
            ):
                raise AssertionError(
                    f"Real X Manual Target {key} did not resume cleanly: "
                    f"end_response={manual_end_response}, solver={manual_solver_error}"
                )

            auto_align_metrics[f"{key[0]}.{key[1]}"] = {
                "enable_solver_position_error": float(enable_solver_error),
                "enable_target_basis_write": float(enable_target_write),
                "auto_rotation_leak": float(auto_rotation_leak),
                "auto_rotation_solver_error": float(auto_rotation_solver_error),
                "auto_target_motion": float(auto_target_motion),
                "auto_solver_motion": float(auto_solver_motion),
                "natural_end_rotation_error": float(natural_end_error),
                "disable_solver_position_error": float(disable_solver_error),
                "disable_end_rotation_error": float(disable_end_error),
                "disable_target_sync_rotation": float(disable_target_sync),
                "manual_end_rotation_response": float(manual_end_response),
                "manual_solver_position_error": float(manual_solver_error),
            }
        finally:
            # Every limb returns to its exact pre-test Manual state even if an
            # assertion above fails. The generated rig is still removed by the
            # normal probe cleanup below, and this process never saves.
            target.rotation_mode = saved_mode
            target.matrix_basis = saved_basis
            end_rotation.mute = saved_mute
            if saved_auto_present:
                target.bone[limb_ik.AUTO_ALIGN_KEY] = saved_auto
            elif limb_ik.AUTO_ALIGN_KEY in target.bone:
                del target.bone[limb_ik.AUTO_ALIGN_KEY]
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()

    direct_metrics(armature, inventory)
    assert_deformed_mesh_equal(armature, skin_before, "Direct Auto Align reset")

    arm_rig = inventory["rigs"][("ARM", "L")]
    arm_target = armature.pose.bones[arm_rig["target"].name]
    target_basis = arm_target.matrix_basis.copy()
    upper = armature.pose.bones[arm_rig["chain"][0]]
    lower = armature.pose.bones[arm_rig["chain"][1]]
    inward = Vector(upper.head) - Vector(lower.tail)
    inward.normalize()
    moved_matrix = arm_target.matrix.copy()
    moved_matrix.translation += inward * 0.005
    arm_target.matrix = moved_matrix
    bpy.context.view_layer.update()
    target_error = (Vector(lower.tail) - Vector(arm_target.head)).length
    moved_alignment = pole_alignment(armature, arm_rig)
    if target_error > 5.0e-4 or moved_alignment is None or moved_alignment < 0.995:
        raise AssertionError(
            f"Direct target motion failed: target_error={target_error}, alignment={moved_alignment}"
        )
    arm_target.matrix_basis = target_basis
    bpy.context.view_layer.update()
    direct_metrics(armature, inventory)
    assert_deformed_mesh_equal(armature, skin_before, "Direct target reset")

    rebuild_result = bpy.ops.character_designer.limb_ik_rebuild()
    if rebuild_result != {"FINISHED"}:
        raise AssertionError(f"Direct Rebuild failed: {settings.last_message}")
    rebuilt, rebuilt_registry = assert_minimal_inventory(armature)
    rebuild_metrics = direct_metrics(armature, rebuilt)
    rebuild_control_metrics = control_acceptance_metrics(armature, rebuilt)
    rebuild_skin_metrics = assert_deformed_mesh_equal(armature, skin_before, "Direct Rebuild")
    if limb_ik._armature_digest(armature) != applied_digest:
        raise AssertionError("Direct Rebuild changed the applied source Rest geometry")

    remove_result = bpy.ops.character_designer.limb_ik_remove()
    if remove_result != {"FINISHED"}:
        raise AssertionError(f"Direct Remove failed: {settings.last_message}")
    empty = limb_ik._validate_inventory(armature)
    if empty["rigs"] or empty["bones"] or empty["records"]:
        raise AssertionError("Direct Remove left owned rig data")
    if any(
        key in armature.data
        for key in (
            limb_ik.ARMATURE_ID_KEY,
            limb_ik.SCHEMA_KEY,
            limb_ik.DIRECT_REST_KEY,
            limb_ik.SOURCE_WIDGETS_KEY,
        )
    ):
        raise AssertionError("Direct Remove left Armature ownership properties")
    restore_maxima = assert_source_rest_equal(armature, source_before, "Direct Remove")
    remove_skin_metrics = assert_deformed_mesh_equal(armature, skin_before, "Direct Remove")
    if limb_ik._armature_digest(armature) != source_digest_before:
        raise AssertionError("Direct Remove did not restore the exact source Rest digest")

    if shoes_object is not None and shoes_visibility is not None:
        shoes_object.hide_viewport = shoes_visibility[0]
        shoes_object.hide_set(shoes_visibility[1])

    disk_after = fingerprint(path)
    report = {
        "blender": bpy.app.version_string,
        "addon": list(character_designer.bl_info["version"]),
        "armature": armature.name,
        "opened_inventory": opened_summary,
        "readiness": readiness,
        "direct_build": {
            "operator_result": sorted(build_result),
            "schema": int(inventory["schema"]),
            "limbs": len(inventory["rigs"]),
            "generated_bones": len(inventory["bones"]),
            "rest_entries": len(registry["limbs"]),
            "start_metrics": start_metrics,
            "control_acceptance": build_control_metrics,
            "skin_identity": build_skin_metrics,
            "moved_left_arm_target_error": float(target_error),
            "moved_left_arm_alignment": float(moved_alignment),
            "auto_align": auto_align_metrics,
        },
        "direct_rebuild": {
            "operator_result": sorted(rebuild_result),
            "schema": int(rebuilt["schema"]),
            "generated_bones": len(rebuilt["bones"]),
            "rest_entries": len(rebuilt_registry["limbs"]),
            "start_metrics": rebuild_metrics,
            "control_acceptance": rebuild_control_metrics,
            "skin_identity": rebuild_skin_metrics,
        },
        "direct_remove": {
            "operator_result": sorted(remove_result),
            "source_rest_max_errors": restore_maxima,
            "source_digest_restored": True,
            "skin_restored": remove_skin_metrics,
        },
        "blend_dirty_after_memory_acceptance": bool(bpy.data.is_dirty),
        "disk_before": disk_before,
        "disk_after": disk_after,
        "disk_unchanged": disk_after == disk_before,
    }
    if not report["disk_unchanged"]:
        raise AssertionError(f"Input Blend changed: {disk_before} -> {disk_after}")
    print("REAL_X_DIRECT_PREROLL_BUILD_JSON=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("PASS in-memory real-X Direct Pre-Roll Build/Rebuild/Remove; input was never saved")


if __name__ == "__main__":
    main()
