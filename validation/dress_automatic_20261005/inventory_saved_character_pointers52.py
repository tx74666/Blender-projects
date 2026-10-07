"""Read-only saved pointer/storage inventory; no target guessing or registration."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PARENT=HERE/"compare_current_artist_fixture52.py"
PARENT_SHA="b0b4730dac104dc6ad750eaba2ee7cb89acf6ed57a274d15f8c7bc57f296ec6f"


def main():
    spec=importlib.util.spec_from_file_location("pointer_inventory_frozen",PARENT);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    p.need(p.sha(PARENT)==PARENT_SHA,"Frozen comparator changed")
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--artist-protection",type=Path,required=True);parser.add_argument("--artist-protection-sha",required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    p.need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists(),"Fresh private JSON required")
    import bpy
    p.need(bpy.app.background and bpy.app.version[:2]==(5,2) and "--factory-startup" in sys.argv and not bpy.data.filepath,"Empty factory5.2 only")
    disk=p.load(p.DISK,p.DISK_SHA,"inventory_disk");source=p.load(p.SOURCE,p.SOURCE_SHA,"inventory_source")
    pins={PARENT:PARENT_SHA,p.QA:p.QA_SHA,p.DISK:p.DISK_SHA,p.SOURCE:p.SOURCE_SHA,p.FIXTURE:p.FIXTURE_SHA,Path(__file__):p.sha(__file__)}
    p.need(all(p.sha(path)==sha for path,sha in pins.items()),"Frozen inventory dependencies changed")
    report={"collection_success":False,"accepted":False,"registration_seek_save_or_graph_request":False,"errors":[],"inventory":{}}
    before=source.current_manifest();report["source_before"]=before
    try:
        report["artist_before"]=disk.proof(args.artist_protection,args.artist_protection_sha);q=p.readers(bpy)
        def value(item,depth=0):
            if isinstance(item,bpy.types.ID):return {"type":type(item).__name__,"ID":q.id_name(item),"native_pointer":item.as_pointer()}
            if isinstance(item,(bool,int,float)) or item is None:return {"type":type(item).__name__,"value":item}
            if isinstance(item,str):return {"type":"str","length":len(item),"value_prefix":item[:1024],"complete":len(item)<=1024}
            if hasattr(item,"items"):
                pairs=list(item.items());return {"type":type(item).__name__,"keys":[str(k) for k,_ in pairs],"values":{str(k):value(v,depth+1) for k,v in pairs[:128]} if depth<5 else "Unrecorded depth limit","complete":len(pairs)<=128 and depth<5}
            if hasattr(item,"to_list"):item=item.to_list()
            if isinstance(item,(list,tuple)):return {"type":type(item).__name__,"count":len(item),"values":[value(v,depth+1) for v in item[:32]] if depth<5 else "Unrecorded depth limit","complete":len(item)<=32 and depth<5}
            return {"type":type(item).__name__,"status":"Unrecorded unsupported storage"}
        for label,path in (("Artist",Path(report["artist_before"]["receipt"]["artist_path"])),("7ac",p.FIXTURE)):
            bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False);protection=q.Protection()
            row={"current_scene":bpy.context.scene.name,"filepath":bpy.data.filepath,"scenes":[],"objects":[]}
            for scene in bpy.data.scenes:
                row["scenes"].append({"name":scene.name,"custom_keys":list(scene.keys()),"CD_storage":{k:value(v) for k,v in scene.items() if str(k).startswith("character_designer")},
                    "Setup_raw":value(scene.get("character_designer_setup")),"Setup_RNA":value(getattr(scene,"character_designer_setup",None))})
            for obj in bpy.data.objects:
                if obj.type not in ("MESH","ARMATURE"):continue
                entry={"name":obj.name,"type":obj.type,"ID":q.id_name(obj),"data":q.id_name(obj.data),"parent":q.id_name(obj.parent),"parent_type":obj.parent_type,"parent_bone":obj.parent_bone,
                    "custom_keys":list(obj.keys()),"CD_storage":{k:value(v) for k,v in obj.items() if str(k).startswith("character_designer")},
                    "data_CD_storage":{k:value(v) for k,v in obj.data.items() if str(k).startswith("character_designer")},
                    "native_ARM_bindings":[{"name":m.name,"target":q.id_name(m.object),"target_pointer":m.object.as_pointer() if m.object else None,"enabled":m.show_viewport} for m in obj.modifiers if m.type=="ARMATURE"]}
                if p.RECORD_KEY in obj:
                    try:
                        record=json.loads(obj[p.RECORD_KEY]);entry["record_identity"]={k:record.get(k) for k in ("source","rig","owner","shared")};entry["record_keys"]=list(record)
                        entry["surface_body"]=record.get("physics",{}).get("surface",{}).get("body")
                    except Exception as error:entry["record_parse_unknown"]=repr(error)
                row["objects"].append(entry)
            row["loaded_raw_Rest_Actions_NLA_unchanged"]=protection.verify();p.need(row["loaded_raw_Rest_Actions_NLA_unchanged"]["success"],"Inventory changed loaded assets")
            report["inventory"][label]=p.primitive(row)
        report["collection_success"]=True
    except Exception as error:report["errors"].append({"exception":repr(error),"traceback":traceback.format_exc()})
    finally:
        try:
            bpy.ops.wm.read_factory_settings(use_empty=True);report["loaded_scenes_disposed"]=True
            report["artist_after"]=disk.proof(args.artist_protection,args.artist_protection_sha);report["source_after"]=source.current_manifest()
            p.need(report["source_after"]==before and all(p.sha(path)==sha for path,sha in pins.items()),"Files/source changed");report["disk_and_source_exact"]=True
        except Exception as error:report["errors"].append({"final_guard":repr(error)})
        report["collection_success"]=report["collection_success"] and not report["errors"]
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2),encoding="utf-8")
    print(json.dumps({"collection_success":report["collection_success"],"report":str(args.output),"errors":report["errors"]}));return 0 if report["collection_success"] else 2


if __name__=="__main__":raise SystemExit(main())
