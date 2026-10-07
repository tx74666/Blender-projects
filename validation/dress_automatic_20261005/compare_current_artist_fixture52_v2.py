"""Explicit QA Body/Dress selection, verified against native saved ownership.

No saved Character Setup registration is claimed. Names are mandatory inputs;
content equality is measured separately after pointer/binding identity checks.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PARENT=HERE/"compare_current_artist_fixture52.py"
PARENT_SHA="b0b4730dac104dc6ad750eaba2ee7cb89acf6ed57a274d15f8c7bc57f296ec6f"
INVENTORY=HERE/"actual_saved_pointer_inventory_52_20261007_010841_855/report.json"
INVENTORY_SHA="cb4d4146d1a165245cae37048ca7010c17adcbc495d4f5c16e5faca9027685d8"
OWNER_KEY="character_designer_skirt_owner"
SHARED_KEY="character_designer_shared_skirts_v1"


def parent():
    spec=importlib.util.spec_from_file_location("comparator_v2_frozen",PARENT);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    p.need(p.sha(PARENT)==PARENT_SHA and p.sha(INVENTORY)==INVENTORY_SHA,"Frozen comparator/inventory changed")
    return p


def locate_explicit(bpy,p,body_name,dress_name,receipts):
    scene=bpy.context.scene;body=bpy.data.objects.get(body_name);dress=bpy.data.objects.get(dress_name)
    p.need(body is not None and dress is not None and body!=dress and body.type==dress.type=="MESH","Explicit Body/Dress mesh inputs missing or ambiguous")
    p.need(body.name in scene.objects and dress.name in scene.objects,"Explicit Body/Dress not in saved current scene")
    p.need(p.RECORD_KEY in dress and p.RIG_KEY in dress,"Explicit Dress has no saved native record/RIG pointer")
    record=json.loads(dress[p.RECORD_KEY]);rig=dress[p.RIG_KEY]
    p.need(isinstance(rig,bpy.types.Object) and rig.type=="ARMATURE" and rig.name in scene.objects,"Dress authoritative MainRig pointer missing")
    p.need(record["source"]==dress.name and record["rig"]==rig.name and record.get("shared") and dress.get(OWNER_KEY)==record["owner"],"Saved Dress owner/source/shared Rig record mismatch")
    shared=rig.get(SHARED_KEY)
    p.need(shared is not None and shared.get(record["owner"])==dress,"MainRig sharedSkirts owner is not exact explicit Dress pointer")
    for label,obj in (("Body",body),("Dress",dress)):
        p.need([m.object for m in obj.modifiers if m.type=="ARMATURE" and m.show_viewport]==[rig],"Explicit "+label+" must have one enabled ARM targeting authoritative Dress Rig")
    fixture=Path(bpy.data.filepath).resolve()==p.FIXTURE.resolve()
    saved_body=record.get("physics",{}).get("surface",{}).get("body")
    p.need(not fixture or saved_body==body_name,"Immutable7ac surface.body must equal explicit Body selection")
    receipts.append({"file":bpy.data.filepath,"selection_scope":"Mandatory explicit QA Body/Dress; no artist Setup registration or locator fallback",
        "Body":body_name,"Dress":dress_name,"MainRig":rig.name,"owner":record["owner"],"record_RIG_sharedSkirts_ARM_identity_exact":True,
        "fixture_saved_surface_body":saved_body,"fixture_record_body_matches_input":fixture and saved_body==body_name,
        "artist_registered_setup_claimed":False,"raw_content_same_model":"Measured separately by comparator","accepted":False})
    return scene,rig,body,dress,record


def main():
    p=parent();parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument("--body-object",required=True);parser.add_argument("--dress-object",required=True)
    raw=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    explicit,remaining=parser.parse_known_args(raw)
    output=Path(remaining[remaining.index("--output")+1]);receipts=[]
    original_argv,original_locate,original_file=sys.argv,p.locate,p.__file__
    try:
        p.locate=lambda bpy:locate_explicit(bpy,p,explicit.body_object,explicit.dress_object,receipts)
        p.__file__=str(Path(__file__));sys.argv=[*original_argv[:original_argv.index("--")+1],*remaining]
        result=p.main()
    finally:
        sys.argv=original_argv;p.locate=original_locate;p.__file__=original_file
    report=json.loads(output.read_text(encoding="utf-8"));pins_exact=p.sha(PARENT)==PARENT_SHA and p.sha(INVENTORY)==INVENTORY_SHA
    report.update(explicit_QA_selection=receipts,parent_and_inventory_pins_exact=pins_exact,
        historical_failed_saved_Setup_locator_not_upgraded=True,saved_Setup_registration_claimed=False,
        inventory_provenance={"path":str(INVENTORY),"sha256":INVENTORY_SHA},immutable_parent={"path":str(PARENT),"sha256":PARENT_SHA})
    report["collection_success"]=report["collection_success"] and pins_exact and len(receipts)==2
    output.write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2),encoding="utf-8")
    return result if report["collection_success"] else 2


if __name__=="__main__":raise SystemExit(main())
