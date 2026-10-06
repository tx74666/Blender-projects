"""Private replay of exact 799efb world endpoints; one closed-proxy RNA change.

Never imports current Canonical, recaptures poses, edits an artist, or accepts
geometry. Pinned helper definitions are extracted without their module imports.
Open exact 7ac only to read four native CollisionSettings, then factory-clear.
N/L/T are recorded endpoint interpolation, not actual intermediate bone motion.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time
import traceback
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OLD = HERE / "actual_body_follow_v2_51_20261006_124313_276/result"
ENDPOINTS = OLD / "native_endpoints.json"
REPORT = OLD / "body_follow_contact_preview.json"
INPUT = HERE / "actual_install_51_20261006_031045_111/scenes/Cosha_Dress_QA_surface_install.blend"
INSTALL = INPUT.parent.parent / "result/workflow_install.json"
PINS = {
    ENDPOINTS: "4551d6e76a068358872a48f8105da06af4530b945a74f758fbca33b3e0721753",
    REPORT: "76190e8bf563e713ad181076f0ff44a74265461dc56eda333869fe0e77a21890",
    INPUT: "7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f",
    INSTALL: "a2157ba399bfe32cc28401847c2556f776761fd607eaa3ba7ea23b61aaec6a32",
    HERE / "prototype_static_final_cloth_relax.py": "06b7f1656dcb8a68ad5ddf9b92ec005a6b7c3cf2968eb60825e48f5de5721e1e",
    HERE / "prototype_static_continuous_contact_preview.py": "9366a924d4bf5e1cfe30dafa8ceef020db774130d9c66e153fc661517988f8fe",
    HERE / "verify_actual_body_proxy_coverage.py": "a232ae99e26a998f911c38efd1b95fcc45fb4c76ebd5d3a2c87bd8686196a055",
    HERE / "validate_real_dress.py": "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046",
    HERE / "diagnose_skin_transfer.py": "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28",
}


def need(ok, message):
    if not ok: raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""): h.update(block)
    return h.hexdigest()


def definitions(name, names, environment):
    """Compile only named frozen definitions: no top-level imports or startup."""
    path = HERE / name
    need(sha(path) == PINS[path], "Frozen helper changed: " + name)
    nodes = [n for n in ast.parse(path.read_text(encoding="utf-8")).body
             if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    need({n.name for n in nodes} == set(names), "Missing exact frozen helper definitions")
    namespace = dict(environment)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return SimpleNamespace(**{n.name: namespace[n.name] for n in nodes})


def scalars(owner):
    return {p.identifier: list(getattr(owner, p.identifier)) if getattr(p, 'is_array', False) else getattr(owner, p.identifier)
            for p in owner.bl_rna.properties if not p.is_readonly
            and p.type in {"BOOLEAN", "INT", "FLOAT", "ENUM", "STRING"}}


def apply_scalars(values, owner):
    for name, value in values.items():
        prop = owner.bl_rna.properties.get(name)
        if prop is not None and prop.type == "POINTER": continue
        need(prop is not None and not prop.is_readonly and prop.type in {"BOOLEAN", "INT", "FLOAT", "ENUM", "STRING"},
             "Unresolved saved scalar RNA: " + name)
        setattr(owner, name, value)
    observed = scalars(owner)
    need(all(observed[name] == value for name, value in values.items() if name in observed), "Native scalar copy changed recorded values")


def closed(mesh, Vector):
    """Same closed/connected/positive-winding contract, on exact frozen geometry."""
    faces = mesh["faces"]; count = len(mesh["points"])
    need(count >= 4 and faces and all(len(f) >= 3 and len(set(f)) == len(f) for f in faces), "Incomplete closed proxy")
    uses = Counter(tuple(sorted((a, b))) for f in faces for a, b in zip(f, f[1:] + f[:1]))
    need(all(n == 2 for n in uses.values()) and set(uses) == {tuple(sorted(e)) for e in mesh["edges"]}, "Proxy is not closed")
    adjacent = {i: set() for i in range(count)}
    for a, b in uses: adjacent[a].add(b); adjacent[b].add(a)
    seen = set(); pending = [0]
    while pending:
        i = pending.pop()
        if i not in seen: seen.add(i); pending.extend(adjacent[i] - seen)
    need(len(seen) == count, "Proxy is not connected")
    points = [Vector(p) for p in mesh["points"]]
    volume = sum(points[f[0]].dot(points[a].cross(points[b])) / 6.
                 for f in faces for a, b in zip(f[1:-1], f[2:]))
    need(math.isfinite(volume) and volume > 1.e-14, "Proxy winding/volume unresolved")
    return {"closed": True, "connected": True, "positive_volume_world3": volume}


def inventory(bpy):
    return {name: sorted((x.name, x.as_pointer()) for x in getattr(bpy.data, name))
            for name in ("objects", "meshes", "shape_keys", "actions", "scenes", "collections", "cameras")}


def arguments():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-seconds", type=float, default=170.)
    p.add_argument("--triangle-pair-limit", type=int, default=10000)
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1:])
    need(args.output.is_absolute() and not args.output.exists(), "Fresh absolute private output required")
    need(0. < args.max_seconds <= 180. and args.triangle_pair_limit == 10000, "Keep original pair budget; root controls the external lease")
    return args


def main(args):
    import bpy
    from mathutils import Euler, Matrix, Quaternion, Vector
    from mathutils.bvhtree import BVHTree
    need(bpy.app.background and bpy.app.version[:2] == (5, 1) and not bpy.data.filepath
         and "--factory-startup" in sys.argv and "--disable-autoexec" in sys.argv
         and "--threads" in sys.argv and sys.argv[sys.argv.index("--threads") + 1] == "1", "Empty leased factory Blender5.1 only")
    need(all(sha(p) == value for p, value in PINS.items()), "Fixed input/helper hash changed")
    common = dict(bpy=bpy, math=math, hashlib=hashlib, json=json, Path=Path, struct=struct,
                  traceback=traceback, time=time, Matrix=Matrix, Euler=Euler, Quaternion=Quaternion, Vector=Vector, BVHTree=BVHTree)
    qa = definitions("validate_real_dress.py", {"digest", "file_state", "curve_paths", "save_candidate", "ClosedCollider", "collision_metrics"}, common)
    diag = definitions("diagnose_skin_transfer.py", {"require", "matrix", "vector", "json_content", "segment_triangle", "triangle_crossings", "native_render"}, {**common, "qa": qa})
    read = definitions("verify_actual_body_proxy_coverage.py", {"need", "sha", "digest", "matrix", "native_mesh", "body_collision_comparison"}, common)
    static = definitions("prototype_static_final_cloth_relax.py", {"need", "freeze", "metrics"}, common)
    continuous = definitions("prototype_static_continuous_contact_preview.py", {"need", "path_weights", "path_points", "point_delta", "readback_guard", "residual", "normal_diagnostics", "animate"}, common)
    old = json.loads(REPORT.read_text(encoding="utf-8")); saved = json.loads(ENDPOINTS.read_text(encoding="utf-8"))
    need(old["native_completed"] and old["accepted"] is False and saved["frame"] == 1, "799 native evidence incomplete")
    endpoints = saved["endpoints"]; names = list(endpoints["N"]); collider_names = [n for n in names if n not in {"O3040", "RegisteredBody"}]
    need(len(names) == 6 and len(collider_names) == 4 and all(set(endpoints[x]) == set(names) for x in ("N", "L", "T")), "Exact six endpoint inventories required")
    fixed = saved["fixed160"]; original = endpoints["T"]["O3040"]; parameters = old["parameters"]; meters = saved["units_to_metres"]
    need(parameters["private_steps"] == 30 and parameters["soft_goal_raw_weight"] == .5 and parameters["hard160"] == fixed
         and parameters["units_to_metres"] == meters and len(fixed) == len(set(fixed)) == 160, "799 path/units/pin semantics changed")
    for label in ("N", "L", "T"):
        for name, mesh in endpoints[label].items():
            need(mesh["native_vertex_index_order"] == list(range(len(mesh["points"]))) and mesh["weights_complete"], "Endpoint indices/weights unresolved")
            need(all(len(p) == 3 and all(math.isfinite(float(x)) for x in p) for p in mesh["points"]), "Nonfinite endpoint")
            need(all(mesh[k] == endpoints["N"][name][k] for k in ("native_vertex_index_order", "faces", "edges", "weights", "native_group_mapping")), "Endpoint topology/weights changed")
    # Compare the original JSON containers before normalising every endpoint.
    for meshes in endpoints.values():
        for mesh in meshes.values():
            for field in ("faces", "edges", "triangles"): mesh[field] = [tuple(x) for x in mesh[field]]
    need(len(original["points"]) == 3040 and all(0 <= i < 3040 for i in fixed), "Exact final3040/fixed160 missing")
    guard = continuous.readback_guard((p for meshes in endpoints.values() for m in meshes.values() for p in m["points"]), meters)
    need(guard == old["native_input_guard"], "Original independent precision allowance changed")
    bounds = dict(saved["evidence"]["T"]["bounds"])
    for key in ("waist", "up", "right", "forward"): bounds[key] = Vector(bounds[key])
    bounds["knees"] = {k: Vector(v) for k, v in bounds["knees"].items()}
    artist = Path(json.loads(INSTALL.read_text(encoding="utf-8"))["artist_path"])
    before = {str(p): qa.file_state(p) for p in [*PINS, artist]}; own = sha(Path(__file__))
    args.output.mkdir(); destination = args.output / "closed_proxy_normals_replay.json"
    report = {"native_completed": False, "accepted": False, "artist_saved": False, "script_sha256": own,
              "fixed_files_before": before, "pins": {str(p): h for p, h in PINS.items()}, "parameters_from_799": parameters,
              "source_version_from_799": old["source_before"], "scope": "Exact recorded799 N/L/T world-vertex interpolation; no recapture or current Canonical import, not actual intermediate bone motion or GUI FPS", "samples": {}, "path_readback": []}
    def write(): destination.write_text(json.dumps(diag.json_content(report), indent=2, allow_nan=False), encoding="utf-8")
    started = time.perf_counter(); ids = {k: [] for k in ("objects", "meshes", "collections", "scenes", "keys", "actions")}
    home = probe = None; baseline = None
    def budget(): need(time.perf_counter() - started < args.max_seconds, "Soft phase budget exhausted; root must enforce external lease")
    try:
        need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(INPUT), load_ui=False, use_scripts=False), "Exact7ac read failed")
        need(Path(bpy.data.filepath).resolve() == INPUT.resolve(), "Native input path differs")
        collider_settings = {}; collision_modifiers = {}
        for name in collider_names:
            obj = bpy.data.objects.get(name)
            need(obj is not None and obj.type == "MESH" and len([m for m in obj.modifiers if m.type == "COLLISION"]) == 1, "Native collider identity/modifier missing")
            modifier = next(m for m in obj.modifiers if m.type == "COLLISION")
            collision_modifiers[name] = {"name": modifier.name, "show_viewport": bool(modifier.show_viewport), "show_render": bool(modifier.show_render)}
            need(modifier.show_viewport and modifier.show_render, "Read input collider is disabled; replay would not preserve its semantics")
            collider_settings[name] = scalars(obj.collision)
        report["observed_7ac_collider_scalars"] = collider_settings; report["observed_7ac_collision_modifiers"] = collision_modifiers; write()
        need("FINISHED" in bpy.ops.wm.read_factory_settings(use_empty=True), "Read-only input factory-clear failed")
        need(not bpy.data.filepath, "Factory graph still has an input filepath")
        home = bpy.context.scene; baseline = inventory(bpy)
        proxy_names, clone_name = collider_names[:3], collider_names[-1]
        need(all("Collider" in n for n in proxy_names) and "Body Collision" in clone_name, "Fixed recorded collider roles ambiguous")
        report["closed_endpoint_proof"] = {label: {name: closed(endpoints[label][name], Vector) for name in proxy_names} for label in ("N", "L", "T")}
        need(all("use_normal" in collider_settings[n] and "use_culling" in collider_settings[n] for n in collider_names), "Native normal/culling flags unavailable")
        if all(collider_settings[n]["use_normal"] for n in proxy_names):
            report["skipped_no_parameter_change"] = True
            report["skip_reason"] = "All three closed proxies already use Override Normals; no duplicate simulation or effect claim"
        else:
            private = bpy.data.scenes.new("Closed Proxy Normal Replay"); ids["scenes"].append(private)
            private.frame_start, private.frame_end = 1, 31; private.gravity = (0., 0., 0.); private.use_gravity = False
            private.unit_settings.scale_length = meters; private.render.fps = parameters["fps"]; private.render.fps_base = parameters["fps_base"]
            collision = bpy.data.collections.new("Continuous Native Collision"); ids["collections"].append(collision); private.collection.children.link(collision)
            dress = static.freeze(endpoints["N"]["O3040"], "Replay Dress", private.collection, ids, bpy)
            pin = dress.vertex_groups.new(name="Continuous Target Goal"); pin.add(fixed, 1., "REPLACE")
            need(pin.name == parameters["cloth"]["vertex_group_mass"], "Exact799 goal name would collide with original groups")
            free = [i for i in range(3040) if i not in set(fixed)]; pin.add(free, .5, "REPLACE")
            animated = {"O3040": dress}; animation = {"O3040": continuous.animate(dress, *(endpoints[x]["O3040"] for x in ("N", "L", "T")), 30, ids, bpy, qa)}
            for name in ["RegisteredBody", *collider_names]:
                obj = static.freeze(endpoints["N"][name], "Replay " + name, private.collection if name == "RegisteredBody" else collision, ids, bpy)
                animated[name] = obj; animation[name] = continuous.animate(obj, *(endpoints[x][name] for x in ("N", "L", "T")), 30, ids, bpy, qa)
                if name in collider_names:
                    obj.modifiers.new("Replay Collision", "COLLISION"); apply_scalars(collider_settings[name], obj.collision)
                    if name in proxy_names: obj.collision.use_normal = True
                    expected = dict(collider_settings[name]); expected["use_normal"] = True if name in proxy_names else expected["use_normal"]
                    need(scalars(obj.collision) == expected, "More than closed-proxy Override Normals changed")
            probe = dress.copy(); ids["objects"].append(probe); probe.name = "Replay Pre-Cloth Input"; private.collection.objects.link(probe); probe.hide_render = True
            need(probe.data == dress.data and len(probe.modifiers) == 0 and [(g.name, g.index, g.lock_weight) for g in probe.vertex_groups] == [(g.name, g.index, g.lock_weight) for g in dress.vertex_groups], "Shared readback probe differs")
            cloth = dress.modifiers.new("Replay Cloth", "CLOTH")
            apply_scalars(parameters["cloth"], cloth.settings); apply_scalars(parameters["collision"], cloth.collision_settings); apply_scalars(parameters["effectors"], cloth.settings.effector_weights)
            cloth.settings.rest_shape_key = None; cloth.settings.effector_weights.collection = None; cloth.collision_settings.collection = collision
            cloth.point_cache.frame_start, cloth.point_cache.frame_end, cloth.point_cache.frame_step = 1, 31, 1
            need(not cloth.point_cache.is_baked and not cloth.point_cache.use_external, "New cache unexpectedly sealed/external")
            need(bpy.context.window is not None, "Background Scene switch unavailable")
            bpy.context.window.scene = private; private.frame_set(1); bpy.context.view_layer.update()
            qa.save_candidate(args.output / "scenes/Cosha_Closed_Proxy_Normal_Replay.blend", INPUT)
            cache = args.output / "private_cache"; cache.mkdir(); cloth.point_cache.filepath = str(cache); cloth.point_cache.use_library_path = False; cloth.point_cache.use_disk_cache = True
            need(Path(bpy.path.abspath(cloth.point_cache.filepath)).resolve() == cache.resolve(), "Private cache path escaped")
            report["only_parameter_change"] = {n: {"before": collider_settings[n]["use_normal"], "after": True} for n in proxy_names}
            report["body_collider_parameters_exact"] = scalars(animated[clone_name].collision) == collider_settings[clone_name]
            report["native_Cloth_scalars"] = scalars(cloth.settings); report["native_collision_scalars"] = scalars(cloth.collision_settings)
            influenced = [i for i, delta in enumerate(continuous.point_delta(endpoints["L"]["O3040"]["points"], original["points"], meters)) if delta > guard["metres"]]
            need(influenced and set(influenced).isdisjoint(fixed), "Recorded Manual region/fixed isolation changed")
            final = None
            for frame in range(1, 32):
                budget(); start = time.perf_counter(); private.frame_set(frame); bpy.context.view_layer.update(); graph = bpy.context.evaluated_depsgraph_get()
                observed = {name: read.native_mesh(probe if name == "O3040" else obj, graph, diag) for name, obj in animated.items()}
                cloth_mesh = read.native_mesh(dress, graph, diag); row = {"frame": frame, "native_update_and_all_mesh_read_seconds": time.perf_counter() - start, "input_errors_m": {}}
                weights = continuous.path_weights(frame, 30)
                for name, mesh in {**observed, "simulated": cloth_mesh}.items():
                    origin = endpoints["N"]["O3040" if name == "simulated" else name]
                    need(all(mesh[k] == origin[k] for k in ("native_vertex_index_order", "faces", "edges")), "Native replay connectivity/index changed")
                    filtered = [[x for x in items if x["index"] != pin.index] for items in mesh["weights"]] if name in {"O3040", "simulated"} else mesh["weights"]
                    mapping = [x for x in mesh["native_group_mapping"] if x["index"] != pin.index] if name in {"O3040", "simulated"} else mesh["native_group_mapping"]
                    need(filtered == origin["weights"] and mapping == origin["native_group_mapping"], "Native original weights/groups changed")
                    if name != "simulated":
                        expected = continuous.path_points(*(endpoints[x][name]["points"] for x in ("N", "L", "T")), weights)
                        row["input_errors_m"][name] = max(continuous.point_delta(mesh["points"], expected, meters))
                        need(row["input_errors_m"][name] <= guard["metres"], "Native frozen input response differs")
                        keys = animation[name]["keys"].evaluated_get(graph)
                        need(all(abs(keys.key_blocks[b.name].value - v) <= 1.e-6 for b, v in zip(animation[name]["blocks"], weights)), "Native Key path values differ")
                need(all(next((x["weight"] for x in items if x["index"] == pin.index), None) == (1. if i in set(fixed) else .5) for i, items in enumerate(cloth_mesh["weights"])), "Native exact160/soft2880 weights changed")
                row["current_target_hard160"] = continuous.residual(cloth_mesh["points"], observed["O3040"]["points"], fixed, meters)
                need(row["current_target_hard160"]["maximum_m"] <= guard["metres"], "Native moving hard160 exceeds original independent allowance")
                report["path_readback"].append(row)
                if frame in (1, 16, 31):
                    label = {1: "initial", 16: "leg", 31: "final"}[frame]; cloth_mesh["free_indices"] = free
                    epsilon = max(1.e-8, (bounds["upper"] - bounds["lower"]) * 1.e-6)
                    crossings = {name: diag.triangle_crossings(cloth_mesh, mesh, bounds, args.triangle_pair_limit, epsilon) for name, mesh in observed.items() if name != "O3040"}
                    need(all(x.get("status") == "measured" for x in crossings.values()), "Native triangle crossings unresolved/budget-exhausted")
                    distances = {}
                    for name in proxy_names:
                        closed(observed[name], Vector); collider = qa.ClosedCollider(animated[name], graph, epsilon, mesh=observed[name])
                        distances[name] = qa.collision_metrics(cloth_mesh["points"], collider, meters, free)
                    report["samples"][label] = {"frame": frame, "strict_crossings": crossings, "closed_proxy_sampled_vertex_distance": distances,
                        "quality_relative_safe_rest_N": static.metrics(endpoints["N"]["O3040"]["points"], cloth_mesh["points"], original["edges"], cloth_mesh["triangles"], fixed, meters),
                        "quality_relative_current_target": static.metrics(observed["O3040"]["points"], cloth_mesh["points"], original["edges"], cloth_mesh["triangles"], fixed, meters),
                        "normal_diagnostics_relative_current_target": continuous.normal_diagnostics(observed["O3040"]["points"], cloth_mesh["points"], cloth_mesh["triangles"]),
                        "target_residual_all": continuous.residual(cloth_mesh["points"], observed["O3040"]["points"], list(range(3040)), meters),
                        "target_residual_manual_region": continuous.residual(cloth_mesh["points"], observed["O3040"]["points"], influenced, meters), "accepted": False}
                    (args.output / (label + "_native_sample.json")).write_text(json.dumps(diag.json_content({"observed_input_and_bodies": observed, "simulated_cloth": cloth_mesh}), allow_nan=False), encoding="utf-8")
                    write(); print("Replay closed normals sample: " + label, flush=True)
                    if frame == 31: final = cloth_mesh
            need(final is not None and len(report["path_readback"]) == 31, "Replay did not collect complete30steps")
            for mesh in (original, endpoints["T"]["RegisteredBody"]): mesh["points"] = [Vector(p) for p in mesh["points"]]
            report["render"] = {}
            for label, mesh in (("requested_target", original), ("continuous_final", final)):
                budget(); folder = args.output / label; folder.mkdir()
                report["render"][label] = diag.native_render(SimpleNamespace(frame=31, output=folder), mesh, endpoints["T"]["RegisteredBody"], bounds)
                report["render"][label].update(source_author_frame=1, private_synthetic_frame=31, provenance="Recorded799 source frame1 T or synthetic replay frame31; same recorded target Body, no author Action result at31")
            need(all(r.get("success") and set(r.get("views", {})) == {"front", "side", "back"} for r in report["render"].values()), "Six actual renders incomplete")
            report["six_native_images_collected"] = True; report["native_completed"] = True
    except Exception as error:
        report["native_completed"] = False; report["error"] = {"reason": str(error), "traceback": traceback.format_exc()}
    finally:
        try:
            if home is not None: bpy.context.window.scene = home
            receipts = {kind: [(x.name, x.as_pointer()) for x in items] for kind, items in ids.items()}
            if probe is not None: bpy.data.objects.remove(probe, do_unlink=True)
            for name, pointer in receipts["keys"]:
                key = bpy.data.shape_keys.get(name); need(key is not None and key.as_pointer() == pointer, "Owned Key identity changed")
                owners = bpy.data.user_map(subset={key}).get(key, set()); need(len(owners) == 1, "Owned Key has outside/nonunique users")
                mesh = next(iter(owners)); need(mesh in ids["meshes"] and mesh.shape_keys == key and mesh.users == 1, "Owned Key Mesh is not uniquely private")
                obj = [o for o in ids["objects"] if o is not probe and o.data == mesh]; need(len(obj) == 1, "Exact animated object missing")
                obj[0].shape_key_clear(); need(mesh.shape_keys is None, "Owned Key failed to detach")
                remaining = bpy.data.shape_keys.get(name)
                if remaining is not None:
                    need(remaining.as_pointer() == pointer and not bpy.data.user_map(subset={remaining}).get(remaining, set()), "Detached Key acquired outside users")
                    bpy.data.batch_remove(ids=(remaining,))
            for obj in reversed(ids["objects"]):
                if obj is not probe: bpy.data.objects.remove(obj, do_unlink=True)
            for scene in ids["scenes"]: bpy.data.scenes.remove(scene)
            for collection in ids["collections"]: bpy.data.collections.remove(collection)
            for mesh in ids["meshes"]: need(mesh.users == 0, "Owned mesh still referenced"); bpy.data.meshes.remove(mesh)
            for action in ids["actions"]: need(action.users == 0, "Owned Action has outside users"); bpy.data.actions.remove(action)
            need(baseline is None or inventory(bpy) == baseline, "Factory private ID inventory not restored")
            report["only_exact_owned_ids_removed"] = True
        except Exception as error:
            report["cleanup_error"] = str(error); report["native_completed"] = False
        report["fixed_files_after"] = {str(p): qa.file_state(p) for p in [*PINS, artist]}
        report["fixed_files_exact"] = report["fixed_files_after"] == before
        report["script_exact"] = sha(Path(__file__)) == own
        report["native_completed"] &= report["fixed_files_exact"] and report["script_exact"]
        report["ready_for_independent_evaluation"] = bool(report["native_completed"] and report.get("six_native_images_collected"))
        report["elapsed_seconds"] = time.perf_counter() - started; write()
        print(json.dumps({"native_completed": report["native_completed"], "accepted": False, "skipped_no_parameter_change": report.get("skipped_no_parameter_change", False), "report": str(destination)}), flush=True)
    return 0 if report["native_completed"] or report.get("skipped_no_parameter_change") and report["fixed_files_exact"] and report["script_exact"] and report.get("only_exact_owned_ids_removed") else 2


if __name__ == "__main__": raise SystemExit(main(arguments()))
