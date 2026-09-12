import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import forearm_twist as rt,limb_ik
from character_designer.forearm_twist_topology import detect_rings
OUT=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'fixtures/X_forearm_ranges_0555_source.blend'),load_ui=False,use_scripts=False)
cd.register()
rig=bpy.data.objects['CoshaRig'];obj=bpy.data.objects['Cosha']
if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
for o in bpy.context.selected_objects:o.select_set(False)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
report={'objects':(obj.name,rig.name),'keys':list(obj.data.shape_keys.key_blocks.keys()),'old_errors':rt._ERRORS}
try:
    report['wrist_sync']=limb_ik.sync_wrist_local_axes(rig)
    inv=limb_ik._validate_inventory(rig)
    report['limbs']={':'.join(k):dict(chain=v['chain'],auto_align=v['auto_align']) for k,v in inv['rigs'].items()}
    report['rings']={s:[dict(position=r['position'],size=len(r['vertices'])) for r in detect_rings(obj,rig,*inv['rigs'][('ARM',s)]['chain'][1:])] for s in ('L','R')}
    result=rt.start_test(bpy.context,obj,'L',symmetry=True,recapture=True)
    report['start']=dict(rings=len(result['rings']),range=(result['range_start'],result['range_end']),pose_locked=rt._SESSION['pose_locked'])
    rt.finish_test(bpy.context,confirm=False)
except Exception as e:report['error']=str(e);report['traceback']=traceback.format_exc()
(OUT/'forearm_ranges_actual_0555_probe.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('ACTUAL_FOREARM_PROBE',json.dumps(report),flush=True)
