import bpy,sys,runpy,json
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import forearm_twist,bone_display_sync
OUT=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'fixtures/X_before_setup_repair_20260912_163011.blend'),load_ui=False,use_scripts=False)
cd.register()
namespace=runpy.run_path(str(OUT/'repair_reversal_20260912.py'))
result=namespace['repair']()
assert not forearm_twist._BUSY and not bone_display_sync._BUSY
bpy.context.view_layer.update()
assert result['ok']
print('REGISTERED_HANDLER_REPAIR',json.dumps({'ok':True,'meshes_preserved':result['meshes_weights_shapes_objects_unchanged'],'actions_preserved':result['animations_unchanged'],'records_preserved':result['corrective_metadata_unchanged'],'twist_errors':forearm_twist._ERRORS}),flush=True)
