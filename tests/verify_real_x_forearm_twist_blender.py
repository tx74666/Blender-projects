"""Disposable real-X runtime/visual acceptance; never overwrite X.blend.

Run with Blender --factory-startup -b --disable-autoexec --python-exit-code 1
--python this_file.py. Outputs are confined to .codex-backups/forearm-twist-probe.
"""

import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".codex-backups" / "forearm-twist-probe"
sys.path.insert(0, str(ROOT / "addons"))
sys.path.insert(0, str(ROOT / "tests"))
import character_designer
from character_designer import forearm_twist as twist, limb_ik
from character_designer.forearm_twist_math import desired_vertex, profile_ratio, twist_angle


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return {"size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns, "sha256": digest.hexdigest()}


def activate(obj):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for item in bpy.context.selected_objects:
        item.select_set(False)
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mesh_signature(obj):
    return {
        "vertices": [tuple(vertex.co) for vertex in obj.data.vertices],
        "edges": [tuple(edge.vertices) for edge in obj.data.edges],
        "polygons": [tuple(face.vertices) for face in obj.data.polygons],
        "groups": [(group.name, group.lock_weight) for group in obj.vertex_groups],
        "weights": [tuple((group.group, group.weight) for group in vertex.groups) for vertex in obj.data.vertices],
        "keys": {key.name: {"coordinates": [tuple(point.co) for point in key.data],
                            "value": key.value, "mute": key.mute, "relative": key.relative_key.name}
                 for key in obj.data.shape_keys.key_blocks},
        "modifiers": [(mod.name, mod.type, mod.show_viewport, mod.show_render) for mod in obj.modifiers],
    }


def skeleton_signature(armature):
    return {bone.name: {"rest": tuple(value for row in bone.matrix_local for value in row),
                        "parent": bone.parent.name if bone.parent else None, "deform": bone.use_deform,
                        "constraints": [(c.name, c.type, c.influence, c.mute) for c in armature.pose.bones[bone.name].constraints]}
            for bone in armature.data.bones}


def pose_channels(armature):
    return {bone.name: {"mode": bone.rotation_mode, "euler": tuple(bone.rotation_euler),
                        "quaternion": tuple(bone.rotation_quaternion), "axis_angle": tuple(bone.rotation_axis_angle),
                        "location": tuple(bone.location), "scale": tuple(bone.scale)}
            for bone in armature.pose.bones}


def verify_existing_fk(obj, armature):
    """The user's saved skeleton is immediately usable without building IK."""
    activate(obj)
    before_mesh = mesh_signature(obj)
    before_skeleton = skeleton_signature(armature)
    before_pose = pose_channels(armature)
    before_lock = bpy.context.scene.render.use_lock_interface
    assert twist.RECORD_KEY not in obj
    assert "CTRL_hand_IK.L" not in armature.pose.bones
    subdiv = next(mod for mod in obj.modifiers if mod.type == "SUBSURF")
    enabled = subdiv.show_viewport
    subdiv.show_viewport = False
    tick(obj)
    record = twist.start_test(bpy.context, obj, "L")
    assert record["target"] == "hand.L", record["target"]
    assert len(record["rings"]) == 7
    assert skeleton_signature(armature) == before_skeleton
    result = verify_pose(obj, armature, record)
    assert abs(result["twist_degrees"] - 90.0) < 0.01, result
    assert result["wrist_swing_degrees"] < 0.05, result
    assert result["pair_only_radial_error"] < 2e-5, result
    twist.set_ratio(bpy.context, 2, 0.40)
    assert twist._records(obj)["L"]["rings"][2]["ratio"] == 0.40
    twist.finish_test(bpy.context, confirm=False)
    subdiv.show_viewport = enabled
    tick(obj)
    assert twist._SESSION is None and twist.RECORD_KEY not in obj
    assert mesh_signature(obj) == before_mesh
    assert skeleton_signature(armature) == before_skeleton
    assert pose_channels(armature) == before_pose
    assert bpy.context.scene.render.use_lock_interface == before_lock
    result.update({"target": "hand.L", "original_rotation_mode": before_pose["hand.L"]["mode"],
                   "no_bones_or_modifiers_added": True, "cancel_restored_all_channels_and_data": True})
    return result


def evaluated_base(obj):
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    result = [vertex.co.copy() for vertex in mesh.vertices]
    evaluated.to_mesh_clear()
    assert len(result) == len(obj.data.vertices)
    return result


def tick(obj):
    bpy.context.view_layer.update()
    # Exercise the registered depsgraph handler, then an idempotent explicit refresh.
    assert not twist._ERRORS.get(obj.name), twist._ERRORS.get(obj.name)


def verify_pose(obj, armature, record):
    tick(obj)
    actual = evaluated_base(obj)
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated_armature = armature.evaluated_get(graph)
    to_arm = evaluated_armature.matrix_world.inverted() @ obj.evaluated_get(graph).matrix_world
    from_arm = to_arm.inverted()
    all_names = {bone.name for bone in armature.data.bones if bone.use_deform}
    group_names = {group.index: group.name for group in obj.vertex_groups if group.name in all_names}
    transforms = {name: evaluated_armature.pose.bones[name].matrix @ armature.data.bones[name].matrix_local.inverted()
                  for name in all_names}
    lower, hand = record["chain"][1:]
    lower_bone = armature.data.bones[lower]
    axis = (lower_bone.tail_local - lower_bone.head_local).normalized()
    pivot = armature.data.bones[hand].head_local
    angle = twist_angle(transforms[lower], transforms[hand], axis)
    relative = transforms[lower].to_quaternion().conjugated() @ transforms[hand].to_quaternion()
    swing = relative @ Quaternion(axis, -angle)
    swing_angle = min(swing.angle, math.tau - swing.angle)
    knots = [(0, 0)] + [(ring["position"], ring["ratio"]) for ring in record["rings"] if 0 < ring["position"] < 1] + [(1, 1)]
    basis = obj.data.shape_keys.reference_key
    positions = dict(zip(record["vertices"], record["positions"]))
    owned = set(record["vertices"])
    maximum = 0.0
    outside_maximum = 0.0
    radial_error = 0.0
    radial_count = 0
    for vertex in obj.data.vertices:
        weights = {group_names[group.group]: group.weight for group in vertex.groups if group.group in group_names and group.weight > 0}
        total = sum(weights.values())
        weights = {name: weight / total for name, weight in weights.items()} if total else {}
        point = to_arm @ basis.data[vertex.index].co
        if vertex.index in owned:
            ratio = profile_ratio(positions[vertex.index], knots)
            expected = desired_vertex(point, transforms, weights, lower, hand, axis, pivot, ratio, angle=angle)
        elif weights:
            expected = sum((weight * (transforms[name] @ point) for name, weight in weights.items()), Vector((0, 0, 0)))
        else:
            expected = point
        error = (actual[vertex.index] - from_arm @ expected).length
        if vertex.index in owned:
            maximum = max(maximum, error)
            if weights.get(lower, 0) + weights.get(hand, 0) > 1.0 - 1e-6:
                actual_local = transforms[lower].inverted() @ (to_arm @ actual[vertex.index])
                before = point - pivot
                after = actual_local - pivot
                before_radius = (before - axis * before.dot(axis)).length
                after_radius = (after - axis * after.dot(axis)).length
                radial_error = max(radial_error, abs(after_radius - before_radius))
                radial_count += 1
        else:
            outside_maximum = max(outside_maximum, error)
    assert maximum < 2e-5, maximum
    assert outside_maximum < 2e-5, outside_maximum
    first = [tuple(point.co) for point in obj.data.shape_keys.key_blocks[record["key"]].data]
    for _ in range(5):
        twist.update_runtime(bpy.context.scene, graph)
    assert first == [tuple(point.co) for point in obj.data.shape_keys.key_blocks[record["key"]].data]
    return {"twist_degrees": math.degrees(angle), "wrist_swing_degrees": math.degrees(swing_angle), "corrected_coordinate_error": maximum,
            "outside_coordinate_error": outside_maximum, "pair_only_radial_error": radial_error,
            "pair_only_vertex_count": radial_count, "no_accumulation": True}


def setup_camera(obj, armature):
    scene = bpy.context.scene
    for item in scene.objects:
        item.hide_render = item != obj
    data = bpy.data.cameras.new("Forearm Twist Review Camera")
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    lower = armature.pose.bones["forearm.L"]
    hand = armature.pose.bones["hand.L"]
    elbow = armature.matrix_world @ lower.head
    wrist = armature.matrix_world @ hand.head
    hand_end = armature.matrix_world @ hand.tail
    right = (wrist - elbow).normalized()
    up = Vector((0, 0, 1))
    up = (up - right * up.dot(right)).normalized()
    front = right.cross(up).normalized()
    target = (elbow + hand_end) * 0.5
    camera.location = target + front
    camera.rotation_euler = Matrix((right, up, front)).transposed().to_euler()
    data.type = "ORTHO"
    data.ortho_scale = (hand_end - elbow).length * 1.32
    data.lens = 50
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 650
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (0.58, 0.68, 0.80)
    scene.display.shading.background_type = "WORLD"
    scene.world.color = (0.055, 0.065, 0.08)
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.5
    scene.display.shading.curvature_valley_factor = 1.2
    scene.display.shading.show_object_outline = True
    return camera


def wrist_radius_stats(obj, armature, record):
    """Actual evaluated pure-twist radial loss on pair-only distal vertices."""
    subdiv = next(mod for mod in obj.modifiers if mod.type == "SUBSURF")
    enabled = subdiv.show_viewport
    subdiv.show_viewport = False
    tick(obj)
    actual = evaluated_base(obj)
    graph = bpy.context.evaluated_depsgraph_get()
    arm = armature.evaluated_get(graph)
    to_arm = arm.matrix_world.inverted() @ obj.evaluated_get(graph).matrix_world
    lower_name, hand_name = record["chain"][1:]
    lower = armature.data.bones[lower_name]
    axis = (lower.tail_local - lower.head_local).normalized()
    pivot = armature.data.bones[hand_name].head_local
    unpose = (arm.pose.bones[lower_name].matrix @ lower.matrix_local.inverted()).inverted()
    weights = twist._weights(obj, armature, record["vertices"])
    basis = obj.data.shape_keys.reference_key
    ratios = []
    for index, position in zip(record["vertices"], record["positions"]):
        if position < 0.8 or weights[index].get(lower_name, 0) + weights[index].get(hand_name, 0) < 1 - 1e-6:
            continue
        before = to_arm @ basis.data[index].co - pivot
        after = unpose @ (to_arm @ actual[index]) - pivot
        before_radius = (before - axis * before.dot(axis)).length
        after_radius = (after - axis * after.dot(axis)).length
        ratios.append(after_radius / before_radius)
    assert ratios
    subdiv.show_viewport = enabled
    tick(obj)
    return {"count": len(ratios), "minimum_radius_ratio": min(ratios), "maximum_radius_ratio": max(ratios),
            "mean_radius_ratio": sum(ratios) / len(ratios)}


def render_image(name):
    path = OUT / name
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    blend_path = ROOT / "X.blend"
    before_file = fingerprint(blend_path)
    bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False, use_scripts=False)
    character_designer.register()
    obj = bpy.data.objects["Cosha"]
    armature = obj.modifiers[0].object
    fk_result = verify_existing_fk(obj, armature)
    activate(armature)
    assert bpy.ops.character_designer.limb_ik_analyze() == {"FINISHED"}
    settings = bpy.context.window_manager.character_designer_limb_ik
    settings.selected_limb = "LEFT_ARM"
    settings.build_method = "ROLL_DECOUPLED"
    assert bpy.ops.character_designer.limb_ik_build_selected() == {"FINISHED"}, settings.last_message
    activate(obj)
    original_mesh = mesh_signature(obj)
    original_skeleton = skeleton_signature(armature)
    original_target = armature.pose.bones["CTRL_hand_IK.L"].rotation_euler.copy()
    subdiv = next(mod for mod in obj.modifiers if mod.type == "SUBSURF")
    subdiv.show_viewport = False
    tick(obj)
    record = twist.start_test(bpy.context, obj, "L")
    assert len(record["rings"]) == 7
    positions_by_vertex = dict(zip(record["vertices"], record["positions"]))
    for ring in record["rings"]:
        assert all(positions_by_vertex[index] == ring["position"] for index in ring["vertices"])
    assert skeleton_signature(armature) == original_skeleton
    poses = {}
    report = {"source": str(blend_path), "source_before": before_file, "existing_fk": fk_result,
              "rings": [{"position": ring["position"], "count": len(ring["vertices"])} for ring in record["rings"]],
              "corrected_vertices": len(record["vertices"]), "poses": {}}
    for degrees in (90, 45, -45, -90, 0):
        twist._test_pose(bpy.context, math.radians(degrees))
        poses[degrees] = armature.pose.bones[record["target"]].rotation_euler.copy()
        result = verify_pose(obj, armature, record)
        assert abs(result["twist_degrees"] - degrees) < 0.01
        assert result["wrist_swing_degrees"] < 0.05, result
        assert result["pair_only_radial_error"] < 2e-5, result
        report["poses"][str(degrees)] = result
    twist._test_pose(bpy.context, math.pi / 2)
    twist.set_ratio(bpy.context, 2, 0.35)
    record = twist._records(obj)["L"]
    assert record["rings"][2]["ratio"] == 0.35
    report["poses"]["custom90"] = verify_pose(obj, armature, record)
    twist.finish_test(bpy.context, confirm=True)
    assert (Vector(armature.pose.bones[record["target"]].rotation_euler) - Vector(original_target)).length < 1e-7
    assert twist._SESSION is None
    target = armature.pose.bones[record["target"]]
    for degrees in (-90, -45, 45, 90):
        target.rotation_euler = poses[degrees]
        report["poses"]["confirmed" + str(degrees)] = verify_pose(obj, armature, record)
    target.rotation_euler = poses[45]
    target.rotation_euler.x += 0.30
    target.location.y += 0.075
    report["poses"]["bent_elbow_and_wrist"] = verify_pose(obj, armature, record)
    target.location.y -= 0.075
    target.rotation_euler = original_target
    tick(obj)
    subdiv.show_viewport = original_mesh["modifiers"][1][2]
    current_mesh = mesh_signature(obj)
    for field in ("vertices", "edges", "polygons", "groups", "weights", "modifiers"):
        assert current_mesh[field] == original_mesh[field], field
    for name, value in original_mesh["keys"].items():
        assert current_mesh["keys"][name] == value, name
    key = obj.data.shape_keys.key_blocks[record["key"]]
    selected = set(record["vertices"])
    assert all(tuple(point.co) == original_mesh["keys"]["Basis"]["coordinates"][index]
               for index, point in enumerate(key.data) if index not in selected)
    assert skeleton_signature(armature) == original_skeleton
    report["protected_data_unchanged"] = True
    setup_camera(obj, armature)
    report["images"] = {"rest": render_image("X-forearm-rest.png")}
    target.rotation_euler = poses[90]
    tick(obj)
    records = twist._records(obj)
    records["L"]["enabled"] = False
    twist._write_records(obj, records)
    twist.update_runtime(bpy.context.scene)
    report["original90_radius"] = wrist_radius_stats(obj, armature, record)
    report["images"]["original90"] = render_image("X-forearm-original90.png")
    records["L"]["enabled"] = True
    twist._write_records(obj, records)
    twist.update_runtime(bpy.context.scene)
    report["corrected90_radius"] = wrist_radius_stats(obj, armature, record)
    assert report["corrected90_radius"]["minimum_radius_ratio"] > 0.999
    assert report["original90_radius"]["minimum_radius_ratio"] < 0.9
    report["images"]["corrected90"] = render_image("X-forearm-corrected90.png")
    target.rotation_euler = poses[45]
    target.rotation_euler.x += 0.30
    target.location.y += 0.075
    tick(obj)
    report["images"]["bent"] = render_image("X-forearm-bent45.png")
    target.location.y -= 0.075
    target.rotation_euler = poses[90]
    tick(obj)
    preview = OUT / "X-forearm-twist-preview.blend"
    assert preview.resolve() != blend_path.resolve() and OUT.resolve() in preview.resolve().parents
    bpy.ops.wm.save_as_mainfile(filepath=str(preview), copy=True)
    report["preview"] = str(preview)
    saved_record = json.loads(obj[twist.RECORD_KEY])
    bpy.ops.wm.open_mainfile(filepath=str(preview), load_ui=False, use_scripts=False)
    obj = bpy.data.objects["Cosha"]
    armature = obj.modifiers[0].object
    assert twist._records(obj) == saved_record
    subdiv = next(mod for mod in obj.modifiers if mod.type == "SUBSURF")
    subdiv.show_viewport = False
    report["reopened90"] = verify_pose(obj, armature, twist._records(obj)["L"])
    subdiv.show_viewport = original_mesh["modifiers"][1][2]
    report["source_after"] = fingerprint(blend_path)
    assert report["source_after"] == before_file
    (OUT / "real-x-verification.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    (OUT / "real-x-verification-error.txt").unlink(missing_ok=True)
    print("REAL_X_FOREARM_TWIST_VERIFICATION=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "real-x-verification-error.txt").write_text(traceback.format_exc(), encoding="utf8")
        raise
