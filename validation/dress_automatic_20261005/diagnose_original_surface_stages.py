"""Private observational run60; preparation is not native or effect acceptance.

Run only in a new --background --factory-startup Blender 5.1 child, with the
frozen workflow's normal --stage motion / --cases run / --frames 60 arguments.
The unchanged workflow owns all opening, native cache, failure and reload gates.
Extra native readbacks and the independent S-prefix probe can warm evaluation;
stage differences localize observations, not a proven cause or a timing result.
"""
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy

HERE = Path(__file__).resolve().parent
REPOSITORY = Path(r"D:\MyRepository\Blender-addons-by-Randy")
INPUT = HERE / "actual_install_51_20261006_031045_111/scenes/Cosha_Dress_QA_surface_install.blend"
INSTALL = INPUT.parent.parent / "result/workflow_install.json"
PINS = {
    INPUT: "7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f",
    INSTALL: "a2157ba399bfe32cc28401847c2556f776761fd607eaa3ba7ea23b61aaec6a32",
    HERE / "verify_actual_surface_workflow.py": "2e8d82bbbde00604bf3f62bc17cbcb31244ed87290e083ebb17b25f4b9216140",
    REPOSITORY / "addons/character_designer/skirt_surface.py": "3905846f751659a6970cc80b70118201eaea068a657c69cd764b789e893b127b",
    REPOSITORY / "addons/character_designer/unity_export_worker.py": "069fb0f21b02e36a23dd02b1978d2a917c2873f290fc3331cdf0d55e877ce5bc",
    HERE / "verify_actual_original_refinement.py": "8f03f687853841a5de1199d3ae1762bc5da160df1d46ac9eb9d8224ce6b71e67",
}
STAGES = ("active_action_baseline", "action_none_first_native_update",
          "body_bake_sources_completed_before_dress_enter", "public_original_completed")


def require(value, message):
    if not value:
        raise RuntimeError("Original stage diagnostic: " + message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matrix(value):
    result = [[float(x) for x in row] for row in value]
    require(all(math.isfinite(x) for row in result for x in row), "nonfinite native matrix")
    return result


def native_mesh(obj, graph):
    posed = obj.evaluated_get(graph)
    mesh = posed.to_mesh(preserve_all_data_layers=False, depsgraph=graph)
    try:
        require(all(vertex.index == i for i, vertex in enumerate(mesh.vertices)), "native vertex indices are not contiguous")
        points = [[float(x) for x in posed.matrix_world @ vertex.co] for vertex in mesh.vertices]
        require(points and all(math.isfinite(x) for point in points for x in point), "nonfinite/empty native mesh")
        return {"object": obj.name, "object_pointer": obj.as_pointer(), "data_pointer": obj.data.as_pointer(),
                "points": points, "count": len(points), "native_vertex_index_order": "exact_contiguous_0_to_count_minus_1",
                "points_sha256": hashlib.sha256(json.dumps(points, separators=(",", ":")).encode()).hexdigest()}
    finally:
        posed.to_mesh_clear()


def delta(old, new, metres):
    require(len(old) == len(new), "stage point identity/count changed")
    index, distance = max(enumerate(math.dist(a, b) for a, b in zip(old, new)), key=lambda item: item[1])
    return {"maximum_m": distance * metres, "native_vertex_index": index,
            "before_world": old[index], "after_world": new[index],
            "delta_world": [b-a for a, b in zip(old[index], new[index])]}


def pose_row(obj, names, graph):
    posed = obj.evaluated_get(graph)
    return {"object": obj.name, "object_pointer": obj.as_pointer(),
            "original_matrix_world": matrix(obj.matrix_world), "evaluated_matrix_world": matrix(posed.matrix_world),
            "bones": {name: {"original_matrix": matrix(obj.pose.bones[name].matrix),
                              "original_matrix_basis": matrix(obj.pose.bones[name].matrix_basis),
                              "evaluated_matrix": matrix(posed.pose.bones[name].matrix),
                              "evaluated_matrix_basis": matrix(posed.pose.bones[name].matrix_basis),
                              "evaluated_world_matrix": matrix(posed.matrix_world @ posed.pose.bones[name].matrix)}
                      for name in names}}


def matrix_deltas(old, new):
    result = {}
    for rig_name, row in new.items():
        earlier = old[rig_name]
        for field in ("original_matrix_world", "evaluated_matrix_world"):
            result[rig_name + "/" + field] = max(abs(a-b) for x, y in zip(earlier[field], row[field]) for a, b in zip(x, y))
        for name, bone in row["bones"].items():
            for field, values in bone.items():
                result[rig_name + "/" + name + "/" + field] = max(
                    abs(a-b) for x, y in zip(earlier["bones"][name][field], values) for a, b in zip(x, y))
    return result


def observed_roundtrip(original, workflow, diagnostic, source, rig, actual, cloth, neutral, result, qa, surface, metres):
    from character_designer import body_original_mode as body
    record = qa.skirt.read_record(source)
    reference = bpy.data.objects[record["physics"]["surface"]["roles"]["NEUTRAL_RIG"][0]]
    body_mesh = bpy.context.scene.character_designer_setup.body
    require(body_mesh is not None and body_mesh.name == result["body"]["object"], "registered Body identity changed")
    names = list(dict.fromkeys(surface._ancestors(rig, record) + [record["controls"]["waist"]]))
    require(all(name in reference.pose.bones for name in names), "neutral upstream counterpart missing")
    overlay = surface._overlay(source, record)
    prefix = [modifier.name for modifier in list(source.modifiers)[:list(source.modifiers).index(overlay)]]
    require(prefix and all(modifier.type != "NODES" for modifier in list(source.modifiers)[:len(prefix)]), "S is not a native pre-overlay prefix")
    probe = None
    old_bake, old_switch, old_trace = body._bake_sources, qa.public_switch, sys.gettrace()
    require(old_trace is None, "existing Python tracer prevents exact observational hook")
    activate = qa.skirt._activate
    require(Path(activate.__code__.co_filename).resolve() ==
            (REPOSITORY / "addons/character_designer/skirt_rig.py").resolve(), "activation hook is not canonical")
    definition = next(node for node in ast.parse(Path(activate.__code__.co_filename).read_text(encoding="utf-8")).body
                      if isinstance(node, ast.FunctionDef) and node.name == activate.__name__)
    require(ast.unparse(definition.body[0]) == "context.view_layer.update()", "native activation first-update ABI changed")
    after_update_line = definition.body[1].lineno
    samples = diagnostic["stages"]
    diagnostic["prefix_modifiers"] = prefix
    diagnostic["upstream_bones"] = names
    diagnostic["activation_hook"] = {"file": activate.__code__.co_filename,
                                      "source_sha256": sha(Path(activate.__code__.co_filename)),
                                      "line": after_update_line, "policy": "specific native code object; only its first update in this roundtrip; no replacement activation"}
    diagnostic["geometry_guard_m"] = qa.geometry_guard(metres)
    require(diagnostic["geometry_guard_m"] == 5e-5, "the existing 50 micrometre guard changed")

    def sample(label):
        require(label == STAGES[len(samples)], "observed stages are missing, duplicated or out of order")
        began = time.perf_counter()
        context, scene = bpy.context, bpy.context.scene
        graph = context.evaluated_depsgraph_get()  # No explicit update or frame_set here.
        meshes = {key: native_mesh(obj, graph) for key, obj in
                  (("O", source), ("S", probe), ("C", actual), ("H0", neutral), ("Body", body_mesh))}
        require([meshes[key]["count"] for key in ("O", "S", "C", "H0")] == [3040, 800, 800, 800], "actual surface layout changed")
        require(meshes["Body"]["count"] <= 100000, "actual Body readback exceeds inherited budget")
        poses = {"main": pose_row(rig, names, graph), "neutral": pose_row(reference, names, graph)}
        action = rig.animation_data.action if rig.animation_data else None
        row = {"label": label, "frame": scene.frame_current, "subframe": scene.frame_subframe,
               "graph_pointer": graph.as_pointer(), "graph_strategy": "one current graph for all five meshes and evaluated matrices; no added frame_set/update",
               "action": action.name if action else None, "action_pointer": action.as_pointer() if action else None,
               "public_original_active": body.active(rig), "native_cache": qa.cache_state(cloth),
               "cache_filepath": cloth.point_cache.filepath, "baked_range": qa.skirt.read_record(source)["physics"].get("baked_range"),
               "meshes": meshes, "poses": poses, "quality": {"finite": True, "counts_exact": True, "readback_seconds": time.perf_counter()-began}}
        require(row["native_cache"]["is_baked"] and row["baked_range"] == [1, 60], "inherited cache is not sealed run60")
        if samples:
            require((row["frame"], row["subframe"]) == (samples[0]["frame"], samples[0]["subframe"]), "observation changed frame")
            for comparison, earlier in (("from_active_baseline", samples[0]), ("from_previous_stage", samples[-1])):
                row[comparison] = {"meshes": {key: delta(earlier["meshes"][key]["points"], value["points"], metres)
                                               for key, value in meshes.items()},
                                   "matrix_element_errors": matrix_deltas(earlier["poses"], poses),
                                   "native_cache_state_exact": earlier["native_cache"] == row["native_cache"]}
        samples.append(row)
        print(json.dumps({"original_stage": label, "frame": row["frame"], "readback_seconds": row["quality"]["readback_seconds"]}), flush=True)

    def local_trace(frame, event, _arg):
        if (event == "line" and frame.f_lineno == after_update_line and len(samples) == 1
                and frame.f_locals.get("obj") is rig and frame.f_locals.get("mode") == "POSE"
                and rig.animation_data.action is None):
            sample(STAGES[1])
            sys.settrace(None)  # No tracing of the later transfer, Controls cleanup or other workflow code.
            diagnostic["activation_trace_stopped_after_single_observation"] = True
            return None
        return local_trace

    def observer(frame, event, _arg):
        return local_trace if event == "call" and frame.f_code is activate.__code__ else None

    def bake(*args, **kwargs):
        value = old_bake(*args, **kwargs)
        if len(samples) == 2 and args[1] is rig:
            sample(STAGES[2])
        return value

    def public_switch(*args, **kwargs):
        value = old_switch(*args, **kwargs)
        if kwargs.get("action") == "ORIGINAL" and body.active(rig):
            sample(STAGES[3])
        return value

    try:
        probe = workflow.motion_probe(source, bpy.context.scene, "Observed Original Prefix", lambda item: item.name in prefix)
        probe_ids = {"object": probe.name, "mesh": probe.data.name,
                     "keys": probe.data.shape_keys.name if probe.data.shape_keys else None}
        require(not any(key in probe for key in (qa.skirt.RECORD_KEY, qa.skirt.RIG_KEY, qa.skirt.SOURCE_KEY)),
                "temporary S prefix retained an artist Dress registration")
        require(rig.animation_data.action is not None and rig.animation_data.action.get("CD_QA_SyntheticInput") is True,
                "active baseline is not the inherited private synthetic Action")
        sample(STAGES[0])
        body._bake_sources, qa.public_switch = bake, public_switch
        sys.settrace(observer)
        return original(source, rig, actual, cloth, neutral, result, qa, surface, metres)
    finally:
        sys.settrace(old_trace)
        body._bake_sources, qa.public_switch = old_bake, old_switch
        diagnostic["wrappers_restored"] = body._bake_sources is old_bake and qa.public_switch is old_switch and sys.gettrace() is old_trace
        if probe is not None:
            require(bpy.data.objects.get(probe_ids["object"]) is probe and probe.data.name == probe_ids["mesh"], "temporary prefix probe identity changed")
            workflow.remove_motion_probe(probe)
            diagnostic["temporary_prefix_probe_removed"] = (
                bpy.data.objects.get(probe_ids["object"]) is None and bpy.data.meshes.get(probe_ids["mesh"]) is None
                and (probe_ids["keys"] is None or bpy.data.shape_keys.get(probe_ids["keys"]) is None))
            require(diagnostic["temporary_prefix_probe_removed"], "temporary prefix probe was not completely removed")


def main():
    require(bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath,
            "use an empty isolated background factory-startup child")
    require(bpy.app.version[:2] == (5, 1), "this diagnostic requires Blender 5.1")
    before = {str(path): sha(path) for path in PINS}
    require(all(before[str(path)] == expected for path, expected in PINS.items()), "an exact frozen input/source pin differs")
    own_sha = sha(Path(__file__))
    spec = importlib.util.spec_from_file_location("observed_frozen_actual_surface_workflow", HERE / "verify_actual_surface_workflow.py")
    workflow = importlib.util.module_from_spec(spec)
    require(spec.name not in sys.modules, "the frozen workflow diagnostic module is already loaded")
    sys.modules[spec.name] = workflow  # The unchanged workflow passes its module to the refinement helper.
    spec.loader.exec_module(workflow)
    args = workflow.arguments()
    require(args.stage == "motion" and args.cases == ["run"] and args.frames == 60, "reuse precisely the unchanged single-case motion/run60")
    require(args.input == INPUT.resolve() and args.install_report == INSTALL.resolve(), "use the exact installed QA/report")
    require(args.expected_surface_sha == PINS[REPOSITORY / "addons/character_designer/skirt_surface.py"]
            and args.expected_worker_sha == PINS[REPOSITORY / "addons/character_designer/unity_export_worker.py"], "runtime hashes differ")
    destination = args.output / "result/original_surface_stages.json"
    require(not args.output.exists() and not destination.exists(), "use a fresh unique diagnostic run directory")
    report = {"diagnostic_only": True, "formal_validation": False, "production_effect_accepted": False,
              "source_preparation_alone_is_not_execution": True, "script_sha256": own_sha, "pins_before": before,
              "stages": [], "instrumentation_collection_complete": False,
              "readback_limitation": "Extra evaluated readbacks and an independent S-prefix mesh may affect warmup/evaluation timing. This observational run does not by itself prove cause, a speed change, or formal acceptance.",
              "cache_policy": "No new diagnostic cache; unchanged workflow owns its unique candidate/native run60 cache and cleanup gates."}
    original = workflow.original_roundtrip
    workflow.original_roundtrip = lambda *values: observed_roundtrip(original, workflow, report, *values)
    exit_code = 2
    try:
        exit_code = workflow.main(args)  # Its exception handling, failure checks and exact reload gates are unchanged.
    except Exception:
        report["diagnostic_error"] = traceback.format_exc()
        raise
    finally:
        workflow.original_roundtrip = original
        report["workflow_exit_code"] = exit_code
        report["pins_after"] = {str(path): sha(path) for path in PINS}
        report["pins_and_script_exact"] = report["pins_after"] == before and sha(Path(__file__)) == own_sha
        report["workflow_wrapper_restored"] = workflow.original_roundtrip is original
        native_report = args.output / "result/workflow_motion.json"
        if native_report.is_file():
            frozen = json.loads(native_report.read_text(encoding="utf-8"))
            report["inherited_final_gates"] = {"workflow_success": frozen.get("success") is True,
                "original_raw_protection": frozen.get("protected_original_after", {}).get("success") is True,
                "artist_disk_exact": frozen.get("artist_disk_exact") is True,
                "canonical_and_frozen_code_exact": frozen.get("canonical_and_frozen_code_exact") is True,
                "workflow_report": str(native_report), "workflow_report_sha256": sha(native_report)}
            case_report = args.output / "cases/run/motion_case.json"
            case = json.loads(case_report.read_text(encoding="utf-8")) if case_report.is_file() else {}
            report["inherited_final_gates"]["case_final_input_protection"] = case.get("final_input_asset_protection", {}).get("success") is True
            report["inherited_final_gates"]["reload_and_probe_cleanup_no_error"] = (
                "final_reload_error" not in case and "probe_cleanup_error" not in case)
            report["inherited_failure"] = case.get("error") or frozen.get("error")
            report["instrumentation_collection_complete"] = (
                [item["label"] for item in report["stages"]] == list(STAGES)
                and all(report["inherited_final_gates"].get(key) is True for key in
                        ("original_raw_protection", "artist_disk_exact", "canonical_and_frozen_code_exact", "case_final_input_protection", "reload_and_probe_cleanup_no_error"))
                and report["pins_and_script_exact"] and report.get("wrappers_restored") is True
                and report.get("temporary_prefix_probe_removed") is True and report["workflow_wrapper_restored"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    require(report["pins_and_script_exact"] and report["instrumentation_collection_complete"], "observational collection/protection is incomplete; inspect failure report")
    return exit_code  # Preserve failed public Original's exit 2, rather than convert a diagnosis to PASS.


if __name__ == "__main__":
    raise SystemExit(main())
