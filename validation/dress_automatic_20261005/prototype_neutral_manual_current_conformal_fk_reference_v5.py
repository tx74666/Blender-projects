"""Private current/conformal component with an explicit connectivity exception.

Only this disposable reference's Manual bones lose use_connect. Their parent,
Rest geometry and all other flags, and the entire Main Rig, stay exact. The
current live native parent/Rest convert is measured under the original 4e-5
and 50um/C-exact gates. Native RNA is re-resolved from primitive receipts,
including exceptional restoration. This is not the identity default Rest chart.
Born-conformal/current-pose only: future Body input, modes, persistence and
production/artistic acceptance remain unproved. No handler, source rewire,
run60, public Original, bake or scene save. Canonical 9d7 stays frozen.
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
FAILED_V4 = HERE / "prototype_neutral_manual_disconnected_fk_reference_v4.py"
FAILED_V4_SHA = "1b3594de915ad5a7329efbf51545e3b392f569698d2ad6d91ddd8be904ce2e4a"


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


def restore_constructor(context, reference, parent, channels, succeeded, bases, receipts, surface, marker, *, restore_parent=True):
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
    if restore_parent:
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


def conformal_matrix(matrix):
    """Current Float32 native affine chart, with an explicit relative noise bound."""
    values = [[float(value) for value in row] for row in matrix]
    finite = len(values) == 4 and all(len(row) == 4 for row in values) and all(math.isfinite(value) for row in values for value in row)
    result = {"finite": finite, "admissible_current_chart": False, "relative_F32_storage_bound": 1.e-6,
              "matrix": values if finite else None}
    if not finite:
        result["reason"] = "nonfinite or invalid native affine matrix"
        return result
    columns = [[values[row][column] for row in range(3)] for column in range(3)]
    lengths = [math.sqrt(math.fsum(value*value for value in column)) for column in columns]
    determinant = math.fsum(values[0][i]*(values[1][(i+1)%3]*values[2][(i+2)%3]
        - values[1][(i+2)%3]*values[2][(i+1)%3]) for i in range(3))
    valid = all(math.isfinite(value) and value > 0. for value in lengths) and math.isfinite(determinant)
    uniform = (max(lengths)-min(lengths))/max(lengths) if valid else None
    shear = max(abs(math.fsum(a*b for a,b in zip(columns[i],columns[j])))/(lengths[i]*lengths[j])
                for i in range(3) for j in range(i+1,3)) if valid else None
    affine = values[3] == [0., 0., 0., 1.]
    result.update({"column_lengths": lengths, "determinant": determinant, "positive": valid and determinant > 0.,
                   "relative_uniform_error": uniform, "normalized_shear_error": shear, "affine_last_row_exact": affine})
    result["admissible_current_chart"] = bool(valid and determinant > 0. and affine and uniform <= 1.e-6 and shear <= 1.e-6)
    result["reason"] = "within declared native F32 conformal storage bound" if result["admissible_current_chart"] else "nonuniform, shear, reflection or degenerate affine"
    return result


def numeric_evidence(values):
    numbers = [float(value) for value in values]
    return {"values": [value if math.isfinite(value) else repr(value) for value in numbers],
            "finite": all(math.isfinite(value) for value in numbers)}


def current_conformal_manual(context, reference, wires, record, surface, diagnostic, marker, report, destination):
    """Capture the actual default Manual at this Body pose, without identity chart."""
    target = reference.constraints[0].target if reference.constraints else None
    require(reference.get(surface.ROLE_KEY) == "NEUTRAL_RIG" and target is not None and reference != target
            and reference.data != target.data and reference.data.users == 1 and reference.data.pose_position == "POSE",
            "only an independent owned pose-reference may be converted")
    require(reference.animation_data is not None and reference.animation_data.action is None
            and not reference.animation_data.nla_tracks and reference.data.animation_data is None,
            "private neutral reference has an unexpected author Action/NLA")
    manual = [name for chain in record["chains"] for name in chain["manual"]]
    terminal = {chain["manual"][-1]: wire for chain, wire in zip(record["chains"], wires)}
    require(len(wires) == len(terminal) == record["chain_count"] == 8, "all eight current Manual wire solvers are required")
    neutral = {"location": [0.,0.,0.], "rotation_euler": [0.,0.,0.], "rotation_quaternion": [1.,0.,0.,0.],
               "rotation_axis_angle": [0.,0.,1.,0.], "scale": [1.,1.,1.]}
    channels = {name: {field: list(getattr(reference.pose.bones[name], field)) for field in surface._CHANNELS} for name in manual}
    marker["current_manual_raw_channels"] = {name: {field: numeric_evidence(values) for field,values in fields.items()}
                                            for name,fields in channels.items()}
    marker["current_manual_raw_channels_neutral"] = all(fields == neutral for fields in channels.values())
    graph = context.evaluated_depsgraph_get()
    posed, main = reference.evaluated_get(graph), target.evaluated_get(graph)
    upstream = surface._ancestors(target, record) + [record["controls"]["waist"]]
    chart = {"strategy": "CURRENT_CONFORMAL_LOCAL_FK", "chart": "LIVE_UNIFORM_POSITIVE_BODY_POSE_V1",
             "frame": context.scene.frame_current, "subframe": context.scene.frame_subframe,
             "future_body_domain_proved": False, "identity_default_Rest_proved": False, "samples": {},
             "artist_raw_scale_is_readonly_evidence_not_an_acceptance_gate": True,
             "limits": "Only this measured positive/uniform current Body chart; no future pose, scale, mode, persistence or writer promise."}
    for label, obj, evaluated in (("MainObject", target, main), ("NeutralObject", reference, posed)):
        chart["samples"][label] = conformal_matrix(evaluated.matrix_world)
        chart["samples"][label]["original_scale_evidence"] = numeric_evidence(obj.scale)
        for name in upstream:
            bone = evaluated.pose.bones.get(name)
            row = {"bone_exists": False, "admissible_current_chart": False} if bone is None else conformal_matrix(evaluated.matrix_world @ bone.matrix)
            if bone is not None:
                row["bone_exists"] = True
                row["raw_scale_evidence"] = numeric_evidence(obj.pose.bones[name].scale)
            chart["samples"][label + "/" + name] = row
    marker["born_current_body_chart"] = chart
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    require(marker["current_manual_raw_channels_neutral"], "candidate default Manual contains raw manual input; no author pose may be absorbed")
    require(all(row["admissible_current_chart"] for row in chart["samples"].values()), "the current Body/Object/Waist chart is not proved positive and conformal")
    desired = {bone.name: bone.matrix.copy() for bone in posed.pose.bones}
    splines = []
    for name in manual:
        items = list(reference.pose.bones[name].constraints)
        if name in terminal:
            require(len(items) == 1 and items[0].type == "SPLINE_IK" and items[0].target == terminal[name]
                    and not items[0].mute and items[0].influence == 1., "private current Manual terminal solver differs")
            splines.append((reference.pose.bones[name],items[0]))
        else:
            require(not items, "private Manual has an additional live constraint")
    rest = surface._rest(reference, reference.data.bones.keys())
    parents = {bone.name: bone.parent.name if bone.parent else None for bone in reference.data.bones}
    parent_chart = surface._frame(reference)
    parent = (reference.parent, reference.parent_type, reference.parent_bone, reference.matrix_parent_inverse.copy(), reference.matrix_basis.copy())
    mutes = [(item,item.mute) for owner in [reference] + list(reference.pose.bones) for item in owner.constraints]
    drivers = [(curve,curve.mute) for curve in reference.animation_data.drivers]
    receipts = native_receipts(reference,mutes,drivers,splines)
    succeeded, bases = False, {}
    try:
        disconnect_owned(context, reference, manual, surface, marker)
        _mutes, _drivers, current_splines = rebind_native(reference, receipts)
        for name in manual:
            bone = reference.pose.bones[name]
            options = {"parent_matrix": desired[bone.parent.name], "parent_matrix_local": bone.parent.bone.matrix_local} if bone.parent else {}
            bases[name] = bone.bone.convert_local_to_pose(desired[name], bone.bone.matrix_local, invert=True, **options)
            require(all(math.isfinite(value) for row in bases[name] for value in row), "nonfinite current local FK matrix")
        for _owner,item in current_splines:
            item.mute = True
        for name,basis in bases.items():
            reference.pose.bones[name].matrix_basis = basis
        reference.update_tag()
        context.view_layer.update()
        bones = diagnostic.rows(reference,desired,bases,context.evaluated_depsgraph_get(),context.scene.unit_settings.scale_length)
        maximum = max(row["actual_vs_desired"]["matrix_max"] for row in bones.values())
        marker["current_conformal_chart_native"] = {"bones": bones, "summary": diagnostic.summary(bones),
            "maximum_matrix_error": maximum, "unchanged_matrix_limit": 4.e-5, "current_native_parent_Rest_inverse": True}
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        require(maximum <= 4.e-5, "current neutral Manual cannot be represented by native FK channels; no fallback")
        bases = {name: surface._matrix(reference.pose.bones[name].matrix_basis) for name in manual}
        succeeded = True
    finally:
        # No Object chart or nonManual channels were changed. Do not rewrite them.
        restore_constructor(context,reference,parent,channels,succeeded,bases,receipts,surface,marker,restore_parent=False)
    remove_saved_splines(reference,receipts)
    require(derived_rest_equal(rest,surface._rest(reference,reference.data.bones.keys()),manual)
            and parents == {bone.name:bone.parent.name if bone.parent else None for bone in reference.data.bones}
            and surface._frame(reference) == parent_chart, "current FK changed something besides private Manual connectivity")
    expression = {"version": 1, "strategy": "CURRENT_CONFORMAL_LOCAL_FK", "chart": "LIVE_UNIFORM_POSITIVE_BODY_POSE_V1",
                  "bases": bases, "rest": surface._digest(surface._rest(reference,reference.data.bones.keys())), "parents": parents,
                  "connectivity_exception": copy.deepcopy(marker["connectivity_exception"]), "birth_chart": chart,
                  "current_pose_only": True, "future_body_domain_proved": False, "identity_default_Rest_proved": False}
    reference[surface.NEUTRAL_MANUAL_KEY] = surface._json(expression)
    reference.update_tag()
    context.view_layer.update()
    return expression


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
    require(sha(FAILED_V4) == FAILED_V4_SHA, "frozen failed private v4 changed")
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
        "failed_private_v4_sha256": FAILED_V4_SHA,
        "scope": "Current/conformal native local FK and one existing-pose H0/O/C; no identity default Rest equivalence",
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
        original_mode_frame = (rig.mode, rig.data.pose_position, bpy.context.scene.frame_current, bpy.context.scene.frame_subframe)
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
        expression = current_conformal_manual(bpy.context,candidate,copied_wires,record,surface,diagnostic,marker,report,destination)
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
                report["original_rig_pose_mode_frame_exact"] = (rig.mode, rig.data.pose_position, bpy.context.scene.frame_current, bpy.context.scene.frame_subframe) == original_mode_frame
            require("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(helper.INPUT), load_ui=False, use_scripts=False), "exact input cleanup reload failed")
            report["final_raw_input_protection"] = protection.verify() if protection is not None else None
        except Exception:
            report["cleanup_error"] = traceback.format_exc()
        report["pins_after"] = {str(path): sha(path) for path in helper.PINS}
        report["pins_helpers_script_exact"] = report["pins_after"] == pins and sha(UPGRADE) == UPGRADE_SHA and sha(DIAGNOSTIC) == DIAGNOSTIC_SHA and sha(PREVIOUS) == PREVIOUS_SHA and sha(FAILED_V3) == FAILED_V3_SHA and sha(FAILED_V4) == FAILED_V4_SHA and sha(Path(__file__)) == own_sha
        report["disk_exact"] = {str(path): qa.file_state(path) for path in (helper.INPUT, helper.INSTALL, helper.ARTIST)} == disks
        report["canonical_inventory_exact"] = diag.source_manifest() == source_manifest
        report["elapsed_seconds"] = time.perf_counter()-began
        report["component_success"] = (completed and "error" not in report and "cleanup_error" not in report
            and all(report.get(key) is True for key in ("candidate_flags_remained_disconnected_before_delete",
                "candidate_derived_rest_before_delete_exact", "original_native_IDs_exact", "original_source_reference_input_bindings_cache_exact",
                "original_rig_pose_mode_frame_exact",
                "pins_helpers_script_exact", "disk_exact", "canonical_inventory_exact"))
            and (report.get("final_raw_input_protection") or {}).get("success") is True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"component_success": report["component_success"], "report": str(destination)}), flush=True)
    return 0 if report["component_success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
