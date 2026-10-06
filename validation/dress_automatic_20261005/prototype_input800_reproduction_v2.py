"""PREPARED ONLY: INPUT800_REPRODUCTION, no new/evaluated Cloth or bake.

Root alone leases factory Blender 5.1/disable-autoexec/threads1. Exact 7ac is
read, never overwritten. N/L/T are public Manual/FK, at the saved author frame;
Key values are not varied. Owned input-only Rig/wires/native skin reproduce the
manual-only pre-Subdivision oracle. Original raw channels are snapshot replay,
not a claim of live Original integration. Body attachment is a separate layer.
V2 changes only the raw authored-channel guard: native finite TRS replay can
preserve signed/nonuniform scale. It compares source/private native basis
getters after exact RNA channel replay, not an evaluated/sheared pose matrix.
No artist application, render, timeline travel, runtime handler or acceptance.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPOSITORY = Path(r"D:\MyRepository\Blender-addons-by-Randy")
INPUT = HERE / "actual_install_51_20261006_031045_111/scenes/Cosha_Dress_QA_surface_install.blend"
INSTALL = INPUT.parent.parent / "result/workflow_install.json"
ARTIST = HERE.parent.parent / "X.blend"
SURFACE = REPOSITORY / "addons/character_designer/skirt_surface.py"
WORKER = SURFACE.parent / "unity_export_worker.py"
PINS = {
    HERE / "prototype_input800_reproduction.py": "d3967d5d212ee2660b432c0f31c3ce33262d31bc6510d46cbe202a10ad726bc1",
    INPUT: "7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f",
    INSTALL: "a2157ba399bfe32cc28401847c2556f776761fd607eaa3ba7ea23b61aaec6a32",
    ARTIST: "2b36fb936082cbe7a81dd29e1dba22b9f9fbefa935015bfb29cc37b5b496ca9a",
    SURFACE: "9d7a928e27464e772330304d03e9ca81462f800951b3172921c87429cf78891c",
    WORKER: "069fb0f21b02e36a23dd02b1978d2a917c2873f290fc3331cdf0d55e877ce5bc",
    HERE / "verify_actual_surface_workflow.py": "2e8d82bbbde00604bf3f62bc17cbcb31244ed87290e083ebb17b25f4b9216140",
    HERE / "verify_actual_same_frame_pose.py": "812841f31309bea8ee923dd8299c0240ec1576d2ed4842ba46793c854d1830ff",
    HERE / "verify_actual_body_proxy_coverage.py": "a232ae99e26a998f911c38efd1b95fcc45fb4c76ebd5d3a2c87bd8686196a055",
    HERE / "validate_real_dress.py": "613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046",
    HERE / "diagnose_skin_transfer.py": "9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28",
}
CHANNELS = ("rotation_mode", "location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale")
GEOMETRY_GUARD_M = 5.e-5
RAW_NATIVE_BASIS_GUARD = 2.e-6  # Native matrix coefficients, not a geometry acceptance budget.


def need(ok, message):
    if not ok: raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""): h.update(block)
    return h.hexdigest()


def load(name):
    path = HERE / name
    need(sha(path) == PINS[path], "Frozen helper changed: " + name)
    spec = importlib.util.spec_from_file_location("input800_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # No helper main/arguments are invoked.
    return module


def conformal(matrix, label, tolerance=2.e-6):
    """Positive uniform orthogonal affine transform; no decompose/repair."""
    a = [[float(x) for x in row] for row in matrix]
    need(len(a) == 4 and all(len(row) == 4 and all(math.isfinite(x) for x in row) for row in a), label + ": finite affine 4x4 required")
    need(max(abs(a[3][i] - (1. if i == 3 else 0.)) for i in range(4)) <= 1.e-7, label + ": perspective refused")
    cols = [tuple(a[i][j] for i in range(3)) for j in range(3)]
    dot = lambda p, q: math.fsum(x*y for x, y in zip(p, q))
    lengths = [dot(c, c) for c in cols]; scale2 = max(lengths)
    determinant = (a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
                   - a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
                   + a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]))
    need(scale2 > 1.e-20 and determinant > 0., label + ": singular/mirrored transform refused")
    skew = max(abs(dot(cols[i], cols[j])) for i in range(3) for j in range(i))
    need(max(lengths)-min(lengths) <= scale2*tolerance and skew <= scale2*tolerance, label + ": nonuniform scale/shear refused")
    return {"positive_uniform_conformal": True, "scale": math.sqrt(sum(lengths)/3.), "relative_gram_tolerance": tolerance}


def native_trs_copy_proof(expected, original, copied, source_basis, copied_basis, source_connected, copied_connected, label):
    """Native RNA replay recomposes TRS, including connected-bone getter rules.

    No decompose/normalization/matrix setter is used. All stored representations
    are retained exactly; only the active mode affects Blender's basis getter.
    A constrained/evaluated bone matrix is not substituted for matrix_basis.
    """
    modes={"QUATERNION","AXIS_ANGLE","XYZ","XZY","YXZ","YZX","ZXY","ZYX"}
    need(set(expected)==set(CHANNELS) and expected["rotation_mode"] in modes,label+": incomplete native TRS/mode")
    for name,length in (("location",3),("rotation_euler",3),("rotation_quaternion",4),("rotation_axis_angle",4),("scale",3)):
        need(len(expected[name])==length and all(math.isfinite(float(x)) for x in expected[name]),label+": nonfinite native "+name)
    need(original==expected and copied==expected,label+": raw native channel replay differs")
    need(type(source_connected) is bool and type(copied_connected) is bool and source_connected==copied_connected,label+": connected-bone policy differs")
    matrices=[[[float(x) for x in row] for row in m] for m in (source_basis,copied_basis)]
    for matrix in matrices:
        need(len(matrix)==4 and all(len(row)==4 and all(math.isfinite(x) for x in row) for row in matrix),label+": nonfinite native basis")
        need(max(abs(matrix[3][i]-(1. if i==3 else 0.)) for i in range(4))<=1.e-7,label+": native basis is not affine")
        if source_connected: need(all(matrix[i][3]==0. for i in range(3)),label+": connected native getter translation differs")
    residual=max(abs(matrices[0][i][j]-matrices[1][i][j]) for i in range(4) for j in range(4))
    need(residual<=RAW_NATIVE_BASIS_GUARD,label+": native TRS recomposition residual exceeds unchanged2e-6 coefficient guard")
    return {"all_stored_native_channels_exact":True,"rotation_mode":expected["rotation_mode"],"signed_axis_scales":expected["scale"],
        "native_connected":source_connected,"raw_location_preserved":expected["location"],"native_basis_max_component_residual":residual,
        "native_basis_coefficient_guard":RAW_NATIVE_BASIS_GUARD,
        "recomposition":"Exact RNA replay; source/private native matrix_basis getters; connected getter translation0 without rewriting rawloc",
        "rotation_policy":"Blender native active Euler order/axis-angle/normalized quaternion; inactive stored channels unchanged",
        "scope":"Raw TRS only; object/upstream conformal and actual800 physical50um gates remain separate"}


def error_summary(actual, expected, metres, ids=None):
    need(len(actual) == len(expected) and actual and math.isfinite(metres) and metres > 0., "Exact finite point correspondence/physical units required")
    ids = list(range(len(actual))) if ids is None else list(ids)
    need(ids and len(set(ids)) == len(ids) and all(type(i) is int and 0 <= i < len(actual) for i in ids), "Explicit nonempty unique point IDs required")
    values = [math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(actual[i], expected[i])))*metres for i in ids]
    need(all(len(actual[i]) == len(expected[i]) == 3 for i in ids) and all(math.isfinite(v) for v in values), "Nonfinite/incomplete native points")
    worst = max(range(len(values)), key=values.__getitem__)
    return {"count": len(ids), "maximum_m": values[worst], "rms_m": math.sqrt(math.fsum(v*v for v in values)/len(values)), "worst_native_index": ids[worst]}


def allowed_edge(role, target, subtarget, input_name, main_name, upstream, controls, manual, wires, body_name):
    """Exact role whitelist. No tolerated unresolved or inferred dependency."""
    if role == "object_world": return target == main_name and subtarget == ""
    if role == "upstream": return target == main_name and subtarget in upstream
    if role == "manual_def": return target == input_name and subtarget in manual
    if role == "spline": return target in wires and subtarget == ""
    if role == "hook": return target == input_name and subtarget in controls
    if role == "wire_parent": return target == input_name and subtarget in upstream | {""}
    if role in {"mesh_parent", "skin"}: return target == input_name and subtarget == ""
    if role == "body_attachment": return target == body_name and subtarget == ""
    return False


def pure_checks():
    identity = [[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]]
    conformal(identity, "identity"); scaled = [row[:] for row in identity]
    for i in range(3): scaled[i][i] = .782
    scaled[0][3] = 7.; conformal(scaled, "translated uniform")
    rejected = 0
    for i,j,value in ((0,0,2.),(0,1,.01),(0,0,-1.),(3,0,.01)):
        bad = [row[:] for row in identity]; bad[i][j] = value
        try: conformal(bad, "negative control")
        except RuntimeError: rejected += 1
    need(rejected == 4, "Conformal guards must refuse nonuniform/shear/mirror/perspective")
    q = error_summary([(0.,0.,0.),(.00006,0.,0.)],[(0.,0.,0.),(0.,0.,0.)],1.)
    need(q["maximum_m"] > GEOMETRY_GUARD_M and q["worst_native_index"] == 1, "60um reproduction error must fail50um")
    need(error_summary([(.004,0.,0.)],[(0.,0.,0.)],.01)["maximum_m"] == .00004, "Physical metres conversion")
    args = ("Input", "Main", {"Hips","Waist"}, {"Hem"}, {"MCH"}, {"Wire"}, "Body")
    need(allowed_edge("upstream","Main","Hips",*args) and allowed_edge("manual_def","Input","MCH",*args), "Expected native dependency controls")
    for role,target,bone in (("upstream","Main","DEF"),("manual_def","Main","DEF"),("skin","C",""),("spline","Tracker",""),("unknown","Input","")):
        need(not allowed_edge(role,target,bone,*args), "Forbidden/unknown input dependency must fail")
    raw={"rotation_mode":"QUATERNION","location":[0.,2.3841730012463813e-7,0.],"rotation_euler":[0.,0.,0.],
         "rotation_quaternion":[1.,0.,0.,0.],"rotation_axis_angle":[0.,0.,1.,0.],
         "scale":[1.000000238418579,.9999940991401672,1.0000004768371582]}
    basis=[row[:] for row in identity]
    for i in range(3): basis[i][i]=raw["scale"][i]
    for connected in (False,True):
        b=[row[:] for row in basis]
        if not connected:b[1][3]=raw["location"][1]
        native_trs_copy_proof(raw,raw,raw,b,b,connected,connected,"actual nonuniform raw/connected control")
    signed={k:(v[:] if isinstance(v,list) else v) for k,v in raw.items()}; signed["scale"]=[-1.,0.,2.]
    signed_basis=[row[:] for row in identity]
    for i in range(3):signed_basis[i][i]=signed["scale"][i]
    native_trs_copy_proof(signed,signed,signed,signed_basis,signed_basis,False,False,"finite signed native scale")
    failures=0
    for kind in ("channel_change","nan_channel","shear_residual","nan_basis","connected_policy","connected_translation"):
        e={k:(v[:] if isinstance(v,list) else v) for k,v in raw.items()}; c={k:(v[:] if isinstance(v,list) else v) for k,v in raw.items()}
        a,b=[row[:] for row in basis],[row[:] for row in basis]; ca=cb=False
        if kind=="channel_change":c["rotation_euler"][0]=.01
        elif kind=="nan_channel":e["scale"][0]=math.nan
        elif kind=="shear_residual":a[0][1]=.01
        elif kind=="nan_basis":b[0][0]=math.nan
        elif kind=="connected_policy":cb=True
        else:ca=cb=True; a[1][3]=b[1][3]=1.e-6
        try:native_trs_copy_proof(e,raw,c,a,b,ca,cb,kind)
        except RuntimeError:failures+=1
    need(failures==6,"Raw TRS copy/residual negative controls must reject")
    return {"passed": True, "legacy_focused_controls": 13,"new_raw_trs_controls":9,"native_run": False, "accepted": False}


def inventory(bpy):
    return {name: sorted((x.name, x.as_pointer()) for x in getattr(bpy.data, name)) for name in
            ("objects","meshes","armatures","curves","shape_keys","actions","collections","node_groups")}


def key_values(obj, graph=None):
    keys = obj.data.shape_keys
    if keys is None: return None
    evaluated = keys.evaluated_get(graph) if graph is not None else keys
    return {"use_relative": bool(keys.use_relative), "eval_time": float(evaluated.eval_time),
            "blocks": [{"name": k.name, "value": float(k.value), "mute": bool(k.mute)} for k in evaluated.key_blocks]}


def channels(pb):
    return {name: getattr(pb,name) if name == "rotation_mode" else list(getattr(pb,name)) for name in CHANNELS}


def replay(pb, values):
    for name in CHANNELS: setattr(pb,name,values[name])


def clear_metadata(owner):
    for key in list(owner.keys()): del owner[key]


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path)
    p.add_argument("--max-seconds",type=float,default=120.)
    p.add_argument("--pure-checks",action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    if not args.pure_checks:
        need(args.output is not None and args.output.is_absolute() and not args.output.exists()
             and args.output.resolve().is_relative_to(HERE) and args.output.resolve() != HERE,"Fresh absolute Validation output only")
        need(0. < args.max_seconds <= 120.,"Soft bound<=120s; root enforces external180s lease")
    return args


def main(args):
    if args.pure_checks: print(json.dumps(pure_checks())); return 0
    import bpy
    from mathutils import Matrix, Quaternion
    need(bpy.app.background and bpy.app.version[:2] == (5,1) and not bpy.data.filepath
         and "--factory-startup" in sys.argv and "--disable-autoexec" in sys.argv
         and "--threads" in sys.argv and sys.argv[sys.argv.index("--threads")+1] == "1","Root-leased empty factory Blender5.1 only")
    need(all(sha(path) == expected for path,expected in PINS.items()),"Exact input/artist/frozen dependency changed")
    workflow,same,read = (load(name) for name in ("verify_actual_surface_workflow.py","verify_actual_same_frame_pose.py","verify_actual_body_proxy_coverage.py"))
    qa,diag,addon,surface = workflow.load_dependencies()
    args.input,args.install_report = INPUT.resolve(),INSTALL.resolve()
    args.expected_surface_sha,args.expected_worker_sha = PINS[SURFACE],PINS[WORKER]
    args.body_vertex_limit = 100000
    report = {"stage":"INPUT800_REPRODUCTION","native_completed":False,"accepted":False,"artist_saved":False,
              "scope":"Owned native input-only evaluation, no Cloth steps/bake/time travel. Original is raw-channel snapshot replay; Keys retained but not deliberately exercised.",
              "script_sha256":sha(Path(__file__)),"pins":{str(k):v for k,v in PINS.items()},"pure_checks":pure_checks(),
              "source_before":diag.source_manifest(),"files_before":{str(p):qa.file_state(p) for p in (INPUT,INSTALL,ARTIST)},"checks":[],"samples":{}}
    args.output.mkdir(); destination = args.output / "input800_reproduction.json"; endpoint_path = args.output / "native_input800_endpoints.json"
    owned = {name:[] for name in ("objects","meshes","armatures","curves","shape_keys")}; home=protection=baseline=None
    source=rig=cloth=None; disabled=[]; started=time.perf_counter(); endpoint_data={}; source_name=None
    def write(): destination.write_text(json.dumps(diag.json_content(report),indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    def budget(): need(time.perf_counter()-started < args.max_seconds,"Input reproduction soft phase budget exhausted")
    def remember(kind,item):
        owned[kind].append((item.as_pointer(),item.name) if kind=="shape_keys" else item)
        return item
    def copy_object(original,label,data=True):
        obj=remember("objects",original.copy()); obj.name=label
        if data:
            kind={"MESH":"meshes","CURVE":"curves","ARMATURE":"armatures"}[original.type]
            obj.data=remember(kind,original.data.copy())
            if original.type=="MESH" and obj.data.shape_keys is not None:
                need(obj.data.shape_keys != original.data.shape_keys,"Independent Key copy unexpectedly shared")
                remember("shape_keys",obj.data.shape_keys)
        for owner in (obj,obj.data):
            if data or owner is obj:
                owner.animation_data_clear(); clear_metadata(owner); owner.use_fake_user=False
        if data and original.type=="MESH" and obj.data.shape_keys:
            obj.data.shape_keys.animation_data_clear(); clear_metadata(obj.data.shape_keys); obj.data.shape_keys.use_fake_user=False
        obj.hide_viewport=obj.hide_render=False; obj.hide_select=True
        return obj
    def link(obj): home.collection.objects.link(obj); obj.hide_set(False)
    def set_keys(obj,values):
        if values is None: need(obj.data.shape_keys is None,"Unexpected copied Keys"); return
        keys=obj.data.shape_keys; need(keys is not None and [k.name for k in keys.key_blocks] == [k["name"] for k in values["blocks"]],"Exact Key block identity changed")
        need(bool(keys.use_relative)==values["use_relative"],"Relative/absolute Key policy changed")
        keys.eval_time=values["eval_time"]
        for key,row in zip(keys.key_blocks,values["blocks"]): key.value,key.mute=row["value"],row["mute"]
    try:
        source_name=workflow.motion_input_gate(args,report,qa,diag); addon.register()
        need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(INPUT),load_ui=False,use_scripts=False),"Exact input open failed")
        source,rig,record=qa.owned_source(source_name); home=bpy.context.scene; protection=qa.Protection(); baseline=inventory(bpy)
        report["author_pose"]=qa.digest(same.pose_checkpoint(rig,qa)); report["author_playback"]=qa.digest(same.playback_state(qa)); report["author_frame"]=[home.frame_current,home.frame_subframe]
        report["saved_cache_preflight"]=qa.saved_cache_preflight(source,record); need(report["saved_cache_preflight"]["allowed"],"Sealed/external/disk/baking cache refused")
        actual=bpy.data.objects[record["physics"]["proxy"]]; cloth=next(m for m in actual.modifiers if m.type=="CLOTH")
        surface.validate(source,rig,record); report["canonical_validation_before_private_ids"]=True
        all_cloths=[m for o in home.objects for m in o.modifiers if m.type=="CLOTH"]
        need(all_cloths==[cloth],"Unknown additional Cloth in input; not disabled or reset")
        report["cache_before"]=same.cache_state(cloth,qa)
        disabled.append((cloth,cloth.show_viewport,cloth.show_render)); cloth.show_viewport=cloth.show_render=False
        home.tool_settings.use_keyframe_insert_auto=False
        report["animation_backup"]=qa.backup_animation(home,[rig],protection.action_refs)
        original_keys=key_values(source); report["source_raw_keys_initial"]=original_keys
        qa.skirt._activate(bpy.context,rig,"POSE"); qa.public_switch(bpy.ops.character_designer.body_ik_fk_switch,mode="FK")
        legs,axes,height=qa.body_inputs(rig,record)
        qa.tuning.apply(bpy.context,(source,),mode="MANUAL")
        holder,_identifier,_path=qa.skirt.physics_control(source)
        need(float(holder["physics_influence"])==0.,"Public Manual did not set physics influence0")
        record=qa.skirt.read_record(source); body,report["registered_body"]=qa.registered_body(bpy.context,rig,args)
        need(body is not None and report["registered_body"]["measured"] and body.name==record["physics"]["surface"]["body"],"Registered actual Body absent")
        source_armature=source.modifiers[0]
        need(source_armature.type=="ARMATURE" and source_armature.object==rig and source_armature.show_viewport and source_armature.show_render,"Exact first native skin modifier required")
        need([m.type for m in source.modifiers]==["ARMATURE","NODES","SUBSURF"] and source.parent==rig and source.parent_type=="OBJECT" and not source.constraints,"Unsupported source modifier/parent input; no guessed prefix")
        metres=float(home.unit_settings.scale_length); guard=qa.geometry_guard(metres)
        need(math.isfinite(metres) and metres>0. and guard==GEOMETRY_GUARD_M,"Exact physical50um reproduction guard required")
        report["units_to_metres"],report["geometry_guard_m"]=metres,guard
        raw_contract=qa.raw_mesh_content(source); report["source_raw_contract"]=raw_contract
        oracle=copy_object(source,"QA Manual800 Oracle")
        for m in list(oracle.modifiers)[1:]: oracle.modifiers.remove(m)
        link(oracle)
        snapshots={}; saved_basis=rig.matrix_basis.copy(); saved_mode=rig.rotation_mode
        upstream=surface._ancestors(rig,record); waist=record["controls"]["waist"]
        controls={record["controls"][k] for k in ("waist","mid","hem")}
        controls.update(name for entry in record["controls"]["chains"] for name in entry.values())
        manual={n for chain in record["chains"] for n in chain["manual"]}; deform={n for chain in record["chains"] for n in chain["def"]}
        forbidden={n for chain in record["chains"] for n in chain["phys"]}|deform
        keep=set(upstream)|controls|manual|deform
        need(len(record["chains"])==len(record["controls"]["chains"])==8 and keep<=set(rig.data.bones.keys()) and not(set(upstream)&forbidden),"Exact8-wire upstream/input subset unresolved")
        def capture(label):
            budget(); need([home.frame_current,home.frame_subframe]==report["author_frame"],"Author frame/subframe changed")
            bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get(); values=key_values(source,graph)
            need(key_values(source)==original_keys,"Author raw Key values changed; not frozen by rewriting")
            set_keys(oracle,values); bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get()
            posed=rig.evaluated_get(graph)
            snap={"label":label,"author_frame":list(report["author_frame"]),"key_values":values,
                  "rig_channels":qa.pose_channels(rig),"input_channels":{n:channels(rig.pose.bones[n]) for n in keep},
                  "rig_world":diag.matrix(posed.matrix_world),"source_frame":surface._frame(source),
                  "upstream_world":{n:diag.matrix(posed.matrix_world@posed.pose.bones[n].matrix) for n in upstream+[waist]},
                  "native_original_raw_channels":{n:channels(rig.pose.bones[n]) for n in deform},
                  "source_manual_constraint_modes":{n:rig.pose.bones[n].constraints["Skirt manual pose"].mix_mode for n in deform},
                  "native_main_manual_matrices":{n:diag.matrix(posed.pose.bones[n].matrix) for n in manual|deform}}
            meshes={"ManualOracle800":read.native_mesh(oracle,graph,diag),"RegisteredBody":read.native_mesh(body,graph,diag)}
            for name in record["physics"]["colliders"]: meshes[name]=read.native_mesh(bpy.data.objects[name],graph,diag)
            need(len(meshes["ManualOracle800"]["points"])==800,"Oracle is not preSubdivision800")
            snap["native_meshes"]=meshes; snapshots[label]=snap
            endpoint_data[label]={"sample":snap,"scope":"Native captured public Manual influence0; no evaluated C result is used as input","accepted":False}
            endpoint_path.write_text(json.dumps(diag.json_content({"stage":"INPUT800_REPRODUCTION","units_to_metres":metres,"endpoints":endpoint_data,"accepted":False}),indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
            return snap
        n=capture("N"); posed=rig.evaluated_get(bpy.context.evaluated_depsgraph_get()); knee_n=posed.matrix_world@posed.pose.bones[legs["L"]["chain"][1]].head
        thigh=rig.pose.bones[legs["L"]["chain"][0]]
        need(not any(thigh.lock_rotation) and not(thigh.lock_rotations_4d and thigh.lock_rotation_w),"Native thigh rotation locked")
        rotation=thigh.matrix_basis.to_quaternion().copy(); thigh.rotation_mode="QUATERNION"; thigh.rotation_quaternion=rotation@Quaternion(axes[thigh.name],.55)
        rig.update_tag(refresh={"OBJECT"}); l=capture("L")
        handle=rig.pose.bones[record["controls"]["hem"]]; same.unoccupied_handle(rig,handle)
        posed=rig.evaluated_get(bpy.context.evaluated_depsgraph_get()); hem_n=posed.matrix_world@posed.pose.bones[handle.name].matrix.translation
        direction=rig.matrix_world.to_3x3().col[0].normalized(); step=float(record["fit"]["height_world"])*.04
        candidates=[(side,(posed.matrix_world@posed.pose.bones[e["chain"][1]].head-hem_n).dot(direction)) for side,e in legs.items()]
        candidates=[item for item in candidates if item[1]<0.]; need(candidates and step>0.,"No actual reverse-knee input; no guessed direction")
        side,projection=min(candidates,key=lambda x:abs(x[1])); offset=max(2.*step,abs(projection)+step)
        target=handle.matrix.copy(); target.translation-=rig.matrix_world.to_3x3().inverted()@(direction*offset)
        local=rig.convert_space(pose_bone=handle,matrix=target,from_space="POSE",to_space="LOCAL")
        need(not any(locked and abs(local.translation[i]-handle.matrix_basis.translation[i])>1.e-10 for i,locked in enumerate(handle.lock_location)),"Hem native lock would be bypassed")
        handle.matrix_basis=local; rig.update_tag(refresh={"OBJECT"}); t=capture("T")
        posed=rig.evaluated_get(bpy.context.evaluated_depsgraph_get()); knee_t=posed.matrix_world@posed.pose.bones[legs["L"]["chain"][1]].head; hem_t=posed.matrix_world@posed.pose.bones[handle.name].matrix.translation
        report["actual_inputs"]={"thigh":thigh.name,"angle_rad":.55,"knee_delta_m":(knee_t-knee_n).length*metres,
            "hem":handle.name,"reverse_target_side":side,"reverse_offset_world":offset,"hem_L_T_delta_m":(hem_t-hem_n).length*metres,
            "Body_N_L":error_summary(l["native_meshes"]["RegisteredBody"]["points"],n["native_meshes"]["RegisteredBody"]["points"],metres),
            "Body_L_T":error_summary(t["native_meshes"]["RegisteredBody"]["points"],l["native_meshes"]["RegisteredBody"]["points"],metres),
            "Manual800_L_T":error_summary(t["native_meshes"]["ManualOracle800"]["points"],l["native_meshes"]["ManualOracle800"]["points"],metres)}
        write(); need(report["actual_inputs"]["knee_delta_m"]>height*.01*metres and report["actual_inputs"]["Body_N_L"]["maximum_m"]>guard
                      and min(report["actual_inputs"]["hem_L_T_delta_m"],report["actual_inputs"]["Manual800_L_T"]["maximum_m"])>guard,"Actual leg or independent Manual input swallowed")
        need(report["actual_inputs"]["Body_L_T"]["maximum_m"]<=guard and l["upstream_world"]==t["upstream_world"],"Manual changed Body/upstream input")
        need(all(snap["key_values"]==n["key_values"] for snap in snapshots.values()),"Evaluated Keys changed with pose; current fixed-Key fixture unsupported")
        for snap in snapshots.values():
            for role in n["native_meshes"]:
                need(all(snap["native_meshes"][role][key]==n["native_meshes"][role][key] for key in ("native_vertex_index_order","edges","faces","weights","native_group_mapping")),"Native cross-Pose source index/topology/group identity changed: "+role)
        report["native_endpoint_index_identity_exact"]=True
        # Build only after complete actual N/L/T evidence has been persisted.
        budget(); input_rig=copy_object(rig,"QA Dress Input Rig")
        input_rig.parent=None; input_rig.matrix_parent_inverse=Matrix.Identity(4); input_rig.matrix_basis=rig.matrix_world.copy()
        surface._clear(input_rig.constraints); input_rig.data.pose_position="POSE"
        for pb in input_rig.pose.bones:
            surface._clear(pb.constraints); pb.custom_shape=None; clear_metadata(pb); clear_metadata(input_rig.data.bones[pb.name])
        link(input_rig); input_rig.hide_select=False; qa.skirt._activate(bpy.context,input_rig,"EDIT")
        for bone in list(input_rig.data.edit_bones):
            if bone.name not in keep: input_rig.data.edit_bones.remove(bone)
        bpy.ops.object.mode_set(mode="OBJECT"); input_rig.hide_select=True
        need(set(input_rig.data.bones.keys())==keep and surface._rest(input_rig,keep)==surface._rest(rig,keep),"Input subset Rest/parent data changed")
        parent_map=lambda owner:{name:None if owner.data.bones[name].parent is None else owner.data.bones[name].parent.name for name in keep}
        need(parent_map(input_rig)==parent_map(rig),"Input retained bone parents differ")
        report["input_rig_native_parent_map"]=parent_map(input_rig)
        surface._world_follow(input_rig,rig,name="QA upstream rig world")
        for name in upstream+[waist]: surface._world_follow(input_rig.pose.bones[name],rig,name,"QA upstream bone")
        wires=[]
        for i,chain in enumerate(record["chains"]):
            original=surface._generated_wire(source,rig,record,i); wire=copy_object(original,"QA Dress Input Wire %02d"%(i+1))
            wire.parent=input_rig; wire.parent_type,wire.parent_bone=original.parent_type,original.parent_bone
            wire.matrix_parent_inverse,wire.matrix_basis=original.matrix_parent_inverse.copy(),original.matrix_basis.copy()
            for modifier in wire.modifiers:
                need(modifier.type=="HOOK" and modifier.object==rig and modifier.subtarget in controls,"Unexpected original native Hook input")
                inverse,center=modifier.matrix_inverse.copy(),modifier.center.copy()
                modifier.object=input_rig  # Native object setter resets Hook bind/offset.
                modifier.matrix_inverse,modifier.center=inverse,center
                need(modifier.matrix_inverse==inverse and modifier.center==center,"Hook retarget did not preserve native bind/center")
            link(wire); wires.append(wire)
            old_spline=rig.pose.bones[chain["manual"][-1]].constraints["Skirt manual wire"]
            spline=input_rig.pose.bones[chain["manual"][-1]].constraints.new("SPLINE_IK"); surface._copy_scalars(old_spline,spline); spline.target=wire
            for name,mch in zip(chain["def"],chain["manual"]):
                old_copy=rig.pose.bones[name].constraints["Skirt manual pose"]
                need(not old_copy.mute and old_copy.influence==1. and old_copy.mix_mode in {"REPLACE","BEFORE_FULL"},"Unsupported Original manual constraint")
                new=input_rig.pose.bones[name].constraints.new("COPY_TRANSFORMS"); surface._copy_scalars(old_copy,new); new.target,new.subtarget=input_rig,mch
        before=copy_object(source,"QA Input800 Before Body")
        for m in list(before.modifiers)[1:]: before.modifiers.remove(m)
        before.parent=input_rig; before.modifiers[0].object=input_rig; link(before)
        clone=bpy.data.objects[record["physics"]["colliders"][-1]]
        original_group_count=len(source.vertex_groups)
        def audit(mesh_objects,body_attachment=None):
            rows=[]; wire_names={w.name for w in wires}; input_name=input_rig.name; main_name=rig.name
            def edge(role,target,subtarget=""):
                name=None if target is None else target.name
                need(allowed_edge(role,name,subtarget,input_name,main_name,set(upstream+[waist]),controls,manual,wire_names,clone.name),"Forbidden/unknown native dependency: "+str((role,name,subtarget)))
                rows.append({"role":role,"target":name,"subtarget":subtarget,"target_pointer":target.as_pointer()})
            need(input_rig.parent is None and len(input_rig.constraints)==1,"Input object has extra relationship")
            edge("object_world",input_rig.constraints[0].target,input_rig.constraints[0].subtarget)
            for pb in input_rig.pose.bones:
                if pb.name in upstream+[waist]:
                    need(len(pb.constraints)==1 and pb.constraints[0].type=="COPY_TRANSFORMS","Extra upstream constraint"); edge("upstream",pb.constraints[0].target,pb.constraints[0].subtarget)
                elif pb.name in deform:
                    need(len(pb.constraints)==1 and pb.constraints[0].type=="COPY_TRANSFORMS","Extra input DEF constraint"); edge("manual_def",pb.constraints[0].target,pb.constraints[0].subtarget)
                elif pb.constraints:
                    need(pb.name in {c["manual"][-1] for c in record["chains"]} and len(pb.constraints)==1 and pb.constraints[0].type=="SPLINE_IK","Unknown manual mechanism constraint"); edge("spline",pb.constraints[0].target)
            for w in wires:
                need(w.parent_type in {"OBJECT","BONE"},"Unknown wire parent input")
                edge("wire_parent",w.parent,w.parent_bone if w.parent_type=="BONE" else "")
                for mod in w.modifiers: need(mod.type=="HOOK","Non-Hook wire input"); edge("hook",mod.object,mod.subtarget)
            for mesh in mesh_objects:
                edge("mesh_parent",mesh.parent); edge("skin",mesh.modifiers[0].object)
                need(mesh.modifiers[0].type=="ARMATURE" and all(m.type!="CLOTH" for m in mesh.modifiers),"Active/new Cloth unexpectedly present")
            if body_attachment is not None: edge("body_attachment",body_attachment.target)
            for obj in [input_rig,*wires,*mesh_objects]:
                for owner in (obj,obj.data,getattr(obj.data,"shape_keys",None)):
                    need(owner is None or owner.animation_data is None,"Owned input acquired Action/NLA/driver dependency")
            for name in upstream+[waist]:
                for constraint in rig.pose.bones[name].constraints:
                    need(getattr(constraint,"subtarget","") not in forbidden and getattr(constraint,"pole_subtarget","") not in forbidden,"Body/waist upstream reads mainDEF/PHYS")
                    banned_objects={actual,bpy.data.objects[record["physics"]["surface"]["tracker"]],source}
                    need(getattr(constraint,"target",None) not in banned_objects and getattr(constraint,"pole_target",None) not in banned_objects,"Body/waist upstream reads a downstream geometry target")
            need(not(set(input_rig.data.bones.keys())&{n for c in record["chains"] for n in c["phys"]}),"PHYS bone leaked into input subset")
            return {"native_edges":rows,"drivers_actions_nla_absent":True,"PHYS_Tracker_C_mainDEF_solver_dependencies_absent":True}
        def apply_input(snap):
            budget(); qa.restore_channels(rig,snap["rig_channels"],saved_basis,saved_mode)
            for name,values in snap["input_channels"].items(): replay(input_rig.pose.bones[name],values)
            set_keys(before,snap["key_values"]); input_rig.update_tag(refresh={"OBJECT"}); bpy.context.view_layer.update()
            graph=bpy.context.evaluated_depsgraph_get()
            proof={"input_object":conformal(input_rig.evaluated_get(graph).matrix_world,"input world"),"source_object":conformal(source.evaluated_get(graph).matrix_world,"source world")}
            posed=rig.evaluated_get(graph)
            for name in upstream+[waist]: proof[name]=conformal(posed.matrix_world@posed.pose.bones[name].matrix,"upstream "+name)
            # Raw basis is recomposed by Blender from exact copied channels.
            # Legitimate axis scales are retained; constrained/native Spline
            # matrices are neither decomposed nor substituted for raw basis.
            proof["raw_native_trs"]={name:native_trs_copy_proof(snap["input_channels"][name],channels(rig.pose.bones[name]),channels(input_rig.pose.bones[name]),
                rig.pose.bones[name].matrix_basis,input_rig.pose.bones[name].matrix_basis,
                bool(rig.data.bones[name].use_connect),bool(input_rig.data.bones[name].use_connect),"raw authored channel "+name) for name in controls|deform}
            return graph,proof
        # Persist the actual Rig reproduction even if separate bind-copy fails.
        report["input_rig_rest"]=surface._rest(input_rig,keep)
        for label,snap in snapshots.items():
            graph,proof=apply_input(snap); refs=audit((before,)); mesh=read.native_mesh(before,graph,diag); expected=snap["native_meshes"]["ManualOracle800"]
            need(mesh["weights_complete"] and mesh["native_vertex_index_order"]==list(range(800)) and all(mesh[k]==expected[k] for k in ("edges","faces","weights","native_group_mapping")),"Native preattachment topology/groups/weights changed")
            need(qa.raw_mesh_content(before)==raw_contract,"Private input raw mesh/Keys/groups/UV changed")
            err=error_summary(mesh["points"],expected["points"],metres); private_pose=input_rig.evaluated_get(graph)
            report["samples"][label]={"reproduction_before_attachment":err,"transform_proof":proof,"reference_audit":refs,"raw_data_exact":True,"key_values":key_values(before),
                "private_manual_pose_matrices":{name:diag.matrix(private_pose.pose.bones[name].matrix) for name in manual|deform}}
            endpoint_data[label]["private_native_inputs"]={"Input800BeforeBody":mesh}; endpoint_data[label]["comparison"]=report["samples"][label]
            endpoint_path.write_text(json.dumps(diag.json_content({"stage":"INPUT800_REPRODUCTION","units_to_metres":metres,"endpoints":endpoint_data,"accepted":False}),indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8"); write()
            need(err["maximum_m"]<=guard,"Native manual input reproduction exceeds unchanged50um guard: "+label)
        report["before_attachment_reproduction_complete"]=True; write()
        # Native copied bound SurfaceDeform; strict raw/chart equality, no implicit rebinding.
        report["copied_attachment_chart"]={"source":surface._frame(source),"actual_C":surface._frame(actual),
            "exact_native_frame_match":surface._frame(source)==surface._frame(actual)}; write()
        need(report["copied_attachment_chart"]["exact_native_frame_match"],"C/source local parent charts differ; copying a bind would guess its space")
        basis=surface._basis(source)
        need([list(v.co) for v in actual.data.vertices]==basis,"Copied attachment Basis differs from author reference")
        after=remember("objects",actual.copy()); after.name="QA Input800 After Body"
        after.data=remember("meshes",source.data.copy())
        if after.data.shape_keys is not None:
            need(after.data.shape_keys!=source.data.shape_keys,"After attachment Key copy shared"); remember("shape_keys",after.data.shape_keys); after.data.shape_keys.animation_data_clear(); clear_metadata(after.data.shape_keys); after.data.shape_keys.use_fake_user=False
        for owner in (after,after.data): owner.animation_data_clear(); clear_metadata(owner); owner.use_fake_user=False
        for m in list(after.modifiers):
            if m.type=="CLOTH": after.modifiers.remove(m)
        need([m.type for m in after.modifiers]==["ARMATURE","SURFACE_DEFORM"],"Copied attachment modifier structure changed")
        surface._copy_scalars(source_armature,after.modifiers[0]); after.modifiers[0].object=input_rig; after.parent=input_rig
        after.show_only_shape_key,after.active_shape_key_index=source.show_only_shape_key,source.active_shape_key_index
        attachment=after.modifiers[1]; mask_name=attachment.vertex_group; ring=list(record["fit"]["rings"][0])
        need(mask_name not in after.vertex_groups and mask_name not in input_rig.data.bones and len(ring)==len(set(ring))==80,"Native raw80 mask/index collision")
        after.vertex_groups.new(name=mask_name).add(ring,1.,"REPLACE")
        need(attachment.is_bound and attachment.target==clone and attachment.use_sparse_bind and not attachment.invert_vertex_group and attachment.strength==1.,"STRUCTURE_BLOCKER: native bound SurfaceDeform copy unavailable")
        after.hide_viewport=after.hide_render=False; after.hide_select=True; link(after)
        report["input_rig_rest"]=surface._rest(input_rig,keep); report["raw80_attachment"]={"ring0_ids":ring,"mask_name":mask_name,"native_is_bound":attachment.is_bound,"target":clone.name,"copied_rna":surface._rna(attachment),"scope":"After-input layer only; reused native bind requires identical Basis/local chart. No final collision/waist result is inferred."}
        for label,snap in snapshots.items():
            graph,transform_proof=apply_input(snap); set_keys(after,snap["key_values"])
            input_rig.update_tag(refresh={"OBJECT"}); bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get()
            refs=audit((before,after),attachment); meshes={"Input800BeforeBody":read.native_mesh(before,graph,diag),"Input800AfterBody":read.native_mesh(after,graph,diag)}
            expected=snap["native_meshes"]["ManualOracle800"]
            need(all(len(m["points"])==800 and m["native_vertex_index_order"]==list(range(800)) for m in meshes.values()),"Input count/order changed")
            raw_before=qa.raw_mesh_content(before); raw_after=qa.raw_mesh_content(after)
            need(raw_before==raw_contract,"Private input raw mesh/Keys/groups/UV changed")
            raw_after["groups"]=raw_after["groups"][:original_group_count]
            raw_after["weights"]=[[w for w in row if w[0]<original_group_count] for row in raw_after["weights"]]
            need(raw_after==raw_contract,"After attachment changed original raw mesh/Keys/groups/UV")
            first_read=endpoint_data[label]["private_native_inputs"]["Input800BeforeBody"]
            need(meshes["Input800BeforeBody"]["points"]==first_read["points"] and meshes["Input800BeforeBody"]["triangles"]==first_read["triangles"],"Identical native input repeat changed coordinates/triangulation")
            err=error_summary(meshes["Input800BeforeBody"]["points"],expected["points"],metres)
            outside=[i for i in range(800) if i not in set(ring)]
            effect={"raw80":error_summary(meshes["Input800AfterBody"]["points"],meshes["Input800BeforeBody"]["points"],metres,ring),"outside720":error_summary(meshes["Input800AfterBody"]["points"],meshes["Input800BeforeBody"]["points"],metres,outside)}
            private_pose=input_rig.evaluated_get(graph)
            report["samples"][label]={"reproduction_before_attachment":err,"attachment_effect":effect,"transform_proof":transform_proof,"reference_audit":refs,"raw_data_exact":True,"key_values":key_values(before),
                "private_manual_pose_matrices":{name:diag.matrix(private_pose.pose.bones[name].matrix) for name in manual|deform},
                "native_timing_scope":"graph update plus native mesh reads, not GUI FPS"}
            endpoint_data[label]["private_native_inputs"]=meshes; endpoint_data[label]["comparison"]=report["samples"][label]
            endpoint_path.write_text(json.dumps(diag.json_content({"stage":"INPUT800_REPRODUCTION","units_to_metres":metres,"endpoints":endpoint_data,"accepted":False}),indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8"); write()
            need(err["maximum_m"]<=guard,"Native manual input reproduction exceeds unchanged50um guard: "+label)
            need(effect["outside720"]["maximum_m"]<=guard,"Body attachment affects vertices outside explicit raw80 mask")
        report["Keys_exercise"]={"original_data_and_current_values_preserved":True,"deliberately_exercised":False,"limitation":"No Key-value sweep or animated Key/Original live-dependency validation in this first gate."}
        report["native_completed"]=True
    except Exception as error:
        report["exception"]={"type":type(error).__name__,"message":str(error),"traceback":traceback.format_exc()}
    finally:
        cleanup_errors=[]
        try:
            if home is not None:
                if bpy.context.object is not None and bpy.context.object.mode!="OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
                for obj in list(owned["objects"]):
                    if obj.type=="MESH" and obj.data.shape_keys is not None:
                        keys=obj.data.shape_keys; name,pointer=keys.name,keys.as_pointer(); data=obj.data
                        need(pointer in {p for p,_name in owned["shape_keys"]} and data.users==1 and bpy.data.user_map(subset={keys}).get(keys,set())=={data},"Owned Key acquired foreign/shared user")
                        obj.shape_key_clear(); remaining=bpy.data.shape_keys.get(name)
                        if remaining is not None:
                            need(remaining.as_pointer()==pointer and not bpy.data.user_map(subset={remaining}).get(remaining,set()),"Owned detached Key acquired foreign user")
                            bpy.data.batch_remove(ids=(remaining,))
                for obj in reversed(owned["objects"]): bpy.data.objects.remove(obj,do_unlink=True)
                for kind in ("meshes","curves","armatures"):
                    for item in reversed(owned[kind]): need(item.users==0,"Owned data acquired external user"); bpy.data.batch_remove(ids=(item,))
                report["owned_cleanup_exact"]=inventory(bpy)==baseline; need(report["owned_cleanup_exact"],"Original/native ID inventory differs after owned cleanup")
                report["protection_before_reload"]=protection.verify(); need(report["protection_before_reload"]["success"],"Raw source/Keys/groups/Rest/Actions/NLA protection failed")
                report["cache_after"]=same.cache_state(cloth,qa); report["cache_metadata_exact"]=report["cache_after"]==report["cache_before"]
                need(report["cache_metadata_exact"],"Original cache metadata changed despite no Cloth steps/reset/bake")
        except Exception as error: cleanup_errors.append({"phase":"owned_cleanup","message":str(error),"traceback":traceback.format_exc()})
        try:
            need("FINISHED" in bpy.ops.wm.open_mainfile(filepath=str(INPUT),load_ui=False,use_scripts=False),"Finally exact input reopen failed")
            reloaded_source,reloaded_rig,_=qa.owned_source(source_name)
            report["protection_after_reload"]=protection.verify() if protection else {"success":False}
            report["pose_after_reload_exact"]=qa.digest(same.pose_checkpoint(reloaded_rig,qa))==report.get("author_pose")
            report["playback_after_reload_exact"]=qa.digest(same.playback_state(qa))==report.get("author_playback")
            report["author_frame_after_reload_exact"]=[bpy.context.scene.frame_current,bpy.context.scene.frame_subframe]==report.get("author_frame")
            need(report["protection_after_reload"]["success"] and report["pose_after_reload_exact"] and report["playback_after_reload_exact"] and report["author_frame_after_reload_exact"],"Exact reload author protection failed")
            surface.validate(reloaded_source,reloaded_rig,qa.skirt.read_record(reloaded_source)); report["canonical_validation_after_reload"]=True
        except Exception as error: cleanup_errors.append({"phase":"exact_reload","message":str(error),"traceback":traceback.format_exc()})
        report["cleanup_errors"]=cleanup_errors; report["files_after"]={str(p):qa.file_state(p) for p in (INPUT,INSTALL,ARTIST)}
        report["source_after"]=diag.source_manifest(); report["source_disk_exact"]=report["source_before"]==report["source_after"]
        report["input_artist_disk_exact"]=report["files_before"]==report["files_after"]
        report["script_disk_exact"]=sha(Path(__file__))==report["script_sha256"]
        report["native_endpoint_file"]={"path":str(endpoint_path),"sha256":sha(endpoint_path) if endpoint_path.exists() else None}
        report["ready_for_next_private_gate"]=bool(report["native_completed"] and not cleanup_errors and report["source_disk_exact"] and report["input_artist_disk_exact"] and report["script_disk_exact"])
        report["elapsed_seconds"]=time.perf_counter()-started; write()
    print("INPUT800 report:",destination,"ready:",report["ready_for_next_private_gate"],flush=True)
    return 0 if report["ready_for_next_private_gate"] else 2


if __name__ == "__main__": raise SystemExit(main(arguments()))
