import bpy, json, traceback
from pathlib import Path
import character_designer
from character_designer import finger_layout

target=bpy.data.objects['Cosha']
reload_before=finger_layout.fingerprint(target)
reload_keys={key.name:key.value for key in target.data.shape_keys.key_blocks}
character_designer._reload_addon_deferred()
exec(compile(Path(r'D:\Blender\Projects\Character\X\outputs\topology_subdivision_20260921\rebind_live.py').read_text(encoding='utf8'),'rebind_live.py','exec'))
from character_designer import finger_layout
result_path=Path(r'D:\Blender\Projects\Character\X\outputs\topology_subdivision_20260921\live_after.json')
result=json.loads(result_path.read_text(encoding='utf8'))
result['reload_mesh_unchanged']=reload_before==finger_layout.fingerprint(target)
result['reload_key_values_unchanged']=reload_keys=={key.name:key.value for key in target.data.shape_keys.key_blocks}
result_path.write_text(json.dumps(result,indent=2),encoding='utf8')
