"""Read-only reopen/geometry check using the preference-enabled installed addon.

Run without --factory-startup, for example:
blender --background --disable-autoexec path/to/X.blend --python-exit-code 1
        --python tests/test_forearm_twist_installed_x_reopen_blender.py

This script never enables an addon, registers handlers, migrates calibration,
calls the twist updater, or saves the input blend. Startup must work unaided.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import addon_utils
import bpy
from mathutils import Quaternion


def fingerprint(path):
    stat = path.stat()
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def pose_snapshot(armature):
    return {bone.name: {"rotation_mode": bone.rotation_mode,
                        "rotation_euler": tuple(bone.rotation_euler),
                        "rotation_quaternion": tuple(bone.rotation_quaternion),
                        "rotation_axis_angle": tuple(bone.rotation_axis_angle),
                        "location": tuple(bone.location), "scale": tuple(bone.scale)}
            for bone in armature.pose.bones}


def restore_pose(armature, saved):
    for name, values in saved.items():
        bone = armature.pose.bones[name]
        for field, value in values.items():
            setattr(bone, field, value)


def main():
    assert bpy.app.background, "Run this read-only test in a background Blender process."
    path = Path(bpy.data.filepath).resolve()
    assert path.is_file(), "Pass the blend file on Blender's command line."
    before = fingerprint(path)
    armature = None
    bones = None
    modifiers = []
    frame = bpy.context.scene.frame_current
    subframe = bpy.context.scene.frame_subframe
    results = []
    try:
        # Check immediately, before any explicit scene or frame evaluation.
        assert "character_designer" in sys.modules, "Preferences did not automatically load Character Designer."
        assert addon_utils.check("character_designer") == (True, True), addon_utils.check("character_designer")
        import character_designer
        from character_designer import forearm_twist as runtime

        assert tuple(character_designer.bl_info["version"]) == (0, 37, 0), character_designer.bl_info
        installed = Path(bpy.utils.user_resource("SCRIPTS", path="addons")) / "character_designer"
        assert Path(character_designer.__file__).resolve().is_relative_to(installed.resolve()), character_designer.__file__
        assert Path(runtime.__file__).resolve().is_relative_to(installed.resolve()), runtime.__file__
        obj = bpy.data.objects["Cosha"]
        armature = next(mod.object for mod in obj.modifiers if mod.type == "ARMATURE")
        records = runtime._records(obj)
        assert set(records) == {"L", "R"}, records.keys()
        assert not runtime._ERRORS, runtime._ERRORS
        assert runtime._SESSION is None, "A saved test preview was not recovered."
        startup = {}
        for side, record in records.items():
            assert record["enabled"], (side, "saved calibration disabled")
            key = obj.data.shape_keys.key_blocks.get(record["key"])
            assert key is not None and not key.mute and abs(key.value - 1.0) < 1.0e-8, (side, key)
            assert record["rest"] == runtime._rest_signature(armature, record["chain"]), (side, "startup did not migrate changed bone Rest")
            startup[side] = {"target": record["target"], "rings": len(record["rings"]),
                             "support_vertices": len(record["vertices"]), "key": key.name,
                             "key_mute": key.mute, "key_value": key.value}
        print("INSTALLED_REOPEN_STARTUP=" + json.dumps({"module": character_designer.__file__,
              "version": character_designer.bl_info["version"], "records": startup,
              "errors": dict(runtime._ERRORS)}, sort_keys=True), flush=True)

        # The helper respects this already-imported installed addon. It neither
        # registers it nor changes sys.path to prefer the source addon here.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_real_x_forearm_twist_rig_lifecycle_blender import (
            current_targets, ratios, source_snapshot, verify_geometry)
        assert Path(character_designer.__file__).resolve().is_relative_to(installed.resolve())
        assert not any(Path(entry).resolve() == Path(__file__).resolve().parents[1] / "addons"
                       for entry in sys.path if entry), "The source addons directory entered the import path."

        bones = pose_snapshot(armature)
        modifiers = [(modifier, modifier.show_viewport, modifier.show_render) for modifier in obj.modifiers]
        saved_ratios = ratios(obj)
        saved_source = source_snapshot(obj)
        for modifier, _viewport, _render in modifiers:
            if modifier.type == "SUBSURF":
                modifier.show_viewport = False
        protected = source_snapshot(obj)
        results.append(verify_geometry(obj, armature, "installed-reopen/current-saved-pose"))
        for degrees, bend_degrees in ((90, 0), (-90, 0), (45, 25), (-45, 25)):
            # Evaluate via Blender's ordinary scene/frame/depsgraph lifecycle.
            bpy.context.scene.frame_set(frame, subframe=subframe)
            restore_pose(armature, bones)
            targets = current_targets(armature)
            requested = {}
            for side, target in targets.items():
                assert target.name == records[side]["target"], (side, target.name, records[side]["target"])
                assert target.name.startswith("CTRL_hand_IK."), target.name
                target.rotation_mode = "XYZ"
                baseline = Quaternion((1, 0, 0), math.radians(bend_degrees))
                local_y = Quaternion((0, 1, 0), math.radians(degrees) * (1 if side == "L" else -1))
                target.rotation_euler = (baseline @ local_y).to_euler("XYZ")
                requested[side] = tuple(target.rotation_euler)
            armature.update_tag(refresh={"OBJECT"})
            results.append(verify_geometry(obj, armature, f"installed-reopen/RYY={degrees}/bend={bend_degrees}"))
            assert all(tuple(targets[side].rotation_euler) == value for side, value in requested.items()), "Correction changed controller channels."
            assert ratios(obj) == saved_ratios, "Ordinary playback changed saved ring ratios."
            assert source_snapshot(obj) == protected, "Ordinary playback modified artist geometry, weights, shape keys or modifiers."
        print("INSTALLED_REOPEN_PASS=" + json.dumps({"input": str(path), "poses": len(results),
              "max_vertex_error": max(item["max_vertex_error"] for item in results),
              "max_hand_error": max(item["hand_only_error"] for item in results)}, sort_keys=True), flush=True)
    finally:
        if bones is not None:
            bpy.context.scene.frame_set(frame, subframe=subframe)
            restore_pose(armature, bones)
            for modifier, viewport, render in modifiers:
                modifier.show_viewport = viewport
                modifier.show_render = render
            armature.update_tag(refresh={"OBJECT"})
            bpy.context.view_layer.update()
            assert pose_snapshot(armature) == bones, "Temporary controller channels were not restored."
            assert source_snapshot(obj) == saved_source, "Temporary modifier or source state was not restored."
        after = fingerprint(path)
        assert after == before, {"before": before, "after": after}
        print("INSTALLED_REOPEN_INPUT_UNCHANGED=" + json.dumps({"path": str(path), **after}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
