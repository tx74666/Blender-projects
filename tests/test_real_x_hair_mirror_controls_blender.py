"""Verify full Hair3 controls on a read-only X copy; optionally save a review."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons"))
sys.path.insert(0, str(ROOT / "tests"))
import character_designer as addon
from character_designer import hair_bones_groups as groups
from character_designer import hair_bones_topology as topology
from character_designer import hair_bones_variants as variants
from character_designer import hair_bones_rig as rig
from test_real_x_hair_variants_blender import activate, points, error, snapshot


def coarse_points_and_weights(obj):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = evaluated.to_mesh()
    names = {group.index: group.name for group in obj.vertex_groups}
    try:
        return (tuple(evaluated.matrix_world @ vertex.co for vertex in data.vertices),
                tuple({names[item.group]: item.weight for item in vertex.groups} for vertex in data.vertices))
    finally:
        evaluated.to_mesh_clear()


def main():
    source_path = Path(bpy.data.filepath)
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    addon.register()
    addon._validate_registration_integrity()
    source = bpy.data.objects["Hair3"]
    activate(source)
    original = snapshot(source)
    baseline = points(source)
    main_rig = bpy.data.objects["CoshaRig"]
    original_bones = tuple((bone.name, bone.matrix_local.copy(), main_rig.pose.bones[bone.name].matrix_basis.copy())
                           for bone in main_rig.data.bones)
    activate(source, "EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    _, captured = topology.select_strands(bpy.context)
    assert len(captured) == 7
    groups.capture_plans(source, captured)
    _, plans = groups.build_plans(bpy.context, source=source)
    result = variants.build_variant(bpy.context, source, plans, bone_count=4)
    mesh, armature = result["mesh"], result["armature"]
    record = rig._read_records(mesh)
    assert record["mirror_layout"] == "BEFORE_ARMATURE_X"
    assert len(result["chains"]) == len(record["chains"]) == 13
    names = tuple(name for chain in result["chains"] for name in chain["bones"])
    assert len(names) == 52 and len(armature.data.bones) == 53
    central = tuple(chain for chain in result["chains"] if all(name.endswith(".C") for name in chain["bones"]))
    assert len(central) == 1
    left = tuple(chain for chain in result["chains"] if all(name.endswith(".L") for name in chain["bones"]))
    right = tuple(chain for chain in result["chains"] if all(name.endswith(".R") for name in chain["bones"]))
    assert len(left) == len(right) == 6
    mods = list(mesh.modifiers)
    skin = next(mod for mod in mods if mod.type == "ARMATURE")
    mirror = next(mod for mod in mods if mod.type == "MIRROR")
    assert mods.index(mirror) < mods.index(skin)
    assert mirror.mirror_object is None and mirror.use_mirror_vertex_groups
    assert mesh.get(rig.MIRROR_KEY) is None
    bind_error = error(points(mesh), baseline)
    assert bind_error < 2e-5, bind_error
    to_source = source.matrix_world.inverted() @ armature.matrix_world
    for name in central[0]["bones"]:
        bone = armature.data.bones[name]
        assert max(abs((to_source @ end).x) for end in (bone.head_local, bone.tail_local)) < 1e-5
    for chain in left:
        for name in chain["bones"]:
            l_bone, r_bone = armature.data.bones[name], armature.data.bones[name[:-2] + ".R"]
            for first, second in ((l_bone.head_local, r_bone.head_local), (l_bone.tail_local, r_bone.tail_local)):
                first, second = to_source @ first, to_source @ second
                assert (Vector((-first.x, first.y, first.z)) - second).length < 1e-5

    # Inspect the actual mirrored, skinned coarse vertices, before subdivision.
    downstream = [(mod, mod.show_viewport) for mod in mods[mods.index(skin) + 1:]]
    for mod, _ in downstream:
        mod.show_viewport = False
    original_points, weights = coarse_points_and_weights(mesh)
    side_motion = {}
    for side, chain in (("L", left[0]), ("R", right[0])):
        other = ".R" if side == "L" else ".L"
        affected = [i for i, values in enumerate(weights) if any(values.get(name, 0) > .5 for name in chain["bones"])]
        untouched = [i for i, values in enumerate(weights) if any(name.endswith(other) and weight > .5 for name, weight in values.items())]
        assert affected and untouched
        control = armature.pose.bones[chain["bones"][0]]
        control.rotation_mode = "XYZ"
        control.rotation_euler.x = .25
        moved, _ = coarse_points_and_weights(mesh)
        displacement = max((moved[i] - original_points[i]).length for i in affected)
        cross_side_error = max((moved[i] - original_points[i]).length for i in untouched)
        assert displacement > .001 and cross_side_error < 2e-5, (side, displacement, cross_side_error)
        side_motion[side] = dict(movement=displacement, opposite_side_error=cross_side_error)
        control.matrix_basis = Matrix.Identity(4)
    center_vertices = [i for i, values in enumerate(weights) if sum(values.get(name, 0) for name in central[0]["bones"]) > .99999]
    assert center_vertices
    control = armature.pose.bones[central[0]["bones"][0]]
    control.location.x = .04
    moved, _ = coarse_points_and_weights(mesh)
    assert len(moved) == len(original_points)
    deltas = tuple(moved[i] - original_points[i] for i in center_vertices)
    assert min(delta.length for delta in deltas) > .001
    assert max((delta - deltas[0]).length for delta in deltas) < 2e-5, "Central strand did not move as one piece"
    control.matrix_basis = Matrix.Identity(4)
    for mod, shown in downstream:
        mod.show_viewport = shown
    bpy.context.view_layer.update()

    head = main_rig.pose.bones[rig._head_bone(main_rig)]
    saved = head.matrix_basis.copy()
    head_world = main_rig.matrix_world @ head.matrix.copy()
    head.matrix_basis = Matrix.Translation((.02, .01, -.01)) @ Matrix.Rotation(.23, 4, "Y")
    bpy.context.view_layer.update()
    delta = main_rig.matrix_world @ head.matrix @ head_world.inverted()
    follow_error = error(points(mesh), tuple(delta @ point for point in baseline))
    assert follow_error < 3e-5, follow_error
    head.matrix_basis = saved
    bpy.context.view_layer.update()
    assert snapshot(source) == original
    for name, rest, pose in original_bones:
        assert main_rig.data.bones[name].matrix_local == rest and main_rig.pose.bones[name].matrix_basis == pose
    assert len(main_rig.data.bones) == len(original_bones)
    report = dict(source="Hair3", source_strands=7, chains=13, hair_bones=52, center_chains=1,
                  left_chains=6, right_chains=6, bind_error=bind_error, head_follow_error=follow_error,
                  independent_sides=side_motion, source_preserved=True)
    if "--output" in sys.argv:
        output = Path(sys.argv[sys.argv.index("--output") + 1])
        assert output.resolve() != source_path.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        settings = bpy.context.window_manager.character_designer_hair_bones
        settings.mode = "PER_STRAND"
        settings.bone_count = 4
        settings.active_variant = result["collection"].name
        bpy.context.window_manager.character_designer.ui_page = "HAIR"
        bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
        output.with_suffix(".verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == digest
    print("REAL_X_FULL_MIRROR_PASS=" + json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
