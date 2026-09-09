"""Read-only, on-disk armature audit for Rain/X torso-control comparison."""
import bpy
import json
import os
import sys


def vector(value):
    return [round(float(component), 7) for component in value]


def properties(owner):
    result = {}
    for key in owner.keys():
        value = owner[key]
        if isinstance(value, (str, int, float, bool)):
            result[key] = value if not isinstance(value, str) else value[:300]
        else:
            result[key] = str(value)[:120]
    return result


def constraint_record(constraint):
    result = {"name": constraint.name, "type": constraint.type,
              "influence": constraint.influence, "mute": constraint.mute}
    for name in ("subtarget", "target_space", "owner_space", "mix_mode", "use_offset",
                 "use_x", "use_y", "use_z", "invert_x", "invert_y", "invert_z",
                 "chain_count", "head_tail"):
        if hasattr(constraint, name):
            result[name] = getattr(constraint, name)
    target = getattr(constraint, "target", None)
    if target:
        result["target"] = target.name
    return result


def audit_armature(obj):
    bones = []
    for pb in obj.pose.bones:
        bone = pb.bone
        shape = pb.custom_shape
        bones.append({
            "name": pb.name, "parent": bone.parent.name if bone.parent else None,
            "children": [child.name for child in bone.children],
            "use_deform": bone.use_deform, "connected": bone.use_connect,
            "hide": bone.hide, "hide_select": bone.hide_select,
            "collections": [collection.name for collection in bone.collections],
            "head": vector(bone.head_local), "tail": vector(bone.tail_local),
            "pose_head": vector(pb.head), "pose_tail": vector(pb.tail),
            "rotation_mode": pb.rotation_mode, "rotation_euler": vector(pb.rotation_euler),
            "rotation_quaternion": vector(pb.rotation_quaternion), "location": vector(pb.location),
            "lock_location": list(pb.lock_location), "lock_rotation": list(pb.lock_rotation),
            "lock_scale": list(pb.lock_scale),
            "shape": None if shape is None else {
                "name": shape.name, "type": shape.type,
                "vertices": len(shape.data.vertices) if shape.type == "MESH" else None,
                "scale": vector(pb.custom_shape_scale_xyz),
                "rotation": vector(pb.custom_shape_rotation_euler),
                "translation": vector(pb.custom_shape_translation),
                "transform": pb.custom_shape_transform.name if pb.custom_shape_transform else None,
            },
            "constraints": [constraint_record(constraint) for constraint in pb.constraints],
            "bone_properties": properties(bone), "pose_properties": properties(pb),
        })
    drivers = []
    if obj.animation_data:
        for curve in obj.animation_data.drivers:
            drivers.append({"path": curve.data_path, "index": curve.array_index,
                "expression": curve.driver.expression, "type": curve.driver.type,
                "variables": [{"name": var.name, "type": var.type,
                    "targets": [{"id": target.id.name if target.id else None,
                        "path": target.data_path, "bone": target.bone_target,
                        "transform": target.transform_type} for target in var.targets]}
                    for var in curve.driver.variables]})
    return {"name": obj.name, "data": obj.data.name, "bone_count": len(bones),
            "data_properties": properties(obj.data), "object_properties": properties(obj),
            "action": obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None,
            "bones": bones, "drivers": drivers}


args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]
result = {"filepath": bpy.data.filepath, "blender_version": bpy.app.version_string,
          "frame": bpy.context.scene.frame_current,
          "armatures": [audit_armature(obj) for obj in bpy.data.objects if obj.type == "ARMATURE"]}
result["torso_widgets"] = {name: {"vertices": [vector(vertex.co) for vertex in bpy.data.objects[name].data.vertices],
    "edges": [list(edge.vertices) for edge in bpy.data.objects[name].data.edges]}
    for name in ("WGT-Torso", "WGT-FK_Limb", "WGT-Oval", "WGT-Root", "WGT-Hips")
    if name in bpy.data.objects and bpy.data.objects[name].type == "MESH"}
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=False)
print("SPINE_AUDIT_WRITTEN", out)
for armature in result["armatures"]:
    candidates = [bone for bone in armature["bones"] if any(token in bone["name"].lower()
        for token in ("spine", "torso", "chest", "hips", "hip", "pelvis", "waist", "zero", "root", "master", "neck", "head"))]
    print(json.dumps({"armature": armature["name"], "bone_count": armature["bone_count"],
        "torso_candidates": [{"name": bone["name"], "parent": bone["parent"],
            "deform": bone["use_deform"], "shape": bone["shape"]["name"] if bone["shape"] else None,
            "constraints": [(con["type"], con.get("subtarget"), con["influence"]) for con in bone["constraints"]]}
        for bone in candidates]}, ensure_ascii=False))
