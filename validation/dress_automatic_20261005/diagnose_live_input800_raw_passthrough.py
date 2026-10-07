"""DIAGNOSTICS ONLY: observe the frozen e939 first raw-channel rejection.

No bridge recipe, equality, tolerance, geometry or acceptance change. The exact
original sample_raw guard still throws after one small native RNA observation
is written. Only a fresh private QA output is permitted; Root owns native runs.
Unsupported observations are Unknown, never inferred driver evaluations.
"""
import ast
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CORE = HERE / "verify_live_input800_main_manual_bridge.py"
CORE_SHA = "e93948a4a8cf958990ac9271e3fa92d8801f055e230b9b0462dbe16310b2f7c5"
FAILED = HERE / "actual_live_input800_main_manual_bridge_51_20261006_174455_874/result/input800_reproduction.json"
FAILED_SHA = "bafd861a5d0e34873e49abdf2c698cd576ba0bf37253862094a8c7b95ce998e5"
TARGET_MESSAGE = "native evaluated raw passthrough differs"
FIELDS = ("rotation_mode", "location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale")


def require(condition, message):
    if not condition:
        raise RuntimeError("raw diagnostic: " + message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def load_core():
    require(sha(CORE) == CORE_SHA and sha(FAILED) == FAILED_SHA, "immutable bridge/failure evidence changed")
    spec = importlib.util.spec_from_file_location("raw_diagnostic_frozen_e939", CORE)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core


def primitive(value):
    """Copy observations immediately; nonfinite native numbers stay explicit."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {"status": "Unknown", "nonfinite": repr(value)}
    if isinstance(value, dict):
        require(all(isinstance(key, str) for key in value), "observation has non-string keys")
        return {key: primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)) or type(value).__module__ == "mathutils":
        return [primitive(item) for item in value]
    if hasattr(value, "as_pointer"):
        return {"name": str(value.name), "pointer": int(value.as_pointer())}
    raise TypeError("Unsupported observation type: " + type(value).__name__)


def observe(callback):
    try:
        return {"status": "Measured", "value": primitive(callback())}
    except Exception as error:
        return {"status": "Unknown", "error": type(error).__name__ + ": " + str(error)}


def first_difference(original, copied):
    for field in FIELDS:
        if field not in original or field not in copied:
            return {"field": field, "component": None, "status": "Unknown", "reason": "missing channel"}
        left, right = original[field], copied[field]
        if left != right:
            if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
                if len(left) != len(right):
                    return {"field": field, "component": None, "main": primitive(left), "private": primitive(right), "reason": "array length differs"}
                for index, (a, b) in enumerate(zip(left, right)):
                    if a != b:
                        return {"field": field, "component": index, "main": primitive(a), "private": primitive(b), "reason": "exact native values differ"}
            return {"field": field, "component": None, "main": primitive(left), "private": primitive(right), "reason": "exact native values differ"}
    return None


def property_metadata(owner, field):
    prop = owner.bl_rna.properties[field]
    return {key: observe(lambda key=key: getattr(prop, key))
            for key in ("type", "subtype", "is_readonly", "is_animatable", "is_array", "array_length")}


def bone_observation(obj, name, base):
    bone = obj.pose.bones[name]
    rest = obj.data.bones[name]
    return {"object": observe(lambda: obj), "bone_pointer": observe(lambda: int(bone.as_pointer())),
            "channels": observe(lambda: base.channels(bone)),
            "matrix_basis": observe(lambda: bone.matrix_basis), "matrix": observe(lambda: bone.matrix),
            "rest_matrix_local": observe(lambda: rest.matrix_local), "use_connect": observe(lambda: bool(rest.use_connect)),
            "parent": observe(lambda: None if rest.parent is None else rest.parent.name),
            "raw_RNA_properties": {field: observe(lambda field=field: property_metadata(bone, field)) for field in FIELDS},
            "manual_constraints": observe(lambda: [{"name": item.name, "type": item.type,
                "mix_mode": getattr(item, "mix_mode", None), "mute": bool(item.mute),
                "influence": float(item.influence), "pointer": int(item.as_pointer())} for item in bone.constraints])}


def resolve_scalar(obj, path, index=None):
    value = obj.path_resolve(path)
    return value if index is None else value[index]


def generated_driver_observations(core, rig, input_rig, name, graph):
    expected = [row for row in core._STATE["expected_drivers"]
                if row["output"].startswith(input_rig.pose.bones[name].path_from_id() + ".")]
    curves = list(input_rig.animation_data.drivers)
    rows = []
    for row in expected:
        matches = [curve for curve in curves if curve.data_path == row["output"] and curve.array_index == row["index"]]
        item = {"expected": primitive(row), "matching_curve_count": len(matches),
                "main_target_raw": observe(lambda row=row: resolve_scalar(rig, row["target"])),
                "main_target_evaluated": observe(lambda row=row: resolve_scalar(rig.evaluated_get(graph), row["target"])),
                "private_output_raw": observe(lambda row=row: resolve_scalar(input_rig, row["output"], row["index"])
                    if row["output"].rsplit(".", 1)[1] in core.RAW_FIELDS else resolve_scalar(input_rig, row["output"])),
                "private_output_evaluated": observe(lambda row=row: resolve_scalar(input_rig.evaluated_get(graph), row["output"], row["index"])
                    if row["output"].rsplit(".", 1)[1] in core.RAW_FIELDS else resolve_scalar(input_rig.evaluated_get(graph), row["output"]))}
        if len(matches) == 1:
            curve, driver = matches[0], matches[0].driver
            item["FCurve"] = {field: observe(lambda field=field: getattr(curve, field))
                              for field in ("data_path", "array_index", "mute", "is_valid")}
            item["driver"] = {field: observe(lambda field=field: getattr(driver, field))
                              for field in ("type", "expression", "use_self", "is_valid", "is_simple_expression")}
            item["variables"] = observe(lambda: [{"name": variable.name, "type": variable.type,
                "targets": [{"id": target.id, "id_type": target.id_type, "data_path": target.data_path}
                            for target in variable.targets]} for variable in driver.variables])
        else:
            item["driver"] = {"status": "Unknown", "reason": "not one exact generated driver"}
        rows.append(item)
    return {"expected_count": len(expected), "all_19_expected_observed": len(expected) == 19,
            "scope": "Native RNA status and path_resolve values; FCurve.evaluate is deliberately not treated as driver output.", "rows": rows}


def gather(core, local):
    name, rig, input_rig, graph, base = (local[key] for key in ("name", "rig", "input_rig", "graph", "base"))
    original, copied = local["original"], local["copied"]
    return {"bone": name, "first_exact_channel_difference": first_difference(original, copied),
            "already_compared_native_channels": {"main": primitive(original), "private": primitive(copied)},
            "all_main_raw_components_finite": all(math.isfinite(value) for field in core.RAW_FIELDS for value in original[field]),
            "rotation_mode_receipt": observe(lambda: core._STATE["rotation_modes"][name]),
            "main_writable_RNA": observe(lambda: bone_observation(rig, name, base)),
            "main_evaluated_RNA": observe(lambda: bone_observation(rig.evaluated_get(graph), name, base)),
            "private_writable_RNA": observe(lambda: bone_observation(input_rig, name, base)),
            "private_evaluated_RNA": observe(lambda: bone_observation(input_rig.evaluated_get(graph), name, base)),
            "generated_drivers": observe(lambda: generated_driver_observations(core, rig, input_rig, name, graph))}


def make_observer(core, callback):
    original_need = core.need
    def observing_need(condition, message):
        if not condition and message == TARGET_MESSAGE:
            frame = inspect.currentframe().f_back
            try:
                if frame.f_code is core.sample_raw.__code__:
                    # No RNA references leave this observation callback.
                    callback(dict(frame.f_locals))
            except Exception:
                # Observation failures cannot replace or swallow the frozen guard.
                pass
            finally:
                del frame
        return original_need(condition, message)
    return observing_need


def pure_checks(core):
    from types import SimpleNamespace as NS
    base_checks = core.pure_checks()
    text = Path(__file__).read_text(encoding="utf-8")
    ast.parse(text); compile(text, str(Path(__file__)), "exec")
    baseline = {"rotation_mode": "QUATERNION", "location": [0., 0., 0.], "rotation_euler": [0., 0., 0.],
                "rotation_quaternion": [1., 0., 0., 0.], "rotation_axis_angle": [0., 0., 1., 0.], "scale": [1., 1., 1.]}
    changed = {key: list(value) if isinstance(value, list) else value for key, value in baseline.items()}
    changed["rotation_axis_angle"][2] = 0.
    difference = first_difference(baseline, changed)
    require(difference["field"] == "rotation_axis_angle" and difference["component"] == 2
            and difference["main"] == 1. and difference["private"] == 0., "first exact field/component control")
    require(first_difference(baseline, baseline) is None, "equal channels must not manufacture mismatch")
    saved_need, saved_state = core.need, dict(core._STATE)
    receipts = []
    try:
        core._STATE["rotation_modes"] = {"DEF": "QUATERNION"}
        left, right = NS(rotation_mode="QUATERNION", channels=baseline), NS(rotation_mode="QUATERNION", channels=changed)
        def obj(bone):
            value = NS(pose=NS(bones={"DEF": bone})); value.evaluated_get = lambda graph: value
            return value
        core.need = make_observer(core, lambda local: receipts.append({"bone": local["name"],
            "difference": first_difference(local["original"], local["copied"])}))
        try:
            core.sample_raw(obj(left), obj(right), {"DEF"}, object(), NS(channels=lambda bone: bone.channels))
        except RuntimeError as error:
            require(str(error) == "LIVE bridge: " + TARGET_MESSAGE, "original rejection unchanged")
        else:
            raise RuntimeError("frozen raw guard did not reject")
        require(len(receipts) == 1 and receipts[0]["bone"] == "DEF" and receipts[0]["difference"] == difference,
                "actual sample_raw caller identity/locals must be observed before throw")
        core.need = saved_need
        core.need = make_observer(core, lambda local: (_ for _ in ()).throw(RuntimeError("diagnostic failure")))
        try:
            core.sample_raw(obj(left), obj(right), {"DEF"}, object(), NS(channels=lambda bone: bone.channels))
        except RuntimeError as error:
            require(str(error) == "LIVE bridge: " + TARGET_MESSAGE, "observer exception swallowed original rejection")
        else:
            raise RuntimeError("observer exception manufactured success")
        count = len(receipts)
        try:
            core.need(False, "unrelated guard")
        except RuntimeError as error:
            require(str(error) == "LIVE bridge: unrelated guard" and len(receipts) == count, "unrelated guard changed")
        require(observe(lambda: float("nan"))["value"]["status"] == "Unknown", "nonfinite is not serialized as measured finite value")
    finally:
        core.need = saved_need; core._STATE.clear(); core._STATE.update(saved_state)
    return {"passed": True, "diagnostic_controls": 6, "frozen_bridge_pure_checks": base_checks,
            "native_run": False, "acceptance_changed": False}


def main(args, core):
    if args.pure_checks:
        print(json.dumps(pure_checks(core), ensure_ascii=False)); return 0
    wrapper_sha = sha(Path(__file__))
    report_holder = {}; original_prepare, original_capture, original_need = core.prepared_namespace, core.capture_program, core.need
    observed = []
    def save_observation(local):
        if observed:
            return
        row = {"diagnostics_only": True, "native_guard_still_rejects": True, "accepted": False,
               "frozen_bridge": {"path": str(CORE), "sha256": CORE_SHA},
               "wrapper": {"path": str(Path(__file__)), "sha256": wrapper_sha},
               "original_failure": {"path": str(FAILED), "sha256": FAILED_SHA},
               "guard_message": TARGET_MESSAGE, "observation_complete": False}
        observed.append(row)
        try:
            row.update(gather(core, local)); row["observation_complete"] = True
        except Exception as error:
            row["diagnostic_error"] = type(error).__name__ + ": " + str(error)
        sidecar = args.output / "first_live_raw_mismatch.json"
        sidecar.write_text(json.dumps(primitive(row), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        report = report_holder.get("report")
        if report is not None:
            report["first_live_raw_mismatch"] = row
            report["first_live_raw_mismatch_file"] = {"path": str(sidecar), "sha256": sha(sidecar)}
            # The sidecar is already on disk before the unchanged original guard.
            # The frozen native finally writes this same row with all protections.
    def capture(*values):
        source, rig, cloth, home, qa, surface, same, actual, report = values
        report_holder["report"] = report
        report["raw_diagnostic_wrapper"] = {"path": str(Path(__file__)), "sha256": wrapper_sha,
            "core_sha256": CORE_SHA, "recipe_and_guards_unchanged": True, "acceptance_changed": False}
        return original_capture(*values)
    def prepare(base):
        namespace, edits = original_prepare(base)
        namespace["PINS"] = dict(namespace["PINS"])
        namespace["PINS"].update({CORE: CORE_SHA, FAILED: FAILED_SHA, Path(__file__): wrapper_sha})
        return namespace, edits
    core.prepared_namespace, core.capture_program, core.need = prepare, capture, make_observer(core, save_observation)
    try:
        return core.main(args)
    finally:
        core.prepared_namespace, core.capture_program, core.need = original_prepare, original_capture, original_need


if __name__ == "__main__":
    frozen = load_core()
    raise SystemExit(main(frozen.arguments(), frozen))
