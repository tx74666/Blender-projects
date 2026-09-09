"""Read-only scene inventory for hair attachment/removal design; never saves."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

CANONICAL = Path("D:/MyRepository/Blender-addons-by-Randy")
sys.path.insert(0, str(CANONICAL / "addons"))
from character_designer import hair_bones_groups as groups
from character_designer import hair_bones_rig as rig
from character_designer import hair_bones_variants as variants

target = Path(bpy.data.filepath)
before_hash = hashlib.sha256(target.read_bytes()).hexdigest()


def point(vector):
    return [round(float(value), 7) for value in vector]


def bounds(obj, indices=None):
    chosen = tuple(range(len(obj.data.vertices))) if indices is None else tuple(indices)
    if not chosen:
        return None
    coords = [obj.matrix_world @ obj.data.vertices[index].co for index in chosen]
    return {"count": len(chosen), "min": [min(c[axis] for c in coords) for axis in range(3)],
            "max": [max(c[axis] for c in coords) for axis in range(3)],
            "mean": point(sum(coords, Vector()) / len(coords))}


def reference(value):
    return value.name if isinstance(value, bpy.types.ID) else str(value)


def modifiers(obj):
    result = []
    for modifier in obj.modifiers:
        value = {"name": modifier.name, "type": modifier.type,
                 "viewport": modifier.show_viewport, "render": modifier.show_render}
        if modifier.type == "ARMATURE":
            value.update(object=modifier.object.name if modifier.object else None,
                         volume=modifier.use_deform_preserve_volume, vertex_group=modifier.vertex_group)
        if modifier.type == "MIRROR":
            value.update(axes=list(modifier.use_axis), mirror_object=modifier.mirror_object.name if modifier.mirror_object else None,
                         flip_groups=modifier.use_mirror_vertex_groups, merge=modifier.use_mirror_merge,
                         threshold=modifier.merge_threshold)
        result.append(value)
    return result


def weighted(obj, indices):
    names = {group.index: group.name for group in obj.vertex_groups}
    counts, full, summed, unweighted, totals = {}, {}, {}, [], []
    for index in indices:
        entries = [(names[entry.group], float(entry.weight)) for entry in obj.data.vertices[index].groups if entry.weight > 1e-7]
        total = sum(weight for _, weight in entries)
        totals.append(total)
        if not entries:
            unweighted.append(index)
        for name, weight in entries:
            counts[name] = counts.get(name, 0) + 1
            summed[name] = summed.get(name, 0.0) + weight
            if abs(weight - 1.0) < 1e-6:
                full[name] = full.get(name, 0) + 1
    return {"vertex_count": len(indices), "nonzero_counts": counts, "full_weight_counts": full,
            "sum_by_group": summed, "unweighted_count": len(unweighted),
            "unweighted_indices": unweighted, "total_weight_range": [min(totals), max(totals)] if totals else None}


def components(obj, chosen):
    adjacency = {index: set() for index in chosen}
    for edge in obj.data.edges:
        a, b = edge.vertices
        if a in chosen and b in chosen:
            adjacency[a].add(b)
            adjacency[b].add(a)
    remaining, result = set(chosen), []
    while remaining:
        pending = [remaining.pop()]
        component = set(pending)
        while pending:
            added = adjacency[pending.pop()] & remaining
            remaining.difference_update(added)
            component.update(added)
            pending.extend(added)
        result.append(component)
    return sorted(result, key=len, reverse=True)


source = bpy.data.objects.get("Hair3")
assert source and source.type == "MESH"
raw_capture = source.get(groups.GROUPS_KEY)
capture = json.loads(raw_capture) if raw_capture else None
native_strands = capture.get("strands", []) if capture else []
if not native_strands:
    # Metadata can live on a source reached through a version reference.
    native_strands = []
covered = {index for strand in native_strands for index in strand["vertices"]}
root_indices = {index for strand in native_strands for index in strand["layers"][0]}
outside = set(range(len(source.data.vertices))) - covered
boundary = []
for edge in source.data.edges:
    a, b = edge.vertices
    if (a in covered) != (b in covered):
        boundary.append((a, b) if a in outside else (b, a))

scene_meshes = []
hair_details = []
for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    scene_meshes.append({"name": obj.name, "vertices": len(obj.data.vertices), "bounds": bounds(obj),
                         "parent": obj.parent.name if obj.parent else None,
                         "groups": len(obj.vertex_groups)})
    if "hair" not in obj.name.lower() and "cap" not in obj.name.lower():
        continue
    record = rig._read_records(obj) if obj.get(rig.RECORD_KEY) else None
    item = {"name": obj.name, "data": obj.data.name, "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons), "bounds": bounds(obj),
            "collections": [c.name for c in obj.users_collection], "parent": obj.parent.name if obj.parent else None,
            "parent_type": obj.parent_type, "parent_bone": obj.parent_bone,
            "modifiers": modifiers(obj), "group_names": [g.name for g in obj.vertex_groups],
            "own_properties": {key: reference(value) for key, value in obj.items()
                               if "character_designer_hair" in key and key not in (rig.RECORD_KEY, groups.GROUPS_KEY)},
            "source": variants.source_for(obj).name if variants.source_for(obj) else None,
            "visible": obj.visible_get(), "capture_strands": len(json.loads(obj[groups.GROUPS_KEY])["strands"]) if obj.get(groups.GROUPS_KEY) else None,
            "record": {key: value for key, value in record.items() if key != "chains"} if record else None,
            "chain_summary": [{"bones": c["bones"], "member_count": len(c.get("members", [])),
                               "side": c.get("mirror_side"), "vertex_count": len(c["vertices"])} for c in record["chains"]] if record else None}
    if len(obj.data.vertices) == len(source.data.vertices) and (obj is source or variants.source_for(obj) is source):
        item["captured_weights"] = weighted(obj, sorted(covered))
        item["uncaptured_weights"] = weighted(obj, sorted(outside))
        item["capture_root_weights"] = weighted(obj, sorted(root_indices))
    hair_details.append(item)

armatures = []
for obj in bpy.data.objects:
    if obj.type != "ARMATURE":
        continue
    head = rig._head_bone(obj)
    candidates = [b for b in obj.data.bones if "head" in b.name.lower() or "attachment" in b.name.lower()]
    if head and obj.data.bones[head] not in candidates:
        candidates.append(obj.data.bones[head])
    armatures.append({"name": obj.name, "data": obj.data.name, "bones": len(obj.data.bones),
                       "resolved_head": head, "parent": obj.parent.name if obj.parent else None,
                       "candidates": [{"name": b.name, "head_local": point(b.head_local), "tail_local": point(b.tail_local),
                                       "head_world": point(obj.matrix_world @ b.head_local),
                                       "tail_world": point(obj.matrix_world @ b.tail_local),
                                       "posed_head_world": point(obj.matrix_world @ obj.pose.bones[b.name].head),
                                       "deform": b.use_deform, "parent": b.parent.name if b.parent else None,
                                       "constraints": [{"name": c.name, "type": c.type, "target": c.target.name if getattr(c, "target", None) else None,
                                                        "subtarget": getattr(c, "subtarget", None)} for c in obj.pose.bones[b.name].constraints]}
                                      for b in candidates]})

report = {"file": str(target), "hash_before": before_hash, "hash_after": hashlib.sha256(target.read_bytes()).hexdigest(),
          "frame": bpy.context.scene.frame_current, "mode": bpy.context.mode,
          "active": bpy.context.active_object.name if bpy.context.active_object else None,
          "mesh_inventory": scene_meshes, "armatures": armatures, "hair_details": hair_details,
          "source_capture": {"strand_count": len(native_strands), "vertex_count": len(source.data.vertices),
                             "covered": bounds(source, covered), "uncaptured": bounds(source, outside),
                             "root": bounds(source, root_indices), "outside_indices": sorted(outside),
                             "outside_components": [{"bounds": bounds(source, ids), "indices": sorted(ids)} for ids in components(source, outside)],
                             "boundary_edges_count": len(boundary), "boundary_captured_all_roots": all(b in root_indices for a, b in boundary),
                             "boundary_strand_vertices": sorted({b for a, b in boundary}),
                             "native_strands": [{"vertex_count": len(s["vertices"]), "layer_count": len(s["layers"]),
                                                 "root_indices": s["layers"][0], "bounds": bounds(source, s["vertices"])} for s in native_strands]}}


def properties(block):
    return {key: reference(value) for key, value in block.items()
            if key not in (rig.RECORD_KEY, groups.GROUPS_KEY)}


def animation(block):
    value = getattr(block, "animation_data", None)
    if not value:
        return None
    return {"action": value.action.name if value.action else None,
            "action_users": value.action.users if value.action else None,
            "drivers": [{"path": curve.data_path, "index": curve.array_index} for curve in value.drivers],
            "nla": [{"name": track.name, "strips": [{"name": strip.name,
                                                       "action": strip.action.name if strip.action else None}
                                                      for strip in track.strips]} for track in value.nla_tracks]}


def id_details(block):
    return {"name": block.name, "type": block.bl_rna.identifier, "users": block.users,
            "library": block.library.filepath if block.library else None, "fake_user": block.use_fake_user}


version_collections = [collection for collection in bpy.data.collections if collection.get(variants.VERSION_KEY)]
def collection_targets(collection):
    found = set(collection.all_objects)
    for key in (variants.MESH_KEY, variants.ARMATURE_KEY):
        value = collection.get(key)
        if isinstance(value, bpy.types.Object):
            found.add(value)
    return found


version_objects = {obj for collection in version_collections for obj in collection_targets(collection)}
owned_ids = set(version_collections) | version_objects
for obj in version_objects:
    if obj.data:
        owned_ids.add(obj.data)
    keys = getattr(obj.data, "shape_keys", None)
    if keys:
        owned_ids.add(keys)
user_map = bpy.data.user_map(subset=owned_ids)
ownership = []
for collection in version_collections:
    item = {"name": collection.name, "properties": properties(collection), "children": [child.name for child in collection.children],
            "users": [id_details(block) for block in user_map.get(collection, [])], "objects": []}
    for obj in sorted(collection_targets(collection), key=lambda value: value.name):
        keys = getattr(obj.data, "shape_keys", None)
        item["objects"].append({"name": obj.name, "type": obj.type, "properties": properties(obj),
                                "all_collections": [coll.name for coll in obj.users_collection],
                                "external_collections": [coll.name for coll in obj.users_collection if coll is not collection],
                                "parent": obj.parent.name if obj.parent else None,
                                "source_matches_collection": obj.get(variants.SOURCE_KEY) is collection.get(variants.SOURCE_KEY),
                                "data": id_details(obj.data) if obj.data else None,
                                "data_objects": [candidate.name for candidate in bpy.data.objects if candidate.data is obj.data] if obj.data else [],
                                "keys": id_details(keys) if keys else None, "object_animation": animation(obj),
                                "data_animation": animation(obj.data) if obj.data else None,
                                "key_animation": animation(keys) if keys else None,
                                "users": [id_details(block) for block in user_map.get(obj, [])],
                                "data_properties": properties(obj.data) if obj.data else None,
                                "bone_owners": {reference(bone.get(rig.OWNER_KEY)): sum(1 for candidate in obj.data.bones
                                                        if candidate.get(rig.OWNER_KEY) == bone.get(rig.OWNER_KEY))
                                                for bone in obj.data.bones} if obj.type == "ARMATURE" else None,
                                "bone_sources": sorted({reference(bone.get(rig.SOURCE_KEY)) for bone in obj.data.bones}) if obj.type == "ARMATURE" else None})
    ownership.append(item)
report["version_ownership"] = ownership
report["external_references_to_version_objects"] = [{"target": obj.name, "users": [id_details(block) for block in user_map.get(obj, [])
                                                                                      if block not in owned_ids]}
                                                       for obj in version_objects]
assert report["hash_before"] == report["hash_after"]
output = Path("D:/Blender/Projects/Character/X/.codex-backups/hair3_attachment_readonly_report.json")
output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print("HAIR3_ATTACHMENT_READONLY_REPORT", str(output))
print(json.dumps({"version_ownership": [{"name": entry["name"], "properties": entry["properties"], "objects": [
                  {key: value for key, value in obj.items() if key != "properties"} | {
                      "properties": {key: value for key, value in obj["properties"].items() if "hair_" in key}}
                  for obj in entry["objects"]]} for entry in ownership],
                  "external_references": report["external_references_to_version_objects"]}, ensure_ascii=False))
