"""Three isolated native Rest roundtrips from the failed public library.

Prepare/run only in a new Blender 5.1 factory background child. Never saves a
blend, edits the original rig, repairs its home Scene, evaluates source meshes,
resets/bakes/replays Cloth, launches children, deploys or publishes anything.
Opening a native library can evaluate cold dependencies; no zero-evaluation
claim is made. Every branch owns separate Object AND Armature data copies.
"""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy
from mathutils import Matrix, Vector


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
INPUT = HERE / "actual_export_51_20261006_035935_884/scenes/Cosha_Dress_QA_public_library.blend"
WORKER = Path(r"D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\unity_export_worker.py")
GUARD = 3.e-6
BRANCHES = ("native_edit_roundtrip", "canonical_clean_skeleton", "native_geometry_filter")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def disk(path):
    return {"path": str(path), "exists": path.is_file(),
            **({"bytes": path.stat().st_size, "sha256": sha(path)} if path.is_file() else {})}


def digest(content):
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True,
                                    allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, required=True, help="New dedicated Validation directory")
    parser.add_argument("--rig", default="CoshaRig", help="Exact source name; no rig heuristic")
    parser.add_argument("--artist", type=Path, default=PROJECT / "X.blend", help="Read-only artist disk protection")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args.input, args.output, args.artist = (path.resolve() for path in (args.input, args.output, args.artist))
    require(args.input == INPUT.resolve() and args.input.is_file(), "Use this exact failed public library")
    require(args.output.is_relative_to(HERE) and args.output != HERE and not args.input.is_relative_to(args.output),
            "Use an independent diagnostic child directory")
    require(not (args.output / "static_rest_roundtrip.json").exists(), "Refusing to replace an existing diagnostic")
    require(args.input != args.artist, "Artist and diagnostic input must be separate")
    return args


def vector(value):
    return [float(component) for component in value]


def matrix(value):
    return [[float(component) for component in row] for row in value]


def parent_name(bone):
    return bone.parent.name if bone.parent is not None else None


def rest_content(obj):
    result = {}
    for bone in obj.data.bones:
        axis = bone.tail_local - bone.head_local
        require(axis.length > 0., "Degenerate original Rest bone: " + bone.name)
        # Native API already used by canonical limb_ik.py. Bone has no roll
        # property; this is explicitly a roll derived from its native matrix.
        _axis, roll = bpy.types.Bone.AxisRollFromMatrix(bone.matrix_local.to_3x3(), axis=axis.normalized())
        result[bone.name] = {"matrix": matrix(bone.matrix_local), "head": vector(bone.head_local),
            "tail": vector(bone.tail_local), "roll_from_native_matrix": float(roll), "length": float(bone.length),
            "parent": parent_name(bone), "connect": bool(bone.use_connect), "deform": bool(bone.use_deform),
            "inherit_scale": bone.inherit_scale, "inherit_rotation": bool(bone.use_inherit_rotation),
            "local_location": bool(bone.use_local_location)}
    require(all(math.isfinite(value) for entry in result.values() for row in entry["matrix"] for value in row),
            "Nonfinite native Rest matrix")
    return result


def edit_content(obj):
    # Only plain floats/strings survive the subsequent mode change.
    return {bone.name: {"matrix": matrix(bone.matrix), "head": vector(bone.head), "tail": vector(bone.tail),
                       "roll": float(bone.roll), "length": float(bone.length),
                       "parent": parent_name(bone), "connect": bool(bone.use_connect)}
            for bone in obj.data.edit_bones}


def matrix_gap(first, second):
    return max(abs(first[row][column]-second[row][column]) for row in range(4) for column in range(4))


def vector_gap(first, second):
    return math.sqrt(sum((a-b) ** 2 for a, b in zip(first, second)))


def angle_gap(first, second):
    return abs((first-second+math.pi) % math.tau-math.pi)


def comparison(source, before, entry, pre_exit, after):
    details = {}
    for name in after:
        original, start, entering, exiting, output = source[name], before[name], entry[name], pre_exit[name], after[name]
        details[name] = {"original_rest": original, "copy_before_rest": start,
                        "entry_edit": entering, "pre_exit_edit": exiting, "output_rest": output,
            "copy_before_vs_original_matrix_max": matrix_gap(start["matrix"], original["matrix"]),
            "entry_edit_vs_before_rest_matrix_max": matrix_gap(entering["matrix"], start["matrix"]),
            "pre_exit_vs_entry_edit_matrix_max": matrix_gap(exiting["matrix"], entering["matrix"]),
            "output_rest_vs_pre_exit_edit_matrix_max": matrix_gap(output["matrix"], exiting["matrix"]),
            "output_rest_vs_original_matrix_max": matrix_gap(output["matrix"], original["matrix"]),
            "output_head_delta": vector_gap(output["head"], original["head"]),
            "output_tail_delta": vector_gap(output["tail"], original["tail"]),
            "output_length_delta": abs(output["length"]-original["length"]),
            "entry_native_roll_vs_original_derived_roll_rad": angle_gap(entering["roll"], original["roll_from_native_matrix"]),
            "output_derived_roll_vs_entry_native_roll_rad": angle_gap(output["roll_from_native_matrix"], entering["roll"]),
            "output_parent_changed": output["parent"] != original["parent"],
            "output_connect_changed": output["connect"] != original["connect"]}
    ordered = sorted(details, key=lambda name: details[name]["output_rest_vs_original_matrix_max"], reverse=True)
    maximum = max((details[name]["output_rest_vs_original_matrix_max"] for name in ordered), default=None)
    return {"retained_names": sorted(after), "per_bone": details,
            "original_bone_count": len(source), "retained_bone_count": len(after),
            "removed_names": sorted(set(source)-set(after)), "matrix_guard": GUARD,
            "matrix_comparison_space": "Native Armature-local Bone.matrix_local, identical to existing export gate",
            "rest_within_guard": maximum is not None and maximum <= GUARD,
            "matrix_max_error": maximum, "worst_entry": ordered[0] if ordered else None,
            "worst_eight": [{"name": name, **{key: value for key, value in details[name].items()
                                             if not isinstance(value, dict)}} for name in ordered[:8]],
            "over_guard_names": [name for name in ordered if details[name]["output_rest_vs_original_matrix_max"] > GUARD],
            "head_tail_roll_parent_changes": [name for name in sorted(after) if
                details[name]["output_head_delta"] > 0. or details[name]["output_tail_delta"] > 0.
                or details[name]["output_derived_roll_vs_entry_native_roll_rad"] > 0.
                or details[name]["output_parent_changed"] or details[name]["output_connect_changed"]]}


def activate(obj):
    bpy.context.view_layer.update()
    for candidate in bpy.context.view_layer.objects:
        candidate.select_set(False)
    obj.hide_set(False)
    obj.hide_viewport = obj.hide_select = obj.hide_render = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if obj.mode != "OBJECT":
        require("FINISHED" in bpy.ops.object.mode_set(mode="OBJECT"), "Private copy did not enter Object Mode")


def owned_copy(source, scene, name):
    obj = source.copy()
    data = None
    try:
        data = source.data.copy()
        require(data != source.data and data.library is None and data.override_library is None,
                "The diagnostic requires independent local Armature data")
        obj.data = data
        obj.name, data.name = "QA Rest " + name, "QA Rest " + name + " Data"
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
        for owner in (obj, data):
            owner.animation_data_clear()  # Independent AnimData; borrowed author Actions are not edited.
            owner.use_fake_user = False
        for constraint in tuple(obj.constraints):
            obj.constraints.remove(constraint)
        for bone in obj.pose.bones:
            for constraint in tuple(bone.constraints):
                bone.constraints.remove(constraint)
            bone.matrix_basis = Matrix.Identity(4)
        data.pose_position = "REST"
        scene.collection.objects.link(obj)
        require(data.users == 1, "The copied Armature acquired an outside user")
        activate(obj)
        return obj, data
    except Exception:
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.armatures.remove(data)
        raise


def release_copy(obj, data):
    if obj.mode != "OBJECT":
        bpy.context.view_layer.objects.active = obj
        require("FINISHED" in bpy.ops.object.mode_set(mode="OBJECT"), "Private diagnostic Edit cleanup failed")
    require(bpy.data.objects.get(obj.name) == obj and bpy.data.armatures.get(data.name) == data,
            "A private diagnostic ID was replaced")
    bpy.data.objects.remove(obj, do_unlink=True)
    require(data.users == 0, "A private diagnostic Armature has an outside user; preserve it")
    bpy.data.armatures.remove(data)
    bpy.context.view_layer.update()


class Delegate:
    def __init__(self, target, **overrides):
        self.target, self.overrides = target, overrides
    def __getattr__(self, name):
        return self.overrides[name] if name in self.overrides else getattr(self.target, name)


def canonical_branch(worker, obj, capture):
    original_bpy = worker.bpy
    def mode_set(*args, **options):
        if options.get("mode") == "OBJECT" and obj.mode == "EDIT":
            capture["pre_exit"] = edit_content(obj)
        result = bpy.ops.object.mode_set(*args, **options)
        require("FINISHED" in result, "Native canonical mode switch did not finish")
        if options.get("mode") == "EDIT":
            capture["entry"] = edit_content(obj)
        return result
    try:
        worker.bpy = Delegate(bpy, ops=Delegate(bpy.ops, object=Delegate(bpy.ops.object, mode_set=mode_set)))
        return worker._clean_skeleton(bpy.context, obj, objects=[obj])
    finally:
        worker.bpy = original_bpy


def geometry_filter(worker, obj, capture):
    # Same current filter/reparent policy as _clean_skeleton with objects=[obj].
    accessory = bool(obj.get("character_designer_skirt_owner") or obj.get("character_designer_hair_bones_owner")
                     or obj.get("character_designer_hair_variant_version"))
    names = {bone.name for bone in obj.data.bones if not worker._is_control(bone) and (not accessory or bone.use_deform)}
    require(any(obj.data.bones[name].use_deform for name in names), "No deform skeleton retained")
    require("FINISHED" in bpy.ops.object.mode_set(mode="EDIT"), "Native geometry branch did not enter Edit Mode")
    restored = []
    try:
        capture["entry"] = edit_content(obj)
        saved = {name: capture["entry"][name] for name in names}
        parents = {}
        for name in names:
            parent = obj.data.edit_bones[name].parent
            while parent is not None and parent.name not in names:
                parent = parent.parent
            parents[name] = parent.name if parent is not None else None
        for name in names:
            bone = obj.data.edit_bones[name]
            bone.use_connect = False
            bone.parent = obj.data.edit_bones.get(parents[name]) if parents[name] else None
        for bone in tuple(obj.data.edit_bones):
            if bone.name not in names:
                obj.data.edit_bones.remove(bone)
        for name in names:
            bone, fields = obj.data.edit_bones[name], []
            # Restore native geometry only when actually changed. No EditBone
            # matrix setter or roll/axis decomposition roundtrip is used here.
            if vector(bone.head) != saved[name]["head"]:
                bone.head = Vector(saved[name]["head"])
                fields.append("head")
            if vector(bone.tail) != saved[name]["tail"]:
                bone.tail = Vector(saved[name]["tail"])
                fields.append("tail")
            if float(bone.roll) != saved[name]["roll"]:
                bone.roll = saved[name]["roll"]
                fields.append("roll")
            if fields:
                restored.append({"name": name, "fields": fields})
        capture["pre_exit"] = edit_content(obj)
        capture["conditional_geometry_restores"] = restored
    finally:
        require("FINISHED" in bpy.ops.object.mode_set(mode="OBJECT"), "Native geometry branch did not leave Edit Mode")
    obj.data.pose_position = "REST"
    for bone in obj.pose.bones:
        bone.custom_shape = None
        bone.matrix_basis = Matrix.Identity(4)
    return sorted(names)


def run_branch(name, source, source_rest, scene, worker):
    result = {"name": name, "native_operations_finished": False}
    obj = data = None
    try:
        obj, data = owned_copy(source, scene, name.replace("_", " "))
        before = rest_content(obj)
        require(before == source_rest, "The independent copy differs before its first native Edit operation")
        capture = {}
        if name == "native_edit_roundtrip":
            require("FINISHED" in bpy.ops.object.mode_set(mode="EDIT"), "Native roundtrip did not enter Edit Mode")
            capture["entry"] = edit_content(obj)
            capture["pre_exit"] = edit_content(obj)
            require("FINISHED" in bpy.ops.object.mode_set(mode="OBJECT"), "Native roundtrip did not leave Edit Mode")
            retained = sorted(before)
        elif name == "canonical_clean_skeleton":
            retained = canonical_branch(worker, obj, capture)
        else:
            retained = geometry_filter(worker, obj, capture)
        after = rest_content(obj)
        require(sorted(after) == retained, "The branch returned a different retained inventory")
        result.update(comparison(source_rest, before, capture["entry"], capture["pre_exit"], after))
        result["conditional_geometry_restores"] = capture.get("conditional_geometry_restores")
        result["native_operations_finished"] = True
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        if obj is not None:
            try:
                release_copy(obj, data)
                result["private_copy_removed"] = True
            except Exception as error:
                result["native_operations_finished"] = False
                result["cleanup_error"] = str(error)
    return result


def main(args):
    require(bpy.app.background and "--factory-startup" in sys.argv and "--disable-autoexec" in sys.argv
            and not bpy.data.filepath and bpy.app.version[:2] == (5, 1), "Use a fresh isolated Blender 5.1 factory background child")
    require("--threads" in sys.argv and sys.argv[sys.argv.index("--threads") + 1] == "1", "Use --threads 1")
    report = {"success": False, "success_scope": "Diagnostic execution/source protection only; inspect each branch rest_within_guard",
              "production_export_accepted": False, "input_saved": False, "artist_saved": False,
              "input_before": disk(args.input), "artist_before": disk(args.artist),
              "blender_version": bpy.app.version_string, "script_sha256": sha(Path(__file__)),
              "worker_path": str(WORKER), "worker_sha256_before": sha(WORKER), "matrix_guard": GUARD,
              "branches": [], "limits": ["Private copy-only Rest diagnosis; no production homeScene repair",
                  "No source mesh evaluation or Cloth Reset/Bake/forward replay; cold native load evaluation is possible",
                  "Canonical branch uses objects=[copy], isolating Rest behavior without skin/attachment export acceptance",
                  "Bone roll is derived by native AxisRollFromMatrix; entry/pre-exit EditBone roll is native RNA"]}
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    source = scene = None
    source_rest = None
    try:
        require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False),
                "Public diagnostic library could not be opened")
        source = bpy.data.objects.get(args.rig)
        require(source is not None and source.type == "ARMATURE", "The exact source Armature is missing")
        source_rest = rest_content(source)
        source_identity = (source.as_pointer(), source.data.as_pointer())
        report["source"] = {"name": source.name, "data": source.data.name, "bones": len(source_rest),
                            "rest_sha256_before": digest(source_rest), "original_rest": source_rest}
        before_ids = {kind: sorted(block.name for block in getattr(bpy.data, kind))
                      for kind in ("objects", "armatures", "scenes")}
        spec = importlib.util.spec_from_file_location("cdesigner_rest_diagnostic_worker", WORKER)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)  # No add-on registration or worker main().
        require(bpy.context.window is not None, "Native background context has no Window for the private Scene")
        original_scene = bpy.context.window.scene
        scene = bpy.data.scenes.new("QA Private Rest Diagnosis")
        scene.tool_settings.use_keyframe_insert_auto = False
        bpy.context.window.scene = scene
        report["private_scene_policy"] = "Copies only; this is not a replacement for or repair of the proven production homeScene"
        for name in BRANCHES:
            report["branches"].append(run_branch(name, source, source_rest, scene, worker))
            require((source.as_pointer(), source.data.as_pointer()) == source_identity and rest_content(source) == source_rest,
                    "A branch changed the original source Rest/identity")
        retained = [branch.get("retained_names") for branch in report["branches"][1:]]
        report["filtered_branch_retained_names_equal"] = retained[0] is not None and retained[0] == retained[1]
        bpy.context.window.scene = original_scene
        bpy.data.scenes.remove(scene)
        scene = None
        after_ids = {kind: sorted(block.name for block in getattr(bpy.data, kind))
                     for kind in ("objects", "armatures", "scenes")}
        report["original_id_inventory_exact"] = after_ids == before_ids
        report["success"] = all(branch["native_operations_finished"] for branch in report["branches"])
        report["success"] = report["success"] and report["filtered_branch_retained_names_equal"] and report["original_id_inventory_exact"]
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        if scene is not None:
            try:
                if bpy.context.window.scene == scene:
                    alternatives = [candidate for candidate in bpy.data.scenes if candidate != scene]
                    require(bool(alternatives), "No original Scene available for private cleanup")
                    bpy.context.window.scene = alternatives[0]
                bpy.data.scenes.remove(scene)
            except Exception as error:
                report["success"] = False
                report["private_scene_cleanup_error"] = str(error)
        if source_rest is not None:
            try:
                report["source_rest_sha256_after"] = digest(rest_content(source))
                report["original_source_rest_exact"] = rest_content(source) == source_rest
            except Exception as error:
                report["original_source_rest_exact"] = False
                report["source_protection_error"] = str(error)
        report["input_after"], report["artist_after"] = disk(args.input), disk(args.artist)
        report["input_disk_exact"] = report["input_after"] == report["input_before"]
        report["artist_disk_exact"] = report["artist_after"] == report["artist_before"]
        report["worker_sha256_after"] = sha(WORKER)
        report["worker_code_exact"] = report["worker_sha256_after"] == report["worker_sha256_before"]
        report["script_code_exact"] = sha(Path(__file__)) == report["script_sha256"]
        report["success"] = report["success"] and all(report.get(key) is True for key in
            ("original_source_rest_exact", "input_disk_exact", "artist_disk_exact", "worker_code_exact", "script_code_exact"))
        report["elapsed_seconds"] = time.perf_counter()-started
        destination = args.output / "static_rest_roundtrip.json"
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"success": report["success"], "report": str(destination), "elapsed_seconds": report["elapsed_seconds"]}), flush=True)
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
