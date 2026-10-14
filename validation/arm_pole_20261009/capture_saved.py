import bpy
from pathlib import Path

BASE = Path(r'D:\Blender\Projects\Character\X\validation\arm_pole_20261009')
with bpy.data.libraries.load(r'D:\Blender\Projects\Character\X\X.blend', link=False) as (src, dst):
    assert 'CoshaRig' in src.objects
    dst.objects = ['CoshaRig']
rig = bpy.data.objects['CoshaRig']
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.context.view_layer.update()
CAPTURE_OUTPUT_PATH = BASE / 'saved_before.json'
exec(compile((BASE / 'capture_live.py').read_text(encoding='utf-8'), str(BASE / 'capture_live.py'), 'exec'))
print('SAVED_ONLY_ARMATURE_LOADED', len(bpy.data.objects), len(bpy.data.meshes))
