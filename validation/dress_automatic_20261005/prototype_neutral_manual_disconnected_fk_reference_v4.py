"""Private default-chart component with an explicit connectivity exception.

Only this disposable reference's Manual bones lose use_connect. Their parent,
Rest geometry and all other flags, and the entire Main Rig, stay exact. The
unchanged 9d7 default-chart convert/set/4e-5 guard is copied into a private
namespace. Native RNA is re-resolved from primitive pre-edit receipts, including
exceptional restoration; canonical code and the unrun 1869 are never patched.
V4 preserves the copied parent/Hook chart and writes clone-before/conversion
geometry receipts before calling each unchanged 50um/C-exact guard.
One current-pose H0/O comparison uses the original 50um/C-exact gate. No
run60, public Original, bake, save, production schema or artistic acceptance.
"""
import argparse
import ast
import copy
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy

HERE = Path(__file__).resolve().parent
DIAGNOSTIC = HERE / "diagnose_neutral_manual_rest_chart_v2.py"
DIAGNOSTIC_SHA = "7774f54d145de697a372e1e9ebfb3a428b25e85fe4543090b626d1ea032d9b18"
UPGRADE = HERE / "verify_neutral_manual_reference_upgrade.py"
UPGRADE_SHA = "bfa061a5ac95da758ecd5d42dcc8187ff5316b604439a31298bae1a36358ec76"
PREVIOUS = HERE / "prototype_neutral_manual_disconnected_fk_reference_v2.py"
PREVIOUS_SHA = "21f38ab00a1e4832e256f76b645b6e6b44b8a2ac74ac084cafa93d962886481a"
FAILED_V3 = HERE / "prototype_neutral_manual_disconnected_fk_reference_v3.py"
FAILED_V3_SHA = "e145deebc4102416aa4c5c404bcc661148a1d5679694b9e7dbdada4a5f647b8a"


def require(condition, message):
    if not condition:
        raise RuntimeError("Disconnected neutral component: " + message)


def derived_rest_equal(before, after, manual):
    expected = copy.deepcopy(before)
    require(set(manual) <= set(expected), "unexpected Manual connectivity inventory")
    for name in manual:
        expected[name]["connected"] = False
    return expected == after


def pose_storage(reference):
    return {bone.name: [bone.as_pointer(), [item.as_pointer() for item in bone.constraints]] for bone in reference.pose.bones}


def native_receipts(reference, mutes, drivers, splines):
    """Record names/types/values while every pre-edit RNA reference is valid."""
    owners = {item.as_pointer(): {"owner": owner.name if owner is not reference else None,
                                 "name": item.name, "type": item.type}
              for owner in [reference] + list(reference.pose.bones) for item in owner.constraints}
    require(len(owners) == len(mutes), "pre-edit constraint owner inventory differs")
    constraints = [dict(owners[item.as_pointer()], mute=bool(mute)) for item, mute in mutes]
    curves = [{"path": curve.data_path, "index": curve.array_index, "mute": bool(mute)} for curve, mute in drivers]
    require(len({(item["path"], item["index"]) for item in curves}) == len(curves), "ambiguous driver identity")
    solvers = [{"owner": bone.name, "name": item.name, "type": item.type} for bone, item in splines]
    require(all(item["type"] == "SPLINE_IK" for item in solvers), "unexpected private solver type")
    return {"constraints": constraints, "drivers": curves, "splines": solvers}


def current_constraint(reference, receipt):
    owner = reference if receipt["owner"] is None else reference.pose.bones.get(receipt["owner"])
    require(owner is not None, "missing current constraint owner: " + str(receipt["owner"]))
    found = [item for item in owner.constraints if item.name == receipt["name"]]
    require(len(found) == 1 and found[0].type == receipt["type"], "missing/ambiguous/current constraint type differs: " + str(receipt))
    return owner, found[0]


def current_driver(reference, receipt):
    found = [curve for curve in reference.animation_data.drivers
             if curve.data_path == receipt["path"] and curve.array_index == receipt["index"]] if reference.animation_data else []
    require(len(found) == 1, "missing/ambiguous current driver identity: " + str(receipt))
    return found[0]


def rebind_native(reference, receipts):
    """Normal post-edit use has only freshly resolved RNA, never old wrappers."""
    mutes = [(current_constraint(reference, row)[1], row["mute"]) for row in receipts["constraints"]]
    drivers = [(current_driver(reference, row), row["mute"]) for row in receipts["drivers"]]
    splines = [current_constraint(reference, row) for row in receipts["splines"]]
    return mutes, drivers, splines


def restore_constructor(context, reference, parent, channels, succeeded, bases, receipts, surface, marker):
    """Attempt every restore by current identity, then reject any missing item."""
    errors = []
    attempts = {"Object_mode": 0, "parent_fields": 0, "channel_fields": 0, "constraint_mutes": 0, "driver_mutes": 0}

    def attempt(label, callback):
        try:
            callback()
        except Exception as error:
            errors.append(label + ": " + type(error).__name__ + ": " + str(error))

    if reference.mode != "OBJECT":
        attempts["Object_mode"] += 1
        attempt("return private reference to Object mode", lambda: surface.skirt._activate(context, reference, "OBJECT"))
        if reference.mode != "OBJECT":
            errors.append("private reference still not in Object mode")
    for field, value in zip(("parent", "parent_type", "parent_bone", "matrix_parent_inverse", "matrix_basis"), parent):
        attempts["parent_fields"] += 1
        attempt("parent/" + field, lambda field=field, value=value: setattr(reference, field, value))
    for name, fields in channels.items():
        if not succeeded or name not in bases:
            for field, value in fields.items():
                attempts["channel_fields"] += 1
                def channel(name=name, field=field, value=value):
                    bone = reference.pose.bones.get(name)
                    require(bone is not None, "missing current Pose channel owner: " + name)
                    setattr(bone, field, value)
                attempt("channel/" + name + "/" + field, channel)
    for row in receipts["constraints"]:
        attempts["constraint_mutes"] += 1
        def constraint(row=row):
            current_constraint(reference, row)[1].mute = row["mute"]
        attempt("constraint/" + str(row["owner"]) + "/" + row["name"], constraint)
    for row in receipts["drivers"]:
        attempts["driver_mutes"] += 1
        def driver(row=row):
            current_driver(reference, row).mute = row["mute"]
        attempt("driver/" + row["path"] + "/" + str(row["index"]), driver)
    marker["current_RNA_restore"] = {"attempts": attempts, "errors": errors,
                                     "primitive_identity_receipts": True, "old_RNA_never_used": True}
    require(not errors, "current-identity restoration incomplete: " + "; ".join(errors))


def remove_saved_splines(reference, receipts):
    errors = []
    for row in receipts["splines"]:
        try:
            owner, item = current_constraint(reference, row)
            owner.constraints.remove(item)
        except Exception as error:
            errors.append(str(row) + ": " + type(error).__name__ + ": " + str(error))
    require(not errors, "private solver removal incomplete: " + "; ".join(errors))


def disconnect_owned(context, reference, manual, surface, marker):
    before = surface._rest(reference, reference.data.bones.keys())
    parents = {bone.name: bone.parent.name if bone.parent else None for bone in reference.data.bones}
    storage = pose_storage(reference)
    driver_storage = [item.as_pointer() for item in reference.animation_data.drivers]
    state = surface.skirt._context_state(context)
    marker["connectivity_exception"] = {"version": 1, "scope": "OWNED_NEUTRAL_MANUAL_ONLY",
        "reference_only_manual_use_connect_false": True,
        "manual_bones": list(manual), "before": {name: before[name]["connected"] for name in manual},
        "object_Bone_RNA_readonly": {name: reference.data.bones[name].bl_rna.properties["use_connect"].is_readonly for name in manual},
        "setter": "Private owned EditBone.use_connect=False; no head/tail/roll/parent/weight write"}
    try:
        surface.skirt._activate(context, reference, "EDIT")
        require(reference.mode == "EDIT" and context.view_layer.objects.active is reference, "private EditBone context differs")
        for name in manual:
            reference.data.edit_bones[name].use_connect = False
        require("FINISHED" in bpy.ops.object.mode_set(mode="OBJECT"), "private reference Object-mode return failed")
    finally:
        if reference.mode == "EDIT":
            bpy.ops.object.mode_set(mode="OBJECT")
        surface.skirt._restore_context(context, state)
        context.view_layer.update()
    marker["native_storage_after_Edit"] = {"pose_and_constraints_unchanged": pose_storage(reference) == storage,
        "drivers_unchanged": [item.as_pointer() for item in reference.animation_data.drivers] == driver_storage,
        "usage": "All subsequent setters/restoration/removal re-resolve primitive identities; pointer stability is diagnostic only"}
    after = surface._rest(reference, reference.data.bones.keys())
    require(derived_rest_equal(before, after, manual)
            and {bone.name: bone.parent.name if bone.parent else None for bone in reference.data.bones} == parents,
            "Private connectivity edit changed other Rest geometry, hierarchy or flags")
    marker["connectivity_exception"]["geometry_parent_other_flags_exact"] = True
    marker["connectivity_exception"]["changed_true_bones"] = [name for name in manual if before[name]["connected"]]
    marker["connectivity_exception"]["retained_false_until_ID_delete"] = True


def private_constructor(surface, marker):
    """Declare the three component edits and four current-RNA safety edits."""
    definition = copy.deepcopy(next(node for node in ast.parse(Path(surface.__file__).read_text(encoding="utf-8")).body
                                   if isinstance(node, ast.FunctionDef) and node.name == "_fixed_neutral_manual"))
    definition.name = "private_default_chart"
    changes = {"disconnect_before_setter": 0, "derived_rest_proof": 0, "candidate_schema": 0,
               "capture_primitive_receipts": 0, "rebind_after_Edit": 0, "finally_current_identity": 0, "remove_current_identity": 0}

    class Changes(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            self.generic_visit(node)
            tries = [index for index, statement in enumerate(node.body) if isinstance(statement, ast.Try)]
            require(len(tries) == 1, "constructor try/finally ABI differs")
            node.body.insert(tries[0], ast.copy_location(ast.parse("receipts = _native_receipts(reference, mutes, drivers, splines)").body[0], node.body[tries[0]]))
            changes["capture_primitive_receipts"] += 1
            return node

        def visit_Try(self, node):
            self.generic_visit(node)
            for index, statement in enumerate(node.body):
                if isinstance(statement, ast.For) and ast.unparse(statement.target) == "(_bone, spline)":
                    node.body.insert(index, ast.copy_location(ast.parse("_disconnect(context, reference, manual)").body[0], statement))
                    node.body.insert(index+1, ast.copy_location(ast.parse("mutes, drivers, splines = _rebind_native(reference, receipts)").body[0], statement))
                    changes["disconnect_before_setter"] += 1
                    changes["rebind_after_Edit"] += 1
                    require(node.finalbody, "constructor finally absent")
                    node.finalbody = [ast.copy_location(ast.parse("_restore_constructor(context, reference, parent, channels, succeeded, bases, receipts)").body[0], node.finalbody[0])]
                    changes["finally_current_identity"] += 1
                    break
            return node

        def visit_For(self, node):
            self.generic_visit(node)
            if ast.unparse(node.target) == "(bone, spline)":
                require(len(node.body) == 1 and ast.unparse(node.body[0]) == "bone.constraints.remove(spline)", "solver removal ABI differs")
                changes["remove_current_identity"] += 1
                return ast.copy_location(ast.parse("_remove_saved_splines(reference, receipts)").body[0], node)
            return node

        def visit_Compare(self, node):
            self.generic_visit(node)
            if (isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name) and node.left.func.id == "_rest"
                    and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq) and len(node.comparators) == 1
                    and isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "rest"):
                changes["derived_rest_proof"] += 1
                return ast.copy_location(ast.parse("_derived_rest(reference, rest, manual)", mode="eval").body, node)
            return node

        def visit_Assign(self, node):
            self.generic_visit(node)
            if any(isinstance(target, ast.Name) and target.id == "expression" for target in node.targets):
                require(isinstance(node.value, ast.Dict), "default constructor expression ABI changed")
                positions = {key.value: index for index, key in enumerate(node.value.keys)}
                require(set(positions) == {"version", "strategy", "chart", "bases", "rest", "parents"}, "default expression fields changed")
                node.value.values[positions["version"]] = ast.Constant(value=2)
                node.value.values[positions["strategy"]] = ast.Constant(value="REST_FK_MANUAL_DISCONNECTED")
                node.value.values[positions["rest"]] = ast.parse("_digest(_rest(reference, reference.data.bones.keys()))", mode="eval").body
                node.value.keys.append(ast.Constant(value="connectivity_exception"))
                node.value.values.append(ast.parse("copy.deepcopy(_marker['connectivity_exception'])", mode="eval").body)
                changes["candidate_schema"] += 1
            return node

    definition = Changes().visit(definition)
    require(changes == {name: 1 for name in changes}, "private AST edit count differs")
    namespace = dict(surface.__dict__)
    namespace.update({"_marker": marker,
        "_native_receipts": native_receipts, "_rebind_native": rebind_native, "_remove_saved_splines": remove_saved_splines,
        "_restore_constructor": lambda context, reference, parent, channels, succeeded, bases, receipts:
            restore_constructor(context, reference, parent, channels, succeeded, bases, receipts, surface, marker),
        "_disconnect": lambda context, reference, manual: disconnect_owned(context, reference, manual, surface, marker),
        "_derived_rest": lambda reference, before, manual: derived_rest_equal(before, surface._rest(reference, reference.data.bones.keys()), manual)})
    tree = ast.fix_missing_locations(ast.Module(body=[definition], type_ignores=[]))
    exec(compile(tree, str(Path(__file__)), "exec"), namespace)
    marker["private_AST_edits"] = changes
    return namespace["private_default_chart"]


def construct_observed(surface, marker, diagnostic, context, reference, wires, record):
    """Read once before the unchanged guard; never change its inputs or outcome."""
    constructor = private_constructor(surface, marker)
    original = next(node for node in ast.parse(Path(surface.__file__).read_text(encoding="utf-8")).body
                    if isinstance(node, ast.FunctionDef) and node.name == "_fixed_neutral_manual")
    guards = [node for node in ast.walk(original) if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Name) and node.func.id == "_require"
              and any(isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                      and "cannot be represented by native FK channels" in arg.value for arg in node.args)]
    require(len(guards) == 1, "unique unchanged default-chart matrix guard required")
    guard_line = guards[0].lineno
    previous_trace = sys.gettrace()
    require(previous_trace is None, "an existing process trace cannot be replaced")
    receipts = set()

    def observer(frame, event, _argument):
        if event == "line" and frame.f_code is constructor.__code__ and frame.f_lineno == guard_line:
            require(guard_line not in receipts, "default-chart guard visited more than once")
            receipts.add(guard_line)
            sys.settrace(None)
            values = frame.f_locals
            require(values["reference"] is reference and values["context"] is context,
                    "observed default-chart reference/context identity differs")
            desired, bases, posed = values["desired"], values["bases"], values["posed"]
            evaluated = {name: diagnostic.plain(posed.pose.bones[name].matrix) for name in bases}
            graph = context.evaluated_depsgraph_get()
            bones = diagnostic.rows(reference, desired, bases, graph, context.scene.unit_settings.scale_length)
            require(all(bones[name]["actual"]["matrix"] == evaluated[name] for name in bases),
                    "observational same-stage evaluated matrices changed without input")
            marker["default_chart_native"] = {"bones": bones, "summary": diagnostic.summary(bones),
                "maximum_matrix_error": max(bones[name]["actual_vs_desired"]["matrix_max"] for name in bones),
                "original_guard_line": guard_line, "original_matrix_limit": 4.0e-5,
                "trace_target_exact_code_object": True, "capture_count": len(receipts),
                "same_stage_evaluated_readback_exact": True, "no_extra_explicit_update": True,
                "observational_warmup_caveat": "Extra evaluated RNA reads can warm the graph; this component makes no timing claim."}
        return observer

    try:
        sys.settrace(observer)
        result = constructor(context, reference, wires, record)
    finally:
        sys.settrace(previous_trace)
    require(len(receipts) == 1 and "default_chart_native" in marker, "actual default-chart numeric capture absent")
    require(marker["default_chart_native"]["maximum_matrix_error"] <= 4.0e-5
            and marker["default_chart_native"]["summary"]["over_unchanged_4e_minus_5_matrix_guard"] == 0,
            "actual matrix capture failed the original default-chart limit")
    return result


def preserve_parent_chart(original, copied, parent, surface):
    """The parent setter can clear inverse; retain the exact old local chart."""
    kind, bone = original.parent_type, original.parent_bone
    inverse, basis = original.matrix_parent_inverse.copy(), original.matrix_basis.copy()
    copied.parent = parent
    copied.parent_type, copied.parent_bone = kind, bone
    copied.matrix_parent_inverse = inverse
    # A native basis setter decomposes TRS. Avoid rewriting already exact channels.
    if surface._matrix(copied.matrix_basis) != surface._matrix(basis):
        copied.matrix_basis = basis
    result = {"source": original.name, "copy": copied.name, "parent_target": parent.name if parent else None,
        "parent_type": kind, "parent_bone": bone, "matrix_parent_inverse": surface._matrix(inverse),
        "matrix_basis": surface._matrix(basis), "exact": copied.parent == parent and copied.parent_type == kind
        and copied.parent_bone == bone and surface._matrix(copied.matrix_parent_inverse) == surface._matrix(inverse)
        and surface._matrix(copied.matrix_basis) == surface._matrix(basis)}
    require(result["exact"], "copied parent chart differs; no artificial offset was applied")
    return result


def retarget_hooks(original, copied, reference, surface):
    require(len(original.modifiers) == len(copied.modifiers), "copied wire modifier inventory differs")
    result = []
    for old, new in zip(original.modifiers, copied.modifiers):
        require(old.type == new.type == "HOOK" and old.name == new.name, "only exact owned wire Hooks can be retargeted")
        inverse, center = old.matrix_inverse.copy(), old.center.copy()
        new.object = reference
        new.matrix_inverse, new.center = inverse, center
        row = {"modifier": old.name, "matrix_inverse": surface._matrix(inverse), "center": list(center),
               "exact": new.object == reference and surface._matrix(new.matrix_inverse) == surface._matrix(inverse)
               and list(new.center) == list(center)}
        result.append(row)
        require(row["exact"], "copied Hook chart differs after retarget; preserve its native inverse and center")
    return result


def geometry_receipts(before, after, metres):
    """Plain-float witnesses are written before the canonical guarded call."""
    require(type(metres) in (int, float) and math.isfinite(metres) and metres > 0., "invalid scene metres")
    rows = {}
    for key in ("H0", "O", "C"):
        left, right = before[key]["points"], after[key]["points"]
        require(left and len(left) == len(right), "comparison native point identity/count differs")
        distances = [math.dist(tuple(a), tuple(b))*metres for a, b in zip(left, right)]
        require(all(math.isfinite(value) for value in distances), "comparison has nonfinite geometry")
        index = max(range(len(distances)), key=distances.__getitem__)
        rows[key] = {"count": len(left), "maximum_m": distances[index], "worst_vertex_index": index,
                     "before_world": left[index], "after_world": right[index],
                     "structure_exact": before[key]["structure"] == after[key]["structure"]}
    return {"native_world_units_to_metres": metres, "measurements": rows,
            "unchanged_surface_guard_m": 5e-5, "C_requires_exact_zero": True,
            "canonical_guard_called": False, "canonical_guard_passed": False}


def guarded_comparison(report, label, before, after, metres, surface, destination):
    row = geometry_receipts(before, after, metres)
    report.setdefault("geometry_comparisons", {})[label] = row
    row["canonical_guard_called"] = True
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Fresh private report only. Preserve numeric/point receipts even when the call raises.
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    row["canonical_errors_m"] = surface._reference_upgrade_errors({key: before[key]["points"] for key in before},
        {key: after[key]["points"] for key in after}, metres)
    require(all(item["structure_exact"] for item in row["measurements"].values()), "native connectivity or skin weights changed")
    row["canonical_guard_passed"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    args.output = args.output.resolve()
    require(args.output.is_relative_to(HERE) and args.output != HERE and not args.output.exists(), "fresh unique Validation output required")
    require(bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath
            and bpy.app.version[:2] == (5, 1), "empty factory/background Blender 5.1 required")
    import hashlib
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    require(sha(UPGRADE) == UPGRADE_SHA and sha(DIAGNOSTIC) == DIAGNOSTIC_SHA, "frozen thin helper changed")
    require(sha(PREVIOUS) == PREVIOUS_SHA, "frozen failed private v2 changed")
    require(sha(FAILED_V3) == FAILED_V3_SHA, "frozen failed private v3 changed")
    import importlib.util

    def load(path, name):
        require(name not in sys.modules, "private helper module already loaded")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    helper = load(UPGRADE, "disconnected_upgrade_helpers")
    diagnostic = load(DIAGNOSTIC, "disconnected_affine_readback_helpers")
    pins = {str(path): sha(path) for path in helper.PINS}
    require(all(pins[str(path)] == expected for path, expected in helper.PINS.items()), "fixed input/runtime/artist pin changed")
    own_sha = sha(Path(__file__))
    workflow = helper.load(HERE / "verify_actual_surface_workflow.py", "disconnected_frozen_workflow")
    qa, diag, addon, surface = workflow.load_dependencies()
    source_manifest = diag.source_manifest()
    disks = {str(path): qa.file_state(path) for path in (helper.INPUT, helper.INSTALL, helper.ARTIST)}
    report = {"component_success": False, "formal_validation": False, "production_effect_accepted": False,
        "public_original_nojump_proved": False, "production_schema_installed": False, "artist_saved_by_verifier": False,
        "private_candidate_marker": {}, "pins_before": pins, "script_sha256": own_sha,
        "previous_private_v2_sha256": PREVIOUS_SHA,
        "failed_private_v3_sha256": FAILED_V3_SHA,
        "scope": "Default chart native FK and one existing-pose H0/O/C; derived reference has a real, explicit connectivity exception",
        "limits": "No original-cache modification, bake, save/reopen, run60, Original roundtrip, Body affine domain or artistic acceptance"}
    args.output.mkdir()
    destination = args.output / "result/neutral_manual_disconnected_fk_component.json"
    began = time.perf_counter()
    tx = None
    protection = None
    completed = False
    try:
        gate_args = argparse.Namespace(input=helper.INPUT.resolve(), install_report=helper.INSTALL.resolve(),
            expected_surface_sha=helper.SURFACE_SHA, expected_worker_sha=helper.WORKER_SHA)
        source_name = workflow.motion_input_gate(gate_args, report, qa, diag)
        addon.register()
        require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(helper.INPUT), load_ui=False, use_scripts=False), "exact legacy input open failed")
        source, rig, record = qa.owned_source(source_name)
        record, rig, actual, cloth, neutral = workflow.motion_objects(source, qa, surface)
        reference = surface._object(record, "NEUTRAL_RIG", source)
        wires = [bpy.data.objects[name] for name in record["physics"]["surface"]["roles"]["NEUTRAL_WIRE"]]
        require(surface._neutral_manual_record(record["physics"]["surface"]) == surface.NEUTRAL_MANUAL_LEGACY, "exact fixture is not legacy")
        protection = qa.Protection()
        inventory = {name: {item.name: item.as_pointer() for item in getattr(bpy.data, name)} for name in workflow.inventory()}
        source_raw, ref_contract = source[qa.skirt.RECORD_KEY], surface._helper_contract(reference)
        inputs = surface._upgrade_inputs(bpy.context, source, rig, record, cloth)
        bindings, cache = helper.author_bindings(surface), helper.cache_semantics(cloth, qa, surface)
        before = helper.sample(source, actual, neutral, diag)
        tx = surface._Transaction(bpy.context, source)
        candidate = tx.copy(reference, "QA Disconnected Default Neutral Rig", bpy.context.scene.collection)
        surface._tag(candidate, source, record, "NEUTRAL_RIG")
        marker = report["private_candidate_marker"]
        marker["copied_parent_charts"] = [preserve_parent_chart(reference, candidate, reference.parent, surface)]
        marker["copied_hook_charts"] = []
        old_constraints = {item.as_pointer() for owner in [reference] + list(reference.pose.bones) for item in owner.constraints}
        require(all(item.as_pointer() not in old_constraints for owner in [candidate] + list(candidate.pose.bones) for item in owner.constraints),
                "private candidate shares native constraint storage")
        require(all(item.as_pointer() not in {curve.as_pointer() for curve in reference.animation_data.drivers}
                    for item in candidate.animation_data.drivers), "private candidate shares native driver storage")
        for bone in candidate.pose.bones:
            for item in bone.constraints:
                if getattr(item, "target", None) == reference:
                    item.target = candidate
        copied_wires = []
        for chain, wire in zip(record["chains"], wires):
            copied = tx.copy(wire, "QA Disconnected Default Wire", bpy.context.scene.collection)
            surface._tag(copied, source, record, "NEUTRAL_WIRE")
            marker["copied_parent_charts"].append(preserve_parent_chart(wire, copied, candidate, surface))
            marker["copied_hook_charts"].append({"wire": wire.name, "Hooks": retarget_hooks(wire, copied, candidate, surface)})
            candidate.pose.bones[chain["manual"][-1]].constraints[0].target = copied
            copied_wires.append(copied)
        marker["wire_copy_scope"] = "Exact original parent type/bone/inverse/basis and Hook inverse/center retained; no world offset. Unconverted clone is measured before default FK."
        marker["reference_rest_before"] = surface._rest(candidate, candidate.data.bones.keys())
        clone_surface = tx.copy(neutral, "QA Disconnected Neutral Surface", bpy.context.scene.collection)
        surface._tag(clone_surface, source, record, "NEUTRAL_SURFACE")
        clone_surface.modifiers[0].object = candidate
        overlay = surface._overlay(source, record)
        preview = tx.copy(source, "QA Disconnected Final Output", bpy.context.scene.collection)
        for owner in (preview, preview.data, preview.data.shape_keys):
            if owner is not None:
                for key in list(owner.keys()):
                    del owner[key]
        group = overlay.node_group.copy()
        tx.nodes.append(group)
        for key in list(group.keys()):
            del group[key]
        preview.modifiers[overlay.name].node_group = group
        group.nodes["Reference"].inputs["Object"].default_value = clone_surface
        surface._node_verify(group, actual, clone_surface)
        require(overlay.node_group.users == group.users == 1, "original/private unique GN users differ")
        bpy.context.view_layer.update()
        clone_before = helper.sample(preview, actual, clone_surface, diag)
        report["native_geometry"] = {"original": before, "unconverted_clone": clone_before}
        metres = bpy.context.scene.unit_settings.scale_length
        guarded_comparison(report, "unconverted_clone_vs_original", before, clone_before, metres, surface, destination)
        expression = construct_observed(surface, marker, diagnostic, bpy.context, candidate, copied_wires, record)
        marker["candidate_schema"] = expression
        require(derived_rest_equal(marker["reference_rest_before"], surface._rest(candidate, candidate.data.bones.keys()), expression["bases"]),
                "derived geometry/hierarchy proof failed")
        bpy.context.view_layer.update()
        after = helper.sample(preview, actual, clone_surface, diag)
        report["native_geometry"]["converted_clone"] = after
        # Persist both comparisons before either native-equivalence guard can raise.
        report.setdefault("geometry_comparisons", {})["converted_vs_unconverted_clone"] = geometry_receipts(clone_before, after, metres)
        report["geometry_comparisons"]["converted_vs_original"] = geometry_receipts(before, after, metres)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        guarded_comparison(report, "converted_vs_unconverted_clone", clone_before, after, metres, surface, destination)
        guarded_comparison(report, "converted_vs_original", before, after, metres, surface, destination)
        completed = True
    except Exception:
        report["error"] = traceback.format_exc()
    finally:
        try:
            if tx is not None:
                if "candidate_schema" in report["private_candidate_marker"]:
                    report["candidate_flags_remained_disconnected_before_delete"] = all(not candidate.data.bones[name].use_connect
                        for name in report["private_candidate_marker"]["candidate_schema"]["bases"])
                    report["candidate_derived_rest_before_delete_exact"] = derived_rest_equal(report["private_candidate_marker"]["reference_rest_before"],
                        surface._rest(candidate, candidate.data.bones.keys()), report["private_candidate_marker"]["candidate_schema"]["bases"])
                surface._clear_reference_upgrade(tx, source, locals().get("preview"))
                bpy.context.view_layer.update()
                report["original_native_IDs_exact"] = {name: {item.name: item.as_pointer() for item in getattr(bpy.data, name)} for name in inventory} == inventory
                report["original_source_reference_input_bindings_cache_exact"] = (source[qa.skirt.RECORD_KEY] == source_raw
                    and surface._helper_contract(reference) == ref_contract and surface._upgrade_inputs(bpy.context, source, rig, record, cloth) == inputs
                    and helper.author_bindings(surface) == bindings and helper.cache_semantics(cloth, qa, surface) == cache)
            require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(helper.INPUT), load_ui=False, use_scripts=False), "exact input cleanup reload failed")
            report["final_raw_input_protection"] = protection.verify() if protection is not None else None
        except Exception:
            report["cleanup_error"] = traceback.format_exc()
        report["pins_after"] = {str(path): sha(path) for path in helper.PINS}
        report["pins_helpers_script_exact"] = report["pins_after"] == pins and sha(UPGRADE) == UPGRADE_SHA and sha(DIAGNOSTIC) == DIAGNOSTIC_SHA and sha(PREVIOUS) == PREVIOUS_SHA and sha(FAILED_V3) == FAILED_V3_SHA and sha(Path(__file__)) == own_sha
        report["disk_exact"] = {str(path): qa.file_state(path) for path in (helper.INPUT, helper.INSTALL, helper.ARTIST)} == disks
        report["canonical_inventory_exact"] = diag.source_manifest() == source_manifest
        report["elapsed_seconds"] = time.perf_counter()-began
        report["component_success"] = (completed and "error" not in report and "cleanup_error" not in report
            and all(report.get(key) is True for key in ("candidate_flags_remained_disconnected_before_delete",
                "candidate_derived_rest_before_delete_exact", "original_native_IDs_exact", "original_source_reference_input_bindings_cache_exact",
                "pins_helpers_script_exact", "disk_exact", "canonical_inventory_exact"))
            and (report.get("final_raw_input_protection") or {}).get("success") is True)
        destination.parent.mkdir()
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"component_success": report["component_success"], "report": str(destination)}), flush=True)
    return 0 if report["component_success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
