"""Read-only saved Artist vs immutable7ac provenance; no registration/seek/save.

Exact raw content comparison is separate from saved-frame pose/evaluated world.
Collection success does not make differing assets compatible or accept effects.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
QA=HERE/"validate_real_dress.py"
QA_SHA="613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046"
DISK=HERE/"artist_disk_protection52.py"
DISK_SHA="11d925f0356a45d831ff84339e31bf691df21c257e195497fd36922907167b37"
SOURCE=HERE/"source_compatibility52_node_ui.py"
SOURCE_SHA="08d36c4e561c808ed40a49e6b094085ef687a8a2e02bf5413c56ea203332507b"
FIXTURE=HERE/"actual_install_51_20261006_031045_111/scenes/Cosha_Dress_QA_surface_install.blend"
FIXTURE_SHA="7acb26009d56c4f066163055a3cb92b6b779772a3a51b289015b4133ebae788f"
READ=("digest","id_name","custom_content","simple_rna","curve_content","action_content","raw_mesh_content","rest_content","pose_channels")
RECORD_KEY="character_designer_skirt_v1"
RIG_KEY="character_designer_skirt_armature"


def need(value,message):
    if not value:raise RuntimeError("ArtistFixture52: "+message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    return h.hexdigest()


def load(path,expected,name):
    need(sha(path)==expected,"Frozen helper changed: "+str(path))
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def readers(bpy):
    text=QA.read_text(encoding="utf-8");tree=ast.parse(text)
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in READ]
    nodes += [node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=="Protection"]
    need({node.name for node in nodes}==set(READ)|{"Protection"},"Frozen raw read ABI differs")
    values={"bpy":bpy,"hashlib":hashlib,"json":json}
    for node in nodes:
        source=ast.get_source_segment(text,node)
        if node.name=="simple_rna":
            need(source.count("elif prop.is_array:")==1,"Scalar RNA compatibility ABI differs")
            source=source.replace("elif prop.is_array:","elif getattr(prop, 'is_array', False):",1)
        exec(compile(source,str(QA),"exec"),values)
    return SimpleNamespace(**values)


def primitive(value):return json.loads(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False))
def matrix(value):return [list(row) for row in value]


def animation(owner,q):
    data=owner.animation_data
    if data is None:return None
    return {"rna":q.simple_rna(data),"nla":[{"rna":q.simple_rna(track),"strips":[q.simple_rna(s) for s in track.strips]} for track in data.nla_tracks],
            "drivers":[{"path":c.data_path,"index":c.array_index,"curve":q.curve_content(c),"driver":q.simple_rna(c.driver),
              "variables":[{"rna":q.simple_rna(v),"targets":[q.simple_rna(t) for t in v.targets]} for v in c.driver.variables]} for c in data.drivers]}


def locate(bpy):
    choices=[]
    for scene in bpy.data.scenes:
        setup=scene.get("character_designer_setup")
        if setup is None:continue
        rig,body=setup.get("rig"),setup.get("body")
        if not isinstance(rig,bpy.types.Object) or rig.type!="ARMATURE" or not isinstance(body,bpy.types.Object) or body.type!="MESH":continue
        sources=[obj for obj in scene.objects if obj.type=="MESH" and RECORD_KEY in obj and obj.get(RIG_KEY)==rig]
        for obj in sources:
            record=json.loads(obj[RECORD_KEY])
            need(record["source"]==obj.name and record["rig"]==rig.name,"Saved Dress pointer/record disagreement")
            need([m.object for m in body.modifiers if m.type=="ARMATURE" and m.show_viewport]==[rig],"Registered Body binding ambiguous")
            choices.append((scene,rig,body,obj,record))
    need(len(choices)==1,"Need one saved Setup rig/body + native Dress record, no name fallback: "+str(len(choices)))
    return choices[0]


def snapshot(bpy,q):
    scene,rig,body,dress,record=locate(bpy)
    need(scene==bpy.context.scene,"Saved pointer scene is not current; no scene-switch fallback")
    protection=q.Protection();graph=bpy.context.evaluated_depsgraph_get()
    result={"frame":[scene.frame_current,scene.frame_subframe],"units":q.simple_rna(scene.unit_settings),"raw_meshes":{},
            "Rest":q.rest_content(rig),"rig_pose":q.pose_channels(rig),"rig_object_basis":matrix(rig.matrix_basis),
            "rig_world_raw":matrix(rig.matrix_world),"rig_world_evaluated":matrix(rig.evaluated_get(graph).matrix_world),
            "parent_charts":{},"bindings":{},"Keys_channels":{},"Actions":{},"selection":{"Scene":scene.name,"MainRig":q.id_name(rig),"Body":q.id_name(body),"Dress":q.id_name(dress)},
            "Dress_record":record,"native_pointers_comparable_across_files":False}
    for bone in rig.data.bones:
        result["Rest"][bone.name].update(head=list(bone.head_local),tail=list(bone.tail_local),roll_matrix_only=True)
    for role,obj in (("Body",body),("Dress",dress),("MainRig",rig)):
        result["parent_charts"][role]={"parent":q.id_name(obj.parent),"type":obj.parent_type,"bone":obj.parent_bone,
            "inverse":matrix(obj.matrix_parent_inverse),"basis":matrix(obj.matrix_basis),"world":matrix(obj.matrix_world)}
        owners=[obj,obj.data]
        if obj.type=="MESH":
            result["raw_meshes"][role]=q.raw_mesh_content(obj)
            if obj.data.shape_keys:
                owners.append(obj.data.shape_keys);result["Keys_channels"][role]=q.simple_rna(obj.data.shape_keys)
                result["Keys_channels"][role]["blocks"]=[q.simple_rna(block) for block in obj.data.shape_keys.key_blocks]
            else:result["Keys_channels"][role]=None
        result["bindings"][role]=[animation(owner,q) for owner in owners]
    result["Actions"]={action.name:{"sha256":q.digest(q.action_content(action)),"slots":q.simple_rna(action).get("last_slot_handle"),
                       "native_slot_count":len(action.slots) if hasattr(action,"slots") else None} for action in bpy.data.actions}
    stable={"pose":q.digest(q.pose_channels(rig)),"bindings":q.digest(result["bindings"]),"pointers":[(o.as_pointer(),o.data.as_pointer()) for o in (rig,body,dress)]}
    result=primitive(result)
    need(q.Protection.verify(protection)["success"],"Read-only raw/Rest/Actions/NLA protection failed")
    current_bindings={role:[animation(owner,q) for owner in ([obj,obj.data]+([obj.data.shape_keys] if obj.type=="MESH" and obj.data.shape_keys else []))] for role,obj in (("Body",body),("Dress",dress),("MainRig",rig))}
    need(stable["pose"]==q.digest(q.pose_channels(rig)) and stable["bindings"]==q.digest(current_bindings)
         and stable["pointers"]==[(o.as_pointer(),o.data.as_pointer()) for o in (rig,body,dress)],"Read-only pose/bindings/pointer changed")
    return result


def compare(a,b,q):
    def first(old,new,path=""):
        if old==new:return None
        if isinstance(old,dict) and isinstance(new,dict):
            for k in sorted(set(old)|set(new)):
                if k not in old or k not in new:return {"path":path+"/"+str(k),"presence":[k in old,k in new]}
                if old[k]!=new[k]:return first(old[k],new[k],path+"/"+str(k))
        if isinstance(old,list) and isinstance(new,list):
            for i,(x,y) in enumerate(zip(old,new)):
                if x!=y:return first(x,y,path+"/"+str(i))
            return {"path":path,"lengths":[len(old),len(new)]}
        return {"path":path,"Artist":old,"fixture":new}
    def rows(old,new):
        result={}
        for key in sorted(set(old)|set(new)):
            x,y=old.get(key),new.get(key);equal=key in old and key in new and x==y
            result[key]={"equal":equal,"Artist_sha256":q.digest(x),"fixture_sha256":q.digest(y),
                "Artist_count":len(x) if isinstance(x,(dict,list)) else None,"fixture_count":len(y) if isinstance(y,(dict,list)) else None,
                "first_exact_difference":None if equal else first(x,y)}
        return result
    meshes={role:rows(a["raw_meshes"][role],b["raw_meshes"][role]) for role in ("Body","Dress")}
    rest=rows(a["Rest"],b["Rest"]);actions=rows(a["Actions"],b["Actions"])
    return {"raw_mesh_fields":meshes,"Rest_per_bone":rest,"Actions_per_ID":actions,
            "Rest_changed_bones":[name for name,row in rest.items() if not row["equal"]],
            "saved_frame_context_fields":rows({k:a[k] for k in ("frame","units","parent_charts","rig_world_raw","rig_world_evaluated","rig_object_basis","rig_pose","bindings","Keys_channels")},{k:b[k] for k in ("frame","units","parent_charts","rig_world_raw","rig_world_evaluated","rig_object_basis","rig_pose","bindings","Keys_channels")}),
            "all_primary_raw_mesh_and_Rest_equal":all(r["equal"] for table in meshes.values() for r in table.values()) and all(r["equal"] for r in rest.values()),
            "physics_results_applicable_to_current_artist":"Unproven; content identity alone excludes live mode/pose/cache/deployment/quality acceptance","accepted":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--artist-protection",type=Path,required=True);parser.add_argument("--artist-protection-sha",required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists(),"Fresh private output JSON required")
    import bpy
    need(bpy.app.background and bpy.app.version[:2]==(5,2) and "--factory-startup" in sys.argv and not bpy.data.filepath,"Empty factory BG5.2 only")
    disk=load(DISK,DISK_SHA,"compare_disk");source=load(SOURCE,SOURCE_SHA,"compare_source")
    pins={QA:QA_SHA,DISK:DISK_SHA,SOURCE:SOURCE_SHA,FIXTURE:FIXTURE_SHA,Path(__file__):sha(__file__)}
    need(all(sha(p)==value for p,value in pins.items()),"Frozen comparator files changed")
    report={"accepted":False,"collection_success":False,"artist_loaded_readonly":False,"saved_any_blend":False,"seek_or_Cloth_api_called":False,
            "no_addon_registration":True,"RNA_scalar_array_API":"Frozen QA private simple_rna getattr(is_array,False); captures scalar strings","errors":[]}
    before=source.current_manifest();report["source_before"]=before
    try:
        report["artist_before"]=disk.proof(args.artist_protection,args.artist_protection_sha);q=readers(bpy)
        artist=Path(report["artist_before"]["receipt"]["artist_path"])
        bpy.ops.wm.open_mainfile(filepath=str(artist),load_ui=False);report["artist_loaded_readonly"]=True
        a=snapshot(bpy,q);report["Artist_identity"]=a["selection"]
        bpy.ops.wm.open_mainfile(filepath=str(FIXTURE),load_ui=False);b=snapshot(bpy,q);report["fixture_identity"]=b["selection"]
        report["comparison"]=compare(a,b,q);report["collection_success"]=True
    except Exception as error:report["errors"].append({"exception":repr(error),"traceback":traceback.format_exc()})
    finally:
        try:
            bpy.ops.wm.read_factory_settings(use_empty=True);report["loaded_scenes_disposed"]=True
        except Exception as error:report["errors"].append({"factory_disposal":repr(error)})
        try:
            report["artist_after"]=disk.proof(args.artist_protection,args.artist_protection_sha);report["source_after"]=source.current_manifest()
            report["all_files_source_disk_exact"]=report["source_after"]==before and all(sha(p)==value for p,value in pins.items())
            need(report["all_files_source_disk_exact"],"Source/file fingerprint changed")
        except Exception as error:report["errors"].append({"final_guard":repr(error)})
        report["collection_success"]=report["collection_success"] and not report["errors"]
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2),encoding="utf-8")
    print(json.dumps({"collection_success":report["collection_success"],"errors":report["errors"],"report":str(args.output)}));return 0 if report["collection_success"] else 2


if __name__=="__main__":raise SystemExit(main())
