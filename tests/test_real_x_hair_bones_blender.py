"""Build, pose, and reopen hair controls on a disposable in-memory copy of X.

Load X.blend on Blender's command line. Only --preview PATH writes a new file;
the production input is checked byte-for-byte and is never saved over.
"""

import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
import character_designer as addon
from character_designer import hair_bones_rig as rig_service
from character_designer import hair_bones_topology as topology


def activate(obj, mode="OBJECT"):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for item in bpy.context.selected_objects:
        item.select_set(False)
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if mode != "OBJECT":
        bpy.ops.object.mode_set(mode=mode)


def evaluated(obj):
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    result = obj.evaluated_get(graph)
    mesh = result.to_mesh()
    try:
        return tuple(result.matrix_world @ vertex.co for vertex in mesh.vertices)
    finally:
        result.to_mesh_clear()


def max_error(first, second):
    assert len(first) == len(second), (len(first), len(second))
    return max(((a - b).length for a, b in zip(first, second)), default=0)


def native_snapshot(obj):
    return (tuple(tuple(v.co) for v in obj.data.vertices),
            tuple(tuple(edge.vertices) for edge in obj.data.edges),
            tuple(tuple(face.vertices) for face in obj.data.polygons))


def main():
    source = Path(bpy.data.filepath)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    addon.register()
    addon._validate_registration_integrity()
    armature = bpy.data.objects["CoshaRig"]
    original_bones = {
        bone.name: (bone.matrix_local.copy(), armature.pose.bones[bone.name].matrix_basis.copy())
        for bone in armature.data.bones
    }
    created_bones = []
    results = []
    baseline = {}
    try:
        for name in ("Hair1", "Hair2", "Hair3"):
            obj = bpy.data.objects[name]
            activate(obj)
            geometry = native_snapshot(obj)
            original_modifiers = tuple((mod.name, mod.type) for mod in obj.modifiers)
            baseline[name] = evaluated(obj)
            activate(obj, "EDIT")
            bpy.ops.mesh.select_all(action="DESELECT")
            assert bpy.ops.character_designer.select_hair_strands() == {"FINISHED"}
            _obj, plans = topology.selected_strands(bpy.context)
            assert bpy.ops.character_designer.generate_hair_bones() == {"FINISHED"}
            assert bpy.context.mode == "POSE" and bpy.context.object == armature
            record = json.loads(obj[rig_service.RECORD_KEY])
            names = [bone for chain in record["chains"] for bone in chain["bones"]]
            assert names and all(name in armature.pose.bones for name in names)
            assert {bone.name for bone in bpy.context.selected_pose_bones} == set(names)
            assert native_snapshot(obj) == geometry
            assert tuple((mod.name, mod.type) for mod in obj.modifiers if mod.type != "ARMATURE") == original_modifiers
            error = max_error(evaluated(obj), baseline[name])
            assert error < 1e-5, (name, "binding changed appearance", error)
            chain = max(record["chains"], key=lambda item: len(item["vertices"]))
            control = armature.pose.bones[chain["bones"][0]]
            saved_basis = control.matrix_basis.copy()
            control.rotation_mode = "XYZ"
            control.rotation_euler.x = math.radians(24)
            movement = max_error(evaluated(obj), baseline[name])
            assert movement > 0.001, (name, "hair bone did not deform hair", movement)
            control.matrix_basis = saved_basis
            bpy.context.view_layer.update()
            count_bones = len(armature.data.bones)
            activate(obj, "EDIT")
            # This is the same selection left by the discovery operator.
            assert bpy.ops.character_designer.generate_hair_bones() == {"FINISHED"}
            assert len(armature.data.bones) == count_bones
            assert max_error(evaluated(obj), baseline[name]) < 1e-5
            created_bones.extend(names)
            results.append({"object": name, "strands": len(plans), "bones": len(names),
                            "bind_error": error, "pose_movement": movement})
            print("PASS_REAL_X_HAIR=" + json.dumps(results[-1]), flush=True)

        head = armature.pose.bones["spine.006"]
        saved_head = head.matrix_basis.copy()
        head_world = armature.matrix_world @ head.matrix.copy()
        head.matrix_basis = Matrix.Translation((0.027, -0.014, 0.008)) @ Matrix.Rotation(0.23, 4, "Y")
        bpy.context.view_layer.update()
        delta = armature.matrix_world @ head.matrix @ head_world.inverted()
        for name, points in baseline.items():
            error = max_error(evaluated(bpy.data.objects[name]), tuple(delta @ point for point in points))
            assert error < 2e-5, (name, "head following failed", error)
            print("PASS_REAL_X_HEAD_FOLLOW=" + json.dumps({"object": name, "max_error": error}), flush=True)
        head.matrix_basis = saved_head
        bpy.context.view_layer.update()
        for name, (rest, basis) in original_bones.items():
            assert armature.data.bones[name].matrix_local == rest, name
            assert armature.pose.bones[name].matrix_basis == basis, name
        print("PASS_REAL_X_ORIGINAL_BONES_UNCHANGED", flush=True)
        # Keep the preview ready for direct FK manipulation.
        activate(armature, "POSE")
        for bone in armature.pose.bones:
            bone.select = bone.name in created_bones
        armature.data.bones.active = armature.data.bones[created_bones[0]]
        bpy.context.window_manager.character_designer.ui_page = "HAIR"
        if "--preview" in sys.argv:
            destination = Path(sys.argv[sys.argv.index("--preview") + 1]).resolve()
            assert destination != source.resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(destination), check_existing=False)
            print("HAIR_PREVIEW=" + str(destination), flush=True)
        print("REAL_X_HAIR_BONES_PASS=" + json.dumps(results), flush=True)
    finally:
        after = hashlib.sha256(source.read_bytes()).hexdigest()
        assert before == after
        print("REAL_X_HAIR_SOURCE_UNCHANGED=" + after, flush=True)


if __name__ == "__main__":
    main()
