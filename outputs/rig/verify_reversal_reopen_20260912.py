import bpy,sys,json,runpy
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik,forearm_twist as twist,foot_controls,torso_controls,spine_ik_fk
OUT=Path(__file__).parent
helper=runpy.run_path(str(OUT/'verify_root_height_0523_saved.py'))
source=OUT/'fixtures/X_before_setup_repair_20260912_163011.blend'
dest=OUT/'fixtures/X_repaired_roll_20260912.blend'
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
actions=helper['animation_state']()
bpy.ops.wm.open_mainfile(filepath=str(dest),load_ui=False,use_scripts=False)
assert actions==helper['animation_state'](),'Animation changed'
rig=bpy.data.objects['CoshaRig'];print('INVENTORY',len(limb_ik._validate_inventory(rig)['rigs']))
for m in (foot_controls,torso_controls,spine_ik_fk):assert m.validate(rig)
print('ACTION_UNCHANGED',True)
for o in bpy.data.objects:
    if o.type!='MESH' or twist.RECORD_KEY not in o:continue
    for side,r in twist._records(o).items():
        current=twist._rest_signature(rig,r['chain'])
        print('TWIST',o.name,side,{'exact_match':r['rest']==current,'max_error':max(abs(a-b) for (_,old),(_,new) in zip(r['rest'],current) for a,b in zip(old,new)),'topology_match':r['topology']==twist._topology(o.data),'enabled':r['enabled'],'key_mute':o.data.shape_keys.key_blocks[r['key']].mute})
