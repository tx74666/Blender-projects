"""Compare native strand/group versions using X, never overwriting the input.

Optional --output-directory saves two independent review files for six strands:
18 per-strand deform bones versus six deform bones in two shared chains.
"""

import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
import character_designer as addon
from character_designer import hair_bones_groups as groups
from character_designer import hair_bones_topology as topology
from character_designer import hair_bones_variants as variants
from character_designer import hair_bones_rig as rig
from character_designer import hair_bones_mirror as mirror_controls


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


def points(obj):
    bpy.context.view_layer.update()
    result = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = result.to_mesh()
    try:
        return tuple(result.matrix_world @ vertex.co for vertex in mesh.vertices)
    finally:
        result.to_mesh_clear()


def error(first, second):
    assert len(first) == len(second)
    return max(((a - b).length for a, b in zip(first, second)), default=0.0)


def surface_change(first, second):
    # Mirror merge may change evaluated vertex count during bending. Compare
    # surfaces without assuming correspondence through that native operation.
    def directed(points_a, points_b):
        tree = KDTree(len(points_b))
        for index, point in enumerate(points_b):
            tree.insert(point, index)
        tree.balance()
        return max(tree.find(point)[2] for point in points_a)
    return max(directed(first, second), directed(second, first))


def snapshot(obj):
    return (tuple(tuple(vertex.co) for vertex in obj.data.vertices),
            tuple((group.name, group.lock_weight) for group in obj.vertex_groups),
            tuple(tuple((item.group, item.weight) for item in vertex.groups) for vertex in obj.data.vertices),
            tuple((mod.name, mod.type, mod.show_viewport, mod.show_render) for mod in obj.modifiers),
            obj.parent, obj.matrix_world.copy())


def choose(plans):
    bm = bmesh.from_edit_mesh(bpy.context.object.data)
    # Only one exclusive inner/tip vertex per member is needed for grouping.
    chosen = {plan["layers"][-1][0] for plan in plans}
    for face in bm.faces:
        face.select = False
    for edge in bm.edges:
        edge.select = False
    for vertex in bm.verts:
        vertex.select = vertex.index in chosen
    bmesh.update_edit_mesh(bpy.context.object.data, loop_triangles=False, destructive=False)


def bone_names(result):
    return tuple(name for chain in result["chains"] for name in chain["bones"])


def save_review(directory, name, source_path):
    if directory is None:
        return
    destination = directory / name
    assert destination.resolve() != source_path.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    bpy.context.window_manager.character_designer.ui_page = "HAIR"
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), check_existing=False)
    print("HAIR_COMPARISON_FILE=" + str(destination), flush=True)


def main():
    path = Path(bpy.data.filepath)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    output = Path(sys.argv[sys.argv.index("--output-directory") + 1]) if "--output-directory" in sys.argv else None
    addon.register()
    addon._validate_registration_integrity()
    main_rig = bpy.data.objects["CoshaRig"]
    original_bones = {bone.name: (bone.matrix_local.copy(), main_rig.pose.bones[bone.name].matrix_basis.copy())
                      for bone in main_rig.data.bones}
    results = []
    try:
        for source_name in ("Hair2", "Hair1", "Hair3"):
            source = bpy.data.objects[source_name]
            activate(source)
            original = snapshot(source)
            baseline = points(source)
            activate(source, "EDIT")
            bpy.ops.mesh.select_all(action="DESELECT")
            _, detected = topology.select_strands(bpy.context)
            if source_name == "Hair2":
                # Select the six closest roots to one end of the source patch.
                detected = tuple(sorted(detected, key=lambda p: tuple(p["centers"][0])))[:6]
            assert detected
            groups.capture_plans(source, detected)
            _, per_strand = groups.build_plans(bpy.context, mode="PER_STRAND")
            a = variants.build_variant(bpy.context, source, per_strand, mode="PER_STRAND", bone_count=3)
            assert len(bone_names(a)) == mirror_controls.preview_full_chain_count(source, per_strand) * 3
            initial_error = error(points(a["mesh"]), baseline)
            assert initial_error < 2e-5, (source_name, "per-strand bind jump", initial_error,
                                        tuple(a["mesh"].matrix_world.translation),
                                        tuple(source.matrix_world.translation))
            assert snapshot(source) == original
            if source_name == "Hair2":
                assert len(bone_names(a)) == 18
                save_review(output, "X-Hair-A-Per-Strand.blend", path)
            # Keep a hand-tuned prior result through regrouping/generation.
            tuned = a["armature"].pose.bones[bone_names(a)[1]]
            tuned.rotation_mode = "XYZ"
            tuned.rotation_euler.x = 0.31
            tuned_basis = tuned.matrix_basis.copy()
            variants.show_source(bpy.context, source)
            if source_name == "Hair2":
                choose(detected[:3])
                groups.group_selected(bpy.context, name="Back Hair 1")
                choose(detected[3:])
                group_id = groups.group_selected(bpy.context, name="Back Hair 2")
            else:
                choose(detected)
                group_id = groups.group_selected(bpy.context, name="Shared Hair")
            groups.create_group_guide(bpy.context, group_id, point_count=4)
            _, grouped = groups.build_plans(bpy.context, mode="GROUPED")
            guide_plan = next(plan for plan in grouped if plan["group_id"] == group_id)
            for endpoint in (0, -1):
                expected_center = sum((Vector(member["centers"][endpoint]) for member in guide_plan["members"]), Vector()) / len(guide_plan["members"])
                discrepancy = source.matrix_world.to_3x3() @ (Vector(guide_plan["centers"][endpoint]) - expected_center)
                assert discrepancy.length < 1e-5, (source_name, "new guide world frame", endpoint, discrepancy.length)
            b = variants.build_variant(bpy.context, source, grouped, mode="GROUPED", bone_count=3)
            expected = 6 if source_name == "Hair2" else 3
            assert len(bone_names(b)) == expected
            assert len(variants.variants_for(source)) == 2
            assert tuned.matrix_basis == tuned_basis
            assert snapshot(source) == original
            bind_error = error(points(b["mesh"]), baseline)
            assert bind_error < 2e-5, (source_name, "group bind jump", bind_error)
            # Both results consume exactly the same head motion, including Mirror.
            head = main_rig.pose.bones[rig._head_bone(main_rig)]
            saved = head.matrix_basis.copy()
            head_world = main_rig.matrix_world @ head.matrix.copy()
            head.matrix_basis = Matrix.Translation((0.026, 0.004, -0.01)) @ Matrix.Rotation(0.20, 4, "Y")
            bpy.context.view_layer.update()
            delta = main_rig.matrix_world @ head.matrix @ head_world.inverted()
            follow_error = error(points(b["mesh"]), tuple(delta @ point for point in baseline))
            assert follow_error < 3e-5, (source_name, "group head follow", follow_error)
            head.matrix_basis = saved
            bpy.context.view_layer.update()
            control = b["armature"].pose.bones[bone_names(b)[0]]
            control.rotation_mode = "XYZ"
            control.rotation_euler.x = 0.24
            movement = surface_change(points(b["mesh"]), baseline)
            assert movement > 0.001, (source_name, "group control had no effect", movement)
            assert movement < 0.3, (source_name, "unexpected group pivot or deformation", movement)
            control.matrix_basis = Matrix.Identity(4)
            tuned.matrix_basis = Matrix.Identity(4)
            bpy.context.view_layer.update()
            if source_name == "Hair2":
                save_review(output, "X-Hair-B-Grouped.blend", path)
            result = {"source": source_name, "strands": len(detected), "per_strand_bones": len(bone_names(a)),
                      "grouped_bones": len(bone_names(b)), "bind_error": bind_error,
                      "head_follow_error": follow_error, "group_bend_movement": movement}
            results.append(result)
            print("REAL_X_HAIR_VARIANTS=" + json.dumps(result), flush=True)
        for name, (rest, basis) in original_bones.items():
            assert main_rig.data.bones[name].matrix_local == rest, name
            assert main_rig.pose.bones[name].matrix_basis == basis, name
        assert len(main_rig.data.bones) == len(original_bones)
        print("REAL_X_HAIR_VARIANTS_PASS=" + json.dumps(results), flush=True)
    finally:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        print("REAL_X_INPUT_UNCHANGED=" + digest, flush=True)


if __name__ == "__main__":
    main()
