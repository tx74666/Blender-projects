"""Real-X FK calibration through generated IK Build/Rebuild/Remove/Build.

Loads production X.blend read-only into a disposable Blender process. Never
saves any blend. Run --background --factory-startup --disable-autoexec
--python-exit-code 1 --python tests/test_real_x_forearm_twist_rig_lifecycle_blender.py.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
if "character_designer" not in sys.modules:
    sys.path.insert(0, str(ROOT / "addons"))
import character_designer
from character_designer import forearm_twist as runtime, limb_ik
from character_designer.forearm_twist_math import desired_vertex, profile_ratio, twist_angle


def digest():
    return hashlib.sha256((ROOT / "X.blend").read_bytes()).hexdigest()


def activate(obj):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for current in bpy.context.selected_objects:
        current.select_set(False)
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def source_snapshot(obj):
    basis = obj.data.shape_keys.reference_key
    return {"basis": tuple(tuple(point.co) for point in basis.data),
            "edges": tuple(tuple(edge.vertices) for edge in obj.data.edges),
            "faces": tuple(tuple(face.vertices) for face in obj.data.polygons),
            "groups": tuple(group.name for group in obj.vertex_groups),
            "weights": tuple(tuple((group.group, group.weight) for group in vertex.groups) for vertex in obj.data.vertices),
            "modifiers": tuple((mod.name, mod.type, mod.show_viewport, mod.show_render) for mod in obj.modifiers),
            "artist_keys": {key.name: (key.value, key.mute, key.relative_key.name, tuple(tuple(point.co) for point in key.data))
                            for key in obj.data.shape_keys.key_blocks if not key.name.startswith(runtime.KEY_PREFIX)}}


def ratios(obj):
    return {side: {tuple(sorted(ring["vertices"])): ring["ratio"] for ring in record["rings"]}
            for side, record in runtime._records(obj).items()}


def rest_snapshot(armature):
    return {bone.name: {"matrix": tuple(value for row in bone.matrix_local for value in row),
                        "head": tuple(bone.head_local), "tail": tuple(bone.tail_local)}
            for bone in armature.data.bones if bone.use_deform}


def rest_changes(before, after):
    return {name: {"matrix_max": max(abs(a - b) for a, b in zip(old["matrix"], after[name]["matrix"])),
                   "head_delta": (Vector(old["head"]) - Vector(after[name]["head"])).length,
                   "tail_delta": (Vector(old["tail"]) - Vector(after[name]["tail"])).length}
            for name, old in before.items() if name in after and
            max(abs(a - b) for a, b in zip(old["matrix"], after[name]["matrix"])) > 1.0e-5}


def current_targets(armature):
    inventory = limb_ik._validate_inventory(armature)
    return {side: armature.pose.bones[inventory["rigs"][("ARM", side)]["target"].name
                                    if ("ARM", side) in inventory["rigs"] else "hand." + side]
            for side in ("L", "R")}


def independent_input_mix(obj, graph):
    keys = obj.data.shape_keys
    basis = keys.reference_key
    evaluated = keys.evaluated_get(graph)
    managed = {record["key"] for record in runtime._records(obj).values()}
    result = [point.co.copy() for point in basis.data]
    for key in keys.key_blocks:
        if key == basis or key.name in managed or key.mute:
            continue
        value = evaluated.key_blocks[key.name].value
        if abs(value) < 1.0e-12:
            continue
        group = obj.vertex_groups.get(key.vertex_group) if key.vertex_group else None
        for index, point in enumerate(key.data):
            mask = 1.0 if not key.vertex_group else next((entry.weight for entry in obj.data.vertices[index].groups
                                                       if group is not None and entry.group == group.index), 0.0)
            result[index] += value * mask * (point.co - key.relative_key.data[index].co)
    return result


def verify_geometry(obj, armature, label):
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated_arm = armature.evaluated_get(graph)
    evaluated_obj = obj.evaluated_get(graph)
    data = evaluated_obj.to_mesh()
    try:
        actual = [vertex.co.copy() for vertex in data.vertices]
    finally:
        evaluated_obj.to_mesh_clear()
    assert len(actual) == len(obj.data.vertices)
    to_arm = evaluated_arm.matrix_world.inverted() @ evaluated_obj.matrix_world
    from_arm = to_arm.inverted()
    transforms = {bone.name: evaluated_arm.pose.bones[bone.name].matrix @ bone.matrix_local.inverted()
                  for bone in armature.data.bones if bone.use_deform}
    groups = {group.index: group.name for group in obj.vertex_groups if group.name in transforms}
    source = independent_input_mix(obj, graph)
    records = runtime._records(obj)
    parameters, owners = {}, {}
    for side, record in records.items():
        lower, hand = record["chain"][1:]
        lower_bone = armature.data.bones[lower]
        axis = (lower_bone.tail_local - lower_bone.head_local).normalized()
        pivot = armature.data.bones[hand].head_local
        angle = twist_angle(transforms[lower], transforms[hand], axis)
        knots = [(0.0, 0.0)] + [(ring["position"], ring["ratio"]) for ring in record["rings"]
                               if 1.0e-6 < ring["position"] < 1.0 - 1.0e-6] + [(1.0, 1.0)]
        parameters[side] = lower, hand, axis, pivot, angle, knots
        for index, position in zip(record["vertices"], record["positions"]):
            assert index not in owners
            owners[index] = side, position
    maximum, outside_maximum, hand_maximum, hand_count = 0.0, 0.0, 0.0, 0
    for index, vertex in enumerate(obj.data.vertices):
        weights = {groups[group.group]: group.weight for group in vertex.groups if group.group in groups and group.weight > 0}
        total = sum(weights.values())
        weights = {name: weight / total for name, weight in weights.items()} if total else {}
        point = to_arm @ source[index]
        if index in owners:
            side, position = owners[index]
            lower, hand, axis, pivot, angle, knots = parameters[side]
            expected = desired_vertex(point, transforms, weights, lower, hand, axis, pivot,
                                      profile_ratio(position, knots), angle=angle)
        else:
            expected = sum((weight * (transforms[name] @ point) for name, weight in weights.items()), Vector()) if weights else point
        error = (actual[index] - from_arm @ expected).length
        maximum = max(maximum, error)
        if index not in owners:
            outside_maximum = max(outside_maximum, error)
        for side in ("L", "R"):
            if weights.get("hand." + side, 0.0) > 1.0 - 1.0e-6:
                hand_count += 1
                hand_maximum = max(hand_maximum, (actual[index] - from_arm @ (transforms["hand." + side] @ point)).length)
    result = {"label": label, "max_vertex_error": maximum, "outside_error": outside_maximum,
              "hand_only_error": hand_maximum, "hand_only_count": hand_count,
              "angles": {side: math.degrees(values[4]) for side, values in parameters.items()},
              "runtime_error": runtime._ERRORS.get(obj.name),
              "key_mutes": {side: obj.data.shape_keys.key_blocks[record["key"]].mute for side, record in records.items()}}
    print("LIFECYCLE_GEOMETRY=" + json.dumps(result, sort_keys=True), flush=True)
    # Evaluate actual vertices before these assertions: a paused key is not
    # merely a status issue; it demonstrably falls back to the old LBS surface.
    assert maximum < 2.5e-5, result
    assert hand_count > 0 and hand_maximum < 2.5e-5, result
    assert not result["runtime_error"] and not any(result["key_mutes"].values()), result
    return result


def motion_checks(obj, armature, label, saved_ratios, protected):
    activate(obj)
    results = []
    poses = (((45, 0.0),) if "--legacy-rest-guard" in sys.argv else
             ((45, math.radians(25.0)), (-45, math.radians(25.0))) if "--bend-only" in sys.argv else
             ((45, 0.0), (-45, 0.0), (90, 0.0), (-90, 0.0), (45, math.radians(25.0)), (-45, math.radians(25.0))))
    for degrees, bend in poses:
        targets = current_targets(armature)
        requested = {}
        for side, target in targets.items():
            target.rotation_mode = "XYZ"
            baseline = Quaternion((1, 0, 0), bend) @ Quaternion((0, 0, 1), 0.08 if bend else 0.0)
            # R Y Y rotates about the controller's current local Y, i.e. a
            # right-multiplied local increment after the existing wrist bend.
            local_y = Quaternion((0, 1, 0), math.radians(degrees) * (1 if side == "L" else -1))
            target.rotation_euler = (baseline @ local_y).to_euler("XYZ")
            requested[side] = tuple(target.rotation_euler)
        armature.update_tag(refresh={"OBJECT"})
        results.append(verify_geometry(obj, armature, f"{label}/{degrees}/bend={math.degrees(bend)}"))
        assert all(tuple(targets[side].rotation_euler) == values for side, values in requested.items()), "Runtime changed hand controller channels"
        assert ratios(obj) == saved_ratios, "Rig lifecycle changed the artist's saved ring shares"
        assert source_snapshot(obj) == protected, "Rig lifecycle rebound or modified source weights/geometry/keys/modifiers"
    # Rig generation requires neutral animator channels; keep this setup step
    # separate from the tested nonzero poses and verify no calibration recapture.
    for target in current_targets(armature).values():
        target.rotation_euler = (0.0, 0.0, 0.0)
    armature.update_tag(refresh={"OBJECT"})
    bpy.context.view_layer.update()
    return results


def rig_operation(obj, armature, method, operation):
    activate(armature)
    bpy.ops.object.mode_set(mode="POSE")
    settings = bpy.context.window_manager.character_designer_limb_ik
    settings.armature = armature
    before = rest_snapshot(armature)
    if operation in {"BUILD", "REBUILD"}:
        assert bpy.ops.character_designer.limb_ik_analyze() == {"FINISHED"}, settings.last_message
        settings.build_method = method
    operator = {"BUILD": bpy.ops.character_designer.limb_ik_build_all,
                "REBUILD": bpy.ops.character_designer.limb_ik_rebuild,
                "REMOVE": bpy.ops.character_designer.limb_ik_remove}[operation]
    assert operator() == {"FINISHED"}, settings.last_message
    bpy.context.view_layer.update()
    changes = rest_changes(before, rest_snapshot(armature))
    print("LIFECYCLE_REST_CHANGES=" + json.dumps({"method": method, "operation": operation, "bones": changes}, sort_keys=True), flush=True)
    activate(obj)
    return changes


def run_method(method):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "X.blend"), load_ui=False, use_scripts=False)
    obj = bpy.data.objects["Cosha"]
    armature = obj.modifiers[0].object
    activate(obj)
    assert not limb_ik._validate_inventory(armature)["rigs"], "Saved source must begin with the existing FK skeleton"
    # The artist may already have saved an FK calibration. Reset only this
    # disposable in-memory fixture before exercising a fresh complete lifecycle.
    for side in tuple(runtime._records(obj)):
        runtime.remove_calibration(bpy.context, obj, side)
    for modifier in obj.modifiers[1:]:
        modifier.show_viewport = False
    runtime.start_test(bpy.context, obj, "L", symmetry=True)
    runtime.set_ratio(bpy.context, 2, 0.68)
    runtime.set_ratio(bpy.context, 4, 0.87)
    runtime.finish_test(bpy.context, True)
    saved_ratios = ratios(obj)
    protected = source_snapshot(obj)
    results = {"FK": motion_checks(obj, armature, method + "/FK", saved_ratios, protected)}
    for stage, operation in (("BUILD", "BUILD"), ("REBUILD", "REBUILD"), ("REMOVED_FK", "REMOVE"), ("BUILD_AGAIN", "BUILD")):
        results[stage + "_rest"] = rig_operation(obj, armature, method, operation)
        results[stage] = motion_checks(obj, armature, method + "/" + stage, saved_ratios, protected)
    assert len(obj.modifiers) == len(protected["modifiers"])
    return results


def main():
    before = digest()
    character_designer.register()
    legacy_guard = "--legacy-rest-guard" in sys.argv
    if legacy_guard:
        # Isolated negative control: run the unchanged strict core directly,
        # bypassing only the new automatic rebind wrapper. No source edit.
        runtime._calculate_object = runtime._calculate_records
    try:
        methods = (("ROLL_DECOUPLED",) if "--stable-only" in sys.argv else
                   ("DIRECT_PREROLL",) if "--direct-only" in sys.argv or legacy_guard else
                   ("DIRECT_PREROLL", "ROLL_DECOUPLED"))
        try:
            results = {method: run_method(method) for method in methods}
        except AssertionError as error:
            details = error.args[0] if error.args else None
            if not (legacy_guard and isinstance(details, dict)
                    and "/BUILD/45/" in details.get("label", "")
                    and details.get("max_vertex_error", 0.0) > 1.0e-3
                    and details.get("runtime_error")
                    and all(details.get("key_mutes", {}).values())):
                raise
            print("REAL_X_LEGACY_REST_GUARD_FAILURE_REPRODUCED=" + str(error), flush=True)
            return
        assert not legacy_guard, "Negative control unexpectedly preserved calibration without rebind"
        print("REAL_X_FOREARM_TWIST_RIG_LIFECYCLE_PASS=" + json.dumps({"methods": list(results), "production_sha256": before}), flush=True)
    finally:
        assert digest() == before, "Production X.blend changed on disk"


if __name__ == "__main__":
    main()
