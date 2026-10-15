"""Source-only protected live CD .40 -> .41 refresh; no automatic entry point.

The separate pinned Console installer authorizes begin() in the observed X
process. No file open, artist save, frame_set, manual runtime update/reacquire,
scene repair, deployment, blanket reload, or automatic scene rollback occurs.
Large artist arrays are streamed into hashes, never dumped into the receipt.
The independent SaveCopy is recovery evidence, not an automatic rollback.
"""
import ctypes
import datetime
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import sys
import time
import traceback
import types
import uuid
import zipfile

ROUND = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round4")
ARTIST = Path(r"D:\Blender\Projects\Character\X\X.blend")
ARTIST_PIN = {"sha256": "40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721", "bytes": 34691613}
CANONICAL = Path(r"D:\MyRepository\Blender-addons-by-Randy\addons\character_designer")
PROJECT_COPY = ARTIST.parent / "addons" / "character_designer"
PREPARED = ROUND.parent / "round3" / "prepared_candidate_07741.json"
PREPARED_SHA = "4d0dd17651ab78ad0f80901f271ff507d4743d25dfed442917578ffbe73b1843"
ORACLE = ARTIST.parent / "validation" / "direct_original_rig_return_20261011" / "validation_preservation.py"
ORACLE_SHA = "260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d"
EXPECTED_PID = 24416
EXPECTED_RUNTIME_ROOT = Path(r"C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer")
HELPER_NAME = "_x_protected_refresh_07741_20261015"
TIMEOUT_SECONDS = 30.0


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def pin(path, expected=None):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    row = {"path": str(path), "sha256": h.hexdigest(), "bytes": path.stat().st_size}
    if expected:
        require(all(row[key] == value for key, value in expected.items() if key != "path"), "File pin changed: " + str(path))
        if "path" in expected:
            require(path == Path(expected["path"]).resolve(), "Pinned path changed: " + str(path))
    return row


def identity(value):
    if value is None:
        return None
    return {"type": value.bl_rna.identifier, "name": value.name,
            "pointer": int(value.as_pointer()), "library": value.library.filepath if value.library else None}


def exact(value):
    """Typed JSON representation; preserves signed zero and native pointers."""
    import bpy
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        require(math.isfinite(value), "Non-finite artist value cannot be certified")
        return {"float_hex": value.hex()}
    if isinstance(value, bpy.types.ID):
        return {"native_id": identity(value)}
    if isinstance(value, dict) or hasattr(value, "items"):
        return {str(key): exact(item) for key, item in value.items()}
    if isinstance(value, set):
        return sorted(exact(item) for item in value)
    if hasattr(value, "to_list"):
        return exact(value.to_list())
    if isinstance(value, (list, tuple)) or hasattr(value, "__iter__"):
        return [exact(item) for item in value]
    raise RuntimeError("Unsupported artist value: " + type(value).__name__)


def digest(value):
    return hashlib.sha256(json.dumps(exact(value), ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def rna(value, *, depth=0, collections=False):
    """Writable authored RNA, ID references only; no recursive ID expansion."""
    import bpy
    require(depth < 12, "RNA protection exceeds bounded nesting")
    out = {}
    for prop in value.bl_rna.properties:
        name = prop.identifier
        if name == "rna_type":
            continue
        if prop.is_readonly and prop.type not in {"COLLECTION", "POINTER"}:
            continue
        current = getattr(value, name)
        if prop.type == "COLLECTION":
            if collections:
                out[name] = [identity(item) if isinstance(item, bpy.types.ID)
                             else rna(item, depth=depth + 1, collections=True) for item in current]
        elif prop.type == "POINTER":
            if current is None or isinstance(current, bpy.types.ID):
                out[name] = current
            elif isinstance(current, bpy.types.PropertyGroup):
                out[name] = rna(current, depth=depth + 1, collections=True)
            elif not prop.is_readonly:
                # Non-ID pointers are stored as actual native identities, not followed.
                out[name] = {"rna_type": current.bl_rna.identifier, "pointer": int(current.as_pointer())}
        else:
            out[name] = list(current) if getattr(prop, "is_array", False) else current
    return out


def pg(value):
    """Retain typed collection boundaries for conservative WM restoration."""
    import bpy
    out = {}
    for prop in value.bl_rna.properties:
        name = prop.identifier
        if name == "rna_type" or (prop.is_readonly and prop.type not in {"COLLECTION", "POINTER"}):
            continue
        current = getattr(value, name)
        if prop.type == "COLLECTION":
            out[name] = {"kind": "COLLECTION", "items": [pg(item) for item in current]}
        elif prop.type == "POINTER" and isinstance(current, bpy.types.PropertyGroup):
            out[name] = {"kind": "GROUP", "fields": pg(current)}
        else:
            out[name] = list(current) if getattr(prop, "is_array", False) else current
    return out


def restore_changed_wm(group, saved, prefix, restored):
    current = pg(group)
    require(set(current) == set(saved), "WM schema changed: " + prefix)
    for name, expected in saved.items():
        if exact(current[name]) == exact(expected):
            continue
        prop = group.bl_rna.properties[name]
        require(prop.type != "COLLECTION", "WM collection changed; no blind rewrite: " + prefix + "." + name)
        if isinstance(expected, dict) and expected.get("kind") == "GROUP":
            restore_changed_wm(getattr(group, name), expected["fields"], prefix + "." + name, restored)
        else:
            setattr(group, name, expected)
            restored.append(prefix + "." + name)


def memory_guard():
    class Status(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    state = Status()
    state.dwLength = ctypes.sizeof(state)
    require(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)), "Cannot observe memory before capture")
    require(state.ullAvailPhys >= 200 * 1024 * 1024, "Available memory is below the authorized 200 MiB threshold")
    return {"load_percent": int(state.dwMemoryLoad), "available_bytes": int(state.ullAvailPhys)}


def package_proof(runtime_root):
    receipt_pin = pin(PREPARED, {"sha256": PREPARED_SHA})
    receipt = json.loads(PREPARED.read_text(encoding="utf-8"))
    require(receipt["prepared"] and receipt["candidate_version"] == "0.77.41"
            and receipt["package_files"] == 190, "Prepared candidate identity changed")
    package_pin = pin(receipt["package"]["path"], receipt["package"])
    files = {}
    with zipfile.ZipFile(package_pin["path"]) as package:
        require(package.testzip() is None, "Candidate ZIP CRC failed")
        for member in package.infolist():
            path = PurePosixPath(member.filename)
            require(not member.is_dir() and path.parts[0] == "character_designer"
                    and len(path.parts) > 1 and ".." not in path.parts and "\\" not in member.filename,
                    "Unexpected candidate ZIP entry")
            relative = PurePosixPath(*path.parts[1:]).as_posix()
            require(relative not in files, "Duplicate ZIP source")
            files[relative] = hashlib.sha256(package.read(member)).hexdigest()
    require(len(files) == 190, "Incomplete candidate ZIP")
    roots = {}
    for root in (CANONICAL, runtime_root, PROJECT_COPY):
        root = root.resolve()
        actual = {path.relative_to(root).as_posix(): pin(path)["sha256"]
                  for path in root.rglob("*") if path.is_file()
                  and not any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(root).parts)
                  and path.suffix not in {".pyc", ".pyo"}}
        require(actual == files, "Complete candidate deployment differs: " + str(root))
        roots[str(root)] = {"files": len(actual), "map_sha256": digest(actual)}
    for row in receipt["runtime_sources"]:
        pin(row["path"], row)
    return {"prepared": receipt_pin, "package": package_pin, "roots": roots}, files


def load_oracle():
    pin(ORACLE, {"sha256": ORACLE_SHA})
    name = HELPER_NAME + "_oracle"
    require(name not in sys.modules, "Refresh oracle name is already owned")
    module = types.ModuleType(name)
    module.__file__ = str(ORACLE)
    sys.modules[name] = module
    try:
        raw = ORACLE.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == ORACLE_SHA, "Oracle changed before source execution")
        exec(compile(raw.decode("utf-8-sig"), str(ORACLE), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def require_context(window, screen, area, scene):
    import bpy
    require(os.getpid() == EXPECTED_PID and not bpy.app.background, "Wrong artist process")
    require(Path(bpy.data.filepath).resolve() == ARTIST.resolve(), "The live file is not original X.blend")
    require(window.screen == screen and window.scene == scene and any(item == area for item in screen.areas),
            "Owning artist window/context changed")
    require(area.type == "CONSOLE", "The observed Console area changed")
    require(scene.name == "Scene" and bpy.data.objects.get("CoshaRig") is not None, "Original scene/rig unavailable")
    require(not screen.is_animation_playing, "Pause artist before refresh")


def idle(cd):
    import bpy
    require(bpy.context.mode in {"OBJECT", "POSE"}, "Finish current edit mode before refresh")
    require(not any(name.startswith("_x_playback") for name in sys.modules), "An owned profiler/helper installation remains")
    for kind in ("frame_change_pre", "frame_change_post", "depsgraph_update_pre", "depsgraph_update_post"):
        for callback in getattr(bpy.app.handlers, kind):
            filename = getattr(getattr(callback, "__code__", None), "co_filename", "")
            require("live_profiler" not in filename, "Profiler callback remains: " + filename)
    for name, module in tuple(sys.modules.items()):
        if name == "character_designer" or name.startswith("character_designer."):
            for value in vars(module).values():
                filename = getattr(getattr(value, "__code__", None), "co_filename", "")
                require("live_profiler" not in filename, "Profiler function/panel wrapper remains")
                if isinstance(value, type):
                    for method in vars(value).values():
                        if isinstance(method, (staticmethod, classmethod)):
                            method = method.__func__
                        filename = getattr(getattr(method, "__code__", None), "co_filename", "")
                        require("live_profiler" not in filename, "Profiler class callback wrapper remains")
    for obj in bpy.data.objects:
        animation = obj.animation_data
        require(not (animation and animation.use_tweak_mode), "Tweak session is active: " + obj.name)
        for key in ("character_designer_unity_animation_active", "character_designer_rigging_session_v1",
                    "character_designer_composition_session_v1"):
            require(not obj.get(key), "An actual editing session is active: " + obj.name + "/" + key)
    cached = lambda suffix: sys.modules.get("character_designer." + suffix)
    needed = ("unity_animation", "forearm_twist", "forearm_original_inventory", "body_original_mode",
              "bone_collections", "limb_fk_visuals", "limb_ik", "limb_ik_fk", "animation_worklist_fingerprint", "unity_animation_rigging")
    require(all(cached(name) is not None for name in needed), "Protection dependency is not already loaded; refuse mixed pre-refresh imports")
    for suffix, field, empty in (("animation", "_job", None), ("animation_worklist_ui", "_SCAN_PENDING", None)):
        module = cached(suffix)
        require(module is None or getattr(module, field) == empty, "An animation/scan job is active")
    for suffix, method in (("animation_export", "active_job"), ("unity_export", "export_running"),
                           ("animation_worklist_collection", "running")):
        module = cached(suffix)
        require(module is None or not getattr(module, method)(), "A cached job is active: " + suffix)
    settings = cd._settings(bpy.context)
    require(settings is not None and not bpy.app.timers.is_registered(cd._live_preview_tick), "Centreline preview is active")
    for name in ("root_indices_json", "root_edges_json", "root_ignored_indices_json"):
        require(not getattr(settings, name) or not json.loads(getattr(settings, name)), "Centreline capture would be cleared")
    for name in ("root_object", "root_mesh", "root_vertex_count", "root_ignored_count", "root_kind", "root_capture_mode", "topology_signature"):
        require(not getattr(settings, name), "Centreline root capture would be cleared")
    for name in ("_LIVE_PREVIEW_INPUT_SIGNATURE", "_LIVE_PREVIEW_WORLD_POINTS", "_LIVE_PREVIEW_PATHS", "_LIVE_PREVIEW_HANDLE_POINTS",
                 "_LIVE_PREVIEW_LAYERS", "_LIVE_PREVIEW_METADATA_JSON", "_LIVE_PREVIEW_SOURCE_KEY", "_LIVE_PREVIEW_TRACKED_SOURCE_KEY", "_LIVE_PREVIEW_DRAW_HANDLE"):
        require(not getattr(cd, name, None), "Centreline transient runtime is active")
    delta = cached("delta_symmetry")
    require(delta is None or (not delta._CAPTURE and not delta._RUNTIME), "Delta capture/runtime is active")
    hair = cached("hair_wiggle_adapter")
    require(hair is None or hair._SESSION is None, "Hair preview would be restored by SaveCopy/unload")
    ft = cached("forearm_twist")
    require(ft._SESSION is None and not ft._BUSY and not ft._INITIALIZE_PENDING
            and not ft._SCENE_CLEANUP_PENDING and not ft._ERRORS, "Forearm runtime is not idle/healthy")
    require(not any(ft.PREVIEW_KEY in obj for obj in bpy.data.objects), "Interrupted Forearm preview would be recovered by SaveCopy/reload")
    native = cached("unity_animation_rigging")
    require(native._REACQUIRE_TIMER is None and not native._REACQUIRE_PENDING and not native._HANDLER_ERRORS
            and not native._BUSY and not native._SUSPENDED, "Original20 lifecycle/session is active")
    skirt = cached("skirt_wiggle")
    require(skirt is None or (not skirt._SESSIONS and not skirt._SAVE_RESUME), "Dress adapter would be changed by SaveCopy/unload")
    if skirt:
        require(not any(skirt.STATE_KEY in obj for obj in bpy.data.objects), "Saved Dress adapter needs separate cleanup review")
        require(not any(bpy.app.timers.is_registered(callback) for callback in (skirt._timer, skirt._resume_saved)), "A Dress resume/solver timer is pending")
    for suffix, field in (("skirt", "_ACTIVE_BAKES"), ("unity_export_ui", "_MODAL_EXPORTS"), ("animation_worklist_ui", "_DRAGS")):
        module = cached(suffix)
        require(module is None or not getattr(module, field), "An actual modal/bake operation is active")
    paint = cached("control_weight_paint")
    require(paint is None or (paint.active(bpy.context) is None and paint.SESSION not in bpy.context.scene), "Weight-paint workspace would be restored by unload")
    fragments = ("This finger surface changed beyond complete loop subdivision/dissolve",
                 "Reference faces/edges changed; recapture this finger only.",
                 "Reference points changed or became ambiguous; recapture this finger only.",
                 "The reference geometry changed. Capture the finger definition again.",
                 "Geometry changed: Recheck symmetry.")
    for obj in bpy.data.objects:
        bank = getattr(obj, "character_designer_finger_bank", None)
        if bank is None:
            continue
        owners = [(bank, ("status", "bone_status", "needs_recheck"))]
        owners += [(owner, fields) for slot in bank.slots if slot.guide.record
                   for owner, fields in ((slot, ("error",)), (slot.guide, ("status",)))]
        require(not any(getattr(owner, field) and any(text in getattr(owner, field) for text in fragments)
                        for owner, fields in owners for field in fields),
                "Reload would clear existing legacy finger feedback: " + obj.name)


def complete_artist_owners(scene):
    """Reject a deleted/missing baseline before SaveCopy or refresh admission."""
    import bpy
    ft = sys.modules["character_designer.forearm_twist"]
    rig = scene.objects.get("CoshaRig")
    require(rig is not None and rig.type == "ARMATURE" and bpy.data.objects.get("CoshaRig") is rig,
            "Expected live CoshaRig membership is missing")
    meshes = {}
    for name in ("Cosha", "Shoes"):
        obj = scene.objects.get(name)
        require(obj is not None and obj.type == "MESH" and bpy.data.objects.get(name) is obj
                and obj.data is not None and bpy.data.meshes.get(obj.data.name) is obj.data,
                "Expected complete artist Mesh membership is missing: " + name)
        meshes[name] = obj
    owners = [obj for obj in bpy.data.objects if obj.type == "MESH" and ft.RECORD_KEY in obj]
    require(len(owners) == 1 and owners[0] is meshes["Cosha"], "Expected exactly the live Cosha Forearm owner")
    require(not ft._ERRORS, "Complete Forearm baseline has runtime errors")
    obj = meshes["Cosha"]
    records = ft._records(obj)
    require(set(records) == {"L", "R"} and obj.data.shape_keys is not None, "Expected complete L/R calibration and Key datablock")
    key_pointers = set()
    sides = {}
    for side in ("L", "R"):
        record = records[side]
        indices = record.get("vertices", ())
        require(len(indices) == 191 and len(set(indices)) == 191
                and len(record.get("positions", ())) == 191
                and all(type(index) is int and 0 <= index < len(obj.data.vertices) for index in indices)
                and record.get("enabled", True) is True and record.get("armature") == rig.name,
                "Expected enabled 191-vertex calibrated support: " + side)
        key = ft._managed_key(obj, side, record, required=True, repair_name=False)
        require(key is not None and not key.mute and key.value == 1.0
                and len(key.data) == len(obj.data.vertices)
                and key.relative_key.as_pointer() == obj.data.shape_keys.reference_key.as_pointer() and not key.vertex_group,
                "Expected enabled/present healthy managed output: " + side)
        require(key.as_pointer() not in key_pointers, "Managed L/R outputs share one Key")
        key_pointers.add(key.as_pointer())
        sides[side] = {"support_vertices": len(indices), "key": key.name, "pointer": key.as_pointer(),
                       "enabled": True, "value": key.value, "mute": key.mute}
    return {"scene": identity(scene), "rig": identity(rig), "Cosha": identity(meshes["Cosha"]),
            "Shoes": identity(meshes["Shoes"]), "calibrated_owner_count": 1, "sides": sides}


def context_record():
    import bpy
    return {"filepath": bpy.data.filepath, "window": bpy.context.window.as_pointer(),
            "screen": bpy.context.screen.as_pointer(), "area": bpy.context.area.as_pointer(),
            "area_type": bpy.context.area.type, "scene": identity(bpy.context.scene),
            "view_layer": bpy.context.view_layer.name, "workspace": identity(bpy.context.window.workspace),
            "frame": bpy.context.scene.frame_current, "subframe": bpy.context.scene.frame_subframe,
            "mode": bpy.context.mode, "active": identity(bpy.context.view_layer.objects.active),
            "selected": sorted(obj.as_pointer() for obj in bpy.context.selected_objects),
            "auto_key": bpy.context.scene.tool_settings.use_keyframe_insert_auto}


def handler_witness():
    import bpy
    result = {}
    for name in dir(bpy.app.handlers):
        collection = getattr(bpy.app.handlers, name)
        if not isinstance(collection, list):
            continue
        rows = [{"module": getattr(callback, "__module__", ""),
                 "name": getattr(callback, "__qualname__", getattr(callback, "__name__", type(callback).__name__)),
                 "python_id": id(callback)} for callback in collection]
        owned = [(row["module"], row["name"]) for row in rows
                 if row["module"] == "character_designer" or row["module"].startswith("character_designer.")]
        require(len(set(owned)) == len(owned), "Duplicate owned callback registration: " + name)
        result[name] = rows
    return result


def compare_handlers(before, after):
    require(set(before) == set(after), "Handler list schema changed")
    order_changes = []
    for kind, old in before.items():
        current = after[kind]
        owned = lambda row: row["module"] == "character_designer" or row["module"].startswith("character_designer.")
        semantic = lambda rows: [(row["module"], row["name"]) for row in rows]
        require(sorted(semantic([row for row in old if owned(row)])) == sorted(semantic([row for row in current if owned(row)])),
                "Owned callbacks were added or lost: " + kind)
        require([row for row in old if not owned(row)] == [row for row in current if not owned(row)],
                "Foreign callback object/order changed: " + kind)
        if semantic(old) != semantic(current):
            order_changes.append(kind)
    return order_changes


def animation_data(owner):
    data = owner.animation_data
    if data is None:
        return None
    return {"settings": rna(data), "tracks": [rna(track, collections=True) for track in data.nla_tracks],
            "drivers": [{"curve": rna(curve, collections=True), "driver": rna(curve.driver, collections=True)} for curve in data.drivers]}


def capture(cd, oracle):
    import bpy
    began = time.perf_counter()
    memory_guard()
    fingerprint = sys.modules["character_designer.animation_worklist_fingerprint"]
    components = {}
    actions = []
    for action in bpy.data.actions:
        slots = [{"handle": slot.handle, "identifier": slot.identifier,
                  "target_id_type": slot.target_id_type, "name_display": slot.name_display} for slot in action.slots] if action.is_action_layered else []
        motions = {str(handle): fingerprint.fingerprint_action(action, handle)
                   for handle in ([slot["handle"] for slot in slots] if slots else [0])}
        require(motions and all(item["fingerprint_known"] is True for item in motions.values()), "Unknown full Action content: " + action.name)
        actions.append({"identity": identity(action), "slots": slots, "motion": motions,
                        "properties": dict(action.items()), "settings": rna(action)})
    components["actions_slots_complete_motion"] = digest(actions)
    ids = sorted(bpy.data.user_map(), key=lambda block: block.as_pointer())
    id_rows = [{"identity": identity(block), "users": block.users, "fake_user": block.use_fake_user,
                "properties": dict(block.items()), "asset": rna(block.asset_data) if block.asset_data else None,
                "animation": animation_data(block) if hasattr(block, "animation_data") else None} for block in ids]
    components["all_ID_ownership_properties_animation_asset_catalog"] = digest(id_rows)
    objects, meshes, rigs, poses, managed = [], {}, {}, {}, {}
    ft = sys.modules["character_designer.forearm_twist"]
    for obj in bpy.data.objects:
        row = {"identity": identity(obj), "settings": rna(obj), "properties": dict(obj.items()),
               "basis": [list(values) for values in obj.matrix_basis], "parent_inverse": [list(values) for values in obj.matrix_parent_inverse],
               "modifiers": [dict(rna(mod, collections=True), custom_properties=dict(mod.items())) for mod in obj.modifiers],
               "constraints": [dict(rna(con, collections=True), custom_properties=dict(con.items()) if hasattr(con, "items") else {}) for con in obj.constraints],
               "groups": [rna(group) for group in obj.vertex_groups], "collections": sorted(col.as_pointer() for col in obj.users_collection),
               "hidden": obj.hide_get(), "selected": obj.select_get(), "active_shape_key": obj.active_shape_key_index}
        objects.append(row)
        if obj.type == "MESH":
            payload = oracle.mesh_content(obj, separate_generated=False)
            payload["settings"] = rna(obj.data)
            if obj.data.shape_keys:
                payload["shape_key_settings"] = rna(obj.data.shape_keys)
                payload["shape_key_states"] = [rna(key) for key in obj.data.shape_keys.key_blocks]
            meshes[obj.name] = digest(payload)
            if ft.RECORD_KEY in obj:
                require(obj.data.shape_keys is not None, "Managed output has no Key datablock")
                entries = []
                for side, record in ft._records(obj).items():
                    key = ft._managed_key(obj, side, record, required=True, repair_name=False)
                    entries.append({"side": side, "name": key.name, "pointer": key.as_pointer(),
                                    "value": key.value, "mute": key.mute,
                                    "coordinates": oracle.packed_digest(tuple(point.co) for point in key.data),
                                    "calibration_sha256": digest(record)})
                managed[obj.name] = entries
        if obj.type == "ARMATURE":
            rigs[obj.name] = {"settings": rna(obj.data), "bones": [{"name": bone.name, "pointer": bone.as_pointer(),
                "parent": bone.parent.name if bone.parent else None, "rest": [list(values) for values in bone.matrix_local],
                "rna": rna(bone), "properties": dict(bone.items()), "color": oracle.color(bone.color),
                "collections": sorted(col.name for col in bone.collections)} for bone in obj.data.bones],
                "collections": [dict(rna(col), properties=dict(col.items()), members=sorted(bone.name for bone in col.bones)) for col in obj.data.collections_all]}
            poses[obj.name] = [{"name": bone.name, "pointer": bone.as_pointer(), "rna": rna(bone),
                "properties": dict(bone.items()), "color": oracle.color(bone.color),
                "constraints": [rna(con, collections=True) for con in bone.constraints]} for bone in obj.pose.bones]
    components["objects_modifiers_constraints_transforms"] = digest(objects)
    components["mesh_topology_weights_all_shape_coordinates_states"] = digest(meshes)
    components["all_rig_Rest_colors_groups_widgets"] = digest(rigs)
    components["all_pose_channels_constraints"] = digest(poses)
    components["managed_full_coordinates_value_mute_calibration"] = digest(managed)
    scenes = [{"identity": identity(scene), "settings": rna(scene), "properties": dict(scene.items()),
               "setup": pg(scene.character_designer_setup), "worklist": pg(scene.character_designer_animation_worklist),
               "objects": sorted(obj.as_pointer() for obj in scene.objects), "render": rna(scene.render)} for scene in bpy.data.scenes]
    components["scene_setup_worklist_catalog"] = digest(scenes)
    components["materials_nodes"] = digest([oracle.material_content(mat) for mat in bpy.data.materials])
    ua = sys.modules["character_designer.unity_animation"]
    components["original_asset_output_proofs"] = digest({obj.name: oracle.asset_snapshot(bpy.context.scene, obj, ua)
                                                        for obj in bpy.data.objects if obj.type == "ARMATURE" and obj.name in {"CoshaRig", "CoshaRig.001"}})
    wm = {name: pg(getattr(bpy.context.window_manager, name)) for name, _cls in cd._WINDOW_MANAGER_POINTER_TYPES}
    components["WM_scalars_ID_pointers_collections"] = digest(wm)
    components["context"] = digest(context_record())
    return {"components": components, "combined_sha256": digest(components), "context": context_record(),
            "dirty": bool(bpy.data.is_dirty), "counts": {"IDs": len(ids), "Actions": len(actions), "meshes": len(meshes), "rigs": len(rigs)},
            "managed": exact(managed), "elapsed_seconds": time.perf_counter() - began}, wm


def differences(before, after):
    return [name for name, value in before["components"].items() if after["components"].get(name) != value]


class ProtectedRefresh:
    def __init__(self, window, screen, area, scene):
        self.window, self.screen, self.area, self.scene = window, screen, area, scene
        self.poll_callback = self.poll
        self.created = time.monotonic()
        self.output = ROUND / ("refresh_07741_" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:12])
        self.output.mkdir()
        self.report = {"schema": "x.protected-live-refresh-07741/1", "created_utc": utc(), "pid": os.getpid(),
                       "completed": False, "phase": "created", "artist_saved": False,
                       "file_opened": False, "manual_reacquire_called": False, "frame_set_called": False,
                       "manual_forearm_update_called": False, "automatic_scene_rollback": False,
                       "scope": "Exact recorded authored content/identity witnesses; no Undo-stack preservation proof.",
                       "source": pin(Path(__file__)), "errors": []}
        self.closed = False
        self.oracle = None
        self.savecopy = self.output / "artist_unsaved_before_07741.blend"
        self.before = self.wm = None
        self.old = None
        self.scheduled = False
        self.seen_new_timer = None
        self.deadline = None
        self.restored_wm = None
        self.write()

    def write(self):
        path = self.output / "refresh_receipt.json"
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(self.report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temp.replace(path)

    def finish(self, error=None):
        import bpy
        self.report["finished_utc"] = utc()
        if error:
            self.report["completed"] = False
            self.report["errors"].append(str(error))
            self.report["phase"] = "failed_" + self.report["phase"]
        self.closed = True
        try:
            self.report["final_artist_disk"] = pin(ARTIST)
            self.report["artist_disk_unchanged"] = all(self.report["final_artist_disk"][key] == value for key, value in ARTIST_PIN.items())
            self.report["final_filepath"] = bpy.data.filepath
            self.report["final_dirty"] = bool(bpy.data.is_dirty)
            self.report["savecopy_retained"] = self.savecopy.exists()
            if self.report["completed"]:
                require(self.report["artist_disk_unchanged"] and Path(bpy.data.filepath).resolve() == ARTIST.resolve()
                        and self.before is not None and self.report["final_dirty"] == self.before["dirty"]
                        and not self.report["errors"], "Final disk/filepath/dirty/error guard failed")
        except Exception:
            self.report["completed"] = False
            self.report["phase"] = "failed_final_guard"
            self.report["errors"].append(traceback.format_exc())
        self.report["helper_cleanup"] = "Closed helper/source/oracle retained for audit; call controller.release() in a later idle event-loop turn."
        self.write()
        print(json.dumps({"completed": self.report["completed"], "phase": self.report["phase"], "receipt": str(self.output / "refresh_receipt.json")}, ensure_ascii=False))

    def release(self):
        """Remove only this closed task's helpers after its timer returned None."""
        import bpy
        require(self.closed and not bpy.app.timers.is_registered(self.poll_callback), "Refresh is still active; retain its ownership")
        helper = sys.modules.get(HELPER_NAME)
        require(helper is not None and getattr(helper, "controller", None) is self, "Helper ownership changed")
        oracle = sys.modules.get(HELPER_NAME + "_oracle")
        require(oracle is None or oracle is self.oracle, "Oracle ownership changed")
        source = sys.modules.get(HELPER_NAME + "_source")
        require(source is not None and vars(source) is globals(), "Source helper ownership changed")
        self.report["helper_cleanup"] = "Owned closed helper/source/oracle removed; no live timer."
        self.report["helper_released_utc"] = utc()
        self.write()
        sys.modules.pop(HELPER_NAME + "_oracle", None)
        sys.modules.pop(HELPER_NAME + "_source", None)
        sys.modules.pop(HELPER_NAME, None)
        return {"released": True, "receipt": str(self.output / "refresh_receipt.json")}

    def prepare(self):
        import bpy
        require_context(self.window, self.screen, self.area, self.scene)
        self.report["memory"] = memory_guard()
        self.report["artist_disk_before"] = pin(ARTIST, ARTIST_PIN)
        cd = sys.modules.get("character_designer")
        require(cd is not None and tuple(cd.bl_info["version"]) == (0, 77, 40), "Live artist runtime must be .40")
        root = Path(cd.__file__).resolve().parent
        require(root == EXPECTED_RUNTIME_ROOT.resolve(), "Unexpected installed runtime root")
        cd._validate_registration_integrity()
        idle(cd)
        self.report["complete_artist_owner_before"] = complete_artist_owners(self.scene)
        self.report["handlers_before"] = handler_witness()
        self.report["candidate_proof"], self.files = package_proof(root)
        self.old = cd
        self.oracle = load_oracle()
        self.report["phase"] = "capture_before_SaveCopy"
        self.write()
        self.before, self.wm = capture(cd, self.oracle)
        self.report["before"] = self.before
        self.report["phase"] = "SaveCopy"
        self.write()
        idle(cd)
        require(bpy.ops.wm.save_as_mainfile.poll(), "SaveCopy poll failed")
        returned = bpy.ops.wm.save_as_mainfile("EXEC_DEFAULT", filepath=str(self.savecopy), copy=True, check_existing=False)
        self.report["savecopy_result"] = sorted(returned)
        require(returned == {"FINISHED"} and self.savecopy.is_file(), "SaveCopy did not finish")
        self.report["savecopy"] = pin(self.savecopy)
        require_context(self.window, self.screen, self.area, self.scene)
        self.report["phase"] = "capture_after_SaveCopy"
        after, _wm = capture(cd, self.oracle)
        self.report["after_SaveCopy"] = after
        require(not differences(self.before, after) and self.before["dirty"] == after["dirty"], "SaveCopy changed protected artist content/context/dirty")
        pin(ARTIST, ARTIST_PIN)
        idle(cd)
        require(complete_artist_owners(self.scene) == self.report["complete_artist_owner_before"], "Complete owner membership changed before official refresh")
        self.report["phase"] = "waiting_official_refresh_poll"
        self.write()
        self.deadline = time.monotonic() + TIMEOUT_SECONDS
        bpy.app.timers.register(self.poll_callback, first_interval=0.02)

    def poll(self):
        import bpy
        if self.closed:
            return None
        try:
            require_context(self.window, self.screen, self.area, self.scene)
            require(self.deadline is not None and time.monotonic() < self.deadline, "Natural refresh/lifecycle/output verification timed out")
            with bpy.context.temp_override(window=self.window, screen=self.screen, area=self.area):
                if not self.scheduled:
                    require(sys.modules.get("character_designer") is self.old, "Runtime changed before official refresh")
                    idle(self.old)
                    require(complete_artist_owners(self.scene) == self.report["complete_artist_owner_before"], "Complete owner membership changed before refresh scheduling")
                    if not bpy.ops.character_designer.refresh_addon.poll():
                        return 0.1
                    self.report["phase"] = "official_refresh_scheduled"
                    self.report["refresh_result"] = sorted(bpy.ops.character_designer.refresh_addon())
                    require(self.report["refresh_result"] == ["FINISHED"], "Official refresh did not schedule")
                    self.scheduled = True
                    self.deadline = time.monotonic() + TIMEOUT_SECONDS
                    self.write()
                    return 0.02
                new = sys.modules.get("character_designer")
                if new is self.old or new is None:
                    require(not getattr(self.old, "ADDON_REFRESH_LAST_ERROR", ""), "Official refresh error: " + getattr(self.old, "ADDON_REFRESH_LAST_ERROR", ""))
                    return 0.02
                require(tuple(new.bl_info["version"]) == (0, 77, 41), "Unexpected refreshed runtime version")
                require(not new.ADDON_REFRESH_LAST_ERROR, "New runtime refresh error: " + new.ADDON_REFRESH_LAST_ERROR)
                if new.ADDON_REFRESH_PENDING:
                    return 0.02
                native = sys.modules.get("character_designer.unity_animation_rigging")
                ft = sys.modules.get("character_designer.forearm_twist")
                require(native is not None and ft is not None, "Refreshed lifecycle module missing")
                if native._REACQUIRE_TIMER is not None:
                    self.seen_new_timer = native._REACQUIRE_TIMER
                require(not native._HANDLER_ERRORS and not ft._ERRORS, "Natural lifecycle/runtime reported errors")
                if native._REACQUIRE_TIMER is not None or native._REACQUIRE_PENDING or ft._INITIALIZE_PENDING or ft._SCENE_CLEANUP_PENDING or ft._BUSY:
                    return 0.02
                require(native._REACQUIRE_GENERATION == 2, "Fresh standard registration lifecycle did not naturally complete its expected generation")
                # No frame_set, view_layer.update or direct runtime call: wait for
                # the real depsgraph callback to restore managed output state.
                current_managed = {}
                for obj in bpy.data.objects:
                    if obj.type == "MESH" and ft.RECORD_KEY in obj:
                        entries = []
                        for side, record in ft._records(obj).items():
                            key = ft._managed_key(obj, side, record, required=True, repair_name=False)
                            entries.append({"side": side, "name": key.name, "pointer": key.as_pointer(), "value": key.value, "mute": key.mute,
                                            "coordinates": self.oracle.packed_digest(tuple(point.co) for point in key.data), "calibration_sha256": digest(record)})
                        current_managed[obj.name] = entries
                if exact(current_managed) != self.before["managed"]:
                    self.report["phase"] = "waiting_natural_same_frame_managed_output"
                    self.report["managed_last_observed"] = exact(current_managed)
                    return 0.1
                self.report["phase"] = "verify_refreshed_protection"
                self.write()
                if self.restored_wm is None:
                    self.restored_wm = []
                    for name, fields in self.wm.items():
                        restore_changed_wm(getattr(bpy.context.window_manager, name), fields, name, self.restored_wm)
                    self.report["restored_only_changed_WM_scalars_IDs"] = self.restored_wm
                    if self.restored_wm:
                        self.report["phase"] = "waiting_natural_after_WM_restore"
                        self.write()
                        return 0.05
                new._validate_registration_integrity()
                self.report["handlers_after"] = handler_witness()
                self.report["handler_order_changes"] = compare_handlers(self.report["handlers_before"], self.report["handlers_after"])
                proof, _files = package_proof(Path(new.__file__).resolve().parent)
                for name, module in tuple(sys.modules.items()):
                    if name == "character_designer" or name.startswith("character_designer."):
                        path = Path(module.__file__).resolve()
                        root = EXPECTED_RUNTIME_ROOT.resolve()
                        require(path.is_relative_to(root), "Refreshed module has a foreign root: " + name)
                        relative = path.relative_to(root).as_posix()
                        require(relative in self.files and pin(path)["sha256"] == self.files[relative], "Refreshed source pin differs: " + name)
                after, _wm = capture(new, self.oracle)
                self.report["after"] = after
                self.report["changed_components"] = differences(self.before, after)
                self.report["natural_lifecycle"] = {"generation": native._REACQUIRE_GENERATION,
                    "timer_observed": self.seen_new_timer is not None, "timer_empty": native._REACQUIRE_TIMER is None,
                    "pending_empty": not native._REACQUIRE_PENDING, "errors_empty": not native._HANDLER_ERRORS,
                    "managed_output_same_frame_equal": exact(current_managed) == self.before["managed"]}
                require(not self.report["changed_components"] and after["dirty"] == self.before["dirty"], "Refreshed protection/content/context/dirty differs")
                pin(ARTIST, ARTIST_PIN)
                idle(new)
                self.report["complete_artist_owner_after"] = complete_artist_owners(self.scene)
                require(self.report["complete_artist_owner_after"] == self.report["complete_artist_owner_before"], "Complete owner membership changed after refresh")
                self.report.update(completed=True, phase="completed", loaded_version=[0, 77, 41], final_candidate_proof=proof)
                self.finish()
                return None
        except BaseException:
            self.report["traceback"] = traceback.format_exc()
            self.finish(self.report["traceback"])
            return None


def begin(window, screen, area, scene):
    """Only called by the separate pinned one-shot Console installer."""
    require(HELPER_NAME not in sys.modules, "A protected refresh already exists")
    helper = types.ModuleType(HELPER_NAME)
    sys.modules[HELPER_NAME] = helper
    controller = ProtectedRefresh(window, screen, area, scene)
    helper.controller = controller
    try:
        import bpy
        with bpy.context.temp_override(window=window, screen=screen, area=area):
            controller.prepare()
    except BaseException:
        controller.report["traceback"] = traceback.format_exc()
        controller.finish(controller.report["traceback"])
    return controller
