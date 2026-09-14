import bpy
import character_designer
import json
from pathlib import Path

rig = bpy.data.objects['CoshaRig']
config = rig.character_designer_unity_export
assert config.last_report and Path(config.last_report).is_file(), 'Live export must finish first'
assert config.last_status.startswith('Exported'), config.last_status
config.directory = r'D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha'
config.filename = 'Cosha'
record = {'version': character_designer.bl_info['version'], 'folder': config.directory,
          'filename': config.filename, 'asset_id':config.asset_id,
          'extras': [e.object.name for e in config.extras if e.enabled],
          'last_test_status': config.last_status, 'last_test_report': config.last_report,
          'unity_import_verified': False}
Path(r'D:\Blender\Projects\Character\X\outputs\unity_export\live_profile.json').write_text(
    json.dumps(record, indent=2), encoding='utf8')
bpy.context.area.type = 'VIEW_3D'
def save_configured_character():
    bpy.ops.wm.save_as_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend')
    return None
bpy.app.timers.register(save_configured_character, first_interval=1.0)
