"""Background regression for the standalone recovered FK / SPIK script.

Run with Blender --background --factory-startup --disable-autoexec --threads 2
--python tests/test_legacy_spline_recovery_blender.py.
"""

import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile

import bpy
from mathutils import Euler, Matrix, Vector


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "References", "Elaina", "legacy_spline_setup_repaired.py")


def matrix_values(matrix):
    return [list(row) for row in matrix]


def matrices(rig, names):
    bpy.context.view_layer.update()
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {name: matrix_values(evaluated.pose.bones[name].matrix) for name in names}


def maximum_error(left, right):
    return max(abs(a - b) for name in left for row_a, row_b in zip(left[name], right[name]) for a, b in zip(row_a, row_b))


def verify_reopen(path):
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False, use_scripts=False)
    rig = bpy.data.objects["Artist renamed recovered rig"]
    expected = json.loads(rig["recovery_test_expected"])
    names = json.loads(rig["recovery_test_names"])
    for frame in (7, 1, 4, 2, 6, 3, 5):
        bpy.context.scene.frame_set(frame)
        error = maximum_error(matrices(rig, names), expected[str(frame)])
        assert error < 3e-5, ("Native reopen drift", frame, error)
    assert not bpy.data.texts, "The fixture must not rely on embedded scripts"
    print("RECOVERY_NATIVE_REOPEN_OK", flush=True)


if "--reopen" in sys.argv:
    verify_reopen(sys.argv[sys.argv.index("--reopen") + 1])
    sys.exit(0)

spec = importlib.util.spec_from_file_location("legacy_spline_setup_repaired", SCRIPT)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def select(rig, names, mode="POSE"):
    active = bpy.context.object
    if active and active.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj is rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode=mode)
    bones = rig.data.edit_bones if mode == "EDIT" else rig.pose.bones
    for bone in bones:
        bone.select = bone.name in names
        if mode == "EDIT":
            bone.select_head = bone.select_tail = bone.select
    active_bones = rig.data.edit_bones if mode == "EDIT" else rig.data.bones
    active_bones.active = active_bones[names[-1]] if names else None


def fixture(*, curved=False, parent_scale=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = bpy.data.armatures.new("Artist original armature data")
    rig = bpy.data.objects.new("Original artist rig", data)
    bpy.context.scene.collection.objects.link(rig)
    rig.matrix_world = (Matrix.Translation((1.4, -.8, .5))
                        @ Euler((.18, -.21, .41)).to_matrix().to_4x4()
                        @ Matrix.Diagonal((1.3, .75, 1.6, 1)))
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    parent = data.edit_bones.new("Animated parent")
    parent.head, parent.tail = (0, 0, .1), (0, 0, .7)
    origin = Vector((.4, -.2, 1.4))
    direction = Vector((.17, .13, -1)).normalized()
    names, joints = [], [origin.copy()]
    for index, (name, length) in enumerate(zip(("Z_FK.first", "A_FK.middle", "M_FK.last"), (.42, .35, .52))):
        bone = data.edit_bones.new(name)
        bone.head = origin
        bone.tail = origin + direction * length + (Vector((.08, 0, 0)) if curved and index == 1 else Vector())
        bone.roll = .31
        bone.parent = data.edit_bones[names[-1]] if names else parent
        bone.use_connect = bool(names)
        names.append(bone.name)
        origin = bone.tail.copy()
        joints.append(origin)
    unrelated = data.edit_bones.new("Unrelated artist bone")
    unrelated.head, unrelated.tail = (-.4, 0, .6), (-.4, 0, 1.1)
    bpy.ops.object.mode_set(mode="POSE")
    collection = data.collections.new("Artist retained collection")
    for name in names + ["Unrelated artist bone"]:
        collection.assign(data.bones[name])
    pose = rig.pose.bones["Animated parent"]
    pose.rotation_mode = "XYZ"
    pose.rotation_euler = (.12, -.21, .31)
    pose.location = (.02, .03, -.01)
    if parent_scale:
        pose.scale = (1.1, .85, 1.2)
    pose.keyframe_insert("rotation_euler", frame=1)
    pose.rotation_euler.z += .19
    pose.keyframe_insert("rotation_euler", frame=7)
    keep_constraint = rig.pose.bones["Unrelated artist bone"].constraints.new("LIMIT_ROTATION")
    keep_constraint.name = "Artist retained constraint"
    keep_constraint.use_limit_x = True
    keep_constraint.min_x, keep_constraint.max_x = -.5, .5
    rig["Artist note"] = "Preserve me"
    vertices = [tuple(point + Vector((x, y, 0))) for point in joints for x, y in ((-.04, -.04), (.04, -.04), (.04, .04), (-.04, .04))]
    faces = [(row * 4 + j, row * 4 + (j + 1) % 4, (row + 1) * 4 + (j + 1) % 4, (row + 1) * 4 + j)
             for row in range(3) for j in range(4)]
    mesh = bpy.data.meshes.new("Retained artist mesh")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new("Retained artist skin", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = rig.matrix_world.copy()
    modifier = obj.modifiers.new("Retained artist skinning", "ARMATURE")
    modifier.object = rig
    for index, name in enumerate(names):
        group = obj.vertex_groups.new(name=name)
        group.add(list(range(index * 4, (index + 1) * 4)), 1, "REPLACE")
    obj.vertex_groups[names[-1]].add(list(range(12, 16)), 1, "REPLACE")
    keep = obj.vertex_groups.new(name="Artist retained pin")
    keep.add([2, 13], .375, "REPLACE")
    bpy.context.scene.frame_set(1)
    select(rig, names)
    return rig, names, obj


def mesh_points(obj):
    bpy.context.view_layer.update()
    return [vertex.co.copy() for vertex in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]


def signature(rig, obj):
    bpy.context.view_layer.update()
    return {
        "bones": [(bone.name, matrix_values(bone.matrix_local), bone.length,
                   bone.parent.name if bone.parent else None, bone.use_deform,
                   sorted(collection.name for collection in bone.collections),
                   matrix_values(rig.pose.bones[bone.name].matrix_basis),
                   tuple((constraint.name, constraint.type) for constraint in rig.pose.bones[bone.name].constraints))
                  for bone in rig.data.bones],
        "objects": sorted(item.name for item in bpy.data.objects),
        "curves": sorted(item.name for item in bpy.data.curves),
        "collections": sorted(collection.name for collection in rig.data.collections),
        "action": [(curve.data_path, curve.array_index, [tuple(key.co) for key in curve.keyframe_points])
                   for curve in recovery._action_curves(rig.animation_data.action if rig.animation_data else None)],
        "weights": [(vertex.index, [(group.group, group.weight) for group in vertex.groups]) for vertex in obj.data.vertices],
        "groups": [group.name for group in obj.vertex_groups],
        "modifier": [(modifier.name, modifier.type, modifier.object.name) for modifier in obj.modifiers],
        "registry": rig.get(recovery.REGISTRY),
    }


def expect_refusal(rig, obj, function, message):
    before = signature(rig, obj)
    try:
        function()
    except recovery.RecoveryError as error:
        assert message in str(error), (message, str(error))
    else:
        raise AssertionError("Expected refusal: " + message)
    assert signature(rig, obj) == before, "Refused operation changed artist data"


def test_lifecycle():
    rig, names, obj = fixture()
    original = signature(rig, obj)
    baseline = matrices(rig, names)
    record = recovery.build_selected()
    assert record["source"] == names, "Bone topology, not alphabetical selection order, defines the chain"
    assert len(record["mechanism"]) == len(names) and len(record["controls"]) == 3
    assert all(not rig.data.bones[name].use_deform for name in record["mechanism"] + record["controls"])
    error = maximum_error(matrices(rig, names), baseline)
    print("RECOVERY_INITIAL_MATRIX_ERROR", error, flush=True)
    assert error < 2e-3
    curve = recovery._curve_for(rig, record["owner"])
    assert curve.data.splines[0].type == "NURBS"
    assert [tuple(modifier.vertex_indices) for modifier in curve.modifiers] == [(0,), (1,), (2,)]
    before = mesh_points(obj)
    control = rig.pose.bones[record["controls"][1]]
    control.location.x = .18
    after = mesh_points(obj)
    movement = max((a - b).length for a, b in zip(before, after))
    print("RECOVERY_CONTROL_MESH_MOVEMENT", movement, flush=True)
    assert movement > .02
    control.location.x = 0
    rig.name, curve.name = "Artist renamed recovered rig", "Artist renamed recovered curve"
    counts = (len(bpy.data.objects), len(rig.data.bones))
    select(rig, names)
    assert recovery.build_selected()["owner"] == record["owner"]
    assert (len(bpy.data.objects), len(rig.data.bones)) == counts
    select(rig, names[:2])
    expect_refusal(rig, obj, recovery.build_selected, "overlaps")
    select(rig, record["controls"])
    foreign = rig.pose.bones["Unrelated artist bone"].constraints.new("COPY_LOCATION")
    foreign.target, foreign.subtarget = rig, record["controls"][0]
    expect_refusal(rig, obj, recovery.remove_selected, "artist constraint")
    rig.pose.bones["Unrelated artist bone"].constraints.remove(foreign)
    rig.name = "Original artist rig"
    recovery.remove_selected()
    assert signature(rig, obj) == original, "Removal failed to restore exact original rig/mesh data"
    assert maximum_error(matrices(rig, names), baseline) < 1e-6


def test_preflight():
    rig, names, obj = fixture(curved=True)
    expect_refusal(rig, obj, recovery.build_selected, "curved rest chain")
    rig, names, obj = fixture()
    rig.pose.bones[names[1]].location.x = .1
    expect_refusal(rig, obj, recovery.build_selected, "neutral local poses")
    rig.pose.bones[names[1]].location.x = 0
    rig.pose.bones[names[0]].constraints.new("LIMIT_ROTATION")
    expect_refusal(rig, obj, recovery.build_selected, "existing constraints")
    rig, names, obj = fixture()
    rig.pose.bones[names[1]].keyframe_insert("location", frame=1)
    expect_refusal(rig, obj, recovery.build_selected, "animated or driven")
    rig, names, obj = fixture()
    driver = rig.pose.bones[names[1]].driver_add("rotation_euler", 0)
    driver.driver.expression = "0"
    expect_refusal(rig, obj, recovery.build_selected, "animated or driven")
    rig, names, obj = fixture()
    select(rig, [names[0], names[-1]])
    expect_refusal(rig, obj, recovery.build_selected, "continuous parent-child")


def test_rollback_and_edit_mode():
    for stage in ("bones", "curve", "constraints"):
        rig, names, obj = fixture()
        baseline, original = matrices(rig, names), signature(rig, obj)
        previous = recovery._checkpoint

        def fail(current):
            if current == stage:
                raise RuntimeError("Injected failure at " + stage)

        recovery._checkpoint = fail
        try:
            try:
                recovery.build_selected()
            except RuntimeError as error:
                assert "Injected failure" in str(error)
            else:
                raise AssertionError("The injected failure did not run")
        finally:
            recovery._checkpoint = previous
        assert signature(rig, obj) == original, ("Rollback residue", stage)
        assert maximum_error(matrices(rig, names), baseline) < 1e-6
        assert rig.mode == "POSE"
        assert {bone.name for bone in rig.pose.bones if bone.select} == set(names)
    rig, names, obj = fixture()
    original = signature(rig, obj)
    select(rig, names, "EDIT")
    record = recovery.build_selected()
    assert rig.mode == "EDIT"
    assert {bone.name for bone in rig.data.edit_bones if bone.select} == set(record["controls"])
    recovery.remove_selected()
    assert rig.mode == "EDIT"
    bpy.ops.object.mode_set(mode="POSE")
    assert signature(rig, obj) == original


def test_scaled_parent():
    rig, names, obj = fixture(parent_scale=True)
    expect_refusal(rig, obj, recovery.build_selected, "sheared or reflected")


def test_removal_dependencies():
    for dependency in ("custom_property_animation", "bone_driver", "property_driver", "curve_driver",
                       "material_node_driver", "curve_child", "curve_modifier"):
        rig, names, obj = fixture()
        record = recovery.build_selected()
        curve = recovery._curve_for(rig, record["owner"])
        control = rig.pose.bones[record["controls"][1]]
        if dependency == "custom_property_animation":
            control["Artist value"] = .5
            control.keyframe_insert('["Artist value"]', frame=1)
            message = "are animated"
        elif dependency in {"bone_driver", "property_driver", "curve_driver", "material_node_driver"}:
            if dependency == "material_node_driver":
                material = bpy.data.materials.new("Artist driven material")
                material.use_nodes = True
                obj.data.materials.append(material)
                shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
                driver = shader.inputs["Roughness"].driver_add("default_value").driver
            else:
                driver = obj.driver_add("location", 0).driver
            variable = driver.variables.new()
            if dependency in {"bone_driver", "material_node_driver"}:
                variable.type = "TRANSFORMS"
                variable.targets[0].id = rig
                variable.targets[0].bone_target = control.name
                variable.targets[0].transform_type = "LOC_X"
            else:
                variable.type = "SINGLE_PROP"
                if dependency == "property_driver":
                    control["Artist value"] = .5
                    variable.targets[0].id = rig
                    variable.targets[0].data_path = control.path_from_id() + '["Artist value"]'
                else:
                    variable.targets[0].id = curve
                    variable.targets[0].data_path = "location.x"
            driver.expression = variable.name
            message = "artist driver"
        elif dependency == "curve_child":
            child = bpy.data.objects.new("Artist curve child", None)
            bpy.context.scene.collection.objects.link(child)
            child.parent = curve
            message = "parented to the generated curve"
        else:
            modifier = obj.modifiers.new("Artist curve deformation", "CURVE")
            modifier.object = curve
            message = "artist modifier"
        expect_refusal(rig, obj, recovery.remove_selected, message)


def test_native_reopen():
    rig, names, obj = fixture()
    record = recovery.build_selected()
    rig.name = "Artist renamed recovered rig"
    control = rig.pose.bones[record["controls"][1]]
    control.location = (0, 0, 0)
    control.keyframe_insert("location", frame=1)
    control.location.x = .18
    control.keyframe_insert("location", frame=7)
    expect_refusal(rig, obj, recovery.remove_selected, "are animated")
    expected = {}
    for frame in range(1, 8):
        bpy.context.scene.frame_set(frame)
        expected[frame] = matrices(rig, names)
    assert maximum_error(expected[1], expected[7]) > .05
    rig["recovery_test_names"] = json.dumps(names)
    rig["recovery_test_expected"] = json.dumps(expected)
    with tempfile.TemporaryDirectory(prefix="elaina-spline-recovery-") as output:
        path = os.path.join(output, "native-recovery.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        result = subprocess.run([bpy.app.binary_path, "--background", "--factory-startup", "--disable-autoexec",
                                 "--threads", "2", "--python", os.path.abspath(__file__), "--", "--reopen", path],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        print(result.stdout, flush=True)
        assert result.returncode == 0 and "RECOVERY_NATIVE_REOPEN_OK" in result.stdout


if __name__ == "__main__":
    for test in (test_lifecycle, test_preflight, test_rollback_and_edit_mode, test_scaled_parent, test_removal_dependencies, test_native_reopen):
        test()
        print("PASS", test.__name__, flush=True)
    print("LEGACY_SPLINE_RECOVERY_ALL_TESTS_PASSED", flush=True)
