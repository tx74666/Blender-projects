"""Factory-only native proof of connected versus disconnected WORLD transfer.

This disposable fixture does not open artist files or import installed add-ons.
It proves a narrowly specified native constraint graph, not production, animation,
Original-mode, physics-solver, Shape Key, or exporter compatibility.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback

import bpy
from mathutils import Euler, Vector


def value(item):
    if item is None or isinstance(item, (str, bool, int)):
        return item
    if isinstance(item, float):
        if not math.isfinite(item):
            raise RuntimeError("Nonfinite native RNA")
        return item
    if isinstance(item, bpy.types.ID):
        return {"type": item.bl_rna.identifier, "name": item.name_full,
                "library": item.library.filepath if item.library else None}
    if isinstance(item, set):
        return sorted(item)
    try:
        return [value(member) for member in item]
    except TypeError:
        raise RuntimeError("Unsupported native RNA: " + type(item).__name__)


def rna(owner):
    result = {}
    for prop in owner.bl_rna.properties:
        name = prop.identifier
        if name == "rna_type" or prop.is_readonly or prop.type == "COLLECTION":
            continue
        result[name] = value(getattr(owner, name))
    return result


def channels(rig):
    return {bone.name: {key: value(getattr(bone, key)) for key in (
        "rotation_mode", "location", "rotation_euler", "rotation_quaternion",
        "rotation_axis_angle", "scale", "lock_location", "lock_rotation",
        "lock_rotation_w", "lock_rotations_4d", "lock_scale")}
        for bone in rig.pose.bones}


def restore_channels(rig, saved):
    for name, fields in saved.items():
        for key, item in fields.items():
            setattr(rig.pose.bones[name], key, item)


def rest(rig):
    return [{"name": bone.name, "parent": bone.parent.name if bone.parent else None,
             "head": value(bone.head_local), "tail": value(bone.tail_local),
             "matrix": value(bone.matrix_local), "length": bone.length,
             "use_connect": bone.use_connect, "use_deform": bone.use_deform,
             "inherit_scale": bone.inherit_scale,
             "use_inherit_rotation": bone.use_inherit_rotation,
             "use_local_location": bone.use_local_location}
            for bone in rig.data.bones]


def graph(rig):
    return {bone.name: [rna(constraint) for constraint in bone.constraints]
            for bone in rig.pose.bones}


def drivers(rig):
    animation = rig.animation_data
    return [] if not animation else [{
        "path": curve.data_path, "index": curve.array_index, "mute": curve.mute,
        "driver": rna(curve.driver),
        "variables": [{"rna": rna(var), "targets": [rna(target) for target in var.targets]}
                      for var in curve.driver.variables]}
        for curve in animation.drivers]


def update(rigs):
    for rig in rigs:
        rig.update_tag()
    bpy.context.view_layer.update()


def mesh_points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh(preserve_all_data_layers=True,
                             depsgraph=bpy.context.evaluated_depsgraph_get())
    try:
        return [value(evaluated.matrix_world @ vertex.co) for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def snapshot(rig, skin):
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {"rest": rest(rig), "channels": channels(rig), "constraints": graph(rig),
            "drivers": drivers(rig), "object_matrix": value(rig.matrix_world),
            "pose": {bone.name: {"world": value(evaluated.matrix_world @ bone.matrix),
                                  "pose": value(bone.matrix), "basis": value(bone.matrix_basis),
                                  "head_world": value(evaluated.matrix_world @ bone.head),
                                  "tail_world": value(evaluated.matrix_world @ bone.tail)}
                     for bone in evaluated.pose.bones},
            "raw_vertices": [value(vertex.co) for vertex in skin.data.vertices],
            "weights": [[(entry.group, entry.weight) for entry in vertex.groups]
                        for vertex in skin.data.vertices],
            "group_names": [(group.index, group.name) for group in skin.vertex_groups],
            "armature": rna(skin.modifiers[0]), "skin_world": mesh_points(skin)}


def point_error(left, right):
    assert len(left) == len(right)
    return max((Vector(a) - Vector(b)).length for a, b in zip(left, right))


def matrix_error(left, right):
    return max(abs(left[row][col] - right[row][col])
               for row in range(4) for col in range(4))


def connect(rig, mapping):
    assert bpy.context.mode == "OBJECT"
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        for name, flag in mapping.items():
            rig.data.edit_bones[name].use_connect = flag
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")


def make_rig(name, layers, connected):
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(rig)
    rig.location = (0.4, -0.2, 0.15)
    rig.rotation_euler = (0.05, 0.03, -0.04)
    rig.scale = (1.1, 1.1, 1.1)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    root = data.edit_bones.new("Waist")
    root.head, root.tail = (0, -1, 0), (0, 0, 0)
    root.use_deform = False
    for layer in layers:
        parent = root
        for index in range(3):
            bone = data.edit_bones.new(f"{layer}_{index + 1:02d}")
            bone.head, bone.tail = (0, index, 0), (0, index + 1, 0)
            bone.parent = parent
            bone.use_connect = connected
            bone.use_deform = layer in {"DEF", "Driver"}
            bone.inherit_scale = "FULL"
            parent = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
    return rig


def make_skin(name, rig, layer):
    points = [(x, segment + y, z) for segment in range(3)
              for x, y, z in [(-0.15, 0.1, 0), (0.18, 0.5, 0.1), (0, 0.9, -0.14)]]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], [])
    skin = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(skin)
    skin.matrix_world = rig.matrix_world.copy()
    for segment in range(3):
        group = skin.vertex_groups.new(name=f"{layer}_{segment + 1:02d}")
        group.add(list(range(segment * 3, segment * 3 + 3)), 1.0, "REPLACE")
    armature = skin.modifiers.new("Native Armature", "ARMATURE")
    armature.object = rig
    armature.use_deform_preserve_volume = True
    armature.use_vertex_groups = True
    armature.use_bone_envelopes = False
    return skin


def influence(constraint, rig):
    driver = constraint.driver_add("influence").driver
    driver.type = "AVERAGE"
    variable = driver.variables.new()
    variable.name, variable.type = "physics", "SINGLE_PROP"
    variable.targets[0].id = rig
    variable.targets[0].data_path = '["physics_influence"]'


def main(report):
    assert bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath
    assert "--disable-autoexec" in sys.argv and bpy.app.version[:2] == (5, 1)
    bpy.context.preferences.use_preferences_save = False
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    rig = make_rig("QA Connected Transfer Rig", ("Manual", "PHYS", "DEF"), True)
    helper = make_rig("QA Independent Driver Rig", ("Driver",), False)
    update((rig, helper))
    skin = make_skin("QA DEF Native Skin", rig, "DEF")
    driver_skin = make_skin("QA Driver Native Skin", helper, "Driver")
    rig["physics_influence"] = 0.0
    for index in range(3):
        bone = rig.pose.bones[f"DEF_{index + 1:02d}"]
        manual = bone.constraints.new("COPY_TRANSFORMS")
        manual.name, manual.target, manual.subtarget = "Skirt manual pose", rig, f"Manual_{index + 1:02d}"
        manual.owner_space = manual.target_space = "LOCAL"
        physics = bone.constraints.new("COPY_ROTATION")
        physics.name, physics.target, physics.subtarget = "Skirt physics delta", rig, f"PHYS_{index + 1:02d}"
        physics.owner_space = physics.target_space = "LOCAL"
        physics.mix_mode = "BEFORE"
        influence(physics, rig)
        manual.active = True
        physics.active = False
    update((rig, helper))
    original = snapshot(rig, skin)
    original_helper_channels = channels(helper)
    original_flags = {bone.name: bone.use_connect for bone in rig.data.bones}
    changed_flags = {f"{layer}_{index + 1:02d}": False
                     for layer in ("PHYS", "DEF") for index in range(3)}
    added = []
    report.update(runtime=bpy.app.version_string, source_file_never_opened=True,
                  saved_scene=False, production_compatibility_proved=False,
                  fixture="Three segments; LOCAL manual REPLACE + LOCAL physics rotation BEFORE; native DQ skin",
                  initial=original, driver_initial=snapshot(helper, driver_skin), samples={})
    try:
        neutral = snapshot(rig, skin)
        for index in range(3):
            bone = rig.pose.bones[f"Manual_{index + 1:02d}"]
            bone.rotation_euler = (0.13 * (index + 1), -0.08, 0.11 - index * 0.03)
            bone.scale = (1.03, 0.97, 1.02)
        update((rig, helper))
        connected_manual = snapshot(rig, skin)
        connect(rig, changed_flags)
        update((rig, helper))
        disconnected_manual = snapshot(rig, skin)
        stripped = [{key: item for key, item in bone.items() if key != "use_connect"}
                    for bone in rest(rig)]
        original_stripped = [{key: item for key, item in bone.items() if key != "use_connect"}
                             for bone in original["rest"]]
        assert stripped == original_stripped, "Disconnect changed Rest beyond flags"
        manual_error = point_error(connected_manual["skin_world"], disconnected_manual["skin_world"])
        assert manual_error < 2e-6, "Manual skin changed after disconnect"
        assert connected_manual["channels"] == disconnected_manual["channels"]
        assert connected_manual["drivers"] == disconnected_manual["drivers"]
        assert connected_manual["weights"] == disconnected_manual["weights"]
        restore_channels(rig, original["channels"])
        rig["physics_influence"] = 1.0
        connect(rig, original_flags)
        update((rig, helper))
        neutral_auto_connected = snapshot(rig, skin)
        connect(rig, changed_flags)
        update((rig, helper))
        neutral_auto_disconnected = snapshot(rig, skin)
        neutral_error = point_error(neutral_auto_connected["skin_world"], neutral_auto_disconnected["skin_world"])
        assert neutral_error < 2e-6
        for index in range(3):
            target = helper.pose.bones[f"Driver_{index + 1:02d}"]
            target.location = (0.18 + index * 0.025, 0.06, -0.11 + index * 0.01)
            target.rotation_euler = (0.09, 0.17 + index * 0.03, -0.13)
            target.scale = (1.08, 0.92, 1.04)
        for index in range(3):
            for layer, target, subtarget in (
                ("PHYS", helper, f"Driver_{index + 1:02d}"),
                ("DEF", rig, f"PHYS_{index + 1:02d}")):
                bone = rig.pose.bones[f"{layer}_{index + 1:02d}"]
                constraint = bone.constraints.new("COPY_TRANSFORMS")
                constraint.name = "QA Full World Transfer"
                constraint.target, constraint.subtarget = target, subtarget
                constraint.owner_space = constraint.target_space = "WORLD"
                constraint.mix_mode = "REPLACE"
                influence(constraint, rig)
                added.append((bone.name, constraint))
                for previous, saved in zip(bone.constraints, original["constraints"][bone.name]):
                    previous.active = saved["active"]
                constraint.active = False
        connect(rig, original_flags)
        update((rig, helper))
        connected_world = snapshot(rig, skin)
        connect(rig, changed_flags)
        update((rig, helper))
        disconnected_world = snapshot(rig, skin)
        helper_world = snapshot(helper, driver_skin)
        comparisons = []
        for index in range(3):
            target = helper_world["pose"][f"Driver_{index + 1:02d}"]
            entry = {"segment": index + 1, "target_world": target["world"]}
            for layer in ("PHYS", "DEF"):
                name = f"{layer}_{index + 1:02d}"
                for label, sample in (("connected", connected_world), ("disconnected", disconnected_world)):
                    pose = sample["pose"][name]
                    entry[f"{layer}_{label}_matrix_max"] = matrix_error(pose["world"], target["world"])
                    entry[f"{layer}_{label}_head_distance"] = (Vector(pose["head_world"]) - Vector(target["head_world"])).length
            comparisons.append(entry)
        world_error = max(entry[f"{layer}_disconnected_matrix_max"]
                          for entry in comparisons for layer in ("PHYS", "DEF"))
        skin_error = point_error(disconnected_world["skin_world"], helper_world["skin_world"])
        connected_skin_error = point_error(connected_world["skin_world"], helper_world["skin_world"])
        assert world_error < 3e-6, "Disconnected WORLD matrix did not match independent helper"
        assert skin_error < 3e-6, "Disconnected native ARM skin did not match helper skin"
        assert comparisons[1]["PHYS_connected_head_distance"] > 0.05
        assert comparisons[1]["DEF_connected_head_distance"] > 0.05
        # Driver zero must keep the existing manual graph even with the late WORLD constraint.
        rig["physics_influence"] = 0.0
        for name, fields in disconnected_manual["channels"].items():
            for key, item in fields.items():
                setattr(rig.pose.bones[name], key, item)
        update((rig, helper))
        manual_with_world_disabled = snapshot(rig, skin)
        disabled_error = point_error(manual_with_world_disabled["skin_world"], disconnected_manual["skin_world"])
        assert disabled_error < 2e-6
        report["samples"] = {"neutral": neutral, "manual_connected": connected_manual,
            "manual_disconnected": disconnected_manual, "neutral_auto_connected": neutral_auto_connected,
            "neutral_auto_disconnected": neutral_auto_disconnected, "world_connected": connected_world,
            "world_disconnected": disconnected_world, "helper_target": helper_world,
            "manual_with_world_disabled": manual_with_world_disabled}
        report["scalars"] = {"manual_disconnect_skin_max_m": manual_error,
            "neutral_auto_disconnect_skin_max_m": neutral_error,
            "world_disconnected_matrix_max": world_error,
            "world_disconnected_skin_max_m": skin_error,
            "world_connected_skin_max_m": connected_skin_error,
            "manual_world_disabled_skin_max_m": disabled_error}
        report["segment_comparison"] = comparisons
        # Explicit failure injection: exercise the same cleanup with mutated flags/constraints/channels.
        try:
            rig.pose.bones["DEF_02"].location.x += 0.3
            raise RuntimeError("QA intentional late failure")
        except RuntimeError as exc:
            assert str(exc) == "QA intentional late failure"
            report["intentional_failure_exercised"] = True
    finally:
        for name, constraint in reversed(added):
            constraint.driver_remove("influence")
            rig.pose.bones[name].constraints.remove(constraint)
        connect(rig, original_flags)
        restore_channels(rig, original["channels"])
        restore_channels(helper, original_helper_channels)
        rig["physics_influence"] = 0.0
        for name, saved_constraints in original["constraints"].items():
            for constraint, saved in zip(rig.pose.bones[name].constraints, saved_constraints):
                constraint.active = saved["active"]
        update((rig, helper))
        rollback = snapshot(rig, skin)
        report["rollback"] = rollback
        exact_fields = ("rest", "channels", "constraints", "drivers", "raw_vertices", "weights",
                        "group_names", "armature", "object_matrix")
        report["rollback_exact"] = {key: rollback[key] == original[key] for key in exact_fields}
        report["rollback_skin_error_m"] = point_error(rollback["skin_world"], original["skin_world"])
        assert all(report["rollback_exact"].values()), "Rollback changed protected fixture data"
        assert report["rollback_skin_error_m"] < 2e-6
        assert channels(helper) == original_helper_channels
    assert not bpy.data.filepath
    report["success"] = True


parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
assert not args.output.exists()
args.output.mkdir(parents=True)
report = {"success": False, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
try:
    main(report)
except Exception:
    report["exception"] = traceback.format_exc()
finally:
    path = args.output / "connected_world_transfer.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("CONNECTED_WORLD_TRANSFER_REPORT=" + str(path), flush=True)
if not report["success"]:
    raise RuntimeError(report.get("exception", "Native fixture failed"))
