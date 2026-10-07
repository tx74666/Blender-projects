"""Read-only factory5.2 diagnosis of saved vs current native Dress RNA contracts.

No add-on import/registration, graph repair, validation bypass, physics request,
frame stepping or blend save. Selected canonical read-only functions are AST-
extracted exactly. Collection success is not compatibility or effect acceptance.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPOSITORY=Path("D:/MyRepository/Blender-addons-by-Randy")
SURFACE=REPOSITORY/"addons/character_designer/skirt_surface.py"
SURFACE_SHA="9d7a928e27464e772330304d03e9ca81462f800951b3172921c87429cf78891c"
ORIGINAL=REPOSITORY/"addons/character_designer/skirt_original_mode.py"
ORIGINAL_SHA="209fe00aa8f90eb57e61d06d10bfe6cd90ab7cbf56ec451794c5012da3684e58"
SOURCE_HELPER=HERE/"source_compatibility52.py"
SOURCE_HELPER_SHA="438e36cd95a9c11f4e1d650f78b58d79fd2866eae8e59a929b993bd42dfbbbdf"
DISK_HELPER=HERE/"artist_disk_protection52.py"
DISK_HELPER_SHA="11d925f0356a45d831ff84339e31bf691df21c257e195497fd36922907167b37"
INPUT=HERE/"actual_install_51_20261006_031045_111/scenes/Cosha_Dress_QA_surface_install.blend"
INPUT_SHA="7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f"
INSTALL=HERE/"actual_install_51_20261006_031045_111/result/workflow_install.json"
INSTALL_SHA="a2157ba399bfe32cc28401847c2556f776761fd607eaa3ba7ea23b61aaec6a32"
FAILED=HERE/"actual_direct_main_manual_source_compat_52_20261006_194401_885/result/input800_reproduction.json"
FAILED_SHA="9d738db7d0f63850ce7fa091bd79d2dc3d20d981e95ffd1afc8b3792a2578b83"
PINS={SURFACE:SURFACE_SHA,ORIGINAL:ORIGINAL_SHA,SOURCE_HELPER:SOURCE_HELPER_SHA,DISK_HELPER:DISK_HELPER_SHA,
      INPUT:INPUT_SHA,INSTALL:INSTALL_SHA,FAILED:FAILED_SHA}
READ_FUNCTIONS=("_require","_json","_digest","_matrix","_id","_rna","_drivers","_topology","_groups","_frame",
                "_node_content","_graph","_helper_contract","_collider_contract","_cloth_contract")
CONSTANTS=("_CHANNELS","_TUNE_CLOTH","_TUNE_COLLISION","COLLIDER_CONTRACT_VERSION","PIN_GROUP","NEUTRAL_MANUAL_KEY")
RECORD_KEY="character_designer_skirt_v1"
RIG_KEY="character_designer_skirt_armature"


def need(condition,message):
    if not condition:raise RuntimeError("NodeContractDiagnostic52: "+message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1048576),b""):h.update(block)
    return h.hexdigest()


def state(path):
    stat=path.stat();return {"bytes":stat.st_size,"mtime_ns":stat.st_mtime_ns,"sha256":sha(path)}


def load(path,expected,name):
    need(sha(path)==expected,"frozen helper differs: "+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def native_namespace(bpy):
    """No package execution. Canonical source text/AST definitions stay exact."""
    need(sha(SURFACE)==SURFACE_SHA and sha(ORIGINAL)==ORIGINAL_SHA,"read-only native ABI source differs")
    text=SURFACE.read_text(encoding="utf-8");tree=ast.parse(text)
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in READ_FUNCTIONS]
    selected+=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="SkirtSurfaceError"]
    selected+=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in CONSTANTS for t in n.targets)]
    need({n.name for n in selected if isinstance(n,ast.FunctionDef)}==set(READ_FUNCTIONS),"canonical read-only function ABI incomplete")
    namespace={"bpy":bpy,"json":json,"hashlib":hashlib}
    for node in selected:exec(compile(ast.get_source_segment(text,node),str(SURFACE),"exec"),namespace)
    original=ORIGINAL.read_text(encoding="utf-8");definitions={n.name:n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
    for name in ("_values","_rest"):exec(compile(ast.get_source_segment(original,definitions[name]),str(ORIGINAL),"exec"),namespace)
    # Surface._rest is exactly a read-only delegation to this original function.
    rest_wrapper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="_rest")
    need(ast.get_source_segment(text,rest_wrapper)=="def _rest(rig, names):\n    from . import skirt_original_mode\n    return skirt_original_mode._rest(rig, names)","Rest delegation ABI changed")
    return namespace,{name:{"line":next(n.lineno for n in selected if isinstance(n,ast.FunctionDef) and n.name==name),
        "AST_sha256":hashlib.sha256(ast.dump(next(n for n in selected if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False).encode()).hexdigest()}
        for name in READ_FUNCTIONS}


def differences(saved,actual,limit=4096):
    """Exact primitive values/types/order; no normalization or tolerance."""
    rows=[];truncated=False
    def add(path,kind,old,new):
        nonlocal truncated
        if len(rows)>=limit:truncated=True;return
        rows.append({"path":path,"kind":kind,"saved_type":type(old).__name__,"runtime_type":type(new).__name__,
                     "saved":old,"runtime":new})
    def visit(old,new,path):
        if len(rows)>=limit:
            nonlocal truncated
            truncated=True;return
        if type(old) is not type(new):add(path,"type",old,new);return
        if type(old) is dict:
            for key in sorted(set(old)|set(new)):
                if key not in old:add(path+[key],"runtime_added_property",None,new[key])
                elif key not in new:add(path+[key],"runtime_missing_property",old[key],None)
                else:visit(old[key],new[key],path+[key])
        elif type(old) is list:
            if len(old)!=len(new):add(path,"sequence_length",len(old),len(new))
            for index in range(min(len(old),len(new))):visit(old[index],new[index],path+[index])
        else:
            need(type(old) in (str,int,float,bool,type(None)),"non-primitive contract value")
            need(type(old) is not float or (math.isfinite(old) and math.isfinite(new)),"nonfinite contract value")
            if old!=new:add(path,"value",old,new)
    visit(saved,actual,[])
    return {"status":"Unknown" if truncated else "measured","exact_equal":not rows and not truncated,
            "canonical_python_equality":saved==actual,
            "difference_count":len(rows),"truncated":truncated,"differences":rows,"accepted":False}


def property_metadata(owner):
    result={}
    for prop in owner.bl_rna.properties:
        if prop.identifier=="rna_type":continue
        result[prop.identifier]={"RNA_type":prop.type,"is_readonly":prop.is_readonly,
            "is_array":getattr(prop,"is_array",False),"array_length":getattr(prop,"array_length",None)}
    return result


def node_metadata(group):
    return {"group_type":group.bl_idname,"interface":[{"name":item.name,"identifier":item.identifier,
            "RNA":property_metadata(item)} for item in group.interface.items_tree if item.item_type=="SOCKET"],
        "nodes":{node.name:{"type":node.bl_idname,"RNA":property_metadata(node),
            "inputs":[{"index":i,"name":socket.name,"identifier":socket.identifier,"type":socket.bl_idname,
                       "RNA":property_metadata(socket)} for i,socket in enumerate(node.inputs)],
            "outputs":[{"index":i,"name":socket.name,"identifier":socket.identifier,"type":socket.bl_idname}
                       for i,socket in enumerate(node.outputs)]} for node in group.nodes}}


def snapshot(source,rig,group,read,bpy):
    channels={bone.name:{"mode":bone.rotation_mode,"channels":{key:list(getattr(bone,key)) for key in read["_CHANNELS"]}}
              for bone in rig.pose.bones}
    return {"record_sha256":hashlib.sha256(source[RECORD_KEY].encode()).hexdigest(),"frame":[bpy.context.scene.frame_current,bpy.context.scene.frame_subframe],
        "source_raw_mesh":read["_digest"]({"topology":read["_topology"](source.data),"vertices":[list(v.co) for v in source.data.vertices],"groups":read["_groups"](source)}),
        "source_modifiers":read["_digest"]([read["_rna"](m) for m in source.modifiers]),
        "rig_rest":read["_digest"](read["_rest"](rig,rig.data.bones.keys())),"rig_raw_channels":read["_digest"](channels),
        "nodes":read["_digest"](read["_node_content"](group)),
        "native_ID_inventory":{kind:sorted((item.name,item.as_pointer()) for item in getattr(bpy.data,kind))
            for kind in ("objects","meshes","armatures","curves","shape_keys","actions","node_groups","collections","scenes")}}


def pure_checks():
    same={"a":[True,1,2.0,None],"b":{"type":"RNA"}}
    need(differences(same,same)["exact_equal"],"equal contract rejected")
    cases=({"a":[1,1,2.0,None],"b":{"type":"RNA"}}, {"a":[True,1,2.0,None],"b":{"type":"RNA","new":False}},
        {"a":[True,1,2.0,None]}, {"a":[True,1,2.0],"b":{"type":"RNA"}}, {"a":[True,2,2.0,None],"b":{"type":"RNA"}})
    need(all(not differences(same,value)["exact_equal"] for value in cases),"exact difference lost")
    need(differences({"a":1,"b":2},{"a":2,"b":3},1)["status"]=="Unknown","budget became pass")
    namespace,_abi=native_namespace(SimpleNamespace())
    need(set(READ_FUNCTIONS)<=set(namespace),"actual AST ABI not executable")
    need(not any("character_designer" in name for name in sys.modules),"canonical package unexpectedly imported")
    return {"passed":True,"pure_difference_controls":7,"actual_read_only_AST_ABI":len(READ_FUNCTIONS),"native_run":False,"accepted":False}


def arguments():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path)
    parser.add_argument("--input",type=Path,default=INPUT);parser.add_argument("--max-seconds",type=float,default=30.)
    parser.add_argument("--artist-protection",type=Path);parser.add_argument("--artist-protection-sha")
    parser.add_argument("--include-helper-contracts",action="store_true")
    parser.add_argument("--pure-checks",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    if not args.pure_checks:
        need(args.input.resolve()==INPUT.resolve() and args.output is not None and args.output.is_absolute()
             and not args.output.exists() and args.output.resolve().is_relative_to(HERE) and args.output.resolve()!=HERE,
             "exact immutable input and fresh private output only")
        need(args.artist_protection is not None and args.artist_protection_sha is not None and 0.<args.max_seconds<=30.,"explicit V3 protection and soft30 required")
    return args


def main(args):
    if args.pure_checks:print(json.dumps(pure_checks()));return 0
    import bpy
    need(bpy.app.background and tuple(bpy.app.version[:3])==(5,2,0) and not bpy.data.filepath
         and Path(bpy.app.binary_path).resolve()==Path("D:/Blender5.2/blender.exe").resolve()
         and "--factory-startup" in sys.argv and "--disable-autoexec" in sys.argv and "--threads" in sys.argv
         and sys.argv[sys.argv.index("--threads")+1]=="1","empty factory native5.2/one thread only")
    need(all(sha(path)==expected for path,expected in PINS.items()),"input/source/evidence frozen pin changed")
    helper=load(SOURCE_HELPER,SOURCE_HELPER_SHA,"node_source_helper52")
    disk=load(DISK_HELPER,DISK_HELPER_SHA,"node_disk_helper52")
    protected=disk.proof(args.artist_protection,args.artist_protection_sha)
    files=tuple(PINS)+(Path(__file__),args.artist_protection,disk.ARTIST)
    before={str(path):state(path) for path in files};manifest=helper.current_manifest()
    report={"stage":"NODE_CONTRACT_DIAGNOSTIC_52","collection_success":False,"native_compatibility_proved":False,
        "accepted":False,"artist_saved":False,"guard_bypassed":False,"graph_rebaselined":False,
        "runtime":{"version":list(bpy.app.version),"binary":bpy.app.binary_path},"script_sha256":sha(Path(__file__)),
        "input_sha256":INPUT_SHA,"current_artist_disk_protection":protected,"source_before":manifest,"files_before":before,
        "contracts":{},"unresolved":[],"cleanup_errors":[],"scope":__doc__}
    args.output.mkdir();destination=args.output/"node_contract_diagnostic.json";started=time.perf_counter();raw_before=None
    def budget():need(time.perf_counter()-started<args.max_seconds,"diagnostic soft30 exhausted")
    def collect(label,expected,reader):
        budget()
        try:
            actual=reader();row=differences(expected,actual)
            report["contracts"][label]={"saved":expected,"runtime":actual,"comparison":row}
            if row["status"]!="measured":report["unresolved"].append(label+": diff budget incomplete")
        except Exception as error:
            report["contracts"][label]={"status":"Unknown","error":str(error),"accepted":False};report["unresolved"].append(label)
    try:
        need(bpy.ops.wm.open_mainfile(filepath=str(INPUT),load_ui=False,use_scripts=False)=={"FINISHED"},"native read failed")
        budget();read,abi=native_namespace(bpy);report["canonical_AST_read_only_ABI"]=abi
        source_name=json.loads(INSTALL.read_text(encoding="utf-8"))["source"]
        source=bpy.data.objects.get(source_name);need(source is not None and type(source.get(RECORD_KEY)) is str,"saved source record missing")
        raw=source[RECORD_KEY];record=json.loads(raw);surface=record["physics"]["surface"];rig=source.get(RIG_KEY)
        need(record["source"]==source.name and rig is not None and record["rig"]==rig.name,"source/rig record identity differs")
        group=bpy.data.node_groups.get(surface["node_group"]);modifier=source.modifiers.get(surface["overlay"])
        need(group is not None and modifier is not None and modifier.type=="NODES" and modifier.node_group==group,"exact saved overlay group missing")
        report["identity"]={"source":source.name,"rig":rig.name,"owner":record["owner"],"group":group.name,"group_users":group.users,
            "group_role":group.get("character_designer_skirt_surface_role"),"modifier":modifier.name,"loaded_frame":bpy.context.scene.frame_current}
        raw_before=snapshot(source,rig,group,read,bpy);report["native_raw_before"]=raw_before
        collect("node_contract",surface["node_contract"],lambda:read["_node_content"](group))
        report["node_native_RNA_metadata"]=node_metadata(group)
        report["phase"]="node_contract_collected"
        # Persist first-failure evidence before any optional wider raw reads.
        destination.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
        if args.include_helper_contracts:
            actual=bpy.data.objects[surface["roles"]["CLOTH_PROXY"][0]];body=bpy.data.objects[surface["roles"]["BODY_ATTACHMENT"][0]]
            for role,names in surface["roles"].items():
                if role=="BODY_ATTACHMENT":continue
                for name in names:
                    collect("helper/"+name,surface["contracts"][name],lambda name=name:read["_helper_contract"](bpy.data.objects[name],dynamic_pin=(name==actual.name)))
            cloth=actual.modifiers[2];need(cloth.type=="CLOTH","saved Cloth slot differs")
            collect("cloth_contract",surface["cloth_contract"],lambda:read["_cloth_contract"](cloth))
            collect("body_frame",surface["body_frame"],lambda:read["_frame"](body))
            collect("body_constraints",surface["body_constraints"],lambda:[read["_rna"](c) for c in body.constraints])
            collect("body_collision",surface["body_collision"],lambda:read["_rna"](body.collision))
            upstream=bpy.data.objects[surface["body"]]
            collect("body_topology",surface["body_topology"],lambda:read["_digest"](read["_topology"](upstream.data)))
            collect("body_groups",surface["body_groups"],lambda:read["_digest"](read["_groups"](upstream)))
            for name in record["physics"]["colliders"][:-1]:
                expected=surface["colliders"][name]
                collect("collider/"+name,expected,lambda name=name,expected=expected:read["_collider_contract"](bpy.data.objects[name])
                    if isinstance(expected,dict) and "version" in expected else read["_helper_contract"](bpy.data.objects[name]))
        report["native_raw_after"]=snapshot(source,rig,group,read,bpy)
        report["native_raw_exact"]=report["native_raw_after"]==raw_before
        need(report["native_raw_exact"],"read-only diagnostic changed loaded source/rig/node state")
        report["collection_success"]=not report["unresolved"]
    except Exception as error:report["exception"]={"type":type(error).__name__,"message":str(error)}
    finally:
        try:need(bpy.ops.wm.read_factory_settings(use_empty=True)=={"FINISHED"},"factory disposal failed")
        except Exception as error:report["cleanup_errors"].append(str(error))
        report["files_after"]={str(path):state(path) for path in files};report["disk_exact"]=report["files_after"]==before
        report["source_after"]=helper.current_manifest();report["source_exact"]=report["source_after"]==manifest
        try:disk.proof(args.artist_protection,args.artist_protection_sha);report["current_artist_protection_after_exact"]=True
        except Exception as error:report["current_artist_protection_after_exact"]=False;report["cleanup_errors"].append(str(error))
        report["elapsed_seconds"]=time.perf_counter()-started
        report["collection_success"]=bool(report["collection_success"] and not report["cleanup_errors"] and report["disk_exact"] and report["source_exact"])
        destination.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    print(json.dumps({"collection_success":report["collection_success"],"report":str(destination),"accepted":False}))
    return 0 if report["collection_success"] else 2


if __name__=="__main__":raise SystemExit(main(arguments()))
