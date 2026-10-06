"""Private affine/TRS localization; no canonical fix or acceptance.

Exact legacy 7ac + current 9d7, empty factory/background Blender 5.1 only.
Observe the unchanged controlled Rest-chart constructor before assignment and
before its unchanged 4e-5 matrix guard; then compare the frozen a725 current-pose
conversion on a separate private clone. No frame, Action, cache, save or bake.
Extra native wire/mesh reads may warm evaluation; this does not prove causality.
"""
import argparse
import ast
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
UPGRADE = HERE / "verify_neutral_manual_reference_upgrade.py"
UPGRADE_SHA = "bfa061a5ac95da758ecd5d42dcc8187ff5316b604439a31298bae1a36358ec76"
CURRENT = HERE / "prototype_neutral_manual_fk_reference.py"
CURRENT_SHA = "a725ac8d2a60388b7a6274e5210b4ed7fc202777d854636c0a54db6a361791d6"


def require(value, message):
    if not value:
        raise RuntimeError("Neutral Rest-chart diagnostic: " + message)


def plain(value):
    result = [[float(x) for x in row] for row in value]
    require(all(math.isfinite(x) for row in result for x in row), "nonfinite native matrix")
    return result


def metrics(value):
    location, rotation, scale = value.decompose()
    recomposed = Matrix.LocRotScale(location, rotation, scale)
    columns = [value.to_3x3().col[index].copy() for index in range(3)]
    lengths = [column.length for column in columns]
    require(all(length > 0. for length in lengths), "singular affine decomposition")
    return {"matrix": plain(value), "translation": list(location), "quaternion": list(rotation), "scale": list(scale),
            "column_lengths": lengths, "determinant_3x3": value.to_3x3().determinant(),
            "normalized_column_dot": {str(i)+"/"+str(j): columns[i].dot(columns[j])/(lengths[i]*lengths[j])
                                      for i in range(3) for j in range(i+1, 3)},
            "native_TRS_recomposition": plain(recomposed),
            "TRS_recomposition_max_matrix_error": maximum(value, recomposed)}


def maximum(first, second):
    return max(abs(float(first[i][j])-float(second[i][j])) for i in range(4) for j in range(4))


def id_inventory(current):
    return current.inventory() | {name: {item.name: item.as_pointer() for item in getattr(bpy.data, name)}
                                 for name in ("curves", "collections")}


def errors(first, second, metres):
    left, right = first.decompose(), second.decompose()
    return {"matrix_max": maximum(first, second), "translation_m": (left[0]-right[0]).length*metres,
            "rotation_difference_radians": left[1].rotation_difference(right[1]).angle,
            "scale_component_max": max(abs(float(a)-float(b)) for a, b in zip(left[2], right[2])),
            "linear_3x3_max": max(abs(float(first[i][j])-float(second[i][j])) for i in range(3) for j in range(3))}


def summary(bones):
    worst = sorted(bones, key=lambda name: bones[name]["actual_vs_desired"]["matrix_max"], reverse=True)
    return {"count": len(bones), "over_unchanged_4e_minus_5_matrix_guard": sum(bones[name]["actual_vs_desired"]["matrix_max"] > 4e-5 for name in bones),
            "worst8": [{"bone": name, "actual_vs_desired": bones[name]["actual_vs_desired"],
                        "requested_basis_TRS_residual": bones[name]["requested_basis"]["TRS_recomposition_max_matrix_error"],
                        "assignment_basis_loss": bones[name]["assignment_basis_loss"],
                        "inverse_forward_roundtrip": bones[name]["inverse_forward_roundtrip"]} for name in worst[:8]]}


def rows(reference, desired, bases, graph, metres):
    posed = reference.evaluated_get(graph)
    result = {}
    for name, basis in bases.items():
        bone = reference.pose.bones[name]
        parent_options = {"parent_matrix": desired[bone.parent.name],
                          "parent_matrix_local": bone.parent.bone.matrix_local} if bone.parent else {}
        from_requested = bone.bone.convert_local_to_pose(basis, bone.bone.matrix_local, **parent_options)
        from_getter = bone.bone.convert_local_to_pose(bone.matrix_basis, bone.bone.matrix_local, **parent_options)
        actual = posed.pose.bones[name].matrix.copy()
        result[name] = {"parent": bone.parent.name if bone.parent else None, "rotation_mode": bone.rotation_mode,
            "bone_flags": {"inherit_scale": bone.bone.inherit_scale, "inherit_rotation": bone.bone.use_inherit_rotation,
                           "local_location": bone.bone.use_local_location, "connect": bone.bone.use_connect,
                           "rest_length": bone.bone.length},
            "rest": plain(bone.bone.matrix_local), "desired_parent": plain(desired[bone.parent.name]) if bone.parent else None,
            "parent_rest": plain(bone.parent.bone.matrix_local) if bone.parent else None,
            "desired": metrics(desired[name]), "requested_basis": metrics(basis), "stored_basis": metrics(bone.matrix_basis),
            "actual": metrics(actual), "assignment_basis_loss": errors(basis, bone.matrix_basis, metres),
            "inverse_forward_roundtrip": errors(desired[name], from_requested, metres),
            "stored_basis_with_desired_parent": errors(desired[name], from_getter, metres),
            "actual_vs_desired": errors(desired[name], actual, metres)}
    return result


def wire_rows(wires, graph, diag, surface):
    result = {}
    for wire in wires:
        posed = wire.evaluated_get(graph)
        snapshot = diag.json_content(diag.mesh_snapshot(wire, graph))
        result[wire.name] = {"frame": surface._frame(wire), "original_world": plain(wire.matrix_world),
            "evaluated_world": plain(posed.matrix_world), "native_tessellated_world_points": snapshot["points"],
            "native_edges": snapshot["edges"], "RNA_control_points": [[list(point.co) for point in spline.points] for spline in wire.data.splines],
            "Hooks": [surface._rna(modifier) for modifier in wire.modifiers]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    args.output = args.output.resolve()
    require(args.output.is_relative_to(HERE) and args.output != HERE and not args.output.exists(), "fresh unique Validation child required")
    require(bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath
            and bpy.app.version[:2] == (5, 1), "empty factory/background Blender 5.1 required")
    import hashlib
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    require(sha(UPGRADE) == UPGRADE_SHA and sha(CURRENT) == CURRENT_SHA, "frozen helper changed")
    import importlib.util

    def load(path, name):
        require(name not in sys.modules, "diagnostic module already loaded")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    helper = load(UPGRADE, "rest_chart_upgrade_helpers")
    current = load(CURRENT, "rest_chart_frozen_current_pose")
    pins_before = {str(path): sha(path) for path in helper.PINS}
    require(all(pins_before[str(path)] == expected for path, expected in helper.PINS.items()), "fixed input/runtime/artist pin changed")
    own_sha = sha(Path(__file__))
    workflow = helper.load(HERE / "verify_actual_surface_workflow.py", "rest_chart_frozen_workflow")
    qa, diag, addon, surface = workflow.load_dependencies()
    source_manifest = diag.source_manifest()
    disks_before = {str(path): qa.file_state(path) for path in (helper.INPUT, helper.INSTALL, helper.ARTIST)}
    started = time.perf_counter()
    report = {"diagnostic_collection_success": False, "formal_validation": False, "production_effect_accepted": False,
              "default_chart_repair_accepted": False, "matrix_guard_unchanged": 4e-5, "public_surface_guard_m": 5e-5,
              "script_sha256": own_sha, "pins_before": pins_before, "default_chart_stages": [],
              "scope": "Observe unchanged 9d7 constructor on private legacy clone and frozen a725 current-pose conversion at this saved input pose, not its earlier run60 pose",
              "warmup_limitation": "Same-graph wire/pose readbacks add evaluation work; rejection and primitive matrices are recorded, not solver-internal cause or timing acceptance"}
    args.output.mkdir()
    tx = None
    protection = None
    initial_inventory = None
    completed = False
    old_trace = sys.gettrace()
    require(old_trace is None, "existing Python tracer prevents specific observational hook")
    try:
        gate_args = argparse.Namespace(input=helper.INPUT.resolve(), install_report=helper.INSTALL.resolve(),
            expected_surface_sha=helper.SURFACE_SHA, expected_worker_sha=helper.WORKER_SHA)
        source_name = workflow.motion_input_gate(gate_args, report, qa, diag)
        addon.register()
        require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(helper.INPUT), load_ui=False, use_scripts=False), "exact input open failed")
        source, rig, record = qa.owned_source(source_name)
        record, rig, actual, cloth, neutral = workflow.motion_objects(source, qa, surface)
        reference = surface._object(record, "NEUTRAL_RIG", source)
        wires = [bpy.data.objects[name] for name in record["physics"]["surface"]["roles"]["NEUTRAL_WIRE"]]
        require(surface._neutral_manual_record(record["physics"]["surface"]) == surface.NEUTRAL_MANUAL_LEGACY, "fixed input must remain legacy")
        protection = qa.Protection()
        initial_inventory = id_inventory(current)
        inputs = surface._upgrade_inputs(bpy.context, source, rig, record, cloth)
        contract, bindings = surface._helper_contract(reference), helper.author_bindings(surface)
        cache_before = helper.cache_semantics(cloth, qa, surface)
        metres = bpy.context.scene.unit_settings.scale_length
        require(math.isfinite(metres) and metres > 0., "invalid scene units")
        report["units_to_metres"] = metres
        report["input_frame"] = [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe]
        tx = surface._Transaction(bpy.context, source)
        candidate = tx.copy(reference, "QA Default Neutral Rest Chart", bpy.context.scene.collection)
        surface._tag(candidate, source, record, "NEUTRAL_RIG")
        require(qa.rest_content(candidate) == qa.rest_content(reference), "copied default Rest changed")
        old_constraints = {item.as_pointer() for owner in [reference] + list(reference.pose.bones) for item in owner.constraints}
        require(all(item.as_pointer() not in old_constraints for owner in [candidate] + list(candidate.pose.bones)
                    for item in owner.constraints), "default clone shares native constraint storage")
        old_drivers = {item.as_pointer() for item in reference.animation_data.drivers}
        require(all(item.as_pointer() not in old_drivers for item in candidate.animation_data.drivers),
                "default clone shares native driver storage")
        for bone in candidate.pose.bones:
            for constraint in bone.constraints:
                if getattr(constraint, "target", None) == reference:
                    constraint.target = candidate
        copied_wires = []
        for chain, wire in zip(record["chains"], wires):
            copied = tx.copy(wire, "QA Default Neutral Wire", bpy.context.scene.collection)
            surface._tag(copied, source, record, "NEUTRAL_WIRE")
            copied.parent = candidate
            for modifier in copied.modifiers:
                modifier.object = candidate
            candidate.pose.bones[chain["manual"][-1]].constraints[0].target = copied
            copied_wires.append(copied)
        code = surface._fixed_neutral_manual.__code__
        require(Path(code.co_filename).resolve() == helper.REPOSITORY / "addons/character_designer/skirt_surface.py", "wrong hook code path")
        definition = next(node for node in ast.parse(Path(code.co_filename).read_text(encoding="utf-8")).body
                          if isinstance(node, ast.FunctionDef) and node.name == "_fixed_neutral_manual")
        before_line = next(node.lineno for node in ast.walk(definition) if isinstance(node, ast.For)
                           and ast.unparse(node.target) == "(_bone, spline)")
        after_line = next(node.lineno for node in ast.walk(definition) if isinstance(node, ast.Expr)
                         and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                         and node.value.func.id == "_require" and len(node.value.args) == 2
                         and isinstance(node.value.args[1], ast.Constant)
                         and "cannot be represented" in str(node.value.args[1].value))

        def trace(frame, event, _value):
            if event == "line" and frame.f_lineno in (before_line, after_line):
                local = frame.f_locals
                require(local["reference"] is candidate, "unexpected controlled-chart call")
                stage = "before_basis_assignment" if frame.f_lineno == before_line else "after_basis_assignment_before_unchanged_guard"
                graph = bpy.context.evaluated_depsgraph_get()
                bones = rows(candidate, local["desired"], local["bases"], graph, metres)
                report["default_chart_stages"].append({"stage": stage, "native_graph": graph.as_pointer(),
                    "bones": bones, "summary": summary(bones),
                    "wires": wire_rows(copied_wires, graph, diag, surface),
                    "object_world": plain(candidate.evaluated_get(graph).matrix_world)})
                if frame.f_lineno == after_line:
                    sys.settrace(None)
                    return None
            return trace

        def observer(frame, event, _value):
            return trace if event == "call" and frame.f_code is code else None

        sys.settrace(observer)
        try:
            surface._fixed_neutral_manual(bpy.context, candidate, copied_wires, record)
            report["unchanged_constructor_rejected"] = False
        except surface.SkirtSurfaceError as error:
            report["unchanged_constructor_rejected"] = True
            report["unchanged_constructor_rejection"] = str(error)
        finally:
            sys.settrace(old_trace)
        require([row["stage"] for row in report["default_chart_stages"]] ==
                ["before_basis_assignment", "after_basis_assignment_before_unchanged_guard"], "both controlled chart stages were not actually observed")
        # Capture with the frozen successful component's exact conversion helper;
        # its desired parent frames are all read before any private setter.
        graph = bpy.context.evaluated_depsgraph_get()
        marker = {}
        captured = {}

        def current_trace(frame, event, _value):
            if event == "return" and _value is not None:
                captured["desired"] = {name: value.copy() for name, value in frame.f_locals["desired"].items()}
                captured["bases"] = {name: value.copy() for name, value in frame.f_locals["bases"].items()}
            return current_trace

        def current_observer(frame, event, _value):
            return current_trace if event == "call" and frame.f_code is current.clone_fk.__code__ else None

        sys.settrace(current_observer)
        try:
            clone = current.clone_fk(reference, rig, record, bpy.context.scene, graph, tx.objects, tx.data, qa,
                                     argparse.Namespace(matrix=plain), marker)
        finally:
            sys.settrace(old_trace)
        require(set(captured) == {"desired", "bases"}, "current-pose helper's exact captured parent context missing")
        probe = tx.copy(neutral, "QA Current Pose Neutral FK Readback", bpy.context.scene.collection)
        surface._tag(probe, source, record, "NEUTRAL_SURFACE")
        probe.modifiers[0].object = clone
        clone.update_tag(); probe.update_tag()
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        desired, bases = captured["desired"], captured["bases"]
        original_points = diag.json_content(diag.mesh_snapshot(neutral, graph))["points"]
        clone_points = diag.json_content(diag.mesh_snapshot(probe, graph))["points"]
        require(len(original_points) == len(clone_points) == 800, "current-pose neutral surface count changed")
        current_bones = rows(clone, desired, bases, graph, metres)
        report["current_pose_comparison"] = {"frozen_helper_sha256": CURRENT_SHA, "marker": marker,
            "bones": current_bones, "summary": summary(current_bones),
            "H0_maximum_difference_m": max(math.dist(a, b)*metres for a, b in zip(original_points, clone_points)),
            "earlier_a725_run60_pose_recreated": False}
        completed = True
    except Exception:
        report["error"] = traceback.format_exc()
    finally:
        sys.settrace(old_trace)
        try:
            if tx is not None:
                tx.rollback()
                bpy.context.view_layer.update()
                report["private_ID_cleanup_exact"] = id_inventory(current) == initial_inventory
                report["original_inputs_reference_bindings_cache_exact"] = (
                    surface._upgrade_inputs(bpy.context, source, rig, qa.skirt.read_record(source), cloth) == inputs
                    and surface._helper_contract(reference) == contract and helper.author_bindings(surface) == bindings
                    and helper.cache_semantics(cloth, qa, surface) == cache_before)
            require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(helper.INPUT), load_ui=False, use_scripts=False), "exact input reload failed")
            report["final_raw_input_protection"] = protection.verify() if protection is not None else None
        except Exception:
            report["cleanup_error"] = traceback.format_exc()
        report["pins_after"] = {str(path): sha(path) for path in helper.PINS}
        report["pins_helpers_and_script_exact"] = (report["pins_after"] == pins_before and sha(Path(__file__)) == own_sha
            and sha(UPGRADE) == UPGRADE_SHA and sha(CURRENT) == CURRENT_SHA)
        report["disk_exact"] = {str(path): qa.file_state(path) for path in (helper.INPUT, helper.INSTALL, helper.ARTIST)} == disks_before
        report["canonical_inventory_exact"] = diag.source_manifest() == source_manifest
        report["elapsed_seconds"] = time.perf_counter()-started
        report["diagnostic_collection_success"] = (completed and "error" not in report and "cleanup_error" not in report
            and report.get("private_ID_cleanup_exact") is True and report.get("original_inputs_reference_bindings_cache_exact") is True
            and (report.get("final_raw_input_protection") or {}).get("success") is True and report["pins_helpers_and_script_exact"]
            and report["disk_exact"] and report["canonical_inventory_exact"])
        destination = args.output / "result/neutral_manual_rest_chart.json"
        destination.parent.mkdir()
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"diagnostic_collection_success": report["diagnostic_collection_success"], "report": str(destination)}), flush=True)
    return 0 if report["diagnostic_collection_success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
