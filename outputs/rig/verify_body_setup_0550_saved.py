"""Read-only verification of the saved production file."""
import bpy,sys,json,hashlib
from pathlib import Path
out=Path(__file__).parent
source=out.parents[1]/'X.blend'
before=hashlib.sha256(source.read_bytes()).hexdigest()
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
cd.register()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
from character_designer import body_setup,body_setup_removal,limb_ik
rig=bpy.data.objects['CoshaRig']
result=body_setup.plan(bpy.context,rig)
assert not result['blocked'], result
assert all(entry['status']=='REUSE' for entry in result['components']),result
preflight=body_setup_removal.preflight(bpy.context,rig,keep_native_rest=True)
report={'ok':True,'version':list(cd.bl_info['version']),'all_components_reused':True,
        'limbs':len(limb_ik._validate_inventory(rig)['rigs']),
        'remove_preflight_bones':len(preflight['names']),
        'rig_object_hidden':rig.hide_get(),
        'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before}
(out/'body_setup_0550_saved_verification.json').write_text(json.dumps(report,indent=2))
assert report['source_unchanged']
print(json.dumps(report))
