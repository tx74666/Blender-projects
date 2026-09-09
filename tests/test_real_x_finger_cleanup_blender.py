"""Read-only validation of the finalized Cosha finger cleanup.

This script opens ``X.blend`` into a disposable background Blender process and
never calls a save or Weight Symmetry apply operator.  It validates the saved
thumb names, legacy-group cleanup, and mirrored finger weights.  Building a
15-bone Weight Symmetry plan must be an idempotent, read-only operation.

Run::

    blender.exe --background --factory-startup --disable-autoexec \
        --python-exit-code 1 --python tests/test_real_x_finger_cleanup_blender.py
"""

from array import array
import hashlib
from pathlib import Path
import sys

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BLEND_PATH = PROJECT_ROOT / "X.blend"
ADDONS_ROOT = PROJECT_ROOT / "addons"

MESH_NAME = "Cosha"
ARMATURE_NAME = "CoshaRig"
EPSILON = 1.0e-8
WEIGHT_TOLERANCE = 1.0e-6
MIRROR_TOLERANCE = 1.0e-6

FINAL_THUMB_BONES = tuple(
    f"thumb.{segment:02d}.{side}"
    for side in ("L", "R")
    for segment in (1, 2, 3)
)

LEFT_FINGER_BONES = (
    "f_index.01.L",
    "f_index.02.L",
    "f_index.03.L",
    "thumb.01.L",
    "thumb.02.L",
    "thumb.03.L",
    "f_middle.01.L",
    "f_middle.02.L",
    "f_middle.03.L",
    "f_ring.01.L",
    "f_ring.02.L",
    "f_ring.03.L",
    "f_pinky.01.L",
    "f_pinky.02.L",
    "f_pinky.03.L",
)

STALE_FINGER_GROUPS = tuple(
    f"{stem}.{side}"
    for side in ("r", "l")
    for stem in (
        "c_pinky1_base",
        "pinky1",
        "c_pinky2",
        "c_pinky3",
        "c_ring1_base",
        "ring1",
        "c_ring2",
        "c_ring3",
        "c_middle1_base",
        "middle1",
        "c_middle2",
        "c_middle3",
        "c_index1_base",
        "index1",
        "c_index2",
        "c_index3",
        "thumb1",
        "c_thumb2",
        "c_thumb3",
    )
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def float_buffer_hash(data, attribute, width):
    values = array("f", [0.0]) * (len(data) * width)
    data.foreach_get(attribute, values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def mesh_coordinate_fingerprint(mesh_obj):
    return (
        len(mesh_obj.data.vertices),
        float_buffer_hash(mesh_obj.data.vertices, "co", 3),
    )


def shape_key_fingerprint(mesh_obj):
    keys = mesh_obj.data.shape_keys
    if keys is None:
        return None
    blocks = []
    for block in keys.key_blocks:
        blocks.append(
            (
                block.name,
                float(block.value),
                float(block.slider_min),
                float(block.slider_max),
                bool(block.mute),
                str(block.interpolation),
                block.relative_key.name if block.relative_key else None,
                block.vertex_group,
                float(block.frame),
                len(block.data),
                float_buffer_hash(block.data, "co", 3),
            )
        )
    return (
        keys.name,
        bool(keys.use_relative),
        float(keys.eval_time),
        keys.reference_key.name if keys.reference_key else None,
        tuple(blocks),
    )


def _pointer_identity(value):
    if value is None:
        return None
    return (
        type(value).__name__,
        getattr(value, "name_full", getattr(value, "name", None)),
        getattr(getattr(value, "library", None), "filepath", None),
    )


def modifier_fingerprint(mesh_obj):
    """Capture all scalar/array/pointer RNA values on every modifier."""

    result = []
    for modifier in mesh_obj.modifiers:
        properties = []
        for prop in modifier.bl_rna.properties:
            identifier = prop.identifier
            if identifier == "rna_type":
                continue
            try:
                value = getattr(modifier, identifier)
            except (AttributeError, RuntimeError, TypeError):
                continue
            if prop.type == "POINTER":
                serialized = _pointer_identity(value)
            elif prop.type in {"BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"}:
                if getattr(prop, "is_array", False):
                    serialized = tuple(value)
                elif isinstance(value, set):
                    serialized = tuple(sorted(value))
                else:
                    serialized = value
            else:
                continue
            properties.append((identifier, serialized))
        try:
            custom = tuple(
                sorted((key, repr(value)) for key, value in modifier.items())
            )
        except TypeError:
            custom = ()
        result.append((modifier.name, modifier.type, tuple(properties), custom))
    return tuple(result)


def _vector_tuple(value):
    return tuple(float(component) for component in value)


def bone_rest_fingerprint(armature_obj):
    """Capture rest transforms and deformation/relation properties, not UI selection."""

    result = {}
    for bone in armature_obj.data.bones:
        result[bone.name] = (
            bone.parent.name if bone.parent else None,
            _vector_tuple(bone.head_local),
            _vector_tuple(bone.tail_local),
            tuple(float(value) for row in bone.matrix_local for value in row),
            bool(bone.use_connect),
            bool(bone.use_deform),
            str(bone.inherit_scale),
            bool(bone.use_inherit_rotation),
            bool(bone.use_local_location),
            bool(bone.use_relative_parent),
            bool(bone.use_envelope_multiply),
            float(bone.head_radius),
            float(bone.tail_radius),
            float(bone.envelope_distance),
            float(bone.envelope_weight),
            float(bone.bbone_x),
            float(bone.bbone_z),
        )
    return result


def deform_totals(mesh_obj, armature_obj):
    deform_indices = {
        mesh_obj.vertex_groups[bone.name].index
        for bone in armature_obj.data.bones
        if bone.use_deform and mesh_obj.vertex_groups.get(bone.name) is not None
    }
    totals = array("d", [0.0]) * len(mesh_obj.data.vertices)
    for vertex in mesh_obj.data.vertices:
        totals[vertex.index] = sum(
            float(membership.weight)
            for membership in vertex.groups
            if membership.group in deform_indices
        )
    return totals


def weight_map(mesh_obj, group_name):
    group = mesh_obj.vertex_groups[group_name]
    result = {}
    for vertex in mesh_obj.data.vertices:
        try:
            weight = float(group.weight(vertex.index))
        except RuntimeError:
            continue
        if weight > EPSILON:
            result[vertex.index] = weight
    return result


def enter_selected_pose_context(mesh_obj, armature_obj, source_names):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="DESELECT")
    for name in source_names:
        armature_obj.pose.bones[name].select = True
    armature_obj.data.bones.active = armature_obj.data.bones[source_names[0]]
    selected = tuple(
        bone.name
        for bone in armature_obj.pose.bones
        if bone.select
    )
    require(selected == source_names, f"Unexpected Pose selection: {selected}")


def validate_thumb_chains(armature_obj):
    for side in ("L", "R"):
        names = tuple(f"thumb.{segment:02d}.{side}" for segment in (1, 2, 3))
        bones = tuple(armature_obj.data.bones[name] for name in names)
        require(all(bone.use_deform for bone in bones), f"{side} thumb is not Deform")
        require(
            bones[1].parent is not None and bones[1].parent.name == bones[0].name,
            f"{names[1]} parent is incorrect",
        )
        require(
            bones[2].parent is not None and bones[2].parent.name == bones[1].name,
            f"{names[2]} parent is incorrect",
        )


def validate_pair_symmetry(mesh_obj, plan):
    source = weight_map(mesh_obj, plan.source_name)
    target = weight_map(mesh_obj, plan.target_name)
    source_side = set(plan.source_indices)
    target_side = set(plan.target_indices)
    pairs = dict(plan.pairs)

    wrong_source = sorted(index for index in source if index in target_side)
    wrong_target = sorted(index for index in target if index in source_side)
    require(
        not wrong_source,
        f'{plan.source_name} retains target-side vertices: {wrong_source[:5]}',
    )
    require(
        not wrong_target,
        f'{plan.target_name} retains source-side vertices: {wrong_target[:5]}',
    )

    source_support = {index: weight for index, weight in source.items() if index in source_side}
    target_support = {index: weight for index, weight in target.items() if index in target_side}
    require(
        set(source_support) == set(pairs),
        f"{plan.source_name} support and spatial plan differ",
    )
    require(
        set(target_support) == set(pairs.values()),
        f"{plan.target_name} support and spatial plan differ",
    )

    vertices = mesh_obj.data.vertices
    for source_index, target_index in pairs.items():
        source_co = vertices[source_index].co
        target_co = vertices[target_index].co
        mirror_error = max(
            abs(float(source_co.x + target_co.x)),
            abs(float(source_co.y - target_co.y)),
            abs(float(source_co.z - target_co.z)),
        )
        require(
            mirror_error <= MIRROR_TOLERANCE,
            f"{plan.source_name} vertex {source_index} mirror error {mirror_error}",
        )
        weight_error = abs(source_support[source_index] - target_support[target_index])
        require(
            weight_error <= WEIGHT_TOLERANCE,
            f"{plan.source_name}/{plan.target_name} weight error {weight_error}",
        )


def main():
    require(BLEND_PATH.is_file(), f"Missing real test file: {BLEND_PATH}")
    before_stat = BLEND_PATH.stat()
    before_hash = file_sha256(BLEND_PATH)
    print(f"REAL_X_FINGER_CLEANUP file_before_sha256={before_hash}")

    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH), load_ui=False)
    mesh_obj = bpy.data.objects.get(MESH_NAME)
    armature_obj = bpy.data.objects.get(ARMATURE_NAME)
    require(mesh_obj is not None and mesh_obj.type == "MESH", "Cosha Mesh not found")
    require(
        armature_obj is not None and armature_obj.type == "ARMATURE",
        "CoshaRig Armature not found",
    )

    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    if str(ADDONS_ROOT) not in sys.path:
        sys.path.insert(0, str(ADDONS_ROOT))
    from character_designer import weight_symmetry

    coords_before = mesh_coordinate_fingerprint(mesh_obj)
    shape_keys_before = shape_key_fingerprint(mesh_obj)
    modifiers_before = modifier_fingerprint(mesh_obj)
    bones_before = bone_rest_fingerprint(armature_obj)
    groups_before = weight_symmetry._capture_vertex_groups(mesh_obj)

    validate_thumb_chains(armature_obj)
    for name in FINAL_THUMB_BONES:
        require(
            armature_obj.data.bones.get(name) is not None,
            f'Missing finalized thumb bone "{name}"',
        )
        require(
            mesh_obj.vertex_groups.get(name) is not None,
            f'Missing finalized thumb Vertex Group "{name}"',
        )
    for name in STALE_FINGER_GROUPS:
        require(
            mesh_obj.vertex_groups.get(name) is None,
            f'Stale finger Vertex Group still exists: "{name}"',
        )

    relevant_prefixes = ("thumb.", "f_index.", "f_middle.", "f_ring.", "f_pinky.")
    relevant_groups = tuple(
        group.name
        for group in mesh_obj.vertex_groups
        if group.name.startswith(relevant_prefixes)
    )
    relevant_bones = tuple(
        bone.name
        for bone in armature_obj.data.bones
        if bone.name.startswith(relevant_prefixes)
    )
    require(
        not any(".001" in name for name in relevant_groups),
        f"Relevant .001 Vertex Groups remain: {relevant_groups}",
    )
    require(
        not any(".001" in name for name in relevant_bones),
        f"Relevant .001 bones remain: {relevant_bones}",
    )

    for source_name in LEFT_FINGER_BONES:
        target_name = source_name[:-1] + "R"
        require(mesh_obj.vertex_groups.get(source_name) is not None, source_name)
        require(mesh_obj.vertex_groups.get(target_name) is not None, target_name)

    deform_before_plan = deform_totals(mesh_obj, armature_obj)
    enter_selected_pose_context(mesh_obj, armature_obj, LEFT_FINGER_BONES)

    batch = weight_symmetry.build_weight_symmetry_batch_plan(bpy.context)
    require(len(batch.plans) == 15, f"Expected 15 plans, got {len(batch.plans)}")
    require(
        tuple(plan.source_name for plan in batch.plans) == LEFT_FINGER_BONES,
        "Batch source order differs from the selected Armature order",
    )
    changed = sum(plan.changed_count for plan in batch.plans)
    cleared = sum(plan.cleared_count for plan in batch.plans)
    paired = sum(plan.paired_count for plan in batch.plans)
    require(changed == 0, f"Final saved weights are not idempotent: changed={changed}")
    require(cleared == 0, f"Final saved weights retain wrong-side data: cleared={cleared}")
    require(
        batch.affected_count == 0,
        f"Read-only plan reports affected={batch.affected_count}",
    )

    for plan in batch.plans:
        validate_pair_symmetry(mesh_obj, plan)

    deform_after_plan = deform_totals(mesh_obj, armature_obj)
    max_deform_delta = max(
        abs(after - before)
        for before, after in zip(deform_before_plan, deform_after_plan)
    )
    require(
        max_deform_delta == 0.0,
        f"Read-only plan changed a per-vertex Deform total by {max_deform_delta}",
    )
    require(
        weight_symmetry._capture_vertex_groups(mesh_obj) == groups_before,
        "Read-only plan changed Vertex Groups",
    )

    require(
        mesh_coordinate_fingerprint(mesh_obj) == coords_before,
        "Base Mesh coordinates changed",
    )
    require(
        shape_key_fingerprint(mesh_obj) == shape_keys_before,
        "Shape Keys changed",
    )
    require(
        modifier_fingerprint(mesh_obj) == modifiers_before,
        "Modifier stack changed",
    )
    require(
        bone_rest_fingerprint(armature_obj) == bones_before,
        "Bone rest transforms/relations changed",
    )

    after_stat = BLEND_PATH.stat()
    after_hash = file_sha256(BLEND_PATH)
    require(after_hash == before_hash, "X.blend bytes changed during background validation")
    require(after_stat.st_size == before_stat.st_size, "X.blend size changed")
    require(
        after_stat.st_mtime_ns == before_stat.st_mtime_ns,
        "X.blend modification timestamp changed",
    )

    print(
        "REAL_X_FINGER_CLEANUP final_plan "
        f"bones={len(batch.plans)} paired={paired} "
        f"changed={changed} cleared={cleared} "
        f"affected={batch.affected_count} max_deform_delta={max_deform_delta:.9g}"
    )
    print(f"REAL_X_FINGER_CLEANUP file_after_sha256={after_hash}")
    print("PASS Final Real X finger cleanup + idempotent read-only 15-bone plan")


if __name__ == "__main__":
    main()
