"""PREPARED ONLY: disposable Direct cold bind and private static-pose solve.

Root alone leases factory BG5.2. Current held/H, native leg/L and Manual/T are
captured at the unchanged author frame. Only independent world meshes and own
Keys/Actions advance internally. Their linear world path is not bone motion.
The two same-time L-hold/T branches prevent settling from masquerading as a
Manual response. A private Mesh can be written only after all finite gates;
artist application, runtime Recalculate, ART and general clearance stay false.
"""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import struct
import sys
import time
import traceback
from types import SimpleNamespace as NS

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
COLD = HERE / "verify_direct_cold_install52.py"
COLD_SHA = "acd898a2f4076d0cb92a1651ae661241d2a916d66bbfe490cc7bd803a2411ad6"
DIAG = HERE / "diagnose_skin_transfer.py"
DIAG_SHA = "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28"
QA = HERE / "validate_real_dress.py"
QA_SHA = "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046"
WINDING = HERE / "verify_live_direct_cloth52_movement_winding_collision.py"
WINDING_SHA = "3ef6233443a3c7c1845afd5843daba13389e32dea89a661f54d2c9b24addfb77"
PROGRESSIVE = HERE / "verify_live_direct_cloth52_progressive_manual.py"
PROGRESSIVE_SHA = "0c6c2747123460a31bb67ca7fb3038eed27189dfc296dd0648cfbf569ebc8bd6"
PROVIDER_SHA = "e4765407f998cc57f89e4ab0d1afd9607799c6abcfff2634cb3c340cba298e0d"
PINS = {COLD: COLD_SHA, DIAG: DIAG_SHA, QA: QA_SHA, WINDING: WINDING_SHA, PROGRESSIVE: PROGRESSIVE_SHA}
STAGE = "DIRECT52_PRIVATE_SAME_FRAME_WORLD_RECALCULATE_PROOF"
ENDPOINTS = {1: "N", 16: "H", 31: "L", 46: "T", 76: "hold_T"}
LIMITS = {"edge_min": .75, "edge_max": 1.25, "area_min": .5, "area_max": 1.5,
          "manual_gain_min": .25, "safe_manual_residual_rms_fraction_max": .75,
          "late_step_height_fraction_max": .001}


def need(value, message):
    if not value:
        raise RuntimeError("PrivateRecalculate52: " + message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            value.update(block)
    return value.hexdigest()


def definitions(path, expected, names, values):
    """Only specified frozen observer definitions; no old main/import gates."""
    need(sha(path) == expected, "Frozen helper changed: " + str(path))
    nodes = [n for n in ast.parse(path.read_text(encoding="utf-8")).body
             if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    need({n.name for n in nodes} == set(names), "Actual frozen helper ABI missing")
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), values)
    return NS(**values)


def route(frame, manual):
    need(type(frame) is int and 1 <= frame <= 76 and type(manual) is bool, "Exact owned76-frame route required")
    if frame <= 16: return ((frame-1)/15., 0., 0.)
    if frame <= 31:
        phase = (frame-16)/15.
        return (1.-phase, phase, 0.)
    phase = min(1., (frame-31)/15.) if manual else 0.
    return (0., 1.-phase, phase)


def points_on_path(endpoints, weights):
    need(len(endpoints) == 4 and all(len(row) == len(endpoints[0]) for row in endpoints), "Native endpoint identity differs")
    coefficients = (1.-sum(weights), *weights)
    need(min(coefficients) >= -1.e-14, "Invalid synthetic world coefficients")
    return [[math.fsum(float(row[i][axis])*coefficient for row, coefficient in zip(endpoints, coefficients))
             for axis in range(3)] for i in range(len(endpoints[0]))]


def precision(points, metres):
    need(math.isfinite(metres) and metres > 0 and points, "Finite physical input required")
    need(all(len(p) == 3 and all(math.isfinite(float(x)) for x in p) for p in points), "Nonfinite/incomplete world input")
    scale = max(abs(float(x)) for p in points for x in p)
    guard = max(1.e-7, 8.*2.**-23*scale*metres)
    need(guard <= 1.e-5, "World precision exceeds independent10um copy/path allowance")
    return {"metres": guard, "absolute_world_scale": scale, "units_to_metres": metres,
            "formula": "max(0.1um,8*Float32epsilon*absWorldScale*sceneMetres), capped10um; input readback only"}


def response(counter, observed, before, target, ids, metres):
    need(ids and len(set(ids)) == len(ids), "Manual safe region is empty/ambiguous: Unknown")
    wanted = [[float(target[i][j])-float(before[i][j]) for j in range(3)] for i in ids]
    actual = [[float(observed[i][j])-float(counter[i][j]) for j in range(3)] for i in ids]
    norm = math.fsum(x*x for row in wanted for x in row)
    need(norm > 0 and all(math.isfinite(x) for rows in (wanted, actual) for row in rows for x in row), "No finite actual Manual target signal")
    residual = math.sqrt(math.fsum((x-y)**2 for a,b in zip(actual,wanted) for x,y in zip(a,b))/len(ids))*metres
    target_rms = math.sqrt(norm/len(ids))*metres
    return {"vertices": len(ids), "ids": ids, "same_time_dot_gain": math.fsum(x*y for a,b in zip(actual,wanted) for x,y in zip(a,b))/norm,
            "response_rms_m": math.sqrt(math.fsum(x*x for row in actual for x in row)/len(ids))*metres,
            "target_rms_m": target_rms, "delta_residual_rms_m": residual,
            "delta_residual_rms_fraction": residual/target_rms, "artist_shape_acceptance": False}


def quality(reference, current):
    need(current["edges"] == reference["edges"] and current["faces"] == reference["faces"], "Native final index/topology changed")
    edge = []
    for a,b in current["edges"]:
        old = (reference["points"][a]-reference["points"][b]).length
        need(old > 1.e-12, "Degenerate native seed edge: Unknown")
        edge.append((current["points"][a]-current["points"][b]).length/old)
    area = []
    for a,b,c in current["triangles"]:
        def size(points): return (points[b]-points[a]).cross(points[c]-points[a]).length
        original = size(reference["points"])
        need(original > 1.e-20, "Degenerate current native corner triple at seed: Unknown")
        area.append(size(current["points"])/original)
    need(edge and area and all(math.isfinite(x) for x in edge+area), "Incomplete/nonfinite final quality")
    return {"edge_min": min(edge), "edge_max": max(edge), "area_min": min(area), "area_max": max(area),
            "triangulation_changed": current["triangles"] != reference["triangles"],
            "area_scope": "Actual current triangle corners compared at the same seed native indices; no unknown default",
            "self_intersection_checked": False}


def cold_proof(path, expected):
    need(Path(path).is_absolute() and Path(path).is_relative_to(HERE) and sha(path) == expected, "Actual Cold report path/SHA required")
    row = json.loads(Path(path).read_text(encoding="utf-8"))
    need(row.get("native_component_completed") is True and row.get("source_files_Artist_exact") is True
         and row.get("private_scene_disposed") is True and row.get("errors") == []
         and row.get("installed_backend") == "DIRECT_MAIN_CLOTH_V1"
         and row.get("fresh_bind", {}).get("native_bound") is True
         and row.get("raw_Rest_Actions_protection", {}).get("success") is True,
         "Cold component was failed, incomplete or Unknown; no borrowed success")
    need(any(value.get("label") == "late_bound" and value.get("exact") is True for value in row.get("rollback_checks", []))
         and any(value.get("label") == "late_validated" and value.get("exact") is True for value in row.get("rollback_checks", [])), "Actual late rollback proofs missing")
    need(sha(path) == expected, "Cold report changed during read")
    return {"path": str(path), "sha256": expected, "component_only": True, "old_effect_or_runtime_accepted": False}


def observers(bpy, q):
    from mathutils import Euler, Matrix, Quaternion, Vector
    from mathutils.bvhtree import BVHTree
    from character_designer import limb_ik, limb_ik_fk
    env = dict(vars(q), math=math, bpy=bpy, Vector=Vector, Matrix=Matrix, Quaternion=Quaternion,
               limb_ik=limb_ik, limb_ik_fk=limb_ik_fk, Path=Path, hashlib=hashlib)
    actual = definitions(QA, QA_SHA, ("body_inputs", "file_state", "curve_paths"), env)
    diag = definitions(DIAG, DIAG_SHA, ("require", "matrix", "vector", "json_content", "mesh_snapshot", "framing",
        "segment_triangle", "triangle_crossings", "native_render"), dict(bpy=bpy, qa=actual, math=math, json=json,
        Vector=Vector, Matrix=Matrix, Euler=Euler, Quaternion=Quaternion, BVHTree=BVHTree, struct=struct,
        time=time, traceback=traceback, Path=Path))
    winding = definitions(WINDING, WINDING_SHA, ("point3", "sub", "dot", "cross", "integer_winding", "ClosedWinding"),
        dict(need=need, math=math, defaultdict=defaultdict, FLOAT64_EPS=2.**-52))
    renderer = definitions(PROGRESSIVE, PROGRESSIVE_SHA, ("two_view_renderer",), dict(need=need, ast=ast, inspect=inspect)).two_view_renderer(diag)
    return actual, diag, winding, renderer


def contact(mesh, body, proxies, bounds, diag, winding, budget, metres, epsilon):
    complete = dict(mesh, free_indices=list(range(len(mesh["points"]))))
    band = dict(bounds)
    values = [(p-band["waist"]).dot(band["up"]) for data in (mesh, body, *proxies) for p in data["points"]]
    band["lower"], band["upper"] = min(values)-epsilon, max(values)+epsilon
    crossing = diag.triangle_crossings(complete, body, band, 20000, epsilon)
    result = {"crossing": crossing, "signed": [], "Unknown": False, "accepted": False}
    covered = (crossing.get("status") == "measured" and crossing["dress_region_triangles"] == len(mesh["triangles"])
        and crossing["body_region_triangles"] == len(body["triangles"]) and not any(crossing[key] for key in
        ("coplanar_unresolved", "degenerate_unresolved", "boundary_unresolved")))
    result["complete_triangles"] = covered
    for data in (body, *proxies):
        row = {"object": data["object"], "status": "Unknown", "sampled_vertices": 0, "inside_ids": [], "accepted": False}
        result["signed"].append(row)
        try:
            model = winding.ClosedWinding(data["points"], data["triangles"])
            row["closed_topology"] = model.proof
            for index, point in enumerate(mesh["points"]):
                budget()
                answer = model.classify(point)
                row["sampled_vertices"] += 1
                if answer["inside"]: row["inside_ids"].append(index)
            row["status"] = "measured"
        except Exception as error:
            row["error"] = repr(error); result["Unknown"] = True
            # Budget exhaustion still propagates; no further work after lease.
            budget()
    result["Unknown"] |= not covered or any(row["status"] != "measured" or row["sampled_vertices"] != 3040 for row in result["signed"])
    result["measured_zero"] = (not result["Unknown"] and crossing.get("actual_crossing_pair_count") == 0
                              and all(not row["inside_ids"] for row in result["signed"]))
    result["scope"] = "All3040, all native Body triangles and independent positive closed winding for Body+3 proxies. Open/boundary/budget Unknown is not outside. Self intersections unmeasured."
    return result


def run_private(bpy, p, q, direct, source, rig, body, report, write, budget, output):
    from mathutils import Matrix, Quaternion, Vector
    original_pose = p.primitive(q.pose_channels(rig)); original_frame = [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe]
    protected = q.Protection(); context = bpy.context; home = context.scene
    installed = direct.install(context, source, body=body, capability="BOTH")
    actual, template = direct.validate(source, rig, installed)
    need(p.primitive(q.pose_channels(rig)) == original_pose and protected.verify()["success"], "Fresh bind changed original pose/raw/Rest/Actions")
    saved_mode = direct.capture_mode(source, installed); direct.set_mode(source, installed, "MANUAL")
    input_obj = bpy.data.objects[installed["physics"]["surface"]["roles"]["INPUT_SURFACE"][0]]
    clone = input_obj.modifiers[1].target; proxy_objects = [bpy.data.objects[n] for n in installed["physics"]["colliders"][:-1]]
    need(input_obj.modifiers[1].is_bound and len(proxy_objects) == 3 and clone.data == body.data, "Fresh actual Body80/3proxy input missing")
    qa, diag, winding, renderer = observers(bpy, q)
    metres = home.unit_settings.scale_length; endpoints = {}; crop = {}; phase_data = {}
    tx = direct.shared._Transaction(context, source); tx.remember_keys(body.data.shape_keys)
    modes = {pb.name: pb.rotation_mode for pb in rig.pose.bones}
    def capture(label):
        budget(); graph = context.evaluated_depsgraph_get()
        need([home.frame_current, home.frame_subframe] == original_frame, "Endpoint sampling changed artist time")
        meshes = {"input": diag.mesh_snapshot(input_obj, graph), "Body": diag.mesh_snapshot(body, graph),
                  "BodyClone": diag.mesh_snapshot(clone, graph)}
        meshes.update({"proxy"+str(i): diag.mesh_snapshot(obj, graph) for i,obj in enumerate(proxy_objects)})
        need(len(meshes["input"]["points"]) == 800, "Native AfterBody800 endpoint missing")
        endpoints[label] = meshes; crop[label] = diag.framing(rig, installed, graph)
        phase_data[label] = {"frame": original_frame, "pose": p.primitive(q.pose_channels(rig)),
            "native_world": [list(row) for row in rig.evaluated_get(graph).matrix_world], "own_Dress_keys": False}
        return meshes
    try:
        capture("H"); legs, axes, height = qa.body_inputs(rig, installed)
        thigh = rig.pose.bones[legs["L"]["chain"][0]]; hem = rig.pose.bones[installed["controls"]["hem"]]
        need(not any(thigh.lock_rotation) and not thigh.lock_rotation_w and not hem.lock_location[0], "Authored input locked; no bypass")
        old_q = thigh.matrix_basis.to_quaternion(); old_hem = hem.location.copy()
        thigh.rotation_mode = "QUATERNION"; thigh.rotation_quaternion = old_q @ Quaternion(axes[thigh.name], -.55)
        rig.update_tag(); context.view_layer.update(); capture("L")
        hem.location = old_hem + Vector((-.04*height, 0., 0.)); rig.update_tag(); context.view_layer.update(); capture("T")
        for pb in rig.pose.bones: pb.rotation_mode = modes[pb.name]
        tx.restore_context()
        tx.rest(rig)
        for mod in body.modifiers:
            if mod.type == "ARMATURE" and mod.object is not None: tx.rest(mod.object)
        context.view_layer.update(); capture("N")
    finally:
        for pb in rig.pose.bones: pb.rotation_mode = modes[pb.name]
        tx.restore_context()
    need(p.primitive(q.pose_channels(rig)) == original_pose and protected.verify()["success"]
         and [home.frame_current, home.frame_subframe] == original_frame, "Endpoint capture failed to restore author inputs")
    for label in ("H", "L", "T"):
        for role, mesh in endpoints[label].items():
            base = endpoints["N"][role]
            need(mesh["edges"] == base["edges"] and mesh["faces"] == base["faces"] and len(mesh["points"]) == len(base["points"])
                 and mesh["weights"] == base["weights"], "Endpoint native indices/topology/weights changed")
    all_points = [point for meshes in endpoints.values() for mesh in meshes.values() for point in mesh["points"]]
    copy_guard = precision(all_points, metres); guard = copy_guard["metres"]
    ring = direct._ring_ids(installed, 800); hard = {i for i,v in enumerate(installed["physics"]["pin_weights"]) if v == 1.}
    need(len(ring) == 80 and hard == set(ring), "Actual hard80 membership differs")
    for role in ("Body", "BodyClone", "proxy0", "proxy1", "proxy2"):
        need(max((a-b).length*metres for a,b in zip(endpoints["L"][role]["points"], endpoints["T"][role]["points"])) <= guard, "Manual changed Body/proxy geometry")
    need(max((endpoints["L"]["input"]["points"][i]-endpoints["T"]["input"]["points"][i]).length*metres for i in ring) <= guard, "Manual changed actual Body-follow hard80")
    output.mkdir(); (output/"native_endpoints.json").write_text(json.dumps(diag.json_content({"endpoints": endpoints, "raw_inputs": phase_data,
        "precision": copy_guard, "fresh_bind": installed["physics"]["surface"]["bind_proof"], "accepted": False}), allow_nan=False), encoding="utf-8")
    data = {"stage": STAGE, "frames": 76, "artist_frame": original_frame, "input": "Four actual captured endpoints; synthetic linear world path only",
        "same_time_Lhold_counter": True, "physics": {"settings": direct.shared._rna(template.settings), "collision": direct.shared._rna(template.collision_settings),
        "effectors": direct.shared._rna(template.settings.effector_weights), "scene_gravity": list(home.gravity), "use_gravity": home.use_gravity},
        "pin_weights": installed["physics"]["pin_weights"], "input_precision": copy_guard, "limits": LIMITS, "contacts": {}, "steps": [],
        "preview_published": False, "mechanism_collected": False, "effect_accepted": False, "runtime_supported": False, "ART_accepted": False}
    report["private_recalculate"] = data; write()
    owned = {name: [] for name in ("objects", "meshes", "scenes", "keys", "actions")}; probes = []; targets = {}; results = {}; private = None
    def mesh_object(name, meshes, raw=None, manual=True):
        mesh = raw.copy() if raw is not None else bpy.data.meshes.new(name+" Mesh"); owned["meshes"].append(mesh)
        if raw is None: mesh.from_pydata(meshes[0]["points"], [], meshes[0]["faces"]); mesh.update()
        else:
            need(mesh.shape_keys is None and len(mesh.vertices) == 800, "Own copy cannot clear artist Keys or guess layout")
            mesh.vertices.foreach_set("co", [float(x) for point in meshes[0]["points"] for x in point])
        obj = bpy.data.objects.new(name, mesh); owned["objects"].append(obj); private.collection.objects.link(obj); obj.matrix_world = Matrix.Identity(4)
        basis = obj.shape_key_add(name="Native Safe N"); keys = mesh.shape_keys; owned["keys"].append((keys, keys.as_pointer(), mesh, obj))
        blocks = [obj.shape_key_add(name="Native "+label) for label in ("H", "L", "T")]
        for block, snapshot in zip([basis]+blocks, meshes): block.data.foreach_set("co", [float(x) for point in snapshot["points"] for x in point])
        action = bpy.data.actions.new(name+" private world path"); owned["actions"].append(action)
        keys.animation_data_create(); keys.animation_data.action = action
        for frame in (1, 16, 31, 46, 76):
            for block, value in zip(blocks, route(frame, manual)):
                block.value = value; need(block.keyframe_insert(data_path="value", frame=frame), "Own Key input failed")
        for curve in qa.curve_paths(action):
            for point in curve.keyframe_points: point.interpolation = "LINEAR"
        slot = keys.animation_data.action_slot
        need(slot is not None and slot.target_id_type == "KEY" and any(s.handle == slot.handle for s in action.slots), "Native own KEY Action slot missing")
        targets[obj.name] = (obj, meshes, manual)
        return obj
    def snapshot(obj, graph):
        value = diag.mesh_snapshot(obj, graph); need(all(math.isfinite(x) for point in value["points"] for x in point), "Nonfinite native private mesh")
        return value
    def subdiv(obj):
        originals = [mod for mod in source.modifiers if mod.type == "SUBSURF"]
        need(len(originals) == 1, "Actual artist one-level output Subsurf required")
        mod = obj.modifiers.new("Original native Subsurf", "SUBSURF"); direct.shared._copy_scalars(originals[0], mod)
        return mod
    try:
        private = bpy.data.scenes.new("QA private same-frame solve"); owned["scenes"].append(private)
        private.unit_settings.scale_length = metres; private.render.fps = 30; private.render.fps_base = 1.
        private.gravity = home.gravity; private.use_gravity = home.use_gravity; private.frame_start, private.frame_end = 1, 76
        private.tool_settings.use_keyframe_insert_auto = False; context.window.scene = private
        collisions = []
        for role, original in zip(("BodyClone", "proxy0", "proxy1", "proxy2"), (clone, *proxy_objects)):
            obj = mesh_object("QA "+role, [endpoints[label][role] for label in ("N", "H", "L", "T")])
            obj.modifiers.new("Native collision copy", "COLLISION"); direct.shared._copy_scalars(original.collision, obj.collision)
            collisions.append(obj)
        for branch, manual in (("Lhold", False), ("T", True)):
            obj = mesh_object("QA Cloth "+branch, [endpoints[label]["input"] for label in ("N", "H", "L", "T")], actual.data, manual)
            probe = obj.copy(); owned["objects"].append(probe); probes.append(probe); private.collection.objects.link(probe)
            cloth = obj.modifiers.new("Native private Cloth", "CLOTH")
            direct.shared._copy_scalars(template.settings, cloth.settings); direct.shared._copy_scalars(template.collision_settings, cloth.collision_settings)
            direct.shared._copy_scalars(template.settings.effector_weights, cloth.settings.effector_weights)
            cloth.settings.rest_shape_key = None; cloth.settings.use_dynamic_mesh = True; cloth.collision_settings.collection = private.collection
            cloth.point_cache.frame_start, cloth.point_cache.frame_end, cloth.point_cache.frame_step = 1, 76, 1
            cloth.point_cache.use_disk_cache = cloth.point_cache.use_external = False
            need(not cloth.point_cache.is_baked and not cloth.point_cache.is_baking, "New private cache not fresh")
            # A separate result object shares the computed C mesh only through
            # native ObjectInfo/absolute SampleIndex; it never reads artist C.
            final = obj.copy(); owned["objects"].append(final); final.data = obj.data
            private.collection.objects.link(final); subdiv(final)
            # This first prototype uses a copied native Cloth evaluation, not a
            # second cache: freeze final from the actual C readback below.
            final.modifiers.clear(); subdiv(final)
            results[branch] = (obj, probe, final, cloth)
        need(set(private.collection.objects) == set(owned["objects"]), "Private collision scene contains outside objects")
        # Cloth collision filtering must include only the four collision objs.
        from mathutils.bvhtree import BVHTree
        collections = []
        collision = bpy.data.collections.new("QA private exact collision targets"); collections.append(collision); private.collection.children.link(collision)
        for obj in collisions: private.collection.objects.unlink(obj); collision.objects.link(obj)
        for obj, probe, final, cloth in results.values(): cloth.collision_settings.collection = collision
        seed = None; last = {}; late = []; prefix = []
        for frame in range(1, 77):
            budget(); tick = time.perf_counter(); private.frame_set(frame); graph = context.evaluated_depsgraph_get()
            step = {"frame": frame, "frame_set_seconds": time.perf_counter()-tick, "GUI_FPS": False, "input_errors": {}}
            for name,(obj, meshes, manual) in targets.items():
                observed = snapshot(results["T"][1] if obj == results["T"][0] else results["Lhold"][1] if obj == results["Lhold"][0] else obj, graph)
                expected = points_on_path([mesh["points"] for mesh in meshes], route(frame, manual))
                err = max((Vector(a)-Vector(b)).length*metres for a,b in zip(observed["points"], expected))
                step["input_errors"][name] = err; need(err <= guard, "Private world input readback differs")
            outputs = {}
            for branch,(obj, probe, final, cloth) in results.items():
                c = snapshot(obj, graph); requested = snapshot(probe, graph)
                pin_error = max((c["points"][i]-requested["points"][i]).length*metres for i in ring)
                step[branch+"_hard80_m"] = pin_error; need(pin_error <= guard, "Forward private hard80 stale")
                # Native final uses actual C800 via an own per-frame mesh only;
                # no persistent runtime handler or artist/cached-C override.
                temp = bpy.data.meshes.new("QA actual C endpoint"); owned["meshes"].append(temp)
                temp.from_pydata(c["points"], [], c["faces"]); temp.update()
                old_data = final.data; final.data = temp; context.view_layer.update(); graph = context.evaluated_depsgraph_get()
                outputs[branch] = snapshot(final, graph)
                need(len(outputs[branch]["points"]) == 3040 and len(outputs[branch]["triangles"]) == 5760, "Actual native Subsurf3040 missing")
                if branch in last and frame >= 67: late.append((outputs[branch]["points"][i]-last[branch]["points"][i]).length*metres for i in range(3040))
                last[branch] = outputs[branch]
            if frame <= 31:
                delta = max((a-b).length*metres for a,b in zip(outputs["T"]["points"], outputs["Lhold"]["points"]))
                prefix.append(delta); need(delta <= guard, "Same input private branch prefix differs")
            data["steps"].append(step)
            if frame in ENDPOINTS:
                label = ENDPOINTS[frame]; body_now = snapshot(collisions[0], graph); proxies_now = [snapshot(obj, graph) for obj in collisions[1:]]
                bounds = crop["T" if label == "hold_T" else label]
                if frame == 1: seed = outputs["T"]
                rows = {}
                for branch, value in outputs.items():
                    value["free_indices"] = list(range(3040))
                    rows[branch] = {"contacts": contact(value, body_now, proxies_now, bounds, diag, winding, budget, metres, height*1.e-6), "quality": quality(seed, value)}
                data["contacts"][label] = rows; write()
                if frame == 1: need(all(row["contacts"]["measured_zero"] for row in rows.values()), "Safe REST seed Unknown/intersecting; target not used as initial cloth")
                if frame == 76:
                    directory = output/"actual_final"; directory.mkdir()
                    rendered = renderer(NS(output=directory, frame=frame), outputs["T"], body_now, bounds)
                    data["final_render"] = rendered; need(rendered.get("success") is True, "Actual final anterior/side image collection failed")
            write()
        data["last10_max_step_m"] = max(late); data["same_input_prefix_max_m"] = max(prefix)
        data["late_duration_seconds"] = 9/30.; data["equilibrium_claim"] = False
        data["mechanism_collected"] = True
        # No feasible-region/body-sign shortcut: target inspection is mandatory
        # before any Manual preservation or publication may be marked passed.
        data["preview_gate"] = {"passed": False, "reason": "Target3040/Body feasibility and same-time Manual safe-region response not yet collected by this prepared first interface", "Unknown": True}
        write()
    finally:
        context.window.scene = home
        cleanup = []
        for probe in reversed(probes):
            try: bpy.data.objects.remove(probe, do_unlink=True)
            except Exception as error: cleanup.append(repr(error))
        for keys, pointer, mesh, obj in owned["keys"]:
            try:
                users = bpy.data.user_map(subset={keys}).get(keys, set())
                need(users == {mesh} and mesh.users == 1, "Own Key acquired an outside/shared user")
                obj.shape_key_clear()
                need(not any(k.as_pointer() == pointer for k in bpy.data.shape_keys), "Own Key receipt still exists")
            except Exception as error: cleanup.append(repr(error))
        for obj in reversed(owned["objects"]):
            if obj in probes: continue
            try: bpy.data.objects.remove(obj, do_unlink=True)
            except Exception as error: cleanup.append(repr(error))
        for kind in ("meshes", "actions"):
            for value in reversed(owned[kind]):
                try:
                    need(value.users == 0, "Own data acquired an outside user")
                    bpy.data.batch_remove(ids=(value,))
                except Exception as error: cleanup.append(repr(error))
        for collection in locals().get("collections", []):
            try: bpy.data.collections.remove(collection)
            except Exception as error: cleanup.append(repr(error))
        if private is not None:
            try: bpy.data.scenes.remove(private)
            except Exception as error: cleanup.append(repr(error))
        direct.restore_mode(source, installed, saved_mode)
        data["owned_cleanup_errors"] = cleanup
        data["author_pose_frame_exact"] = (p.primitive(q.pose_channels(rig)) == original_pose and [home.frame_current, home.frame_subframe] == original_frame)
        data["author_raw_Rest_Actions_protection"] = protected.verify(); write()
        need(not cleanup and data["author_pose_frame_exact"] and data["author_raw_Rest_Actions_protection"]["success"], "Private cleanup/author protection incomplete")


def pure_checks():
    for path, value in PINS.items(): need(sha(path) == value, "Frozen dependency differs")
    need(route(1, True) == (0.,0.,0.) and route(16, True) == (1.,0.,0.) and route(31, True) == (0.,1.,0.)
         and route(46, True) == route(76, True) == (0.,0.,1.), "Captured endpoints route differs")
    need(all(route(i, False) == route(i, True) for i in range(1,32)) and route(76, False) == (0.,1.,0.), "Same-time counter prefix/hold differs")
    before = [[0.,0.,0.]]; target = [[1.,0.,0.]]
    need(response(before, target, before, target, [0], 1.)["same_time_dot_gain"] == 1., "Exact manual response control")
    need(response(before, before, before, target, [0], 1.)["same_time_dot_gain"] == 0., "Lost Manual could be labelled response")
    for frame in (0,77,True):
        try: route(frame, True)
        except RuntimeError: pass
        else: need(False, "Invalid frame accepted")
    print(json.dumps({"prepared_only": True, "native_run": False, "route_and_response_controls": 7,
                      "preview_gate": "Unknown until complete native target/final observers", "accepted": False}))


def main():
    own = argparse.ArgumentParser(add_help=False)
    own.add_argument("--cold-proof", type=Path, required=True); own.add_argument("--cold-proof-sha", required=True)
    own.add_argument("--preview-output", type=Path, required=True)
    args, rest = own.parse_known_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:])
    need(args.preview_output.is_absolute() and args.preview_output.is_relative_to(HERE) and not args.preview_output.exists(), "Fresh private output required")
    proof = cold_proof(args.cold_proof, args.cold_proof_sha)
    for path, value in PINS.items(): need(sha(path) == value, "Frozen observer/cold driver changed")
    spec = importlib.util.spec_from_file_location("private_recalc_frozen_cold", COLD); cold = importlib.util.module_from_spec(spec); spec.loader.exec_module(cold)
    def exercise(bpy, p, q, direct, source, rig, body, record, report, write, budget):
        need(sha(cold.PROVIDER) == PROVIDER_SHA and bpy.app.version[:2] == (5,2), "Exact Direct provider/native5.2 required")
        report["same_frame_scope"] = {"stage": STAGE, "actual_cold_proof": proof, "current_artist_equivalence_to_7ac": "Unmeasured",
            "original_Cold_Original_edit_recipe_repeated": False, "artist_applied": False, "runtime_Recalculate_supported": False}
        report["installed_backend"] = direct.BACKEND
        run_private(bpy, p, q, direct, source, rig, body, report, write, budget, args.preview_output)
        report["native_component_completed"] = report["private_recalculate"]["mechanism_collected"]
    cold.exercise = exercise
    sys.argv = [sys.argv[0], "--"]+rest
    return cold.main()


if __name__ == "__main__":
    if "--pure-checks" in sys.argv: pure_checks()
    else: raise SystemExit(main())
