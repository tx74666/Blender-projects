"""Blender 5.2 regressions for source-bone Finger/Shoulder widgets.

These tests exercise in-memory factory-startup fixtures only.  They never open
or save the production ``X.blend`` file.  Character Designer may decorate
existing source finger and shoulder PoseBones, but it must not manufacture
extra controls for that display-only feature.

Run against the workspace add-on::

    blender --background --factory-startup --python tests/test_limb_ik_source_widgets_blender.py

An alternate add-ons directory (or its ``character_designer`` package) may be
passed after ``--``::

    blender --background --factory-startup --python tests/test_limb_ik_source_widgets_blender.py -- D:/path/to/addons
"""

from __future__ import annotations

import json
import os
import sys

import bpy
from mathutils import Vector


def _requested_addons_root():
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not arguments:
        return None
    requested = os.path.abspath(arguments[0])
    if os.path.basename(requested).lower() == "character_designer":
        requested = os.path.dirname(requested)
    return requested if os.path.isdir(os.path.join(requested, "character_designer")) else None


REQUESTED_ADDONS = _requested_addons_root()
if REQUESTED_ADDONS and REQUESTED_ADDONS not in sys.path:
    # Import the requested package before the shared fixture module adds the
    # workspace source directory to sys.path.
    sys.path.insert(0, REQUESTED_ADDONS)
    from character_designer import limb_ik as _requested_limb_ik
else:
    _requested_limb_ik = None

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import test_limb_ik_blender as base


limb_ik = _requested_limb_ik or base.limb_ik
base.limb_ik = limb_ik

SIDES = ("L", "R")
FINGER_BASES = ("thumb", "f_index", "f_middle", "f_ring", "f_pinky")
FINGER_NAMES = tuple(
    f"{base_name}.{segment:02d}.{side}"
    for side in SIDES
    for base_name in FINGER_BASES
    for segment in range(1, 4)
)
SHOULDER_NAMES = tuple(f"shoulder.{side}" for side in SIDES)
SOURCE_WIDGET_NAMES = frozenset((*FINGER_NAMES, *SHOULDER_NAMES))


def _make_widget_humanoid(name="SourceWidgetRig"):
    armature = base.make_humanoid(name=name)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones
    for side in SIDES:
        sign = 1.0 if side == "L" else -1.0
        hand = edit_bones[f"hand.{side}"]
        for finger_index, base_name in enumerate(FINGER_BASES):
            lane = (finger_index - 2) * 0.026
            head = Vector((1.18 * sign, lane - 0.02, 1.41 - finger_index * 0.002))
            parent = hand
            for segment in range(1, 4):
                length = 0.068 - segment * 0.009
                tail = head + Vector((length * sign, 0.002 * (finger_index - 2), -0.0015 * segment))
                parent = base.add_bone(
                    edit_bones,
                    f"{base_name}.{segment:02d}.{side}",
                    head,
                    tail,
                    parent,
                )
                head = tail
    bpy.ops.object.mode_set(mode="POSE")
    return armature


def _shape_state(pose_bone):
    return {
        "custom_shape": pose_bone.custom_shape,
        "custom_shape_transform": pose_bone.custom_shape_transform,
        "use_bone_size": bool(pose_bone.use_custom_shape_bone_size),
        "scale": tuple(float(value) for value in pose_bone.custom_shape_scale_xyz),
        "translation": tuple(float(value) for value in pose_bone.custom_shape_translation),
        "rotation": tuple(float(value) for value in pose_bone.custom_shape_rotation_euler),
        "wire_width": (
            float(pose_bone.custom_shape_wire_width)
            if hasattr(pose_bone, "custom_shape_wire_width")
            else None
        ),
    }


def _shape_assignment_signature(pose_bone):
    """Stable, value-based signature that survives owned widget recreation."""
    state = _shape_state(pose_bone)
    shape = state["custom_shape"]
    transform = state["custom_shape_transform"]
    return {
        "custom_shape": shape.name if shape is not None else "",
        "custom_shape_data": shape.data.name if shape is not None else "",
        "custom_shape_kind": shape.get(limb_ik.KIND_KEY, "") if shape is not None else "",
        "custom_shape_transform": transform.name if transform is not None else "",
        "use_bone_size": state["use_bone_size"],
        "scale": state["scale"],
        "translation": state["translation"],
        "rotation": state["rotation"],
        "wire_width": state["wire_width"],
    }


def _assert_assignment_signature(actual, expected, label):
    for field in (
        "custom_shape",
        "custom_shape_data",
        "custom_shape_kind",
        "custom_shape_transform",
        "use_bone_size",
    ):
        if actual[field] != expected[field]:
            raise AssertionError(
                f"{label}: {field}={actual[field]!r}, expected={expected[field]!r}"
            )
    for field in ("scale", "translation", "rotation"):
        _assert_vector_close(actual[field], expected[field], f"{label} {field}")
    if actual["wire_width"] is None or expected["wire_width"] is None:
        if actual["wire_width"] != expected["wire_width"]:
            raise AssertionError(f"{label}: wire-width availability changed")
    elif abs(actual["wire_width"] - expected["wire_width"]) > 1.0e-6:
        raise AssertionError(f"{label}: wire width changed")


def _assert_vector_close(actual, expected, label, tolerance=1.0e-6):
    if len(actual) != len(expected) or any(
        abs(float(left) - float(right)) > tolerance
        for left, right in zip(actual, expected)
    ):
        raise AssertionError(f"{label}: actual={tuple(actual)}, expected={tuple(expected)}")


def _assert_shape_state(actual, expected, label):
    if actual["custom_shape"] is not expected["custom_shape"]:
        raise AssertionError(f"{label}: Custom Shape reference changed")
    if actual["custom_shape_transform"] is not expected["custom_shape_transform"]:
        raise AssertionError(f"{label}: Custom Shape Transform reference changed")
    if actual["use_bone_size"] != expected["use_bone_size"]:
        raise AssertionError(f"{label}: use_custom_shape_bone_size changed")
    for field in ("scale", "translation", "rotation"):
        _assert_vector_close(actual[field], expected[field], f"{label} {field}")
    if actual["wire_width"] is not None or expected["wire_width"] is not None:
        if actual["wire_width"] is None or expected["wire_width"] is None:
            raise AssertionError(f"{label}: wire-width availability changed")
        if abs(actual["wire_width"] - expected["wire_width"]) > 1.0e-6:
            raise AssertionError(
                f"{label}: wire width {actual['wire_width']} != {expected['wire_width']}"
            )


def _json_original_state(state):
    return {
        "custom_shape": state["custom_shape"].name if state["custom_shape"] is not None else "",
        "custom_shape_transform": (
            state["custom_shape_transform"].name
            if state["custom_shape_transform"] is not None
            else ""
        ),
        "use_bone_size": state["use_bone_size"],
        "scale": list(state["scale"]),
        "translation": list(state["translation"]),
        "rotation": list(state["rotation"]),
        "wire_width": state["wire_width"],
    }


def _assert_registry_original(record, expected, label):
    original = record.get("original")
    if not isinstance(original, dict):
        raise AssertionError(f"{label}: registry has no original display state")
    serialized = _json_original_state(expected)
    for field in ("custom_shape", "custom_shape_transform", "use_bone_size"):
        if original.get(field) != serialized[field]:
            raise AssertionError(
                f"{label}: original {field}={original.get(field)!r}, expected={serialized[field]!r}"
            )
    for field in ("scale", "translation", "rotation"):
        _assert_vector_close(original.get(field, ()), serialized[field], f"{label} original {field}")
    expected_width = serialized["wire_width"]
    actual_width = original.get("wire_width")
    if expected_width is None:
        if actual_width is not None:
            raise AssertionError(f"{label}: unexpected saved wire width {actual_width}")
    elif actual_width is None or abs(float(actual_width) - expected_width) > 1.0e-6:
        raise AssertionError(f"{label}: original wire width was not saved")


def _source_registry(armature):
    if not hasattr(limb_ik, "SOURCE_WIDGETS_KEY"):
        raise AssertionError("limb_ik.SOURCE_WIDGETS_KEY is missing")
    raw = armature.data.get(limb_ik.SOURCE_WIDGETS_KEY)
    if not isinstance(raw, str) or not raw:
        raise AssertionError("ARM build did not create the source-widget registry")
    payload = json.loads(raw)
    if not isinstance(payload.get("bones"), dict):
        raise AssertionError(f"Malformed source-widget registry: {payload}")
    return payload


def _downgrade_source_registry_to_v1_midpoints(armature):
    """Recreate the exact display contract written by source-widget v1."""
    if limb_ik.SOURCE_WIDGETS_VERSION != 2:
        raise AssertionError(
            f"Expected source-widget registry v2, got {limb_ik.SOURCE_WIDGETS_VERSION}"
        )
    payload = _source_registry(armature)
    if payload.get("version") != limb_ik.SOURCE_WIDGETS_VERSION:
        raise AssertionError(f"Can only downgrade a current registry, got {payload.get('version')}")
    payload["version"] = limb_ik.LEGACY_SOURCE_WIDGETS_VERSION
    for bone_name, record in payload["bones"].items():
        if record["kind"] != "FINGER":
            continue
        midpoint = [0.0, float(armature.data.bones[bone_name].length) * 0.5, 0.0]
        record["generated"]["translation"] = midpoint
        armature.pose.bones[bone_name].custom_shape_translation = midpoint
    raw = limb_ik._canonical_json(payload)
    armature.data[limb_ik.SOURCE_WIDGETS_KEY] = raw
    limb_ik._validate_source_widget_assignments(armature, payload)
    return raw


def _owned_widget_by_kind(armature, kind):
    armature_id = armature.data.get(limb_ik.ARMATURE_ID_KEY, "")
    matches = [
        obj
        for obj in bpy.data.objects
        if limb_ik._owned(obj, armature_id, role="WIDGET")
        and obj.get(limb_ik.KIND_KEY) == kind
    ]
    if len(matches) != 1:
        raise AssertionError(f"Expected one shared {kind} widget, found {[obj.name for obj in matches]}")
    return matches[0]


def _stable_arm_bones():
    expected = {"CTRL_master"}
    for side in SIDES:
        expected.update(
            {
                f"CTRL_hand_IK.{side}",
                f"CTRL_elbow_pole.{side}",
                f"VIS_elbow_pole_line.{side}",
                f"MCH_elbow_pole_aim.{side}",
                f"MCH_upper_arm_IK.{side}",
                f"MCH_forearm_IK.{side}",
                f"ORI_upper_arm_IK.{side}",
                f"ORI_forearm_IK.{side}",
            }
        )
    return expected


def _direct_arm_bones():
    # Direct schema 5 still exposes only Target + Pole to the animator, but it
    # owns one hidden, non-deforming Pole-display aim helper per limb.  Source
    # Finger/Shoulder decoration must not add anything beyond this baseline.
    return {
        f"{stem}.{side}"
        for side in SIDES
        for stem in ("CTRL_hand_IK", "CTRL_elbow_pole", "MCH_elbow_pole_aim")
    }


def _configure_distinct_original_state(armature, bone_name="f_index.02.L"):
    pose_bone = armature.pose.bones[bone_name]
    pose_bone.use_custom_shape_bone_size = True
    pose_bone.custom_shape_scale_xyz = (0.83, 1.17, 0.91)
    pose_bone.custom_shape_translation = (0.012, -0.023, 0.034)
    pose_bone.custom_shape_rotation_euler = (0.11, -0.22, 0.33)
    if hasattr(pose_bone, "custom_shape_wire_width"):
        pose_bone.custom_shape_wire_width = 3.25


def _build_arms(method):
    armature = _make_widget_humanoid(name=f"{method}SourceWidgetRig")
    _configure_distinct_original_state(armature)
    original = {name: _shape_state(armature.pose.bones[name]) for name in SOURCE_WIDGET_NAMES}
    source_bones = {bone.name for bone in armature.data.bones}
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = method
    if bpy.ops.character_designer.limb_ik_build_arm() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    bpy.context.view_layer.update()
    return armature, original, source_bones, settings


def _assert_arm_widget_contract(armature, original, source_bones, expected_generated):
    generated = {bone.name for bone in base.owned_bones(armature)}
    if generated != expected_generated:
        raise AssertionError(
            "Source-widget decoration changed the generated-bone contract: "
            f"actual={sorted(generated)}, expected={sorted(expected_generated)}"
        )
    current_bones = {bone.name for bone in armature.data.bones}
    if current_bones != source_bones | expected_generated:
        raise AssertionError(
            "Finger/Shoulder decoration created additional bones: "
            f"extras={sorted(current_bones - source_bones - expected_generated)}"
        )
    if any(armature.data.bones[name].get(limb_ik.OWNER_KEY) for name in SOURCE_WIDGET_NAMES):
        raise AssertionError("A source Finger/Shoulder bone was retagged as generated data")

    registry = _source_registry(armature)
    if registry.get("version") != limb_ik.SOURCE_WIDGETS_VERSION:
        raise AssertionError(
            f"Source-widget registry was not upgraded to v{limb_ik.SOURCE_WIDGETS_VERSION}: "
            f"{registry.get('version')}"
        )
    if set(registry["bones"]) != SOURCE_WIDGET_NAMES:
        raise AssertionError(
            f"Registry source set changed: actual={sorted(registry['bones'])}, "
            f"expected={sorted(SOURCE_WIDGET_NAMES)}"
        )
    finger_widget = _owned_widget_by_kind(armature, "FINGER")
    shoulder_widget = _owned_widget_by_kind(armature, "SHOULDER")
    if len(finger_widget.data.vertices) != 32 or len(finger_widget.data.edges) != 32:
        raise AssertionError("FINGER widget topology must remain 32 vertices / 32 edges")
    if len(shoulder_widget.data.vertices) != 44 or len(shoulder_widget.data.edges) != 44:
        raise AssertionError("SHOULDER widget topology must remain 44 vertices / 44 edges")

    for bone_name in SOURCE_WIDGET_NAMES:
        record = registry["bones"][bone_name]
        expected_kind = "FINGER" if bone_name in FINGER_NAMES else "SHOULDER"
        expected_side = bone_name.rsplit(".", 1)[-1]
        if record.get("kind") != expected_kind or record.get("side") != expected_side:
            raise AssertionError(f"{bone_name}: wrong registry routing {record}")
        pose_bone = armature.pose.bones[bone_name]
        expected_widget = finger_widget if expected_kind == "FINGER" else shoulder_widget
        if pose_bone.custom_shape is not expected_widget:
            raise AssertionError(f"{bone_name}: did not share the {expected_kind} widget")
        if pose_bone.custom_shape_transform is not None:
            raise AssertionError(f"{bone_name}: unexpected Custom Shape Transform bone")
        if pose_bone.use_custom_shape_bone_size:
            raise AssertionError(f"{bone_name}: source widget still scales from bone-size mode")
        if expected_kind == "FINGER":
            _assert_vector_close(
                pose_bone.custom_shape_translation,
                (0.0, 0.0, 0.0),
                f"{bone_name} joint-centered Finger widget",
            )
            _assert_vector_close(
                record["generated"]["translation"],
                (0.0, 0.0, 0.0),
                f"{bone_name} registry Finger translation",
            )
        _assert_registry_original(record, original[bone_name], bone_name)

    if armature.pose.bones["f_index.01.L"].custom_shape_scale_xyz.x <= 0.0:
        raise AssertionError("Left Finger widget lost its positive local-X scale")
    if armature.pose.bones["f_index.01.R"].custom_shape_scale_xyz.x >= 0.0:
        raise AssertionError("Right Finger widget was not mirrored in local X")


def _assert_remove_restores(armature, original):
    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        settings = bpy.context.window_manager.character_designer_limb_ik
        raise AssertionError(settings.last_message)
    if limb_ik.SOURCE_WIDGETS_KEY in armature.data:
        raise AssertionError("Remove left the source-widget registry behind")
    if base.owned_bones(armature):
        raise AssertionError("Remove left generated bones behind")
    for bone_name, expected in original.items():
        _assert_shape_state(_shape_state(armature.pose.bones[bone_name]), expected, bone_name)
    armature_id = armature.data.get(limb_ik.ARMATURE_ID_KEY, "")
    remaining = [
        obj.name
        for obj in bpy.data.objects
        if obj.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        and (not armature_id or obj.get(limb_ik.ARMATURE_ID_KEY) == armature_id)
        and obj.get(limb_ik.KIND_KEY) in {"FINGER", "SHOULDER"}
    ]
    if remaining:
        raise AssertionError(f"Remove left source widgets behind: {remaining}")


def test_stable_source_widgets_share_geometry_add_zero_bones_and_restore_exactly():
    base.reset_scene()
    armature, original, source_bones, _settings = _build_arms("ROLL_DECOUPLED")
    _assert_arm_widget_contract(armature, original, source_bones, _stable_arm_bones())
    _assert_remove_restores(armature, original)


def test_direct_source_widgets_keep_minimal_bone_contract_and_restore_exactly():
    base.reset_scene()
    armature, original, source_bones, _settings = _build_arms("DIRECT_PREROLL")
    expected_generated = _direct_arm_bones()
    _assert_arm_widget_contract(armature, original, source_bones, expected_generated)
    inventory = limb_ik._validate_inventory(armature)
    if (
        inventory["schema"] != limb_ik.DIRECT_PREROLL_SCHEMA
        or len(inventory["bones"]) != 6
        or len(inventory["records"]) != 8
    ):
        raise AssertionError(
            "Source-widget decoration changed the schema-5 Direct two-arm baseline"
        )
    for rig in inventory["rigs"].values():
        display = rig["display"]
        if (
            display is None
            or display.name not in expected_generated
            or display.parent is None
            or display.parent.name != rig["pole"].name
            or display.use_connect
            or display.use_deform
            or not display.hide
            or not display.hide_select
        ):
            raise AssertionError(
                "Source-widget decoration altered a hidden Direct Pole-display helper"
            )
    _assert_remove_restores(armature, original)


def _artist_widget(name="ArtistFingerWidget"):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(((-0.1, 0.0, 0.0), (0.1, 0.0, 0.0), (0.0, 0.0, 0.15)), ((0, 1), (1, 2), (2, 0)), ())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def test_foreign_source_custom_shape_is_skipped_and_preserved():
    base.reset_scene()
    armature = _make_widget_humanoid(name="ForeignShapeRig")
    protected_name = "thumb.01.L"
    protected = armature.pose.bones[protected_name]
    artist_widget = _artist_widget()
    protected.custom_shape = artist_widget
    protected.use_custom_shape_bone_size = False
    protected.custom_shape_scale_xyz = (0.37, 0.41, 0.43)
    protected.custom_shape_translation = (0.01, 0.02, 0.03)
    protected.custom_shape_rotation_euler = (0.04, 0.05, 0.06)
    before = _shape_state(protected)

    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if bpy.ops.character_designer.limb_ik_build_arm() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    registry = _source_registry(armature)
    expected = SOURCE_WIDGET_NAMES - {protected_name}
    if set(registry["bones"]) != expected:
        raise AssertionError(
            f"Foreign-shaped source bone was not skipped exactly: {sorted(registry['bones'])}"
        )
    _assert_shape_state(_shape_state(protected), before, "foreign source shape after Build")

    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_shape_state(_shape_state(protected), before, "foreign source shape after Remove")
    if bpy.data.objects.get(artist_widget.name) is not artist_widget:
        raise AssertionError("Remove deleted an artist-owned source widget")


def test_tampered_source_widget_makes_remove_fail_closed():
    base.reset_scene()
    armature, _original, _source_bones, settings = _build_arms("ROLL_DECOUPLED")
    registry_raw = armature.data[limb_ik.SOURCE_WIDGETS_KEY]
    registry = json.loads(registry_raw)
    victim_name = "f_middle.02.R"
    victim = armature.pose.bones[victim_name]
    generated_scale = tuple(registry["bones"][victim_name]["generated"]["scale"])
    victim.custom_shape_scale_xyz.x *= 1.5
    owned_before = {bone.name for bone in base.owned_bones(armature)}

    if base.cancelled_result(
        lambda: bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT")
    ) != {"CANCELLED"}:
        raise AssertionError("Remove accepted a tampered source-widget display assignment")
    if armature.data.get(limb_ik.SOURCE_WIDGETS_KEY) != registry_raw:
        raise AssertionError("Refused Remove rewrote the source-widget registry")
    if {bone.name for bone in base.owned_bones(armature)} != owned_before:
        raise AssertionError("Refused Remove partially deleted the generated rig")
    if victim.custom_shape is None:
        raise AssertionError("Refused Remove cleared the tampered source widget")

    # Restore the owned contract so this test can verify the normal cleanup
    # path too, without leaving shared data for the following test.
    victim.custom_shape_scale_xyz = generated_scale
    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(settings.last_message)


def test_v1_midpoint_registry_rebuilds_to_joint_centers_and_remove_restores_originals():
    base.reset_scene()
    armature, original, source_bones, settings = _build_arms("ROLL_DECOUPLED")
    legacy_raw = _downgrade_source_registry_to_v1_midpoints(armature)
    legacy = json.loads(legacy_raw)
    if legacy.get("version") != limb_ik.LEGACY_SOURCE_WIDGETS_VERSION:
        raise AssertionError("Legacy fixture did not retain source-widget registry v1")
    for bone_name in FINGER_NAMES:
        expected = (0.0, float(armature.data.bones[bone_name].length) * 0.5, 0.0)
        _assert_vector_close(
            armature.pose.bones[bone_name].custom_shape_translation,
            expected,
            f"{bone_name} v1 midpoint fixture",
        )

    if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_arm_widget_contract(armature, original, source_bones, _stable_arm_bones())
    _assert_remove_restores(armature, original)


def test_tampered_v1_midpoint_registry_refuses_migration_without_overwrite():
    base.reset_scene()
    armature, original, _source_bones, settings = _build_arms("ROLL_DECOUPLED")
    legacy_raw = _downgrade_source_registry_to_v1_midpoints(armature)
    victim_name = "f_ring.02.L"
    victim = armature.pose.bones[victim_name]
    victim.custom_shape_translation.x += 0.019
    assignments_before = {
        name: _shape_assignment_signature(armature.pose.bones[name])
        for name in SOURCE_WIDGET_NAMES
    }
    owned_before = {bone.name for bone in base.owned_bones(armature)}

    if base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild) != {"CANCELLED"}:
        raise AssertionError("Rebuild accepted an artist-edited v1 Finger display assignment")
    if armature.data.get(limb_ik.SOURCE_WIDGETS_KEY) != legacy_raw:
        raise AssertionError("Refused v1 migration rewrote the legacy registry")
    if {bone.name for bone in base.owned_bones(armature)} != owned_before:
        raise AssertionError("Refused v1 migration partially changed the generated rig")
    for bone_name, expected in assignments_before.items():
        _assert_assignment_signature(
            _shape_assignment_signature(armature.pose.bones[bone_name]),
            expected,
            f"Refused v1 migration {bone_name}",
        )

    # Restore the owned v1 contract and verify that legacy Remove still uses
    # the untouched original snapshots rather than the new joint-center state.
    legacy = json.loads(legacy_raw)
    victim.custom_shape_translation = legacy["bones"][victim_name]["generated"]["translation"]
    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    for bone_name, expected in original.items():
        _assert_shape_state(_shape_state(armature.pose.bones[bone_name]), expected, bone_name)


def test_leg_only_build_never_creates_or_assigns_source_widgets():
    base.reset_scene()
    armature = _make_widget_humanoid(name="LegOnlySourceWidgetRig")
    before = {name: _shape_state(armature.pose.bones[name]) for name in SOURCE_WIDGET_NAMES}
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if bpy.ops.character_designer.limb_ik_build_leg() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if limb_ik.SOURCE_WIDGETS_KEY in armature.data:
        raise AssertionError("LEG-only Build created an ARM source-widget registry")
    armature_id = armature.data.get(limb_ik.ARMATURE_ID_KEY, "")
    unexpected = [
        obj.name
        for obj in bpy.data.objects
        if limb_ik._owned(obj, armature_id, role="WIDGET")
        and obj.get(limb_ik.KIND_KEY) in {"FINGER", "SHOULDER"}
    ]
    if unexpected:
        raise AssertionError(f"LEG-only Build created ARM source widgets: {unexpected}")
    for bone_name, expected in before.items():
        _assert_shape_state(_shape_state(armature.pose.bones[bone_name]), expected, bone_name)


def test_initial_build_failure_after_source_decoration_rolls_back_exactly():
    base.reset_scene()
    armature = _make_widget_humanoid(name="SourceWidgetBuildRollbackRig")
    _configure_distinct_original_state(armature)
    original = {name: _shape_state(armature.pose.bones[name]) for name in SOURCE_WIDGET_NAMES}
    source_bones = {bone.name for bone in armature.data.bones}
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)

    original_create = limb_ik._create_constraints_and_shapes
    calls = {"count": 0}

    def fail_after_source_decoration(*args, **kwargs):
        calls["count"] += 1
        original_create(*args, **kwargs)
        raise RuntimeError("injected failure after source-widget decoration")

    limb_ik._create_constraints_and_shapes = fail_after_source_decoration
    try:
        if base.cancelled_result(
            bpy.ops.character_designer.limb_ik_build_arm
        ) != {"CANCELLED"}:
            raise AssertionError("Injected post-decoration Build failure did not cancel")
    finally:
        limb_ik._create_constraints_and_shapes = original_create
    if calls["count"] != 1:
        raise AssertionError(f"Post-decoration Build injection ran {calls['count']} times")

    if {bone.name for bone in armature.data.bones} != source_bones:
        raise AssertionError("Failed initial Build left generated or deleted source bones")
    if base.owned_bones(armature) or limb_ik._owned_constraint_records(armature):
        raise AssertionError("Failed initial Build left owned bones or constraints")
    if limb_ik.SOURCE_WIDGETS_KEY in armature.data:
        raise AssertionError("Failed initial Build left SOURCE_WIDGETS_KEY")
    if limb_ik.ARMATURE_ID_KEY in armature.data or limb_ik.SCHEMA_KEY in armature.data:
        raise AssertionError("Failed initial Build left Armature ownership metadata")
    for bone_name, expected in original.items():
        _assert_shape_state(
            _shape_state(armature.pose.bones[bone_name]),
            expected,
            f"Build rollback {bone_name}",
        )

    owned_widgets = [
        obj.name
        for obj in bpy.data.objects
        if obj.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        and obj.get(limb_ik.ROLE_KEY) == "WIDGET"
    ]
    owned_widget_data = [
        mesh.name
        for mesh in bpy.data.meshes
        if mesh.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        and mesh.get(limb_ik.ROLE_KEY) == "WIDGET_DATA"
    ]
    if owned_widgets or owned_widget_data:
        raise AssertionError(
            "Failed initial Build left owned widget resources: "
            f"objects={owned_widgets}, meshes={owned_widget_data}"
        )
    if bpy.data.collections.get(limb_ik.WIDGET_COLLECTION_NAME) is not None:
        raise AssertionError("Failed initial Build left its widget collection")
    if armature.data.collections.get(limb_ik.CONTROL_COLLECTION_NAME) is not None:
        raise AssertionError("Failed initial Build left its control Bone Collection")


def test_failed_rebuild_restores_source_registry_assignments_and_old_rig_ids():
    base.reset_scene()
    armature, original, _source_bones, settings = _build_arms("ROLL_DECOUPLED")
    inventory_before = limb_ik._validate_inventory(armature)
    old_rig_ids = {rig["rig_id"] for rig in inventory_before["rigs"].values()}
    registry_raw = armature.data[limb_ik.SOURCE_WIDGETS_KEY]
    registry_before = json.loads(registry_raw)
    if set(registry_before["bones"]) != SOURCE_WIDGET_NAMES:
        raise AssertionError("Rebuild fixture does not contain all 32 source controls")
    assignments_before = {
        name: _shape_assignment_signature(armature.pose.bones[name])
        for name in SOURCE_WIDGET_NAMES
    }

    original_create = limb_ik._create_constraints_and_shapes
    calls = {"count": 0}

    def fail_first_new_rig_after_source_decoration(*args, **kwargs):
        calls["count"] += 1
        result = original_create(*args, **kwargs)
        if calls["count"] == 1:
            raise RuntimeError("injected Rebuild failure after source-widget decoration")
        return result

    limb_ik._create_constraints_and_shapes = fail_first_new_rig_after_source_decoration
    try:
        if base.cancelled_result(
            bpy.ops.character_designer.limb_ik_rebuild
        ) != {"CANCELLED"}:
            raise AssertionError("Injected post-decoration Rebuild failure did not cancel")
    finally:
        limb_ik._create_constraints_and_shapes = original_create
    if calls["count"] < 2:
        raise AssertionError("Failed Rebuild did not invoke old-rig snapshot recovery")

    inventory_after = limb_ik._validate_inventory(armature)
    restored_rig_ids = {rig["rig_id"] for rig in inventory_after["rigs"].values()}
    if restored_rig_ids != old_rig_ids:
        raise AssertionError(
            f"Failed Rebuild changed old rig IDs: {restored_rig_ids} != {old_rig_ids}"
        )
    if armature.data.get(limb_ik.SOURCE_WIDGETS_KEY) != registry_raw:
        raise AssertionError("Failed Rebuild did not restore exact SOURCE_WIDGETS_KEY JSON")
    registry_after = _source_registry(armature)
    if registry_after != registry_before:
        raise AssertionError("Failed Rebuild changed parsed source-widget registry data")
    for bone_name, expected in assignments_before.items():
        _assert_assignment_signature(
            _shape_assignment_signature(armature.pose.bones[bone_name]),
            expected,
            f"Rebuild recovery {bone_name}",
        )
    _owned_widget_by_kind(armature, "FINGER")
    _owned_widget_by_kind(armature, "SHOULDER")

    # Recovery must leave a normal, removable old rig, not merely data that
    # happens to resemble it at the first inspection.
    _assert_remove_restores(armature, original)


def test_failed_rebuild_restores_exact_registry_after_source_eligibility_drift():
    base.reset_scene()
    armature = _make_widget_humanoid(name="SourceWidgetEligibilityDriftRig")
    victim_name = "thumb.01.L"
    victim = armature.pose.bones[victim_name]
    artist_widget = _artist_widget("EligibilityDriftArtistWidget")
    # Keep the old snapshot free of the entire FINGER widget kind.  Clearing
    # one assignment later makes recovery create a new kind as well as a new
    # record, exercising cleanup of both forms of eligibility drift.
    for finger_name in FINGER_NAMES:
        armature.pose.bones[finger_name].custom_shape = artist_widget
    victim.use_custom_shape_bone_size = False
    victim.custom_shape_scale_xyz = (0.39, 0.43, 0.47)
    victim.custom_shape_translation = (0.013, -0.021, 0.034)
    victim.custom_shape_rotation_euler = (0.07, -0.11, 0.19)

    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if bpy.ops.character_designer.limb_ik_build_arm() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    registry_raw = armature.data[limb_ik.SOURCE_WIDGETS_KEY]
    if victim_name in json.loads(registry_raw)["bones"]:
        raise AssertionError("Artist-shaped eligibility fixture was unexpectedly registered")
    old_rig_ids = {
        rig["rig_id"]
        for rig in limb_ik._validate_inventory(armature)["rigs"].values()
    }
    registered_before = {
        name: _shape_assignment_signature(armature.pose.bones[name])
        for name in SOURCE_WIDGET_NAMES
        if name != victim_name
    }

    # Clearing an unowned artist display while the rig exists is legal.  It
    # makes this Finger newly eligible for the next source-decoration pass.
    victim.custom_shape = None
    victim_at_snapshot = _shape_state(victim)

    original_create = limb_ik._create_constraints_and_shapes
    calls = {"count": 0}

    def fail_first_new_rig_after_source_decoration(*args, **kwargs):
        calls["count"] += 1
        result = original_create(*args, **kwargs)
        if calls["count"] == 1:
            raise RuntimeError("injected Rebuild failure after eligibility drift")
        return result

    limb_ik._create_constraints_and_shapes = fail_first_new_rig_after_source_decoration
    try:
        if base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild) != {"CANCELLED"}:
            raise AssertionError("Eligibility-drift Rebuild failure did not cancel")
    finally:
        limb_ik._create_constraints_and_shapes = original_create
    if calls["count"] < 2:
        raise AssertionError("Eligibility-drift failure did not invoke old-rig recovery")

    recovered = limb_ik._validate_inventory(armature)
    if {rig["rig_id"] for rig in recovered["rigs"].values()} != old_rig_ids:
        raise AssertionError("Eligibility-drift recovery changed or lost the old rig IDs")
    if armature.data.get(limb_ik.SOURCE_WIDGETS_KEY) != registry_raw:
        raise AssertionError("Eligibility-drift recovery did not restore exact registry JSON")
    if victim_name in recovered["source_widgets"]["bones"]:
        raise AssertionError("Recovery retained the newly eligible Finger in the old registry")
    _assert_shape_state(_shape_state(victim), victim_at_snapshot, "eligibility-drift victim")
    for bone_name, expected in registered_before.items():
        _assert_assignment_signature(
            _shape_assignment_signature(armature.pose.bones[bone_name]),
            expected,
            f"eligibility-drift recovery {bone_name}",
        )

    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_shape_state(_shape_state(victim), victim_at_snapshot, "eligibility-drift Remove")
    if bpy.data.objects.get(artist_widget.name) is not artist_widget:
        raise AssertionError("Eligibility-drift recovery deleted the artist widget Object")


def test_failed_v1_rebuild_recovers_exact_legacy_registry_and_midpoints():
    base.reset_scene()
    armature, original, _source_bones, settings = _build_arms("ROLL_DECOUPLED")
    legacy_raw = _downgrade_source_registry_to_v1_midpoints(armature)
    assignments_before = {
        name: _shape_assignment_signature(armature.pose.bones[name])
        for name in SOURCE_WIDGET_NAMES
    }
    inventory_before = limb_ik._validate_inventory(armature)
    old_rig_ids = {rig["rig_id"] for rig in inventory_before["rigs"].values()}

    original_create = limb_ik._create_constraints_and_shapes
    calls = {"count": 0}

    def fail_first_new_rig_after_source_decoration(*args, **kwargs):
        calls["count"] += 1
        result = original_create(*args, **kwargs)
        if calls["count"] == 1:
            raise RuntimeError("injected v1 Rebuild failure after source-widget decoration")
        return result

    limb_ik._create_constraints_and_shapes = fail_first_new_rig_after_source_decoration
    try:
        if base.cancelled_result(bpy.ops.character_designer.limb_ik_rebuild) != {"CANCELLED"}:
            raise AssertionError("Injected v1 Rebuild failure did not cancel")
    finally:
        limb_ik._create_constraints_and_shapes = original_create
    if calls["count"] < 2:
        raise AssertionError("Failed v1 Rebuild did not invoke old-rig snapshot recovery")

    inventory_after = limb_ik._validate_inventory(armature)
    restored_rig_ids = {rig["rig_id"] for rig in inventory_after["rigs"].values()}
    if restored_rig_ids != old_rig_ids:
        raise AssertionError(
            f"Failed v1 Rebuild changed old rig IDs: {restored_rig_ids} != {old_rig_ids}"
        )
    if armature.data.get(limb_ik.SOURCE_WIDGETS_KEY) != legacy_raw:
        raise AssertionError("Failed v1 Rebuild did not restore exact legacy registry JSON")
    for bone_name, expected in assignments_before.items():
        _assert_assignment_signature(
            _shape_assignment_signature(armature.pose.bones[bone_name]),
            expected,
            f"v1 Rebuild recovery {bone_name}",
        )
    _assert_remove_restores(armature, original)


def test_incremental_selected_arms_merge_source_registry_without_duplicates():
    base.reset_scene()
    armature = _make_widget_humanoid(name="IncrementalSourceWidgetRig")
    _configure_distinct_original_state(armature)
    original = {name: _shape_state(armature.pose.bones[name]) for name in SOURCE_WIDGET_NAMES}
    source_bones = {bone.name for bone in armature.data.bones}
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "ROLL_DECOUPLED"

    settings.selected_limb = "LEFT_ARM"
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    left_sources = {name for name in SOURCE_WIDGET_NAMES if name.endswith(".L")}
    left_registry = _source_registry(armature)
    if set(left_registry["bones"]) != left_sources or len(left_registry["bones"]) != 16:
        raise AssertionError(
            "Left selected Build did not decorate exactly 15 Fingers + shoulder.L: "
            f"{sorted(left_registry['bones'])}"
        )
    left_generated = {
        name
        for name in _stable_arm_bones()
        if name == "CTRL_master" or name.endswith(".L")
    }
    actual_bones = {bone.name for bone in armature.data.bones}
    if actual_bones != source_bones | left_generated:
        raise AssertionError(
            "Left selected source decoration added unexpected bones: "
            f"{sorted(actual_bones - source_bones - left_generated)}"
        )
    left_finger_widget = _owned_widget_by_kind(armature, "FINGER")
    left_shoulder_widget = _owned_widget_by_kind(armature, "SHOULDER")
    for bone_name in left_sources:
        expected_widget = (
            left_finger_widget if bone_name in FINGER_NAMES else left_shoulder_widget
        )
        if armature.pose.bones[bone_name].custom_shape is not expected_widget:
            raise AssertionError(f"Left selected Build did not decorate '{bone_name}'")
    for bone_name in SOURCE_WIDGET_NAMES - left_sources:
        _assert_shape_state(
            _shape_state(armature.pose.bones[bone_name]),
            original[bone_name],
            f"Left selected Build touched unbuilt {bone_name}",
        )

    # A saved one-sided v1 registry must be migrated transactionally before
    # the second side is added.  Existing records move from midpoint to joint;
    # new records are born at the joint.
    _downgrade_source_registry_to_v1_midpoints(armature)

    settings.selected_limb = "RIGHT_ARM"
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    _assert_arm_widget_contract(armature, original, source_bones, _stable_arm_bones())
    if _owned_widget_by_kind(armature, "FINGER") is not left_finger_widget:
        raise AssertionError("Right selected Build duplicated/replaced the shared FINGER widget")
    if _owned_widget_by_kind(armature, "SHOULDER") is not left_shoulder_widget:
        raise AssertionError("Right selected Build duplicated/replaced the shared SHOULDER widget")
    _assert_remove_restores(armature, original)


def test_failed_incremental_v1_migration_rolls_back_registry_and_display_exactly():
    base.reset_scene()
    armature = _make_widget_humanoid(name="FailedIncrementalV1MigrationRig")
    _configure_distinct_original_state(armature)
    original = {name: _shape_state(armature.pose.bones[name]) for name in SOURCE_WIDGET_NAMES}
    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    settings.build_method = "ROLL_DECOUPLED"
    settings.selected_limb = "LEFT_ARM"
    if bpy.ops.character_designer.limb_ik_build_selected() != {"FINISHED"}:
        raise AssertionError(settings.last_message)

    legacy_raw = _downgrade_source_registry_to_v1_midpoints(armature)
    assignments_before = {
        name: _shape_assignment_signature(armature.pose.bones[name])
        for name in SOURCE_WIDGET_NAMES
    }
    bones_before = {bone.name for bone in armature.data.bones}
    original_create = limb_ik._create_constraints_and_shapes

    def fail_after_v1_migration(*args, **kwargs):
        result = original_create(*args, **kwargs)
        raise RuntimeError("injected failure after in-place v1 source-widget migration")

    settings.selected_limb = "RIGHT_ARM"
    limb_ik._create_constraints_and_shapes = fail_after_v1_migration
    try:
        if base.cancelled_result(bpy.ops.character_designer.limb_ik_build_selected) != {"CANCELLED"}:
            raise AssertionError("Injected incremental v1 migration failure did not cancel")
    finally:
        limb_ik._create_constraints_and_shapes = original_create

    if armature.data.get(limb_ik.SOURCE_WIDGETS_KEY) != legacy_raw:
        raise AssertionError("Failed incremental v1 migration did not restore exact registry JSON")
    if {bone.name for bone in armature.data.bones} != bones_before:
        raise AssertionError("Failed incremental v1 migration left generated bones behind")
    for bone_name, expected in assignments_before.items():
        _assert_assignment_signature(
            _shape_assignment_signature(armature.pose.bones[bone_name]),
            expected,
            f"Incremental v1 rollback {bone_name}",
        )
    recovered = limb_ik._validate_inventory(armature)
    if recovered["source_widgets"].get("version") != limb_ik.LEGACY_SOURCE_WIDGETS_VERSION:
        raise AssertionError("Failed incremental migration did not recover a valid v1 inventory")
    _assert_remove_restores(armature, original)


def test_pre_source_widget_rig_removes_and_rebuild_migrates_to_full_registry():
    base.reset_scene()
    armature = _make_widget_humanoid(name="PreSourceWidgetRig")
    _configure_distinct_original_state(armature)
    original = {name: _shape_state(armature.pose.bones[name]) for name in SOURCE_WIDGET_NAMES}
    source_bones = {bone.name for bone in armature.data.bones}

    def build_0297_style_rig(settings):
        plans = limb_ik._plans_for_kind(bpy.context, armature, settings, "ARM")
        limb_ik._build_plans(
            bpy.context,
            armature,
            plans,
            schema=limb_ik.CURRENT_SCHEMA,
            decorate_source_widgets=False,
        )
        inventory = limb_ik._validate_inventory(armature)
        if inventory.get("source_widgets") is not None:
            raise AssertionError("0.29.7-style fixture unexpectedly has source-widget inventory")
        if limb_ik.SOURCE_WIDGETS_KEY in armature.data:
            raise AssertionError("0.29.7-style fixture unexpectedly has SOURCE_WIDGETS_KEY")
        armature_id = inventory["armature_id"]
        unexpected = [
            obj.name
            for obj in bpy.data.objects
            if limb_ik._owned(obj, armature_id, role="WIDGET")
            and obj.get(limb_ik.KIND_KEY) in {"FINGER", "SHOULDER"}
        ]
        if unexpected:
            raise AssertionError(f"0.29.7-style fixture has new source widgets: {unexpected}")
        if {bone.name for bone in armature.data.bones} != source_bones | _stable_arm_bones():
            raise AssertionError("0.29.7-style fixture changed the generated-bone contract")
        for bone_name, expected in original.items():
            _assert_shape_state(
                _shape_state(armature.pose.bones[bone_name]),
                expected,
                f"0.29.7-style {bone_name}",
            )
        return inventory

    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    build_0297_style_rig(settings)
    if bpy.ops.character_designer.limb_ik_remove("EXEC_DEFAULT") != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    if base.owned_bones(armature) or limb_ik.SOURCE_WIDGETS_KEY in armature.data:
        raise AssertionError("Remove left residue from the 0.29.7-style rig")
    for bone_name, expected in original.items():
        _assert_shape_state(
            _shape_state(armature.pose.bones[bone_name]),
            expected,
            f"0.29.7-style Remove {bone_name}",
        )

    result, settings = base.analyze(armature)
    if result != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    old_inventory = build_0297_style_rig(settings)
    old_rig_ids = {rig["rig_id"] for rig in old_inventory["rigs"].values()}
    if bpy.ops.character_designer.limb_ik_rebuild() != {"FINISHED"}:
        raise AssertionError(settings.last_message)
    migrated = limb_ik._validate_inventory(armature)
    migrated_ids = {rig["rig_id"] for rig in migrated["rigs"].values()}
    if old_rig_ids & migrated_ids:
        raise AssertionError("Rebuild migration retained a pre-0.29.8 rig ID")
    _assert_arm_widget_contract(armature, original, source_bones, _stable_arm_bones())
    registry = _source_registry(armature)
    if len(registry["bones"]) != 32 or set(registry["bones"]) != SOURCE_WIDGET_NAMES:
        raise AssertionError("Normal Rebuild did not migrate to all 30 Finger + 2 Shoulder records")
    _assert_remove_restores(armature, original)


def main():
    base.ensure_registered()
    tests = (
        test_stable_source_widgets_share_geometry_add_zero_bones_and_restore_exactly,
        test_direct_source_widgets_keep_minimal_bone_contract_and_restore_exactly,
        test_foreign_source_custom_shape_is_skipped_and_preserved,
        test_tampered_source_widget_makes_remove_fail_closed,
        test_v1_midpoint_registry_rebuilds_to_joint_centers_and_remove_restores_originals,
        test_tampered_v1_midpoint_registry_refuses_migration_without_overwrite,
        test_leg_only_build_never_creates_or_assigns_source_widgets,
        test_initial_build_failure_after_source_decoration_rolls_back_exactly,
        test_failed_rebuild_restores_source_registry_assignments_and_old_rig_ids,
        test_failed_rebuild_restores_exact_registry_after_source_eligibility_drift,
        test_failed_v1_rebuild_recovers_exact_legacy_registry_and_midpoints,
        test_incremental_selected_arms_merge_source_registry_without_duplicates,
        test_failed_incremental_v1_migration_rolls_back_registry_and_display_exactly,
        test_pre_source_widget_rig_removes_and_rebuild_migrates_to_full_registry,
    )
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        base.reset_scene()
        base.ensure_unregistered()
    print(f"PASS Limb IK source widgets {len(tests)} tests")


if __name__ == "__main__":
    main()
