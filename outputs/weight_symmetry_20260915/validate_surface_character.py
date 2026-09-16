"""Validate canonical surface weights on a frozen artist file and save a review.

Never changes the user's X.blend. Opens only the frozen saved input, preserves
the saved pose, and writes the explicitly named standalone review copy.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import sys
import types

import bpy

ROOT = Path(r"D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915")
INPUT = ROOT / "X_saved_input.blend"
REVIEW = ROOT / "X_upper_arm_weights_review.blend"
REPORT = ROOT / "surface_character_validation.json"
EXPECTED = "5FB5B96E5C629340FEC5CC2696E0861A5C0884A1F1E03BBFEAF9C608CB96CA79"
CANONICAL = Path(r"D:\MyRepository\Blender-addons-by-Randy\addons\character_designer")
arguments = argparse.ArgumentParser(description=__doc__)
arguments.add_argument("--review", type=Path, default=REVIEW)
arguments.add_argument("--report", type=Path, default=REPORT)
options = arguments.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
REVIEW = options.review.resolve()
REPORT = options.report.resolve()
assert REVIEW != INPUT.resolve() and REPORT != INPUT.resolve()
assert REVIEW.suffix.lower() == ".blend" and REPORT.suffix.lower() == ".json"

def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()

assert file_digest(INPUT) == EXPECTED
assert not REVIEW.exists(), "Refuse to overwrite an existing review artifact"
pkg = types.ModuleType("surface_character_canonical")
pkg.__path__ = [str(CANONICAL)]
sys.modules[pkg.__name__] = pkg
spec = importlib.util.spec_from_file_location(pkg.__name__ + ".weight_surface", CANONICAL / "weight_surface.py")
surface = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = surface
spec.loader.exec_module(surface)
ws = surface.ws

def scalar(value):
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, bpy.types.ID):
        return (value.bl_rna.identifier, value.name_full)
    if hasattr(value, "to_dict"):
        return tuple(sorted((k, scalar(v)) for k, v in value.to_dict().items()))
    if isinstance(value, dict):
        return tuple(sorted((k, scalar(v)) for k, v in value.items()))
    try:
        return tuple(scalar(v) for v in value)
    except TypeError:
        return str(value)

def properties(owner):
    return tuple(sorted((key, scalar(owner[key])) for key in owner.keys() if key != "_RNA_UI"))

def rna_settings(owner):
    result = []
    for prop in owner.bl_rna.properties:
        if prop.identifier == "rna_type" or prop.is_readonly:
            continue
        if prop.type == "COLLECTION":
            continue
        try:
            result.append((prop.identifier, scalar(getattr(owner, prop.identifier))))
        except (AttributeError, TypeError, ValueError):
            continue
    return tuple(result)

def geometry(mesh):
    shapes = mesh.shape_keys
    return (
        tuple(tuple(v.co) for v in mesh.vertices),
        tuple(tuple(e.vertices) for e in mesh.edges),
        tuple((tuple(p.vertices), p.material_index, p.use_smooth) for p in mesh.polygons),
        tuple((uv.name, tuple(tuple(v.uv) for v in uv.data)) for uv in mesh.uv_layers),
        tuple(material.name_full if material else None for material in mesh.materials),
        None if shapes is None else (
            shapes.name, shapes.use_relative, shapes.eval_time,
            tuple((key.name, key.value, key.mute, key.slider_min, key.slider_max,
                   key.vertex_group, key.relative_key.name if key.relative_key else None,
                   tuple(tuple(v.co) for v in key.data)) for key in shapes.key_blocks),
        ),
    )

def stable_scene_state(target_name):
    result = {}
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        data = (
            obj.type, obj.parent.name if obj.parent else None, obj.parent_type, obj.parent_bone,
            tuple(obj.location), tuple(obj.rotation_euler), tuple(obj.rotation_quaternion),
            tuple(obj.rotation_axis_angle), tuple(obj.scale), obj.rotation_mode,
            tuple(tuple(r) for r in obj.matrix_parent_inverse),
            properties(obj),
            tuple((m.name, m.type, rna_settings(m)) for m in obj.modifiers),
            tuple((c.name, c.type, rna_settings(c)) for c in obj.constraints),
        )
        if obj.type == "MESH":
            data += (geometry(obj.data),)
            if obj.name != target_name:
                data += (ws._capture_vertex_groups(obj),)
        elif obj.type == "ARMATURE":
            data += (
                tuple((b.name, b.parent.name if b.parent else None, b.use_deform,
                       tuple(b.head_local), tuple(b.tail_local),
                       tuple(tuple(r) for r in b.matrix_local), properties(b))
                      for b in obj.data.bones),
                tuple((b.name, b.rotation_mode, tuple(b.location), tuple(b.scale),
                       tuple(b.rotation_euler), tuple(b.rotation_quaternion),
                       tuple(b.rotation_axis_angle), properties(b),
                       tuple((c.name, c.type, rna_settings(c)) for c in b.constraints))
                      for b in obj.pose.bones),
            )
        result[obj.name] = digest(data)
    result["__scene__"] = digest(tuple((s.name, s.frame_current, s.frame_subframe,
                                        s.frame_start, s.frame_end, properties(s)) for s in bpy.data.scenes))
    return result

def group_maps(states):
    return {s.name: dict(s.weights) for s in states}

def summarize_plan(plan):
    return {"source_names": plan.source_names, "target_names": plan.target_names,
            "sampled_count": plan.sampled_count, "affected_count": len(plan.affected_indices),
            "affected_indices": plan.affected_indices,
            "max_sample_distance": plan.max_sample_distance, "distance_limit": plan.distance_limit}

report = {"input": str(INPUT), "input_sha256": EXPECTED,
          "runtime_sha256": file_digest(CANONICAL / "weight_surface.py"),
          "review": str(REVIEW)}

def write_report():
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf8")

bpy.ops.wm.open_mainfile(filepath=str(INPUT), load_ui=False)
obj = bpy.data.objects["Cosha"]
arm = bpy.data.objects["CoshaRig"]
original_groups = ws._capture_vertex_groups(obj)
original_stable = stable_scene_state(obj.name)
original_active = obj.vertex_groups.active_index
original_mode = obj.mode
report["original_mode"] = original_mode
report["original_active_group"] = obj.vertex_groups[original_active].name
report["initial_zero_budget_vertices"] = [
    {"vertex": index, "local": list(obj.data.vertices[index].co),
     "all_memberships": {obj.vertex_groups[g.group].name: g.weight for g in obj.data.vertices[index].groups}}
    for index in (3273, 923, 3396)
]
report["dry_runs"] = {}
for name in ("forearm.L", "hand.L"):
    try:
        planned = surface.build_surface_plan_for_sources(bpy.context, obj, arm, (name,))
        report["dry_runs"][name] = {"status": "planned_only", **summarize_plan(planned)}
    except ws.WeightSymmetryError as error:
        report["dry_runs"][name] = {"status": "refused_without_writes", "error": str(error),
                                   "vertex_indices": error.vertex_indices}
    assert ws._capture_vertex_groups(obj) == original_groups
    assert stable_scene_state(obj.name) == original_stable
write_report()
try:
    plan = surface.build_surface_plan_for_sources(bpy.context, obj, arm, ("upper_arm.L",))
except ws.WeightSymmetryError as error:
    report["upper_arm"] = {"status": "refused_without_writes", "error": str(error),
                           "vertex_indices": error.vertex_indices}
    report["input_file_unchanged"] = file_digest(INPUT) == EXPECTED
    write_report()
    print(json.dumps(report, indent=2))
    raise
report["upper_arm"] = {"status": "planned", **summarize_plan(plan)}
assert ws._capture_vertex_groups(obj) == original_groups
assert stable_scene_state(obj.name) == original_stable

# Fail after all writes, then prove exact rollback before applying normally.
original_verify = surface._verify_surface_state
def injected_failure(mesh_obj, applied_plan):
    assert ws._capture_vertex_groups(mesh_obj) != applied_plan.group_snapshot
    raise RuntimeError("Injected real-character verification failure")
surface._verify_surface_state = injected_failure
try:
    try:
        surface.apply_surface_plan(plan)
    except ws.WeightSymmetryError as error:
        assert "rolled back" in str(error)
        report["rollback_error"] = str(error)
    else:
        raise AssertionError("Injected verification failure did not refuse")
finally:
    surface._verify_surface_state = original_verify
assert ws._capture_vertex_groups(obj) == original_groups
assert stable_scene_state(obj.name) == original_stable
report["rollback_exact"] = True

surface.apply_surface_plan(plan)
after_groups = ws._capture_vertex_groups(obj)
assert stable_scene_state(obj.name) == original_stable
assert obj.vertex_groups.active_index == original_active
assert obj.mode == original_mode
before_map, after_map = group_maps(original_groups), group_maps(after_groups)
deform_names = {b.name for b in arm.data.bones if b.use_deform}
tol = ws._automatic_tolerance(obj)
source, target, center = ws._classify_mesh_halves(obj, plan.source_side, tol)
source_center = set(source) | set(center)
affected = set(plan.affected_indices)
all_names = set(before_map) | set(after_map)
all_indices = set(range(len(obj.data.vertices)))
changes = {}
for name in sorted(all_names):
    old, new = before_map.get(name, {}), after_map.get(name, {})
    changed = [i for i in sorted(set(old) | set(new)) if old.get(i) != new.get(i)]
    if changed:
        assert name in deform_names, f"Non-Deform group changed: {name}"
        assert not set(changed) & source_center, f"Source/center changed: {name}"
        assert set(changed) <= affected, f"Weight changed outside destination region: {name}"
        changes[name] = {"changed_memberships": len(changed), "vertices": changed}
budget_deltas = []
for index in all_indices:
    before_total = sum(before_map.get(n, {}).get(index, 0) for n in deform_names)
    after_total = sum(after_map.get(n, {}).get(index, 0) for n in deform_names)
    delta = abs(after_total - before_total)
    assert delta <= ws.WEIGHT_TOLERANCE, f"Deform budget changed at {index}: {delta}"
    budget_deltas.append(delta)
for index in (3273, 923, 3396):
    assert all(before_map.get(n, {}).get(index) == after_map.get(n, {}).get(index) for n in all_names)
report.update({"changed_groups": changes, "protected_source_center_unchanged": True,
               "non_deform_groups_unchanged": True, "outside_affected_vertices_unchanged": True,
               "geometry_shape_keys_rest_pose_other_assets_unchanged": True,
               "max_deform_budget_delta": max(budget_deltas),
               "zero_budget_hand_region_unchanged": True,
               "before_groups_digest": digest(original_groups), "after_groups_digest": digest(after_groups),
               "stable_scene_before": original_stable})
repeat = surface.build_surface_plan_for_sources(bpy.context, obj, arm, ("upper_arm.L",))
assert not repeat.affected_indices, f"Repeat would change {repeat.affected_indices}"
surface.apply_surface_plan(repeat)
assert ws._capture_vertex_groups(obj) == after_groups
assert stable_scene_state(obj.name) == original_stable
report["repeat_exact_noop"] = True
report["upper_arm"]["status"] = "applied_and_verified"
write_report()

bpy.ops.wm.save_as_mainfile(filepath=str(REVIEW), check_existing=False)
assert file_digest(INPUT) == EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(REVIEW), load_ui=False)
reopened = bpy.data.objects["Cosha"]
assert ws._capture_vertex_groups(reopened) == after_groups
reopened_stable = stable_scene_state(reopened.name)
assert reopened_stable == original_stable, f"Reopen changed protected assets: {[n for n in original_stable if original_stable[n] != reopened_stable.get(n)]}"
assert reopened.vertex_groups.active_index == original_active
assert reopened.mode == original_mode
report.update({"saved_reopened_exact": True, "input_file_unchanged": file_digest(INPUT) == EXPECTED,
               "review_sha256": file_digest(REVIEW), "status": "PASS"})
write_report()
print(json.dumps({key: value for key, value in report.items() if key != "stable_scene_before"}, indent=2))
