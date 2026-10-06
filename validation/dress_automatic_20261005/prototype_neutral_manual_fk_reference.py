"""Private current-pose Neutral Manual FK component experiment; no acceptance.

Reuse pinned 27e6 run60/public Original stages and 4198 read-only helpers. Only
private clones lose their Manual SPLINE_IK. Capture native evaluated Manual
pose and convert it to Local Pose bases with exact cloned Rest/inheritance.
This tests current-pose equivalence, not installed Rest equivalence, arbitrary
Body shear, a production migration, speed, or final cloth/artist/Unity quality.
The unchanged public 50um guard and its failure/exit 2 remain authoritative.
Additional copies, one construction update and readbacks may warm the graph.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import bpy

HERE = Path(__file__).resolve().parent
BASE = HERE / "diagnose_original_surface_stages.py"
DEPENDENCY = HERE / "diagnose_original_surface_dependency_chain.py"
BASE_SHA = "27e6c7780a7bc89dfb4bb21d20b5d0b7ba783282676f73702322dda5e4b40c2a"
DEPENDENCY_SHA = "4198e9966cb94113e35cfbc4aa1efcbbd882a3702f035da7111a5e40e02e6471"


def require(value, message):
    if not value:
        raise RuntimeError("Private Neutral Manual FK: " + message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, name):
    require(name not in sys.modules, "private diagnostic module is already loaded")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def inventory():
    return {name: {item.name: item.as_pointer() for item in getattr(bpy.data, name)}
            for name in ("objects", "meshes", "armatures", "shape_keys", "node_groups", "actions")}


def receipt(obj):
    keys = getattr(obj.data, "shape_keys", None)
    return {"object": obj.name, "object_pointer": obj.as_pointer(), "data": obj.data.name,
            "data_pointer": obj.data.as_pointer(),
            "keys": keys.name if keys else None, "keys_pointer": keys.as_pointer() if keys else None}


def strip_tags(owner):
    owner.use_fake_user = False
    for key in list(owner.keys()):
        del owner[key]


def immutable(source, rig, neutral, reference, qa, surface):
    keys = source.data.shape_keys
    return {"source_raw": qa.raw_mesh_content(source), "neutral_raw": qa.raw_mesh_content(neutral),
            "main_rest": qa.rest_content(rig), "neutral_rest": qa.rest_content(reference),
            "main_drivers": surface._drivers(rig), "neutral_drivers": surface._drivers(reference),
            "source_keys": None if keys is None else [keys.name, keys.as_pointer()],
            "overlay_node_content": surface._node_content(surface._overlay(source, qa.skirt.read_record(source)).node_group)}


def clone_fk(reference, rig, record, scene, graph, objects, data, qa, base, marker):
    manual = [name for chain in record["chains"] for name in chain["manual"]]
    posed = reference.evaluated_get(graph)
    # All desired parent frames are captured before changing any private basis.
    desired = {bone.name: bone.matrix.copy() for bone in posed.pose.bones}
    clone = reference.copy()
    objects.append(clone)  # Exact allocation receipt precedes every later fallible operation.
    copied = reference.data.copy()
    data.append(copied)
    clone.data = copied
    clone.name = "QA Neutral Manual FK Rig"
    copied.name = "QA Neutral Manual FK Rest"
    strip_tags(clone); strip_tags(copied)
    require(clone != reference and copied != reference.data and copied.users == 1,
            "neutral rig/data copy is not independent")
    require(qa.rest_content(clone) == qa.rest_content(reference), "private copy changed exact native Rest subset")
    require(clone.animation_data and clone.animation_data.action is None
            and not clone.animation_data.nla_tracks and copied.animation_data is None,
            "neutral clone unexpectedly carries Action/NLA/data animation")
    old_curves = {curve.as_pointer() for curve in reference.animation_data.drivers}
    require(all(curve.as_pointer() not in old_curves for curve in clone.animation_data.drivers),
            "private neutral drivers are not independent")
    old_constraints = {con.as_pointer() for owner in [reference] + list(reference.pose.bones)
                       for con in owner.constraints}
    require(all(con.as_pointer() not in old_constraints for owner in [clone] + list(clone.pose.bones)
                for con in owner.constraints), "private neutral constraints are not independent")
    retargeted = []
    for owner in [clone] + list(clone.pose.bones):
        for constraint in owner.constraints:
            for field in ("target", "space_object", "pole_target"):
                if hasattr(constraint, field) and getattr(constraint, field) == reference:
                    setattr(constraint, field, clone)
                    retargeted.append([getattr(owner, "name", clone.name), constraint.name, field])
    for curve in clone.animation_data.drivers:
        for variable in curve.driver.variables:
            for target in variable.targets:
                if target.id == reference:
                    target.id = clone
                elif target.id == reference.data:
                    target.id = copied
    bases = {}
    splines = []
    for name in manual:
        bone = clone.pose.bones[name]
        kwargs = {"parent_matrix": desired[bone.parent.name],
                  "parent_matrix_local": bone.parent.bone.matrix_local} if bone.parent else {}
        bases[name] = bone.bone.convert_local_to_pose(desired[name], bone.bone.matrix_local,
                                                     invert=True, **kwargs)
        for constraint in bone.constraints:
            require(constraint.type == "SPLINE_IK" and name in [chain["manual"][-1] for chain in record["chains"]],
                    "unexpected live Manual constraint would be baked twice")
            splines.append((bone, constraint))
    require(len(splines) == record["chain_count"] == 8, "expected exactly eight private Manual SplineIK constraints")
    for bone, constraint in splines:
        bone.constraints.remove(constraint)
    for name, basis in bases.items():
        clone.pose.bones[name].matrix_basis = basis
    require(not any(con.type == "SPLINE_IK" for bone in clone.pose.bones for con in bone.constraints),
            "private FK reference retained a SplineIK solver")
    clone.hide_viewport = False
    clone.hide_render = clone.hide_select = True
    scene.collection.objects.link(clone)
    clone.hide_set(True)
    marker["rig_receipt"] = receipt(clone)
    marker["retargeted_self_constraint_fields"] = retargeted
    marker["manual_names"] = manual
    marker["manual_capture_pose_matrices"] = {name: base.matrix(desired[name]) for name in manual}
    marker["private_local_bases"] = {name: base.matrix(value) for name, value in bases.items()}
    return clone


def component(original, base, dep, workflow, diagnostic, source, rig, actual, cloth, neutral, result, qa, surface, metres):
    record = qa.skirt.read_record(source)
    reference = bpy.data.objects[record["physics"]["surface"]["roles"]["NEUTRAL_RIG"][0]]
    names = list(reference.pose.bones.keys())
    marker = {"script": str(Path(__file__)), "sha256": sha(Path(__file__)),
              "current_pose_only": True, "installed_rest_equivalence_proved": False,
              "arbitrary_body_shear_equivalence_proved": False, "formal_validation": False,
              "production_effect_accepted": False, "artist_effect_accepted": False,
              "automatic_writer_changed": False, "stages": [], "component_complete": False,
              "public_geometry_guard_m": qa.geometry_guard(metres),
              "limitation": "Private current-pose FK clone; construction/update and extra reads affect warmup. Original public reference, cache, writer and 50um failure are unchanged."}
    diagnostic["neutral_manual_fk_component"] = marker
    require(marker["public_geometry_guard_m"] == 5e-5, "public 50um guard changed")
    old_mesh, old_pose = base.native_mesh, base.pose_row
    before_inventory = inventory()
    protected = immutable(source, rig, neutral, reference, qa, surface)
    graph = bpy.context.evaluated_depsgraph_get()
    before = {name: old_mesh(obj, graph) for name, obj in (("O", source), ("H0", neutral), ("C", actual))}
    objects, data, probes, group = [], [], [], None
    try:
        clone = clone_fk(reference, rig, record, bpy.context.scene, graph, objects, data, qa, base, marker)
        h0 = workflow.motion_probe(neutral, bpy.context.scene, "Neutral Manual FK Surface", lambda _item: True)
        probes.append(h0)
        marker["neutral_mesh_receipt"] = receipt(h0)
        require([item.type for item in h0.modifiers] == ["ARMATURE"], "private H0 modifier chain changed")
        h0.modifiers[0].object = clone
        overlay = surface._overlay(source, record)
        output = workflow.motion_probe(source, bpy.context.scene, "Neutral Manual FK Output", lambda _item: True)
        probes.append(output)
        marker["output_receipt"] = receipt(output)
        # No evaluation/validation occurs while copying briefly adds a second original group user.
        group = overlay.node_group.copy()
        marker["node_receipt"] = {"name": group.name, "pointer": group.as_pointer()}
        strip_tags(group)
        group.name = "QA Neutral Manual FK Surface Delta"
        marker["node_receipt"]["name"] = group.name
        require(surface._node_content(group) == protected["overlay_node_content"], "private GN copy changed graph")
        output.modifiers[overlay.name].node_group = group
        group.nodes["Reference"].inputs["Object"].default_value = h0
        surface._node_verify(group, actual, h0)
        require(overlay.node_group.users == group.users == 1, "original/private overlay must each have exactly one user")
        require(qa.raw_mesh_content(h0) == protected["neutral_raw"]
                and qa.raw_mesh_content(output) == protected["source_raw"], "private copy changed raw data/Keys/weights")
        require(immutable(source, rig, neutral, reference, qa, surface) == protected, "construction changed original protected data")
        clone.update_tag(); h0.update_tag(); output.update_tag()
        bpy.context.view_layer.update()  # Declared construction evaluation, never a frame_set/cache/bake.
        graph = bpy.context.evaluated_depsgraph_get()
        marker["original_after_construction_errors_m"] = {
            name: base.delta(before[name]["points"], old_mesh(obj, graph)["points"], metres)["maximum_m"]
            for name, obj in (("O", source), ("H0", neutral), ("C", actual))}
        marker["native_C_exact_after_construction"] = old_mesh(actual, graph)["points"] == before["C"]["points"]
        marker["preserved_live_inputs"] = {"object_constraints": [surface._rna(item) for item in clone.constraints],
            "upstream_constraints": dep.constraint_rows(clone, surface._ancestors(rig, record) + [record["controls"]["waist"]], graph, surface),
            "physics_drivers": dep.physics_drivers(clone, names)}
        require(len(clone.constraints) == 1, "private object acquired another world input")
        surface._follow_proof(clone.constraints[0], rig, "")
        for name in surface._ancestors(rig, record) + [record["controls"]["waist"]]:
            require(len(clone.pose.bones[name].constraints) == 1, "private live Body/Waist follow changed")
            surface._follow_proof(clone.pose.bones[name].constraints[0], rig, name)
        for chain in record["chains"]:
            for name in chain["phys"]:
                require([surface._rna(item) for item in clone.pose.bones[name].constraints]
                        == [surface._rna(item) for item in reference.pose.bones[name].constraints], "private PHYS tracker route changed")
        require(surface._drivers(clone) == protected["neutral_drivers"], "private PHYS influence drivers differ")

        def mesh(obj, same_graph):
            row = old_mesh(obj, same_graph)
            if obj is neutral:
                began = time.perf_counter()
                candidate = {name: old_mesh(target, same_graph) for name, target in (("H0", h0), ("O", output), ("C", actual))}
                require([candidate[name]["count"] for name in ("H0", "O", "C")] == [800, 3040, 800], "candidate index/count changed")
                label = base.STAGES[len(marker["stages"])]
                entry = {"label": label, "graph_pointer": same_graph.as_pointer(),
                         "frame": bpy.context.scene.frame_current, "subframe": bpy.context.scene.frame_subframe,
                         "meshes": candidate, "current_pose_equivalence_errors_m": {
                             "H0": base.delta(row["points"], candidate["H0"]["points"], metres)["maximum_m"],
                             "O": base.delta(old_mesh(source, same_graph)["points"], candidate["O"]["points"], metres)["maximum_m"]},
                         "candidate_pose": old_pose(clone, names, same_graph),
                         "reference_pose": old_pose(reference, names, same_graph),
                         "candidate_physics_constraints": dep.constraint_rows(clone, [name for chain in record["chains"] for name in chain["phys"]], same_graph, surface),
                         "candidate_physics_drivers": dep.physics_drivers(clone, names),
                         "same_graph_extra_reads": True, "readback_seconds": time.perf_counter()-began}
                if marker["stages"]:
                    entry["from_candidate_active_baseline"] = {name: base.delta(marker["stages"][0]["meshes"][name]["points"], value["points"], metres)
                                                                 for name, value in candidate.items()}
                else:
                    marker["current_pose_equivalence_within_50um"] = max(entry["current_pose_equivalence_errors_m"].values()) <= 5e-5
                marker["stages"].append(entry)
            return row

        base.native_mesh = mesh
        return original(workflow, diagnostic, source, rig, actual, cloth, neutral, result, qa, surface, metres)
    finally:
        base.native_mesh, base.pose_row = old_mesh, old_pose
        # Retain the original public failure; component gates add evidence only.
        cleanup_errors = []
        try:
            marker["original_data_exact_before_cleanup"] = immutable(source, rig, neutral, reference, qa, surface) == protected
        except Exception as exc:
            # A partial output copy may still be a second original GN user.
            # Always remove the exact private receipts before checking that gate.
            marker["original_data_exact_before_cleanup"] = False
            marker["before_cleanup_proof_error"] = str(exc)
        try:
            marker["clone_rest_exact"] = not objects or qa.rest_content(objects[0]) == protected["neutral_rest"]
        except Exception as exc:
            marker["clone_rest_exact"] = False
            marker["clone_rest_proof_error"] = str(exc)
        for probe in reversed(probes):
            try:
                expected = marker["output_receipt"] if probe is probes[-1] and len(probes) == 2 else marker["neutral_mesh_receipt"]
                require(receipt(probe) == expected, "private mesh/Key allocation receipt changed")
                workflow.remove_motion_probe(probe)
            except Exception as exc:
                cleanup_errors.append("private mesh/Key cleanup: " + str(exc))
        if group is not None:
            try:
                require(group.users == 0 and bpy.data.node_groups.get(marker["node_receipt"]["name"]) == group
                        and group.as_pointer() == marker["node_receipt"]["pointer"], "private group acquired foreign users or changed identity")
                bpy.data.node_groups.remove(group)
            except Exception as exc:
                cleanup_errors.append("private node cleanup: " + str(exc))
        for obj in reversed(objects):
            try:
                require(bpy.data.objects.get(obj.name) == obj, "private rig object identity changed")
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception as exc:
                cleanup_errors.append("private rig cleanup: " + str(exc))
        for item in reversed(data):
            try:
                require(item.users == 0, "private FK data acquired foreign users")
                bpy.data.batch_remove(ids=(item,))
            except Exception as exc:
                cleanup_errors.append("private Rest cleanup: " + str(exc))
        marker["cleanup_errors"] = cleanup_errors
        marker["exact_helper_inventory_restored"] = inventory() == before_inventory
        marker["original_data_exact_after_cleanup"] = immutable(source, rig, neutral, reference, qa, surface) == protected
        marker["wrappers_restored"] = base.native_mesh is old_mesh and base.pose_row is old_pose
        marker["candidate_native_C_unchanged"] = (len(marker["stages"]) == 4 and all(
            row["from_candidate_active_baseline"]["C"]["maximum_m"] == 0.
            for row in marker["stages"][1:]))
        marker["component_complete"] = ([row["label"] for row in marker["stages"]] == list(base.STAGES)
            and marker.get("current_pose_equivalence_within_50um") is True
            and marker.get("native_C_exact_after_construction") is True
            and marker["candidate_native_C_unchanged"] and not cleanup_errors
            and max(marker.get("original_after_construction_errors_m", {"unknown": 1.}).values()) <= 5e-5
            and all(marker.get(key) is True for key in ("clone_rest_exact", "original_data_exact_before_cleanup",
                "original_data_exact_after_cleanup", "exact_helper_inventory_restored", "wrappers_restored")))
        require(marker["exact_helper_inventory_restored"] and marker["original_data_exact_after_cleanup"]
                and marker["clone_rest_exact"] and not cleanup_errors, "private helper cleanup/original data protection failed")


def main():
    require(bpy.app.background and "--factory-startup" in sys.argv and not bpy.data.filepath,
            "use a new empty isolated factory background child")
    own = sha(Path(__file__))
    require(sha(BASE) == BASE_SHA and sha(DEPENDENCY) == DEPENDENCY_SHA, "pinned component helpers changed")
    base = load(BASE, "private_neutral_fk_stage_base")
    dep = load(DEPENDENCY, "private_neutral_fk_dependency_helpers")
    old = base.observed_roundtrip
    base.observed_roundtrip = lambda original, workflow, diagnostic, *values: component(
        lambda *_values: old(original, *_values), base, dep, workflow, diagnostic, *values)
    try:
        return base.main()  # Complete unchanged run60/cache/public 50um/exit/reload/raw/source/disk gates.
    finally:
        base.observed_roundtrip = old
        require(sha(Path(__file__)) == own and sha(BASE) == BASE_SHA and sha(DEPENDENCY) == DEPENDENCY_SHA,
                "component source changed during full workflow")
        print(json.dumps({"neutral_manual_fk_source_exact": True, "sha256": own,
                          "base_sha256": BASE_SHA, "dependency_sha256": DEPENDENCY_SHA,
                          "production_effect_accepted": False}), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
