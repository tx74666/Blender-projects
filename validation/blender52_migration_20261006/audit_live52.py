import bpy
import json
import os
import sys
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\Validation\blender52_migration_20261006\live52.json')
rig = bpy.data.objects.get('CoshaRig')
module = sys.modules.get('character_designer')
hips = rig.pose.bones.get('Hips') if rig and rig.type == 'ARMATURE' else None
report = {
    'pid': os.getpid(),
    'blender_version': bpy.app.version_string,
    'blender_binary': bpy.app.binary_path,
    'filepath': bpy.data.filepath,
    'frame': bpy.context.scene.frame_current,
    'object_mode': rig.mode if rig else None,
    'rig_bones': len(rig.data.bones) if rig else None,
    'active_bone': rig.data.bones.active.name if rig and rig.data.bones.active else None,
    'hips_display_scale': list(hips.custom_shape_scale_xyz) if hips else None,
    'character_designer_file': getattr(module, '__file__', None),
    'character_designer_version': list(module.bl_info['version']) if module else None,
    'character_designer_enabled': 'character_designer' in bpy.context.preferences.addons,
    'asset_libraries': [{'name': x.name, 'path': x.path} for x in bpy.context.preferences.filepaths.asset_libraries],
    'actions': [x.name for x in bpy.data.actions],
}
assert bpy.app.version[:2] == (5, 2), report
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve(), report
assert module is not None and tuple(module.bl_info['version']) == (0, 76, 3), report
assert 'Blender\\5.2\\scripts\\addons' in str(module.__file__), report
assert report['character_designer_enabled'], report
assert rig is not None and report['rig_bones'] == 346, report
assert report['hips_display_scale'] == [0.0, 0.0, 0.0], report
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('X2_LIVE_52_VERIFIED', report['pid'], report['blender_version'])
bpy.context.area.ui_type = 'ShaderNodeTree'
