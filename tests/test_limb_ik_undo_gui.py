"""Two-phase Blender GUI Undo/Redo check for Character Designer Limb IK.

The first process builds and saves a disposable humanoid fixture.  A second,
normal Blender window opens that file as the global Undo baseline and invokes
the production build and Remove operators through real key events.  Passing
``--build-all`` covers Build All as one Undo/Redo step; the default retains the
legacy Build Arms plus incremental Build Legs compatibility path.  The test
never opens or saves the user's X.blend.

The GUI phase must be launched with Blender's ``--enable-event-simulate``.
"""

import json
import sys
import traceback
from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT / "addons", PROJECT_ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import character_designer
from character_designer import limb_ik, selected_bone_weights
from test_limb_ik_blender import make_humanoid


STATE = {}
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
EXPECTED_CONTROLS = {
    "CTRL_master",
    "CTRL_hand_IK.L",
    "CTRL_elbow_pole.L",
    "VIS_elbow_pole_line.L",
    "MCH_elbow_pole_aim.L",
    "CTRL_hand_IK.R",
    "CTRL_elbow_pole.R",
    "VIS_elbow_pole_line.R",
    "MCH_elbow_pole_aim.R",
    "MCH_upper_arm_IK.L",
    "MCH_forearm_IK.L",
    "ORI_upper_arm_IK.L",
    "ORI_forearm_IK.L",
    "MCH_upper_arm_IK.R",
    "MCH_forearm_IK.R",
    "ORI_upper_arm_IK.R",
    "ORI_forearm_IK.R",
}
EXPECTED_ALL_CONTROLS = EXPECTED_CONTROLS | {
    "CTRL_foot_IK.L",
    "CTRL_knee_pole.L",
    "VIS_knee_pole_line.L",
    "MCH_knee_pole_aim.L",
    "CTRL_heel_roll.L",
    "MCH_foot_target.L",
    "CTRL_foot_IK.R",
    "CTRL_knee_pole.R",
    "VIS_knee_pole_line.R",
    "MCH_knee_pole_aim.R",
    "CTRL_heel_roll.R",
    "MCH_foot_target.R",
    "MCH_thigh_IK.L",
    "MCH_shin_IK.L",
    "ORI_thigh_IK.L",
    "ORI_shin_IK.L",
    "MCH_thigh_IK.R",
    "MCH_shin_IK.R",
    "ORI_thigh_IK.R",
    "ORI_shin_IK.R",
}
LEGACY_CONTROLS = {
    "CTRL_hand_IK.L",
    "CTRL_elbow_pole.L",
    "CTRL_hand_IK.R",
    "CTRL_elbow_pole.R",
}


def _freeze(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze(item)) for key, item in value.items()))
    if hasattr(value, "to_list"):
        return _freeze(value.to_list())
    if isinstance(value, (tuple, list, set)) or (
        hasattr(value, "__iter__") and not isinstance(value, (str, bytes))
    ):
        return tuple(_freeze(item) for item in value)
    return repr(value)


def _id_properties(owner):
    try:
        keys = tuple(owner.keys())
    except (AttributeError, ReferenceError, TypeError):
        return ()
    return tuple(sorted((str(key), _freeze(owner[key])) for key in keys))


def view3d_context():
    window = bpy.context.window_manager.windows[0]
    area = next(area for area in window.screen.areas if area.type == "VIEW_3D")
    region = next(region for region in area.regions if region.type == "WINDOW")
    x = area.x + region.x + max(1, region.width // 2)
    y = area.y + region.y + max(1, region.height // 2)
    return window, area, region, x, y


def cleanup_keymap():
    keymap = STATE.get("keymap")
    item = STATE.get("keymap_item")
    if keymap is not None and item is not None:
        try:
            keymap.keymap_items.remove(item)
        except (ReferenceError, RuntimeError):
            pass
    STATE["keymap_item"] = None


def fail(stage, exc):
    print(f"FAIL Limb IK GUI Undo/Redo at {stage}: {exc}", flush=True)
    traceback.print_exc()
    try:
        cleanup_keymap()
        if hasattr(bpy.types.WindowManager, "character_designer_limb_ik"):
            character_designer.unregister()
    finally:
        bpy.ops.wm.quit_blender()
    return None


def simulate_key(key_type, *, ctrl=False, shift=False):
    window = STATE["window"]
    x = STATE["event_x"]
    y = STATE["event_y"]
    window.event_simulate(
        type=key_type,
        value="PRESS",
        ctrl=ctrl,
        shift=shift,
        x=x,
        y=y,
    )
    window.event_simulate(
        type=key_type,
        value="RELEASE",
        ctrl=ctrl,
        shift=shift,
        x=x,
        y=y,
    )


def install_binding(operator_idname):
    cleanup_keymap()
    keymap = STATE["keymap"]
    item = keymap.keymap_items.new(
        operator_idname,
        "F8",
        "PRESS",
        head=True,
    )
    STATE["keymap_item"] = item
    bpy.context.window_manager.keyconfigs.update()


def _bone_signature(bone):
    return (
        bone.name,
        bone.parent.name if bone.parent else "",
        _freeze(bone.head_local),
        _freeze(bone.tail_local),
        _freeze(bone.matrix_local),  # Rest matrix contains the exact Bone Roll.
        bool(bone.use_deform),
        bool(bone.use_connect),
        tuple(sorted(collection.name for collection in bone.collections)),
        _id_properties(bone),
    )


def source_bone_signature(armature):
    names = tuple(
        bone.name
        for bone in armature.data.bones
        if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
    )
    expected = STATE.get("source_names")
    if expected is not None and names != expected:
        raise AssertionError(f"Source Bone order/set changed: expected={expected}, actual={names}")
    return tuple(_bone_signature(armature.data.bones[name]) for name in names)


def weight_signature():
    mesh_obj = bpy.data.objects[STATE["mesh_name"]]
    return selected_bone_weights._capture_vertex_groups(mesh_obj)


def source_pose_signature(armature):
    result = []
    for name in STATE["source_names"]:
        pose_bone = armature.pose.bones[name]
        result.append(
            (
                name,
                _id_properties(pose_bone),
                tuple((constraint.name, constraint.type) for constraint in pose_bone.constraints),
            )
        )
    return tuple(result)


def clean_rig_signature(armature):
    owned_bones = tuple(
        sorted(
            bone.name
            for bone in armature.data.bones
            if bone.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        )
    )
    owned_objects = tuple(
        sorted(
            obj.name
            for obj in bpy.data.objects
            if obj.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        )
    )
    owned_meshes = tuple(
        sorted(
            mesh.name
            for mesh in bpy.data.meshes
            if mesh.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        )
    )
    owned_collections = tuple(
        sorted(
            collection.name
            for collection in bpy.data.collections
            if collection.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        )
    )
    owned_bone_collections = tuple(
        sorted(
            collection.name
            for collection in armature.data.collections
            if collection.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE
        )
    )
    return (
        armature.data.get(limb_ik.ARMATURE_ID_KEY),
        armature.data.get(limb_ik.SCHEMA_KEY),
        owned_bones,
        owned_objects,
        owned_meshes,
        owned_collections,
        owned_bone_collections,
        source_pose_signature(armature),
    )


def _constraint_signature(armature, pose_bone, constraint, record):
    properties = []
    for name in (
        "subtarget",
        "pole_subtarget",
        "chain_count",
        "pole_angle",
        "target_space",
        "owner_space",
        "mix_mode",
        "use_tail",
        "use_stretch",
        "track_axis",
        "use_limit_x",
        "min_x",
        "max_x",
        "use_x",
        "use_y",
        "use_z",
        "invert_x",
        "invert_y",
        "invert_z",
        "influence",
        "mute",
    ):
        if hasattr(constraint, name):
            properties.append((name, _freeze(getattr(constraint, name))))
    return (
        pose_bone.name,
        constraint.name,
        constraint.type,
        constraint.target.name if getattr(constraint, "target", None) else "",
        constraint.pole_target.name
        if getattr(constraint, "pole_target", None)
        else "",
        tuple(properties),
        _freeze(record),
    )


def _rig_signature(armature, *, schema, expected_controls, expected_records, expected_rigs=None):
    inventory = limb_ik._validate_inventory(armature)
    if inventory["schema"] != schema:
        raise AssertionError(f"Expected schema {schema}, got {inventory['schema']}")
    expected_rigs = expected_rigs or {("ARM", "L"), ("ARM", "R")}
    if set(inventory["rigs"]) != expected_rigs:
        raise AssertionError(f"Unexpected built rig sides: {sorted(inventory['rigs'])}")
    if {bone.name for bone in inventory["bones"]} != expected_controls:
        raise AssertionError(
            f"Unexpected Arm control set: {sorted(bone.name for bone in inventory['bones'])}"
        )
    if len(inventory["records"]) != expected_records:
        raise AssertionError(
            f"Expected {expected_records} owned constraints, got {len(inventory['records'])}"
        )
    resources = limb_ik._removal_resources(bpy.context, armature, inventory)

    controls = []
    for name in sorted(expected_controls):
        bone = armature.data.bones[name]
        pose_bone = armature.pose.bones[name]
        if bone.use_deform:
            raise AssertionError(f"Generated control '{name}' unexpectedly deforms")
        controls.append(
            (
                _bone_signature(bone),
                pose_bone.rotation_mode,
                _freeze(pose_bone.matrix_basis),
                pose_bone.custom_shape.name if pose_bone.custom_shape else "",
            )
        )

    constraints = tuple(
        sorted(
            _constraint_signature(armature, pose_bone, constraint, record)
            for pose_bone, constraint, record in inventory["records"]
        )
    )
    widgets = []
    for obj in sorted(resources["widget_objects"], key=lambda item: item.name):
        mesh = obj.data
        widgets.append(
            (
                obj.name,
                mesh.name,
                tuple(collection.name for collection in obj.users_collection),
                _id_properties(obj),
                _id_properties(mesh),
                tuple(_freeze(vertex.co) for vertex in mesh.vertices),
                tuple(tuple(vertex for vertex in edge.vertices) for edge in mesh.edges),
            )
        )
    collection = resources["control_collection"]
    control_collection = (
        collection.name,
        _id_properties(collection),
        tuple(sorted(bone.name for bone in collection.bones)),
    )
    widget_collection = (
        resources["widget_collection"].name,
        _id_properties(resources["widget_collection"]),
        tuple(sorted(obj.name for obj in resources["widget_collection"].objects)),
    )
    return (
        inventory["armature_id"],
        tuple(sorted((kind, side, rig["rig_id"], tuple(rig["chain"])) for (kind, side), rig in inventory["rigs"].items())),
        tuple(controls),
        constraints,
        control_collection,
        widget_collection,
        tuple(widgets),
    )


def built_rig_signature(armature):
    build_all = bool(STATE.get("build_all"))
    return _rig_signature(
        armature,
        schema=limb_ik.CURRENT_SCHEMA,
        expected_controls=EXPECTED_ALL_CONTROLS if build_all else EXPECTED_CONTROLS,
        expected_records=47 if build_all else 23,
        expected_rigs={
            ("ARM", "L"), ("ARM", "R"), ("LEG", "L"), ("LEG", "R")
        } if build_all else None,
    )


def legacy_rig_signature(armature):
    return _rig_signature(
        armature,
        schema=limb_ik.LEGACY_SCHEMA,
        expected_controls=LEGACY_CONTROLS,
        expected_records=4,
    )


def assert_source_unchanged(stage):
    armature = bpy.data.objects[STATE["armature_name"]]
    bpy.context.view_layer.update()
    actual_bones = source_bone_signature(armature)
    if actual_bones != STATE["source_bones"]:
        raise AssertionError(f"{stage}: source Bone topology/rest matrices (including Roll) changed")
    actual_weights = weight_signature()
    if actual_weights != STATE["weights"]:
        raise AssertionError(f"{stage}: original Vertex Group weights changed")


def assert_clean(stage):
    armature = bpy.data.objects[STATE["armature_name"]]
    assert_source_unchanged(stage)
    actual = clean_rig_signature(armature)
    if actual != STATE["clean"]:
        raise AssertionError(f"{stage}: generated rig was not completely absent: {actual}")


def assert_built(stage):
    armature = bpy.data.objects[STATE["armature_name"]]
    assert_source_unchanged(stage)
    actual = built_rig_signature(armature)
    if actual != STATE["built"]:
        raise AssertionError(f"{stage}: exact generated rig was not restored")


def assert_visual_pose(stage):
    armature = bpy.data.objects[STATE["armature_name"]]
    bpy.context.view_layer.update()
    for name, expected in STATE["transport_pose"].items():
        actual = armature.pose.bones[name].matrix
        location_error = (actual.translation - expected.translation).length
        rotation_error = actual.to_quaternion().rotation_difference(expected.to_quaternion()).angle
        scale_error = (actual.to_scale() - expected.to_scale()).length
        if location_error > 8.0e-4 or rotation_error > 7.0e-3 or scale_error > 1.5e-3:
            raise AssertionError(
                f"{stage}: visual pose changed for '{name}': "
                f"location={location_error}, rotation={rotation_error}, scale={scale_error}"
            )


def assert_matrix_close(actual, expected, stage, *, location=8.0e-4, rotation=7.0e-3, scale=1.5e-3):
    location_error = (actual.translation - expected.translation).length
    rotation_error = actual.to_quaternion().rotation_difference(expected.to_quaternion()).angle
    scale_error = (actual.to_scale() - expected.to_scale()).length
    if location_error > location or rotation_error > rotation or scale_error > scale:
        raise AssertionError(
            f"{stage}: location={location_error}, rotation={rotation_error}, scale={scale_error}"
        )


def build_fixture(filepath, *, legacy=False):
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    armature = make_humanoid(
        name="LimbUndoRig",
        near_straight=False,
        include_right=True,
        roll_offset=0.43,
    )
    bpy.ops.object.mode_set(mode="OBJECT")

    mesh_data = bpy.data.meshes.new("LimbUndoMeshData")
    mesh_data.from_pydata(
        (
            (-0.6, -0.2, 0.0),
            (-0.2, -0.2, 0.0),
            (0.2, -0.2, 0.0),
            (0.6, -0.2, 0.0),
            (-0.6, 0.2, 0.0),
            (-0.2, 0.2, 0.0),
            (0.2, 0.2, 0.0),
            (0.6, 0.2, 0.0),
        ),
        (),
        ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6)),
    )
    mesh_data.update()
    mesh_obj = bpy.data.objects.new("LimbUndoMesh", mesh_data)
    bpy.context.scene.collection.objects.link(mesh_obj)
    assignments = (
        ("Chest", False, {0: 0.8, 1: 0.6, 4: 0.8, 5: 0.6}),
        ("Hips", False, {0: 0.2, 4: 0.2}),
        ("upper_arm.L", False, {1: 0.4, 2: 0.7}),
        ("forearm.L", False, {2: 0.3, 3: 0.65}),
        ("hand.L", True, {3: 0.35}),
        ("upper_arm.R", False, {5: 0.4, 6: 0.7}),
        ("forearm.R", False, {6: 0.3, 7: 0.65}),
        ("hand.R", False, {7: 0.35}),
    )
    for name, locked, weights in assignments:
        group = mesh_obj.vertex_groups.new(name=name)
        group.lock_weight = locked
        for vertex_index, weight in weights.items():
            group.add((vertex_index,), weight, "REPLACE")
    modifier = mesh_obj.modifiers.new("LimbUndoArmature", "ARMATURE")
    modifier.object = armature

    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="POSE")
    armature.data.bones.active = armature.data.bones["upper_arm.L"]
    armature.pose.bones["upper_arm.L"].select = True

    if legacy:
        character_designer.register()
        try:
            result = bpy.ops.character_designer.limb_ik_analyze()
            settings = bpy.context.window_manager.character_designer_limb_ik
            if result != {"FINISHED"}:
                raise AssertionError(f"Legacy fixture Analyze failed: {settings.last_message}")
            plans = limb_ik._plans_for_kind(bpy.context, armature, settings, "ARM")
            limb_ik._build_plans(
                bpy.context,
                armature,
                plans,
                schema=limb_ik.LEGACY_SCHEMA,
            )
            inventory = limb_ik._validate_inventory(armature)
            if (
                inventory["schema"] != limb_ik.LEGACY_SCHEMA
                or {bone.name for bone in inventory["bones"]} != LEGACY_CONTROLS
                or len(inventory["records"]) != 4
            ):
                raise AssertionError("Legacy Undo fixture did not build exact schema-1 Arms")
        finally:
            character_designer.unregister()
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="POSE") if armature.mode != "POSE" else None
        armature.data.bones.active = armature.data.bones["upper_arm.L"]
        armature.pose.bones["upper_arm.L"].select = True

    result = bpy.ops.wm.save_as_mainfile(filepath=filepath, check_existing=False)
    if result != {"FINISHED"}:
        raise AssertionError(f"Could not save Limb IK Undo fixture: {result}")
    label = "legacy" if legacy else "clean"
    print(f"PASS Built {label} Limb IK Undo fixture: {filepath}", flush=True)


def setup_and_build():
    try:
        bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
        bpy.context.preferences.edit.use_global_undo = True
        character_designer.register()

        armature = bpy.data.objects["LimbUndoRig"]
        mesh_obj = bpy.data.objects["LimbUndoMesh"]
        bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.mode != "OBJECT" else None
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="POSE")
        armature.data.bones.active = armature.data.bones["upper_arm.L"]
        armature.pose.bones["upper_arm.L"].select = True

        STATE.update(
            armature_name=armature.name,
            mesh_name=mesh_obj.name,
            source_names=tuple(bone.name for bone in armature.data.bones),
            build_all="--build-all" in ARGS,
        )
        STATE["source_bones"] = source_bone_signature(armature)
        STATE["weights"] = selected_bone_weights._capture_vertex_groups(mesh_obj)
        STATE["clean"] = clean_rig_signature(armature)
        if any(STATE["clean"][index] for index in range(7)):
            raise AssertionError(f"Fixture contains generated Limb IK data: {STATE['clean']}")

        result = bpy.ops.character_designer.limb_ik_analyze()
        settings = bpy.context.window_manager.character_designer_limb_ik
        if result != {"FINISHED"}:
            raise AssertionError(f"Analyze failed: {settings.last_message}")
        payload = json.loads(settings.analysis_json)
        expected_kinds = limb_ik.KINDS if STATE["build_all"] else ("ARM",)
        if any(
            payload["limbs"][kind][side]["status"] not in {"READY", "WARNING"}
            for kind in expected_kinds
            for side in limb_ik.SIDES
        ):
            raise AssertionError("Analyze did not resolve every requested Build chain")

        window_manager = bpy.context.window_manager
        keymap = window_manager.keyconfigs.active.keymaps.get("3D View")
        if keymap is None:
            raise AssertionError("The active 3D View keymap is unavailable")
        STATE["keymap"] = keymap
        window, _area, _region, x, y = view3d_context()
        STATE.update(window=window, event_x=x, event_y=y)
        if STATE["build_all"]:
            # Invoke the public operator in the real GUI/window context, then
            # drive its global Undo/Redo through actual key events below.
            bpy.ops.ed.undo_push(message="Build All GUI baseline")
            if bpy.ops.character_designer.limb_ik_build_all() != {"FINISHED"}:
                raise AssertionError("Build All GUI operator call did not finish")
            bpy.ops.ed.undo_push(message="Build All GUI result")
        else:
            install_binding("character_designer.limb_ik_build_arm")
            simulate_key("F8")
        bpy.app.timers.register(verify_build, first_interval=0.65)
    except Exception as exc:
        return fail("setup/Build All" if STATE.get("build_all") else "setup/Build Arms", exc)
    return None


def verify_build():
    try:
        armature = bpy.data.objects[STATE["armature_name"]]
        label = "Build All" if STATE["build_all"] else "Build Arms"
        assert_source_unchanged(label)
        STATE["built"] = built_rig_signature(armature)
        simulate_key("Z", ctrl=True)
        bpy.app.timers.register(verify_build_undo, first_interval=0.65)
    except Exception as exc:
        return fail("Build All result" if STATE.get("build_all") else "Build Arms result", exc)
    return None


def verify_build_undo():
    try:
        label = "Build All" if STATE["build_all"] else "Build Arms"
        assert_clean(f"one Ctrl+Z after {label}")
        simulate_key("Z", ctrl=True, shift=True)
        bpy.app.timers.register(verify_build_redo, first_interval=0.65)
    except Exception as exc:
        return fail("Build All single Undo" if STATE.get("build_all") else "Build Arms single Undo", exc)
    return None


def verify_build_redo():
    try:
        label = "Build All" if STATE["build_all"] else "Build Arms"
        assert_built(f"one Ctrl+Shift+Z after {label}")
        if STATE["build_all"]:
            install_binding("character_designer.limb_ik_remove")
            simulate_key("F8")
            bpy.app.timers.register(confirm_remove, first_interval=0.3)
            return None
        armature = bpy.data.objects[STATE["armature_name"]]
        master = armature.pose.bones[limb_ik.MASTER_NAME]
        master.rotation_mode = "XYZ"
        master.location = (0.23, -0.14, 0.09)
        master.rotation_euler = (0.08, -0.05, 0.16)
        master.scale = (1.06, 1.06, 1.06)
        bpy.context.view_layer.update()
        bpy.ops.ed.undo_push(message="Moved Master Build Legs baseline")
        STATE["master_basis"] = master.matrix_basis.copy()
        tracked = STATE["source_names"] + (
            "CTRL_hand_IK.L",
            "CTRL_hand_IK.R",
            "CTRL_elbow_pole.L",
            "CTRL_elbow_pole.R",
        )
        STATE["transport_pose"] = {
            name: armature.pose.bones[name].matrix.copy()
            for name in tracked
        }
        STATE["built"] = built_rig_signature(armature)
        install_binding("character_designer.limb_ik_build_leg")
        simulate_key("F8")
        bpy.app.timers.register(verify_moved_master_build_legs, first_interval=0.8)
    except Exception as exc:
        return fail("Build All single Redo" if STATE.get("build_all") else "Build Arms single Redo", exc)
    return None


def verify_moved_master_build_legs():
    try:
        armature = bpy.data.objects[STATE["armature_name"]]
        inventory = limb_ik._validate_inventory(armature)
        if set(inventory["rigs"]) != {
            ("ARM", "L"),
            ("ARM", "R"),
            ("LEG", "L"),
            ("LEG", "R"),
        }:
            raise AssertionError("Moved-Master Build Legs did not generate all four limbs")
        if len(inventory["bones"]) != 37 or len(inventory["records"]) != 47:
            raise AssertionError("Moved-Master Build Legs generated an unexpected inventory")
        assert_matrix_close(
            armature.pose.bones[limb_ik.MASTER_NAME].matrix_basis,
            STATE["master_basis"],
            "Moved-Master Build Legs did not restore the Master basis",
        )
        assert_visual_pose("moved-Master Build Legs")
        simulate_key("Z", ctrl=True)
        bpy.app.timers.register(verify_moved_master_build_legs_undo, first_interval=0.8)
    except Exception as exc:
        return fail("moved-Master Build Legs result", exc)
    return None


def verify_moved_master_build_legs_undo():
    try:
        assert_built("one Ctrl+Z after moved-Master Build Legs")
        assert_visual_pose("one Ctrl+Z after moved-Master Build Legs")
        install_binding("character_designer.limb_ik_remove")
        simulate_key("F8")
        bpy.app.timers.register(confirm_remove, first_interval=0.3)
    except Exception as exc:
        return fail("moved-Master Build Legs single Undo", exc)
    return None


def confirm_remove():
    try:
        simulate_key("RET")
        bpy.app.timers.register(verify_remove, first_interval=0.7)
    except Exception as exc:
        return fail("Remove confirmation", exc)
    return None


def verify_remove():
    try:
        assert_clean("Remove")
        simulate_key("Z", ctrl=True)
        bpy.app.timers.register(verify_remove_undo, first_interval=0.7)
    except Exception as exc:
        return fail("Remove result", exc)
    return None


def verify_remove_undo():
    try:
        assert_built("one Ctrl+Z after Remove")
        simulate_key("Z", ctrl=True, shift=True)
        bpy.app.timers.register(verify_remove_redo, first_interval=0.7)
    except Exception as exc:
        return fail("Remove single Undo", exc)
    return None


def verify_remove_redo():
    try:
        assert_clean("one Ctrl+Shift+Z after Remove")
        build_all = STATE["build_all"]
        result = {
            "build_operator": "Build All" if build_all else "Build Arms",
            "build_controls": len(EXPECTED_ALL_CONTROLS if build_all else EXPECTED_CONTROLS),
            "build_constraints": 47 if build_all else 23,
            "build_single_undo": "clean",
            "build_single_redo": "restored",
            "remove_single_undo": "restored",
            "remove_single_redo": "clean",
            "source_bones": len(STATE["source_names"]),
            "vertex_groups": len(STATE["weights"]),
        }
        if not build_all:
            result.update(
                moved_master_build_legs="visual-pose-preserved",
                moved_master_build_legs_single_undo="arm-rig-restored",
            )
        print(f"LIMB_IK_GUI_UNDO_JSON={json.dumps(result, sort_keys=True)}", flush=True)
        print("PASS Limb IK GUI single-step Build/Remove Undo/Redo", flush=True)
        cleanup_keymap()
        character_designer.unregister()
        bpy.ops.wm.quit_blender()
    except Exception as exc:
        return fail("Remove single Redo", exc)
    return None


def setup_legacy_rebuild():
    try:
        bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
        bpy.context.preferences.edit.use_global_undo = True
        character_designer.register()

        armature = bpy.data.objects["LimbUndoRig"]
        mesh_obj = bpy.data.objects["LimbUndoMesh"]
        bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.mode != "OBJECT" else None
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode="POSE")
        armature.data.bones.active = armature.data.bones["upper_arm.L"]
        armature.pose.bones["upper_arm.L"].select = True

        STATE.update(
            armature_name=armature.name,
            mesh_name=mesh_obj.name,
            source_names=tuple(
                bone.name
                for bone in armature.data.bones
                if bone.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE
            ),
        )
        STATE["source_bones"] = source_bone_signature(armature)
        STATE["weights"] = selected_bone_weights._capture_vertex_groups(mesh_obj)
        STATE["legacy"] = legacy_rig_signature(armature)

        result = bpy.ops.character_designer.limb_ik_analyze()
        settings = bpy.context.window_manager.character_designer_limb_ik
        if result != {"FINISHED"}:
            raise AssertionError(f"Legacy Rebuild Analyze failed: {settings.last_message}")

        window_manager = bpy.context.window_manager
        keymap = window_manager.keyconfigs.active.keymaps.get("3D View")
        if keymap is None:
            raise AssertionError("The active 3D View keymap is unavailable")
        STATE["keymap"] = keymap
        window, _area, _region, x, y = view3d_context()
        STATE.update(window=window, event_x=x, event_y=y)
        install_binding("character_designer.limb_ik_rebuild")
        simulate_key("F8")
        bpy.app.timers.register(verify_legacy_rebuild, first_interval=0.8)
    except Exception as exc:
        return fail("setup/legacy Rebuild", exc)
    return None


def verify_legacy_rebuild():
    try:
        armature = bpy.data.objects[STATE["armature_name"]]
        assert_source_unchanged("legacy Rebuild")
        STATE["current"] = built_rig_signature(armature)
        simulate_key("Z", ctrl=True)
        bpy.app.timers.register(verify_legacy_rebuild_undo, first_interval=0.8)
    except Exception as exc:
        return fail("legacy Rebuild result", exc)
    return None


def verify_legacy_rebuild_undo():
    try:
        armature = bpy.data.objects[STATE["armature_name"]]
        assert_source_unchanged("one Ctrl+Z after legacy Rebuild")
        if legacy_rig_signature(armature) != STATE["legacy"]:
            raise AssertionError("one Ctrl+Z did not restore the exact schema-1 rig")
        simulate_key("Z", ctrl=True, shift=True)
        bpy.app.timers.register(verify_legacy_rebuild_redo, first_interval=0.8)
    except Exception as exc:
        return fail("legacy Rebuild single Undo", exc)
    return None


def verify_legacy_rebuild_redo():
    try:
        armature = bpy.data.objects[STATE["armature_name"]]
        assert_source_unchanged("one Ctrl+Shift+Z after legacy Rebuild")
        if built_rig_signature(armature) != STATE["current"]:
            raise AssertionError("one Ctrl+Shift+Z did not restore the exact current-schema rig")
        result = {
            "legacy_controls": len(LEGACY_CONTROLS),
            "legacy_constraints": 4,
            "current_controls": len(EXPECTED_CONTROLS),
            "current_constraints": 23,
            "rebuild_single_undo": "schema1-restored",
            "rebuild_single_redo": f"schema{limb_ik.CURRENT_SCHEMA}-restored",
        }
        print(f"LIMB_IK_GUI_LEGACY_REBUILD_JSON={json.dumps(result, sort_keys=True)}", flush=True)
        print("PASS Limb IK GUI single-step legacy Rebuild Undo/Redo", flush=True)
        cleanup_keymap()
        character_designer.unregister()
        bpy.ops.wm.quit_blender()
    except Exception as exc:
        return fail("legacy Rebuild single Redo", exc)
    return None


if ARGS and ARGS[0] in {"--build-fixture", "--build-legacy-fixture"}:
    if len(ARGS) != 2:
        raise SystemExit("Expected --build-fixture/--build-legacy-fixture <absolute .blend path>")
    build_fixture(ARGS[1], legacy=ARGS[0] == "--build-legacy-fixture")
elif ARGS and ARGS[0] == "--legacy-rebuild":
    bpy.app.timers.register(setup_legacy_rebuild, first_interval=0.5)
else:
    bpy.app.timers.register(setup_and_build, first_interval=0.5)
