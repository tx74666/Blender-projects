"""Saved-Cosha Dress effect diagnostics; never writes the artist blend.

Run with a verified Blender executable, serially with other heavy jobs:
  blender --background --factory-startup --disable-autoexec --threads 1 \
    --python validate_real_dress.py -- --frames 60

This is a native-effect QA harness, not a production-animation or Magica Cloth
equivalence acceptance test. It creates explicitly synthetic representative
inputs and keeps authored Actions, raw meshes, Shape Keys and Rest bones intact.
All scene/cache writes stay under --output. Collision coverage is vertex-based,
not a proof that triangles cannot intersect. Inspect the saved candidate scenes.
"""

import argparse
from array import array
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree


REPOSITORY = Path("D:/MyRepository/Blender-addons-by-Randy")
PROJECT = Path("D:/Blender/Projects/Character/X")
sys.path.insert(0, str(REPOSITORY / "addons"))
import character_designer
from character_designer import body_original_mode as original
from character_designer import limb_ik, limb_ik_fk
from character_designer import skirt_rig as skirt, skirt_physics as physics
from character_designer import skirt_motion_profiles as profiles
from character_designer import skirt_motion_tuning as tuning


CASES = ("walk", "turn", "leg_raise", "squat", "abrupt_stop")
# Keep the earlier real-X geometry guard. It is not loosened for this QA.
GEOMETRY_LIMIT_M = 5.0e-5
GEOMETRY_LIMIT_WORLD = 5.0e-5


def geometry_guard(meters):
    if not math.isfinite(meters) or meters <= 0:
        raise RuntimeError("Scene units must have a finite positive metres scale")
    # Preserve BOTH the previous native-world guard and this physical guard.
    return min(GEOMETRY_LIMIT_M, GEOMETRY_LIMIT_WORLD * meters)


def require_isolated_background():
    """Fail before output creation, registration, file opening or scene saving."""
    state = {"background": bool(bpy.app.background),
             "factory_startup_argument": "--factory-startup" in sys.argv,
             "initial_filepath": bpy.data.filepath}
    if not state["background"] or not state["factory_startup_argument"] or state["initial_filepath"]:
        raise RuntimeError("Refusing Dress QA outside an empty --background --factory-startup process; "
                           "do not execute this script in an artist Console or an already-open blend. "
                           + json.dumps(state, ensure_ascii=False))
    return state


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT / "X.blend")
    parser.add_argument("--output", type=Path,
                        default=PROJECT / "Validation/dress_automatic_20261005")
    parser.add_argument("--source", help="Exact source object name; its native ownership is still proved")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--collision-stride", type=int, default=3)
    parser.add_argument("--max-penetration-mm", type=float, default=2.0)
    parser.add_argument("--max-stop-jitter-mm", type=float, default=1.0)
    parser.add_argument("--max-edge-ratio", type=float, default=3.0)
    parser.add_argument("--memory-cache", action="store_true",
                        help="Use RAM cache; candidate bake persistence may then fail the reopen check")
    parser.add_argument("--body-vertex-limit", type=int, default=100000,
                        help="Skip the optional Body BVH when its conservative subdivision estimate exceeds this")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not 20 <= args.frames <= 240 or not 1 <= args.collision_stride <= args.frames:
        parser.error("Use 20..240 frames and a positive collision stride no larger than the interval")
    if any(not math.isfinite(value) or value <= 0 for value in
           (args.max_penetration_mm, args.max_stop_jitter_mm, args.max_edge_ratio)):
        parser.error("Diagnostic thresholds must be finite and positive")
    if args.body_vertex_limit < 1000:
        parser.error("Use a Body BVH budget of at least 1000 vertices")
    args.input, args.output = args.input.resolve(), args.output.resolve()
    if args.input.suffix.casefold() != ".blend" or not args.input.is_file():
        parser.error("--input must be an existing saved .blend")
    if args.output == args.input.parent:
        parser.error("Keep QA candidates/caches in a separate validation directory")
    args.cases = list(dict.fromkeys(args.cases))
    return args


def file_state(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    stat = path.stat()
    return {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest.hexdigest()}


def digest(value):
    encoder = json.JSONEncoder(sort_keys=True, ensure_ascii=False, allow_nan=False,
                              separators=(",", ":"))
    hasher = hashlib.sha256()
    for block in encoder.iterencode(value):
        hasher.update(block.encode("utf-8"))
    return hasher.hexdigest()


def id_name(value):
    if isinstance(value, bpy.types.ID):
        return (value.bl_rna.identifier, value.name_full,
                value.library.filepath if value.library else None)
    return None


def custom_content(value):
    if isinstance(value, bpy.types.ID):
        return {"ID": id_name(value)}
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if hasattr(value, "items"):
        return {str(key): custom_content(item) for key, item in value.items()}
    if hasattr(value, "to_list"):
        return [custom_content(item) for item in value.to_list()]
    if isinstance(value, (tuple, list)):
        return [custom_content(item) for item in value]
    # Reject unstable wrappers rather than treating an address as asset content.
    raise TypeError(f"Unsupported authored custom metadata type: {type(value).__name__}")


def simple_rna(owner):
    """Stable asset properties; user counts/evaluation identity are not content."""
    result = {}
    for prop in owner.bl_rna.properties:
        name = prop.identifier
        if name in {"rna_type", "users", "session_uid", "is_evaluated", "original"}:
            continue
        if prop.type == "COLLECTION":
            continue
        try:
            value = getattr(owner, name)
            if prop.type == "POINTER":
                result[name] = id_name(value)
            elif prop.is_array:
                result[name] = list(value)
            elif isinstance(value, (str, bool, int, float)) or value is None:
                result[name] = value
            elif isinstance(value, set):
                result[name] = sorted(value)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            continue
    return result


def curve_content(curve):
    return {"rna": simple_rna(curve),
            "keys": [simple_rna(point) for point in curve.keyframe_points],
            "samples": [tuple(point.co) for point in curve.sampled_points],
            "modifiers": [simple_rna(modifier) for modifier in curve.modifiers]}


def action_content(action):
    result = {"rna": simple_rna(action), "slots": [], "layers": [], "legacy_curves": []}
    if hasattr(action, "slots"):
        result["slots"] = [simple_rna(slot) for slot in action.slots]
        for layer in action.layers:
            layer_info = {"rna": simple_rna(layer), "strips": []}
            for strip in layer.strips:
                strip_info = {"rna": simple_rna(strip), "bags": []}
                for bag in getattr(strip, "channelbags", ()):
                    strip_info["bags"].append({"slot_handle": bag.slot_handle,
                                               "groups": [simple_rna(group) for group in getattr(bag, "groups", ())],
                                               "curves": [curve_content(curve) for curve in bag.fcurves]})
                layer_info["strips"].append(strip_info)
            result["layers"].append(layer_info)
    if getattr(action, "is_action_legacy", False) and hasattr(action, "fcurves"):
        result["legacy_curves"] = [curve_content(curve) for curve in action.fcurves]
    result["custom"] = {key: custom_content(value) for key, value in action.items()}
    result["pose_markers"] = [simple_rna(marker) for marker in action.pose_markers]
    result["asset_metadata"] = simple_rna(action.asset_data) if action.asset_data else None
    return result


def raw_mesh_content(obj):
    mesh, keys = obj.data, obj.data.shape_keys
    # Key values/eval_time are animation channels, not original deformation data.
    return {
        "vertices": [tuple(vertex.co) for vertex in mesh.vertices],
        "edges": [tuple(edge.vertices) for edge in mesh.edges],
        "faces": [(tuple(face.vertices), face.material_index, face.use_smooth) for face in mesh.polygons],
        "loops": [(loop.vertex_index, loop.edge_index) for loop in mesh.loops],
        "uv": [(layer.name, layer.active_render, [tuple(point.uv) for point in layer.data])
               for layer in mesh.uv_layers],
        "groups": [(group.name, group.index, group.lock_weight) for group in obj.vertex_groups],
        "weights": [sorted((group.group, group.weight) for group in vertex.groups)
                    for vertex in mesh.vertices],
        "materials": [id_name(material) for material in mesh.materials],
        "keys": None if keys is None else {
            "relative": keys.use_relative, "reference": keys.reference_key.name,
            "blocks": [(key.name, key.relative_key.name, key.mute, key.slider_min, key.slider_max,
                        key.vertex_group, key.interpolation, key.frame,
                        [tuple(point.co) for point in key.data]) for key in keys.key_blocks]},
    }


def rest_content(rig):
    return {bone.name: {"parent": bone.parent.name if bone.parent else None,
                        "matrix": [tuple(row) for row in bone.matrix_local],
                        "length": bone.length, "connect": bone.use_connect,
                        "deform": bone.use_deform, "inherit_scale": bone.inherit_scale,
                        "inherit_rotation": bone.use_inherit_rotation,
                        "local_location": bone.use_local_location}
            for bone in rig.data.bones}


class Protection:
    def __init__(self):
        self.meshes = {obj.name: digest(raw_mesh_content(obj)) for obj in bpy.data.objects if obj.type == "MESH"}
        self.rests = {obj.name: digest(rest_content(obj)) for obj in bpy.data.objects if obj.type == "ARMATURE"}
        self.actions = {action.name: digest(action_content(action)) for action in bpy.data.actions}
        self.action_refs = tuple(bpy.data.actions)
        self.start_nla = {}
        for obj in bpy.data.objects:
            animation = obj.animation_data
            if animation:
                self.start_nla[obj.name] = [self.nla_track(track) for track in animation.nla_tracks]

    @staticmethod
    def nla_track(track):
        values = simple_rna(track)
        # Candidate QA temporarily mutes playback, preserving this value in metadata.
        values.pop("mute", None)
        values.pop("is_solo", None)
        return {"rna": values, "strips": [simple_rna(strip) for strip in track.strips]}

    def verify(self):
        missing, changed = [], {"meshes": [], "rest": [], "actions": [], "nla_assets": []}
        for name, expected in self.meshes.items():
            obj = bpy.data.objects.get(name)
            if obj is None or obj.type != "MESH":
                missing.append(("mesh", name))
            elif digest(raw_mesh_content(obj)) != expected:
                changed["meshes"].append(name)
        for name, expected in self.rests.items():
            obj = bpy.data.objects.get(name)
            if obj is None or obj.type != "ARMATURE":
                missing.append(("rig", name))
            elif digest(rest_content(obj)) != expected:
                changed["rest"].append(name)
        for name, expected in self.actions.items():
            action = bpy.data.actions.get(name)
            if action is None:
                missing.append(("action", name))
            elif digest(action_content(action)) != expected:
                changed["actions"].append(name)
        for name, expected in self.start_nla.items():
            obj = bpy.data.objects.get(name)
            actual = [self.nla_track(track) for track in obj.animation_data.nla_tracks] if obj and obj.animation_data else []
            if actual != expected:
                changed["nla_assets"].append(name)
        return {"success": not missing and not any(changed.values()), "missing": missing, "changed": changed}

    def summary(self):
        return {"raw_mesh_sha256": self.meshes, "rest_sha256": self.rests,
                "author_action_sha256": self.actions, "nla_assets_sha256": digest(self.start_nla)}


def report_check(report, name, condition, **evidence):
    report.setdefault("checks", []).append({"name": name, "passed": bool(condition), **evidence})
    return bool(condition)


def save_candidate(path, artist):
    path = path.resolve()
    if path == artist:
        raise RuntimeError("Refusing to save the artist blend")
    path.parent.mkdir(parents=True, exist_ok=True)
    # No unnecessary .blend1 backups for repeatedly saved QA-owned candidates.
    # This isolated process does not save user preferences.
    previous_versions = bpy.context.preferences.filepaths.save_version
    try:
        bpy.context.preferences.filepaths.save_version = 0
        result = bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
    finally:
        bpy.context.preferences.filepaths.save_version = previous_versions
    if "FINISHED" not in result or Path(bpy.data.filepath).resolve() != path or not path.is_file():
        raise RuntimeError(f"Blender did not save the independent candidate: {path}")
    return str(path)


def owned_source(requested=None):
    choices = []
    for obj in bpy.data.objects:
        if obj.type == "MESH" and skirt.RECORD_KEY in obj:
            record = skirt.read_record(obj)
            if record:
                choices.append((obj, record))
    if requested:
        choices = [item for item in choices if item[0].name == requested]
    if len(choices) != 1:
        raise RuntimeError(f"Choose one exact proved Dress source with --source; found {[obj.name for obj, _ in choices]}")
    source, record = choices[0]
    rig = source[skirt.RIG_KEY]
    if not skirt.is_shared(record):
        raise RuntimeError("This real-Cosha QA expects the completed shared MainRig Dress; it will not merge a legacy rig")
    return source, rig, record


def backup_animation(scene, owners, actions):
    """Keep old assets reachable, including an Action formerly used only once."""
    for index, action in enumerate(actions):
        scene[f"CD_QA_AuthorAction_{index:04d}"] = action
    backups = []
    seen = set()
    for owner in owners:
        if owner is None or owner.as_pointer() in seen:
            continue
        seen.add(owner.as_pointer())
        animation = owner.animation_data
        if not animation:
            continue
        if animation.use_tweak_mode:
            raise RuntimeError(f"Exit NLA Tweak Mode before representative QA: {owner.name}")
        backups.append({"owner": id_name(owner), "action": id_name(animation.action),
                        "slot": getattr(animation.action_slot, "identifier", None),
                        "nla_track_flags": [(track.name, track.mute, track.is_solo) for track in animation.nla_tracks]})
        animation.action = None
        for track in animation.nla_tracks:
            track.mute = True
            track.is_solo = False
    scene["CD_QA_AuthorAnimationBackup"] = json.dumps(backups, ensure_ascii=False)
    return backups


def pose_channels(rig):
    return {bone.name: {"mode": bone.rotation_mode, "location": tuple(bone.location),
                        "quaternion": tuple(bone.rotation_quaternion), "euler": tuple(bone.rotation_euler),
                        "axis_angle": tuple(bone.rotation_axis_angle), "scale": tuple(bone.scale)}
            for bone in rig.pose.bones}


def restore_channels(rig, channels, object_basis, object_mode):
    rig.animation_data_create().action = None
    rig.rotation_mode = object_mode
    rig.matrix_basis = object_basis
    for name, values in channels.items():
        bone = rig.pose.bones[name]
        bone.rotation_mode = values["mode"]
        bone.location, bone.scale = values["location"], values["scale"]
        bone.rotation_quaternion = values["quaternion"]
        bone.rotation_euler = values["euler"]
        bone.rotation_axis_angle = values["axis_angle"]
    rig.update_tag(refresh={"OBJECT"})
    bpy.context.view_layer.update()


def curve_paths(action):
    if action is None:
        return []
    if hasattr(action, "layers"):
        return [curve for layer in action.layers for strip in layer.strips
                for bag in getattr(strip, "channelbags", ()) for curve in bag.fcurves]
    return list(getattr(action, "fcurves", ()))


def public_switch(operator, **kwargs):
    result = operator(**kwargs)
    if "FINISHED" not in result:
        raise RuntimeError(f"Public operator refused the copy-only switch: {kwargs}, {result}")


def body_inputs(rig, record):
    if rig.parent is not None or rig.constraints:
        raise RuntimeError("Root-object QA needs an unconstrained, parentless MainRig; no artist relationship is bypassed")
    inventory = limb_ik._validate_inventory(rig)
    legs = {side: inventory["rigs"][("LEG", side)] for side in ("L", "R")}
    if any(limb_ik_fk.mode_for_rig(rig, value) != "FK" for value in legs.values()):
        raise RuntimeError("Public Body FK switch did not enable the two native source-leg chains")
    blocked = []
    prefixes = ("location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale")
    paths = set(prefixes)
    for item in legs.values():
        for name in item["chain"]:
            paths.update(rig.pose.bones[name].path_from_id(path) for path in prefixes)
    if rig.animation_data:
        blocked = [curve.data_path for curve in rig.animation_data.drivers if curve.data_path in paths]
    if blocked:
        raise RuntimeError(f"Authored transform drivers control QA inputs; preserved without bypass: {blocked}")
    native = [bone for bone in rig.data.bones if bone.use_deform and bone.name not in record["shared"]["names"]]
    if not native:
        raise RuntimeError("No native Body deform bones for a rig-local height measurement")
    minimum = min(min(bone.head_local.z, bone.tail_local.z) for bone in native)
    maximum = max(max(bone.head_local.z, bone.tail_local.z) for bone in native)
    height = (maximum - minimum) * rig.matrix_world.to_3x3().col[2].length
    if not math.isfinite(height) or height <= 0:
        raise RuntimeError("Invalid Body Rest height")
    axes = {name: (rig.data.bones[name].matrix_local.to_3x3().inverted() @ Vector((1, 0, 0))).normalized()
            for item in legs.values() for name in item["chain"]}
    return legs, axes, height


def smooth(value):
    value = max(0., min(1., value))
    return value * value * (3. - 2. * value)


def representative_values(case, phase, height):
    """Rig +Y is declared forward. These are tests, not foot-planted gait."""
    displacement, yaw = Vector((0, 0, 0)), 0.
    angles = {"L": [0., 0., 0.], "R": [0., 0., 0.]}
    if case in {"walk", "abrupt_stop"}:
        travel = phase if case == "walk" else min(phase / .55, 1.)
        displacement.y = height * (.28 if case == "walk" else .32) * travel
        cycle = math.tau * 2. * phase
        motion = 1. if case == "walk" else (1. - smooth((phase - .4) / .15))
        displacement.z = height * .003 * math.sin(cycle * 2.) * motion
        for side, offset in (("L", 0.), ("R", math.pi)):
            swing = math.sin(cycle + offset) * motion
            angles[side] = [math.radians(18.) * swing, -math.radians(20.) * max(swing, 0.), 0.]
    elif case == "turn":
        yaw = math.radians(100.) * smooth(phase)
        displacement.y = height * .08 * smooth(phase)
    elif case in {"leg_raise", "squat"}:
        pulse = smooth(phase / .35) * (1. - smooth((phase - .65) / .35))
        if case == "leg_raise":
            angles["L"] = [math.radians(55.) * pulse, -math.radians(20.) * pulse, 0.]
        else:
            displacement.z = -height * .085 * pulse
            for side in angles:
                angles[side] = [math.radians(50.) * pulse, -math.radians(85.) * pulse, math.radians(15.) * pulse]
    return displacement, yaw, angles


def author_case(case, rig, legs, axes, channels, basis, height, frames):
    action = bpy.data.actions.new(f"QA Representative · {case.replace('_', ' ').title()}")
    action["CD_QA_SyntheticInput"] = True
    action["CD_QA_InputDescription"] = "Representative stress input; not production gait/animation"
    action.use_fake_user = True
    rig.animation_data_create().action = action
    slot = action.slots.new(id_type="OBJECT", name=rig.name)
    rig.animation_data.action_slot = slot
    rig.rotation_mode = "QUATERNION"
    base_location, base_quaternion, base_scale = basis.decompose()
    base_rotations = {name: rig.pose.bones[name].matrix_basis.to_quaternion()
                      for item in legs.values() for name in item["chain"]}
    for frame in range(1, frames + 1):
        phase = (frame - 1) / (frames - 1)
        move, yaw, angles = representative_values(case, phase, height)
        rig.location = base_location + base_quaternion @ move
        rig.rotation_quaternion = base_quaternion @ Quaternion((0, 0, 1), yaw)
        rig.scale = base_scale
        for path in ("location", "rotation_quaternion", "scale"):
            if not rig.keyframe_insert(path, frame=frame, group="QA representative root motion"):
                raise RuntimeError(f"Could not key the representative root {path} at {frame}")
        for side, item in legs.items():
            for index, name in enumerate(item["chain"]):
                bone = rig.pose.bones[name]
                bone.rotation_mode = "QUATERNION"
                bone.location, bone.scale = channels[name]["location"], channels[name]["scale"]
                bone.rotation_quaternion = base_rotations[name] @ Quaternion(axes[name], angles[side][index])
                for path in ("location", "rotation_quaternion", "scale"):
                    if not bone.keyframe_insert(path, frame=frame, group="QA native " + side + " leg"):
                        raise RuntimeError(f"Could not key the representative {name} {path} at {frame}")
    for curve in curve_paths(action):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    return action


def world_mesh(obj, graph, waist_group=None, hem_groups=(), triangles=False):
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=bool(waist_group or hem_groups), depsgraph=graph)
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        result = {"points": points, "edges": [tuple(edge.vertices) for edge in mesh.edges]}
        if waist_group or hem_groups:
            waist = obj.vertex_groups.get(waist_group) if waist_group else None
            hems = {obj.vertex_groups[name].index for name in hem_groups if name in obj.vertex_groups}
            available = any(vertex.groups for vertex in mesh.vertices)
            result["weights_available"] = available
            result["free_indices"] = [vertex.index for vertex in mesh.vertices if waist is None or
                                      next((weight.weight for weight in vertex.groups if weight.group == waist.index), 0.) < .999]
            result["hem_indices"] = [vertex.index for vertex in mesh.vertices if
                                     sum(weight.weight for weight in vertex.groups if weight.group in hems) >= .5]
        if triangles:
            mesh.calc_loop_triangles()
            result["triangles"] = [tuple(triangle.vertices) for triangle in mesh.loop_triangles]
        return result
    finally:
        evaluated.to_mesh_clear()


def pack(points):
    return array("f", (value for point in points for value in point))


def packed_error(expected, points, meters):
    if len(expected) != len(points) * 3:
        raise RuntimeError("Evaluated surface vertex count changed during replay")
    return max((math.sqrt(sum((expected[index * 3 + axis] - point[axis]) ** 2 for axis in range(3)))
                * meters for index, point in enumerate(points)), default=0.)


def finite(points):
    return all(math.isfinite(value) for point in points for value in point)


def edge_lengths(points, edges):
    return [(points[first] - points[second]).length for first, second in edges]


def edge_ratio(points, edges, base):
    return max(((points[first] - points[second]).length / length
                for (first, second), length in zip(edges, base) if length > 1.e-10), default=1.)


class ClosedCollider:
    """Fast exact convex sign; three-ray parity fallback for edited concave fits."""
    def __init__(self, obj, graph, epsilon, mesh=None):
        mesh = mesh or world_mesh(obj, graph, triangles=True)
        self.points, self.triangles = mesh["points"], mesh["triangles"]
        self.tree = BVHTree.FromPolygons(self.points, self.triangles, all_triangles=True)
        self.epsilon = epsilon
        volume = sum(self.points[a].dot(self.points[b].cross(self.points[c])) / 6.
                     for a, b, c in self.triangles)
        self.convex = volume > 0
        if self.convex:
            for a, b, c in self.triangles:
                normal = (self.points[b] - self.points[a]).cross(self.points[c] - self.points[a]).normalized()
                if any(normal.dot(point - self.points[a]) > epsilon for point in self.points):
                    self.convex = False
                    break
        self.ray_distance = max(max(point[axis] for point in self.points) - min(point[axis] for point in self.points)
                                for axis in range(3)) * 5. + epsilon * 10.

    def signed_distance(self, point):
        location, normal, _index, distance = self.tree.find_nearest(point)
        if location is None or not math.isfinite(distance):
            raise RuntimeError("Closed collider BVH returned an invalid nearest triangle")
        if distance <= self.epsilon:
            return 0.
        if self.convex:
            inside = (point - location).dot(normal) < 0.
        else:
            votes = []
            for direction in (Vector((1., .371, .529)), Vector((.233, 1., .417)), Vector((.619, .283, 1.))):
                direction.normalize()
                origin, hits, remaining = point.copy(), 0, self.ray_distance
                for _ in range(len(self.triangles) + 1):
                    hit, _normal, _index, length = self.tree.ray_cast(origin, direction, remaining)
                    if hit is None:
                        break
                    hits += 1
                    remaining -= length + self.epsilon
                    if remaining <= 0:
                        break
                    origin = hit + direction * self.epsilon
                else:
                    raise RuntimeError("Unresolved parity ray at a collider seam")
                votes.append(bool(hits % 2))
            inside = sum(votes) >= 2
        return -distance if inside else distance


def collision_metrics(points, collider, meters, indices=None):
    distances = [collider.signed_distance(points[index]) * meters
                 for index in (range(len(points)) if indices is None else indices)]
    return {"sampled_vertices": len(distances), "minimum_signed_distance_m": min(distances, default=0.),
            "maximum_penetration_m": max(0., -min(distances, default=0.)),
            "inside_vertices": sum(value < 0. for value in distances)}


def registered_body(context, rig, args):
    setup = getattr(context.scene, "character_designer_setup", None)
    body = getattr(setup, "body", None)
    status = {"registered_pointer_only": True, "measured": False,
              "vertex_budget": args.body_vertex_limit}
    if setup is None or setup.rig != rig or body is None or body.type != "MESH":
        status["reason"] = "Character Setup has no Body Mesh registered to this exact MainRig; no object was guessed"
        return None, status
    status["object"] = body.name
    if (body.name not in context.scene.objects or body.name not in context.view_layer.objects
            or body.hide_viewport):
        status["reason"] = "Registered Body is outside the evaluated view layer or disabled in the viewport"
        return None, status
    bindings = [modifier.object for modifier in body.modifiers
                if modifier.type == "ARMATURE" and modifier.show_viewport]
    if bindings != [rig]:
        status["reason"] = "Registered Body does not have exactly this MainRig as its active native Armature binding"
        return None, status
    levels = sum(modifier.levels for modifier in body.modifiers
                 if modifier.type == "SUBSURF" and modifier.show_viewport)
    estimate = len(body.data.vertices) * 4 ** levels
    status["conservative_subdivision_vertex_estimate"] = estimate
    if estimate > args.body_vertex_limit:
        status["reason"] = "Optional Body BVH exceeds the declared memory budget; final Dress-vs-Body penetration is unmeasured"
        return None, status
    status["measured"] = True
    status["definition"] = "Actual evaluated registered Body, with Dress samples in native pelvis-to-knee projection interval"
    return body, status


def body_surface_metrics(body, graph, rig, record, legs, final, meters, height, limit):
    mesh = world_mesh(body, graph, triangles=True)
    if len(mesh["points"]) > limit:
        return {"measured": False, "reason": "Actual evaluated Body vertex count exceeded the declared BVH budget",
                "vertices": len(mesh["points"]), "vertex_budget": limit}
    evaluated = rig.evaluated_get(graph)
    axis = evaluated.matrix_world.to_3x3().col[2].normalized()
    pelvis = evaluated.matrix_world @ evaluated.pose.bones[record["shared"]["anchor"]].head
    knees = [evaluated.matrix_world @ evaluated.pose.bones[item["chain"][1]].head for item in legs.values()]
    lower = min((point - pelvis).dot(axis) for point in knees) - height * .02
    upper = height * .08
    indices = [index for index in final["free_indices"]
               if lower <= (final["points"][index] - pelvis).dot(axis) <= upper]
    incidence = Counter(tuple(sorted((a, b))) for triangle in mesh["triangles"]
                        for a, b in zip(triangle, triangle[1:] + triangle[:1]))
    closed = bool(incidence) and all(count == 2 for count in incidence.values())
    collider = ClosedCollider(body, graph, max(1.e-8, height * 1.e-6), mesh=mesh)
    result = {"measured": True, "object": body.name, "evaluated_vertices": len(mesh["points"]),
              "sampled_dress_free_vertices": len(indices), "closed_triangle_edge_incidence": closed,
              "open_or_nonmanifold_edges": sum(count != 2 for count in incidence.values()),
              "region_projection_world_units": [lower, upper],
              "region_definition": "Dress free surface between lowest posed native knee minus 2% height and pelvis plus 8% height"}
    if not indices:
        result.update(measured=False, reason="No evaluated Dress free vertices in the declared pelvis-to-knee interval")
        return result
    if closed:
        result["signed_surface"] = collision_metrics(final["points"], collider, meters, indices)
        result["sign_method"] = "convex_normal" if collider.convex else "three_ray_parity_on_full_closed_registered_body"
        result["limitation"] = "Closed incidence does not rule out Body self-intersections; sampled vertices do not prove triangle separation"
    else:
        nearest = [collider.tree.find_nearest(final["points"][index]) for index in indices]
        result["unsigned_minimum_surface_distance_m"] = min((item[3] * meters for item in nearest), default=None)
        approximate = [(final["points"][index] - hit[0]).dot(hit[1]) * meters for index, hit in zip(indices, nearest)]
        result["unproven_minimum_nearest_normal_distance_m"] = min(approximate, default=None)
        result["sign_method"] = "UNPROVEN_nearest_triangle_normal_only"
        result["limitation"] = "Registered Body is not closed; actual inside/outside and body penetration are NOT established"
    return result


def cache_state(cloth):
    cache = cloth.point_cache
    return {"pointer": cache.as_pointer(), "start": cache.frame_start, "end": cache.frame_end,
            "step": cache.frame_step, "is_baked": cache.is_baked, "disk": cache.use_disk_cache,
            "external": cache.use_external, "name": cache.name}


def saved_cache_preflight(source, record):
    """Read only, before the first candidate save; no cache-directory guesses.

    A saved disk/external/sealed cache may have files owned by the artist.
    Without proving Blender's exact directory lifecycle we refuse that input,
    rather than free/reset/rebake it after a filepath change. An unsealed RAM
    cache has no active native disk-cache ownership to release; candidate disk
    caching is enabled only after the independent candidate has been saved.
    """
    state = {"physics_present": bool(record.get("physics")), "allowed": True,
             "policy": "Refuse any pre-existing sealed, disk, external or baking cache; no artist cache files are enumerated or touched"}
    physics_record = record.get("physics")
    if not physics_record:
        state["reason"] = "No saved owned Dress physics cache"
        return state
    if not isinstance(physics_record, dict):
        state.update(allowed=False, reason="Unreadable saved Dress physics cache metadata")
        return state
    state["saved_baked_range"] = physics_record.get("baked_range")
    proxy = bpy.data.objects.get(physics_record.get("proxy", ""))
    state["proxy_record_name"] = physics_record.get("proxy")
    if (proxy is None or proxy.type != "MESH" or proxy.get(skirt.OWNER_KEY) != record["owner"]
            or proxy.get(skirt.SOURCE_KEY) != source):
        state.update(allowed=False, reason="Saved cache proxy does not have this exact native source/owner")
        return state
    cloths = [modifier for modifier in proxy.modifiers if modifier.type == "CLOTH"]
    if len(cloths) != 1:
        state.update(allowed=False, reason="Saved owned cache does not have exactly one native Cloth modifier")
        return state
    cache = cloths[0].point_cache
    state["native"] = {**cache_state(cloths[0]), "is_baking": cache.is_baking,
                        "is_outdated": cache.is_outdated,
                        "native_filepath": cache.filepath, "index": cache.index}
    if (cache.is_baked or cache.is_baking or cache.use_disk_cache or cache.use_external
            or physics_record.get("baked_range") is not None):
        state.update(allowed=False,
                     reason="Existing saved cache cannot be proved safe to clear after filepath switching; "
                            "the verifier refuses it before any candidate save, clear, Reset or Bake")
    else:
        state["reason"] = "Only an unsealed native RAM cache is present; all later disk/cache operations use QA candidate paths"
    return state


def measure_frame(source, rig, proxy, record, legs, frame, meters, collision, previous=None, bases=None,
                  body=None, body_limit=100000, height=1.):
    graph = bpy.context.evaluated_depsgraph_get()
    final = world_mesh(source, graph, record["controls"]["waist"], [chain["def"][-1] for chain in record["chains"]])
    cage = world_mesh(proxy, graph)
    evaluated_rig = rig.evaluated_get(graph)
    waist = evaluated_rig.matrix_world @ evaluated_rig.pose.bones[record["controls"]["waist"]].matrix
    original_waist = rig.data.bones[record["controls"]["waist"]].matrix_local
    expected = waist @ original_waist.inverted() @ rig.matrix_world.inverted() @ proxy.matrix_world
    pin = record["physics"].get("pin_weights", [1. if index < record["physics"]["columns"] else 0.
                                               for index in range(len(cage["points"]))])
    pinned = [index for index, value in enumerate(pin) if value >= 1. - 1.e-6]
    pin_error = max(((cage["points"][index] - expected @ proxy.data.vertices[index].co).length * meters
                     for index in pinned), default=0.)
    if bases is None:
        columns, rows = record["physics"]["columns"], record["physics"]["rows"]
        rings = [(row * columns + column, row * columns + (column + 1) % columns)
                 for row in range(rows) for column in range(columns)]
        bases = {"final_edges": final["edges"], "final_lengths": edge_lengths(final["points"], final["edges"]),
                 "rings": rings, "ring_lengths": edge_lengths(cage["points"], rings),
                 "native_knees": {side: evaluated_rig.pose.bones[item["chain"][1]].head.copy()
                                  for side, item in legs.items()}}
    if final["edges"] != bases["final_edges"]:
        raise RuntimeError("Final Dress topology changed during synthetic inputs")
    names = {name for chain in record["chains"] for layer in ("def", "manual", "phys") for name in chain[layer]}
    names.update(name for item in legs.values() for name in item["chain"])
    matrices_finite = all(math.isfinite(value) for name in names for row in evaluated_rig.pose.bones[name].matrix for value in row)
    hem_start = (record["physics"]["rows"] - 1) * record["physics"]["columns"]
    inverse_waist = waist.inverted()
    cage_hem = [inverse_waist @ point for point in cage["points"][hem_start:]]
    final_hem = [inverse_waist @ final["points"][index] for index in final["hem_indices"]]
    values = {"frame": frame, "finite": finite(final["points"]) and finite(cage["points"]) and matrices_finite,
              "waist_pin_error_m": pin_error, "pinned_vertices": len(pinned),
              "final_edge_ratio": edge_ratio(final["points"], bases["final_edges"], bases["final_lengths"]),
              "proxy_ring_neighbor_ratio": edge_ratio(cage["points"], bases["rings"], bases["ring_lengths"]),
              "native_knee_motion_without_root_m": {
                  side: (evaluated_rig.matrix_world.to_3x3() @
                         (evaluated_rig.pose.bones[item["chain"][1]].head - bases["native_knees"][side])).length * meters
                  for side, item in legs.items()},
              "final_vertices": len(final["points"]), "proxy_vertices": len(cage["points"]),
              "final_hem_vertices": len(final_hem), "evaluated_weights_available": final["weights_available"]}
    if previous is not None:
        linear = waist.to_3x3()
        for label, points, old in (("proxy", cage_hem, previous["cage_hem"]),
                                   ("final", final_hem, previous["final_hem"])):
            if len(points) != len(old):
                raise RuntimeError("Hem vertex identity changed during the trajectory")
            lengths = [(linear @ (point - prior)).length * meters for point, prior in zip(points, old)]
            values[label + "_hem_delta_max_m"] = max(lengths, default=0.)
            values[label + "_hem_delta_rms_m"] = math.sqrt(sum(value * value for value in lengths) / max(1, len(lengths)))
    if collision:
        values["collision"] = {}
        for name in record["physics"]["colliders"]:
            obj = bpy.data.objects[name]
            binding = obj.vertex_groups[0].name  # Already proved exactly one whole-mesh group.
            side = next((side for side, item in legs.items() if binding == item["chain"][0]), None)
            collider = ClosedCollider(obj, graph, max(1.e-8, record["fit"]["height_world"] * 1.e-6))
            values["collision"][name] = {"binding_bone": binding, "role": "leg." + side if side else "pelvis_or_other",
                "sign_method": "proved_convex_triangle_normal" if collider.convex else "three_ray_parity",
                "final_all": collision_metrics(final["points"], collider, meters),
                "final_free": collision_metrics(final["points"], collider, meters, final["free_indices"]),
                "proxy": collision_metrics(cage["points"], collider, meters)}
        if body is not None:
            values["registered_body_surface"] = body_surface_metrics(body, graph, rig, record, legs, final,
                                                                     meters, height, body_limit)
    return values, {"cage_hem": cage_hem, "final_hem": final_hem}, bases, pack(final["points"]), pack(cage["points"])


def sample_frames(frames):
    return sorted({1, frames, max(1, round(frames * .2)), max(1, round(frames * .35)),
                   max(1, round(frames * .5)), max(1, round(frames * .65)), max(1, round(frames * .8))})


def summarize_motion(case, frames, args, result):
    report_check(result, "finite_all_frames", all(item["finite"] for item in frames))
    if case != "turn":
        moved = {side: max(item["native_knee_motion_without_root_m"][side] for item in frames)
                 for side in ("L", "R")}
        requested = ("L",) if case == "leg_raise" else ("L", "R")
        threshold = result["body_height_world_units"] * result["scene_units_to_meters"] * .01
        report_check(result, "representative_native_leg_inputs_reach_evaluated_bones",
                     all(moved[side] > threshold for side in requested), maximum_knee_motion_m=moved,
                     minimum_representative_response_m=threshold)
    pin_error = max(item["waist_pin_error_m"] for item in frames)
    guard = geometry_guard(result["scene_units_to_meters"])
    report_check(result, "fixed_waist_attachment", pin_error <= guard,
                 maximum_error_m=pin_error, guard_m=guard)
    ratio = max(max(item["final_edge_ratio"], item["proxy_ring_neighbor_ratio"]) for item in frames)
    report_check(result, "diagnostic_neighbor_continuity", ratio <= args.max_edge_ratio,
                 maximum_ratio=ratio, diagnostic_limit=args.max_edge_ratio)
    sampled = [item for item in frames if "collision" in item]
    aggregate = {}
    for item in sampled:
        for name, collision in item["collision"].items():
            current = aggregate.setdefault(name, {"role": collision["role"], "binding_bone": collision["binding_bone"],
                "final_maximum_penetration_m": 0., "proxy_maximum_penetration_m": 0., "worst_final_frame": None,
                "minimum_final_signed_distance_m": math.inf})
            final = collision["final_free"]["maximum_penetration_m"]
            if final > current["final_maximum_penetration_m"]:
                current["final_maximum_penetration_m"], current["worst_final_frame"] = final, item["frame"]
            current["proxy_maximum_penetration_m"] = max(current["proxy_maximum_penetration_m"], collision["proxy"]["maximum_penetration_m"])
            current["minimum_final_signed_distance_m"] = min(current["minimum_final_signed_distance_m"], collision["final_free"]["minimum_signed_distance_m"])
    result["collider_summary"] = aggregate
    result["collision_sampled_frames"] = [item["frame"] for item in sampled]
    legs = {value["role"] for value in aggregate.values() if value["role"].startswith("leg.")}
    report_check(result, "both_native_leg_colliders_measured", legs == {"leg.L", "leg.R"}, roles=sorted(legs))
    report_check(result, "evaluated_final_weight_identity_available", all(item["evaluated_weights_available"] for item in frames))
    maximum = max((item["final_maximum_penetration_m"] for item in aggregate.values()), default=0.)
    report_check(result, "diagnostic_final_free_surface_penetration", maximum <= args.max_penetration_mm / 1000.,
                 maximum_m=maximum, diagnostic_limit_m=args.max_penetration_mm / 1000.)
    bodies = [item["registered_body_surface"] for item in sampled if "registered_body_surface" in item]
    if bodies:
        signed = [item["signed_surface"] for item in bodies if "signed_surface" in item]
        result["registered_body_diagnostic_summary"] = {
            "sampled_frames": len(bodies), "signed_frames": len(signed),
            "actual_body_penetration_proved_by_this_qa": False,
            "maximum_sampled_signed_penetration_m": max((item["maximum_penetration_m"] for item in signed), default=None),
            "coverage": "Closed registered Body vertex sign available" if len(signed) == len(bodies)
                        else "Unsigned/normal distance only or skipped; actual body penetration is unproved"}
        if signed:
            maximum_body = max(item["maximum_penetration_m"] for item in signed)
            report_check(result, "diagnostic_registered_closed_body_surface_penetration",
                         maximum_body <= args.max_penetration_mm / 1000., maximum_m=maximum_body,
                         diagnostic_limit_m=args.max_penetration_mm / 1000.)
    else:
        result["registered_body_diagnostic_summary"] = {"coverage": "UNMEASURED; see main registered Body status",
                                                        "actual_body_penetration_proved_by_this_qa": False}
    if case == "abrupt_stop":
        stopped = [item for item in frames if item["frame"] > args.frames - 10]
        jitter = {label: max(item.get(label + "_hem_delta_max_m", 0.) for item in stopped) for label in ("proxy", "final")}
        result["stop_settling"] = {"frames": [item["frame"] for item in stopped], "waist_relative_max_delta_m_per_frame": jitter,
                                  "observation": "Last ten frames only; this short interval is not long-run equilibrium"}
        report_check(result, "diagnostic_stop_tail_jitter", bool(stopped[0]["final_hem_vertices"]) and
                     max(jitter.values()) <= args.max_stop_jitter_mm / 1000.,
                     maximum_m_per_frame=jitter, diagnostic_limit_m_per_frame=args.max_stop_jitter_mm / 1000.)


def replay(source, proxy, frames, reference, meters):
    maximum = {"final_m": 0., "proxy_m": 0.}
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        for key, obj in (("final", source), ("proxy", proxy)):
            error = packed_error(reference[frame][key], world_mesh(obj, graph)["points"], meters)
            maximum[key + "_m"] = max(maximum[key + "_m"], error)
    return maximum


def baked_modes_and_manual(source, rig, proxy, cloth, record, frames, references, meters, result):
    frame = max(1, round(frames * .5))
    bpy.context.scene.frame_set(frame)
    native_before = cache_state(cloth)
    profile = tuning.effective(source)
    result["mode_capability"] = profile["capability"]
    if profile["capability"] == "BOTH":
        automatic = world_mesh(source, bpy.context.evaluated_depsgraph_get())["points"]
        tuning.apply(bpy.context, (source,), mode="MANUAL")
        manual = world_mesh(source, bpy.context.evaluated_depsgraph_get())["points"]
        response = packed_error(pack(automatic), manual, meters)
        middle = cache_state(cloth)
        tuning.apply(bpy.context, (source,), mode="AUTOMATIC")
        return_error = packed_error(pack(automatic), world_mesh(source, bpy.context.evaluated_depsgraph_get())["points"], meters)
        after = cache_state(cloth)
        report_check(result, "automatic_manual_automatic_keeps_sealed_cache", native_before == middle == after,
                     before=native_before, manual=middle, restored=after)
        report_check(result, "automatic_mode_has_actual_surface_effect", response > 1.e-5, displacement_m=response)
        report_check(result, "mode_roundtrip_surface", return_error <= geometry_guard(meters),
                     error_m=return_error, guard_m=geometry_guard(meters))
    else:
        result["mode_switch_not_exercised"] = "Saved generation capability does not expose MANUAL; its profile was preserved"
        report_check(result, "manual_mode_coverage", False, capability=profile["capability"])
    control = rig.pose.bones[record["controls"]["hem"]]
    animation = rig.animation_data
    prefix = control.path_from_id()
    if any(curve.data_path.startswith(prefix) for curve in curve_paths(animation.action)):
        raise RuntimeError("QA Action unexpectedly controls the manual hem; no authored input is overridden")
    basis = control.matrix_basis.copy()
    graph = bpy.context.evaluated_depsgraph_get()
    before = world_mesh(source, graph)["points"]
    cached = cache_state(cloth)
    action_before = digest(action_content(animation.action))
    try:
        delta = Vector((record["fit"]["height_world"] * .02, 0., 0.))
        control.location += control.bone.matrix_local.to_3x3().inverted() @ delta
        rig.update_tag(refresh={"OBJECT"})
        bpy.context.view_layer.update()
        changed = world_mesh(source, bpy.context.evaluated_depsgraph_get())["points"]
        displacement = packed_error(pack(before), changed, meters)
    finally:
        control.matrix_basis = basis
        rig.update_tag(refresh={"OBJECT"})
        bpy.context.view_layer.update()
    restored = world_mesh(source, bpy.context.evaluated_depsgraph_get())["points"]
    report_check(result, "manual_fine_tune_after_physics_bake_surface", displacement > 1.e-5,
                 control=control.name, displacement_m=displacement, synthetic_control_delta=tuple(delta))
    report_check(result, "manual_fine_tune_keeps_cache_and_qa_action", cache_state(cloth) == cached and
                 digest(action_content(animation.action)) == action_before,
                 before_cache=cached, after_cache=cache_state(cloth))
    error = packed_error(pack(before), restored, meters)
    report_check(result, "manual_fine_tune_restore_surface", error <= geometry_guard(meters), error_m=error,
                 guard_m=geometry_guard(meters))


def save_reference(path, values):
    with path.open("wb") as handle:
        values.tofile(handle)
    return {"path": str(path), "float32_values": len(values), "byte_order": sys.byteorder,
            "sha256": file_state(path)["sha256"]}


def load_reference(reference):
    path = Path(reference["path"])
    if file_state(path)["sha256"] != reference["sha256"] or reference["byte_order"] != sys.byteorder:
        raise RuntimeError("Saved frame reference bytes changed or have another byte order")
    values = array("f")
    with path.open("rb") as handle:
        values.fromfile(handle, reference["float32_values"])
    return values


def run_case(case, args, source, rig, proxy, cloth, record, legs, axes, height, channels, basis, mode, protection,
             body=None):
    scene = bpy.context.scene
    result = {"name": case, "representative_input_only": True, "frames": args.frames,
              "collision_stride": args.collision_stride, "checks": [], "success": False,
              "scene_units_to_meters": scene.unit_settings.scale_length,
              "body_height_world_units": height}
    candidate = args.output / f"Cosha_Dress_QA_{case}.blend"
    result["candidate"] = str(candidate)
    started = time.perf_counter()
    try:
        physics.clear_cache(bpy.context, source)
        restore_channels(rig, channels, basis, mode)
        action = author_case(case, rig, legs, axes, channels, basis, height, args.frames)
        result["qa_action"] = action.name
        result["qa_action_sha256"] = digest(action_content(action))
        scene.frame_start, scene.frame_end = 1, args.frames
        cloth.point_cache.frame_start, cloth.point_cache.frame_end = 1, args.frames
        cloth.point_cache.frame_step = 1
        # Save BEFORE enabling/walking disk cache so its folder belongs to this
        # candidate, never to X.blend or the previous case's cache folder.
        save_candidate(candidate, args.input)
        cloth.point_cache.use_disk_cache = not args.memory_cache
        result["reset_initial"] = physics.reset_simulation(bpy.context, source)
        report_check(result, "reset_returns_start_unbaked", scene.frame_current == 1 and not cloth.point_cache.is_baked)
        keyframes = sample_frames(args.frames)
        result["visual_keyframes"] = keyframes
        for marker in list(scene.timeline_markers):
            if marker.name.startswith("QA "):
                scene.timeline_markers.remove(marker)
        for frame in keyframes:
            scene.timeline_markers.new(f"QA {case} {frame}", frame=frame)
        reference, measurements, previous, bases = {}, [], None, None
        for frame in range(1, args.frames + 1):
            scene.frame_set(frame)
            values, previous, bases, final, cage = measure_frame(
                source, rig, proxy, skirt.read_record(source), legs, frame, scene.unit_settings.scale_length,
                collision=(frame - 1) % args.collision_stride == 0 or frame in keyframes,
                previous=previous, bases=bases, body=body, body_limit=args.body_vertex_limit, height=height)
            reference[frame] = {"final": final, "proxy": cage}
            measurements.append(values)
            if frame % 10 == 0 or frame == args.frames:
                print(f"CD QA {case}: simulated {frame}/{args.frames}", flush=True)
        result["measurements"] = measurements
        summarize_motion(case, measurements, args, result)
        result["reset_replay"] = physics.reset_simulation(bpy.context, source)
        reset_error = replay(source, proxy, range(1, args.frames + 1), reference, scene.unit_settings.scale_length)
        result["reset_replay_error"] = reset_error
        guard = geometry_guard(scene.unit_settings.scale_length)
        report_check(result, "reset_replay_surface", max(reset_error.values()) <= guard,
                     maximum_error_m=reset_error, guard_m=guard)
        for done, total, label in physics.bake_steps(bpy.context, source, 1, args.frames, "SIMULATION"):
            if done % 10 == 0 or done == total:
                print(f"CD QA {case}: bake {label}", flush=True)
        report_check(result, "native_bake_sealed", cloth.point_cache.is_baked,
                     native_cache=cache_state(cloth), saved_range=skirt.read_record(source)["physics"]["baked_range"])
        order = list(dict.fromkeys([args.frames, 1, keyframes[-2], keyframes[2], keyframes[-3], args.frames, 1]))
        result["bake_seek_order"] = order
        seek_error = replay(source, proxy, order, reference, scene.unit_settings.scale_length)
        result["bake_seek_error"] = seek_error
        report_check(result, "bake_random_seek_surface", max(seek_error.values()) <= guard,
                     maximum_error_m=seek_error, guard_m=guard)
        baked_modes_and_manual(source, rig, proxy, cloth, record, args.frames, reference,
                               scene.unit_settings.scale_length, result)
        result["protection"] = protection.verify()
        report_check(result, "original_models_rest_actions_nla_preserved", result["protection"]["success"],
                     details=result["protection"])
        physics.validate_physics(source)
        scene.frame_set(args.frames if case == "abrupt_stop" else max(1, round(args.frames * .5)))
        result["saved_visual_frame"] = scene.frame_current
        result["saved_frame_reference"] = {
            key: save_reference(args.output / f"reference_{case}_{key}.float32", reference[scene.frame_current][key])
            for key in ("final", "proxy")}
        # A readable scene Text keeps its own input declaration and visual plan.
        name = f"QA Read Me · {case}"
        text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
        text.clear()
        text.write(json.dumps({"purpose": "Synthetic representative Dress effect QA; not production acceptance",
                               "source": source.name, "action": action.name, "visual_keyframes": keyframes,
                               "original_animation_backup": "Scene CD_QA_AuthorAnimationBackup and CD_QA_AuthorAction ID references",
                               "collider_summary": result["collider_summary"], "checks": result["checks"]},
                              indent=2, ensure_ascii=False, allow_nan=False))
        result["candidate"] = save_candidate(candidate, args.input)
        result["candidate_file"] = file_state(candidate)
        result["cache_folder_hint"] = str(candidate.parent / ("blendcache_" + candidate.stem))
        result["success"] = all(check["passed"] for check in result["checks"])
    except Exception as error:
        result["exception"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        try:
            result["candidate"] = save_candidate(candidate, args.input)
        except Exception as save_error:
            result["failure_candidate_save_error"] = str(save_error)
    finally:
        result["elapsed_seconds"] = time.perf_counter() - started
        # Reference arrays are not dumped per frame, keeping report/memory small.
        (args.output / f"result_{case}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                                                  allow_nan=False), encoding="utf-8")
    return result


def main(args):
    isolation = require_isolated_background()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    report = {"success": False, "production_effect_accepted": False,
              "purpose": "Real saved-Cosha native Dress diagnostic with synthetic representative inputs",
              "artist_saved_by_verifier": False, "artist_path": str(args.input),
              "source_root": str(REPOSITORY), "version": list(character_designer.bl_info["version"]),
              "blender_version": bpy.app.version_string, "artist_before": file_state(args.input),
              "thresholds": {"replay_and_restore_guard_m": GEOMETRY_LIMIT_M,
                             "additional_native_world_guard": GEOMETRY_LIMIT_WORLD,
                             "diagnostic_penetration_m": args.max_penetration_mm / 1000.,
                             "diagnostic_stop_jitter_m_per_frame": args.max_stop_jitter_mm / 1000.,
                             "diagnostic_neighbor_edge_ratio": args.max_edge_ratio,
                             "origin": "Replay guard retained from prior real-X checks; other limits are explicit QA diagnostics"},
              "limits": ["Saved file only; no live unsaved scene is inspected",
                         "Synthetic inputs are not production walks, turns, squats or foot planting",
                         "Vertex signed distance does not prove absence of triangle intersections",
                         "Closed generated collision proxies are not the actual body mesh",
                         "60-frame default is a short diagnostic, not long-run equilibrium",
                         "Blender Cloth and Unity Magica Cloth require separate effect validation",
                         "No render or production animation acceptance is performed"],
              "cases": [], "checks": []}
    report["isolated_background_preflight"] = isolation
    report["source_files"] = {Path(module.__file__).name: file_state(Path(module.__file__)) for module in
                              (skirt, physics, profiles, tuning, original, limb_ik, limb_ik_fk)}
    report["planned_case_names"] = args.cases
    report["planned_frame_range"] = [1, args.frames]
    report["planned_evaluated_frame_passes"] = len(args.cases) * args.frames * 3
    protection = None
    try:
        character_designer.register()
        bpy.ops.wm.open_mainfile(filepath=str(args.input), load_ui=False, use_scripts=False)
        protection = Protection()
        report["protected_original_content"] = protection.summary()
        source, rig, record = owned_source(args.source)
        report["initial_saved_owned_cache"] = saved_cache_preflight(source, record)
        if not report["initial_saved_owned_cache"]["allowed"]:
            raise RuntimeError(report["initial_saved_owned_cache"]["reason"])
        # Preserve even an authored Action with no other user before the first
        # candidate save; public-operator failure must not discard that asset.
        for index, action in enumerate(protection.action_refs):
            bpy.context.scene[f"CD_QA_AuthorAction_{index:04d}"] = action
        # Move the copy's own filepath before any physics/cache or pose operation.
        save_candidate(args.output / "Cosha_Dress_QA_initial_copy.blend", args.input)
        report["ownership"] = {"source": source.name, "main_rig": rig.name, "owner": record["owner"],
                               "shared_registry_pointer_proved": True, "chain_count": record["chain_count"],
                               "segment_count": record["segment_count"], "shared_bone_names": record["shared"]["names"]}
        scene = bpy.context.scene
        scene.tool_settings.use_keyframe_insert_auto = False
        report["saved_frame"] = scene.frame_current
        report["initial_original_active"] = original.active(rig)
        skirt._activate(bpy.context, rig, "POSE")
        owner = rig.get(skirt.ORIGINAL_DISPLAY_OWNER_KEY)
        if original.active(rig) or owner:
            if isinstance(owner, bpy.types.Object) and owner.type == "ARMATURE" and original.active(owner):
                skirt._activate(bpy.context, owner, "POSE")
            public_switch(bpy.ops.character_designer.body_original_mode, action="CONTROLS")
            report["copy_only_original_exit"] = "Public Original/Controls operator FINISHED"
            skirt._activate(bpy.context, rig, "POSE")
        skirt._require_controls_for_setup(source)
        # Prove a saved physics graph BEFORE detaching any authored playback.
        # A proxy/PHYS animation or foreign target must not be hidden by QA.
        if record.get("physics"):
            physics.validate_physics(source)
            report["saved_physics_graph_proved_before_qa_overlay"] = True
        protected = protection.verify()
        report_check(report, "copy_original_exit_protected_data", protected["success"], details=protected)
        if not protected["success"]:
            raise RuntimeError("Original exit changed protected raw assets; preserving a failure candidate")
        relevant = [rig, source, source.data.shape_keys]
        relevant.extend(bpy.data.objects.get(name) for name in record.get("owned_objects", ()))
        report["author_animation_backup"] = backup_animation(scene, relevant, protection.action_refs)
        public_switch(bpy.ops.character_designer.body_ik_fk_switch, mode="FK")
        legs, axes, height = body_inputs(rig, skirt.read_record(source))
        report["input_definition"] = {"native_leg_chains": {side: list(item["chain"]) for side, item in legs.items()},
            "bone_local_rotation_axes": {name: tuple(axis) for name, axis in axes.items()},
            "height_world_units": height, "height_definition": "Body deform Rest head/tail Z extent excluding owned Dress, multiplied by rig world Z scale",
            "forward_axis": "MainRig local +Y", "up_axis": "MainRig local +Z", "leg_bend_axis": "MainRig Rest +X converted to each native bone local space",
            "motion_formulas": {"walk": "+Y .28*height, two sine cycles, +/-18 degree thighs and up to -20 degree shin swing",
                "turn": "100 degree smooth local-Z yaw plus .08*height forward",
                "leg_raise": "Left native thigh +55 degree and shin -20 degree smooth hold/release",
                "squat": "Both thighs +50, shins -85, feet +15 degrees; root -0.085*height; not planted feet",
                "abrupt_stop": "+Y .32*height travel stops by 55 percent; leg swing smoothly ends by that point"}}
        record = skirt.read_record(source)
        report["physics_present_in_saved_file"] = bool(record.get("physics"))
        if not record.get("physics"):
            physics.add_physics(bpy.context, source)
            report["physics_added_to_candidate_only"] = True
        record, rig, proxy, cloth = physics.validate_physics(source)
        profile = tuning.initialize(source, capability="BOTH" if report.get("physics_added_to_candidate_only") else None)
        tuning.apply(bpy.context, (source,), mode="AUTOMATIC")
        report["native_profile"] = profile
        report["scene_units_to_meters"] = scene.unit_settings.scale_length
        report["thresholds"]["actual_replay_and_restore_guard_m"] = geometry_guard(scene.unit_settings.scale_length)
        report["fps"] = scene.render.fps / scene.render.fps_base
        report["physics_graph_proved"] = {"proxy": proxy.name, "colliders": record["physics"]["colliders"],
                                          "rows": record["physics"]["rows"], "columns": record["physics"]["columns"]}
        body, report["registered_body_status"] = registered_body(bpy.context, rig, args)
        channels, basis, mode = pose_channels(rig), rig.matrix_basis.copy(), rig.rotation_mode
        # Each case starts by reopening this unbaked prepared copy. Reusing a
        # sealed disk cache and then freeing it for the next case could delete
        # the first saved candidate's cache files; independent loads avoid that.
        physics.clear_cache(bpy.context, source)
        cloth.point_cache.use_disk_cache = False
        scene.frame_start, scene.frame_end = 1, args.frames
        cloth.point_cache.frame_start, cloth.point_cache.frame_end = 1, args.frames
        cloth.point_cache.frame_step = 1
        physics.reset_simulation(bpy.context, source)
        prepared = args.output / "Cosha_Dress_QA_prepared.blend"
        report["prepared_copy"] = save_candidate(prepared, args.input)
        for case in args.cases:
            bpy.ops.wm.open_mainfile(filepath=str(prepared), load_ui=False, use_scripts=False)
            source, rig, record = owned_source(report["ownership"]["source"])
            record, rig, proxy, cloth = physics.validate_physics(source)
            legs, axes, height = body_inputs(rig, record)
            body, _body_status = registered_body(bpy.context, rig, args)
            report["cases"].append(run_case(case, args, source, rig, proxy, cloth, record, legs, axes, height,
                                            channels, basis, mode, protection, body=body))
            # A native procedural failure could leave a half-active session.
            # Stop; do not bypass proof and continue with a damaged copy.
            if "exception" in report["cases"][-1]:
                break
        report["final_protection"] = protection.verify()
        report_check(report, "original_assets_preserved_after_all_cases", report["final_protection"]["success"],
                     details=report["final_protection"])
        completed = [case for case in report["cases"] if "exception" not in case]
        report["candidate_save_reopen"] = []
        for saved in completed:
            bpy.ops.wm.open_mainfile(filepath=saved["candidate"], load_ui=False, use_scripts=False)
            source, rig, record = owned_source(report["ownership"]["source"])
            record, rig, proxy, cloth = physics.validate_physics(source)
            graph = bpy.context.evaluated_depsgraph_get()
            error = {key: packed_error(load_reference(saved["saved_frame_reference"][key]), world_mesh(obj, graph)["points"],
                                       bpy.context.scene.unit_settings.scale_length)
                     for key, obj in (("final", source), ("proxy", proxy))}
            report["candidate_save_reopen"].append({"path": saved["candidate"], "frame": bpy.context.scene.frame_current,
                                                     "is_baked": cloth.point_cache.is_baked, "error_m": error})
            guard = geometry_guard(bpy.context.scene.unit_settings.scale_length)
            report_check(report, "candidate_native_bake_save_reopen_" + saved["name"], cloth.point_cache.is_baked and
                         max(error.values()) <= guard, maximum_error_m=error, guard_m=guard)
        report["success"] = (len(report["cases"]) == len(args.cases) and all(case["success"] for case in report["cases"])
                             and all(check["passed"] for check in report["checks"]))
    except Exception as error:
        report["exception"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        if bpy.data.filepath and Path(bpy.data.filepath).resolve() != args.input:
            try:
                report["failure_candidate"] = save_candidate(args.output / "Cosha_Dress_QA_failure.blend", args.input)
            except Exception as save_error:
                report["failure_candidate_save_error"] = str(save_error)
    finally:
        report["source_files_after"] = {Path(module.__file__).name: file_state(Path(module.__file__)) for module in
                                        (skirt, physics, profiles, tuning, original, limb_ik, limb_ik_fk)}
        report_check(report, "canonical_source_files_unchanged_during_qa", report["source_files"] == report["source_files_after"])
        report["artist_after"] = file_state(args.input)
        report_check(report, "artist_file_unchanged", report["artist_before"] == report["artist_after"])
        report["success"] = report["success"] and all(check["passed"] for check in report["checks"])
        report["elapsed_seconds"] = time.perf_counter() - started
        report_path = args.output / "real_dress_effect_qa.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print("CD QA report:", report_path, "success:", report["success"], flush=True)
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main(arguments()))
