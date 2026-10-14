import bpy
import json
from pathlib import Path

rig = bpy.data.objects['CoshaRig.001']
def saved_strings(owner):
    return {key: owner[key] for key in owner.keys() if isinstance(owner[key], str)}
data = {'rig_props': saved_strings(rig), 'data_props': saved_strings(rig.data),
        'scene_props': saved_strings(bpy.context.scene)}
path = Path(r'D:\Blender\Projects\Character\X\validation\original_bone_diagnosis_20261010\animation_link_readonly.json')
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'path': str(path), 'rig_keys': list(data['rig_props']),
                  'data_keys': list(data['data_props']), 'scene_keys': list(data['scene_props'])}, ensure_ascii=False))
