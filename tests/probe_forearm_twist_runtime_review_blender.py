"""Synthetic runtime review diagnostics; never opens production X.blend."""
import json
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import test_forearm_twist_blender as fixture_module
from character_designer import forearm_twist as runtime


def result(label, **values):
    print("REVIEW " + json.dumps({"label": label, **values}), flush=True)


def main():
    data = fixture_module.make_fixture("DIRECT_PREROLL")
    mesh, target = data["mesh"], data["target"]
    scene = bpy.context.scene
    scene.render.use_lock_interface = False
    runtime.start_test(bpy.context, mesh)
    runtime.finish_test(bpy.context, True)
    target.rotation_euler.y = math.radians(50)
    bpy.context.view_layer.update()
    key = mesh.data.shape_keys.key_blocks[runtime.KEY_PREFIX + "L"]
    result("initial", value=key.value, mute=key.mute, errors=runtime._ERRORS)
    key.value = 0
    bpy.context.view_layer.update()
    result("managed_value_changed", value=key.value, errors=runtime._ERRORS)
    assert key.value == 1 and not runtime._ERRORS
    key.value = 1
    key.mute = True
    bpy.context.view_layer.update()
    result("managed_mute_changed", mute=key.mute, errors=runtime._ERRORS)
    assert not key.mute and not runtime._ERRORS
    key.mute = False
    key.vertex_group = data["lower_name"]
    bpy.context.view_layer.update()
    result("managed_mask_changed", mask=key.vertex_group, mute=key.mute, errors=runtime._ERRORS)
    assert key.mute and mesh.name in runtime._ERRORS
    key.vertex_group = ""
    bpy.context.view_layer.update()
    index = data["outside"][0]
    basis = mesh.data.shape_keys.reference_key
    delta_before = tuple(key.data[index].co - basis.data[index].co)
    basis.data[index].co.x += 0.1
    mesh.data.shape_keys.update_tag()
    mesh.data.update()
    bpy.context.view_layer.update()
    result("basis_outside_modified", before=delta_before,
           after=tuple(key.data[index].co - basis.data[index].co), errors=runtime._ERRORS)
    assert (key.data[index].co - basis.data[index].co).length < 1e-7
    runtime.unregister_forearm_twist_runtime()
    result("unregistered", render_lock=scene.render.use_lock_interface, lock_property=runtime.LOCK_KEY in scene)
    assert not scene.render.use_lock_interface and runtime.LOCK_KEY not in scene
    runtime.register_forearm_twist_runtime()
    mesh[runtime.RECORD_KEY] = "bad json"
    runtime.update_runtime(scene, bpy.context.view_layer.depsgraph)
    runtime._load_post(None)
    assert mesh.name in runtime._ERRORS
    result("corrupt_record", contained=True)
    del mesh[runtime.RECORD_KEY]

    data = fixture_module.make_fixture("DIRECT_PREROLL")
    mesh, armature = data["mesh"], data["armature"]
    original_pose = fixture_module.pose_snapshot(armature)
    original_keys = fixture_module.key_snapshot(mesh)
    assert bpy.ops.character_designer.forearm_twist_start("EXEC_DEFAULT") == {"FINISHED"}
    assert bpy.ops.character_designer.forearm_twist_finish(action="CANCEL") == {"FINISHED"}
    assert runtime._SESSION is None and runtime.RECORD_KEY not in mesh and runtime.PREVIEW_KEY not in mesh
    fixture_module.assert_pose_snapshot(armature, original_pose, "direct cancel")
    assert fixture_module.key_snapshot(mesh) == original_keys
    assert bpy.ops.character_designer.forearm_twist_start("EXEC_DEFAULT") == {"FINISHED"}
    assert bpy.ops.character_designer.forearm_twist_finish(action="CONFIRM") == {"FINISHED"}
    assert runtime._SESSION is None and runtime.RECORD_KEY in mesh and runtime.PREVIEW_KEY not in mesh
    assert bpy.ops.character_designer.forearm_twist_remove() == {"FINISHED"}
    result("direct_operators", cancel=True, confirm=True, remove=True)

    runtime.start_test(bpy.context, mesh)
    runtime._SESSION = None
    runtime._undo_post(None)
    bpy.context.view_layer.update()
    assert runtime.PREVIEW_KEY not in mesh and runtime.RECORD_KEY not in mesh
    fixture_module.assert_pose_snapshot(armature, original_pose, "orphan new preview")
    assert fixture_module.key_snapshot(mesh) == original_keys
    result("orphan_new_preview", recovered=True)

    runtime.start_test(bpy.context, mesh)
    runtime.finish_test(bpy.context, True)
    saved_records = mesh[runtime.RECORD_KEY]
    runtime.start_test(bpy.context, mesh)
    runtime.set_ratio(bpy.context, 3, 0.73)
    assert mesh[runtime.RECORD_KEY] != saved_records
    runtime._SESSION = None
    runtime._undo_post(None)
    bpy.context.view_layer.update()
    assert runtime.PREVIEW_KEY not in mesh and mesh[runtime.RECORD_KEY] == saved_records
    fixture_module.assert_pose_snapshot(armature, original_pose, "orphan recalibration")
    assert not runtime._ERRORS, runtime._ERRORS
    result("orphan_recalibration", recovered=True)

    runtime.remove_calibration(bpy.context, mesh, "L")
    runtime.start_test(bpy.context, mesh)
    bpy.data.objects.remove(mesh, do_unlink=True)
    runtime.finish_test(bpy.context, False)
    assert runtime._SESSION is None
    fixture_module.assert_pose_snapshot(armature, original_pose, "deleted mesh cancel")
    result("deleted_mesh_cancel", recovered=True)


if __name__ == "__main__":
    main()
