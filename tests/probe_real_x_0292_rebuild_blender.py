"""Disposable 0.29.3 repeat-Rebuild probe for the current saved X rig.

The input is opened read-only and is never saved.  Its one known ownership
drift (the exact-owned left Hand IK bone moved out of Randy Controls) is repaired
in memory before the normal transactional Rebuild is exercised.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "addons"
TESTS_ROOT = PROJECT_ROOT / "tests"
for path in (ADDONS_ROOT, TESTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import character_designer
from character_designer import limb_ik
import probe_limb_ik_real_x_blender as probe
import test_real_x_pole_direction_migration_blender as migration
import test_real_x_remove_analyze_modeled_build_blender as real_x


EXPECTED_KEYS = {("ARM", "L"), ("ARM", "R"), ("LEG", "L"), ("LEG", "R")}
KNOWN_MISSING_CONTROL = "CTRL_hand_IK.L"


def _fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {"sha256": digest.hexdigest().upper(), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _owned_control_collection(armature, armature_id):
    matches = [
        collection
        for collection in armature.data.collections
        if limb_ik._owned(collection, armature_id, role="CONTROL_COLLECTION")
    ]
    if len(matches) != 1:
        raise AssertionError(f"Expected one owned control collection, found {len(matches)}")
    return matches[0]


def _repair_known_collection_drift(armature, inventory):
    collection = _owned_control_collection(armature, inventory["armature_id"])
    expected = {bone.name for bone in inventory["bones"]}
    actual = {bone.name for bone in collection.bones}
    missing = expected - actual
    foreign = actual - expected
    if not missing and not foreign:
        bone = armature.data.bones[KNOWN_MISSING_CONTROL]
        memberships = tuple(sorted(item.name for item in bone.collections))
        if memberships != (collection.name,):
            raise AssertionError(
                f"Control collection is complete but {KNOWN_MISSING_CONTROL} has unexpected memberships: {memberships}"
            )
        limb_ik._removal_resources(bpy.context, armature, inventory)
        problems = limb_ik._foreign_dependency_problems(armature, inventory)
        if problems:
            raise AssertionError(f"Already-valid collection state exposed a foreign dependency: {problems[0]}")
        return {"bone": bone.name, "before": memberships, "after": memberships, "already_valid": True}
    if missing != {KNOWN_MISSING_CONTROL} or foreign:
        raise AssertionError(f"Unexpected control collection drift: missing={sorted(missing)}, foreign={sorted(foreign)}")
    bone = armature.data.bones[KNOWN_MISSING_CONTROL]
    old_collections = tuple(sorted(item.name for item in bone.collections))
    if (
        bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
        or bone.get(limb_ik.ROLE_KEY) != "HAND_IK"
        or bone.get(limb_ik.KIND_KEY) != "ARM"
        or bone.get(limb_ik.SIDE_KEY) != "L"
    ):
        raise AssertionError("Known missing control does not have the exact expected ownership tags")
    collection.assign(bone)
    for other in tuple(bone.collections):
        if other.name != collection.name:
            other.unassign(bone)
    if {item.name for item in bone.collections} != {collection.name}:
        raise AssertionError("Known collection repair did not produce exact membership")
    limb_ik._removal_resources(bpy.context, armature, limb_ik._validate_inventory(armature))
    problems = limb_ik._foreign_dependency_problems(armature, limb_ik._validate_inventory(armature))
    if problems:
        raise AssertionError(f"Collection repair exposed a foreign dependency: {problems[0]}")
    return {"bone": bone.name, "before": old_collections, "after": (collection.name,)}


def _set_fixed_defaults(settings):
    values = {}
    for key in sorted(EXPECTED_KEYS):
        settings.selected_limb = probe.SELECTED_LIMBS[key]
        result = bpy.ops.character_designer.limb_ik_default_pole_direction()
        if result != {"FINISHED"}:
            raise AssertionError(f"Default Direction failed for {key}: {result}; {settings.last_message}")
        field = probe.POLE_DIRECTION_PROPERTIES[key]
        value = Vector(getattr(settings, field))
        expected = probe.DEFAULT_POLE_DIRECTIONS[key]
        if (value - expected).length > 1.0e-9:
            raise AssertionError(f"Wrong raw default for {key}: {tuple(value)} != {tuple(expected)}")
        values[key] = value
    return values


def _source_rest_signature(armature, source_names):
    return {
        name: {
            "parent": armature.data.bones[name].parent.name if armature.data.bones[name].parent else "",
            "head": tuple(armature.data.bones[name].head_local),
            "tail": tuple(armature.data.bones[name].tail_local),
            "matrix": tuple(float(value) for row in armature.data.bones[name].matrix_local for value in row),
            "use_connect": bool(armature.data.bones[name].use_connect),
            "use_deform": bool(armature.data.bones[name].use_deform),
        }
        for name in source_names
    }


def _validate_geometry_and_directions(armature, inventory):
    result = {}
    for key, rig in sorted(inventory["rigs"].items()):
        kind, side = key
        pole = rig["pole"]
        saved = Vector(pole[limb_ik.POLE_DIRECTION_KEY]).normalized()
        if kind == "ARM" and saved.y <= 0.95:
            raise AssertionError(f"{kind}.{side} Pole is not behind at +Y: {tuple(saved)}")
        if kind == "LEG" and (saved.y >= -0.99 or abs(saved.x) >= 0.01):
            raise AssertionError(f"{kind}.{side} Pole is not straight forward at -Y: {tuple(saved)}")

        pole_axis = Vector(pole.tail_local) - Vector(pole.head_local)
        if pole_axis.length <= limb_ik.EPSILON or pole_axis.normalized().dot(saved) <= 0.999999:
            raise AssertionError(f"{kind}.{side} short Pole bone tail does not follow its bend direction")

        lower = armature.data.bones[rig["chain"][1]]
        joint = Vector(lower.head_local)
        full_guide = Vector(pole.head_local) - joint
        line = rig["line"]
        line_axis = Vector(line.tail_local) - Vector(line.head_local)
        if line.parent is None or line.parent.name != rig["chain"][0] or line.use_connect:
            raise AssertionError(f"{kind}.{side} line helper is not Keep Offset under the upper bone")
        if line_axis.length <= limb_ik.EPSILON or line_axis.length >= full_guide.length * 0.2:
            raise AssertionError(f"{kind}.{side} Edit helper was not shortened: {line_axis.length} / {full_guide.length}")
        rest_aim_dot = line_axis.normalized().dot(full_guide.normalized())
        if rest_aim_dot <= 0.999:
            raise AssertionError(
                f"{kind}.{side} short line helper does not aim toward its Pole: "
                f"dot={rest_aim_dot}, line_head={tuple(line.head_local)}, "
                f"line_axis={tuple(line_axis)}, joint={tuple(joint)}, pole={tuple(pole.head_local)}"
            )

        bpy.context.view_layer.update()
        pose_line = armature.pose.bones[line.name]
        pose_pole = armature.pose.bones[pole.name]
        guide_error = (Vector(pose_line.tail) - Vector(pose_pole.head)).length
        if guide_error > 2.0e-4:
            raise AssertionError(f"{kind}.{side} Pose guide does not reach the Pole: {guide_error}")

        for source_name in rig["chain"][:2]:
            pose_bone = armature.pose.bones[source_name]
            data_bone = armature.data.bones[source_name]
            length_error = abs((Vector(pose_bone.tail) - Vector(pose_bone.head)).length - data_bone.length)
            if length_error > 2.0e-5:
                raise AssertionError(f"{kind}.{side} source segment stretched: {source_name} {length_error}")
        result[f"{kind}.{side}"] = {
            "direction": tuple(saved),
            "pole_edit_length": pole_axis.length,
            "line_edit_length": line_axis.length,
            "joint_to_pole": full_guide.length,
            "line_rest_aim_dot": rest_aim_dot,
            "pose_guide_error": guide_error,
        }
    return result


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("Expected one backup .blend path after --")
    path = Path(args[0]).resolve()
    before_disk = _fingerprint(path)
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    character_designer.register()
    armature = migration._find_real_armature()
    migration._mode_set(bpy.context, armature, "POSE")
    initial = limb_ik._validate_inventory(armature)
    if set(initial["rigs"]) != EXPECTED_KEYS:
        raise AssertionError(f"Expected four saved rigs, found {sorted(initial['rigs'])}")

    source_names = tuple(bone.name for bone in armature.data.bones if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE)
    protected_assets = real_x._protected_asset_fingerprints()
    source_rest = _source_rest_signature(armature, source_names)
    source_pose = real_x._source_pose_snapshot(armature, source_names)
    repair = _repair_known_collection_drift(armature, initial)

    analyze = bpy.ops.character_designer.limb_ik_analyze()
    settings = bpy.context.window_manager.character_designer_limb_ik
    if analyze != {"FINISHED"}:
        raise AssertionError(f"Analyze failed: {analyze}; {settings.last_message}")
    _set_fixed_defaults(settings)
    rebuild = bpy.ops.character_designer.limb_ik_rebuild()
    if rebuild != {"FINISHED"}:
        raise AssertionError(f"Rebuild failed: {rebuild}; {settings.last_message}")

    final = limb_ik._validate_inventory(armature)
    limb_ik._removal_resources(bpy.context, armature, final)
    geometry = _validate_geometry_and_directions(armature, final)
    if real_x._protected_asset_fingerprints() != protected_assets:
        raise AssertionError("Rebuild changed a protected Mesh/Object/shape-key/vertex-group asset")
    if _source_rest_signature(armature, source_names) != source_rest:
        raise AssertionError("Rebuild changed source bone rest data")

    excluded = {name for names in probe.EXPECTED_CHAINS.values() for name in names[:2]}
    unrelated = real_x._compare_source_pose(
        source_pose,
        real_x._source_pose_snapshot(armature, source_names),
        excluded,
    )
    if unrelated["max_position"] > real_x.POSITION_TOLERANCE or unrelated["max_rotation_degrees"] > 0.05:
        raise AssertionError(f"Rebuild changed an unrelated source pose: {unrelated}")
    after_disk = _fingerprint(path)
    if after_disk != before_disk:
        raise AssertionError(f"Input backup changed on disk: {before_disk} -> {after_disk}")
    print("REAL_X_0292_REBUILD_JSON=" + json.dumps({
        "input": str(path),
        "fingerprint": after_disk,
        "repair": repair,
        "geometry": geometry,
        "unrelated_source_pose": unrelated,
    }, sort_keys=True))
    print("PASS real-X 0.29.3 repeat-Rebuild helper + anatomical directions (input unchanged)")


if __name__ == "__main__":
    main()
