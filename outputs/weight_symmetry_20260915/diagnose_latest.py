"""Read-only comparison of two frozen artist inputs; never save a blend file."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import struct
import sys
import types

import bpy
from mathutils.kdtree import KDTree

ROOT = Path(r"D:\Blender\Projects\Character\X\outputs\weight_symmetry_20260915")
CANONICAL = Path(r"D:\MyRepository\Blender-addons-by-Randy\addons\character_designer")
INPUTS = {
    "old": (ROOT / "X_saved_input.blend", "5FB5B96E5C629340FEC5CC2696E0861A5C0884A1F1E03BBFEAF9C608CB96CA79"),
    "latest": (ROOT / "X_saved_input_104450.blend", "E76E49B66A26954BE603BDB321EF841901FBD013E124282A0247303EEDA82492"),
}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


for path, expected in INPUTS.values():
    assert file_hash(path) == expected, f"Frozen input hash changed: {path}"

pkg = types.ModuleType("latest_input_character_designer")
pkg.__path__ = [str(CANONICAL)]
sys.modules[pkg.__name__] = pkg
spec = importlib.util.spec_from_file_location(pkg.__name__ + ".weight_symmetry", CANONICAL / "weight_symmetry.py")
ws = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ws
spec.loader.exec_module(ws)

# Reuse only the read-only snapshot function definitions from the prior validator.
# Its loading, planning, applying, and saving code is never executed.
definitions = {"digest", "scalar", "properties", "rna_settings", "geometry", "stable_scene_state"}
tree = ast.parse((ROOT / "validate_surface_character.py").read_text(encoding="utf8"))
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in definitions]
assert {node.name for node in nodes} == definitions
exec(compile(ast.Module(body=nodes, type_ignores=[]), "readonly_snapshot_definitions", "exec"))


def basic_geometry_digest(obj):
    h = hashlib.sha256()
    for vertex in obj.data.vertices:
        h.update(struct.pack("<3f", *vertex.co))
    for edge in obj.data.edges:
        h.update(struct.pack("<2I", *edge.vertices))
    for polygon in obj.data.polygons:
        h.update(struct.pack("<I", len(polygon.vertices)))
        h.update(struct.pack("<" + "I" * len(polygon.vertices), *polygon.vertices))
    if obj.data.shape_keys:
        for block in obj.data.shape_keys.key_blocks:
            h.update(block.name.encode())
            for vertex in block.data:
                h.update(struct.pack("<3f", *vertex.co))
    return h.hexdigest()


def snapshot():
    obj = bpy.data.objects["Cosha"]
    arm = bpy.data.objects["CoshaRig"]
    mesh = obj.data
    shapes = mesh.shape_keys
    bone_rest = tuple((b.name, b.parent.name if b.parent else None, b.use_deform,
                       tuple(b.head_local), tuple(b.tail_local), tuple(tuple(r) for r in b.matrix_local), properties(b))
                      for b in arm.data.bones)
    bone_pose = tuple((b.name, b.rotation_mode, tuple(b.location), tuple(b.scale), tuple(b.rotation_euler),
                       tuple(b.rotation_quaternion), tuple(b.rotation_axis_angle), properties(b),
                       tuple((c.name, c.type, rna_settings(c)) for c in b.constraints)) for b in arm.pose.bones)
    evaluated_pose = tuple((b.name, tuple(tuple(r) for r in b.matrix)) for b in arm.pose.bones)
    transforms = tuple((o.name, tuple(tuple(r) for r in o.matrix_world)) for o in (obj, arm))
    all_groups = ws._capture_vertex_groups(obj)
    memberships = tuple(tuple((g.group, g.weight) for g in vertex.groups) for vertex in mesh.vertices)
    categories = {
        "vertex_coordinates": digest(tuple(tuple(v.co) for v in mesh.vertices)),
        "edges": digest(tuple(tuple(e.vertices) for e in mesh.edges)),
        "polygons": digest(tuple((tuple(p.vertices), p.material_index, p.use_smooth) for p in mesh.polygons)),
        "uv_layers": digest(tuple((uv.name, tuple(tuple(v.uv) for v in uv.data)) for uv in mesh.uv_layers)),
        "shape_keys": digest(None if shapes is None else (shapes.name, shapes.use_relative, shapes.eval_time,
            tuple((key.name, key.value, key.mute, key.slider_min, key.slider_max, key.vertex_group,
                   key.relative_key.name if key.relative_key else None, tuple(tuple(v.co) for v in key.data))
                  for key in shapes.key_blocks))),
        "geometry_full": digest(geometry(mesh)),
        "geometry_basic": basic_geometry_digest(obj),
        "all_vertex_groups": digest(all_groups),
        "raw_vertex_memberships": digest(memberships),
        "armature_rest": digest(bone_rest),
        "armature_pose": digest(bone_pose),
        "armature_evaluated_pose": digest(evaluated_pose),
        "mesh_and_armature_world_transforms": digest(transforms),
    }
    deform_names = {b.name for b in arm.data.bones if b.use_deform}
    def weights(index):
        return {obj.vertex_groups[g.group].name: float(g.weight) for g in mesh.vertices[index].groups}
    zero_all = [v.index for v in mesh.vertices if not v.groups]
    zero_positive = [v.index for v in mesh.vertices if not any(g.weight > ws.WEIGHT_EPSILON for g in v.groups)]
    zero_deform = [v.index for v in mesh.vertices if sum(g.weight for g in v.groups
                   if obj.vertex_groups[g.group].name in deform_names) <= ws.WEIGHT_EPSILON]
    return {
        "mesh": obj.name, "armature": arm.name, "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges), "polygon_count": len(mesh.polygons), "digests": categories,
        "stable_scene": stable_scene_state(obj.name),
        "saved_context": {"mode": obj.mode, "active_object": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
                          "active_group": obj.vertex_groups.active.name if obj.vertex_groups.active else None,
                          "selected_vertices": [v.index for v in mesh.vertices if v.select]},
        "zero_all_memberships": zero_all, "zero_positive_all_groups": zero_positive, "zero_deform_budget": zero_deform,
        "hand_vertices": [{"vertex": i, "local": list(mesh.vertices[i].co), "all_weights": weights(i),
            "deform_total": sum(w for n, w in weights(i).items() if n in deform_names)} for i in (3273, 3396, 923)],
    }


def diagnose_groups():
    obj = bpy.data.objects["Cosha"]
    arm = bpy.data.objects["CoshaRig"]
    coords = [v.co.copy() for v in obj.data.vertices]
    state = ws._state_map(ws._capture_vertex_groups(obj))
    tol = ws._automatic_tolerance(obj)
    adj = [set() for _ in coords]
    for edge in obj.data.edges:
        a, b = edge.vertices
        adj[a].add(b)
        adj[b].add(a)
    result = {}
    for stem in ("upper_arm", "forearm", "hand", "shoulder"):
        for suffix in ("L", "R"):
            name = f"{stem}.{suffix}"
            opposite = ws._strict_opposite_name(name)
            side = ws._bone_source_side(obj, arm, name, opposite, tol)
            si, ti, ci = ws._classify_mesh_halves(obj, side, tol)
            weights = ws._weight_map(state[name])
            support = {i for i, w in weights.items() if w > ws.WEIGHT_EPSILON}
            unvisited = set(support)
            component_counts = []
            wrong_components = []
            while unvisited:
                start = min(unvisited)
                unvisited.remove(start)
                component = [start]
                pending = [start]
                while pending:
                    current = pending.pop()
                    following = adj[current] & unvisited
                    unvisited.difference_update(following)
                    pending.extend(following)
                    component.extend(following)
                component_counts.append(len(component))
                if all(coords[i].x * side < -tol for i in component):
                    wrong_components.append(sorted(component))
            tree = KDTree(len(ti))
            for i in ti:
                tree.insert(coords[i], i)
            tree.balance()
            source_support = tuple(i for i in si if i in support)
            misses, ambiguous, exact = [], [], []
            used = set()
            for i in source_support:
                reflected = coords[i].copy()
                reflected.x *= -1
                hits = sorted(tree.find_range(reflected, tol), key=lambda h: (h[2], h[1]))
                if not hits:
                    misses.append(i)
                elif len(hits) != 1 or hits[0][1] in used:
                    ambiguous.append(i)
                else:
                    used.add(hits[0][1])
                    exact.append((i, hits[0][1]))
            try:
                ws._spatial_pairs(obj, source_support, ti, tol)
                spatial_result = "ok"
            except Exception as error:
                spatial_result = f"{type(error).__name__}: {error}"
            result[name] = {"bone_side_sign": side, "positive_support_count": len(support),
                "positive_source_count": len(support & set(si)), "positive_opposite_count": len(support & set(ti)),
                "positive_center_count": len(support & set(ci)), "component_sizes": component_counts,
                "wrong_side_island_count": len(wrong_components), "wrong_side_islands": wrong_components,
                "unmatched_count": len(misses), "unmatched_vertices": misses, "ambiguous_vertices": ambiguous,
                "exact_pair_count": len(exact), "canonical_spatial_result": spatial_result}
    return {"tolerance": tol, "groups": result}


report = {"blender_version": bpy.app.version_string,
          "canonical_algorithm_sha256": file_hash(CANONICAL / "weight_symmetry.py"), "inputs": {}}
for label, (path, expected) in INPUTS.items():
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    initial = snapshot()
    diagnosis = diagnose_groups()
    assert snapshot() == initial, "Read-only diagnosis changed in-memory state"
    report["inputs"][label] = {"path": str(path), "sha256": expected, **initial, **diagnosis,
                               "in_memory_unchanged": True}

old, latest = report["inputs"]["old"], report["inputs"]["latest"]
matches = {key: old["digests"][key] == value for key, value in latest["digests"].items()}
scene_names = sorted(set(old["stable_scene"]) | set(latest["stable_scene"]))
scene_changed = [name for name in scene_names if old["stable_scene"].get(name) != latest["stable_scene"].get(name)]
prior = json.loads((ROOT / "saved_input_diagnostic.json").read_text(encoding="utf8"))
report["comparison"] = {
    "digests_match": matches,
    "changed_scene_objects": scene_changed,
    "all_checked_scene_state_identical": not scene_changed and all(matches.values()),
    "diagnostic_groups_identical": old["groups"] == latest["groups"],
    "zero_budget_sets_identical": old["zero_deform_budget"] == latest["zero_deform_budget"],
    "old_report_geometry_digest_matches": old["digests"]["geometry_basic"] == prior["geometry_digest_before"],
    "old_report_all_groups_digest_matches": old["digests"]["all_vertex_groups"] == prior["groups_digest_before"],
    "review_weight_result_reusable_for_latest_geometry_weights_rig": all(matches[k] for k in
        ("geometry_full", "all_vertex_groups", "armature_rest", "armature_pose", "mesh_and_armature_world_transforms")),
    "saved_context_identical": old["saved_context"] == latest["saved_context"],
    "interpretation_scope": "Snapshot includes mesh topology, coordinates, material assignments, UVs, shape keys, all vertex groups, object transforms/modifiers/constraints/custom properties, armature rest/pose/constraints, scene frame and properties. It does not establish equality of every Blender datablock or UI setting.",
}
report["frozen_files_unchanged"] = {label: file_hash(path) == expected for label, (path, expected) in INPUTS.items()}
assert all(report["frozen_files_unchanged"].values())
(ROOT / "latest_input_comparison.json").write_text(json.dumps(report, indent=2), encoding="utf8")
print(json.dumps({"comparison": report["comparison"], "latest_sha256": latest["sha256"],
                  "latest_groups": latest["groups"], "zero_all_memberships": latest["zero_all_memberships"],
                  "zero_positive_all_groups": latest["zero_positive_all_groups"],
                  "zero_deform_budget": latest["zero_deform_budget"], "hand_vertices": latest["hand_vertices"],
                  "frozen_files_unchanged": report["frozen_files_unchanged"]}, indent=2))
