"""Real Blender preview cancels when a mode menu enters armature Edit Mode.

The scene, modes, preview and window timer are real. The modal handler receives
a TIMER-shaped event directly because background Blender runs INVOKE_DEFAULT
as execute(). No GUI or production file is used. Run with --background
--factory-startup --python-exit-code 1 --python.
"""
import os
import sys
from types import SimpleNamespace

import bpy

TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS)
sys.path.insert(0, os.path.join(os.path.dirname(TESTS), "addons"))

import character_designer
from character_designer import forearm_twist as runtime, limb_ik
from test_forearm_twist_blender import pose_snapshot, assert_pose_snapshot, key_snapshot
from test_forearm_twist_paired_ui_blender import select_controller, assert_pose_context
from test_forearm_twist_symmetry_blender import fixture


def main():
    mesh, armature, _left, _right = fixture()
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    for side in ("L", "R"):
        armature.data.edit_bones["upper_arm." + side].head.z = 0.16
    bpy.ops.object.mode_set(mode="OBJECT")
    modifier = mesh.modifiers.new("Armature", "ARMATURE")
    modifier.object = armature
    character_designer.register()
    assert bpy.ops.character_designer.limb_ik_analyze() == {"FINISHED"}
    assert bpy.ops.character_designer.limb_ik_build_all() == {"FINISHED"}
    inventory = limb_ik._validate_inventory(armature)
    target = armature.pose.bones[inventory["rigs"][("ARM", "R")]["target"].name]
    select_controller(armature, target)

    assert bpy.ops.character_designer.forearm_twist_start("EXEC_DEFAULT") == {"FINISHED"}
    runtime.set_ratio(bpy.context, 2, 0.31)
    assert bpy.ops.character_designer.forearm_twist_finish(action="CONFIRM") == {"FINISHED"}
    assert_pose_context(armature, target)
    before_records = mesh[runtime.RECORD_KEY]
    before_pose = pose_snapshot(armature)
    key_names = tuple(key.name for key in mesh.data.shape_keys.key_blocks)
    before_keys = key_snapshot(mesh, key_names)

    assert bpy.ops.character_designer.forearm_twist_start("EXEC_DEFAULT") == {"FINISHED"}
    timer = bpy.context.window_manager.event_timer_add(0.2, window=bpy.context.window)
    errors = []
    modal = SimpleNamespace(_timer=timer, report=lambda kinds, message: errors.append(message))
    runtime._SESSION["modal"] = True
    runtime.set_ratio(bpy.context, 2, 0.79)
    assert mesh[runtime.RECORD_KEY] != before_records
    # Selection of the same bound Armature is valid in Object/Pose mode.
    mesh.select_set(False)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    event = SimpleNamespace(type="TIMER", value="NOTHING", ctrl=False)
    handler = runtime.CHARACTERDESIGNER_OT_forearm_twist_start.modal
    assert handler(modal, bpy.context, event) == {"PASS_THROUGH"}
    assert runtime._SESSION is not None

    # A mode-menu change does not send the intercepted Tab key event.
    bpy.ops.object.mode_set(mode="EDIT")
    assert bpy.context.mode == "EDIT_ARMATURE"
    assert runtime.context_mesh(bpy.context) == mesh
    assert handler(modal, bpy.context, event) == {"CANCELLED"}
    bpy.context.view_layer.update()
    assert runtime._SESSION is None and runtime.PREVIEW_KEY not in mesh
    assert_pose_context(armature, target)
    assert_pose_snapshot(armature, before_pose, "Armature Edit Mode cancellation")
    assert mesh[runtime.RECORD_KEY] == before_records
    after_keys = key_snapshot(mesh, key_names)
    assert set(after_keys) == set(before_keys)
    for name, before in before_keys.items():
        after = after_keys[name]
        assert before[:3] == after[:3], (name, before[:3], after[:3])
        error = max(abs(a - b) for original, restored in zip(before[3], after[3])
                    for a, b in zip(original, restored))
        assert error < 2e-6, (name, error)
    assert not runtime._ERRORS and not errors, (runtime._ERRORS, errors)
    print("PASS armature Edit Mode cancels modal preview and restores Pose Mode, pose and saved paired profile", flush=True)


if __name__ == "__main__":
    main()
