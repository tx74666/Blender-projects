"""Read Blender references without saving them or executing embedded scripts.

Run with Blender --background --factory-startup --disable-autoexec --python
this_file.py -- OUTPUT_DIRECTORY SOURCE.blend [SOURCE.blend ...].
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def simple(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, bpy.types.ID):
        return value.name
    try:
        return [simple(item) for item in value]
    except TypeError:
        return str(value)


def fields(value):
    if value is None:
        return None
    result = {}
    for prop in value.bl_rna.properties:
        if prop.identifier == "rna_type" or prop.type == "COLLECTION":
            continue
        if prop.type == "POINTER" and prop.identifier not in (
            "object", "target", "pole_target", "curve", "rest_shape_key",
            "collection", "collision_collection", "mirror_object", "node_group",
        ):
            continue
        try:
            result[prop.identifier] = simple(getattr(value, prop.identifier))
        except (AttributeError, TypeError, ValueError):
            pass
    return result


def drivers(owner):
    animation = getattr(owner, "animation_data", None)
    if not animation:
        return []
    return [
        {
            "path": fc.data_path,
            "index": fc.array_index,
            "expression": fc.driver.expression,
            "type": fc.driver.type,
            "variables": [
                {"name": var.name, "type": var.type,
                 "targets": [fields(target) for target in var.targets]}
                for var in fc.driver.variables
            ],
        }
        for fc in animation.drivers
    ]


def constraint_fields(constraint):
    result = fields(constraint)
    if constraint.type == "ARMATURE":
        result["targets"] = [fields(target) for target in constraint.targets]
    return result


def topology(mesh):
    adjacency = [set() for _ in mesh.vertices]
    uses = {tuple(sorted(edge.vertices)): 0 for edge in mesh.edges}
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    faces_by_size = {}
    for face in mesh.polygons:
        size = len(face.vertices)
        faces_by_size[size] = faces_by_size.get(size, 0) + 1
        for edge in face.edge_keys:
            uses[tuple(sorted(edge))] += 1
    def components(vertices, links):
        pending = set(vertices)
        result = []
        while pending:
            seed = pending.pop()
            visited = {seed}
            stack = [seed]
            while stack:
                for neighbor in links[stack.pop()]:
                    if neighbor in pending:
                        pending.remove(neighbor)
                        visited.add(neighbor)
                        stack.append(neighbor)
            result.append(sorted(visited))
        return result
    boundary_edges = [edge for edge, count in uses.items() if count == 1]
    boundary_links = [set() for _ in mesh.vertices]
    for a, b in boundary_edges:
        boundary_links[a].add(b)
        boundary_links[b].add(a)
    return {
        "component_sizes": sorted([len(c) for c in components(range(len(mesh.vertices)), adjacency)], reverse=True),
        "faces_by_size": faces_by_size,
        "wire_edges": sum(count == 0 for count in uses.values()),
        "nonmanifold_edges_more_than_two_faces": sum(count > 2 for count in uses.values()),
        "boundary_components": [
            {"vertices": c, "closed_loop": all(len(boundary_links[v]) == 2 for v in c),
             "local_bounds": [[min(mesh.vertices[v].co[i] for v in c), max(mesh.vertices[v].co[i] for v in c)] for i in range(3)]}
            for c in components([i for i, links in enumerate(boundary_links) if links], boundary_links)
        ],
        "vertices": [list(v.co) for v in mesh.vertices],
        "edges": [list(e.vertices) for e in mesh.edges],
        "polygons": [list(p.vertices) for p in mesh.polygons],
    }


def inspect_object(obj):
    result = {
        "name": obj.name, "type": obj.type,
        "collections": [coll.name for coll in obj.users_collection],
        "parent": obj.parent.name if obj.parent else None,
        "parent_type": obj.parent_type, "parent_bone": obj.parent_bone,
        "location": list(obj.location), "scale": list(obj.scale),
        "matrix_world": [list(row) for row in obj.matrix_world],
        "hide_viewport": obj.hide_viewport, "hide_render": obj.hide_render,
        "modifiers": [], "constraints": [constraint_fields(c) for c in obj.constraints],
        "drivers": drivers(obj),
        "custom_property_names": list(obj.keys()),
    }
    for modifier in obj.modifiers:
        item = fields(modifier)
        if modifier.type == "CLOTH":
            item["cloth_settings"] = fields(modifier.settings)
            item["cloth_collision_settings"] = fields(modifier.collision_settings)
            item["point_cache"] = fields(modifier.point_cache)
        result["modifiers"].append(item)
    if obj.type == "MESH":
        mesh = obj.data
        groups = [{"name": vg.name, "index": vg.index, "vertices": 0,
                   "weight_sum": 0.0, "min": None, "max": None}
                  for vg in obj.vertex_groups]
        for vertex in mesh.vertices:
            for influence in vertex.groups:
                group = groups[influence.group]
                weight = influence.weight
                group["vertices"] += 1
                group["weight_sum"] += weight
                group["min"] = weight if group["min"] is None else min(group["min"], weight)
                group["max"] = weight if group["max"] is None else max(group["max"], weight)
        points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
        result["mesh"] = {
            "vertices": len(mesh.vertices), "edges": len(mesh.edges),
            "polygons": len(mesh.polygons), "vertex_groups": groups,
            "world_bounds": [[min(p[i] for p in points), max(p[i] for p in points)]
                             for i in range(3)] if points else [],
            "shape_keys": [key.name for key in mesh.shape_keys.key_blocks]
                          if mesh.shape_keys else [],
            "shape_key_drivers": drivers(mesh.shape_keys),
            "materials": [mat.name if mat else None for mat in mesh.materials],
        }
        if any(word in obj.name.lower() for word in ("dress", "skirt", "tracktarget", "body_col")):
            result["mesh"]["topology"] = topology(mesh)
    elif obj.type == "ARMATURE":
        result["armature"] = {
            "collections": [collection.name for collection in obj.data.collections_all],
            "bones": [
                {"name": bone.name, "parent": bone.parent.name if bone.parent else None,
                 "head": list(bone.head_local), "tail": list(bone.tail_local),
                 "deform": bone.use_deform, "connected": bone.use_connect,
                 "collections": [collection.name for collection in bone.collections],
                 "constraints": [constraint_fields(c) for c in obj.pose.bones[bone.name].constraints],
                 "custom_shape": simple(obj.pose.bones[bone.name].custom_shape),
                 "custom_properties": {key: simple(value) for key, value in obj.pose.bones[bone.name].items()}}
                for bone in obj.data.bones
            ],
        }
    elif obj.type == "CURVE":
        result["curve"] = {"dimensions": obj.data.dimensions,
                           "splines": [{"type": s.type, "points": len(s.points),
                                        "bezier_points": len(s.bezier_points),
                                        "cyclic": s.use_cyclic_u} for s in obj.data.splines]}
    if obj.data:
        result["data_drivers"] = drivers(obj.data)
    return result


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    output_dir = Path(args[0]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    for filename in args[1:]:
        source = Path(filename).resolve()
        before = digest(source)
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
        report = {
            "source": str(source), "sha256": before,
            "blender_version": bpy.app.version_string,
            "scenes": [{"name": s.name, "frame": s.frame_current,
                        "frame_start": s.frame_start, "frame_end": s.frame_end,
                        "gravity": list(s.gravity)} for s in bpy.data.scenes],
            "collections": [{"name": coll.name,
                             "children": [child.name for child in coll.children],
                             "objects": [obj.name for obj in coll.objects]}
                            for coll in bpy.data.collections],
            "texts": [{"name": t.name, "lines": len(t.lines), "use_module": t.use_module,
                       "source_text": t.as_string() if not source.stem == "X" else None}
                      for t in bpy.data.texts],
            "objects": [inspect_object(obj) for obj in bpy.data.objects],
        }
        report["source_unchanged"] = digest(source) == before
        assert report["source_unchanged"], f"Source changed during inspection: {source}"
        output = output_dir / (source.stem + "_inventory.json")
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("REFERENCE_INVENTORY", json.dumps({
            "source": str(source), "output": str(output),
            "objects": len(report["objects"]), "texts": [t["name"] for t in report["texts"]],
            "collections": [coll["name"] for coll in report["collections"]],
            "source_unchanged": report["source_unchanged"],
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
