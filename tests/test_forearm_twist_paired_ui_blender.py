"""Paired forearm UI exercised from a real hand controller in Pose Mode.

Uses synthetic sleeves only. Run Blender --background --factory-startup
--python-exit-code 1 --python tests/test_forearm_twist_paired_ui_blender.py.
"""
import os
import sys
from types import SimpleNamespace

import bpy

TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS)
sys.path.insert(0, os.path.join(os.path.dirname(TESTS), "addons"))

import character_designer
from character_designer import forearm_twist, limb_ik
from test_forearm_twist_symmetry_blender import fixture


class LayoutRecorder:
    def __init__(self):
        self.properties = []
        self.operators = []
        self.labels = []

    def prop(self, _owner, name, **_kwargs):
        self.properties.append(name)

    def operator(self, name, **kwargs):
        self.operators.append((name, kwargs))
        return SimpleNamespace()

    def label(self, **kwargs):
        self.labels.append(kwargs.get("text", ""))

    def row(self, **_kwargs):
        return self

    def box(self):
        return self


def draw_panel():
    layout = LayoutRecorder()
    panel = SimpleNamespace(layout=layout)
    forearm_twist.CHARACTERDESIGNER_PT_forearm_twist.draw(panel, bpy.context)
    assert "side" not in layout.properties and "symmetry" not in layout.properties
    assert not any("mirror" in name for name, _kwargs in layout.operators)
    assert not any("Left Arm" in text or "Right Arm" in text or "Sync" in text for text in layout.labels)
    return layout


def select_controller(armature, target):
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="POSE")
    for bone in armature.pose.bones:
        bone.select = False
    target.select = True
    armature.data.bones.active = target.bone
    bpy.context.view_layer.update()
    assert bpy.context.mode == "POSE" and bpy.context.active_pose_bone == target


def assert_pose_context(armature, target):
    assert bpy.context.mode == "POSE"
    assert bpy.context.object == armature and bpy.context.active_pose_bone == target


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
    bpy.context.view_layer.objects.active = armature
    assert bpy.ops.character_designer.limb_ik_analyze() == {"FINISHED"}
    assert bpy.ops.character_designer.limb_ik_build_all() == {"FINISHED"}
    inventory = limb_ik._validate_inventory(armature)
    target = armature.pose.bones[inventory["rigs"][("ARM", "R")]["target"].name]
    select_controller(armature, target)
    assert forearm_twist.context_mesh(bpy.context) == mesh
    panel = draw_panel()
    assert "Both Arms" in panel.labels
    assert [name for name, _kwargs in panel.operators] == ["character_designer.forearm_twist_start"]

    assert bpy.ops.character_designer.forearm_twist_start("EXEC_DEFAULT") == {"FINISHED"}
    assert forearm_twist._SESSION is not None
    panel = draw_panel()
    assert "Both Arms" in panel.labels
    assert set(panel.properties) == {"test_angle", "ring_index", "ratio"}
    assert bpy.ops.character_designer.forearm_twist_finish(action="CANCEL") == {"FINISHED"}
    assert forearm_twist.RECORD_KEY not in mesh
    assert_pose_context(armature, target)

    assert bpy.ops.character_designer.forearm_twist_start("EXEC_DEFAULT") == {"FINISHED"}
    assert bpy.ops.character_designer.forearm_twist_finish(action="CONFIRM") == {"FINISHED"}
    assert_pose_context(armature, target)
    assert set(forearm_twist._records(mesh)) == {"L", "R"}
    panel = draw_panel()
    assert {name for name, _kwargs in panel.operators} == {
        "character_designer.forearm_twist_start", "character_designer.forearm_twist_toggle",
        "character_designer.forearm_twist_remove"}
    assert bpy.ops.character_designer.forearm_twist_toggle() == {"FINISHED"}
    assert not any(record["enabled"] for record in forearm_twist._records(mesh).values())
    assert_pose_context(armature, target)
    assert bpy.ops.character_designer.forearm_twist_toggle() == {"FINISHED"}
    assert all(record["enabled"] for record in forearm_twist._records(mesh).values())
    assert bpy.ops.character_designer.forearm_twist_remove() == {"FINISHED"}
    assert forearm_twist.RECORD_KEY not in mesh
    assert_pose_context(armature, target)
    assert all(cls.__name__ != "CHARACTERDESIGNER_OT_forearm_twist_mirror"
               for cls in forearm_twist.FOREARM_TWIST_CLASSES)
    bpy.ops.object.mode_set(mode="OBJECT")
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = None
    panel = draw_panel()
    assert "Select body Mesh or Hand Target" in panel.labels and not panel.operators
    print("PASS paired forearm UI: hand-controller Pose Mode start/cancel/confirm/toggle/remove", flush=True)


if __name__ == "__main__":
    main()
