"""QA-only native Stretch/Scale transfer over the frozen actual-surface test.

Same factory background entry/arguments/60 forward frames as the frozen base:
  --background --factory-startup --disable-autoexec --threads 1 --python <file>
  -- --output <fresh Validation result folder> --render
Add --preflight-only for field-level install/rollback diagnosis without frame 1.
No runtime/frozen-source writes. Only 32 original PHYS aim mutes, 32 added
STRETCH_TO and 32 added DEF COPY_SCALE constraints are allowed. All other
constraint fields/order, drivers, Rest, raw source, weights and corrections
remain exact. Results stay diagnostic; FULL inheritance plus bending may
introduce local shear that separate Rotation/Scale constraints cannot convey.
The native enabled == not mute alias is explicitly proved and whitelisted;
original constraint UI active flags are restored, new constraints are inactive.
"""

import copy
import hashlib
import json
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "experimental_actual_surface.py"
BASE_SHA256 = "188fd43531133a42aa7c12cf689a3dcb0fc5e1bfbfb2bc2f9527f83fa6ce5bae"
if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != BASE_SHA256:
    raise RuntimeError("Frozen actual-surface experiment differs; refuse Stretch experiment")
sys.path.insert(0, str(HERE))
import experimental_actual_surface as base

diag, qa, bodyqa, skirt = base.diag, base.qa, base.bodyqa, base.skirt
require = base.require
ORIGINAL_CONTRACT = base.dress_contract
ORIGINAL_PROBE = base.make_skin_probe
ORIGINAL_MEASUREMENT = base.measured_frame
ORIGINAL_MANIFEST = base.manifest
STATE = {"installed": False}
PREFLIGHT_ONLY = "--preflight-only" in sys.argv
STRETCH_NAME = "QA Native Physics Stretch"
SCALE_NAME = "QA Native Physics Relative Scale"
SCALE_NUMERIC_LIMIT = 2.e-5
PRIMARY_SOURCE = "https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/blenkernel/intern/constraint.cc"
PRIMARY_RNA = "https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/makesrna/intern/rna_constraint.cc"


def field_differences(before, after, path="$"):
    """Complete primitive field diff, including writable native UI state."""
    before, after = diag.json_content(before), diag.json_content(after)
    result = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(before.keys() | after.keys()):
            location = path + "." + key
            if key not in before or key not in after:
                result.append({"path": location, "before_present": key in before, "after_present": key in after,
                    "before": before.get(key), "after": after.get(key)})
            else:
                result.extend(field_differences(before[key], after[key], location))
    elif isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            location = path + f"[{index}]"
            if index >= len(before) or index >= len(after):
                result.append({"path": location, "before_present": index < len(before), "after_present": index < len(after),
                    "before": before[index] if index < len(before) else None, "after": after[index] if index < len(after) else None})
            else:
                result.extend(field_differences(before[index], after[index], location))
    elif before != after or type(before) is not type(after):
        result.append({"path": path, "before": before, "after": after})
    return result


def verify_enable_alias(rig):
    for bone in rig.pose.bones:
        for constraint in bone.constraints:
            require(constraint.enabled == (not constraint.mute), "Native enabled/mute alias differs: " + bone.name + "/" + constraint.name)


def graph_content(rig):
    verify_enable_alias(rig)
    return {bone.name: [bodyqa.copied_parameters(c) for c in bone.constraints] for bone in rig.pose.bones}


def restore_original_active(rig, before, added=()):
    """Preserve writable UI state rather than ignoring it in graph protection."""
    for _bone, constraint in added:
        constraint.active = False
    for name, original in before.items():
        constraints = rig.pose.bones[name].constraints
        require(len(constraints) >= len(original), "Original constraint list shortened while restoring active: " + name)
        for index, parameters in enumerate(original):
            if constraints[index].active != parameters["active"]:
                constraints[index].active = parameters["active"]
    require(all(not constraint.active for _bone, constraint in added), "New QA constraints must not change the edited UI constraint")
    require(all(rig.pose.bones[name].constraints[index].active == parameters["active"]
                for name, original in before.items() for index, parameters in enumerate(original)),
            "Original constraint active state was not restored exactly")


def drivers_content(rig):
    return [{"path": curve.data_path, "index": curve.array_index,
        "curve": bodyqa.copied_parameters(curve), "driver": bodyqa.copied_parameters(curve.driver),
        "variables": [{"name": variable.name, "type": variable.type,
            "targets": [bodyqa.copied_parameters(target) for target in variable.targets]} for variable in curve.driver.variables]}
        for curve in rig.animation_data.drivers] if rig.animation_data else []


def local_matrix(evaluated, name):
    pose = evaluated.pose.bones[name]
    kwargs = {"parent_matrix": pose.parent.matrix, "parent_matrix_local": pose.parent.bone.matrix_local} if pose.parent else {}
    return pose.bone.convert_local_to_pose(pose.matrix, pose.bone.matrix_local, invert=True, **kwargs)


def axis_scales(matrix):
    return [matrix.to_3x3().col[index].length for index in range(3)]


def local_shear(matrix):
    axes = [matrix.to_3x3().col[index] for index in range(3)]
    require(min(axis.length for axis in axes) > 1.e-10, "Degenerate native local scale")
    return max(abs(axes[a].normalized().dot(axes[b].normalized())) for a, b in ((0, 1), (0, 2), (1, 2)))


def fixture_preflight(source, rig, tracker, record):
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = rig.evaluated_get(graph)
    require(bpy.context.scene.frame_current == 0, "Install only after binding and before the first simulation frame")
    holder, _id, _path = skirt.physics_control(source)
    require(holder["physics_influence"] == 1., "This experiment is limited to the existing fully automatic fixture")
    rows = []
    for ci, chain in enumerate(record["chains"]):
        for si in range(record["segment_count"]):
            names = {layer: chain[layer][si] for layer in ("manual", "phys", "def")}
            bones = {layer: rig.data.bones[name] for layer, name in names.items()}
            poses = {layer: rig.pose.bones[name] for layer, name in names.items()}
            aim = poses["phys"].constraints.get("CD Physics Aim")
            rotation = poses["def"].constraints.get("Skirt physics delta")
            manual = poses["def"].constraints.get("Skirt manual pose")
            require(len(poses["phys"].constraints) == 1 and aim is not None and aim.type == "DAMPED_TRACK"
                    and not aim.mute and aim.enabled and aim.influence == 1. and aim.target == tracker and aim.track_axis == "TRACK_Y"
                    and aim.owner_space == aim.target_space == "WORLD", "Original exact PHYS aim contract differs")
            require(len(poses["def"].constraints) == 2 and list(poses["def"].constraints) == [manual, rotation]
                    and manual is not None and manual.type == "COPY_TRANSFORMS" and manual.target == rig
                    and manual.subtarget == names["manual"] and manual.owner_space == manual.target_space == "LOCAL"
                    and not manual.mute and rotation is not None and rotation.type == "COPY_ROTATION"
                    and not rotation.mute and rotation.target == rig and rotation.subtarget == names["phys"]
                    and rotation.owner_space == rotation.target_space == "LOCAL" and rotation.mix_mode == "BEFORE"
                    and evaluated.pose.bones[names["def"]].constraints[1].influence == 1.,
                    "Final DEF manual/physics stack differs from the fully automatic fixture")
            for layer, bone in bones.items():
                parent = chain[layer][si - 1] if si else record["controls"]["waist"]
                require(bone.parent is not None and bone.parent.name == parent and bone.use_connect == (si > 0)
                        and bone.inherit_scale == "FULL" and bone.use_inherit_rotation,
                        "Exact corresponding FULL/connected parent lineage differs")
            require(max(abs(a-b) for ra, rb in zip(bones["phys"].matrix_local, bones["def"].matrix_local) for a,b in zip(ra,rb)) <= 1.e-7
                    and bones["phys"].length == bones["def"].length, "PHYS/DEF Rest geometry differs")
            raw_manual_scale = tuple(poses["manual"].scale)
            observed_manual_scale = axis_scales(local_matrix(evaluated, names["manual"]))
            require(raw_manual_scale == (1., 1., 1.) and tuple(evaluated.pose.bones[names["manual"]].scale) == (1., 1., 1.)
                    and max(abs(value - 1.) for value in observed_manual_scale) <= SCALE_NUMERIC_LIMIT,
                    "Manual fixture is not unit scale; do not silently replace artist scaling")
            require(tuple(poses["phys"].scale) == (1., 1., 1.) and not any(poses["phys"].location)
                    and bones["phys"].length > 1.e-8, "PHYS neutral channels or positive Rest length differ")
            rows.append({"chain": ci, "segment": si, "names": names, "parents": {layer: bone.parent.name for layer,bone in bones.items()},
                "inherit_scale": {layer: bone.inherit_scale for layer,bone in bones.items()},
                "connected": {layer: bone.use_connect for layer,bone in bones.items()},
                "manual_raw_scale": raw_manual_scale, "manual_evaluated_local_axis_scales": observed_manual_scale,
                "manual_scale_numeric_limit": SCALE_NUMERIC_LIMIT, "rest_length_rig": bones["phys"].length,
                "exact_target_object": tracker.name, "exact_target_group": aim.subtarget,
                "original_aim": bodyqa.copied_parameters(aim), "original_def_stack": [bodyqa.copied_parameters(c) for c in poses["def"].constraints]})
    require(len(rows) == 32, "Must prove all exact 32 segments before any constraint mutation")
    return rows


def verify_active_constraints(rig, rows):
    for row in rows:
        names = row["names"]
        aim, stretch = rig.pose.bones[names["phys"]].constraints
        scale = rig.pose.bones[names["def"]].constraints[2]
        require(aim.name == "CD Physics Aim" and aim.type == "DAMPED_TRACK" and aim.mute and not aim.enabled,
                "Original aim must remain explicitly muted, not pretend to be the active driver")
        require(stretch.name == STRETCH_NAME and stretch.type == "STRETCH_TO" and not stretch.mute and stretch.enabled and not stretch.active
                and stretch.target == aim.target and stretch.subtarget == aim.subtarget
                and stretch.volume == "NO_VOLUME" and stretch.keep_axis == "SWING_Y"
                and stretch.owner_space == stretch.target_space == "WORLD" and stretch.influence == 1.
                and stretch.rest_length == row["rest_length_rig"] and stretch.rest_length > 0.,
                "Active Stretch exact target/explicit Rest length/settings proof failed")
        require(scale.name == SCALE_NAME and scale.type == "COPY_SCALE" and not scale.mute and scale.enabled and not scale.active
                and scale.target == rig and scale.subtarget == names["phys"]
                and scale.owner_space == scale.target_space == "LOCAL" and scale.influence == 1.
                and scale.use_x and scale.use_y and scale.use_z and scale.use_offset and not scale.use_add
                and not scale.use_make_uniform and scale.power == 1.,
                "Active multiplicative parent-relative scale proof failed")


def install_transfer(source, rig, tracker, record, report):
    rows = fixture_preflight(source, rig, tracker, record)
    before = graph_content(rig)
    before_contract = ORIGINAL_CONTRACT(rig, record, source)
    before_drivers = drivers_content(rig)
    before_rest = qa.digest(qa.rest_content(rig))
    report.update(fixture=rows, graph_before=before, drivers_before=before_drivers,
                  before_rest_sha256=before_rest, original_contract_sha256=before_contract,
                  diagnostic_preflight_only_requested=PREFLIGHT_ONLY)
    created, muted = [], []
    try:
        for row in rows:
            names = row["names"]
            phys, deform = rig.pose.bones[names["phys"]], rig.pose.bones[names["def"]]
            aim = phys.constraints[0]
            stretch = phys.constraints.new("STRETCH_TO")
            created.append((phys, stretch))
            stretch.mute = True
            stretch.name = STRETCH_NAME
            # Set explicit native rig-unit length before target/evaluation; never auto-calibrate from the posed frame.
            stretch.rest_length = row["rest_length_rig"]
            stretch.volume, stretch.keep_axis = "NO_VOLUME", "SWING_Y"
            stretch.owner_space = stretch.target_space = "WORLD"
            stretch.head_tail, stretch.influence = 0., 1.
            stretch.target, stretch.subtarget = aim.target, aim.subtarget
            scale = deform.constraints.new("COPY_SCALE")
            created.append((deform, scale))
            scale.name = SCALE_NAME
            scale.target, scale.subtarget = rig, names["phys"]
            scale.owner_space = scale.target_space = "LOCAL"
            scale.use_x = scale.use_y = scale.use_z = True
            scale.use_offset, scale.use_add, scale.use_make_uniform = True, False, False
            scale.power, scale.influence = 1., 1.
            muted.append(aim)
            aim.mute = True
            stretch.mute = False
        restore_original_active(rig, before, created)
        bpy.context.view_layer.update()
        after = graph_content(rig)
        after_drivers = drivers_content(rig)
        report.update(graph_after=after, drivers_after=after_drivers,
            before_to_after_graph_field_differences=field_differences(before, after),
            before_to_after_driver_field_differences=field_differences(before_drivers, after_drivers),
            after_rest_sha256=qa.digest(qa.rest_content(rig)))
        verify_active_constraints(rig, rows)
        expected = copy.deepcopy(before)
        allowed = []
        for row in rows:
            phys, deform = row["names"]["phys"], row["names"]["def"]
            expected[phys][0]["mute"] = True
            expected[phys][0]["enabled"] = False
            expected[phys].append(after[phys][1])
            expected[deform].append(after[deform][2])
            allowed.append({"PHYS": phys, "existing_aim_only_fields": {"mute": {"before": False, "after": True},
                "enabled": {"before": True, "after": False}},
                "added_active_stretch": after[phys][1], "DEF": deform, "added_final_copy_scale": after[deform][2]})
        report.update(graph_whitelist_expected=expected, diff_whitelist=allowed,
                      whitelist_expected_to_actual_field_differences=field_differences(expected, after))
        require(after == expected, "Constraint diff escaped the explicit 32-mute/64-add whitelist")
        require(before_drivers == drivers_content(rig) and before_rest == qa.digest(qa.rest_content(rig)),
                "Stretch installation changed original drivers or Rest")
        report.update(fixture=rows, graph_before=before, graph_after=after, diff_whitelist=allowed,
            original_rig_drivers_sha256=qa.digest(before_drivers), rest_sha256=before_rest,
            original_contract_sha256=before_contract, all_non_whitelisted_constraints_exact=True,
            enabled_mute_native_reverse_alias_proved=True, original_constraint_active_flags_exact=True,
            new_constraints_ui_active_false=True,
            activity="Original Damped Track is retained muted solely for rollback/target evidence. Only the separately proved Stretch drives PHYS.",
            primary_sources=[PRIMARY_SOURCE, PRIMARY_RNA],
            theory="Stretch SWING_Y normalizes world Y scale, uses explicit bone.length, then produces target distance / bone.length; NO_VOLUME preserves transverse scales. Native Copy Scale LOCAL derives PHYS scale relative to its own corresponding parent; multiplicative offset preserves preexisting manual scale. No world-total scale is copied a second time.",
            limitation="FULL inheritance plus bends/nonuniform length can create local target shear. Separate Rotation/Scale constraints decompose it and are not mathematically guaranteed to reconstruct PHYS. This experiment measures that error, makes no success assumption, and never changes inherit_scale/Rest/manual graph.")
        STATE.update(installed=True, source=source, rig=rig, tracker=tracker, record=record, rows=rows,
                     graph_before=before, graph_after=after, drivers_before=before_drivers,
                     before_contract=before_contract, report=report)
        bpy.context.scene["CD_QA_StretchTransfer"] = json.dumps({"unreleased": True,
            "allowed_diffs": "32 owned aim mute changes plus 32 Stretch and 32 Copy Scale additions only",
            "automatic_influence": 1.0, "rest_inheritance_and_manual_graph_unchanged": True,
            "public_setup_reset_bake_or_Original_mode_unsupported_on_this_diagnostic_graph": True})
    except Exception:
        report["graph_at_failure"] = graph_content(rig)
        report["drivers_at_failure"] = drivers_content(rig)
        report["before_to_failure_graph_field_differences"] = field_differences(before, report["graph_at_failure"])
        try:
            for bone, constraint in reversed(created):
                bone.constraints.remove(constraint)
            for aim in muted:
                aim.mute = False
            restore_original_active(rig, before)
        finally:
            rollback = graph_content(rig)
            rollback_drivers = drivers_content(rig)
            report.update(graph_after_rollback=rollback, drivers_after_rollback=rollback_drivers,
                before_to_rollback_graph_field_differences=field_differences(before, rollback),
                before_to_rollback_driver_field_differences=field_differences(before_drivers, rollback_drivers),
                rollback_rest_sha256=qa.digest(qa.rest_content(rig)),
                rollback_original_contract_sha256=ORIGINAL_CONTRACT(rig, record, source))
        require(rollback == before and rollback_drivers == before_drivers
                and report["rollback_original_contract_sha256"] == before_contract, "Constraint installation rollback failed")
        raise


def guarded_contract(rig, record, source):
    if not STATE["installed"]:
        return ORIGINAL_CONTRACT(rig, record, source)
    require(rig == STATE["rig"] and source == STATE["source"], "Wrong fixture for transfer whitelist")
    verify_active_constraints(rig, STATE["rows"])
    current = graph_content(rig)
    require(current == STATE["graph_after"] and drivers_content(rig) == STATE["drivers_before"],
            "Constraint/driver graph changed outside the declared exact experiment")
    normalized = copy.deepcopy(current)
    for row in STATE["rows"]:
        phys, deform = row["names"]["phys"], row["names"]["def"]
        normalized[phys].pop(1)  # Only the already-validated exact added Stretch.
        normalized[phys][0]["mute"] = False  # Only the declared false -> true mute diff.
        normalized[phys][0]["enabled"] = True  # Native opposite alias of that same declared mute diff.
        normalized[deform].pop(2)  # Only the already-validated exact added Copy Scale.
    require(normalized == STATE["graph_before"], "Normalized graph is not the exact original graph")
    # Same original base content/fields, reconstructed only after strict graph proof.
    content = {"rest": qa.rest_content(rig),
        "constraints": {name: normalized[name] for name in record["shared"]["names"]},
        "source_modifiers": [bodyqa.copied_parameters(m) for m in source.modifiers],
        "source_record": source.get(skirt.RECORD_KEY),
        "corrections": {key: source[key] for key in source.keys() if "correction" in key},
        "shared_names": list(record["shared"]["names"])}
    normalized_hash = qa.digest(content)
    require(normalized_hash == STATE["before_contract"], "Rest/skin/source/corrections changed outside the constraint whitelist")
    STATE["report"]["final_normalized_original_contract_exact"] = True
    return normalized_hash


def probe_then_transfer(source, actual, collection, report):
    probe = ORIGINAL_PROBE(source, actual, collection, report)
    try:
        rig = source[skirt.RIG_KEY]
        record = skirt.read_record(source)
        tracker = bpy.data.objects[record["physics"]["proxy"]]
        report["stretch_transfer"] = {}
        install_transfer(source, rig, tracker, record, report["stretch_transfer"])
        if PREFLIGHT_ONLY:
            report["stretch_transfer"]["diagnostic_stop_after_install_before_first_frame"] = True
            raise RuntimeError("QA_PREFLIGHT_ONLY_STOP_AFTER_PROVED_INSTALL; no simulation frames requested")
    except Exception:
        base.remove_skin_probe(probe, source, report)
        raise
    return probe


def measured_transfer(*args):
    require(STATE["installed"], "Stretch transfer must be installed before any measured frame")
    source, rig, tracker, record = STATE["source"], STATE["rig"], STATE["tracker"], STATE["record"]
    guarded_contract(rig, record, source)
    item = ORIGINAL_MEASUREMENT(*args)
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = rig.evaluated_get(graph)
    rows = []
    for row in STATE["rows"]:
        names = row["names"]
        phys_local, def_local = local_matrix(evaluated, names["phys"]), local_matrix(evaluated, names["def"])
        manual_scales = axis_scales(local_matrix(evaluated, names["manual"]))
        require(max(abs(scale-1.) for scale in manual_scales) <= SCALE_NUMERIC_LIMIT,
                "Manual scale changed; unit-manual fixture premise no longer holds")
        require(evaluated.pose.bones[names["def"]].constraints[1].influence == 1., "Physics rotation ceased to be fully automatic")
        a, b = evaluated.pose.bones[names["phys"]], evaluated.pose.bones[names["def"]]
        meters = bpy.context.scene.unit_settings.scale_length
        rows.append({"chain": row["chain"], "segment": row["segment"], "names": names,
            "phys_local_axis_scales": axis_scales(phys_local), "def_local_axis_scales": axis_scales(def_local),
            "manual_local_axis_scales": manual_scales,
            "phys_local_normalized_shear": local_shear(phys_local), "def_local_normalized_shear": local_shear(def_local),
            "def_vs_phys_head_m": (evaluated.matrix_world @ a.head-evaluated.matrix_world @ b.head).length * meters,
            "def_vs_phys_tail_m": (evaluated.matrix_world @ a.tail-evaluated.matrix_world @ b.tail).length * meters})
    item["active_stretch_transfer"] = {"active_constraints_exactly_proved": True,
        "retained_original_aims_are_muted": True, "rest_lengths_never_auto_initialized": True,
        "all_non_whitelisted_graph_and_driver_fields_exact": True, "segments": rows,
        "phys_local_shear_max": max(row["phys_local_normalized_shear"] for row in rows),
        "def_vs_phys_tail_max_m": max(row["def_vs_phys_tail_m"] for row in rows),
        "definition": "Active Stretch target/settings are independently proved; base endpoint metrics use the identically targeted retained muted aim only as exact target metadata."}
    return item


def experiment_manifest():
    values = ORIGINAL_MANIFEST()
    values[str(Path(__file__).resolve())] = qa.file_state(Path(__file__).resolve())
    return values


def main():
    base.dress_contract, base.make_skin_probe = guarded_contract, probe_then_transfer
    base.measured_frame, base.manifest = measured_transfer, experiment_manifest
    if PREFLIGHT_ONLY:
        sys.argv.remove("--preflight-only")  # Narrow diagnostic flag; all frozen base guards/arguments stay intact.
    args = base.arguments()
    result = base.main(args)
    result["purpose"] = "Unreleased native Stretch/relative Scale transfer over exact frozen actual-surface experiment"
    result["frozen_actual_surface_sha256"] = BASE_SHA256
    result["actual_constraint_changes_are_diagnostic_only"] = True
    result["diagnostic_preflight_only_requested"] = PREFLIGHT_ONLY
    result["simulation_frames_executed"] = 0 if PREFLIGHT_ONLY else (60 if result.get("diagnostic_completed") else None)
    result["production_effect_accepted"] = result["canonical_full_graph_pass"] = False
    result["limitations"].append("FULL parent-scale inheritance may create LOCAL shear that separate native Rotation/Scale cannot preserve; no Rest/inheritance modification is authorized by this experiment.")
    result["limitations"].append("Added Copy Scale uses fixed influence 1 only for the proved fully automatic fixture; this diagnostic does not implement production Original/mode suppression or blended physics scaling.")
    path = args.output / "experimental_actual_surface.json"
    conversions = []
    output = diag.json_content(result, conversions=conversions)
    output["json_mathutils_conversions"] = conversions
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("EXPERIMENTAL_STRETCH_TRANSFER_REPORT=" + str(path), flush=True)
    if not result["success"]:
        raise RuntimeError("QA Stretch transfer incomplete; inspect exact whitelist/protection JSON")
    return result


if __name__ == "__main__":
    main()
