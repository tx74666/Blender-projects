"""PREPARED ONLY: INPUT800_REPRODUCTION, no new/evaluated Cloth or bake.

Root alone leases factory Blender 5.1/disable-autoexec/threads1. Exact 7ac is
read, never overwritten. N/L/T replay protected, sealed V2 actual main inputs;
Key values are not varied. Owned input-only Rig/wires/native skin reproduce the
manual-only pre-Subdivision oracle. Original raw channels are snapshot replay,
not a claim of live Original integration. Body attachment is a separate layer.
V3 preserves V2 raw TRS guards and restores mesh parent charts after retarget.
It streams selected actual main input fields from frozen V2 endpoints, never
uses its failed private mesh as an expected target, and checks fresh native
main oracle/Body geometry before independent input Rig reproduction.
V4 normalizes only native containers across sealed JSON comparisons with the
frozen diagnostic converter, preserving primitive values/order exactly.
V5 changes only upstream bone follows to POSE/POSE REPLACE under exact native
Rig world/Rest identity, and records actual pose/world differences. This is a
different native Float32 path, not a promise of fewer conversions or success.
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
SEALED_ROOT = HERE / "actual_input800_reproduction_v2_51_20261006_141642_284/result"
SEALED_REPORT = SEALED_ROOT / "input800_reproduction.json"
SEALED_ENDPOINT = SEALED_ROOT / "native_input800_endpoints.json"
PINS = {
    HERE / "prototype_input800_reproduction_v4.py": "0f53894d3791ae8935fa3dbb532bb34a32f35d6a408dc297996597931d9e6632",
    HERE / "prototype_input800_reproduction_v3.py": "2116224dcc19fa3f8ae505acc8ce1498ceb02a6dd6e7cae40d64bec94298aaa5",
    HERE / "prototype_input800_reproduction_v2.py": "07e24ef1f0b1829971ca2fc50e319af5aac219364063ed6ffbde1a976c5a7b1d",
    SEALED_REPORT: "8a344ffcc72de2ae7c0ac2bb1a64d3f0fde601f8225039ba7949986f754d56db",
    SEALED_ENDPOINT: "c85f511ce8dbeabb4c05b9b10003dee38111efafe30086fd9bb252193c598f20",
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


def sealed_input_samples(stream):
    """Read exact two-space V2 JSON, retaining only actual sample fields.

    The outer file is SHA pinned. Old private_native_inputs/comparison are
    excluded, and Body dense evaluated weights are not expanded in memory.
    Full original evidence remains in the immutable sealed endpoint file.
    """
    import re
    sample_fields={"label","author_frame","key_values","rig_channels","input_channels","rig_world","source_frame","upstream_world",
                   "native_original_raw_channels","source_manual_constraint_modes","native_main_manual_matrices"}
    body_fields={"points","native_vertex_index_order","native_vertex_face_edge_sha256","native_group_mapping","matrix_world","weights_complete"}
    rows={}; label=None; sample=False; body=False; iterator=iter(stream)
    def value(text,indent):
        stripped=text.strip().rstrip(",")
        if stripped not in {"{","["}:return json.loads(stripped)
        close="}" if stripped=="{" else "]"; lines=[stripped+"\n"]
        for line in iterator:
            lines.append(line)
            if len(line)-len(line.lstrip())==indent and line.strip() in {close,close+","}:
                return json.loads("".join(lines).strip().rstrip(","))
        raise RuntimeError("Truncated sealed JSON field")
    for line in iterator:
        indent=len(line)-len(line.lstrip()); match=re.match(r'^\s*"([^"\\]+)": (.*)$',line)
        if sample and indent==6 and line.strip() in {"}","},"}:sample=body=False; continue
        if body and indent==10 and line.strip() in {"}","},"}:body=False; continue
        if match is None:continue
        key,text=match.groups()
        if indent==4 and key in {"N","L","T"}:
            need(key not in rows,"Duplicate sealed input label"); label=key; rows[label]={"native_meshes":{}}; sample=body=False
        elif label is not None and indent==6 and key=="sample":sample=True
        elif sample and indent==8 and key in sample_fields:rows[label][key]=value(text,indent)
        elif sample and indent==10 and key=="ManualOracle800":rows[label]["native_meshes"][key]=value(text,indent)
        elif sample and indent==10 and key=="RegisteredBody":body=True; rows[label]["native_meshes"][key]={}
        elif sample and body and indent==12 and key in body_fields:rows[label]["native_meshes"]["RegisteredBody"][key]=value(text,indent)
    need(set(rows)=={"N","L","T"} and all(sample_fields<=set(row) and set(row["native_meshes"])=={"ManualOracle800","RegisteredBody"}
        and body_fields<=set(row["native_meshes"]["RegisteredBody"]) for row in rows.values()),"Sealed actual input schema incomplete")
    return rows


def native_world_copy_proof(actual,expected,label):
    matrices=[[[float(x) for x in row] for row in matrix] for matrix in (actual,expected)]
    need(all(len(matrix)==4 and all(len(row)==4 and all(math.isfinite(x) for x in row) for row in matrix) for matrix in matrices),label+": invalid native world matrix")
    residual=max(abs(matrices[0][i][j]-matrices[1][i][j]) for i in range(4) for j in range(4))
    need(residual<=RAW_NATIVE_BASIS_GUARD,label+": restored parent chart world differs")
    return {"maximum_native_world_component_residual":residual,"coefficient_guard":RAW_NATIVE_BASIS_GUARD,"geometry50um_gate_separate":True}


def pose_upstream_follow(surface, owner, target, bone):
    """Bone-only native same-Rig-space numerical comparison; no matrix write."""
    need(getattr(getattr(owner,"id_data",None),"type",None)=="ARMATURE" and hasattr(owner,"bone"),"POSE follow is bone-only")
    constraint=surface._world_follow(owner,target,bone,"QA upstream bone pose")
    constraint.owner_space=constraint.target_space="POSE"
    return constraint


def upstream_pose_diagnostic(main_world, input_world, main_pose, input_pose, metres):
    def rows(value):
        value=[[float(x) for x in row] for row in value]
        need(len(value)==4 and all(len(row)==4 and all(math.isfinite(x) for x in row) for row in value),"Invalid native upstream matrix")
        return value
    main_world,input_world=rows(main_world),rows(input_world)
    need(math.isfinite(metres) and metres>0.,"Invalid native physical unit")
    need(set(main_pose)==set(input_pose) and main_pose,"Missing same-space native upstream bone")
    proof={"native_main_rig_world":main_world,"native_input_rig_world":input_world,
           "rig_world_exact":main_world==input_world,
           "rig_world_max_component_delta":max(abs(main_world[i][j]-input_world[i][j]) for i in range(4) for j in range(4)),
           "upstream_pose":{},"policy":"POSE/POSE REPLACE requires exact current Rig world and retained Rest; matrices diagnostic only, no setter/decompose/offset"}
    # Keep pose differences diagnostic: unchanged actual80050um is the geometry gate.
    for name in main_pose:
        a,b=rows(main_pose[name]),rows(input_pose[name])
        multiply=lambda m,n:[[math.fsum(m[i][k]*n[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
        aw,bw=multiply(main_world,a),multiply(input_world,b)
        proof["upstream_pose"][name]={"native_main_pose":a,"native_input_pose":b,
            "maximum_pose_component_delta":max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4)),
            "maximum_pose_linear_component_delta":max(abs(a[i][j]-b[i][j]) for i in range(3) for j in range(3)),
            "pose_translation_norm_rig_units":math.sqrt(math.fsum((a[i][3]-b[i][3])**2 for i in range(3))),
            "pose_translation_world_delta_m":math.sqrt(math.fsum((aw[i][3]-bw[i][3])**2 for i in range(3)))*metres,
            "derived_world_arithmetic":"Python double from exact captured native matrices; not evaluated native world"}
    return proof


def primitive_equality_receipt(actual,expected,converter,limit=3):
    """Normalize declared native containers, without rounding/casting values."""
    converted=converter(actual); types=[]; differences=[]
    def visit(a,b,path,rows,container_types=False):
        if len(rows)>=limit:return
        if container_types and type(a) is not type(b):
            rows.append({"path":path,"native_type":type(a).__name__,"sealed_type":type(b).__name__}); return
        if isinstance(a,dict) and isinstance(b,dict):
            for key in sorted(set(a)|set(b)):
                if key not in a or key not in b:rows.append({"path":path+"["+json.dumps(key)+"]","actual_missing":key not in a,"sealed_missing":key not in b})
                else:visit(a[key],b[key],path+"["+json.dumps(key)+"]",rows,container_types)
                if len(rows)>=limit:return
        elif isinstance(a,(tuple,list)) and isinstance(b,(tuple,list)):
            if len(a)!=len(b):rows.append({"path":path,"actual_count":len(a),"sealed_count":len(b)}); return
            for index,(x,y) in enumerate(zip(a,b)):
                visit(x,y,path+"["+str(index)+"]",rows,container_types)
                if len(rows)>=limit:return
        elif a!=b:rows.append({"path":path,"actual":a,"sealed":b,"actual_type":type(a).__name__,"sealed_type":type(b).__name__})
    visit(actual,expected,"$",types,True)
    if converted!=expected:visit(converted,expected,"$",differences)
    return {"primitive_exact_equal":converted==expected,"native_type":type(actual).__name__,"sealed_type":type(expected).__name__,
            "native_container_differences":types,"first_primitive_differences":differences,"receipt_limit":limit,
            "policy":"Frozen diag.json_content; container normalization only, primitive numeric values/order unchanged; no tolerance"}


def real_abi_serialization_controls():
    """Execute the pinned real helper AST definitions with minimal RNA stubs."""
    import ast
    from types import SimpleNamespace as NS
    class Matrix(list):
        def __matmul__(self,v):return Vector(math.fsum(self[i][j]*v[j] for j in range(3))+self[i][3] for i in range(3))
    class Vector(tuple):pass
    class Euler(tuple):pass
    class Quaternion(tuple):pass
    namespace={"json":json,"math":math,"hashlib":hashlib,"Matrix":Matrix,"Vector":Vector,"Euler":Euler,"Quaternion":Quaternion}
    def definitions(path,names):
        need(sha(path)==PINS[path],"Real ABI control helper changed")
        tree=ast.parse(path.read_text(encoding="utf-8")); chosen=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
        need({node.name for node in chosen}==set(names),"Real ABI definitions missing")
        exec(compile(ast.Module(body=chosen,type_ignores=[]),str(path),"exec"),namespace)
    definitions(HERE/"validate_real_dress.py",("pose_channels",))
    definitions(HERE/"diagnose_skin_transfer.py",("json_content","matrix"))
    native_pose=namespace["pose_channels"]; converter=namespace["json_content"]; diag_matrix=namespace["matrix"]
    bone=NS(name="DEF",rotation_mode="QUATERNION",location=[0.,2.3841730012463813e-7,0.],rotation_euler=[0.,0.,0.],
        rotation_quaternion=[1.,0.,0.,0.],rotation_axis_angle=[0.,0.,1.,0.],scale=[1.000000238418579,.9999940991401672,1.0000004768371582])
    rig=NS(pose=NS(bones=[bone])); actual=native_pose(rig); sealed=json.loads(json.dumps(actual))
    need(type(actual["DEF"]["location"]) is tuple and actual!=sealed,"Real qa native tuple-vs-JSON regression control")
    proof=primitive_equality_receipt(actual,sealed,converter); need(proof["primitive_exact_equal"] and proof["native_container_differences"],"Real qa container normalization failed")
    bone.scale[1]+=.00000001
    need(not primitive_equality_receipt(native_pose(rig),sealed,converter)["primitive_exact_equal"],"Primitive float difference must remain exact/rejected")
    definitions(HERE/"verify_actual_body_proxy_coverage.py",("native_mesh","matrix","digest","need"))
    identity=Matrix([[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]])
    vertices=[NS(index=i,co=Vector(p),groups=[NS(group=0,weight=1.)]) for i,p in enumerate(((0.,0.,0.),(1.,0.,0.),(0.,1.,0.)))]
    snapshot=NS(vertices=vertices,edges=[NS(vertices=(0,1)),NS(vertices=(1,2)),NS(vertices=(2,0))],polygons=[NS(vertices=(0,1,2))],loop_triangles=[NS(vertices=(0,1,2))],calc_loop_triangles=lambda:None)
    released=[]; evaluated=NS(matrix_world=identity,to_mesh=lambda **kwargs:snapshot,to_mesh_clear=lambda:released.append(True))
    obj=NS(name="Scope",vertex_groups=[NS(index=0,name="DEF",lock_weight=False)],data=NS(name="Mesh",as_pointer=lambda:2),as_pointer=lambda:1,evaluated_get=lambda graph:evaluated)
    native_mesh=namespace["native_mesh"](obj,None,None); sealed_mesh=json.loads(json.dumps(converter(native_mesh)))
    fields=("native_vertex_index_order","edges","faces","weights","native_group_mapping")
    need(released==[True] and type(native_mesh["edges"][0]) is tuple and native_mesh["edges"]!=sealed_mesh["edges"],"Real native_mesh tuple ABI control")
    need(primitive_equality_receipt({k:native_mesh[k] for k in fields},{k:sealed_mesh[k] for k in fields},converter)["primitive_exact_equal"],"Real sealed mesh container comparison failed")
    sealed_mesh["faces"][0].reverse()
    need(not primitive_equality_receipt(native_mesh["faces"],sealed_mesh["faces"],converter)["primitive_exact_equal"],"Native index/face order change must reject")
    need(diag_matrix(identity)==json.loads(json.dumps(diag_matrix(identity))),"Real diag.matrix list ABI control")
    definitions(SURFACE,("_frame","_matrix","_id"))
    frame_obj=NS(parent=NS(name="Main",bl_rna=NS(identifier="Object")),parent_type="OBJECT",parent_bone="",matrix_parent_inverse=identity,matrix_basis=identity)
    frame=namespace["_frame"](frame_obj)
    need(type(frame["inverse"][0]) is list and frame==json.loads(json.dumps(frame)),"Real surface._frame list ABI control")
    try:converter({1:1.})
    except TypeError:pass
    else:raise RuntimeError("Real converter must reject undeclared integer dictionary keys")
    return {"passed":True,"real_pinned_definitions": ["qa.pose_channels","diag.json_content","diag.matrix","surface._frame","coverage.native_mesh"],"controls":8,"native_run":False}


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

    No decompose/normalization/bone-matrix setter is used. All stored representations
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
    native_world_copy_proof(identity,identity,"world chart exact control")
    reset=[row[:] for row in identity]; reset[2][3]=1.0064
    try:native_world_copy_proof(reset,identity,"lost parent inverse control")
    except RuntimeError:pass
    else:raise RuntimeError("Lost parent inverse world offset must reject")
    import io
    tiny={"native_meshes":{"ManualOracle800":{"points":[[1.,2.,3.]]},"RegisteredBody":{"points":[[0.,0.,0.]],
        "native_vertex_index_order":[0],"native_vertex_face_edge_sha256":"fixture","native_group_mapping":[],"matrix_world":identity,"weights_complete":True,"weights":[{"dense":"skip"}]}}}
    for name in ("label","author_frame","key_values","rig_channels","input_channels","rig_world","source_frame","upstream_world","native_original_raw_channels","source_manual_constraint_modes","native_main_manual_matrices"):tiny[name]=None
    fake={"endpoints":{label:{"sample":dict(tiny,label=label),"private_native_inputs":{"ManualOracle800":{"points":[[999.,999.,999.]]}}} for label in ("N","L","T")}}
    parsed=sealed_input_samples(io.StringIO(json.dumps(fake,indent=2)))
    need(all(row["native_meshes"]["ManualOracle800"]["points"]==[[1.,2.,3.]] and "weights" not in row["native_meshes"]["RegisteredBody"] for row in parsed.values()),"Stream must ignore old private/dense fields")
    del fake["endpoints"]["L"]["sample"]["input_channels"]
    try:sealed_input_samples(io.StringIO(json.dumps(fake,indent=2)))
    except RuntimeError:pass
    else:raise RuntimeError("Missing sealed sample input must reject")
    from types import SimpleNamespace as NS
    made=[]
    def follow(owner,target,bone,name):
        constraint=NS(owner_space="WORLD",target_space="WORLD",mix_mode="REPLACE",remove_target_shear=False)
        made.append((owner,target,bone,constraint));return constraint
    owner=NS(id_data=NS(type="ARMATURE"),bone=NS())
    con=pose_upstream_follow(NS(_world_follow=follow),owner,"Main","Hips")
    need(con.owner_space==con.target_space=="POSE" and con.mix_mode=="REPLACE" and not con.remove_target_shear,"Bone-only pose-space control failed")
    try:pose_upstream_follow(NS(_world_follow=follow),NS(type="ARMATURE"),"Main","")
    except RuntimeError:pass
    else:raise RuntimeError("Object cannot use bone-only POSE follow")
    exact=upstream_pose_diagnostic(identity,identity,{"Hips":identity},{"Hips":identity},1.)
    need(exact["rig_world_exact"] and exact["upstream_pose"]["Hips"]["maximum_pose_component_delta"]==0.,"Native identical space diagnostic")
    changed=[row[:] for row in identity];changed[2][3]=1.e-8
    need(not upstream_pose_diagnostic(identity,changed,{"Hips":identity},{"Hips":identity},1.)["rig_world_exact"],"World mismatch must remain exact")
    pose=[row[:] for row in identity];pose[0][3]=6.e-5
    delta=upstream_pose_diagnostic(scaled,scaled,{"Hips":identity},{"Hips":pose},1.)["upstream_pose"]["Hips"]
    need(abs(delta["pose_translation_world_delta_m"]-.782*6.e-5)<1.e-15,"Physical pose diagnostic must retain world scale")
    return {"passed": True, "legacy_focused_controls": 13,"new_raw_trs_controls":9,"new_v3_chart_stream_controls":4,"real_abi_serialization":real_abi_serialization_controls(),
            "new_v5_pose_space_controls":5,"native_run": False, "accepted": False}


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
    from mathutils import Matrix
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
              "scope":"Owned native input-only evaluation from protected sealed actual N/L/T replay, freshly verified against main oracle/Body. No Cloth steps/bake/time travel. Original is raw-channel snapshot replay; Keys retained but not deliberately exercised.",
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
        saved_basis=rig.matrix_basis.copy(); saved_mode=rig.rotation_mode
        upstream=surface._ancestors(rig,record); waist=record["controls"]["waist"]
        controls={record["controls"][k] for k in ("waist","mid","hem")}
        controls.update(name for entry in record["controls"]["chains"] for name in entry.values())
        manual={n for chain in record["chains"] for n in chain["manual"]}; deform={n for chain in record["chains"] for n in chain["def"]}
        forbidden={n for chain in record["chains"] for n in chain["phys"]}|deform
        keep=set(upstream)|controls|manual|deform
        need(len(record["chains"])==len(record["controls"]["chains"])==8 and keep<=set(rig.data.bones.keys()) and not(set(upstream)&forbidden),"Exact8-wire upstream/input subset unresolved")
        sealed=json.loads(SEALED_REPORT.read_text(encoding="utf-8"))
        need(sealed["script_sha256"]==PINS[HERE/"prototype_input800_reproduction_v2.py"] and sealed["native_endpoint_file"]["sha256"]==PINS[SEALED_ENDPOINT]
             and Path(sealed["native_endpoint_file"]["path"]).resolve()==SEALED_ENDPOINT.resolve(),"Sealed actual input provenance differs")
        need(all(sealed.get(k) is True for k in ("canonical_validation_before_private_ids","canonical_validation_after_reload","owned_cleanup_exact","cache_metadata_exact",
             "pose_after_reload_exact","playback_after_reload_exact","author_frame_after_reload_exact","source_disk_exact","input_artist_disk_exact","script_disk_exact","native_endpoint_index_identity_exact"))
             and not sealed["cleanup_errors"] and sealed["protection_before_reload"]["success"] and sealed["protection_after_reload"]["success"],"Sealed actual input capture was not protected/cleaned")
        need({p:v["sha256"] for p,v in sealed["source_before"].items()}=={p:v["sha256"] for p,v in report["source_before"].items()},"Canonical/helpers differ from sealed actual input runtime")
        with SEALED_ENDPOINT.open(encoding="utf-8") as stream:snapshots=sealed_input_samples(stream)
        report["sealed_input_replay"]={"report":str(SEALED_REPORT),"report_sha256":PINS[SEALED_REPORT],"endpoint":str(SEALED_ENDPOINT),"endpoint_sha256":PINS[SEALED_ENDPOINT],
            "old_private_result":"Failed and not reused as expected geometry","old_completed":sealed["native_completed"],"fresh_main_oracle_and_body":{},"primitive_comparisons":{},"dense_evaluated_Body_weights":"Remain in sealed evidence; fresh geometry/index/groups verified, artist raw protection still exact"}
        def primitive_equal(label,field,actual_value,sealed_value):
            receipt=primitive_equality_receipt(actual_value,sealed_value,diag.json_content)
            report["sealed_input_replay"]["primitive_comparisons"].setdefault(label,{})[field]=receipt
            write()  # Low-volume typed differences persist before every require.
            return receipt["primitive_exact_equal"]
        for label,snap in snapshots.items():
            budget(); need(snap["author_frame"]==report["author_frame"] and key_values(source)==original_keys,"Saved author frame/raw Keys differ")
            qa.restore_channels(rig,snap["rig_channels"],saved_basis,saved_mode); bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get()
            pose_equal=primitive_equal(label,"main_native_pose_channels",qa.pose_channels(rig),snap["rig_channels"])
            keys_equal=primitive_equal(label,"native_Key_values",key_values(source,graph),snap["key_values"])
            need(pose_equal and keys_equal,"Native main replay/Key values differ")
            set_keys(oracle,snap["key_values"]); bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get()
            fresh_oracle=read.native_mesh(oracle,graph,diag); fresh_body=read.native_mesh(body,graph,diag)
            old_oracle,old_body=(snap["native_meshes"][key] for key in ("ManualOracle800","RegisteredBody"))
            fields=("native_vertex_index_order","edges","faces","weights","native_group_mapping")
            oracle_identity=primitive_equal(label,"main_native_oracle_identity",{k:fresh_oracle[k] for k in fields},{k:old_oracle[k] for k in fields})
            need(len(fresh_oracle["points"])==800 and oracle_identity,"Actual oracle replay topology/groups/weights differ")
            need(fresh_body["native_vertex_face_edge_sha256"]==old_body["native_vertex_face_edge_sha256"] and fresh_body["native_group_mapping"]==old_body["native_group_mapping"] and fresh_body["weights_complete"] and old_body["weights_complete"],"Native Body replay index/group identity differs")
            errors={"oracle":error_summary(fresh_oracle["points"],old_oracle["points"],metres),"Body":error_summary(fresh_body["points"],old_body["points"],metres)}
            need(max(error["maximum_m"] for error in errors.values())<=guard,"Fresh main oracle/Body does not reproduce sealed actual pose")
            source_chart_equal=primitive_equal(label,"source_frame",surface._frame(source),snap["source_frame"])
            rig_world_equal=primitive_equal(label,"rig_world",diag.matrix(rig.evaluated_get(graph).matrix_world),snap["rig_world"])
            need(source_chart_equal and rig_world_equal,"Native saved object chart differs")
            posed=rig.evaluated_get(graph); upstream_equal=primitive_equal(label,"upstream_world",{name:diag.matrix(posed.matrix_world@posed.pose.bones[name].matrix) for name in upstream+[waist]},snap["upstream_world"])
            need(upstream_equal,"Native Body/waist upstream pose differs")
            report["sealed_input_replay"]["fresh_main_oracle_and_body"][label]=errors
            endpoint_data[label]={"sealed_actual_sample_reference":{"path":str(SEALED_ENDPOINT),"sha256":PINS[SEALED_ENDPOINT],"label":label},
                "fresh_main_replay":errors,"fresh_Body_world_points":fresh_body["points"],"accepted":False}
            del fresh_body,fresh_oracle
        n,l,t=(snapshots[label] for label in ("N","L","T")); report["actual_inputs"]=sealed["actual_inputs"]
        need(report["actual_inputs"]["knee_delta_m"]>height*.01*metres and report["actual_inputs"]["Body_N_L"]["maximum_m"]>guard
             and min(report["actual_inputs"]["hem_L_T_delta_m"],report["actual_inputs"]["Manual800_L_T"]["maximum_m"])>guard
             and report["actual_inputs"]["Body_L_T"]["maximum_m"]<=guard and l["upstream_world"]==t["upstream_world"],"Sealed actual input/motion isolation insufficient")
        need(all(snap["key_values"]==n["key_values"] for snap in snapshots.values()),"Sealed evaluated Keys differ across poses")
        endpoint_path.write_text(json.dumps(diag.json_content({"stage":"INPUT800_REPRODUCTION","units_to_metres":metres,"endpoints":endpoint_data,"accepted":False}),indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
        report["native_endpoint_index_identity_exact"]=True; write()
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
        for name in upstream+[waist]: pose_upstream_follow(surface,input_rig.pose.bones[name],rig,name)
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
        before.parent=input_rig; before.parent_type,before.parent_bone=source.parent_type,source.parent_bone
        before.matrix_parent_inverse,before.matrix_basis=source.matrix_parent_inverse.copy(),source.matrix_basis.copy()
        before.modifiers[0].object=input_rig; link(before)
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
                    need(len(pb.constraints)==1 and pb.constraints[0].type=="COPY_TRANSFORMS","Extra upstream constraint")
                    con=pb.constraints[0]
                    need(con.owner_space==con.target_space=="POSE" and con.mix_mode=="REPLACE" and not con.remove_target_shear and con.influence==1. and not con.mute,"Changed native upstream pose follow")
                    edge("upstream",con.target,con.subtarget)
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
                expected_frame=surface._frame(source if mesh is before else actual); copied_frame=surface._frame(mesh)
                need(all(copied_frame[key]==expected_frame[key] for key in ("type","bone","inverse","basis")),"Copied native mesh parent chart differs")
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
            posed=rig.evaluated_get(graph); private_pose=input_rig.evaluated_get(graph)
            space_proof=upstream_pose_diagnostic(posed.matrix_world,private_pose.matrix_world,
                {name:posed.pose.bones[name].matrix for name in upstream+[waist]},
                {name:private_pose.pose.bones[name].matrix for name in upstream+[waist]},metres)
            report.setdefault("native_space_diagnostics",{})[snap["label"]]=space_proof; write()
            need(space_proof["rig_world_exact"],"POSE upstream requires exact current native Rig world identity")
            proof["native_space_diagnostic"]=space_proof
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
            proof["mesh_world_chart"]=native_world_copy_proof(mesh["matrix_world"],source.evaluated_get(graph).matrix_world,"before Body native mesh")
            proof["native_mesh_parent_chart"]=surface._frame(before)
            fields=("edges","faces","weights","native_group_mapping")
            private_identity=primitive_equal(label,"private_native_before800_identity",{k:mesh[k] for k in fields},{k:expected[k] for k in fields})
            need(mesh["weights_complete"] and mesh["native_vertex_index_order"]==list(range(800)) and private_identity,"Native preattachment topology/groups/weights changed")
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
        after.parent_type,after.parent_bone=actual.parent_type,actual.parent_bone
        after.matrix_parent_inverse,after.matrix_basis=actual.matrix_parent_inverse.copy(),actual.matrix_basis.copy()
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
            transform_proof["before_mesh_world_chart"]=native_world_copy_proof(meshes["Input800BeforeBody"]["matrix_world"],source.evaluated_get(graph).matrix_world,"before Body native mesh")
            transform_proof["after_mesh_world_chart"]=native_world_copy_proof(meshes["Input800AfterBody"]["matrix_world"],actual.evaluated_get(graph).matrix_world,"after Body native mesh")
            transform_proof["native_mesh_parent_charts"]={"before":surface._frame(before),"after":surface._frame(after)}
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
        report["frozen_pins_disk_exact"]=all(sha(path)==expected for path,expected in PINS.items())
        report["native_endpoint_file"]={"path":str(endpoint_path),"sha256":sha(endpoint_path) if endpoint_path.exists() else None}
        report["ready_for_next_private_gate"]=bool(report["native_completed"] and not cleanup_errors and report["source_disk_exact"] and report["input_artist_disk_exact"] and report["script_disk_exact"] and report["frozen_pins_disk_exact"])
        report["elapsed_seconds"]=time.perf_counter()-started; write()
    print("INPUT800 report:",destination,"ready:",report["ready_for_next_private_gate"],flush=True)
    return 0 if report["ready_for_next_private_gate"] else 2


if __name__ == "__main__": raise SystemExit(main(arguments()))
