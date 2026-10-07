"""Explicit live-console Hips display inspection/apply; never save artist X.blend.

Run with a globals dict containing action='inspect' (default) or action='apply'.
The companion restore script selects action='restore'. This script must only be
executed after the scene's owner has released its live/background verification.
It does not refresh add-ons, evaluate the depsgraph, or change mode/selection/frame.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import traceback
import uuid

import bpy


ARTIST_FILE = Path(r"D:\Blender\Projects\Character\X\X.blend")
OUTPUT_DIR = Path(r"D:\Blender\Projects\Character\X\Validation\hips_display_20261006")
RIG_NAME = "CoshaRig"
RESTORE_KEY = "character_designer_hips_display_restore_v1"
LOCAL_TZ = timezone(timedelta(hours=8))


def _now():
    return datetime.now(LOCAL_TZ).isoformat(timespec="microseconds")


def _same_path(first, second):
    # Windows comparison is case-insensitive, but no other artist file is allowed.
    return str(Path(first).resolve()).casefold() == str(Path(second).resolve()).casefold()


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identity(value):
    if value is None:
        return None
    return {"pointer": value.as_pointer(), "name": getattr(value, "name", None),
            "rna": value.bl_rna.identifier}


def _value(value):
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    if hasattr(value, "as_pointer"):
        return _identity(value)
    try:
        return [_value(item) for item in value]
    except TypeError:
        return repr(value)


def _rna_config(item, depth=0):
    result = {"identity": _identity(item)}
    for prop in item.bl_rna.properties:
        if prop.identifier == "rna_type" or prop.is_readonly:
            continue
        value = getattr(item, prop.identifier)
        if prop.type == "COLLECTION":
            if depth < 2:
                result[prop.identifier] = [_rna_config(child, depth+1) for child in value]
        else:
            result[prop.identifier] = _value(value)
    return result


def _color(value):
    return {"palette": value.palette,
            "custom": {key: list(getattr(value.custom, key)) for key in ("normal", "select", "active")}}


def _display(pb):
    return {"shape": _identity(pb.custom_shape),
            "shape_mesh": _identity(pb.custom_shape.data) if pb.custom_shape is not None else None,
            "transform": _identity(pb.custom_shape_transform),
            "use_bone_size": pb.use_custom_shape_bone_size,
            "scale": list(pb.custom_shape_scale_xyz),
            "translation": list(pb.custom_shape_translation),
            "rotation": list(pb.custom_shape_rotation_euler),
            "wire_width": getattr(pb, "custom_shape_wire_width", None),
            "bone_color": _color(pb.bone.color), "pose_color": _color(pb.color)}


def _animation(item):
    animation = item.animation_data
    if animation is None:
        return None
    return {"identity": _identity(animation), "action": _identity(animation.action),
            "action_slot": _identity(getattr(animation, "action_slot", None)),
            "drivers": [{"identity": _identity(curve), "path": curve.data_path,
                         "index": curve.array_index, "mute": curve.mute}
                        for curve in animation.drivers],
            "nla": [{"identity": _identity(track), "mute": track.mute,
                     "strips": [{"identity": _identity(strip), "action": _identity(strip.action),
                                "action_slot": _identity(getattr(strip, "action_slot", None)),
                                "mute": strip.mute, "influence": strip.influence,
                                "start": strip.frame_start, "end": strip.frame_end}
                               for strip in track.strips]}
                    for track in animation.nla_tracks]}


def _snapshot(rig, service):
    scene = bpy.context.scene
    bones = {}
    for pb in rig.pose.bones:
        bone = pb.bone
        bones[pb.name] = {
            "basis": [list(row) for row in pb.matrix_basis], "rotation_mode": pb.rotation_mode,
            "rest": [list(row) for row in bone.matrix_local],
            "parent": _identity(bone.parent), "deform": bone.use_deform,
            "connected": bone.use_connect, "inherit_scale": bone.inherit_scale,
            "inherit_rotation": bone.use_inherit_rotation, "local_location": bone.use_local_location,
            "hide": bone.hide, "hide_select": bone.hide_select,
            "pose_hide": getattr(pb, "hide", None),
            "collections": [collection.name for collection in bone.collections],
            "constraints": [_rna_config(constraint) for constraint in pb.constraints],
            "display": _display(pb),
        }
    return {"file": bpy.data.filepath, "mode": bpy.context.mode, "rig_mode": rig.mode,
            "active_object": _identity(bpy.context.view_layer.objects.active),
            "selected_objects": sorted(obj.name for obj in bpy.context.selected_objects),
            "active_bone": _identity(rig.data.bones.active),
            "bone_selection": {pb.name: [getattr(pb, "select", getattr(pb.bone, "select", None)),
                                          getattr(pb.bone, "select_head", None),
                                          getattr(pb.bone, "select_tail", None)]
                               for pb in rig.pose.bones},
            "frame": scene.frame_current, "subframe": scene.frame_subframe,
            "rig": _identity(rig), "rig_data": _identity(rig.data),
            "bones": bones, "animation": _animation(rig), "data_animation": _animation(rig.data),
            "all_actions": [_identity(item) for item in bpy.data.actions],
            "record_raw": rig.data.get(service.RECORD_KEY),
            "collections": {item.name: [item.is_visible, item.is_solo] for item in rig.data.collections_all}}


def _scale(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise RuntimeError("The Hips display restore scale is invalid.")
    if any(type(item) not in (int, float) or not math.isfinite(item) for item in value):
        raise RuntimeError("The Hips display restore scale is non-finite or invalid.")
    return tuple(float(item) for item in value)


def _metadata(pb, record):
    raw = pb.get(RESTORE_KEY)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise RuntimeError("The existing Hips display restore property is not valid JSON text.")
    result = json.loads(raw)
    if (not isinstance(result, dict) or type(result.get("version")) is not int or result["version"] != 1
            or result.get("rig_name") != RIG_NAME or result.get("bone_name") != pb.name
            or result.get("shape_name") != pb.custom_shape.name
            or result.get("body_detail_record_id") != record["id"]
            or not _same_path(result.get("artist_file", ""), ARTIST_FILE)):
        raise RuntimeError("The Hips display restore metadata does not match this live bone/widget.")
    _scale(result.get("original_scale"))
    original_backup = Path(result.get("scene_backup", ""))
    if (not original_backup.is_file() or original_backup.parent.resolve() != (OUTPUT_DIR / "backups").resolve()
            or _sha256(original_backup) != result.get("scene_backup_sha256")):
        raise RuntimeError("The original Hips display scene backup is missing or changed.")
    return result


def _preflight():
    if bpy.app.background or bpy.app.version[:2] != (5, 1):
        raise RuntimeError("This script requires the current interactive Blender 5.1 session.")
    if not bpy.data.filepath or not _same_path(bpy.data.filepath, ARTIST_FILE) or not ARTIST_FILE.is_file():
        raise RuntimeError("The current artist file must be exactly D:\\Blender\\Projects\\Character\\X\\X.blend.")
    rigs = [obj for obj in bpy.data.objects if obj.type == "ARMATURE" and obj.name == RIG_NAME]
    if len(rigs) != 1 or bpy.context.scene.objects.get(RIG_NAME) != rigs[0]:
        raise RuntimeError("There must be one live CoshaRig armature in this scene.")
    rig = rigs[0]
    if rig.mode == "EDIT" or rig.library or rig.data.library or not rig.is_editable or rig.data.users != 1:
        raise RuntimeError("CoshaRig must be a local editable single-user rig outside Edit Mode.")
    if "character_designer_body_original_mode_v1" in rig:
        raise RuntimeError("Leave Original mode before changing the Hips control display.")
    from character_designer import body_detail_visuals as service
    record = service.validate(rig)
    if not record or "HIPS" not in record.get("names", {}):
        raise RuntimeError("The installed Body Detail service has no validated HIPS binding.")
    name = record["names"]["HIPS"]
    entry = record["bindings"][name]
    pb = rig.pose.bones.get(name)
    if pb is None or entry["role"] != "HIPS" or pb.custom_shape is None or pb.custom_shape.name != entry["object"]:
        raise RuntimeError("The live HIPS custom shape does not match its exact binding.")
    guard = getattr(getattr(service, "visuals", None), "_animated_display", None)
    if not callable(guard) or guard(rig, pb):
        raise RuntimeError("The Hips display is animated/driven, or its installed animation guard is unavailable.")
    master = rig.pose.bones.get("CTRL_master")
    if master is None or master.custom_shape is None:
        raise RuntimeError("The bottom CTRL_master display must exist before Hips is simplified.")
    return rig, pb, service, record


def _unchanged(before, after, hips_name, expected_scale):
    normalized = json.loads(json.dumps(after))
    if normalized["bones"][hips_name]["display"]["scale"] != list(expected_scale):
        raise RuntimeError("The requested Hips display scale did not persist in the live RNA value.")
    normalized["bones"][hips_name]["display"]["scale"] = before["bones"][hips_name]["display"]["scale"]
    if normalized != before:
        changed = [key for key in before if before[key] != normalized.get(key)]
        raise RuntimeError("Unexpected live scene change outside Hips display scale: " + ", ".join(changed))


def _backup_scene():
    directory = OUTPUT_DIR / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(LOCAL_TZ).strftime("%Y%m%d_%H%M%S_%f")
    path = directory / ("X_before_hips_display_" + stamp + "_" + uuid.uuid4().hex[:8] + ".blend")
    if path.exists():
        raise RuntimeError("A new scene backup path unexpectedly exists; no file was overwritten.")
    result = bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, check_existing=False)
    if "FINISHED" not in result or not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Blender did not confirm the separate current-scene backup.")
    if not _same_path(bpy.data.filepath, ARTIST_FILE):
        raise RuntimeError("Saving the separate copy unexpectedly changed the active artist filepath.")
    return {"path": str(path), "sha256": _sha256(path), "size": path.stat().st_size,
            "blender_result": sorted(result)}


def main(requested_action="inspect"):
    if requested_action not in {"inspect", "apply", "restore"}:
        raise ValueError("action must be inspect, apply, or restore.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = OUTPUT_DIR / (requested_action + "_" + datetime.now(LOCAL_TZ).strftime("%Y%m%d_%H%M%S_%f")
                                  + "_" + uuid.uuid4().hex[:8] + ".json")
    evidence = {"version": 1, "action": requested_action, "started_at": _now(),
                "artist_file": str(ARTIST_FILE), "main_artist_saved": False,
                "depsgraph_update_requested": False, "status": "RUNNING"}
    pb = None
    property_changed = False
    prior_scale = None
    prior_metadata = None
    try:
        rig, pb, service, record = _preflight()
        prior_scale = tuple(pb.custom_shape_scale_xyz)
        prior_metadata = pb.get(RESTORE_KEY)
        metadata = _metadata(pb, record)
        before = _snapshot(rig, service)
        disk_hash = _sha256(ARTIST_FILE)
        evidence.update({"blender_version": bpy.app.version_string, "installed_service": service.__file__,
                         "hips_bone": pb.name, "master_bone": "CTRL_master",
                         "before": before, "validated_record": record,
                         "artist_sha256_before": disk_hash, "restore_metadata_before": metadata})
        target_scale = prior_scale
        if requested_action == "apply":
            if metadata is not None and prior_scale not in {(0.0, 0.0, 0.0), _scale(metadata["original_scale"])}:
                raise RuntimeError("Hips display scale was edited after this task's backup; preserve that edit before reapplying.")
            if metadata is None or prior_scale != (0.0, 0.0, 0.0):
                backup = _backup_scene()
                evidence["current_scene_backup"] = backup
                _unchanged(before, _snapshot(rig, service), pb.name, prior_scale)
                if _sha256(ARTIST_FILE) != disk_hash:
                    raise RuntimeError("The artist disk file changed while preparing its separate backup.")
                if metadata is None:
                    metadata = {"version": 1, "created_at": _now(), "artist_file": str(ARTIST_FILE),
                                "rig_name": rig.name, "bone_name": pb.name, "shape_name": pb.custom_shape.name,
                                "body_detail_record_id": record["id"], "original_scale": list(prior_scale),
                                "scene_backup": backup["path"], "scene_backup_sha256": backup["sha256"],
                                "blender_version": bpy.app.version_string}
            target_scale = (0.0, 0.0, 0.0)
            property_changed = True
            if prior_metadata is None:
                pb[RESTORE_KEY] = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            pb.custom_shape_scale_xyz = target_scale
        elif requested_action == "restore":
            if metadata is None:
                raise RuntimeError("No task-owned Hips display restore metadata exists.")
            target_scale = _scale(metadata["original_scale"])
            if prior_scale not in {(0.0, 0.0, 0.0), target_scale}:
                raise RuntimeError("Hips display scale has later artist edits; do not overwrite them with this restore.")
            property_changed = True
            # Keep the immutable restore metadata and its original scene backup.
            pb.custom_shape_scale_xyz = target_scale
        validated_after = service.validate(rig)
        if validated_after != record:
            raise RuntimeError("The installed Body Detail binding/recovery record changed.")
        after = _snapshot(rig, service)
        _unchanged(before, after, pb.name, target_scale)
        if _sha256(ARTIST_FILE) != disk_hash:
            raise RuntimeError("The artist disk file changed during this operation.")
        final_metadata = _metadata(pb, record)
        if prior_metadata is not None and pb.get(RESTORE_KEY) != prior_metadata:
            raise RuntimeError("An existing original display backup was overwritten.")
        evidence.update({"status": "PASS", "after": after, "restore_metadata_after": final_metadata,
                         "artist_sha256_after": disk_hash, "all_other_display_and_rig_data_unchanged": True,
                         "next_step": "Inspect viewport, then save the active X.blend with Ctrl+S."})
    except Exception as exc:
        if property_changed and pb is not None:
            pb.custom_shape_scale_xyz = prior_scale
            if prior_metadata is None:
                if RESTORE_KEY in pb:
                    del pb[RESTORE_KEY]
            else:
                pb[RESTORE_KEY] = prior_metadata
            evidence["task_property_and_metadata_rolled_back"] = True
        evidence.update({"status": "FAILED", "error": str(exc), "traceback": traceback.format_exc()})
        raise
    finally:
        evidence["finished_at"] = _now()
        try:
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            # Evidence output is part of the transaction: keep neither change
            # if its result cannot be written to the persistent review folder.
            if property_changed and pb is not None:
                pb.custom_shape_scale_xyz = prior_scale
                if prior_metadata is None:
                    if RESTORE_KEY in pb:
                        del pb[RESTORE_KEY]
                else:
                    pb[RESTORE_KEY] = prior_metadata
            print("HIPS_DISPLAY", requested_action, "FAILED_EVIDENCE_WRITE; task changes rolled back")
            raise
        print("HIPS_DISPLAY", requested_action, evidence["status"], str(evidence_path))
    return evidence


main(globals().get("action", "inspect"))
